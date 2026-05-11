import asyncio
import os
import logging
import time
import threading
import requests as req_lib
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from .database import engine, Base, get_db
from .models import User, APICredential, TradingSetting
from .auth import get_password_hash, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY, ALGORITHM, encrypt_data, decrypt_data
from datetime import timedelta
import jwt
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv
import pandas as pd

from skills.api_clients.alpaca_client import AlpacaClient
from skills.core_logic.state_machine import TradingStateMachine
from skills.indicators.rsi import calculate_rsi

# .env 파일 로드
load_dotenv()

# DB 테이블 생성
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Anti-Gravity Trading Bot API")

# 프론트엔드 정적 파일 서빙 (CSS/JS 404 방지)
app.mount("/img", StaticFiles(directory="dashboard/img"), name="img")
app.mount("/css", StaticFiles(directory="dashboard/css"), name="css")
app.mount("/js", StaticFiles(directory="dashboard/js"), name="js")
app.mount("/dashboard", StaticFiles(directory="dashboard"), name="dashboard")

logger = logging.getLogger("bot_engine")
logging.basicConfig(level=logging.INFO)

# 다중 사용자 대시보드 상태 DB (user_id를 키로 사용)
user_bot_states = {}
user_bots = {}

# USD/KRW 환율 캐시 (1시간 갱신)
_usd_krw_cache = {"rate": 1380.0, "fetched_at": 0.0}

def get_usd_krw_rate() -> float:
    """환율 API에서 USD→KRW 환율을 가져와 1시간 캐싱"""
    if time.time() - _usd_krw_cache["fetched_at"] < 3600:
        return _usd_krw_cache["rate"]
    try:
        res = req_lib.get("https://open.er-api.com/v6/latest/USD", timeout=3)
        if res.status_code == 200:
            rate = res.json()["rates"].get("KRW", 1380.0)
            _usd_krw_cache["rate"] = rate
            _usd_krw_cache["fetched_at"] = time.time()
            logger.info(f"환율 갱신: 1 USD = {rate:.0f} KRW")
            return rate
    except Exception as e:
        logger.warning(f"환율 조회 실패, 기본값 사용: {e}")
    return _usd_krw_cache["rate"]

