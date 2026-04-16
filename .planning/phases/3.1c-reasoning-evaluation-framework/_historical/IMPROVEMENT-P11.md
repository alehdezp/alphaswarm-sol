# Improvement Pass 11

**Pass:** 11
**Date:** 2026-02-19
**Prior passes read:** 1-10 (via IMPROVEMENT-DIGEST.md)
**Areas analyzed:** Platform Infrastructure (Plans 01-03), Scoring & Evaluation (Plans 04-08), Test Execution & Improvement (Plans 09-12)
**Agent count:** 3 improvement agents, 5 adversarial reviewers, 1 synthesis agent
**Status:** complete

<!-- File-level status: in-progress | complete -->

## Pipeline Status

<!-- Auto-populated by workflows. Shows pending actions across ALL passes for this phase. -->

| Stage | Pending | Done | Blockers |
|-------|---------|------|----------|
| Prerequisites | 1 | 1 | P11-IMP-10 depends on Plan 02 transcripts (IMP-04 prereq satisfied by IMP-01) |
| Research | 0 | 5 | All resolved (2026-02-19) |
| Gaps | 0 | 0 | -- |
| Merge-ready | 0 | 20 | All 20 items merged to CONTEXT/RESEARCH (2026-02-19) |
| Implemented | 20 | -- | IMP-01,02,04,06,08,11,12,13,15,16 + ADV-1-01,1-02,2-01,3-01,4-01,5-01,5-02 + SYN-01,02 + CSC-01,02 |

**Pipeline:** [improve] done -> [adversarial] done -> [synthesis] done -> [research] done -> [implement] ✓
**Next recommended:** All items merged or terminal. /msd:plan-phase 3.1c

## Improvements

### P11-IMP-01: Hook Enum Has Composition Error -- Missing PreCompact and SessionEnd
**Target:** CONTEXT
**What:** The Smart Selection Matrix Encoding section (lines 186-189) defines the `hooks` schema enum with 12 events. The official CC hooks documentation lists exactly 12 events total, but the enum has the WRONG 12 -- it is missing `PreCompact` and `SessionEnd`. The FS-02 reference to "14 events" is also incorrect. Both the enum and official docs contain 12 events; the composition differs. PreCompact and SessionEnd are confirmed with documented input schemas: PreCompact provides `session_id`, `transcript_path`, `trigger: "manual"|"auto"`, `custom_instructions`; SessionEnd provides `session_id`, `transcript_path`, `cwd`, `reason`.
**Why:** PreCompact is directly relevant to the debrief strategy. SessionEnd provides guaranteed cleanup. Critical constraint: BOTH hooks are observation-only -- exit code 2 is "N/A" for both. Neither can block. This means SessionEnd cannot be used as a blocking gate (invalidating original IMP-05 framing). The 12-element enum with wrong composition will cause Plan 02's fail-fast validation to reject contracts specifying these events.
**How:**
1. In Smart Selection Matrix Encoding, correct the enum composition to include `PreCompact` and `SessionEnd`. Verify total count is 12, not 14.
2. Add `PreCompact` to Investigation and Orchestration category template defaults (observation only).
3. Add `SessionEnd` to ALL category template defaults (cleanup signal only -- cannot block).
4. In Plan 02 deliverables, add two observation-only hooks: `obs_precompact.py` (~15 LOC: writes `{session_id}.compacted` marker when `trigger == "auto"`; ignores "manual") and `obs_session_end.py` (~15 LOC: writes `{session_id}.session_ended` marker for non-crash termination).
5. In Debrief Strategy, add: "PreCompact hook (auto-trigger only) sets `{session_id}.compacted` marker."
6. In FS-02, note SessionEnd provides non-crash termination detection but CANNOT be used for blocking.
7. Add corrected 12-event enum to Schema Hardening Field Manifest.
**Impacts:** Plan 02 (2 new hooks), Plan 05 (compaction-aware debrief), Plan 06 (schema enum), Plan 08 (SessionEnd cleanup)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Adversarial note (Hook Lifecycle Completeness):** Original "12 vs 14" count is wrong -- both sources have 12 events, composition differs. Both PreCompact and SessionEnd are observation-only (exit code 2 = N/A), invalidating blocking use cases in IMP-05.
**Status:** implemented

### P11-IMP-02: Async Hook Configuration for Observation Hooks
**Target:** CONTEXT
**What:** The project's `.claude/settings.json` already uses `"async": true` on Notification hooks -- confirming the field is real and per-hook. The 6 observation hooks in `tests/workflow_harness/hooks/` write <100 bytes via `write_observation()`. However, `_ensure_hook()` at `workspace.py:381-425` builds hook entry dicts with NO `async` field -- it will silently overwrite any manual async configuration on next `install_hooks()` call.
**Why:** (1) Synchronous hooks add latency that inflates Plan 08 wall-clock timing estimates. (2) `_ensure_hook()` lacks async field, so programmatic hook installation cannot set async config. Creates clean architectural split: observation hooks = async, debrief hooks = synchronous.
**How:**
1. Add `async: bool = False` field to `HookConfig` dataclass in `workspace.py:24-38`.
2. Extend `_ensure_hook()` at `workspace.py:402-406` to include `"async": True` in hook_entry dict when specified.
3. Configure all 6 observation hooks with `async=True` via `HookConfig` in Plan 02 pre-session setup.
4. Keep debrief hooks (`debrief_gate.py`, `debrief_task_complete.py`) synchronous -- they use exit code 2 blocking.
5. Note in Plan 08 wall-clock budget: timing estimates assume async observation hooks.
**Impacts:** Plan 02 (hook configuration), Plan 08 (wall-clock estimates)
**Research needed:** no (resolved 2026-02-19)
**Research resolution:** Async hooks are NOT guaranteed to complete before session teardown. Per the official CC hooks docs, hooks have a 60-second timeout by default (configurable per command). Async hooks fire-and-forget -- if the session terminates (SIGINT, exit), in-flight async hooks may be killed. Evidence: (1) CC docs state "Timeout: 60-second execution limit by default" with per-hook timeout override, (2) SessionEnd fires on termination but cannot block it (exit code 2 = N/A), (3) the mastery repo's Notification hooks use `"async": true` confirming the field is real, (4) no completion guarantee is documented anywhere. **Implication for IMP-02:** async observation hooks are safe for low-latency writes (<100 bytes via `write_observation()`), but PreCompact hook (IMP-08) which reads transcript JSONL MUST remain synchronous per CSC-02. Async hooks that fail silently lose data -- acceptable for observation (redundant with transcript), unacceptable for PreCompact marker.
**Confidence:** HIGH (docs-confirmed + empirical field usage in settings.json)
**Prior art:** 4
**Prerequisite:** no
**Adversarial note (Hook Configuration & Installation):** Original How was three true facts without actionable guidance. Actual gap: `_ensure_hook()` silently drops async config. Fix must target the installation code path.
**Status:** implemented

