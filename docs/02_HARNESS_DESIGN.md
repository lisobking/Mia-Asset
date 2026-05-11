# 테스트 하네스(Test Harness) 도입 및 아키텍처

실거래 시스템의 치명적인 버그를 사전에 방지하고 로직을 검증하기 위해, 개발자는 본 테스트 하네스를 통해 로직을 구축해야 합니다.

## 1. Mock Data Injector (데이터 모의 주입기)
- **목적**: 실시간 시세를 무한정 기다리며 테스트할 수 없으므로, 과거 특정 시점의 데이터(예: 급락장, 횡보장)를 강제 주입.
- **방식**: CSV 형태의 과거 분봉 데이터를 읽어 실시간 Websocket 스트림처럼 발생시키는 Event Generator 클래스 구현.

## 2. Paper Brokerage Adapter (가상 브로커리지)
- **목적**: 실제 증권사 API 주문 오류(무한 루프에 의한 반복 매수 등)를 방지.
- **방식**: 증권사 API를 감싸는 인터페이스(Interface)를 두고, 테스트 시에는 `MockBroker` 객체를 주입하여 잔고 변화, 수수료, 슬리피지(Slippage)를 내부 메모리에서만 시뮬레이션함.

## 3. State Machine Assertion (상태 검증기)
- **목적**: 매매 시스템의 상태(State)가 정상적으로 전이되는지 검증.
- **상태 정의**: `IDLE` -> `BUY_PENDING` -> `HOLDING` -> `SELL_PENDING` -> `IDLE`
- **단위 테스트(Unit Test)**: 주문이 체결되지 않은 상태에서 다음 로직이 실행되는지, 손절 라인을 터치했을 때 즉각 `SELL_PENDING`으로 넘어가는지 PyTest 기반으로 강제 검증.
