"""Meeting Transcriber — 메인 엔트리포인트."""
from __future__ import annotations

import sys

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
    """앱을 시작한다.

    QApplication을 생성하고, 첫 실행이면 온보딩을 표시한 뒤,
    모든 UI 컴포넌트를 초기화하고 Signal/Slot으로 연결한다.
    """
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # 트레이 상주

    # 첫 실행 온보딩
    if not is_model_downloaded("small"):
        wizard = OnboardingWizard()
        if wizard.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)

    # 워크스페이스 초기화
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

    # -- Signal/Slot 연결 --

    # 트레이: 녹음 토글 -> MainWindow 녹음 제어
    tray.recording_toggled.connect(window.toggle_recording)

    # 트레이: 윈도우 표시
    tray.show_window_requested.connect(window.show)
    tray.show_window_requested.connect(window.raise_)

    # 트레이: 오버레이 토글
    tray.overlay_toggle_requested.connect(overlay.toggle_visibility)

    # 트레이: 종료
    tray.quit_requested.connect(app.quit)

    # MainWindow: 오버레이에 캡션 전달
    window.caption_updated.connect(overlay.append_caption)
    window.recording_started.connect(overlay.clear_caption)

    # 단축키 등록
    def _toggle_recording() -> None:
        tray.recording_toggled.emit(not tray.is_recording)

    def _open_settings() -> None:
        dialog = SettingsDialog(window)
        dialog.exec()

    shortcuts.register("Ctrl+Shift+R", _toggle_recording)
    shortcuts.register("Ctrl+Shift+C", overlay.toggle_visibility)
    shortcuts.register("Ctrl+,", _open_settings)

    # 윈도우 표시
    window.show()

    # 이벤트 루프 실행
    ret = app.exec()  # noqa: F841
    sys.exit(ret)


if __name__ == "__main__":
    main()