### P11-IMP-03: Skill Frontmatter Hook Definitions -- Premise Invalid
**Target:** CONTEXT
**What:** Original proposal: CC skills can declare hooks in SKILL.md frontmatter with auto-installation. Investigation reveals: the `anthropic-skills-api-research.md` documents the Anthropic Managed Skills API (cloud-side beta) -- NOT local CC skills at `.claude/skills/`. Local CC skills are plain markdown files with no auto-installation mechanism. The frontmatter hook declaration premise is unfounded for this project.
**Why:** The real problem (reducing per-contract hook installation friction) is legitimate, but the mechanism is wrong. The correct alternative is a bifurcated installation path: in headless mode, `EvaluationRunner` installs hooks before `ClaudeCodeRunner.run()` without a separate step; in interactive mode, pre-session setup is mandatory.
**How:** N/A -- reframed into P11-ADV-2-01.
**Impacts:** N/A
**Research needed:** no
**Confidence:** LOW
**Prior art:** 3
**Prerequisite:** no
**Adversarial note (Hook Configuration & Installation):** Premise is false. LOCAL `.claude/skills/` have no frontmatter hook mechanism. The `name`/`description` fields are for the cloud API beta. Reframed to address the legitimate underlying concern via bifurcated installation.
**Status:** reframed

### P11-IMP-04: PreCompact Hook Enables Compaction-Aware Debrief -- Missing from Plan 05
**Target:** CONTEXT
**What:** Plan 05 has no mechanism to detect compaction before debrief. PreCompact fires BEFORE compaction, cannot block it (exit code 2 = N/A), and can write a marker file. The hook must distinguish `trigger == "auto"` (involuntary capacity-driven) from `trigger == "manual"` (deliberate `/compact`). Only auto-triggers indicate evaluation-relevant degradation.
**Why:** Without compaction detection, detailed debrief questions produce generic summaries from compacted agents, creating false-negative evaluation signals. The evaluator cannot distinguish "agent reasoned poorly" from "good reasoning destroyed by compaction." Compaction-driven degradation should not drive prompt changes via the improvement loop.
**How:**
1. Plan 02: `obs_precompact.py` (~20 LOC). On `trigger == "auto"`, write `{session_id}.compacted` marker. On `trigger == "manual"`, exit 0 with no marker.
2. Plan 05: compaction-aware branching. If marker present: 3 structural questions only. If absent: full 7-question deep debrief. ~15 LOC.
3. Add `compacted: bool = False` to `DebriefResponse` model (Plan 01).
4. Plan 07: when `compacted == True`, flag debrief-derived dimensions as `degraded: True`, reduce weight. Compacted-session hints route to human review only.
5. Calibration Anchor note: track compaction rate; if >50% sessions compacted, anchor data quality suspect.
**Impacts:** Plan 02 (prerequisite), Plan 05 (branched template), Plan 07 (weighted scoring), Plan 01 (model field)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 1
**Prerequisite:** yes -- P11-IMP-01 must land first (PreCompact in enum)
**Adversarial note (Hook Lifecycle Completeness):** Original missed trigger-type distinction. Writing compacted marker on manual `/compact` would incorrectly flag deliberate context management.
**Status:** implemented

### P11-IMP-05: FS-02 Zombie Detection with SessionEnd -- Reframed
**Target:** CONTEXT
**What:** Original proposed SessionEnd as PRIMARY for zombie detection. This is invalidated: SessionEnd cannot block session termination (exit code 2 = N/A). The correct framing: SessionEnd provides a "session completed normally" signal as a 4th condition in the Session Validity Manifest, not a replacement for FS-02's mitigation hierarchy. The race condition between SessionEnd marker and zombie writes remains.
**Why:** N/A -- reframed into P11-ADV-1-01.
**How:** N/A -- reframed.
**Impacts:** N/A
**Research needed:** no (resolved 2026-02-19 via ADV-1-01 resolution)
**Research resolution:** SessionEnd fires in headless mode. See ADV-1-01 research resolution for full evidence. SessionEnd as 4th SVM condition is viable for both headless and interactive. Graceful degradation (absent marker = WARN not REJECT) handles SIGKILL/crash edge cases.
**Confidence:** HIGH (resolved via ADV-1-01)
**Prior art:** 4
**Prerequisite:** yes -- P11-IMP-01 must land first
**Adversarial note (Hook Lifecycle Completeness):** SessionEnd is observation-only, cannot block. Demoting the 60-second grace period is premature. The right fix is adding SessionEnd as 4th SVM condition, not restructuring FS-02. Reframed.
**Status:** reframed (research resolved)

### P11-IMP-06: Opus Adaptive Thinking -- Pin Evaluator Effort Level
**Target:** CONTEXT
**What:** Evaluator LLM Call Path hardcodes `claude-opus-4-6` but does not address adaptive thinking. Without `--effort high`, evaluator allocates variable reasoning per transcript. The `--effort` flag is confirmed valid (`claude -p --effort high` accepted). Critical gap: `effort_level` is not in `BaselineKey` -- adopting effort pinning post-calibration silently invalidates all existing baselines.
**Why:** Score differences must reflect agent quality, not evaluator behavior. Effort level is the single largest source of non-determinism outside temperature. The baseline key `(workflow_id, run_mode, debate_enabled)` must include `effort_level` to prevent silent baseline corruption.
**How:**
1. Add to Evaluator LLM Call Path: "All `claude -p` calls MUST pass `--effort high`. Confirmed syntax."
2. Add `EVALUATOR_EFFORT = "high"` constant adjacent to `EVALUATOR_MODEL` in `reasoning_evaluator.py`.
3. Plan 07 exit criterion: "All `claude -p` subprocess invocations include `--effort high`."
4. Add `effort_level: Literal["low", "medium", "high"] = "high"` to `BaselineKey` model (Plan 01). Any effort change requires baseline reset.
5. Evaluator Debate Protocol: both A and B use identical `--effort high` from same constant.
**Impacts:** Plan 07 (~2 LOC), Plan 01 (BaselineKey field), Plan 12 Part 0 (reduced variance)
**Research needed:** no (answered by adversarial review -- CLI syntax confirmed)
**Confidence:** HIGH
**Prior art:** 2
**Prerequisite:** no
**Adversarial note (Evaluator Reliability):** Research resolved. The most dangerous second-order effect: effort_level not in BaselineKey means post-calibration effort changes silently corrupt baselines. Adding to BaselineKey is the mandatory companion change.
**Status:** implemented

