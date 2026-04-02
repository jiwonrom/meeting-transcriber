---
phase: 08-per-task-provider-override
plan: 01
subsystem: ai
tags: [provider-override, per-task, fallback, BYOK]
dependency_graph:
  requires: [provider_manager, FallbackProvider]
  provides: [per-task-provider-resolution]
  affects: [ai-tasks, main-window-ai-calls]
tech_stack:
  added: []
  patterns: [per-task-provider-resolution, lazy-import-FallbackProvider]
key_files:
  created: []
  modified:
    - src/meeting_transcriber/ai/tasks.py
    - src/meeting_transcriber/ui/main_window.py
    - tests/test_ai_provider.py
decisions:
  - AITaskWorker accepts provider_manager + settings instead of single AIProvider
  - Each task resolves its own FallbackProvider via _get_provider() helper
  - Lazy import FallbackProvider inside _get_provider() to avoid circular imports
  - Worker collects fallback_messages from all per-task providers
metrics:
  duration: 4min
  completed: 2026-04-02T13:56:12Z
  tasks: 2
  files: 3
---

# Phase 08 Plan 01: Per-Task Provider Override Summary

AITaskWorker resolves separate FallbackProvider per AI task (proofread, summarize, keywords, title) via ProviderManager.get_provider_for_task(), enabling user-configured per-task provider overrides from ai.task_overrides settings.

## Tasks Completed

### Task 1: AITaskWorker signature change + per-task provider resolution + tests (TDD)
- **Commit:** f276346
- Changed AITaskWorker.__init__ to accept `provider_manager: ProviderManager` and `settings: dict` instead of `provider: AIProvider`
- Added `_get_provider(task)` helper that creates per-task FallbackProvider
- Updated `run()` to resolve per-task provider for each AI operation
- Added `self.fallback_messages` list that collects messages from all per-task providers
- Updated 6 existing AITaskWorker tests to use MockProviderManager
- Added 3 new tests: test_per_task_override, test_per_task_fallback, test_per_task_empty_chain
- All 40 tests in test_ai_provider.py pass

### Task 2: Update main_window.py call sites
- **Commit:** 9a39f35
- Call site 1 (_run_ai_tasks): passes provider_manager+settings to AITaskWorker, removed FallbackProvider import, passes self._ai_worker to _on_ai_done_with_fallback
- Call site 2 (re-run AI): uses get_provider_for_task("summarize", settings) instead of get_provider_chain
- Call site 3 (cross-meeting analysis): uses get_provider_for_task("analyze", settings)
- All 371 tests pass

## Deviations from Plan

None -- plan executed exactly as written.

## Verification Results

- `pytest tests/test_ai_provider.py -x --tb=short -v`: 40 passed
- `pytest tests/ -x --tb=short -v`: 371 passed
- `grep -c "get_provider_for_task" src/meeting_transcriber/ai/tasks.py`: 1
- `grep -c "get_provider_for_task" src/meeting_transcriber/ui/main_window.py`: 2
- `grep -c "provider_manager=manager" src/meeting_transcriber/ui/main_window.py`: 1

## Known Stubs

None.
