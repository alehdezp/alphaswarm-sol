# Improvement Pass 1

**Date:** 2026-03-01
**Phase:** 3.1c.2
**Status:** complete

## Pipeline Status

| Stage | Pending | Done | Blockers |
|-------|---------|------|----------|
| Prerequisites | 0 | 1 | — |
| Research | 0 | 3 | — |
| Gaps | 0 | 3 | — |
| Merge-ready | 0 | 21 | — |

**Pipeline:** [discuss] ~ → [improve] ✓ → [pre-impl] ✓ → [research] ✓ → [implement] ✓ → [plan] ~ → [execute] —
**Merged:** 21 items into CONTEXT.md
**ADV Validation:** 8 items reviewed — 1 RESEARCH, 7 ENHANCE

## Adversarial Lenses

| Lens | Brief | Items | Attack Vector |
|------|-------|-------|---------------|
| Enforcement Model Correction | You are the executor reading CONTEXT.md Assumptions and Decisions. Assumption 1 claims subagent_type enforces tool access; Decision D-1 claims prompt-based restrictions work. Both were disproven by Plan 12 Batch 1 where agents used Bash(python -c "import ...") to bypass. For each item: if the proposed fix still leaves Bash as an open vector, what specifically breaks? | P1-IMP-01, P1-IMP-02, P1-IMP-03, P1-IMP-08, P1-IMP-11 | Does the proposed enforcement fix actually close the Bash bypass vector, or does it just rename the gap? |
| Plan Completeness & Verification | You are the executor reading the 6-plan table and exit criteria. Plan 02 depends on JSONL access (unverified), Plan 05 re-designs an already-designed protocol, Plan 06 has "verify PASS" with no thresholds. For each item: if you encounter this instruction for the first time with no prior context, what specifically would confuse, block, or mislead you? | P1-IMP-04, P1-IMP-05, P1-IMP-06, P1-IMP-07, P1-IMP-09, P1-IMP-10, P1-IMP-12, P1-IMP-13, P1-IMP-14 | Are the plans verifiable and non-circular, or do they assume infrastructure that doesn't exist yet? |

## Improvements

### P1-IMP-01: Assumption 1 Is Factually Incorrect — subagent_type Does Not Enforce Tool Restrictions
**Target:** CONTEXT
**What:** Assumption 1 ("subagent_type controls tool access") is factually wrong and must be replaced. The actual enforcement primitive is delegate_guard.py's PreToolUse hook, but only when its `blocked_patterns` cover Bash invocations — since agents can use `Bash(cat ...)` or `Bash(python -c "import ...")` to bypass any `blocked_tools` list.
**Why:** Every plan that treats either `subagent_type` OR `blocked_tools`-only configs as sufficient enforcement will fail the same way Plan 12 did. The failure mode is Bash, not Read/Write tools. Stating the correct mechanism precisely prevents the next generation of partially-correct configs.
**How:**
1. In CONTEXT.md Assumptions section, replace Assumption 1 with: "Tool access in evaluation sessions is enforced via the delegate_guard.py PreToolUse hook. The hook blocks by tool name (`blocked_tools`) AND by Bash command patterns (`blocked_patterns`). `subagent_type` determines system prompt only — it does not restrict tools."
2. Add: "Assumption 1a: Bash calls matching `blocked_patterns` (e.g., `python`, `import`, `cat`) are blocked at the hook layer, not the tool layer. Both lists must be configured for complete enforcement."
3. Cross-reference with the delegate_guard.py `blocked_patterns` field as evidence that this capability already exists.
**Impacts:** Every plan in this phase that relies on subagent_type for tool restriction needs to be redirected to use delegate_guard.py activation instead.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL

### P1-IMP-02: Decision D-1 Is Contradicted by Its Own Triggering Failure
**Target:** CONTEXT
**What:** D-1 must be rewritten from "prompt-enforced tool restrictions" to "hook-enforced restrictions via delegate_guard.py," but only after confirming that `blocked_patterns` in delegate_guard.py actually intercepts Bash-level Python import calls — not just filename patterns. The rewrite is blocked until this is confirmed with a canary test.
**Why:** Rewriting D-1 to name delegate_guard.py without confirming Bash pattern coverage encodes a third false enforcement model. "Impossible to fabricate" requires that `Bash(python -c "import alphaswarm_sol...")` returns exit 2. Whether `blocked_patterns: [".sol"]` accomplishes this is unknown from the cited source.
**How:**
1. Before rewriting D-1, run: inside an evaluation session with delegate_guard.py active, invoke `Bash(python -c "import sys; print(sys.path)")`. Confirm exit 2.
2. If blocked: rewrite D-1 to "Enforcement uses delegate_guard.py PreToolUse hook with `blocked_tools` (tool-level) and `blocked_patterns` (Bash command-level, including `python`, `import`, raw module paths)."
3. If NOT blocked: D-1 rewrite must additionally specify that a new blocked_patterns entry `python` or `python -c` must be added to the eval config, and that the hook's pattern matching logic must be verified to apply to the full Bash command string.
4. Add canary test to exit criteria: `test_bash_python_import_blocked` must be a required passing test before any plan is marked complete.
**Impacts:** Plans that implement "configure agent type" for restriction will need to implement "activate delegate_guard.py config" instead.
**Research needed:** no (resolved: GAP-01)
**research_summary:** Current `blocked_patterns: [".sol"]` does NOT block Python imports via Bash. Pattern `.sol` only matches Solidity file paths, not `python -c "import os"` or `from alphaswarm_sol...`. Eval config must add `["python", "python3", "import "]` to blocked_patterns.
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL

### P1-IMP-03: Exit Criterion 1 Is Unverifiable as Written
**Target:** CONTEXT
**What:** Exit criterion 1 states: "Evaluation-specific agent configs exist with enforced tool restrictions (Bash(alphaswarm*) + Read(contracts/*) only)." The phrase "enforced tool restrictions" is ambiguous — it could mean prompt instructions, subagent_type config, or actual runtime blocking. Given D-1's claim that prompt restrictions count as enforcement, this criterion will be satisfied by writing better prompts without any runtime blocking. It's not disk-observable whether restrictions are "enforced."
**Why:** Exit criteria need to be verifiable by reading files or running commands, not by judgment calls about whether a config "enforces" something. A criterion like "delegate_guard_config.yaml exists with blocked_tools containing ['Read', 'Write', 'Bash'] and a whitelist for alphaswarm*" is disk-observable. "Enforced tool restrictions exist" is not.
**How:**
1. Rewrite exit criterion 1 to: "A `delegate_guard_config.yaml` file exists for evaluation sessions with: `blocked_tools: [Read, Write]`, `blocked_patterns: ['.py', 'from alphaswarm', 'import alphaswarm']`, and `allowed_reads: ['contracts/']`. The `delegate_guard.py` hook references this config and is registered in the evaluation session's hooks configuration."
2. Add a verification step: "Run a canary evaluation where an agent attempts `from alphaswarm_sol.kg import KnowledgeGraph` — the session log must show tool_use blocked with exit code 2, not a successful import."
**Impacts:** All plans must include a canary/smoke test that attempts the known bypass pattern and verifies it is blocked.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL

### P1-IMP-04: Assumption 2 Is Unverified and May Be False — JSONL Transcripts for Agent Teams Teammates
**Target:** CONTEXT
**What:** Assumption 2 states: "JSONL session transcripts are accessible after agent completion (stored by Claude Code)." The domain section notes: "Hooks may not capture all events for Agent Teams teammates (teammates run in separate processes)." If teammates run in separate processes with `isolation: "worktree"`, the write path is process-local unless explicitly shared. The parser specification depends entirely on what path the transcript lands at (if anywhere) in the teammate's worktree.
**Why:** The entire JSONL-parsing verification strategy (exit criterion 2) depends on JSONL being accessible per-teammate. If teammates produce separate JSONL streams that the orchestrator cannot read, the verification mechanism silently fails — no error, just a missing file. This is a silent failure mode, the most dangerous kind. This must be empirically confirmed before Plan 02 can specify a parser.
**How:**
1. Before planning any JSONL-based verification, add a prerequisite task: "Empirically verify JSONL transcript accessibility for Agent Teams teammates. Spawn one Agent Teams teammate with a known tool sequence (build-kg, then a deliberate Bash error), then attempt to locate and parse the resulting JSONL. If inaccessible, fall back to hook-based capture (obs_session_end.py) as primary verification source."
2. Rewrite Assumption 2 as conditional: "JSONL session transcripts may be accessible for the orchestrator session. For Agent Teams teammates (separate processes), transcript access is unverified. Plans must include a preflight check for transcript file existence before the JSONL parser step, and fall back to hook-based capture if absent."
**Impacts:** Exit criterion 2 depends entirely on JSONL access being confirmed. If it fails, the criterion needs a hook-based fallback path. Blocks all of Plan 02 until resolved.
**Research needed:** no (resolved: GAP-02)
**research_summary:** JSONL transcripts stored at `~/.claude/projects/{encoded-path}/{uuid}.jsonl` (user-level, always readable by orchestrator). SubagentStop hook provides direct `agent_transcript_path` field (v2.0.42+). Worktree isolation does not prevent access. Primary method: capture path via SubagentStop hook. Fallback: filesystem scan with timestamp filtering.
**Confidence:** HIGH
**Prior art:** 1
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL

### P1-IMP-05: Missing Assumption — delegate_guard.py Scope Is Session-Global, Not Per-Evaluation
**Target:** CONTEXT
**What:** delegate_guard.py enforces a static global config. Evaluations need per-session guard rules (stricter during eval, normal during dev). No safe session-scoping mechanism exists.
**Why:** Without scoping, either (a) guard is always strict and blocks normal dev work, or (b) guard is always permissive and provides no eval-time protection. The symlink swap approach fails silently if obs hooks are observation-only — the session proceeds unguarded with no error signal.
**How:**
1. Audit delegate_guard.py's config loading path — confirm whether it reads config at invocation time or at import time.
2. If invocation-time: add a `--config <path>` CLI flag so evaluation_runner.py can pass an eval-specific config explicitly. No symlinks needed.
3. If import-time: add a PreToolUse hook that checks an env var (`ALPHASWARM_EVAL_MODE=1`) and rejects any tool call if the guard is not loaded with the eval config.
4. Add an explicit check to evaluation_runner Stage 1 (preflight): verify the guard is loaded with the correct config before any agent is spawned. Fail-fast with a clear error.
5. Document the scoping mechanism in CONTEXT.md assumptions, replacing the symlink proposal.
**Impacts:** Plans implementing delegate_guard activation must use invocation-time config, not symlink swap.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3
**Prerequisite:** no
**Status:** reframed (Plan Completeness & Verification — symlink swap rejected: obs hooks are observation-only and cannot block/abort on failure; replaced by P1-ADV-2-01)
**Origin:** NOVEL
**Reframed by:** P1-ADV-2-01

### P1-IMP-06: Exit Criterion 5 Depends on 3.1c.1 Fixes That May Not Cover All Failure Modes
**Target:** CONTEXT
**What:** Exit criterion 5 states: "Retry of Plan 12 Batch 1 passes integrity check with VERDICT: PASS." Plan 12 Batch 1 had four distinct failure modes: (1) generic CLI queries returning 0 results, (2) shared graph state cross-contamination, (3) Python import fallback, (4) context leakage via Python module access. 3.1c.1 fixes items 1 and 2. This phase (3.1c.2) addresses item 3 via enforcement and item 4 partially. However, the exit criterion accepts a PASS verdict without specifying that all four failure modes must be independently verified as fixed.
**Why:** If the retry PASSES but item 4 slips through because `agent_execution_validator.py`'s 12 checks don't specifically test for successful Python imports, the phase declares success with a latent vulnerability. The "VERDICT: PASS" is only as reliable as the validator's coverage of the actual failure modes.
**How:**
1. Add a prerequisite sub-task: Before the Batch 1 retry, map each of the 4 failure modes to a specific check in `agent_execution_validator.py`. For any failure mode with no corresponding check, add it.
2. Rewrite exit criterion 5: "Retry of Plan 12 Batch 1 passes integrity check with VERDICT: PASS, AND the integrity report explicitly confirms: (a) no Bash tool calls containing 'import' or 'from alphaswarm', (b) all build-kg calls used --graph flag with hash-based path, (c) no reads of CLAUDE.md/.planning/docs/ by any agent, (d) all query results had non-zero result counts."
**Impacts:** Adds specificity to what "PASS" means; reduces risk of a false-pass verdict.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL

### P1-IMP-07: Simpler Alternative — delegate_guard.py Is Already the Solution; Phase May Be Over-Scoped
**Target:** CONTEXT
**What:** Both delegate_guard.py and agent_execution_validator.py exist as functional artifacts. The 6-plan table was written without auditing what these artifacts already cover. Plans that re-implement covered functionality waste implementation time and risk diverging from tested code.
**Why:** If the 12 validator checks already cover 3 of the 4 Batch 1 failure modes, Plan 02 scope shrinks. If delegate_guard already supports per-config invocation, Plan 01 scope shrinks. Unaudited plans risk producing 6 plans of work where 3-4 plans are the real scope.
**How:**
1. Before writing any plan file, perform a coverage audit with two outputs:
   a. For agent_execution_validator.py: list each of the 12 checks and map to Batch 1 failure mode (1-4) or "unrelated." Identify gaps — failure modes with no check.
   b. For delegate_guard.py: determine if config is read at invocation or import time (see P1-IMP-05 rewrite). Identify whether per-session scoping already exists.
2. Record audit results in CONTEXT.md Decisions section as D-AUDIT: coverage map.
3. Use the coverage map to collapse plans: any plan whose entire scope is already implemented in the audited artifacts should be struck from the table or merged.
4. Target: if audit shows >= 60% existing coverage, reduce 6 plans to 4 and document the reduction rationale in CONTEXT.md.
**Impacts:** Could reduce from 6 plans to 3-4, accelerating the Batch 1 retry.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL

### P1-IMP-08: Plan 01 Misidentifies Deliverable — Hook Config vs New Agent Types
**Target:** CONTEXT
**What:** Plan 01's deliverable is not "restricted agent types" or "prompt templates" but a concrete delegate_guard_config_eval.yaml with required content: `blocked_tools` covering non-CLI tools AND `blocked_patterns` covering Bash invocations that bypass tool blocking (specifically: `python`, `python3`, `import`, `cat contracts/`, `grep -r`).
**Why:** A config that blocks Read/Write but not Bash satisfies the file-existence check while leaving the Plan 12 failure vector (raw Python import via Bash) fully open. The deliverable spec must name both required sections to prevent partial configs from passing review.
**How:**
1. In CONTEXT.md, update Plan 01 scope to: "Produce `tests/workflow_harness/hooks/delegate_guard_config_eval.yaml` with: (a) `blocked_tools` list; (b) `blocked_patterns` list including at minimum `python`, `python3`, `import`, `cat contracts/`; (c) `allowed_reads` list scoped to `.vrs/observations/` only."
2. Add a verify step: load the YAML, confirm both `blocked_tools` and `blocked_patterns` keys exist and are non-empty.
3. Add a canary test: spawn a hooked subprocess, invoke `Bash(python -c "import os")`, assert exit code 2.
**Impacts:** Plan 01 redesign; Plan 06 (Batch 1 retry) depends on Plan 01 being correct.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL

### P1-IMP-09: Plan 02 Scope Ambiguity — NEW vs Integration Work Creates Duplication Risk
**Target:** CONTEXT
**What:** Plan 02 conflates new parsing work with coverage already in agent_execution_validator.py (12 checks). The real new work is distinguishing "tried CLI and failed" from "never tried CLI" — a distinction the validator cannot make from post-hoc checks alone. This requires parsing Bash tool-call events in JSONL transcripts.
**Why:** The distinction matters for root cause: "tried and failed" means the CLI interface is broken (IMP-02 territory, delegate_guard blocking); "never tried" means the agent chose Python imports from the start. Treating both as equivalent masks the fix required.
**How:**
1. Prerequisite: P1-IMP-04 must confirm JSONL transcript path for worktree-isolated teammates. If unresolvable, Plan 02 scope narrows to transcript-available sessions only.
2. Define CLIAttemptState enum: `ATTEMPTED_SUCCESS | ATTEMPTED_FAILED | NOT_ATTEMPTED | TRANSCRIPT_UNAVAILABLE`. The last state is the explicit fallback when JSONL is absent — do not collapse into NOT_ATTEMPTED.
3. Scope Plan 02 exclusively to: (a) JSONL Bash event extraction for CLIAttemptState, and (b) wiring CLIAttemptState into the existing validator as check 13. Explicitly exclude re-implementing the existing 12 checks.
4. Add a unit test: given a JSONL fixture with a Bash call to `alphaswarm` that exits non-zero, assert CLIAttemptState == ATTEMPTED_FAILED (not NOT_ATTEMPTED).
**Impacts:** Plan 02 scope narrows significantly; Plan 04 must reference CLIAttemptState. Blocked by P1-IMP-04 (JSONL access prerequisite).
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL

### P1-IMP-10: Plan 05 Re-Designs Already-Designed Protocol — Should Wire, Not Design
**Target:** CONTEXT
**What:** CONTEXT describes Plan 05 as "Agent debrief + integrity pipeline — Post-session structured interview with pre-debrief CLI validation." The domain section states the debrief protocol from 3.1c is a "4-layer strategy already designed — needs implementation and pipeline wiring." The plan description implies design work, but design is done.
**Why:** If a plan is written as "design X" when X is already designed, the implementer either re-designs (wasted effort, possible regression from parent phase decisions) or recognizes the mismatch and improvises scope — neither is reliable.
**How:**
1. Change Plan 05 scope to: "Wire 3.1c debrief protocol into evaluation_runner.py: (1) add Stage 9 to the 8-stage pipeline that runs pre-debrief CLI validation via agent_execution_validator, (2) issue SendMessage with canonical debrief prompt template to agent, (3) parse structured JSON response against schema, (4) write debrief artifact to `.vrs/observations/{session}/debrief.json`. Template and schema must match 4-layer strategy from 3.1c."
2. In the Output Contract table, change to: "Debrief pipeline stage | Stage 9 in evaluation_runner.py + canonical prompt template + JSON schema | Post-session analysis + baseline comparison."
**Impacts:** Plan 05 scope becomes implementation-only (no design); Plan 06 depends on Plan 05 producing Stage 9.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL

### P1-IMP-11: Output Contract Lists "Prompt Templates" as Primary Artifact — Wrong Enforcement Layer
**Target:** CONTEXT
**What:** CONTEXT Output Contract table lists "Evaluation-specific agent configs | Prompt templates with tool restrictions | Agent prompt files" as the first output. The domain section establishes that `delegate_guard.py` blocks at the PreToolUse level. Prompt templates are advisory; they do not block. The Plan 12 Batch 1 failure explicitly shows agents bypassed prompt-based restrictions.
**Why:** The Output Contract is the acceptance gate for the phase. If it lists prompt templates as the deliverable for isolation, Plan 06 will be accepted even if no hook config is deployed — the acceptance criterion will be satisfied by the wrong artifact.
**How:**
1. Replace the first Output Contract row with: "Evaluation delegate_guard config | YAML config (`delegate_guard_config_eval.yaml`) + activation script | `tests/workflow_harness/hooks/` | Evaluation runner (must activate before any session spawn in Plan 06)"
2. Add a Testing Gate required check: "Hook activation check: before Plan 06 session spawn, verify `delegate_guard_config_eval.yaml` is present and loaded by the hook; absence = automatic BLOCK."
**Impacts:** Plan 01 (must produce YAML config); Plan 06 (must activate hook); Testing Gate adds hook presence check.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL

### P1-IMP-12: Testing Gate Missing Observable Done Criterion for Snapshot Pre-Change ID
**Target:** CONTEXT
**What:** The Testing Gate states: "Per the Snapshot Protocol, a pre-modification snapshot must be used for acceptance validation." No task in any plan creates `.vrs/snapshots/3.1c.2/pre-change-id.txt`. If no plan owns this, the bootstrap exception is always void.
**Why:** A testing gate with an acceptance criterion that depends on a file no plan creates is a design trap. The implementer will either skip the snapshot, create it mid-execution (defeating its purpose), or block indefinitely.
**How:**
1. Add an explicit prerequisite step: "Pre-phase action: Run `alphaswarm snapshot create --label 3.1c.2-pre-change` and write the ID to `.vrs/snapshots/3.1c.2/pre-change-id.txt`. This must be the FIRST action before Plan 01 runs."
2. Add this as a required Testing Gate validator check.
3. Assign ownership: Plan 01 Task 1 creates this file, or it becomes a phase-level prerequisite.
**Impacts:** Plan 01 (new first task); Testing Gate (new validator check); Plan 06 acceptance (snapshot diff is verifiable).
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL

### P1-IMP-13: Plan 06 (Batch 1 Retry) Has No Explicit Failure Handling Path
**Target:** CONTEXT
**What:** Plan 06 describes "Re-run calibration with hardened harness, verify PASS." Plan 12 Batch 1 failed with 6 critical, 15 warning violations. Plan 06 has no defined behavior for partial failure, no acceptance thresholds, and no escalation path.
**Why:** A retry plan without defined success/failure thresholds is a plan that can be declared "done" when the implementer gets tired. "Verify PASS" without numeric thresholds creates the same failure mode as Batch 1: a partial success looks like a success.
**How:**
1. Expand Plan 06 scope: "Done criteria: (a) `agent_execution_validator.py` VERDICT: PASS with 0 critical violations (down from 6); (b) no Python import fallback (CLIAttemptState == ATTEMPTED_SUCCEEDED for all CLI calls); (c) at least 3 of 5 agents produce non-empty query results; (d) debrief Stage 9 completes for all agents. If any criterion fails, produce failure analysis at `.vrs/observations/plan12-retry/failure-analysis.md` and halt."
2. Plan 06 should distinguish new violations from pre-existing ones when evaluating against thresholds.
**Impacts:** Plan 06 done criteria become explicit; Testing Gate references specific metrics.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL

### P1-IMP-14: Plans Table Lacks Dependency Graph — Sequential Assumption Unverified
**Target:** CONTEXT
**What:** The Plans table lists 6 plans with no explicit dependency relationships. Several dependencies are non-obvious: Plan 04 depends on Plan 02 producing `CLIAttemptState`. Plan 06 depends on ALL of Plans 01-05. Plan 03 is independent of Plans 01-02 and could run in parallel.
**Why:** Out-of-order execution is a concrete failure mode: running Plan 06 before Plan 01 would repeat the exact Plan 12 Batch 1 failure. The external dependency on 3.1c.1 Plans 01-04 being merged (commit 06087cca) is also unstated in the plan table.
**How:**
1. Add a "Dependencies" column: Plan 01 depends_on [3.1c.1 Plans 01-03 MERGED]; Plan 02 depends_on [Plan 01]; Plan 03 depends_on [3.1c.1 Plan 04 MERGED]; Plan 04 depends_on [Plan 02, Plan 03]; Plan 05 depends_on [Plan 04]; Plan 06 depends_on [Plans 01-05].
2. Add before the Plans table: "All plans in this phase require 3.1c.1 Plans 01-04 MERGED (committed as 06087cca) as a hard prerequisite."
**Impacts:** All plans affected — execution ordering becomes explicit; reduces risk of Plan 06 running unprotected.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL

### P1-ADV-2-01: Session-Scoped Guard Config via Invocation-Time Parameter
**Target:** CONTEXT
**What:** Evaluation sessions need per-session delegate_guard config that is stricter than dev sessions. The symlink swap approach (rejected in P1-IMP-05) fails silently because obs hooks are observation-only. The correct mechanism is either invocation-time config path passing or env-var gating.
**Why:** Without a fail-safe scoping mechanism, the guard is either always strict (blocks dev) or always permissive (no eval protection). The symlink approach provides no error signal on failure — the session proceeds unguarded believing it is protected, which is worse than no scoping at all.
**How:**
1. Audit delegate_guard.py's config loading path — confirm whether it reads config at invocation time or at import time.
2. If invocation-time: add a `--config <path>` CLI flag so evaluation_runner.py can pass an eval-specific config explicitly. No symlinks needed.
3. If import-time: add a PreToolUse hook that checks an env var (`ALPHASWARM_EVAL_MODE=1`) and rejects any tool call if the guard is not loaded with the eval config.
4. Add an explicit check to evaluation_runner Stage 1 (preflight): verify the guard is loaded with the correct config before any agent is spawned. Fail-fast with a clear error.
5. Document the scoping mechanism in CONTEXT.md assumptions, replacing the symlink proposal.
**Impacts:** Plans implementing delegate_guard activation must use invocation-time config, not symlink swap. evaluation_runner.py preflight must verify config before spawning.
**Research needed:** no (resolved: GAP-03)
**research_summary:** Config read at INVOCATION time (per PreToolUse call, no caching). Each hook invocation is a fresh process. Hooks propagate to Agent Teams via project-level config sharing (v2.1.63). Recommended: env-var gating (`ALPHASWARM_EVAL_MODE=1`) + env-var config path override (`DELEGATE_GUARD_CONFIG=/path/to/eval.yaml`). No symlinks needed.
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Status:** implemented
**Origin:** ADVERSARIAL — created by Plan Completeness & Verification lens as REFRAME replacement for P1-IMP-05 (symlink swap rejected; obs hooks cannot block)
**Replaces:** P1-IMP-05

## Post-Review Synthesis

