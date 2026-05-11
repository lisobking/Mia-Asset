import os
from .base_broker import BaseBroker
import alpaca_trade_api as tradeapi

class AlpacaClient(BaseBroker):
    def __init__(self, is_paper=True, api_key=None, secret_key=None):
        # 파라미터가 없으면 환경변수에서 로드
        self.api_key = api_key or os.getenv("ALPACA_API_KEY", "")
        self.secret_key = secret_key or os.getenv("ALPACA_SECRET_KEY", "")
        # 모의투자(Paper) 여부에 따라 엔드포인트 분기
        self.base_url = "https://paper-api.alpaca.markets" if is_paper else "https://api.alpaca.markets"
        
        if self.api_key and self.secret_key:
            self.api = tradeapi.REST(self.api_key, self.secret_key, self.base_url, api_version='v2')
        else:
            self.api = None
        
    def get_current_price(self, symbol: str) -> float:
        """종목의 가장 최근 가격(호가) 반환"""
        if not self.api: return 0.0
        quote = self.api.get_latest_quote(symbol)
        return float(quote.ap)
        
    def submit_order(self, symbol: str, qty: int, side: str, order_type: str = "market") -> dict:
        """시장가 주문 제출"""
        if not self.api: return {"order_id": "failed", "status": "rejected", "reason": "No API Key"}
        order = self.api.submit_order(
            symbol=symbol,
            qty=qty,
            side=side,
            type=order_type,
            time_in_force='gtc' # Good Till Cancelled
        )
        return {"order_id": order.id, "status": order.status}
        
    def get_position(self, symbol: str) -> dict:
        """현재 보유 포지션 조회"""
        if not self.api: return {"qty": 0, "avg_entry_price": 0.0}
        try:
            position = self.api.get_position(symbol)
            return {"qty": int(position.qty), "avg_entry_price": float(position.avg_entry_price)}
        except Exception:
            return {"qty": 0, "avg_entry_price": 0.0}

    def get_account_balance(self) -> float:
        """Alpaca API를 통한 실시간 총 자산(Portfolio Value) 조회"""
        if not self.api: return 0.0
        try:
            account = self.api.get_account()
            return float(account.portfolio_value)
        except Exception as e:
            # 로깅 추가 가능
            return 0.0
