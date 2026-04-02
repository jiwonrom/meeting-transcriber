# Phase 8: Per-Task AI Provider Override - Research

**Researched:** 2026-04-02
**Domain:** AI provider routing / PyQt6 QThread wiring
**Confidence:** HIGH

## Summary

This phase is a deterministic wiring fix. The infrastructure for per-task provider overrides (`ProviderManager.get_provider_for_task()`, `ai.task_overrides` settings key, `FallbackProvider` adapter) is fully implemented from Phase 1. The gap is that all three AI call sites in `main_window.py` use `get_provider_chain()` (global default) instead of `get_provider_for_task()` (per-task override). The fix requires changing `AITaskWorker` to accept `ProviderManager` + `settings` instead of a single `AIProvider`, then resolving a per-task `FallbackProvider` inside `AITaskWorker.run()` for each task.

The cross-meeting analysis call site uses a separate `CrossMeetingAnalysisWorker` which also takes a single `AIProvider`. This call site needs similar treatment, but since it runs a single task (`analyze_cross_meeting`), it can resolve one `FallbackProvider` at the call site using `get_provider_for_task("analyze", settings)`.

**Primary recommendation:** Modify `AITaskWorker.__init__` to accept `ProviderManager` + `settings`, resolve per-task `FallbackProvider` chains inside `run()`, and update all three call sites in `main_window.py`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Create a separate FallbackProvider for each task inside `AITaskWorker.run()`. Pass `ProviderManager` + `settings` to `AITaskWorker` instead of a single `provider`. Each task (proofread, summarize, keywords, title) gets its own chain from `get_provider_for_task(task_name, settings)`.
- **D-02:** `AITaskWorker.__init__` signature changes: remove `provider: AIProvider` parameter, add `provider_manager: ProviderManager` and `settings: dict[str, Any]` parameters.
- **D-03:** Inside `AITaskWorker.run()`, resolve chain per task: `chain = self._manager.get_provider_for_task("summarize", self._settings)` -> `FallbackProvider(self._manager, chain)` for each task call.
- **D-04:** For re-run AI call site (line ~1395), use `get_provider_for_task("summarize", settings)` since it only runs summarize.
- **D-05:** For cross-meeting analysis call site (line ~1644), use `get_provider_for_task("analyze", settings)` -- if no "analyze" override exists, `get_provider_for_task` falls back to `get_provider_chain()`.
- **D-06:** `_run_ai_tasks` call site (line ~1272) passes `ProviderManager` and `settings` to `AITaskWorker` instead of creating a single FallbackProvider.

### Claude's Discretion
- Whether to create a helper method in AITaskWorker for resolving per-task FallbackProvider
- How to handle the "analyze" task name for cross-meeting analysis (new task name or reuse "summarize")
- Test structure for verifying per-task override behavior

### Deferred Ideas (OUT OF SCOPE)
None
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BYOK-03 | User can select which AI provider to use for each task (summarize, proofread, translate) | `get_provider_for_task()` already implemented; wiring fix to use it at all 3 call sites + AITaskWorker signature change |
</phase_requirements>

## Standard Stack

No new libraries needed. This phase modifies existing code only.

### Core (already in project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyQt6 | >= 6.6 | QThread workers, signals | Already used for AITaskWorker |
| pytest | >= 8.0 | Testing | Already configured |
| pytest-qt | >= 4.3 | QThread testing with qtbot | Already configured |

## Architecture Patterns

### Current Pattern (BEFORE -- to be changed)
```
main_window.py call site:
  chain = manager.get_provider_chain(settings)  # global default only
  provider = FallbackProvider(manager, chain)    # one provider for all tasks
  worker = AITaskWorker(provider=provider, ...)  # passed as single AIProvider
```

### Target Pattern (AFTER)
```
main_window.py call site:
  worker = AITaskWorker(
      provider_manager=manager,
      settings=settings,
      text=full_text, ...
  )

AITaskWorker.run():
  # Each task resolves its own chain
  chain = self._manager.get_provider_for_task("proofread", self._settings)
  provider = FallbackProvider(self._manager, chain)
  result.proofread_text = provider.proofread(...)
  
  chain = self._manager.get_provider_for_task("summarize", self._settings)
  provider = FallbackProvider(self._manager, chain)
  result.summary = provider.summarize(...)
  # ... etc
```

