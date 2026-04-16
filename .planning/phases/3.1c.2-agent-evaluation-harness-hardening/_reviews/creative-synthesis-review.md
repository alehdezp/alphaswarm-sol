# Phase 3.1c.2 Creative Synthesis Review

**Reviewer:** Systems Architect (Claude Opus 4.6)
**Date:** 2026-03-02
**Scope:** All 6 plans as a unified system, downstream impact, testing vision alignment
**Confidence:** HIGH on structural analysis, MEDIUM on some downstream predictions

---

## A. System-Level Assessment

### A.1 Is the wave structure optimal?

**No. The wave structure is defensible but suboptimal for feedback speed.**

The current structure is:

```
Wave 1: Plan 01 (delegate_guard config) + Plan 03 (ground truth generation)
Wave 2: Plan 02 (CLIAttemptState + check 13)
Wave 3: Plan 04 (integrity pipeline integration)
Wave 4: Plan 05 (debrief Stage 9)
Wave 5: Plan 06 (Plan 12 retry)
```

The problem: Waves 2-4 are strictly sequential despite partial independence. Plan 05 (debrief wiring) depends on Plan 04 only because it adds a stage "after" the integrity check in the pipeline. But the debrief persistence logic has zero data dependency on the integrity check. They modify the same file (`evaluation_runner.py`) but touch different code paths. If the debrief stage ran independently and was ordered by `PIPELINE_STAGES` position, Plans 04 and 05 could execute in parallel as Wave 3.

**Proposed reordering:**

```
Wave 1: Plan 01 (guard config) + Plan 03 (ground truth)      [unchanged]
Wave 2: Plan 02 (CLIAttemptState)                             [unchanged]
Wave 3: Plan 04 (integrity pipeline) + Plan 05 (debrief)      [merged wave]
Wave 4: Plan 06 (retry)                                       [unchanged]
```

This compresses 5 waves to 4, saving one full execution cycle. The risk is merge conflicts in `evaluation_runner.py` if Plans 04 and 05 run simultaneously. Mitigation: Plan 05 should be written knowing Plan 04's changes are incoming, or they can be a single plan (see A.2).

### A.2 Are there redundancies that could be merged?

**Yes. Plans 04 and 05 share enough surface area to be a single plan.**

Both modify `evaluation_runner.py`. Both add post-pipeline stages. Both write artifacts to `effective_obs_dir`. Both have integration tests that share the same test setup (create temp obs dir, create synthetic observations, run the pipeline, assert artifact outputs). The "critical realization" in Plan 05 Task 1 -- that the debrief already runs in Stage 6 and Plan 05 is just a persistence stage -- makes it a 30-line addition, not a full plan.

**Recommendation:** Merge Plans 04 and 05 into a single "Post-Pipeline Verification + Persistence" plan. This also eliminates the artificial dependency chain and enables a cleaner `evaluation_runner.py` diff.

**Counter-argument for keeping them separate:** Modularity of review. Each plan gets its own summary, its own verification. If one fails, the other is unaffected. This is valid but the cost (extra wave, extra context load for the executor) outweighs the benefit.

### A.3 Is the scope too narrow or too broad?

**The scope is precisely calibrated for enforcement -- but too narrow for data capture.**

What 3.1c.2 does well:
- Prevention (Plan 01): Hook-level blocking of Python imports
- Detection (Plan 02): Post-session forensic verification via CLIAttemptState
- Reference data (Plan 03): Ground truth for comparison
- Automation (Plan 04): Auto-reject pipeline
- Completeness (Plan 05): Debrief artifact persistence
- Validation (Plan 06): End-to-end retry proving it works

What 3.1c.2 misses:
- **Structured observation data for 3.1c.3 consumption.** The retry in Plan 06 produces observation JSONs and transcript JONSLs, but none of these are in the format that 3.1c.3's intelligence modules need. The coverage radar (3.1c.3-03) needs vulnerability-class annotations. The reasoning decomposer (3.1c.3-02) needs per-move transcript segments. The scenario synthesizer (3.1c.3-04) needs skill-claim coverage mappings. Plan 06 captures data, but it is enforcement-verification data (did the agent comply?) not intelligence-training data (how did the agent reason?).

- **No observation of what agents DO correctly.** The entire phase focuses on what agents must NOT do (no Python imports, no context reads). It says nothing about what good agent behavior looks like: Which query formulations produced useful results? Which graph traversal patterns led to real findings? This positive-signal data is what 3.1c.3's intelligence modules most need.

