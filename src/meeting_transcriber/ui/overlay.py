"""Spotlight 스타일 플로팅 오버레이 — 화면 하단 중앙 캡션 바."""
from __future__ import annotations

from collections import deque
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLabel, QWidget

from meeting_transcriber.ui.theme import ThemeEngine
from meeting_transcriber.utils.config import load_settings, save_settings
from meeting_transcriber.utils.constants import OVERLAY_DEFAULT_LINES, OVERLAY_MAX_LINES


class OverlayWidget(QWidget):
    """Spotlight 스타일 플로팅 캡션 오버레이.

    화면 하단 중앙에 떠있는 둥근 바로, 실시간 전사 텍스트를 표시한다.
    단축키(Cmd+Shift+C)로 나타남/사라짐.
    """

    visibility_changed = pyqtSignal(bool)
    position_changed = pyqtSignal(int, int)

    def __init__(
        self,
        max_lines: int = OVERLAY_DEFAULT_LINES,
        font_size: int = 15,
        opacity: float = 0.92,
        parent: Any = None,
    ) -> None:
        """OverlayWidget을 초기화한다.

        Args:
            max_lines: 표시할 최대 줄 수 (1~5)
            font_size: 캡션 폰트 크기 (px)
            opacity: 배경 투명도 (0.0~1.0)
            parent: Qt 부모 위젯
        """
        super().__init__(parent)

        self._max_lines = min(max(max_lines, 1), OVERLAY_MAX_LINES)
        self._lines: deque[str] = deque(maxlen=self._max_lines)
        self._font_size = font_size
        self._bg_opacity = opacity
        self._bg_color = QColor(28, 28, 30, int(opacity * 255))  # bg.primary
        self._border_radius = 20
        self._is_recording = False

        self._setup_window()
        self._setup_ui()
        self.setAccessibleName("Transcription Overlay")

    def _setup_window(self) -> None:
        """Spotlight 스타일 윈도우 속성."""
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(600)
        self.setFixedHeight(80)

    def _setup_ui(self) -> None:
        """내부 레이아웃."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(8)

        # 녹음 상태 점
        self._status_dot = QLabel()
        self._status_dot.setFixedSize(10, 10)
        self._status_dot.setStyleSheet(
            "background-color: #FF453A; border-radius: 5px;"
        )  # status.recording token
        self._status_dot.hide()
        layout.addWidget(self._status_dot)

        # 캡션 텍스트
        self._label = QLabel("")
        self._label.setWordWrap(True)
        self._label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        font = QFont()
        font.setPixelSize(self._font_size)
        font.setWeight(QFont.Weight.Medium)
        self._label.setFont(font)
        self._label.setStyleSheet("color: #F5F5F7; background: transparent;")  # text.primary
        layout.addWidget(self._label, 1)

    # -- 캡션 관리 --

    def update_caption(self, text: str) -> None:
        """캡션 텍스트를 설정한다."""
        self._lines.clear()
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped:
                self._lines.append(stripped)
        self._refresh_label()

    def append_caption(self, text: str) -> None:
        """기존 캡션에 새 텍스트를 추가한다."""
        stripped = text.strip()
        if stripped:
            self._lines.append(stripped)
            self._refresh_label()

    def clear_caption(self) -> None:
        """캡션을 초기화한다."""
        self._lines.clear()
        self._refresh_label()

    def get_caption_text(self) -> str:
        """현재 캡션 텍스트를 반환한다."""
        return "\n".join(self._lines)

    def _refresh_label(self) -> None:
        """라벨 텍스트를 업데이트한다."""
        self._label.setText("\n".join(self._lines))

    # -- 녹음 상태 표시 --

    def set_recording(self, recording: bool) -> None:
        """녹음 상태를 표시한다.

        Args:
            recording: True이면 빨간 점 표시
        """
        self._is_recording = recording
        if recording:
            self._status_dot.show()
            if not self._lines:
                self._label.setText("Recording...")
        else:
            self._status_dot.hide()

    # -- 외관 설정 --

    def set_max_lines(self, n: int) -> None:
        """최대 줄 수를 변경한다."""
        n = min(max(n, 1), OVERLAY_MAX_LINES)
        self._max_lines = n
        old_lines = list(self._lines)
        self._lines = deque(old_lines[-n:], maxlen=n)
        self._refresh_label()

    def set_font_size(self, size: int) -> None:
        """폰트 크기를 변경한다."""
        self._font_size = size
        font = self._label.font()
        font.setPixelSize(size)
        self._label.setFont(font)

    def set_opacity(self, opacity: float) -> None:
        """배경 투명도를 변경한다."""
        self._bg_opacity = min(max(opacity, 0.0), 1.0)
        self._bg_color.setAlpha(int(self._bg_opacity * 255))
        self.update()

    def apply_theme(self, theme: ThemeEngine) -> None:
        """테마를 적용한다."""
        t = theme.tokens
        font_size = t.get("typography", {}).get("fontSize", {}).get("overlay", self._font_size)
        self.set_font_size(font_size)
        text_color = t.get("colors", {}).get("text", {}).get("overlay", "#FFFFFF")
        self._label.setStyleSheet(f"color: {text_color}; background: transparent;")
        self.update()

    # -- 위치 관리 (화면 하단 중앙) --

    def center_on_screen(self) -> None:
        """화면 하단 중앙에 위치시킨다."""
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        x = geo.x() + (geo.width() - self.width()) // 2
        y = geo.y() + geo.height() - self.height() - 40  # 하단에서 40px 위
        self.move(x, y)

    def save_position(self) -> None:
        """현재 위치를 settings.json에 저장한다."""
        pos = self.pos()
        settings = load_settings()
        settings.setdefault("overlay", {})["position"] = [pos.x(), pos.y()]
        save_settings(settings)

    def restore_position(self) -> None:
        """저장된 위치를 복원하거나, 없으면 화면 하단 중앙에 배치한다."""
        settings = load_settings()
        position = settings.get("overlay", {}).get("position")
        if position and len(position) == 2:
            self.move(int(position[0]), int(position[1]))
        else:
            self.center_on_screen()

    # -- 표시/숨기기 --

    def toggle_visibility(self) -> None:
        """오버레이 표시/숨기기를 토글한다."""
        if self.isVisible():
            self.hide()
            self.visibility_changed.emit(False)
        else:
            self.center_on_screen()
            self.show()
            self.visibility_changed.emit(True)

    # -- 배경 렌더링 --

    def paintEvent(self, event: Any) -> None:  # noqa: N802
        """둥근 직사각형 배경을 그린다."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(
            0.0, 0.0,
            float(self.width()), float(self.height()),
            self._border_radius, self._border_radius,
        )
        painter.fillPath(path, QBrush(self._bg_color))
        painter.end()
