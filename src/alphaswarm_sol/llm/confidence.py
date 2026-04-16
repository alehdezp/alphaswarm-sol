"""
Tier B Confidence Thresholds (Task 11.3) + Workflow Integrity Gates (Phase 5.11-03)

Manages confidence-based routing of findings to Tier B analysis.
Handles auto-confirm/dismiss logic for high/low confidence findings.

Phase 5.11-03: Workflow Integrity Gates
- Evidence gate: No confidence upgrade without evidence_refs
- Provenance gate: Only DECLARED expectations trigger misconfig findings
- Causal chain validation: root_cause -> exploit_steps -> financial_loss chain
- Unknown gate: Missing context forces unknown state

Rules enforced:
1. evidence_gate(): No confidence upgrade without evidence_refs
2. provenance_gate(): Misconfig findings require DECLARED provenance only
3. validate_causal_chain(): Complete causal chain required for confidence upgrade
4. stale_context_gate(): Stale context forces unknown or expansion

Usage:
    from alphaswarm_sol.llm.confidence import (
        evidence_gate,
        provenance_gate,
        validate_causal_chain,
        CausalChainValidator,
        ExpectationProvenance,
    )

    # Check evidence before upgrade
    if not evidence_gate(finding):
        # Block upgrade - no evidence_refs
        pass

    # Validate causal chain
    result = validate_causal_chain(vulnerability_id, chain_data)
    if not result.is_complete:
        # Incomplete chain - trigger gap nodes
        pass
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import logging

from alphaswarm_sol.findings.model import Finding, FindingConfidence

logger = logging.getLogger(__name__)


# =============================================================================
# Phase 5.11-03: Expectation Provenance Types
# =============================================================================


class ExpectationProvenance(str, Enum):
    """Provenance labels for expectations (per 05.11-CONTEXT.md).

    - DECLARED: Explicit in official docs/governance or on-chain config
    - INFERRED: Deduced from code + common patterns + risk heuristics
    - HYPOTHESIS: Plausible but unsupported; requires probe to confirm

    Rules:
    - Only DECLARED can trigger misconfig findings
    - INFERRED expectations emit warnings only
    - HYPOTHESIS triggers probes, not findings
    """

    DECLARED = "declared"
    INFERRED = "inferred"
    HYPOTHESIS = "hypothesis"

    def can_trigger_finding(self) -> bool:
        """Check if this provenance can trigger a misconfig finding."""
        return self == ExpectationProvenance.DECLARED

    def requires_probe(self) -> bool:
        """Check if this provenance requires a probe task."""
        return self == ExpectationProvenance.HYPOTHESIS


@dataclass
class ExpectationEvidence:
    """Evidence supporting an expectation.

    Per 05.11-CONTEXT.md, expectations must include source attribution.

    Attributes:
        source_id: Identifier for the source (doc ID, governance proposal, etc.)
        source_date: Date of the source document
        source_type: Type of source (docs, governance, on-chain, audit)
        provenance: DECLARED, INFERRED, or HYPOTHESIS
        confidence: Confidence in the expectation (0.0-1.0)
        scope: Scope of the expectation (protocol-wide, contract, function)
        conflict_flags: List of conflicting evidence if any
    """

    source_id: str
    source_date: str
    source_type: str  # "docs", "governance", "on_chain", "audit"
    provenance: ExpectationProvenance
    confidence: float = 0.8
    scope: str = "function"  # "protocol", "contract", "function"
    conflict_flags: List[str] = field(default_factory=list)

    def is_valid_for_finding(self) -> bool:
        """Check if this evidence can support a finding."""
        return self.provenance.can_trigger_finding() and self.confidence >= 0.5


# =============================================================================
# Phase 5.11-03: Causal Chain Validation
# =============================================================================


class CausalLinkType(str, Enum):
    """Types of links in a causal chain."""

    ROOT_CAUSE = "root_cause"
    EXPLOIT_STEP = "exploit_step"
    FINANCIAL_LOSS = "financial_loss"
    COUNTERFACTUAL = "counterfactual"  # Mitigation that would prevent


@dataclass
class CausalLink:
    """A single link in a causal chain.

    Attributes:
        link_type: Type of causal relationship
        source_id: ID of the source node (e.g., root cause ID)
        target_id: ID of the target node (e.g., exploit step ID)
        probability: Probability of this link (0.0-1.0)
        evidence_refs: References supporting this link
        description: Human-readable description
    """

    link_type: CausalLinkType
    source_id: str
    target_id: str
    probability: float = 0.5
    evidence_refs: List[str] = field(default_factory=list)
    description: str = ""

    def is_viable(self) -> bool:
        """Check if this link is viable (probability > 0.1)."""
        return self.probability > 0.1


@dataclass
class CausalChain:
    """Complete causal chain from root cause to financial loss.

    Per 05.11-03: A complete chain requires:
    - root_cause: The underlying vulnerability
    - exploit_steps: Steps to exploit the vulnerability
    - financial_loss: The resulting financial impact
    - counterfactuals: Mitigations that would prevent (optional but recorded)

    Attributes:
        vulnerability_id: ID of the vulnerability
        root_cause: Root cause link
        exploit_steps: List of exploit step links
        financial_loss: Financial loss link
        counterfactuals: Optional mitigation links
        chain_probability: Overall probability of the chain
    """

    vulnerability_id: str
    root_cause: Optional[CausalLink] = None
    exploit_steps: List[CausalLink] = field(default_factory=list)
    financial_loss: Optional[CausalLink] = None
    counterfactuals: List[CausalLink] = field(default_factory=list)
    chain_probability: float = 0.0

    def compute_probability(self) -> float:
        """Compute overall chain probability."""
        if not self.is_complete():
            return 0.0

        prob = self.root_cause.probability if self.root_cause else 0.0

        for step in self.exploit_steps:
            prob *= step.probability

        if self.financial_loss:
            prob *= self.financial_loss.probability

        self.chain_probability = prob
        return prob

    def is_complete(self) -> bool:
        """Check if the causal chain is complete."""
        return (
            self.root_cause is not None
            and len(self.exploit_steps) > 0
            and self.financial_loss is not None
        )

    def is_viable(self) -> bool:
        """Check if the chain is viable (probability > 0.1)."""
        return self.compute_probability() > 0.1

    def get_missing_links(self) -> List[CausalLinkType]:
        """Get list of missing link types."""
        missing = []
        if self.root_cause is None:
            missing.append(CausalLinkType.ROOT_CAUSE)
        if not self.exploit_steps:
            missing.append(CausalLinkType.EXPLOIT_STEP)
        if self.financial_loss is None:
            missing.append(CausalLinkType.FINANCIAL_LOSS)
        return missing


@dataclass
class CausalChainValidationResult:
    """Result of causal chain validation.

    Attributes:
        vulnerability_id: ID of the vulnerability
        is_complete: Whether the chain is complete
        is_viable: Whether the chain is viable (prob > 0.1)
        missing_links: List of missing link types
        chain_probability: Overall chain probability
        gap_nodes_needed: List of gap node IDs to create
        errors: Validation error messages
        warnings: Validation warning messages
    """

    vulnerability_id: str
    is_complete: bool = False
    is_viable: bool = False
    missing_links: List[CausalLinkType] = field(default_factory=list)
    chain_probability: float = 0.0
    gap_nodes_needed: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def allows_confidence_upgrade(self) -> bool:
        """Check if this result allows confidence upgrade."""
        return self.is_complete and self.is_viable and len(self.errors) == 0


class CausalChainValidator:
    """Validates causal chains for vulnerability findings.

    Per 05.11-03: Incomplete chains trigger gap graph nodes
    and block confidence upgrades.

    Usage:
        validator = CausalChainValidator()
        result = validator.validate(chain)

        if not result.allows_confidence_upgrade():
            # Block upgrade, create gap nodes
            for gap_id in result.gap_nodes_needed:
                create_gap_node(gap_id)
    """

    # Minimum probability threshold for viable chains
    MIN_CHAIN_PROBABILITY = 0.1

    def validate(self, chain: CausalChain) -> CausalChainValidationResult:
        """Validate a causal chain.

        Args:
            chain: CausalChain to validate

        Returns:
            CausalChainValidationResult with validation status
        """
        result = CausalChainValidationResult(vulnerability_id=chain.vulnerability_id)

        # Check completeness
        missing = chain.get_missing_links()
        result.missing_links = missing
        result.is_complete = len(missing) == 0

        if not result.is_complete:
            result.errors.append(
                f"Incomplete causal chain: missing {[m.value for m in missing]}"
            )
            # Create gap node IDs for missing links
            for link_type in missing:
                gap_id = f"gap:{chain.vulnerability_id}:{link_type.value}"
                result.gap_nodes_needed.append(gap_id)

        # Check viability
        result.chain_probability = chain.compute_probability()
        result.is_viable = result.chain_probability > self.MIN_CHAIN_PROBABILITY

        if result.is_complete and not result.is_viable:
            result.warnings.append(
                f"Low probability chain ({result.chain_probability:.2%}), may need expansion"
            )

        # Validate individual links
        if chain.root_cause and not chain.root_cause.evidence_refs:
            result.warnings.append("Root cause has no evidence references")

        for i, step in enumerate(chain.exploit_steps):
            if not step.is_viable():
                result.warnings.append(
                    f"Exploit step {i + 1} has low probability ({step.probability:.2%})"
                )

        return result

    def validate_root_cause_attribution(
        self,
        vulnerability_id: str,
        finding_data: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """Validate that a finding has proper root cause attribution.

        Per 05.11-03: Every finding must link to a root cause node.

        Args:
            vulnerability_id: ID of the vulnerability
            finding_data: Finding data dict

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Check for root_cause field
        root_cause = finding_data.get("root_cause")
        if not root_cause:
            errors.append(f"Finding {vulnerability_id} has no root_cause attribution")
            return False, errors

        # Check for evidence in root cause
        if isinstance(root_cause, dict):
            if not root_cause.get("evidence_refs"):
                errors.append(f"Root cause for {vulnerability_id} has no evidence_refs")
                return False, errors

        return True, errors


