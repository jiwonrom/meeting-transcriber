"""실시간 마이크 오디오 캡처 — sounddevice + QThread."""
from __future__ import annotations

import io
import queue
import wave
from dataclasses import dataclass
from typing import Any

import numpy as np
import sounddevice as sd
from PyQt6.QtCore import QThread, QTimer, pyqtSignal

from meeting_transcriber.utils.constants import (
    AUDIO_CHANNELS,
    AUDIO_CHUNK_SECONDS,
    AUDIO_LEVEL_INTERVAL_MS,
    AUDIO_SAMPLE_RATE,
    AUDIO_VAD_THRESHOLD,
)


@dataclass(frozen=True)
class AudioDeviceInfo:
    """오디오 입력 장치 정보."""

    index: int
    name: str
    channels: int
    sample_rate: float
    is_default: bool


def list_audio_devices() -> list[AudioDeviceInfo]:
    """사용 가능한 오디오 입력 장치 목록을 반환한다.

    Returns:
        입력 채널이 1개 이상인 장치 정보 리스트
    """
    devices: list[AudioDeviceInfo] = []
    try:
        all_devices = sd.query_devices()
    except sd.PortAudioError:
        return devices

    default_input = sd.default.device[0] if isinstance(sd.default.device, tuple) else None

    if isinstance(all_devices, dict):
        all_devices = [all_devices]

    for i, dev in enumerate(all_devices):
        max_input = dev.get("max_input_channels", 0)
        if max_input < 1:
            continue
        devices.append(AudioDeviceInfo(
            index=i,
            name=dev.get("name", f"Device {i}"),
            channels=max_input,
            sample_rate=dev.get("default_samplerate", 44100.0),
            is_default=(i == default_input),
        ))

    return devices


def encode_wav_chunk(
    chunk: np.ndarray,
    sample_rate: int = AUDIO_SAMPLE_RATE,
) -> bytes:
    """float32 ndarray를 WAV 바이트로 인코딩한다.

    Args:
        chunk: float32 mono 오디오 데이터 (-1.0 ~ 1.0)
        sample_rate: 샘플링 레이트

    Returns:
        WAV 포맷 바이트 데이터
    """
    buf = io.BytesIO()
    int16_data = np.clip(chunk, -1.0, 1.0)
    int16_data = (int16_data * 32767).astype(np.int16)

    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(int16_data.tobytes())

    return buf.getvalue()


