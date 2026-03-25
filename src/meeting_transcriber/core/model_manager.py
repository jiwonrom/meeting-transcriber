"""Whisper 모델 파일 관리 — 경로 확인, 다운로드, 목록."""
from __future__ import annotations

import pathlib
import urllib.request
from collections.abc import Callable
from typing import Any

from meeting_transcriber.utils.config import ensure_workspace
from meeting_transcriber.utils.constants import MODELS_DIR, WHISPER_MODELS
from meeting_transcriber.utils.exceptions import ModelDownloadError, WhisperModelNotFoundError

_HF_BASE_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main"


def get_model_path(model_name: str) -> pathlib.Path:
    """모델 이름에 해당하는 파일 경로를 반환한다.

    Args:
        model_name: 모델 이름 ("small", "medium", "large-v3")

    Returns:
        모델 파일의 전체 경로

    Raises:
        WhisperModelNotFoundError: 알 수 없는 모델 이름일 때
    """
    filename = WHISPER_MODELS.get(model_name)
    if filename is None:
        available = ", ".join(sorted(WHISPER_MODELS.keys()))
        raise WhisperModelNotFoundError(
            f"Unknown model '{model_name}'. Available: {available}"
        )
    return MODELS_DIR / filename


def is_model_downloaded(model_name: str) -> bool:
    """모델 파일이 다운로드되어 있는지 확인한다.

    Args:
        model_name: 모델 이름

    Returns:
        모델 파일이 존재하고 크기가 0보다 크면 True
    """
    path = get_model_path(model_name)
    return path.exists() and path.stat().st_size > 0


def list_available_models() -> list[dict[str, Any]]:
    """사용 가능한 모든 모델의 정보를 반환한다.

    Returns:
        모델 정보 딕셔너리 리스트 (name, filename, downloaded, size_bytes)
    """
    models = []
    for name, filename in sorted(WHISPER_MODELS.items()):
        path = MODELS_DIR / filename
        downloaded = path.exists() and path.stat().st_size > 0
        size_bytes = path.stat().st_size if downloaded else None
        models.append({
            "name": name,
            "filename": filename,
            "downloaded": downloaded,
            "size_bytes": size_bytes,
        })
    return models


def download_model(
    model_name: str,
    progress_callback: Callable[[int, int], None] | None = None,
) -> pathlib.Path:
    """HuggingFace에서 모델을 다운로드한다.

    Args:
        model_name: 다운로드할 모델 이름
        progress_callback: 진행률 콜백 (downloaded_bytes, total_bytes)

    Returns:
        다운로드된 모델 파일 경로

    Raises:
        WhisperModelNotFoundError: 알 수 없는 모델 이름일 때
        ModelDownloadError: 다운로드 실패 시
    """
    model_path = get_model_path(model_name)
    filename = WHISPER_MODELS[model_name]
    url = f"{_HF_BASE_URL}/{filename}"

    ensure_workspace()
    part_path = model_path.with_suffix(".part")

    def _reporthook(block_num: int, block_size: int, total_size: int) -> None:
        if progress_callback is not None:
            downloaded = block_num * block_size
            progress_callback(min(downloaded, total_size), total_size)

    try:
        urllib.request.urlretrieve(url, part_path, reporthook=_reporthook)
        part_path.rename(model_path)
    except Exception as e:
        part_path.unlink(missing_ok=True)
        raise ModelDownloadError(f"Failed to download model '{model_name}': {e}") from e

    return model_path
