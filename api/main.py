import asyncio
import os
import logging
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from .database import engine, Base, get_db
from .models import User, APICredential, TradingSetting
from .auth import get_password_hash, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY, ALGORITHM
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
app.mount("/css", StaticFiles(directory="dashboard/css"), name="css")
app.mount("/js", StaticFiles(directory="dashboard/js"), name="js")
app.mount("/dashboard", StaticFiles(directory="dashboard"), name="dashboard")

logger = logging.getLogger("bot_engine")
logging.basicConfig(level=logging.INFO)

# 다중 사용자 대시보드 상태 DB (user_id를 키로 사용)
user_bot_states = {}
user_bots = {}

async def trading_bot_loop():
    """주기적으로 각 사용자의 시세를 가져오고 매매 로직을 실행하는 백그라운드 태스크"""
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
                            "api_connected": False
                        }
                    
                    state_db = user_bot_states[user.id]
                    
                    if not cred or not cred.api_key:
                        state_db["api_connected"] = False
                        continue
                        
                    if user.id not in user_bots:
                        is_paper = (cred.env_type == "paper")
                        if cred.broker_name == "kis":
                            from skills.api_clients.kis_client import KisClient
                            broker = KisClient(is_paper=is_paper, api_key=cred.api_key, secret_key=cred.secret_key, account_number=cred.account_number)
                        else:
                            broker = AlpacaClient(is_paper=is_paper, api_key=cred.api_key, secret_key=cred.secret_key)
                        
                        bot = TradingStateMachine(broker=broker, symbol=state_db["symbol"])
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
                    
                    # 2. 15분봉 데이터 조회 및 RSI 계산
                    try:
                        bars = broker.api.get_bars(bot.symbol, "15Min", limit=30).df
                        if not bars.empty:
                            rsi_df = calculate_rsi(bars, period=14, price_col="close")
                            current_rsi = float(rsi_df['rsi'].iloc[-1])
                            state_db["rsi_15m"] = current_rsi
                        else:
                            current_rsi = 50.0
                    except Exception as e:
                        current_rsi = state_db["rsi_15m"]

                    # 3. 메인 트레이딩 로직 실행
                    if current_price > 0:
                        bot.process_data(current_price, current_rsi)
                    
                    # 4. 상태 및 잔고 업데이트
                    state_db["state"] = bot.state.value
                    balance = broker.get_account_balance()
                    state_db["balance"] = balance
                    state_db["api_connected"] = True
                    
                except Exception as user_e:
                    logger.error(f"Error processing bot for user {user.id}: {user_e}")
                    if user.id in user_bot_states:
                        user_bot_states[user.id]["api_connected"] = False

        except Exception as e:
            logger.error(f"Bot loop main error: {e}")
            
        # 10초마다 갱신
        await asyncio.sleep(10)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting multi-tenant background trading loop...")
    asyncio.create_task(trading_bot_loop())

@app.get("/")
@app.head("/")
def read_root():
    return RedirectResponse(url="/dashboard/index.html")

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
    return user_bot_states.get(current_user.id, {
        "symbol": "SOXL",
        "state": "IDLE",
        "current_price": 0.0,
        "rsi_15m": 0.0,
        "balance": 0.0,
        "today_profit_pct": 0.0,
        "recent_trades": [],
        "api_connected": False
    })

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
        db_cred.api_key = settings.api_key
        db_cred.secret_key = settings.secret_key
        db_cred.account_number = settings.account_number
        db.commit()
        
        return {"status": "success", "message": "API credentials saved to DB"}
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        return {"status": "error", "message": str(e)}

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
        return {"status": "success", "message": "Trading settings updated"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
