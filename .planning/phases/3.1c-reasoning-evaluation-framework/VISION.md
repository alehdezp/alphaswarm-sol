# Phase 3.1c Vision: The Full Aspirational Design (v2+ Scope)

> **This document is NOT binding for 3.1c v1.** It describes the full evaluation system
> we aspire to build across multiple phases. v1 binding constraints live in `PHILOSOPHY.md`.
> Where `CONTEXT.md` and this document conflict, `CONTEXT.md` wins.
>
> Moved from PHILOSOPHY.md on 2026-02-19 during improvement pass cleanup (P4-IMP-01, P2-IMP-05).

## One Sentence

Phase 3.1c answers the question no other phase can: "Did the agent THINK correctly, and can we make it think better?"

---

## Identity

Phase 3.1c IS the testing framework. Not an add-on. Not a quality gate. Not a scoring system. It is the entire reason Phases 3.1 and 3.1b exist.

3.1b builds pipes. 3.1c builds the brain that uses them.

The testing framework is an intelligent, adaptive system that runs real workflows, observes behavior selectively, evaluates reasoning quality, identifies failures, diagnoses WHY, improves prompts safely, detects regressions, and reports to humans when it can't auto-fix.

This is the Test -> Evaluate -> Improve -> Re-test loop. Every plan in this phase must serve this loop.

---

## The Core Insight

**The most dangerous failure mode is a workflow that "works" but reasons badly.**

An agent can:
- Run BSKG queries as checkbox compliance and ignore the results
- Produce a finding that happens to be correct through pattern matching, not reasoning
- Pass all liveness checks ("did it run?") while producing shallow, unreliable output
- Score perfectly on mechanical assertions while thinking poorly

Traditional testing cannot catch this. Only reasoning evaluation can. That is why this phase exists.

---

## The Five Pillars

### Pillar 1: Evaluate Reasoning, Not Just Output

Output correctness is necessary but insufficient. Two agents can produce identical findings — one through deep graph-informed analysis, one through shallow pattern matching. The first will generalize to novel contracts; the second will fail silently.

**Every evaluation must assess HOW the agent arrived at its conclusion, not just WHAT the conclusion was.**

This means:
- Reading transcripts to trace reasoning chains
- Checking whether graph queries informed analysis or were performative
- Verifying evidence grounding (specific node IDs, code locations)
- Assessing hypothesis formation and testing
- Distinguishing genuine reasoning from coincidentally correct output
- **Analyzing temporal reasoning trajectory**: WHEN did the agent form hypotheses relative to queries? Was evidence gathering iterative (exploring) or single-dump (checkbox)? Did reasoning depth increase over time or stay flat? The TranscriptParser already has timestamps — use them.

The Graph Value Scorer (3.1c-04) catches checkbox compliance mechanically. The Reasoning Evaluator (3.1c-07) catches everything else through Opus-powered assessment (Opus everywhere, no cost constraints).

**Reasoning chain decomposition** goes beyond holistic scoring to per-move assessment. Evaluation decomposes each agent's reasoning into discrete reasoning moves, evaluates each move independently, and produces a reasoning move profile showing which specific reasoning skills are strong and weak. Seven move types are tracked:

- `HYPOTHESIS_FORMATION`: Agent explicitly states what vulnerability it expects to find and why
- `QUERY_FORMULATION`: Agent constructs a specific, targeted graph query
- `RESULT_INTERPRETATION`: Agent reads query results and extracts meaningful information
- `EVIDENCE_INTEGRATION`: Agent connects multiple pieces of evidence into a coherent picture
- `CONTRADICTION_HANDLING`: Agent encounters unexpected results and adjusts its approach
- `CONCLUSION_SYNTHESIS`: Agent derives specific, well-supported findings from accumulated evidence
- `SELF_CRITIQUE`: Agent questions its own reasoning or identifies gaps

Each move is scored independently (0-100) on quality. The aggregate produces a reasoning move profile — a radar chart of strengths and weaknesses per workflow. This enables precise metaprompting: instead of "improve graph utilization" (vague), the system generates "query formulation is fine (85) but evidence integration is weak (35) — the agent runs good queries but ignores the results. Add explicit 'cite query results in conclusions' instruction."

**Cascade-aware evaluation scoring** recognizes that the 7 reasoning moves form a directed acyclic graph with causal dependencies: HYPOTHESIS_FORMATION → QUERY_FORMULATION → RESULT_INTERPRETATION → EVIDENCE_INTEGRATION → [CONTRADICTION_HANDLING] → CONCLUSION_SYNTHESIS → SELF_CRITIQUE. When an upstream move fails, downstream moves are "cascade-blocked" — they may score poorly not due to their own weakness but because they received corrupted input. The cascade-aware scorer uses three modes: (1) Hard blocking for strict dependencies (score=0 if prerequisite failed), (2) Soft blocking for degradable dependencies (score proportional to prerequisite health), (3) Attribution mode that classifies each low score as either "root cause" (failed independently) or "cascade victim" (failed due to upstream failure). Root cause identification directly feeds metaprompting: instead of improving all 7 moves, the system targets only the root causes. If QUERY_FORMULATION is the root cause, fixing it may automatically resolve RESULT_INTERPRETATION, EVIDENCE_INTEGRATION, and CONCLUSION_SYNTHESIS without additional prompt changes. SELF_CRITIQUE is a cross-cutting move with multiple entry points — it can succeed even when upstream moves fail (detecting the failure IS good self-critique), so it is never hard-blocked. This approach — proven optimal by PRISM-Physics ancestor closure scoring (Stanford/ICLR 2026) — prevents the common evaluation failure of treating symptoms as causes.

