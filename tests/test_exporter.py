"""exporter 모듈 단위 테스트."""
from __future__ import annotations

import pathlib

from meeting_transcriber.storage.exporter import (
    _format_duration,
    _format_timestamp,
    export_to_markdown,
    export_to_txt,
    save_export,
)


def _sample_transcript() -> dict:
    """테스트용 transcript 딕셔너리를 반환한다."""
    return {
        "version": "1.0",
        "metadata": {
            "title": "Weekly Standup",
            "created_at": "2026-03-25T10:00:00+09:00",
            "duration_seconds": 150.0,
            "languages": ["en", "ko"],
            "source": "microphone",
            "model": "whisper-small",
            "tags": [],
        },
        "segments": [
            {"start": 0.0, "end": 2.5, "text": "Good morning everyone", "language": "en"},
            {"start": 2.5, "end": 5.0, "text": "Let's get started", "language": "en"},
            {"start": 65.0, "end": 68.0, "text": "다음 주제로 넘어갑시다", "language": "ko"},
        ],
    }


# -- 타임스탬프 포맷 --


def test_format_timestamp_short() -> None:
    """1시간 미만은 [MM:SS] 형식인지 확인."""
    assert _format_timestamp(0.0) == "[00:00]"
    assert _format_timestamp(65.0) == "[01:05]"
    assert _format_timestamp(3599.0) == "[59:59]"


def test_format_timestamp_long() -> None:
    """1시간 이상은 [H:MM:SS] 형식인지 확인."""
    assert _format_timestamp(3600.0) == "[1:00:00]"
    assert _format_timestamp(3723.0) == "[1:02:03]"


def test_format_duration() -> None:
    """duration 포맷이 올바른지 확인."""
    assert _format_duration(30.0) == "30s"
    assert _format_duration(150.0) == "2m 30s"
    assert _format_duration(3723.0) == "1h 2m 3s"


# -- Markdown export --


def test_export_markdown_basic() -> None:
    """기본 Markdown export에 제목과 세그먼트가 포함되는지 확인."""
    md = export_to_markdown(_sample_transcript())
    assert "# Weekly Standup" in md
    assert "Good morning everyone" in md
    assert "Let's get started" in md


def test_export_markdown_with_metadata() -> None:
    """메타데이터가 포함되는지 확인."""
    md = export_to_markdown(_sample_transcript(), include_metadata=True)
    assert "**Date**" in md
    assert "2026-03-25" in md
    assert "**Duration**" in md
    assert "2m 30s" in md
    assert "**Languages**" in md
    assert "en, ko" in md


def test_export_markdown_without_metadata() -> None:
    """include_metadata=False일 때 메타데이터가 제외되는지 확인."""
    md = export_to_markdown(_sample_transcript(), include_metadata=False)
    assert "**Date**" not in md
    assert "**Duration**" not in md
    assert "# Weekly Standup" in md
    assert "Good morning everyone" in md


def test_export_markdown_with_timestamps() -> None:
    """타임스탬프가 [MM:SS] 형식으로 포함되는지 확인."""
    md = export_to_markdown(_sample_transcript(), include_timestamps=True)
    assert "[00:00]" in md
    assert "[00:02]" in md
    assert "[01:05]" in md


def test_export_markdown_without_timestamps() -> None:
    """include_timestamps=False일 때 타임스탬프가 제외되는지 확인."""
    md = export_to_markdown(_sample_transcript(), include_timestamps=False)
    assert "[00:00]" not in md
    assert "Good morning everyone" in md


def test_export_markdown_long_duration() -> None:
    """1시간+ transcript의 타임스탬프가 [H:MM:SS] 형식인지 확인."""
    transcript = _sample_transcript()
    transcript["segments"].append(
        {"start": 3700.0, "end": 3705.0, "text": "Wrapping up"}
    )
    md = export_to_markdown(transcript)
    assert "[1:01:40]" in md


# -- TXT export --


def test_export_txt_basic() -> None:
    """기본 TXT export에 제목과 세그먼트가 포함되는지 확인."""
    txt = export_to_txt(_sample_transcript())
    assert "Weekly Standup" in txt
    assert "Good morning everyone" in txt


def test_export_txt_with_timestamps() -> None:
    """TXT에 타임스탬프가 포함되는지 확인."""
    txt = export_to_txt(_sample_transcript(), include_timestamps=True)
    assert "[00:00]" in txt


def test_export_txt_without_timestamps() -> None:
    """include_timestamps=False일 때 타임스탬프가 제외되는지 확인."""
    txt = export_to_txt(_sample_transcript(), include_timestamps=False)
    assert "[00:00]" not in txt
    assert "Good morning everyone" in txt


def test_export_txt_includes_date_and_duration() -> None:
    """TXT에 날짜와 duration이 포함되는지 확인."""
    txt = export_to_txt(_sample_transcript())
    assert "Date:" in txt
    assert "Duration:" in txt


# -- 엣지 케이스 --


def test_export_empty_segments() -> None:
    """빈 세그먼트 transcript를 처리하는지 확인."""
    transcript = {
        "metadata": {"title": "Empty"},
        "segments": [],
    }
    md = export_to_markdown(transcript)
    assert "# Empty" in md

    txt = export_to_txt(transcript)
    assert "Empty" in txt


def test_export_korean_content() -> None:
    """한국어 콘텐츠가 올바르게 처리되는지 확인."""
    transcript = _sample_transcript()
    md = export_to_markdown(transcript)
    assert "다음 주제로 넘어갑시다" in md

    txt = export_to_txt(transcript)
    assert "다음 주제로 넘어갑시다" in txt


# -- save_export --


def test_save_export_creates_file(tmp_path: pathlib.Path) -> None:
    """파일이 생성되는지 확인."""
    content = "# Test\nHello"
    path = tmp_path / "export" / "test.md"
    result = save_export(content, path)

    assert result.exists()
    assert result.read_text(encoding="utf-8") == content


def test_save_export_utf8(tmp_path: pathlib.Path) -> None:
    """UTF-8 인코딩으로 저장되는지 확인."""
    content = "# 회의록\n한국어 테스트"
    path = tmp_path / "test.txt"
    save_export(content, path)

    assert path.read_text(encoding="utf-8") == content
