"""shortcuts 모듈 단위 테스트."""
from __future__ import annotations

from PyQt6.QtWidgets import QWidget

from meeting_transcriber.utils.shortcuts import ShortcutManager


def test_shortcut_register(qtbot: object) -> None:
    """단축키 등록이 동작하는지 확인."""
    parent = QWidget()
    qtbot.addWidget(parent)  # type: ignore[union-attr]

    manager = ShortcutManager(parent)
    called = [False]

    manager.register("Ctrl+T", lambda: called.__setitem__(0, True))
    assert "Ctrl+T" in manager.registered_keys


def test_shortcut_unregister(qtbot: object) -> None:
    """단축키 해제가 동작하는지 확인."""
    parent = QWidget()
    qtbot.addWidget(parent)  # type: ignore[union-attr]

    manager = ShortcutManager(parent)
    manager.register("Ctrl+T", lambda: None)
    manager.unregister("Ctrl+T")

    assert "Ctrl+T" not in manager.registered_keys


def test_shortcut_unregister_all(qtbot: object) -> None:
    """모든 단축키 해제가 동작하는지 확인."""
    parent = QWidget()
    qtbot.addWidget(parent)  # type: ignore[union-attr]

    manager = ShortcutManager(parent)
    manager.register("Ctrl+A", lambda: None)
    manager.register("Ctrl+B", lambda: None)
    manager.unregister_all()

    assert manager.registered_keys == []


def test_shortcut_re_register(qtbot: object) -> None:
    """같은 키를 재등록하면 이전 것이 교체되는지 확인."""
    parent = QWidget()
    qtbot.addWidget(parent)  # type: ignore[union-attr]

    manager = ShortcutManager(parent)
    manager.register("Ctrl+T", lambda: None)
    manager.register("Ctrl+T", lambda: None)  # 재등록

    assert manager.registered_keys.count("Ctrl+T") == 1


def test_shortcut_unregister_nonexistent(qtbot: object) -> None:
    """존재하지 않는 키 해제가 에러 없이 동작하는지 확인."""
    parent = QWidget()
    qtbot.addWidget(parent)  # type: ignore[union-attr]

    manager = ShortcutManager(parent)
    manager.unregister("Ctrl+Z")  # 에러 없어야 함
