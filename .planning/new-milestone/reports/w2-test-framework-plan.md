# W2-6: Test Framework Overhaul Plan

## Executive Summary

The test suite has **11,106 test functions** across **365 files** with **362 Solidity test contracts** and **36 test project contracts**. A sample audit of 15 representative files reveals a **~60/40 split: roughly 60% test outcomes on real data, 40% test internal implementation with mocks or trivial assertions**. The mock problem is concentrated: 82 files (22%) use mocks, with ~597 total mock occurrences, but the top 10 files account for 221 of those. The most valuable tests — pattern detection on real graphs — are already well-structured but account for only ~12% of the test suite (45 files using `load_graph`).

**Verdict: The test count is inflated but not fabricated. The core detection tests are excellent. The problem is that ~4,400 tests add little signal (dataclass field checking, enum iteration, mock-heavy agent simulation).**

---

## Current Test Quality (Sample Audit of 15 Files)

### File-by-File Classification

| # | File | Test Count | Classification | Mocks? | Notes |
|---|------|-----------|----------------|--------|-------|
| 1 | `test_vql2.py` | ~20 | **OUTCOME** | No | Tests VQL lexer/parser on real inputs, checks real AST output. Good. |
| 2 | `test_policy_enforcer.py` | ~30 | **MIXED** | Yes (MagicMock for AuditLogger) | Policy validation logic is real, but audit logger is mocked unnecessarily. |
| 3 | `test_agent_runtime.py` | ~40 | **IMPLEMENTATION** | Heavy (AsyncMock, MagicMock) | Tests enum values, dataclass fields, config serialization. Mock-driven runtime tests. |
| 4 | `test_golden_snapshots.py` | ~5 | **OUTCOME** | No | Builds real graphs from DVDeFi, validates fingerprints. **Excellent** — exactly what we need more of. |
| 5 | `test_defi_infrastructure_patterns.py` | ~50 | **OUTCOME** | No | Runs real patterns on real graphs (load_graph). TP/TN/FP testing. **Gold standard.** |
| 6 | `test_cross_contract.py` | ~30 | **MIXED** | Some (MagicMock for nodes) | Fingerprint/similarity tests use fabricated data. Exploit detection tests use real structures. |
| 7 | `test_P2_T2_attacker_agent.py` | ~15 | **IMPLEMENTATION** | Heavy (Mock everything) | Entire context is mocked. Tests that attacker returns expected shapes, not that it finds real vulns. |
| 8 | `test_full_audit_run.py` | ~10 | **MIXED** | Yes (MagicMock) | Integration test concept is right but mocks core components, defeating the purpose. |
| 9 | `test_toon.py` | ~25 | **OUTCOME** | No | Tests TOON serialization roundtrips with real data. Clean, focused on behavior. |
| 10 | `test_verifier_agent.py` | ~20 | **IMPLEMENTATION** | Heavy (MagicMock for LLM, bead, attack, defense) | Every input is mocked. Tests verifier plumbing, not whether verification works on real findings. |
| 11 | `test_confidence_enforcement.py` | ~25 | **OUTCOME** | No | Tests confidence rules on real verdict objects. Clear pass/fail criteria. Good. |
| 12 | `test_queries_call_graph.py` | ~8 | **OUTCOME** | No | Runs real graph queries on real contracts via load_graph. **Gold standard.** |
| 13 | `test_context_pack.py` | ~25 | **OUTCOME** | No | Tests schema creation, storage, builder orchestration with real objects. |
| 14 | `test_fingerprint.py` | ~10 | **OUTCOME** | No | Tests fingerprinting on constructed graph data. Behavior-focused. |
| 15 | `test_beads_types.py` | ~30 | **IMPLEMENTATION** | No | Tests enum values exist, from_string aliases, serialization. No mocks but tests implementation details. |

### Quality Breakdown

