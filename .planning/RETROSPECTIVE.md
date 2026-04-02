# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v2.0 — Meeting Intelligence Platform

**Shipped:** 2026-04-02
**Phases:** 8 | **Plans:** 19 | **Timeline:** 8 days (2026-03-25 → 2026-04-02)

### What Was Built
- SRT/VTT/Obsidian export with multi-provider AI (OpenAI, Anthropic, Gemini) and automatic fallback
- System audio capture via BlackHole with guided setup wizard and dual-channel recording
- Speaker diarization with pyannote.audio, CoreML optimization attempt, and inline speaker labels
- Meeting intelligence: 5 YAML templates, structured AI summaries, auto meeting detection with snooze
- Cross-meeting analysis: multi-transcript selection, combined AI insights, searchable metadata index
- Gap closure: SidebarWidget wiring, MetadataIndex fixes, per-task provider resolution

### What Worked
- **Provider pattern** — Abstract base + concrete providers made adding OpenAI/Anthropic trivial; FallbackProvider adapter kept AITaskWorker unchanged
- **Lazy imports** — pyobjc, pyannote, torch, coremltools all lazy-loaded; avoids SDK errors on machines without optional deps
- **Signal/Slot for all reverse communication** — Clean separation between core/ai and ui; no import cycles
- **Gap closure phases** — Phases 6-8 caught real integration bugs (SidebarWidget never shown, MetadataIndex field mismatch) that would have been shipped broken
- **3-source cross-reference audit** — VERIFICATION + SUMMARY + REQUIREMENTS caught discrepancies that single-source checks missed

### What Was Inefficient
- **Phase 2 had no VERIFICATION.md** — Skipped formal verification, caught only during milestone audit; added a full extra phase (Phase 6) to retroactively verify
- **SidebarWidget created but never parented** — Signal wiring existed but widget wasn't in layout; integration checker caught what unit tests missed
- **Per-task provider UI not built** — Backend fully wired but no UI to expose it; BYOK-03 technically satisfied but users can't use the feature without editing JSON

### Patterns Established
- **SidebarWidget injection via constructor** — Pass external widget to MainWindow rather than creating internally; enables testing and prevents duplicates
- **MetadataIndex as optional kwarg** — `index: MetadataIndex | None = None` pattern for backward compat when passing index through call chains
- **Vendor-specific JSON modes** — Gemini `response_mime_type`, OpenAI `json_object`, Anthropic prompt-only; wrapped per-provider
- **YAML template files** — User-extensible via filesystem; `TemplateManager.load_all()` globs directory

### Key Lessons
1. **Integration testing catches what unit tests miss** — SidebarWidget had 10 passing unit tests but was never visible at runtime. The integration checker found it by tracing signal wiring to layout parenting.
2. **Verify every phase formally** — Skipping Phase 2 verification created a Phase 6 remediation. The cost of verification is much lower than the cost of gap closure.
3. **UI coverage for backend features** — Don't wire a backend feature (per-task overrides) without the UI to expose it. The feature is invisible to users.
4. **Milestone audits pay for themselves** — The 3-source cross-reference + integration checker found 4 real bugs across 5 phases that passed their individual verifications.

### Cost Observations
- Model mix: Primarily sonnet for execution, opus for planning/review
- Notable: Gap closure phases (6-8) were lightweight (1-2 plans each) but caught critical integration bugs

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Timeline | Phases | Key Change |
|-----------|----------|--------|------------|
| v2.0 | 8 days | 8 | Milestone audit + gap closure phases introduced |

### Cumulative Quality

| Milestone | Tests | LOC | Phases |
|-----------|-------|-----|--------|
| v2.0 | 371 | 9,501 | 8 |

### Top Lessons (Verified Across Milestones)

1. Integration testing + milestone audits catch cross-phase wiring bugs that per-phase verification misses
2. Lazy imports are essential for optional heavy dependencies (pyannote, torch, pyobjc, coremltools)
