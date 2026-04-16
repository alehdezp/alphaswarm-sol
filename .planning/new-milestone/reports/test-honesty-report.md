# T4: Test Honesty Report

## Executive Summary

**Of 11,282 collected tests, approximately 3,800-4,200 (34-37%) prove real, meaningful behavior. The rest are a mix of dataclass/enum existence checks, mock-dependent tests that verify synthetic scenarios, schema round-trip tests, and aspirational tests that currently fail.**

The suite is NOT fraudulent — it's inflated. There's genuine testing work happening (pattern detection on real contracts, graph building, serialization), but it's buried under thousands of low-signal tests that pad the count without improving confidence in the system's actual capability.

### Key Numbers

| Metric | Value |
|--------|-------|
| Total collected | 11,282 |
| Collection errors | 1 (`test_checkpoint.py` — ImportError) |
| **Passed** | **10,310** (91.4%) |
| **Failed** | **905** (8.0%) |
| Skipped | 54 (0.5%) |
| xfailed | 13 (0.1%) |
| Files with mocks | 95 of ~365 test files (26%) |
| Mock references total | 1,148 across all tests |
| Parametrized files | 6 (minimal inflation from parametrization) |

---

## Test Distribution

### By Directory

| Directory | Files | Est. Tests | Quality Assessment |
|-----------|-------|-----------|-------------------|
| `tests/` (root) | 228 | ~8,500 | MIXED — contains everything from excellent lens tests to trivial enum checks |
| `tests/agents/` | 23 | ~850 | LOW-MEDIUM — heavy mock usage, tests synthetic agent behavior |
| `tests/integration/` | 14 | ~430 | LOW — uses `OrchestratorTester` in MOCK mode by default, simulates flows |
| `tests/testing/` | 12 | ~350 | MEDIUM — tests the testing infrastructure (meta) |
| `tests/test_3.5/` | 11+13 | ~700 | LOW — heavy mocking of agent context with `Mock()` objects |
| `tests/e2e/` | 8 | ~240 | MEDIUM — pipeline tests pass but don't verify detection accuracy |
| `tests/vulndocs/` | 6 | ~250 | MEDIUM — schema/skill validation |
| `tests/orchestration/` | 6 | ~200 | MEDIUM — schema and pool management |
| `tests/kg/` | 4 | ~120 | MEDIUM — uses synthetic SubGraph nodes, not real contracts |
| `tests/templates/` | 3 | ~100 | HIGH — tests property detection on real-ish structures |
| `tests/metrics/` | 3 | ~90 | LOW-MEDIUM — tests metric computation logic |
| `tests/skills/` | 3 | ~80 | MEDIUM — skill registry validation |
| `tests/adapters/` | 4 | ~90 | MEDIUM — SARIF/Slither adapter conversion |
| `tests/gauntlet/` | 0 Python | 0 | **NO EXECUTABLE TESTS** — only YAML manifests |

### Top 10 Test Files by Count

| File | Tests | Quality | Notes |
|------|-------|---------|-------|
| `test_external_influence_lens.py` | 226 | HIGH (when passing) | **115 FAIL** — pattern detection not matching expectations |
| `test_token_lens.py` | 203 | HIGH (when passing) | **92 FAIL** — many labeled as known builder limitations |
| `test_investigation_templates.py` | 153 | LOW | Parametrized template existence/structure checks × 7 templates |
| `test_upgradeability_lens.py` | 145 | HIGH (when passing) | **80 FAIL** — detection mismatches |
| `test_metrics.py` | 116 | LOW-MEDIUM | Metric enum existence, value calculation, status thresholds |
| `test_agents.py` | 91 | LOW | 35 of 91 are trivial enum/dataclass creation tests |
| `test_queries_access.py` | 88 | HIGH (when passing) | **57 FAIL** — access control query tests |
| `test_grimoires.py` | 87 | LOW-MEDIUM | Schema, registry, executor tests; no real execution |
| `test_tool_adapters.py` | 82 | MEDIUM | 33 mock references; tests SARIF conversion with mocked tool output |
| `test_liveness_lens.py` | 82 | HIGH (when passing) | **59 FAIL** — liveness detection mismatches |

---

## Mock Analysis

### Mock Usage Distribution

- **95 files** out of ~365 test files use mocks (26%)
- **1,148 total mock references** across the codebase
- Most-mocked areas: `tests/test_3.5/phase-2/` (agent tests), `tests/agents/` (runtime tests)

### Boundary Assessment

