---
name: vrs-test-component
description: |
  Single agent component test skill. Tests one agent role in isolation
  with mocked dependencies using deterministic TestModel responses.

  Invoke when user wants to:
  - Test specific agent: "test context-merge agent", "/vrs-test-component context-merge"
  - Validate agent changes: "check vuln-discovery agent"
  - Debug agent behavior: "why is verifier failing"

  This skill tests agent components in isolation:
  1. Load agent definition
  2. Configure TestModel with deterministic responses
  3. Run component tests
  4. Report agent-specific metrics

slash_command: vrs:test-component
context: fork
disable-model-invocation: false

allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(pytest*)
  - Bash(uv run*)
---

# VRS Test Component - Single Agent Testing

You are the **VRS Test Component** skill, responsible for testing individual agent roles in isolation. This skill uses deterministic mock responses to validate agent logic without real LLM calls.

## Philosophy

- **Isolation** - Test one agent at a time, mock all dependencies
- **Deterministic** - Use TestModel for reproducible results
- **Fast** - No real LLM calls, quick feedback
- **Focused** - Validate specific agent behavior, not integration

## How to Invoke

```bash
/vrs-test-component <agent-role>
/vrs-test-component context-merge
/vrs-test-component vuln-discovery
/vrs-test-component verifier --verbose
```

---

## Agent Roles Available

| Agent Role | Description | Model (Production) |
|------------|-------------|-------------------|
| `context-merge` | Merges vulnerability context from multiple sources | Sonnet 4.5 |
| `context-verifier` | Quality gates merged context | Sonnet 4.5 |
| `vuln-discovery` | Discovers vulnerabilities from BSKG patterns | Task router |
| `attacker` | Constructs exploit paths | Opus 4.5 |
| `defender` | Finds guards and mitigations | Sonnet 4.5 |
| `verifier` | Synthesizes verdicts from evidence | Opus 4.5 |
| `orchestrator` | Coordinates audit workflow | Opus 4.5 |
| `sub-coordinator` | Manages parallel agent spawning | Opus 4.5 |

---

## Execution Flow

```
LOAD AGENT -> CONFIGURE MOCK -> RUN TESTS -> REPORT
```

### Phase 1: Load Agent Definition
```bash
# Load agent configuration
# Identifies required inputs, expected outputs, behaviors
```

### Phase 2: Configure TestModel
```python
# TestModel provides deterministic responses
from pydantic_ai import TestModel

test_model = TestModel()
test_model.add_response(
    prompt_pattern="Analyze reentrancy*",
    response={"finding": "reentrancy-classic", "confidence": 0.95}
)
```

### Phase 3: Run Component Tests
```bash
# Run tests for specific agent role
pytest tests/agents/test_{agent_role}_agent.py -v
```

### Phase 4: Report Agent Metrics
```bash
# Agent-specific metrics:
# - Input processing accuracy
# - Output format validation
# - Reasoning quality (when applicable)
```

---

## Usage Examples

### Test Context-Merge Agent
```bash
/vrs-test-component context-merge

# Output:
# Testing: vrs-context-merge
# Model: TestModel (mock)
# -------------------------
#
# Tests:
# - test_merge_basic_context: PASS
# - test_merge_multiple_bundles: PASS
# - test_merge_conflicting_evidence: PASS
# - test_output_format_valid: PASS
# - test_reasoning_included: PASS
#
# Results: 5/5 PASS
# Duration: 2.3s
```

### Test Vuln-Discovery Agent
```bash
/vrs-test-component vuln-discovery

# Tests detection accuracy with known patterns
```

### Test Verifier Agent
```bash
/vrs-test-component verifier --verbose

# Shows detailed reasoning validation
```

### Test with Custom Mock Responses
```bash
/vrs-test-component attacker --mock-file mocks/attacker-responses.yaml

# Uses custom mock responses for specific scenarios
```

---

## TestModel Usage

### Basic Mock Setup
```python
from pydantic_ai import TestModel

@pytest.fixture
def mock_context_merge():
    """Deterministic context-merge agent for testing."""
    model = TestModel()

    # Pre-program responses
    model.add_response(
        prompt_pattern="Merge context for reentrancy*",
        response={
            "merged_context": "CEI violation detected...",
            "confidence": 0.9,
            "evidence_refs": ["Vault.sol:L42"]
        }
    )

    return model
```

### Testing Agent Logic
```python
def test_context_merge_basic(mock_context_merge):
    """Test context merge with deterministic response."""
    agent = ContextMergeAgent(model=mock_context_merge)

    result = agent.merge(
        vuln_class="reentrancy",
        bundles=[
            {"source": "pattern", "evidence": "..."},
            {"source": "vulndoc", "evidence": "..."}
        ]
    )

    # Validate agent processed input correctly
    assert result.status == "complete"
    assert "CEI violation" in result.merged_context
    assert len(result.evidence_refs) > 0
```

### No Real LLM Calls
```python
# Ensure tests don't make real API calls
import os
os.environ["ALLOW_MODEL_REQUESTS"] = "false"

# TestModel raises error if real call attempted
```

---

## Output Format

### Component Test Report
```markdown
# Component Test: vrs-context-merge

**Agent:** vrs-context-merge
**Model Used:** TestModel (deterministic)
**Duration:** 2.3s

## Test Results

| Test | Status | Duration |
|------|--------|----------|
| test_merge_basic_context | PASS | 0.4s |
| test_merge_multiple_bundles | PASS | 0.6s |
| test_merge_conflicting_evidence | PASS | 0.5s |
| test_output_format_valid | PASS | 0.3s |
| test_reasoning_included | PASS | 0.5s |

## Agent Metrics

| Metric | Value |
|--------|-------|
| Input Processing | Valid |
| Output Format | Valid |
| Reasoning Quality | Included |
| Evidence Linking | Present |

## Summary

**Status:** PASS (5/5 tests)
**Coverage:** 92% of agent module
```

### Failure Report
```markdown
# Component Test: vrs-verifier

**Agent:** vrs-verifier
**Status:** FAIL

## Failure Details

**Test:** test_verifier_synthesizes_verdict
**Error:** Invalid verdict format

```
AssertionError: Expected verdict.confidence to be float
Got: verdict.confidence = "high" (str)
```

## Fix Suggestion

Update verifier output schema to use float confidence:
```python
verdict.confidence: float  # 0.0 to 1.0
# NOT: verdict.confidence: str  # "high", "medium", "low"
```
```

---

## Agent Test Files

| Agent Role | Test File |
|------------|-----------|
| context-merge | `tests/agents/test_context_merge_agent.py` |
| context-verifier | `tests/agents/test_context_verifier_agent.py` |
| vuln-discovery | `tests/agents/test_vuln_discovery_agent.py` |
| attacker | `tests/agents/test_attacker_agent.py` |
| defender | `tests/agents/test_defender_agent.py` |
| verifier | `tests/agents/test_verifier_agent.py` |
| orchestrator | `tests/agents/test_orchestrator_agent.py` |
| sub-coordinator | `tests/agents/test_sub_coordinator_agent.py` |

---

## Related Skills

| Skill | Purpose |
|-------|---------|
| `/vrs-test-full` | Complete test orchestration |
| `/vrs-test-quick` | Fast smoke tests |
| `/vrs-verify` | Multi-agent verification (integration) |

---

## When to Use

| Scenario | Use Component Test? |
|----------|---------------------|
| Debugging specific agent | YES |
| After changing agent logic | YES |
| Validating output format | YES |
| Testing agent interactions | NO - use integration tests |
| Full pipeline validation | NO - use `/vrs-test-full` |

---

## Write Boundaries

This skill is restricted to writing in:
- `.vrs/testing/component-results/` - Component test results

All other directories are read-only.

---

## Notes

- Component tests use TestModel, never real LLM calls
- Tests are fast (< 5 seconds per agent)
- Mock responses should cover typical scenarios
- Edge cases need explicit mock programming
- This skill CAN be invoked by orchestrators (disable-model-invocation: false)
