"""Tests for autonomous testing harness.

Note: These tests verify the harness infrastructure itself,
not the actual Claude Code analysis (which would require API calls).

Tests validate:
- ClaudeCodeRunner command building and result parsing
- AgentSpawner parallel execution with mocked runner
- ScenarioLoader YAML loading and validation
- OutputParser accuracy calculations
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from alphaswarm_sol.testing.harness import (
    AgentSpawner,
    ClaudeCodeRunner,
    OutputParser,
    ScenarioLoader,
    TestScenario,
)
from alphaswarm_sol.testing.harness.agent_spawner import AgentResult, AgentTask
from alphaswarm_sol.testing.harness.output_parser import ParsedFinding
from alphaswarm_sol.testing.harness.runner import ClaudeCodeResult
from alphaswarm_sol.testing.harness.scenario_loader import ContractCase


class TestClaudeCodeRunner:
    """Test ClaudeCodeRunner command building and parsing."""

    def test_build_command_basic(self, tmp_path: Path) -> None:
        """Test basic command building."""
        runner = ClaudeCodeRunner(project_root=tmp_path)
        cmd = runner._build_command(
            prompt="Test prompt",
            allowed_tools=None,
            system_prompt=None,
            append_system_prompt=None,
            json_schema=None,
            resume_session=None,
            model=None,
            max_turns=None,
        )

        assert cmd[0] == "claude"
        assert cmd[1] == "-p"
        assert cmd[2] == "Test prompt"
        assert "--output-format" in cmd
        assert "json" in cmd

    def test_build_command_with_tools(self, tmp_path: Path) -> None:
        """Test command with allowed tools."""
        runner = ClaudeCodeRunner(project_root=tmp_path)
        cmd = runner._build_command(
            prompt="Test",
            allowed_tools=["Bash(uv run*)", "Read", "Glob"],
            system_prompt=None,
            append_system_prompt=None,
            json_schema=None,
            resume_session=None,
            model=None,
            max_turns=None,
        )

        assert "--allowedTools" in cmd
        tools_idx = cmd.index("--allowedTools")
        assert "Bash(uv run*),Read,Glob" == cmd[tools_idx + 1]

    def test_build_command_with_schema(self, tmp_path: Path) -> None:
        """Test command with JSON schema."""
        runner = ClaudeCodeRunner(project_root=tmp_path)
        schema = {"type": "object", "properties": {"test": {"type": "string"}}}

        cmd = runner._build_command(
            prompt="Test",
            allowed_tools=None,
            system_prompt=None,
            append_system_prompt=None,
            json_schema=schema,
            resume_session=None,
            model=None,
            max_turns=None,
        )

        assert "--json-schema" in cmd
        schema_idx = cmd.index("--json-schema")
        assert json.loads(cmd[schema_idx + 1]) == schema

    def test_build_command_with_model(self, tmp_path: Path) -> None:
        """Test command with model selection."""
        runner = ClaudeCodeRunner(project_root=tmp_path)
        cmd = runner._build_command(
            prompt="Test",
            allowed_tools=None,
            system_prompt=None,
            append_system_prompt=None,
            json_schema=None,
            resume_session=None,
            model="claude-opus-4",
            max_turns=None,
        )

        assert "--model" in cmd
        model_idx = cmd.index("--model")
        assert cmd[model_idx + 1] == "claude-opus-4"

    def test_build_command_with_resume(self, tmp_path: Path) -> None:
        """Test command with session resume."""
        runner = ClaudeCodeRunner(project_root=tmp_path)
        cmd = runner._build_command(
            prompt="Continue analysis",
            allowed_tools=None,
            system_prompt=None,
            append_system_prompt=None,
            json_schema=None,
            resume_session="session-abc123",
            model=None,
            max_turns=None,
        )

        assert "--resume" in cmd
        resume_idx = cmd.index("--resume")
        assert cmd[resume_idx + 1] == "session-abc123"

    def test_build_command_with_max_turns(self, tmp_path: Path) -> None:
        """Test command with max turns."""
        runner = ClaudeCodeRunner(project_root=tmp_path)
        cmd = runner._build_command(
            prompt="Test",
            allowed_tools=None,
            system_prompt=None,
            append_system_prompt=None,
            json_schema=None,
            resume_session=None,
            model=None,
            max_turns=5,
        )

        assert "--max-turns" in cmd
        turns_idx = cmd.index("--max-turns")
        assert cmd[turns_idx + 1] == "5"

    def test_build_command_with_system_prompts(self, tmp_path: Path) -> None:
        """Test command with system prompt options."""
        runner = ClaudeCodeRunner(project_root=tmp_path)
        cmd = runner._build_command(
            prompt="Test",
            allowed_tools=None,
            system_prompt="Custom system",
            append_system_prompt=None,
            json_schema=None,
            resume_session=None,
            model=None,
            max_turns=None,
        )

        assert "--system-prompt" in cmd

        cmd2 = runner._build_command(
            prompt="Test",
            allowed_tools=None,
            system_prompt=None,
            append_system_prompt="Additional context",
            json_schema=None,
            resume_session=None,
            model=None,
            max_turns=None,
        )

        assert "--append-system-prompt" in cmd2

    def test_parse_result_json(self, tmp_path: Path) -> None:
        """Test parsing JSON result."""
        runner = ClaudeCodeRunner(project_root=tmp_path)

        mock_result = Mock()
        mock_result.stdout = json.dumps(
            {
                "result": "Analysis complete",
                "session_id": "abc123",
                "structured_output": {"findings": []},
            }
        )
        mock_result.stderr = ""
        mock_result.returncode = 0

        parsed = runner._parse_result(mock_result)

        assert parsed.result_text == "Analysis complete"
        assert parsed.session_id == "abc123"
        assert parsed.structured_output == {"findings": []}
        assert parsed.return_code == 0

    def test_parse_result_with_cost(self, tmp_path: Path) -> None:
        """Test parsing result with cost information."""
        runner = ClaudeCodeRunner(project_root=tmp_path)

        mock_result = Mock()
        mock_result.stdout = json.dumps(
            {
                "result": "Done",
                "cost_usd": 0.05,
            }
        )
        mock_result.stderr = ""
        mock_result.returncode = 0

        parsed = runner._parse_result(mock_result)
        assert parsed.cost_usd == 0.05

    def test_parse_result_non_json(self, tmp_path: Path) -> None:
        """Test parsing non-JSON result."""
        runner = ClaudeCodeRunner(project_root=tmp_path)

        mock_result = Mock()
        mock_result.stdout = "Plain text output"
        mock_result.stderr = ""
        mock_result.returncode = 0

        parsed = runner._parse_result(mock_result)

        assert parsed.result_text == "Plain text output"
        assert parsed.parsed_json is None

    def test_claude_code_result_properties(self) -> None:
        """Test ClaudeCodeResult property methods."""
        result = ClaudeCodeResult(
            raw_output="{}",
            parsed_json={},
            result_text="Done",
            session_id="123",
            structured_output={"findings": []},
            return_code=0,
            stderr="",
            cost_usd=0.01,
            duration_ms=1000,
        )

        assert result.success is True
        assert result.has_structured_output is True

        result_failed = ClaudeCodeResult(
            raw_output="",
            parsed_json=None,
            result_text="",
            session_id=None,
            structured_output=None,
            return_code=1,
            stderr="Error",
        )

        assert result_failed.success is False
        assert result_failed.has_structured_output is False


class TestOutputParser:
    """Test output parsing and accuracy calculation."""

    def test_parse_findings(self) -> None:
        """Test parsing findings from structured output."""
        output = {
            "findings": [
                {
                    "pattern": "reentrancy",
                    "severity": "critical",
                    "location": "withdraw:45",
                    "confidence": 0.9,
                },
                {
                    "pattern": "unchecked-return",
                    "severity": "medium",
                    "location": "transfer:23",
                    "confidence": 0.7,
                },
            ]
        }

        findings = OutputParser.parse_findings(output)

        assert len(findings) == 2
        assert findings[0].pattern == "reentrancy"
        assert findings[0].severity == "critical"
        assert findings[1].confidence == 0.7

    def test_parse_findings_empty(self) -> None:
        """Test parsing empty or None output."""
        assert OutputParser.parse_findings(None) == []
        assert OutputParser.parse_findings({}) == []
        assert OutputParser.parse_findings({"findings": []}) == []

    def test_calculate_accuracy_perfect(self) -> None:
        """Test accuracy with perfect detection."""
        findings = [
            ParsedFinding(
                pattern="reentrancy",
                severity="critical",
                location="withdraw:45",
                confidence=0.9,
            )
        ]
        ground_truth = [
            {"pattern": "reentrancy", "severity": "critical", "location": "withdraw:45"}
        ]

        accuracy = OutputParser.calculate_accuracy(findings, ground_truth)

        assert accuracy["precision"] == 1.0
        assert accuracy["recall"] == 1.0
        assert accuracy["f1_score"] == 1.0
        assert accuracy["true_positives"] == 1
        assert accuracy["false_positives"] == 0
        assert accuracy["false_negatives"] == 0

    def test_calculate_accuracy_with_fp_fn(self) -> None:
        """Test accuracy with false positives and negatives."""
        findings = [
            ParsedFinding(
                pattern="reentrancy",
                severity="critical",
                location="withdraw:45",
                confidence=0.9,
            ),
            ParsedFinding(
                pattern="overflow",
                severity="high",
                location="add:10",
                confidence=0.6,
            ),  # FP
        ]
        ground_truth = [
            {"pattern": "reentrancy", "severity": "critical", "location": "withdraw:45"},
            {"pattern": "access-control", "severity": "high", "location": "admin:30"},  # FN
        ]

        accuracy = OutputParser.calculate_accuracy(findings, ground_truth)

        assert accuracy["true_positives"] == 1
        assert accuracy["false_positives"] == 1
        assert accuracy["false_negatives"] == 1
        assert accuracy["precision"] == 0.5
        assert accuracy["recall"] == 0.5

    def test_calculate_accuracy_empty(self) -> None:
        """Test accuracy with empty inputs."""
        # No findings, no ground truth
        accuracy = OutputParser.calculate_accuracy([], [])
        assert accuracy["precision"] == 0.0
        assert accuracy["recall"] == 0.0

        # Findings but no ground truth (all FP)
        findings = [
            ParsedFinding(
                pattern="test", severity="low", location="test:1", confidence=0.5
            )
        ]
        accuracy = OutputParser.calculate_accuracy(findings, [])
        assert accuracy["precision"] == 0.0
        assert accuracy["false_positives"] == 1

    def test_calculate_severity_recall(self) -> None:
        """Test severity-based recall calculation."""
        findings = [
            ParsedFinding(
                pattern="reentrancy",
                severity="critical",
                location="withdraw",
                confidence=0.9,
            ),
            ParsedFinding(
                pattern="overflow",
                severity="high",
                location="add",
                confidence=0.8,
            ),
        ]
        ground_truth = [
            {"pattern": "reentrancy", "severity": "critical", "location": "withdraw"},
            {"pattern": "another", "severity": "critical", "location": "other"},  # Missed
            {"pattern": "overflow", "severity": "high", "location": "add"},
        ]

        recall = OutputParser.calculate_severity_recall(findings, ground_truth)

        assert recall["critical"] == 0.5  # 1/2 critical found
        assert recall["high"] == 1.0  # 1/1 high found
        assert recall["medium"] == 1.0  # No medium in GT

    def test_extract_detection_decision(self) -> None:
        """Test extraction of vulnerability detection decision."""
        assert OutputParser.extract_detection_decision({"has_vulnerability": True}) is True
        assert OutputParser.extract_detection_decision({"has_vulnerability": False}) is False
        assert OutputParser.extract_detection_decision(None) is None

        # Fallback to findings check
        output_with_critical = {
            "findings": [{"severity": "critical", "pattern": "test"}]
        }
        assert OutputParser.extract_detection_decision(output_with_critical) is True

    def test_group_findings_by_pattern(self) -> None:
        """Test grouping findings by pattern."""
        findings = [
            ParsedFinding("reentrancy", "critical", "loc1", 0.9),
            ParsedFinding("reentrancy", "critical", "loc2", 0.8),
            ParsedFinding("overflow", "high", "loc3", 0.7),
        ]

        grouped = OutputParser.group_findings_by_pattern(findings)

        assert len(grouped["reentrancy"]) == 2
        assert len(grouped["overflow"]) == 1

    def test_group_findings_by_severity(self) -> None:
        """Test grouping findings by severity."""
        findings = [
            ParsedFinding("test1", "critical", "loc1", 0.9),
            ParsedFinding("test2", "critical", "loc2", 0.8),
            ParsedFinding("test3", "high", "loc3", 0.7),
        ]

        grouped = OutputParser.group_findings_by_severity(findings)

        assert len(grouped["critical"]) == 2
        assert len(grouped["high"]) == 1

    def test_filter_by_confidence(self) -> None:
        """Test filtering findings by confidence threshold."""
        findings = [
            ParsedFinding("test1", "high", "loc1", 0.9),
            ParsedFinding("test2", "high", "loc2", 0.4),
            ParsedFinding("test3", "high", "loc3", 0.6),
        ]

        filtered = OutputParser.filter_by_confidence(findings, min_confidence=0.5)

        assert len(filtered) == 2
        assert all(f.confidence >= 0.5 for f in filtered)

    def test_format_findings_summary(self) -> None:
        """Test formatting findings as summary."""
        findings = [
            ParsedFinding("reentrancy", "critical", "withdraw:45", 0.9),
            ParsedFinding("overflow", "high", "add:10", 0.7),
        ]

        summary = OutputParser.format_findings_summary(findings)

        assert "2 potential issue(s)" in summary
        assert "[CRITICAL]" in summary
        assert "[HIGH]" in summary
        assert "reentrancy" in summary

    def test_format_findings_summary_empty(self) -> None:
        """Test formatting empty findings."""
        summary = OutputParser.format_findings_summary([])
        assert "No findings detected" in summary


class TestScenarioLoader:
    """Test scenario loading from YAML."""

    def test_load_scenario(self, tmp_path: Path) -> None:
        """Test loading a single scenario."""
        scenarios_dir = tmp_path / "scenarios" / "reentrancy"
        scenarios_dir.mkdir(parents=True)

        config = {
            "name": "Classic Reentrancy",
            "category": "reentrancy",
            "description": "Test reentrancy detection",
            "contracts": [
                {
                    "path": "corpus/reentrancy/vuln-001.sol",
                    "has_vulnerability": True,
                    "expected_pattern": "reentrancy-classic",
                    "ground_truth": [
                        {
                            "pattern": "reentrancy-classic",
                            "severity": "critical",
                            "location": "withdraw",
                        }
                    ],
                }
            ],
            "prompt_template": "Analyze {contract_path} for reentrancy",
            "allowed_tools": ["Bash(uv run*)", "Read"],
            "json_schema": {"type": "object"},
            "timeout_seconds": 120,
        }

        with open(scenarios_dir / "config.yaml", "w") as f:
            yaml.dump(config, f)

        loader = ScenarioLoader(tmp_path / "scenarios")
        scenario = loader.load_scenario(scenarios_dir / "config.yaml")

        assert scenario.name == "Classic Reentrancy"
        assert scenario.category == "reentrancy"
        assert len(scenario.contracts) == 1
        assert scenario.contracts[0].has_vulnerability is True

    def test_load_all_scenarios(self, tmp_path: Path) -> None:
        """Test loading multiple scenarios."""
        scenarios_dir = tmp_path / "scenarios"

        # Create two scenarios
        for category in ["reentrancy", "access_control"]:
            cat_dir = scenarios_dir / category
            cat_dir.mkdir(parents=True)

            config = {
                "name": f"{category} Test",
                "category": category,
                "description": f"Test {category}",
                "contracts": [],
                "prompt_template": "Analyze {contract_path}",
                "json_schema": {"type": "object"},
            }

            with open(cat_dir / "config.yaml", "w") as f:
                yaml.dump(config, f)

        loader = ScenarioLoader(scenarios_dir)
        scenarios = loader.load_all()

        assert len(scenarios) == 2
        assert "reentrancy Test" in scenarios
        assert "access_control Test" in scenarios

    def test_load_by_category(self, tmp_path: Path) -> None:
        """Test loading scenarios by category."""
        scenarios_dir = tmp_path / "scenarios"

        # Create scenarios with different categories
        for name, category in [
            ("Test1", "reentrancy"),
            ("Test2", "reentrancy"),
            ("Test3", "oracle"),
        ]:
            cat_dir = scenarios_dir / name.lower()
            cat_dir.mkdir(parents=True)

            config = {
                "name": name,
                "category": category,
                "contracts": [],
                "prompt_template": "Test",
                "json_schema": {},
            }

            with open(cat_dir / "config.yaml", "w") as f:
                yaml.dump(config, f)

        loader = ScenarioLoader(scenarios_dir)
        reentrancy_scenarios = loader.load_by_category("reentrancy")

        assert len(reentrancy_scenarios) == 2
        assert all(s.category == "reentrancy" for s in reentrancy_scenarios)

    def test_scenario_get_prompt(self) -> None:
        """Test scenario prompt generation."""
        scenario = TestScenario(
            name="Test",
            category="test",
            description="Test scenario",
            contracts=[],
            prompt_template="Analyze {contract_path} for vulnerabilities",
            allowed_tools=["Read"],
            json_schema={},
        )

        prompt = scenario.get_prompt("contracts/Vault.sol")
        assert "contracts/Vault.sol" in prompt

    def test_scenario_get_vulnerable_contracts(self) -> None:
        """Test filtering vulnerable contracts."""
        scenario = TestScenario(
            name="Test",
            category="test",
            description="",
            contracts=[
                ContractCase(path="vuln.sol", has_vulnerability=True),
                ContractCase(path="safe.sol", has_vulnerability=False),
                ContractCase(path="vuln2.sol", has_vulnerability=True),
            ],
            prompt_template="",
            allowed_tools=[],
            json_schema={},
        )

        vuln_contracts = scenario.get_vulnerable_contracts()
        safe_contracts = scenario.get_safe_contracts()

        assert len(vuln_contracts) == 2
        assert len(safe_contracts) == 1

    def test_list_categories(self, tmp_path: Path) -> None:
        """Test listing available categories."""
        scenarios_dir = tmp_path / "scenarios"

        for name, category in [
            ("s1", "reentrancy"),
            ("s2", "oracle"),
            ("s3", "access"),
        ]:
            cat_dir = scenarios_dir / name
            cat_dir.mkdir(parents=True)

            config = {
                "name": name,
                "category": category,
                "contracts": [],
                "prompt_template": "",
                "json_schema": {},
            }

            with open(cat_dir / "config.yaml", "w") as f:
                yaml.dump(config, f)

        loader = ScenarioLoader(scenarios_dir)
        categories = loader.list_categories()

        assert "reentrancy" in categories
        assert "oracle" in categories
        assert "access" in categories

    def test_create_scenario(self, tmp_path: Path) -> None:
        """Test creating a new scenario."""
        scenarios_dir = tmp_path / "scenarios"
        scenarios_dir.mkdir()

        loader = ScenarioLoader(scenarios_dir)
        config_path = loader.create_scenario(
            name="New Scenario",
            category="oracle",
            description="Test oracle manipulation",
            prompt_template="Analyze {contract_path}",
        )

        assert config_path.exists()

        # Verify it can be loaded
        scenario = loader.load_scenario(config_path)
        assert scenario.name == "New Scenario"
        assert scenario.category == "oracle"


class TestAgentSpawner:
    """Test parallel agent spawning."""

    def test_run_parallel_mock(self, tmp_path: Path) -> None:
        """Test parallel execution with mocked runner."""
        runner = Mock(spec=ClaudeCodeRunner)
        runner.run_analysis.return_value = ClaudeCodeResult(
            raw_output="{}",
            parsed_json={},
            result_text="Done",
            session_id="123",
            structured_output=None,
            return_code=0,
            stderr="",
        )

        spawner = AgentSpawner(runner, max_workers=2)

        tasks = [
            AgentTask(task_id="task1", prompt="Test 1", allowed_tools=[]),
            AgentTask(task_id="task2", prompt="Test 2", allowed_tools=[]),
        ]

        results = spawner.run_parallel(tasks)

        assert len(results) == 2
        assert results[0].task_id == "task1"
        assert results[1].task_id == "task2"
        assert runner.run_analysis.call_count == 2

    def test_run_parallel_preserves_order(self, tmp_path: Path) -> None:
        """Test that results are returned in original task order."""
        runner = Mock(spec=ClaudeCodeRunner)

        def slow_then_fast(prompt, **kwargs):
            import time

            # Simulate task2 finishing before task1
            if "task1" in prompt:
                time.sleep(0.1)
            return ClaudeCodeResult(
                raw_output="{}",
                parsed_json={},
                result_text=prompt,
                session_id=None,
                structured_output=None,
                return_code=0,
                stderr="",
            )

        runner.run_analysis.side_effect = slow_then_fast

        spawner = AgentSpawner(runner, max_workers=2)

        tasks = [
            AgentTask(task_id="task1", prompt="task1 prompt", allowed_tools=[]),
            AgentTask(task_id="task2", prompt="task2 prompt", allowed_tools=[]),
        ]

        results = spawner.run_parallel(tasks)

        # Results should be in original order regardless of completion order
        assert results[0].task_id == "task1"
        assert results[1].task_id == "task2"

    def test_run_parallel_handles_errors(self, tmp_path: Path) -> None:
        """Test that errors are captured in results."""
        runner = Mock(spec=ClaudeCodeRunner)

        def fail_on_task2(prompt, **kwargs):
            if "task2" in prompt:
                raise RuntimeError("Task 2 failed")
            return ClaudeCodeResult(
                raw_output="{}",
                parsed_json={},
                result_text="OK",
                session_id=None,
                structured_output=None,
                return_code=0,
                stderr="",
            )

        runner.run_analysis.side_effect = fail_on_task2

        spawner = AgentSpawner(runner, max_workers=2)

        tasks = [
            AgentTask(task_id="task1", prompt="task1", allowed_tools=[]),
            AgentTask(task_id="task2", prompt="task2", allowed_tools=[]),
        ]

        results = spawner.run_parallel(tasks)

        assert results[0].success is True
        assert results[1].success is False
        assert results[1].error is not None
        assert "Task 2 failed" in str(results[1].error)

    def test_run_parallel_with_progress_callback(self, tmp_path: Path) -> None:
        """Test progress callback is called correctly."""
        runner = Mock(spec=ClaudeCodeRunner)
        runner.run_analysis.return_value = ClaudeCodeResult(
            raw_output="{}",
            parsed_json={},
            result_text="Done",
            session_id=None,
            structured_output=None,
            return_code=0,
            stderr="",
        )

        progress_calls: list[tuple[str, int, int]] = []

        def track_progress(task_id: str, completed: int, total: int) -> None:
            progress_calls.append((task_id, completed, total))

        spawner = AgentSpawner(runner, max_workers=2)

        tasks = [
            AgentTask(task_id="task1", prompt="Test 1", allowed_tools=[]),
            AgentTask(task_id="task2", prompt="Test 2", allowed_tools=[]),
        ]

        spawner.run_parallel(tasks, progress_callback=track_progress)

        assert len(progress_calls) == 2
        # Final call should show 2/2 complete
        assert any(c[1] == 2 and c[2] == 2 for c in progress_calls)

    def test_run_model_comparison(self, tmp_path: Path) -> None:
        """Test model comparison convenience method."""
        runner = Mock(spec=ClaudeCodeRunner)
        runner.run_analysis.return_value = ClaudeCodeResult(
            raw_output="{}",
            parsed_json={},
            result_text="Done",
            session_id=None,
            structured_output=None,
            return_code=0,
            stderr="",
        )

        spawner = AgentSpawner(runner, max_workers=3)

        results = spawner.run_model_comparison(
            prompt="Analyze for vulnerabilities",
            allowed_tools=["Read"],
            models=["claude-opus-4", "claude-sonnet-4", "claude-haiku-4"],
        )

        assert len(results) == 3
        assert "claude-opus-4" in results
        assert "claude-sonnet-4" in results
        assert "claude-haiku-4" in results

        # Check that models were passed correctly
        calls = runner.run_analysis.call_args_list
        models_used = [call.kwargs.get("model") for call in calls]
        assert set(models_used) == {"claude-opus-4", "claude-sonnet-4", "claude-haiku-4"}

    def test_get_aggregate_stats(self, tmp_path: Path) -> None:
        """Test aggregate statistics calculation."""
        runner = Mock(spec=ClaudeCodeRunner)
        spawner = AgentSpawner(runner, max_workers=2)

        results = [
            AgentResult(
                task_id="task1",
                result=ClaudeCodeResult(
                    raw_output="",
                    parsed_json=None,
                    result_text="",
                    session_id=None,
                    structured_output=None,
                    return_code=0,
                    stderr="",
                    cost_usd=0.01,
                ),
                error=None,
                duration_ms=1000,
            ),
            AgentResult(
                task_id="task2",
                result=None,
                error=RuntimeError("Failed"),
                duration_ms=500,
            ),
            AgentResult(
                task_id="task3",
                result=ClaudeCodeResult(
                    raw_output="",
                    parsed_json=None,
                    result_text="",
                    session_id=None,
                    structured_output=None,
                    return_code=0,
                    stderr="",
                    cost_usd=0.02,
                ),
                error=None,
                duration_ms=2000,
            ),
        ]

        stats = spawner.get_aggregate_stats(results)

        assert stats["total_tasks"] == 3
        assert stats["successful"] == 2
        assert stats["failed"] == 1
        assert stats["total_duration_ms"] == 3500
        assert stats["avg_duration_ms"] == 1166  # 3500 // 3
        assert stats["total_cost_usd"] == 0.03
        assert "task2" in stats["failed_task_ids"]


class TestAgentTask:
    """Test AgentTask dataclass."""

    def test_default_values(self) -> None:
        """Test AgentTask default values."""
        task = AgentTask(task_id="test", prompt="Test prompt")

        assert task.allowed_tools == []
        assert task.json_schema is None
        assert task.model is None
        assert task.timeout_seconds == 300
        assert task.system_prompt is None
        assert task.metadata == {}


class TestAgentResult:
    """Test AgentResult dataclass."""

    def test_success_property(self) -> None:
        """Test success property."""
        success_result = AgentResult(
            task_id="test",
            result=ClaudeCodeResult(
                raw_output="",
                parsed_json=None,
                result_text="",
                session_id=None,
                structured_output=None,
                return_code=0,
                stderr="",
            ),
            error=None,
            duration_ms=100,
        )
        assert success_result.success is True

        failed_result = AgentResult(
            task_id="test",
            result=None,
            error=RuntimeError("Failed"),
            duration_ms=100,
        )
        assert failed_result.success is False

    def test_to_dict(self) -> None:
        """Test serialization to dict."""
        result = AgentResult(
            task_id="test",
            result=None,
            error=RuntimeError("Failed"),
            duration_ms=100,
            metadata={"key": "value"},
        )

        data = result.to_dict()

        assert data["task_id"] == "test"
        assert data["success"] is False
        assert data["error"] == "Failed"
        assert data["metadata"] == {"key": "value"}


class TestContractCase:
    """Test ContractCase dataclass."""

    def test_from_dict(self) -> None:
        """Test creating from dictionary."""
        data = {
            "path": "test.sol",
            "has_vulnerability": True,
            "expected_pattern": "reentrancy",
            "expected_severity": "critical",
            "ground_truth": [{"pattern": "reentrancy", "location": "withdraw"}],
        }

        case = ContractCase.from_dict(data)

        assert case.path == "test.sol"
        assert case.has_vulnerability is True
        assert case.expected_pattern == "reentrancy"
        assert len(case.ground_truth) == 1

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        case = ContractCase(
            path="test.sol",
            has_vulnerability=True,
            expected_pattern="reentrancy",
            ground_truth=[{"pattern": "reentrancy"}],
        )

        data = case.to_dict()

        assert data["path"] == "test.sol"
        assert data["has_vulnerability"] is True
        assert data["expected_pattern"] == "reentrancy"


class TestParsedFinding:
    """Test ParsedFinding dataclass."""

    def test_matches_pattern(self) -> None:
        """Test pattern matching."""
        finding = ParsedFinding(
            pattern="reentrancy-classic",
            severity="critical",
            location="test",
            confidence=0.9,
        )

        assert finding.matches_pattern("reentrancy") is True
        assert finding.matches_pattern("REENTRANCY") is True
        assert finding.matches_pattern("overflow") is False

    def test_matches_severity(self) -> None:
        """Test severity matching."""
        finding = ParsedFinding(
            pattern="test",
            severity="critical",
            location="test",
            confidence=0.9,
        )

        assert finding.matches_severity("critical") is True
        assert finding.matches_severity("CRITICAL") is True
        assert finding.matches_severity("high") is False

    def test_from_dict(self) -> None:
        """Test creating from dictionary."""
        data = {
            "pattern": "reentrancy",
            "severity": "critical",
            "location": "withdraw:45",
            "confidence": 0.95,
            "reasoning": "External call before state update",
        }

        finding = ParsedFinding.from_dict(data)

        assert finding.pattern == "reentrancy"
        assert finding.confidence == 0.95
        assert finding.reasoning == "External call before state update"
