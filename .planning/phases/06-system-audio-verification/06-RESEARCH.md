# Phase 6: System Audio Completion & Verification - Research

**Researched:** 2026-04-02
**Domain:** System audio capture verification, gap closure, PyQt6 UI wiring
**Confidence:** HIGH

## Summary

Phase 6 is a **gap closure phase** identified by the v2.0 milestone audit. The audit found that Phase 2 (System Audio Capture) was executed (3/3 plans complete, all SUMMARYs exist) but never formally verified -- no VERIFICATION.md was created. Additionally, REQUIREMENTS.md still marks all four SYSAUD items as `[ ]` (unchecked).

After thorough code investigation, **the implementation for all four SYSAUD requirements appears functionally complete**. The SystemAudioToggle widget exists in MainWindow recording controls, BlackHole detection works, the setup wizard guides installation, and `start_recording()` uses the Aggregate Device when system audio is enabled. The 02-02-SUMMARY frontmatter lists `requirements-completed: [SYSAUD-01, SYSAUD-02, SYSAUD-03]` and 02-01-SUMMARY lists `[SYSAUD-01, SYSAUD-02, SYSAUD-04]`. All 65 related tests pass.

**Primary recommendation:** This phase is primarily a verification/documentation task. Create the Phase 2 VERIFICATION.md with formal test evidence for all 4 SYSAUD requirements, update REQUIREMENTS.md checkboxes to `[x]`, and confirm ROADMAP accuracy. No significant new code is expected unless verification reveals actual defects.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SYSAUD-01 | App detects whether BlackHole virtual audio driver is installed | `detect_blackhole()` and `is_blackhole_installed()` in `core/system_audio.py`, 14 unit tests in `test_system_audio.py`, Settings Dialog shows BlackHole status |
| SYSAUD-02 | App provides guided setup wizard for BlackHole installation and Aggregate Device creation | `BlackHoleSetupWizard` 5-step dialog in `ui/blackhole_wizard.py`, 8 tests in `test_blackhole_wizard.py`, accessible from toggle and settings |
| SYSAUD-03 | User can select system audio (via BlackHole) as input source alongside microphone | `SystemAudioToggle` widget in MainWindow recording controls, `_on_system_audio_toggled` saves setting, `start_recording()` resolves Aggregate Device by UID |
| SYSAUD-04 | User can capture both microphone and system audio simultaneously (dual-channel) | Aggregate Device creation via CoreAudio in `create_aggregate_device()`, DualLevelMeter visualization, mid-recording fallback on failure |
</phase_requirements>

## Standard Stack

No new libraries needed. This phase operates entirely within the existing stack.

### Core (already installed)
| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| PyQt6 | >= 6.6 | UI framework, SystemAudioToggle, BlackHoleSetupWizard | Installed |
| sounddevice | >= 0.4.6 | Audio device enumeration, BlackHole detection | Installed |
| pyobjc-framework-CoreAudio | >= 12.0 | Aggregate Device CRUD, device UID resolution | Installed |
| pytest | >= 8.0 | Test runner for verification | Installed |
| pytest-qt | >= 4.3 | Widget testing | Installed |

## Architecture Patterns

### Existing Code Structure (no changes needed)
```
src/meeting_transcriber/
  core/
    system_audio.py          # BlackHole detection, Aggregate Device CRUD
    audio_capture.py         # AudioCaptureWorker (device parameter)
  ui/
    blackhole_wizard.py      # 5-step setup wizard
    widgets/
      toggle_switch.py       # SystemAudioToggle widget
      dual_level_meter.py    # Dual-source level visualization
    main_window.py           # Toggle wiring, recording logic
    settings_dialog.py       # System Audio settings section
```

### Signal Flow (already wired)
```
SystemAudioToggle.toggled -> MainWindow._on_system_audio_toggled -> save_settings
SystemAudioToggle.setup_requested -> MainWindow._on_system_audio_setup_requested -> BlackHoleSetupWizard
BlackHoleSetupWizard.setup_completed -> MainWindow._on_blackhole_setup_completed -> toggle.setChecked(True)
MainWindow.start_recording() -> resolve_device_by_uid(aggregate_uid) -> AudioCaptureWorker(device=idx)
```

### SYSAUD-03 Implementation Path (already implemented)
The user selects system audio via the SystemAudioToggle in the recording controls:
1. Toggle ON saves `audio.system_audio.enabled = True` to settings
2. `start_recording()` reads `sys_audio.get("enabled")` and `sys_audio.get("aggregate_device_uid")`
3. If both are present, `resolve_device_by_uid()` finds the Aggregate Device index
4. `AudioCaptureWorker(device=aggregate_idx)` opens the combined mic+system stream
5. If Aggregate Device not found, falls back to mic-only with status bar message

### Anti-Patterns to Avoid
- **Writing new code when verification suffices:** Do not refactor or add features. This phase is about formally verifying existing work.
- **Skipping test execution:** Verification must include actually running tests and recording results, not just reviewing code.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Formal verification | Custom verification scripts | Standard VERIFICATION.md format with test evidence | Consistency with other phases (01, 03, 04, 05) |

## Common Pitfalls

### Pitfall 1: Confusing Verification Gap with Implementation Gap
**What goes wrong:** Spending time implementing features that already exist.
**Why it happens:** The audit marks SYSAUD-03 as "unsatisfied" and all SYSAUD items as unchecked in REQUIREMENTS.md, which looks like missing implementation.
**How to avoid:** Run the existing tests first. Examine the code. The 02-02-SUMMARY and 02-03-SUMMARY confirm implementation. The gap is documentation/verification, not code.
**Warning signs:** Writing new source files for Phase 6 (beyond verification artifacts).

