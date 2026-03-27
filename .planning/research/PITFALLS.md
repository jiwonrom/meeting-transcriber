# Domain Pitfalls

**Domain:** macOS meeting transcription app -- system audio capture, real-time diarization, meeting templates, cross-meeting analysis, export integrations
**Researched:** 2026-03-27
**Overall Confidence:** MEDIUM (training-data-based; web search unavailable for live verification)

---

## Critical Pitfalls

Mistakes that cause rewrites, data loss, or fundamental architecture problems.

### Pitfall 1: BlackHole Requires User-Managed Multi-Output Device

**What goes wrong:** Developers assume BlackHole can capture system audio directly via `sounddevice`. In reality, BlackHole is a virtual audio driver that creates a loopback device. To capture system audio while still hearing it through speakers, the user must manually create a "Multi-Output Device" in macOS Audio MIDI Setup that routes audio to both BlackHole and their speakers. If you only route to BlackHole, the user hears nothing. If you skip Multi-Output entirely, you capture nothing.

**Why it happens:** BlackHole's README makes it sound simple ("install and select as output"), but the Multi-Output Device step is mandatory for a usable experience, and there is no public programmatic API to create Multi-Output Devices on macOS.

**Consequences:**
- Users install BlackHole but cannot figure out how to configure it -- support burden becomes enormous
- App appears broken ("I can't hear my meeting anymore") when user selects BlackHole as system output without Multi-Output
- No way to fully automate the setup -- `coreaudiod` does not expose Multi-Output creation via any public API
- Competing apps (Slipbox, Krisp) solve this by shipping their own Audio HAL driver, which is a multi-month native development effort

**Prevention:**
1. Build an interactive setup wizard that walks users through Multi-Output Device creation step-by-step with annotated screenshots
2. Add a detection check: query `sounddevice.query_devices()` for a device named "BlackHole" and a Multi-Output device containing "BlackHole" -- if BlackHole exists but Multi-Output does not, show the wizard
3. Consider ScreenCaptureKit (macOS 13+) as a future alternative -- it can capture app-level audio without BlackHole, but requires entitlements and has Python binding challenges (pyobjc-framework-ScreenCaptureKit)
4. Never make system audio the default -- keep microphone as default, system audio as opt-in
5. Provide a "test capture" button that plays a brief tone and verifies the capture pipeline actually records something

**Detection (warning signs):**
- Users report "no audio captured" or "can't hear speakers anymore"
- `list_audio_devices()` returns BlackHole but no Multi-Output Device
- Test environment works (developer has Multi-Output set up) but user environments fail

**Phase:** System audio capture phase -- must be addressed in the first sprint of that feature.

---

### Pitfall 2: pyannote Real-Time Diarization Is Not Actually Real-Time on Isolated Chunks

**What goes wrong:** Developers integrate pyannote-audio expecting frame-by-frame speaker labels on 2-second chunks. pyannote's diarization pipeline (`pyannote.audio.Pipeline`) requires the complete audio file (or a substantial window) to perform speaker embedding + clustering. Running it on 2-second isolated chunks produces garbage -- each chunk independently yields "SPEAKER_00" because there is no cross-chunk speaker identity persistence.

**Why it happens:** pyannote's API accepts any audio input, so it does not error on small chunks. It silently produces useless single-speaker results. The documentation focuses on file-level diarization. The current codebase architecture (see `ChunkTranscriberThread` in `main_window.py:341-390`) processes each 2-second chunk independently with zero shared state -- this model is fundamentally incompatible with diarization.

**Consequences:**
- Speaker labels change randomly between chunks (SPEAKER_00 in chunk 1 is not the same person as SPEAKER_00 in chunk 2)
- Architecture must be fundamentally different from the current "transcribe each 2s chunk independently" model
- If you try to paper over this with post-hoc alignment, you need the full recording anyway, making "real-time" labels impossible with this approach
- Concurrent pyannote + whisper.cpp inference competes for CPU/ANE/GPU, degrading transcription latency

