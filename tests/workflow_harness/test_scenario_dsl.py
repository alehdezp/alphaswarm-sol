"""Tests for Scenario DSL extensions, CodeGrader, and ModelGrader.

Validates:
- ScenarioConfig parsing with new evaluation/grader/step fields
- CodeGrader deterministic checks (string match, regex, tool usage, schema)
- ModelGrader with mocked subprocess (no real claude calls)
- GradeResult structured result objects
- Full DSL round-trip: YAML -> ScenarioConfig -> graders -> GradeResult
- Backward compatibility (existing scenarios still load)
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from src.alphaswarm_sol.testing.scenarios.config_schema import (
    EvaluationConfig,
    EvaluationGuidanceConfig,
    GraderConfig,
    ScenarioConfig,
    ScenarioStep,
    StepExpect,
)
from tests.workflow_harness.graders import CodeGrader, ModelGrader
from tests.workflow_harness.graders.code_grader import GradeResult
from tests.workflow_harness.lib.output_collector import CollectedOutput


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_output() -> CollectedOutput:
    """A CollectedOutput with known content for grading tests."""
    return CollectedOutput(
        scenario_name="test-scenario",
        run_id="run-001",
        transcript=None,
        team_observation=None,
        structured_output={"has_vulnerability": True, "findings": []},
        tool_sequence=["Bash", "Read", "Glob", "Bash"],
        bskg_queries=[],
        duration_ms=1500.0,
        cost_usd=0.0,
        failure_notes="",
    )


@pytest.fixture
def code_grader() -> CodeGrader:
    return CodeGrader()


@pytest.fixture
def full_scenario_yaml(tmp_path: Path) -> Path:
    """Create a YAML file with all new DSL fields."""
    data = {
        "name": "health-check-basic",
        "category": "health-check",
        "description": "Verify health check output",
        "timeout_seconds": 120,
        "model": "sonnet",
        "modes": ["single"],
        "contracts": [
            {
                "path": "examples/testing/simple/Token.sol",
                "has_vulnerability": False,
            }
        ],
        "prompt_template": "Run /vrs-health-check on {contract_path}",
        "graders": [
            {
                "type": "code",
                "method": "contains_all",
                "expected": ["alphaswarm", "build-kg"],
                "target": "response",
            },
            {
                "type": "model",
                "prompt": "Did the agent check all components?",
                "model": "sonnet",
            },
        ],
        "trials": 3,
        "evaluation": {
            "contract": "vrs-health-check",
            "run_gvs": False,
            "run_reasoning": False,
        },
        "evaluation_guidance": {
            "reasoning_questions": [
                "Did the health check cover all required components?",
            ],
            "hooks_if_failed": ["hooks/debug_health_check.py"],
        },
        "steps": [
            {
                "prompt": "Step 1: Run health check",
                "expect": {
                    "response_contains": ["OK"],
                    "tool_was_used": ["Bash"],
                },
            },
            {
                "prompt": "Step 2: Verify output",
            },
        ],
        "post_run_hooks": ["hooks/log_completion.py"],
    }
    yaml_path = tmp_path / "scenario.yaml"
    with open(yaml_path, "w") as f:
        yaml.dump(data, f)
    return yaml_path


# ---------------------------------------------------------------------------
# ScenarioConfig parsing tests
# ---------------------------------------------------------------------------


class TestScenarioConfigParsing:
    """Test that ScenarioConfig parses all new DSL fields."""

    def test_load_yaml_with_all_new_fields(self, full_scenario_yaml: Path) -> None:
        config = ScenarioConfig.from_yaml(full_scenario_yaml)

        assert config.name == "health-check-basic"
        assert config.evaluation is not None
        assert config.evaluation.contract == "vrs-health-check"
        assert config.evaluation.run_gvs is False
        assert config.evaluation.run_reasoning is False

        assert config.evaluation_guidance is not None
        assert len(config.evaluation_guidance.reasoning_questions) == 1
        assert config.evaluation_guidance.hooks_if_failed == ["hooks/debug_health_check.py"]

        assert len(config.graders) == 2
        assert config.graders[0].type == "code"
        assert config.graders[0].method == "contains_all"
        assert config.graders[1].type == "model"

        assert len(config.steps) == 2
        assert config.steps[0].prompt == "Step 1: Run health check"
        assert config.steps[0].expect is not None
        assert config.steps[0].expect.response_contains == ["OK"]
        assert config.steps[1].expect is None

        assert config.post_run_hooks == ["hooks/log_completion.py"]
        assert config.trials == 3

    def test_backward_compat_no_new_fields(self, tmp_path: Path) -> None:
        """Existing scenarios without new fields should load without error."""
        data = {
            "name": "legacy-scenario",
            "category": "reentrancy",
            "contracts": [
                {"path": "vuln.sol", "has_vulnerability": True}
            ],
            "prompt_template": "Analyze {contract_path}",
        }
        yaml_path = tmp_path / "legacy.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(data, f)

        config = ScenarioConfig.from_yaml(yaml_path)
        assert config.evaluation is None
        assert config.evaluation_guidance is None
        assert config.graders == []
        assert config.steps == []
        assert config.post_run_hooks == []
        assert config.trials == 1

    def test_evaluation_config_defaults(self) -> None:
        cfg = EvaluationConfig()
        assert cfg.contract is None
        assert cfg.run_gvs is True
        assert cfg.run_reasoning is True

    def test_evaluation_guidance_config_defaults(self) -> None:
        cfg = EvaluationGuidanceConfig()
        assert cfg.reasoning_questions == []
        assert cfg.hooks_if_failed == []

    def test_grader_config_code_type(self) -> None:
        cfg = GraderConfig(type="code", method="string_match", expected=["hello"])
        assert cfg.type == "code"
        assert cfg.method == "string_match"
        assert cfg.expected == ["hello"]
        assert cfg.target is None

    def test_grader_config_model_type(self) -> None:
        cfg = GraderConfig(type="model", prompt="Evaluate quality")
        assert cfg.type == "model"
        assert cfg.prompt == "Evaluate quality"
        assert cfg.model == "sonnet"

    def test_step_with_expect(self) -> None:
        step = ScenarioStep(
            prompt="Do something",
            expect=StepExpect(
                response_contains=["success"],
                tool_was_used=["Bash"],
                response_not_contains=["error"],
            ),
        )
        assert step.prompt == "Do something"
        assert step.expect is not None
        assert step.expect.response_contains == ["success"]

    def test_step_without_expect(self) -> None:
        step = ScenarioStep(prompt="Do something")
        assert step.expect is None

    def test_round_trip_yaml(self, full_scenario_yaml: Path, tmp_path: Path) -> None:
        """Load from YAML, save to YAML, reload -- should be equivalent."""
        original = ScenarioConfig.from_yaml(full_scenario_yaml)
        out_path = tmp_path / "roundtrip.yaml"
        original.to_yaml(out_path)
        reloaded = ScenarioConfig.from_yaml(out_path)
        assert reloaded.name == original.name
        assert reloaded.evaluation is not None
        assert reloaded.evaluation.contract == original.evaluation.contract
        assert reloaded.trials == original.trials


# ---------------------------------------------------------------------------
# CodeGrader tests
# ---------------------------------------------------------------------------


class TestCodeGrader:
    """Test deterministic grading methods."""

    def test_string_match_pass(self, code_grader: CodeGrader, sample_output: CollectedOutput) -> None:
        result = code_grader.grade_string_match(sample_output, ["test-scenario", "run-001"])
        assert result.passed is True
        assert result.score == 100
        assert result.grader_type == "code"

    def test_string_match_fail(self, code_grader: CodeGrader, sample_output: CollectedOutput) -> None:
        result = code_grader.grade_string_match(sample_output, ["nonexistent-string"])
        assert result.passed is False
        assert result.score == 0
        assert "Missing" in result.reason

    def test_string_match_partial(self, code_grader: CodeGrader, sample_output: CollectedOutput) -> None:
        result = code_grader.grade_string_match(sample_output, ["test-scenario", "nonexistent"])
        assert result.passed is False
        assert result.score == 50

    def test_string_match_empty_expected(self, code_grader: CodeGrader, sample_output: CollectedOutput) -> None:
        result = code_grader.grade_string_match(sample_output, [])
        assert result.passed is True
        assert result.score == 100

    def test_regex_match(self, code_grader: CodeGrader, sample_output: CollectedOutput) -> None:
        result = code_grader.grade_regex(sample_output, r"Scenario:\s+test-scenario")
        assert result.passed is True
        assert result.score == 100

    def test_regex_no_match(self, code_grader: CodeGrader, sample_output: CollectedOutput) -> None:
        result = code_grader.grade_regex(sample_output, r"NEVER_MATCHES_\d+")
        assert result.passed is False
        assert result.score == 0

    def test_regex_invalid_pattern(self, code_grader: CodeGrader, sample_output: CollectedOutput) -> None:
        result = code_grader.grade_regex(sample_output, r"[invalid")
        assert result.passed is False
        assert "Invalid regex" in result.reason

    def test_tool_usage_pass(self, code_grader: CodeGrader, sample_output: CollectedOutput) -> None:
        result = code_grader.grade_tool_usage(sample_output, ["Bash", "Read"])
        assert result.passed is True
        assert result.score == 100

    def test_tool_usage_fail(self, code_grader: CodeGrader, sample_output: CollectedOutput) -> None:
        result = code_grader.grade_tool_usage(sample_output, ["Bash", "Write"])
        assert result.passed is False
        assert result.score == 50

    def test_tool_usage_empty(self, code_grader: CodeGrader, sample_output: CollectedOutput) -> None:
        result = code_grader.grade_tool_usage(sample_output, [])
        assert result.passed is True

    def test_grade_routing_string_match(self, code_grader: CodeGrader, sample_output: CollectedOutput) -> None:
        config = GraderConfig(type="code", method="string_match", expected=["test-scenario"])
        result = code_grader.grade(sample_output, config)
        assert result.passed is True

    def test_grade_routing_contains_all(self, code_grader: CodeGrader, sample_output: CollectedOutput) -> None:
        config = GraderConfig(type="code", method="contains_all", expected=["test-scenario"])
        result = code_grader.grade(sample_output, config)
        assert result.passed is True

    def test_grade_routing_regex(self, code_grader: CodeGrader, sample_output: CollectedOutput) -> None:
        config = GraderConfig(type="code", method="regex", pattern=r"run-\d+")
        result = code_grader.grade(sample_output, config)
        assert result.passed is True

    def test_grade_routing_tool_usage(self, code_grader: CodeGrader, sample_output: CollectedOutput) -> None:
        config = GraderConfig(type="code", method="tool_usage", expected=["Bash"])
        result = code_grader.grade(sample_output, config)
        assert result.passed is True

    def test_grade_routing_unknown_method(self, code_grader: CodeGrader, sample_output: CollectedOutput) -> None:
        config = GraderConfig(type="code", method="unknown_method")
        result = code_grader.grade(sample_output, config)
        assert result.passed is False
        assert "Unknown" in result.reason

    def test_schema_validation_pass(self, code_grader: CodeGrader, sample_output: CollectedOutput, tmp_path: Path) -> None:
        schema = {
            "type": "object",
            "properties": {"has_vulnerability": {"type": "boolean"}},
            "required": ["has_vulnerability"],
        }
        schema_path = tmp_path / "test_schema.json"
        with open(schema_path, "w") as f:
            json.dump(schema, f)

        result = code_grader.grade_schema(sample_output, str(schema_path))
        assert result.passed is True

    def test_schema_validation_fail(self, code_grader: CodeGrader, tmp_path: Path) -> None:
        output = CollectedOutput(
            scenario_name="test",
            run_id="run-001",
            structured_output={"wrong_field": 123},
        )
        schema = {
            "type": "object",
            "required": ["has_vulnerability"],
        }
        schema_path = tmp_path / "strict_schema.json"
        with open(schema_path, "w") as f:
            json.dump(schema, f)

        result = code_grader.grade_schema(output, str(schema_path))
        assert result.passed is False

    def test_schema_no_structured_output(self, code_grader: CodeGrader) -> None:
        output = CollectedOutput(
            scenario_name="test",
            run_id="run-001",
            structured_output=None,
        )
        result = code_grader.grade_schema(output, "some_schema.json")
        assert result.passed is False
        assert "No structured_output" in result.reason

    def test_schema_file_not_found(self, code_grader: CodeGrader, sample_output: CollectedOutput) -> None:
        result = code_grader.grade_schema(sample_output, "/nonexistent/schema.json")
        assert result.passed is False
        assert "not found" in result.reason


# ---------------------------------------------------------------------------
# ModelGrader tests (mocked subprocess)
# ---------------------------------------------------------------------------


class TestModelGrader:
    """Test AI judge grading with mocked subprocess calls."""

    def test_grade_success(self, sample_output: CollectedOutput) -> None:
        grader = ModelGrader(model="sonnet", timeout=30)

        mock_response = json.dumps({
            "passed": True,
            "score": 85,
            "reason": "Good analysis coverage",
        })
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = mock_response

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = grader.grade(sample_output, "Evaluate the analysis quality")

        assert result.passed is True
        assert result.score == 85
        assert result.reason == "Good analysis coverage"
        assert result.grader_type == "model"
        mock_run.assert_called_once()

    def test_grade_failure_response(self, sample_output: CollectedOutput) -> None:
        grader = ModelGrader()

        mock_response = json.dumps({
            "passed": False,
            "score": 20,
            "reason": "Missing key checks",
        })
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = mock_response

        with patch("subprocess.run", return_value=mock_result):
            result = grader.grade(sample_output, "Evaluate")

        assert result.passed is False
        assert result.score == 20

    def test_grade_cli_not_found(self, sample_output: CollectedOutput) -> None:
        grader = ModelGrader()

        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = grader.grade(sample_output, "Evaluate")

        assert result.passed is False
        assert "not found" in result.reason

    def test_grade_timeout(self, sample_output: CollectedOutput) -> None:
        grader = ModelGrader(timeout=5)

        import subprocess

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("claude", 5)):
            result = grader.grade(sample_output, "Evaluate")

        assert result.passed is False
        assert "timed out" in result.reason

    def test_grade_nonzero_exit(self, sample_output: CollectedOutput) -> None:
        grader = ModelGrader()

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Some error"

        with patch("subprocess.run", return_value=mock_result):
            result = grader.grade(sample_output, "Evaluate")

        assert result.passed is False
        assert "exited with code 1" in result.reason

    def test_grade_unparseable_response(self, sample_output: CollectedOutput) -> None:
        grader = ModelGrader()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Not JSON at all"

        with patch("subprocess.run", return_value=mock_result):
            result = grader.grade(sample_output, "Evaluate")

        assert result.passed is False
        assert "No JSON" in result.reason

    def test_grade_wrapped_json_response(self, sample_output: CollectedOutput) -> None:
        """--output-format json wraps in {"result": "..."}"""
        grader = ModelGrader()

        inner = json.dumps({"passed": True, "score": 90, "reason": "Excellent"})
        wrapped = json.dumps({"result": inner})
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = wrapped

        with patch("subprocess.run", return_value=mock_result):
            result = grader.grade(sample_output, "Evaluate")

        assert result.passed is True
        assert result.score == 90

    def test_prompt_construction(self, sample_output: CollectedOutput) -> None:
        """Verify the prompt sent to claude includes both output summary and instructions."""
        grader = ModelGrader()
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"passed": True, "score": 100, "reason": "OK"})

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            grader.grade(sample_output, "Check completeness")

        # Extract the prompt argument from the call
        call_args = mock_run.call_args[0][0]
        prompt_arg = call_args[3]  # -p argument
        assert "test-scenario" in prompt_arg  # output summary included
        assert "Check completeness" in prompt_arg  # evaluation instructions included
        assert "AI judge" in prompt_arg  # system context included


# ---------------------------------------------------------------------------
# GradeResult tests
# ---------------------------------------------------------------------------


class TestGradeResult:
    """Test GradeResult dataclass creation."""

    def test_create_passing(self) -> None:
        result = GradeResult(passed=True, score=1.0, reason="All checks passed", grader_type="code")
        assert result.passed is True
        assert result.score == 1.0

    def test_create_failing(self) -> None:
        result = GradeResult(passed=False, score=0.3, reason="Partial match", grader_type="model")
        assert result.passed is False
        assert result.score == 0.3
        assert result.grader_type == "model"


# ---------------------------------------------------------------------------
# Full DSL round-trip test
# ---------------------------------------------------------------------------


class TestDSLRoundTrip:
    """Test full YAML -> ScenarioConfig -> run graders -> GradeResult pipeline."""

    def test_yaml_to_grader_roundtrip(self, full_scenario_yaml: Path, sample_output: CollectedOutput) -> None:
        """Load scenario YAML, extract grader configs, run code grader, get results."""
        config = ScenarioConfig.from_yaml(full_scenario_yaml)

        code_grader = CodeGrader()

        # Run the code grader (first grader in the scenario)
        code_grader_config = config.graders[0]
        assert code_grader_config.type == "code"
        assert code_grader_config.method == "contains_all"

        result = code_grader.grade(sample_output, code_grader_config)
        assert isinstance(result, GradeResult)
        assert result.grader_type == "code"
        # Expected strings are "alphaswarm" and "build-kg" which are NOT
        # in the sample_output summary, so this should fail
        assert result.passed is False

    def test_scenario_loader_with_new_fields(self, tmp_path: Path) -> None:
        """ScenarioLoader parses new fields into TestScenario."""
        from src.alphaswarm_sol.testing.harness.scenario_loader import ScenarioLoader

        scenario_dir = tmp_path / "scenarios" / "test_cat"
        scenario_dir.mkdir(parents=True)
        data = {
            "name": "loader-test",
            "category": "test",
            "contracts": [{"path": "test.sol", "has_vulnerability": True}],
            "prompt_template": "Analyze {contract_path}",
            "evaluation": {"contract": "test-eval", "run_gvs": True},
            "evaluation_guidance": {
                "reasoning_questions": ["Did it work?"],
                "hooks_if_failed": ["hooks/retry.py"],
            },
            "graders": [{"type": "code", "method": "string_match", "expected": ["OK"]}],
            "steps": [{"prompt": "Step 1"}],
            "post_run_hooks": ["hooks/log.py"],
            "trials": 2,
        }
        with open(scenario_dir / "config.yaml", "w") as f:
            yaml.dump(data, f)

        loader = ScenarioLoader(tmp_path / "scenarios", validate_schema=False)
        scenarios = loader.load_all()
        scenario = scenarios["loader-test"]

        # Verify new fields are preserved in TestScenario
        assert scenario.evaluation is not None
        assert scenario.evaluation["contract"] == "test-eval"
        assert scenario.evaluation_guidance is not None
        assert scenario.evaluation_guidance["reasoning_questions"] == ["Did it work?"]
        assert len(scenario.graders) == 1
        assert len(scenario.steps) == 1
        assert scenario.post_run_hooks == ["hooks/log.py"]
        assert scenario.trials == 2

    def test_scenario_loader_backward_compat(self, tmp_path: Path) -> None:
        """Old scenarios without new fields still load."""
        from src.alphaswarm_sol.testing.harness.scenario_loader import ScenarioLoader

        scenario_dir = tmp_path / "scenarios" / "legacy"
        scenario_dir.mkdir(parents=True)
        data = {
            "name": "legacy-scenario",
            "category": "reentrancy",
            "contracts": [{"path": "vuln.sol"}],
            "prompt_template": "Analyze {contract_path}",
        }
        with open(scenario_dir / "config.yaml", "w") as f:
            yaml.dump(data, f)

        loader = ScenarioLoader(tmp_path / "scenarios", validate_schema=False)
        scenarios = loader.load_all()
        scenario = scenarios["legacy-scenario"]

        assert scenario.evaluation is None
        assert scenario.evaluation_guidance is None
        assert scenario.graders == []
        assert scenario.steps == []
        assert scenario.post_run_hooks == []
        assert scenario.trials == 1
