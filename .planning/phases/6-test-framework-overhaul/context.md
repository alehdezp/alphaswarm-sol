# Phase 6: Test Framework Overhaul

## Goal

Shift the test portfolio toward behavior-validating, live, evidence-producing tests that directly protect the product's audit workflow.

## Why This Phase Exists

The suite is large, but too much of it validates implementation details or mock behavior instead of end-to-end outcomes.

## Critical Gaps to Close

1. E2E tests are still partially mock/skeleton instead of live pipeline validation.
2. Orchestration marker checks are not first-class in tests.
3. Evidence-pack completeness is not consistently asserted in test outputs.
4. Mock-heavy tests still consume substantial maintenance while adding low confidence.

## Dependencies

- Phase 3.2 complete for one real audit flow.
- Phase 4 debate flow available for multi-agent validation paths.
- Phase 4 debate-path workflows identified so coverage requirements include every workflow/agent/skill actually used by `/vrs-audit`.

## Design Principle: Tests As Early As Possible (But Artifact-Real)

Move tests to the earliest possible step in the pipeline **without** faking core artifacts. The rule is:

- Tests may start early, but **must consume real pipeline artifacts** (graph, tool outputs, detection outputs, evidence packs, transcripts).
- No mocks for core audit artifacts; mocks only at true external boundaries (network/LLM).

**Minimum real artifacts for Phase 6 tests:**
- Graph build output + hash
- Tool outputs (Slither/Aderyn) normalized to SARIF
- Pattern detection results (Tier A/B/C)
- Orchestration transcript markers
- Evidence packets with node IDs + code locations

## Key Files

- `tests/e2e/test_full_audit.py`
- `tests/e2e/test_audit_pipeline.py`
- `tests/test_benchmark_validation.py`
- `src/alphaswarm_sol/testing/`
- `docs/reference/testing-framework.md`
- `docs/reference/graph-usage-metrics.md`

## Plans (Reordered, Test-First)

### 6-01: Build Live Test Harness and Contracts

- Add failing tests for required run artifacts and orchestration markers.
- Make harness fail if run is mock-only in audit mode.

#### Reasoning

The live test harness is the foundation all other Phase 6 plans depend on. Without a harness that enforces real artifact production and rejects mock-only runs, subsequent E2E and regression tests have no trustworthy execution environment. This must be built and gated first so that every downstream test inherits artifact-real guarantees.

#### Expected Outputs

- `tests/harness/live_harness.py` — Harness class that orchestrates contract build, graph construction, and detection with real artifacts
- Pytest fixtures exposing `live_harness` and `harness_contract` for downstream tests
- Assertion helpers: `assert_artifacts_real()`, `assert_markers_present()`, `assert_not_mock_only()`
- Gate check that raises `HarnessViolation` if any core artifact is a `MagicMock` instance
- At least 3 failing tests (red) that define the harness contract before implementation

#### Testing Strategy

| Output | Method 1 | Method 2 |
|--------|----------|----------|
| Harness rejects mock-only runs | Feed `MagicMock()` graph node, assert `HarnessViolation` raised | Run harness with `audit_mode=True` and no real contracts, assert failure |
| Required artifacts produced | Check `.vrs/testing/` for graph hash, SARIF, evidence files after harness run | Assert `load_graph()` returns non-empty graph with expected node types |
| Orchestration markers emitted | Grep harness transcript for all 9 markers (`[PREFLIGHT_*]` through `[REPORT_GENERATED]`) | Validate marker sequence ordering via `TranscriptValidator` |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|-------------------|-------------------|-------------|
| Graph nodes come from `load_graph()` on real `.sol` files | Tests use `MagicMock()` for graph nodes or `patch('builder.build')` returning fake data | CI gate: scan test files for `MagicMock` applied to graph/builder classes; BLOCK if found |
| Harness fails when artifacts are absent | `HarnessViolation` exception removed or caught silently | Pre-commit hook validates `HarnessViolation` is raised in at least 3 tests |
| Audit mode requires real pipeline | `audit_mode` flag ignored or defaulted to `False` | Harness `__init__` asserts `audit_mode=True` in CI; config cannot override |

### 6-02: Add Five Live E2E Tests First

- Contract -> graph -> detection -> bead -> verdict path.
- Assert markers and evidence pack completeness.

#### Reasoning

Five live E2E tests establish the minimum viable proof that the full audit pipeline works end-to-end on real contracts. Each test exercises the complete path from Solidity source through graph construction, detection, bead creation, and verdict generation. This is the single most important coverage milestone because it proves the product actually works, not just that individual units pass.

