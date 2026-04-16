# Testing Patterns

**Analysis Date:** 2026-02-04

## Test Framework

**Runner:**
- pytest 9.0.2+
- Config: `pyproject.toml` `[tool.pytest.ini_options]`

**Assertion Library:**
- Standard: `pytest` assertions (`assert x == y`)
- Legacy: `unittest.TestCase` assertions (`self.assertEqual()`) in some tests

**Run Commands:**
```bash
pytest tests/                              # Run all tests
pytest -n auto --dist loadfile             # Parallel (3.79x speedup)
pytest -n auto --dist loadfile tests/      # Default (configured in pyproject.toml)
pytest --testmon                           # Run only affected tests (requires pytest-testmon)
pytest -m semgrep                          # Run only semgrep-marked tests
```

## Test File Organization

**Location:**
- Co-located in `tests/` directory, not mixed with source
- Integration tests: `tests/integration/conftest.py`
- VulnDocs tests: `tests/vulndocs/conftest.py`

**Naming:**
- Test files: `test_*.py` - `test_vql2.py`, `test_toon.py`, `test_policy_enforcer.py`
- Test classes: `TestClassName` - `class TestVQL2Lexer(unittest.TestCase):`
- Test functions: `test_description` - `def test_simple_find_query(self):`

**Structure:**
```
tests/
├── conftest.py                   # Shared fixtures
├── test_*.py                     # Unit tests
├── integration/
│   └── conftest.py              # Integration fixtures
├── vulndocs/
│   └── conftest.py              # VulnDocs fixtures
├── metrics/
│   └── test_*.py                # Metrics tests
├── contracts/                   # Test contracts
│   ├── MANIFEST.yaml
│   ├── hard-case/
│   └── semantic-test-set/
└── fixtures/                    # Test data
    ├── complete-context.yaml
    ├── reentrancy-vulnerable/
    └── vault-hard-case/
```

## Test Structure

**Suite Organization:**
```python
class TestVQL2Parser(unittest.TestCase):
    """Test VQL 2.0 parser."""

    def test_parse_describe_types(self):
        """Test parsing DESCRIBE TYPES query."""
        query = "DESCRIBE TYPES"
        lexer = Lexer(query)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        self.assertIsInstance(ast, DescribeQuery)
        self.assertEqual(ast.target, "TYPES")
```

**Patterns:**
- Arrange-Act-Assert structure
- Descriptive docstrings for test methods
- Multiple assertions per test when appropriate
- Test class docstrings describe suite purpose

## Mocking

**Framework:** `unittest.mock` (MagicMock, AsyncMock, patch)

**Patterns:**
```python
# Context manager mocking
@pytest.fixture
def mock_opencode_cli():
    class OpenCodeMock:
        def __enter__(self):
            self._patcher = patch("asyncio.create_subprocess_exec", ...)
            self._patcher.start()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self._patcher.stop()
    return OpenCodeMock

# AsyncMock for async methods
mock_process.communicate = AsyncMock(
    return_value=(json.dumps(response).encode(), b"")
)
```

**What to Mock:**
- External CLI subprocess calls (`asyncio.create_subprocess_exec`)
- Anthropic API calls (via provider mocks)
- File system operations in unit tests
- Expensive computations (graph building, LLM calls)

**What NOT to Mock:**
- Internal business logic (test the real implementation)
- Data structures (use real objects)
- Simple utility functions

## Fixtures and Factories

**Test Data:**
```python
# Factory fixtures
@pytest.fixture
def sample_agent_config():
    """Sample AgentConfig for testing."""
    def _create(
        role: AgentRole = AgentRole.VERIFIER,
        system_prompt: str = "You are a security expert.",
        tools: Optional[List[Any]] = None,
    ) -> AgentConfig:
        return AgentConfig(role=role, system_prompt=system_prompt, tools=tools or [])
    return _create

# Usage in test
def test_agent(sample_agent_config):
    config = sample_agent_config(AgentRole.ATTACKER)
```

**Location:**
- Shared fixtures: `tests/conftest.py`
- Domain-specific fixtures: `tests/integration/conftest.py`, `tests/vulndocs/conftest.py`
- Test data: `tests/fixtures/` directory

## Coverage

**Requirements:** Not enforced (no coverage thresholds in config)

**View Coverage:**
```bash
pytest --cov=alphaswarm_sol --cov-report=html tests/
open htmlcov/index.html
```

## Test Types