### Pillar 2: Smart Selection Over Blanket Application

Not every workflow needs every evaluation component. The smart selection matrix maps workflow categories to evaluation dimensions:

- **Investigation workflows** (attacker, defender, verifier): Tool use hooks (PreToolUse/PostToolUse), graph scoring, deep reasoning evaluation, Stop debrief. No SubagentStart/Stop hooks (single-agent).
- **Tool integration workflows** (slither, aderyn): Tool use hooks, standard reasoning evaluation, no graph scoring, no debrief blocking
- **Orchestration workflows** (audit, verify, debate): Agent lifecycle hooks (SubagentStart/Stop), coordination evaluation + cross-agent coherence scoring, multi-agent debrief via SendMessage, graph scoring optional (MAYBE per contract)
- **Support workflows** (health-check, bead-*): Minimal hooks (none by default), lite reasoning evaluation, deterministic checks only

Applying Graph Value Score to a health-check skill produces meaningless noise. Applying SubagentStart/Stop hooks to a single-agent workflow produces false negatives. Smart selection eliminates both.

Every evaluation contract (3.1c-06) specifies exactly which components apply. **51 per-workflow contracts**, not 24 category-level ones. Each workflow gets its own specification.

**Testing Tiers** (all workflows get reasoning evaluation):
- **Core** (~10 workflows): Full evaluation depth — GVS, deep reasoning evaluator, debrief, ground truth comparison, meta-evaluation, contrastive calibration, scenario difficulty scaling
- **Important** (~15 workflows): Standard evaluation — reasoning evaluator + deterministic checks + ground truth comparison
- **Standard** (~26 workflows): Lite evaluation — reasoning evaluator (focused template) + deterministic checks

**No workflow is excluded from reasoning evaluation.** The old "Mechanical" tier (capability-only, no LLM evaluation) is eliminated. Cost is not a constraint. Even "simple" workflows can have subtle quality issues that only LLM evaluation catches.

**Adaptive tier promotion**: Tiers are dynamic, not static. The `evaluation_tier` field is mutable, with `tier_history` tracking every transition. Promotion rules (automatic, no human approval needed):
- Standard → Important: If reasoning evaluation score drops below 40 on any dimension for 3 consecutive runs — consistent low scores indicate the workflow has problems that lite evaluation cannot diagnose.
- Important → Core: If meta-evaluation shows inter-rater disagreement > 15 points on 2+ dimensions for 2 consecutive runs — the evaluator cannot agree on what's happening, deeper scrutiny is needed.
- Any tier → Core (emergency): If the failure mode catalog flags a new failure pattern affecting this workflow with severity > HIGH — new failure patterns need the deepest investigation.

Demotion suggestions (require human approval):
- Core → Important: All dimensions score 90+ for 10 consecutive runs AND meta-evaluation agreement > 95%. Generate a demotion proposal for human review.
- Important → Standard: All dimensions score 85+ for 15 consecutive runs. Generate a demotion proposal.
- Demotions are NEVER automatic — humans approve because reducing scrutiny is a risk decision.

Tier history is tracked per workflow with: timestamp, reason, triggering scores, approver (system for promotions, human for demotions). This history is queryable and appears in the failure reporter output.

**Signal-appropriate evaluation depth** ensures the right level of scrutiny at every stage. Three evaluation depth levels operate: Shallow (structural, deterministic — transcript format validation, score extraction, fingerprint delta computation), Standard (full LLM-powered dimensional scoring, reasoning decomposition), and Deep (meta-evaluation, counterfactual analysis, full debrief). Shallow evaluation runs on EVERY execution — it catches structural failures (crashes, missing output, format violations) immediately with zero LLM calls, catching ~60% of regressions. Standard evaluation is the default for scheduled runs — full dimensional scoring and reasoning move profiling. Deep evaluation triggers automatically on: score regression, new/modified workflow, shallow anomaly detection, or human request — it adds meta-evaluation and counterfactual analysis for thorough root cause diagnosis. This is about signal quality, not cost: shallow checks free evaluator attention for genuine quality assessment, while deep evaluation is reserved for when the investment in thorough analysis actually produces actionable insight. The tier manager can upgrade evaluation depth dynamically — a workflow flagged by shallow evaluation gets immediate Standard or Deep analysis.

### Pillar 3: Capability THEN Evaluation

Every test runs in two stages:

1. **Capability contract check** (HDG-10): Binary pass/fail. Did the workflow satisfy its preconditions and postconditions? Did it use required tools? Did it produce valid output? Did it respect role constraints?

2. **Reasoning evaluation**: Scored assessment. HOW WELL did it reason? How genuinely did it use the graph? How well-grounded was the evidence? How specific were the conclusions?

Stage 2 runs ONLY if stage 1 passes. There is no point evaluating reasoning quality if the workflow crashed or violated its contract.

This two-stage approach prevents a common testing failure: scoring a broken workflow's reasoning and getting meaningless numbers.

### Pillar 4: Safe Improvement with Regression Detection

The framework's purpose is not just measurement — it is improvement. But improvement must be safe.

**Safe sandboxing (ABSOLUTE RULE):**
- NEVER modify production `.claude/` paths
- PREFERRED: Use Jujutsu workspace isolation (`jj workspace add/forget`) for atomic rollback and concurrent experiments (from 3.1b-04)
- FALLBACK: Copy to `.claude.sandbox/`, modify there, test there, delete after
- Human approves any change before it touches production
- No exceptions, regardless of confidence level

