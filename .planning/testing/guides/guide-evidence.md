# Guide Evidence Packs

**Purpose:** Define the required evidence for any test run.

## Required Evidence Pack Layout (Canonical)

```text
.vrs/testing/runs/<run_id>/
  manifest.json          # run metadata + session label + pane id
  transcript.txt
  report.json
  commands.log
  environment.json
  ground_truth.json
  proofs/
    proof-*.json
```

**Note:** `transcripts/` and `reports/` under `.vrs/testing/` may store copies for quick lookup, but the **run directory is canonical**.

## Manifest Schema (manifest.json)

**Schema:** `schemas/testing/evidence_manifest.schema.json`
**Validator:** `python scripts/validate_evidence_pack.py .vrs/testing/runs/<run_id>`

**Required fields:**
- `run_id`
- `workflow`
- `session_label` (must match `vrs-demo-{workflow}-{timestamp}`)
- `pane_id`
- `timestamp_utc`
- `git_commit`
- `duration_ms`
- `line_count`
- `required_markers_present` (boolean + list)

**Minimal example:**
```json
{
  "run_id": "vrs-2026-02-03-120000",
  "workflow": "audit-entrypoint",
  "session_label": "vrs-demo-audit-20260203-120000",
  "pane_id": "0:1.2",
  "timestamp_utc": "2026-02-03T12:00:00Z",
  "git_commit": "abc1234",
  "duration_ms": 62000,
  "line_count": 214,
  "required_markers_present": true,
  "marker_list": ["[PREFLIGHT_PASS]", "[GRAPH_BUILD_SUCCESS]", "TaskCreate(...)", "TaskUpdate(...)"]
}
```

## Evidence Pack Schema (report.json)

**Schema:** `schemas/testing/evidence_report.schema.json`
**Validator:** `python scripts/validate_evidence_pack.py .vrs/testing/runs/<run_id>`

`report.json` must include the core runtime fields plus workflow-specific proof tokens and markers.

**Required fields (all workflows):**
- `session_label`
- `pane_id`
- `mode`
- `duration_ms`
- `tokens_used`
- `workflow_type` (install, init, audit, orchestration, tool-only)
- `proof_tokens` (see workflow-specific requirements below)

**Required fields (reasoning workflows only):**
- `orchestration_markers` (TaskCreate/TaskUpdate + subagent markers)
- `graph_first` (verification that queries run before conclusions)
- `graph_usage` (query counts + node usage metrics; see `docs/reference/graph-usage-metrics.md`)

**Minimal example:**
```json
{
  "mode": "live",
  "duration_ms": 62000,
  "tokens_used": 18750,
  "workflow_type": "audit",
  "proof_tokens": [
    { "stage_id": "stage.graph_build", "status": "required", "token_path": "proofs/proof-graph.json" },
    { "stage_id": "stage.graph_integrity", "status": "required", "token_path": "proofs/proof-graph-integrity.json" },
    { "stage_id": "stage.context_pack", "status": "required", "token_path": "proofs/proof-context.json" },
    { "stage_id": "stage.pattern_match", "status": "required", "token_path": "proofs/proof-pattern.json" },
    { "stage_id": "stage.agent_spawn", "status": "required", "token_path": "proofs/proof-agents.json" },
    { "stage_id": "stage.debate", "status": "required", "token_path": "proofs/proof-debate.json" },
    { "stage_id": "stage.report", "status": "required", "token_path": "proofs/proof-report.json" }
  ],
  "orchestration_markers": {
    "task_create": ["TaskCreate(task-001)"],
    "task_update": ["TaskUpdate(task-001, confirmed)"],
    "subagent_start": ["SubagentStart(vrs-attacker)", "SubagentStart(vrs-defender)", "SubagentStart(vrs-verifier)"]
  },
  "graph_first": {
    "required": true,
    "verified": true,
    "query_markers": ["VQL-MIN-01", "VQL-MIN-02"],
    "first_query_line": 124,
    "first_conclusion_line": 387
  }
}
```

## Required Proof Tokens by Workflow Type

**Rule:** Every workflow must declare **all** stage proof tokens. If a stage does not apply, mark it as `status: "na"` with a reason.

| Stage proof token | Install / Init | Audit / Orchestration |
|------------------|----------------|------------------------|
| `stage.graph_build` | N/A | Required |
| `stage.graph_integrity` | N/A | Required |
| `stage.context_pack` | N/A (unless context enabled) | Required when context is enabled |
| `stage.pattern_match` | N/A | Required |
| `stage.agent_spawn` | N/A | Required |
| `stage.debate` | N/A | Required |
| `stage.report` | Required if a report is emitted | Required |

**N/A example:**
```json
{ "stage_id": "stage.agent_spawn", "status": "na", "reason": "install-only workflow" }
```

## Environment Schema (environment.json)

**Schema:** `schemas/testing/evidence_environment.schema.json`
**Validator:** `python scripts/validate_evidence_pack.py .vrs/testing/runs/<run_id>`

## Evidence Rules

- Transcripts must be raw and unedited.
- Reports must include `mode`, `duration_ms`, and `tokens_used`.
- Ground truth must include provenance details.
- Missing or edited evidence invalidates the run.
- Evidence packs for reasoning workflows MUST include orchestration markers (TaskCreate/TaskUpdate + subagent markers).
- Evidence packs for reasoning workflows MUST include a `graph_first` verification section.
- Evidence packs for graph-using workflows MUST include `graph_usage` metrics.
- Graph-using workflows MUST include a `stage.graph_integrity` proof token.
- Session label and pane ID MUST appear in both `manifest.json` and `report.json`.

## Minimum Transcript Requirements

- Include tool invocation markers.
- Meet minimum line thresholds for the operation type.
- Show CLI prompts and command execution in order.

## Scenario Boundary Markers (High-Quality Signal)

Add explicit start/end markers to make validation deterministic:

```
[ALPHASWARM-START] <scenario-id> <timestamp>
[ALPHASWARM-END] <scenario-id> <exit-code> <duration-ms>
```

Runs without boundary markers are harder to validate and should be treated as lower quality evidence.

## Marker Registry

Core marker strings are centralized in `.planning/testing/MARKER-REGISTRY.yaml`.
