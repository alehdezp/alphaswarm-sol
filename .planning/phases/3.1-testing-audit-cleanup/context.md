# Phase 3.1: Testing Audit & Cleanup

## Planning Status

- This phase is a **planning draft** and has not been fully implemented/tested yet.
- Commands and checks below are target-state contracts for implementation, not evidence of completion.
- Execution split is intentional:
  - Shipping/runtime uses Claude Code workflows with `/vrs-*` skills + subagent/task orchestration.
  - Testing/harness uses Claude Code Agent Teams features (`TeamCreate`, `SendMessage`) via `claude-code-controller`.

## Goal

Remove dead testing infrastructure, enforce testing rules automatically, and prepare the infrastructure foundation for Phase 3.1c's evaluation framework — so Phase 3.1b (Workflow Testing Harness), Phase 3.1c (Agentic Testing Evaluation), Phase 3.2 (First Working Audit), and Phase 4 (Agent Teams Debate) build on clean foundations with a shipping manifest, evaluator audit, and evaluation contract schema ready for downstream consumption.

## What Prompted This

Exploration (3 parallel agents) of `src/alphaswarm_sol/testing/` revealed:

- **~31K LOC across 82 Python files** — massive module with significant dead code
- **Only 8 symbols consumed by CLI** (`cli/main.py:820`): `TestTier`, `generate_with_fallback`, `detect_project_structure`, `write_scaffold_to_file`, `batch_generate_with_quality`, `QualityTracker`, `TIER_DEFINITIONS`, `format_tier_summary`
- **`__init__.py` re-export problem**: 456 lines re-exporting ~150 symbols — creates false "callers" for any import analysis tool (everything appears imported because `__init__.py` imports everything)
- **7 runner implementations**: 5 dead/broken, 2 mature (WorkflowEvaluator 554 LOC, TrajectoryEvaluator 241 LOC)
- **Legacy infrastructure already mostly clean**: zero tmux in production code, clean registry/policies
- **Rules docs have 152 `claude-code-controller` references** — need Agent Teams rewrite
- **`tests/workflow_harness/`** (12 files) already exists with assertions, transcript parsing
- **Pattern-tester agent** is 843 lines, comprehensive — rewrite deferred to 3.1c-09 where evaluation pipeline lives

## Architecture Context

**Claude Code IS the orchestrator for this testing phase.** Team-based controls below are test-harness behavior, not a replacement for shipping `/vrs-*` runtime workflows.
- Claude Code creates teams via `TeamCreate`, spawns teammates, assigns tasks
- `claude-code-controller` (npm) provides programmatic trigger from pytest for workflow tests
- Hook-based enforcement: `PreToolUse` (command hooks for safety), `PostToolUse` (agent hooks for quality gates)
- Agent Teams hooks: `TeammateIdle`, `TaskCompleted`, `SubagentStart/Stop`, `Stop`
- Rules enforcement targets Agent Teams patterns, NOT Python SDK hooks

## Cross-Phase Invariants

These invariants apply to ALL plans (3.1-01 through 3.1-07):

1. **100%/100% Rule**: Any metric reported as 100% precision AND 100% recall triggers mandatory fabrication investigation.
2. **Fail-Closed Default**: Every enforcement mechanism defaults to BLOCK; allow requires evidence.
3. **Real Contracts Only**: Detection tests use `load_graph()` on real `.sol` files from `tests/contracts/`, never `MagicMock()` for graph internals.
4. **Duration Bounds**: Pipeline tests must take > 5 seconds; < 1 second indicates mock bypass. Enforced by `MIN_DURATION_MS` in `src/alphaswarm_sol/testing/evidence_pack.py`.

## Phase-Wide Strict Validation Contract (Mandatory)

No 3.1 plan can be marked complete unless all three artifacts exist for that plan ID:

1. **Machine Gate Report**: `.vrs/debug/phase-3.1/gates/<plan-id>.json`
2. **Human Checkpoint Record**: `.vrs/debug/phase-3.1/hitl/<plan-id>.md`
3. **Drift Log**: `.vrs/debug/phase-3.1/drift-log.jsonl` (append-only; at least one entry when deviation occurs)

Required machine gate fields:
- `plan_id`, `commands_executed[]`, `assertions[]`, `status`, `started_at`, `ended_at`, `duration_ms`
- `artifacts[]` with file hashes for reproducibility

Required human checkpoint fields:
- `scenario_id`, `reviewer`, `steps_executed[]`, `observed_result`, `expected_result`, `decision`
- `repeatability_rating` (`fast-repeatable` / `repeatable-with-notes` / `not-repeatable`)

## `/gsd-plan-phase` Dynamic Check Contract

For each `3.1-xx` plan, `/gsd-plan-phase` must generate research-backed checks (not static expected outcomes):

1. `.vrs/debug/phase-3.1/plan-phase/derived-checks/<plan-id>.yaml`
2. `.vrs/debug/phase-3.1/plan-phase/research/<plan-id>.md`
3. `.vrs/debug/phase-3.1/plan-phase/hitl-runbooks/<scenario-id>.md`

Required governance references:
- `.planning/testing/PLAN-PHASE-GOVERNANCE.md`
- `.planning/testing/schemas/phase_plan_contract.schema.json`
- `.planning/testing/templates/PLAN-INVESTIGATION-CHECKS-TEMPLATE.yaml`
- `.planning/testing/templates/HITL-RUNBOOK-TEMPLATE.md`
- `.planning/testing/templates/DRIFT-RCA-TEMPLATE.md`

Rule: checks must be derived from measured baseline, external reference, or explicit human decision path. No prefilled pass/fail targets without derivation evidence.

## Plan Preconditions (Resolve During `/gsd-plan-phase`)

