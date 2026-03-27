---
phase: 03-speaker-diarization
plan: 03
subsystem: core
tags: [coreml, pyannote, apple-silicon, ane, diarization]

requires:
  - phase: 03-01
    provides: "DiarizationWorker with CPU-based pyannote pipeline"
provides:
  - "CoreML conversion attempt for pyannote segmentation model"
  - "Cached CoreML model at DIARIZATION_COREML_DIR/segmentation.mlpackage"
  - "Transparent CPU fallback when CoreML unavailable or conversion fails"
affects: []

tech-stack:
  added: [coremltools (optional lazy import)]
  patterns: [CoreML conversion with silent fallback, cached model artifacts]

key-files:
  created: []
  modified:
    - src/meeting_transcriber/core/diarizer.py
    - src/meeting_transcriber/utils/constants.py
    - tests/test_diarizer.py

key-decisions:
  - "CoreML conversion via coremltools lazy import -- no hard dependency"
  - "CPU is only fallback (no MPS) per PyTorch sparse tensor bugs"
  - "_try_coreml_pipeline accepts ct parameter for testability instead of internal import"

patterns-established:
  - "Optional accelerator pattern: try hardware optimization, fallback to CPU silently"

requirements-completed: [DIAR-01]

duration: 3min
completed: 2026-03-27
---

# Phase 03 Plan 03: CoreML/ANE Optimization Summary

**CoreML conversion attempt for pyannote segmentation model with cached .mlpackage and transparent CPU fallback**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-27T18:04:35Z
- **Completed:** 2026-03-27T18:08:00Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 3

## Accomplishments
- Added `_try_coreml_pipeline` method that attempts CoreML conversion of pyannote segmentation model
- CoreML model cached to `DIARIZATION_COREML_DIR/segmentation.mlpackage` to avoid repeated conversion
- Transparent CPU fallback when coremltools is unavailable or conversion fails -- no user-visible degradation
- 6 new CoreML-specific tests covering success, failure, cache, and worker integration paths

## Task Commits

Each task was committed atomically:

1. **Task 1: CoreML conversion attempt with CPU fallback gate**
   - RED: `7126a99` (test) -- failing CoreML tests
   - GREEN: `ce6a7e9` (feat) -- implementation passing all tests

## Files Created/Modified
- `src/meeting_transcriber/core/diarizer.py` - Added `_try_coreml_pipeline` method and CoreML gate in `run()`
- `src/meeting_transcriber/utils/constants.py` - Added `DIARIZATION_COREML_DIR` constant
- `tests/test_diarizer.py` - Added `TestCoreMLOptimization` class with 6 tests

## Decisions Made
- CoreML conversion uses coremltools lazy import -- no hard dependency added to pyproject.toml
- CPU is the only fallback (no MPS path) per PyTorch issue #143955 sparse tensor bugs
- `_try_coreml_pipeline` takes `ct` parameter directly for clean testability rather than internal lazy import

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## Known Stubs
None - all code paths are fully wired.

## User Setup Required
None - coremltools is optional. If not installed, CPU inference is used transparently.

## Next Phase Readiness
- CoreML optimization is a stretch goal; CPU path remains the reliable default
- Speaker diarization feature complete across all 3 plans

---
*Phase: 03-speaker-diarization*
*Completed: 2026-03-27*
