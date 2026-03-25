"""Meeting Transcriber — 메인 엔트리포인트."""
from __future__ import annotations

import os
import sys

os.environ["QT_LOGGING_RULES"] = "qt.text.font.db=false"

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QApplication, QDialog

from meeting_transcriber.core.model_manager import is_model_downloaded
from meeting_transcriber.storage.workspace import WorkspaceManager
from meeting_transcriber.ui.main_window import MainWindow
from meeting_transcriber.ui.onboarding import OnboardingWizard
from meeting_transcriber.ui.overlay import OverlayWidget
from meeting_transcriber.ui.settings_dialog import SettingsDialog
from meeting_transcriber.ui.theme import ThemeEngine
from meeting_transcriber.ui.tray import TrayIcon
from meeting_transcriber.utils.shortcuts import ShortcutManager


def main() -> None:
    """앱을 시작한다."""
    app = QApplication(sys.argv)
    app.setApplicationName("Meeting Transcriber")
    app.setApplicationDisplayName("Meeting Transcriber")
    app.setQuitOnLastWindowClosed(False)

    # 첫 실행 온보딩
    if not is_model_downloaded("small"):
        wizard = OnboardingWizard()
        if wizard.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)

    # 워크스페이스
    workspace = WorkspaceManager()
    workspace.ensure_default_folders()

    # 테마
    theme = ThemeEngine()

    # 메인 윈도우
    window = MainWindow(workspace=workspace)

    # 오버레이
    overlay = OverlayWidget()
    overlay.apply_theme(theme)
    overlay.restore_position()

    # 트레이
    tray = TrayIcon()
    tray.show()

    # 단축키
    shortcuts = ShortcutManager(window)

    # -- macOS 메뉴바 --
    menubar = window.menuBar()
    assert menubar is not None

    file_menu = menubar.addMenu("File")
    assert file_menu is not None

    new_recording = QAction("New Recording", window)
    new_recording.setShortcut("Ctrl+N")
    new_recording.triggered.connect(lambda: window.toggle_recording(not window.is_recording))
    file_menu.addAction(new_recording)

    file_menu.addSeparator()

    settings_action = QAction("Settings...", window)
    settings_action.setShortcut("Ctrl+,")
    settings_action.triggered.connect(lambda: SettingsDialog(window).exec())
    file_menu.addAction(settings_action)

    view_menu = menubar.addMenu("View")
    assert view_menu is not None

    toggle_overlay = QAction("Toggle Overlay", window)
    toggle_overlay.setShortcut("Ctrl+Shift+C")
    toggle_overlay.triggered.connect(overlay.toggle_visibility)
    view_menu.addAction(toggle_overlay)

    # -- Signal/Slot 연결 --
    tray.recording_toggled.connect(window.toggle_recording)
    tray.show_window_requested.connect(window.show)
    tray.show_window_requested.connect(window.raise_)
    tray.overlay_toggle_requested.connect(overlay.toggle_visibility)
    tray.quit_requested.connect(app.quit)

    window.caption_updated.connect(overlay.append_caption)
    window.recording_started.connect(overlay.clear_caption)
    window.recording_started.connect(lambda: overlay.set_recording(True))
    window.recording_stopped.connect(lambda: overlay.set_recording(False))

    # 단축키
    def _toggle_recording() -> None:
        window.toggle_recording(not window.is_recording)

    shortcuts.register("Ctrl+Shift+R", _toggle_recording)

    window.show()

    ret = app.exec()  # noqa: F841
    sys.exit(ret)


if __name__ == "__main__":
    main()
