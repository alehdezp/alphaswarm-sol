# Phase 3.1c Philosophy: v1 Binding Constraints

**Scope:** This document contains ONLY the binding constraints for 3.1c v1.
The full aspirational vision (v2+ scope) lives in `VISION.md` in this directory.
Where CONTEXT.md and this document conflict, CONTEXT.md wins.
This document is synchronized with CONTEXT.md as of 2026-02-19. If they diverge again, CONTEXT.md is authoritative.

---

## One Sentence

Phase 3.1c answers: "Did the agent THINK correctly, and can we make it think better?"

---

## The Five Pillars (v1 Scope)

### Pillar 1: Evaluate Reasoning, Not Just Output

Every evaluation must assess HOW the agent arrived at its conclusion, not just WHAT the conclusion was. This means checking whether graph queries informed analysis or were performative, verifying evidence grounding, and distinguishing genuine reasoning from coincidentally correct output.

**v1 implementation:** 7 reasoning move types (HYPOTHESIS_FORMATION through SELF_CRITIQUE) scored via dual-Opus blind-then-debate evaluator with per-category prompt templates (investigation, tool integration, orchestration, support-lite). External ground truth calibration anchor validates evaluator accuracy. Cascade-aware DAG scoring is v2 scope.

### Pillar 2: Smart Selection Over Blanket Application

Not every workflow needs every evaluation component. Evaluation depth is determined by the workflow's evaluation contract. Four workflow categories with tiered evaluation:

- **Investigation** (attacker, defender, verifier): Full reasoning evaluation (GVS + LLM scoring + debrief)
- **Tool Integration** (slither, aderyn, mythril): Tool use hooks, standard reasoning, no graph scoring, no debrief
- **Orchestration** (audit, verify, debate): Agent lifecycle hooks, coordination + coherence scoring, multi-agent debrief
- **Support** (health-check, bead-*): Minimal hooks, lite reasoning, deterministic checks only

Testing tiers: Core (~10), Important (~15), Standard (~26) — ALL get reasoning evaluation, no exclusions. Tier assignment is dynamic with adaptive promotion/demotion based on behavioral signals.

**v1 implementation:** 51 per-workflow evaluation contracts. Core (~10) fully tailored. Important (~15) stub + 1 workflow-specific check. Standard (~26) template-derived stubs (full authoring deferred until after first real run).

### Pillar 3: Capability THEN Evaluation

Every test runs in two stages:
1. **Capability contract check** (binary pass/fail)
2. **Reasoning evaluation** (scored 0-100, ONLY if capability passes)

No exceptions. No evaluating reasoning of a crashed workflow.

### Pillar 4: Safe Improvement with Regression Detection

- **NEVER** modify production `.claude/` paths. Use jujutsu workspace isolation.
- Every prompt change requires before/after score comparison
- Tier-weighted regression thresholds (Core >10pt=REJECT, Important >15pt, Standard >25pt)
- Improvement loop is HYBRID: system proposes, human disposes
- Single-variable experiment ledger protocol for every prompt change

### Pillar 5: Scores Are Internal Signals, Not Quality Metrics

Scores enable before/after comparison. That is their only purpose. They are NOT product quality certifications or customer-facing metrics.

---

## Binding Rules (v1)

| Rule | Constraint |
|------|-----------|
| A: Serve the Loop | Every plan serves Test -> Evaluate -> Improve -> Re-test |
| B: Two-Stage Testing | Capability FIRST, evaluation ONLY if passes |
| C: Contracts Are Truth | Evaluation contracts define what "good" means per workflow |
| D: Anti-Fabrication | Level 1 static triggers (6 checks) active for all runs. Level 2 adversarial diversity = v2 |
| E: Human Final Word | Scores are suggestions, prompt improvements are proposals |
| F: Honest Research | Never claim success without evidence |
| G: Validation Artifacts | Machine gate report + human checkpoint + drift log per plan |
| H: Coherence Measured | Orchestrator flows must include cross-agent coherence metrics |
| I: Failures Cataloged | Living failure-modes.yaml with frequency, severity, fixes |

**Deferred to v2:** Rule K (full self-healing contracts with automated proposals queue — v1 has real contract_healer with statistical detection, propose-only, no auto-apply), Rule L (live coverage radar with scenario synthesis integration — v1 has real coverage_radar with 4-axis cross-referencing, reporting-only, no synthesis), Rule M (composition stress testing), Rule N (adversarial evaluator testing), Rule O (counterfactual replay), cascade-aware DAG scoring. See `VISION.md` for full descriptions.

**Promoted to v1 (from v2):** Rule J (dual-Opus meta-evaluation) — now core of Plan 07 blind-then-debate protocol. 7-move reasoning taxonomy — now fully scoped in CONTEXT.md Plan 07.

---

## North Star (v1 Achievable)

Phase 3.1c succeeds when:

1. Every shipped skill and agent has an evaluation contract (Core with full eval, Standard with lite evaluation: capability + focused reasoning evaluator + deterministic checks)
2. Framework distinguishes good from bad reasoning (differential > 20 points on anchor transcripts)
3. GVS distinguishes checkbox compliance (< 30) from genuine graph use (> 70)
4. Improvement loop safely proposes prompt changes and detects regressions with tier-weighted thresholds
5. Regression baseline established from day 1
6. Human reading evaluation report understands WHAT failed, WHY, and WHAT to try next
7. Dual-Opus evaluator validated via external corpus ground truth (Spearman rho > 0.6 on agent rank-ordering by detection outcome)
8. Cross-agent coherence measured for orchestrator flows
9. Debrief captures agent responses before shutdown (Layer 1 primary)
10. Improvement loop NEVER modifies production `.claude/`

**Forward-tracked (do not block Phase 3.2):**
11. Anti-fabrication Level 1 active; Level 2 data collection passive
12. Timestamps in all observations for future temporal analysis
13. Coverage assessment documented (live radar is v2)
14. Evaluator validity tracked via anchor transcripts

---

## Environment Acknowledgment

Agents run with production prompts and tools, targeting corpus contracts that provide ground truth for evaluation. This is a controlled corpus environment, not "blind" real-world analysis. Test signal is bounded by corpus quality. Phase 3.2 is where agents face real contracts.

---

*Phase: 3.1c-reasoning-evaluation-framework*
*v1 binding constraints. Full vision: VISION.md*
