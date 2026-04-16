---
phase: 07.3.1.5-full-testing-orchestrator
status: active
updated: 2026-02-11
---

# Core Testing Philosophy

## The Testing Framework Identity

This project's testing framework is not a collection of assertions.
It is an intelligent, adaptive system that:

1. **RUNS** real workflows in simulated environments
   (agents don't know they're being tested)
2. **OBSERVES** selectively via evaluation-contract-driven hooks
   (tool calls, graph queries, sub-agents, reasoning)
3. **EVALUATES** reasoning quality, not just output correctness
   (did the agent THINK correctly?)
4. **IDENTIFIES** failures and diagnoses WHY
   (debrief protocol, transcript analysis)
5. **IMPROVES** prompts safely in sandboxes
   (never modifies production)
6. **DETECTS** regressions before changes ship
   (before/after score comparison)
7. **REPORTS** to humans when auto-fix fails
   (full debugging context)

This is the Test -> Evaluate -> Improve -> Re-test loop.
It is the project's core testing identity.
It is Phase 3.1c.

## Principles

### 1. Evaluate Reasoning, Not Just Output

Checkbox testing (assert tool was called, assert output contains string) cannot answer "did the agent think correctly?" An agent can run graph queries as compliance, ignore results, and pass all assertions.

Reasoning evaluation reads the full transcript, observation log, and debrief responses, then judges:
- Did graph queries inform analysis or were they performative?
- Is reasoning deep or shallow?
- Are claims backed by specific evidence?
- Did the agent stay within its role?
- Did the agent find something beyond pattern matching?

Binary pass/fail testing misses the most dangerous failure mode: workflows that "pass" but produce shallow, unreliable, or coincidentally-correct results. The evaluation framework catches these by tracking reasoning quality across multiple dimensions as internal regression signals — detecting what broke and where, not producing quality scores. These signals enable before/after comparison to identify improvement or degradation, not threshold-based pass/fail.

### 2. Smart Selection Over Blanket Application

Not every workflow needs every check. Applying Graph Value Score to a health-check skill produces meaningless scores (GVS = 0.0). Applying SubagentStart/Stop hooks to a single-agent workflow produces false negatives.

Each workflow's evaluation contract specifies WHICH components apply. This:
- Reduces cost (no wasted evaluator subagent calls)
- Reduces false positives (no meaningless scores inflating results)
- Improves signal quality (every check produces actionable information)
- Avoids false negative rankings (no penalizing workflows for missing irrelevant features)

The smart selection matrix maps workflow categories (investigation, tool integration, orchestration, support) to evaluation components (hooks, GVS, reasoning evaluator depth, debrief mode).

### 3. Safe Sandboxing for Prompt Improvement

Production prompts (SKILL.md, agent .md) are NEVER modified during testing. The framework proposes improvements but never applies them directly.

When experimenting with prompt improvements:
1. Copy production `.md` file into test project's `.claude/` folder (sandbox)
2. Modify ONLY the sandbox copy
3. Re-run the workflow with the modified prompt
4. Compare evaluation scores (before/after)
5. If improved: human approves change to production `.md` manually
6. Delete sandbox

This is a hard rule. Automated prompt modification of production files is never acceptable, regardless of confidence level.

### 4. Regression Detection is Mandatory

Every prompt change requires before/after score comparison. The evaluation framework enforces:
- **Hard regression threshold**: any dimension drops > 0.2 triggers immediate revert and human alert
- **Soft regression threshold**: any dimension drops > 0.1 triggers a warning
- **Improvement minimum**: target dimension must improve by >= 0.03 to justify the change
- Score history is tracked across iterations for convergence detection

Improvements require explicit human approval before production update. The framework presents the score diff and narrative assessment; the human decides.

### 5. Smart Observability

Hooks are available infrastructure; each test's evaluation contract specifies which hooks to enable. The observation layer is passive: hooks write JSONL event logs, and the evaluation framework reads them after runs complete.

This design enables:
- Performance: tests that don't need hook observation skip it entirely
- Context-efficiency: each test only enables hooks that honestly contribute to its evaluation
- Smart selection: investigation tests get full observation; support tests get none or minimal
- Debugging: when investigating issues, full hook capture is available on demand

### 6. Real Execution Only

Any plan tagged `type: validation`, `type: ga-validation`, or `type: e2e` MUST use LIVE execution mode via claude-code-controller.

The product is a human-facing workflow; correctness depends on interactive behavior, timing, and operator control. Simulations and mocks miss failure modes: agent-teams sessions, CLI prompts, tool calls, and workflow resumes must be exercised exactly as users do.

If a behavior cannot be observed through a real claude-code-controller-driven session, it is **not validated**.

### 7. External Ground Truth Only

Ground truth for validation MUST come from external sources (Code4rena, SmartBugs, etc.) with documented provenance. Never use the system's own output as ground truth.

This prevents circular validation where the system confirms its own biases. External ground truth with provenance is stored in `.vrs/corpus/ground-truth/` with source tracking in `provenance.yaml`.

### 8. Evidence-First

Every finding must link to:
- Real graph node IDs from BSKG queries
- Real code locations (file:line)
- Real timestamps from actual execution
- Real token counts from API responses

Evidence-first validation requires real transcripts, timestamps, and artifacts; fabricated outputs invalidate trust. The evaluation framework verifies evidence grounding as a scored dimension, not just a presence check.

### 9. Imperfection is Expected