| Mock Category | Count (est.) | Boundary Quality |
|---------------|-------------|-----------------|
| **subprocess/shutil.which** | ~15 files | PROPER — mocking external tool presence at system boundary |
| **Agent context (Mock() subgraph)** | ~25 files | IMPROPER — fakes entire internal graph structure |
| **LLM responses (AsyncMock)** | ~20 files | PROPER — mocking external LLM API calls |
| **File system (tmp_path)** | ~20 files | PROPER — using pytest tmp_path for isolation |
| **OrchestratorTester (MOCK mode)** | ~8 files | IMPROPER — simulates multi-agent flow without real agents |
| **FlowSimulator** | ~5 files | IMPROPER — simulates debate flows synthetically |

### Worst Offenders

**`tests/test_3.5/phase-2/test_P2_T2_attacker_agent.py`**: Creates `Mock()` subgraph nodes with hardcoded properties (`has_reentrancy_guard: False`), then tests that the attacker agent reads those properties correctly. This proves the attacker agent can read a dictionary, not that it can find real vulnerabilities.

**`tests/agents/test_runtime_e2e.py`**: 70 mock references. The "E2E" test creates mock responses, mock runtimes, and tests that the routing/fallback logic handles them. Real E2E would actually call a runtime.

**`tests/integration/test_debate_flow.py`**: Uses `OrchestratorTester(mode=InvocationMode.MOCK)` with `FlowSimulator`. Tests that the simulator simulates correctly, not that real agents produce correct verdicts.

---

## Detection Test Quality

### Pattern Lens Tests (THE GOOD)

The lens tests (`test_external_influence_lens.py`, `test_token_lens.py`, etc.) are **genuinely high-quality** when they work:
- Build real knowledge graphs from real Solidity contracts via Slither
- Run the actual PatternEngine with actual PatternStore
- Assert specific function names appear/don't appear in findings
- Document known limitations explicitly (labeled "BUILDER LIMITATION" or "FN:")

