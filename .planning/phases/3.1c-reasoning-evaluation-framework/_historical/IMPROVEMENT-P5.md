# Improvement Pass 5

**Pass:** 5
**Date:** 2026-02-19
**Prior passes read:** 1, 2, 3, 4 (via IMPROVEMENT-DIGEST.md)
**Areas:** Foundation & Contracts, Observation Pipeline, Evaluation Core, Test Suite & Improvement Loop
**Agents spawned:** 4 improvement + (pending) adversarial
**Status:** complete

<!-- File-level status: in-progress | complete -->

## Improvements

### P5-IMP-01: Contract Schema Missing `evaluation_config` in `required`
**What:** The JSON schema at `.vrs/testing/schemas/evaluation_contract.schema.json` does not include `evaluation_config` in the `required` array. All 10 hand-authored Core contracts omit it. The runner must dispatch GVS/reasoning/debrief per contract, but without `evaluation_config`, it must guess dispatch from `category` alone, re-implementing the smart selection matrix in code.
**Why:** Creates two sources of truth: contract YAML (for checks/dimensions) and hardcoded runner logic (for pipeline dispatch). When a contract needs non-default dispatch (e.g., investigation agent without debrief), there is no way to express it.
**How:** (1) Add `evaluation_config` to `required` in schema, (2) Add to all 10 existing contracts, (3) Document as single source for pipeline dispatch.
**Impacts:** Plan 06 — contracts need `evaluation_config`. Plan 08 — runner simplification.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented

**Original framing:** "Add `evaluation_config` to `required` in schema so the runner can read dispatch from contracts instead of guessing from category."

**Adversarial note (Contract & Schema Integrity):** The framing treats a missing `required` field as a schema defect, but the actual defect is upstream: CONTEXT.md already locks the smart selection matrix into evaluation contracts (Implementation Decisions, "Evaluation Architecture" section). That decision is already made. The real problem this improvement exposes is that the 10 existing hand-authored contracts do not conform to the architecture decision that already governs them — they use `metadata.evaluation_depth` (a prose annotation) instead of a structured `evaluation_config` block. Confirmed by reading `agent-vrs-attacker.yaml` and `skill-vrs-audit.yaml`: both have `metadata.evaluation_depth: deep` but no `evaluation_config` dict at all.

Making `evaluation_config` required in the schema is the right fix, but the How needs a sharper scope: the schema field definition already exists (lines 62-84 of the schema file) — the only thing missing is its inclusion in the top-level `required` array and the four sub-fields need their own `required` list within `evaluation_config`. Without requiring the sub-fields (`run_gvs`, `run_reasoning`, `debrief`, `depth`), an empty `evaluation_config: {}` passes validation and the runner still cannot read dispatch. The reframed How: (1) add `evaluation_config` to top-level `required`, (2) add `required: [run_gvs, run_reasoning, debrief, depth]` inside the `evaluation_config` definition, (3) retrofit all 10 existing contracts (mechanical, ~10 min), (4) retire the `metadata.evaluation_depth` field which now duplicates `evaluation_config.depth`. This is not premature optimization — the runner cannot be written without knowing which pipeline branches to take per contract, and that decision point arrives in Wave 5 (3.1c-08). Fixing the schema now costs 30 minutes; discovering the gap at Wave 5 costs a full round of contract rework.

---

### P5-IMP-02: 3.1c-01 Type List Includes 4 Intelligence-Layer Types That v1 Must Not Depend On
**What:** Plan 3.1c-01 lists `TemporalAnalysis`, `CoherenceScore`, `DifficultyProfile`, `ContrastivePair` as core v1 types. But CONTEXT.md line 168-169 says "Do not design 3.1c-01 through 3.1c-11 to depend on intelligence-layer features." These 4 types are intelligence-layer consumers.
**Why:** Internal contradiction. Either they are stubs (belong in 3.1c-12 intelligence/) or core types (constraint is wrong). Moving them to v2 stubs reduces v1 scope from ~35 to ~22 types.
**How:** (1) Split Plan 01 type list into v1 pipeline types vs v2 stubs, (2) Move 4 types to intelligence stubs, (3) Update pre-addressed estimate to ~70%.
**Impacts:** Plan 01 scope reduction. Cleaner v1/v2 boundary.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Evaluation Scope & Calibration):** The improvement correctly identifies the v1/v2 contradiction but conflates four types that have different statuses. `CoherenceScore`, `DifficultyProfile`, and `ContrastivePair` are genuine intelligence-layer types — they require accumulated run data or contrastive samples to compute and have no v1 pipeline producer. These three should move to v2 stubs. `TemporalAnalysis`, however, is NOT an intelligence-layer type: RESEARCH.md line 702 explicitly recommends adding it to 3.1c-01 as a Pydantic model for timestamp-based reasoning trajectory, populated by the ObservationParser from hook timestamps. It has a concrete v1 producer (ObservationParser, which already records timestamps) and a concrete v1 consumer (exit gate 15 — even if that gate is disputed by IMP-17). Treating `TemporalAnalysis` identically to the other three discards a legitimate v1 model. Additionally, the actual `models.py` file already exists and contains NONE of these four types — the CONTEXT.md plan summary is stale relative to the code. The code is already correct; the docs are wrong. The correct rewritten How: (1) Confirm `TemporalAnalysis` as a v1 Pydantic type with ObservationParser as producer; add it to `models.py`, (2) Move `CoherenceScore`, `DifficultyProfile`, `ContrastivePair` to v2 intelligence stubs in `evaluation/intelligence/`, (3) Update CONTEXT.md 3.1c-01 plan summary to match `models.py` reality — the code is already correct, the docs are wrong, (4) Pre-addressed estimate update is correct but the reason is "docs are stale relative to existing code," not "scope reduction" — the scope reduction is 3 types, not 4.

### P5-IMP-03: Contract `reasoning_dimensions` Are Free-Text With No Registry
**What:** Evaluation contracts define `reasoning_dimensions` as free-text strings validated only by `minLength: 1`. CONTEXT.md defines 7 reasoning move types (HYPOTHESIS_FORMATION etc.) but contracts use different names (evidence_quality, reasoning_depth). No canonical vocabulary.
**Why:** The evaluator must map contract dimensions to prompts. Without a registry, every contract author invents names, and the evaluator either ignores contracts (decorative) or fuzzy-matches (unreliable). A contract specifying `exploit_path_construction` has no evaluator template.
**How:** (1) Define canonical dimension registry (~12-15 names covering 7 moves + domain dimensions), (2) Add `enum` constraint to schema, (3) Document that new dimensions need registry entry + prompt template.
**Impacts:** Plan 06 (contracts must use registered dimensions), Plan 07 (evaluator gets 1:1 prompt map).
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Contract & Schema Integrity):** The diagnosis is correct but the proposed remedy over-constrains the schema at the wrong time. The 10 existing contracts already use 13 distinct dimension names across five naming conventions (`graph_utilization`, `hypothesis_formation`, `exploit_path_construction`, `tool_selection`, `coordination_quality`, etc.). Locking an `enum` now means Plan 06 cannot author the remaining 41 contracts without first completing the registry — that is a hard sequencing dependency that is not noted. More critically: the schema `enum` approach creates a coupling where the schema and the evaluator prompt library must be updated in lockstep. If they drift, valid contracts fail schema validation before the evaluator even loads. The stronger design is to use `enum` only for the well-known move types (the 7 HYPOTHESIS_FORMATION etc. are stable), and to allow free-text for workflow-specific domain dimensions while requiring each domain dimension to have a corresponding entry in a registry YAML (e.g., `contracts/dimension_registry.yaml`). This decouples schema stability from registry growth.

Rewritten How: (1) Define the 7 canonical move-type names as an `enum` in schema (these are locked by CONTEXT.md, not subject to per-contract invention), (2) Create `contracts/dimension_registry.yaml` with ~6-8 additional domain dimensions already in use (`graph_utilization`, `evidence_quality`, `tool_selection`, `coordination_quality`, `evidence_flow`, `finding_quality`, `completeness`, `error_handling`), (3) Add a schema `pattern` or CI validation script that rejects dimensions not in the union of the `enum` and the registry file, (4) Plan 07 maps registry entries to prompt templates 1:1. This approach allows growth without schema churn, and the registry doubles as the prompt template index Plan 07 needs.

---

### P5-IMP-04: EvaluationPlugin Protocol Lacks `context` Kwarg
**What:** DC-3 Protocol defines only `score(output) -> PluginScore`. CONTEXT.md line 397 says "Plugins receive optional `context` kwarg" but the Protocol doesn't have it. The debrief plugin is already hardwired around this.
**Why:** When intelligence modules arrive (fingerprinter, adversarial auditor), they need session context not in `CollectedOutput`. Without protocol support, they either access global state (bad) or get hardwired (defeats plugin pattern).
**How:** Add `context: dict[str, Any] | None = None` as optional parameter to `score()` in Protocol. Backward-compatible.
**Impacts:** Plan 07 — uniform context passing. Plan 12 — intelligence modules get standard access.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3
**Prerequisite:** no
**Status:** implemented

**Original framing:** "DC-3 Protocol defines only `score(output) -> PluginScore`. CONTEXT.md line 397 says 'Plugins receive optional `context` kwarg' but the Protocol doesn't have it. The debrief plugin is already hardwired around this."

**Adversarial note (Evaluation Scope & Calibration):** The improvement diagnoses the wrong problem. The Protocol gap is not a future-proofing issue for v2 intelligence modules — it is a present-day API violation that breaks the plugin system now. `reasoning_evaluator.py` line 201 already calls `plugin.score(collected_output, context=context)` with the `context` kwarg. The EvaluationPlugin Protocol in `models.py` declares `score(self, collected_output: Any) -> PluginScore` without `context`. Any plugin that strictly implements the Protocol signature will receive a TypeError when `_run_plugins()` passes `context=context`. This is currently masked only by Python's duck typing. The Protocol IS `@runtime_checkable` (line 124 of `models.py`), and pyright is enabled in this project, meaning the mismatch is a live type-checking error at the call site. The improvement frames this as "when intelligence modules arrive." This is wrong — the evaluator already passes `context` for debrief and obs_summary data used today. The correct framing: "The EvaluationPlugin Protocol signature in `models.py` is inconsistent with the actual call site in `ReasoningEvaluator._run_plugins()` (line 201), creating a present-day API contract violation. Fix the Protocol to match the call site — not as preparation for v2, but because the contract is already broken." Confidence should be HIGH, not MEDIUM. GraphValueScorer must be immediately verified for `**kwargs` or explicit `context` acceptance to confirm no current TypeError in production-path code. See also P5-ADV-03.

