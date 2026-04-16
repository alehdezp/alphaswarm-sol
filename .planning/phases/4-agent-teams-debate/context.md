# Phase 4: Agent Teams Debate

## Goal

Run real attacker-defender-verifier debates with evidence-grounded verdicts and transcript proof, using Claude Code Agent Teams as the orchestrator model.

## Why This Phase Exists

`docs/PHILOSOPHY.md` makes debate central, but current code reality still has major gaps:

- No implemented TeamCreate/TaskCreate/TaskUpdate flow in production path.
- Debate execution path is only partially wired.
- Graph-first and evidence completeness are documented, not enforced.
- Orchestration markers are required but not systematically emitted.

## Dependencies

- Phase 3.1 cleanup complete (dead infrastructure removed).
- Phase 3.1c provides multi-agent evaluation (3.1c-11) and agent debrief (3.1c-05, approach pending research) via SendMessage for per-agent reasoning assessment during debate.
- Phase 3.2 first working audit complete with at least one real bead lifecycle.
- Hook and marker enforcement introduced before scaling debate.
- `jj` workspace isolation available for parallel team runs.

## Critical Gaps to Close

1. Missing Agent Teams wiring and task lifecycle primitives.
2. Missing graph-node and proof-token fields in evidence schemas.
3. Missing runtime enforcement for graph-first behavior.
4. Missing required orchestration markers in transcripts.
5. Missing team-level regression tests.

## Key Files

- `src/alphaswarm_sol/orchestration/handlers.py`
- `src/alphaswarm_sol/orchestration/debate.py`
- `src/alphaswarm_sol/orchestration/schemas.py`
- `.claude/settings.json`
- `.claude/agents/vrs-attacker.md`
- `.claude/agents/vrs-defender.md`
- `.claude/agents/vrs-verifier.md`
- `.planning/research/agent-teams-migration/ROADMAP.md`

## Plans (Reordered, Test-First)

### 4-01: Add Failing Tests for Debate Contracts and Markers

- Add tests that fail unless Team lifecycle markers are present.
- Add tests that fail unless evidence packets carry graph references and proof fields.

#### Reasoning

Test-first is the only honest way to prove debate infrastructure works: if the tests pass before implementation, the tests are worthless. Debate lifecycle markers (TeamCreate, TaskCreate, TaskUpdate, TaskComplete) and evidence graph references are the two structural pillars that distinguish real multi-agent debate from a single-agent pretending. These tests encode the contract that Phase 4 implementation must satisfy.

#### Expected Outputs

- `tests/test_debate_markers.py` with tests for TeamCreate/TaskCreate/TaskUpdate/TaskComplete marker presence in transcripts
- `tests/test_evidence_graph_refs.py` with tests asserting `graph_node_id` is present and non-empty in every `EvidenceItem`
- `tests/test_proof_token_fields.py` with tests asserting proof tokens are linked to evidence packets
- All tests fail (RED) on the current codebase -- verified by running `pytest` and capturing failure output
- A `tests/contracts/DebateTarget.sol` (or reuse of an existing vulnerable contract like `ReentrancyClassic.sol`) designated as the canonical debate test contract

#### Testing Strategy

| Output | Method 1 | Method 2 |
|--------|----------|----------|
| Marker presence tests | `pytest tests/test_debate_markers.py` -- all FAIL (xfail) | Manual transcript grep for `[TEAM-CREATE]`, `[TASK-CREATE]` markers absent |
| Evidence graph ref tests | `pytest tests/test_evidence_graph_refs.py` -- all FAIL (xfail) | Construct `EvidenceItem` without `graph_node_id`, assert validator rejects |
| Proof token linkage tests | `pytest tests/test_proof_token_fields.py` -- all FAIL (xfail) | Build `EvidencePacket` via `EvidencePackBuilder`, assert proof token list non-empty |
| Test contract compilation | `load_graph("ReentrancyClassic")` succeeds via `graph_cache.py` | `uv run alphaswarm build-kg tests/contracts/ReentrancyClassic.sol` succeeds |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|-------------------|-------------------|-------------|
| Tests fail before 4-03 implementation | Tests marked `xfail` pass on current code (wrong: tests are trivial) | CI gate: `pytest --strict-markers` rejects unintended xpass |
| Tests assert structural markers, not string content | Tests grep for exact substrings like "attacker found vuln" instead of marker tokens | Code review: tests must reference `[TEAM-CREATE]`, `[TASK-CREATE]` constants |
| Tests use real graph from `load_graph()` | Tests use hardcoded mock dicts instead of `graph_cache.py` | Pre-commit check: no `{"nodes": ...}` literals in test files |
| Tests are not implementation mirrors | Test checks same code path as production (circular) | Tests validate outputs (marker set, field presence), not internal calls |

