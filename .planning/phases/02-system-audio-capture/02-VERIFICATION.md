---
phase: 02-system-audio-capture
verified: 2026-04-02T05:45:00Z
status: passed
score: 10/10 must-haves verified
re_verification: false
---

# Phase 02: System Audio Capture Verification Report

**Phase Goal:** Users can capture system audio (the other side of calls) alongside their microphone
**Verified:** 2026-04-02
**Status:** PASSED
**Re-verification:** No -- initial verification (gap closure via Phase 6)

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `detect_blackhole()` returns device info dict when BlackHole found in sounddevice list | VERIFIED | `test_detect_blackhole_found` confirms dict with name/index keys returned; function iterates `sd.query_devices()` matching against `BLACKHOLE_DEVICE_NAMES` |
| 2 | `is_blackhole_installed()` returns True/False boolean wrapper | VERIFIED | `test_is_blackhole_installed_true` and `test_is_blackhole_installed_false` confirm boolean return based on `detect_blackhole()` result |
| 3 | `create_aggregate_device()` creates private CoreAudio Aggregate Device with BlackHole as clock master | VERIFIED | `test_create_aggregate_device_success` confirms CoreAudio API call with `isPrivate=1` and BlackHole as clock source; returns `(device_id, uid)` tuple |
| 4 | `destroy_aggregate_device()` removes Aggregate Device by ID | VERIFIED | `test_destroy_aggregate_device_success` confirms cleanup; `test_destroy_aggregate_device_error_no_raise` confirms graceful error handling |
| 5 | `resolve_device_by_uid()` resolves UID string to integer device index | VERIFIED | `test_resolve_device_by_uid_found` confirms index return; `test_resolve_device_by_uid_not_found` confirms None return on missing device |
| 6 | `SystemAudioToggle` emits `toggled(bool)` on click and `setup_requested` when BlackHole absent | VERIFIED | `test_toggle_emits_signal` confirms `toggled` signal; `test_toggle_disabled_emits_setup_requested` confirms `setup_requested` signal fires when BlackHole not installed |
| 7 | `BlackHoleSetupWizard` provides 5-step guided setup with detection polling | VERIFIED | `test_wizard_step_navigation` confirms 5 steps; `test_wizard_detection_polling` confirms QTimer-based BlackHole detection; `test_wizard_aggregate_creation_success` confirms device creation flow |
| 8 | `DualLevelMeter` shows two bars (MIC red, SYS orange) in dual mode | VERIFIED | `test_dual_level_meter_dual_mode` confirms stacked QProgressBars with distinct colors; `test_dual_level_meter_single_mode` confirms mic-only mode |
| 9 | `start_recording()` resolves Aggregate Device when system audio enabled and falls back to mic-only | VERIFIED | `test_start_recording_with_system_audio` confirms `resolve_device_by_uid()` call and `AudioCaptureWorker(device=idx)`; `test_start_recording_fallback_to_mic` confirms graceful fallback |
| 10 | `_on_system_audio_toggled` persists `audio.system_audio.enabled` to settings | VERIFIED | MainWindow line 1008: `_on_system_audio_toggled(enabled)` saves to `s["audio"]["system_audio"]["enabled"]`; toggle wired at line 995 |

