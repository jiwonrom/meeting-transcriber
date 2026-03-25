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
