---
phase: 5
slug: cross-meeting-analysis
status: draft
nyquist_compliant: false
wave_0_complete: false
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

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | CMA-03 | unit | `pytest tests/test_metadata_index.py -x` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | CMA-03 | unit | `pytest tests/test_metadata_index.py -x` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 1 | CMA-02 | unit | `pytest tests/test_cross_meeting.py -x` | ❌ W0 | ⬜ pending |
| 05-02-02 | 02 | 1 | CMA-02 | unit | `pytest tests/test_cross_meeting.py -x` | ❌ W0 | ⬜ pending |
| 05-03-01 | 03 | 2 | CMA-01 | unit | `pytest tests/test_sidebar.py -x` | ✅ | ⬜ pending |
| 05-03-02 | 03 | 2 | CMA-01, CMA-02 | integration | `pytest tests/ -x --tb=short` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_metadata_index.py` — stubs for CMA-03 (index CRUD, update hooks, search)
- [ ] `tests/test_cross_meeting.py` — stubs for CMA-02 (analysis worker, result parsing, export)
- [ ] `tests/test_analysis_store.py` — stubs for analysis persistence

*Existing test infrastructure (conftest.py, fixtures) covers shared needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Sidebar checkbox selection mode UX | CMA-01 | Visual interaction flow requires manual verification | Enter selection mode, check 2+ transcripts across folders, verify "Analyze N selected" button appears |
| Cross-meeting analysis HTML rendering | CMA-02 | Visual rendering quality of structured sections | Run analysis, verify recurring topics and action items render as collapsible sections with proper styling |
| Analyses section in sidebar browsability | CMA-01 | UI navigation flow | Save an analysis, verify it appears under "Analyses" section, click to reopen |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
