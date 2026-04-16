# Phase 5: Benchmark Reality

## Goal

Produce reproducible, honest benchmark results that reflect real pipeline behavior, not YAML annotations or synthetic status flags.

## Why This Phase Exists

Current benchmark structure has scaffolding but not credible measured outcomes for GA decisions.

## Critical Gaps to Close

1. Detection-rate logic is partially annotation-driven, not fully run-driven.
2. Ground-truth completeness and provenance need strict enforcement.
3. False-positive measurement on safe sets is underused in release gating.
4. DVDeFi scope consistency (focused subset vs full suite) must be explicit.
5. Ablation claims require executable no-graph comparison path and evidence.

## Dependencies

- Phase 3.2 complete (first working end-to-end run).
- Core Phase 6 live test harness in place before benchmark scaling.
- Phase 7 hook/schema enforcement active and fail-closed before publishing benchmark results.
- Phase 4 debate artifacts available for contested finding arbitration.

## Key Files

- `src/alphaswarm_sol/benchmark/suite.py`
- `src/alphaswarm_sol/benchmark/runner.py`
- `src/alphaswarm_sol/benchmark/results.py`
- `src/alphaswarm_sol/validation/ground_truth.py`
- `benchmarks/dvdefi/`
- `benchmarks/smartbugs/`
- `benchmarks/safe-set/`

## Plans (Reordered, Test-First)

### 5-01: Ground-Truth Contract and Matching Tests

- Add failing tests for contract/function/location matching with category checks.
- Require deterministic matcher behavior before any benchmark publication.

#### Reasoning

The matcher is the foundation of every metric; if contract/function/location matching is non-deterministic or incorrectly scoped, every downstream TP/FP/FN count is unreliable. Tests must prove deterministic, category-aware matching BEFORE any benchmark run is considered valid. This also prevents the scorer from silently reading the YAML `status` field instead of comparing against pipeline-produced artifact JSON.

#### Expected Outputs

- Pytest test file `tests/benchmark/test_ground_truth_matcher.py` with contract-level, function-level, and location-level matching tests
- Deterministic assertion: same inputs produce identical match sets across 10 consecutive runs
- Category cross-check tests: matcher respects category boundaries (reentrancy finding does not match oracle ground-truth)
- Edge-case tests: partial matches, missing fields, duplicate entries, empty ground-truth
- CI integration: matcher tests run in `pytest -n auto` parallel suite

#### Testing Strategy

| Output | Method 1 | Method 2 |
|--------|----------|----------|
| Matcher determinism | Run matcher 10x on frozen input, assert identical output sets | Hash matcher output, compare across runs |
| Category boundaries | Feed cross-category pairs, assert zero matches | Property-based test: random category pairs never cross-match |
| Edge cases | Pytest parametrize over missing/partial/duplicate fixtures | Mutation: corrupt one ground-truth field, assert graceful failure |
| No YAML leakage | Mock YAML loader to raise on `status` field access during scoring | Grep scorer source for `status` / `yaml` imports, fail if found |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|--------------------|-------------------|-------------|
| Matcher reads only artifact JSON, never YAML `status` | Import of `yaml` or `status` field access in matcher module | Pre-commit hook + CI grep gate on matcher source |
| Identical output across runs for identical input | Timestamp, random seed, or ordering dependency in matcher | 10x determinism test in CI (fail on any diff) |
| Category boundaries respected | Wildcard or `*` category in ground-truth YAML | Schema validation rejects wildcard categories |
| All matcher tests pass before benchmark plans 5-02+ run | Benchmark CI job does not depend on matcher test job | CI DAG: `test_matcher -> benchmark_*` explicit dependency |

### 5-02: Build Minimal Runtime Benchmark Loop

- Run on a small DVDeFi subset first.
- Score TP/FP/FN from actual findings artifacts, not suite labels.

#### Reasoning

