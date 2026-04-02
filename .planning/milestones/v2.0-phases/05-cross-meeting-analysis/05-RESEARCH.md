# Phase 5: Cross-Meeting Analysis - Research

**Researched:** 2026-03-31
**Domain:** Multi-transcript AI analysis, metadata indexing, sidebar selection UX
**Confidence:** HIGH

## Summary

Phase 5 adds three capabilities: (1) multi-transcript selection in the sidebar, (2) AI-powered cross-meeting analysis that produces structured JSON with recurring topics, action items, and timeline, and (3) a lightweight JSON metadata index for fast transcript browsing. The codebase has strong established patterns for all three -- QThread workers for async AI, structured JSON rendering in TranscriptViewer via `setHtml()`, and filesystem-based storage in `WorkspaceManager`. No new dependencies are needed; this phase extends existing abstractions.

The primary technical consideration is prompt engineering for multi-transcript analysis. Gemini 2.0 Flash (the default model, confirmed via API) has a 1M token input limit, which comfortably fits dozens of full transcripts. The `AIProvider` ABC needs a new `analyze_cross_meeting()` method, each provider implements it with vendor-specific JSON mode (Gemini `response_mime_type`, OpenAI `json_object`, Anthropic prompt-only -- per Phase 4 decision D-vendor-specific JSON modes). The metadata index is a single `index.json` file with versioned schema, updated via hooks in `TranscriptStore` and `WorkspaceManager` operations.

**Primary recommendation:** Extend `AIProvider` with a new `analyze_cross_meeting()` abstract method, create a `CrossMeetingAnalysisWorker` QThread modeled after `AITaskWorker`, add selection mode to `SidebarWidget` with checkboxes and a sticky action bar, store analysis results as `analysis_{timestamp}.json` in `~/.meeting_transcriber/analyses/`, and build `MetadataIndex` as a new storage module that hooks into existing transcript CRUD.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Sidebar enters "selection mode" via a toolbar button (next to "+ New Folder"). Checkboxes appear next to each transcript. Toggle on/off.
- **D-02:** Cross-folder selection allowed -- users can check transcripts from any folder.
- **D-03:** Folder-level checkbox selects all transcripts within that folder.
- **D-04:** "Select All" and "Cancel" buttons in selection mode toolbar.
- **D-05:** Minimum 2 transcripts required, no upper limit. Gemini's 1M context window is the practical cap.
- **D-06:** "Analyze N selected" button appears as sticky bar at bottom of sidebar when >= 2 transcripts checked.
- **D-07:** Analysis output uses structured JSON (consistent with Phase 4 template summaries). Sections: `recurring_topics`, `action_items`, `timeline`.
- **D-08:** Recurring topics section shows topic name, which meetings it appeared in, and frequency.
- **D-09:** Action item tracker aggregates items across meetings, flags unresolved items, tracks completion status, includes assignee from speaker labels.
- **D-10:** Timeline section shows chronological progression of topics across meetings ordered by date.
- **D-11:** Mixed template types handled via unified analysis -- AI adapts to extract what's available from each transcript type. One combined output.
- **D-12:** Output language follows majority language of selected transcripts.
- **D-13:** Optional custom query text field lets users ask specific questions appended to the AI prompt (e.g., "What decisions changed since last month?").
- **D-14:** Analysis results exportable as Markdown file, reusing existing exporter pattern from Phase 1.
- **D-15:** Single `index.json` file in workspace root (`~/.meeting_transcriber/index.json`).
- **D-16:** Index updated on every transcript change (create, save, delete). Hook into TranscriptStore and WorkspaceManager operations.
- **D-17:** Indexed fields per transcript: title, created_at, duration_seconds, languages, folder, template_type (core), keywords, summary_snippet (AI-generated), segment_count, word_count (stats).
- **D-18:** Index versioned (`"version": "1.0"`) for future schema evolution.
- **D-19:** Analysis results displayed in TranscriptViewer panel (reused, not a new window). Content replaced when analysis is active.
- **D-20:** Inline progress indicator in viewer panel during analysis ("Analyzing N transcripts...").
- **D-21:** Analysis results saved persistently as JSON in workspace: `~/.meeting_transcriber/analyses/analysis_{timestamp}.json`.
- **D-22:** Saved analyses browsable from sidebar under a dedicated "Analyses" section below folder tree.
- **D-23:** Clicking a saved analysis in sidebar reopens it in TranscriptViewer.