### P5-IMP-05: 41 Template-Generated Contracts Need Per-Workflow Differentiation Guidance
**What:** CONTEXT.md says "~10 Core hand-authored; Important/Standard template-generated." `generate_from_template()` does shallow merge. No guidance on what overrides per workflow. 41 contracts will be nearly identical to templates.
**Why:** Exit gate 2 says "each tailored." A reviewer finding 5 byte-for-byte identical contracts (except `workflow_id`) fails the gate. A `vrs-bead-create` and `vrs-bead-list` contract should differ.
**How:** (1) Add differentiation requirement: each contract needs at least 1 workflow-specific capability check, (2) Add categorization guide for ~41 workflows, OR (3) Allow shared contracts for truly identical workflows (reduce file count).
**Impacts:** Plan 06 scope may increase (per-workflow authoring) or decrease (shared contracts).
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Status:** implemented

**Original framing:** "41 template-generated contracts need per-workflow differentiation guidance so they are not identical except for workflow_id."

**Adversarial note (Contract & Schema Integrity):** This improvement is solving the wrong problem at the wrong level. The problem is not that contracts might look identical — it is that we have zero tested workflows, zero real transcripts, and therefore no empirical basis for knowing what "tailored" means for a `vrs-bead-list` workflow versus `vrs-bead-create`. Exit gate 2 says "each tailored" but that gate was written before anyone ran a single real evaluation. Authoring 41 differentiated contracts by hand before running any real workflow is specification fiction: we will invent differences that may not correspond to actual behavioral differences observed in real runs.

The right framing is a sequenced authoring policy, not a differentiation rule. Recommended: (1) For Core tier (~10 workflows): hand-author contracts now, they represent genuine behavioral understanding, (2) For Important tier (~15): author stub contracts with template defaults + one required workflow-specific check placeholder marked `TODO: validate against real run`, (3) For Standard tier (~26): defer authoring until after at least 1 real run of each workflow — templates are placeholders, not final contracts. Exit gate 2 should be tiered: "Core contracts fully tailored; Important contracts have at least 1 validated workflow-specific check; Standard contracts have correct `workflow_id` and schema-valid structure." This is both more honest and more achievable. The `generate_from_template()` shallow-merge problem noted is real and should be fixed to support deep merge of nested dicts (e.g., `evaluation_config` sub-fields), but that is a Plan 06 implementation detail, not a planning crisis.

---

### P5-IMP-06: `_WORKFLOW_TO_CONTRACT` Hardcoded Dict Is a Maintenance Trap
**What:** `contract_loader.py` has a 10-entry static dict that must grow to 51. Silent identity-function fallback masks missing entries.
**Why:** When Plan 06 adds 41 contracts, someone must add 41 dict entries. If one is missed, `resolve_contract_id` falls through silently, producing FileNotFoundError with no helpful message.
**How:** (1) Convention-based resolver with prefix tries (`skill-`, `agent-`, `orchestrator-`), OR (2) `workflow_aliases` field in contract YAML, OR (3) Startup validation of mapping completeness.
**Impacts:** Plan 06 (41 new entries needed), Plan 08 (runner robustness).
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Contract & Schema Integrity):** The diagnosis is accurate but the proposed solutions have different costs and the improvement does not rank them. The lens question is: is this necessary complexity for v1, or are we over-engineering a 51-entry dict?

The fallback in `resolve_contract_id` (line 54: `return _WORKFLOW_TO_CONTRACT.get(workflow_id, workflow_id)`) is not strictly silent — if the fallback produces a bad filename, `load_contract` raises `FileNotFoundError` with the resolved name and original ID in the message (lines 91-95). The error IS traceable. The maintenance burden argument is real, but convention-based resolution introduces its own risk: what happens when a workflow named `vrs-tool-slither` should map to `skill-vrs-tool-slither` but the convention produces `skill-vrs-vrs-tool-slither` for a `vrs-` prefixed skill?

The right answer for v1 is option (3): startup validation, not convention magic. Specifically: add a `validate_mapping_completeness(contracts_dir)` function that walks `contracts_dir/*.yaml`, reads `workflow_id` from each, and warns for any contract whose `workflow_id` has no entry in `_WORKFLOW_TO_CONTRACT`. This is ~15 LOC, zero convention risk, and catches gaps at startup rather than at test time. Option (1) can be added later if the dict maintenance truly becomes painful. Rewritten How: (1) Add `validate_mapping_completeness()` — reads all contract files, cross-checks against dict, warns on gaps, (2) Call it from `list_contracts()` or from a dedicated `check_health()` function called by Plan 08 runner startup, (3) Note: convention-based resolution is a valid v2 improvement once the 51-entry set is stable and naming conventions are proven consistent.

---

### P5-IMP-07: ObservationWriter `threading.Lock` Is No-Op for Hook Concurrency
**What:** `observation_writer.py` uses `threading.Lock()` for "thread-safe writes." But Claude Code hooks run as separate processes. `threading.Lock` only protects within a single process. GAP-06 resolved this with "use fcntl.flock()" but the code never implemented it. Additionally, CONTEXT.md Known Code Issues gap 11 names `log_session.py` as the location of the thread-safety problem, but the actual threading.Lock is in `observation_writer.py` lines 22 and 77.
**Why:** When `obs_tool_use.py` and `obs_bskg_query.py` fire in rapid succession (separate processes, same file), the threading lock provides zero inter-process protection. False sense of safety. GAP-06 explicitly resolved this gap with `fcntl.flock()` but that resolution was never carried into the implementation.
**How:** Two actions: (1) Correct CONTEXT.md Known Code Issues gap 11 to name `observation_writer.py` as the location (not `log_session.py`). (2) Add to 3.1c-02 scope: replace `threading.Lock()` with `fcntl.flock()` wrapping the `open(output_path, "a")` call per GAP-06 resolution. Note: `fcntl` is POSIX-only; add a platform guard (`if sys.platform != "win32"`) or use the `portalocker` library if cross-platform support is needed. The fix is ~10 LOC. This is a Plan 02 implementation task, not a new design gap.
**Impacts:** Plan 02 scope — fcntl.flock implementation (~10 LOC).
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Observation Pipeline Correctness):** The lens brief asks whether this belongs in an improvement pass (CONTEXT.md design) vs. a bug tracker. It belongs here for two reasons: (1) it corrects a factual error in CONTEXT.md Known Code Issues (wrong file named in gap 11), and (2) it assigns the fix to Plan 02 scope, which is a planning decision that will not happen automatically. The bug is confirmed by reading `observation_writer.py` line 22 (`_write_lock = threading.Lock()`) and line 77 (`with _write_lock:`). The ENHANCE sharpens the original How by identifying the file-name error in Known Code Issues, providing the specific code location, and adding the platform caveat that the original omitted. Without the platform caveat, a Plan 02 developer on a team that tests on Windows will ship code that crashes on import.

### P5-IMP-08: Tool Use/Result Pairing Will Break on Parallel Tool Calls
**What:** `observation_parser.py` pairs tool results by matching "most recent tool_use without a result" (line 161) — assumes strict alternation. Real Claude Code sessions batch parallel tool calls. The proposed fix (correlate via `tool_use_id` from hook input) depends on an assumption that the project's own hook verification research does not support.
**Why:** The pairing bug at line 161 is real. However, the hook-verification-findings.md (RS-04, 2026-02-11) documents verified `PreToolUse` input schema fields as: session_id, transcript_path, cwd, permission_mode, hook_event_name, tool_name, tool_input. No `tool_use_id` field appears. If `tool_use_id` is not present in hook payloads, the proposed fix cannot be implemented as described and an alternative pairing strategy must be evaluated before Plan 03 scope is set.
**How:** Keep `research_needed: yes`. Before finalizing Plan 03 scope: verify whether Claude Code injects `tool_use_id` into PreToolUse/PostToolUse hook stdin in real sessions. The specific evidence gap: hook-verification-findings.md RS-04 (the project's own verified hook schema documentation) shows no such field. If the field is absent, evaluate alternatives: (a) timestamp proximity pairing, (b) command-content fingerprinting, or (c) accepting imperfect pairing for v1 with a documented limitation. If the field is present, add to 3.1c-02 scope (hooks capture it) and 3.1c-03 scope (parser pairs by ID not position).
**Impacts:** Plan 02 (hooks capture tool_use_id, if field exists), Plan 03 (parser pairing logic depends on research outcome).
**Research needed:** no — RESOLVED by GAP-10. `tool_use_id` IS present in official Claude Code hook payloads (PreToolUse, PostToolUse, PostToolUseFailure). RS-04 missed it by relying on secondary sources. See gaps/done/GAP-10-tool-use-id-hook-payload.md.
**Research summary:** `tool_use_id` confirmed available in hook stdin JSON per official Anthropic docs (code.claude.com/docs/en/hooks). Format: `toolu_01ABC123...`. Use for direct pairing in Plans 02 and 03.
**Confidence:** HIGH (pairing bug exists), HIGH (fix is viable — field confirmed present)
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Observation Pipeline Correctness):** The pairing bug is confirmed at `observation_parser.py` line 161: the comment "Try to pair with most recent tool_use" and the `tool_events[-1]` access make the LIFO assumption explicit. The improvement correctly identifies the bug and already has `research_needed: yes`. The ENHANCE strengthens the How by citing the specific conflicting evidence: the project's own RS-04 research shows PreToolUse schemas without `tool_use_id`. A Plan 03 developer who proceeds assuming this field is available will build broken pairing logic and discover the failure mid-implementation. By naming the evidence source (hook-verification-findings.md, RS-04), the improvement prevents that failure mode without needing to resolve the research question here.

