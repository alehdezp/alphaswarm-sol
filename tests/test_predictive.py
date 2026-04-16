"""
Tests for Predictive Vulnerability Intelligence (Novel Solution 6)

Tests the predictive system including:
- Risk factor calculation
- Code evolution analysis
- Market signal analysis
- Vulnerability prediction
"""

import unittest
from datetime import datetime, timedelta

from alphaswarm_sol.predictive import (
    # Risk Factors
    RiskFactor,
    RiskFactorType,
    RiskProfile,
    RiskCalculator,
    # Code Evolution
    CodeEvolutionAnalyzer,
    EvolutionMetrics,
    ChangeVelocity,
    ComplexityTrend,
    # Market Signals
    MarketSignalAnalyzer,
    MarketSignal,
    SignalType,
    ProtocolPhase,
    # Predictor
    VulnerabilityPredictor,
    Prediction,
    PredictionConfidence,
    RiskTimeline,
)
from alphaswarm_sol.predictive.risk_factors import RiskSeverity
from alphaswarm_sol.predictive.predictor import VulnerabilityCategory


class TestRiskFactors(unittest.TestCase):
    """Test risk factor calculation."""

    def test_risk_factor_creation(self):
        """Test creating a risk factor."""
        factor = RiskFactor(
            factor_type=RiskFactorType.CODE_COMPLEXITY,
            severity=RiskSeverity.HIGH,
            score=0.8,
            description="High code complexity",
            evidence=["Cyclomatic complexity > 20"],
            exploit_correlation=0.35,
        )

        self.assertEqual(factor.factor_type, RiskFactorType.CODE_COMPLEXITY)
        self.assertEqual(factor.severity, RiskSeverity.HIGH)
        self.assertAlmostEqual(factor.score, 0.8)

    def test_weighted_score(self):
        """Test weighted score calculation."""
        factor = RiskFactor(
            factor_type=RiskFactorType.LAUNCH_WINDOW,
            severity=RiskSeverity.CRITICAL,
            score=1.0,
            description="Launch window",
        )

        # Critical = 4x weight
        self.assertEqual(factor.get_weighted_score(), 4.0)

    def test_risk_profile_creation(self):
        """Test creating a risk profile."""
        profile = RiskProfile(
            protocol_id="test-protocol",
            protocol_name="Test Protocol",
        )

        self.assertEqual(profile.protocol_id, "test-protocol")
        self.assertEqual(profile.overall_risk_score, 0.0)

    def test_risk_profile_scoring(self):
        """Test risk profile score calculation."""
        profile = RiskProfile(
            protocol_id="test-protocol",
            factors=[
                RiskFactor(
                    factor_type=RiskFactorType.NO_AUDIT,
                    severity=RiskSeverity.CRITICAL,
                    score=1.0,
                    description="No audit",
                    exploit_correlation=0.6,
                ),
                RiskFactor(
                    factor_type=RiskFactorType.LAUNCH_WINDOW,
                    severity=RiskSeverity.CRITICAL,
                    score=0.8,
                    description="Launch window",
                    exploit_correlation=0.7,
                ),
            ]
        )

        self.assertGreater(profile.overall_risk_score, 0)
        self.assertGreater(profile.exploit_probability, 0)

    def test_risk_level(self):
        """Test risk level classification."""
        profile = RiskProfile(protocol_id="test")
        profile.overall_risk_score = 85

        self.assertEqual(profile.get_risk_level(), "CRITICAL")

        profile.overall_risk_score = 65
        self.assertEqual(profile.get_risk_level(), "HIGH")

        profile.overall_risk_score = 45
        self.assertEqual(profile.get_risk_level(), "MEDIUM")


