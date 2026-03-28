"""tray 모듈 단위 테스트."""

from __future__ import annotations

from meeting_transcriber.ui.tray import TrayIcon, _create_tray_icon
from meeting_transcriber.utils.constants import APP_NAME


def test_create_tray_icon_idle() -> None:
    """대기 상태 아이콘이 생성되는지 확인."""
    icon = _create_tray_icon(recording=False)
    assert not icon.isNull()


def test_create_tray_icon_recording() -> None:
    """녹음 상태 아이콘이 생성되는지 확인."""
    icon = _create_tray_icon(recording=True)
    assert not icon.isNull()


def test_tray_creation(qtbot: object) -> None:
    """트레이 아이콘이 정상 생성되는지 확인."""
    tray = TrayIcon()
    assert tray.toolTip() == APP_NAME
    assert not tray.is_recording


def test_tray_menu_items(qtbot: object) -> None:
    """트레이 메뉴에 필수 항목이 있는지 확인."""
    tray = TrayIcon()
    menu = tray.menu
    actions = menu.actions()
    texts = [a.text() for a in actions if not a.isSeparator()]

    assert "Start Recording" in texts
    assert f"Show {APP_NAME}" in texts
    assert "Show/Hide Overlay" in texts
    assert "Quit" in texts


def test_tray_recording_toggle(qtbot: object) -> None:
    """녹음 토글 시 상태와 signal이 변경되는지 확인."""
    tray = TrayIcon()

    signals: list[bool] = []
    tray.recording_toggled.connect(lambda v: signals.append(v))

    tray._toggle_recording()
    assert tray.is_recording is True
    assert signals[-1] is True
    assert tray._record_action.text() == "Stop Recording"

    tray._toggle_recording()
    assert tray.is_recording is False
    assert signals[-1] is False
    assert tray._record_action.text() == "Start Recording"


def test_tray_set_recording(qtbot: object) -> None:
    """set_recording으로 외부에서 상태를 설정할 수 있는지 확인."""
    tray = TrayIcon()

    tray.set_recording(True)
    assert tray.is_recording is True
    assert "Recording" in tray.toolTip()

    tray.set_recording(False)
    assert tray.is_recording is False


def test_show_meeting_notification(qtbot: object) -> None:
    """show_meeting_notification이 스누즈 액션을 표시하는지 확인."""
    tray = TrayIcon()
    assert not tray._snooze_action.isVisible()

    tray.show_meeting_notification("Zoom", "team_meeting", "us.zoom.xos")

    assert tray._pending_template == "team_meeting"
    assert tray._pending_bundle_id == "us.zoom.xos"
    assert tray._snooze_action.isVisible()
    assert "Zoom" in tray._snooze_action.text()


def test_notification_click_emits_signal(qtbot: object) -> None:
    """알림 클릭 시 recording_from_detection 시그널이 발신되는지 확인."""
    tray = TrayIcon()
    tray._pending_template = "team_meeting"

    signals: list[str] = []
    tray.recording_from_detection.connect(lambda t: signals.append(t))

    tray._on_notification_clicked()

    assert signals == ["team_meeting"]
    assert tray._pending_template == ""


def test_snooze_emits_signal(qtbot: object) -> None:
    """스누즈 클릭 시 snooze_requested 시그널이 발신되는지 확인."""
    tray = TrayIcon()
    tray._pending_bundle_id = "us.zoom.xos"
    tray._pending_template = "team_meeting"
    tray._snooze_action.setVisible(True)

    signals: list[str] = []
    tray.snooze_requested.connect(lambda b: signals.append(b))

    tray._on_snooze_clicked()

    assert signals == ["us.zoom.xos"]
    assert not tray._snooze_action.isVisible()
    assert tray._pending_bundle_id == ""
    assert tray._pending_template == ""


def test_snooze_action_hidden_after_notification_click(qtbot: object) -> None:
    """알림 클릭 후 스누즈 액션이 숨겨지는지 확인."""
    tray = TrayIcon()
    tray.show_meeting_notification("FaceTime", "one_on_one", "com.apple.FaceTime")
    assert tray._snooze_action.isVisible()

    tray._on_notification_clicked()
    assert not tray._snooze_action.isVisible()


def test_detection_toggled_signal(qtbot: object) -> None:
    """감지 메뉴 토글 시 detection_toggled 시그널이 발신되는지 확인."""
    tray = TrayIcon()

    signals: list[bool] = []
    tray.detection_toggled.connect(lambda v: signals.append(v))

    tray._detection_action.setChecked(False)
    assert signals[-1] is False
    assert "Off" in tray._detection_action.text()

    tray._detection_action.setChecked(True)
    assert signals[-1] is True
    assert "On" in tray._detection_action.text()


def test_set_detection_state(qtbot: object) -> None:
    """set_detection_state가 액션 상태와 텍스트를 업데이트하는지 확인."""
    tray = TrayIcon()

    tray.set_detection_state(False)
    assert not tray._detection_action.isChecked()
    assert "Off" in tray._detection_action.text()

    tray.set_detection_state(True)
    assert tray._detection_action.isChecked()
    assert "On" in tray._detection_action.text()


def test_tray_menu_has_detection_item(qtbot: object) -> None:
    """트레이 메뉴에 Meeting Detection 항목이 있는지 확인."""
    tray = TrayIcon()
    menu = tray.menu
    actions = menu.actions()
    texts = [a.text() for a in actions if not a.isSeparator()]
    assert any("Meeting Detection" in t for t in texts)
