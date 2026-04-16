"""Incentive analysis for protocol security assessment.

Per 05.11-06: The IncentiveAnalyzer identifies Proof-of-Behavior-style
incentive structures, flags when honest behavior is NOT dominant, and
suggests blocking conditions for mitigations.

Key Features:
- Incentive misalignment detection
- Proof-of-Behavior pattern recognition
- Honest behavior dominance checking
- Mitigation suggestions via blocking conditions

Usage:
    from alphaswarm_sol.economics.gate.incentive_analysis import (
        IncentiveAnalyzer,
        IncentiveReport,
        IncentiveMisalignment,
    )

    analyzer = IncentiveAnalyzer()
    report = analyzer.analyze_incentives(protocol_state)

    if not report.is_honest_dominant:
        print(f"Misalignment detected: {report.misalignment_reasons}")
        for suggestion in report.blocking_suggestions:
            print(f"Suggested mitigation: {suggestion}")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .attack_synthesis import AttackPayoffMatrix, AttackStrategy, ProtocolDefense
from .nash_solver import BlockingCondition, BlockingConditionType, NashResult

logger = logging.getLogger(__name__)


# =============================================================================
# Incentive Misalignment Types
# =============================================================================


class MisalignmentType(Enum):
    """Types of incentive misalignments in protocol design.

    Per 05.11-06: Identifies patterns where user/attacker incentives
    diverge from protocol-intended behavior.
    """

    GRIEFING = "griefing"  # Profitable to cause harm to others
    FREE_RIDING = "free_riding"  # Benefit without contributing
    MEV_EXTRACTION = "mev_extraction"  # Value extraction via ordering
    GOVERNANCE_CAPTURE = "governance_capture"  # Control via token acquisition
    ORACLE_MANIPULATION = "oracle_manipulation"  # Profit from price manipulation
    FLASHLOAN_AMPLIFICATION = "flashloan_amplification"  # Capital-free attacks
    SANDWICH_ATTACK = "sandwich_attack"  # Profit from sandwiching users
    LIQUIDATION_GAMING = "liquidation_gaming"  # Manipulating liquidations
    FRONT_RUNNING = "front_running"  # Profit from information asymmetry
    SELFISH_MINING = "selfish_mining"  # Deviation from honest mining

    @classmethod
    def from_pattern(cls, pattern_id: str) -> Optional["MisalignmentType"]:
        """Infer misalignment type from vulnerability pattern.

        Args:
            pattern_id: Pattern identifier

        Returns:
            Corresponding misalignment type or None
        """
        pattern_lower = pattern_id.lower()

        mapping = {
            "grief": cls.GRIEFING,
            "free_rid": cls.FREE_RIDING,
            "mev": cls.MEV_EXTRACTION,
            "govern": cls.GOVERNANCE_CAPTURE,
            "oracle": cls.ORACLE_MANIPULATION,
            "flash": cls.FLASHLOAN_AMPLIFICATION,
            "sandwich": cls.SANDWICH_ATTACK,
            "liquidat": cls.LIQUIDATION_GAMING,
            "front_run": cls.FRONT_RUNNING,
            "frontrun": cls.FRONT_RUNNING,
        }

        for key, mtype in mapping.items():
            if key in pattern_lower:
                return mtype

        return None


@dataclass
class IncentiveMisalignment:
    """A detected incentive misalignment in the protocol.

    Attributes:
        misalignment_type: Type of misalignment
        description: Human-readable description
        severity: Severity level (critical/high/medium/low)
        attacker_benefit_usd: How much attacker benefits from misalignment
        protocol_cost_usd: Cost to protocol from exploitation
        mitigation: Suggested mitigation
        confidence: Confidence in this assessment (0-1)
        evidence_refs: Supporting evidence references
    """

    misalignment_type: MisalignmentType
    description: str
    severity: str = "medium"
    attacker_benefit_usd: float = 0.0
    protocol_cost_usd: float = 0.0
    mitigation: str = ""
    confidence: float = 0.8
    evidence_refs: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate confidence range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be 0.0-1.0, got {self.confidence}")

    @property
    def profit_ratio(self) -> float:
        """Ratio of attacker benefit to protocol cost."""
        if self.protocol_cost_usd == 0:
            return float("inf") if self.attacker_benefit_usd > 0 else 0.0
        return self.attacker_benefit_usd / self.protocol_cost_usd

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "misalignment_type": self.misalignment_type.value,
            "description": self.description,
            "severity": self.severity,
            "attacker_benefit_usd": self.attacker_benefit_usd,
            "protocol_cost_usd": self.protocol_cost_usd,
            "mitigation": self.mitigation,
            "confidence": self.confidence,
            "evidence_refs": self.evidence_refs,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IncentiveMisalignment":
        """Create IncentiveMisalignment from dictionary."""
        return cls(
            misalignment_type=MisalignmentType(data.get("misalignment_type", "griefing")),
            description=str(data.get("description", "")),
            severity=str(data.get("severity", "medium")),
            attacker_benefit_usd=float(data.get("attacker_benefit_usd", 0)),
            protocol_cost_usd=float(data.get("protocol_cost_usd", 0)),
            mitigation=str(data.get("mitigation", "")),
            confidence=float(data.get("confidence", 0.8)),
            evidence_refs=list(data.get("evidence_refs", [])),
        )


# =============================================================================
# Incentive Report
# =============================================================================


@dataclass
class IncentiveReport:
    """Report on protocol incentive alignment.

    Per 05.11-06: Comprehensive assessment of whether protocol incentives
    encourage honest behavior.

    Attributes:
        is_honest_dominant: True if honest behavior is the dominant strategy
        misalignments: List of detected incentive misalignments
        blocking_suggestions: Suggested blocking conditions for mitigations
        overall_alignment_score: 0-100 score of incentive alignment
        has_proof_of_behavior: True if protocol uses PoB-style incentives
        honest_ev_usd: Expected value of honest behavior
        exploit_ev_usd: Expected value of exploiting misalignments
        rationale: Human-readable summary
        evidence_refs: Supporting evidence references
    """

    is_honest_dominant: bool
    misalignments: List[IncentiveMisalignment] = field(default_factory=list)
    blocking_suggestions: List[BlockingCondition] = field(default_factory=list)
    overall_alignment_score: float = 0.0
    has_proof_of_behavior: bool = False
    honest_ev_usd: float = 0.0
    exploit_ev_usd: float = 0.0
    rationale: str = ""
    evidence_refs: List[str] = field(default_factory=list)

    @property
    def misalignment_count(self) -> int:
        """Number of detected misalignments."""
        return len(self.misalignments)

    @property
    def critical_misalignments(self) -> List[IncentiveMisalignment]:
        """Get critical severity misalignments."""
        return [m for m in self.misalignments if m.severity == "critical"]

    @property
    def total_attacker_benefit(self) -> float:
        """Total attacker benefit across all misalignments."""
        return sum(m.attacker_benefit_usd for m in self.misalignments)

    @property
    def total_protocol_cost(self) -> float:
        """Total protocol cost across all misalignments."""
        return sum(m.protocol_cost_usd for m in self.misalignments)

    def get_summary(self) -> str:
        """Get human-readable summary.

        Returns:
            Summary string
        """
        status = "ALIGNED" if self.is_honest_dominant else "MISALIGNED"
        return (
            f"Incentive Status: {status}\n"
            f"Alignment Score: {self.overall_alignment_score:.0f}/100\n"
            f"Misalignments: {self.misalignment_count}\n"
            f"Total Attacker Benefit: ${self.total_attacker_benefit:,.2f}\n"
            f"Suggested Mitigations: {len(self.blocking_suggestions)}"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "is_honest_dominant": self.is_honest_dominant,
            "misalignments": [m.to_dict() for m in self.misalignments],
            "blocking_suggestions": [b.to_dict() for b in self.blocking_suggestions],
            "overall_alignment_score": self.overall_alignment_score,
            "has_proof_of_behavior": self.has_proof_of_behavior,
            "honest_ev_usd": self.honest_ev_usd,
            "exploit_ev_usd": self.exploit_ev_usd,
            "rationale": self.rationale,
            "evidence_refs": self.evidence_refs,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IncentiveReport":
        """Create IncentiveReport from dictionary."""
        return cls(
            is_honest_dominant=bool(data.get("is_honest_dominant", True)),
            misalignments=[
                IncentiveMisalignment.from_dict(m)
                for m in data.get("misalignments", [])
            ],
            blocking_suggestions=[
                BlockingCondition.from_dict(b)
                for b in data.get("blocking_suggestions", [])
            ],
            overall_alignment_score=float(data.get("overall_alignment_score", 0)),
            has_proof_of_behavior=bool(data.get("has_proof_of_behavior", False)),
            honest_ev_usd=float(data.get("honest_ev_usd", 0)),
            exploit_ev_usd=float(data.get("exploit_ev_usd", 0)),
            rationale=str(data.get("rationale", "")),
            evidence_refs=list(data.get("evidence_refs", [])),
        )


# =============================================================================
# Incentive Analyzer
# =============================================================================


class IncentiveAnalyzer:
    """Analyzer for protocol incentive alignment.

    Per 05.11-06: Identifies Proof-of-Behavior-style incentive structures,
    detects misalignments, and suggests blocking conditions for mitigations.

    The analyzer checks:
    1. Whether honest behavior is the dominant strategy
    2. Specific misalignment patterns (griefing, MEV, etc.)
    3. Protocol features that improve alignment (timelocks, etc.)

    Usage:
        analyzer = IncentiveAnalyzer()

        # Analyze from protocol state
        report = analyzer.analyze_incentives(protocol_state)

        # Analyze from Nash result
        report = analyzer.analyze_from_nash(nash_result, payoff_matrix)

        if not report.is_honest_dominant:
            for suggestion in report.blocking_suggestions:
                print(f"Suggested: {suggestion.description}")
    """

    def __init__(
        self,
        min_alignment_score: float = 70.0,
        misalignment_threshold_usd: float = 1000.0,
    ):
        """Initialize incentive analyzer.

        Args:
            min_alignment_score: Minimum score to consider aligned (0-100)
            misalignment_threshold_usd: Minimum benefit to report misalignment
        """
        self.min_alignment_score = min_alignment_score
        self.misalignment_threshold_usd = misalignment_threshold_usd

    def analyze_incentives(
        self,
        protocol_state: Dict[str, Any],
    ) -> IncentiveReport:
        """Analyze incentive alignment from protocol state.

        Args:
            protocol_state: Protocol state dict with:
                - tvl_usd: Total value locked
                - vulnerabilities: List of vulnerability dicts
                - defenses: List of active defenses
                - mev_exposure: MEV exposure level
                - has_timelock: Whether protocol has timelock
                - has_pause: Whether protocol can pause

        Returns:
            IncentiveReport with alignment assessment
        """
        misalignments: List[IncentiveMisalignment] = []
        blocking_suggestions: List[BlockingCondition] = []

        tvl = protocol_state.get("tvl_usd", 1_000_000)
        vulnerabilities = protocol_state.get("vulnerabilities", [])

        # Analyze each vulnerability for incentive misalignment
        for vuln in vulnerabilities:
            mtype = MisalignmentType.from_pattern(vuln.get("pattern_id", ""))
            if mtype:
                misalignment = self._analyze_vulnerability_misalignment(
                    vuln, mtype, tvl
                )
                if misalignment and misalignment.attacker_benefit_usd >= self.misalignment_threshold_usd:
                    misalignments.append(misalignment)

        # Check MEV exposure
        mev_exposure = protocol_state.get("mev_exposure", "medium")
        if mev_exposure in ("high", "very_high"):
            misalignment = IncentiveMisalignment(
                misalignment_type=MisalignmentType.MEV_EXTRACTION,
                description="High MEV exposure creates incentive to extract value via transaction ordering",
                severity="high" if mev_exposure == "very_high" else "medium",
                attacker_benefit_usd=tvl * 0.001,  # 0.1% of TVL
                protocol_cost_usd=tvl * 0.002,
                mitigation="Implement MEV protection (Flashbots, private transactions, commit-reveal)",
                confidence=0.85,
            )
            misalignments.append(misalignment)

            blocking_suggestions.append(
                BlockingCondition(
                    condition_type=BlockingConditionType.MEV_PROTECTION,
                    threshold="mev_protection_enabled = true",
                    effect_usd=tvl * 0.001,
                    description="MEV protection would reduce extraction by ~$"
                    f"{tvl * 0.001:,.0f}",
                )
            )

        # Check for Proof-of-Behavior patterns
        has_pob = self._detect_proof_of_behavior(protocol_state)

        # Compute alignment score
        alignment_score = self._compute_alignment_score(
            protocol_state, misalignments, has_pob
        )

        # Determine if honest is dominant
        is_honest_dominant = (
            alignment_score >= self.min_alignment_score
            and len([m for m in misalignments if m.severity in ("critical", "high")]) == 0
        )

        # Generate blocking suggestions based on misalignments
        for misalignment in misalignments:
            suggestion = self._suggest_blocking_condition(misalignment)
            if suggestion and suggestion not in blocking_suggestions:
                blocking_suggestions.append(suggestion)

        # Compute EV estimates
        honest_ev = self._estimate_honest_ev(protocol_state)
        exploit_ev = sum(m.attacker_benefit_usd for m in misalignments)

        rationale = self._build_rationale(
            is_honest_dominant, misalignments, alignment_score, has_pob
        )

        return IncentiveReport(
            is_honest_dominant=is_honest_dominant,
            misalignments=misalignments,
            blocking_suggestions=blocking_suggestions,
            overall_alignment_score=alignment_score,
            has_proof_of_behavior=has_pob,
            honest_ev_usd=honest_ev,
            exploit_ev_usd=exploit_ev,
            rationale=rationale,
        )

    def analyze_from_nash(
        self,
        nash_result: NashResult,
        payoff_matrix: AttackPayoffMatrix,
    ) -> IncentiveReport:
        """Analyze incentives from Nash equilibrium result.

        Args:
            nash_result: Result from Nash equilibrium solver
            payoff_matrix: Attack payoff matrix

        Returns:
            IncentiveReport based on game-theoretic analysis
        """
        misalignments: List[IncentiveMisalignment] = []

        # If attack is dominant, there's a misalignment
        if nash_result.is_attack_dominant:
            mtype = MisalignmentType.from_pattern(payoff_matrix.scenario)
            if mtype is None:
                mtype = MisalignmentType.FREE_RIDING

            misalignment = IncentiveMisalignment(
                misalignment_type=mtype,
                description=f"Attack ({nash_result.attacker_strategy}) dominates honest behavior",
                severity="critical" if nash_result.attacker_payoff > 100000 else "high",
                attacker_benefit_usd=nash_result.attacker_payoff,
                protocol_cost_usd=-nash_result.protocol_payoff,  # Protocol payoff is negative
                mitigation=f"Implement {nash_result.protocol_strategy} or stronger defense",
                confidence=nash_result.convergence_prob,
                evidence_refs=nash_result.evidence_refs,
            )
            misalignments.append(misalignment)

        # Get blocking conditions from Nash result
        blocking_suggestions = list(nash_result.blocking_conditions)

        # Add suggestions for any defenses not currently active
        if not nash_result.is_attack_dominant:
            # Attack is blocked - identify what's doing the blocking
            if nash_result.blocking_conditions:
                # Already have suggestions
                pass
            else:
                # Suggest maintaining current defense
                blocking_suggestions.append(
                    BlockingCondition(
                        condition_type=BlockingConditionType.from_defense(
                            ProtocolDefense(nash_result.protocol_strategy)
                        ),
                        threshold=f"{nash_result.protocol_strategy} = active",
                        effect_usd=0,
                        description="Current defense is blocking attack",
                    )
                )

        # Compute alignment score
        alignment_score = 100.0 if not nash_result.is_attack_dominant else max(
            0, 100 - len(misalignments) * 30
        )

        is_honest_dominant = not nash_result.is_attack_dominant

        rationale = self._build_nash_rationale(nash_result, payoff_matrix)

        return IncentiveReport(
            is_honest_dominant=is_honest_dominant,
            misalignments=misalignments,
            blocking_suggestions=blocking_suggestions,
            overall_alignment_score=alignment_score,
            has_proof_of_behavior=False,  # Can't determine from Nash alone
            honest_ev_usd=0 if is_honest_dominant else nash_result.attacker_payoff,
            exploit_ev_usd=nash_result.attacker_payoff,
            rationale=rationale,
            evidence_refs=nash_result.evidence_refs,
        )

    def find_blocking_conditions(
        self,
        misalignments: List[IncentiveMisalignment],
    ) -> List[BlockingCondition]:
        """Find blocking conditions to mitigate misalignments.

        Args:
            misalignments: List of detected misalignments

        Returns:
            List of suggested blocking conditions
        """
        suggestions: List[BlockingCondition] = []

        for misalignment in misalignments:
            suggestion = self._suggest_blocking_condition(misalignment)
            if suggestion:
                suggestions.append(suggestion)

        return suggestions

    def _analyze_vulnerability_misalignment(
        self,
        vulnerability: Dict[str, Any],
        mtype: MisalignmentType,
        tvl: float,
    ) -> Optional[IncentiveMisalignment]:
        """Analyze a vulnerability for incentive misalignment.

        Args:
            vulnerability: Vulnerability data
            mtype: Misalignment type
            tvl: Total value locked

        Returns:
            IncentiveMisalignment if detected
        """
        severity = vulnerability.get("severity", "medium").lower()
        pattern_id = vulnerability.get("pattern_id", "unknown")

        # Estimate attacker benefit
        severity_rates = {
            "critical": 0.10,
            "high": 0.05,
            "medium": 0.01,
            "low": 0.001,
        }
        rate = severity_rates.get(severity, 0.01)
        attacker_benefit = vulnerability.get("potential_profit_usd", tvl * rate)

        # Protocol cost is typically higher due to reputation damage
        protocol_cost = attacker_benefit * 1.5

        # Get mitigation based on misalignment type
        mitigations = {
            MisalignmentType.GRIEFING: "Implement griefing penalties or deposit requirements",
            MisalignmentType.FREE_RIDING: "Add contribution requirements or fee mechanisms",
            MisalignmentType.MEV_EXTRACTION: "Use MEV protection (Flashbots, private transactions)",
            MisalignmentType.GOVERNANCE_CAPTURE: "Add timelock and quorum requirements",
            MisalignmentType.ORACLE_MANIPULATION: "Use TWAP oracles or multi-oracle validation",
            MisalignmentType.FLASHLOAN_AMPLIFICATION: "Add flash loan guards or rate limits",
            MisalignmentType.SANDWICH_ATTACK: "Implement slippage protection or batch auctions",
            MisalignmentType.LIQUIDATION_GAMING: "Add liquidation delays or gradual liquidation",
            MisalignmentType.FRONT_RUNNING: "Use commit-reveal or encrypted mempools",
            MisalignmentType.SELFISH_MINING: "Adjust consensus parameters or uncle rewards",
        }

        return IncentiveMisalignment(
            misalignment_type=mtype,
            description=f"Vulnerability {pattern_id} creates {mtype.value} incentive",
            severity=severity,
            attacker_benefit_usd=attacker_benefit,
            protocol_cost_usd=protocol_cost,
            mitigation=mitigations.get(mtype, "Implement appropriate defense"),
            confidence=0.75 if severity in ("medium", "low") else 0.9,
            evidence_refs=vulnerability.get("evidence_refs", []),
        )

    def _detect_proof_of_behavior(
        self,
        protocol_state: Dict[str, Any],
    ) -> bool:
        """Detect if protocol uses Proof-of-Behavior-style incentives.

        PoB patterns include:
        - Staking with slashing conditions
        - Reputation systems
        - Bonding curves
        - Vesting with clawback

        Args:
            protocol_state: Protocol state

        Returns:
            True if PoB patterns detected
        """
        pob_features = [
            "has_staking",
            "has_slashing",
            "has_reputation",
            "has_bonding",
            "has_vesting",
            "has_escrow",
            "has_collateral",
        ]

        detected = sum(1 for f in pob_features if protocol_state.get(f, False))
        return detected >= 2  # At least 2 features for PoB classification

    def _compute_alignment_score(
        self,
        protocol_state: Dict[str, Any],
        misalignments: List[IncentiveMisalignment],
        has_pob: bool,
    ) -> float:
        """Compute overall incentive alignment score (0-100).

        Args:
            protocol_state: Protocol state
            misalignments: Detected misalignments
            has_pob: Whether protocol has PoB patterns

        Returns:
            Alignment score 0-100
        """
        score = 100.0

        # Deduct for misalignments
        severity_penalties = {
            "critical": 30,
            "high": 20,
            "medium": 10,
            "low": 5,
        }

        for m in misalignments:
            penalty = severity_penalties.get(m.severity, 10)
            score -= penalty

        # Bonus for PoB patterns
        if has_pob:
            score += 10

        # Bonus for defenses
        if protocol_state.get("has_timelock"):
            score += 5
        if protocol_state.get("has_pause"):
            score += 5
        if protocol_state.get("has_monitoring"):
            score += 5

        return max(0, min(100, score))

    def _suggest_blocking_condition(
        self,
        misalignment: IncentiveMisalignment,
    ) -> Optional[BlockingCondition]:
        """Suggest blocking condition for a misalignment.

        Args:
            misalignment: Detected misalignment

        Returns:
            Suggested blocking condition or None
        """
        type_to_condition = {
            MisalignmentType.GRIEFING: (
                BlockingConditionType.GAS_COST,
                "griefing_deposit > attack_cost",
            ),
            MisalignmentType.FREE_RIDING: (
                BlockingConditionType.RATE_LIMIT,
                "contribution_required = true",
            ),
            MisalignmentType.MEV_EXTRACTION: (
                BlockingConditionType.MEV_PROTECTION,
                "mev_protection_enabled = true",
            ),
            MisalignmentType.GOVERNANCE_CAPTURE: (
                BlockingConditionType.TIMELOCK,
                "timelock > 2 days",
            ),
            MisalignmentType.ORACLE_MANIPULATION: (
                BlockingConditionType.GUARD,
                "oracle_deviation_check <= 5%",
            ),
            MisalignmentType.FLASHLOAN_AMPLIFICATION: (
                BlockingConditionType.RATE_LIMIT,
                "flashloan_guard_active = true",
            ),
            MisalignmentType.SANDWICH_ATTACK: (
                BlockingConditionType.SLIPPAGE,
                "slippage_protection <= 1%",
            ),
            MisalignmentType.LIQUIDATION_GAMING: (
                BlockingConditionType.TIMELOCK,
                "liquidation_delay > 1 hour",
            ),
            MisalignmentType.FRONT_RUNNING: (
                BlockingConditionType.MEV_PROTECTION,
                "commit_reveal_enabled = true",
            ),
        }

        if misalignment.misalignment_type not in type_to_condition:
            return None

        condition_type, threshold = type_to_condition[misalignment.misalignment_type]

        return BlockingCondition(
            condition_type=condition_type,
            threshold=threshold,
            effect_usd=misalignment.attacker_benefit_usd,
            description=misalignment.mitigation,
            confidence=misalignment.confidence,
            evidence_refs=misalignment.evidence_refs,
        )

    def _estimate_honest_ev(
        self,
        protocol_state: Dict[str, Any],
    ) -> float:
        """Estimate expected value of honest behavior.

        Args:
            protocol_state: Protocol state

        Returns:
            Estimated EV in USD
        """
        # Honest users typically earn yield or fees
        tvl = protocol_state.get("tvl_usd", 1_000_000)
        apy = protocol_state.get("apy", 0.05)  # 5% default

        # Annual yield for honest participation
        return tvl * apy

    def _build_rationale(
        self,
        is_honest_dominant: bool,
        misalignments: List[IncentiveMisalignment],
        alignment_score: float,
        has_pob: bool,
    ) -> str:
        """Build human-readable rationale.

        Args:
            is_honest_dominant: Whether honest is dominant
            misalignments: Detected misalignments
            alignment_score: Alignment score
            has_pob: Whether protocol has PoB

        Returns:
            Rationale string
        """
        parts = []

        if is_honest_dominant:
            parts.append("Honest behavior is the dominant strategy for rational actors.")
        else:
            parts.append("WARNING: Honest behavior is NOT dominant - exploitation is profitable.")

        parts.append(f"Alignment score: {alignment_score:.0f}/100.")

        if misalignments:
            critical = len([m for m in misalignments if m.severity == "critical"])
            high = len([m for m in misalignments if m.severity == "high"])
            if critical > 0:
                parts.append(f"Found {critical} critical misalignment(s).")
            if high > 0:
                parts.append(f"Found {high} high-severity misalignment(s).")

        if has_pob:
            parts.append("Protocol uses Proof-of-Behavior incentive patterns.")

        return " ".join(parts)

    def _build_nash_rationale(
        self,
        nash_result: NashResult,
        payoff_matrix: AttackPayoffMatrix,
    ) -> str:
        """Build rationale from Nash equilibrium result.

        Args:
            nash_result: Nash equilibrium result
            payoff_matrix: Attack payoff matrix

        Returns:
            Rationale string
        """
        parts = []

        if nash_result.is_attack_dominant:
            parts.append(
                f"At Nash equilibrium, attack ({nash_result.attacker_strategy}) "
                f"dominates with EV = ${nash_result.attacker_payoff:,.2f}."
            )
        else:
            parts.append(
                f"At Nash equilibrium, attack is not profitable "
                f"(EV = ${nash_result.attacker_payoff:,.2f})."
            )

        parts.append(
            f"Protocol best response: {nash_result.protocol_strategy}."
        )

        if nash_result.blocking_conditions:
            blockers = [bc.condition_type.value for bc in nash_result.blocking_conditions]
            parts.append(f"Blocking conditions: {', '.join(blockers)}.")

        if not nash_result.is_pure_equilibrium:
            parts.append(
                f"Mixed equilibrium approximated in {nash_result.iterations_to_converge} iterations."
            )

        return " ".join(parts)


# =============================================================================
# Module Exports
# =============================================================================


__all__ = [
    "MisalignmentType",
    "IncentiveMisalignment",
    "IncentiveReport",
    "IncentiveAnalyzer",
]
