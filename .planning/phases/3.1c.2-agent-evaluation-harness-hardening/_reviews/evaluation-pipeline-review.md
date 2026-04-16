# Evaluation Pipeline Review: Phase 3.1c.2 Plans 02-05

**Reviewer:** Evaluation Pipeline Architect
**Date:** 2026-03-02
**Scope:** Plans 02-05 of Phase 3.1c.2 — from transcript capture to verdict
**Confidence:** HIGH (all source files read, all plan docs analyzed, framework spec cross-referenced)

---

## A. Pipeline Stage Coverage

The TESTING-FRAMEWORK.md defines a 9-stage evaluation pipeline vision. Below is how Phase 3.1c.2 Plans 02-05 map to each stage.

| # | Pipeline Stage (Framework Vision) | 3.1c.2 Delivers | Gap Analysis |
|---|---|---|---|
| 1 | **Hooks observe** (selective per eval contract) | Plan 01 (delegate_guard_config_eval.yaml) provides enforcement hooks. SubagentStop hook captures `agent_transcript_path`. | **PARTIAL.** Hook *enforcement* is delivered but hook *selectivity per evaluation contract* is not. The framework vision calls for each evaluation contract YAML to declare which hooks are enabled. 3.1c.2 applies the same guard config to all evaluation sessions. There is no per-contract hook selection matrix. |
| 2 | **Transcript captured** (full session JSONL) | Plan 02 (CLIAttemptState + JSONL parsing via TranscriptParser). `obs_agent_stop.py` already captures `agent_transcript_path`. | **DELIVERED.** Transcript capture is functional. The SubagentStop hook provides reliable per-teammate paths. TranscriptParser already extracts tool_use events. |
| 3 | **Evaluation contract loaded** (smart selection matrix) | Not addressed by Plans 02-05. Contract loading exists in `evaluation_runner.py` Stage 2 (`load_contract`), but it was built in 3.1c Plans 01-08 (pre-existing). | **GAP.** 3.1c.2 does not create or modify evaluation contracts. The 24 per-workflow contracts (EVAL-05) are downstream. Plans 02-05 build infrastructure that contracts will *depend on* but do not deliver the contracts themselves. |
| 4 | **Deterministic checks** (category-specific assertions) | Plan 02 (check 13: CLIAttemptState). Plan 03 (ground truth for stats comparison). Plan 04 (integrity check wired into runner). | **DELIVERED.** The validator now has 13 checks covering: session duration, graph stats, knowledge leakage, fabricated identifiers, finding uniformity, query count, cross-file similarity, worktree isolation, ground truth comparison, and CLIAttemptState. These are deterministic, category-specific, and repeatable. |
| 5 | **Graph Value Score** (mechanical graph quality scoring) | Not modified by 3.1c.2. GVS exists in `GraphValueScorer` (from 3.1c Plan 04) and is called in evaluation_runner.py Stage 5. | **DELIVERED (pre-existing).** No gap from 3.1c.2. However, the GVS currently does not consume ground truth stats.json to calibrate its scoring. See Improvement 1 below. |
| 6 | **LLM Reasoning Evaluator** (per-category prompt templates) | Not modified by 3.1c.2. `ReasoningEvaluator` exists (from 3.1c Plan 07), called in evaluation_runner.py Stage 6. | **DELIVERED (pre-existing).** No gap from 3.1c.2. The reasoning evaluator receives debrief data as input. Plan 05's debrief persistence does not change the evaluator's input contract. |
| 7 | **Debrief** (agent interview post-session) | Plan 05 (Stage 9 wiring: debrief persistence as `debrief.json`). The debrief protocol itself is pre-existing (from 3.1c Plan 05). | **MOSTLY DELIVERED.** Plan 05 correctly wires the existing 4-layer debrief cascade into the evaluation pipeline. However, it is a *persistence* stage, not an *enhancement* stage. The debrief call itself happens in Stage 6 (before reasoning evaluation) and is unchanged. See Section D for detailed gap analysis. |
| 8 | **Improvement suggestions** (failure -> prompt fix mapping) | Not addressed by 3.1c.2. This is 3.1c.3 (Evaluation Intelligence Bootstrap) scope. | **GAP (intentional).** 3.1c.2 is a hardening phase. The improvement loop is explicitly deferred to 3.1c.3. No violation of phase boundary. |
| 9 | **Regression detection** (before/after score comparison) | Not addressed by 3.1c.2. Regression detection requires baseline history and score comparison logic. | **GAP (intentional but concerning).** While the CONTEXT.md notes that integrity pipeline is a "PREREQUISITE for EVAL-07 (regression detection) but does not satisfy EVAL-07 itself," the auto-REJECT mechanism in Plan 04 effectively creates a binary regression gate (FAIL -> rejected). There is no *graduated* regression detection (e.g., score dropped 10 points). This is a downstream concern, but the lack of any connection between integrity verdicts and regression baselines means the integrity system operates in isolation from the improvement loop. |

