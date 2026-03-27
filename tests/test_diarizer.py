"""화자 분리 엔진 테스트."""

from __future__ import annotations

import pathlib
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from PyQt6.QtCore import QThread

from meeting_transcriber.core.diarizer import (
    DiarizationModelManager,
    DiarizationWorker,
    align_speakers,
    rename_speaker,
)


# ============================================================
# align_speakers 테스트
# ============================================================


class TestAlignSpeakers:
    """align_speakers 함수 테스트."""

    def test_two_speakers_three_segments(self) -> None:
        """2명의 화자, 3개 세그먼트 — 최대 겹침 화자 할당."""
        turns = [
            {"start": 0.0, "end": 5.0, "speaker": "SPEAKER_00"},
            {"start": 5.0, "end": 12.0, "speaker": "SPEAKER_01"},
        ]
        segments = [
            {"start": 0.5, "end": 3.0, "text": "Hello"},
            {"start": 4.0, "end": 6.0, "text": "World"},
            {"start": 7.0, "end": 10.0, "text": "Bye"},
        ]
        result = align_speakers(turns, segments)
        assert result[0]["speaker"] == "SPEAKER_00"
        # seg 4.0-6.0: overlap with SPEAKER_00 is 1.0s, SPEAKER_01 is 1.0s — tie goes to first
        # Actually: SPEAKER_00 overlap = min(3,5)-max(4,0)=min(5,3)-4=... wait
        # seg[1] 4.0-6.0: SPEAKER_00(0-5) overlap = min(5,6)-max(0,4) = 5-4=1.0
        #                  SPEAKER_01(5-12) overlap = min(12,6)-max(5,4) = 6-5=1.0
        # Tie — first encountered wins, so SPEAKER_00
        assert result[1]["speaker"] == "SPEAKER_00"
        assert result[2]["speaker"] == "SPEAKER_01"

    def test_no_overlap_returns_empty_speaker(self) -> None:
        """겹치는 화자 턴이 없는 세그먼트 — 빈 문자열 화자."""
        turns = [
            {"start": 0.0, "end": 2.0, "speaker": "SPEAKER_00"},
        ]
        segments = [
            {"start": 5.0, "end": 8.0, "text": "Isolated"},
        ]
        result = align_speakers(turns, segments)
        assert result[0]["speaker"] == ""

    def test_single_speaker_assigns_to_all(self) -> None:
        """단일 화자 — 모든 세그먼트에 동일 화자 할당."""
        turns = [
            {"start": 0.0, "end": 100.0, "speaker": "SPEAKER_00"},
        ]
        segments = [
            {"start": 1.0, "end": 5.0, "text": "A"},
            {"start": 10.0, "end": 15.0, "text": "B"},
            {"start": 20.0, "end": 25.0, "text": "C"},
        ]
        result = align_speakers(turns, segments)
        for seg in result:
            assert seg["speaker"] == "SPEAKER_00"


# ============================================================
# rename_speaker 테스트
# ============================================================


class TestRenameSpeaker:
    """rename_speaker 함수 테스트."""

    def test_rename_updates_segments_and_metadata(self) -> None:
        """화자 이름 변경 — 세그먼트와 메타데이터 모두 업데이트."""
        transcript = {
            "segments": [
                {"start": 0.0, "end": 5.0, "text": "Hi", "speaker": "SPEAKER_00"},
                {"start": 5.0, "end": 10.0, "text": "Bye", "speaker": "SPEAKER_01"},
                {"start": 10.0, "end": 15.0, "text": "Again", "speaker": "SPEAKER_00"},
            ],
            "metadata": {
                "speakers": {
                    "SPEAKER_00": "SPEAKER_00",
                    "SPEAKER_01": "SPEAKER_01",
                },
            },
        }
        result = rename_speaker(transcript, "SPEAKER_00", "Alice")
        assert result["segments"][0]["speaker"] == "Alice"
        assert result["segments"][1]["speaker"] == "SPEAKER_01"
        assert result["segments"][2]["speaker"] == "Alice"
        assert result["metadata"]["speakers"]["SPEAKER_00"] == "Alice"

    def test_rename_nonexistent_label_no_change(self) -> None:
        """존재하지 않는 화자 라벨 이름 변경 — 변경 없음."""
        transcript = {
            "segments": [
                {"start": 0.0, "end": 5.0, "text": "Hi", "speaker": "SPEAKER_00"},
            ],
            "metadata": {
                "speakers": {"SPEAKER_00": "SPEAKER_00"},
            },
        }
        result = rename_speaker(transcript, "NONEXISTENT", "Alice")
        assert result["segments"][0]["speaker"] == "SPEAKER_00"
        assert "NONEXISTENT" not in result["metadata"]["speakers"]


# ============================================================
# DiarizationModelManager 테스트
# ============================================================


