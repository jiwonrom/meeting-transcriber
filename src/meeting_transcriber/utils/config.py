"""설정 관리 — settings.json 로드/저장."""
from __future__ import annotations

import json
import pathlib
from typing import Any

from meeting_transcriber.utils.constants import DEFAULT_WORKSPACE_DIR, SETTINGS_FILE


def _default_settings() -> dict[str, Any]:
    """기본 설정값을 반환한다."""
    return {
        "language": "auto",
        "whisper_model": "small",
        "overlay": {
            "lines": 2,
            "font_size": 18,
            "opacity": 0.85,
            "position": None,
        },
        "audio": {
            "device": None,
            "post_recording": "ask",  # "delete" | "keep" | "ask"
        },
        "theme": "system",
    }


def ensure_workspace() -> pathlib.Path:
    """워크스페이스 디렉토리가 존재하는지 확인하고, 없으면 생성한다."""
    DEFAULT_WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    (DEFAULT_WORKSPACE_DIR / "models").mkdir(exist_ok=True)
    return DEFAULT_WORKSPACE_DIR


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """base에 override를 깊은 병합한다. 누락된 키는 base 값을 유지."""
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_settings() -> dict[str, Any]:
    """settings.json을 읽어 기본값과 병합하여 반환한다.

    파일이 없거나 손상되어도 기본값으로 동작한다.
    """
    defaults = _default_settings()
    if not SETTINGS_FILE.exists():
        return defaults
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            user_settings: dict[str, Any] = json.load(f)
        return _deep_merge(defaults, user_settings)
    except (json.JSONDecodeError, OSError):
        return defaults


def save_settings(settings: dict[str, Any]) -> None:
    """settings.json에 설정을 저장한다."""
    ensure_workspace()
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
