# Phase 7: Cross-Meeting Wiring Fixes - Research

**Researched:** 2026-04-02
**Domain:** PyQt6 widget integration, metadata indexing, signal wiring
**Confidence:** HIGH

## Summary

This phase addresses three deterministic wiring bugs that prevent Phase 5's cross-meeting analysis features from working at runtime. The bugs are well-defined and have clear fixes documented in the audit.

Bug 1: `SidebarWidget` is created in `app.py` (line 92) but never inserted into `MainWindow`'s layout. The old `QListWidget`-based sidebar (lines 811-829) is still the visible sidebar. Bug 2: `MetadataIndex.update_entry()` reads `meta["language"]` (singular) on line 67, but `create_transcript()` stores `meta["languages"]` (plural list). This means v2.0 transcripts with `languages` never get indexed correctly. Bug 3: `update_transcript_speakers()` on line 1656 of main_window.py does not pass `self._metadata_index`, so diarization results never update the index.

**Primary recommendation:** Fix all three bugs with minimal code changes: replace QListWidget sidebar with SidebarWidget in MainWindow layout, fix the field key in MetadataIndex, and add optional index parameter to `update_transcript_speakers`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: Replace the existing QListWidget-based sidebar in MainWindow with SidebarWidget from `ui/sidebar.py`. SidebarWidget already has all recording list functionality plus selection mode.
- D-02: Wire SidebarWidget signals in `app.py` following existing signal wiring patterns (transcript_selected, analysis_requested, etc.).
- D-03: Remove or deprecate the old QListWidget recording list code in MainWindow.
- D-04: Fix `metadata_index.py` line 67 to read `meta["languages"]` (plural list) instead of `meta["language"]` (singular). This matches the transcript schema established in Phase 3.
- D-05: Add fallback: `meta.get("languages", [meta["language"]] if "language" in meta else [])` to handle v1.0 transcripts that may have only `language` (singular).
- D-06: Add optional `index: MetadataIndex | None = None` parameter to `update_transcript_speakers()`, consistent with the `save_transcript()` pattern.
- D-07: In MainWindow `_on_diarization_done`, pass `self._metadata_index` to `update_transcript_speakers()`.

### Claude's Discretion
- Exact signal wiring order in app.py
- Whether to add a sidebar property to MainWindow for external access
- Test structure for the new wiring (extend existing tests vs new test file)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CMA-01 | User can select multiple transcripts for combined analysis | SidebarWidget already implements selection mode with checkboxes and analysis_requested signal. Fix is to make SidebarWidget visible in MainWindow layout (D-01, D-02, D-03). |
| CMA-03 | Lightweight transcript index maintains searchable metadata without loading full files | MetadataIndex exists and works except for the `language` vs `languages` field bug (D-04, D-05) and missing index update on diarization (D-06, D-07). |
</phase_requirements>

## Standard Stack

No new dependencies. All fixes use existing libraries already in the project.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyQt6 | >= 6.6 | UI framework, signals/slots, QSplitter layout | Already in project |

### Supporting
No new supporting libraries needed.

## Architecture Patterns

### Bug 1: SidebarWidget Layout Integration

**Current state:** `app.py` creates `SidebarWidget` (line 92) and wires its signals, but it is a standalone widget never added to `MainWindow`'s layout. Meanwhile, `MainWindow._setup_ui()` creates its own `QListWidget` sidebar (lines 811-829) and adds it to the `QSplitter`.

**Fix pattern:** Replace the QListWidget construction in `MainWindow._setup_ui()` with SidebarWidget. MainWindow should accept `sidebar: SidebarWidget` as a constructor parameter (or create one internally), then add it to `self._splitter` as the left panel.

**Key integration points:**
1. `MainWindow.__init__()` -- accept or create SidebarWidget
2. `MainWindow._setup_ui()` -- replace lines 811-829 with SidebarWidget
3. `MainWindow._refresh_recording_list()` -- delegate to `SidebarWidget.refresh()` or remove
4. `MainWindow._on_recording_selected()` -- adapt to SidebarWidget's `transcript_selected` signal (emits path string, not QListWidgetItem)
5. `MainWindow._on_recording_context_menu()` -- remove (SidebarWidget has its own context menu)
6. `MainWindow._delete_recording()` -- adapt to work without QListWidget reference
7. `MainWindow.sidebar` property (line 2008) -- return type changes from QListWidget to SidebarWidget
8. `app.py` -- sidebar signals are already wired (lines 92-101), need to pass sidebar to MainWindow instead of creating separately

**Import changes in main_window.py:** Remove `QListWidget`, `QListWidgetItem` imports if no longer used elsewhere. Add SidebarWidget import.

### Bug 2: MetadataIndex Field Fix

**Current code (line 67):**
```python
"languages": [meta["language"]] if "language" in meta else [],
```