### Claude's Discretion
- Exact AI prompt engineering for cross-meeting analysis
- JSON schema details for analysis result file
- How to render structured JSON sections as HTML in TranscriptViewer (inline styling approach from Phase 4 is reference)
- Index rebuild/migration logic for corrupted or missing index files
- Selection mode keyboard shortcuts (if any)
- Analysis section collapse/expand behavior in viewer

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CMA-01 | User can select multiple transcripts for combined analysis | Sidebar selection mode with QStandardItemModel checkboxes, cross-folder selection, sticky action bar (D-01 through D-06) |
| CMA-02 | AI generates cross-meeting summary highlighting recurring topics and action items | New `analyze_cross_meeting()` method on AIProvider ABC, CrossMeetingAnalysisWorker QThread, structured JSON output with `recurring_topics`, `action_items`, `timeline` sections (D-07 through D-13) |
| CMA-03 | Lightweight transcript index maintains searchable metadata without loading full files | Single `index.json` file with versioned schema, hooks into TranscriptStore/WorkspaceManager CRUD operations (D-15 through D-18) |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyQt6 | >= 6.6 | UI framework, QThread workers, signals/slots | Already in stack -- sidebar, TranscriptViewer, AITaskWorker |
| google-generativeai | 0.8.5 | Gemini API with JSON mode for structured output | Already installed, `response_mime_type` for structured JSON |
| pathlib | stdlib | Filesystem operations for index.json and analyses/ | Already used throughout storage module |
| json | stdlib | Index file read/write, analysis result serialization | Already used in transcript_store.py |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| datetime (stdlib) | -- | Timestamps for analysis files and index entries | Already used in transcript_store.py |
| dataclasses (stdlib) | -- | Frozen dataclasses for analysis results | Matches TranscriptionResult, AIResult patterns |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Single index.json | SQLite for index | Overkill -- hundreds of transcripts max, JSON is fast enough and consistent with filesystem approach |
| QStandardItemModel checkboxes | QListWidget with checkboxes | QStandardItemModel is already used in SidebarWidget, adding checkboxes is trivial |

**Installation:**
No new packages needed. Phase 5 uses only existing dependencies.

## Architecture Patterns

### Recommended Project Structure
```
src/meeting_transcriber/
├── ai/
│   ├── provider_base.py      # Add analyze_cross_meeting() abstract method
│   ├── gemini_provider.py    # Implement with response_mime_type JSON mode
│   ├── openai_provider.py    # Implement with json_object response format
│   ├── anthropic_provider.py # Implement with prompt-only JSON instruction
│   └── cross_meeting.py      # NEW: CrossMeetingAnalysisWorker QThread + CrossMeetingResult dataclass
├── storage/
│   ├── metadata_index.py     # NEW: MetadataIndex class for index.json CRUD
│   ├── analysis_store.py     # NEW: Analysis result save/load/list/delete
│   ├── transcript_store.py   # Hook: update index on create/save
│   ├── workspace.py          # Hook: update index on delete_recording/delete_folder
│   └── exporter.py           # Add export_analysis_to_markdown()
├── ui/
│   ├── sidebar.py            # Add selection mode, analyses section
│   └── main_window.py        # Add analysis display to TranscriptViewer
└── utils/
    ├── constants.py           # Add ANALYSES_DIR, INDEX_FILE constants
    └── exceptions.py          # Add AnalysisError exception
```

### Pattern 1: CrossMeetingAnalysisWorker (QThread)
**What:** Dedicated QThread worker for cross-meeting analysis, modeled after `AITaskWorker`.
**When to use:** When user clicks "Analyze N selected" button.
**Example:**
```python
# Follows AITaskWorker pattern from ai/tasks.py
class CrossMeetingResult:
    """Cross-meeting analysis result."""
    recurring_topics: list[dict[str, Any]]  # [{name, meetings, frequency}]
    action_items: list[dict[str, Any]]      # [{item, meeting, status, assignee}]
    timeline: list[dict[str, Any]]          # [{date, meeting, topic, detail}]
    custom_answer: str                       # Response to custom query (D-13)
    errors: list[str]

class CrossMeetingAnalysisWorker(QThread):
    progress = pyqtSignal(str)   # "Analyzing N transcripts..."
    finished = pyqtSignal(object)  # CrossMeetingResult

    def __init__(self, provider: AIProvider, transcripts: list[dict], ...):
        ...

    def run(self) -> None:
        # Concatenate transcript texts with metadata headers
        # Call provider.analyze_cross_meeting()
        # Parse JSON result into CrossMeetingResult
        ...
```

