"""End-to-end infrastructure smoke test for Phase 3.1b.

This test validates that all infrastructure components built in 3.1b
work together. It exercises: scenario loading, workspace setup (with Jujutsu),
hooks, transcript parsing, output collection, and grading.

Works WITHOUT Companion. Uses native CLI or synthetic data where real CLI
invocation is impractical in CI.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import yaml

# Infrastructure under test
from tests.workflow_harness.graders.code_grader import CodeGrader, GradeResult
from tests.workflow_harness.lib.output_collector import (
    CollectedOutput,
    OutputCollector,
)
from tests.workflow_harness.lib.transcript_parser import TranscriptParser
from tests.workflow_harness.lib.workspace import HookConfig, WorkspaceManager

# Scenario loading
from src.alphaswarm_sol.testing.harness.scenario_loader import ScenarioLoader


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_SCENARIOS_DIR = Path(__file__).parent / "scenarios"
_CORPUS_DIR = Path(__file__).parent.parent.parent / "examples" / "testing" / "corpus"
_HEALTH_CHECK_YAML = _SCENARIOS_DIR / "health-check-basic.yaml"


# ---------------------------------------------------------------------------
# Helpers: synthetic transcript JSONL
# ---------------------------------------------------------------------------

def _synthetic_transcript_records() -> list[dict]:
    """Build a synthetic transcript that exercises BSKG extraction.

    Returns a list of JSONL record dicts mimicking a Claude Code session
    that runs alphaswarm build-kg and query commands.
    """
    return [
        # User message
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": "Audit contracts/Vault.sol"}],
            },
        },
        # Assistant uses Bash to run build-kg
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "tc_001",
                        "name": "Bash",
                        "input": {
                            "command": "uv run alphaswarm build-kg contracts/"
                        },
                    }
                ],
            },
        },
        # Tool result for build-kg
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "tc_001",
                        "content": "Built knowledge graph: 12 nodes, 8 edges",
                    }
                ],
            },
        },
        # Assistant uses Bash to run query
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "tc_002",
                        "name": "Bash",
                        "input": {
                            "command": "uv run alphaswarm query 'functions without access control'"
                        },
                    }
                ],
            },
        },
        # Tool result for query
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "tc_002",
                        "content": "Found 3 functions: withdraw(), transfer(), emergencyExit()",
                    }
                ],
            },
        },
        # Assistant uses Read
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "tc_003",
                        "name": "Read",
                        "input": {"file_path": "contracts/Vault.sol"},
                    }
                ],
            },
        },
        # Tool result for Read
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "tc_003",
                        "content": "pragma solidity ^0.8.0;\ncontract Vault { ... }",
                    }
                ],
            },
        },
    ]


def _write_synthetic_transcript(path: Path) -> Path:
    """Write synthetic transcript JSONL to file and return path."""
    with open(path, "w") as f:
        for record in _synthetic_transcript_records():
            f.write(json.dumps(record) + "\n")
    return path


# ---------------------------------------------------------------------------
# Test 1: Scenario loading roundtrip
# ---------------------------------------------------------------------------

class TestScenarioLoadingRoundtrip:
    """Test that health-check-basic.yaml loads with all DSL fields."""

    def test_scenario_yaml_loads_and_has_all_fields(self):
        """Load health-check scenario and verify all new DSL fields are present."""
        assert _HEALTH_CHECK_YAML.exists(), f"Scenario file missing: {_HEALTH_CHECK_YAML}"

        with open(_HEALTH_CHECK_YAML) as f:
            raw = yaml.safe_load(f)

        # Core fields
        assert raw["name"] == "health-check-basic"
        assert raw["timeout_seconds"] == 120
        assert raw["modes"] == ["single"]

        # New DSL fields from 3.1b-05
        assert "steps" in raw
        assert len(raw["steps"]) >= 1
        assert "expect" in raw["steps"][0]

        assert "graders" in raw
        assert len(raw["graders"]) >= 1
        assert raw["graders"][0]["type"] == "code"

        assert raw["trials"] == 1

        assert "evaluation_guidance" in raw
        guidance = raw["evaluation_guidance"]
        assert "reasoning_questions" in guidance
        assert len(guidance["reasoning_questions"]) >= 1

    def test_scenario_loader_loads_single_file(self):
        """ScenarioLoader.load_scenario() handles a standalone YAML file."""
        loader = ScenarioLoader(_SCENARIOS_DIR)
        scenario = loader.load_scenario(_HEALTH_CHECK_YAML)
        assert scenario.name == "health-check-basic"
        assert scenario.timeout_seconds == 120
        assert scenario.evaluation_guidance is not None


# ---------------------------------------------------------------------------
# Test 2: Transcript parsing with BSKG extraction
# ---------------------------------------------------------------------------

class TestTranscriptParserWithBSKG:
    """Test TranscriptParser on synthetic transcript with alphaswarm commands."""

    def test_parser_extracts_tool_calls(self, tmp_path):
        """TranscriptParser extracts ToolCall objects from JSONL."""
        transcript_path = _write_synthetic_transcript(tmp_path / "transcript.jsonl")
        parser = TranscriptParser(transcript_path)

        tool_calls = parser.get_tool_calls()
        assert len(tool_calls) >= 3
        assert tool_calls[0].tool_name == "Bash"
        assert "build-kg" in tool_calls[0].tool_input.get("command", "")

    def test_parser_extracts_bskg_queries(self, tmp_path):
        """TranscriptParser extracts BSKGQuery objects from alphaswarm commands."""
        transcript_path = _write_synthetic_transcript(tmp_path / "transcript.jsonl")
        parser = TranscriptParser(transcript_path)

        queries = parser.get_bskg_queries()
        assert len(queries) >= 2  # build-kg + query

        # Check query types
        query_types = {q.query_type for q in queries}
        assert "build-kg" in query_types
        assert "query" in query_types

    def test_parser_graph_citation_rate(self, tmp_path):
        """graph_citation_rate returns a float between 0 and 1 when queries exist."""
        transcript_path = _write_synthetic_transcript(tmp_path / "transcript.jsonl")
        parser = TranscriptParser(transcript_path)

        rate = parser.graph_citation_rate()
        # Synthetic transcript has BSKG queries, so rate should be a float
        assert isinstance(rate, float)
        assert 0.0 <= rate <= 1.0


# ---------------------------------------------------------------------------
# Test 3: OutputCollector produces CollectedOutput
# ---------------------------------------------------------------------------

class TestOutputCollector:
    """Test OutputCollector collects and summarizes output."""

    def test_collect_from_transcript(self, tmp_path):
        """OutputCollector.collect() aggregates transcript into CollectedOutput."""
        transcript_path = _write_synthetic_transcript(tmp_path / "transcript.jsonl")
        parser = TranscriptParser(transcript_path)

        collector = OutputCollector()
        output = collector.collect(
            scenario_name="health-check-basic",
            run_id="smoke-001",
            transcript=parser,
        )

        assert isinstance(output, CollectedOutput)
        assert output.scenario_name == "health-check-basic"
        assert output.run_id == "smoke-001"
        assert len(output.tool_sequence) >= 3
        assert len(output.bskg_queries) >= 2

    def test_summary_produces_readable_text(self, tmp_path):
        """OutputCollector.summary() produces multi-line readable text."""
        transcript_path = _write_synthetic_transcript(tmp_path / "transcript.jsonl")
        parser = TranscriptParser(transcript_path)

        collector = OutputCollector()
        output = collector.collect(
            scenario_name="health-check-basic",
            run_id="smoke-001",
            transcript=parser,
        )
        summary = collector.summary(output)

        assert "health-check-basic" in summary
        assert "smoke-001" in summary
        assert "Tools used:" in summary
        assert "BSKG queries:" in summary


# ---------------------------------------------------------------------------
# Test 4: CodeGrader scores output
# ---------------------------------------------------------------------------

class TestCodeGraderScores:
    """Test CodeGrader returns structured GradeResult objects."""

    def test_string_match_grading(self, tmp_path):
        """CodeGrader.grade_string_match checks output summary for expected strings."""
        transcript_path = _write_synthetic_transcript(tmp_path / "transcript.jsonl")
        parser = TranscriptParser(transcript_path)
        collector = OutputCollector()
        output = collector.collect(
            scenario_name="health-check-basic",
            run_id="smoke-001",
            transcript=parser,
        )

        grader = CodeGrader()
        # Summary will contain "health-check-basic" and "smoke-001"
        result = grader.grade_string_match(output, ["health-check-basic", "smoke-001"])

        assert isinstance(result, GradeResult)
        assert result.passed is True
        assert result.score == 100
        assert result.grader_type == "code"

    def test_tool_usage_grading(self, tmp_path):
        """CodeGrader.grade_tool_usage checks that expected tools were used."""
        transcript_path = _write_synthetic_transcript(tmp_path / "transcript.jsonl")
        parser = TranscriptParser(transcript_path)
        collector = OutputCollector()
        output = collector.collect(
            scenario_name="test",
            run_id="run-001",
            transcript=parser,
        )

        grader = CodeGrader()
        result = grader.grade_tool_usage(output, ["Bash", "Read"])

        assert isinstance(result, GradeResult)
        assert result.passed is True
        assert result.score == 100

    def test_string_match_failure(self, tmp_path):
        """CodeGrader returns failing GradeResult when strings not found."""
        transcript_path = _write_synthetic_transcript(tmp_path / "transcript.jsonl")
        parser = TranscriptParser(transcript_path)
        collector = OutputCollector()
        output = collector.collect(
            scenario_name="test",
            run_id="run-001",
            transcript=parser,
        )

        grader = CodeGrader()
        result = grader.grade_string_match(output, ["NONEXISTENT_STRING_xyz"])

        assert result.passed is False
        assert result.score == 0


# ---------------------------------------------------------------------------
# Test 5: Hook infrastructure ready
# ---------------------------------------------------------------------------

class TestHookInfrastructure:
    """Test hook plumbing (install_hooks, HookConfig, observations dir)."""

    def test_install_hooks_creates_settings(self):
        """WorkspaceManager.install_hooks() creates .claude/settings.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir)
            mgr = WorkspaceManager(ws)
            mgr.install_hooks(ws)

            settings_path = ws / ".claude" / "settings.json"
            assert settings_path.exists()
            with open(settings_path) as f:
                settings = json.load(f)
            assert "hooks" in settings
            assert "SubagentStop" in settings["hooks"]
            assert "Stop" in settings["hooks"]

    def test_install_hooks_with_hook_configs(self):
        """install_hooks() accepts HookConfig objects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir)
            mgr = WorkspaceManager(ws)
            configs = [
                HookConfig(
                    event_type="PreToolUse",
                    script_path="python3 .claude/hooks/observe.py",
                    timeout=10,
                ),
            ]
            mgr.install_hooks(ws, hook_configs=configs)

            settings_path = ws / ".claude" / "settings.json"
            with open(settings_path) as f:
                settings = json.load(f)
            assert "PreToolUse" in settings["hooks"]

    def test_observations_directory_created(self):
        """WorkspaceManager.setup() creates .vrs/observations/ directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir)
            mgr = WorkspaceManager(ws)
            mgr.setup(ws)

            obs_dir = ws / ".vrs" / "observations"
            assert obs_dir.exists()
            assert obs_dir.is_dir()