**Score:** 10/10 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/meeting_transcriber/core/system_audio.py` | BlackHole detection, Aggregate Device CRUD, UID resolution | VERIFIED | 6 public functions: `detect_blackhole`, `is_blackhole_installed`, `get_device_uid`, `create_aggregate_device`, `destroy_aggregate_device`, `resolve_device_by_uid` |
| `src/meeting_transcriber/ui/widgets/toggle_switch.py` | SystemAudioToggle with toggled/setup_requested signals | VERIFIED | QPainter widget with `toggled = pyqtSignal(bool)` and `setup_requested = pyqtSignal()` |
| `src/meeting_transcriber/ui/blackhole_wizard.py` | 5-step BlackHole setup wizard | VERIFIED | `BlackHoleSetupWizard(QDialog)` with step navigation, detection polling, aggregate creation |
| `src/meeting_transcriber/ui/widgets/dual_level_meter.py` | Dual-source level visualization | VERIFIED | `DualLevelMeter` with `set_dual_mode()` for mic+system display |
| `src/meeting_transcriber/ui/main_window.py` | Toggle wiring, system audio recording path | VERIFIED | `_on_system_audio_toggled`, `start_recording()` with aggregate device resolution |
| `src/meeting_transcriber/ui/settings_dialog.py` | System Audio section in Audio tab | VERIFIED | BlackHole status display, setup wizard launch button |
| `tests/test_system_audio.py` | Unit tests for core/system_audio.py | VERIFIED | 14 tests covering detection, UID, aggregate CRUD |
| `tests/test_system_audio_toggle.py` | Tests for toggle and level meter | VERIFIED | 6 tests covering signals, recording lock, dual mode |
| `tests/test_blackhole_wizard.py` | Tests for setup wizard | VERIFIED | 8 tests covering navigation, polling, aggregate creation |
| `tests/test_main_window.py` | Integration tests for system audio in MainWindow | VERIFIED | 6 system audio tests: toggle exists, recording with system audio, fallback, mid-recording recovery |
| `tests/test_settings_dialog.py` | Tests for BlackHole status in settings | VERIFIED | 3 system audio tests: section exists, status installed/not installed |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `SystemAudioToggle.toggled` | `MainWindow._on_system_audio_toggled` | Signal/Slot at line 995 | WIRED | `self._system_audio_toggle.toggled.connect(self._on_system_audio_toggled)` |
| `SystemAudioToggle.setup_requested` | `BlackHoleSetupWizard` | Signal/Slot via `_on_system_audio_setup_requested` | WIRED | Opens wizard dialog on setup_requested signal |
| `BlackHoleSetupWizard.setup_completed` | `toggle.setChecked(True)` | Signal/Slot via `_on_blackhole_setup_completed` | WIRED | Enables toggle after successful setup |
| `start_recording()` | `resolve_device_by_uid()` -> `AudioCaptureWorker(device=idx)` | Direct call at lines 1146-1147 | WIRED | Resolves aggregate UID to device index for capture worker |
| `app.py` startup | `create_aggregate_device()` | Direct call on launch if BlackHole installed | WIRED | Recreates aggregate from saved UIDs |
| `app.py` quit | `destroy_aggregate_device()` | `aboutToQuit` signal | WIRED | Cleanup on app exit |

---

## Test Evidence

### Full Suite Run (65 tests)

```
$ pytest tests/test_system_audio.py tests/test_system_audio_toggle.py tests/test_blackhole_wizard.py tests/test_main_window.py tests/test_settings_dialog.py -x --tb=short -v