### P5-IMP-09: GraphValueScorer Citation Rate Is Keyword Soup, Not Just "Uncalibrated"
**What:** `graph_value_scorer.py` has two citation rate paths. The PRIMARY path (lines 85-87) uses `transcript.graph_citation_rate()` when a TranscriptParser is available — this is structural and potentially calibratable. The FALLBACK path (lines 88-96) activates when `transcript` is None and counts regex matches for `node:|edge:|graph:|BSKG|build-kg` — this is keyword soup and cannot be calibrated. Plan 3.1c-04 in CONTEXT.md uses the word "calibrate" without distinguishing these two paths, implying a single calibration exercise covers both.
**Why:** Pass 3 flagged the citation regex; P-1 quarantined heuristic scores. These addressed the downstream effect. The upstream cause — Plan 04's undifferentiated "calibrate" scope — was not corrected. A Plan 04 developer will encounter both paths under one instruction and may spend calibration effort on the structurally broken fallback. The fallback is broken because `graph:` matches any English use of the word "graph", `node:` matches Node.js path output, and the regex fires regardless of whether the matched text follows from a BSKG query result. Near-zero signal regardless of transcript quantity.
**How:** Update Plan 04 scope in CONTEXT.md to distinguish two tasks: (1) PRIMARY PATH calibration: wire TranscriptParser into CollectedOutput for all non-simulated evaluation modes so `graph_citation_rate()` is always called; calibrate this path with 30+ real transcripts. (2) FALLBACK replacement: replace the regex at lines 88-96 with observation-based structural matching — cross-reference BSKG query result node IDs (captured by hooks in Plan 02) against node references in conclusion text. Do not attempt to calibrate the regex. Note the cross-plan dependency: the fallback replacement requires Plan 02 hooks to capture BSKG query result node IDs, which the current Plan 02 scope does not specify.
**Impacts:** Plan 04 scope splits into primary-path calibration plus fallback replacement. Plan 02 scope may need addition of result node ID capture to enable Plan 04 fallback replacement.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Observation Pipeline Correctness):** The lens brief asks whether IMP-09 is a re-proposal of something already addressed. It is not: P-1 quarantined outputs (addressed the downstream effect) and Pass 3 flagged the regex (named the problem). Neither corrected the Plan 04 scope language, which still says "calibrate" uniformly. The ENHANCE makes the primary/fallback distinction explicit and adds a cross-plan dependency note that neither the original improvement nor any prior pass captured: the fallback replacement requires node ID capture in Plan 02 hooks. Without that note, Plan 04 will attempt structural matching on data that does not exist in the observation stream.

### P5-IMP-10: Smart Selection Matrix Has No Encoding Specification
**What:** CONTEXT.md Architecture defines a matrix table for per-category hook/check selection. Nowhere does it specify how this is encoded at runtime (contracts? hooks? runner?).
**Why:** Plans 02, 06, and 08 will make conflicting assumptions about where selection lives. The encoding choice has significant implementation implications.
**How:** Add to Implementation Decisions: "Smart Selection Matrix encoded in evaluation contracts. Each contract includes `hooks` field listing which hooks to install. Runner reads contract's hook list and passes to `install_hooks()`. Selection happens at installation time." Update Plan 02 to remove smart selection from scope (belongs to Plan 06/08).
**Impacts:** Plan 02 (scope reduction), Plan 06 (must include hooks field), Plan 08 (reads and applies).
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Contract & Schema Integrity):** The core diagnosis is valid — the matrix table exists in CONTEXT.md but has no runtime encoding spec, creating ambiguity across three plans. However, the proposed How contains a hidden dependency problem that must be resolved before encoding in contracts.

The Implementation Decisions section of CONTEXT.md already partially resolves this: "Smart selection matrix: each evaluation contract specifies which hooks/checks apply per workflow category." This is already a locked decision. The gap is not that the decision is missing — it is that no one added a `hooks` field to the schema or to any of the 10 existing contracts.

The "hooks at installation time" model in the proposed How has a sequencing conflict: hooks are installed BEFORE the session starts (CONTEXT.md: "Hooks snapshot at startup — must install BEFORE starting session"). The runner reads the contract AFTER the session ends (it processes observation artifacts). So the runner cannot install hooks based on contract contents — that must happen in a pre-session setup step, not in the runner. This invalidates the proposed How's "Runner reads contract's hook list and passes to `install_hooks()`" framing.

Rewritten How: (1) The pre-session setup step (not the runner) reads the contract's `hooks` field and installs the appropriate hooks before the session starts, (2) Add `hooks` as a structured field to the schema with an enum of known hook names, (3) The runner uses the same `hooks` field to know which observation types to expect in the JSONL file (passive validation, not installation), (4) Plan 02 scope: implement hook installation in the pre-session setup helper, not in the runner. This distinction matters: the runner is post-session, the hook installer is pre-session.

---

### P5-IMP-11: "70% Pre-addressed" for Plan 3.1c-02 Is Misleading
**What:** CONTEXT.md says "3.1c-02: ~70% pre-addressed." The 8 hook scripts are ~200 LOC of stdin-parse-and-write. The hard work — real Claude Code input validation, concurrency fix, debrief blocking, smart selection — is entirely absent from existing code.
**Why:** "~70% pre-addressed" in the scope adjustment table implies the substantial work is done. The actual state: 8 hooks exist with correct structure (stdin parsing, JSONL write) but have never been validated against real Claude Code sessions, ObservationWriter uses a no-op threading.Lock for process-level concurrency (IMP-07), both debrief hooks exit 0 unconditionally (stubs), and smart selection is unimplemented. These four unfinished items represent the majority of Plan 02 value. A team reading "70% pre-addressed" will under-staff this plan.
**How:** Update the 3.1c-02 row in the CONTEXT.md scope adjustment table to: "~30% pre-addressed. 8 hooks exist with correct stdin/stdout structure but unvalidated on real sessions. ObservationWriter uses threading.Lock (no-op for inter-process concurrency). Both debrief hooks are exit-0 stubs. Smart selection matrix unenforced." This is a planning document correction that affects effort allocation for Plan 02.
**Impacts:** Plan 02 effort estimates — team should treat this as a mostly-new implementation, not a validation pass.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** N/A
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Observation Pipeline Correctness):** The lens brief asks whether a planning estimate correction is appropriate for an improvement pass. It is: the scope adjustment table in CONTEXT.md is a living planning artifact, and correcting it prevents systematic under-resourcing of Plan 02. The 70% figure is objectively wrong by inspection of what exists vs. what is needed: the 200 LOC of stdin-parse-write skeleton covers the easy 30%; process-safe locking, blocking debrief, real-session validation, and smart selection (the hard 70%) are absent. The ENHANCE adds the specific corrected text and names the three major defects driving the correction so the rationale is auditable. This is not a design change — it is a correction to a factual claim about the current state of the code.

### P5-IMP-12: Graph-First Compliance Check Assumes Any Bash = BSKG Query
**What:** `graph_value_scorer.py` `_check_graph_first` (lines 170-193) checks whether "first Bash call appears before first Read call" with the comment "assumed BSKG." The first Bash call in any real session could be `ls`, `git status`, `pip install slither`, or any non-BSKG command.
**Why:** Any non-BSKG Bash call before a Read call produces `graph_first_compliant=True` — a false positive. The `_check_graph_first` dimension carries 30% of GVS weight (DEFAULT_WEIGHTS). A 30% weight component producing anti-signal makes GVS scores unreliable for compliance measurement even after the citation fallback is repaired (IMP-09).
**How:** Add to Known Code Issues with code location (`graph_value_scorer.py` lines 170-193). Add to Plan 04 scope: filter `tool_sequence` for `alphaswarm` substrings before determining `first_bash` — an agent gets `graph_first_compliant=True` only if the first `alphaswarm` command precedes the first Read call. Non-alphaswarm Bash calls treated as neutral. The fix is ~5 LOC in `_check_graph_first`.
**Impacts:** Plan 04 (scorer correctness). Any GVS baselines must be recomputed after applying the fix since the compliance signal changes.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Observation Pipeline Correctness):** The bug is confirmed by code inspection at `graph_value_scorer.py` lines 170-193. The docstring states "Returns True if the first Bash call (assumed BSKG) appears before the first Read call" — the assumption is explicit in the source. This is a genuine correctness defect with a clear fix (~5 LOC) and a clear plan assignment (Plan 04). The 30% weight on a broken component is significant signal corruption. P-1 quarantines current scores so no active baselines are corrupted today, but the fix must be applied before Plan 04 calibrates the scorer on real transcripts. The improvement correctly identifies the scope (Known Code Issues + Plan 04) and the fix is narrowly contained. CONFIRM stands.

### P5-IMP-13: Debrief Layer 1 Cannot Work From Python — SendMessage Is a Claude Code Tool

**Original framing:** "Plan 3.1c-05 says 'Layer 1: SendMessage to idle agent' with location `src/.../debrief.py`. But SendMessage exists only inside Claude Code sessions as a tool call. The evaluation runner is Python code — it cannot call SendMessage. This is the PRIMARY debrief layer. If it cannot be called from Python, the pipeline needs a different integration. Debrief collection must happen during the Claude Code session (pre-evaluation), not in the Python runner (post-session)."

**What:** Plan 3.1c-05 has no specification for WHICH component calls SendMessage in live (non-simulated) mode. The Python `debrief_protocol.py` Layer 1 correctly fails in simulated mode with graceful fallback. In live mode, `attempt_send_message_layer` returns "not yet implemented" — silently falling to Layer 3 (transcript analysis). The four-layer cascade architecture is already correct and was validated by GAP-02 research. The actual gap is that no Implementation Decision records whether the Claude Code test orchestrator (Plans 09-11) or the Python runner owns the SendMessage call in live mode, and there is no integration contract specifying how live debrief data reaches the runner.

