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
    assert "system audio disconnected" in window._status_bar.currentMessage().lower()
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


def test_sidebar_integrated(qtbot: object, tmp_path: pathlib.Path) -> None:
    """SidebarWidget이 MainWindow에 통합되어 있는지 확인."""
    from meeting_transcriber.ui.sidebar import SidebarWidget

    ws = WorkspaceManager(workspace_dir=tmp_path)
    ws.ensure_default_folders()

    window = MainWindow(workspace=ws)
    qtbot.addWidget(window)  # type: ignore[union-attr]
    assert isinstance(window.sidebar, SidebarWidget)


def test_transcript_viewer_has_tabs(qtbot: object) -> None:
    """TranscriptViewer에 3개 탭이 있는지 확인."""
    viewer = TranscriptViewer()
    qtbot.addWidget(viewer)  # type: ignore[union-attr]
    assert viewer._tabs.count() == 3
    assert viewer._tabs.tabText(0) == "Original"
    assert viewer._tabs.tabText(1) == "Proofread"
    assert viewer._tabs.tabText(2) == "Summary"


def test_transcript_viewer_speaker_labels(qtbot: object, tmp_path: pathlib.Path) -> None:
    """v2.0 transcript에서 화자 라벨이 인라인 접두사로 표시되는지 확인."""
    viewer = TranscriptViewer()
    qtbot.addWidget(viewer)  # type: ignore[union-attr]

    path = tmp_path / "speaker_test" / "transcript.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "version": "2.0",
                "metadata": {
                    "title": "Speaker Test",
                    "duration_seconds": 30,
                    "languages": ["en"],
                    "speakers": {"SPEAKER_00": "Speaker 1", "SPEAKER_01": "Speaker 2"},
                    "diarization": {"model": "pyannote/speaker-diarization-community-1"},
                },
                "segments": [
                    {"start": 0.0, "end": 2.0, "text": "Hello there", "speaker": "SPEAKER_00"},
                    {"start": 2.0, "end": 4.0, "text": "Hi back", "speaker": "SPEAKER_01"},
                ],
            }
        )
    )

    viewer.display_transcript(str(path))
    html = viewer._original_edit.toHtml()
    assert "Speaker 1:" in html
    assert "Speaker 2:" in html
    assert "font-weight: 600" in html or "font-weight:600" in html


def test_transcript_viewer_no_speaker_labels(qtbot: object, tmp_path: pathlib.Path) -> None:
    """v1.0 transcript에서 화자 접두사가 표시되지 않는지 확인."""
    viewer = TranscriptViewer()
    qtbot.addWidget(viewer)  # type: ignore[union-attr]

    path = tmp_path / "no_speaker" / "transcript.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "metadata": {"title": "No Speaker", "duration_seconds": 10, "languages": ["en"]},
                "segments": [{"start": 0.0, "end": 2.0, "text": "Just text"}],
            }
        )
    )

    viewer.display_transcript(str(path))
    plain = viewer._original_edit.toPlainText()
    assert "Just text" in plain
    assert "Speaker" not in plain


def test_transcript_viewer_identify_btn_states(qtbot: object, tmp_path: pathlib.Path) -> None:
    """recording.wav 존재 여부에 따라 Identify Speakers 버튼 상태가 변하는지 확인."""
    viewer = TranscriptViewer()
    qtbot.addWidget(viewer)  # type: ignore[union-attr]

    # Without recording.wav -> disabled
    path = tmp_path / "no_audio" / "transcript.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "metadata": {"title": "No Audio", "duration_seconds": 10, "languages": ["en"]},
                "segments": [{"start": 0.0, "end": 2.0, "text": "Hi"}],
            }
        )
    )
    viewer.display_transcript(str(path))
    assert not viewer._identify_btn.isEnabled()

    # With recording.wav -> enabled
    path2 = tmp_path / "with_audio" / "transcript.json"
    path2.parent.mkdir(parents=True)
    path2.write_text(
        json.dumps(
            {
                "version": "1.0",
                "metadata": {"title": "Audio", "duration_seconds": 10, "languages": ["en"]},
                "segments": [{"start": 0.0, "end": 2.0, "text": "Hi"}],
            }
        )
    )
    (tmp_path / "with_audio" / "recording.wav").write_bytes(b"RIFF" + b"\x00" * 40)
    viewer.display_transcript(str(path2))
    assert viewer._identify_btn.isEnabled()


def test_transcript_viewer_speaker_panel_visible(qtbot: object, tmp_path: pathlib.Path) -> None:
    """화자가 있는 transcript에서 화자 패널이 표시되는지 확인."""
    viewer = TranscriptViewer()
    qtbot.addWidget(viewer)  # type: ignore[union-attr]

    # No speakers -> hidden
    path1 = tmp_path / "nospeaker" / "transcript.json"
    path1.parent.mkdir(parents=True)
    path1.write_text(
        json.dumps(
            {
                "version": "1.0",
                "metadata": {"title": "NS", "duration_seconds": 10, "languages": ["en"]},
                "segments": [{"start": 0.0, "end": 2.0, "text": "Hi"}],
            }
        )
    )
    viewer.display_transcript(str(path1))
    assert not viewer._speaker_panel.isVisibleTo(viewer)

    # With speakers -> visible
    path2 = tmp_path / "withspeaker" / "transcript.json"
    path2.parent.mkdir(parents=True)
    path2.write_text(
        json.dumps(
            {
                "version": "2.0",
                "metadata": {
                    "title": "WS",
                    "duration_seconds": 10,
                    "languages": ["en"],
                    "speakers": {"SPEAKER_00": "Alice"},
                    "diarization": {},
                },
                "segments": [
                    {"start": 0.0, "end": 2.0, "text": "Hi", "speaker": "SPEAKER_00"},
                ],
            }
        )
    )
    viewer.display_transcript(str(path2))
    assert viewer._speaker_panel.isVisibleTo(viewer)


