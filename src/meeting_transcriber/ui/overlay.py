"""Spotlight 스타일 플로팅 오버레이 — 화면 하단 중앙 캡션 바."""

from __future__ import annotations

from collections import deque
from typing import Any

from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QMouseEvent, QPainter, QPainterPath
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLabel, QWidget

from meeting_transcriber.ui.theme import ThemeEngine
from meeting_transcriber.utils.config import load_settings, save_settings
from meeting_transcriber.utils.constants import OVERLAY_DEFAULT_LINES, OVERLAY_MAX_LINES


class OverlayWidget(QWidget):
    """Spotlight 스타일 플로팅 캡션 오버레이.

    화면 하단 중앙에 떠있는 둥근 바로, 실시간 전사 텍스트를 표시한다.
    단축키(Cmd+Shift+C)로 나타남/사라짐. 드래그로 위치 이동 가능.
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
        self._border_radius = 20
        self._is_recording = False

        # 테마 기반 색상 (기본값, apply_theme에서 갱신)
        self._bg_base_color = QColor(28, 28, 30)
        self._bg_color = QColor(28, 28, 30, int(opacity * 255))
        self._recording_color = "#FF453A"
        self._text_color = "#F5F5F7"

        # 드래그 상태
        self._drag_pos: QPoint | None = None

        self._setup_window()
        self._setup_ui()
        self.setAccessibleName("Transcription Overlay")

    def _setup_window(self) -> None:
        """Spotlight 스타일 윈도우 속성."""
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedWidth(600)
        self.setMinimumHeight(48)
        self.setMaximumHeight(120)
        self._update_height()

    def _setup_ui(self) -> None:
        """내부 레이아웃."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(8)

        # 녹음 상태 점
        self._status_dot = QLabel()
        self._status_dot.setFixedSize(10, 10)
        self._status_dot.setStyleSheet(
            f"background-color: {self._recording_color}; border-radius: 5px;"
        )
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
        self._label.setStyleSheet(f"color: {self._text_color}; background: transparent;")
        layout.addWidget(self._label, 1)

    # -- 드래그 지원 --

    def mousePressEvent(self, event: QMouseEvent | None) -> None:  # noqa: N802
        """드래그 시작 — 마우스 위치를 기록한다."""
        if event and event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent | None) -> None:  # noqa: N802
        """드래그 중 — 오버레이를 마우스 위치로 이동한다."""
        if event and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent | None) -> None:  # noqa: N802
        """드래그 종료 — 위치를 저장한다."""
        if event and event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None
            self.save_position()
            self.position_changed.emit(self.pos().x(), self.pos().y())
            event.accept()

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
        """라벨 텍스트를 업데이트하고 높이를 조정한다."""
        self._label.setText("\n".join(self._lines))
        self._update_height()

    def _update_height(self) -> None:
        """현재 줄 수에 따라 높이를 조정한다."""
        line_count = max(len(self._lines), 1)
        new_h = max(48, 24 + line_count * (self._font_size + 6))
        new_h = min(new_h, 120)
        self.setFixedHeight(new_h)

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
        self._update_height()

    def set_opacity(self, opacity: float) -> None:
        """배경 투명도를 변경한다."""
        self._bg_opacity = min(max(opacity, 0.0), 1.0)
        self._bg_color = QColor(
            self._bg_base_color.red(),
            self._bg_base_color.green(),
            self._bg_base_color.blue(),
            int(self._bg_opacity * 255),
        )
        self.update()

    def apply_theme(self, theme: ThemeEngine) -> None:
        """테마를 적용한다."""
        t = theme.tokens
        colors = t.get("colors", {})

        # 배경색
        overlay_bg = colors.get("background", {}).get("overlay")
        if overlay_bg and isinstance(overlay_bg, str) and overlay_bg.startswith("rgba"):
            # rgba(r,g,b,a) 파싱은 복잡하므로 기본값 유지
            pass
        else:
            bg_primary = colors.get("background", {}).get("primary", "#1C1C1E")
            self._bg_base_color = QColor(bg_primary)

        # 텍스트 색상
        self._text_color = colors.get("text", {}).get("overlay", "#FFFFFF")
        self._label.setStyleSheet(f"color: {self._text_color}; background: transparent;")

        # 녹음 상태 색상
        self._recording_color = colors.get("status", {}).get("recording", "#FF453A")
        self._status_dot.setStyleSheet(
            f"background-color: {self._recording_color}; border-radius: 5px;"
        )

        # 배경 투명도 갱신
        self._bg_color = QColor(
            self._bg_base_color.red(),
            self._bg_base_color.green(),
            self._bg_base_color.blue(),
            int(self._bg_opacity * 255),
        )

        # 폰트 크기
        font_size = t.get("typography", {}).get("fontSize", {}).get("overlay", self._font_size)
        self.set_font_size(font_size)
        self.update()

    def apply_settings(self, settings: dict[str, Any]) -> None:
        """설정 다이얼로그에서 변경된 값을 런타임에 반영한다.

        Args:
            settings: 전체 설정 딕셔너리
        """
        overlay = settings.get("overlay", {})
        if "lines" in overlay:
            self.set_max_lines(overlay["lines"])
        if "font_size" in overlay:
            self.set_font_size(overlay["font_size"])
        if "opacity" in overlay:
            self.set_opacity(overlay["opacity"])

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
            0.0,
            0.0,
            float(self.width()),
            float(self.height()),
            self._border_radius,
            self._border_radius,
        )
        painter.fillPath(path, QBrush(self._bg_color))
        painter.end()
