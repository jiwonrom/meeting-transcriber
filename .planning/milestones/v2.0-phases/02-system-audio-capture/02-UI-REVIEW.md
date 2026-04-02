# Phase 02 — UI Review

**Audited:** 2026-03-27
**Baseline:** 02-UI-SPEC.md (approved design contract)
**Screenshots:** Not captured (PyQt6 desktop app — no web dev server)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Near-complete contract match; two status bar strings deviate from spec and "System Audio" label color change during recording is missing |
| 2. Visuals | 3/4 | All spec components present and positioned correctly; toggle label accent color change unimplemented |
| 3. Color | 3/4 | Hardcoded hex values throughout wizard and settings instead of token lookups; all values are correct tokens so semantic intent holds |
| 4. Typography | 4/4 | All four spec type roles used exclusively (11px/14px/17px + 13px for detail text); weight only 400 and 600 |
| 5. Spacing | 4/4 | All spacing values align with declared token scale (xs=4, sm=8, md=16); no arbitrary CSS values |
| 6. Experience Design | 4/4 | All five interaction states covered; loading/error/success/disabled states fully implemented; mid-recording fallback (D-11) and Aggregate Device lifecycle handled |

**Overall: 21/24**

---

## Top 3 Priority Fixes

1. **"System Audio" label does not turn accent color during dual-source recording** — Users have no visual signal that both audio sources are actively capturing; they rely solely on the level meter to distinguish mic-only from dual mode — Add `self._system_audio_label.setStyleSheet("font-size: 11px; color: #FF443A;")` in `_on_capture_started` when `self._recording_with_system_audio` is True, and restore neutral color in `_on_capture_stopped` and `_on_capture_error`

2. **Hardcoded hex colors in wizard and settings bypass ThemeEngine** — The app will render dark-mode colors even when the user selects light mode via Preferences, because `setStyleSheet("color: #30D158")` is evaluated at widget construction time and ignores the live QSS cascade — Replace all inline `setStyleSheet("color: #...")` calls in `blackhole_wizard.py` and `settings_dialog.py` with QSS property selectors or dynamic `set_theme_colors()` calls so ThemeEngine can reapply them on theme switch

3. **Status bar copy for mid-recording failure deviates from spec** — The spec declares "System audio disconnected -- continuing with microphone only" for the mid-recording failure case (`_on_capture_error`), but the implementation shows "System audio lost -- continuing with microphone only" — users searching documentation or support articles for the exact phrasing will find a mismatch — Change line 897 of `main_window.py` to match the spec string exactly

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

**Passing strings (verified against copywriting contract):**
- Toggle tooltip (enabled): "Capture system audio alongside microphone" — exact match
- Toggle tooltip (disabled/no BlackHole): "BlackHole audio driver required -- click to set up" — exact match
- Toggle tooltip (disabled/recording): "Cannot change audio source while recording" — exact match
- Wizard title: "Scribe \u2014 System Audio Setup" (rendered as "Scribe — System Audio Setup") — exact match
- Wizard step 1 heading: "Capture System Audio" — exact match
- Wizard step 1 body: exact match
- Wizard step 2 heading: "Install BlackHole" — exact match
- Wizard install option A/B labels and button text: exact matches
- Detection status waiting: "Waiting for BlackHole installation..." — exact match
- Detection success: "\u2713 BlackHole detected!" — exact match
- Wizard aggregate heading: "Set Up Audio Mixing" — exact match
- Wizard aggregate body: exact match
- Device preview name: "Scribe Audio (Mic + System)" — exact match
- Wizard aggregate button: "Create Aggregate Device" — exact match
- Aggregate loading: "Creating..." — exact match
- Aggregate success: "\u2713 Aggregate Device created!" — exact match
- Aggregate error: "Failed to create device: {message}. Please try again." — exact match
- Wizard complete heading: "All Set!" — exact match
- Wizard complete body: exact match
- Step indicator: "Step N of 5" — deviation from spec "Step N of 4" (intentional: 5th step added for audio output routing per RESEARCH.md Pitfall 5; plan 02-02 overrides UI-SPEC on this point)
- Settings "Installed" / "Not installed" / "Reconfigure" / "Set Up": exact matches
- Status bar "Recording: Mic + System Audio": exact match
- Status bar "Recording: Microphone": exact match

**Deviations:**