def test_transcript_viewer_identify_btn_label_reidentify(
    qtbot: object, tmp_path: pathlib.Path
) -> None:
    """diarization 메타데이터 존재 시 버튼이 'Re-identify Speakers'로 표시되는지 확인."""
    viewer = TranscriptViewer()
    qtbot.addWidget(viewer)  # type: ignore[union-attr]

    path = tmp_path / "reidentify" / "transcript.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "version": "2.0",
                "metadata": {
                    "title": "Re-ID",
                    "duration_seconds": 10,
                    "languages": ["en"],
                    "speakers": {"SPEAKER_00": "Speaker 1"},
                    "diarization": {"model": "pyannote/speaker-diarization-community-1"},
                },
                "segments": [
                    {"start": 0.0, "end": 2.0, "text": "Hi", "speaker": "SPEAKER_00"},
                ],
            }
        )
    )
    (tmp_path / "reidentify" / "recording.wav").write_bytes(b"RIFF" + b"\x00" * 40)
    viewer.display_transcript(str(path))
    assert viewer._identify_btn.text() == "Re-identify Speakers"
    assert viewer._identify_btn.isEnabled()


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


def test_template_combo_exists(qtbot: object, tmp_path: pathlib.Path) -> None:
    """template_combo 위젯이 MainWindow에 존재하고 올바른 objectName을 가지는지 확인."""
    ws = WorkspaceManager(workspace_dir=tmp_path)
    window = MainWindow(workspace=ws)
    qtbot.addWidget(window)  # type: ignore[union-attr]

    assert window._template_combo.objectName() == "template_combo"
    assert window._template_combo.count() >= 5  # 5개 빌트인 템플릿


def test_rerun_template_combo_exists(qtbot: object, tmp_path: pathlib.Path) -> None:
    """rerun_template_combo 위젯이 TranscriptViewer에 존재하는지 확인."""
    ws = WorkspaceManager(workspace_dir=tmp_path)
    window = MainWindow(workspace=ws)
    qtbot.addWidget(window)  # type: ignore[union-attr]

    combo = window._transcript_viewer._rerun_template_combo
    assert combo.objectName() == "rerun_template_combo"
    assert combo.count() >= 5


def test_template_combos_different_names(qtbot: object, tmp_path: pathlib.Path) -> None:
    """두 템플릿 콤보의 objectName이 다른지 확인."""
    ws = WorkspaceManager(workspace_dir=tmp_path)
    window = MainWindow(workspace=ws)
    qtbot.addWidget(window)  # type: ignore[union-attr]

    assert (
        window._template_combo.objectName()
        != window._transcript_viewer._rerun_template_combo.objectName()
    )


def test_get_selected_template_key(qtbot: object, tmp_path: pathlib.Path) -> None:
    """기본 템플릿 키가 'general'인지 확인."""
    ws = WorkspaceManager(workspace_dir=tmp_path)
    window = MainWindow(workspace=ws)
    qtbot.addWidget(window)  # type: ignore[union-attr]

    assert window._get_selected_template_key() == "general"


def test_suggest_template(qtbot: object, tmp_path: pathlib.Path) -> None:
    """suggest_template이 템플릿 콤보 선택을 변경하는지 확인."""
    ws = WorkspaceManager(workspace_dir=tmp_path)
    window = MainWindow(workspace=ws)
    qtbot.addWidget(window)  # type: ignore[union-attr]

    window.suggest_template("team_meeting")
    assert window._get_selected_template_key() == "team_meeting"


def test_structured_summary_display(qtbot: object, tmp_path: pathlib.Path) -> None:
    """구조화 dict 요약이 HTML로 표시되는지 확인."""
    viewer = TranscriptViewer()
    qtbot.addWidget(viewer)  # type: ignore[union-attr]

    path = tmp_path / "structured" / "transcript.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "metadata": {
                    "title": "Structured Test",
                    "duration_seconds": 60,
                    "languages": ["en"],
                    "summary": {
                        "decisions": ["Use React for frontend"],
                        "action_items": ["Alice: set up repo"],
                    },
                    "summary_template": "team_meeting",
                },
                "segments": [{"start": 0.0, "end": 2.0, "text": "Hello"}],
            }
        )
    )

    viewer.display_transcript(str(path))
    html = viewer._summary_edit.toHtml()
    assert "Decisions" in html
    assert "Action Items" in html
    assert "Use React for frontend" in html


def test_rerun_ai_btn_exists(qtbot: object, tmp_path: pathlib.Path) -> None:
    """Re-run AI 버튼이 TranscriptViewer에 존재하는지 확인."""
    viewer = TranscriptViewer()
    qtbot.addWidget(viewer)  # type: ignore[union-attr]
    assert viewer._rerun_ai_btn.objectName() == "rerun_ai_btn"
    assert not viewer._rerun_ai_btn.isEnabled()  # 초기에 비활성