class TestRiskCalculator(unittest.TestCase):
    """Test risk calculator functionality."""

    def setUp(self):
        self.calculator = RiskCalculator()
        self.calculator.create_profile("test-protocol", "Test Protocol")

    def test_assess_code_complexity(self):
        """Test code complexity assessment."""
        factor = self.calculator.assess_code_complexity(
            "test-protocol",
            avg_cyclomatic=20.0,
            max_cyclomatic=60,
            total_lines=6000,
        )

        self.assertIsNotNone(factor)
        self.assertEqual(factor.factor_type, RiskFactorType.CODE_COMPLEXITY)
        self.assertGreater(factor.score, 0)

    def test_assess_change_velocity(self):
        """Test change velocity assessment."""
        factor = self.calculator.assess_change_velocity(
            "test-protocol",
            changes_last_week=25,
            changes_last_month=50,
            avg_changes_per_month=10.0,
        )

        self.assertIsNotNone(factor)
        self.assertEqual(factor.factor_type, RiskFactorType.RAPID_CHANGES)

    def test_assess_no_audit(self):
        """Test audit assessment - no audit."""
        factor = self.calculator.assess_audit_status(
            "test-protocol",
            has_audit=False,
        )

        self.assertIsNotNone(factor)
        self.assertEqual(factor.factor_type, RiskFactorType.NO_AUDIT)
        self.assertEqual(factor.severity, RiskSeverity.CRITICAL)

    def test_assess_stale_audit(self):
        """Test audit assessment - stale audit."""
        factor = self.calculator.assess_audit_status(
            "test-protocol",
            has_audit=True,
            audit_age_days=200,
            changes_since_audit=60,
        )

        self.assertIsNotNone(factor)
        self.assertEqual(factor.factor_type, RiskFactorType.STALE_AUDIT)

    def test_assess_launch_timing(self):
        """Test launch timing assessment."""
        factor = self.calculator.assess_launch_timing(
            "test-protocol",
            days_since_launch=5,
        )

        self.assertIsNotNone(factor)
        self.assertEqual(factor.factor_type, RiskFactorType.LAUNCH_WINDOW)
        self.assertEqual(factor.severity, RiskSeverity.CRITICAL)

    def test_assess_tvl_growth(self):
        """Test TVL growth assessment."""
        factor = self.calculator.assess_tvl_growth(
            "test-protocol",
            tvl_growth_30d_pct=300,
            current_tvl=150_000_000,
        )

        self.assertIsNotNone(factor)
        self.assertEqual(factor.factor_type, RiskFactorType.HIGH_TVL_GROWTH)

    def test_assess_competitor_exploit(self):
        """Test competitor exploit assessment."""
        factor = self.calculator.assess_competitor_exploit(
            "test-protocol",
            similar_protocol_exploited=True,
            days_since_exploit=3,
            exploit_type="reentrancy",
        )

        self.assertIsNotNone(factor)
        self.assertEqual(factor.factor_type, RiskFactorType.COMPETITOR_EXPLOIT)
        self.assertEqual(factor.severity, RiskSeverity.CRITICAL)

    def test_assess_code_patterns(self):
        """Test code pattern assessment."""
        factors = self.calculator.assess_code_patterns(
            "test-protocol",
            has_reentrancy_guards=False,
            external_call_count=10,
            admin_function_count=8,
            uses_oracles=True,
        )

        self.assertGreater(len(factors), 0)
        factor_types = [f.factor_type for f in factors]
        self.assertIn(RiskFactorType.MISSING_GUARDS, factor_types)

    def test_get_high_risk_protocols(self):
        """Test getting high risk protocols."""
        # Add high risk factors
        self.calculator.assess_code_complexity("test-protocol", 25, 70, 8000)
        self.calculator.assess_launch_timing("test-protocol", 3)
        self.calculator.assess_audit_status("test-protocol", False)

        high_risk = self.calculator.get_high_risk_protocols(threshold=30.0)
        self.assertGreater(len(high_risk), 0)


