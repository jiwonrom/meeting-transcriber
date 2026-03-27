# Phase 3: Speaker Diarization - Research

**Researched:** 2026-03-27
**Domain:** Speaker diarization (pyannote.audio), transcript schema migration, PyQt6 UI integration
**Confidence:** MEDIUM

## Summary

Phase 3 adds post-recording speaker diarization to Scribe using pyannote.audio 4.x with the `speaker-diarization-community-1` pipeline. After recording completes, diarization auto-runs and assigns speaker labels to transcript segments. Users can also manually trigger "Identify Speakers" on existing transcripts. The transcript schema upgrades to v2.0 with an optional `speaker` field per segment. Speaker labels display as inline text prefixes in TranscriptViewer, and SRT/VTT exports (already prepared in Phase 1) include speaker labels when available.

The CoreML/ANE optimization (D-12) is high-risk. FluidInference has pre-converted CoreML models but they are consumed via a Swift SDK (FluidAudio), not Python. Converting pyannote models to CoreML from Python requires `coremltools` and involves significant challenges with dynamic graph operations. PyTorch MPS (Metal) backend also has known issues with sparse tensor operations used by pyannote, making CPU the most reliable backend for initial implementation.

**Primary recommendation:** Use pyannote.audio 4.x with `speaker-diarization-community-1` on CPU device. Implement CoreML as a stretch goal with clear fallback to CPU. Save WAV audio alongside transcripts to enable diarization on existing recordings.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: Diarization runs automatically after recording completes -- no manual trigger needed for new recordings
- D-02: "Identify Speakers" button available on all transcripts (including pre-existing ones) for manual re-run, as long as audio file exists
- D-03: Progress shown in status bar with spinner/progress indicator ("Identifying speakers...")
- D-04: Non-blocking -- user can browse/edit transcript while diarization runs in background. Speaker labels populate when done.
- D-05: Inline text prefix format (e.g., "Speaker 1: Hello everyone") -- no color coding
- D-06: Users can rename speakers by clicking the speaker label (e.g., "Speaker 1" -> "Alice"). Rename applies to all segments by that speaker and is saved in transcript.json.
- D-07: Transcripts without diarization data display normally without any speaker labels -- graceful handling of both v1.0 and v2.0 transcripts
- D-08: Lazy migration on load -- v1.0 transcripts treated as-is (missing speaker fields are empty). Only write v2.0 format when diarization runs or transcript is explicitly saved.
- D-09: No batch migration -- existing files are never modified unless user triggers diarization or saves
- D-10: On-demand model download on first diarization attempt. Progress dialog. Cache in `~/.meeting_transcriber/models/`. Follows existing whisper model download pattern.
- D-11: HuggingFace token stored in macOS Keychain via existing `keychain.py` pattern (service: `meeting_transcriber.huggingface`)
- D-12: Apple Neural Engine (ANE) optimization via CoreML conversion of pyannote model -- included in this phase (pulled forward from v3.0 ANE-01)
- D-13: PyTorch with MPS (Metal) as fallback when CoreML conversion is not available

### Claude's Discretion
- Exact pyannote pipeline configuration and parameters
- Speaker count estimation (auto-detect vs user-specified)
- CoreML conversion toolchain and caching strategy
- "Identify Speakers" button placement in TranscriptViewer
- Diarization worker thread architecture (QThread pattern)
- Speaker color palette assignment for future color-coding (defer actual color UI to later)

