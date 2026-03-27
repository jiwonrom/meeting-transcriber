---
phase: 03-speaker-diarization
verified: 2026-03-27T18:30:00Z
status: passed
score: 12/12 must-haves verified
re_verification: false
---

# Phase 3: Speaker Diarization Verification Report

**Phase Goal:** Transcripts identify who said what, with speaker labels visible in the UI and exports
**Verified:** 2026-03-27
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | After a recording completes, user can trigger diarization and see speaker labels assigned to transcript segments | VERIFIED | `_auto_diarize()` at main_window.py:1236 wired into `_on_transcription_done`; `_on_identify_speakers_requested` handles manual trigger |
| 2 | Transcript viewer displays speaker labels (inline text prefix) next to each segment | VERIFIED | `setHtml()` with `font-weight: 600` speaker prefix at main_window.py:302–317; test `test_transcript_viewer_speaker_labels` passes |
| 3 | Existing v1.x transcripts load without error (schema v2.0 migration is backward-compatible) | VERIFIED | `create_transcript` only sets version "2.0" when `speakers is not None`; v1.0 path leaves schema unchanged; test `test_transcript_viewer_no_speaker_labels` passes |
| 4 | SRT/VTT exports include speaker labels prefixed to each subtitle entry when diarization data is available | VERIFIED | `export_to_srt`/`export_to_vtt` have `include_speaker=True` default; 4 new exporter tests pass including `test_srt_speaker_labels_included` |

### Plan-Level Truths (from must_haves frontmatter)

**03-01 must_haves:**

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Speaker labels can be assigned to transcript segments after diarization runs | VERIFIED | `align_speakers()` returns segments with "speaker" key; `DiarizationWorker.run()` calls it at diarizer.py:287 |
| 2 | v1.0 transcripts load without error after schema upgrade — missing speaker fields default to empty | VERIFIED | `seg.get("speaker", "")` pattern throughout; no forced migration on load |
| 3 | Users can rename a speaker and see the change applied to all that speaker's segments | VERIFIED | `rename_speaker()` updates both segments and metadata.speakers dict; wired to `_on_speaker_clicked` in TranscriptViewer |
| 4 | SRT/VTT exports include speaker labels when diarization data is present | VERIFIED | exporter.py:272, 306 — `include_speaker` param, speaker prefix format |
| 5 | First-time diarization triggers on-demand model download with visible progress — no silent freeze | VERIFIED | diarizer.py:258 emits "Downloading speaker identification model..." when `was_cached is False`; lazy import inside `run()` |

**03-02 must_haves:**

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | After recording completes, diarization auto-runs and speaker labels appear in TranscriptViewer | VERIFIED | `_auto_diarize()` called at main_window.py:1236; `_on_diarization_done` calls `display_transcript` to refresh viewer |
| 2 | User can click 'Identify Speakers' button on any transcript with an audio file to trigger diarization | VERIFIED | `_identify_speakers_clicked()` at main_window.py:436; button wired to `diarization_requested` signal |
| 3 | Speaker labels display as inline text prefix ('Speaker 1: text') in the Original tab | VERIFIED | HTML rendering with speaker prefix in `display_transcript()` at main_window.py:309–316 |
| 4 | User can rename speakers via the speaker list panel — rename propagates to all segments | VERIFIED | `_on_speaker_clicked()` uses `QInputDialog.getText` then `rename_speaker()`; calls `save_transcript()` and refresh |
| 5 | User can add HuggingFace token in Settings > Speaker Identification section | VERIFIED | `_create_speaker_tab()` in settings_dialog.py:276; token stored via `store_api_key("huggingface", ...)` with "hf_" validation |
| 6 | Status bar shows 'Identifying speakers...' during diarization and 'Speakers identified' on completion | VERIFIED | main_window.py:1353 and 1382 |
| 7 | Audio WAV file is preserved in transcript folder for diarization (not deleted after transcription) | VERIFIED | `temp_wav.rename(folder / "recording.wav")` at main_window.py:1216; `temp_wav.unlink` only occurs in exception path (line 1184) and cross-device copy fallback (line 1222) |

**03-03 must_haves:**

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Diarization uses CoreML model on Apple Neural Engine when conversion succeeds | VERIFIED | `_try_coreml_pipeline()` at diarizer.py:185; emits "Identifying speakers (CoreML)..." when successful |
| 2 | Diarization falls back to CPU (torch) when CoreML conversion fails | VERIFIED | Returns None on any exception; `run()` at diarizer.py:271 uses CPU path when `coreml_result is None` |
| 3 | CoreML converted model is cached so conversion only runs once | VERIFIED | Cache check at diarizer.py:212; `DIARIZATION_COREML_DIR / "segmentation.mlpackage"` |