**Prevention:**
1. Separate real-time transcription (whisper on 2s chunks, as current) from diarization (pyannote on accumulated audio)
2. Architecture: maintain a growing audio buffer in `RecordingController`. Run diarization periodically (every 30-60 seconds) on the accumulated buffer, then retroactively assign speaker labels to existing transcript segments
3. Display real-time captions without speaker labels first, then update with "[Speaker A]:" prefixes as diarization catches up (eventual consistency model)
4. Alternative: whisper.cpp has experimental `--tinydiarize` flag for basic 2-speaker detection at near-zero additional cost. Evaluate this as a lightweight v2.0 option before committing to full pyannote integration
5. For the "ANE optimized" goal from PRD: pyannote models are PyTorch-based. Converting to CoreML/ANE requires `coremltools` export, which has known issues with attention layers in speaker embedding models. Budget significant research time or defer ANE optimization

**Detection (warning signs):**
- All chunks labeled as single speaker
- Speaker IDs do not persist across chunks
- Diarization accuracy is far worse than pyannote benchmarks (DER > 30%)

**Phase:** Real-time diarization phase. Architecture decision must happen before any code is written. This pitfall requires the chunk-based transcription pipeline to be redesigned into a buffer-based model.

---

### Pitfall 3: Mixing System Audio + Microphone Creates Echo/Duplicate Transcription

**What goes wrong:** When capturing both system audio (via BlackHole) and microphone input simultaneously for meetings where you want to transcribe both remote participants and yourself, the system audio contains the remote speakers' voices, and the microphone captures your voice PLUS room echo of the remote speakers. Without acoustic echo cancellation (AEC), every remote utterance is transcribed twice -- once from system audio, once from the microphone bleed.

**Why it happens:** Physical microphones pick up speaker output. In a typical video call, the remote participant's audio plays through speakers, bounces around the room, and enters the microphone. Professional conferencing apps (Zoom, Teams) have built-in AEC. This app does not. The current `AudioCaptureWorker` (see `audio_capture.py`) opens a single `sd.InputStream` and has no concept of multi-source mixing or echo cancellation.

**Consequences:**
- Duplicate transcription of every remote speaker utterance
- Speaker diarization becomes meaningless (same utterance appears as two different speakers from two sources)
- Transcript quality drops dramatically in non-headphone setups
- Users blame the app's transcription quality when it is actually an echo problem

**Prevention:**
1. Detect if user is using speakers (not headphones) and show a warning recommending headphones
2. For v2.0 MVP: recommend headphones as requirement for system audio + mic combo. AEC is a complex DSP problem
3. If both streams are active, consider keeping them as SEPARATE channels with source labeling (`source: "microphone"` vs `source: "system"`) so diarization can distinguish local vs remote speakers without AEC
4. Alternative approach: capture only system audio (for remote participants), only microphone (for local user), and label segments by source channel rather than running full diarization across mixed audio
5. Long-term: investigate WebRTC's AEC module (webrtcvad/py-webrtcvad), but this is a significant integration effort

**Detection (warning signs):**
- Same text appears twice in transcript with slightly different timestamps
- Diarization shows 2x the expected number of speakers
- Users report "everything is repeated"

**Phase:** System audio capture phase. Must design the audio routing architecture before implementation.

---

### Pitfall 4: transcript.json Schema Breaks When Adding Speaker/Source Fields

**What goes wrong:** The current `transcript.json` schema has segments with `{start, end, text, language, confidence}`. Adding `speaker` field (for diarization) and `source` field (for system-audio vs microphone) seems trivial but breaks backward compatibility. Existing v1.0/v1.5 transcripts have no speaker data. CLAUDE.md explicitly states "transcript.json schema arbitrary changes forbidden."

**Why it happens:** Schema migration is overlooked because "just adding a field" seems backward-compatible. But code that reads transcripts now needs null-checking, UI display logic changes, export formats need updating, and cross-meeting analysis needs to handle mixed schemas. The current `_parse_whisper_output` in `transcriber.py:181-228` directly constructs segment dicts without a schema validator.

