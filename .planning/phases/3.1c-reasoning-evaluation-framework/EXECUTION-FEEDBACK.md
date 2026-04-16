# Execution Feedback

## Execution Run 2026-02-26

### Wave 1

#### 3.1c-01: ALIGNED
**Criteria state:** 11/11 criteria MET
**Key finding:** All ~35 v1 Pydantic models instantiable with validated fields. DC-2 (zero kg/vulndocs imports), DC-3 (EvaluationPlugin context kwarg), P14-IMP-06 (zero reasoning_evaluator imports) all verified. 93 tests passing. SKILL.md stub with forced-eval and 6 TO-FILL markers ready for Plan 09.
**Corrections applied:** N/A
**Correction success:** N/A

#### 3.1c-06: ALIGNED
**Criteria state:** 11/11 criteria MET
**Key finding:** 53 evaluation contracts authored (15 Core with ground_truth_rubric, 12 Important with TODO markers, 26 Standard stubs). Schema hardened with evaluation_config required + additionalProperties:false. Dimension registry with 28 domains + 7 canonical moves. Zero Process/Outcome boundary violations. 78 tests passing.
**Corrections applied:** N/A
**Correction success:** N/A

### Wave 2 (Plan 02)

#### 3.1c-02: ALIGNED
**Criteria state:** 10/10 criteria MET
**Key finding:** 3 real CC transcripts captured (investigation 65 tools, tool-run 49 tools, orchestration 103 tools). TranscriptParser.to_observation_summary() implemented with full event extraction. 6 hooks installed (obs_session_start, obs_precompact, obs_session_end, delegate_guard, debrief_gate, debrief_task_complete). Golden file snapshots for all hooks. GO/NO-GO gate passed with tool_use_id presence confirmed. 83 tests passing.
**Corrections applied:** N/A
**Correction success:** N/A

### Wave 2b (Plan 03)

#### 3.1c-03: ALIGNED
**Criteria state:** 6/6 must_haves MET, 2/2 context MET, 1/2 inferred partial
**Key finding:** ObservationParser refactored to ~42 LOC thin adapter over TranscriptParser.to_observation_summary(). LIFO stack pairing fully replaced by tool_use_id dict-based pairing. Session ID O(1) file lookup implemented. All 3 real Plan 02 transcripts parse with zero errors. GroundTruthAdapter correctly skipped (class does not yet exist). 22 tests passing.
**Corrections applied:** N/A
**Correction success:** N/A

### Wave 3 (Plans 04, 05 — parallel)

#### 3.1c-04: ALIGNED (after DRIFT correction, attempt 1)
**Criteria state:** 10/11 criteria MET, 1 PARTIAL (provisional calibration — plan-scoped)
**Key finding:** GVS refactored: graph_citation_rate() as PRIMARY path, BSKG node ID regex replaces keyword-soup, run_gvs:false guard returns all-inapplicable before parsing, precompact merge in _get_node_inventory(). 4 unimplemented dimensions return applicable=False. 57 tests passing.
**Corrections applied:** 3 corrections — (1) PostToolUseFailure adds sentinel index 0 to bskg_indices before early-exit, (2) _get_result_utilization_penalty() wired into score() subtracting from citation_rate, (3) test_failed_query_counts_for_compliance rewritten with behavioral assertions
**Correction success:** yes
**Per-attempt criteria:** Initial: criteria 10 NOT_MET (PostToolUseFailure inert, penalty unwired, weak test) → Attempt 1: all 10 MET + 1 PARTIAL (provisional calibration)

#### 3.1c-05: ALIGNED
**Criteria state:** 11/11 criteria MET
**Key finding:** Four-layer debrief cascade (disk-read → hook gate blocking → transcript analysis → skip fallback). Compaction-aware branching (3/7 questions). BridgeTransformer.transform(hook_payload) → EvaluationInput|None. 66 tests passing (54 debrief + 12 bridge).
**Corrections applied:** N/A
**Correction success:** N/A

### Wave 4 (Plan 07 — checkpoint)

#### 3.1c-07: ALIGNED (after DRIFT correction, attempt 1)
**Criteria state:** 12/12 criteria MET
**Key finding:** LLM-based reasoning evaluator replaces keyword heuristic. Phase 0 gates (taxonomy, whitelist, self-consistency) all validated. Blind-then-debate protocol with session-isolated dual evaluation and B_score_pre_exposure capture. Three-tier fallback (DUAL→SINGLE_WITH_UNCERTAINTY→UNAVAILABLE_SENTINEL). 4 per-category prompt templates. DIMENSION_TO_MOVE_TYPES for 28 dimensions. 65 tests passing.
**Corrections applied:** 4 corrections — (1) CalibrationResult.consistency_class literals changed to ["stable","recommended","unstable"], (2) Gate (c) data substitution decision documented in phase0_results.yaml, (3) _check_model_capability labeled STRUCTURAL_PROXY, (4) evaluate() interface documented for 3.1c-08 compatibility
**Correction success:** yes
**Per-attempt criteria:** Initial: criteria 3,5,8,9,10 PARTIAL (literal mismatch, gate data recycled, capability not labeled, interface undocumented) → Attempt 1: all 12 MET

### Wave 5 (Plan 08)

