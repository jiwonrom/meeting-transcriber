# Meeting Transcriber — Multi-Agentic Self-Socratic Review

**Review Target**: 전체 설계 협의 내용 (UI, 엔진, 오디오, 저장, AI, 폴더, 테스트, MCP, 배포, 스코프)
**Agents**: 6명 | **Alternation Rounds**: 3회 이상
**Acceptance Threshold**: Round 1-2 무조건 진행, Round 3+ 평균 8.5/10 이상 시 종료

---

## Agent Roster

| ID | Agent | Emoji | 전문 영역 |
|----|-------|-------|-----------|
| A1 | **System Architect** | 🏗️ | 아키텍처, 모듈 의존성, 확장성, 데이터 흐름 |
| A2 | **Audio/ML Engineer** | 🎧 | Whisper, pyannote, 실시간 오디오 파이프라인, Apple Silicon 최적화 |
| A3 | **UX Designer** | 🎨 | 오버레이 UX, 사이드바, 접근성, macOS HIG 준수 |
| A4 | **Pragmatist** | ⚡ | 실현 가능성, 개발 공수, v1 스코프 적정성, 리스크 |
| A5 | **DX Advocate** | 🧑‍💻 | Claude Code 구조, CLAUDE.md, Cowork 핸드오버, 테스트 |
| A6 | **Security/Privacy** | 🔒 | 로컬 데이터 보호, API 키 관리, 녹음 동의, 개인정보 |

---

## ROUND 1: 구조적 의문 제기

### 1.1 🏗️ System Architect → 전체 아키텍처

**Q: PyQt6 단일 스택에서 whisper.cpp(C++) + pyannote(PyTorch) + Gemini API가 공존하는데, 메인 스레드 블로킹 전략이 부재하다.**

> whisper.cpp 추론은 CPU/ANE를 수초간 점유한다. PyQt6의 이벤트 루프가 블로킹되면 오버레이 캡션이 멈추고, 사이드바가 응답 불능이 된다. 현재 설계에는 스레딩/프로세싱 모델이 명시되지 않았다.

**제안**: `QThread` 또는 `multiprocessing`으로 분리 필수. 구체적으로:
- **Audio Capture Thread**: 마이크 입력 → 버퍼 관리
- **Transcription Worker (별도 프로세스)**: whisper.cpp 추론 (GIL 회피 위해 subprocess 권장)
- **AI Worker Thread**: Gemini API 비동기 호출
- **Main Thread**: UI 렌더링 전용

**심각도**: 🔴 Critical — 이것 없이는 실시간 캡션 자체가 불가능

---

### 1.2 🎧 Audio/ML Engineer → Whisper 모델 전략

**Q: M1 Max에서 medium 모델을 "실시간 기본값"으로 확정했는데, 다국어(EN/KO/ZH/JA) 동시 감지 시 성능 드롭을 고려했는가?**

> 벤치마크 데이터(Voicci)는 단일 화자/단일 언어 기준이다. 한국어↔영어 코드 스위칭, 중국어 성조 처리, 일본어 한자/히라가나 혼합 시 medium 모델의 RTF가 0.3x → 0.5x 이상으로 올라갈 수 있다. 또한 whisper.cpp의 `--language auto` 모드는 30초 청크마다 언어를 재감지하므로, 빠른 코드 스위칭에서 오탐이 높다.

**제안**:
- 실시간 캡션 기본값을 `small`로 하향 조정하고, medium은 "고성능 모드"로 분리
- `--language auto` 대신 사용자가 사전에 "주 사용 언어"를 설정하고, 30초마다 재감지하는 방식으로 변경
- 벤치마크를 4개 언어 샘플로 직접 측정하는 테스트 케이스를 v1에 포함

**심각도**: 🟡 High — 핵심 기능(다국어)의 품질 직결

---

### 1.3 🎨 UX Designer → 오버레이 캡션

**Q: "드래그 가능한 플로팅 캡션"이 macOS 접근성 가이드라인과 충돌할 수 있다.**

> macOS에서 `Qt.WindowStaysOnTopHint + Qt.FramelessWindowHint`는 기술적으로 가능하지만:
> 1. VoiceOver(스크린 리더)가 플로팅 윈도우를 올바르게 읽지 못할 수 있음
> 2. 풀스크린 앱 위에서 오버레이가 표시되지 않을 수 있음 (macOS Space 제약)
> 3. 캡션 위치를 사용자가 매번 재설정해야 하는 UX 마찰

**제안**:
- 오버레이 위치를 `~/.meeting_transcriber/settings.json`에 저장하여 세션 간 유지
- 풀스크린 대응: `Qt.WindowDoesNotAcceptFocus` + `NSWindow.collectionBehavior` 설정
- 캡션 줄 수 제한 (기본 2줄, 최대 5줄) — 무한 스크롤 방지
- 폰트 크기/배경 투명도 조절 슬라이더

