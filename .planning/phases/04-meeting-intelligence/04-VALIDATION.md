---
phase: 4
slug: meeting-intelligence
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-28
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x with pytest-qt 4.3 |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/ -x --tb=short -q` |
| **Full suite command** | `pytest tests/ -x --tb=short -v` |
| **Estimated runtime** | ~3 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x --tb=short -q`
- **After every plan wave:** Run `pytest tests/ -x --tb=short -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | TPL-01, TPL-02, TPL-03 | unit | `pytest tests/test_templates.py -x --tb=short -v` | W0 | pending |
| 04-01-02 | 01 | 1 | TPL-01, TPL-02 | unit+integration | `pytest tests/test_ai_provider.py tests/test_exporter.py -x --tb=short -v` | exists | pending |
| 04-02-01 | 02 | 1 | DET-01, DET-02 | unit | `pytest tests/test_meeting_detector.py -x --tb=short -v` | W0 | pending |
| 04-03-01 | 03 | 2 | TPL-01, TPL-02 | unit+integration | `pytest tests/test_main_window.py -x --tb=short -v` | exists | pending |
| 04-03-02 | 03 | 2 | DET-01, DET-02 | unit+integration | `pytest tests/test_tray.py tests/test_main_window.py -x --tb=short -v` | exists | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_templates.py` — stubs for TPL-01, TPL-02, TPL-03 (template loading, prompt generation, YAML parsing)
- [ ] `tests/test_meeting_detector.py` — stubs for DET-01, DET-02 (process detection, notification trigger)

*TDD-within-task approach: test files created alongside implementation in each task.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| macOS notification appears when Zoom/Teams detected | DET-02 | Requires real conferencing app running | Open Zoom, wait 10s, verify notification |
| Snooze action suppresses repeated notification | DET-02 | Requires real conferencing app + tray interaction | After notification, click Snooze in tray menu, verify no repeat |
| Template dropdown visible next to Record button | TPL-01 | Visual layout verification | Launch app, check Record button area |
| Structured summary sections render correctly | TPL-02 | Visual formatting check | Record with template, verify summary display |
| Custom YAML template loads and works | TPL-03 | End-to-end with real AI call | Create YAML file, restart app, select template, run AI |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