**Regression detection (MANDATORY):**
Scores are 0-100 per dimension. Thresholds are **tier-weighted**:
- Every prompt change requires before/after score comparison
- **Core workflows:** >10 point drop = REJECT, >5 point drop = WARN
- **Important workflows:** >15 point drop = REJECT, >10 point drop = WARN
- **Standard workflows:** >25 point drop = REJECT, >15 point drop = WARN
- Improvement < 3 points on target dimension -> not worth the risk
- Score history tracked across iterations for convergence detection

**Parallel prompt exploration**: During the improvement loop, run 3-5 prompt variants in parallel instead of sequential iterate-and-test. Select the best-performing variant. With no cost constraints, parallel exploration is strictly better.

**Cross-workflow learning**: When the improvement loop discovers a successful prompt fix, it automatically tests whether the same fix helps related workflows. A workflow similarity graph maintains edges between workflows based on: shared evaluation dimensions, same agent category, overlapping tool usage patterns, and historical co-improvement (edges strengthen when fixes transfer successfully). Before propagating a fix, the system attempts to abstract it from workflow-specific to category-level — for example, "Add 'MUST query BSKG before conclusions' to vrs-attacker.md" abstracts to "Add graph-first enforcement to investigation agent prompts." The abstract version is tested first; if it works, it is applied to all matching workflows at once. Every propagation produces a report: which workflows received the fix, which benefited, which did not, and the abstracted version. This compounds fix value: one fix cycle benefits N related workflows.

**Evaluator self-improvement**: When meta-evaluation detects persistent inter-rater disagreement (> 15 points on a dimension for 3+ consecutive evaluations), the system generates 3-5 evaluator prompt variants targeting the ambiguous dimension. Variants are tested against anchor transcripts (from contrastive pairs where the good/bad distinction is obvious). The variant that maximizes inter-rater agreement while preserving discrimination is selected. This loop is bounded to 3 iterations per dimension per improvement cycle — if 3 rounds do not achieve > 80% inter-rater agreement, the dimension is flagged for human review with full diagnostic info. Human approval is required before any evaluator template change is deployed. This prevents the recursive self-improvement trap (improving the evaluator to evaluate the evaluator to evaluate the evaluator...).

**Self-describing failure narratives** turn every scored dimension into an improvement signal. Every scored dimension produces a paired output: "what happened" (extracted from transcript) and "what should have happened" (generated by the evaluator as a concrete counterfactual). Example: "QUERY_FORMULATION scored 35/100. Actual: Agent queried 'functions with external calls' (too broad, 47 results). Ideal: Agent should have queried 'functions calling untrusted addresses without reentrancy guards' (specific to hypothesis about reentrancy in withdraw())." These narrative pairs are the primary training signal for metaprompting — not just "score was low" but "here's the specific behavioral delta." The metaprompting engine uses the ideal behavior description to generate targeted prompt instructions. Failure narratives accumulate in the failure mode catalog with their corresponding ideal behaviors. Over time, this builds a library of "what good looks like" per dimension per workflow category — making each improvement cycle more precise. Self-describing failures make the improvement loop self-documenting: anyone can read the narrative pairs and understand both the problem and the target behavior without needing to parse raw transcripts.

The improvement loop is what makes this framework a living system instead of a one-time gate.

### Pillar 5: Scores Are Internal Signals, Not Quality Metrics

Evaluation scores (0-100 per dimension) are **internal regression signals**. They answer: "Did this change make things better or worse?"

They are NOT:
- Product quality certifications ("our tool scores 85/100!")
- Customer-facing metrics
- Threshold-based pass/fail gates
- Comparable across different workflow categories

Scores enable before/after comparison. That is their only purpose. A score of 45 today that becomes 55 tomorrow tells you the prompt improvement worked. The absolute number 45 tells you nothing useful in isolation.

**Reasoning fingerprinting** tracks behavioral consistency beyond absolute scores. For each workflow, the framework computes a statistical profile from the last 20+ runs across multiple dimensions: query patterns (count, type distribution, complexity, query-to-conclusion ratio), temporal profile (time in each reasoning phase, hypothesis-formation timing), reasoning move distribution (relative frequency of each move type), tool usage pattern (call frequency, order, count per run), and output characteristics (finding count, evidence citations per finding, conclusion length distribution). Each dimension is stored as (mean, stddev, min, max) from historical data. Anomaly detection uses Mahalanobis distance to catch subtle behavioral drift that score-based regression misses:

- **Mild anomaly** (z-score 2-3): Log for observation, no action.
- **Significant anomaly** (z-score > 3): Flag for investigation.
- **Pattern shift** (3+ consecutive mild anomalies): Trigger fingerprint update with human approval.
- **Positive anomaly** (deviation with significantly higher scores): Flag as a potential breakthrough for human review — the agent may have discovered a better reasoning approach.

Fingerprints are updated periodically (after every 10 runs or after a prompt change). Old fingerprints are archived for comparison, enabling tracking of how an agent's behavior evolves over time.