| Category | Count (sampled) | % of Sample | Description |
|----------|----------------|-------------|-------------|
| **OUTCOME (real data)** | 7/15 | 47% | Tests real behavior with real inputs |
| **OUTCOME (constructed data)** | 2/15 | 13% | Tests real behavior with hand-crafted data |
| **MIXED** | 3/15 | 20% | Some real testing, some mocked |
| **IMPLEMENTATION** | 3/15 | 20% | Tests internal shapes, mocks core logic |

### Extrapolation to Full Suite

Based on sampling and quantitative data:

| Metric | Value | Notes |
|--------|-------|-------|
| Total test functions | 11,106 | |
| Files using `load_graph` (real graphs) | 45 (~12%) | ~3,500 tests — **most valuable** |
| Files using mocks | 82 (22%) | ~3,000 tests — **many need review** |
| Files with neither (pure logic) | ~238 (66%) | ~4,600 tests — mix of good and trivial |
| Estimated high-value tests | ~5,000 (45%) | Actually prove detection/behavior |
| Estimated low-value tests | ~4,400 (40%) | Dataclass fields, enum values, mock simulations |
| Estimated borderline tests | ~1,700 (15%) | Could go either way |

### Test Inflation Patterns Observed

1. **Enum value enumeration**: `test_all_severity_values_exist`, `test_from_string_lowercase`, `test_from_string_uppercase`, `test_from_string_mixed_case`, `test_from_string_with_whitespace` — 5 tests for one enum that could be 1 parametrized test or none at all.

2. **Heavy parametrization**: `test_investigation_templates.py` has 19 `@parametrize` decorators over 7 templates = 133+ test cases from ~20 test functions. Valuable but inflates counts.

3. **Lens test explosion**: `test_external_influence_lens.py` (226 tests), `test_token_lens.py` (203 tests) — each pattern variant gets its own named test. This is **actually good** for detection regression but inflates numbers.

4. **Mock-simulated integration**: `test_full_audit_run.py` claims to be "integration" but mocks the components being integrated.

---

## New Test Categories

### Category A: Detection Regression Tests (HIGHEST VALUE)

**Purpose**: Prove that AlphaSwarm detects known vulnerabilities in real Solidity contracts.

**Design:**

```python
# tests/detection/test_reentrancy_detection.py

class TestReentrancyDetection:
    """Regression tests: reentrancy variants are detected."""

    def test_classic_withdraw_reentrancy(self):
        """DVDeFi: Classic CEI violation in withdraw."""
        graph = load_graph("ReentrancyVulnerable.sol")
        findings = run_patterns(graph, category="reentrancy")
        assert_finding_exists(
            findings,
            pattern_id="reentrancy-001",
            function="withdraw",
            severity="high",
        )

    def test_cross_function_reentrancy(self):
        """Cross-function reentrancy via shared state."""
        graph = load_graph("projects/token-vault/ERC777ReentrancyTest.sol")
        findings = run_patterns(graph, category="reentrancy")
        assert any(f["pattern_id"].startswith("reentrancy-") for f in findings)

    def test_safe_contract_no_reentrancy(self):
        """Safe contract with proper CEI should produce zero reentrancy findings."""
        graph = load_graph("safe/ReentrancySafe.sol")
        findings = run_patterns(graph, category="reentrancy")
        assert len(findings) == 0, f"False positives: {findings}"
```

**Key principles:**
- Input: Real `.sol` file → real graph build → real pattern execution
- Assert: Vulnerability detected (TP) or not detected (TN)
- Coverage: Every vulnerability class has TP + TN + hard-case tests
- Safe contracts are equally important — they test false positive rate

**Test matrix target:**

| Vulnerability Class | Contracts (vuln) | Contracts (safe) | Min Tests |
|---------------------|-------------------|-------------------|-----------|
| Reentrancy | 8 | 3 | 20 |
| Access Control | 12 | 4 | 30 |
| Oracle Manipulation | 6 | 3 | 18 |
| MEV/Frontrunning | 5 | 3 | 15 |
| Token Handling | 10 | 4 | 25 |
| Upgradeability | 6 | 3 | 18 |
| DoS/Liveness | 5 | 2 | 12 |
| Economic/Flash Loan | 4 | 2 | 10 |
| Cryptographic | 5 | 2 | 12 |
| **TOTAL** | **61** | **26** | **~160** |

