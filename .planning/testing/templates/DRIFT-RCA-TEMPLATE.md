# Drift RCA Template

## Metadata

- `phase_id`:
- `plan_id`:
- `drift_event_id`:
- `detected_at`:
- `detected_by`:
- `severity`: `minor` | `major` | `critical`

## Drift Description

- Expected behavior:
- Observed behavior:
- Scope of impact:

## Severity Justification

- Why this severity applies:
- Systems/artifacts affected:
- Gate impact:

## Cause Analysis

- Primary cause code:
  - `bad_assumption`
  - `missing_dependency`
  - `scope_change`
  - `test_gap`
  - `tooling_failure`
  - `environment_drift`
  - `human_process_gap`
- Secondary cause code (optional):
- Evidence supporting cause:

## Root Cause Narrative

- What changed:
- Why it changed:
- Why this was not detected earlier:

## Corrective Actions

1. Immediate containment:
2. Plan/context correction:
3. Test/check updates:
4. Documentation updates:

## Verification Plan

- How to prove drift is resolved:
- Commands/artifacts used:
- Human checkpoint needed:

## Preventive Controls

- New guardrails added:
- Ownership:
- Effective date:

## Required Log Update

Append structured record to:
- `.vrs/debug/phase-<phase>/drift-log.jsonl`

Required fields:
- `timestamp`
- `phase_id`
- `plan_id`
- `severity`
- `primary_cause_code`
- `why_drift_happened`
- `corrective_actions[]`
- `verification_ref`

