"""system_audio 모듈 단위 테스트."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from meeting_transcriber.utils.exceptions import SystemAudioError


# -- detect_blackhole 테스트 --


def test_detect_blackhole_found() -> None:
    """BlackHole 2ch가 장치 목록에 있을 때 인덱스를 반환하는지 확인."""
    fake_devices = [
        {"name": "MacBook Pro Microphone", "max_input_channels": 1},
        {"name": "BlackHole 2ch", "max_input_channels": 2},
        {"name": "Speaker", "max_input_channels": 0},
    ]
    with patch("meeting_transcriber.core.system_audio.sd.query_devices", return_value=fake_devices):
        from meeting_transcriber.core.system_audio import detect_blackhole

        result = detect_blackhole()
    assert result == 1


def test_detect_blackhole_not_installed() -> None:
    """BlackHole이 없을 때 None을 반환하는지 확인."""
    fake_devices = [
        {"name": "MacBook Pro Microphone", "max_input_channels": 1},
        {"name": "Speaker", "max_input_channels": 0},
    ]
    with patch("meeting_transcriber.core.system_audio.sd.query_devices", return_value=fake_devices):
        from meeting_transcriber.core.system_audio import detect_blackhole

        result = detect_blackhole()
    assert result is None


def test_detect_blackhole_portaudio_error() -> None:
    """PortAudioError 발생 시 None을 반환하는지 확인."""
    import sounddevice as sd

    with patch(
        "meeting_transcriber.core.system_audio.sd.query_devices",
        side_effect=sd.PortAudioError("No audio"),
    ):
        from meeting_transcriber.core.system_audio import detect_blackhole

        result = detect_blackhole()
    assert result is None


def test_detect_blackhole_single_device_dict() -> None:
    """query_devices가 dict(단일 장치)를 반환할 때 올바르게 처리하는지 확인."""
    fake_device = {"name": "BlackHole 16ch", "max_input_channels": 16}
    with patch("meeting_transcriber.core.system_audio.sd.query_devices", return_value=fake_device):
        from meeting_transcriber.core.system_audio import detect_blackhole

        result = detect_blackhole()
    assert result == 0


# -- is_blackhole_installed 테스트 --


def test_is_blackhole_installed_true() -> None:
    """BlackHole이 있을 때 True를 반환하는지 확인."""
    with patch("meeting_transcriber.core.system_audio.detect_blackhole", return_value=1):
        from meeting_transcriber.core.system_audio import is_blackhole_installed

        assert is_blackhole_installed() is True


def test_is_blackhole_installed_false() -> None:
    """BlackHole이 없을 때 False를 반환하는지 확인."""
    with patch("meeting_transcriber.core.system_audio.detect_blackhole", return_value=None):
        from meeting_transcriber.core.system_audio import is_blackhole_installed

        assert is_blackhole_installed() is False


# -- get_device_uid 테스트 --


def test_get_device_uid_success() -> None:
    """장치 UID를 올바르게 반환하는지 확인."""
    mock_core_audio = MagicMock()
    mock_core_audio.AudioObjectGetPropertyData.return_value = (0, "UID-Test-Device")
    mock_core_audio.kAudioDevicePropertyDeviceUID = 1969841266
    mock_core_audio.kAudioObjectPropertyScopeGlobal = 1735159650
    mock_core_audio.AudioObjectPropertyAddress = MagicMock(return_value="fake_address")

    with patch.dict("sys.modules", {"CoreAudio": mock_core_audio}):
        from meeting_transcriber.core.system_audio import get_device_uid

        uid = get_device_uid(42)
    assert uid == "UID-Test-Device"


def test_get_device_uid_failure() -> None:
    """CoreAudio 호출 실패 시 SystemAudioError를 발생시키는지 확인."""
    mock_core_audio = MagicMock()
    mock_core_audio.AudioObjectGetPropertyData.return_value = (-50, None)
    mock_core_audio.kAudioDevicePropertyDeviceUID = 1969841266
    mock_core_audio.kAudioObjectPropertyScopeGlobal = 1735159650
    mock_core_audio.AudioObjectPropertyAddress = MagicMock(return_value="fake_address")

    with patch.dict("sys.modules", {"CoreAudio": mock_core_audio}):
        from meeting_transcriber.core.system_audio import get_device_uid

        with pytest.raises(SystemAudioError, match="Failed to get device UID"):
            get_device_uid(42)


# -- create_aggregate_device 테스트 --


def test_create_aggregate_device_success() -> None:
    """Aggregate Device 생성 성공 시 device_id를 반환하는지 확인."""
    mock_core_audio = MagicMock()
    mock_core_audio.AudioHardwareCreateAggregateDevice.return_value = (0, 42)
    mock_core_audio.kAudioAggregateDeviceNameKey = "name"
    mock_core_audio.kAudioAggregateDeviceUIDKey = "uid"
    mock_core_audio.kAudioAggregateDeviceIsPrivateKey = "private"
    mock_core_audio.kAudioAggregateDeviceSubDeviceListKey = "subdevices"
    mock_core_audio.kAudioSubDeviceUIDKey = "subuid"
    mock_core_audio.kAudioAggregateDeviceMasterSubDeviceKey = "master"

    with patch.dict("sys.modules", {"CoreAudio": mock_core_audio}):
        from meeting_transcriber.core.system_audio import create_aggregate_device

        device_id = create_aggregate_device("mic-uid", "blackhole-uid")
    assert device_id == 42


def test_create_aggregate_device_failure() -> None:
    """Aggregate Device 생성 실패 시 SystemAudioError를 발생시키는지 확인."""
    mock_core_audio = MagicMock()
    mock_core_audio.AudioHardwareCreateAggregateDevice.return_value = (-50, 0)
    mock_core_audio.kAudioAggregateDeviceNameKey = "name"
    mock_core_audio.kAudioAggregateDeviceUIDKey = "uid"
    mock_core_audio.kAudioAggregateDeviceIsPrivateKey = "private"
    mock_core_audio.kAudioAggregateDeviceSubDeviceListKey = "subdevices"
    mock_core_audio.kAudioSubDeviceUIDKey = "subuid"
    mock_core_audio.kAudioAggregateDeviceMasterSubDeviceKey = "master"

    with patch.dict("sys.modules", {"CoreAudio": mock_core_audio}):
        from meeting_transcriber.core.system_audio import create_aggregate_device

        with pytest.raises(SystemAudioError, match="Failed to create Aggregate Device"):
            create_aggregate_device("mic-uid", "blackhole-uid")


# -- destroy_aggregate_device 테스트 --


def test_destroy_aggregate_device_success() -> None:
    """Aggregate Device 해제가 예외 없이 완료되는지 확인."""
    mock_core_audio = MagicMock()
    mock_core_audio.AudioHardwareDestroyAggregateDevice.return_value = 0

    with patch.dict("sys.modules", {"CoreAudio": mock_core_audio}):
        from meeting_transcriber.core.system_audio import destroy_aggregate_device

        destroy_aggregate_device(42)
    mock_core_audio.AudioHardwareDestroyAggregateDevice.assert_called_once_with(42)


def test_destroy_aggregate_device_error_no_raise() -> None:
    """Aggregate Device 해제 실패 시에도 예외가 발생하지 않는지 확인."""
    mock_core_audio = MagicMock()
    mock_core_audio.AudioHardwareDestroyAggregateDevice.return_value = -50

    with patch.dict("sys.modules", {"CoreAudio": mock_core_audio}):
        from meeting_transcriber.core.system_audio import destroy_aggregate_device

        # Should not raise
        destroy_aggregate_device(42)


# -- resolve_device_by_uid 테스트 --


def test_resolve_device_by_uid_found() -> None:
    """UID로 장치를 찾을 때 올바른 인덱스를 반환하는지 확인."""
    fake_devices = [
        {"name": "Mic", "max_input_channels": 1},
        {"name": "BlackHole 2ch", "max_input_channels": 2},
    ]
    with (
        patch(
            "meeting_transcriber.core.system_audio.sd.query_devices",
            return_value=fake_devices,
        ),
        patch(
            "meeting_transcriber.core.system_audio.get_device_uid",
            side_effect=lambda idx: {0: "uid-mic", 1: "uid-blackhole"}[idx],
        ),
    ):
        from meeting_transcriber.core.system_audio import resolve_device_by_uid

        result = resolve_device_by_uid("uid-blackhole")
    assert result == 1


def test_resolve_device_by_uid_not_found() -> None:
    """UID가 일치하는 장치가 없을 때 None을 반환하는지 확인."""
    fake_devices = [
        {"name": "Mic", "max_input_channels": 1},
    ]
    with (
        patch(
            "meeting_transcriber.core.system_audio.sd.query_devices",
            return_value=fake_devices,
        ),
        patch(
            "meeting_transcriber.core.system_audio.get_device_uid",
            return_value="uid-mic",
        ),
    ):
        from meeting_transcriber.core.system_audio import resolve_device_by_uid

        result = resolve_device_by_uid("uid-nonexistent")
    assert result is None
