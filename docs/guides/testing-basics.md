# Pattern Testing Basics

**Getting started with testing vulnerability detection patterns.**

**For advanced topics (workflow harness, reliability, VulnDocs validation), see [Testing Advanced Guide](testing-advanced.md).**

---

## Overview

Pattern testing ensures vulnerability detection is:
- **Accurate**: Low false-positive rate
- **Comprehensive**: Catches real vulnerabilities
- **Implementation-agnostic**: Works across coding styles

---

## Quick Reference

```bash
# Run all lens tests
uv run pytest tests/test_*_lens.py -v

# Specific pattern
uv run pytest -k "auth-001" -v

# With timing
uv run pytest -v --durations=10
```

---

## Test Project Structure

```
tests/
├── graph_cache.py                    # LRU-cached BSKG builder
├── test_<lens>_lens.py               # Test files per lens
└── projects/                         # Organized test scenarios
    ├── defi-lending/                 # DeFi lending protocol
    │   └── MANIFEST.yaml             # Pattern tracking
    ├── governance-dao/               # Governance/DAO scenarios
    ├── token-vault/                  # Vault and token scenarios
    └── oracle-price/                 # Oracle scenarios
```

### Project Selection

| Project | Use For |
|---------|---------|
| `defi-lending` | Interest rates, collateral, flash loans |
| `governance-dao` | Voting, proposals, timelocks |
| `token-vault` | Deposits, withdrawals, shares |
| `oracle-price` | Price feeds, staleness |

---

## Pattern Rating System

| Status | Precision | Recall | Description |
|--------|-----------|--------|-------------|
| `draft` | < 70% | < 50% | NOT production-ready |
| `ready` | >= 70% | >= 50% | Production with review |
| `excellent` | >= 90% | >= 85% | Minimal review needed |

### Metric Definitions

**Precision** = TP / (TP + FP)
- How often the pattern is correct when it flags something

**Recall** = TP / (TP + FN)
- How many actual vulnerabilities the pattern catches

**Variation Score** = Variations Passed / Total Tested
- How well the pattern handles different implementations

---

## Writing Tests

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
from tests.graph_cache import load_graph
from alphaswarm_sol.queries.patterns import PatternEngine, PatternStore

class TestAuth001(unittest.TestCase):

    def setUp(self):
        self.patterns = PatternStore.load_vulndocs_patterns(Path("vulndocs"))
        self.engine = PatternEngine()

    def _run_pattern(self, contract, pattern_id):
        graph = load_graph(contract)
        return self.engine.run(graph, self.patterns, pattern_ids=[pattern_id])

    # TRUE POSITIVE
    def test_tp_basic(self):
        findings = self._run_pattern("NoAccessGate.sol", "auth-001")
        labels = {f["node_label"] for f in findings if f["pattern_id"] == "auth-001"}
        self.assertIn("setOwner(address)", labels)

    # TRUE NEGATIVE
    def test_tn_with_modifier(self):
        findings = self._run_pattern("AuthorityLens.sol", "auth-001")
        labels = {f["node_label"] for f in findings if f["pattern_id"] == "auth-001"}
        self.assertNotIn("setOwnerProtected(address)", labels)
```

### Test Categories

| Category | Purpose | Minimum |
|----------|---------|---------|
| **True Positives (TP)** | Vulnerable code IS flagged | 3+ |
| **True Negatives (TN)** | Safe code NOT flagged | 2+ |
| **Edge Cases** | Boundary conditions | 2+ |
| **Variations** | Different implementations | 3+ |

---

## Implementation Variations to Test

### Naming Conventions

```solidity
// All should be detected equivalently:
owner / admin / controller / governance
setX / updateX / changeX / modifyX
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
```

---

## Test Solidity Contracts

### Adding to Existing Contracts (Preferred)

```solidity
// In tests/projects/defi-lending/LendingPool.sol

// VULNERABLE: No access control (TP)
function setInterestRate(uint256 rate) external {
    interestRate = rate;  // auth-001 should flag this
}

// SAFE: Has access control (TN)
function setInterestRateProtected(uint256 rate) external onlyOwner {
    interestRate = rate;  // auth-001 should NOT flag
}
```

### When to Create New Files

Only create new `.sol` files when:
- Testing requires different contract structure
- Contract would exceed ~500 lines
- Testing cross-contract scenarios

---

## Quality Checklist

Before a pattern can be marked `ready`:

- [ ] **3+ True Positives**: Different implementations flagged
- [ ] **2+ True Negatives**: Safe code NOT flagged
- [ ] **2+ Edge Cases**: Boundary conditions tested
- [ ] **3+ Variations**: Naming/style variations tested
- [ ] **Tests Pass**: `uv run pytest tests/test_<lens>_lens.py -v`
- [ ] **Rating Assigned**: Based on decision tree
- [ ] **Pattern YAML Updated**: status and test_coverage fields

---

## Running Tests

```bash
# All lens tests
uv run pytest tests/test_*_lens.py -v

# Specific pattern
uv run pytest -k "auth-001" -v

# With coverage
uv run pytest tests/test_authority_lens.py --cov=alphaswarm_sol.queries.patterns

# Parallel execution (3.79x faster)
uv run pytest tests/ -n auto --dist loadfile
```

---

## Related Documentation

- [Testing Advanced Guide](testing-advanced.md) - Batch benchmarks, VulnDocs validation, GA framework
- [Pattern Basics](patterns-basics.md) - Creating patterns
- [Property Reference](../reference/properties.md) - All 275 emitted properties

---

*Version 1.3 | February 2026*
