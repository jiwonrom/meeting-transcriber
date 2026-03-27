"""BlackHole 설치 및 Aggregate Device 생성 위저드."""

from __future__ import annotations

import logging
from typing import Any

import sounddevice as sd
from PyQt6.QtCore import QRectF, Qt, QThread, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QDesktopServices, QPainter, QPen
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from meeting_transcriber.core.system_audio import (
    create_aggregate_device,
    detect_blackhole,
    get_device_uid,
)
from meeting_transcriber.utils.config import load_settings, save_settings
from meeting_transcriber.utils.constants import AGGREGATE_DEVICE_UID
from meeting_transcriber.utils.exceptions import SystemAudioError

logger = logging.getLogger(__name__)


# ============================================================
# Aggregate Device 생성 백그라운드 스레드
# ============================================================


class AggregateDeviceThread(QThread):
    """Aggregate Device 생성을 별도 스레드에서 실행한다."""

    creation_finished = pyqtSignal(bool, str, int)  # (success, message, device_id)

    def __init__(
        self, mic_uid: str, blackhole_uid: str, parent: Any = None
    ) -> None:
        super().__init__(parent)
        self._mic_uid = mic_uid
        self._blackhole_uid = blackhole_uid

    def run(self) -> None:
        """Aggregate Device를 생성한다."""
        try:
            device_id = create_aggregate_device(self._mic_uid, self._blackhole_uid)
            self.creation_finished.emit(True, "Aggregate Device created!", device_id)
        except SystemAudioError as e:
            self.creation_finished.emit(False, str(e), 0)
        except Exception as e:
            self.creation_finished.emit(False, str(e), 0)


# ============================================================
# BlackHole 설치 위저드 (5단계)
# ============================================================


