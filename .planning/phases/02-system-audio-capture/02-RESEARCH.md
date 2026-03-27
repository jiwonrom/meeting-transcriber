# Phase 2: System Audio Capture - Research

**Researched:** 2026-03-27
**Domain:** macOS system audio capture via BlackHole virtual audio driver + CoreAudio Aggregate Device
**Confidence:** MEDIUM

## Summary

This phase adds system audio capture to Scribe so users can transcribe the other side of calls. The approach uses BlackHole 2ch as a virtual audio loopback driver, combined with a CoreAudio Aggregate Device that merges the user's microphone and BlackHole into a single input stream. The existing `AudioCaptureWorker` already accepts a `device` parameter and works with any CoreAudio input device, so the core audio pipeline requires no changes.

The primary engineering challenges are: (1) detecting BlackHole installation via `sounddevice.query_devices()`, (2) auto-creating an Aggregate Device via `pyobjc-framework-CoreAudio` using `AudioHardwareCreateAggregateDevice`, and (3) building a setup wizard UI that guides users through BlackHole installation without leaving the app. The Aggregate Device creation via pyobjc is the highest-risk area -- CoreAudio is a low-level C API with no published Python examples, and the pyobjc maintainer has noted uncertainty about whether all CoreAudio APIs work correctly from Python.

**Primary recommendation:** Use `pyobjc-framework-CoreAudio` (v12.1) for Aggregate Device creation, with a fallback path that opens Audio MIDI Setup if programmatic creation fails. Detect BlackHole via existing `list_audio_devices()`. Reuse `AudioCaptureWorker` by switching its `device` parameter to the Aggregate Device index.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** In-app setup wizard with step-by-step instructions + external download link (Homebrew command copy button, or BlackHole GitHub releases page link)
- **D-02:** Aggregate Device auto-creation via CoreAudio API (pyobjc) -- user should NOT need to open Audio MIDI Setup manually
- **D-03:** Toggle switch next to record button for "System Audio" -- ON means capture mic + system simultaneously
- **D-04:** When BlackHole is not installed, toggle is visible but disabled (grayed out). Clicking it opens the installation wizard.
- **D-05:** Single mix -- merge mic + system audio into one stream before sending to whisper. Reuses existing AudioCaptureWorker pipeline.
- **D-06:** Aggregate Device (created in D-02) handles hardware-level mixing -- app opens a single input stream from the Aggregate Device
- **D-07:** App works exactly as before (mic-only mode). System audio features are present but disabled until BlackHole is installed.
- **D-08:** No startup prompt to install BlackHole -- discovery is through the disabled toggle or Preferences
- **D-09:** Claude's Discretion -- volume balance/normalization approach for mic + system mix (auto-normalization recommended)
- **D-10:** Claude's Discretion -- how to visually indicate dual-source capture (dual level meters or badge approach)
- **D-11:** If system audio stream fails mid-recording, microphone recording continues uninterrupted. Status bar shows warning message.
- **D-12:** BlackHole disconnection is non-fatal -- graceful degradation to mic-only

