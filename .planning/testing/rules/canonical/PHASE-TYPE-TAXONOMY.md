# Phase-Type Taxonomy

**Status:** Canonical
**Created:** 2026-03-01
**Purpose:** Define phase types with type-specific, measurable testing requirements so the cross-phase testing mandate is enforceable, not aspirational.

---

## Phase Types

Every phase in the roadmap belongs to one of four types. Each type has fundamentally different testing requirements — not just different test counts, but different **kinds** of validation.

### CODE

**Definition:** Implements or modifies Python source code, Solidity contracts, or CLI behavior.

**Testing Requirements:**
- Agent Teams evaluation using `TeamCreate` + teammates with `isolation: "worktree"`
- AgentExecutionValidator: all 12 checks must pass (CLI tool calls present, no Python imports, non-empty results, correct graph queried, plus 8 additional behavioral checks)
- At least 1 red-path session: an agent session deliberately targeting a failure mode (wrong contract, missing graph, concurrent access) to verify error handling
- Persistent artifacts in `.vrs/observations/{phase-id}/` with at least one session transcript and one validator report

**Rationale:** CODE phases change CLI behavior that agents depend on. Only real agent sessions (not unit tests alone) can validate that the CLI works correctly in the agent workflow context.

### EVALUATION

**Definition:** Runs agent evaluation sessions, measures reasoning quality, calibrates scoring.

**Testing Requirements:**
- Dual-Opus evaluator: two independent LLM evaluations of the same transcript; disagreement > 15 points flags unreliable evaluation
- Fabrication checks: 100% pass rate, identical outputs, scores at exactly 100, or duration < 5 seconds all trigger investigation (per TESTING-PHILOSOPHY.md Principle 9)
- Baseline comparison: every evaluation dimension must have a before/after comparison against a documented baseline; regression threshold > 10 points triggers alert
- Persistent artifacts in `.vrs/observations/{phase-id}/` with at least one evaluation result JSON and one baseline comparison

**Rationale:** EVALUATION phases produce quality measurements. The measurements themselves must be validated — an uncalibrated evaluator is worse than no evaluator because it provides false confidence.

### FRAMEWORK

**Definition:** Modifies testing infrastructure, evaluation pipeline, governance documents, or planning templates.

**Testing Requirements:**
- Snapshot Protocol (see below): record pre-modification state before first framework-modifying task
- Snapshot-before/after diff: compare framework behavior using the pre-modification snapshot vs the modified version on identical inputs
- Regression on prior baselines: run at least one prior evaluation baseline through both the snapshot and modified framework; verify no regression > 10 points on any dimension
- Persistent artifacts in `.vrs/observations/{phase-id}/` with at least one diff report

**Rationale:** FRAMEWORK phases modify the measurement tool itself. The modified version cannot validate itself — a bug in the evaluator could cause the evaluator to report "all good." External reference (snapshot) is required.

### SYNTHESIS

**Definition:** Produces VulnDocs, documentation, pattern definitions, governance design artifacts, or planning documents.

**Testing Requirements:**
- Human review checklist: explicit checklist with binary pass/fail items (not subjective quality ratings)
- Pattern validation CLI pass: `uv run alphaswarm vulndocs validate vulndocs/` must pass with zero errors (for VulnDocs phases); or equivalent mechanical validation for other artifact types
- No Agent Teams required: SYNTHESIS phases produce documents, not behavioral changes — agent evaluation would be meaningless
- Persistent artifacts in `.vrs/observations/{phase-id}/` with at least one review checklist (completed) and one validation output

**Rationale:** SYNTHESIS phases are fundamentally different in KIND from CODE phases, not just in degree. Requiring Agent Teams for a documentation phase produces meaningless compliance. Human review + mechanical validation is the appropriate bar.

---

## Mixed-Type Protocol

A phase may declare multiple types separated by `+` (e.g., `type: CODE+FRAMEWORK`).

**Rules:**
1. **Acceptance bar = UNION** of requirements for all declared types
2. **Primary type** (listed first) determines which team owns the acceptance decision
3. **No contradiction resolution needed** if requirements are additive (as they are for all current type combinations)

### Worked Example: Phase 3.1c.1 as `CODE+FRAMEWORK`

Phase 3.1c.1 modifies CLI behavior (CODE) and creates governance/testing framework artifacts (FRAMEWORK).

**CODE requirements:**
- Agent Teams evaluation with AgentExecutionValidator (all 12 checks)
- At least 1 red-path session
- Persistent artifacts in `.vrs/observations/3.1c.1/`

**FRAMEWORK requirements:**
- Snapshot Protocol: record pre-modification state
- Snapshot-before/after diff
- Regression on prior baselines
- Persistent artifacts in `.vrs/observations/3.1c.1/`

**Union (CODE+FRAMEWORK) acceptance bar:**
- Agent Teams evaluation with AgentExecutionValidator (all 12 checks) — from CODE
- At least 1 red-path session — from CODE
- Snapshot Protocol: record pre-modification state — from FRAMEWORK
- Snapshot-before/after diff — from FRAMEWORK
- Regression on prior baselines — from FRAMEWORK
- Persistent artifacts in `.vrs/observations/3.1c.1/` — from both (shared)

**Non-contradiction verification:** CODE requires Agent Teams in worktree-isolated environments. FRAMEWORK requires snapshot diff in a separate workspace. These are independent — Agent Teams run in worktrees while snapshot comparison runs against a jj/git checkout of the pre-modification state. No conflict. Both are satisfiable independently within the same phase.

