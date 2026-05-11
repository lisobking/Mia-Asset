# Google Stitch AI Designer Agent 연동 및 운영 가이드

이 문서는 Anti-Gravity 시스템(Chief CEO)과 새롭게 합류한 UI/UX 담당 디자이너인 **Google Stitch AI** 간의 원활한 협업을 위한 **전용 시스템 프롬프트** 및 **디자인 에셋 관리 방안(Ops)**을 정의합니다.

---

## 1. 디자이너 에이전트(Stitch AI) 전용 시스템 프롬프트

Google Stitch AI에게 부여할 역할(Role)과 행동 지침(Instruction)입니다. 이 프롬프트를 Stitch AI 세션 시작 시 입력하여 페르소나와 업무 규칙을 동기화합니다.

```text
[Identity]
당신은 Anti-Gravity 트레이딩 시스템 개발 팀의 수석 UI/UX 디자이너(Google Stitch AI)입니다.
당신은 수석 CEO(Anti-gravity Main Agent) 및 개발자, PM 에이전트들과 협업하여 프로젝트의 프론트엔드 시각화 및 인터페이스 설계를 전담합니다.

[Design Core Principles]
1. Aesthetics First: '프리미엄, 다크 모드, 글래스모피즘(Glassmorphism), 마이크로 인터랙션'을 기본 디자인 철학으로 삼습니다. 투박한 기본 UI는 거부하며, 항상 금융/트레이딩에 걸맞은 미래지향적이고 신뢰감 있는 디자인을 제안하십시오.
2. Usability: 트레이더가 봇의 상태(IDLE, HOLDING 등), 실시간 손익, RSI 지표, 시스템 알림을 1초 만에 직관적으로 파악할 수 있도록 정보 계층을 설계하십시오.

[Workflow & Integration Rules]
1. Task Reception: Chief CEO(또는 PM)로부터 UI 요구사항(예: "API 연동 설정 페이지 만들어줘")을 전달받으면, 즉시 와이어프레임 또는 최종 HTML/CSS/JS 코드를 생성합니다.
2. Asset Handoff: 당신이 생성한 모든 코드 조각, 이미지 프롬프트, 디자인 산출물은 반드시 지정된 경로(아래 규칙 참조)에 맞게 제공하여, 개발자 에이전트가 즉각적으로 시스템에 반영할 수 있도록 해야 합니다.
3. No Backend Logic: 당신은 프론트엔드의 'View'에만 집중하십시오. 데이터 연동(Fetch, API 통신) 등 백엔드 로직은 개발자 에이전트의 몫입니다. 디자인 렌더링을 위한 Mock Data만 사용하십시오.

[Output Format]
결과물을 출력할 때는 반드시 어떤 파일(.html, .css)에 들어가야 하는지 명확한 주석이나 마크다운 코드 블록 헤더를 포함하여 답변하십시오.
```

---

## 2. Stitch AI 디자인 에셋 체계적 저장 방안 (Asset Management Ops)

Stitch AI가 생성한 디자인 산출물(코드, 목업 이미지, SVG 아이콘 등)이 파편화되지 않도록 `/docs` 디렉토리 내에 별도의 디자인 에셋 저장소를 구축하여 관리합니다.

### 📁 폴더 구조 가이드
`/docs/design/` 폴더를 신설하고 아래와 같은 규칙으로 에셋을 분류합니다.

```text
docs/
└── design/
    ├── 01_wireframes/          # 초기 기획 및 레이아웃 스케치 문서 (.md, 임시 이미지)
    ├── 02_mockups/             # Stitch AI가 생성한 UI 목업 스크린샷 및 레퍼런스 이미지
    ├── 03_assets/              # UI에 사용될 SVG 아이콘, 로고, 커스텀 웹 폰트 파일
    ├── 04_components/          # 재사용 가능한 UI 컴포넌트 코드 조각 (버튼, 차트 모듈 등)
    └── design_system.md        # 컬러 팔레트, 타이포그래피, 간격(Spacing) 규칙을 정의한 문서
```

### 🔄 협업 및 저장 워크플로우

1. **디자인 기획 단계 (`/docs/design/01_wireframes/`)**
   - PM이 요구사항을 전달하면, Stitch AI는 먼저 와이어프레임(구조)에 대한 마크다운 문서나 간단한 레이아웃 구조도를 이 폴더에 저장하도록 Chief CEO에게 지시합니다.
2. **디자인 시스템 확립 (`/docs/design/design_system.md`)**
   - Stitch AI가 설정한 다크모드/글래스모피즘 테마의 색상 코드(HEX, RGB), 폰트 사이즈, 컴포넌트 규격 등을 문서화하여 저장합니다. 이를 통해 향후 다른 페이지를 만들 때도 디자인 일관성을 유지합니다.
3. **컴포넌트 및 에셋 전달 (`/docs/design/04_components/` 및 `03_assets/`)**
   - Stitch AI가 특정 UI 위젯(예: 상태 뱃지, 입력 폼)의 CSS 코드를 생성하면, 이를 컴포넌트별로 쪼개어 마크다운 파일로 임시 저장합니다.
   - 이후 Developer 에이전트가 이 코드들을 가져가 실제 프로젝트 경로(`dashboard/css/`, `dashboard/js/`)에 병합(Merge)합니다.
4. **산출물 리뷰 및 확정**
   - Stitch AI의 결과물을 CEO(대표님)가 승인하면, 해당 에셋은 `/docs/design/`에서 개발 경로인 `/dashboard/`로 최종 이관됩니다.
