"""듀얼 레벨 미터 -- 마이크 + 시스템 오디오."""

from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget


class DualLevelMeter(QWidget):
    """마이크와 시스템 오디오의 입력 레벨을 표시하는 듀얼 미터.

    기본 상태에서는 마이크 바만 표시하며 (4px 높이),
    듀얼 모드에서는 마이크 + 시스템 바를 모두 표시한다 (12px 높이).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)

        # 마이크 레벨 바
        self._mic_label = QLabel("MIC")
        self._mic_label.setObjectName("caption")
        self._mic_label.setStyleSheet("font-size: 11px;")
        self._mic_label.setVisible(False)
        layout.addWidget(self._mic_label)

        self._mic_bar = QProgressBar()
        self._mic_bar.setObjectName("mic_level_bar")
        self._mic_bar.setRange(0, 100)
        self._mic_bar.setValue(0)
        self._mic_bar.setFixedHeight(4)
        self._mic_bar.setTextVisible(False)
        layout.addWidget(self._mic_bar)

        # 시스템 레벨 바
        self._system_label = QLabel("SYS")
        self._system_label.setObjectName("caption")
        self._system_label.setStyleSheet("font-size: 11px;")
        self._system_label.setVisible(False)
        layout.addWidget(self._system_label)

        self._system_bar = QProgressBar()
        self._system_bar.setObjectName("system_level_bar")
        self._system_bar.setRange(0, 100)
        self._system_bar.setValue(0)
        self._system_bar.setFixedHeight(4)
        self._system_bar.setTextVisible(False)
        self._system_bar.setVisible(False)
        layout.addWidget(self._system_bar)

    def set_dual_mode(self, dual: bool) -> None:
        """듀얼 모드를 설정한다.

        Args:
            dual: True이면 마이크 + 시스템 바 모두 표시
        """
        self._system_bar.setVisible(dual)
        self._system_label.setVisible(dual)
        self._mic_label.setVisible(dual)

    def set_mic_level(self, level: float) -> None:
        """마이크 레벨을 업데이트한다.

        Args:
            level: 0.0 ~ 1.0 사이의 레벨 값
        """
        self._mic_bar.setValue(int(level * 100))

    def set_system_level(self, level: float) -> None:
        """시스템 오디오 레벨을 업데이트한다.

        Args:
            level: 0.0 ~ 1.0 사이의 레벨 값
        """
        self._system_bar.setValue(int(level * 100))

    def reset(self) -> None:
        """양쪽 바를 모두 0으로 초기화한다."""
        self._mic_bar.setValue(0)
        self._system_bar.setValue(0)
