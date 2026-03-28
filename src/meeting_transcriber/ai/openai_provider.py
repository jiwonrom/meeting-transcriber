"""OpenAI AI 프로바이더 구현."""

from __future__ import annotations

from openai import OpenAI

from meeting_transcriber.ai.provider_base import AIProvider
from meeting_transcriber.utils.keychain import get_api_key


class OpenAIProvider(AIProvider):
    """OpenAI GPT를 사용하는 AI 프로바이더.

    macOS Keychain에서 API 키를 로드하여 OpenAI API를 호출한다.
    """

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o-mini") -> None:
        """OpenAIProvider를 초기화한다.

        Args:
            api_key: OpenAI API 키. None이면 Keychain에서 로드.
            model: 사용할 OpenAI 모델명.

        Raises:
            ValueError: API 키가 없을 때.
        """
        key = api_key or get_api_key("openai")
        if not key:
            raise ValueError("OpenAI API key not found. Set it in Settings > API Keys.")
        self._client = OpenAI(api_key=key)
        self._model = model

    def _call(self, prompt: str) -> str:
        """OpenAI Chat API를 호출하고 텍스트 응답을 반환한다."""
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
        )
        content: str = response.choices[0].message.content
        return content.strip()

    def summarize(
        self, text: str, *, language: str = "auto", template_prompt: str | None = None
    ) -> str:
        """텍스트를 요약한다.

        Args:
            text: 요약할 전사 텍스트
            language: 출력 언어
            template_prompt: 템플릿 프롬프트 (있으면 json_object 모드로 호출)

        Returns:
            요약된 텍스트 (또는 JSON 문자열)
        """
        if template_prompt:
            prompt = f"{template_prompt}\n\nTranscript:\n{text}"
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            content: str = response.choices[0].message.content
            return content.strip()

        lang_hint = f" Respond in {language}." if language != "auto" else ""
        prompt = (
            f"Summarize the following meeting transcript concisely "
            f"in 3-5 bullet points.{lang_hint}\n\n"
            f"Transcript:\n{text}"
        )
        return self._call(prompt)

    def proofread(self, text: str, *, language: str = "auto") -> str:
        """텍스트를 교열한다."""
        prompt = (
            "Proofread and correct the following transcribed text. "
            "Fix spelling, grammar, and punctuation errors. "
            "Keep the original meaning and tone. "
            "Return only the corrected text, no explanations.\n\n"
            f"Text:\n{text}"
        )
        return self._call(prompt)

    def translate(self, text: str, *, target_language: str) -> str:
        """텍스트를 번역한다."""
        lang_map = {"en": "English", "ko": "Korean", "zh": "Chinese", "ja": "Japanese"}
        lang_name = lang_map.get(target_language, target_language)
        prompt = (
            f"Translate the following text to {lang_name}. "
            "Return only the translation.\n\n"
            f"Text:\n{text}"
        )
        return self._call(prompt)

    def extract_keywords(self, text: str, *, max_keywords: int = 10) -> list[str]:
        """텍스트에서 키워드를 추출한다."""
        prompt = (
            f"Extract up to {max_keywords} key topics/keywords from "
            "the following transcript. Return as comma-separated list.\n\n"
            f"Transcript:\n{text}"
        )
        result = self._call(prompt)
        return [kw.strip() for kw in result.split(",") if kw.strip()]

    def generate_title(self, text: str) -> str:
        """텍스트로 짧은 제목을 생성한다."""
        prompt = (
            "Generate a short, descriptive title (max 50 characters) "
            "for the following meeting transcript. "
            "Return only the title, no quotes.\n\n"
            f"Transcript:\n{text[:500]}"
        )
        title = self._call(prompt)
        return title[:50]