**심각도**: 🟡 High — UX 핵심 기능이므로 세부 스펙 필요

---

### 1.4 ⚡ Pragmatist → v1 스코프 과부하

**Q: v1에 화자 분리(pyannote)까지 포함하면 개발 공수가 과도하지 않은가?**

> 현재 v1 스코프: 실시간 transcription + 오버레이 + 마이크 녹음 + 파일 임포트 + 사이드바 폴더 관리 + AI 요약/번역/키워드 + 자동 파일명 + 화자 분리 + 디자인 토큰 + 메뉴바 상주 + 글로벌 단축키 + 캡션 커스터마이즈 + 내용 교열. 이것은 1인 개발 기준 3-4개월 분량이다. pyannote 통합만으로도 Whisper 세그먼트 정렬, HuggingFace 인증, GPU/CPU 폴백 등 복잡도가 급증한다.

**제안**: v1을 두 단계로 분할
- **v1.0 (MVP)**: 실시간 transcription + 오버레이 + 녹음 + 파일 임포트 + 사이드바 + 기본 export
- **v1.5**: AI 기능 (요약/번역/키워드) + 화자 분리 + 자동 파일명 + 교열
- **v2.0**: 시스템 오디오, 자동 감지, BYOK, 템플릿 등

**심각도**: 🟡 High — 스코프 과부하는 프로젝트 실패의 1순위 원인

---

### 1.5 🧑‍💻 DX Advocate → Claude Code 구조

**Q: CLAUDE.md가 아직 정의되지 않았고, 에이전트 5개 구성이 과다하다.**

> Claude Code 베스트 프랙티스에서 CLAUDE.md는 < 60줄, 핵심 MUST/MUST NOT만 포함하라고 권장한다. 에이전트 5개(ui/audio/ai/test/bug-fix)는 컨텍스트 전환 비용이 크고, Cowork 사용자가 어떤 에이전트를 써야 할지 혼란을 겪을 수 있다.

**제안**:
- CLAUDE.md: 40줄 이하, Progressive Disclosure 원칙
- 에이전트를 3개로 축소: `ui-agent`, `core-agent` (audio+ai), `review-agent` (test+bug-fix)
- 상세 규칙은 `docs/` 하위로 분리하여 `@docs/architecture.md` 식으로 필요 시 로드
- `.claude/commands/`에 `/socratic-review`, `/run-tests`, `/build-dmg` 커맨드 추가

**심각도**: 🟠 Medium — DX 효율성 직결

---

### 1.6 🔒 Security/Privacy → 녹음 동의 & 데이터 보호

**Q: 녹음 앱의 법적 요구사항(동의)이 PRD에 전혀 반영되지 않았다.**

> 한국(통신비밀보호법), 미국(연방/주별 2-party consent 법), 일본(개인정보보호법) 등 녹음 관련 법규가 다르다. Notion, Zoom, Tiro 모두 녹음 시작 시 명시적 동의 메커니즘을 구현했다. 또한:
> 1. `~/.meeting_transcriber/`에 오디오 파일이 평문 저장됨 — 디스크 암호화 미적용 시 유출 위험
> 2. Gemini API 호출 시 transcript 전문이 Google 서버로 전송됨 — 민감 회의 내용 유출
> 3. HuggingFace 토큰이 설정 파일에 평문 저장될 수 있음

**제안**:
- 녹음 시작 시 동의 안내 UI (Notion 참조: "모든 참여자의 동의를 확인하세요")
- 오디오 파일 보관 정책: 전사 완료 후 원본 오디오 자동 삭제 옵션
- API 키 저장: macOS Keychain 활용 (`keyring` 라이브러리)
- Gemini API 전송 전 사용자 확인 또는 로컬 전용 모드 옵션
- 설정에 "민감 모드" 토글: AI 기능 비활성화, 모든 것 로컬 처리

**심각도**: 🔴 Critical — 법적 리스크 + 사용자 신뢰

---

## ROUND 1 점수 (10점 만점)

| 평가 항목 | A1 | A2 | A3 | A4 | A5 | A6 | 평균 |
|-----------|----|----|----|----|----|----|------|
| 아키텍처 완성도 | 4 | 5 | 6 | 5 | 4 | 5 | **4.8** |
| 기술 실현 가능성 | 5 | 4 | 6 | 4 | 5 | 5 | **4.8** |
| UX 품질 | 6 | 5 | 4 | 5 | 5 | 5 | **5.0** |
| 스코프 적정성 | 5 | 5 | 5 | 3 | 4 | 5 | **4.5** |
| 보안/개인정보 | 3 | 4 | 4 | 4 | 4 | 3 | **3.7** |
| **라운드 평균** | | | | | | | **4.6** |

**판정: ITERATION 1 — REQUIRES SUBSTANTIAL IMPROVEMENT** ❌

---

## ROUND 2: 수정 반영 및 재비판