### Deferred Ideas (OUT OF SCOPE)
- Real-time speaker diarization during live recording (RT-DIAR-01) -- remains in v3.0
- Speaker color coding in TranscriptViewer (color-coded badges/borders) -- can be added as enhancement later
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DIAR-01 | Post-recording diarization assigns speaker labels to transcript segments | pyannote.audio 4.x community-1 pipeline; temporal alignment algorithm maps diarization output to whisper segments |
| DIAR-02 | Transcript viewer displays speaker labels (color-coded per speaker) | D-05 overrides to inline text prefix (no color coding); TranscriptViewer segment rendering with speaker prefix |
| DIAR-03 | Transcript schema v2.0 supports optional speaker field per segment | Lazy migration pattern; optional `speaker` field in segment dict; version bump to "2.0" |
| DIAR-04 | SRT/VTT exports include speaker labels when available | Already implemented in Phase 1 -- `exporter.py` checks `seg.get("speaker", "")` with `include_speaker` flag |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pyannote.audio | 4.0.4 | Speaker diarization pipeline | State-of-the-art open-source diarization; community-1 model is best-in-class |
| torch | >=2.1 (installed: 2.8.0) | PyTorch backend for pyannote | Required dependency; already installed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| coremltools | latest | CoreML model conversion | Only if CoreML optimization is pursued (D-12) |
| torchaudio | (bundled with torch) | Audio loading for pyannote | Loading WAV from memory or file for pipeline input |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| community-1 | speaker-diarization-3.1 | community-1 has 50% less speaker confusion; 3.1 is legacy |
| CPU inference | MPS (Metal) | MPS has sparse tensor bugs with pyannote -- CPU is safer |
| CoreML via Python | FluidAudio (Swift SDK) | FluidAudio is Swift-only; not usable from Python/PyQt6 |

**Installation:**
```bash
pip install "pyannote.audio>=4.0,<5.0"
# torch already installed (2.8.0)
# Optional for CoreML:
pip install coremltools
```

**Note:** pyproject.toml already has `diarization = ["pyannote.audio>=3.1", "torch>=2.1"]`. Update to `pyannote.audio>=4.0` for community-1 support.

## Architecture Patterns

### Recommended Project Structure
```
src/meeting_transcriber/
├── core/
│   ├── diarizer.py           # DiarizationWorker + pipeline wrapper
│   └── model_manager.py      # Extended for pyannote model management
├── storage/
│   └── transcript_store.py   # Schema v2.0 support
├── ui/
│   └── main_window.py        # TranscriptViewer speaker labels + rename
└── utils/
    └── constants.py           # DIARIZATION_MODEL constant
```

### Pattern 1: DiarizationWorker (QThread)
**What:** Background worker that runs pyannote pipeline on audio file
**When to use:** After transcription completes (auto) or when user clicks "Identify Speakers"
**Example:**
```python
# Source: project pattern from ai/tasks.py AITaskWorker
class DiarizationWorker(QThread):
    """화자 분리를 백그라운드에서 실행한다."""

    progress = pyqtSignal(str)
    finished = pyqtSignal(object)  # list[dict] of speaker assignments or Exception

    def __init__(
        self,
        audio_path: pathlib.Path,
        transcript_path: pathlib.Path,
        segments: list[dict[str, Any]],
        hf_token: str,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._audio_path = audio_path
        self._transcript_path = transcript_path
        self._segments = segments
        self._hf_token = hf_token

    def run(self) -> None:
        try:
            self.progress.emit("Identifying speakers...")
            # Lazy import to avoid loading torch at app startup
            from pyannote.audio import Pipeline

            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-community-1",
                token=self._hf_token,
            )
            # CPU is safest -- MPS has sparse tensor issues
            import torch
            pipeline.to(torch.device("cpu"))

            diarization = pipeline(str(self._audio_path))

            # Align diarization with transcript segments
            labeled_segments = self._align_speakers(diarization, self._segments)
            self.finished.emit(labeled_segments)
        except Exception as e:
            self.finished.emit(e)
```

