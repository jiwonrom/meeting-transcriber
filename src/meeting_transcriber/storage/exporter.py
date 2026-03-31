"""transcript 내보내기 — Markdown, TXT, SRT, VTT, Obsidian 포맷."""

from __future__ import annotations

import pathlib
import re
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


def _format_summary_for_export(summary: str | dict[str, Any]) -> str:
    """요약 데이터를 내보내기용 문자열로 변환한다.

    str이면 그대로 반환하고, dict이면 섹션별 Markdown으로 포맷한다.

    Args:
        summary: 요약 텍스트 또는 구조화된 dict

    Returns:
        포맷된 문자열
    """
    if isinstance(summary, dict):
        parts: list[str] = []
        for key, items in summary.items():
            label = key.replace("_", " ").title()
            parts.append(f"### {label}")
            if isinstance(items, list):
                for item in items:
                    parts.append(f"- {item}")
            else:
                parts.append(str(items))
            parts.append("")
        return "\n".join(parts)
    return str(summary) if summary else ""


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
            formatted = _format_summary_for_export(summary)
            parts.append(formatted)
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
            formatted = _format_summary_for_export(summary)
            parts.append(formatted)
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


# ============================================================
# SRT / VTT subtitle export
# ============================================================


def _format_srt_timestamp(seconds: float) -> str:
    """초를 SRT 타임스탬프 형식(HH:MM:SS,mmm)으로 변환한다.

    Args:
        seconds: 시간 (초)

    Returns:
        "HH:MM:SS,mmm" 형식 문자열 (쉼표 구분)
    """
    total_ms = int(seconds * 1000)
    h = total_ms // 3_600_000
    m = (total_ms % 3_600_000) // 60_000
    s = (total_ms % 60_000) // 1000
    ms = total_ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _format_vtt_timestamp(seconds: float) -> str:
    """초를 VTT 타임스탬프 형식(HH:MM:SS.mmm)으로 변환한다.

    Args:
        seconds: 시간 (초)

    Returns:
        "HH:MM:SS.mmm" 형식 문자열 (마침표 구분)
    """
    total_ms = int(seconds * 1000)
    h = total_ms // 3_600_000
    m = (total_ms % 3_600_000) // 60_000
    s = (total_ms % 60_000) // 1000
    ms = total_ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def export_to_srt(
    transcript: dict[str, Any],
    *,
    include_speaker: bool = True,
) -> str:
    """transcript를 SRT 자막 형식으로 내보낸다.

    Args:
        transcript: transcript.json 스키마를 따르는 딕셔너리
        include_speaker: 화자 라벨 포함 여부

    Returns:
        SRT 포맷 문자열 (빈 세그먼트일 경우 빈 문자열)
    """
    segments = transcript.get("segments", [])
    if not segments:
        return ""

    entries: list[str] = []
    for i, seg in enumerate(segments, start=1):
        text = seg.get("text", "")
        if not text:
            continue

        start = _format_srt_timestamp(seg.get("start", 0.0))
        end = _format_srt_timestamp(seg.get("end", 0.0))

        speaker = seg.get("speaker", "")
        if include_speaker and speaker:
            text = f"{speaker}: {text}"

        entries.append(f"{i}\n{start} --> {end}\n{text}\n")

    return "\n".join(entries)


def export_to_vtt(
    transcript: dict[str, Any],
    *,
    include_speaker: bool = True,
) -> str:
    """transcript를 WebVTT 자막 형식으로 내보낸다.

    Args:
        transcript: transcript.json 스키마를 따르는 딕셔너리
        include_speaker: 화자 라벨 포함 여부

    Returns:
        WebVTT 포맷 문자열 (WEBVTT 헤더 포함)
    """
    segments = transcript.get("segments", [])

    entries: list[str] = []
    for i, seg in enumerate(segments, start=1):
        text = seg.get("text", "")
        if not text:
            continue

        start = _format_vtt_timestamp(seg.get("start", 0.0))
        end = _format_vtt_timestamp(seg.get("end", 0.0))

        speaker = seg.get("speaker", "")
        if include_speaker and speaker:
            text = f"{speaker}: {text}"

        entries.append(f"{i}\n{start} --> {end}\n{text}\n")

    return "WEBVTT\n\n" + "\n".join(entries)


# ============================================================
# Obsidian Markdown export
# ============================================================


