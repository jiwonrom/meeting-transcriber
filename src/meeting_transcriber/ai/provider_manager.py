"""AI 프로바이더 관리 및 폴백 처리."""

from __future__ import annotations

import importlib
import logging
from typing import Any

from meeting_transcriber.ai.provider_base import AIProvider
from meeting_transcriber.utils.keychain import get_api_key

logger = logging.getLogger(__name__)


class ProviderManager:
    """AI 프로바이더 체인을 관리하고 폴백을 처리한다.

    설정에 따라 프로바이더 우선순위를 결정하고,
    실패 시 다음 프로바이더로 자동 폴백한다.
    """

    PROVIDERS: dict[str, tuple[str, str]] = {
        "gemini": ("meeting_transcriber.ai.gemini_provider", "GeminiProvider"),
        "openai": ("meeting_transcriber.ai.openai_provider", "OpenAIProvider"),
        "anthropic": ("meeting_transcriber.ai.anthropic_provider", "AnthropicProvider"),
    }

    def get_provider_chain(self, settings: dict[str, Any]) -> list[AIProvider]:
        """설정에 따른 프로바이더 체인을 구성한다.

        기본 프로바이더를 첫 번째로, 키가 있는 나머지를 순서대로 추가한다.

        Args:
            settings: 앱 설정 딕셔너리 (ai.default_provider, ai.task_overrides)

        Returns:
            우선순위 순으로 정렬된 AIProvider 인스턴스 리스트
        """
        ai_settings = settings.get("ai", {})
        default = ai_settings.get("default_provider", "gemini")
        return self._build_chain(default)

    def get_provider_for_task(self, task: str, settings: dict[str, Any]) -> list[AIProvider]:
        """특정 태스크에 대한 프로바이더 체인을 반환한다.

        task_overrides에 해당 태스크가 지정되어 있으면 그 프로바이더를 우선한다.

        Args:
            task: AI 태스크명 (summarize, proofread 등)
            settings: 앱 설정 딕셔너리

        Returns:
            태스크별 우선순위로 정렬된 AIProvider 인스턴스 리스트
        """
        ai_settings = settings.get("ai", {})
        task_overrides = ai_settings.get("task_overrides", {})

        if task in task_overrides:
            override_default = task_overrides[task]
            return self._build_chain(override_default)

        return self.get_provider_chain(settings)

    def execute_with_fallback(
        self,
        chain: list[AIProvider],
        method: str,
        *args: Any,
        **kwargs: Any,
    ) -> tuple[Any, str | None]:
        """프로바이더 체인을 순서대로 시도하여 첫 성공 결과를 반환한다.

        Args:
            chain: 시도할 프로바이더 리스트
            method: 호출할 AIProvider 메서드명
            *args: 메서드 인자
            **kwargs: 메서드 키워드 인자

        Returns:
            (결과, 폴백 메시지) 튜플. 첫 시도 성공 시 메시지는 None.

        Raises:
            RuntimeError: 모든 프로바이더가 실패했을 때.
        """
        last_error: Exception | None = None
        failed_names: list[str] = []

        for i, provider in enumerate(chain):
            try:
                func = getattr(provider, method)
                result = func(*args, **kwargs)
                if i == 0:
                    return result, None
                failed_str = ", ".join(failed_names)
                success_name = type(provider).__name__
                msg = f"{failed_str} failed, using {success_name}"
                return result, msg
            except Exception as e:
                provider_name = type(provider).__name__
                logger.warning("Provider %s.%s failed: %s", provider_name, method, e)
                failed_names.append(provider_name)
                last_error = e

        raise RuntimeError(f"All providers failed. Last error: {last_error}")

    def _build_chain(self, default: str) -> list[AIProvider]:
        """기본 프로바이더를 첫 번째로 하는 체인을 구성한다.

        Args:
            default: 첫 번째로 시도할 프로바이더명

        Returns:
            AIProvider 인스턴스 리스트
        """
        chain: list[AIProvider] = []
        order = [default] + [n for n in self.PROVIDERS if n != default]

        for name in order:
            if name not in self.PROVIDERS:
                continue
            if not self._has_key(name):
                continue
            try:
                provider = self._instantiate(name)
                chain.append(provider)
            except Exception as e:
                logger.warning("Failed to instantiate %s: %s", name, e)

        return chain

    def _instantiate(self, name: str) -> AIProvider:
        """프로바이더를 지연 임포트하여 인스턴스를 생성한다.

        Args:
            name: 프로바이더 식별자 (gemini, openai, anthropic)

        Returns:
            AIProvider 인스턴스

        Raises:
            KeyError: 알 수 없는 프로바이더명일 때.
            ImportError: 모듈 로드 실패 시.
        """
        if name not in self.PROVIDERS:
            raise KeyError(f"Unknown provider: {name}")

        module_path, class_name = self.PROVIDERS[name]
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        return cls()

    def _has_key(self, name: str) -> bool:
        """프로바이더의 API 키가 Keychain에 있는지 확인한다.

        Args:
            name: 프로바이더 식별자

        Returns:
            키가 있으면 True
        """
        return get_api_key(name) is not None


class FallbackProvider(AIProvider):
    """AIProvider 어댑터 — 각 메서드를 execute_with_fallback으로 위임한다.

    AITaskWorker에 단일 AIProvider 인스턴스를 전달하면서,
    내부적으로는 프로바이더 체인 전체를 자동 폴백으로 시도한다.
    폴백 상태 메시지를 수집하여 UI에서 표시할 수 있다.
    """

    def __init__(self, manager: ProviderManager, chain: list[AIProvider]) -> None:
        """FallbackProvider를 초기화한다.

        Args:
            manager: 폴백 실행을 담당하는 ProviderManager
            chain: 시도할 프로바이더 체인
        """
        self._manager = manager
        self._chain = chain
        self.fallback_messages: list[str] = []

    def _call_with_fallback(self, method: str, *args: Any, **kwargs: Any) -> Any:
        """프로바이더 체인을 통해 메서드를 실행하고 폴백 메시지를 수집한다.

        Args:
            method: 호출할 AIProvider 메서드명
            *args: 메서드 인자
            **kwargs: 메서드 키워드 인자

        Returns:
            메서드 실행 결과
        """
        result, msg = self._manager.execute_with_fallback(self._chain, method, *args, **kwargs)
        if msg:
            self.fallback_messages.append(msg)
        return result

    def summarize(
        self, text: str, *, language: str = "auto", template_prompt: str | None = None
    ) -> str:
        """텍스트를 요약한다 (폴백 지원)."""
        return self._call_with_fallback(
            "summarize", text, language=language, template_prompt=template_prompt
        )

    def proofread(self, text: str, *, language: str = "auto") -> str:
        """텍스트를 교열한다 (폴백 지원)."""
        return self._call_with_fallback("proofread", text, language=language)

    def translate(self, text: str, *, target_language: str) -> str:
        """텍스트를 번역한다 (폴백 지원)."""
        return self._call_with_fallback("translate", text, target_language=target_language)

    def extract_keywords(self, text: str, *, max_keywords: int = 10) -> list[str]:
        """텍스트에서 키워드를 추출한다 (폴백 지원)."""
        return self._call_with_fallback("extract_keywords", text, max_keywords=max_keywords)

    def generate_title(self, text: str) -> str:
        """텍스트로 짧은 제목을 생성한다 (폴백 지원)."""
        return self._call_with_fallback("generate_title", text)