### A.4 Single highest-risk assumption

**Env-var propagation from orchestrator session to Agent Teams teammate hook subprocesses.**

This is called out in RESEARCH.md as Pitfall 4 and is rated MEDIUM confidence -- the only non-HIGH confidence item in the entire research document. The entire enforcement stack depends on `ALPHASWARM_EVAL_MODE=1` and `DELEGATE_GUARD_CONFIG` being visible inside the hook process when a teammate makes a tool call. If these env vars do not propagate through:

```
Orchestrator session -> TeamCreate -> Teammate session -> PreToolUse hook subprocess
```

...then Plan 01's delegate_guard config is never loaded, Plans 01-05 are bypassed, and Plan 06 fails with the exact same failure modes as the original Plan 12 Batch 1.

Plan 06 Task 1 includes a 1-agent smoke test for this (step 8), but this is the only empirical test of the most critical assumption. If it fails, there is no Plan B documented. The entire phase halts.

**Mitigation gap:** Plan 01 should include a documented fallback mechanism: if env-var propagation fails, the eval config can be installed as the default config (symlink or file copy to the standard search path) with a post-session restore step. This is less clean but provides a working alternative.

### A.5 Single most valuable thing this phase delivers

**The auto-reject pipeline (Plan 04) wired into evaluation_runner.py.**

Not the delegate_guard config (that is a prerequisite). Not the ground truth (that is reference data). Not the retry (that is validation). The auto-reject pipeline is what transforms the evaluation framework from a passive measurement system into an active quality gate. After Plan 04:

- Every evaluation session automatically checks integrity
- Failed sessions produce rejection.json artifacts at predictable paths
- Rejected sessions cannot pollute baselines
- The evaluation runner has a `metadata["integrity_check"]` field that downstream consumers can query

This is the primitive that enables 3.1c.3's tier management (auto-promote on sustained failures), 3.1f's regression detection (only non-rejected baselines count), and 3.2's audit validation (only integrity-verified results are reportable).

---

## B. The "10x" Question: Redesign from Scratch

If I were designing 3.1c.2 from scratch with the same scope (6 plans, enforcement + verification + retry), I would restructure around the data lifecycle rather than around individual enforcement mechanisms.

### Current Structure: Mechanism-Oriented

```
Plan 01: Build the enforcement primitive (delegate_guard)
Plan 02: Build the detection primitive (CLIAttemptState)
Plan 03: Build the reference data (ground truth)
Plan 04: Wire enforcement into pipeline
Plan 05: Wire debrief into pipeline
Plan 06: Validate everything works
```

### Proposed Structure: Data-Lifecycle-Oriented

```
Plan 01: "Enforcement + Observation Config" (Wave 1)
  - delegate_guard_config_eval.yaml
  - Env-var gating in delegate_guard.py
  - ALSO: observation_schema_eval.yaml defining what data to capture
  - Canary test for blocking + canary test for data capture format

Plan 02: "Ground Truth + Reference Baseline" (Wave 1, parallel)
  - Ground truth graph generation (current Plan 03)
  - ALSO: Reference "ideal agent transcript" for each calibration contract
    (hand-crafted, showing what good CLI usage looks like)
  - These become the training exemplars for 3.1c.3 intelligence

Plan 03: "Transcript Intelligence: CLIAttemptState + Reasoning Markers" (Wave 2)
  - CLIAttemptState (current Plan 02)
  - ALSO: extract reasoning move markers from transcripts
  - ALSO: extract query-result-usage chain (did agent use query results?)
  - This creates the structured data 3.1c.3 reasoning decomposer needs

Plan 04: "Pipeline Integration: Integrity + Debrief + Observation Export" (Wave 3)
  - Auto-reject pipeline (current Plan 04)
  - Debrief persistence (current Plan 05)
  - ALSO: structured observation export in 3.1c.3-consumable format
  - Single plan because these are all post-pipeline stages in the same file

Plan 05: "Calibration Retry with Structured Data Capture" (Wave 4)
  - Plan 12 retry (current Plan 06)
  - BUT: also captures structured observation data for intelligence
  - Outputs not just "did it pass?" but "what can we learn from it?"

Plan 06: "Interface Verification: 3.1c.3 Data Contract Validation" (Wave 4, parallel)
  - Verify that Plan 05 outputs satisfy 3.1c.3 consumer contracts
  - Verify coverage radar can ingest observation data
  - Verify reasoning decomposer can consume transcript markers
  - This is the "did we build the right bridge?" validation
```

