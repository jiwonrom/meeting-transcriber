# Meeting Transcriber

macOS 데스크탑 앱. 실시간 음성 전사 + AI 요약. PyQt6 + whisper.cpp + Gemini API.

## Commands
- `make setup` — 의존성 설치 + whisper 모델 다운로드
- `make test` — pytest 전체 실행
- `make lint` — ruff + mypy
- `make build` — py2app → DMG 생성

## Architecture
- `@docs/architecture.md` 참조
- 의존 방향: ui → core, ui → ai, ai → storage (단방향만 허용)
- core ↛ ui, ai ↛ ui (Signal/Slot으로만 역방향 통신)

## MUST
- PEP8 준수, ruff 자동 포맷
- 모든 public 함수에 type hint + docstring
- 새 기능 추가 시 테스트 필수 (pytest)
- whisper.cpp 추론은 반드시 별도 프로세스에서 실행 (메인 스레드 블로킹 금지)
- API 키는 macOS Keychain 저장 (평문 파일 금지)

## MUST NOT
- ui/ 모듈에서 외부 API 직접 호출 금지
- 메인 스레드에서 blocking I/O 금지
- transcript.json 스키마 임의 변경 금지

## Testing
- `pytest tests/ -x --tb=short`
- `pytest tests/test_transcriber.py -k "test_korean"`
- fixtures/에 4개 언어 샘플 오디오 (각 30초)

## Phase
- 현재: v1.0 MVP
- `@PRD.md`에서 v1.0/v1.5/v2.0 스코프 확인

<!-- GSD:project-start source:PROJECT.md -->
## Project

**Scribe**

macOS 네이티브 데스크탑 앱. 실시간 음성 전사를 오버레이 캡션으로 표시하고, 녹음/파일 임포트를 통해 다국어 transcript를 생성하며, AI 기반 요약·번역·키워드 추출을 제공한다. 모든 데이터는 로컬 우선으로 처리된다. PyQt6 + whisper.cpp + Gemini API 기반.

**Core Value:** 실시간 캡션 — Closed Caption처럼 화면 위에 자막을 표시하여 회의/강의를 실시간으로 전사한다.

### Constraints

