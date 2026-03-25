"""constants 모듈 단위 테스트."""
from __future__ import annotations

import pathlib

from meeting_transcriber.utils.constants import (
    APP_NAME,
    APP_VERSION,
    AUDIO_CHANNELS,
    AUDIO_CHUNK_SECONDS,
    AUDIO_SAMPLE_RATE,
    DEFAULT_LANGUAGE,
    DEFAULT_WHISPER_MODEL,
    DEFAULT_WORKSPACE_DIR,
    MODELS_DIR,
    OVERLAY_DEFAULT_LINES,
    OVERLAY_MAX_LINES,
    SUPPORTED_AUDIO_FORMATS,
    SUPPORTED_LANGUAGES,
    WHISPER_MODELS,
)


def test_app_metadata() -> None:
    """앱 이름과 버전이 올바른지 확인."""
    assert APP_NAME == "Meeting Transcriber"
    assert APP_VERSION == "1.0.0"


def test_workspace_paths() -> None:
    """워크스페이스 경로가 ~/.meeting_transcriber 하위인지 확인."""
    assert DEFAULT_WORKSPACE_DIR == pathlib.Path.home() / ".meeting_transcriber"
    assert MODELS_DIR == DEFAULT_WORKSPACE_DIR / "models"


def test_supported_languages() -> None:
    """PRD에 명시된 4개 언어가 모두 포함되어 있는지 확인."""
    assert "en" in SUPPORTED_LANGUAGES
    assert "ko" in SUPPORTED_LANGUAGES
    assert "zh" in SUPPORTED_LANGUAGES
    assert "ja" in SUPPORTED_LANGUAGES


def test_default_language_is_auto() -> None:
    """기본 언어 감지 모드가 auto인지 확인."""
    assert DEFAULT_LANGUAGE == "auto"


def test_whisper_models_include_small() -> None:
    """기본 모델 small이 WHISPER_MODELS에 포함되어 있는지 확인."""
    assert DEFAULT_WHISPER_MODEL == "small"
    assert "small" in WHISPER_MODELS
    assert WHISPER_MODELS["small"] == "ggml-small.bin"


def test_audio_settings() -> None:
    """오디오 설정이 PRD 스펙과 일치하는지 확인."""
    assert AUDIO_SAMPLE_RATE == 16000
    assert AUDIO_CHANNELS == 1
    assert AUDIO_CHUNK_SECONDS == 2


def test_overlay_defaults() -> None:
    """오버레이 기본값이 PRD 스펙과 일치하는지 확인."""
    assert OVERLAY_DEFAULT_LINES == 2
    assert OVERLAY_MAX_LINES == 5


def test_supported_audio_formats() -> None:
    """지원 오디오 포맷이 PRD에 명시된 포맷을 포함하는지 확인."""
    assert ".wav" in SUPPORTED_AUDIO_FORMATS
    assert ".mp3" in SUPPORTED_AUDIO_FORMATS
    assert ".m4a" in SUPPORTED_AUDIO_FORMATS
