---
phase: 08
slug: per-task-provider-override
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-02
---

# Phase 08 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/test_ai_provider.py -x --tb=short -q` |
| **Full suite command** | `pytest tests/ -x --tb=short -v` |
| **Estimated runtime** | ~4 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_ai_provider.py -x --tb=short -q`
- **After every plan wave:** Run `pytest tests/ -x --tb=short -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | BYOK-03 | unit | `pytest tests/test_ai_provider.py -x -v` | existing | pending |
| 08-01-02 | 01 | 1 | BYOK-03 | unit | `pytest tests/test_ai_provider.py -x -v` | existing | pending |

*Status: pending · green · red · flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Per-task override applied at runtime | BYOK-03 | Requires configured API keys | Set task_overrides in settings, trigger AI tasks, verify different providers used |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