### 4-02: Add Hook Tests for Graph-First Enforcement

- Add hook tests that block Solidity reads before graph queries in audit mode.
- Add hook tests that reject incomplete evidence at task completion.

#### Reasoning

Graph-first is a core PHILOSOPHY.md invariant, but without runtime enforcement agents will silently skip BSKG queries and go straight to `.sol` file reads. The `PreToolUse` hook with a `has_queried_graph` state flag is the only mechanism that makes graph-first non-optional. Without testing the hook itself, we cannot distinguish between an agent that queries the graph because it wants to and one that is forced to -- only the latter is reliable.

#### Expected Outputs

- `tests/test_graph_first_hooks.py` with tests for `PreToolUse` hook blocking `Read *.sol` when `has_queried_graph` is False
- `tests/test_evidence_completion_hooks.py` with tests for `SubagentStop` hook rejecting output missing required evidence fields
- `tests/test_hook_state_tracking.py` with tests for `has_queried_graph` state transitions (False -> True after `alphaswarm query`)
- Hook implementation stubs in `.claude/settings.json` (or `hooks/` directory) referenced by tests
- `PostToolUse` hook test asserting logged query strings are non-empty and results are non-empty

#### Testing Strategy

| Output | Method 1 | Method 2 |
|--------|----------|----------|
| PreToolUse blocks .sol reads | Simulate hook call with `has_queried_graph=False` + `Read contracts/Vault.sol`, assert BLOCK | Integration: run audit workflow, intercept first tool call, verify it is `alphaswarm query` not `Read` |
| SubagentStop rejects bad evidence | Call hook with `EvidencePacket(items=[])`, assert rejection | Call hook with `EvidenceItem(graph_node_id="")`, assert rejection |
| State flag transitions | Unit: set flag False, simulate `alphaswarm query` PostToolUse, assert flag True | Sequence: simulate [query, Read .sol], assert both allowed; simulate [Read .sol] alone, assert blocked |
| Verifier Stop hook blocks query tools | Simulate verifier `PreToolUse` with `alphaswarm query`, assert BLOCK | Simulate verifier `PreToolUse` with `build-kg`, assert BLOCK |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|-------------------|-------------------|-------------|
| Hook blocks .sol reads until graph is queried | Agent issues no-op BSKG query (empty string, `*`, or query whose results are never referenced) | `PostToolUse` hook logs query string + result count; downstream test asserts result count > 0 AND query string length > 10 |
| `has_queried_graph` starts False per session | Flag is initialized to True (always passes, never blocks) | Test explicitly asserts initial state is False before any tool calls |
| Hook operates in audit mode only | Hook is active in all modes (false positives in development) OR hook is never active (misconfigured mode check) | Test runs hook in both `audit` and `development` mode, asserts block only in audit |
| Verifier cannot run graph queries | Verifier PreToolUse allows `alphaswarm query` (verifier doing its own analysis instead of synthesizing) | Stop hook on verifier rejects `alphaswarm query` and `build-kg` tool names |

### 4-03: Implement Agent Teams Wiring

- Introduce team orchestration path with explicit task lifecycle handling.
- Ensure attacker, defender, verifier run as separate teammates with isolated outputs.

#### Reasoning

This is the core implementation plan that the test-first plans (4-01, 4-02) exist to validate. Agent Teams wiring means TeamCreate spawns three real subagents (attacker, defender, verifier) with isolated message channels and separate output artifacts. The critical design constraint is independence: attacker and defender must query the graph independently, and verifier must synthesize only from their outputs without running its own primary analysis. Without this structural isolation, "multi-agent debate" degenerates into a single agent talking to itself.

#### Expected Outputs

