# Phase 4: Meeting Intelligence - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase adds two capabilities: (1) meeting templates that adapt AI summary output to the meeting type (Team Meeting, 1:1, Lecture, Interview, General), with user-customizable templates via YAML files; and (2) automatic meeting detection that monitors for active conferencing apps (Zoom, Teams, Meet, FaceTime) combined with audio activity heuristics, prompting users to start recording via macOS notifications. Templates leverage Phase 3 speaker labels to attribute actions to specific speakers.

</domain>

<decisions>
## Implementation Decisions

### Template Selection UX
- **D-01:** Template is selectable both before recording (dropdown next to Record button) and changeable after recording (via "Re-run AI" button with template picker)
- **D-02:** Dropdown/combo box next to the Record button in MainWindow for template selection before recording. Compact, always visible.
- **D-03:** 5 built-in templates: General (default, matches current behavior), Team Meeting, 1:1, Lecture, Interview
- **D-04:** After recording, user can change template and hit "Re-run AI" to regenerate summary with new template. Non-destructive — keeps original results until replaced.

### AI Prompt Adaptation
- **D-05:** Each template defines template-specific summary sections. Team Meeting: Decisions + Action Items + Next Steps. 1:1: Discussion Points + Agreements + Follow-ups. Lecture: Key Concepts + Q&A + Takeaways. Interview: Candidate Responses + Assessment + Notes. General: current behavior (free-form summary).
- **D-06:** When diarization data exists, AI attributes action items/decisions to specific speakers (e.g., "Alice: Review PR by Friday"). Leverages Phase 3 speaker labels.
- **D-07:** Each template has a system prompt that instructs the AI on format and focus. Injected before the transcript text. Single API call per summarize step.
- **D-08:** Template replaces only the summarize step. Proofread, keywords, and title still run as before — no change to existing pipeline for those tasks.
- **D-09:** Summary output matches transcript language (Korean transcript → Korean summary). Consistent with current behavior.
- **D-10:** Template summaries stored as structured JSON sections (e.g., `{"decisions": [...], "action_items": [...], "next_steps": [...]}`). Enables richer display and Phase 5 cross-meeting analysis.

### Custom Template Authoring
- **D-11:** Custom templates stored as YAML files in `~/.meeting_transcriber/templates/`. No in-app editor — power-user file editing.
- **D-12:** Template YAML defines: name, system prompt (instructions to AI), and section names for structured output.
- **D-13:** Built-in templates also stored as YAML files, serving as editable examples. Single source of truth for all templates — both built-in and custom.

### Meeting Detection
- **D-14:** Detection uses both process monitoring (known conferencing apps) AND audio activity heuristic. Detects the app and confirms audio activity before prompting.
- **D-15:** Recording prompt appears as native macOS notification with "Start Recording" action button. Non-intrusive, dismissable.
- **D-16:** Annoyance prevention: dismissing a prompt snoozes that meeting session. Global 5-minute cooldown between prompts. User can disable detection entirely in settings.
- **D-17:** When detection triggers, auto-suggest template based on app (Zoom/Teams/Meet → Team Meeting, FaceTime → 1:1). User can change before recording starts.
- **D-18:** Detection runs continuously as long as tray icon is active, even if main window is closed.
- **D-19:** Polling interval: every 10 seconds. Known apps: Zoom, Microsoft Teams, Google Chrome (Meet), FaceTime, Webex, Slack huddle.
- **D-20:** Detection is opt-in via Settings toggle. Defaults to ON.

### Claude's Discretion
- YAML template schema design (field names, structure, validation rules)
- Exact system prompts for each built-in template
- Process detection implementation (NSWorkspace vs subprocess ps)
- Audio activity heuristic threshold and implementation
- macOS notification framework choice (NSUserNotification vs UNUserNotificationCenter)
- "Re-run AI" button placement in TranscriptViewer
- Template dropdown widget style in MainWindow
- How to display structured summary sections in TranscriptViewer

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### AI Pipeline
- `src/meeting_transcriber/ai/provider_base.py` — AIProvider ABC with `summarize()` method signature that templates will modify
- `src/meeting_transcriber/ai/tasks.py` — AITaskWorker pipeline: proofread → summarize → keywords → title. Template replaces summarize step only.
- `src/meeting_transcriber/ai/gemini_provider.py` — Reference provider implementation showing current prompt structure

### Transcript Storage
- `src/meeting_transcriber/storage/transcript_store.py` — Schema v2.0 with speakers field. Summary currently stored as flat string — needs structured JSON support.
- `src/meeting_transcriber/storage/exporter.py` — Export functions, may need template-aware summary formatting

### UI Integration Points
- `src/meeting_transcriber/ui/main_window.py` — MainWindow with Record button (template dropdown goes next to it), TranscriptViewer (structured summary display, "Re-run AI" button)
- `src/meeting_transcriber/ui/tray.py` — TrayIcon where detection runs in background
- `src/meeting_transcriber/ui/settings_dialog.py` — Settings tabs (add detection toggle, template management)

### Config & Utils
- `src/meeting_transcriber/utils/config.py` — Settings management. New keys for detection preferences, default template.
- `src/meeting_transcriber/utils/constants.py` — Central constants. Add detection polling interval, known app list.

### Requirements
- `.planning/REQUIREMENTS.md` §Meeting Templates — TPL-01 through TPL-03
- `.planning/REQUIREMENTS.md` §Meeting Detection — DET-01 through DET-02

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ai/tasks.py`: AITaskWorker with boolean toggles per task — extend to accept template context for summarize step
- `ai/provider_base.py`: `summarize(text, language=)` signature — may need template prompt parameter
- `utils/keychain.py`: API key pattern reusable if detection needs any credentials
- `ui/tray.py`: TrayIcon already has menu actions — add detection status indicator
- `core/audio_capture.py`: AudioCaptureWorker with level monitoring — reuse for audio activity heuristic

### Established Patterns
- QThread workers for all background I/O
- Signal/Slot for worker → UI communication
- Settings in `~/.meeting_transcriber/settings.json` via load_settings/save_settings
- Lazy imports for optional dependencies (Phase 2 pattern)
- Per-task AI provider overrides via `ai.task_overrides` in settings (Phase 1)

### Integration Points
- `MainWindow.toggle_recording()` — Where template dropdown connects to recording flow
- `app.py` signal wiring — Where detection signals get connected to notification
- `AITaskWorker.__init__()` — Where template system prompt gets injected
- `transcript_store.create_transcript()` — Where structured summary gets stored
- `settings.json` — New keys: `detection.enabled`, `detection.cooldown_seconds`, `templates.default`, `templates.directory`

</code_context>

<specifics>
## Specific Ideas

- 빌트인 템플릿도 YAML 파일로 저장하여 사용자가 수정 가능한 예시 역할
- 회의 감지 시 앱 종류에 따라 템플릿 자동 추천 (Zoom → Team Meeting, FaceTime → 1:1)
- 구조화된 JSON 섹션으로 요약 저장하여 Phase 5 크로스 미팅 분석에 활용
- 화자 라벨이 있으면 액션 아이템/결정사항을 화자에게 귀속 (Phase 3 연계)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-meeting-intelligence*
*Context gathered: 2026-03-28*
