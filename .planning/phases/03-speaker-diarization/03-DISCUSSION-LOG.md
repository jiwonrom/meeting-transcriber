# Phase 3: Speaker Diarization - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-27
**Phase:** 03-speaker-diarization
**Areas discussed:** Diarization trigger & flow, Speaker label display, Schema migration strategy, Model & performance

---

## Diarization Trigger & Flow

| Option | Description | Selected |
|--------|-------------|----------|
| Manual button | "Identify Speakers" button in TranscriptViewer. User decides when to run. | |
| Auto-run after recording | Diarization starts automatically when recording stops. | ✓ |
| Both — toggle in settings | Default to manual, with auto-run option in Preferences. | |

**User's choice:** Auto-run after recording
**Notes:** None

---

| Option | Description | Selected |
|--------|-------------|----------|
| Status bar + progress indicator | Status bar shows "Identifying speakers..." with spinner. Non-blocking. | ✓ |
| Inline in TranscriptViewer | Banner/overlay within transcript view showing progress. | |
| You decide | Claude picks best progress UX. | |

**User's choice:** Status bar + progress indicator
**Notes:** None

---

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — button available for all transcripts | "Identify Speakers" on any transcript with saved audio file. | ✓ |
| Only new recordings | Diarization only for recordings after feature ships. | |
| Yes, but only if audio file exists | Button shows, grayed out if audio deleted. | |

**User's choice:** Yes — button available for all transcripts
**Notes:** None

---

## Speaker Label Display

| Option | Description | Selected |
|--------|-------------|----------|
| Color-coded badges | Colored badge/tag before text. Colors auto-assigned. | |
| Colored left border | Left border color per speaker. Name on first occurrence. | |
| Inline prefix | Simple text prefix "Speaker 1:" before each segment. | ✓ |

**User's choice:** Inline prefix
**Notes:** None

---

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — click to rename | Click speaker label to edit. Applies to all segments. | ✓ |
| No — auto labels only | Auto-generated labels only, no editing. | |
| You decide | Claude picks. | |

**User's choice:** Yes — click to rename
**Notes:** User also noted: "없는 버전도 출력 가능하게" — transcripts without diarization should display normally without speaker labels

---

## Schema Migration Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Lazy migration on load | Missing speaker fields treated as empty. Write v2.0 only when diarization runs. | ✓ |
| Batch migration on app update | Scan all transcripts and upgrade on first launch after update. | |
| You decide | Claude picks safest approach. | |

**User's choice:** Lazy migration on load
**Notes:** None

---

## Model & Performance

| Option | Description | Selected |
|--------|-------------|----------|
| On-demand download | Download on first diarization attempt. Progress dialog. Cache in models/. | ✓ |
| During onboarding | Add step to onboarding wizard. | |
| You decide | Claude picks. | |

**User's choice:** On-demand download
**Notes:** None

---

| Option | Description | Selected |
|--------|-------------|----------|
| Keychain storage like API keys | Prompt for HuggingFace token. Store in Keychain. | ✓ |
| Bundle model to avoid token | Pre-download and bundle model (~75MB). | |
| You decide | Claude picks. | |

**User's choice:** Keychain storage like API keys
**Notes:** None

---

| Option | Description | Selected |
|--------|-------------|----------|
| Non-blocking with notification | Browse/edit transcript while diarization runs. Labels populate when done. | ✓ |
| Modal progress dialog | Block interaction until complete. | |
| You decide | Claude picks. | |

**User's choice:** Non-blocking with notification
**Notes:** None

---

| Option | Description | Selected |
|--------|-------------|----------|
| CPU/MPS only for v2.0 | PyTorch with MPS on Apple Silicon. ANE deferred to v3.0. | |
| Include ANE optimization | CoreML conversion for ANE acceleration. | ✓ |

**User's choice:** Include ANE optimization
**Notes:** User pulled ANE-01 from v3.0 into Phase 3

## Claude's Discretion

- pyannote pipeline configuration and parameters
- Speaker count estimation approach
- CoreML conversion toolchain and caching
- "Identify Speakers" button placement
- Diarization worker thread architecture
- Speaker color palette for future use

## Deferred Ideas

- Real-time speaker diarization during live recording (RT-DIAR-01) — remains v3.0
- Speaker color coding in TranscriptViewer — future enhancement