- `main_window.py:824` — Status bar pre-recording fallback: "System audio disconnected -- continuing with microphone only". Spec declares this same string for this scenario (SPEC line 234/265), so this is a pass.
- `main_window.py:897` — Mid-recording failure: "System audio lost -- continuing with microphone only". Spec declares "System audio disconnected -- continuing with microphone only" for this scenario (SPEC line 235). The words "lost" vs "disconnected" diverge from contract. **Flag.**
- Spec: "System Audio" label text turns to `text.accent` during dual-source recording. No corresponding `_system_audio_label.setStyleSheet(...)` call exists anywhere in `main_window.py`. The label never changes color. **Flag.**
- Spec: "BlackHole audio driver not found. System audio capture disabled." expected as a status bar or UI message when BlackHole disappears between sessions. Implementation only logs this to `logger.info` in `app.py:115`. No user-visible message shown. Minor gap.

### Pillar 2: Visuals (3/4)

**Passing:**
- SystemAudioToggle placed between `_duration_label` and `_record_btn` in control bar — matches spec position exactly (`main_window.py:616-631`)
- Toggle is 44x24px with 12px border-radius, 20px thumb, 2px inset — all match spec dimensions
- OFF state colors (track `#3A3A3C`, thumb `#F5F5F7`) match tokens exactly
- ON state colors (track `#FF443A`, thumb `#FFFFFF`) match spec
- DISABLED state uses 50% opacity track (`QColor(58, 58, 60, 128)`) and muted thumb — spec-compliant
- 150ms `QPropertyAnimation` with `InOutQuad` curve implemented as specified
- PointingHandCursor (enabled) and ForbiddenCursor (disabled/recording) both implemented
- "System Audio" caption label below toggle at 11px, center-aligned — matches spec
- DualLevelMeter replaces single QProgressBar — verified by absence of `_level_bar` references
- DualLevelMeter: mic bar 4px, system bar 4px, 4px spacing between — matches spec
- Control bar height expands 72px → 80px in dual mode — matches spec token `heightDual`
- Wizard illustration: `_WaveIllustration` 200x120px QPainter sine waves in `background.elevated` fill — spec-compliant
- Wizard success icon: `_SuccessIcon` 48x48px green circle + white checkmark — spec-compliant
- BlackHoleSetupWizard dialog: 500x520px — spec says 500x480px (deviation due to 5th step addition; proportional adjustment)
- `import math` placed inline inside `paintEvent` at `blackhole_wizard.py:560` — minor code style issue (CLAUDE.md: imports at top of file), not a visual bug

