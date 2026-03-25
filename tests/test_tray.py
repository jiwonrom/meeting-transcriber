"""tray 모듈 단위 테스트."""
from __future__ import annotations

from meeting_transcriber.ui.tray import TrayIcon, _create_tray_icon


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
    assert tray.toolTip() == "Meeting Transcriber"
    assert not tray.is_recording


def test_tray_menu_items(qtbot: object) -> None:
    """트레이 메뉴에 필수 항목이 있는지 확인."""
    tray = TrayIcon()
    menu = tray.menu
    actions = menu.actions()
    texts = [a.text() for a in actions if not a.isSeparator()]

    assert "Start Recording" in texts
    assert "Show Window" in texts
    assert "Toggle Overlay" in texts
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
