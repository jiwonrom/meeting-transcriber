"""ThemeEngine — 디자인 토큰 JSON에서 PyQt6 QSS를 생성한다."""
from __future__ import annotations

import json
import pathlib
from typing import Any

from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QApplication

_DESIGN_DIR = pathlib.Path(__file__).resolve().parent.parent.parent.parent / "design"
_TOKENS_LIGHT = _DESIGN_DIR / "tokens_light.json"
_TOKENS_DARK = _DESIGN_DIR / "tokens_dark.json"


def is_dark_mode() -> bool:
    """macOS 시스템 Dark 모드 여부를 반환한다.

    Returns:
        Dark 모드이면 True
    """
    app = QApplication.instance()
    if not isinstance(app, QApplication):
        return False
    palette = app.palette()
    return bool(palette.color(QPalette.ColorRole.Window).lightness() < 128)


def _load_tokens(path: pathlib.Path) -> dict[str, Any]:
    """토큰 JSON 파일을 로드한다."""
    with open(path, encoding="utf-8") as f:
        result: dict[str, Any] = json.load(f)
        return result


class ThemeEngine:
    """디자인 토큰에서 QSS를 생성하는 테마 엔진.

    Args:
        tokens_path: 토큰 JSON 경로. None이면 시스템 Dark/Light 모드에 따라 자동 선택.
    """

    def __init__(self, tokens_path: pathlib.Path | None = None) -> None:
        if tokens_path is not None:
            self._tokens = _load_tokens(tokens_path)
        else:
            path = _TOKENS_DARK if is_dark_mode() else _TOKENS_LIGHT
            self._tokens = _load_tokens(path)

    @property
    def tokens(self) -> dict[str, Any]:
        """현재 로드된 토큰 딕셔너리."""
        return self._tokens

    def generate_overlay_qss(self) -> str:
        """오버레이 위젯 전용 QSS를 생성한다.

        Returns:
            오버레이 QLabel에 적용할 QSS 문자열
        """
        t = self._tokens
        bg = t["colors"]["background"]["overlay"]
        text_color = t["colors"]["text"]["overlay"]
        font_family = t["typography"]["fontFamily"]
        font_size = t["typography"]["fontSize"]["overlay"]
        radius = t["borderRadius"]["overlay"]
        padding = t["overlay"]["padding"]

        return (
            f"QLabel {{\n"
            f"    color: {text_color};\n"
            f"    font-family: {font_family};\n"
            f"    font-size: {font_size}px;\n"
            f"    padding: {padding}px;\n"
            f"    border-radius: {radius}px;\n"
            f"    background-color: {bg};\n"
            f"}}"
        )

    def generate_qss(self) -> str:
        """전체 앱 QSS를 생성한다.

        Returns:
            앱 전체에 적용할 QSS 문자열. P4에서 확장 예정.
        """
        t = self._tokens
        bg_primary = t["colors"]["background"]["primary"]
        text_primary = t["colors"]["text"]["primary"]
        bg_sidebar = t["colors"]["background"]["sidebar"]
        border = t["colors"]["border"]["default"]
        font_family = t["typography"]["fontFamily"]

        sidebar_cfg = t.get("sidebar", {})
        item_height = sidebar_cfg.get("itemHeight", 32)
        font_size_body = t["typography"]["fontSize"].get("body", 14)
        accent = t["colors"]["text"].get("accent", "#0071E3")
        text_secondary = t["colors"]["text"].get("secondary", "#6E6E73")

        return (
            f"QMainWindow {{\n"
            f"    background-color: {bg_primary};\n"
            f"    color: {text_primary};\n"
            f"    font-family: {font_family};\n"
            f"}}\n"
            f"QTreeView {{\n"
            f"    background-color: {bg_sidebar};\n"
            f"    border-right: 1px solid {border};\n"
            f"    font-size: {font_size_body}px;\n"
            f"    outline: none;\n"
            f"}}\n"
            f"QTreeView::item {{\n"
            f"    height: {item_height}px;\n"
            f"    padding-left: 8px;\n"
            f"}}\n"
            f"QTreeView::item:selected {{\n"
            f"    background-color: {accent};\n"
            f"    color: #FFFFFF;\n"
            f"}}\n"
            f"QStatusBar {{\n"
            f"    color: {text_secondary};\n"
            f"    font-size: 12px;\n"
            f"}}"
        )
