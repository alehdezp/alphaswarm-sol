# Pattern Testing Guide

**Comprehensive testing framework for vulnerability detection patterns**

Validation expectations (real‑world runs, evidence packs, ground truth) are defined in:
- `docs/reference/testing-framework.md`

---

## Overview

Pattern testing ensures vulnerability detection is:
- **Accurate**: Low false-positive rate
- **Comprehensive**: Catches real vulnerabilities
- **Implementation-agnostic**: Works across different coding styles and naming conventions

## Quick Reference

| Command | Purpose |
|---------|---------|
| `uv run pytest tests/test_*_lens.py -v` | Run all lens tests |
| `uv run pytest -k "auth-001" -v` | Run specific pattern tests |
| `uv run pytest -v --durations=10` | Run with timing |

---

## 1. Test Project Structure

```
tests/
├── graph_cache.py                    # LRU-cached BSKG builder
├── test_<lens>_lens.py               # Test files per lens
├── contracts/                        # Legacy: individual test contracts
└── projects/                         # Organized test scenarios
    ├── defi-lending/                 # DeFi lending protocol
    │   ├── MANIFEST.yaml             # Pattern tracking
    │   ├── LendingPool.sol
    │   └── ...
    ├── governance-dao/               # Governance/DAO scenarios
    ├── token-vault/                  # Vault and token scenarios
    ├── oracle-price/                 # Oracle/price feed scenarios
    ├── upgrade-proxy/                # Upgrade and proxy scenarios
    └── cross-contract/               # Cross-contract interactions
```

### Project Selection Guidelines

| Project | Use For |
|---------|---------|
| `defi-lending` | Interest rates, collateral, liquidations, flash loans |
| `governance-dao` | Voting, proposals, timelocks, multisig |
| `token-vault` | Deposits, withdrawals, token transfers, shares |
| `oracle-price` | Price feeds, staleness, aggregation |
| `upgrade-proxy` | Proxies, initializers, storage gaps |
| `cross-contract` | Multi-contract interactions, callbacks |

---

## 2. Pattern Rating System

Patterns are rated based on test performance:

| Status | Precision | Recall | Variation | Description |
|--------|-----------|--------|-----------|-------------|
| `draft` | < 70% | < 50% | < 60% | NOT production-ready |
| `ready` | >= 70% | >= 50% | >= 60% | Production with review |
| `excellent` | >= 90% | >= 85% | >= 85% | Minimal review needed |

### Metric Definitions

**Precision** = TP / (TP + FP)
- How often the pattern is correct when it flags something
- Low precision = too many false alarms

**Recall** = TP / (TP + FN)
- How many actual vulnerabilities the pattern catches
- Low recall = misses real vulnerabilities

**Variation Score** = Variations Passed / Total Tested
- How well the pattern handles different implementations
- Tests: naming conventions, modifier styles, inheritance

### Rating Decision Flow

```
precision < 0.70?           → draft
recall < 0.50?              → draft
variation_score < 0.60?     → draft
all >= 0.90/0.85/0.85?      → excellent
otherwise                   → ready
```

---

## 3. Writing Tests

### Load Graphs with Caching

```python
from tests.graph_cache import load_graph

# Legacy: from tests/contracts/
graph = load_graph("NoAccessGate.sol")

# New: from test projects
graph = load_graph("projects/defi-lending/LendingPool.sol")
```

### Standard Test Pattern

```python
"""Authority lens pattern coverage tests."""

from __future__ import annotations
import unittest
from pathlib import Path
from tests.graph_cache import load_graph
from alphaswarm_sol.queries.patterns import PatternEngine, PatternStore

try:
    import slither
    _HAS_SLITHER = True
except Exception:
    _HAS_SLITHER = False


class TestAuth001UnprotectedStateWriter(unittest.TestCase):
    """Tests for auth-001: Unprotected State Writer pattern."""

    def setUp(self) -> None:
        self.patterns = PatternStore(Path("patterns")).load()
        self.engine = PatternEngine()

    def _labels_for(self, findings, pattern_id: str) -> set[str]:
        return {f["node_label"] for f in findings if f["pattern_id"] == pattern_id}

    def _run_pattern(self, contract: str, pattern_id: str):
        graph = load_graph(contract)
        return self.engine.run(graph, self.patterns, pattern_ids=[pattern_id], limit=200)

    # === TRUE POSITIVES ===

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tp_basic(self) -> None:
        """TP: setOwner without access control."""
        findings = self._run_pattern("NoAccessGate.sol", "auth-001")
        self.assertIn("setOwner(address)", self._labels_for(findings, "auth-001"))

    # === TRUE NEGATIVES ===

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tn_with_modifier(self) -> None:
        """TN: setOwner WITH onlyOwner should NOT be flagged."""
        findings = self._run_pattern("AuthorityLens.sol", "auth-001")
        self.assertNotIn("setOwnerProtected(address)", self._labels_for(findings, "auth-001"))

    # === EDGE CASES ===

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_edge_require_msg_sender(self) -> None:
        """Edge: require(msg.sender == owner) should NOT be flagged."""
        findings = self._run_pattern("CustomAccessGate.sol", "auth-001")
        self.assertNotIn("protectedFunction()", self._labels_for(findings, "auth-001"))
```