### Recommended: Helper Method in AITaskWorker
```python
def _get_provider(self, task: str) -> FallbackProvider:
    """Resolve per-task FallbackProvider."""
    from meeting_transcriber.ai.provider_manager import FallbackProvider
    chain = self._manager.get_provider_for_task(task, self._settings)
    return FallbackProvider(self._manager, chain)
```
This reduces repetition in `run()` and keeps fallback message collection per-task.

### Task Name Mapping
The four tasks in AITaskWorker map to these task names for `get_provider_for_task()`:
| AITaskWorker Task | Task Name String | Notes |
|-------------------|-----------------|-------|
| proofread | `"proofread"` | Direct match |
| summarize | `"summarize"` | Direct match |
| extract_keywords | `"keywords"` | Shortened per BYOK-03 UI convention |
| generate_title | `"title"` | Shortened |
| analyze_cross_meeting | `"analyze"` | New task name for D-05; falls back to default chain |

### Anti-Patterns to Avoid
- **Single FallbackProvider for all tasks:** This is the current bug -- defeats the purpose of per-task overrides.
- **Accumulating fallback_messages across tasks:** Each task should use its own FallbackProvider instance so fallback messages are per-task, not mixed.

## Affected Files Summary

| File | Change | Complexity |
|------|--------|------------|
| `src/meeting_transcriber/ai/tasks.py` | `AITaskWorker.__init__` signature change; `run()` resolves per-task provider | Medium |
| `src/meeting_transcriber/ui/main_window.py` | 3 call sites updated to pass `ProviderManager` + `settings` | Low |
| `tests/test_ai_provider.py` | Existing AITaskWorker tests updated; new per-task override tests | Medium |

### Call Site Details

**Call Site 1: `_run_ai_tasks` (line ~1263)**
- Currently creates one `FallbackProvider` from `get_provider_chain()`
- Change: Pass `manager` and `settings` to `AITaskWorker`
- Remove: `chain = manager.get_provider_chain(settings)` and `provider = FallbackProvider(manager, chain)`
- The `_on_ai_done_with_fallback` handler checks `provider.fallback_messages` -- this needs adjustment since there is no longer a single provider. Options: collect fallback messages from AITaskWorker itself, or simplify to just call `_on_ai_done`.

**Call Site 2: Re-run AI (line ~1370)**
- Only runs `summarize` task (`do_summarize=True`, all others `False`)
- Two options: (a) use same AITaskWorker pattern with manager+settings, or (b) resolve single FallbackProvider at call site using `get_provider_for_task("summarize", settings)` since only one task runs.
- Recommendation: Option (b) is simpler -- this call site only ever runs summarize, so resolving once at the call site is sufficient and matches D-04.

**Call Site 3: Cross-meeting analysis (line ~1638)**
- Uses `CrossMeetingAnalysisWorker` (separate class, not AITaskWorker)
- Takes single `provider: AIProvider` parameter
- Change: Resolve FallbackProvider at call site using `get_provider_for_task("analyze", settings)` per D-05
- `CrossMeetingAnalysisWorker` signature does NOT need changing (single task worker)

### Fallback Message Handling

Current pattern: `_on_ai_done_with_fallback` receives the single `FallbackProvider` and reads `provider.fallback_messages`. With per-task providers inside `AITaskWorker.run()`, options are:

1. **Collect in AITaskWorker:** Add `self.fallback_messages: list[str] = []` to AITaskWorker, append from each per-task FallbackProvider after each task completes. Return via the worker instance.
2. **Simplify:** Since fallback messages are informational only (status bar display), include them in `AIResult.errors` with a distinct prefix like `"[fallback] ..."`.
3. **Drop for now:** Fallback messages are low-priority UI feedback.

Recommendation: Option 1 -- collect on the worker, minimal change to `_on_ai_done_with_fallback` callback (read from worker instead of provider).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Per-task provider resolution | Custom logic in main_window | `ProviderManager.get_provider_for_task()` | Already implemented, handles fallback to default chain |
| Provider chain fallback | Try/except loops at call sites | `FallbackProvider` adapter | Wraps chain transparently |

## Common Pitfalls

