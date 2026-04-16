# Testing Framework

## Purpose

Define how AlphaSwarm.sol validates its features, from unit tests to end-to-end pipeline verification.

---

## Testing Approaches

### pytest (Unit and Integration Tests)

pytest is the primary testing tool for Python internals and integration tests:

- **Unit tests:** Builder property computation, schema validation, data transforms, graph structure operations
- **Integration tests:** PatternEngine API, Router/Resume, VulnDocs validation on real entries
- **Detection regression tests:** Contract-to-finding tests on real Solidity contracts

```bash
# Run all tests (parallel, 3.79x faster)
uv run pytest tests/ -n auto --dist loadfile

# Run specific test category
uv run pytest tests/vulndocs/ -v
uv run pytest tests/test_execution_loop.py -v
```

### Workflow Testing (Agent Teams + ClaudeCodeRunner)

For testing skills and workflows, use Agent Teams (native Claude Code) and `ClaudeCodeRunner` (sync `claude --print` wrapper) for headless programmatic runs. See `docs/workflows/diagrams/05-testing-architecture.md` for the testing architecture.

### E2E Pipeline Validation

End-to-end validation is a target for Phase 3.2. Current status: pipeline is partially working and still being proven end-to-end.

Planned full pipeline on real contracts:

```
build-kg contract.sol -> query patterns -> create beads -> verdict
```

Target benchmarks: DVDeFi challenges, SmartBugs subset.

---

## Validation Rules

1. **Real execution** -- Tests must run on real Solidity contracts, not simulated inputs
2. **External ground truth** -- Validation claims must reference external sources (Code4rena, Sherlock, DVDeFi)
3. **Anti-fabrication** -- Perfect metrics (100%/100%) trigger investigation; real systems have edge cases
4. **Evidence-linked** -- Findings must trace to graph node IDs and code locations

---

## Test Categories

| Category | Tool | Examples |
|----------|------|---------|
| Unit tests | pytest | Builder functions, schema validation, data transforms |
| Integration tests | pytest | PatternEngine E2E, Router/Resume state advancement |
| Detection regression | pytest | Contract-to-finding on real Solidity contracts |
| Workflow validation | Agent Teams / controller | Skill execution in isolated Claude Code sessions |
| E2E pipeline | controller / manual | Full audit on DVDeFi targets |

---

## Key Metrics (Honest)

| Metric | Current | Notes |
|--------|---------|-------|
| DVDeFi Detection | Unknown | Benchmarks not yet run (Phase 5 target) |
| Test Count | 11,282 | pytest unit tests |
| Test Files | 245 | pytest unit tests |
| Rescued Pattern TP | 90% | 9/10 on real contracts (Phase 2.1) |

---

*Updated February 2026*
