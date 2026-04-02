"""메인 윈도우 — Apple Voice Memos 스타일 UI."""

from __future__ import annotations

import json
import logging
import pathlib
import tempfile
from datetime import UTC, datetime
from typing import Any

import numpy as np
from PyQt6.QtCore import QSize, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from meeting_transcriber.ai.templates import TemplateManager
from meeting_transcriber.core.audio_capture import AudioCaptureWorker, encode_wav_chunk
from meeting_transcriber.core.system_audio import (
    is_blackhole_installed,
    resolve_device_by_uid,
)
from meeting_transcriber.core.transcriber import FileTranscriber, TranscriptionResult
from meeting_transcriber.storage.transcript_store import (
    create_transcript,
    load_transcript,
    save_transcript,
    update_transcript_speakers,
)
from meeting_transcriber.storage.workspace import WorkspaceManager
from meeting_transcriber.ui.blackhole_wizard import BlackHoleSetupWizard
from meeting_transcriber.ui.theme import ThemeEngine
from meeting_transcriber.ui.widgets.dual_level_meter import DualLevelMeter
from meeting_transcriber.ui.widgets.toggle_switch import SystemAudioToggle
from meeting_transcriber.utils.config import load_settings, save_settings
from meeting_transcriber.utils.constants import (
    APP_NAME,
    BUILTIN_TEMPLATE_NAMES,
    DEFAULT_TEMPLATE,
    DIARIZATION_MODEL,
)

logger = logging.getLogger(__name__)

# ============================================================
# 녹음 버튼 (큰 원형, Voice Memos 스타일)
# ============================================================


