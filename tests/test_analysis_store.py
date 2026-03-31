"""AnalysisStore 테스트."""

from __future__ import annotations

import pathlib

import pytest

from meeting_transcriber.storage.analysis_store import (
    delete_analysis,
    list_analyses,
    load_analysis,
    save_analysis,
)
from meeting_transcriber.utils.exceptions import AnalysisError


def test_save_and_load_analysis(tmp_path: pathlib.Path) -> None:
    """분석 결과를 저장하고 다시 로드하면 동일한 데이터를 반환한다."""
    result = {"recurring_topics": [{"name": "Sprint"}], "action_items": []}
    saved_path = save_analysis(result, tmp_path)
    assert saved_path.exists()

    loaded = load_analysis(saved_path)
    assert loaded == result


def test_list_analyses_sorted(tmp_path: pathlib.Path) -> None:
    """여러 분석 결과를 저장하면 최신순으로 정렬된다."""
    import time

    save_analysis({"id": 1}, tmp_path)
    time.sleep(0.05)  # 타임스탬프 차이 보장
    second_path = save_analysis({"id": 2}, tmp_path)

    analyses = list_analyses(tmp_path)
    assert len(analyses) == 2
    # 최신이 먼저
    assert analyses[0] == second_path


def test_delete_analysis(tmp_path: pathlib.Path) -> None:
    """분석 결과를 삭제하면 파일이 사라진다."""
    saved_path = save_analysis({"test": True}, tmp_path)
    assert saved_path.exists()

    delete_analysis(saved_path)
    assert not saved_path.exists()


def test_load_missing_raises(tmp_path: pathlib.Path) -> None:
    """존재하지 않는 파일 로드 시 AnalysisError를 발생시킨다."""
    with pytest.raises(AnalysisError):
        load_analysis(tmp_path / "nonexistent.json")