def export_to_obsidian(transcript: dict[str, Any]) -> str:
    """transcript를 Obsidian 호환 Markdown으로 내보낸다.

    YAML frontmatter에 title, date, duration, languages, tags, source를 포함하고,
    본문에 AI 결과와 타임스탬프 세그먼트를 포함한다.

    Args:
        transcript: transcript.json 스키마를 따르는 딕셔너리

    Returns:
        Obsidian 호환 Markdown 문자열
    """
    metadata = transcript.get("metadata", {})
    segments = transcript.get("segments", [])

    parts: list[str] = []

    # YAML frontmatter
    title = metadata.get("title", "Untitled")
    created_at = metadata.get("created_at", "")
    date = created_at[:10] if created_at else ""
    duration = int(metadata.get("duration_seconds", 0))
    languages = metadata.get("languages", [])
    tags = metadata.get("tags", [])
    source = metadata.get("source", "")

    parts.append("---")
    parts.append(f'title: "{title}"')
    parts.append(f"date: {date}")
    parts.append(f"duration: {duration}")
    parts.append(f"languages: [{', '.join(languages)}]")
    parts.append(f"tags: [{', '.join(tags)}]")
    parts.append(f"source: {source}")
    parts.append("---")
    parts.append("")

    # 제목
    parts.append(f"# {title}")
    parts.append("")

    # 메타데이터 요약
    if date:
        parts.append(f"- **Date**: {date}")
    if duration:
        parts.append(f"- **Duration**: {_format_duration(float(duration))}")
    if languages:
        parts.append(f"- **Languages**: {', '.join(languages)}")
    parts.append("")

    # AI 결과
    summary = metadata.get("summary", "")
    if summary:
        parts.append("## Summary")
        parts.append("")
        formatted = _format_summary_for_export(summary)
        parts.append(formatted)
        parts.append("")

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
        start = seg.get("start", 0.0)
        parts.append(f"{_format_timestamp(start)} {text}")

    parts.append("")
    return "\n".join(parts)


def export_analysis_to_markdown(analysis: dict[str, Any]) -> str:
    """교차 회의 분석 결과를 Markdown으로 변환한다.

    Args:
        analysis: 분석 결과 딕셔너리 (result, transcript_paths, created_at 등)

    Returns:
        Markdown 형식 문자열
    """
    parts: list[str] = []
    created = analysis.get("created_at", "")[:10]
    count = analysis.get("transcript_count", 0)
    parts.append("# Cross-Meeting Analysis")
    parts.append(f"\n**Date:** {created}")
    parts.append(f"**Transcripts analyzed:** {count}\n")

    result = analysis.get("result", {})

    # Recurring Topics
    topics = result.get("recurring_topics", [])
    if topics:
        parts.append("## Recurring Topics\n")
        for t in topics:
            name = t.get("name", "")
            freq = t.get("frequency", 0)
            meetings = ", ".join(t.get("meetings", []))
            parts.append(f"### {name} ({freq}x)\n")
            parts.append(f"Meetings: {meetings}\n")

    # Action Items
    items = result.get("action_items", [])
    if items:
        parts.append("## Action Items\n")
        for item in items:
            status = item.get("status", "unresolved")
            checkbox = "[x]" if status == "resolved" else "[ ]"
            text = item.get("item", "")
            assignee = item.get("assignee", "")
            meeting = item.get("meeting", "")
            line = f"- {checkbox} {text}"
            if assignee:
                line += f" (@{assignee})"
            if meeting:
                line += f" -- {meeting}"
            parts.append(line)
        parts.append("")

    # Timeline
    timeline = result.get("timeline", [])
    if timeline:
        parts.append("## Timeline\n")
        for entry in timeline:
            date = entry.get("date", "")
            meeting = entry.get("meeting", "")
            topic = entry.get("topic", "")
            detail = entry.get("detail", "")
            parts.append(f"- **{date}** [{meeting}] {topic}: {detail}")
        parts.append("")

    # Custom answer
    custom = result.get("custom_answer", "")
    if custom:
        query = analysis.get("custom_query", "")
        parts.append("## Custom Query\n")
        if query:
            parts.append(f"**Q:** {query}\n")
        parts.append(f"**A:** {custom}\n")

    return "\n".join(parts)


def obsidian_filename(transcript: dict[str, Any]) -> str:
    """Obsidian 호환 파일명을 생성한다.

    {YYYY-MM-DD}_{sanitized_title}.md 형식으로 반환한다.
    파일시스템 비안전 문자(/ \\ | # ^ [ ])를 제거한다.

    Args:
        transcript: transcript.json 스키마를 따르는 딕셔너리

    Returns:
        안전한 파일명 문자열
    """
    metadata = transcript.get("metadata", {})
    created_at = metadata.get("created_at", "")
    date = created_at[:10] if created_at else "unknown"
    title = metadata.get("title", "Untitled")

    # 비안전 문자 제거
    safe_title = re.sub(r"[/\\|#\^{}\[\]]", "", title)
    # 공백을 언더스코어로 변환
    safe_title = safe_title.replace(" ", "_")
    # 연속 언더스코어 정리
    safe_title = re.sub(r"_+", "_", safe_title)
    # 길이 제한
    safe_title = safe_title[:100]

    return f"{date}_{safe_title}.md"