**Primary type:** CODE (listed first) — the code changes team owns the acceptance decision, with FRAMEWORK requirements as additional gates.

**Done criterion for mixed-type protocol:** This worked example for 3.1c.1 produces a coherent, non-contradictory requirement list. The union is additive — no requirement from one type conflicts with a requirement from the other.

---

## 3.1c.2 Bootstrap Exception

**Problem:** Phases modifying testing infrastructure (FRAMEWORK type) must validate using the pre-modification version. But what if the Snapshot Protocol itself has not been set up?

**Exception text:**

> Phases modifying testing infrastructure use a pre-modification snapshot for acceptance validation. The modified version cannot validate itself. Use snapshot recorded per Snapshot Protocol; if `.vrs/snapshots/{phase}/pre-change-id.txt` is absent, the exception is void and standard FRAMEWORK requirements apply.

**When it applies:** Binary condition — the phase modifies testing infrastructure (FRAMEWORK or mixed-type including FRAMEWORK).

**Why:** A modified evaluator could mask its own bugs. Pre-modification state provides an independent reference.

**How:** Use the snapshot recorded per the Snapshot Protocol section below. Restore via `jj co` or `git checkout` in a separate workspace. Run the pre-modification framework version against the same inputs.

**Fallback:** If `.vrs/snapshots/{phase}/pre-change-id.txt` (or `pre-change-sha.txt`) is absent, the exception is void. Standard FRAMEWORK requirements apply — the phase must produce snapshot diff and regression results using whatever baseline is available.

**Conditions are binary:** Either the snapshot file exists (exception applies) or it does not (standard requirements apply). No judgment required.

---

## Snapshot Protocol

Before the first framework-modifying task in a FRAMEWORK or mixed-type phase:

**Recording (jj-based):**
```bash
jj log -r @ --no-graph -T change_id > .vrs/snapshots/{phase}/pre-change-id.txt
```

**Recording (git-based alternative):**
```bash
git rev-parse HEAD > .vrs/snapshots/{phase}/pre-change-sha.txt
```

**Directory creation (if needed):**
```bash
mkdir -p .vrs/snapshots/{phase}/
```

**Restoration (jj):**
```bash
jj workspace add .vrs/snapshots/{phase}/workspace && cd .vrs/snapshots/{phase}/workspace && jj co $(cat ../.vrs/snapshots/{phase}/pre-change-id.txt)
```
Or in a separate workspace:
```bash
jj co $(cat .vrs/snapshots/{phase}/pre-change-id.txt)
```

**Restoration (git):**
```bash
git worktree add .vrs/snapshots/{phase}/workspace $(cat .vrs/snapshots/{phase}/pre-change-sha.txt)
```

**Verification:**
```bash
cat .vrs/snapshots/{phase}/pre-change-id.txt
# Must be non-empty
jj log -r $(cat .vrs/snapshots/{phase}/pre-change-id.txt) --no-graph
# Must show a valid commit matching the recorded change ID
```

**Verification (git):**
```bash
cat .vrs/snapshots/{phase}/pre-change-sha.txt
# Must be non-empty
git log -1 $(cat .vrs/snapshots/{phase}/pre-change-sha.txt)
# Must show a valid commit matching the recorded SHA
```

---

## intelligence_contribution Metadata Field

**Purpose:** Optional metadata annotation documenting which Tier 2 intelligence modules each phase's data feeds. Enables Phase 3.1c.3 to trace data lineage from phase outputs to intelligence modules.

**Usage:** Included in the Testing Gate template as an optional field. Phase planners list the Tier 2 modules their phase data feeds (e.g., `coverage_radar`, `scenario_synthesizer`, `reasoning_decomposer`).

**Not an enforcement gate:** This field is metadata only. Its presence or absence does not affect acceptance criteria. It exists to support traceability and planning for Phase 3.1c.3 (Evaluation Intelligence Bootstrap).

**Available Tier 2 modules** (from TESTING-FRAMEWORK.md):
1. `scenario_synthesis_engine`
2. `coverage_radar`
3. `adaptive_tier_management`
4. `behavioral_fingerprinting`
5. `self_healing_contracts`
6. `cross_workflow_learning`
7. `reasoning_chain_decomposition`
8. `evaluator_self_improvement`
9. `compositional_stress_testing`
10. `gap_driven_synthesis_loop`

---

## Enforcement

Testing requirements defined in this taxonomy are enforced through **plan task done criteria** (per `PLAN-PHASE-GOVERNANCE.md`), not through advisory CONTEXT.md sections.

Each phase's Testing Gate (see `TESTING-GATE-TEMPLATE.md`) translates the type-specific requirements into concrete `<done_criteria>` items in plan tasks. A plan task is not complete unless its done criteria — derived from this taxonomy — are satisfied.

Advisory sections without done-criteria enforcement are insufficient (ADV-301 insight).

---

## References

- Testing gate template: `.planning/testing/templates/TESTING-GATE-TEMPLATE.md`
- Testing framework: `.planning/testing/rules/canonical/TESTING-FRAMEWORK.md`
- Testing philosophy: `.planning/testing/rules/canonical/TESTING-PHILOSOPHY.md`
- Plan governance: `.planning/testing/PLAN-PHASE-GOVERNANCE.md`
- Phase 3.1c.1 CONTEXT: `.planning/phases/3.1c.1-cli-graph-isolation-hardening/3.1c.1-CONTEXT.md`