**Consequences:**
- Existing transcripts from v1.0/v1.5 crash when loaded with v2.0 code expecting speaker fields
- AI summarization prompts that reference speaker data fail on old transcripts
- Export to SRT/VTT needs speaker info but old transcripts have none
- Cross-meeting analysis produces inconsistent results when mixing v1.x and v2.0 transcripts

**Prevention:**
1. Bump schema version to "2.0" in transcript.json
2. Write a migration function that runs on load: if `version < "2.0"`, add default values (`speaker: null`, `source: "microphone"`)
3. All segment field access must use `.get()` with defaults, never direct key access
4. Create a `TranscriptSegment` dataclass (like the existing `TranscriptionResult`) to enforce typed access
5. Test with a corpus of existing v1.0/v1.5 transcripts -- create fixtures from real recordings

**Detection (warning signs):**
- KeyError exceptions when loading old transcripts
- AI tasks producing empty/error results on old recordings
- Export functions crashing on transcripts without speaker data

**Phase:** Must be addressed at the very start of v2.0 before any diarization or system audio work begins. It is a prerequisite for all v2.0 features.

---

### Pitfall 5: MainWindow God Object Makes v2.0 Features Exponentially Harder

**What goes wrong:** The existing MainWindow (876 lines, 5+ embedded classes including `ChunkTranscriberThread`, `TranscriptionWorkerThread`, `RecordButton`, `RecordingListItem`, `TranscriptViewer`) already violates single-responsibility. Adding system audio controls, diarization display, meeting templates, and cross-meeting analysis UI will push it past 2000+ lines. Every new feature interacts with recording state, UI state, and worker threads through the same monolithic class.

**Why it happens:** Incremental feature addition without refactoring. Each feature "just adds one more signal handler" to MainWindow. The existing recording state machine (already documented as fragile in CONCERNS.md with zero test coverage) gets more complex: recording-mic-only / recording-system-only / recording-both / diarizing / template-active.

**Consequences:**
- Recording state machine becomes untestable (CONCERNS.md notes zero test coverage for recording state transitions)
- System audio + mic toggle interactions create combinatorial state explosion
- Bug fixes in one feature break others (the race condition fixed in v1.0 is symptomatic)
- Silent error swallowing (`except Exception: pass` in `ChunkTranscriberThread.run`) hides new bugs
- Per-chunk `FileTranscriber` instantiation (CONCERNS.md) becomes even worse with dual audio streams

**Prevention:**
1. Refactor MainWindow BEFORE adding v2.0 features. Extract:
   - `RecordingController` -- owns recording state machine, audio workers, chunk management
   - `DiarizationController` -- owns pyannote pipeline, speaker assignment, buffer management
   - `TranscriptViewer` widget -- separate file under `ui/`
   - `RecordingListPanel` widget -- separate file under `ui/`
   - Worker threads -- separate files under `core/`
2. Replace scattered boolean state (`_is_recording`, worker nullability checks) with an explicit FSM using enum states + transition table
3. Fix the per-chunk `FileTranscriber` instantiation: create one at recording start, reuse across chunks
4. Replace `except Exception: pass` with proper error propagation
5. Budget 1-2 sprints for this refactor before any v2.0 feature work

**Detection (warning signs):**
- main_window.py exceeds 1200 lines
- New features require modifying 5+ methods in MainWindow
- Race condition bugs increase after adding features
- Test coverage for MainWindow remains at 0% for state transitions

**Phase:** Must be the FIRST phase of v2.0. All other features depend on a clean component architecture.

---

## Moderate Pitfalls

### Pitfall 6: ScreenCaptureKit Entitlement Blocks App Distribution

**What goes wrong:** If you pivot from BlackHole to ScreenCaptureKit (macOS 13+) for system audio capture, the app needs the `com.apple.security.screen-capture` entitlement. This requires a paid Apple Developer account and proper notarization. The current py2app build pipeline may not handle entitlements correctly, and unsigned/un-notarized apps cannot use ScreenCaptureKit at all.

