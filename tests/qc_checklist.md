# Quality Control (QC) Checklist
**Author:** QC Agent

본 체크리스트는 프론트엔드 대시보드와 백엔드 간의 데이터 연동 시 발생할 수 있는 품질 문제를 사전에 차단하기 위해 작성되었습니다.

## 1. Data Loading & Latency (데이터 로딩 지연)
- [ ] **초기 로딩 속도**: `index.html` 진입 시 초기 데이터 바인딩까지 걸리는 시간이 1초 이내인가?
- [ ] **API 응답 시간**: `/api/status` 호출 시 응답 지연(Latency)이 200ms를 초과하지 않는가?
- [ ] **비동기 처리(Non-blocking)**: 백엔드에서 Alpaca API 시세를 당겨올 때(Network I/O) Uvicorn/FastAPI 메인 스레드가 블로킹되어 프론트엔드 응답이 지연되지 않는가? (asyncio 및 Task 활용 검증 완료)
- [ ] **에러 핸들링**: Alpaca API Rate Limit에 도달하거나 인터넷이 끊겼을 때 대시보드가 멈추지 않고 적절한 폴백(또는 재시도) 로직을 수행하는가?

## 2. Chart & Rendering (차트 및 UI 렌더링)
- [ ] **RSI 게이지 바 오류**: RSI가 0 미만 혹은 100 초과로 수신될 때 CSS width 렌더링이 깨지지 않는가? (`min-width`, `max-width` 캡 적용 여부)
- [ ] **모바일 레이아웃 깨짐**: 300px 이하의 초소형 디스플레이 기기에서 폰트나 숫자가 패널 밖으로 튀어나가지 않는가?
- [ ] **데이터 튀는 현상 (Flickering)**: 2초 단위 Polling 시, DOM 업데이트로 인해 화면이 번쩍거리는 현상(Flicker)이 발생하지 않는가? (Virtual DOM이 없는 Vanilla JS이므로 `innerText` 교체 시 성능 및 시각적 부작용 확인)
- [ ] **SVG 차트 렌더링**: 그라데이션 SVG 차트가 브라우저 해상도 변경 시(`resize` 이벤트) 비율(Aspect Ratio)이 정상적으로 유지되는가?

## 3. Data Integrity (데이터 정합성)
- [ ] **잔고 동기화**: Broker API에서 가져온 Portfolio Value가 대시보드의 `$ Balance`에 소수점 2자리로 정확히 표기되는가?
- [ ] **상태 전이 타이밍**: 백엔드 봇의 State(예: BUY_PENDING)가 프론트엔드에 노출될 때 딜레이(최대 2초 Polling)로 인해 유저의 인지와 실제 매매 간 괴리가 크지 않은가?
