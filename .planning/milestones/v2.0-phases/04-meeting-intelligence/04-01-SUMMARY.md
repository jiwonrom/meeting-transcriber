---
phase: 04-meeting-intelligence
plan: 01
subsystem: ai
tags: [yaml, templates, structured-summary, json-mode, pyyaml]

# Dependency graph
requires:
  - phase: 01-export-byok
    provides: "AIProvider ABC, FallbackProvider, AITaskWorker, exporters"
provides:
  - "TemplateManager with 5 built-in YAML meeting templates"
  - "MeetingTemplate frozen dataclass with section_keys/is_structured"
  - "template_prompt parameter on all AI providers (Gemini JSON mode, OpenAI json_object, Anthropic prompt-based)"
  - "AITaskWorker template_prompt forwarding"
  - "_format_summary_for_export() for dict/str summary backward compatibility"
affects: [04-meeting-intelligence, ui-template-selector]

# Tech tracking
tech-stack:
  added: [PyYAML]
  patterns: [YAML template loading via importlib.resources, provider JSON mode per-vendor]

key-files:
  created:
    - src/meeting_transcriber/ai/templates.py
    - src/meeting_transcriber/ai/builtin_templates/__init__.py
    - src/meeting_transcriber/ai/builtin_templates/general.yaml
    - src/meeting_transcriber/ai/builtin_templates/team_meeting.yaml
    - src/meeting_transcriber/ai/builtin_templates/one_on_one.yaml
    - src/meeting_transcriber/ai/builtin_templates/lecture.yaml
    - src/meeting_transcriber/ai/builtin_templates/interview.yaml
    - tests/test_templates.py
  modified:
    - pyproject.toml
    - src/meeting_transcriber/utils/constants.py
    - src/meeting_transcriber/ai/provider_base.py
    - src/meeting_transcriber/ai/gemini_provider.py
    - src/meeting_transcriber/ai/openai_provider.py
    - src/meeting_transcriber/ai/anthropic_provider.py
    - src/meeting_transcriber/ai/provider_manager.py
    - src/meeting_transcriber/ai/tasks.py
    - src/meeting_transcriber/storage/exporter.py
    - tests/test_ai_provider.py
    - tests/test_exporter.py

key-decisions:
  - "importlib.resources for bundled YAML access -- portable across installed/editable modes"
  - "Gemini response_mime_type, OpenAI json_object, Anthropic prompt-only for JSON mode -- vendor-appropriate approaches"
  - "General template is non-structured (plain bullet summary) maintaining backward compatibility"

patterns-established:
  - "YAML template loading: importlib.resources -> ensure_templates copies to user dir -> load_all globs"
  - "Template prompt rendering: {speaker_instruction} and {language_instruction} placeholders"
  - "Provider JSON mode: template_prompt triggers vendor-specific JSON response configuration"

requirements-completed: [TPL-01, TPL-02, TPL-03]

# Metrics
duration: 5min
completed: 2026-03-28
---

# Phase 04 Plan 01: Template System Summary

**TemplateManager with 5 built-in YAML templates and template-aware AI provider pipeline with per-vendor JSON mode**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-28T03:28:30Z
- **Completed:** 2026-03-28T03:33:32Z
- **Tasks:** 2
- **Files modified:** 19

## Accomplishments
- TemplateManager loads 5 built-in YAML templates (General, Team Meeting, 1:1, Lecture, Interview) with custom template support
- All 3 AI providers + FallbackProvider extended with template_prompt parameter and vendor-specific JSON mode
- Exporters handle both str and dict summary fields with backward compatibility
- 22 new tests added, full suite of 325 tests passing

## Task Commits

Each task was committed atomically:

1. **Task 1: TemplateManager, MeetingTemplate, built-in YAML templates** - `c147fb1` (feat)
2. **Task 2: Extend AI providers with template_prompt + exporters** - `1bb72a5` (feat)

## Files Created/Modified
- `src/meeting_transcriber/ai/templates.py` - TemplateManager and MeetingTemplate dataclass
- `src/meeting_transcriber/ai/builtin_templates/*.yaml` - 5 built-in YAML meeting templates
- `src/meeting_transcriber/ai/provider_base.py` - template_prompt on AIProvider.summarize() ABC
- `src/meeting_transcriber/ai/gemini_provider.py` - JSON mode via response_mime_type
- `src/meeting_transcriber/ai/openai_provider.py` - JSON mode via response_format json_object
- `src/meeting_transcriber/ai/anthropic_provider.py` - Prompt-based JSON instruction
- `src/meeting_transcriber/ai/provider_manager.py` - FallbackProvider template_prompt forwarding
- `src/meeting_transcriber/ai/tasks.py` - AITaskWorker template_prompt parameter
- `src/meeting_transcriber/storage/exporter.py` - _format_summary_for_export() dict/str handler
- `pyproject.toml` - PyYAML>=6.0 runtime dependency
- `src/meeting_transcriber/utils/constants.py` - TEMPLATES_DIR, BUILTIN_TEMPLATE_NAMES, DEFAULT_TEMPLATE

## Decisions Made
- Used importlib.resources for bundled YAML access -- portable across installed and editable modes
- Gemini uses response_mime_type, OpenAI uses json_object format, Anthropic relies on prompt instructions -- vendor-appropriate JSON approaches
- General template uses non-structured plain bullet summary to maintain backward compatibility with existing behavior

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Known Stubs

None - all template data is real YAML content, all providers are wired to actual API calls.

## Next Phase Readiness
- Template infrastructure ready for UI template selector (04-02/04-03)
- TemplateManager.render_prompt() ready for integration with MainWindow
- Exporter dict summary handling ready for structured AI results

---
*Phase: 04-meeting-intelligence*
*Completed: 2026-03-28*
