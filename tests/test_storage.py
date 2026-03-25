"""storage 모듈 단위 테스트."""
from __future__ import annotations

import pathlib

from meeting_transcriber.storage.transcript_store import (
    create_transcript,
    load_transcript,
    save_transcript,
)


def test_create_transcript_schema() -> None:
    """create_transcript이 PRD 스키마를 따르는 딕셔너리를 반환하는지 확인."""
    segments = [
        {"start": 0.0, "end": 2.5, "text": "Hello world", "language": "en", "confidence": 0.95}
    ]
    transcript = create_transcript(
        segments,
        title="Test Meeting",
        languages=["en"],
        source="microphone",
        model="whisper-small",
        duration_seconds=30.0,
    )

    assert transcript["version"] == "1.0"
    assert transcript["metadata"]["title"] == "Test Meeting"
    assert transcript["metadata"]["languages"] == ["en"]
    assert transcript["metadata"]["source"] == "microphone"
    assert transcript["metadata"]["model"] == "whisper-small"
    assert transcript["metadata"]["duration_seconds"] == 30.0
    assert len(transcript["segments"]) == 1
    assert transcript["segments"][0]["text"] == "Hello world"


def test_create_transcript_auto_title() -> None:
    """title이 None일 때 자동 생성되는지 확인."""
    transcript = create_transcript([], languages=["en", "ko"])
    title = transcript["metadata"]["title"]
    assert "en_ko" in title


def test_save_and_load_transcript(tmp_path: pathlib.Path) -> None:
    """transcript를 저장하고 다시 로드했을 때 동일한지 확인."""
    segments = [
        {"start": 0.0, "end": 1.0, "text": "테스트", "language": "ko", "confidence": 0.90}
    ]
    transcript = create_transcript(segments, title="저장 테스트", languages=["ko"])

    file_path = tmp_path / "transcripts" / "test" / "transcript.json"
    saved_path = save_transcript(transcript, file_path)

    assert saved_path.exists()

    loaded = load_transcript(saved_path)
    assert loaded["metadata"]["title"] == "저장 테스트"
    assert loaded["segments"][0]["text"] == "테스트"


def test_save_transcript_creates_parent_dirs(tmp_path: pathlib.Path) -> None:
    """저장 시 부모 디렉토리가 없으면 자동 생성하는지 확인."""
    path = tmp_path / "deep" / "nested" / "dir" / "transcript.json"
    transcript = create_transcript([], title="nested")
    save_transcript(transcript, path)
    assert path.exists()


def test_load_transcript_file_not_found(tmp_path: pathlib.Path) -> None:
    """존재하지 않는 파일 로드 시 FileNotFoundError가 발생하는지 확인."""
    import pytest

    with pytest.raises(FileNotFoundError):
        load_transcript(tmp_path / "nonexistent.json")