# =============================================================================
# Phase 5.11-03: Integrity Gates
# =============================================================================


def evidence_gate(finding: Finding) -> bool:
    """Check if finding has sufficient evidence for confidence upgrade.

    Per 05.11-03: No confidence upgrade without evidence_refs.

    Args:
        finding: Finding to check

    Returns:
        True if finding has evidence, False otherwise
    """
    if not finding.evidence:
        logger.debug(f"Evidence gate: {finding.id} has no evidence object")
        return False

    # Check for evidence_refs
    if finding.evidence.evidence_refs and len(finding.evidence.evidence_refs) > 0:
        return True

    # Fall back to behavioral evidence
    if finding.evidence.has_behavioral_evidence():
        return True

    logger.debug(f"Evidence gate: {finding.id} has no evidence_refs or behavioral evidence")
    return False


def provenance_gate(
    finding: Finding,
    expectation_evidence: Optional[ExpectationEvidence] = None,
    is_misconfig_finding: bool = False,
) -> Tuple[bool, str]:
    """Check if finding meets provenance requirements.

    Per 05.11-03:
    - Misconfig findings require DECLARED provenance only
    - INFERRED expectations emit warnings only
    - HYPOTHESIS expectations trigger probes, not findings

    Args:
        finding: Finding to check
        expectation_evidence: Evidence for the expectation
        is_misconfig_finding: Whether this is a misconfiguration finding

    Returns:
        Tuple of (passes_gate, warning_message)
    """
    if not is_misconfig_finding:
        # Non-misconfig findings don't require specific provenance
        return True, ""

    if expectation_evidence is None:
        return False, "Misconfig finding requires expectation evidence"

    if expectation_evidence.provenance == ExpectationProvenance.DECLARED:
        return True, ""

    if expectation_evidence.provenance == ExpectationProvenance.INFERRED:
        return False, f"Inferred expectation cannot trigger misconfig finding (emit warning only): {expectation_evidence.source_id}"

    if expectation_evidence.provenance == ExpectationProvenance.HYPOTHESIS:
        return False, f"Hypothesis expectation triggers probe, not finding: {expectation_evidence.source_id}"

    return False, "Unknown provenance type"