**Fixed code (D-04 + D-05):**
```python
"languages": meta.get("languages", [meta["language"]] if "language" in meta else []),
```

This first checks for `languages` (plural, v2.0 schema), then falls back to wrapping `language` (singular, v1.0 schema) in a list.

### Bug 3: Speaker Update Index Wiring

**Current `update_transcript_speakers` signature:**
```python
def update_transcript_speakers(
    path: pathlib.Path,
    segments: list[dict[str, Any]],
    speakers: dict[str, str],
    diarization_meta: dict[str, str],
) -> dict[str, Any]:
```

**Fixed signature (D-06):**
```python
def update_transcript_speakers(
    path: pathlib.Path,
    segments: list[dict[str, Any]],
    speakers: dict[str, str],
    diarization_meta: dict[str, str],
    *,
    index: MetadataIndex | None = None,
) -> dict[str, Any]:
```

The function already calls `save_transcript(transcript, path)` internally (line 120). Change to `save_transcript(transcript, path, index=index)` to propagate the index.

**Caller fix (D-07):** In `MainWindow._on_diarization_done()` line 1656:
```python
# Before:
update_transcript_speakers(transcript_path, result, speakers, diarization_meta)
# After:
update_transcript_speakers(transcript_path, result, speakers, diarization_meta, index=self._metadata_index)
```

### Anti-Patterns to Avoid
- **Duplicating sidebar logic:** Do not recreate recording list functionality in MainWindow. SidebarWidget already handles folder browsing, transcript listing, and context menus.
- **Breaking existing signal wiring:** The `app.py` already has SidebarWidget signal connections. Do not duplicate them in MainWindow.
- **Modifying SidebarWidget itself:** This phase is about wiring, not feature changes. SidebarWidget is complete.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sidebar folder tree | New QListWidget-based tree | Existing SidebarWidget | Already built in Phase 5 with full functionality |
| Transcript selection UI | Custom checkbox overlay | SidebarWidget selection mode | Already implemented with checkbox propagation |

## Common Pitfalls

### Pitfall 1: RecordingListItem Widget References
**What goes wrong:** MainWindow has a custom `RecordingListItem` widget class used with QListWidget. Removing QListWidget may leave dead code.
**Why it happens:** The `RecordingListItem` class and `_refresh_recording_list()` method are QListWidget-specific.
**How to avoid:** Remove or keep `RecordingListItem` class and `_refresh_recording_list()` method based on whether SidebarWidget's tree view provides equivalent display. SidebarWidget uses `QStandardItem` text labels, not custom widgets with styled title/date/duration rows.
**Warning signs:** `RecordingListItem` references in code with no QListWidget to host them.

### Pitfall 2: Signal Connection Duplication
**What goes wrong:** `app.py` already connects `sidebar.transcript_selected` to a lambda that calls `window._transcript_viewer.display_transcript(path)`. If MainWindow internally also connects the same signal, transcript selection fires twice.
**Why it happens:** Signal wiring exists in two places: `app.py` (external) and `MainWindow.__init__` (internal).
**How to avoid:** Choose one location for all SidebarWidget signal connections. Since `app.py` already has them, MainWindow should not duplicate. Alternatively, move all wiring into MainWindow and remove from `app.py`.
**Warning signs:** Double transcript loads, flickering UI on selection.

### Pitfall 3: Property Type Change Breaking External Code
**What goes wrong:** `MainWindow.sidebar` property returns `QListWidget` (line 2008). Changing to `SidebarWidget` may break code that calls QListWidget-specific methods.
**Why it happens:** External code (tests, app.py) may use QListWidget API.
**How to avoid:** Search all usages of `window.sidebar` and `window._recording_list` before changing. Update return type annotation.
**Warning signs:** AttributeError at runtime.

### Pitfall 4: v1.0 Transcripts Without Either Field
**What goes wrong:** Old transcripts may have neither `language` nor `languages` in metadata.
**Why it happens:** Very early transcripts or manually created ones may lack language fields entirely.
**How to avoid:** D-05's fallback handles this: `meta.get("languages", [meta["language"]] if "language" in meta else [])` returns `[]` when neither exists.
**Warning signs:** KeyError during MetadataIndex rebuild.

## Code Examples

### MetadataIndex Fix (D-04 + D-05)
```python
# In metadata_index.py, update_entry(), line 67
# Before:
"languages": [meta["language"]] if "language" in meta else [],
# After:
"languages": meta.get("languages", [meta["language"]] if "language" in meta else []),
```