**Why:** GAP-02 research (resolved 2026-02-18) explicitly documented the "Python cannot call SendMessage" constraint and concluded: "the existing cascade design is correct," recommending "Option C: After the orchestrator receives the agent's final status message, immediately send debrief questions via SendMessage" — meaning the Claude Code orchestrator is the caller, not Python. This is already the correct design. The `simulated=True` fallback in `attempt_send_message_layer` is intentional. The "primary debrief layer is broken" characterization is accurate only for live mode, and the proposed full architectural split (pre-evaluation collection phase vs post-evaluation scoring phase) is more drastic than required — the split already implicitly exists, since the runner receives `CollectedOutput` as input from a prior collection step.

**How:** Add a single Implementation Decision to CONTEXT.md: "Layer 1 (SendMessage) is called by the Claude Code test orchestrator (Plans 09-11) as part of the test teardown sequence, not by the Python runner. After receiving the agent's final status message, the orchestrator sends debrief questions, collects the response, and serializes a `DebriefResponse` to `.vrs/observations/{session_id}_debrief.json`. The runner reads this artifact from disk in live mode; `attempt_send_message_layer` in live mode loads from disk rather than calling SendMessage itself." Update Plan 05 to specify this integration contract as a deliverable. Plans 09-11 gain a debrief-trigger step in their test teardown sequence. Plan 08 runner gains a disk-read path for live-mode debrief (small addition, not a structural rewrite).

**Impacts:** Plan 05 gains integration contract spec (~1 page). Plans 09-11 gain a debrief trigger step in their test teardown sequence. Plan 08 gains disk-read path in `attempt_send_message_layer` for live mode. Architecture diagram in CONTEXT.md gains a "(Collection: during session, by orchestrator)" annotation. No plans require structural rewrite.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Debrief Execution Model):** The original framing treats "Python cannot call SendMessage" as a discovery requiring architectural restructuring. This constraint was already documented in GAP-02 resolution — the research concluded the cascade design is correct and explicitly recommended the Claude Code orchestrator (not Python) as the SendMessage caller. The existing `simulated=True` fallback already handles this correctly for simulated mode. The actual gap is a missing integration contract between Plans 09-11 (which run the Claude Code sessions and should trigger debrief) and Plan 08 (the runner, which should read the serialized result). The proposed "pre-evaluation collection phase" architectural split is the right destination but the wrong framing: it implies a larger structural change than is needed when in fact only a disk-read path must be added to Layer 1's live-mode branch plus an Integration Decision must be recorded. Reframing targets the missing spec rather than a complete architectural reversal that would require rewriting all three debrief-cluster improvements simultaneously.

### P5-IMP-14: 7 Reasoning Move Types Only Fit Investigation Workflows
**What:** CONTEXT.md defines 7 move types with investigation-focused DAG (HYPOTHESIS → QUERY → ...). All 51 workflows get reasoning evaluation. Tool integration (slither, aderyn) doesn't form hypotheses or query graphs. Scoring on HYPOTHESIS_FORMATION produces zeros that cascade-poison the scorecard.
**Why:** Cascade DAG only makes sense for ~10 investigation workflows. For 41 others, the 7 types are wrong decomposition. Need per-category move types or restrict 7-type DAG to investigation only.
**How:** (1) State 7-move DAG applies to Investigation only, (2) Tool Integration: 3 types (TOOL_SELECTION, RESULT_FILTERING, RESULT_PRESENTATION), (3) Orchestration: 4 types (TASK_DECOMPOSITION, AGENT_SELECTION, COORDINATION, SYNTHESIS), (4) Support: skip per-move evaluation.
**Impacts:** Plan 07 scope increases (per-category definitions) but implementation simplifies. Plan 06 contracts specify which move set.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2
**Prerequisite:** no
**Status:** implemented

**Original framing:** "Need per-category move types or restrict 7-type DAG to investigation only. How: (1) 7-move DAG for Investigation, (2) 3 types for Tool Integration, (3) 4 types for Orchestration, (4) Support: skip per-move evaluation."

**Adversarial note (Evaluation Scope & Calibration):** The problem diagnosis is correct — zero-scoring move types cascade-poison scorecards for non-investigation workflows. But the proposed solution adds a new maintenance surface where a simpler instrument already exists. CONTEXT.md 3.1c-07 already specifies "4 prompt templates by category (investigation, tool integration, orchestration, support-lite)." These prompt templates are the correct instrument for per-category differentiation — they already scope which reasoning moves are relevant for each workflow type without requiring a parallel vocabulary of move types. The cascade-poisoning problem is prevented by not asking about HYPOTHESIS_FORMATION in a tool-integration template, not by defining TOOL_SELECTION as a formal alternative move type. Defining TOOL_SELECTION, RESULT_FILTERING, RESULT_PRESENTATION as formal move types creates a maintenance surface of 14 move type definitions across 4 categories, plus 4 separate DAG structures, plus 51 contracts each specifying which move set applies. The existing 4-template approach already handles scope differentiation at the prompt level. The correct framing: "The 4 prompt templates in 3.1c-07 must include explicit scoring directives for applicable move types per category, and an explicit skip directive for non-applicable move types (e.g., investigation template assesses all 7 moves; tool-integration template only assesses RESULT_INTERPRETATION and CONCLUSION_SYNTHESIS, marking others as N/A with no cascade effect). No new move-type vocabulary is needed. Plan 07 scope is unchanged; the cascade-poisoning guard is a two-line addition to the scoring aggregator that skips N/A-scored moves." This narrows the fix to a single plan (07) rather than expanding it across Plans 06 and 07, and eliminates the 51-contract move-set specification burden.

### P5-IMP-15: Debrief Layer 2 Is Infrastructure for Layer 1, Not an Independent Layer

**Original framing:** "Layer 2 'hook gates (exit 2)' blocks agent shutdown but has no mechanism to inject debrief questions. Hooks are passive — they get JSON stdin and produce exit codes. CONTEXT.md presents Layer 2 as MEDIUM_CONFIDENCE debrief. In reality, it only provides a time window for Layer 1 (SendMessage) to operate. Blocking without collecting is useless alone. Simplify cascade to 3 functional layers: Layer 1 (SendMessage + optional blocking), Layer 2 (transcript analysis fallback), Layer 3 (skip)."

**What:** `DebriefStatus.MEDIUM_CONFIDENCE` is assigned to `layer_used == "hook_gate"` results in `debrief_protocol.py:44-48` regardless of whether any answers were actually collected. The `_extract_debrief_from_observations` helper returns `answers: []` for hook_gate results (visible in the code at line 352). An empty-answers result classified as MEDIUM_CONFIDENCE contaminates scoring: the evaluator receives a non-trivial confidence weight for data that is effectively absent. This is a code-level mislabeling, not an architectural defect.

**Why:** CONTEXT.md already describes Layer 2 as "SAFETY NET" — the design intent is exactly what this improvement claims should replace the current framing. The improvement's conclusion that Layer 2 is a "blocking window for Layer 1, not independent collection" matches the design; the implementation disagrees with the design at one specific point: the confidence classification. Collapsing to 3 functional layers discards the hook gate as a named, testable component — but the gate IS architecturally distinct: it is the mechanism that creates the time window. Losing it as a named layer loses the ability to test it independently and to report when it fires vs when it does not.

**How:** Fix the mislabeling in code without altering the architecture. (1) In `classify_debrief()` in `debrief_protocol.py:40-49`: change the `hook_gate` branch to check `len(debrief.answers) > 0 and not all(a == "[No answer]" for a in debrief.answers)` before assigning MEDIUM_CONFIDENCE; when the gate fired but collected no answers, assign LOW_CONFIDENCE instead. (2) Add a clarifying note to CONTEXT.md Layer 2 description: "Hook gate confidence is LOW unless Layer 1 (SendMessage) also fired in the same session and populated answers — the gate blocks but does not independently collect responses." (3) Do NOT collapse to 3 layers; retain the 4-layer named structure. The gate is a real component and will have its own HITL validation scenario (Plan 05 HITL: "Trigger debrief, verify capture").

**Impacts:** `debrief_protocol.py:44-48` — 3-line conditional fix. CONTEXT.md Layer 2 description — one-sentence annotation. No plan scope changes.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Debrief Execution Model):** The original framing aims at the wrong target. CONTEXT.md already calls Layer 2 a "SAFETY NET" — the design intent matches what the improvement claims should be the corrected framing. Prior Pass 2 rejected P2-IMP-16 on debrief layer redundancy for the same reason: the architecture was always correct. The actual bug is the `DebriefStatus.MEDIUM_CONFIDENCE` code assignment in `debrief_protocol.py` applied unconditionally to hook_gate results regardless of whether answers were collected. Collapsing to 3 layers is unnecessary and loses the blocking gate as a named, independently testable component. The fix is a targeted 3-line code correction plus a one-sentence CONTEXT.md annotation — not an architectural simplification.

### P5-IMP-16: Evaluation Runner Has Circular Dependency With Debrief

**Original framing:** "Runner imports `run_debrief` and architecture shows runner orchestrating all components including debrief. But debrief requires Claude Code session (IMP-13). The session is what the runner evaluates *after it completes*. Pipeline must split into: Phase 1 (Collection: hooks + debrief during session) and Phase 2 (Evaluation: runner scores collected artifacts). Runner should only do Phase 2."

**What:** The runner's `run_debrief()` call (evaluation_runner.py:190) in live mode silently falls through to transcript analysis because `attempt_send_message_layer` returns "not yet implemented." This is a missing live-mode implementation path in Layer 1, not a circular dependency. The runner correctly handles all modes by design via `simulated=self._run_mode == RunMode.SIMULATED`. The architecture is already two-phase implicitly: the Claude Code session completes first (producing CollectedOutput and, in the future, a serialized DebriefResponse artifact), then the runner evaluates. There is no logical circularity — the runner does not re-enter a live session.