#### Expected Outputs

- 5 test functions in `tests/e2e/test_live_audit_e2e.py`, each targeting a distinct vulnerability class
- Contract selection: at least 2 from `tests/contracts/` (existing), at least 1 from DamnVulnerableDeFi-style, at least 1 synthetic minimal case, at least 1 safe contract (true negative)
- Each test asserts: all 9 orchestration markers present, evidence pack with >= 1 node ID + code location, bead created with correct status, verdict field non-empty
- Per-test transcript saved to `.vrs/testing/e2e/<test_name>/transcript.json`
- Evidence pack validator confirms `MIN_DURATION_MS` threshold met

#### Testing Strategy

| Output | Method 1 | Method 2 |
|--------|----------|----------|
| Full pipeline execution | Run contract through harness, assert verdict is `CONFIRMED` or `SAFE` (not `ERROR`) | Compare output against known-good baseline for each contract |
| All 9 markers present | `TranscriptValidator.assert_markers(transcript, REQUIRED_MARKERS)` | Parse transcript JSON, assert set difference with required markers is empty |
| Evidence pack completeness | `EvidencePackBuilder.validate()` returns no errors | Assert pack contains `node_ids`, `code_locations`, `operation_sequences` fields, all non-empty |
| Bead lifecycle correct | Assert bead transitions: `CREATED -> INVESTIGATED -> VERDICT` | Query bead store, verify timestamp ordering and status progression |
| True negative contract passes clean | Run safe contract, assert zero findings with severity >= MEDIUM | Verify evidence pack is empty or contains only INFO-level notes |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|-------------------|-------------------|-------------|
| Tests exercise full pipeline (contract to verdict) | Tests skip detection or bead creation steps; assertions only on graph build | CI: each E2E test must assert on `verdict` field; BLOCK if missing |
| Contracts are non-trivial and representative | All 5 tests use single-function trivial contracts (< 20 LOC) | Review gate: contract complexity check; at least 3 contracts have cross-function interactions |
| True negative included | All 5 tests expect findings (no false-positive testing) | CI: at least 1 test must assert zero high-severity findings |
| Duration reflects real work | Tests complete in < 1 second (indicates skipped steps) | Assert `elapsed_ms >= MIN_DURATION_MS` (5000ms) per test |

### 6-03: Add Twenty Detection Regressions

- Prioritize high-impact categories with TP and TN cases.
- Include rename-resistance and cross-function cases.

#### Reasoning

Twenty detection regression tests lock in the behavioral contract for pattern detection across the most impactful vulnerability categories. By requiring both true-positive and true-negative cases, rename-resistance variants, and cross-function reasoning, these tests ensure detection quality cannot silently degrade. This is the broadest coverage layer and the primary defense against detection regressions during refactoring.

#### Expected Outputs

- 20 test functions in `tests/detection/test_detection_regressions.py` (or split by category)
- Coverage: at least 5 vulnerability categories (reentrancy, access control, oracle manipulation, flash loan, price manipulation)
- Distribution: minimum 12 TP cases, minimum 5 TN cases, minimum 3 rename-resistance variants
- Each test uses `load_graph(contract_name)` on real `.sol` files from `tests/contracts/`
- Each test produces an evidence packet with graph node IDs linked to detection results
- At least 3 cross-function tests where the vulnerability spans multiple functions or contracts
- `PatternTestFramework` used for consistent assertion patterns and metric collection
- Aggregate metrics: `precision()`, `recall()`, `f1()` computed across all 20 tests

#### Testing Strategy

| Output | Method 1 | Method 2 |
|--------|----------|----------|
| TP detection correctness | Run detection on vulnerable contract, assert finding matches expected category and location | Cross-check against `PatternTestFramework.expected_findings` baseline |
| TN detection correctness | Run detection on safe contract variant, assert zero findings for that category | Run on renamed-safe variant (guards present), confirm no false alarm |
| Rename resistance | Rename key functions/variables in vulnerable contract, re-run detection, assert same findings | Use `PatternTestFramework.rename_variant()` to auto-generate renamed contracts and assert parity |
| Cross-function detection | Provide contract where vulnerability spans `contractA.deposit()` -> `contractB.withdraw()`, assert detection traces both | Assert evidence packet contains node IDs from multiple functions/contracts |
| Aggregate metrics meet threshold | `precision() >= 0.70`, `recall() >= 0.50` across all 20 tests | `CategoryMetrics` per-category breakdown shows no category below 0.50 precision |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|-------------------|-------------------|-------------|
| Graph built from real contracts via `load_graph()` | `MagicMock()` used for graph internals; `patch` applied to builder | CI: grep test files for `MagicMock` on graph/node classes; BLOCK if found |
| Both TP and TN cases present | All 20 tests are TP (no false-positive testing) | CI: count tests with `assert_no_findings`; BLOCK if fewer than 5 TN tests |
| Rename-resistance tests included | All tests use original function names only | CI: at least 3 test names contain `rename` or `semantic_equiv`; BLOCK otherwise |
| Metrics are real, not perfect | `precision() == 1.0 AND recall() == 1.0` across all categories | 100%/100% triggers automatic fabrication investigation per cross-phase invariant |

