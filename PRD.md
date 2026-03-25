# Meeting Transcriber — Product Requirements Document

**Version**: 1.0.0
**Date**: 2026-03-25
**Status**: Approved (Socratic Review Round 4, Score 8.7/10)

---

## 1. 제품 개요

### 1.1 비전

macOS 네이티브 데스크탑 앱. 실시간 음성 전사를 오버레이 캡션으로 표시하고, 녹음/파일 임포트를 통해 다국어 transcript를 생성하며, AI 기반 요약·번역·키워드 추출을 제공한다. 모든 데이터는 로컬 우선으로 처리된다.

### 1.2 핵심 가치

- **실시간 캡션**: Closed Caption처럼 화면 위에 자막 표시
- **다국어 우선**: 영어, 한국어, 중국어, 일본어
- **로컬 우선**: whisper.cpp 온디바이스 처리, 클라우드는 AI 기능에만 사용
- **폴더 기반 관리**: 실제 파일시스템에 대응되는 사이드바 UI

### 1.3 레퍼런스 앱

| 앱 | 차용 요소 |
|----|----------|
| Slipbox | 로컬 우선 아키텍처, 메뉴바 상주, Apple Silicon 최적화 |
| Notion AI Meeting Notes | 사이드바 관리 UX, `/meet` 식 빠른 시작 |
| Zoom AI Companion | 실시간 캡션 UX, 언어 자동 감지, 상태 표시 |
| Tiro | 한국어/일본어 정확도 기준, 커스텀 요약 템플릿 |
| Mangonote | Apple Silicon 전용 최적화, 요약 크기 조절 |

---

## 2. 기술 스택

| 영역 | 기술 | 선정 근거 |
|------|------|----------|
| UI 프레임워크 | **PyQt6** | Python 단일 스택, 오버레이 윈도우 지원, PEP8 자연스러움 |
| Transcription | **whisper.cpp** (subprocess CLI) | Apple Silicon CoreML/Metal 가속, 최신 빌드 즉시 활용 |
| 화자 분리 | **pyannote community-1** (v1.5) | 오픈소스 최고 정확도, exclusive_speaker_diarization |
| AI 프로바이더 | **Gemini 3.0 Flash** | 저비용, 빠른 응답, 전 AI 기능 커버 |
| 오디오 입력 | **sounddevice** (PortAudio) | macOS 네이티브, 저지연 |
| 파일 임포트 | **PyAV** (v1.5에서 영상 추가) | pip install 가능, ffmpeg 바인딩 |
| 패키징 | **py2app → create-dmg** | macOS .app 번들 + DMG 인스톨러 |
| 디자인 시스템 | **Design Systems MCP + 자체 토큰** | WCAG/접근성 참조 + JSON→QSS ThemeEngine |
| 테스트 | **pytest + pytest-qt** | 코어 + UI + E2E + API mock |

---

## 3. 아키텍처

### 3.1 스레딩 모델 (4-Layer)

```
┌─────────────────────────────────────────────────┐
│ Main Thread (UI Only)                           │
│  PyQt6 이벤트 루프, 위젯 렌더링, Signal/Slot    │
│  ❌ blocking I/O 절대 금지                       │
└──────────────┬──────────────────────────────────┘
               │ Signal/Slot
┌──────────────▼──────────────────────────────────┐
│ Audio Capture Thread (QThread)                  │
│  sounddevice 콜백 → 오디오 버퍼 관리            │
│  2초 청크 단위로 Transcription Worker에 전달     │
└──────────────┬──────────────────────────────────┘
               │ Queue
┌──────────────▼──────────────────────────────────┐
│ Transcription Worker (subprocess — 별도 프로세스)│
│  whisper-cli 실행, GIL 회피                     │
│  --print-realtime + --output-json               │
│  프로세스 warm 상태 유지 (시작 오버헤드 최소화)  │
└──────────────┬──────────────────────────────────┘
               │ Signal
┌──────────────▼──────────────────────────────────┐
│ AI Worker Thread (QThread)                      │
│  Gemini API 비동기 호출                         │
│  요약, 번역, 키워드 등 — 전사 완료 후 실행      │
└─────────────────────────────────────────────────┘
```

### 3.2 모듈 의존 방향

```
ui/ → core/     (단방향)
ui/ → ai/       (단방향)
ai/ → storage/  (단방향 — 파일명 자동 생성 시)
core/ ↛ ui/     (금지 — Signal/Slot으로만 역방향)
ai/ ↛ ui/       (금지 — Signal/Slot으로만 역방향)
storage/ ↛ ai/  (금지 — 단방향만 허용)
```

