# Intelligence Bootstrap Review: Can 3.1c.2 Do More for 3.1c.3?

**Reviewer:** ML Systems Architect
**Date:** 2026-03-02
**Scope:** Data format readiness, missing signals, early intelligence, observation schema, feedback loop architecture
**Confidence:** HIGH on format analysis, MEDIUM on early intelligence proposals (grounded in source code, not speculation)

---

## A. Data Format Readiness

For each Tier 2 intelligence module, I assessed whether 3.1c.2's planned outputs are in the format 3.1c.3 needs. The assessment is based on reading: the 3.1c.2 output contract (CONTEXT.md), Plan 06's artifact structure, the 3.1c.3 CONTEXT.md (12 plans), existing `cal-*.json` observation format, and the `models.py` data definitions.

| # | Intelligence Module | What Data It Needs | What 3.1c.2 Produces | Format Match? | Gap |
|---|---|---|---|---|---|
| 1 | **Scenario synthesis** | Skill/agent prompt text + coverage gaps + untested behavioral claims | Observation JSONs with agent type, contract, findings. Plan 06 captures what agents DO, not what skills CLAIM. | PARTIAL | **Missing: No extraction of testable claims from agent prompts.** The synthesizer (3.1c.3 Plan 04) needs a `claims_index` -- a structured list of what each agent/skill prompt says it does (e.g., "must query BSKG before conclusions"). 3.1c.2 captures execution traces but not the gap between "promised" and "delivered." |
| 2 | **Coverage radar** | Test results across 4 axes (workflow, dimension, tier, contract) | Plan 06 produces observations tagged with `contract_id`, `agent_type`, `graph_stats`, `queries_executed`. EvaluationResult has `score_card.workflow_id` and `score_card.dimensions`. | GOOD | **Minor: No `tier` field in observations.** Coverage radar's Axis 3 needs tier classification (Core/Important/Standard) per workflow. The current `cal-*.json` format has no tier field. The radar currently relies on `tier_distribution` passed at init time, which is external to the observation data. This works but means the tier mapping is duplicated (once in eval contract templates, once in radar constructor). |
| 3 | **Adaptive tier management** | Score history + meta-eval disagreement data | Plan 06 produces observation files that will be evaluated by the dual-Opus evaluator. Tier manager needs `EvaluationResult.score_card.dimensions[].score` over time + inter-rater disagreement metric. | GOOD | **Minor: No explicit disagreement field in observation output.** The dual-Opus evaluator produces two scores; their disagreement is computed at evaluation time. 3.1c.2 does not persist the raw dual scores -- only the final merged score. The tier manager needs the disagreement metric to trigger auto-promotion. **Recommendation:** Add `evaluator_disagreement: float` to `EvaluationResult.metadata` when dual-Opus runs. |
| 4 | **Behavioral fingerprinting** | Reasoning move profiles + tool call sequence patterns per run | Plan 06 produces transcripts (JSONL) with full tool call sequences. The `TranscriptParser` can extract `ToolSequenceEntry` objects. | GOOD | **Minor: No pre-computed fingerprint vector.** The fingerprinter (3.1c.3 Plan 06) needs to compute a `BehavioralFingerprint` from raw transcripts. 3.1c.2 provides the raw data but not a standardized intermediate representation. This is acceptable -- the fingerprinter is designed to work from raw transcripts. |
| 5 | **Self-healing contracts** | Dimension score distributions over time | Same as tier manager (needs `EvaluationResult` with dimension scores). Contract healer detects CEILING, FLOOR, ZERO_VARIANCE, and (planned) bimodal patterns. | GOOD | **No gap.** The existing `EvaluationResult.score_card.dimensions` list provides exactly what the contract healer needs. 3.1c.2's Plan 06 retry will produce the first real data points. |
| 6 | **Cross-workflow learning** | Evaluation insights indexed by workflow ID | Plan 06 observations have `agent_type` but the current `cal-*.json` format does NOT have a `workflow_id` field. The observation format is keyed by `contract_id + agent` (e.g., `cal-01-attacker`). | PARTIAL | **Missing: `workflow_id` field in observation data.** Cross-workflow learning needs to index insights by which skill/workflow was being evaluated, not just which agent ran. A `vrs-attacker` running under `/vrs-investigate` vs `/vrs-audit` produces different reasoning patterns. The current observation format conflates agent identity with workflow identity. **Recommendation:** Add `workflow_id` to observation JSONs in Plan 06. |
| 7 | **Reasoning decomposition** | Per-move transcript segments (hypothesis, evidence, conclusion sections) | Plan 06 captures JSONL transcripts. The `TranscriptParser` has `get_text_between_tools()` and `get_bskg_queries()` methods. `MoveAssessment` model exists with 7 `ReasoningMove` values. | GOOD | **Minor: No pre-segmented transcript.** The decomposer (3.1c.3 Plan 02) must segment transcripts into reasoning moves from raw text. 3.1c.2 provides raw transcripts but not move-level segmentation. This is acceptable -- segmentation IS the decomposer's job. However, the transcript format must preserve message ordering and tool-call boundaries. The `TranscriptParser` already handles this. |
| 8 | **Evaluator self-improvement** | Inter-rater disagreement data across multiple evaluations | Same as adaptive tier management. Needs persistent `evaluator_disagreement` metric. | PARTIAL | **Same gap as #3.** The dual-Opus evaluator runs in 3.1c Plan 07 scope, and its disagreement metric needs to be persisted in `EvaluationResult`. 3.1c.2 does not control this format (it is upstream), but Plan 06's retry will exercise the evaluator and produce the first real disagreement data. **If the evaluator doesn't persist disagreement, the self-improvement module has no signal.** |
| 9 | **Compositional stress testing** | Agent composition configs (which agents present, missing, doubled) | 3.1c.2 Plan 06 runs a FIXED composition (3-5 agents, attacker + defender per contract). It does NOT test variant compositions. | NOT PRODUCED | **3.1c.2 does not produce composition variant data.** This is expected -- compositional stress testing is explicitly deferred to post-Phase 4 (needs Agent Teams Debate). No action needed from 3.1c.2. |
| 10 | **Gap-driven synthesis loop** | Coverage radar output + synthesizer scenarios | Depends on modules 1 and 2 (coverage radar + scenario synthesis). 3.1c.2 does not directly produce either. | NOT PRODUCED (EXPECTED) | **No gap.** This is a composed module that consumes outputs from modules 1 and 2. It has no independent data dependency on 3.1c.2. |

