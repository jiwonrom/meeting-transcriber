"""설정 다이얼로그 — 언어, 모델, 오버레이, 오디오, API 키, 내보내기."""

from __future__ import annotations

import pathlib
from typing import Any

from PyQt6.QtCore import QUrl, Qt, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
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
from meeting_transcriber.core.system_audio import is_blackhole_installed
from meeting_transcriber.ui.blackhole_wizard import BlackHoleSetupWizard
from meeting_transcriber.utils.config import load_settings, save_settings
from meeting_transcriber.ai.templates import TemplateManager
from meeting_transcriber.utils.constants import (
    AGGREGATE_DEVICE_NAME,
    BUILTIN_TEMPLATE_NAMES,
    OVERLAY_DEFAULT_LINES,
    OVERLAY_MAX_LINES,
    SUPPORTED_LANGUAGES,
    TEMPLATES_DIR,
)
from meeting_transcriber.utils.keychain import get_api_key, store_api_key


class SettingsDialog(QDialog):
    """앱 설정 다이얼로그.

    General, Overlay, Audio, API Keys 4개 탭으로 구성된다.
    """

    settings_changed = pyqtSignal(dict)

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Preferences")
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
        self._tabs.addTab(self._create_speaker_tab(), "Speaker Identification")
        self._tabs.addTab(self._create_detection_tab(), "Detection")
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

        # 내보내기 디렉토리
        export_dir_layout = QHBoxLayout()
        self._export_dir_input = QLineEdit()
        self._export_dir_input.setPlaceholderText("Choose directory...")
        self._export_dir_input.setReadOnly(True)
        export_dir_layout.addWidget(self._export_dir_input)
        export_dir_browse = QPushButton("Browse...")
        export_dir_browse.setFixedWidth(80)
        export_dir_browse.clicked.connect(self._browse_export_dir)
        export_dir_layout.addWidget(export_dir_browse)
        form.addRow("Export Directory:", export_dir_layout)

        # Obsidian 볼트 경로
        obsidian_layout = QHBoxLayout()
        self._obsidian_vault_input = QLineEdit()
        self._obsidian_vault_input.setPlaceholderText("Choose Obsidian vault...")
        self._obsidian_vault_input.setReadOnly(True)
        obsidian_layout.addWidget(self._obsidian_vault_input)
        obsidian_browse = QPushButton("Browse...")
        obsidian_browse.setFixedWidth(80)
        obsidian_browse.clicked.connect(self._browse_obsidian_vault)
        obsidian_layout.addWidget(obsidian_browse)
        form.addRow("Obsidian Vault:", obsidian_layout)

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
        self._opacity_slider.valueChanged.connect(lambda v: self._opacity_label.setText(f"{v}%"))
        form.addRow("Opacity:", self._opacity_slider)
        form.addRow("", self._opacity_label)

        return tab

    def _create_audio_tab(self) -> QWidget:
        """Audio 탭."""
        tab = QWidget()
        audio_layout = QVBoxLayout(tab)

        form = QFormLayout()

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

        audio_layout.addLayout(form)

        # System Audio section
        sys_audio_heading = QLabel("System Audio")
        sys_audio_heading.setObjectName("heading")
        audio_layout.addWidget(sys_audio_heading)

        # BlackHole status row
        status_row = QHBoxLayout()
        status_row.addWidget(QLabel("BlackHole:"))
        self._blackhole_status = QLabel()
        self._blackhole_setup_btn = QPushButton()

        if is_blackhole_installed():
            self._blackhole_status.setText("Installed")
            self._blackhole_status.setProperty("status", "success")
            self._blackhole_setup_btn.setText("Reconfigure")
        else:
            self._blackhole_status.setText("Not installed")
            self._blackhole_status.setObjectName("caption")
            self._blackhole_setup_btn.setText("Set Up")

        self._blackhole_setup_btn.clicked.connect(self._open_blackhole_wizard)
        status_row.addWidget(self._blackhole_status)
        status_row.addStretch()
        status_row.addWidget(self._blackhole_setup_btn)
        audio_layout.addLayout(status_row)

        # Aggregate Device status row
        device_row = QHBoxLayout()
        device_row.addWidget(QLabel("Device:"))
        settings = load_settings()
        agg_uid = settings.get("audio", {}).get("system_audio", {}).get(
            "aggregate_device_uid"
        )
        if agg_uid:
            self._agg_device_label = QLabel(AGGREGATE_DEVICE_NAME)
            self._agg_device_label.setObjectName("caption")
        else:
            self._agg_device_label = QLabel("Not configured")
            self._agg_device_label.setObjectName("caption")
        device_row.addWidget(self._agg_device_label)
        device_row.addStretch()
        audio_layout.addLayout(device_row)

        audio_layout.addStretch()

        return tab

    def _open_blackhole_wizard(self) -> None:
        """BlackHole 설치 위저드를 연다."""
        wizard = BlackHoleSetupWizard(self)
        wizard.setup_completed.connect(self._on_blackhole_setup_done)
        wizard.exec()

    def _on_blackhole_setup_done(self) -> None:
        """BlackHole 설치 완료 -- 상태 갱신."""
        self._blackhole_status.setText("Installed")
        self._blackhole_status.setProperty("status", "success")
        style = self._blackhole_status.style()
        if style is not None:
            style.unpolish(self._blackhole_status)
            style.polish(self._blackhole_status)
        self._blackhole_setup_btn.setText("Reconfigure")
        self._agg_device_label.setText(AGGREGATE_DEVICE_NAME)

    def _create_api_tab(self) -> QWidget:
        """API Keys 탭."""
        tab = QWidget()
        form = QFormLayout(tab)

        info = QLabel("API keys are stored securely in macOS Keychain.")
        info.setObjectName("caption")
        info.setWordWrap(True)
        form.addRow(info)

        self._gemini_key_input = QLineEdit()
        self._gemini_key_input.setPlaceholderText("Enter Gemini API key")
        self._gemini_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Gemini API Key:", self._gemini_key_input)

        self._openai_key_input = QLineEdit()
        self._openai_key_input.setPlaceholderText("Enter OpenAI API key")
        self._openai_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("OpenAI API Key:", self._openai_key_input)

        self._anthropic_key_input = QLineEdit()
        self._anthropic_key_input.setPlaceholderText("Enter Anthropic API key")
        self._anthropic_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Anthropic API Key:", self._anthropic_key_input)

        save_key_btn = QPushButton("Save Keys")
        save_key_btn.clicked.connect(self._save_api_keys)
        form.addRow("", save_key_btn)

        # 기본 AI 프로바이더 선택
        self._default_provider_combo = QComboBox()
        self._default_provider_combo.addItem("Gemini", "gemini")
        self._default_provider_combo.addItem("OpenAI", "openai")
        self._default_provider_combo.addItem("Anthropic", "anthropic")
        form.addRow("Default AI Provider:", self._default_provider_combo)

        return tab

    def _create_speaker_tab(self) -> QWidget:
        """Speaker Identification 탭."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        heading = QLabel("Speaker Identification")
        heading.setFont(QLabel().font())
        font = heading.font()
        font.setPixelSize(14)
        font.setWeight(font.Weight.DemiBold)
        heading.setFont(font)
        layout.addWidget(heading)

        info = QLabel(
            "Required for downloading the speaker identification model. "
            "Get a token at huggingface.co/settings/tokens"
        )
        info.setObjectName("caption")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Token input row
        token_row = QHBoxLayout()
        token_label = QLabel("HuggingFace Token")
        token_row.addWidget(token_label)

        self._hf_token_input = QLineEdit()
        self._hf_token_input.setObjectName("hf_token_input")
        self._hf_token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._hf_token_input.setFixedWidth(280)
        self._hf_token_input.setPlaceholderText("Enter HuggingFace token")
        token_row.addWidget(self._hf_token_input)

        save_token_btn = QPushButton("Save Token")
        save_token_btn.setFixedWidth(80)
        save_token_btn.clicked.connect(self._save_hf_token)
        token_row.addWidget(save_token_btn)
        layout.addLayout(token_row)

        # Status label
        self._hf_status_label = QLabel("Required for speaker identification")
        self._hf_status_label.setObjectName("caption")
        layout.addWidget(self._hf_status_label)

        # Get Token button
        get_token_btn = QPushButton("Get Token")
        get_token_btn.setFixedWidth(100)
        get_token_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://huggingface.co/settings/tokens"))
        )
        layout.addWidget(get_token_btn)

        layout.addStretch()

        # Load existing token state
        existing = get_api_key("huggingface")
        if existing:
            self._hf_token_input.setPlaceholderText("••••••• (saved)")
            self._hf_status_label.setText("Token saved")

        return tab

    def _save_hf_token(self) -> None:
        """HuggingFace 토큰을 Keychain에 저장한다."""
        token = self._hf_token_input.text().strip()
        if not token:
            return

        if not token.startswith("hf_"):
            self._hf_status_label.setText("Token must start with 'hf_'")
            return

        store_api_key("huggingface", token)
        self._hf_token_input.clear()
        self._hf_token_input.setPlaceholderText("••••••• (saved)")
        self._hf_status_label.setText("Token saved")

    def _create_detection_tab(self) -> QWidget:
        """Detection 탭 — 회의 감지 + 템플릿 설정."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # -- Meeting Detection 섹션 --
        det_heading = QLabel("Meeting Detection")
        font = det_heading.font()
        font.setPixelSize(14)
        font.setWeight(font.Weight.DemiBold)
        det_heading.setFont(font)
        layout.addWidget(det_heading)

        from PyQt6.QtWidgets import QCheckBox

        det_row = QHBoxLayout()
        self._detection_toggle = QCheckBox("Auto-detect meetings")
        self._detection_toggle.setChecked(True)
        det_row.addWidget(self._detection_toggle)
        det_row.addStretch()
        layout.addLayout(det_row)

        self._detection_help = QLabel(
            "Detect Zoom, Teams, Meet, and FaceTime to prompt recording."
        )
        self._detection_help.setObjectName("caption")
        self._detection_help.setWordWrap(True)
        layout.addWidget(self._detection_help)

        self._detection_toggle.toggled.connect(self._on_detection_toggled)

        # -- Meeting Templates 섹션 --
        tmpl_heading = QLabel("Meeting Templates")
        font2 = tmpl_heading.font()
        font2.setPixelSize(14)
        font2.setWeight(font2.Weight.DemiBold)
        tmpl_heading.setFont(font2)
        layout.addWidget(tmpl_heading)

        # 기본 템플릿 선택
        tmpl_row = QHBoxLayout()
        tmpl_row.addWidget(QLabel("Default template"))
        self._default_template_combo = QComboBox()
        self._default_template_combo.setFixedWidth(140)

        # 템플릿 목록 채우기
        tmgr = TemplateManager()
        tmgr.ensure_templates()
        templates = tmgr.load_all()
        for key in BUILTIN_TEMPLATE_NAMES:
            tmpl = templates.get(key)
            if tmpl:
                self._default_template_combo.addItem(tmpl.name, key)
        custom_keys = sorted(k for k in templates if k not in BUILTIN_TEMPLATE_NAMES)
        for key in custom_keys:
            self._default_template_combo.addItem(templates[key].name, key)

        tmpl_row.addWidget(self._default_template_combo)
        tmpl_row.addStretch()
        layout.addLayout(tmpl_row)

        # 템플릿 폴더
        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("Templates folder"))
        folder_path = QLabel(f"~/.meeting_transcriber/templates/")
        folder_path.setObjectName("caption")
        folder_row.addWidget(folder_path)
        open_folder_btn = QPushButton("Open Folder")
        open_folder_btn.setFixedWidth(100)
        open_folder_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(TEMPLATES_DIR)))
        )
        folder_row.addWidget(open_folder_btn)
        folder_row.addStretch()
        layout.addLayout(folder_row)

        tmpl_help = QLabel(
            "Add custom templates by placing YAML files in the templates folder. "
            "New files are loaded on next app launch."
        )
        tmpl_help.setObjectName("caption")
        tmpl_help.setWordWrap(True)
        layout.addWidget(tmpl_help)

        layout.addStretch()
        return tab

    def _on_detection_toggled(self, checked: bool) -> None:
        """감지 토글 변경 시 도움말 텍스트를 업데이트한다.

        Args:
            checked: 감지 활성화 여부
        """
        if checked:
            self._detection_help.setText(
                "Detect Zoom, Teams, Meet, and FaceTime to prompt recording."
            )
        else:
            self._detection_help.setText("Meeting detection is off.")

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

        # Export
        export = s.get("export", {})
        export_dir = export.get("default_dir", "")
        if export_dir:
            self._export_dir_input.setText(export_dir)
        obsidian_vault = export.get("obsidian_vault", "")
        if obsidian_vault:
            self._obsidian_vault_input.setText(obsidian_vault)

        # AI 기본 프로바이더
        ai = s.get("ai", {})
        default_provider = ai.get("default_provider", "gemini")
        idx = self._default_provider_combo.findData(default_provider)
        if idx >= 0:
            self._default_provider_combo.setCurrentIndex(idx)

        # Detection
        detection = s.get("detection", {})
        det_enabled = detection.get("enabled", True)
        self._detection_toggle.setChecked(det_enabled)

        # Templates
        templates_cfg = s.get("templates", {})
        default_tmpl = templates_cfg.get("default", "general")
        idx = self._default_template_combo.findData(default_tmpl)
        if idx >= 0:
            self._default_template_combo.setCurrentIndex(idx)

        # API Key (Keychain에서 존재 여부만 표시)
        existing = get_api_key("gemini")
        if existing:
            self._gemini_key_input.setPlaceholderText("••••••• (saved)")
        if get_api_key("openai"):
            self._openai_key_input.setPlaceholderText("••••••• (saved)")
        if get_api_key("anthropic"):
            self._anthropic_key_input.setPlaceholderText("••••••• (saved)")

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

        s.setdefault("export", {})
        s["export"]["default_dir"] = self._export_dir_input.text()
        s["export"]["obsidian_vault"] = self._obsidian_vault_input.text()

        s.setdefault("ai", {})
        s["ai"]["default_provider"] = self._default_provider_combo.currentData()

        s.setdefault("detection", {})
        s["detection"]["enabled"] = self._detection_toggle.isChecked()

        s.setdefault("templates", {})
        s["templates"]["default"] = self._default_template_combo.currentData()

        save_settings(s)
        self.settings_changed.emit(s)
        self.accept()

    def _save_api_keys(self) -> None:
        """모든 AI 프로바이더의 API 키를 Keychain에 저장한다."""
        for service, input_field in [
            ("gemini", self._gemini_key_input),
            ("openai", self._openai_key_input),
            ("anthropic", self._anthropic_key_input),
        ]:
            key = input_field.text().strip()
            if key:
                store_api_key(service, key)
                input_field.clear()
                input_field.setPlaceholderText("••••••• (saved)")

    def _browse_export_dir(self) -> None:
        """내보내기 디렉토리를 선택한다."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Export Directory",
            str(pathlib.Path.home()),
        )
        if directory:
            self._export_dir_input.setText(directory)

    def _browse_obsidian_vault(self) -> None:
        """Obsidian 볼트 디렉토리를 선택한다."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Obsidian Vault",
            str(pathlib.Path.home()),
        )
        if directory:
            self._obsidian_vault_input.setText(directory)

    def get_settings(self) -> dict[str, Any]:
        """현재 UI의 설정값을 딕셔너리로 반환한다."""
        return self._settings
