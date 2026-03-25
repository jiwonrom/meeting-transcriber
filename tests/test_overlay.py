"""overlay 및 theme 모듈 단위 테스트."""
from __future__ import annotations

import pathlib
from unittest.mock import patch

from PyQt6.QtCore import Qt

from meeting_transcriber.ui.overlay import OverlayWidget
from meeting_transcriber.ui.theme import ThemeEngine

# -- pytest-qt가 QApplication을 자동 생성 --


# ============================================================
# ThemeEngine 테스트
# ============================================================

FIXTURES_DIR = pathlib.Path(__file__).parent.parent / "design"


def test_theme_engine_light() -> None:
    """light 토큰으로 ThemeEngine이 생성되는지 확인."""
    engine = ThemeEngine(FIXTURES_DIR / "tokens_light.json")
    assert engine.tokens["colors"]["background"]["overlay"] == "rgba(0, 0, 0, 0.75)"


def test_theme_engine_dark() -> None:
    """dark 토큰으로 ThemeEngine이 생성되는지 확인."""
    engine = ThemeEngine(FIXTURES_DIR / "tokens_dark.json")
    assert engine.tokens["colors"]["background"]["overlay"] == "rgba(0, 0, 0, 0.85)"


def test_theme_engine_overlay_qss() -> None:
    """overlay QSS가 올바른 속성을 포함하는지 확인."""
    engine = ThemeEngine(FIXTURES_DIR / "tokens_light.json")
    qss = engine.generate_overlay_qss()
    assert "color: #FFFFFF" in qss
    assert "font-size: 16px" in qss
    assert "padding: 12px" in qss
    assert "border-radius: 12px" in qss
    assert "rgba(0, 0, 0, 0.75)" in qss


def test_theme_engine_app_qss() -> None:
    """전체 앱 QSS가 올바른 속성을 포함하는지 확인."""
    engine = ThemeEngine(FIXTURES_DIR / "tokens_light.json")
    qss = engine.generate_qss()
    assert "QMainWindow" in qss
    assert "QTreeView" in qss
    assert "#FFFFFF" in qss


# ============================================================
# OverlayWidget 테스트
# ============================================================


def test_overlay_creation(qtbot: object) -> None:
    """오버레이가 올바른 윈도우 플래그로 생성되는지 확인."""
    overlay = OverlayWidget()
    qtbot.addWidget(overlay)  # type: ignore[union-attr]

    flags = overlay.windowFlags()
    assert flags & Qt.WindowType.WindowStaysOnTopHint
    assert flags & Qt.WindowType.FramelessWindowHint
    assert flags & Qt.WindowType.Tool


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
    """기본 2줄 제한이 동작하는지 확인."""
    overlay = OverlayWidget(max_lines=2)
    qtbot.addWidget(overlay)  # type: ignore[union-attr]

    overlay.append_caption("Line 1")
    overlay.append_caption("Line 2")
    overlay.append_caption("Line 3")

    text = overlay.get_caption_text()
    lines = text.split("\n")
    assert len(lines) == 2
    assert "Line 2" in lines
    assert "Line 3" in lines
    assert "Line 1" not in text


def test_overlay_max_lines_change(qtbot: object) -> None:
    """set_max_lines로 줄 수 변경이 동작하는지 확인."""
    overlay = OverlayWidget(max_lines=2)
    qtbot.addWidget(overlay)  # type: ignore[union-attr]

    overlay.append_caption("A")
    overlay.append_caption("B")
    overlay.append_caption("C")

    # 현재 2줄: B, C
    overlay.set_max_lines(5)
    # 확장해도 기존 데이터는 유지
    assert "B" in overlay.get_caption_text()
    assert "C" in overlay.get_caption_text()


def test_overlay_max_lines_shrink(qtbot: object) -> None:
    """set_max_lines로 줄 수를 줄이면 오래된 줄이 제거되는지 확인."""
    overlay = OverlayWidget(max_lines=5)
    qtbot.addWidget(overlay)  # type: ignore[union-attr]

    for i in range(5):
        overlay.append_caption(f"Line {i}")

    overlay.set_max_lines(2)
    lines = overlay.get_caption_text().split("\n")
    assert len(lines) == 2
    assert "Line 3" in lines
    assert "Line 4" in lines