**These 160 tests are worth more than the other 11,000 combined.**

**Existing assets:**
- Already have 362 test contracts + 36 project contracts = **rich existing corpus**
- 45 files already use `load_graph` — the pattern is established
- `test_defi_infrastructure_patterns.py` and lens tests are the model

### Category B: Pipeline Integration Tests

**Purpose**: Test that the E2E pipeline connects correctly: build-kg → query → pattern → bead → orchestrate.

**Design:**

```python
# tests/integration/test_pipeline_e2e.py

class TestPipelineE2E:
    """E2E pipeline tests with real Solidity contracts."""

    def test_build_query_detect(self):
        """Contract → graph → query → pattern findings."""
        # Build real graph
        graph = VKGBuilder(ROOT).build(CONTRACTS / "NoAccessGate.sol")

        # Query for vulnerable functions
        executor = QueryExecutor()
        results = executor.execute(graph, QueryPlan(
            kind="logic",
            node_types=["Function"],
            match=MatchSpec(all=[
                ConditionSpec(property="has_access_gate", op="eq", value=False),
                ConditionSpec(property="writes_privileged_state", op="eq", value=True),
            ]),
        ))

        # Must find the unprotected function
        labels = {n["label"] for n in results["nodes"]}
        assert "setOwner(address)" in labels

    def test_full_bead_lifecycle(self):
        """Bead creation → status transitions → verdict."""
        # Real finding from real graph → bead → status progression
        graph = load_graph("DelegatecallUntrusted.sol")
        findings = run_patterns(graph, category="upgradeability")

        bead = create_bead_from_finding(findings[0])
        assert bead.status == BeadStatus.PENDING

        bead.transition_to(BeadStatus.INVESTIGATING)
        assert bead.status == BeadStatus.INVESTIGATING
```

**Key principles:**
- Real Solidity contracts as input, never mocked
- Mocks ONLY at: network calls, external tool binaries, LLM API calls
- Tests the connections between components, not the components themselves
- No more than 30 of these — they're slow but important

### Category C: Component Unit Tests

**Purpose**: Test individual components produce correct outputs for given inputs.

**Guidelines:**

```python
# GOOD: Tests outcome of real logic
def test_toon_roundtrip_preserves_data():
    """TOON encode → decode preserves original data."""
    original = {"nodes": [{"id": "fn:1", "type": "Function"}], "edges": []}
    assert toon_loads(toon_dumps(original)) == original

# GOOD: Tests boundary behavior
def test_confidence_enforcer_downgrades_unsubstantiated():
    """CONFIRMED without test evidence → downgraded to LIKELY."""
    verdict = Verdict(confidence=VerdictConfidence.CONFIRMED, ...)
    corrected = ConfidenceEnforcer().enforce(verdict)
    assert corrected.confidence == VerdictConfidence.LIKELY

# BAD: Tests implementation detail
def test_severity_enum_has_critical():
    """Testing that an enum value exists is not useful."""
    assert Severity.CRITICAL.value == "critical"  # This can never break without compile error

# BAD: Tests mock behavior
def test_attacker_with_mocked_context():
    """Testing what a mock returns tells us nothing about real behavior."""
    context = Mock()  # Everything is fake → test proves nothing
    context.subgraph.nodes = {"fn": Mock(properties={"visibility": "public"})}
    result = attacker.analyze(context)  # Result depends on mock, not real logic
```

**Mock policy:**

| Boundary | Mock? | Replacement |
|----------|-------|-------------|
| LLM API calls | Yes | Recorded response fixtures |
| External tool binaries (slither, mythril) | Yes | Recorded output fixtures |
| Network/HTTP | Yes | Standard practice |
| File system | Prefer `tmp_path` | pytest tmp fixtures |
| Graph building (Slither) | **No** | Use `load_graph` cache |
| Internal classes | **Never** | Use real instances |
| Dataclass creation | **Never** | Just construct real objects |

