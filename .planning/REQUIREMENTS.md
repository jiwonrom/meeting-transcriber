# Requirements: Scribe v2.0

**Defined:** 2026-03-27
**Core Value:** 실시간 캡션 — 화면 위 자막으로 회의/강의를 실시간 전사

## v2.0 Requirements

### Export

- [x] **EXP-01**: User can export transcript as SRT subtitle file with proper timestamp formatting
- [x] **EXP-02**: User can export transcript as VTT subtitle file with proper timestamp formatting
- [x] **EXP-03**: User can export transcript as Obsidian-compatible Markdown to a configured vault directory
- [ ] **EXP-04**: User can configure default export directory in Preferences

### Multi-Provider (BYOK)

- [ ] **BYOK-01**: User can add their own OpenAI API key in Preferences
- [ ] **BYOK-02**: User can add their own Anthropic API key in Preferences
- [x] **BYOK-03**: User can select which AI provider to use for each task (summarize, proofread, translate)
- [x] **BYOK-04**: App falls back to next provider if primary fails

### System Audio

- [ ] **SYSAUD-01**: App detects whether BlackHole virtual audio driver is installed
- [ ] **SYSAUD-02**: App provides guided setup wizard for BlackHole installation and Aggregate Device creation
- [ ] **SYSAUD-03**: User can select system audio (via BlackHole) as input source alongside microphone
- [ ] **SYSAUD-04**: User can capture both microphone and system audio simultaneously (dual-channel)

### Speaker Diarization

- [ ] **DIAR-01**: Post-recording diarization assigns speaker labels to transcript segments
- [ ] **DIAR-02**: Transcript viewer displays speaker labels (color-coded per speaker)
- [ ] **DIAR-03**: Transcript schema v2.0 supports optional speaker field per segment
- [ ] **DIAR-04**: SRT/VTT exports include speaker labels when available

### Meeting Templates

- [ ] **TPL-01**: User can select a meeting template before or after recording (Team Meeting, 1:1, Lecture, Interview)
- [ ] **TPL-02**: AI summary output adapts to selected template format (action items for meetings, Q&A for lectures)
- [ ] **TPL-03**: User can create custom templates with prompt instructions

### Meeting Detection

- [ ] **DET-01**: App detects when common conferencing apps are active (Zoom, Teams, Meet, FaceTime)
- [ ] **DET-02**: App offers to start recording when a meeting is detected (notification prompt)

### Cross-Meeting Analysis

- [ ] **CMA-01**: User can select multiple transcripts for combined analysis
- [ ] **CMA-02**: AI generates cross-meeting summary highlighting recurring topics and action items
- [ ] **CMA-03**: Lightweight transcript index maintains searchable metadata without loading full files

## v3.0 Requirements (Deferred)

- **RT-DIAR-01**: Real-time speaker diarization during live recording (ANE optimized)
- **NOTION-01**: Export transcripts to Notion database via API
- **ANE-01**: Apple Neural Engine optimization for diarization model
- **REFACTOR-01**: Extract RecordingSession orchestrator from MainWindow

## Out of Scope

| Feature | Reason |
|---------|--------|
| Cloud sync | Local-first architecture is core principle |
| Mobile app | macOS only — platform focus |
| Video recording | Audio-only scope |
| Calendar integration | Adds complexity without core value |
| Conferencing bot (auto-join meetings) | Security/privacy concerns, out of local-first ethos |
| Real-time collaboration | Single-user desktop app |
| Custom model training | Use pre-trained models only |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| EXP-01 | Phase 1 | Complete |
| EXP-02 | Phase 1 | Complete |
| EXP-03 | Phase 1 | Complete |
| EXP-04 | Phase 1 | Pending |
| BYOK-01 | Phase 1 | Pending |
| BYOK-02 | Phase 1 | Pending |
| BYOK-03 | Phase 1 | Complete |
| BYOK-04 | Phase 1 | Complete |
| SYSAUD-01 | Phase 2 | Pending |
| SYSAUD-02 | Phase 2 | Pending |
| SYSAUD-03 | Phase 2 | Pending |
| SYSAUD-04 | Phase 2 | Pending |
| DIAR-01 | Phase 3 | Pending |
| DIAR-02 | Phase 3 | Pending |
| DIAR-03 | Phase 3 | Pending |
| DIAR-04 | Phase 3 | Pending |
| TPL-01 | Phase 4 | Pending |
| TPL-02 | Phase 4 | Pending |
| TPL-03 | Phase 4 | Pending |
| DET-01 | Phase 4 | Pending |
| DET-02 | Phase 4 | Pending |
| CMA-01 | Phase 5 | Pending |
| CMA-02 | Phase 5 | Pending |
| CMA-03 | Phase 5 | Pending |

---
*Defined: 2026-03-27 from PRD §4.3 + research findings*