### Pattern 2: Temporal Alignment (Diarization to Transcript Segments)
**What:** Maps pyannote speaker turns to whisper transcript segments by temporal overlap
**When to use:** After diarization pipeline returns results
**Example:**
```python
def _align_speakers(
    self,
    diarization: Any,  # pyannote Annotation
    segments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """화자 분리 결과를 전사 세그먼트에 매핑한다."""
    # Use exclusive_speaker_diarization for cleaner alignment
    speaker_turns = []
    for turn, speaker in diarization.exclusive_speaker_diarization:
        speaker_turns.append({
            "start": turn.start,
            "end": turn.end,
            "speaker": speaker,
        })

    # For each transcript segment, find the speaker with maximum overlap
    for seg in segments:
        seg_start = seg.get("start", 0.0)
        seg_end = seg.get("end", 0.0)
        best_speaker = ""
        best_overlap = 0.0

        for turn in speaker_turns:
            overlap_start = max(seg_start, turn["start"])
            overlap_end = min(seg_end, turn["end"])
            overlap = max(0.0, overlap_end - overlap_start)
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = turn["speaker"]

        seg["speaker"] = best_speaker or ""

    return segments
```

### Pattern 3: Schema v2.0 Lazy Migration
**What:** Backward-compatible transcript schema with optional speaker field
**When to use:** When loading/saving transcripts
**Example:**
```python
# In transcript_store.py
def create_transcript(..., speakers: dict[str, str] | None = None) -> dict[str, Any]:
    result = {
        "version": "2.0",
        "metadata": {
            ...
            "speakers": speakers or {},  # {"SPEAKER_00": "Alice", ...}
        },
        "segments": segments,  # segments may have optional "speaker" key
    }
    return result

def load_transcript(path: pathlib.Path) -> dict[str, Any]:
    """v1.0 and v2.0 transcripts load identically."""
    with open(path, encoding="utf-8") as f:
        result = json.load(f)
    # No migration needed -- missing "speaker" fields in segments
    # are simply absent; code uses seg.get("speaker", "")
    return result
```

### Pattern 4: Audio File Preservation
**What:** Save WAV audio alongside transcript for later diarization
**When to use:** During recording completion flow
**Critical finding:** Currently `_on_transcription_done` in `main_window.py` line 1007 deletes `temp_wav` before diarization can use it. The audio must be saved to the transcript folder.
```python
# In _on_transcription_done, BEFORE unlink:
audio_dest = folder / "recording.wav"
temp_wav.rename(audio_dest)  # Move instead of delete
# Then diarization worker uses audio_dest
```

### Anti-Patterns to Avoid
- **Loading pyannote at import time:** pyannote.audio + torch take ~5 seconds to import. Use lazy import inside worker thread only.
- **MPS device for pyannote:** Known sparse tensor bugs cause crashes. Use CPU.
- **Modifying v1.0 transcripts on load:** Per D-08/D-09, only write v2.0 format when diarization runs or user saves.
- **Blocking UI during diarization:** Diarization takes 30-120 seconds. Must be QThread per D-04.
- **Deleting audio before diarization:** Current code deletes temp WAV immediately. Must preserve for diarization.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Speaker diarization | Custom ML pipeline | pyannote.audio Pipeline.from_pretrained | Trained on massive datasets, handles VAD + embedding + clustering |
| Speaker count estimation | Manual heuristic | pyannote auto-detection | Pipeline handles clustering automatically |
| Audio format conversion | Manual ffmpeg wrapper | pyannote built-in resampling | Pipeline auto-converts sample rate and channels |
| Model download with auth | Custom HTTP + token logic | Pipeline.from_pretrained with token | Handles HuggingFace model hub authentication |
| Temporal alignment | Complex interval tree | Simple max-overlap loop | Whisper segments are coarse (2-10s); simple overlap is sufficient |

**Key insight:** pyannote.audio handles the entire diarization pipeline including VAD, segmentation, embedding, and clustering. The only custom code needed is temporal alignment between pyannote output and whisper segments.

## Common Pitfalls