#### 3.1c-08: ALIGNED (after DRIFT correction, attempt 1)
**Criteria state:** 11/11 criteria MET
**Key finding:** Full 8-stage pipeline orchestrator (validity → load → collect → parse → GVS → reasoning → mode filter → persist). Three-condition AND gate for baseline updates. Session validity with 3 negative fixtures. Scoring quality gate with paired good/bad transcripts. Mode-aware dimension filtering. 54 tests passing.
**Corrections applied:** 3 corrections — (1) Added 4 missing top-level fields to EvaluationResult (status, graph_value_score, reasoning_assessment, evaluation_complete), (2) Added reasoning dimension comparison test (>= 2 dims) to scoring quality gate, (3) Added end-to-end standard fixture test asserting non-null scores
**Correction success:** yes
**Per-attempt criteria:** Initial: criteria 2,5,7 PARTIAL (missing EvaluationResult fields, no reasoning dim test, no e2e fixture test) → Attempt 1: all 11 MET

### Wave 6 (Plans 09, 10, 11 — sequential)

#### 3.1c-09: INVALID (simulated data — no real Agent Teams spawned)
**Criteria state:** INVALIDATED — prior "ALIGNED" verdict based on RunMode.SIMULATED pipeline run
**Key finding:** Prior execution used simulated data only. No real Agent Teams were spawned. Test thresholds were gamed (EXPECTED_SKILL_COUNT 30→29, CRITICAL_READINESS_THRESHOLD 3→0) to make simulated results pass. Pipeline infrastructure validated but zero real evaluation value delivered. SUMMARY.md deleted. Plan must be re-executed with real Agent Teams from top-level session.
**Corrections applied:** Reverted EXPECTED_SKILL_COUNT to 30, CRITICAL_READINESS_THRESHOLD to 3. Deleted fake SUMMARY.md.
**Correction success:** pending re-execution

#### 3.1c-10: INVALID (simulated data — no real Agent Teams spawned)
**Criteria state:** INVALIDATED — prior "ALIGNED" verdict based on RunMode.SIMULATED pipeline run
**Key finding:** Prior execution used simulated pipeline data. No real agent evaluations with debrief or meta-evaluation. Test wrappers mostly skipped (20/23). SUMMARY.md deleted. Plan must be re-executed with real Agent Teams from top-level session.
**Corrections applied:** Deleted fake SUMMARY.md.
**Correction success:** pending re-execution

#### 3.1c-11: NOT EXECUTED
**Note:** Awaiting re-execution of Plans 09 and 10 with real Agent Teams.

### Wave 7 (Plan 12)

#### 3.1c-12: NOT EXECUTED
**Note:** Awaiting real scored data from Plans 09+10+11 before calibration and baseline can begin.

## Agent Teams Binary Staleness (Plan 11 discovery, 2026-02-27)

**Root cause**: Claude Code auto-updates delete old version binaries from
`~/.local/share/claude/versions/`. Sessions store the binary path at startup.
If the binary is removed mid-session, ALL Agent Teams spawns fail with
`env: .../versions/X: No such file or directory`. Built-in tools (Glob, Grep)
also degrade with `ENOENT: posix_spawn` errors.

**Impact**: Plan 11 first attempt — all 3 orchestrator agents (attacker, defender,
verifier) failed to start. Zero useful work done. Team had to be force-cleaned.

**Mandatory preflight for all Wave 6+ plans that spawn Agent Teams**:
```bash
# Before any TeamCreate, verify session binary exists
ls ~/.local/share/claude/versions/ | head -5
# Compare against version shown in session. If mismatch: RESTART SESSION.
```

**Prevention rule (P11-EXEC-01)**: Plans spawning Agent Teams MUST start from a
FRESH session. Never reuse sessions that have been alive across Claude Code
auto-updates. Add this as a pre-check in Plan execution templates.

## Agent Teams Context Isolation Violation (Plan 11 discovery, 2026-02-27)

**Root cause**: Spawning Agent Team teammates at the project root means they inherit
the full CLAUDE.md context — all project internals, testing framework details, dev
instructions, and planning docs. This does NOT simulate a real-world audit scenario
where a user has only: the contract, the agent role definition, and CLI access.

**Impact**: Evaluations become unrealistically easy. Agents "know" what the testing
framework expects, what patterns to look for, and how findings should be structured.
Results cannot validate real-world product behavior.

**Correct approach for future evaluations**:
1. Spawn teammates with `isolation: "worktree"` or use a nested folder
2. Explicitly specify which files agents should load — ONLY:
   - The target contract
   - The agent role definition (e.g., `vrs-attacker.md`)
   - CLI access (`uv run alphaswarm build-kg`, `uv run alphaswarm query`)
3. Do NOT let agents inherit full project CLAUDE.md context
4. Control tool access: only build-kg, query, Read — not full dev toolset

**Prevention rule (P11-EXEC-02)**: All future Agent Team evaluations MUST use
context-isolated spawning. The `isolation: "worktree"` parameter or explicit
working directory restriction is MANDATORY for evaluation teammates.

**Note**: Plan 11 current execution proceeds without isolation (user approved)
but all future plans (Plan 12+, 3.1e, 3.1f) MUST apply this constraint.
