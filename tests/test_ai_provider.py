"""AI provider 모듈 단위 테스트."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from meeting_transcriber.ai.provider_base import AIProvider
from meeting_transcriber.ai.tasks import AIResult, AITaskWorker

# -- Mock Provider --


class MockProvider(AIProvider):
    """테스트용 mock AI 프로바이더."""

    def summarize(
        self, text: str, *, language: str = "auto", template_prompt: str | None = None
    ) -> str:
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
        def summarize(
            self, text: str, *, language: str = "auto", template_prompt: str | None = None
        ) -> str:
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
    with patch("meeting_transcriber.ai.gemini_provider.get_api_key", return_value=None):
        from meeting_transcriber.ai.gemini_provider import GeminiProvider

        with pytest.raises(ValueError, match="API key not found"):
            GeminiProvider()


# -- OpenAIProvider 테스트 (mock) --


def _make_openai_mock_response(content: str) -> MagicMock:
    """OpenAI chat completion mock 응답을 생성한다."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = content
    return mock_response


def test_openai_provider_implements_abc() -> None:
    """OpenAIProvider가 AIProvider ABC를 구현하는지 확인."""
    with (
        patch("meeting_transcriber.ai.openai_provider.OpenAI") as mock_cls,
        patch("meeting_transcriber.ai.openai_provider.get_api_key", return_value="test-key"),
    ):
        mock_cls.return_value = MagicMock()
        from meeting_transcriber.ai.openai_provider import OpenAIProvider

        provider = OpenAIProvider()
        assert isinstance(provider, AIProvider)


def test_openai_provider_requires_api_key() -> None:
    """API 키 없으면 ValueError를 발생시키는지 확인."""
    with patch("meeting_transcriber.ai.openai_provider.get_api_key", return_value=None):
        from meeting_transcriber.ai.openai_provider import OpenAIProvider

        with pytest.raises(ValueError, match="API key not found"):
            OpenAIProvider()


def test_openai_provider_summarize() -> None:
    """OpenAI summarize가 동작하는지 확인."""
    with (
        patch("meeting_transcriber.ai.openai_provider.OpenAI") as mock_cls,
        patch("meeting_transcriber.ai.openai_provider.get_api_key", return_value="test-key"),
    ):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_openai_mock_response(
            "- Summary point 1\n- Summary point 2"
        )

        from meeting_transcriber.ai.openai_provider import OpenAIProvider

        provider = OpenAIProvider()
        result = provider.summarize("Test transcript text")
        assert "Summary point 1" in result
        mock_client.chat.completions.create.assert_called_once()


def test_openai_provider_proofread() -> None:
    """OpenAI proofread가 동작하는지 확인."""
    with (
        patch("meeting_transcriber.ai.openai_provider.OpenAI") as mock_cls,
        patch("meeting_transcriber.ai.openai_provider.get_api_key", return_value="test-key"),
    ):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_openai_mock_response(
            "The quick brown fox"
        )

        from meeting_transcriber.ai.openai_provider import OpenAIProvider

        provider = OpenAIProvider()
        result = provider.proofread("teh quick brown fox")
        assert result == "The quick brown fox"


def test_openai_provider_extract_keywords() -> None:
    """OpenAI extract_keywords가 리스트를 반환하는지 확인."""
    with (
        patch("meeting_transcriber.ai.openai_provider.OpenAI") as mock_cls,
        patch("meeting_transcriber.ai.openai_provider.get_api_key", return_value="test-key"),
    ):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_openai_mock_response(
            "AI, transcription, meeting"
        )

        from meeting_transcriber.ai.openai_provider import OpenAIProvider

        provider = OpenAIProvider()
        keywords = provider.extract_keywords("AI meeting transcription text")
        assert isinstance(keywords, list)
        assert len(keywords) == 3
        assert "AI" in keywords


# -- AnthropicProvider 테스트 (mock) --


def _make_anthropic_mock_response(text: str) -> MagicMock:
    """Anthropic messages mock 응답을 생성한다."""
    mock_response = MagicMock()
    mock_content = MagicMock()
    mock_content.text = text
    mock_response.content = [mock_content]
    return mock_response


