"""시스템 오디오 토글 스위치 -- QPainter 커스텀 위젯."""

from __future__ import annotations

from PyQt6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    Qt,
    pyqtProperty,
    pyqtSignal,
)
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QWidget


class SystemAudioToggle(QWidget):
    """시스템 오디오 캡처 활성화 토글 스위치.

    44x24px QPainter 기반 커스텀 위젯. BlackHole 미설치 시 클릭하면
    setup_requested 시그널을 발생시켜 설치 위저드를 연다.
    """

    toggled = pyqtSignal(bool)
    setup_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(44, 24)

        self._checked = False
        self._enabled = True
        self._blackhole_available = False
        self._recording = False
        self._thumb_pos = 0.0

        # 색상 기본값 (다크 모드)
        self._track_off_color = QColor("#3A3A3C")
        self._track_on_color = QColor("#FF453A")
        self._thumb_color = QColor("#F5F5F7")
        self._disabled_track_color = QColor(58, 58, 60, 128)
        self._disabled_thumb_color = QColor("#48484A")

        # 애니메이션
        self._animation = QPropertyAnimation(self, b"thumb_position", self)
        self._animation.setDuration(150)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Capture system audio alongside microphone")

    # -- Q_PROPERTY for animation --

    def _get_thumb_position(self) -> float:
        """thumb_position 프로퍼티 getter."""
        return self._thumb_pos

    def _set_thumb_position(self, value: float) -> None:
        """thumb_position 프로퍼티 setter."""
        self._thumb_pos = value
        self.update()

    thumb_position = pyqtProperty(  # type: ignore[assignment]
        float, _get_thumb_position, _set_thumb_position
    )

    # -- 공개 API --

    def set_theme_colors(
        self,
        track_off: str,
        track_on: str,
        thumb: str,
        disabled_track_rgba: tuple[int, int, int, int],
        disabled_thumb: str,
    ) -> None:
        """테마 색상을 업데이트한다.

        Args:
            track_off: OFF 상태 트랙 색상 (hex)
            track_on: ON 상태 트랙 색상 (hex)
            thumb: 썸 색상 (hex)
            disabled_track_rgba: 비활성 트랙 RGBA 튜플
            disabled_thumb: 비활성 썸 색상 (hex)
        """
        self._track_off_color = QColor(track_off)
        self._track_on_color = QColor(track_on)
        self._thumb_color = QColor(thumb)
        self._disabled_track_color = QColor(*disabled_track_rgba)
        self._disabled_thumb_color = QColor(disabled_thumb)
        self.update()

    def set_blackhole_available(self, available: bool) -> None:
        """BlackHole 설치 여부를 설정한다.

        Args:
            available: BlackHole 설치 여부
        """
        self._blackhole_available = available
        self._update_cursor_and_tooltip()
        self.update()

    def set_recording(self, recording: bool) -> None:
        """녹음 상태를 설정한다. 녹음 중에는 토글 비활성화.

        Args:
            recording: 녹음 진행 중 여부
        """
        self._recording = recording
        self._update_cursor_and_tooltip()
        self.update()

    def setChecked(self, checked: bool) -> None:  # noqa: N802
        """프로그래밍 방식으로 토글 상태를 설정한다.

        Args:
            checked: 토글 ON/OFF 상태
        """
        if self._checked == checked:
            return
        self._checked = checked
        self._animate_thumb(1.0 if checked else 0.0)
        self.toggled.emit(self._checked)

    def isChecked(self) -> bool:  # noqa: N802
        """현재 토글 상태를 반환한다.

        Returns:
            토글 ON이면 True
        """
        return self._checked

    # -- 이벤트 핸들러 --

    def mousePressEvent(self, event: object) -> None:  # noqa: N802
        """마우스 클릭 이벤트를 처리한다.

        Args:
            event: 마우스 이벤트
        """
        if self._recording:
            return

        if not self._blackhole_available:
            self.setup_requested.emit()
            return

        self._checked = not self._checked
        self._animate_thumb(1.0 if self._checked else 0.0)
        self.toggled.emit(self._checked)

    def paintEvent(self, event: object) -> None:  # noqa: N802
        """QPainter로 토글 스위치를 그린다.

        Args:
            event: 페인트 이벤트
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # 상태에 따른 색상 결정
        is_disabled = not self._blackhole_available or self._recording
        if is_disabled:
            track_color = self._disabled_track_color
            thumb_color = self._disabled_thumb_color
        elif self._checked:
            track_color = self._track_on_color
            thumb_color = QColor("#FFFFFF")
        else:
            track_color = self._track_off_color
            thumb_color = self._thumb_color

        # 트랙 그리기 (rounded rect)
        track_rect = QRectF(0, 0, w, h)
        painter.setBrush(track_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(track_rect, 12, 12)

        # 썸 그리기 (20x20 circle)
        thumb_size = 20
        inset = 2
        thumb_x = inset + (self._thumb_pos * (w - thumb_size - 2 * inset))
        thumb_y = inset
        thumb_rect = QRectF(thumb_x, thumb_y, thumb_size, thumb_size)
        painter.setBrush(thumb_color)
        painter.drawEllipse(thumb_rect)

        painter.end()

    # -- 내부 헬퍼 --

    def _animate_thumb(self, target: float) -> None:
        """썸 위치 애니메이션을 실행한다.

        Args:
            target: 목표 위치 (0.0=OFF, 1.0=ON)
        """
        self._animation.stop()
        self._animation.setStartValue(self._thumb_pos)
        self._animation.setEndValue(target)
        self._animation.start()

    def _update_cursor_and_tooltip(self) -> None:
        """커서와 툴팁을 현재 상태에 맞게 업데이트한다."""
        if self._recording:
            self.setCursor(Qt.CursorShape.ForbiddenCursor)
            self.setToolTip("Cannot change audio source while recording")
        elif not self._blackhole_available:
            self.setCursor(Qt.CursorShape.ForbiddenCursor)
            self.setToolTip("BlackHole audio driver required -- click to set up")
        else:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setToolTip("Capture system audio alongside microphone")