def test_overlay_clear(qtbot: object) -> None:
    """clear_caption으로 텍스트가 초기화되는지 확인."""
    overlay = OverlayWidget()
    qtbot.addWidget(overlay)  # type: ignore[union-attr]

    overlay.append_caption("Some text")
    overlay.clear_caption()
    assert overlay.get_caption_text() == ""


def test_overlay_toggle_visibility(qtbot: object) -> None:
    """toggle_visibility가 신호와 함께 동작하는지 확인."""
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
    """set_font_size가 폰트 크기를 변경하는지 확인."""
    overlay = OverlayWidget(font_size=18)
    qtbot.addWidget(overlay)  # type: ignore[union-attr]

    overlay.set_font_size(24)
    assert overlay._label.font().pixelSize() == 24


def test_overlay_opacity(qtbot: object) -> None:
    """set_opacity가 배경 색상 알파를 변경하는지 확인."""
    overlay = OverlayWidget(opacity=0.5)
    qtbot.addWidget(overlay)  # type: ignore[union-attr]

    assert overlay._bg_color.alpha() == 127  # 0.5 * 255 = 127

    overlay.set_opacity(1.0)
    assert overlay._bg_color.alpha() == 255

    overlay.set_opacity(0.0)
    assert overlay._bg_color.alpha() == 0


def test_overlay_opacity_clamped(qtbot: object) -> None:
    """범위를 벗어난 opacity가 클램핑되는지 확인."""
    overlay = OverlayWidget()
    qtbot.addWidget(overlay)  # type: ignore[union-attr]

    overlay.set_opacity(2.0)
    assert overlay._bg_opacity == 1.0

    overlay.set_opacity(-1.0)
    assert overlay._bg_opacity == 0.0


def test_overlay_position_save_restore(qtbot: object, tmp_path: pathlib.Path) -> None:
    """위치 저장/복원이 동작하는지 확인."""
    overlay = OverlayWidget()
    qtbot.addWidget(overlay)  # type: ignore[union-attr]
    overlay.move(100, 200)

    with (
        patch("meeting_transcriber.ui.overlay.load_settings", return_value={"overlay": {}}),
        patch("meeting_transcriber.ui.overlay.save_settings") as mock_save,
    ):
        overlay.save_position()
        saved = mock_save.call_args[0][0]
        assert saved["overlay"]["position"] == [100, 200]

    with patch(
        "meeting_transcriber.ui.overlay.load_settings",
        return_value={"overlay": {"position": [300, 400]}},
    ):
        overlay.restore_position()
        assert overlay.pos().x() == 300
        assert overlay.pos().y() == 400


def test_overlay_apply_theme(qtbot: object) -> None:
    """apply_theme이 테마 설정을 적용하는지 확인."""
    overlay = OverlayWidget()
    qtbot.addWidget(overlay)  # type: ignore[union-attr]

    theme = ThemeEngine(FIXTURES_DIR / "tokens_light.json")
    overlay.apply_theme(theme)

    assert overlay._label.font().pixelSize() == 16
    assert overlay._border_radius == 12


def test_overlay_update_caption_multiline(qtbot: object) -> None:
    """update_caption이 여러 줄 텍스트를 올바르게 처리하는지 확인."""
    overlay = OverlayWidget(max_lines=3)
    qtbot.addWidget(overlay)  # type: ignore[union-attr]

    overlay.update_caption("Line 1\nLine 2\nLine 3\nLine 4")
    lines = overlay.get_caption_text().split("\n")
    assert len(lines) == 3
    # 가장 최근 3줄만 유지
    assert "Line 2" in lines
    assert "Line 3" in lines
    assert "Line 4" in lines


def test_overlay_empty_append_ignored(qtbot: object) -> None:
    """빈 문자열 append가 무시되는지 확인."""
    overlay = OverlayWidget()
    qtbot.addWidget(overlay)  # type: ignore[union-attr]

    overlay.append_caption("Hello")
    overlay.append_caption("")
    overlay.append_caption("   ")
    assert overlay.get_caption_text() == "Hello"
