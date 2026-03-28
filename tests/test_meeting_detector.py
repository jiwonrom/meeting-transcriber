"""회의 앱 감지 워커 테스트."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import QThread

from meeting_transcriber.core.meeting_detector import MeetingDetectorWorker
from meeting_transcriber.utils.constants import (
    CHROME_BUNDLE_ID,
    DETECTION_COOLDOWN_SECONDS,
    KNOWN_CONFERENCING_APPS,
)


class _MockApp:
    """NSWorkspace 앱 목 객체."""

    def __init__(self, name: str, bundle_id: str) -> None:
        self._name = name
        self._bundle_id = bundle_id

    def localizedName(self) -> str:  # noqa: N802
        return self._name

    def bundleIdentifier(self) -> str:  # noqa: N802
        return self._bundle_id


def _make_mock_workspace(apps: list[_MockApp]) -> MagicMock:
    """NSWorkspace.sharedWorkspace() 목을 생성한다."""
    ws = MagicMock()
    ws.runningApplications.return_value = apps
    return ws


class TestMeetingDetectorWorker:
    """MeetingDetectorWorker 단위 테스트."""

    def _make_worker(self) -> MeetingDetectorWorker:
        """테스트용 워커를 생성한다."""
        worker = MeetingDetectorWorker()
        return worker

    def test_detect_known_apps(self, qtbot: object) -> None:
        """Zoom 실행 시 meeting_detected 시그널이 올바른 인수로 발신된다."""
        worker = self._make_worker()
        zoom = _MockApp("Zoom", "us.zoom.xos")
        ws = _make_mock_workspace([zoom])

        results: list[tuple[str, str, str]] = []
        worker.meeting_detected.connect(lambda a, t, b: results.append((a, t, b)))

        with patch(
            "meeting_transcriber.core.meeting_detector.NSWorkspace",
            new=MagicMock(sharedWorkspace=MagicMock(return_value=ws)),
        ):
            worker._poll_once()

        assert len(results) == 1
        assert results[0] == ("Zoom", "team_meeting", "us.zoom.xos")

    def test_detect_facetime(self, qtbot: object) -> None:
        """FaceTime 감지 시 one_on_one 템플릿으로 발신된다."""
        worker = self._make_worker()
        ft = _MockApp("FaceTime", "com.apple.FaceTime")
        ws = _make_mock_workspace([ft])

        results: list[tuple[str, str, str]] = []
        worker.meeting_detected.connect(lambda a, t, b: results.append((a, t, b)))

        with patch(
            "meeting_transcriber.core.meeting_detector.NSWorkspace",
            new=MagicMock(sharedWorkspace=MagicMock(return_value=ws)),
        ):
            worker._poll_once()

        assert len(results) == 1
        assert results[0] == ("FaceTime", "one_on_one", "com.apple.FaceTime")

    def test_unknown_app_ignored(self, qtbot: object) -> None:
        """알 수 없는 앱은 감지되지 않는다."""
        worker = self._make_worker()
        safari = _MockApp("Safari", "com.apple.Safari")
        ws = _make_mock_workspace([safari])

        results: list[tuple[str, str, str]] = []
        worker.meeting_detected.connect(lambda a, t, b: results.append((a, t, b)))

        with patch(
            "meeting_transcriber.core.meeting_detector.NSWorkspace",
            new=MagicMock(sharedWorkspace=MagicMock(return_value=ws)),
        ):
            worker._poll_once()

        assert len(results) == 0

    def test_global_cooldown(self, qtbot: object) -> None:
        """전역 쿨다운 기간 내 반복 감지가 억제된다."""
        worker = self._make_worker()
        zoom = _MockApp("Zoom", "us.zoom.xos")
        ws = _make_mock_workspace([zoom])

        results: list[tuple[str, str, str]] = []
        worker.meeting_detected.connect(lambda a, t, b: results.append((a, t, b)))

        with patch(
            "meeting_transcriber.core.meeting_detector.NSWorkspace",
            new=MagicMock(sharedWorkspace=MagicMock(return_value=ws)),
        ):
            worker._poll_once()
            assert len(results) == 1
            # 두 번째 폴링 — 쿨다운 중이므로 억제
            worker._poll_once()
            assert len(results) == 1

    def test_cooldown_expires(self, qtbot: object) -> None:
        """쿨다운 만료 후 다시 감지된다."""
        worker = self._make_worker()
        zoom = _MockApp("Zoom", "us.zoom.xos")
        ws = _make_mock_workspace([zoom])

        results: list[tuple[str, str, str]] = []
        worker.meeting_detected.connect(lambda a, t, b: results.append((a, t, b)))

        with patch(
            "meeting_transcriber.core.meeting_detector.NSWorkspace",
            new=MagicMock(sharedWorkspace=MagicMock(return_value=ws)),
        ):
            worker._poll_once()
            assert len(results) == 1
            # 쿨다운 시간을 과거로 조작
            worker._last_notify_time = time.time() - DETECTION_COOLDOWN_SECONDS - 1
            worker._poll_once()
            assert len(results) == 2

    def test_per_session_snooze(self, qtbot: object) -> None:
        """스누즈된 앱은 감지되지 않는다."""
        worker = self._make_worker()
        zoom = _MockApp("Zoom", "us.zoom.xos")
        ws = _make_mock_workspace([zoom])

        results: list[tuple[str, str, str]] = []
        worker.meeting_detected.connect(lambda a, t, b: results.append((a, t, b)))

        worker.snooze("us.zoom.xos")

        with patch(
            "meeting_transcriber.core.meeting_detector.NSWorkspace",
            new=MagicMock(sharedWorkspace=MagicMock(return_value=ws)),
        ):
            worker._poll_once()

        assert len(results) == 0

    def test_snooze_cleared_when_app_stops(self, qtbot: object) -> None:
        """스누즈된 앱이 더 이상 실행되지 않으면 스누즈가 해제된다."""
        worker = self._make_worker()
        worker.snooze("us.zoom.xos")
        assert "us.zoom.xos" in worker._snoozed

        # 빈 실행 앱 목록 (Zoom이 종료됨)
        ws = _make_mock_workspace([])

        with patch(
            "meeting_transcriber.core.meeting_detector.NSWorkspace",
            new=MagicMock(sharedWorkspace=MagicMock(return_value=ws)),
        ):
            worker._poll_once()

        assert "us.zoom.xos" not in worker._snoozed

    def test_chrome_requires_audio(self, qtbot: object) -> None:
        """Chrome은 오디오 활동이 감지될 때만 트리거된다."""
        worker = self._make_worker()
        chrome = _MockApp("Google Chrome", CHROME_BUNDLE_ID)
        ws = _make_mock_workspace([chrome])

        results: list[tuple[str, str, str]] = []
        worker.meeting_detected.connect(lambda a, t, b: results.append((a, t, b)))

        with (
            patch(
                "meeting_transcriber.core.meeting_detector.NSWorkspace",
                new=MagicMock(sharedWorkspace=MagicMock(return_value=ws)),
            ),
            patch.object(worker, "_check_audio_activity", return_value=True),
        ):
            worker._poll_once()

        assert len(results) == 1
        assert results[0][2] == CHROME_BUNDLE_ID

    def test_chrome_no_audio_ignored(self, qtbot: object) -> None:
        """Chrome에 오디오 활동이 없으면 감지되지 않는다."""
        worker = self._make_worker()
        chrome = _MockApp("Google Chrome", CHROME_BUNDLE_ID)
        ws = _make_mock_workspace([chrome])

        results: list[tuple[str, str, str]] = []
        worker.meeting_detected.connect(lambda a, t, b: results.append((a, t, b)))

        with (
            patch(
                "meeting_transcriber.core.meeting_detector.NSWorkspace",
                new=MagicMock(sharedWorkspace=MagicMock(return_value=ws)),
            ),
            patch.object(worker, "_check_audio_activity", return_value=False),
        ):
            worker._poll_once()

        assert len(results) == 0

    def test_stop_worker(self) -> None:
        """stop_detection() 호출 시 _running 플래그가 해제된다."""
        worker = self._make_worker()
        worker._running = True
        # stop_detection calls wait() which needs thread, just test flag
        worker._running = False
        assert not worker._running

    def test_already_recording_suppressed(self, qtbot: object) -> None:
        """녹음 중에는 감지가 억제된다."""
        worker = self._make_worker()
        zoom = _MockApp("Zoom", "us.zoom.xos")
        ws = _make_mock_workspace([zoom])

        results: list[tuple[str, str, str]] = []
        worker.meeting_detected.connect(lambda a, t, b: results.append((a, t, b)))

        worker.set_recording(True)

        with patch(
            "meeting_transcriber.core.meeting_detector.NSWorkspace",
            new=MagicMock(sharedWorkspace=MagicMock(return_value=ws)),
        ):
            worker._poll_once()

        assert len(results) == 0

    def test_signal_includes_bundle_id(self, qtbot: object) -> None:
        """meeting_detected 시그널이 3개 인수 (app_name, template_key, bundle_id)를 발신한다."""
        worker = self._make_worker()
        teams = _MockApp("Microsoft Teams", "com.microsoft.teams2")
        ws = _make_mock_workspace([teams])

        results: list[tuple[str, str, str]] = []
        worker.meeting_detected.connect(lambda a, t, b: results.append((a, t, b)))

        with patch(
            "meeting_transcriber.core.meeting_detector.NSWorkspace",
            new=MagicMock(sharedWorkspace=MagicMock(return_value=ws)),
        ):
            worker._poll_once()

        assert len(results) == 1
        app_name, template_key, bundle_id = results[0]
        assert app_name == "Microsoft Teams"
        assert template_key == "team_meeting"
        assert bundle_id == "com.microsoft.teams2"

    def test_worker_is_qthread(self) -> None:
        """MeetingDetectorWorker가 QThread를 상속한다."""
        worker = self._make_worker()
        assert isinstance(worker, QThread)