def _bot_loop_thread():
    """븇 루프를 별도 daemon 스레드에서 실행
    
    asyncio task 대신 thread를 사용하는 이유:
    - requests 라이브러리의 동기 HTTP 호출이 asyncio 이벤트 루프를 블로킹함
    - 블로킹 중 Render 헬스체크 HTTP 요청이 응답을 못 받아 타임아웃 발생
    - thread는 이벤트 루프와 완전히 분리되어 FastAPI가 항상 응답 가능
    """
    # 서버 완전 시작 후 보트 루프 시작 (Render 헬스체크 시간 확보)
    time.sleep(10)
    logger.info("Bot loop thread started.")

    while True:
        try:
            db = next(get_db())
            users = db.query(User).all()

            for user in users:
                try:
                    cred = db.query(APICredential).filter(APICredential.user_id == user.id).first()
                    setting = db.query(TradingSetting).filter(TradingSetting.user_id == user.id).first()

                    if user.id not in user_bot_states:
                        symbol = setting.target_symbol if setting else "SOXL"
                        user_bot_states[user.id] = {
                            "symbol": symbol,
                            "state": "IDLE",
                            "current_price": 0.0,
                            "rsi_15m": 0.0,
                            "balance": 0.0,
                            "today_profit_pct": 0.0,
                            "recent_trades": [],
                            "api_connected": False,
                            "is_active": False
                        }

                    state_db = user_bot_states[user.id]

                    if not cred or not cred.api_key:
                        state_db["api_connected"] = False
                        continue

                    if user.id not in user_bots:
                        decrypted_api_key = decrypt_data(cred.api_key)
                        decrypted_secret_key = decrypt_data(cred.secret_key)
                        decrypted_account = decrypt_data(cred.account_number) if cred.account_number else None

                        is_paper = (cred.env_type == "paper")
                        if cred.broker_name == "kis":
                            from skills.api_clients.kis_client import KisClient
                            broker = KisClient(is_paper=is_paper, api_key=decrypted_api_key, secret_key=decrypted_secret_key, account_number=decrypted_account)
                        else:
                            broker = AlpacaClient(is_paper=is_paper, api_key=decrypted_api_key, secret_key=decrypted_secret_key)

                        trade_amount = setting.trade_amount if setting else 500.0  # 기본값 $500
                        bot = TradingStateMachine(broker=broker, symbol=state_db["symbol"], trade_amount=trade_amount)
                        user_bots[user.id] = {"broker": broker, "bot": bot}

                    user_bot = user_bots[user.id]
                    broker = user_bot["broker"]
                    bot = user_bot["bot"]

                    # 종목 변경 체크
                    if setting and bot.symbol != setting.target_symbol:
                        bot.symbol = setting.target_symbol
                        state_db["symbol"] = setting.target_symbol

                    # 1. 시세 조회
                    current_price = broker.get_current_price(bot.symbol)
                    state_db["current_price"] = current_price

                    # 2. 15분봉 RSI 계산 (알파카인 경우만)
                    try:
                        if hasattr(broker, 'api') and broker.api:
                            bars = broker.api.get_bars(bot.symbol, "15Min", limit=30).df
                            if not bars.empty:
                                rsi_df = calculate_rsi(bars, period=14, price_col="close")
                                current_rsi = float(rsi_df['rsi'].iloc[-1])
                                state_db["rsi_15m"] = current_rsi
                            else:
                                current_rsi = state_db["rsi_15m"]
                        else:
                            current_rsi = state_db["rsi_15m"]
                    except Exception:
                        current_rsi = state_db["rsi_15m"]

                    # 3. 메인 트레이딩 로직 실행
                    is_active = setting.is_active if setting else False
                    state_db["is_active"] = is_active

                    if current_price > 0 and is_active:
                        bot.process_data(current_price, current_rsi)

                    # 4. 상태 및 잔고 업데이트
                    state_db["state"] = bot.state.value
                    # get_balance_detail() 지원 브로커(KIS)는 원화/달러 각각 저장
                    if hasattr(broker, 'get_balance_detail'):
                        bd = broker.get_balance_detail()
                        state_db["balance_krw"] = bd.get("krw", 0.0)
                        state_db["balance_usd"] = bd.get("usd", 0.0)
                        usd_krw = _usd_krw_cache.get("rate", 1380.0)
                        state_db["balance"] = bd["usd"] if bd["usd"] > 0 else round(bd["krw"] / usd_krw, 4)
                    else:
                        b = broker.get_account_balance()
                        state_db["balance"] = b
                        state_db["balance_krw"] = 0.0
                        state_db["balance_usd"] = b
                    pos = broker.get_position(bot.symbol)
                    state_db["held_qty"] = pos.get("qty", 0) if pos else 0
                    state_db["api_connected"] = True

                except Exception as user_e:
                    logger.error(f"Error processing bot for user {user.id}: {user_e}")
                    if user.id in user_bot_states:
                        user_bot_states[user.id]["api_connected"] = False

        except Exception as e:
            logger.error(f"Bot loop main error: {e}")

        # 15초마다 갱신
        time.sleep(15)

from sqlalchemy import text
from .database import SessionLocal

@app.on_event("startup")
async def startup_event():
    """uvicorn 포트 바인딩을 막지 않도록 즉시 리턴.
    DB 작업(migration) + 봇 루프 모두 daemon thread에서 실행."""
    def _init_and_run():
        # 10초 대기: Render 헬스체크가 포트를 확인할 시간 확보
        import time as _time
        _time.sleep(10)

        # DB 마이그레이션 (timeout 5초 내 실패 시 skip)
        try:
            from sqlalchemy import text
            engine_name = engine.dialect.name
            db = SessionLocal()
            if engine_name in ["mysql", "mariadb"]:
                db.execute(text("ALTER TABLE api_credentials MODIFY api_key VARCHAR(512);"))
                db.execute(text("ALTER TABLE api_credentials MODIFY secret_key VARCHAR(512);"))
                db.execute(text("ALTER TABLE api_credentials MODIFY account_number VARCHAR(512);"))
            elif engine_name == "postgresql":
                db.execute(text("ALTER TABLE api_credentials ALTER COLUMN api_key TYPE VARCHAR(512);"))
                db.execute(text("ALTER TABLE api_credentials ALTER COLUMN secret_key TYPE VARCHAR(512);"))
                db.execute(text("ALTER TABLE api_credentials ALTER COLUMN account_number TYPE VARCHAR(512);"))
            db.commit()
            logger.info(f"DB 마이그레이션 완료 (dialect: {engine_name})")
        except Exception as e:
            logger.warning(f"Migration skipped: {e}")
        finally:
            try: db.close()
            except: pass

        # 봇 루프 실행
        logger.info("Bot loop thread started.")
        _bot_loop_thread()

    # 마이그레이션 + 봇 루프를 하나의 daemon thread에서 실행
    t = threading.Thread(target=_init_and_run, daemon=True, name="InitAndBotThread")
    t.start()
    logger.info("✅ Startup event complete. Bot thread scheduled.")


