# Architecture Patterns

**Domain:** macOS meeting transcription desktop app -- v2.0 feature integration
**Researched:** 2026-03-27

## Recommended Architecture

v2.0 adds five major capabilities to the existing layered architecture. The core principle is: **extend the existing module boundaries, do not create new layers.** Each v2.0 feature maps cleanly onto the existing `core/`, `ai/`, `storage/`, `ui/` structure with one new cross-cutting concern (the template system) that lives in `storage/`.

### High-Level v2.0 Component Map

```
                         app.py (wiring hub)
                              |
              +---------+-----+------+-----------+
              |         |            |            |
           ui/       core/         ai/        storage/
              |         |            |            |
  +----------+    +-----+-----+    |    +-------+--------+
  |          |    |     |     |    |    |       |        |
  AudioMix  Diar  Sys   Mic   Diar  Cross  Template  ExportPlugin
  Panel     View  Audio Capt  Worker Meet   Registry  Registry
                  Capt  (v1)         Engine
                  (v2)
```

### Component Inventory -- New v2.0 Components

| Component | Module | New File(s) | Purpose |
|-----------|--------|-------------|---------|
| `SystemAudioCapture` | `core/` | `system_audio.py` | BlackHole virtual device capture |
| `AudioMixer` | `core/` | `audio_mixer.py` | Mix mic + system audio into unified stream |
| `DiarizationWorker` | `core/` | `diarization.py` | pyannote speaker diarization (QThread) |
| `DiarizationResult` | `core/` | `diarization.py` | Frozen dataclass for speaker segments |
| `CrossMeetingEngine` | `ai/` | `cross_meeting.py` | Multi-transcript analysis via Gemini |
| `TemplateRegistry` | `storage/` | `templates.py` | Meeting template CRUD and application |
| `ExportPluginRegistry` | `storage/` | `export_plugins.py` | Plugin discovery and dispatch |
| `SRTExporter` | `storage/` | `exporters/srt.py` | SRT subtitle export |
| `VTTExporter` | `storage/` | `exporters/vtt.py` | WebVTT subtitle export |
| `ObsidianExporter` | `storage/` | `exporters/obsidian.py` | Obsidian vault markdown export |
| `NotionExporter` | `storage/` | `exporters/notion.py` | Notion API export |
| `AudioSourcePanel` | `ui/` | In `settings_dialog.py` or new `audio_source.py` | UI for mic + system audio selection |
| `DiarizationView` | `ui/` | In `main_window.py` or new `diarization_view.py` | Speaker-labeled transcript display |
| `TemplateSelector` | `ui/` | `template_selector.py` | Pre-recording template picker |
| `CrossMeetingDialog` | `ui/` | `cross_meeting_dialog.py` | Multi-transcript selection and results |

## Component Boundaries

### 1. System Audio Capture (BlackHole Integration)

**Boundary:** `core/system_audio.py` -- same layer as `audio_capture.py`

BlackHole creates a virtual audio device on macOS. From sounddevice's perspective, it is just another input device. The architecture should NOT create a fundamentally different capture pipeline. Instead:

```
core/system_audio.py
  - SystemAudioCapture(QThread)
    - Uses sounddevice.InputStream targeting BlackHole device
    - Same 2-second chunk buffering as AudioCaptureWorker
    - Emits chunk_ready signal (same signature)
    - Detects BlackHole availability via device enumeration

core/audio_mixer.py
  - AudioMixer
    - Accepts N AudioCaptureWorker-like sources
    - Mixes float32 numpy arrays (simple addition + clipping)
    - Emits unified chunk_ready signal
    - Tracks which source produced which audio range (for diarization hint)
```

**Key design decision:** `SystemAudioCapture` should subclass or duck-type `AudioCaptureWorker` so the rest of the pipeline (chunk transcription, post-recording processing) does not need to know which source produced the audio. The `AudioMixer` is the new coordination point.

**Communicates with:**
- `ui/` -- receives device selection, shows BlackHole installation status
- Downstream `ChunkTranscriberThread` -- via same `chunk_ready` signal interface
- `AudioMixer` -- feeds mixed stream to transcription pipeline

