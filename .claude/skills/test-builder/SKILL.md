---
name: test-builder
description: |
  Test construction guidelines derived from Phase 8 performance research. Ensures tests are built for parallel execution compatibility and optimal performance.

  **AUTO-INVOKE** when:
  - Writing new test files
  - Adding test functions to existing files
  - Creating test fixtures
  - Modifying tests/conftest.py
  - Working on any tests/*.py file

  Invoke patterns:
  - "write tests for...", "create tests for...", "add tests for..."
  - "build test suite for...", "test this feature..."
  - /test-builder (explicit invocation)

  This skill ensures all tests follow the performance guidelines that achieve 3.79x speedup.

# Slash command invocation
slash_command: test-builder

# Tool permissions
tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash(uv run pytest*)        # Run tests
  - Bash(uv run alphaswarm*)      # Build graphs for test contracts
---

# Test Builder - Performance-Optimized Test Construction

You are constructing tests for AlphaSwarm.sol. Follow these guidelines derived from Phase 8 performance research to ensure tests run optimally in parallel execution.

## Critical Performance Facts

```
Baseline (serial):     1,178.75s (19m 38s)
With xdist:            311.34s   (5m 11s)
Speedup:               3.79x
Configuration:         pytest -n auto --dist loadfile
```

The `--dist loadfile` mode groups tests by source file to maximize `load_graph()` LRU cache hits.

---

## Reasoning-Aware Test Design

When designing tests, consider which **reasoning moves** the test exercises:

- **HYPOTHESIS_FORMATION**: Does the test require formulating a vulnerability hypothesis from graph structure?
- **QUERY_FORMULATION**: Does it test the ability to construct effective BSKG queries?
- **RESULT_INTERPRETATION**: Does it validate correct interpretation of query results?
- **EVIDENCE_INTEGRATION**: Does it require combining evidence from multiple sources?
- **CONTRADICTION_HANDLING**: Does it present conflicting signals that must be reconciled?
- **CONCLUSION_SYNTHESIS**: Does it validate the final verdict reasoning?

Use the **coverage radar** (4-axis heat map: vulnerability class, semantic operation, reasoning skill, graph query pattern) to identify what needs testing. Before writing new tests, check which radar cells are cold — those are your highest-value targets.

### Difficulty Scaling Tiers

Design test scenarios at three difficulty tiers:

| Tier | Difficulty | Example |
|------|-----------|---------|
| **A** | Obvious, single-function | Missing `onlyOwner` on public setter |
| **B** | Hidden, cross-function | Reentrancy via callback in helper function |
| **C** | Adversarial, multi-contract | Flash-loan-enabled governance takeover across 3 contracts |

Aim for a balanced mix: ~40% Tier A, ~40% Tier B, ~20% Tier C.

---

## Test Construction Guidelines

### 1. Group Related Tests in Same File

**WHY:** `--dist loadfile` sends all tests from a file to the same worker. Tests sharing the same graph benefit from cache hits.

```python
# GOOD: All LendingPool tests in one file
# tests/test_lending_pool.py
class TestLendingPoolReentrancy:
    def test_deposit_reentrancy(self, lending_pool_graph):
        ...
    def test_withdraw_reentrancy(self, lending_pool_graph):
        ...
    def test_flashloan_reentrancy(self, lending_pool_graph):
        ...

# BAD: Split across files (graph rebuilt per worker)
# tests/test_deposit.py
# tests/test_withdraw.py
# tests/test_flashloan.py
```

### 2. Use `load_graph()` from `tests/graph_cache.py`

**WHY:** The `@lru_cache` decorator amortizes graph construction across tests in the same process.

```python
from tests.graph_cache import load_graph

def test_reentrancy_detection():
    graph = load_graph("LendingPool")  # Cached if called before
    ...
```

**Cache Stats (from Phase 8):**
- 620 load_graph() calls
- 102 unique contracts
- 6.1x average cache efficiency

### 3. Avoid Session-Scoped Fixtures for Graphs

**WHY:** Session scope doesn't help in parallel execution (each worker has its own process).

```python
# BAD: Session scope doesn't help with xdist
@pytest.fixture(scope="session")
def shared_graph():
    return build_kg("contract.sol")

# GOOD: Use load_graph() with LRU cache
@pytest.fixture
def contract_graph():
    return load_graph("Contract")
```

### 4. Keep Tests Isolated (No Shared Mutable State)

**WHY:** Parallel workers run independently. Shared state causes flaky tests.

```python
# BAD: Shared mutable state
_results = []

def test_first():
    _results.append(1)

def test_second():
    assert len(_results) == 1  # Fails in parallel

# GOOD: Each test is isolated
def test_first():
    results = []
    results.append(1)
    assert len(results) == 1
```

### 5. Use Unique Temp Directories

**WHY:** Parallel workers may collide on shared paths.

```python
# BAD: Shared temp path
def test_export():
    path = "/tmp/export.json"
    ...

# GOOD: Use pytest tmp_path fixture
def test_export(tmp_path):
    path = tmp_path / "export.json"
    ...
```

### 6. Minimize Fixture Setup Time

**WHY:** Top 3 slowest tests (37s each) are dominated by fixture setup.

```python
# BAD: Heavy fixture used once
@pytest.fixture
def full_analysis():
    graph = build_kg("LargeContract.sol")  # 7.4s
    analyze_all(graph)                      # 3.2s
    return graph

def test_single_property(full_analysis):
    ...  # Only uses one property

# GOOD: Lazy evaluation or split fixtures
@pytest.fixture
def graph():
    return load_graph("LargeContract")  # Cached

def test_single_property(graph):
    result = analyze_single_property(graph)  # Fast
    ...
```

---

## Test File Naming Conventions

Follow these patterns for test organization:

| Pattern | Purpose | Example |
|---------|---------|---------|
| `test_{feature}.py` | Feature tests | `test_reentrancy_detection.py` |
| `test_{lens}_lens.py` | Pattern lens tests | `test_value_movement_lens.py` |
| `test_{component}.py` | Component unit tests | `test_builder.py` |
| `test_{contract}.py` | Contract-specific tests | `test_lending_pool.py` |

---

## Test Contract Organization

Test contracts live in `tests/contracts/` and `tests/projects/`:

```
tests/
├── contracts/           # Simple test contracts
│   ├── Reentrancy.sol
│   ├── AccessControl.sol
│   └── ...
├── projects/            # Complex multi-contract projects
│   ├── defi-lending/
│   │   ├── LendingPool.sol
│   │   ├── FlashLoan.sol
│   │   └── ...
│   └── ...
└── graph_cache.py       # load_graph() with LRU cache
```

**Creating Test Contracts:**

1. Add `.sol` file to `tests/contracts/` or `tests/projects/`
2. Include both vulnerable and safe variants
3. Name functions descriptively (the graph is name-agnostic)

```solidity
// tests/contracts/Reentrancy.sol
contract VulnerableReentrancy {
    // Vulnerable: external call before state update
    function withdraw(uint amount) public {
        require(balances[msg.sender] >= amount);
        (bool ok,) = msg.sender.call{value: amount}("");
        require(ok);
        balances[msg.sender] -= amount;  // State update after call
    }
}

contract SafeReentrancy {
    // Safe: state update before external call (CEI pattern)
    function withdraw(uint amount) public {
        require(balances[msg.sender] >= amount);
        balances[msg.sender] -= amount;  // State update first
        (bool ok,) = msg.sender.call{value: amount}("");
        require(ok);
    }
}
```

---

## Running Tests

### Full Suite (Parallel)
```bash
# Default configuration (from pyproject.toml)
uv run pytest tests/

# Explicit parallel execution
uv run pytest tests/ -n auto --dist loadfile
```

### Single File
```bash
uv run pytest tests/test_reentrancy.py -v
```

### Incremental (Development)
```bash
# First run builds .testmondata
uv run pytest tests/ --testmon

# Subsequent runs only execute affected tests
uv run pytest tests/ --testmon
```

### Specific Pattern
```bash
uv run pytest -k "reentrancy" -v
```

---

## Performance Checklist

Before committing new tests, verify:

- [ ] Tests using same graph are in same file
- [ ] Using `load_graph()` from `graph_cache.py`
- [ ] No session-scoped fixtures for graphs
- [ ] No shared mutable state between tests
- [ ] Using `tmp_path` fixture for temp files
- [ ] Heavy setup is amortized across multiple tests
- [ ] Tests pass with `pytest -n auto --dist loadfile`

---

## Anti-Patterns to Avoid

### 1. One Test Per File
```python
# BAD: Defeats loadfile distribution benefit
# tests/test_deposit.py (1 test)
# tests/test_withdraw.py (1 test)
# tests/test_borrow.py (1 test)

# GOOD: Group related tests
# tests/test_lending_operations.py (3+ tests)
```

### 2. Global State Modification
```python
# BAD: Global state breaks parallel execution
import my_module
my_module.DEBUG = True

# GOOD: Use fixtures or monkeypatch
@pytest.fixture
def debug_mode(monkeypatch):
    monkeypatch.setattr("my_module.DEBUG", True)
```

### 3. Hardcoded Ports/Paths
```python
# BAD: Port collision in parallel
def test_server():
    server = start_server(port=8080)

# GOOD: Dynamic ports
def test_server():
    server = start_server(port=0)  # OS assigns free port
```

### 4. Sleep-Based Synchronization
```python
# BAD: Flaky in parallel, wastes time
def test_async_operation():
    start_operation()
    time.sleep(5)  # Hope it's done
    assert is_complete()

# GOOD: Polling with timeout
def test_async_operation():
    start_operation()
    wait_for_completion(timeout=5)
    assert is_complete()
```

---

## Configuration Reference

From `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
norecursedirs = ["examples"]
markers = ["semgrep: semgrep coverage and parity tests"]
addopts = "-n auto --dist loadfile"
```

From `.gitignore`:

```
.testmondata
```

---

## Example: Creating Tests for New Feature

```python
# tests/test_oracle_manipulation.py
"""Tests for oracle manipulation detection pattern."""

from tests.graph_cache import load_graph

class TestOracleManipulationDetection:
    """All oracle tests in one file for cache efficiency."""

    def test_direct_price_manipulation(self):
        """Detect direct oracle price read without validation."""
        graph = load_graph("VulnerableOracle")
        findings = query_pattern(graph, "oracle-manipulation")
        assert len(findings) >= 1
        assert any(f.function == "getPrice" for f in findings)

    def test_stale_price_check(self):
        """Detect missing staleness check."""
        graph = load_graph("VulnerableOracle")  # Cache hit!
        findings = query_pattern(graph, "stale-oracle")
        assert len(findings) >= 1

    def test_safe_oracle_excluded(self):
        """Verify safe oracle patterns are not flagged."""
        graph = load_graph("SafeOracle")
        findings = query_pattern(graph, "oracle-manipulation")
        assert len(findings) == 0

    def test_twap_protection(self):
        """Verify TWAP-protected oracle is not flagged."""
        graph = load_graph("SafeOracle")  # Cache hit!
        findings = query_pattern(graph, "oracle-manipulation")
        assert not any(f.function == "getTWAPPrice" for f in findings)
```

---

## Notes

- Phase 8 research achieved **3.79x speedup** (73.6% faster)
- `loadfile` distribution is critical for `load_graph()` cache efficiency
- Always run full suite with parallel execution before merging
- Use `pytest --testmon` for rapid local iteration

---

*Guidelines derived from Phase 8 Test Performance Research (08-REPORT.md)*
