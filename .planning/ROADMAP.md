# Roadmap: Scribe v2.0

## Overview

Scribe v2.0 transforms the app from a personal mic transcriber into a full meeting intelligence platform. The roadmap starts with zero-dependency quick wins (export formats, multi-provider AI), then tackles the highest-value audio feature (system audio capture), adds speaker identification, builds meeting-aware intelligence on top, and culminates with cross-meeting analysis. Each phase delivers a complete, independently verifiable capability.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Export & Multi-Provider** - SRT/VTT/Obsidian export and BYOK multi-provider AI support
- [ ] **Phase 2: System Audio Capture** - BlackHole integration for capturing both sides of calls
- [ ] **Phase 3: Speaker Diarization** - Post-recording speaker identification with labeled transcripts
- [ ] **Phase 4: Meeting Intelligence** - Meeting templates, adaptive summaries, and auto meeting detection
- [ ] **Phase 5: Cross-Meeting Analysis** - Multi-transcript selection, combined insights, and searchable index
- [ ] **Phase 6: System Audio Completion & Verification** - Complete SYSAUD-03 and formally verify Phase 2
- [ ] **Phase 7: Cross-Meeting Analysis Wiring Fixes** - Show SidebarWidget, fix MetadataIndex field mismatch
- [ ] **Phase 8: Per-Task AI Provider Override** - Wire get_provider_for_task() into _run_ai_tasks

## Phase Details

### Phase 1: Export & Multi-Provider
**Goal**: Users can export transcripts in professional subtitle formats and to Obsidian, and can use their own AI provider keys
**Depends on**: Nothing (builds on v1.5 foundation)
**Requirements**: EXP-01, EXP-02, EXP-03, EXP-04, BYOK-01, BYOK-02, BYOK-03, BYOK-04
**Success Criteria** (what must be TRUE):
  1. User can export any transcript as an SRT file with correct timestamp formatting and open it in a video player
  2. User can export any transcript as a VTT file with correct timestamp formatting
  3. User can export a transcript to a configured Obsidian vault directory as properly formatted Markdown with frontmatter
  4. User can configure a default export directory in Preferences that persists across app restarts
  5. User can add OpenAI or Anthropic API keys in Preferences and select which provider handles summarization, proofreading, and translation -- with automatic fallback if the primary provider fails
**Plans:** 3 plans

Plans:
- [x] 01-01-PLAN.md — Export core: SRT/VTT/Obsidian export functions + config defaults
- [x] 01-02-PLAN.md — Provider core: OpenAI/Anthropic providers + ProviderManager with fallback
- [x] 01-03-PLAN.md — UI wiring: settings dialog extensions + export buttons + ProviderManager integration

**UI hint**: yes

### Phase 2: System Audio Capture
**Goal**: Users can capture system audio (the other side of calls) alongside their microphone
**Depends on**: Phase 1 (export formats ready for richer transcripts)
**Requirements**: SYSAUD-01, SYSAUD-02, SYSAUD-03, SYSAUD-04
**Success Criteria** (what must be TRUE):
  1. App detects whether BlackHole virtual audio driver is installed and clearly communicates the status to the user
  2. User who does not have BlackHole can follow the in-app setup wizard to install it and create an Aggregate Device without leaving the app
  3. User can select system audio as an input source from the recording controls and see it transcribed
  4. User can capture microphone and system audio simultaneously, producing a single merged transcript
**Plans:** 3/3 plans executed

Plans:
- [x] 02-01-PLAN.md — Core backend: BlackHole detection, Aggregate Device CRUD, constants/exceptions/config
- [x] 02-02-PLAN.md — UI widgets: SystemAudioToggle, DualLevelMeter, BlackHoleSetupWizard
- [x] 02-03-PLAN.md — Integration: MainWindow wiring, settings dialog, app.py signals, end-to-end verification

**UI hint**: yes

### Phase 3: Speaker Diarization
**Goal**: Transcripts identify who said what, with speaker labels visible in the UI and exports
**Depends on**: Phase 2 (dual-channel audio improves diarization accuracy)
**Requirements**: DIAR-01, DIAR-02, DIAR-03, DIAR-04
**Success Criteria** (what must be TRUE):
  1. After a recording completes, user can trigger diarization and see speaker labels assigned to transcript segments
  2. Transcript viewer displays speaker labels (inline text prefix) next to each segment
  3. Existing v1.x transcripts load without error (schema v2.0 migration is backward-compatible)
  4. SRT/VTT exports include speaker labels prefixed to each subtitle entry when diarization data is available
**Plans:** 3 plans

Plans:
- [x] 03-01-PLAN.md — Core backend: DiarizationWorker, temporal alignment, model download manager, schema v2.0, constants/exceptions
- [x] 03-02-PLAN.md — UI integration: audio preservation, auto-diarization, TranscriptViewer speaker labels, Identify Speakers button, speaker rename, Settings HF token
- [x] 03-03-PLAN.md — CoreML/ANE optimization: attempt CoreML conversion of pyannote model with CPU fallback gate

**UI hint**: yes