### 2.0 Round 1 피드백 반영 사항

Round 1의 6개 이슈를 다음과 같이 반영:

| # | 이슈 | 조치 |
|---|------|------|
| 1.1 | 스레딩 모델 부재 | ✅ 4-레이어 스레딩 아키텍처 명시 |
| 1.2 | 다국어 성능 드롭 | ✅ 기본값 small, 고성능 모드 medium, 벤치마크 테스트 케이스 추가 |
| 1.3 | 오버레이 세부 스펙 | ✅ 위치 저장, 풀스크린 대응, 줄 수 제한 명시 |
| 1.4 | v1 스코프 과부하 | ✅ v1.0/v1.5/v2.0 3단계 분할 |
| 1.5 | 에이전트 과다 | ✅ 3개로 축소, CLAUDE.md 40줄 제한 |
| 1.6 | 녹음 동의 미반영 | ✅ 동의 UI, 오디오 삭제 정책, Keychain 저장 명시 |

---

### 2.1 🎧 Audio/ML Engineer → pyannote + Whisper 정렬 복잡도

**Q: Round 1에서 화자 분리를 v1.5로 미뤘지만, pyannote community-1의 exclusive_speaker_diarization과 whisper.cpp 세그먼트 정렬 방식이 구체적이지 않다. v1.5에서 이걸 어떻게 구현할 것인가?**

> pyannote는 오디오 전체를 받아서 화자별 타임스탬프를 반환하고, whisper.cpp는 별도로 텍스트+타임스탬프를 반환한다. 두 결과를 정렬(alignment)하려면 temporal intersection 알고리즘이 필요한데, 이는 whisper 세그먼트 경계와 pyannote 화자 전환 경계가 정확히 일치하지 않는 문제가 있다. WhisperX는 이걸 word-level alignment로 해결했다.

**제안**:
- v1.5 구현 시 WhisperX의 정렬 알고리즘을 참고하되, 자체 구현
- `core/alignment.py` 모듈을 미리 인터페이스만 정의 (v1.0에서 stub)
- 정렬 정확도 테스트: 샘플 오디오 3개(2/3/5명 화자)로 DER 측정

**심각도**: 🟠 Medium — v1.5 구현 복잡도 사전 파악 필요

---

### 2.2 🏗️ System Architect → 디자인 토큰과 PyQt6 QSS의 간극

**Q: Design Systems MCP에서 가져온 WCAG/디자인 원칙을 PyQt6 QSS로 변환하는 파이프라인이 없다. 디자인 토큰 JSON → QSS 자동 생성이 실제로 가능한가?**

> PyQt6의 QSS(Qt Style Sheets)는 CSS의 서브셋이지만, CSS 변수(`var(--color)`)를 지원하지 않는다. 즉, 디자인 토큰 JSON을 직접 QSS에 바인딩하는 표준 메커니즘이 없다. 수동으로 QSS 문자열을 생성해야 한다.

**제안**:
- `ui/theme.py` 모듈에 `ThemeEngine` 클래스 구현
- `design_tokens.json` → Python dict 로드 → QSS 문자열 f-string 생성
- Dark/Light 모드: 토큰 파일을 2벌 유지 (`tokens_light.json`, `tokens_dark.json`)
- macOS 시스템 다크 모드 감지: `QApplication.palette()` 또는 `NSAppearance` 바인딩
- 이 구조는 단순하고, MCP 의존 없이도 동작. MCP는 개발 시 참고용으로만 활용

**심각도**: 🟠 Medium — 구현 경로 명확화 필요

---

### 2.3 ⚡ Pragmatist → Gemini 단일 스택의 리스크

**Q: 모든 AI 기능을 Gemini 3.0 Flash 단일 프로바이더에 의존하는 것은 단일 장애점(SPOF)이다.**

> Gemini API 장애, 가격 변동, rate limit, 또는 특정 언어(한국어) 품질 이슈 발생 시 AI 기능 전체가 마비된다. 또한 Gemini Flash의 한국어 요약 품질이 Claude 대비 어떤 수준인지 벤치마크가 없다.

**제안**:
- AI 프로바이더 추상화 레이어는 유지 (이미 계획됨)
- v1.0에서는 Gemini Flash 단일이되, `ai/providers/` 구조로 확장 가능하게
- 설정 파일에 `fallback_provider` 옵션 (v1.5에서 Claude/OpenAI 추가)
- 한국어 요약 품질 비교 테스트를 v1.0 QA에 포함 (Gemini vs 수동 요약)

**심각도**: 🟠 Medium — 리스크 인지 + 완화 전략 필요

---

### 2.4 🧑‍💻 DX Advocate → 파일 임포트 파이프라인 복잡도

**Q: "영상 파일에서 오디오 추출"이 v1.0에 포함되어 있는데, ffmpeg 의존성 관리와 지원 포맷 범위가 정의되지 않았다.**

