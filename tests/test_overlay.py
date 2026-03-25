"""overlay 및 theme 모듈 단위 테스트."""
from __future__ import annotations

import pathlib

from PyQt6.QtCore import Qt

from meeting_transcriber.ui.overlay import OverlayWidget
from meeting_transcriber.ui.theme import ThemeEngine

FIXTURES_DIR = pathlib.Path(__file__).parent.parent / "design"


# ============================================================
# ThemeEngine 테스트
# ============================================================


def test_theme_engine_light() -> None:
    """light 토큰으로 ThemeEngine이 생성되는지 확인."""
    engine = ThemeEngine(FIXTURES_DIR / "tokens_light.json")
    assert "rgba" in engine.tokens["colors"]["background"]["overlay"]


def test_theme_engine_dark() -> None:
    """dark 토큰으로 ThemeEngine이 생성되는지 확인."""
    engine = ThemeEngine(FIXTURES_DIR / "tokens_dark.json")
    assert "rgba" in engine.tokens["colors"]["background"]["overlay"]


def test_theme_engine_overlay_qss() -> None:
    """overlay QSS가 올바른 속성을 포함하는지 확인."""
    engine = ThemeEngine(FIXTURES_DIR / "tokens_light.json")
    qss = engine.generate_overlay_qss()
    assert "color: #FFFFFF" in qss
    assert "font-size:" in qss


def test_theme_engine_app_qss() -> None:
    """전체 앱 QSS가 올바른 속성을 포함하는지 확인."""
    engine = ThemeEngine(FIXTURES_DIR / "tokens_light.json")
    qss = engine.generate_qss()
    assert "QMainWindow" in qss
    assert "QListWidget" in qss


# ============================================================
# OverlayWidget 테스트 (Spotlight 스타일)
# ============================================================


def test_overlay_creation(qtbot: object) -> None:
    """오버레이가 올바른 윈도우 플래그로 생성되는지 확인."""
    overlay = OverlayWidget()
    qtbot.addWidget(overlay)  # type: ignore[union-attr]
    flags = overlay.windowFlags()
    assert flags & Qt.WindowType.WindowStaysOnTopHint
    assert flags & Qt.WindowType.FramelessWindowHint
    assert flags & Qt.WindowType.Tool


def test_overlay_fixed_size(qtbot: object) -> None:
    """오버레이가 고정 크기(600x80)인지 확인."""
    overlay = OverlayWidget()
    qtbot.addWidget(overlay)  # type: ignore[union-attr]
    assert overlay.width() == 600
    assert overlay.height() == 80


def test_overlay_update_caption(qtbot: object) -> None:
    """update_caption으로 텍스트가 설정되는지 확인."""
    overlay = OverlayWidget()
    qtbot.addWidget(overlay)  # type: ignore[union-attr]
    overlay.update_caption("Hello world")
    assert overlay.get_caption_text() == "Hello world"


def test_overlay_append_caption(qtbot: object) -> None:
    """append_caption으로 텍스트가 추가되는지 확인."""
    overlay = OverlayWidget(max_lines=5)
    qtbot.addWidget(overlay)  # type: ignore[union-attr]
    overlay.append_caption("Line 1")
    overlay.append_caption("Line 2")
    assert overlay.get_caption_text() == "Line 1\nLine 2"


def test_overlay_line_limit(qtbot: object) -> None:
    """줄 수 제한이 동작하는지 확인."""
    overlay = OverlayWidget(max_lines=2)
    qtbot.addWidget(overlay)  # type: ignore[union-attr]
    overlay.append_caption("Line 1")
    overlay.append_caption("Line 2")
    overlay.append_caption("Line 3")
    lines = overlay.get_caption_text().split("\n")
    assert len(lines) == 2
    assert "Line 1" not in overlay.get_caption_text()


def test_overlay_clear(qtbot: object) -> None:
    """clear_caption으로 텍스트가 초기화되는지 확인."""
    overlay = OverlayWidget()
    qtbot.addWidget(overlay)  # type: ignore[union-attr]
    overlay.append_caption("Some text")
    overlay.clear_caption()
    assert overlay.get_caption_text() == ""


def test_overlay_toggle_visibility(qtbot: object) -> None:
    """toggle_visibility가 동작하는지 확인."""
    overlay = OverlayWidget()
    qtbot.addWidget(overlay)  # type: ignore[union-attr]
    signals: list[bool] = []
    overlay.visibility_changed.connect(lambda v: signals.append(v))

    overlay.show()
    overlay.toggle_visibility()
    assert not overlay.isVisible()
    assert signals[-1] is False

    overlay.toggle_visibility()
    assert overlay.isVisible()
    assert signals[-1] is True


def test_overlay_font_size(qtbot: object) -> None:
    """set_font_size가 동작하는지 확인."""
    overlay = OverlayWidget(font_size=15)
    qtbot.addWidget(overlay)  # type: ignore[union-attr]
    overlay.set_font_size(20)
    assert overlay._label.font().pixelSize() == 20


def test_overlay_opacity(qtbot: object) -> None:
    """set_opacity가 동작하는지 확인."""
    overlay = OverlayWidget(opacity=0.5)
    qtbot.addWidget(overlay)  # type: ignore[union-attr]
    assert overlay._bg_color.alpha() == 127

    overlay.set_opacity(1.0)
    assert overlay._bg_color.alpha() == 255


def test_overlay_recording_state(qtbot: object) -> None:
    """set_recording이 상태를 변경하는지 확인."""
    overlay = OverlayWidget()
    qtbot.addWidget(overlay)  # type: ignore[union-attr]

    overlay.set_recording(True)
    assert overlay._is_recording is True
    # _status_dot.isHidden()은 위젯이 hide()된 경우에만 True
    assert not overlay._status_dot.isHidden()

    overlay.set_recording(False)
    assert overlay._is_recording is False
    assert overlay._status_dot.isHidden()


def test_overlay_empty_append_ignored(qtbot: object) -> None:
    """빈 문자열 append가 무시되는지 확인."""
    overlay = OverlayWidget()
    qtbot.addWidget(overlay)  # type: ignore[union-attr]
    overlay.append_caption("Hello")
    overlay.append_caption("")
    overlay.append_caption("   ")
    assert overlay.get_caption_text() == "Hello"


def test_overlay_max_lines_change(qtbot: object) -> None:
    """set_max_lines로 줄 수 변경이 동작하는지 확인."""
    overlay = OverlayWidget(max_lines=5)
    qtbot.addWidget(overlay)  # type: ignore[union-attr]
    for i in range(5):
        overlay.append_caption(f"Line {i}")
    overlay.set_max_lines(2)
    lines = overlay.get_caption_text().split("\n")
    assert len(lines) == 2
