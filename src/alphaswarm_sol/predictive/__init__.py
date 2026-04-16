"""
Predictive Vulnerability Intelligence Module (Novel Solution 6)

Predicts vulnerabilities BEFORE they're exploited by analyzing:
- Code evolution patterns (rushed changes, complexity spikes)
- Developer behavior indicators (commit patterns, review quality)
- Market conditions (TVL growth, protocol launch timing)
- Historical exploit patterns (similar protocols, timing)

This enables PROACTIVE security rather than reactive detection.
"""

from alphaswarm_sol.predictive.risk_factors import (
    RiskFactor,
    RiskFactorType,
    RiskProfile,
    RiskCalculator,
)

from alphaswarm_sol.predictive.code_evolution import (
    CodeEvolutionAnalyzer,
    EvolutionMetrics,
    ChangeVelocity,
    ComplexityTrend,
)

from alphaswarm_sol.predictive.market_signals import (
    MarketSignalAnalyzer,
    MarketSignal,
    SignalType,
    ProtocolPhase,
)

from alphaswarm_sol.predictive.predictor import (
    VulnerabilityPredictor,
    Prediction,
    PredictionConfidence,
    RiskTimeline,
)

__all__ = [
    # Risk Factors
    "RiskFactor",
    "RiskFactorType",
    "RiskProfile",
    "RiskCalculator",
    # Code Evolution
    "CodeEvolutionAnalyzer",
    "EvolutionMetrics",
    "ChangeVelocity",
    "ComplexityTrend",
    # Market Signals
    "MarketSignalAnalyzer",
    "MarketSignal",
    "SignalType",
    "ProtocolPhase",
    # Predictor
    "VulnerabilityPredictor",
    "Prediction",
    "PredictionConfidence",
    "RiskTimeline",
]