### Key Differences

1. **Plan 01 captures observation schema alongside enforcement config.** The same hook infrastructure that blocks bad behavior should capture good behavior. This is one YAML file, one additional test, zero new modules.

2. **Plan 02 creates reference transcripts.** Hand-crafted "ideal agent" transcripts for each calibration contract establish what good looks like. These are 50-100 lines each and become training exemplars for 3.1c.3's intelligence modules.

3. **Plan 03 extracts richer transcript data.** Instead of just CLIAttemptState (4 enum values), extract reasoning markers (which transcript lines contain hypothesis formation, query formulation, result interpretation). This is where the intelligence seed lives.

4. **Plans 04+05 merge.** As discussed in A.2.

5. **Plan 06 is an interface contract test, not more enforcement validation.** The retry (Plan 05 in this structure) validates enforcement. Plan 06 validates that the data produced by the retry is consumable by downstream phases.

### Why This is Better

The current design treats 3.1c.2 as a gate: "block bad things, verify blocking works." The redesign treats 3.1c.2 as a bridge: "block bad things AND capture good things, so the intelligence layer has data to learn from." The enforcement mechanisms are identical. The additional data capture is small in implementation effort but transformative in downstream value.

---

## C. Top 10 Improvements (Ranked by Impact)

### 1. Add Observation Schema for 3.1c.3 Intelligence Consumption

**Impact:** Enables 3.1c.3-02 (reasoning decomposer), 3.1c.3-03 (coverage radar), 3.1c.3-04 (scenario synthesizer), 3.1c.3-08 (graph diagnostics). Without this, 3.1c.3 must design its own data ingestion from scratch, likely requiring reprocessing of all Plan 06 retry data.

**Effort:** Small (1 YAML schema file, ~50 lines; 1 export function, ~80 lines)

**Which plan:** Plan 01 (add observation schema alongside enforcement config)

**Implementation sketch:**
- Define `observation_schema_eval.yaml` with fields: `vulnerability_class`, `query_formulations[]`, `result_usage_evidence[]`, `reasoning_moves[]`, `graph_traversal_pattern`
- Add a `structured_observation_export()` function to the observation writer that emits these fields
- Include in the observation JSONL written by hooks
- Test: verify schema fields present in synthetic observation output

**Risk:** Over-engineering the schema before 3.1c.3 knows what it needs. Mitigation: make the schema extensible (additional fields are ignored, missing fields default to null).

### 2. Create Reference "Ideal Agent Transcripts" for Calibration Contracts

**Impact:** Enables 3.1c.3-05 (contract healer -- needs examples of good performance to detect degradation), 3.1c.3-10 (recommendation engine -- needs examples of good query patterns to recommend). Also provides a gold-standard comparison target for the reasoning evaluator.

**Effort:** Moderate (4 hand-crafted transcript stubs, ~100 lines each, plus a comparison utility ~60 lines)

**Which plan:** Plan 03 (alongside ground truth generation)

**Implementation sketch:**
- For each calibration contract, write a synthetic "ideal transcript" showing: correct build-kg invocation, 3+ meaningful queries, evidence-backed finding, structured output
- Store at `.vrs/ground-truth/{cal-id}/ideal-transcript.jsonl`
- Create `compare_transcript_quality(actual, ideal) -> QualityDelta` utility
- Test: verify ideal transcripts parse correctly with TranscriptParser

**Risk:** Hand-crafted transcripts may not match real agent output format exactly. Mitigation: validate against TranscriptParser at creation time.

### 3. Extract Query-Result Usage Chain from Transcripts

**Impact:** Directly enables the Graph Value Scorer to distinguish "checkbox compliance" (query ran, results ignored) from "genuine graph use" (query results informed finding). This is the core question from TESTING-PHILOSOPHY.md Principle 1: "Did graph queries inform analysis or were they performative?" Currently CLIAttemptState only answers "did they try?" not "did they use what they found?"

**Effort:** Small (extend `compute_cli_attempt_state()` with a `query_result_usage` field, ~40 lines)

**Which plan:** Plan 02 (extend CLIAttemptState module)

