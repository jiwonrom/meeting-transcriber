"""화자 분리 -- pyannote.audio 파이프라인 실행 및 세그먼트 정렬."""

from __future__ import annotations

import pathlib
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

from meeting_transcriber.utils.constants import (
    DIARIZATION_CACHE_DIR,
    DIARIZATION_DEVICE,
    DIARIZATION_MODEL,
)


def _import_pipeline() -> Any:
    """pyannote.audio Pipeline을 lazy import한다.

    Returns:
        pyannote.audio.Pipeline 클래스
    """
    from pyannote.audio import Pipeline  # noqa: I001

    return Pipeline


def _import_torch() -> Any:
    """torch를 lazy import한다.

    Returns:
        torch 모듈
    """
    import torch  # noqa: I001

    return torch


def align_speakers(
    diarization_turns: list[dict[str, Any]],
    segments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """화자 분리 결과를 전사 세그먼트에 정렬한다.

    각 세그먼트에 대해 최대 시간 겹침을 가진 화자 턴의 화자를 할당한다.

    Args:
        diarization_turns: 화자 턴 리스트 ({"start": float, "end": float, "speaker": str})
        segments: 전사 세그먼트 리스트 ({"start": float, "end": float, "text": str, ...})

    Returns:
        화자가 할당된 세그먼트 리스트 (각 세그먼트에 "speaker" 키 추가)
    """
    for seg in segments:
        seg_start = seg["start"]
        seg_end = seg["end"]
        best_speaker = ""
        best_overlap = 0.0

        for turn in diarization_turns:
            overlap = max(0.0, min(seg_end, turn["end"]) - max(seg_start, turn["start"]))
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = turn["speaker"]

        seg["speaker"] = best_speaker

    return segments


def rename_speaker(
    transcript: dict[str, Any],
    old_label: str,
    new_name: str,
) -> dict[str, Any]:
    """트랜스크립트에서 화자 이름을 변경한다.

    세그먼트와 메타데이터의 speakers 딕셔너리 모두 업데이트한다.

    Args:
        transcript: 트랜스크립트 딕셔너리
        old_label: 기존 화자 라벨
        new_name: 새 화자 이름

    Returns:
        수정된 트랜스크립트 딕셔너리
    """
    # 메타데이터 speakers 딕셔너리 업데이트
    speakers = transcript.get("metadata", {}).get("speakers", {})
    if old_label in speakers:
        speakers[old_label] = new_name

    # 세그먼트 화자 라벨 업데이트
    for seg in transcript.get("segments", []):
        if seg.get("speaker") == old_label:
            seg["speaker"] = new_name

    return transcript


class DiarizationModelManager:
    """pyannote 모델 캐시 관리자.

    HuggingFace Hub 캐시 디렉토리를 확인하여 모델 다운로드 여부를 판단한다.
    """

    def __init__(self, cache_dir: pathlib.Path = DIARIZATION_CACHE_DIR) -> None:
        """DiarizationModelManager를 초기화한다.

        Args:
            cache_dir: 모델 캐시 디렉토리 경로
        """
        self._cache_dir = cache_dir

    def is_model_cached(self) -> bool:
        """모델이 캐시되어 있는지 확인한다.

        HuggingFace Hub 캐시 구조에서 모델 스냅샷 존재 여부를 확인한다.
        캐시 디렉토리 또는 기본 HuggingFace 캐시를 모두 확인한다.

        Returns:
            모델 캐시 존재 시 True
        """
        # Check in provided cache dir (HuggingFace hub structure)
        model_dir = self._cache_dir / "models--pyannote--speaker-diarization-community-1"
        snapshots = model_dir / "snapshots"
        if snapshots.exists():
            # Check if any snapshot directory has files
            for snapshot in snapshots.iterdir():
                if snapshot.is_dir() and any(snapshot.iterdir()):
                    return True

        # Check default HuggingFace cache
        default_cache = pathlib.Path.home() / ".cache" / "huggingface" / "hub"
        default_model = default_cache / "models--pyannote--speaker-diarization-community-1"
        default_snapshots = default_model / "snapshots"
        if default_snapshots.exists():
            for snapshot in default_snapshots.iterdir():
                if snapshot.is_dir() and any(snapshot.iterdir()):
                    return True

        return False

    def get_cache_dir(self) -> pathlib.Path:
        """캐시 디렉토리를 반환한다. 없으면 생성한다.

        Returns:
            캐시 디렉토리 경로
        """
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        return self._cache_dir


class DiarizationWorker(QThread):
    """화자 분리 워커 스레드.

    pyannote.audio 파이프라인을 별도 스레드에서 실행하여 메인 스레드 블로킹을 방지한다.
    완료 시 화자 라벨이 할당된 세그먼트를 finished 시그널로 emit한다.
    """

    progress = pyqtSignal(str)
    finished = pyqtSignal(object)

    def __init__(
        self,
        audio_path: pathlib.Path,
        segments: list[dict[str, Any]],
        hf_token: str,
        parent: Any = None,
    ) -> None:
        """DiarizationWorker를 초기화한다.

        Args:
            audio_path: 오디오 파일 경로
            segments: 전사 세그먼트 리스트
            hf_token: HuggingFace 인증 토큰
            parent: Qt 부모 객체
        """
        super().__init__(parent)
        self._audio_path = audio_path
        self._segments = segments
        self._hf_token = hf_token

    def run(self) -> None:
        """pyannote 파이프라인을 실행하고 결과를 시그널로 emit한다."""
        try:
            self.progress.emit("Identifying speakers...")

            # Lazy imports -- pyannote와 torch는 run() 내에서만 import
            pipeline_cls = _import_pipeline()
            torch = _import_torch()

            # 모델 캐시 확인
            model_mgr = DiarizationModelManager()
            was_cached = model_mgr.is_model_cached()

            if not was_cached:
                self.progress.emit("Downloading speaker identification model...")

            # 파이프라인 로드 (미캐시 시 자동 다운로드)
            pipeline = pipeline_cls.from_pretrained(
                DIARIZATION_MODEL,
                token=self._hf_token,
            )
            pipeline.to(torch.device(DIARIZATION_DEVICE))

            if not was_cached:
                self.progress.emit("Identifying speakers...")

            # 화자 분리 실행
            diarization = pipeline(str(self._audio_path))

            # 결과 추출
            turns: list[dict[str, Any]] = []
            for turn, _track, speaker in diarization.itertracks(yield_label=True):
                turns.append({
                    "start": turn.start,
                    "end": turn.end,
                    "speaker": speaker,
                })

            # 세그먼트에 화자 정렬
            labeled_segments = align_speakers(turns, self._segments)
            self.finished.emit(labeled_segments)

        except Exception as e:
            self.finished.emit(e)