> 영상 파일(mp4, mov, avi, mkv, webm 등)에서 오디오를 추출하려면 ffmpeg가 필수다. ffmpeg는 macOS에 기본 설치되어 있지 않으며, Homebrew 설치를 요구하면 비개발자 사용자의 진입 장벽이 된다. DMG 패키징 시 ffmpeg 바이너리를 번들에 포함할지 결정해야 한다.

**제안**:
- ffmpeg-python 대신 `ffmpeg` static binary를 앱 번들에 포함 (약 80MB 추가)
- 또는 PyAV (ffmpeg의 Python 바인딩, pip install 가능)를 사용
- 지원 포맷을 명시: 입력(mp4, mov, m4a, mp3, wav, webm, avi), 출력(16kHz mono WAV)
- 비지원 포맷은 명확한 에러 메시지 + 변환 안내

**심각도**: 🟠 Medium — 배포 파이프라인에 직접 영향

---

### 2.5 🎨 UX Designer → 사이드바 폴더 관리의 UX 디테일

**Q: "실제 파일시스템 폴더에 1:1 대응"이라고 했는데, 파일 이동/삭제 시 충돌 시나리오가 고려되지 않았다.**

> 사용자가 Finder에서 직접 폴더를 이동/삭제하면 앱 사이드바와 동기화가 깨진다. 또한:
> 1. 같은 이름의 폴더가 이미 존재할 때 rename 동작
> 2. transcript.json이 손상되었을 때 복구 방안
> 3. 대량 파일(100개+) 시 사이드바 로딩 성능
> 4. 드래그&드롭으로 폴더 간 이동 지원 여부

**제안**:
- `FileSystemWatcher` (QFileSystemWatcher)로 외부 변경 실시간 감지
- workspace.json에 파일 해시 저장 → 무결성 검증
- 충돌 시 사용자에게 "외부에서 변경됨" 알림 + 새로고침 옵션
- 사이드바는 가상화 (QTreeView + lazy loading) — 100개+ 폴더에서도 부드럽게
- v1.0에서는 drag&drop 폴더 이동은 제외 (rename/delete만)

**심각도**: 🟡 High — 데이터 무결성 관련

---

### 2.6 🔒 Security/Privacy → Gemini API 전송 데이터 범위

**Q: Round 1에서 "민감 모드"를 제안했지만, 기본 모드에서 Gemini에 전송되는 데이터의 정확한 범위가 정의되지 않았다.**

> 요약/번역/키워드 추출 시 transcript 전문이 Gemini에 전송된다. 1시간 회의의 transcript는 약 10,000-15,000 토큰이다. 이 데이터에 비밀 정보(인사, 재무, 계약 조건)가 포함될 수 있다. Google의 Gemini API 데이터 정책(학습에 사용되지 않음)을 확인해도, 전송 자체가 리스크다.

**제안**:
- AI 기능 호출 전 "이 transcript를 Gemini API로 전송합니다" 확인 다이얼로그 (첫 사용 시)
- 설정에서 "항상 묻기 / 항상 허용 / 항상 차단" 3단계
- transcript 전송 시 개인 식별 정보(이름, 전화번호 등) 자동 마스킹 옵션 (v1.5)
- API 호출 로그를 `~/.meeting_transcriber/api_log.json`에 기록 (어떤 데이터가 언제 전송되었는지)

**심각도**: 🟡 High — 사용자 신뢰의 핵심

---

## ROUND 2 점수

| 평가 항목 | A1 | A2 | A3 | A4 | A5 | A6 | 평균 |
|-----------|----|----|----|----|----|----|------|
| 아키텍처 완성도 | 7 | 7 | 7 | 7 | 7 | 7 | **7.0** |
| 기술 실현 가능성 | 7 | 6 | 7 | 6 | 6 | 7 | **6.5** |
| UX 품질 | 7 | 7 | 7 | 7 | 7 | 7 | **7.0** |
| 스코프 적정성 | 7 | 7 | 7 | 7 | 7 | 7 | **7.0** |
| 보안/개인정보 | 7 | 7 | 7 | 7 | 7 | 6 | **6.8** |
| **라운드 평균** | | | | | | | **6.9** |

**판정: ITERATION 2 — SUBSTANTIAL PROGRESS BUT NOT YET READY** ❌

**개선**: Round 1 (4.6) → Round 2 (6.9) = +2.3점. 아키텍처와 스코프가 크게 개선되었으나, 기술 실현 가능성과 보안 세부사항에서 추가 보완 필요.

---

## ROUND 3: 최종 보완 및 합의 도출

### 3.0 Round 2 피드백 반영 사항

