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
    segments = [{"start": 0.0, "end": 1.0, "text": "테스트", "language": "ko", "confidence": 0.90}]
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


# ============================================================
# Schema v2.0 테스트
# ============================================================


def test_create_transcript_v2_with_speakers() -> None:
    """speakers 파라미터 제공 시 version 2.0과 speakers 메타데이터 생성 확인."""
    from meeting_transcriber.storage.transcript_store import update_transcript_speakers

    segments = [{"start": 0.0, "end": 5.0, "text": "Hello", "speaker": "SPEAKER_00"}]
    speakers = {"SPEAKER_00": "Alice"}
    transcript = create_transcript(
        segments,
        title="V2 Test",
        speakers=speakers,
        diarization_meta={"model": "pyannote/speaker-diarization-community-1"},
    )
    assert transcript["version"] == "2.0"
    assert transcript["metadata"]["speakers"] == {"SPEAKER_00": "Alice"}
    assert transcript["metadata"]["diarization"]["model"] == "pyannote/speaker-diarization-community-1"


def test_create_transcript_v1_without_speakers() -> None:
    """speakers 파라미터 없이 호출 시 version 1.0 유지 확인."""
    transcript = create_transcript(
        [{"start": 0.0, "end": 1.0, "text": "Hi"}],
        title="V1 Test",
    )
    assert transcript["version"] == "1.0"
    assert "speakers" not in transcript["metadata"]
    assert "diarization" not in transcript["metadata"]


def test_load_v1_transcript_no_speaker_key(tmp_path: pathlib.Path) -> None:
    """v1.0 파일 로드 시 세그먼트에 speaker 키가 없는 것 확인 (마이그레이션 없음)."""
    transcript = create_transcript(
        [{"start": 0.0, "end": 2.0, "text": "Old recording"}],
        title="V1",
    )
    path = tmp_path / "v1.json"
    save_transcript(transcript, path)

    loaded = load_transcript(path)
    assert loaded["version"] == "1.0"
    assert "speaker" not in loaded["segments"][0]


def test_load_v2_transcript_preserves_speakers(tmp_path: pathlib.Path) -> None:
    """v2.0 파일 로드 시 speaker 필드 보존 확인."""
    transcript = create_transcript(
        [{"start": 0.0, "end": 5.0, "text": "Hello", "speaker": "Alice"}],
        title="V2",
        speakers={"SPEAKER_00": "Alice"},
    )
    path = tmp_path / "v2.json"
    save_transcript(transcript, path)

    loaded = load_transcript(path)
    assert loaded["version"] == "2.0"
    assert loaded["segments"][0]["speaker"] == "Alice"
    assert loaded["metadata"]["speakers"] == {"SPEAKER_00": "Alice"}


def test_save_load_roundtrip_v2(tmp_path: pathlib.Path) -> None:
    """v2.0 save + load 라운드트립에서 화자 데이터 보존 확인."""
    segments = [
        {"start": 0.0, "end": 5.0, "text": "Hi", "speaker": "SPEAKER_00"},
        {"start": 5.0, "end": 10.0, "text": "Bye", "speaker": "SPEAKER_01"},
    ]
    speakers = {"SPEAKER_00": "Alice", "SPEAKER_01": "Bob"}
    transcript = create_transcript(segments, title="Roundtrip", speakers=speakers)

    path = tmp_path / "roundtrip.json"
    save_transcript(transcript, path)
    loaded = load_transcript(path)

    assert loaded["version"] == "2.0"
    assert loaded["segments"][0]["speaker"] == "SPEAKER_00"
    assert loaded["segments"][1]["speaker"] == "SPEAKER_01"
    assert loaded["metadata"]["speakers"] == speakers


def test_update_transcript_speakers(tmp_path: pathlib.Path) -> None:
    """update_transcript_speakers로 기존 transcript에 화자 정보 업데이트 확인."""
    from meeting_transcriber.storage.transcript_store import update_transcript_speakers

    # v1.0 transcript 생성 및 저장
    transcript = create_transcript(
        [{"start": 0.0, "end": 5.0, "text": "Hello"}],
        title="Update Test",
    )
    path = tmp_path / "update.json"
    save_transcript(transcript, path)

    # 화자 정보 업데이트
    new_segments = [{"start": 0.0, "end": 5.0, "text": "Hello", "speaker": "SPEAKER_00"}]
    speakers = {"SPEAKER_00": "SPEAKER_00"}
    diarization_meta = {"model": "pyannote/speaker-diarization-community-1"}

    updated = update_transcript_speakers(path, new_segments, speakers, diarization_meta)
    assert updated["version"] == "2.0"
    assert updated["segments"][0]["speaker"] == "SPEAKER_00"
    assert updated["metadata"]["speakers"] == speakers
    assert updated["metadata"]["diarization"] == diarization_meta

    # 파일도 업데이트 되었는지 확인
    reloaded = load_transcript(path)
    assert reloaded["version"] == "2.0"
