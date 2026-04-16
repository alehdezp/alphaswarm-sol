# HITL Runbook Template

## Metadata

- `scenario_id`:
- `phase_id`:
- `plan_id`:
- `reviewer`:
- `time_budget_minutes`:
- `generated_from`:

## Purpose

- What uncertainty this checkpoint resolves.
- Why human judgment is required.

## Preconditions

1. Required artifacts and their paths.
2. Required environment variables/config.
3. Required baseline state.

## Setup Commands

```bash
# Exact setup commands here
```

## Execution Steps

1. Command:
```bash
# step command
```
Expected observable signal:
- Concrete output pattern or artifact change.
Failure signature:
- Explicit error/state that indicates failure.

2. Command:
```bash
# step command
```
Expected observable signal:
- ...
Failure signature:
- ...

## Decision Rules

- `pass` if:
  - Rule 1
  - Rule 2
- `fail` if:
  - Rule 1
  - Rule 2
- `needs_follow_up` if:
  - Rule 1

## Repeatability Controls

- Maximum allowed runtime:
- Inputs that must stay constant:
- Inputs allowed to vary:
- Re-run instructions:

## Output Record

Write checkpoint result to:
- `.vrs/debug/phase-<phase>/hitl/<plan-id>.md`

Minimum required fields:
- `scenario_id`
- `reviewer`
- `steps_executed[]`
- `observed_result`
- `expected_result`
- `decision`
- `why_decision`
- `repeatability_rating`
- `time_to_run_minutes`

## Stop/Resume

- Stop condition:
- Resume condition:
- Escalation target:

