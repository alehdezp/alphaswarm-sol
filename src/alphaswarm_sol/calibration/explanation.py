"""Task 14.6: Confidence Explanation Generator.

Generates human-readable explanations for calibrated confidence values,
helping users understand why a finding has a particular confidence level.

Philosophy:
- Transparency builds trust in automated findings
- Explain both the evidence FOR and AGAINST
- Reference specific code patterns and guards
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from alphaswarm_sol.calibration.context import ContextResult, GUARD_MULTIPLIERS
from alphaswarm_sol.calibration.calibrator import CalibrationResult, CalibrationMethod


# Confidence level thresholds and descriptions
CONFIDENCE_LEVELS = {
    "critical": (0.90, 1.00, "Very high confidence - strong evidence of vulnerability"),
    "high": (0.70, 0.90, "High confidence - likely a real vulnerability"),
    "medium": (0.50, 0.70, "Medium confidence - requires manual review"),
    "low": (0.30, 0.50, "Low confidence - possible false positive"),
    "very_low": (0.00, 0.30, "Very low confidence - likely false positive"),
}


# Pattern-specific descriptions
PATTERN_DESCRIPTIONS: Dict[str, str] = {
    "vm-001": "Classic reentrancy vulnerability where external calls occur before state updates",
    "vm-002": "Read-only reentrancy where view functions read stale state during reentrant call",
    "vm-003": "Cross-function reentrancy exploiting shared state across multiple functions",
    "auth-001": "Missing access control on state-modifying function",
    "auth-002": "Weak access control using tx.origin instead of msg.sender",
    "auth-003": "Missing owner check on privileged operation",
    "oracle-001": "Missing staleness check on oracle price data",
    "oracle-002": "Missing sequencer uptime check for L2 oracles",
    "dos-001": "Unbounded loop that could cause out-of-gas",
    "dos-002": "External calls in loop creating DoS vector",
    "mev-001": "Missing slippage protection on swap operation",
    "mev-002": "Missing deadline check allowing transaction delay attacks",
    "crypto-001": "Signature malleability - missing s-value check",
    "crypto-002": "Missing zero-address check on ecrecover result",
    "upgrade-001": "Missing initializer guard in upgradeable contract",
    "upgrade-002": "Storage collision risk in proxy pattern",
}


@dataclass
class ConfidenceExplanation:
    """Structured explanation of a confidence value."""

    confidence: float
    level: str
    level_description: str
    pattern_id: str
    pattern_description: str

    # Evidence components
    positive_factors: List[str] = field(default_factory=list)  # Why it might be a vuln
    negative_factors: List[str] = field(default_factory=list)  # Why it might not be
    context_adjustments: List[str] = field(default_factory=list)  # Guard effects

    # Calibration info
    calibration_method: str = "bayesian"
    sample_basis: str = ""  # "Based on N samples from benchmarks"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "confidence": round(self.confidence, 4),
            "level": self.level,
            "level_description": self.level_description,
            "pattern_id": self.pattern_id,
            "pattern_description": self.pattern_description,
            "positive_factors": self.positive_factors,
            "negative_factors": self.negative_factors,
            "context_adjustments": self.context_adjustments,
            "calibration_method": self.calibration_method,
            "sample_basis": self.sample_basis,
        }

    def to_markdown(self) -> str:
        """Generate markdown-formatted explanation."""
        lines = [
            f"## Confidence: {self.confidence:.1%} ({self.level.upper()})",
            "",
            f"*{self.level_description}*",
            "",
            f"### Pattern: {self.pattern_id}",
            self.pattern_description,
            "",
        ]

        if self.positive_factors:
            lines.append("### Evidence FOR vulnerability:")
            for factor in self.positive_factors:
                lines.append(f"- {factor}")
            lines.append("")

        if self.negative_factors:
            lines.append("### Evidence AGAINST vulnerability:")
            for factor in self.negative_factors:
                lines.append(f"- {factor}")
            lines.append("")

        if self.context_adjustments:
            lines.append("### Context adjustments:")
            for adj in self.context_adjustments:
                lines.append(f"- {adj}")
            lines.append("")

        if self.sample_basis:
            lines.append(f"*{self.sample_basis}*")

        return "\n".join(lines)

    def to_text(self) -> str:
        """Generate plain text explanation."""
        lines = [
            f"Confidence: {self.confidence:.1%} ({self.level.upper()})",
            self.level_description,
            "",
            f"Pattern: {self.pattern_id}",
            self.pattern_description,
        ]

        if self.positive_factors:
            lines.append("\nEvidence FOR:")
            for factor in self.positive_factors:
                lines.append(f"  + {factor}")

        if self.negative_factors:
            lines.append("\nEvidence AGAINST:")
            for factor in self.negative_factors:
                lines.append(f"  - {factor}")

        if self.context_adjustments:
            lines.append("\nContext adjustments:")
            for adj in self.context_adjustments:
                lines.append(f"  * {adj}")

        if self.sample_basis:
            lines.append(f"\n{self.sample_basis}")

        return "\n".join(lines)


class ConfidenceExplainer:
    """Generate explanations for calibrated confidence values.

    Example:
        explainer = ConfidenceExplainer()

        explanation = explainer.explain(
            confidence=0.75,
            pattern_id="vm-001-classic",
            positive_evidence=["External call before state update"],
            negative_evidence=["Function is internal"],
            context_result=context_result,
            calibration_result=calibration_result,
        )

        print(explanation.to_markdown())
    """

    def __init__(
        self,
        pattern_descriptions: Optional[Dict[str, str]] = None,
        custom_levels: Optional[Dict[str, tuple]] = None,
    ):
        """Initialize explainer.

        Args:
            pattern_descriptions: Custom pattern descriptions
            custom_levels: Custom confidence level thresholds
        """
        self._patterns = {**PATTERN_DESCRIPTIONS, **(pattern_descriptions or {})}
        self._levels = custom_levels or CONFIDENCE_LEVELS

    def explain(
        self,
        confidence: float,
        pattern_id: str,
        positive_evidence: Optional[List[str]] = None,
        negative_evidence: Optional[List[str]] = None,
        context_result: Optional[ContextResult] = None,
        calibration_result: Optional[CalibrationResult] = None,
        sample_size: int = 0,
    ) -> ConfidenceExplanation:
        """Generate explanation for a confidence value.

        Args:
            confidence: Calibrated confidence value
            pattern_id: Pattern identifier
            positive_evidence: Evidence supporting vulnerability
            negative_evidence: Evidence against vulnerability
            context_result: Result of context factor adjustments
            calibration_result: Result of calibration
            sample_size: Number of samples used for calibration

        Returns:
            ConfidenceExplanation with detailed breakdown
        """
        # Determine confidence level
        level, level_desc = self._get_level(confidence)

        # Get pattern description
        pattern_desc = self._get_pattern_description(pattern_id)

        # Build positive factors
        positive_factors = list(positive_evidence or [])
        if not positive_factors:
            positive_factors = self._infer_positive_factors(pattern_id)

        # Build negative factors
        negative_factors = list(negative_evidence or [])

        # Extract context adjustments
        context_adjustments = []
        if context_result and context_result.factors_applied:
            for adj in context_result.factors_applied:
                effect = "reduces" if adj.multiplier < 1.0 else "increases"
                pct = abs(1.0 - adj.multiplier) * 100
                context_adjustments.append(
                    f"{adj.factor_name} {effect} confidence by {pct:.0f}% ({adj.reason})"
                )

        # Determine calibration method
        cal_method = "bayesian"
        if calibration_result:
            cal_method = calibration_result.method_used.value

        # Sample basis text
        sample_basis = ""
        if sample_size > 0:
            sample_basis = f"Calibrated using {sample_size} labeled samples from benchmark data"
        elif calibration_result and calibration_result.bounds_used:
            bounds = calibration_result.bounds_used
            if bounds.sample_size and bounds.sample_size > 0:
                sample_basis = f"Calibrated using {bounds.sample_size} samples (precision: {bounds.observed_precision:.1%})"

        return ConfidenceExplanation(
            confidence=confidence,
            level=level,
            level_description=level_desc,
            pattern_id=pattern_id,
            pattern_description=pattern_desc,
            positive_factors=positive_factors,
            negative_factors=negative_factors,
            context_adjustments=context_adjustments,
            calibration_method=cal_method,
            sample_basis=sample_basis,
        )

    def _get_level(self, confidence: float) -> tuple[str, str]:
        """Get confidence level and description."""
        for level_name, (low, high, desc) in self._levels.items():
            if low <= confidence < high or (level_name == "critical" and confidence >= high):
                return level_name, desc
        return "unknown", "Confidence level not determined"

    def _get_pattern_description(self, pattern_id: str) -> str:
        """Get description for a pattern."""
        # Try exact match
        if pattern_id in self._patterns:
            return self._patterns[pattern_id]

        # Try prefix match (e.g., "vm-001-classic" -> "vm-001")
        for prefix, desc in self._patterns.items():
            if pattern_id.startswith(prefix):
                return desc

        return f"Vulnerability pattern: {pattern_id}"

    def _infer_positive_factors(self, pattern_id: str) -> List[str]:
        """Infer positive evidence based on pattern type."""
        factors = []

        pid_lower = pattern_id.lower()

        if "reentrancy" in pid_lower or "vm-001" in pid_lower or "vm-002" in pid_lower:
            factors.append("External call detected before state update")
            factors.append("No reentrancy guard found")
        elif "auth" in pid_lower:
            factors.append("State modification without access control")
            factors.append("Function is externally callable")
        elif "oracle" in pid_lower:
            factors.append("Oracle price read without validation")
        elif "dos" in pid_lower:
            factors.append("Loop with potentially unbounded iterations")
        elif "mev" in pid_lower or "slippage" in pid_lower:
            factors.append("Swap operation without slippage protection")
        elif "crypto" in pid_lower or "signature" in pid_lower:
            factors.append("Signature validation without malleability checks")
        elif "upgrade" in pid_lower or "proxy" in pid_lower:
            factors.append("Upgradeable contract without proper initialization guards")

        return factors if factors else ["Pattern match found in code"]

    def add_pattern_description(self, pattern_id: str, description: str) -> None:
        """Add or update a pattern description."""
        self._patterns[pattern_id] = description

    def available_patterns(self) -> Set[str]:
        """Get all patterns with descriptions."""
        return set(self._patterns.keys())


def explain_confidence(
    confidence: float,
    pattern_id: str,
    positive_evidence: Optional[List[str]] = None,
    negative_evidence: Optional[List[str]] = None,
    context_result: Optional[ContextResult] = None,
    calibration_result: Optional[CalibrationResult] = None,
) -> ConfidenceExplanation:
    """Convenience function to generate confidence explanation.

    Args:
        confidence: Calibrated confidence value
        pattern_id: Pattern identifier
        positive_evidence: Evidence supporting vulnerability
        negative_evidence: Evidence against vulnerability
        context_result: Context factor adjustments
        calibration_result: Calibration details

    Returns:
        ConfidenceExplanation
    """
    explainer = ConfidenceExplainer()
    return explainer.explain(
        confidence=confidence,
        pattern_id=pattern_id,
        positive_evidence=positive_evidence,
        negative_evidence=negative_evidence,
        context_result=context_result,
        calibration_result=calibration_result,
    )


def format_explanation(
    explanation: ConfidenceExplanation,
    format: str = "text",
) -> str:
    """Format explanation for output.

    Args:
        explanation: ConfidenceExplanation to format
        format: Output format ("text", "markdown", "json")

    Returns:
        Formatted string
    """
    if format == "markdown":
        return explanation.to_markdown()
    elif format == "json":
        import json
        return json.dumps(explanation.to_dict(), indent=2)
    else:
        return explanation.to_text()


def generate_finding_explanation(
    finding: Dict[str, Any],
    calibration_result: Optional[CalibrationResult] = None,
    context_result: Optional[ContextResult] = None,
) -> ConfidenceExplanation:
    """Generate explanation from a finding dictionary.

    Args:
        finding: Finding dictionary with pattern_id, confidence, etc.
        calibration_result: Optional calibration result
        context_result: Optional context adjustments

    Returns:
        ConfidenceExplanation
    """
    pattern_id = finding.get("pattern_id", finding.get("pattern", "unknown"))
    confidence = finding.get("calibrated_confidence", finding.get("confidence", 0.5))

    # Extract evidence from finding
    positive = []
    negative = []

    if "evidence" in finding:
        for ev in finding.get("evidence", []):
            if isinstance(ev, dict):
                positive.append(ev.get("description", str(ev)))
            else:
                positive.append(str(ev))

    if "mitigations" in finding:
        for mit in finding.get("mitigations", []):
            negative.append(str(mit))

    if "guards_present" in finding:
        for guard in finding.get("guards_present", []):
            negative.append(f"Guard present: {guard}")

    return explain_confidence(
        confidence=confidence,
        pattern_id=pattern_id,
        positive_evidence=positive if positive else None,
        negative_evidence=negative if negative else None,
        context_result=context_result,
        calibration_result=calibration_result,
    )