| Plan | Preconditions to Resolve | Derivation Requirement |
|---|---|---|
| 3.1-01 | Import graph excluding `__init__.py` re-exports; symbol-level caller analysis for all `src/alphaswarm_sol/testing/**` modules | AST scan that skips `__init__.py` barrel imports; trace actual call sites in CLI and tests |
| 3.1-02 | Legacy marker inventory across `src/`, `configs/`, and skill/registry files | Baseline from grep + registry load checks; derive removal scope from findings |
| 3.1-03 | Shipped skill/agent filesystem inventory, WorkflowEvaluator/TrajectoryEvaluator API stability, workflow_harness readiness, settings.json hook state | Scan `src/alphaswarm_sol/shipping/skills/` and `agents/`, audit evaluator public APIs, review harness test results (91 passed), inspect settings.json for orphaned hooks |
| 3.1-04 | Current canonical testing rules and enforcement ownership map | Build category-to-enforcement map from actual rule docs and existing validators |
| 3.1-05 | Existing `tests/workflow_harness/lib/assertions.py` API (241 LOC, 7 categories), 3.1c-06 evaluation contract needs, stable rule IDs from 3.1-04 | Review assertions.py extension points, derive schema fields from 3.1c-06 plan requirements, verify rule IDs from 3.1-04 are available |
| 3.1-06 | Test-file-to-module dependency map for removed/kept infrastructure | Derive safe deletions from module liveness and coverage impact |
| 3.1-07 | Composite gate command matrix and artifact dependencies | Derive final gate list from outputs of 3.1-01..06; no static checklist reuse |

## Human-In-The-Loop Scenarios (Fast + Repeatable)

Each plan has one mandatory human checkpoint scenario designed for <= 10 minutes:

| Plan | Scenario ID | Human Steps (must be explicit and repeatable) | Pass Condition |
|---|---|---|---|
| 3.1-01 | `HITL-3.1-01-import-graph` | Review top 10 deleted paths vs import graph categories; run one CLI smoke command | No deleted file appears in `PRODUCTION_DEPENDENT`; CLI still works |
| 3.1-02 | `HITL-3.1-02-legacy-sweep` | Inspect grep sweep output and registry diff; spot-check 3 removed legacy references | Zero production legacy markers; registries load |
| 3.1-03 | `HITL-3.1-03-manifest-audit` | Verify MANIFEST.yaml skill count matches `ls shipping/skills/*.md`; review evaluator audit for completeness; inspect one sample capability contract | Counts match; audit documents API signatures; sample contract has >= 3 capability checks |
| 3.1-04 | `HITL-3.1-04-rules-map` | Review rule-to-enforcement mapping table and 3 sample merged rules | Every rule category maps to one enforcement mechanism |
| 3.1-05 | `HITL-3.1-05-eval-contracts` | Validate 3 sample evaluation contracts against schema; run assertion helpers with one passing and one failing result | Valid contracts pass schema; assertion catches invalid result; existing 7 assertion categories still work |
| 3.1-06 | `HITL-3.1-06-test-cleanup` | Review deleted test files against removed modules list | No living-module tests were deleted |
| 3.1-07 | `HITL-3.1-07-composite-gate` | Confirm 7/7 final checks from verification report | All checks pass and are timestamped |

## Exploration Findings Summary

These findings come from 3 parallel exploration agents and inform all plans below.

### Module Scale
- `src/alphaswarm_sol/testing/` has **~31K LOC across 82 Python files**
- `__init__.py` alone is 456 lines re-exporting ~150 symbols
- Only **8 functions/classes** consumed by the CLI (`cli/main.py:820`)

### Runner Inventory (7 found, decisions below)

| Runner | LOC | Decision | Rationale |
|---|---|---|---|
| MasterOrchestrator | 378 | DELETE | Zero external callers |
| AgenticRunner | 45 | DELETE | Stub, zero external callers |
| FullTestingOrchestrator | 1,038 | DELETE | Zero external callers, broken |
| SupervisionLoop | 227 | DELETE | Zero external callers |
| SelfImprovingRunner | 474 | DELETE | Zero external callers |
| WorkflowEvaluator | 554 | KEEP | Mature, used by 3.1c agentic evaluation |
| TrajectoryEvaluator | 241 | KEEP | Research metrics needed for 3.1c |

### Dead Subdirectories (~9K LOC)

| Directory | LOC | Status |
|---|---|---|
| `flexible/` | 2,839 | DELETE — Jujutsu workspace migration, zero production callers |
| `corpus/` | 2,234 | DELETE — Dead test corpus infrastructure |
| `e2e/` | ~1,500 | DELETE — Dead E2E infrastructure |
| `integration/` | 1,256 | DELETE — Zero production callers |
| `unit/` | 1,014 | DELETE — Zero production callers |
| `evolution/` | ~500 | DELETE — Evolution engine, zero callers |
| `chaos/` | ~400 | DELETE — Chaos layer, zero callers |
| `benchmarks/` | 374 | DELETE — Zero production callers |

### Dead Standalone Files (~4K LOC)

| File | LOC | Status |
|---|---|---|
| `full_testing_orchestrator.py` | 1,038 | DELETE |
| `full_testing_schema.py` | 721 | DELETE |
| `failure_catalog.py` | ~750 | DELETE |
| `evidence_pack.py` | ~800 | DELETE |
| `proof_tokens.py` | ~650 | DELETE |
| `ranking.py` | 501 | DELETE |
| `gaps.py` | 388 | DELETE |
| `fix_retest_loop.py` | 320 | DELETE |
| `state_persistence.py` | 304 | DELETE |
| `wave_gate.py` | 294 | DELETE |
| `blind_sandbox.py` | 268 | DELETE |
| `anti_lazy.py` | 167 | DELETE |
| `agent_teams_harness.py` | stub | DELETE |

### Keep (Production-Dependent)

These files are imported by CLI or have active callers:
- `tiers.py`, `detection.py`, `remappings.py`, `pragma.py`, `generator.py`, `quality.py`, `verification.py` (CLI consumers)
- `runner.py`, `metrics.py`, `mutations.py`, `tier_c_harness.py`, `debug_mode.py`, `debug_artifacts.py`, `self_improving_loop.py`
- `workflow/workflow_evaluator.py`, `workflow/improvement_loop.py`, `trajectory/evaluator.py`, `scenarios/`

### Verify Before Deciding

- `harness/` (1,789 LOC) — `ClaudeCodeRunner` may have CLI callers; verify during plan 01 import graph

### Legacy Infrastructure Status

- Zero tmux references in production code (already clean)
- Clean registry and policy files
- 152 `claude-code-controller` references in rules docs (rewrite needed in plan 04)
- `tests/workflow_harness/` (12 files) already exists with assertions, transcript parsing

### Existing Evaluator Infrastructure Maturity

These mature components exist but are not yet "blessed" for 3.1b/3.1c use — 3.1-03 audits them:

| Component | LOC | Status | 3.1c Role |
|---|---|---|---|
| `WorkflowEvaluator` | 553 | Mature, stable API | Core evaluation pipeline in 3.1c-08 |
| `TrajectoryEvaluator` | 240 | 8 quality dimensions | Reasoning quality scoring in 3.1c-07 |
| `tests/workflow_harness/` | 12 files | 91 tests passing | Infrastructure foundation for 3.1b |
| `tests/workflow_harness/lib/assertions.py` | 241 | 7 assertion categories | Extended in 3.1-05 for evaluation contracts |