def test_anthropic_provider_implements_abc() -> None:
    """AnthropicProvider가 AIProvider ABC를 구현하는지 확인."""
    with (
        patch("meeting_transcriber.ai.anthropic_provider.Anthropic") as mock_cls,
        patch("meeting_transcriber.ai.anthropic_provider.get_api_key", return_value="test-key"),
    ):
        mock_cls.return_value = MagicMock()
        from meeting_transcriber.ai.anthropic_provider import AnthropicProvider

        provider = AnthropicProvider()
        assert isinstance(provider, AIProvider)


def test_anthropic_provider_requires_api_key() -> None:
    """API 키 없으면 ValueError를 발생시키는지 확인."""
    with patch("meeting_transcriber.ai.anthropic_provider.get_api_key", return_value=None):
        from meeting_transcriber.ai.anthropic_provider import AnthropicProvider

        with pytest.raises(ValueError, match="API key not found"):
            AnthropicProvider()


def test_anthropic_provider_summarize() -> None:
    """Anthropic summarize가 동작하는지 확인."""
    with (
        patch("meeting_transcriber.ai.anthropic_provider.Anthropic") as mock_cls,
        patch("meeting_transcriber.ai.anthropic_provider.get_api_key", return_value="test-key"),
    ):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = _make_anthropic_mock_response(
            "- Summary from Claude"
        )

        from meeting_transcriber.ai.anthropic_provider import AnthropicProvider

        provider = AnthropicProvider()
        result = provider.summarize("Test transcript text")
        assert "Summary from Claude" in result
        mock_client.messages.create.assert_called_once()


# -- FailingProvider (모든 메서드 실패) --


class FailingMockProvider(AIProvider):
    """모든 메서드에서 예외를 발생시키는 테스트 프로바이더."""

    def summarize(
        self, text: str, *, language: str = "auto", template_prompt: str | None = None
    ) -> str:
        raise RuntimeError("FailingMockProvider error")

    def proofread(self, text: str, *, language: str = "auto") -> str:
        raise RuntimeError("FailingMockProvider error")

    def translate(self, text: str, *, target_language: str) -> str:
        raise RuntimeError("FailingMockProvider error")

    def extract_keywords(self, text: str, *, max_keywords: int = 10) -> list[str]:
        raise RuntimeError("FailingMockProvider error")

    def generate_title(self, text: str) -> str:
        raise RuntimeError("FailingMockProvider error")


# -- ProviderManager 테스트 --


def test_provider_manager_default_chain() -> None:
    """기본 설정으로 gemini key만 있을 때 체인이 1개인지 확인."""
    from meeting_transcriber.ai.provider_manager import ProviderManager

    manager = ProviderManager()
    settings = {"ai": {"default_provider": "gemini", "task_overrides": {}}}

    with patch.object(manager, "_has_key", side_effect=lambda n: n == "gemini"):
        with patch.object(manager, "_instantiate", return_value=MockProvider()):
            chain = manager.get_provider_chain(settings)
            assert len(chain) == 1


def test_provider_manager_multi_chain() -> None:
    """gemini+openai key가 있으면 체인이 2개인지 확인."""
    from meeting_transcriber.ai.provider_manager import ProviderManager

    manager = ProviderManager()
    settings = {"ai": {"default_provider": "gemini", "task_overrides": {}}}

    with patch.object(manager, "_has_key", side_effect=lambda n: n in ("gemini", "openai")):
        with patch.object(manager, "_instantiate", return_value=MockProvider()):
            chain = manager.get_provider_chain(settings)
            assert len(chain) == 2


def test_provider_manager_custom_default() -> None:
    """default=openai일 때 openai가 체인 첫 번째인지 확인."""
    from meeting_transcriber.ai.provider_manager import ProviderManager

    manager = ProviderManager()
    settings = {"ai": {"default_provider": "openai", "task_overrides": {}}}

    providers_created: list[str] = []

    def mock_instantiate(name: str) -> MockProvider:
        providers_created.append(name)
        return MockProvider()

    with patch.object(manager, "_has_key", side_effect=lambda n: n in ("gemini", "openai")):
        with patch.object(manager, "_instantiate", side_effect=mock_instantiate):
            chain = manager.get_provider_chain(settings)
            assert len(chain) == 2
            assert providers_created[0] == "openai"