**Why:** "Circular dependency" is a precise term that does not fit the actual relationship. A circular dependency means A cannot complete without B and B cannot complete without A. Here, the session completes unconditionally first; then the runner evaluates. The runner calling `run_debrief()` that reads from disk is sequential, not circular. The proposed "two-phase pipeline" structural split is already the implicit architecture — the runner receives `CollectedOutput` as input, meaning prior collection already happened. The concrete actionable content of this improvement is entirely covered by the IMP-13 reframing: record an Integration Decision specifying that Plans 09-11 orchestration triggers and serializes debrief during the session, and the runner's live-mode Layer 1 reads from disk.

**How:** No new structural changes beyond what IMP-13 reframing already specifies. Two informational updates to make the implicit design explicit: (1) Add a comment to `evaluation_runner.py:188-196` in the debrief block: "In live mode, `run_debrief()` reads a pre-serialized DebriefResponse from disk written by the test orchestrator (Plans 09-11). SendMessage is called by the orchestrator during session teardown, not here." (2) Add "(Collection: during session, by orchestrator)" as an annotation above the runner box in the CONTEXT.md architecture diagram.

**Impacts:** One code comment. One diagram annotation. All substantive scope changes are captured by IMP-13 reframing.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Debrief Execution Model):** "Circular dependency" is an incorrect characterization of the actual relationship. The session runs to completion first; the runner evaluates the artifacts produced by that completed session. The runner's import of `run_debrief` is not circular — it is a call to a function that reads prior-phase artifacts from disk. The two-phase split the improvement proposes is already implicit in the architecture (the runner receives CollectedOutput as input, not a live session handle). All concrete content of this improvement is captured by the IMP-13 reframing. Accepting all three debrief-cluster improvements in their original form would apply three overlapping architectural changes to the same subsystem, producing inconsistent CONTEXT.md edits. The reframing consolidates the actionable content into one Integration Decision (IMP-13) plus two targeted code fixes (IMP-15 confidence classifier, IMP-16 comment).

### P5-IMP-17: Exit Gate 15 (Temporal Reasoning) Has No Plan Coverage
**What:** Exit gate 15: "Temporal reasoning trajectory distinguishes hypothesis-first from retrofit." No plan summary mentions building this. Not same as counterfactual replay (deferred idea).
**Why:** Exit gate with no plan coverage = guaranteed blocker. With zero real transcripts, cannot calibrate what hypothesis-first vs retrofit looks like.
**How:** Recommend deferral: Move exit gate 15 to Deferred Ideas: "Requires real transcripts showing both patterns to calibrate; defer to v2."
**Impacts:** Exit gate count reduces. Phase scope narrows.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 2
**Prerequisite:** yes — Requires real transcripts showing both reasoning patterns
**Status:** implemented

**Adversarial note (Evaluation Scope & Calibration):** This improvement is correct and the deferral recommendation is sound, but it undersells how thoroughly this ground has already been covered, and it misapplies both the confidence rating and the prerequisite flag. P1-IMP-27 (status: implemented) in `_historical/IMPROVEMENT-P1.md` already proposed exactly this deferral — moving temporal reasoning trajectory from v1 North Star to v2 scope — and was marked implemented. The exit gate persisted because P1-IMP-27's implementation updated PHILOSOPHY.md but did not remove the corresponding exit gate from CONTEXT.md. IMP-17 is therefore completing a previously accepted decision that was only half-implemented. The How should note this provenance: "P1-IMP-27 (implemented, Pass 1) accepted this deferral and updated PHILOSOPHY.md North Star #9. Completing that implementation by removing exit gate 15 from CONTEXT.md and adding it to the Deferred Ideas section." Confidence should be HIGH, not MEDIUM — this is a previously accepted decision with a concrete historical record, not a new judgment call. The prerequisite flag is also misapplied: real transcripts are not needed to remove the gate from CONTEXT.md. Transcripts would be needed to implement the temporal reasoning feature itself. The prerequisite applies to the deferred feature, not to completing the gate removal. Second-order effect: removing gate 15 reduces the exit gate count from 16 to 15. Gate numbering should remain stable for external references — mark as "deferred to v2" inline rather than renumbering the remaining gates.

### P5-IMP-18: 3x Baseline Runs Are Wasteful Without Variance Analysis
**What:** Plan 3.1c-12 Part 1: "Run all tests 3x." 51 workflows x 3 = 12+ hours, ~$100. Three samples too few for statistical significance on LLM non-determinism.
**Why:** N=3 gives confidence intervals of approximately plus or minus 58% for a Bernoulli process — not enough for usable variance data but too expensive for a blanket baseline pass. Either 1x (initial baseline) or 5-10x on Core only (statistical) is defensible. 3x across all 51 is the worst of both: expensive but still statistically unusable.
**How:** In Plan 3.1c-12 Part 1, change "Run all tests 3x" to: "Run all 51 tests 1x for initial baseline. For Core tier (~10 workflows), run 5x for variance estimation. pass@k computed for Core only." Update HITL scenario 12 to "1-run baseline (Core 5-run variance check)." Exit gate 11 already says "baseline established from day 1" — no change there. Plan 12 Part 1 scope reduced approximately 60%.
**Impacts:** Plan 12 Part 1 scope reduced ~60%.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Test Suite Operability):** The original Why is numerically correct but does not explain why 3x is specifically worse than 1x or 5x — it states "too few for statistical significance" without quantifying the actual CI. N=3 on a Bernoulli process gives approximately plus or minus 58% confidence interval (based on Wilson score interval at 95%), making 3x useless for variance analysis while costing 3x the resources of a 1x baseline. The rewritten Why makes this concrete. The rewritten How is anchored to specific plan text. Exit gate 11 is confirmed unaffected. Second-order note: the 5-run Core variance check should specify that the 5 runs must use the same contract version and be run within the same model release window — variance measured across model updates is not LLM non-determinism, it is model drift, which requires different treatment.

---

### P5-IMP-19: 51-Workflow Test Suite Needs Staging Strategy
**What:** Plans 09-11 say "All 51 workflows tested" as single wave. But 41 contracts don't exist yet. No rollout plan from 9 HITL-validated to 51.
**Why:** Without staging, the most likely outcome is batch-generating 41 contracts and tests simultaneously with no inter-tier validation — mirroring the 3.1d batch-fabrication failure pattern documented in CONTEXT.md "What Was Fabricated" section. Result: 51 green tests that test nothing, indistinguishable from the fabricated transcripts failure.
**How:** Add staged rollout as a required sequencing constraint: (1) Core tier ~10 first, HITL validated with gate passage required before next sub-wave; (2) Important tier ~15, template plus review, with spot-check gate; (3) Standard tier ~26, template plus structural check gate. Tier-qualified exit gate language for gates 3, 4, 5. Update Wave 6 in the same commit: "Wave 6: [3.1c-09+10+11] — 3-sub-wave execution: (a) Core tier ~10 with HITL gate, (b) Important tier ~15 with spot-check gate, (c) Standard tier ~26 with structural check gate." Constrain Plan 06 authoring order to Core first.
**Impacts:** Exit gates 3, 4, 5 need tier qualification. Wave 6 description updated to 3-sub-wave execution. Plan 06 authoring order constrained.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Test Suite Operability):** The original Why ("51 green tests that test nothing") is abstract. The rewritten Why connects this to the 3.1d fabricated transcript failure pattern documented in CONTEXT.md — same batch-generation anti-pattern, concrete historical evidence from this project. The original How omits two critical propagation points: Wave 6 must be updated (it is the primary execution reference that developers read first, not the per-plan staging notes), and Plan 06 authoring must be constrained to match the staged order. A staging constraint that lives only in Plans 09-11 text but not in Wave 6 will be overridden under execution pressure. See also P5-ADV-04, which flags the Wave 6 update as a required co-edit.

---

### P5-IMP-20: Intelligence Layer Stubs Lack Activation Mechanism Specification
**What:** 12 modules have "Activates: After X" triggers but no spec for what "activate" means mechanistically. Feature flag? Config? Import guard? Runtime check?
**Why:** 3.1c-12 Part 5 will create 12 empty files with docstrings. Exit gate 16 says "activation strategy documented" but without a concrete mechanism spec, any prose description satisfies the gate without producing a testable activation system.
**How:** Add to Implementation Decisions (Design Constraint, binding on all 12 modules): "Each stub exports `is_active(store: EvaluationStoreProtocol) -> bool`. Central `intelligence/__init__.py` exposes `get_active_modules(store) -> list[str]`. Exit gate 16 verifiable as: (a) all 12 stubs implement `is_active`, (b) unit tests verify at least 3 activation thresholds against mock stores, (c) `get_active_modules()` returns non-empty set on day 1." ~50 LOC total. Exit gate 16 is verifiable, not prose-satisfiable.
**Impacts:** Plan 12 Part 5 gains ~50 LOC. Exit gate 16 becomes objectively verifiable.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Test Suite Operability):** The original correctly proposes `is_active()` but frames it as an implementation choice for Plan 12. The rewritten How elevates it to an Implementation Decision (Design Constraint) so it binds all 12 modules regardless of who authors them and regardless of execution order. Without locking it in CONTEXT.md as a Design Constraint, the activation mechanism is an implementation choice that could be made differently per-module — 12 different activation patterns, no central registry, no testable exit gate. The specific exit gate verifiability criteria (3 threshold unit tests, non-empty on day 1) transform gate 16 from prose-satisfiable to objectively checkable.

---