**Key gap:** None of these components have formal API stability contracts or documented input/output types for downstream consumption. 3.1-03 creates this documentation so 3.1b/3.1c can build on stable foundations rather than discovering API shapes mid-execution.

## Plans (7)

### 3.1-01: Import Graph Analysis + Delete Dead Testing Code

**MANDATORY FIRST STEP: Symbol-level import graph analysis before deleting anything.**

#### The `__init__.py` Re-Export Problem

`src/alphaswarm_sol/testing/__init__.py` is 456 lines that re-export ~150 symbols. Any naive import analysis (grep, pyright references) will show every symbol as "imported by `__init__.py`" — creating false liveness signals. The import graph MUST:

1. **Exclude `__init__.py` barrel imports** from caller counts
2. **Trace actual call sites** in `cli/main.py`, `tests/`, and other `src/` modules
3. **Use symbol-level tracking**, not just file-level (a file may export 10 symbols but only 1 is actually used)

#### Step 1: Build import graph (excluding `__init__.py` re-exports)
```bash
# Symbol-level analysis: for each exported symbol, find actual callers
# Skip __init__.py barrel imports — they create false positives
python -c "import ast; ..." # or use pyright find-references per symbol
```

#### Step 2: Categorize each file
| Category | Meaning | Action |
|---|---|---|
| TRULY_DEAD | Zero callers anywhere (excluding `__init__.py` re-exports) | SAFE TO DELETE |
| TEST_ONLY | Called only by `tests/` files | DELETE if tests also being deleted |
| PRODUCTION_DEPENDENT | Called by `cli/main.py` or other `src/` modules | KEEP |
| TRANSITIVE | Only called by other testing modules | Analyze callers recursively |

#### Step 3: Delete dead code using exploration findings

**Known safe deletions (from exploration — 5 dead runners + dead subdirectories + dead standalone files):**

Dead runners (~2,162 LOC):
| File | LOC | Status |
|---|---|---|
| `master_orchestrator.py` | 378 | DELETE — zero external callers |
| `agentic_runner.py` | 45 | DELETE — stub |
| `full_testing_orchestrator.py` | 1,038 | DELETE — zero external callers, broken |
| `supervision_loop.py` | 227 | DELETE — zero external callers |
| `workflow/self_improving_runner.py` | 474 | DELETE — zero external callers |

Dead subdirectories (~9K LOC): `flexible/`, `corpus/`, `e2e/`, `integration/`, `unit/`, `evolution/`, `chaos/`, `benchmarks/` (see Exploration Findings above for per-directory LOC).

Dead standalone files (~4K LOC): `full_testing_schema.py`, `failure_catalog.py`, `evidence_pack.py`, `proof_tokens.py`, `ranking.py`, `gaps.py`, `fix_retest_loop.py`, `state_persistence.py`, `wave_gate.py`, `blind_sandbox.py`, `anti_lazy.py`, `agent_teams_harness.py` (see Exploration Findings above for per-file LOC).

Keep (mature runners for 3.1c): `workflow/workflow_evaluator.py` (554 LOC), `trajectory/evaluator.py` (241 LOC).

**Requires verification during import graph step:**
| Directory/File | LOC | Concern |
|---|---|---|
| `harness/` (4 files) | 1,789 | `ClaudeCodeRunner` — verify no CLI callers |

#### Step 4: Rewrite `__init__.py`

After deletion, rewrite `testing/__init__.py` to export ONLY the 8 CLI-consumed symbols plus any symbols with verified live callers. Target: ~20-30 lines replacing the current 456-line barrel export.

After: Run `pytest tests/` to confirm nothing breaks.

**Exit gate:** `pytest tests/ -x` passes. No import errors. Import graph analysis artifact saved to `.vrs/debug/phase-3.1/import-graph.json`. `__init__.py` exports only symbols with verified callers.

**Estimated scope:** ~15K LOC deleted (9K subdirectories + 4K standalone files + 2K runners).

#### Reasoning

Dead code creates false confidence in the testing infrastructure's maturity. The `__init__.py` re-export problem means naive analysis will show everything as "live" — the import graph must use symbol-level tracking that excludes barrel imports. The runner cleanup decisions (5 delete, 2 keep) are based on exploration finding zero external callers for the deleted runners and confirmed maturity for the kept ones. This directly serves the 6.0 "prove everything" philosophy.

#### Expected Outputs

- **Created:** `.vrs/debug/phase-3.1/import-graph.json` — symbol-level import analysis excluding `__init__.py` re-exports
- **Deleted:** ~15K LOC of dead code (runners, subdirectories, standalone files)
- **Rewritten:** `src/alphaswarm_sol/testing/__init__.py` (456 lines -> ~20-30 lines)
- **Metric:** LOC count drops by verified amount (based on import graph, not estimate)
- **State:** `testing/` contains only live, imported modules; `__init__.py` exports only verified symbols

#### Testing Strategy

| Output | Verification Method 1 | Verification Method 2 |
|---|---|---|
| Import graph created (symbol-level) | `.vrs/debug/phase-3.1/import-graph.json` exists with per-symbol caller lists | `__init__.py` re-exports excluded from caller counts |
| Only TRULY_DEAD files deleted | Every deleted file has zero callers in import graph (excluding `__init__.py`) | `grep -r "from alphaswarm_sol.testing.flexible" src/` returns 0 hits |
| `__init__.py` rewritten (not just trimmed) | New `__init__.py` < 50 lines | Exports match the 8 CLI-consumed symbols + verified live callers |
| No live code removed | Every remaining module has at least one real caller | `pytest tests/ -n auto --dist loadfile` passes, test count unchanged for living-code tests |
| CLI still works | `uv run alphaswarm --help` succeeds | `uv run alphaswarm build-kg tests/contracts/SimpleToken.sol` completes |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|---|---|---|
| Import graph analysis runs BEFORE any deletion | Files deleted without import-graph.json artifact existing | Gate: import-graph.json must exist and be non-empty before any `git rm` |
| `__init__.py` re-exports excluded from caller counts | Import graph shows ~150 callers for every symbol (all from `__init__.py`) | Graph must distinguish barrel-import callers from real callers |
| Only files classified as TRULY_DEAD are deleted | Agent deletes files classified as PRODUCTION_DEPENDENT | Diff review: every deleted path must be TRULY_DEAD in import-graph.json |
| `__init__.py` is rewritten, not just left broken | Exports reference deleted modules, causing lazy import errors | `python -c "from alphaswarm_sol.testing import *"` must not raise |