### Coverage Summary

| Delivered | Partially Delivered | Intentional Gap | Unintentional Gap |
|---|---|---|---|
| Transcript capture, Deterministic checks, GVS (pre-existing), Reasoning evaluator (pre-existing), Debrief wiring | Hook observability (enforcement only, no per-contract selectivity) | Improvement suggestions, Regression detection | Hook selectivity matrix |

**Overall pipeline coverage: 5/9 stages fully covered, 1 partial, 3 gaps (2 intentional).**

---

## B. Integrity Check Design Review

### B.1. Check Coverage Analysis

The validator has checks 1-6 (per-file) + cross-file checks + ground truth comparison + check 13 (CLIAttemptState). Here is how they map to the Plan 12 Batch 1 failure modes:

| Check | Name | FM-1 (CLI returns 0) | FM-2 (Shared graph) | FM-3 (Python import) | FM-4 (Context leak) | Other |
|---|---|---|---|---|---|---|
| 1 | session_duration | | | | | Plausibility |
| 2 | graph_stats | | PARTIAL | | | Plausibility |
| 3 | knowledge_leakage | | | | YES | Isolation |
| 4 | fabricated_identifiers | | | | | Fabrication |
| 5 | finding_uniformity | | | | | Fabrication |
| 6 | query_count (zero=critical) | YES | | PARTIAL | | Usage |
| 7 | cross_file_similarity | | | | | Cross-agent |
| 8 | worktree_isolation | | YES | | | Isolation |
| GT | graph_stats_vs_ground_truth | | YES | | | Accuracy |
| 13 | cli_attempt_state | | | YES | | Transcript |

**Failure modes still not covered:**

1. **FM-1 (CLI returns 0 results) is only partially detected.** Check 6 catches `queries_executed == 0` as critical but does NOT catch `queries_executed > 0 with all empty results`. An agent could claim `queries_executed: 4` but every query returned zero matches. The CLIAttemptState (check 13) catches this at the transcript level (`ATTEMPTED_FAILED`), but it's classified as WARNING, not CRITICAL. This means an agent that tries CLI but always gets empty results (because the query is too generic or the graph is wrong) gets a WARNING rather than an actionable signal.

2. **FM-2 (Shared graph state) detection is indirect.** Check 2 detects implausible node counts. The ground truth comparison detects >30% deviation. But neither directly detects the failure mode: Agent A builds a graph, Agent B queries Agent A's graph instead of building its own. The worktree check (8) is a proxy, not a direct detection. If agents share a graph path but are in separate worktrees, check 8 passes but the graph contamination still occurs.

3. **No check detects FABRICATED QUERY RESULTS.** An agent could fabricate the content of query results (e.g., invent node IDs that look real) without triggering any check. Check 4 detects fabricated *identifiers* in the observation file, but if the agent writes fabricated identifiers into the *transcript* (which is what the JSONL records), those are not cross-referenced against ground truth graph nodes. This is a gap between what the transcript records and what the validator checks.

