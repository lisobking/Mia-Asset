# 🎨 Anti-Gravity Dashboard Premium Design Guide v2.0
**Author:** Google Stitch AI (Lead UI/UX Designer)
**Status:** Approved & Implemented

본 문서는 투박한 기본 UI를 완벽하게 대체할 **"초현대적 다크 모드 금융 대시보드(Ultra-Modern Dark Financial Theme)"**의 확정된 디자인 시스템(Design System) 가이드라인입니다.

---

## 1. Design Concept: "Void & Neon (공허와 네온)"
복잡한 수치와 차트가 난무하는 트레이딩 환경에서, 시각적 노이즈를 극도로 억제하고 **사용자의 시선이 정확히 '수익'과 '위험'에 꽂히도록** 설계합니다.

- **Void (공간감)**: 극단적으로 어두운 네이비/블랙 배경을 사용하여 차트와 숫자가 공중에 떠 있는 듯한 느낌을 줍니다.
- **Neon (직관성)**: 매수/매도/수익률 등 중요 이벤트 발생 시 네온사인과 같은 발광(Glow) 효과를 통해 즉각적인 인지를 돕습니다.

---

## 2. Color System (색상 팔레트)

### 2.1 Backgrounds (배경)
- **Void Black (Main)**: `#06080F` (시각적 피로도가 가장 낮은 깊은 흑색)
- **Atmosphere Gradient**: `radial-gradient(circle at top left, #151C33, #06080F)` (단조로움을 없애는 은은한 방사형 빛)
- **Glass Panel (Surface)**: `rgba(255, 255, 255, 0.02)` (투명도 2%의 극세사 글래스 패널)

### 2.2 Accents (포인트 컬러)
- **Primary Accent (Cyan)**: `#00E5FF` (선택된 메뉴, 주요 수치)
- **Glow Shadow**: `rgba(0, 229, 255, 0.4)` (Cyan 색상 발광 효과)

### 2.3 Semantic Colors (상태 컬러)
- **Success / Buy (Neon Green)**: `#00FF88` (매수, 익절, 수익률 상승)
- **Danger / Sell (Neon Pink/Red)**: `#FF2E63` (매도, 손절, 수익률 하락)
- **Warning / Wait (Neon Gold)**: `#FFD700` (IDLE, 대기 상태)

---

## 3. Glassmorphism & Depth (글래스모피즘과 공간감)
패널(Card) 요소는 단순히 색으로 구분하지 않고 투명도와 블러링을 통해 깊이를 줍니다.

- **Backdrop Blur**: `blur(20px)` (뒷 배경을 강하게 뭉개어 패널 안의 텍스트 가독성을 높임)
- **Border Reflection**: `1px solid rgba(255, 255, 255, 0.05)` (유리 단면이 빛을 받는 듯한 미세한 테두리)
- **Hover Elevation**: 마우스 오버 시 `transform: translateY(-3px)`와 패널 그림자(`0 10px 30px rgba(0,0,0,0.5)`) 부여.

---

## 4. Typography (타이포그래피)
금융 데이터의 '숫자 가독성'과 '미적 아름다움'을 동시에 잡는 듀얼 폰트 시스템을 사용합니다.

- **Display & Numbers (수치/제목)**: `Outfit` (구글 폰트)
  - 특징: 동글동글하면서도 세련된 기하학적 형태. 큰 금액 표기(`$102,450.00`)나 퍼센티지 표기에 압도적인 미감을 제공.
- **Body & Labels (본문/라벨)**: `Inter` (구글 폰트)
  - 특징: 장평이 좁고 밀도가 높아 수많은 데이터를 한 화면에 욱여넣어도 깨끗하게 읽힘.

---

## 5. UI Elements & Micro-Interactions
- **RSI Indicator**: 투박한 프로그레스 바를 버리고, Cyan에서 Green으로 넘어가는 `Linear-Gradient` 바이트 스케일을 적용했습니다. 
- **State Badges**: `HOLDING` 등의 상태를 나타내는 뱃지는 배경에 10%의 투명도를 주고 텍스트와 보더 라인에 원색을 칠하여 명확히 구별되게 합니다.
- **Pulse Animation**: 시스템 온라인 상태를 알리는 좌측 하단 인디케이터는 1.5초 주기로 박동(`Pulsate`)하는 심장 박동 애니메이션을 넣었습니다.

---
**[Developer & QC 전달 사항]**
> *Stitch AI 코멘트: "해당 디자인 가이드는 현재 `dashboard/css/styles.css`에 100% 반영되어 렌더링 중입니다. 개발팀은 신규 컴포넌트 추가 시 반드시 위 Color System과 Typography를 준수하십시오."*