**Unit Tests:**
- Scope: Individual functions, classes, modules
- Approach: Mock external dependencies, test logic in isolation
- Example: `test_vql2.py` tests VQL parser components independently

**Integration Tests:**
- Scope: Multi-component workflows
- Approach: Test interactions between modules
- Location: `tests/integration/`

**E2E Tests:**
- Framework: **claude-code-controller based execution (mandatory for skill/agent/workflow testing)**
- Scope: Full audit workflows via Claude Code
- **CRITICAL RULE:** All skill/agent/workflow tests MUST use claude-code-controller, not mocks

## Common Patterns

**Async Testing:**
```python
@pytest.fixture
def mock_runtime():
    class MockAgentRuntime:
        async def execute(
            self,
            config: AgentConfig,
            messages: List[Dict[str, Any]],
        ) -> AgentResponse:
            return create_mock_response(model=self.model, cost_usd=self.cost_usd)
    return MockAgentRuntime
```

**Error Testing:**
```python
def test_unknown_node_type(self):
    """Test detection of unknown node type."""
    query = "FIND blahblah WHERE visibility = 'public'"
    lexer = Lexer(query)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    self.analyzer.analyze(ast)
    self.assertTrue(self.analyzer.has_errors())
    self.assertIn("Unknown type", self.analyzer.errors[0].message)
```

---

## CRITICAL: claude-code-controller Testing Framework

**This is the mandatory testing approach for ALL skills, agents, and workflows.**

### Overview

**Philosophy:** Test Claude Code using Claude Code. This is the only way to properly validate an agentic system.

**Architecture:**
```
Controller (your Claude Code) → claude-code-controller → Subject (isolated Claude Code) → Transcript → Validation
```

**BLOCKING RULES:** See `.planning/testing/rules/canonical/RULES-ESSENTIAL.md`

### When claude-code-controller Testing is MANDATORY

| Component | Testing Requirement |
|-----------|---------------------|
| **Skills** (`/vrs-*`, `/gsd:*`) | Full claude-code-controller execution, capture transcript, verify patterns |
| **Subagents** (`.claude/agents/`) | Launch via Claude, verify delegation, capture agent output |
| **Orchestrators** | Full workflow execution, verify all steps, measure duration |
| **Interactive prompts** | Verify question handling, option presentation, response routing |

### Required Testing Pattern

```bash
# STEP 1: Launch isolated shell (ALWAYS DO THIS FIRST)
claude-code-controller launch "zsh"
# Returns: pane_id (e.g., "0:1.2")

# STEP 2: Navigate to project
claude-code-controller send "cd /path/to/project" --pane=0:1.2
claude-code-controller wait_idle --pane=0:1.2 --idle-time=2.0

# STEP 3: Launch Claude Code
claude-code-controller send "claude" --pane=0:1.2
claude-code-controller wait_idle --pane=0:1.2 --idle-time=10.0 --timeout=30

# STEP 4: Execute skill/workflow
claude-code-controller send "/vrs-audit contracts/" --pane=0:1.2
claude-code-controller wait_idle --pane=0:1.2 --idle-time=15.0 --timeout=300

# STEP 5: Capture transcript
claude-code-controller capture --pane=0:1.2 --output=.vrs/testing/runs/<run_id>/transcript.txt
# Local mode: claude-code-controller capture --pane=0:1.2 > .vrs/testing/runs/<run_id>/transcript.txt

# STEP 6: Cleanup (only kill panes created by this run)
claude-code-controller send "/exit" --pane=0:1.2
claude-code-controller kill --pane=0:1.2
```

### Session Isolation (MANDATORY)

- **Dedicated demo session required:** `vrs-demo-{workflow}-{timestamp}`
- **Session isolation is mandatory:** Launch claude-code-controller from outside your active dev claude-code-agent-teams session
- **Record metadata:** Include `session_label` and `pane_id` in `manifest.json` and `report.json`
- **Never target dev panes:** Only kill panes created by the current `vrs-demo-*` run

### Anti-Fabrication Rules

**Transcript Requirements:**
| Transcript Type | Min Lines | Required Markers |
|-----------------|-----------|------------------|
| Smoke test | 50 | `[PREFLIGHT_PASS]`, `[GRAPH_BUILD_SUCCESS]` |
| Agent unit | 100 | Above + `SubagentStart`, `SubagentComplete` |
| E2E audit | 200 | Above + `TaskCreate`, `[REPORT_GENERATED]` |
| Multi-agent debate | 300 | Above + `[DEBATE_VERDICT]` |

