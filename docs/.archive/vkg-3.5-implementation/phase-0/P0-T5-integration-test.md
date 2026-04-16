# [P0-T5] Phase 0 Integration Test

**Phase**: 0 - Knowledge Foundation
**Task ID**: P0-T5
**Status**: NOT_STARTED
**Priority**: CRITICAL
**Estimated Effort**: 2-3 days
**Actual Effort**: -

---

## Executive Summary

Create comprehensive integration tests that validate the entire Phase 0 knowledge foundation works correctly together. This is the **quality gate** for Phase 0 - we cannot proceed to Phase 1 until these tests pass.

**Critical**: This task includes creating the benchmark suite that will measure BSKG 3.5 improvements throughout development.

---

## Dependencies

### Required Before Starting
- [ ] [P0-T1] Domain Knowledge Graph - Complete
- [ ] [P0-T2] Adversarial Knowledge Graph - Complete
- [ ] [P0-T3] Cross-Graph Linker - Complete
- [ ] [P0-T4] KG Persistence - Complete

### Blocks These Tasks
- ALL Phase 1+ tasks - Phase 0 must pass quality gate

---

## Objectives

### Primary Objectives
1. End-to-end test: Solidity → BSKG → Knowledge Graphs → Cross-Links → Candidates
2. Benchmark suite measuring detection quality
3. Known vulnerability test corpus (10+ contracts with labeled vulnerabilities)
4. Performance regression tests
5. Baseline metrics establishment

### Stretch Goals
1. Automated CI integration
2. Visual report generation

---

## Test Corpus

### Vulnerable Contracts (Must Detect)

| Contract | Vulnerability | Pattern | Spec Violation |
|----------|--------------|---------|----------------|
| `VulnReentrancy.sol` | Classic reentrancy | reentrancy_classic | CEI |
| `VulnReadOnly.sol` | Read-only reentrancy | reentrancy_read_only | CEI |
| `VulnOracle.sol` | Spot price manipulation | oracle_spot_price | price_integrity |
| `VulnFirstDeposit.sol` | First depositor attack | first_depositor | share_fairness |
| `VulnAccessControl.sol` | Missing access control | unprotected_function | authorization |
| `VulnFlashLoan.sol` | Flash loan governance | flash_loan_governance | governance |
| `VulnUpgrade.sol` | Uninitialized proxy | uninitialized_proxy | upgrade_safety |

### Safe Contracts (Must NOT Flag)

| Contract | Protection | Why Safe |
|----------|------------|----------|
| `SafeReentrancy.sol` | ReentrancyGuard | has_reentrancy_guard |
| `SafeOracle.sol` | TWAP + staleness | has_staleness_check, uses_twap |
| `SafeVault.sol` | Virtual shares | has_virtual_shares |
| `SafeAccess.sol` | onlyOwner | has_access_gate |

---

## Validation Tests

### Integration Test Suite

```python
# tests/test_3.5/test_phase0_integration.py

import pytest
from pathlib import Path
from true_vkg.kg.builder import VKGBuilder
from true_vkg.knowledge.domain_kg import DomainKnowledgeGraph
from true_vkg.knowledge.adversarial_kg import AdversarialKnowledgeGraph
from true_vkg.knowledge.linker import CrossGraphLinker


class TestPhase0Integration:
    """Full Phase 0 integration tests."""

    @pytest.fixture
    def knowledge_system(self, tmp_path):
        """Create complete knowledge graph system."""
        # Build code KG from test contract
        builder = VKGBuilder(tmp_path)
        code_kg = builder.build(Path("tests/contracts/VulnReentrancy.sol"))

        # Create domain and adversarial KGs
        domain_kg = DomainKnowledgeGraph()
        domain_kg.load_all()

        adversarial_kg = AdversarialKnowledgeGraph()
        adversarial_kg.load_all()

        # Link everything
        linker = CrossGraphLinker(code_kg, domain_kg, adversarial_kg)
        linker.link_all()

        return code_kg, domain_kg, adversarial_kg, linker

    def test_end_to_end_reentrancy_detection(self, knowledge_system):
        """Test complete pipeline detects reentrancy."""
        code_kg, domain_kg, adversarial_kg, linker = knowledge_system

        # Query for vulnerabilities
        candidates = linker.query_vulnerabilities(min_confidence=0.5)

        # Must find reentrancy vulnerability
        assert len(candidates) > 0

        # Find the vulnerable function
        vuln_candidate = next(
            (c for c in candidates if "withdraw" in c.function_id.lower()),
            None
        )
        assert vuln_candidate is not None, "Must detect withdraw function"

        # Must have correct pattern and spec violation
        assert any("reentrancy" in p.id for p in vuln_candidate.attack_patterns)
        assert len(vuln_candidate.violated_specs) > 0

        # Must be high confidence
        assert vuln_candidate.is_high_confidence()

    def test_false_positive_prevention(self, knowledge_system):
        """Test that safe contract doesn't flag."""
        # Build safe contract
        builder = VKGBuilder(Path("."))
        code_kg = builder.build(Path("tests/contracts/SafeReentrancy.sol"))

        domain_kg = DomainKnowledgeGraph()
        domain_kg.load_all()
        adversarial_kg = AdversarialKnowledgeGraph()
        adversarial_kg.load_all()

        linker = CrossGraphLinker(code_kg, domain_kg, adversarial_kg)
        linker.link_all()

        # Query
        candidates = linker.query_vulnerabilities(min_confidence=0.7)

        # Should NOT find high-confidence reentrancy
        reentrancy_candidates = [
            c for c in candidates
            if any("reentrancy" in p.id for p in c.attack_patterns)
            and c.is_high_confidence()
        ]
        assert len(reentrancy_candidates) == 0, \
            "Should not flag protected contract as reentrancy vulnerable"


class TestBenchmarkSuite:
    """Benchmark tests for measuring detection quality."""

    VULNERABLE_CONTRACTS = [
        ("VulnReentrancy.sol", ["reentrancy"]),
        ("VulnOracle.sol", ["oracle"]),
        ("VulnFirstDeposit.sol", ["first_depositor", "economic"]),
        ("VulnAccessControl.sol", ["access_control", "unprotected"]),
    ]

    SAFE_CONTRACTS = [
        "SafeReentrancy.sol",
        "SafeOracle.sol",
        "SafeVault.sol",
        "SafeAccess.sol",
    ]

    def test_benchmark_precision_recall(self):
        """Calculate precision and recall on test corpus."""
        true_positives = 0
        false_positives = 0
        false_negatives = 0

        # Test vulnerable contracts (should detect)
        for contract, expected_patterns in self.VULNERABLE_CONTRACTS:
            candidates = self._analyze_contract(contract)
            detected = self._check_detection(candidates, expected_patterns)

            if detected:
                true_positives += 1
            else:
                false_negatives += 1
                print(f"MISSED: {contract} - expected {expected_patterns}")

        # Test safe contracts (should not detect)
        for contract in self.SAFE_CONTRACTS:
            candidates = self._analyze_contract(contract)
            if len(candidates) > 0:
                false_positives += 1
                print(f"FALSE POSITIVE: {contract}")

        # Calculate metrics
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        print(f"\n=== BENCHMARK RESULTS ===")
        print(f"Precision: {precision:.2%}")
        print(f"Recall: {recall:.2%}")
        print(f"F1 Score: {f1:.2%}")

        # Phase 0 targets
        assert precision >= 0.70, f"Precision {precision:.2%} below 70% target"
        assert recall >= 0.60, f"Recall {recall:.2%} below 60% target"

    def _analyze_contract(self, contract_name):
        """Analyze a contract and return candidates."""
        # Implementation
        pass

    def _check_detection(self, candidates, expected_patterns):
        """Check if expected patterns were detected."""
        for candidate in candidates:
            for pattern in candidate.attack_patterns:
                for expected in expected_patterns:
                    if expected in pattern.id:
                        return True
        return False
```