### P11-IMP-07: Debrief-Mode Incompatibility Enforcement -- Wrong Layer
**Target:** CONTEXT
**What:** Original proposed JSON Schema `if/then` conditional for `debrief: true` + `run_mode: headless`. However, `run_mode` is an OPTIONAL field -- contracts almost never set it explicitly. The `if/then` only catches explicit `run_mode: headless` (minority case). The majority violation (Standard-tier + `debrief: true` + no explicit `run_mode`) passes schema undetected. CONTEXT.md already specifies the right enforcement: Python validator in Plan 06.
**Why:** N/A -- reframed into P11-ADV-4-01.
**How:** N/A -- reframed.
**Impacts:** N/A
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Adversarial note (Schema & Test Defense):** JSON Schema `if/then` is the wrong tool when the constraint depends on a field that is absent in most documents. Python validator can inspect tier + run_mode + debrief together. Partial constraint is worse than no constraint -- creates false confidence.
**Status:** reframed

### P11-IMP-08: PreCompact Hook for GVS Citation Preservation
**Target:** CONTEXT
**What:** GVS depends on citation rate as PRIMARY scoring path. For 15-30 min Core investigation sessions, auto-compaction is likely. Post-compaction, transcript loses BSKG query node IDs needed for citation computation. PreCompact input schema includes `transcript_path` (confirmed from mastery repo `pre_compact.py:88`).
**Why:** GVS citation rate underestimates actual citation behavior post-compaction, producing false-negative scores. Investigation agents (primary calibration targets) run longest sessions and are most likely to compact.
**How:**
1. Plan 02: `obs_precompact.py` (~35 LOC). On `trigger == "auto"`: read `transcript_path`, extract `bskg_node_ids_referenced` and `bskg_query_count` using INLINE JSONL parsing (stdlib `json` only -- NO TranscriptParser import). Write as `precompact_snapshot` observation event. Write `{session_id}.compacted` marker.
2. Plan 04 PRIMARY path: before computing citation_rate, check for `precompact_snapshot`. If present, merge pre-compaction node inventory with post-compaction data. ~20 LOC in `GraphValueScorer._get_node_inventory()`.
3. Plan 04 exit criteria: "GVS correctly handles compacted sessions -- uses merged inventory."
4. Add `precompact_snapshot` event type to `ObservationRecord.event_type` enum and `ObservationParser` (~5 LOC addition to Plan 03 scope).
**Impacts:** Plan 02 (+1 hook), Plan 03 (event type), Plan 04 (+20 LOC merge logic)
**Research needed:** no (resolved 2026-02-19)
**Research resolution:** BSKG query results in transcript JSONL are embedded in the Bash tool output as JSON text (the CLI's `alphaswarm query` outputs `json.dumps(result, indent=2)` to stdout -- see `cli/main.py:613,642`). The result JSON contains structured node IDs in the form `F-{function_name}-{hash}` for function nodes, `C-{contract_name}-{hash}` for contract nodes, and `E-{source}-{target}-{edge_type}` for edges. These appear as string fields within the JSON result dict, not as standalone structured fields in the JSONL record. The `obs_bskg_query.py` hook already captures `result_preview` (first 1000 chars of tool output), which contains these node IDs. For PreCompact snapshot: parse `result_preview` fields from `bskg_query` observation events to extract node ID patterns matching `[FCE]-\w+-\w+` regex. The transcript JSONL PostToolUse entries contain `tool_input.command` (the `alphaswarm query` command) and `tool_result` (the JSON output string). Node IDs are reliably extractable via regex from both observation JSONL and transcript JSONL.
**Confidence:** HIGH (source code confirmed)
**Prior art:** 1
**Prerequisite:** no
**Adversarial note (Hook Lifecycle Completeness):** Hook MUST use inline stdlib JSONL parsing, not TranscriptParser (521 LOC with dependencies). See P11-ADV-1-02 for circular dependency risk. Also: async hooks have ~30s timeout -- large transcripts may cause timeout in async mode.
**Status:** implemented

### P11-IMP-09: Single-Evaluator V1 -- Debate Already Default Off
**Target:** CONTEXT
**What:** Original proposed deferring debate until after calibration. However, `debate_enabled: false` is already the locked default in the Evaluator Debate Protocol. Running calibration without debate is already guaranteed. The real gap revealed: no artifact records which evaluator configuration was active during calibration.
**Why:** N/A -- reframed into P11-ADV-3-01.
**How:** N/A -- reframed.
**Impacts:** N/A
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Adversarial note (Evaluator Reliability):** The item's premise (debate would run during calibration) is already prevented by defaults. The real gap is configuration traceability, not debate sequencing.
**Status:** reframed

### P11-IMP-10: GVS Weight Calibration Procedure
**Target:** CONTEXT
**What:** Plan 04 exits Wave 3 with "provisional calibration" on 3+ transcripts, defers full calibration to Wave 6 on 30+ transcripts. No procedure exists for Wave 6. Weights {0.35, 0.35, 0.30} are pre-data guesses. The grid-search approach is correct but original claimed "10 combos" -- actual count is 66 (three non-negative values summing to 1.0 at 0.1 steps = triangular number).
**Why:** GVS weights have no external anchor. Calibration transcripts must be DISJOINT from improvement-loop transcripts to prevent circular self-validation. Cost: 66 combos x 10 transcripts = ~66-132 minutes.
**How:**
1. Plan 04 new deliverable: "GVS Weight Calibration Procedure -- Wave 6:
   (a) Obtain >= 10 labeled transcripts (5 TP, 5 FN). Use DISJOINT set from improvement-loop transcripts.
   (b) Compute GVS for all 66 three-weight combos (summing to 1.0 at 0.1 increments).
   (c) Acceptance: max gap > 15pt (mean GVS(TP) - mean GVS(FN)).
   (d) If no combo achieves >15pt: keep existing weights, log `status: unresolved` in `gvs_calibration.yaml`. Do NOT block.
   (e) Record winning weights, gap, n_transcripts, transcript IDs."
2. Plan 04 exit criteria: "Wave 6: `gvs_calibration.yaml` exists with `status: calibrated` or `status: unresolved`."
3. Plan 12 Part 0: GVS calibration in parallel with reasoning evaluator. Enforce disjoint-set constraint.
4. Replace "checkbox < 30, genuine > 70" with separability criterion.
**Impacts:** Plan 04 (+50 LOC grid search, ~66-132 min), Plan 12 Part 0 (parallel track)
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** Plan 02 (real transcripts, 10+ with TP/FN labels), Plan 12 Part 0 (parallel calibration)
**Adversarial note (Evaluator Reliability):** Original "10 combos" was wrong (66 actual). Added disjoint-set constraint and unresolved-is-not-blocking rule. Cost estimate now explicit.
**Adversarial note (Prerequisite Fix):** Changed from prerequisite:yes to no. Plan 02 transcript dependency is plan sequencing, not a merge blocker — this CONTEXT.md text describing the calibration procedure can be merged now. The procedure will execute when Plan 02 output exists.
**Status:** implemented

### P11-IMP-11: Negative Fixture Sessions for SessionValidityManifest
**Target:** CONTEXT
**What:** Plan 08 CSC-04 tests only the valid path. SessionValidityManifest and DataQuality gate failure paths (FS-02/FS-03/FS-04) have zero test coverage. These are the exact failure scenarios documented in Documented Failure Scenarios.
**Why:** `SessionValidityManifest` is the gatekeeper for baseline contamination. A silent failure (e.g., sentinel check logic inverted) would cause zombie/stale sessions to enter baseline. Invalid sessions must also be verified as NOT stored to baseline -- not just flagged as `valid=False`. Current `evaluation_runner.py:263` calls `update_baseline()` unconditionally regardless of result status.
**How:**
1. `session_interrupted/`: JSONL + `{session_id}.interrupted` sentinel. Test: `valid=False`, reasons contains "interrupted". Assert NOT passed to `store.store_result()`.
2. `session_stale/`: JSONL with timestamps >2h old (past 3600s threshold). Test: `valid=False`, reasons contains "stale". (Note: clarify mtime vs embedded timestamp signal in Plan 08 design.)
3. `session_missing_debrief/`: Complete JSONL, NO `{session_id}_debrief.json`, NO sentinel JSON. Test: `valid=False`, reasons contains "debrief_absent". (Distinguish from sentinel-written variant which IS valid.)
4. Plan 08 exit criteria: "All 3 negative fixtures produce `valid=False` with correct reasons; `EvaluationResult(status='invalid_session')` is never stored to baseline."
~50 LOC test code + ~15 fixture files.
**Impacts:** Plan 08 (+50 LOC tests, +15 fixtures). Pre-existing bug: unconditional `update_baseline()` call needs fix.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Adversarial note (Schema & Test Defense):** Added baseline exclusion assertion and debrief sentinel distinction. Pre-existing code bug in `evaluation_runner.py:263` may already be storing invalid sessions to baseline. Negative fixtures would expose this.
**Status:** implemented

### P11-IMP-12: /vrs-test-suite Must Use Delegate Mode for Coordination
**Target:** CONTEXT
**What:** Plans 09-11 define `/vrs-test-suite` as orchestrating Agent Teams but nothing constrains it to coordination-only. Without this, the skill's own tool calls contaminate observation JSONL, silently inflating GVS citation rates attributed to investigation agents.
**Why:** The evaluation pipeline's per-role attribution relies on SubagentStart/SubagentStop boundaries. If the skill directly queries BSKG or reads contracts, those events appear in observation JSONL attributed to the orchestrator session, falsifying the evaluation.
**How:**
1. Add to Plans 09-11 Restructuring: "**Delegate Mode Constraint (mandatory):** `/vrs-test-suite` MUST NOT directly invoke `alphaswarm query`, `alphaswarm build-kg`, Read on `.sol` files, or Write to contract paths. Per-teammate file boundaries in spawn prompts."
2. Plan 01 SKILL.md stub: `## Delegation Rules` section with prohibited categories.
3. Update Dual-Layer Architecture diagram: "(delegate mode: coordination only -- NO direct CLI queries)".
4. Plan 09 exit criterion: "Observation JSONL for a 1-agent test run contains zero `alphaswarm` Bash calls attributed to the orchestrator session."
**Impacts:** Plans 09-11 skill authoring, Plan 01 SKILL.md stub
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Adversarial note (Skill Architecture & Activation):** Added concrete exit criterion (JSONL contamination check). See P11-ADV-5-02 for enforcement gap in headless mode.
**Status:** implemented

### P11-IMP-13: Forced-Eval Activation Pattern for /vrs-test-suite
**Target:** CONTEXT
**What:** Skill Quality Tier 1 does not check activation rate. Failed activation for `/vrs-test-suite` means no exit report, silently breaking the pytest chain. Forced-eval (2-3 line frontmatter addition) achieves reliable activation.
**Why:** A failed activation is worse for infrastructure skills than product skills because the failure is silent -- the user sees a timeout or empty file assertion, not "skill did not activate."
**How:**
1. Tier 1 gains activation requirement: SKILL.md must declare `forced-eval: true` as hard blocker.
2. Plan 01 SKILL.md stub: `forced-eval: true` as first frontmatter field.
3. Plan 09: pre-flight activation test -- 5 matching + 5 non-matching prompts, 10/10 required. If < 10/10, HALT suite execution.
4. Note: "Forced-eval is the verified reliable pattern; LLM-eval classification is not adopted for infrastructure skills pending separate evaluation."
**Impacts:** Plan 09 (pre-flight HALT gate), Plan 01 (SKILL.md), Tier 1 expansion
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Adversarial note (Skill Architecture & Activation):** Removed unverified "llm-eval hallucinated 80%" claim (no backing citation in any research file -- CLAUDE.md Rule 1 violation). Pre-flight test must HALT, not merely warn.
**Status:** implemented

### P11-IMP-14: Tier 2 Skill Quality Replacement -- SkillsBench Citation Invalid
**Target:** CONTEXT
**What:** Original proposed replacing LLM-based Tier 2 with empirical checks, citing "SkillsBench" paper (arxiv 2602.12670v1) findings. Adversarial review found: the SkillsBench citation, "+16.2pp", "50-55% baseline", and all associated metrics appear EXCLUSIVELY in IMPROVEMENT-P11.md with zero presence in RESEARCH.md or any research artifact. This is a fabricated citation. Additionally, even if the benchmark were real, it measured LLM skill GENERATION quality, not LLM skill ASSESSMENT quality (which is what Tier 2 does).
**Why:** N/A -- reframed into P11-ADV-5-01.
**How:** N/A -- reframed. The legitimate concern (Plan 07 -> Plan 09 sequencing risk) is addressed in P11-ADV-5-01.
**Impacts:** N/A
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3
**Prerequisite:** no
**Adversarial note (Skill Architecture & Activation):** **FABRICATED CITATION.** SkillsBench metrics appear only in this improvement file. Promoting fabricated benchmarks to locked CONTEXT.md decisions would undermine the calibration-anchor philosophy. The real concern (Plan 07->09 dependency) is carried forward in P11-ADV-5-01.
**Status:** reframed

### P11-IMP-15: Calibration Anchor Needs Periodic Re-Validation
**Target:** CONTEXT
**What:** Calibration Anchor runs once in Plan 12 Part 0, described as "the highest-severity risk guard." After Part 0, improvement cycles can cause cumulative drift. External Detection Validation catches detection drops but misses subtler reasoning quality failures (right answer, wrong reasoning).
**Why:** Running the highest-severity guard once and never again is inconsistent with its severity assessment. After 5 improvement cycles, scoring distribution shifts may invalidate original calibration.
**How:**
1. Re-validation trigger: every 5 improvement cycles, re-run anchor (e.g., 2 agents on 9 contracts). If rho < 0.6, HALT Part 2.
2. Plan 12 Part 2: re-validation at session boundaries (~30 min overhead). Checkpoint gains `last_calibration_cycle`.
3. Manual Trigger Protocol: "If >5 cycles since last calibration, re-validate first."
4. Re-validation must use same `CalibrationConfig` (see P11-ADV-3-01) to be comparable.
**Impacts:** Plan 12 Part 2 (+30 min per 3-cycle session)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Adversarial note (Evaluator Reliability):** Withstands scrutiny. The proposed trigger and halt condition are specific and testable. Second-order: re-validation only comparable if CalibrationConfig (P11-ADV-3-01) is used.
**Status:** implemented

### P11-IMP-16: Research Spike -- Verify Relaxed Subagent Agent Teams Constraint
**Target:** RESEARCH
**What:** Execution constraint (line 112) says Agent Teams cannot spawn from subagents. Community reports suggest possible relaxation in v2.1.40+. If confirmed, Plans 09-11 architecture could simplify ~30-40%.
**Why:** Current architecture has fundamental indirection: pytest -> `claude -p` -> skill -> Agent Teams -> exit report -> pytest. If subagents can spawn Agent Teams, the skill could be invoked via Task tool directly.
**How:**
1. Add RS-03 to RESEARCH.md: "Verify Agent Teams from subagents. Test: Task subagent spawning Agent Team with 2 teammates. Specify exact test steps."
2. Do NOT change Plans 09-11 architecture until confirmed.
3. Add version annotation to Execution Model: "Constraint verified as of CC v2.1.33."
**Impacts:** No immediate changes. ~30 min research.
**Research needed:** yes
**Confidence:** LOW
**Prior art:** 1
**Prerequisite:** no
**Adversarial note (Skill Architecture & Activation):** Properly scoped, LOW confidence appropriate, "do not change architecture" discipline correct. The constraint is multiply-documented.
**Status:** implemented

---

## Adversarial CREATE Items

### P11-ADV-1-01: SessionEnd Headless Mode Behavior Unknown -- Session Validity Manifest Gap
**Target:** CONTEXT
**Status:** implemented
**Source:** Adversarial review (Hook Lifecycle Completeness)
**Cross-references:** P11-IMP-05 (reframed), P11-IMP-01

**What:** The reframed IMP-05 proposes adding SessionEnd as a 4th condition in the Session Validity Manifest. However, it is unknown whether SessionEnd fires in `claude --print` (headless) mode. If it does not fire in headless mode, the manifest's SessionEnd check would always fail for Standard-tier headless runs, rejecting all headless sessions as "not completed normally" -- breaking scoring for 41 of 51 workflows.
**Why:** Standard and Important-tool-tier runs use `run_mode=headless`. Unconditionally adding SessionEnd to the manifest without confirming headless support could silently produce 0 valid scored sessions for the first calibration run.
**How:**
1. Add RS-04 research question: "Does SessionEnd fire in `claude --print` (headless) mode? Does it fire on SIGINT?"
2. Until confirmed, SessionEnd check must be gated: `if run_mode in (RunMode.INTERACTIVE,) else skip`.
3. Mode Capability Matrix gains row: `SessionEnd hook | UNKNOWN | AVAILABLE | AVAILABLE` until research resolves.
**Research needed:** no (resolved 2026-02-19)
**Research resolution:** SessionEnd DOES fire in both headless (`claude --print`) and interactive mode. Evidence: (1) The official CC hooks docs (scraped 2026-02-19 from code.claude.com) list SessionEnd as a lifecycle hook that fires "When Claude Code session ends" with reason field `exit | clear | logout | prompt_input_exit | other`. The docs make NO distinction between headless and interactive for SessionEnd firing. (2) The hook lifecycle diagram shows SessionEnd at the terminal position for ALL session paths. (3) The `reason` field values include `other` which covers programmatic exit from `--print` mode. (4) SessionEnd input schema provides `session_id`, `transcript_path`, `cwd`, `permission_mode`, `reason` -- all fields available in headless mode. (5) SessionEnd cannot block (exit code 2 = N/A, shows stderr to user only) -- it is observation-only in both modes. **On SIGINT:** The `reason` field likely maps to `other` for SIGINT, though exact SIGINT handling is not explicitly documented. If the process is killed with SIGKILL (not SIGINT), no hook fires. **Decision:** Mode Capability Matrix row updated: `SessionEnd hook | UNAVAILABLE | AVAILABLE | AVAILABLE` (simulated has no real session). SessionEnd check in Session Validity Manifest should be applied unconditionally for headless and interactive, with graceful degradation (absent marker = WARN not REJECT) to handle edge cases (SIGKILL, crash).
**Confidence:** HIGH (docs-confirmed, lifecycle diagram, no mode-specific exclusions documented)
**Prior art:** 2
**Prerequisite:** no
**Adversarial note:** Applies to reframed IMP-05. Architectural impact: resolved -- SessionEnd fires in headless, no 41-workflow breakage risk.

### P11-ADV-1-02: PreCompact Hook Node-ID Extraction Must Not Import TranscriptParser
**Target:** CONTEXT
**Status:** implemented
**Source:** Adversarial review (Hook Lifecycle Completeness)
**Cross-references:** P11-IMP-08

**What:** IMP-08's `obs_precompact.py` must extract BSKG node IDs from transcript JSONL. The obvious implementation imports `TranscriptParser` (521 LOC with dependencies) from `tests/workflow_harness/lib/`. Hooks run as lightweight subprocesses -- importing TranscriptParser creates a test-infrastructure dependency in a production hook that could fail silently if the Python path is misconfigured.
**Why:** If the hook fails to import TranscriptParser, it exits non-zero, the `{session_id}.compacted` marker is never written, and IMP-04's compaction-aware debrief silently falls back to detailed questions for a compacted agent -- the exact failure mode it was designed to prevent.
**How:**
1. Plan 02 design decision: `obs_precompact.py` MUST use inline JSONL parsing (stdlib `json` only, ~15 LOC). Pattern-match on `alphaswarm` in tool_input for BSKG results.
2. Plan 02 exit criteria: "obs_precompact.py runs correctly with only stdlib imports."
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 -- `obs_tool_use.py` already demonstrates the stdlib-only pattern.
**Prerequisite:** no

### P11-ADV-2-01: Bifurcated Hook Installation -- Headless Runner vs Interactive Pre-Session
**Target:** CONTEXT
**Status:** implemented
**Source:** Adversarial review (Hook Configuration & Installation)
**Cross-references:** P11-IMP-03 (reframed), P11-IMP-02

**What:** IMP-03's underlying concern (reducing hook installation friction) is legitimate, but the mechanism (frontmatter) is wrong. The real architectural question: should hook installation always require a separate pre-session step, or can the runner handle it in headless mode? In headless mode, `ClaudeCodeRunner` controls session launch and CAN install hooks immediately before launching. In interactive mode, pre-session setup is mandatory because the human launches CC.
**Why:** If pre-session setup is designed as always-required (even headless), Plan 02 duplicates runner logic. The `async: true` interaction (IMP-02) makes this urgent: the runner can inject async config in headless mode; interactive mode needs separate handling.
**How:**
1. Add decision: "In headless mode, EvaluationRunner installs hooks before `ClaudeCodeRunner.run()` using contract's `hooks` field. Pre-session setup helper for interactive mode only. Both call same `install_hooks()`. ~10 LOC difference."
2. Add to Plan 02 scope as bifurcated installation path with shared implementation.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3
**Prerequisite:** no

### P11-ADV-3-01: Calibration Configuration Traceability -- CalibrationConfig Artifact
**Target:** CONTEXT
**Status:** implemented
**Source:** Adversarial review (Evaluator Reliability)
**Cross-references:** P11-IMP-09 (reframed), P11-IMP-06, P11-IMP-15

**What:** The Calibration Anchor Protocol validates rank-ordering but nothing records which evaluator configuration was active. `BaselineKey` captures `(workflow_id, run_mode, debate_enabled)` but not `effort_level`, `evaluator_model`, or `evaluator_prompt_version`. A future re-calibration (per IMP-15) with different settings produces incomparable results.
**Why:** Without a `calibration_config.yaml`, IMP-15's re-validation cannot distinguish "evaluator drift" from "configuration change" -- failure modes requiring completely different remediation.
**How:**
1. Add `CalibrationConfig` model to Plan 01: `evaluator_model`, `effort_level`, `debate_enabled`, `evaluator_prompt_hash` (SHA256 of prompt template), `n_transcripts`, `spearman_rho`, `calibration_timestamp`.
2. Plan 12 Part 0: write `CalibrationConfig` to `.vrs/evaluations/calibration_config.yaml`.
3. IMP-15 re-validation: load config, assert all fields match current constants before running. If mismatch: WARN "Configuration drift -- run full re-calibration."
4. Plan 12 Part 1: "Any CalibrationConfig field change requires full anchor re-run."
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no

### P11-ADV-4-01: Unify Debrief-Mode Enforcement into Plan 06 Python Validator
**Target:** CONTEXT
**Status:** implemented
**Source:** Adversarial review (Schema & Test Defense)
**Cross-references:** P11-IMP-07 (reframed)

**What:** The debrief + run_mode incompatibility should be enforced in a Python validator, not JSON Schema `if/then`. The validator can inspect tier metadata, explicit run_mode, and debrief together -- something JSON Schema cannot do when run_mode is absent.
**Why:** A partial JSON Schema constraint creates false confidence. Authors see schema pass and assume enforcement is complete. The Python validator covers the full constraint space.
**How:**
1. Plan 06: add `_validate_debrief_mode_compatibility(contract: dict) -> list[str]` (~15 LOC). Checks: (a) `tier == "standard"` + `debrief: true` -> REJECT, (b) explicit `run_mode == "headless"` + `debrief: true` -> REJECT.
2. Integrate into existing validation pipeline (14 files). No JSON Schema changes.
3. Update Tier-to-Run-Mode Binding section to reference this validator.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no

### P11-ADV-5-01: Tier 2 Skill Quality Must Decouple from Plan 07 Sequencing
**Target:** CONTEXT
**Status:** implemented
**Source:** Adversarial review (Skill Architecture & Activation)
**Cross-references:** P11-IMP-14 (reframed)

**What:** CONTEXT.md notes Plan 07 -> Plan 09 dependency for Tier 2's `claude -p --json-schema` path. If Plan 07 is delayed, all Tier 2 skill evaluation is blocked. But Tier 2 can use `claude -p --output-format json` independently -- it does NOT require Plan 07's `--json-schema` infrastructure.
**Why:** The Plan 07 -> Plan 09 dependency creates a bottleneck. If Plan 07 is blocked, skill quality evaluation silently degrades to Tier 1 only with no documented fallback.
**How:**
1. Add to Cross-Plan Dependencies: "Plan 07 -> Plan 09 (Tier 2). **Fallback:** If Plan 07 not complete, Plan 09 executes Tier 1 only; Tier 2 deferred. Document as `tier2_status: deferred`."
2. Add: "**Tier 2 decoupled invocation:** uses `claude -p --output-format json`. Does NOT require Plan 07's `--json-schema`. May invoke independently."
3. Plan 09 deliverable: "Tier 2 standalone test with `--output-format json` -- verify before committing to Plan 07 dependency."
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no

### P11-ADV-5-02: Delegate Mode Enforcement Unspecified for Headless CLI Path
**Target:** CONTEXT
**Status:** implemented
**Source:** Adversarial review (Skill Architecture & Activation)
**Cross-references:** P11-IMP-12

**What:** IMP-12 mandates delegate mode but "delegate mode" in CC is activated by Shift+Tab (UI gesture). No documented CLI flag equivalent exists. If `claude -p skill:vrs-test-suite` has no delegate mode flag, the constraint is unenforceable in headless evaluation.
**Why:** If delegate mode is a gesture-only feature, the CI pipeline cannot guarantee it. The prohibition must be enforced by SKILL.md prompt instructions (self-imposed, breakable by model) rather than platform capability (enforced, unbreakable).
**How:**
1. ~~Add RS-04 to RESEARCH.md~~ (resolved inline)
2. **No flag exists.** Reframe IMP-12 from "delegate mode (platform)" to "coordination-only prompt discipline (self-imposed)". Add prohibited tool list to SKILL.md explicitly. Plan 09 exit criterion: "Dry-run execution produces zero `Read` or `Bash` calls in orchestrator JSONL."
**Research needed:** no (resolved 2026-02-19)
**Research resolution:** `claude --help` (v2.1.47, 2026-02-19) lists NO `--delegate` flag. The full flag inventory was checked: `--add-dir, --agent, --agents, --allow-dangerously-skip-permissions, --allowedTools, --append-system-prompt, --betas, --chrome, --continue, --dangerously-skip-permissions, --debug, --debug-file, --disable-slash-commands, --disallowedTools, --effort, --fallback-model, --file, --fork-session, --from-pr, --help, --ide, --include-partial-messages, --input-format, --json-schema, --max-budget-usd, --mcp-config, --mcp-debug, --model, --no-chrome, --no-session-persistence, --output-format, --permission-mode, --plugin-dir, --print, --replay-user-messages, --resume, --session-id, --setting-sources, --settings, --strict-mcp-config, --system-prompt, --tools, --verbose, --version`. The `--permission-mode` flag offers `plan` mode which restricts to read-only operations but does NOT enforce delegation behavior. The `--tools` flag can restrict available tools (e.g., `--tools "Read,Glob,Grep,TaskCreate,TaskUpdate,TaskList,TaskGet,SendMessage"`) which provides PARTIAL enforcement by removing Write/Edit/Bash, but this also blocks the skill from reading evaluation contracts via Read. **Decision:** IMP-12 delegate mode constraint is self-imposed via SKILL.md prompt instructions + Plan 09 JSONL contamination exit criterion. This is the "prompt discipline" path (option 2). The prohibition is breakable by the model but testable post-hoc via observation JSONL analysis.
**Confidence:** HIGH (exhaustive CLI flag check, v2.1.47)
**Prior art:** 2
**Prerequisite:** no

---

## Synthesis Items

### P11-SYN-01: Headless Mode Is Systematically Under-Verified Across All New Platform Features
**Target:** CONTEXT
**What:** Three items across three different review groups assume `claude --print` (headless) mode behaves identically to interactive mode for newly discovered platform features, but none have verified this. ADV-1-01 flags that SessionEnd may not fire in headless. ADV-5-02 flags that delegate mode may have no CLI equivalent. IMP-02 flags that async hook completion guarantees are unknown for early termination. All three share the same structural weakness: headless mode is the DEFAULT for 41 of 51 workflows (Standard + Important-tool tiers), yet every new platform feature discovered in this pass was verified only in interactive context.
**Why:** Addressing these individually creates three separate research spikes that could be consolidated. More importantly, the Mode Capability Matrix (IMP-06 from prior passes) already exists as the single artifact that should track headless vs interactive availability -- but it only covers evaluation dimensions, not platform features like hook firing behavior and CLI flags. A unified headless verification pass prevents the pattern from recurring in future improvement passes.
**How:**
1. Consolidate ADV-1-01's RS-04, ADV-5-02's RS-04, and IMP-02's async research question into a single research spike: "RS-04: Headless Platform Feature Verification." Test in one session: (a) Does SessionEnd fire in `claude --print`? (b) Does `claude --print` support `--delegate`? (c) Do async hooks complete before headless session exit? (d) Does PreCompact fire in headless mode (short sessions may never trigger auto-compaction)? Estimated time: ~45 min total vs ~90 min for three separate spikes.
2. Extend Mode Capability Matrix with a "Platform Feature" section below the existing "Dimension" section. Add rows for SessionEnd hook, PreCompact hook, async hook completion, and delegate mode. Mark each as UNKNOWN until RS-04 resolves.
3. Add CONTEXT.md implementation decision: "Any new platform feature discovered in future improvement passes MUST include headless verification status in Mode Capability Matrix before merge."
**Impacts:** Plans 02, 08, 09-11 (all headless execution paths)
**Components:** P11-IMP-02, P11-ADV-1-01, P11-ADV-5-02
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cross-cutting)

