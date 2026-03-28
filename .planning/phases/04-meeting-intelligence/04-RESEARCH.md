# Phase 04: Meeting Intelligence - Research

**Researched:** 2026-03-27
**Domain:** AI prompt templating, process monitoring, macOS notifications
**Confidence:** HIGH

## Summary

Phase 4 adds two capabilities: (1) YAML-based meeting templates that adapt the AI summarize step to produce structured JSON output, and (2) background conferencing app detection with macOS notification prompts. The template system replaces only the `summarize()` call in the existing `AITaskWorker` pipeline, injecting a template-specific system prompt and requesting structured JSON sections. The detection system uses `NSWorkspace.sharedWorkspace().runningApplications()` via PyObjC (already a dependency) to poll for known conferencing apps every 10 seconds.

Both features integrate cleanly with the existing architecture. Templates require extending `AIProvider.summarize()` with an optional `template_prompt` parameter and storing results as structured JSON in `transcript.json`. Detection requires a new `QThread` worker in `core/` that emits signals consumed by `TrayIcon` / `app.py`, using `QSystemTrayIcon.showMessage()` for notifications (avoids the UNUserNotificationCenter signing requirement).

**Primary recommendation:** Use PyYAML (already installed via pre-commit) for template parsing, `NSWorkspace` via PyObjC AppKit (already installed) for process detection, and `QSystemTrayIcon.showMessage()` for notification prompts. No new dependencies required.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Template is selectable both before recording (dropdown next to Record button) and changeable after recording (via "Re-run AI" button with template picker)
- **D-02:** Dropdown/combo box next to the Record button in MainWindow for template selection before recording. Compact, always visible.
- **D-03:** 5 built-in templates: General (default, matches current behavior), Team Meeting, 1:1, Lecture, Interview
- **D-04:** After recording, user can change template and hit "Re-run AI" to regenerate summary with new template. Non-destructive -- keeps original results until replaced.
- **D-05:** Each template defines template-specific summary sections. Team Meeting: Decisions + Action Items + Next Steps. 1:1: Discussion Points + Agreements + Follow-ups. Lecture: Key Concepts + Q&A + Takeaways. Interview: Candidate Responses + Assessment + Notes. General: current behavior (free-form summary).
- **D-06:** When diarization data exists, AI attributes action items/decisions to specific speakers. Leverages Phase 3 speaker labels.
- **D-07:** Each template has a system prompt that instructs the AI on format and focus. Injected before the transcript text. Single API call per summarize step.
- **D-08:** Template replaces only the summarize step. Proofread, keywords, and title still run as before.
- **D-09:** Summary output matches transcript language (Korean transcript -> Korean summary).
- **D-10:** Template summaries stored as structured JSON sections (e.g., `{"decisions": [...], "action_items": [...], "next_steps": [...]}`).
- **D-11:** Custom templates stored as YAML files in `~/.meeting_transcriber/templates/`. No in-app editor.
- **D-12:** Template YAML defines: name, system prompt (instructions to AI), and section names for structured output.
- **D-13:** Built-in templates also stored as YAML files, serving as editable examples. Single source of truth for all templates.
- **D-14:** Detection uses both process monitoring (known conferencing apps) AND audio activity heuristic.
- **D-15:** Recording prompt appears as native macOS notification with "Start Recording" action button. Non-intrusive, dismissable.
- **D-16:** Annoyance prevention: dismissing snoozes that session. Global 5-minute cooldown. User can disable entirely in settings.
- **D-17:** When detection triggers, auto-suggest template based on app (Zoom/Teams/Meet -> Team Meeting, FaceTime -> 1:1).
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

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TPL-01 | User can select a meeting template before or after recording (Team Meeting, 1:1, Lecture, Interview) | Template YAML system + QComboBox dropdown + "Re-run AI" button. See Architecture Patterns. |
| TPL-02 | AI summary output adapts to selected template format (action items for meetings, Q&A for lectures) | Template-specific system prompts injected into `summarize()`. Gemini JSON mode for structured output. See Code Examples. |
| TPL-03 | User can create custom templates with prompt instructions | YAML files in `~/.meeting_transcriber/templates/` loaded by TemplateManager. See Template YAML Schema. |
| DET-01 | App detects when common conferencing apps are active (Zoom, Teams, Meet, FaceTime) | NSWorkspace.runningApplications() via PyObjC + audio level heuristic. See Detection Architecture. |
| DET-02 | App offers to start recording when a meeting is detected (notification prompt) | QSystemTrayIcon.showMessage() with cooldown/snooze logic. See Notification Strategy. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyYAML | 6.0.3 | Template YAML parsing | Already installed (pre-commit dependency). Simple read-only parsing -- no comment preservation needed. |
| PyObjC AppKit | 12.1 | NSWorkspace for process detection | Already installed (pyobjc-framework-Cocoa). Native macOS API access. |
| PyQt6 QSystemTrayIcon | 6.6+ | Notification prompts | Already available. `showMessage()` provides native macOS notifications without signing requirements. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json (stdlib) | N/A | Structured summary parsing from AI response | Parse Gemini JSON mode output |
| pathlib (stdlib) | N/A | Template directory management | File I/O for `~/.meeting_transcriber/templates/` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyYAML | ruamel.yaml | Comment preservation unnecessary; PyYAML simpler, already installed |
| QSystemTrayIcon.showMessage | UNUserNotificationCenter | UNUserNotificationCenter requires signed executable; QSystemTrayIcon works for Homebrew Python and py2app builds |
| NSWorkspace | subprocess + pgrep | NSWorkspace is native, no subprocess overhead, returns bundle IDs for reliable matching |

