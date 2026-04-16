"""
Risk Factor Analysis

Identifies and quantifies risk factors that correlate with future exploits.
Based on analysis of historical exploit data patterns.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class RiskFactorType(Enum):
    """Categories of risk factors."""
    # Code-related
    CODE_COMPLEXITY = "code_complexity"           # High cyclomatic complexity
    RAPID_CHANGES = "rapid_changes"               # Many changes in short time
    LOW_TEST_COVERAGE = "low_test_coverage"       # Insufficient testing
    EXTERNAL_DEPENDENCIES = "external_deps"       # Many external calls
    UPGRADE_FREQUENCY = "upgrade_frequency"       # Frequent upgrades

    # Process-related
    NO_AUDIT = "no_audit"                         # Never audited
    STALE_AUDIT = "stale_audit"                   # Audit > 6 months old
    RUSHED_DEPLOYMENT = "rushed_deployment"       # Deployed too quickly
    SINGLE_DEVELOPER = "single_developer"         # Bus factor = 1
    NO_FORMAL_VERIFICATION = "no_formal_verif"    # No Z3/Certora

    # Market-related
    HIGH_TVL_GROWTH = "high_tvl_growth"           # TVL growing > 100%/month
    LAUNCH_WINDOW = "launch_window"               # First 30 days post-launch
    COMPETITOR_EXPLOIT = "competitor_exploit"     # Similar protocol exploited
    INCENTIVE_MISALIGNMENT = "incentive_misalign" # Token emissions > fees

    # Pattern-related
    KNOWN_ANTIPATTERN = "known_antipattern"       # Uses known bad patterns
    MISSING_GUARDS = "missing_guards"             # No reentrancy guards
    PRIVILEGED_FUNCTIONS = "privileged_funcs"     # Many admin functions
    ORACLE_DEPENDENCE = "oracle_dependence"       # Heavy oracle reliance


class RiskSeverity(Enum):
    """Severity levels for risk factors."""
    CRITICAL = "critical"   # 4x weight
    HIGH = "high"           # 2x weight
    MEDIUM = "medium"       # 1x weight
    LOW = "low"             # 0.5x weight


@dataclass
class RiskFactor:
    """A single identified risk factor."""
    factor_type: RiskFactorType
    severity: RiskSeverity
    score: float                  # 0.0 to 1.0
    description: str
    evidence: List[str] = field(default_factory=list)
    detected_at: datetime = field(default_factory=datetime.now)

    # Historical correlation
    exploit_correlation: float = 0.0   # How often this factor precedes exploits

    def get_weighted_score(self) -> float:
        """Get score weighted by severity."""
        weights = {
            RiskSeverity.CRITICAL: 4.0,
            RiskSeverity.HIGH: 2.0,
            RiskSeverity.MEDIUM: 1.0,
            RiskSeverity.LOW: 0.5,
        }
        return self.score * weights[self.severity]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "factor_type": self.factor_type.value,
            "severity": self.severity.value,
            "score": round(self.score, 3),
            "weighted_score": round(self.get_weighted_score(), 3),
            "description": self.description,
            "evidence": self.evidence,
            "exploit_correlation": round(self.exploit_correlation, 3),
        }


@dataclass
class RiskProfile:
    """Complete risk profile for a protocol."""
    protocol_id: str
    protocol_name: Optional[str] = None

    # Risk factors
    factors: List[RiskFactor] = field(default_factory=list)

    # Aggregate scores
    overall_risk_score: float = 0.0     # 0-100
    exploit_probability: float = 0.0     # 0-1 probability in next 30 days
    confidence: float = 0.0              # Confidence in prediction

    # Timing
    high_risk_window: Optional[str] = None  # When exploit most likely
    analyzed_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if self.factors:
            self._calculate_scores()

    def _calculate_scores(self):
        """Calculate aggregate risk scores."""
        if not self.factors:
            return

        # Weighted sum of factors
        total_weighted = sum(f.get_weighted_score() for f in self.factors)
        max_possible = len(self.factors) * 4.0  # If all were critical

        self.overall_risk_score = min(100, (total_weighted / max_possible) * 100)

        # Exploit probability based on factor correlation
        avg_correlation = sum(f.exploit_correlation for f in self.factors) / len(self.factors)
        self.exploit_probability = min(1.0, avg_correlation * (self.overall_risk_score / 50))

        # Confidence based on number of factors analyzed
        self.confidence = min(1.0, len(self.factors) / 10)

    def add_factor(self, factor: RiskFactor):
        """Add a risk factor and recalculate."""
        self.factors.append(factor)
        self._calculate_scores()

    def get_critical_factors(self) -> List[RiskFactor]:
        """Get critical and high severity factors."""
        return [
            f for f in self.factors
            if f.severity in [RiskSeverity.CRITICAL, RiskSeverity.HIGH]
        ]

    def get_risk_level(self) -> str:
        """Get human-readable risk level."""
        if self.overall_risk_score >= 80:
            return "CRITICAL"
        elif self.overall_risk_score >= 60:
            return "HIGH"
        elif self.overall_risk_score >= 40:
            return "MEDIUM"
        elif self.overall_risk_score >= 20:
            return "LOW"
        else:
            return "MINIMAL"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "protocol_id": self.protocol_id,
            "protocol_name": self.protocol_name,
            "overall_risk_score": round(self.overall_risk_score, 1),
            "risk_level": self.get_risk_level(),
            "exploit_probability": round(self.exploit_probability, 3),
            "confidence": round(self.confidence, 3),
            "high_risk_window": self.high_risk_window,
            "critical_factors": len(self.get_critical_factors()),
            "total_factors": len(self.factors),
            "factors": [f.to_dict() for f in self.factors],
            "analyzed_at": self.analyzed_at.isoformat(),
        }


class RiskCalculator:
    """
    Calculates risk profiles based on various input signals.

    Uses historical exploit data to calibrate factor correlations.
    """

    # Historical correlation data (from analyzing past exploits)
    # Factor type -> (avg_days_before_exploit, correlation_strength)
    FACTOR_CORRELATIONS = {
        RiskFactorType.CODE_COMPLEXITY: (45, 0.35),
        RiskFactorType.RAPID_CHANGES: (14, 0.55),
        RiskFactorType.LOW_TEST_COVERAGE: (60, 0.40),
        RiskFactorType.EXTERNAL_DEPENDENCIES: (30, 0.45),
        RiskFactorType.UPGRADE_FREQUENCY: (21, 0.50),
        RiskFactorType.NO_AUDIT: (90, 0.60),
        RiskFactorType.STALE_AUDIT: (30, 0.45),
        RiskFactorType.RUSHED_DEPLOYMENT: (7, 0.65),
        RiskFactorType.SINGLE_DEVELOPER: (60, 0.35),
        RiskFactorType.NO_FORMAL_VERIFICATION: (45, 0.40),
        RiskFactorType.HIGH_TVL_GROWTH: (21, 0.55),
        RiskFactorType.LAUNCH_WINDOW: (30, 0.70),
        RiskFactorType.COMPETITOR_EXPLOIT: (14, 0.60),
        RiskFactorType.INCENTIVE_MISALIGNMENT: (45, 0.35),
        RiskFactorType.KNOWN_ANTIPATTERN: (30, 0.75),
        RiskFactorType.MISSING_GUARDS: (21, 0.65),
        RiskFactorType.PRIVILEGED_FUNCTIONS: (45, 0.40),
        RiskFactorType.ORACLE_DEPENDENCE: (30, 0.50),
    }

    def __init__(self):
        self.profiles: Dict[str, RiskProfile] = {}

    def create_profile(
        self,
        protocol_id: str,
        protocol_name: Optional[str] = None
    ) -> RiskProfile:
        """Create a new risk profile."""
        profile = RiskProfile(
            protocol_id=protocol_id,
            protocol_name=protocol_name,
        )
        self.profiles[protocol_id] = profile
        return profile

    def assess_code_complexity(
        self,
        protocol_id: str,
        avg_cyclomatic: float,
        max_cyclomatic: int,
        total_lines: int
    ) -> Optional[RiskFactor]:
        """Assess code complexity risk."""
        profile = self.profiles.get(protocol_id)
        if not profile:
            return None

        score = 0.0
        evidence = []

        # High average complexity
        if avg_cyclomatic > 15:
            score += 0.4
            evidence.append(f"High average complexity: {avg_cyclomatic:.1f}")
        elif avg_cyclomatic > 10:
            score += 0.2
            evidence.append(f"Moderate complexity: {avg_cyclomatic:.1f}")

        # Very complex functions
        if max_cyclomatic > 50:
            score += 0.4
            evidence.append(f"Very complex function: complexity {max_cyclomatic}")
        elif max_cyclomatic > 25:
            score += 0.2
            evidence.append(f"Complex function: complexity {max_cyclomatic}")

        # Large codebase without organization
        if total_lines > 5000:
            score += 0.2
            evidence.append(f"Large codebase: {total_lines} lines")

        if score == 0:
            return None

        severity = RiskSeverity.HIGH if score >= 0.6 else RiskSeverity.MEDIUM
        _, correlation = self.FACTOR_CORRELATIONS[RiskFactorType.CODE_COMPLEXITY]

        factor = RiskFactor(
            factor_type=RiskFactorType.CODE_COMPLEXITY,
            severity=severity,
            score=min(1.0, score),
            description="Code complexity increases bug likelihood",
            evidence=evidence,
            exploit_correlation=correlation,
        )
        profile.add_factor(factor)
        return factor

    def assess_change_velocity(
        self,
        protocol_id: str,
        changes_last_week: int,
        changes_last_month: int,
        avg_changes_per_month: float
    ) -> Optional[RiskFactor]:
        """Assess risk from rapid changes."""
        profile = self.profiles.get(protocol_id)
        if not profile:
            return None

        score = 0.0
        evidence = []

        # Recent spike in changes
        if changes_last_week > avg_changes_per_month:
            score += 0.5
            evidence.append(f"Change spike: {changes_last_week} changes this week vs {avg_changes_per_month:.1f}/month avg")

        # High overall velocity
        if changes_last_month > avg_changes_per_month * 2:
            score += 0.3
            evidence.append(f"High velocity: {changes_last_month} changes this month")

        # Many changes = higher risk
        if changes_last_week > 10:
            score += 0.2
            evidence.append(f"Very active: {changes_last_week} changes in 7 days")

        if score == 0:
            return None

        severity = RiskSeverity.HIGH if score >= 0.6 else RiskSeverity.MEDIUM
        _, correlation = self.FACTOR_CORRELATIONS[RiskFactorType.RAPID_CHANGES]

        factor = RiskFactor(
            factor_type=RiskFactorType.RAPID_CHANGES,
            severity=severity,
            score=min(1.0, score),
            description="Rapid changes increase bug introduction risk",
            evidence=evidence,
            exploit_correlation=correlation,
        )
        profile.add_factor(factor)
        return factor

    def assess_audit_status(
        self,
        protocol_id: str,
        has_audit: bool,
        audit_age_days: Optional[int] = None,
        changes_since_audit: int = 0
    ) -> Optional[RiskFactor]:
        """Assess audit-related risk."""
        profile = self.profiles.get(protocol_id)
        if not profile:
            return None

        if not has_audit:
            _, correlation = self.FACTOR_CORRELATIONS[RiskFactorType.NO_AUDIT]
            factor = RiskFactor(
                factor_type=RiskFactorType.NO_AUDIT,
                severity=RiskSeverity.CRITICAL,
                score=1.0,
                description="Protocol has never been audited",
                evidence=["No audit records found"],
                exploit_correlation=correlation,
            )
            profile.add_factor(factor)
            return factor

        score = 0.0
        evidence = []

        # Stale audit
        if audit_age_days and audit_age_days > 180:
            score += 0.5
            evidence.append(f"Audit is {audit_age_days} days old")

        # Changes since audit
        if changes_since_audit > 50:
            score += 0.5
            evidence.append(f"{changes_since_audit} changes since last audit")
        elif changes_since_audit > 20:
            score += 0.3
            evidence.append(f"{changes_since_audit} changes since last audit")

        if score == 0:
            return None

        _, correlation = self.FACTOR_CORRELATIONS[RiskFactorType.STALE_AUDIT]

        factor = RiskFactor(
            factor_type=RiskFactorType.STALE_AUDIT,
            severity=RiskSeverity.HIGH if score >= 0.5 else RiskSeverity.MEDIUM,
            score=min(1.0, score),
            description="Audit may not reflect current code",
            evidence=evidence,
            exploit_correlation=correlation,
        )
        profile.add_factor(factor)
        return factor

    def assess_launch_timing(
        self,
        protocol_id: str,
        days_since_launch: int
    ) -> Optional[RiskFactor]:
        """Assess launch window risk."""
        profile = self.profiles.get(protocol_id)
        if not profile:
            return None

        if days_since_launch > 90:
            return None  # Past the high-risk window

        score = 0.0
        evidence = []

        if days_since_launch <= 7:
            score = 1.0
            evidence.append("First week post-launch (highest risk period)")
        elif days_since_launch <= 30:
            score = 0.7
            evidence.append(f"Launch window: {days_since_launch} days old")
        elif days_since_launch <= 90:
            score = 0.3
            evidence.append(f"Early stage: {days_since_launch} days old")

        _, correlation = self.FACTOR_CORRELATIONS[RiskFactorType.LAUNCH_WINDOW]

        factor = RiskFactor(
            factor_type=RiskFactorType.LAUNCH_WINDOW,
            severity=RiskSeverity.CRITICAL if score >= 0.7 else RiskSeverity.HIGH,
            score=score,
            description="New protocols face highest exploit risk",
            evidence=evidence,
            exploit_correlation=correlation,
        )
        profile.add_factor(factor)
        return factor

    def assess_tvl_growth(
        self,
        protocol_id: str,
        tvl_growth_30d_pct: float,
        current_tvl: float
    ) -> Optional[RiskFactor]:
        """Assess risk from rapid TVL growth."""
        profile = self.profiles.get(protocol_id)
        if not profile:
            return None

        score = 0.0
        evidence = []

        # Rapid growth attracts attackers
        if tvl_growth_30d_pct > 500:
            score += 0.8
            evidence.append(f"Explosive growth: {tvl_growth_30d_pct:.0f}% in 30 days")
        elif tvl_growth_30d_pct > 200:
            score += 0.5
            evidence.append(f"Rapid growth: {tvl_growth_30d_pct:.0f}% in 30 days")
        elif tvl_growth_30d_pct > 100:
            score += 0.3
            evidence.append(f"Strong growth: {tvl_growth_30d_pct:.0f}% in 30 days")

        # High TVL = higher target value
        if current_tvl > 100_000_000:  # $100M+
            score += 0.2
            evidence.append(f"High value target: ${current_tvl/1e6:.0f}M TVL")

        if score == 0:
            return None

        _, correlation = self.FACTOR_CORRELATIONS[RiskFactorType.HIGH_TVL_GROWTH]

        factor = RiskFactor(
            factor_type=RiskFactorType.HIGH_TVL_GROWTH,
            severity=RiskSeverity.HIGH if score >= 0.5 else RiskSeverity.MEDIUM,
            score=min(1.0, score),
            description="Rapid TVL growth attracts attacker attention",
            evidence=evidence,
            exploit_correlation=correlation,
        )
        profile.add_factor(factor)
        return factor

    def assess_competitor_exploit(
        self,
        protocol_id: str,
        similar_protocol_exploited: bool,
        days_since_exploit: int,
        exploit_type: Optional[str] = None
    ) -> Optional[RiskFactor]:
        """Assess risk from similar protocol exploits."""
        profile = self.profiles.get(protocol_id)
        if not profile:
            return None

        if not similar_protocol_exploited:
            return None

        score = 0.0
        evidence = []

        if days_since_exploit <= 7:
            score = 1.0
            evidence.append(f"Similar protocol exploited {days_since_exploit} days ago")
        elif days_since_exploit <= 30:
            score = 0.7
            evidence.append(f"Similar protocol exploited {days_since_exploit} days ago")
        elif days_since_exploit <= 90:
            score = 0.4
            evidence.append(f"Similar protocol exploited {days_since_exploit} days ago")
        else:
            return None

        if exploit_type:
            evidence.append(f"Exploit type: {exploit_type}")

        _, correlation = self.FACTOR_CORRELATIONS[RiskFactorType.COMPETITOR_EXPLOIT]

        factor = RiskFactor(
            factor_type=RiskFactorType.COMPETITOR_EXPLOIT,
            severity=RiskSeverity.CRITICAL if score >= 0.7 else RiskSeverity.HIGH,
            score=score,
            description="Similar protocols being targeted",
            evidence=evidence,
            exploit_correlation=correlation,
        )
        profile.add_factor(factor)
        return factor

    def assess_code_patterns(
        self,
        protocol_id: str,
        has_reentrancy_guards: bool,
        external_call_count: int,
        admin_function_count: int,
        uses_oracles: bool
    ) -> List[RiskFactor]:
        """Assess code pattern risks."""
        profile = self.profiles.get(protocol_id)
        if not profile:
            return []

        factors = []

        # Missing guards
        if not has_reentrancy_guards and external_call_count > 0:
            _, correlation = self.FACTOR_CORRELATIONS[RiskFactorType.MISSING_GUARDS]
            factor = RiskFactor(
                factor_type=RiskFactorType.MISSING_GUARDS,
                severity=RiskSeverity.HIGH,
                score=0.8,
                description="No reentrancy protection on external calls",
                evidence=[f"{external_call_count} external calls without guards"],
                exploit_correlation=correlation,
            )
            factors.append(factor)
            profile.add_factor(factor)

        # Many privileged functions
        if admin_function_count > 5:
            _, correlation = self.FACTOR_CORRELATIONS[RiskFactorType.PRIVILEGED_FUNCTIONS]
            factor = RiskFactor(
                factor_type=RiskFactorType.PRIVILEGED_FUNCTIONS,
                severity=RiskSeverity.MEDIUM,
                score=min(1.0, admin_function_count / 10),
                description="Many privileged functions increase centralization risk",
                evidence=[f"{admin_function_count} admin functions"],
                exploit_correlation=correlation,
            )
            factors.append(factor)
            profile.add_factor(factor)

        # Oracle dependence
        if uses_oracles:
            _, correlation = self.FACTOR_CORRELATIONS[RiskFactorType.ORACLE_DEPENDENCE]
            factor = RiskFactor(
                factor_type=RiskFactorType.ORACLE_DEPENDENCE,
                severity=RiskSeverity.MEDIUM,
                score=0.5,
                description="Protocol depends on external price feeds",
                evidence=["Uses oracle price data"],
                exploit_correlation=correlation,
            )
            factors.append(factor)
            profile.add_factor(factor)

        return factors

    def get_profile(self, protocol_id: str) -> Optional[RiskProfile]:
        """Get risk profile for a protocol."""
        return self.profiles.get(protocol_id)

    def get_high_risk_protocols(self, threshold: float = 60.0) -> List[RiskProfile]:
        """Get protocols above risk threshold."""
        return [
            p for p in self.profiles.values()
            if p.overall_risk_score >= threshold
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """Get calculator statistics."""
        if not self.profiles:
            return {"total_profiles": 0}

        scores = [p.overall_risk_score for p in self.profiles.values()]
        probs = [p.exploit_probability for p in self.profiles.values()]

        return {
            "total_profiles": len(self.profiles),
            "avg_risk_score": round(sum(scores) / len(scores), 1),
            "max_risk_score": round(max(scores), 1),
            "avg_exploit_probability": round(sum(probs) / len(probs), 3),
            "high_risk_count": len(self.get_high_risk_protocols()),
            "critical_count": len([
                p for p in self.profiles.values()
                if p.get_risk_level() == "CRITICAL"
            ]),
        }