### Pitfall 1: Empty Chain from get_provider_for_task
**What goes wrong:** If no API keys are configured for the overridden provider, `get_provider_for_task` returns an empty chain.
**Why it happens:** User sets `task_overrides.summarize = "anthropic"` but has no Anthropic API key.
**How to avoid:** Check `if not chain` before creating FallbackProvider. The current `_run_ai_tasks` already has this guard for the global chain -- similar guards needed per-task.
**Warning signs:** AITaskWorker silently skips tasks or raises RuntimeError.

### Pitfall 2: Existing Test Breakage
**What goes wrong:** All existing AITaskWorker tests pass `provider=MockProvider()` -- this parameter is being removed.
**Why it happens:** Signature change from D-02.
**How to avoid:** Update all 6 existing test functions that construct AITaskWorker. New signature requires `provider_manager` and `settings` mocks.
**Warning signs:** `TypeError: __init__() got an unexpected keyword argument 'provider'`

### Pitfall 3: Import Location for FallbackProvider in tasks.py
**What goes wrong:** Circular import if FallbackProvider is imported at module level in tasks.py.
**Why it happens:** `tasks.py` -> `provider_manager.py` -> `provider_base.py`, and `tasks.py` already imports from `provider_base.py`.
**How to avoid:** Use lazy import inside `_get_provider()` helper method, consistent with the project's established pattern (D-03 in CONTEXT.md references this).
**Warning signs:** `ImportError` on module load.

### Pitfall 4: Fallback Message Collection Across Tasks
**What goes wrong:** If using a single FallbackProvider for all tasks, fallback messages from early tasks bleed into later task reporting.
**Why it happens:** FallbackProvider accumulates messages in a list across all method calls.
**How to avoid:** Create a fresh FallbackProvider per task (per D-01/D-03).

## Code Examples

### AITaskWorker Signature Change (D-02)
```python
class AITaskWorker(QThread):
    def __init__(
        self,
        provider_manager: ProviderManager,
        settings: dict[str, Any],
        text: str,
        *,
        language: str = "auto",
        do_proofread: bool = True,
        do_summarize: bool = True,
        do_keywords: bool = True,
        do_title: bool = True,
        template_prompt: str | None = None,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._manager = provider_manager
        self._settings = settings
        self._text = text
        # ... rest unchanged
        self.fallback_messages: list[str] = []
```

### Per-Task Resolution in run() (D-03)
```python
def _get_provider(self, task: str) -> FallbackProvider:
    """태스크별 FallbackProvider를 생성한다."""
    from meeting_transcriber.ai.provider_manager import FallbackProvider
    chain = self._manager.get_provider_for_task(task, self._settings)
    if not chain:
        raise RuntimeError(f"No providers available for task: {task}")
    return FallbackProvider(self._manager, chain)

def run(self) -> None:
    result = AIResult()

    if self._do_proofread:
        try:
            self.progress.emit("Proofreading...")
            provider = self._get_provider("proofread")
            result.proofread_text = provider.proofread(
                self._text, language=self._language
            )
            self.fallback_messages.extend(provider.fallback_messages)
        except Exception as e:
            result.errors.append(f"Proofread failed: {e}")
    # ... similar for summarize, keywords, title
```

### Call Site 1 Update (_run_ai_tasks, D-06)
```python
def _run_ai_tasks(self, result, transcript_path):
    from meeting_transcriber.ai.provider_manager import ProviderManager
    from meeting_transcriber.ai.tasks import AITaskWorker

    settings = load_settings()
    manager = ProviderManager()

    # No longer create chain/FallbackProvider here
    full_text = " ".join(s.get("text", "") for s in result.segments)
    if not full_text.strip():
        return

    # ... template handling unchanged ...

    self._ai_worker = AITaskWorker(
        provider_manager=manager,
        settings=settings,
        text=full_text,
        language=result.language,
        template_prompt=template_prompt,
    )
    self._ai_worker.progress.connect(lambda msg: self._status_bar.showMessage(msg))
    self._ai_worker.finished.connect(
        lambda ai_result: self._on_ai_done_with_fallback(
            ai_result, transcript_path, self._ai_worker
        )
    )
    self._ai_worker.start()
```