**Installation:**
```bash
# No new dependencies required. PyYAML already installed via pre-commit.
# Verify: pip show PyYAML
```

**Version verification:** PyYAML 6.0.3 is current on PyPI (verified 2026-03-27). pyobjc-framework-Cocoa 12.1 already installed.

## Architecture Patterns

### Recommended Project Structure
```
src/meeting_transcriber/
  ai/
    templates.py          # TemplateManager: load, validate, list YAML templates
    provider_base.py      # Extended summarize() signature with template_prompt
    tasks.py              # AITaskWorker accepts template context
  core/
    meeting_detector.py   # MeetingDetectorWorker: QThread, NSWorkspace polling
  ui/
    main_window.py        # Template QComboBox, "Re-run AI" button
    settings_dialog.py    # Detection toggle, template preferences
    tray.py               # Notification display via showMessage()
  utils/
    constants.py          # Detection constants (polling interval, known apps, cooldown)

~/.meeting_transcriber/
  templates/
    general.yaml          # Built-in: General (default)
    team_meeting.yaml     # Built-in: Team Meeting
    one_on_one.yaml       # Built-in: 1:1
    lecture.yaml          # Built-in: Lecture
    interview.yaml        # Built-in: Interview
```

### Pattern 1: Template YAML Schema
**What:** Each template is a YAML file defining name, system prompt, and expected output sections.
**When to use:** All template loading and validation.
**Example:**
```yaml
# ~/.meeting_transcriber/templates/team_meeting.yaml
name: "Team Meeting"
description: "Regular team standup or sync meeting"
icon: "people"  # optional, for UI display
sections:
  - key: "decisions"
    label: "Decisions"
  - key: "action_items"
    label: "Action Items"
  - key: "next_steps"
    label: "Next Steps"
prompt: |
  You are a meeting summarizer for a team meeting.
  Analyze the transcript and produce a JSON object with these sections:
  - "decisions": list of key decisions made
  - "action_items": list of action items (include responsible person if speaker labels available)
  - "next_steps": list of agreed next steps
  Each section value is a list of strings.
  {speaker_instruction}
  {language_instruction}
  Respond ONLY with valid JSON.
```