**Implementation sketch:**
- After determining `ATTEMPTED_SUCCESS`, analyze whether subsequent assistant messages reference query results
- Add field: `query_result_referenced: bool` (did any assistant message after a query cite specific node IDs or finding details from the query result?)
- Add field: `result_usage_ratio: float` (fraction of successful queries whose results appear in subsequent reasoning)
- These fields go into the observation data, not the violation system
- Test: synthetic transcript where agent queries but ignores results vs. queries and references results

**Risk:** False positive on "references results" if agent fabricates node IDs. Mitigation: cross-reference with ground truth node IDs from Plan 03.

### 4. Merge Plans 04 and 05 into Single Pipeline Integration Plan

**Impact:** Reduces wave count from 5 to 4 (faster completion), eliminates artificial dependency, simplifies executor context loading (one plan summary instead of two). Enables parallel test development for integrity and debrief in a single test file.

**Effort:** Trivial (restructure two plan documents into one; no new code)

**Which plan:** Merge Plans 04+05 into Plan 04 "Post-Pipeline Integration: Integrity + Debrief"

**Implementation sketch:**
- Combine Plan 04 Task 1 (wire integrity check) and Plan 05 Task 1 (wire debrief persistence) into a single task modifying `evaluation_runner.py`
- Combine test files into `test_post_pipeline_integration.py` with sections for integrity and debrief
- Remove Plan 05 as a separate entity; renumber Plan 06 to Plan 05

**Risk:** Larger single plan may exceed executor attention capacity. Mitigation: the combined plan is still < 300 lines of code changes.

### 5. Add Env-Var Propagation Fallback in Plan 01

**Impact:** Eliminates the single highest-risk assumption (see A.4). If env-var propagation to teammate hooks fails, the phase does not halt -- it falls back to a less elegant but functional mechanism.

**Effort:** Small (~30 lines of shell script + documentation)

**Which plan:** Plan 01

**Implementation sketch:**
- After the canary test passes for direct invocation, add a second canary: invoke via a subprocess that simulates the hook being called from a child process
- If direct env-var propagation fails: document a fallback where the eval config is copied to the standard search path (`Path(__file__).parent / "delegate_guard_config.yaml"`) with a restore script
- Add `_restore_config()` function that swaps back the original config after evaluation sessions
- Plan 06 preflight check (Task 1 step 8) becomes non-blocking: if smoke test fails, apply fallback and re-test

**Risk:** Fallback mechanism could accidentally leave eval config as default config if restore fails. Mitigation: the restore script runs in a `finally` block and also checks file modification timestamps.

### 6. Add Structured Debrief Questions Targeting 3.1c.3 Intelligence Needs

**Impact:** Enables 3.1c.3-10 (recommendation engine), 3.1c.3-08 (graph diagnostics). The debrief protocol already has a `questions_asked` field, but the questions are generic. Adding intelligence-targeted questions like "Which query gave you the most useful information?" and "What would you query differently next time?" provides direct input to the recommendation engine.

**Effort:** Small (5 additional debrief questions in the debrief prompt template, ~20 lines)

