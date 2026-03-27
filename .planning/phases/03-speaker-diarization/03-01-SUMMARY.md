---
phase: 03-speaker-diarization
plan: 01
subsystem: core
tags: [pyannote, diarization, speaker-id, schema-v2, qthread]

# Dependency graph
requires:
  - phase: 01-export-byok
    provides: "SRT/VTT exporter with speaker label support, Keychain utility"
provides:
  - "DiarizationWorker QThread for running pyannote pipeline"
  - "align_speakers temporal overlap algorithm"
  - "rename_speaker utility for speaker label changes"
  - "DiarizationModelManager for cache detection"
  - "Schema v2.0 transcript format with optional speaker fields"
  - "update_transcript_speakers for upgrading existing transcripts"
  - "DiarizationError exception class"
  - "DIARIZATION_MODEL, DIARIZATION_DEVICE, DIARIZATION_CACHE_DIR constants"
affects: [03-02, 03-03]

# Tech tracking
tech-stack:
  added: ["pyannote.audio>=4.0,<5.0 (optional diarization extra)"]
  patterns: ["Lazy import for heavy deps (pyannote/torch inside run() only)", "Schema versioning with backward compat"]

key-files:
  created:
    - src/meeting_transcriber/core/diarizer.py
    - tests/test_diarizer.py
  modified:
    - src/meeting_transcriber/utils/constants.py
    - src/meeting_transcriber/utils/exceptions.py
    - src/meeting_transcriber/storage/transcript_store.py
    - tests/test_storage.py
    - tests/test_exporter.py
    - pyproject.toml

key-decisions:
  - "CPU-only for pyannote inference -- MPS sparse tensor bugs (PyTorch #143955)"
  - "Lazy import via helper functions (_import_pipeline, _import_torch) for testability"
  - "Schema v2.0 only written when speakers provided -- v1.0 transcripts never modified"
  - "itertracks(yield_label=True) for extracting speaker turns from pyannote output"

patterns-established:
  - "Lazy import helpers: _import_X() functions wrapping heavy deps for mock-friendly testing"
  - "Schema versioning: conditional v2.0 upgrade only when new data is present"
  - "Temporal overlap alignment: max(0, min(seg_end, turn_end) - max(seg_start, turn_start))"

requirements-completed: [DIAR-01, DIAR-03, DIAR-04]

# Metrics
duration: 5min
completed: 2026-03-27
---

# Phase 03 Plan 01: Core Diarization Engine Summary

**DiarizationWorker QThread with pyannote pipeline, temporal speaker alignment, schema v2.0 with backward-compatible speaker fields, and on-demand model download with progress reporting**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-27T17:57:00Z
- **Completed:** 2026-03-27T18:02:00Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- DiarizationWorker QThread runs pyannote.audio pipeline with lazy imports (no module-level torch/pyannote)
- align_speakers algorithm assigns speaker labels via maximum temporal overlap
- rename_speaker updates all matching segments and metadata speakers dict
- DiarizationModelManager detects HuggingFace hub cache for model download status
- Schema v2.0 adds optional speakers/diarization metadata; v1.0 transcripts unmodified
- update_transcript_speakers upgrades existing v1.0 transcripts to v2.0
- SRT/VTT speaker label export verified with 4 new tests
- 10 diarizer tests + 7 storage tests + 4 exporter tests = 21 new tests, all passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Core diarization engine** (TDD)
   - `0485288` (test) - Failing tests for diarizer
   - `ea2cb90` (feat) - DiarizationWorker, align_speakers, rename_speaker, DiarizationModelManager, constants, exceptions

2. **Task 2: Schema v2.0 + export tests** (TDD)
   - `153c52b` (test) - Failing tests for schema v2.0 and speaker exports
   - `edd3c70` (feat) - Schema v2.0 in transcript_store, update_transcript_speakers

## Files Created/Modified
- `src/meeting_transcriber/core/diarizer.py` - DiarizationWorker, align_speakers, rename_speaker, DiarizationModelManager
- `src/meeting_transcriber/utils/constants.py` - DIARIZATION_MODEL, DIARIZATION_DEVICE, DIARIZATION_CACHE_DIR
- `src/meeting_transcriber/utils/exceptions.py` - DiarizationError exception
- `src/meeting_transcriber/storage/transcript_store.py` - Schema v2.0 create_transcript, update_transcript_speakers
- `pyproject.toml` - pyannote.audio>=4.0,<5.0 diarization extra
- `tests/test_diarizer.py` - 10 tests for diarizer module
- `tests/test_storage.py` - 7 new tests for schema v2.0
- `tests/test_exporter.py` - 4 new speaker label export tests

## Decisions Made
- CPU-only inference: MPS has sparse tensor bugs with pyannote (PyTorch issue #143955), so DIARIZATION_DEVICE is hardcoded to "cpu"
- Lazy import helpers: Created _import_pipeline() and _import_torch() wrapper functions rather than patching sys.modules, enabling clean mock injection in tests
- Schema v2.0 conditional: Only set version to "2.0" when speakers param is provided; callers without diarization data still get v1.0
- pyannote.audio version: Bumped from >=3.1 to >=4.0,<5.0 per research findings on community-1 model compatibility

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all functions are fully implemented with real logic.

## Next Phase Readiness
- Core diarization engine ready for UI integration in Plan 02
- DiarizationWorker signals (progress, finished) match existing QThread patterns
- Schema v2.0 backward compatibility ensures existing transcripts work seamlessly
- Plan 02 can wire "Identify Speakers" button to DiarizationWorker
- Plan 03 can add HuggingFace token settings to SettingsDialog

---
## Self-Check: PASSED

All 8 files verified present. All 4 commit hashes found in git log.

---
*Phase: 03-speaker-diarization*
*Completed: 2026-03-27*
