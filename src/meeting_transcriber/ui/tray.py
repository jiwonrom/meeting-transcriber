"""macOS 메뉴바 트레이 아이콘 — 빠른 녹음 제어."""
from __future__ import annotations

from typing import Any

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

from meeting_transcriber.utils.constants import APP_NAME


def _create_tray_icon(recording: bool = False) -> QIcon:
    """트레이 아이콘을 동적으로 생성한다.

    Args:
        recording: 녹음 중이면 True (빨간색), 아니면 False (회색)

    Returns:
        16x16 원형 아이콘
    """
    size = 32
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    color = QColor("#FF453A") if recording else QColor("#98989D")
    painter.setBrush(color)
    painter.setPen(QColor(0, 0, 0, 0))
    painter.drawEllipse(4, 4, size - 8, size - 8)
    painter.end()

    return QIcon(pixmap)


class TrayIcon(QSystemTrayIcon):
    """macOS 메뉴바 트레이 아이콘.

    녹음 시작/정지, 윈도우/오버레이 표시, 앱 종료를 제공한다.
    """

    recording_toggled = pyqtSignal(bool)
    show_window_requested = pyqtSignal()
    overlay_toggle_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, parent: Any = None) -> None:
        """TrayIcon을 초기화한다.

        Args:
            parent: Qt 부모 객체
        """
        super().__init__(parent)
        self._recording = False

        self.setIcon(_create_tray_icon(recording=False))
        self.setToolTip(APP_NAME)

        self._setup_menu()

    def _setup_menu(self) -> None:
        """트레이 메뉴를 구성한다."""
        self._menu = QMenu()

        self._record_action = QAction("Start Recording", self)
        self._record_action.triggered.connect(self._toggle_recording)
        self._menu.addAction(self._record_action)

        self._menu.addSeparator()

        self._show_window_action = QAction("Show Window", self)
        self._show_window_action.triggered.connect(self.show_window_requested.emit)
        self._menu.addAction(self._show_window_action)

        self._overlay_action = QAction("Toggle Overlay", self)
        self._overlay_action.triggered.connect(self.overlay_toggle_requested.emit)
        self._menu.addAction(self._overlay_action)

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
        self.setIcon(_create_tray_icon(recording=self._recording))
        self._record_action.setText(
            "Stop Recording" if self._recording else "Start Recording"
        )
        self.setToolTip(
            f"{APP_NAME} — Recording..." if self._recording else APP_NAME
        )

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