### B.2. CLIAttemptState Enum Completeness

The current enum has 4 states:

```python
ATTEMPTED_SUCCESS     # CLI called, got results
ATTEMPTED_FAILED      # CLI called, error/empty
NOT_ATTEMPTED         # No CLI calls in transcript
TRANSCRIPT_UNAVAILABLE # JSONL not found/empty
```

**Missing states:**

| Proposed State | Scenario | Why It Matters |
|---|---|---|
| `ATTEMPTED_PARTIAL` | Some queries succeeded, some failed (currently mapped to `ATTEMPTED_SUCCESS`) | Collapsing mixed results into SUCCESS loses diagnostic signal. If 1 of 5 queries succeeds, the agent's analysis quality is degraded but the state says "success." The severity mapping should distinguish 1/5 from 5/5. |
| `BYPASSED_WITH_PYTHON` | Transcript contains both `alphaswarm query` and `python -c "import alphaswarm"` calls | An agent could use CLI for compliance AND Python imports for real analysis. The current enum would return `ATTEMPTED_SUCCESS` because CLI queries exist, masking the Python import fallback. This requires cross-checking with delegate_guard blocked patterns. |
| `BUILD_ONLY` | Agent ran `build-kg` but never ran `query` | Graph was built but never queried. The agent completed the mechanical step but didn't use the graph for analysis. Currently classified as `ATTEMPTED_SUCCESS` if build-kg alone counts as a BSKG query event. |

**Recommendation:** Add `ATTEMPTED_PARTIAL` as a distinct state with severity `warning`. The `BYPASSED_WITH_PYTHON` case should be caught by delegate_guard at runtime (Plan 01) and is less critical for post-session forensics. The `BUILD_ONLY` case should be distinguished in `compute_cli_attempt_state()` by checking whether `get_bskg_queries()` returns only `build-kg` events vs. actual `query` events.

### B.3. Auto-REJECT Threshold Analysis

Plan 04 defines: `verdict == "FAIL"` -> auto-REJECT. The verdict is FAIL if any critical violation exists.

**Current graduated responses:**

| Verdict | Meaning | Response |
|---|---|---|
| PASS | No violations | Results trusted |
| DEGRADED | Warnings only | Results trusted (no action) |
| FAIL | Any critical violation | Auto-REJECT + rejection.json |

**Problem: DEGRADED is a dead zone.** Multiple warnings (3+ knowledge leakage terms, uniform confidence across findings, no edges in graph, excessive queries, worktree check failed) all produce DEGRADED but take no action. This means an observation file with 5 warnings of different types is treated the same as one with 0 warnings -- both proceed to baseline update.

**Recommendation:** Introduce a `WARNING_THRESHOLD` (e.g., 3 warnings -> escalate to FAIL). Alternatively, introduce a `DEGRADED` response that: (a) permits the results but (b) adds a metadata flag `"degraded": true` that downstream consumers (improvement loop, regression detection) can use to weight the results lower. The current binary PASS/FAIL loses the graduated signal that warnings provide.

**Secondary issue:** Check 6 (`zero_queries`) is `severity="critical"` and check 13 (`NOT_ATTEMPTED`) is also `severity="critical"`. These overlap: if an agent never tried CLI (check 13), the observation file likely also has `queries_executed: 0` (check 6). The agent gets two critical violations for the same failure mode. This is not incorrect but inflates the violation count. Consider deduplication logic or a hierarchy where check 13 subsumes check 6 when transcript data is available.

---

## C. Ground Truth Architecture

### C.1. stats.json Sufficiency

Plan 03 generates `stats.json` per calibration contract:

```json
{
    "contract": "ReentrancyClassic",
    "contract_id": "cal-01",
    "nodes": 12,
    "edges": 17,
    "identity": "271b6cf5c178",
    "graph_path": "/absolute/path/to/graph.toon"
}
```