### 3.1-02: Delete Legacy Testing Infrastructure Files

Delete remaining legacy testing infrastructure files. Exploration confirmed this is already mostly clean — zero tmux in production code, clean registry/policies. This plan handles the remaining references.

**Actions:**
1. Delete any remaining legacy Python files in `src/alphaswarm_sol/testing/workflow/` that reference superseded execution models (post-3.1-01 cleanup)
2. Delete associated legacy skill `.md` files and agent `.md` files
3. Update `testing/workflow/__init__.py` to remove exports of deleted modules
4. Update `configs/skill_tool_policies.yaml` to remove any remaining legacy enforcement fields
5. Update `src/alphaswarm_sol/skills/registry.yaml` to remove any legacy entries
6. Archive removed configs to `.planning/archive/testing-rules/legacy/`

**Exploration context:** Most legacy infrastructure was already removed in prior phases. This plan is minimal — confirm the sweep is complete and handle any stragglers found during 3.1-01 import graph analysis.

**Exit gate:** `grep -ri "legacy-infra-marker" src/alphaswarm_sol/` returns zero production hits (allow only in archive/planning). Skills load without errors.

**Estimated scope:** ~500 LOC (mostly config/registry cleanup, minimal Python deletion after 3.1-01).

#### Reasoning

Target end-state for Phase 3 is Agent Teams (Claude Code native) + `claude-code-controller` (npm v0.6.1) for test execution. Exploration confirmed most legacy code is already gone, but config files and registries may still reference deleted entries. This must follow 3.1-01 because the import graph may reveal additional legacy files that overlap with dead code.

#### Expected Outputs

- **Deleted:** Any remaining legacy Python files, associated skill and agent `.md` files
- **Modified:** `testing/workflow/__init__.py`, `configs/skill_tool_policies.yaml`, `src/alphaswarm_sol/skills/registry.yaml`
- **Archived:** Removed configs to `.planning/archive/testing-rules/legacy/`
- **Metric:** `grep -ri "legacy-infra-marker" src/alphaswarm_sol/` hit count drops to 0
- **State:** Skill registry loads without referencing deleted skills; config files contain no legacy enforcement fields

#### Testing Strategy

| Output | Verification Method 1 | Verification Method 2 |
|---|---|---|
| Zero legacy references in testing | `grep -ri "legacy-infra-marker" src/alphaswarm_sol/testing/` returns 0 hits | `grep -ri "legacy-infra-marker" src/alphaswarm_sol/skills/registry.yaml` returns 0 hits |
| Skills load cleanly | `python -c "from alphaswarm_sol.skills import registry; registry.load()"` succeeds (or equivalent import check) | `uv run alphaswarm tools status` does not error on missing skills |
| Config consistency | `grep -i "legacy_enforcement" configs/skill_tool_policies.yaml` returns 0 hits | JSON/YAML schema validation on `configs/skill_tool_policies.yaml` passes |
| Workflow module still importable | `python -c "import alphaswarm_sol.testing.workflow"` succeeds | `pytest tests/ -x` passes (no import cascade failures) |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|---|---|---|
| All legacy Python files deleted from `testing/` | Files deleted but legacy string literals remain in other files | `grep -ri "legacy-infra-marker" src/alphaswarm_sol/` must return 0 production hits |
| Config files updated, not just legacy files deleted | `registry.yaml` still lists deleted skills; `skill_tool_policies.yaml` still has legacy fields | Schema validation on registry + policy configs; load test must pass |
| `workflow/__init__.py` rewritten, not emptied | `__init__.py` becomes empty or still exports deleted modules | Import check: module must export only existing symbols |

### 3.1-03: Shipping Manifest + Infrastructure Audit for 3.1c

**Purpose:** Create the authoritative inventory that 3.1c-09 (skill tests) and 3.1c-10 (agent tests) need, and audit existing evaluator infrastructure for 3.1c readiness.

**Why this replaces the pattern-tester rewrite:** The pattern-tester rewrite moves to 3.1c-09 where the evaluation pipeline that consumes its output actually lives. The existing 843-line pattern-tester agent continues to work as-is for development use — it just isn't a 3.1 deliverable anymore.

#### Actions

1. **Create `src/alphaswarm_sol/shipping/MANIFEST.yaml`** — enumerate all 30 shipped skills and 21 shipped agents with: `id`, `name`, `path`, `category`, `tier` (core/support/experimental), `model_tier`
2. **Audit `WorkflowEvaluator` (553 LOC)** — verify API is stable, document input/output contract for 3.1c evaluation pipeline, note any gaps (e.g., no evaluation-contract-aware mode)
3. **Audit `TrajectoryEvaluator` (240 LOC)** — verify 8 quality dimensions are extensible, document where LLM-graded reasoning replaces keyword heuristics in 3.1c
4. **Audit `tests/workflow_harness/` (12 files)** — verify assertions library, transcript parser, controller events, workspace manager are ready for 3.1b to build on
5. **Clean `.claude/settings.json`** — remove orphaned hook config from prior phases, ensure clean slate for 3.1b-03 hook registration
6. **Create 2-3 sample capability contracts** at `tests/workflow_harness/contracts/samples/` showing the schema 3.1c-09 will use for all 30 skills

**Exit gate:** MANIFEST.yaml exists with correct counts (30 skills, 21 agents verified against filesystem). Evaluator audit docs created. workflow_harness blessed with known gaps documented. settings.json hook config is clean. Sample capability contracts validate against a basic JSON schema.

**Estimated scope:** ~200 lines YAML manifest + ~100 lines audit notes + 2-3 sample contract files (~50 lines each)

#### Reasoning

3.1c-09 and 3.1c-10 each need the full skill/agent inventory. Without a manifest, every 3.1c plan must re-derive it by scanning the filesystem — wasted effort and drift risk. The evaluator audit ensures 3.1c doesn't discover API gaps mid-execution. Sample contracts give 3.1c-06 a concrete starting point instead of inventing the format from scratch.

#### Expected Outputs