### 3.3 데이터 흐름

```
마이크 → sounddevice → 2초 청크 버퍼
  → whisper-cli subprocess (small/medium 모델)
  → transcript segments [{start, end, text, language, confidence}]
  → UI 오버레이 캡션 표시
  → transcript.json 저장
  → (선택) Gemini API → 요약/번역/키워드
  → storage/ → 파일시스템 (~/.meeting_transcriber/)
```

---

## 4. 기능 요구사항

### 4.1 v1.0 — MVP

#### 4.1.1 실시간 Transcription

| 항목 | 스펙 |
|------|------|
| 엔진 | whisper.cpp (subprocess CLI 호출) |
| 기본 모델 | small (실시간 캡션) |
| 고성능 모드 | medium (설정에서 전환) |
| 언어 | EN, KO, ZH, JA + auto-detect |
| 언어 감지 | 사용자 "주 사용 언어" 사전 설정, 30초마다 보조 감지 |
| 지연 목표 | 발화 종료 후 **2초 이내** 캡션 표시 |
| 허용 최대 | 3초 |
| 청크 크기 | 2초 + VAD(무음 구간 건너뛰기) |

#### 4.1.2 오버레이 캡션

| 항목 | 스펙 |
|------|------|
| 윈도우 타입 | `Qt.WindowStaysOnTopHint + Qt.FramelessWindowHint` |
| 위치 | 드래그로 이동 가능, **위치 세션 간 저장** (settings.json) |
| 풀스크린 대응 | `Qt.WindowDoesNotAcceptFocus` + `NSWindow.collectionBehavior` |
| 줄 수 | 기본 2줄, 최대 5줄 (설정 가능) |
| 커스터마이즈 | 폰트, 크기, 배경 투명도, 텍스트 색상 |
| 모드 | 표시/숨기기 토글 (글로벌 단축키) |

#### 4.1.3 오디오 입력

| 소스 | v1.0 | 구현 |
|------|------|------|
| 마이크 | ✅ | sounddevice, 장치 선택 가능 |
| 오디오 파일 (mp3, wav, m4a) | ✅ | 직접 로드, 16kHz mono WAV 변환 |
| 영상에서 오디오 추출 | ❌ v1.5 | PyAV |
| 시스템 오디오 | ❌ v2.0 | BlackHole 연동 |

#### 4.1.4 사이드바 폴더 관리

| 항목 | 스펙 |
|------|------|
| 구조 | 실제 파일시스템 폴더와 1:1 대응 |
| 저장 경로 | `~/.meeting_transcriber/` |
| 기능 | rename, delete, 새 폴더 생성 |
| 외부 변경 감지 | QFileSystemWatcher로 실시간 동기화 |
| 무결성 | workspace.json에 파일 해시 저장 |
| 충돌 처리 | "외부에서 변경됨" 알림 + 새로고침 |
| 성능 | QTreeView + lazy loading (100개+ 폴더 대응) |
| drag&drop 이동 | ❌ v1.5 (rename/delete만 v1.0) |

#### 4.1.5 저장 포맷

**transcript.json** (내부 전용):
```json
{
  "version": "1.0",
  "metadata": {
    "title": "2026-03-25_Weekly-Standup_EN",
    "created_at": "2026-03-25T10:00:00+09:00",
    "duration_seconds": 3600,
    "languages": ["en", "ko"],
    "source": "microphone",
    "model": "whisper-small",
    "tags": ["meeting", "standup"]
  },
  "segments": [
    {
      "start": 0.0,
      "end": 2.5,
      "text": "Good morning everyone",
      "language": "en",
      "confidence": 0.95
    }
  ]
}
```

**Export**: Markdown, TXT

#### 4.1.6 UX 기능

| 기능 | 구현 |
|------|------|
| macOS 메뉴바 트레이 | 상주 아이콘, 빠른 녹음 시작/정지 |
| 글로벌 단축키 | 녹음 시작/정지 (기본: Cmd+Shift+R) |
| 언어 자동 감지 | whisper --language auto + 주 언어 사전 설정 |
| 캡션 커스터마이즈 | 폰트, 크기, 줄 수, 투명도 |
| Dark/Light 모드 | macOS 시스템 설정 자동 감지 |
| 첫 실행 온보딩 | 3단계: 언어 선택 → 모델 다운로드 → 마이크 권한 |