### Pattern 2: AI Provider Extension
**What:** Extend `AIProvider.summarize()` to accept an optional template prompt parameter.
**When to use:** Template-aware summarization.
**Example:**
```python
# provider_base.py -- extended signature
@abstractmethod
def summarize(
    self, text: str, *, language: str = "auto", template_prompt: str | None = None
) -> str:
    """텍스트를 요약한다. template_prompt가 있으면 템플릿 프롬프트를 사용."""

# gemini_provider.py -- implementation
def summarize(
    self, text: str, *, language: str = "auto", template_prompt: str | None = None
) -> str:
    if template_prompt:
        prompt = f"{template_prompt}\n\nTranscript:\n{text}"
    else:
        # existing default behavior
        lang_hint = f" Respond in {language}." if language != "auto" else ""
        prompt = f"Summarize the following meeting transcript concisely in 3-5 bullet points.{lang_hint}\n\nTranscript:\n{text}"
    return self._call(prompt)
```

### Pattern 3: Detection Worker
**What:** QThread-based background worker using NSWorkspace for app detection.
**When to use:** Continuous monitoring while tray icon is active.
**Example:**
```python
class MeetingDetectorWorker(QThread):
    meeting_detected = pyqtSignal(str, str)  # (app_name, suggested_template)

    KNOWN_APPS: dict[str, str] = {
        "us.zoom.xos": "team_meeting",
        "com.microsoft.teams2": "team_meeting",
        "com.google.Chrome": "team_meeting",  # Meet detection needs URL heuristic
        "com.apple.FaceTime": "one_on_one",
        "com.webex.meetingmanager": "team_meeting",
        "com.tinyspeck.slackmacgap": "team_meeting",  # Slack huddle
    }

    def run(self) -> None:
        from AppKit import NSWorkspace
        while self._running:
            apps = NSWorkspace.sharedWorkspace().runningApplications()
            for app in apps:
                bid = app.bundleIdentifier()
                if bid in self.KNOWN_APPS:
                    # Check audio activity + cooldown before emitting
                    ...
            self.msleep(10_000)  # 10-second polling interval
```

### Pattern 4: Structured Summary Storage
**What:** Summary stored as dict in transcript.json metadata instead of flat string.
**When to use:** When a template is used (non-General).
**Example:**
```python
# In _on_ai_done: store structured summary
if template_name != "general":
    # AI returns JSON string -> parse to dict
    import json
    try:
        structured = json.loads(ai_result.summary)
        metadata["summary"] = structured  # dict with section keys
        metadata["summary_template"] = template_name
    except json.JSONDecodeError:
        metadata["summary"] = ai_result.summary  # fallback to plain text
else:
    metadata["summary"] = ai_result.summary  # plain string (backward compat)
```

### Anti-Patterns to Avoid
- **Modifying AITaskWorker pipeline order:** Template replaces ONLY the summarize step (D-08). Do not change proofread/keywords/title behavior.
- **Hardcoding template prompts in Python:** All templates (including built-in) must be YAML files (D-13). Never embed prompt strings in source code.
- **Blocking main thread with NSWorkspace:** Always call `runningApplications()` from a QThread worker.
- **Using UNUserNotificationCenter directly:** Requires signed executable. Use `QSystemTrayIcon.showMessage()` instead.
- **Breaking transcript.json backward compatibility:** Summary field must accept both `str` (v1.0/v2.0 legacy) and `dict` (v2.0 template). Display code must handle both types.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML parsing | Custom config parser | `yaml.safe_load()` from PyYAML | Handles edge cases, type coercion, multiline strings |
| Process detection | `subprocess.run(["pgrep", ...])` | `NSWorkspace.sharedWorkspace().runningApplications()` | Native API, returns bundle IDs, no string parsing, no subprocess overhead |
| macOS notifications | Raw PyObjC UNUserNotificationCenter | `QSystemTrayIcon.showMessage()` | Works without code signing, already available via PyQt6 |
| JSON structured output parsing | Regex extraction from AI text | Gemini `response_mime_type="application/json"` | Guaranteed valid JSON response, no parsing errors |

**Key insight:** Every external dependency this phase needs is already installed. The architecture additions are extensions of existing patterns (QThread workers, signal/slot communication, settings.json keys).

## Common Pitfalls