### Call Site 3 Update (cross-meeting, D-05)
```python
# Resolve at call site -- single task, no need to change CrossMeetingAnalysisWorker
chain = manager.get_provider_for_task("analyze", settings)
if not chain:
    self._status_bar.showMessage("No API keys configured")
    return
provider = FallbackProvider(manager, chain)

self._analysis_worker = CrossMeetingAnalysisWorker(
    provider=provider, ...
)
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 8.0 + pytest-qt >= 4.3 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_ai_provider.py -x --tb=short` |
| Full suite command | `pytest tests/ -x --tb=short -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BYOK-03-a | AITaskWorker accepts manager+settings, resolves per-task provider | unit | `pytest tests/test_ai_provider.py -k "test_ai_task_worker" -x` | Exists but needs update |
| BYOK-03-b | Per-task override uses different provider than default | unit | `pytest tests/test_ai_provider.py -k "test_per_task_override" -x` | New test needed |
| BYOK-03-c | Tasks without overrides fall back to default provider chain | unit | `pytest tests/test_ai_provider.py -k "test_per_task_fallback" -x` | New test needed |
| BYOK-03-d | Empty chain for overridden task is handled gracefully | unit | `pytest tests/test_ai_provider.py -k "test_per_task_empty_chain" -x` | New test needed |

### Sampling Rate
- **Per task commit:** `pytest tests/test_ai_provider.py -x --tb=short`
- **Per wave merge:** `pytest tests/ -x --tb=short -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] Update 6 existing `AITaskWorker` tests to use new `provider_manager`/`settings` signature
- [ ] Add test: per-task override resolves different provider per task
- [ ] Add test: no override falls back to default chain
- [ ] Add test: empty chain for overridden task produces error in AIResult

### Existing Tests Requiring Signature Updates
| Test Function | File | Change Needed |
|--------------|------|---------------|
| `test_ai_task_worker_all_tasks` | `tests/test_ai_provider.py:94` | `provider=` -> `provider_manager=` + `settings=` |
| `test_ai_task_worker_selective` | `tests/test_ai_provider.py:120` | Same |
| `test_ai_task_worker_error_handling` | `tests/test_ai_provider.py:~140` | Same |
| `test_ai_task_worker_progress_signals` | `tests/test_ai_provider.py:166` | Same |
| `test_ai_task_worker_template_prompt` | `tests/test_ai_provider.py:540` | Same |
| `test_ai_task_worker_no_template` | `tests/test_ai_provider.py:567` | Same |

For test mocking, the simplest approach: create a mock `ProviderManager` whose `get_provider_for_task()` always returns `[MockProvider()]`. This preserves existing test behavior while exercising the new code path.

## Open Questions

1. **Fallback message reporting with per-task providers**
   - What we know: Current `_on_ai_done_with_fallback` reads `provider.fallback_messages` from a single FallbackProvider
   - What's unclear: Exact format for per-task fallback messages in status bar
   - Recommendation: Collect on AITaskWorker, format as `"summarize: GeminiProvider failed, using OpenAIProvider; keywords: ..."`. Read from `self._ai_worker.fallback_messages` in callback.

2. **"analyze" task name recognition**
   - What we know: `get_provider_for_task("analyze", settings)` will fall back to `get_provider_chain()` if `task_overrides` has no `"analyze"` key
   - What's unclear: Whether to document `"analyze"` as a valid task override key for users
   - Recommendation: Use `"analyze"` as the task name. It naturally falls back to default. Document later if settings UI is added.

## Sources

### Primary (HIGH confidence)
- `src/meeting_transcriber/ai/provider_manager.py` -- ProviderManager and FallbackProvider implementation, verified `get_provider_for_task()` logic
- `src/meeting_transcriber/ai/tasks.py` -- AITaskWorker current implementation and signature
- `src/meeting_transcriber/ui/main_window.py` -- All 3 call sites verified at lines ~1272, ~1395, ~1644
- `src/meeting_transcriber/utils/config.py` -- `ai.task_overrides: {}` default confirmed
- `tests/test_ai_provider.py` -- 6 AITaskWorker tests and FallbackProvider tests identified

### Secondary (MEDIUM confidence)
- `.planning/v2.0-MILESTONE-AUDIT.md` -- Documents BYOK-03 partial status (referenced, not re-read)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, pure wiring change
- Architecture: HIGH -- all affected code read and verified, decisions are explicit
- Pitfalls: HIGH -- identified from direct code analysis (empty chains, test breakage, import cycles)

**Research date:** 2026-04-02
**Valid until:** 2026-05-02 (stable -- internal wiring change, no external dependencies)