**Prevention:**
- If pursuing ScreenCaptureKit, verify Apple Developer enrollment and notarization pipeline first
- Test the full py2app -> codesign -> notarize -> DMG pipeline with ScreenCaptureKit entitlement early (before writing capture code)
- Keep BlackHole as fallback for users who cannot use ScreenCaptureKit (macOS < 13) or un-notarized builds
- Note: ScreenCaptureKit Python bindings via pyobjc-framework-ScreenCaptureKit need evaluation for stability

**Phase:** System audio capture phase -- evaluate during planning, decide before implementation.

---

### Pitfall 7: pyannote Model Size Blows Up App Bundle

**What goes wrong:** pyannote-audio pulls in PyTorch (~2GB), plus the diarization model itself (~100MB). The app bundle goes from manageable to 3-4GB. First-launch download becomes painful. py2app bundling of PyTorch is notoriously problematic (missing .dylib files, arm64 vs x86_64 architecture mismatches on Apple Silicon).

**Prevention:**
1. Do NOT bundle PyTorch in the app. Export pyannote models to ONNX format and use ONNX Runtime instead (~100MB total vs 2GB+ PyTorch)
2. If ONNX export is not feasible, make `torch` a runtime dependency installed separately, not bundled in .app
3. Download diarization models on-demand (matching the existing whisper model download pattern in `model_manager.py`), not at install time
4. Test py2app bundling with PyTorch as the FIRST step of diarization work -- it is the highest-risk packaging step
5. Consider whether whisper.cpp `--tinydiarize` (if mature enough) eliminates the need for pyannote entirely

**Detection (warning signs):**
- DMG size exceeds 500MB
- py2app build fails with missing torch .dylib
- App crashes on launch with `ImportError` for torch._C

**Phase:** Real-time diarization phase -- model packaging strategy must be decided before implementation.

---

### Pitfall 8: Per-Chunk FileTranscriber Instantiation Worsens with Dual Audio Streams

**What goes wrong:** The current code creates a new `FileTranscriber` for every 2-second chunk (`ChunkTranscriberThread` at `main_window.py:370-374` calls `FileTranscriber()` each time, which resolves whisper-cli path and validates model file). With system audio capture, there are potentially TWO audio streams producing chunks. That doubles the subprocess spawning rate. With diarization running concurrently, the machine runs whisper-cli + pyannote simultaneously, overwhelming even Apple Silicon.

**Prevention:**
1. Fix the per-chunk instantiation issue BEFORE adding system audio (reuse a single FileTranscriber instance, pass it to chunk workers)
2. Implement a chunk queue with backpressure -- if transcription falls behind, queue chunks instead of silently dropping them (current behavior at `main_window.py:674`)
3. For dual-stream: mix mic + system audio into a single stream before transcription, do NOT run two parallel transcription pipelines
4. Profile CPU/memory with concurrent whisper + pyannote on target hardware (M1 8GB RAM is the floor)

**Detection (warning signs):**
- CPU usage exceeds 100% during recording
- Chunks are silently dropped (gaps in transcript timestamps)
- Transcription latency exceeds the 3-second max from PRD

**Phase:** Should be fixed in the MainWindow refactor phase, before system audio or diarization.

---

### Pitfall 9: Meeting Templates Conflate Configuration with Content

**What goes wrong:** "Meeting templates" (Team Meeting, 1:1, Lecture, Interview) start as simple preset configurations but creep into content territory -- template-specific AI prompts, expected output sections, custom export formats. The template becomes a mini-schema that touches every layer: UI (template picker), AI (template-specific prompts), storage (template metadata in transcript.json), and export (template-specific formatting).

**Prevention:**
1. Keep templates as CONFIGURATION ONLY in v2.0: a template is a JSON file containing `{name, default_language, ai_prompts: {summary_prompt, action_items_prompt}, export_format, expected_duration}`
2. Templates modify AI task behavior (different prompts via the existing `AIProvider` abstraction) and export behavior, but do NOT add structural fields to transcript.json
3. Store template association as metadata only: `transcript.json.metadata.template: "team-meeting"`
4. Ship 4 built-in templates as JSON files under `~/.meeting_transcriber/templates/`, allow user-created templates later
5. Do NOT build a template editor UI in v2.0 -- just template selection at recording start