**Score:** 12/12 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/meeting_transcriber/core/diarizer.py` | DiarizationWorker, align_speakers, rename_speaker, DiarizationModelManager, CoreML support | VERIFIED | All 4 classes/functions present; `_try_coreml_pipeline` present; lazy imports via `_import_pipeline()`/`_import_torch()` |
| `src/meeting_transcriber/storage/transcript_store.py` | Schema v2.0 with speakers param, update_transcript_speakers | VERIFIED | `speakers: dict[str, str] | None = None` param; conditional `"version": "2.0"`; `update_transcript_speakers()` present |
| `src/meeting_transcriber/ui/main_window.py` | TranscriptViewer with speaker labels, speaker panel, identify button, auto-diarization | VERIFIED | All wiring present: `_auto_diarize`, `_on_diarization_done`, `_on_identify_speakers_requested`, `_speaker_panel`, `_identify_btn`, `setHtml()` rendering |
| `src/meeting_transcriber/ui/settings_dialog.py` | HuggingFace token input in Speaker Identification section | VERIFIED | `_create_speaker_tab()` with `hf_token_input`, `hf_"` validation, `store_api_key("huggingface", ...)`, "Get Token" button with URL |
| `src/meeting_transcriber/utils/constants.py` | DIARIZATION_MODEL, DIARIZATION_DEVICE, DIARIZATION_CACHE_DIR, DIARIZATION_COREML_DIR | VERIFIED | All 4 constants present at lines 49–52 |
| `src/meeting_transcriber/utils/exceptions.py` | DiarizationError subclass | VERIFIED | `class DiarizationError(MeetingTranscriberError)` at line 38 |
| `tests/test_diarizer.py` | 10+ test functions for diarizer module | VERIFIED | 16 test methods: TestAlignSpeakers (3), TestRenameSpeaker (2), TestDiarizationModelManager (2), TestDiarizationWorker (3), TestCoreMLOptimization (6) |
| `tests/test_storage.py` | Schema v2.0 and backward compat tests | VERIFIED | `test_create_transcript_v2_with_speakers`, `test_update_transcript_speakers` present; 3 v2-related test functions |
| `tests/test_exporter.py` | Speaker label export tests for SRT/VTT | VERIFIED | `test_srt_speaker_labels_included`, `test_srt_no_speaker_clean_text`, `test_vtt_speaker_labels_included`, `test_srt_include_speaker_false_omits_labels` — 4 speaker tests |
| `tests/test_main_window.py` | 5 speaker-related test functions | VERIFIED | `test_transcript_viewer_speaker_labels`, `test_transcript_viewer_no_speaker_labels`, `test_transcript_viewer_identify_btn_states`, `test_transcript_viewer_speaker_panel_visible`, `test_transcript_viewer_identify_btn_label_reidentify` |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `diarizer.py` | `pyannote.audio` | lazy import via `_import_pipeline()` inside `run()` | WIRED | `_import_pipeline()` at diarizer.py:18; called in `run()` at line 244 |
| `diarizer.py` | `keychain.py` | `hf_token` parameter passed from MainWindow | WIRED | Token retrieved via `get_api_key("huggingface")` in `_auto_diarize()` at main_window.py:1337 |
| `diarizer.py` | HuggingFace model hub | `DiarizationModelManager.is_model_cached()` + download progress emit | WIRED | `was_cached` check at diarizer.py:255–258; download message emitted at line 258 |
| `transcript_store.py` | transcript.json files | `create_transcript` with speakers kwarg produces v2.0 | WIRED | Conditional version logic at transcript_store.py:55–60 |
| `main_window.py` | `diarizer.py` | `DiarizationWorker` instantiation in `_auto_diarize` and `_on_identify_speakers_requested` | WIRED | `from meeting_transcriber.core.diarizer import DiarizationWorker` at lines 1341, 1416 |
| `main_window.py` | `transcript_store.py` | `update_transcript_speakers` to persist diarization results | WIRED | Imported at main_window.py:43; called in `_on_diarization_done` at line 1381 |
| `settings_dialog.py` | `keychain.py` | `store_api_key("huggingface", token)` | WIRED | Called in `_save_hf_token()` at settings_dialog.py:348 |
| `main_window.py` | `recording.wav` | `temp_wav.rename(folder / "recording.wav")` with shutil fallback | WIRED | main_window.py:1216–1222 |
| `diarizer.py` | `coremltools` | lazy import inside `_try_coreml_pipeline` | WIRED | `import coremltools as ct` inside try block at diarizer.py:249; `ct` param passed to `_try_coreml_pipeline` |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `TranscriptViewer.display_transcript()` | `speakers_map` | `transcript["metadata"]["speakers"]` loaded from disk via `load_transcript()` | Yes — file content, not hardcoded | FLOWING |
| `TranscriptViewer._update_speaker_panel()` | `unique_speakers` | extracted from `segments` via `seg.get("speaker", "")` | Yes — data from diarization results | FLOWING |
| `MainWindow._on_diarization_done()` | `speakers` dict | built from labeled segments emitted by `DiarizationWorker.finished` | Yes — pipeline output | FLOWING |
| `export_to_srt()` | segment speaker prefix | `seg.get("speaker", "")` from loaded transcript | Yes — stored in v2.0 transcript.json | FLOWING |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| DiarizationWorker emits labeled segments | `pytest tests/test_diarizer.py::TestDiarizationWorker` | 3 passed | PASS |
| Speaker labels render in HTML viewer | `pytest tests/test_main_window.py::test_transcript_viewer_speaker_labels` | 1 passed | PASS |
| SRT export includes speaker prefix | `pytest tests/test_exporter.py::test_srt_speaker_labels_included` | 1 passed | PASS |
| v1.0 backward compat on load | `pytest tests/test_main_window.py::test_transcript_viewer_no_speaker_labels` | 1 passed | PASS |
| CoreML fallback to CPU | `pytest tests/test_diarizer.py::TestCoreMLOptimization` | 6 passed | PASS |
| Full test suite regression | `pytest tests/ -x --tb=short` | 290 passed | PASS |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DIAR-01 | 03-01, 03-02, 03-03 | Post-recording diarization assigns speaker labels to transcript segments | SATISFIED | `DiarizationWorker` + `align_speakers` + auto-diarize trigger wired in MainWindow |
| DIAR-02 | 03-02 | Transcript viewer displays speaker labels (inline text prefix per speaker) | SATISFIED | `setHtml()` with speaker prefix in `display_transcript()`; 2 viewer tests verify |
| DIAR-03 | 03-01 | Transcript schema v2.0 supports optional speaker field per segment | SATISFIED | `create_transcript(speakers=...)` produces v2.0; v1.0 unchanged when speakers=None |
| DIAR-04 | 03-01, 03-02 | SRT/VTT exports include speaker labels when available | SATISFIED | `export_to_srt`/`export_to_vtt` with `include_speaker=True` default; 4 tests verify |