### Test Categories

Every pattern should have tests in these categories:

| Category | Purpose | Minimum Count |
|----------|---------|---------------|
| **True Positives (TP)** | Verify vulnerable code IS flagged | 3+ |
| **True Negatives (TN)** | Verify safe code is NOT flagged | 2+ |
| **Edge Cases** | Boundary conditions | 2+ |
| **Variations** | Different implementations | 3+ |

---

## 4. Implementation Variations to Test

### Naming Conventions

```solidity
// All should be detected equivalently:
owner / admin / controller / governance / authority
setX / updateX / changeX / modifyX / configureX
```

### Access Control Styles

```solidity
// Style 1: Modifier
function setRate(uint256 rate) external onlyOwner { ... }

// Style 2: Require statement
function setRate(uint256 rate) external {
    require(msg.sender == owner, "Not owner");
    ...
}

// Style 3: If-revert
function setRate(uint256 rate) external {
    if (msg.sender != owner) revert Unauthorized();
    ...
}

// Style 4: OpenZeppelin Ownable
function setRate(uint256 rate) external onlyOwner { ... }

// Style 5: AccessControl
function setRate(uint256 rate) external onlyRole(ADMIN_ROLE) { ... }
```

### Function Patterns

- Direct public/external
- Public wrapper calling internal
- Through inheritance
- Through library delegatecall

---

## 5. Test Solidity Contracts

### Adding to Existing Contracts (Preferred)

```solidity
// In tests/projects/defi-lending/LendingPool.sol

// === auth-001: Unprotected State Writer ===

// VULNERABLE: No access control (TP)
function setInterestRate(uint256 rate) external {
    interestRate = rate;  // auth-001 should flag this
}

// SAFE: Has access control (TN)
function setInterestRateProtected(uint256 rate) external onlyOwner {
    interestRate = rate;  // auth-001 should NOT flag this
}

// VARIATION: Different naming (TP)
function updateBorrowRate(uint256 rate) external {
    borrowRate = rate;  // auth-001 should flag this
}
```

### When to Create New Files

Only create new `.sol` files when:
- Testing requires different contract structure (inheritance, library)
- Contract would exceed ~500 lines
- Testing cross-contract scenarios

---

## 6. MANIFEST.yaml Format

Each test project tracks patterns tested:

```yaml
# tests/projects/defi-lending/MANIFEST.yaml
project: defi-lending
description: DeFi lending protocol test scenarios
max_files: 30
current_files: 12

patterns:
  auth-001:
    files: [LendingPool.sol, CollateralManager.sol]
    functions:
      vulnerable: [setInterestRate, updateOracle]
      safe: [setInterestRateProtected, updateOracleOnlyOwner]
    last_updated: "2025-01-15"

  vm-001:
    files: [LendingPool.sol, FlashLoan.sol]
    functions:
      vulnerable: [withdraw, flashLoan]
      safe: [withdrawCEI, flashLoanGuarded]
    last_updated: "2025-01-14"

notes: |
  Suitable patterns:
  - Authority lens (auth-*): Access control
  - Value Movement (vm-*): Reentrancy, flash loans
```

---

## 7. Using the pattern-tester Agent

The `pattern-tester` agent automates comprehensive pattern testing. Use it when:

1. **Testing new patterns** created by `vrs-pattern-architect`
2. **Evaluating pattern quality** across a lens
3. **Validating false-positive rates**

### Invoking the Agent

The agent is typically invoked automatically after pattern creation, or manually:

```
# In Claude Code conversation:
"Test the new auth-120 pattern I just created"
"Review and test all authority lens patterns"
"What's the false-positive rate for vm-001?"
```

### Agent Workflow

```
Pattern YAML → pattern-tester agent
    ├── Reads pattern match conditions
    ├── Selects or creates test project
    ├── Adds test functions to contracts
    ├── Writes Python test cases
    ├── Runs tests
    ├── Calculates metrics
    ├── Assigns rating (draft/ready/excellent)
    └── Updates pattern YAML with test_coverage
```

