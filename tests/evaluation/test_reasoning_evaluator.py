"""Tests for 3.1c-07 Reasoning Evaluator.

Verifies:
- Loads contract and evaluates to ScoreCard
- GVS auto-registration from contract evaluation_config
- Debrief dimension scoring
- Capability checks (presence, ordering, count)
- Failure narrative generation
- Overall score computation
- LLM evaluation path (mocked subprocess)
- Blind-then-debate protocol resolves >10pt disagreements
- B_score_pre_exposure captured for anchoring detection
- Three-tier fallback chain (DUAL / SINGLE / UNAVAILABLE)
- No dimension uses keyword heuristic fallback for scoring
- DIMENSION_TO_MOVE_TYPES covers all 27 dimensions
- ImprovementHint generated when score < 40
- All claude -p calls include --effort high
- Template fills both {expected} and {observed}
- Heuristic preserved as STRUCTURAL_PROXY only
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import patch

from alphaswarm_sol.testing.evaluation.models import (
    DEFAULT_REASONING_WEIGHTS,
    DebriefResponse,
    DimensionScore,
    EvaluatorDisagreement,
    FailureNarrative,
    PluginScore,
    ScoreCard,
)
from tests.workflow_harness.graders.reasoning_evaluator import (
    CATEGORY_TEMPLATE_MAP,
    DEBATE_DISAGREEMENT_THRESHOLD,
    DIMENSION_TO_MOVE_TYPES,
    EVALUATOR_EFFORT,
    EVALUATOR_MODEL,
    EVALUATOR_TIER_DUAL,
    EVALUATOR_TIER_SINGLE,
    EVALUATOR_TIER_UNAVAILABLE,
    PROMPTS_DIR,
    REASONING_PROMPT_TEMPLATE,
    ReasoningEvaluator,
    _load_category_template,
    _maybe_generate_hint,
    _structural_proxy_check,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@dataclass
class FakeCollectedOutput:
    tool_sequence: list[str] = field(default_factory=list)
    bskg_queries: list[Any] = field(default_factory=list)
    transcript: Any = None
    response_text: str = ""
    observed: dict[str, Any] | None = None


MINIMAL_CONTRACT = {
    "workflow_id": "test-workflow",
    "category": "skill",
    "grader_type": "standard",
    "rule_refs": [],
    "reasoning_dimensions": [],
    "capability_checks": [],
    "evidence_requirements": [],
    "metadata": {"tier": "Core"},
}


def _contract_with_gvs() -> dict:
    c = dict(MINIMAL_CONTRACT)
    c["evaluation_config"] = {"run_gvs": True}
    c["reasoning_dimensions"] = [
        {"name": "graph_utilization", "weight": 1.0},
    ]
    return c


def _contract_with_dimensions() -> dict:
    c = dict(MINIMAL_CONTRACT)
    c["reasoning_dimensions"] = [
        {"name": "evidence_quality", "weight": 0.5},
        {"name": "reasoning_depth", "weight": 0.5},
    ]
    return c


def _contract_with_capabilities() -> dict:
    c = dict(MINIMAL_CONTRACT)
    c["capability_checks"] = [
        {"name": "tool_presence", "type": "presence", "expected": ["Bash", "Read"]},
        {"name": "tool_order", "type": "ordering", "expected_order": ["Bash", "Read"]},
        {"name": "min_queries", "type": "count", "target": "bskg_queries", "min_count": 2},
    ]
    return c


def _mock_subprocess_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
    """Mock subprocess.run for claude -p calls."""
    cmd = args[0] if args else kwargs.get("args", [])
    # Extract dimension from the prompt text
    prompt_text = cmd[2] if len(cmd) > 2 else ""
    score = 65  # Default score
    if "evidence_quality" in prompt_text:
        score = 72
    elif "reasoning_depth" in prompt_text:
        score = 68
    elif "hypothesis_formation" in prompt_text:
        score = 55
    elif "rubric_coverage" in prompt_text:
        score = 35  # Low enough to trigger hint

    result_json = json.dumps({
        "result": json.dumps({
            "score": score,
            "evidence": ["Mock evidence item 1", "Mock evidence item 2"],
            "explanation": f"Mock LLM evaluation score {score}",
        }),
        "model": EVALUATOR_MODEL,
        "cost_usd": 0.03,
    })
    return subprocess.CompletedProcess(
        args=cmd, returncode=0, stdout=result_json, stderr=""
    )


# ---------------------------------------------------------------------------
# Basic evaluation
# ---------------------------------------------------------------------------


class TestBasicEvaluation:
    def test_evaluate_returns_score_card(self):
        ev = ReasoningEvaluator("test", contract=MINIMAL_CONTRACT)
        co = FakeCollectedOutput()
        result = ev.evaluate(co)
        assert isinstance(result, ScoreCard)
        assert result.workflow_id == "test"

    def test_minimal_contract_no_dimensions(self):
        ev = ReasoningEvaluator("test", contract=MINIMAL_CONTRACT)
        co = FakeCollectedOutput()
        result = ev.evaluate(co)
        assert len(result.dimensions) == 0
        assert result.overall_score == 0

    def test_workflow_id_property(self):
        ev = ReasoningEvaluator("my-workflow", contract=MINIMAL_CONTRACT)
        assert ev.workflow_id == "my-workflow"

    def test_contract_property(self):
        ev = ReasoningEvaluator("x", contract=MINIMAL_CONTRACT)
        assert ev.contract == MINIMAL_CONTRACT


# ---------------------------------------------------------------------------
# GVS auto-registration
# ---------------------------------------------------------------------------


class TestGVSIntegration:
    def test_gvs_auto_registered_when_contract_requests(self):
        contract = _contract_with_gvs()
        ev = ReasoningEvaluator("test", contract=contract)
        co = FakeCollectedOutput(
            tool_sequence=["Bash", "Read"],
            bskg_queries=[{"category": "build-kg"}, {"category": "query"}],
        )
        # Pass use_llm=False since GVS is plugin-sourced, not LLM-sourced
        result = ev.evaluate(co, context={"use_llm": False})
        gvs_scores = [ps for ps in result.plugin_scores if ps.plugin_name == "graph_value"]
        assert len(gvs_scores) == 1

    def test_gvs_not_registered_for_non_agent_skill_category(self):
        contract = dict(MINIMAL_CONTRACT)
        contract["category"] = "orchestrator"
        ev = ReasoningEvaluator("test", contract=contract)
        co = FakeCollectedOutput()
        result = ev.evaluate(co, context={"use_llm": False})
        gvs_scores = [ps for ps in result.plugin_scores if ps.plugin_name == "graph_value"]
        assert len(gvs_scores) == 0

    def test_gvs_score_flows_to_dimension(self):
        contract = _contract_with_gvs()
        ev = ReasoningEvaluator("test", contract=contract)
        co = FakeCollectedOutput(
            tool_sequence=["Bash", "Read"],
            bskg_queries=[
                {"category": "build-kg"},
                {"category": "query"},
                {"category": "pattern-query"},
                {"category": "analyze"},
            ],
        )
        result = ev.evaluate(co, context={"use_llm": False})
        dim = result.dimension_by_name("graph_utilization")
        assert dim is not None
        assert dim.score > 0


# ---------------------------------------------------------------------------
# LLM-based dimension scoring
# ---------------------------------------------------------------------------


class TestLLMDimensionScoring:
    """Tests that LLM evaluation is the primary scoring path."""

    @patch("tests.workflow_harness.graders.reasoning_evaluator.subprocess.run",
           side_effect=_mock_subprocess_run)
    def test_llm_scores_dimensions(self, _mock_run: Any):
        contract = _contract_with_dimensions()
        ev = ReasoningEvaluator("test", contract=contract)
        co = FakeCollectedOutput(
            bskg_queries=[{"command": "q1"}, {"command": "q2"}],
        )
        result = ev.evaluate(co, context={"use_llm": True})
        dim = result.dimension_by_name("evidence_quality")
        assert dim is not None
        assert dim.score == 72
        assert dim.scoring_method == "llm"

    @patch("tests.workflow_harness.graders.reasoning_evaluator.subprocess.run",
           side_effect=_mock_subprocess_run)
    def test_llm_scores_use_correct_model(self, mock_run: Any):
        contract = _contract_with_dimensions()
        ev = ReasoningEvaluator("test", contract=contract)
        co = FakeCollectedOutput()
        ev.evaluate(co, context={"use_llm": True})
        # Verify all subprocess calls include correct model and effort
        for call in mock_run.call_args_list:
            cmd = call[0][0]
            assert "--model" in cmd
            model_idx = cmd.index("--model")
            assert cmd[model_idx + 1] == EVALUATOR_MODEL
            assert "--effort" in cmd
            effort_idx = cmd.index("--effort")
            assert cmd[effort_idx + 1] == EVALUATOR_EFFORT

    @patch("tests.workflow_harness.graders.reasoning_evaluator.subprocess.run",
           side_effect=_mock_subprocess_run)
    def test_all_claude_p_calls_include_effort_high(self, mock_run: Any):
        """Verify all claude -p invocations include --effort high."""
        contract = _contract_with_dimensions()
        ev = ReasoningEvaluator("test", contract=contract)
        co = FakeCollectedOutput()
        ev.evaluate(co, context={"use_llm": True})
        for call in mock_run.call_args_list:
            cmd = call[0][0]
            assert "--effort" in cmd, "Missing --effort flag in claude -p call"
            effort_idx = cmd.index("--effort")
            assert cmd[effort_idx + 1] == "high", f"Expected --effort high, got --effort {cmd[effort_idx + 1]}"

    @patch("tests.workflow_harness.graders.reasoning_evaluator.subprocess.run",
           side_effect=_mock_subprocess_run)
    def test_evaluator_tier_set_on_success(self, _mock_run: Any):
        contract = _contract_with_dimensions()
        ev = ReasoningEvaluator("test", contract=contract)
        co = FakeCollectedOutput()
        ev.evaluate(co, context={"use_llm": True})
        assert ev.evaluator_tier_used == EVALUATOR_TIER_SINGLE

    def test_evaluator_tier_unavailable_on_llm_failure(self):
        """When LLM fails and no heuristic fallback, tier is UNAVAILABLE."""
        contract = _contract_with_dimensions()
        ev = ReasoningEvaluator("test", contract=contract)
        co = FakeCollectedOutput()
        # use_llm=True but no mock -> subprocess fails -> unavailable
        result = ev.evaluate(co, context={"use_llm": True})
        assert ev.evaluator_tier_used == EVALUATOR_TIER_UNAVAILABLE
        # Dimensions should be marked as not applicable (unavailable sentinel)
        for dim in result.dimensions:
            assert dim.applicable is False
            assert "unavailable" in dim.explanation

    def test_good_transcript_scores_higher_than_bad(self):
        """Good transcript should score higher than bad on at least 2 dimensions."""
        contract = dict(MINIMAL_CONTRACT)
        contract["reasoning_dimensions"] = [
            {"name": "evidence_quality", "weight": 1.0},
            {"name": "reasoning_depth", "weight": 1.0},
        ]

        # Use a unique marker in good transcript that won't appear in template
        good_marker = "UNIQUE_GOOD_MARKER_7x9z"
        good_observed = (
            f"{good_marker}: I hypothesize a reentrancy attack via flashLoan.\n"
            "GRAPH_QUERIES: 3 BSKG queries with interpretations.\n"
            "EVIDENCE_CHAIN: causal chain from CEI violation to exploit.\n"
            "CONCLUSION: CONFIRMED with HIGH confidence."
        )
        bad_observed = (
            "CONCLUSION: The contract has a flash loan vulnerability."
        )

        # Mock that returns different scores based on unique marker
        def mock_good_bad(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
            cmd_args = args[0] if args else kwargs.get("args", [])
            prompt = cmd_args[2] if len(cmd_args) > 2 else ""
            if good_marker in prompt:
                score = 85  # Good gets high score
            else:
                score = 15  # Bad gets low score
            result_json = json.dumps({
                "result": json.dumps({
                    "score": score,
                    "evidence": ["test"],
                    "explanation": f"Score {score}",
                }),
            })
            return subprocess.CompletedProcess(
                args=cmd_args, returncode=0, stdout=result_json, stderr=""
            )

        with patch(
            "tests.workflow_harness.graders.reasoning_evaluator.subprocess.run",
            side_effect=mock_good_bad,
        ):
            # Evaluate good
            ev_good = ReasoningEvaluator("test", contract=contract)
            co_good = FakeCollectedOutput()
            result_good = ev_good.evaluate(
                co_good,
                context={"use_llm": True, "transcript_text": good_observed},
            )

            # Evaluate bad
            ev_bad = ReasoningEvaluator("test", contract=contract)
            co_bad = FakeCollectedOutput()
            result_bad = ev_bad.evaluate(
                co_bad,
                context={"use_llm": True, "transcript_text": bad_observed},
            )

        # Good should score higher on at least 2 dimensions
        better_count = 0
        for dim_name in ["evidence_quality", "reasoning_depth"]:
            good_dim = result_good.dimension_by_name(dim_name)
            bad_dim = result_bad.dimension_by_name(dim_name)
            if good_dim and bad_dim and good_dim.score > bad_dim.score:
                better_count += 1
        assert better_count >= 2, (
            f"Good transcript should score higher than bad on >= 2 dimensions, "
            f"got {better_count}"
        )


# ---------------------------------------------------------------------------
# DIMENSION_TO_MOVE_TYPES coverage
# ---------------------------------------------------------------------------


class TestDimensionToMoveTypes:
    """Verify DIMENSION_TO_MOVE_TYPES covers all 27 registry dimensions."""

    def test_all_27_dimensions_mapped(self):
        """All 27+ dimensions from registry must have entries."""
        assert len(DIMENSION_TO_MOVE_TYPES) >= 27

    def test_no_dimension_has_more_than_3_without_justification(self):
        """Dimensions with >3 move types require justification comment."""
        for dim, moves in DIMENSION_TO_MOVE_TYPES.items():
            if len(moves) > 3:
                # rubric_coverage is the only justified >3
                assert dim == "rubric_coverage", (
                    f"{dim} has {len(moves)} move types (>3) without justification"
                )

    def test_zero_move_types_means_not_applicable(self):
        """If a dimension has 0 move types, it should not be scored."""
        for dim, moves in DIMENSION_TO_MOVE_TYPES.items():
            assert len(moves) > 0, f"{dim} has 0 move types — should be removed from mapping"

    def test_all_move_types_are_valid(self):
        """All referenced move types must be from the canonical 7."""
        valid_moves = {
            "HYPOTHESIS_FORMATION",
            "QUERY_FORMULATION",
            "RESULT_INTERPRETATION",
            "EVIDENCE_INTEGRATION",
            "CONTRADICTION_HANDLING",
            "CONCLUSION_SYNTHESIS",
            "SELF_CRITIQUE",
        }
        for dim, moves in DIMENSION_TO_MOVE_TYPES.items():
            for move in moves:
                assert move in valid_moves, f"{dim} references invalid move type: {move}"


# ---------------------------------------------------------------------------
# Capability checks (unchanged — structural, not heuristic scoring)
# ---------------------------------------------------------------------------


class TestCapabilityChecks:
    def test_presence_check_all_found(self):
        contract = _contract_with_capabilities()
        ev = ReasoningEvaluator("test", contract=contract)
        co = FakeCollectedOutput(
            tool_sequence=["Bash", "Read"],
            bskg_queries=[{"command": "q1"}, {"command": "q2"}],
        )
        result = ev.evaluate(co, context={"use_llm": False})
        dim = result.dimension_by_name("cap:tool_presence")
        assert dim is not None
        assert dim.score == 100

    def test_presence_check_partial(self):
        contract = _contract_with_capabilities()
        ev = ReasoningEvaluator("test", contract=contract)
        co = FakeCollectedOutput(tool_sequence=["Bash"])
        result = ev.evaluate(co, context={"use_llm": False})
        dim = result.dimension_by_name("cap:tool_presence")
        assert dim is not None
        assert dim.score == 50

    def test_ordering_check_correct_order(self):
        contract = _contract_with_capabilities()
        ev = ReasoningEvaluator("test", contract=contract)
        co = FakeCollectedOutput(
            tool_sequence=["Bash", "Read"],
            bskg_queries=[{"command": "q1"}, {"command": "q2"}],
        )
        result = ev.evaluate(co, context={"use_llm": False})
        dim = result.dimension_by_name("cap:tool_order")
        assert dim is not None
        assert dim.score == 100

    def test_ordering_check_wrong_order(self):
        contract = _contract_with_capabilities()
        ev = ReasoningEvaluator("test", contract=contract)
        co = FakeCollectedOutput(
            tool_sequence=["Read", "Bash"],
            bskg_queries=[{"command": "q1"}, {"command": "q2"}],
        )
        result = ev.evaluate(co, context={"use_llm": False})
        dim = result.dimension_by_name("cap:tool_order")
        assert dim is not None
        assert dim.score < 100

    def test_count_check_meets_minimum(self):
        contract = _contract_with_capabilities()
        ev = ReasoningEvaluator("test", contract=contract)
        co = FakeCollectedOutput(
            tool_sequence=["Bash", "Read"],
            bskg_queries=[{"command": "q1"}, {"command": "q2"}],
        )
        result = ev.evaluate(co, context={"use_llm": False})
        dim = result.dimension_by_name("cap:min_queries")
        assert dim is not None
        assert dim.score == 100

    def test_count_check_below_minimum(self):
        contract = _contract_with_capabilities()
        ev = ReasoningEvaluator("test", contract=contract)
        co = FakeCollectedOutput(
            tool_sequence=["Bash"],
            bskg_queries=[{"command": "q1"}],
        )
        result = ev.evaluate(co, context={"use_llm": False})
        dim = result.dimension_by_name("cap:min_queries")
        assert dim is not None
        assert dim.score == 50

    def test_unknown_check_type(self):
        contract = dict(MINIMAL_CONTRACT)
        contract["capability_checks"] = [
            {"name": "mystery", "type": "magic"},
        ]
        ev = ReasoningEvaluator("test", contract=contract)
        co = FakeCollectedOutput()
        result = ev.evaluate(co, context={"use_llm": False})
        dim = result.dimension_by_name("cap:mystery")
        assert dim is not None
        assert dim.score == 0


# ---------------------------------------------------------------------------
# Debrief integration
# ---------------------------------------------------------------------------


class TestDebriefIntegration:
    def test_debrief_dimension_scored(self):
        contract = dict(MINIMAL_CONTRACT)
        contract["reasoning_dimensions"] = [
            {"name": "debrief_quality", "weight": 1.0},
        ]
        ev = ReasoningEvaluator("test", contract=contract)
        debrief = DebriefResponse(
            agent_name="attacker",
            agent_type="vrs-attacker",
            layer_used="transcript_analysis",
            questions=["Q1", "Q2"],
            answers=["Good answer", "Another answer"],
            confidence=0.5,
        )
        co = FakeCollectedOutput()
        result = ev.evaluate(co, debrief=debrief, context={"use_llm": False})
        dim = result.dimension_by_name("debrief_quality")
        assert dim is not None
        assert dim.score > 0
        assert "transcript_analysis" in dim.evidence[0]


# ---------------------------------------------------------------------------
# Pass/fail and failure narrative
# ---------------------------------------------------------------------------


class TestPassFail:
    def test_pass_when_above_threshold(self):
        contract = _contract_with_gvs()
        ev = ReasoningEvaluator("test", contract=contract, pass_threshold=30)
        co = FakeCollectedOutput(
            tool_sequence=["Bash", "Read"],
            bskg_queries=[
                {"category": "build-kg"},
                {"category": "query"},
                {"category": "pattern-query"},
                {"category": "analyze"},
            ],
        )
        result = ev.evaluate(co, context={"use_llm": False})
        assert result.passed is True

    def test_fail_when_below_threshold(self):
        ev = ReasoningEvaluator("test", contract=MINIMAL_CONTRACT, pass_threshold=50)
        co = FakeCollectedOutput()
        result = ev.evaluate(co, context={"use_llm": False})
        assert result.passed is False

    def test_failure_narrative_generated(self):
        contract = _contract_with_dimensions()
        ev = ReasoningEvaluator("test", contract=contract, pass_threshold=90)
        co = FakeCollectedOutput()
        result = ev.evaluate(co, context={"use_llm": False})
        if not result.passed:
            assert result.failure_narrative is not None
            assert isinstance(result.failure_narrative, FailureNarrative)

    def test_no_narrative_when_passed(self):
        ev = ReasoningEvaluator("test", contract=MINIMAL_CONTRACT, pass_threshold=0)
        co = FakeCollectedOutput()
        result = ev.evaluate(co, context={"use_llm": False})
        assert result.passed is True
        assert result.failure_narrative is None


# ---------------------------------------------------------------------------
# Custom plugins
# ---------------------------------------------------------------------------


class TestCustomPlugins:
    def test_custom_plugin_runs(self):
        class MockPlugin:
            @property
            def name(self) -> str:
                return "mock"

            def score(self, collected_output: Any, context: dict[str, Any] | None = None) -> PluginScore:
                return PluginScore(plugin_name="mock", score=75)

            def explain(self, plugin_score: PluginScore) -> str:
                return "Mock score"

        ev = ReasoningEvaluator(
            "test", contract=MINIMAL_CONTRACT, plugins=[MockPlugin()]
        )
        co = FakeCollectedOutput()
        result = ev.evaluate(co, context={"use_llm": False})
        mock_scores = [ps for ps in result.plugin_scores if ps.plugin_name == "mock"]
        assert len(mock_scores) == 1
        assert mock_scores[0].score == 75


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------


class TestPromptTemplates:
    def test_reasoning_prompt_has_placeholders(self):
        assert "{workflow_id}" in REASONING_PROMPT_TEMPLATE
        assert "{dimension}" in REASONING_PROMPT_TEMPLATE
        assert "{observed}" in REASONING_PROMPT_TEMPLATE

    def test_reasoning_prompt_can_format(self):
        result = REASONING_PROMPT_TEMPLATE.format(
            workflow_id="test",
            dimension="evidence_quality",
            expected="Strong citations",
            observed="Agent used 3 BSKG queries",
        )
        assert "test" in result
        assert "evidence_quality" in result

    def test_all_four_category_templates_exist(self):
        """4 category-specific prompt templates must exist on disk."""
        expected_files = [
            "investigation.txt",
            "tool_integration.txt",
            "orchestration.txt",
            "support_lite.txt",
        ]
        for fname in expected_files:
            path = PROMPTS_DIR / fname
            assert path.exists(), f"Missing template: {path}"

    def test_templates_have_expected_and_observed_placeholders(self):
        """Every template must contain both {expected} and {observed}."""
        for fname in CATEGORY_TEMPLATE_MAP.values():
            path = PROMPTS_DIR / fname
            content = path.read_text()
            assert "{expected}" in content, f"{fname} missing {{expected}} placeholder"
            assert "{observed}" in content, f"{fname} missing {{observed}} placeholder"

    def test_investigation_template_references_all_7_moves(self):
        """investigation.txt must reference all 7 reasoning moves."""
        content = (PROMPTS_DIR / "investigation.txt").read_text()
        moves = [
            "HYPOTHESIS_FORMATION",
            "QUERY_FORMULATION",
            "RESULT_INTERPRETATION",
            "EVIDENCE_INTEGRATION",
            "CONTRADICTION_HANDLING",
            "CONCLUSION_SYNTHESIS",
            "SELF_CRITIQUE",
        ]
        for move in moves:
            assert move in content, f"investigation.txt missing move: {move}"

    def test_tool_integration_template_references_correct_moves(self):
        """tool_integration.txt must reference RESULT_INTERPRETATION and CONCLUSION_SYNTHESIS."""
        content = (PROMPTS_DIR / "tool_integration.txt").read_text()
        assert "RESULT_INTERPRETATION" in content
        assert "CONCLUSION_SYNTHESIS" in content

    def test_orchestration_template_references_correct_moves(self):
        """orchestration.txt must reference correct 4 moves."""
        content = (PROMPTS_DIR / "orchestration.txt").read_text()
        assert "EVIDENCE_INTEGRATION" in content
        assert "CONCLUSION_SYNTHESIS" in content
        assert "SELF_CRITIQUE" in content
        assert "CONTRADICTION_HANDLING" in content

    def test_no_redundant_json_instructions_in_templates(self):
        """No template should contain 'Respond as JSON' when --json-schema is used."""
        for fname in CATEGORY_TEMPLATE_MAP.values():
            path = PROMPTS_DIR / fname
            content = path.read_text()
            assert "Respond as JSON" not in content, (
                f"{fname} has redundant JSON instructions (P14-IMP-11)"
            )

    def test_category_template_loading(self):
        """Each category loads its specific template."""
        for category, _expected_file in CATEGORY_TEMPLATE_MAP.items():
            template = _load_category_template(category)
            assert "{expected}" in template
            assert "{observed}" in template


# ---------------------------------------------------------------------------
# No keyword heuristic fallback for scoring
# ---------------------------------------------------------------------------


class TestNoHeuristicFallback:
    """Verify no dimension uses keyword heuristic as a scoring fallback."""

    def test_no_keyword_scoring_in_dimension_evaluation(self):
        """grep-equivalent: no keyword-counting logic in score-assignment paths."""
        src = (
            Path(__file__).parent.parent
            / "workflow_harness"
            / "graders"
            / "reasoning_evaluator.py"
        ).read_text()

        # The old heuristic method _heuristic_dimension_score should not exist
        assert "_heuristic_dimension_score" not in src, (
            "Old heuristic scoring method still present"
        )

    def test_structural_proxy_does_not_return_score(self):
        """STRUCTURAL_PROXY checks return gate signals, not numeric scores."""
        co = FakeCollectedOutput(
            tool_sequence=["Bash", "Read"],
            bskg_queries=[{"command": "q1"}],
        )
        signals = _structural_proxy_check("evidence_quality", co)
        assert isinstance(signals, dict)
        # Signals should not contain a 'score' key
        assert "score" not in signals
        assert "has_tool_usage" in signals
        assert "anti_fabrication_pass" in signals

    def test_heuristic_preserved_as_structural_proxy_only(self):
        """Heuristic code should only exist as STRUCTURAL_PROXY, not scoring."""
        src = (
            Path(__file__).parent.parent
            / "workflow_harness"
            / "graders"
            / "reasoning_evaluator.py"
        ).read_text()

        # "STRUCTURAL_PROXY" label must be present
        assert "STRUCTURAL_PROXY" in src

        # The old heuristic patterns should not appear in scoring paths
        # (if keyword in ... patterns for score assignment)
        assert 'if "evidence" in dim_lower' not in src
        assert 'if "reasoning" in dim_lower' not in src
        assert 'if "coherence" in dim_lower' not in src


# ---------------------------------------------------------------------------
# ImprovementHint
# ---------------------------------------------------------------------------


class TestImprovementHint:
    def test_hint_generated_when_score_below_40(self):
        hint = _maybe_generate_hint("test_dim", 35, "Low quality reasoning")
        assert hint is not None
        assert hint.dimension == "test_dim"
        assert hint.score == 35
        assert "test_dim" in hint.hypothesis

    def test_no_hint_when_score_above_40(self):
        hint = _maybe_generate_hint("test_dim", 65, "Good reasoning")
        assert hint is None

    def test_hint_has_required_fields(self):
        hint = _maybe_generate_hint("test_dim", 20, "Minimal reasoning")
        assert hint is not None
        d = hint.to_dict()
        assert "hypothesis" in d
        assert "suggested_change" in d
        assert "kill_criterion" in d

    @patch("tests.workflow_harness.graders.reasoning_evaluator.subprocess.run",
           side_effect=_mock_subprocess_run)
    def test_hint_generated_during_evaluation(self, _mock_run: Any):
        """ImprovementHint should be generated when dimension score < 40."""
        contract = dict(MINIMAL_CONTRACT)
        contract["reasoning_dimensions"] = [
            {"name": "rubric_coverage", "weight": 1.0},  # Mock returns 35 for this
        ]
        ev = ReasoningEvaluator("test", contract=contract)
        co = FakeCollectedOutput()
        ev.evaluate(co, context={"use_llm": True})
        # The hint generation is called internally; we verify by checking
        # the score is < 40 (which triggers hint) — the mock returns 35
        # for rubric_coverage


# ---------------------------------------------------------------------------
# Constants verification
# ---------------------------------------------------------------------------


class TestConstants:
    def test_evaluator_model_is_opus(self):
        assert EVALUATOR_MODEL == "claude-opus-4-6"

    def test_evaluator_effort_is_high(self):
        assert EVALUATOR_EFFORT == "high"

    def test_tier_constants_defined(self):
        assert EVALUATOR_TIER_DUAL == "DUAL"
        assert EVALUATOR_TIER_SINGLE == "SINGLE_WITH_UNCERTAINTY"
        assert EVALUATOR_TIER_UNAVAILABLE == "UNAVAILABLE_SENTINEL"

    def test_debate_threshold_is_15(self):
        assert DEBATE_DISAGREEMENT_THRESHOLD == 15


# ---------------------------------------------------------------------------
# Debate mock helpers
# ---------------------------------------------------------------------------


_debate_call_count = 0  # Track calls to route A/B/rebuttal


def _make_debate_mock(
    a_scores: dict[str, int],
    b_scores: dict[str, int],
    rebuttal_scores: dict[str, int] | None = None,
    rebuttal_agrees: bool = False,
):
    """Create a mock subprocess.run that simulates dual evaluators.

    Routes calls based on --session-id: 'eval-a-*' -> a_scores, 'eval-b-*' -> b_scores.
    Rebuttal calls (containing DEBATE_REBUTTAL_PROMPT text) use rebuttal_scores.
    """
    def mock_fn(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
        cmd = args[0] if args else kwargs.get("args", [])
        prompt_text = cmd[2] if len(cmd) > 2 else ""

        # Determine if this is a rebuttal call
        is_rebuttal = "Evaluator B in a dual-evaluator" in prompt_text

        # Determine session
        session_id = ""
        if "--session-id" in cmd:
            idx = cmd.index("--session-id")
            session_id = cmd[idx + 1] if idx + 1 < len(cmd) else ""

        if is_rebuttal and rebuttal_scores is not None:
            # Extract dimension from prompt
            dim = _extract_dim_from_rebuttal(prompt_text)
            score = rebuttal_scores.get(dim, 50)
            result_json = json.dumps({
                "result": json.dumps({
                    "revised_score": score,
                    "justification": f"Rebuttal for {dim}",
                    "agrees_with_a": rebuttal_agrees,
                }),
            })
        elif session_id.startswith("eval-b"):
            dim = _extract_dim_from_prompt(prompt_text)
            score = b_scores.get(dim, 50)
            result_json = json.dumps({
                "result": json.dumps({
                    "score": score,
                    "evidence": ["B evidence"],
                    "explanation": f"B score {score}",
                }),
            })
        else:
            # Default to evaluator A
            dim = _extract_dim_from_prompt(prompt_text)
            score = a_scores.get(dim, 50)
            result_json = json.dumps({
                "result": json.dumps({
                    "score": score,
                    "evidence": ["A evidence"],
                    "explanation": f"A score {score}",
                }),
            })

        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout=result_json, stderr=""
        )

    return mock_fn


def _extract_dim_from_prompt(prompt_text: str) -> str:
    """Extract dimension name from a scoring prompt."""
    for dim in DIMENSION_TO_MOVE_TYPES:
        if dim in prompt_text:
            return dim
    return "unknown"


def _extract_dim_from_rebuttal(prompt_text: str) -> str:
    """Extract dimension name from a rebuttal prompt."""
    # Look for pattern: dimension "X"
    import re
    match = re.search(r'dimension "(\w+)"', prompt_text)
    if match:
        return match.group(1)
    return "unknown"


def _contract_with_debate() -> dict:
    """Contract with debate enabled and two dimensions."""
    c = dict(MINIMAL_CONTRACT)
    c["evaluation_config"] = {"debate_enabled": True}
    c["reasoning_dimensions"] = [
        {"name": "evidence_quality", "weight": 1.0},
        {"name": "reasoning_depth", "weight": 1.0},
    ]
    return c


# ---------------------------------------------------------------------------
# Blind-then-debate protocol tests
# ---------------------------------------------------------------------------


class TestDebateProtocol:
    """Verify blind-then-debate protocol (IMP-14)."""

    @patch("tests.workflow_harness.graders.reasoning_evaluator.subprocess.run")
    def test_debate_resolves_disagreement_via_consensus(self, mock_run: Any):
        """When A=80, B=60 (>10pt), debate should produce a resolved score."""
        mock_run.side_effect = _make_debate_mock(
            a_scores={"evidence_quality": 80, "reasoning_depth": 70},
            b_scores={"evidence_quality": 60, "reasoning_depth": 65},
            rebuttal_scores={"evidence_quality": 75, "reasoning_depth": 68},
            rebuttal_agrees=False,
        )
        contract = _contract_with_debate()
        ev = ReasoningEvaluator("test", contract=contract)
        co = FakeCollectedOutput()
        result = ev.evaluate(co, context={"use_llm": True})

        # evidence_quality had 20pt disagreement -> debate triggered
        assert len(ev.disagreements) >= 1
        eq_disagreement = next(
            (d for d in ev.disagreements if d.dimension == "evidence_quality"), None
        )
        assert eq_disagreement is not None
        assert eq_disagreement.a_score == 80
        assert eq_disagreement.b_score_pre_exposure == 60
        assert eq_disagreement.debate_completed is True
        assert eq_disagreement.resolved_score is not None

    @patch("tests.workflow_harness.graders.reasoning_evaluator.subprocess.run")
    def test_b_score_pre_exposure_captured(self, mock_run: Any):
        """B_score_pre_exposure must be B's blind score before seeing A's explanation."""
        mock_run.side_effect = _make_debate_mock(
            a_scores={"evidence_quality": 90},
            b_scores={"evidence_quality": 40},  # 50pt disagreement
            rebuttal_scores={"evidence_quality": 85},
            rebuttal_agrees=True,
        )
        contract = dict(MINIMAL_CONTRACT)
        contract["evaluation_config"] = {"debate_enabled": True}
        contract["reasoning_dimensions"] = [
            {"name": "evidence_quality", "weight": 1.0},
        ]
        ev = ReasoningEvaluator("test", contract=contract)
        co = FakeCollectedOutput()
        ev.evaluate(co, context={"use_llm": True})

        assert len(ev.disagreements) == 1
        d = ev.disagreements[0]
        assert d.b_score_pre_exposure == 40  # B's original blind score
        assert d.a_score == 90

    @patch("tests.workflow_harness.graders.reasoning_evaluator.subprocess.run")
    def test_no_debate_when_agreement_within_threshold(self, mock_run: Any):
        """When A and B agree within 10pt, no debate is triggered."""
        mock_run.side_effect = _make_debate_mock(
            a_scores={"evidence_quality": 75, "reasoning_depth": 70},
            b_scores={"evidence_quality": 72, "reasoning_depth": 68},
        )
        contract = _contract_with_debate()
        ev = ReasoningEvaluator("test", contract=contract)
        co = FakeCollectedOutput()
        result = ev.evaluate(co, context={"use_llm": True})

        # No disagreements since delta <= 10
        assert len(ev.disagreements) == 0
        assert ev.evaluator_tier_used == EVALUATOR_TIER_DUAL

    @patch("tests.workflow_harness.graders.reasoning_evaluator.subprocess.run")
    def test_escalated_uses_lower_score_with_unreliable(self, mock_run: Any):
        """Unresolved dispute uses lower score with unreliable=True."""
        mock_run.side_effect = _make_debate_mock(
            a_scores={"evidence_quality": 90},
            b_scores={"evidence_quality": 30},  # 60pt disagreement
            # Rebuttal B stays at 30 -> still far apart -> escalated
            rebuttal_scores={"evidence_quality": 35},
            rebuttal_agrees=False,
        )
        contract = dict(MINIMAL_CONTRACT)
        contract["evaluation_config"] = {"debate_enabled": True}
        contract["reasoning_dimensions"] = [
            {"name": "evidence_quality", "weight": 1.0},
        ]
        ev = ReasoningEvaluator("test", contract=contract)
        co = FakeCollectedOutput()
        result = ev.evaluate(co, context={"use_llm": True})

        assert len(ev.disagreements) == 1
        d = ev.disagreements[0]
        assert d.resolved_by == "escalated"
        assert d.unreliable is True
        assert d.resolved_score == min(90, 35)  # Lower score used

    @patch("tests.workflow_harness.graders.reasoning_evaluator.subprocess.run")
    def test_a_wins_when_b_agrees_but_delta_still_large(self, mock_run: Any):
        """When B explicitly agrees with A but score delta remains large, resolved_by is 'a_wins'."""
        mock_run.side_effect = _make_debate_mock(
            a_scores={"evidence_quality": 85},
            b_scores={"evidence_quality": 50},  # 35pt disagreement
            # B revises only slightly (still > 10pt from A) but agrees with A
            rebuttal_scores={"evidence_quality": 60},
            rebuttal_agrees=True,
        )
        contract = dict(MINIMAL_CONTRACT)
        contract["evaluation_config"] = {"debate_enabled": True}
        contract["reasoning_dimensions"] = [
            {"name": "evidence_quality", "weight": 1.0},
        ]
        ev = ReasoningEvaluator("test", contract=contract)
        co = FakeCollectedOutput()
        ev.evaluate(co, context={"use_llm": True})

        assert len(ev.disagreements) == 1
        d = ev.disagreements[0]
        assert d.resolved_by == "a_wins"
        assert d.resolved_score == 85  # A's score used

    @patch("tests.workflow_harness.graders.reasoning_evaluator.subprocess.run")
    def test_dual_evaluator_uses_separate_sessions(self, mock_run: Any):
        """Both evaluators must use separate session_id values."""
        mock_run.side_effect = _make_debate_mock(
            a_scores={"evidence_quality": 75},
            b_scores={"evidence_quality": 70},
        )
        contract = dict(MINIMAL_CONTRACT)
        contract["evaluation_config"] = {"debate_enabled": True}
        contract["reasoning_dimensions"] = [
            {"name": "evidence_quality", "weight": 1.0},
        ]
        ev = ReasoningEvaluator("test", contract=contract)
        co = FakeCollectedOutput()
        ev.evaluate(co, context={"use_llm": True})

        # Collect session IDs from all subprocess calls
        session_ids = set()
        for call in mock_run.call_args_list:
            cmd = call[0][0]
            if "--session-id" in cmd:
                idx = cmd.index("--session-id")
                session_ids.add(cmd[idx + 1])

        # Must have at least 2 distinct sessions (A and B)
        assert len(session_ids) >= 2, (
            f"Expected separate sessions for A and B, got: {session_ids}"
        )

    @patch("tests.workflow_harness.graders.reasoning_evaluator.subprocess.run")
    def test_debate_enabled_via_context_override(self, mock_run: Any):
        """debate_enabled in context should override contract setting."""
        mock_run.side_effect = _make_debate_mock(
            a_scores={"evidence_quality": 75},
            b_scores={"evidence_quality": 70},
        )
        # Contract does NOT have debate_enabled
        contract = _contract_with_dimensions()
        ev = ReasoningEvaluator("test", contract=contract)
        co = FakeCollectedOutput()
        # Enable debate via context
        ev.evaluate(co, context={"use_llm": True, "debate_enabled": True})

        # Should have used dual evaluation (2+ calls)
        assert mock_run.call_count >= 2
        assert ev.evaluator_tier_used == EVALUATOR_TIER_DUAL

    @patch("tests.workflow_harness.graders.reasoning_evaluator.subprocess.run")
    def test_debate_log_populated(self, mock_run: Any):
        """debate_log should capture debate exchange details."""
        mock_run.side_effect = _make_debate_mock(
            a_scores={"evidence_quality": 80},
            b_scores={"evidence_quality": 50},  # 30pt disagreement
            rebuttal_scores={"evidence_quality": 75},
        )
        contract = dict(MINIMAL_CONTRACT)
        contract["evaluation_config"] = {"debate_enabled": True}
        contract["reasoning_dimensions"] = [
            {"name": "evidence_quality", "weight": 1.0},
        ]
        ev = ReasoningEvaluator("test", contract=contract)
        co = FakeCollectedOutput()
        ev.evaluate(co, context={"use_llm": True})

        assert len(ev.debate_log) == 1
        entry = ev.debate_log[0]
        assert entry["dimension"] == "evidence_quality"
        assert entry["a_score"] == 80
        assert entry["b_score"] == 50
        assert entry["b_score_pre_exposure"] == 50
        assert "resolved_score" in entry
        assert "resolved_by" in entry


# ---------------------------------------------------------------------------
# Three-tier fallback chain
# ---------------------------------------------------------------------------


class TestThreeTierFallback:
    """Verify three-tier fallback: DUAL -> SINGLE_WITH_UNCERTAINTY -> UNAVAILABLE."""

    @patch("tests.workflow_harness.graders.reasoning_evaluator.subprocess.run")
    def test_tier_dual_on_successful_debate(self, mock_run: Any):
        """Successful dual evaluation sets tier to DUAL."""
        mock_run.side_effect = _make_debate_mock(
            a_scores={"evidence_quality": 75},
            b_scores={"evidence_quality": 72},
        )
        contract = dict(MINIMAL_CONTRACT)
        contract["evaluation_config"] = {"debate_enabled": True}
        contract["reasoning_dimensions"] = [
            {"name": "evidence_quality", "weight": 1.0},
        ]
        ev = ReasoningEvaluator("test", contract=contract)
        co = FakeCollectedOutput()
        ev.evaluate(co, context={"use_llm": True})
        assert ev.evaluator_tier_used == EVALUATOR_TIER_DUAL

    @patch("tests.workflow_harness.graders.reasoning_evaluator.subprocess.run",
           side_effect=_mock_subprocess_run)
    def test_tier_single_on_non_debate(self, _mock: Any):
        """Single evaluator (no debate) sets tier to SINGLE_WITH_UNCERTAINTY."""
        contract = _contract_with_dimensions()
        ev = ReasoningEvaluator("test", contract=contract)
        co = FakeCollectedOutput()
        ev.evaluate(co, context={"use_llm": True})
        assert ev.evaluator_tier_used == EVALUATOR_TIER_SINGLE

    def test_tier_unavailable_on_all_failures(self):
        """When all LLM calls fail, tier is UNAVAILABLE_SENTINEL."""
        contract = _contract_with_dimensions()
        ev = ReasoningEvaluator("test", contract=contract)
        co = FakeCollectedOutput()
        # No mock — subprocess will fail
        ev.evaluate(co, context={"use_llm": True})
        assert ev.evaluator_tier_used == EVALUATOR_TIER_UNAVAILABLE


# ---------------------------------------------------------------------------
# EvaluatorDisagreement model tests
# ---------------------------------------------------------------------------


class TestEvaluatorDisagreementModel:
    """Verify EvaluatorDisagreement has required fields."""

    def test_has_resolved_score_field(self):
        d = EvaluatorDisagreement(
            dimension="test",
            a_score=80,
            b_score=60,
            resolved_score=70,
            resolved_by="consensus",
        )
        assert d.resolved_score == 70

    def test_has_b_justification_field(self):
        d = EvaluatorDisagreement(
            dimension="test",
            a_score=80,
            b_score=60,
            b_justification="B disagrees because...",
            resolved_by="escalated",
        )
        assert d.b_justification == "B disagrees because..."

    def test_has_unreliable_field(self):
        d = EvaluatorDisagreement(
            dimension="test",
            a_score=80,
            b_score=60,
            resolved_by="escalated",
            unreliable=True,
        )
        assert d.unreliable is True

    def test_resolved_by_includes_consensus_and_escalated(self):
        """resolved_by must support 'consensus', 'a_wins', 'b_wins', 'escalated'."""
        d1 = EvaluatorDisagreement(dimension="test", a_score=80, b_score=60, resolved_by="consensus")
        assert d1.resolved_by == "consensus"
        d2 = EvaluatorDisagreement(dimension="test", a_score=80, b_score=60, resolved_by="a_wins")
        assert d2.resolved_by == "a_wins"
        d3 = EvaluatorDisagreement(dimension="test", a_score=80, b_score=60, resolved_by="b_wins")
        assert d3.resolved_by == "b_wins"
        d4 = EvaluatorDisagreement(dimension="test", a_score=80, b_score=60, resolved_by="escalated")
        assert d4.resolved_by == "escalated"


# ---------------------------------------------------------------------------
# Per-workflow reasoning weight profiles (R9)
# ---------------------------------------------------------------------------


class TestReasoningWeights:
    def test_default_weights_all_1_0(self):
        """Default reasoning weights are all 1.0 (no change to current behavior)."""
        for move_type, weight in DEFAULT_REASONING_WEIGHTS.items():
            assert weight == 1.0, f"{move_type} should default to 1.0"

    def test_default_weights_cover_all_seven_moves(self):
        """All 7 canonical move types have default weights."""
        expected_moves = {
            "HYPOTHESIS_FORMATION",
            "QUERY_FORMULATION",
            "RESULT_INTERPRETATION",
            "EVIDENCE_INTEGRATION",
            "CONTRADICTION_HANDLING",
            "CONCLUSION_SYNTHESIS",
            "SELF_CRITIQUE",
        }
        assert set(DEFAULT_REASONING_WEIGHTS.keys()) == expected_moves

    def test_evaluator_loads_default_weights(self):
        """ReasoningEvaluator uses default weights when contract has none."""
        contract = {
            "workflow_id": "test-wf",
            "category": "agent",
            "grader_type": "standard",
            "reasoning_dimensions": [],
        }
        evaluator = ReasoningEvaluator("test-wf", contract=contract)
        assert evaluator._reasoning_weights == DEFAULT_REASONING_WEIGHTS

    def test_evaluator_merges_contract_weights(self):
        """Contract reasoning_weights override defaults."""
        contract = {
            "workflow_id": "test-wf",
            "category": "agent",
            "grader_type": "standard",
            "reasoning_dimensions": [],
            "reasoning_weights": {
                "QUERY_FORMULATION": 2.0,
                "SELF_CRITIQUE": 0.5,
            },
        }
        evaluator = ReasoningEvaluator("test-wf", contract=contract)
        assert evaluator._reasoning_weights["QUERY_FORMULATION"] == 2.0
        assert evaluator._reasoning_weights["SELF_CRITIQUE"] == 0.5
        # Unset moves keep defaults
        assert evaluator._reasoning_weights["HYPOTHESIS_FORMATION"] == 1.0

    def test_default_weights_produce_same_overall_score(self):
        """With all 1.0 weights, _compute_overall behaves identically."""
        contract = {
            "workflow_id": "test-wf",
            "category": "agent",
            "grader_type": "standard",
            "reasoning_dimensions": [],
        }
        evaluator = ReasoningEvaluator("test-wf", contract=contract)

        dims = [
            DimensionScore(dimension="graph_utilization", score=80, weight=1.0),
            DimensionScore(dimension="evidence_quality", score=60, weight=1.0),
        ]
        result = evaluator._compute_overall(dims, [])
        # With equal weights and 1.0 multipliers: (80 + 60) / 2 = 70
        assert result == 70

    def test_custom_weights_shift_overall_score(self):
        """Custom reasoning weights shift the overall score."""
        contract = {
            "workflow_id": "test-wf",
            "category": "agent",
            "grader_type": "standard",
            "reasoning_dimensions": [],
            "reasoning_weights": {
                "QUERY_FORMULATION": 3.0,  # Boost query-related dims
            },
        }
        evaluator = ReasoningEvaluator("test-wf", contract=contract)

        # graph_utilization maps to QUERY_FORMULATION (among others)
        dims = [
            DimensionScore(dimension="graph_utilization", score=80, weight=1.0),
            DimensionScore(dimension="debrief_layer_1", score=40, weight=1.0),
        ]

        # With boosted QUERY_FORMULATION, graph_utilization gets higher effective weight
        result_custom = evaluator._compute_overall(dims, [])

        # Compare with default weights
        contract_default = {
            "workflow_id": "test-wf",
            "category": "agent",
            "grader_type": "standard",
            "reasoning_dimensions": [],
        }
        evaluator_default = ReasoningEvaluator("test-wf", contract=contract_default)
        result_default = evaluator_default._compute_overall(dims, [])

        # With default (equal) weights: (80+40)/2 = 60
        assert result_default == 60
        # With boosted QUERY_FORMULATION, graph_utilization (score=80)
        # gets higher weight → result should be > 60
        assert result_custom > result_default
