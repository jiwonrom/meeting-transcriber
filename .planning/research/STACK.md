# Technology Stack

**Project:** Scribe v2.0
**Researched:** 2026-03-27

## Recommended Stack

### System Audio Capture
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| BlackHole | 2.0+ | Virtual audio loopback driver for macOS | Only viable open-source virtual audio driver on macOS. Soundflower is abandoned. BlackHole is actively maintained (14k+ GitHub stars), supports Apple Silicon natively, and uses the modern Audio Server Plugin architecture on macOS 12+. |
| sounddevice | >=0.4.6 (existing) | Capture audio from BlackHole virtual device | Already in the stack. BlackHole registers as a standard CoreAudio device, so sounddevice can capture from it via the existing `AudioCaptureWorker(device=blackhole_device_index)`. Zero audio capture code changes needed. |

**Confidence:** MEDIUM -- BlackHole is the de-facto standard but requires user installation of a system-level audio plugin. No pure-Python alternative exists for system audio on macOS.

**Key insight:** The app does NOT need new audio capture code. BlackHole appears as a regular audio input device. The real engineering is: (1) detecting BlackHole installation, (2) guiding users through Multi-Output Device setup in Audio MIDI Setup, (3) optionally automating aggregate device creation via CoreAudio API through pyobjc.

### Speaker Diarization
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pyannote.audio | >=3.3 | Speaker diarization pipeline | Best open-source diarization accuracy (DER <10% on AMI benchmark). Already listed in pyproject.toml optional deps. Supports incremental processing since v3.1+. |
| torch | >=2.2 | PyTorch backend for pyannote | Required by pyannote. Use 2.2+ for improved MPS (Metal Performance Shaders) support on Apple Silicon. MPS backend gives ~2x speedup over CPU for inference. |
| onnxruntime | >=1.17 | CoreML/ANE execution provider for speaker embedding model | For ANE optimization: convert pyannote's ECAPA-TDNN embedding model to ONNX, run via CoreML execution provider. Offloads speaker embedding extraction to Apple Neural Engine. |
| speechbrain | >=1.0 | Speaker embedding model (pyannote dependency) | Transitive dependency of pyannote for ECAPA-TDNN embeddings. Pin to >=1.0 for stable API. |

**Confidence:** MEDIUM-HIGH for pyannote itself, MEDIUM for ANE optimization path (requires custom model conversion, no established community workflow).

**Real-time diarization architecture:**
- Incremental approach: run diarization on accumulated audio every 10 seconds, merge with previous results
- Speaker embedding extraction is the bottleneck (~200ms per segment on CPU). ANE offload targets this.
- Alternative lightweight path: whisper.cpp `--tinydiarize` flag for speaker change detection with zero additional model overhead (lower accuracy but zero latency cost).

### Meeting Templates & Cross-Meeting Analysis
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Jinja2 | >=3.1 | Template rendering for meeting format output | Lightweight, well-known, supports conditionals and loops needed for complex meeting templates. |
| google-generativeai | >=0.8 (existing) | Cross-meeting analysis via Gemini | Already in stack. Cross-meeting analysis = multi-transcript summarization prompt. Extend existing `AIProvider` ABC with `analyze_multiple()` method. No new AI library needed. |

**Confidence:** HIGH -- Application-layer features. Template system is straightforward. Cross-meeting analysis is a prompt engineering problem.

### Export Integrations
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pysrt | >=1.1.2 | SRT subtitle file generation | Mature, tiny library for SRT format. Handles encoding, timecode formatting, sequence numbering correctly. |
| webvtt-py | >=0.5.1 | VTT subtitle file generation | Standard WebVTT library. Handles VTT cue format, header, timestamp formatting. |
| notion-client | >=2.2 | Notion API integration | Official Notion SDK for Python. Handles auth, pagination, rate limiting. Needed for page creation. |

