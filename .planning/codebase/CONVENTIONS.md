# Coding Conventions

**Analysis Date:** 2026-02-04

## Naming Patterns

**Files:**
- Python modules: `snake_case.py` - `builder.py`, `client.py`, `validator.py`
- Test files: `test_*.py` - `test_vql2.py`, `test_toon.py`, `test_policy_enforcer.py`
- CLI commands: `snake_case.py` in `src/alphaswarm_sol/cli/` - `vulndocs.py`, `tools.py`, `beads.py`
- Test contracts: `PascalCase.sol` - `ReentrancyClassic.sol`, `SemanticPrivilegedStateTest.sol`

**Functions:**
- Functions: `snake_case` - `build_graph()`, `parse_intent()`, `extract_inputs()`
- Private methods: `_leading_underscore` - `_init_providers()`, `_check_properties()`, `_create_base_result()`
- Async functions: `async def snake_case()` - `async def execute()`, `async def spawn_agent()`

**Variables:**
- Local variables: `snake_case` - `project_root`, `graph_nodes`, `pattern_id`
- Constants: `UPPER_SNAKE_CASE` - `DEFAULT_SESSION_NAME`, `PROVIDER_CLASSES`, `REQUIRED_MARKERS`
- Private attributes: `_leading_underscore` - `self._providers`, `self._cache`, `self._next_response`

**Types:**
- Classes: `PascalCase` - `VKGBuilder`, `LLMClient`, `claude-code-agent-teamsHarness`, `ValidationStatus`
- Enums: `PascalCase` class, `UPPER_SNAKE_CASE` members - `class Provider(Enum)`, `Provider.ANTHROPIC`
- Type aliases: `PascalCase` - `KnowledgeGraph`, `AgentResponse`, `FindQuery`

## Code Style

**Formatting:**
- Tool used: None detected (no ruff.toml, .black, .flake8)
- Indentation: 4 spaces
- Line length: Generally < 100 characters, some longer lines in docstrings
- String quotes: Double quotes preferred for docstrings, mixed single/double in code
- Trailing commas: Used in multi-line data structures

**Linting:**
- Tool used: Not configured (no linting config files found)
- Type hints: Extensive use of type hints throughout
- Docstrings: Google-style docstrings with Args/Returns/Yields sections

## Import Organization

**Order:**
1. Future imports: `from __future__ import annotations`
2. Standard library: `import json`, `from pathlib import Path`, `from typing import Optional`
3. Third-party: `import structlog`, `import typer`, `from anthropic import Anthropic`
4. Local relative: `from alphaswarm_sol.kg.schema import KnowledgeGraph`
5. Conditional imports: `if TYPE_CHECKING:` for circular dependency prevention

**Path Aliases:**
- No path aliases detected
- Uses absolute imports from package root: `from alphaswarm_sol.cli.batch import batch_app`

## Error Handling

**Patterns:**
- Exception handling with specific exceptions: `try/except RuntimeError/ValueError`
- Graceful degradation for optional dependencies:
```python
try:
    import slither
    from slither import Slither
except Exception as exc:
    Slither = None
    _SLITHER_IMPORT_ERROR = exc
```
- Error propagation with context: `raise typer.Exit(code=1) from exc`
- Runtime checks before usage: `if Slither is None: raise RuntimeError(...)`

## Logging

**Framework:** `structlog`

**Patterns:**
- Logger instantiation: `self.logger = structlog.get_logger()` or `logger = structlog.get_logger(__name__)`
- Structured logging: `logger.error("command_failed", error=str(exc))`
- Configuration: `configure_logging(log_level or settings.log_level)` in CLI entry point

## Comments

**When to Comment:**
- Deprecation notices: `# Deprecated since version X.X`
- Complex logic explanations: `# Verify key tokens`, `# Track session usage`
- TODOs/FIXMEs: `# TODO: implement feature X`
- Section markers: `# =============================================================================`
- Pragma markers: `# pragma: no cover - import error handled at runtime`

**JSDoc/TSDoc:**
- Not applicable (Python codebase)
- Uses Google-style Python docstrings with rich detail

## Function Design

**Size:** Functions range from 5-50 lines, with occasional longer functions for complex logic

**Parameters:**
- Use of `*` for keyword-only args: `def __init__(self, project_root: Path, *, exclude_dependencies: bool = True)`
- Extensive type hints: `def build(self, target: Path) -> KnowledgeGraph:`
- Optional parameters with defaults: `config: Optional[LLMConfig] = None`

**Return Values:**
- Explicit return types in function signatures
- Use of dataclasses for structured returns: `@dataclass class CaptureResult:`
- Tuple unpacking for multiple returns: `return (bool, list[str])`

## Module Design

**Exports:**
- Explicit `__all__` in `__init__.py` files
- Clean namespace management via `__init__.py` re-exports
```python
from alphaswarm_sol.validation.benchmarks import (
    ExploitType,
    ExploitBenchmark,
)
```

**Barrel Files:**
- Package initialization files (`__init__.py`) act as barrel files
- Re-export key classes/functions from submodules for clean imports

## Async/Await Patterns

**Async functions:**
- CLI commands use `asyncio.run()` wrapper for sync interface
- LLM providers implement async methods: `async def execute()`
- Mock fixtures use `AsyncMock` for async testing: `mock_process.communicate = AsyncMock(...)`

**Concurrency:**
- Uses `asyncio.create_subprocess_exec` for CLI tool integration
- Agent runtime coordination via async methods

## Testing Conventions

**Test structure:**
- Uses `unittest.TestCase` classes: `class TestVQL2Lexer(unittest.TestCase):`
- Test methods: `def test_simple_find_query(self):` with descriptive names
- Setup methods: `def setUp(self):` for test fixtures

**Assertions:**
- Standard unittest assertions: `self.assertEqual()`, `self.assertTrue()`, `self.assertIsInstance()`
- Custom error messages in assertions

**Fixtures:**
- pytest fixtures in `conftest.py` with docstrings
- Factory fixtures that return callables: `@pytest.fixture def sample_agent_config():`
- Context manager fixtures: `with mock_opencode_cli() as mock:`

## Dataclasses

**Usage:**
- Extensive use of `@dataclass` for data structures
- Field defaults: `@dataclass class HarnessConfig: session_name: str = DEFAULT_SESSION_NAME`
- Field factories: `provider_breakdown: Dict[str, Dict[str, Any]] = field(default_factory=dict)`
- Conversion methods: `def to_dict(self) -> Dict[str, Any]:`

## Enums

**Pattern:**
- Inherit from `str, Enum` or just `Enum`
- Members in UPPER_SNAKE_CASE: `ANTHROPIC = "anthropic"`
- Use `.value` for string representation

## Type Hints

**Coverage:**
- Extensive type hints on all function signatures
- Use of `Optional[T]`, `List[T]`, `Dict[K, V]` from `typing`
- Use of `|` union syntax: `str | None` (Python 3.10+)
- `TYPE_CHECKING` for import-time-only types: `if TYPE_CHECKING: from alphaswarm_sol.kg.schema import KnowledgeGraph`

**Patterns:**
- Return type annotations on all public methods
- Parameter type hints including defaults: `log_level: str | None = None`
- Generic types with concrete parameters: `Dict[Provider, Type[LLMProvider]]`

---

*Convention analysis: 2026-02-04*
