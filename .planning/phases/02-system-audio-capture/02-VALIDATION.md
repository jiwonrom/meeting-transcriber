---
phase: 02
slug: system-audio-capture
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-27
---

# Phase 02 — Validation Strategy

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
| 01-T1 | 01 | 1 | SYSAUD-01 | unit | `python -c "from meeting_transcriber.utils..."` | ✅ | ⬜ pending |
| 01-T2 | 01 | 1 | SYSAUD-01, SYSAUD-04 | unit | `pytest tests/test_system_audio.py -x` | ❌ W0 | ⬜ pending |
| 02-T1 | 02 | 2 | SYSAUD-03 | unit | `pytest tests/test_system_audio_toggle.py -x` | ❌ W0 | ⬜ pending |
| 02-T2 | 02 | 2 | SYSAUD-02 | integration | `pytest tests/test_blackhole_wizard.py -x` | ❌ W0 | ⬜ pending |
| 03-T1 | 03 | 3 | SYSAUD-03, SYSAUD-04 | integration | `pytest tests/test_main_window.py -x` | ✅ | ⬜ pending |
| 03-T2 | 03 | 3 | SYSAUD-02 | integration | `pytest tests/test_settings_dialog.py tests/test_main_window.py -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_system_audio.py` — stubs for SYSAUD-01 (BlackHole detection) + SYSAUD-04 (Aggregate Device CRUD)
- [ ] `tests/test_system_audio_toggle.py` — stubs for SYSAUD-03 (SystemAudioToggle widget)
- [ ] `tests/test_blackhole_wizard.py` — stubs for SYSAUD-02 (BlackHoleSetupWizard UI)
- [ ] `tests/conftest.py` — mock fixtures for CoreAudio APIs (pyobjc stubs)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| BlackHole installer launches correctly | SYSAUD-02 | Requires actual macOS installer interaction | 1. Click "Install BlackHole" in wizard 2. Verify installer opens 3. Complete install 4. Verify app detects new device |
| System audio actually captured from calls | SYSAUD-03 | Requires real audio routing through BlackHole | 1. Play audio in browser 2. Start recording with system audio source 3. Verify transcript contains played audio content |
| Mic + system audio merged transcript quality | SYSAUD-04 | Requires real dual-source audio | 1. Play audio + speak simultaneously 2. Record with Aggregate Device 3. Verify both sources appear in transcript |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
