---
status: complete
phase: 02-system-audio-capture
source: [02-UI-REVIEW.md, UI critique fixes]
started: 2026-03-27T07:00:00Z
updated: 2026-03-27T07:05:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Wizard Heading/Body Theme Rendering
expected: Open the BlackHole wizard (click disabled System Audio toggle). Heading text ("Capture System Audio") and body text should render with correct colors inherited from theme — not hardcoded. Text should be fully visible, not truncated.
result: pass

### 2. Wizard Install Cards Styled via Theme
expected: Navigate to Step 2 (Install BlackHole). The two install option cards (Homebrew / GitHub) have border and padding from the design token system. The brew command "brew install blackhole-2ch" renders in monospace font. No visual glitches or clipping.
result: pass

### 3. System Audio Label Accent During Recording
expected: With system audio toggle ON, start recording. The "System Audio" label below the toggle turns accent red (#FF453A in dark mode). When recording stops, the label returns to secondary gray.
result: pass

### 4. Settings Dialog System Audio Colors
expected: Open Preferences > Audio tab. "System Audio" heading renders as a proper heading. BlackHole status ("Installed" or "Not installed") uses theme colors — green for installed, gray for not installed. No hardcoded dark-mode-only hex values visible.
result: pass

### 5. Status Bar Disconnection Text
expected: If system audio fails mid-recording, status bar shows "System audio disconnected -- continuing with microphone only" (not "lost").
result: pass

## Summary

total: 5
passed: 5
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
