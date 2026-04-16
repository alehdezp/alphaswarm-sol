"""Reasoning Evaluator — LLM-powered reasoning evaluation with debate protocol.

Replaces keyword heuristic evaluator with LLM-as-judge via `claude -p`.
Implements blind-then-debate protocol for dual-evaluator consensus.
Uses per-category prompt templates for dimension scoring.

Implements 3.1c-07: central evaluator that ties together:
- 3.1c-04 GraphValueScorer (optional, per contract)
- 3.1c-05 DebriefProtocol (optional, per contract)
- Contract-defined reasoning dimensions and capability checks
- LLM-based dimension scoring via subprocess `claude -p`
- Blind-then-debate dual-evaluator protocol (IMP-14)

No imports from alphaswarm_sol.kg (DC-2).

CONTRACT_VERSION: 07.3
CONSUMERS: [3.1c-08 (Runner)]
"""

from __future__ import annotations

import json
import logging
import subprocess
import uuid
from pathlib import Path
from typing import Any

import yaml

from alphaswarm_sol.testing.evaluation.contract_loader import load_contract
from alphaswarm_sol.testing.evaluation.models import (
    DebriefResponse,
    DimensionScore,
    EvaluationPlugin,
    EvaluatorDisagreement,
    FailureNarrative,
    PluginScore,
    ScoreCard,
)
from tests.workflow_harness.graders.graph_value_scorer import GraphValueScorer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EVALUATOR_MODEL = "claude-opus-4-6"
EVALUATOR_EFFORT = "high"

# Evaluator tier provenance (P17-CSC-03)
EVALUATOR_TIER_DUAL = "DUAL"
EVALUATOR_TIER_SINGLE = "SINGLE_WITH_UNCERTAINTY"
EVALUATOR_TIER_UNAVAILABLE = "UNAVAILABLE_SENTINEL"

# Debate protocol thresholds
DEBATE_DISAGREEMENT_THRESHOLD = 15  # Points; disagreements above this trigger debate

# Prompt template directory
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

# Category-to-template mapping
CATEGORY_TEMPLATE_MAP: dict[str, str] = {
    "agent": "investigation.txt",
    "skill": "investigation.txt",
    "tool": "tool_integration.txt",
    "orchestrator": "orchestration.txt",
    "support": "support_lite.txt",
}

# ---------------------------------------------------------------------------
# DIMENSION_TO_MOVE_TYPES mapping (27 dimensions -> 1-3 move types each)
# Zero move types = applicable=False. >3 requires justification.
# ---------------------------------------------------------------------------

DIMENSION_TO_MOVE_TYPES: dict[str, list[str]] = {
    # --- Investigation dimensions ---
    "graph_utilization": [
        "QUERY_FORMULATION",
        "RESULT_INTERPRETATION",
        "EVIDENCE_INTEGRATION",
    ],
    "evidence_quality": [
        "EVIDENCE_INTEGRATION",
        "CONCLUSION_SYNTHESIS",
    ],
    "reasoning_depth": [
        "HYPOTHESIS_FORMATION",
        "RESULT_INTERPRETATION",
        "CONCLUSION_SYNTHESIS",
    ],
    "hypothesis_formation": [
        "HYPOTHESIS_FORMATION",
    ],
    "hypothesis_testing": [
        "HYPOTHESIS_FORMATION",
        "CONTRADICTION_HANDLING",
        "SELF_CRITIQUE",
    ],
    "investigation_depth": [
        "QUERY_FORMULATION",
        "RESULT_INTERPRETATION",
        "EVIDENCE_INTEGRATION",
    ],
    "conclusion_support": [
        "CONCLUSION_SYNTHESIS",
        "SELF_CRITIQUE",
    ],
    "creative_adversarial_thinking": [
        "HYPOTHESIS_FORMATION",
        "QUERY_FORMULATION",
    ],
    # --- Defender-specific ---
    "guard_identification": [
        "QUERY_FORMULATION",
        "RESULT_INTERPRETATION",
        "EVIDENCE_INTEGRATION",
    ],
    "rebuttal_quality": [
        "CONTRADICTION_HANDLING",
        "EVIDENCE_INTEGRATION",
        "CONCLUSION_SYNTHESIS",
    ],
    # --- Verifier-specific ---
    "arbitration_quality": [
        "EVIDENCE_INTEGRATION",
        "CONTRADICTION_HANDLING",
        "CONCLUSION_SYNTHESIS",
    ],
    "evidence_weighing": [
        "EVIDENCE_INTEGRATION",
        "CONTRADICTION_HANDLING",
    ],
    "verdict_justification": [
        "CONCLUSION_SYNTHESIS",
        "SELF_CRITIQUE",
    ],
    # --- Reviewer-specific ---
    "review_thoroughness": [
        "QUERY_FORMULATION",
        "RESULT_INTERPRETATION",
        "CONCLUSION_SYNTHESIS",
    ],
    # --- Tool integration ---
    "tool_selection": [
        "QUERY_FORMULATION",
    ],
    "result_interpretation": [
        "RESULT_INTERPRETATION",
        "EVIDENCE_INTEGRATION",
    ],
    "error_handling": [
        "RESULT_INTERPRETATION",
        "SELF_CRITIQUE",
    ],
    # --- Orchestration ---
    "coordination_quality": [
        "QUERY_FORMULATION",
        "EVIDENCE_INTEGRATION",
    ],
    "evidence_flow": [
        "EVIDENCE_INTEGRATION",
    ],
    "debate_coherence": [
        "CONTRADICTION_HANDLING",
        "CONCLUSION_SYNTHESIS",
    ],
    "consensus_quality": [
        "CONCLUSION_SYNTHESIS",
        "SELF_CRITIQUE",
    ],
    "task_delegation": [
        "QUERY_FORMULATION",
    ],
    # --- Finding quality ---
    "finding_quality": [
        "CONCLUSION_SYNTHESIS",
        "EVIDENCE_INTEGRATION",
    ],
    "completeness": [
        "QUERY_FORMULATION",
        "SELF_CRITIQUE",
    ],
    # --- Support ---
    "task_completion": [
        "CONCLUSION_SYNTHESIS",
    ],
    # --- Cross-cutting ---
    "verification_thoroughness": [
        "QUERY_FORMULATION",
        "EVIDENCE_INTEGRATION",
        "SELF_CRITIQUE",
    ],
    "rubric_coverage": [
        "HYPOTHESIS_FORMATION",
        "QUERY_FORMULATION",
        "RESULT_INTERPRETATION",
        "EVIDENCE_INTEGRATION",
        "CONCLUSION_SYNTHESIS",
    ],  # >3 justified: rubric_coverage spans the full reasoning process
    "exploit_path_construction": [
        "HYPOTHESIS_FORMATION",
        "CONCLUSION_SYNTHESIS",
    ],
}


