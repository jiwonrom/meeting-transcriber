---
phase: 07
slug: cross-meeting-wiring-fixes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-02
---

# Phase 07 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/test_metadata_index.py tests/test_sidebar.py tests/test_main_window.py -x --tb=short -q` |
| **Full suite command** | `pytest tests/ -x --tb=short -v` |
| **Estimated runtime** | ~4 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_metadata_index.py tests/test_sidebar.py tests/test_main_window.py -x --tb=short -q`
- **After every plan wave:** Run `pytest tests/ -x --tb=short -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | CMA-03 | unit+tdd | `pytest tests/test_metadata_index.py -x -v` | existing | pending |
| 07-01-02 | 01 | 1 | CMA-03 | unit+tdd | `pytest tests/test_metadata_index.py -x -v` | existing | pending |
| 07-02-01 | 02 | 2 | CMA-01 | integration | `pytest tests/test_main_window.py tests/test_sidebar.py -x -v` | existing | pending |
| 07-02-02 | 02 | 2 | CMA-01 | import | `python -c "from meeting_transcriber.app import main"` | n/a | pending |

*Status: pending · green · red · flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SidebarWidget visible in MainWindow | CMA-01 | Visual layout verification | Launch app, confirm sidebar tree view with selection mode button visible |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