class TestDiarizationModelManager:
    """DiarizationModelManager 테스트."""

    def test_is_model_cached_false_no_dir(self, tmp_path: pathlib.Path) -> None:
        """캐시 디렉토리 없음 — False 반환."""
        cache_dir = tmp_path / "nonexistent"
        mgr = DiarizationModelManager(cache_dir=cache_dir)
        assert mgr.is_model_cached() is False

    def test_is_model_cached_true_with_files(self, tmp_path: pathlib.Path) -> None:
        """HuggingFace 캐시에 모델 파일 존재 — True 반환."""
        # Simulate HuggingFace hub cache structure
        hf_cache = tmp_path / "models--pyannote--speaker-diarization-community-1" / "snapshots"
        snapshot = hf_cache / "abc123"
        snapshot.mkdir(parents=True)
        (snapshot / "config.yaml").write_text("model config")
        mgr = DiarizationModelManager(cache_dir=tmp_path)
        assert mgr.is_model_cached() is True


# ============================================================
# DiarizationWorker 테스트
# ============================================================


class TestDiarizationWorker:
    """DiarizationWorker QThread 테스트."""

    def test_emits_finished_with_labeled_segments(self, qtbot: object) -> None:
        """파이프라인 성공 — labeled segments로 finished 시그널 emit."""
        worker = DiarizationWorker(
            audio_path=pathlib.Path("/tmp/test.wav"),
            segments=[
                {"start": 0.0, "end": 5.0, "text": "Hello"},
                {"start": 5.0, "end": 10.0, "text": "World"},
            ],
            hf_token="fake-token",
        )

        # Mock pyannote and torch
        mock_pipeline_cls = MagicMock()
        mock_pipeline = MagicMock()
        mock_pipeline_cls.from_pretrained.return_value = mock_pipeline

        # Simulate diarization output
        mock_turn1 = MagicMock()
        mock_turn1.start = 0.0
        mock_turn1.end = 5.0
        mock_turn2 = MagicMock()
        mock_turn2.start = 5.0
        mock_turn2.end = 10.0
        mock_diarization = MagicMock()
        mock_diarization.itertracks.return_value = [
            (mock_turn1, None, "SPEAKER_00"),
            (mock_turn2, None, "SPEAKER_01"),
        ]
        mock_pipeline.return_value = mock_diarization

        mock_torch = MagicMock()

        results = []
        worker.finished.connect(results.append)

        with (
            patch.dict("sys.modules", {"pyannote.audio": MagicMock(), "torch": mock_torch}),
            patch(
                "meeting_transcriber.core.diarizer._import_pipeline",
                return_value=mock_pipeline_cls,
            ),
            patch(
                "meeting_transcriber.core.diarizer._import_torch",
                return_value=mock_torch,
            ),
            patch.object(DiarizationModelManager, "is_model_cached", return_value=True),
        ):
            worker.run()

        assert len(results) == 1
        labeled = results[0]
        assert isinstance(labeled, list)
        assert labeled[0]["speaker"] == "SPEAKER_00"
        assert labeled[1]["speaker"] == "SPEAKER_01"

    def test_emits_finished_with_exception_on_failure(self, qtbot: object) -> None:
        """파이프라인 실패 — Exception으로 finished 시그널 emit."""
        worker = DiarizationWorker(
            audio_path=pathlib.Path("/tmp/test.wav"),
            segments=[],
            hf_token="fake-token",
        )

        results = []
        worker.finished.connect(results.append)

        with (
            patch(
                "meeting_transcriber.core.diarizer._import_pipeline",
                side_effect=RuntimeError("Pipeline load failed"),
            ),
            patch(
                "meeting_transcriber.core.diarizer._import_torch",
                return_value=MagicMock(),
            ),
        ):
            worker.run()

        assert len(results) == 1
        assert isinstance(results[0], Exception)

    def test_emits_progress_signal(self, qtbot: object) -> None:
        """진행 상태 시그널 emit 확인."""
        worker = DiarizationWorker(
            audio_path=pathlib.Path("/tmp/test.wav"),
            segments=[],
            hf_token="fake-token",
        )

        progress_msgs: list[str] = []
        worker.progress.connect(progress_msgs.append)

        mock_pipeline_cls = MagicMock()
        mock_pipeline = MagicMock()
        mock_pipeline_cls.from_pretrained.return_value = mock_pipeline
        mock_diarization = MagicMock()
        mock_diarization.itertracks.return_value = []
        mock_pipeline.return_value = mock_diarization
        mock_torch = MagicMock()

        with (
            patch(
                "meeting_transcriber.core.diarizer._import_pipeline",
                return_value=mock_pipeline_cls,
            ),
            patch(
                "meeting_transcriber.core.diarizer._import_torch",
                return_value=mock_torch,
            ),
            patch.object(DiarizationModelManager, "is_model_cached", return_value=True),
        ):
            worker.run()

        assert "Identifying speakers..." in progress_msgs


# ============================================================
# CoreML 최적화 테스트
# ============================================================


