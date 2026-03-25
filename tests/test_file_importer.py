"""file_importer 모듈 단위 테스트."""
from __future__ import annotations

import pathlib
import struct
import wave

import pytest

from meeting_transcriber.core.file_importer import get_audio_duration, validate_audio_file
from meeting_transcriber.utils.exceptions import AudioFormatError


def test_validate_audio_file_wav(tmp_path: pathlib.Path) -> None:
    """유효한 .wav 파일이 통과하는지 확인."""
    wav = tmp_path / "test.wav"
    wav.write_bytes(b"fake wav")
    result = validate_audio_file(wav)
    assert result == wav


def test_validate_audio_file_mp3(tmp_path: pathlib.Path) -> None:
    """유효한 .mp3 파일이 통과하는지 확인."""
    mp3 = tmp_path / "test.mp3"
    mp3.write_bytes(b"fake mp3")
    assert validate_audio_file(mp3) == mp3


def test_validate_audio_file_m4a(tmp_path: pathlib.Path) -> None:
    """유효한 .m4a 파일이 통과하는지 확인."""
    m4a = tmp_path / "test.m4a"
    m4a.write_bytes(b"fake m4a")
    assert validate_audio_file(m4a) == m4a


def test_validate_audio_file_unsupported(tmp_path: pathlib.Path) -> None:
    """지원하지 않는 포맷에 AudioFormatError를 발생시키는지 확인."""
    txt = tmp_path / "test.txt"
    txt.write_bytes(b"not audio")
    with pytest.raises(AudioFormatError, match="Unsupported audio format"):
        validate_audio_file(txt)


def test_validate_audio_file_missing(tmp_path: pathlib.Path) -> None:
    """존재하지 않는 파일에 FileNotFoundError를 발생시키는지 확인."""
    with pytest.raises(FileNotFoundError):
        validate_audio_file(tmp_path / "nonexistent.wav")


def _create_wav(path: pathlib.Path, duration_sec: float, sample_rate: int = 16000) -> None:
    """테스트용 WAV 파일을 생성한다."""
    n_frames = int(duration_sec * sample_rate)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{n_frames}h", *([0] * n_frames)))


def test_get_audio_duration_wav(tmp_path: pathlib.Path) -> None:
    """WAV 파일의 duration을 정확히 계산하는지 확인."""
    wav = tmp_path / "test.wav"
    _create_wav(wav, duration_sec=3.0)
    duration = get_audio_duration(wav)
    assert abs(duration - 3.0) < 0.01


def test_get_audio_duration_non_wav(tmp_path: pathlib.Path) -> None:
    """WAV가 아닌 파일은 0.0을 반환하는지 확인."""
    mp3 = tmp_path / "test.mp3"
    mp3.write_bytes(b"fake mp3")
    assert get_audio_duration(mp3) == 0.0


def test_get_audio_duration_invalid_wav(tmp_path: pathlib.Path) -> None:
    """손상된 WAV 파일은 0.0을 반환하는지 확인."""
    bad_wav = tmp_path / "bad.wav"
    bad_wav.write_bytes(b"not a real wav file")
    assert get_audio_duration(bad_wav) == 0.0
