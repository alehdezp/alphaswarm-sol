# Guide Settings File (YAML)

**Purpose:** Define a project-level settings file that controls tools, patterns, and workflow behavior.

## Status

Required for production readiness. Not yet implemented. Use this guide as the source of truth for expected behavior.

**Schema reference:** `docs/reference/settings-state-schema.md`

## Recommended Location

- `.vrs/settings.yaml` (preferred)

## Settings vs State (Required Separation)

- **Settings** are user-configured and should NOT be auto-modified.
- **State** is runtime and MUST be auto-updated by the orchestrator.

Recommended state location (production expectation):
- `.vrs/state/current.yaml`

Testing state (already used by test harness):
- `.vrs/testing/state/current.yaml`

## Required Capabilities

- Enable/disable tools by name.
- Enable/disable pattern tiers (A/B/C).
- Limit patterns by tag or ID.
- Control context generation (protocol + economic context).
- Define audit mode defaults (solo vs swarm).
- Control progress guidance output (on/off, verbosity).

## Example Schema

```yaml
version: 1

tools:
  enabled: true
  run_on_start: true
  allow:
    - slither
    - aderyn
    - mythril
  deny: []

patterns:
  tiers:
    tier_a: true
    tier_b: true
    tier_c: false   # Only enable when context coverage is sufficient
  allow_tags: ["access-control", "reentrancy"]
  deny_ids: ["vm-9999"]

context:
  protocol_pack: true
  economic_context: true
  sources:
    - docs/
    - README.md

audit:
  mode: swarm
  max_tasks: 200
  fp_verification: true
  progress_guidance: verbose

ground_truth:
  required_for_validation: true
  sources:
    - code4rena
    - sherlock
```

## Enforcement Rules

- Workflow must respect this file if present.
- If a tool or tier is disabled, it must never run.
- If the file is invalid, audit must fail fast with a clear error.

## Orchestrator State Contract (Auto-Updated)

The orchestrator must write runtime status so users can resume and verify progress.

```yaml
version: 1
run_id: "vrs-2026-02-03-120000"
stage: "pattern-detection"
completed_stages:
  - "health-check"
  - "init"
  - "graph-build"
  - "context-generate"
tools:
  available: ["slither", "aderyn"]
  disabled: ["mythril"]
tasks:
  pending_beads: 3
  active:
    - id: "task-001"
      type: "reentrancy"
      agent: "vrs-attacker"
restrictions:
  tier_c: false
  external_calls: true
```

## Validation

- Add a scenario to ` .planning/testing/scenarios/SCENARIO-MANIFEST.yaml `.
- Confirm the audit respects disabled tools/tiers in transcript.