- **Created:** `src/alphaswarm_sol/shipping/MANIFEST.yaml` (~200 lines, 30 skills + 21 agents)
- **Created:** `.vrs/debug/phase-3.1/evaluator-audit.md` (WorkflowEvaluator + TrajectoryEvaluator API documentation)
- **Created:** `.vrs/debug/phase-3.1/harness-audit.md` (workflow_harness readiness assessment with known gaps)
- **Created:** `tests/workflow_harness/contracts/samples/` (2-3 sample capability contracts)
- **Modified:** `.claude/settings.json` (orphaned hook config removed)
- **Metric:** MANIFEST.yaml skill count = `ls src/alphaswarm_sol/shipping/skills/*.md | wc -l`; agent count = `ls src/alphaswarm_sol/shipping/agents/*.md | wc -l`
- **State:** 3.1c-09/10 can consume manifest directly; evaluator APIs documented for 3.1c integration; workflow_harness blessed for 3.1b use

#### Testing Strategy

| Output | Verification Method 1 | Verification Method 2 |
|---|---|---|
| MANIFEST.yaml has correct skill count | `grep -c "^  - id:" src/alphaswarm_sol/shipping/MANIFEST.yaml` = 51 (30 skills + 21 agents) | `ls src/alphaswarm_sol/shipping/skills/*.md \| wc -l` matches manifest skill count |
| MANIFEST.yaml has correct agent count | Agent section count matches filesystem | `ls src/alphaswarm_sol/shipping/agents/*.md \| wc -l` matches manifest agent count |
| Evaluator audit documents API contracts | `.vrs/debug/phase-3.1/evaluator-audit.md` exists and contains input/output signatures | Audit mentions known gaps (if any) for 3.1c integration |
| Harness audit documents readiness | `.vrs/debug/phase-3.1/harness-audit.md` exists with per-file assessment | Known gaps are actionable (assigned to specific 3.1b plan) |
| settings.json is clean | `grep -c "hook" .claude/settings.json` shows only active hooks (no orphaned entries) | 3.1b-03 can register hooks without conflict |
| Sample contracts validate | `python -c "import json; json.load(open('tests/workflow_harness/contracts/samples/skill-audit.json'))"` succeeds | Sample contracts have required fields: `workflow_id`, `category`, `capability_checks[]` |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|---|---|---|
| Manifest verified against filesystem | Manifest has round numbers (30/21) without filesystem verification | Gate: `ls` count must match manifest count; mismatch is a blocker |
| Evaluator audit is substantive, not cursory | Audit doc is < 20 lines or just lists file names | Audit must document at least: public API methods, input types, output types, extension points |
| Harness audit identifies real gaps | Audit says "everything is ready" with no gaps | At least one gap or caveat expected (12-file harness is unlikely perfect for 3.1b) |
| Sample contracts are usable by 3.1c-06 | Samples are trivial (empty or single-field) | Each sample must have >= 3 capability checks with concrete expected behaviors |

### 3.1-04: Update Testing Rules for Agent Teams + Controller

*(Was plan 03 in original. Same content, renumbered.)*

Rewrite rules targeting Agent Teams (Claude Code native) + `claude-code-controller` (npm v0.6.1, programmatic trigger):

**RULES-ESSENTIAL.md:**
- Replace legacy execution rules with "Agent Teams Execution"
- Replace legacy quick commands section with Agent Teams + controller commands
- Rewrite AUTO-INVOKE triggers — add "team", "teammate", "controller"
- Rewrite Mandatory Testing Pattern — 5 steps:
  1. `TeamCreate("vrs-test")` — Create team
  2. `Task(subagent_type="BSKG Attacker")` — Spawn teammates
  3. `TaskCreate/TaskUpdate` — Assign and track work
  4. `SendMessage` — Monitor and coordinate
  5. Verify via controller event capture (message, task:completed, agent:exited)

**VALIDATION-RULES.md:**
- Remove legacy session naming rules
- Update D3 (Isolation) — Agent Teams provides isolation by design; controller manages test environments
- Keep all anti-fabrication rules (F1-F4) — adapt transcript source to Agent Teams DMs and controller event log
- Keep all ground truth rules (B1-B3) unchanged
- Keep all metrics rules (C0-C3) unchanged

**Enforcement mechanism mapping:**
| Rule Category | Enforcement Via |
|---|---|
| Execution Integrity | Command hooks (`PreToolUse`) — block non-compliant tool calls |
| Transcript Authenticity | Agent hooks — verify Agent Teams DM content, min transcript length |
| Metrics Realism | Controller event capture — verify `total_cost_usd > 0`, duration > 5s |
| Ground Truth Provenance | Code-based graders in controller — compare against `ground-truth.yaml` |
| Report Integrity | Prompt hooks — single LLM call validates report structure |

**Simplify from 25 granular rules to ~15 clear categories:**
- Merge F1+F2+F1b -> "Transcript Authenticity"
- Merge C1+C2+C3 -> "Metrics Realism"
- Merge A1+A2+A3 -> "Execution Integrity"
- Merge B1+B2+B3 -> "Ground Truth Provenance"
- Merge E1+E2+E3 -> "Report Integrity"

**Evaluation-contract compatibility (for 3.1c-06):**
- Each consolidated rule category (~15) must have a stable, machine-readable ID (e.g., `EXEC-INTEGRITY`, `TRANSCRIPT-AUTH`, `METRICS-REALISM`, `GROUND-TRUTH`, `REPORT-INTEGRITY`)
- Rule IDs must be stable identifiers usable by 3.1c-06 evaluation contracts as `rule_ref` fields
- Rules should be structured so evaluation contracts can reference specific rule IDs to declare which rules a given workflow test enforces
- This enables 3.1c-06 to create evaluation contracts that cite `rule_refs: [EXEC-INTEGRITY, GROUND-TRUTH]` instead of free-text descriptions

**Exploration context:** Rules docs currently have 152 `claude-code-controller` references that need updating to reflect Agent Teams as primary execution model.

Archive removed rules to `.planning/archive/testing-rules/legacy/`.

**Exit gate:** Rules docs have zero legacy infrastructure references. Rule count reduced from ~25 to ~15. Every rule maps to an enforcement mechanism (hook type or controller check).

**Estimated scope:** ~2 files modified (RULES-ESSENTIAL.md, VALIDATION-RULES.md), ~500 lines rewritten.

#### Reasoning

Rules are the contract that Phase 3.1-05 (evaluation contract foundation) and 3.1c-06 (24 evaluation contracts) will reference. If rules still reference legacy infrastructure, evaluation contracts will be built against a dead execution model. Consolidating from ~25 to ~15 categories with stable IDs also makes it possible for 3.1c-06 evaluation contracts to cite specific rules via `rule_refs[]`. The merge preserves all anti-fabrication and ground-truth integrity rules, which are the backbone of the 6.0 "prove everything" philosophy.