### P5-IMP-21: Vulnerability Markers in Corpus Contracts Invalidate All Evaluations
**What:** 102 `/// @dev VULNERABILITY:` markers across 32 corpus files invalidate evaluation signal. Known Code Issue says "3.1c-06 should document" but 3.1c-06 is contracts authoring, not corpus curation. The marker stripping is unassigned to any plan and unimplemented.
**Why:** Agents seeing "VULNERABILITY: reentrancy in withdraw()" find it trivially — every test becomes reading comprehension, not reasoning evaluation. The `isolation.blind_prompt` field in scenario YAMLs does NOT mitigate this: agents read Solidity source files directly via Bash and Read tools, bypassing the prompt-level blind entirely. Baseline scores with markers present are meaningless and cannot be corrected retroactively.
**How:** Add Prestep P3 (hard precondition on Plans 09-11): "Strip markers via `scripts/strip_vuln_markers.py` (~30 LOC, idempotent). Store originals in `corpus/ground_truth.yaml`. Version control constraint: run on a clean working tree, commit stripped files separately so originals are recoverable on script failure." The script must fail fast on dirty working tree — partial strip on failure destroys originals. This is not a documentation task for Plan 06; it is a blocking prerequisite for any evaluation run using corpus contracts.
**Impacts:** Plans 09-11 gain hard precondition (Prestep P3). Baseline (Plan 12) becomes meaningful. Known Code Issues entry corrected to assign to Prestep P3, not Plan 06.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** yes — Must strip markers before any evaluation run using corpus contracts.
**Status:** implemented
**Pre-implement commit:** 97f6fd4b

**Adversarial note (Test Suite Operability):** The item is genuinely blocking. The lens challenge was "30 LOC script — is this really blocking?" Yes. The `isolation.blind_prompt` field in scenario YAMLs does NOT cover this case: agents receive the skill prompt with the blind injected, but then read Solidity source files directly via Bash and Read tools during the session — bypassing the prompt-level restriction entirely. This factual gap was absent from the original improvement. The version control constraint (clean tree + separate commit for stripped files) is a mandatory safety requirement: a script failure mid-execution that partially strips files with no separate commit leaves the originals unrecoverable. Confirmed marker count by search: 32 files, 105 matching lines.

---

### P5-IMP-22: Improvement Loop Parallel Variants Are Actually Sequential
**What:** Plan 3.1c-12 Part 2: "3-5 parallel prompt variants." But Agent Teams constraint forces sequential execution. "Parallel" means "branched in Jujutsu, evaluated sequentially."
**Why:** If someone tries 5 simultaneous Claude Code sessions, they hit the Agent Teams constraint. Cost: 5 variants x ~25 min = ~125 min per dimension. Should be explicit.
**How:** Amend Plan 3.1c-12 Part 2: "3-5 variants branched in Jujutsu, evaluated sequentially (Agent Teams constraint). ~25 min per dimension per variant. Prioritize 1-2 Core dimensions per cycle." Note cycle time: a 3-dimension improvement cycle for Core tier is approximately 6 hours.
**Impacts:** Plan 12 Part 2 scope clarified. Wall-clock cost made explicit.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Test Suite Operability):** This is execution guidance, not a structural design improvement. The Agent Teams constraint is already documented in CONTEXT.md Execution Model (lines 204-205). The word "parallel" in Plan 12 Part 2 is a real misread risk, and the fix is correct and minimal. The confirmation adds one second-order note: 5 variants x 25 min/variant = 125 min per dimension for Core tier. A 3-dimension improvement cycle is over 6 hours. The amendment must state cycle time explicitly so developers do not discover the wall-clock cost mid-execution and attempt to parallelize, hitting the constraint.

---

### P5-IMP-23: `run_batch` Has No Timeout or Progress Reporting
**What:** `EvaluationRunner.run_batch()` iterates scenarios sequentially with no per-scenario timeout and no progress logging. A hung workflow blocks all remaining tests.
**Why:** Concrete failure mode: workflow #17 enters an infinite loop or hangs waiting for a resource. No timeout fires. Suite hangs. Developer kills process. Note: per-result persistence already works — `store_result()` is called inside `run()` per-scenario (lines 252-260 of evaluation_runner.py), so completed results survive a process kill. The missing capabilities are timeout enforcement and progress visibility.
**How:** Add to Plan 08 scope: per-scenario timeout (default 600 seconds, documented as "conservative minimum — Core tier Agent Teams runs may need 900-1800 seconds"), progress logging (N/total after each scenario), continue-on-failure (catch per-scenario exceptions, log, proceed). ~30 LOC. Future enhancement: read timeout from `evaluation_config.timeout_seconds` (after IMP-01 is implemented) to allow per-tier configuration.
**Impacts:** Plan 08 (runner code). run_batch becomes production-safe for 51-scenario suite.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Test Suite Operability):** The original incorrectly states that per-result persistence is missing and that a process kill loses 16 prior results. Reading `evaluation_runner.py:252-260` confirms `store_result()` IS called inside `run()` per-scenario — completed results survive a process kill. A developer reading the original would dismiss the item after confirming persistence works. The rewritten What removes the false persistence claim so the real gaps (timeout + progress) remain actionable. The 10-minute default needs a caveat: Core tier Agent Teams runs (attacker/defender/verifier on complex contracts) can exceed 15 minutes. The default should be documented as conservative with per-contract override as the v2 mechanism.

---

### P5-IMP-24: "5 Feedback Channels" for Metaprompting Is a Dangling Reference
**What:** Plan 3.1c-12 Part 3: "convert evaluation failures to prompt modifications via 5 feedback channels." These 5 channels are never enumerated anywhere in CONTEXT.md.
**Why:** Developer will either invent 5 on the spot or implement single generic failure-narrative-to-prompt-diff (which is actually fine for v1).
**How:** Simplify to: "Primary channel: failure narrative pairs from reasoning evaluator. Secondary channels (coverage gaps, regression deltas) activate after first improvement cycle."
**Impacts:** Plan 12 Part 3 scope becomes achievable.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 2
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Test Suite Operability):** The "5 feedback channels" reference appears only once in CONTEXT.md (line 532) and is enumerated nowhere across the entire planning corpus. CONTEXT.md's "Self-Describing Failure Narratives" section already canonically names the primary signal. The simplification (primary channel + secondary channels activate after first cycle) does not lose information because the 5 channels were never defined in the first place. Confidence is MEDIUM in the original because there is a possibility the plan author intended to enumerate 5 channels during execution — but after 4 passes with no enumeration, the omission is structural. CONFIRM stands.

---

## New Items (Adversarial Review — Contract & Schema Integrity)

### P5-ADV-01: `evaluation_config` Sub-Fields Have No `required` Constraint — Empty Object Passes Validation
**What:** Even after adding `evaluation_config` to the top-level `required` array (IMP-01), a contract with `evaluation_config: {}` passes schema validation because the `evaluation_config` object definition (lines 62-84 of the schema) has no `required` sub-array. The runner would read `None` for `run_gvs`, `run_reasoning`, `debrief`, and `depth`, and silently fall back to defaults or crash with `AttributeError`.
**Why:** The fix in IMP-01 is necessary but not sufficient. A schema that requires the presence of a key but not the presence of any values inside it provides no actual contract enforcement. For `evaluation_config` to be the single source of truth for pipeline dispatch (the stated goal of IMP-01), all four sub-fields must be required.
**How:** Inside the `evaluation_config` property definition in the schema, add `"required": ["run_gvs", "run_reasoning", "debrief", "depth"]`. Update all 10 existing contracts to include all four fields. This is the missing half of IMP-01's fix.
**Impacts:** Completes IMP-01. Plan 06 contract templates must include all four sub-fields. Runner can safely read all dispatch flags without None-checks.
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Status:** implemented

**Source:** Adversarial review (Contract & Schema Integrity)
**Adversarial note (Contract & Schema Integrity):** Discovered by reading the actual schema file (lines 62-84): the `evaluation_config` object has `properties` but no `required` array. This is a gap that IMP-01 does not address. An improvement that makes `evaluation_config` required at the top level while leaving the object interior unconstrained creates a false sense of completeness.

---

### P5-ADV-02: Schema Has `additionalProperties: true` — Contracts Can Carry Arbitrary Fields Forever
**What:** The schema's top-level `additionalProperties: true` (line 136) means any field is valid. Contracts already use `metadata.evaluation_depth` to carry data that should be in `evaluation_config.depth`. With open additional properties, there is no enforcement preventing future contracts from accumulating arbitrary fields that create silent parallel dispatch signals.
**Why:** As IMP-01 correctly identifies, `metadata.evaluation_depth` is already a second source of truth for pipeline dispatch depth. If `additionalProperties: true` persists, Plan 06 authors will continue adding ad-hoc fields (e.g., `metadata.use_gvs: true`) that contradict or duplicate `evaluation_config`. The schema cannot enforce consolidation if it accepts anything.
**How:** Change `additionalProperties: true` to `additionalProperties: false` at the top level, and add `additionalProperties: false` to the `metadata` sub-object. Permitted additional fields (if any remain after IMP-01 and IMP-03) must be explicitly added to `properties`. Deprecate `metadata.evaluation_depth` in favor of `evaluation_config.depth` with a validator that rejects contracts containing both.
**Impacts:** All 10 existing contracts need audit for any fields that would now fail. Plan 06 contract templates must be schema-complete before generating 41 contracts. Plan 08 runner can trust schema-validated contracts have only known fields.
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Status:** implemented

**Source:** Adversarial review (Contract & Schema Integrity)
**Adversarial note (Contract & Schema Integrity):** This is not premature optimization. The 10 existing contracts already demonstrate the exact failure mode: `agent-vrs-attacker.yaml` uses `metadata.evaluation_depth: deep` while the schema provides `evaluation_config.depth` for the same purpose. With `additionalProperties: true`, this drift is schema-valid and will compound over 51 contracts.

---

## New Items (Adversarial Review — Evaluation Scope & Calibration)