Real validation will show:
- Precision 60-85% (not 100%)
- Recall 50-80% (not 100%)
- Some timeouts and errors
- Variance across test cases

Perfect metrics (100%/100%) are a red flag indicating fabrication. The framework tracks score distributions and flags suspiciously uniform results.

### 10. Dynamic Test Generation Intelligence

The testing framework doesn't just run static test suites — it discovers its own blind spots. A scenario synthesis engine analyzes shipped skill and agent prompts, cross-references against the existing test corpus, identifies untested claims, and generates new test scenarios targeting coverage gaps. Coverage is tracked via a live heat map across 4 axes: vulnerability class, semantic operation, reasoning skill, and graph query pattern.

### 11. Evaluation Self-Improvement

The evaluator itself is a component that can degrade. When meta-evaluation detects persistent inter-rater disagreement, the framework generates evaluator prompt variants and selects the best one. This is bounded to 3 iterations per dimension, and human approval is required before any evaluator prompt change takes effect. The measurement tool improves alongside what it measures.

### 12. Coverage Gap Visibility

You can't improve what you can't see. The framework maintains a live coverage radar showing what IS tested and critically what is NOT tested. Cold cells (zero coverage) are prioritized by vulnerability severity and skill claims. Gap-driven scenario synthesis closes coverage holes automatically, feeding back into the test generation engine.

### 13. Reasoning Chain Decomposition

Beyond holistic per-dimension scores, evaluation decomposes reasoning into discrete moves: HYPOTHESIS_FORMATION, QUERY_FORMULATION, RESULT_INTERPRETATION, EVIDENCE_INTEGRATION, CONTRADICTION_HANDLING, CONCLUSION_SYNTHESIS, and SELF_CRITIQUE. Each move is scored independently, producing reasoning move profiles that enable precise metaprompting — targeting the exact reasoning step that degraded rather than rewriting entire prompts.

### 14. Two-Tier Evaluation Architecture

The evaluation framework operates in two tiers:

- **Evaluation Engine (Tier 1):** The deterministic pipeline — hooks observe, parser extracts, scorer computes, evaluator judges, runner orchestrates. This is the mechanical backbone that produces repeatable results.
- **Evaluation Intelligence (Tier 2):** The adaptive layer — scenario synthesis discovers gaps, coverage radar tracks tested vs untested space, tier management promotes/demotes based on behavioral signals, fingerprinting detects behavioral drift, self-healing contracts detect stale or trivial evaluation dimensions, and cross-workflow learning propagates insights. The intelligence layer activates incrementally as data accumulates.

### 15. Sequential Execution for Agent Teams Tests

Plans that spawn Agent Teams (multi-agent coordination tests) MUST execute in top-level Claude Code sessions, NOT via subagents. Agent Teams cannot be spawned from subagents. Wave parallelism in plan dependencies is for planning only — execution is strictly sequential within a single top-level session.

## The Continuous Improvement Loop

```
     +----------+       +----------+       +----------+
     |   TEST   | ----> | EVALUATE | ----> | IDENTIFY |
     | workflow  |       | reasoning|       | failures |
     +----------+       +----------+       +----------+
          ^                                      |
          |                                      v
     +----------+       +----------+       +----------+
     |  RE-TEST | <---- | IMPROVE  | <---- | DIAGNOSE |
     | compare  |       | prompt   |       |   WHY    |
     +----------+       +----------+       +----------+
          |
          v
     +----------+
     | REGRESS? | ----> Report to human if can't auto-fix
     | detect   |       or if regression detected
     +----------+
```

The loop operates as follows:

1. **TEST** the actual shipped workflow against real scenarios in isolated sessions
2. **EVALUATE** how it performed using observation hooks, graph value scoring, and LLM reasoning evaluation (Claude Code subagent)
3. **IDENTIFY** failures and weaknesses across scored dimensions (not just pass/fail)
4. **DIAGNOSE** WHY it failed using debrief protocol (agent debrief approach TBD + transcript analysis)
5. **IMPROVE** the workflow's prompt (SKILL.md, agent .md) in a sandbox copy
6. **RE-TEST** the improved version against the same scenario and compare scores
7. **REGRESS?** check whether the change made things better or worse; report to human if regression detected or if auto-fix fails

## Phase Relationships

- **Phase 3.1b** provides the infrastructure (controller, parser, hooks, harness, DSL, corpus)
- **Phase 3.1c** provides the intelligence (evaluation, reasoning, improvement, regression) -- THIS IS THE TESTING FRAMEWORK
- Skills, agents, and orchestrator tests live in 3.1c where they can be evaluated intelligently, not in 3.1b
- The regression baseline includes internal regression signals from day 1 (for before/after comparison), not just pass@k

Phase 3.1b answers "did it work?" -- Phase 3.1c answers "did it reason correctly, and can we make it better?"

## Integration with Phase 7.3.*

All plans in Phase 7.3.* MUST:

1. Reference this philosophy document
2. Use `claude-code-controller` for all session management
3. Produce evidence packs in `.vrs/testing/runs/<run_id>/`
4. Compare against external ground truth only
5. Report honest metrics with limitations documented

## Related Documents

- `.planning/testing/rules/canonical/TESTING-FRAMEWORK.md` - Detailed architecture
- `.planning/testing/rules/canonical/VALIDATION-RULES.md` - Enforcement rules (A1-F4, G1-G3)
- `.planning/phases/3.1c-reasoning-evaluation-framework/context.md` - Full phase context
- `.planning/TOOLING.md` - Task -> tool selection
