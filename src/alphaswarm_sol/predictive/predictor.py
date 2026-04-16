"""
Vulnerability Predictor

Combines all risk signals to predict future vulnerabilities:
- Code evolution analysis
- Market signal analysis
- Risk factor calculation
- Historical exploit patterns

Outputs predictions with confidence levels and recommended actions.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
from datetime import datetime, timedelta
import logging

from alphaswarm_sol.predictive.risk_factors import (
    RiskFactor,
    RiskProfile,
    RiskCalculator,
    RiskFactorType,
    RiskSeverity,
)
from alphaswarm_sol.predictive.code_evolution import (
    CodeEvolutionAnalyzer,
    EvolutionMetrics,
    ChangeVelocity,
)
from alphaswarm_sol.predictive.market_signals import (
    MarketSignalAnalyzer,
    ProtocolMarketProfile,
    ProtocolPhase,
    SignalType,
)

logger = logging.getLogger(__name__)


class PredictionConfidence(Enum):
    """Confidence levels for predictions."""
    VERY_HIGH = "very_high"     # >90% confidence
    HIGH = "high"               # 70-90% confidence
    MEDIUM = "medium"           # 50-70% confidence
    LOW = "low"                 # 30-50% confidence
    SPECULATIVE = "speculative" # <30% confidence


class VulnerabilityCategory(Enum):
    """Categories of predicted vulnerabilities."""
    REENTRANCY = "reentrancy"
    ACCESS_CONTROL = "access_control"
    ORACLE_MANIPULATION = "oracle_manipulation"
    FLASH_LOAN = "flash_loan"
    LOGIC_ERROR = "logic_error"
    UPGRADE_VULNERABILITY = "upgrade_vulnerability"
    ECONOMIC_ATTACK = "economic_attack"
    UNKNOWN = "unknown"


@dataclass
class RiskTimeline:
    """Timeline of predicted risk levels."""
    protocol_id: str
    predictions: List[Tuple[datetime, float]] = field(default_factory=list)

    def add_point(self, timestamp: datetime, risk_level: float):
        """Add a risk prediction point."""
        self.predictions.append((timestamp, risk_level))
        self.predictions.sort(key=lambda x: x[0])

    def get_peak_risk(self) -> Tuple[Optional[datetime], float]:
        """Get time of peak predicted risk."""
        if not self.predictions:
            return (None, 0.0)
        return max(self.predictions, key=lambda x: x[1])

    def get_risk_at(self, timestamp: datetime) -> float:
        """Get predicted risk at a specific time."""
        if not self.predictions:
            return 0.0

        # Find closest prediction
        closest = min(self.predictions, key=lambda x: abs((x[0] - timestamp).total_seconds()))
        return closest[1]

    def to_dict(self) -> Dict[str, Any]:
        peak_time, peak_risk = self.get_peak_risk()
        return {
            "protocol_id": self.protocol_id,
            "num_predictions": len(self.predictions),
            "peak_risk": round(peak_risk, 3),
            "peak_time": peak_time.isoformat() if peak_time else None,
            "timeline": [
                {"timestamp": t.isoformat(), "risk": round(r, 3)}
                for t, r in self.predictions[:10]
            ],
        }


@dataclass
class Prediction:
    """A vulnerability prediction."""
    prediction_id: str
    protocol_id: str

    # Prediction content
    vulnerability_category: VulnerabilityCategory
    description: str
    confidence: PredictionConfidence

    # Probability and timing
    probability: float          # 0-1 probability of exploit
    time_window_days: int       # Prediction window (e.g., next 30 days)
    peak_risk_date: Optional[datetime] = None

    # Contributing factors
    contributing_factors: List[str] = field(default_factory=list)
    risk_score: float = 0.0

    # Recommendations
    recommended_actions: List[str] = field(default_factory=list)
    priority: str = "medium"    # critical, high, medium, low

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    valid_until: datetime = field(default_factory=lambda: datetime.now() + timedelta(days=30))

    def is_valid(self) -> bool:
        """Check if prediction is still valid."""
        return datetime.now() < self.valid_until

    def get_urgency_score(self) -> float:
        """Calculate urgency (probability * inverse of time)."""
        days_remaining = max(1, (self.valid_until - datetime.now()).days)
        return self.probability * (30 / days_remaining)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "protocol_id": self.protocol_id,
            "vulnerability_category": self.vulnerability_category.value,
            "description": self.description,
            "confidence": self.confidence.value,
            "probability": round(self.probability, 3),
            "time_window_days": self.time_window_days,
            "risk_score": round(self.risk_score, 1),
            "priority": self.priority,
            "contributing_factors": self.contributing_factors,
            "recommended_actions": self.recommended_actions,
            "is_valid": self.is_valid(),
            "urgency_score": round(self.get_urgency_score(), 3),
            "created_at": self.created_at.isoformat(),
        }


class VulnerabilityPredictor:
    """
    Predicts future vulnerabilities by combining multiple risk signals.

    Uses:
    - Code evolution patterns
    - Market signals
    - Risk factor analysis
    - Historical exploit correlation
    """

    # Weights for different signal sources
    WEIGHTS = {
        "code_evolution": 0.3,
        "market_signals": 0.25,
        "risk_factors": 0.35,
        "historical": 0.1,
    }

    # Vulnerability category correlations
    CATEGORY_CORRELATIONS = {
        RiskFactorType.MISSING_GUARDS: VulnerabilityCategory.REENTRANCY,
        RiskFactorType.ORACLE_DEPENDENCE: VulnerabilityCategory.ORACLE_MANIPULATION,
        RiskFactorType.PRIVILEGED_FUNCTIONS: VulnerabilityCategory.ACCESS_CONTROL,
        RiskFactorType.RAPID_CHANGES: VulnerabilityCategory.LOGIC_ERROR,
        RiskFactorType.UPGRADE_FREQUENCY: VulnerabilityCategory.UPGRADE_VULNERABILITY,
        RiskFactorType.HIGH_TVL_GROWTH: VulnerabilityCategory.FLASH_LOAN,
        RiskFactorType.INCENTIVE_MISALIGNMENT: VulnerabilityCategory.ECONOMIC_ATTACK,
    }

    def __init__(
        self,
        risk_calculator: Optional[RiskCalculator] = None,
        evolution_analyzer: Optional[CodeEvolutionAnalyzer] = None,
        market_analyzer: Optional[MarketSignalAnalyzer] = None
    ):
        self.risk_calculator = risk_calculator or RiskCalculator()
        self.evolution = evolution_analyzer or CodeEvolutionAnalyzer()
        self.market = market_analyzer or MarketSignalAnalyzer()
        self.predictions: Dict[str, List[Prediction]] = {}
        self.timelines: Dict[str, RiskTimeline] = {}

    def analyze_protocol(
        self,
        protocol_id: str,
        protocol_name: Optional[str] = None
    ) -> RiskProfile:
        """Perform full analysis and return risk profile."""
        # Create or get risk profile
        profile = self.risk_calculator.get_profile(protocol_id)
        if not profile:
            profile = self.risk_calculator.create_profile(protocol_id, protocol_name)

        return profile

    def predict(
        self,
        protocol_id: str,
        time_window_days: int = 30
    ) -> List[Prediction]:
        """Generate vulnerability predictions for a protocol."""
        predictions = []

        # Get all analysis data
        risk_profile = self.risk_calculator.get_profile(protocol_id)
        evolution_metrics = self.evolution.get_metrics(protocol_id)
        market_profile = self.market.get_profile(protocol_id)

        # Calculate composite risk score
        composite_score = self._calculate_composite_score(
            risk_profile,
            evolution_metrics,
            market_profile
        )

        # Identify likely vulnerability categories
        likely_categories = self._identify_likely_categories(risk_profile)

        # Generate predictions for each category
        for category, category_score in likely_categories:
            if category_score < 0.2:  # Skip low probability
                continue

            prediction = self._create_prediction(
                protocol_id=protocol_id,
                category=category,
                base_score=composite_score,
                category_score=category_score,
                time_window_days=time_window_days,
                risk_profile=risk_profile,
                evolution_metrics=evolution_metrics,
                market_profile=market_profile,
            )
            predictions.append(prediction)

        # Store predictions
        self.predictions[protocol_id] = predictions

        # Generate timeline
        self._generate_timeline(protocol_id, composite_score, time_window_days)

        return predictions

    def _calculate_composite_score(
        self,
        risk_profile: Optional[RiskProfile],
        evolution_metrics: Optional[EvolutionMetrics],
        market_profile: Optional[ProtocolMarketProfile]
    ) -> float:
        """Calculate weighted composite risk score."""
        scores = []
        weights = []

        if risk_profile:
            scores.append(risk_profile.overall_risk_score / 100)
            weights.append(self.WEIGHTS["risk_factors"])

        if evolution_metrics:
            scores.append(evolution_metrics.get_risk_score())
            weights.append(self.WEIGHTS["code_evolution"])

        if market_profile:
            scores.append(market_profile.get_market_risk_score())
            weights.append(self.WEIGHTS["market_signals"])

        if not scores:
            return 0.0

        # Weighted average
        total_weight = sum(weights)
        if total_weight == 0:
            return 0.0

        return sum(s * w for s, w in zip(scores, weights)) / total_weight

    def _identify_likely_categories(
        self,
        risk_profile: Optional[RiskProfile]
    ) -> List[Tuple[VulnerabilityCategory, float]]:
        """Identify most likely vulnerability categories."""
        if not risk_profile or not risk_profile.factors:
            return [(VulnerabilityCategory.UNKNOWN, 0.3)]

        category_scores: Dict[VulnerabilityCategory, float] = {}

        for factor in risk_profile.factors:
            category = self.CATEGORY_CORRELATIONS.get(
                factor.factor_type,
                VulnerabilityCategory.UNKNOWN
            )
            if category not in category_scores:
                category_scores[category] = 0.0
            category_scores[category] += factor.get_weighted_score() / 4  # Normalize

        # Sort by score
        return sorted(
            category_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

    def _create_prediction(
        self,
        protocol_id: str,
        category: VulnerabilityCategory,
        base_score: float,
        category_score: float,
        time_window_days: int,
        risk_profile: Optional[RiskProfile],
        evolution_metrics: Optional[EvolutionMetrics],
        market_profile: Optional[ProtocolMarketProfile],
    ) -> Prediction:
        """Create a specific vulnerability prediction."""
        import hashlib

        # Calculate probability
        probability = min(1.0, base_score * category_score * 2)

        # Determine confidence
        confidence = self._determine_confidence(
            base_score,
            risk_profile,
            evolution_metrics,
            market_profile
        )

        # Gather contributing factors
        factors = self._gather_contributing_factors(
            category,
            risk_profile,
            evolution_metrics,
            market_profile
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(category, factors)

        # Determine priority
        priority = self._determine_priority(probability, confidence)

        # Calculate peak risk date
        peak_date = self._estimate_peak_risk_date(
            protocol_id,
            market_profile,
            time_window_days
        )

        # Generate prediction ID
        pred_id = hashlib.sha256(
            f"{protocol_id}:{category.value}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        return Prediction(
            prediction_id=f"PRED-{pred_id.upper()}",
            protocol_id=protocol_id,
            vulnerability_category=category,
            description=self._generate_description(category, probability),
            confidence=confidence,
            probability=probability,
            time_window_days=time_window_days,
            peak_risk_date=peak_date,
            contributing_factors=factors,
            risk_score=base_score * 100,
            recommended_actions=recommendations,
            priority=priority,
            valid_until=datetime.now() + timedelta(days=time_window_days),
        )

    def _determine_confidence(
        self,
        base_score: float,
        risk_profile: Optional[RiskProfile],
        evolution_metrics: Optional[EvolutionMetrics],
        market_profile: Optional[ProtocolMarketProfile],
    ) -> PredictionConfidence:
        """Determine confidence level based on data quality."""
        data_sources = 0
        if risk_profile and risk_profile.factors:
            data_sources += 1
        if evolution_metrics:
            data_sources += 1
        if market_profile:
            data_sources += 1

        if data_sources >= 3 and base_score > 0.7:
            return PredictionConfidence.VERY_HIGH
        elif data_sources >= 2 and base_score > 0.5:
            return PredictionConfidence.HIGH
        elif data_sources >= 2:
            return PredictionConfidence.MEDIUM
        elif data_sources >= 1:
            return PredictionConfidence.LOW
        else:
            return PredictionConfidence.SPECULATIVE

    def _gather_contributing_factors(
        self,
        category: VulnerabilityCategory,
        risk_profile: Optional[RiskProfile],
        evolution_metrics: Optional[EvolutionMetrics],
        market_profile: Optional[ProtocolMarketProfile],
    ) -> List[str]:
        """Gather human-readable contributing factors."""
        factors = []

        if risk_profile:
            for f in risk_profile.get_critical_factors()[:3]:
                factors.append(f.description)

        if evolution_metrics:
            if evolution_metrics.rushed_release_detected:
                factors.append("Rushed release detected (high change velocity)")
            if evolution_metrics.complexity_spike_detected:
                factors.append("Code complexity spike detected")
            if evolution_metrics.bus_factor == 1:
                factors.append("Single developer (high bus factor risk)")

        if market_profile:
            if market_profile.phase == ProtocolPhase.LAUNCH:
                factors.append("In launch window (highest risk period)")
            for signal in market_profile.get_active_signals()[:2]:
                factors.append(signal.description)

        return factors[:5]  # Limit to 5 most important

    def _generate_recommendations(
        self,
        category: VulnerabilityCategory,
        factors: List[str]
    ) -> List[str]:
        """Generate actionable recommendations."""
        base_recommendations = {
            VulnerabilityCategory.REENTRANCY: [
                "Add reentrancy guards to external call functions",
                "Implement CEI (Checks-Effects-Interactions) pattern",
                "Consider using OpenZeppelin ReentrancyGuard",
            ],
            VulnerabilityCategory.ACCESS_CONTROL: [
                "Review and minimize admin privileges",
                "Implement timelock for sensitive operations",
                "Add multi-sig requirements for critical functions",
            ],
            VulnerabilityCategory.ORACLE_MANIPULATION: [
                "Use TWAP instead of spot prices",
                "Add circuit breakers for price deviations",
                "Implement multiple oracle sources",
            ],
            VulnerabilityCategory.FLASH_LOAN: [
                "Add block.number checks to prevent same-block manipulation",
                "Implement minimum lock periods",
                "Use time-weighted price calculations",
            ],
            VulnerabilityCategory.LOGIC_ERROR: [
                "Increase test coverage for edge cases",
                "Conduct formal verification of critical functions",
                "Slow down deployment to allow thorough review",
            ],
            VulnerabilityCategory.UPGRADE_VULNERABILITY: [
                "Review storage layout compatibility",
                "Use transparent proxy pattern",
                "Implement upgrade timelock with community review",
            ],
            VulnerabilityCategory.ECONOMIC_ATTACK: [
                "Review tokenomics for attack vectors",
                "Add caps on single-transaction impact",
                "Implement gradual position building requirements",
            ],
        }

        recommendations = base_recommendations.get(
            category,
            ["Conduct comprehensive security audit"]
        )

        # Add generic recommendations
        recommendations.append("Schedule immediate security review")

        return recommendations[:4]

    def _determine_priority(
        self,
        probability: float,
        confidence: PredictionConfidence
    ) -> str:
        """Determine action priority."""
        confidence_weights = {
            PredictionConfidence.VERY_HIGH: 1.5,
            PredictionConfidence.HIGH: 1.2,
            PredictionConfidence.MEDIUM: 1.0,
            PredictionConfidence.LOW: 0.7,
            PredictionConfidence.SPECULATIVE: 0.4,
        }

        weighted_prob = probability * confidence_weights[confidence]

        if weighted_prob > 0.7:
            return "critical"
        elif weighted_prob > 0.5:
            return "high"
        elif weighted_prob > 0.3:
            return "medium"
        else:
            return "low"

    def _estimate_peak_risk_date(
        self,
        protocol_id: str,
        market_profile: Optional[ProtocolMarketProfile],
        window_days: int
    ) -> datetime:
        """Estimate when risk will peak."""
        base = datetime.now()

        # Launch window: peak in first 2 weeks
        if market_profile and market_profile.phase == ProtocolPhase.LAUNCH:
            return base + timedelta(days=7)

        # Competitor exploit: peak soon
        if market_profile:
            for signal in market_profile.signals:
                if signal.signal_type == SignalType.COMPETITOR_EXPLOIT:
                    return base + timedelta(days=3)

        # Default: middle of window
        return base + timedelta(days=window_days // 2)

    def _generate_description(
        self,
        category: VulnerabilityCategory,
        probability: float
    ) -> str:
        """Generate prediction description."""
        prob_text = "high" if probability > 0.6 else "moderate" if probability > 0.3 else "elevated"

        descriptions = {
            VulnerabilityCategory.REENTRANCY: f"{prob_text.title()} probability of reentrancy attack",
            VulnerabilityCategory.ACCESS_CONTROL: f"{prob_text.title()} risk of access control bypass",
            VulnerabilityCategory.ORACLE_MANIPULATION: f"{prob_text.title()} exposure to oracle manipulation",
            VulnerabilityCategory.FLASH_LOAN: f"{prob_text.title()} vulnerability to flash loan attack",
            VulnerabilityCategory.LOGIC_ERROR: f"{prob_text.title()} likelihood of logic bug exploitation",
            VulnerabilityCategory.UPGRADE_VULNERABILITY: f"{prob_text.title()} risk in upgrade mechanism",
            VulnerabilityCategory.ECONOMIC_ATTACK: f"{prob_text.title()} exposure to economic attack",
            VulnerabilityCategory.UNKNOWN: f"{prob_text.title()} general security risk",
        }
        return descriptions.get(category, f"{prob_text.title()} security risk")

    def _generate_timeline(
        self,
        protocol_id: str,
        base_score: float,
        window_days: int
    ):
        """Generate risk timeline."""
        timeline = RiskTimeline(protocol_id=protocol_id)
        now = datetime.now()

        # Generate points at regular intervals
        for day in range(0, window_days + 1, max(1, window_days // 10)):
            timestamp = now + timedelta(days=day)

            # Risk curve: peaks in first third, then declines
            if day <= window_days // 3:
                factor = 1.0 + (day / (window_days // 3)) * 0.3
            else:
                remaining = window_days - day
                factor = 0.7 + (remaining / window_days) * 0.3

            risk = base_score * factor
            timeline.add_point(timestamp, min(1.0, risk))

        self.timelines[protocol_id] = timeline

    def get_predictions(
        self,
        protocol_id: str,
        min_confidence: Optional[PredictionConfidence] = None
    ) -> List[Prediction]:
        """Get predictions for a protocol."""
        predictions = self.predictions.get(protocol_id, [])

        if min_confidence:
            confidence_order = [
                PredictionConfidence.SPECULATIVE,
                PredictionConfidence.LOW,
                PredictionConfidence.MEDIUM,
                PredictionConfidence.HIGH,
                PredictionConfidence.VERY_HIGH,
            ]
            min_index = confidence_order.index(min_confidence)
            predictions = [
                p for p in predictions
                if confidence_order.index(p.confidence) >= min_index
            ]

        return predictions

    def get_timeline(self, protocol_id: str) -> Optional[RiskTimeline]:
        """Get risk timeline for a protocol."""
        return self.timelines.get(protocol_id)

    def get_high_risk_predictions(self, min_probability: float = 0.5) -> List[Prediction]:
        """Get all high-risk predictions across protocols."""
        high_risk = []
        for predictions in self.predictions.values():
            for p in predictions:
                if p.probability >= min_probability and p.is_valid():
                    high_risk.append(p)
        return sorted(high_risk, key=lambda p: p.probability, reverse=True)

    def get_statistics(self) -> Dict[str, Any]:
        """Get predictor statistics."""
        all_predictions = []
        for preds in self.predictions.values():
            all_predictions.extend(preds)

        if not all_predictions:
            return {"total_predictions": 0}

        by_priority = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        by_category = {c.value: 0 for c in VulnerabilityCategory}

        for p in all_predictions:
            by_priority[p.priority] += 1
            by_category[p.vulnerability_category.value] += 1

        avg_prob = sum(p.probability for p in all_predictions) / len(all_predictions)

        return {
            "total_protocols": len(self.predictions),
            "total_predictions": len(all_predictions),
            "avg_probability": round(avg_prob, 3),
            "by_priority": by_priority,
            "by_category": {k: v for k, v in by_category.items() if v > 0},
            "critical_count": by_priority["critical"],
            "high_risk_count": len(self.get_high_risk_predictions()),
        }
