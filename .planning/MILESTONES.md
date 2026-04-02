# Milestones

## v2.0 Meeting Intelligence Platform (Shipped: 2026-04-02)

**Phases completed:** 8 phases, 19 plans, 34 tasks

**Key accomplishments:**

- SRT/VTT subtitle export with ms-precision timestamps and Obsidian Markdown export with YAML frontmatter, plus config defaults for export paths and AI provider
- OpenAI + Anthropic providers with ProviderManager fallback chain and FallbackProvider adapter for AITaskWorker
- Export buttons (SRT/VTT/Obsidian) in TranscriptViewer, multi-provider Preferences with Keychain storage, and FallbackProvider-based AI execution with automatic per-method fallback
- BlackHole detection + CoreAudio Aggregate Device CRUD via pyobjc with lazy imports and 14 mocked unit tests
- SystemAudioToggle (44x24 QPainter), DualLevelMeter (stacked bars), and BlackHoleSetupWizard (5-step QDialog with audio output routing) -- 14 passing tests
- DiarizationWorker QThread with pyannote pipeline, temporal speaker alignment, schema v2.0 with backward-compatible speaker fields, and on-demand model download with progress reporting
- Full speaker diarization UI pipeline: auto-diarization after recording, manual identify button, inline speaker labels, click-to-rename speaker panel, and HuggingFace token settings.
- CoreML conversion attempt for pyannote segmentation model with cached .mlpackage and transparent CPU fallback
- TemplateManager with 5 built-in YAML templates and template-aware AI provider pipeline with per-vendor JSON mode
- MeetingDetectorWorker QThread polling NSWorkspace for 6 conferencing apps with global cooldown, per-session snooze, and Chrome audio heuristic
- Template QComboBox with structured HTML summary rendering, tray meeting notifications with snooze, and full detector-to-UI signal wiring via app.py
- AIProvider analyze_cross_meeting() with vendor-specific JSON modes, MetadataIndex for index.json CRUD, AnalysisStore for timestamped result persistence, and CrossMeetingAnalysisWorker QThread
- Multi-transcript selection mode with checkboxes, folder-level propagation, sticky action bar, and Analyses browsing section
- Cross-meeting analysis end-to-end wiring: sidebar selection triggers AI analysis, results display as styled HTML, saved as JSON, exportable as Markdown, with MetadataIndex hooks on transcript CRUD
- Formal verification of Phase 2 system audio capture with 65/65 tests passing, 4/4 SYSAUD requirements SATISFIED, and documentation gap closed
- Fixed MetadataIndex to read v2.0 languages list with v1.0 fallback, and wired index updates through update_transcript_speakers
- Replaced QListWidget sidebar with SidebarWidget in MainWindow QSplitter layout, removing 90+ lines of legacy sidebar code

---