### Claude's Discretion
- Volume balancing/normalization strategy for mic + system audio mix
- Recording status visual indicator design (dual meters vs badge)
- Setup wizard visual design and step layout
- Aggregate Device naming convention

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SYSAUD-01 | App detects whether BlackHole virtual audio driver is installed | BlackHole detection via `list_audio_devices()` checking for "blackhole" in device names -- HIGH confidence, already verified on dev machine |
| SYSAUD-02 | App provides guided setup wizard for BlackHole installation and Aggregate Device creation | OnboardingWizard pattern reusable for 4-step wizard; pyobjc-framework-CoreAudio for Aggregate Device creation -- MEDIUM confidence on pyobjc path |
| SYSAUD-03 | User can select system audio (via BlackHole) as input source alongside microphone | Aggregate Device appears as standard CoreAudio input; AudioCaptureWorker.device parameter switches source -- HIGH confidence |
| SYSAUD-04 | User can capture both microphone and system audio simultaneously (dual-channel) | Aggregate Device handles hardware-level mixing; single AudioCaptureWorker stream from Aggregate Device -- HIGH confidence for audio path, MEDIUM for device creation |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Threading:** All I/O off main thread (QThread or subprocess). BlackHole detection polling and Aggregate Device creation must not block the main thread.
- **Security:** API keys in macOS Keychain only -- not relevant to this phase but must not regress.
- **Testing:** All new public functions need type hints + docstrings. New features require pytest tests.
- **Dependencies:** ui -> core, ui -> ai, ai -> storage (unidirectional). New `core/system_audio.py` module must not import from ui.
- **Naming:** Korean docstrings, PEP8 snake_case, `_on_{event}` signal handler pattern.
- **UI restrictions:** ui/ modules must not call external APIs directly. BlackHole detection logic belongs in core/.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pyobjc-framework-CoreAudio | 12.1 | CoreAudio API bindings for Aggregate Device creation/destruction | Only way to programmatically create Aggregate Devices from Python. Required by D-02. |
| pyobjc-core | 12.1 | Base pyobjc bridge (dependency of framework package) | Required by pyobjc-framework-CoreAudio |
| sounddevice | >=0.4.6 (existing) | Audio capture + device enumeration | Already in stack. BlackHole/Aggregate Devices appear as standard CoreAudio devices. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pyobjc-framework-Cocoa | 12.1 | Foundation framework (NSString, NSDictionary) needed by CoreAudio calls | Transitive dependency, needed for CF type bridging |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pyobjc CoreAudio | Bundled Swift CLI helper | Simpler API but requires compiling/bundling a Swift binary; harder to debug; adds build complexity |
| pyobjc CoreAudio | subprocess + Audio MIDI Setup | Cannot automate -- Audio MIDI Setup has no CLI |
| pyobjc CoreAudio | macos-audio-devices (npm) | Wrong ecosystem (Node.js); would require bundling Node runtime |

**Installation:**
```bash
pip install pyobjc-framework-CoreAudio>=12.0
```

This pulls in `pyobjc-core` and `pyobjc-framework-Cocoa` as transitive dependencies.

**Version verification:** pyobjc-framework-CoreAudio 12.1 is the latest version on PyPI as of 2026-03-27.

## Architecture Patterns

### Recommended Project Structure
```
src/meeting_transcriber/
  core/
    audio_capture.py       # Existing -- no changes needed
    system_audio.py        # NEW: BlackHole detection, Aggregate Device creation/destruction
  ui/
    main_window.py         # Modified: add SystemAudioToggle to control bar
    blackhole_wizard.py    # NEW: 4-step setup wizard (QDialog)
    widgets/
      toggle_switch.py     # NEW: custom toggle widget (QPainter)
      dual_level_meter.py  # NEW: stacked mic + system level meters
    settings_dialog.py     # Modified: add System Audio section to Audio tab
  utils/
    constants.py           # Modified: add system audio constants
    config.py              # No changes -- settings deep-merge handles new keys
```

### Pattern 1: BlackHole Detection (core/system_audio.py)
**What:** Pure function that checks `sounddevice.query_devices()` for BlackHole presence
**When to use:** On app startup (non-blocking), in wizard polling, before recording with system audio enabled
**Example:**
```python
# Source: Verified on dev machine -- BlackHole appears as "BlackHole 2ch" in device list
import sounddevice as sd

def detect_blackhole() -> int | None:
    """BlackHole 장치 인덱스를 반환한다. 미설치 시 None."""
    try:
        devices = sd.query_devices()
    except sd.PortAudioError:
        return None
    if isinstance(devices, dict):
        devices = [devices]
    for i, dev in enumerate(devices):
        name = dev.get("name", "").lower()
        if "blackhole" in name and dev.get("max_input_channels", 0) > 0:
            return i
    return None
```