**Which plan:** Plan 05 (or merged Plan 04 per improvement #4)

**Implementation sketch:**
- Extend the canonical debrief prompt with 5 intelligence-gathering questions:
  1. "Which graph query was most informative for your analysis?"
  2. "Which query returned unhelpful results, and what would you change?"
  3. "What information did you need that you could not get from the graph?"
  4. "Rate your confidence in each finding (1-5) and explain why."
  5. "If you could add one capability to the tools, what would it be?"
- Store answers in a `intelligence_signals` sub-object within `debrief.json`
- 3.1c.3-10 recommendation engine consumes this directly

**Risk:** Agents may give vacuous answers to debrief questions. Mitigation: score answer quality as part of debrief confidence assessment.

### 7. Pre-compute Graph Query Catalog for Calibration Contracts

**Impact:** Enables Plan 06 agents to use known-good queries instead of formulating their own (reducing variance). Also creates the seed data for 3.1c.3-04 (scenario synthesizer) which needs example query formulations per vulnerability type.

**Effort:** Small (run 10-15 queries per calibration contract, store results in ground truth)

**Which plan:** Plan 03 (extend ground truth generation)

**Implementation sketch:**
- For each calibration contract, run a catalog of queries: "functions with external calls", "state variables modified after external calls", "access control patterns", "functions without modifiers"
- Store results in `.vrs/ground-truth/{cal-id}/query-catalog.json` with: `{query, result_count, sample_node_ids, relevance_to_vuln}`
- Agents in Plan 06 can reference this catalog if their free-form queries fail
- 3.1c.3 scenario synthesizer uses this as template for generating queries for new contracts

**Risk:** Catalog queries may become stale if CLI query interface changes. Mitigation: query catalog generation is idempotent and re-runnable via the generation script.

### 8. Add Timing Telemetry to Each Pipeline Stage

**Impact:** Enables 3.1c.3-05 (contract healer -- detects performance degradation), 3.1c.3-07 (framework self-validation -- identifies slow stages), and general operational insight. Currently `evaluation_runner.py` tracks `stages_completed` but not how long each stage took.

**Effort:** Trivial (~15 lines: `time.monotonic()` before and after each stage, store in `health.stage_durations`)

**Which plan:** Plan 04 (as part of pipeline integration)

**Implementation sketch:**
- Add `stage_durations: dict[str, float]` to `PipelineHealth`
- Before each stage: `t0 = time.monotonic()`
- After each stage: `health.stage_durations[stage_name] = time.monotonic() - t0`
- Include in `result.metadata["pipeline_timing"]`
- Test: verify timing data present in integration test output

**Risk:** Essentially zero. This is pure observability.

### 9. Add Cross-Session Observation Correlation ID

**Impact:** When Plan 06 runs multiple agents, each produces separate observation files. Currently there is no correlation ID linking "these 5 observations came from the same evaluation session." 3.1c.3's cross-workflow learning (module 6) and behavioral fingerprinting (module 4) need to know which observations are from the same session to detect cross-agent patterns.

**Effort:** Trivial (add `session_correlation_id` to observation schema, ~5 lines)

**Which plan:** Plan 04 (integrity pipeline integration adds metadata to observations)

**Implementation sketch:**
- Generate a UUID4 `session_correlation_id` at the start of each evaluation run
- Include it in `result.metadata["session_correlation_id"]`
- Include it in each `rejection.json` and `debrief.json`
- 3.1c.3 modules can group observations by this ID

**Risk:** None.

### 10. Add "Enforcement Bypass Audit" to Integrity Report

**Impact:** The integrity report currently checks for violations (things that went wrong). An enforcement bypass audit would check for things that SHOULD have been blocked but were not -- specifically looking at transcript Bash commands for patterns that match `blocked_patterns` but somehow executed. This detects delegate_guard failures or configuration gaps.

**Effort:** Small (~40 lines in agent_execution_validator.py)

**Which plan:** Plan 02 (alongside CLIAttemptState, as check 14)

**Implementation sketch:**
- Load `delegate_guard_config_eval.yaml` patterns
- Scan transcript Bash commands for any command matching a blocked pattern that also has a successful tool_result
- If found: critical violation "Enforcement bypass detected: command '{cmd}' matches blocked pattern '{pattern}' but executed successfully"
- This is a meta-check: it validates that the enforcement layer is working, not just that agents behaved

**Risk:** May produce false positives if `allowed_reads` exceptions are not accounted for. Mitigation: apply the full blocking/allowing logic from delegate_guard.py, not just pattern matching.

---

## D. Missing Interfaces

### Interface 1: Observation Data -> Coverage Radar

**Producer:** Plan 06 (retry observations)
**Consumer:** 3.1c.3-03 (coverage radar completion)

**What 3.1c.3 needs:** Per-observation records with `vulnerability_class` (e.g., "reentrancy", "access-control", "oracle-manipulation"), `semantic_operations_detected[]`, and `finding_confidence`. The coverage radar tracks tested-vs-untested space across vulnerability class x semantic operation.

**What 3.1c.2 currently produces:** Observation JSONs with `findings[].title`, `findings[].severity`, `findings[].confidence` but no standardized `vulnerability_class` field. Findings use free-text titles like "Reentrancy in withdraw()" which must be classified before the radar can ingest them.

**Bridge:** Add a `vulnerability_class` field to the observation schema. Plan 06's retry prompt should instruct agents to classify findings using the 18 VulnDocs categories. If agents produce free-text, the integrity validator could attempt automatic classification via keyword matching against VulnDocs category names.

### Interface 2: Transcript Segments -> Reasoning Decomposer

**Producer:** Plan 02 (CLIAttemptState / transcript analysis)
**Consumer:** 3.1c.3-02 (reasoning decomposer -- 3-move per-move scoring)

**What 3.1c.3 needs:** Transcript segments annotated with reasoning move types (HYPOTHESIS_FORMATION, QUERY_FORMULATION, RESULT_INTERPRETATION). The decomposer scores each move independently.

**What 3.1c.2 currently produces:** `CLIAttemptState` (4 enum values) and raw JSONL transcripts. No move-level annotation. The transcript is an unstructured sequence of tool calls and assistant messages.

**Bridge:** Plan 02 should extract a `reasoning_timeline` from the transcript: ordered list of `(timestamp, move_type, content_snippet)` tuples. Move type detection can be heuristic: "query" commands -> QUERY_FORMULATION, text before first query -> HYPOTHESIS_FORMATION, text after query results -> RESULT_INTERPRETATION. This heuristic is imperfect but gives 3.1c.3-02 a starting point that it can then refine with LLM-based classification.

### Interface 3: Debrief Responses -> Recommendation Engine

**Producer:** Plan 05 (debrief persistence)
**Consumer:** 3.1c.3-10 (recommendation engine -- failure-to-fix mapping)

**What 3.1c.3 needs:** Structured debrief data with: "what worked", "what failed", "what agent would do differently". The recommendation engine maps these to specific tool improvements and query suggestions.

**What 3.1c.2 currently produces:** `debrief.json` with `answers[]` (list of strings), `confidence` (float), `layer_used` (string). The answers are responses to generic debrief questions, not targeted intelligence-gathering questions.

**Bridge:** See improvement #6 above. Add intelligence-targeted debrief questions whose answers map directly to recommendation engine inputs.

### Interface 4: Ground Truth Stats -> Tier Manager

**Producer:** Plan 03 (ground truth generation)
**Consumer:** 3.1c.3-05 (contract healer + tier manager)

**What 3.1c.3 needs:** Ground truth with expected findings (which vulnerabilities exist in each calibration contract, at what severity). The tier manager uses this to auto-promote agents that consistently miss known vulnerabilities.

**What 3.1c.2 currently produces:** `stats.json` with `nodes`, `edges`, `identity`, `graph_path`. No expected findings. The ground truth is about graph structure, not about vulnerability presence.

**Bridge:** Plan 03 should add an `expected_findings.json` per calibration contract with: `[{vulnerability_class, severity, function_name, description}]`. These are hand-curated (the calibration contracts have known vulnerabilities by design). This is 4 small JSON files, each 5-10 entries.

### Interface 5: Rejection Reports -> Gap Log

**Producer:** Plan 04 (integrity pipeline, rejection.json)
**Consumer:** 3.1f-01 (failure classifier + gap log wiring)

**What 3.1f needs:** Classified failure reports with: failure_mode (FM-1 through FM-4 or new), root_cause, affected_agent, remediation_status. The failure classifier builds a taxonomy from accumulated failures.

**What 3.1c.2 currently produces:** `rejection.json` with `IntegrityReport` containing `violations[]` with `check_name`, `severity`, `details`, `evidence`. The violation check names map to failure modes (check 13 -> FM-3), but the mapping is implicit and not serialized.

**Bridge:** Add a `failure_mode` field to `IntegrityViolation` that explicitly maps each violation to an FM-* code. Include it in `rejection.json`. This is a trivial addition (~5 lines) to `agent_execution_validator.py` that saves 3.1f from having to reverse-engineer the mapping.

---

## E. The "One Thing" Insight

### Proposal: Structured Reasoning Timeline Extraction

If I could add one capability to 3.1c.2 that does not exist in any current plan, it would be **structured reasoning timeline extraction from agent transcripts**.

### What It Is

A function that takes a raw JSONL agent transcript and produces a structured timeline:

```python
@dataclass
class ReasoningEvent:
    timestamp: str
    move_type: Literal[
        "hypothesis", "query_formulation", "query_execution",
        "result_interpretation", "evidence_integration", "conclusion"
    ]
    content_snippet: str  # first 200 chars of the relevant text
    tool_call_id: str | None
    references_prior_event: int | None  # index of the event this builds on

def extract_reasoning_timeline(transcript_path: Path) -> list[ReasoningEvent]:
    ...
```

### Why It Matters More Than Anything Else

The entire testing philosophy (TESTING-PHILOSOPHY.md Principle 1, Principle 13) is built on the premise that reasoning quality is what matters, not just output correctness. The 7-move reasoning decomposition (HYPOTHESIS_FORMATION through SELF_CRITIQUE) is described as a cornerstone of the evaluation intelligence layer. But right now, there is no code that extracts these moves from transcripts. The gap is:

```
TESTING-PHILOSOPHY.md says:    "Each move is scored independently"
3.1c.2 delivers:               CLIAttemptState (4 enum values -- binary compliance)
3.1c.3-02 needs:               Per-move transcript segments to score
```

The reasoning timeline is the missing bridge. Without it:
- 3.1c.3-02 (reasoning decomposer) must build transcript parsing AND move extraction AND scoring from scratch
- 3.1c.3-10 (recommendation engine) has no structured input to map failures to specific reasoning steps
- 3.1c.3-05 (tier manager) cannot distinguish "agent that reasons well but has a knowledge gap" from "agent that reasons poorly across the board"

With it:
- 3.1c.3-02 only needs to build the scorer -- the extraction is done
- 3.1c.3-10 can map failures to specific reasoning moves ("this agent's QUERY_FORMULATION is weak")
- 3.1c.3-05 can track per-move quality trends over time
- The Plan 06 retry produces not just "pass/fail" but "a full reasoning quality profile for 4 calibration contracts"

### How It Fits Within Existing Waves

Add it to Plan 02 (CLIAttemptState + transcript analysis). Plan 02 already creates a module in `testing/evaluation/` that processes JSONL transcripts. The reasoning timeline extractor is a natural extension:

```
cli_attempt_state.py            -> CLIAttemptState enum (4 values)
reasoning_timeline.py [NEW]     -> list[ReasoningEvent] (6 move types)
```

Both consume the same `TranscriptParser` input. Both live in `testing/evaluation/`. The timeline extractor adds ~100-150 lines of code.

### What It Costs

- **LOC:** ~120 lines for the extractor, ~80 lines for tests = ~200 total
- **Complexity:** LOW -- the move type classification is heuristic, not LLM-based:
  - Text before first tool call -> `hypothesis`
  - Bash commands with `alphaswarm query` -> `query_formulation` + `query_execution`
  - Text immediately after tool_result -> `result_interpretation`
  - Text referencing multiple prior results -> `evidence_integration`
  - Final structured output -> `conclusion`
- **Risk:** Heuristic classification will be imprecise (~70% accuracy). But 70% accuracy now is infinitely better than 0% data for 3.1c.3 to work with. 3.1c.3-02 can refine with LLM-based classification later -- but it needs the STRUCTURE to exist first.

### What It Enables That Nothing Else Does

This is the only addition that transforms 3.1c.2 from "hardening" (defensive, blocking) to "hardening + intelligence seed" (defensive + generative). Every other improvement in Section C makes enforcement better or produces cleaner data. This one produces an entirely new kind of data -- structured reasoning traces -- that is the foundation the entire Tier 2 intelligence layer is built on.

The testing philosophy document says: "The most dangerous failure is a workflow that 'works' but reasons badly." The reasoning timeline is the instrument that makes this failure visible. Without it, the evaluation framework can detect non-compliance but not bad reasoning. With it, the evaluation framework begins to answer the question it was designed to answer: "Did the agent THINK correctly?"

---

## Summary of Recommendations

| Priority | Recommendation | Section |
|----------|---------------|---------|
| 1 | Add structured reasoning timeline extraction to Plan 02 | E |
| 2 | Define observation schema for 3.1c.3 intelligence consumption | C.1 |
| 3 | Merge Plans 04 and 05 to compress wave structure | C.4 |
| 4 | Create reference ideal agent transcripts for calibration contracts | C.2 |
| 5 | Add env-var propagation fallback mechanism in Plan 01 | C.5 |
| 6 | Extract query-result usage chain from transcripts in Plan 02 | C.3 |
| 7 | Add intelligence-targeted debrief questions in Plan 05 | C.6 |
| 8 | Add expected findings to ground truth (Plan 03) | D.4 |
| 9 | Add failure_mode field to IntegrityViolation | D.5 |
| 10 | Add timing telemetry and correlation IDs to pipeline | C.8, C.9 |

**The overarching theme:** Phase 3.1c.2 is currently a lock (enforcement only). It should also be a lens (observation and structured data capture). The enforcement mechanisms are well-designed and should not change. But every enforcement touchpoint is also a data capture opportunity, and that data is what the downstream intelligence layer needs to function. The marginal effort to capture structured data alongside enforcement is small. The downstream impact of having vs. not having that data is enormous.
