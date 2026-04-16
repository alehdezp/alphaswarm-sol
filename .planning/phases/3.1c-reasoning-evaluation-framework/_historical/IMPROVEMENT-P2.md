# Improvement Pass 2

**Pass:** 2
**Date:** 2026-02-18
**Prior passes read:** P1
**Status:** complete

## Approach

Pass 1 identified 27 surface-level problems. Pass 2 goes deeper: reading the actual code, finding contradictions between what CONTEXT.md claims exists and what actually exists, exposing interaction effects between components, and questioning whether PHILOSOPHY.md serves the product or serves itself.

## Improvements

### P2-IMP-01: EvaluationPlugin Protocol Is Already Broken -- Existing Code Violates Its Own Contract
**What:** CONTEXT.md DC-3 defines: `def score(self, collected_output: Any) -> PluginScore`. But `GraphValueScorer.score()` at `tests/workflow_harness/graders/graph_value_scorer.py:61-65` has signature `score(self, collected_output: Any, context: dict[str, Any] | None = None) -> PluginScore`. And `ReasoningEvaluator._run_plugins()` at line 201 calls `plugin.score(collected_output, context=context)` -- passing an extra kwarg the Protocol does not declare.
**Why:** This is not a cosmetic mismatch. It means the Protocol defined in `models.py:125-157` is a lie -- no class can simultaneously satisfy the Protocol and accept the `context` kwarg the evaluator actually passes. Any future plugin that correctly implements the Protocol will crash when the evaluator calls it with `context=`. The existing code only works because Python does not enforce Protocol signatures at call time unless you use `isinstance()` checks. This reveals a deeper problem: the protocol was designed before the implementation, and the implementation immediately diverged. The same thing will happen with every other "locked" interface in CONTEXT.md.
**How:** Update DC-3 in CONTEXT.md to include `context` in the Protocol signature: `def score(self, collected_output: Any, *, context: dict[str, Any] | None = None) -> PluginScore`. Fix `models.py` to match. Add a test that verifies GraphValueScorer satisfies the Protocol via `isinstance()`.
**Impacts:** 3.1c-01 (models) -- Protocol definition must change. 3.1c-04 (GVS) -- already compatible but needs test. Any future plugins must accept context kwarg.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P2-IMP-02: ObservationParser Silently Drops Parse Errors -- You Will Never Know When Hooks Fail
**What:** CONTEXT.md 3.1c-03 says "Invalid lines produce warnings, not crashes." But `observation_parser.py:117-118` does `except json.JSONDecodeError: pass` -- no warning, no counter increment during load, no logging. The `parse_errors` counter in `ObservationSummary` only increments for non-dict records (line 143), NOT for JSON decode failures. So corrupted JSONL lines vanish silently.
**Why:** The design says hooks write JSONL and the parser reads it. If hooks write malformed data (which is likely during development -- they are Python scripts with `sys.path` manipulation), you will never know. The `parse_errors` field will show 0 even when half the lines failed to parse. The pipeline health check (`PipelineHealth.health_pct`) depends on `parsed_records`, which also will not reflect dropped lines. You could run an entire evaluation session where hooks fire correctly but produce malformed JSON, and the evaluation runner would report 100% pipeline health.
**How:** Fix the parser to count JSON decode errors: `except json.JSONDecodeError: self._parse_errors += 1`. Add `parse_error_count` property. Add to CONTEXT.md 3.1c-03 exit criteria: "Parser must track and report all parse failures -- zero silent drops."
**Impacts:** 3.1c-03 (parser fix), 3.1c-08 (runner health accuracy).
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P2-IMP-03: The Entire Heuristic Evaluator Is Keyword Soup -- Not "20% Pre-Addressed" but "20% Done Wrong"
**What:** CONTEXT.md says 3.1c-07 is "~20% pre-addressed" by the existing heuristic evaluator. I read the code. The `_heuristic_dimension_score` method (reasoning_evaluator.py:359-443) scores "reasoning_depth" by counting unique tool names (line 386-388: `unique_tools = len(set(tool_seq)); score = min(100, 30 + unique_tools * 20)`). It scores "coherence" based on tool sequence length > 2 (line 392-396: `score = 60` if > 2 tools). It scores "hypothesis formation" by counting BSKG queries (line 399-401: `score = min(100, 20 + len(bskg_queries) * 20)`). The `_check_model_capability` method (lines 505-560) splits the expected_behavior description into words > 3 chars and counts how many appear in the observation text.
**Why:** This is not 20% of the way to a reasoning evaluator. It is 0% of the way because it encodes WRONG assumptions about what constitutes reasoning quality. Using 3 unique tools does not mean deep reasoning. Having a tool sequence > 2 does not mean coherent analysis. Matching keywords from a description does not validate capabilities. CONTEXT.md's "~20% pre-addressed" creates false confidence that the evaluator just needs LLM calls added. In reality, the entire scoring logic needs to be thrown away and replaced with either (a) LLM-based assessment or (b) genuinely meaningful heuristics (e.g., "did BSKG query precede the conclusion that references its results?"). The current heuristics will produce scores that look reasonable but correlate with nothing.
**How:** Change CONTEXT.md 3.1c-07 from "~20% pre-addressed" to "~5% pre-addressed (infrastructure only, scoring logic must be replaced)." Explicitly flag that the heuristic fallback should be used ONLY for simulated mode where we know scores are meaningless. Real evaluation MUST use LLM scoring or be clearly labeled as unreliable.
**Impacts:** 3.1c-07 scope increases. 3.1c-08 runner must tag heuristic-scored results as `reliability: low`.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P2-IMP-04: Scenarios and Contracts Are Redundant Systems That Will Drift
**What:** CONTEXT.md distinguishes between "32 use-case scenarios" (`.planning/testing/scenarios/use-cases/`) and "51 evaluation contracts" (`src/.../evaluation/contracts/`). Scenarios define `expected_behavior.must_happen`, `evaluation.key_dimensions`, `evaluation.pass_threshold`, and `evaluation.regression_signals`. Contracts define `reasoning_dimensions`, `capability_checks`, `evidence_requirements`, and `metadata.tier`. Both define what "good" looks like for the same workflows. The scenario `UC-ATK-001` specifies `graph_first_compliance`, `reasoning_chain_quality`, `exploit_path_quality`, `evidence_quality` as key dimensions. The contract `agent-vrs-attacker.yaml` specifies `graph_utilization`, `evidence_quality`, `reasoning_depth`, `hypothesis_formation`, `exploit_path_construction` as reasoning dimensions. These overlap but differ.
**Why:** Two sources of truth for evaluation criteria will inevitably drift. When someone updates the contract dimensions, the scenario dimensions become stale (or vice versa). The scenario `pass_threshold: 65` and the evaluator's `pass_threshold: 60` (default in ReasoningEvaluator) already conflict. The scenario `regression_signals` are free-text strings ("Agent reads code before querying graph -> CRITICAL REGRESSION") while the contract has structured `evidence_requirements`. No code currently reconciles these. This is not theoretical drift -- the code already shows it: `EvaluationRunner.run()` loads the contract via `ReasoningEvaluator(workflow_id)` and ignores the scenario's evaluation config entirely. The scenarios' `evaluation` section is dead code.
**How:** Choose ONE authoritative source. Contracts are the right choice (machine-readable, used by the runner). Scenarios should reference contracts (`evaluation_contract: agent-vrs-attacker`) and NOT duplicate dimension definitions. Remove `evaluation.key_dimensions` and `evaluation.regression_signals` from scenario schema. Scenarios keep `expected_behavior` (natural language for humans) and `pass_threshold` (scenario-specific override). Everything else comes from contracts.
**Impacts:** 3.1c-06 (contracts become sole authority). Scenario schema simplifies. 32 scenario YAMLs need updates. Test `test_use_cases.py` assertions on `dimension_count` and `regression_signal_count` need updating.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P2-IMP-05: PHILOSOPHY.md Is an Academic Paper, Not a Product Specification
**What:** PHILOSOPHY.md is 517 lines containing 5 pillars, 15 alignment rules (A-O), 15 North Star conditions, 27 anti-patterns, a "Continuous Improvement Vision" section, and references to PRISM-Physics (Stanford/ICLR 2026), Mahalanobis distance, and Goodhart's Law. It describes an evaluation system more sophisticated than most published ML evaluation frameworks.
**Why:** This document does not serve the product. It serves itself. Every concept introduced in PHILOSOPHY.md creates obligation: cascade-aware scoring obligates implementing a DAG, Mahalanobis distance obligates implementing statistical anomaly detection, evaluator rotation obligates implementing multiple evaluator configurations, counterfactual replay obligates trajectory recording infrastructure. The document reads like a research proposal that was accidentally adopted as a spec. The actual product question is simple: "When we change an agent prompt, did it get better or worse at finding vulnerabilities?" You need: (1) run agent on known-vulnerable contract, (2) score whether it found the vulnerability and reasoned well, (3) compare before/after. Everything else -- cascade DAGs, behavioral fingerprinting, composition testing, evaluator stress testing, coverage radar -- is optimization that makes sense after you have 100+ evaluation runs showing WHERE the simple approach fails. PHILOSOPHY.md prescribes all optimizations upfront, which means 3.1c must build the entire evaluation research lab before running a single real evaluation.
**How:** Split PHILOSOPHY.md into two documents: (1) `PHILOSOPHY.md` -- the 3.1c v1 philosophy (1 page: the core question, the evaluation loop, the safety rules), and (2) `VISION.md` -- the aspirational v2+ vision (current document, clearly labeled as future scope). CONTEXT.md should reference PHILOSOPHY.md for current-phase binding constraints and VISION.md for architectural direction. No North Star condition should reference VISION.md features.
**Impacts:** Every plan in 3.1c becomes simpler. North Star reduces from 15 to 6-8 achievable conditions. Planning effort decreases dramatically.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P2-IMP-06: The "Two-Stage: Capability THEN Evaluation" Rule Hides a Conflation
**What:** CONTEXT.md Pillar 3 and Rule B mandate: "Capability contract checks FIRST (binary pass/fail). Reasoning evaluation ONLY IF capability passes." The `ReasoningEvaluator.evaluate()` method runs plugins, evaluates dimensions, AND evaluates capabilities -- all in the same pipeline. There is no separate "capability check" stage that gates the reasoning evaluation.
**Why:** The architecture says "two stages" but the code has one stage. The `_evaluate_capabilities()` method (line 252-283) produces `DimensionScore` objects that are mixed into the same `ScoreCard` as reasoning dimensions. A "failed" capability check (score < 50) does not prevent reasoning evaluation -- it just contributes a low score to the weighted average. The ScoreCard has `passed: bool` but this is computed from the weighted overall score, not from a binary capability gate. So a workflow that crashes but has good BSKG queries could still "pass" because the graph dimension score compensates. The two-stage design is stated but not implemented. If it matters (and Pillar 3 says it does), it needs actual implementation: capability checks run first, return a binary pass/fail, and reasoning evaluation only runs if all capabilities pass.
**How:** Either (a) implement the two-stage gate in `ReasoningEvaluator.evaluate()` with an early return if any capability check scores 0 (true binary gate), or (b) acknowledge that the current weighted-average approach is the actual design and update CONTEXT.md accordingly. I recommend (a) because capability failures (workflow crashed, no BSKG queries at all, no output) genuinely should block reasoning evaluation.
**Impacts:** 3.1c-07 (evaluator logic change). 3.1c-08 (runner needs to handle gate-failed results differently). Test expectations change.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P2-IMP-07: BaselineManager Has No Tier-Weighted Thresholds -- The "Locked Decision" Is Not Implemented
**What:** CONTEXT.md locks tier-weighted regression thresholds: "Core >10pt=REJECT, Important >15pt=REJECT, Standard >25pt=REJECT." The `BaselineManager` in `regression_baseline.py` uses a single `DEFAULT_REGRESSION_THRESHOLD = 5` for all workflows. There is no tier parameter, no contract loading, no per-workflow threshold.
**Why:** CONTEXT.md says this is "~30% pre-addressed" but the actual implementation has zero tier awareness. The `check_regression()` method compares against a flat threshold. When 3.1c-12 tries to implement tier-weighted detection, it will need to either (a) rewrite BaselineManager to accept contract tier metadata, or (b) wrap it with tier-aware logic. The 5-point default is also much more sensitive than any of the locked thresholds (5 vs 10/15/25), which means the current implementation will produce false regression alerts.
**How:** Update CONTEXT.md 3.1c-12 scope to explicitly note: "BaselineManager exists but has no tier awareness. Must be extended with: (a) `check_regression(workflow_id, result, tier=...)` parameter, (b) tier-to-threshold mapping, (c) contract-derived tier lookup." Change "~30% pre-addressed" to "~15% pre-addressed (data structure exists, logic needs replacement)."
**Impacts:** 3.1c-12 scope increases.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P2-IMP-08: Hook `sys.path.insert` Is a Fragility Bomb
**What:** CONTEXT.md says hooks must be lightweight. The actual hook `obs_tool_use.py` (line 15) does `sys.path.insert(0, str(Path(__file__).parents[3]))` and then imports from `tests.workflow_harness.lib.observation_writer`. Every hook does this path manipulation.
**Why:** Claude Code hooks run as standalone scripts from an unpredictable working directory. The `Path(__file__).parents[3]` calculation assumes the hook lives exactly 3 levels deep from the project root. If hooks are installed via symlinks (which `WorkspaceManager.install_hooks(extra_hooks=...)` does) or if the project structure changes, this breaks silently -- the import fails, the hook catches `ImportError` (or crashes), and observations are lost. The fix P1-IMP-12 proposed ("keep imports minimal") does not go far enough. The fundamental problem is that hooks import from a test library that lives in `tests/`, which is not a proper Python package. The `observation_writer` module should either be (a) inlined into each hook as a self-contained function, or (b) moved to an installable package that hooks can import normally.
**How:** Inline the `write_observation` function directly in each hook script (it is ~15 lines: create dir, write JSON line). Remove all `sys.path.insert` calls. Add to CONTEXT.md 3.1c-02: "Hooks MUST be self-contained scripts with no project imports. Inline all helper logic."
**Impacts:** 3.1c-02 (hook implementation). All 8 hooks need updating.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P2-IMP-09: The Observation Writer Has No Tests and a Concurrency Bug That CONTEXT.md Acknowledges But Doesn't Fix
**What:** CONTEXT.md gap #11 says: "`log_session.py` thread-safety -- observation writer uses `open(path, 'a')` without locking; concurrent hook executions could interleave JSONL lines." This is flagged as "minor risk for single-agent runs but affects multi-agent team tests."
**Why:** This is not minor. Multi-agent team tests (3.1c-11) are a core exit gate. If two hooks fire simultaneously (e.g., two agents make tool calls at the same time), their JSONL lines interleave mid-write, producing malformed JSON. The parser (P2-IMP-02) silently drops these lines. So you get: concurrent hooks -> interleaved writes -> malformed JSONL -> silent drops -> missing observations -> inaccurate evaluation -> false regression signals. And because the parser does not count these drops, you will never know. The fix is straightforward: use `fcntl.flock()` on POSIX or write complete lines atomically (Python `write()` of a single line to a file opened in append mode is atomic on most POSIX systems if the line is < PIPE_BUF, typically 4096 bytes).
**How:** Update CONTEXT.md 3.1c-02 to include: "ObservationWriter must ensure atomic line writes. Verify each JSON line < 4096 bytes (POSIX atomic write guarantee) OR use file locking for larger records."
**Impacts:** 3.1c-02 (writer implementation), 3.1c-11 (multi-agent tests depend on this).
**Research needed:** yes -- Verify whether Python's `open(path, 'a').write(line + '\n')` is atomic for lines under PIPE_BUF on macOS/Linux. 10-minute check.
**Confidence:** MEDIUM
**Status:** implemented
**Research summary:** GAP-06 RESOLVED. POSIX does NOT guarantee atomic writes to regular files (PIPE_BUF only applies to pipes). macOS PIPE_BUF=512, empirical atomic limit ~256 bytes. Our records are 400-700 bytes. Current threading.Lock is useless (hooks are separate processes). Use fcntl.flock(LOCK_EX) + flush before unlock. Negligible perf cost (~1-5μs).