### Pattern 2: Aggregate Device Creation via pyobjc
**What:** Create a CoreAudio Aggregate Device combining mic + BlackHole using AudioHardwareCreateAggregateDevice
**When to use:** During wizard step 3, when user clicks "Create Aggregate Device"
**Example:**
```python
# Source: Apple CoreAudio docs + Objective-C gist adapted to pyobjc
# Confidence: MEDIUM -- pyobjc CoreAudio has no published Python examples
import CoreAudio  # pyobjc-framework-CoreAudio

def create_aggregate_device(
    name: str,
    uid: str,
    sub_device_uids: list[str],
    master_device_uid: str,
) -> int:
    """Aggregate Device를 생성한다.

    Args:
        name: 장치 표시 이름
        uid: 고유 식별자
        sub_device_uids: 결합할 장치 UID 목록
        master_device_uid: 클럭 마스터 장치 UID

    Returns:
        새 Aggregate Device의 AudioDeviceID

    Raises:
        SystemAudioError: 생성 실패 시
    """
    description = {
        CoreAudio.kAudioAggregateDeviceNameKey: name,
        CoreAudio.kAudioAggregateDeviceUIDKey: uid,
        CoreAudio.kAudioAggregateDeviceIsPrivateKey: 1,
        CoreAudio.kAudioAggregateDeviceSubDeviceListKey: [
            {CoreAudio.kAudioSubDeviceUIDKey: uid_str}
            for uid_str in sub_device_uids
        ],
        CoreAudio.kAudioAggregateDeviceMasterSubDeviceKey: master_device_uid,
    }

    err, device_id = CoreAudio.AudioHardwareCreateAggregateDevice(
        description, None
    )
    if err != 0:
        raise SystemAudioError(f"AudioHardwareCreateAggregateDevice failed: {err}")
    return device_id
```

**CRITICAL NOTE:** The exact pyobjc calling convention for `AudioHardwareCreateAggregateDevice` is unverified. The function takes `(CFDictionaryRef, AudioDeviceID*)` in C. In pyobjc, output parameters are typically returned as part of a tuple. The implementer MUST test this interactively before writing production code:
```python
python3 -c "import CoreAudio; help(CoreAudio.AudioHardwareCreateAggregateDevice)"
```

### Pattern 3: Device UID Resolution
**What:** Get the CoreAudio UID string for a device (needed for Aggregate Device creation)
**When to use:** Before creating the Aggregate Device -- must resolve device index to UID
**Example:**
```python
# Source: CoreAudio API -- AudioObjectGetPropertyData with kAudioDevicePropertyDeviceUID
# The device UID is a CFString, NOT the integer device index

def get_device_uid(device_id: int) -> str:
    """CoreAudio 장치 UID를 반환한다."""
    # Use AudioObjectGetPropertyData with:
    #   selector = kAudioDevicePropertyDeviceUID
    #   scope = kAudioObjectPropertyScopeGlobal
    #   element = kAudioObjectPropertyElementMain
    # Returns CFStringRef
    ...
```

### Pattern 4: Wizard Setup Flow (reuse OnboardingWizard pattern)
**What:** QDialog with QStackedWidget, Back/Next navigation, 4 steps
**When to use:** BlackHoleSetupWizard in `ui/blackhole_wizard.py`
**Example:** Follow exact pattern from `OnboardingWizard`:
- QStackedWidget for pages
- Back/Next buttons in bottom layout
- QTimer polling for detection (step 2)
- QThread for async operations (step 3 Aggregate Device creation)

