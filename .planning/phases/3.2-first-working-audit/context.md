# Phase 3.2: First Working Audit

## Planning Status

- This phase is a **planning draft** and has not been fully implemented/tested yet.
- Flow diagrams and commands below define target behavior for implementation and validation.
- Execution split is intentional:
  - Shipping/runtime uses `/vrs-*` skills + subagent/task orchestration.
  - Team-based orchestration shown here (`TeamCreate`, `SendMessage`) is the Phase-3 testing harness path.

## Goal

ONE complete audit from Solidity contract to vulnerability report, with deterministic replay and fail-closed evidence gates.

## Architecture Context

**Claude Code IS the orchestrator.** For Phase-3 validation, the pipeline is tested through Claude Code team orchestration and stage tasks:

```
┌──────────────────────────────────────────────────────────────┐
│  Claude Code (Orchestrator)                                    │
│  - Creates audit team: TeamCreate("vrs-audit-mvp")            │
│  - Pipeline stages assigned as tasks:                          │
│    1. TaskCreate("build-kg") → run alphaswarm build-kg        │
│    2. TaskCreate("detect") → run pattern detection             │
│    3. TaskCreate("investigate") → spawn attacker teammate     │
│    4. TaskCreate("verify") → spawn defender + verifier         │
│    5. TaskCreate("report") → generate verdict + evidence       │
│  - Uses examples/testing/ corpus as test targets              │
│  - Controller captures full team transcripts for evidence      │
└──────────────────────────────────────────────────────────────┘
```

**Key existing infrastructure to leverage:**
- **`replay.py`** (633 LOC): Full event sourcing with `ReplayEngine`, `PoolEventStore`, `StateMismatch` tracking — DON'T rebuild this
- **`PatternEngine.run_all_patterns()`** (line 550 in `queries/patterns.py`): May already work — VERIFY before assuming broken
- **`examples/testing/`** corpus from Phase 3.1b: Use these as test targets
- **Marker format**: Router uses lowercase metadata keys (`graph_built`, `patterns_detected`, `context_loaded`, `beads_created`, `report_generated`) — align with these, don't invent uppercase constants

## Plans (5)

## Phase-Wide Strict Validation Contract (Mandatory)

No 3.2 plan can be marked complete unless all artifacts below exist for that plan ID:

1. **Machine Gate Report**: `.vrs/debug/phase-3.2/gates/<plan-id>.json`
2. **Human Checkpoint Record**: `.vrs/debug/phase-3.2/hitl/<plan-id>.md`
3. **Drift Log**: `.vrs/debug/phase-3.2/drift-log.jsonl` (append-only; required when behavior deviates from plan)

Required machine gate fields:
- `plan_id`, `target_contract`, `commands_executed[]`, `assertions[]`
- `markers_expected[]`, `markers_observed[]`, `status`
- `started_at`, `ended_at`, `duration_ms`
- `artifacts[]` with `path` + `sha256`

Required human checkpoint fields:
- `scenario_id`, `reviewer`, `steps_executed[]`
- `observed_result`, `expected_result`, `decision`, `why_decision`
- `repeatability_rating` (`fast-repeatable` / `repeatable-with-notes` / `not-repeatable`)
- `time_to_run_minutes`

## `/gsd-plan-phase` Dynamic Check Contract

For each `3.2-xx` plan, `/gsd-plan-phase` must generate investigation checks and research artifacts before coding:

1. `.vrs/debug/phase-3.2/plan-phase/derived-checks/<plan-id>.yaml`
2. `.vrs/debug/phase-3.2/plan-phase/research/<plan-id>.md`
3. `.vrs/debug/phase-3.2/plan-phase/hitl-runbooks/<scenario-id>.md`

Required references:
- `.planning/testing/PLAN-PHASE-GOVERNANCE.md`
- `.planning/testing/schemas/phase_plan_contract.schema.json`
- `.planning/testing/templates/PLAN-INVESTIGATION-CHECKS-TEMPLATE.yaml`
- `.planning/testing/templates/HITL-RUNBOOK-TEMPLATE.md`
- `.planning/testing/templates/DRIFT-RCA-TEMPLATE.md`

Rule: no hardcoded expected outcomes for findings, markers, or replay consistency. All plan checks must include derivation path and evidence sources.

## Plan Preconditions (Resolve During `/gsd-plan-phase`)