@app.get("/")
@app.head("/")
def read_root():
    return FileResponse("dashboard/index.html")

@app.get("/index.html")
def get_index():
    return FileResponse("dashboard/index.html")

@app.get("/login.html")
def get_login():
    return FileResponse("dashboard/login.html")

@app.get("/signup.html")
def get_signup():
    return FileResponse("dashboard/signup.html")

@app.get("/settings.html")
def get_settings():
    return FileResponse("dashboard/settings.html")

# 미들웨어 함수를 라우트 선언 전에 사용하기 위해 앞으로 가져오기
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

@app.get("/api/status")
def get_bot_status(current_user: User = Depends(get_current_user)):
    state = user_bot_states.get(current_user.id, {
        "symbol": "SOXL",
        "state": "IDLE",
        "current_price": 0.0,
        "rsi_15m": 0.0,
        "balance": 0.0,
        "held_qty": 0,
        "today_profit_pct": 0.0,
        "recent_trades": [],
        "api_connected": False,
        "is_active": False
    }).copy()
    state["email"] = current_user.email
    state["usd_krw"] = get_usd_krw_rate()
    # balance_krw / balance_usd 다 단리지 않으면 기본값 보장
    state.setdefault("balance_krw", 0.0)
    state.setdefault("balance_usd", state.get("balance", 0.0))
    return state

