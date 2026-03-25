# Architecture

## 모듈 구조

```
src/meeting_transcriber/
├── ui/         # PyQt6 위젯 (메인 윈도우, 오버레이, 사이드바, 트레이)
├── core/       # 오디오 캡처, whisper.cpp 래퍼, 파일 임포트
├── ai/         # Gemini 프로바이더, AI 태스크 (요약/번역/키워드)
├── storage/    # 파일시스템 관리, transcript CRUD, export
└── utils/      # 설정, Keychain, 단축키, 상수
```

## 의존 방향 (절대 규칙)

```
허용:
  ui → core     (UI가 오디오/전사 기능 호출)
  ui → ai       (UI가 AI 결과 표시)
  ai → storage  (AI가 파일명 생성 후 storage에 저장 요청)

금지:
  core → ui     (Signal/Slot으로만 역방향 통신)
  ai → ui       (Signal/Slot으로만 역방향 통신)
  storage → ai  (단방향만 허용)
```

## 스레딩 모델

| 레이어 | 구현 | 역할 |
|--------|------|------|
| Main Thread | PyQt6 이벤트 루프 | UI 렌더링 전용. blocking I/O 절대 금지 |
| Audio Capture | QThread | sounddevice 콜백, 2초 청크 버퍼링 |
| Transcription Worker | subprocess (별도 프로세스) | whisper-cli 실행, GIL 회피 |
| AI Worker | QThread | Gemini API 비동기 호출 |

## 데이터 흐름

1. sounddevice → 2초 청크 → Queue
2. Transcription Worker가 Queue에서 청크 수신
3. whisper-cli subprocess로 전사 → JSON 결과
4. Signal로 Main Thread에 전달 → 오버레이 업데이트
5. transcript.json에 세그먼트 추가 저장
6. (v1.5) AI Worker에서 Gemini API 호출 → 요약/번역 결과

## 파일 저장 구조

```
~/.meeting_transcriber/
├── settings.json           # 앱 설정 (오버레이 위치, 모델 선택 등)
├── workspace.json          # 사이드바 메타데이터
├── models/                 # whisper.cpp 모델 파일
│   ├── ggml-small.bin
│   └── ggml-medium.bin
├── Work/
│   └── Meeting-Title/
│       ├── metadata.json
│       ├── transcript.json
│       └── transcript.md
└── Personal/
    └── ...
```