**Confidence:** HIGH for SRT/VTT (trivial format), MEDIUM for Notion (API authentication/OAuth complexity).

**Obsidian export needs NO library.** Obsidian vaults are directories of Markdown files. Export = write `.md` files with YAML frontmatter to a user-specified directory path.

### BYOK (Bring Your Own Key)
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| openai | >=1.30 | OpenAI-compatible API provider | The `openai` SDK supports any OpenAI-compatible endpoint (OpenAI, Groq, Together, local Ollama). One library covers many providers via `base_url` parameter. |
| anthropic | >=0.30 | Anthropic Claude provider | Clean SDK, strong typing, good error messages. For users who prefer Claude. |

**Confidence:** HIGH -- Both SDKs are mature and stable.

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| System audio | BlackHole | Soundflower | Abandoned since 2014. Crashes on Apple Silicon. |
| System audio | BlackHole | ScreenCaptureKit | Apple's API (macOS 13+) can capture app audio but requires screen recording permission, per-app selection, and Objective-C bridge via pyobjc. More fragile integration. Worth revisiting for v3.0 as Apple adds more audio-specific APIs, but too much uncertainty for v2.0. |
| System audio | BlackHole | Loopback (Rogue Amoeba) | Commercial ($99), not embeddable/redistributable. Cannot bundle with free app. |
| Diarization | pyannote.audio | whisperX | WhisperX bundles pyannote internally. Using pyannote directly gives pipeline control, especially for incremental/streaming use. |
| Diarization | pyannote.audio | NeMo MSDD | NVIDIA NeMo is CUDA-focused, poor Apple Silicon support, massive dependency tree. Wrong platform. |
| ANE acceleration | onnxruntime+CoreML EP | coremltools direct | coremltools converts PyTorch to CoreML, but onnxruntime's CoreML execution provider is more battle-tested for inference from Python. |
| SRT export | pysrt | Manual formatting | SRT format has edge cases (BOM, CRLF, timecode format). pysrt handles them. Tiny dependency cost. |
| VTT export | webvtt-py | Manual formatting | Same reasoning. Edge cases in cue timing format. |
| Notion export | notion-client | Raw HTTP requests | Official SDK handles auth flow, retries, pagination. No reason to DIY. |
| Obsidian export | Direct file write | obsidiantools | obsidiantools is for reading/analyzing vaults, not writing. Export = write files. Over-engineering. |
| Template engine | Jinja2 | string.Template | Jinja2 supports conditionals, loops, filters needed for meeting format complexity. string.Template is too primitive. |
| Multi-provider | openai SDK | litellm | litellm abstracts many providers but adds a heavy abstraction layer and is a fast-moving target with frequent breaking changes. openai SDK + explicit provider implementations is more predictable. |

## What NOT to Use

| Technology | Why Not |
|------------|---------|
| Soundflower | Abandoned. Kernel panics on Apple Silicon. |
| ScreenCaptureKit (for v2.0) | Requires pyobjc bridge, screen recording permission (confusing for audio-only use), per-app selection UX. Defer to v3.0. |
| whisperX as a dependency | Bundles too much (pyannote, wav2vec2, its own whisper). The app already uses whisper.cpp subprocess which is superior for real-time. |
| NeMo | NVIDIA/CUDA-focused. Wrong platform for Apple Silicon. |
| litellm | Abstracts providers but introduces version churn risk. Better to implement 2-3 providers directly against stable SDKs. |
| obsidiantools | For vault analysis, not export. Just write Markdown files. |
| pyaudiowpatch | Windows-only WASAPI loopback. Not relevant on macOS. |

## Updated pyproject.toml Dependencies