### Anti-Patterns to Avoid
- **Blocking main thread for device detection:** BlackHole detection via `sd.query_devices()` is fast (<10ms) but Aggregate Device creation involves CoreAudio IPC. Always run creation in a QThread.
- **Creating Aggregate Device on every app launch:** Create once during wizard, persist the device. CoreAudio Aggregate Devices survive reboots if `kAudioAggregateDeviceIsPrivateKey` is 0 (public). With private=1, they only exist while the creating process is alive -- this means the app must recreate on launch if using private devices.
- **Hardcoding BlackHole device index:** Device indices change between reboots and when devices are plugged/unplugged. Always detect by name matching, never cache indices across sessions.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Aggregate Device creation | Custom CoreAudio C extension | pyobjc-framework-CoreAudio | pyobjc bridges all CoreAudio C functions; building a C extension adds massive build complexity |
| Audio stream mixing | Manual numpy array addition of two streams | CoreAudio Aggregate Device (hardware-level mix) | Aggregate Device handles clock sync, drift compensation, and mixing at the HAL layer -- impossible to replicate correctly in userspace |
| BlackHole detection | Custom launchd/kext scanning | `sounddevice.query_devices()` name check | sounddevice already enumerates all CoreAudio devices; BlackHole registers as a standard device |
| Toggle switch widget | QCheckBox with stylesheet hacking | Custom QPainter widget (like RecordButton) | RecordButton pattern already established; QPainter gives pixel-perfect control per UI-SPEC |

**Key insight:** The Aggregate Device does ALL the hard work (clock synchronization, drift compensation, sample rate conversion, mixing). The app just opens a single InputStream from it. This is why D-05 and D-06 are correct -- no application-level mixing code is needed.

## Common Pitfalls

### Pitfall 1: Aggregate Device Persistence
**What goes wrong:** Private Aggregate Devices (isPrivate=1) are destroyed when the creating process exits. On next app launch, the device is gone.
**Why it happens:** CoreAudio private devices are process-scoped.
**How to avoid:** Either (a) use isPrivate=0 so the device persists in Audio MIDI Setup (user-visible, survives reboot), or (b) recreate the Aggregate Device on each app launch using saved UIDs from settings.json. Option (b) is cleaner -- create on launch, destroy on quit.
**Warning signs:** "Device not found" errors after app restart.

### Pitfall 2: Sample Rate Mismatch
**What goes wrong:** Microphone runs at 44100 Hz, BlackHole at 48000 Hz. Aggregate Device creation succeeds but audio is distorted.
**Why it happens:** Aggregate Devices need a master clock device. Sub-devices at different sample rates need drift compensation enabled.
**How to avoid:** Set BlackHole as the master clock device (it runs at whatever rate the app requests). Enable drift compensation on the microphone sub-device. Request 16000 Hz from sounddevice (whisper.cpp expects 16kHz) -- the Aggregate Device will resample.
**Warning signs:** Crackling audio, pitch shifts, buffer underruns.

### Pitfall 3: BlackHole Channel Count
**What goes wrong:** BlackHole 2ch has 2 input channels. Existing AudioCaptureWorker uses `channels=1` (mono). Opening BlackHole with channels=1 may work (sounddevice/PortAudio downmixes) or may fail on some configurations.
**Why it happens:** BlackHole presents stereo I/O.
**How to avoid:** When capturing from Aggregate Device, still request `channels=1`. PortAudio handles downmixing. If issues arise, capture 2 channels and average to mono in the callback.
**Warning signs:** PortAudioError on stream open, or silent second channel.

### Pitfall 4: pyobjc CoreAudio API Uncertainty
**What goes wrong:** `AudioHardwareCreateAggregateDevice` may not work correctly from pyobjc due to the low-level C nature of CoreAudio APIs.
**Why it happens:** pyobjc maintainer has explicitly noted "not yet convinced that the API actually works correctly from Python" for CoreAudio.
**How to avoid:** Implement a fallback path: if pyobjc creation fails, open Audio MIDI Setup with instructions for manual Aggregate Device creation. Test the pyobjc path early (Wave 0 spike) before building the full wizard UI.
**Warning signs:** OSStatus error codes from AudioHardwareCreateAggregateDevice, segfaults, or incorrect device_id return values.

