"""AI 태스크 오케스트레이션 — 전사 후 자동 처리."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

from meeting_transcriber.ai.provider_base import AIProvider


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

    전사 완료 후 자동으로: 교열 → 요약 → 키워드 추출 → 제목 생성.
    각 단계 완료 시 progress signal을 emit한다.
    """

    progress = pyqtSignal(str)  # 현재 진행 중인 태스크명
    finished = pyqtSignal(object)  # AIResult

    def __init__(
        self,
        provider: AIProvider,
        text: str,
        *,
        language: str = "auto",
        do_proofread: bool = True,
        do_summarize: bool = True,
        do_keywords: bool = True,
        do_title: bool = True,
        parent: Any = None,
    ) -> None:
        """AITaskWorker를 초기화한다.

        Args:
            provider: AI 프로바이더 인스턴스
            text: 처리할 전사 텍스트
            language: 텍스트 언어
            do_proofread: 교열 수행 여부
            do_summarize: 요약 수행 여부
            do_keywords: 키워드 추출 여부
            do_title: 제목 생성 여부
            parent: Qt 부모 객체
        """
        super().__init__(parent)
        self._provider = provider
        self._text = text
        self._language = language
        self._do_proofread = do_proofread
        self._do_summarize = do_summarize
        self._do_keywords = do_keywords
        self._do_title = do_title

    def run(self) -> None:
        """AI 태스크를 순차 실행한다."""
        result = AIResult()

        if self._do_proofread:
            try:
                self.progress.emit("Proofreading...")
                result.proofread_text = self._provider.proofread(
                    self._text, language=self._language
                )
            except Exception as e:
                result.errors.append(f"Proofread failed: {e}")

        if self._do_summarize:
            try:
                self.progress.emit("Summarizing...")
                result.summary = self._provider.summarize(
                    self._text, language=self._language
                )
            except Exception as e:
                result.errors.append(f"Summary failed: {e}")

        if self._do_keywords:
            try:
                self.progress.emit("Extracting keywords...")
                result.keywords = self._provider.extract_keywords(self._text)
            except Exception as e:
                result.errors.append(f"Keywords failed: {e}")

        if self._do_title:
            try:
                self.progress.emit("Generating title...")
                result.title = self._provider.generate_title(self._text)
            except Exception as e:
                result.errors.append(f"Title failed: {e}")

        self.finished.emit(result)