A minimal benchmark loop on a small, well-understood DVDeFi slice is the first credible signal of pipeline accuracy. Scoring MUST consume pipeline-produced JSON artifacts (findings with evidence packet IDs), not YAML annotations or suite-level labels. Running small first catches integration bugs before scaling wastes compute, and establishes the artifact-only scoring invariant that all later plans depend on.

#### Expected Outputs

- Benchmark runner script `benchmarks/run_minimal.py` that executes the pipeline on a 5-contract DVDeFi slice
- Scorer module that reads only from `.vrs/validation/runs/<run_id>/` artifact directories
- JSON results file `benchmarks/results/minimal_dvdefi.json` with TP/FP/FN counts, precision, recall, F1
- Evidence packet IDs linked to every counted finding (no anonymous counts)
- Execution log with wall-clock time, tool versions, config hash

#### Testing Strategy

| Output | Method 1 | Method 2 |
|--------|----------|----------|
| Artifact-only scoring | Inject fake YAML annotations, assert scorer ignores them | Remove all YAML files, scorer still produces valid results |
| TP/FP/FN correctness | Hand-verified 5-contract slice with known ground-truth, compare | Cross-check: `TP + FN = total ground-truth`, `TP + FP = total findings` |
| Evidence linkage | Assert every finding in results JSON has non-empty `evidence_pack_id` | Load evidence pack for each finding, validate manifest exists |
| Reproducibility | Run twice with identical config, diff results JSON | Hash results JSON, assert stable across runs |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|--------------------|-------------------|-------------|
| Scorer reads from artifact directories only | Scorer imports ground-truth YAML or reads `status` fields | CI grep gate: scorer module has no `yaml`/`status` imports |
| Every finding links to evidence pack | Findings with `evidence_pack_id: null` or missing field | JSON schema validation on results file (required field) |
| Small slice runs before full suite | Full DVDeFi run without prior minimal pass | CI DAG: `minimal_benchmark -> full_benchmark` dependency |
| Un-verified findings not counted | Findings without verifier verdict included in TP count | Scorer filters: only `verdict: confirmed` findings count as TP |

### 5-03: Add Safe-Set False-Positive Harness

- Run same pipeline over safe contracts.
- Produce severity-weighted FP metrics.

#### Reasoning

A negative-control gate is the single most important honesty check: if the pipeline flags critical vulnerabilities in contracts known to be safe, all positive results are suspect. The safe-set must use production-identical pipeline configuration, and ANY high-confidence critical finding on a safe contract blocks all benchmark publication. This prevents the system from gaming precision by only running on vulnerable contracts.

#### Expected Outputs

- Safe-set corpus in `benchmarks/safe-set/` with at least 10 contracts verified safe by manual audit and external tools
- Safe-set runner that executes identical pipeline (same config, same tools, same scorer)
- FP metrics report: total findings, severity breakdown, confidence breakdown
- Hard gate: zero critical-severity high-confidence findings (blocks all benchmarks on failure)
- Per-contract FP breakdown in `benchmarks/results/safe_set.json`

#### Testing Strategy

| Output | Method 1 | Method 2 |
|--------|----------|----------|
| Safe contracts are genuinely safe | Run Slither + Aderyn on safe-set, confirm zero critical findings | Manual audit checklist per contract in `benchmarks/safe-set/audit_notes.md` |
| Pipeline config identical | Diff config hashes between safe-set run and DVDeFi run | Single config file used by both runners, no override mechanism |
| Critical FP gate | Inject a synthetic critical finding into safe-set results, assert gate blocks | Integration test: safe-set run with planted vulnerability, verify gate catches it |
| Severity weighting | Unit test `CategoryMetrics` with known FP counts, verify weighted score | Compare weighted vs unweighted: critical FP contributes more than low FP |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|--------------------|-------------------|-------------|
| Zero critical high-confidence FPs on safe-set | Safe contracts are trivially simple (e.g., empty contracts, no state) | Minimum complexity gate: safe contracts must have >= 3 functions and state variables |
| Same pipeline config for safe-set and benchmark | Safe-set uses different tool flags or reduced tool set | Config hash comparison in CI; fail if hashes differ |
| FP classified honestly (not downgraded to dodge gate) | Critical findings reclassified as "low confidence" in safe-set only | Confidence thresholds frozen in config, same for all runs |
| Gate blocks ALL downstream benchmarks | Safe-set failure only blocks safe-set report, not others | CI DAG: `safe_set_gate -> benchmark_*` for all benchmark jobs |