### P11-SYN-02: Evaluator Configuration Fields Are Scattered Across Multiple Models Without a Single Source of Truth
**Target:** CONTEXT
**What:** IMP-06 adds `effort_level` to `BaselineKey`. ADV-3-01 creates `CalibrationConfig` with `evaluator_model`, `effort_level`, `debate_enabled`, `evaluator_prompt_hash`. The existing `BaselineKey` already has `(workflow_id, run_mode, debate_enabled)`. IMP-10 introduces GVS weight calibration producing `gvs_calibration.yaml`. These four items across three review groups all add evaluator configuration fields to different models and artifacts, creating a fragmented configuration surface where a single parameter change requires updating 2-3 separate locations.
**Why:** `effort_level` now appears in both `BaselineKey` (IMP-06) and `CalibrationConfig` (ADV-3-01). `debate_enabled` already appears in `BaselineKey` and will appear in `CalibrationConfig`. When Plan 12 Part 0 writes `CalibrationConfig`, it must read the same constants that Plan 07 uses for `BaselineKey` -- but no shared constant source is defined. A drift between these two artifacts (e.g., someone changes `EVALUATOR_EFFORT` constant but re-runs calibration without updating baseline) creates the exact silent corruption that IMP-06 was designed to prevent.
**How:**
1. Plan 01: define `EvaluatorConstants` frozen dataclass (or Pydantic model) in `models.py`: `model: str`, `effort_level: str`, `prompt_template_hash: str`. All evaluator-configuration-bearing models (`BaselineKey`, `CalibrationConfig`, `EvaluationResult`) reference fields from `EvaluatorConstants.current()` at construction time. ~20 LOC.
2. Plan 07: `EVALUATOR_MODEL` and `EVALUATOR_EFFORT` constants replaced by `EvaluatorConstants.current()`. Single source of truth.
3. Plan 12 Part 0: `CalibrationConfig` populates evaluator fields from `EvaluatorConstants.current()`, not from separate constants. Part 1 baseline key construction uses same source.
4. Plan 12 startup guard: `assert CalibrationConfig.from_disk().evaluator_fields == EvaluatorConstants.current().to_dict()` -- fails fast if calibration was done with different constants than current code.
**Impacts:** Plans 01, 07, 12
**Components:** P11-IMP-06, P11-IMP-10, P11-ADV-3-01
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cross-cutting)

