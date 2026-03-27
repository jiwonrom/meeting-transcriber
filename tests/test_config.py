"""config 모듈 단위 테스트."""
from __future__ import annotations

import json
from unittest.mock import patch

from meeting_transcriber.utils.config import _default_settings, load_settings, save_settings


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


def test_default_settings_has_export_keys() -> None:
    """기본 설정에 export 키가 포함되는지 확인."""
    defaults = _default_settings()
    assert "export" in defaults
    assert defaults["export"]["default_dir"] == ""
    assert defaults["export"]["obsidian_vault"] == ""


def test_default_settings_has_ai_keys() -> None:
    """기본 설정에 ai 키가 포함되는지 확인."""
    defaults = _default_settings()
    assert "ai" in defaults
    assert defaults["ai"]["default_provider"] == "gemini"
    assert defaults["ai"]["task_overrides"] == {}


def test_deep_merge_preserves_new_defaults(tmp_path: object) -> None:
    """export/ai 키 없는 기존 설정 로드 시 기본값이 보존되는지 확인."""
    import pathlib

    workspace = pathlib.Path(str(tmp_path)) / ".meeting_transcriber"
    settings_file = workspace / "settings.json"
    workspace.mkdir(parents=True, exist_ok=True)

    # export/ai 키 없는 기존 설정 저장
    old_settings = {"language": "ko", "whisper_model": "medium"}
    settings_file.write_text(json.dumps(old_settings), encoding="utf-8")

    with patch("meeting_transcriber.utils.config.SETTINGS_FILE", settings_file):
        loaded = load_settings()

    # 기존 값 유지
    assert loaded["language"] == "ko"
    # 새 기본값 보존
    assert loaded["export"]["default_dir"] == ""
    assert loaded["export"]["obsidian_vault"] == ""
    assert loaded["ai"]["default_provider"] == "gemini"
    assert loaded["ai"]["task_overrides"] == {}