### Pitfall 1: Gemini JSON Mode Reliability
**What goes wrong:** AI returns malformed JSON or wraps JSON in markdown code fences.
**Why it happens:** Without explicit JSON mode configuration, LLMs sometimes include explanatory text around JSON.
**How to avoid:** Use `generation_config={"response_mime_type": "application/json"}` in Gemini API call when template is active. Parse with `json.loads()` and fall back to raw string on `JSONDecodeError`.
**Warning signs:** Summary tab showing raw JSON text or parse errors in logs.

### Pitfall 2: Template Prompt Injection with Speaker Labels
**What goes wrong:** Template prompt references speakers but transcript has no diarization data.
**Why it happens:** Phase 3 diarization is optional -- many transcripts won't have speaker labels.
**How to avoid:** Template prompt uses `{speaker_instruction}` placeholder. TemplateManager renders it as "Speaker labels are available: [Alice, Bob, ...]" when diarization exists, or omits it entirely when absent.
**Warning signs:** AI output attributing actions to "Speaker 1" or "Unknown" instead of named speakers.

### Pitfall 3: Chrome Bundle ID False Positive for Meet
**What goes wrong:** Any Chrome window triggers "meeting detected" even when user is just browsing.
**Why it happens:** Google Meet runs inside Chrome; detection by bundle ID alone cannot distinguish Meet from general browsing.
**How to avoid:** For Chrome specifically, require BOTH Chrome running AND audio activity (microphone input detected) before triggering the notification. This is the audio activity heuristic from D-14.
**Warning signs:** Constant meeting detection prompts when Chrome is open.

### Pitfall 4: Notification Spam
**What goes wrong:** User gets repeated notifications for the same ongoing meeting.
**Why it happens:** Polling loop detects the same app every 10 seconds.
**How to avoid:** Implement session tracking: once a meeting app is detected and user responds (start or dismiss), snooze that app until it's no longer running. Global 5-minute cooldown between any prompts (D-16).
**Warning signs:** Multiple notifications stacking in Notification Center.

### Pitfall 5: Backward Compatibility of Summary Field
**What goes wrong:** Existing code that reads `metadata["summary"]` as `str` crashes when it's now a `dict`.
**Why it happens:** Template summaries are stored as structured JSON dicts, but old code expects a string.
**How to avoid:** All summary readers must check `isinstance(summary, dict)` and handle both cases. Exporter, TranscriptViewer, and Obsidian export all need updates.
**Warning signs:** `TypeError: expected str` in exporter or viewer when loading template-generated transcripts.

### Pitfall 6: Built-in Template First-Run Installation
**What goes wrong:** Templates directory doesn't exist on first run; built-in templates not copied.
**Why it happens:** `~/.meeting_transcriber/templates/` needs to be created and populated with bundled YAML files.
**How to avoid:** `TemplateManager.ensure_templates()` checks directory existence and copies bundled templates from package data if missing. Use `importlib.resources` to access bundled YAML files.
**Warning signs:** Empty template dropdown on fresh install.

## Code Examples

