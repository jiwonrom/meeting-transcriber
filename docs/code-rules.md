# Code Rules

## 스타일
- PEP8 준수, ruff로 자동 포맷
- 최대 줄 길이: 100자
- import 순서: stdlib → third-party → local (ruff가 자동 정렬)

## Type Hints
- 모든 public 함수에 type hint 필수
- `from __future__ import annotations` 사용
- Optional, Union 대신 `X | None` 구문 (Python 3.10+)

## Docstrings
- 모든 public 함수/클래스에 docstring 필수
- Google 스타일:
  ```python
  def process_audio(chunk: bytes, sample_rate: int = 16000) -> list[Segment]:
      """오디오 청크를 전사하여 세그먼트 리스트를 반환.

      Args:
          chunk: PCM 오디오 데이터
          sample_rate: 샘플링 레이트 (기본 16kHz)

      Returns:
          전사된 세그먼트 리스트
      """
  ```

## 네이밍
- 변수/함수: snake_case
- 클래스: PascalCase
- 상수: UPPER_SNAKE_CASE
- private: _prefix

## 에러 처리
- 구체적 예외 사용 (Exception 금지)
- `src/meeting_transcriber/utils/exceptions.py`에 프로젝트 예외 정의
- 외부 프로세스 실패 시 적절한 fallback + 사용자 알림

## Signal/Slot 패턴
- core → ui 역방향 통신은 반드시 pyqtSignal 사용
- Signal 이름: `{동사}_{명사}` (예: `transcription_completed`, `audio_level_changed`)