### update_transcript_speakers Fix (D-06)
```python
# In transcript_store.py
def update_transcript_speakers(
    path: pathlib.Path,
    segments: list[dict[str, Any]],
    speakers: dict[str, str],
    diarization_meta: dict[str, str],
    *,
    index: MetadataIndex | None = None,
) -> dict[str, Any]:
    transcript = load_transcript(path)
    transcript["version"] = "2.0"
    transcript["segments"] = segments
    transcript["metadata"]["speakers"] = speakers
    transcript["metadata"]["diarization"] = diarization_meta
    save_transcript(transcript, path, index=index)  # pass index through
    return transcript
```

### MainWindow SidebarWidget Integration
```python
# In MainWindow.__init__ or _setup_ui
# Replace QListWidget creation with SidebarWidget parameter
def __init__(self, workspace: WorkspaceManager, sidebar: SidebarWidget | None = None, ...) -> None:
    self._sidebar = sidebar or SidebarWidget(workspace=workspace)
    ...

def _setup_ui(self) -> None:
    ...
    # Replace lines 811-829 with:
    self._splitter.addWidget(self._sidebar)
    ...
```

## State of the Art

No technology changes. This is a bug-fix-only phase using established patterns.

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| QListWidget sidebar in MainWindow | SidebarWidget (QTreeView-based) | Phase 5 | SidebarWidget built but never integrated into layout |

## Open Questions

1. **RecordingListItem deprecation**
   - What we know: MainWindow has a custom `RecordingListItem` widget with styled title/date/duration display
   - What's unclear: SidebarWidget's tree view shows simpler text labels. Is the richer display needed?
   - Recommendation: Claude's discretion. SidebarWidget shows folder names and transcript names without duration/date. The transcript viewer shows full details when selected. Remove RecordingListItem and `_refresh_recording_list` as dead code.

2. **Signal wiring location**
   - What we know: `app.py` already wires `sidebar.analysis_requested`, `sidebar.analysis_selected`, `sidebar.transcript_selected`
   - What's unclear: Should all sidebar signals be in `app.py` or move some into MainWindow?
   - Recommendation: Keep analysis signals in `app.py` (they call MainWindow private methods). Move `transcript_selected` connection into MainWindow since it's purely internal (show/hide transcript viewer). This avoids lambda accessing private attributes from outside.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0 + pytest-qt 4.5 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_metadata_index.py tests/test_sidebar.py -x --tb=short` |
| Full suite command | `pytest tests/ -x --tb=short -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CMA-01 | SidebarWidget visible in MainWindow, selection mode accessible | unit | `pytest tests/test_sidebar.py -x` | Yes (selection mode tests exist) |
| CMA-01 | SidebarWidget integrated in MainWindow layout | integration | Needs new test verifying MainWindow has SidebarWidget in splitter | No -- Wave 0 |
| CMA-03 | MetadataIndex reads `languages` (plural) correctly | unit | `pytest tests/test_metadata_index.py -x` | Yes (but test uses `language` singular -- needs update) |
| CMA-03 | MetadataIndex fallback for v1.0 `language` field | unit | `pytest tests/test_metadata_index.py -x` | No -- Wave 0 |
| CMA-03 | update_transcript_speakers updates MetadataIndex | unit | Needs new test | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_metadata_index.py tests/test_sidebar.py -x --tb=short`
- **Per wave merge:** `pytest tests/ -x --tb=short -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_metadata_index.py::test_update_entry_v2_languages` -- covers CMA-03 with v2.0 `languages` field
- [ ] `tests/test_metadata_index.py::test_update_entry_v1_fallback` -- covers CMA-03 v1.0 fallback
- [ ] `tests/test_metadata_index.py::test_update_entry_no_language_field` -- covers edge case with neither field
- [ ] `tests/test_metadata_index.py::test_update_transcript_speakers_updates_index` -- covers CMA-03 index update after diarization
- [ ] Update existing `test_update_entry` to use v2.0 `languages` (plural) in test transcript

## Sources

### Primary (HIGH confidence)
- Direct code inspection of `src/meeting_transcriber/ui/main_window.py` (lines 811-829, 1030-1058, 1630-1661, 2007-2010)
- Direct code inspection of `src/meeting_transcriber/storage/metadata_index.py` (line 67)
- Direct code inspection of `src/meeting_transcriber/storage/transcript_store.py` (lines 96-121)
- Direct code inspection of `src/meeting_transcriber/ui/sidebar.py` (full widget)
- Direct code inspection of `src/meeting_transcriber/app.py` (lines 92-101)
- Existing test files: `tests/test_metadata_index.py`, `tests/test_sidebar.py`

### Secondary (MEDIUM confidence)
- CONTEXT.md decisions from user discussion

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new dependencies, all existing code
- Architecture: HIGH - bugs are deterministic with clear fixes, code fully inspected
- Pitfalls: HIGH - all integration points identified by code inspection

**Research date:** 2026-04-02
**Valid until:** 2026-05-02 (stable -- bug fix phase, no external dependencies)