# JSON schema for dimension scoring output
DIMENSION_SCORE_SCHEMA = json.dumps({
    "type": "object",
    "properties": {
        "score": {"type": "integer", "minimum": 0, "maximum": 100},
        "evidence": {"type": "array", "items": {"type": "string"}},
        "explanation": {"type": "string"},
    },
    "required": ["score", "evidence", "explanation"],
    "additionalProperties": False,
})


# JSON schema for debate rebuttal output
DEBATE_REBUTTAL_SCHEMA = json.dumps({
    "type": "object",
    "properties": {
        "revised_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "justification": {"type": "string"},
        "agrees_with_a": {"type": "boolean"},
    },
    "required": ["revised_score", "justification", "agrees_with_a"],
    "additionalProperties": False,
})


DEBATE_REBUTTAL_PROMPT = """You are Evaluator B in a dual-evaluator reasoning quality assessment.

You previously scored the dimension "{dimension}" at {b_score}/100.

Evaluator A scored it at {a_score}/100 with this explanation:
{a_explanation}

Your task: Re-evaluate considering A's perspective. You may:
1. Agree with A and adjust your score
2. Disagree and maintain your original score with justification
3. Reach a compromise score

Provide your revised assessment.
"""


# ---------------------------------------------------------------------------
# Prompt template loading
# ---------------------------------------------------------------------------

# REASONING_PROMPT_TEMPLATE — loaded from per-category template files.
# Legacy inline template preserved as fallback constant for backward
# compatibility with tests that reference it directly.
REASONING_PROMPT_TEMPLATE = """You are evaluating an AI agent's reasoning quality.

## Workflow: {workflow_id}
## Dimension: {dimension}
## Expected behavior: {expected}

## Agent's observed behavior:
{observed}

Score 0-100 on this specific dimension. Provide:
1. Score (integer 0-100)
2. Evidence items (list of strings)
3. Explanation (1-2 sentences)
"""


def _load_category_template(category: str) -> str:
    """Load prompt template for a workflow category.

    Args:
        category: Workflow category (agent, skill, tool, orchestrator, support).

    Returns:
        Template string with {workflow_id}, {dimension}, {dimension_description},
        {expected}, {observed} placeholders.
    """
    template_name = CATEGORY_TEMPLATE_MAP.get(category, "investigation.txt")
    template_path = PROMPTS_DIR / template_name
    if template_path.exists():
        return template_path.read_text()
    logger.warning("Template %s not found, using inline fallback", template_path)
    return REASONING_PROMPT_TEMPLATE


# ---------------------------------------------------------------------------
# ImprovementHint
# ---------------------------------------------------------------------------


class ImprovementHint:
    """Hint generated when a dimension scores below threshold."""

    def __init__(
        self,
        dimension: str,
        score: int,
        hypothesis: str,
        suggested_change: str,
        kill_criterion: str,
    ):
        self.dimension = dimension
        self.score = score
        self.hypothesis = hypothesis
        self.suggested_change = suggested_change
        self.kill_criterion = kill_criterion

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "score": self.score,
            "hypothesis": self.hypothesis,
            "suggested_change": self.suggested_change,
            "kill_criterion": self.kill_criterion,
        }


UNCALIBRATED_HINTS_PATH = Path(".vrs/evaluations/uncalibrated_hints.jsonl")


def _maybe_generate_hint(
    dim_name: str, score: int, explanation: str
) -> ImprovementHint | None:
    """Generate an ImprovementHint when dimension score < 40.

    Pre-calibration hints route to uncalibrated_hints.jsonl.
    """
    if score >= 40:
        return None
    hint = ImprovementHint(
        dimension=dim_name,
        score=score,
        hypothesis=f"Agent scores low on {dim_name} ({score}/100)",
        suggested_change=f"Strengthen {dim_name} in agent prompt: {explanation}",
        kill_criterion=f"{dim_name} score remains below 40 after 3 improvement cycles",
    )
    # Route to uncalibrated hints file
    try:
        UNCALIBRATED_HINTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(UNCALIBRATED_HINTS_PATH, "a") as f:
            f.write(json.dumps(hint.to_dict()) + "\n")
    except OSError:
        logger.warning("Could not write uncalibrated hint to %s", UNCALIBRATED_HINTS_PATH)
    return hint


# ---------------------------------------------------------------------------
# Dimension registry loader
# ---------------------------------------------------------------------------

_REGISTRY_PATH = Path("src/alphaswarm_sol/testing/evaluation/contracts/dimension_registry.yaml")


def _load_dimension_descriptions() -> dict[str, str]:
    """Load dimension descriptions from the registry YAML."""
    try:
        with open(_REGISTRY_PATH) as f:
            registry = yaml.safe_load(f)
        return {
            d["name"]: d.get("description", "")
            for d in registry.get("dimensions", [])
        }
    except (OSError, yaml.YAMLError):
        return {}


# Cache dimension descriptions at module load
_DIM_DESCRIPTIONS = _load_dimension_descriptions()


# ---------------------------------------------------------------------------
# LLM Evaluation via subprocess
# ---------------------------------------------------------------------------


