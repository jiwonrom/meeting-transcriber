"""시스템 오디오 캡처 -- BlackHole 감지, Aggregate Device 생성/해제, 장치 UID 해석."""
from __future__ import annotations

import logging

import sounddevice as sd

from meeting_transcriber.utils.constants import (
    AGGREGATE_DEVICE_NAME,
    AGGREGATE_DEVICE_UID,
    BLACKHOLE_DEVICE_NAMES,
)
from meeting_transcriber.utils.exceptions import SystemAudioError

logger = logging.getLogger(__name__)


def detect_blackhole() -> int | None:
    """BlackHole 가상 오디오 장치의 인덱스를 반환한다.

    sounddevice가 열거하는 장치 목록에서 BlackHole을 이름으로 검색한다.
    미설치 시 None을 반환한다.

    Returns:
        BlackHole 장치 인덱스, 또는 미설치 시 None
    """
    try:
        devices = sd.query_devices()
    except sd.PortAudioError:
        return None

    if isinstance(devices, dict):
        devices = [devices]

    for i, dev in enumerate(devices):
        name = dev.get("name", "").lower()
        if (
            any(bh in name for bh in BLACKHOLE_DEVICE_NAMES)
            and dev.get("max_input_channels", 0) > 0
        ):
            return i
    return None


def is_blackhole_installed() -> bool:
    """BlackHole 가상 오디오 드라이버 설치 여부를 반환한다.

    Returns:
        BlackHole이 설치되어 있으면 True
    """
    return detect_blackhole() is not None


def get_device_uid(device_index: int) -> str:
    """CoreAudio 장치 UID 문자열을 반환한다.

    Args:
        device_index: sounddevice 장치 인덱스

    Returns:
        CoreAudio 장치 UID 문자열

    Raises:
        SystemAudioError: UID 조회 실패 시
    """
    import CoreAudio  # noqa: N811 — lazy import, pyobjc may not be installed

    address = CoreAudio.AudioObjectPropertyAddress(
        CoreAudio.kAudioDevicePropertyDeviceUID,
        CoreAudio.kAudioObjectPropertyScopeGlobal,
        0,
    )
    err, uid = CoreAudio.AudioObjectGetPropertyData(
        device_index, address, 0, None, None
    )
    if err != 0:
        raise SystemAudioError(
            f"Failed to get device UID for device {device_index} (OSStatus {err})"
        )
    return str(uid)


def create_aggregate_device(mic_uid: str, blackhole_uid: str) -> int:
    """Aggregate Device를 생성하여 마이크와 BlackHole을 결합한다.

    Args:
        mic_uid: 마이크 장치 CoreAudio UID
        blackhole_uid: BlackHole 장치 CoreAudio UID

    Returns:
        생성된 Aggregate Device의 AudioDeviceID

    Raises:
        SystemAudioError: Aggregate Device 생성 실패 시
    """
    import CoreAudio  # noqa: N811 — lazy import

    description = {
        CoreAudio.kAudioAggregateDeviceNameKey: AGGREGATE_DEVICE_NAME,
        CoreAudio.kAudioAggregateDeviceUIDKey: AGGREGATE_DEVICE_UID,
        CoreAudio.kAudioAggregateDeviceIsPrivateKey: 1,
        CoreAudio.kAudioAggregateDeviceSubDeviceListKey: [
            {CoreAudio.kAudioSubDeviceUIDKey: mic_uid},
            {CoreAudio.kAudioSubDeviceUIDKey: blackhole_uid},
        ],
        CoreAudio.kAudioAggregateDeviceMasterSubDeviceKey: blackhole_uid,
    }

    err, device_id = CoreAudio.AudioHardwareCreateAggregateDevice(
        description, None
    )
    if err != 0:
        raise SystemAudioError(
            f"Failed to create Aggregate Device (OSStatus {err})"
        )
    logger.info("Aggregate Device created: id=%d, name=%s", device_id, AGGREGATE_DEVICE_NAME)
    return device_id


def destroy_aggregate_device(device_id: int) -> None:
    """Aggregate Device를 해제한다.

    정리 작업이므로 실패해도 예외를 발생시키지 않는다.

    Args:
        device_id: 해제할 Aggregate Device의 AudioDeviceID
    """
    import CoreAudio  # noqa: N811 — lazy import

    err = CoreAudio.AudioHardwareDestroyAggregateDevice(device_id)
    if err != 0:
        logger.warning(
            "Failed to destroy Aggregate Device %d (OSStatus %d)", device_id, err
        )
    else:
        logger.info("Aggregate Device %d destroyed", device_id)


def resolve_device_by_uid(uid: str) -> int | None:
    """CoreAudio UID로 장치 인덱스를 찾는다.

    녹음 시작 시 저장된 UID를 실제 장치 인덱스로 변환하는 데 사용한다.
    장치 인덱스는 재부팅/장치 연결 시 변경될 수 있으므로 매번 조회해야 한다.

    Args:
        uid: 검색할 CoreAudio 장치 UID 문자열

    Returns:
        일치하는 장치 인덱스, 또는 미발견 시 None
    """
    try:
        devices = sd.query_devices()
    except sd.PortAudioError:
        return None

    if isinstance(devices, dict):
        devices = [devices]

    for i, dev in enumerate(devices):
        if dev.get("max_input_channels", 0) < 1:
            continue
        try:
            device_uid = get_device_uid(i)
            if device_uid == uid:
                return i
        except (SystemAudioError, Exception):
            continue
    return None
