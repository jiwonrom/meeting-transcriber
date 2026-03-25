"""메인 윈도우 — 앱의 루트 QMainWindow."""
from __future__ import annotations

import json
import pathlib
import tempfile
from datetime import UTC, datetime
from typing import Any

import numpy as np
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QLabel,
    QMainWindow,
    QSplitter,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from meeting_transcriber.core.audio_capture import AudioCaptureWorker, encode_wav_chunk
from meeting_transcriber.core.transcriber import FileTranscriber, TranscriptionResult
from meeting_transcriber.storage.transcript_store import (
    create_transcript,
    load_transcript,
    save_transcript,
)
from meeting_transcriber.storage.workspace import WorkspaceManager
from meeting_transcriber.ui.sidebar import SidebarWidget
from meeting_transcriber.ui.theme import ThemeEngine
from meeting_transcriber.utils.config import load_settings
from meeting_transcriber.utils.constants import APP_NAME, APP_VERSION


class TranscriptViewer(QWidget):
    """transcript.json 내용을 표시하는 읽기 전용 뷰어."""

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        self._title_label = QLabel("")
        self._title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(self._title_label)

        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        layout.addWidget(self._text_edit)

    def display_transcript(self, path: str) -> None:
        """transcript.json 파일 내용을 표시한다.

        Args:
            path: transcript.json 파일 경로
        """
        try:
            transcript = load_transcript(pathlib.Path(path))
        except FileNotFoundError:
            self._title_label.setText("Error")
            self._text_edit.setPlainText(f"File not found: {path}")
            return
        except json.JSONDecodeError:
            self._title_label.setText("Error")
            self._text_edit.setPlainText(f"Invalid JSON: {path}")
            return
        except Exception as e:
            self._title_label.setText("Error")
            self._text_edit.setPlainText(f"Failed to load: {e}")
            return

        metadata = transcript.get("metadata", {})
        title = metadata.get("title", "Untitled")
        self._title_label.setText(title)

        segments = transcript.get("segments", [])
        lines: list[str] = []
        for seg in segments:
            text = seg.get("text", "")
            start = seg.get("start", 0.0)
            lines.append(f"[{start:.1f}s] {text}")

        self._text_edit.setPlainText("\n".join(lines))

    def clear(self) -> None:
        """뷰어 내용을 초기화한다."""
        self._title_label.setText("")
        self._text_edit.clear()