### 5-04: Expand Dataset Coverage

- Expand to full declared DVDeFi scope.
- Run SmartBugs subset with compile-success tracking and transparent exclusions.
- Add SC-Bench and ScaBench slices only after ground-truth contract and matcher are stable.

#### Reasoning

Expanding beyond the minimal slice tests whether accuracy holds at scale and across contract diversity. Compile-success tracking and transparent exclusions prevent silent survivorship bias where only "easy" contracts remain in the benchmark. Every exclusion must be recorded as a first-class output so that reported metrics honestly represent the attempted corpus, not a cherry-picked subset.

#### Expected Outputs

- Full DVDeFi corpus execution with per-contract pass/fail/exclude status
- SmartBugs subset execution with compile-success rate as a tracked metric
- Exclusion manifest `benchmarks/results/exclusions.json` with reason per excluded contract
- Compile failure manifest `benchmarks/results/compile_failures.json` with error details
- Aggregate metrics across full corpus in `benchmarks/results/full_coverage.json`
- Coverage delta report: minimal slice vs full corpus precision/recall comparison

#### Testing Strategy

| Output | Method 1 | Method 2 |
|--------|----------|----------|
| No silent exclusions | Count contracts in corpus, count contracts in results, assert equal | CI check: `len(results) + len(exclusions) + len(compile_failures) == len(corpus)` |
| Compile failures tracked | Intentionally include a non-compiling contract, verify it appears in `compile_failures.json` | Unit test: mock compile failure, assert exclusion manifest entry created |
| Exclusion reasons recorded | Schema validation on `exclusions.json` (required `reason` field) | Review: every exclusion reason is a known enum value, not free-text |
| Coverage delta meaningful | Compare minimal vs full metrics, flag if delta > 15% (possible selection bias in minimal) | Statistical test: confidence interval overlap between minimal and full |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|--------------------|-------------------|-------------|
| Every corpus contract accounted for (pass, fail, or excluded) | Results count < corpus count with no exclusion manifest | CI assertion: `results + exclusions + compile_failures == corpus` |
| Compile failures are first-class outputs | Compile failures silently dropped, not in any manifest | Runner exits non-zero if any contract outcome is unrecorded |
| Exclusion reasons are structured, not free-text | Free-text exclusion reasons that obscure real cause | JSON schema enum validation on exclusion reason field |
| SC-Bench/ScaBench added only after matcher stable | New datasets added before 5-01 matcher tests pass | CI gate: dataset expansion jobs depend on `test_matcher` job |

### 5-05: Head-to-Head and Ablation

- Run Slither baseline on same corpus and matcher.
- Run graph ablation with identical contracts and scoring function.

#### Reasoning

Head-to-head comparison is the only way to demonstrate that BSKG-based analysis adds real value over established static analysis. Both runs must use the SAME corpus, the SAME matcher, and the SAME scorer to eliminate confounding variables. Graph ablation (disabling BSKG) on identical contracts with identical scoring isolates the graph's contribution. Any advantage from extra signals (labels, tool hints) not available to the baseline invalidates the comparison.

#### Expected Outputs

- Slither baseline results `benchmarks/results/baseline_slither.json` on full corpus
- BSKG full results `benchmarks/results/full_bskg.json` on identical corpus
- Graph-ablated results `benchmarks/results/ablation_no_graph.json` on identical corpus
- Comparison report `benchmarks/results/head_to_head.json` with per-category delta
- Evidence packet diffs for findings that differ between variants
- Fairness attestation: config hashes, tool sets, corpus hashes match across all runs