class TestCodeEvolutionAnalyzer(unittest.TestCase):
    """Test code evolution analysis."""

    def setUp(self):
        self.analyzer = CodeEvolutionAnalyzer()

    def test_record_change(self):
        """Test recording a code change."""
        change = self.analyzer.record_change(
            protocol_id="test-protocol",
            author="alice",
            files_changed=5,
            lines_added=200,
            lines_removed=50,
            commit_message="Fix reentrancy",
        )

        self.assertIsNotNone(change.change_id)
        self.assertEqual(change.churn, 250)

    def test_change_velocity(self):
        """Test change velocity calculation."""
        # Add many changes
        for i in range(30):
            self.analyzer.record_change(
                protocol_id="test-protocol",
                author="alice",
                files_changed=2,
                lines_added=50,
                lines_removed=20,
                timestamp=datetime.now() - timedelta(days=i % 7),
            )

        metrics = self.analyzer.analyze("test-protocol")
        self.assertEqual(metrics.velocity, ChangeVelocity.RAPID)

    def test_complexity_tracking(self):
        """Test complexity snapshot tracking."""
        # Need to add some changes for analyze() to work
        self.analyzer.record_change(
            "test-protocol",
            author="alice",
            files_changed=2,
            lines_added=100,
            lines_removed=20,
        )

        # Initial complexity
        self.analyzer.record_complexity(
            "test-protocol",
            total_functions=50,
            avg_cyclomatic=8.0,
            max_cyclomatic=25,
            total_lines=2000,
            timestamp=datetime.now() - timedelta(days=30),
        )

        # Increased complexity (87.5% increase - above 50% spike threshold)
        self.analyzer.record_complexity(
            "test-protocol",
            total_functions=60,
            avg_cyclomatic=15.0,  # 87.5% increase
            max_cyclomatic=45,
            total_lines=3000,
        )

        metrics = self.analyzer.analyze("test-protocol")
        self.assertEqual(metrics.complexity_trend, ComplexityTrend.SPIKING)
        self.assertTrue(metrics.complexity_spike_detected)

    def test_bus_factor(self):
        """Test bus factor calculation."""
        # Single developer
        for _ in range(20):
            self.analyzer.record_change(
                "single-dev-protocol",
                author="alice",
                files_changed=3,
                lines_added=100,
                lines_removed=20,
            )

        metrics = self.analyzer.analyze("single-dev-protocol")
        self.assertEqual(metrics.bus_factor, 1)

    def test_rushed_release_detection(self):
        """Test rushed release detection."""
        # Many changes in short time
        for i in range(25):
            self.analyzer.record_change(
                "rushed-protocol",
                author="alice",
                files_changed=2,
                lines_added=50,
                lines_removed=10,
                timestamp=datetime.now() - timedelta(hours=i),
            )

        metrics = self.analyzer.analyze("rushed-protocol")
        self.assertTrue(metrics.rushed_release_detected)

    def test_weekend_night_tracking(self):
        """Test weekend and night change tracking."""
        # Weekend changes
        saturday = datetime.now()
        while saturday.weekday() != 5:  # Find Saturday
            saturday -= timedelta(days=1)

        for i in range(5):
            self.analyzer.record_change(
                "weekend-protocol",
                author="alice",
                files_changed=2,
                lines_added=30,
                lines_removed=10,
                timestamp=saturday + timedelta(hours=i),
            )

        metrics = self.analyzer.analyze("weekend-protocol")
        self.assertGreater(metrics.weekend_changes_pct, 0)

    def test_hotspot_detection(self):
        """Test file hotspot detection."""
        # Add many changes
        for i in range(20):
            self.analyzer.record_change(
                "hotspot-protocol",
                author="alice",
                files_changed=3,
                lines_added=100,
                lines_removed=30,
            )

        hotspots = self.analyzer.find_hotspots("hotspot-protocol")
        self.assertGreater(len(hotspots), 0)

    def test_evolution_risk_score(self):
        """Test evolution-based risk score."""
        # Create high-risk evolution pattern
        for i in range(50):
            self.analyzer.record_change(
                "risky-evolution",
                author="alice" if i < 45 else "bob",  # Mostly single dev
                files_changed=3,
                lines_added=100,
                lines_removed=20,
                timestamp=datetime.now() - timedelta(days=i % 7),
            )

        metrics = self.analyzer.analyze("risky-evolution")
        risk_score = metrics.get_risk_score()
        self.assertGreater(risk_score, 0)