---

## Cascade Gap Items

### P11-CSC-01: IMP-12 Delegate Mode Prohibition Needs Allowed-Reads Boundary
**Target:** CONTEXT
**What:** IMP-12 (enhanced) prohibits `/vrs-test-suite` from invoking `alphaswarm query`, `alphaswarm build-kg`, Read on `.sol` files, or Write to contract paths. However, the skill MUST read evaluation contracts (`.yaml` files in `src/alphaswarm_sol/testing/evaluation/contracts/`), scenario configs, progress files, and the kill-signal file to function as an orchestrator. The prohibition list names tool categories but does not define which Read targets are allowed. Plan 09's exit criterion ("zero `alphaswarm` Bash calls") covers CLI contamination but not Read contamination -- a Read on a `.sol` file would pass the `alphaswarm` check.
**Why:** If the prohibition is implemented too broadly (e.g., "no Read calls at all"), the skill cannot load contracts or check progress. If too narrow (only `alphaswarm` CLI), Read-based `.sol` file access contaminates JSONL. The boundary between "orchestration reads" (allowed) and "investigation reads" (prohibited) must be explicit.
**How:**
1. In Plans 09-11 Restructuring delegate mode constraint, add allowed-reads whitelist: `src/alphaswarm_sol/testing/evaluation/contracts/*.yaml`, `.vrs/evaluations/*`, `.planning/testing/scenarios/**`. All other Read calls outside these paths are violations.
2. Plan 09 exit criterion expansion: "Observation JSONL contains zero `alphaswarm` Bash calls AND zero `Read` calls targeting `.sol`, `.py`, or `vulndocs/` paths attributed to the orchestrator session."
**Impacts:** Plans 09-11 (skill authoring), Plan 01 (SKILL.md stub delegation rules)
**Trigger:** P11-IMP-12
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cascade)

