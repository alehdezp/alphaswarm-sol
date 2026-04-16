# Operator Status Contract (Draft)

**Purpose:** Define the minimum status information an operator can query during or after a run.

**Status:** Draft placeholder. To be refined in Phase 07.3.1.6 Plan 06 with live claude-code-agent-teams evidence.

## Scope
This contract describes what an operator should see when running:
- `/vrs-status`
- `/vrs-status --verbose`
- `/vrs-resume`

## Required Fields (Minimum)
- `stage.current`
- `stage.completed[]`
- `stage.next`
- `tasks.pending[]`
- `tasks.completed[]`
- `settings.hash`
- `artifacts.transcripts[]`
- `artifacts.reports[]`
- `artifacts.evidence_packs[]`

## Task Listing Requirements
Each task entry must include:
- `id`
- `status` (pending, in_progress, completed, failed)
- `summary`
- `output_ref` (path or ID to output)
- `last_updated`

## Example Status Output (YAML)
```yaml
stage:
  current: graph_build
  completed: [health_check, init]
  next: context_generation

tasks:
  pending:
    - id: task-002
      status: pending
      summary: "Verify access control patterns"
      output_ref: null
      last_updated: "2026-02-03T12:34:56Z"
  completed:
    - id: task-001
      status: completed
      summary: "Build graph"
      output_ref: .vrs/graphs/graph.json
      last_updated: "2026-02-03T12:30:10Z"

settings:
  hash: "sha256:..."

artifacts:
  transcripts:
    - .vrs/testing/runs/<run_id>/transcript.txt
  reports:
    - .vrs/testing/runs/<run_id>/report.json
  evidence_packs:
    - .vrs/testing/runs/<run_id>/
```

## Where It Lives
- Primary: `.vrs/state/current.yaml`
- Session UI mirror: `.claude/data/sessions/{session_id}.json` extras

## Validation Expectations
- Status output MUST reflect real state, not static text.
- Status should update on every stage transition.
- If tasks exist, they must appear in status output.
