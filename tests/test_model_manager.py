"""model_manager 모듈 단위 테스트."""
from __future__ import annotations

import pathlib
from unittest.mock import patch

import pytest

from meeting_transcriber.core.model_manager import (
    download_model,
    get_model_path,
    is_model_downloaded,
    list_available_models,
)
from meeting_transcriber.utils.constants import MODELS_DIR, WHISPER_MODELS
from meeting_transcriber.utils.exceptions import ModelDownloadError, WhisperModelNotFoundError


def test_get_model_path_valid() -> None:
    """유효한 모델 이름에 대해 올바른 경로를 반환하는지 확인."""
    for name, filename in WHISPER_MODELS.items():
        path = get_model_path(name)
        assert path == MODELS_DIR / filename


def test_get_model_path_invalid() -> None:
    """알 수 없는 모델 이름에 WhisperModelNotFoundError를 발생시키는지 확인."""
    with pytest.raises(WhisperModelNotFoundError, match="Unknown model"):
        get_model_path("nonexistent-model")


def test_is_model_downloaded_true(tmp_path: pathlib.Path) -> None:
    """모델 파일이 존재할 때 True를 반환하는지 확인."""
    fake_model = tmp_path / "ggml-small.bin"
    fake_model.write_bytes(b"fake model data")

    with patch("meeting_transcriber.core.model_manager.MODELS_DIR", tmp_path):
        assert is_model_downloaded("small") is True


def test_is_model_downloaded_false(tmp_path: pathlib.Path) -> None:
    """모델 파일이 없을 때 False를 반환하는지 확인."""
    with patch("meeting_transcriber.core.model_manager.MODELS_DIR", tmp_path):
        assert is_model_downloaded("small") is False


def test_is_model_downloaded_empty_file(tmp_path: pathlib.Path) -> None:
    """모델 파일이 비어있을 때 False를 반환하는지 확인."""
    fake_model = tmp_path / "ggml-small.bin"
    fake_model.write_bytes(b"")

    with patch("meeting_transcriber.core.model_manager.MODELS_DIR", tmp_path):
        assert is_model_downloaded("small") is False


def test_list_available_models(tmp_path: pathlib.Path) -> None:
    """모든 모델 정보를 정확히 반환하는지 확인."""
    (tmp_path / "ggml-small.bin").write_bytes(b"x" * 100)

    with patch("meeting_transcriber.core.model_manager.MODELS_DIR", tmp_path):
        models = list_available_models()

    assert len(models) == len(WHISPER_MODELS)
    names = {m["name"] for m in models}
    assert names == set(WHISPER_MODELS.keys())

    small = next(m for m in models if m["name"] == "small")
    assert small["downloaded"] is True
    assert small["size_bytes"] == 100


def test_download_model_success(tmp_path: pathlib.Path) -> None:
    """모델 다운로드가 성공하면 파일이 생성되는지 확인."""
    model_dir = tmp_path / "models"
    model_dir.mkdir()

    def fake_urlretrieve(url: str, path: pathlib.Path, reporthook: object = None) -> None:
        pathlib.Path(path).write_bytes(b"fake model content")

    progress_calls: list[tuple[int, int]] = []

    with (
        patch("meeting_transcriber.core.model_manager.MODELS_DIR", model_dir),
        patch("meeting_transcriber.core.model_manager.ensure_workspace"),
        patch("urllib.request.urlretrieve", side_effect=fake_urlretrieve),
    ):
        def callback(downloaded: int, total: int) -> None:
            progress_calls.append((downloaded, total))

        result = download_model("small", progress_callback=callback)

    assert result.exists()
    assert result.name == "ggml-small.bin"


def test_download_model_failure(tmp_path: pathlib.Path) -> None:
    """다운로드 실패 시 ModelDownloadError를 발생시키고 .part 파일을 정리하는지 확인."""
    model_dir = tmp_path / "models"
    model_dir.mkdir()

    with (
        patch("meeting_transcriber.core.model_manager.MODELS_DIR", model_dir),
        patch("meeting_transcriber.core.model_manager.ensure_workspace"),
        patch("urllib.request.urlretrieve", side_effect=OSError("Network error")),
    ):
        with pytest.raises(ModelDownloadError, match="Network error"):
            download_model("small")

    part_file = model_dir / "ggml-small.part"
    assert not part_file.exists()
