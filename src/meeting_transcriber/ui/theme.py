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
    """macOS 시스템 Dark 모드 여부를 반환한다."""
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
    """디자인 토큰에서 QSS를 생성하는 테마 엔진."""

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
        """오버레이 위젯 전용 QSS."""
        t = self._tokens
        bg = t["colors"]["background"]["overlay"]
        text_color = t["colors"]["text"]["overlay"]
        font = t["typography"]["fontFamily"]
        size = t["typography"]["fontSize"]["overlay"]
        radius = t["borderRadius"]["overlay"]
        pad = t["overlay"]["padding"]

        return (
            f"QLabel {{\n"
            f"    color: {text_color};\n"
            f"    font-family: {font};\n"
            f"    font-size: {size}px;\n"
            f"    padding: {pad}px;\n"
            f"    border-radius: {radius}px;\n"
            f"    background-color: {bg};\n"
            f"}}"
        )

    def generate_qss(self) -> str:
        """전체 앱 QSS를 토큰에서 생성한다."""
        t = self._tokens
        c = t["colors"]
        bg = c["background"]
        tx = c["text"]
        bd = c["border"]
        st = c["status"]
        font = t["typography"]["fontFamily"]
        fs = t["typography"]["fontSize"]
        sp = t["spacing"]
        rad = t["borderRadius"]

        return (
            # 메인 윈도우
            f"QMainWindow {{\n"
            f"    background-color: {bg['primary']};\n"
            f"    color: {tx['primary']};\n"
            f"    font-family: {font};\n"
            f"    font-size: {fs['body']}px;\n"
            f"}}\n\n"
            # 사이드바 (같은 배경 + 미묘한 보더)
            f"QListWidget {{\n"
            f"    background-color: {bg['sidebar']};\n"
            f"    border: none;\n"
            f"    border-right: 1px solid {bd['default']};\n"
            f"    font-size: {fs['body']}px;\n"
            f"    outline: none;\n"
            f"}}\n"
            f"QListWidget::item {{\n"
            f"    border-bottom: 1px solid {bd['default']};\n"
            f"    padding: {sp['sm']}px;\n"
            f"}}\n"
            f"QListWidget::item:selected {{\n"
            f"    background-color: {bg['elevated']};\n"
            f"    border-left: 3px solid {st['recording']};\n"
            f"}}\n\n"
            # 탭 위젯
            f"QTabWidget::pane {{\n"
            f"    border: 1px solid {bd['default']};\n"
            f"    border-radius: {rad['sm']}px;\n"
            f"    background-color: {bg['primary']};\n"
            f"}}\n"
            f"QTabBar::tab {{\n"
            f"    background-color: transparent;\n"
            f"    color: {tx['secondary']};\n"
            f"    padding: {sp['sm']}px {sp['md']}px;\n"
            f"    border: none;\n"
            f"    font-size: {fs['caption']}px;\n"
            f"}}\n"
            f"QTabBar::tab:selected {{\n"
            f"    color: {tx['primary']};\n"
            f"    border-bottom: 2px solid {st['recording']};\n"
            f"}}\n\n"
            # 텍스트 에디터
            f"QTextEdit {{\n"
            f"    background-color: {bg['primary']};\n"
            f"    color: {tx['primary']};\n"
            f"    border: none;\n"
            f"    font-size: {fs['body']}px;\n"
            f"    selection-background-color: {bd['emphasis']};\n"
            f"}}\n\n"
            # 버튼
            f"QPushButton {{\n"
            f"    background-color: {bg['control']};\n"
            f"    color: {tx['primary']};\n"
            f"    border: 1px solid {bd['default']};\n"
            f"    border-radius: {rad['sm']}px;\n"
            f"    padding: {sp['sm']}px {sp['md']}px;\n"
            f"    font-size: {fs['caption']}px;\n"
            f"}}\n"
            f"QPushButton:hover {{\n"
            f"    border-color: {bd['emphasis']};\n"
            f"}}\n"
            f"QPushButton:pressed {{\n"
            f"    background-color: {bg['elevated']};\n"
            f"}}\n\n"
            # 스크롤바
            f"QScrollBar:vertical {{\n"
            f"    background: transparent;\n"
            f"    width: 6px;\n"
            f"}}\n"
            f"QScrollBar::handle:vertical {{\n"
            f"    background: {bd['emphasis']};\n"
            f"    border-radius: 3px;\n"
            f"    min-height: 20px;\n"
            f"}}\n"
            f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{\n"
            f"    height: 0px;\n"
            f"}}\n\n"
            # 상태바
            f"QStatusBar {{\n"
            f"    color: {tx['tertiary']};\n"
            f"    font-size: {fs['caption']}px;\n"
            f"    border-top: 1px solid {bd['default']};\n"
            f"}}\n\n"
            # 라벨
            f"QLabel {{\n"
            f"    color: {tx['primary']};\n"
            f"}}\n"
            f"QLabel#caption {{\n"
            f"    color: {tx['secondary']};\n"
            f"    font-size: {fs['caption']}px;\n"
            f"}}\n"
            f"QLabel#accent {{\n"
            f"    color: {tx['accent']};\n"
            f"    font-size: {fs['body']}px;\n"
            f"    padding: {sp['sm']}px;\n"
            f"}}\n\n"
            # 상태 라벨 (동적 property 기반)
            f'QLabel[state="recording"] {{\n'
            f"    color: {st['recording']};\n"
            f"    font-weight: bold;\n"
            f"}}\n"
            f'QLabel[state="processing"] {{\n'
            f"    color: {st['processing']};\n"
            f"}}\n"
            f'QLabel[state="error"] {{\n'
            f"    color: {st['error']};\n"
            f"}}\n"
            f'QLabel[state="idle"] {{\n'
            f"    color: {tx['secondary']};\n"
            f"}}\n\n"
            # 프로그레스바 (레벨 미터)
            f"QProgressBar {{\n"
            f"    background: {bg['control']};\n"
            f"    border: none;\n"
            f"    border-radius: 2px;\n"
            f"    max-height: 4px;\n"
            f"}}\n"
            f"QProgressBar::chunk {{\n"
            f"    background: {st['recording']};\n"
            f"    border-radius: 2px;\n"
            f"}}\n"
            # System audio level bar (orange chunks)
            f"QProgressBar#system_level_bar {{\n"
            f"    background-color: {bg['control']};\n"
            f"    border: none;\n"
            f"    border-radius: 2px;\n"
            f"}}\n"
            f"QProgressBar#system_level_bar::chunk {{\n"
            f"    background-color: {st['processing']};\n"
            f"    border-radius: 2px;\n"
            f"}}\n\n"
            # Heading labels (wizard, dialogs)
            f"QLabel#heading {{\n"
            f"    font-size: {fs['heading']}px;\n"
            f"    font-weight: 600;\n"
            f"}}\n\n"
            # Step indicator
            f"QLabel#step_indicator {{\n"
            f"    font-size: {fs['caption']}px;\n"
            f"    color: {tx['secondary']};\n"
            f"}}\n\n"
            # Monospace labels
            f"QLabel#mono {{\n"
            f"    font-family: {t['typography']['fontMono']};\n"
            f"    font-size: {fs['body']}px;\n"
            f"}}\n\n"
            # Install cards (wizard)
            f"QFrame#install_card {{\n"
            f"    border: 1px solid {bd['default']};\n"
            f"    border-radius: {rad['sm']}px;\n"
            f"    padding: {sp['md']}px;\n"
            f"}}\n\n"
            # Dynamic status labels
            f'QLabel[status="waiting"] {{\n'
            f"    font-size: {fs['caption']}px;\n"
            f"    color: {tx['tertiary']};\n"
            f"}}\n"
            f'QLabel[status="success"] {{\n'
            f"    font-size: {fs['caption']}px;\n"
            f"    color: {st['success']};\n"
            f"    font-weight: 600;\n"
            f"}}\n"
            f'QLabel[status="info"] {{\n'
            f"    font-size: {fs['body']}px;\n"
            f"    color: {tx['secondary']};\n"
            f"}}\n"
            f'QLabel[status="info_success"] {{\n'
            f"    font-size: {fs['body']}px;\n"
            f"    color: {st['success']};\n"
            f"}}\n"
            f'QLabel[status="info_error"] {{\n'
            f"    font-size: {fs['body']}px;\n"
            f"    color: {st['error']};\n"
            f"}}\n\n"
            # System audio label accent state during recording
            f'QLabel#system_audio_label[state="recording"] {{\n'
            f"    color: {tx['accent']};\n"
            f"    font-size: {fs['caption']}px;\n"
            f"}}\n"
            f'QLabel#system_audio_label[state="idle"] {{\n'
            f"    color: {tx['secondary']};\n"
            f"    font-size: {fs['caption']}px;\n"
            f"}}\n\n"
            # 템플릿 콤보 (컨트롤바)
            f"QComboBox#template_combo {{\n"
            f"    background: {bg['control']};\n"
            f"    color: {tx['primary']};\n"
            f"    border: 1px solid {bd['default']};\n"
            f"    border-radius: 6px;\n"
            f"    padding: 4px 8px;\n"
            f"    font-size: {fs['body']}px;\n"
            f"    min-width: 140px;\n"
            f"    max-width: 140px;\n"
            f"    max-height: 36px;\n"
            f"}}\n"
            f"QComboBox#template_combo::drop-down {{\n"
            f"    border: none;\n"
            f"    width: 20px;\n"
            f"}}\n"
            f"QComboBox#template_combo QAbstractItemView {{\n"
            f"    background: {bg['elevated']};\n"
            f"    color: {tx['primary']};\n"
            f"    border: 1px solid {bd['emphasis']};\n"
            f"    border-radius: 6px;\n"
            f"    selection-background-color: {bg['control']};\n"
            f"}}\n\n"
            # Re-run AI 템플릿 콤보 (Summary 탭)
            f"QComboBox#rerun_template_combo {{\n"
            f"    background: {bg['control']};\n"
            f"    color: {tx['primary']};\n"
            f"    border: 1px solid {bd['default']};\n"
            f"    border-radius: 6px;\n"
            f"    padding: 4px 8px;\n"
            f"    font-size: {fs['body']}px;\n"
            f"    min-width: 140px;\n"
            f"    max-width: 140px;\n"
            f"    max-height: 36px;\n"
            f"}}\n"
            f"QComboBox#rerun_template_combo::drop-down {{\n"
            f"    border: none;\n"
            f"    width: 20px;\n"
            f"}}\n"
            f"QComboBox#rerun_template_combo QAbstractItemView {{\n"
            f"    background: {bg['elevated']};\n"
            f"    color: {tx['primary']};\n"
            f"    border: 1px solid {bd['emphasis']};\n"
            f"    border-radius: 6px;\n"
            f"    selection-background-color: {bg['control']};\n"
            f"}}\n\n"
            # Re-run AI 버튼
            f"QPushButton#rerun_ai_btn {{\n"
            f"    background: {bg['control']};\n"
            f"    color: {tx['primary']};\n"
            f"    border: 1px solid {bd['default']};\n"
            f"    border-radius: 6px;\n"
            f"    padding: 4px 12px;\n"
            f"    font-size: {fs['body']}px;\n"
            f"    min-width: 120px;\n"
            f"}}\n"
            f"QPushButton#rerun_ai_btn:hover {{\n"
            f"    border-color: {bd['emphasis']};\n"
            f"}}\n"
            f"QPushButton#rerun_ai_btn:disabled {{\n"
            f"    color: {tx['muted']};\n"
            f"    opacity: 0.5;\n"
            f"}}\n"
        )
