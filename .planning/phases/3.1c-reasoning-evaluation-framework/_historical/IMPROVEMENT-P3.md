# Improvement Pass 3

**Pass:** 3
**Date:** 2026-02-19
**Prior passes read:** P1, P2
**Status:** complete

## Approach

Passes 1 and 2 caught surface contradictions and code-reality gaps. This pass looks at interaction effects between components and subtle structural problems that only become visible after the prior corrections stabilized the design. I read all the actual source files (models.py, evaluation_runner.py, reasoning_evaluator.py, graph_value_scorer.py, contract_loader.py, observation_parser.py, debrief_protocol.py, regression_baseline.py) to find issues the CONTEXT.md does not surface.

**Adversarial review applied (2026-02-19):** 5 parallel adversarial agents verified each item against actual source code. 1 KEEP, 7 MODIFY, 2 REJECT. 7 NEW gaps discovered — 3 CRITICAL, 4 HIGH. Verdicts and new gaps integrated below.

## Improvements

### P3-IMP-01: EvaluationPlugin Protocol STILL Does Not Match Implementations (P2-IMP-01 Incompletely Fixed)
**What:** P2-IMP-01 was marked "implemented" and DC-3 in CONTEXT.md (line 241-247) was updated to include `context` in the Protocol signature. However, the actual `models.py` file at line 136 still reads `def score(self, collected_output: Any) -> PluginScore:` with NO `context` parameter. The CONTEXT.md says the fix is done. The code says it is not.
**Why:** This is a concrete P2 implementation failure. Anyone planning against CONTEXT.md will assume DC-3 is correct and the Protocol is fixed. When Plan A starts, the first `isinstance(scorer, EvaluationPlugin)` check will fail because `GraphValueScorer.score()` has an extra `context` kwarg not in the Protocol. The CONTEXT.md improvement was textual, not code.
**How:** Add to Plan A exit criteria: "EvaluationPlugin Protocol in models.py matches DC-3 signature (verified by isinstance check in test)." The two-line code fix is noted in Known Code Issues but must be a Plan A deliverable, not a deferred note.
**Impacts:** Plan A scope (add 2-line fix + test). Known Code Issues section should note this is a Plan A deliverable, not just a known issue.
**Research needed:** no
**Confidence:** HIGH
**Status:** rejected

**Adversarial verdict: REJECT.** Python's `isinstance()` for `@runtime_checkable` Protocols does NOT check parameter signatures (PEP 544) — only method name presence. The `GraphValueScorer.score()` signature with optional `context` kwarg is Liskov-substitutable (callers using the Protocol signature `score(output)` still work). The failure scenario described is false. The real issue is a cosmetic docs-to-code mismatch in the Protocol stub — not a runtime failure. A 2-line fix is fine as a Plan A cleanup task, but this is LOW-priority, not HIGH-confidence structural.

### P3-IMP-02: ObservationParser._load() Silently Drops Errors But parse() Counts Them -- Data Loss Between Methods
**What:** P2-IMP-02 flagged that `observation_parser.py:117-118` silently drops JSON decode errors. CONTEXT.md (line 368-369) now documents this. But reading the actual code reveals a deeper problem: `_load()` (lines 100-122) drops malformed lines during loading and never counts them. The `parse_errors` counter in `parse()` (line 139) only counts non-dict records AFTER successful JSON parsing (line 142-143). Records that fail JSON parsing never reach `self._records` and are invisible to `parse()`.
**Why:** The P2 fix description says "add `parse_errors += 1` in except block." But `parse_errors` is a local variable in `parse()`, not accessible from `_load()`. The architectural issue is that error counting happens in the wrong method. `_load()` discards bad records; `parse()` counts errors in the surviving records. The gap between these two operations is where data loss hides. Fix requires either: (a) counting errors in `_load()` via an instance variable `self._load_errors`, or (b) storing raw lines (including failures) so `parse()` can count them. CONTEXT.md says "fix: add parse_errors += 1 in except block" which is the wrong location.
**How:** Update the Known Code Issues entry for ObservationParser to specify the correct fix: "Add `self._load_errors: int = 0` instance variable, increment in `_load()`'s `except json.JSONDecodeError` block. Remove the false comment `# Count errors in parse()`. In `parse()`, set `parse_errors = self._load_errors` as the initial value before counting non-dict records." Update Plan A exit criteria to validate this.
**Impacts:** Plan A (parser fix is more involved than CONTEXT.md suggests). Also: `PipelineHealth.health_pct` currently cannot detect hook crashes that produce malformed JSON — this fix makes health detection meaningful.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

**Adversarial verdict: KEEP (MODIFY).** Factual claim verified. Added: remove false comment in `_load()`, and note that `PipelineHealth.health_pct` is broken for the entire class of hook-crash failures until this is fixed.

