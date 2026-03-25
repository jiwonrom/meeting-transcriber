"""settings_dialog 모듈 단위 테스트."""
from __future__ import annotations

from unittest.mock import patch

from meeting_transcriber.ui.settings_dialog import SettingsDialog


def test_settings_dialog_creation(qtbot: object) -> None:
    """설정 다이얼로그가 정상 생성되는지 확인."""
    with patch("meeting_transcriber.ui.settings_dialog.get_api_key", return_value=None):
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)  # type: ignore[union-attr]

    assert dialog.windowTitle() == "Settings"


def test_settings_dialog_has_tabs(qtbot: object) -> None:
    """4개 탭이 존재하는지 확인."""
    with patch("meeting_transcriber.ui.settings_dialog.get_api_key", return_value=None):
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)  # type: ignore[union-attr]

    assert dialog._tabs.count() == 4
    tab_texts = [dialog._tabs.tabText(i) for i in range(4)]
    assert "General" in tab_texts
    assert "Overlay" in tab_texts
    assert "Audio" in tab_texts
    assert "API Keys" in tab_texts


def test_settings_dialog_loads_defaults(qtbot: object) -> None:
    """기본 설정값이 UI에 반영되는지 확인."""
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


def test_settings_dialog_save_api_key(qtbot: object) -> None:
    """API 키 저장이 Keychain을 사용하는지 확인."""
    with patch("meeting_transcriber.ui.settings_dialog.get_api_key", return_value=None):
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)  # type: ignore[union-attr]

    dialog._gemini_key_input.setText("test-api-key")

    with patch("meeting_transcriber.ui.settings_dialog.store_api_key") as mock_store:
        dialog._save_api_key()
        mock_store.assert_called_once_with("gemini", "test-api-key")