#### Testing Strategy

| Output | Method 1 | Method 2 |
|--------|----------|----------|
| Same corpus across runs | Hash corpus file list, assert identical for all 3 runs | CI check: corpus manifest hash in each results file, compare |
| Same matcher/scorer | Matcher and scorer version pinned in config, diff configs across runs | Unit test: feed identical findings to all 3 scorer instances, assert identical metrics |
| No extra signals in BSKG run | Audit BSKG pipeline for label-dependent signals, list in fairness attestation | Ablation test: disable labels, verify BSKG metrics change (labels contribute) but baseline unaffected |
| Delta cites evidence diffs | Every finding present in BSKG but not baseline has evidence packet diff | Script: for each delta finding, assert `evidence_pack_id` exists and links to valid pack |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|--------------------|-------------------|-------------|
| Identical corpus for all comparison runs | Different corpus hashes across baseline/BSKG/ablation results | CI assertion: corpus hash field identical in all results JSONs |
| No label-dependent signals in baseline or ablation | Ablation run includes semantic labels not available to Slither | Config diff gate: ablation config must disable `labels` module |
| Scorer function identical across variants | Different scoring weights or thresholds per variant | Single scorer module used by all runners, no per-variant config |
| Delta findings backed by evidence diffs | Delta report shows count-only differences without evidence links | Schema validation: delta entries require `evidence_pack_ids` array |

### 5-06: Publish Reproducible Results

- Write `benchmarks/RESULTS.md` from generated artifacts only.
- Include limitations and data-quality caveats.

#### Reasoning

The published results file is the external-facing credibility artifact. It must be generated entirely by a scorer script reading from pipeline artifacts, never hand-edited. Including limitations, caveats, and known failure modes is non-negotiable for intellectual honesty. If any number in the published file cannot be traced back to a specific evidence pack, the entire report is invalid.

#### Expected Outputs

- Generator script `benchmarks/generate_results.py` that reads from `benchmarks/results/*.json` only
- Published `benchmarks/RESULTS.md` with precision, recall, F1, FP rate, ablation delta, and baseline comparison
- Limitations section listing known caveats (corpus size, compile exclusions, category coverage gaps)
- Provenance footer: corpus hash, scorer version, generation timestamp, config hash
- Traceability index: every number in the report maps to a specific JSON artifact path and field

#### Testing Strategy

| Output | Method 1 | Method 2 |
|--------|----------|----------|
| Generated, not hand-edited | CI job: regenerate from artifacts, diff against committed file, fail on difference | Git hook: `RESULTS.md` changes only accepted from generator script commit |
| Limitations included | Grep `RESULTS.md` for required sections: "Limitations", "Caveats", "Exclusions" | Schema check: results template requires non-empty limitations section |
| Provenance footer present | Grep for `corpus_hash`, `scorer_version`, `generated_at` in footer | Unit test: generator always emits footer, even on empty results |
| Traceability | For each number in report, follow traceability index to artifact JSON, verify value matches | Script: parse `RESULTS.md`, extract all metrics, validate each against source artifact |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|--------------------|-------------------|-------------|
| `RESULTS.md` generated by script, never hand-edited | Git diff shows manual edits to `RESULTS.md` not from generator | CI job: regenerate and diff; pre-commit hook blocks manual edits |
| All numbers traceable to artifact JSON | Numbers in report with no corresponding traceability index entry | Generator script: every metric write also writes traceability entry; fail if orphaned |
| Limitations section present and non-trivial | Empty limitations section or boilerplate-only text | CI check: limitations section word count >= 50 |
| No cherry-picked subsets | Report covers different corpus than what pipeline actually ran | Corpus hash in report footer must match corpus hash in latest run artifacts |

## Hard Delivery Gates for Phase 5 (Added 2026-02-10)

Phase 5 owns realism gates that separate "detectable in curated tests" from "usable in real security decisions."