### P2-IMP-10: The Contract Loader Hardcodes 10 Workflow Mappings -- Adding Contracts Requires Code Changes
**What:** `contract_loader.py` lines 26-37 define `_WORKFLOW_TO_CONTRACT` as a hardcoded dict mapping 10 workflow IDs to contract filenames. Adding a new contract requires editing this Python file.
**Why:** CONTEXT.md envisions 51 contracts. Each new contract needs a mapping entry. The current design means contract authoring (3.1c-06, YAML work) requires code changes to the loader (Python work). For template-generated contracts (P1-IMP-04's 3.1c-06b), this creates a coupling: the generator must also update the Python mapping. A simpler design: contracts use the filename as their ID (they already do: `agent-vrs-attacker.yaml` has `workflow_id: agent-vrs-attacker`), and the loader auto-discovers by scanning the directory. The mapping dict exists to handle short names from scenarios (e.g., `vrs-audit` -> `skill-vrs-audit`), but this is a scenario concern, not a contract concern.
**How:** Add to CONTEXT.md 3.1c-06: "Contract loader should auto-discover contracts by directory scan, not hardcoded mapping. Short-name resolution should be a separate utility or convention (prefix: `skill-`, `agent-`, `orchestrator-`)."
**Impacts:** 3.1c-06 (contract authoring becomes independent of code).
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P2-IMP-11: "Self-Describing Failure Narratives" Already Exist But Are Trivial -- Context Overpromises
**What:** PHILOSOPHY.md Pillar 4 describes self-describing failure narratives with "what happened" / "what should have happened" pairs as "the primary training signal for metaprompting." The `_generate_failure_narrative` method (reasoning_evaluator.py:646-674) already produces these. But the output is: `what_happened: "evidence_quality: scored 20/100 | (Heuristic: evidence_quality)"` and `what_should_have_happened: "evidence_quality: should score >= 50"`. This is a score dump, not a narrative.
**Why:** PHILOSOPHY.md gives the example: "QUERY_FORMULATION scored 35. Actual: queried 'functions with external calls' (too broad, 47 results). Ideal: should have queried 'functions calling untrusted addresses without reentrancy guards' (3 results)." The existing implementation produces none of this richness. It reports dimension names and scores, not WHAT the agent actually did or WHAT it should have done differently. Generating real narratives requires either (a) LLM-based summarization of the transcript, or (b) structured extraction from observations. Neither exists. The current implementation is not a v0.1 of failure narratives -- it is printf debugging formatted as a Pydantic model.
**How:** Update CONTEXT.md 3.1c-07 to explicitly scope: "Failure narratives v1: LLM-generated from transcript + low-scoring dimensions. The evaluator prompt must include the transcript excerpt and ask for concrete behavioral descriptions, not score summaries." Flag existing implementation as "placeholder, must be replaced."
**Impacts:** 3.1c-07 scope (narrative generation is part of LLM evaluator, not heuristic code). 3.1c-12 (metaprompting depends on narrative quality).
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P2-IMP-12: 3.1c-01 Location Conflict -- CONTEXT.md Lists Two Different Paths
**What:** CONTEXT.md Plan Summary for 3.1c-01 says "Location: `src/alphaswarm_sol/evaluation/models.py`" (line 351). But Location Resolution table says "Models | `src/alphaswarm_sol/testing/evaluation/models.py`" (line 173). The actual file is at `src/alphaswarm_sol/testing/evaluation/models.py`. The Plan Summary path does not exist.
**Why:** A planner following the Plan Summary location will create files in the wrong directory. The `testing/` intermediate directory exists because the evaluation code lives under the testing subsystem. This is a copy-paste error from the original plan structure that was not updated when 3.1d created the actual files.
**How:** Fix Plan Summary location for 3.1c-01 (and check all other plan locations) to match the Location Resolution table. All plans should use `src/alphaswarm_sol/testing/evaluation/` not `src/alphaswarm_sol/evaluation/`.
**Impacts:** All plan summaries that reference locations.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P2-IMP-13: The Graph Value Scorer Equates "First Bash Call" with "Graph-First Compliance" -- This Is Wrong
**What:** `graph_value_scorer.py:170-193` checks graph-first compliance by comparing `first_bash` index vs `first_read` index in the tool sequence. If the first `Bash` call happens before the first `Read` call, it is "graph-first compliant."
**Why:** Not all `Bash` calls are BSKG queries. An agent might run `Bash(ls contracts/)` to list files before reading them -- this would count as "graph-first compliant" under the current logic. The actual check should verify that the first Bash call is specifically an `alphaswarm` command (build-kg, query, etc.), not any Bash call. The tool sequence stores tool names (`"Bash"`) but not tool arguments. To distinguish BSKG queries from other Bash calls, you need the BSKG query data (which is available as `bskg_queries`). A correct check: "Were there BSKG queries whose timestamps precede the first Read?" or equivalently "Is there at least one BSKG query, and does the first BSKG query appear before the first code read?" The current implementation gives false graph-first compliance to any workflow that runs any Bash command first.
**How:** Fix GVS to check BSKG queries directly: "graph_first_compliant = len(bskg_queries) > 0 AND first bskg_query timestamp < first Read timestamp." This requires either (a) using ObservationParser timestamps, or (b) correlating bskg_queries with tool_sequence positions. Add to 3.1c-04 exit criteria: "Graph-first compliance must verify BSKG commands specifically, not generic Bash usage."
**Impacts:** 3.1c-04 (GVS logic fix). Scores for graph-first compliance will change.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P2-IMP-14: The Execution Waves Claim "Zero Dependencies" for Wave 1 But Models Import Contract Loader
**What:** CONTEXT.md says "Wave 1: [3.1c-01] Models + [3.1c-06] Contracts (zero dependencies)." Building on P1-IMP-05's coupling observation: the actual code shows `reasoning_evaluator.py` imports from `contract_loader.py` (line 22). The evaluator creates `ReasoningEvaluator(workflow_id)` which calls `load_contract()`. So contracts are not independent of models -- the evaluator (which uses models) requires contracts to exist.
**Why:** P1-IMP-05 noted the vocabulary coupling. This goes further: there is a runtime dependency. Wave 1 can define both models and contracts in parallel, but the evaluator (Wave 4) is the first consumer that actually requires both. The "zero dependencies" framing is misleading because it implies models and contracts can be designed independently. In reality, contract schema (what fields a contract YAML must have) is constrained by how `_evaluate_dimensions()` and `_evaluate_capabilities()` read them. If you author contracts before the evaluator code is finalized, contracts may use field names the evaluator does not recognize.
**How:** Change Wave 1 description to: "Soft coupling -- models define types, contracts define instances. Both are consumed by the evaluator (Wave 4). Contracts should follow the existing YAML schema (validated by `evaluation_contract.schema.json`), which constrains field names."
**Impacts:** Wave 1 description. Planning guidance for parallel authoring.
**Research needed:** no
**Confidence:** MEDIUM
**Status:** rejected

### P2-IMP-15: CONTEXT.md Estimates "~110 New Files, ~10,500 LOC" But ~2,500 LOC Already Exists
**What:** CONTEXT.md Estimated Scope says "~110 new files, ~5 modified files, ~10,500 LOC total." But 3.1d already delivered ~2,508 LOC across the 7 key files (reasoning_evaluator: 674, evaluation_runner: 314, observation_parser: 211, graph_value_scorer: 193, debrief_protocol: 400, regression_baseline: 251, models: 465). Plus contract_loader (225 LOC), 8 hook scripts (~50 LOC each = ~400), 10 contract YAMLs, 32 scenario YAMLs.
**Why:** The scope estimate does not account for existing code. If you adopt P1-IMP-21 (collapse to ~5 plans) and P1-IMP-24 (category-level contracts), the remaining new LOC is ~3,000-4,000 on top of ~3,000 existing. The "110 new files" number is also inflated if intelligence stubs are removed (P1-IMP-22). An accurate scope estimate prevents over-planning and sets realistic expectations for phase duration.
**How:** Update CONTEXT.md Estimated Scope: "Existing: ~3,100 LOC across ~55 files. Remaining (v1, after P1 improvements): ~3,000-4,000 new/modified LOC across ~30-40 files. Total target: ~6,000-7,000 LOC."
**Impacts:** Phase time estimation. Planning scope.
**Research needed:** no
**Confidence:** MEDIUM
**Status:** implemented

### P2-IMP-16: The Debrief Protocol's Transcript Layer Is Identical to the Evaluator's Job -- Redundant Architecture
**What:** Debrief Layer 3 (`attempt_transcript_layer` in debrief_protocol.py:164-211) reads a transcript and infers answers to debrief questions via keyword matching. The Reasoning Evaluator (3.1c-07) also reads transcripts and scores reasoning quality. Both attempt to extract meaning from the same data using similar techniques.
**Why:** The debrief protocol exists to ask agents WHY they made choices. Layer 1 (SendMessage) is genuinely different -- it gets the agent's own explanation. But Layer 3 (transcript analysis) is just a worse version of what the evaluator already does. If the evaluator can score reasoning quality from a transcript, it has already extracted the "why" -- producing a separate "debrief" from the same transcript is redundant. The debrief confidence for Layer 3 is 0.3, and the keyword matching (`_infer_from_transcript`) finds lines containing words like "strategy", "evidence", "hypothesis" -- the same kind of keyword matching the evaluator uses. Having two systems do the same thing means twice the maintenance for zero additional signal.
**How:** Simplify debrief to 2 layers: Layer 1 (SendMessage -- genuine debrief, high value) and Layer 2 (skip -- no debrief available). Remove Layer 2 (hook gate) and Layer 3 (transcript analysis) from the cascade. The evaluator already handles transcript interpretation; duplicating it in the debrief protocol adds complexity without value. If SendMessage fails, the evaluator works with transcript data directly -- no separate "debrief" needed.
**Impacts:** 3.1c-05 scope dramatically simplified. Debrief becomes a focused feature: either you can talk to the agent or you cannot.
**Research needed:** no
**Confidence:** MEDIUM
**Status:** rejected

### P2-IMP-17: The "Smart Selection Matrix" Is Overengineered -- 4 Category Templates Already Solve This
**What:** CONTEXT.md defines a Smart Selection Matrix (lines 467-480) specifying which hooks and evaluation components apply per workflow category. The 4 contract templates (`template-investigation.yaml`, `template-tool.yaml`, `template-orchestration.yaml`, `template-support.yaml`) already encode this same information in their `evaluation_config` fields. The support template already has `run_gvs: false`, `run_reasoning: false`, `debrief: false`.
**Why:** The "smart selection matrix" is a concept that sounds like it needs code. But it is already implemented as contract templates. When a workflow uses the investigation template, it gets GVS, reasoning, and debrief. When it uses the support template, it gets none of those. The contract loader + template system IS the smart selection matrix. Adding another layer of "matrix" code on top would be redundant. CONTEXT.md should acknowledge that the templates ARE the implementation of smart selection.
**How:** Remove "smart selection matrix" as a separate concept from CONTEXT.md. Replace with: "Evaluation scope is determined by the workflow's evaluation contract. The 4 category templates (investigation, tool, orchestration, support) encode the default selection. Per-workflow contracts can override."
**Impacts:** 3.1c-02 (no separate matrix implementation needed). 3.1c-06 (templates are the matrix). Reduces conceptual overhead.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P2-IMP-18: The Phase Has No Definition of "Real Workflow Execution" -- The Hardest Part Is Undefined
**What:** CONTEXT.md describes evaluation of "all 51 shipped workflows" but never specifies what "executing a workflow" means concretely. The scenarios have `input.command: "/vrs-audit tests/contracts/ReentrancyClassic.sol --agent attacker"` but this is a slash command that runs inside Claude Code. The `ClaudeCodeRunner` from 3.1b wraps `claude --print` but this does not support slash commands, Agent Teams, or interactive sessions.
**Why:** This is the elephant in the room that P1-IMP-01 (execution model split-brain) touched but did not fully expose. The REAL question is: how do you programmatically run `/vrs-audit` and capture the output? Options: (a) `claude --print "run /vrs-audit on contract X"` -- may work for single-agent skills but cannot spawn Agent Teams, (b) interactive session with hooks -- captures real behavior but cannot be automated in pytest, (c) scripted scenario via `claude -p` with a carefully crafted prompt -- approximates the workflow but is fragile. CONTEXT.md locks "ALL evaluation runs through Claude Code subagents" but the evaluation runner is Python/pytest. Until this is resolved, all 51 workflows exist only as scenario YAMLs, not as executable tests.
**How:** Add a "Workflow Execution Model" section to CONTEXT.md that explicitly documents: (1) Single-agent skills: executed via `claude --print -p "You are testing skill X. Run it on contract Y."` (headless), (2) Multi-agent flows: executed via interactive session with hooks (requires manual trigger, HITL), (3) Support skills: executed via direct CLI call (no Claude Code needed). Define which workflows use which execution mode. Make the exit gate realistic: not "all 51 tested" but "all 51 have contracts, Core workflows tested headless, orchestrator flows tested interactively."
**Impacts:** 3.1c-09/10/11 (fundamental execution model). Exit gate criteria. Phase duration estimate.
**Research needed:** yes -- Test whether `claude --print -p "Run /vrs-audit on tests/contracts/ReentrancyClassic.sol"` actually works. 15-minute spike.
**Confidence:** HIGH
**Status:** implemented
**Research summary:** GAP-07 RESOLVED. Slash commands do NOT work in -p mode (interactive only). However, skills load via natural language + --append-system-prompt-file for deterministic injection. Subagents (Task tool) work in -p mode. Agent Teams do NOT work in -p mode. Three-tier strategy: Tier 1 (~35 single-agent via claude -p), Tier 2 (~12 subagent-orchestrated via -p + --agents), Tier 3 (~4 Agent Team via decomposition or Agent SDK).

### P2-IMP-19: Building on P1-IMP-21 -- The 5-Plan Collapse Should Be Even More Radical
**What:** P1-IMP-21 proposed collapsing 12 plans to 5. But even 5 plans may be too many given the fundamental blocker: zero real transcripts.
**Why:** The single most valuable thing 3.1c can do right now is: (1) run one real workflow, (2) capture its output, (3) evaluate it, (4) prove the loop works. Everything else is speculative design. I propose 3 plans:

Plan A: **Prove the Pipeline** (~1 week). Run 3 real workflows (1 skill, 1 agent, 1 team), capture transcripts, fix parser on real data, prove hooks fire, prove GVS scores meaningfully, prove single-Opus evaluator produces useful scores. Exit: 3 real evaluation results with `run_mode=headless`, scores that distinguish good from bad.

Plan B: **Scale and Formalize** (~1 week). Author 10 Core contracts from real evaluation experience (not speculative). Run all Core workflows. Establish baseline. Fix whatever broke. Exit: 10 workflows with baselines, regression detection works.

Plan C: **Cover and Improve** (~1 week). Extend to Important/Standard tiers via templates. Run improvement loop once. Document what works and what needs v2. Exit: all tiers have contracts, one documented improvement cycle completed.

Total: 3 weeks, 3 plans, outcome-driven. Each plan's exit gate is "something works that didn't before," not "artifacts were produced."
**How:** Replace the 12-plan structure in CONTEXT.md with 3 outcome-driven plans. Each plan's exit is a demonstrated capability, not a document or code artifact.
**Impacts:** Complete restructuring of CONTEXT.md plan summaries, execution waves, and exit gate.
**Research needed:** no
**Confidence:** MEDIUM
**Status:** rejected

### P2-IMP-20: The "Evaluation Intelligence Layer" Section Violates Its Own Rule
**What:** CONTEXT.md says: "Do not design 3.1c-01 through 3.1c-11 to depend on intelligence-layer features" (line 112). Then 3.1c-12 Part 5 says: "Intelligence module stubs with activation strategy documented." And 3.1c-01 scope says: "Intelligence layer type stubs (~20 for v2): CapabilityClaim, CoverageCell, WorkflowFingerprint, ReasoningMove, CascadeResult, etc."
**Why:** Creating type stubs in 3.1c-01 means 3.1c-01 DESIGNS intelligence-layer features even though no plan is supposed to DEPEND on them. Designing interfaces without implementing them is worse than not designing them at all -- the interfaces become commitments that constrain the real implementation when it happens. Building on P1-IMP-22, the stubs should be removed entirely. Not deferred to 3.1c-12 Part 5. Deleted.
**Impacts:** 3.1c-01 scope reduced by ~20 type definitions. 3.1c-12 Part 5 removed.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented
