import os
import time
import requests
import logging
from .base_broker import BaseBroker

logger = logging.getLogger("kis_client")

class KisClient(BaseBroker):
    def __init__(self, is_paper=True, api_key=None, secret_key=None, account_number=None):
        self.api_key = api_key or os.getenv("KIS_API_KEY", "")
        self.secret_key = secret_key or os.getenv("KIS_SECRET_KEY", "")
        self.account_number = account_number or os.getenv("KIS_ACCOUNT", "")
        self.is_paper = is_paper
        
        # 한국투자증권 API 도메인 (모의투자는 포트 29443, 실전은 9443)
        self.base_url = "https://openapivts.koreainvestment.com:29443" if is_paper else "https://openapi.koreainvestment.com:9443"
        
        self.access_token = None
        self.token_expired_at = 0
        self._last_token_request_at = 0  # 토큰 요청 시각 기록 (분당 1회 제한 대응)
        
        logger.info(f"Initialized KIS Client for account {self.account_number} (Paper: {self.is_paper})")
        
    def _get_access_token(self):
        # 1. 유효한 토큰이 있으면 재사용
        if self.access_token and time.time() < self.token_expired_at:
            return self.access_token
        
        # 2. 마지막 요청 후 65초 이내면 대기 (제한: 분당 1회)
        elapsed = time.time() - self._last_token_request_at
        if elapsed < 65:
            wait_left = int(65 - elapsed)
            logger.warning(f"KIS 토큰 요청 쿨다운 중... {wait_left}초 남음. 기존 토큰 사용.")
            return self.access_token  # None일 수 있으나 호출자가 예외 처리
        
        # 3. 신규 토큰 발급 시도
        token_url = f"{self.base_url}/oauth2/tokenP"
        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.api_key,
            "appsecret": self.secret_key
        }
        
        self._last_token_request_at = time.time()  # 요청 시각 기록 (쿨다운 시작)
        try:
            res = requests.post(token_url, headers=headers, json=body, timeout=5)
            if res.status_code == 200:
                data = res.json()
                self.access_token = data.get("access_token")
                # KIS 토큰은 보통 24시간 유효 (안전하게 60초 미리 만료)
                self.token_expired_at = time.time() + int(data.get("expires_in", 86400)) - 60
                logger.info(f"KIS 액세스 토큰 발급 성공. 만료까지 {int(data.get('expires_in', 86400) - 60)}초")
                return self.access_token
            else:
                logger.error(f"KIS Token Error: {res.text}")
                return None
        except Exception as e:
            logger.error(f"KIS Token Request Exception: {e}")
            return None

    def _get_base_headers(self, tr_id: str):
        token = self._get_access_token()
        return {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": self.api_key,
            "appsecret": self.secret_key,
            "tr_id": tr_id
        }

    def get_current_price(self, symbol: str) -> float:
        """해외주식(미국) 현재체결가 조회 (장 마감 시 빈 문자열 안전 처리)"""
        url = f"{self.base_url}/uapi/overseas-price/v1/quotations/price"
        headers = self._get_base_headers("HHDFS00000300")
        params = {
            "AUTH": "",
            "EXCD": "NAS",  # 나스닥 기준 (NYSE: AMS, AMEX: AMX)
            "SYMB": symbol
        }
        try:
            res = requests.get(url, headers=headers, params=params, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if data.get("rt_cd") == "0":
                    output = data.get("output", {})
                    # 장 마감/데이터 없을 때 KIS는 숫자 필드를 빈 문자열('')로 반환함
                    last_str = output.get("last", "").strip()
                    if not last_str:
                        # last가 없으면 전일 종가(base)로 대체 시도
                        last_str = output.get("base", "").strip()
                    if last_str:
                        return float(last_str)
                    logger.warning(f"KIS: {symbol} 가격 데이터 없음 (장 마감 또는 미지원 종목)")
                else:
                    logger.warning(f"KIS Price API 오류: rt_cd={data.get('rt_cd')}, msg={data.get('msg1')}")
        except Exception as e:
            logger.error(f"KIS Price Fetch Error for {symbol}: {e}")
        
        return 0.0
        
    def submit_order(self, symbol: str, qty: int, side: str, order_type: str = "market") -> dict:
        """해외주식 주문"""
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/order"
        # 매수/매도에 따른 tr_id (모의/실전 다름)
        tr_id = "VTTT1002U" if side.lower() == "buy" else "VTTT1001U" # 모의투자 미국 매수/매도
        if not self.is_paper:
            tr_id = "JTTT1002U" if side.lower() == "buy" else "JTTT1001U"
            
        headers = self._get_base_headers(tr_id)
        
        # 계좌번호 파싱 (예: 12345678-01)
        cano = self.account_number[:8] if self.account_number and len(self.account_number) >= 8 else "00000000"
        acnt_prdt_cd = self.account_number.split("-")[-1] if self.account_number and "-" in self.account_number else "01"
        
        body = {
            "CANO": cano,
            "ACNT_PRDT_CD": acnt_prdt_cd,
            "OVRS_EXCG_CD": "NAS",
            "PDNO": symbol,
            "ORD_QTY": str(qty),
            "OVRS_ORD_UNPR": "0", # 시장가 0 달러
            "ORD_SVR_DVSN_CD": "0",
            "ORD_DVSN": "00" # 00: 시장가
        }
        
        try:
            res = requests.post(url, headers=headers, json=body, timeout=5)
            data = res.json()
            if data.get("rt_cd") == "0":
                return {"order_id": data.get("output", {}).get("KRX_FWDG_ORD_ORGNO", "ok"), "status": "submitted"}
            else:
                return {"order_id": "failed", "status": "rejected", "reason": data.get("msg1")}
        except Exception as e:
            logger.error(f"KIS Order Error: {e}")
            return {"order_id": "failed", "status": "error", "reason": str(e)}
            
    def get_position(self, symbol: str) -> dict:
        """해외주식 특정 종목 잔고 조회"""
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-present-balance"
        tr_id = "VTTS3012R" if self.is_paper else "CTTS3012R" # 모의/실전 해외주식 잔고
        headers = self._get_base_headers(tr_id)
        
        cano = self.account_number[:8] if self.account_number and len(self.account_number) >= 8 else "00000000"
        acnt_prdt_cd = self.account_number.split("-")[-1] if self.account_number and "-" in self.account_number else "01"
        
        params = {
            "CANO": cano,
            "ACNT_PRDT_CD": acnt_prdt_cd,
            "WCRC_FRCR_DVSN_CD": "01", # 01: 외화
            "NATN_CD": "840", # 미국
            "TR_MKET_CD": "01", # 나스닥
            "INQR_DVSN_CD": "00"
        }
        
        try:
            res = requests.get(url, headers=headers, params=params, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if data.get("rt_cd") == "0":
                    holdings = data.get("output1", [])
                    for item in holdings:
                        if item.get("ovrs_pdno") == symbol:
                            qty_str = item.get("ovrs_cblc_qty", "").strip()
                            avg_str = item.get("pchs_avg_pric", "").strip()
                            qty = int(float(qty_str)) if qty_str else 0
                            avg_price = float(avg_str) if avg_str else 0.0
                            return {"qty": qty, "avg_entry_price": avg_price}
        except Exception as e:
            logger.error(f"KIS Position Fetch Error for {symbol}: {e}")
            
        return {"qty": 0, "avg_entry_price": 0.0}

    def get_account_balance(self) -> float:
        """해외주식 체결기준 현재잔고 (외화 총 평가금액) 조회"""
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-present-balance"
        tr_id = "VTTS3012R" if self.is_paper else "CTTS3012R"
        headers = self._get_base_headers(tr_id)
        
        cano = self.account_number[:8] if self.account_number and len(self.account_number) >= 8 else "00000000"
        acnt_prdt_cd = self.account_number.split("-")[-1] if self.account_number and "-" in self.account_number else "01"
        
        params = {
            "CANO": cano,
            "ACNT_PRDT_CD": acnt_prdt_cd,
            "WCRC_FRCR_DVSN_CD": "01",
            "NATN_CD": "840",
            "TR_MKET_CD": "01",
            "INQR_DVSN_CD": "00"
        }
        
        try:
            res = requests.get(url, headers=headers, params=params, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if data.get("rt_cd") == "0":
                    summary = data.get("output2", {})
                    if isinstance(summary, list) and len(summary) > 0:
                        summary = summary[0]
                    # API 응답에 따라 총 평가금액 필드 매핑 (빈 문자열 안전 처리)
                    for field in ["tot_evlu_amt", "tot_asst_amt", "frcr_evlu_tota"]:
                        val_str = str(summary.get(field, "")).strip()
                        if val_str and val_str != "0":
                            return float(val_str)
                    return 0.0
        except Exception as e:
            logger.error(f"KIS Balance Fetch Error: {e}")
            
        return 0.0