| Plan | Preconditions to Resolve | Derivation Requirement |
|---|---|---|
| 3.2-01 | Current integration breakpoints across handler/router chain | Derive breakpoints from live connectivity probes, not historical assumptions |
| 3.2-02 | Real handler input/output types from predecessor outputs | Derive signature expectations from actual chained handler execution |
| 3.2-03 | Target contract validity, marker contract, and evidence pack baseline | Derive expected marker/evidence checks from real MVP dry run artifacts |
| 3.2-04 | Non-deterministic fields and replay comparison scope | Derive filter list from two observed runs and documented variance sources |
| 3.2-05 | Vulnerable/safe control selection quality and proof-token stage map | Derive negative-control and completeness rules from corpus reality + stage inventory |

## Human-In-The-Loop Scenarios (Fast + Repeatable)

Each plan has one mandatory checkpoint designed for <= 15 minutes:

| Plan | Scenario ID | Human Steps | Pass Condition |
|---|---|---|---|
| 3.2-01 | `HITL-3.2-01-connectivity` | Review 12 integration-point before/after entries and run one manual chain call through handlers | Every reviewed point has real before/after evidence and chain call succeeds |
| 3.2-02 | `HITL-3.2-02-signature-proof` | Inspect 3 handler signature tests and one mypy output sample | All three handlers accept predecessor-produced pool objects |
| 3.2-03 | `HITL-3.2-03-mvp-proof` | Replay Unstoppable MVP run and verify marker chain + one evidence link | 9/9 required markers and evidence-linked finding are present |
| 3.2-04 | `HITL-3.2-04-replay-check` | Compare two replay outputs after filter and inspect nondeterministic field list | Filtered diff is empty and non-deterministic fields are justified |
| 3.2-05 | `HITL-3.2-05-regression-gate` | Run vulnerable + safe controls once and inspect proof-token completeness | Vulnerable has evidence-backed finding, safe has no high-confidence FP, completeness is 100% |

### 3.2-01: Re-Verify Integration Points and Fix

**IMPORTANT:** The W2-E2E report identified 10 break points (not 12 exactly). Before fixing, re-verify which are still broken — Phase 1 and 2 may have already fixed some.

**Step 1: Re-verify each break point**
- Stage 4 (Pattern Detection): `PatternEngine.run_all_patterns()` EXISTS at line 550 — verify if it actually works
- Stage 4 (Handlers): `DetectPatternsHandler` may have been partially fixed in Phase 1 (PatternEngine API fix)
- Stage 5 (Agent Spawning): `SpawnAttackersHandler`, `SpawnDefendersHandler` — verify import paths
- Stage 6 (Debate): `DebateOrchestrator` — verify signature

**Step 2: Fix only confirmed-broken points**

**Exit gate:** All integration points pass connectivity tests. Number of fixes documented (may be < 12 if some already work).

#### Reasoning

The pipeline has 12 handler-to-handler transitions (BUILD_GRAPH through COMPLETE, plus MergeResults and ResolveConflicts) and every seam between them is an untested assumption. This plan is sequenced first because no downstream work (handler fixes, MVP run, replay, E2E) can succeed if the pipeline skeleton itself is broken. It embodies the milestone 6.0 "prove everything" philosophy by requiring before/after connectivity evidence per integration point rather than trusting architectural diagrams.

#### Expected Outputs

- **Modified:** `src/alphaswarm_sol/orchestration/handlers.py` -- fixes to handler input/output contracts at each seam
- **Modified:** `src/alphaswarm_sol/orchestration/router.py` -- fixes to routing transitions that fail connectivity
- **Created:** `tests/integration/test_pipeline_connectivity.py` -- 12 parametrized tests, one per integration point
- **Created:** `.vrs/debug/phase-3.2/integration-point-evidence.json` -- before/after evidence for all 12 points
- **Metric:** 12/12 integration points pass connectivity test (no partial credit)
- **Metric:** Zero `ImportError` or `AttributeError` when walking the full handler chain
- **State change:** Pool can transition through all statuses (INTAKE -> CONTEXT -> BEADS -> EXECUTE -> VERIFY -> INTEGRATE -> COMPLETE) without manual intervention

#### Testing Strategy

