"""
Multi-Tier Model Support (Task 11.12)

Enables task-appropriate model selection based on:
- Finding complexity
- Analysis type requirements
- Cost constraints
- Performance needs

Model tiers:
- CHEAP: Fast, low-cost models for simple checks
- STANDARD: Balanced models for typical analysis
- PREMIUM: High-quality models for complex reasoning

The system provides hints for parent AI agents (Claude Code, Codex, etc.)
to select appropriate models, as VKG itself doesn't call LLM APIs directly
when running as a tool for AI agents.
"""

from dataclasses import dataclass, field
from typing import Optional, Any
from enum import Enum
import json


class ModelTier(str, Enum):
    """Model tier for analysis complexity."""
    CHEAP = "cheap"         # Fast, simple verification
    STANDARD = "standard"   # Typical security analysis
    PREMIUM = "premium"     # Complex reasoning, business logic


class AnalysisType(str, Enum):
    """Type of analysis required."""
    SIMPLE_CHECK = "simple_check"           # Is guard present? Basic pattern.
    CONTEXT_AWARE = "context_aware"         # Needs surrounding code context
    BUSINESS_LOGIC = "business_logic"       # Requires business understanding
    CROSS_FUNCTION = "cross_function"       # Multi-function analysis
    CROSS_CONTRACT = "cross_contract"       # Multi-contract analysis