### Pitfall 5: Multi-Output Device vs Aggregate Device Confusion
**What goes wrong:** Users need a Multi-Output Device (so system audio goes to both speakers AND BlackHole) but the app creates an Aggregate Device (for INPUT). These are different things.
**Why it happens:** The user setup has TWO parts: (1) Multi-Output Device for routing system output to BlackHole (user must do this in System Settings > Sound or Audio MIDI Setup), (2) Aggregate Device for combining mic + BlackHole input (app can automate this).
**How to avoid:** The wizard must guide users to set their system output to a Multi-Output Device that includes their speakers + BlackHole. The app automates only the Aggregate INPUT device. Clearly separate these steps in the wizard.
**Warning signs:** User enables system audio toggle but no system audio is captured -- because system output is not routed through BlackHole.

### Pitfall 6: Device Index Volatility
**What goes wrong:** Saved device index becomes invalid after plugging in/removing audio devices.
**Why it happens:** CoreAudio device indices are not stable across configuration changes.
**How to avoid:** Store device UIDs (strings) in settings, not integer indices. Resolve UID to index at recording start time via `sounddevice.query_devices()`.
**Warning signs:** Wrong device selected, or "device not found" errors.

## Code Examples

### BlackHole Detection with Caching
```python
# Source: Existing list_audio_devices() pattern + BlackHole name check
# Confidence: HIGH -- verified on dev machine (device index 1: "BlackHole 2ch")

BLACKHOLE_NAMES = ("blackhole 2ch", "blackhole 16ch", "blackhole 64ch")

def is_blackhole_installed() -> bool:
    """BlackHole 가상 오디오 드라이버 설치 여부를 확인한다."""
    return detect_blackhole() is not None

def detect_blackhole() -> int | None:
    """BlackHole 장치 인덱스를 반환한다. 미설치 시 None."""
    try:
        devices = sd.query_devices()
    except sd.PortAudioError:
        return None
    if isinstance(devices, dict):
        devices = [devices]
    for i, dev in enumerate(devices):
        name = dev.get("name", "").lower()
        if any(bh in name for bh in BLACKHOLE_NAMES) and dev.get("max_input_channels", 0) > 0:
            return i
    return None
```

### Settings Schema Extension
```python
# New keys in _default_settings() audio section:
"audio": {
    "device": None,
    "post_recording": "ask",
    "system_audio": {
        "enabled": False,              # Toggle state
        "blackhole_uid": None,         # Detected BlackHole device UID
        "aggregate_device_uid": None,  # Created Aggregate Device UID
        "mic_device_uid": None,        # Mic device in aggregate
    },
}
```

### Toggle Switch Custom Widget (QPainter pattern)
```python
# Source: RecordButton pattern in main_window.py -- custom QPainter on QWidget
# Follow UI-SPEC: 44x24px, 150ms QPropertyAnimation, PointingHandCursor

class SystemAudioToggle(QWidget):
    """시스템 오디오 토글 스위치."""
    toggled = pyqtSignal(bool)

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self.setFixedSize(44, 24)
        self._checked = False
        self._enabled = True
        self._thumb_position = 0.0  # 0.0 = off, 1.0 = on
        # QPropertyAnimation on _thumb_position for 150ms ease-in-out
```

