# Claude Code Workflow Architecture

**Authoritative architecture spec for AlphaSwarm.sol's Claude Code workflow-first model.**

---

## Objective

AlphaSwarm.sol is a **Claude Code orchestration framework** for Solidity security audits.

- Primary interface: Claude Code workflows (`/vrs-*` skills).
- Core behavior: task-oriented orchestration + subagent coordination + evidence contracts.
- CLI role: subordinate tool execution surface for subagents, developers, and CI.

This document defines the target architecture and developer workflow contract.

---

## Execution Model

```text
User
  -> Claude Code (/vrs-audit, /vrs-verify, /vrs-investigate)
      -> Task lifecycle (TaskCreate / TaskUpdate)
      -> Subagents (attacker / defender / verifier)
      -> Tool calls (alphaswarm build-kg, query, tools run)
      -> Evidence packs + transcripts + run state
```

Operational rule:

- **Users drive workflows, not raw commands.**
- **CLI commands are implementation details of orchestrated workflows.**

---

## Architectural Surfaces

| Surface | Purpose | Consumers |
|---------|---------|-----------|
| Claude Code Skills (`/vrs-*`) | Primary product UX | End users, auditors |
| Orchestration Contract | Marker/task/evidence guarantees | Skills, subagents, validators |
| CLI Tooling (`alphaswarm ...`) | Deterministic tool execution | Subagents, developers, CI |
| State + Evidence (`.vrs/`) | Reproducibility and resume | Workflows, validators, regressions |

---

## API Contracts

## Runtime Split (Intentional)

- **Shipping runtime (product contract):** Claude Code invokes shipped `/vrs-*` workflows with subagent/task orchestration and tool calls.
- **Testing runtime (Phase 3 harness contract):** Claude Code Agent Teams features (`TeamCreate`, team messaging/lifecycle) are used to stress and validate workflow behavior via `ClaudeCodeRunner` (headless `claude --print`).
- These are complementary surfaces, not competing designs.

## 1. Workflow API (Primary)

Entrypoints:

- `/vrs-audit <scope>`
- `/vrs-health-check`
- `/vrs-investigate <bead-id>`
- `/vrs-verify <bead-id>`
- `/vrs-debate <bead-id>`
- `/vrs-orch-spawn`, `/vrs-orch-resume`

Required behavior:

- Graph-first query-first enforcement.
- Task lifecycle for every reportable finding.
- Evidence-linked verdicts only.
- Fail-closed validation when contracts are violated.

## 2. Orchestration API (Task/Marker Contract)

Required marker families:

- Stage markers (`[PREFLIGHT_PASS]`, `[GRAPH_BUILD_SUCCESS]`, ...)
- Task markers (`TaskCreate(...)`, `TaskUpdate(...)`)
- Verification markers (agent/debate lifecycle as applicable)

Required finding fields for reportable output:

- graph node references
- source locations (`file`, `start_line`, `end_line`)
- evidence pack linkage
- confidence/verdict + rationale

## 3. Tool API (Subordinate)

Tool calls are expected to be invoked by workflows, but remain available for dev/CI:

- `uv run alphaswarm build-kg ...`
- `uv run alphaswarm query ...`
- `uv run alphaswarm tools status|run ...`
- `uv run alphaswarm vulndocs validate ...`

---

## Developer Workflow

1. Implement or update skill/agent/workflow behavior.
2. Validate with workflow harness (scenario -> trials -> graders).
3. Enforce evidence + marker contracts.
4. Run regression baselines and compare against previous runs.
5. Document only proven behavior.

### Testing Priority

1. Workflow correctness (orchestration and evidence contracts)
2. Agent behavior and role adherence
3. Tool integration reliability
4. Benchmark publication (after workflow reliability is proven)

---

## Integrator Guidance

If you integrate AlphaSwarm.sol into another system:

- Integrate against workflow outcomes and evidence artifacts, not transient CLI text output.
- Treat CLI command shape as tooling surface, not product contract.
- Use `.vrs/state/current.yaml` and evidence manifests for stable automation hooks.

---

## Compatibility Notes

- CLI usage remains supported for advanced diagnostics and CI.
- Product documentation and examples prioritize Claude Code skill workflows.
- Legacy CLI-first operational assumptions should be migrated to workflow-first orchestration.

---

## Related Docs

- [Philosophy](PHILOSOPHY.md)
- [Architecture](architecture.md)
- [Workflows](workflows/README.md)
- [Claude Code Orchestration](reference/claude-code-orchestration.md)
- [Claude Code Workflow Migration Guide](migrations/claude-code-workflow-migration.md)

---

*Updated 2026-02-10*
