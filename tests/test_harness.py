import pytest
import pandas as pd
from skills.api_clients.mock_broker import MockBroker
from skills.core_logic.state_machine import TradingStateMachine, BotState

class MockDataInjector:
    """과거 캔들 데이터를 순차적으로 방출(Emit)하는 하네스 제네레이터"""
    def __init__(self, df: pd.DataFrame):
        self.df = df
        
    def stream(self):
        for index, row in self.df.iterrows():
            yield row['close'], row['rsi']

def test_harness_buy_and_sell_logic():
    # 1. 가상 환경 설정
    broker = MockBroker(initial_balance=100000.0)
    bot = TradingStateMachine(broker=broker, symbol="SOXL")
    
    # 2. 시나리오 데이터 강제 주입
    # IDLE -> RSI 28 -> RSI 32 (매수) -> 고점 돌파 -> 트레일링 스탑 1.5% 하락 (매도)
    data = [
        {"close": 10.0, "rsi": 40},
        {"close":  9.5, "rsi": 28}, # RSI 30 이하 진입
        {"close": 10.0, "rsi": 35}, # RSI 30 상향 돌파 -> 매수 발생 (가격 10.0, 5000주)
        {"close": 10.5, "rsi": 45}, # +5% 도달 (+4% 익절 50% 발동)
        {"close": 10.6, "rsi": 50}, # 고점 갱신
        {"close": 10.4, "rsi": 48}, # 고점(10.6) 대비 1.88% 하락 -> 트레일링 스탑 발동 (전량 매도)
        {"close": 10.0, "rsi": 45},
    ]
    df = pd.DataFrame(data)
    injector = MockDataInjector(df)
    
    # 3. 시뮬레이션 실행 (State Assertion)
    assert bot.state == BotState.IDLE
    
    stream = injector.stream()
    
    # Row 0
    price, rsi = next(stream)
    broker.set_current_price(price)
    bot.process_data(price, rsi)
    assert bot.state == BotState.IDLE
    
    # Row 1 (RSI 28)
    price, rsi = next(stream)
    broker.set_current_price(price)
    bot.process_data(price, rsi)
    assert bot.state == BotState.IDLE
    
    # Row 2 (RSI 35 -> 매수)
    price, rsi = next(stream)
    broker.set_current_price(price)
    bot.process_data(price, rsi)
    assert bot.state == BotState.HOLDING
    pos = broker.get_position("SOXL")
    assert pos["qty"] == 5000
    
    # Row 3 (가격 10.5 -> 5% 수익 -> 절반 익절 발동)
    price, rsi = next(stream)
    broker.set_current_price(price)
    bot.process_data(price, rsi)
    assert bot.state == BotState.HOLDING
    assert bot.partial_sold == True
    pos = broker.get_position("SOXL")
    assert pos["qty"] == 2500 # 50% 팔렸음
    
    # Row 4 (가격 10.6 -> 고점 갱신)
    price, rsi = next(stream)
    broker.set_current_price(price)
    bot.process_data(price, rsi)
    assert bot.high_water_mark == 10.6
    
    # Row 5 (가격 10.4 -> 트레일링 스탑 매도)
    price, rsi = next(stream)
    broker.set_current_price(price)
    bot.process_data(price, rsi)
    assert bot.state == BotState.IDLE
    pos = broker.get_position("SOXL")
    assert pos["qty"] == 0 # 전량 매도됨
    
    print("Test Harness & State Machine Assertion Passed Successfully!")
