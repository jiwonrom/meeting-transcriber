# Meeting Transcriber — Design System

## Direction
**"조용한 녹음실"** — 방음 부스처럼 어둡고 차분한 공간. 텍스트(전사 결과)가 주인공이고 UI는 뒤로 물러남. 빨간 녹음등이 유일한 강한 색.

## Feel
차분하고 전문적. 밀도보다 집중. 콘텐츠 우선.

## Depth Strategy
**보더 기반** — rgba 보더로 영역 구분. 그림자 없음. 사이드바와 본문은 같은 배경 + 미묘한 보더로 분리.

## Palette
- Background: `#1C1C1E` (방음벽의 짙은 다크)
- Elevated: `#2C2C2E` (카드/드롭다운)
- Control: `#3A3A3C` (입력 필드)
- Text primary: `#F5F5F7`
- Text secondary: `#98989D`
- Text tertiary: `#6E6E73`
- Accent: `#FF453A` (녹음등 빨강) — 유일한 강한 색
- Borders: `rgba(255,255,255,0.08)` (기본), `rgba(255,255,255,0.15)` (강조)

## Typography
- Body: System sans-serif, 14px
- Caption: 11px, tertiary color
- Heading: 17px, bold
- Title: 22px, bold
- Timestamps: Monospace (SF Mono/Menlo)

## Spacing
Base unit: 8px. Scale: 4/8/16/24/32.

## Border Radius
sm=6, md=10, lg=14, overlay=20.

## Signature
사이드바 선택 아이템에 왼쪽 빨간 보더 3px — 녹음등이 켜진 것처럼.

## Key Components
- **RecordButton**: 64px 원형, 빨간 원(대기) / 둥근 사각형(녹음 중) + 회색 링
- **RecordingListItem**: 제목(14px medium) + 날짜/길이(11px tertiary)
- **OverlayWidget**: 600x80 Spotlight 바, 하단 중앙, 둥근 코너(20px)
- **TranscriptViewer**: 3탭 (Original/Proofread/Summary)
- **ProgressBar**: 4px 높이, 빨간 청크 (레벨 미터)
