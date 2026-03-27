"""main_window 모듈 단위 테스트."""

from __future__ import annotations

import json
import pathlib
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QSplitter

from meeting_transcriber.storage.workspace import WorkspaceManager
from meeting_transcriber.ui.main_window import (
    MainWindow,
    RecordButton,
    TranscriptViewer,
    _fmt_duration,
)
from meeting_transcriber.ui.widgets.dual_level_meter import DualLevelMeter
from meeting_transcriber.ui.widgets.toggle_switch import SystemAudioToggle
from meeting_transcriber.utils.constants import APP_NAME


def test_main_window_creation(qtbot: object, tmp_path: pathlib.Path) -> None:
    """메인 윈도우가 정상 생성되는지 확인."""
    ws = WorkspaceManager(workspace_dir=tmp_path)
    window = MainWindow(workspace=ws)
    qtbot.addWidget(window)  # type: ignore[union-attr]
    assert window.windowTitle() == APP_NAME


def test_main_window_has_splitter(qtbot: object, tmp_path: pathlib.Path) -> None:
    """스플리터 레이아웃이 구성되어 있는지 확인."""
    ws = WorkspaceManager(workspace_dir=tmp_path)
    window = MainWindow(workspace=ws)
    qtbot.addWidget(window)  # type: ignore[union-attr]
    assert isinstance(window.splitter, QSplitter)


def test_main_window_has_record_button(qtbot: object, tmp_path: pathlib.Path) -> None:
    """녹음 버튼이 존재하는지 확인."""
    ws = WorkspaceManager(workspace_dir=tmp_path)
    window = MainWindow(workspace=ws)
    qtbot.addWidget(window)  # type: ignore[union-attr]
    assert isinstance(window.record_button, RecordButton)


def test_record_button_state(qtbot: object) -> None:
    """RecordButton 상태 전환이 동작하는지 확인."""
    btn = RecordButton()
    qtbot.addWidget(btn)  # type: ignore[union-attr]
    assert btn._recording is False

    btn.set_recording(True)
    assert btn._recording is True

    btn.set_recording(False)
    assert btn._recording is False


def test_main_window_level_meter(qtbot: object, tmp_path: pathlib.Path) -> None:
    """오디오 레벨 미터가 업데이트되는지 확인."""
    ws = WorkspaceManager(workspace_dir=tmp_path)
    window = MainWindow(workspace=ws)
    qtbot.addWidget(window)  # type: ignore[union-attr]
    window._on_level_changed(0.5)
    assert window._level_meter._mic_bar.value() == 50


def test_system_audio_toggle_exists(qtbot: object, tmp_path: pathlib.Path) -> None:
    """SystemAudioToggle이 MainWindow에 존재하는지 확인."""
    ws = WorkspaceManager(workspace_dir=tmp_path)
    window = MainWindow(workspace=ws)
    qtbot.addWidget(window)  # type: ignore[union-attr]
    assert isinstance(window._system_audio_toggle, SystemAudioToggle)


def test_level_meter_is_dual(qtbot: object, tmp_path: pathlib.Path) -> None:
    """DualLevelMeter가 MainWindow에 존재하는지 확인."""
    ws = WorkspaceManager(workspace_dir=tmp_path)
    window = MainWindow(workspace=ws)
    qtbot.addWidget(window)  # type: ignore[union-attr]
    assert isinstance(window._level_meter, DualLevelMeter)


@patch("meeting_transcriber.ui.main_window.resolve_device_by_uid", return_value=5)
@patch("meeting_transcriber.ui.main_window.AudioCaptureWorker")
def test_start_recording_with_system_audio(
    mock_worker_cls: MagicMock,
    mock_resolve: MagicMock,
    qtbot: object,
    tmp_path: pathlib.Path,
) -> None:
    """시스템 오디오 활성 시 Aggregate Device로 녹음을 시작하는지 확인."""
    ws = WorkspaceManager(workspace_dir=tmp_path)
    window = MainWindow(workspace=ws)
    qtbot.addWidget(window)  # type: ignore[union-attr]

    mock_worker = MagicMock()
    mock_worker_cls.return_value = mock_worker

    with patch(
        "meeting_transcriber.ui.main_window.load_settings",
        return_value={
            "audio": {
                "device": None,
                "system_audio": {
                    "enabled": True,
                    "aggregate_device_uid": "com.scribe.aggregate-device",
                },
            },
            "whisper_model": "small",
            "language": "auto",
        },
    ):
        window.start_recording()

    mock_worker_cls.assert_called_once_with(device=5)
    assert window._recording_with_system_audio is True


@patch("meeting_transcriber.ui.main_window.resolve_device_by_uid", return_value=None)
@patch("meeting_transcriber.ui.main_window.AudioCaptureWorker")
def test_start_recording_fallback_to_mic(
    mock_worker_cls: MagicMock,
    mock_resolve: MagicMock,
    qtbot: object,
    tmp_path: pathlib.Path,
) -> None:
    """Aggregate Device 미발견 시 마이크 전용으로 폴백하는지 확인."""
    ws = WorkspaceManager(workspace_dir=tmp_path)
    window = MainWindow(workspace=ws)
    qtbot.addWidget(window)  # type: ignore[union-attr]

    mock_worker = MagicMock()
    mock_worker_cls.return_value = mock_worker

    with patch(
        "meeting_transcriber.ui.main_window.load_settings",
        return_value={
            "audio": {
                "device": None,
                "system_audio": {
                    "enabled": True,
                    "aggregate_device_uid": "com.scribe.aggregate-device",
                },
            },
            "whisper_model": "small",
            "language": "auto",
        },
    ):
        window.start_recording()

    mock_worker_cls.assert_called_once_with(device=None)
    assert window._recording_with_system_audio is False
    assert "disconnected" in window._status_bar.currentMessage().lower()