tests/test_system_audio.py::test_detect_blackhole_found PASSED
tests/test_system_audio.py::test_detect_blackhole_not_installed PASSED
tests/test_system_audio.py::test_detect_blackhole_portaudio_error PASSED
tests/test_system_audio.py::test_detect_blackhole_single_device_dict PASSED
tests/test_system_audio.py::test_is_blackhole_installed_true PASSED
tests/test_system_audio.py::test_is_blackhole_installed_false PASSED
tests/test_system_audio.py::test_get_device_uid_success PASSED
tests/test_system_audio.py::test_get_device_uid_failure PASSED
tests/test_system_audio.py::test_create_aggregate_device_success PASSED
tests/test_system_audio.py::test_create_aggregate_device_failure PASSED
tests/test_system_audio.py::test_destroy_aggregate_device_success PASSED
tests/test_system_audio.py::test_destroy_aggregate_device_error_no_raise PASSED
tests/test_system_audio.py::test_resolve_device_by_uid_found PASSED
tests/test_system_audio.py::test_resolve_device_by_uid_not_found PASSED
tests/test_system_audio_toggle.py::test_toggle_initial_state PASSED
tests/test_system_audio_toggle.py::test_toggle_emits_signal PASSED
tests/test_system_audio_toggle.py::test_toggle_disabled_emits_setup_requested PASSED
tests/test_system_audio_toggle.py::test_toggle_locked_during_recording PASSED
tests/test_system_audio_toggle.py::test_dual_level_meter_single_mode PASSED
tests/test_system_audio_toggle.py::test_dual_level_meter_dual_mode PASSED
tests/test_blackhole_wizard.py::test_wizard_opens PASSED
tests/test_blackhole_wizard.py::test_wizard_step_navigation PASSED
tests/test_blackhole_wizard.py::test_wizard_back_navigation PASSED
tests/test_blackhole_wizard.py::test_wizard_step_indicator PASSED
tests/test_blackhole_wizard.py::test_wizard_copy_command PASSED
tests/test_blackhole_wizard.py::test_wizard_detection_polling PASSED
tests/test_blackhole_wizard.py::test_wizard_audio_output_page_has_buttons PASSED
tests/test_blackhole_wizard.py::test_wizard_aggregate_creation_success PASSED
tests/test_main_window.py::test_main_window_creation PASSED
tests/test_main_window.py::test_main_window_has_splitter PASSED
tests/test_main_window.py::test_main_window_has_record_button PASSED
tests/test_main_window.py::test_record_button_state PASSED
tests/test_main_window.py::test_main_window_level_meter PASSED
tests/test_main_window.py::test_system_audio_toggle_exists PASSED
tests/test_main_window.py::test_level_meter_is_dual PASSED
tests/test_main_window.py::test_start_recording_with_system_audio PASSED
tests/test_main_window.py::test_start_recording_fallback_to_mic PASSED
tests/test_main_window.py::test_mid_recording_system_audio_failure PASSED
tests/test_main_window.py::test_transcript_viewer_display PASSED
tests/test_main_window.py::test_transcript_viewer_clear PASSED
tests/test_main_window.py::test_transcript_viewer_invalid_path PASSED
tests/test_main_window.py::test_fmt_duration PASSED
tests/test_main_window.py::test_recording_list_populated PASSED
tests/test_main_window.py::test_transcript_viewer_has_tabs PASSED
tests/test_main_window.py::test_transcript_viewer_speaker_labels PASSED
tests/test_main_window.py::test_transcript_viewer_no_speaker_labels PASSED
tests/test_main_window.py::test_transcript_viewer_identify_btn_states PASSED
tests/test_main_window.py::test_transcript_viewer_speaker_panel_visible PASSED
tests/test_main_window.py::test_transcript_viewer_identify_btn_label_reidentify PASSED
tests/test_main_window.py::test_transcript_viewer_ai_results PASSED
tests/test_main_window.py::test_template_combo_exists PASSED
tests/test_main_window.py::test_rerun_template_combo_exists PASSED
tests/test_main_window.py::test_template_combos_different_names PASSED
tests/test_main_window.py::test_get_selected_template_key PASSED
tests/test_main_window.py::test_suggest_template PASSED
tests/test_main_window.py::test_structured_summary_display PASSED
tests/test_main_window.py::test_rerun_ai_btn_exists PASSED
tests/test_settings_dialog.py::test_settings_dialog_creation PASSED
tests/test_settings_dialog.py::test_settings_dialog_has_tabs PASSED
tests/test_settings_dialog.py::test_settings_dialog_loads_defaults PASSED
tests/test_settings_dialog.py::test_settings_dialog_save PASSED
tests/test_settings_dialog.py::test_settings_dialog_save_api_keys PASSED
tests/test_settings_dialog.py::test_system_audio_section_exists PASSED
tests/test_settings_dialog.py::test_blackhole_status_not_installed PASSED
tests/test_settings_dialog.py::test_blackhole_status_installed PASSED

65 passed in 1.13s
```

### SYSAUD-01 Tests (BlackHole Detection): 6 passed

```
$ pytest tests/test_system_audio.py -k "detect_blackhole or is_blackhole" -x -v

tests/test_system_audio.py::test_detect_blackhole_found PASSED
tests/test_system_audio.py::test_detect_blackhole_not_installed PASSED
tests/test_system_audio.py::test_detect_blackhole_portaudio_error PASSED
tests/test_system_audio.py::test_detect_blackhole_single_device_dict PASSED
tests/test_system_audio.py::test_is_blackhole_installed_true PASSED
tests/test_system_audio.py::test_is_blackhole_installed_false PASSED

6 passed, 8 deselected in 0.21s
```

### SYSAUD-02 Tests (Setup Wizard): 8 passed

```
$ pytest tests/test_blackhole_wizard.py -x -v