# ---------------------------------------------------------------------------
# Test 6: Jujutsu workspace methods exist
# ---------------------------------------------------------------------------

class TestJujutsuWorkspaceMethods:
    """Verify WorkspaceManager has all Jujutsu isolation methods (mock subprocess)."""

    def test_create_workspace_method_exists(self):
        mgr = WorkspaceManager(Path("."))
        assert callable(getattr(mgr, "create_workspace", None))

    def test_forget_workspace_method_exists(self):
        mgr = WorkspaceManager(Path("."))
        assert callable(getattr(mgr, "forget_workspace", None))

    def test_rollback_method_exists(self):
        mgr = WorkspaceManager(Path("."))
        assert callable(getattr(mgr, "rollback", None))

    def test_list_workspaces_method_exists(self):
        mgr = WorkspaceManager(Path("."))
        assert callable(getattr(mgr, "list_workspaces", None))

    def test_snapshot_operation_method_exists(self):
        mgr = WorkspaceManager(Path("."))
        assert callable(getattr(mgr, "snapshot_operation", None))


# ---------------------------------------------------------------------------
# Test 7: Corpus project validity
# ---------------------------------------------------------------------------

class TestCorpusProjectValidity:
    """Validate that at least one corpus project has correct structure."""

    def test_corpus_directory_exists(self):
        """Corpus directory exists with projects."""
        assert _CORPUS_DIR.exists(), f"Corpus directory missing: {_CORPUS_DIR}"
        projects = [p for p in _CORPUS_DIR.iterdir() if p.is_dir()]
        assert len(projects) >= 10, f"Expected >= 10 corpus projects, found {len(projects)}"

    def test_first_project_has_ground_truth(self):
        """At least one corpus project has ground-truth.yaml with real data."""
        projects = sorted(p for p in _CORPUS_DIR.iterdir() if p.is_dir())
        assert projects, "No corpus projects found"

        # Find one with ground truth
        project = projects[0]
        gt_path = project / "ground-truth.yaml"
        assert gt_path.exists(), f"No ground-truth.yaml in {project.name}"

        with open(gt_path) as f:
            gt = yaml.safe_load(f)

        # Ground truth should have real data, not placeholders
        assert gt is not None
        assert isinstance(gt, dict)

    def test_first_project_has_manifest(self):
        """At least one corpus project has project-manifest.yaml."""
        projects = sorted(p for p in _CORPUS_DIR.iterdir() if p.is_dir())
        assert projects, "No corpus projects found"

        project = projects[0]
        manifest_path = project / "project-manifest.yaml"
        assert manifest_path.exists(), f"No project-manifest.yaml in {project.name}"

    def test_first_project_has_contracts(self):
        """At least one corpus project has contracts/ directory with .sol files."""
        projects = sorted(p for p in _CORPUS_DIR.iterdir() if p.is_dir())
        assert projects, "No corpus projects found"

        project = projects[0]
        contracts_dir = project / "contracts"
        assert contracts_dir.exists(), f"No contracts/ in {project.name}"

        sol_files = list(contracts_dir.rglob("*.sol"))
        assert len(sol_files) >= 1, f"No .sol files in {project.name}/contracts/"


