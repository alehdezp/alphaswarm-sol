"""
Health Score Calculator

Calculates security health scores for contracts and protocols.
Provides quantitative security assessment for comparison and trending.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class HealthTrend(Enum):
    """Trend direction for health score."""
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"
    NEW = "new"  # Not enough history


@dataclass
class HealthFactors:
    """
    Factors that contribute to health score.
    """
    # Vulnerability counts
    critical_vulns: int = 0
    high_vulns: int = 0
    medium_vulns: int = 0
    low_vulns: int = 0

    # Best practices
    has_reentrancy_guard: bool = False
    has_access_control: bool = False
    has_pause_mechanism: bool = False
    uses_safe_math: bool = True         # Default true for Solidity 0.8+
    uses_safe_transfers: bool = False

    # Code quality
    functions_with_natspec: float = 0.0  # Percentage
    test_coverage: float = 0.0           # Percentage

    # History
    previous_audits: int = 0
    days_since_last_audit: int = 0
    known_exploits: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "vulnerabilities": {
                "critical": self.critical_vulns,
                "high": self.high_vulns,
                "medium": self.medium_vulns,
                "low": self.low_vulns,
            },
            "best_practices": {
                "has_reentrancy_guard": self.has_reentrancy_guard,
                "has_access_control": self.has_access_control,
                "has_pause_mechanism": self.has_pause_mechanism,
                "uses_safe_math": self.uses_safe_math,
                "uses_safe_transfers": self.uses_safe_transfers,
            },
            "quality": {
                "functions_with_natspec": self.functions_with_natspec,
                "test_coverage": self.test_coverage,
            },
            "history": {
                "previous_audits": self.previous_audits,
                "days_since_last_audit": self.days_since_last_audit,
                "known_exploits": self.known_exploits,
            }
        }


@dataclass
class HealthScore:
    """
    Security health score for a contract/protocol.
    """
    contract_address: str
    score: int                          # 0-100
    grade: str                          # A+, A, B, C, D, F
    trend: HealthTrend

    factors: HealthFactors
    timestamp: datetime

    # Score breakdown
    vuln_deduction: int = 0
    best_practice_bonus: int = 0
    quality_bonus: int = 0

    # Recommendations
    recommendations: List[str] = field(default_factory=list)

    def __post_init__(self):
        self._calculate_grade()

    def _calculate_grade(self):
        """Calculate letter grade from score."""
        if self.score >= 95:
            self.grade = "A+"
        elif self.score >= 90:
            self.grade = "A"
        elif self.score >= 85:
            self.grade = "A-"
        elif self.score >= 80:
            self.grade = "B+"
        elif self.score >= 75:
            self.grade = "B"
        elif self.score >= 70:
            self.grade = "B-"
        elif self.score >= 65:
            self.grade = "C+"
        elif self.score >= 60:
            self.grade = "C"
        elif self.score >= 55:
            self.grade = "C-"
        elif self.score >= 50:
            self.grade = "D"
        else:
            self.grade = "F"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "contract_address": self.contract_address,
            "score": self.score,
            "grade": self.grade,
            "trend": self.trend.value,
            "factors": self.factors.to_dict(),
            "breakdown": {
                "vuln_deduction": self.vuln_deduction,
                "best_practice_bonus": self.best_practice_bonus,
                "quality_bonus": self.quality_bonus,
            },
            "recommendations": self.recommendations,
            "timestamp": self.timestamp.isoformat(),
        }

    def get_summary(self) -> str:
        """Get human-readable summary."""
        icon = "🟢" if self.score >= 80 else "🟡" if self.score >= 60 else "🔴"

        lines = [
            f"Health Score: {icon} {self.score}/100 ({self.grade})",
            f"Trend: {self.trend.value}",
            "",
            "Vulnerabilities:",
            f"  Critical: {self.factors.critical_vulns}",
            f"  High: {self.factors.high_vulns}",
            f"  Medium: {self.factors.medium_vulns}",
            f"  Low: {self.factors.low_vulns}",
        ]

        if self.recommendations:
            lines.append("")
            lines.append("Recommendations:")
            for rec in self.recommendations[:5]:
                lines.append(f"  • {rec}")

        return "\n".join(lines)


class HealthScoreCalculator:
    """
    Calculates security health scores.
    """

    # Severity weights for deductions
    SEVERITY_WEIGHTS = {
        "critical": 30,
        "high": 15,
        "medium": 5,
        "low": 1,
    }

    # Best practice bonuses
    BEST_PRACTICE_BONUSES = {
        "has_reentrancy_guard": 5,
        "has_access_control": 5,
        "has_pause_mechanism": 3,
        "uses_safe_math": 2,
        "uses_safe_transfers": 3,
    }

    def __init__(self):
        self._history: Dict[str, List[HealthScore]] = {}

    def calculate(
        self,
        contract_address: str,
        factors: HealthFactors,
    ) -> HealthScore:
        """
        Calculate health score for a contract.

        Args:
            contract_address: Contract address
            factors: Health factors

        Returns:
            HealthScore with grade and recommendations
        """
        # Start at 100
        score = 100

        # Deduct for vulnerabilities
        vuln_deduction = (
            factors.critical_vulns * self.SEVERITY_WEIGHTS["critical"] +
            factors.high_vulns * self.SEVERITY_WEIGHTS["high"] +
            factors.medium_vulns * self.SEVERITY_WEIGHTS["medium"] +
            factors.low_vulns * self.SEVERITY_WEIGHTS["low"]
        )
        score -= vuln_deduction

        # Bonus for best practices
        best_practice_bonus = 0
        if factors.has_reentrancy_guard:
            best_practice_bonus += self.BEST_PRACTICE_BONUSES["has_reentrancy_guard"]
        if factors.has_access_control:
            best_practice_bonus += self.BEST_PRACTICE_BONUSES["has_access_control"]
        if factors.has_pause_mechanism:
            best_practice_bonus += self.BEST_PRACTICE_BONUSES["has_pause_mechanism"]
        if factors.uses_safe_math:
            best_practice_bonus += self.BEST_PRACTICE_BONUSES["uses_safe_math"]
        if factors.uses_safe_transfers:
            best_practice_bonus += self.BEST_PRACTICE_BONUSES["uses_safe_transfers"]

        score += best_practice_bonus

        # Quality bonus (up to 5 points)
        quality_bonus = int(
            (factors.functions_with_natspec / 100) * 2 +
            (factors.test_coverage / 100) * 3
        )
        score += quality_bonus

        # Deduct for lack of audits or stale audits
        if factors.previous_audits == 0:
            score -= 10
        elif factors.days_since_last_audit > 365:
            score -= 5

        # Deduct for known exploits
        score -= factors.known_exploits * 20

        # Clamp score
        score = max(0, min(100, score))

        # Determine trend
        trend = self._calculate_trend(contract_address, score)

        # Generate recommendations
        recommendations = self._generate_recommendations(factors, score)

        health_score = HealthScore(
            contract_address=contract_address,
            score=score,
            grade="",  # Will be set in __post_init__
            trend=trend,
            factors=factors,
            timestamp=datetime.now(),
            vuln_deduction=vuln_deduction,
            best_practice_bonus=best_practice_bonus,
            quality_bonus=quality_bonus,
            recommendations=recommendations,
        )

        # Store in history
        if contract_address not in self._history:
            self._history[contract_address] = []
        self._history[contract_address].append(health_score)

        return health_score

    def _calculate_trend(self, contract_address: str, current_score: int) -> HealthTrend:
        """Calculate trend based on history."""
        history = self._history.get(contract_address, [])

        if len(history) < 2:
            return HealthTrend.NEW

        # Compare with last score
        last_score = history[-1].score

        if current_score > last_score + 5:
            return HealthTrend.IMPROVING
        elif current_score < last_score - 5:
            return HealthTrend.DECLINING
        else:
            return HealthTrend.STABLE

    def _generate_recommendations(
        self,
        factors: HealthFactors,
        score: int
    ) -> List[str]:
        """Generate recommendations based on factors."""
        recommendations = []

        # Critical vulnerabilities
        if factors.critical_vulns > 0:
            recommendations.append(
                f"URGENT: Address {factors.critical_vulns} critical vulnerability(ies) immediately"
            )

        if factors.high_vulns > 0:
            recommendations.append(
                f"Address {factors.high_vulns} high severity vulnerability(ies)"
            )

        # Missing best practices
        if not factors.has_reentrancy_guard:
            recommendations.append("Add reentrancy guards to state-changing functions")

        if not factors.has_access_control:
            recommendations.append("Implement access control for privileged functions")

        if not factors.has_pause_mechanism:
            recommendations.append("Consider adding pause functionality for emergencies")

        if not factors.uses_safe_transfers:
            recommendations.append("Use SafeERC20 for token transfers")

        # Quality recommendations
        if factors.test_coverage < 80:
            recommendations.append(
                f"Improve test coverage (currently {factors.test_coverage:.0f}%)"
            )

        if factors.functions_with_natspec < 50:
            recommendations.append("Add NatSpec documentation to functions")

        # Audit recommendations
        if factors.previous_audits == 0:
            recommendations.append("Schedule a professional security audit")
        elif factors.days_since_last_audit > 365:
            recommendations.append("Consider a new audit (last audit over 1 year ago)")

        return recommendations

    def compare_contracts(
        self,
        scores: List[HealthScore]
    ) -> Dict[str, Any]:
        """Compare health scores across contracts."""
        if not scores:
            return {}

        sorted_scores = sorted(scores, key=lambda s: s.score, reverse=True)

        return {
            "best": sorted_scores[0].contract_address,
            "worst": sorted_scores[-1].contract_address,
            "average_score": sum(s.score for s in scores) / len(scores),
            "ranking": [
                {
                    "address": s.contract_address,
                    "score": s.score,
                    "grade": s.grade,
                }
                for s in sorted_scores
            ],
        }

    def get_history(self, contract_address: str) -> List[HealthScore]:
        """Get score history for a contract."""
        return self._history.get(contract_address, [])

    def clear_history(self, contract_address: Optional[str] = None):
        """Clear history for a contract or all contracts."""
        if contract_address:
            self._history.pop(contract_address, None)
        else:
            self._history.clear()

    def calculate_from_findings(
        self,
        contract_address: str,
        findings: List[Dict[str, Any]],
        code_analysis: Optional[Dict[str, Any]] = None
    ) -> HealthScore:
        """
        Calculate health score from VKG findings.

        Args:
            contract_address: Contract address
            findings: List of finding dictionaries with 'severity' key
            code_analysis: Optional code analysis results

        Returns:
            HealthScore
        """
        # Count vulnerabilities by severity
        critical = sum(1 for f in findings if f.get("severity") == "critical")
        high = sum(1 for f in findings if f.get("severity") == "high")
        medium = sum(1 for f in findings if f.get("severity") == "medium")
        low = sum(1 for f in findings if f.get("severity") == "low")

        # Extract best practices from code analysis
        has_reentrancy = False
        has_access = False
        has_pause = False
        uses_safe_transfers = False

        if code_analysis:
            has_reentrancy = code_analysis.get("has_reentrancy_guard", False)
            has_access = code_analysis.get("has_access_control", False)
            has_pause = code_analysis.get("has_pause_mechanism", False)
            uses_safe_transfers = code_analysis.get("uses_safe_erc20", False)

        factors = HealthFactors(
            critical_vulns=critical,
            high_vulns=high,
            medium_vulns=medium,
            low_vulns=low,
            has_reentrancy_guard=has_reentrancy,
            has_access_control=has_access,
            has_pause_mechanism=has_pause,
            uses_safe_transfers=uses_safe_transfers,
        )

        return self.calculate(contract_address, factors)