| Output | Verification Method 1 | Verification Method 2 |
|--------|----------------------|----------------------|
| 12 connectivity tests pass | `pytest tests/integration/test_pipeline_connectivity.py -v` -- all 12 green | Manual: instantiate `create_default_handlers()`, call each handler in sequence with a real `Pool` object, verify `PhaseResult.success == True` |
| No import errors in handler chain | `python -c "from alphaswarm_sol.orchestration.handlers import create_default_handlers"` succeeds | `pytest --collect-only tests/integration/` reports 12 test items collected with zero collection errors |
| Before/after evidence JSON | JSON schema validation against `schemas/integration-point-evidence.schema.json` | Diff check: every integration point ID appears in both `before` and `after` sections, `after.success == True` |
| Full status transition | Single test that walks Pool from INTAKE to COMPLETE via Router, asserting each transition | `route_pool()` returns non-WAIT action for each intermediate status, and WAIT or COMPLETE for terminal |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|-------------------|-------------------|-------------|
| All 12 points tested individually | Test file has < 12 test functions or uses a single loop without per-point assertions | CI gate: `pytest --collect-only` must report exactly >= 12 test items in `test_pipeline_connectivity.py` |
| Tests use real handler instances, not mocks | Test imports `Mock` or `MagicMock` for handler objects | Grep guard in CI: `grep -c "Mock.*Handler" tests/integration/test_pipeline_connectivity.py` must return 0 |
| Before/after evidence is captured, not fabricated | Evidence JSON `timestamp` values are identical or < 1ms apart | Enforce: `after.timestamp - before.timestamp >= 10ms` per integration point |
| Only 3 of 12 points are actually tested (partial coverage) | Test count is 12 but 9 are `@pytest.mark.skip` or `pass` body | CI: no `skip` markers allowed in this file; body of each test must contain at least one `assert` |

---

### 3.2-02: Fix Handler API Mismatches

Fix DetectPatterns, CreateBeads, SpawnAttackers handler APIs.

**Exit gate:** Each handler can be called with correct signatures.

#### Reasoning

Phase 3.2-01 fixes connectivity (can data flow between handlers?) but does not guarantee that each handler's internal API -- its expected argument types, return shapes, and metadata keys -- matches what the router and downstream handlers actually pass. This plan is sequenced second because the integration tests from 3.2-01 will surface the specific signature mismatches that need fixing here. The "prove everything" philosophy requires type-level verification: each handler must be callable with the types the pipeline actually produces, not just the types its docstring claims.

#### Expected Outputs

- **Modified:** `src/alphaswarm_sol/orchestration/handlers.py` -- `DetectPatternsHandler`, `CreateBeadsHandler`, `SpawnAttackersHandler` signatures aligned with actual caller types
- **Created:** `tests/unit/test_handler_signatures.py` -- per-handler callable tests with correct types
- **Metric:** All 3 target handlers callable with `Pool` objects produced by predecessor handlers (not hand-constructed test pools)
- **Metric:** `mypy src/alphaswarm_sol/orchestration/handlers.py` reports zero type errors for the 3 fixed handlers
- **State change:** `DetectPatternsHandler` accepts graph output from `BuildGraphHandler`; `CreateBeadsHandler` accepts match metadata from `DetectPatternsHandler`; `SpawnAttackersHandler` accepts bead IDs from `CreateBeadsHandler`

#### Testing Strategy

| Output | Verification Method 1 | Verification Method 2 |
|--------|----------------------|----------------------|
| DetectPatternsHandler signature | Unit test: build graph via `BuildGraphHandler`, pass resulting `Pool` to `DetectPatternsHandler`, assert `PhaseResult.success` | Type check: `mypy --strict` on handler call site with real Pool type |
| CreateBeadsHandler signature | Unit test: run pattern detection, pass resulting `Pool` (with `metadata["matches"]`) to `CreateBeadsHandler`, assert beads created | Inspect `pool.metadata["matches"]` schema matches what `CreateBeadsHandler._create_bead()` expects |
| SpawnAttackersHandler signature | Unit test: create beads, pass resulting `Pool` (with `bead_ids`) to `SpawnAttackersHandler`, assert non-empty `processed` list | `isinstance` checks on `_build_agent_context()` return value against `AttackerAgent.analyze()` expected input |
| No test expectation drift | Tests assert handler output structure, not hardcoded values | Review: test assertions reference `PhaseResult` fields (`success`, `artifacts`), never string-match on error messages |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|-------------------|-------------------|-------------|
| Fix handlers to match callers, not callers to match handlers | Git diff shows changes only in test files, not in `handlers.py` | Review gate: `handlers.py` must have non-zero diff; tests-only changes are rejected |
| Test expectations match the real pipeline contract | Test creates a `Pool` with hand-picked metadata instead of using predecessor handler output | Enforce: each test must call the predecessor handler to produce its input Pool (chain test pattern) |
| All 3 handlers fixed, not just 1 | Commit message says "fix handlers" but only 1 handler changed | CI: test file must contain at least 3 test functions, one per handler |
| Type errors actually resolved | `mypy` run is skipped or only covers unrelated files | CI gate: `mypy src/alphaswarm_sol/orchestration/handlers.py` must be in the check pipeline |