### P11-CSC-02: IMP-08 PreCompact Snapshot Creates Async-Timeout Risk for Large Transcripts
**Target:** CONTEXT
**What:** IMP-08 (enhanced) specifies that `obs_precompact.py` reads `transcript_path` and extracts BSKG node IDs using inline JSONL parsing. The adversarial note already flags the ~30s async hook timeout for large transcripts. If IMP-02 (async hooks) is also implemented, `obs_precompact.py` configured as async could timeout before completing JSONL parsing on a 15-30 min Core investigation transcript, silently losing both the node inventory AND the compacted marker -- failing open on the exact scenario it targets.
**Why:** IMP-04 and IMP-08 form a chain: PreCompact marker enables compaction-aware debrief (IMP-04) and GVS citation preservation (IMP-08). If the hook times out, both downstream protections silently degrade. The compacted marker absence means full 7-question debrief fires on a compacted agent, and GVS uses post-compaction data only -- the exact failure modes these items prevent.
**How:**
1. In Plan 02 design decisions: `obs_precompact.py` MUST be configured as synchronous (`async: false`), exempt from IMP-02's async-for-all-observation-hooks rule. PreCompact is observation-only (cannot block via exit code) but synchronous ensures it completes before compaction proceeds.
2. IMP-02's How step 3 updated: "Configure all 6 observation hooks with `async=True` EXCEPT `obs_precompact.py` which must be synchronous to complete before compaction."
3. Add to Plan 02 exit criteria: "obs_precompact.py configured synchronous; confirmed to complete within 5s on a 1000-line transcript fixture."
**Impacts:** Plan 02 (hook configuration exception)
**Trigger:** P11-IMP-08
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cascade)