### HDG-07: Blind Unknown-Contract Exams (Primary owner: 5-04)

**Why this is critical**
- A benchmark can look strong while overfitting to known contracts and prompt-tuned patterns.
- Blind holdout contracts are the only clean measure of generalization.

**Implementation contract**
- Maintain a sealed holdout set under `benchmarks/blind-holdout/` with access restricted until scoring time.
- Freeze prompt/config hashes before unsealing holdout contracts.
- Score holdout with the exact same matcher/scorer/thresholds used for declared benchmark runs.
- Publish holdout outputs separately in `benchmarks/results/blind_holdout.json`.
- Add signed holdout manifest:
  - `benchmarks/blind-holdout/manifest.json` (contract list + content hashes)
  - `benchmarks/blind-holdout/manifest.sha256`
  - `benchmarks/blind-holdout/manifest.sig` (Ed25519 signature from pinned public key in repo)
  - Verification key path: `configs/security/holdout_signing_pubkey.pem`
  - Rotation policy: key rotation requires a dedicated changelog entry + dual-signature overlap for one release cycle

**Hard validation**
- Any contract present in development corpus or tuning fixtures is disallowed from holdout.
- Holdout manifest signature must be verified before scoring; verification failure hard-stops benchmark run.
- If holdout precision or recall drops below configured degradation tolerance versus non-blind corpus, benchmark claims are downgraded in release docs.

**Expected strict result**
- Reported benchmark quality includes out-of-distribution behavior, not only seen-corpus performance.

### HDG-08: Economic Realism Gate (Primary owner: 5-05)

**Why this is critical**
- Many technically plausible exploits are economically infeasible in practice.
- Shipping high-severity findings without feasibility checks creates noise and erodes trust.

**Implementation contract**
- Add economics sidecar per high/critical finding:
  - required capital
  - liquidity depth assumptions
  - oracle freshness/manipulation window
  - slippage and gas sensitivity
  - expected attacker profit after costs
- Write feasibility artifacts to `benchmarks/results/economic_realism/<finding-id>.json`.
- Integrate a deterministic classifier: `feasible`, `marginal`, `infeasible`.

**Hard validation**
- High/critical findings must be `feasible` or explicitly downgraded.
- Missing economics sidecar on high/critical findings blocks benchmark publication.
- Feasibility inputs must reference concrete data sources in the artifact bundle (not free-text assumptions).

**Expected strict result**
- Severity reflects exploitability under realistic market constraints, not only symbolic possibility.

## Benchmark Order (Phase 5 Execution Sequence)

1. **Negative-Control Gate (must pass before any scaling)**
Run the full pipeline on `benchmarks/safe-set/` with identical scoring. Gate is a hard stop if critical-FP rate breaches threshold or if any FP lacks evidence packet.
2. **Deterministic Scoring Harness**
Freeze scorer inputs to run artifacts only (no YAML hints, no status flags). Enforce deterministic matcher behavior and stable seed/config hashes.
3. **Small DVDeFi Slice (truth-bound)**
Run a minimal, ground-truth-verified subset. Require exact match behavior for contract/function/location categories.
4. **Ablation Fairness Run**
Run graph-ablation vs full graph on identical corpus, matcher, and scorer. Disallow any tool or label that is not common to both variants.
5. **Baseline Comparison**
Run Slither baseline on the same corpus with the same matcher and scoring function.
6. **Scale to Declared Scope**
Expand to full DVDeFi and approved SmartBugs subset. Record exclusions and compile failures as first-class outputs.
7. **Repeatability Pass**
Re-run a fixed slice to measure `pass^k` stability and variance.

## Hard Fail Conditions (Non-Negotiable)

- Any benchmark report derived from annotations or YAML labels instead of run artifacts.
- Missing evidence packets for any TP or FP in reported metrics.
- Negative-control failure (critical-FP rate above threshold or unverified FP).
- Non-deterministic matcher results across identical inputs.
- Ablation comparison with mismatched corpora, tools, or scoring functions.
- Unlogged exclusions or compile failures.
- Blind holdout set contamination (any overlap with development/tuning corpus).
- High/critical findings without passing economic realism classification.