**Sufficient for:** Detecting fabricated graph stats (>30% node count deviation), providing pre-built graphs for agent sessions, verifying basic build-kg functionality.

**Insufficient for:**

1. **Verifying agent query results.** `stats.json` has node/edge counts but not the actual node IDs or query result content. When an agent claims "I queried for reentrancy patterns and found function:abc123," there is no ground truth to verify that `function:abc123` is a real node in the graph. This requires a **node manifest** -- a list of all node IDs in the ground truth graph.

2. **Verifying semantic accuracy.** stats.json doesn't record which vulnerabilities the contract actually contains. For `ReentrancyClassic.sol`, the ground truth should record: "This contract has a classic reentrancy vulnerability in `withdraw()` at line N." Without semantic ground truth, the validator can check structural integrity (did the agent use the CLI?) but not analytical accuracy (did the agent find the right vulnerability?).

3. **Supporting the Graph Value Scorer.** The GVS scores "did graph queries inform analysis?" but has no reference for what a GOOD set of queries looks like. If ground truth included an **expected query set** (e.g., "a good analysis of ReentrancyClassic should query: reentrancy patterns, external calls, balance mutations"), the GVS could score query quality against a rubric instead of heuristically.

### C.2. Semantic Ground Truth

The framework vision describes `ground_truth_rubric` in evaluation contracts:

```yaml
ground_truth_rubric:
  expected_findings:
    - title: "Classic reentrancy in withdraw()"
      severity: high
      evidence_must_include: ["external call before state update"]
  expected_reasoning:
    - must_query: "external calls that precede state writes"
    - must_identify: "withdraw -> call.value -> balance update ordering"
```

This is absent from 3.1c.2. The `ground_truth_rubric` field is listed in `_check_unconsumed_config`'s `known_keys` set (evaluation_runner.py line 476), confirming it's a recognized field, and it's passed to the reasoning evaluator via `eval_context["ground_truth_rubric"]` (line 649-651). But no ground truth rubric data is actually generated for the 4 calibration contracts.

**Recommendation:** Plan 03 should be extended (or a follow-up plan created) to generate `rubric.json` alongside `stats.json` for each calibration contract. Even a minimal rubric with known vulnerability type and affected function would dramatically improve evaluation quality. The calibration contracts are simple enough that ground truth rubrics can be hand-authored:

```json
{
    "contract_id": "cal-01",
    "expected_vulnerabilities": [
        {
            "type": "reentrancy",
            "function": "withdraw",
            "severity": "high",
            "key_indicators": ["external call before balance update"]
        }
    ],
    "expected_query_patterns": [
        "reentrancy OR re-entrancy",
        "external call",
        "state mutation after call"
    ]
}
```

### C.3. Ground Truth and Graph Value Scorer Connection

The GVS (`GraphValueScorer`) receives context including `obs_summary` and `contract` but does NOT receive ground truth stats. The pipeline in `evaluation_runner.py` Stage 5 calls:

```python
gvs_result = gvs.score(collected_output, context=context)
```

where `context` includes `obs_summary` and `contract` but NOT `ground_truth_stats`. This means the GVS cannot distinguish:
- Agent queried the graph and found 12 nodes (correct -- matches ground truth)
- Agent queried the graph and found 50 nodes (fabricated -- ground truth says 12)

The ground truth comparison is only done in the integrity validator (check GT), which runs AFTER the GVS in a separate code path.

**Recommendation:** Pass ground truth stats to the GVS as additional context so it can factor accuracy into its score, not just query quantity.

### C.4. Tier 2 Intelligence Module Requirements

The Tier 2 intelligence modules (from TESTING-FRAMEWORK.md) need ground truth that 3.1c.2 does not generate:

