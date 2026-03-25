"""macOS Keychain 연동 — API 키 안전 저장."""
from __future__ import annotations

import keyring

_SERVICE_PREFIX = "meeting_transcriber"


def store_api_key(service: str, key: str) -> None:
    """API 키를 macOS Keychain에 저장한다.

    Args:
        service: 서비스 식별자 (예: "gemini")
        key: 저장할 API 키
    """
    keyring.set_password(f"{_SERVICE_PREFIX}.{service}", "api_key", key)


def get_api_key(service: str) -> str | None:
    """macOS Keychain에서 API 키를 가져온다.

    Args:
        service: 서비스 식별자 (예: "gemini")

    Returns:
        API 키 문자열. 없으면 None.
    """
    return keyring.get_password(f"{_SERVICE_PREFIX}.{service}", "api_key")


def delete_api_key(service: str) -> None:
    """macOS Keychain에서 API 키를 삭제한다.

    Args:
        service: 서비스 식별자 (예: "gemini")
    """
    try:
        keyring.delete_password(f"{_SERVICE_PREFIX}.{service}", "api_key")
    except keyring.errors.PasswordDeleteError:
        pass  # 이미 없으면 무시