### Template Manager Core
```python
# Source: project-specific design based on existing patterns
import pathlib
import yaml
from dataclasses import dataclass, field
from typing import Any

TEMPLATES_DIR = pathlib.Path.home() / ".meeting_transcriber" / "templates"

@dataclass(frozen=True)
class MeetingTemplate:
    """회의 템플릿 정의."""
    name: str
    description: str
    sections: list[dict[str, str]]  # [{"key": "decisions", "label": "Decisions"}, ...]
    prompt: str
    icon: str = ""
    file_path: str = ""

    @property
    def section_keys(self) -> list[str]:
        return [s["key"] for s in self.sections]


class TemplateManager:
    """YAML 기반 회의 템플릿 관리자."""

    def __init__(self) -> None:
        self._templates: dict[str, MeetingTemplate] = {}

    def ensure_templates(self) -> None:
        """템플릿 디렉토리를 확인하고 빌트인 템플릿을 설치한다."""
        TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
        # Copy bundled templates if not present
        ...

    def load_all(self) -> dict[str, MeetingTemplate]:
        """모든 YAML 템플릿을 로드한다."""
        self._templates.clear()
        for path in sorted(TEMPLATES_DIR.glob("*.yaml")):
            try:
                tpl = self._load_one(path)
                self._templates[path.stem] = tpl
            except Exception:
                pass  # Skip invalid templates
        return self._templates

    def _load_one(self, path: pathlib.Path) -> MeetingTemplate:
        """단일 YAML 파일을 MeetingTemplate으로 파싱한다."""
        with open(path, encoding="utf-8") as f:
            data: dict[str, Any] = yaml.safe_load(f)
        return MeetingTemplate(
            name=data["name"],
            description=data.get("description", ""),
            sections=data.get("sections", []),
            prompt=data["prompt"],
            icon=data.get("icon", ""),
            file_path=str(path),
        )

    def render_prompt(
        self, template: MeetingTemplate, *, language: str, speakers: dict[str, str] | None
    ) -> str:
        """템플릿 프롬프트에 컨텍스트 변수를 주입한다."""
        speaker_instruction = ""
        if speakers:
            names = ", ".join(speakers.values())
            speaker_instruction = (
                f"Speaker labels are available in the transcript: {names}. "
                "Attribute action items and decisions to specific speakers when possible."
            )
        language_instruction = ""
        if language != "auto":
            language_instruction = f"Respond in {language}."
        else:
            language_instruction = "Respond in the same language as the transcript."

        return template.prompt.format(
            speaker_instruction=speaker_instruction,
            language_instruction=language_instruction,
        )
```

### Notification via QSystemTrayIcon
```python
# Source: PyQt6 QSystemTrayIcon.showMessage() -- already available
# In tray.py or detection handler:
tray_icon.showMessage(
    "Meeting Detected",
    f"{app_name} is active. Start recording?",
    QSystemTrayIcon.MessageIcon.Information,
    10000,  # display for 10 seconds
)
# Connect messageClicked signal for "click to record" action
tray_icon.messageClicked.connect(self._on_notification_clicked)
```

### NSWorkspace Process Detection
```python
# Source: PyObjC AppKit NSWorkspace API
def _detect_conferencing_apps() -> list[tuple[str, str]]:
    """실행 중인 화상회의 앱을 감지한다."""
    from AppKit import NSWorkspace
    active: list[tuple[str, str]] = []
    for app in NSWorkspace.sharedWorkspace().runningApplications():
        bid = app.bundleIdentifier()
        if bid and bid in KNOWN_CONFERENCING_APPS:
            active.append((app.localizedName(), KNOWN_CONFERENCING_APPS[bid]))
    return active
```

