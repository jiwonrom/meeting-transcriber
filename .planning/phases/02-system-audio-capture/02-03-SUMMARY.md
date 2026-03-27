---
phase: 02-system-audio-capture
plan: 03
status: complete
approved: 2026-03-27
---

# Plan 02-03 Summary: Application Integration

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Integrate SystemAudioToggle + DualLevelMeter into MainWindow, modify recording logic with mid-recording fallback | 8b73d53 |
| 2 | Add System Audio settings section, wire signals in app.py, manage Aggregate Device lifecycle | ae9913b |
| 3 | Human verification checkpoint | approved by user |

## Key Changes

### MainWindow (main_window.py)
- SystemAudioToggle placed between duration label and record button in control bar
- DualLevelMeter replaces single level bar when system audio is active
- `start_recording()` resolves Aggregate Device via UID; falls back to mic-only if not found
- `_on_capture_error()` detects mid-recording system audio failure and restarts with mic-only (D-11)
- Toggle locked during active recording

### Settings Dialog (settings_dialog.py)
- System Audio section in Audio tab shows BlackHole status ("Installed"/"Not installed")
- Set Up / Reconfigure button opens BlackHoleSetupWizard

### App Lifecycle (app.py)
- On startup: recreates Aggregate Device from saved UIDs if BlackHole is installed
- On quit: destroys Aggregate Device via `aboutToQuit` signal
- Detects BlackHole uninstall between sessions and auto-disables system audio

### Theme (theme.py)
- QSS rule for `QProgressBar#system_level_bar` with orange processing color

## Tests Added
- 6 new tests in test_main_window.py (toggle wiring, recording with system audio, fallback, mid-recording recovery)
- 3 new tests in test_settings_dialog.py (BlackHole status display, wizard launch, settings persistence)

## Requirements Covered
- SYSAUD-01: BlackHole detection status shown in settings and toggle state
- SYSAUD-02: Setup wizard accessible from both toggle and settings
- SYSAUD-03: System audio selectable via toggle, used in recording
- SYSAUD-04: Dual-channel capture via Aggregate Device with DualLevelMeter visualization