### Pattern 2: Sidebar Selection Mode
**What:** Toggle between normal browse mode and selection mode with checkboxes.
**When to use:** User clicks "Select" toolbar button.
**Example:**
```python
# QStandardItemModel supports checkboxes natively via setCheckable()
def _enter_selection_mode(self) -> None:
    self._selection_mode = True
    # Iterate all items, set checkable
    for i in range(self._model.rowCount()):
        folder_item = self._model.item(i)
        folder_item.setCheckable(True)
        folder_item.setCheckState(Qt.CheckState.Unchecked)
        for j in range(folder_item.rowCount()):
            child = folder_item.child(j)
            if child and child.data(Qt.ItemDataRole.UserRole + 1) == "transcript":
                child.setCheckable(True)

def _exit_selection_mode(self) -> None:
    self._selection_mode = False
    # Remove checkboxes from all items
    ...
```

### Pattern 3: MetadataIndex
**What:** Manages `~/.meeting_transcriber/index.json` with transcript metadata.
**When to use:** On every transcript CRUD operation and for sidebar display.
**Example:**
```python
class MetadataIndex:
    def __init__(self, workspace_root: pathlib.Path):
        self._index_path = workspace_root / "index.json"
        self._data = self._load_or_create()

    def update_entry(self, transcript_path: pathlib.Path, transcript: dict) -> None:
        """Update index entry from transcript data."""
        ...

    def remove_entry(self, transcript_path: pathlib.Path) -> None:
        """Remove entry when transcript is deleted."""
        ...

    def rebuild(self) -> None:
        """Full rebuild by scanning all transcript.json files."""
        ...

    def _load_or_create(self) -> dict:
        """Load existing index or create empty one with version."""
        ...
```

### Pattern 4: Analysis Display in TranscriptViewer
**What:** Reuse TranscriptViewer panel to display analysis results as inline-styled HTML.
**When to use:** When analysis completes or user clicks saved analysis.
**Example:**
```python
# Follows Phase 4 structured summary HTML rendering pattern
def display_analysis(self, result: CrossMeetingResult) -> None:
    html_parts: list[str] = []
    # Recurring topics section
    html_parts.append('<h2 style="...">Recurring Topics</h2>')
    for topic in result.recurring_topics:
        html_parts.append(f'<h3 style="...">{topic["name"]} ({topic["frequency"]}x)</h3>')
        html_parts.append(f'<p style="...">Meetings: {", ".join(topic["meetings"])}</p>')
    # Action items, timeline sections...
    self._summary_edit.setHtml("".join(html_parts))
```

### Anti-Patterns to Avoid
- **Loading full transcripts for sidebar display:** Use index.json metadata instead -- this is the whole point of CMA-03.
- **Modifying TranscriptViewer to have analysis-specific tabs:** Per D-19, reuse the existing panel. Replace content, don't add permanent tabs.
- **Running analysis on main thread:** Must use QThread worker. Multi-transcript analysis can take 10-30 seconds.
- **Mutating transcript files during analysis:** Analysis reads transcripts but never writes to them. Results go to separate `analyses/` directory.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Checkbox selection in tree | Custom checkbox widgets | `QStandardItem.setCheckable(True)` | Built into Qt's item model, handles tristate for folders natively |
| JSON structured output from AI | Manual JSON parsing from freeform text | Vendor-specific JSON modes (Gemini `response_mime_type`, OpenAI `json_object`) | Phase 4 already established this pattern, proven reliable |
| Transcript concatenation for AI input | Naive text concatenation | Header-delimited format with metadata per transcript | AI needs to distinguish which meeting said what |
| Index file corruption recovery | Manual recovery | `rebuild()` method that scans all transcript.json files | Single source of truth is the transcript files, index is derived |

