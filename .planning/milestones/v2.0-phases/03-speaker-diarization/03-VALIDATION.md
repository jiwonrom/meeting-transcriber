---
phase: 3
slug: speaker-diarization
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-27
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ with pytest-qt 4.3+ |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/ -x --tb=short` |
| **Full suite command** | `pytest tests/ -x --tb=short -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x --tb=short`
- **After every plan wave:** Run `pytest tests/ -x --tb=short -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | DIAR-01 | unit | `pytest tests/test_diarizer.py::test_align_speakers -x` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | DIAR-03 | unit | `pytest tests/test_storage.py::test_schema_v2_speaker_field -x` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 2 | DIAR-02 | unit | `pytest tests/test_main_window.py::test_transcript_viewer_speaker_labels -x` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 2 | DIAR-04 | unit | `pytest tests/test_exporter.py::test_srt_speaker_labels -x` | Partial | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_diarizer.py` — stubs for DIAR-01 (speaker alignment logic, mocked pipeline)
- [ ] `tests/test_storage.py::test_schema_v2_*` — stubs for DIAR-03 (v2.0 schema, v1.0 backward compat)
- [ ] `tests/test_exporter.py::test_*_speaker_*` — stubs for DIAR-04 (speaker labels in SRT/VTT export)
- [ ] `tests/test_main_window.py::test_transcript_viewer_speaker_*` — stubs for DIAR-02 (speaker label display)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Color-coded speaker labels visible in UI | DIAR-02 | Visual rendering verification | 1. Record/import audio with 2+ speakers 2. Trigger diarization 3. Verify speaker labels show with distinct colors |
| Diarization progress feedback | DIAR-01 | UX timing/feedback quality | 1. Start diarization on ~5min recording 2. Verify progress indication 3. Check completion notification |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
