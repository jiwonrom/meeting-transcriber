"""AI 프로바이더 추상 기반 클래스."""
from __future__ import annotations

from abc import ABC, abstractmethod


class AIProvider(ABC):
    """AI 프로바이더 인터페이스.

    모든 AI 프로바이더(Gemini, OpenAI 등)는 이 ABC를 상속한다.
    """

    @abstractmethod
    def summarize(self, text: str, *, language: str = "auto") -> str:
        """텍스트를 요약한다.

        Args:
            text: 요약할 전사 텍스트
            language: 출력 언어 (auto면 입력 언어 유지)

        Returns:
            요약된 텍스트
        """

    @abstractmethod
    def proofread(self, text: str, *, language: str = "auto") -> str:
        """텍스트를 교열한다 (맞춤법, 문법 교정).

        Args:
            text: 교열할 텍스트
            language: 텍스트 언어

        Returns:
            교열된 텍스트
        """

    @abstractmethod
    def translate(self, text: str, *, target_language: str) -> str:
        """텍스트를 번역한다.

        Args:
            text: 번역할 텍스트
            target_language: 대상 언어 코드 (en, ko, zh, ja)

        Returns:
            번역된 텍스트
        """

    @abstractmethod
    def extract_keywords(self, text: str, *, max_keywords: int = 10) -> list[str]:
        """텍스트에서 키워드를 추출한다.

        Args:
            text: 분석할 텍스트
            max_keywords: 최대 키워드 수

        Returns:
            키워드 리스트
        """

    @abstractmethod
    def generate_title(self, text: str) -> str:
        """텍스트 내용으로 짧은 제목을 생성한다.

        Args:
            text: 제목을 생성할 전사 텍스트

        Returns:
            생성된 제목 (최대 50자)
        """