```toml
[project]
dependencies = [
    "PyQt6>=6.6",
    "sounddevice>=0.4.6",
    "numpy>=1.26",
    "keyring>=25.0",
    "google-generativeai>=0.8",
    "Jinja2>=3.1",
    "pysrt>=1.1.2",
    "webvtt-py>=0.5.1",
]

[project.optional-dependencies]
diarization = [
    "pyannote.audio>=3.3",
    "torch>=2.2",
    "speechbrain>=1.0",
]
ane = [
    "onnxruntime>=1.17",
]
notion = [
    "notion-client>=2.2",
]
byok = [
    "openai>=1.30",
    "anthropic>=0.30",
]
dev = [
    "pytest>=8.0",
    "pytest-qt>=4.3",
    "pytest-cov>=5.0",
    "ruff>=0.5",
    "mypy>=1.10",
    "pre-commit>=3.7",
]
video = [
    "av>=12.0",
]
```

## BlackHole Integration Details

BlackHole is NOT a pip package. It is a macOS audio driver installed system-wide.

**User setup flow:**
1. Install BlackHole: `brew install blackhole-2ch`
2. Open Audio MIDI Setup (macOS built-in utility)
3. Create a Multi-Output Device: real speakers + BlackHole 2ch
4. Set the Multi-Output Device as system output
5. In Scribe, select "BlackHole 2ch" as input device

**App detection logic:**
```python
# Check if BlackHole is available as an audio device
for device in sounddevice.query_devices():
    if "blackhole" in device["name"].lower() and device["max_input_channels"] > 0:
        return device  # BlackHole is installed and available
```

**App responsibilities:**
- Detect BlackHole in device list (check `sounddevice.query_devices()`)
- Show setup wizard if not detected, with step-by-step instructions
- Provide a "Capture system audio" toggle in settings that switches input device to BlackHole
- Handle the case where user removes BlackHole after setup (graceful fallback to mic)

**Risk:** macOS updates can break audio plugins. BlackHole uses the modern Audio Server Plugin architecture (not kernel extension) since macOS 12, which is more resilient. Still, validate after each macOS major release.

## pyannote Real-Time Diarization Details

**Incremental approach (recommended for v2.0):**

```
Recording starts
  -> Every 10 seconds:
     1. Run diarization on full audio accumulated so far
     2. Compare with previous diarization result
     3. Merge: keep stable speaker labels for earlier segments, update recent ones
     4. Emit updated speaker assignments to UI
```

**Performance on Apple Silicon (estimated):**
- M1/M2 CPU: ~1s for 10min audio, ~3s for 30min, ~8s for 1hr
- M1/M2 MPS: ~0.5s for 10min, ~1.5s for 30min, ~4s for 1hr
- M1/M2 ANE (ONNX+CoreML): ~0.3s for 10min, ~1s for 30min, ~2.5s for 1hr (estimated, needs validation)

**Why not true frame-level streaming:** pyannote's pipeline is designed for full-audio processing. Frame-by-frame streaming produces lower accuracy and unstable speaker labels (speakers merge/split unpredictably). Incremental re-processing is the pragmatic middle ground.

**Fallback: whisper.cpp --tinydiarize:**
- Built into whisper.cpp, zero additional dependencies
- Detects speaker changes (not speaker identity) -- marks "new speaker" in output
- Much lower accuracy than pyannote but zero latency overhead
- Good for "lightweight mode" setting

## Sources

- BlackHole: https://github.com/ExistentialAudio/BlackHole
- pyannote.audio: https://github.com/pyannote/pyannote-audio
- pysrt: https://github.com/byroot/pysrt
- webvtt-py: https://github.com/glut23/webvtt-py
- notion-client: https://github.com/ramnes/notion-sdk-py
- onnxruntime CoreML EP: https://onnxruntime.ai/docs/execution-providers/CoreML-ExecutionProvider.html

**Confidence note:** WebSearch was unavailable during this research. All version numbers are based on training data (cutoff: May 2025). Verify versions against PyPI before adding to pyproject.toml. The most likely stale information is pyannote.audio version (may have released 3.4+ with improved streaming) and onnxruntime version (moves fast).