---

### 3.2-03: Run MVP Pipeline on DVDeFi Challenge #1 (Unstoppable)

```text
build-kg contract.sol -> query patterns -> create beads -> simple verdict
```

**Exit gate:** Pipeline completes without errors on Unstoppable challenge and emits required markers.

#### Reasoning

This is the moment of truth: the first real-world audit run on a non-trivial vulnerable contract. DVDeFi Unstoppable (`examples/damm-vuln-defi/src/unstoppable/UnstoppableVault.sol`) is specifically chosen because it contains a flash loan vault with a known accounting invariant bug -- complex enough to validate the pipeline beyond toy contracts, yet well-documented enough to have a ground truth for validation. This plan is sequenced after handler fixes (3.2-01, 3.2-02) because the pipeline must be structurally sound before we can trust its output on a real contract. Running on SimpleToken.sol or a trivial contract would prove nothing.

#### Expected Outputs

- **Created:** `tests/e2e/test_mvp_unstoppable.py` -- E2E test that runs the full MVP pipeline on UnstoppableVault.sol
- **Created:** `.vrs/debug/phase-3.2/unstoppable-transcript.json` -- full pipeline transcript with all 9 markers
- **Metric:** All 9 required markers emitted: `[PREFLIGHT_PASS]`, `[GRAPH_BUILD_SUCCESS]`, `[CONTEXT_READY]`, `[TOOLS_COMPLETE]`, `[DETECTION_COMPLETE]`, `TaskCreate(task-id)`, `TaskUpdate(task-id, verdict)`, `[REPORT_GENERATED]`, `[PROGRESS_SAVED]`
- **Metric:** Pipeline wall-clock duration > 5 seconds (real execution, not mocked)
- **Metric:** At least 1 finding with `severity >= medium` linked to a graph node in UnstoppableVault
- **State change:** First successful audit run recorded; `.vrs/validation/runs/` contains a valid evidence pack

#### Testing Strategy

| Output | Verification Method 1 | Verification Method 2 |
|--------|----------------------|----------------------|
| 9/9 markers emitted | Parse transcript JSON, assert each of the 9 marker strings present | Transcript validator (Phase 3.1-04) run on the transcript file returns zero missing markers |
| Duration > 5 seconds | `manifest.json` field `duration_ms > 5000` | Python `time.monotonic()` wrapper around pipeline call in test, assert `elapsed > 5.0` |
| Finding linked to graph node | Finding evidence items contain `graph_node_id` values that exist in built graph `nodes` | Cross-reference: each `evidence_item["graph_node_id"]` resolves via `graph.nodes[graph_node_id]` to a function in `UnstoppableVault.sol` |
| Contract is UnstoppableVault, not SimpleToken | Test hardcodes path `examples/damm-vuln-defi/src/unstoppable/UnstoppableVault.sol` | Transcript contains `UnstoppableVault` in graph build output; no `SimpleToken` string present |
| Evidence pack created | `.vrs/validation/runs/<run_id>/manifest.json` exists and passes JSON schema validation | `EvidencePackBuilder.validate()` returns True on the generated pack |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|-------------------|-------------------|-------------|
| Run on DVDeFi Unstoppable, not a trivial contract | Test path contains `SimpleToken`, `tests/contracts/`, or any non-DVDeFi path | Grep guard: test file must contain `unstoppable/UnstoppableVault.sol`; must NOT contain `SimpleToken` |
| Markers are emitted by real pipeline stages, not injected | All 9 markers appear with identical timestamps or within < 100ms | Enforce: markers must have monotonically increasing timestamps with at least 100ms between first and last |
| Duration reflects real execution | `duration_ms < 5000` in manifest | Hard gate: test asserts `duration_ms >= 5000`; CI rejects if < 5000 |
| Finding references real graph data | `graph_node_id` is a fabricated string like `"test-node-1"` instead of a VKG-generated ID | Enforce: `graph_node_id` must match pattern `^[A-Za-z0-9_]+::\w+` (contract::function format from VKG builder) |
| Pipeline markers fabricated into transcript post-hoc | Transcript file modified timestamp is after pipeline completion timestamp | Enforce: transcript file is written during pipeline execution, not as a separate step; hash chain validates integrity |

---

### 3.2-04: Capture Transcript and Deterministic Replay

Record full pipeline execution transcript with timing and intermediate outputs, then re-run with identical inputs.

