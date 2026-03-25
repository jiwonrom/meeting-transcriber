# Design Tokens

## 개요

디자인 토큰은 `design/tokens_light.json`과 `design/tokens_dark.json`에 정의된다.
`ui/theme.py`의 `ThemeEngine`이 JSON을 읽어 PyQt6 QSS 문자열을 생성한다.

## 토큰 → QSS 변환 방식

PyQt6의 QSS는 CSS 변수(`var()`)를 지원하지 않으므로,
Python f-string으로 QSS를 동적 생성한다.

```python
# ui/theme.py 예시
class ThemeEngine:
    def __init__(self, tokens_path: str):
        self.tokens = json.loads(Path(tokens_path).read_text())

    def generate_qss(self) -> str:
        t = self.tokens
        return f"""
        QMainWindow {{
            background-color: {t['colors']['background']['primary']};
            color: {t['colors']['text']['primary']};
        }}
        QTreeView {{
            background-color: {t['colors']['background']['sidebar']};
            border-right: 1px solid {t['colors']['border']['default']};
        }}
        """
```

## Dark/Light 모드 전환

macOS 시스템 설정을 감지하여 자동 전환:
```python
from PyQt6.QtWidgets import QApplication
palette = QApplication.palette()
is_dark = palette.color(palette.ColorRole.Window).lightness() < 128
```

## MCP 참조

개발 시 Design Systems MCP (`https://design-systems-mcp.southleft.com/mcp`)를 사용하여
WCAG 색상 대비, 접근성 기준 등을 조회할 수 있다.
Claude Code에서: "WCAG AA 대비 비율 확인해줘" 식으로 활용.