| Module | Ground Truth Needed | Provided by 3.1c.2? |
|---|---|---|
| Coverage radar | Per-vuln-class coverage data (which contracts test which vuln types) | NO -- stats.json has no vulnerability classification |
| Scenario synthesis | Untested behavioral claims from skill prompts | NO -- not ground truth but metadata about test coverage |
| Behavioral fingerprinting | Historical reasoning move profiles per agent | NO -- debrief persistence (Plan 05) captures answers but not reasoning move decomposition |
| Self-healing contracts | Score distribution history per evaluation dimension | NO -- Plan 04 stores rejection.json but not per-dimension score history |
| Adaptive tier management | Sustained low score signals | PARTIAL -- improvement queue (existing IMP-01) flags HIGH_PRIORITY but doesn't feed tier management |

**Assessment:** This is expected. 3.1c.2 is hardening infrastructure. Tier 2 intelligence is 3.1c.3 scope. However, the ground truth format should be designed with Tier 2 extensibility in mind -- adding vulnerability classification to stats.json now avoids a migration later.

---

## D. Debrief Pipeline Gaps

### D.1. Is Wiring the 3.1c Protocol Sufficient?

Plan 05 wires the existing 4-layer debrief cascade as Stage 9 in evaluation_runner.py. The debrief call itself remains in Stage 6 (before reasoning evaluation, because the evaluator needs debrief data as input). Stage 9 is purely a persistence stage.

**This is correct architecturally** but creates a subtle problem: the debrief happens BEFORE integrity checking (Stage 8.5). If integrity fails (auto-REJECT), the debrief data has already been generated and passed to the reasoning evaluator. This means:

- **A fabricating agent's debrief informs the reasoning evaluation.** If the agent fabricated its findings, its debrief answers (e.g., "My hypothesis was reentrancy, supported by evidence from graph node function:abc123") are also likely fabricated. The reasoning evaluator would score these fabricated answers, producing a score card that reflects fabricated reasoning.
- **The auto-REJECT in Plan 04 handles this correctly** by setting `baseline_update_status = "rejected"`, but the *scores themselves* are computed from tainted data.

**Recommendation:** Add a metadata flag `integrity_tainted: true` to the evaluation result when integrity check fails. Downstream consumers of the score card should be aware that the scores were computed from tainted input. This is distinct from auto-REJECT (which prevents baseline pollution) -- it's about signal quality labeling.

### D.2. Fabrication-Detecting Debrief Questions

The current debrief questions are:

```python
FULL_DEBRIEF_QUESTIONS = [
    "What was your primary hypothesis?",
    "What BSKG queries informed your analysis?",
    "What surprised you in the results?",
    "What evidence supports your conclusion?",
    "What evidence contradicts your conclusion?",
    "What would you investigate further?",
    "Rate your confidence in the finding (1-5 with justification)",
]
```

These are good for genuine analysis assessment but weak for fabrication detection. Questions that would help diagnose fabrication:

| Question | What It Detects |
|---|---|
| "Quote the exact CLI command you ran and its first line of output." | Fabricating agents produce plausible-sounding but generic commands. Real agents recall specific output including counts and error messages. Cross-reference with transcript. |
| "How many graph nodes did `build-kg` produce? How many query matches did your best query return?" | Fabricating agents guess round numbers. Real agents recall specific counts that match ground truth. |
| "What was the identity hash of the graph you built?" | Fabricating agents cannot produce this unless they actually ran build-kg. Cross-reference with ground truth `identity` field. |
| "Name one function in the contract that is NOT vulnerable and explain why." | Fabricating agents focus on positive findings. Genuine analysis considers the full contract surface. |
| "Describe a query you tried that returned NO useful results." | Fabricating agents report only successes. Real analysis involves failed queries and pivots. |

**Recommendation:** Add a `FABRICATION_PROBE_QUESTIONS` list (3-4 questions) that is appended to `FULL_DEBRIEF_QUESTIONS` when `integrity_check.verdict != "PASS"`. This creates a targeted probe for sessions where integrity is already suspicious.

### D.3. Debrief -> Improvement Loop Feedback

Plan 05 persists `debrief.json` with:

```json
{
    "agent_name": "...",
    "layer_used": "...",
    "answers": ["...", "..."],
    "confidence": 0.9,
    "questions_asked": ["...", "..."]
}
```

**Missing from the debrief artifact:**

1. **Reasoning move classification.** The framework describes 7 reasoning moves (HYPOTHESIS_FORMATION through SELF_CRITIQUE). The debrief questions map loosely to these moves, but the mapping is implicit. The debrief artifact should include a `reasoning_moves` field that explicitly maps each answer to its reasoning move, enabling the metaprompting feedback loop.

2. **Cross-reference to transcript events.** When an agent answers "I queried for reentrancy patterns," the debrief artifact should include the tool_call_index from the transcript that corresponds to this claim. This enables automated verification: does the transcript confirm the debrief claim?

3. **Delta from expected behavior.** For calibration contracts with semantic ground truth, the debrief should include a `delta` field: "Agent claimed X but ground truth says Y." This is not the debrief module's responsibility -- it's the evaluator's -- but the debrief artifact should be structured to ENABLE this delta computation downstream.

### D.4. Detecting Performance vs. Genuine Reasoning

The hardest debrief challenge: distinguishing an agent that is "performing" (producing plausible-sounding answers that match expected patterns) from one that genuinely reasoned about the contract.

**Signals that distinguish performance from reasoning:**

| Signal | Performance | Genuine |
|---|---|---|
| Specificity of evidence references | Generic ("I found a reentrancy vulnerability") | Specific ("function:withdraw at line 23 has an external call to msg.sender before state update") |
| Mention of failed hypotheses | Never mentions dead ends | "I initially suspected oracle manipulation but found no price feed dependency" |
| Surprise or confusion | Always confident, no uncertainty | "The graph showed an unexpected call to an external contract I hadn't noticed" |
| Self-critique quality | "I could have looked at more things" (generic) | "My query for access control missed the `onlyOwner` modifier because I queried 'authorization' instead of 'access control'" (specific) |
| Cross-reference consistency | Claims match a template pattern | Claims match the actual transcript tool calls |

**Implementation approach:** The reasoning evaluator already scores along these dimensions. But the debrief persistence format should capture *raw* answers verbatim (it does) AND the evaluator's per-answer assessment (it currently stores only the aggregate `confidence`). To close this gap, the debrief artifact should include the evaluator's per-answer annotations.

---

## E. Creative Improvements

### Improvement 1: Ground Truth Node Manifest for Cross-Reference Verification

**What it does:** Extend `scripts/generate_ground_truth.py` to also extract and persist a `nodes.json` file containing all node IDs and their types from each calibration contract's graph. This enables cross-reference verification: when an agent claims a node ID in its findings, the validator can check if that node actually exists in the ground truth graph.

**Which plan it modifies:** Plan 03 (Ground Truth Graph Generation) -- add a Task 3 that runs `uv run alphaswarm query "all nodes" --graph {graph_path} --compact` and parses the output into `nodes.json`.

**How it advances the full evaluation vision:** Closes the fabricated-node-ID gap identified in Section B.3. Currently, check 4 (`fabricated_identifiers`) uses regex heuristics to detect fabricated-looking IDs but cannot verify whether a correctly-formatted ID actually exists in the graph. With a node manifest, the validator can do exact-match verification.

**Implementation complexity:** LOW. The query CLI already returns node IDs. Parsing the output and writing JSON is straightforward. The validator already has the `_check_fabricated_identifiers` function that can be extended with a ground truth cross-reference.

### Improvement 2: Integrity-Aware Score Tainting

**What it does:** When the integrity check (Plan 04) returns FAIL or DEGRADED, annotate the EvaluationResult's score_card with a `tainted: true` flag and a `taint_reason` string. This does NOT change scores -- it labels them as computed from potentially unreliable input. Downstream consumers (regression detection, baseline management, improvement loop) can filter or weight tainted results differently.