#### 4.1.7 Whisper 모델 관리

| 항목 | 스펙 |
|------|------|
| 첫 실행 | small 모델 자동 다운로드 (~466MB) |
| 다운로드 중 | 진행률 표시 UI |
| 추가 모델 | 설정에서 medium/large-v3 다운로드 가능 |
| 저장 경로 | `~/.meeting_transcriber/models/` |
| CoreML 가속 | 활성화 필수 (첫 실행 시 컴파일, 이후 캐시) |

#### 4.1.8 디자인 시스템

| 항목 | 스펙 |
|------|------|
| 토큰 파일 | `design/tokens_light.json`, `design/tokens_dark.json` |
| 변환 | `ui/theme.py` ThemeEngine — JSON→QSS f-string 생성 |
| MCP 참조 | Design Systems MCP (WCAG, 접근성 기준 조회) |
| Notion MCP | 디자인 결정 기록, 컴포넌트 스펙 문서화 |

#### 4.1.9 보안

| 항목 | 구현 |
|------|------|
| API 키 저장 | macOS Keychain (`keyring` 라이브러리) |
| 오디오 보관 정책 | 설정: 전사 후 삭제 / 보관 / 묻기 |
| macOS 마이크 권한 | 온보딩에서 안내, 거부 시 시스템 환경설정 딥링크 |
| .env 유출 방지 | .gitignore + pre-commit hook |
| Info.plist | NSMicrophoneUsageDescription 포함 |

---

### 4.2 v1.5 — AI 확장

| 기능 | 설명 |
|------|------|
| AI 요약 | Gemini Flash, transcript 기반 구조화 요약 |
| 액션 아이템 추출 | 할일/담당자/기한 자동 추출 |
| 번역 | 전사 결과를 타 언어로 번역 |
| 키워드/토픽 추출 | 빈출 키워드, 주제 분류 |
| 내용 교열 | 맞춤법, 문법 자동 교정 |
| 파일명/카테고리 자동 생성 | Gemini Flash로 제목+카테고리 자동 분류 |
| 화자 분리 | pyannote community-1, 파일 전사 시 적용 |
| 화자-텍스트 정렬 | alignment.py, WhisperX 알고리즘 참조 |
| 영상 오디오 추출 | PyAV, mp4/mov/avi/mkv/webm 지원 |
| AI 프로바이더 폴백 | 설정에서 fallback provider 추가 가능 구조 |
| PII 마스킹 | AI 전송 전 개인 식별 정보 자동 마스킹 |
| transcript 암호화 | 자체 암호화 옵션 |
| 사이드바 drag&drop | 폴더 간 파일 이동 |

### 4.3 v2.0 — 고급

| 기능 | 설명 |
|------|------|
| 시스템 오디오 캡처 | BlackHole 연동 |
| 자동 미팅 감지 | 마이크/시스템 프로세스 모니터링 |
| 실시간 화자 분리 | ANE 최적화 (Slipbox 참조) |
| BYOK | 사용자 API 키 설정 |
| 미팅 포맷/템플릿 | Team Meeting, 1:1, Lecture, Interview 등 |
| 크로스 미팅 분석 | 여러 회의록 통합 분석 |
| Obsidian/Notion 연동 | export 자동화 |
| SRT/VTT export | 자막 포맷 추가 |

---

## 5. 프로젝트 구조