def stale_context_gate(
    context_last_verified: Optional[str],
    max_age_days: int = 90,
) -> Tuple[bool, str]:
    """Check if context is stale.

    Per 05.11-03: Stale context forces unknown state or expansion.

    Args:
        context_last_verified: ISO timestamp of last verification
        max_age_days: Maximum age in days before context is stale

    Returns:
        Tuple of (is_fresh, message)
    """
    if context_last_verified is None:
        return False, "No context verification date - context is stale"

    try:
        verified_dt = datetime.fromisoformat(context_last_verified.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        age_days = (now - verified_dt).days

        if age_days > max_age_days:
            return False, f"Context is {age_days} days old (max: {max_age_days}) - stale"

        return True, f"Context is {age_days} days old - fresh"
    except (ValueError, AttributeError) as e:
        return False, f"Invalid verification date: {e}"


def validate_causal_chain(
    vulnerability_id: str,
    chain_data: Optional[Dict[str, Any]] = None,
) -> CausalChainValidationResult:
    """Validate causal chain for a vulnerability.

    Convenience function wrapping CausalChainValidator.

    Args:
        vulnerability_id: ID of the vulnerability
        chain_data: Optional dict with chain data

    Returns:
        CausalChainValidationResult
    """
    if chain_data is None:
        # No chain data - return incomplete result
        result = CausalChainValidationResult(vulnerability_id=vulnerability_id)
        result.errors.append("No causal chain data provided")
        result.missing_links = list(CausalLinkType)[:3]  # root_cause, exploit_step, financial_loss
        result.gap_nodes_needed = [
            f"gap:{vulnerability_id}:root_cause",
            f"gap:{vulnerability_id}:exploit_step",
            f"gap:{vulnerability_id}:financial_loss",
        ]
        return result

    # Build chain from data
    chain = CausalChain(vulnerability_id=vulnerability_id)

    # Parse root cause
    if "root_cause" in chain_data:
        rc = chain_data["root_cause"]
        chain.root_cause = CausalLink(
            link_type=CausalLinkType.ROOT_CAUSE,
            source_id=vulnerability_id,
            target_id=rc.get("id", "unknown"),
            probability=rc.get("probability", 0.5),
            evidence_refs=rc.get("evidence_refs", []),
            description=rc.get("description", ""),
        )

    # Parse exploit steps
    for step in chain_data.get("exploit_steps", []):
        chain.exploit_steps.append(
            CausalLink(
                link_type=CausalLinkType.EXPLOIT_STEP,
                source_id=step.get("source_id", ""),
                target_id=step.get("target_id", ""),
                probability=step.get("probability", 0.5),
                evidence_refs=step.get("evidence_refs", []),
                description=step.get("description", ""),
            )
        )

    # Parse financial loss
    if "financial_loss" in chain_data:
        fl = chain_data["financial_loss"]
        chain.financial_loss = CausalLink(
            link_type=CausalLinkType.FINANCIAL_LOSS,
            source_id=fl.get("source_id", ""),
            target_id=fl.get("target_id", "financial_impact"),
            probability=fl.get("probability", 0.5),
            evidence_refs=fl.get("evidence_refs", []),
            description=fl.get("description", ""),
        )

    # Parse counterfactuals
    for cf in chain_data.get("counterfactuals", []):
        chain.counterfactuals.append(
            CausalLink(
                link_type=CausalLinkType.COUNTERFACTUAL,
                source_id=cf.get("source_id", ""),
                target_id=cf.get("target_id", ""),
                probability=cf.get("probability", 0.9),
                evidence_refs=cf.get("evidence_refs", []),
                description=cf.get("description", ""),
            )
        )

    validator = CausalChainValidator()
    return validator.validate(chain)


# =============================================================================
# Original Confidence Action Types
# =============================================================================


class ConfidenceAction(str, Enum):
    """Action to take based on confidence level."""
    AUTO_CONFIRM = "auto_confirm"  # High confidence, skip Tier B
    AUTO_DISMISS = "auto_dismiss"  # Low confidence, skip Tier B
    ANALYZE = "analyze"            # Middle range, send to Tier B


@dataclass
class ConfidenceThresholds:
    """Configurable confidence thresholds for Tier B routing."""

    # Numeric confidence >= this value auto-confirms (skips Tier B)
    auto_confirm_threshold: float = 0.9

    # Numeric confidence <= this value auto-dismisses (skips Tier B)
    auto_dismiss_threshold: float = 0.3

    # Require evidence for auto-confirm
    require_evidence_for_confirm: bool = True

    # Pattern categories that always go to Tier B regardless of confidence
    always_analyze_patterns: list[str] = None

    def __post_init__(self):
        if self.always_analyze_patterns is None:
            self.always_analyze_patterns = [
                "business-logic",
                "access-control",
                "economic",
            ]


# Default thresholds
DEFAULT_THRESHOLDS = ConfidenceThresholds()


# Mapping from FindingConfidence enum to numeric values
CONFIDENCE_TO_NUMERIC = {
    FindingConfidence.HIGH: 0.85,
    FindingConfidence.MEDIUM: 0.60,
    FindingConfidence.LOW: 0.35,
}


@dataclass
class ConfidenceResult:
    """Result of confidence evaluation."""
    action: ConfidenceAction
    numeric_confidence: float
    reason: str
    skip_tier_b: bool

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "action": self.action.value,
            "numeric_confidence": self.numeric_confidence,
            "reason": self.reason,
            "skip_tier_b": self.skip_tier_b,
        }