**Which plan it modifies:** Plan 04 (Integrity Check Pipeline Integration) -- add score tainting logic after the auto-REJECT block.

**How it advances the full evaluation vision:** The improvement loop (3.1c.3) needs to distinguish "low scores from genuine analysis" (improve the prompt) from "low scores from tainted execution" (re-run the evaluation). Without tainting, the improvement loop would attempt to fix prompts when the real problem was execution integrity.

**Implementation complexity:** LOW. Add a `tainted: bool` and `taint_reason: str | None` field to ScoreCard model, set them in the integrity check block.

### Improvement 3: Fabrication Probe Questions for Suspicious Sessions

**What it does:** Define a `FABRICATION_PROBE_QUESTIONS` list (4 questions targeting verifiable claims) that is injected into the debrief when the integrity check produces warnings or failures. The probe questions ask for specific, cross-referenceable facts: exact CLI command output, node counts, identity hashes, and failed queries.

**Which plan it modifies:** Plan 05 (Agent Debrief Pipeline Wiring) -- modify the debrief call to inject probe questions when `result.metadata.get("integrity_check", {}).get("verdict") != "PASS"`.

**How it advances the full evaluation vision:** Creates a diagnostic pathway for fabrication. Currently, debrief questions assess reasoning quality but don't probe for verifiable facts. Adding probe questions turns the debrief from a reasoning assessment into an integrity interrogation when suspicion is raised, providing data for the Tier 2 behavioral fingerprinting module.

**Implementation complexity:** MEDIUM. Requires the debrief call to be integrity-aware, which means passing the integrity result back to Stage 6 (currently, integrity runs after debrief). This creates a chicken-and-egg problem: integrity check needs the debrief, but the fabrication probe needs the integrity check. Resolution: run a PRELIMINARY integrity check (checks 1-6 only, no transcript-based checks) before Stage 6, then run the full integrity check after Stage 8. This splits the integrity check into fast/slow passes.

### Improvement 4: DEGRADED Verdict Escalation Policy

**What it does:** Replace the binary PASS/FAIL threshold with a graduated escalation policy. Define `DEGRADED_ESCALATION_THRESHOLD = 3` -- if a session accumulates 3+ warnings, the verdict escalates from DEGRADED to FAIL. Additionally, introduce `warning_weight` per check name so that some warnings are heavier than others (e.g., `knowledge_leakage` is weight 2 because it directly indicates isolation failure).

**Which plan it modifies:** Plan 04 (Integrity Check Pipeline Integration) -- modify the verdict computation in `validate_batch()`.

**How it advances the full evaluation vision:** Closes the "DEGRADED dead zone" where multiple warnings are ignored. The testing philosophy (Principle 9: imperfection is expected) acknowledges that some degradation is normal, but accumulated degradation signals a systemic problem. A threshold converts accumulated soft signals into an actionable hard signal.

**Implementation complexity:** LOW. Modify the verdict computation logic in `validate_batch()` to count weighted warnings and escalate when threshold is exceeded.

### Improvement 5: Debrief-Transcript Cross-Reference Validation

**What it does:** After the debrief is persisted (Stage 9), run a lightweight cross-reference check: for each debrief answer that mentions a CLI command, query result, or node ID, verify that the claim appears in the agent's JSONL transcript. Record the cross-reference results as `debrief_verification.json` alongside `debrief.json`.

**Which plan it modifies:** Plan 05 (Agent Debrief Pipeline Wiring) -- add a post-debrief verification step.

**How it advances the full evaluation vision:** Directly addresses the "performing vs. genuine reasoning" problem from Section D.4. Cross-reference verification transforms the debrief from a self-report (which a fabricating agent can game) into a verifiable claim set (which requires consistency with the transcript). This is the foundation for the Tier 2 behavioral fingerprinting module.

