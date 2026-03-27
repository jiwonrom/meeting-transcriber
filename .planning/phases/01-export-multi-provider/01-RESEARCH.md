# Phase 1: Export & Multi-Provider - Research

**Researched:** 2026-03-27
**Domain:** Subtitle export formats (SRT/VTT), Obsidian Markdown, multi-provider AI (OpenAI/Anthropic), provider fallback
**Confidence:** HIGH

## Summary

This phase adds three export formats (SRT, VTT, Obsidian Markdown) and two new AI providers (OpenAI, Anthropic) with automatic fallback. The existing codebase is well-structured for extension: `exporter.py` has a clear pure-function pattern for new formats, `AIProvider` ABC defines the 5-method contract, and `keychain.py` handles secure key storage. No new architectural patterns are needed -- this is additive work on established foundations.

The SRT and VTT formats are well-defined standards with minor but critical differences (SRT uses comma for milliseconds, VTT uses period; VTT requires "WEBVTT" header). The OpenAI and Anthropic Python SDKs both follow similar client-instantiation patterns. The main complexity is in the fallback orchestration within `AITaskWorker`, which currently takes a single provider and needs to support ordered fallback across multiple configured providers.

**Primary recommendation:** Implement exports as pure functions in `exporter.py` following existing patterns. Implement providers as new `AIProvider` subclasses. Add a `ProviderManager` to handle fallback logic, keeping `AITaskWorker` focused on task orchestration.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** SRT and VTT use millisecond precision timestamps (00:00:00,000 for SRT, 00:00:00.000 for VTT)
- **D-02:** When speaker labels are available, prefix each subtitle entry with speaker name (e.g., "Speaker 1: Hello everyone")
- **D-03:** Export actions appear in transcript viewer context/toolbar -- not a separate export dialog
- **D-04:** User configures default export directory in Preferences > General tab
- **D-05:** User sets Obsidian vault path in Preferences > General tab
- **D-06:** Obsidian export writes Markdown with YAML frontmatter: title, date, duration, languages, tags, source
- **D-07:** File naming follows Obsidian convention: `{YYYY-MM-DD}_{title}.md` (sanitized)
- **D-08:** No Obsidian API/plugin needed -- just write files to the vault directory
- **D-09:** Extend existing API Keys tab in Preferences with OpenAI and Anthropic key fields
- **D-10:** Global default provider selection (dropdown) with per-task override available in AI task settings
- **D-11:** Provider selection stored in settings.json under `ai.default_provider` and `ai.task_overrides`
- **D-12:** Implement OpenAIProvider and AnthropicProvider extending existing AIProvider ABC
- **D-13:** When primary provider fails, silently retry with next configured provider
- **D-14:** Show status bar message indicating fallback occurred (e.g., "Gemini failed, using OpenAI")
- **D-15:** Provider order: user's selected default -> other configured providers in order added
- **D-16:** If all providers fail, show error in status bar with last error message

### Claude's Discretion
- Export button placement in transcript viewer (toolbar vs menu vs both)
- Exact SRT/VTT formatting details beyond timestamp precision
- Provider configuration UI layout within existing Preferences tabs

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EXP-01 | User can export transcript as SRT subtitle file with proper timestamp formatting | SRT format spec documented; pure function pattern from existing `export_to_markdown`; timestamp conversion helper needed |
| EXP-02 | User can export transcript as VTT subtitle file with proper timestamp formatting | VTT format spec documented; nearly identical to SRT with header and period separator |
| EXP-03 | User can export transcript as Obsidian-compatible Markdown to a configured vault directory | YAML frontmatter pattern documented; file naming convention `{YYYY-MM-DD}_{title}.md` |
| EXP-04 | User can configure default export directory in Preferences | Extend `_create_general_tab()` in SettingsDialog; add `export.default_dir` to settings schema |
| BYOK-01 | User can add their own OpenAI API key in Preferences | Extend `_create_api_tab()` with OpenAI field; reuse `keychain.store_api_key("openai", key)` |
| BYOK-02 | User can add their own Anthropic API key in Preferences | Same pattern as BYOK-01 with `keychain.store_api_key("anthropic", key)` |
| BYOK-03 | User can select which AI provider to use for each task | Add provider dropdown to settings; store in `ai.default_provider` and `ai.task_overrides` |
| BYOK-04 | App falls back to next provider if primary fails | New `ProviderManager` class with ordered fallback; modify `_run_ai_tasks` in MainWindow |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- PEP8 via ruff auto-format
- All public functions need type hints + docstrings
- New features require pytest tests
- whisper.cpp inference in separate process only (not relevant to this phase)
- API keys in macOS Keychain only -- no plaintext files
- ui/ modules must NOT call external APIs directly
- No blocking I/O on main thread
- No changes to transcript.json schema

## Standard Stack

### Core (already in project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyQt6 | >=6.6 | UI framework | Already in use |
| keyring | >=25.0 | macOS Keychain API key storage | Already in use |
| google-generativeai | >=0.8 | Gemini provider | Already in use |

### New Dependencies
| Library | Latest Version | Purpose | Why Standard |
|---------|---------------|---------|--------------|
| openai | 2.30.0 | OpenAI API client (GPT-4o/GPT-5 chat completions) | Official SDK, type-safe, sync+async |
| anthropic | 0.86.0 | Anthropic API client (Claude messages API) | Official SDK, type-safe, sync+async |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| openai SDK | Raw httpx calls | SDK handles auth, retries, types; no reason to hand-roll |
| anthropic SDK | Raw httpx calls | Same reasoning |
| YAML frontmatter lib (python-frontmatter) | Manual string formatting | For the simple frontmatter needed, manual `---\n` formatting is sufficient and avoids a dependency |

**Installation:**
```bash
pip install openai>=2.0 anthropic>=0.80
```

**Version verification:** Confirmed via PyPI on 2026-03-27: openai 2.30.0, anthropic 0.86.0.

## Architecture Patterns

### New Files to Create
```
src/meeting_transcriber/
  ai/
    openai_provider.py       # OpenAIProvider(AIProvider)
    anthropic_provider.py    # AnthropicProvider(AIProvider)
    provider_manager.py      # ProviderManager — fallback orchestration
  storage/
    exporter.py              # ADD: export_to_srt(), export_to_vtt(), export_to_obsidian()
  ui/
    settings_dialog.py       # MODIFY: extend General + API tabs
    main_window.py           # MODIFY: add export actions to TranscriptViewer
  utils/
    config.py                # MODIFY: add new settings defaults
```

### Pattern 1: Pure Export Functions (existing pattern)
**What:** Each export format is a pure function taking a transcript dict and returning a formatted string.
**When to use:** All export formats.
**Example:**
```python
# Follows existing export_to_markdown / export_to_txt pattern
def export_to_srt(
    transcript: dict[str, Any],
    *,
    include_speaker: bool = True,
) -> str:
    """transcript를 SRT 자막 형식으로 내보낸다."""
    segments = transcript.get("segments", [])
    parts: list[str] = []
    for i, seg in enumerate(segments, 1):
        start = _format_srt_timestamp(seg.get("start", 0.0))
        end = _format_srt_timestamp(seg.get("end", 0.0))
        text = seg.get("text", "")
        if include_speaker and seg.get("speaker"):
            text = f"{seg['speaker']}: {text}"
        parts.append(f"{i}\n{start} --> {end}\n{text}\n")
    return "\n".join(parts)
```

### Pattern 2: Provider ABC Implementation (existing pattern)
**What:** Each provider subclass implements the 5 AIProvider abstract methods.
**When to use:** OpenAI and Anthropic providers.
**Example:**
```python
# Follows GeminiProvider pattern
class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str | None = None, model: str = "gpt-4o") -> None:
        key = api_key or get_api_key("openai")
        if not key:
            raise ValueError("OpenAI API key not found.")
        self._client = openai.OpenAI(api_key=key)
        self._model = model

    def _call(self, prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()

    # ... implement summarize, proofread, translate, extract_keywords, generate_title
    #     using same prompts as GeminiProvider
```