### Summary

- **4 modules have GOOD format match** (fingerprinting, self-healing contracts, reasoning decomposition, behavioral fingerprinting)
- **3 modules have PARTIAL match** (scenario synthesis, cross-workflow learning, evaluator self-improvement) -- actionable gaps
- **2 modules are NOT PRODUCED** (composition testing, gap-driven loop) -- expected, no action needed
- **1 module has a MINOR gap** (coverage radar tier field)

### Critical Actionable Gaps

1. **Add `workflow_id` to observation JSON format** -- needed by cross-workflow learning (module 6), scenario synthesis (module 1), and coverage radar axis 1. Currently observations are keyed by `contract_id + agent`, losing the workflow context.

2. **Persist `evaluator_disagreement` in EvaluationResult.metadata** -- needed by adaptive tier management (module 3) and evaluator self-improvement (module 8). Without this, two of the most important feedback signals are lost.

3. **Capture testable claims from agent prompts** -- needed by scenario synthesis (module 1). This is a one-time extraction task, not a per-run data capture. Could be done as a pre-computation step in Plan 06's preflight.

---

## B. Missing Data Signals

3.1c.2 Plan 06 will be the first run of the hardened harness with real agents. This is a unique opportunity to capture signals that would be EXTREMELY expensive to reconstruct later. Here is what Plan 06 SHOULD capture but currently does NOT plan to.

### B1. Timing Data (Per-Phase Reasoning Duration)

**What:** Wall-clock time from first tool call to last tool call, broken into phases: (a) graph build phase, (b) query phase, (c) analysis/reasoning phase, (d) report generation phase.

**Why it matters:** The reasoning decomposer (3.1c.3 Plan 02) can correlate time-per-phase with quality. An agent that spends 90% of time building the graph and 10% reasoning is fundamentally different from one that queries extensively. Timing profiles are the cheapest behavioral fingerprint.

**What to capture:** For each agent transcript, compute:
```json
{
  "timing": {
    "total_duration_s": 240,
    "build_kg_duration_s": 45,
    "query_duration_s": 90,
    "inter_query_gap_avg_s": 12,
    "first_query_at_s": 50,
    "last_query_at_s": 180,
    "post_query_reasoning_s": 60
  }
}
```

**Effort:** LOW. The `TranscriptParser` already extracts timestamps per tool call. Computing phase durations is ~20 lines of code in the post-session analysis.

### B2. Tool Call Sequences (Ordered Interaction Patterns)