**Detection (warning signs):**
- Template code appears in 3+ modules simultaneously
- transcript.json gets template-specific structural fields beyond metadata
- AI prompts are hardcoded per template instead of loaded from template config files

**Phase:** Meeting templates phase. Define the template schema before any implementation.

---

### Pitfall 10: Cross-Meeting Analysis Without Indexing Is O(n) on Every Query

**What goes wrong:** "Cross-meeting analysis" (multi-transcript insights) requires reading every transcript.json in the workspace. The current sidebar already has this problem (CONCERNS.md: "Full sidebar refresh reads every transcript.json"). At 100+ meetings, a cross-meeting query takes seconds of disk I/O. At 500+, it is unusable. The current `_refresh_recording_list` at `main_window.py:530-554` does a full rebuild on every save.

**Prevention:**
1. Build a lightweight index: `~/.meeting_transcriber/index.db` (SQLite) containing transcript metadata, keywords, speaker names, and text search index
2. Index is populated incrementally: when a transcript is saved, update the index entry
3. Cross-meeting queries hit the index, not individual JSON files
4. Use SQLite FTS5 for full-text search across transcripts
5. This index ALSO solves the sidebar performance problem from CONCERNS.md -- two birds, one stone

**Detection (warning signs):**
- Cross-meeting analysis takes >2 seconds for 50 meetings
- UI freezes during analysis (blocking I/O on main thread -- violates CLAUDE.md MUST NOT)
- Memory usage spikes when loading all transcripts into memory

**Phase:** Cross-meeting analysis phase. But the SQLite index should be introduced earlier (during MainWindow refactor) to also fix the existing sidebar performance issue.

---

### Pitfall 11: Aggregate Device Audio Clock Drift

**What goes wrong:** When using a CoreAudio Aggregate Device (mic + BlackHole), the two audio sources use different clock sources. Over long meetings (1+ hours), the streams drift out of sync. Mic audio and system audio timestamps diverge by seconds, making diarization alignment impossible and producing garbled mixed transcripts.

**Prevention:**
1. If creating an Aggregate Device programmatically or in the wizard, set the clock source to the physical microphone (not BlackHole)
2. Enable drift correction for the BlackHole sub-device in the Aggregate Device configuration
3. Test with 2+ hour recording sessions to verify sync stability
4. Monitor timestamp drift during recording and warn the user if drift exceeds 100ms

**Detection (warning signs):**
- Transcription text becomes garbled or repeated after 30+ minutes
- System audio timestamps drift from mic timestamps
- Mixed stream sounds like it has echo/phasing

**Phase:** System audio capture phase. Must test during implementation.

---

### Pitfall 12: SRT/VTT Export with Speaker Labels Has Subtle Spec Requirements

**What goes wrong:** SRT and VTT subtitle formats have strict formatting requirements. Speaker labels are not part of the official SRT spec -- they are a convention. WebVTT has official `<v Speaker A>` voice tags, but SRT does not. Getting this wrong means subtitle players do not render them correctly, or worse, show raw markup as visible text.

**Prevention:**
1. WebVTT: Use the official `<v>` voice tag for speaker identification
2. SRT: Prefix speaker name on the text line only: `Speaker A: Hello everyone` (no markup)
3. SRT uses comma for milliseconds (`00:00:02,500`), VTT uses period (`00:00:02.500`) -- do not mix them
4. Handle segments without speaker info gracefully (omit the prefix, do not show "Unknown:")
5. Test exported files in VLC, QuickTime Player, and at least one web-based player

**Detection (warning signs):**
- Subtitle players show raw tags as text
- Speaker labels appear as garbled markup
- Timing overlaps cause display glitches in players

**Phase:** SRT/VTT export phase.

---

### Pitfall 13: Obsidian/Notion Export -- Notion Becomes a Permanent Maintenance Burden

