# Decision Log Schema (Draft)

**Purpose:** Capture operator-visible decision summaries for each run so reasoning is transparent and reviewable.

**Status:** Draft placeholder. To be validated in Phase 07.3.1.6 Plan 06 with claude-code-agent-teams evidence.

## Proposed Location
- `.vrs/decisions/decision-log.json`

## Required Fields (Per Entry)
- `decision_id`
- `timestamp`
- `stage`
- `summary`
- `rationale`
- `alternatives_considered[]`
- `evidence_refs[]`
- `task_refs[]`
- `result`

## Example (JSON)
```json
{
  "decision_id": "dec-0003",
  "timestamp": "2026-02-03T12:40:12Z",
  "stage": "verification",
  "summary": "Skip Tier C patterns due to missing context pack",
  "rationale": "context.economic.enabled=false in settings",
  "alternatives_considered": ["Generate context pack", "Run Tier A/B only"],
  "evidence_refs": [".vrs/testing/runs/run-123/report.json"],
  "task_refs": ["task-007"],
  "result": "Tier C gated"
}
```

## Validation Expectations
- Each decision must link to evidence and tasks.
- Decisions must be append-only and ordered by timestamp.
- The log must be referenced from runbook and operator status contract.