**BlackHole detection strategy:**
```python
def detect_blackhole() -> AudioDeviceInfo | None:
    """Check if BlackHole virtual audio device is available."""
    for device in list_audio_devices():
        if "blackhole" in device.name.lower():
            return device
    return None
```

If BlackHole is not installed, the UI should show an install guide (link to BlackHole GitHub), not silently fail.

### 2. Real-Time Speaker Diarization

**Boundary:** `core/diarization.py`

This is the most architecturally complex v2.0 feature. pyannote.audio's `Pipeline` is a heavy model (~100MB+) that runs inference on audio segments. It MUST run off the main thread.

**Two modes required:**

| Mode | When | Implementation |
|------|------|----------------|
| Post-recording | After full transcription completes | `DiarizationWorker(QThread)` processes full audio file |
| Real-time (streaming) | During live recording | Periodic diarization on accumulated audio buffer |

**Post-recording mode (build first):**

```
core/diarization.py
  - DiarizationWorker(QThread)
    - Loads pyannote Pipeline once (cached in memory)
    - Processes full audio WAV file
    - Emits DiarizationResult (list of SpeakerSegment)
    - SpeakerSegment: {speaker_id, start, end, confidence}

  - DiarizationResult (frozen dataclass)
    - segments: list[SpeakerSegment]
    - num_speakers: int
    - Provides merge_with_transcript(transcript_segments) method
```

**Real-time mode (stretch goal):**

Real-time speaker diarization with pyannote is experimental. The approach:
1. Accumulate audio in a rolling buffer (e.g., last 30 seconds)
2. Run diarization periodically (every 5-10 seconds) on the buffer
3. Emit incremental speaker labels
4. This is CPU/GPU intensive -- must NOT block transcription pipeline

**Architecture decision: Run diarization as a parallel pipeline, not inline with transcription.** The transcription pipeline produces text; the diarization pipeline produces speaker labels. They merge AFTER both complete for a given time range.

```
Audio Source --+-> ChunkTranscriberThread -> text segments -----+
               |                                                +--> Merge -> Speaker-labeled transcript
               +-> DiarizationWorker -> speaker segments -------+
```

**Communicates with:**
- `core/audio_capture.py` / `core/audio_mixer.py` -- receives audio data
- `ui/main_window.py` -- displays speaker labels via signals
- `storage/transcript_store.py` -- speaker info saved in transcript.json

**Transcript schema evolution (v2.0):**
```json
{
  "version": "2.0",
  "metadata": {
    "speakers": {
      "SPEAKER_00": {"label": "Alice", "color": "#FF6B6B"},
      "SPEAKER_01": {"label": "Bob", "color": "#4ECDC4"}
    }
  },
  "segments": [
    {
      "start": 0.0,
      "end": 2.5,
      "text": "Good morning everyone",
      "speaker": "SPEAKER_00",
      "language": "en",
      "confidence": 0.95
    }
  ]
}
```

The schema adds `speaker` to each segment and `speakers` map to metadata. This is backward compatible: v1.x transcripts simply have no `speaker` field.

### 3. Meeting Template System

**Boundary:** `storage/templates.py`

Templates are metadata presets + AI prompt customization applied before/during/after recording. They do NOT change the audio pipeline -- they change how AI processes the transcript.

```
storage/templates.py
  - MeetingTemplate (dataclass)
    - id: str
    - name: str (e.g., "Team Standup", "1:1", "Lecture", "Interview")
    - description: str
    - ai_prompts: dict[str, str]  # Override prompts for summarize, keywords, etc.
    - export_format: str  # Preferred export format
    - expected_speakers: int | None  # Hint for diarization
    - tags: list[str]  # Auto-applied tags
    - sections: list[str]  # Expected sections (e.g., ["Updates", "Blockers", "Action Items"])

  - TemplateRegistry
    - Built-in templates (shipped with app, read-only)
    - User templates (stored in ~/.meeting_transcriber/templates/)
    - CRUD operations for user templates
    - get_template(id) -> MeetingTemplate
    - list_templates() -> list[MeetingTemplate]
```