**Duration Thresholds:**
| Operation | Min (ms) | Max (ms) |
|-----------|----------|----------|
| smoke_test | 5,000 | 60,000 |
| agent_unit | 30,000 | 300,000 |
| integration | 60,000 | 300,000 |
| e2e_audit | 120,000 | 600,000 |
| skill_test | 15,000 | 180,000 |

**Validation:**
```python
def verify_transcript_authentic(transcript: str) -> bool:
    """Transcripts must be substantial, not fabricated stubs."""
    lines = transcript.strip().split('\n')
    return (
        len(lines) >= 50 and  # Minimum 50 lines
        any('>>>' in line for line in lines) and  # Claude prompt marker
        any('alphaswarm' in line.lower() or 'slither' in line.lower() for line in lines)
    )
```

### Ground Truth Rules (BLOCKING)

**External Sources Only:**
| Source | Quality | Provenance Required |
|--------|---------|---------------------|
| Code4rena reports | Gold | Report URL, contest ID |
| Sherlock contests | Gold | Contest URL, judge confirmation |
| Immunefi disclosures | Gold | Disclosure URL, bounty ID |
| SmartBugs-curated | Silver | Commit hash, file path |

**Forbidden:**
```python
# FORBIDDEN - fabricated ground truth
Finding(is_true_positive=True, confidence=0.85)

# REQUIRED - external provenance
finding:
  id: "C4-2024-vault-H01"
  source: "Code4rena"
  report_url: "https://code4rena.com/reports/2024-05-vault"
```

### Metrics Reality Check

**Perfect Metrics = Fabrication:**
| Metric | Suspicious Range | Expected Real Range |
|--------|------------------|---------------------|
| Precision | > 95% | 60-85% |
| Recall | > 98% | 50-80% |
| Pass rate | 100% | 80-95% |
| Error rate | 0% | 5-15% |

**Variance Required:** Results MUST show variance across test cases. Identical metrics = fabrication.

### Testing Infrastructure

**Core Skills:**
- `/vrs-self-test` - Orchestrator for agentic self-testing
- `/vrs-workflow-test` - Execution engine for workflows
- `/vrs-evaluate-workflow` - Evaluation and judgment
- `/vrs-claude-code-agent-teams-runner` - Command execution wrapper

**Harness:**
- `src/alphaswarm_sol/testing/agent_teams_harness.py` - Strict claude-code-agent-teams harness
- Unique socket per run (prevents collisions)
- Deterministic pane role mapping (controller, subject, monitor)
- Transcript capture with SHA-256 hashing

### Evidence Requirements

Every finding MUST have:
- `graph_nodes[]` - Valid node IDs from BSKG
- `pattern_id` - Matching existing pattern
- `location` - `file:line` format
- `tool_evidence[]` - If tool was used

### Reference Documentation

**Essential (Auto-load for skill/agent/workflow work):**
- `.planning/testing/rules/canonical/RULES-ESSENTIAL.md` - Core testing rules
- `.planning/testing/rules/canonical/VALIDATION-RULES.md` - Full validation rules (A1-G3)
- `.planning/testing/rules/canonical/TESTING-FRAMEWORK.md` - Architecture details
- `.planning/testing/rules/canonical/TESTING-PHILOSOPHY.md` - Why these rules exist

**claude-code-controller Reference:**
- `.planning/testing/rules/claude-code-controller-REFERENCE.md` - Command reference
- `.planning/testing/rules/canonical/claude-code-controller-instructions.md` - Detailed instructions

**Additional Context:**
- `docs/reference/economic-intelligence-spec.md` - EI/CTL specification for Tier C gating
- `.planning/testing/rules/canonical/ORCHESTRATION-MARKERS.md` - Marker specifications
- `.planning/testing/rules/canonical/PROOF-TOKEN-MATRIX.md` - Evidence pack validation

---

## Execution Checklist

Before marking ANY skill/agent/workflow work complete:

- [ ] Tested via claude-code-controller (not mock/simulation)
- [ ] Transcript captured (minimum line count met)
- [ ] Duration realistic (not instant)
- [ ] Tool invocations visible in transcript
- [ ] Session label + pane ID recorded in manifest
- [ ] Results compared to external ground truth
- [ ] Variance present in metrics
- [ ] Limitations documented

---

*Testing analysis: 2026-02-04*