class RecordButton(QPushButton):
    """원형 녹음 버튼 — 빨간 원(대기) / 빨간 정사각형(녹음 중)."""

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._recording = False
        self._recording_color = QColor("#FF453A")
        self._ring_color = QColor(255, 255, 255, 38)
        self.setFixedSize(56, 56)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("border: none; background: transparent;")

    def set_theme_colors(self, recording: str, ring_rgba: tuple[int, int, int, int]) -> None:
        """테마 색상을 설정한다.

        Args:
            recording: 녹음 상태 색상 (hex)
            ring_rgba: 외부 링 RGBA 튜플
        """
        self._recording_color = QColor(recording)
        self._ring_color = QColor(*ring_rgba)
        self.update()

    def set_recording(self, recording: bool) -> None:
        """녹음 상태를 설정한다."""
        self._recording = recording
        self.update()

    def paintEvent(self, event: Any) -> None:  # noqa: N802
        """원형/사각형 녹음 아이콘을 그린다."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setBrush(self._recording_color)
        painter.setPen(Qt.PenStyle.NoPen)

        if self._recording:
            # 정지 아이콘: 둥근 사각형
            size = 18
            x = (self.width() - size) // 2
            y = (self.height() - size) // 2
            path = QPainterPath()
            path.addRoundedRect(float(x), float(y), float(size), float(size), 4.0, 4.0)
            painter.fillPath(path, self._recording_color)
        else:
            # 녹음 아이콘: 큰 원
            size = 40
            x = (self.width() - size) // 2
            y = (self.height() - size) // 2
            painter.drawEllipse(x, y, size, size)

        # 외부 링
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(self._ring_color)
        ring_size = 52
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

    diarization_requested = pyqtSignal(str)
    rerun_ai_requested = pyqtSignal(str, str)  # (transcript_path, template_key)

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._current_path: str = ""
        self._current_transcript: dict[str, Any] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # 제목 + 메타
        self._title_label = QLabel("")
        self._title_label.setFont(QFont("", 17, QFont.Weight.Bold))
        layout.addWidget(self._title_label)

        self._meta_label = QLabel("")
        self._meta_label.setObjectName("caption")
        layout.addWidget(self._meta_label)

        # 화자 패널
        self._speaker_panel = QWidget()
        self._speaker_layout = QHBoxLayout(self._speaker_panel)
        self._speaker_layout.setContentsMargins(0, 0, 0, 0)
        self._speaker_prefix = QLabel("Speakers:")
        self._speaker_prefix.setObjectName("speaker_list_prefix")
        speaker_font = self._speaker_prefix.font()
        speaker_font.setPixelSize(11)
        self._speaker_prefix.setFont(speaker_font)
        self._speaker_layout.addWidget(self._speaker_prefix)
        self._speaker_layout.addStretch()
        self._speaker_panel.setVisible(False)
        layout.addWidget(self._speaker_panel)

        # 3탭
        self._tabs = QTabWidget()
        edit_style = "border: none;"

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

        # Re-run AI 버튼 + 템플릿 콤보
        rerun_row = QHBoxLayout()
        self._rerun_ai_btn = QPushButton("Re-run AI")
        self._rerun_ai_btn.setObjectName("rerun_ai_btn")
        self._rerun_ai_btn.setFixedWidth(120)
        self._rerun_ai_btn.setEnabled(False)
        self._rerun_ai_btn.clicked.connect(self._on_rerun_ai_clicked)
        rerun_row.addWidget(self._rerun_ai_btn)

        self._rerun_template_combo = QComboBox()
        self._rerun_template_combo.setObjectName("rerun_template_combo")
        self._rerun_template_combo.setFixedWidth(140)
        rerun_row.addWidget(self._rerun_template_combo)

        rerun_row.addStretch()
        summary_layout.addLayout(rerun_row)

        self._tabs.addTab(summary_widget, "Summary")

        layout.addWidget(self._tabs)

        # Export buttons — per D-03, export actions in transcript viewer toolbar
        export_bar = QHBoxLayout()

        # Identify Speakers button (left side)
        self._identify_btn = QPushButton("Identify Speakers")
        self._identify_btn.setFixedWidth(160)
        self._identify_btn.clicked.connect(self._identify_speakers_clicked)
        export_bar.addWidget(self._identify_btn)

        export_bar.addStretch()

        self._export_srt_btn = QPushButton("Export SRT")
        self._export_srt_btn.setFixedWidth(100)
        self._export_srt_btn.clicked.connect(self._export_srt)
        export_bar.addWidget(self._export_srt_btn)

        self._export_vtt_btn = QPushButton("Export VTT")
        self._export_vtt_btn.setFixedWidth(100)
        self._export_vtt_btn.clicked.connect(self._export_vtt)
        export_bar.addWidget(self._export_vtt_btn)

        self._export_obsidian_btn = QPushButton("Export to Obsidian")
        self._export_obsidian_btn.setFixedWidth(140)
        self._export_obsidian_btn.clicked.connect(self._export_obsidian)
        export_bar.addWidget(self._export_obsidian_btn)

        layout.addLayout(export_bar)

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

        self._current_transcript = transcript
        metadata = transcript.get("metadata", {})
        self._title_label.setText(metadata.get("title", "Untitled"))

        duration = metadata.get("duration_seconds", 0)
        langs = ", ".join(metadata.get("languages", []))
        self._meta_label.setText(f"{_fmt_duration(duration)}  {langs}")

        # Tab 0: 원본 세그먼트 (화자 라벨 포함)
        segments = transcript.get("segments", [])
        speakers_map = metadata.get("speakers", {})
        has_speakers = bool(speakers_map)

        if has_speakers:
            # 테마에 따른 화자 라벨 색상
            palette = self.palette()
            bg_lightness = palette.window().color().lightness()
            speaker_color = "#6E6E73" if bg_lightness > 128 else "#98989D"

            html_parts = []
            for seg in segments:
                text = seg.get("text", "")
                if not text:
                    continue
                speaker = seg.get("speaker", "")
                display_name = speakers_map.get(speaker, speaker) if speaker else ""
                if display_name:
                    html_parts.append(
                        f'<p style="margin: 0 0 8px 0;">'
                        f'<span style="color: {speaker_color}; font-weight: 600;">'
                        f"{display_name}:</span> {text}</p>"
                    )
                else:
                    html_parts.append(f'<p style="margin: 0 0 8px 0;">{text}</p>')
            self._original_edit.setHtml("".join(html_parts))
        else:
            lines = [seg.get("text", "") for seg in segments if seg.get("text")]
            self._original_edit.setPlainText("\n".join(lines))

        # 화자 패널 업데이트
        self._update_speaker_panel(segments, speakers_map)

        # Identify Speakers 버튼 상태
        audio_path = pathlib.Path(path).parent / "recording.wav"
        if audio_path.exists():
            if metadata.get("diarization"):
                self._identify_btn.setText("Re-identify Speakers")
            else:
                self._identify_btn.setText("Identify Speakers")
            self._identify_btn.setEnabled(True)
            self._identify_btn.setToolTip("")
        else:
            self._identify_btn.setText("Identify Speakers")
            self._identify_btn.setEnabled(False)
            self._identify_btn.setToolTip(
                "Audio file not found — cannot identify speakers"
            )

        # Tab 1: 교열
        proofread = metadata.get("proofread", "")
        self._proofread_edit.setPlainText(
            proofread if proofread else "(AI processing required — set Gemini API key in Settings)"
        )
        self._proofread_edit.setReadOnly(not bool(proofread))

        # Tab 2: 요약 + 키워드
        summary = metadata.get("summary", "")
        if isinstance(summary, dict):
            # 구조화 템플릿 요약 — HTML 렌더링
            # Inline styles required: QTextEdit HTML ignores QSS, only respects inline CSS.
            # Values match design tokens: font-size 14px (text.body), weight 600 (heading).
            html_parts: list[str] = []
            for section_key, items in summary.items():
                label = section_key.replace("_", " ").title()
                html_parts.append(
                    f'<h3 style="font-size: 14px; font-weight: 600; '
                    f'margin-top: 16px; margin-bottom: 8px;">'
                    f"{label}</h3>"
                )
                if isinstance(items, list):
                    html_parts.append('<ul style="margin: 0; padding-left: 20px;">')
                    for item in items:
                        html_parts.append(
                            f'<li style="font-size: 14px; margin-bottom: 4px;">'
                            f"{item}</li>"
                        )
                    html_parts.append("</ul>")
                else:
                    html_parts.append(f'<p style="font-size: 14px;">{items}</p>')
            self._summary_edit.setHtml("".join(html_parts))
        elif summary:
            self._summary_edit.setPlainText(summary)
        else:
            self._summary_edit.setPlainText("(No summary available)")

        # Re-run AI 버튼 활성화 (transcript가 있으면)
        has_transcript_text = bool(segments)
        self._rerun_ai_btn.setEnabled(has_transcript_text)
        if not summary and has_transcript_text:
            self._rerun_ai_btn.setText("Run AI")
        else:
            self._rerun_ai_btn.setText("Re-run AI")

        tags = metadata.get("tags", [])
        if tags:
            self._keywords_label.setText("Keywords: " + ", ".join(tags))
        else:
            self._keywords_label.setText("")

    def _update_speaker_panel(
        self,
        segments: list[dict[str, Any]],
        speakers_map: dict[str, str],
    ) -> None:
        """화자 패널을 업데이트한다.

        Args:
            segments: 전사 세그먼트 리스트
            speakers_map: 화자 라벨 -> 표시 이름 딕셔너리
        """
        # 기존 화자 라벨 제거 (prefix와 stretch 제외)
        while self._speaker_layout.count() > 2:
            item = self._speaker_layout.takeAt(1)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not speakers_map:
            self._speaker_panel.setVisible(False)
            return

        # 세그먼트에서 고유 화자 추출 (순서 유지)
        seen: set[str] = set()
        unique_speakers: list[str] = []
        for seg in segments:
            speaker = seg.get("speaker", "")
            if speaker and speaker not in seen:
                seen.add(speaker)
                unique_speakers.append(speaker)

        if not unique_speakers:
            self._speaker_panel.setVisible(False)
            return

        display_count = min(len(unique_speakers), 8)
        for raw_label in unique_speakers[:display_count]:
            display_name = speakers_map.get(raw_label, raw_label)
            label = QLabel(display_name)
            label.setObjectName("speaker_name")
            label.setCursor(Qt.CursorShape.PointingHandCursor)
            # 클릭 이벤트를 람다로 연결
            label.mousePressEvent = lambda _evt, lbl=raw_label: self._on_speaker_clicked(lbl)
            self._speaker_layout.insertWidget(self._speaker_layout.count() - 1, label)

        if len(unique_speakers) > 8:
            more = QLabel(f"+{len(unique_speakers) - 8} more")
            more.setObjectName("caption")
            self._speaker_layout.insertWidget(self._speaker_layout.count() - 1, more)

        self._speaker_panel.setVisible(True)

    def _on_speaker_clicked(self, raw_label: str) -> None:
        """화자 이름 클릭 시 이름 변경 다이얼로그를 표시한다.

        Args:
            raw_label: 화자 원본 라벨
        """
        from PyQt6.QtWidgets import QInputDialog

        speakers_map = self._current_transcript.get("metadata", {}).get("speakers", {})
        current_name = speakers_map.get(raw_label, raw_label)

        new_name, ok = QInputDialog.getText(
            self,
            "Rename Speaker",
            f"Enter name for {current_name}:",
            text=current_name,
        )
        if not ok or new_name == current_name:
            return

        from meeting_transcriber.core.diarizer import rename_speaker

        self._current_transcript = rename_speaker(self._current_transcript, raw_label, new_name)
        save_transcript(self._current_transcript, pathlib.Path(self._current_path))
        self.display_transcript(self._current_path)

    def _identify_speakers_clicked(self) -> None:
        """Identify Speakers 버튼 클릭 처리."""
        from meeting_transcriber.utils.keychain import get_api_key

        token = get_api_key("huggingface")
        if not token:
            QMessageBox.warning(
                self,
                "Token Required",
                "HuggingFace token required. Add it in Settings > Speaker Identification.",
            )
            return

        self._identify_btn.setEnabled(False)
        self._identify_btn.setText("Identifying speakers...")
        self.diarization_requested.emit(self._current_path)

    def _on_rerun_ai_clicked(self) -> None:
        """Re-run AI 버튼 클릭 처리. 선택된 템플릿으로 요약을 재생성한다."""
        template_key = self._rerun_template_combo.currentData()
        if not template_key or not self._current_path:
            return
        self._rerun_ai_btn.setEnabled(False)
        self._rerun_ai_btn.setText("Running AI...")
        # MainWindow에서 처리하도록 시그널 emit
        self.rerun_ai_requested.emit(self._current_path, template_key)

    def _save_proofread(self) -> None:
        """교열 텍스트를 transcript.json에 저장한다."""
        if not self._current_path:
            return

        try:
            transcript = load_transcript(pathlib.Path(self._current_path))
            transcript.setdefault("metadata", {})["proofread"] = self._proofread_edit.toPlainText()
            save_transcript(transcript, pathlib.Path(self._current_path))
        except Exception:
            logger.warning("Failed to save proofread: %s", self._current_path, exc_info=True)

    def _export_srt(self) -> None:
        """현재 트랜스크립트를 SRT 형식으로 내보낸다."""
        if not self._current_path:
            return
        from meeting_transcriber.storage.exporter import export_to_srt, save_export

        try:
            transcript = load_transcript(pathlib.Path(self._current_path))
        except Exception:
            return

        content = export_to_srt(transcript)
        settings = load_settings()
        default_dir = settings.get("export", {}).get("default_dir", "")

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export SRT",
            str(pathlib.Path(default_dir) / "transcript.srt") if default_dir else "transcript.srt",
            "SRT Files (*.srt)",
        )
        if path:
            save_export(content, pathlib.Path(path))

    def _export_vtt(self) -> None:
        """현재 트랜스크립트를 VTT 형식으로 내보낸다."""
        if not self._current_path:
            return
        from meeting_transcriber.storage.exporter import export_to_vtt, save_export

        try:
            transcript = load_transcript(pathlib.Path(self._current_path))
        except Exception:
            return

        content = export_to_vtt(transcript)
        settings = load_settings()
        default_dir = settings.get("export", {}).get("default_dir", "")

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export VTT",
            str(pathlib.Path(default_dir) / "transcript.vtt") if default_dir else "transcript.vtt",
            "VTT Files (*.vtt)",
        )
        if path:
            save_export(content, pathlib.Path(path))

    def _export_obsidian(self) -> None:
        """현재 트랜스크립트를 Obsidian 형식으로 내보낸다."""
        if not self._current_path:
            return
        from meeting_transcriber.storage.exporter import (
            export_to_obsidian,
            obsidian_filename,
            save_export,
        )

        try:
            transcript = load_transcript(pathlib.Path(self._current_path))
        except Exception:
            return

        content = export_to_obsidian(transcript)
        settings = load_settings()
        vault_path = settings.get("export", {}).get("obsidian_vault", "")

        if not vault_path:
            vault_path = QFileDialog.getExistingDirectory(
                self,
                "Select Obsidian Vault",
                str(pathlib.Path.home()),
            )
            if not vault_path:
                return

        filename = obsidian_filename(transcript)
        save_export(content, pathlib.Path(vault_path) / filename)

    def clear(self) -> None:
        """뷰어 내용을 초기화한다."""
        self._current_path = ""
        self._current_transcript = {}
        self._title_label.setText("")
        self._meta_label.setText("")
        self._original_edit.clear()
        self._proofread_edit.clear()
        self._summary_edit.clear()
        self._keywords_label.setText("")
        self._speaker_panel.setVisible(False)
        self._identify_btn.setText("Identify Speakers")
        self._identify_btn.setEnabled(False)
        self._rerun_ai_btn.setText("Re-run AI")
        self._rerun_ai_btn.setEnabled(False)


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
            logger.debug("Chunk transcription failed", exc_info=True)


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
        self._diarization_worker: Any = None
        self._chunk_workers: list[ChunkTranscriberThread] = []
        self._realtime_segments: list[dict[str, Any]] = []
        self._chunk_count = 0
        self._is_recording = False
        self._analysis_worker: Any = None
        self._metadata_index: Any = None
        self._current_analysis_path: str | None = None
        self._export_analysis_btn: QPushButton | None = None

        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(800, 520)

        self._setup_ui()
        self._apply_theme()
        self._connect_signals()
        self._refresh_recording_list()

        # 템플릿 관리자 초기화
        self._template_manager = TemplateManager()
        self._template_manager.ensure_templates()
        self._template_manager.load_all()
        self._populate_template_combos()

        # 메타데이터 인덱스 초기화
        self._init_metadata_index()

        # System audio state init
        self._recording_with_system_audio = False
        blackhole_ok = is_blackhole_installed()
        self._system_audio_toggle.set_blackhole_available(blackhole_ok)
        settings = load_settings()
        sys_audio = settings.get("audio", {}).get("system_audio", {})
        if blackhole_ok and sys_audio.get("enabled"):
            self._system_audio_toggle.setChecked(True)
            self._level_meter.set_dual_mode(True)
            self._control_bar.setFixedHeight(80)

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

        sidebar_header = QLabel("Recordings")
        sidebar_header.setFont(QFont("", 14, QFont.Weight.Bold))
        sidebar_header.setFixedHeight(40)
        sidebar_header.setObjectName("heading")
        sidebar_layout.addWidget(sidebar_header)

        self._recording_list = QListWidget()
        # 스타일은 ThemeEngine QSS에서 적용
        self._recording_list.currentItemChanged.connect(self._on_recording_selected)
        self._recording_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._recording_list.customContextMenuRequested.connect(self._on_recording_context_menu)
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
        self._control_bar.setFixedHeight(72)
        bar_layout = QVBoxLayout(self._control_bar)
        bar_layout.setContentsMargins(0, 6, 0, 6)
        bar_layout.setSpacing(4)

        # 레벨 미터 (마이크 + 시스템 오디오 듀얼)
        self._level_meter = DualLevelMeter()
        bar_layout.addWidget(self._level_meter)

        # 버튼 + 타이머
        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_row.setSpacing(16)

        self._duration_label = QLabel("00:00")
        self._duration_label.setFixedWidth(50)
        self._duration_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._duration_label.setObjectName("caption")
        btn_row.addWidget(self._duration_label)

        # System audio toggle
        self._system_audio_toggle = SystemAudioToggle()
        toggle_container = QWidget()
        toggle_layout = QVBoxLayout(toggle_container)
        toggle_layout.setContentsMargins(0, 0, 0, 0)
        toggle_layout.setSpacing(2)
        toggle_layout.addWidget(
            self._system_audio_toggle, alignment=Qt.AlignmentFlag.AlignCenter
        )
        self._system_audio_label = QLabel("System Audio")
        self._system_audio_label.setObjectName("system_audio_label")
        self._system_audio_label.setProperty("state", "idle")
        self._system_audio_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        toggle_layout.addWidget(self._system_audio_label)
        toggle_container.setFixedWidth(56)
        btn_row.addWidget(toggle_container)

        # 템플릿 선택 콤보
        self._template_combo = QComboBox()
        self._template_combo.setObjectName("template_combo")
        self._template_combo.setFixedWidth(140)
        btn_row.addWidget(self._template_combo)

        self._record_btn = RecordButton()
        self._record_btn.clicked.connect(self._on_record_btn_clicked)
        btn_row.addWidget(self._record_btn)

        self._status_label = QLabel("Ready")
        self._status_label.setFixedWidth(100)
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

    def _populate_template_combos(self) -> None:
        """템플릿 콤보박스를 채운다.

        빌트인 템플릿을 순서대로, 커스텀 템플릿은 알파벳순으로 추가한다.
        """
        templates = self._template_manager.load_all()

        for combo in (self._template_combo, self._transcript_viewer._rerun_template_combo):
            combo.clear()
            # 빌트인 먼저 (정해진 순서)
            for key in BUILTIN_TEMPLATE_NAMES:
                tmpl = templates.get(key)
                if tmpl:
                    combo.addItem(tmpl.name, key)
            # 커스텀 템플릿 (알파벳순)
            custom_keys = sorted(k for k in templates if k not in BUILTIN_TEMPLATE_NAMES)
            for key in custom_keys:
                combo.addItem(templates[key].name, key)

        # 기본 선택: General
        idx = self._template_combo.findData(DEFAULT_TEMPLATE)
        if idx >= 0:
            self._template_combo.setCurrentIndex(idx)
        idx2 = self._transcript_viewer._rerun_template_combo.findData(DEFAULT_TEMPLATE)
        if idx2 >= 0:
            self._transcript_viewer._rerun_template_combo.setCurrentIndex(idx2)

    def _get_selected_template_key(self) -> str:
        """컨트롤바 템플릿 콤보에서 선택된 키를 반환한다.

        Returns:
            템플릿 키 문자열 (예: "general")
        """
        return str(self._template_combo.currentData() or DEFAULT_TEMPLATE)

    def _get_transcript_speakers(self) -> dict[str, str] | None:
        """현재 표시 중인 transcript에서 화자 매핑을 반환한다.

        Returns:
            화자 매핑 딕셔너리 또는 None
        """
        transcript = self._transcript_viewer._current_transcript
        speakers = transcript.get("metadata", {}).get("speakers", {})
        return speakers if speakers else None

    def suggest_template(self, template_key: str) -> None:
        """외부에서 템플릿을 제안한다. 감지 알림 클릭 시 사용.

        Args:
            template_key: 제안할 템플릿 키
        """
        idx = self._template_combo.findData(template_key)
        if idx >= 0:
            self._template_combo.setCurrentIndex(idx)

    def _set_status_state(self, state: str) -> None:
        """상태 라벨의 동적 스타일 프로퍼티를 설정하고 QSS를 갱신한다."""
        self._status_label.setProperty("state", state)
        self._set_status_state_on(self._status_label)

    @staticmethod
    def _set_status_state_on(widget: QWidget) -> None:
        """위젯의 QSS property 변경 후 스타일을 갱신한다."""
        style = widget.style()
        if style is not None:
            style.unpolish(widget)
            style.polish(widget)

    def _apply_theme(self) -> None:
        """테마를 적용한다."""
        qss = self._theme.generate_qss()
        self.setStyleSheet(qss)

    def _connect_signals(self) -> None:
        """내부 signal을 연결한다."""
        self._system_audio_toggle.toggled.connect(self._on_system_audio_toggled)
        self._system_audio_toggle.setup_requested.connect(
            self._on_system_audio_setup_requested
        )
        self._transcript_viewer.diarization_requested.connect(
            self._on_identify_speakers_requested
        )
        self._transcript_viewer.rerun_ai_requested.connect(
            self._on_rerun_ai_requested
        )

    # -- 시스템 오디오 --

    def _on_system_audio_toggled(self, enabled: bool) -> None:
        """시스템 오디오 토글 변경."""
        settings = load_settings()
        settings["audio"]["system_audio"]["enabled"] = enabled
        save_settings(settings)
        self._level_meter.set_dual_mode(enabled)
        if enabled:
            self._control_bar.setFixedHeight(80)
        else:
            self._control_bar.setFixedHeight(72)

    def _on_system_audio_setup_requested(self) -> None:
        """BlackHole 설치 위저드를 연다."""
        wizard = BlackHoleSetupWizard(self)
        wizard.setup_completed.connect(self._on_blackhole_setup_completed)
        wizard.exec()

    def _on_blackhole_setup_completed(self) -> None:
        """BlackHole 설치 완료 -- 토글 활성화."""
        self._system_audio_toggle.set_blackhole_available(True)
        self._system_audio_toggle.setChecked(True)

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
                    logger.warning("Failed to load transcript: %s", t_path)
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

    # -- 녹음 삭제 --

    def _on_recording_context_menu(self, pos: Any) -> None:
        """녹음 리스트 우클릭 컨텍스트 메뉴를 표시한다."""
        item = self._recording_list.itemAt(pos)
        if item is None:
            return

        menu = QMenu(self)
        delete_action = menu.addAction("Delete")
        chosen = menu.exec(self._recording_list.mapToGlobal(pos))
        if chosen == delete_action:
            self._delete_recording(item)

    def _delete_recording(self, item: QListWidgetItem) -> None:
        """녹음을 삭제한다."""
        path_str = item.data(Qt.ItemDataRole.UserRole)
        if not path_str:
            return

        reply = QMessageBox.question(
            self,
            "Delete Recording",
            "Are you sure you want to delete this recording?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            self._workspace.delete_recording(
                pathlib.Path(path_str), index=self._metadata_index
            )
        except (ValueError, FileNotFoundError, OSError):
            self._status_bar.showMessage("Failed to delete recording", 3000)
            return

        self._transcript_viewer.clear()
        self._transcript_viewer.hide()
        self._empty_state.show()
        self._refresh_recording_list()
        self._status_bar.showMessage("Recording deleted", 2000)

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
        sys_audio = settings.get("audio", {}).get("system_audio", {})
        device = settings.get("audio", {}).get("device")
        self._recording_with_system_audio = False

        # System audio: use Aggregate Device (per D-05, D-06)
        if sys_audio.get("enabled") and sys_audio.get("aggregate_device_uid"):
            aggregate_idx = resolve_device_by_uid(sys_audio["aggregate_device_uid"])
            if aggregate_idx is not None:
                device = aggregate_idx
                self._recording_with_system_audio = True
                self._status_bar.showMessage("Recording: Mic + System Audio")
            else:
                # Aggregate Device not found -- fallback to mic (per D-11, D-12)
                self._status_bar.showMessage(
                    "System audio disconnected -- continuing with microphone only"
                )
        else:
            self._status_bar.showMessage("Recording: Microphone")

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
        self._system_audio_toggle.set_recording(True)
        self._record_seconds = 0
        self._duration_label.setText("00:00")
        self._status_label.setText("Recording...")
        self._set_status_state("recording")
        self._record_timer.start()
        self._status_bar.showMessage("Recording...")
        # 듀얼 소스 녹음 시 System Audio 라벨 강조
        if self._recording_with_system_audio:
            self._system_audio_label.setProperty("state", "recording")
            self._set_status_state_on(self._system_audio_label)
        self.recording_started.emit()

    def _on_capture_stopped(self) -> None:
        """녹음 정지됨 — 전사를 시작한다."""
        self._is_recording = False
        self._record_btn.set_recording(False)
        self._system_audio_toggle.set_recording(False)
        self._recording_with_system_audio = False
        self._record_timer.stop()
        self._level_meter.reset()
        # System Audio 라벨 원래 색상으로 복원
        self._system_audio_label.setProperty("state", "idle")
        self._set_status_state_on(self._system_audio_label)
        self._status_label.setText("Processing...")
        self._set_status_state("processing")
        self._status_bar.showMessage("Processing recording...")
        self.recording_stopped.emit()

        if self._audio_worker is None:
            return

        recording = self._audio_worker.get_full_recording()
        self._audio_worker = None

        if len(recording) == 0:
            self._status_label.setText("Tap to Record")
            self._set_status_state("idle")
            self._status_bar.showMessage("No audio recorded")
            return

        self._process_recording(recording)

    def _on_capture_error(self, message: str) -> None:
        """오디오 캡처 오류 처리 -- 시스템 오디오 실패 시 마이크 전용으로 재시작."""
        if self._recording_with_system_audio and self._is_recording:
            # Mid-recording system audio failure (per D-11):
            # Restart with mic-only while keeping recording state active.
            logger.warning("System audio stream failed: %s", message)
            self._recording_with_system_audio = False
            self._level_meter.set_dual_mode(False)
            self._control_bar.setFixedHeight(72)
            self._status_bar.showMessage(
                "System audio disconnected -- continuing with microphone only"
            )
            self._system_audio_label.setProperty("state", "idle")
            self._set_status_state_on(self._system_audio_label)

            # Restart AudioCaptureWorker with mic-only device
            settings = load_settings()
            mic_device = settings.get("audio", {}).get("device")
            self._audio_worker = AudioCaptureWorker(device=mic_device)
            self._audio_worker.capture_started.connect(self._on_capture_started)
            self._audio_worker.capture_stopped.connect(self._on_capture_stopped)
            self._audio_worker.error_occurred.connect(self._on_capture_error)
            self._audio_worker.level_changed.connect(self._on_level_changed)
            self._audio_worker.chunk_ready.connect(self._on_chunk_ready)
            self._audio_worker.start()
            return

        # Non-system-audio error or mic-only error: stop recording
        self._is_recording = False
        self._record_btn.set_recording(False)
        self._system_audio_toggle.set_recording(False)
        self._recording_with_system_audio = False
        self._record_timer.stop()
        self._level_meter.reset()
        self._system_audio_label.setProperty("state", "idle")
        self._set_status_state_on(self._system_audio_label)
        self._status_label.setText("Error")
        self._set_status_state("error")
        self._status_bar.showMessage(f"Error: {message}")

    def _on_level_changed(self, level: float) -> None:
        """오디오 레벨 업데이트."""
        self._level_meter.set_mic_level(level)
        # Aggregate Device merges both sources into one stream,
        # so mic_level reflects the combined level
        if self._system_audio_toggle.isChecked():
            self._level_meter.set_system_level(level)

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
        self._transcription_worker.progress.connect(lambda msg: self._status_bar.showMessage(msg))
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
        self._transcription_worker = None

        if isinstance(result, Exception):
            temp_wav.unlink(missing_ok=True)
            self._status_label.setText("Tap to Record")
            self._set_status_state("idle")
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
        save_transcript(transcript, folder / "transcript.json", index=self._metadata_index)

        # 오디오 파일 보존 — diarization에 필요
        audio_dest = folder / "recording.wav"
        try:
            temp_wav.rename(audio_dest)
        except OSError:
            # rename 실패 시 (cross-device 등) 복사 후 삭제
            import shutil

            shutil.copy2(temp_wav, audio_dest)
            temp_wav.unlink(missing_ok=True)

        self._refresh_recording_list()
        self._status_label.setText("Tap to Record")
        self._set_status_state("idle")
        self._status_bar.showMessage(f"Saved: {now}")

        for seg in result.segments:
            self.caption_updated.emit(seg.get("text", ""))

        # AI 처리 (API 키가 있을 때만)
        self._run_ai_tasks(result, folder / "transcript.json")

        # 자동 화자 분리 (HF 토큰이 있을 때만)
        self._auto_diarize(audio_dest, result.segments, folder / "transcript.json")

    # -- AI 처리 --

    def _run_ai_tasks(self, result: TranscriptionResult, transcript_path: pathlib.Path) -> None:
        """전사 결과에 AI 처리(교열, 요약, 키워드, 제목)를 실행한다."""
        from meeting_transcriber.ai.provider_manager import FallbackProvider, ProviderManager
        from meeting_transcriber.ai.tasks import AITaskWorker

        settings = load_settings()
        manager = ProviderManager()

        try:
            chain = manager.get_provider_chain(settings)
        except Exception:
            return  # 프로바이더 초기화 실패

        if not chain:
            return  # API 키가 하나도 없음

        full_text = " ".join(s.get("text", "") for s in result.segments)
        if not full_text.strip():
            return

        # FallbackProvider wraps the full chain — each AI method call
        # automatically tries the next provider on failure (per D-13, BYOK-04)
        provider = FallbackProvider(manager, chain)

        # 템플릿 프롬프트 렌더링
        template_key = self._get_selected_template_key()
        template = self._template_manager.get(template_key)
        template_prompt = None
        if template and template.is_structured:
            speakers = self._get_transcript_speakers()
            template_prompt = self._template_manager.render_prompt(
                template, language=result.language, speakers=speakers,
            )

        try:
            self._ai_worker = AITaskWorker(
                provider=provider,
                text=full_text,
                language=result.language,
                template_prompt=template_prompt,
            )
            self._ai_worker.progress.connect(lambda msg: self._status_bar.showMessage(msg))
            # After worker finishes, check for fallback messages and display per D-14
            self._ai_worker.finished.connect(
                lambda ai_result: self._on_ai_done_with_fallback(
                    ai_result, transcript_path, provider
                )
            )
            self._ai_worker.start()
        except Exception as e:
            self._status_bar.showMessage(f"AI processing skipped: {e}")

    def _on_ai_done_with_fallback(
        self,
        ai_result: Any,
        transcript_path: pathlib.Path,
        provider: Any,
    ) -> None:
        """AI 완료 후 폴백 메시지를 상태바에 표시하고 결과를 처리한다."""
        # Show fallback messages in status bar per D-14
        if hasattr(provider, "fallback_messages") and provider.fallback_messages:
            fallback_info = "; ".join(provider.fallback_messages)
            self._status_bar.showMessage(f"AI complete (fallback: {fallback_info})", 10000)
        # Delegate to existing handler
        self._on_ai_done(ai_result, transcript_path)

    def _on_ai_done(self, ai_result: Any, transcript_path: pathlib.Path) -> None:
        """AI 처리 완료 — 결과를 transcript에 저장한다."""
        self._ai_worker = None

        try:
            transcript = load_transcript(transcript_path)
            metadata = transcript.setdefault("metadata", {})

            if ai_result.summary:
                template_key = self._get_selected_template_key()
                template = self._template_manager.get(template_key)
                if template and template.is_structured:
                    try:
                        structured = json.loads(ai_result.summary)
                        metadata["summary"] = structured  # dict
                        metadata["summary_template"] = template_key
                    except json.JSONDecodeError:
                        metadata["summary"] = ai_result.summary  # 폴백: 평문
                else:
                    metadata["summary"] = ai_result.summary
            if ai_result.proofread_text:
                metadata["proofread"] = ai_result.proofread_text
            if ai_result.keywords:
                metadata["tags"] = ai_result.keywords
            if ai_result.title:
                metadata["title"] = ai_result.title

            save_transcript(transcript, transcript_path, index=self._metadata_index)
            self._refresh_recording_list()
            self._status_bar.showMessage("AI processing complete")

            # Re-run AI 버튼 복원
            self._transcript_viewer._rerun_ai_btn.setText("Re-run AI")
            self._transcript_viewer._rerun_ai_btn.setEnabled(True)

            # 뷰어 새로고침
            if self._transcript_viewer._current_path == str(transcript_path):
                self._transcript_viewer.display_transcript(str(transcript_path))
        except Exception as e:
            self._status_bar.showMessage(f"AI save failed: {e}")

    def _on_rerun_ai_requested(self, transcript_path_str: str, template_key: str) -> None:
        """Re-run AI 요청 처리. 선택된 템플릿으로 요약만 재생성한다.

        Args:
            transcript_path_str: transcript.json 경로 문자열
            template_key: 사용할 템플릿 키
        """
        from meeting_transcriber.ai.provider_manager import FallbackProvider, ProviderManager
        from meeting_transcriber.ai.tasks import AITaskWorker

        transcript_path = pathlib.Path(transcript_path_str)
        try:
            transcript = load_transcript(transcript_path)
        except Exception:
            self._status_bar.showMessage("Failed to load transcript")
            return

        segments = transcript.get("segments", [])
        full_text = " ".join(s.get("text", "") for s in segments)
        if not full_text.strip():
            return

        settings = load_settings()
        manager = ProviderManager()
        try:
            chain = manager.get_provider_chain(settings)
        except Exception:
            return
        if not chain:
            return

        provider = FallbackProvider(manager, chain)

        # 템플릿 프롬프트
        template = self._template_manager.get(template_key)
        template_prompt = None
        if template and template.is_structured:
            speakers = transcript.get("metadata", {}).get("speakers")
            language = transcript.get("metadata", {}).get("languages", ["auto"])[0]
            template_prompt = self._template_manager.render_prompt(
                template, language=language, speakers=speakers,
            )

        template_name = template.name if template else template_key
        self._status_bar.showMessage(f"Running AI with {template_name} template...")

        try:
            self._ai_worker = AITaskWorker(
                provider=provider,
                text=full_text,
                language="auto",
                template_prompt=template_prompt,
                do_proofread=False,
                do_summarize=True,
                do_keywords=False,
                do_title=False,
            )
            self._ai_worker.progress.connect(lambda msg: self._status_bar.showMessage(msg))

            # Re-run 완료 시 사용할 template_key를 캡처
            def on_rerun_done(ai_result: Any) -> None:
                self._ai_worker = None
                try:
                    t = load_transcript(transcript_path)
                    meta = t.setdefault("metadata", {})
                    if ai_result.summary:
                        tmpl = self._template_manager.get(template_key)
                        if tmpl and tmpl.is_structured:
                            try:
                                structured = json.loads(ai_result.summary)
                                meta["summary"] = structured
                                meta["summary_template"] = template_key
                            except json.JSONDecodeError:
                                meta["summary"] = ai_result.summary
                        else:
                            meta["summary"] = ai_result.summary
                    save_transcript(t, transcript_path, index=self._metadata_index)
                    self._status_bar.showMessage(f"{template_name} summary generated")
                    self._transcript_viewer._rerun_ai_btn.setText("Re-run AI")
                    self._transcript_viewer._rerun_ai_btn.setEnabled(True)
                    if self._transcript_viewer._current_path == str(transcript_path):
                        self._transcript_viewer.display_transcript(str(transcript_path))
                except Exception as e:
                    self._status_bar.showMessage(f"AI summary failed: {e}")
                    self._transcript_viewer._rerun_ai_btn.setText("Re-run AI")
                    self._transcript_viewer._rerun_ai_btn.setEnabled(True)

            self._ai_worker.finished.connect(on_rerun_done)
            self._ai_worker.start()
        except Exception as e:
            self._status_bar.showMessage(f"AI summary failed: {e}")
            self._transcript_viewer._rerun_ai_btn.setText("Re-run AI")
            self._transcript_viewer._rerun_ai_btn.setEnabled(True)

    # -- 화자 분리 --

    def _auto_diarize(
        self,
        audio_path: pathlib.Path,
        segments: list[dict[str, Any]],
        transcript_path: pathlib.Path,
    ) -> None:
        """녹음 완료 후 자동 화자 분리를 실행한다.

        HF 토큰이 없으면 조용히 건너뛴다.

        Args:
            audio_path: 오디오 파일 경로
            segments: 전사 세그먼트 리스트
            transcript_path: transcript.json 경로
        """
        from meeting_transcriber.utils.keychain import get_api_key

        token = get_api_key("huggingface")
        if not token:
            return

        from meeting_transcriber.core.diarizer import DiarizationWorker

        self._diarization_worker = DiarizationWorker(
            audio_path, segments, token, parent=self,
        )
        self._diarization_worker.progress.connect(
            lambda msg: self._status_bar.showMessage(msg)
        )
        self._diarization_worker.finished.connect(
            lambda result: self._on_diarization_done(result, transcript_path)
        )
        self._diarization_worker.start()
        self._status_bar.showMessage("Identifying speakers...")

    def _on_diarization_done(
        self,
        result: list[dict[str, Any]] | Exception,
        transcript_path: pathlib.Path,
    ) -> None:
        """화자 분리 완료 처리.

        Args:
            result: 화자 라벨이 포함된 세그먼트 리스트 또는 예외
            transcript_path: transcript.json 경로
        """
        self._diarization_worker = None

        if isinstance(result, Exception):
            self._status_bar.showMessage(f"Speaker identification failed: {result}")
            return

        speakers = {
            seg["speaker"]: seg["speaker"]
            for seg in result
            if seg.get("speaker")
        }
        diarization_meta = {
            "model": DIARIZATION_MODEL,
            "completed_at": datetime.now(tz=UTC).isoformat(),
        }
        update_transcript_speakers(
            transcript_path, result, speakers, diarization_meta,
            index=self._metadata_index,
        )
        self._status_bar.showMessage("Speakers identified", 3000)

        # 뷰어 새로고침
        if self._transcript_viewer._current_path == str(transcript_path):
            self._transcript_viewer.display_transcript(str(transcript_path))

    def _on_identify_speakers_requested(self, transcript_path_str: str) -> None:
        """수동 화자 분리 요청 처리.

        Args:
            transcript_path_str: transcript.json 파일 경로 문자열
        """
        from meeting_transcriber.utils.keychain import get_api_key

        transcript_path = pathlib.Path(transcript_path_str)
        audio_path = transcript_path.parent / "recording.wav"

        if not audio_path.exists():
            self._status_bar.showMessage("Audio file not found — cannot identify speakers")
            return

        token = get_api_key("huggingface")
        if not token:
            self._status_bar.showMessage("HuggingFace token required — add in Settings")
            return

        try:
            transcript = load_transcript(transcript_path)
        except Exception:
            self._status_bar.showMessage("Failed to load transcript")
            return

        segments = transcript.get("segments", [])

        from meeting_transcriber.core.diarizer import DiarizationWorker

        self._diarization_worker = DiarizationWorker(
            audio_path, segments, token, parent=self,
        )
        self._diarization_worker.progress.connect(
            lambda msg: self._status_bar.showMessage(msg)
        )
        self._diarization_worker.finished.connect(
            lambda result: self._on_diarization_done(result, transcript_path)
        )
        self._diarization_worker.start()
        self._status_bar.showMessage("Identifying speakers...")

    # -- 메타데이터 인덱스 --

    def _init_metadata_index(self) -> None:
        """메타데이터 인덱스를 초기화한다."""
        from meeting_transcriber.storage.metadata_index import MetadataIndex

        try:
            self._metadata_index = MetadataIndex(self._workspace.root)
        except Exception:
            logger.warning("Failed to initialize MetadataIndex", exc_info=True)
            self._metadata_index = None

    # -- 교차 회의 분석 --

    def _on_analysis_requested(self, transcript_paths: list[str]) -> None:
        """사이드바에서 교차 회의 분석을 요청한다.

        Args:
            transcript_paths: 선택된 transcript 파일 경로 리스트
        """
        # 사용자 커스텀 쿼리 입력
        custom_query, ok = QInputDialog.getText(
            self, "Cross-Meeting Analysis", "Custom query (optional):"
        )
        if not ok:
            custom_query = ""

        # 진행 표시
        self._transcript_viewer._summary_edit.setPlainText(
            f"Analyzing {len(transcript_paths)} transcripts..."
        )
        self._empty_state.hide()
        self._transcript_viewer.show()
        self._transcript_viewer._tabs.setCurrentIndex(2)  # Summary 탭

        # Transcript 로드
        loaded: list[dict[str, Any]] = []
        for p in transcript_paths:
            try:
                loaded.append(load_transcript(pathlib.Path(p)))
            except Exception:
                logger.warning("Failed to load transcript for analysis: %s", p)

        if not loaded:
            self._status_bar.showMessage("No transcripts could be loaded")
            return

        # 다수 언어 결정
        lang_counts: dict[str, int] = {}
        for t in loaded:
            for lang in t.get("metadata", {}).get("languages", []):
                lang_counts[lang] = lang_counts.get(lang, 0) + 1
        majority_lang = max(lang_counts, key=lang_counts.get) if lang_counts else "auto"  # type: ignore[arg-type]

        # 동시 실행 방지
        if self._analysis_worker is not None and self._analysis_worker.isRunning():
            self._status_bar.showMessage("Analysis already in progress")
            return

        # Provider 생성
        from meeting_transcriber.ai.provider_manager import FallbackProvider, ProviderManager

        settings = load_settings()
        manager = ProviderManager()
        try:
            chain = manager.get_provider_chain(settings)
        except Exception:
            self._status_bar.showMessage("AI provider not configured")
            return
        if not chain:
            self._status_bar.showMessage("No API keys configured")
            return

        provider = FallbackProvider(manager, chain)

        from meeting_transcriber.ai.cross_meeting import CrossMeetingAnalysisWorker

        self._analysis_worker = CrossMeetingAnalysisWorker(
            provider=provider,
            transcripts=loaded,
            transcript_paths=transcript_paths,
            language=majority_lang,
            custom_query=custom_query or None,
            parent=self,
        )
        self._analysis_worker.progress.connect(
            lambda msg: self._status_bar.showMessage(msg)
        )
        self._analysis_worker.finished.connect(self._on_analysis_finished)
        self._analysis_worker.start()

    def _on_analysis_finished(self, result: Any) -> None:
        """교차 회의 분석 완료 처리.

        Args:
            result: CrossMeetingResult 인스턴스
        """
        from meeting_transcriber.storage.analysis_store import save_analysis

        # 분석 결과 딕셔너리 구성
        analysis_dict: dict[str, Any] = {
            "version": "1.0",
            "created_at": datetime.now(tz=UTC).isoformat(),
            "transcript_paths": result.transcript_paths,
            "transcript_count": result.transcript_count,
            "custom_query": result.custom_query,
            "language": result.language,
            "result": {
                "recurring_topics": result.recurring_topics,
                "action_items": result.action_items,
                "timeline": result.timeline,
                "custom_answer": result.custom_answer,
            },
        }

        # 저장
        try:
            saved_path = save_analysis(analysis_dict, self._workspace.root)
            self._current_analysis_path = str(saved_path)
        except Exception as e:
            logger.warning("Failed to save analysis: %s", e, exc_info=True)
            self._current_analysis_path = None

        # 결과 표시
        self._display_analysis_result(result)

        # 상태 메시지
        if result.errors:
            self._status_bar.showMessage(f"Analysis complete with errors: {result.errors[0]}")
        else:
            self._status_bar.showMessage("Analysis complete")

        # 사이드바 갱신 (Analyses 섹션 반영)
        self._refresh_recording_list()

        # 워커 정리
        self._analysis_worker = None

    def _display_analysis_result(self, result: Any) -> None:
        """분석 결과를 TranscriptViewer에 HTML로 표시한다.

        Args:
            result: CrossMeetingResult 인스턴스
        """
        html_parts: list[str] = []

        # Header
        html_parts.append(
            f'<h2 style="font-size: 18px; font-weight: 600; margin-bottom: 12px;">'
            f"Cross-Meeting Analysis ({result.transcript_count} meetings)</h2>"
        )

        # Recurring Topics
        if result.recurring_topics:
            html_parts.append(
                '<h3 style="font-size: 16px; font-weight: 600; '
                'margin: 16px 0 8px 0;">Recurring Topics</h3>'
            )
            for topic in result.recurring_topics:
                name = topic.get("name", "")
                freq = topic.get("frequency", 0)
                meetings = ", ".join(topic.get("meetings", []))
                html_parts.append(
                    f'<p style="margin: 4px 0;"><b>{name}</b> ({freq}x) -- {meetings}</p>'
                )

        # Action Items
        if result.action_items:
            html_parts.append(
                '<h3 style="font-size: 16px; font-weight: 600; '
                'margin: 16px 0 8px 0;">Action Items</h3>'
            )
            html_parts.append('<ul style="margin: 0; padding-left: 20px;">')
            for item in result.action_items:
                text = item.get("item", "")
                status = item.get("status", "unresolved")
                assignee = item.get("assignee", "")
                meeting = item.get("meeting", "")
                icon = "&#9745;" if status == "resolved" else "&#9744;"
                line = f"{icon} {text}"
                if assignee:
                    line += f' <span style="color: #666;">(@{assignee})</span>'
                if meeting:
                    line += f' <span style="color: #888;">-- {meeting}</span>'
                html_parts.append(f'<li style="margin: 4px 0;">{line}</li>')
            html_parts.append("</ul>")

        # Timeline
        if result.timeline:
            html_parts.append(
                '<h3 style="font-size: 16px; font-weight: 600; '
                'margin: 16px 0 8px 0;">Timeline</h3>'
            )
            for entry in result.timeline:
                date = entry.get("date", "")
                meeting = entry.get("meeting", "")
                topic = entry.get("topic", "")
                detail = entry.get("detail", "")
                html_parts.append(
                    f'<p style="margin: 4px 0;"><b>{date}</b> [{meeting}] '
                    f"{topic}: {detail}</p>"
                )

        # Custom Answer
        if result.custom_answer:
            html_parts.append(
                '<h3 style="font-size: 16px; font-weight: 600; '
                'margin: 16px 0 8px 0;">Custom Query Answer</h3>'
            )
            html_parts.append(f'<p style="margin: 4px 0;">{result.custom_answer}</p>')

        self._transcript_viewer._summary_edit.setHtml("".join(html_parts))

        # 분석된 transcript 목록 표시
        paths_text = "\n".join(result.transcript_paths)
        self._transcript_viewer._original_edit.setPlainText(
            f"Analyzed {result.transcript_count} transcripts:\n\n{paths_text}"
        )
        self._transcript_viewer._title_label.setText("Cross-Meeting Analysis")
        self._transcript_viewer._meta_label.setText(
            f"{result.transcript_count} transcripts"
        )

        # Export 버튼 표시
        if self._export_analysis_btn is None:
            self._export_analysis_btn = QPushButton("Export as Markdown")
            self._export_analysis_btn.setFixedWidth(180)
            self._export_analysis_btn.clicked.connect(self._export_current_analysis)
            # Summary 탭의 레이아웃에 추가
            summary_tab = self._transcript_viewer._tabs.widget(2)
            if summary_tab is not None:
                tab_layout = summary_tab.layout()
                if tab_layout is not None:
                    tab_layout.addWidget(self._export_analysis_btn)
        self._export_analysis_btn.setVisible(True)

    def _on_analysis_selected(self, analysis_path: str) -> None:
        """사이드바에서 저장된 분석을 선택한다.

        Args:
            analysis_path: 분석 결과 파일 경로
        """
        from meeting_transcriber.ai.cross_meeting import CrossMeetingResult
        from meeting_transcriber.storage.analysis_store import load_analysis

        try:
            analysis_dict = load_analysis(pathlib.Path(analysis_path))
        except Exception as e:
            self._status_bar.showMessage(f"Failed to load analysis: {e}")
            return

        res = analysis_dict.get("result", {})
        result = CrossMeetingResult(
            recurring_topics=res.get("recurring_topics", []),
            action_items=res.get("action_items", []),
            timeline=res.get("timeline", []),
            custom_answer=res.get("custom_answer", ""),
            transcript_paths=analysis_dict.get("transcript_paths", []),
            transcript_count=analysis_dict.get("transcript_count", 0),
            custom_query=analysis_dict.get("custom_query", ""),
            language=analysis_dict.get("language", "auto"),
        )

        self._empty_state.hide()
        self._transcript_viewer.show()
        self._transcript_viewer._tabs.setCurrentIndex(2)
        self._display_analysis_result(result)
        self._current_analysis_path = analysis_path

    def _export_current_analysis(self) -> None:
        """현재 표시 중인 분석을 Markdown으로 내보낸다."""
        if self._current_analysis_path is None:
            return

        from meeting_transcriber.storage.analysis_store import load_analysis
        from meeting_transcriber.storage.exporter import export_analysis_to_markdown, save_export

        try:
            analysis_dict = load_analysis(pathlib.Path(self._current_analysis_path))
        except Exception as e:
            self._status_bar.showMessage(f"Failed to load analysis: {e}")
            return

        markdown = export_analysis_to_markdown(analysis_dict)

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Analysis",
            "cross_meeting_analysis.md",
            "Markdown (*.md)",
        )
        if path:
            save_export(markdown, pathlib.Path(path))
            self._status_bar.showMessage("Analysis exported")

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