**How templates integrate with AI:**

The `AITaskWorker` currently uses hardcoded prompts in `GeminiProvider`. Templates override these:

```python
# Current: GeminiProvider.summarize() uses fixed prompt
# v2.0: AITaskWorker receives template, passes custom prompts to provider

class AITaskWorker(QThread):
    def __init__(self, provider, text, *, template: MeetingTemplate | None = None, ...):
        self._template = template

    def run(self):
        prompt_overrides = self._template.ai_prompts if self._template else {}
        # Pass to provider methods
```

**This requires extending the AIProvider ABC** to accept optional prompt overrides:
```python
def summarize(self, text: str, *, language: str = "auto", prompt_override: str | None = None) -> str:
```

**Communicates with:**
- `ui/template_selector.py` -- template selection before recording
- `ai/tasks.py` -- prompt customization during AI processing
- `storage/transcript_store.py` -- template ID saved in transcript metadata

### 4. Cross-Meeting Analysis Engine

**Boundary:** `ai/cross_meeting.py`

This is an AI-layer component that operates on multiple transcripts. It does NOT introduce a new data store -- it reads from existing transcript.json files via `storage/`.

```
ai/cross_meeting.py
  - CrossMeetingEngine
    - __init__(provider: AIProvider)
    - analyze(transcripts: list[dict], *, query: str | None = None) -> CrossMeetingResult
    - find_recurring_topics(transcripts) -> list[Topic]
    - track_action_items(transcripts) -> list[ActionItem]
    - generate_summary(transcripts) -> str

  - CrossMeetingResult (dataclass)
    - summary: str
    - recurring_topics: list[Topic]
    - action_items: list[ActionItem]
    - participant_stats: dict[str, ParticipantStat]
    - timeline: list[TimelineEvent]

  - CrossMeetingWorker(QThread)
    - Wraps CrossMeetingEngine.analyze() for async execution
    - Emits progress and finished signals (same pattern as AITaskWorker)
```

**Key constraint:** Gemini Flash has a context window limit. For many transcripts, the engine must:
1. Summarize each transcript individually first (use cached summaries from metadata)
2. Send summaries + specific queries to the model
3. For detailed analysis, use map-reduce: analyze pairs/groups, then synthesize

**Communicates with:**
- `storage/workspace.py` -- discovers and loads multiple transcripts
- `storage/transcript_store.py` -- reads transcript data
- `ui/cross_meeting_dialog.py` -- transcript selection and result display
- `ai/provider_base.py` -- uses existing AIProvider for LLM calls

### 5. Export Plugin Architecture

**Boundary:** `storage/export_plugins.py` + `storage/exporters/` directory

The current `exporter.py` has two hardcoded formats (Markdown, TXT). v2.0 needs SRT, VTT, Obsidian, Notion. Use a plugin registry pattern.

```
storage/export_plugins.py
  - ExportPlugin (ABC)
    - name: str
    - file_extension: str
    - supports_speakers: bool
    - supports_timestamps: bool
    - export(transcript: dict, *, options: dict) -> str | bytes
    - validate_config() -> bool  # Check if plugin is usable (e.g., Notion API key exists)

  - ExportPluginRegistry
    - register(plugin: ExportPlugin) -> None
    - get(name: str) -> ExportPlugin
    - list_available() -> list[ExportPlugin]
    - export(transcript, format_name, *, options) -> Path

storage/exporters/
  __init__.py
  markdown.py    # Refactored from exporter.py
  txt.py         # Refactored from exporter.py
  srt.py         # New: SubRip subtitle format
  vtt.py         # New: WebVTT subtitle format
  obsidian.py    # New: Obsidian vault integration
  notion.py      # New: Notion API integration
```

**SRT/VTT are pure format converters** -- they take transcript segments and output timed subtitle text. No external dependencies needed.

**Obsidian export** writes markdown files with YAML frontmatter to a configured vault path. Configuration stored in settings.json:
```json
{
  "export": {
    "obsidian": {
      "vault_path": "/Users/.../ObsidianVault",
      "folder": "Meeting Notes",
      "template": "default"
    }
  }
}
```