**Missing:**
- "System Audio" label under the toggle never changes to `text.accent` (#FF443A) during dual-source recording. Spec states: "When recording dual-source, label color changes to `text.accent`." (`02-UI-SPEC.md:104`). The label is initialized once with `"font-size: 11px;"` and never updated during recording state changes.
- No hover state feedback on SystemAudioToggle (spec mentions "control bg +5% lighter" on hover for OFF state). The QPainter `paintEvent` does not implement hover, though this is cosmetic and the toggle has a clear interaction affordance via cursor change and tooltip.

### Pillar 3: Color (3/4)

**Color usage is semantically correct** — all hardcoded values are drawn from the correct token positions:

| Hardcoded Value | Token Mapping | Correct? |
|----------------|---------------|----------|
| `#30D158` (success green) | `colors.status.success` dark | Yes |
| `#FF453A` (accent/recording) | `colors.status.recording` dark | Yes |
| `#FF9F0A` (system audio orange) | `colors.status.processing` dark | Yes |
| `#3A3A3C` (track off) | `colors.background.control` dark | Yes |
| `#F5F5F7` (thumb) | `colors.text.primary` dark | Yes |
| `#48484A` (disabled thumb) | `colors.text.muted` dark | Yes |
| `#2C2C2E` (illustration bg) | `colors.background.elevated` dark | Yes |
| `#98989D` (secondary text) | `colors.text.secondary` dark | Yes |
| `#6E6E73` (tertiary text) | `colors.text.tertiary` dark | Yes |

**Issue:** These values are hardcoded as literal strings in `setStyleSheet()` calls rather than being read from ThemeEngine tokens. Light mode counterparts are never applied:
- `blackhole_wizard.py` contains 8 inline `setStyleSheet("color: #...")` calls
- `settings_dialog.py` contains 4 inline `setStyleSheet("color: #...")` calls

When the user switches to light mode (which exists in `design/tokens_light.json`), the wizard and settings dialog will display dark-mode colors on a light background. For example, `#6E6E73` (tertiary dark) against `#FFFFFF` (primary light background) produces inadequate contrast.

**Accent reservation:** Accent (#FF453A) is used on: record button fill (existing, correct), toggle ON track (correct), status.recording label (correct). No accent overuse observed on decorative elements.

**QSS system_level_bar rule** correctly uses `colors['status']['processing']` via ThemeEngine — this is the right pattern that the wizard/settings should follow.

### Pillar 4: Typography (4/4)

Font sizes in use across all new files:
- 11px: step indicator, detection status, hint text, MIC/SYS labels, System Audio label — maps to Caption role
- 13px: instruction text, aggregate status — detail text (between Caption and Body; used sparingly)
- 14px: body text in all wizard pages, settings section body — maps to Body role
- 17px: all wizard page headings — maps to Heading role

All four roles match the spec. No size outside the declared scale (11/14/17px) except 13px for fine-grained status feedback text, which is a reasonable interpolation.

Font weights used: 400 (regular, implicit default) and 600 (semibold via `font-weight: 600`). No weight outside the declared two-weight system.

### Pillar 5: Spacing (4/4)

All spacing values map cleanly to the declared token scale:

| Usage | Value | Token |
|-------|-------|-------|
| DualLevelMeter bar gap | 4px (`setSpacing(4)`) | xs |
| Toggle-label gap | 2px (`setSpacing(2)`) | sub-xs, acceptable for tight caption pair |
| Btn row gap | 16px (`setSpacing(16)`) | md |
| Wizard page layout gap | 16px (`setSpacing(16)`) | md |
| Install card padding | 16px (CSS `padding: 16px`) | md |
| Device preview padding | 12px (CSS `padding: 12px`) | between sm and md; minor |
| Level bar to btn row gap | 4px (`bar_layout.setSpacing(4)`) | xs |

No `[Npx]` or `[Nrem]` arbitrary Tailwind-style values (not applicable — QSS). No magic numbers outside the token scale. The 12px device preview padding is the only value between token stops, and it is contextually appropriate for a smaller card.

Design tokens have been extended correctly with all 6 declared `controlBar` additions in both `tokens_dark.json` and `tokens_light.json`.

### Pillar 6: Experience Design (4/4)

**Loading states:**
- Aggregate Device creation: "Creating..." button text + disabled button + indeterminate `QProgressBar` (range 0,0) — fully implemented (`blackhole_wizard.py:474-477`)

**Error states:**
- Aggregate Device creation failure: error message in red + "Retry" button re-enabled — fully implemented (`blackhole_wizard.py:521-527`)
- Aggregate Device not found at recording start: status bar fallback message + continues with mic — implemented (`main_window.py:821-825`)
- Mid-recording system audio failure (D-11): AudioCaptureWorker restart with mic-only device, dual meter collapses to single, status bar warning — implemented (`main_window.py:887-910`)
- BlackHole uninstalled between sessions: toggle disabled on startup, settings `enabled` auto-set to False — implemented (`app.py`)

**Disabled states:**
- Toggle during recording: `ForbiddenCursor` + tooltip + `mousePressEvent` guard — implemented
- Wizard Next button on step 2: disabled until BlackHole detected — implemented
- Wizard Next button on step 4: disabled until Aggregate Device created — implemented
- "Create Aggregate Device" button: disabled during creation, stays disabled on success, re-enabled as "Retry" on failure — implemented

**Empty states:**
- Spec notes "Not applicable" for this phase. No empty state needed.

**Confirmation for destructive actions:**
- No destructive actions introduced in this phase.

**Aggregate Device lifecycle:**
- Created on startup from saved UIDs if BlackHole is installed (`app.py`)
- Destroyed on `app.aboutToQuit` signal (`app.py`)
- Wizard writes UIDs to settings on completion — full round-trip implemented

**One minor UX gap:** When BlackHole disappears between sessions (uninstall after previous setup), the app auto-disables system audio in settings and logs to `logger.info`, but no user-visible status bar or notification message informs the user why the toggle is now greyed out. The spec declares "BlackHole audio driver not found. System audio capture disabled." as an error copy string (`02-UI-SPEC.md:243`). The current silent degradation works correctly but gives no user feedback.

---

## Files Audited

- `src/meeting_transcriber/ui/widgets/toggle_switch.py` — SystemAudioToggle widget
- `src/meeting_transcriber/ui/widgets/dual_level_meter.py` — DualLevelMeter widget
- `src/meeting_transcriber/ui/blackhole_wizard.py` — BlackHoleSetupWizard + helper widgets
- `src/meeting_transcriber/ui/main_window.py` — Control bar integration, recording logic, mid-recording fallback
- `src/meeting_transcriber/ui/settings_dialog.py` — System Audio section in Audio tab
- `src/meeting_transcriber/ui/theme.py` — QSS rule for `system_level_bar`
- `src/meeting_transcriber/app.py` — Aggregate Device lifecycle (startup/quit)
- `design/tokens_dark.json` — controlBar token additions
- `design/tokens_light.json` — controlBar token additions
- `.planning/phases/02-system-audio-capture/02-UI-SPEC.md` — Audit baseline
- `.planning/phases/02-system-audio-capture/02-02-PLAN.md` — Step count deviation context