class TestCoreMLOptimization:
    """CoreML 변환 시도 및 CPU 폴백 테스트."""

    def _make_worker(self) -> DiarizationWorker:
        """테스트용 DiarizationWorker를 생성한다."""
        return DiarizationWorker(
            audio_path=pathlib.Path("/tmp/test.wav"),
            segments=[{"start": 0.0, "end": 5.0, "text": "Hello"}],
            hf_token="fake-token",
        )

    def test_coreml_success_returns_pipeline(self, tmp_path: pathlib.Path) -> None:
        """coremltools 사용 가능하고 변환 성공 시 파이프라인 반환."""
        worker = self._make_worker()

        mock_ct = MagicMock()
        mock_pipeline = MagicMock()
        mock_torch = MagicMock()

        # Simulate segmentation model
        mock_seg_model = MagicMock()
        mock_pipeline._segmentation.model = mock_seg_model

        with patch(
            "meeting_transcriber.core.diarizer.DIARIZATION_COREML_DIR",
            tmp_path / "coreml",
        ):
            result = worker._try_coreml_pipeline(mock_pipeline, mock_torch, mock_ct)

        assert result is not None

    def test_coreml_no_coremltools_returns_none(self) -> None:
        """coremltools 미설치 시 None 반환."""
        worker = self._make_worker()
        mock_pipeline = MagicMock()
        mock_torch = MagicMock()

        result = worker._try_coreml_pipeline(mock_pipeline, mock_torch, None)

        assert result is None

    def test_coreml_conversion_failure_returns_none(self, tmp_path: pathlib.Path) -> None:
        """coremltools 변환 실패 시 None 반환."""
        worker = self._make_worker()

        mock_ct = MagicMock()
        mock_ct.convert.side_effect = RuntimeError("Unsupported operation")
        mock_pipeline = MagicMock()
        mock_torch = MagicMock()

        # Make traced model raise during convert
        mock_seg_model = MagicMock()
        mock_pipeline._segmentation.model = mock_seg_model

        with patch(
            "meeting_transcriber.core.diarizer.DIARIZATION_COREML_DIR",
            tmp_path / "coreml",
        ):
            result = worker._try_coreml_pipeline(mock_pipeline, mock_torch, mock_ct)

        assert result is None

    def test_coreml_uses_cached_model(self, tmp_path: pathlib.Path) -> None:
        """캐시된 CoreML 모델 존재 시 변환 건너뛰기."""
        worker = self._make_worker()

        mock_ct = MagicMock()
        mock_pipeline = MagicMock()
        mock_torch = MagicMock()

        # Create cached model file
        coreml_dir = tmp_path / "coreml"
        coreml_dir.mkdir(parents=True)
        cached_model = coreml_dir / "segmentation.mlpackage"
        cached_model.mkdir()  # mlpackage is a directory

        with patch(
            "meeting_transcriber.core.diarizer.DIARIZATION_COREML_DIR",
            tmp_path / "coreml",
        ):
            result = worker._try_coreml_pipeline(mock_pipeline, mock_torch, mock_ct)

        assert result is not None
        # Should NOT have called convert since cache exists
        mock_ct.convert.assert_not_called()

    def test_coreml_worker_run_uses_coreml_when_available(
        self, qtbot: object
    ) -> None:
        """CoreML 성공 시 run()에서 CoreML 경로 사용."""
        worker = self._make_worker()

        mock_pipeline_cls = MagicMock()
        mock_pipeline = MagicMock()
        mock_pipeline_cls.from_pretrained.return_value = mock_pipeline
        mock_diarization = MagicMock()
        mock_diarization.itertracks.return_value = []
        mock_pipeline.return_value = mock_diarization
        mock_torch = MagicMock()

        progress_msgs: list[str] = []
        worker.progress.connect(progress_msgs.append)

        with (
            patch(
                "meeting_transcriber.core.diarizer._import_pipeline",
                return_value=mock_pipeline_cls,
            ),
            patch(
                "meeting_transcriber.core.diarizer._import_torch",
                return_value=mock_torch,
            ),
            patch.object(DiarizationModelManager, "is_model_cached", return_value=True),
            patch.object(
                DiarizationWorker,
                "_try_coreml_pipeline",
                return_value=mock_pipeline,
            ),
        ):
            worker.run()

        assert "Identifying speakers (CoreML)..." in progress_msgs

    def test_coreml_worker_run_falls_back_to_cpu(self, qtbot: object) -> None:
        """CoreML 실패 시 run()에서 CPU 폴백 사용."""
        worker = self._make_worker()

        mock_pipeline_cls = MagicMock()
        mock_pipeline = MagicMock()
        mock_pipeline_cls.from_pretrained.return_value = mock_pipeline
        mock_diarization = MagicMock()
        mock_diarization.itertracks.return_value = []
        mock_pipeline.return_value = mock_diarization
        mock_torch = MagicMock()

        progress_msgs: list[str] = []
        worker.progress.connect(progress_msgs.append)

        with (
            patch(
                "meeting_transcriber.core.diarizer._import_pipeline",
                return_value=mock_pipeline_cls,
            ),
            patch(
                "meeting_transcriber.core.diarizer._import_torch",
                return_value=mock_torch,
            ),
            patch.object(DiarizationModelManager, "is_model_cached", return_value=True),
            patch.object(
                DiarizationWorker,
                "_try_coreml_pipeline",
                return_value=None,
            ),
        ):
            worker.run()

        assert "Identifying speakers..." in progress_msgs
        # Should NOT have the CoreML progress message
        assert "Identifying speakers (CoreML)..." not in progress_msgs