**Exit gate:** Marker chain present and deterministic replay passes (two consecutive runs with matching evidence outputs).

#### Reasoning

A pipeline that works once but produces different outputs on re-run is useless for security auditing -- findings must be reproducible or they cannot be trusted. This plan is sequenced after the MVP run (3.2-03) because we need a known-working execution to replay. The "prove everything" philosophy demands that we identify and filter every source of non-determinism (timestamps, UUIDs, random seeds) rather than pretending they do not exist. Two consecutive runs with identical filtered outputs is the minimum bar for deterministic replay.

#### Expected Outputs

- **Created:** `tests/e2e/test_deterministic_replay.py` -- runs pipeline twice, compares filtered outputs
- **Created:** `src/alphaswarm_sol/testing/replay_filter.py` -- filters non-deterministic fields (timestamps, UUIDs, run IDs) from evidence packs
- **Modified:** `.vrs/debug/phase-3.2/replay-evidence.json` -- side-by-side comparison of two runs
- **Metric:** Graph hash identical between Run 1 and Run 2 (SHA256 of serialized graph, excluding metadata timestamps)
- **Metric:** Filtered evidence pack diff is empty (zero differences after filtering declared non-deterministic fields)
- **Metric:** All declared non-deterministic fields are documented in `replay_filter.py` with justification
- **State change:** Deterministic replay capability established; future regressions detectable by re-running the same test

#### Testing Strategy

| Output | Verification Method 1 | Verification Method 2 |
|--------|----------------------|----------------------|
| Graph hash identity | `SHA256(run1_graph_json) == SHA256(run2_graph_json)` computed in test | `load_graph()` both graphs, compare `len(nodes)`, `len(edges)`, and sorted node ID lists |
| Filtered evidence diff is empty | `json_diff(filter(run1_evidence), filter(run2_evidence)) == {}` | Line-by-line `difflib.unified_diff` on filtered JSON produces zero diff lines |
| Non-deterministic fields declared | `replay_filter.py` contains explicit `NONDETERMINISTIC_FIELDS` list | Review: every field in the list has a comment explaining why it is non-deterministic |
| Two actual runs executed | Test contains two separate pipeline invocations | `replay-evidence.json` contains `run1_id` and `run2_id` that are different UUIDs |
| Replay filter does not over-filter | Filter list has < 20 field paths | Review: no `*` wildcards or `**` globs that could suppress real differences |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|-------------------|-------------------|-------------|
| Compare ALL outputs, not a cherry-picked subset | Test only compares graph hash, ignoring findings, verdicts, or evidence packs | Enforce: test must compare at least 4 output categories: graph, findings, verdicts, evidence pack manifest |
| Non-deterministic fields are declared, not silently ignored | Diff tool is configured to ignore all differences (trivially passes) | Enforce: `NONDETERMINISTIC_FIELDS` list must be frozen in test; any addition requires explicit justification |
| Two real runs, not one run copied | `run1_id == run2_id` or outputs are byte-identical including timestamps | Enforce: timestamps must differ between runs; run IDs must differ; only filtered outputs match |
| Graph hash is computed on the full graph, not a subset | Hash computed on `len(nodes)` only instead of full serialization | Enforce: hash input is `json.dumps(graph.to_dict(), sort_keys=True)`, not a derived summary |

---

### 3.2-05: Create E2E Regression + Negative Control

Create automated test that runs the full pipeline and verifies output for vulnerable and safe controls.

**Exit gate:** Vulnerable run produces evidence-linked finding, safe run produces no high-confidence false positive, and proof-token completeness is 100%.

#### Reasoning

A security tool that only finds vulnerabilities is half-tested -- it must also provably NOT find vulnerabilities in safe code. This plan creates the permanent regression gate that all future changes must pass. It is sequenced last in Phase 3.2 because it requires everything before it: fixed integration (3.2-01), fixed handlers (3.2-02), working MVP (3.2-03), and deterministic replay (3.2-04). The negative control is the hardest part: the safe contract must be strong enough that any tool could plausibly flag it, so that a clean result actually means something. The "prove everything" philosophy requires that any high-confidence finding on the safe contract is treated as a test failure, not a "maybe."

#### Expected Outputs

- **Created:** `tests/e2e/test_e2e_regression.py` -- dual-run test: vulnerable contract + safe control
- **Metric (vulnerable run):** At least 1 finding with `confidence >= likely` and non-empty `evidence_refs` list linking to graph node IDs
- **Metric (safe run):** Zero findings with `confidence >= likely` (any high-confidence FP = test failure)
- **Metric:** Proof-token completeness = 100% (every pipeline stage has a valid proof token)
- **Metric (vulnerable):** Every evidence item `graph_node_id` resolves to a function in the target contract (not a library or interface)
- **State change:** Permanent regression gate established; CI blocks merge if either the vulnerable or safe run fails