### Graceful Degradation on Stream Failure
```python
# Source: D-11, D-12 -- microphone continues if system audio fails
# Pattern: catch PortAudioError on Aggregate Device, fall back to mic-only

def start_recording(self) -> None:
    settings = load_settings()
    sys_audio = settings.get("audio", {}).get("system_audio", {})

    if sys_audio.get("enabled") and sys_audio.get("aggregate_device_uid"):
        device = resolve_device_by_uid(sys_audio["aggregate_device_uid"])
        if device is None:
            # Aggregate device not found -- fall back to mic
            self._status_bar.showMessage(
                "System audio disconnected -- continuing with microphone only"
            )
            device = settings.get("audio", {}).get("device")
    else:
        device = settings.get("audio", {}).get("device")

    self._audio_worker = AudioCaptureWorker(device=device)
    # ... connect signals as before
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Soundflower (kernel ext) | BlackHole (Audio Server Plugin) | ~2019 | BlackHole is macOS 12+ compatible, Apple Silicon native |
| Manual Aggregate Device in Audio MIDI Setup | Programmatic via AudioHardwareCreateAggregateDevice | Always available | Users don't need to understand CoreAudio internals |
| ScreenCaptureKit for app audio | BlackHole for system-wide audio | ScreenCaptureKit macOS 13+ | ScreenCaptureKit requires screen recording permission and per-app selection; BlackHole captures all system audio; decision to use BlackHole is locked (STACK.md) |

**Deprecated/outdated:**
- Soundflower: Abandoned since 2014, kernel panics on Apple Silicon
- HAL plugins (old style): Replaced by Audio Server Plugin architecture on macOS 12+

## Open Questions

1. **pyobjc AudioHardwareCreateAggregateDevice calling convention**
   - What we know: The C function takes `(CFDictionaryRef, AudioDeviceID*)`. pyobjc typically returns output params as tuple elements.
   - What's unclear: Exact Python calling convention. No published examples exist. pyobjc maintainer has expressed uncertainty about CoreAudio bindings.
   - Recommendation: Spike test in Wave 0 -- `python3 -c "import CoreAudio; help(CoreAudio.AudioHardwareCreateAggregateDevice)"` to verify function signature. If it doesn't work, fallback to bundling a small Swift CLI helper.

2. **Aggregate Device persistence strategy**
   - What we know: Private devices die with the process. Public devices persist and are visible in Audio MIDI Setup.
   - What's unclear: Whether recreating on every launch causes Audio MIDI Setup clutter or notification spam.
   - Recommendation: Use private (isPrivate=1) and recreate on launch from saved UIDs. This is cleaner -- no leftover devices in the system.

3. **Multi-Output Device automation**
   - What we know: Users need a Multi-Output Device to route system audio to BlackHole. This is a separate device from the Aggregate INPUT device.
   - What's unclear: Can `AudioHardwareCreateAggregateDevice` create Multi-Output Devices too? (Apple docs mention `kAudioAggregateDeviceIsStackedKey` for this purpose.)
   - Recommendation: Research whether the same API can create both. If yes, automate both in the wizard. If no, wizard step must guide user to manually set system output to include BlackHole (via System Settings > Sound).

4. **Volume normalization for mixed audio**
   - What we know: Mic audio and system audio have different gain levels.
   - What's unclear: Whether the Aggregate Device's hardware mixing produces balanced levels, or if software normalization is needed.
   - Recommendation: Start with no normalization (hardware mix as-is). If testing shows imbalance, add RMS-based auto-gain in `_drain_queue()`. This is Claude's Discretion per D-09.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| BlackHole 2ch | System audio capture | Yes (on dev machine) | 2ch variant | Wizard guides installation; app degrades gracefully without it |
| pyobjc-framework-CoreAudio | Aggregate Device creation (D-02) | No (not installed) | Need 12.1 | Must add to dependencies; if API doesn't work from Python, use Swift CLI helper |
| sounddevice | Audio capture + detection | Yes (existing dep) | >=0.4.6 | -- |
| Homebrew | BlackHole installation path | Yes (on dev machine) | -- | GitHub releases download as alternative |

**Missing dependencies with no fallback:**
- `pyobjc-framework-CoreAudio` must be installed. Add to `pyproject.toml` dependencies.

**Missing dependencies with fallback:**
- BlackHole itself -- app works in mic-only mode without it (D-07)

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ with pytest-qt 4.3+ |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `pytest tests/ -x --tb=short -v` |
| Full suite command | `make test` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SYSAUD-01 | detect_blackhole() returns index when BlackHole in device list | unit | `pytest tests/test_system_audio.py::test_detect_blackhole -x` | Wave 0 |
| SYSAUD-01 | detect_blackhole() returns None when not in device list | unit | `pytest tests/test_system_audio.py::test_detect_blackhole_not_installed -x` | Wave 0 |
| SYSAUD-02 | BlackHoleSetupWizard opens and navigates 4 steps | unit (pytest-qt) | `pytest tests/test_blackhole_wizard.py -x` | Wave 0 |
| SYSAUD-02 | Aggregate Device creation function called with correct params | unit (mocked) | `pytest tests/test_system_audio.py::test_create_aggregate_device -x` | Wave 0 |
| SYSAUD-03 | SystemAudioToggle emits toggled signal | unit (pytest-qt) | `pytest tests/test_system_audio_toggle.py -x` | Wave 0 |
| SYSAUD-03 | start_recording uses aggregate device when system audio enabled | unit (mocked) | `pytest tests/test_main_window.py::test_start_recording_system_audio -x` | Wave 0 |
| SYSAUD-04 | Dual recording uses aggregate device index | unit (mocked) | `pytest tests/test_system_audio.py::test_resolve_aggregate_device -x` | Wave 0 |
| SYSAUD-04 | Graceful fallback when aggregate device unavailable | unit | `pytest tests/test_system_audio.py::test_fallback_to_mic -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_system_audio.py tests/test_blackhole_wizard.py -x --tb=short`
- **Per wave merge:** `make test`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_system_audio.py` -- covers SYSAUD-01, SYSAUD-02 (backend), SYSAUD-04
- [ ] `tests/test_blackhole_wizard.py` -- covers SYSAUD-02 (wizard UI)
- [ ] `tests/test_system_audio_toggle.py` -- covers SYSAUD-03 (toggle widget)
- [ ] pyobjc-framework-CoreAudio spike test -- verify `AudioHardwareCreateAggregateDevice` is callable from Python