### Category D: Agent Behavior Tests

**Purpose**: Validate that agent configurations produce reasonable behavior.

**Design:**

```python
# tests/agents/test_agent_behavior.py

class TestAttackerBehavior:
    """Test attacker agent on real vulnerability contexts."""

    def test_attacker_finds_reentrancy_indicators(self):
        """Given a reentrancy-vulnerable graph, attacker should identify attack path."""
        graph = load_graph("ReentrancyVulnerable.sol")
        # Extract real subgraph context (not mocked)
        context = extract_investigation_context(graph, focal_node="fn_withdraw")

        result = AttackerAgent(use_llm=False).analyze(context)

        assert result.category == AttackCategory.REENTRANCY
        assert result.feasibility in (AttackFeasibility.HIGH, AttackFeasibility.MEDIUM)
        assert len(result.attack_steps) > 0

    def test_defender_finds_guard(self):
        """Given a protected function, defender should identify the guard."""
        graph = load_graph("safe/ReentrancySafe.sol")
        context = extract_investigation_context(graph, focal_node="fn_withdraw_safe")

        result = DefenderAgent(use_llm=False).analyze(context)
        assert any("reentrancy_guard" in g.guard_type for g in result.guards_identified)
```

**Key principle**: Use `use_llm=False` mode for deterministic testing with real graph data. LLM behavior is tested via recorded fixture tests (not live API calls).

---

## Mock Reduction Strategy

### Current State

| Category | Files | Mock Occurrences | Verdict |
|----------|-------|-----------------|---------|
| Agent tests (attacker, defender, verifier) | 12 | ~180 | **Remove**: replace with real graph contexts |
| Integration tests | 8 | ~90 | **Remove**: defeat the purpose of integration tests |
| Tool adapter tests | 5 | ~60 | **Keep**: mocking `subprocess.run` and `shutil.which` is correct |
| Runtime/config tests | 10 | ~80 | **Remove**: test real config objects, not mock plumbing |
| Observability/governance | 8 | ~70 | **Keep partial**: mock external loggers, use real policy objects |
| Orchestration tests | 7 | ~50 | **Mixed**: keep pool lifecycle mocks, remove internal mocks |
| Remaining | 32 | ~67 | **Case by case** |

### Action Plan

| Action | Tests Affected | Effort |
|--------|---------------|--------|
| **Phase 1: Replace agent mocks with real graph contexts** | ~12 files, ~180 mocks | Medium — need to create context extraction helpers |
| **Phase 2: Fix "integration" tests that mock everything** | ~8 files, ~90 mocks | Medium — need real fixture contracts |
| **Phase 3: Remove dataclass/enum field-checking tests** | ~30 files, ~800 tests | Easy — just delete |
| **Phase 4: Replace runtime mocks with real objects** | ~10 files, ~80 mocks | Easy — instantiate real configs |

### What to Keep

- `@patch("shutil.which")` — correct, mocks system boundary
- `@patch("subprocess.run")` — correct, mocks external tool execution
- `MagicMock()` for HTTP clients — correct, mocks network boundary
- `tmp_path` fixtures — correct, pytest's file system isolation

### What to Remove

- `Mock()` for graph nodes, contexts, beads, findings — use real objects
- `MagicMock()` for internal classes (AttackerAgent input, VerifierAgent input)
- `@patch` for internal module functions (defeats the test purpose)
- Any mock that creates a "test universe" disconnected from real behavior

---

## Speed Optimization

### Current Bottleneck: Graph Building

Graph building via Slither is the expensive operation (~2-5s per contract). The existing `graph_cache.py` with `@lru_cache` already solves this within a single pytest session.

### Optimization Strategy

