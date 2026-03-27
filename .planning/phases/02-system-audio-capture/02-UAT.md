---
status: complete
phase: 02-system-audio-capture
source: [02-01-SUMMARY.md, 02-02-SUMMARY.md, 02-03-SUMMARY.md]
started: 2026-03-27T06:10:00Z
updated: 2026-03-27T06:20:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running Scribe instance. Start the app fresh with `python -m meeting_transcriber.app`. App boots without errors, main window appears, tray icon shows, no crash or traceback in terminal.
result: pass

### 2. System Audio Toggle Visible in Control Bar
expected: In the main window control bar, a toggle switch labeled "System Audio" appears between the duration label and the record button. The toggle is 44x24px with a sliding thumb. If BlackHole is not installed, the toggle appears grayed out (disabled).
result: pass

### 3. Toggle Tooltip Shows Correct State
expected: Hover over the System Audio toggle. If BlackHole is not installed, tooltip says "BlackHole audio driver required -- click to set up". If installed and not recording, tooltip says "Capture system audio alongside microphone".
result: pass

### 4. Disabled Toggle Opens BlackHole Wizard
expected: With BlackHole NOT installed, click the grayed-out System Audio toggle. The BlackHoleSetupWizard dialog opens (modal, 500x480px, titled "Scribe -- System Audio Setup") showing Step 1 with "Capture System Audio" heading and "Get Started" button.
result: pass

### 5. BlackHole Wizard Navigation
expected: In the wizard, click "Get Started" to advance to Step 2 (Install BlackHole). Back button appears. Step indicator shows "Step 2 of 4". Two install options visible: Homebrew command with "Copy Command" button, and "Open Download Page" link. Next button is disabled until BlackHole is detected.
result: pass

### 6. Settings Dialog System Audio Section
expected: Open Preferences > Audio tab. A "System Audio" section shows BlackHole status ("Installed" or "Not installed") with a "Set Up" or "Reconfigure" button that opens the BlackHole wizard.
result: pass

### 7. Dual Level Meter During System Audio Recording
expected: With system audio enabled and toggle ON, start recording. Two stacked level meters appear — top (red/mic) and bottom (orange/system). Both respond to audio input in real time. Control bar height increases slightly to accommodate both meters.
result: pass

### 8. Mid-Recording System Audio Fallback
expected: If system audio stream fails during recording, the app continues recording with microphone only. Status bar shows a warning message about system audio disconnection. Recording is not interrupted.
result: pass

## Summary

total: 8
passed: 8
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