def test_provider_manager_fallback_success() -> None:
    """첫 번째 프로바이더 실패 시 두 번째 프로바이더 결과를 반환하는지 확인."""
    from meeting_transcriber.ai.provider_manager import ProviderManager

    manager = ProviderManager()
    chain = [FailingMockProvider(), MockProvider()]

    result, msg = manager.execute_with_fallback(chain, "summarize", "test text")
    assert "Point 1" in result
    assert msg is not None  # fallback이 발생했으므로 메시지가 있어야 함


def test_provider_manager_fallback_status() -> None:
    """첫 시도 성공 시 fallback_message가 None인지 확인."""
    from meeting_transcriber.ai.provider_manager import ProviderManager

    manager = ProviderManager()
    chain = [MockProvider()]

    result, msg = manager.execute_with_fallback(chain, "summarize", "test text")
    assert "Point 1" in result
    assert msg is None


def test_provider_manager_all_fail() -> None:
    """모든 프로바이더 실패 시 RuntimeError를 발생시키는지 확인."""
    from meeting_transcriber.ai.provider_manager import ProviderManager

    manager = ProviderManager()
    chain = [FailingMockProvider(), FailingMockProvider()]

    with pytest.raises(RuntimeError, match="All providers failed"):
        manager.execute_with_fallback(chain, "summarize", "test text")


def test_provider_manager_task_override() -> None:
    """task_overrides가 있을 때 해당 프로바이더가 우선인지 확인."""
    from meeting_transcriber.ai.provider_manager import ProviderManager

    manager = ProviderManager()
    settings = {
        "ai": {
            "default_provider": "gemini",
            "task_overrides": {"summarize": "openai"},
        }
    }

    providers_created: list[str] = []

    def mock_instantiate(name: str) -> MockProvider:
        providers_created.append(name)
        return MockProvider()

    with patch.object(manager, "_has_key", side_effect=lambda n: n in ("gemini", "openai")):
        with patch.object(manager, "_instantiate", side_effect=mock_instantiate):
            chain = manager.get_provider_for_task("summarize", settings)
            assert len(chain) >= 1
            assert providers_created[0] == "openai"


# -- FallbackProvider 테스트 --


def test_fallback_provider_is_aiprovider() -> None:
    """FallbackProvider가 AIProvider 인스턴스인지 확인."""
    from meeting_transcriber.ai.provider_manager import FallbackProvider, ProviderManager

    manager = ProviderManager()
    chain = [MockProvider()]
    provider = FallbackProvider(manager, chain)
    assert isinstance(provider, AIProvider)


def test_fallback_provider_summarize_uses_fallback() -> None:
    """FallbackProvider.summarize가 execute_with_fallback을 통해 결과를 반환하는지 확인."""
    from meeting_transcriber.ai.provider_manager import FallbackProvider, ProviderManager

    manager = ProviderManager()
    chain = [MockProvider()]
    provider = FallbackProvider(manager, chain)

    result = provider.summarize("test text")
    assert "Point 1" in result


def test_fallback_provider_fallback_emits_message() -> None:
    """폴백 발생 시 fallback_messages에 메시지가 추가되는지 확인."""
    from meeting_transcriber.ai.provider_manager import FallbackProvider, ProviderManager

    manager = ProviderManager()
    chain = [FailingMockProvider(), MockProvider()]
    provider = FallbackProvider(manager, chain)

    result = provider.summarize("test text")
    assert "Point 1" in result
    assert len(provider.fallback_messages) == 1
    assert "failed" in provider.fallback_messages[0].lower()


def test_summarize_with_template_prompt() -> None:
    """각 프로바이더의 summarize()가 template_prompt kwarg를 수용하는지 확인."""
    provider = MockProvider()
    result = provider.summarize("test text", template_prompt="Custom prompt")
    assert result is not None


def test_fallback_provider_forwards_template_prompt() -> None:
    """FallbackProvider.summarize()가 template_prompt를 전달하는지 확인."""
    from meeting_transcriber.ai.provider_manager import FallbackProvider, ProviderManager

    manager = ProviderManager()
    chain = [MockProvider()]
    provider = FallbackProvider(manager, chain)

    result = provider.summarize("test text", template_prompt="Custom prompt")
    assert "Point 1" in result