### P3-IMP-03: EvaluationRunner Catches FileNotFoundError But Swallows All Other Exceptions
**What:** `evaluation_runner.py:211` catches `FileNotFoundError` (contract not found) and produces a zero-score result. But any OTHER exception during stages 1-5 (e.g., TypeError from malformed contract YAML, KeyError from missing contract fields, AttributeError from CollectedOutput API mismatch) is uncaught and will crash the entire evaluation run. The `FileNotFoundError` handler also discards the exception variable `e` entirely — no logging, no error details in metadata.
**Why:** CONTEXT.md describes the runner (lines 553-556) as the orchestrator that "produces repeatable results." A runner that crashes on unexpected evaluator errors is not repeatable -- it is fragile. Real workflows will surface malformed data, missing fields, and type mismatches. Note: stages 3, 6, and 7 ARE already guarded with `except Exception` — the gap is specifically in stages 1, 2, 4, and 5 within the outer try block.
**How:** Add to **Plan A** scope (not Plan C — the runner is infrastructure Plan A immediately uses): "EvaluationRunner.run() must (1) keep narrow `except FileNotFoundError` but LOG the error with `str(e)` in `result.metadata['runner_error']`, (2) add `except Exception as e` after it for degraded results with exception details, (3) use `logger.exception()` in both handlers. Plan C benefits from this but Plan A cannot debug reliably without it."
**Impacts:** Plan A scope (runner robustness is infrastructure, not a downstream feature).
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

**Adversarial verdict: MODIFY.** Plan assignment changed from Plan C to Plan A. Exception handling refined: keep narrow FileNotFoundError + add broad Exception handler + LOG both (current code discards `e`). Stages 3/6/7 already guarded — gap is narrower than originally stated.

### P3-IMP-04: Contract Loader Has No Template Fallback -- Unlisted Workflows Get FileNotFoundError
**What:** CONTEXT.md (line 141-142) says "Per-workflow contracts for non-Core workflows created ON DEMAND when category-level evaluation proves insufficient." And "Contract loader: Auto-discovers contracts by directory scan" (line 142). But `contract_loader.py:69-103` `load_contract()` does a simple file lookup -- if no `{workflow_id}.yaml` file exists, it raises `FileNotFoundError`. There is NO fallback to category templates. The `generate_from_template()` function exists (line 165-195) but is never called by `load_contract()`.
**Why:** The template fallback is needed when non-Core workflows are first evaluated. Plan C only tests Core workflows (which all have contracts), so the fallback is needed in **Plan E** when Standard/Important tiers are tested. Additionally, 3 Core tool skills (`vrs-tool-aderyn`, `vrs-tool-mythril`, `vrs-tool-coordinator`) have neither a mapping entry in `_WORKFLOW_TO_CONTRACT` nor a contract file — this IS a Core gap affecting Plan B/C.
**How:** Two fixes: (1) **Plan B scope:** Add missing contract mappings or files for 3 Core tool skills. (2) **Plan E scope:** Contract loader template fallback — the evaluator already accepts a pre-loaded `contract` dict, so the fallback can live in the scenario runner that decides which contract to load (pass `generate_from_template()` result directly), not in `load_contract()` itself.
**Impacts:** Plan B (3 missing Core tool contracts), Plan E (template fallback for non-Core).
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

**Adversarial verdict: MODIFY.** Plan assignment split: missing Core tool contracts → Plan B; template fallback → Plan E (not Plan B, since Plan C only tests Core). Also found: 3 Core tool skills missing from contract mapping.

### P3-IMP-05: The "Soft Capability Gating" Design Creates an Untestable Intermediate State
**What:** CONTEXT.md (line 381-382) says: "Implement soft gating: add `is_gating: bool` field to capability check schema. If a gating capability scores below threshold, add prominent `failure_narrative` but do not zero the overall score (preserve gradient information)." Plan C exit criteria (line 466) includes "Soft capability gating implemented (`is_gating` flag)."
**Why:** "Soft gating" is a contradiction. A gate either blocks or it does not. If a workflow crashes but gets a nonzero score, the baseline records it. The next working run (score 65) looks like a +50 improvement instead of "it started working." `BaselineManager.update_baseline()` only gates on `result.is_reliable` (pipeline health >= 60%), not on capability gate status. Additionally, `update_baseline()` has a hole: if `is_reliable=False` but NO baseline exists, it falls through and seeds the baseline with the crash score anyway.
**How:** Replace "soft gating" with tag-and-segregate: "Add `capability_gating_failed: bool` field to `ScoreCard`. `BaselineManager.update_baseline()` stores this flag alongside the score. `check_regression()` skips comparison when the new run has `capability_gating_failed=True` (emits 'SKIP: capability gate failure — not comparable'). This isolates crashed runs from successful runs without discarding any data. The `overall_score` is still computed (preserving gradient); regression detection refuses to compare across capability gate boundaries. Also fix: `update_baseline()` must NOT seed a baseline from an unreliable first run."
**Impacts:** Plan C (capability gating logic), Plan D (BaselineManager filtering + first-run hole).
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

