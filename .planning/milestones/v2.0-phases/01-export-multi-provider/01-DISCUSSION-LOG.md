# Phase 1: Export & Multi-Provider - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-27
**Phase:** 01-export-multi-provider
**Areas discussed:** Export format, Obsidian integration, Provider UX, Fallback behavior
**Mode:** Auto (recommended defaults selected)

---

## Export Format

| Option | Description | Selected |
|--------|-------------|----------|
| Millisecond precision | 00:00:00,000 (SRT standard) | ✓ |
| Second precision | 00:00:00 (simpler but non-standard) | |

**User's choice:** [auto] Millisecond precision (standard)

| Option | Description | Selected |
|--------|-------------|----------|
| Prefix with speaker name | "Speaker 1: text" when labels available | ✓ |
| No speaker labels | Plain text only in subtitles | |

**User's choice:** [auto] Prefix with speaker name

---

## Obsidian Integration

| Option | Description | Selected |
|--------|-------------|----------|
| Vault path in Preferences | User sets path, exports write Markdown with frontmatter | ✓ |
| Auto-detect vault | Scan for .obsidian directory | |

**User's choice:** [auto] Vault path in Preferences

---

## Provider UX

| Option | Description | Selected |
|--------|-------------|----------|
| Global default + per-task override | One default, can override per AI task type | ✓ |
| Per-task only | No global default, select each time | |
| Global only | One provider for all tasks | |

**User's choice:** [auto] Global default + per-task override

---

## Fallback Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Silent retry + status bar | Try next provider, show message | ✓ |
| Ask user on failure | Show dialog asking which provider to try | |
| Fail immediately | Show error, no retry | |

**User's choice:** [auto] Silent retry + status bar

---

## Claude's Discretion

- Export button placement in transcript viewer
- Exact SRT/VTT formatting beyond timestamps
- Provider config UI layout within Preferences

## Deferred Ideas

None