class AudioCaptureWorker(QThread):
    """실시간 마이크 캡처 워커 스레드.

    sounddevice InputStream을 열고 2초 청크 단위로 오디오를 버퍼링한다.
    PortAudio 콜백 -> queue.Queue -> QTimer(50ms) drain -> 버퍼 누적 -> Signal emit.
    """

    capture_started = pyqtSignal()
    capture_stopped = pyqtSignal()
    chunk_ready = pyqtSignal(np.ndarray)
    silence_detected = pyqtSignal()
    level_changed = pyqtSignal(float)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        device: int | str | None = None,
        sample_rate: int = AUDIO_SAMPLE_RATE,
        channels: int = AUDIO_CHANNELS,
        chunk_seconds: float = AUDIO_CHUNK_SECONDS,
        vad_threshold: float = AUDIO_VAD_THRESHOLD,
        parent: Any = None,
    ) -> None:
        """AudioCaptureWorker를 초기화한다.

        Args:
            device: sounddevice 장치 식별자 (None이면 시스템 기본)
            sample_rate: 샘플링 레이트 (기본 16000)
            channels: 채널 수 (기본 1, mono)
            chunk_seconds: 청크 크기 (초, 기본 2.0)
            vad_threshold: VAD RMS 임계값 (기본 0.01)
            parent: Qt 부모 객체
        """
        super().__init__(parent)
        self._device = device
        self._sample_rate = sample_rate
        self._channels = channels
        self._chunk_seconds = chunk_seconds
        self._vad_threshold = vad_threshold

        self._chunk_size = int(sample_rate * chunk_seconds)
        self._queue: queue.Queue[np.ndarray] = queue.Queue()
        self._buffer = np.zeros(self._chunk_size, dtype=np.float32)
        self._write_pos = 0
        self._chunks: list[np.ndarray] = []
        self._running = False
        self._level_sample_count = 0
        self._level_interval_samples = int(
            sample_rate * AUDIO_LEVEL_INTERVAL_MS / 1000
        )

    def run(self) -> None:
        """QThread 진입점. InputStream을 열고 이벤트 루프를 실행한다."""
        stream: sd.InputStream | None = None
        timer: QTimer | None = None

        try:
            stream = sd.InputStream(
                device=self._device,
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype="float32",
                callback=self._audio_callback,
            )
            stream.start()
            self._running = True
            self.capture_started.emit()

            timer = QTimer()
            timer.setInterval(50)
            timer.timeout.connect(self._drain_queue)
            timer.start()

            # QThread 이벤트 루프 — quit() 호출까지 블록
            self._event_loop()

        except sd.PortAudioError as e:
            err_msg = str(e)
            if "permission" in err_msg.lower() or "denied" in err_msg.lower():
                self.error_occurred.emit(
                    "Microphone access denied. "
                    "Open System Settings > Privacy & Security > Microphone."
                )
            else:
                self.error_occurred.emit(f"Audio device error: {err_msg}")
        except Exception as e:
            self.error_occurred.emit(f"Audio capture error: {e}")
        finally:
            self._running = False
            if timer is not None:
                timer.stop()
            if stream is not None:
                stream.stop()
                stream.close()
            self.capture_stopped.emit()

    def _event_loop(self) -> None:
        """QThread 내부 이벤트 루프를 실행한다. quit() 호출 시 반환."""
        loop = self.thread()  # noqa: F841 — keep reference
        # QThread.exec() 호출로 이벤트 루프 시작
        super().exec()

    def stop(self) -> None:
        """캡처를 중지한다."""
        self._running = False
        self.quit()

    def get_full_recording(self) -> np.ndarray:
        """전체 녹음 데이터를 반환한다.

        stop() 호출 후에 사용해야 스레드 안전하다.

        Returns:
            캡처된 모든 청크를 결합한 float32 ndarray. 녹음이 없으면 빈 배열.
        """
        chunks = list(self._chunks)  # 스냅샷 복사
        if not chunks:
            return np.array([], dtype=np.float32)
        return np.concatenate(chunks)

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: Any,
        status: sd.CallbackFlags,
    ) -> None:
        """PortAudio 콜백. lock-free로 queue에만 put한다."""
        if self._running:
            self._queue.put_nowait(indata[:, 0].copy())

    def _drain_queue(self) -> None:
        """QTimer에서 호출. queue의 데이터를 버퍼에 누적하고 청크 완성 시 emit한다."""
        while not self._queue.empty():
            try:
                data = self._queue.get_nowait()
            except queue.Empty:
                break

            remaining = len(data)
            offset = 0

            while remaining > 0:
                space = self._chunk_size - self._write_pos
                to_copy = min(remaining, space)

                self._buffer[self._write_pos : self._write_pos + to_copy] = (
                    data[offset : offset + to_copy]
                )
                self._write_pos += to_copy
                offset += to_copy
                remaining -= to_copy

                self._level_sample_count += to_copy
                if self._level_sample_count >= self._level_interval_samples:
                    rms = float(np.sqrt(np.mean(
                        self._buffer[: self._write_pos] ** 2
                    )))
                    self.level_changed.emit(min(rms, 1.0))
                    self._level_sample_count = 0

                if self._write_pos >= self._chunk_size:
                    self._emit_chunk()

    def _emit_chunk(self) -> None:
        """완성된 2초 청크를 Signal로 emit하고 버퍼를 리셋한다."""
        chunk = self._buffer.copy()
        self._chunks.append(chunk)

        rms = float(np.sqrt(np.mean(chunk ** 2)))

        if rms > self._vad_threshold:
            self.chunk_ready.emit(chunk)
        else:
            self.silence_detected.emit()

        self._buffer = np.zeros(self._chunk_size, dtype=np.float32)
        self._write_pos = 0
