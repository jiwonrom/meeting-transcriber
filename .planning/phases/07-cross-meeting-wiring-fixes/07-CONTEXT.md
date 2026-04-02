# Phase 7: Cross-Meeting Analysis Wiring Fixes - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase fixes integration wiring so Phase 5 cross-meeting analysis features work at runtime. Three concrete bugs: (1) SidebarWidget created but never shown in MainWindow layout, (2) MetadataIndex reads wrong field key for languages, (3) update_transcript_speakers bypasses MetadataIndex. No new features, no UI redesign — pure wiring fixes.

</domain>

<decisions>
## Implementation Decisions

### SidebarWidget Layout Integration
- **D-01:** Replace the existing QListWidget-based sidebar in MainWindow with SidebarWidget from `ui/sidebar.py`. SidebarWidget already has all recording list functionality plus selection mode.
- **D-02:** Wire SidebarWidget signals in `app.py` following existing signal wiring patterns (transcript_selected, analysis_requested, etc.).
- **D-03:** Remove or deprecate the old QListWidget recording list code in MainWindow.

### MetadataIndex Field Fix
- **D-04:** Fix `metadata_index.py` line 67 to read `meta["languages"]` (plural list) instead of `meta["language"]` (singular). This matches the transcript schema established in Phase 3.
- **D-05:** Add fallback: `meta.get("languages", [meta["language"]] if "language" in meta else [])` to handle v1.0 transcripts that may have only `language` (singular).

### Speaker Update Index Wiring
- **D-06:** Add optional `index: MetadataIndex | None = None` parameter to `update_transcript_speakers()`, consistent with the `save_transcript()` pattern.
- **D-07:** In MainWindow `_on_diarization_done`, pass `self._metadata_index` to `update_transcript_speakers()`.

### Claude's Discretion
- Exact signal wiring order in app.py
- Whether to add a sidebar property to MainWindow for external access
- Test structure for the new wiring (extend existing tests vs new test file)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core Files to Fix
- `src/meeting_transcriber/ui/main_window.py` -- Contains QListWidget sidebar (lines 811-829) to be replaced; contains `_on_diarization_done` that needs MetadataIndex pass-through
- `src/meeting_transcriber/storage/metadata_index.py` -- Line 67 has `language` vs `languages` bug
- `src/meeting_transcriber/storage/transcript_store.py` -- `update_transcript_speakers()` needs optional index param

### Reference Implementation
- `src/meeting_transcriber/ui/sidebar.py` -- SidebarWidget with QTreeView, selection mode, analysis_requested signal
- `src/meeting_transcriber/app.py` -- Signal wiring patterns for existing widgets

### Audit Evidence
- `.planning/v2.0-MILESTONE-AUDIT.md` -- Full audit report with issue descriptions
- `.planning/phases/05-cross-meeting-analysis/05-CONTEXT.md` -- Original Phase 5 decisions

### Requirements
- `.planning/REQUIREMENTS.md` -- CMA-01, CMA-03

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SidebarWidget` (sidebar.py): Fully built with QTreeView, QStandardItemModel, selection mode toggle, folder-level checkboxes, "Analyze N selected" button. Ready to drop in.
- `MetadataIndex` (metadata_index.py): Working index with rebuild capability. Only needs field key fix.
- `update_transcript_speakers` (transcript_store.py): Already follows the optional-index pattern from `save_transcript`. Just needs the parameter added.

### Established Patterns
- **Optional index parameter**: `save_transcript()` and `delete_recording()` both accept `index: MetadataIndex | None = None`. Same pattern for `update_transcript_speakers`.
- **Signal wiring in app.py**: All widget signals connected in `main()` function. SidebarWidget signals follow same pattern.
- **QSplitter layout**: MainWindow uses QSplitter for sidebar + content area. SidebarWidget replaces the left panel.

### Integration Points
- `app.py main()`: Add SidebarWidget signal connections
- `MainWindow.__init__`: Replace QListWidget with SidebarWidget
- `MainWindow._on_diarization_done`: Pass `self._metadata_index` to `update_transcript_speakers`
- `MetadataIndex.update_entry`: Fix language field key

</code_context>

<specifics>
## Specific Ideas

No specific requirements -- these are deterministic bug fixes with clear solutions from the audit report.

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 07-cross-meeting-wiring-fixes*
*Context gathered: 2026-04-02*
