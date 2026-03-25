"""transcriber 모듈 단위 테스트."""
from __future__ import annotations

import json
import pathlib
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from meeting_transcriber.core.transcriber import (
    FileTranscriber,
    TranscriptionResult,
    _parse_whisper_output,
    _resolve_whisper_cli,
)
from meeting_transcriber.utils.exceptions import (
    AudioFormatError,
    TranscriptionError,
    WhisperCliNotFoundError,
    WhisperModelNotFoundError,
)

# -- whisper-cli JSON 출력 fixtures --

SAMPLE_WHISPER_OUTPUT = json.dumps({
    "transcription": [
        {
            "timestamps": {"from": "00:00:00,000", "to": "00:00:02,500"},
            "offsets": {"from": 0, "to": 2500},
            "text": " Good morning everyone",
        },
        {
            "timestamps": {"from": "00:00:02,500", "to": "00:00:05,000"},
            "offsets": {"from": 2500, "to": 5000},
            "text": " Let's get started",
        },
    ]
})

SAMPLE_WHISPER_OUTPUT_WITH_EMPTY = json.dumps({
    "transcription": [
        {
            "timestamps": {"from": "00:00:00,000", "to": "00:00:01,000"},
            "offsets": {"from": 0, "to": 1000},
            "text": " ",
        },
        {
            "timestamps": {"from": "00:00:01,000", "to": "00:00:03,000"},
            "offsets": {"from": 1000, "to": 3000},
            "text": " Hello",
        },
    ]
})


# -- _parse_whisper_output 테스트 --


def test_parse_whisper_output_basic() -> None:
    """기본 JSON 파싱이 올바른 segment 스키마를 반환하는지 확인."""
    segments = _parse_whisper_output(SAMPLE_WHISPER_OUTPUT, "en")

    assert len(segments) == 2
    seg = segments[0]
    assert seg["start"] == 0.0
    assert seg["end"] == 2.5
    assert seg["text"] == "Good morning everyone"
    assert seg["language"] == "en"
    assert seg["confidence"] == 1.0


def test_parse_whisper_output_multiple_segments() -> None:
    """여러 세그먼트의 순서와 값이 올바른지 확인."""
    segments = _parse_whisper_output(SAMPLE_WHISPER_OUTPUT, "en")

    assert segments[0]["start"] == 0.0
    assert segments[0]["end"] == 2.5
    assert segments[1]["start"] == 2.5
    assert segments[1]["end"] == 5.0


def test_parse_whisper_output_strips_whitespace() -> None:
    """텍스트 앞뒤 공백이 제거되는지 확인."""
    segments = _parse_whisper_output(SAMPLE_WHISPER_OUTPUT, "en")
    assert segments[0]["text"] == "Good morning everyone"
    assert not segments[0]["text"].startswith(" ")


def test_parse_whisper_output_filters_empty() -> None:
    """빈 텍스트 세그먼트가 필터링되는지 확인."""
    segments = _parse_whisper_output(SAMPLE_WHISPER_OUTPUT_WITH_EMPTY, "en")
    assert len(segments) == 1
    assert segments[0]["text"] == "Hello"


def test_parse_whisper_output_invalid_json() -> None:
    """잘못된 JSON에 TranscriptionError를 발생시키는지 확인."""
    with pytest.raises(TranscriptionError, match="Failed to parse"):
        _parse_whisper_output("not json at all", "en")


def test_parse_whisper_output_empty_transcription() -> None:
    """빈 transcription 배열에서 빈 리스트를 반환하는지 확인."""
    segments = _parse_whisper_output('{"transcription": []}', "en")
    assert segments == []


def test_parse_whisper_output_language_auto() -> None:
    """language='auto'가 세그먼트에 그대로 전달되는지 확인."""
    segments = _parse_whisper_output(SAMPLE_WHISPER_OUTPUT, "auto")
    assert all(s["language"] == "auto" for s in segments)


# -- _resolve_whisper_cli 테스트 --


def test_resolve_whisper_cli_override(tmp_path: pathlib.Path) -> None:
    """사용자 지정 경로가 유효하면 그대로 반환하는지 확인."""
    cli = tmp_path / "whisper-cli"
    cli.write_bytes(b"fake binary")
    assert _resolve_whisper_cli(str(cli)) == str(cli)


def test_resolve_whisper_cli_override_missing() -> None:
    """사용자 지정 경로가 없을 때 에러를 발생시키는지 확인."""
    with pytest.raises(WhisperCliNotFoundError, match="Specified whisper-cli not found"):
        _resolve_whisper_cli("/nonexistent/whisper-cli")


def test_resolve_whisper_cli_from_path() -> None:
    """PATH에서 whisper-cli를 찾는지 확인."""
    with patch("shutil.which", return_value="/usr/local/bin/whisper-cli"):
        assert _resolve_whisper_cli() == "/usr/local/bin/whisper-cli"


def test_resolve_whisper_cli_not_found() -> None:
    """PATH에도 없을 때 에러를 발생시키는지 확인."""
    with patch("shutil.which", return_value=None):
        with pytest.raises(WhisperCliNotFoundError, match="not found in PATH"):
            _resolve_whisper_cli()


# -- FileTranscriber 초기화 테스트 --


