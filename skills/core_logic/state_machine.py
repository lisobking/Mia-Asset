from enum import Enum
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BotState(Enum):
    IDLE = "IDLE"
    BUY_PENDING = "BUY_PENDING"
    HOLDING = "HOLDING"
    SELL_PENDING = "SELL_PENDING"

class TradingStateMachine:
    """
    RSI 15분봉 전략에 따른 상태 머신(State Machine)
    IDLE -> BUY_PENDING -> HOLDING -> SELL_PENDING -> IDLE 상태 전이 관리
    """
    def __init__(self, broker, symbol="SOXL"):
        self.broker = broker
        self.symbol = symbol
        self.state = BotState.IDLE
        
        # 이전 RSI 값을 추적하여 30을 '상향 돌파'하는지 확인
        self.prev_rsi = None
        
        # 보유 시 고점 기록 (Trailing Stop 용)
        self.high_water_mark = 0.0
        self.partial_sold = False

    def process_data(self, current_price: float, current_rsi: float):
        """매 캔들(또는 틱)마다 데이터를 받아 상태를 업데이트합니다."""
        
        logger.info(f"[{self.state.value}] Price: {current_price:.2f}, RSI: {current_rsi:.2f}")

        # IDLE 상태: 매수 조건 대기
        if self.state == BotState.IDLE:
            # RSI 30 이하에서 위로 돌파하는지 확인
            if self.prev_rsi is not None and self.prev_rsi <= 30 and current_rsi > 30:
                logger.info("매수 조건 충족! (RSI 30 상향 돌파)")
                self._transition_to(BotState.BUY_PENDING)
                self.execute_buy_order(current_price)

        # HOLDING 상태: 매도 조건 대기 (익절, 트레일링 스탑, 손절)
        elif self.state == BotState.HOLDING:
            pos = self.broker.get_position(self.symbol)
            if pos["qty"] == 0:
                self._transition_to(BotState.IDLE)
                self.prev_rsi = current_rsi
                return

            entry_price = pos["avg_entry_price"]
            profit_pct = (current_price - entry_price) / entry_price * 100
            
            # 최고가 경신 시 업데이트 (트레일링 스탑 기준)
            if current_price > self.high_water_mark:
                self.high_water_mark = current_price

            # 1. 손절 (-2%)
            if profit_pct <= -2.0:
                logger.warning(f"손절 조건 도달! (손익률: {profit_pct:.2f}%)")
                self._transition_to(BotState.SELL_PENDING)
                self.execute_sell_order(pos["qty"])
                return

            # 2. RSI 70 도달 시 전량 청산
            if current_rsi >= 70:
                logger.info(f"RSI 과매수(70) 도달! 전량 익절 (손익률: {profit_pct:.2f}%)")
                self._transition_to(BotState.SELL_PENDING)
                self.execute_sell_order(pos["qty"])
                return

            # 3. 익절 (+4% 50% 매도)
            if profit_pct >= 4.0 and not self.partial_sold:
                sell_qty = max(1, pos["qty"] // 2)
                logger.info(f"+4% 도달! 절반({sell_qty}주) 익절 (손익률: {profit_pct:.2f}%)")
                self.broker.submit_order(self.symbol, sell_qty, "sell")
                self.partial_sold = True

            # 4. 트레일링 스탑 (최고점 대비 1.5% 하락 시 전량 청산)
            drawdown_from_high = (self.high_water_mark - current_price) / self.high_water_mark * 100
            if drawdown_from_high >= 1.5:
                logger.info(f"트레일링 스탑 발동! (고점 대비 하락: {drawdown_from_high:.2f}%)")
                self._transition_to(BotState.SELL_PENDING)
                self.execute_sell_order(pos["qty"])
                return

        # 이전 RSI 기록
        self.prev_rsi = current_rsi

    def execute_buy_order(self, current_price):
        # 자금 관리: 잔고의 50% 투입 가정
        # 실제로는 position_sizer 모듈과 연동해야 함
        target_amount = 50000.0 # 하드코딩 (테스트용)
        qty = int(target_amount / current_price)
        if qty > 0:
            res = self.broker.submit_order(self.symbol, qty, "buy")
            if res["status"] == "filled":
                self.high_water_mark = current_price
                self.partial_sold = False
                self._transition_to(BotState.HOLDING)
            else:
                self._transition_to(BotState.IDLE)
        else:
            self._transition_to(BotState.IDLE)

    def execute_sell_order(self, qty):
        res = self.broker.submit_order(self.symbol, qty, "sell")
        if res["status"] == "filled":
            self._transition_to(BotState.IDLE)

    def _transition_to(self, new_state: BotState):
        logger.info(f"State Transition: {self.state.value} -> {new_state.value}")
        self.state = new_state
