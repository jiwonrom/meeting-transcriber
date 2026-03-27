"""SystemAudioToggle 및 DualLevelMeter 위젯 테스트."""

from __future__ import annotations

from PyQt6.QtCore import Qt

from meeting_transcriber.ui.widgets.dual_level_meter import DualLevelMeter
from meeting_transcriber.ui.widgets.toggle_switch import SystemAudioToggle


def test_toggle_initial_state(qtbot):
    """토글의 초기 상태를 확인한다."""
    toggle = SystemAudioToggle()
    qtbot.addWidget(toggle)

    assert toggle.isChecked() is False
    assert toggle._thumb_pos == 0.0


def test_toggle_emits_signal(qtbot):
    """BlackHole 사용 가능 시 클릭하면 toggled 시그널을 발생시킨다."""
    toggle = SystemAudioToggle()
    qtbot.addWidget(toggle)
    toggle.set_blackhole_available(True)

    with qtbot.waitSignal(toggle.toggled, timeout=1000) as blocker:
        qtbot.mouseClick(toggle, Qt.MouseButton.LeftButton)

    assert blocker.args == [True]
    assert toggle.isChecked() is True


def test_toggle_disabled_emits_setup_requested(qtbot):
    """BlackHole 미설치 시 클릭하면 setup_requested 시그널을 발생시킨다."""
    toggle = SystemAudioToggle()
    qtbot.addWidget(toggle)
    toggle.set_blackhole_available(False)

    toggled_emitted = False

    def on_toggled(_: bool) -> None:
        nonlocal toggled_emitted
        toggled_emitted = True

    toggle.toggled.connect(on_toggled)

    with qtbot.waitSignal(toggle.setup_requested, timeout=1000):
        qtbot.mouseClick(toggle, Qt.MouseButton.LeftButton)

    assert not toggled_emitted
    assert toggle.isChecked() is False


def test_toggle_locked_during_recording(qtbot):
    """녹음 중에는 클릭해도 시그널이 발생하지 않는다."""
    toggle = SystemAudioToggle()
    qtbot.addWidget(toggle)
    toggle.set_blackhole_available(True)
    toggle.set_recording(True)

    toggled_emitted = False
    setup_emitted = False

    toggle.toggled.connect(lambda _: None)
    toggle.setup_requested.connect(lambda: None)

    def on_toggled(_: bool) -> None:
        nonlocal toggled_emitted
        toggled_emitted = True

    def on_setup() -> None:
        nonlocal setup_emitted
        setup_emitted = True

    toggle.toggled.connect(on_toggled)
    toggle.setup_requested.connect(on_setup)

    qtbot.mouseClick(toggle, Qt.MouseButton.LeftButton)

    assert not toggled_emitted
    assert not setup_emitted
    assert toggle.isChecked() is False


def test_dual_level_meter_single_mode(qtbot):
    """기본 모드에서는 시스템 바가 숨겨져 있다."""
    meter = DualLevelMeter()
    qtbot.addWidget(meter)

    assert meter._system_bar.isHidden()
    assert not meter._mic_bar.isHidden()


def test_dual_level_meter_dual_mode(qtbot):
    """듀얼 모드에서는 시스템 바가 표시된다."""
    meter = DualLevelMeter()
    qtbot.addWidget(meter)

    meter.set_dual_mode(True)

    assert not meter._system_bar.isHidden()
    assert not meter._mic_bar.isHidden()
    assert not meter._mic_label.isHidden()
    assert not meter._system_label.isHidden()