class TestMarketSignalAnalyzer(unittest.TestCase):
    """Test market signal analysis."""

    def setUp(self):
        self.analyzer = MarketSignalAnalyzer()
        self.analyzer.create_profile(
            "test-protocol",
            "Test Protocol",
            launch_date=datetime.now() - timedelta(days=10),
        )

    def test_tvl_spike_detection(self):
        """Test TVL spike signal."""
        self.analyzer.update_tvl(
            "test-protocol",
            current_tvl=100_000_000,
            tvl_7d_ago=30_000_000,
            tvl_30d_ago=20_000_000,
        )

        profile = self.analyzer.get_profile("test-protocol")
        signals = profile.get_active_signals()

        spike_signals = [s for s in signals if s.signal_type == SignalType.TVL_SPIKE]
        self.assertGreater(len(spike_signals), 0)

    def test_tvl_decline_detection(self):
        """Test TVL decline signal."""
        self.analyzer.update_tvl(
            "test-protocol",
            current_tvl=50_000_000,
            tvl_7d_ago=100_000_000,
            tvl_30d_ago=120_000_000,
        )

        profile = self.analyzer.get_profile("test-protocol")
        signals = profile.get_active_signals()

        decline_signals = [s for s in signals if s.signal_type == SignalType.TVL_DECLINE]
        self.assertGreater(len(decline_signals), 0)

    def test_high_yield_detection(self):
        """Test high yield signal."""
        profile = self.analyzer.get_profile("test-protocol")
        profile.sustainable_apy = 10.0

        self.analyzer.update_yield("test-protocol", current_apy=50.0)

        signals = profile.get_active_signals()
        yield_signals = [s for s in signals if s.signal_type == SignalType.HIGH_YIELD]
        self.assertGreater(len(yield_signals), 0)

    def test_competitor_exploit(self):
        """Test competitor exploit signal."""
        self.analyzer.record_competitor_exploit(
            exploited_protocol="SimilarProtocol",
            exploit_type="reentrancy",
            amount_lost=50_000_000,
            similar_protocols=["test-protocol"],
        )

        profile = self.analyzer.get_profile("test-protocol")
        signals = profile.get_active_signals()

        exploit_signals = [s for s in signals if s.signal_type == SignalType.COMPETITOR_EXPLOIT]
        self.assertGreater(len(exploit_signals), 0)

    def test_whale_movement(self):
        """Test whale movement signal."""
        self.analyzer.update_tvl("test-protocol", current_tvl=100_000_000)

        self.analyzer.record_whale_movement(
            "test-protocol",
            amount=10_000_000,  # 10% of TVL
            is_deposit=False,
        )

        profile = self.analyzer.get_profile("test-protocol")
        signals = profile.get_active_signals()

        whale_signals = [s for s in signals if s.signal_type == SignalType.WHALE_MOVEMENT]
        self.assertGreater(len(whale_signals), 0)

    def test_market_volatility(self):
        """Test market volatility signal."""
        self.analyzer.set_market_volatility(75.0)

        profile = self.analyzer.get_profile("test-protocol")
        signals = profile.get_active_signals()

        vol_signals = [s for s in signals if s.signal_type == SignalType.MARKET_VOLATILITY]
        self.assertGreater(len(vol_signals), 0)

    def test_protocol_phase(self):
        """Test protocol phase calculation."""
        # Launch phase (10 days old)
        profile = self.analyzer.get_profile("test-protocol")
        self.assertEqual(profile.phase, ProtocolPhase.LAUNCH)

        # Growth phase
        growth_profile = self.analyzer.create_profile(
            "growth-protocol",
            launch_date=datetime.now() - timedelta(days=60),
        )
        self.assertEqual(growth_profile.phase, ProtocolPhase.GROWTH)

        # Mature phase
        mature_profile = self.analyzer.create_profile(
            "mature-protocol",
            launch_date=datetime.now() - timedelta(days=400),
        )
        self.assertEqual(mature_profile.phase, ProtocolPhase.MATURE)

    def test_market_risk_score(self):
        """Test market risk score calculation."""
        profile = self.analyzer.get_profile("test-protocol")
        profile.current_tvl = 100_000_000
        profile.tvl_30d_ago = 20_000_000
        profile.current_apy = 100.0

        risk_score = profile.get_market_risk_score()
        self.assertGreater(risk_score, 0)


class TestVulnerabilityPredictor(unittest.TestCase):
    """Test vulnerability predictor."""

    def setUp(self):
        self.predictor = VulnerabilityPredictor()

        # Set up test protocol
        self.predictor.risk_calculator.create_profile("test-protocol", "Test Protocol")
        self.predictor.market.create_profile(
            "test-protocol",
            "Test Protocol",
            launch_date=datetime.now() - timedelta(days=15),
        )

    def test_analyze_protocol(self):
        """Test protocol analysis."""
        profile = self.predictor.analyze_protocol("test-protocol")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.protocol_id, "test-protocol")

    def test_basic_prediction(self):
        """Test basic prediction generation."""
        # Add risk factors
        self.predictor.risk_calculator.assess_launch_timing("test-protocol", 15)
        self.predictor.risk_calculator.assess_audit_status("test-protocol", False)
        self.predictor.risk_calculator.assess_code_patterns(
            "test-protocol",
            has_reentrancy_guards=False,
            external_call_count=10,
            admin_function_count=5,
            uses_oracles=True,
        )

        predictions = self.predictor.predict("test-protocol")
        self.assertGreater(len(predictions), 0)

    def test_prediction_confidence(self):
        """Test prediction confidence levels."""
        # Add multiple data sources for high confidence
        self.predictor.risk_calculator.assess_launch_timing("test-protocol", 10)
        self.predictor.risk_calculator.assess_audit_status("test-protocol", False)

        # Add evolution data
        for i in range(30):
            self.predictor.evolution.record_change(
                "test-protocol",
                author="alice",
                files_changed=3,
                lines_added=100,
                lines_removed=20,
            )
        self.predictor.evolution.analyze("test-protocol")

        # Add market data
        self.predictor.market.update_tvl("test-protocol", 50_000_000, 20_000_000, 10_000_000)

        predictions = self.predictor.predict("test-protocol")
        self.assertGreater(len(predictions), 0)

        # Should have reasonable confidence
        high_confidence = [
            p for p in predictions
            if p.confidence in [PredictionConfidence.HIGH, PredictionConfidence.VERY_HIGH]
        ]
        self.assertGreater(len(high_confidence), 0)

    def test_prediction_categories(self):
        """Test vulnerability category identification."""
        # Add specific risk factors
        self.predictor.risk_calculator.assess_code_patterns(
            "test-protocol",
            has_reentrancy_guards=False,
            external_call_count=15,
            admin_function_count=3,
            uses_oracles=True,
        )

        predictions = self.predictor.predict("test-protocol")

        categories = [p.vulnerability_category for p in predictions]
        # Should identify reentrancy risk
        self.assertIn(VulnerabilityCategory.REENTRANCY, categories)

    def test_prediction_recommendations(self):
        """Test recommendation generation."""
        self.predictor.risk_calculator.assess_audit_status("test-protocol", False)
        self.predictor.risk_calculator.assess_code_patterns(
            "test-protocol",
            has_reentrancy_guards=False,
            external_call_count=10,
            admin_function_count=5,
            uses_oracles=False,
        )

        predictions = self.predictor.predict("test-protocol")
        self.assertGreater(len(predictions), 0)

        for pred in predictions:
            self.assertGreater(len(pred.recommended_actions), 0)

    def test_risk_timeline(self):
        """Test risk timeline generation."""
        self.predictor.risk_calculator.assess_launch_timing("test-protocol", 10)

        self.predictor.predict("test-protocol", time_window_days=30)

        timeline = self.predictor.get_timeline("test-protocol")
        self.assertIsNotNone(timeline)
        self.assertGreater(len(timeline.predictions), 0)

    def test_timeline_peak_risk(self):
        """Test peak risk identification."""
        self.predictor.risk_calculator.assess_launch_timing("test-protocol", 5)
        self.predictor.predict("test-protocol", time_window_days=30)

        timeline = self.predictor.get_timeline("test-protocol")
        peak_time, peak_risk = timeline.get_peak_risk()

        self.assertIsNotNone(peak_time)
        self.assertGreater(peak_risk, 0)

    def test_high_risk_predictions(self):
        """Test getting high risk predictions."""
        # Create high-risk protocol
        self.predictor.risk_calculator.assess_launch_timing("test-protocol", 3)
        self.predictor.risk_calculator.assess_audit_status("test-protocol", False)
        self.predictor.risk_calculator.assess_competitor_exploit(
            "test-protocol",
            similar_protocol_exploited=True,
            days_since_exploit=2,
            exploit_type="reentrancy",
        )

        self.predictor.predict("test-protocol")

        high_risk = self.predictor.get_high_risk_predictions(min_probability=0.3)
        self.assertGreater(len(high_risk), 0)

    def test_prediction_validity(self):
        """Test prediction validity checking."""
        self.predictor.risk_calculator.assess_launch_timing("test-protocol", 10)
        predictions = self.predictor.predict("test-protocol", time_window_days=30)

        self.assertGreater(len(predictions), 0)
        for pred in predictions:
            self.assertTrue(pred.is_valid())

    def test_urgency_score(self):
        """Test urgency score calculation."""
        self.predictor.risk_calculator.assess_launch_timing("test-protocol", 3)
        predictions = self.predictor.predict("test-protocol", time_window_days=7)

        self.assertGreater(len(predictions), 0)
        for pred in predictions:
            urgency = pred.get_urgency_score()
            self.assertGreaterEqual(urgency, 0)

    def test_prediction_priority(self):
        """Test prediction priority assignment."""
        # High risk factors
        self.predictor.risk_calculator.assess_launch_timing("test-protocol", 3)
        self.predictor.risk_calculator.assess_audit_status("test-protocol", False)
        self.predictor.risk_calculator.assess_code_patterns(
            "test-protocol",
            has_reentrancy_guards=False,
            external_call_count=20,
            admin_function_count=10,
            uses_oracles=True,
        )

        predictions = self.predictor.predict("test-protocol")

        priorities = [p.priority for p in predictions]
        # Should have some high priority predictions
        self.assertTrue(any(p in ["critical", "high"] for p in priorities))