**Reproducibility index** measures evaluation stability per dimension. Some evaluation dimensions are inherently noisy — LLM scoring varies across identical inputs. The reproducibility index quantifies this variance by running the same transcript through the same evaluator 3 times and measuring score variance. Dimensions with variance > 15 points are flagged as "noisy." Noisy dimensions require larger score deltas before triggering improvement actions: a 5-point drop on a reproducible dimension (variance < 5) is meaningful, while a 5-point drop on a noisy dimension (variance > 15) is just noise. The contract healer uses reproducibility data to flag dimensions that need better rubrics — high variance indicates ambiguous evaluation criteria, feeding into evaluator self-improvement where high-variance dimensions get priority for rubric tightening. Reproducibility is tracked over time: if a dimension becomes more reproducible after an evaluator prompt change, that change is validated; if it becomes noisier, roll back.

**Model migration protocol** handles the inevitable shifts when the underlying model changes (new Claude version, provider update). Without a migration protocol, all fingerprints, baselines, and behavioral expectations shift simultaneously — the fingerprinter flags everything as anomalous, the tier manager promotes everything, and the improvement loop generates spurious recommendations. The protocol detects model changes via run metadata and enters a "migration mode" that disables auto-promotion, anomaly alerts, and the improvement loop. A calibration suite of 10-15 representative workflows across tiers runs to compute the systematic delta between model versions. The delta is applied to historical expectations (not raw scores) — adjusting what "normal" looks like for the new model. After calibration, the system exits migration mode and resumes normal operation with updated baselines. Model migration is an expected event, not an error. The protocol ensures continuity of evaluation quality across model transitions without manual recalibration.

---

## What "Done" Looks Like for Each Plan

| Plan | The Question |
|------|-------------|
| 3.1c-01 | Do Pydantic models for all evaluation types (including MetaEvaluationResult, CoherenceScore, DifficultyProfile, TemporalAnalysis) serialize cleanly and reject invalid data? |
| 3.1c-02 | Do all 6 observation hooks + 2 debrief hooks fire and write valid JSONL to `.vrs/observations/`? |
| 3.1c-03 | Does the parser transform raw JSONL into a structured `ObservationSummary` with temporal reasoning trajectory for all event types? |
| 3.1c-04 | Does the scorer distinguish checkbox compliance (< 30) from genuine graph use (> 70), calibrated with 30+ labeled transcripts? |
| 3.1c-05 | Is there a working approach to ask agents WHY they made choices? (Research outcome documented honestly) |
| 3.1c-06 | Do 51 per-workflow evaluation contracts exist, each tailored per smart selection matrix? |
| 3.1c-07 | Does the dual-Opus evaluator (meta-evaluation) produce specific, actionable assessments with inter-rater agreement checks? |
| 3.1c-08 | Does the runner orchestrate the full pipeline: observe -> parse -> score -> dual-evaluate -> persist? |
| 3.1c-09+10+11 | Are all 51 shipped workflows tested with capability contracts AND reasoning evaluation, including difficulty scaling for Core tier? (Merged plan, three parallel suites) |
| 3.1c-12 | Is the regression baseline established with tiered thresholds, contrastive calibration, failure mode catalog, and parallel prompt improvement loop? |

### Execution Waves (~35% faster planning)

```
Wave 1: [3.1c-01] Models  +  [3.1c-06] Contracts     (zero dependencies)
Wave 2: [3.1c-02] Hooks   +  [3.1c-03] Parser         (depend on 01)
Wave 3: [3.1c-04] GVS     +  [3.1c-05] Debrief        (depend on 02/03)
Wave 4: [3.1c-07] Evaluator                            (depends on 04/05/06)
Wave 5: [3.1c-08] Runner                               (depends on 07)
Wave 6: [3.1c-09+10+11] Merged Test Suite              (depends on 08)
Wave 7: [3.1c-12] Improvement Loop + Baseline          (depends on 09+10+11)
```

> **CRITICAL EXECUTION CONSTRAINT:** Wave parallelism is for dependency understanding and planning ONLY. Execution is strictly sequential because plans 3.1c-09+10+11 and 3.1c-12 spawn Agent Teams, which cannot run from subagents. Execution order: 01 → 06 → 02 → 03 → 04 → 05 → 07 → 08 → 09+10+11 → 12. Each plan executes in a top-level Claude Code session, NOT via subagent. Planning CAN use subagents (plans are just documents). But every generated plan's "Execution Notes" section MUST state: "Execute in top-level session, NOT via subagent."

---

## Alignment Rules for Every Plan

### Rule A: Serve the Loop

Every plan must serve the Test -> Evaluate -> Improve -> Re-test loop. If a plan produces artifacts that no other plan consumes, or that don't feed back into the loop, it is misaligned.

The dependency chain (wave-parallel planning):
```
Wave 1: Models (01) ----+----> Hooks (02) ----> Scorer (04) ----+
         Contracts (06) -+----> Parser (03) --> Debrief (05) ---+
                                                                 |
                              Evaluator (07) <------------------+
                              [dual-Opus meta-evaluation]
                                     |
                               Runner (08)
                                     |
                     Merged Test Suite (09+10+11)
                     [difficulty scaling]
                     [cross-agent coherence]
                                     |
                     Improvement Loop + Baseline (12)
                     [contrastive calibration]
                     [failure mode catalog]
                     [parallel prompt variants]
```

Every plan either produces data for downstream plans or consumes data from upstream plans. Orphan plans don't belong here.

### Rule B: Two-Stage Testing

Every skill/agent/orchestrator test (3.1c-09, 10, 11) MUST run:
1. Capability contract checks FIRST (binary pass/fail)
2. Reasoning evaluation ONLY IF capability passes

No exceptions. No "skip capability, just evaluate." No "evaluate even though it crashed."

