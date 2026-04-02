# Phase 4: Meeting Intelligence - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-28
**Phase:** 04-meeting-intelligence
**Areas discussed:** Template selection UX, AI prompt adaptation, Custom template authoring, Meeting detection behavior

---

## Template Selection UX

| Option | Description | Selected |
|--------|-------------|----------|
| Before recording | User selects template before hitting Record | |
| After recording | User picks template after transcription completes | |
| Both — before and changeable after | Default template set before recording, can be changed after | ✓ |

**User's choice:** Both — before and changeable after

| Option | Description | Selected |
|--------|-------------|----------|
| Dropdown next to Record button | Compact dropdown near record button | ✓ |
| Toolbar row above transcript area | Dedicated row with template chips/pills | |
| Record button long-press/menu | Default auto-applied, long-press reveals picker | |

**User's choice:** Dropdown next to Record button

| Option | Description | Selected |
|--------|-------------|----------|
| Those 4 + General | Team Meeting, 1:1, Lecture, Interview + General default | ✓ |
| Those 4 only | No General template, must always pick | |
| Those 4 + General + more | Add Brainstorm, Standup, Workshop | |

**User's choice:** Those 4 + General

| Option | Description | Selected |
|--------|-------------|----------|
| Re-run AI button with template picker | Change template and re-run, non-destructive | ✓ |
| Template dropdown in transcript viewer | Persistent dropdown, auto-triggers re-run | |
| You decide | Claude picks best UX pattern | |

**User's choice:** Re-run AI button with template picker

---

## AI Prompt Adaptation

| Option | Description | Selected |
|--------|-------------|----------|
| Template-specific sections | Each template defines its summary sections | ✓ |
| Same sections, different emphasis | All templates same output, different prompt emphasis | |
| Fully custom per template | Each template controls which tasks run and prompts | |

**User's choice:** Template-specific sections

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — attribute actions to speakers | AI attributes items to specific speakers when diarization exists | ✓ |
| No — keep speaker-agnostic | Templates ignore speaker data | |
| You decide | Claude picks per template type | |

**User's choice:** Yes — attribute actions to speakers

| Option | Description | Selected |
|--------|-------------|----------|
| System prompt per template | Each template has system prompt injected before transcript | ✓ |
| Section-based prompt fragments | Separate prompt per section, multiple API calls | |
| You decide | Claude picks best architecture | |

**User's choice:** System prompt per template

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — template replaces only summarize | Proofread/keywords/title unchanged | ✓ |
| Template controls everything | Template decides which tasks run | |
| You decide | Claude picks based on architecture | |

**User's choice:** Template replaces only summarize

| Option | Description | Selected |
|--------|-------------|----------|
| Match transcript language | Summary in same language as transcript | ✓ |
| User-configured default | Always summarize in preferred language | |
| You decide | Claude picks best default | |

**User's choice:** Match transcript language

| Option | Description | Selected |
|--------|-------------|----------|
| Structured JSON sections | Store as dict with named sections | ✓ |
| Keep as flat string | Single markdown string like today | |
| You decide | Claude picks for Phase 5 benefit | |

**User's choice:** Structured JSON sections

---

## Custom Template Authoring

| Option | Description | Selected |
|--------|-------------|----------|
| In-app editor in Settings | Preferences > Templates tab with text area | |
| Duplicate & edit built-in | Clone built-in template and modify | |
| JSON/YAML files in workspace | Files in ~/.meeting_transcriber/templates/ | ✓ |

**User's choice:** JSON/YAML files in workspace

| Option | Description | Selected |
|--------|-------------|----------|
| Name + system prompt + section names | Template name, AI prompt, section structure | ✓ |
| Name + system prompt only | Minimal, sections auto-inferred | |
| Full control including AI task toggles | Also toggle proofread/keywords/title per template | |

**User's choice:** Name + system prompt + section names

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — built-ins as editable files | Built-in templates as YAML files, serve as examples | ✓ |
| Built-ins hardcoded, examples separate | Two sources of truth | |
| No examples — docs only | Document schema, users write from scratch | |

**User's choice:** Yes — built-ins as editable files

---

## Meeting Detection Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Process monitoring | Poll for known conferencing app processes | |
| Audio activity detection | Monitor audio input for speech patterns | |
| Both — process + audio heuristic | Check apps AND audio activity | ✓ |

**User's choice:** Both — process + audio heuristic

| Option | Description | Selected |
|--------|-------------|----------|
| macOS notification | Native notification with "Start Recording" action | ✓ |
| In-app alert dialog | Modal dialog in Scribe window | |
| Tray icon badge + menu item | Tray icon changes, click reveals option | |

**User's choice:** macOS notification

| Option | Description | Selected |
|--------|-------------|----------|
| Cooldown + dismiss = snooze | Session snooze + 5min global cooldown + settings toggle | ✓ |
| Always prompt once per app launch | Single prompt per launch | |
| You decide | Claude picks best strategy | |

**User's choice:** Cooldown + dismiss = snooze

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — suggest template based on app | Zoom/Teams → Team Meeting, FaceTime → 1:1 | ✓ |
| No — use current template | Detection only triggers prompt | |
| You decide | Claude picks best UX | |

**User's choice:** Yes — suggest template based on app

| Option | Description | Selected |
|--------|-------------|----------|
| Always when tray icon is active | Runs in background even with window closed | ✓ |
| Only when main window is open | Stops when window closes | |
| User toggle in settings | On/off in Preferences, defaults ON | |

**User's choice:** Always when tray icon is active

| Option | Description | Selected |
|--------|-------------|----------|
| Every 10 seconds | Good balance of responsiveness and CPU | ✓ |
| Every 30 seconds | Very low resource usage | |
| You decide | Claude picks optimal interval | |

**User's choice:** Every 10 seconds

---

## Claude's Discretion

- YAML template schema design (field names, structure, validation rules)
- Exact system prompts for each built-in template
- Process detection implementation (NSWorkspace vs subprocess ps)
- Audio activity heuristic threshold and implementation
- macOS notification framework choice
- "Re-run AI" button placement in TranscriptViewer
- Template dropdown widget style
- Structured summary section display in TranscriptViewer

## Deferred Ideas

None — discussion stayed within phase scope.
