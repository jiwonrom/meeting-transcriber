---
phase: 02-system-audio-capture
plan: 01
subsystem: core
tags: [coreaudio, pyobjc, blackhole, aggregate-device, system-audio, sounddevice]

# Dependency graph
requires: []
provides:
  - "BlackHole detection via sounddevice (detect_blackhole, is_blackhole_installed)"
  - "CoreAudio Aggregate Device CRUD (create_aggregate_device, destroy_aggregate_device)"
  - "Device UID resolution (get_device_uid, resolve_device_by_uid)"
  - "SystemAudioError exception class"
  - "System audio settings schema (audio.system_audio in config defaults)"
  - "BlackHole/Aggregate Device constants"
affects: [02-02-PLAN, 02-03-PLAN]

# Tech tracking
tech-stack:
  added: [pyobjc-framework-CoreAudio]
  patterns: [lazy-import-for-optional-deps, mocked-coreaudio-testing]

key-files:
  created:
    - src/meeting_transcriber/core/system_audio.py
    - tests/test_system_audio.py
  modified:
    - pyproject.toml
    - src/meeting_transcriber/utils/constants.py
    - src/meeting_transcriber/utils/exceptions.py
    - src/meeting_transcriber/utils/config.py
    - tests/test_constants.py
    - tests/test_config.py

key-decisions:
  - "Lazy import CoreAudio at function level to avoid import-time failure when pyobjc not installed"
  - "Private Aggregate Device (isPrivate=1) for process-scoped lifecycle"
  - "BlackHole as clock master for Aggregate Device per research pitfall guidance"

patterns-established:
  - "Lazy pyobjc import: import CoreAudio inside function body, not at module top"
  - "Mocked CoreAudio testing: patch sys.modules with MagicMock for unit tests without pyobjc"

requirements-completed: [SYSAUD-01, SYSAUD-02, SYSAUD-04]

# Metrics
duration: 4min
completed: 2026-03-27
---

# Phase 02 Plan 01: System Audio Core Backend Summary

**BlackHole detection + CoreAudio Aggregate Device CRUD via pyobjc with lazy imports and 14 mocked unit tests**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-27T05:43:01Z
- **Completed:** 2026-03-27T05:47:00Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- core/system_audio.py with 6 public functions: detect_blackhole, is_blackhole_installed, get_device_uid, create_aggregate_device, destroy_aggregate_device, resolve_device_by_uid
- Settings schema extended with system_audio section (enabled, blackhole_uid, aggregate_device_uid, mic_device_uid)
- SystemAudioError exception and BlackHole/Aggregate Device constants added
- 14 unit tests passing with fully mocked CoreAudio and sounddevice

## Task Commits

Each task was committed atomically:

1. **Task 1: Add pyobjc dependency + constants + exceptions + config defaults**
   - `9d8ea52` (test: RED - failing tests for constants and config)
   - `500375e` (feat: GREEN - pyobjc dep, constants, exception, config schema)
2. **Task 2: Create core/system_audio.py with detection, UID resolution, and Aggregate Device CRUD**
   - `d66354a` (test: RED - failing tests for system_audio module)
   - `a87ea41` (feat: GREEN - full system_audio implementation)

_TDD flow: RED commit (failing tests) then GREEN commit (passing implementation) per task._

## Files Created/Modified
- `src/meeting_transcriber/core/system_audio.py` - BlackHole detection, Aggregate Device CRUD, UID resolution
- `tests/test_system_audio.py` - 14 unit tests with mocked CoreAudio/sounddevice
- `pyproject.toml` - Added pyobjc-framework-CoreAudio>=12.0 dependency
- `src/meeting_transcriber/utils/constants.py` - BLACKHOLE_DEVICE_NAMES, AGGREGATE_DEVICE_NAME, AGGREGATE_DEVICE_UID
- `src/meeting_transcriber/utils/exceptions.py` - SystemAudioError exception class
- `src/meeting_transcriber/utils/config.py` - system_audio settings defaults under audio section
- `tests/test_constants.py` - Tests for new BlackHole/Aggregate constants
- `tests/test_config.py` - Test for system_audio config schema

## Decisions Made
- Lazy import CoreAudio at function level to avoid ImportError when pyobjc not installed -- allows the module to be imported and non-CoreAudio functions to work without pyobjc
- Private Aggregate Device (isPrivate=1) per research recommendation -- process-scoped, no leftover devices in Audio MIDI Setup
- BlackHole set as clock master for Aggregate Device per Pitfall 2 guidance -- avoids sample rate mismatch issues
- destroy_aggregate_device logs warning but does not raise on failure -- cleanup should not crash the app

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None - all functions are fully implemented with real logic (CoreAudio calls are lazy-imported, not stubbed).

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- core/system_audio.py ready for integration by Plan 02 (BlackHole wizard UI) and Plan 03 (recording integration)
- All 6 public functions exported and tested
- Settings schema ready for wizard to persist device UIDs

## Self-Check: PASSED

All files and commits verified.

---
*Phase: 02-system-audio-capture*
*Completed: 2026-03-27*
