---
status: partial
phase: 01-export-multi-provider
source: [01-VERIFICATION.md]
started: 2026-03-27T04:20:00.000Z
updated: 2026-03-27T04:20:00.000Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Export Buttons Visible in TranscriptViewer
expected: Three buttons appear below transcript tabs — "Export SRT", "Export VTT", "Export to Obsidian"
result: [pending]

### 2. Preferences General Tab — Export Path Fields
expected: "Export Directory" and "Obsidian Vault" rows with read-only input and "Browse..." button in General tab
result: [pending]

### 3. Preferences API Keys Tab — Multi-Provider Fields
expected: Three key fields (Gemini, OpenAI, Anthropic), "Save Keys" button, and "Default AI Provider" dropdown
result: [pending]

### 4. Export File Dialog Flow
expected: Native macOS save dialog with *.srt filter; saved file is valid SRT with numbered entries and HH:MM:SS,mmm timestamps
result: [pending]

### 5. Provider Fallback Status Bar Message
expected: Status bar shows fallback message when primary provider fails (e.g., "AI complete (fallback: GeminiProvider failed, using OpenAIProvider)")
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