### 6-04: Audit Existing Tests with Signal Score

- Sample and classify tests by behavior signal and maintenance cost.
- Rank rewrite/delete candidates by impact.

#### Reasoning

Before rewriting tests, we need an honest assessment of what the current suite actually validates. Sampling 50 test files and classifying each as OUTCOME-testing or IMPLEMENTATION-testing produces the signal score that prioritizes rewrite effort. Without this audit, we risk rewriting tests that were already fine or ignoring the worst offenders. The signal score is the decision input for plan 6-05.

#### Expected Outputs

- Audit report: `.vrs/testing/audit/test-signal-score.json` containing 50 classified test files
- Per-file classification: `{file, category: OUTCOME|IMPLEMENTATION, mock_count, assertion_types, signal_score, recommendation: KEEP|REWRITE|DELETE}`
- Summary statistics: total OUTCOME vs IMPLEMENTATION count, mock ratio (mock assertions / total assertions), top-20 rewrite candidates ranked by `(mock_count * maintenance_cost) / signal_score`
- Signal score formula documented and reproducible
- Visualization-ready CSV export for trend tracking across phases

#### Testing Strategy

| Output | Method 1 | Method 2 |
|--------|----------|----------|
| Classification accuracy | Manually verify 10 random samples from the 50; confirm OUTCOME/IMPLEMENTATION label matches human judgment | Run classifier on known OUTCOME test (e.g., E2E) and known IMPLEMENTATION test (e.g., pure mock); confirm correct labels |
| Sample is representative | Verify sample covers at least 8 different test directories/modules | Statistical check: sample proportions match overall suite proportions within 15% |
| Signal score discriminates | Top-20 rewrite candidates have signal_score < 0.3; kept tests have signal_score > 0.7 | Correlation: mock_count and signal_score have negative Pearson r < -0.5 |
| Recommendations actionable | Each REWRITE recommendation includes specific mock-to-live replacement strategy | Each DELETE recommendation cites what the test was supposed to validate and why it no longer does |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|-------------------|-------------------|-------------|
| Actual 50-file sample analyzed | Report contains fewer than 50 entries or entries lack file paths | CI: validate JSON schema has exactly 50 entries with non-empty `file` fields |
| Honest classification with both categories | All 50 classified as OUTCOME (no IMPLEMENTATION found) | BLOCK if IMPLEMENTATION count < 10 (statistically implausible given known mock density) |
| Signal score computed from real metrics | `signal_score` field is hardcoded or uniform across all files | Assert standard deviation of signal_score > 0.1 across sample |
| Top-20 list actually used by 6-05 | 6-05 rewrites different files than top-20 list | Gate: 6-05 must reference at least 15 of the top-20 from this audit |

### 6-05: Rewrite/Remove Top Mock-Heavy Offenders

- Replace with live checks where feasible.
- Keep mocks only at true external boundaries.

#### Reasoning

The top-20 mock-heavy offenders identified in 6-04 consume the most maintenance effort while providing the least behavioral confidence. Rewriting them with live checks using `load_graph()`, real tool outputs, and actual detection results transforms the test suite from a maintenance burden into a safety net. The 40% mock ratio target ensures the suite as a whole shifts toward artifact-real testing while preserving legitimate boundary mocks.

#### Expected Outputs

