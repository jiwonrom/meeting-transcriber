---
phase: 07-cross-meeting-wiring-fixes
plan: 01
subsystem: storage
tags: [metadata-index, transcript-store, diarization, languages]

requires:
  - phase: 05-cross-meeting-intelligence
    provides: MetadataIndex and transcript_store with index kwarg pattern
provides:
  - Fixed MetadataIndex language field reading for v2.0 transcripts
  - MetadataIndex update propagation through update_transcript_speakers
affects: [07-02, cross-meeting search, diarization pipeline]

tech-stack:
  added: []
  patterns:
    - "meta.get('languages', fallback) for v1.0/v2.0 schema compat"
    - "Optional index kwarg propagation through transcript mutation functions"

key-files:
  created: []
  modified:
    - src/meeting_transcriber/storage/metadata_index.py
    - src/meeting_transcriber/storage/transcript_store.py
    - src/meeting_transcriber/ui/main_window.py
    - tests/test_metadata_index.py

key-decisions:
  - "Prefer meta.get('languages', fallback) over separate if/elif for concise v1.0/v2.0 compat"

patterns-established:
  - "Language field compat: always read languages (plural) first, wrap language (singular) as list fallback"

requirements-completed: [CMA-03]

duration: 3min
completed: 2026-04-02
---

# Phase 07 Plan 01: MetadataIndex Language Fix and Speaker Update Wiring Summary

**Fixed MetadataIndex to read v2.0 languages list with v1.0 fallback, and wired index updates through update_transcript_speakers**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-02T06:17:52Z
- **Completed:** 2026-04-02T06:20:52Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- MetadataIndex correctly reads `languages` (plural list) from v2.0 transcripts, falls back to `language` (singular) for v1.0, returns empty list when neither exists
- update_transcript_speakers accepts optional index kwarg and propagates it to save_transcript
- MainWindow._on_diarization_done passes self._metadata_index so diarization results update the index
- 10 passing tests covering all edge cases

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix MetadataIndex language field and add tests** - `b062fa2` (feat)
2. **Task 2: Wire MetadataIndex through update_transcript_speakers** - `075090c` (feat)

_Both tasks used TDD: RED (failing tests) -> GREEN (implementation) -> verified_

## Files Created/Modified
- `src/meeting_transcriber/storage/metadata_index.py` - Fixed language field to read v2.0 `languages` first with v1.0 `language` fallback
- `src/meeting_transcriber/storage/transcript_store.py` - Added optional `index` kwarg to `update_transcript_speakers`, passes through to `save_transcript`
- `src/meeting_transcriber/ui/main_window.py` - `_on_diarization_done` now passes `self._metadata_index` to `update_transcript_speakers`
- `tests/test_metadata_index.py` - Added 5 new tests: v2.0 languages, v1.0 fallback, no-field edge case, speaker update with index, speaker update without index

## Decisions Made
- Prefer `meta.get("languages", fallback)` one-liner over multi-branch if/elif for concise v1.0/v2.0 schema compatibility

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Package needed reinstall (`pip install -e .`) after merge to pick up source changes in worktree

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- MetadataIndex now correctly indexes language data from both v1.0 and v2.0 transcripts
- Diarization results properly update the metadata index
- Ready for 07-02 plan execution

---
*Phase: 07-cross-meeting-wiring-fixes*
*Completed: 2026-04-02*
