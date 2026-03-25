"""config 모듈 단위 테스트."""
from __future__ import annotations

import json
from unittest.mock import patch

from meeting_transcriber.utils.config import load_settings, save_settings


def test_load_settings_returns_defaults_when_no_file(tmp_path: object) -> None:
    """settings.json이 없을 때 기본값을 반환하는지 확인."""
    fake_path = tmp_path / "nonexistent" / "settings.json"  # type: ignore[operator]
    with patch("meeting_transcriber.utils.config.SETTINGS_FILE", fake_path):
        settings = load_settings()

    assert settings["language"] == "auto"
    assert settings["whisper_model"] == "small"
    assert settings["overlay"]["lines"] == 2
    assert settings["theme"] == "system"


def test_save_and_load_settings_roundtrip(tmp_path: object) -> None:
    """설정을 저장하고 다시 로드했을 때 동일한지 확인."""
    import pathlib

    workspace = pathlib.Path(str(tmp_path)) / ".meeting_transcriber"
    settings_file = workspace / "settings.json"

    with (
        patch("meeting_transcriber.utils.config.DEFAULT_WORKSPACE_DIR", workspace),
        patch("meeting_transcriber.utils.config.SETTINGS_FILE", settings_file),
    ):
        original = {"language": "ko", "whisper_model": "medium", "theme": "dark"}
        save_settings(original)

        assert settings_file.exists()
        loaded = json.loads(settings_file.read_text(encoding="utf-8"))
        assert loaded["language"] == "ko"
        assert loaded["whisper_model"] == "medium"
