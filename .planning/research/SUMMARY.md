# Research Summary: Scribe v2.0

**Domain:** macOS meeting transcription desktop app -- v2.0 advanced features
**Researched:** 2026-03-27
**Overall confidence:** MEDIUM (no web search available; based on training data through mid-2025 + codebase analysis)

## Executive Summary

Scribe v2.0 adds six major capabilities to an existing PyQt6 + whisper.cpp + Gemini app: system audio capture (BlackHole), real-time speaker diarization (pyannote), meeting format templates, cross-meeting analysis, export integrations (SRT/VTT/Obsidian/Notion), and BYOK multi-provider support.

The most important finding is that **system audio capture is the highest-value single feature** -- without it, Scribe only captures the user's own microphone, missing half of every meeting conversation. However, it carries the highest UX risk: BlackHole requires user installation of a system audio driver and manual creation of an Aggregate Audio Device in macOS Audio MIDI Setup. This tension between value and setup friction should drive significant UX investment.

Real-time speaker diarization is the most technically complex feature. pyannote.audio v3.x provides excellent offline diarization but was not designed for streaming inference. The recommended approach is incremental: re-run diarization on accumulated audio every 10 seconds rather than attempting true frame-level streaming. For lightweight real-time use, whisper.cpp's built-in `--tinydiarize` flag provides speaker change detection with zero additional compute cost, though at lower accuracy. ANE optimization via ONNX+CoreML is technically feasible but requires custom model conversion work with no established community workflow.

The remaining features (SRT/VTT export, templates, Obsidian export, BYOK) are lower-risk, well-understood problems. SRT/VTT is trivial format conversion. Templates are prompt engineering + Jinja2. Obsidian export is writing Markdown files to a directory. BYOK extends the existing AIProvider ABC with OpenAI and Anthropic SDKs. These should ship first to deliver immediate v2.0 value while the harder features (system audio, diarization) are developed.

## Key Findings

**Stack:** Keep PyQt6 + whisper.cpp + Gemini core. Add BlackHole (system audio), pyannote.audio >=3.3 + torch >=2.2 (diarization), pysrt + webvtt-py (subtitles), Jinja2 (templates), openai + anthropic SDKs (BYOK), notion-client (Notion export). No Obsidian library needed -- just write files.

**Architecture:** Extend existing 4-module structure (ui/core/ai/storage). Key additions: AudioSource abstraction + AudioMixer in core/, DiarizationWorker as parallel QThread pipeline, ExportPlugin registry in storage/, ProviderManager registry in ai/. Critical refactoring: extract RecordingSession orchestrator from MainWindow god object.

**Critical pitfall:** BlackHole setup UX is the adoption risk. Real-time diarization performance contention with whisper.cpp is the technical risk. Transcript schema migration (v1.0 -> v2.0 with speaker fields) must be backward-compatible.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Quick Wins & Foundation** - SRT/VTT export, BYOK multi-provider, Obsidian export, transcript schema v2.0 migration
   - Addresses: Three independent features with zero cross-dependencies
   - Avoids: Touching the audio pipeline (highest-risk area) too early
   - Rationale: Deliver tangible v2.0 value immediately while laying schema groundwork

2. **System Audio Capture** - BlackHole detection, setup wizard, SystemAudioCapture, AudioMixer
   - Addresses: The highest-value single feature (transcribing both sides of calls)
   - Avoids: Rushing UX for complex multi-step setup flow
   - Rationale: Needs dedicated UX attention; AudioSource abstraction benefits future phases

3. **Speaker Diarization** - Post-recording diarization first, then incremental real-time
   - Addresses: "Who said what" -- transforms transcript utility
   - Avoids: Over-engineering real-time streaming; start with reliable offline mode
   - Rationale: Parallel pipeline architecture (transcription + diarization merge) must be built carefully

4. **Meeting Intelligence** - Templates + cross-meeting analysis + auto meeting detection
   - Addresses: Structured output, multi-meeting insights, convenience automation
   - Depends on: Speaker labels (phase 3) for role-based templates; system audio (phase 2) for auto-detection value
   - Rationale: AI-layer features that build on audio and diarization foundation

5. **Polish & Optimization** - ANE optimization, Notion export, MainWindow refactoring
   - Addresses: Performance optimization, secondary integrations, tech debt
   - Rationale: Optimization after baseline works; Notion deferred due to OAuth complexity

**Phase ordering rationale:**
- Independence-first: Phase 1 features have zero dependencies on other v2.0 work
- Foundation before features: System audio (Phase 2) enables auto-detection (Phase 4)
- Reliability before optimization: Post-recording diarization (Phase 3) before real-time streaming
- Corpus dependency: Cross-meeting analysis benefits from accumulated transcripts
- Tech debt last: MainWindow refactoring is safest after all new components are independently tested

**Research flags for phases:**
- Phase 2 (System Audio): Needs deeper research -- ScreenCaptureKit capabilities on macOS 15/16 may offer a zero-install alternative to BlackHole
- Phase 3 (Diarization): pyannote streaming mode may have improved since training cutoff; verify current API before implementation
- Phase 4 (Cross-meeting): Gemini context window limits need validation with real transcript sizes; may need chunking strategy
- Phase 5 (ANE): CoreML model conversion for pyannote's ECAPA-TDNN has no known community workflow; may need significant R&D

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack (core libraries) | MEDIUM-HIGH | pyannote, pysrt, webvtt-py, Jinja2 are established. Versions may be stale (training cutoff mid-2025). |
| Stack (BlackHole) | MEDIUM | De-facto standard but system-level dependency. macOS updates could affect compatibility. |
| Stack (ANE optimization) | LOW | No verified community workflow for pyannote -> ONNX -> CoreML path. Needs prototyping. |
| Features | HIGH | Based on clear competitive landscape analysis + existing codebase understanding. |
| Architecture | HIGH | Extends existing proven patterns. AudioSource abstraction and plugin registry are standard. |
| Pitfalls | MEDIUM-HIGH | Based on domain experience. BlackHole UX and diarization performance are well-known issues. |

## Gaps to Address

- **ScreenCaptureKit on macOS 15/16**: Apple may have added audio-only capture APIs that eliminate BlackHole dependency. Verify before committing to BlackHole-only approach.
- **pyannote v3.3+ streaming API**: May have improved since training cutoff. Check official docs for streaming/online mode maturity.
- **Gemini context window for cross-meeting**: Need to measure actual token counts for typical 1-hour meeting transcripts to design chunking strategy.
- **ONNX export of pyannote models**: No verified path exists. May require custom conversion scripts or alternative acceleration approach (MPS-only).
- **BlackHole on Apple Silicon Macs with macOS 16**: Compatibility testing needed after each macOS major release.
- **openai/anthropic SDK current versions**: Versions cited are from training data; verify on PyPI before adding to pyproject.toml.
