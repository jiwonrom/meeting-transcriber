"""macOS 메뉴바 트레이 아이콘 — 빠른 녹음 제어."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

from meeting_transcriber.utils.constants import APP_NAME

DEFAULT_RECORDING_COLOR = "#FF453A"
DEFAULT_IDLE_COLOR = "#98989D"


def _create_tray_icon(
    recording: bool = False,
    recording_color: str = DEFAULT_RECORDING_COLOR,
    idle_color: str = DEFAULT_IDLE_COLOR,
) -> QIcon:
    """트레이 아이콘을 동적으로 생성한다.

    Args:
        recording: 녹음 중이면 True (빨간색), 아니면 False (회색)
        recording_color: 녹음 상태 색상 (hex)
        idle_color: 대기 상태 색상 (hex)

    Returns:
        16x16 원형 아이콘
    """
    size = 32
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    color = QColor(recording_color) if recording else QColor(idle_color)
    painter.setBrush(color)
    painter.setPen(QColor(0, 0, 0, 0))
    painter.drawEllipse(4, 4, size - 8, size - 8)
    painter.end()

    return QIcon(pixmap)


class TrayIcon(QSystemTrayIcon):
    """macOS 메뉴바 트레이 아이콘.

    녹음 시작/정지, 윈도우/오버레이 표시, 회의 감지 알림, 앱 종료를 제공한다.
    """

    recording_toggled = pyqtSignal(bool)
    show_window_requested = pyqtSignal()
    overlay_toggle_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    recording_from_detection = pyqtSignal(str)  # suggested_template_key
    snooze_requested = pyqtSignal(str)  # bundle_id
    detection_toggled = pyqtSignal(bool)  # enabled

    def __init__(self, parent: Any = None) -> None:
        """TrayIcon을 초기화한다.

        Args:
            parent: Qt 부모 객체
        """
        super().__init__(parent)
        self._recording = False
        self._recording_color = DEFAULT_RECORDING_COLOR
        self._idle_color = DEFAULT_IDLE_COLOR
        self._pending_template = ""
        self._pending_bundle_id = ""

        self.setIcon(_create_tray_icon(recording=False))
        self.setToolTip(APP_NAME)

        self._setup_menu()

        # 알림 클릭 시 처리
        self.messageClicked.connect(self._on_notification_clicked)

    def _setup_menu(self) -> None:
        """트레이 메뉴를 구성한다."""
        self._menu = QMenu()

        self._record_action = QAction("Start Recording", self)
        self._record_action.triggered.connect(self._toggle_recording)
        self._menu.addAction(self._record_action)

        self._menu.addSeparator()

        self._show_window_action = QAction(f"Show {APP_NAME}", self)
        self._show_window_action.triggered.connect(self.show_window_requested.emit)
        self._menu.addAction(self._show_window_action)

        self._overlay_action = QAction("Show/Hide Overlay", self)
        self._overlay_action.triggered.connect(self.overlay_toggle_requested.emit)
        self._menu.addAction(self._overlay_action)

        self._menu.addSeparator()

        # 회의 감지 토글
        self._detection_action = QAction("Meeting Detection: On", self)
        self._detection_action.setCheckable(True)
        self._detection_action.setChecked(True)
        self._detection_action.toggled.connect(self._on_detection_action_toggled)
        self._menu.addAction(self._detection_action)

        # 스누즈 액션 (감지 알림 후에만 표시)
        self._snooze_action = QAction("Snooze", self)
        self._snooze_action.setVisible(False)
        self._snooze_action.triggered.connect(self._on_snooze_clicked)
        self._menu.addAction(self._snooze_action)

        self._menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_requested.emit)
        self._menu.addAction(quit_action)

        self.setContextMenu(self._menu)

    def _toggle_recording(self) -> None:
        """녹음 상태를 토글한다."""
        self._recording = not self._recording
        self._update_state()
        self.recording_toggled.emit(self._recording)

    def _update_state(self) -> None:
        """아이콘과 메뉴 텍스트를 현재 상태에 맞게 업데이트한다."""
        self.setIcon(
            _create_tray_icon(
                recording=self._recording,
                recording_color=self._recording_color,
                idle_color=self._idle_color,
            )
        )
        self._record_action.setText("Stop Recording" if self._recording else "Start Recording")
        self.setToolTip(f"{APP_NAME} — Recording..." if self._recording else APP_NAME)

    @property
    def is_recording(self) -> bool:
        """현재 녹음 중인지 반환한다."""
        return self._recording

    def set_recording(self, recording: bool) -> None:
        """녹음 상태를 외부에서 설정한다.

        Args:
            recording: 녹음 상태
        """
        self._recording = recording
        self._update_state()

    @property
    def menu(self) -> QMenu:
        """트레이 메뉴."""
        return self._menu

    # -- 회의 감지 알림 --

    def show_meeting_notification(
        self, app_name: str, suggested_template: str, bundle_id: str
    ) -> None:
        """회의 감지 알림을 표시한다.

        Args:
            app_name: 감지된 앱 이름
            suggested_template: 제안 템플릿 키
            bundle_id: 감지된 앱 번들 ID (스누즈용)
        """
        self._pending_template = suggested_template
        self._pending_bundle_id = bundle_id
        self.showMessage(
            "Meeting Detected",
            f"{app_name} is active. Click to start recording.",
            QSystemTrayIcon.MessageIcon.Information,
            10000,
        )
        self._snooze_action.setVisible(True)
        self._snooze_action.setText(f"Snooze {app_name}")

    def _on_notification_clicked(self) -> None:
        """알림 클릭 시 감지된 템플릿으로 녹음을 시작한다."""
        if self._pending_template:
            self.recording_from_detection.emit(self._pending_template)
            self._pending_template = ""
            self._snooze_action.setVisible(False)

    def _on_snooze_clicked(self) -> None:
        """스누즈 클릭 시 해당 앱 감지를 억제한다."""
        if self._pending_bundle_id:
            self.snooze_requested.emit(self._pending_bundle_id)
            self._snooze_action.setVisible(False)
            self._pending_bundle_id = ""
            self._pending_template = ""

    def _on_detection_action_toggled(self, checked: bool) -> None:
        """감지 메뉴 토글 처리.

        Args:
            checked: 감지 활성화 여부
        """
        self._detection_action.setText(
            "Meeting Detection: On" if checked else "Meeting Detection: Off"
        )
        self.detection_toggled.emit(checked)

    def set_detection_state(self, enabled: bool) -> None:
        """감지 상태를 외부에서 설정한다. Settings 동기화용.

        Args:
            enabled: 감지 활성화 여부
        """
        self._detection_action.setChecked(enabled)
        self._detection_action.setText(
            "Meeting Detection: On" if enabled else "Meeting Detection: Off"
        )