#### Testing Strategy

| Output | Verification Method 1 | Verification Method 2 |
|--------|----------------------|----------------------|
| Vulnerable contract produces evidence-linked finding | Assert `len(findings) >= 1` and `findings[0]["evidence_refs"]` is non-empty list | Cross-reference: each `evidence_ref` ID exists in the evidence pack manifest |
| Safe contract produces zero high-confidence FP | Assert `all(f["confidence"] < "likely" for f in findings)` | Count findings by confidence: `confirmed=0, likely=0` (uncertain and rejected are allowed) |
| Proof-token completeness 100% | `ProofTokenCollector.completeness()` returns `1.0` for both runs | Manual: count proof tokens in evidence pack, compare against expected stage count (9 stages) |
| Finding references real contract function | `evidence_item["graph_node_id"]` matches a node whose `source_file` ends in target contract name | `graph.nodes[evidence_item["graph_node_id"]].properties["file_path"]` does not contain `lib/` or `interface/` |
| Safe contract is genuinely safe (not trivially unflaggable) | Safe contract contains ERC20 transfers, access control, external calls (non-trivial surface) | Code review: safe contract has >= 5 functions and >= 3 semantic operations from VKG taxonomy |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|-------------------|-------------------|-------------|
| Safe contract is strong negative control | Safe contract is < 20 lines, has no external calls, or is an empty interface | Enforce: safe contract must have >= 5 functions, >= 100 LOC, and use `load_graph()` to produce a graph with >= 10 nodes |
| High-confidence FP is a test failure, not a warning | Test logs FP but does not fail (`assert` replaced with `print`) | CI: test must contain `assert` on the safe-run finding count; `pytest` exit code must be non-zero on FP |
| Proof-token completeness is real, not stubbed | `completeness()` is mocked to return 1.0 | Grep guard: test file must not mock `ProofTokenCollector`; completeness must be computed from actual proof files |
| Vulnerable finding is evidence-linked, not naked | Finding has `confidence >= likely` but `evidence_refs` is `[]` or `None` | Enforce: test asserts `len(finding["evidence_refs"]) >= 1`; empty evidence = test failure regardless of confidence |
| Counting low-confidence findings as negatives to inflate safe-run pass rate | Safe run has findings but all are `uncertain` -- and the test counts this as "no findings" | Enforce: test explicitly logs all findings on safe run at any confidence level; only `confirmed` and `likely` are the failure threshold, but `uncertain` findings are reported for review |

---

## Hard Delivery Gates for Phase 3.2 (Added 2026-02-10)

Phase 3.2 is where "first working audit" becomes "first defensible audit". These gates are mandatory sub-gates on top of plans `3.2-03` through `3.2-05`.

### HDG-04: Evidence Provenance Lock (Sub-gate on 3.2-03 and 3.2-05)

**Why this is critical**
- A finding is not auditable unless it can be traced from verdict to graph node to source span to tool output.
- This gate prevents narrative-only findings and forces every claim to carry provenance.

**Implementation contract**
- Require these fields on every `confirmed` or `likely` finding (or evidence item linked to the finding):
  - `graph_node_id` (non-empty on each evidence item)
  - `source_location` (`file`, `start_line`, `end_line`)
  - `tool_output_hashes` (hashes of raw tool outputs used by the claim)
  - `evidence_pack_id`
  - `transcript_hash`
- Add `validate_provenance_lock.py` in `src/alphaswarm_sol/testing/` and run it inside `test_e2e_regression.py`.
- Persist validation artifacts to `.vrs/debug/phase-3.2/provenance-lock.json`.

**Hard validation**
- Any `confirmed` or `likely` finding missing one required field fails the run immediately.
- Hashes must recompute exactly from referenced raw artifacts.
- Every `graph_node_id` must resolve in the run graph; dangling node references are hard failures.

**Expected strict result**
- 100% of reportable findings become reproducible, hash-linked evidence objects.

### HDG-01: Exploit-or-it-didn't-happen (Sub-gate on 3.2-03 and 3.2-05)

**Why this is critical**
- High-confidence security claims without exploit traces are indistinguishable from plausible speculation.
- This gate forces proof of exploitability, not only pattern matching.

