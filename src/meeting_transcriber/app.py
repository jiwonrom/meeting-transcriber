"""Scribe — 메인 엔트리포인트."""

from __future__ import annotations

import logging
import os
import pathlib
import sys
from logging.handlers import RotatingFileHandler

os.environ["QT_LOGGING_RULES"] = "qt.text.font.db=false"

from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QApplication, QDialog

from meeting_transcriber.core.model_manager import is_model_downloaded
from meeting_transcriber.core.system_audio import (
    create_aggregate_device,
    destroy_aggregate_device,
    is_blackhole_installed,
)
from meeting_transcriber.storage.workspace import WorkspaceManager
from meeting_transcriber.ui.main_window import MainWindow
from meeting_transcriber.ui.onboarding import OnboardingWizard
from meeting_transcriber.ui.overlay import OverlayWidget
from meeting_transcriber.ui.settings_dialog import SettingsDialog
from meeting_transcriber.ui.sidebar import SidebarWidget
from meeting_transcriber.ui.theme import ThemeEngine
from meeting_transcriber.ui.tray import TrayIcon
from meeting_transcriber.utils.config import load_settings, save_settings
from meeting_transcriber.utils.constants import LOGS_DIR
from meeting_transcriber.utils.shortcuts import ShortcutManager

logger = logging.getLogger(__name__)


def _setup_logging() -> None:
    """로깅을 설정한다. ~/.meeting_transcriber/logs/scribe.log에 기록."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / "scribe.log"

    handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)


def main() -> None:
    """앱을 시작한다."""
    _setup_logging()
    logger.info("Scribe starting")

    app = QApplication(sys.argv)
    app.setApplicationName("Meeting Transcriber")
    app.setApplicationDisplayName("Meeting Transcriber")
    app.setQuitOnLastWindowClosed(False)

    # 앱 아이콘
    icon_path = pathlib.Path(__file__).parent.parent.parent / "resources" / "AppIcon.icns"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

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

    # 사이드바 (교차 회의 분석 등)
    sidebar = SidebarWidget(workspace=workspace)
    sidebar.analysis_requested.connect(window._on_analysis_requested)
    sidebar.analysis_selected.connect(window._on_analysis_selected)
    sidebar.transcript_selected.connect(
        lambda path: (
            window._transcript_viewer.display_transcript(path),
            window._empty_state.hide(),
            window._transcript_viewer.show(),
        )
    )

    # Aggregate Device lifecycle management
    # Private Aggregate Devices (isPrivate=1) are process-scoped and destroyed on exit.
    # We recreate from saved UIDs on startup and destroy on quit.
    aggregate_device_id: int | None = None

    settings = load_settings()
    sys_audio = settings.get("audio", {}).get("system_audio", {})

    if is_blackhole_installed():
        logger.info("BlackHole audio driver detected")

        # Recreate Aggregate Device from saved UIDs if system audio was configured
        mic_uid = sys_audio.get("mic_device_uid")
        blackhole_uid = sys_audio.get("blackhole_uid")
        if mic_uid and blackhole_uid:
            try:
                aggregate_device_id = create_aggregate_device(mic_uid, blackhole_uid)
                logger.info("Aggregate Device recreated (id=%d)", aggregate_device_id)
            except Exception:
                logger.warning(
                    "Failed to recreate Aggregate Device -- system audio may not work",
                    exc_info=True,
                )
                aggregate_device_id = None
    else:
        logger.info("BlackHole audio driver not detected -- system audio disabled")
        # If BlackHole was uninstalled since last session, disable system audio
        if sys_audio.get("enabled"):
            sys_audio["enabled"] = False
            save_settings(settings)

    # Destroy Aggregate Device on quit to clean up CoreAudio resources
    def _cleanup_aggregate_device() -> None:
        """앱 종료 시 Aggregate Device 정리."""
        if aggregate_device_id is not None:
            destroy_aggregate_device(aggregate_device_id)
            logger.info("Aggregate Device destroyed on quit")

    app.aboutToQuit.connect(_cleanup_aggregate_device)

    # 오버레이
    overlay = OverlayWidget()
    overlay.apply_theme(theme)
    overlay.restore_position()
    overlay.show()

    # 트레이
    tray = TrayIcon()
    tray.show()

    # 회의 감지
    from meeting_transcriber.core.meeting_detector import MeetingDetectorWorker

    detector = MeetingDetectorWorker()

    # 감지 → 트레이 알림 (3-arg signal: app_name, template_key, bundle_id)
    detector.meeting_detected.connect(tray.show_meeting_notification)

    # 알림 클릭 → MainWindow 템플릿 제안 + 윈도우 표시
    tray.recording_from_detection.connect(window.suggest_template)
    tray.recording_from_detection.connect(lambda _: (window.show(), window.raise_()))

    # 스누즈 → 감지기
    tray.snooze_requested.connect(detector.snooze)

    # 감지 토글 → 감지기 시작/중지
    tray.detection_toggled.connect(
        lambda enabled: detector.start_detection() if enabled else detector.stop_detection()
    )

    # 녹음 상태 → 감지기 (녹음 중 감지 억제)
    window.recording_started.connect(lambda: detector.set_recording(True))
    window.recording_stopped.connect(lambda: detector.set_recording(False))

    # 설정에서 감지 활성화 확인 후 시작
    if settings.get("detection", {}).get("enabled", True):
        detector.start_detection()
        tray.set_detection_state(True)
    else:
        tray.set_detection_state(False)

    # 앱 종료 시 감지 중지
    app.aboutToQuit.connect(detector.stop_detection)

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

    settings_action = QAction("Preferences...", window)
    settings_action.setShortcut("Ctrl+,")

    def _open_settings() -> None:
        dlg = SettingsDialog(window)
        dlg.settings_changed.connect(overlay.apply_settings)
        dlg.exec()

    settings_action.triggered.connect(_open_settings)
    file_menu.addAction(settings_action)

    view_menu = menubar.addMenu("View")
    assert view_menu is not None

    toggle_overlay = QAction("Show/Hide Overlay", window)
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
    window.recording_started.connect(overlay.show)
    window.recording_started.connect(overlay.clear_caption)
    window.recording_started.connect(lambda: overlay.set_recording(True))
    window.recording_stopped.connect(lambda: overlay.set_recording(False))

    # 트레이 ↔ 윈도우 녹음 상태 동기화
    window.recording_started.connect(lambda: tray.set_recording(True))
    window.recording_stopped.connect(lambda: tray.set_recording(False))

    # 단축키
    def _toggle_recording() -> None:
        window.toggle_recording(not window.is_recording)

    shortcuts.register("Ctrl+Shift+R", _toggle_recording)

    window.show()

    ret = app.exec()  # noqa: F841
    sys.exit(ret)


if __name__ == "__main__":
    main()
