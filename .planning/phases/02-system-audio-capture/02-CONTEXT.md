# Phase 2: System Audio Capture - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase adds system audio capture (the other side of calls) via BlackHole virtual audio driver. Users can capture both microphone and system audio simultaneously, producing a single merged transcript. Includes BlackHole detection, installation wizard, Aggregate Device auto-creation, and dual-source recording with graceful degradation when BlackHole is not installed.

</domain>

<decisions>
## Implementation Decisions

### BlackHole Installation Guide
- **D-01:** In-app setup wizard with step-by-step instructions + external download link (Homebrew command copy button, or BlackHole GitHub releases page link)
- **D-02:** Aggregate Device auto-creation via CoreAudio API (pyobjc) — user should NOT need to open Audio MIDI Setup manually

### Audio Source Selection UX
- **D-03:** Toggle switch next to record button for "System Audio" — ON means capture mic + system simultaneously
- **D-04:** When BlackHole is not installed, toggle is visible but disabled (grayed out). Clicking it opens the installation wizard.

### Dual Channel Mixing
- **D-05:** Single mix — merge mic + system audio into one stream before sending to whisper. Reuses existing AudioCaptureWorker pipeline.
- **D-06:** Aggregate Device (created in D-02) handles hardware-level mixing — app opens a single input stream from the Aggregate Device

### BlackHole Not Installed Behavior
- **D-07:** App works exactly as before (mic-only mode). System audio features are present but disabled until BlackHole is installed.
- **D-08:** No startup prompt to install BlackHole — discovery is through the disabled toggle or Preferences

### Audio Quality
- **D-09:** Claude's Discretion — volume balance/normalization approach for mic + system mix (auto-normalization recommended)

### Recording Status Display
- **D-10:** Claude's Discretion — how to visually indicate dual-source capture (dual level meters or badge approach)

### Error Handling
- **D-11:** If system audio stream fails mid-recording, microphone recording continues uninterrupted. Status bar shows warning message.
- **D-12:** BlackHole disconnection is non-fatal — graceful degradation to mic-only

### Claude's Discretion
- Volume balancing/normalization strategy for mic + system audio mix
- Recording status visual indicator design (dual meters vs badge)
- Setup wizard visual design and step layout
- Aggregate Device naming convention

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Audio Architecture
- `src/meeting_transcriber/core/audio_capture.py` — Existing AudioCaptureWorker, sounddevice InputStream pattern, chunk buffering
- `src/meeting_transcriber/utils/constants.py` — AUDIO_SAMPLE_RATE, AUDIO_CHANNELS, AUDIO_CHUNK_SECONDS

### Prior Research
- `.planning/research/STACK.md` §BlackHole Integration Details — BlackHole architecture, detection, Aggregate Device creation approach

### UI Patterns
- `src/meeting_transcriber/ui/main_window.py` — Recording controls, where toggle switch should be added
- `src/meeting_transcriber/ui/onboarding.py` — Existing wizard pattern (reuse for BlackHole setup wizard)
- `src/meeting_transcriber/ui/settings_dialog.py` — Preferences extension pattern from Phase 1

### Requirements
- `.planning/REQUIREMENTS.md` §System Audio — SYSAUD-01 through SYSAUD-04

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AudioCaptureWorker` — Already supports `device` parameter. BlackHole/Aggregate Device appears as standard CoreAudio device, so same worker can capture from it.
- `list_audio_devices()` — Returns all input devices including BlackHole when installed. Can be used for detection.
- `OnboardingWizard` — Existing wizard UI pattern for step-by-step setup (reuse for BlackHole wizard)
- `encode_wav_chunk()` — WAV encoding for whisper-cli, works with any mono input

### Established Patterns
- QThread workers for all I/O (audio capture, transcription)
- Signal/Slot for worker → UI communication
- Settings in ~/.meeting_transcriber/settings.json via load_settings/save_settings
- Preferences dialog tab extension (Phase 1 pattern)

### Integration Points
- `MainWindow.toggle_recording()` — Where system audio toggle connects
- `app.py` signal wiring — Where new signals get connected
- `settings.json` — New keys for system audio preferences

</code_context>

<specifics>
## Specific Ideas

- BlackHole은 시스템 레벨 드라이버이므로 앱에서 직접 설치 불가 — Homebrew 또는 수동 설치 안내 필요
- Aggregate Device 자동 생성은 pyobjc의 CoreAudio 바인딩 사용
- 기존 AudioCaptureWorker의 device 파라미터만 변경하면 BlackHole/Aggregate Device에서 캡처 가능

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-system-audio-capture*
*Context gathered: 2026-03-27*
