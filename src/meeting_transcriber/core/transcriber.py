"""whisper-cli subprocess 래퍼 — 파일 기반 전사."""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any

from meeting_transcriber.core.file_importer import validate_audio_file
from meeting_transcriber.core.model_manager import get_model_path, is_model_downloaded
from meeting_transcriber.utils.exceptions import (
    TranscriptionError,
    WhisperCliNotFoundError,
    WhisperModelNotFoundError,
)


@dataclass(frozen=True)
class TranscriptionResult:
    """전사 결과를 담는 불변 데이터 클래스."""

    segments: list[dict[str, Any]] = field(default_factory=list)
    language: str = "auto"
    model: str = "whisper-small"
    duration_seconds: float = 0.0
    raw_output: str = ""


def _resolve_whisper_cli(override: str | None = None) -> str:
    """whisper-cli 바이너리 경로를 찾는다.

    Args:
        override: 사용자가 직접 지정한 경로 (settings.json에서)

    Returns:
        whisper-cli 실행 파일 경로

    Raises:
        WhisperCliNotFoundError: 바이너리를 찾을 수 없을 때
    """
    if override:
        path = pathlib.Path(override)
        if path.is_file():
            return str(path)
        raise WhisperCliNotFoundError(f"Specified whisper-cli not found: {override}")

    found = shutil.which("whisper-cli")
    if found:
        return found

    raise WhisperCliNotFoundError(
        "whisper-cli not found in PATH. "
        "Install via 'brew install whisper-cpp' or set path in settings."
    )


class FileTranscriber:
    """파일 기반 whisper-cli 전사기.

    whisper-cli를 subprocess로 호출하여 오디오 파일을 전사한다.
    P2에서 RealtimeTranscriber로 확장할 기반 클래스.
    """

    def __init__(
        self,
        model_name: str = "small",
        language: str = "auto",
        whisper_cli_path: str | None = None,
    ) -> None:
        """FileTranscriber를 초기화한다.

        Args:
            model_name: Whisper 모델 이름 ("small", "medium", "large-v3")
            language: 전사 언어 ("auto", "en", "ko", "zh", "ja")
            whisper_cli_path: whisper-cli 바이너리 경로 (None이면 자동 탐색)

        Raises:
            WhisperCliNotFoundError: whisper-cli를 찾을 수 없을 때
            WhisperModelNotFoundError: 모델 파일이 없을 때
        """
        self._cli_path = _resolve_whisper_cli(whisper_cli_path)
        self._model_path = get_model_path(model_name)
        self._model_name = model_name
        self._language = language

        if not is_model_downloaded(model_name):
            raise WhisperModelNotFoundError(
                f"Model '{model_name}' not downloaded. "
                f"Expected at: {self._model_path}"
            )

    def transcribe_file(
        self,
        audio_path: pathlib.Path,
        *,
        timeout: int = 300,
    ) -> TranscriptionResult:
        """오디오 파일을 전사한다.

        Args:
            audio_path: 전사할 오디오 파일 경로
            timeout: subprocess 타임아웃 (초)

        Returns:
            전사 결과

        Raises:
            FileNotFoundError: 오디오 파일이 없을 때
            AudioFormatError: 지원하지 않는 포맷일 때
            TranscriptionError: 전사 프로세스 오류 시
        """
        validate_audio_file(audio_path)

        cmd = [
            self._cli_path,
            "-m", str(self._model_path),
            "-l", self._language,
            "-oj",
            "-f", str(audio_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as e:
            raise TranscriptionError(
                f"Transcription timed out after {timeout}s"
            ) from e
        except OSError as e:
            raise TranscriptionError(f"Failed to execute whisper-cli: {e}") from e

        if result.returncode != 0:
            raise TranscriptionError(
                f"whisper-cli exited with code {result.returncode}: "
                f"{result.stderr[:500]}"
            )

        segments = _parse_whisper_output(result.stdout, self._language)
        duration = segments[-1]["end"] if segments else 0.0

        return TranscriptionResult(
            segments=segments,
            language=self._language,
            model=f"whisper-{self._model_name}",
            duration_seconds=duration,
            raw_output=result.stdout,
        )


def _parse_whisper_output(raw_json: str, language: str) -> list[dict[str, Any]]:
    """whisper-cli -oj JSON 출력을 segment 리스트로 변환한다.

    whisper-cli 출력 형식:
        {"transcription": [{"timestamps": {...}, "offsets": {"from": ms, "to": ms}, "text": "..."}]}

    변환 결과:
        [{"start": float초, "end": float초, "text": str, "language": str, "confidence": 1.0}]

    Args:
        raw_json: whisper-cli의 stdout JSON 문자열
        language: 전사에 사용된 언어 코드

    Returns:
        세그먼트 딕셔너리 리스트

    Raises:
        TranscriptionError: JSON 파싱 실패 시
    """
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as e:
        raise TranscriptionError(f"Failed to parse whisper-cli output: {e}") from e

    entries = data.get("transcription", [])
    segments: list[dict[str, Any]] = []

    for entry in entries:
        text = entry.get("text", "").strip()
        if not text:
            continue

        offsets = entry.get("offsets", {})
        start_ms = offsets.get("from", 0)
        end_ms = offsets.get("to", 0)

        segments.append({
            "start": start_ms / 1000.0,
            "end": end_ms / 1000.0,
            "text": text,
            "language": language,
            "confidence": 1.0,
        })

    return segments