**What goes wrong:** Export integrations to Obsidian and Notion have vastly different requirements. Obsidian is just Markdown files in a vault directory -- trivial. Notion requires the Notion API, OAuth or integration tokens, database selection, page creation, block formatting, and handling rate limits. Building both in parallel means the Notion integration becomes a permanent maintenance burden as Notion's API evolves.

**Prevention:**
1. Ship Obsidian FIRST -- it is literally "write Markdown to a user-selected directory." Can be done in a day using the existing `exporter.py` pattern
2. Notion SECOND, scoped minimally: export creates a new page in a selected database. No sync, no updating existing pages, no bidirectional sync
3. Use the existing `storage/exporter.py` module pattern -- add `ObsidianExporter` and `NotionExporter` classes
4. For Notion: store the integration token in Keychain (same pattern as Gemini key). Handle rate limits with exponential backoff
5. Do NOT build bidirectional sync. Export-only, one-way

**Detection (warning signs):**
- Notion API errors appear in logs frequently after Notion API updates
- Users request "sync" features (scope creep signal)
- Export code grows beyond 200 lines per exporter

**Phase:** Export integrations phase. Ship Obsidian first, Notion as a separate sub-phase.

---

## Minor Pitfalls

### Pitfall 14: sounddevice Device Index Instability

**What goes wrong:** The current `AudioCaptureWorker.__init__` accepts `device: int | str | None`. If the user saves a device index in settings, that index may point to a different device after a reboot or when BlackHole is installed/removed, because macOS reassigns device indices dynamically.

**Prevention:**
- Store device by name (string), not index. Resolve name to index at recording start via `list_audio_devices()`
- Fall back to system default if saved device name is not found
- Re-query devices when the user opens recording settings or before each recording start

**Phase:** System audio capture phase (when adding BlackHole device selection).

---

### Pitfall 15: Auto Meeting Detection Privacy and False Positive Risk

**What goes wrong:** "Auto meeting detection" (monitoring for Zoom/Teams/Meet processes) triggers recording when the user opens a conferencing app for non-meeting purposes (checking settings, joining a social call they do not want recorded, or just having the app open in background). False positives erode trust and raise serious privacy concerns.

**Prevention:**
- Require user confirmation before auto-starting recording (macOS notification with "Record this meeting?" action)
- Never auto-record without explicit consent -- privacy implications are severe
- Monitor for active audio streams from the process, not just process existence
- Make auto-detection opt-in with default OFF
- Minimum audio activity duration before triggering (e.g., 5 seconds of sustained speech)

**Phase:** Auto meeting detection phase.

---

### Pitfall 16: BYOK Multi-Provider Key Validation

**What goes wrong:** Users paste invalid API keys, keys for the wrong API tier, or keys with insufficient permissions. The current code stores keys in Keychain but has no validation beyond storage. With BYOK supporting multiple providers (Gemini, OpenAI, Anthropic), each provider has different key formats, validation endpoints, and error responses.

**Prevention:**
- Validate keys on save: make a minimal API call (e.g., list models) to verify the key works
- Show clear error messages per provider ("This key does not have access to Gemini Flash")
- Store provider type alongside the key in Keychain
- Map provider-specific error messages to user-friendly strings (never show raw API errors in UI)
- Handle rate limit errors separately from authentication errors

**Phase:** BYOK phase.

---

### Pitfall 17: Cross-Meeting Analysis Context Window Overflow

**What goes wrong:** User selects 20 one-hour meetings for cross-meeting analysis. Combined transcript text exceeds Gemini's context window. API call fails or truncates silently, producing incomplete/hallucinated analysis.

**Prevention:**
1. Calculate approximate token count before API call
2. If over limit: use AI-generated summaries (from v1.5 feature) as input instead of raw transcripts
3. If summaries unavailable: chunk transcripts, summarize each first, then analyze summaries (map-reduce pattern)
4. Show user feedback: "Analyzing N meetings (estimated time: X)"
5. Set reasonable defaults in UI (suggest max 10-15 meetings per analysis batch)