**Notion export** requires the Notion API and an integration token (stored in Keychain). This is the only export plugin that makes network calls, so it must run off the main thread via a worker.

**Communicates with:**
- `ui/settings_dialog.py` -- export configuration
- `ui/main_window.py` -- export action triggers
- `utils/keychain.py` -- Notion API token storage

## Data Flow

### v2.0 Recording Flow (with system audio + diarization)

```
1. User selects template (optional) via TemplateSelector
2. User selects audio sources: mic, system audio, or both
3. User clicks Record

4. AudioCaptureWorker starts (mic)
   SystemAudioCapture starts (system audio, if enabled)
   AudioMixer combines streams

5. Mixer emits chunk_ready (2-second chunks)
   |
   +--> ChunkTranscriberThread (whisper-cli subprocess)
   |      emits text_ready -> OverlayWidget.append_caption()
   |
   +--> DiarizationWorker (pyannote, periodic on accumulated buffer)
          emits speaker_update -> OverlayWidget.update_speaker_label()

6. User clicks Stop

7. Full audio saved as WAV
8. TranscriptionWorkerThread processes full audio
9. DiarizationWorker processes full audio (parallel with transcription)
10. Merge: transcript segments + speaker segments -> speaker-labeled transcript

11. AITaskWorker runs with template-customized prompts:
    proofread -> summarize -> keywords -> title
    (template may add: extract_action_items, section_detection)

12. Save transcript.json (v2.0 schema with speakers)
13. Auto-export if configured (e.g., Obsidian vault)
```

### Cross-Meeting Analysis Flow

```
1. User opens CrossMeetingDialog
2. Selects multiple transcripts from sidebar
3. CrossMeetingWorker spawned (QThread)
4. Engine loads transcripts, uses cached summaries where available
5. Sends to Gemini: "Analyze these N meeting summaries..."
6. Returns CrossMeetingResult
7. UI displays: recurring topics, action item tracker, participant stats
```

### Export Flow (Plugin Architecture)

```
1. User clicks Export on a transcript
2. ExportPluginRegistry.list_available() -> shows format options
3. User selects format + options
4. For sync plugins (SRT, VTT, MD, TXT, Obsidian):
   - ExportPlugin.export() called on main thread (fast, no I/O wait)
   - File saved to chosen path
5. For async plugins (Notion):
   - ExportWorker(QThread) wraps the API call
   - Progress signal updates status bar
   - Error handling for network failures
```

## Patterns to Follow

### Pattern 1: Audio Source Abstraction

All audio sources (mic, system audio, future sources) should conform to a common interface so the mixer and downstream pipeline are source-agnostic.

**What:** Abstract base for audio sources with a common signal interface.
**When:** Any new audio input source is added.

```python
class AudioSource(QThread):
    """Base class for all audio input sources."""
    chunk_ready = pyqtSignal(bytes)  # WAV-encoded 2-second chunk
    capture_started = pyqtSignal()
    capture_stopped = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def start_capture(self) -> None: ...
    def stop_capture(self) -> None: ...
    def get_full_recording(self) -> bytes: ...
```

`AudioCaptureWorker` and `SystemAudioCapture` both conform to this interface. `AudioMixer` accepts `list[AudioSource]`.

### Pattern 2: Export Plugin Registration

**What:** Self-registering plugins via a registry singleton.
**When:** Adding any new export format.

```python
# storage/export_plugins.py
class ExportPluginRegistry:
    _plugins: dict[str, ExportPlugin] = {}

    @classmethod
    def register(cls, plugin: ExportPlugin) -> None:
        cls._plugins[plugin.name] = plugin

    @classmethod
    def get(cls, name: str) -> ExportPlugin:
        return cls._plugins[name]

# storage/exporters/srt.py
class SRTExporter(ExportPlugin):
    name = "srt"
    file_extension = ".srt"
    ...

# storage/exporters/__init__.py -- auto-register all exporters
from .srt import SRTExporter
from .vtt import VTTExporter
ExportPluginRegistry.register(SRTExporter())
ExportPluginRegistry.register(VTTExporter())
```