**Implementation note (2026-02-19):** Implemented as part of Prestep P-1. `ScoreCard.capability_gating_failed` field added. `BaselineManager.update_baseline()` rejects capability-gate failures from baselines. `check_regression()` returns SKIP for capability-gate failures. Unreliable first runs no longer seed baselines (all three guard conditions active).

**Adversarial verdict: MODIFY.** Original "binary filter" proposed blocking `passed=False` from baselines, which prevents baseline accumulation during early dev. Better fix: tag-and-segregate with `capability_gating_failed` flag. Also found: `update_baseline()` seeds baselines from unreliable first runs (hole in the guard).

### P3-IMP-06: Debrief Layer 2 (Hook Gate) Returns Success With Empty Answers -- False Positive
**What:** CONTEXT.md (line 171) describes Layer 2 as "Hook gates via exit code 2 (SAFETY NET)." The actual `attempt_hook_gate_layer()` at `debrief_protocol.py:124-161` calls `_extract_debrief_from_observations()` which returns `answers: []` always (hardcoded empty list, line 354). Layer returns `success=True` with confidence 0.6, blocking Layer 3 (transcript analysis).
**Why:** Two-level problem: (1) **Immediate:** Layer 2 "succeeds" with empty answers, pads to `"[No answer]"` x5, blocks Layer 3 which might extract real content via `_infer_from_transcript()`. The debrief scorer gives 30 (confidence 0.6 * 0.5 + 0 answer quality * 0.5) instead of letting Layer 3 potentially score higher. (2) **Structural:** Layer 2 is not a hook gate at all — it's passive observation scraping. CONTEXT.md describes "hooks return exit 2 to block until debrief marker file exists," but the code scrapes `task_completed`/`agent_stop` events, which is a different mechanism entirely. The debrief confidence formula (`base_score = confidence * 100`) also inflates scores: Layer 2 with ZERO answers outscores Layer 3 with full keyword-matched answers.
**How:** Two-part fix: (1) **Plan A (immediate):** `attempt_hook_gate_layer()` must return `success=False` when `answers` list is empty. One-line fix prevents cascade blocking. (2) **Plan B (structural):** Document in Known Code Issues that Layer 2 is NOT a blocking hook gate — it is a passive observer. Real hook gate behavior requires `debrief_gate.py` implementation (currently a stub). Until then, the cascade should be: Layer 1 (SendMessage) → Layer 3 (transcript analysis) → skip. Layer 2 is a placeholder.
**Impacts:** Plan A (cascade fix), Plan B (debrief architecture documentation).
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

**Adversarial verdict: MODIFY.** Root cause is deeper than originally stated — Layer 2 is not a hook gate, it's passive scraping. Split into immediate fix (Plan A: return false on empty) + structural fix (Plan B: document Layer 2 as placeholder, adjust cascade). Also found: confidence formula inflates Layer 2 scores above Layer 3.

### P3-IMP-07: Plan B Exit Criteria Allow Heuristic Scoring to Pass Gate
**What:** CONTEXT.md Plan B (lines 444-454) says it delivers "single-Opus evaluator with 3 reasoning dimensions." The estimated scope is ~1,500-2,000 LOC. But the exit criteria say "Evaluator produces per-dimension 0-100 scores for 3 dimensions" — which the current heuristic code ALREADY does (incorrectly, but numerically).
**Why:** The `REASONING_PROMPT_TEMPLATE` at `reasoning_evaluator.py:40-55` is a 15-line placeholder. The actual LLM evaluation path requires: prompt building with transcript context, `claude -p --json-schema` subprocess integration, response parsing, failure handling. But the exit criteria don't require an actual LLM call — the heuristic path can silently "pass" Plan B's exit gate by producing 0-100 numbers.
**How:** Add to Plan B exit criteria: "At least one reasoning dimension (`graph_query_quality`) is scored via an actual `claude -p --json-schema` call using the anchored rubric prompt — heuristic keyword matching is explicitly disqualified for this exit criterion." This is the blocking structural fix. LOC estimate update is secondary.
**Impacts:** Plan B exit criteria (prevents heuristic from passing the gate).
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

**Adversarial verdict: MODIFY.** Reframed from "LOC estimate is wrong" (cosmetic) to "exit criteria allow heuristic to pass" (structural). The LOC estimate correction is secondary to closing the gate loophole.

