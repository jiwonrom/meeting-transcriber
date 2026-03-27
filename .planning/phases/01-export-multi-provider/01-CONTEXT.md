# Phase 1: Export & Multi-Provider - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase adds three export formats (SRT, VTT, Obsidian Markdown) and multi-provider AI support (BYOK: OpenAI, Anthropic alongside existing Gemini). No audio pipeline changes. No new UI windows — extends existing Preferences and adds export actions to transcript viewer.

</domain>

<decisions>
## Implementation Decisions

### Export Formats
- **D-01:** SRT and VTT use millisecond precision timestamps (00:00:00,000 for SRT, 00:00:00.000 for VTT)
- **D-02:** When speaker labels are available, prefix each subtitle entry with speaker name (e.g., "Speaker 1: Hello everyone")
- **D-03:** Export actions appear in transcript viewer context/toolbar — not a separate export dialog
- **D-04:** User configures default export directory in Preferences > General tab

### Obsidian Integration
- **D-05:** User sets Obsidian vault path in Preferences > General tab
- **D-06:** Obsidian export writes Markdown with YAML frontmatter: title, date, duration, languages, tags, source
- **D-07:** File naming follows Obsidian convention: `{YYYY-MM-DD}_{title}.md` (sanitized)
- **D-08:** No Obsidian API/plugin needed — just write files to the vault directory

### Multi-Provider (BYOK)
- **D-09:** Extend existing API Keys tab in Preferences with OpenAI and Anthropic key fields
- **D-10:** Global default provider selection (dropdown) with per-task override available in AI task settings
- **D-11:** Provider selection stored in settings.json under `ai.default_provider` and `ai.task_overrides`
- **D-12:** Implement OpenAIProvider and AnthropicProvider extending existing AIProvider ABC

### Fallback Behavior
- **D-13:** When primary provider fails, silently retry with next configured provider
- **D-14:** Show status bar message indicating fallback occurred (e.g., "Gemini failed, using OpenAI")
- **D-15:** Provider order: user's selected default → other configured providers in order added
- **D-16:** If all providers fail, show error in status bar with last error message

### Claude's Discretion
- Export button placement in transcript viewer (toolbar vs menu vs both)
- Exact SRT/VTT formatting details beyond timestamp precision
- Provider configuration UI layout within existing Preferences tabs

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Export Formats
- `PRD.md` §4.1.5 — transcript.json schema (segments with start/end/text/language/confidence)
- `src/meeting_transcriber/storage/exporter.py` — existing Markdown/TXT export pattern to extend
- `src/meeting_transcriber/storage/transcript_store.py` — transcript CRUD, load_transcript function

### AI Provider
- `src/meeting_transcriber/ai/provider_base.py` — AIProvider ABC (5 methods: summarize, proofread, translate, extract_keywords, generate_title)
- `src/meeting_transcriber/ai/gemini_provider.py` — reference implementation for new providers
- `src/meeting_transcriber/ai/tasks.py` — AITaskWorker orchestration (proofread→summarize→keywords→title)
- `src/meeting_transcriber/utils/keychain.py` — API key storage pattern (store_api_key, get_api_key)

### Settings
- `src/meeting_transcriber/ui/settings_dialog.py` — existing 4-tab Preferences dialog to extend
- `src/meeting_transcriber/utils/config.py` — settings load/save with cache

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `storage/exporter.py`: `export_markdown()` and `export_txt()` — pattern for new export functions
- `ai/provider_base.py`: `AIProvider` ABC — extend for OpenAI/Anthropic providers
- `ai/gemini_provider.py`: Reference implementation showing how to implement provider ABC
- `utils/keychain.py`: `store_api_key(service, key)` / `get_api_key(service)` — reuse for new providers
- `ui/settings_dialog.py`: `_create_api_tab()` — extend with new provider key fields

### Established Patterns
- Export functions are pure functions that take transcript dict and return formatted string
- AI providers inherit from ABC and implement 5 methods
- API keys stored via keyring with service prefix `meeting_transcriber.{provider}`
- Settings use deep-merge with defaults for backward compatibility

### Integration Points
- TranscriptViewer in `main_window.py` — add export buttons/menu
- SettingsDialog — extend API Keys tab and add General tab export directory field
- AITaskWorker in `tasks.py` — modify to accept provider instance (currently hardcoded to Gemini)
- `config.py` settings schema — add `ai.default_provider`, `ai.task_overrides`, `export.default_dir`, `export.obsidian_vault`

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Follow existing codebase patterns.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-export-multi-provider*
*Context gathered: 2026-03-27*
