"""keychain 모듈 단위 테스트."""
from __future__ import annotations

from unittest.mock import patch

from meeting_transcriber.utils.keychain import delete_api_key, get_api_key, store_api_key


def test_store_api_key() -> None:
    """API 키 저장이 keyring.set_password를 호출하는지 확인."""
    with patch("meeting_transcriber.utils.keychain.keyring") as mock_kr:
        store_api_key("gemini", "test-key-123")
        mock_kr.set_password.assert_called_once_with(
            "meeting_transcriber.gemini", "api_key", "test-key-123"
        )


def test_get_api_key() -> None:
    """API 키 조회가 keyring.get_password를 호출하는지 확인."""
    with patch("meeting_transcriber.utils.keychain.keyring") as mock_kr:
        mock_kr.get_password.return_value = "my-secret-key"
        result = get_api_key("gemini")
        assert result == "my-secret-key"
        mock_kr.get_password.assert_called_once_with(
            "meeting_transcriber.gemini", "api_key"
        )


def test_get_api_key_not_found() -> None:
    """존재하지 않는 키 조회 시 None을 반환하는지 확인."""
    with patch("meeting_transcriber.utils.keychain.keyring") as mock_kr:
        mock_kr.get_password.return_value = None
        result = get_api_key("nonexistent")
        assert result is None


def test_delete_api_key() -> None:
    """API 키 삭제가 keyring.delete_password를 호출하는지 확인."""
    with patch("meeting_transcriber.utils.keychain.keyring") as mock_kr:
        delete_api_key("gemini")
        mock_kr.delete_password.assert_called_once_with(
            "meeting_transcriber.gemini", "api_key"
        )


def test_delete_api_key_not_found() -> None:
    """존재하지 않는 키 삭제가 에러 없이 동작하는지 확인."""
    with patch("meeting_transcriber.utils.keychain.keyring") as mock_kr:
        mock_kr.delete_password.side_effect = mock_kr.errors.PasswordDeleteError
        mock_kr.errors.PasswordDeleteError = Exception
        delete_api_key("nonexistent")  # 에러 없어야 함