- **Tech stack**: PyQt6 + whisper.cpp + Gemini — no framework changes
- **Threading**: All I/O off main thread (QThread or subprocess)
- **Security**: API keys in macOS Keychain only, no plaintext storage
- **Compatibility**: macOS only, Apple Silicon optimized
- **Performance**: Real-time caption ≤ 2s latency after speech
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.11+ - All application code (`src/meeting_transcriber/`)
- C/C++ (external) - whisper.cpp binary, invoked as subprocess
- JSON - Configuration files, design tokens, transcript storage
## Runtime
- Python >= 3.11 (specified in `pyproject.toml` `requires-python`)
- macOS only (uses macOS Keychain via `keyring`, PortAudio via `sounddevice`, `py2app` for bundling)
- Qt6 event loop as main runtime
- pip with setuptools backend
- Build requires: `setuptools>=68.0`, `wheel`
- Lockfile: Not present (no `requirements.txt` lock or `pip-compile` output)
## Frameworks
- PyQt6 >= 6.6 - GUI framework, event loop, threading (`QThread`), signals/slots
- whisper.cpp (external CLI) - Speech-to-text via `whisper-cli` subprocess
- pytest >= 8.0 - Test runner, config in `pyproject.toml` `[tool.pytest.ini_options]`
- pytest-qt >= 4.3 - PyQt6 widget testing
- pytest-cov >= 5.0 - Coverage reporting
- py2app - macOS `.app` bundle generation (`setup.py`)
- create-dmg - DMG packaging (`make dmg`)
- ruff >= 0.5 - Linting and formatting
- mypy >= 1.10 - Static type checking
- pre-commit >= 3.7 - Git hook management
## Key Dependencies
- `PyQt6 >= 6.6` - Entire UI layer, threading model, event loop
- `sounddevice >= 0.4.6` - Real-time microphone audio capture via PortAudio
- `numpy >= 1.26` - Audio buffer manipulation, WAV encoding, RMS level calculation
- `keyring >= 25.0` - macOS Keychain integration for API key storage
- `google-generativeai >= 0.8` - Gemini API client for AI features (summarize, proofread, translate, keywords, title)
- `pyannote.audio >= 3.1` + `torch >= 2.1` - Speaker diarization (optional `[diarization]` extra, not yet used in core)
- `av >= 12.0` - Video file support (optional `[video]` extra, not yet used in core)
- `ruff >= 0.5` - Linter + formatter (line-length 100, target py311, rules: E/F/I/N/W/UP)
- `mypy >= 1.10` - Type checker (disallow_untyped_defs=true)
- `pytest >= 8.0` - Test runner
- `pre-commit >= 3.7` - Pre-commit hooks
## Configuration
- `~/.meeting_transcriber/settings.json` - User preferences (language, model, overlay, audio, theme)
- Settings managed by `src/meeting_transcriber/utils/config.py` with deep-merge defaults
- Default settings defined in `_default_settings()` in `src/meeting_transcriber/utils/config.py`
- `design/tokens_light.json` - Light mode color/typography/spacing tokens
- `design/tokens_dark.json` - Dark mode tokens
- Consumed by `src/meeting_transcriber/ui/theme.py` `ThemeEngine` to generate QSS stylesheets
- `pyproject.toml` - Package metadata, dependencies, tool configs (ruff, mypy, pytest)
- `setup.py` - py2app-specific bundling config (plist, data_files, includes)
- `Makefile` - Development workflow commands
- Ruff config in `pyproject.toml` `[tool.ruff]`: line-length=100, target-version="py311"
- Ruff lint rules: `["E", "F", "I", "N", "W", "UP"]`
- mypy config in `pyproject.toml` `[tool.mypy]`: python_version="3.11", disallow_untyped_defs=true
## External Binary Dependencies
- Required for transcription, NOT bundled - must be installed separately
- Install via: `brew install whisper-cpp`
- Or specify custom path in settings
- Resolution logic in `src/meeting_transcriber/core/transcriber.py` `_resolve_whisper_cli()`
- Stored at `~/.meeting_transcriber/models/`
- Downloaded from HuggingFace: `https://huggingface.co/ggerganov/whisper.cpp/resolve/main/`
- Available models: `small` (ggml-small.bin), `medium` (ggml-medium.bin), `large-v3` (ggml-large-v3.bin)
- Default model: `small` (auto-downloaded during `make setup`)
- Model management in `src/meeting_transcriber/core/model_manager.py`
## Platform Requirements
- macOS (required for Keychain integration and py2app)
- Python 3.11+
- whisper-cpp installed (`brew install whisper-cpp`)
- PortAudio (installed as sounddevice dependency)
- macOS (`.app` bundle via py2app)
- Microphone access permission (`NSMicrophoneUsageDescription` in plist)
- Internet access for Gemini API calls and model downloads
- Bundle ID: `com.meetingtranscriber.app`
## Make Targets
| Command | Purpose |
|---------|---------|
| `make setup` | Install deps + download whisper small model |
| `make test` | Run pytest with `-x --tb=short -v` |
| `make lint` | Run ruff check + format on `src/` and `tests/` |
| `make typecheck` | Run mypy on `src/` |
| `make build` | Build `.app` bundle via py2app |
| `make dmg` | Build `.app` then package into DMG |
| `make clean` | Remove build artifacts |
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- All source files use `snake_case.py`
- Module names match their primary class/concept: `transcriber.py`, `audio_capture.py`, `workspace.py`
- Private helper functions within modules start with `_`: `_parse_whisper_output`, `_resolve_whisper_cli`, `_deep_merge`
- Use `snake_case` for all functions and methods
- Private methods use `_prefix`: `_drain_queue`, `_emit_chunk`, `_audio_callback`
- Signal handlers use `_on_{event}` pattern: `_on_record_btn_clicked`, `_on_capture_started`, `_on_level_changed`
- Qt overrides retain `camelCase` with `# noqa: N802` suppression: `paintEvent`, `closeEvent`
- Use `snake_case` for all variables
- Private instance variables use `_prefix`: `self._running`, `self._buffer`, `self._model_path`
- Use `PascalCase`: `FileTranscriber`, `AudioCaptureWorker`, `WorkspaceManager`
- Dataclasses use `PascalCase`: `TranscriptionResult`, `AudioDeviceInfo`
- Use `UPPER_SNAKE_CASE`: `AUDIO_SAMPLE_RATE`, `DEFAULT_WHISPER_MODEL`, `SUPPORTED_LANGUAGES`
- Defined centrally in `src/meeting_transcriber/utils/constants.py`
- Use `snake_case` with `{verb}_{noun}` pattern: `capture_started`, `chunk_ready`, `level_changed`, `error_occurred`
- Defined as class-level `pyqtSignal()` attributes
## Code Style
- Tool: ruff (configured in `pyproject.toml`)
- Line length: 100 characters
- Target: Python 3.11+
- Tool: ruff
- Rules: `["E", "F", "I", "N", "W", "UP"]` (pycodestyle, pyflakes, isort, pep8-naming, warnings, pyupgrade)
- Config: `pyproject.toml` `[tool.ruff.lint]`
- Tool: mypy (strict mode)
- Config: `pyproject.toml` `[tool.mypy]`
- `disallow_untyped_defs = true` -- all functions require type hints
- `warn_return_any = true`, `warn_unused_configs = true`
## Type Hints
- Every file starts with `from __future__ import annotations`
- All public functions have full type annotations (parameters + return)
- Use `X | None` syntax instead of `Optional[X]` (Python 3.10+ style)
- Use `list[str]`, `dict[str, Any]` lowercase generics (Python 3.9+)
## Import Organization
- No path aliases used. All imports use full dotted paths: `from meeting_transcriber.core.transcriber import FileTranscriber`
- Prefer `from X import Y` for specific items
- Use `import X` for top-level modules (e.g., `import json`, `import pathlib`)
- Group multiple imports from same package with parenthesized multi-line:
## Docstrings
- All public functions, classes, and modules have docstrings
- Module-level docstring is the first line of every `.py` file
- Docstrings are written in Korean
- Include `Args:`, `Returns:`, `Raises:` sections when applicable
- Single-line Korean description: `"""프로젝트 전역 예외 정의."""`
- Reference: `src/meeting_transcriber/utils/exceptions.py`, `src/meeting_transcriber/core/transcriber.py`
## Error Handling
- Base: `MeetingTranscriberError(Exception)` in `src/meeting_transcriber/utils/exceptions.py`
- Domain-specific subclasses:
- Never catch bare `Exception` in core/business logic. Use specific exceptions.
- Chain exceptions with `raise X from e` to preserve tracebacks
- External process failures get wrapped in domain exceptions with user-friendly messages
- Settings load: falls back to defaults on corrupt/missing file (see `src/meeting_transcriber/utils/config.py`)
- Audio device listing: returns empty list on PortAudioError (see `src/meeting_transcriber/core/audio_capture.py`)
- Realtime chunk transcription: silently ignores failures (see `ChunkTranscriberThread.run()` in `src/meeting_transcriber/ui/main_window.py`)
- Core/AI modules never touch UI directly
- Errors propagate via `pyqtSignal(str)`: e.g., `error_occurred = pyqtSignal(str)` in `AudioCaptureWorker`
- MainWindow shows errors in status bar: `self._status_bar.showMessage(f"Error: {message}")`
## Logging
- `pyqtSignal(str)` for error propagation to UI
- Status bar messages for user feedback
- Silent fallbacks for non-critical failures
## Module & File Design
- `ui` -> `core`, `ui` -> `ai`, `ai` -> `storage` (allowed)
- `core` -> `ui`, `ai` -> `ui` (forbidden -- use Signal/Slot only)
- No `__all__` definitions in modules
- `__init__.py` files are empty (no barrel exports)
- Use `@dataclass(frozen=True)` for immutable value objects: `TranscriptionResult`, `AudioDeviceInfo`
- Use `field(default_factory=...)` for mutable defaults
- Use comment blocks with `# ============================================================` (see `src/meeting_transcriber/ui/main_window.py`)
- Section headers describe the class/component that follows
## Comments
- Inline comments for non-obvious logic (e.g., `# QThread.exec() 호출로 이벤트 루프 시작`)
- Section separators for large files
- `# noqa: N802` for Qt method overrides that violate PEP8 naming
- `# noqa: F841` for intentional unused variables (e.g., keeping references alive)
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- 5 modules with enforced dependency direction: `ui -> core`, `ui -> ai`, `ai -> storage`, `ui -> storage`, `ui -> utils`, `core -> utils`, `storage -> utils`
- Reverse communication (core/ai -> ui) exclusively via PyQt6 Signal/Slot mechanism
- Heavy work (transcription, AI calls, audio capture) offloaded to QThread workers and subprocesses
- Provider pattern for AI backends (abstract base class + concrete Gemini implementation)
- Filesystem-based data storage (JSON files, no database)
## Module Dependency Graph
```
```
- `ui -> core` : UI invokes audio capture and transcription
- `ui -> ai` : UI triggers AI processing and displays results
- `ui -> storage` : UI reads/writes transcripts and workspace folders
- `ai -> storage` : AI tasks save results to transcript files (via main_window orchestration)
- `core -> utils` : Core uses constants, config, exceptions
- `storage -> utils` : Storage uses constants, config
- `ai -> utils` : AI uses keychain for API key retrieval
- `core -> ui` : Use Signal/Slot only
- `ai -> ui` : Use Signal/Slot only
- `storage -> ai` : Unidirectional only
## Layers
- Purpose: All PyQt6 widgets, windows, and visual components
- Contains: `MainWindow`, `OverlayWidget`, `SidebarWidget`, `TrayIcon`, `OnboardingWizard`, `SettingsDialog`, `ThemeEngine`, `TranscriptViewer`
- Depends on: `core`, `ai`, `storage`, `utils`
- Used by: `app.py` (entry point wiring)
- Key pattern: Widgets emit signals; `app.py` connects them
- Purpose: Audio capture, whisper.cpp transcription, file import, model management
- Contains: `AudioCaptureWorker` (QThread), `FileTranscriber` (subprocess wrapper), `ModelManager`, `FileImporter`
- Depends on: `utils` (constants, exceptions, config)
- Used by: `ui` (MainWindow creates workers)
- Key pattern: Workers emit signals on completion; never reference UI directly
- Purpose: AI provider abstraction and task orchestration
- Contains: `AIProvider` (ABC), `GeminiProvider`, `AITaskWorker` (QThread)
- Depends on: `utils` (keychain for API keys)
- Used by: `ui` (MainWindow._run_ai_tasks)
- Key pattern: Provider pattern with abstract base; worker emits `progress` and `finished` signals
- Purpose: Filesystem-based transcript CRUD, workspace folder management, export
- Contains: `TranscriptStore` (create/save/load), `WorkspaceManager` (folder CRUD), `Exporter` (Markdown/TXT)
- Depends on: `utils` (constants, config)
- Used by: `ui`, `ai` (indirectly via MainWindow orchestration)
- Key pattern: Pure functions for transcript operations; class-based for workspace management
- Purpose: Cross-cutting concerns -- config, constants, keychain, shortcuts, exceptions
- Contains: `config.py`, `constants.py`, `keychain.py`, `shortcuts.py`, `exceptions.py`
- Depends on: Nothing internal (leaf module)
- Used by: All other modules
## Data Flow
- Recording state: `MainWindow._is_recording` boolean, propagated via signals to `RecordButton`, `OverlayWidget`, `TrayIcon`
- Settings: `~/.meeting_transcriber/settings.json` loaded via `load_settings()`, deep-merged with defaults
- Transcript data: Individual `transcript.json` files per recording in workspace folders
- API keys: macOS Keychain via `keyring` library (never stored in files)
## Key Abstractions
- Purpose: Pluggable AI backend interface
- Definition: `src/meeting_transcriber/ai/provider_base.py`
- Concrete: `src/meeting_transcriber/ai/gemini_provider.py` (`GeminiProvider`)
- Methods: `summarize()`, `proofread()`, `translate()`, `extract_keywords()`, `generate_title()`
- Pattern: Strategy pattern -- swap providers without changing orchestration logic
- Purpose: Immutable container for whisper-cli output
- Definition: `src/meeting_transcriber/core/transcriber.py`
- Fields: `segments`, `language`, `model`, `duration_seconds`, `raw_output`
- Pattern: Frozen dataclass passed between threads via signals
- Purpose: Container for all AI processing outputs
- Definition: `src/meeting_transcriber/ai/tasks.py`
- Fields: `summary`, `proofread_text`, `keywords`, `title`, `translation`, `errors`
- Purpose: Generates PyQt6 QSS stylesheets from design token JSON files
- Definition: `src/meeting_transcriber/ui/theme.py`
- Pattern: Token-driven theming -- reads `design/tokens_dark.json` or `design/tokens_light.json`, generates complete QSS
- Purpose: Manages filesystem-based workspace (folders and transcript discovery)
- Definition: `src/meeting_transcriber/storage/workspace.py`
- Pattern: Wraps `~/.meeting_transcriber/` directory with CRUD operations
## Entry Points
- Function: `main()`
- Triggers: `python -m meeting_transcriber` or direct execution
- Responsibilities:
- `tray.recording_toggled` -> `window.toggle_recording`
- `tray.show_window_requested` -> `window.show` + `window.raise_`
- `tray.overlay_toggle_requested` -> `overlay.toggle_visibility`
- `tray.quit_requested` -> `app.quit`
- `window.caption_updated` -> `overlay.append_caption`
- `window.recording_started` -> `overlay.clear_caption` + `overlay.set_recording(True)`
- `window.recording_stopped` -> `overlay.set_recording(False)`
## Threading Model
| Thread | Implementation | Location | Responsibility |
|--------|---------------|----------|----------------|
| Main Thread | PyQt6 event loop | `app.py` `main()` | UI rendering, signal dispatch. **No blocking I/O.** |
| Audio Capture | `QThread` + `QTimer` | `core/audio_capture.py` `AudioCaptureWorker` | sounddevice InputStream, 2s chunk buffering, VAD |
| Chunk Transcription | `QThread` (multiple, max 2) | `ui/main_window.py` `ChunkTranscriberThread` | Real-time whisper-cli subprocess per 2s chunk |
| Full Transcription | `QThread` | `ui/main_window.py` `TranscriptionWorkerThread` | Post-recording whisper-cli subprocess |
| AI Tasks | `QThread` | `ai/tasks.py` `AITaskWorker` | Sequential Gemini API calls |
| Model Download | `QThread` | `ui/onboarding.py` `ModelDownloadThread` | HuggingFace model download |
- PortAudio callback -> `queue.Queue` (lock-free put) -> QTimer drain (main-thread-safe)
- All worker results communicated via `pyqtSignal` (thread-safe by Qt design)
- `AudioCaptureWorker.get_full_recording()` copies chunk list for thread safety
## Error Handling
- `MeetingTranscriberError` (base)
- Worker threads catch all exceptions, emit via signals (never crash silently)
- `AudioCaptureWorker` distinguishes permission errors from device errors in PortAudio exceptions
- Real-time chunk transcription failures are silently ignored (final transcription recovers)
- AI task failures are collected in `AIResult.errors` list, non-fatal to the overall flow
- UI displays errors in status bar (`QStatusBar.showMessage()`)
## Cross-Cutting Concerns
- Audio file format validation in `src/meeting_transcriber/core/file_importer.py` (suffix check against `SUPPORTED_AUDIO_FORMATS`)
- Folder name validation in `src/meeting_transcriber/storage/workspace.py` (empty, path separators, dots, reserved names)
- Model name validation in `src/meeting_transcriber/core/model_manager.py` (against `WHISPER_MODELS` dict)
- API keys stored in macOS Keychain via `keyring` library (`src/meeting_transcriber/utils/keychain.py`)
- Service prefix: `meeting_transcriber.<service>` (e.g., `meeting_transcriber.gemini`)
- Keys never stored in files or settings.json
- `~/.meeting_transcriber/settings.json` for app preferences
- Deep-merge with defaults ensures forward compatibility
- Constants centralized in `src/meeting_transcriber/utils/constants.py`
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