### Pattern 3: Parallel Pipeline Merge

**What:** Run independent processing pipelines in parallel, merge results after both complete.
**When:** Transcription + diarization both need the same audio.

```python
# In MainWindow or a dedicated orchestrator
self._transcription_done = False
self._diarization_done = False
self._transcript_result = None
self._diarization_result = None

def _on_transcription_done(self, result):
    self._transcript_result = result
    self._transcription_done = True
    self._try_merge()

def _on_diarization_done(self, result):
    self._diarization_result = result
    self._diarization_done = True
    self._try_merge()

def _try_merge(self):
    if self._transcription_done and self._diarization_done:
        merged = merge_speaker_labels(self._transcript_result, self._diarization_result)
        self._save_and_display(merged)
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Monolithic MainWindow Grows Further

**What:** Adding v2.0 logic directly into `main_window.py` (already 877 lines).
**Why bad:** MainWindow is already flagged as a god object. Adding mixer orchestration, diarization merge, template handling, and cross-meeting analysis would push it past 1500 lines.
**Instead:** Extract a `RecordingSession` orchestrator class that manages the lifecycle of a single recording (audio sources, transcription, diarization, AI tasks, saving). MainWindow creates and connects to it via signals but does not contain the logic.

```python
# core/recording_session.py (or a new orchestration module)
class RecordingSession(QObject):
    """Orchestrates a complete recording lifecycle."""
    caption_updated = pyqtSignal(str)
    transcription_done = pyqtSignal(object)
    diarization_done = pyqtSignal(object)
    session_complete = pyqtSignal(object)  # Final merged result

    def __init__(self, *, sources: list[AudioSource], template: MeetingTemplate | None = None): ...
    def start(self) -> None: ...
    def stop(self) -> None: ...
```

### Anti-Pattern 2: Diarization Blocking Transcription

**What:** Running diarization inline with the transcription pipeline.
**Why bad:** pyannote inference is 2-5x slower than whisper for the same audio. If diarization blocks transcription, real-time captions will lag badly.
**Instead:** Always run diarization as a parallel, independent pipeline. Merge after both complete. For real-time mode, accept that speaker labels may lag behind text by several seconds.

### Anti-Pattern 3: Hardcoded Export Formats

**What:** Adding SRT/VTT/Obsidian/Notion as more functions in the existing `exporter.py`.
**Why bad:** Each format has different requirements (timestamps, speaker labels, API calls, configuration). A flat file of format functions becomes unmaintainable.
**Instead:** Plugin registry with one class per format, each in its own file under `storage/exporters/`.

### Anti-Pattern 4: Modifying transcript.json Schema Without Migration

**What:** Adding `speaker` field to segments without handling v1.x files.
**Why bad:** Existing transcripts will not have speaker data. Code that assumes `speaker` exists will crash.
**Instead:** Version the schema (`"version": "2.0"`), write a migration function, and always use `.get("speaker", None)` with graceful fallback.

## Scalability Considerations

| Concern | Current (v1.x) | v2.0 Addition | At Scale |
|---------|-----------------|---------------|----------|
| Audio sources | 1 mic | Mic + system audio | AudioMixer handles N sources; memory scales linearly with source count |
| Transcription threads | Max 2 chunk threads | Same | No change needed |
| Diarization | None | 1 worker thread | pyannote uses ~500MB RAM; for long meetings (2hr+), process in windows |
| Cross-meeting analysis | N/A | Load N transcripts | Use cached summaries; for 100+ transcripts, paginate/batch LLM calls |
| Export plugins | 2 hardcoded | Plugin registry | Registry lookup is O(1); plugins loaded lazily |
| Transcript size | Small JSON files | + speaker data per segment | ~20% size increase from speaker fields; negligible |

## Suggested Build Order

Build order is driven by dependency chains. Components that other features depend on must be built first.

```
Phase 1: Foundation (no dependencies on other v2.0 features)
  1. Export plugin architecture (refactor exporter.py -> plugin registry)
  2. SRT/VTT exporters (pure format conversion, easy to test)
  3. Meeting template data model (storage + registry, no AI wiring yet)