**What:** The complete sequence of tool calls in order, abstracted to tool types (not full arguments).

**Why it matters:** The behavioral fingerprinter (3.1c.3 Plan 06) needs this as its core input. A tool call sequence like `[build-kg, query, query, query, Read, query, Read]` vs `[Read, Read, build-kg, query]` reveals fundamentally different reasoning strategies. The sequence IS the behavioral fingerprint.

**What to capture:** For each agent:
```json
{
  "tool_sequence": [
    {"tool": "Bash", "subtype": "build-kg", "index": 0, "ts": "..."},
    {"tool": "Bash", "subtype": "query", "index": 1, "ts": "..."},
    {"tool": "Read", "subtype": "contract", "index": 2, "ts": "..."},
    {"tool": "Bash", "subtype": "query", "index": 3, "ts": "..."}
  ]
}
```

**Effort:** LOW. `TranscriptParser.get_tool_calls()` already extracts this. The `subtype` classification (build-kg vs query vs other) needs ~15 lines.

### B3. Query Progression Quality (Specificity Over Time)

**What:** Track how query specificity evolves over the session. First queries are often generic ("functions without access control"), later queries should be specific ("function withdraw has state_write_after_external_call").

**Why it matters:** This is the single strongest signal for distinguishing genuine reasoning from performative compliance. An agent that asks progressively more specific queries is ACTUALLY reasoning from graph data. An agent that asks the same generic queries repeatedly is checkbox-checking.

**What to capture:** For each query in sequence:
```json
{
  "query_progression": [
    {"index": 0, "query": "all functions", "specificity": "generic", "result_count": 12},
    {"index": 1, "query": "functions with external calls", "specificity": "filtered", "result_count": 3},
    {"index": 2, "query": "withdraw function reentrancy guard", "specificity": "targeted", "result_count": 1}
  ]
}
```

**Specificity heuristic:** Count named entities (function names, property names, specific values) in query text. 0 = generic, 1-2 = filtered, 3+ = targeted. Simple regex, ~10 lines.

**Effort:** LOW-MEDIUM. The query extraction already exists in `TranscriptParser.get_bskg_queries()`. Adding specificity classification is ~25 lines.

### B4. Failure Mode Fingerprints (When Agents Fail, How Do They Fail?)

**What:** When an agent produces a low-quality result or fails entirely, capture the trajectory that led to the failure.

**Why it matters:** The recommendation engine (3.1c.3 Plan 10) needs to map failure types to root causes. Without failure fingerprints, it has to re-derive the diagnosis every time. Captured once, the fingerprint enables instant classification: "This looks like a query-routing failure" vs "This looks like a context-leakage violation."

**What to capture:**
```json
{
  "failure_fingerprint": {
    "classification": "query_failure",
    "trajectory": ["build-kg:success", "query:empty", "query:empty", "Read:fallback", "fabricate"],
    "pivot_point": "query:empty at index 1",
    "fallback_behavior": "switched from CLI to direct file read",
    "cli_attempt_state": "ATTEMPTED_FAILED"
  }
}
```

**Effort:** MEDIUM. Requires combining `CLIAttemptState` with tool sequence analysis. Plan 06 already validates integrity -- extending it to classify the failure TYPE is ~40 lines.

### B5. Graph Query Result Overlap (Information Gain Per Query)

**What:** For agents that run multiple queries, measure how much NEW information each subsequent query provides vs repeating what was already known.

**Why it matters:** An agent that runs 5 queries but gets the same 3 nodes back each time is wasting tokens and not demonstrating deep graph engagement. High overlap means the agent is not learning from its queries -- a key signal for the Graph Value Scorer and reasoning decomposer.

**What to capture:**
```json
{
  "query_overlap": {
    "queries": 5,
    "unique_node_ids_seen": 8,
    "cumulative_new_ids_per_query": [4, 3, 1, 0, 0],
    "information_gain_curve": "diminishing",
    "saturation_at_query": 3
  }
}
```

**Effort:** MEDIUM. Requires parsing query results for node IDs (the `TranscriptParser` already has `_BSKG_NODE_ID_RE` for this) and tracking a running set. ~30 lines.

---

## C. Early Intelligence Opportunities

These are concrete ways 3.1c.2 can bootstrap lightweight intelligence that does NOT wait for 3.1c.3, integrated into the existing 6-plan structure.

### C1. Query Progression Scorer (embed in Plan 04 integrity pipeline)

