# Skills (재사용 가능한 핵심 모듈) 관리

본 디렉토리는 향후 TQQQ, BULZ 등 다른 ETF나 코인 자동매매 등 **추가 프로젝트**에 즉시 재사용할 수 있도록 기능별로 모듈화(Skill)하여 관리합니다.
각 스킬은 상호 의존성을 최소화하여 레고 블록처럼 조립 가능해야 합니다.

## 디렉토리 구조 및 역할

- `api_clients/`
  - 증권사 통신 모듈. (예: `alpaca_client.py`, `koreainvest_client.py`)
  - 모든 클라이언트는 공통 인터페이스(`BaseBroker`)를 상속받아, 증권사가 바뀌어도 메인 로직은 수정할 필요 없게 구축.

- `indicators/`
  - 기술적 지표 계산 전용 모듈. Pandas/TA-Lib 기반.
  - 외부 의존성 없이 순수 OHLCV 데이터 프레임만 받아 값을 반환하는 순수 함수(Pure Function)로 구성.
  - 예: `calculate_rsi()`, `calculate_moving_average()`

- `risk_manager/`
  - 매매의 안전장치를 담당하는 뇌.
  - 역할: 목표 수량 계산(Position Sizing), 현재 가격에 따른 트레일링 스탑 지점 계산, 일일 최대 손실액 도달 시 킬 스위치(Kill Switch) 작동 로직.
