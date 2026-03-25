"""글로벌 단축키 관리 — QShortcut 기반 앱 내 단축키."""
from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import QWidget


class ShortcutManager:
    """앱 내 키보드 단축키를 관리한다.

    PyQt6 QShortcut 기반으로 앱 포커스 내에서 동작한다.
    """

    def __init__(self, parent: QWidget) -> None:
        """ShortcutManager를 초기화한다.

        Args:
            parent: 단축키가 바인딩될 부모 위젯
        """
        self._parent = parent
        self._shortcuts: dict[str, QShortcut] = {}

    def register(self, key_combo: str, callback: Callable[[], None]) -> None:
        """단축키를 등록한다.

        Args:
            key_combo: 키 조합 문자열 (예: "Ctrl+Shift+R")
            callback: 단축키 활성화 시 호출할 함수
        """
        if key_combo in self._shortcuts:
            self.unregister(key_combo)

        shortcut = QShortcut(QKeySequence(key_combo), self._parent)
        shortcut.activated.connect(callback)
        self._shortcuts[key_combo] = shortcut

    def unregister(self, key_combo: str) -> None:
        """단축키를 해제한다.

        Args:
            key_combo: 해제할 키 조합 문자열
        """
        shortcut = self._shortcuts.pop(key_combo, None)
        if shortcut is not None:
            shortcut.setEnabled(False)
            shortcut.deleteLater()

    def unregister_all(self) -> None:
        """모든 단축키를 해제한다."""
        for key in list(self._shortcuts.keys()):
            self.unregister(key)

    @property
    def registered_keys(self) -> list[str]:
        """등록된 단축키 목록을 반환한다."""
        return list(self._shortcuts.keys())