**What intelligence it provides:** A numerical score (0-100) measuring whether an agent's queries became progressively more specific over the session. This is the simplest and most reliable proxy for "genuine graph engagement" vs "performative querying."

**How it integrates:** Add as check 14 in `agent_execution_validator.py` (Plan 04 already extends this to 13 checks). The scorer consumes the same `TranscriptParser` data that check 13 (CLIAttemptState) already uses. It does not require new infrastructure -- just a new check function.

**Why now vs later:** The data from Plan 06 is the first real agent transcript data. If we capture progression scores NOW, the coverage radar (3.1c.3 Plan 03) and behavioral fingerprinter (3.1c.3 Plan 06) have Day 1 training data. If we wait, we need to re-process transcripts after 3.1c.3 lands. Transcript re-processing is fragile because JSONL files may be rotated or cleaned.

**Scope creep risk:** LOW. This is ~30 lines added to an existing module. It does NOT change the validation logic -- it adds an informational metric to the integrity report, not a pass/fail gate.

**Implementation sketch:**
```python
# In agent_execution_validator.py
def _compute_query_progression_score(queries: list[BSKGQueryEvent]) -> float:
    """Score 0-100 based on query specificity progression.

    Generic queries score 0-1 entity mentions. Specific queries score 3+.
    The score rewards: (a) increasing specificity over time, (b) using
    results from previous queries in subsequent ones.
    """
    if len(queries) < 2:
        return 50.0  # Single query = neutral (can't assess progression)

    # Count named entities per query (function names, property names, etc.)
    entity_re = re.compile(r'\b(function|modifier|variable|withdraw|deposit|transfer|balance|guard|reentrancy|oracle|staleness|access|owner)\b', re.IGNORECASE)
    specificity_scores = [len(entity_re.findall(q.command)) for q in queries]

    # Is the trend increasing?
    increasing_pairs = sum(1 for i in range(1, len(specificity_scores))
                          if specificity_scores[i] >= specificity_scores[i-1])
    progression_ratio = increasing_pairs / (len(specificity_scores) - 1)

    return round(progression_ratio * 100)
```

### C2. Lightweight Timing Profile (embed in Plan 06 post-session analysis)

**What intelligence it provides:** Per-agent timing breakdown (build vs query vs reasoning vs report). This is the cheapest behavioral fingerprint and directly feeds the fingerprinter (3.1c.3 Plan 06) and reasoning decomposer (3.1c.3 Plan 02).

**How it integrates:** After Plan 06 Task 2 runs the Agent Teams session and validates integrity, add a post-processing step that computes timing profiles from each transcript and appends them to the observation JSON. This fits naturally into Task 3 (record results).

**Why now vs later:** Timing data is only available from the raw JSONL transcripts with microsecond-precision timestamps. If transcripts are not preserved (Claude Code rotates session files), the timing data is lost forever. Computing it at capture time is trivially cheap; reconstructing it later is impossible.

**Scope creep risk:** LOW. This is a read-only computation on existing data, ~20 lines added to Task 3's result recording.

**Implementation sketch:**
```python
def compute_timing_profile(parser: TranscriptParser) -> dict:
    """Extract phase-level timing from a transcript."""
    tool_calls = parser.get_tool_calls()  # Already exists
    if not tool_calls:
        return {"total_duration_s": 0}

    build_calls = [t for t in tool_calls if "build-kg" in (t.command or "")]
    query_calls = [t for t in tool_calls if "query" in (t.command or "")]

    first_ts = tool_calls[0].timestamp
    last_ts = tool_calls[-1].timestamp

    return {
        "total_duration_s": _ts_diff(first_ts, last_ts),
        "build_kg_count": len(build_calls),
        "query_count": len(query_calls),
        "first_query_offset_s": _ts_diff(first_ts, query_calls[0].timestamp) if query_calls else None,
        "inter_query_gap_avg_s": _mean_gaps(query_calls) if len(query_calls) > 1 else None,
    }
```

### C3. Tool Sequence Capture (embed in Plan 02 JSONL verification)

**What intelligence it provides:** The ordered sequence of tool types used by each agent, abstracted to `[build-kg, query, query, Read, query]` form. This is the core input for behavioral fingerprinting and the cheapest form of trajectory recording.

**How it integrates:** Plan 02 (JSONL transcript verification + CLIAttemptState) already parses transcripts and extracts Bash commands. Adding tool sequence extraction is a natural extension -- store the sequence alongside the CLIAttemptState in the verification output.