| # | 이슈 | 조치 |
|---|------|------|
| 2.1 | pyannote 정렬 복잡도 | ✅ alignment.py 인터페이스 사전 정의, WhisperX 참조, v1.5 스코프 명확화 |
| 2.2 | QSS 토큰 변환 | ✅ ThemeEngine 클래스, JSON→QSS 생성 파이프라인, Dark/Light 2벌 |
| 2.3 | Gemini SPOF | ✅ 프로바이더 추상화 유지, fallback 구조, 한국어 품질 테스트 |
| 2.4 | ffmpeg 의존성 | ✅ PyAV 사용, 지원 포맷 명시, 앱 번들 포함 전략 |
| 2.5 | 사이드바 동기화 | ✅ QFileSystemWatcher, workspace.json 무결성, lazy loading |
| 2.6 | API 전송 범위 | ✅ 확인 다이얼로그, 3단계 설정, API 로그 기록 |

---

### 3.1 🏗️ System Architect → 최종 모듈 의존성 검증

**Q: 4-레이어 스레딩 + 3단계 스코프 + 프로바이더 추상화를 결합하면, 모듈 간 의존 방향이 명확한가?**

**검증 결과** — 의존 방향 정의:

```
ui/ → core/ (단방향, UI가 core를 호출)
ui/ → ai/ (단방향, UI가 AI 결과를 표시)
core/ → (외부: whisper.cpp, pyav)
ai/ → (외부: Gemini API)
storage/ → (외부: filesystem)
core/ ↛ ui/ (역방향 금지 — Signal/Slot으로만 통신)
ai/ ↛ ui/ (역방향 금지 — Signal/Slot으로만 통신)
```

**남은 이슈**: `storage/`와 `ai/`의 관계 — AI가 파일명을 자동 생성할 때 storage를 직접 호출하는가, 아니면 UI를 거치는가?

**해결**: `ai/` → `storage/` 직접 호출 허용 (파일명 생성 + 메타데이터 업데이트). 단, `storage/`는 ai에 의존하지 않음 (단방향).

**상태**: ✅ 해결됨

---

### 3.2 🎧 Audio/ML Engineer → 실시간 캡션 지연 시간 목표값

**Q: 실시간 캡션의 허용 지연 시간(latency)이 정의되지 않았다. 사용자가 말한 후 몇 초 이내에 캡션이 표시되어야 하는가?**

**정의**:
- **목표**: 발화 종료 후 2초 이내 캡션 표시 (Zoom CC 수준)
- **허용 최대**: 3초 (그 이상은 "실시간"으로 느껴지지 않음)
- **측정 방법**: 오디오 입력 타임스탬프 ~ 캡션 UI 렌더링 타임스탬프 차이

**구현 영향**:
- whisper.cpp의 청크 크기를 3초로 설정 (5초 기본값 대비 더 빈번한 추론)
- 3초 청크 + 추론 시간(~0.5초 small 모델) = 약 3.5초 → 목표 초과
- **해결**: 2초 청크 + VAD(Voice Activity Detection)로 무음 구간은 건너뛰기

**상태**: ✅ 목표값 정의 완료, 구현 전략 수립

---

### 3.3 ⚡ Pragmatist → v1.0 MVP 최종 범위 확인

**Q: 3단계 분할 후 v1.0의 범위가 여전히 적절한가? 최소 기능 제품(MVP)의 정의를 재확인한다.**

**v1.0 MVP 최종 체크리스트** (각 항목의 필수/선택 구분):

| 기능 | 필수/선택 | 근거 |
|------|----------|------|
| 실시간 transcription (small 모델) | 필수 | 핵심 가치 |
| 드래그 가능 오버레이 캡션 | 필수 | 핵심 가치 |
| 마이크 녹음 | 필수 | 기본 입력 |
| 오디오 파일 임포트 | 필수 | 요구사항 |
| 영상에서 오디오 추출 | 선택→**v1.5로 이동** | ffmpeg 복잡도, MVP에서 제외 가능 |
| 사이드바 폴더 관리 | 필수 | 핵심 UX |
| transcript.json 저장 | 필수 | 데이터 기반 |
| MD/TXT export | 필수 | 기본 출력 |
| 언어 자동 감지 | 필수 | 다국어 핵심 |
| 메뉴바 트레이 상주 | 필수 | macOS UX |
| 글로벌 단축키 | 필수 | 빠른 접근 |
| 캡션 커스터마이즈 | 선택→필수 | 접근성 요구 |
| Dark/Light 모드 | 필수 | macOS 기본 기대 |
| 녹음 동의 안내 | 필수 | 법적 요구 |

**결론**: 영상 오디오 추출을 v1.5로 이동하여 v1.0 공수를 절감. 나머지는 유지.

**상태**: ✅ 스코프 최적화 완료

---

### 3.4 🧑‍💻 DX Advocate → CLAUDE.md + 커맨드 구조 최종안

**Q: Claude Code 핸드오프 패키지의 최종 구조가 실제 워크플로우에서 동작하는가?**

**최종 구조**:

```
meeting-transcriber/
├── CLAUDE.md                          # ≤40줄, MUST/MUST NOT만
├── PRD.md                             # 전체 요구사항 (이 리뷰 결과 반영)
├── .claude/
│   ├── settings.json
│   ├── agents/
│   │   ├── ui-agent.md                # PyQt6 UI 전담
│   │   ├── core-agent.md              # audio + ai + storage 전담
│   │   └── review-agent.md            # test + bug-fix + socratic review
│   └── commands/
│       ├── socratic-review.md         # /socratic-review — Phase 전환 시 실행
│       ├── run-tests.md               # /run-tests — pytest 전체 실행
│       └── build-dmg.md               # /build-dmg — 배포 빌드
├── docs/
│   ├── architecture.md                # 모듈 구조, 의존 방향, 데이터 흐름
│   ├── code-rules.md                  # PEP8 + 프로젝트 특화 규칙
│   └── design-tokens.md              # 디자인 토큰 스펙
├── src/meeting_transcriber/
│   ├── __init__.py
│   ├── app.py                         # 메인 엔트리포인트
│   ├── ui/                            # PyQt6 위젯
│   │   ├── main_window.py
│   │   ├── overlay.py                 # 플로팅 캡션
│   │   ├── sidebar.py                 # 폴더 트리
│   │   └── theme.py                   # ThemeEngine (JSON→QSS)
│   ├── core/
│   │   ├── audio_capture.py           # 마이크 입력
│   │   ├── transcriber.py             # whisper.cpp 래퍼
│   │   ├── file_importer.py           # 오디오 파일 임포트
│   │   └── alignment.py               # 화자-텍스트 정렬 (v1.5 stub)
│   ├── ai/
│   │   ├── provider_base.py           # ABC 추상화
│   │   ├── gemini_provider.py         # Gemini 3.0 Flash
│   │   └── tasks.py                   # 요약, 번역, 키워드 등
│   ├── storage/
│   │   ├── workspace.py               # 폴더 구조 관리
│   │   ├── transcript_store.py        # JSON 저장/로드
│   │   └── exporter.py                # MD/TXT export
│   └── utils/
│       ├── config.py                  # 설정 관리
│       ├── keychain.py                # macOS Keychain 연동
│       └── constants.py
├── tests/
│   ├── conftest.py                    # 공통 fixture
│   ├── fixtures/                      # 샘플 오디오 파일
│   ├── test_transcriber.py
│   ├── test_sidebar.py
│   └── test_ai_provider.py
├── design/
│   ├── tokens_light.json
│   └── tokens_dark.json
├── pyproject.toml
├── Makefile                           # setup, test, build-dmg, lint
└── README.md
```

**CLAUDE.md 초안** (38줄):

```markdown
# Meeting Transcriber

macOS 데스크탑 앱. 실시간 음성 전사 + AI 요약. PyQt6 + whisper.cpp + Gemini API.

## Commands
- `make setup` — 의존성 설치 + whisper 모델 다운로드
- `make test` — pytest 전체 실행
- `make lint` — ruff + mypy
- `make build` — py2app → DMG 생성

## Architecture
- `@docs/architecture.md` 참조
- 의존 방향: ui → core, ui → ai, ai → storage (단방향만 허용)
- core ↛ ui, ai ↛ ui (Signal/Slot으로만 역방향 통신)

## MUST
- PEP8 준수, ruff로 자동 포맷
- 모든 public 함수에 type hint + docstring
- 새 기능 추가 시 테스트 필수 (pytest)
- whisper.cpp 추론은 반드시 별도 프로세스에서 실행 (메인 스레드 블로킹 금지)
- API 키는 macOS Keychain 저장 (평문 파일 금지)

## MUST NOT
- ui/ 모듈에서 외부 API 직접 호출 금지
- 메인 스레드에서 blocking I/O 금지
- transcript.json 스키마 임의 변경 금지
- 사용자 동의 없이 오디오 녹음 시작 금지

## Testing
- `pytest tests/ -x --tb=short` (단일 실패 시 중단)
- `pytest tests/test_transcriber.py -k "test_korean"` (한국어 테스트)
- fixtures/에 4개 언어 샘플 오디오 (각 30초)

## Phase
- 현재: v1.0 MVP
- `@PRD.md`에서 v1.0/v1.5/v2.0 스코프 확인
```

**상태**: ✅ 구조 확정

---

### 3.5 🎨 UX Designer → 최종 UI 플로우 검증

**Q: 사용자의 핵심 여정(Job-to-be-done)이 3클릭 이내에 완료되는가?**

**검증 — 핵심 시나리오 3가지**:

**시나리오 1: 실시간 미팅 전사**
1. 메뉴바 아이콘 클릭 (또는 글로벌 단축키)
2. "녹음 시작" 버튼 → 동의 안내 → 시작
3. 오버레이 캡션 자동 표시
→ **2클릭** ✅