- Updated `src/alphaswarm_sol/orchestration/handlers.py` with `TeamCreate` + `SendMessage` lifecycle calls
- Updated `src/alphaswarm_sol/orchestration/debate.py` with 3-agent debate flow (attacker -> defender -> verifier)
- Agent prompt updates in `.claude/agents/vrs-attacker.md`, `.claude/agents/vrs-defender.md`, `.claude/agents/vrs-verifier.md` enforcing isolated output format
- Hook implementations: `PreToolUse` (graph-first gate), `PostToolUse` (query logging), `SubagentStop` (evidence validation), `Stop` on verifier (blocks primary analysis tools)
- `src/alphaswarm_sol/orchestration/team_config.py` (or equivalent) defining team topology and message routing
- Transcript output per agent stored under `.vrs/debug/phase-4/transcripts/{attacker,defender,verifier}.txt`
- All 4-01 and 4-02 tests passing (GREEN)

#### Testing Strategy

| Output | Method 1 | Method 2 |
|--------|----------|----------|
| Team lifecycle wiring | Run `pytest tests/test_debate_markers.py` -- all pass | Manual: inspect `.vrs/debug/phase-4/` for 3 separate transcript files |
| Agent isolation | Jaccard similarity of attacker vs defender BSKG query strings < 0.8 | Verify attacker transcript contains no defender-attributed markers and vice versa |
| Verifier synthesize-only | Verifier transcript contains zero `alphaswarm query` or `build-kg` calls | `Stop` hook rejection log shows blocked tool attempts (if any) |
| Evidence completeness | `pytest tests/test_evidence_graph_refs.py` -- all pass | JSON schema validation of verdict artifacts against `schemas/` |
| Hook enforcement live | `pytest tests/test_graph_first_hooks.py` -- all pass | `PostToolUse` log shows non-empty query strings with result_count > 0 |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|-------------------|-------------------|-------------|
| Attacker and defender query independently | Defender copies attacker's exact query strings (Jaccard >= 0.8) | CI metric: compute Jaccard similarity of query string sets, fail if >= 0.8 |
| Verifier synthesizes from attacker+defender outputs only | Verifier runs its own `alphaswarm query` or reads `.sol` files directly | `Stop` hook on verifier blocks `alphaswarm query`, `build-kg`, and `Read *.sol` |
| Three separate transcripts exist | Single transcript file with role labels (fake isolation) | Test asserts 3 distinct files exist under `.vrs/debug/phase-4/transcripts/` |
| Team uses SendMessage for inter-agent communication | Agents share a global variable or file instead of message passing | Test checks SendMessage call count >= 2 in orchestration log |

### 4-04: Extend Evidence Schema and Validators

- Add graph node IDs, operation sequence refs, and proof-token refs to verdict artifacts.
- Update validators and tests to enforce fields.

#### Reasoning

The current `EvidenceItem` dataclass in `src/alphaswarm_sol/orchestration/schemas.py` has `type`, `value`, `location`, `confidence`, and `source` but no `graph_node_id` or `operation_sequence` field. Without these, evidence is structurally disconnected from the knowledge graph -- claims reference code locations but not the graph nodes that make them verifiable. This plan closes that gap at the schema level and adds validators that reject evidence items missing graph anchors.

#### Expected Outputs

- Updated `EvidenceItem` in `src/alphaswarm_sol/orchestration/schemas.py` with new fields: `graph_node_id: str = ""`, `operation_sequence: str = ""`, `proof_token_ref: str = ""`
- Updated `EvidenceItem.to_dict()` and `EvidenceItem.from_dict()` to include new fields
- New validator function `validate_evidence_item(item: EvidenceItem) -> tuple[bool, list[str]]` that rejects empty/placeholder `graph_node_id`
- Updated JSON schema in `schemas/` (if a verdict/evidence schema exists) to include new required fields
- Updated `EvidencePacket` validation to check all items have valid `graph_node_id`
- Tests in `tests/test_evidence_schema.py` covering valid, missing, and placeholder cases

#### Testing Strategy

