"""Autonomous Testing Harness for Claude Code.

This module enables fully automated testing without human intervention
by invoking Claude Code programmatically via subprocess.

Key insight from research: Skills (/vrs-*) don't work in headless mode.
Instead, we use prompt-based invocation with --allowedTools and
--output-format json to achieve the same functionality autonomously.

Key components:
- ClaudeCodeRunner: Subprocess wrapper with JSON parsing
- AgentSpawner: Parallel agent orchestration
- ScenarioLoader: Test scenario configuration
- OutputParser: Structured result extraction

Example:
    >>> from alphaswarm_sol.testing.harness import ClaudeCodeRunner
    >>> runner = ClaudeCodeRunner(project_root=Path("."))
    >>> result = runner.run_analysis(
    ...     prompt="Analyze contracts/ for reentrancy",
    ...     allowed_tools=["Bash(uv run alphaswarm*)", "Read", "Glob"]
    ... )
    >>> print(result.structured_output)
"""

from alphaswarm_sol.testing.harness.runner import ClaudeCodeRunner, ClaudeCodeResult
from alphaswarm_sol.testing.harness.output_parser import OutputParser, ParsedFinding
from alphaswarm_sol.testing.harness.agent_spawner import (
    AgentSpawner,
    AgentTask,
    AgentResult,
)
from alphaswarm_sol.testing.harness.scenario_loader import (
    ScenarioLoader,
    TestScenario,
    ContractCase,
)

__all__ = [
    # Runner
    "ClaudeCodeRunner",
    "ClaudeCodeResult",
    # Output Parser
    "OutputParser",
    "ParsedFinding",
    # Agent Spawner
    "AgentSpawner",
    "AgentTask",
    "AgentResult",
    # Scenario Loader
    "ScenarioLoader",
    "TestScenario",
    "ContractCase",
]
