"""transcript 내보내기 — Markdown, TXT 포맷."""
from __future__ import annotations

import pathlib
from typing import Any


def _format_timestamp(seconds: float) -> str:
    """초를 [MM:SS] 또는 [H:MM:SS] 형식으로 변환한다.

    Args:
        seconds: 시간 (초)

    Returns:
        포맷된 타임스탬프 문자열
    """
    total = int(seconds)
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60

    if h > 0:
        return f"[{h}:{m:02d}:{s:02d}]"
    return f"[{m:02d}:{s:02d}]"


def _format_duration(seconds: float) -> str:
    """초를 사람이 읽기 쉬운 형식으로 변환한다.

    Args:
        seconds: 총 시간 (초)

    Returns:
        "Xh Ym Zs" 또는 "Ym Zs" 형식 문자열
    """
    total = int(seconds)
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60

    if h > 0:
        return f"{h}h {m}m {s}s"
    if m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


def export_to_markdown(
    transcript: dict[str, Any],
    *,
    include_metadata: bool = True,
    include_timestamps: bool = True,
    include_ai_results: bool = True,
) -> str:
    """transcript를 Markdown 형식으로 내보낸다.

    Args:
        transcript: transcript.json 스키마를 따르는 딕셔너리
        include_metadata: 메타데이터 헤더 포함 여부
        include_timestamps: 세그먼트 타임스탬프 포함 여부
        include_ai_results: AI 처리 결과(요약, 키워드) 포함 여부

    Returns:
        Markdown 포맷 문자열
    """
    metadata = transcript.get("metadata", {})
    segments = transcript.get("segments", [])

    parts: list[str] = []

    # 제목
    title = metadata.get("title", "Untitled")
    parts.append(f"# {title}")
    parts.append("")

    # 메타데이터
    if include_metadata:
        created = metadata.get("created_at", "")
        if created:
            parts.append(f"- **Date**: {created}")

        duration = metadata.get("duration_seconds", 0)
        if duration:
            parts.append(f"- **Duration**: {_format_duration(duration)}")

        languages = metadata.get("languages", [])
        if languages:
            parts.append(f"- **Languages**: {', '.join(languages)}")

        parts.append("")

    # AI 결과
    if include_ai_results:
        summary = metadata.get("summary", "")
        if summary:
            parts.append("## Summary")
            parts.append("")
            parts.append(summary)
            parts.append("")

        tags = metadata.get("tags", [])
        if tags:
            parts.append(f"**Keywords**: {', '.join(tags)}")
            parts.append("")

    parts.append("---")
    parts.append("")

    # 세그먼트
    for seg in segments:
        text = seg.get("text", "")
        if not text:
            continue

        if include_timestamps:
            start = seg.get("start", 0.0)
            parts.append(f"{_format_timestamp(start)} {text}")
        else:
            parts.append(text)

    parts.append("")
    return "\n".join(parts)


def export_to_txt(
    transcript: dict[str, Any],
    *,
    include_timestamps: bool = True,
    include_ai_results: bool = True,
) -> str:
    """transcript를 플레인 텍스트 형식으로 내보낸다.

    Args:
        transcript: transcript.json 스키마를 따르는 딕셔너리
        include_timestamps: 세그먼트 타임스탬프 포함 여부
        include_ai_results: AI 처리 결과(요약, 키워드) 포함 여부

    Returns:
        플레인 텍스트 문자열
    """
    metadata = transcript.get("metadata", {})
    segments = transcript.get("segments", [])

    parts: list[str] = []

    title = metadata.get("title", "Untitled")
    parts.append(title)

    created = metadata.get("created_at", "")
    if created:
        parts.append(f"Date: {created}")

    duration = metadata.get("duration_seconds", 0)
    if duration:
        parts.append(f"Duration: {_format_duration(duration)}")

    parts.append("")

    # AI 결과
    if include_ai_results:
        summary = metadata.get("summary", "")
        if summary:
            parts.append("Summary:")
            parts.append(summary)
            parts.append("")

        tags = metadata.get("tags", [])
        if tags:
            parts.append(f"Keywords: {', '.join(tags)}")
            parts.append("")

    # 세그먼트
    for seg in segments:
        text = seg.get("text", "")
        if not text:
            continue

        if include_timestamps:
            start = seg.get("start", 0.0)
            parts.append(f"{_format_timestamp(start)} {text}")
        else:
            parts.append(text)

    parts.append("")
    return "\n".join(parts)


def save_export(content: str, path: pathlib.Path) -> pathlib.Path:
    """내보낸 콘텐츠를 파일로 저장한다.

    Args:
        content: 저장할 텍스트 콘텐츠
        path: 저장 경로

    Returns:
        저장된 파일 경로
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path
