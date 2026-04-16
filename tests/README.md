# AlphaSwarm.sol Test Suite

**Comprehensive testing for vulnerability detection patterns**

---

## Quick Start

```bash
# Run all tests
uv run python -m unittest discover tests -v

# Run lens tests only
uv run pytest tests/test_*_lens.py -v

# Run specific pattern
uv run pytest -k "auth-001" -v
```

---

## Directory Structure

```
tests/
├── README.md                         # This file
├── QUICK_START_GUIDE.md              # Detailed running guide
├── graph_cache.py                    # LRU-cached BSKG builder
│
├── contracts/                        # Individual test contracts
│   ├── AuthorityLens.sol             # Authority pattern tests
│   ├── ValueMovementLens.sol         # Reentrancy/value tests
│   ├── ExternalInfluenceLens.sol     # Oracle/external tests
│   ├── ArithmeticLens.sol            # Arithmetic tests
│   ├── LivenessLens.sol              # DoS/liveness tests
│   └── ...                           # ~150+ contracts
│
├── projects/                         # Organized test scenarios
│   ├── defi-lending/                 # Lending protocol (Aave-like)
│   │   ├── MANIFEST.yaml             # Pattern tracking
│   │   └── *.sol
│   ├── governance-dao/               # DAO governance
│   ├── token-vault/                  # Vault operations
│   ├── oracle-price/                 # Price feeds
│   ├── upgrade-proxy/                # Proxy patterns
│   └── cross-contract/               # Multi-contract
│
└── test_*.py                         # Python test files
    ├── test_authority_lens.py        # 120+ authority patterns
    ├── test_value_movement_lens.py   # 56+ value movement patterns
    ├── test_queries_liveness.py      # DoS patterns
    ├── test_queries_external_influence.py  # Oracle patterns
    ├── test_arithmetic_lens.py       # Arithmetic patterns
    └── ...
```

---

## Test Categories

### By Lens

| Lens | Test File | Patterns |
|------|-----------|----------|
| Authority | `test_authority_lens.py` | auth-001 to auth-120 |
| Value Movement | `test_value_movement_lens.py` | vm-001 to vm-056+ |
| External Influence | `test_queries_external_influence.py` | ext-* |
| Arithmetic | `test_arithmetic_lens.py` | arith-* |
| Liveness | `test_queries_liveness.py` | live-* |
| Ordering/Upgradability | `test_ordering_upgradability_lens.py` | ord-* |

### By Purpose

| Test File | Purpose |
|-----------|---------|
| `test_schema_snapshot.py` | Schema integrity validation |
| `test_full_coverage_patterns.py` | Cross-lens pattern tests |
| `test_semgrep_coverage.py` | Semgrep rule parity |
| `test_semgrep_vkg_parity.py` | BSKG vs Semgrep comparison |

---

## Loading Test Graphs

Use the cached loader for performance:

```python
from tests.graph_cache import load_graph

# From tests/contracts/
graph = load_graph("NoAccessGate.sol")

# From test projects
graph = load_graph("projects/defi-lending/LendingPool.sol")
```

---

## Writing New Tests

### Standard Pattern Test

```python
"""Authority lens pattern tests."""

from __future__ import annotations
import unittest
from pathlib import Path
from tests.graph_cache import load_graph
from true_vkg.queries.patterns import PatternEngine, PatternStore

try:
    import slither
    _HAS_SLITHER = True
except Exception:
    _HAS_SLITHER = False


class TestAuthPattern(unittest.TestCase):
    def setUp(self) -> None:
        self.patterns = PatternStore.load_vulndocs_patterns(Path("vulndocs"))
        self.engine = PatternEngine()

    def _labels_for(self, findings, pattern_id: str) -> set[str]:
        return {f["node_label"] for f in findings if f["pattern_id"] == pattern_id}

    def _run_pattern(self, contract: str, pattern_id: str):
        graph = load_graph(contract)
        return self.engine.run(graph, self.patterns, pattern_ids=[pattern_id], limit=200)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tp_vulnerable_flagged(self) -> None:
        """TP: Vulnerable code should be flagged."""
        findings = self._run_pattern("NoAccessGate.sol", "auth-001")
        self.assertIn("setOwner(address)", self._labels_for(findings, "auth-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tn_safe_not_flagged(self) -> None:
        """TN: Safe code should NOT be flagged."""
        findings = self._run_pattern("AuthorityLens.sol", "auth-001")
        self.assertNotIn("setOwnerProtected(address)", self._labels_for(findings, "auth-001"))
```

### Test Categories Required

| Category | Description | Minimum |
|----------|-------------|---------|
| **TP** | Vulnerable code flagged | 3+ |
| **TN** | Safe code NOT flagged | 2+ |
| **Edge** | Boundary conditions | 2+ |
| **Variation** | Different implementations | 3+ |

---

## Test Projects

### MANIFEST.yaml Format

```yaml
project: defi-lending
description: DeFi lending protocol scenarios
max_files: 30
current_files: 12

patterns:
  auth-001:
    files: [LendingPool.sol]
    functions:
      vulnerable: [setInterestRate]
      safe: [setInterestRateProtected]
    last_updated: "2025-01-15"

notes: |
  Suitable for: auth-*, vm-*, ext-*
```

### Project Guidelines

| Constraint | Limit |
|------------|-------|
| Max files per project | 30 |
| Prefer | Add functions to existing contracts |
| Create new file when | Structure differs, >500 lines, cross-contract |

---

## Running Tests

```bash
# All tests
uv run python -m unittest discover tests -v

# Lens tests
uv run pytest tests/test_*_lens.py -v

# Specific pattern
uv run pytest -k "auth-001" -v

# With coverage
uv run pytest tests/test_authority_lens.py --cov=true_vkg.queries.patterns

# With timing
uv run pytest -v --durations=10

# Skip Slither tests (faster)
uv run pytest tests/ -v -k "not slither"
```

---

## Pattern Quality Rating

Patterns are rated by the `vrs-test-conductor` agent:

| Status | Precision | Recall | Variation |
|--------|-----------|--------|-----------|
| `draft` | < 70% | < 50% | < 60% |
| `ready` | >= 70% | >= 50% | >= 60% |
| `excellent` | >= 90% | >= 85% | >= 85% |

---

## Troubleshooting

### Slither Not Available

Tests requiring Slither are automatically skipped:

```bash
pip install slither-analyzer
```

### Graph Cache Issues

If test contracts changed, clear the cache:

```bash
rm -rf .vrs/
```

### Semgrep Tests

Semgrep tests require separate installation:

```bash
pip install semgrep
uv run pytest tests/test_semgrep_*.py -v -m semgrep
```

---

## Related Documentation

- [Pattern Testing Guide](../docs/guides/testing-basics.md) - Full testing documentation
- [Pattern Authoring](../docs/guides/patterns-basics.md) - Creating patterns
- [QUICK_START_GUIDE.md](QUICK_START_GUIDE.md) - Running tests