## Sources

### Primary (HIGH confidence)
- Dev machine device enumeration -- verified BlackHole 2ch at index 1 via `sounddevice.query_devices()`
- [Apple CoreAudio AudioHardwareCreateAggregateDevice docs](https://developer.apple.com/documentation/coreaudio/audiohardwarecreateaggregatedevice(_:_:)) -- function signature and parameters
- [BlackHole GitHub repository](https://github.com/ExistentialAudio/BlackHole) -- installation, architecture, Aggregate Device wiki
- [BlackHole Aggregate Device wiki](https://github.com/ExistentialAudio/BlackHole/wiki/Aggregate-Device) -- user setup flow

### Secondary (MEDIUM confidence)
- [Objective-C Aggregate Device creation gist](https://gist.github.com/larussverris/5387819a3a7337937084730a86cee073) -- dictionary structure for AudioHardwareCreateAggregateDevice
- [flyaga.info CoreAudio aggregate devices article](https://www.flyaga.info/creating-core-audio-aggregate-devices-programmatically/) -- creation/destruction process, workarounds for CoreAudio bugs
- [CAAudioHardware Swift library](https://github.com/sbooth/CAAudioHardware/blob/main/Sources/CAAudioHardware/AudioAggregateDevice.swift) -- Swift reference implementation
- [pyobjc-framework-CoreAudio on PyPI](https://pypi.org/project/pyobjc-framework-CoreAudio/) -- version 12.1, latest

### Tertiary (LOW confidence)
- [pyobjc CoreAudio API notes](https://pyobjc.readthedocs.io/en/latest/apinotes/CoreAudio.html) -- warns about low-level API uncertainty (403 on fetch, info from search results)
- pyobjc Python calling convention for AudioHardwareCreateAggregateDevice -- NO published examples found; needs spike test

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM -- pyobjc-framework-CoreAudio is the right tool but calling convention is unverified
- Architecture: HIGH -- existing AudioCaptureWorker pipeline handles everything once Aggregate Device exists
- Pitfalls: HIGH -- well-documented in CoreAudio community (persistence, sample rate, channel count)
- BlackHole detection: HIGH -- verified on dev machine
- Aggregate Device creation: LOW-MEDIUM -- no Python examples exist; may need fallback to Swift CLI

**Research date:** 2026-03-27
**Valid until:** 2026-04-27 (stable domain; pyobjc releases quarterly)