class TestIntegration(unittest.TestCase):
    """Integration tests for the full predictive pipeline."""

    def test_full_prediction_pipeline(self):
        """Test complete prediction workflow."""
        predictor = VulnerabilityPredictor()

        # Setup protocol
        protocol_id = "defi-protocol"

        # 1. Risk factor assessment
        predictor.risk_calculator.create_profile(protocol_id, "DeFi Protocol")
        predictor.risk_calculator.assess_launch_timing(protocol_id, 20)
        predictor.risk_calculator.assess_audit_status(
            protocol_id,
            has_audit=True,
            audit_age_days=100,
            changes_since_audit=40,
        )
        predictor.risk_calculator.assess_code_complexity(protocol_id, 12.0, 35, 4000)
        predictor.risk_calculator.assess_code_patterns(
            protocol_id,
            has_reentrancy_guards=True,
            external_call_count=8,
            admin_function_count=4,
            uses_oracles=True,
        )

        # 2. Code evolution analysis
        for i in range(20):
            predictor.evolution.record_change(
                protocol_id,
                author="alice" if i < 15 else "bob",
                files_changed=2,
                lines_added=50,
                lines_removed=15,
            )
        predictor.evolution.analyze(protocol_id)

        # 3. Market signal analysis
        predictor.market.create_profile(
            protocol_id,
            "DeFi Protocol",
            launch_date=datetime.now() - timedelta(days=20),
        )
        predictor.market.update_tvl(protocol_id, 80_000_000, 40_000_000, 20_000_000)
        predictor.market.update_yield(protocol_id, 25.0)

        # 4. Generate predictions
        predictions = predictor.predict(protocol_id, time_window_days=30)

        # Verify results
        self.assertGreater(len(predictions), 0)

        # Check prediction quality
        for pred in predictions:
            self.assertIsNotNone(pred.prediction_id)
            self.assertGreater(len(pred.contributing_factors), 0)
            self.assertGreater(len(pred.recommended_actions), 0)
            self.assertTrue(pred.is_valid())

        # Check timeline
        timeline = predictor.get_timeline(protocol_id)
        self.assertIsNotNone(timeline)

        # Check statistics
        stats = predictor.get_statistics()
        self.assertGreater(stats["total_predictions"], 0)

    def test_multi_protocol_comparison(self):
        """Test comparing predictions across protocols."""
        predictor = VulnerabilityPredictor()

        # High risk protocol
        predictor.risk_calculator.create_profile("high-risk", "High Risk")
        predictor.risk_calculator.assess_launch_timing("high-risk", 5)
        predictor.risk_calculator.assess_audit_status("high-risk", False)
        predictor.market.create_profile("high-risk", launch_date=datetime.now() - timedelta(days=5))

        # Low risk protocol
        predictor.risk_calculator.create_profile("low-risk", "Low Risk")
        predictor.risk_calculator.assess_audit_status("low-risk", True, audit_age_days=30)
        predictor.market.create_profile("low-risk", launch_date=datetime.now() - timedelta(days=400))

        # Generate predictions
        high_preds = predictor.predict("high-risk")
        low_preds = predictor.predict("low-risk")

        # High risk should have higher probability predictions
        high_max_prob = max(p.probability for p in high_preds) if high_preds else 0
        low_max_prob = max(p.probability for p in low_preds) if low_preds else 0

        self.assertGreater(high_max_prob, low_max_prob)


if __name__ == "__main__":
    unittest.main()