- 20 test files rewritten (sourced from 6-04's top-20 list)
- Each rewritten test uses `load_graph()` for graph interactions instead of `MagicMock()`
- Each rewritten test asserts on behavioral outcomes (detection results, evidence packs, verdicts) not internal method calls
- Mock inventory: remaining mocks documented with justification (must be true external boundary: network, LLM API, filesystem for test isolation)
- Post-rewrite mock ratio: `mock_assertions / total_assertions < 0.40` across the audited 50-file sample
- Before/after comparison report showing signal score improvement per rewritten file

#### Testing Strategy

| Output | Method 1 | Method 2 |
|--------|----------|----------|
| Rewritten tests pass | `pytest tests/ -k "rewritten"` all green | Run full suite, confirm no regressions introduced by rewrites |
| Mock ratio below 40% | Re-run 6-04 classifier on post-rewrite suite; verify ratio | Count `MagicMock`, `patch`, `Mock()` occurrences in test files; compute ratio against total assertions |
| Live checks replace mocks | Diff before/after: `MagicMock` calls removed, `load_graph()` calls added | Each rewritten test imports from `tests/graph_cache.py` or `tests/conftest.py` fixtures |
| Signal score improved | Mean signal_score of rewritten files increases by >= 0.3 | No rewritten file has signal_score < 0.5 post-rewrite |
| Only boundary mocks remain | Grep for remaining `MagicMock`/`patch` usage; each has adjacent comment citing boundary justification | Review: remaining mocks target only `httpx`, `anthropic`, `subprocess` (network/LLM/external process) |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|-------------------|-------------------|-------------|
| Tests actually rewritten with live behavior | Tests marked `@pytest.mark.skip` instead of rewritten | CI: BLOCK if any of the 20 target files contain `@pytest.mark.skip` or `@pytest.mark.xfail` |
| Mocks removed, not relabeled | `MagicMock` still present but variable renamed to `live_graph` | CI: grep rewritten files for `MagicMock`, `Mock()`, `create_autospec` on non-boundary classes; BLOCK if found |
| 40% threshold is real | Mock ratio computed on subset excluding mock-heavy files | CI: ratio computed on full 50-file sample from 6-04; not a cherry-picked subset |
| Rewrites sourced from 6-04 top-20 | Rewritten files differ from 6-04's ranked list | Gate: file list overlap >= 15 of 20 with 6-04 output |

### 6-06: Optimize with Graph Cache

- Cache only after live harness is stable.
- Measure cache impact on median and P95 runtime.

#### Reasoning

Graph construction is the most expensive repeated operation in the test suite. Caching graph builds across test runs delivers significant speedup, but only after the live harness (6-01) and E2E tests (6-02) confirm that the cache does not mask correctness issues. This plan is intentionally last because premature caching risks hiding stale-graph bugs and invalidating test results. The cache must prove it is both fast and faithful.

#### Expected Outputs

- `tests/graph_cache.py` enhanced with persistent LRU cache (keyed on contract content hash + builder version)
- Cache invalidation logic: invalidate on contract file change, builder version bump, or Slither/Aderyn version change
- Benchmark report: `{median_ms, p95_ms, cache_hit_rate}` for both cached and uncached runs across full test suite
- Correctness proof: cached graph hash == fresh graph hash for all test contracts
- Cache size management: configurable max entries, LRU eviction, total disk budget
- Integration with `conftest.py` so `load_graph()` transparently uses cache

#### Testing Strategy

| Output | Method 1 | Method 2 |
|--------|----------|----------|
| Cache produces identical graphs | Build graph fresh and from cache; compare content hash byte-for-byte | Run detection on both cached and fresh graphs; assert identical findings |
| Speedup is real and measured | Run suite twice (cold then warm); compare median and P95 with `pytest-benchmark` or manual timing | Assert cache_hit_rate > 0.90 on second run; assert warm median < 0.5 * cold median |
| Invalidation works correctly | Modify contract source, rebuild; assert cache miss and fresh build | Bump builder version in config; assert all cache entries invalidated |
| No stale graph bugs | After cache warm, introduce new vulnerability in contract; assert detection finds it on next run | Compare cached graph node count against fresh build; assert equality |
| Disk budget respected | Fill cache to max_entries + 1; assert oldest entry evicted and total size <= budget | Assert cache directory size after full suite < configured `max_cache_mb` |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|-------------------|-------------------|-------------|
| Cache only active after harness stable | Cache enabled before 6-01 and 6-02 pass | Gate: cache activation requires 6-01 + 6-02 exit gates passed (checked in CI) |
| Speedup measured with correctness verified | Benchmark report shows speedup but no hash comparison | CI: benchmark report must contain both `speedup_ratio` and `hash_match: true` fields |
| Invalidation fires on real changes | Cache serves stale graph after contract modification | Integration test: modify contract, assert cache miss on next `load_graph()` |
| Metrics from real runs, not synthetic | Benchmark uses trivial 5-line contracts only | Assert benchmark contract set includes at least 3 contracts with > 100 LOC |

## Test Pyramid (Project-Specific)

**Top: Live E2E (small count, highest confidence)**
- 5 tests
- Full audit run on real contracts (mini DVDeFi + synthetic minimal cases)
- Must assert all orchestration markers and evidence packets

**Middle: Detection Regression (broad coverage, medium cost)**
- 20 tests (TP + TN)
- Contract -> graph -> detection -> evidence packet
- Must assert rename resistance and cross-function reasoning

**Bottom: Fault Injection (stability + recovery)**
- 10 tests (targeted)
- Simulate tool failures, partial outputs, timeout conditions
- Must assert recovery behavior and transcript markers remain coherent

## Debugging Hooks (Required)

Add structured hooks that fire during tests and attach debug artifacts:

- `[PREFLIGHT_*]`, `[GRAPH_BUILD_SUCCESS]`, `[TOOLS_COMPLETE]`, `[DETECTION_COMPLETE]`, `TaskCreate`, `TaskUpdate`, `[REPORT_GENERATED]`, `[PROGRESS_SAVED]`
- Evidence packet validator: node IDs, property IDs, code locations, operation sequences
- Graph hash + counts snapshot
- Tool versions + CLI commands executed
- Per-test transcript capture under `.vrs/testing/`

## JJ Workspace Usage (Parallel Test Waves)

- Use a **dedicated `jj` workspace per test wave**:
  - `jj workspace add phase6-e2e`
  - `jj workspace add phase6-regression`
  - `jj workspace add phase6-faults`
- Keep artifacts and transcripts isolated per workspace to avoid cross-contamination.
- Merge only after each wave passes its local gate.

## Exit Gates (Phase 6)

All gates are required and must be evidenced by test outputs:

- 5 live E2E tests passing (full artifact chain + markers)
- 20 detection regressions passing (TP + TN, evidence packets validated)
- 10 fault-injection tests passing (recovery + marker coherence)
- Existing test audit complete with signal score + top-20 rewrites or deletions
- Graph cache operational with measured median and P95 speedups
- Mock ratio below 40% in audited sample
- Coverage map proves every active workflow/agent/skill has at least one live behavior test

## Interactive Validation Method (Agent Teams + JJ Workspace)

- Use isolated `jj` workspaces for parallel test waves.
- Use attacker-defender-verifier teams for controversial regressions.
- Keep per-run transcripts, command logs, and evidence packs under `.vrs/testing/`.

## Non-Vanity Metrics

- Live-run compliance rate.
- Evidence-pack completeness rate.
- Marker coverage rate.
- Detection precision/recall on real contracts.
- Mock ratio and trend.
- Robustness under semantically equivalent prompt/query perturbations.
- Fault-tolerance recovery rate for transient tool failures in live tests.

## Recommended Subagents

- `vrs-test-conductor`
- `vrs-regression-hunter`
- `vrs-pattern-verifier`
- `vrs-secure-reviewer`
- `vrs-verifier`

## Exit Gate

Core test portfolio proves real audit behavior with high-signal metrics and reduced mock dependence.

## Research Inputs

- `.planning/new-milestone/reports/w2-test-framework-plan.md`
- `docs/reference/testing-framework.md`
- `docs/PHILOSOPHY.md`
- External: ReliabilityBench (Jan 2026) for consistency, robustness, and fault tolerance dimensions

## 2026-02-09 Reordering Audit Context

### Global Sequence

Execution order after Phase 2.1 is now fixed:
`3.1 -> 3.1b -> 3.2 -> 4 -> 4.1 -> 6 -> 7 -> 5 -> 8`

### Iteration Notes (1 -> 3)

1. Iteration 1: testing phase was valuable but insufficiently explicit about coverage of every workflow/agent/skill.
2. Iteration 2: added test pyramid, debug hooks, and artifact-real constraints.
3. Iteration 3: strict review locked phase acceptance to full workflow/agent/skill live-coverage proof.

### This Phase's Role

Phase 6 turns one successful audit path into durable system reliability by making all active behaviors testable and debuggable.

### Mandatory Carry-Forward Gates

- Marker and evidence completeness assertions in live tests.
- Fault-injection and recovery assertions.
- Workflow/agent/skill live-coverage map.

### Debug/Artifact Contract

- Any failure writes `.vrs/debug/phase-6/repro.json`.
- Repro includes workspace name, command, artifact location, and failing assertion IDs.

### Assigned Research Subagent

- `vrs-test-conductor` for test portfolio quality and coverage integrity

### Research Sources Used

- https://arxiv.org/abs/2601.06112
- https://arxiv.org/abs/2507.21504
- https://docs.jj-vcs.dev/latest/working-copy/
