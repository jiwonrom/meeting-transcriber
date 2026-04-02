---
phase: 6
slug: system-audio-verification
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-02
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-qt 4.3 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/test_system_audio.py tests/test_system_audio_toggle.py tests/test_blackhole_wizard.py -x --tb=short -q` |
| **Full suite command** | `pytest tests/ -x --tb=short -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_system_audio.py tests/test_system_audio_toggle.py tests/test_blackhole_wizard.py -x --tb=short -q`
- **After every plan wave:** Run `pytest tests/ -x --tb=short -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | SYSAUD-03 | integration | `pytest tests/test_system_audio_toggle.py tests/test_main_window.py -k "system_audio" -x` | ✅ | ⬜ pending |
| 06-01-02 | 01 | 1 | SYSAUD-01 | unit | `pytest tests/test_system_audio.py -k "detect_blackhole or is_blackhole" -x` | ✅ | ⬜ pending |
| 06-01-03 | 01 | 1 | SYSAUD-02 | integration | `pytest tests/test_blackhole_wizard.py -x` | ✅ | ⬜ pending |
| 06-01-04 | 01 | 1 | SYSAUD-04 | unit+integration | `pytest tests/test_system_audio.py -k "aggregate" tests/test_main_window.py -k "system_audio" -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No new test infrastructure needed — all test files exist and 65/65 tests pass.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| BlackHole toggle visible in recording controls | SYSAUD-03 | Runtime UI visibility | Launch app, verify SystemAudioToggle appears in recording controls area |
| Aggregate Device creation wizard flow | SYSAUD-02 | Requires real macOS Audio MIDI Setup | Run wizard, verify Aggregate Device appears in System Preferences |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