### P5-ADV-03: EvaluationPlugin Protocol Violation Is a Present-Day TypeError Risk, Not a Missing Feature
**What:** `ReasoningEvaluator._run_plugins()` (`reasoning_evaluator.py` line 201) calls `plugin.score(collected_output, context=context)`. The EvaluationPlugin Protocol in `models.py` declares `score(self, collected_output: Any) -> PluginScore` with no `context` parameter. Any plugin written to strictly conform to the Protocol signature will receive a TypeError at runtime when the evaluator passes `context=context`. IMP-04 frames this as future-proofing for v2 intelligence modules; it is a present-day API contract violation in active production-path code.
**Why:** The GraphValueScorer — the only plugin currently auto-registered by the evaluator — must be immediately verified for `**kwargs` or an explicit `context` parameter. If it does not have either, every evaluation run that calls GraphValueScorer through the plugin system encounters a TypeError. The mismatch is currently masked only by Python's duck typing, but pyright is enabled in this project (per `.claude/settings.json`) and will flag this as a type error at the `plugin.score(collected_output, context=context)` call site. This is not a design gap — it is a broken code path that must be fixed before any real plugin is registered.
**How:** (1) Immediately verify `GraphValueScorer.score()` signature in `graph_value_scorer.py` for `**kwargs` or `context` acceptance, (2) Fix the Protocol in `models.py`: add `context: dict[str, Any] | None = None` to `score()`, (3) Add a unit test: instantiate a strict Protocol-conformant plugin (no `**kwargs`), register it with ReasoningEvaluator, call `evaluate()`, verify no TypeError, (4) Update DC-3 design constraint to document the `context` parameter as part of the Protocol contract.
**Impacts:** IMP-04 (superseded in urgency framing — the fix is the same but this is v1-blocking, not v2-prep). Plan 07 reasoning evaluator must ensure all prompt-based plugins accept `context`. Plan 12 intelligence module stubs must include `context` in their stub signatures from the start.
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Status:** implemented

**Source:** Adversarial review (Evaluation Scope & Calibration)
**Adversarial note (Evaluation Scope & Calibration):** This is a direct code-inspection finding at two locations: `reasoning_evaluator.py:201` (call site passes `context=context`) and `models.py:136` (Protocol declares `score` without `context`). The Protocol IS `@runtime_checkable` (line 124 of `models.py`). Any plugin conforming to the Protocol signature and registered with the evaluator will encounter a TypeError. The fix is the same as IMP-04 proposes, but the framing difference matters for triage: this must be fixed before any real plugin is registered, not deferred to when intelligence modules arrive in v2.

---

## New Items (Adversarial Review — Test Suite Operability)

### P5-ADV-04: Staging in IMP-19 Must Also Update Wave 6 or It Collapses Under Execution Pressure
**What:** IMP-19's staged rollout requirement must be anchored in the Wave 6 description in CONTEXT.md's Execution Waves section. Wave 6 currently reads "[3.1c-09+10+11] Merged Workflow Test Suite" as a single entry. The staging precondition in Plans 09-11 text is subordinate to the wave definition — the wave is read first, and per-plan staging notes are discovered later, if at all.
**Why:** Execution pressure collapses any staging constraint that is not visible at the schedule level. This matches the 3.1d batch fabrication pattern: all deliverables described as one wave, executed as one batch with no inter-tier validation.
**How:** When implementing IMP-19, update Wave 6 in the same commit: "Wave 6: [3.1c-09+10+11] Merged Workflow Test Suite — 3-sub-wave execution: (a) Core tier ~10 with HITL gate, (b) Important tier ~15 with spot-check gate, (c) Standard tier ~26 with structural check gate. Each sub-wave requires gate passage before the next begins." Note: the IMP-19 ENHANCE already includes this Wave 6 update. This ADV item ensures it is treated as a required co-edit, not optional follow-up.
**Impacts:** Wave 6 description in CONTEXT.md Execution Waves section. No additional plan scope changes beyond IMP-19.
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Status:** implemented

**Source:** Adversarial review (Test Suite Operability)
**Adversarial note (Test Suite Operability):** The Wave 6 entry is the primary execution reference that developers and project managers read when assessing schedule. A staging constraint buried in Plans 09-11 body text will be invisible at planning-level reviews. Without the Wave 6 update, IMP-19's staging guarantee evaporates the first time a deadline forces the Core+Important+Standard tiers to be treated as one deliverable. This item ensures the two edits (Plans 09-11 staging language and Wave 6 description) land in the same commit.

---

## Adversarial Review: Contract & Schema Integrity

**Items reviewed:** 5 (P5-IMP-01, P5-IMP-03, P5-IMP-05, P5-IMP-06, P5-IMP-10)
**Verdicts:**
- REFRAME: 2 (IMP-01, IMP-05)
- ENHANCE: 3 (IMP-03, IMP-06, IMP-10)
- CREATE: 2 (P5-ADV-01, P5-ADV-02)

**Cross-group conflicts:**
- IMP-10 (smart selection matrix encoding) and IMP-01 (evaluation_config required) are tightly coupled: IMP-10 proposes adding a `hooks` field to contracts, and IMP-01 proposes adding `evaluation_config`. Together they add two new required top-level fields to all 51 contracts. Neither improvement notes the other. Plan 06 authoring must address both simultaneously or the schema will be revised twice mid-authoring.
- IMP-14 (other group, 7 move types per category) directly constrains IMP-03's dimension registry: if IMP-14 defines per-category move-type sets (Investigation: 7, Tool Integration: 3, Orchestration: 4, Support: 0), then IMP-03's canonical enum must cover all sets — approximately 14 distinct move names total, not the proposed 12-15. The two items need to be authored together.
- IMP-01 and IMP-05 conflict on sequencing: IMP-01 requires retrofitting 10 existing contracts before the schema can be declared stable. IMP-05 (reframed as a tiered authoring policy) depends on knowing which schema fields are required before Plan 06 begins. If IMP-01 is deferred, IMP-05's tiered approach authors contracts against an unstable schema.
- IMP-06 (convention resolver) interacts with IMP-05 (shared contracts): if IMP-05 allows shared contracts for identical workflows (e.g., one contract serving both `vrs-bead-create` and `vrs-bead-list`), then the `_WORKFLOW_TO_CONTRACT` dict entries can point multiple workflow IDs at one contract filename, which is already supported by the current architecture. This is actually the cleanest resolution to IMP-06's maintenance concern for identical workflows — no convention magic needed.

**Second-order risks:**
1. IMP-01 + P5-ADV-01 + P5-ADV-02 together require touching the schema, all 10 existing contracts, and the contract loader validation logic. If implemented piecemeal across different plans, each partial fix will leave the system in a valid-but-inconsistent state. All three should be treated as a single atomic schema hardening task.
2. IMP-03's `enum` constraint on `reasoning_dimensions` will break all 10 existing contracts immediately after implementation (they use non-enumerated names like `exploit_path_construction`, `coordination_quality`). The fix requires authoring the registry and updating contracts in the same commit — if split across plan boundaries, CI will fail between commits.
3. IMP-10's pre-session hook installation model (corrected in the ENHANCE note) creates a dependency where Plan 02 (hooks) must expose a pre-session setup API before Plan 08 (runner) can read contracts to determine which hooks to install. This means the hook installation API design is a Wave 2 decision that constrains Wave 5, but it is not currently noted in the execution wave dependencies.

---

## Adversarial Review: Debrief Execution Model

**Items reviewed:** 3 (P5-IMP-13, P5-IMP-15, P5-IMP-16)
**Verdicts:** REFRAME: 3

**Cross-group conflicts:**
- IMP-13, IMP-15, and IMP-16 form an internally dependent cluster. All three are attempting to fix the same root cause (the missing integration contract for live-mode debrief) from three different angles. Accepting all three in their original form would produce three overlapping CONTEXT.md edits and one Plan 05 scope change, two Plan 08 scope changes, and a layer-count reduction — all addressing the same gap and likely producing contradictions. The reframings consolidate the actionable content: one Integration Decision (from IMP-13), one 3-line code fix (from IMP-15), one comment + diagram annotation (from IMP-16).
- IMP-13 reframing adds a debrief-trigger step to Plans 09-11. This is new scope for those plans. IMP-19 (other group, staged rollout for Plans 09-11) does not account for this added step. Whoever implements the staged rollout must include the debrief trigger in the Core-tier test orchestration.
- IMP-15 reframing fixes `DebriefStatus.MEDIUM_CONFIDENCE` in `debrief_protocol.py`. If IMP-04/P5-ADV-03 (EvaluationPlugin `context` kwarg) is implemented at the same time, both touch the debrief scoring path. Should be coordinated to avoid merge conflicts.
- No conflicts with IMP-07 through IMP-12 or IMP-17 through IMP-24 detected. Those items address orthogonal concerns.

**Second-order risks:**
1. If all three items are applied in their original form rather than the reframings, Plan 05 is told to "build debrief as a Claude Code orchestration protocol" (IMP-13), Layer 2 is collapsed to a blocking window (IMP-15), and the runner is told not to call `run_debrief` at all (IMP-16). These three changes together effectively require rebuilding the debrief subsystem when in fact the existing design is structurally sound and needs only a live-mode integration contract plus a one-file confidence-classification fix.
2. The IMP-13 reframing adds a debrief-trigger step to Plans 09-11. This new step requires the Claude Code orchestrator to send questions, await a response, serialize `DebriefResponse` to disk, and then invoke the runner. This is a new orchestration sequence that needs its own HITL validation (HITL Plan 05: "Trigger debrief, verify capture"). Currently planned HITL scenarios do not explicitly test the serialization handoff. The HITL scenario should be updated to cover this.
3. The IMP-15 reframing (fixing the MEDIUM_CONFIDENCE mislabeling) has a second-order effect on any future baseline comparisons: hook_gate-only results that were previously scored as MEDIUM_CONFIDENCE will now score as LOW_CONFIDENCE. Since zero real transcripts currently exist, this recalibration costs nothing. But the change should be noted in the baseline initialization docs so future reviewers understand the score-level semantics were corrected before baseline was established.
4. Prior Pass 2 rejected P2-IMP-16 on debrief layer redundancy. Both IMP-15 (this pass) and P2-IMP-16 (Pass 2) reach the same conclusion — the architecture is correct, the implementation disagrees at one specific point. The reframing applied here is consistent with the prior rejection and should be cited when presenting this verdict in the merge step, to avoid the same argument recurring in Pass 6.

---

## Adversarial Review: Observation Pipeline Correctness