### Pitfall 2: Not Running Tests Before Verification
**What goes wrong:** Creating VERIFICATION.md that claims PASS without actually running tests.
**Why it happens:** Rushing to close the gap.
**How to avoid:** Execute `pytest tests/test_system_audio.py tests/test_system_audio_toggle.py tests/test_blackhole_wizard.py tests/test_main_window.py tests/test_settings_dialog.py -x --tb=short -v` and capture output.
**Warning signs:** VERIFICATION.md without test output evidence.

### Pitfall 3: Stale REQUIREMENTS.md
**What goes wrong:** Forgetting to update the `[ ]` -> `[x]` checkboxes and traceability table.
**Why it happens:** Focus on VERIFICATION.md and forgetting the other artifact.
**How to avoid:** Checklist: VERIFICATION.md + REQUIREMENTS.md + ROADMAP.md all updated.

## Code Examples

### Verification Test Execution
```bash
# Run all system audio related tests
pytest tests/test_system_audio.py tests/test_system_audio_toggle.py \
  tests/test_blackhole_wizard.py tests/test_main_window.py \
  tests/test_settings_dialog.py -x --tb=short -v

# Current result: 65 passed in 0.91s
```

### Key Test Coverage Per Requirement

**SYSAUD-01 (BlackHole detection):**
- `test_detect_blackhole_found` - finds BlackHole in device list
- `test_detect_blackhole_not_installed` - returns None when absent
- `test_is_blackhole_installed_true/false` - boolean wrapper
- `test_blackhole_status_installed/not_installed` - Settings dialog display

**SYSAUD-02 (Setup wizard):**
- `test_wizard_opens` - wizard instantiation
- `test_wizard_step_navigation` - 5-step forward navigation
- `test_wizard_back_navigation` - back button works
- `test_wizard_detection_polling` - BlackHole detection timer
- `test_wizard_aggregate_creation_success` - device creation flow

**SYSAUD-03 (System audio selection):**
- `test_system_audio_toggle_exists` - toggle in MainWindow
- `test_toggle_emits_signal` - toggled signal fires
- `test_toggle_disabled_emits_setup_requested` - wizard launch when no BlackHole
- `test_start_recording_with_system_audio` - Aggregate Device used in recording
- `test_start_recording_fallback_to_mic` - graceful fallback

**SYSAUD-04 (Dual-channel capture):**
- `test_create_aggregate_device_success` - CoreAudio API
- `test_destroy_aggregate_device_success` - cleanup
- `test_level_meter_is_dual` - DualLevelMeter visualization
- `test_mid_recording_system_audio_failure` - mid-recording recovery

## State of the Art

| Old State | Current State | Impact |
|-----------|---------------|--------|
| Phase 2 VERIFICATION.md missing | Must be created | Blocks formal milestone completion |
| SYSAUD items `[ ]` in REQUIREMENTS.md | Must be checked `[x]` | Traceability gap |
| ROADMAP Phase 2 status stale | Already fixed per audit | Verify accuracy |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-qt 4.3 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_system_audio.py tests/test_system_audio_toggle.py tests/test_blackhole_wizard.py -x --tb=short -q` |
| Full suite command | `pytest tests/ -x --tb=short -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SYSAUD-01 | BlackHole detection | unit | `pytest tests/test_system_audio.py -k "detect_blackhole or is_blackhole" -x` | Yes |
| SYSAUD-02 | Setup wizard | integration | `pytest tests/test_blackhole_wizard.py -x` | Yes |
| SYSAUD-03 | System audio selection | integration | `pytest tests/test_system_audio_toggle.py tests/test_main_window.py -k "system_audio" -x` | Yes |
| SYSAUD-04 | Dual-channel capture | unit+integration | `pytest tests/test_system_audio.py -k "aggregate" tests/test_main_window.py -k "system_audio" -x` | Yes |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x --tb=short -q`
- **Per wave merge:** `pytest tests/ -x --tb=short -v`
- **Phase gate:** Full suite green before verification

### Wave 0 Gaps
None -- all test files exist and pass. No new test infrastructure needed.

## Open Questions

1. **Is SYSAUD-03 truly unsatisfied or just unverified?**
   - What we know: Code exists (SystemAudioToggle wired in MainWindow, start_recording uses Aggregate Device), tests pass, 02-02-SUMMARY lists it in requirements-completed
   - What's unclear: The audit says "unsatisfied" but the evidence suggests "unverified" -- the functionality exists but was never formally verified
   - Recommendation: Run verification. If tests pass and code review confirms the flow, mark as SATISFIED. Only implement new code if verification reveals actual gaps.

## Sources

### Primary (HIGH confidence)
- Direct codebase examination of `src/meeting_transcriber/core/system_audio.py`, `ui/main_window.py`, `ui/widgets/toggle_switch.py`, `ui/blackhole_wizard.py`
- Test execution: 65/65 tests passing across system audio test files
- Phase 2 SUMMARY files (02-01, 02-02, 02-03) confirming implementation

### Secondary (MEDIUM confidence)
- v2.0 milestone audit findings (`.planning/v2.0-MILESTONE-AUDIT.md`)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new dependencies, all existing
- Architecture: HIGH - direct code examination, all wiring verified
- Pitfalls: HIGH - clear gap between audit findings and actual code state

**Research date:** 2026-04-02
**Valid until:** 2026-05-02 (stable -- no external dependencies changing)
