"""Economic Rationality Gate for vulnerability filtering (Phase 5.11-03).

Per 05.11-CONTEXT.md: Economic rationality filtering based on game-theoretic analysis.
Filters vulnerabilities with negative expected value to reduce false positive noise.

The rationality gate computes expected profit for an attacker and deprioritizes
(not hides) vulnerabilities that are economically irrational to exploit.

Components:
- RationalityGate: Evaluates attack EV using PayoffMatrix
- EVThreshold: Configurable thresholds for filtering and escalation
- filter_by_economic_rationality(): Filters vulnerability list by positive EV

Rules:
- EV < filter_threshold: Deprioritize (add flag, don't hide)
- EV > escalation_threshold: Mark as critical priority
- Always log filtered vulnerabilities for transparency

Usage:
    from alphaswarm_sol.economics.rationality_gate import (
        RationalityGate,
        EVThreshold,
        filter_by_economic_rationality,
    )

    gate = RationalityGate()

    # Evaluate a single vulnerability
    result = gate.evaluate_attack_ev(vulnerability, protocol_state)
    if result.is_economically_rational:
        # Prioritize for verification
        pass
    else:
        # Deprioritize (but don't hide)
        pass

    # Filter a list of vulnerabilities
    rational, deprioritized = filter_by_economic_rationality(vulnerabilities, protocol_state)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import logging

from .payoff import AttackPayoff, DefensePayoff, PayoffMatrix

logger = logging.getLogger(__name__)


# =============================================================================
# EV Threshold Configuration
# =============================================================================


@dataclass
class EVThreshold:
    """Configurable thresholds for economic rationality filtering.

    Per 05.11-03:
    - filter_threshold: EV below which vulnerabilities are deprioritized
    - escalation_threshold: EV above which vulnerabilities are critical

    Default:
    - Filter if EV < 0 (economically irrational to exploit)
    - Escalate if EV > 10 ETH equivalent (~$30,000 USD at typical prices)

    Attributes:
        filter_threshold_usd: EV below this is deprioritized (default: 0)
        escalation_threshold_usd: EV above this is critical (default: 30000 USD)
        min_success_probability: Minimum success prob to consider (default: 0.1)
        max_gas_cost_fraction: Max gas cost as fraction of profit (default: 0.5)
    """

    filter_threshold_usd: float = 0.0
    escalation_threshold_usd: float = 30000.0  # ~10 ETH equivalent
    min_success_probability: float = 0.1
    max_gas_cost_fraction: float = 0.5

    def is_below_filter(self, ev_usd: float) -> bool:
        """Check if EV is below filter threshold."""
        return ev_usd < self.filter_threshold_usd

    def is_above_escalation(self, ev_usd: float) -> bool:
        """Check if EV is above escalation threshold."""
        return ev_usd > self.escalation_threshold_usd

    def get_priority_bucket(self, ev_usd: float) -> str:
        """Get priority bucket based on EV.

        Returns:
            "critical", "high", "medium", "low", or "deprioritized"
        """
        if ev_usd < self.filter_threshold_usd:
            return "deprioritized"
        elif ev_usd > self.escalation_threshold_usd:
            return "critical"
        elif ev_usd > self.escalation_threshold_usd * 0.3:  # 30% of escalation
            return "high"
        elif ev_usd > 0:
            return "medium"
        else:
            return "low"


# Default thresholds
DEFAULT_EV_THRESHOLD = EVThreshold()


# =============================================================================
# Rationality Gate Result
# =============================================================================


@dataclass
class EVResult:
    """Result of economic rationality evaluation.

    Attributes:
        vulnerability_id: ID of the vulnerability
        expected_value_usd: Computed expected value in USD
        is_economically_rational: Whether EV > 0
        priority_bucket: Priority bucket (critical/high/medium/low/deprioritized)
        attack_payoff: The AttackPayoff used in computation
        defense_payoff: The DefensePayoff used in computation
        rationale: Human-readable explanation
        evidence_refs: References supporting the computation
    """

    vulnerability_id: str
    expected_value_usd: float
    is_economically_rational: bool
    priority_bucket: str
    attack_payoff: Optional[AttackPayoff] = None
    defense_payoff: Optional[DefensePayoff] = None
    rationale: str = ""
    evidence_refs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "vulnerability_id": self.vulnerability_id,
            "expected_value_usd": self.expected_value_usd,
            "is_economically_rational": self.is_economically_rational,
            "priority_bucket": self.priority_bucket,
            "attack_payoff": self.attack_payoff.to_dict() if self.attack_payoff else None,
            "defense_payoff": self.defense_payoff.to_dict() if self.defense_payoff else None,
            "rationale": self.rationale,
            "evidence_refs": self.evidence_refs,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EVResult":
        """Create EVResult from dictionary."""
        return cls(
            vulnerability_id=str(data.get("vulnerability_id", "")),
            expected_value_usd=float(data.get("expected_value_usd", 0)),
            is_economically_rational=bool(data.get("is_economically_rational", False)),
            priority_bucket=str(data.get("priority_bucket", "low")),
            attack_payoff=AttackPayoff.from_dict(data["attack_payoff"]) if data.get("attack_payoff") else None,
            defense_payoff=DefensePayoff.from_dict(data["defense_payoff"]) if data.get("defense_payoff") else None,
            rationale=str(data.get("rationale", "")),
            evidence_refs=list(data.get("evidence_refs", [])),
        )


# =============================================================================
# Rationality Gate
# =============================================================================


class RationalityGate:
    """Economic rationality gate for vulnerability filtering.

    Per 05.11-03: Filters vulnerabilities with negative expected value
    to reduce false positive noise and focus on economically viable attacks.

    The gate uses PayoffMatrix from economics/payoff.py to compute:
    - expected_profit = (success_prob * profit) - gas_cost - mev_risk

    Vulnerabilities with EV < 0 are deprioritized (not hidden) because:
    - A rational attacker wouldn't exploit them
    - They represent lower real-world risk
    - They still appear in full reports for completeness

    Usage:
        gate = RationalityGate()

        # Evaluate single vulnerability
        result = gate.evaluate_attack_ev(vuln_data, protocol_state)

        # Check result
        if result.is_economically_rational:
            prioritize(vuln_data)
        else:
            deprioritize(vuln_data)  # Don't hide, just lower priority
    """

    def __init__(
        self,
        threshold: Optional[EVThreshold] = None,
        default_gas_cost_usd: float = 50.0,
        default_success_probability: float = 0.5,
    ):
        """Initialize rationality gate.

        Args:
            threshold: EV thresholds (uses defaults if None)
            default_gas_cost_usd: Default gas cost assumption
            default_success_probability: Default success probability
        """
        self.threshold = threshold or DEFAULT_EV_THRESHOLD
        self.default_gas_cost_usd = default_gas_cost_usd
        self.default_success_probability = default_success_probability

    def evaluate_attack_ev(
        self,
        vulnerability: Dict[str, Any],
        protocol_state: Optional[Dict[str, Any]] = None,
    ) -> EVResult:
        """Evaluate expected value of exploiting a vulnerability.

        Per 05.11-03: Uses PayoffMatrix for EV computation.

        Args:
            vulnerability: Vulnerability data dict with:
                - id: Vulnerability ID
                - severity: Severity level
                - potential_profit_usd: Estimated profit (optional)
                - gas_cost_usd: Estimated gas cost (optional)
                - success_probability: Success probability (optional)
                - mev_risk: MEV front-running risk (optional)
            protocol_state: Optional protocol state with:
                - tvl_usd: Total value locked
                - detection_probability: Protocol's detection capability
                - emergency_pause_capable: Whether protocol can emergency pause

        Returns:
            EVResult with expected value and priority bucket
        """
        vuln_id = vulnerability.get("id", "unknown")
        protocol_state = protocol_state or {}

        # Extract or estimate attack parameters
        potential_profit = vulnerability.get(
            "potential_profit_usd",
            self._estimate_profit(vulnerability, protocol_state)
        )
        gas_cost = vulnerability.get("gas_cost_usd", self.default_gas_cost_usd)
        success_prob = vulnerability.get("success_probability", self.default_success_probability)
        mev_risk = vulnerability.get("mev_risk", self._estimate_mev_risk(vulnerability))

        # Validate probability range
        success_prob = max(0.0, min(1.0, success_prob))
        mev_risk = max(0.0, min(1.0, mev_risk))

        # Build attack payoff
        attack_payoff = AttackPayoff(
            expected_profit_usd=potential_profit,
            gas_cost_usd=gas_cost,
            mev_risk=mev_risk,
            success_probability=success_prob,
            capital_required_usd=vulnerability.get("capital_required_usd", 0),
            execution_complexity=vulnerability.get("execution_complexity", "medium"),
            detection_risk=protocol_state.get("detection_probability", 0.3),
            evidence_refs=vulnerability.get("evidence_refs", []),
        )

        # Build defense payoff
        defense_payoff = DefensePayoff(
            detection_probability=protocol_state.get("detection_probability", 0.3),
            mitigation_cost_usd=protocol_state.get("mitigation_cost_usd", 0),
            timelock_delay_seconds=protocol_state.get("timelock_delay_seconds", 0),
            response_time_seconds=protocol_state.get("response_time_seconds", 0),
            insurance_coverage_usd=protocol_state.get("insurance_coverage_usd", 0),
            emergency_pause_capable=protocol_state.get("emergency_pause_capable", False),
        )

        # Compute expected value
        ev = attack_payoff.expected_value
        is_rational = ev > self.threshold.filter_threshold_usd
        priority_bucket = self.threshold.get_priority_bucket(ev)

        # Build rationale
        rationale_parts = [
            f"EV = ${ev:,.2f}",
            f"(P(success)={success_prob:.0%} * profit=${potential_profit:,.0f})",
            f"- gas=${gas_cost:.0f}",
            f"- MEV_risk={mev_risk:.0%}",
        ]
        rationale = " ".join(rationale_parts)

        if not is_rational:
            rationale += f" | DEPRIORITIZED: EV < ${self.threshold.filter_threshold_usd:.0f}"
        elif priority_bucket == "critical":
            rationale += f" | CRITICAL: EV > ${self.threshold.escalation_threshold_usd:,.0f}"

        # Log for transparency
        logger.info(f"Rationality gate: {vuln_id} -> {priority_bucket} ({rationale})")

        return EVResult(
            vulnerability_id=vuln_id,
            expected_value_usd=ev,
            is_economically_rational=is_rational,
            priority_bucket=priority_bucket,
            attack_payoff=attack_payoff,
            defense_payoff=defense_payoff,
            rationale=rationale,
            evidence_refs=vulnerability.get("evidence_refs", []),
        )

    def _estimate_profit(
        self,
        vulnerability: Dict[str, Any],
        protocol_state: Dict[str, Any],
    ) -> float:
        """Estimate potential profit from vulnerability.

        Uses severity and TVL as heuristics if not provided.

        Args:
            vulnerability: Vulnerability data
            protocol_state: Protocol state with TVL

        Returns:
            Estimated profit in USD
        """
        tvl = protocol_state.get("tvl_usd", 1_000_000)  # Default 1M TVL

        # Severity-based extraction fraction
        severity = vulnerability.get("severity", "medium").lower()
        extraction_fractions = {
            "critical": 0.1,   # Could extract 10% of TVL
            "high": 0.05,     # Could extract 5% of TVL
            "medium": 0.01,   # Could extract 1% of TVL
            "low": 0.001,     # Could extract 0.1% of TVL
        }
        extraction = extraction_fractions.get(severity, 0.01)

        # Cap at reasonable maximum
        return min(tvl * extraction, 10_000_000)

    def _estimate_mev_risk(self, vulnerability: Dict[str, Any]) -> float:
        """Estimate MEV front-running risk for vulnerability.

        Args:
            vulnerability: Vulnerability data

        Returns:
            MEV risk probability (0.0-1.0)
        """
        # Check for vulnerability types with high MEV exposure
        pattern = vulnerability.get("pattern_id", "").lower()
        high_mev_patterns = [
            "sandwich", "frontrun", "arbitrage", "swap",
            "flash", "amm", "dex", "liquidation",
        ]

        for mev_pattern in high_mev_patterns:
            if mev_pattern in pattern:
                return 0.6  # High MEV risk

        # Default moderate risk
        return 0.2


# =============================================================================
# Filtering Functions
# =============================================================================


def filter_by_economic_rationality(
    vulnerabilities: List[Dict[str, Any]],
    protocol_state: Optional[Dict[str, Any]] = None,
    threshold: Optional[EVThreshold] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Filter vulnerabilities by economic rationality.

    Per 05.11-03: Filters vulnerabilities with negative expected value.
    Deprioritizes (does not hide) economically irrational vulnerabilities.

    Args:
        vulnerabilities: List of vulnerability dicts
        protocol_state: Optional protocol state for context
        threshold: Optional custom thresholds

    Returns:
        Tuple of (rational_vulnerabilities, deprioritized_vulnerabilities)

    Usage:
        rational, deprioritized = filter_by_economic_rationality(vulns, protocol_state)

        # Process rational vulnerabilities first
        for vuln in rational:
            verify(vuln)

        # Deprioritized still exist, just lower priority
        for vuln in deprioritized:
            add_to_secondary_report(vuln)
    """
    gate = RationalityGate(threshold=threshold)

    rational = []
    deprioritized = []

    for vuln in vulnerabilities:
        result = gate.evaluate_attack_ev(vuln, protocol_state)

        # Add rationality metadata to vulnerability
        vuln_with_ev = {
            **vuln,
            "is_economically_rational": result.is_economically_rational,
            "expected_value_usd": result.expected_value_usd,
            "priority_bucket": result.priority_bucket,
            "ev_rationale": result.rationale,
        }

        if result.is_economically_rational:
            rational.append(vuln_with_ev)
        else:
            deprioritized.append(vuln_with_ev)

    # Log summary for transparency
    logger.info(
        f"Rationality filter: {len(rational)} rational, {len(deprioritized)} deprioritized "
        f"(total: {len(vulnerabilities)})"
    )

    return rational, deprioritized


