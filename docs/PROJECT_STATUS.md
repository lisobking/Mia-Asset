# 🚀 Anti-Gravity Trading System - Project Status

## 📅 프로젝트 개요
*   **목적**: 초보자도 쉽게 다룰 수 있는 토스증권 스타일의 UX를 갖춘 24시간 자동매매 봇 시스템 구축
*   **아키텍처**:
    *   **Backend**: `FastAPI`, Python (비동기 처리)
    *   **Frontend**: HTML, CSS, Vanilla JS (`Pretendard` 폰트, 토스/로빈후드 스타일)
    *   **Database**: `MariaDB` (Docker Compose 연동)
    *   **Broker**: `Alpaca` 연동 완료, `한국투자증권(KIS)` 추가 예정

## ✅ 구현 완료 기능 (Completed)
1.  **코어 트레이딩 로직 (`skills/core_logic/state_machine.py`)**
    *   상태 머신(IDLE, BUY_PENDING, HOLDING, SELL_PENDING) 기반 거래
    *   RSI 15분봉 지표 기반의 조건부 진입/청산
2.  **API 클라이언트 추상화 (`skills/api_clients/`)**
    *   `BaseBroker` 인터페이스 설계
    *   `AlpacaClient` 구현 완료 (실거래/모의투자) 및 Fail-Safe 적용 (키 누락 시 Crash 방지)
3.  **UI/UX 디자인 전면 개편 (`dashboard/`)**
    *   초보자 친화적 디자인(밝은 톤, 카드 뷰, 가독성 높은 폰트)
    *   한글화 100% 적용 (`index.html`, `settings.html`)
    *   모바일 환경 대응 (반응형 웹)
4.  **환경 설정(API Key) 자동 연동**
    *   `settings.html` ➡️ `FastAPI 백엔드` ➡️ `.env 파일 저장 및 런타임 즉시 반영` 파이프라인 완비
5.  **웹 배포(Cloud) 환경 준비**
    *   `Dockerfile` 작성 완료
    *   `docker-compose.yml` (FastAPI + MariaDB) 구축 완료

## 🔄 다음 진행 예정 (Next Steps)
1.  **한국투자증권(KIS) API 클라이언트 개발**
    *   `skills/api_clients/kis_client.py` 구현
    *   발급받은 실전/모의투자 키와 계좌번호를 통한 잔고/포지션/주문 처리
2.  **MariaDB 연동 및 매매 일지 로깅**
    *   `SQLAlchemy` ORM 세팅
    *   체결 내역 및 일별 수익률 영구 저장 기능
3.  **위험 관리 및 자본금 조절 (`skills/risk_manager/`)**
    *   전체 자산의 일정 비율(%)만 진입하도록 포지션 사이징 로직 연결

---
*기록자: PM 에이전트*
*최종 업데이트: 2026-05-11*