#### Expected Outputs

- **Modified:** `.planning/testing/rules/canonical/RULES-ESSENTIAL.md`, `.planning/testing/rules/canonical/VALIDATION-RULES.md`
- **Archived:** Original pre-rewrite versions to `.planning/archive/testing-rules/legacy/`
- **Metric:** Rule count drops from ~25 to ~15 categories; legacy infrastructure string count in both files = 0
- **State:** Every rule category has a stable machine-readable ID usable by 3.1c-06 evaluation contracts as `rule_ref` fields

#### Testing Strategy

| Output | Verification Method 1 | Verification Method 2 |
|---|---|---|
| Zero legacy references | `grep -ri "legacy-infra-marker" .planning/testing/rules/canonical/RULES-ESSENTIAL.md` returns 0 | `grep -ri "legacy-infra-marker" .planning/testing/rules/canonical/VALIDATION-RULES.md` returns 0 |
| Rule count ~15 | Count `### ` headers (or rule IDs) in both files; total in range [12, 18] | Cross-reference: every merged category appears as a heading |
| Merge correctness | Each original rule (F1, F2, F1b, etc.) content appears under its merged category | No original rule content is silently dropped (diff review against archived originals) |
| Anti-fabrication rules preserved | `grep -c "fabricat\|fake\|authentic" VALIDATION-RULES.md` >= 3 | Rules F1-F4 substance (nonce, hash, duration) present in "Transcript Authenticity" category |
| Archive complete | Archived files are byte-identical to pre-rewrite originals | `diff` between archive and git HEAD~1 version shows no changes |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|---|---|---|
| Rules restructured around Agent Teams model | Legacy terms replaced without restructuring the actual workflow steps | Manual review: new rules reference `TeamCreate`, `SendMessage`, `TaskCreate` -- not just string replacement |
| Merge consolidates without losing substance | Merged categories are shorter than the sum of their parts (content dropped) | Word count of merged category >= 60% of sum of original rule word counts |
| Anti-fabrication rules are strengthened, not weakened | F1-F4 rules weakened (e.g., nonce verification removed, duration bounds relaxed) | Each fabrication check (nonce, hash, duration, evidence) has a corresponding rule sentence |

### 3.1-05: Evaluation Contract Foundation + Assertion Integration

**Purpose:** Build the foundation that 3.1c-06 (24 evaluation contracts) will scale from, and integrate with existing `tests/workflow_harness/lib/assertions.py` instead of creating parallel enforcement.

**Why this replaces standalone enforcement:** The original plan created a parallel enforcement stack (pytest plugin, transcript validator, report schema) that 3.1c-06 would duplicate independently. This plan instead builds the evaluation contract schema and samples that 3.1c-06 needs, and extends the existing workflow_harness assertions rather than creating new enforcement files.

#### Actions

1. **Define evaluation contract JSON schema** at `.vrs/testing/schemas/evaluation_contract.schema.json` — fields: `workflow_id`, `category`, `rule_refs[]` (from 3.1-04 stable rule IDs), `capability_checks[]`, `reasoning_dimensions[]`, `evidence_requirements[]`, `grader_type` (code/model)
2. **Create 3 sample evaluation contracts** (1 skill, 1 agent, 1 orchestrator flow) as concrete examples for 3.1c-06
3. **Extend `tests/workflow_harness/lib/assertions.py`** (currently 241 LOC, 7 categories) with evaluation-contract-aware assertion helpers: `assert_matches_contract(result, contract)`, `assert_reasoning_dimensions_covered(transcript, contract)`
4. **Create `tests/test_evaluation_contracts.py`** — validates sample contracts against schema, tests assertion integration
5. **Explicitly NOT building:** standalone enforcement functions (pytest_rules_plugin.py), report JSON schema, transcript validator — these belong in 3.1c where the evaluation pipeline consumes them

**Exit gate:** Schema defined. 3 sample contracts validate. Assertion helpers integrated with existing workflow_harness. Tests pass with both valid and invalid contract fixtures.

**Estimated scope:** ~100 lines schema + 3 contracts (~50 lines each) + ~100 lines assertion extensions + ~150 lines tests

#### Reasoning

3.1c-06 creates 24 evaluation contracts. Without a schema and samples, it invents the format from scratch — risking inconsistency and rework. By building the foundation here, 3.1c-06 becomes "scale the pattern" rather than "invent the pattern." The assertion integration reuses existing infrastructure (`tests/workflow_harness/lib/assertions.py`) rather than creating a parallel enforcement stack (`pytest_rules_plugin.py`, `transcript_validator.py`). The `rule_refs[]` field connects evaluation contracts to the stable rule IDs created in 3.1-04.

#### Expected Outputs

- **Created:** `.vrs/testing/schemas/evaluation_contract.schema.json` (~100 lines)
- **Created:** `.vrs/testing/contracts/samples/skill-audit.json`, `.vrs/testing/contracts/samples/agent-attacker.json`, `.vrs/testing/contracts/samples/orchestrator-debate.json` (~50 lines each)
- **Modified:** `tests/workflow_harness/lib/assertions.py` (+~100 lines, 2 new assertion helpers)
- **Created:** `tests/test_evaluation_contracts.py` (~150 lines, schema validation + assertion integration tests)
- **Metric:** 3 sample contracts validate against schema; assertion helpers have pass + fail tests
- **State:** 3.1c-06 can reference schema and extend from samples; assertion helpers available for all downstream tests

#### Testing Strategy