class BlackHoleSetupWizard(QDialog):
    """BlackHole 설치 및 시스템 오디오 설정 5단계 위저드.

    Step 1: 소개
    Step 2: BlackHole 설치 안내
    Step 3: 시스템 오디오 출력 라우팅 안내
    Step 4: Aggregate Device 생성
    Step 5: 완료
    """

    setup_completed = pyqtSignal()

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Scribe \u2014 System Audio Setup")
        self.setFixedSize(500, 520)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )

        self._detection_timer: QTimer | None = None
        self._creation_thread: AggregateDeviceThread | None = None
        self._aggregate_device_id: int = 0
        self._blackhole_uid: str = ""
        self._mic_uid: str = ""

        self._setup_ui()

    def _setup_ui(self) -> None:
        """UI를 구성한다."""
        layout = QVBoxLayout(self)

        # 페이지 스택
        self._stack = QStackedWidget()
        self._stack.addWidget(self._create_intro_page())
        self._stack.addWidget(self._create_install_page())
        self._stack.addWidget(self._create_audio_output_page())
        self._stack.addWidget(self._create_aggregate_page())
        self._stack.addWidget(self._create_complete_page())
        layout.addWidget(self._stack)

        # 하단 네비게이션
        nav_layout = QHBoxLayout()

        self._back_btn = QPushButton("Back")
        self._back_btn.clicked.connect(self._go_back)
        self._back_btn.setVisible(False)
        nav_layout.addWidget(self._back_btn)

        nav_layout.addStretch()

        self._step_label = QLabel("Step 1 of 5")
        self._step_label.setStyleSheet("font-size: 11px; color: #98989D;")
        nav_layout.addWidget(self._step_label)

        nav_layout.addStretch()

        self._next_btn = QPushButton("Get Started")
        self._next_btn.clicked.connect(self._go_next)
        nav_layout.addWidget(self._next_btn)

        layout.addLayout(nav_layout)

    # -- 페이지 생성 --

    def _create_intro_page(self) -> QWidget:
        """Step 1: 소개 페이지."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        heading = QLabel("Capture System Audio")
        heading.setStyleSheet("font-size: 17px; font-weight: 600;")
        layout.addWidget(heading)

        body = QLabel(
            "To transcribe the other side of calls, Scribe needs "
            "BlackHole \u2014 a free virtual audio driver."
        )
        body.setStyleSheet("font-size: 14px;")
        body.setWordWrap(True)
        layout.addWidget(body)

        # 일러스트레이션 영역
        illustration = _WaveIllustration()
        illustration.setFixedSize(200, 120)
        layout.addWidget(illustration, alignment=Qt.AlignmentFlag.AlignHCenter)

        layout.addStretch()
        return page

    def _create_install_page(self) -> QWidget:
        """Step 2: BlackHole 설치 페이지."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        heading = QLabel("Install BlackHole")
        heading.setStyleSheet("font-size: 17px; font-weight: 600;")
        layout.addWidget(heading)

        # Option A: Homebrew
        card_a = QFrame()
        card_a.setObjectName("install_card")
        card_a.setStyleSheet(
            "QFrame#install_card { border: 1px solid rgba(255,255,255,0.08); "
            "border-radius: 6px; padding: 16px; }"
        )
        card_a_layout = QVBoxLayout(card_a)
        card_a_layout.addWidget(QLabel("Install via Homebrew"))
        cmd_label = QLabel("brew install blackhole-2ch")
        cmd_label.setStyleSheet("font-family: 'SF Mono', 'Menlo', monospace; font-size: 13px;")
        card_a_layout.addWidget(cmd_label)
        self._copy_btn = QPushButton("Copy Command")
        self._copy_btn.clicked.connect(self._copy_brew_command)
        card_a_layout.addWidget(self._copy_btn)
        layout.addWidget(card_a)

        # Option B: GitHub
        card_b = QFrame()
        card_b.setObjectName("install_card")
        card_b.setStyleSheet(
            "QFrame#install_card { border: 1px solid rgba(255,255,255,0.08); "
            "border-radius: 6px; padding: 16px; }"
        )
        card_b_layout = QVBoxLayout(card_b)
        card_b_layout.addWidget(QLabel("Download from GitHub"))
        open_btn = QPushButton("Open Download Page")
        open_btn.clicked.connect(self._open_github_releases)
        card_b_layout.addWidget(open_btn)
        layout.addWidget(card_b)

        # 상태 표시
        self._detection_status = QLabel("Waiting for BlackHole installation...")
        self._detection_status.setStyleSheet("font-size: 11px; color: #6E6E73;")
        layout.addWidget(self._detection_status)

        layout.addStretch()
        return page

    def _create_audio_output_page(self) -> QWidget:
        """Step 3: 시스템 오디오 출력 라우팅 안내 페이지."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        heading = QLabel("Route System Audio")
        heading.setStyleSheet("font-size: 17px; font-weight: 600;")
        layout.addWidget(heading)

        body = QLabel(
            "For Scribe to hear system audio, your Mac's sound output must include "
            "BlackHole. Open Sound Settings and create a Multi-Output Device that "
            "sends audio to both your speakers and BlackHole."
        )
        body.setStyleSheet("font-size: 14px;")
        body.setWordWrap(True)
        layout.addWidget(body)

        # 단계별 안내
        instructions = QLabel(
            "1. Open Sound Settings below\n"
            "2. Go to Output and select 'Multi-Output Device' "
            "(or create one in Audio MIDI Setup)\n"
            "3. Ensure both your speakers/headphones AND BlackHole 2ch are checked"
        )
        instructions.setStyleSheet("font-size: 13px;")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # 버튼
        sound_settings_btn = QPushButton("Open Sound Settings")
        sound_settings_btn.clicked.connect(self._open_sound_settings)
        layout.addWidget(sound_settings_btn)

        midi_setup_btn = QPushButton("Open Audio MIDI Setup")
        midi_setup_btn.clicked.connect(self._open_audio_midi_setup)
        layout.addWidget(midi_setup_btn)

        hint = QLabel(
            "Tip: In Audio MIDI Setup, click '+' at the bottom left, "
            "select 'Create Multi-Output Device', then check your speakers "
            "and BlackHole 2ch."
        )
        hint.setStyleSheet("font-size: 11px; color: #6E6E73;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addStretch()
        return page

    def _create_aggregate_page(self) -> QWidget:
        """Step 4: Aggregate Device 생성 페이지."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        heading = QLabel("Set Up Audio Mixing")
        heading.setStyleSheet("font-size: 17px; font-weight: 600;")
        layout.addWidget(heading)

        body = QLabel(
            "Scribe will create an Aggregate Device that combines your "
            "microphone and BlackHole into a single input."
        )
        body.setStyleSheet("font-size: 14px;")
        body.setWordWrap(True)
        layout.addWidget(body)

        # 장치 이름 미리보기
        device_preview = QFrame()
        device_preview.setStyleSheet(
            "border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 12px;"
        )
        preview_layout = QVBoxLayout(device_preview)
        device_name_label = QLabel("Scribe Audio (Mic + System)")
        device_name_label.setStyleSheet(
            "font-family: 'SF Mono', 'Menlo', monospace; font-size: 14px;"
        )
        preview_layout.addWidget(device_name_label)
        layout.addWidget(device_preview)

        # 생성 버튼
        self._create_device_btn = QPushButton("Create Aggregate Device")
        self._create_device_btn.clicked.connect(self._start_aggregate_creation)
        layout.addWidget(self._create_device_btn, alignment=Qt.AlignmentFlag.AlignHCenter)

        # 프로그레스 바
        self._aggregate_progress = QProgressBar()
        self._aggregate_progress.setRange(0, 0)  # indeterminate
        self._aggregate_progress.setVisible(False)
        layout.addWidget(self._aggregate_progress)

        # 상태 라벨
        self._aggregate_status = QLabel("")
        self._aggregate_status.setStyleSheet("font-size: 13px;")
        self._aggregate_status.setWordWrap(True)
        layout.addWidget(self._aggregate_status)

        layout.addStretch()
        return page

    def _create_complete_page(self) -> QWidget:
        """Step 5: 완료 페이지."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        # 성공 아이콘
        success_icon = _SuccessIcon()
        success_icon.setFixedSize(48, 48)
        layout.addWidget(success_icon, alignment=Qt.AlignmentFlag.AlignHCenter)

        heading = QLabel("All Set!")
        heading.setStyleSheet("font-size: 17px; font-weight: 600;")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(heading)

        body = QLabel(
            "System audio capture is ready. Toggle 'System Audio' next to "
            "the record button to capture both sides of your calls."
        )
        body.setStyleSheet("font-size: 14px;")
        body.setWordWrap(True)
        body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(body)

        layout.addStretch()
        return page

    # -- 네비게이션 --

    def _go_next(self) -> None:
        """다음 페이지로 이동한다."""
        current = self._stack.currentIndex()

        if current == 0:
            # Step 1 -> Step 2: 설치 페이지로, 타이머 시작
            self._stack.setCurrentIndex(1)
            self._back_btn.setVisible(True)
            self._next_btn.setText("Continue")
            self._next_btn.setEnabled(False)
            self._start_detection_timer()

        elif current == 1:
            # Step 2 -> Step 3: 오디오 출력 라우팅
            self._stop_detection_timer()
            self._stack.setCurrentIndex(2)
            self._next_btn.setText("I've set it up")
            self._next_btn.setEnabled(True)

        elif current == 2:
            # Step 3 -> Step 4: Aggregate Device 생성
            self._stack.setCurrentIndex(3)
            self._next_btn.setText("Continue")
            self._next_btn.setEnabled(False)

        elif current == 3:
            # Step 4 -> Step 5: 완료
            self._stack.setCurrentIndex(4)
            self._next_btn.setText("Done")
            self._next_btn.setEnabled(True)

        elif current == 4:
            # 완료
            self._finish()

        self._step_label.setText(f"Step {self._stack.currentIndex() + 1} of 5")

    def _go_back(self) -> None:
        """이전 페이지로 이동한다."""
        current = self._stack.currentIndex()
        if current > 0:
            if current == 1:
                self._stop_detection_timer()

            self._stack.setCurrentIndex(current - 1)

            if current - 1 == 0:
                self._back_btn.setVisible(False)
                self._next_btn.setText("Get Started")
            else:
                self._next_btn.setText("Continue")

            self._next_btn.setEnabled(True)
            self._step_label.setText(f"Step {self._stack.currentIndex() + 1} of 5")

    def _finish(self) -> None:
        """위저드를 완료하고 설정을 저장한다."""
        settings = load_settings()
        settings["audio"]["system_audio"]["enabled"] = True
        settings["audio"]["system_audio"]["blackhole_uid"] = self._blackhole_uid
        settings["audio"]["system_audio"]["aggregate_device_uid"] = AGGREGATE_DEVICE_UID
        settings["audio"]["system_audio"]["mic_device_uid"] = self._mic_uid
        save_settings(settings)

        self.setup_completed.emit()
        self.accept()

    # -- BlackHole 감지 --

    def _start_detection_timer(self) -> None:
        """BlackHole 감지 타이머를 시작한다."""
        if self._detection_timer is not None:
            return
        self._detection_timer = QTimer(self)
        self._detection_timer.setInterval(2000)
        self._detection_timer.timeout.connect(self._poll_blackhole_detection)
        self._detection_timer.start()
        # 즉시 한 번 실행
        self._poll_blackhole_detection()

    def _stop_detection_timer(self) -> None:
        """BlackHole 감지 타이머를 중지한다."""
        if self._detection_timer is not None:
            self._detection_timer.stop()
            self._detection_timer = None

    def _poll_blackhole_detection(self) -> None:
        """BlackHole 설치 여부를 확인한다."""
        bh_index = detect_blackhole()
        if bh_index is not None:
            self._stop_detection_timer()
            self._detection_status.setText("\u2713 BlackHole detected!")
            self._detection_status.setStyleSheet(
                "font-size: 11px; color: #30D158; font-weight: 600;"
            )
            self._next_btn.setEnabled(True)

    # -- 클립보드/링크 --

    @staticmethod
    def _copy_brew_command() -> None:
        """Homebrew 설치 명령어를 클립보드에 복사한다."""
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText("brew install blackhole-2ch")

    @staticmethod
    def _open_github_releases() -> None:
        """BlackHole GitHub 릴리스 페이지를 연다."""
        QDesktopServices.openUrl(
            QUrl("https://github.com/ExistentialAudio/BlackHole/releases")
        )

    @staticmethod
    def _open_sound_settings() -> None:
        """macOS 사운드 설정을 연다."""
        QDesktopServices.openUrl(
            QUrl("x-apple.systempreferences:com.apple.preference.sound")
        )

    @staticmethod
    def _open_audio_midi_setup() -> None:
        """Audio MIDI Setup 앱을 연다."""
        QDesktopServices.openUrl(
            QUrl(
                "file:///System/Applications/Utilities/Audio%20MIDI%20Setup.app"
            )
        )

    # -- Aggregate Device 생성 --

    def _start_aggregate_creation(self) -> None:
        """Aggregate Device 생성을 시작한다."""
        self._create_device_btn.setEnabled(False)
        self._create_device_btn.setText("Creating...")
        self._aggregate_progress.setVisible(True)
        self._aggregate_status.setText("")

        try:
            # 기본 마이크 장치 인덱스
            default_device = sd.default.device
            mic_index = default_device[0] if isinstance(default_device, tuple) else default_device
            bh_index = detect_blackhole()
            if bh_index is None:
                raise SystemAudioError("BlackHole not found")

            mic_uid = get_device_uid(int(mic_index))
            blackhole_uid = get_device_uid(bh_index)

            self._mic_uid = mic_uid
            self._blackhole_uid = blackhole_uid

            self._creation_thread = AggregateDeviceThread(mic_uid, blackhole_uid, self)
            self._creation_thread.creation_finished.connect(
                self._on_aggregate_creation_finished
            )
            self._creation_thread.start()
        except Exception as e:
            self._on_aggregate_creation_finished(False, str(e), 0)

    def _on_aggregate_creation_finished(
        self, success: bool, message: str, device_id: int
    ) -> None:
        """Aggregate Device 생성 결과를 처리한다.

        Args:
            success: 생성 성공 여부
            message: 결과 메시지
            device_id: 생성된 장치 ID
        """
        self._creation_thread = None
        self._aggregate_progress.setVisible(False)

        if success:
            self._aggregate_device_id = device_id
            self._aggregate_status.setText(f"\u2713 {message}")
            self._aggregate_status.setStyleSheet("font-size: 13px; color: #30D158;")
            self._create_device_btn.setText("Create Aggregate Device")
            self._create_device_btn.setEnabled(False)
            self._next_btn.setEnabled(True)
        else:
            self._aggregate_status.setText(
                f"Failed to create device: {message}. Please try again."
            )
            self._aggregate_status.setStyleSheet("font-size: 13px; color: #FF453A;")
            self._create_device_btn.setText("Retry")
            self._create_device_btn.setEnabled(True)
            logger.error("Aggregate Device creation failed: %s", message)


# ============================================================
# QPainter 헬퍼 위젯
# ============================================================


class _WaveIllustration(QWidget):
    """두 사인파가 합쳐지는 간단한 일러스트레이션."""

    def paintEvent(self, event: object) -> None:  # noqa: N802
        """일러스트레이션을 그린다.

        Args:
            event: 페인트 이벤트
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # 배경
        painter.setBrush(QColor("#2C2C2E"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(0, 0, w, h), 8, 8)

        # 파형 1 (마이크 - 빨강)
        pen1 = QPen(QColor("#FF453A"))
        pen1.setWidth(2)
        painter.setPen(pen1)
        import math

        mid_y = h // 3
        for x in range(0, w - 1):
            y1 = mid_y + int(15 * math.sin(x * 0.08))
            y2 = mid_y + int(15 * math.sin((x + 1) * 0.08))
            painter.drawLine(x, y1, x + 1, y2)

        # 파형 2 (시스템 - 주황)
        pen2 = QPen(QColor("#FF9F0A"))
        pen2.setWidth(2)
        painter.setPen(pen2)
        mid_y2 = 2 * h // 3
        for x in range(0, w - 1):
            y1 = mid_y2 + int(10 * math.sin(x * 0.12 + 1.5))
            y2 = mid_y2 + int(10 * math.sin((x + 1) * 0.12 + 1.5))
            painter.drawLine(x, y1, x + 1, y2)

        painter.end()


class _SuccessIcon(QWidget):
    """48x48 초록색 원 안에 흰색 체크마크."""

    def paintEvent(self, event: object) -> None:  # noqa: N802
        """성공 아이콘을 그린다.

        Args:
            event: 페인트 이벤트
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 초록 원
        painter.setBrush(QColor("#30D158"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(0, 0, 48, 48))

        # 흰색 체크마크
        pen = QPen(QColor("#FFFFFF"))
        pen.setWidth(3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(14, 24, 21, 32)
        painter.drawLine(21, 32, 34, 18)

        painter.end()