```
meeting-transcriber/
├── CLAUDE.md                              # ≤40줄
├── PRD.md                                 # 이 문서
├── .claude/
│   ├── settings.json                      # hooks 설정
│   ├── agents/
│   │   ├── ui-agent.md
│   │   ├── core-agent.md
│   │   └── review-agent.md
│   └── commands/
│       ├── socratic-review.md             # 자율 3-에이전트 검증 + 자동 수정
│       ├── auto-commit.md                 # 테스트 통과 후 git commit+push
│       ├── run-tests.md
│       └── build-dmg.md
├── scripts/
│   ├── auto_review.py                     # PostToolUse hook
│   └── phase_gate_check.py                # Stop hook
├── docs/
│   ├── architecture.md
│   ├── code-rules.md
│   └── design-tokens.md
├── design/
│   ├── tokens_light.json
│   └── tokens_dark.json
├── src/meeting_transcriber/
│   ├── __init__.py
│   ├── app.py                             # 메인 엔트리포인트
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py                 # 메인 윈도우 + 사이드바
│   │   ├── overlay.py                     # 플로팅 캡션 오버레이
│   │   ├── sidebar.py                     # 폴더 트리 위젯
│   │   ├── settings_dialog.py             # 설정 다이얼로그
│   │   ├── onboarding.py                  # 첫 실행 온보딩
│   │   ├── tray.py                        # 메뉴바 트레이 아이콘
│   │   └── theme.py                       # ThemeEngine (JSON→QSS)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── audio_capture.py               # sounddevice 마이크 입력
│   │   ├── transcriber.py                 # whisper-cli subprocess 래퍼
│   │   ├── file_importer.py               # 오디오 파일 임포트 + 변환
│   │   ├── model_manager.py               # Whisper 모델 다운로드/관리
│   │   └── alignment.py                   # 화자-텍스트 정렬 (v1.5 stub)
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── provider_base.py               # ABC 추상화
│   │   ├── gemini_provider.py             # Gemini 3.0 Flash 구현
│   │   └── tasks.py                       # 요약, 번역, 키워드, 교열, 파일명 생성
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── workspace.py                   # 폴더 구조 + workspace.json 관리
│   │   ├── transcript_store.py            # transcript.json CRUD
│   │   └── exporter.py                    # MD/TXT export
│   └── utils/
│       ├── __init__.py
│       ├── config.py                      # 설정 관리 (settings.json)
│       ├── keychain.py                    # macOS Keychain 연동
│       ├── shortcuts.py                   # 글로벌 단축키 관리
│       └── constants.py                   # 상수 정의
├── tests/
│   ├── conftest.py                        # 공통 fixture
│   ├── fixtures/
│   │   ├── sample_en_30s.wav              # 영어 30초
│   │   ├── sample_ko_30s.wav              # 한국어 30초
│   │   ├── sample_zh_30s.wav              # 중국어 30초
│   │   └── sample_ja_30s.wav              # 일본어 30초
│   ├── test_transcriber.py
│   ├── test_audio_capture.py
│   ├── test_file_importer.py
│   ├── test_sidebar.py
│   ├── test_overlay.py
│   ├── test_ai_provider.py
│   ├── test_storage.py
│   └── test_exporter.py
├── pyproject.toml
├── Makefile
└── README.md
```

---

## 6. Claude Code 설정

### 6.1 CLAUDE.md

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
- PEP8 준수, ruff 자동 포맷
- 모든 public 함수에 type hint + docstring
- 새 기능 추가 시 테스트 필수 (pytest)
- whisper.cpp 추론은 반드시 별도 프로세스에서 실행 (메인 스레드 블로킹 금지)
- API 키는 macOS Keychain 저장 (평문 파일 금지)

## MUST NOT
- ui/ 모듈에서 외부 API 직접 호출 금지
- 메인 스레드에서 blocking I/O 금지
- transcript.json 스키마 임의 변경 금지

## Testing
- `pytest tests/ -x --tb=short`
- `pytest tests/test_transcriber.py -k "test_korean"`
- fixtures/에 4개 언어 샘플 오디오 (각 30초)

## Phase
- 현재: v1.0 MVP
- `@PRD.md`에서 v1.0/v1.5/v2.0 스코프 확인
```

### 6.2 settings.json (Hooks)

```json
{
  "permissions": {
    "allow": [
      "make lint",
      "make test",
      "make typecheck",
      "pytest*",
      "ruff*",
      "mypy*",
      "git add*",
      "git commit*",
      "git push*",
      "python scripts/*"
    ]
  },
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "write_file|create_file|str_replace",
        "command": "python scripts/auto_review.py"
      }
    ],
    "Stop": [
      {
        "command": "python scripts/phase_gate_check.py"
      }
    ]
  }
}
```

### 6.3 에이전트

**ui-agent.md**:
```markdown
너는 PyQt6 UI 전문가다. 담당 범위: src/meeting_transcriber/ui/ 전체.

규칙:
- 모든 위젯은 QWidget 또는 QMainWindow 상속
- blocking 호출 절대 금지 — 긴 작업은 Signal/Slot으로 core/ai에 위임
- ThemeEngine의 QSS를 통해서만 스타일링 (인라인 스타일 금지)
- 접근성: 모든 버튼에 tooltip, 키보드 네비게이션 지원

수정 후 반드시: pytest tests/test_overlay.py tests/test_sidebar.py
```

**core-agent.md**:
```markdown
너는 오디오 처리 + AI 통합 전문가다.
담당 범위: src/meeting_transcriber/core/, src/meeting_transcriber/ai/, src/meeting_transcriber/storage/

