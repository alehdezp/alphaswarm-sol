# Workflow Task Orchestration

**Purpose:** Define TaskCreate/Task/TaskUpdate expectations.

## Inputs

- Pattern candidates
- Graph evidence

## Outputs

- Task records
- Subagent outputs
- Task‑scoped evidence packets

## Skills

- `vrs-orch-spawn`
- `vrs-orch-resume`
- `vrs-investigate`

## Subagents

- `vrs-attacker`
- `vrs-defender`
- `vrs-verifier`

## Traceability

- Skill definitions: `docs/guides/skills-basics.md`, `src/alphaswarm_sol/skills/registry.yaml`
- Subagent definitions (if used): `src/alphaswarm_sol/agents/catalog.yaml`

## Steps

1. Create tasks per candidate pattern (TaskCreate).
2. Assign scoped subagents with explicit task IDs.
3. Collect evidence and update status (TaskUpdate).
4. Mark false positives explicitly with TaskUpdate.

## TaskUpdate Output Schema (Required)

TaskUpdate output must be structured and map directly to evidence pack fields.

**Required fields:**
- `task_id`
- `status` (open | investigating | confirmed | rejected)
- `verdict` (confirmed | rejected | inconclusive)
- `evidence` (graph nodes, code locations, queries, proof tokens)
- `subagents` (attacker/defender/verifier summaries)
- `markers` (TaskUpdate marker string)

**Example YAML (required format):**
```yaml
task_update:
  task_id: task-001
  status: confirmed
  verdict: confirmed
  evidence:
    graph_nodes:
      - node: "Function:Vault.withdraw"
    code_locations:
      - "Vault.sol:145"
    vql_queries:
      - "VQL-MIN-01"
    proof_tokens:
      - "proofs/proof-agents.json"
      - "proofs/proof-debate.json"
  subagents:
    attacker: "Exploit path documented with evidence refs."
    defender: "Mitigations checked; no guard found."
    verifier: "Verdict confirmed; evidence complete."
  markers:
    task_update_marker: "TaskUpdate(task-001, confirmed)"
```

## Hook Enforcement

- **Stop / SubagentStop** must block completion if TaskCreate/TaskUpdate markers are missing.
- **PostToolUse** should log task IDs and evidence markers.

See: `docs/reference/claude-code-orchestration.md`.

## Success

- Each finding maps to a task lifecycle.
- Subagents do not drift beyond task scope.

## Failure

- Findings produced without tasks or scope enforcement.
- Subagent reports exceed assigned scope.

## Testing

- `.planning/testing/workflows/workflow-orchestration.md`