| Output | Method 1 | Method 2 |
|--------|----------|----------|
| New fields present in schema | `EvidenceItem(type="sig", value="v", location="l", graph_node_id="fn-42")` constructs without error | `item.to_dict()` output includes `graph_node_id` key |
| Validator rejects empty graph_node_id | `validate_evidence_item(EvidenceItem(..., graph_node_id=""))` returns `(False, ["graph_node_id empty"])` | `validate_evidence_item(EvidenceItem(..., graph_node_id="N/A"))` returns `(False, ...)` |
| Validator rejects placeholder values | Test with `graph_node_id` in `{"unknown", "N/A", "TODO", "placeholder", ""}` -- all rejected | Test with valid `graph_node_id` like `"fn-withdraw-42"` -- accepted |
| Backward compatibility | Existing tests in `tests/` still pass with new optional fields | `EvidenceItem.from_dict({"type": "x", "value": "y", "location": "z"})` succeeds with defaults |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|-------------------|-------------------|-------------|
| `graph_node_id` contains real graph node references | Field filled with placeholder strings: `"unknown"`, `"N/A"`, `""`, `"none"`, `"TODO"` | Validator maintains a BLOCKED_VALUES set and rejects any match (case-insensitive) |
| `operation_sequence` references real operation chains | Field contains generic strings like `"read-write"` instead of `"R:bal->X:out->W:bal"` format | Regex validator: must match `[A-Z]:[a-z]+(->[A-Z]:[a-z]+)+` pattern or be empty |
| Schema changes are backward compatible | Old serialized evidence fails to deserialize | `from_dict` defaults new fields to `""`, existing tests kept as-is |
| New fields are actually used in debate output | Fields always contain default values even after real debates run | Phase 4-05 tests assert `graph_node_id != ""` in at least 80% of evidence items |

### 4-05: Run Three Real Debate Scenarios

- Execute against three known-vulnerable contracts.
- Capture full transcripts and evidence packets.
- Cap debate rounds at two and keep team size at 3-4 agents to control coordination overhead.

#### Reasoning

Plans 4-01 through 4-04 build infrastructure; this plan proves the infrastructure works on real contracts. Three debates (not one, not ten) balance coverage against cost. The contracts must have different vulnerability profiles so that identical verdicts across all three would be a red flag. Using real test contracts from `tests/contracts/` (like `ReentrancyClassic.sol`, `CrossFunctionReentrancy.sol`, `NoAccessGate.sol`) rather than trivial `SimpleToken.sol` ensures the debate exercises actual graph-first reasoning over non-trivial vulnerability patterns.

**Field alignment note:** Evidence items use `graph_node_id` (singular), while finding-level summaries may aggregate these into a derived list (`graph_node_ids`) for reporting. Validators must treat item-level `graph_node_id` as canonical.

#### Expected Outputs

- Three complete debate runs with transcripts under `.vrs/debug/phase-4/debates/{contract_name}/`
- Evidence packets for each debate: `.vrs/debug/phase-4/debates/{contract_name}/evidence_pack/`
- Verdict artifacts (JSON/YAML) for each contract with non-default `graph_node_id` values
- Debate summary report: `.vrs/debug/phase-4/debate_summary.json` with per-contract verdicts
- At least one verdict that differs from the others (not all three identical CONFIRMED)
- Transcript marker coverage report showing TeamCreate, TaskCreate, TaskUpdate, TaskComplete markers present in all 3 runs
- Duration > 5 seconds per debate (MIN_DURATION_MS enforcement from `evidence_pack.py`)

#### Testing Strategy

| Output | Method 1 | Method 2 |
|--------|----------|----------|
| Three debates complete | `ls .vrs/debug/phase-4/debates/` shows 3 directories | `debate_summary.json` contains 3 entries with `status: complete` |
| Verdicts are not all identical | Parse 3 verdict JSONs, assert not all `confidence` values equal | Assert at least one contract produces `REJECTED` or `UNCERTAIN` if it is actually safe |
| Evidence packets valid | `validate_evidence_pack()` returns `(True, [])` for each | JSON schema validation against `schemas/` passes |
| Graph node refs populated | `>= 80%` of `EvidenceItem` instances have non-empty `graph_node_id` | Grep verdict JSON for `"graph_node_id": ""` -- count < 20% of total items |
| Duration bounds met | Each `manifest.json` shows `duration_ms > 5000` | `evidence_pack.py` validator rejects any pack with duration <= 5000 |
| Contracts are non-trivial | Contract names in summary are from `tests/contracts/` (not `SimpleToken.sol`) | Each contract has >= 5 functions in its VKG |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|-------------------|-------------------|-------------|
| Three different contracts used | All 3 runs use the same contract (e.g., `ReentrancyClassic.sol` three times) | CI: assert 3 unique contract names in `debate_summary.json` |
| Not all verdicts identical | All 3 produce `CONFIRMED` with identical confidence and rationale | Automated check: at least one pairwise verdict difference across the 3 runs |
| Real debate occurred (not single-pass) | Transcript shows only attacker output, no defender or verifier turns | Assert each transcript directory has 3 files (attacker, defender, verifier) with non-zero size |
| 100%/100% results trigger investigation | All evidence items have confidence 1.0 and all verdicts CONFIRMED | Fabrication check: if all metrics perfect, flag for manual review per Cross-Phase Invariant #1 |

