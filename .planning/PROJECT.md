# Scribe

## What This Is

macOS 네이티브 데스크탑 앱. 실시간 음성 전사를 오버레이 캡션으로 표시하고, 녹음/파일 임포트를 통해 다국어 transcript를 생성하며, AI 기반 요약·번역·키워드 추출을 제공한다. 모든 데이터는 로컬 우선으로 처리된다. PyQt6 + whisper.cpp + Gemini API 기반.

## Core Value

실시간 캡션 — Closed Caption처럼 화면 위에 자막을 표시하여 회의/강의를 실시간으로 전사한다.

## Requirements

### Validated

- ✓ Real-time transcription via whisper.cpp subprocess — v1.0
- ✓ Spotlight-style floating overlay with drag support — v1.0 + v1.5
- ✓ Multi-language support (EN, KO, ZH, JA + auto-detect) — v1.0
- ✓ Folder-based workspace management with CRUD — v1.0
- ✓ macOS tray icon with recording controls — v1.0
- ✓ Global keyboard shortcuts (Cmd+Shift+R) — v1.0
- ✓ First-run onboarding wizard (language, model, mic) — v1.0
- ✓ AI summarization, proofreading, keywords, title via Gemini — v1.5
- ✓ Design token system (dark/light themes) — v1.0
- ✓ API key storage in macOS Keychain — v1.0
- ✓ Transcript export (Markdown, TXT) — v1.0
- ✓ Recording deletion from UI — v1.5
- ✓ App icon and "Scribe" branding — v1.5
- ✓ Runtime overlay settings application — v1.5
- ✓ Structured logging framework — v1.5
- ✓ Settings cache for performance — v1.5
- ✓ SRT/VTT subtitle export — Validated in Phase 1: Export & Multi-Provider
- ✓ Obsidian Markdown export — Validated in Phase 1: Export & Multi-Provider
- ✓ BYOK multi-provider AI (OpenAI, Anthropic, Gemini) — Validated in Phase 1: Export & Multi-Provider
- ✓ System audio capture (BlackHole integration) — Validated in Phase 2: System Audio Capture
- ✓ Post-recording speaker diarization with pyannote.audio — Validated in Phase 3: Speaker Diarization
- ✓ Speaker labels in transcript viewer (inline prefix) — Validated in Phase 3: Speaker Diarization
- ✓ Transcript schema v2.0 with speaker data — Validated in Phase 3: Speaker Diarization
- ✓ CoreML/ANE optimization attempt with CPU fallback — Validated in Phase 3: Speaker Diarization
- ✓ Meeting templates (General, Team Meeting, 1:1, Lecture, Interview) — Validated in Phase 4: Meeting Intelligence
- ✓ Template-adaptive AI summaries with structured JSON sections — Validated in Phase 4: Meeting Intelligence
- ✓ Custom YAML template support — Validated in Phase 4: Meeting Intelligence
- ✓ Auto meeting detection (Zoom, Teams, Meet, FaceTime) — Validated in Phase 4: Meeting Intelligence
- ✓ Recording prompt via macOS notification with snooze — Validated in Phase 4: Meeting Intelligence
- ✓ Cross-meeting analysis (multi-transcript selection, AI insights, metadata index) — Validated in Phase 5: Cross-Meeting Analysis

### Active

- [ ] Notion export integration

### Out of Scope

- Cloud sync / multi-device — local-first architecture is core principle
- Mobile app — macOS only
- Video recording — audio-only focus
- Real-time collaboration — single-user desktop app
- Custom AI model training — use pre-trained models only

## Context

- **Codebase**: ~30 Python files across 5 modules (ui, core, ai, storage, utils)
- **Architecture**: Strict unidirectional deps (ui→core, ui→ai, ai→storage), Signal/Slot for reverse communication
- **Current state**: Phase 5 complete with 363 passing tests, all v2.0 phases done
- **Key tech debt**: MainWindow god object (1000+ lines), no file import UI
- **PRD**: Detailed v2.0 scope in PRD.md §4.3

## Constraints

- **Tech stack**: PyQt6 + whisper.cpp + Gemini — no framework changes
- **Threading**: All I/O off main thread (QThread or subprocess)
- **Security**: API keys in macOS Keychain only, no plaintext storage
- **Compatibility**: macOS only, Apple Silicon optimized
- **Performance**: Real-time caption ≤ 2s latency after speech

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| whisper.cpp via subprocess CLI | GIL avoidance, latest builds, CoreML/Metal accel | ✓ Good |
| PyQt6 over Electron | Single Python stack, native overlay support | ✓ Good |
| Gemini Flash as primary AI | Low cost, fast response, covers all AI features | ✓ Good |
| Rebrand to "Scribe" from "Meeting Transcriber" | Shorter, catchier, broader scope | — Pending |
| BlackHole for system audio | Only viable macOS virtual audio option | — Pending |
| pyannote for speaker diarization | Best open-source accuracy | ✓ Good — Phase 3 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-02 after Phase 7 completion — Cross-meeting analysis wiring fixed (CMA-01, CMA-03 unblocked)*