**Key insight:** The metadata index is a cache/derived view, not a source of truth. If it gets corrupted, rebuild from transcript files. This means index writes don't need to be transactional -- worst case is a rebuild.

## Common Pitfalls

### Pitfall 1: Checkbox State Not Propagating to Children
**What goes wrong:** Checking a folder checkbox doesn't check its transcript children, or vice versa.
**Why it happens:** QStandardItemModel doesn't auto-propagate check state between parent/child items.
**How to avoid:** Connect to `itemChanged` signal and manually propagate: folder check -> set all children; child uncheck -> uncheck parent if no children checked; all children checked -> check parent.
**Warning signs:** Folder shows checked but "0 selected" in action bar.

### Pitfall 2: Index Stale After External Filesystem Changes
**What goes wrong:** User deletes a transcript folder outside the app, index still has the entry.
**Why it happens:** `QFileSystemWatcher` triggers sidebar refresh but doesn't trigger index update.
**How to avoid:** When sidebar refreshes from watcher, also validate index entries exist. Or do a lightweight consistency check on app startup.
**Warning signs:** Clicking an indexed transcript leads to FileNotFoundError.

### Pitfall 3: Token Limit Exceeded with Many Transcripts
**What goes wrong:** User selects 50+ transcripts, concatenated text exceeds model context window.
**Why it happens:** Gemini 2.0 Flash has 1M token limit (~750K words), but very large selections can exceed this.
**How to avoid:** Calculate approximate token count before sending (rough: 1 token per 4 chars). If exceeds ~900K tokens, warn user and suggest reducing selection. Use summaries instead of full text for very large sets.
**Warning signs:** API returns error about context length.

### Pitfall 4: Analysis Worker Thread Lifecycle
**What goes wrong:** User starts analysis, clicks away, starts another -- old worker still running.
**Why it happens:** No guard against concurrent analysis workers.
**How to avoid:** Track active worker reference. If new analysis requested while one is running, either queue or cancel the existing one. Use `QThread.isRunning()` check.
**Warning signs:** Multiple progress indicators, UI showing stale results.

### Pitfall 5: Empty or Minimal Transcripts in Selection
**What goes wrong:** User selects transcripts that have no segments or are very short, AI produces poor results.
**Why it happens:** No validation of selection quality before analysis.
**How to avoid:** Warn user if any selected transcript has zero segments. Show total word count in action bar to set expectations.
**Warning signs:** Analysis returns generic/empty sections.

## Code Examples

### Cross-Meeting AI Prompt Structure
```python
# Prompt engineering for multi-transcript analysis (Claude's discretion area)
def _build_analysis_prompt(
    transcripts: list[dict[str, Any]],
    custom_query: str | None = None,
    language: str = "auto",
) -> str:
    parts: list[str] = []
    parts.append(
        "Analyze the following meeting transcripts and produce a structured analysis."
    )
    parts.append("Output JSON with these sections:")
    parts.append('- "recurring_topics": [{name, meetings, frequency}]')
    parts.append('- "action_items": [{item, meeting, status, assignee}]')
    parts.append('- "timeline": [{date, meeting, topic, detail}]')

    if custom_query:
        parts.append(f'\nAlso answer this question: "{custom_query}"')
        parts.append('Include answer in "custom_answer" field.')

    lang_hint = f"\nRespond in {language}." if language != "auto" else ""
    parts.append(lang_hint)

    for i, t in enumerate(transcripts, 1):
        meta = t.get("metadata", {})
        title = meta.get("title", f"Meeting {i}")
        date = meta.get("created_at", "unknown")[:10]
        segments = t.get("segments", [])
        text = " ".join(seg.get("text", "") for seg in segments)
        parts.append(f"\n--- MEETING {i}: {title} ({date}) ---")
        parts.append(text)

    return "\n".join(parts)
```

### Index JSON Schema
```json
{
  "version": "1.0",
  "updated_at": "2026-03-31T12:00:00Z",
  "entries": {
    "Work/2026-03-30_standup/transcript.json": {
      "title": "Daily Standup",
      "created_at": "2026-03-30T09:00:00Z",
      "duration_seconds": 900,
      "languages": ["en"],
      "folder": "Work",
      "template_type": "team_meeting",
      "keywords": ["sprint", "blockers", "progress"],
      "summary_snippet": "Team discussed sprint progress...",
      "segment_count": 45,
      "word_count": 1200
    }
  }
}
```

