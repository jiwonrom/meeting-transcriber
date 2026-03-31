# Phase 5: Cross-Meeting Analysis - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase adds cross-meeting analysis: users select multiple transcripts via sidebar checkboxes, trigger AI analysis that produces structured insights (recurring topics, action items, timeline), and view/export/save results. A lightweight JSON metadata index enables fast transcript browsing without loading full files. No changes to recording, transcription, or single-transcript AI features.

</domain>

<decisions>
## Implementation Decisions

### Multi-Transcript Selection UX
- **D-01:** Sidebar enters "selection mode" via a toolbar button (next to "+ New Folder"). Checkboxes appear next to each transcript. Toggle on/off.
- **D-02:** Cross-folder selection allowed -- users can check transcripts from any folder.
- **D-03:** Folder-level checkbox selects all transcripts within that folder.
- **D-04:** "Select All" and "Cancel" buttons in selection mode toolbar.
- **D-05:** Minimum 2 transcripts required, no upper limit. Gemini's 1M context window is the practical cap.
- **D-06:** "Analyze N selected" button appears as sticky bar at bottom of sidebar when >= 2 transcripts checked.

### Cross-Meeting Insight Format
- **D-07:** Analysis output uses structured JSON (consistent with Phase 4 template summaries). Sections: `recurring_topics`, `action_items`, `timeline`.
- **D-08:** Recurring topics section shows topic name, which meetings it appeared in, and frequency.
- **D-09:** Action item tracker aggregates items across meetings, flags unresolved items, tracks completion status, includes assignee from speaker labels.
- **D-10:** Timeline section shows chronological progression of topics across meetings ordered by date.
- **D-11:** Mixed template types handled via unified analysis -- AI adapts to extract what's available from each transcript type. One combined output.
- **D-12:** Output language follows majority language of selected transcripts.
- **D-13:** Optional custom query text field lets users ask specific questions appended to the AI prompt (e.g., "What decisions changed since last month?").
- **D-14:** Analysis results exportable as Markdown file, reusing existing exporter pattern from Phase 1.

### Metadata Index
- **D-15:** Single `index.json` file in workspace root (`~/.meeting_transcriber/index.json`).
- **D-16:** Index updated on every transcript change (create, save, delete). Hook into TranscriptStore and WorkspaceManager operations.
- **D-17:** Indexed fields per transcript: title, created_at, duration_seconds, languages, folder, template_type (core), keywords, summary_snippet (AI-generated), segment_count, word_count (stats).
- **D-18:** Index versioned (`"version": "1.0"`) for future schema evolution.

### Analysis Trigger & Results Display
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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### AI Pipeline
- `src/meeting_transcriber/ai/provider_base.py` -- AIProvider ABC. Cross-meeting analysis will need a new method or extended `summarize()` call.
- `src/meeting_transcriber/ai/tasks.py` -- AITaskWorker pipeline. Reference for QThread-based AI work pattern.
- `src/meeting_transcriber/ai/gemini_provider.py` -- Reference provider with JSON mode (`response_mime_type`). Phase 4 D-vendor-specific JSON modes apply.

### Transcript Storage & Index
- `src/meeting_transcriber/storage/transcript_store.py` -- `create_transcript()`, `save_transcript()`, `load_transcript()`. Index hooks go here.
- `src/meeting_transcriber/storage/workspace.py` -- `WorkspaceManager` with folder CRUD, `list_transcripts()`, `delete_recording()`. Index hooks go here too.
- `src/meeting_transcriber/storage/exporter.py` -- Existing Markdown/TXT/SRT/VTT export. Cross-meeting Markdown export extends this.

### UI Integration Points
- `src/meeting_transcriber/ui/sidebar.py` -- `SidebarWidget` with `QTreeView`, `QStandardItemModel`, single-selection signals. Must add selection mode.
- `src/meeting_transcriber/ui/main_window.py` -- MainWindow with TranscriptViewer. Analysis results display here.
- `src/meeting_transcriber/ui/theme.py` -- ThemeEngine for consistent styling of analysis view.

### Config & Utils
- `src/meeting_transcriber/utils/constants.py` -- Central constants. Add analysis-related constants.
- `src/meeting_transcriber/utils/config.py` -- Settings management.
- `src/meeting_transcriber/utils/exceptions.py` -- Exception hierarchy. Add analysis-specific exceptions if needed.

### Requirements
- `.planning/REQUIREMENTS.md` -- CMA-01, CMA-02, CMA-03

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SidebarWidget` (sidebar.py): QTreeView + QStandardItemModel + QFileSystemWatcher. Foundation for selection mode -- needs checkbox extension.
- `AITaskWorker` (tasks.py): QThread pattern for async AI calls. Can be extended or paralleled for cross-meeting analysis.
- `TranscriptViewer` (main_window.py): QTextEdit-based viewer with HTML rendering. Phase 4 added structured summary display with `setHtml()`.
- `Exporter` (exporter.py): Markdown/TXT/SRT/VTT export functions. Cross-meeting Markdown export follows this pattern.
- `WorkspaceManager` (workspace.py): Filesystem CRUD. `list_folders()`, `list_transcripts()` -- index hooks attach here.
- Phase 4 structured JSON summaries: `metadata.summary` stored as dict with section arrays. Direct input for cross-meeting analysis.

### Established Patterns
- **QThread workers with signal-based result delivery**: All heavy work (AI, transcription, audio) uses this pattern.
- **Structured JSON for AI output**: Phase 4 established vendor-specific JSON mode (Gemini `response_mime_type`, OpenAI `json_object`, Anthropic prompt-only).
- **HTML rendering in QTextEdit**: Phase 4 renders structured summaries as inline-styled HTML via `setHtml()`.
- **Lazy imports**: Phase 3/4 established `_import_X()` pattern for optional dependencies.
- **Status bar for user feedback**: Errors and progress via `QStatusBar.showMessage()`.

### Integration Points
- `SidebarWidget.transcript_selected` signal -- analysis mode needs a parallel `analysis_requested(list[str])` signal.
- `TranscriptViewer` in MainWindow -- needs to switch between transcript view and analysis view.
- `TranscriptStore.save_transcript()` / `WorkspaceManager.delete_recording()` -- index update hooks.
- `app.py` signal wiring -- new connections for selection mode and analysis flow.

</code_context>

<specifics>
## Specific Ideas

- Selection mode mockup with sticky "Analyze N selected" button at sidebar bottom was chosen by user
- "Analyses" section in sidebar below folder tree for browsing saved analyses
- Custom query field for user-specified analysis questions
- Unified analysis approach for mixed template types (no grouping by template)

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 05-cross-meeting-analysis*
*Context gathered: 2026-03-31*