**Items reviewed:** 5 (P5-IMP-07, P5-IMP-08, P5-IMP-09, P5-IMP-11, P5-IMP-12)
**Verdicts:**
- ENHANCE: 4 (IMP-07, IMP-08, IMP-09, IMP-11)
- CONFIRM: 1 (IMP-12)
- REJECT: 0
- RESEARCH: 0
- REFRAME: 0
- PREREQUISITE: 0
- CREATE: 0

**Cross-group conflicts:**
- IMP-07 (threading.Lock fix, Plan 02 scope) and IMP-09 (citation fallback replacement, Plan 04 scope) are independent changes but share an implicit cross-plan dependency: IMP-09's fallback replacement requires BSKG query result node IDs captured by hooks — which is Plan 02 work. Neither item notes this. Correct sequencing: fix IMP-07 in Plan 02 AND capture node IDs in Plan 02 hooks, then rebuild citation fallback in Plan 04. If node ID capture is omitted from Plan 02 scope, Plan 04's structural matching is blocked.
- IMP-08 (tool_use_id pairing, Plans 02+03) affects Plan 02 hook scope independently from IMP-07. If tool_use_id does not exist in hook payloads (the research question), Plan 02 hook scope is smaller. The research outcome of IMP-08 should be resolved before Plan 02 scope is finalized to avoid implementing both IMP-07 (fcntl.flock) and a tool_use_id capture that turns out to be impossible.
- IMP-11 (70% to 30% estimate for Plan 02) is consistent with IMP-07 (concurrency defect), IMP-08 (pairing fix TBD), and IMP-09 (node ID capture needed). All four items together confirm that Plan 02 is substantially understated in the current estimate. No conflicts among these items.
- IMP-09 and IMP-12 both affect GVS output independently. If both are fixed in Plan 04, GVS compliance scores will change on two dimensions simultaneously. P-1 already quarantines pre-fix scores; the merge step should confirm the quarantine covers both the citation fallback replacement (IMP-09) and the graph-first filter fix (IMP-12).
- IMP-10 (other group, ENHANCE verdict from Contract & Schema Integrity lens) correctly reframes the smart selection hook installation to a pre-session setup step. This affects IMP-07's scope: the pre-session setup step must call the hook installer, and IMP-07's fcntl.flock fix must be in place before that installer writes to the observations file. No conflict, but ordering matters within Plan 02.

**Second-order risks:**
1. IMP-08's research question (does tool_use_id exist in hook payloads?) is the blocking dependency for Plan 03's pairing logic design. If research is deferred and Plan 03 development begins assuming tool_use_id is available, and it is not, Plan 03 ships broken pairing logic. The research must be resolved before Plan 03 design begins. The hook-verification-findings.md (RS-04) is the starting point — it shows no such field, which may be definitive or may simply reflect incomplete schema documentation.
2. IMP-12's fix (alphaswarm-only Bash filtering in `_check_graph_first`) changes GVS behavior on all existing synthetic test data. Current tests that pass because "any Bash before Read = compliant" will fail after the fix if those Bash calls are not alphaswarm commands. This is a legitimate break in test continuity. Plan 04 scope should include "update GVS unit tests to use alphaswarm commands in compliant scenarios" to avoid a spurious test-failure wall after the fix is applied.
3. IMP-09's ENHANCE splits Plan 04 into primary-path calibration and fallback replacement. The fallback replacement depends on Plan 02 capturing BSKG query result node IDs. This creates an implicit PREREQUISITE: Plan 04 fallback replacement REQUIRES Plan 02 node ID capture. The execution wave ordering (02 before 04) handles this IF Plan 02 scope is updated — which it currently is not. The merge step must add node ID capture to Plan 02 scope when merging IMP-09.

---

## Adversarial Review: Evaluation Scope & Calibration

**Items reviewed:** 4 (P5-IMP-02, P5-IMP-04, P5-IMP-14, P5-IMP-17)

**Verdicts:**
- ENHANCE: 1 (IMP-02 — correct direction, but conflates TemporalAnalysis with three genuinely deferred types; models.py is already correct, docs are stale; scope reduction is 3 types not 4)
- REFRAME: 2 (IMP-04 — not a v2 future-proofing gap but a present-day Protocol violation at an active call site; IMP-14 — per-category move type vocabulary adds a 14-type maintenance surface where 4 prompt templates with N/A directives already solve the cascade-poisoning problem)
- CONFIRM: 1 (IMP-17 — correct and sound, with P1-IMP-27 provenance, confidence corrected from MEDIUM to HIGH, prerequisite flag corrected)
- CREATE: 1 (P5-ADV-03 — IMP-04's Protocol gap is a verifiable present-day TypeError risk warranting a separate item that distinguishes urgency from the v2 framing in IMP-04)

**Cross-group conflicts:**
- IMP-02 (type list split) and IMP-20 (intelligence stub activation mechanism): if `TemporalAnalysis` stays in v1 as this review recommends, its producer/consumer contract must be established before Plan 12 creates the intelligence stubs. ObservationParser (Plan 03) must be confirmed as the producer before Plan 01 finalizes the `TemporalAnalysis` model shape. This is a Wave 1/Wave 2 coordination dependency not currently in the execution wave notes.
- IMP-04/P5-ADV-03 (Protocol context kwarg) and IMP-13/IMP-16 (debrief two-phase pipeline): the `context` dict passed to plugins will carry a `DebriefResponse` artifact path rather than triggering debrief collection in the two-phase model. The Protocol fix must accommodate the two-phase model or a third revision will be needed when the debrief integration contract (IMP-13) is implemented.
- IMP-14 (REFRAME: N/A directives in templates) and IMP-03 (dimension registry): the dimension registry proposed by IMP-03 must include per-category applicability annotations if move types are to be marked N/A via template directives. Without this, contract authors cannot know which move types apply to their workflow category. The two items need a shared vocabulary decision before either Plan 06 or Plan 07 begins.
- IMP-17 (gate 15 deferral) touches both CONTEXT.md (exit gate list) and PHILOSOPHY.md (North Star #9 already updated by P1-IMP-27). Both files must change atomically. If only CONTEXT.md is updated, internal references from VISION.md and RESEARCH.md to "North Star #9 temporal reasoning" will point to content that has been removed or changed.

**Second-order risks:**
- IMP-02 ENHANCE: Keeping `TemporalAnalysis` in v1 means Plans 02 and 03 must emit timestamp data in a format the model can consume. The `TemporalAnalysis` Pydantic model must be authored with a placeholder schema in Plan 01, then validated and potentially revised after Plans 02/03 solidify the hook timestamp format. This coordination cost is low but must be made explicit in the execution wave dependencies.
- IMP-14 REFRAME: The N/A scoring directive approach requires the scoring aggregator to distinguish "not applicable" from "scored zero." If the aggregator treats N/A as 0, cascade-poisoning re-emerges through the aggregation step rather than the scoring step. The scoring aggregator (Plan 07 scope) must handle a third score state — `applicable: bool` on `DimensionScore` where `applicable=False` entries are excluded from the weighted average. This is a two-line change to `ScoreCard.overall_score` computation but must be called out explicitly or it will be missed.
- IMP-17 CONFIRM: Gate numbering should remain stable — mark gate 15 as "deferred to v2" inline rather than renumbering the remaining 15 gates, to preserve reference stability across VISION.md, RESEARCH.md, and any external documents referencing gate numbers by index.

---

## Adversarial Review: Test Suite Operability

**Items reviewed:** 7 (P5-IMP-18, P5-IMP-19, P5-IMP-20, P5-IMP-21, P5-IMP-22, P5-IMP-23, P5-IMP-24)

**Verdicts:** ENHANCE: 4 (IMP-18, IMP-19, IMP-20, IMP-23) | CONFIRM: 2 (IMP-22, IMP-24) | ENHANCE with PREREQUISITE maintained: 1 (IMP-21) | CREATE: 1 (P5-ADV-04)

**Cross-group conflicts:**
- IMP-19 (staging) and IMP-21 (marker stripping Prestep P3): IMP-21 must complete before Core-tier staging in IMP-19 begins. Neither item documents this ordering. Merge step: list IMP-21 as hard precondition of IMP-19's Core stage, not just of Plans 09-11 generically.
- IMP-19 (staging) and IMP-13 reframing (Debrief group): IMP-13 adds a debrief-trigger step to Plans 09-11 test teardown. Both changes modify Plans 09-11 scope simultaneously. Core-tier sub-wave must include the debrief trigger step from IMP-13 as part of its test teardown sequence.
- IMP-23 (run_batch timeout) and IMP-01 (Contract & Schema Integrity): the enhanced How specifies that timeout should eventually be read from `evaluation_config.timeout_seconds`. This is v2, not v1 blocker. Both reviewers have flagged this; note in Plan 08 implementation notes.
- IMP-19 (staging) and IMP-05 reframing (Contract & Schema Integrity, tiered authoring policy): both converge on Core-first contract authoring. Merge step should produce a single canonical staging statement covering both Plan 06 authoring order and Plans 09-11 execution order to prevent conflicting CONTEXT.md sections.
- IMP-18, IMP-20, IMP-22, IMP-24 are independent. No cross-group conflicts.

**Second-order risks:**
1. IMP-23 default timeout of 600 seconds may be too short for Core tier Agent Teams runs (attacker/defender/verifier on complex contracts can exceed 15 minutes). Default should be documented as "conservative minimum — expect Core tier runs to need 900-1800 seconds." Per-contract configuration is the right v2 mechanism; v1 needs a generous documented default.
2. IMP-22 wall-clock cost: 5 variants x 25 min = 125 min per dimension for Core tier. A 3-dimension improvement cycle is over 6 hours. Plan 12 Part 2 amendment must state this explicitly.
3. IMP-21 strip script must be idempotent (safe to run twice) and must fail fast on dirty working tree rather than producing a partial strip. Both properties are behavioral requirements for the script.
4. IMP-19 combined with IMP-05 reframing: single canonical staging statement needed at merge time to avoid conflicting tier sequencing guidance in different CONTEXT.md sections.