class Complexity(str, Enum):
    """Finding complexity level."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ModelTierConfig:
    """Configuration for model tiers."""

    # Model names per tier (for reference - actual selection by parent agent)
    tier_models: dict[ModelTier, list[str]] = field(default_factory=dict)

    # Complexity thresholds
    low_complexity_patterns: list[str] = field(default_factory=list)
    high_complexity_patterns: list[str] = field(default_factory=list)

    # Cost weights (relative)
    tier_cost_weights: dict[ModelTier, float] = field(default_factory=dict)

    def __post_init__(self):
        if not self.tier_models:
            self.tier_models = {
                ModelTier.CHEAP: ["claude-3-haiku", "gpt-4o-mini", "gemini-1.5-flash"],
                ModelTier.STANDARD: ["claude-3-5-sonnet", "gpt-4o", "gemini-1.5-pro"],
                ModelTier.PREMIUM: ["claude-3-opus", "o1", "claude-3-5-opus"],
            }

        if not self.low_complexity_patterns:
            self.low_complexity_patterns = [
                "unchecked-return",
                "timestamp-dependency",
                "strict-equality",
                "magic-number",
            ]

        if not self.high_complexity_patterns:
            self.high_complexity_patterns = [
                "business-logic",
                "access-control",
                "reentrancy",
                "price-manipulation",
                "flash-loan",
                "governance",
            ]

        if not self.tier_cost_weights:
            self.tier_cost_weights = {
                ModelTier.CHEAP: 0.1,
                ModelTier.STANDARD: 1.0,
                ModelTier.PREMIUM: 10.0,
            }


@dataclass
class TierBContext:
    """
    Context for parent AI agent to perform Tier B analysis.

    This is the structured output that VKG provides to AI agents
    (Claude Code, Codex, OpenCode) so they can perform intelligent
    Tier B verification using their own model selection.
    """
    finding_id: str
    tier_a_verdict: str  # "match", "possible", "unlikely"
    pattern: str
    severity: str
    confidence: str

    # Complexity hints for model selection
    complexity: Complexity
    suggested_tier: ModelTier
    analysis_type: AnalysisType

    # Context for analysis
    code_context: str = ""
    evidence_summary: str = ""
    investigation_hints: list[str] = field(default_factory=list)

    # Cost/performance hints
    estimated_tokens: int = 0
    urgency: str = "normal"  # "low", "normal", "high"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON output."""
        return {
            "finding_id": self.finding_id,
            "tier_a_verdict": self.tier_a_verdict,
            "pattern": self.pattern,
            "severity": self.severity,
            "confidence": self.confidence,
            "complexity": self.complexity.value,
            "suggested_tier": self.suggested_tier.value,
            "analysis_type": self.analysis_type.value,
            "code_context": self.code_context,
            "evidence_summary": self.evidence_summary,
            "investigation_hints": self.investigation_hints,
            "estimated_tokens": self.estimated_tokens,
            "urgency": self.urgency,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class TierRouter:
    """
    Routes findings to appropriate model tiers based on complexity.

    This router provides hints for parent AI agents to select
    appropriate models. It does NOT call models directly.

    Example:
        >>> router = TierRouter()
        >>> context = router.create_context(finding)
        >>> print(f"Suggested tier: {context.suggested_tier}")
        >>> # Parent agent uses this to select model
    """

    def __init__(self, config: Optional[ModelTierConfig] = None):
        """
        Initialize tier router.

        Args:
            config: Optional tier configuration
        """
        self.config = config or ModelTierConfig()

    def estimate_complexity(self, finding: Any) -> Complexity:
        """
        Estimate the complexity of a finding for model selection.

        Args:
            finding: The finding to analyze

        Returns:
            Complexity level
        """
        pattern = getattr(finding, "pattern", "").lower()
        severity = getattr(finding, "severity", None)
        evidence = getattr(finding, "evidence", None)

        # Check for known high-complexity patterns
        for high_pattern in self.config.high_complexity_patterns:
            if high_pattern in pattern:
                return Complexity.HIGH

        # Check for known low-complexity patterns
        for low_pattern in self.config.low_complexity_patterns:
            if low_pattern in pattern:
                return Complexity.LOW

        # Check severity
        severity_str = getattr(severity, "value", str(severity)).lower() if severity else "medium"
        if severity_str in ["critical", "high"]:
            return Complexity.HIGH

        # Check evidence complexity
        if evidence:
            behavioral = getattr(evidence, "behavioral_signature", "")
            if behavioral and len(behavioral.split("→")) > 3:
                return Complexity.HIGH

        return Complexity.MEDIUM

    def determine_analysis_type(self, finding: Any) -> AnalysisType:
        """
        Determine the type of analysis needed.

        Args:
            finding: The finding to analyze

        Returns:
            Analysis type
        """
        pattern = getattr(finding, "pattern", "").lower()
        evidence = getattr(finding, "evidence", None)

        # Business logic patterns need deep analysis
        if any(p in pattern for p in ["business-logic", "economic", "governance"]):
            return AnalysisType.BUSINESS_LOGIC

        # Cross-contract patterns
        if any(p in pattern for p in ["cross-contract", "external-call", "flash-loan"]):
            return AnalysisType.CROSS_CONTRACT

        # Multi-function patterns
        if any(p in pattern for p in ["reentrancy", "state-manipulation"]):
            return AnalysisType.CROSS_FUNCTION

        # Check for behavioral evidence that suggests context needed
        if evidence:
            behavioral = getattr(evidence, "behavioral_signature", "")
            if behavioral and "→" in behavioral:
                return AnalysisType.CONTEXT_AWARE

        return AnalysisType.SIMPLE_CHECK

    def suggest_tier(
        self,
        complexity: Complexity,
        analysis_type: AnalysisType,
    ) -> ModelTier:
        """
        Suggest a model tier based on complexity and analysis type.

        Args:
            complexity: Finding complexity
            analysis_type: Type of analysis needed

        Returns:
            Suggested model tier
        """
        # Premium for business logic or cross-contract analysis
        if analysis_type in [AnalysisType.BUSINESS_LOGIC, AnalysisType.CROSS_CONTRACT]:
            return ModelTier.PREMIUM

        # Premium for critical complexity
        if complexity == Complexity.CRITICAL:
            return ModelTier.PREMIUM

        # Standard for high complexity or cross-function
        if complexity == Complexity.HIGH or analysis_type == AnalysisType.CROSS_FUNCTION:
            return ModelTier.STANDARD

        # Cheap for low complexity simple checks
        if complexity == Complexity.LOW and analysis_type == AnalysisType.SIMPLE_CHECK:
            return ModelTier.CHEAP

        # Default to standard
        return ModelTier.STANDARD

    def estimate_tokens(self, finding: Any, code_context: str = "") -> int:
        """
        Estimate tokens needed for analysis.

        Args:
            finding: The finding
            code_context: Code context string

        Returns:
            Estimated token count
        """
        base_tokens = 200  # Prompt overhead

        # Add context tokens
        if code_context:
            base_tokens += len(code_context.split()) * 2  # Rough estimate

        # Add pattern-specific estimate
        evidence = getattr(finding, "evidence", None)
        if evidence:
            snippet = getattr(evidence, "code_snippet", "")
            if snippet:
                base_tokens += len(snippet.split()) * 2

        return min(base_tokens, 4000)  # Cap at 4000

    def create_context(
        self,
        finding: Any,
        code_context: str = "",
    ) -> TierBContext:
        """
        Create Tier B context for a finding.

        Args:
            finding: The finding to create context for
            code_context: Optional code context

        Returns:
            TierBContext with all hints for parent agent
        """
        complexity = self.estimate_complexity(finding)
        analysis_type = self.determine_analysis_type(finding)
        suggested_tier = self.suggest_tier(complexity, analysis_type)
        estimated_tokens = self.estimate_tokens(finding, code_context)

        # Extract finding details
        evidence = getattr(finding, "evidence", None)
        evidence_summary = ""
        investigation_hints = []

        if evidence:
            behavioral = getattr(evidence, "behavioral_signature", "")
            if behavioral:
                evidence_summary = f"Behavioral: {behavioral}"

            why = getattr(evidence, "why_vulnerable", "")
            if why:
                investigation_hints.append(f"Initial assessment: {why}")

            props = getattr(evidence, "properties_matched", [])
            if props:
                investigation_hints.append(f"Properties: {', '.join(props[:3])}")

        # Determine urgency based on severity
        severity = getattr(finding, "severity", None)
        severity_str = getattr(severity, "value", str(severity)).lower() if severity else "medium"
        urgency = "high" if severity_str in ["critical", "high"] else "normal"

        # Get tier A verdict from confidence
        confidence = getattr(finding, "confidence", None)
        confidence_str = getattr(confidence, "value", str(confidence)).lower() if confidence else "medium"
        tier_a_verdict = {
            "high": "match",
            "medium": "possible",
            "low": "unlikely",
        }.get(confidence_str, "possible")

        return TierBContext(
            finding_id=getattr(finding, "id", "unknown"),
            tier_a_verdict=tier_a_verdict,
            pattern=getattr(finding, "pattern", "unknown"),
            severity=severity_str,
            confidence=confidence_str,
            complexity=complexity,
            suggested_tier=suggested_tier,
            analysis_type=analysis_type,
            code_context=code_context or self._get_default_context(finding),
            evidence_summary=evidence_summary,
            investigation_hints=investigation_hints,
            estimated_tokens=estimated_tokens,
            urgency=urgency,
        )

    def _get_default_context(self, finding: Any) -> str:
        """Get default code context from finding."""
        evidence = getattr(finding, "evidence", None)
        if evidence:
            snippet = getattr(evidence, "code_snippet", "")
            if snippet:
                return snippet

        location = getattr(finding, "location", None)
        if location:
            return f"// Location: {location}"

        return ""

    def batch_create_contexts(
        self,
        findings: list[Any],
    ) -> list[TierBContext]:
        """
        Create contexts for a batch of findings.

        Args:
            findings: List of findings

        Returns:
            List of TierBContext objects
        """
        return [self.create_context(f) for f in findings]


@dataclass
class TierStats:
    """Statistics for tier usage."""
    cheap_count: int = 0
    standard_count: int = 0
    premium_count: int = 0
    total_estimated_tokens: int = 0
    total_estimated_cost: float = 0.0

    def add_context(self, context: TierBContext, config: ModelTierConfig):
        """Add a context to stats."""
        if context.suggested_tier == ModelTier.CHEAP:
            self.cheap_count += 1
        elif context.suggested_tier == ModelTier.STANDARD:
            self.standard_count += 1
        else:
            self.premium_count += 1

        self.total_estimated_tokens += context.estimated_tokens

        # Estimate cost
        cost_weight = config.tier_cost_weights.get(context.suggested_tier, 1.0)
        self.total_estimated_cost += (context.estimated_tokens * 0.00001 * cost_weight)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        total = self.cheap_count + self.standard_count + self.premium_count
        return {
            "tier_distribution": {
                "cheap": self.cheap_count,
                "standard": self.standard_count,
                "premium": self.premium_count,
            },
            "tier_percentages": {
                "cheap": round(self.cheap_count / total * 100, 1) if total > 0 else 0,
                "standard": round(self.standard_count / total * 100, 1) if total > 0 else 0,
                "premium": round(self.premium_count / total * 100, 1) if total > 0 else 0,
            },
            "total_estimated_tokens": self.total_estimated_tokens,
            "total_estimated_cost_usd": round(self.total_estimated_cost, 4),
        }


def create_tier_router(config: Optional[ModelTierConfig] = None) -> TierRouter:
    """
    Factory function to create a tier router.

    Args:
        config: Optional configuration

    Returns:
        Configured TierRouter
    """
    return TierRouter(config=config)


class PolicyAwareTierRouter(TierRouter):
    """TierRouter extended with routing policy support.

    This router integrates with TierRoutingPolicy for cost-effective
    tier selection based on risk, evidence, and budget.

    Example:
        from alphaswarm_sol.llm.routing_policy import TierRoutingPolicy

        policy = TierRoutingPolicy()
        router = PolicyAwareTierRouter(policy=policy)

        # Route with policy
        decision = router.route_with_policy(
            task_type="tier_b_verification",
            risk_score=0.7,
            evidence_completeness=0.4,
        )
        print(f"Tier: {decision.tier}, Rationale: {decision.rationale}")
    """

    def __init__(
        self,
        config: Optional[ModelTierConfig] = None,
        policy: Optional[Any] = None,
    ):
        """Initialize policy-aware tier router.

        Args:
            config: Model tier configuration
            policy: TierRoutingPolicy instance (lazy import to avoid circular)
        """
        super().__init__(config=config)
        self._policy = policy

    @property
    def policy(self) -> Any:
        """Get or create routing policy."""
        if self._policy is None:
            from alphaswarm_sol.llm.routing_policy import TierRoutingPolicy
            self._policy = TierRoutingPolicy(tier_config=self.config)
        return self._policy

    def route_with_policy(
        self,
        task_type: str,
        risk_score: float = 0.0,
        evidence_completeness: float = 1.0,
        budget_remaining: Optional[float] = None,
        severity: Optional[str] = None,
        pattern_type: Optional[str] = None,
        pool_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ) -> Any:
        """Route a task using the routing policy.

        Args:
            task_type: Type of task
            risk_score: Risk score (0.0 - 1.0)
            evidence_completeness: Evidence completeness (0.0 - 1.0)
            budget_remaining: Remaining budget in USD
            severity: Severity level
            pattern_type: Pattern being analyzed
            pool_id: Pool ID for per-pool configuration
            workflow_id: Workflow ID for per-workflow configuration

        Returns:
            RoutingDecision from policy
        """
        return self.policy.route(
            task_type=task_type,
            risk_score=risk_score,
            evidence_completeness=evidence_completeness,
            budget_remaining=budget_remaining,
            severity=severity,
            pattern_type=pattern_type,
            pool_id=pool_id,
            workflow_id=workflow_id,
        )

    def suggest_tier_with_policy(
        self,
        finding: Any,
        budget_remaining: Optional[float] = None,
    ) -> tuple[ModelTier, Any]:
        """Suggest tier for a finding using both heuristics and policy.

        Combines the existing suggest_tier logic with policy-based routing.

        Args:
            finding: The finding to analyze
            budget_remaining: Remaining budget in USD

        Returns:
            Tuple of (ModelTier, RoutingDecision)
        """
        # Get heuristic-based suggestions
        complexity = self.estimate_complexity(finding)
        analysis_type = self.determine_analysis_type(finding)
        heuristic_tier = self.suggest_tier(complexity, analysis_type)

        # Extract finding metadata for policy routing
        pattern = getattr(finding, "pattern", "unknown")
        severity = getattr(finding, "severity", None)
        severity_str = getattr(severity, "value", str(severity)).lower() if severity else None

        # Calculate risk score from heuristics
        risk_score = 0.0
        if complexity in [Complexity.HIGH, Complexity.CRITICAL]:
            risk_score = 0.7 if complexity == Complexity.HIGH else 0.9
        elif heuristic_tier == ModelTier.PREMIUM:
            risk_score = 0.8

        # Estimate evidence completeness
        evidence = getattr(finding, "evidence", None)
        evidence_completeness = 0.5  # Default
        if evidence:
            props = getattr(evidence, "properties_matched", [])
            evidence_completeness = min(1.0, len(props) * 0.2) if props else 0.3

        # Route with policy
        decision = self.route_with_policy(
            task_type="tier_b_verification",
            risk_score=risk_score,
            evidence_completeness=evidence_completeness,
            budget_remaining=budget_remaining,
            severity=severity_str,
            pattern_type=pattern,
        )

        return decision.tier, decision


def create_policy_aware_router(
    config: Optional[ModelTierConfig] = None,
    policy: Optional[Any] = None,
) -> PolicyAwareTierRouter:
    """Factory function to create a policy-aware tier router.

    Args:
        config: Optional model tier configuration
        policy: Optional TierRoutingPolicy

    Returns:
        Configured PolicyAwareTierRouter
    """
    return PolicyAwareTierRouter(config=config, policy=policy)


def estimate_batch_tiers(
    findings: list[Any],
    config: Optional[ModelTierConfig] = None,
) -> TierStats:
    """
    Estimate tier distribution for a batch of findings.

    Args:
        findings: List of findings
        config: Optional configuration

    Returns:
        TierStats with distribution and cost estimates
    """
    router = TierRouter(config=config or ModelTierConfig())
    config = config or ModelTierConfig()
    stats = TierStats()

    for finding in findings:
        context = router.create_context(finding)
        stats.add_context(context, config)

    return stats
