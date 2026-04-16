"""Tests for taint availability and unknown semantics.

This module tests the expanded taint analysis system from Phase 5.9-06,
verifying that:
- Missing taint data yields unknown, not safe
- Aliasing strategy (direct vs aliased) works correctly
- Sanitizers are properly tracked
- Availability calibration matches TAINT_RULES.md criteria
- Source types are correctly classified

Reference: docs/reference/TAINT_RULES.md
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from alphaswarm_sol.kg.taint import (
    TaintAnalyzer,
    TaintAvailability,
    TaintResult,
    TaintSanitizer,
    TaintSink,
    TaintSource,
    InputSource,
    SANITIZER_AFFECTS,
    TAINT_SINK_SEVERITY,
    TAINT_SOURCE_RISK,
    extract_inputs,
    extract_external_return_sources,
    extract_oracle_sources,
    extract_special_sources,
)


class TestUnknownSemantics(unittest.TestCase):
    """Tests for unknown semantics - missing yields unknown, not safe."""

    def test_missing_taint_yields_unknown_not_safe(self):
        """Missing taint data must yield unknown, not safe.

        TAINT_RULES.md: 'When availability.available = false, the taint
        result is UNKNOWN, not safe.'
        """
        # Create unknown result
        result = TaintResult.unknown("delegatecall present")

        # is_tainted is False but this is NOT safe
        self.assertFalse(result.is_tainted)

        # is_unknown should be True
        self.assertTrue(result.is_unknown)

        # is_safe should be False (unknown != safe)
        self.assertFalse(result.is_safe)

    def test_unknown_result_has_unavailable_availability(self):
        """Unknown results have availability.available = False."""
        result = TaintResult.unknown("test reason")

        self.assertFalse(result.availability.available)
        self.assertEqual(result.availability.confidence, 0.0)
        self.assertEqual(result.availability.reason, "test reason")

    def test_safe_result_requires_availability(self):
        """Safe result must have availability.available = True."""
        # Create truly safe result
        safe_result = TaintResult.safe()

        self.assertFalse(safe_result.is_tainted)
        self.assertTrue(safe_result.availability.available)
        self.assertTrue(safe_result.is_safe)

        # Unknown result should not be considered safe
        unknown_result = TaintResult.unknown("test")
        self.assertFalse(unknown_result.is_safe)

    def test_delegatecall_forces_unavailable(self):
        """Delegatecall to external contract makes taint unavailable.

        TAINT_RULES.md: 'Delegatecall to external contracts creates
        unavailable taint analysis.'
        """
        avail = TaintAvailability.delegatecall()

        self.assertFalse(avail.available)
        self.assertEqual(avail.confidence, 0.0)
        self.assertIn("delegatecall", avail.reason.lower())

    def test_inline_assembly_forces_unavailable(self):
        """Inline assembly makes taint unavailable.

        TAINT_RULES.md: 'Inline assembly: availability = false,
        confidence = 0.0'
        """
        avail = TaintAvailability.inline_assembly()

        self.assertFalse(avail.available)
        self.assertEqual(avail.confidence, 0.0)
        self.assertIn("assembly", avail.reason.lower())


class TestAliasingStrategy(unittest.TestCase):
    """Tests for aliasing strategy (Direct-then-Aliased).

    TAINT_RULES.md: 'This implementation uses Direct-then-Aliased
    taint propagation.'
    """

    def test_direct_taint_full_confidence(self):
        """Direct taint has confidence = 1.0.

        TAINT_RULES.md: 'Direct taint properties: Confidence: 1.0'
        """
        avail = TaintAvailability.full()

        self.assertTrue(avail.available)
        self.assertEqual(avail.confidence, 1.0)

    def test_aliased_taint_lower_confidence(self):
        """Aliased taint has lower confidence than direct.

        TAINT_RULES.md: 'Aliased taint: Confidence: 0.7 (reduced due
        to storage indirection)'
        """
        direct = TaintAvailability.full()
        aliased = TaintAvailability.aliased()

        self.assertGreater(direct.confidence, aliased.confidence)
        self.assertEqual(aliased.confidence, 0.7)

    def test_aliased_taint_storage_propagation(self):
        """Aliased taint propagates through storage with lower confidence."""
        # Create tainted result via storage
        result = TaintResult.tainted(
            sources=[TaintSource.STORAGE_ALIASED],
            path=["oracle.getPrice() -> cachedPrice", "cachedPrice -> localVar"],
            availability=TaintAvailability.aliased(),
        )

        self.assertTrue(result.is_tainted)
        self.assertIn(TaintSource.STORAGE_ALIASED, result.sources)
        self.assertEqual(result.availability.confidence, 0.7)

    def test_storage_taint_tracking(self):
        """TaintAnalyzer tracks storage taint."""
        mock_contract = MagicMock()
        analyzer = TaintAnalyzer(mock_contract)

        # Mark storage as tainted
        analyzer.mark_storage_tainted(
            "cachedPrice",
            [TaintSource.ORACLE],
            ["oracle.getPrice() -> cachedPrice"],
        )

        # Check storage taint
        storage_taint = analyzer.get_storage_taint()
        self.assertIn("cachedPrice", storage_taint)
        self.assertTrue(storage_taint["cachedPrice"].is_tainted)
        self.assertEqual(storage_taint["cachedPrice"].availability.confidence, 0.7)

    def test_clear_storage_taint(self):
        """TaintAnalyzer can clear storage taint."""
        mock_contract = MagicMock()
        analyzer = TaintAnalyzer(mock_contract)

        analyzer.mark_storage_tainted("slot", [TaintSource.USER_INPUT])
        self.assertIn("slot", analyzer.get_storage_taint())

        analyzer.clear_storage_taint("slot")
        self.assertNotIn("slot", analyzer.get_storage_taint())


class TestSanitizers(unittest.TestCase):
    """Tests for sanitizer tracking and effects."""

    def test_bounds_check_sanitizes_arithmetic(self):
        """require(x < MAX) sanitizes ARITHMETIC sink risk.

        TAINT_RULES.md: 'Bounds check before arithmetic: Removes
        ARITHMETIC sink risk'
        """
        affected = SANITIZER_AFFECTS[TaintSanitizer.BOUNDS_CHECK]
        self.assertIn(TaintSink.ARITHMETIC, affected)

    def test_whitelist_sanitizes_call_target(self):
        """Whitelist check sanitizes CALL_TARGET sink risk.

        TAINT_RULES.md: 'Whitelist before call: Removes CALL_TARGET
        sink risk'
        """
        affected = SANITIZER_AFFECTS[TaintSanitizer.WHITELIST_CHECK]
        self.assertIn(TaintSink.CALL_TARGET, affected)

    def test_ownership_check_does_not_remove_taint(self):
        """Ownership check validates context, doesn't remove taint.

        TAINT_RULES.md: 'Ownership check: Does NOT remove taint,
        validates context only'
        """
        affected = SANITIZER_AFFECTS[TaintSanitizer.OWNERSHIP_CHECK]
        self.assertEqual(len(affected), 0)

    def test_zero_check_is_weak_sanitizer(self):
        """Zero check is weak, doesn't remove significant taint.

        TAINT_RULES.md: 'Zero check: Weak sanitizer, does NOT remove
        significant taint'
        """
        affected = SANITIZER_AFFECTS[TaintSanitizer.ZERO_CHECK]
        self.assertEqual(len(affected), 0)

    def test_sanitizer_recorded_in_result(self):
        """Applied sanitizers appear in result.sanitizers_applied."""
        result = TaintResult.tainted(
            sources=[TaintSource.USER_INPUT],
            sanitizers=[TaintSanitizer.BOUNDS_CHECK],
        )

        self.assertIn(TaintSanitizer.BOUNDS_CHECK, result.sanitizers_applied)

    def test_safe_math_sanitizes_arithmetic(self):
        """SafeMath operations sanitize ARITHMETIC sink."""
        affected = SANITIZER_AFFECTS[TaintSanitizer.SAFE_MATH]
        self.assertIn(TaintSink.ARITHMETIC, affected)


class TestAvailabilityCalibration(unittest.TestCase):
    """Tests for availability flag calibration criteria.

    TAINT_RULES.md defines specific confidence values for different
    conditions. These tests verify the calibration is correct.
    """

    def test_full_cfg_direct_taint(self):
        """Full CFG, direct taint: (True, 1.0)."""
        avail = TaintAvailability.full()

        self.assertTrue(avail.available)
        self.assertEqual(avail.confidence, 1.0)

    def test_storage_aliased(self):
        """Storage aliased: (True, 0.7)."""
        avail = TaintAvailability.aliased()

        self.assertTrue(avail.available)
        self.assertEqual(avail.confidence, 0.7)

    def test_external_call_in_path(self):
        """External call in path: (True, 0.5)."""
        avail = TaintAvailability.external_call()

        self.assertTrue(avail.available)
        self.assertEqual(avail.confidence, 0.5)

    def test_delegatecall_present(self):
        """Delegatecall: (False, 0.0)."""
        avail = TaintAvailability.delegatecall()

        self.assertFalse(avail.available)
        self.assertEqual(avail.confidence, 0.0)

    def test_inline_assembly_present(self):
        """Inline assembly: (False, 0.0)."""
        avail = TaintAvailability.inline_assembly()

        self.assertFalse(avail.available)
        self.assertEqual(avail.confidence, 0.0)

    def test_dynamic_loop_bound(self):
        """Loop with dynamic bound: (True, 0.6)."""
        avail = TaintAvailability.dynamic_loop()

        self.assertTrue(avail.available)
        self.assertEqual(avail.confidence, 0.6)

    def test_recursive_call(self):
        """Recursive call: (True, 0.5)."""
        avail = TaintAvailability.recursive()

        self.assertTrue(avail.available)
        self.assertEqual(avail.confidence, 0.5)

    def test_try_catch_external(self):
        """Try/catch with external: (True, 0.4)."""
        avail = TaintAvailability.try_catch()

        self.assertTrue(avail.available)
        self.assertEqual(avail.confidence, 0.4)

    def test_confidence_thresholds_high(self):
        """Confidence >= 0.9 is high confidence."""
        avail = TaintAvailability(available=True, confidence=0.95)
        self.assertTrue(avail.is_high_confidence())
        self.assertFalse(avail.is_insufficient())

    def test_confidence_thresholds_medium(self):
        """Confidence 0.7-0.89 is medium confidence."""
        avail = TaintAvailability(available=True, confidence=0.75)
        self.assertTrue(avail.is_medium_confidence())
        self.assertFalse(avail.is_high_confidence())
        self.assertFalse(avail.is_insufficient())

    def test_confidence_thresholds_low(self):
        """Confidence 0.5-0.69 is low confidence."""
        avail = TaintAvailability(available=True, confidence=0.55)
        self.assertTrue(avail.is_low_confidence())
        self.assertFalse(avail.is_medium_confidence())
        self.assertFalse(avail.is_insufficient())

    def test_confidence_thresholds_insufficient(self):
        """Confidence < 0.5 is insufficient."""
        avail = TaintAvailability(available=True, confidence=0.45)
        self.assertTrue(avail.is_insufficient())

    def test_unavailable_is_insufficient(self):
        """Unavailable is always insufficient regardless of confidence."""
        avail = TaintAvailability(available=False, confidence=0.0)
        self.assertTrue(avail.is_insufficient())


class TestSourceTypes(unittest.TestCase):
    """Tests for taint source type classification."""

    def test_external_return_taint_source(self):
        """External call return values are EXTERNAL_RETURN source."""
        self.assertEqual(TaintSource.EXTERNAL_RETURN.value, "external_return")
        self.assertEqual(TAINT_SOURCE_RISK[TaintSource.EXTERNAL_RETURN], "HIGH")

    def test_call_target_control_is_critical(self):
        """User-controlled call targets are CRITICAL risk.

        TAINT_RULES.md: 'Call-target control | CRITICAL'
        """
        self.assertEqual(
            TaintSource.CALL_TARGET_CONTROL.value, "call_target_control"
        )
        self.assertEqual(
            TAINT_SOURCE_RISK[TaintSource.CALL_TARGET_CONTROL], "CRITICAL"
        )

    def test_oracle_taint_source(self):
        """Oracle values (Chainlink, etc.) are ORACLE source."""
        self.assertEqual(TaintSource.ORACLE.value, "oracle")
        self.assertEqual(TAINT_SOURCE_RISK[TaintSource.ORACLE], "HIGH")

    def test_user_input_is_high_risk(self):
        """User input parameters are HIGH risk."""
        self.assertEqual(TAINT_SOURCE_RISK[TaintSource.USER_INPUT], "HIGH")

    def test_environment_is_medium_risk(self):
        """Environment variables are MEDIUM risk."""
        self.assertEqual(TAINT_SOURCE_RISK[TaintSource.ENVIRONMENT], "MEDIUM")

    def test_storage_aliased_is_low_risk(self):
        """Storage aliased is LOW risk (indirect)."""
        self.assertEqual(TAINT_SOURCE_RISK[TaintSource.STORAGE_ALIASED], "LOW")

    def test_risk_level_property(self):
        """TaintResult.risk_level returns highest source risk."""
        # Single high-risk source
        result1 = TaintResult.tainted([TaintSource.USER_INPUT])
        self.assertEqual(result1.risk_level, "HIGH")

        # Critical source
        result2 = TaintResult.tainted([TaintSource.CALL_TARGET_CONTROL])
        self.assertEqual(result2.risk_level, "CRITICAL")

        # Mixed sources - returns highest
        result3 = TaintResult.tainted([
            TaintSource.STORAGE_ALIASED,  # LOW
            TaintSource.ORACLE,  # HIGH
        ])
        self.assertEqual(result3.risk_level, "HIGH")

        # No sources
        result4 = TaintResult.safe()
        self.assertEqual(result4.risk_level, "NONE")


class TestSinkTypes(unittest.TestCase):
    """Tests for sink type classification."""

    def test_call_target_is_critical(self):
        """CALL_TARGET sink is CRITICAL severity."""
        self.assertEqual(TAINT_SINK_SEVERITY[TaintSink.CALL_TARGET], "CRITICAL")

    def test_external_call_value_is_critical(self):
        """EXTERNAL_CALL_VALUE sink is CRITICAL severity."""
        self.assertEqual(
            TAINT_SINK_SEVERITY[TaintSink.EXTERNAL_CALL_VALUE], "CRITICAL"
        )

    def test_storage_write_is_high(self):
        """STORAGE_WRITE sink is HIGH severity."""
        self.assertEqual(TAINT_SINK_SEVERITY[TaintSink.STORAGE_WRITE], "HIGH")

    def test_arithmetic_is_medium(self):
        """ARITHMETIC sink is MEDIUM severity."""
        self.assertEqual(TAINT_SINK_SEVERITY[TaintSink.ARITHMETIC], "MEDIUM")

    def test_comparison_is_low(self):
        """COMPARISON sink is LOW severity."""
        self.assertEqual(TAINT_SINK_SEVERITY[TaintSink.COMPARISON], "LOW")

    def test_result_with_sink(self):
        """TaintResult can track target sink."""
        result = TaintResult.tainted(
            sources=[TaintSource.USER_INPUT],
            sink=TaintSink.STORAGE_WRITE,
        )
        self.assertEqual(result.sink, TaintSink.STORAGE_WRITE)


class TestInputSourceExtraction(unittest.TestCase):
    """Tests for input source extraction functions."""

    def test_extract_inputs_from_function(self):
        """extract_inputs extracts function parameters."""
        mock_fn = MagicMock()
        mock_param1 = MagicMock()
        mock_param1.name = "amount"
        mock_param2 = MagicMock()
        mock_param2.name = "recipient"
        mock_fn.parameters = [mock_param1, mock_param2]

        sources = extract_inputs(mock_fn)

        self.assertEqual(len(sources), 2)
        self.assertEqual(sources[0].name, "amount")
        self.assertEqual(sources[0].kind, "parameter")
        self.assertEqual(sources[1].name, "recipient")

    def test_extract_special_sources(self):
        """extract_special_sources extracts msg.sender, msg.value."""
        mock_fn = MagicMock()
        mock_var1 = MagicMock()
        mock_var1.name = "msg.sender"
        mock_var2 = MagicMock()
        mock_var2.name = "msg.value"
        mock_var3 = MagicMock()
        mock_var3.name = "localVar"  # Should be ignored
        mock_fn.variables_read = [mock_var1, mock_var2, mock_var3]

        sources = extract_special_sources(mock_fn)

        self.assertEqual(len(sources), 2)
        names = {s.name for s in sources}
        self.assertIn("msg.sender", names)
        self.assertIn("msg.value", names)
        self.assertNotIn("localVar", names)

    def test_extract_external_return_sources(self):
        """extract_external_return_sources extracts external call returns."""
        mock_fn = MagicMock()
        mock_fn.external_calls_as_expressions = [
            MagicMock(),  # Some external call
            MagicMock(),
        ]

        sources = extract_external_return_sources(mock_fn)

        self.assertEqual(len(sources), 2)
        self.assertEqual(sources[0].kind, "external_return")
        self.assertEqual(sources[1].kind, "external_return")

    def test_extract_oracle_sources(self):
        """extract_oracle_sources detects oracle patterns."""
        mock_fn = MagicMock()
        mock_call1 = MagicMock()
        mock_call1.__str__ = lambda self: "chainlink.latestAnswer()"
        mock_call2 = MagicMock()
        mock_call2.__str__ = lambda self: "token.transfer()"  # Not oracle
        mock_call3 = MagicMock()
        mock_call3.__str__ = lambda self: "oracle.getPrice()"
        mock_fn.external_calls_as_expressions = [
            mock_call1,
            mock_call2,
            mock_call3,
        ]

        sources = extract_oracle_sources(mock_fn)

        # Should detect latestAnswer and getPrice, not transfer
        self.assertEqual(len(sources), 2)
        self.assertTrue(all(s.kind == "oracle" for s in sources))


class TestTaintAvailabilityValidation(unittest.TestCase):
    """Tests for TaintAvailability validation."""

    def test_confidence_must_be_in_range(self):
        """Confidence must be between 0.0 and 1.0."""
        # Valid values
        TaintAvailability(available=True, confidence=0.0)
        TaintAvailability(available=True, confidence=0.5)
        TaintAvailability(available=True, confidence=1.0)

        # Invalid values
        with self.assertRaises(ValueError):
            TaintAvailability(available=True, confidence=-0.1)
        with self.assertRaises(ValueError):
            TaintAvailability(available=True, confidence=1.1)

    def test_unavailable_factory(self):
        """TaintAvailability.unavailable creates proper result."""
        avail = TaintAvailability.unavailable("custom reason")

        self.assertFalse(avail.available)
        self.assertEqual(avail.confidence, 0.0)
        self.assertEqual(avail.reason, "custom reason")


class TestTaintAnalyzerDelegatecallDetection(unittest.TestCase):
    """Tests for TaintAnalyzer delegatecall/assembly detection."""

    def test_analyzer_detects_delegatecall(self):
        """Analyzer detects delegatecall in function."""
        mock_contract = MagicMock()
        mock_fn = MagicMock()
        mock_fn.high_level_calls = []
        mock_fn.low_level_calls = [
            (MagicMock(), "delegatecall"),  # (target, call_type)
        ]
        mock_fn.contains_assembly = False
        mock_fn.variables = []

        analyzer = TaintAnalyzer(mock_contract)
        results = analyzer.analyze_function(mock_fn)

        # After analyzing function with delegatecall, analyzer should have flag set
        self.assertTrue(analyzer._has_delegatecall)

    def test_analyzer_detects_inline_assembly(self):
        """Analyzer detects inline assembly in function."""
        mock_contract = MagicMock()
        mock_fn = MagicMock()
        mock_fn.high_level_calls = []
        mock_fn.low_level_calls = []
        mock_fn.contains_assembly = True
        mock_fn.variables = []
        mock_fn.parameters = []
        mock_fn.variables_read = []

        analyzer = TaintAnalyzer(mock_contract)

        # Analyze a variable with assembly present
        mock_var = MagicMock()
        mock_var.name = "x"
        result = analyzer.analyze_variable(mock_fn, mock_var)

        # Should return unknown due to assembly
        self.assertTrue(result.is_unknown)
        self.assertIn("assembly", result.availability.reason.lower())


class TestTaintResultFactoryMethods(unittest.TestCase):
    """Tests for TaintResult factory methods."""

    def test_safe_factory(self):
        """TaintResult.safe() creates proper safe result."""
        result = TaintResult.safe()

        self.assertFalse(result.is_tainted)
        self.assertTrue(result.is_safe)
        self.assertFalse(result.is_unknown)
        self.assertEqual(len(result.sources), 0)
        self.assertEqual(len(result.path), 0)

    def test_unknown_factory(self):
        """TaintResult.unknown() creates proper unknown result."""
        result = TaintResult.unknown("test reason")

        self.assertFalse(result.is_tainted)
        self.assertFalse(result.is_safe)
        self.assertTrue(result.is_unknown)
        self.assertEqual(result.availability.reason, "test reason")

    def test_tainted_factory(self):
        """TaintResult.tainted() creates proper tainted result."""
        result = TaintResult.tainted(
            sources=[TaintSource.USER_INPUT, TaintSource.ORACLE],
            path=["x -> y", "y -> z"],
            availability=TaintAvailability.full(),
            sanitizers=[TaintSanitizer.BOUNDS_CHECK],
            sink=TaintSink.ARITHMETIC,
        )

        self.assertTrue(result.is_tainted)
        self.assertFalse(result.is_safe)
        self.assertFalse(result.is_unknown)
        self.assertEqual(len(result.sources), 2)
        self.assertEqual(len(result.path), 2)
        self.assertIn(TaintSanitizer.BOUNDS_CHECK, result.sanitizers_applied)
        self.assertEqual(result.sink, TaintSink.ARITHMETIC)


if __name__ == "__main__":
    unittest.main()
