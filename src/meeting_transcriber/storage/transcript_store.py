"""transcript.json CRUD 관리."""

from __future__ import annotations

import json
import pathlib
from datetime import UTC, datetime
from typing import Any


def create_transcript(
    segments: list[dict[str, Any]],
    *,
    title: str | None = None,
    languages: list[str] | None = None,
    source: str = "microphone",
    model: str = "whisper-small",
    duration_seconds: float = 0.0,
    speakers: dict[str, str] | None = None,
    diarization_meta: dict[str, str] | None = None,
) -> dict[str, Any]:
    """새 transcript 딕셔너리를 생성한다.

    speakers가 제공되면 schema v2.0으로 생성하고, 없으면 v1.0을 유지한다.

    Args:
        segments: 전사 세그먼트 리스트 [{start, end, text, language, confidence}]
        title: 트랜스크립트 제목 (None이면 자동 생성)
        languages: 감지된 언어 리스트
        source: 오디오 소스 ("microphone" | "file")
        model: 사용된 Whisper 모델명
        duration_seconds: 총 오디오 길이 (초)
        speakers: 화자 딕셔너리 (라벨 -> 이름). None이면 v1.0
        diarization_meta: 화자 분리 메타데이터 (모델명 등)

    Returns:
        transcript.json 스키마를 따르는 딕셔너리
    """
    now = datetime.now(tz=UTC).isoformat()
    if title is None:
        lang_suffix = "_".join(languages) if languages else "auto"
        title = f"{datetime.now(tz=UTC).strftime('%Y-%m-%d_%H%M')}_{lang_suffix}"

    metadata: dict[str, Any] = {
        "title": title,
        "created_at": now,
        "duration_seconds": duration_seconds,
        "languages": languages or [],
        "source": source,
        "model": model,
        "tags": [],
    }

    # v2.0: 화자 분리 데이터 포함
    if speakers is not None:
        version = "2.0"
        metadata["speakers"] = speakers
        metadata["diarization"] = diarization_meta or {}
    else:
        version = "1.0"

    return {
        "version": version,
        "metadata": metadata,
        "segments": segments,
    }


def save_transcript(transcript: dict[str, Any], path: pathlib.Path) -> pathlib.Path:
    """transcript를 JSON 파일로 저장한다.

    Args:
        transcript: transcript 딕셔너리
        path: 저장할 파일 경로

    Returns:
        저장된 파일의 경로
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(transcript, f, indent=2, ensure_ascii=False)
    return path


def update_transcript_speakers(
    path: pathlib.Path,
    segments: list[dict[str, Any]],
    speakers: dict[str, str],
    diarization_meta: dict[str, str],
) -> dict[str, Any]:
    """기존 transcript에 화자 정보를 업데이트한다.

    파일을 로드하여 v2.0으로 업그레이드하고, 세그먼트와 화자 메타데이터를 덮어쓴다.

    Args:
        path: transcript.json 파일 경로
        segments: 화자 라벨이 포함된 세그먼트 리스트
        speakers: 화자 딕셔너리 (라벨 -> 이름)
        diarization_meta: 화자 분리 메타데이터

    Returns:
        업데이트된 transcript 딕셔너리
    """
    transcript = load_transcript(path)
    transcript["version"] = "2.0"
    transcript["segments"] = segments
    transcript["metadata"]["speakers"] = speakers
    transcript["metadata"]["diarization"] = diarization_meta
    save_transcript(transcript, path)
    return transcript


def load_transcript(path: pathlib.Path) -> dict[str, Any]:
    """JSON 파일에서 transcript를 로드한다.

    Args:
        path: 읽을 파일 경로

    Returns:
        transcript 딕셔너리

    Raises:
        FileNotFoundError: 파일이 존재하지 않을 때
        json.JSONDecodeError: JSON 파싱 실패 시
    """
    with open(path, encoding="utf-8") as f:
        result: dict[str, Any] = json.load(f)
        return result