**Implementation contract**
- For every `severity in {high, critical}` finding, attach `exploit_trace`:
  - ordered call sequence
  - pre-state assumptions
  - attacker actions
  - post-state violation
  - expected economic delta (if applicable)
- Store traces in `.vrs/debug/phase-3.2/exploit-traces/<finding-id>.json`.
- Add runner `tests/e2e/test_exploit_replay.py` that replays each trace against vulnerable target.

**Hard validation**
- Replay must reproduce the declared violation at least 2/2 times on identical inputs.
- Trace execution that cannot reproduce the violation downgrades finding to `uncertain` and fails this gate for `high/critical`.
- Trace must point to the exact finding ID and evidence pack used in the report.

**Expected strict result**
- No high/critical claim survives without a replayable exploit trace.

### HDG-02: Patch-and-Retest (Sub-gate on 3.2-05)

**Why this is critical**
- Real security value is demonstrated when a minimal fix kills the exploit without breaking core behavior.
- This gate avoids "found bug" claims that do not survive patch validation.

**Implementation contract**
- For each exploit-backed high/critical finding:
  - produce `patch.diff` (minimal remediation)
  - rerun exploit trace on patched target (must fail to exploit)
  - run core functional smoke tests (must still pass)
- Persist artifacts:
  - `.vrs/debug/phase-3.2/patch-retest/<finding-id>/patch.diff`
  - `.vrs/debug/phase-3.2/patch-retest/<finding-id>/pre.json`
  - `.vrs/debug/phase-3.2/patch-retest/<finding-id>/post.json`

**Hard validation**
- Exploit succeeds pre-patch and fails post-patch for the same trace inputs.
- Functional smoke checks remain green post-patch.
- If patch kills exploit but breaks core behavior, finding is marked `needs-human-review` and gate fails.

**Expected strict result**
- Every critical vulnerability report includes evidence that remediation is both effective and non-destructive.

## Required Marker Contract

**IMPORTANT:** The router uses lowercase metadata keys in `pool.metadata`, NOT uppercase constants. Align with existing format:

| Router Metadata Key | Pipeline Stage | What It Proves |
|---|---|---|
| `graph_built` | INTAKE → CONTEXT | Graph construction completed |
| `context_loaded` | CONTEXT phase | Protocol context loaded |
| `patterns_detected` | CONTEXT → BEADS | Pattern matching ran |
| `beads_created` | BEADS phase | Vulnerability beads generated |
| `report_generated` | INTEGRATE → COMPLETE | Final report produced |

Additional markers (from task lifecycle):
- `TaskCreate(task-id)` — Task created for pipeline stage
- `TaskUpdate(task-id, verdict)` — Task completed with verdict
- `pool.status` transitions: INTAKE → CONTEXT → BEADS → EXECUTE → VERIFY → INTEGRATE → COMPLETE

## MVP Pipeline

```text
build-kg contract.sol → query patterns → create beads → simple verdict
```

**Test targets:** Use `examples/testing/` corpus from Phase 3.1b (known ground truth) in addition to DVDeFi Unstoppable.

## Key Files