class ConfidenceEvaluator:
    """
    Evaluates finding confidence and determines Tier B routing.

    The workflow is:
    1. Convert FindingConfidence enum to numeric (0.0 - 1.0)
    2. Apply adjustments based on evidence quality
    3. Check against thresholds
    4. Return action: AUTO_CONFIRM, AUTO_DISMISS, or ANALYZE
    """

    def __init__(self, thresholds: Optional[ConfidenceThresholds] = None):
        """
        Initialize evaluator.

        Args:
            thresholds: Custom thresholds (uses defaults if None)
        """
        self.thresholds = thresholds or DEFAULT_THRESHOLDS

    def evaluate(self, finding: Finding) -> ConfidenceResult:
        """
        Evaluate finding confidence and determine Tier B routing.

        Args:
            finding: The finding to evaluate

        Returns:
            ConfidenceResult with action and reasoning
        """
        # Convert enum to numeric
        base_confidence = self._get_numeric_confidence(finding)

        # Apply adjustments
        adjusted = self._apply_adjustments(finding, base_confidence)

        # Determine action
        return self._determine_action(finding, adjusted)

    def _get_numeric_confidence(self, finding: Finding) -> float:
        """Convert FindingConfidence enum to numeric value."""
        return CONFIDENCE_TO_NUMERIC.get(finding.confidence, 0.60)

    def _apply_adjustments(self, finding: Finding, base: float) -> float:
        """
        Apply confidence adjustments based on evidence quality.

        Boosts confidence if:
        - Has behavioral evidence (+0.05)
        - Has attack context (+0.05)
        - Has complete evidence (+0.05)

        Reduces confidence if:
        - No code snippet (-0.05)
        - No behavioral signature (-0.10)
        """
        adjusted = base

        evidence = finding.evidence

        # Boosts
        if evidence.has_behavioral_evidence():
            adjusted += 0.05
        if evidence.has_attack_context():
            adjusted += 0.05
        if evidence.is_complete():
            adjusted += 0.05

        # Reductions
        if not evidence.code_snippet and not evidence.evidence_refs:
            adjusted -= 0.05
        if not evidence.behavioral_signature and not evidence.operations:
            adjusted -= 0.10

        # Clamp to [0, 1]
        return max(0.0, min(1.0, adjusted))

    def _determine_action(
        self, finding: Finding, confidence: float
    ) -> ConfidenceResult:
        """
        Determine action based on confidence and thresholds.

        Args:
            finding: The finding
            confidence: Adjusted numeric confidence

        Returns:
            ConfidenceResult with determined action
        """
        # Check for always-analyze patterns
        pattern_lower = finding.pattern.lower()
        for always_pattern in self.thresholds.always_analyze_patterns:
            if always_pattern in pattern_lower:
                return ConfidenceResult(
                    action=ConfidenceAction.ANALYZE,
                    numeric_confidence=confidence,
                    reason=f"Pattern '{finding.pattern}' always requires Tier B analysis",
                    skip_tier_b=False,
                )

        # Check auto-confirm threshold
        if confidence >= self.thresholds.auto_confirm_threshold:
            # Verify evidence if required
            if self.thresholds.require_evidence_for_confirm:
                if not finding.evidence.has_behavioral_evidence():
                    return ConfidenceResult(
                        action=ConfidenceAction.ANALYZE,
                        numeric_confidence=confidence,
                        reason="High confidence but lacks behavioral evidence",
                        skip_tier_b=False,
                    )

            return ConfidenceResult(
                action=ConfidenceAction.AUTO_CONFIRM,
                numeric_confidence=confidence,
                reason=f"Confidence {confidence:.2f} >= {self.thresholds.auto_confirm_threshold} threshold",
                skip_tier_b=True,
            )

        # Check auto-dismiss threshold
        if confidence <= self.thresholds.auto_dismiss_threshold:
            return ConfidenceResult(
                action=ConfidenceAction.AUTO_DISMISS,
                numeric_confidence=confidence,
                reason=f"Confidence {confidence:.2f} <= {self.thresholds.auto_dismiss_threshold} threshold",
                skip_tier_b=True,
            )

        # Middle range - send to Tier B
        return ConfidenceResult(
            action=ConfidenceAction.ANALYZE,
            numeric_confidence=confidence,
            reason=f"Confidence {confidence:.2f} in analysis range ({self.thresholds.auto_dismiss_threshold}-{self.thresholds.auto_confirm_threshold})",
            skip_tier_b=False,
        )

    def batch_evaluate(
        self, findings: list[Finding]
    ) -> dict:
        """
        Evaluate a batch of findings and return statistics.

        Args:
            findings: List of findings

        Returns:
            Dict with results and statistics
        """
        results = []
        stats = {
            "total": len(findings),
            "auto_confirm": 0,
            "auto_dismiss": 0,
            "analyze": 0,
            "tier_b_required": 0,
        }

        for finding in findings:
            result = self.evaluate(finding)
            results.append({
                "finding_id": finding.id,
                "result": result,
            })

            stats[result.action.value] += 1
            if not result.skip_tier_b:
                stats["tier_b_required"] += 1

        # Calculate percentages
        total = stats["total"]
        if total > 0:
            stats["auto_confirm_pct"] = stats["auto_confirm"] / total * 100
            stats["auto_dismiss_pct"] = stats["auto_dismiss"] / total * 100
            stats["analyze_pct"] = stats["analyze"] / total * 100
            stats["tier_b_pct"] = stats["tier_b_required"] / total * 100

        return {
            "results": results,
            "stats": stats,
        }