### Performance Tests

```python
def test_phase0_performance():
    """Test Phase 0 performance requirements."""
    import time

    # Load KGs
    start = time.time()
    domain_kg = DomainKnowledgeGraph()
    domain_kg.load_all()
    adversarial_kg = AdversarialKnowledgeGraph()
    adversarial_kg.load_all()
    load_time = time.time() - start

    assert load_time < 2.0, f"KG load too slow: {load_time:.2f}s"

    # Build and link
    builder = VKGBuilder(Path("."))
    code_kg = builder.build(Path("tests/contracts/LargeContract.sol"))

    start = time.time()
    linker = CrossGraphLinker(code_kg, domain_kg, adversarial_kg)
    linker.link_all()
    link_time = time.time() - start

    assert link_time < 5.0, f"Linking too slow: {link_time:.2f}s"

    # Query
    start = time.time()
    candidates = linker.query_vulnerabilities(min_confidence=0.5)
    query_time = time.time() - start

    assert query_time < 0.5, f"Query too slow: {query_time:.2f}s"
```

---

## Success Criteria (Quality Gate)

### Must Pass to Proceed to Phase 1

| Criteria | Target | Weight |
|----------|--------|--------|
| All unit tests pass | 100% | BLOCKING |
| Integration tests pass | 100% | BLOCKING |
| Precision on test corpus | >= 70% | BLOCKING |
| Recall on test corpus | >= 60% | BLOCKING |
| No false positives on safe contracts | 100% | BLOCKING |
| KG load time | < 2s | High |
| Link time (100 functions) | < 5s | High |
| Query time | < 0.5s | High |

### Quality Gate Checklist

- [ ] All P0-T1 through P0-T4 completed
- [ ] All unit tests passing (95%+ coverage)
- [ ] Integration tests passing
- [ ] Benchmark metrics meet targets
- [ ] Performance requirements met
- [ ] Documentation complete
- [ ] No critical bugs open

---

## Baseline Metrics File

Create `task/3.5/metrics/baseline.json`:

```json
{
  "version": "3.5.0-phase0",
  "measured_at": "2026-01-XX",
  "detection": {
    "precision": null,
    "recall": null,
    "f1_score": null,
    "false_positive_rate": null
  },
  "performance": {
    "kg_load_time_ms": null,
    "link_time_per_100_functions_ms": null,
    "query_time_ms": null
  },
  "coverage": {
    "vulnerability_classes": null,
    "erc_standards": null,
    "defi_primitives": null,
    "attack_patterns": null
  },
  "test_corpus": {
    "vulnerable_contracts": 7,
    "safe_contracts": 4,
    "true_positives": null,
    "false_positives": null,
    "false_negatives": null
  }
}
```

---

## Implementation Plan

### Phase 1: Test Corpus Creation (1 day)
- [ ] Create vulnerable test contracts
- [ ] Create safe test contracts
- [ ] Label expected findings in manifest

### Phase 2: Integration Test Suite (1 day)
- [ ] Implement end-to-end tests
- [ ] Implement false positive tests
- [ ] Implement edge case tests

### Phase 3: Benchmark Suite (0.5 days)
- [ ] Implement precision/recall calculation
- [ ] Create metrics output file
- [ ] Document measurement methodology

### Phase 4: Quality Gate Validation (0.5 days)
- [ ] Run full test suite
- [ ] Validate all criteria met
- [ ] Create Phase 0 completion report

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-01-02 | Created | Claude |