### Test Report Format

The agent produces structured reports:

```markdown
## Pattern Test Report: auth-001

### Test Summary
- True Positives: 8
- True Negatives: 5
- False Positives: 1
- False Negatives: 0
- Edge Cases Tested: 3

### Metrics
- Precision: 0.89
- Recall: 1.00
- Variation Score: 0.88

### Assigned Rating: ready

### Reasoning
Pattern reliably detects unprotected state writers across
owner/admin/controller naming conventions. One false positive
on internal helper function with external visibility.

### Improvement Suggestions
Add edge case for constructor initialization.

### Files Modified
- tests/projects/defi-lending/LendingPool.sol
- tests/test_authority_lens.py
- patterns/authority-lens.yaml (status: ready)
```

---

## 8. Quality Checklist

Before a pattern can be marked `ready`:

- [ ] **3+ True Positives**: Different implementations flagged
- [ ] **2+ True Negatives**: Safe code NOT flagged
- [ ] **2+ Edge Cases**: Boundary conditions tested
- [ ] **3+ Variations**: Naming/style variations tested
- [ ] **Tests Pass**: `uv run pytest tests/test_<lens>_lens.py -v`
- [ ] **Metrics Calculated**: precision, recall, variation_score
- [ ] **Rating Assigned**: Based on decision tree
- [ ] **Pattern YAML Updated**: status and test_coverage fields
- [ ] **MANIFEST Updated**: Pattern tracked in project

---

## 9. Common Mistakes

| Mistake | Correct Approach |
|---------|------------------|
| Creating new `.sol` for every test | Add functions to existing contracts |
| Only testing happy path | Include TN and edge cases |
| Not testing variations | Test naming conventions, styles |
| Forgetting MANIFEST update | Track all tested patterns |
| Guessing ratings | Calculate metrics first |

---

## 10. Advanced: Renamed Contract Testing

For implementation-agnostic validation, patterns should work on renamed contracts:

```python
STANDARD_RENAMES = {
    'owner': 'controller',
    'admin': 'supervisor',
    'withdraw': 'removeFunds',
    'balances': 'userDeposits',
    'onlyOwner': 'requiresController',
}
```

**Target**: Rename detection rate >= 95% for `ready`, 100% for `excellent`.

See `tests/contracts/renamed/` for renamed contract examples.

---

## 11. Running Tests

```bash
# All lens tests
uv run pytest tests/test_*_lens.py -v

# Specific pattern
uv run pytest -k "auth-001" -v

# With coverage
uv run pytest tests/test_authority_lens.py --cov=alphaswarm_sol.queries.patterns

# With timing
uv run pytest -v --durations=10

# Specific project tests
uv run pytest tests/test_authority_lens.py::AuthorityLensTests::test_authority_patterns -v
```

---

## 12. Batch Quality Benchmarks

Batch discovery quality is measured and tracked using the benchmark runner. This ensures batch discovery improves results without regression.

### Running Benchmarks

```bash
# Run benchmark with console output
python scripts/benchmarks/batch_quality.py

# Save results to JSON for CI
python scripts/benchmarks/batch_quality.py --output results.json

# Compare against baseline
python scripts/benchmarks/batch_quality.py --compare baseline.json --output results.json

# CI mode (non-zero exit on regression)
python scripts/benchmarks/batch_quality.py --ci --output results.json

# Custom thresholds
python scripts/benchmarks/batch_quality.py --precision-threshold 0.03 --output results.json
```

### Benchmark Metrics

The benchmark measures these quality dimensions:

| Metric | Description | Threshold |
|--------|-------------|-----------|
| **Precision Delta** | Batch precision - Sequential precision | >= -0.05 |
| **Recall Delta** | Batch recall - Sequential recall | >= -0.05 |
| **Batch F1** | F1 score for batch discovery | >= 0.60 |
| **Novelty Yield** | Novel patterns found by batch | >= 0.10 |
| **Normalized Entropy** | Evidence diversity | >= 0.30 |

### JSON Output Format

The benchmark outputs CI-ready JSON:

```json
{
  "timestamp": "2026-01-27T22:15:00Z",
  "version": "1.0.0",
  "status": "passed",
  "config": {
    "precision_threshold": 0.05,
    "recall_threshold": 0.05,
    "novelty_threshold": 0.10,
    "entropy_threshold": 0.30
  },
  "sequential_metrics": {
    "precision": 0.75,
    "recall": 0.70,
    "f1_score": 0.72
  },
  "batch_metrics": {
    "precision": 0.80,
    "recall": 0.78,
    "f1_score": 0.79
  },
  "regression_checks": [
    {
      "check_name": "precision_delta",
      "current_value": 0.05,
      "status": "passed"
    }
  ],
  "summary": {
    "total_checks": 5,
    "passed": 5,
    "regressions": 0
  }
}
```

