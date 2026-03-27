"""config 모듈 단위 테스트."""
from __future__ import annotations

import json
from unittest.mock import patch

from meeting_transcriber.utils.config import (
    invalidate_settings_cache,
    load_settings,
    save_settings,
)


def test_load_settings_returns_defaults_when_no_file(tmp_path: object) -> None:
    """settings.json이 없을 때 기본값을 반환하는지 확인."""
    invalidate_settings_cache()
    fake_path = tmp_path / "nonexistent" / "settings.json"  # type: ignore[operator]
    with patch("meeting_transcriber.utils.config.SETTINGS_FILE", fake_path):
        settings = load_settings()
    invalidate_settings_cache()

    assert settings["language"] == "auto"
    assert settings["whisper_model"] == "small"
    assert settings["overlay"]["lines"] == 2
    assert settings["theme"] == "system"


def test_save_and_load_settings_roundtrip(tmp_path: object) -> None:
    """설정을 저장하고 다시 로드했을 때 동일한지 확인."""
    import pathlib

    invalidate_settings_cache()
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
    invalidate_settings_cache()


def test_settings_cache_returns_same_object(tmp_path: object) -> None:
    """캐시된 설정이 디스크를 다시 읽지 않는지 확인."""
    import pathlib

    invalidate_settings_cache()
    workspace = pathlib.Path(str(tmp_path)) / ".meeting_transcriber"
    settings_file = workspace / "settings.json"

    with (
        patch("meeting_transcriber.utils.config.DEFAULT_WORKSPACE_DIR", workspace),
        patch("meeting_transcriber.utils.config.SETTINGS_FILE", settings_file),
    ):
        # 첫 번째 호출: 디스크 읽기 (파일 없으므로 기본값)
        s1 = load_settings()
        # 두 번째 호출: 캐시에서 반환 (같은 객체)
        s2 = load_settings()
        assert s1 is s2

        # save 후 캐시 갱신 확인
        s1["language"] = "ja"
        save_settings(s1)
        s3 = load_settings()
        assert s3["language"] == "ja"
    invalidate_settings_cache()