Phase 2: Audio Pipeline (extends core/)
  4. System audio capture (BlackHole detection + SystemAudioCapture)
  5. Audio source abstraction (refactor AudioCaptureWorker to conform to base interface)
  6. AudioMixer (requires #4 and #5)

Phase 3: Diarization (depends on audio pipeline)
  7. Post-recording diarization (DiarizationWorker + pyannote integration)
  8. Transcript schema v2.0 migration (add speaker fields, version bump)
  9. Speaker-labeled UI display (DiarizationView)
  10. Real-time streaming diarization (stretch goal)

Phase 4: Intelligence (depends on templates + diarization for full value)
  11. Template-aware AI processing (extend AITaskWorker + AIProvider ABC)
  12. Cross-meeting analysis engine + worker
  13. Obsidian/Notion export plugins (network-dependent, need async workers)

Phase 5: Integration + Refactoring
  14. RecordingSession orchestrator (ties phases 2-4 together)
  15. UI integration (template selector, audio source panel, cross-meeting dialog)
  16. MainWindow refactoring (extract god-object logic into RecordingSession)
```

**Dependency rationale:**
- Export plugins have zero dependencies on other v2.0 features and deliver immediate user value. Build first.
- System audio capture is independent but must exist before the mixer can be built.
- Diarization depends on the audio pipeline producing full recordings.
- Templates are a data model that feeds into AI processing -- define the model early, wire it into AI later.
- Cross-meeting analysis needs multiple transcripts to exist (benefits from diarization data but does not require it).
- The RecordingSession orchestrator ties everything together and should be built last, once all pieces exist.
- MainWindow refactoring is safest as the final step, after new components are tested independently.

## Threading Model (v2.0 Extended)

| Thread | Implementation | Location | Responsibility |
|--------|---------------|----------|----------------|
| Main Thread | PyQt6 event loop | `app.py` | UI rendering, signal dispatch. No blocking I/O. |
| Mic Capture | QThread | `core/audio_capture.py` | sounddevice mic input |
| System Audio Capture | QThread | `core/system_audio.py` | sounddevice BlackHole input |
| Audio Mixer | Main thread QTimer callback | `core/audio_mixer.py` | Combines audio chunks (fast numpy ops), emits unified signal |
| Chunk Transcription | QThread (max 2) | `ui/main_window.py` | Real-time whisper-cli subprocess |
| Full Transcription | QThread | Recording session | Post-recording whisper-cli |
| Diarization | QThread | `core/diarization.py` | pyannote inference (heavy, ~500MB RAM) |
| AI Tasks | QThread | `ai/tasks.py` | Gemini API calls |
| Cross-Meeting | QThread | `ai/cross_meeting.py` | Multi-transcript Gemini analysis |
| Notion Export | QThread | `storage/exporters/notion.py` | Notion API upload |

**Peak concurrent threads during recording with diarization:** 5-6 (main, mic capture, system audio capture, 2x chunk transcription, real-time diarization). This is acceptable for Apple Silicon Macs.

## Sources

- Codebase analysis: direct reading of all source files in `src/meeting_transcriber/`
- PRD v2.0 scope: `PRD.md` section 4.3
- Existing architecture docs: `.planning/codebase/ARCHITECTURE.md`, `docs/architecture.md`
- BlackHole virtual audio: training data knowledge (MEDIUM confidence -- BlackHole appears as standard sounddevice input device on macOS; confirmed by existing `list_audio_devices()` pattern in `audio_capture.py`)
- pyannote.audio pipeline: training data knowledge (MEDIUM confidence -- pyannote 3.x Pipeline API for offline diarization is well-established; streaming/real-time mode is less mature and needs phase-specific research)
- SRT/VTT formats: training data knowledge (HIGH confidence -- standardized, stable text-based formats)
- Notion API: training data knowledge (MEDIUM confidence -- REST API with database/page creation; needs phase-specific research for current SDK)

---

*Architecture research: 2026-03-27*