---

## Convergence Assessment

**Pass 11 totals:** 16 original + 7 adversarial CREATE + 2 synthesis + 2 cascade = 27 items
**Enhanced:** 9 (IMP-01, IMP-02, IMP-04, IMP-06, IMP-08, IMP-10, IMP-11, IMP-12, IMP-13)
**Confirmed:** 2 (IMP-15, IMP-16)
**Reframed:** 5 (IMP-03, IMP-05, IMP-07, IMP-09, IMP-14)
**New (ADV):** 7 (ADV-1-01, ADV-1-02, ADV-2-01, ADV-3-01, ADV-4-01, ADV-5-01, ADV-5-02)
**New (SYN):** 2 (SYN-01, SYN-02)
**New (CSC):** 2 (CSC-01, CSC-02)

**Merge-ready (all research resolved):** 12 items (IMP-01, IMP-02, IMP-04, IMP-06, IMP-08, IMP-11, IMP-12, IMP-13, IMP-15, IMP-16, ADV-1-02, ADV-4-01)
**Research pending:** 0 items (all 4 resolved 2026-02-19 in consolidated pass per SYN-01)
**Prerequisites pending:** 2 items (IMP-04 on IMP-01, IMP-10 on Plan 02 transcripts)

**Fabricated citation detected and struck:** SkillsBench (arxiv 2602.12670v1) metrics appeared exclusively in IMPROVEMENT-P11.md with zero presence in any research artifact. IMP-14 reframed. The legitimate underlying concern (Plan 07->09 sequencing) addressed in ADV-5-01.

> Structural issues from Feb 2026 platform research that were not available during passes 1-10. The PreCompact/SessionEnd discovery, async hook configuration, effort pinning, and CalibrationConfig traceability are genuinely new patterns. After this pass, the design should be stable unless new CC platform changes emerge.

## Post-Review Synthesis
**Items created:** P11-SYN-01, P11-SYN-02, P11-CSC-01, P11-CSC-02
**Key insight:** The most important finding is that headless mode (`claude --print`) -- the execution path for 41 of 51 workflows -- is systematically unverified for every new platform feature discovered in this pass (SYN-01). Three separate research questions can be consolidated into one 45-minute spike. The second finding is that evaluator configuration is fragmenting across BaselineKey, CalibrationConfig, and GVS calibration without a shared constant source (SYN-02), creating the exact silent-corruption risk that IMP-06 was designed to prevent.