def evaluate_confidence(
    finding: Finding,
    thresholds: Optional[ConfidenceThresholds] = None,
) -> ConfidenceResult:
    """
    Convenience function to evaluate finding confidence.

    Args:
        finding: The finding to evaluate
        thresholds: Optional custom thresholds

    Returns:
        ConfidenceResult with action and reasoning
    """
    evaluator = ConfidenceEvaluator(thresholds)
    return evaluator.evaluate(finding)


def needs_tier_b_analysis(
    finding: Finding,
    thresholds: Optional[ConfidenceThresholds] = None,
) -> bool:
    """
    Quick check if a finding needs Tier B analysis.

    Args:
        finding: The finding to check
        thresholds: Optional custom thresholds

    Returns:
        True if Tier B analysis is needed
    """
    result = evaluate_confidence(finding, thresholds)
    return not result.skip_tier_b


# =============================================================================
# Phase 5.11-03: Module Exports
# =============================================================================

__all__ = [
    # Original exports
    "ConfidenceAction",
    "ConfidenceThresholds",
    "DEFAULT_THRESHOLDS",
    "CONFIDENCE_TO_NUMERIC",
    "ConfidenceResult",
    "ConfidenceEvaluator",
    "evaluate_confidence",
    "needs_tier_b_analysis",
    # Phase 5.11-03: Expectation Provenance
    "ExpectationProvenance",
    "ExpectationEvidence",
    # Phase 5.11-03: Causal Chain Validation
    "CausalLinkType",
    "CausalLink",
    "CausalChain",
    "CausalChainValidationResult",
    "CausalChainValidator",
    # Phase 5.11-03: Integrity Gates
    "evidence_gate",
    "provenance_gate",
    "stale_context_gate",
    "validate_causal_chain",
]