**Ground truth validation gate**: Before using ground truth YAML for evaluation, validate it. Verify the expected reasoning chain is actually valid (not stale logic). Check for stale references (node IDs, file paths that no longer exist in the codebase). Confirm the vulnerable contract still exhibits the vulnerability (compile and verify). Bad ground truth silently corrupts evaluation quality — a validation gate catches stale or incorrect ground truth before it enters the evaluation pipeline.

### Rule C: Evaluation Contracts Are the Source of Truth

The **51 per-workflow evaluation contracts** (3.1c-06) are the central specification. Every downstream test must:
- Load the correct contract for the specific workflow being tested
- Enable ONLY the hooks specified in the contract
- Evaluate ONLY the dimensions specified in the contract
- Track regression ONLY on the signals specified in the contract
- Apply tier-weighted regression thresholds

If a test evaluates dimensions not in the contract, or skips dimensions that are, it is misaligned.

### Rule D: Anti-Fabrication Is Active

The framework MUST detect and flag fabricated results at TWO levels:

**Level 1 — Static triggers (per-run):**
- 100% pass rate -> investigation, not celebration
- Identical outputs across all runs -> investigation
- All evaluation scores at 100 -> investigation
- No meaningful variance in scores -> investigation
- Duration < 5s for complex workflows -> investigation
- Transcript < 500 chars per agent -> investigation

**Level 2 — Adversarial diversity analysis (cross-run):**
- Run N executions of the same workflow
- Compute cosine similarity of reasoning chains across runs
- If reasoning chains are suspiciously similar (high similarity despite different execution contexts), flag for investigation
- This catches subtle fabrication where outputs LOOK different but follow identical reasoning patterns
- Diversity analysis is applied to Core and Important tier workflows

These are not paranoid checks. They are necessary because LLM-based testing can produce convincingly fake results. The anti-fabrication rules are as important as the evaluation itself.

### Rule E: Human Has Final Word

The framework supports human reasoning, it does not replace it.
- Scores are suggestions, not verdicts
- Prompt improvements are proposals, not automatic deployments
- Regression alerts are notifications, not automatic rollbacks
- The improvement loop proposes; the human disposes

This is not a weakness. It is the design. LLM evaluation is valuable but imperfect. Human judgment catches what automated evaluation misses.

### Rule F: Honest Research

3.1c-05 (Debrief Protocol) — research is COMPLETE (Research Spike 02, 2026-02-11). Four-layer strategy verified. The rule for research remains:
- If it works, document how and why
- If it doesn't work, document what was tried and why it failed
- NEVER claim success without evidence
- ALWAYS document alternatives for future attempts
- ALWAYS check 3.1b-04's debrief research findings before starting (findings at `.vrs/debug/phase-3.1b/research/hook-verification-findings.md`)

Honest "the blocking approach doesn't work, but orchestrator-level debrief does" is infinitely more valuable than optimistic "blocking works (with workarounds that sometimes fail silently)."

### Rule G: Validation Artifacts Are Mandatory

No plan is complete without:
1. **Machine Gate Report**: `.vrs/debug/phase-3.1c/gates/<plan-id>.json`
2. **Human Checkpoint Record**: `.vrs/debug/phase-3.1c/hitl/<plan-id>.md`
3. **Drift Log Entry**: `.vrs/debug/phase-3.1c/drift-log.jsonl`

### Rule H: Cross-Agent Coherence Is Measured

For ALL orchestrator flows (3.1c-09+10+11 orchestration tests), evaluation MUST include cross-agent coherence metrics:
- Did the attacker's findings inform the defender's analysis? (evidence flow)
- Did the verifier reference BOTH sides of the debate? (synthesis completeness)
- Did evidence flow between agents or did they operate in silos? (coordination quality)
- A team where each agent scores well individually but produces no emergent insight is a FAILURE

Individual agent scores are necessary but insufficient. The coherence score catches the failure mode where agents work in parallel isolation rather than genuine collaboration.

### Rule I: Failure Modes Are Cataloged

The framework MUST maintain a living `failure-modes.yaml` catalog:
- Every discovered failure pattern gets an entry (e.g., "shallow graph use after compaction", "evidence fabrication under time pressure", "role confusion in multi-agent")
- Each entry tracks: frequency, severity, which prompt fixes worked, which made it worse, first/last seen dates
- The catalog is the institutional memory of the testing framework
- 3.1c-12 manages the catalog; all downstream phases (4.1, 6) inherit it
- The catalog informs metaprompting: known failure patterns get targeted prompt fixes

### Rule J: Meta-Evaluation Validates the Evaluator

The Reasoning Evaluator itself must be validated:
- TWO independent Opus evaluator subagents score the same transcript
- Inter-rater agreement is measured per dimension
- Disagreement > 15 points on any dimension = unreliable evaluation, flagged for human review
- This catches evaluator prompt bugs, scoring inconsistencies, and dimension ambiguity early
- Meta-evaluation runs on ALL Core tier workflows and a random sample of Important tier

### Rule K: Evaluation Contracts Self-Heal

Evaluation contracts are not static specifications — they are living documents subject to statistical anomaly detection. After every evaluation run, the contract healer computes per-dimension statistics across the last N runs and flags problems:

- **Score ceiling detection:** mean > 92 AND stddev < 5 — dimension is trivially easy, flag for tightening
- **Score floor detection:** mean < 20 AND stddev < 8 — dimension may be unreasonable, flag for review
- **Zero variance detection:** stddev < 2 across 10+ runs — dimension is not discriminating
- **Bimodal detection:** scores cluster at two extremes (< 30 or > 80, nothing in between) — dimension may be measuring something binary that should be a capability check, not a scored dimension
- **Meta-evaluation alignment cross-reference:** persistent disagreement (> 15 points) on the SAME dimension across multiple workflows — the dimension definition is ambiguous in the prompt template
- **Failure catalog cross-reference:** failure mode flagged > 5 times but human review overturns it > 60% of the time — detection criteria are too aggressive, propose relaxation

For each detected issue, the system generates a contract improvement proposal: what to change, why (supporting statistics), risk assessment, and test plan. Proposals go to a human review queue (`.vrs/evaluation/contract-proposals/`). They are NEVER auto-applied — changing what "good" means requires human judgment.

**Contract versioning** ensures historical data remains comparable as contracts evolve. Evaluation contracts evolve — dimensions get added, rubrics get refined, tiers change. Without version tracking, historical data becomes incomparable and trend analysis breaks. Every contract has an explicit version number. When a contract changes, the migration record specifies: renamed dimensions, split dimensions, dropped dimensions, added dimensions, and changed rubrics. During the transition, BOTH old and new contract versions run for N=5 transition runs. This produces a calibration mapping between old and new scores, ensuring trend continuity across versions. Historical trend data carries forward: the calibration mapping translates old scores to new-version equivalents, so regression detection works across contract boundaries. Contract version history is queryable — you can always trace what "good" meant at any point in time.

### Rule L: Coverage Gaps Are Visible

The framework maintains a live coverage heat map across four axes:

- **Vulnerability class coverage:** VulnDocs categories (reentrancy, access control, oracle manipulation, flash loan, etc.) vs test scenarios that exercise them
- **Semantic operation coverage:** Semantic operations exercised by tests (TRANSFERS_VALUE_OUT, CHECKS_PERMISSION, MODIFIES_CRITICAL_STATE, etc.) vs total operations defined
- **Reasoning skill coverage:** Reasoning moves exercised during evaluation (HYPOTHESIS_FORMATION, CONTRADICTION_HANDLING, etc.) vs total move types
- **Graph query pattern coverage:** Query patterns agents actually use during tests vs the full set of supported patterns

Coverage intensity per cell: Hot (green) = well-covered (5+ scenarios). Warm (yellow) = minimal (1-4 scenarios). Cold (red) = zero coverage.

Cold cells are prioritized by: VulnDocs severity (HIGH/CRITICAL patterns get highest priority), skill claims count (multiple skills claiming the capability makes the gap more urgent), and historical incidents (real-world exploits from VulnDocs financial loss data).

The coverage radar feeds directly into the scenario synthesis engine. The radar identifies gaps; the synthesis engine generates scenarios to fill them. Together they form a closed loop: detect gap -> generate scenario -> run scenario -> update radar.

### Rule M: Non-Standard Compositions Are Tested

Production usage will not always follow the standard 3-agent template (attacker + defender + verifier). The framework systematically tests 8 composition variants:

- **Missing agent** (3 variants): attacker+verifier (no defender), defender+verifier (no attacker), attacker+defender (no verifier)
- **Degraded agent** (3 variants): standard team but one agent uses a deliberately weakened prompt (from contrastive pairs) — weak-attacker, weak-defender, weak-verifier
- **Doubled agent**: attacker+attacker+verifier
- **Unusual order**: verifier runs first, then attacker and defender (reversal of normal flow)

Each composition runs the full evaluation pipeline. **Keystone analysis** computes `degradation_impact = baseline_team_score - degraded_team_score` for each degraded-agent variant. The agent with the highest degradation impact is the "keystone" — identifying where prompt improvement investment has the highest ROI.

**Graceful degradation scoring**: For missing-agent compositions, the framework measures what fraction of the standard team's findings are still discovered. If attacker+verifier (no defender) still finds 80% of vulnerabilities, the defender's contribution is 20%. This data informs both architecture decisions and resource allocation.

### Rule N: The Evaluator Is Tested Too

If the improvement loop optimizes agent prompts based on evaluation scores, Goodhart's Law guarantees that agents will eventually learn to game the evaluator — producing outputs that score well without actually being good. Adversarial evaluation resistance is not optional; it is a design requirement.

**Evaluator Stress Testing (EST):** Periodically apply controlled perturbations to agent outputs — remove reasoning structure but keep conclusions, add verbose but empty reasoning, swap evidence citations. If perturbed outputs score within 3 points of originals, the evaluator is not discriminating on substance.

**Fragility detection:** For 10% of evaluation runs, compute `fragility = score(original) - score(perturbed)`. Fragility < 3 points = evaluator is vulnerable to gaming on this output. Track fragility rate over time — if >15% of outputs are fragile, the evaluator rubric needs tightening.

**Canary tests:** Maintain a set of known-bad outputs (gibberish reasoning, fabricated evidence, shallow pattern matching). Run through the evaluator monthly. If any canary scores > 40, the evaluator is compromised.

**Evaluator rotation:** After every 10 optimization iterations of the improvement loop, rotate the evaluator — change prompt templates, update rubrics, or swap judge models. This prevents agents from overfitting to a specific evaluator configuration.

**Detection signals monitored weekly:**
- Score drift: +10%/month without corresponding quality improvement → investigate
- Format convergence: All agent outputs adopt identical phrasing → evaluator rewarding format over content
- Reasoning hollowing: Outputs have structure of good reasoning but shallow content → evaluator not checking depth
- Evidence gaming: Citations exist but don't support claims → graph grounding check failing