규칙:
- whisper-cli는 subprocess로만 호출 (Python 바인딩 사용 금지)
- 오디오 처리는 항상 별도 스레드/프로세스
- AI provider_base.py의 ABC를 반드시 상속
- storage 모듈은 ai에 의존하지 않음 (단방향: ai → storage)

수정 후 반드시: pytest tests/test_transcriber.py tests/test_ai_provider.py tests/test_storage.py
```

**review-agent.md**:
```markdown
너는 품질 검증 전문가다. 3개 페르소나로 자율 검토를 수행한다.

절차 (사용자 입력 없이 자동 완료):
1. git diff --name-only로 변경 파일 확인
2. 3 페르소나 순차 검토:
   - 🏗️ Architect: 모듈 의존 방향 위반, 스레딩 규칙
   - 🎧 Core Engineer: 오디오 파이프라인 정합성, 테스트 커버리지
   - 🔒 Security: API 키 노출, 평문 저장, Keychain 사용 여부
3. 이슈 발견 시 직접 수정 실행
4. pytest 재실행하여 통과 확인
5. 전원 APPROVE 시 완료 보고

반복: 이슈 발견 시 최대 3회 자동 수정. 3회 후 미해결 시 사용자 보고.
```

### 6.4 커맨드

**socratic-review.md** (`/project:socratic-review`):
```markdown
review-agent.md의 절차를 실행하라.
추가로, 변경 규모가 클 경우 (10개+ 파일 또는 새 모듈 추가):
- PRD.md의 해당 Phase 스펙과 대조
- 누락된 acceptance criteria 식별
- 결과를 마크다운 테이블로 출력
```

**auto-commit.md** (`/project:auto-commit`):
```markdown
1. make lint && make test 실행
2. 모두 통과 시:
   - git add -A
   - 변경 내용 분석하여 conventional commit 메시지 생성
     - feat: 새 기능 | fix: 버그 | refactor: 리팩터링 | test: 테스트 | docs: 문서
   - git commit -m "{메시지}"
   - git push origin main
3. 실패 시: 실패 원인 보고, 커밋 중단
```

**run-tests.md** (`/project:run-tests`):
```markdown
pytest tests/ -x --tb=short -v
실패 시 실패한 테스트의 원인을 분석하고 수정 제안.
```

**build-dmg.md** (`/project:build-dmg`):
```markdown
1. make lint && make test (phase gate)
2. python setup.py py2app
3. create-dmg로 DMG 생성
4. codesign 서명 (개발자 인증서 있을 경우)
5. 결과물 경로 출력
```

---

## 7. 자동화 스크립트

### 7.1 auto_review.py (PostToolUse Hook)

```python
#!/usr/bin/env python3
"""PostToolUse hook — 파일 수정 후 자동 검증."""
import subprocess
import sys

checks = [
    ("ruff check src/", "lint"),
    ("mypy src/ --ignore-missing-imports", "typecheck"),
]

for cmd, name in checks:
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"⚠️ {name} issues found:\n{result.stdout[:500]}", file=sys.stderr)
```

### 7.2 phase_gate_check.py (Stop Hook)

```python
#!/usr/bin/env python3
"""Stop hook — 작업 완료 시 phase gate 검증."""
import subprocess
import sys

checks = {
    "lint": "ruff check src/",
    "typecheck": "mypy src/ --ignore-missing-imports",
    "test": "pytest tests/ -x --tb=short -q",
}

failed = []
for name, cmd in checks.items():
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        failed.append(name)
        print(f"❌ {name}: {result.stdout[:200]}", file=sys.stderr)

if failed:
    print(f"\n❌ Phase gate FAILED: {', '.join(failed)}", file=sys.stderr)
    print("위 체크를 통과하도록 수정하라.", file=sys.stderr)
    sys.exit(1)
else:
    print("✅ Phase gate PASSED — auto-commit 가능", file=sys.stderr)
```

---

## 8. 테스트 전략

### 8.1 테스트 레이어

| 레이어 | 도구 | 대상 | 커버리지 목표 |
|--------|------|------|--------------|
| 단위 테스트 | pytest | core/, ai/, storage/ | 80%+ |
| UI 테스트 | pytest-qt | ui/ 위젯 | 주요 인터랙션 |
| E2E | pytest + fixtures | 전체 파이프라인 | 4개 언어 |
| API mock | pytest + unittest.mock | ai/gemini_provider.py | 100% |

### 8.2 핵심 테스트 케이스

```python
# test_transcriber.py
def test_english_transcription(sample_en_wav):
    """영어 30초 샘플 전사 — 정확도 80%+ WER"""