| Output | Verification Method 1 | Verification Method 2 |
|---|---|---|
| Schema is well-formed | `python -c "import jsonschema; jsonschema.Draft7Validator.check_schema(json.load(open('schema.json')))"` succeeds | Schema requires at least: `workflow_id`, `category`, `capability_checks[]` |
| Sample contracts validate | All 3 samples pass schema validation | Each sample has >= 3 capability checks with concrete expected behaviors |
| Invalid contracts rejected | Contract missing `workflow_id` fails schema validation | Contract with empty `capability_checks[]` fails validation |
| Assertion helpers work | `assert_matches_contract(good_result, contract)` passes | `assert_matches_contract(bad_result, contract)` raises `AssertionError` |
| Integration with existing harness | `from tests.workflow_harness.lib.assertions import assert_matches_contract` succeeds | Existing 7 assertion categories still work (no regressions) |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|---|---|---|
| Schema is substantive, not trivial | Schema has < 5 required fields or no `capability_checks` validation | Schema must validate structure of `capability_checks[]`, `rule_refs[]`, `reasoning_dimensions[]` |
| Sample contracts are realistic | Samples have 1 field or generic descriptions | Each sample must reference real skill/agent IDs and concrete behaviors |
| Assertion helpers actually validate | `assert_matches_contract` returns True without checking anything | Both pass and fail test cases required; fail case must raise on specific mismatch |
| No parallel enforcement stack created | New files created at `src/alphaswarm_sol/testing/pytest_rules_plugin.py` or `transcript_validator.py` | Only `assertions.py` extended; no new enforcement modules in `src/` |

### 3.1-06: Clean Up Testing Test Files

*(Was plan 06 in original. Same content, renumbered.)*

Handle test files that test removed infrastructure:

- Tests for dead runners (MasterOrchestrator, AgenticRunner, FullTestingOrchestrator, etc.) -> DELETE
- Tests for `flexible/` -> DELETE
- Tests for `e2e/` infrastructure -> DELETE
- Tests for dead standalone files (evidence_pack, proof_tokens, etc.) -> DELETE
- Tests for legacy workflow controllers -> DELETE

Preserve tests for:
- Living CLI-consumed modules (tiers, detection, generator, quality, etc.)
- Kept runners (WorkflowEvaluator, TrajectoryEvaluator)
- Active workflow modules (improvement_loop, scenarios)

Run full test suite after removal to verify no cascading failures.

**Exit gate:** `pytest tests/ -n auto --dist loadfile` passes with zero errors. Test count drops (dead tests removed) but no false failures.

**Estimated scope:** ~2K LOC of test files deleted (matching ~15K LOC of deleted production code).

#### Reasoning

After removing dead code (3.1-01) and legacy infrastructure (3.1-02), test files that test those removed modules become dead weight and import-error sources. Only tests whose import targets no longer exist should be deleted; tests for living modules must be preserved.

#### Expected Outputs

- **Deleted:** Test files whose sole purpose is testing modules removed in 3.1-01 and 3.1-02
- **Metric:** Test count drops (dead tests removed); zero test failures in `pytest tests/ -n auto --dist loadfile`; test count for living modules unchanged
- **State:** Every remaining test file imports only modules that exist in the codebase

#### Testing Strategy

| Output | Verification Method 1 | Verification Method 2 |
|---|---|---|
| Only dead-code tests deleted | Each deleted test file's imports reference ONLY modules deleted in 3.1-01/3.1-02 | `pytest tests/ --collect-only` collects all remaining tests without import errors |
| No cascade failures | `pytest tests/ -n auto --dist loadfile` exit code 0 | `pytest tests/ -n auto --dist loadfile 2>&1 \| grep -c "FAILED"` returns 0 |
| Living-code tests preserved | Test count for `tiers`, `detection`, `generator`, `quality` modules unchanged | `ls tests/test_workflow_evaluator*` exists (tests for kept runner) |
| Test count delta accurate | Before/after `pytest --collect-only \| wc -l` comparison; delta = number of deleted test functions | No test that was passing before is now missing (except those testing deleted code) |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|---|---|---|
| Only tests for REMOVED code are deleted | Tests for living modules deleted | Pre/post diff: test files for living modules must exist in both states |
| Deletion is surgical, not bulk | `git rm tests/` or bulk deletion of test directory | Each deleted file must be individually justified (imports only dead modules) |
| No false failures introduced | Tests that were passing before 3.1-06 now fail | `pytest tests/ -x` exit code 0; same pass count for non-deleted tests |

### 3.1-07: Verify Clean State

Final verification — **7 checks** (expanded to cover 3.1c readiness deliverables):

1. `grep -ri "legacy-infra-marker" src/alphaswarm_sol/` — zero production hits
2. `pytest tests/ -n auto --dist loadfile` — all pass
3. `uv run alphaswarm build-kg tests/contracts/SimpleToken.sol` — still works
4. Dead code scan — no orphaned imports in `testing/`; `__init__.py` exports only verified symbols
5. Evaluation contract schema defined — sample contracts validate against it; assertion integration importable
6. `MANIFEST.yaml` exists with 30 skills + 21 agents (verified against `src/alphaswarm_sol/shipping/`)
7. Sample evaluation contracts validate against schema; `assert_matches_contract` importable from workflow_harness

**Exit gate:** All 7 checks pass. Phase 3.1 is complete.

**Estimated scope:** ~2 hours verification, no code changes.

#### Reasoning

This is the composite gate that proves Phase 3.1 achieved its goal. Each prior plan has its own exit gate, but isolated gates can pass while the overall system is inconsistent. This plan runs all 7 checks as a single verification pass. It must be the last plan because it validates the cumulative effect of 3.1-01 through 3.1-06. Checks 6-7 verify the new 3.1c readiness deliverables (manifest, evaluation contracts) that ensure downstream phases have what they need. Passing this gate is the prerequisite for entering Phase 3.1b (Workflow Testing Harness) and eventually Phase 3.2 (First Working Audit).

#### Expected Outputs

- **Created:** `.vrs/debug/phase-3.1/verification-report.json` (structured results of all 7 checks)
- **Metric:** 7/7 checks pass; composite gate status = PASS
- **State:** Phase 3.1 marked complete in `.planning/STATE.md`; Phase 3.1b and 3.2 unblocked

#### Testing Strategy