The goal is not paranoia — it is calibration confidence. An evaluator that has passed adversarial testing can be trusted. One that hasn't is an assumption.

### Rule O: Counterfactual Replay Validates Causation

When a workflow scores poorly, the improvement loop knows the outcome but not the cause. Was it the prompt? The contract difficulty? The agent composition? The graph quality? Correlation (score dropped after prompt change) is not causation.

**Trajectory recording:** Every evaluation run captures a full trajectory — agent decisions, reasoning, tool calls (including graph queries and their results), intermediate state, and checkpoints at decision boundaries. Trajectories are replayable.

**Counterfactual analysis:** When a failure occurs, the system generates intervention hypotheses and replays the trajectory from the checkpoint before the suspected failure point, with one variable changed:
- Same contract, different prompt → isolates prompt quality
- Same prompt, different contract → measures generalization
- Same everything, different agent composition → measures composition sensitivity
- Same everything, degraded graph → measures graph dependency

**Milestone scoring:** Counterfactuals measure intermediate progress (evidence discovered, queries executed, reasoning moves attempted) — not just final success/failure. An intervention that improves evidence discovery by 200% but doesn't change the final verdict still demonstrates causation.

**Attribution is often ill-posed:** In multi-agent systems, multiple independent interventions can fix the same failure. The goal is not "find THE cause" but "find interventions that demonstrably improve outcomes." Validated improvements matter more than causal purity.

**Research dependency:** Phase 3.1c implements trajectory recording and basic replay infrastructure. Full counterfactual experiments require Phase 3.2+ data accumulation. Initial implementation records trajectories; counterfactual analysis activates when sufficient data exists.

---

## The North Star

Phase 3.1c succeeds when:

1. Every shipped skill and agent has been tested with BOTH capability verification AND reasoning evaluation (ALL tiers, no exclusions)
2. The framework can distinguish good reasoning from bad reasoning (score differential > 20 points), validated by contrastive evaluation
3. The framework can detect checkbox compliance vs genuine graph use (graph scorer < 30 vs > 70), calibrated with 30+ labeled transcripts
4. The improvement loop can safely propose prompt changes (3-5 parallel variants) and detect regressions with tier-weighted thresholds
5. The regression baseline exists with evaluation scores from day 1, including difficulty curves for Core workflows
6. A human reading the evaluation report can understand WHAT failed, WHY it failed, and WHAT to try next — with the failure mode catalog providing historical context
7. The evaluator itself is validated via meta-evaluation with inter-rater agreement checks
8. Cross-agent coherence is measured for orchestrator flows — individual agent quality is necessary but insufficient
9. Temporal reasoning analysis distinguishes hypothesis-first from retrofit reasoning
10. Coverage radar shows > 60% vulnerability class coverage with gap prioritization active
11. No evaluation dimension stuck at ceiling (> 92) or floor (< 20) for 10+ consecutive runs — self-healing contract proposals generated
12. Real-world feedback ingestion pipeline ready for Phase 3.2 outcomes (TP/FP/miss capture, ground truth enrichment, corpus growth)
13. Cascade-aware scoring correctly classifies root causes vs cascade victims (validated against manually-labeled failure transcripts)
14. Adversarial evaluation audit passes: canary tests score < 40, fragility rate < 15%, no format convergence detected
15. Contract versioning preserves trend continuity across at least one contract evolution (calibration mapping validated)

If all fifteen conditions are met, Phase 3.2 (First Working Audit) can begin with confidence that audit quality will be evaluated — not just "did it produce a finding?" but "was the reasoning sound, the evidence well-anchored, the graph queries informative, the temporal reasoning trajectory good, and the multi-agent coordination coherent?"

---

## Anti-Patterns