**Why now vs later:** The counterfactual replayer (3.1c.3 Plan 06) needs trajectories. If 3.1c.2 captures tool sequences from its Plan 06 retry, the replayer has seed data on Day 1. Without it, the replayer launches with no historical data and needs to wait for NEW sessions.

**Scope creep risk:** LOW. This is ~15 lines in the transcript verification module. It does not change any validation logic.

**Implementation sketch:**
```python
def extract_tool_sequence(parser: TranscriptParser) -> list[dict]:
    """Extract ordered tool type sequence from transcript."""
    tool_calls = parser.get_tool_calls()
    sequence = []
    for tc in tool_calls:
        subtype = "other"
        if tc.tool_name == "Bash":
            if "build-kg" in (tc.command or ""):
                subtype = "build-kg"
            elif "query" in (tc.command or ""):
                subtype = "query"
        elif tc.tool_name == "Read":
            subtype = "read-file"
        sequence.append({
            "tool": tc.tool_name,
            "subtype": subtype,
            "index": tc.tool_call_index,
        })
    return sequence
```

### C4. Observation Enrichment Hook (embed in Plan 05 debrief stage)

**What intelligence it provides:** After the debrief captures agent self-assessment (Stage 9), enrich the observation JSON with all computed metrics (timing, tool sequence, query progression, CLIAttemptState) in a standardized `_enrichment` block. This creates a single "fat observation" that every intelligence module can consume without re-parsing transcripts.

**How it integrates:** Plan 05 adds Stage 9 (debrief) to evaluation_runner.py. Add a Stage 10 (or extend Stage 9) that reads the transcript, computes all enrichment metrics, and writes them into the observation JSON before persistence. This is the last touch before the observation file is finalized.

**Why now vs later:** If observations are persisted WITHOUT enrichment, every intelligence module in 3.1c.3 must independently re-parse transcripts. This duplicates effort across 10 modules and creates inconsistency risk (each module may parse slightly differently). Enriching once at capture time ensures all modules see the same derived data.

**Scope creep risk:** MEDIUM. This touches the evaluation pipeline's output format. However, it is purely additive (new `_enrichment` field, no modification to existing fields) and the enrichment logic is already available from C1-C3 above.

**Implementation sketch:**
```python
# In evaluation_runner.py, after Stage 9 (debrief)
def _enrich_observation(obs_path: Path, transcript_path: Path | None) -> None:
    """Add computed metrics to observation JSON for intelligence consumption."""
    if not transcript_path or not transcript_path.exists():
        return

    obs = json.loads(obs_path.read_text())
    parser = TranscriptParser(transcript_path)

    obs["_enrichment"] = {
        "version": "3.1c.2",
        "timing_profile": compute_timing_profile(parser),
        "tool_sequence": extract_tool_sequence(parser),
        "query_progression_score": _compute_query_progression_score(parser.get_bskg_queries()),
        "query_overlap": _compute_query_overlap(parser),
        "enriched_at": datetime.now(timezone.utc).isoformat(),
    }

    obs_path.write_text(json.dumps(obs, indent=2))
```

### C5. Claims Index Pre-Computation (embed in Plan 06 Task 1 preflight)

**What intelligence it provides:** A structured index of testable claims extracted from the agent/skill prompts that Plan 06 will exercise. Example: The vrs-attacker prompt says "construct exploit paths using BSKG queries" -- this becomes a testable claim that the scenario synthesizer (3.1c.3 Plan 04) can verify.

**How it integrates:** Plan 06 Task 1 (preflight) already validates that configs, ground truth, and tooling are in place. Add a step that reads the agent prompts from `src/alphaswarm_sol/agents/catalog.yaml` and extracts testable behavioral claims into `.vrs/ground-truth/claims-index.json`.

**Why now vs later:** The scenario synthesizer needs this index to generate targeted test scenarios. Building it now means the synthesizer can start generating scenarios from Day 1 of 3.1c.3, instead of spending its first plan doing the extraction.

**Scope creep risk:** MEDIUM. Extracting claims from unstructured prompt text is inherently heuristic. But a simple regex-based extraction (verbs + tools + behavioral patterns) produces a useful first pass that humans can review.