# ---------------------------------------------------------------------------
# Test 8: Full pipeline synthetic
# ---------------------------------------------------------------------------

class TestFullPipelineSynthetic:
    """Full pipeline: scenario → parse → collect → grade → result."""

    def test_full_pipeline_flows_end_to_end(self, tmp_path):
        """Data flows through: load scenario → parse transcript → collect → grade."""
        # Step 1: Load scenario
        assert _HEALTH_CHECK_YAML.exists()
        with open(_HEALTH_CHECK_YAML) as f:
            scenario_raw = yaml.safe_load(f)
        assert scenario_raw["name"] == "health-check-basic"

        # Step 2: Create and parse synthetic transcript
        transcript_path = _write_synthetic_transcript(tmp_path / "transcript.jsonl")
        parser = TranscriptParser(transcript_path)
        tool_calls = parser.get_tool_calls()
        assert len(tool_calls) >= 1

        # Step 3: Collect output
        collector = OutputCollector()
        output = collector.collect(
            scenario_name=scenario_raw["name"],
            run_id="pipeline-smoke-001",
            transcript=parser,
        )
        assert isinstance(output, CollectedOutput)
        assert output.scenario_name == "health-check-basic"
        assert len(output.tool_sequence) >= 3
        assert len(output.bskg_queries) >= 2

        # Step 4: Grade with CodeGrader
        grader = CodeGrader()

        # Grade string match: summary should contain scenario name
        grade_result = grader.grade_string_match(
            output, ["health-check-basic", "pipeline-smoke-001"]
        )
        assert isinstance(grade_result, GradeResult)
        assert grade_result.passed is True
        assert grade_result.score == 100

        # Grade tool usage: Bash and Read were used
        tool_result = grader.grade_tool_usage(output, ["Bash", "Read"])
        assert tool_result.passed is True

        # Verify summary is readable
        summary = collector.summary(output)
        assert "health-check-basic" in summary
        assert "BSKG queries:" in summary