| Optimization | Impact | Effort |
|--------------|--------|--------|
| **1. Keep `graph_cache.py` as-is** | Already ~3.79x with `-n auto` | None |
| **2. Pre-built graph fixtures for CI** | Skip Slither in CI for known contracts | Medium |
| **3. Parallel-safe test design** | Already using `--dist loadfile` | None |
| **4. Skip external-tool tests by default** | `@pytest.mark.requires_slither` | Easy |
| **5. Tiered test markers** | `fast` / `standard` / `slow` | Easy |

### Proposed Markers

```python
# conftest.py
def pytest_configure(config):
    config.addinivalue_line("markers", "fast: tests that run without Slither (<0.1s each)")
    config.addinivalue_line("markers", "detection: pattern detection regression tests")
    config.addinivalue_line("markers", "integration: pipeline integration tests")
    config.addinivalue_line("markers", "agent: agent behavior tests")
    config.addinivalue_line("markers", "slow: tests requiring external tools or >5s")
```

### CI Pipeline

```bash
# Fast gate (PR checks, <30s)
pytest -m "fast" -n auto --dist loadfile

# Standard gate (merge to main, <5min)
pytest -m "not slow" -n auto --dist loadfile

# Full suite (nightly, <15min)
pytest -n auto --dist loadfile
```

---

## Honest Metrics Design

### What to Measure

| Metric | Definition | Target | Anti-Pattern |
|--------|-----------|--------|--------------|
| **Detection TP Rate** | Vulns correctly found / total known vulns | 70-85% | 100% = either too few test cases or inflated |
| **Detection FP Rate** | False findings / total findings | <20% | 0% = not testing hard cases |
| **Pattern Coverage** | Patterns with ≥1 TP + ≥1 TN test | >80% | 100% in 1 sprint = fabricated |
| **Test Quality Ratio** | Category A+B tests / total tests | >30% | <10% = inflated with trivial tests |
| **Mock Ratio** | Files with mocks / total test files | <15% | >30% = testing implementation |
| **Corpus Coverage** | Vuln classes with test contracts | >90% | Coverage without TP/TN = meaningless |

### How to Report

```
Detection Regression Dashboard
================================
Total detection tests: 160
  - True Positives verified: 92/110 (83.6%)
  - True Negatives verified: 44/50 (88.0%)
  - Known false positives: 8 (tracked)
  - Known false negatives: 18 (tracked, with issue links)

Pattern Health
================================
  - Patterns with TP tests: 142/556 (25.5%)  ← HONEST, not inflated
  - Patterns untested: 414 (tracked)
  - Patterns with known FPs: 23 (tracked)

Test Suite Health
================================
  - Total tests: ~6,800 (after cleanup from 11,106)
  - Category A (detection): 160
  - Category B (integration): 30
  - Category C (unit): ~6,500
  - Category D (agent): 50
  - Mock ratio: 12% (down from 22%)
```

### Avoiding the "100%/100% = Fabrication" Problem

1. **Always track known failures**: Maintain `tests/known_failures.yaml` with issues that we KNOW patterns miss
2. **Include hard cases**: Every vulnerability class must have a "hard case" contract that we currently fail on
3. **Report ranges, not perfection**: "TP rate: 78-85% depending on pattern tier"
4. **External ground truth**: Use DVDeFi, SmartBugs, SWC benchmarks — not self-authored
5. **Track regressions over time**: Git-tracked metrics file updated by CI

### Regression Tracking

```yaml
# tests/detection_metrics.yaml (updated by CI)
snapshot_date: 2026-02-08
total_detection_tests: 160
tp_tests_passing: 92
tn_tests_passing: 44
known_fp_patterns:
  - pattern: "oracle-001"
    contract: "OracleStalenessPatterns.sol"
    function: "getPriceOnlyRoundIdCheck"
    issue: "#423"
known_fn_patterns:
  - pattern: "reentrancy-001"
    contract: "CrossFunctionReentrancy.sol"
    function: "withdrawAll"
    issue: "#456"
    reason: "Cross-function reentrancy not yet supported"
```