- `src/alphaswarm_sol/orchestration/router.py` — Pipeline router (routes based on pool.metadata markers)
- `src/alphaswarm_sol/orchestration/handlers.py` — Pipeline handlers (17 handlers, 1,489 lines)
- `src/alphaswarm_sol/queries/patterns.py` — Pattern engine (`run_all_patterns()` at line 550)
- `src/alphaswarm_sol/kg/builder/` — Graph builder (WORKS TODAY)
- `src/alphaswarm_sol/orchestration/replay.py` — Replay engine (633 LOC, event sourcing — USE THIS, don't rebuild)

## Success Criteria

1. All confirmed-broken integration points fixed (re-verify before assuming all 12 broken)
2. Handler APIs match expected signatures
3. MVP pipeline completes on DVDeFi Unstoppable
4. Full transcript captured with markers (lowercase metadata keys)
5. Deterministic replay gate passes using existing `replay.py` infrastructure
6. Negative control gate passes (safe contract from `examples/testing/`)
7. HDG-04 provenance lock passes for all reportable findings
8. HDG-01 exploit traces are replayable for all high/critical findings
9. HDG-02 patch-and-retest passes for all high/critical findings

## Debug/Artifact Contract

- Any failure writes `.vrs/debug/phase-3.2/repro.json`.
- Repro includes input contract hash, command sequence, marker diff, and evidence diff summary.

## Cross-Phase: Failure Handling & Regression Protocol

### On Test Failure
- Controller captures: failure details, handler output, pool state, marker chain
- Environment preserved at `.vrs/debug/phase-3.2/failures/{plan}-{timestamp}/`
- Include handler input/output types for debugging API mismatches

### Anti-Fabrication Rules
- Pipeline wall-clock duration > 5 seconds (real execution)
- At least 1 finding with `severity >= medium` on vulnerable contract
- Safe contract: zero findings with `confidence >= likely`
- Proof-token completeness = 100% (every stage has valid proof token)
- Markers must have monotonically increasing timestamps with >= 100ms between first and last
- High/critical findings require replayable exploit traces (HDG-01)
- High/critical findings require patch-and-retest artifacts (HDG-02)
- Confirmed/likely findings require full provenance lock fields and hash checks (HDG-04)

## 2026-02-09 Reordering Audit Context

### Global Sequence

Execution order after Phase 2.1 is now fixed:
`3.1 → 3.1b → 3.2 → 4 → 4.1 → 6 → 7 → 5 → 8`

### Iteration Notes (1 → 4)

1. Iteration 1: first-working-audit target was valid but lacked replay/negative-control rigor.
2. Iteration 2: introduced deterministic replay and artifact schema expectations.
3. Iteration 3: strict review required hard replay and safe-control gates before any downstream debate/benchmark work.
4. Iteration 4: Phase 3.1b inserted before 3.2 — harness provides systematic verification. Phase 3.2 now uses `examples/testing/` corpus and controller for E2E capture.

### This Phase's Role

Phase 3.2 is the proof-of-reality gate that converts architecture claims into one reproducible audit run. It benefits from Phase 3.1b's harness for systematic regression testing and corpus for ground truth comparison.

### Key Investigation Findings (from parallel agents)

- **PatternEngine API confusion:** W2-E2E report claims `run_all_patterns()` doesn't exist, but it DOES exist at line 550 in `queries/patterns.py`. May be an import path issue, not a missing function.
- **Handler system:** 17 handlers exist (1,489 LOC) but have never successfully executed end-to-end
- **Replay infrastructure:** Fully built (633 LOC) with event sourcing, deterministic reconstruction, validation — DO NOT rebuild
- **DVDeFi Unstoppable:** 148 lines, ERC4626 vault with known flash loan accounting bug (line 85)
- **Marker format:** Router uses lowercase metadata keys, not uppercase constants — align with existing format

### Assigned Research Subagent

- `vrs-verifier` for deterministic replay and evidence-gate adjudication

## Research

- `.planning/new-milestone/reports/w2-e2e-pipeline-plan.md`
- `docs/PHILOSOPHY.md`
- https://arxiv.org/abs/2601.06112
- Phase 3.2 assumption verification (parallel agent investigation, 2026-02-09)

## Phase 3.1c Dependency: Reasoning-Based Evaluation (2026-02-11)

Phase 3.2 is evaluated by the 3.1c testing framework (12 plans) which provides capability + reasoning evaluation for the audit workflow, not just output checking. Phase 3.1c sits between 3.1b and 3.2 in the critical path.

### How 3.1c Evaluates Audit Quality

When the MVP pipeline runs on DVDeFi Unstoppable (plan 3.2-03), the reasoning evaluation framework provides:

1. **Hook Observability**: PreToolUse and PostToolUse hooks log all graph queries, tool calls, and their results in `.vrs/observations/{session_id}.jsonl`
2. **Graph Value Score**: Mechanical scoring of whether graph queries in the audit pipeline informed findings (not just checkbox compliance)
3. **Reasoning Assessment**: LLM evaluator judges the quality of analysis beyond "did it find the bug" — assesses evidence grounding, reasoning depth, and novel insight
4. **Evaluation Contract**: `tests/workflow_harness/contracts/workflows/vrs-audit.yaml` defines what "good audit performance" looks like

### Impact on Phase 3.2 Plans

| Plan | 3.1c Enhancement |
|---|---|
| 3.2-03 (MVP run) | Hook observations validate graph-first behavior; GVS measures graph utilization |
| 3.2-04 (Deterministic replay) | Observation logs provide additional determinism validation data |
| 3.2-05 (Regression + negative control) | Reasoning evaluator adds quality dimension beyond pass/fail |

### Updated Execution Sequence

`3.1 → 3.1b → 3.1c → 3.2 → 4 → 4.1 → 6 → 7 → 5 → 8`

Phase 3.2 benefits from 3.1c's evaluation infrastructure but is NOT blocked by it for core pipeline functionality. The evaluation framework adds quality measurement ON TOP of the existing deterministic gates.
