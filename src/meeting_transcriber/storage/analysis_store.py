"""교차 회의 분석 결과 저장소."""

from __future__ import annotations

import json
import pathlib
from datetime import UTC, datetime
from typing import Any

from meeting_transcriber.utils.constants import ANALYSES_DIR
from meeting_transcriber.utils.exceptions import AnalysisError


def _analyses_dir(workspace_root: pathlib.Path) -> pathlib.Path:
    """분석 결과 디렉토리를 반환한다. 없으면 생성한다.

    Args:
        workspace_root: 워크스페이스 루트 경로

    Returns:
        분석 결과 디렉토리 경로
    """
    d = workspace_root / ANALYSES_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_analysis(result: dict[str, Any], workspace_root: pathlib.Path) -> pathlib.Path:
    """분석 결과를 JSON 파일로 저장한다.

    Args:
        result: 분석 결과 딕셔너리
        workspace_root: 워크스페이스 루트 경로

    Returns:
        저장된 파일 경로
    """
    d = _analyses_dir(workspace_root)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
    filename = f"analysis_{timestamp}.json"
    path = d / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    return path


def load_analysis(path: pathlib.Path) -> dict[str, Any]:
    """분석 결과를 로드한다.

    Args:
        path: 분석 결과 파일 경로

    Returns:
        분석 결과 딕셔너리

    Raises:
        AnalysisError: 파일이 없거나 파싱 실패 시
    """
    try:
        with open(path, encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
            return data
    except FileNotFoundError as e:
        raise AnalysisError(f"Analysis file not found: {path}") from e
    except json.JSONDecodeError as e:
        raise AnalysisError(f"Failed to parse analysis file: {path}") from e


def list_analyses(workspace_root: pathlib.Path) -> list[pathlib.Path]:
    """분석 결과 파일 목록을 최신순으로 반환한다.

    Args:
        workspace_root: 워크스페이스 루트 경로

    Returns:
        분석 결과 파일 경로 리스트 (최신순)
    """
    d = _analyses_dir(workspace_root)
    files = sorted(d.glob("analysis_*.json"), reverse=True)
    return files


def delete_analysis(path: pathlib.Path) -> None:
    """분석 결과 파일을 삭제한다.

    Args:
        path: 삭제할 파일 경로

    Raises:
        AnalysisError: 파일이 없을 때
    """
    if not path.exists():
        raise AnalysisError(f"Analysis file not found: {path}")
    path.unlink()
