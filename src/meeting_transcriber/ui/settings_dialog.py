"""설정 다이얼로그 — 언어, 모델, 오버레이, 오디오, API 키."""
from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from meeting_transcriber.core.audio_capture import list_audio_devices
from meeting_transcriber.core.model_manager import list_available_models
from meeting_transcriber.utils.config import load_settings, save_settings
from meeting_transcriber.utils.constants import (
    OVERLAY_DEFAULT_LINES,
    OVERLAY_MAX_LINES,
    SUPPORTED_LANGUAGES,
)
from meeting_transcriber.utils.keychain import get_api_key, store_api_key


class SettingsDialog(QDialog):
    """앱 설정 다이얼로그.

    General, Overlay, Audio, API Keys 4개 탭으로 구성된다.
    """

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(450, 400)

        self._settings = load_settings()
        self._setup_ui()
        self._load_current_settings()

    def _setup_ui(self) -> None:
        """UI를 구성한다."""
        layout = QVBoxLayout(self)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._create_general_tab(), "General")
        self._tabs.addTab(self._create_overlay_tab(), "Overlay")
        self._tabs.addTab(self._create_audio_tab(), "Audio")
        self._tabs.addTab(self._create_api_tab(), "API Keys")
        layout.addWidget(self._tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # -- 탭 생성 --

    def _create_general_tab(self) -> QWidget:
        """General 탭."""
        tab = QWidget()
        form = QFormLayout(tab)

        # 언어
        self._lang_combo = QComboBox()
        self._lang_combo.addItem("Auto-detect", "auto")
        lang_labels = {"en": "English", "ko": "한국어", "zh": "中文", "ja": "日本語"}
        for lang in SUPPORTED_LANGUAGES:
            self._lang_combo.addItem(lang_labels.get(lang, lang), lang)
        form.addRow("Language:", self._lang_combo)

        # 모델
        self._model_combo = QComboBox()
        models = list_available_models()
        for m in models:
            status = "✓" if m["downloaded"] else "↓"
            self._model_combo.addItem(f"{m['name']} [{status}]", m["name"])
        form.addRow("Whisper Model:", self._model_combo)

        return tab

    def _create_overlay_tab(self) -> QWidget:
        """Overlay 탭."""
        tab = QWidget()
        form = QFormLayout(tab)

        self._lines_spin = QSpinBox()
        self._lines_spin.setRange(1, OVERLAY_MAX_LINES)
        self._lines_spin.setValue(OVERLAY_DEFAULT_LINES)
        form.addRow("Caption Lines:", self._lines_spin)

        self._font_spin = QSpinBox()
        self._font_spin.setRange(10, 48)
        self._font_spin.setValue(18)
        form.addRow("Font Size:", self._font_spin)

        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(10, 100)
        self._opacity_slider.setValue(85)
        self._opacity_label = QLabel("85%")
        self._opacity_slider.valueChanged.connect(
            lambda v: self._opacity_label.setText(f"{v}%")
        )
        form.addRow("Opacity:", self._opacity_slider)
        form.addRow("", self._opacity_label)

        return tab

    def _create_audio_tab(self) -> QWidget:
        """Audio 탭."""
        tab = QWidget()
        form = QFormLayout(tab)

        self._device_combo = QComboBox()
        self._device_combo.addItem("System Default", None)
        devices = list_audio_devices()
        for dev in devices:
            label = f"{dev.name} ({dev.channels}ch)"
            self._device_combo.addItem(label, dev.index)
        form.addRow("Input Device:", self._device_combo)

        self._post_recording_combo = QComboBox()
        self._post_recording_combo.addItem("Ask each time", "ask")
        self._post_recording_combo.addItem("Keep audio", "keep")
        self._post_recording_combo.addItem("Delete after transcription", "delete")
        form.addRow("After Recording:", self._post_recording_combo)

        return tab

    def _create_api_tab(self) -> QWidget:
        """API Keys 탭."""
        tab = QWidget()
        form = QFormLayout(tab)

        info = QLabel("API keys are stored securely in macOS Keychain.")
        info.setStyleSheet("color: #6E6E73; font-size: 12px;")
        info.setWordWrap(True)
        form.addRow(info)

        self._gemini_key_input = QLineEdit()
        self._gemini_key_input.setPlaceholderText("Enter Gemini API key")
        self._gemini_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Gemini API Key:", self._gemini_key_input)

        save_key_btn = QPushButton("Save Key")
        save_key_btn.clicked.connect(self._save_api_key)
        form.addRow("", save_key_btn)

        return tab

    # -- 설정 로드/저장 --

    def _load_current_settings(self) -> None:
        """현재 설정값을 UI에 반영한다."""
        s = self._settings

        # General
        lang = s.get("language", "auto")
        idx = self._lang_combo.findData(lang)
        if idx >= 0:
            self._lang_combo.setCurrentIndex(idx)

        model = s.get("whisper_model", "small")
        idx = self._model_combo.findData(model)
        if idx >= 0:
            self._model_combo.setCurrentIndex(idx)

        # Overlay
        overlay = s.get("overlay", {})
        self._lines_spin.setValue(overlay.get("lines", OVERLAY_DEFAULT_LINES))
        self._font_spin.setValue(overlay.get("font_size", 18))
        opacity_pct = int(overlay.get("opacity", 0.85) * 100)
        self._opacity_slider.setValue(opacity_pct)

        # Audio
        audio = s.get("audio", {})
        device = audio.get("device")
        if device is not None:
            idx = self._device_combo.findData(device)
            if idx >= 0:
                self._device_combo.setCurrentIndex(idx)

        post = audio.get("post_recording", "ask")
        idx = self._post_recording_combo.findData(post)
        if idx >= 0:
            self._post_recording_combo.setCurrentIndex(idx)

        # API Key (Keychain에서 존재 여부만 표시)
        existing = get_api_key("gemini")
        if existing:
            self._gemini_key_input.setPlaceholderText("••••••• (saved)")

    def _save_and_close(self) -> None:
        """설정을 저장하고 다이얼로그를 닫는다."""
        s = self._settings

        s["language"] = self._lang_combo.currentData()
        s["whisper_model"] = self._model_combo.currentData()

        s.setdefault("overlay", {})
        s["overlay"]["lines"] = self._lines_spin.value()
        s["overlay"]["font_size"] = self._font_spin.value()
        s["overlay"]["opacity"] = self._opacity_slider.value() / 100.0

        s.setdefault("audio", {})
        s["audio"]["device"] = self._device_combo.currentData()
        s["audio"]["post_recording"] = self._post_recording_combo.currentData()

        save_settings(s)
        self.accept()

    def _save_api_key(self) -> None:
        """Gemini API 키를 Keychain에 저장한다."""
        key = self._gemini_key_input.text().strip()
        if key:
            store_api_key("gemini", key)
            self._gemini_key_input.clear()
            self._gemini_key_input.setPlaceholderText("••••••• (saved)")

    def get_settings(self) -> dict[str, Any]:
        """현재 UI의 설정값을 딕셔너리로 반환한다."""
        return self._settings