**Items created:** P1-SYN-01, P1-SYN-02, P1-SYN-03, P1-CSC-01, P1-CSC-02, P1-CSC-03, P1-CSC-04
**Key insight:** Two systemic defects run through CONTEXT.md at every layer: (1) the enforcement mechanism is documented at the wrong abstraction layer (prompt/subagent_type instead of hook/config) across Assumptions, Decisions, Plans, and Output Contract simultaneously, and (2) all success conditions are defined in terms of internal states that cannot be externally observed, making the phase unverifiable by design.

### P1-SYN-01: Wrong Enforcement Layer Documented at Four CONTEXT Locations
**Target:** CONTEXT
**What:** The same incorrect abstraction — "subagent_type and prompt restrictions enforce tool access" — appears in four distinct CONTEXT.md sections simultaneously: Assumption 1, Decision D-1, Plans table row 01, and Output Contract row 1. IMP-01, IMP-08, and IMP-11 each correct one location but no item corrects all four. If three locations are fixed but one remains, future planners will re-derive the wrong assumption from the uncorrected location.
**Why:** A self-contradicting CONTEXT (three locations corrected, one not) is worse than a uniformly wrong one — it creates ambiguity about which statement is authoritative. The fix must be atomic across all four locations.
**How:** 1. Cite all four locations: Assumption 1 (CONTEXT.md line ~X), Decision D-1 (CONTEXT.md line ~Y), Plans table row 01 (CONTEXT.md line ~Z), Output Contract row 1 (CONTEXT.md line ~W). 2. Rewrite all four atomically to reference delegate_guard.py PreToolUse hook with blocked_tools + blocked_patterns. 3. Provide verbatim replacement text for each location showing post-fix state.
**Impacts:** PLAN-01, PLAN-06
**Components:** P1-IMP-01, P1-IMP-08, P1-IMP-11
**depends_on_plans:** P1-IMP-01, P1-IMP-08
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cross-cutting)
**Origin:** genuine

### P1-SYN-02: Systemic Unverifiability — All Success Conditions Defined as Internal States
**Target:** CONTEXT
**What:** Three items (IMP-03, IMP-06, IMP-13) each found a different exit criterion is unobservable. This is not three editorial errors — it is a structural pattern. Every success condition uses internal-state language.
**Why:** A phase where no exit criterion is independently verifiable cannot be reviewed or audited. The entire exit criteria section needs a consistent observable standard.
**How:** 1. Audit all 5 current exit criteria with observability status (observable/unobservable). 2. For each unobservable criterion, map to a proposed disk-observable artifact (file path + key/value) AND/OR behavior-observable signal (command + expected output/exit code). 3. Rewrite all five exit criteria in CONTEXT.md Testing Gate section against this standard. 4. Add the verification standard as a footnote in the Testing Gate section of CONTEXT.md.
**Impacts:** PLAN-01, PLAN-02, PLAN-03, PLAN-04, PLAN-05, PLAN-06
**Components:** P1-IMP-03, P1-IMP-06, P1-IMP-13
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cross-cutting)
**Origin:** genuine

### P1-SYN-03: Dependency Blindness at Two Granularities — Inter-Plan and Intra-Plan
**Target:** CONTEXT
**What:** IMP-14 found no inter-plan dependency graph. IMP-09 found Plan 02's CLIAttemptState is blocked by IMP-04's JSONL access prerequisite (intra-plan). Together: dependency blindness at both levels. A planner reading only the table will attempt Plan 02 before JSONL access is confirmed.
**Why:** Fixing only table-level (IMP-14) leaves intra-plan dependency invisible. Fixing only intra-plan (IMP-09) leaves inter-plan ordering undocumented. The two must be coordinated.
**How:** 1. Add dependency graph as a markdown table in CONTEXT.md Plans section with columns: Plan, depends_on, wave. 2. In CONTEXT.md Plan 02 scope, add "Task 0: Confirm JSONL transcript accessibility — shell command to locate transcript file after teammate completion, fail-fast if absent." Task 0 confirmation = file existence check at expected path, not a code review. 3. In CONTEXT.md Plan 01 scope, add "Task 1: Create `.vrs/snapshots/3.1c.2/pre-change-id.txt`" (per IMP-12). 4. Define artifact format for pre-change-id.txt: single line containing snapshot hash from `alphaswarm snapshot create`.
**Impacts:** PLAN-01, PLAN-02, PLAN-04, PLAN-06
**Components:** P1-IMP-14, P1-IMP-09
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cross-cutting)
**Origin:** genuine