**Implementation sketch:**
```python
# Simple claim extraction from catalog.yaml agent descriptions
import yaml, re

def extract_testable_claims(catalog_path: Path) -> list[dict]:
    catalog = yaml.safe_load(catalog_path.read_text())
    claims = []
    # Look for behavioral verbs + tool references
    behavior_re = re.compile(
        r'(must|should|always|never|required to|constructs?|builds?|queries?|verif(?:y|ies)|analyz(?:e|es))\s+(.{10,80})',
        re.IGNORECASE
    )
    for agent in catalog.get("agents", []):
        desc = agent.get("description", "") + " " + agent.get("system_prompt", "")
        for match in behavior_re.finditer(desc):
            claims.append({
                "agent": agent["name"],
                "verb": match.group(1),
                "claim": match.group(0).strip(),
                "source_field": "description" if match.group(0) in agent.get("description", "") else "system_prompt",
                "tested": False,
            })
    return claims
```

---

## D. Observation Schema Design

### The Problem

3.1c.2 currently produces observation JSONs in a format designed for Plan 12's integrity validation (see `cal-01-attacker.json`). This format is ad-hoc: it has `contract`, `agent`, `findings`, `graph_stats`, `queries_executed`, and `session_metadata`. But the 10 intelligence modules need a richer, more standardized format.

