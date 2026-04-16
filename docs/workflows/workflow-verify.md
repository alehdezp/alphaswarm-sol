# Workflow Verification And Debate

**Purpose:** Define verification and false‑positive handling.

## Inputs

- Candidate findings
- Evidence packs

## Outputs

- Verified findings
- Discarded false positives
- TaskUpdate markers for each verdict

## Skills

- `vrs-investigate`
- `vrs-verify`
- `vrs-debate`
- `vrs-evidence-audit`
- `vrs-ordering-proof`

## Subagents

- `vrs-attacker`
- `vrs-defender`
- `vrs-verifier`
- `vrs-secure-reviewer`
- `vrs-pattern-verifier`
- `vrs-finding-merger`
- `vrs-finding-synthesizer`
- `vrs-contradiction`

## Traceability

- Skill definitions: `docs/guides/skills-basics.md`, `src/alphaswarm_sol/skills/registry.yaml`
- Subagent definitions (if used): `src/alphaswarm_sol/agents/catalog.yaml`

## Steps

1. Verify each candidate finding.
2. Run debate when needed.
3. Discard false positives explicitly.
4. Update task status with evidence and verdict.

## Success

- Verified findings only, with evidence.
- TaskUpdate markers exist for all verified or discarded items.

## Failure

- All findings reported without verification.
- Verdicts without TaskUpdate evidence.

## Testing

- `.planning/testing/workflows/workflow-e2e.md`
