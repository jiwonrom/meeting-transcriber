---
phase: 03-speaker-diarization
plan: 02
subsystem: ui
tags: [pyannote, diarization, speaker-labels, huggingface, transcript-viewer]

requires:
  - phase: 03-01
    provides: DiarizationWorker, align_speakers, rename_speaker, update_transcript_speakers, schema v2.0

provides:
  - Audio file preservation (recording.wav) for post-recording diarization
  - Auto-diarization trigger after recording completion
  - Manual "Identify Speakers" / "Re-identify Speakers" button in TranscriptViewer
  - Speaker labels as inline HTML prefixes in transcript Original tab
  - Speaker list panel with click-to-rename via QInputDialog
  - HuggingFace token management in Settings > Speaker Identification tab
  - Diarization status bar progress messages

affects: [03-03, ui-testing]

tech-stack:
  added: []
  patterns:
    - "Lazy import pattern for DiarizationWorker and keychain in UI methods"
    - "HTML rendering with setHtml() for speaker-labeled transcript segments"
    - "Speaker panel with dynamic QLabel creation and mousePressEvent lambda binding"

key-files:
  created: []
  modified:
    - src/meeting_transcriber/ui/main_window.py
    - src/meeting_transcriber/ui/settings_dialog.py
    - tests/test_main_window.py
    - tests/test_settings_dialog.py

key-decisions:
  - "Speaker labels rendered as HTML via setHtml() rather than plain text for inline styling"
  - "Speaker rename uses QInputDialog.getText for simple modal rename flow"
  - "Audio preservation uses rename with shutil.copy2 fallback for cross-device moves"
  - "HF token validation requires hf_ prefix before saving to Keychain"

patterns-established:
  - "HTML segment rendering: setHtml() with inline styles for rich transcript display"
  - "Speaker panel: dynamic QLabel widgets with mousePressEvent overrides for click handling"

requirements-completed: [DIAR-01, DIAR-02, DIAR-04]

duration: 5min
completed: 2026-03-27
---

# Phase 3 Plan 2: Diarization UI Wiring Summary

**Full speaker diarization UI pipeline: auto-diarization after recording, manual identify button, inline speaker labels, click-to-rename speaker panel, and HuggingFace token settings.**

## What Was Built

### Audio File Preservation
- Replaced `temp_wav.unlink()` with `temp_wav.rename(folder / "recording.wav")` in `_on_transcription_done`
- Added shutil.copy2 fallback for cross-device rename failures
- Audio file is now preserved in transcript folder for diarization processing

### Auto-Diarization Trigger
- `_auto_diarize()` method runs after transcription completes when HF token is available
- Silently skips when no token configured (no error shown to user)
- Status bar shows "Identifying speakers..." during processing

### Manual Diarization
- `_on_identify_speakers_requested()` handles manual trigger from TranscriptViewer signal
- Loads transcript, verifies audio file existence, creates DiarizationWorker
- Connected via `diarization_requested` pyqtSignal(str) on TranscriptViewer

### Speaker Labels in TranscriptViewer
- Original tab uses `setHtml()` for rich text rendering with speaker prefixes
- Speaker labels styled with `font-weight: 600` and theme-aware color (#98989D dark / #6E6E73 light)
- v1.0 transcripts (no speakers) continue to use `setPlainText()` -- backward compatible

### Speaker List Panel
- Horizontal panel below meta label showing clickable speaker names
- Supports up to 8 speakers with "+N more" overflow
- Click triggers QInputDialog rename -> rename_speaker() -> save_transcript() -> refresh

### Identify Speakers Button
- Added to export bar (left side, before stretch)
- States: "Identify Speakers" (no diarization), "Re-identify Speakers" (has diarization)
- Disabled when recording.wav not found, with tooltip explaining why
- Token check with QMessageBox warning when HF token missing

### Settings Dialog HF Token
- New "Speaker Identification" tab in SettingsDialog
- HuggingFace token input with Password echo mode
- Validation: token must start with "hf_"
- "Get Token" button opens huggingface.co/settings/tokens in browser
- Existing token shown as masked placeholder

## Tests Added

5 new tests in `tests/test_main_window.py`:
- `test_transcript_viewer_speaker_labels` -- v2.0 transcript shows speaker prefixes in HTML
- `test_transcript_viewer_no_speaker_labels` -- v1.0 transcript has no speaker prefix
- `test_transcript_viewer_identify_btn_states` -- button enabled/disabled based on recording.wav
- `test_transcript_viewer_speaker_panel_visible` -- panel visibility with/without speakers
- `test_transcript_viewer_identify_btn_label_reidentify` -- button label changes for re-identification

1 existing test updated in `tests/test_settings_dialog.py`:
- `test_settings_dialog_has_tabs` -- updated count from 4 to 5

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Settings tab count test**
- **Found during:** Task 1
- **Issue:** Existing test `test_settings_dialog_has_tabs` expected 4 tabs, now 5 with Speaker Identification
- **Fix:** Updated assertion from 4 to 5, added "Speaker Identification" to expected tab texts
- **Files modified:** tests/test_settings_dialog.py
- **Commit:** 07082a0

**2. [Rule 1 - Bug] Speaker panel visibility test**
- **Found during:** Task 2
- **Issue:** `isVisible()` returns False for widgets whose parent is not shown (Qt behavior)
- **Fix:** Changed test to use `isVisibleTo(viewer)` which checks relative visibility
- **Files modified:** tests/test_main_window.py
- **Commit:** a624dbb

## Known Stubs

None -- all data flows are fully wired from backend (Plan 01) through UI (Plan 02).

## Self-Check: PASSED

- All key files exist (main_window.py, settings_dialog.py, test_main_window.py)
- Both commits found (07082a0, a624dbb)
- All acceptance criteria patterns present in source files
- 290/290 tests passing
