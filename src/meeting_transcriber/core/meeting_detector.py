"""회의 앱 감지 워커 -- 백그라운드 폴링."""

from __future__ import annotations

import time
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

from meeting_transcriber.utils.constants import (
    CHROME_BUNDLE_ID,
    DETECTION_COOLDOWN_SECONDS,
    DETECTION_POLL_INTERVAL_MS,
    KNOWN_CONFERENCING_APPS,
)

# NSWorkspace는 _poll_once() 내에서 lazy import
NSWorkspace: Any = None


class MeetingDetectorWorker(QThread):
    """회의 앱 감지 워커 스레드.

    NSWorkspace를 10초마다 폴링하여 화상 회의 앱 실행을 감지한다.
    Chrome(Meet)은 오디오 활동 휴리스틱을 추가 확인한다.
    전역 쿨다운과 세션별 스누즈로 알림 스팸을 방지한다.
    """

    meeting_detected = pyqtSignal(str, str, str)

    def __init__(self, *, parent: Any = None) -> None:
        """MeetingDetectorWorker를 초기화한다.

        Args:
            parent: Qt 부모 객체
        """
        super().__init__(parent)
        self._running: bool = False
        self._snoozed: set[str] = set()
        self._last_notify_time: float = 0.0
        self._is_recording: bool = False

    def start_detection(self) -> None:
        """감지를 시작한다."""
        self._running = True
        self.start()

    def stop_detection(self) -> None:
        """감지를 중지하고 스레드 종료를 기다린다."""
        self._running = False
        self.wait()

    def set_recording(self, recording: bool) -> None:
        """녹음 상태를 설정한다. 녹음 중에는 감지가 억제된다.

        Args:
            recording: 현재 녹음 중 여부
        """
        self._is_recording = recording

    def snooze(self, bundle_id: str) -> None:
        """특정 앱의 감지를 스누즈한다. 앱이 종료되면 자동 해제된다.

        Args:
            bundle_id: 스누즈할 앱의 번들 ID
        """
        self._snoozed.add(bundle_id)

    def run(self) -> None:
        """QThread 진입점. 폴링 루프를 실행한다."""
        while self._running:
            try:
                self._poll_once()
            except Exception:
                pass  # 감지 실패는 무시 (UI-SPEC error states)
            self.msleep(DETECTION_POLL_INTERVAL_MS)

    def _poll_once(self) -> None:
        """한 번의 폴링 사이클을 실행한다.

        NSWorkspace에서 실행 중인 앱을 가져와 회의 앱 여부를 확인한다.
        쿨다운, 스누즈, 녹음 상태를 고려하여 meeting_detected 시그널을 발신한다.
        """
        global NSWorkspace  # noqa: PLW0603
        if NSWorkspace is None:
            from AppKit import NSWorkspace  # type: ignore[no-redef]

        workspace = NSWorkspace.sharedWorkspace()
        running_apps = workspace.runningApplications()

        # 실행 중인 번들 ID 집합
        running_bids: set[str] = set()
        for app in running_apps:
            bid = app.bundleIdentifier()
            if bid:
                running_bids.add(bid)

        # 스누즈된 앱 중 종료된 앱의 스누즈 해제
        self._snoozed -= (self._snoozed - running_bids)

        # 녹음 중이면 감지 억제 (D-16)
        if self._is_recording:
            return

        # 전역 쿨다운 확인
        if time.time() - self._last_notify_time < DETECTION_COOLDOWN_SECONDS:
            return

        # 회의 앱 감지
        for app in running_apps:
            bid = app.bundleIdentifier()
            if not bid or bid not in KNOWN_CONFERENCING_APPS:
                continue
            if bid in self._snoozed:
                continue

            # Chrome(Meet)은 오디오 활동 확인 필요
            if bid == CHROME_BUNDLE_ID:
                if not self._check_audio_activity():
                    continue

            self.meeting_detected.emit(
                app.localizedName(),
                KNOWN_CONFERENCING_APPS[bid],
                bid,
            )
            self._last_notify_time = time.time()
            return  # 폴링 사이클당 하나의 알림만

    def _check_audio_activity(self) -> bool:
        """마이크 오디오 활동을 확인한다.

        0.5초간 녹음하여 RMS가 임계값을 초과하면 활동으로 판단한다.

        Returns:
            오디오 활동이 감지되면 True
        """
        try:
            import numpy as np
            import sounddevice as sd

            recording = sd.rec(
                int(0.5 * 16000), samplerate=16000, channels=1, dtype="float32"
            )
            sd.wait()
            rms = float(np.sqrt(np.mean(recording**2)))
            return rms > 0.005
        except Exception:
            return False
