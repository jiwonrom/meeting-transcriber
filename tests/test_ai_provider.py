"""AI provider 모듈 단위 테스트."""
from __future__ import annotations

from unittest.mock import patch

from meeting_transcriber.ai.provider_base import AIProvider
from meeting_transcriber.ai.tasks import AIResult, AITaskWorker

# -- Mock Provider --


class MockProvider(AIProvider):
    """테스트용 mock AI 프로바이더."""

    def summarize(self, text: str, *, language: str = "auto") -> str:
        return "- Point 1\n- Point 2\n- Point 3"

    def proofread(self, text: str, *, language: str = "auto") -> str:
        return text.replace("teh", "the")

    def translate(self, text: str, *, target_language: str) -> str:
        return f"[{target_language}] {text}"

    def extract_keywords(self, text: str, *, max_keywords: int = 10) -> list[str]:
        return ["meeting", "transcription", "AI"]

    def generate_title(self, text: str) -> str:
        return "Weekly Standup Meeting"


# -- Provider Base 테스트 --


def test_mock_provider_implements_abc() -> None:
    """MockProvider가 ABC를 올바르게 구현하는지 확인."""
    provider = MockProvider()
    assert isinstance(provider, AIProvider)


def test_mock_provider_summarize() -> None:
    """요약이 동작하는지 확인."""
    provider = MockProvider()
    result = provider.summarize("Hello world meeting transcript")
    assert "Point 1" in result


def test_mock_provider_proofread() -> None:
    """교열이 동작하는지 확인."""
    provider = MockProvider()
    result = provider.proofread("teh quick brown fox")
    assert result == "the quick brown fox"


def test_mock_provider_translate() -> None:
    """번역이 동작하는지 확인."""
    provider = MockProvider()
    result = provider.translate("Hello", target_language="ko")
    assert "[ko]" in result


def test_mock_provider_extract_keywords() -> None:
    """키워드 추출이 동작하는지 확인."""
    provider = MockProvider()
    keywords = provider.extract_keywords("meeting about AI transcription")
    assert len(keywords) > 0
    assert "meeting" in keywords


def test_mock_provider_generate_title() -> None:
    """제목 생성이 동작하는지 확인."""
    provider = MockProvider()
    title = provider.generate_title("We discussed the weekly standup")
    assert len(title) <= 50


# -- AITaskWorker 테스트 --


def test_ai_task_worker_all_tasks(qtbot: object) -> None:
    """모든 AI 태스크가 순차 실행되는지 확인."""
    provider = MockProvider()
    worker = AITaskWorker(
        provider=provider,
        text="teh quick brown fox jumped over teh lazy dog",
        language="en",
    )

    results: list[AIResult] = []
    progress_msgs: list[str] = []

    worker.progress.connect(lambda msg: progress_msgs.append(msg))
    worker.finished.connect(lambda r: results.append(r))

    worker.run()  # 직접 호출 (QThread.start() 대신)

    assert len(results) == 1
    result = results[0]
    assert "the quick brown fox" in result.proofread_text
    assert "Point 1" in result.summary
    assert len(result.keywords) == 3
    assert result.title == "Weekly Standup Meeting"
    assert len(result.errors) == 0


def test_ai_task_worker_selective(qtbot: object) -> None:
    """선택적 태스크만 실행되는지 확인."""
    provider = MockProvider()
    worker = AITaskWorker(
        provider=provider,
        text="Hello world",
        do_proofread=False,
        do_summarize=True,
        do_keywords=False,
        do_title=False,
    )

    results: list[AIResult] = []
    worker.finished.connect(lambda r: results.append(r))
    worker.run()

    result = results[0]
    assert result.proofread_text == ""  # 비활성화됨
    assert "Point 1" in result.summary  # 활성화됨
    assert result.keywords == []  # 비활성화됨
    assert result.title == ""  # 비활성화됨


def test_ai_task_worker_error_handling(qtbot: object) -> None:
    """태스크 실패 시 에러가 수집되는지 확인."""

    class FailingProvider(MockProvider):
        def summarize(self, text: str, *, language: str = "auto") -> str:
            raise RuntimeError("API error")

    provider = FailingProvider()
    worker = AITaskWorker(provider=provider, text="test")

    results: list[AIResult] = []
    worker.finished.connect(lambda r: results.append(r))
    worker.run()

    result = results[0]
    assert len(result.errors) == 1
    assert "Summary failed" in result.errors[0]
    # 다른 태스크는 정상 수행됨
    assert result.proofread_text != ""


def test_ai_task_worker_progress_signals(qtbot: object) -> None:
    """진행 상태 signal이 emit되는지 확인."""
    provider = MockProvider()
    worker = AITaskWorker(provider=provider, text="test")

    msgs: list[str] = []
    worker.progress.connect(lambda m: msgs.append(m))
    worker.run()

    assert "Proofreading..." in msgs
    assert "Summarizing..." in msgs
    assert "Extracting keywords..." in msgs
    assert "Generating title..." in msgs


# -- GeminiProvider 테스트 (mock) --


def test_gemini_provider_requires_api_key() -> None:
    """API 키 없으면 ValueError를 발생시키는지 확인."""
    import pytest

    with patch("meeting_transcriber.ai.gemini_provider.get_api_key", return_value=None):
        from meeting_transcriber.ai.gemini_provider import GeminiProvider

        with pytest.raises(ValueError, match="API key not found"):
            GeminiProvider()
