"""앱 전역 상수 정의."""

from __future__ import annotations

import pathlib

# 앱 기본 정보
APP_NAME = "Scribe"
APP_VERSION = "1.5.0"

# 저장 경로
DEFAULT_WORKSPACE_DIR = pathlib.Path.home() / ".meeting_transcriber"
MODELS_DIR = DEFAULT_WORKSPACE_DIR / "models"
SETTINGS_FILE = DEFAULT_WORKSPACE_DIR / "settings.json"
LOGS_DIR = DEFAULT_WORKSPACE_DIR / "logs"

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

# 시스템 오디오 (BlackHole)
BLACKHOLE_DEVICE_NAMES = ("blackhole 2ch", "blackhole 16ch", "blackhole 64ch")
AGGREGATE_DEVICE_NAME = "Scribe Audio (Mic + System)"
AGGREGATE_DEVICE_UID = "com.scribe.aggregate-device"

# 화자 분리 (Speaker Diarization)
DIARIZATION_MODEL = "pyannote/speaker-diarization-community-1"
DIARIZATION_DEVICE = "cpu"  # MPS has sparse tensor bugs with pyannote (PyTorch issue #143955)
DIARIZATION_CACHE_DIR = DEFAULT_WORKSPACE_DIR / "models" / "pyannote"
DIARIZATION_COREML_DIR = DIARIZATION_CACHE_DIR / "coreml"

# 회의 템플릿
TEMPLATES_DIR = DEFAULT_WORKSPACE_DIR / "templates"
BUILTIN_TEMPLATE_NAMES = ("general", "team_meeting", "one_on_one", "lecture", "interview")
DEFAULT_TEMPLATE = "general"

# 회의 감지 (Meeting Detection)
DETECTION_POLL_INTERVAL_MS = 10_000  # 10초 폴링 주기
DETECTION_COOLDOWN_SECONDS = 300  # 5분 전역 쿨다운
KNOWN_CONFERENCING_APPS: dict[str, str] = {
    "us.zoom.xos": "team_meeting",
    "com.microsoft.teams2": "team_meeting",
    "com.google.Chrome": "team_meeting",  # Meet — requires audio heuristic
    "com.apple.FaceTime": "one_on_one",
    "com.cisco.webexmeetingsapp": "team_meeting",
    "com.tinyspeck.slackmacgap": "team_meeting",
}
CHROME_BUNDLE_ID = "com.google.Chrome"

# 교차 회의 분석 (Cross-Meeting Analysis)
ANALYSES_DIR = "analyses"
INDEX_FILE = "index.json"
INDEX_VERSION = "1.0"
MIN_SELECTION_COUNT = 2
