# Context Marker Registry (Canonical)

**Purpose:** Define the single source of truth for context quality gating markers.

## Canonical Markers (Use These Only)

- `[CONTEXT_READY]` — Context pack passes required-field validation and can be used for Tier B/C and Tier C reasoning.
- `[CONTEXT_INCOMPLETE]` — Context pack failed validation (missing required fields). Tier B/C and Tier C must be skipped/marked unknown.
- `[CONTEXT_SIMULATED]` — Context pack is simulated or bypassed. Must be emitted in addition to READY/INCOMPLETE when applicable.

## Emission Rules

- Emit exactly one of `[CONTEXT_READY]` or `[CONTEXT_INCOMPLETE]` for every context validation.
- Emit `[CONTEXT_SIMULATED]` only when simulated/bypassed context is used.
- Markers must appear **before** any Tier B/C or Tier C reasoning.

## Deprecated Markers (Do Not Use)

Replace any legacy markers with the canonical set above:

- `[CONTEXT_QUALITY_PASS]` → `[CONTEXT_READY]`
- `[CONTEXT_QUALITY_FAIL]` → `[CONTEXT_INCOMPLETE]`
- `[CONTEXT_LOADED]` → `[CONTEXT_READY]`

## Related Docs

- `.planning/testing/guides/guide-context-quality.md`
- `.planning/testing/workflows/workflow-orchestration.md`
- `docs/reference/testing-framework.md`
- `.planning/testing/scenarios/tier-bc/TEMPLATE.md`