### Pattern 3: Provider Manager with Fallback
**What:** A manager that resolves the active provider and handles ordered fallback.
**When to use:** When `_run_ai_tasks` needs to execute with fallback.
**Example:**
```python
class ProviderManager:
    """AI 프로바이더 관리 및 폴백 처리."""

    PROVIDERS = {
        "gemini": ("meeting_transcriber.ai.gemini_provider", "GeminiProvider"),
        "openai": ("meeting_transcriber.ai.openai_provider", "OpenAIProvider"),
        "anthropic": ("meeting_transcriber.ai.anthropic_provider", "AnthropicProvider"),
    }

    def get_provider_chain(self, settings: dict) -> list[AIProvider]:
        """설정에 따라 우선순위 순서로 프로바이더 리스트를 반환한다."""
        default = settings.get("ai", {}).get("default_provider", "gemini")
        chain = [default]
        for name in self.PROVIDERS:
            if name != default and get_api_key(name):
                chain.append(name)
        return [self._instantiate(name) for name in chain if self._has_key(name)]

    def execute_with_fallback(
        self, chain: list[AIProvider], method: str, *args, **kwargs
    ) -> tuple[Any, str | None]:
        """체인의 프로바이더를 순서대로 시도하고 첫 성공 결과를 반환한다."""
        last_error = None
        for provider in chain:
            try:
                result = getattr(provider, method)(*args, **kwargs)
                return result, None
            except Exception as e:
                last_error = f"{provider.__class__.__name__}: {e}"
        raise RuntimeError(f"All providers failed. Last: {last_error}")
```

### Pattern 4: Settings Schema Extension
**What:** Add new keys to `_default_settings()` with deep-merge backward compatibility.
**When to use:** Adding export and AI provider settings.
**Example:**
```python
# In config.py _default_settings()
{
    # ... existing ...
    "export": {
        "default_dir": "",         # empty = ask each time
        "obsidian_vault": "",      # empty = not configured
    },
    "ai": {
        "default_provider": "gemini",
        "task_overrides": {},      # e.g. {"summarize": "openai", "translate": "anthropic"}
    },
}
```

### Anti-Patterns to Avoid
- **Calling AI APIs from ui/ modules:** Per CLAUDE.md, ui/ must not call external APIs. Provider instantiation and calls happen in ai/ module, orchestrated by AITaskWorker.
- **Blocking the main thread with exports:** File I/O for export is fast for transcript sizes (< 1MB), but Obsidian vault writes to external paths should still use `save_export()` which is non-blocking for typical sizes. If a concern arises, wrap in QThread.
- **Hardcoding provider in MainWindow:** Currently `_run_ai_tasks` imports GeminiProvider directly. Refactor to use ProviderManager so provider selection is dynamic.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OpenAI API client | HTTP client wrapper | `openai` SDK | Handles auth, retries, rate limits, streaming, type safety |
| Anthropic API client | HTTP client wrapper | `anthropic` SDK | Same reasoning |
| SRT timestamp formatting | Ad-hoc string formatting | Dedicated `_format_srt_timestamp()` helper | Comma vs period, zero-padding, edge cases at hour boundaries |
| macOS Keychain access | Direct Security framework calls | `keyring` library | Already in use, cross-platform, handles edge cases |
| YAML serialization | Manual string building | Manual `---\n` prefix (acceptable here) | Frontmatter is simple enough; adding `pyyaml` dependency is overkill for 6 fields |

**Key insight:** The export formats are simple enough that no external libraries are needed beyond the SDKs. The complexity is in getting the format details exactly right (comma vs period, header lines, newline conventions).

## Common Pitfalls

### Pitfall 1: SRT Comma vs VTT Period
**What goes wrong:** Using period in SRT timestamps or comma in VTT timestamps produces files that fail to load in players.
**Why it happens:** The formats are nearly identical except for this one character.
**How to avoid:** Separate timestamp formatters: `_format_srt_timestamp()` uses comma, `_format_vtt_timestamp()` uses period.
**Warning signs:** Subtitle files that open but show "0:00" for all entries in VLC or other players.

### Pitfall 2: VTT Missing Header
**What goes wrong:** VTT file without "WEBVTT" on the first line is not recognized by browsers or players.
**Why it happens:** Developer treats VTT as "SRT with periods" and forgets the required header.
**How to avoid:** VTT export function always starts with "WEBVTT\n\n".
**Warning signs:** HTML5 `<track>` element silently fails to load the file.

### Pitfall 3: Provider Import at Module Level
**What goes wrong:** Importing `openai` or `anthropic` at module level causes ImportError when the SDK is not installed.
**Why it happens:** These are new optional dependencies.
**How to avoid:** Lazy import inside provider class `__init__` or use try/except at module level. The existing GeminiProvider imports `google.generativeai` at module level, so the same pattern is acceptable IF the dependency is listed in `pyproject.toml`. Since we are adding openai/anthropic as required dependencies, module-level import is fine.
**Warning signs:** App crashes on startup for users who installed from an older requirements file.

