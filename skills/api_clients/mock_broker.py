from .base_broker import BaseBroker

class MockBroker(BaseBroker):
    """
    테스트 하네스를 위한 가상 브로커리지 어댑터입니다.
    실제 증권사 API 호출 없이 내부 메모리에서 잔고 변화 및 포지션을 시뮬레이션합니다.
    """
    def __init__(self, initial_balance=100000.0):
        self.current_price = 0.0
        self.positions = {}
        self.orders = []
        self.balance = initial_balance
        self.order_counter = 0

    def set_current_price(self, price: float):
        """Mock Data Injector가 현재 시세를 업데이트할 때 사용합니다."""
        self.current_price = price
        
    def get_current_price(self, symbol: str) -> float:
        return self.current_price
        
    def submit_order(self, symbol: str, qty: int, side: str, order_type: str = "market") -> dict:
        self.order_counter += 1
        order_id = f"mock_{side}_{self.order_counter}"
        
        # 시장가 주문 즉시 체결 시뮬레이션
        if side == "buy":
            cost = qty * self.current_price
            if self.balance >= cost:
                self.balance -= cost
                pos = self.positions.get(symbol, {"qty": 0, "avg_entry_price": 0.0})
                
                total_cost = pos["qty"] * pos["avg_entry_price"] + cost
                new_qty = pos["qty"] + qty
                new_avg = total_cost / new_qty
                
                self.positions[symbol] = {"qty": new_qty, "avg_entry_price": new_avg}
                order = {"order_id": order_id, "status": "filled", "side": "buy", "qty": qty, "price": self.current_price}
                self.orders.append(order)
                return order
            else:
                return {"order_id": order_id, "status": "rejected", "reason": "insufficient funds"}
                
        elif side == "sell":
            pos = self.positions.get(symbol, {"qty": 0, "avg_entry_price": 0.0})
            if pos["qty"] >= qty:
                revenue = qty * self.current_price
                self.balance += revenue
                pos["qty"] -= qty
                if pos["qty"] == 0:
                    pos["avg_entry_price"] = 0.0
                self.positions[symbol] = pos
                
                order = {"order_id": order_id, "status": "filled", "side": "sell", "qty": qty, "price": self.current_price}
                self.orders.append(order)
                return order
            else:
                return {"order_id": order_id, "status": "rejected", "reason": "insufficient qty"}
                
    def get_position(self, symbol: str) -> dict:
        return self.positions.get(symbol, {"qty": 0, "avg_entry_price": 0.0})