class EmptyStateWidget(QWidget):
    """transcript가 선택되지 않았을 때 표시하는 빈 상태 화면."""

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        label = QLabel("Select a transcript to view")
        label.setStyleSheet("color: #6E6E73; font-size: 16px;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)


class TranscriptionWorkerThread(QThread):
    """파일 전사를 별도 스레드에서 실행한다.

    FileTranscriber.transcribe_file()이 blocking이므로
    메인 스레드를 차단하지 않기 위해 QThread를 사용한다.
    """

    finished = pyqtSignal(object)  # TranscriptionResult or Exception
    progress = pyqtSignal(str)

    def __init__(
        self,
        audio_path: pathlib.Path,
        model_name: str = "small",
        language: str = "auto",
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._audio_path = audio_path
        self._model_name = model_name
        self._language = language

    def run(self) -> None:
        """전사를 실행한다."""
        try:
            self.progress.emit("Transcribing...")
            transcriber = FileTranscriber(
                model_name=self._model_name,
                language=self._language,
            )
            result = transcriber.transcribe_file(self._audio_path)
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit(e)


class MainWindow(QMainWindow):
    """Meeting Transcriber 메인 윈도우.

    왼쪽 사이드바 + 오른쪽 콘텐츠 영역으로 구성된다.
    녹음 시작/정지 및 전사 파이프라인을 관리한다.
    """

    caption_updated = pyqtSignal(str)
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()

    def __init__(
        self,
        workspace: WorkspaceManager | None = None,
        parent: Any = None,
    ) -> None:
        """MainWindow를 초기화한다.

        Args:
            workspace: WorkspaceManager 인스턴스. None이면 기본값 생성.
            parent: Qt 부모 위젯
        """
        super().__init__(parent)
        self._workspace = workspace or WorkspaceManager()
        self._theme = ThemeEngine()
        self._audio_worker: AudioCaptureWorker | None = None
        self._transcription_worker: TranscriptionWorkerThread | None = None
        self._is_recording = False

        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(800, 500)

        self._setup_ui()
        self._apply_theme()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """UI를 구성한다."""
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        self._sidebar = SidebarWidget(workspace=self._workspace)
        self._splitter.addWidget(self._sidebar)

        self._content_stack = QWidget()
        content_layout = QVBoxLayout(self._content_stack)
        content_layout.setContentsMargins(0, 0, 0, 0)

        self._empty_state = EmptyStateWidget()
        self._transcript_viewer = TranscriptViewer()
        self._transcript_viewer.hide()

        content_layout.addWidget(self._empty_state)
        content_layout.addWidget(self._transcript_viewer)

        self._splitter.addWidget(self._content_stack)
        self._splitter.setSizes([260, 540])

        self.setCentralWidget(self._splitter)

        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._update_status()

    def _apply_theme(self) -> None:
        """테마 QSS를 적용한다."""
        qss = self._theme.generate_qss()
        self.setStyleSheet(qss)

    def _connect_signals(self) -> None:
        """사이드바 signal을 연결한다."""
        self._sidebar.transcript_selected.connect(self._on_transcript_selected)
        self._sidebar.folder_selected.connect(self._on_folder_selected)
        self._sidebar.folder_created.connect(lambda _: self._update_status())
        self._sidebar.folder_deleted.connect(lambda _: self._update_status())

    # -- 녹음 제어 --

    def toggle_recording(self, start: bool) -> None:
        """녹음을 시작하거나 정지한다.

        Args:
            start: True이면 녹음 시작, False이면 정지
        """
        if start and not self._is_recording:
            self.start_recording()
        elif not start and self._is_recording:
            self.stop_recording()

    def start_recording(self) -> None:
        """녹음을 시작한다."""
        if self._is_recording:
            return

        settings = load_settings()
        device = settings.get("audio", {}).get("device")

        self._audio_worker = AudioCaptureWorker(device=device)
        self._audio_worker.capture_started.connect(self._on_capture_started)
        self._audio_worker.capture_stopped.connect(self._on_capture_stopped)
        self._audio_worker.error_occurred.connect(self._on_capture_error)
        self._audio_worker.start()

    def stop_recording(self) -> None:
        """녹음을 정지한다."""
        if not self._is_recording or self._audio_worker is None:
            return

        self._audio_worker.stop()

    def _on_capture_started(self) -> None:
        """녹음 시작 시 호출된다."""
        self._is_recording = True
        self._status_bar.showMessage("Recording...")
        self.recording_started.emit()

    def _on_capture_stopped(self) -> None:
        """녹음 정지 시 호출된다. 전사를 시작한다."""
        self._is_recording = False
        self._status_bar.showMessage("Processing recording...")
        self.recording_stopped.emit()

        if self._audio_worker is None:
            return

        recording = self._audio_worker.get_full_recording()
        self._audio_worker = None

        if len(recording) == 0:
            self._status_bar.showMessage("No audio recorded")
            return

        self._process_recording(recording)

    def _on_capture_error(self, message: str) -> None:
        """오디오 캡처 에러 시 호출된다."""
        self._is_recording = False
        self._status_bar.showMessage(f"Error: {message}")

    def _process_recording(self, recording: np.ndarray) -> None:
        """녹음 데이터를 WAV로 저장하고 전사를 시작한다."""
        wav_bytes = encode_wav_chunk(recording)
        temp_wav = pathlib.Path(tempfile.mktemp(suffix=".wav"))
        temp_wav.write_bytes(wav_bytes)

        settings = load_settings()
        model = settings.get("whisper_model", "small")
        language = settings.get("language", "auto")

        self._transcription_worker = TranscriptionWorkerThread(
            audio_path=temp_wav,
            model_name=model,
            language=language,
        )
        self._transcription_worker.progress.connect(
            lambda msg: self._status_bar.showMessage(msg)
        )
        self._transcription_worker.finished.connect(
            lambda result: self._on_transcription_done(result, temp_wav)
        )
        self._transcription_worker.start()

    def _on_transcription_done(
        self,
        result: TranscriptionResult | Exception,
        temp_wav: pathlib.Path,
    ) -> None:
        """전사 완료 시 호출된다."""
        # 임시 파일 정리
        temp_wav.unlink(missing_ok=True)
        self._transcription_worker = None

        if isinstance(result, Exception):
            self._status_bar.showMessage(f"Transcription failed: {result}")
            return

        # transcript 저장
        now = datetime.now(tz=UTC).strftime("%Y-%m-%d_%H%M%S")
        transcript = create_transcript(
            segments=result.segments,
            title=now,
            languages=[result.language],
            source="microphone",
            model=result.model,
            duration_seconds=result.duration_seconds,
        )

        folder = self._workspace.root / "Work" / now
        folder.mkdir(parents=True, exist_ok=True)
        save_transcript(transcript, folder / "transcript.json")

        self._sidebar.refresh()
        self._status_bar.showMessage(f"Saved: {now}")
        self._update_status()

        # 오버레이에 캡션 전달
        for seg in result.segments:
            self.caption_updated.emit(seg.get("text", ""))

    # -- UI 이벤트 --

    def _on_transcript_selected(self, path: str) -> None:
        """transcript 선택 시 뷰어에 표시한다."""
        self._empty_state.hide()
        self._transcript_viewer.show()
        self._transcript_viewer.display_transcript(path)

    def _on_folder_selected(self, path: str) -> None:
        """폴더 선택 시 상태바를 업데이트한다."""
        self._update_status(path)

    def _update_status(self, folder_path: str = "") -> None:
        """상태바를 업데이트한다."""
        if self._is_recording:
            return  # 녹음 중에는 상태바 변경하지 않음

        folders = self._workspace.list_folders()
        total = sum(f.transcript_count for f in folders)
        self._status_bar.showMessage(
            f"{len(folders)} folders, {total} transcripts"
        )

    @property
    def sidebar(self) -> SidebarWidget:
        """사이드바 위젯."""
        return self._sidebar

    @property
    def transcript_viewer(self) -> TranscriptViewer:
        """transcript 뷰어."""
        return self._transcript_viewer

    @property
    def splitter(self) -> QSplitter:
        """메인 스플리터."""
        return self._splitter

    def closeEvent(self, event: Any) -> None:  # noqa: N802
        """윈도우 닫기 시 녹음을 중지하고 설정을 저장한다."""
        if self._audio_worker is not None:
            self._audio_worker.stop()
        super().closeEvent(event)
