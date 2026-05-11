from abc import ABC, abstractmethod

class BaseBroker(ABC):
    """
    브로커(증권사) 연결을 위한 공통 인터페이스입니다.
    향후 한국투자증권 등 다른 API로 변경하더라도 
    메인 트레이딩 로직은 전혀 수정할 필요가 없도록 추상화합니다.
    """
    
    @abstractmethod
    def get_current_price(self, symbol: str) -> float:
        pass
        
    @abstractmethod
    def submit_order(self, symbol: str, qty: int, side: str, order_type: str = "market") -> dict:
        pass
        
    @abstractmethod
    def get_position(self, symbol: str) -> dict:
        pass
        
    @abstractmethod
    def get_account_balance(self) -> float:
        """계좌의 총 자산(Portfolio Value)을 반환합니다."""
        pass
