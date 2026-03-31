---
phase: 5
slug: cross-meeting-analysis
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-31
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-qt 4.3 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/ -x --tb=short -q` |
| **Full suite command** | `pytest tests/ -x --tb=short -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x --tb=short -q`
- **After every plan wave:** Run `pytest tests/ -x --tb=short -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Wave 0 | Status |
|---------|------|------|-------------|-----------|-------------------|--------|--------|
| 05-01-01 | 01 | 1 | CMA-03 | unit | `pytest tests/test_metadata_index.py tests/test_analysis_store.py -x` | TDD-in-task | pending |
| 05-01-02 | 01 | 1 | CMA-02 | unit | `pytest tests/test_cross_meeting.py -x` | TDD-in-task | pending |
| 05-02-01 | 02 | 1 | CMA-01 | unit | `pytest tests/test_sidebar.py -x` | exists | pending |
| 05-03-01 | 03 | 2 | CMA-01, CMA-03 | unit | `pytest tests/test_workspace.py -x` | exists | pending |
| 05-03-02 | 03 | 2 | CMA-01, CMA-02 | integration | `pytest tests/ -x --tb=short` | exists | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

Wave 0 is satisfied via **within-task TDD ordering** in Plan 01:

- `tests/test_metadata_index.py` — created FIRST within Plan 01 Task 1 (tests written before source, RED then GREEN)
- `tests/test_analysis_store.py` — created FIRST within Plan 01 Task 1 (tests written before source, RED then GREEN)
- `tests/test_cross_meeting.py` — created FIRST within Plan 01 Task 2 (tests written before source, RED then GREEN)

Plan 01 task actions contain explicit **TDD ordering instructions**: write test files first, run to confirm RED, then implement source files and run to confirm GREEN. This ensures test files pre-exist before the implementation code they verify, satisfying the Nyquist Wave 0 requirement without a separate Wave 0 plan.

*Existing test infrastructure (conftest.py, fixtures) covers shared needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Sidebar checkbox selection mode UX | CMA-01 | Visual interaction flow requires manual verification | Enter selection mode, check 2+ transcripts across folders, verify "Analyze N selected" button appears |
| Cross-meeting analysis HTML rendering | CMA-02 | Visual rendering quality of structured sections | Run analysis, verify recurring topics and action items render as collapsible sections with proper styling |
| Analyses section in sidebar browsability | CMA-01 | UI navigation flow | Save an analysis, verify it appears under "Analyses" section, click to reopen |
| Export as Markdown button | CMA-02 | UI trigger verification | After analysis displays, verify "Export as Markdown" button is visible and opens save dialog |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (via TDD-in-task ordering)
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved
