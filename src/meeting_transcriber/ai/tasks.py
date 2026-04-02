"""AI 태스크 오케스트레이션 -- 전사 후 자동 처리."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

from meeting_transcriber.ai.provider_manager import ProviderManager


@dataclass
class AIResult:
    """AI 처리 결과."""

    summary: str = ""
    proofread_text: str = ""
    keywords: list[str] = field(default_factory=list)
    title: str = ""
    translation: str = ""
    errors: list[str] = field(default_factory=list)


class AITaskWorker(QThread):
    """전사 텍스트에 대해 AI 태스크를 순차 실행하는 워커.

    전사 완료 후 자동으로: 교열 -> 요약 -> 키워드 추출 -> 제목 생성.
    각 단계 완료 시 progress signal을 emit한다.
    태스크별로 get_provider_for_task()를 호출하여 개별 FallbackProvider를 생성한다.
    """

    progress = pyqtSignal(str)  # 현재 진행 중인 태스크명
    finished = pyqtSignal(object)  # AIResult

    def __init__(
        self,
        provider_manager: ProviderManager,
        settings: dict[str, Any],
        text: str,
        *,
        language: str = "auto",
        do_proofread: bool = True,
        do_summarize: bool = True,
        do_keywords: bool = True,
        do_title: bool = True,
        template_prompt: str | None = None,
        parent: Any = None,
    ) -> None:
        """AITaskWorker를 초기화한다.

        Args:
            provider_manager: 프로바이더 체인을 관리하는 ProviderManager 인스턴스
            settings: 앱 설정 딕셔너리 (ai.default_provider, ai.task_overrides 포함)
            text: 처리할 전사 텍스트
            language: 텍스트 언어
            do_proofread: 교열 수행 여부
            do_summarize: 요약 수행 여부
            do_keywords: 키워드 추출 여부
            do_title: 제목 생성 여부
            template_prompt: 템플릿 프롬프트 (있으면 요약 시 전달)
            parent: Qt 부모 객체
        """
        super().__init__(parent)
        self._manager = provider_manager
        self._settings = settings
        self._text = text
        self._language = language
        self._do_proofread = do_proofread
        self._do_summarize = do_summarize
        self._do_keywords = do_keywords
        self._do_title = do_title
        self._template_prompt = template_prompt
        self.fallback_messages: list[str] = []

    def _get_provider(self, task: str) -> Any:
        """태스크별 FallbackProvider를 생성한다.

        Args:
            task: AI 태스크명 (proofread, summarize, keywords, title)

        Returns:
            해당 태스크에 대한 FallbackProvider 인스턴스

        Raises:
            RuntimeError: 사용 가능한 프로바이더가 없을 때
        """
        from meeting_transcriber.ai.provider_manager import FallbackProvider

        chain = self._manager.get_provider_for_task(task, self._settings)
        if not chain:
            raise RuntimeError(f"No providers available for task: {task}")
        return FallbackProvider(self._manager, chain)

    def run(self) -> None:
        """AI 태스크를 순차 실행한다."""
        result = AIResult()

        if self._do_proofread:
            try:
                self.progress.emit("Proofreading...")
                provider = self._get_provider("proofread")
                result.proofread_text = provider.proofread(
                    self._text, language=self._language
                )
                self.fallback_messages.extend(provider.fallback_messages)
            except Exception as e:
                result.errors.append(f"Proofread failed: {e}")

        if self._do_summarize:
            try:
                self.progress.emit("Summarizing...")
                provider = self._get_provider("summarize")
                result.summary = provider.summarize(
                    self._text,
                    language=self._language,
                    template_prompt=self._template_prompt,
                )
                self.fallback_messages.extend(provider.fallback_messages)
            except Exception as e:
                result.errors.append(f"Summary failed: {e}")

        if self._do_keywords:
            try:
                self.progress.emit("Extracting keywords...")
                provider = self._get_provider("keywords")
                result.keywords = provider.extract_keywords(self._text)
                self.fallback_messages.extend(provider.fallback_messages)
            except Exception as e:
                result.errors.append(f"Keywords failed: {e}")

        if self._do_title:
            try:
                self.progress.emit("Generating title...")
                provider = self._get_provider("title")
                result.title = provider.generate_title(self._text)
                self.fallback_messages.extend(provider.fallback_messages)
            except Exception as e:
                result.errors.append(f"Title failed: {e}")

        self.finished.emit(result)