### 4-06: Multi-run Stability Check

- Repeat debates across multiple runs for variance assessment.
- Flag unstable categories for follow-up.

#### Reasoning

A single successful debate proves nothing about reliability. LLM-driven analysis is inherently stochastic: the same contract may produce CONFIRMED on one run and UNCERTAIN on the next. The `pass^k` metric (does the same verdict appear across k independent runs?) quantifies this stability. Without measuring variance, we cannot distinguish a robust finding from a lucky coin flip. Running at least 3 repetitions per contract (k=3) gives a baseline for `pass^3` while staying within cost bounds.

#### Expected Outputs

- `pass^k` metric computed for k=3 across at least 2 contracts (6 total debate runs minimum)
- Stability report: `.vrs/debug/phase-4/stability_report.json` with per-contract, per-run verdict comparison
- Variance metrics: verdict agreement rate, confidence standard deviation, evidence overlap ratio
- Flagged categories: any vulnerability category where `pass^3 < 0.67` (verdict flipped in >= 1 of 3 runs)
- Run metadata: timestamps, duration, cost (`total_cost_usd > 0` per Cross-Phase Invariant #5)
- Recommendations for unstable categories (e.g., "reentrancy stable, access-control unstable -- needs prompt tuning")

#### Testing Strategy

| Output | Method 1 | Method 2 |
|--------|----------|----------|
| Multiple runs executed | `stability_report.json` contains >= 6 entries (3 runs x 2 contracts) | `.vrs/debug/phase-4/debates/` contains timestamped subdirectories showing distinct runs |
| `pass^k` computed correctly | Unit test: given 3 verdicts [CONFIRMED, CONFIRMED, UNCERTAIN], `pass^3` = 0.0, `pass^2` = 1.0 | Integration: parse `stability_report.json`, verify `pass_k` field matches manual calculation |
| Variance metrics meaningful | Confidence std_dev > 0 for at least one contract (non-trivial variance) | Evidence overlap ratio (Jaccard of graph_node_ids across runs) < 1.0 for at least one contract |
| Unstable categories flagged | `stability_report.json` has `flagged_categories` list | Any category with `pass^3 < 0.67` appears in the list |
| Cost tracked | Each run entry has `total_cost_usd > 0` | Sum of all costs is reasonable (not $0.00, not > $50 for 6 runs) |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|-------------------|-------------------|-------------|
| 3+ independent runs per contract | Only 1 run performed, duplicated 3 times in report | Assert distinct timestamps and distinct transcript hashes across runs for same contract |
| Variance is measured, not hidden | Report shows `pass^3 = 1.0` for all categories (suspiciously stable) | If all `pass^3 = 1.0`, trigger investigation per 100%/100% rule |
| Unstable categories are flagged, not ignored | Report has empty `flagged_categories` despite variance in verdicts | Automated: if any `pass^3 < 0.67`, assert `flagged_categories` is non-empty |
| Real cost incurred | `total_cost_usd = 0` across all runs (mocked API, no real inference) | CI: assert `total_cost_usd > 0` for at least 1 run; if all zero, reject as non-real |

## Hard Delivery Gates for Phase 4 (Added 2026-02-10)

Phase 4 is responsible for making multi-agent debate adversarial and falsifiable, not merely conversational.

### HDG-03: Independent Shadow Verifier (Sub-gate on 4-05 and 4-06)

**Why this is critical**
- A single verifier can inherit hidden bias from attacker/defender framing.
- A second isolated verifier is the minimal check against coordinated self-confirmation.

**Implementation contract**
- Spawn two verifier roles for each debate:
  - `verifier_primary`: sees attacker and defender evidence.
  - `verifier_shadow`: receives normalized evidence packet only (no primary verdict, no prior rationale).
- Both emit structured verdicts (`decision`, `confidence`, `required_evidence`, `unresolved_questions`).
- Write concordance artifact to `.vrs/debug/phase-4/shadow-verifier/<debate-id>.json`.

**Hard validation**
- If primary and shadow disagree on `decision` class (`confirmed` vs `rejected`), debate status becomes `needs-human-review`.
- If confidence delta > 0.25, automatic release-block for that finding category.
- Missing shadow-verifier artifact for any debate is an immediate phase failure.

**Expected strict result**
- Debate verdicts gain a second independent adjudication path, with explicit disagreement surfacing.

### HDG-11: Consensus Skepticism (Sub-gate on 4-05)

**Why this is critical**
- Debate quality collapses when agents only optimize to "win" rather than surface uncertainty.
- Forcing each side to state why it might be wrong increases epistemic pressure and reduces fabricated certainty.

**Implementation contract**
- Enforce structured self-critique fields in attacker and defender outputs:
  - `self_doubt.claim`
  - `self_doubt.evidence_gap`
  - `self_doubt.disproof_test`
- Require verifier to resolve both self-critiques in final verdict under:
  - `resolved_attacker_risk`
  - `resolved_defender_risk`
- Persist to `.vrs/debug/phase-4/consensus-skepticism/<debate-id>.json`.

**Hard validation**
- Any missing self-critique field blocks verdict finalization.
- Verifier output without explicit resolution of both sides is invalid.
- If both sides claim certainty with zero self-doubt across all runs, trigger fabrication investigation.

**Expected strict result**
- Debate transcripts include explicit "why I may be wrong" reasoning and adjudicated resolution.

### HDG-09: Uncertainty Protocol (Sub-gate on 4-06, hardened in Phase 7)

**Why this is critical**
- Systems that cannot emit uncertainty will over-claim by design.
- This gate forces safe degradation to `needs-human-review` when evidence is incomplete or contradictory.

**Phase boundary**
- **Phase 4 responsibility:** emit uncertainty fields and reason codes in debate verdict artifacts.
- **Phase 7 responsibility:** harden uncertainty into fail-closed schema + hook enforcement in production.
- Phase 4 is considered complete when uncertainty output exists and is exercised in debate tests; Phase 7 is considered complete when invalid uncertainty outputs are blocked at schema/hook level.

**Implementation contract**
- Add uncertainty schema fields to verdicts:
  - `evidence_completeness_score`
  - `conflict_set` (list of unresolved contradictions)
  - `human_review_required` (boolean)
  - `reason_codes` (enum list)
- Map unresolved conflicts to explicit reason codes (`MISSING_GRAPH_ANCHOR`, `EXPLOIT_NOT_REPLAYABLE`, `VERIFIER_DISAGREEMENT`, etc.).
- Block `confirmed` verdicts when `human_review_required=true`.

**Hard validation**
- Any verdict with unresolved conflicts and `confirmed` status fails schema validation.
- Reason codes must be present and non-empty for every `needs-human-review` verdict.
- At least one synthetic contradictory scenario in tests must produce `needs-human-review`.

**Expected strict result**
- The debate system can refuse confidence when proof is insufficient, with machine-readable reasons.

## Interactive Validation Method (Agent Teams + JJ Workspace)

- One `jj` workspace per debate run.
- One team per bead or per contract slice.
- Shared read-only graph artifacts, isolated write paths per teammate.
- Transcript logging and marker extraction required per run.

## Non-Vanity Metrics

- Debate completion rate by bead.
- Evidence completeness rate (required fields present).
- Graph-first compliance rate (hook logs).
- Transcript marker coverage rate.
- Inter-run verdict stability rate.
- `pass^k` verdict consistency on repeated runs of the same bead.
- Fault-tolerance recovery rate under injected tool/API failures during debate runs.

## Recommended Subagents

- `vrs-attacker`
- `vrs-defender`
- `vrs-verifier`
- `vrs-secure-reviewer`
- `vrs-integrator`
- `vrs-supervisor`

## Exit Gate

Three real debates run end-to-end with complete evidence packets, required markers, reproducible verdict artifacts, full debate-path workflow/agent/skill coverage evidence, and passing HDG-03/HDG-11/HDG-09 sub-gates.

## Research Inputs

- `.planning/new-milestone/reports/w2-agent-teams-architecture.md`
- `.planning/research/agent-teams-migration/ROADMAP.md`
- `docs/PHILOSOPHY.md`
- `docs/reference/claude-code-orchestration.md`
- `docs/reference/graph-first-template.md`
- External: ICML 2024 multi-agent debate factuality results
- External: ReliabilityBench (2026-01) consistency, robustness, and fault-tolerance methodology

## 2026-02-09 Reordering Audit Context

### Global Sequence

Execution order after Phase 2.1 is now fixed:
`3.1 -> 3.1b -> 3.2 -> 4 -> 4.1 -> 6 -> 7 -> 5 -> 8`

### Iteration Notes (1 -> 3)

1. Iteration 1: debate tasks existed but lacked hard all-skills-tested obligations.
2. Iteration 2: added explicit workflow/agent/skill coverage matrix for debate path.
3. Iteration 3: strict review required this matrix as exit-gate evidence, not optional reporting.

### This Phase's Role

Phase 4 proves multi-agent verification is real, tool-grounded, and reproducible before broad test and benchmark scaling.

### Mandatory Carry-Forward Gates

- Graph-first hook compliance in debate transcripts.
- Evidence completeness for every verdict.
- Debate-path workflow/agent/skill live coverage matrix.
- Shadow verifier concordance artifacts for every debate.
- Uncertainty protocol reason-code artifacts for non-confirmed decisions.

### Debug/Artifact Contract

- Any failure writes `.vrs/debug/phase-4/repro.json`.
- Repro includes teammate transcripts, marker coverage output, and evidence validation output.

### Phase 3.1c Integration: Multi-Agent Evaluation (2026-02-11)

Phase 4's multi-agent debate is the primary beneficiary of Phase 3.1c's reasoning evaluation framework.

#### Per-Agent Evaluation Contracts

Each debate participant has an evaluation contract:
- `tests/workflow_harness/contracts/workflows/vrs-attacker.yaml` — Full investigation evaluation (GVS, reasoning depth, evidence grounding, role compliance, novel insight)
- `tests/workflow_harness/contracts/workflows/vrs-defender.yaml` — Full investigation evaluation with emphasis on guard identification
- `tests/workflow_harness/contracts/workflows/vrs-verifier.yaml` — Synthesis evaluation (must NOT run primary analysis, must synthesize from attacker+defender)

#### Interactive Debrief via SendMessage

Before issuing shutdown_request to teammates, the orchestrator sends targeted debrief questions:

**To attacker/defender:**
1. Which graph queries were most useful?
2. Why did you choose the tools you used?
3. Did your analysis stay within scope?
4. What is your honest confidence?
5. What would you do differently?

**To verifier:**
1. Were attacker and defender outputs sufficient to synthesize?
2. What evidence gaps did you identify?
3. Where did attacker and defender most disagree?

Agent debrief captures reasoning before shutdown (approach per 3.1c-05 research outcome — blocking hook, orchestrator-level interview, or dedicated teammate).

#### Safe Prompt Sandboxing for Agent Improvements

When the evaluation framework identifies systematic weaknesses in an agent's performance:
1. Copy production agent .md (e.g., `src/alphaswarm_sol/shipping/agents/vrs-attacker.md`) to test project `.claude/agents/`
2. Modify the copy with targeted improvements
3. Re-run the same debate scenario
4. Compare before/after scores per dimension
5. Detect regressions (any dimension drops > 0.2 → revert)
6. Human reviews and approves production prompt update

This ensures debate agents are continuously improved based on real evaluation data without risking production prompt breakage.

#### Graph Value Score in Debate

GVS is particularly important for debate:
- Attacker GVS: measures whether exploit paths are graph-grounded (not fabricated)
- Defender GVS: measures whether guard identification uses graph data
- Verifier GVS: should be N/A (verifier synthesizes, doesn't query)
- Cross-agent GVS comparison: if attacker has low GVS but high confidence, flag as potential fabrication

#### C-Tier Pattern Tracking

Debate scenarios specifically test C-tier vulnerability patterns (complex multi-step reasoning). The evaluation framework tracks:
- Multi-predicate graph queries
- Cross-function reference chains
- Sequential query refinement patterns
- Whether agents can leverage graph for complex reasoning that code reading alone cannot provide

### Assigned Research Subagent

- `vrs-supervisor` for debate-path coverage and stability review

### Research Sources Used

- https://proceedings.mlr.press/v235/du24e.html
- https://arxiv.org/abs/2601.04742
- https://arxiv.org/abs/2601.06112
