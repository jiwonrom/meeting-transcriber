"""오디오 파일 검증 및 임포트."""
from __future__ import annotations

import pathlib
import wave

from meeting_transcriber.utils.constants import SUPPORTED_AUDIO_FORMATS
from meeting_transcriber.utils.exceptions import AudioFormatError


def validate_audio_file(path: pathlib.Path) -> pathlib.Path:
    """오디오 파일의 존재 여부와 포맷을 검증한다.

    Args:
        path: 검증할 오디오 파일 경로

    Returns:
        검증된 파일 경로 (pass-through)

    Raises:
        FileNotFoundError: 파일이 존재하지 않을 때
        AudioFormatError: 지원하지 않는 포맷일 때
    """
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_AUDIO_FORMATS:
        supported = ", ".join(SUPPORTED_AUDIO_FORMATS)
        raise AudioFormatError(
            f"Unsupported audio format '{suffix}'. Supported: {supported}"
        )

    return path


def get_audio_duration(path: pathlib.Path) -> float:
    """오디오 파일의 길이(초)를 반환한다.

    WAV 파일만 정확한 길이를 반환하며, 다른 포맷은 0.0을 반환한다.

    Args:
        path: 오디오 파일 경로

    Returns:
        오디오 길이 (초). WAV가 아니면 0.0.
    """
    if path.suffix.lower() != ".wav":
        return 0.0

    try:
        with wave.open(str(path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            if rate == 0:
                return 0.0
            return frames / rate
    except wave.Error:
        return 0.0
