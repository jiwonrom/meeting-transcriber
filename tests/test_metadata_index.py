"""MetadataIndex CRUD 테스트."""

from __future__ import annotations

import json
import pathlib

from meeting_transcriber.storage.metadata_index import MetadataIndex


def test_create_empty_index(tmp_path: pathlib.Path) -> None:
    """빈 디렉토리에서 MetadataIndex 생성 시 version 1.0, 빈 entries."""
    idx = MetadataIndex(tmp_path)
    index_file = tmp_path / "index.json"
    assert index_file.exists()
    data = json.loads(index_file.read_text())
    assert data["version"] == "1.0"
    assert data["entries"] == {}


def test_update_entry(tmp_path: pathlib.Path) -> None:
    """transcript를 추가하면 올바른 필드가 인덱싱된다."""
    idx = MetadataIndex(tmp_path)

    # 트랜스크립트 파일 생성
    folder = tmp_path / "Work" / "rec_001"
    folder.mkdir(parents=True)
    transcript_path = folder / "transcript.json"
    transcript = {
        "metadata": {
            "title": "Sprint Review",
            "created_at": "2026-01-01T00:00:00Z",
            "duration_seconds": 120.0,
            "language": "en",
            "keywords": ["sprint", "review"],
            "summary": "A summary of the sprint review meeting.",
        },
        "segments": [
            {"text": "Hello world"},
            {"text": "Good morning everyone"},
        ],
    }
    transcript_path.write_text(json.dumps(transcript))
    idx.update_entry(transcript_path, transcript)

    entry = idx.get_entry(transcript_path)
    assert entry is not None
    assert entry["title"] == "Sprint Review"
    assert entry["segment_count"] == 2
    assert entry["word_count"] == 5  # "Hello world" + "Good morning everyone"
    assert entry["duration_seconds"] == 120.0
    assert entry["languages"] == ["en"]
    assert entry["keywords"] == ["sprint", "review"]


def test_remove_entry(tmp_path: pathlib.Path) -> None:
    """엔트리 추가 후 삭제하면 None을 반환한다."""
    idx = MetadataIndex(tmp_path)

    folder = tmp_path / "Work" / "rec_002"
    folder.mkdir(parents=True)
    transcript_path = folder / "transcript.json"
    transcript = {
        "metadata": {"title": "Test"},
        "segments": [],
    }
    transcript_path.write_text(json.dumps(transcript))
    idx.update_entry(transcript_path, transcript)
    assert idx.get_entry(transcript_path) is not None

    idx.remove_entry(transcript_path)
    assert idx.get_entry(transcript_path) is None


def test_rebuild(tmp_path: pathlib.Path) -> None:
    """rebuild는 워크스페이스의 모든 transcript.json을 스캔한다."""
    # 2개의 transcript 생성
    for i in range(2):
        folder = tmp_path / f"Folder{i}" / f"rec_{i}"
        folder.mkdir(parents=True)
        transcript = {
            "metadata": {"title": f"Meeting {i}"},
            "segments": [{"text": "hello"}],
        }
        (folder / "transcript.json").write_text(json.dumps(transcript))

    idx = MetadataIndex(tmp_path)
    idx.rebuild(tmp_path)
    entries = idx.entries()
    assert len(entries) == 2


def test_corrupted_index_recovery(tmp_path: pathlib.Path) -> None:
    """손상된 index.json에서 복구하여 빈 entries를 생성한다."""
    index_file = tmp_path / "index.json"
    index_file.write_text("NOT VALID JSON {{{")

    idx = MetadataIndex(tmp_path)
    assert idx.entries() == {}
    # 파일이 올바르게 복구되었는지 확인
    data = json.loads(index_file.read_text())
    assert data["version"] == "1.0"