### P3-IMP-08: The 10% Spot-Check Dual Evaluation Has No Implementation Path
**What:** CONTEXT.md (line 153) says "10% spot-check dual evaluation on Core tier: randomly select 10% of Core runs for dual-evaluator scoring. Flag >15pt divergence for manual review." This is part of the Evaluator Design locked decision.
**Why:** With ~10 Core workflows and ~3 runs per workflow for baseline (Plan D), that is ~30 runs. 10% = 3 dual-evaluator runs. The sample size is too small for statistical conclusions (need 20-30 minimum for Cohen's kappa). More importantly, `claude -p` has no temperature parameter. You cannot control or guarantee variance — you get either identical scores (measuring nothing) or uncontrolled sampling noise (measuring nothing useful). CONTEXT.md lines 153-154 already contradict: line 153 commits to spot-check, line 154 commits to anchor transcripts. Anchor transcripts are the right validity mechanism.
**How:** Remove the 10% spot-check from v1 locked decisions. Replace with: "Evaluator validity is assessed via anchor transcripts (10-20 human-scored transcripts as ground truth). Dual-evaluator comparison is v2 scope, requires prompt perturbation mechanism not available in v1." This is already partially stated (line 154) but contradicts line 153.
**Impacts:** Evaluator Design section cleanup. Removes an unimplementable commitment.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

**Adversarial verdict: KEEP.** Unimplementable as described. Factual correction: `claude -p` with constrained decoding may produce variance due to default temperature=1.0, but you can't control it — so variance is noise, not signal. Strengthens the rejection.

### P3-IMP-09: Plan A Must Capture >= 3 Transcripts (Not >= 1) to Satisfy P0.5
**What:** Plan A exit criteria (line 439): "TranscriptParser processes >= 1 real Claude Code transcript." Prestep P0.5 (line 407-413): "Before Plan B planning, score 3 core dimensions on 3 real transcripts."
**Why:** Plan A commits to >= 1 transcript but P0.5 (which blocks Plan B) needs 3. Either Plan A must produce >= 3 or there must be a separate capture step between Plan A and P0.5. The 10-20 anchor transcripts mentioned in Evaluator Design (line 154) are a long-term program target, NOT a Plan B entry gate — Plan B exit criteria requires "differential > 20 points on anchor transcripts" which needs >= 2 (one good, one bad), not 10-20.
**How:** Update Plan A exit criteria from ">= 1" to ">= 3 real transcripts (1 skill, 1 agent, 1 orchestrator flow)." Update P0.5 to explicitly say "Use the 3 transcripts captured in Plan A."
**Impacts:** Plan A scope (must capture 3, not 1 transcript). P0.5 dependency clarified.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

**Adversarial verdict: MODIFY.** Conflict is narrower than originally claimed — only Plan A vs P0.5, not a three-way conflict. The 10-20 anchor figure is a program target, not a Plan B entry requirement. Fix scoped correctly.

**Implementation note (2026-02-19):** Plan A exit criteria in CONTEXT.md updated from ">= 1" to ">= 3 real transcripts (1 skill, 1 agent, 1 orchestrator)." P0.5 checkpoint updated to reference these 3 transcripts.

### P3-IMP-10: Exit Gate Item 3 Says "All 30 Skills Tested" But Plan C Only Tests >= 5 Core Skills
**What:** Exit gate (line 639): "All 30 skills tested -- Investigation/Synthesis with reasoning evaluation, Mechanical with capability checks only." Plan C exit criteria (line 463): ">= 5 Core skills tested with `run_mode=headless`." Plan E (line 486): "All shipped workflows have an evaluation contract (direct or template-generated)" and "Important tier workflows have at least deterministic capability checks passing."
**Why:** There is a gap between Plan C (>= 5 Core) and the exit gate (all 30). Plan E fills this partially (template contracts + capability checks for Important tier). But the exit gate says "All 30 skills tested" while Plan E says "Important tier workflows have at least deterministic capability checks passing." Standard tier (~26 workflows) only gets contracts, not tests. "Tested" is ambiguous -- does having a contract count as "tested"? Or must each skill actually be executed and evaluated?
**How:** Clarify exit gate item 3: "All 30 skills have evaluation contracts. Core skills (~10) tested with full evaluation. Important skills (~15) tested with at least capability checks. Standard skills (~5 spot-checked) have template contracts validated." This matches what Plans C+E can actually deliver. Remove "all 30 tested" language that implies full execution.
**Impacts:** Exit gate (more realistic). Prevents false exit gate failure.
**Research needed:** no
**Confidence:** HIGH
**Status:** rejected

**Adversarial verdict: REJECT.** Exit gate language already disambiguates: "Investigation/Synthesis with reasoning evaluation, Mechanical with capability checks only." CONTEXT.md lines 139-141 + Testing Tiers table define "tested" per tier. Standard tier "tested" = capability checks passing, which is deterministic (no LLM cost). The exit gate is achievable as written.

---

## NEW GAPS (Discovered by Adversarial Gap Hunter)

These are structural issues all 3 prior improvement passes missed. They address the core question: "Is this phase theoretical or practical? Do the tests provide real value?"

### P3-IMP-11: 32 Scenario Tests Validate YAML Documents, Not Agent Behavior [NEW-GAP-01]
**What:** `tests/scenarios/test_use_cases.py` contains 4 test methods: `test_scenario_structure` (validates YAML field presence), `test_scenario_simulated_evaluation` (checks `must_happen` list length >= 3), `test_scenario_id_matches_filename` (prefix matching), `test_scenario_evaluation_model_construction` (constructs `EvaluationInput(run_mode=RunMode.SIMULATED)` then asserts `== RunMode.SIMULATED`). None of these run a workflow. None evaluate agent behavior.
**Why:** CONTEXT.md (line 13) says "Each plan's exit gate is a demonstrated capability, not an artifact count." These 32 scenarios, if counted as "tested," add nothing to capability evidence. They create false test coverage — 32 parametrized tests, all green, all testing YAML structure. An agent's ability to reason about cross-chain bridges is not measured.
**How:** Add to CONTEXT.md: "The 32 scenario YAMLs are test *specifications*, not tests. They have zero value until headless execution (Plan C). The `test_use_cases.py` suite validates specification quality only. It does NOT appear in any exit gate as evidence of agent capability. Plan C exit gates must distinguish 'scenario executed headless' from 'scenario structure valid'."
**Impacts:** Clarifies what the 32 scenarios actually prove. Prevents false confidence from green test suite.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P3-IMP-12: Heuristic Scorer Rewards Verbosity and Activity Quantity — Inverts Quality Signal [NEW-GAP-02]
**What:** `reasoning_evaluator.py:359-443` — the heuristic dimension scorer uses: `reasoning_depth = 30 + unique_tools * 20` (4 different tools = 100), `evidence = 40 + len(bskg_queries) * 15` (5 queries = 100), `coherence = 60` if `len(tool_seq) > 2` else 30, `hypothesis_formation = 20 + len(bskg_queries) * 20`, `completeness = 20 + len(tool_seq) * 10`. The `else` branch (line 434) for unknown dimensions returns hardcoded `score = 30`.
**Why:** An agent that makes 5 unfocused graph queries and outputs verbose garbage outscores an agent that makes 1 targeted query and finds the vulnerability. For the Core attacker contract, 4 of 5 dimensions (`evidence_quality`, `reasoning_depth`, `hypothesis_formation`, `exploit_path_construction`) fall through to heuristics because `_find_plugin_score()` only maps `graph_utilization`/`graph_value`/`bskg_usage`. The remaining 4 either match a named heuristic (activity-based) or the unknown `else` branch (hardcoded 30). **This is the PRIMARY scorer right now.** The evaluator actively harms prompt improvement by rewarding wrong behaviors.
**How:** Add to CONTEXT.md Known Code Issues: "The heuristic dimension scorer is the DEFAULT path for all contract dimensions not mapped to plugins. For Core contracts, 80% of dimensions use activity-quantity heuristics or hardcoded 30. This inverts quality signal — high-activity low-quality runs outscore targeted precise runs. CRITICAL: No baseline may be established from heuristic-scored Core workflows. Plan B (LLM evaluator) MUST complete before Plan D (baseline establishment) for Core tier. Plan A/B execution must explicitly quarantine heuristic scores."
**Impacts:** Plan A (must quarantine heuristic scores), Plan B (LLM evaluator is not optional — it's the fix for inverted signal), Plan D (baselines must wait for LLM evaluator on Core tier).
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P3-IMP-13: GVS citation_rate Is Keyword Regex — Ignores Observation Data [NEW-GAP-03]
**What:** `graph_value_scorer.py:84-96` — `citation_rate` falls back to regex `r"node:|edge:|graph:|BSKG|build-kg"` on `response_text`. The `obs_summary` is passed via `context["obs_summary"]` but `GraphValueScorer.score()` never reads it (line 76-121 ignores context). In headless mode, `CollectedOutput.transcript` is `None`, so the regex fallback is the only path. Citation rate is 35% of GVS weight.
**Why:** An agent can score full citation_rate credit by mentioning "build-kg" in its preamble without citing any graph results. 35% of GVS for all agent/skill workflows is computed from keyword presence in free text. CONTEXT.md (line 379) notes the graph-first compliance problem but not the citation_rate problem — same root cause (ignoring `obs_summary`), different symptom.
**How:** Add to CONTEXT.md Known Code Issues: "`GraphValueScorer.score()` receives `obs_summary` in context but ignores it. The `citation_rate` fallback (keyword regex on response_text) measures 'mentioned graph keywords' not 'cited graph results.' Fix in Plan A: use `context['obs_summary'].bskg_query_count` and observation-level data for citation scoring. Until fixed, citation_rate (35% of GVS) is keyword matching."
**Impacts:** Plan A (GVS fix scope — must also address citation_rate, not just graph-first compliance).
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P3-IMP-14: No Multi-Agent Ground Truth Format — Cannot Test Orchestration Quality [NEW-GAP-04]
**What:** The corpus (18 projects) has `ground-truth.yaml` files defining single-agent findings with `expected_reasoning_chain` (3-5 steps per finding). No fields for defender counter-arguments, verifier arbitration basis, or disagreement-to-resolution paths. Plan C exit criteria (line 465): "At least 1 orchestrator flow tested with multi-agent lifecycle observation." Prestep P1 (line 416) acknowledges "0 multi-agent ground truth templates."
**Why:** An orchestrator where the attacker submits a finding, the defender immediately agrees, and the verifier rubber-stamps passes identically to one where genuine adversarial debate occurred. The test cannot distinguish valuable orchestration from trivial pass-through. "Lifecycle observation" (did all three agents execute?) is testable. "Debate quality" (was the disagreement genuine, was resolution evidence-based?) is not, because no ground truth format exists for it.
**How:** CONTEXT.md must distinguish two claims: "(1) Lifecycle observation: did attacker, defender, verifier all execute and produce outputs? This is testable with current corpus. (2) Debate quality: was the adversarial process genuine? This requires a multi-agent ground truth format capturing valid debate patterns (defender counter-arguments, verifier arbitration criteria). Format design is Plan C scope; 10-15 templates are Prestep P1. Plan C exit criterion should say 'lifecycle observation' explicitly, NOT 'orchestration quality evaluation.'"
**Impacts:** Plan C (exit criterion language), Prestep P1 (must define multi-agent ground truth FORMAT, not just add entries).
**Research needed:** yes — What does a multi-agent ground truth entry look like? What fields are needed to judge debate quality vs rubber-stamping? 1-hour design exercise.
**Confidence:** MEDIUM
**Status:** implemented
**Research summary:** GAP-08 RESOLVED. Use additive `debate_expectations` section alongside existing `findings` schema. Four outcome types (confirmed/refuted/disputed/escalated). Defender position taxonomy (concede/partial/full/challenge) is the core rubber-stamping detector. Anti-rubber-stamp checks are explicit strings mapping to evaluation contract capability checks. Quality signals: evidence citation rate 90%+, cross-reference rate 70%+, convergence budget 3 rounds max. Based on D3 framework, ColMAD, and Safety Evaluation MAJ research.

**Implementation note (2026-02-19):** Prestep P-2 completed. `debate_expectations` schema implemented in 2 corpus projects: defi-lending-protocol-01 (3 entries) and flash-loan-vault-04 (2 entries). 5 total debate ground truth entries with attacker/defender/verifier expectations, quality signals, and anti-rubber-stamp checks.

### P3-IMP-15: Headless Skill Injection Loses YAML Front-Matter Semantics [NEW-GAP-05]
**What:** CONTEXT.md (line 107): "Tier 1: `claude -p --append-system-prompt-file skill.md`." But skill files have YAML front-matter (`allowed-tools`, `context: fork`, `disable-model-invocation: true`) that is parsed by Claude Code's skill system — NOT by the model. When injected via `--append-system-prompt-file`, the front-matter is raw text. Tool permissions are not enforced. Execution context is not forked.
**Why:** Headless evaluation runs the skill's prose instructions with different tool permissions, different execution context, and different invocation semantics than production. An agent that passes headless evaluation may fail in production (or vice versa) because the environment differs in undefined ways. GAP-07 resolved "use --append-system-prompt-file for skill injection" but did not address whether front-matter is semantically processed.
**How:** Add to CONTEXT.md Known Code Issues: "Headless skill injection via `--append-system-prompt-file` does not process skill YAML front-matter. `allowed-tools`, `context: fork`, and `disable-model-invocation` are lost. Headless tests validate reasoning instructions but NOT execution environment constraints. Plan C must acknowledge this: headless evaluation measures reasoning quality under relaxed constraints. A separate production-mode HITL test (already in HITL scenarios) validates full skill semantics." Mark GAP-07 resolution as **partial** in the gaps table.
**Impacts:** Plan C (known limitation documentation), GAP-07 (resolution status).
**Research needed:** yes — Verify whether `--append-system-prompt-file` processes YAML front-matter or treats it as raw text. 15-minute test with a skill that has `allowed-tools` restrictions.
**Confidence:** HIGH
**Status:** implemented
**Research summary:** GAP-09 RESOLVED. Front-matter is NOT processed by `--append-system-prompt-file` — injected as raw text. Skill tool is a separate mechanism. Fix: strip frontmatter before injection, mirror `allowed-tools` via `--allowedTools` CLI flag, mirror `model` via `--model` flag. Skills requiring `context: fork` belong in Tier 2, not Tier 1. Evaluation harness needs `parse_frontmatter()` preprocessing step.

### P3-IMP-16: Improvement Loop Has No Variant Execution Mechanism [NEW-GAP-06]
**What:** Plan D (lines 469-478) describes "one complete improvement cycle: low-scoring dimension identified → prompt variant created → re-evaluated → decision recorded in experiment ledger." But no code wires: (1) workspace creation with modified agent file, (2) headless re-execution against same scenario, (3) score comparison against baseline, (4) experiment recording. The `WorkspaceManager` handles jujutsu isolation but has no agent-file-injection interface.
**Why:** Plan D is the payoff for the entire framework. If the improvement loop cannot execute, Plans A-C produce evidence (scores, baselines, narratives) that goes nowhere. The ~600-900 LOC estimate for Plan D does not account for the variant execution orchestration (~200-400 LOC).
**How:** Add to Plan D scope: "Variant Execution Mechanism — how a prompt variant is tested: (1) Create jujutsu workspace copy, (2) Apply variant to agent/skill file in workspace, (3) Run ClaudeCodeRunner against same scenario with workspace-scoped file, (4) Compare score against baseline for same scenario, (5) Record in experiment ledger. This mechanism requires ~200-400 LOC and must be scoped explicitly. Without it, the improvement loop is a process document, not a working system." Update Plan D scope estimate to ~800-1,300 LOC.
**Impacts:** Plan D scope (significant expansion). The improvement loop transitions from "process" to "implementation."
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P3-IMP-17: Core Contract Dimensions Default to Hardcoded score=30 With No Signal [NEW-GAP-07]
**What:** `reasoning_evaluator.py:434-436` — the `else` branch for unknown dimensions: `evidence.append("Unknown dimension (no heuristic)")`, `score = 30`. The `_find_plugin_score()` name map (lines 317-330) only covers `graph_utilization`, `graph_value`, `bskg_usage`. For the Core attacker contract (`agent-vrs-attacker.yaml`), 4 of 5 dimensions (`evidence_quality`, `reasoning_depth`, `hypothesis_formation`, `exploit_path_construction`) have no plugin match and no named heuristic match → all return 30.
**Why:** The evaluator produces a nonsense aggregate for the most important contracts: GVS score for `graph_utilization` + four hardcoded 30s. An agent that does nothing useful but generates BSKG queries will have its GVS score dominate the weighted average, while the dimensions that measure actual security reasoning quality are invisible. **This is not just a "known limitation" — it means the current evaluator cannot distinguish a good attacker from a bad one on 80% of the evaluation criteria.**
**How:** Add to CONTEXT.md Known Code Issues: "Core contract dimensions not covered by plugins or named heuristics default to score=30 with zero signal. For the attacker contract: 4/5 dimensions return 30. The evaluator cannot distinguish good from bad attackers on reasoning quality. CRITICAL sequencing constraint: Plan B (LLM evaluator) MUST complete before Plan D (baseline) for Core workflows. Baselines established from heuristic-scored Core workflows are meaningless and must be discarded when LLM evaluation is deployed."
**Impacts:** Plan B (LLM evaluator is the fix — not optional), Plan D (Core baselines blocked until Plan B completes), Plan A (must NOT establish Core baselines with heuristic scores).
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

**Implementation note (2026-02-19):** Prestep P-1 quarantine guard implemented. `BaselineManager.update_baseline()` now rejects heuristic-scored Core workflow results from baselines. `CORE_WORKFLOW_PREFIXES` defines which workflows are Core tier. `ScoreCard.has_heuristic_scores` property detects heuristic contamination.

---

## Mini-Plan: Sequencing These Improvements

### What Must Come BEFORE Planning (New Presteps)

**Prestep P-1 (NEW — Blocks Plan A): Quarantine Heuristic Scores** ✅ DONE (2026-02-19)
The heuristic evaluator inverts quality signal (P3-IMP-12) and Core dimensions default to 30 (P3-IMP-17). Any baseline established with these scores is poison. Before Plan A executes:
- ✅ Added `scoring_method: Literal["heuristic", "llm"]` tag to `DimensionScore` in models.py
- ✅ Added `capability_gating_failed: bool` to `ScoreCard` + `has_heuristic_scores` property
- ✅ Added `BaselineManager` guards: rejects heuristic-scored Core, capability-gate failures, unreliable first runs
- ✅ Added `TIER_THRESHOLDS`, `CORE_WORKFLOW_PREFIXES` to regression_baseline.py
- ✅ 298 tests pass, 0 regressions. 4 inline verification scenarios tested.
- **Effort:** ~80 LOC model change + ~50 LOC baseline guard. Completed in 1 session.
- **Why prestep:** Without this, Plan A's pipeline validation accidentally seeds baselines that Plan D inherits, creating the contamination problem P3-IMP-05 identifies.

**Prestep P-2 (NEW — Blocks Plan B): Multi-Agent Ground Truth Format Design** ✅ DONE (2026-02-19)
No ground truth format exists for multi-agent debate quality (P3-IMP-14). Before Plan B contracts are authored:
- ✅ Designed `debate_expectations` schema: additive alongside existing `findings`
- ✅ 4 outcome types (confirmed/refuted/disputed/escalated), defender position taxonomy (concede/partial_mitigation/full_mitigation/challenge_preconditions)
- ✅ Anti-rubber-stamp checks as explicit strings, quality signals (evidence citation rate, cross-reference rate, convergence budget)
- ✅ 3 entries in defi-lending-protocol-01 (balance-update-after-transfer easy, oracle-stale-price medium, auth-002 easy)
- ✅ 2 entries in flash-loan-vault-04 (balance-update-after-transfer medium, vault-share-inflation medium)
- ✅ Total: 5 debate ground truth entries across 2 corpus projects
- **Effort:** ~3 hours design + implementation. Completed in 1 session.
- **Why prestep:** Plan B contracts for orchestrator flows need to reference multi-agent ground truth. Without the format, orchestrator contracts are single-agent contracts with extra steps.

### What Can Be Fixed During Plan Execution

| Item | Plan | Why This Plan |
|------|------|---------------|
| P3-IMP-02 (parser error counting) | Plan A | Infrastructure — parser is Plan A's first deliverable |
| P3-IMP-03 (runner exception handling) | Plan A | Infrastructure — runner must be robust before any real evaluation |
| P3-IMP-06 immediate (debrief cascade) | Plan A | One-line fix, prevents false positives from day one |
| P3-IMP-13 (GVS citation_rate) | Plan A | GVS fixes already scoped in Plan A; add citation_rate |
| P3-IMP-11 (scenario test clarity) | Plan A | Documentation — clarify what scenarios prove |
| P3-IMP-04 missing Core contracts | Plan B | 3 tool skills need contract entries |
| P3-IMP-06 structural (debrief Layer 2) | Plan B | Layer 2 architecture requires debrief protocol work |
| P3-IMP-07 (exit criteria loophole) | Plan B | Exit criteria must require actual LLM call |
| P3-IMP-08 (remove spot-check) | Plan B | Evaluator Design cleanup |
| P3-IMP-09 (transcript quantities) | Plan A | Plan A exit criteria update (>= 3 transcripts) |
| P3-IMP-05 (capability gating) | Plan C | Gating logic implemented during pipeline integration |
| P3-IMP-15 (headless front-matter) | Plan C | Known limitation documented during headless testing |
| P3-IMP-04 template fallback | Plan E | Non-Core workflows first tested in Plan E |
| P3-IMP-16 (variant execution) | Plan D | Improvement loop mechanism is Plan D's core scope |

### Research Needed (2 items)

| Item | Question | Effort | Blocks |
|------|----------|--------|--------|
| P3-IMP-14 | What does a multi-agent ground truth entry look like? | 1 hour | Prestep P-2, Plan C orchestrator contracts |
| P3-IMP-15 | Does `--append-system-prompt-file` process YAML front-matter? | 15 min | Plan C known limitation documentation |

---

## Updated Convergence Assessment

**Original P3 items:** 10 (2 rejected, 8 active after adversarial review)
**New gaps added:** 7 (3 CRITICAL, 4 HIGH)
**Total active improvements:** 15

**Structural improvements:** 12 (P3-IMP-02, 03, 04, 05, 06, 07, 08, 12, 13, 14, 16, 17)
**Cosmetic/documentation:** 3 (P3-IMP-09, 11, 15)
**Rejected:** 2 (P3-IMP-01, P3-IMP-10)

**Ratio:** 20% cosmetic — document is NOT converged. The 7 new gaps represent fundamental practical-vs-theoretical issues that prior passes missed because they focused on document consistency rather than code-reality alignment and test value.

> **Key insight:** The framework's biggest problem is not design contradictions (those are mostly fixed after P1+P2). It is that the current evaluation code produces anti-signal — heuristic scoring rewards wrong behaviors, citation rate measures keywords not citations, and 80% of Core contract dimensions return hardcoded 30. Until Plan B's LLM evaluator is live, the entire evaluation pipeline is worse than random for Core workflows. The 2 new presteps (quarantine heuristic scores, design multi-agent ground truth) must complete before planning proceeds.
