"""플로팅 캡션 오버레이 — 화면 위 실시간 자막 윈도우."""
from __future__ import annotations

from collections import deque
from typing import Any

from PyQt6.QtCore import QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QMouseEvent, QPainter, QPainterPath
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from meeting_transcriber.ui.theme import ThemeEngine
from meeting_transcriber.utils.config import load_settings, save_settings
from meeting_transcriber.utils.constants import OVERLAY_DEFAULT_LINES, OVERLAY_MAX_LINES


class OverlayWidget(QWidget):
    """화면 위에 떠있는 캡션 오버레이 위젯.

    항상 최상위에 표시되며, 드래그로 이동 가능하고, 위치가 세션 간 저장된다.
    """

    visibility_changed = pyqtSignal(bool)
    position_changed = pyqtSignal(int, int)

    def __init__(
        self,
        max_lines: int = OVERLAY_DEFAULT_LINES,
        font_size: int = 18,
        opacity: float = 0.85,
        parent: Any = None,
    ) -> None:
        """OverlayWidget을 초기화한다.

        Args:
            max_lines: 표시할 최대 줄 수 (2~5)
            font_size: 캡션 폰트 크기 (px)
            opacity: 배경 투명도 (0.0~1.0)
            parent: Qt 부모 위젯
        """
        super().__init__(parent)

        self._max_lines = min(max(max_lines, 1), OVERLAY_MAX_LINES)
        self._lines: deque[str] = deque(maxlen=self._max_lines)
        self._font_size = font_size
        self._bg_opacity = opacity
        self._drag_pos: QPoint | None = None
        self._bg_color = QColor(0, 0, 0, int(opacity * 255))
        self._border_radius = 12

        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(1000)
        self._save_timer.timeout.connect(self._deferred_save_position)

        self._setup_window()
        self._setup_ui()
        self.setAccessibleName("Transcription Overlay")

    def _setup_window(self) -> None:
        """윈도우 속성을 설정한다."""
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumWidth(400)

    def _setup_ui(self) -> None:
        """내부 레이아웃과 라벨을 생성한다."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._label = QLabel("")
        self._label.setWordWrap(True)
        self._label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom
        )
        self._update_label_font()
        self._label.setStyleSheet(
            "color: #FFFFFF; padding: 12px; background: transparent;"
        )
        layout.addWidget(self._label)

    def _update_label_font(self) -> None:
        """라벨 폰트를 현재 설정값으로 업데이트한다."""
        font = QFont()
        font.setFamily("-apple-system")
        font.setPixelSize(self._font_size)
        font.setWeight(QFont.Weight.Medium)
        self._label.setFont(font)

    # -- 캡션 관리 --

    def update_caption(self, text: str) -> None:
        """캡션 텍스트를 설정한다. 여러 줄이면 줄 수 제한을 적용한다.

        Args:
            text: 표시할 텍스트 (줄바꿈으로 구분 가능)
        """
        self._lines.clear()
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped:
                self._lines.append(stripped)
        self._refresh_label()

    def append_caption(self, text: str) -> None:
        """기존 캡션에 새 텍스트를 추가한다.

        Args:
            text: 추가할 텍스트
        """
        stripped = text.strip()
        if stripped:
            self._lines.append(stripped)
            self._refresh_label()

    def clear_caption(self) -> None:
        """캡션을 초기화한다."""
        self._lines.clear()
        self._refresh_label()

    def get_caption_text(self) -> str:
        """현재 표시 중인 캡션 텍스트를 반환한다.

        Returns:
            줄바꿈으로 구분된 캡션 문자열
        """
        return "\n".join(self._lines)

    def _refresh_label(self) -> None:
        """라벨 텍스트를 _lines 내용으로 업데이트한다."""
        self._label.setText("\n".join(self._lines))
        self.adjustSize()

    # -- 외관 설정 --

    def set_max_lines(self, n: int) -> None:
        """최대 줄 수를 변경한다.

        Args:
            n: 새 최대 줄 수 (1~OVERLAY_MAX_LINES 범위로 클램핑)
        """
        n = min(max(n, 1), OVERLAY_MAX_LINES)
        self._max_lines = n
        old_lines = list(self._lines)
        self._lines = deque(old_lines[-n:], maxlen=n)
        self._refresh_label()

    def set_font_size(self, size: int) -> None:
        """폰트 크기를 변경한다.

        Args:
            size: 새 폰트 크기 (px)
        """
        self._font_size = size
        self._update_label_font()
        self.adjustSize()

    def set_opacity(self, opacity: float) -> None:
        """배경 투명도를 변경한다.

        Args:
            opacity: 0.0(완전 투명)~1.0(불투명)
        """
        self._bg_opacity = min(max(opacity, 0.0), 1.0)
        self._bg_color.setAlpha(int(self._bg_opacity * 255))
        self.update()

    def apply_theme(self, theme: ThemeEngine) -> None:
        """테마 엔진에서 오버레이 스타일을 적용한다.

        Args:
            theme: ThemeEngine 인스턴스
        """
        t = theme.tokens
        overlay_cfg = t.get("overlay", {})
        typography = t.get("typography", {})
        colors = t.get("colors", {})

        font_size = typography.get("fontSize", {}).get("overlay", self._font_size)
        self.set_font_size(font_size)

        padding = overlay_cfg.get("padding", 12)
        text_color = colors.get("text", {}).get("overlay", "#FFFFFF")
        self._label.setStyleSheet(
            f"color: {text_color}; padding: {padding}px; background: transparent;"
        )

        self._border_radius = t.get("borderRadius", {}).get("overlay", 12)
        self.update()

    # -- 위치 저장/복원 --

    def save_position(self) -> None:
        """현재 위치를 settings.json에 저장한다."""
        pos = self.pos()
        settings = load_settings()
        settings.setdefault("overlay", {})["position"] = [pos.x(), pos.y()]
        save_settings(settings)

    def restore_position(self) -> None:
        """settings.json에서 저장된 위치를 복원한다."""
        settings = load_settings()
        position = settings.get("overlay", {}).get("position")
        if position and len(position) == 2:
            self.move(int(position[0]), int(position[1]))

    # -- 표시/숨기기 --

    def toggle_visibility(self) -> None:
        """오버레이 표시/숨기기를 토글한다."""
        if self.isVisible():
            self.hide()
            self.visibility_changed.emit(False)
        else:
            self.show()
            self.visibility_changed.emit(True)

    # -- 드래그 이동 --

    def mousePressEvent(self, event: QMouseEvent | None) -> None:  # noqa: N802
        """마우스 버튼 누름 — 드래그 시작 위치를 기록한다."""
        if event and event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent | None) -> None:  # noqa: N802
        """마우스 이동 — 윈도우를 드래그한다."""
        if (
            event
            and self._drag_pos is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            self.move(new_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent | None) -> None:  # noqa: N802
        """마우스 버튼 뗌 — 드래그 종료, 위치 저장 (디바운스)."""
        if event and event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None
            pos = self.pos()
            self.position_changed.emit(pos.x(), pos.y())
            self._save_timer.start()  # 1초 디바운스
        super().mouseReleaseEvent(event)

    def _deferred_save_position(self) -> None:
        """디바운스 타이머 만료 후 위치를 저장한다."""
        self.save_position()

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