All 4 DIAR requirements satisfied. No orphaned requirements.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | — |

Specifically checked:
- No `temp_wav.unlink` in the happy-path recording flow (only in exception path + cross-device copy)
- No empty/static returns in DiarizationWorker or update_transcript_speakers
- No TODO/FIXME/placeholder comments in new code
- No MPS device references (`torch.device("mps")` absent from diarizer.py as required)
- No module-level pyannote/torch imports (lazy import pattern enforced)

---

## Human Verification Required

The following behaviors require human testing as they cannot be verified programmatically:

### 1. End-to-End Diarization with Real pyannote Model

**Test:** Install HuggingFace token, accept pyannote model terms, record 15–30s audio with 2 speakers, verify auto-diarization runs
**Expected:** Status bar shows "Downloading speaker identification model..." (first run), then "Identifying speakers...", then "Speakers identified"; speaker labels appear in Original tab
**Why human:** Requires real pyannote.audio and model download from HuggingFace; cannot mock end-to-end

### 2. Speaker Rename Flow

**Test:** Display a v2.0 transcript with speakers; click a speaker name in the panel; rename via dialog
**Expected:** All segments for that speaker show the new name; transcript.json updated on disk
**Why human:** QInputDialog interaction requires manual UI interaction

### 3. "Re-identify Speakers" Button After Diarization

**Test:** After diarization completes, verify button text changes to "Re-identify Speakers" and is re-enabled
**Expected:** Button updates correctly when viewer path matches the diarized transcript
**Why human:** Requires live diarization completion to trigger the refresh path in `_on_diarization_done`

### 4. Settings HF Token Persistence

**Test:** Open Settings > Speaker Identification, enter a valid token starting with "hf_", click Save Token
**Expected:** Status shows "Token saved"; on re-open, placeholder shows "••••••• (saved)"
**Why human:** Keychain write/read requires actual macOS Keychain access

---

## Gaps Summary

No gaps found. All 12 must-have truths verified, all artifacts present and substantive, all key links wired, data flows confirmed, 290/290 tests pass.

---

*Verified: 2026-03-27*
*Verifier: Claude (gsd-verifier)*
