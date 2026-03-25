"""메인 윈도우 — Apple Voice Memos 스타일 UI."""
from __future__ import annotations

import json
import pathlib
import tempfile
from datetime import UTC, datetime
from typing import Any

import numpy as np
from PyQt6.QtCore import QSize, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
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
from meeting_transcriber.ui.theme import ThemeEngine
from meeting_transcriber.utils.config import load_settings
from meeting_transcriber.utils.constants import APP_NAME

# ============================================================
# 녹음 버튼 (큰 원형, Voice Memos 스타일)
# ============================================================


class RecordButton(QPushButton):
    """원형 녹음 버튼 — 빨간 원(대기) / 빨간 정사각형(녹음 중)."""

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._recording = False
        self.setFixedSize(64, 64)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("border: none; background: transparent;")

    def set_recording(self, recording: bool) -> None:
        """녹음 상태를 설정한다."""
        self._recording = recording
        self.update()

    def paintEvent(self, event: Any) -> None:  # noqa: N802
        """원형/사각형 녹음 아이콘을 그린다."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        red = QColor("#FF453A")  # status.recording
        painter.setBrush(red)
        painter.setPen(Qt.PenStyle.NoPen)

        if self._recording:
            # 정지 아이콘: 둥근 사각형
            size = 22
            x = (self.width() - size) // 2
            y = (self.height() - size) // 2
            path = QPainterPath()
            path.addRoundedRect(float(x), float(y), float(size), float(size), 4.0, 4.0)
            painter.fillPath(path, red)
        else:
            # 녹음 아이콘: 큰 원
            size = 48
            x = (self.width() - size) // 2
            y = (self.height() - size) // 2
            painter.drawEllipse(x, y, size, size)

        # 외부 링
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QColor(255, 255, 255, 38))  # border.emphasis rgba
        ring_size = 60
        rx = (self.width() - ring_size) // 2
        ry = (self.height() - ring_size) // 2
        painter.drawEllipse(rx, ry, ring_size, ring_size)

        painter.end()


# ============================================================
# 녹음 리스트 아이템
# ============================================================


class RecordingListItem(QWidget):
    """사이드바 녹음 항목 — 제목, 날짜, 길이."""

    def __init__(self, title: str, date: str, duration: str, parent: Any = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(2)

        self._title = QLabel(title)
        self._title.setFont(QFont("", 14, QFont.Weight.Medium))
        layout.addWidget(self._title)

        info = QHBoxLayout()
        info.setSpacing(8)
        self._date = QLabel(date)
        self._date.setObjectName("caption")
        info.addWidget(self._date)

        self._duration = QLabel(duration)
        self._duration.setObjectName("caption")
        info.addWidget(self._duration)
        info.addStretch()

        layout.addLayout(info)


# ============================================================
# Transcript 뷰어
# ============================================================


class TranscriptViewer(QWidget):
    """transcript.json 내용을 3탭(원본/교열/요약)으로 표시하는 뷰어."""

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._current_path: str = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # 제목 + 메타
        self._title_label = QLabel("")
        self._title_label.setFont(QFont("", 18, QFont.Weight.Bold))
        layout.addWidget(self._title_label)

        self._meta_label = QLabel("")
        self._meta_label.setObjectName("caption")
        layout.addWidget(self._meta_label)

        # 3탭
        self._tabs = QTabWidget()
        edit_style = "border: none; font-size: 14px;"

        # Tab 0: 원본
        self._original_edit = QTextEdit()
        self._original_edit.setReadOnly(True)
        self._original_edit.setStyleSheet(edit_style)
        self._tabs.addTab(self._original_edit, "Original")

        # Tab 1: 교열
        proofread_widget = QWidget()
        proof_layout = QVBoxLayout(proofread_widget)
        proof_layout.setContentsMargins(0, 0, 0, 0)
        self._proofread_edit = QTextEdit()
        self._proofread_edit.setStyleSheet(edit_style)
        proof_layout.addWidget(self._proofread_edit)

        save_btn = QPushButton("Save Proofread")
        save_btn.setFixedWidth(140)
        save_btn.clicked.connect(self._save_proofread)
        proof_layout.addWidget(save_btn)
        self._tabs.addTab(proofread_widget, "Proofread")

        # Tab 2: 요약
        summary_widget = QWidget()
        summary_layout = QVBoxLayout(summary_widget)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        self._summary_edit = QTextEdit()
        self._summary_edit.setReadOnly(True)
        self._summary_edit.setStyleSheet(edit_style)
        summary_layout.addWidget(self._summary_edit)

        self._keywords_label = QLabel("")
        self._keywords_label.setWordWrap(True)
        self._keywords_label.setObjectName("accent")
        summary_layout.addWidget(self._keywords_label)
        self._tabs.addTab(summary_widget, "Summary")

        layout.addWidget(self._tabs)

    def display_transcript(self, path: str) -> None:
        """transcript.json 파일을 3탭에 표시한다."""
        self._current_path = path

        try:
            transcript = load_transcript(pathlib.Path(path))
        except FileNotFoundError:
            self._title_label.setText("Error")
            self._original_edit.setPlainText(f"File not found: {path}")
            return
        except json.JSONDecodeError:
            self._title_label.setText("Error")
            self._original_edit.setPlainText(f"Invalid JSON: {path}")
            return
        except Exception as e:
            self._title_label.setText("Error")
            self._original_edit.setPlainText(f"Failed to load: {e}")
            return

        metadata = transcript.get("metadata", {})
        self._title_label.setText(metadata.get("title", "Untitled"))

        duration = metadata.get("duration_seconds", 0)
        langs = ", ".join(metadata.get("languages", []))
        self._meta_label.setText(f"{_fmt_duration(duration)}  {langs}")

        # Tab 0: 원본 세그먼트
        segments = transcript.get("segments", [])
        lines = [seg.get("text", "") for seg in segments if seg.get("text")]
        self._original_edit.setPlainText("\n".join(lines))

        # Tab 1: 교열
        proofread = metadata.get("proofread", "")
        self._proofread_edit.setPlainText(
            proofread if proofread else "(AI processing required — set Gemini API key in Settings)"
        )
        self._proofread_edit.setReadOnly(not bool(proofread))

        # Tab 2: 요약 + 키워드
        summary = metadata.get("summary", "")
        self._summary_edit.setPlainText(
            summary if summary else "(No summary available)"
        )

        tags = metadata.get("tags", [])
        if tags:
            self._keywords_label.setText("Keywords: " + ", ".join(tags))
        else:
            self._keywords_label.setText("")

    def _save_proofread(self) -> None:
        """교열 텍스트를 transcript.json에 저장한다."""
        if not self._current_path:
            return

        try:
            transcript = load_transcript(pathlib.Path(self._current_path))
            transcript.setdefault("metadata", {})["proofread"] = (
                self._proofread_edit.toPlainText()
            )
            save_transcript(transcript, pathlib.Path(self._current_path))
        except Exception:
            pass  # 저장 실패 무시 (상태바에서 알림은 MainWindow 담당)

    def clear(self) -> None:
        """뷰어 내용을 초기화한다."""
        self._current_path = ""
        self._title_label.setText("")
        self._meta_label.setText("")
        self._original_edit.clear()
        self._proofread_edit.clear()
        self._summary_edit.clear()
        self._keywords_label.setText("")


# ============================================================
# 빈 상태 화면
# ============================================================


class EmptyStateWidget(QWidget):
    """녹음이 선택되지 않았을 때 표시."""

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        label = QLabel("Select a recording to view\nor press the record button to start")
        label.setObjectName("caption")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)


# ============================================================
# 전사 워커 스레드
# ============================================================


class TranscriptionWorkerThread(QThread):
    """파일 전사를 별도 스레드에서 실행한다."""

    finished = pyqtSignal(object)
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


class ChunkTranscriberThread(QThread):
    """2초 오디오 청크를 실시간 전사하는 워커.

    청크가 도착할 때마다 WAV로 변환 → whisper-cli → 텍스트 emit.
    """

    text_ready = pyqtSignal(str, list)  # (text, segments)

    def __init__(
        self,
        chunk: np.ndarray,
        model_name: str = "small",
        language: str = "auto",
        time_offset: float = 0.0,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._chunk = chunk
        self._model_name = model_name
        self._language = language
        self._time_offset = time_offset

    def run(self) -> None:
        """청크를 전사한다."""
        try:
            wav_bytes = encode_wav_chunk(self._chunk)
            temp_wav = pathlib.Path(tempfile.mktemp(suffix=".wav"))
            temp_wav.write_bytes(wav_bytes)

            transcriber = FileTranscriber(
                model_name=self._model_name,
                language=self._language,
            )
            result = transcriber.transcribe_file(temp_wav)
            temp_wav.unlink(missing_ok=True)

            # 시간 오프셋 보정
            segments = []
            for seg in result.segments:
                adjusted = dict(seg)
                adjusted["start"] += self._time_offset
                adjusted["end"] += self._time_offset
                segments.append(adjusted)

            text = " ".join(s["text"] for s in segments)
            if text.strip():
                self.text_ready.emit(text.strip(), segments)
        except Exception:
            pass  # 실시간 전사 실패는 무시 (최종 전사에서 복구)


# ============================================================
# 메인 윈도우
# ============================================================


class MainWindow(QMainWindow):
    """Meeting Transcriber 메인 윈도우 — Voice Memos 스타일."""

    caption_updated = pyqtSignal(str)
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()

    def __init__(
        self,
        workspace: WorkspaceManager | None = None,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._workspace = workspace or WorkspaceManager()
        self._theme = ThemeEngine()
        self._audio_worker: AudioCaptureWorker | None = None
        self._transcription_worker: TranscriptionWorkerThread | None = None
        self._ai_worker: Any = None
        self._chunk_workers: list[ChunkTranscriberThread] = []
        self._realtime_segments: list[dict[str, Any]] = []
        self._chunk_count = 0
        self._is_recording = False

        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(800, 520)

        self._setup_ui()
        self._apply_theme()
        self._connect_signals()
        self._refresh_recording_list()

    def _setup_ui(self) -> None:
        """Voice Memos 스타일 UI를 구성한다."""
        central = QWidget()
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 상단: 스플리터 (사이드바 | 콘텐츠)
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        # 왼쪽: 녹음 리스트
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        sidebar_header = QLabel("  Recordings")
        sidebar_header.setFont(QFont("", 13, QFont.Weight.Bold))
        sidebar_header.setFixedHeight(40)
        sidebar_header.setStyleSheet("padding-left: 16px;")
        sidebar_layout.addWidget(sidebar_header)

        self._recording_list = QListWidget()
        # 스타일은 ThemeEngine QSS에서 적용
        self._recording_list.currentItemChanged.connect(self._on_recording_selected)
        sidebar_layout.addWidget(self._recording_list)

        self._splitter.addWidget(sidebar)

        # 오른쪽: 콘텐츠
        self._content_stack = QWidget()
        content_layout = QVBoxLayout(self._content_stack)
        content_layout.setContentsMargins(0, 0, 0, 0)

        self._empty_state = EmptyStateWidget()
        self._transcript_viewer = TranscriptViewer()
        self._transcript_viewer.hide()

        content_layout.addWidget(self._empty_state)
        content_layout.addWidget(self._transcript_viewer)

        self._splitter.addWidget(self._content_stack)
        self._splitter.setSizes([280, 520])

        main_layout.addWidget(self._splitter, 1)

        # 하단: 녹음 컨트롤 바
        self._control_bar = QWidget()
        self._control_bar.setFixedHeight(90)
        bar_layout = QVBoxLayout(self._control_bar)
        bar_layout.setContentsMargins(0, 8, 0, 8)
        bar_layout.setSpacing(4)

        # 레벨 바
        self._level_bar = QProgressBar()
        self._level_bar.setRange(0, 100)
        self._level_bar.setValue(0)
        self._level_bar.setTextVisible(False)
        self._level_bar.setFixedHeight(4)
        # 레벨 바 스타일은 ThemeEngine QSS에서 적용
        bar_layout.addWidget(self._level_bar)

        # 버튼 + 타이머
        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_row.setSpacing(16)

        self._duration_label = QLabel("00:00")
        self._duration_label.setFixedWidth(60)
        self._duration_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._duration_label.setObjectName("caption")
        btn_row.addWidget(self._duration_label)

        self._record_btn = RecordButton()
        self._record_btn.clicked.connect(self._on_record_btn_clicked)
        btn_row.addWidget(self._record_btn)

        self._status_label = QLabel("Tap to Record")
        self._status_label.setFixedWidth(120)
        self._status_label.setObjectName("caption")
        btn_row.addWidget(self._status_label)

        bar_layout.addLayout(btn_row)

        main_layout.addWidget(self._control_bar)

        self.setCentralWidget(central)

        # 녹음 타이머
        self._record_seconds = 0
        self._record_timer = QTimer()
        self._record_timer.setInterval(1000)
        self._record_timer.timeout.connect(self._tick_duration)

        # 상태바
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

    def _set_status_state(self, state: str) -> None:
        """상태 라벨의 동적 스타일 프로퍼티를 설정하고 QSS를 갱신한다."""
        self._status_label.setProperty("state", state)
        style = self._status_label.style()
        if style is not None:
            style.unpolish(self._status_label)
            style.polish(self._status_label)

    def _apply_theme(self) -> None:
        """테마를 적용한다."""
        qss = self._theme.generate_qss()
        self.setStyleSheet(qss)

    def _connect_signals(self) -> None:
        """내부 signal을 연결한다."""
        pass  # 외부 연결은 app.py에서 수행

    # -- 녹음 리스트 --

    def _refresh_recording_list(self) -> None:
        """사이드바 녹음 목록을 갱신한다."""
        self._recording_list.clear()
        folders = self._workspace.list_folders()

        for folder in folders:
            transcripts = self._workspace.list_transcripts(folder.name)
            for t_path in transcripts:
                try:
                    transcript = load_transcript(t_path)
                except Exception:
                    continue

                meta = transcript.get("metadata", {})
                title = meta.get("title", t_path.parent.name)
                duration = _fmt_duration(meta.get("duration_seconds", 0))
                created = meta.get("created_at", "")[:10]

                item = QListWidgetItem()
                item.setData(Qt.ItemDataRole.UserRole, str(t_path))
                item.setSizeHint(QSize(0, 56))

                widget = RecordingListItem(title, created, duration)
                self._recording_list.addItem(item)
                self._recording_list.setItemWidget(item, widget)

    def _on_recording_selected(
        self, current: QListWidgetItem | None, previous: QListWidgetItem | None
    ) -> None:
        """녹음 항목 선택 시 뷰어에 표시한다."""
        if current is None:
            return
        path = current.data(Qt.ItemDataRole.UserRole)
        if path:
            self._empty_state.hide()
            self._transcript_viewer.show()
            self._transcript_viewer.display_transcript(path)

    # -- 녹음 컨트롤 --

    def _on_record_btn_clicked(self) -> None:
        """녹음 버튼 클릭."""
        self.toggle_recording(not self._is_recording)

    def _tick_duration(self) -> None:
        """1초마다 녹음 시간 갱신."""
        self._record_seconds += 1
        m = self._record_seconds // 60
        s = self._record_seconds % 60
        self._duration_label.setText(f"{m:02d}:{s:02d}")

    def toggle_recording(self, start: bool) -> None:
        """녹음을 시작하거나 정지한다."""
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

        self._realtime_segments = []
        self._chunk_count = 0
        self._chunk_workers = []

        self._audio_worker = AudioCaptureWorker(device=device)
        self._audio_worker.capture_started.connect(self._on_capture_started)
        self._audio_worker.capture_stopped.connect(self._on_capture_stopped)
        self._audio_worker.error_occurred.connect(self._on_capture_error)
        self._audio_worker.level_changed.connect(self._on_level_changed)
        self._audio_worker.chunk_ready.connect(self._on_chunk_ready)
        self._audio_worker.start()

    def stop_recording(self) -> None:
        """녹음을 정지한다."""
        if not self._is_recording or self._audio_worker is None:
            return
        self._audio_worker.stop()

    def _on_capture_started(self) -> None:
        """녹음 시작됨."""
        self._is_recording = True
        self._record_btn.set_recording(True)
        self._record_seconds = 0
        self._duration_label.setText("00:00")
        self._status_label.setText("Recording...")
        self._set_status_state( "recording")
        self._record_timer.start()
        self._status_bar.showMessage("Recording...")
        self.recording_started.emit()

    def _on_capture_stopped(self) -> None:
        """녹음 정지됨 — 전사를 시작한다."""
        self._is_recording = False
        self._record_btn.set_recording(False)
        self._record_timer.stop()
        self._level_bar.setValue(0)
        self._status_label.setText("Processing...")
        self._set_status_state( "processing")
        self._status_bar.showMessage("Processing recording...")
        self.recording_stopped.emit()

        if self._audio_worker is None:
            return

        recording = self._audio_worker.get_full_recording()
        self._audio_worker = None

        if len(recording) == 0:
            self._status_label.setText("Tap to Record")
            self._set_status_state( "idle")
            self._status_bar.showMessage("No audio recorded")
            return

        self._process_recording(recording)

    def _on_capture_error(self, message: str) -> None:
        """캡처 에러."""
        self._is_recording = False
        self._record_btn.set_recording(False)
        self._record_timer.stop()
        self._level_bar.setValue(0)
        self._status_label.setText("Error")
        self._set_status_state( "error")
        self._status_bar.showMessage(f"Error: {message}")

    def _on_level_changed(self, level: float) -> None:
        """오디오 레벨 업데이트."""
        self._level_bar.setValue(int(level * 100))

    def _on_chunk_ready(self, chunk: np.ndarray) -> None:
        """2초 오디오 청크 도착 — 실시간 전사를 시작한다.

        최대 2개 워커만 동시 실행하여 리소스 누수를 방지한다.
        """
        # 완료된 워커 정리
        self._chunk_workers = [w for w in self._chunk_workers if w.isRunning()]

        # 최대 2개 동시 워커 제한 — 초과 시 건너뜀
        if len(self._chunk_workers) >= 2:
            return

        settings = load_settings()
        model = settings.get("whisper_model", "small")
        language = settings.get("language", "auto")
        time_offset = self._chunk_count * 2.0
        self._chunk_count += 1

        worker = ChunkTranscriberThread(
            chunk=chunk,
            model_name=model,
            language=language,
            time_offset=time_offset,
        )
        worker.text_ready.connect(self._on_realtime_text)
        self._chunk_workers.append(worker)
        worker.start()

    def _on_realtime_text(self, text: str, segments: list[dict[str, Any]]) -> None:
        """실시간 전사 텍스트가 도착했을 때 오버레이에 표시한다."""
        self._realtime_segments.extend(segments)
        self.caption_updated.emit(text)

    def _process_recording(self, recording: np.ndarray) -> None:
        """녹음을 WAV로 저장하고 전사를 시작한다."""
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
        """전사 완료."""
        temp_wav.unlink(missing_ok=True)
        self._transcription_worker = None

        if isinstance(result, Exception):
            self._status_label.setText("Tap to Record")
            self._set_status_state( "idle")
            self._status_bar.showMessage(f"Transcription failed: {result}")
            return

        now = datetime.now(tz=UTC).strftime("%Y-%m-%d_%H%M%S")

        # 제목: 전사 첫 문장의 앞 40자 (없으면 타임스탬프)
        first_text = ""
        if result.segments:
            first_text = result.segments[0].get("text", "").strip()[:40]
        title = f"{now}_{first_text}" if first_text else now
        # 폴더명에 사용할 수 없는 문자 제거
        safe_title = "".join(c for c in title if c not in r'\/:*?"<>|')

        transcript = create_transcript(
            segments=result.segments,
            title=safe_title,
            languages=[result.language],
            source="microphone",
            model=result.model,
            duration_seconds=result.duration_seconds,
        )

        folder = self._workspace.root / "Work" / safe_title
        folder.mkdir(parents=True, exist_ok=True)
        save_transcript(transcript, folder / "transcript.json")

        self._refresh_recording_list()
        self._status_label.setText("Tap to Record")
        self._set_status_state( "idle")
        self._status_bar.showMessage(f"Saved: {now}")

        for seg in result.segments:
            self.caption_updated.emit(seg.get("text", ""))

        # AI 처리 (API 키가 있을 때만)
        self._run_ai_tasks(result, folder / "transcript.json")

    # -- AI 처리 --

    def _run_ai_tasks(
        self, result: TranscriptionResult, transcript_path: pathlib.Path
    ) -> None:
        """전사 결과에 AI 처리(교열, 요약, 키워드, 제목)를 실행한다."""
        from meeting_transcriber.utils.keychain import get_api_key

        api_key = get_api_key("gemini")
        if not api_key:
            return  # API 키 없으면 건너뜀

        full_text = " ".join(s.get("text", "") for s in result.segments)
        if not full_text.strip():
            return

        try:
            from meeting_transcriber.ai.gemini_provider import GeminiProvider
            from meeting_transcriber.ai.tasks import AITaskWorker

            provider = GeminiProvider(api_key=api_key)
            self._ai_worker = AITaskWorker(
                provider=provider,
                text=full_text,
                language=result.language,
            )
            self._ai_worker.progress.connect(
                lambda msg: self._status_bar.showMessage(msg)
            )
            self._ai_worker.finished.connect(
                lambda ai_result: self._on_ai_done(ai_result, transcript_path)
            )
            self._ai_worker.start()
        except Exception as e:
            self._status_bar.showMessage(f"AI processing skipped: {e}")

    def _on_ai_done(self, ai_result: Any, transcript_path: pathlib.Path) -> None:
        """AI 처리 완료 — 결과를 transcript에 저장한다."""
        self._ai_worker = None

        try:
            transcript = load_transcript(transcript_path)
            metadata = transcript.setdefault("metadata", {})

            if ai_result.summary:
                metadata["summary"] = ai_result.summary
            if ai_result.proofread_text:
                metadata["proofread"] = ai_result.proofread_text
            if ai_result.keywords:
                metadata["tags"] = ai_result.keywords
            if ai_result.title:
                metadata["title"] = ai_result.title

            save_transcript(transcript, transcript_path)
            self._refresh_recording_list()
            self._status_bar.showMessage("AI processing complete")
        except Exception as e:
            self._status_bar.showMessage(f"AI save failed: {e}")

    # -- 프로퍼티 --

    @property
    def is_recording(self) -> bool:
        """현재 녹음 중인지 반환한다."""
        return self._is_recording

    @property
    def sidebar(self) -> QListWidget:
        """녹음 리스트 위젯."""
        return self._recording_list

    @property
    def transcript_viewer(self) -> TranscriptViewer:
        """transcript 뷰어."""
        return self._transcript_viewer

    @property
    def splitter(self) -> QSplitter:
        """메인 스플리터."""
        return self._splitter

    @property
    def record_button(self) -> RecordButton:
        """녹음 버튼."""
        return self._record_btn

    def closeEvent(self, event: Any) -> None:  # noqa: N802
        """윈도우 닫기 시 녹음 중지."""
        if self._audio_worker is not None:
            self._audio_worker.stop()
        super().closeEvent(event)


# ============================================================
# 유틸리티
# ============================================================


def _fmt_duration(seconds: float) -> str:
    """초를 MM:SS 또는 H:MM:SS로 변환한다."""
    total = int(seconds)
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"