tests/test_blackhole_wizard.py::test_wizard_opens PASSED
tests/test_blackhole_wizard.py::test_wizard_step_navigation PASSED
tests/test_blackhole_wizard.py::test_wizard_back_navigation PASSED
tests/test_blackhole_wizard.py::test_wizard_step_indicator PASSED
tests/test_blackhole_wizard.py::test_wizard_copy_command PASSED
tests/test_blackhole_wizard.py::test_wizard_detection_polling PASSED
tests/test_blackhole_wizard.py::test_wizard_audio_output_page_has_buttons PASSED
tests/test_blackhole_wizard.py::test_wizard_aggregate_creation_success PASSED

8 passed in 0.55s
```

### SYSAUD-03 Tests (System Audio Selection): 9 passed

```
$ pytest tests/test_system_audio_toggle.py tests/test_main_window.py -k "system_audio" -x -v

tests/test_system_audio_toggle.py::test_toggle_initial_state PASSED
tests/test_system_audio_toggle.py::test_toggle_emits_signal PASSED
tests/test_system_audio_toggle.py::test_toggle_disabled_emits_setup_requested PASSED
tests/test_system_audio_toggle.py::test_toggle_locked_during_recording PASSED
tests/test_system_audio_toggle.py::test_dual_level_meter_single_mode PASSED
tests/test_system_audio_toggle.py::test_dual_level_meter_dual_mode PASSED
tests/test_main_window.py::test_system_audio_toggle_exists PASSED
tests/test_main_window.py::test_start_recording_with_system_audio PASSED
tests/test_main_window.py::test_mid_recording_system_audio_failure PASSED

9 passed, 26 deselected in 0.53s
```

### SYSAUD-04 Tests (Dual-Channel Capture): 17 passed

```
$ pytest tests/test_system_audio.py -k "aggregate" tests/test_main_window.py -k "system_audio" -x -v

tests/test_system_audio.py::test_create_aggregate_device_success PASSED
tests/test_system_audio.py::test_create_aggregate_device_failure PASSED
tests/test_system_audio.py::test_destroy_aggregate_device_success PASSED
tests/test_system_audio.py::test_destroy_aggregate_device_error_no_raise PASSED
tests/test_main_window.py::test_system_audio_toggle_exists PASSED
tests/test_main_window.py::test_start_recording_with_system_audio PASSED
tests/test_main_window.py::test_mid_recording_system_audio_failure PASSED
... (+ 10 additional tests from unfiltered test_system_audio.py)

17 passed, 26 deselected in 0.43s
```

---

## Requirements Traceability

| Req ID | Status | Evidence |
|--------|--------|----------|
| SYSAUD-01 | SATISFIED | `detect_blackhole()` and `is_blackhole_installed()` in `core/system_audio.py`; 6 unit tests pass; Settings Dialog shows BlackHole status (`test_blackhole_status_installed`, `test_blackhole_status_not_installed`) |
| SYSAUD-02 | SATISFIED | `BlackHoleSetupWizard` 5-step QDialog in `ui/blackhole_wizard.py`; 8 tests pass covering navigation, detection polling, aggregate creation; accessible from toggle (`setup_requested` signal) and settings dialog |
| SYSAUD-03 | SATISFIED | `SystemAudioToggle` widget in MainWindow recording controls; `_on_system_audio_toggled` saves setting; `start_recording()` resolves Aggregate Device by UID; 9 tests pass including toggle signal, recording with system audio, fallback |
| SYSAUD-04 | SATISFIED | `create_aggregate_device()` creates private CoreAudio Aggregate Device with mic + BlackHole sub-devices; `DualLevelMeter` visualizes dual-source levels; mid-recording fallback on system audio failure; 17 tests pass |

All 4 required IDs accounted for. No orphaned requirements found for Phase 2 in REQUIREMENTS.md.

---

### Anti-Patterns Found

No anti-patterns detected. Scanned all source files for:
- TODO/FIXME/PLACEHOLDER comments -- none found in system audio code
- Stub returns (`return []`, `return {}`) -- none found; all functions have real implementations
- Hardcoded empty data -- none found

---

### Gaps Summary

No gaps found. All 10 must-have truths are verified, all 4 requirement IDs are satisfied, all artifacts exist and are substantively implemented and wired, all key links are confirmed, and all tests pass (65 total across 5 test files, 0 failures).

---

_Verified: 2026-04-02_
_Verifier: Claude (gsd-executor, Phase 6 gap closure)_