def get_priority_sorted_vulnerabilities(
    vulnerabilities: List[Dict[str, Any]],
    protocol_state: Optional[Dict[str, Any]] = None,
    threshold: Optional[EVThreshold] = None,
) -> List[Dict[str, Any]]:
    """Sort vulnerabilities by economic priority.

    Returns all vulnerabilities sorted by EV, with priority bucket attached.

    Args:
        vulnerabilities: List of vulnerability dicts
        protocol_state: Optional protocol state
        threshold: Optional custom thresholds

    Returns:
        List sorted by expected value (descending)
    """
    gate = RationalityGate(threshold=threshold)

    evaluated = []
    for vuln in vulnerabilities:
        result = gate.evaluate_attack_ev(vuln, protocol_state)
        evaluated.append({
            **vuln,
            "is_economically_rational": result.is_economically_rational,
            "expected_value_usd": result.expected_value_usd,
            "priority_bucket": result.priority_bucket,
            "ev_rationale": result.rationale,
        })

    # Sort by EV descending
    evaluated.sort(key=lambda v: v.get("expected_value_usd", 0), reverse=True)

    return evaluated


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "EVThreshold",
    "DEFAULT_EV_THRESHOLD",
    "EVResult",
    "RationalityGate",
    "filter_by_economic_rationality",
    "get_priority_sorted_vulnerabilities",
]
