"""Integration tests for 3.1c API contracts.

These tests verify that 3.1b implementations match the API contracts
specified in api-contracts/*.md. All contracts are now implemented.

Each test imports or instantiates a type from the contract,
ensuring the contract and the codebase module structure are aligned.

Run: pytest tests/workflow_harness/test_api_contracts_stub.py -v
"""


# ---------------------------------------------------------------------------
# Contract: transcript-parser.md (3.1b-02)
# ---------------------------------------------------------------------------


class TestTranscriptParserContracts:
    """Verify TranscriptParser extension contracts from transcript-parser.md."""

    def test_toolcall_has_timestamp_field(self):
        from tests.workflow_harness.lib.transcript_parser import ToolCall

        tc = ToolCall(
            tool_name="Bash",
            tool_input={"command": "echo hello"},
            tool_result="hello",
            index=0,
            timestamp="2026-01-15T10:30:00Z",
            duration_ms=150,
        )
        assert tc.timestamp == "2026-01-15T10:30:00Z"
        assert tc.duration_ms == 150

    def test_toolcall_has_duration_ms_field(self):
        from tests.workflow_harness.lib.transcript_parser import ToolCall

        tc = ToolCall(
            tool_name="Read",
            tool_input={},
            tool_result="file content",
            index=1,
            duration_ms=42,
        )
        assert tc.duration_ms == 42

    def test_toolcall_has_content_block_field(self):
        from tests.workflow_harness.lib.transcript_parser import ToolCall

        tc = ToolCall(
            tool_name="Bash",
            tool_input={},
            content_block={"id": "tc_001", "type": "tool_use"},
        )
        assert tc.content_block["id"] == "tc_001"

    def test_bskg_query_dataclass_exists(self):
        from tests.workflow_harness.lib.transcript_parser import BSKGQuery

        q = BSKGQuery(
            command="uv run alphaswarm query 'functions without access control'",
            query_type="query",
            query_text="functions without access control",
            result_snippet="Found 3 functions...",
            tool_call_index=5,
            cited_in_conclusion=True,
        )
        assert q.query_type == "query"
        assert q.cited_in_conclusion is True

    def test_transcript_parser_get_bskg_queries(self):
        from pathlib import Path
        from tests.workflow_harness.lib.transcript_parser import TranscriptParser

        # Method must exist and return a list (even if empty for empty transcript)
        parser = TranscriptParser(Path("/dev/null"))
        result = parser.get_bskg_queries()
        assert isinstance(result, list)

    def test_transcript_parser_graph_citation_rate(self):
        from pathlib import Path
        from tests.workflow_harness.lib.transcript_parser import TranscriptParser

        parser = TranscriptParser(Path("/dev/null"))
        rate = parser.graph_citation_rate()
        # Empty transcript has no BSKG queries, so rate is None
        assert rate is None

    def test_transcript_parser_records_property(self):
        from pathlib import Path
        from tests.workflow_harness.lib.transcript_parser import TranscriptParser

        parser = TranscriptParser(Path("/dev/null"))
        records = parser.records
        assert isinstance(records, list)
        assert len(records) == 0

    def test_transcript_parser_get_raw_messages(self):
        from pathlib import Path
        from tests.workflow_harness.lib.transcript_parser import TranscriptParser

        parser = TranscriptParser(Path("/dev/null"))
        messages = parser.get_raw_messages()
        assert isinstance(messages, list)


# ---------------------------------------------------------------------------
# Contract: observation-models.md (3.1b-02, 3.1b-04)
# ---------------------------------------------------------------------------


class TestObservationModelContracts:
    """Verify observation model contracts from observation-models.md."""

    def test_agent_observation_importable(self):
        from tests.workflow_harness.lib.output_collector import AgentObservation

        assert AgentObservation is not None

    def test_team_observation_importable(self):
        from tests.workflow_harness.lib.output_collector import TeamObservation

        assert TeamObservation is not None

    def test_team_observation_get_agent_by_type(self):
        from tests.workflow_harness.lib.output_collector import TeamObservation

        team = TeamObservation()
        result = team.get_agent_by_type("attacker")
        assert result is None  # No agents yet, should return None

    def test_collected_output_importable(self):
        from tests.workflow_harness.lib.output_collector import CollectedOutput

        assert CollectedOutput is not None

    def test_output_collector_collect_method(self):
        from pathlib import Path
        from tests.workflow_harness.lib.output_collector import OutputCollector
        from tests.workflow_harness.lib.transcript_parser import TranscriptParser

        collector = OutputCollector()
        parser = TranscriptParser(Path("/dev/null"))
        output = collector.collect(
            scenario_name="test",
            run_id="run-001",
            transcript=parser,
        )
        assert output.scenario_name == "test"

    def test_evaluation_guidance_importable(self):
        from tests.workflow_harness.lib.output_collector import EvaluationGuidance

        guidance = EvaluationGuidance(
            reasoning_questions=["Did the agent use the graph?"],
        )
        assert len(guidance.reasoning_questions) == 1
        assert hasattr(guidance, "to_pydantic_dict")

    def test_evaluation_guidance_to_pydantic_dict(self):
        from tests.workflow_harness.lib.output_collector import EvaluationGuidance

        guidance = EvaluationGuidance(
            reasoning_questions=["Q1", "Q2"],
            hooks_if_failed=["hook1.py"],
        )
        d = guidance.to_pydantic_dict()
        assert d["reasoning_questions"] == ["Q1", "Q2"]
        assert d["hooks_if_failed"] == ["hook1.py"]

    def test_inbox_message_importable(self):
        from tests.workflow_harness.lib.output_collector import InboxMessage

        msg = InboxMessage(
            sender="agent-1",
            recipient="agent-2",
            content="Found reentrancy in withdraw()",
            timestamp="2026-01-15T10:30:00Z",
            message_type="finding",
        )
        assert msg.content == "Found reentrancy in withdraw()"

    def test_captured_message_alias(self):
        from tests.workflow_harness.lib.output_collector import CapturedMessage, InboxMessage

        assert CapturedMessage is InboxMessage


