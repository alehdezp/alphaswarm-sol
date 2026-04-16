# Testing Advanced Guide

**Workflow harness design, evidence gates, and reliability validation for AlphaSwarm.sol.**

**Prerequisites:** [Testing Basics](testing-basics.md)

---

## Current Reality (v6.0)

- Full E2E audit is not yet proven end-to-end (Phase 3 target).
- Multi-agent debate is planned and under staged validation.
- Benchmarks are not yet published as final product metrics.

Use this guide as the **specification target** for workflow-first validation and regression hardening.

---

## Primary Validation Surface

AlphaSwarm.sol is **Claude Code workflow-first**.

- Primary: `/vrs-*` workflows with transcript + evidence capture.
- Secondary: `ClaudeCodeRunner` (sync `claude --print`) for headless programmatic runs in pytest.
- Subordinate tooling: `uv run alphaswarm ...` commands for dev/debug/CI.

---

## Workflow Harness Architecture

The advanced harness validates orchestration outcomes, not implementation internals.

1. Define scenario (`task`, success criteria, constraints).
2. Execute scenario through Claude Code orchestration.
3. Capture transcript, markers, and artifacts.
4. Grade outputs using deterministic checks + model-assisted grading where needed.
5. Store evidence pack and compare with baseline.

---

## Scenario Design (Tasks + Trials + Graders)

Each advanced scenario should include:

- `task`: concrete security objective.
- `trials`: at least 3 repeated runs for reliability.
- `graders`:
  - Code-based grader for required markers and schema validity.
  - Optional model-based grader for nuanced reasoning quality.

Recommended fields:

```yaml
name: orchestrator-flow-reentrancy
task: verify attacker-defender-verifier flow on vulnerable contract
trials: 3
timeout_s: 300
required_markers:
  - "[PREFLIGHT_PASS]"
  - "[GRAPH_BUILD_SUCCESS]"
  - "TaskCreate("
  - "TaskUpdate("
required_artifacts:
  - transcript
  - report
  - evidence_pack
negative_control:
  enabled: true
```

---

## Evidence Gates (Fail-Closed)

All advanced tests should hard-fail when these conditions are not met:

1. Missing required orchestration markers.
2. Findings without graph-linked evidence references.
3. Unsafe confidence claims on negative controls.
4. Missing proof-token fields for reportable findings.
5. Invalid transcript/evidence schema.

---

## Reliability and Anti-Fabrication Rules

- Minimum 3 trials per scenario.
- Any 100%/100% precision+recall claim triggers manual investigation.
- Identical outputs across all trials require drift/fabrication review.
- Runtime and cost must indicate real execution (not stubbed paths).

Track:

- `pass@1`, `pass@3`
- variance across findings
- runtime distribution
- cost distribution

---

## VulnDocs Validation (Advanced)

Use workflow-first invocation for authoring/validation loops:

```text
/vrs-validate-vulndocs
/vrs-validate-vulndocs --mode quick
/vrs-validate-vulndocs --mode thorough
```

Tool-level equivalent for CI:

```bash
uv run alphaswarm vulndocs validate vulndocs/
```

---

## Advanced Regression Contract

Before merging major workflow/agent/skill changes:

1. Run advanced workflow suite (multi-trial).
2. Compare against last accepted baseline.
3. Block merge on baseline degradation.
4. Attach failure artifacts for deterministic repro.

---

## Evaluation Intelligence Layer

The testing framework operates in two tiers. The **evaluation engine** (Tier 1) is the deterministic pipeline: hooks observe, parser extracts, scorer computes, evaluator judges. The **evaluation intelligence** (Tier 2) is the adaptive layer that activates incrementally as run data accumulates.

### Coverage Radar

A live heat map tracks what is tested and what is not, across 4 axes: vulnerability class, semantic operation, reasoning skill, and graph query pattern. Cold cells (zero coverage) are prioritized by vulnerability severity. The radar integrates with scenario synthesis for closed-loop gap filling.

### Scenario Synthesis

The scenario synthesis engine analyzes shipped skill/agent prompts, identifies claims that have no corresponding test scenario, and generates new scenarios targeting those gaps. This reduces reliance on manual test authoring for coverage expansion.

### Self-Healing Evaluation Contracts

Evaluation contracts can go stale as workflows evolve. The framework statistically monitors dimension score distributions and flags dimensions that consistently produce zero-variance or trivially-passing scores. Replacement dimensions are proposed automatically; human approval is required before changes take effect.

---

## Reasoning Chain Decomposition

Beyond holistic dimension scores, evaluation decomposes agent reasoning into 7 discrete moves:

- **HYPOTHESIS_FORMATION** — Quality of initial vulnerability hypothesis
- **QUERY_FORMULATION** — Precision and relevance of graph queries
- **RESULT_INTERPRETATION** — Correct reading of query results
- **EVIDENCE_INTEGRATION** — Combining multiple evidence sources coherently
- **CONTRADICTION_HANDLING** — Response to conflicting evidence
- **CONCLUSION_SYNTHESIS** — Logical soundness of final conclusions
- **SELF_CRITIQUE** — Honest assessment of own limitations

Each move is scored independently, producing a reasoning move profile. This enables targeted metaprompting — fixing the exact reasoning step that degraded rather than rewriting entire prompts.

---

## Compositional Stress Testing (Multi-Agent)

Multi-agent workflows are tested under 8 non-standard compositions to validate resilience:

- **Missing agent** (x3): Each of attacker, defender, verifier removed individually
- **Degraded agent** (x3): Each agent given a deliberately weakened prompt
- **Doubled agent**: One agent role duplicated to test deduplication
- **Unusual order**: Agent execution order reversed or shuffled

Keystone analysis identifies which agent's absence causes the largest quality drop, informing where to invest in prompt hardening.

---

## What This Guide Does Not Claim

- It does not claim GA-level benchmark performance today.
- It does not claim production-grade debate reliability is complete.
- It does not replace phase-specific acceptance gates in `.planning/`.

---

## Related Documentation

- [Testing Basics](testing-basics.md) - Foundations and test categories
- [Testing Framework](testing-framework.md) - Product-level testing contract
- [Workflow Testing Architecture](../workflows/diagrams/05-testing-architecture.md) - Diagram-level model
- [State and Roadmap](../../.planning/STATE.md) - Current implementation status

---

*Updated 2026-02-10 | Claude Code workflow-first alignment*
