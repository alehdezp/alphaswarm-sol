# Guide Context Quality Gate

**Purpose:** Define required protocol context fields and validation rules so Tier B/C reasoning only runs on usable context packs.

## When To Use

- Before any Tier B/C or Tier C pattern evaluation.
- When adding or modifying context pack generation.

## Required Fields (Minimum)

Context packs must include these fields with non-empty values:

- `roles` (roles, permissions, authorities)
- `upgradeability` (proxy model, admin roles, upgrade flow)
- `asset_flows` (asset types, custody model, pricing inputs)
- `trust_boundaries` (trusted/untrusted components and assumptions)
- `assumptions` (explicit invariants relied upon)

Acceptable aliases (validator supports these): `roles|actors|participants|stakeholders`,
`upgradeability|proxy|proxies|upgrade`, `asset_flows|value_flow|assets|flows`,
`trust_boundaries|trust_model|boundaries`, `assumptions|invariants|constraints`.

## Pass/Fail Criteria

**Pass** when all required fields exist and are populated.  
**Fail fast** if any required field is missing or empty.

## Tier B/C Gate Behavior

- If context **fails** validation:
  - Tier B/C and Tier C **must not run**.
  - Mark Tier C as **unknown** and emit a clear skip reason.
- If context **passes** validation:
  - Tier B/C and Tier C may proceed.

## Required Transcript Markers

Canonical registry: `.planning/testing/CONTEXT-MARKERS.md` (aligned to `.planning/testing/MARKER-REGISTRY.yaml`).

Emit one of the following before any Tier B/C reasoning:

- `[CONTEXT_READY]`
- `[CONTEXT_INCOMPLETE]`

If simulated context is used, also emit:

- `[CONTEXT_SIMULATED]`

## Evidence Requirements

Evidence packs must include:

- Validation output (pass/fail + missing fields list)
- Context pack reference path
- Transcript marker for quality gate
 - Validator output showing `[CONTEXT_READY]` or `[CONTEXT_INCOMPLETE]` marker

## Validation Command (Expected)

```bash
claude-code-controller send "uv run python scripts/validate_context.py --context <context.yaml>" --pane=<PANE_ID>
```

## Failure Handling

If validation fails:

- Record the missing fields in the report.
- Provide a remediation hint (e.g., "add roles list with owners/guardians").

## Fixtures (Examples)

- `tests/fixtures/complete-context.yaml`
- `tests/fixtures/incomplete-context.yaml`

## Related Docs

- `docs/workflows/workflow-context.md`
- `docs/reference/testing-framework.md`
- `.planning/testing/guides/guide-tier-c.md`
 - `.planning/testing/CONTEXT-MARKERS.md`