### CI Integration

Add to your CI workflow:

```yaml
# .github/workflows/benchmark.yml
- name: Run batch quality benchmark
  run: |
    python scripts/benchmarks/batch_quality.py \
      --ci \
      --compare benchmarks/baseline.json \
      --output benchmarks/current.json

- name: Upload benchmark results
  uses: actions/upload-artifact@v4
  with:
    name: benchmark-results
    path: benchmarks/current.json
```

### Test Coverage

Batch quality metrics are covered by dedicated tests:

```bash
# Run all batch quality metric tests
uv run pytest tests/metrics/ -v

# Individual test files
uv run pytest tests/metrics/test_batch_quality.py -v    # Precision/recall/novelty/entropy
uv run pytest tests/metrics/test_calibration.py -v      # Confidence calibration
uv run pytest tests/metrics/test_budget_pareto.py -v    # Budget-quality Pareto
```

---

---

## 13. VulnDocs Validation Pipeline

When making changes to `vulndocs/`, the validation pipeline is **mandatory**. Use `/vrs-validate-vulndocs` to orchestrate the full validation workflow.

### Quick Reference

```bash
# Validate all vulndocs changes (standard mode)
/vrs-validate-vulndocs

# Quick validation (prevalidator + schema only) for development
/vrs-validate-vulndocs --mode quick

# Full GA-level validation for release
/vrs-validate-vulndocs --mode thorough
```

### Validation Subagents

| Agent | Purpose | Model |
|-------|---------|-------|
| vrs-prevalidator | URL provenance, schema, duplicate checks | claude-haiku-4.5 |
| vrs-corpus-curator | Corpus integrity, ground truth verification | claude-sonnet-4 |
| vrs-pattern-verifier | Evidence gates for Tier B/C patterns | claude-sonnet-4 |
| vrs-benchmark-runner | Precision/recall metrics computation | claude-haiku-4 |
| vrs-mutation-tester | Variant generation for robustness | claude-haiku-4 |
| vrs-regression-hunter | Accuracy degradation detection | claude-sonnet-4 |
| vrs-gap-finder-lite | Fast coverage and FP hotspot scan | claude-sonnet-4.5 |

### Quality Gates

The pipeline enforces these blocking gates:

| Gate | Target |
|------|--------|
| Precision | >= 85% |
| Recall (critical) | >= 95% |
| Recall (high) | >= 85% |
| Schema compliance | 100% |
| Provenance verified | 100% |

For full documentation, see [VulnDocs Framework Guide](vulndocs.md#mandatory-validation-pipeline).

---

## Related Documentation

- [Pattern Authoring Guide](patterns.md) - Creating patterns
- [Property Reference](../reference/properties.md) - All 50+ properties
- [Operations Reference](../reference/operations.md) - Semantic operations
- [VulnDocs Framework Guide](vulndocs.md) - VulnDocs structure and validation

---

---

## 14. GA Validation Framework (Phase 7.3)

AlphaSwarm.sol uses a comprehensive validation framework for GA release verification.

### Validation Architecture

```
Controller (subscription) → claude-code-controller → Subject (isolated) → Transcript → EXTERNAL ground truth
```

### Testing Skills

| Skill | Purpose |
|-------|---------|
| `/vrs-full-testing` | Super-orchestrator for all validation |
| `/vrs-agentic-testing` | Agentic test orchestration |
| `/vrs-workflow-test` | Workflow testing |
| `/vrs-claude-code-agent-teams-testing` | claude-code-agent-teams-based test isolation |

### Validation Rules

All skill/agent/workflow testing MUST follow `.planning/testing/rules/canonical/RULES-ESSENTIAL.md`:

1. **LIVE Mode Required** - Use LIVE mode, not mock
2. **claude-code-agent-teams-Based** - Interactive tests MUST use claude-code-agent-teams isolation
3. **External Ground Truth** - Ground truth from external sources only
4. **Anti-Fabrication** - Authentic transcripts, realistic duration

### Key Metrics (Phase 7.3)

| Metric | Current |
|--------|---------|
| DVDeFi Detection | 84.6% (11/13) |
| Gauntlet Detection | 78.2% (G4 PASS) |
| Test Count | 2,000+ |
| Test Files | 245 |

### Test Performance (Phase 8)

```bash
# Parallel execution (3.79x faster)
uv run pytest tests/ -n auto --dist loadfile
```

---

*Version 1.3 | February 2026*