### Pitfall 4: Fallback Masking Real Errors
**What goes wrong:** Silent fallback hides configuration errors (wrong API key, expired quota) from the user.
**Why it happens:** Per D-13, fallback is "silent" (no dialog), but D-14 requires a status bar message.
**How to avoid:** Always show which provider failed and which took over in the status bar. Log full error details to the log file.
**Warning signs:** User doesn't realize their primary provider is misconfigured and is always using fallback.

### Pitfall 5: Obsidian Filename Sanitization
**What goes wrong:** Special characters in transcript titles create invalid filenames or break Obsidian's wikilink system.
**Why it happens:** Titles may contain `/`, `\`, `|`, `#`, `^`, `[`, `]` which are special in Obsidian.
**How to avoid:** Sanitize: remove `/ \ | # ^ [ ]` and other filesystem-unsafe characters. Use the same `safe_title` pattern already in `MainWindow._on_transcription_done`.
**Warning signs:** Files appear in Finder but not in Obsidian's file explorer.

### Pitfall 6: Settings Cache Invalidation
**What goes wrong:** New settings keys (export.default_dir, ai.default_provider) are not picked up after save.
**Why it happens:** `config.py` uses `_settings_cache` and `_deep_merge` with defaults. New keys in defaults are merged correctly on first load, but if settings were loaded before the code update, the cache may not include new keys.
**How to avoid:** The existing `_deep_merge` pattern handles this correctly -- new default keys are preserved. Just ensure new keys are added to `_default_settings()`.
**Warning signs:** Settings appear empty after upgrade until app restart.

## Code Examples

### SRT Timestamp Formatter
```python
def _format_srt_timestamp(seconds: float) -> str:
    """초를 SRT 타임스탬프 형식(HH:MM:SS,mmm)으로 변환한다."""
    total_ms = int(seconds * 1000)
    h = total_ms // 3_600_000
    m = (total_ms % 3_600_000) // 60_000
    s = (total_ms % 60_000) // 1_000
    ms = total_ms % 1_000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
```

### VTT Timestamp Formatter
```python
def _format_vtt_timestamp(seconds: float) -> str:
    """초를 VTT 타임스탬프 형식(HH:MM:SS.mmm)으로 변환한다."""
    total_ms = int(seconds * 1000)
    h = total_ms // 3_600_000
    m = (total_ms % 3_600_000) // 60_000
    s = (total_ms % 60_000) // 1_000
    ms = total_ms % 1_000
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
```

### Obsidian YAML Frontmatter
```python
def _build_obsidian_frontmatter(metadata: dict[str, Any]) -> str:
    """Obsidian용 YAML frontmatter를 생성한다."""
    title = metadata.get("title", "Untitled")
    created = metadata.get("created_at", "")[:10]  # YYYY-MM-DD
    duration = metadata.get("duration_seconds", 0)
    languages = metadata.get("languages", [])
    tags = metadata.get("tags", [])
    source = metadata.get("source", "microphone")

    lines = [
        "---",
        f"title: \"{title}\"",
        f"date: {created}",
        f"duration: {int(duration)}",
        f"languages: [{', '.join(languages)}]",
        f"tags: [{', '.join(tags)}]",
        f"source: {source}",
        "---",
    ]
    return "\n".join(lines)
```

### OpenAI Provider Core Call
```python
# Using openai SDK v2.x
from openai import OpenAI

client = OpenAI(api_key=key)
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": prompt}],
)
text = response.choices[0].message.content.strip()
```

### Anthropic Provider Core Call
```python
# Using anthropic SDK v0.86.x
from anthropic import Anthropic

client = Anthropic(api_key=key)
message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[{"role": "user", "content": prompt}],
)
text = message.content[0].text.strip()
```

