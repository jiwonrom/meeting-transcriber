# Phase 5: Cross-Meeting Analysis - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-03-31
**Phase:** 05-cross-meeting-analysis
**Areas discussed:** Multi-transcript selection UX, Cross-meeting insight format, Metadata index design, Analysis trigger & results display

---

## Multi-Transcript Selection UX

### How should users select multiple transcripts?

| Option | Description | Selected |
|--------|-------------|----------|
| Sidebar checkboxes | Toggle into selection mode via button, checkboxes appear next to transcripts | ✓ |
| Dedicated analysis picker | Separate dialog/panel with filters (date range, folder, template type) | |
| Shift/Cmd-click in sidebar | Standard OS multi-select, less discoverable | |

**User's choice:** Sidebar checkboxes
**Notes:** Familiar pattern like mail apps, reuses existing tree.

### Cross-folder selection?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, cross-folder | Users can check transcripts from any folder | ✓ |
| Same folder only | Selection limited to one folder at a time | |

**User's choice:** Yes, cross-folder

### Selection mode entry?

| Option | Description | Selected |
|--------|-------------|----------|
| Sidebar toolbar button | Add 'Select' button next to '+ New Folder' | ✓ |
| Right-click context menu | Less discoverable | |
| Always show checkboxes | Adds visual noise | |

**User's choice:** Sidebar toolbar button

### Transcript count limits?

| Option | Description | Selected |
|--------|-------------|----------|
| Min 2, no max | Gemini 1M context is practical cap | ✓ |
| Min 2, max 10 | Hard cap for focus | |
| Min 2, max 5 | Tighter limit | |

**User's choice:** Min 2, no max

### Folder-level select all?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, folder checkbox | Checking folder selects all transcripts | ✓ |
| No, individual only | Only transcript checkboxes | |

**User's choice:** Yes, folder checkbox

---

## Cross-Meeting Insight Format

### Output sections?

| Option | Description | Selected |
|--------|-------------|----------|
| Recurring topics | Topics across multiple meetings with frequency | ✓ |
| Action item tracker | Aggregated action items, unresolved flags, completion tracking | ✓ |
| Decision evolution | How decisions changed over meetings | |
| Speaker participation | Who spoke across meetings, how often | |

**User's choice:** Recurring topics + Action item tracker

### Structured JSON vs free-form?

| Option | Description | Selected |
|--------|-------------|----------|
| Structured JSON | Consistent with Phase 4, enables richer UI rendering | ✓ |
| Free-form Markdown | Natural language, simpler prompting | |

**User's choice:** Structured JSON

### Mixed template handling?

| Option | Description | Selected |
|--------|-------------|----------|
| Unified analysis | AI adapts to mix, one combined output | ✓ |
| Template-grouped | Separate analysis per type + combined summary | |
| You decide | Claude picks during implementation | |

**User's choice:** Unified analysis

### Timeline view?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, timeline in output | Topic progression ordered by meeting date | ✓ |
| No, just aggregated lists | Simpler, no temporal ordering | |
| You decide | Claude picks | |

**User's choice:** Yes, timeline in output

### Multi-language handling?

| Option | Description | Selected |
|--------|-------------|----------|
| Majority language | Use most common language among selected transcripts | ✓ |
| User's app language | Use language from app preferences | |
| Always ask | Prompt user each time | |

**User's choice:** Majority language

### Export?

| Option | Description | Selected |
|--------|-------------|----------|
| Markdown export | Reuse existing exporter pattern | ✓ |
| No export for now | View-only in app | |
| You decide | Claude picks | |

**User's choice:** Markdown export

### Custom query?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, optional text field | Default analysis + optional specific questions | ✓ |
| No, fixed analysis only | Standard sections only | |

**User's choice:** Yes, optional text field

---

## Metadata Index Design

### Index storage?

| Option | Description | Selected |
|--------|-------------|----------|
| Single JSON index file | index.json in workspace root, simple and portable | ✓ |
| SQLite database | Full-text search, SQL queries, adds dependency | |
| In-memory only | Load at startup, no persistence | |

**User's choice:** Single JSON index file

### Index update timing?

| Option | Description | Selected |
|--------|-------------|----------|
| On every transcript change | Hook into create/save/delete operations | ✓ |
| On app startup only | Full rebuild at launch | |
| On-demand rebuild | User-triggered | |

**User's choice:** On every transcript change

### Index fields?

| Option | Description | Selected |
|--------|-------------|----------|
| Core fields | title, created_at, duration, languages, folder, template_type | ✓ |
| AI-generated fields | keywords, summary snippet | ✓ |
| Speaker data | List of speaker names | |
| Segment count & word count | Quick stats | ✓ |

**User's choice:** Core fields + AI-generated fields + Segment/word count

---

## Analysis Trigger & Results Display

### Results display location?

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse TranscriptViewer panel | Same right-side panel, replace content during analysis | ✓ |
| New dedicated panel/tab | Separate tab alongside TranscriptViewer | |
| Modal dialog | Pop-up dialog, blocks interaction | |

**User's choice:** Reuse TranscriptViewer panel

### Results persistence?

| Option | Description | Selected |
|--------|-------------|----------|
| Saved to workspace | JSON file in analyses/ directory, reopenable | ✓ |
| Ephemeral only | View-only in current session | |
| You decide | Claude picks | |

**User's choice:** Saved to workspace

### Progress display?

| Option | Description | Selected |
|--------|-------------|----------|
| Inline progress in viewer | Progress indicator in TranscriptViewer panel | ✓ |
| Status bar only | Use existing status bar | |

**User's choice:** Inline progress in viewer

### Saved analyses browsable?

| Option | Description | Selected |
|--------|-------------|----------|
| Analyses section in sidebar | Dedicated section below folder tree | ✓ |
| No sidebar entry | Re-select transcripts to access | |

**User's choice:** Analyses section in sidebar

### Analyze button placement?

| Option | Description | Selected |
|--------|-------------|----------|
| Sidebar bottom bar | Sticky button at bottom during selection mode | ✓ |
| Viewer panel button | Button in TranscriptViewer area | |

**User's choice:** Sidebar bottom bar

---

## Claude's Discretion

- AI prompt engineering for cross-meeting analysis
- JSON schema for analysis result files
- HTML rendering of structured sections in TranscriptViewer
- Index rebuild/migration for corrupted files
- Selection mode keyboard shortcuts
- Analysis section collapse/expand behavior

## Deferred Ideas

None -- discussion stayed within phase scope