**시나리오 2: 오디오 파일 전사**
1. 앱 열기 → 사이드바의 "파일 임포트" 버튼
2. 파일 선택 다이얼로그 → 파일 선택
3. 전사 자동 시작 → 완료 후 사이드바에 표시
→ **3클릭** ✅

**시나리오 3: 전사 결과 AI 요약**
1. 사이드바에서 전사 파일 클릭
2. 메인 영역 상단 "AI 요약" 버튼 클릭
3. (Gemini 전송 동의 후) 요약 생성 → 인라인 표시
→ **2-3클릭** ✅

**남은 UX 이슈**:
- 첫 실행 경험(First Run Experience): Whisper 모델 다운로드 중 진행률 표시 필요
- 언어 설정 온보딩: "주 사용 언어" 선택 화면
- 해결: 첫 실행 시 3단계 온보딩 (언어 선택 → 모델 다운로드 → 마이크 권한)

**상태**: ✅ UX 플로우 검증 완료

---

### 3.6 🔒 Security/Privacy → 최종 보안 체크리스트

**Q: v1.0 출시 전 보안 체크리스트가 완비되었는가?**

| 항목 | 상태 | 구현 방법 |
|------|------|----------|
| API 키 안전 저장 | ✅ | macOS Keychain (`keyring` 라이브러리) |
| 녹음 동의 | ✅ | 첫 녹음 시 다이얼로그 |
| 오디오 파일 보관 정책 | ✅ | 설정: 전사 후 삭제 / 보관 / 묻기 |
| Gemini 전송 알림 | ✅ | 첫 사용 시 동의 + 설정 3단계 |
| API 호출 로그 | ✅ | api_log.json 자동 기록 |
| .env 유출 방지 | ✅ | .gitignore + pre-commit hook |
| transcript 암호화 | 🔲 v1.5 | FileVault 의존, 자체 암호화는 과도 |
| PII 마스킹 | 🔲 v1.5 | AI 전송 전 자동 마스킹 |

**상태**: ✅ v1.0 범위 내 보안 완비

---

## ROUND 3 점수

| 평가 항목 | A1 | A2 | A3 | A4 | A5 | A6 | 평균 |
|-----------|----|----|----|----|----|----|------|
| 아키텍처 완성도 | 9 | 9 | 8 | 8 | 9 | 8 | **8.5** |
| 기술 실현 가능성 | 8 | 8 | 8 | 9 | 8 | 8 | **8.2** |
| UX 품질 | 8 | 8 | 9 | 8 | 8 | 8 | **8.2** |
| 스코프 적정성 | 9 | 9 | 9 | 9 | 9 | 9 | **9.0** |
| 보안/개인정보 | 8 | 8 | 8 | 8 | 8 | 9 | **8.2** |
| **라운드 평균** | | | | | | | **8.4** |

**판정: ITERATION 3 — NEAR THRESHOLD (8.4 < 8.5)** ⚠️

0.1점 부족. 기술 실현 가능성과 보안에서 미세 보완 필요. Round 4 진행.

---

## ROUND 4: 마이크로 보완 (Threshold 달성)

### 4.1 🎧 Audio/ML Engineer → whisper.cpp Python 바인딩 최종 선택

**Q: `pywhispercpp`를 쓸 것인가, `whispercpp` 패키지를 쓸 것인가, 아니면 subprocess로 CLI를 호출할 것인가?**

> `pywhispercpp`는 업데이트가 느리고, whisper.cpp의 최신 기능(CoreML 가속 등)을 즉시 지원하지 않을 수 있다. subprocess로 `whisper-cli`를 호출하면 최신 빌드를 그대로 사용 가능하지만, 스트리밍 출력 파싱이 필요하다.

**최종 결정**:
- **v1.0**: subprocess로 `whisper-cli` 호출 (최신 빌드 활용, CoreML 가속 보장)
- 출력 파싱: `--output-json` 옵션으로 구조화된 결과 수신
- 실시간 스트리밍: `--print-realtime` + stdout 파이프라인 파싱
- **장점**: whisper.cpp 업데이트 시 바이너리만 교체하면 됨, Python 바인딩 호환성 문제 없음
- **단점**: 프로세스 시작 오버헤드 (~200ms) — 실시간에서는 프로세스를 warm 상태로 유지

**기술 실현 가능성 보완**: ✅ +0.3점 예상

---

### 4.2 🔒 Security/Privacy → macOS 권한 관리

**Q: macOS에서 마이크 접근 권한 요청 플로우가 정의되지 않았다.**

> macOS Sonoma 이후, 마이크 접근 시 시스템 권한 다이얼로그가 표시된다. PyQt6 앱에서는 `AVCaptureDevice.requestAccess(for:)` 대신 `pyaudio`/`sounddevice`가 첫 접근 시 자동으로 트리거하지만, 거부 시 복구 플로우가 없다.