**The problem: 752 of these tests currently FAIL.** The detection engine doesn't match expectations. This means either:
1. Tests are aspirational (written for detection that doesn't exist yet), or
2. Regressions broke previously-working detection

### Benchmark "Detection Rate" (THE FRAUDULENT)

The claimed 91.6% detection rate (from `test_benchmark.py`) is **self-labeled, not computed**.

**How it works:**
1. `BenchmarkSuite.load()` reads a YAML file
2. Each challenge has a `status` field set **in the YAML** (e.g., `status: detected`)
3. `detection_rate` = count of `status == "detected"` / total
4. The test asserts `detection_rate >= 0.8`

**This is not a detection test. It's a YAML parsing test.** Nobody runs the detector on the benchmark contracts and checks if it actually finds the vulnerabilities. The status is manually set by whoever wrote the YAML.

### Gauntlet (THE MISSING)

The "78.2% gauntlet" metric has:
- 20 real Solidity contracts in `tests/gauntlet/` (10 reentrancy, 10 access/oracle)
- YAML manifests describing expected detections
- **ZERO executable Python test files**

There is no test that runs the gauntlet. The contracts exist, the manifests exist, but nothing executes them.

---

## Parametrized Test Inflation

**Minimal.** Only 6 files use `@pytest.mark.parametrize`, contributing roughly 200-300 tests total. This is not a significant source of inflation.

The real inflation comes from:

### Structural/Enum Test Inflation

Many files have 10-40+ tests that only verify:
- Enum members exist (`assert AttackCategory.STATE_MANIPULATION`)
- Dataclass fields have default values
- Serialization round-trips (`to_dict()` → `from_dict()`)
- String representation works
- Case-insensitive parsing

**Estimated: ~2,500-3,000 tests are structural/schema/enum verification.** These tests add count but prove nothing about system behavior.

### Example from `test_beads_types.py` (42 of 57 tests are trivial):
- `test_evidence_creation` — creates a dataclass
- `test_evidence_type_enum` — asserts 7 enum values exist
- `test_unknown_evidence_type_fallback` — tests fallback for unknown string

---

## Reproducibility Check

### "84.6% detection rate" — CANNOT REPRODUCE

No test produces this number. The benchmark test asserts `>= 0.8`, and the actual YAML-computed rate is 91.6% (11/12). The "84.6%" appears to come from documentation, not executable tests.

### "78.2% gauntlet" — CANNOT REPRODUCE

No executable gauntlet test exists. The contracts and manifests are present but there's no Python test to run them.

### What CAN be reproduced:

```
Full suite: 905 failed, 10310 passed, 54 skipped, 13 xfailed (392s)
```

This is reproducible and accurate.

---

## Test Execution Status

| Status | Count | % |
|--------|-------|---|
| **Passed** | 10,310 | 91.4% |
| **Failed** | 905 | 8.0% |
| **Skipped** | 54 | 0.5% |
| **xfailed** | 13 | 0.1% |
| **Collection error** | 1 file | — |

### Failure Breakdown

| Category | Failed Tests | Root Cause |
|----------|-------------|-----------|
| Lens/pattern detection | 752 | PatternEngine not matching expected functions |
| Agent/consensus (3.5) | 21 | Enhanced consensus module issues |
| VulnDocs navigator | 18 | Navigator API changes |
| Codex CLI runtime | 12 | Runtime configuration mismatches |
| Schema snapshot | 11 | Graph structure expectations not met |
| Full coverage patterns | 11 | Pattern coverage gaps |
| Semgrep parity | 9 | Parity comparison failures |
| Rename resistance | 10 | Builder rename robustness |
| Other | ~46 | Assorted module issues |

---

## Honest Verdict

### Test Quality Tiers

| Tier | Description | Est. Tests | % of Total |
|------|-------------|-----------|-----------|
| **A: Proves real detection** | Lens tests that PASS + run PatternEngine on real .sol contracts | ~1,100 | 9.7% |
| **B: Proves real logic** | Graph building, serialization, schema validation with meaningful assertions | ~2,500 | 22.2% |
| **C: Proves structure** | Enum existence, dataclass creation, basic round-trips | ~2,800 | 24.8% |
| **D: Mock-dependent** | Tests with mocked internals that verify code reacts to mocks correctly | ~1,800 | 16.0% |
| **E: Aspirational/Failing** | Tests that should work but don't (905 failures) | ~905 | 8.0% |
| **F: Meta/Infrastructure** | Tests for the testing framework itself, skill/template existence | ~600 | 5.3% |
| **G: Genuinely valuable E2E** | E2E pipeline, benchmark loading, corpus management | ~500 | 4.4% |
| **Unclassified** | Other | ~1,077 | 9.6% |

### Bottom Line

**~3,800-4,200 tests (Tiers A+B+G, roughly 34-37%) prove real, meaningful behavior.** The rest are either failing (905), structurally trivial (2,800), or mock-dependent (1,800).

The test suite is NOT completely fraudulent. The lens tests in particular are well-designed and test the actual detection pipeline on real Solidity contracts. The problem is:

1. **752 of the best tests fail** — the detection engine doesn't match expectations
2. **~3,000 tests are structural filler** — enum/dataclass/serialization checks that pad count
3. **Key metrics are self-labeled** — 91.6% detection rate is from YAML, not runtime detection
4. **Gauntlet has no executable test** — contracts exist but nothing runs them
5. **"Integration" tests use mock mode** — OrchestratorTester defaults to `InvocationMode.MOCK`

---

## Specific Gaps

1. **No runtime detection benchmark** — No test actually RUNS the detector on DVDeFi contracts and checks results
2. **No gauntlet test runner** — 20 contracts, 0 tests
3. **No real multi-agent test** — All debate/verification tests use mock/simulated flows
4. **No cross-contract detection test on real projects** — Cross-contract tests use synthetic graphs
5. **No external tool integration test** — Tool adapter tests mock `subprocess.run`
6. **Self-referential detection rate** — The benchmark "proves" detection by reading pre-labeled YAML
7. **752 failing lens tests** indicate detection engine has regressed or was never complete

---

## Recommendations for Milestone 6.0

### P0: Fix What's Broken (Before Adding More)

1. **Triage the 905 failing tests** — Determine which are regressions vs aspirational. Fix regressions; mark aspirational as `xfail` with tickets.
2. **Fix or remove `test_checkpoint.py`** — It can't even import.
3. **Fix the 752 lens test failures** — These are the BEST tests in the suite. If they fail, the detection engine has serious issues.

### P1: Make Metrics Honest

4. **Build a runtime benchmark test** — Actually run detection on DVDeFi contracts, compare to ground truth, compute real detection rate.
5. **Build the gauntlet runner** — The contracts are already there. Write the test that runs them.
6. **Replace self-labeled YAML** with computed results from actual runs.

### P2: Improve Test Quality

7. **Delete or consolidate enum/dataclass existence tests** — `assert AttackCategory.STATE_MANIPULATION` proves nothing. If the enum changes, the import fails. No need for separate tests.
8. **Convert mock-heavy agent tests to real integration tests** — Use real SubGraphs from actual Slither builds instead of `Mock()` objects.
9. **Add `InvocationMode.LIVE` integration tests** — The framework already supports it. Use it.
10. **Set a quality gate**: no test file should have >50% trivial (creation/existence/enum) tests.

### P3: Add Missing Coverage

11. **Real multi-agent debate test** — Actually spawn attacker+defender+verifier on a real bead
12. **External tool integration test** — Actually run Slither (it's installed!) instead of mocking subprocess
13. **Cross-contract detection on Damn Vulnerable DeFi** — The contracts are in `examples/damm-vuln-defi`

### Honest Test Count Target

A healthy test suite for this codebase would have **3,000-4,000 meaningful tests** rather than 11,282 padded ones. Quality over quantity. Every test should answer: "What would break if this test didn't exist?"