## Deterministic Scoring Rules

- Scoring uses only run-time artifacts and matcher outputs.
- Contract/function/location matching must be deterministic and version-pinned.
- Evidence packet IDs are required for all counted findings.
- All thresholds and weights are fixed and recorded in artifacts.

## Ablation Fairness Requirements

- Same corpus, same matcher version, same scoring function.
- Same tool set, with label-dependent signals disabled in both runs.
- Any delta must cite evidence packet diffs, not just counts.

## Reproducibility Requirements

- Dataset hashes, tool versions, and config hashes recorded per run.
- Results reproducible from artifacts with a single command.
- All randomness seeded and recorded.

## Interactive Validation Method (Agent Teams + JJ Workspace)

- Benchmark batches execute in isolated `jj` workspaces.
- Use `vrs-benchmark-runner` plus `vrs-verifier` for challenged findings.
- Route disputed TP/FP calls to attacker-defender-verifier mini-debates.

## Non-Vanity Metrics

- Precision, recall, and F1 from run artifacts.
- Safe-set false-positive rate and critical-FP rate.
- Compile success rate by dataset.
- Median and P95 runtime per contract.
- Graph ablation delta (same scorer, same corpus).
- `pass^k` stability for repeated benchmark runs on the same corpus slice.

## Recommended Subagents

- `vrs-benchmark-runner`
- `vrs-corpus-curator`
- `vrs-prevalidator`
- `vrs-verifier`
- `vrs-regression-hunter`

## Exit Gate

Benchmark report is reproducible from artifacts, includes baseline and ablation, rejects non-computed claims, publishes repeatability and false-positive results, and passes HDG-07 blind holdout and HDG-08 economic realism gates.

## Research Inputs

- `.planning/new-milestone/reports/w2-benchmark-plan.md`
- `docs/PHILOSOPHY.md`
- `docs/reference/testing-framework.md`
- External: SC-Bench (ICSE 2025 LLM4Code), SmartBugs 2.0, ReliabilityBench (Jan 2026)
- External: ScaBench curated 2024-08 to 2025-08 vulnerability set

## 2026-02-09 Reordering Audit Context

### Global Sequence

Execution order after Phase 2.1 is now fixed:
`3.1 -> 3.1b -> 3.2 -> 4 -> 4.1 -> 6 -> 7 -> 5 -> 8`

### Iteration Notes (1 -> 3)

1. Iteration 1: benchmark plan improved but still risked vanity metrics.
2. Iteration 2: added negative-control, deterministic scorer, fairness, and hard fail conditions.
3. Iteration 3: strict review moved benchmark execution after Phase 7 to ensure hook/schema enforcement is active before metric publication.

### This Phase's Role

Phase 5 provides honest external evidence after runtime behavior is already hardened by testing and hook enforcement.

### Mandatory Carry-Forward Gates

- Negative-control gate passes before scaling.
- Deterministic artifact-only scoring.
- Fair ablation protocol.
- Repeatability (`pass^k`) reporting.
- Blind holdout evaluation (HDG-07) with zero corpus contamination.
- Economic realism classification (HDG-08) for high/critical findings.

### Debug/Artifact Contract

- Any benchmark gate failure writes `.vrs/debug/phase-5/repro.json`.
- Repro includes corpus slice, scorer hash, matcher hash, and failing metric artifacts.

### Assigned Research Subagent

- `vrs-benchmark-runner` for benchmark reproducibility and variance analysis

### Research Sources Used

- https://arxiv.org/abs/2601.06112
- https://conf.researchr.org/details/icse-2025/llm4code-2025-papers/22/SC-Bench-A-Large-Scale-Dataset-for-Smart-Contract-Auditing
- https://arxiv.org/abs/2306.05057