**Implementation complexity:** MEDIUM. Requires parsing debrief answers for CLI commands and node IDs (regex), then searching the transcript for matching tool_use events. The TranscriptParser already provides `get_bskg_queries()` and `get_bash_commands()` which return structured data suitable for cross-referencing.

---

## Summary of Findings

### What 3.1c.2 Gets Right

1. **Defense in depth.** Plan 01 (prevention via delegate_guard) + Plan 02 (detection via CLIAttemptState) + Plan 04 (enforcement via auto-REJECT) creates a three-layer defense. This is sound architecture.

2. **Graceful degradation.** `TRANSCRIPT_UNAVAILABLE` is a warning, not a critical failure. This prevents the system from rejecting valid sessions due to infrastructure issues (stale binaries, missing transcripts).

3. **Non-blocking integrity.** Plan 04 correctly places the integrity check AFTER store_result so results are persisted even when integrity fails. This enables forensic analysis. Plan 05 correctly ensures debrief runs even for FAIL sessions.

4. **Wiring-not-redesigning.** Plans 02-05 extend existing infrastructure (TranscriptParser, agent_execution_validator, evaluation_runner, debrief_protocol) rather than creating new systems. This is the right approach for a hardening phase.

### What 3.1c.2 Misses

1. **No semantic ground truth.** stats.json captures structural facts (node/edge counts) but not semantic facts (expected vulnerabilities, expected reasoning patterns). This limits evaluation to "did the agent use the tools?" rather than "did the agent find the right answer?"

2. **No node-level verification.** Agent claims about specific graph nodes cannot be verified because ground truth doesn't include a node manifest. Fabricated node IDs that look syntactically correct pass all checks.

3. **DEGRADED verdict is inert.** Multiple warnings accumulate without consequence. The graduated response model (PASS -> DEGRADED -> FAIL) has no threshold for DEGRADED -> FAIL escalation.

4. **Debrief is not integrity-aware.** The debrief runs before the integrity check, so fabricating agents are debriefed with the same questions as genuine agents. Probe questions for suspicious sessions would improve diagnostic quality.

5. **No debrief-transcript cross-reference.** Debrief answers are taken at face value. An agent can claim "I queried for reentrancy" without verification that the transcript contains such a query.

### Priority Recommendations

| Priority | Improvement | Plan | Effort |
|---|---|---|---|
| P0 | Ground truth node manifest | Plan 03 | LOW |
| P1 | DEGRADED escalation threshold | Plan 04 | LOW |
| P1 | Integrity-aware score tainting | Plan 04 | LOW |
| P2 | Fabrication probe questions | Plan 05 | MEDIUM |
| P2 | Debrief-transcript cross-reference | Plan 05 | MEDIUM |
| P3 | Semantic ground truth (rubric.json) | Plan 03 (follow-up) | MEDIUM |
| P3 | Two-pass integrity (fast/slow) | Plan 04 (follow-up) | HIGH |

---

## Appendix: Validator Check Inventory

For reference, the complete check inventory after 3.1c.2:

| # | Check Name | Scope | Severity | Failure Mode |
|---|---|---|---|---|
| 1 | session_duration | Per-file | critical if < 10s | Plausibility |
| 2 | graph_stats | Per-file | warning if < 2 nodes or 0 edges | Plausibility |
| 3 | knowledge_leakage | Per-file | critical if leaked terms found | FM-4 |
| 4 | fabricated_identifiers | Per-file | warning (unverified) | Fabrication |
| 5 | finding_uniformity | Per-file | warning/info | Fabrication |
| 6 | query_count | Per-file | critical if 0, warning if > 20 | FM-1 |
| 7 | cross_file_similarity | Cross-file | critical if identical timestamps | Cross-agent |
| 8 | worktree_isolation | Cross-file | critical if no worktrees | FM-2 |
| GT | graph_stats_vs_ground_truth | Cross-file | critical if > 30% deviation | Accuracy |
| 13 | cli_attempt_state | Per-file + transcript | critical if NOT_ATTEMPTED, warning if FAILED | FM-3 |
