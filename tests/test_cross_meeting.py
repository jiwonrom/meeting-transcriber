"""교차 회의 분석 워커 테스트."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

from meeting_transcriber.ai.cross_meeting import (
    CrossMeetingAnalysisWorker,
    CrossMeetingResult,
)
from meeting_transcriber.ai.gemini_provider import (
    _build_analysis_prompt,
)


def _make_mock_provider(return_value: str | None = None, error: Exception | None = None) -> Any:
    """analyze_cross_meeting을 가진 목 프로바이더를 생성한다."""
    provider = MagicMock()
    if error:
        provider.analyze_cross_meeting.side_effect = error
    else:
        if return_value is None:
            return_value = json.dumps({
                "recurring_topics": [{"name": "Sprint", "meetings": ["M1"], "frequency": 1}],
                "action_items": [],
                "timeline": [],
                "custom_answer": "",
            })
        provider.analyze_cross_meeting.return_value = return_value
    return provider


def _make_dummy_transcripts(count: int = 2) -> list[dict[str, Any]]:
    """더미 트랜스크립트 리스트를 생성한다."""
    return [
        {
            "metadata": {"title": f"Meeting {i}", "created_at": f"2026-01-0{i}T00:00:00Z"},
            "segments": [{"text": f"Content of meeting {i}"}],
        }
        for i in range(1, count + 1)
    ]


def test_cross_meeting_result_defaults() -> None:
    """빈 CrossMeetingResult의 기본값을 검증한다."""
    result = CrossMeetingResult()
    assert result.recurring_topics == []
    assert result.action_items == []
    assert result.timeline == []
    assert result.custom_answer == ""
    assert result.errors == []
    assert result.transcript_count == 0


def test_cross_meeting_worker_emits_finished(qtbot: Any) -> None:
    """워커가 finished 시그널과 함께 CrossMeetingResult를 emit한다."""
    provider = _make_mock_provider()
    transcripts = _make_dummy_transcripts(2)

    worker = CrossMeetingAnalysisWorker(
        provider, transcripts, transcript_paths=["a.json", "b.json"]
    )

    with qtbot.waitSignal(worker.finished, timeout=5000) as blocker:
        worker.start()

    result: CrossMeetingResult = blocker.args[0]
    assert len(result.recurring_topics) > 0
    assert result.transcript_count == 2
    assert result.errors == []


def test_cross_meeting_worker_handles_error(qtbot: Any) -> None:
    """프로바이더 에러 시 errors 리스트에 기록된다."""
    provider = _make_mock_provider(error=RuntimeError("API failure"))
    transcripts = _make_dummy_transcripts(2)

    worker = CrossMeetingAnalysisWorker(provider, transcripts)

    with qtbot.waitSignal(worker.finished, timeout=5000) as blocker:
        worker.start()

    result: CrossMeetingResult = blocker.args[0]
    assert len(result.errors) > 0
    assert "API failure" in result.errors[0]


def test_build_analysis_prompt_custom_query() -> None:
    """custom_query가 프롬프트에 포함되는지 검증한다."""
    transcripts = _make_dummy_transcripts(1)
    prompt = _build_analysis_prompt(transcripts, custom_query="test question")
    assert "test question" in prompt
    assert "custom_answer" in prompt