**Phase:** Cross-meeting analysis phase.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation | Priority |
|-------------|---------------|------------|----------|
| MainWindow refactor | Regression in recording flow (zero test coverage) | Write recording integration tests BEFORE refactoring | P0 |
| Schema migration | Old transcripts break on load | Version bump + migration function + fixtures test | P0 |
| System audio (BlackHole) | User setup complexity, Multi-Output creation | Interactive wizard with device detection | P0 |
| System audio + mic mixing | Echo/duplicate transcription | Separate channels, recommend headphones | P1 |
| System audio | Aggregate Device clock drift | Drift correction + long-session testing | P1 |
| Real-time diarization | pyannote not real-time on 2s chunks | Accumulated buffer + eventual consistency model | P0 |
| Real-time diarization | PyTorch bundle size (2GB+) | ONNX export or tinydiarize alternative | P1 |
| Meeting templates | Scope creep into content/structure | Templates = config JSON only | P2 |
| Cross-meeting analysis | O(n) disk reads per query | SQLite FTS5 index | P1 |
| Cross-meeting analysis | Context window overflow | Map-reduce with summaries | P2 |
| SRT/VTT export | Spec compliance (timestamp format, voice tags) | Format validation + multi-player testing | P2 |
| Obsidian/Notion export | Notion maintenance burden | Obsidian first, Notion minimal scope | P2 |
| Auto meeting detection | Privacy violations, false positives | Opt-in default OFF + confirmation required | P1 |
| BYOK | Invalid key handling, raw error leakage | Validate on save + error message mapping | P2 |

## Recommended Phase Ordering Based on Pitfall Dependencies

The pitfall analysis strongly suggests this ordering:

1. **MainWindow Refactor + Schema Migration** -- both are prerequisites for everything else. Without refactoring, adding features causes exponential complexity. Without schema migration, diarization and source data have nowhere to go. Write recording integration tests first (addresses the zero-coverage gap in CONCERNS.md).

2. **System Audio Capture** -- depends on clean `RecordingController` from step 1. High user-facing complexity (BlackHole setup wizard). Includes device index-by-name fix and Aggregate Device drift correction.

3. **Real-time Diarization** -- depends on system audio (for full-meeting diarization with separate channels) and refactored recording pipeline. Requires architecture change from chunk-independent to buffer-based model. Evaluate tinydiarize vs pyannote decision here.

4. **Meeting Templates + BYOK** -- lower risk, independent of audio pipeline changes. Templates are config-only JSON files. BYOK extends existing Keychain pattern.

5. **Cross-Meeting Analysis + SQLite Index** -- depends on schema migration and sufficient transcript volume for meaningful analysis. Index also retroactively fixes sidebar performance.

6. **Export Integrations (SRT/VTT, Obsidian, Notion)** -- lowest coupling to other features, can ship independently. Obsidian is trivial; Notion requires separate scoping.

---

## Sources

- Codebase analysis: `src/meeting_transcriber/core/audio_capture.py`, `core/transcriber.py`, `ui/main_window.py:320-420`
- Existing concerns: `.planning/codebase/CONCERNS.md` (MainWindow god object, per-chunk instantiation, silent error swallowing, zero recording test coverage)
- PRD scope: `PRD.md` sections 4.2 (v1.5), 4.3 (v2.0)
- Project constraints: `CLAUDE.md` (schema change prohibition, threading rules)
- BlackHole behavior: training data knowledge of BlackHole project and macOS CoreAudio architecture (MEDIUM confidence -- no live web verification)
- pyannote real-time limitations: training data knowledge of pyannote-audio pipeline architecture (MEDIUM confidence -- no live web verification)
- ScreenCaptureKit entitlements: training data knowledge of Apple developer documentation (MEDIUM confidence)
- SRT/VTT spec: W3C WebVTT and SRT format knowledge (HIGH confidence -- stable specs)

*Note: WebSearch was unavailable during this research. All findings are based on training data + codebase analysis. Pitfalls related to BlackHole, pyannote, and ScreenCaptureKit should be verified against current documentation before implementation begins.*

---

*Pitfalls audit: 2026-03-27*