def test_file_transcriber_init_model_not_downloaded(tmp_path: pathlib.Path) -> None:
    """모델이 다운로드되지 않았을 때 에러를 발생시키는지 확인."""
    with (
        patch("shutil.which", return_value="/usr/local/bin/whisper-cli"),
        patch(
            "meeting_transcriber.core.transcriber.is_model_downloaded",
            return_value=False,
        ),
        patch(
            "meeting_transcriber.core.transcriber.get_model_path",
            return_value=tmp_path / "ggml-small.bin",
        ),
    ):
        with pytest.raises(WhisperModelNotFoundError, match="not downloaded"):
            FileTranscriber(model_name="small")


# -- FileTranscriber.transcribe_file 테스트 --


@pytest.fixture
def transcriber(tmp_path: pathlib.Path) -> FileTranscriber:
    """mock된 FileTranscriber 인스턴스를 반환한다."""
    model_file = tmp_path / "ggml-small.bin"
    model_file.write_bytes(b"fake model")

    with (
        patch("shutil.which", return_value="/usr/local/bin/whisper-cli"),
        patch(
            "meeting_transcriber.core.transcriber.is_model_downloaded",
            return_value=True,
        ),
        patch(
            "meeting_transcriber.core.transcriber.get_model_path",
            return_value=model_file,
        ),
    ):
        return FileTranscriber(model_name="small", language="en")


def _mock_whisper_run(tmp_path: pathlib.Path, json_content: str) -> MagicMock:
    """whisper-cli 실행을 mock한다. -of로 지정된 경로에 JSON 파일을 생성."""

    def side_effect(cmd: list[str], **kwargs: object) -> MagicMock:
        # cmd에서 -of 다음 값 찾기
        if "-of" in cmd:
            idx = cmd.index("-of")
            output_base = pathlib.Path(cmd[idx + 1])
            output_json = output_base.with_suffix(".json")
            output_json.write_text(json_content, encoding="utf-8")

        result = MagicMock()
        result.returncode = 0
        result.stdout = ""
        result.stderr = ""
        return result

    return MagicMock(side_effect=side_effect)


def test_transcribe_file_success(transcriber: FileTranscriber, tmp_path: pathlib.Path) -> None:
    """전사 성공 시 올바른 TranscriptionResult를 반환하는지 확인."""
    audio = tmp_path / "test.wav"
    audio.write_bytes(b"fake audio")

    mock_run = _mock_whisper_run(tmp_path, SAMPLE_WHISPER_OUTPUT)

    with patch("subprocess.run", mock_run):
        result = transcriber.transcribe_file(audio)

    assert isinstance(result, TranscriptionResult)
    assert len(result.segments) == 2
    assert result.language == "en"
    assert result.model == "whisper-small"
    assert result.duration_seconds == 5.0


def test_transcribe_file_subprocess_failure(
    transcriber: FileTranscriber, tmp_path: pathlib.Path
) -> None:
    """subprocess 실패 시 TranscriptionError를 발생시키는지 확인."""
    audio = tmp_path / "test.wav"
    audio.write_bytes(b"fake audio")

    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "error: model file not found"

    with patch("subprocess.run", return_value=mock_result):
        with pytest.raises(TranscriptionError, match="exited with code 1"):
            transcriber.transcribe_file(audio)


def test_transcribe_file_timeout(
    transcriber: FileTranscriber, tmp_path: pathlib.Path
) -> None:
    """타임아웃 시 TranscriptionError를 발생시키는지 확인."""
    audio = tmp_path / "test.wav"
    audio.write_bytes(b"fake audio")

    timeout_err = subprocess.TimeoutExpired(cmd="whisper-cli", timeout=300)
    with patch("subprocess.run", side_effect=timeout_err):
        with pytest.raises(TranscriptionError, match="timed out"):
            transcriber.transcribe_file(audio)


def test_transcribe_file_invalid_format(
    transcriber: FileTranscriber, tmp_path: pathlib.Path
) -> None:
    """지원하지 않는 오디오 포맷에 AudioFormatError를 발생시키는지 확인."""
    txt = tmp_path / "test.txt"
    txt.write_bytes(b"not audio")
    with pytest.raises(AudioFormatError):
        transcriber.transcribe_file(txt)


def test_transcribe_file_missing(
    transcriber: FileTranscriber, tmp_path: pathlib.Path
) -> None:
    """존재하지 않는 파일에 FileNotFoundError를 발생시키는지 확인."""
    with pytest.raises(FileNotFoundError):
        transcriber.transcribe_file(tmp_path / "nonexistent.wav")


def test_language_parameter_in_cli_command(
    tmp_path: pathlib.Path,
) -> None:
    """CLI 명령어에 language 파라미터가 올바르게 전달되는지 확인."""
    model_file = tmp_path / "ggml-small.bin"
    model_file.write_bytes(b"fake model")
    audio = tmp_path / "test.wav"
    audio.write_bytes(b"fake audio")

    mock_run = _mock_whisper_run(tmp_path, '{"transcription": []}')

    with (
        patch("shutil.which", return_value="/usr/local/bin/whisper-cli"),
        patch(
            "meeting_transcriber.core.transcriber.is_model_downloaded",
            return_value=True,
        ),
        patch(
            "meeting_transcriber.core.transcriber.get_model_path",
            return_value=model_file,
        ),
        patch("subprocess.run", mock_run) as patched_run,
    ):
        t = FileTranscriber(model_name="small", language="ko")
        t.transcribe_file(audio)

        cmd = patched_run.call_args[0][0]
        assert "-l" in cmd
        lang_idx = cmd.index("-l")
        assert cmd[lang_idx + 1] == "ko"
