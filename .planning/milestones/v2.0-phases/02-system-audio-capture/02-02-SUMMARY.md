---
phase: 02-system-audio-capture
plan: 02
subsystem: ui
tags: [pyqt6, qpainter, qstackedwidget, blackhole, aggregate-device, toggle-switch, level-meter]

requires:
  - phase: 02-system-audio-capture-01
    provides: system_audio.py (detect_blackhole, create_aggregate_device, get_device_uid), SystemAudioError, constants

provides:
  - SystemAudioToggle custom QPainter widget with toggled/setup_requested signals
  - DualLevelMeter stacked level bars widget
  - BlackHoleSetupWizard 5-step QDialog with audio output routing guidance
  - Design tokens for toggle dimensions (controlBar section)

affects: [02-system-audio-capture-03, ui-integration, main-window]

tech-stack:
  added: []
  patterns: [QPainter custom toggle widget, QPropertyAnimation for thumb slide, QTimer polling for hardware detection, QThread for CoreAudio device creation]

key-files:
  created:
    - src/meeting_transcriber/ui/widgets/__init__.py
    - src/meeting_transcriber/ui/widgets/toggle_switch.py
    - src/meeting_transcriber/ui/widgets/dual_level_meter.py
    - src/meeting_transcriber/ui/blackhole_wizard.py
    - tests/test_system_audio_toggle.py
    - tests/test_blackhole_wizard.py
  modified:
    - design/tokens_dark.json
    - design/tokens_light.json
    - src/meeting_transcriber/ui/__init__.py

key-decisions:
  - "QRectF lives in QtCore not QtGui in PyQt6 -- corrected import"
  - "Use isHidden() over isVisible() for testing widget visibility without show()"

patterns-established:
  - "QPainter toggle pattern: pyqtProperty + QPropertyAnimation for smooth thumb animation"
  - "Widget testing: use isHidden() for visibility assertions in headless pytest-qt"

requirements-completed: [SYSAUD-01, SYSAUD-02, SYSAUD-03]

duration: 6min
completed: 2026-03-27
---

# Phase 02 Plan 02: System Audio UI Widgets Summary

**SystemAudioToggle (44x24 QPainter), DualLevelMeter (stacked bars), and BlackHoleSetupWizard (5-step QDialog with audio output routing) -- 14 passing tests**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-27T05:49:38Z
- **Completed:** 2026-03-27T05:55:44Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- SystemAudioToggle with QPainter rendering, 150ms thumb animation, toggled/setup_requested signals, and recording lock
- DualLevelMeter with mic-only (4px) and dual (12px) modes using stacked QProgressBars
- BlackHoleSetupWizard with 5 navigable steps including audio output routing guidance (RESEARCH.md Pitfall 5)
- Design tokens extended with controlBar toggle dimensions for both dark and light themes

## Task Commits

Each task was committed atomically:

1. **Task 1: Create SystemAudioToggle and DualLevelMeter widgets + design token updates** - `2ef72f1` (feat)
2. **Task 2: Create BlackHoleSetupWizard 5-step QDialog with audio output routing guidance** - `701c0a7` (feat)

## Files Created/Modified
- `src/meeting_transcriber/ui/widgets/__init__.py` - UI widgets subpackage init
- `src/meeting_transcriber/ui/widgets/toggle_switch.py` - SystemAudioToggle QPainter widget
- `src/meeting_transcriber/ui/widgets/dual_level_meter.py` - DualLevelMeter stacked bars
- `src/meeting_transcriber/ui/blackhole_wizard.py` - 5-step BlackHole setup wizard
- `src/meeting_transcriber/ui/__init__.py` - Added BlackHoleSetupWizard export
- `design/tokens_dark.json` - controlBar toggle dimensions
- `design/tokens_light.json` - controlBar toggle dimensions
- `tests/test_system_audio_toggle.py` - 6 tests for toggle and meter
- `tests/test_blackhole_wizard.py` - 8 tests for wizard

## Decisions Made
- QRectF is in PyQt6.QtCore (not QtGui) -- corrected at import time
- Used isHidden() instead of isVisible() for testing widget visibility in headless pytest-qt environment

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] QRectF import location**
- **Found during:** Task 1 (SystemAudioToggle creation)
- **Issue:** QRectF was imported from PyQt6.QtGui but lives in PyQt6.QtCore
- **Fix:** Moved import to PyQt6.QtCore
- **Files modified:** src/meeting_transcriber/ui/widgets/toggle_switch.py
- **Verification:** Import succeeds, tests pass
- **Committed in:** 2ef72f1

**2. [Rule 1 - Bug] Widget visibility test assertions**
- **Found during:** Task 1 (test verification)
- **Issue:** isVisible() returns False for widgets with hidden parent; tests failed
- **Fix:** Used isHidden() which checks widget's own visibility flag
- **Files modified:** tests/test_system_audio_toggle.py
- **Verification:** All 6 tests pass
- **Committed in:** 2ef72f1

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both auto-fixes were necessary for correct PyQt6 API usage. No scope creep.

## Issues Encountered
- Worktree did not have 02-01 artifacts; required merge from main to access system_audio.py, constants, and config

## Known Stubs
None -- all widgets are fully functional with correct signal/slot connections.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All three widget files ready for Plan 03 to wire into MainWindow and settings dialog
- SystemAudioToggle.setup_requested signal connects to BlackHoleSetupWizard
- DualLevelMeter.set_dual_mode() connects to system audio toggle state

---
*Phase: 02-system-audio-capture*
*Completed: 2026-03-27*