### Pitfall 1: Audio File Lifecycle
**What goes wrong:** Temp WAV is deleted before diarization can run
**Why it happens:** Current `_on_transcription_done` unlinks temp_wav at line 1007 before AI tasks start
**How to avoid:** Move (not copy) the WAV file to the transcript folder before any cleanup
**Warning signs:** "File not found" errors when diarization starts

### Pitfall 2: MPS Sparse Tensor Crash
**What goes wrong:** `NotImplementedError: Could not run 'aten::_sparse_coo_tensor_with_dims_and_tensors' with arguments from the 'SparseMPS' backend`
**Why it happens:** PyTorch MPS backend doesn't support sparse COO tensors used internally by pyannote
**How to avoid:** Explicitly use `pipeline.to(torch.device("cpu"))`. Do NOT rely on `PYTORCH_ENABLE_MPS_FALLBACK=1` (it doesn't work for this case).
**Warning signs:** App crashes or hangs when running on Apple Silicon with MPS enabled

### Pitfall 3: HuggingFace Model Access Gate
**What goes wrong:** Model download fails with 401/403 error
**Why it happens:** pyannote models require (1) accepting terms on HuggingFace website and (2) valid access token
**How to avoid:** Clear error message guiding user to accept model terms; validate token before download attempt
**Warning signs:** First-time users always hit this -- need onboarding flow

### Pitfall 4: Import-Time Torch Loading
**What goes wrong:** App startup takes 5+ seconds
**Why it happens:** `import pyannote.audio` triggers torch import which is heavy (~3-5s)
**How to avoid:** Lazy import inside DiarizationWorker.run() only -- never at module level
**Warning signs:** App launch time regression

### Pitfall 5: Speaker Label Inconsistency Across Runs
**What goes wrong:** Same speakers get different labels (SPEAKER_00 vs SPEAKER_01) on re-run
**Why it happens:** pyannote assigns arbitrary labels based on order of first speech
**How to avoid:** Store speaker name mappings in transcript metadata; re-apply custom names after re-diarization by matching speaker patterns
**Warning signs:** User renames "SPEAKER_00" to "Alice" then re-runs diarization and loses the name

### Pitfall 6: CoreML Conversion Complexity
**What goes wrong:** CoreML conversion fails due to dynamic graph operations in pyannote
**Why it happens:** pyannote's internal logic has conditional statements based on input dimensions; CoreML requires static graphs
**How to avoid:** Treat CoreML as stretch goal; implement CPU-first with fallback architecture
**Warning signs:** `torch.jit.trace` failures, coremltools conversion errors

## Code Examples

### Loading Pipeline (Lazy Import Pattern)
```python
# Source: project pattern from Phase 2 (lazy pyobjc import)
def _load_pipeline(hf_token: str) -> Any:
    """pyannote 파이프라인을 로드한다 (lazy import)."""
    from pyannote.audio import Pipeline
    import torch

    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-community-1",
        token=hf_token,
    )
    pipeline.to(torch.device("cpu"))
    return pipeline
```

### Running Diarization
```python
# Source: https://huggingface.co/pyannote/speaker-diarization-community-1
from pyannote.audio import Pipeline

pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-community-1",
    token="hf_xxx",
)

# Run on audio file
output = pipeline("audio.wav")

# Exclusive mode -- one speaker at a time (best for transcript alignment)
for turn, speaker in output.exclusive_speaker_diarization:
    print(f"{speaker} speaks between t={turn.start:.3f}s and t={turn.end:.3f}s")

# Control speaker count (optional)
output = pipeline("audio.wav", min_speakers=2, max_speakers=5)
```

### Speaker Rename in Transcript
```python
def rename_speaker(
    transcript: dict[str, Any],
    old_label: str,
    new_name: str,
) -> dict[str, Any]:
    """화자 라벨을 사용자 지정 이름으로 변경한다."""
    # Update speaker mapping in metadata
    speakers = transcript.get("metadata", {}).get("speakers", {})
    speakers[old_label] = new_name
    transcript.setdefault("metadata", {})["speakers"] = speakers

    # Update all segment labels
    for seg in transcript.get("segments", []):
        if seg.get("speaker") == old_label:
            seg["speaker"] = new_name

    return transcript
```

### Schema v2.0 Transcript Structure
```json
{
  "version": "2.0",
  "metadata": {
    "title": "Team Meeting 2026-03-27",
    "created_at": "2026-03-27T10:00:00+00:00",
    "duration_seconds": 1800.0,
    "languages": ["en"],
    "source": "microphone",
    "model": "whisper-small",
    "tags": [],
    "speakers": {
      "SPEAKER_00": "Alice",
      "SPEAKER_01": "Bob"
    },
    "diarization": {
      "model": "pyannote/speaker-diarization-community-1",
      "completed_at": "2026-03-27T10:35:00+00:00"
    }
  },
  "segments": [
    {
      "start": 0.0,
      "end": 3.5,
      "text": "Good morning everyone",
      "language": "en",
      "confidence": 0.95,
      "speaker": "Alice"
    }
  ]
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pyannote 3.1 (onnxruntime) | pyannote 4.x community-1 (pure PyTorch) | Sep 2025 | 50% less speaker confusion, better counting |
| `use_auth_token` param | `token` param | pyannote 4.0 | API change in Pipeline.from_pretrained |
| speaker-diarization-3.1 | speaker-diarization-community-1 | Sep 2025 | New exclusive_speaker_diarization output |
| Manual speaker alignment | exclusive_speaker_diarization | pyannote 4.0 | Simplifies transcript-diarization alignment |

**Deprecated/outdated:**
- `pyannote.audio 3.x`: Still works but community-1 (4.x) is significantly better
- `use_auth_token` parameter: Replaced by `token` in Pipeline.from_pretrained
- `onnxruntime` dependency: Removed in 3.1+, pure PyTorch now

## Open Questions

1. **CoreML Conversion Feasibility from Python**
   - What we know: FluidInference has CoreML versions but only accessible via Swift SDK. Python coremltools conversion requires static graph workarounds.
   - What's unclear: Whether coremltools can handle pyannote 4.x community-1 model conversion without significant code modifications
   - Recommendation: Implement CPU-first. CoreML as stretch goal with clear pass/fail gate. If conversion fails, CPU performance on Apple Silicon is acceptable (~1-3 min for 30min audio).

2. **MPS Sparse Tensor Fix Timeline**
   - What we know: PyTorch MPS doesn't support sparse COO tensors. PYTORCH_ENABLE_MPS_FALLBACK=1 doesn't help for this case.
   - What's unclear: Whether PyTorch 2.11+ resolves this
   - Recommendation: Use CPU explicitly. Re-evaluate MPS support in future phase.

3. **HuggingFace Terms Acceptance UX**
   - What we know: Users must accept terms on huggingface.co before the token works for model downloads
   - What's unclear: Best UX flow for guiding users through this external step
   - Recommendation: Settings dialog with HF token input + clear instructions linking to the model page for terms acceptance

4. **Speaker Re-identification After Re-diarization**
   - What we know: pyannote assigns arbitrary speaker labels (SPEAKER_00, SPEAKER_01) that may change on re-run
   - What's unclear: Best strategy for preserving user-assigned names after re-diarization
   - Recommendation: Store raw diarization labels as internal keys. Map display names separately. On re-diarization, attempt to match new labels to old by temporal overlap of speaker segments.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | All | Yes | 3.11+ | -- |
| PyTorch | pyannote.audio | Yes | 2.8.0 | -- |
| pyannote.audio | Diarization | No | -- | Install via pip (optional dep) |
| coremltools | CoreML conversion (D-12) | No | -- | Skip CoreML, use CPU |
| MPS backend | Metal acceleration (D-13) | Yes (PyTorch) | -- | CPU (required due to sparse tensor bug) |
| HuggingFace token | Model download | N/A (user-provided) | -- | Cannot proceed without token |

**Missing dependencies with no fallback:**
- pyannote.audio -- must be installed. Already listed in pyproject.toml optional deps.

**Missing dependencies with fallback:**
- coremltools -- CoreML optimization optional; CPU is viable fallback
- MPS -- available but broken for pyannote; CPU fallback required

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ with pytest-qt 4.3+ |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/ -x --tb=short` |
| Full suite command | `pytest tests/ -x --tb=short -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DIAR-01 | Diarization assigns speaker labels to segments | unit | `pytest tests/test_diarizer.py::test_align_speakers -x` | No -- Wave 0 |
| DIAR-02 | TranscriptViewer displays speaker labels as inline prefix | unit | `pytest tests/test_main_window.py::test_transcript_viewer_speaker_labels -x` | No -- Wave 0 |
| DIAR-03 | Schema v2.0 with optional speaker field, backward compat | unit | `pytest tests/test_storage.py::test_schema_v2_speaker_field -x` | No -- Wave 0 |
| DIAR-04 | SRT/VTT exports include speaker labels | unit | `pytest tests/test_exporter.py::test_srt_speaker_labels -x` | Partial (export tests exist, speaker tests needed) |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x --tb=short`
- **Per wave merge:** `pytest tests/ -x --tb=short -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_diarizer.py` -- covers DIAR-01 (speaker alignment logic, mocked pipeline)
- [ ] `tests/test_storage.py::test_schema_v2_*` -- covers DIAR-03 (v2.0 schema, v1.0 backward compat)
- [ ] `tests/test_exporter.py::test_*_speaker_*` -- covers DIAR-04 (speaker labels in SRT/VTT export)
- [ ] `tests/test_main_window.py::test_transcript_viewer_speaker_*` -- covers DIAR-02 (speaker label display)

## Sources

### Primary (HIGH confidence)
- [pyannote/speaker-diarization-community-1 HuggingFace](https://huggingface.co/pyannote/speaker-diarization-community-1) - API usage, model requirements, output format
- [pyannote-audio PyPI](https://pypi.org/project/pyannote-audio/) - Version 4.0.4 confirmed
- [PyTorch MPS docs](https://docs.pytorch.org/docs/stable/notes/mps.html) - MPS backend limitations
- Existing codebase: `exporter.py`, `transcript_store.py`, `model_manager.py`, `keychain.py`, `main_window.py`

### Secondary (MEDIUM confidence)
- [FluidInference/speaker-diarization-coreml](https://huggingface.co/FluidInference/speaker-diarization-coreml) - CoreML performance benchmarks (10x CPU, 20x GPU speedup)
- [pyannote.ai community-1 blog](https://www.pyannote.ai/blog/community-1) - 50% speaker confusion reduction, exclusive diarization mode
- [pyannote MPS discussion #1155](https://github.com/pyannote/pyannote-audio/discussions/1155) - MPS sparse tensor incompatibility confirmed
- [PyTorch sparse tensor MPS issue #143955](https://github.com/pytorch/pytorch/issues/143955) - Upstream PyTorch bug

### Tertiary (LOW confidence)
- CoreML conversion from Python for pyannote 4.x -- no verified examples found; FluidInference used custom Swift pipeline
- MPS fix timeline -- no official PyTorch roadmap for sparse tensor MPS support

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - pyannote.audio 4.0.4 verified on PyPI, community-1 model well documented
- Architecture: MEDIUM - alignment algorithm is standard practice but needs tuning; CoreML path is uncertain
- Pitfalls: HIGH - MPS bug, import-time loading, audio lifecycle all verified from multiple sources
- CoreML/ANE optimization: LOW - no verified Python-side CoreML conversion path for pyannote 4.x

**Research date:** 2026-03-27
**Valid until:** 2026-04-27 (pyannote.audio stable; torch MPS may improve)