def _llm_evaluate_dimension(
    workflow_id: str,
    category: str,
    dimension: str,
    expected: str,
    observed: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Invoke claude -p to score a single dimension via LLM.

    Uses subprocess to avoid nested Claude Code session restriction (3.1e-02).

    Args:
        workflow_id: Workflow being evaluated.
        category: Workflow category for template selection.
        dimension: Dimension name to score.
        expected: Expected reasoning coverage (from ground_truth_rubric).
        observed: Observed agent behavior (from transcript/context).
        session_id: Optional session ID for evaluator isolation.

    Returns:
        Dict with score (int), evidence (list[str]), explanation (str).

    Raises:
        subprocess.CalledProcessError: If claude -p fails.
        json.JSONDecodeError: If output is not valid JSON.
    """
    template = _load_category_template(category)
    dim_description = _DIM_DESCRIPTIONS.get(dimension, "")

    prompt = template.format(
        workflow_id=workflow_id,
        dimension=dimension,
        dimension_description=dim_description,
        expected=expected if expected else "(No expected reasoning coverage specified)",
        observed=observed,
    )

    cmd = [
        "claude",
        "-p",
        prompt,
        "--model", EVALUATOR_MODEL,
        "--effort", EVALUATOR_EFFORT,
        "--output-format", "json",
        "--json-schema", DIMENSION_SCORE_SCHEMA,
    ]
    if session_id:
        cmd.extend(["--session-id", session_id])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )

    parsed = json.loads(result.stdout)
    # Extract the result field if present (claude -p --output-format json wraps in {result, ...})
    if "result" in parsed and isinstance(parsed["result"], str):
        parsed = json.loads(parsed["result"])
    elif "result" in parsed and isinstance(parsed["result"], dict):
        parsed = parsed["result"]

    return {
        "score": int(parsed.get("score", 0)),
        "evidence": parsed.get("evidence", []),
        "explanation": parsed.get("explanation", ""),
    }


# ---------------------------------------------------------------------------
# Blind-then-debate protocol (IMP-14)
# ---------------------------------------------------------------------------


def _run_debate_rebuttal(
    dimension: str,
    a_score: int,
    a_explanation: str,
    b_score: int,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Run debate rebuttal: B sees A's explanation and writes rebuttal.

    Args:
        dimension: Dimension under debate.
        a_score: Evaluator A's score.
        a_explanation: Evaluator A's explanation.
        b_score: Evaluator B's original (pre-exposure) score.
        session_id: Session ID for evaluator B.

    Returns:
        Dict with revised_score (int), justification (str), agrees_with_a (bool).
    """
    prompt = DEBATE_REBUTTAL_PROMPT.format(
        dimension=dimension,
        a_score=a_score,
        a_explanation=a_explanation,
        b_score=b_score,
    )
    cmd = [
        "claude",
        "-p",
        prompt,
        "--model", EVALUATOR_MODEL,
        "--effort", EVALUATOR_EFFORT,
        "--output-format", "json",
        "--json-schema", DEBATE_REBUTTAL_SCHEMA,
    ]
    if session_id:
        cmd.extend(["--session-id", session_id])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    parsed = json.loads(result.stdout)
    if "result" in parsed and isinstance(parsed["result"], str):
        parsed = json.loads(parsed["result"])
    elif "result" in parsed and isinstance(parsed["result"], dict):
        parsed = parsed["result"]

    return {
        "revised_score": int(parsed.get("revised_score", b_score)),
        "justification": parsed.get("justification", ""),
        "agrees_with_a": parsed.get("agrees_with_a", False),
    }


def _resolve_disagreement(
    dimension: str,
    a_result: dict[str, Any],
    b_result: dict[str, Any],
    b_session_id: str,
) -> EvaluatorDisagreement:
    """Resolve a >10pt disagreement via structured debate exchange.

    Protocol:
    1. B sees A's explanation (not score initially — B already committed blind score).
    2. B writes rebuttal with revised_score.
    3. If scores converge within threshold -> consensus.
    4. If B agrees explicitly -> a_wins.
    5. If B holds position -> escalated (lower score, unreliable=True).

    Args:
        dimension: Dimension under dispute.
        a_result: Evaluator A's full result dict.
        b_result: Evaluator B's full result dict.
        b_session_id: Session ID for evaluator B (separate from A).

    Returns:
        EvaluatorDisagreement with resolution details.
    """
    a_score = a_result["score"]
    b_score = b_result["score"]
    b_pre_exposure = b_score  # Capture before any exposure to A

    try:
        rebuttal = _run_debate_rebuttal(
            dimension=dimension,
            a_score=a_score,
            a_explanation=a_result.get("explanation", ""),
            b_score=b_score,
            session_id=b_session_id,
        )

        revised_b = rebuttal["revised_score"]
        justification = rebuttal["justification"]
        agrees = rebuttal["agrees_with_a"]

        # Determine resolution
        new_delta = abs(a_score - revised_b)

        if new_delta <= DEBATE_DISAGREEMENT_THRESHOLD:
            # Converged — use average as consensus
            resolved_score = (a_score + revised_b) // 2
            resolved_by = "consensus"
            unreliable = False
        elif agrees:
            # B explicitly agrees with A
            resolved_score = a_score
            resolved_by = "a_wins"
            unreliable = False
        else:
            # Unresolved — use lower score with unreliable flag
            resolved_score = min(a_score, revised_b)
            resolved_by = "escalated"
            unreliable = True

        return EvaluatorDisagreement(
            dimension=dimension,
            a_score=a_score,
            b_score=revised_b,
            b_score_pre_exposure=b_pre_exposure,
            b_justification=justification,
            resolved_score=resolved_score,
            debate_completed=True,
            resolved_by=resolved_by,
            unreliable=unreliable,
        )

    except (subprocess.CalledProcessError, json.JSONDecodeError, OSError) as e:
        logger.warning("Debate rebuttal failed for %s: %s", dimension, e)
        # Fallback: escalated with lower score
        return EvaluatorDisagreement(
            dimension=dimension,
            a_score=a_score,
            b_score=b_score,
            b_score_pre_exposure=b_pre_exposure,
            b_justification="",
            resolved_score=min(a_score, b_score),
            debate_completed=False,
            resolved_by="escalated",
            unreliable=True,
        )


# ---------------------------------------------------------------------------
# Structural proxy (heuristic) — STRUCTURAL_PROXY role only, not scoring
# ---------------------------------------------------------------------------


def _structural_proxy_check(
    _dim_name: str,
    collected_output: Any,
) -> dict[str, Any]:
    """STRUCTURAL_PROXY: Heuristic check for anti-fabrication and fast-fail gating.

    Does NOT produce a numeric score for evaluation. Returns gate signals only.
    Per P17-IMP-01: heuristics do not score, they gate.
    """
    tool_seq = getattr(collected_output, "tool_sequence", [])
    bskg_queries = getattr(collected_output, "bskg_queries", [])

    signals: dict[str, Any] = {
        "has_tool_usage": len(tool_seq) > 0,
        "has_bskg_queries": len(bskg_queries) > 0,
        "tool_count": len(tool_seq),
        "query_count": len(bskg_queries),
        "anti_fabrication_pass": True,
    }

    # Anti-fabrication: if transcript claims BSKG queries but tool_sequence
    # has no Bash calls, flag as suspicious
    if len(bskg_queries) > 0 and "Bash" not in tool_seq:
        signals["anti_fabrication_pass"] = False
        signals["anti_fabrication_reason"] = "BSKG queries claimed but no Bash in tool sequence"

    return signals


# ---------------------------------------------------------------------------
# FAILURE_NARRATIVE_TEMPLATE (kept for backward compatibility)
# ---------------------------------------------------------------------------

FAILURE_NARRATIVE_TEMPLATE = """An agent scored {score}/100 on {workflow_id}.

Low-scoring dimensions:
{low_dims}

Generate a failure narrative with:
1. what_happened: Factual description of what the agent did
2. what_should_have_happened: Expected behavior for a higher score
"""


# ---------------------------------------------------------------------------
# ReasoningEvaluator
# ---------------------------------------------------------------------------


class ReasoningEvaluator:
    """Orchestrate evaluation plugins and LLM-based dimension scoring.

    Usage:
        evaluator = ReasoningEvaluator("agent-vrs-attacker")
        score_card = evaluator.evaluate(collected_output, contract, context)

    The evaluator replaces keyword heuristic scoring with LLM evaluation.
    Heuristic code is demoted to STRUCTURAL_PROXY role only (gate signals).
    """

    def __init__(
        self,
        workflow_id: str,
        contract: dict[str, Any] | None = None,
        contracts_dir: Path | None = None,
        plugins: list[EvaluationPlugin] | None = None,
        pass_threshold: int = 60,
    ):
        """Initialize the evaluator.

        Args:
            workflow_id: Which workflow to evaluate.
            contract: Pre-loaded contract dict. If None, loads from disk.
            contracts_dir: Override contracts directory.
            plugins: Additional plugins to run alongside contract-defined ones.
            pass_threshold: Score needed to pass (default 60).
        """
        self._workflow_id = workflow_id

        if contract is not None:
            self._contract = contract
        else:
            self._contract = load_contract(workflow_id, contracts_dir)

        self._pass_threshold = pass_threshold
        self._plugins: list[EvaluationPlugin] = list(plugins or [])
        self._improvement_hints: list[ImprovementHint] = []
        self._evaluator_tier_used: str = EVALUATOR_TIER_UNAVAILABLE
        self._consistency_class: str | None = None
        self._debate_log: list[dict[str, Any]] = []
        self._disagreements: list[EvaluatorDisagreement] = []

        # Per-workflow reasoning weight profiles (R9)
        from alphaswarm_sol.testing.evaluation.models import DEFAULT_REASONING_WEIGHTS

        self._reasoning_weights: dict[str, float] = dict(DEFAULT_REASONING_WEIGHTS)
        contract_weights = self._contract.get("reasoning_weights", {})
        if isinstance(contract_weights, dict):
            self._reasoning_weights.update(contract_weights)

        # Auto-register GVS - default ON for agent/skill workflows
        eval_config = self._contract.get("evaluation_config", {})
        category = self._contract.get("category", "")
        should_run_gvs = eval_config.get("run_gvs", category in ("agent", "skill"))
        if should_run_gvs:
            if not any(p.name == "graph_value" for p in self._plugins):
                self._plugins.append(GraphValueScorer())

    @property
    def workflow_id(self) -> str:
        return self._workflow_id

    @property
    def contract(self) -> dict[str, Any]:
        return self._contract

    @property
    def evaluator_tier_used(self) -> str:
        """Evaluator tier provenance: DUAL, SINGLE_WITH_UNCERTAINTY, UNAVAILABLE_SENTINEL."""
        return self._evaluator_tier_used

    @property
    def consistency_class(self) -> str | None:
        """Self-consistency classification: stable, recommended, or unstable."""
        return self._consistency_class

    @property
    def debate_log(self) -> list[dict[str, Any]]:
        """Log of debate exchanges between evaluators."""
        return self._debate_log

    @property
    def disagreements(self) -> list[EvaluatorDisagreement]:
        """Disagreements between dual evaluators (if debate was active)."""
        return self._disagreements

    def evaluate(
        self,
        collected_output: Any,
        debrief: DebriefResponse | None = None,
        obs_dir: Path | None = None,  # noqa: ARG002 - reserved for future debrief/GVS use
        obs_summary: Any | None = None,
        context: dict[str, Any] | None = None,
    ) -> ScoreCard:
        """Run the full evaluation pipeline.

        3.1c-08 Interface Contract
        --------------------------
        This is the primary entry point consumed by the EvaluationRunner (3.1c-08).

        - **contract**: The evaluation contract (workflow under test) is passed
          via the constructor, NOT per-call. Each ReasoningEvaluator instance is
          bound to exactly one contract for its lifetime.
        - **collected_output**: Maps to the "transcript" concept in evaluation
          documentation. This is the observed agent output (CollectedOutput or
          EvaluationInput) containing tool_sequence, bskg_queries, transcript
          text, and other observable data from the workflow run.
        - **context**: Carries supplementary evaluation data that is not part of
          the transcript itself. Keys include ground_truth_rubric (expected
          reasoning coverage from contract), transcript_text (full text for LLM
          evaluation), use_llm (bool, default True), and debate_enabled (bool,
          override for debate setting).

        The return type (ScoreCard) includes dimension_scores, and the instance
        exposes evaluator_tier_used, consistency_class, and disagreements
        properties for suite-level health reporting by 3.1c-08.

        Args:
            collected_output: CollectedOutput or EvaluationInput with
                tool_sequence, bskg_queries, transcript, etc.
            debrief: Pre-computed debrief. If None and contract requests
                debrief, runs debrief protocol.
            obs_dir: Path to observations dir for debrief/GVS.
            obs_summary: Parsed observation summary from ObservationParser.
            context: Optional evaluation context dict. May contain:
                - ground_truth_rubric: str (expected reasoning coverage)
                - transcript_text: str (full transcript for LLM evaluation)
                - use_llm: bool (whether to use LLM evaluation, default True)
                - debate_enabled: bool (override debate setting)

        Returns:
            ScoreCard with all dimension scores and pass/fail.
        """
        context = context or {}

        # 1. Run plugins (with optional runtime context)
        plugin_context: dict[str, Any] = {}
        if obs_summary is not None:
            plugin_context["obs_summary"] = obs_summary
        if debrief is not None:
            plugin_context["debrief"] = debrief
        plugin_scores = self._run_plugins(collected_output, context=plugin_context)

        # 2. Evaluate contract dimensions (LLM-based or structural proxy)
        dimension_scores = self._evaluate_dimensions(
            collected_output, plugin_scores, debrief, context
        )

        # 3. Evaluate capability checks
        cap_scores = self._evaluate_capabilities(collected_output)
        dimension_scores.extend(cap_scores)

        # 4. Compute overall score
        overall = self._compute_overall(dimension_scores, plugin_scores)

        # 5. Determine pass/fail
        passed = overall >= self._pass_threshold

        # 6. Generate failure narrative if needed
        narrative = None
        if not passed:
            narrative = self._generate_failure_narrative(
                overall, dimension_scores, plugin_scores
            )

        return ScoreCard(
            workflow_id=self._workflow_id,
            dimensions=dimension_scores,
            plugin_scores=plugin_scores,
            overall_score=overall,
            passed=passed,
            pass_threshold=self._pass_threshold,
            failure_narrative=narrative,
        )

    def _run_plugins(
        self,
        collected_output: Any,
        context: dict[str, Any] | None = None,
    ) -> list[PluginScore]:
        """Run all registered plugins."""
        scores = []
        for plugin in self._plugins:
            score = plugin.score(collected_output, context=context)
            scores.append(score)
        return scores

    def _is_debate_enabled(self, context: dict[str, Any]) -> bool:
        """Check if debate protocol should be used.

        Debate is enabled by: context override > contract evaluation_config > default False.
        """
        if "debate_enabled" in context:
            return bool(context["debate_enabled"])
        eval_config = self._contract.get("evaluation_config", {})
        return bool(eval_config.get("debate_enabled", False))

    def _evaluate_dimensions(
        self,
        collected_output: Any,
        plugin_scores: list[PluginScore],
        debrief: DebriefResponse | None,
        context: dict[str, Any],
    ) -> list[DimensionScore]:
        """Evaluate contract-defined reasoning dimensions.

        Uses LLM scoring when context['use_llm'] is True (default).
        When debate is enabled, runs blind-then-debate dual-evaluator protocol.
        Falls back to UNAVAILABLE_SENTINEL when LLM fails.
        Heuristic is STRUCTURAL_PROXY only — no score assignment.
        """
        # Use active_dimensions whitelist if present, else reasoning_dimensions
        active_dims = self._contract.get("active_dimensions")
        if active_dims is not None:
            dimensions = [{"name": d, "weight": 1.0} for d in active_dims]
        else:
            dimensions = self._contract.get("reasoning_dimensions", [])

        scores = []
        use_llm = context.get("use_llm", True)
        debate_enabled = self._is_debate_enabled(context)
        category = self._contract.get("category", "agent")
        rubric = (
            context.get("ground_truth_rubric")
            or self._contract.get("ground_truth_rubric", "")
        )

        # Generate session IDs for dual evaluators (separate sessions per IMP-14)
        session_a = f"eval-a-{uuid.uuid4().hex[:8]}" if debate_enabled else None
        session_b = f"eval-b-{uuid.uuid4().hex[:8]}" if debate_enabled else None

        for dim in dimensions:
            if isinstance(dim, str):
                dim_name = dim
                dim_weight = 1.0
                dim_dict: dict[str, Any] = {"name": dim, "weight": 1.0}
            else:
                dim_name = dim.get("name", "unknown")
                dim_weight = dim.get("weight", 1.0)
                dim_dict = dim

            # Try to source score from plugins first (before mapping check)
            plugin_score = self._find_plugin_score(dim_name, plugin_scores)
            if plugin_score is not None:
                scores.append(DimensionScore(
                    dimension=dim_name,
                    score=plugin_score.score,
                    weight=dim_weight,
                    scoring_method="llm",
                    evidence=[f"Plugin: {plugin_score.plugin_name}"],
                    explanation=plugin_score.explanation or f"From {plugin_score.plugin_name}",
                ))
                continue

            # Try debrief-sourced dimensions
            if debrief is not None and "debrief" in dim_name.lower():
                debrief_score = self._score_debrief_dimension(debrief, dim_dict)
                scores.append(debrief_score)
                continue

            # Check if dimension has move types (applicable)
            move_types = DIMENSION_TO_MOVE_TYPES.get(dim_name, [])
            if not move_types:
                scores.append(DimensionScore(
                    dimension=dim_name,
                    score=0,
                    weight=dim_weight,
                    scoring_method="heuristic",
                    applicable=False,
                    explanation="DIMENSION_UNMAPPED: no move types mapped",
                ))
                continue

            # LLM-based dimension scoring (primary path)
            if use_llm:
                observed = self._build_observed_text(collected_output, context)

                if debate_enabled:
                    # Blind-then-debate protocol (IMP-14)
                    dim_score = self._evaluate_with_debate(
                        dim_name, dim_weight, category, rubric, observed,
                        session_a, session_b,
                    )
                else:
                    # Single evaluator
                    dim_score = self._score_dimension_via_llm(
                        dim_name, dim_weight, category, rubric, observed,
                    )

                if dim_score is not None:
                    scores.append(dim_score)
                    # Generate improvement hint if score < 40
                    _maybe_generate_hint(
                        dim_name, dim_score.score, dim_score.explanation
                    )
                    continue

            # Three-tier fallback: tier (c) — UNAVAILABLE_SENTINEL
            # No heuristic fallback for scoring (P17-IMP-01, 3.1e-03)
            self._evaluator_tier_used = EVALUATOR_TIER_UNAVAILABLE
            scores.append(DimensionScore(
                dimension=dim_name,
                score=0,
                weight=dim_weight,
                scoring_method="heuristic",
                applicable=False,
                explanation="evaluation_status: unavailable — LLM evaluation failed, no heuristic fallback",
            ))

        return scores

    def _evaluate_with_debate(
        self,
        dim_name: str,
        weight: float,
        category: str,
        rubric: str,
        observed: str,
        session_a: str | None,
        session_b: str | None,
    ) -> DimensionScore | None:
        """Run blind-then-debate dual-evaluator protocol for one dimension.

        Protocol (IMP-14):
        1. Evaluator A scores dimension (with session_a).
        2. Evaluator B scores blind (with session_b) — receives transcript
           and A's raw score but NOT A's explanation.
        3. If disagreement > 10pt, B sees A's explanation and writes rebuttal.
        4. Tie-breaking: unresolved -> lower score with unreliable=True.

        Returns:
            DimensionScore with resolved score, or None if both evaluators fail.
        """
        # Step 1: Evaluator A scores
        try:
            a_result = _llm_evaluate_dimension(
                workflow_id=self._workflow_id,
                category=category,
                dimension=dim_name,
                expected=rubric,
                observed=observed,
                session_id=session_a,
            )
        except (subprocess.CalledProcessError, json.JSONDecodeError, OSError) as e:
            logger.warning("Evaluator A failed for %s: %s", dim_name, e)
            # Fall through to single-evaluator
            return self._score_dimension_via_llm(
                dim_name, weight, category, rubric, observed
            )

        # Step 2: Evaluator B scores blind (separate session)
        try:
            b_result = _llm_evaluate_dimension(
                workflow_id=self._workflow_id,
                category=category,
                dimension=dim_name,
                expected=rubric,
                observed=observed,
                session_id=session_b,
            )
        except (subprocess.CalledProcessError, json.JSONDecodeError, OSError) as e:
            logger.warning("Evaluator B failed for %s: %s — falling back to single", dim_name, e)
            # Tier (b): single evaluator with uncertainty
            self._evaluator_tier_used = EVALUATOR_TIER_SINGLE
            return DimensionScore(
                dimension=dim_name,
                score=a_result["score"],
                weight=weight,
                scoring_method="llm",
                evidence=a_result.get("evidence", []) + ["evaluator_b_failed: single evaluator mode"],
                explanation=a_result.get("explanation", ""),
            )

        a_score = a_result["score"]
        b_score = b_result["score"]
        delta = abs(a_score - b_score)

        # Step 3: Check for disagreement
        if delta > DEBATE_DISAGREEMENT_THRESHOLD:
            # Run structured debate exchange
            disagreement = _resolve_disagreement(
                dimension=dim_name,
                a_result=a_result,
                b_result=b_result,
                b_session_id=session_b or "",
            )
            self._disagreements.append(disagreement)
            self._debate_log.append({
                "dimension": dim_name,
                "a_score": a_score,
                "b_score": b_score,
                "b_score_pre_exposure": disagreement.b_score_pre_exposure,
                "resolved_score": disagreement.resolved_score,
                "resolved_by": disagreement.resolved_by,
                "unreliable": disagreement.unreliable,
            })

            final_score = disagreement.resolved_score if disagreement.resolved_score is not None else min(a_score, b_score)
            evidence = a_result.get("evidence", []) + [
                f"debate: {disagreement.resolved_by}",
                f"B_pre_exposure: {disagreement.b_score_pre_exposure}",
            ]
            if disagreement.unreliable:
                evidence.append("unreliable: True")
        else:
            # Agreement — use average
            final_score = (a_score + b_score) // 2
            evidence = a_result.get("evidence", []) + [
                f"dual_evaluator_agreement: A={a_score}, B={b_score}",
            ]

        self._evaluator_tier_used = EVALUATOR_TIER_DUAL

        return DimensionScore(
            dimension=dim_name,
            score=final_score,
            weight=weight,
            scoring_method="llm",
            evidence=evidence,
            explanation=a_result.get("explanation", ""),
        )

    def _score_dimension_via_llm(
        self,
        dim_name: str,
        weight: float,
        category: str,
        rubric: str,
        observed: str,
    ) -> DimensionScore | None:
        """Score a dimension via LLM subprocess call.

        Returns:
            DimensionScore if successful, None if LLM call fails.
        """
        try:
            result = _llm_evaluate_dimension(
                workflow_id=self._workflow_id,
                category=category,
                dimension=dim_name,
                expected=rubric,
                observed=observed,
            )
            if self._evaluator_tier_used == EVALUATOR_TIER_UNAVAILABLE:
                self._evaluator_tier_used = EVALUATOR_TIER_SINGLE
            return DimensionScore(
                dimension=dim_name,
                score=result["score"],
                weight=weight,
                scoring_method="llm",
                evidence=result.get("evidence", []),
                explanation=result.get("explanation", ""),
            )
        except (subprocess.CalledProcessError, json.JSONDecodeError, OSError, KeyError) as e:
            logger.warning("LLM evaluation failed for %s: %s", dim_name, e)
            return None

    def _build_observed_text(
        self, collected_output: Any, context: dict[str, Any]
    ) -> str:
        """Build observed behavior text from collected output and context."""
        # Prefer explicit transcript text from context
        if "transcript_text" in context:
            return context["transcript_text"]

        # Build from collected_output fields
        parts = []
        observed = getattr(collected_output, "observed", None)
        if isinstance(observed, dict):
            for key, value in observed.items():
                if isinstance(value, list):
                    parts.append(f"## {key}")
                    for item in value:
                        if isinstance(item, dict):
                            parts.append(json.dumps(item, indent=2))
                        else:
                            parts.append(str(item))
                elif value:
                    parts.append(f"## {key}\n{value}")

        response_text = getattr(collected_output, "response_text", "")
        if response_text and not parts:
            parts.append(response_text)

        tool_seq = getattr(collected_output, "tool_sequence", [])
        if tool_seq:
            parts.append(f"Tool sequence: {', '.join(tool_seq)}")

        bskg_queries = getattr(collected_output, "bskg_queries", [])
        if bskg_queries:
            parts.append(f"BSKG queries: {len(bskg_queries)} queries issued")
            for q in bskg_queries[:5]:
                if isinstance(q, dict):
                    parts.append(f"  - {q.get('command', q.get('category', str(q)))}")

        return "\n\n".join(parts) if parts else "(No observed behavior data)"

    def _apply_debrief_weight(
        self, score: int, debrief: DebriefResponse | None
    ) -> int:
        """Apply debrief_layer_weight from contract to debrief-derived scores.

        Multiplies debrief-derived dimension scores by
        contract's evaluation_config.debrief_layer_weight.
        """
        if debrief is None:
            return score
        eval_config = self._contract.get("evaluation_config", {})
        weight = eval_config.get("debrief_layer_weight", 1.0)
        return int(min(100, max(0, score * weight)))

    def _evaluate_capabilities(self, collected_output: Any) -> list[DimensionScore]:
        """Evaluate contract-defined capability checks."""
        checks = self._contract.get("capability_checks", [])
        scores = []

        for check in checks:
            check_name = check.get("name") or check.get("id", "unknown")
            check_type = check.get("type") or check.get("grader_type", "code")

            if check_type == "presence":
                score = self._check_presence(check, collected_output)
            elif check_type == "ordering":
                score = self._check_ordering(check, collected_output)
            elif check_type == "count":
                score = self._check_count(check, collected_output)
            elif check_type == "code":
                score = self._check_code_capability(check, collected_output)
            elif check_type == "model":
                score = self._check_model_capability(check, collected_output)
            else:
                score = DimensionScore(
                    dimension=f"cap:{check_name}",
                    score=0,
                    weight=0.5,
                    explanation=f"Unknown check type: {check_type}",
                )
            scores.append(score)

        return scores

    def _compute_overall(
        self,
        dimensions: list[DimensionScore],
        plugin_scores: list[PluginScore],
    ) -> int:
        """Compute weighted overall score.

        Applies per-workflow reasoning weight multipliers (R9) when
        available. Each dimension's weight is multiplied by the average
        reasoning weight of its associated move types. Default 1.0
        preserves current behavior.
        """
        if not dimensions and not plugin_scores:
            return 0

        total_weight = 0.0
        weighted_sum = 0.0

        for dim in dimensions:
            if not dim.applicable:
                continue
            # Apply reasoning weight multiplier based on dimension's move types
            move_types = DIMENSION_TO_MOVE_TYPES.get(dim.dimension, [])
            if move_types:
                multipliers = [
                    self._reasoning_weights.get(mt, 1.0) for mt in move_types
                ]
                reasoning_multiplier = sum(multipliers) / len(multipliers)
            else:
                reasoning_multiplier = 1.0
            effective_weight = dim.weight * reasoning_multiplier
            weighted_sum += dim.score * effective_weight
            total_weight += effective_weight

        # Include plugin scores with equal weight if no dimensions reference them
        referenced_plugins = {
            e for d in dimensions for e in d.evidence if e.startswith("Plugin:")
        }
        for ps in plugin_scores:
            ref = f"Plugin: {ps.plugin_name}"
            if ref not in referenced_plugins:
                weighted_sum += ps.score * 1.0
                total_weight += 1.0

        if total_weight == 0:
            return 0

        raw = weighted_sum / total_weight
        return int(min(100, max(0, raw)))

    def _find_plugin_score(
        self, dim_name: str, plugin_scores: list[PluginScore]
    ) -> PluginScore | None:
        """Find a plugin score matching a dimension name."""
        name_map = {
            "graph_utilization": "graph_value",
            "graph_value": "graph_value",
            "bskg_usage": "graph_value",
        }
        target = name_map.get(dim_name, dim_name)
        for ps in plugin_scores:
            if ps.plugin_name == target:
                return ps
        return None

    def _score_debrief_dimension(
        self, debrief: DebriefResponse, dim: dict[str, Any]
    ) -> DimensionScore:
        """Score a debrief-related dimension."""
        base_score = int(debrief.confidence * 100)

        non_empty = sum(
            1 for a in debrief.answers
            if a and not a.startswith("[No")
        )
        answer_ratio = non_empty / max(len(debrief.answers), 1)
        adjusted_score = int((base_score * 0.5) + (answer_ratio * 100 * 0.5))
        adjusted_score = self._apply_debrief_weight(adjusted_score, debrief)

        return DimensionScore(
            dimension=dim.get("name", "debrief"),
            score=min(100, adjusted_score),
            weight=dim.get("weight", 1.0),
            scoring_method="llm",
            evidence=[
                f"Layer: {debrief.layer_used}",
                f"Confidence: {debrief.confidence:.2f}",
                f"Non-empty answers: {non_empty}/{len(debrief.answers)}",
            ],
            explanation=f"Debrief via {debrief.layer_used} layer",
        )

    def _check_code_capability(
        self, check: dict[str, Any], collected_output: Any
    ) -> DimensionScore:
        """Evaluate a code-based capability check from contract."""
        check_name = check.get("name") or check.get("id", "unknown")
        description = check.get("expected_behavior", "")
        tool_seq = getattr(collected_output, "tool_sequence", [])
        bskg_queries = getattr(collected_output, "bskg_queries", [])

        score = 0
        evidence = []

        desc_lower = description.lower()

        if "bash" in desc_lower or "tool sequence" in desc_lower:
            if "Bash" in tool_seq:
                score += 50
                evidence.append("Bash found in tool sequence")

        if "alphaswarm" in desc_lower or "build-kg" in desc_lower:
            has_alphaswarm = any(
                "alphaswarm" in str(q.get("command", "") if isinstance(q, dict) else "")
                or "build-kg" in str(q.get("category", "") if isinstance(q, dict) else "")
                for q in bskg_queries
            )
            if has_alphaswarm:
                score += 50
                evidence.append("BSKG queries found")

        if "query" in desc_lower or "analyze" in desc_lower:
            has_query = any(
                q.get("category", "") in ("query", "analyze", "pattern-query")
                if isinstance(q, dict) else False
                for q in bskg_queries
            )
            if has_query:
                score += 30
                evidence.append("Query/analyze commands found")

        if "finding" in desc_lower or "vulnerabilit" in desc_lower:
            response = getattr(collected_output, "response_text", "")
            if response and len(response) > 50:
                score += 30
                evidence.append("Non-trivial response text present")

        score = min(100, score)

        return DimensionScore(
            dimension=f"cap:{check_name}",
            score=score,
            weight=0.5,
            evidence=evidence or ["No matching observations"],
            explanation=f"Code check: {description[:80]}",
        )

    def _check_model_capability(
        self, check: dict[str, Any], collected_output: Any
    ) -> DimensionScore:
        """Evaluate a model-based capability check via keyword heuristic.

        STRUCTURAL_PROXY: capability gate -- keyword matching for cap: checks only.

        This is a capability check (pass/fail structural), not a reasoning
        dimension score. Keyword matching is appropriate for capability gating
        (cap: prefix dimensions). It does NOT produce reasoning scores --
        reasoning scoring is exclusively handled by _llm_evaluate_dimension().
        """
        check_name = check.get("name") or check.get("id", "unknown")
        description = check.get("expected_behavior", "") or check.get("description", "")
        tool_seq = getattr(collected_output, "tool_sequence", [])
        bskg_queries = getattr(collected_output, "bskg_queries", [])
        response_text = getattr(collected_output, "response_text", "")

        desc_lower = description.lower()
        keywords = [w for w in desc_lower.split() if len(w) > 3]

        if not keywords:
            return DimensionScore(
                dimension=f"cap:{check_name}",
                score=30,
                weight=0.5,
                explanation="Model check: no keywords in description",
            )

        obs_parts = []
        obs_parts.extend(tool_seq)
        for q in bskg_queries:
            if isinstance(q, dict):
                obs_parts.append(str(q.get("command", "")))
                obs_parts.append(str(q.get("category", "")))
            else:
                obs_parts.append(str(q))
        obs_parts.append(response_text)
        obs_text = " ".join(obs_parts).lower()

        matched = sum(1 for kw in keywords if kw in obs_text)
        ratio = matched / len(keywords)
        score = int(min(100, ratio * 100))

        evidence = [f"Keywords matched: {matched}/{len(keywords)}"]
        if tool_seq:
            evidence.append(f"Tools observed: {len(tool_seq)}")
        if bskg_queries:
            evidence.append(f"BSKG queries: {len(bskg_queries)}")

        return DimensionScore(
            dimension=f"cap:{check_name}",
            score=score,
            weight=0.5,
            evidence=evidence,
            explanation=f"Model check (capability gate): {description[:80]}",
        )

    def _check_presence(
        self, check: dict[str, Any], collected_output: Any
    ) -> DimensionScore:
        """Check if expected tools/queries are present."""
        expected = check.get("expected", [])
        tool_seq = getattr(collected_output, "tool_sequence", [])
        bskg_queries = getattr(collected_output, "bskg_queries", [])

        found = []
        for item in expected:
            if item in tool_seq:
                found.append(item)
            elif any(
                item in str(getattr(q, "command", q.get("command", "") if isinstance(q, dict) else ""))
                for q in bskg_queries
            ):
                found.append(item)

        ratio = len(found) / max(len(expected), 1)
        score = int(ratio * 100)

        return DimensionScore(
            dimension=f"cap:{check.get('name', 'presence')}",
            score=score,
            weight=0.5,
            evidence=[f"Found {len(found)}/{len(expected)}: {found}"],
            explanation=f"Presence check: {len(found)}/{len(expected)} items found",
        )

    def _check_ordering(
        self, check: dict[str, Any], collected_output: Any
    ) -> DimensionScore:
        """Check if tools appear in expected order."""
        expected_order = check.get("expected_order", [])
        tool_seq = getattr(collected_output, "tool_sequence", [])

        if not expected_order:
            return DimensionScore(
                dimension=f"cap:{check.get('name', 'ordering')}",
                score=100,
                weight=0.5,
            )

        last_idx = -1
        in_order = 0
        for item in expected_order:
            for i in range(last_idx + 1, len(tool_seq)):
                if tool_seq[i] == item:
                    last_idx = i
                    in_order += 1
                    break

        ratio = in_order / len(expected_order)
        score = int(ratio * 100)

        return DimensionScore(
            dimension=f"cap:{check.get('name', 'ordering')}",
            score=score,
            weight=0.5,
            evidence=[f"In-order: {in_order}/{len(expected_order)}"],
            explanation=f"Ordering: {in_order}/{len(expected_order)} steps in sequence",
        )

    def _check_count(
        self, check: dict[str, Any], collected_output: Any
    ) -> DimensionScore:
        """Check if a minimum count of items exists."""
        target = check.get("target", "tool_sequence")
        min_count = check.get("min_count", 1)

        items = getattr(collected_output, target, [])
        actual = len(items) if isinstance(items, list) else 0

        score = 100 if actual >= min_count else int((actual / max(min_count, 1)) * 100)

        return DimensionScore(
            dimension=f"cap:{check.get('name', 'count')}",
            score=score,
            weight=0.5,
            evidence=[f"{target}: {actual} (min: {min_count})"],
            explanation=f"Count: {actual}/{min_count}",
        )

    def _generate_failure_narrative(
        self,
        overall: int,
        dimensions: list[DimensionScore],
        _plugin_scores: list[PluginScore],
    ) -> FailureNarrative:
        """Generate a failure narrative for low scores."""
        low_dims = [d for d in dimensions if d.score < 50 and d.applicable]
        low_names = [d.dimension for d in low_dims]

        what_parts = []
        should_parts = []

        for d in low_dims:
            what_parts.append(f"{d.dimension}: scored {d.score}/100")
            if d.explanation:
                what_parts.append(f"  ({d.explanation})")
            should_parts.append(f"{d.dimension}: should score >= 50")

        if not what_parts:
            what_parts.append(f"Overall score {overall} below threshold")
            should_parts.append("Overall score should meet pass threshold")

        return FailureNarrative(
            what_happened=" | ".join(what_parts),
            what_should_have_happened=" | ".join(should_parts),
            root_dimensions=low_names,
        )