def test_korean_transcription(sample_ko_wav):
    """한국어 30초 샘플 전사 — 정확도 70%+ WER"""

def test_language_autodetect(sample_en_wav, sample_ko_wav):
    """언어 자동 감지 정확도"""

def test_realtime_latency():
    """실시간 캡션 지연 3초 이내"""

# test_overlay.py
def test_overlay_drag(qtbot):
    """오버레이 드래그 이동 + 위치 저장"""

def test_overlay_line_limit(qtbot):
    """캡션 줄 수 제한 (기본 2줄)"""

# test_sidebar.py
def test_folder_create_rename_delete(tmp_path):
    """폴더 CRUD — 파일시스템 동기화 확인"""

def test_external_change_detection(tmp_path):
    """Finder에서 파일 삭제 시 사이드바 반영"""

# test_ai_provider.py
def test_gemini_summary_mock():
    """Gemini 요약 API 호출 mock"""

def test_provider_abstraction():
    """ABC 인터페이스 준수 검증"""
```

---

## 9. 마일스톤

### v1.0 MVP

| Phase | 기능 | 예상 기간 |
|-------|------|----------|
| P0 | 프로젝트 부트스트랩, CI 설정, 테스트 인프라 | 1주 |
| P1 | core/transcriber.py — whisper-cli 연동, 파일 전사 | 2주 |
| P2 | core/audio_capture.py — 실시간 마이크 입력 | 1주 |
| P3 | ui/overlay.py — 플로팅 캡션 오버레이 | 1주 |
| P4 | ui/main_window.py + sidebar.py — 메인 UI + 폴더 관리 | 2주 |
| P5 | storage/ — transcript.json CRUD + export | 1주 |
| P6 | 통합 + 메뉴바 트레이 + 글로벌 단축키 | 1주 |
| P7 | 온보딩 + 모델 다운로드 UI + 설정 | 1주 |
| P8 | 테스트 + 버그 수정 + DMG 패키징 | 1주 |
| **합계** | | **~11주** |

### v1.5 AI 확장

| Phase | 기능 | 예상 기간 |
|-------|------|----------|
| P9 | ai/ — Gemini 연동, 요약/번역/키워드 | 2주 |
| P10 | 화자 분리 (pyannote) + alignment | 2주 |
| P11 | 영상 오디오 추출 (PyAV) | 1주 |
| P12 | 자동 파일명/카테고리 + 교열 | 1주 |

### v2.0 고급

별도 계획.

---

## 10. Socratic Review 프로토콜

### 적용 시점

- 매 Phase 완료 시 `/project:socratic-review` 자동 실행
- 10개+ 파일 변경 시 Stop hook에서 자동 트리거
- 수동 실행: 언제든 `/project:socratic-review`

### 에이전트 구성

3개 페르소나가 순차 검토:

| 페르소나 | 검토 초점 |
|----------|----------|
| 🏗️ Architect | 모듈 의존 방향 위반, 스레딩 규칙, 데이터 흐름 |
| 🎧 Core Engineer | 오디오 파이프라인, 테스트 커버리지, 성능 |
| 🔒 Security | API 키 노출, 평문 저장, 권한 관리 |

### 자동 실행 플로우

```
코드 작성 완료
  ↓
[Stop Hook] phase_gate_check.py
  ↓ (lint + typecheck + test 통과)
[자동] /socratic-review
  ↓ (3 페르소나 검토, 이슈 시 최대 3회 자동 수정)
[자동] /auto-commit
  ↓ (git add + commit + push)
GitHub 반영 완료
```

---

## 11. 참고: Socratic Review 이력

이 PRD는 6개 에이전트 × 4라운드 Socratic Review를 거쳐 확정되었다.

| Round | 점수 | 핵심 변경 |
|-------|------|----------|
| 1 | 4.6 | 스레딩 모델 추가, 다국어 기본 모델 small로 변경, 보안 메커니즘 추가 |
| 2 | 6.9 | pyannote 정렬 전략, QSS ThemeEngine, Gemini SPOF 완화, ffmpeg→PyAV |
| 3 | 8.4 | whisper CLI subprocess 확정, 지연 2초 목표, v1.0 스코프 최종 확정 |
| 4 | 8.7 | whisper 바인딩 최종 결정, macOS 권한 관리, 전원 APPROVE |

전체 변경 상세: `meeting-transcriber-socratic-review.md` 참조.