### QFileDialog for Directory Selection (Export/Obsidian paths)
```python
from PyQt6.QtWidgets import QFileDialog

def _browse_export_dir(self) -> None:
    """기본 내보내기 디렉토리를 선택한다."""
    path = QFileDialog.getExistingDirectory(
        self, "Select Export Directory", str(pathlib.Path.home())
    )
    if path:
        self._export_dir_input.setText(path)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| openai.ChatCompletion.create() | client.chat.completions.create() | openai SDK v1.0 (Nov 2023) | Must use new client-based API |
| anthropic.Completion | client.messages.create() | anthropic SDK v0.18 (2024) | Messages API is the only supported interface |
| SRT only | SRT + VTT + ASS | Ongoing | VTT is the web standard; SRT remains dominant for desktop players |

**Deprecated/outdated:**
- `openai.ChatCompletion.create()` -- removed in openai SDK v1.0+. Use `OpenAI().chat.completions.create()`.
- `anthropic.Client().completion()` -- old completions API. Use `Anthropic().messages.create()`.

## Open Questions

1. **Default model for each provider**
   - What we know: Gemini uses "gemini-2.0-flash". OpenAI has gpt-4o, gpt-5. Anthropic has claude-sonnet-4.
   - What's unclear: Which model balances cost/speed best for transcript tasks (summarize, proofread)
   - Recommendation: Default to cost-effective fast models: `gpt-4o-mini` for OpenAI, `claude-sonnet-4-20250514` for Anthropic. These are sufficient for summarization/proofreading and keep API costs low.

2. **Per-task provider override UI**
   - What we know: D-10 requires per-task override capability
   - What's unclear: Where exactly in the UI this appears (separate section in API tab? dropdown per task?)
   - Recommendation: Add a "Task Providers" section below the key fields in the API Keys tab with dropdowns for each task type (summarize, proofread, translate, keywords, title). Default each to "Use Default Provider".

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-qt 4.3 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/ -x --tb=short` |
| Full suite command | `pytest tests/ --tb=short` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXP-01 | SRT export with correct timestamps | unit | `pytest tests/test_exporter.py -k "srt" -x` | Partially (test_exporter.py exists, SRT tests needed) |
| EXP-02 | VTT export with correct timestamps | unit | `pytest tests/test_exporter.py -k "vtt" -x` | Partially (VTT tests needed) |
| EXP-03 | Obsidian Markdown export with frontmatter | unit | `pytest tests/test_exporter.py -k "obsidian" -x` | Partially (Obsidian tests needed) |
| EXP-04 | Default export directory persists in settings | unit | `pytest tests/test_config.py -k "export" -x` | Partially (config tests exist, export key tests needed) |
| BYOK-01 | OpenAI API key stored in Keychain | unit | `pytest tests/test_keychain.py -k "openai" -x` | Partially (keychain tests exist, OpenAI-specific tests trivial) |
| BYOK-02 | Anthropic API key stored in Keychain | unit | `pytest tests/test_keychain.py -k "anthropic" -x` | Partially (same pattern) |
| BYOK-03 | Provider selection per task | unit | `pytest tests/test_ai_provider.py -k "provider_manager" -x` | No -- Wave 0 |
| BYOK-04 | Fallback to next provider on failure | unit | `pytest tests/test_ai_provider.py -k "fallback" -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_exporter.py tests/test_ai_provider.py -x --tb=short`
- **Per wave merge:** `pytest tests/ -x --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_exporter.py` -- add SRT, VTT, Obsidian export tests (file exists, extend)
- [ ] `tests/test_ai_provider.py` -- add ProviderManager, fallback, OpenAI/Anthropic mock tests (file exists, extend)
- [ ] `tests/test_config.py` -- add export/AI settings defaults tests (file exists, extend)

## Sources

### Primary (HIGH confidence)
- [SubRip Wikipedia](https://en.wikipedia.org/wiki/SubRip) -- SRT format specification
- [W3C WebVTT Spec](https://www.w3.org/TR/webvtt1/) -- VTT format specification
- [MDN WebVTT](https://developer.mozilla.org/en-US/docs/Web/API/WebVTT_API/Web_Video_Text_Tracks_Format) -- VTT format reference
- [OpenAI Python SDK GitHub](https://github.com/openai/openai-python) -- SDK usage patterns
- [Anthropic Python SDK GitHub](https://github.com/anthropics/anthropic-sdk-python) -- SDK usage patterns
- [PyPI openai 2.30.0](https://pypi.org/project/openai/) -- latest version verified
- [PyPI anthropic 0.86.0](https://pypi.org/project/anthropic/) -- latest version verified

### Secondary (MEDIUM confidence)
- [OpenAI Developers Changelog](https://developers.openai.com/api/docs/changelog) -- current model names
- [Anthropic Client SDKs](https://platform.claude.com/docs/en/api/client-sdks) -- messages API usage

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- using official SDKs with verified versions, extending established codebase patterns
- Architecture: HIGH -- follows existing patterns exactly (pure export functions, ABC providers, keychain storage)
- Pitfalls: HIGH -- SRT/VTT specs are stable and well-documented; provider SDK patterns are well-known

**Research date:** 2026-03-27
**Valid until:** 2026-04-27 (stable domain, 30 days)
