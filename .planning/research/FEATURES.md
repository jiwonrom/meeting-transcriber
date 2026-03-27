# Feature Landscape

**Domain:** macOS meeting transcription desktop app (v2.0 advanced features)
**Researched:** 2026-03-27
**Confidence:** MEDIUM (based on training data through mid-2025; no web search available)

## Context

Scribe v1.0+v1.5 already covers: real-time transcription, overlay captions, multi-language support, AI summarization/translation/keywords, file-based diarization (pyannote), folder management, Markdown/TXT export. The v2.0 scope adds power-user features that move Scribe from "transcription tool" to "meeting intelligence platform."

Competitive reference points: Otter.ai, Fireflies.ai, Granola, Krisp, Fathom, tl;dv (cloud); Slipbox, Mangonote, MacWhisper (macOS-native local-first).

---

## Table Stakes

Features users expect. Missing = product feels incomplete for a v2.0 release.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| SRT/VTT subtitle export | Every transcription tool supports subtitle formats. Users need these for video editing and accessibility. Standard format, no ambiguity. | Low | Pure formatting of existing `segments[].start/end/text`. Both formats are trivially spec'd. 1-2 days including tests. |
| System audio capture | Users need to transcribe what others say in Zoom/Teams/Meet. Mic-only misses half the conversation. Every serious competitor captures both sides. | High | BlackHole driver integration. Major UX challenge: guiding users through Audio MIDI Setup. Engineering is medium; UX design is the hard part. |
| BYOK (multi-provider) | Power users expect to use their own API keys. Standard in local-first AI tools (MacWhisper, Slipbox all support this). | Medium | Extend existing `AIProvider` ABC. Add OpenAI-compatible + Anthropic providers. Keychain storage per provider. |
| Speaker labels in transcript | "Who said what" is fundamental for meeting notes. v1.5 has file-based diarization; v2.0 should extend to real-time or near-real-time. | Very High | See detailed analysis below. Recommend incremental approach, not true streaming. |

## Differentiators

Features that set Scribe apart from cloud competitors and other local-first tools.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Auto meeting detection | "Never forget to record." Detect when Zoom/Teams launches and prompt to start. Granola does this. Most tools require manual start. | Medium | Monitor `NSWorkspace.runningApplications` for meeting app bundle IDs. Notification: "Meeting detected. Start recording?" |
| Meeting templates | Structured output per meeting type (standup: blockers/progress; 1:1: action items/feedback; interview: Q&A). Goes beyond generic summary. | Medium | Template = Jinja2 template + Gemini prompt template. Built-in defaults + user-customizable. |
| Cross-meeting analysis | "What did we discuss about Project X across 5 standups?" No local-first tool does this. | High | Multi-transcript Gemini prompt. Requires chunking strategy for large corpora. Needs accumulated transcripts to be useful. |
| Obsidian vault export | Direct vault integration with YAML frontmatter, tags, daily note links. Killer feature for local-first PKM audience. | Low | Write `.md` files to vault directory. No library needed. |
| Notion page export | Push structured notes to Notion workspace. | Medium | notion-client SDK. Requires user OAuth/integration token setup. |

## Anti-Features

Features to explicitly NOT build in v2.0.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Cloud sync / multi-device | Core principle is local-first. Cloud sync changes the product identity entirely. | Users can sync via iCloud Drive, Obsidian Sync, or their own solution. |
| Video recording | Scope creep. Every meeting platform already records video. | Stay audio-only. Support video audio extraction (v1.5, PyAV). |
| Live collaboration | Single-user desktop app. Real-time collab needs networking, conflict resolution. Different product. | Export to Notion/Obsidian for sharing. |
| Calendar integration | OAuth with Google/Microsoft/Apple Calendar, timezone handling, recurring event logic. High complexity, moderate value. | Auto meeting detection + AI-generated titles from content achieves 80% of the value. |
| Meeting bot injection | Otter/Fireflies inject bots into Zoom. Requires bot infrastructure, users dislike bots. | System audio capture (BlackHole) is the local-first alternative. |
| Custom model fine-tuning | ML expertise, training data, infrastructure. Diminishing returns. | Use pre-trained models. whisper.cpp `--initial-prompt` for custom vocabulary. |
| Real-time translation overlay | Latency compounds: transcription + translation = 4-6s delay. Poor UX. | Post-meeting translation (already in v1.5). |

---

## Feature Dependencies

```
SRT/VTT Export ---- (independent, ship anytime)
Obsidian Export --- (independent, ship anytime)
BYOK ------------- (independent, extends existing AIProvider ABC)

System Audio Capture
  +-- Auto Meeting Detection (full value requires system audio working)

Speaker Diarization (file-based, v1.5 exists)
  +-- Real-time Diarization (extends existing pipeline)
  +-- Meeting Templates (benefit from speaker labels for role attribution)

Meeting Templates
  +-- Cross-meeting Analysis (uses templates for structured output)

transcript schema v2.0 (add speaker field to segments)
  +-- SRT/VTT with speaker labels
  +-- Obsidian/Notion export with speaker attribution
  +-- Meeting templates with per-speaker sections
```

## Dependency-Driven Build Order

```
Phase 1 (Independent, low-risk):
  SRT/VTT Export, BYOK, Obsidian Export, transcript schema v2.0

Phase 2 (Core infrastructure):
  System Audio Capture (BlackHole)

Phase 3 (Builds on Phase 2):
  Auto Meeting Detection

Phase 4 (AI-heavy, benefits from speaker data):
  Meeting Templates, Real-time Speaker Diarization

Phase 5 (Requires accumulated corpus):
  Cross-meeting Analysis
  Notion Export (deferred due to OAuth complexity)
```

---

## MVP Recommendation for v2.0

**Must ship (core v2.0):**
1. SRT/VTT export -- Low effort, completes export story
2. BYOK multi-provider -- Medium effort, power user retention
3. System audio capture -- High effort but highest user value
4. Obsidian export -- Low effort, massive value for target audience
5. Meeting templates -- Medium effort, makes output professional

**Should ship (stretch):**
6. Real-time speaker diarization (incremental approach)
7. Auto meeting detection

**Defer to v2.5+:**
- Cross-meeting analysis -- needs transcript corpus to be useful
- Notion export -- OAuth complexity, lower priority than Obsidian for local-first users
- ANE-optimized diarization -- optimization, not feature. Ship after baseline works.

## Sources

- Competitive landscape: Otter.ai, Fireflies.ai, Granola, Krisp, Fathom, Slipbox, Mangonote, MacWhisper
- PRD.md section 4.3 (v2.0 scope)
- PROJECT.md active requirements
- Existing codebase: exporter.py, provider_base.py, transcript_store.py, audio_capture.py
