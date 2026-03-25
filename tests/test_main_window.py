"""main_window 모듈 단위 테스트."""
from __future__ import annotations

import json
import pathlib

from PyQt6.QtWidgets import QSplitter

from meeting_transcriber.storage.workspace import WorkspaceManager
from meeting_transcriber.ui.main_window import MainWindow, TranscriptViewer


def test_main_window_creation(qtbot: object, tmp_path: pathlib.Path) -> None:
    """메인 윈도우가 정상 생성되는지 확인."""
    ws = WorkspaceManager(workspace_dir=tmp_path)
    window = MainWindow(workspace=ws)
    qtbot.addWidget(window)  # type: ignore[union-attr]

    assert window.windowTitle().startswith("Meeting Transcriber")


def test_main_window_has_sidebar(qtbot: object, tmp_path: pathlib.Path) -> None:
    """메인 윈도우에 사이드바가 존재하는지 확인."""
    ws = WorkspaceManager(workspace_dir=tmp_path)
    window = MainWindow(workspace=ws)
    qtbot.addWidget(window)  # type: ignore[union-attr]

    assert window.sidebar is not None


def test_main_window_has_splitter(qtbot: object, tmp_path: pathlib.Path) -> None:
    """스플리터 레이아웃이 구성되어 있는지 확인."""
    ws = WorkspaceManager(workspace_dir=tmp_path)
    window = MainWindow(workspace=ws)
    qtbot.addWidget(window)  # type: ignore[union-attr]

    splitter = window.splitter
    assert isinstance(splitter, QSplitter)
    assert splitter.count() == 2


def test_main_window_theme_applied(qtbot: object, tmp_path: pathlib.Path) -> None:
    """테마 QSS가 적용되어 있는지 확인."""
    ws = WorkspaceManager(workspace_dir=tmp_path)
    window = MainWindow(workspace=ws)
    qtbot.addWidget(window)  # type: ignore[union-attr]

    qss = window.styleSheet()
    assert "QMainWindow" in qss


def test_transcript_viewer_display(qtbot: object, tmp_path: pathlib.Path) -> None:
    """TranscriptViewer가 transcript 내용을 표시하는지 확인."""
    viewer = TranscriptViewer()
    qtbot.addWidget(viewer)  # type: ignore[union-attr]

    # transcript 파일 생성
    transcript_path = tmp_path / "test" / "transcript.json"
    transcript_path.parent.mkdir(parents=True)
    transcript_path.write_text(json.dumps({
        "version": "1.0",
        "metadata": {"title": "Test Meeting"},
        "segments": [
            {"start": 0.0, "end": 2.5, "text": "Hello world"}
        ],
    }))

    viewer.display_transcript(str(transcript_path))
    assert "Test Meeting" in viewer._title_label.text()
    assert "Hello world" in viewer._text_edit.toPlainText()


def test_transcript_viewer_clear(qtbot: object) -> None:
    """TranscriptViewer의 clear가 동작하는지 확인."""
    viewer = TranscriptViewer()
    qtbot.addWidget(viewer)  # type: ignore[union-attr]

    viewer._title_label.setText("Something")
    viewer._text_edit.setPlainText("Content")
    viewer.clear()

    assert viewer._title_label.text() == ""
    assert viewer._text_edit.toPlainText() == ""


def test_transcript_viewer_invalid_path(qtbot: object) -> None:
    """존재하지 않는 파일 표시 시 에러 메시지를 보여주는지 확인."""
    viewer = TranscriptViewer()
    qtbot.addWidget(viewer)  # type: ignore[union-attr]

    viewer.display_transcript("/nonexistent/path.json")
    assert "Error" in viewer._title_label.text()