---

## Migration Plan

### Phase 1: Foundation (Week 1-2)

**Goal**: Set up new test categories without breaking existing tests.

1. Create directory structure:
   ```
   tests/
   ├── detection/          # Category A: Detection regression
   │   ├── conftest.py     # Shared helpers: run_patterns, assert_finding_exists
   │   ├── test_reentrancy.py
   │   ├── test_access_control.py
   │   └── ...
   ├── integration/        # Category B: Pipeline (already exists, needs cleanup)
   ├── agents/             # Category D: Agent behavior (already exists, needs refactor)
   ├── unit/               # Category C: Component tests (migrated from root)
   ├── contracts/          # Test Solidity (keep as-is)
   ├── projects/           # Test projects (keep as-is)
   └── fixtures/           # Shared fixtures (keep as-is)
   ```

2. Create shared test helpers:
   ```python
   # tests/detection/conftest.py
   def run_patterns(graph, category=None, pattern_ids=None):
       """Run patterns and return findings."""
       ...

   def assert_finding_exists(findings, pattern_id, function=None, severity=None):
       """Assert a specific finding exists in results."""
       ...

   def assert_no_findings(findings, category=None):
       """Assert no findings for a category (TN test)."""
       ...
   ```

3. Add test markers to `conftest.py`

### Phase 2: Detection Test Build (Week 2-4)

**Goal**: Build the core Category A detection regression suite.

1. Audit existing lens tests (226 tests in `test_external_influence_lens.py` etc.)
2. Reorganize by vulnerability class into `tests/detection/`
3. Add missing TP/TN pairs for uncovered patterns
4. Add hard-case contracts for known limitations
5. **Target: 160 detection tests covering 9 vulnerability classes**

### Phase 3: Mock Cleanup (Week 3-5)

**Goal**: Replace bad mocks with real objects.

1. Agent tests: Create `extract_investigation_context()` helper, replace Mock contexts
2. Integration tests: Remove mocks, use real graph building
3. Delete dataclass enumeration tests
4. **Target: Mock ratio from 22% to <15%**

### Phase 4: Metrics & CI (Week 5-6)

**Goal**: Automated quality tracking.

1. Create `detection_metrics.yaml`, CI update script
2. Add `known_failures.yaml` tracking
3. Set up tiered CI (fast/standard/full)
4. **Target: Dashboard reporting honest metrics**

### Phase 5: Consolidation (Week 6-8)

**Goal**: Stabilize at healthy test count.

1. Remove redundant tests identified in Phase 3
2. Merge overlapping test files
3. Final test count target: ~6,500-7,500 (down from 11,106)
4. **Target: Every remaining test justifies its existence**

---

## Effort Estimate

| Phase | Description | Effort | Dependencies |
|-------|-------------|--------|--------------|
| Phase 1: Foundation | Directory + helpers + markers | 3-4 plans | None |
| Phase 2: Detection Tests | Build Category A suite | 8-10 plans | Phase 1 |
| Phase 3: Mock Cleanup | Remove bad mocks, replace with real | 6-8 plans | Phase 1 |
| Phase 4: Metrics & CI | Tracking + dashboard | 3-4 plans | Phase 2 |
| Phase 5: Consolidation | Test count reduction + cleanup | 4-5 plans | Phase 3 |
| **TOTAL** | | **24-31 plans** | |

### Priority Order

1. **Phase 2 is highest priority** — detection regression tests are the most valuable thing we can build
2. Phase 1 is a prerequisite
3. Phases 3-5 improve quality but don't add new capability

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Existing tests break during migration | Medium | Low | Keep old tests, add new alongside |
| Detection tests reveal real pattern bugs | High | Medium | Track as known failures, fix in pattern work |
| Mock removal exposes broken integration | Medium | High | Good — that's the point. Fix the integration. |
| Test suite gets slower | Low | Medium | Tiered markers + graph cache |
