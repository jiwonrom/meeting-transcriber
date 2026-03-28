"""settings_dialog 모듈 단위 테스트."""

from __future__ import annotations

from unittest.mock import patch

from PyQt6.QtWidgets import QLabel

from meeting_transcriber.ui.settings_dialog import SettingsDialog
from meeting_transcriber.utils.config import invalidate_settings_cache


def test_settings_dialog_creation(qtbot: object) -> None:
    """설정 다이얼로그가 정상 생성되는지 확인."""
    with patch("meeting_transcriber.ui.settings_dialog.get_api_key", return_value=None):
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)  # type: ignore[union-attr]

    assert dialog.windowTitle() == "Preferences"


def test_settings_dialog_has_tabs(qtbot: object) -> None:
    """4개 탭이 존재하는지 확인."""
    with patch("meeting_transcriber.ui.settings_dialog.get_api_key", return_value=None):
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)  # type: ignore[union-attr]

    assert dialog._tabs.count() == 6
    tab_texts = [dialog._tabs.tabText(i) for i in range(6)]
    assert "General" in tab_texts
    assert "Overlay" in tab_texts
    assert "Audio" in tab_texts
    assert "API Keys" in tab_texts
    assert "Speaker Identification" in tab_texts
    assert "Detection" in tab_texts


def test_settings_dialog_loads_defaults(qtbot: object) -> None:
    """기본 설정값이 UI에 반영되는지 확인."""
    invalidate_settings_cache()
    with patch("meeting_transcriber.ui.settings_dialog.get_api_key", return_value=None):
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)  # type: ignore[union-attr]

    assert dialog._lang_combo.currentData() == "auto"
    assert dialog._lines_spin.value() == 2
    assert dialog._font_spin.value() == 18


def test_settings_dialog_save(qtbot: object) -> None:
    """설정 저장이 동작하는지 확인."""
    with patch("meeting_transcriber.ui.settings_dialog.get_api_key", return_value=None):
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)  # type: ignore[union-attr]

    dialog._lines_spin.setValue(4)
    dialog._font_spin.setValue(24)

    with patch("meeting_transcriber.ui.settings_dialog.save_settings") as mock_save:
        dialog._save_and_close()
        saved = mock_save.call_args[0][0]
        assert saved["overlay"]["lines"] == 4
        assert saved["overlay"]["font_size"] == 24


def test_settings_dialog_save_api_keys(qtbot: object) -> None:
    """API 키 저장이 Keychain을 사용하는지 확인."""
    with patch("meeting_transcriber.ui.settings_dialog.get_api_key", return_value=None):
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)  # type: ignore[union-attr]

    dialog._gemini_key_input.setText("test-gemini-key")
    dialog._openai_key_input.setText("test-openai-key")

    with patch("meeting_transcriber.ui.settings_dialog.store_api_key") as mock_store:
        dialog._save_api_keys()
        assert mock_store.call_count == 2
        mock_store.assert_any_call("gemini", "test-gemini-key")
        mock_store.assert_any_call("openai", "test-openai-key")


def test_system_audio_section_exists(qtbot: object) -> None:
    """Audio 탭에 System Audio 섹션이 존재하는지 확인."""
    with patch("meeting_transcriber.ui.settings_dialog.get_api_key", return_value=None):
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)  # type: ignore[union-attr]

    # Find the System Audio heading label in the audio tab
    audio_tab = dialog._tabs.widget(2)  # Audio tab is index 2
    labels = audio_tab.findChildren(QLabel)  # type: ignore[union-attr]
    label_texts = [lbl.text() for lbl in labels]
    assert "System Audio" in label_texts


@patch(
    "meeting_transcriber.ui.settings_dialog.is_blackhole_installed",
    return_value=False,
)
def test_blackhole_status_not_installed(mock_bh: object, qtbot: object) -> None:
    """BlackHole 미설치 시 상태가 올바르게 표시되는지 확인."""
    with patch("meeting_transcriber.ui.settings_dialog.get_api_key", return_value=None):
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)  # type: ignore[union-attr]

    assert dialog._blackhole_status.text() == "Not installed"
    assert dialog._blackhole_setup_btn.text() == "Set Up"


@patch(
    "meeting_transcriber.ui.settings_dialog.is_blackhole_installed",
    return_value=True,
)
def test_blackhole_status_installed(mock_bh: object, qtbot: object) -> None:
    """BlackHole 설치 시 상태가 올바르게 표시되는지 확인."""
    with patch("meeting_transcriber.ui.settings_dialog.get_api_key", return_value=None):
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)  # type: ignore[union-attr]

    assert dialog._blackhole_status.text() == "Installed"
    assert dialog._blackhole_setup_btn.text() == "Reconfigure"