**해결**:
- 첫 실행 온보딩에서 마이크 권한 명시적 안내
- 권한 거부 시: "시스템 환경설정 → 개인정보 → 마이크"로 안내하는 딥링크
- `sounddevice` 라이브러리 사용 (PortAudio 기반, macOS 네이티브 지원)
- Info.plist에 `NSMicrophoneUsageDescription` 키 포함 (py2app 설정)

**보안 보완**: ✅ +0.2점 예상

---

### 4.3 전체 에이전트 합의 투표

| Agent | 판정 | 코멘트 |
|-------|------|--------|
| 🏗️ A1 | ✅ APPROVE | 모듈 의존성 명확, 스레딩 모델 검증됨 |
| 🎧 A2 | ✅ APPROVE | whisper CLI subprocess 방식이 가장 안전, 지연 목표 달성 가능 |
| 🎨 A3 | ✅ APPROVE | UX 플로우 3클릭, 온보딩 정의 완료 |
| ⚡ A4 | ✅ APPROVE | v1.0/v1.5/v2.0 분할로 스코프 현실적 |
| 🧑‍💻 A5 | ✅ APPROVE | CLAUDE.md 38줄, 에이전트 3개, Progressive Disclosure |
| 🔒 A6 | ✅ APPROVE | 동의 메커니즘, Keychain, 권한 관리 완비 |

**6/6 APPROVE**

---

## ROUND 4 최종 점수

| 평가 항목 | A1 | A2 | A3 | A4 | A5 | A6 | 평균 |
|-----------|----|----|----|----|----|----|------|
| 아키텍처 완성도 | 9 | 9 | 9 | 9 | 9 | 9 | **9.0** |
| 기술 실현 가능성 | 9 | 9 | 8 | 9 | 9 | 8 | **8.7** |
| UX 품질 | 9 | 8 | 9 | 9 | 8 | 8 | **8.5** |
| 스코프 적정성 | 9 | 9 | 9 | 9 | 9 | 9 | **9.0** |
| 보안/개인정보 | 9 | 8 | 8 | 8 | 8 | 9 | **8.3** |
| **라운드 평균** | | | | | | | **8.7** |

**판정: ITERATION 4 — THRESHOLD MET (8.7 > 8.5)** ✅ **APPROVED**

---

## 점수 추이 요약

| Round | 평균 | 상태 |
|-------|------|------|
| 1 | 4.6 | ❌ 구조적 결함 다수 |
| 2 | 6.9 | ❌ 개선 중, 세부 미비 |
| 3 | 8.4 | ⚠️ 근접, 마이크로 보완 필요 |
| 4 | 8.7 | ✅ **APPROVED** |

---

## 최종 확정 변경사항 요약 (Round 1→4 누적)

### 아키텍처 변경
1. **4-레이어 스레딩 모델** 추가 (Main UI / Audio Capture / Transcription Worker / AI Worker)
2. **모듈 의존 방향** 명시 (단방향 강제, Signal/Slot 역방향)
3. **whisper.cpp subprocess 방식** 확정 (Python 바인딩 대신 CLI 호출)

### 스코프 변경
4. **3단계 분할**: v1.0 MVP → v1.5 AI 확장 → v2.0 고급
5. **영상 오디오 추출**: v1.0 → v1.5로 이동
6. **실시간 기본 모델**: medium → **small** (medium은 고성능 모드)

### UX 변경
7. **오버레이 위치 세션 간 저장** (settings.json)
8. **풀스크린 대응** (NSWindow collectionBehavior)
9. **캡션 줄 수 제한** (기본 2줄, 최대 5줄)
10. **첫 실행 온보딩** 3단계 (언어 → 모델 다운로드 → 마이크 권한)
11. **실시간 캡션 지연 목표**: 발화 후 2초 이내

### 보안 변경
12. **녹음 동의 안내 UI** 추가
13. **API 키 macOS Keychain** 저장 (평문 금지)
14. **Gemini 전송 동의 다이얼로그** (첫 사용 시 + 설정 3단계)
15. **API 호출 로그** 자동 기록
16. **오디오 보관 정책** (삭제/보관/묻기)
17. **macOS 마이크 권한** 관리 플로우

### DX 변경
18. **CLAUDE.md ≤ 40줄** (Progressive Disclosure)
19. **에이전트 3개**로 축소 (ui / core / review)
20. **3 커맨드**: /socratic-review, /run-tests, /build-dmg
21. **docs/ 분리**: architecture.md, code-rules.md, design-tokens.md

### 기술 세부
22. **디자인 토큰**: JSON→QSS ThemeEngine, Light/Dark 2벌
23. **사이드바**: QFileSystemWatcher + lazy loading + workspace.json 무결성
24. **오디오 입력**: sounddevice 라이브러리 (PortAudio)
25. **파일 포맷**: mp4, mov, m4a, mp3, wav 지원 (v1.5에서 영상 추가)
