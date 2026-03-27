"""BlackHoleSetupWizard UI 테스트."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from PyQt6.QtCore import Qt

from meeting_transcriber.ui.blackhole_wizard import BlackHoleSetupWizard


@patch("meeting_transcriber.ui.blackhole_wizard.detect_blackhole", return_value=None)
def test_wizard_opens(mock_detect, qtbot):
    """위저드가 5페이지 스택으로 열린다."""
    wizard = BlackHoleSetupWizard()
    qtbot.addWidget(wizard)
    wizard.show()

    assert wizard.isVisible() or not wizard.isHidden()
    assert wizard._stack.count() == 5


@patch("meeting_transcriber.ui.blackhole_wizard.detect_blackhole", return_value=None)
def test_wizard_step_navigation(mock_detect, qtbot):
    """Next 클릭 시 다음 단계로 이동한다."""
    wizard = BlackHoleSetupWizard()
    qtbot.addWidget(wizard)

    assert wizard._stack.currentIndex() == 0

    # Step 1 -> Step 2
    qtbot.mouseClick(wizard._next_btn, Qt.MouseButton.LeftButton)
    assert wizard._stack.currentIndex() == 1
    assert not wizard._back_btn.isHidden()


@patch("meeting_transcriber.ui.blackhole_wizard.detect_blackhole", return_value=None)
def test_wizard_back_navigation(mock_detect, qtbot):
    """Back 클릭 시 이전 단계로 이동한다."""
    wizard = BlackHoleSetupWizard()
    qtbot.addWidget(wizard)

    # Go to step 2
    qtbot.mouseClick(wizard._next_btn, Qt.MouseButton.LeftButton)
    assert wizard._stack.currentIndex() == 1

    # Back to step 1
    qtbot.mouseClick(wizard._back_btn, Qt.MouseButton.LeftButton)
    assert wizard._stack.currentIndex() == 0
    assert wizard._back_btn.isHidden()


@patch("meeting_transcriber.ui.blackhole_wizard.detect_blackhole", return_value=None)
def test_wizard_step_indicator(mock_detect, qtbot):
    """단계 표시기가 올바르게 업데이트된다."""
    wizard = BlackHoleSetupWizard()
    qtbot.addWidget(wizard)

    assert wizard._step_label.text() == "Step 1 of 5"

    # Go to step 2
    qtbot.mouseClick(wizard._next_btn, Qt.MouseButton.LeftButton)
    assert wizard._step_label.text() == "Step 2 of 5"


@patch("meeting_transcriber.ui.blackhole_wizard.detect_blackhole", return_value=None)
def test_wizard_copy_command(mock_detect, qtbot):
    """Copy Command 버튼이 클립보드에 명령어를 복사한다."""
    wizard = BlackHoleSetupWizard()
    qtbot.addWidget(wizard)

    # Go to step 2 (install page)
    qtbot.mouseClick(wizard._next_btn, Qt.MouseButton.LeftButton)

    with patch(
        "meeting_transcriber.ui.blackhole_wizard.QApplication.clipboard"
    ) as mock_clipboard:
        mock_cb = MagicMock()
        mock_clipboard.return_value = mock_cb
        qtbot.mouseClick(wizard._copy_btn, Qt.MouseButton.LeftButton)
        mock_cb.setText.assert_called_once_with("brew install blackhole-2ch")


def test_wizard_detection_polling(qtbot):
    """BlackHole 감지 폴링이 상태를 업데이트한다."""
    with patch(
        "meeting_transcriber.ui.blackhole_wizard.detect_blackhole", return_value=None
    ) as mock_detect:
        wizard = BlackHoleSetupWizard()
        qtbot.addWidget(wizard)

        # Go to step 2 to start timer
        qtbot.mouseClick(wizard._next_btn, Qt.MouseButton.LeftButton)

        # 아직 미감지
        assert "Waiting" in wizard._detection_status.text()

        # 감지됨
        mock_detect.return_value = 5
        wizard._poll_blackhole_detection()

        assert "detected" in wizard._detection_status.text()
        assert wizard._next_btn.isEnabled()


@patch("meeting_transcriber.ui.blackhole_wizard.detect_blackhole", return_value=None)
def test_wizard_audio_output_page_has_buttons(mock_detect, qtbot):
    """Step 3에 Open Sound Settings와 Open Audio MIDI Setup 버튼이 있다."""
    wizard = BlackHoleSetupWizard()
    qtbot.addWidget(wizard)

    # Navigate to step 3 (audio output page)
    # Step 1 -> Step 2
    qtbot.mouseClick(wizard._next_btn, Qt.MouseButton.LeftButton)
    # Enable next (simulate detection)
    mock_detect.return_value = 5
    wizard._poll_blackhole_detection()
    # Step 2 -> Step 3
    qtbot.mouseClick(wizard._next_btn, Qt.MouseButton.LeftButton)
    assert wizard._stack.currentIndex() == 2

    # 페이지 내의 모든 QPushButton 텍스트 확인
    from PyQt6.QtWidgets import QPushButton

    page = wizard._stack.widget(2)
    buttons = page.findChildren(QPushButton)
    button_texts = [b.text() for b in buttons]

    assert "Open Sound Settings" in button_texts
    assert "Open Audio MIDI Setup" in button_texts


@patch("meeting_transcriber.ui.blackhole_wizard.detect_blackhole", return_value=5)
@patch("meeting_transcriber.ui.blackhole_wizard.get_device_uid", return_value="uid-test")
@patch("meeting_transcriber.ui.blackhole_wizard.create_aggregate_device", return_value=42)
def test_wizard_aggregate_creation_success(
    mock_create, mock_uid, mock_detect, qtbot
):
    """Aggregate Device 생성 성공 시 다음 단계 진행 가능하다."""
    wizard = BlackHoleSetupWizard()
    qtbot.addWidget(wizard)

    # 생성 성공 시뮬레이션
    wizard._on_aggregate_creation_finished(True, "Aggregate Device created!", 42)

    assert wizard._aggregate_device_id == 42
    assert wizard._next_btn.isEnabled()
    assert "created" in wizard._aggregate_status.text().lower()