### P1-CSC-01: D-1 Correction Not Propagated After IMP-01 Fix
**Target:** CONTEXT
**What:** IMP-01 corrects Assumption 1 but D-1 still reads "subagent_type determines tool access." The more authoritative document (Decisions) contradicts the corrected assumption.
**How:** After IMP-01, update D-1 in CONTEXT.md Decisions section. Old text: "D-1: Use prompt-enforced tool restrictions for evaluation agents." New text: "D-1: Use delegate_guard.py PreToolUse hook with delegate_guard_config_eval.yaml for evaluation enforcement. Prompt restrictions are advisory only — hook-level blocking is the enforcement primitive." Add cross-reference: "See Assumption 1 (corrected) and P1-IMP-08 (Plan 01 deliverable)."
**Trigger:** P1-IMP-01
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cascade)

### P1-CSC-02: Output Contract Row 1 Mismatches After IMP-08 Implementation
**Target:** CONTEXT
**What:** IMP-08 changes Plan 01 deliverable to YAML config, but Output Contract row 1 still says "Prompt templates." Phase acceptance check references non-existent artifact type.
**How:** After IMP-08, update Output Contract table in CONTEXT.md. Old row 1: "Evaluation-specific agent configs | Prompt templates with tool restrictions | Agent prompt files". New row 1: "Evaluation delegate_guard config | delegate_guard_config_eval.yaml + hook activation script | tests/workflow_harness/hooks/". Update Testing Gate acceptance: add check "delegate_guard_config_eval.yaml exists AND is loaded by hook before any session spawn."
**Trigger:** P1-IMP-08
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cascade)

### P1-CSC-03: Failure Mode Map Becomes Stale When Check 13 Added by IMP-09
**Target:** PLAN-02
**What:** IMP-06 maps 4 failure modes to 12 checks. IMP-09 adds check 13 (CLIAttemptState). After IMP-09, the 12-check map is stale — check 13 may cover a failure mode not in the taxonomy.
**How:** After IMP-09, extend the failure mode map (in CONTEXT.md exit criterion 5 or Plan 02 scope) to include check 13. CLIAttemptState maps to failure mode 3 (Python import fallback): ATTEMPTED_SUCCESS = pass, ATTEMPTED_FAILED = CLI broken (failure mode 1), NOT_ATTEMPTED = Python import (failure mode 3), TRANSCRIPT_UNAVAILABLE = degrade gracefully. The CLIAttemptState enum would be defined in the JSONL parser module (Plan 02 scope). Check 13 is a NEW failure mode check, not a duplicate of existing checks 1-12.
**Trigger:** P1-IMP-09
**Research needed:** no
**Confidence:** MEDIUM
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cascade)

### P1-CSC-04: Testing Gate References 6-Plan Structure — Breaks If IMP-07 Reduces to 4
**Target:** CONTEXT
**What:** Testing Gate references Plans 01-06 by position. If IMP-07 reduces to 4 plans, acceptance check references Plans 05/06 that no longer exist.
**How:** This is a conditional cascade: IF P1-IMP-07 is confirmed/enhanced AND reduces plan count, THEN atomically update Testing Gate section in CONTEXT.md with new plan numbers and acceptance criteria. Constraint: plan count reduction MUST be accompanied by Testing Gate update. If P1-IMP-07 is rejected (plans stay at 6), this item is NOT NEEDED.
**Trigger:** P1-IMP-07
**depends_on_plans:** P1-IMP-07
**Research needed:** no
**Confidence:** MEDIUM
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cascade)

## Auto-Fixes Applied

- P1-IMP-04: `prerequisite: yes` → `prerequisite: no` (target is CONTEXT — text can always be written once research completes; status: prerequisite reflects blocking nature for downstream plans)
- P1-IMP-10: `prerequisite: yes` → `prerequisite: no` (target is CONTEXT — 3.1c debrief protocol design is accessible per domain section)
- P1-IMP-13: `prerequisite: yes` → `prerequisite: no` (target is CONTEXT — Plans 01-05 dependency is a planning constraint, not a code prerequisite)

## Convergence

Pass 1: 0% cosmetic (0/22)
Structural: 22 | Cosmetic: 0
Threshold: 80% (novelty: default)
Signal: ACTIVE