@app.get("/api/admin/users")
def get_admin_users(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.email != "lisob@naver.com":
        raise HTTPException(status_code=403, detail="Not authorized")
    users = db.query(User).all()
    return [{"id": u.id, "email": u.email} for u in users]

# --- Auth 라우트 ---
class UserCreate(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

@app.post("/api/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pw = get_password_hash(user.password)
    new_user = User(email=user.email, hashed_password=hashed_pw)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully"}

@app.post("/api/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
# -------------------

# (JWT 미들웨어 위로 이동됨)

# --- 유저별 설정 API ---
class APISettings(BaseModel):
    broker: str
    env_type: str
    api_key: str
    secret_key: str
    account_number: str = None

@app.post("/api/settings")
def save_settings(settings: APISettings, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        # 다중 사용자 환경이므로 .env가 아닌 DB에 저장합니다. (비밀키는 원래 암호화해야 하나 데모상 평문 저장)
        db_cred = db.query(APICredential).filter(APICredential.user_id == current_user.id).first()
        if not db_cred:
            db_cred = APICredential(user_id=current_user.id)
            db.add(db_cred)
            
        db_cred.broker_name = settings.broker
        db_cred.env_type = settings.env_type
        db_cred.api_key = encrypt_data(settings.api_key)
        db_cred.secret_key = encrypt_data(settings.secret_key)
        db_cred.account_number = encrypt_data(settings.account_number) if settings.account_number else None
        db.commit()
        
        # 새로운 API 키가 반영될 수 있도록 메모리에 캐싱된 봇 인스턴스 초기화
        if current_user.id in user_bots:
            del user_bots[current_user.id]
        
        return {"status": "success", "message": "API credentials saved to DB"}
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/settings")
def get_api_settings(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """현재 저장된 자격증명 조회 (API 키는 마스킹 처리)"""
    cred = db.query(APICredential).filter(APICredential.user_id == current_user.id).first()
    setting = db.query(TradingSetting).filter(TradingSetting.user_id == current_user.id).first()
    if not cred or not cred.api_key:
        return {
            "has_credentials": False,
            "target_symbol": setting.target_symbol if setting else "SOXL",
            "trade_amount": setting.trade_amount if setting else 500.0
        }
    # HTTPS + JWT 인증으로 본인에게만 노출 → 복호화된 값 반환하여 폼 재편집 가능하게
    decrypted_api_key = decrypt_data(cred.api_key) or ""
    decrypted_secret_key = decrypt_data(cred.secret_key) or ""
    decrypted_account = decrypt_data(cred.account_number) if cred.account_number else ""
    return {
        "has_credentials": True,
        "broker_name": cred.broker_name,
        "env_type": cred.env_type,
        # 연동 현황 박스용 마스킹 표시
        "masked_api_key": (decrypted_api_key[:4] + "••••" + decrypted_api_key[-4:]) if len(decrypted_api_key) > 8 else "••••",
        # 폼 재편집용 복호화 실제값
        "api_key": decrypted_api_key,
        "secret_key": decrypted_secret_key,
        "account_number": decrypted_account,
        "target_symbol": setting.target_symbol if setting else "SOXL",
        "trade_amount": setting.trade_amount if setting else 500.0
    }

@app.delete("/api/settings")
def delete_api_settings(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """저장된 자격증명 삭제 (메모리 캐시 포함)"""
    cred = db.query(APICredential).filter(APICredential.user_id == current_user.id).first()
    if cred:
        db.delete(cred)
        db.commit()
    # 메모리 캐시도 즉시 초기화
    user_bots.pop(current_user.id, None)
    user_bot_states.pop(current_user.id, None)
    logger.info(f"User {current_user.id} credentials deleted.")
    return {"status": "success", "message": "연동 정보가 삭제되었습니다."}

class TradingSettingsUpdate(BaseModel):
    target_symbol: str
    trade_amount: float

@app.post("/api/trading-settings")
def update_trading_settings(settings: TradingSettingsUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        db_setting = db.query(TradingSetting).filter(TradingSetting.user_id == current_user.id).first()
        if not db_setting:
            db_setting = TradingSetting(user_id=current_user.id)
            db.add(db_setting)
        
        db_setting.target_symbol = settings.target_symbol
        db_setting.trade_amount = settings.trade_amount
        db.commit()
        
        # 봇의 상태에도 즉시 반영
        if current_user.id in user_bots:
            user_bots[current_user.id]["bot"].trade_amount = settings.trade_amount
            
        return {"status": "success", "message": "Trading settings updated"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class ManualTradeRequest(BaseModel):
    action: str # "buy" or "sell"
    qty: int

@app.post("/api/trade")
def manual_trade(req: ManualTradeRequest, current_user: User = Depends(get_current_user)):
    user_bot = user_bots.get(current_user.id)
    if not user_bot:
        return {"status": "error", "message": "봇이 아직 API에 연결되지 않았습니다. 설정 페이지에서 증권사 정보를 연동해주세요."}
    
    bot = user_bot["bot"]
    broker = user_bot["broker"]
    current_price = broker.get_current_price(bot.symbol)
    
    if req.qty <= 0:
        return {"status": "error", "message": "수량은 1주 이상이어야 합니다."}

    if req.action == "buy":
        res = broker.submit_order(bot.symbol, req.qty, "buy")
        if res.get("status") == "filled":
            bot.high_water_mark = current_price
            bot.partial_sold = False
            bot._transition_to(bot.state.HOLDING)
        return {"status": "success", "message": f"{req.qty}주 수동 매수 요청 완료!"}
        
    elif req.action == "sell":
        pos = broker.get_position(bot.symbol)
        if pos.get("qty", 0) < req.qty:
            return {"status": "error", "message": f"매도 수량({req.qty}주)이 보유 수량({pos.get('qty', 0)}주)보다 많습니다."}
            
        res = broker.submit_order(bot.symbol, req.qty, "sell")
        
        # 전량 매도시 IDLE, 일부 매도시 HOLDING 유지
        new_pos = broker.get_position(bot.symbol)
        if new_pos.get("qty", 0) <= 0:
            bot._transition_to(bot.state.IDLE)
            
        return {"status": "success", "message": f"{req.qty}주 수동 매도 요청 완료!"}

class BotToggleRequest(BaseModel):
    is_active: bool

@app.post("/api/bot/toggle")
def toggle_bot(req: BotToggleRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    setting = db.query(TradingSetting).filter(TradingSetting.user_id == current_user.id).first()
    if not setting:
        setting = TradingSetting(user_id=current_user.id)
        db.add(setting)
    
    setting.is_active = req.is_active
    db.commit()
    
    # 상태 즉시 업데이트
    if current_user.id in user_bot_states:
        user_bot_states[current_user.id]["is_active"] = req.is_active
        
    status_text = "자동매매가 시작되었습니다!" if req.is_active else "자동매매가 일시정지되었습니다."
    return {"status": "success", "message": status_text, "is_active": req.is_active}