### Analysis Result JSON Schema
```json
{
  "version": "1.0",
  "created_at": "2026-03-31T14:00:00Z",
  "transcript_paths": ["Work/meeting1/transcript.json", "Work/meeting2/transcript.json"],
  "transcript_count": 2,
  "custom_query": "What decisions changed?",
  "language": "en",
  "result": {
    "recurring_topics": [
      {"name": "Sprint Planning", "meetings": ["Daily Standup", "Sprint Review"], "frequency": 2}
    ],
    "action_items": [
      {"item": "Update documentation", "meeting": "Daily Standup", "status": "unresolved", "assignee": "Speaker 1"}
    ],
    "timeline": [
      {"date": "2026-03-28", "meeting": "Sprint Review", "topic": "Architecture Decision", "detail": "Decided to migrate to new API"}
    ],
    "custom_answer": "The team reversed the decision about..."
  }
}
```

### Sidebar Selection Mode Flow
```python
# Selection mode toolbar replaces normal toolbar
# D-01: "Select" button next to "+ New Folder"
# D-04: "Select All" and "Cancel" buttons in selection mode
# D-06: Sticky "Analyze N selected" bar at bottom

def _on_select_btn_clicked(self) -> None:
    self._enter_selection_mode()

def _get_checked_transcript_paths(self) -> list[str]:
    """Collect all checked transcript paths across all folders."""
    paths: list[str] = []
    for i in range(self._model.rowCount()):
        folder_item = self._model.item(i)
        for j in range(folder_item.rowCount()):
            child = folder_item.child(j)
            if (child
                and child.data(Qt.ItemDataRole.UserRole + 1) == "transcript"
                and child.checkState() == Qt.CheckState.Checked):
                paths.append(child.data(Qt.ItemDataRole.UserRole))
    return paths
```

### MetadataIndex Hook Pattern
```python
# In transcript_store.py -- hook index update into save_transcript
def save_transcript(
    transcript: dict[str, Any],
    path: pathlib.Path,
    index: MetadataIndex | None = None,
) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(transcript, f, indent=2, ensure_ascii=False)
    if index is not None:
        index.update_entry(path, transcript)
    return path
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Gemini 1.5 Flash (128K context) | Gemini 2.0 Flash (1M context) | 2024-12 | Multi-transcript analysis feasible without truncation |
| Freeform text AI output | Vendor-specific JSON mode | Phase 4 | Structured analysis output guaranteed parseable |
| Load all transcripts for sidebar | Metadata index lookup | Phase 5 (new) | Fast sidebar population without reading full files |

**Deprecated/outdated:**
- None relevant to this phase.

## Gemini Context Window Verification

**Verified via API (HIGH confidence):**
- `gemini-2.0-flash`: input_token_limit = 1,048,576 tokens, output = 8,192 tokens
- `gemini-2.5-flash`: input_token_limit = 1,048,576 tokens, output = 65,536 tokens
- A typical 1-hour meeting transcript is ~8,000-15,000 words (~10K-20K tokens)
- 1M tokens can fit ~50-100 full meeting transcripts comfortably
- Output limit of 8,192 tokens for gemini-2.0-flash may constrain very detailed analyses -- consider gemini-2.5-flash if available, or design prompts for concise output

## Open Questions

1. **Output Token Limit for Large Analyses**
   - What we know: gemini-2.0-flash has 8,192 output token limit; gemini-2.5-flash has 65,536
   - What's unclear: Whether 8K output tokens is sufficient for analyses spanning 20+ meetings
   - Recommendation: Design prompts for concise structured output. If output truncation detected, retry with "be more concise" instruction. Consider allowing users to upgrade to gemini-2.5-flash for large analyses.

2. **Index Performance at Scale**
   - What we know: JSON read/write is fast for hundreds of entries. Typical user has 10-100 transcripts.
   - What's unclear: Performance with 1000+ transcripts
   - Recommendation: JSON is fine for MVP. Add `rebuild()` for corruption recovery. If scale becomes an issue, migrate to SQLite in a future version.

3. **Folder-Level Check State Propagation**
   - What we know: Qt does support tristate checkboxes (Unchecked/PartiallyChecked/Checked)
   - What's unclear: Whether `QStandardItem` tristate works reliably with `QTreeView` for parent/child propagation
   - Recommendation: Implement manual propagation via `itemChanged` signal. Tristate on folder items: Checked (all children checked), PartiallyChecked (some checked), Unchecked (none checked).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ with pytest-qt 4.3+ |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/ -x --tb=short -v` |