| Output | Verification Method 1 | Verification Method 2 |
|---|---|---|
| Check 1: zero legacy hits | `grep -ri "legacy-infra-marker" src/alphaswarm_sol/` returns 0 (excluding `.planning/` and archive) | `grep -ri "legacy-infra-marker" configs/` returns 0 (excluding archived configs) |
| Check 2: all tests pass | `pytest tests/ -n auto --dist loadfile` exit code 0 | `pytest tests/ -n auto --dist loadfile 2>&1 \| grep -c "FAILED"` = 0 |
| Check 3: pipeline works | `uv run alphaswarm build-kg tests/contracts/SimpleToken.sol` exit code 0 | Output contains valid graph JSON with `nodes` and `edges` |
| Check 4: no orphaned imports | `python -c "import alphaswarm_sol.testing"` succeeds | `__init__.py` exports only symbols with verified callers (~20-30 lines, not 456) |
| Check 5: evaluation contracts valid | Sample contracts pass schema validation | `assert_matches_contract` importable and functional with pass/fail cases |
| Check 6: MANIFEST.yaml complete | `grep -c "^  - id:" src/alphaswarm_sol/shipping/MANIFEST.yaml` = 51 (30 + 21) | Skill count matches `ls src/alphaswarm_sol/shipping/skills/*.md \| wc -l` |
| Check 7: assertion integration works | `from tests.workflow_harness.lib.assertions import assert_matches_contract` succeeds | `assert_reasoning_dimensions_covered` importable and tested |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|---|---|---|
| All 7 checks actually executed | Verification report shows < 7 checks, or some checks show "skipped" | Verification report JSON must have exactly 7 entries, all with `status: "pass"` or `status: "fail"` |
| Failures block phase completion | Agent marks phase complete despite 1+ check failures | `.planning/STATE.md` update gated on verification-report showing 7/7 pass |
| Checks are real, not fabricated | Verification report created without running actual commands (timestamps < 1s apart) | Report includes command stdout/stderr excerpts; total duration > 30 seconds |
| Pipeline test uses real contract | `build-kg` called with empty file or no file | Verification report includes `node_count > 0` from build-kg output |

## Key Files

- `src/alphaswarm_sol/testing/` — Main testing module (~31K LOC, cleanup target)
- `src/alphaswarm_sol/testing/__init__.py` — 456-line barrel export (rewrite target)
- `src/alphaswarm_sol/cli/main.py:820` — CLI entry point consuming 8 testing symbols
- `.planning/testing/rules/canonical/RULES-ESSENTIAL.md` — Testing rules (rewrite for Agent Teams + stable rule IDs)
- `.planning/testing/rules/canonical/VALIDATION-RULES.md` — Validation rules (rewrite for Agent Teams)
- `src/alphaswarm_sol/testing/workflow/workflow_evaluator.py` — 553 LOC (KEEP, audit for 3.1c readiness)
- `src/alphaswarm_sol/testing/trajectory/evaluator.py` — 240 LOC (KEEP, audit for 3.1c readiness)
- `tests/workflow_harness/` — 12 files with assertions, transcript parsing (audit for 3.1b readiness)
- `tests/workflow_harness/lib/assertions.py` — 241 LOC, 7 categories (extend with evaluation-contract helpers)
- `src/alphaswarm_sol/shipping/MANIFEST.yaml` — NEW: authoritative skill/agent inventory for 3.1c-09/10
- `.vrs/testing/schemas/evaluation_contract.schema.json` — NEW: evaluation contract schema for 3.1c-06
- `.vrs/testing/contracts/samples/` — NEW: 3 sample evaluation contracts
- `tests/workflow_harness/contracts/samples/` — NEW: 2-3 sample capability contracts
- `.claude/settings.json` — Clean orphaned hook config for 3.1b-03

## Success Criteria

1. ~15K LOC of dead testing code removed (final amount must match import-graph evidence)
2. Zero deprecated infrastructure references in production code
3. Shipping manifest created with verified skill/agent inventory for 3.1c-09/10
4. Testing rules rewritten for Agent Teams (~15 clear categories with stable rule IDs for 3.1c-06)
5. Evaluation contract schema + 3 samples created for 3.1c-06 foundation; assertion helpers integrated with workflow_harness
6. Existing evaluators (WorkflowEvaluator, TrajectoryEvaluator) audited and blessed for 3.1c; workflow_harness blessed for 3.1b
7. Full test suite passes after cleanup
8. Core pipeline (`build-kg`) still works

## 2026-02-09 Reordering Audit Context

### Global Sequence

Execution order after Phase 2.1 is now fixed:
`3.1 -> 3.1b -> 3.2 -> 4 -> 4.1 -> 6 -> 7 -> 5 -> 8`

### Iteration Notes (1 -> 3)

1. Iteration 1: cleanup plan was strong but did not guarantee marker/proof enforcement early enough.
2. Iteration 2: moved marker and proof-token hard-fail enforcement into Phase 3.1 gates.
3. Iteration 3: strict review accepted this phase only if enforcement becomes a prerequisite for 3.2.

### This Phase's Role

Phase 3.1 is now the enforcement foundation, not only cleanup. It must leave behind fail-closed marker/proof gate infrastructure.

### Mandatory Carry-Forward Gates

- MANIFEST.yaml provides authoritative skill/agent inventory for all downstream phases.
- Evaluation contract schema defines the format 3.1c-06 scales from.
- Assertion helpers (`assert_matches_contract`, `assert_reasoning_dimensions_covered`) available for import by any downstream test.
- Evaluator audit documents (WorkflowEvaluator, TrajectoryEvaluator) provide API contracts for 3.1c integration.
- Clean `.claude/settings.json` provides conflict-free hook registration for 3.1b-03.

### Debug/Artifact Contract

- Any failing gate writes `.vrs/debug/phase-3.1/repro.json`.
- Repro includes validator output, failing artifact IDs, and exact command invocation.

### Assigned Research Subagent

- `vrs-test-conductor` for enforcement harness hardening

### Research Sources Used

- `docs/PHILOSOPHY.md`
- https://arxiv.org/abs/2601.06112
- https://docs.jj-vcs.dev/latest/working-copy/

---

## Cross-Phase: Failure Handling & Regression Protocol

### On Test Failure
- Capture failure details, import graph state, and exact error messages
- Environment preserved at `.vrs/debug/phase-3.1/failures/{plan}-{timestamp}/`
- Include full command output and file diffs
- Append drift record to `.vrs/debug/phase-3.1/drift-log.jsonl` with:
  - `plan_id`, `expected_behavior`, `observed_behavior`, `root_cause_hypothesis`
  - `why_drift_happened` (human-written)
  - `corrective_action`, `verification_after_fix`, `owner`, `timestamp`

### Improvement Cycle
- Fix based on failure artifacts
- Re-run exact same verification
- Compare before/after
- Continue until convergence or max iterations

### Anti-Fabrication Rules
- Import graph analysis MUST run before any deletion (artifact proof)
- Import graph MUST exclude `__init__.py` barrel re-exports from caller counts
- 100%/100% Rule: Any metric reported as 100% precision AND 100% recall triggers mandatory fabrication investigation
- CLI functionality verified post-deletion (not assumed)
- Evaluation contract assertion helpers must have BOTH pass AND fail test cases
- MANIFEST.yaml counts must match filesystem reality, never hardcoded assumptions