| Anti-Pattern | Why It's Wrong | What To Do Instead |
|---|---|---|
| Liveness-only testing ("did it crash?") | Misses the most dangerous failure: workflows that run but reason badly | Two-stage: capability THEN reasoning evaluation |
| Blanket evaluation ("run everything on everything") | Produces meaningless scores for dimensions that don't apply | Smart selection per evaluation contract (51 per-workflow contracts) |
| Scores as product quality metrics | Scores are internal signals for regression detection only | Never report absolute scores externally |
| Modifying production prompts automatically | Unsafe, irreversible without human review | Always sandbox, always get human approval |
| Trusting 100% pass rates | Almost certainly fabrication or trivial tests | Static triggers + adversarial diversity analysis |
| Generic evaluation ("overall good performance") | Provides no actionable information | Specific per-dimension assessment with cited observations |
| Skipping capability checks | Evaluating reasoning of a crashed workflow produces garbage | Capability FIRST, evaluation ONLY if capability passes |
| Hardcoding tests for every pattern | 466 patterns, can't maintain hardcoded tests for all | Dynamic generation guidelines (Tier A/B/C templates from 3.1b-06) |
| Evaluating without contracts | No specification of what "good" means | 51 per-workflow evaluation contracts define "good" specifically |
| Excluding workflows from reasoning eval | "Simple" workflows can have subtle quality issues | ALL workflows get reasoning evaluation |
| Ignoring temporal reasoning order | Output-only analysis misses hypothesis-first vs retrofit reasoning | Temporal trajectory analysis on timestamps |
| Trusting a single evaluator | Evaluator prompt bugs produce systematically wrong scores | Dual-Opus meta-evaluation with inter-rater agreement |
| Scoring agents individually in teams | Team coordination failures invisible when agents score well alone | Cross-agent coherence scoring for orchestrator flows |
| Rediscovering the same failures | Same failure modes found and forgotten repeatedly | Living failure-modes.yaml catalog |
| Fixed-difficulty test scenarios | Only reveals if the skill works on the easy case | Difficulty scaling: Tier A/B/C per vulnerability class |
| Improving workflows but never improving the evaluator | The measurement tool degrades silently | Evaluator self-improvement loop (bounded, human-approved) |
| Static tier assignment ignoring behavioral signals | Wastes evaluation budget on easy workflows, under-scrutinizes struggling ones | Adaptive tier promotion/demotion based on scores and meta-evaluation |
| Testing only standard 3-agent compositions | No data on degraded or non-standard behavior | Compositional stress testing: 8 variants + keystone analysis |
| Ignoring coverage gaps ("someone else will test that") | Unknown blind spots persist silently | Coverage radar with live heat map and gap-driven scenario synthesis |
| Treating cascade victims as root causes | Improvement targets wrong reasoning move, wasting prompt changes on symptoms | Cascade-aware scoring with root cause attribution |
| Trusting evaluator without adversarial testing | Goodhart's Law — agents game the evaluator silently | EST fragility checks, canary tests, evaluator rotation |
| Guessing causes of failures instead of testing them | Correlation ≠ causation; intuitive fixes may not address actual root cause | Counterfactual replay with intervention validation |
| Upgrading models without migration protocol | All fingerprints, baselines, and anomaly detection break simultaneously | Model migration protocol with calibration suite |

---

## Relationship to Testing Philosophy

This phase IS the testing philosophy made concrete:

- TESTING-PHILOSOPHY says "Evaluate Reasoning, Not Just Output" -> 3.1c-07 Reasoning Evaluator
- TESTING-PHILOSOPHY says "Smart Selection Over Blanket Application" -> 3.1c-06 Evaluation Contracts
- TESTING-PHILOSOPHY says "Safe Sandboxing" -> 3.1c-12 Improvement Loop sandbox rule
- TESTING-PHILOSOPHY says "Regression Detection is Mandatory" -> 3.1c-12 Regression Baseline
- TESTING-PHILOSOPHY says "Smart Observability" -> 3.1c-02 Selective Hooks
- TESTING-PHILOSOPHY says "Real Execution Only" -> 3.1c-09/10/11 spawn real agents that don't know they're being tested
- TESTING-PHILOSOPHY says "External Ground Truth Only" -> Uses 3.1b-06b corpus with `ground-truth.yaml` containing `expected_reasoning_chain` per pattern. Evaluation contracts can reference ground truth for automated reasoning chain comparison.
- TESTING-PHILOSOPHY says "Evidence-First" -> 3.1c-04 Graph Value Scorer verifies evidence grounding
- TESTING-PHILOSOPHY says "Imperfection is Expected" -> Anti-fabrication checks flag 100% scores

Phase 3.1b builds the infrastructure. Phase 3.1c embodies the philosophy. Together they form the testing framework.

---

## The Continuous Improvement Vision

This phase is not a one-time gate. It establishes a living system:

```
Day 1:  Run all tests, establish baseline with evaluation scores
Day N:  Someone changes a skill prompt
        -> Framework re-evaluates
        -> Compares against baseline
        -> Detects regression (or improvement)
        -> Reports to human with full context
Day N+1: Human reviews, approves or reverts
        -> Baseline updated
        -> Framework gets smarter about what "good" looks like
```

The framework improves over time because:
- Evaluation contracts get refined based on real failure modes (3.1c-12 identifies when dimensions are too easy/too hard; refinement proposed to human)
- Reasoning evaluator prompts get tuned based on evaluation quality (3.1c-12 metaprompting, 3-5 parallel variants per iteration)
- Debrief questions get better based on what produces actionable insight (3.1c-12 debrief-driven feedback)
- Anti-fabrication rules get updated based on discovered evasion patterns (static triggers + adversarial diversity analysis, evolution tracked in drift log)
- **Failure mode catalog** accumulates institutional memory — which failures occur, how often, which fixes work
- **Contrastive calibration** provides concrete good/bad examples that sharpen evaluator discrimination
- **Meta-evaluation** catches evaluator drift — the evaluator's own quality is tracked over time
- **Difficulty curves** reveal capability ceilings — how far each skill can reason before quality degrades
- **Coverage radar** discovers gaps -> scenario synthesis fills them -> radar updates -> gaps shrink over time
- **Cross-workflow learning** compounds fix value: one fix cycle benefits N related workflows
- **Reasoning fingerprints** detect behavioral drift before scores drop — an early warning system
- **Real-world audit outcomes** (Phase 3.2+) sharpen synthetic evaluation calibration — the framework gets better from production usage
- **Cascade-aware scoring** pinpoints root causes → metaprompting targets actual weaknesses → fewer wasted improvement cycles
- **Adversarial audits** maintain evaluator calibration → trusted scores → trustworthy improvement decisions
- **Counterfactual replay** validates causal hypotheses → improvement loop makes data-driven changes, not guesses
- **Self-describing failure narratives** build a library of "what good looks like" → each improvement cycle starts with more precise target behaviors

This is not aspirational. It is the design. 3.1c-12 establishes the first iteration of this loop. Every plan must contribute to this living system, not just produce a snapshot.