The key tension is: 3.1c.2 should NOT over-engineer the schema (that is 3.1c.3's job), but it SHOULD establish a minimal extensible schema that doesn't require format migration later.

### Proposed Minimal Observation Event Schema

```json
{
  "$schema": "observation-event-v1",

  "identity": {
    "session_id": "plan12-retry-2026-03-02-001",
    "observation_id": "obs-cal01-attacker-001",
    "contract_id": "cal-01",
    "contract_name": "ReentrancyClassic",
    "contract_path": "tests/contracts/ReentrancyClassic.sol",
    "agent_id": "attacker-001",
    "agent_type": "vrs-attacker",
    "workflow_id": "evaluation-calibration",
    "batch_id": "plan12-retry"
  },

  "execution": {
    "started_at": "2026-03-02T13:57:00Z",
    "completed_at": "2026-03-02T14:01:00Z",
    "duration_s": 240,
    "cli_attempt_state": "ATTEMPTED_SUCCESS",
    "transcript_path": "~/.claude/projects/.../agent-001.jsonl",
    "isolation_mode": "worktree",
    "enforcement_config": "delegate_guard_config_eval.yaml"
  },

  "graph": {
    "build_identity": "271b6cf5c178",
    "graph_path": ".vrs/ground-truth/cal-01/graph.toon",
    "nodes": 12,
    "edges": 17,
    "build_source": "ground_truth"
  },

  "queries": {
    "count": 4,
    "successful": 3,
    "empty_result": 1,
    "queries": [
      {
        "index": 0,
        "command": "uv run alphaswarm query \"all functions\" --graph ...",
        "result_count": 12,
        "specificity": "generic",
        "timestamp": "2026-03-02T13:58:15Z"
      }
    ]
  },

  "findings": [
    {
      "id": "FND-0001",
      "title": "Classic Reentrancy via CEI Violation",
      "severity": "critical",
      "vulnerability_class": "reentrancy",
      "confidence": 0.95,
      "graph_evidence_refs": ["function:cf22e8838868"]
    }
  ],

  "integrity": {
    "validator_version": "13-checks",
    "verdict": "PASS",
    "critical_violations": 0,
    "warning_violations": 1,
    "violations": []
  },

  "debrief": {
    "layer_used": "send_message",
    "confidence": "high_confidence",
    "primary_hypothesis": "...",
    "key_queries": ["..."],
    "self_assessment": "..."
  },

  "_enrichment": {
    "version": "3.1c.2",
    "enriched_at": "2026-03-02T14:05:00Z",
    "timing_profile": {},
    "tool_sequence": [],
    "query_progression_score": 75,
    "query_overlap": {}
  }
}
```

### Design Principles

1. **Namespaced sections, not flat keys.** Each intelligence module reads ONE section: fingerprinter reads `_enrichment.tool_sequence`, coverage radar reads `identity.workflow_id`, tier manager reads from `EvaluationResult` (not observation JSON). Namespacing prevents key collisions as modules grow.

2. **`identity` block is required, everything else optional.** A minimal observation that only has `identity` and `execution` is valid. Modules that need richer data check for their section's existence and degrade gracefully.

3. **`_enrichment` is additive-only, versioned.** The `_enrichment` block is written ONCE after capture and never modified. The `version` field enables intelligence modules to know which enrichment pipeline produced the data. Future 3.1c.3 versions can add fields without breaking existing consumers.

4. **`transcript_path` is in `execution`, not computed.** The path to the raw JSONL transcript is captured at observation time. This ensures intelligence modules can always go back to the source if enrichment is insufficient. Transcript paths are user-level (`~/.claude/projects/`), accessible regardless of worktree isolation.

5. **`workflow_id` is explicit, not inferred.** This is the critical addition vs the current format. The `workflow_id` tells intelligence modules which skill/workflow was being evaluated. Without it, cross-workflow learning (module 6) is impossible.

### Backward Compatibility

The existing `cal-*.json` files from Plan 12 Batch 1 do NOT conform to this schema. That is acceptable -- they are INVALID data anyway (integrity check FAILED). Plan 06 (retry) should produce observations in the new schema. Migration is not needed for invalid data.

### What 3.1c.2 Should Actually Do

1. **Plans 01-05:** No schema change needed. These plans build enforcement infrastructure, not data capture.
2. **Plan 06:** Use the schema above for all observation JSONs in `.vrs/observations/plan12-retry/`. The `_enrichment` block is populated as part of Task 3 (post-session analysis).
3. **Document the schema** in a lightweight `observation-schema-v1.md` alongside the observation files. This becomes the contract that 3.1c.3 intelligence modules import.

---

## E. Feedback Loop Architecture

### The Vision

```
Test (3.1c.2) -> Evaluate (3.1c.2/3.1c.3) -> Improve (3.1f) -> Re-test (continuous)
```

### What 3.1c.2 Builds

- **Test:** Plan 06 runs real Agent Teams evaluation sessions with hardened enforcement
- **Evaluate:** Plans 01-05 build the enforcement + validation pipeline (delegate_guard, CLIAttemptState, ground truth, auto-reject, debrief)

### What 3.1c.3 Builds

- **Evaluate (deeper):** Intelligence modules that assess reasoning QUALITY, not just integrity
- **Identify:** Coverage radar finds gaps, recommendation engine diagnoses root causes, scenario synthesizer generates new tests

### What 3.1f Builds

- **Improve:** The proven loop closure that takes evaluation results and actually modifies prompts/patterns/graph builder

### The Missing Interface Contract

There IS a missing interface between 3.1c.2's outputs and 3.1f's inputs. Specifically:

**3.1f needs to know:**
1. Which agents failed and how (from integrity reports + EvaluationResult)
2. Which reasoning moves are weakest (from per-move scores in MoveAssessment)
3. What the root cause is (agent prompt? graph builder? query routing? -- from recommendation engine)
4. What specific fix to attempt (from recommendation engine's `specific_fix` field)
5. Whether the fix worked (from before/after EvaluationResult comparison)

**What is currently defined:**
- Items 1-4 are produced by 3.1c.3 (Plans 02, 08, 10)
- Item 5 requires re-running the SAME scenario with modified inputs -- this is the improvement loop

**What is NOT defined anywhere:**
- **The improvement trigger contract.** When does an evaluation result trigger an improvement attempt? What score threshold? Which modules' outputs are required before triggering? There is no `ImprovementTrigger` model or protocol defined.
- **The sandbox input format.** 3.1f says "prompt experiments run against copies in test project `.claude/` folders." But what does the improvement module receive? A `RecommendationReport`? An `EvaluationResult` with per-move scores? A natural-language fix suggestion? The interface between "recommendation" and "sandbox experiment" is undefined.
- **The regression comparison protocol.** After a prompt change, how do we know it helped? 3.1c.2 establishes the FIRST baseline (Plan 06 retry results). 3.1f needs to compare against THIS baseline. But the comparison format -- which fields, which thresholds, which dimensions -- is not specified.

### Recommendation: Define a Minimal Improvement Trigger Interface in 3.1c.2

3.1c.2 should NOT build the improvement loop (that is 3.1f's scope). But it SHOULD define the interface contract that connects evaluation outputs to improvement inputs. This is analogous to how 3.1c.2 defines CLIAttemptState (an enum consumed by 3.1c.3) -- define the data structure now, implement the consumer later.

**Proposed `ImprovementTrigger` model:**

```python
class ImprovementTrigger(BaseModel):
    """Interface between evaluation results and the improvement loop (3.1f).

    Defined in 3.1c.2 (data structure only).
    Consumed in 3.1f (improvement loop implementation).
    """
    trigger_id: str
    workflow_id: str
    weakest_dimension: str
    weakest_move: ReasoningMove | None
    current_score: int
    baseline_score: int
    regression_delta: int  # negative = regression
    root_cause: str  # "agent_prompt" | "graph_builder" | "query_routing" | "evaluation_contract"
    recommended_fix: str  # Natural language fix suggestion
    fix_target_file: str  # Which file to modify
    evidence: list[str]  # Supporting data points
    priority: str  # "critical" | "high" | "medium" | "low"
```

**Where to define it:** In `models.py` alongside the existing `EvaluationResult`, `MoveAssessment`, and `ReasoningAssessment` models. This is a forward-declaration of the interface, not an implementation.

**Scope creep risk:** LOW. This is a Pydantic model definition (~20 lines). No implementation logic. It establishes the contract without building the consumer.

---

## F. Consolidated Recommendations

### Must-Do (incorporate into 3.1c.2 plans, minimal scope increase)

| # | What | Where | LOC | Risk |
|---|---|---|---|---|
| F1 | Add `workflow_id` to observation JSON format | Plan 06 observation template | ~5 | LOW |
| F2 | Capture tool sequences in transcript verification | Plan 02 (CLIAttemptState module) | ~15 | LOW |
| F3 | Compute timing profiles in post-session analysis | Plan 06 Task 3 | ~20 | LOW |
| F4 | Define `ImprovementTrigger` model in models.py | Plan 04 or Plan 05 (model extension) | ~20 | LOW |
| F5 | Document observation schema v1 | Plan 06 Task 3 | ~1 file | LOW |

**Total additional LOC:** ~60. No new modules, no new plans, no architectural changes. These are field additions and helper functions wired into existing work.

### Should-Do (high value, minor scope increase)

| # | What | Where | LOC | Risk |
|---|---|---|---|---|
| F6 | Add query progression score to integrity check (C1) | Plan 04 (check 14, informational) | ~30 | LOW |
| F7 | Add `_enrichment` block to observation JSONs (C4) | Plan 05 or Plan 06 | ~40 | MEDIUM |
| F8 | Persist `evaluator_disagreement` in EvaluationResult | Requires upstream change in evaluator | ~10 | MEDIUM (cross-module) |

**Total additional LOC:** ~80. F8 requires coordination with the reasoning evaluator module (3.1c Plan 07 scope), which makes it a cross-phase dependency.

### Could-Do (useful but deferrable without loss)

| # | What | Where | LOC | Risk |
|---|---|---|---|---|
| F9 | Claims index pre-computation (C5) | Plan 06 preflight | ~40 | MEDIUM |
| F10 | Query overlap metrics | Plan 06 post-analysis | ~30 | LOW |
| F11 | Failure mode fingerprinting | Plan 06 failure analysis path | ~40 | MEDIUM |

**Total additional LOC:** ~110. These provide Day 1 seed data for 3.1c.3 but can be reconstructed from transcripts if deferred.

### Do NOT Do (scope creep)

- Do NOT build any intelligence module logic in 3.1c.2. The module implementations belong in 3.1c.3.
- Do NOT build the improvement loop. That is 3.1f.
- Do NOT build a claims extraction LLM pipeline. A simple regex-based extraction (C5) is sufficient; LLM-powered analysis is 3.1c.3 Plan 04's scope.
- Do NOT modify the `EvaluationRunner` pipeline stages beyond adding Stage 9 (debrief) as already planned. Adding more stages risks destabilizing the pipeline before its first real run.
- Do NOT attempt compositional stress testing. This requires Agent Teams Debate infrastructure (Phase 4).

---

## G. Risk Assessment

**Overall risk of incorporating Must-Do + Should-Do recommendations:** LOW.

The recommendations add ~140 lines of code across 4 existing files, with no new modules, no new architectural patterns, and no changes to the validation logic. The primary risk is that enrichment data capture adds ~200ms per observation to the post-session analysis -- negligible compared to the Agent Teams session itself (~4 minutes per agent).

The largest risk is F8 (persisting evaluator disagreement), which requires modifying the reasoning evaluator's output format. This is a cross-module change that should be coordinated with the evaluator's maintainer. If this is too risky for 3.1c.2, it can be deferred to 3.1c.3 Plan 02 (reasoning decomposer) which already plans to modify the evaluator's output.

**What happens if we do nothing:** 3.1c.3 launches with no seed data, no timing profiles, no tool sequences, and no standardized observation schema. Each intelligence module independently parses raw transcripts (duplicated effort), and the first 2-3 plans of 3.1c.3 spend significant time establishing the data infrastructure that could have been a free by-product of 3.1c.2's Plan 06 retry. Estimated cost: 1-2 extra plans in 3.1c.3, ~300 additional LOC that could have been ~60 LOC in 3.1c.2.
