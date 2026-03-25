"""첫 실행 온보딩 위저드 — 언어 선택, 모델 다운로드, 마이크 권한."""
from __future__ import annotations

import subprocess
from typing import Any

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from meeting_transcriber.core.model_manager import download_model, is_model_downloaded
from meeting_transcriber.utils.config import load_settings, save_settings
from meeting_transcriber.utils.constants import APP_NAME, SUPPORTED_LANGUAGES


class ModelDownloadThread(QThread):
    """모델 다운로드를 별도 스레드에서 실행한다."""

    progress_updated = pyqtSignal(int, int)
    download_finished = pyqtSignal(bool, str)  # (success, message)

    def __init__(self, model_name: str = "small", parent: Any = None) -> None:
        super().__init__(parent)
        self._model_name = model_name

    def run(self) -> None:
        """다운로드를 실행한다."""
        try:
            download_model(
                self._model_name,
                progress_callback=self._on_progress,
            )
            self.download_finished.emit(True, "Download complete!")
        except Exception as e:
            self.download_finished.emit(False, str(e))

    def _on_progress(self, downloaded: int, total: int) -> None:
        """진행률 콜백."""
        self.progress_updated.emit(downloaded, total)


class OnboardingWizard(QDialog):
    """첫 실행 온보딩 3단계 위저드.

    1. 언어 선택
    2. 모델 다운로드
    3. 마이크 권한 안내
    """

    onboarding_completed = pyqtSignal()

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} — Setup")
        self.setFixedSize(500, 400)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )

        self._selected_language = "auto"
        self._download_thread: ModelDownloadThread | None = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """UI를 구성한다."""
        layout = QVBoxLayout(self)

        # 페이지 스택
        self._stack = QStackedWidget()
        self._stack.addWidget(self._create_language_page())
        self._stack.addWidget(self._create_download_page())
        self._stack.addWidget(self._create_permission_page())
        layout.addWidget(self._stack)

        # 하단 버튼
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._back_btn = QPushButton("Back")
        self._back_btn.clicked.connect(self._go_back)
        self._back_btn.setVisible(False)
        btn_layout.addWidget(self._back_btn)

        self._next_btn = QPushButton("Next")
        self._next_btn.clicked.connect(self._go_next)
        btn_layout.addWidget(self._next_btn)

        layout.addLayout(btn_layout)

    # -- 페이지 생성 --

    def _create_language_page(self) -> QWidget:
        """언어 선택 페이지."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        title = QLabel("Welcome to Meeting Transcriber")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        subtitle = QLabel("Select your primary language:")
        subtitle.setStyleSheet("font-size: 14px; color: #6E6E73;")
        layout.addWidget(subtitle)

        self._lang_group = QButtonGroup(page)
        lang_labels = {"en": "English", "ko": "한국어", "zh": "中文", "ja": "日本語"}

        for lang in SUPPORTED_LANGUAGES:
            radio = QRadioButton(lang_labels.get(lang, lang))
            radio.setProperty("lang_code", lang)
            self._lang_group.addButton(radio)
            layout.addWidget(radio)

        # auto 옵션
        auto_radio = QRadioButton("Auto-detect")
        auto_radio.setProperty("lang_code", "auto")
        auto_radio.setChecked(True)
        self._lang_group.addButton(auto_radio)
        layout.addWidget(auto_radio)

        layout.addStretch()
        return page

    def _create_download_page(self) -> QWidget:
        """모델 다운로드 페이지."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        title = QLabel("Download Whisper Model")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        self._download_label = QLabel(
            "The 'small' model (~466MB) is required for transcription.\n"
            "Download will start automatically."
        )
        self._download_label.setWordWrap(True)
        layout.addWidget(self._download_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        layout.addWidget(self._progress_bar)

        self._progress_label = QLabel("")
        self._progress_label.setStyleSheet("color: #6E6E73;")
        layout.addWidget(self._progress_label)

        layout.addStretch()
        return page

    def _create_permission_page(self) -> QWidget:
        """마이크 권한 안내 페이지."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        title = QLabel("Microphone Access")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        info = QLabel(
            "Meeting Transcriber needs microphone access to capture audio.\n\n"
            "When prompted, please allow microphone access.\n"
            "You can change this later in System Settings."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        open_settings_btn = QPushButton("Open System Settings")
        open_settings_btn.clicked.connect(self._open_mic_settings)
        layout.addWidget(open_settings_btn)

        layout.addStretch()
        return page

    # -- 네비게이션 --

    def _go_next(self) -> None:
        """다음 페이지로 이동한다."""
        current = self._stack.currentIndex()

        if current == 0:
            # 언어 저장
            selected = self._lang_group.checkedButton()
            if selected:
                self._selected_language = selected.property("lang_code")
            self._stack.setCurrentIndex(1)
            self._back_btn.setVisible(True)
            self._start_download()

        elif current == 1:
            self._stack.setCurrentIndex(2)
            self._next_btn.setText("Finish")

        elif current == 2:
            self._finish()

    def _go_back(self) -> None:
        """이전 페이지로 이동한다."""
        current = self._stack.currentIndex()
        if current > 0:
            self._stack.setCurrentIndex(current - 1)
            self._next_btn.setText("Next")
            if current - 1 == 0:
                self._back_btn.setVisible(False)

    def _finish(self) -> None:
        """온보딩을 완료한다."""
        settings = load_settings()
        settings["language"] = self._selected_language
        save_settings(settings)
        self.onboarding_completed.emit()
        self.accept()

    # -- 모델 다운로드 --

    def _start_download(self) -> None:
        """모델 다운로드를 시작한다."""
        if is_model_downloaded("small"):
            self._progress_bar.setValue(100)
            self._progress_label.setText("Model already downloaded.")
            self._next_btn.setEnabled(True)
            return

        self._next_btn.setEnabled(False)
        self._download_thread = ModelDownloadThread("small")
        self._download_thread.progress_updated.connect(self._on_download_progress)
        self._download_thread.download_finished.connect(self._on_download_finished)
        self._download_thread.start()

    def _on_download_progress(self, downloaded: int, total: int) -> None:
        """다운로드 진행률을 업데이트한다."""
        if total > 0:
            percent = int(downloaded / total * 100)
            self._progress_bar.setValue(percent)
            mb_down = downloaded / (1024 * 1024)
            mb_total = total / (1024 * 1024)
            self._progress_label.setText(f"{mb_down:.1f} / {mb_total:.1f} MB")

    def _on_download_finished(self, success: bool, message: str) -> None:
        """다운로드 완료 처리."""
        self._download_thread = None
        self._next_btn.setEnabled(True)

        if success:
            self._progress_bar.setValue(100)
            self._progress_label.setText("Download complete!")
        else:
            self._progress_label.setText(f"Error: {message}")
            self._progress_bar.setValue(0)

    # -- macOS 권한 --

    @staticmethod
    def _open_mic_settings() -> None:
        """macOS 시스템 설정의 마이크 권한 페이지를 연다."""
        subprocess.Popen(
            ["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone"]
        )

    # -- 공개 API --

    def reject(self) -> None:
        """ESC 키 또는 닫기 버튼 — 모델 미다운로드 시 닫기 방지."""
        if not is_model_downloaded("small"):
            return  # 모델 없으면 닫기 거부
        super().reject()

    @property
    def selected_language(self) -> str:
        """선택된 언어 코드."""
        return self._selected_language

    @property
    def current_page(self) -> int:
        """현재 페이지 인덱스 (0-based)."""
        return self._stack.currentIndex()
