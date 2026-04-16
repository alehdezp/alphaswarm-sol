---
name: vrs-test-quick
description: |
  Fast smoke test skill for development iteration. Runs quick benchmark
  (< 2 min) with critical path validation only.

  Invoke when user wants to:
  - Quick validation: "quick test", "smoke test", "/vrs-test-quick"
  - CI check: "fast check", "pre-commit test"
  - Development iteration: "test my changes", "sanity check"

  This skill runs minimal tests for fast feedback:
  1. Health check (essential tools only)
  2. Critical path tests (reentrancy, access control)
  3. Basic agent component tests
  4. Quick metrics summary

slash_command: vrs:test-quick
context: fork
disable-model-invocation: false

allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(pytest*)
  - Bash(uv run*)
---

# VRS Test Quick - Fast Smoke Tests

You are the **VRS Test Quick** skill, responsible for running fast smoke tests for development iteration. This skill provides quick feedback (< 2 minutes) on critical functionality.

## Philosophy

- **Speed over thoroughness** - Quick feedback is more valuable during development
- **Critical path focus** - Test the most important detection patterns
- **Fail fast** - Stop on first critical failure
- **Minimal scope** - Just enough to catch obvious regressions

## How to Invoke

```bash
/vrs-test-quick
/vrs-test-quick --patterns reentrancy,access-control
/vrs-test-quick --fail-fast
```

---

## What Gets Tested

### Tests Included

1. **Essential Health Check**
   - BSKG builder available
   - Pattern engine loads
   - No import errors

2. **Critical Pattern Detection**
   - Reentrancy-classic (critical)
   - Missing access control (critical)
   - Unchecked return values (high)

3. **Basic Agent Components**
   - Context-merge agent responds
   - Vuln-discovery agent responds

---

## Execution Flow

```
HEALTH -> CRITICAL PATTERNS -> AGENT PING -> METRICS
```

### Phase 1: Essential Health Check
```bash
# Quick health validation
python -c "from alphaswarm_sol.kg.builder import BSKGBuilder; print('Builder OK')"
python -c "from alphaswarm_sol.patterns import PatternEngine; print('Patterns OK')"
```

### Phase 2: Critical Pattern Tests
```bash
# Run critical pattern tests only
pytest tests/test_value_movement_lens.py -v --tb=short
pytest tests/test_authority_lens.py -v --tb=short
```

### Phase 3: Agent Ping
```bash
# Verify agents respond (no full execution)
pytest tests/agents/test_claude_code_runtime.py -v --tb=short
```

### Phase 4: Quick Metrics
```bash
# Generate quick summary
# No detailed breakdown, just pass/fail
```

---

## Usage Examples

### Basic Quick Test
```bash
/vrs-test-quick

# Output:
# Quick Test Run (< 2 min)
# -------------------------
# Health Check: PASS (0.5s)
# Critical Patterns: 4/4 PASS (45s)
# Agent Health: 2/2 PASS (15s)
# -------------------------
# Total: 1m 01s
# Status: PASS
```

### With Specific Patterns
```bash
/vrs-test-quick --patterns reentrancy,oracle

# Only tests specified patterns
```

### Fail Fast Mode
```bash
/vrs-test-quick --fail-fast

# Stops on first failure
# Maximum speed for "is anything broken?"
```

### CI Integration
```bash
# In CI pipeline:
/vrs-test-quick --exit-code

# Returns non-zero exit code on failure
```

---

## Output Format

### Quick Summary
```markdown
# VRS Quick Test

**Duration:** 1m 03s
**Status:** PASS

## Health Check
- Builder: OK
- Patterns: OK
- Agents: OK

## Critical Patterns
| Pattern | Status |
|---------|--------|
| reentrancy-classic | PASS |
| missing-access-control | PASS |
| unchecked-return | PASS |
| weak-randomness | PASS |

## Agent Health
| Agent | Status |
|-------|--------|
| vrs-context-merge | RESPONDING |
| vrs-vuln-discovery | RESPONDING |

## Quick Metrics
- Patterns tested: 4
- All critical: PASS
```

### Failure Output
```markdown
# VRS Quick Test

**Duration:** 0m 32s
**Status:** FAIL

## Failure Details

**Pattern:** reentrancy-classic
**Test:** test_classic_reentrancy_detected
**Error:** Expected finding not detected

```
AssertionError: Expected 'reentrancy-classic' in findings
Actual findings: []
```

## Recommendation
Run `/vrs-test-full` for detailed analysis.
```

---

## When to Use

| Scenario | Use Quick Test? |
|----------|-----------------|
| During development iteration | YES |
| Before committing changes | YES |
| CI pipeline gate | YES |
| Before PR merge | NO - use `/vrs-test-full` |
| Before release | NO - use `/vrs-test-full --mode thorough` |
| Debugging specific issue | NO - use `/vrs-test-component` |

---

## Related Skills

| Skill | Purpose |
|-------|---------|
| `/vrs-test-full` | Complete test orchestration |
| `/vrs-test-component` | Single agent component test |
| `/vrs-health-check` | Full installation validation |

---

## Write Boundaries

This skill writes to:
- `.vrs/testing/quick-results/` - Quick test results only

All other directories are read-only.

---

## Notes

- Quick tests are NOT comprehensive - use `/vrs-test-full` for validation
- 2-minute time limit enforced - tests are killed if exceeded
- Critical patterns only - not all vulnerability types tested
- Agent health, not agent quality - just verifies responsiveness
- This skill CAN be invoked by orchestrators (disable-model-invocation: false)