# ---------------------------------------------------------------------------
# Contract: hooks-and-workspace.md (3.1b-03, 3.1b-04)
# ---------------------------------------------------------------------------


class TestHooksAndWorkspaceContracts:
    """Verify hooks and workspace contracts from hooks-and-workspace.md."""

    def test_install_hooks_accepts_hook_configs(self):
        import tempfile
        from pathlib import Path
        from tests.workflow_harness.lib.workspace import WorkspaceManager, HookConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir)
            mgr = WorkspaceManager(ws)
            hooks = [
                HookConfig(
                    event_type="PreToolUse",
                    script_path="python3 .claude/hooks/observe.py",
                    timeout=10,
                ),
            ]
            mgr.install_hooks(ws, hook_configs=hooks)

    def test_jujutsu_create_workspace(self):
        from pathlib import Path
        from tests.workflow_harness.lib.workspace import WorkspaceManager

        mgr = WorkspaceManager(Path("."))
        # Method must exist (will fail at runtime without jj repo)
        assert callable(getattr(mgr, "create_workspace", None))

    def test_jujutsu_forget_workspace(self):
        from pathlib import Path
        from tests.workflow_harness.lib.workspace import WorkspaceManager

        mgr = WorkspaceManager(Path("."))
        assert callable(getattr(mgr, "forget_workspace", None))

    def test_jujutsu_list_workspaces(self):
        from pathlib import Path
        from tests.workflow_harness.lib.workspace import WorkspaceManager

        mgr = WorkspaceManager(Path("."))
        assert callable(getattr(mgr, "list_workspaces", None))

    def test_jujutsu_compat_wrappers_exist(self):
        from pathlib import Path
        from tests.workflow_harness.lib.workspace import WorkspaceManager

        mgr = WorkspaceManager(Path("."))
        assert callable(getattr(mgr, "create_jj_workspace", None))
        assert callable(getattr(mgr, "forget_jj_workspace", None))
        assert callable(getattr(mgr, "rollback_jj_workspace", None))

    def test_workspace_fallback_methods_exist(self):
        from pathlib import Path
        from tests.workflow_harness.lib.workspace import WorkspaceManager

        mgr = WorkspaceManager(Path("."))
        assert callable(getattr(mgr, "create_observation_dir", None))
        assert callable(getattr(mgr, "create_sandbox", None))
        assert callable(getattr(mgr, "restore_from_sandbox", None))


# ---------------------------------------------------------------------------
# Contract: scenario-dsl.md (3.1b-05)
# ---------------------------------------------------------------------------


class TestScenarioDSLContracts:
    """Verify scenario DSL extension contracts from scenario-dsl.md."""

    def test_scenario_config_evaluation_field(self):
        from src.alphaswarm_sol.testing.scenarios.config_schema import ScenarioConfig

        # evaluation field must exist and be optional (None default)
        config = ScenarioConfig(
            name="test",
            category="reentrancy",
            contracts=[],
            prompt_template="test",
        )
        assert config.evaluation is None

    def test_scenario_config_evaluation_guidance_field(self):
        from src.alphaswarm_sol.testing.scenarios.config_schema import ScenarioConfig

        config = ScenarioConfig(
            name="test",
            category="reentrancy",
            contracts=[],
            prompt_template="test",
        )
        assert config.evaluation_guidance is None

    def test_scenario_config_post_run_hooks_field(self):
        from src.alphaswarm_sol.testing.scenarios.config_schema import ScenarioConfig

        config = ScenarioConfig(
            name="test",
            category="reentrancy",
            contracts=[],
            prompt_template="test",
        )
        assert config.post_run_hooks == []

    def test_scenario_config_graders_field(self):
        from src.alphaswarm_sol.testing.scenarios.config_schema import ScenarioConfig

        config = ScenarioConfig(
            name="test",
            category="reentrancy",
            contracts=[],
            prompt_template="test",
        )
        assert config.graders == []

    def test_scenario_config_trials_field(self):
        from src.alphaswarm_sol.testing.scenarios.config_schema import ScenarioConfig

        config = ScenarioConfig(
            name="test",
            category="reentrancy",
            contracts=[],
            prompt_template="test",
        )
        assert config.trials == 1  # default

    def test_modes_field_already_exists(self):
        """Verify modes field exists (already implemented, should pass)."""
        from src.alphaswarm_sol.testing.scenarios.config_schema import ScenarioConfig

        config = ScenarioConfig(
            name="test",
            category="reentrancy",
            contracts=[],
            prompt_template="test",
        )
        assert config.modes == ["single"]

    def test_team_config_field_already_exists(self):
        """Verify team_config field exists (already implemented, should pass)."""
        from src.alphaswarm_sol.testing.scenarios.config_schema import ScenarioConfig

        config = ScenarioConfig(
            name="test",
            category="reentrancy",
            contracts=[],
            prompt_template="test",
        )
        assert config.team_config is not None
        assert "attacker" in config.team_config.roles