### Structured Summary Display in TranscriptViewer
```python
# Source: project-specific design
def _display_summary(self, summary: str | dict[str, Any], template_name: str) -> None:
    """요약 탭에 구조화된 요약을 표시한다."""
    if isinstance(summary, dict):
        # Structured template summary
        html_parts = []
        for section_key, items in summary.items():
            label = section_key.replace("_", " ").title()
            html_parts.append(f"<h3>{label}</h3>")
            if isinstance(items, list):
                html_parts.append("<ul>")
                for item in items:
                    html_parts.append(f"<li>{item}</li>")
                html_parts.append("</ul>")
            else:
                html_parts.append(f"<p>{items}</p>")
        self._summary_edit.setHtml("".join(html_parts))
    else:
        # Plain text summary (General template or legacy)
        self._summary_edit.setPlainText(summary if summary else "(No summary available)")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| NSUserNotificationCenter | UNUserNotificationCenter | macOS 11+ | NSUserNotificationCenter deprecated but still functional. UNUserNotificationCenter requires code signing. |
| Gemini free-text response | Gemini `response_mime_type: application/json` | 2024 | Reliable structured JSON output without regex parsing |
| PyYAML 5.x (unsafe load) | PyYAML 6.x (safe_load default) | 2023 | Always use `yaml.safe_load()` -- never `yaml.load()` without Loader |

**Deprecated/outdated:**
- `NSUserNotificationCenter`: Deprecated since macOS 11 but still works. Our choice of `QSystemTrayIcon.showMessage()` avoids both deprecated and new APIs.
- `yaml.load()` without Loader: Security vulnerability. Always use `yaml.safe_load()`.

## Open Questions

1. **QSystemTrayIcon.showMessage() action button limitations**
   - What we know: `showMessage()` shows a notification and `messageClicked` fires when clicked. macOS treats it as a standard notification.
   - What's unclear: Whether we can add a custom "Start Recording" action button vs. relying on click-to-act. macOS may only show the notification text without an explicit button.
   - Recommendation: Use click-on-notification as the action trigger. The notification text itself says "Click to start recording." This is sufficient for DET-02.

2. **Google Chrome Meet detection accuracy**
   - What we know: Chrome's bundle ID is `com.google.Chrome`. Meet runs inside a Chrome tab.
   - What's unclear: Whether audio activity heuristic alone is sufficient to distinguish Meet from YouTube playback.
   - Recommendation: Require Chrome + microphone input (not just system audio output) as the heuristic. Microphone access means the user is in a meeting, not watching a video.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PyYAML | Template parsing | Yes | 6.0.1 (installed), 6.0.3 (latest) | -- |
| PyObjC AppKit | NSWorkspace detection | Yes | 12.1 | -- |
| PyQt6 QSystemTrayIcon | Notifications | Yes | 6.6+ | -- |
| sounddevice | Audio activity heuristic | Yes | 0.4.6+ | -- |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ with pytest-qt 4.3+ |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `pytest tests/ -x --tb=short` |
| Full suite command | `make test` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TPL-01 | Template selection dropdown and re-run AI | unit | `pytest tests/test_templates.py::test_template_manager_load -x` | Wave 0 |
| TPL-02 | AI summary adapts to template format | unit | `pytest tests/test_templates.py::test_render_prompt -x` | Wave 0 |
| TPL-03 | Custom template YAML loading and validation | unit | `pytest tests/test_templates.py::test_custom_template_load -x` | Wave 0 |
| DET-01 | Conferencing app detection | unit | `pytest tests/test_meeting_detector.py::test_detect_known_apps -x` | Wave 0 |
| DET-02 | Notification prompt with cooldown | unit | `pytest tests/test_meeting_detector.py::test_cooldown_logic -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x --tb=short`
- **Per wave merge:** `make test`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_templates.py` -- covers TPL-01, TPL-02, TPL-03
- [ ] `tests/test_meeting_detector.py` -- covers DET-01, DET-02
- [ ] `design/templates/` bundled YAML files for testing
- [ ] Test fixtures for structured summary JSON

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `ai/provider_base.py`, `ai/tasks.py`, `ai/gemini_provider.py`, `ai/provider_manager.py` -- current AI pipeline
- Codebase analysis: `storage/transcript_store.py` -- transcript schema v2.0
- Codebase analysis: `ui/main_window.py` -- TranscriptViewer, _run_ai_tasks, toggle_recording flow
- Codebase analysis: `ui/tray.py` -- TrayIcon with QSystemTrayIcon
- Codebase analysis: `app.py` -- signal wiring patterns
- PyObjC AppKit NSWorkspace -- verified working: `NSWorkspace.sharedWorkspace().runningApplications()`
- PyYAML 6.0.1 installed, 6.0.3 latest on PyPI

### Secondary (MEDIUM confidence)
- [Gemini Structured Output docs](https://ai.google.dev/gemini-api/docs/structured-output) -- `response_mime_type: application/json` support
- [macOS-notifications GitHub](https://github.com/Jorricks/macos-notifications) -- UNUserNotificationCenter limitations with unsigned Python
- [NSWorkspace Apple docs](https://developer.apple.com/documentation/appkit/nsworkspace) -- runningApplications API

### Tertiary (LOW confidence)
- QSystemTrayIcon.showMessage() notification interaction model on macOS -- click behavior may vary by macOS version

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed and verified
- Architecture: HIGH -- extends existing patterns (QThread workers, signal/slot, settings.json)
- Pitfalls: HIGH -- based on direct codebase analysis and known API limitations

**Research date:** 2026-03-27
**Valid until:** 2026-04-27 (stable dependencies, no fast-moving areas)
