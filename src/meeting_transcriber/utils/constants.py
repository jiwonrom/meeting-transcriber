"""앱 전역 상수 정의."""
from __future__ import annotations

import pathlib

# 앱 기본 정보
APP_NAME = "Meeting Transcriber"
APP_VERSION = "1.0.0"

# 저장 경로
DEFAULT_WORKSPACE_DIR = pathlib.Path.home() / ".meeting_transcriber"
MODELS_DIR = DEFAULT_WORKSPACE_DIR / "models"
SETTINGS_FILE = DEFAULT_WORKSPACE_DIR / "settings.json"

# 지원 언어
SUPPORTED_LANGUAGES = ("en", "ko", "zh", "ja")
DEFAULT_LANGUAGE = "auto"

# Whisper 모델
WHISPER_MODELS = {
    "small": "ggml-small.bin",
    "medium": "ggml-medium.bin",
    "large-v3": "ggml-large-v3.bin",
}
DEFAULT_WHISPER_MODEL = "small"

# 오디오 설정
AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1
AUDIO_CHUNK_SECONDS = 2
AUDIO_VAD_THRESHOLD = 0.01  # RMS 기준 무음 판정 임계값
AUDIO_LEVEL_INTERVAL_MS = 100  # UI 레벨 미터 업데이트 주기(ms)

# 오버레이 기본값
OVERLAY_DEFAULT_LINES = 2
OVERLAY_MAX_LINES = 5

# 지원 오디오 포맷
SUPPORTED_AUDIO_FORMATS = (".wav", ".mp3", ".m4a")
