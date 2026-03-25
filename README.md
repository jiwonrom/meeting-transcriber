# Meeting Transcriber

macOS 데스크탑 앱. 실시간 음성 전사를 오버레이 캡션으로 표시하고, AI 기반 요약·번역·키워드 추출을 제공합니다.

## 기술 스택

- **UI**: PyQt6
- **Transcription**: whisper.cpp (Apple Silicon CoreML 가속)
- **AI**: Gemini 3.0 Flash
- **오디오**: sounddevice (PortAudio)

## 시작하기

### 사전 요구사항

- macOS 14+ (Apple Silicon)
- Python 3.11+
- whisper.cpp CLI (`brew install whisper-cpp` 또는 소스 빌드)

### 설치

```bash
git clone https://github.com/your-repo/meeting-transcriber.git
cd meeting-transcriber
make setup
```

### 실행

```bash
python -m meeting_transcriber.app
```

### 테스트

```bash
make test
```

## Claude Code로 개발

```bash
cd meeting-transcriber
claude

# 사용 가능한 커맨드:
/project:socratic-review   # 자율 3-에이전트 코드 검증
/project:auto-commit       # 테스트 통과 후 자동 git commit+push
/project:run-tests         # 테스트 실행 + 실패 분석
/project:build-dmg         # DMG 패키징
```

## 프로젝트 구조

- `PRD.md` — 전체 요구사항
- `CLAUDE.md` — Claude Code 프로젝트 컨텍스트
- `docs/architecture.md` — 아키텍처 상세
- `docs/code-rules.md` — 코드 규칙

## 라이선스

MIT
