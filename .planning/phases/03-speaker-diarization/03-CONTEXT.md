# Phase 3: Speaker Diarization - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase adds post-recording speaker diarization using pyannote.audio. After a recording completes, diarization auto-runs to assign speaker labels to transcript segments. Labels are displayed in the TranscriptViewer, speakers can be renamed, and SRT/VTT exports include speaker prefixes. Transcript schema upgrades to v2.0 with optional speaker field. Includes Apple Neural Engine (CoreML) optimization for faster inference on Apple Silicon. Existing v1.0 transcripts remain fully compatible.

</domain>

<decisions>
## Implementation Decisions

### Diarization Trigger & Flow
- **D-01:** Diarization runs automatically after recording completes — no manual trigger needed for new recordings
- **D-02:** "Identify Speakers" button available on all transcripts (including pre-existing ones) for manual re-run, as long as audio file exists
- **D-03:** Progress shown in status bar with spinner/progress indicator ("Identifying speakers...")
- **D-04:** Non-blocking — user can browse/edit transcript while diarization runs in background. Speaker labels populate when done.

### Speaker Label Display
- **D-05:** Inline text prefix format (e.g., "Speaker 1: Hello everyone") — no color coding
- **D-06:** Users can rename speakers by clicking the speaker label (e.g., "Speaker 1" → "Alice"). Rename applies to all segments by that speaker and is saved in transcript.json.
- **D-07:** Transcripts without diarization data display normally without any speaker labels — graceful handling of both v1.0 and v2.0 transcripts

### Schema Migration
- **D-08:** Lazy migration on load — v1.0 transcripts treated as-is (missing speaker fields are empty). Only write v2.0 format when diarization runs or transcript is explicitly saved.
- **D-09:** No batch migration — existing files are never modified unless user triggers diarization or saves

### Model & Performance
- **D-10:** On-demand model download on first diarization attempt. Progress dialog. Cache in `~/.meeting_transcriber/models/`. Follows existing whisper model download pattern.
- **D-11:** HuggingFace token stored in macOS Keychain via existing `keychain.py` pattern (service: `meeting_transcriber.huggingface`)
- **D-12:** Apple Neural Engine (ANE) optimization via CoreML conversion of pyannote model — included in this phase (pulled forward from v3.0 ANE-01)
- **D-13:** PyTorch with MPS (Metal) as fallback when CoreML conversion is not available

### Claude's Discretion
- Exact pyannote pipeline configuration and parameters
- Speaker count estimation (auto-detect vs user-specified)
- CoreML conversion toolchain and caching strategy
- "Identify Speakers" button placement in TranscriptViewer
- Diarization worker thread architecture (QThread pattern)
- Speaker color palette assignment for future color-coding (defer actual color UI to later)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Transcript Schema & Storage
- `src/meeting_transcriber/storage/transcript_store.py` — Current v1.0 schema: `{version, metadata, segments}`. Segments have `{start, end, text, language, confidence}`. Must add optional `speaker` field.
- `src/meeting_transcriber/storage/exporter.py` — SRT/VTT exports already handle `seg.get("speaker", "")` with `include_speaker` flag. Phase 1 already prepared this.

### Audio & Transcription
- `src/meeting_transcriber/core/transcriber.py` — `TranscriptionResult` dataclass, `FileTranscriber` subprocess wrapper. Diarization needs access to the same audio file.
- `src/meeting_transcriber/core/model_manager.py` — Existing model download/management pattern to extend for pyannote models.

### UI
- `src/meeting_transcriber/ui/main_window.py` — `TranscriptViewer` class (segment display), `MainWindow` (recording flow, status bar)
- `src/meeting_transcriber/ui/onboarding.py` — `ModelDownloadThread` pattern for download progress UI

### Dependencies
- `pyproject.toml` — `[project.optional-dependencies]` already has `diarization = ["pyannote.audio>=3.1", "torch>=2.1"]`

### Keychain
- `src/meeting_transcriber/utils/keychain.py` — `store_api_key(service, key)` / `get_api_key(service)` for HuggingFace token

### Requirements
- `.planning/REQUIREMENTS.md` §Speaker Diarization — DIAR-01 through DIAR-04
- `.planning/REQUIREMENTS.md` §v3.0 — ANE-01 (now pulled into Phase 3)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `storage/exporter.py`: SRT/VTT exports already check `seg.get("speaker", "")` — Phase 1 prepared this integration point
- `core/model_manager.py`: Model download with progress — extend for pyannote model management
- `utils/keychain.py`: `store_api_key`/`get_api_key` — reuse for HuggingFace token
- `ui/onboarding.py`: `ModelDownloadThread` — QThread pattern for download with progress signals

### Established Patterns
- QThread workers for all I/O (audio capture, transcription, AI tasks)
- Signal/Slot for worker → UI communication (progress, finished, error)
- Model files cached in `~/.meeting_transcriber/models/`
- API keys stored via keyring with service prefix `meeting_transcriber.{service}`
- Optional dependencies via lazy import (Phase 2 pattern for pyobjc)

### Integration Points
- `MainWindow._on_transcription_finished()` — Where auto-diarization should be triggered after recording
- `TranscriptViewer` — Where speaker labels and rename UI should be added
- `transcript_store.create_transcript()` — Schema version bump to 2.0, add speaker field support
- `config.py` settings schema — New keys for diarization preferences

</code_context>

<specifics>
## Specific Ideas

- 기존 v1.0 transcript도 "Identify Speakers" 버튼으로 화자 구분 가능 (오디오 파일 존재 시)
- 화자 이름 변경 시 해당 화자의 모든 세그먼트에 일괄 적용
- ANE 최적화를 v3.0에서 이 페이즈로 앞당겨 포함 — CoreML 변환 포함

</specifics>

<deferred>
## Deferred Ideas

- Real-time speaker diarization during live recording (RT-DIAR-01) — remains in v3.0
- Speaker color coding in TranscriptViewer (color-coded badges/borders) — can be added as enhancement later

</deferred>

---

*Phase: 03-speaker-diarization*
*Context gathered: 2026-03-27*