def test_ai_task_worker_template_prompt(qtbot: object) -> None:
    """AITaskWorker가 template_prompt를 provider.summarize()에 전달하는지 확인."""
    called_kwargs: list[dict] = []

    class TrackingProvider(MockProvider):
        def summarize(self, text: str, *, language: str = "auto", template_prompt: str | None = None) -> str:
            called_kwargs.append({"language": language, "template_prompt": template_prompt})
            return '{"decisions": ["item1"]}'

    provider = TrackingProvider()
    worker = AITaskWorker(
        provider=provider,
        text="test text",
        template_prompt="Custom template prompt",
        do_proofread=False,
        do_keywords=False,
        do_title=False,
    )

    results: list[AIResult] = []
    worker.finished.connect(lambda r: results.append(r))
    worker.run()

    assert len(called_kwargs) == 1
    assert called_kwargs[0]["template_prompt"] == "Custom template prompt"


def test_ai_task_worker_no_template(qtbot: object) -> None:
    """template_prompt 없이 AITaskWorker가 기존 방식대로 동작하는지 확인."""
    called_kwargs: list[dict] = []

    class TrackingProvider(MockProvider):
        def summarize(self, text: str, *, language: str = "auto", template_prompt: str | None = None) -> str:
            called_kwargs.append({"template_prompt": template_prompt})
            return "- Point 1"

    provider = TrackingProvider()
    worker = AITaskWorker(provider=provider, text="test")

    results: list[AIResult] = []
    worker.finished.connect(lambda r: results.append(r))
    worker.run()

    assert called_kwargs[0]["template_prompt"] is None


def test_gemini_json_mode() -> None:
    """GeminiProvider.summarize()에 template_prompt 전달 시 JSON 모드 사용 확인."""
    with (
        patch("meeting_transcriber.ai.gemini_provider.genai") as mock_genai,
        patch("meeting_transcriber.ai.gemini_provider.get_api_key", return_value="test-key"),
    ):
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model
        mock_response = MagicMock()
        mock_response.text = '{"decisions": ["item1"]}'
        mock_model.generate_content.return_value = mock_response

        from meeting_transcriber.ai.gemini_provider import GeminiProvider
        provider = GeminiProvider()
        result = provider.summarize("test", template_prompt="Return JSON")

        # Verify generate_content was called with generation_config
        call_args = mock_model.generate_content.call_args
        assert "generation_config" in call_args.kwargs or (
            len(call_args.args) > 1 or "generation_config" in (call_args.kwargs or {})
        )


def test_openai_json_mode() -> None:
    """OpenAIProvider.summarize()에 template_prompt 전달 시 json_object 모드 사용 확인."""
    with (
        patch("meeting_transcriber.ai.openai_provider.OpenAI") as mock_cls,
        patch("meeting_transcriber.ai.openai_provider.get_api_key", return_value="test-key"),
    ):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_openai_mock_response(
            '{"decisions": ["item1"]}'
        )

        from meeting_transcriber.ai.openai_provider import OpenAIProvider
        provider = OpenAIProvider()
        result = provider.summarize("test", template_prompt="Return JSON")

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs.get("response_format") == {"type": "json_object"}


def test_anthropic_json_fallback() -> None:
    """AnthropicProvider.summarize()에 template_prompt 전달 시 프롬프트에 JSON 지시 포함 확인."""
    with (
        patch("meeting_transcriber.ai.anthropic_provider.Anthropic") as mock_cls,
        patch("meeting_transcriber.ai.anthropic_provider.get_api_key", return_value="test-key"),
    ):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = _make_anthropic_mock_response(
            '{"decisions": ["item1"]}'
        )

        from meeting_transcriber.ai.anthropic_provider import AnthropicProvider
        provider = AnthropicProvider()
        result = provider.summarize("test", template_prompt="Return JSON. Respond ONLY with valid JSON.")

        call_kwargs = mock_client.messages.create.call_args.kwargs
        prompt_content = call_kwargs["messages"][0]["content"]
        assert "Respond ONLY with valid JSON" in prompt_content


def test_fallback_provider_proofread_uses_fallback() -> None:
    """FallbackProvider.proofread가 execute_with_fallback을 통해 동작하는지 확인."""
    from meeting_transcriber.ai.provider_manager import FallbackProvider, ProviderManager

    manager = ProviderManager()
    chain = [MockProvider()]
    provider = FallbackProvider(manager, chain)

    result = provider.proofread("teh quick brown fox")
    assert result == "the quick brown fox"
