"""교차 회의 분석 워커."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

from meeting_transcriber.ai.provider_base import AIProvider


@dataclass
class CrossMeetingResult:
    """교차 회의 분석 결과."""

    recurring_topics: list[dict[str, Any]] = field(default_factory=list)
    action_items: list[dict[str, Any]] = field(default_factory=list)
    timeline: list[dict[str, Any]] = field(default_factory=list)
    custom_answer: str = ""
    transcript_paths: list[str] = field(default_factory=list)
    transcript_count: int = 0
    custom_query: str = ""
    language: str = "auto"
    errors: list[str] = field(default_factory=list)


class CrossMeetingAnalysisWorker(QThread):
    """여러 회의 트랜스크립트를 교차 분석하는 워커."""

    progress = pyqtSignal(str)
    finished = pyqtSignal(object)  # CrossMeetingResult

    def __init__(
        self,
        provider: AIProvider,
        transcripts: list[dict[str, Any]],
        *,
        transcript_paths: list[str] | None = None,
        language: str = "auto",
        custom_query: str | None = None,
        parent: Any = None,
    ) -> None:
        """CrossMeetingAnalysisWorker를 초기화한다.

        Args:
            provider: AI 프로바이더 인스턴스
            transcripts: 트랜스크립트 딕셔너리 리스트
            transcript_paths: 트랜스크립트 파일 경로 리스트
            language: 출력 언어
            custom_query: 사용자 추가 질문
            parent: Qt 부모 객체
        """
        super().__init__(parent)
        self._provider = provider
        self._transcripts = transcripts
        self._transcript_paths = transcript_paths or []
        self._language = language
        self._custom_query = custom_query

    def run(self) -> None:
        """교차 회의 분석을 실행한다."""
        try:
            self.progress.emit(f"Analyzing {len(self._transcripts)} transcripts...")
            raw = self._provider.analyze_cross_meeting(
                self._transcripts,
                language=self._language,
                custom_query=self._custom_query,
            )
            parsed = json.loads(raw)
            result = CrossMeetingResult(
                recurring_topics=parsed.get("recurring_topics", []),
                action_items=parsed.get("action_items", []),
                timeline=parsed.get("timeline", []),
                custom_answer=parsed.get("custom_answer", ""),
                transcript_paths=self._transcript_paths,
                transcript_count=len(self._transcripts),
                custom_query=self._custom_query or "",
                language=self._language,
            )
        except Exception as e:
            result = CrossMeetingResult(
                transcript_paths=self._transcript_paths,
                transcript_count=len(self._transcripts),
                custom_query=self._custom_query or "",
                language=self._language,
                errors=[f"Cross-meeting analysis failed: {e}"],
            )
        self.finished.emit(result)
