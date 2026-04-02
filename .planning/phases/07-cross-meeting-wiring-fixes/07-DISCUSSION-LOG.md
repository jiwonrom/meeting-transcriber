# Phase 7: Cross-Meeting Analysis Wiring Fixes - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-02
**Phase:** 07-cross-meeting-wiring-fixes
**Areas discussed:** SidebarWidget layout integration, MetadataIndex field fix, Speaker update index wiring
**Mode:** auto (all decisions auto-selected with recommended defaults)

---

## SidebarWidget Layout Integration

| Option | Description | Selected |
|--------|-------------|----------|
| Replace QListWidget with SidebarWidget | Drop in existing SidebarWidget which already has all functionality plus selection mode | * |
| Keep both QListWidget and SidebarWidget | Run side by side with tab or toggle | |

**User's choice:** [auto] Replace QListWidget with SidebarWidget (recommended default)
**Notes:** SidebarWidget already has all recording list functionality. Keeping both would be redundant.

---

## MetadataIndex Field Fix

| Option | Description | Selected |
|--------|-------------|----------|
| Read `languages` (plural) directly | Fix to match transcript schema, add v1.0 fallback | * |
| Read `language` (singular) with wrapper | Normalize at read time | |

**User's choice:** [auto] Read `languages` (plural) directly from metadata (recommended default)
**Notes:** The singular key was a bug. Schema stores `languages` as a list since Phase 3.

---

## Speaker Update Index Wiring

| Option | Description | Selected |
|--------|-------------|----------|
| Optional index parameter (None default) | Backward compatible, matches save_transcript pattern | * |
| Always require index parameter | Breaking change to existing callers | |

**User's choice:** [auto] Optional index parameter with default None (recommended default)
**Notes:** Consistent with save_transcript and delete_recording patterns.

## Claude's Discretion

- Exact signal wiring order in app.py
- Whether to add a sidebar property to MainWindow
- Test structure for new wiring

## Deferred Ideas

None -- all items within phase scope
