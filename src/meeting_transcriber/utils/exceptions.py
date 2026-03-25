"""프로젝트 전역 예외 정의."""
from __future__ import annotations


class MeetingTranscriberError(Exception):
    """Meeting Transcriber 기본 예외."""


class WhisperCliNotFoundError(MeetingTranscriberError):
    """whisper-cli 바이너리를 찾을 수 없을 때 발생."""


class WhisperModelNotFoundError(MeetingTranscriberError):
    """Whisper 모델 파일이 존재하지 않을 때 발생."""


class TranscriptionError(MeetingTranscriberError):
    """전사 프로세스 실행 중 오류가 발생했을 때."""


class AudioFormatError(MeetingTranscriberError):
    """지원하지 않는 오디오 포맷일 때 발생."""


class ModelDownloadError(MeetingTranscriberError):
    """모델 다운로드 실패 시 발생."""


class AudioCaptureError(MeetingTranscriberError):
    """오디오 캡처 중 오류 발생 (장치 없음, 권한 거부 등)."""