| Full suite command | `pytest tests/ --tb=short -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CMA-01 | Sidebar selection mode: enter/exit, checkbox toggle, cross-folder select, folder-level select, action bar shows count | unit | `pytest tests/test_sidebar.py -x` | Exists (needs new tests) |
| CMA-01 | "Analyze N selected" button appears when >= 2 checked | unit | `pytest tests/test_sidebar.py::test_selection_mode_action_bar -x` | Wave 0 |
| CMA-02 | AIProvider.analyze_cross_meeting() returns structured JSON | unit | `pytest tests/test_ai_provider.py -x` | Exists (needs new tests) |
| CMA-02 | CrossMeetingAnalysisWorker emits progress and finished signals | unit | `pytest tests/test_cross_meeting.py -x` | Wave 0 |
| CMA-02 | Analysis result displayed as HTML in TranscriptViewer | unit | `pytest tests/test_main_window.py -x` | Exists (needs new tests) |
| CMA-03 | MetadataIndex CRUD: update, remove, rebuild | unit | `pytest tests/test_metadata_index.py -x` | Wave 0 |
| CMA-03 | Index updated on transcript save/delete | integration | `pytest tests/test_metadata_index.py::test_index_hooks -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x --tb=short -v`
- **Per wave merge:** `pytest tests/ --tb=short -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_cross_meeting.py` -- covers CMA-02 (CrossMeetingAnalysisWorker, CrossMeetingResult)
- [ ] `tests/test_metadata_index.py` -- covers CMA-03 (MetadataIndex CRUD, rebuild, hooks)
- [ ] `tests/test_analysis_store.py` -- covers analysis result save/load/list/delete

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `ai/provider_base.py`, `ai/tasks.py`, `ai/gemini_provider.py` -- established AIProvider ABC and QThread worker patterns
- Codebase inspection: `storage/workspace.py`, `storage/transcript_store.py` -- filesystem CRUD patterns, transcript JSON schema
- Codebase inspection: `ui/sidebar.py` -- QStandardItemModel-based tree with folder/transcript items
- Codebase inspection: `ui/main_window.py` -- TranscriptViewer with HTML rendering for structured summaries
- Gemini API: `genai.list_models()` -- confirmed 1M token input limit for gemini-2.0-flash and gemini-2.5-flash

### Secondary (MEDIUM confidence)
- PyQt6 QStandardItem checkable behavior -- based on Qt documentation patterns, consistent with QTreeView usage in codebase

### Tertiary (LOW confidence)
- None

## Project Constraints (from CLAUDE.md)

- **PEP8 + ruff**: All code must pass `ruff check` (line-length 100, rules E/F/I/N/W/UP)
- **Type hints + docstrings**: All public functions require type annotations and Korean docstrings
- **Tests required**: Every new feature must have pytest tests
- **Threading**: whisper.cpp and all I/O must run off main thread (QThread or subprocess)
- **API keys in Keychain**: No plaintext storage
- **No UI direct API calls**: ui/ modules must not call external APIs directly
- **No main thread blocking I/O**: All heavy operations via QThread
- **No transcript.json schema changes**: Existing schema must not be modified
- **Dependency direction**: ui -> core, ui -> ai, ai -> storage (unidirectional only)
- **Signal/Slot for reverse communication**: core/ai modules never reference UI directly

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - No new dependencies, all existing libraries sufficient
- Architecture: HIGH - All patterns directly extend established codebase patterns (AITaskWorker, TranscriptViewer HTML, WorkspaceManager CRUD)
- Pitfalls: HIGH - Based on direct codebase inspection and Qt standard behavior

**Research date:** 2026-03-31
**Valid until:** 2026-04-30 (stable domain, no fast-moving dependencies)
