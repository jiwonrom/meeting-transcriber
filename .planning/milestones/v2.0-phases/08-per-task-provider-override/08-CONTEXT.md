# Phase 8: Per-Task AI Provider Override - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase wires `get_provider_for_task()` into all AI call sites so user's per-task provider overrides from `ai.task_overrides` settings are applied at runtime. Three call sites need fixing: `_run_ai_tasks`, re-run AI, and cross-meeting analysis. No new UI, no new settings — the settings infrastructure (`ai.task_overrides`) already exists from Phase 1.

</domain>

<decisions>
## Implementation Decisions

### Per-Task Provider Resolution
- **D-01:** Create a separate FallbackProvider for each task inside `AITaskWorker.run()`. Pass `ProviderManager` + `settings` to `AITaskWorker` instead of a single `provider`. Each task (proofread, summarize, keywords, title) gets its own chain from `get_provider_for_task(task_name, settings)`.
- **D-02:** `AITaskWorker.__init__` signature changes: remove `provider: AIProvider` parameter, add `provider_manager: ProviderManager` and `settings: dict[str, Any]` parameters.
- **D-03:** Inside `AITaskWorker.run()`, resolve chain per task: `chain = self._manager.get_provider_for_task("summarize", self._settings)` → `FallbackProvider(self._manager, chain)` for each task call.
- **D-04:** For re-run AI call site (line ~1395), use `get_provider_for_task("summarize", settings)` since it only runs summarize.
- **D-05:** For cross-meeting analysis call site (line ~1644), use `get_provider_for_task("analyze", settings)` — if no "analyze" override exists, `get_provider_for_task` falls back to `get_provider_chain()`.
- **D-06:** `_run_ai_tasks` call site (line ~1272) passes `ProviderManager` and `settings` to `AITaskWorker` instead of creating a single FallbackProvider.

### Claude's Discretion
- Whether to create a helper method in AITaskWorker for resolving per-task FallbackProvider
- How to handle the "analyze" task name for cross-meeting analysis (new task name or reuse "summarize")
- Test structure for verifying per-task override behavior

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Provider System
- `src/meeting_transcriber/ai/provider_manager.py` — `ProviderManager` with `get_provider_chain()` and `get_provider_for_task()`. `FallbackProvider` class wraps a chain.
- `src/meeting_transcriber/ai/tasks.py` — `AITaskWorker` QThread that runs proofread/summarize/keywords/title sequentially
- `src/meeting_transcriber/ai/provider_base.py` — `AIProvider` ABC with method signatures

### Call Sites to Fix
- `src/meeting_transcriber/ui/main_window.py` line ~1272 — `_run_ai_tasks` uses `get_provider_chain(settings)`
- `src/meeting_transcriber/ui/main_window.py` line ~1395 — re-run AI uses `get_provider_chain(settings)`
- `src/meeting_transcriber/ui/main_window.py` line ~1644 — cross-meeting analysis uses `get_provider_chain(settings)`

### Config
- `src/meeting_transcriber/utils/config.py` — `_default_settings()` has `ai.task_overrides: {}` key

### Audit Evidence
- `.planning/v2.0-MILESTONE-AUDIT.md` — Documents BYOK-03 partial status and the specific wiring gap

### Requirements
- `.planning/REQUIREMENTS.md` — BYOK-03

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ProviderManager.get_provider_for_task(task, settings)`: Fully implemented. Reads `ai.task_overrides`, falls back to `get_provider_chain()` if no override for that task.
- `FallbackProvider(manager, chain)`: Wraps a chain of providers. Each method tries providers in order until one succeeds.
- `AITaskWorker`: QThread with sequential task execution. Currently takes a single `AIProvider`.

### Established Patterns
- **Lazy import**: ProviderManager and FallbackProvider are imported inside methods, not at module level.
- **FallbackProvider adapter**: Phase 1 decision — passed as single AIProvider to AITaskWorker for transparent fallback.
- **Settings passed to provider resolution**: `load_settings()` called at each call site, settings dict passed to ProviderManager methods.

### Integration Points
- `AITaskWorker.__init__` signature change affects: `_run_ai_tasks`, re-run AI handler, and any tests that construct AITaskWorker.
- `FallbackProvider` creation moves from call sites into `AITaskWorker.run()`.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — this is a deterministic wiring fix with a clear solution from the audit report.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 08-per-task-provider-override*
*Context gathered: 2026-04-02*