@patch("meeting_transcriber.ui.main_window.AudioCaptureWorker")
def test_mid_recording_system_audio_failure(
    mock_worker_cls: MagicMock,
    qtbot: object,
    tmp_path: pathlib.Path,
) -> None:
    """녹음 중 시스템 오디오 실패 시 마이크 전용으로 재시작하는지 확인."""
    ws = WorkspaceManager(workspace_dir=tmp_path)
    window = MainWindow(workspace=ws)
    qtbot.addWidget(window)  # type: ignore[union-attr]

    mock_worker = MagicMock()
    mock_worker_cls.return_value = mock_worker

    # Simulate mid-recording state
    window._recording_with_system_audio = True
    window._is_recording = True
    window._level_meter.set_dual_mode(True)

    with patch(
        "meeting_transcriber.ui.main_window.load_settings",
        return_value={
            "audio": {"device": None, "system_audio": {"enabled": True}},
        },
    ):
        window._on_capture_error("device disconnected")

    # Verify fallback behavior
    assert window._recording_with_system_audio is False
    assert "system audio lost" in window._status_bar.currentMessage().lower()
    assert not window._level_meter._system_bar.isVisible()
    mock_worker_cls.assert_called_once_with(device=None)


def test_transcript_viewer_display(qtbot: object, tmp_path: pathlib.Path) -> None:
    """TranscriptViewer가 transcript 내용을 표시하는지 확인."""
    viewer = TranscriptViewer()
    qtbot.addWidget(viewer)  # type: ignore[union-attr]

    transcript_path = tmp_path / "test" / "transcript.json"
    transcript_path.parent.mkdir(parents=True)
    transcript_path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "metadata": {"title": "Test Meeting", "duration_seconds": 60, "languages": ["en"]},
                "segments": [{"start": 0.0, "end": 2.5, "text": "Hello world"}],
            }
        )
    )

    viewer.display_transcript(str(transcript_path))
    assert "Test Meeting" in viewer._title_label.text()
    assert "Hello world" in viewer._original_edit.toPlainText()


def test_transcript_viewer_clear(qtbot: object) -> None:
    """TranscriptViewer의 clear가 동작하는지 확인."""
    viewer = TranscriptViewer()
    qtbot.addWidget(viewer)  # type: ignore[union-attr]
    viewer._title_label.setText("Something")
    viewer.clear()
    assert viewer._title_label.text() == ""


def test_transcript_viewer_invalid_path(qtbot: object) -> None:
    """존재하지 않는 파일 표시 시 에러 메시지."""
    viewer = TranscriptViewer()
    qtbot.addWidget(viewer)  # type: ignore[union-attr]
    viewer.display_transcript("/nonexistent/path.json")
    assert "Error" in viewer._title_label.text()


def test_fmt_duration() -> None:
    """_fmt_duration 포맷이 올바른지 확인."""
    assert _fmt_duration(0) == "0:00"
    assert _fmt_duration(65) == "1:05"
    assert _fmt_duration(3723) == "1:02:03"


def test_recording_list_populated(qtbot: object, tmp_path: pathlib.Path) -> None:
    """녹음이 있으면 리스트에 표시되는지 확인."""
    ws = WorkspaceManager(workspace_dir=tmp_path)
    ws.ensure_default_folders()

    meeting = tmp_path / "Work" / "test-meeting"
    meeting.mkdir(parents=True)
    (meeting / "transcript.json").write_text(
        json.dumps(
            {
                "version": "1.0",
                "metadata": {"title": "Test", "duration_seconds": 30, "languages": ["en"]},
                "segments": [{"start": 0.0, "end": 1.0, "text": "Hi"}],
            }
        )
    )

    window = MainWindow(workspace=ws)
    qtbot.addWidget(window)  # type: ignore[union-attr]
    assert window._recording_list.count() >= 1


def test_transcript_viewer_has_tabs(qtbot: object) -> None:
    """TranscriptViewer에 3개 탭이 있는지 확인."""
    viewer = TranscriptViewer()
    qtbot.addWidget(viewer)  # type: ignore[union-attr]
    assert viewer._tabs.count() == 3
    assert viewer._tabs.tabText(0) == "Original"
    assert viewer._tabs.tabText(1) == "Proofread"
    assert viewer._tabs.tabText(2) == "Summary"


def test_transcript_viewer_ai_results(qtbot: object, tmp_path: pathlib.Path) -> None:
    """AI 결과가 있는 transcript가 탭에 표시되는지 확인."""
    viewer = TranscriptViewer()
    qtbot.addWidget(viewer)  # type: ignore[union-attr]

    path = tmp_path / "ai_test" / "transcript.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "metadata": {
                    "title": "AI Test",
                    "duration_seconds": 30,
                    "languages": ["en"],
                    "summary": "- Meeting discussed roadmap\n- Action items assigned",
                    "proofread": "Good morning everyone. Let us begin.",
                    "tags": ["meeting", "roadmap"],
                },
                "segments": [{"start": 0.0, "end": 2.0, "text": "Good morning everyone"}],
            }
        )
    )

    viewer.display_transcript(str(path))
    assert "Good morning everyone" in viewer._original_edit.toPlainText()
    assert "Let us begin" in viewer._proofread_edit.toPlainText()
    assert "roadmap" in viewer._summary_edit.toPlainText()
    assert "meeting" in viewer._keywords_label.text()