### Phase 4: Meeting Intelligence
**Goal**: Users get structured, context-aware summaries tailored to their meeting type, with automatic recording prompts
**Depends on**: Phase 3 (speaker labels enable role-based templates), Phase 2 (system audio enables meeting detection value)
**Requirements**: TPL-01, TPL-02, TPL-03, DET-01, DET-02
**Success Criteria** (what must be TRUE):
  1. User can select a meeting template (Team Meeting, 1:1, Lecture, Interview) before or after recording
  2. AI summary output format adapts to the selected template (e.g., action items for meetings, Q&A pairs for lectures)
  3. User can create a custom template with their own prompt instructions and use it for future recordings
  4. When Zoom, Teams, Meet, or FaceTime is active, the app surfaces a notification offering to start recording
**Plans:** 3 plans

Plans:
- [x] 04-01-PLAN.md — Template system backend: TemplateManager, YAML templates, AI provider extension, exporter compatibility
- [x] 04-02-PLAN.md — Meeting detection backend: MeetingDetectorWorker with NSWorkspace polling, cooldown, snooze
- [x] 04-03-PLAN.md — UI integration: template dropdown, structured summary display, Re-run AI, detection notifications, settings

**UI hint**: yes

### Phase 5: Cross-Meeting Analysis
**Goal**: Users can analyze patterns and action items across multiple meetings
**Depends on**: Phase 4 (templates provide structured data that improves cross-meeting insights)
**Requirements**: CMA-01, CMA-02, CMA-03
**Success Criteria** (what must be TRUE):
  1. User can select two or more transcripts from the sidebar and initiate a combined analysis
  2. AI generates a cross-meeting summary that highlights recurring topics, unresolved action items, and decision evolution
  3. App maintains a lightweight searchable index of transcript metadata so cross-meeting queries respond without loading full transcript files
**Plans:** 3 plans

Plans:
- [x] 05-01-PLAN.md — Backend foundation: MetadataIndex, AnalysisStore, AIProvider extension, CrossMeetingAnalysisWorker
- [x] 05-02-PLAN.md — Sidebar selection mode: checkboxes, folder propagation, action bar, Analyses section
- [x] 05-03-PLAN.md — Integration wiring: MainWindow analysis display, app.py signals, index hooks, Markdown export

**UI hint**: yes

### Phase 6: System Audio Completion & Verification
**Goal**: Complete system audio source selection and formally verify all Phase 2 requirements
**Depends on**: Phase 2 (completes unfinished Phase 2 work)
**Requirements**: SYSAUD-01, SYSAUD-02, SYSAUD-03, SYSAUD-04
**Gap Closure:** Closes gaps from v2.0 audit — 1 unsatisfied + 3 verification gaps
**Success Criteria** (what must be TRUE):
  1. User can select system audio (via BlackHole) as an input source from recording controls
  2. Phase 2 VERIFICATION.md exists and all 4 SYSAUD requirements pass formal verification
  3. ROADMAP status for Phase 2 is accurate
**Plans:** 1 plan

Plans:
- [x] 06-01-PLAN.md — Formal verification of Phase 2 + documentation updates

**UI hint**: yes

### Phase 7: Cross-Meeting Analysis Wiring Fixes
**Goal**: Make cross-meeting analysis features accessible at runtime by fixing integration wiring
**Depends on**: Phase 5 (fixes broken wiring from Phase 5 implementation)
**Requirements**: CMA-01, CMA-03
**Gap Closure:** Closes gaps from v2.0 audit — 2 partial requirements, 2 broken flows, 2 integration issues
**Success Criteria** (what must be TRUE):
  1. SidebarWidget is visible in the MainWindow layout and user can enter selection mode
  2. MetadataIndex correctly reads `languages` (plural) from transcript metadata
  3. `update_transcript_speakers` updates MetadataIndex after diarization
  4. "Cross-Meeting Selection Mode" and "Metadata-Indexed Language Search" E2E flows complete
**Plans:** 2 plans

Plans:
- [x] 07-01-PLAN.md — MetadataIndex language field fix + speaker update index wiring
- [ ] 07-02-PLAN.md — SidebarWidget layout integration into MainWindow

**UI hint**: yes

### Phase 8: Per-Task AI Provider Override
**Goal**: Wire per-task AI provider selection so user's task-level overrides are applied
**Depends on**: Phase 1 (fixes unused wiring from Phase 1 implementation)
**Requirements**: BYOK-03
**Gap Closure:** Closes gaps from v2.0 audit — 1 partial requirement
**Success Criteria** (what must be TRUE):
  1. `_run_ai_tasks` uses `get_provider_for_task()` instead of `get_provider_chain()` for each AI call
  2. User's per-task provider overrides from `ai.task_overrides` settings are applied at runtime

**UI hint**: no

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Export & Multi-Provider | 3/3 | Complete | - |
| 2. System Audio Capture | 3/3 | Complete | - |
| 3. Speaker Diarization | 3/3 | Complete | - |
| 4. Meeting Intelligence | 3/3 | Complete | - |
| 5. Cross-Meeting Analysis | 3/3 | Complete | - |
| 6. System Audio Completion & Verification | 1/1 | Complete | 2026-04-02 |
| 7. Cross-Meeting Analysis Wiring Fixes | 0/2 | Pending | |
| 8. Per-Task AI Provider Override | 0/? | Pending | |
