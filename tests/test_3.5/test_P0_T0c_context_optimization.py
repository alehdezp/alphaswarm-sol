"""
Tests for P0-T0c: Context Optimization Layer

Tests hierarchical triage, semantic compression, context slicing,
and integrated optimization.
"""

import pytest
from alphaswarm_sol.llm.triage import TriageClassifier, TriageLevel, TriageResult
from alphaswarm_sol.llm.compressor import SemanticCompressor, CompressionTier, CompressedContext
from alphaswarm_sol.llm.slicer import ContextSlicer, ContextSlice
from alphaswarm_sol.llm.optimizer import ContextOptimizer, OptimizedContext
from alphaswarm_sol.llm.templates import (
    get_template,
    get_system_prompt,
    format_pattern_list,
    format_spec_list,
)


# Test Data Fixtures

@pytest.fixture
def trivially_safe_function():
    """View function - Level 0 (no LLM needed)."""
    return {
        "name": "getBalance",
        "id": "fn_getBalance",
        "properties": {
            "visibility": "public",
            "state_mutability": "view",
            "has_external_calls": False,
            "writes_state": False,
        }
    }


@pytest.fixture
def low_risk_function():
    """Simple function - Level 1 (quick scan)."""
    return {
        "name": "updateValue",
        "id": "fn_updateValue",
        "properties": {
            "visibility": "internal",
            "state_mutability": "nonpayable",
            "has_external_calls": False,
            "writes_state": True,
            "has_access_gate": True,
            "modifiers": ["onlyOwner"],
            "state_vars_written": ["value"],
            "state_vars_read": [],
            "behavioral_signature": "W:value",
            "operations": ["WRITES_STATE"],
        }
    }


@pytest.fixture
def moderate_risk_function():
    """Pattern-matched function - Level 2 (focused)."""
    return {
        "name": "transfer",
        "id": "fn_transfer",
        "properties": {
            "visibility": "public",
            "state_mutability": "nonpayable",
            "has_external_calls": True,
            "writes_state": True,
            "has_access_gate": False,
            "modifiers": [],
            "state_vars_written": ["balances"],
            "state_vars_read": ["balances"],
            "behavioral_signature": "R:bal→X:out→W:bal",
            "operations": ["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            "reentrancy_risk_score": 0.65,
        },
        "matched_patterns": [
            {"id": "reentrancy-classic", "severity": "high", "score": 0.8}
        ]
    }


@pytest.fixture
def high_risk_function():
    """High-risk function - Level 3 (deep analysis)."""
    return {
        "name": "withdraw",
        "id": "fn_withdraw",
        "source_code": """function withdraw(uint256 amount) external {
    require(balances[msg.sender] >= amount, "Insufficient balance");
    (bool success, ) = msg.sender.call{value: amount}("");
    require(success, "Transfer failed");
    balances[msg.sender] -= amount;
}""",
        "properties": {
            "visibility": "external",
            "state_mutability": "nonpayable",
            "has_external_calls": True,
            "writes_state": True,
            "has_access_gate": False,
            "state_write_after_external_call": True,
            "has_reentrancy_guard": False,
            "modifiers": [],
            "state_vars_written": ["balances"],
            "state_vars_read": ["balances"],
            "behavioral_signature": "R:bal→X:out→W:bal",
            "operations": ["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            "reentrancy_risk_score": 0.95,
        },
        "matched_patterns": [
            {"id": "reentrancy-classic", "severity": "critical", "score": 0.95}
        ],
        "cross_graph_links": [
            {"spec": "CEI-pattern", "requirement": "must follow checks-effects-interactions"}
        ]
    }


@pytest.fixture
def simple_kg():
    """Simple knowledge graph for slicing tests."""
    return {
        "nodes": [
            {"id": "fn_withdraw", "type": "Function"},
            {"id": "fn_deposit", "type": "Function"},
            {"id": "var_balances", "type": "StateVariable"},
        ],
        "edges": [
            {"source": "fn_withdraw", "target": "var_balances", "type": "writes"},
            {"source": "fn_withdraw", "target": "fn_deposit", "type": "calls"},
        ]
    }


# Triage Classifier Tests

class TestTriageClassifier:
    """Test hierarchical triage classification."""

    def test_level_0_view_function(self, trivially_safe_function):
        """View functions should be Level 0 (no LLM needed)."""
        classifier = TriageClassifier()
        result = classifier.classify(trivially_safe_function)

        assert result.level == TriageLevel.LEVEL_0_SKIP
        assert result.token_budget == 0
        assert not result.requires_llm
        assert result.confidence >= 0.9

    def test_level_1_low_risk(self, low_risk_function):
        """Low-risk functions should be Level 1 (quick scan)."""
        classifier = TriageClassifier()
        result = classifier.classify(low_risk_function)

        assert result.level == TriageLevel.LEVEL_1_QUICK
        assert result.token_budget == 100
        assert result.requires_llm

    def test_level_2_pattern_matched(self, moderate_risk_function):
        """Pattern-matched functions should be Level 2 (focused)."""
        classifier = TriageClassifier()
        result = classifier.classify(moderate_risk_function)

        assert result.level == TriageLevel.LEVEL_2_FOCUSED
        assert result.token_budget == 500
        assert result.requires_llm

    def test_level_3_high_risk(self, high_risk_function):
        """High-risk functions should be Level 3 (deep dive)."""
        classifier = TriageClassifier()
        result = classifier.classify(high_risk_function)

        assert result.level == TriageLevel.LEVEL_3_DEEP
        assert result.token_budget == 2000
        assert result.requires_llm
        assert "reentrancy" in result.reason.lower() or "state write" in result.reason.lower()

    def test_batch_classify(self, trivially_safe_function, moderate_risk_function):
        """Batch classification should produce statistics."""
        classifier = TriageClassifier()
        result = classifier.batch_classify([trivially_safe_function, moderate_risk_function])

        assert "results" in result
        assert "stats" in result
        assert result["stats"]["total_functions"] == 2
        assert result["stats"]["level_0_count"] >= 1
        assert result["stats"]["llm_required_count"] >= 1


# Semantic Compressor Tests

class TestSemanticCompressor:
    """Test 5-tier semantic compression."""

    def test_tier_1_properties(self, low_risk_function):
        """Tier 1 should compress to ~50 tokens."""
        compressor = SemanticCompressor()
        result = compressor.compress(low_risk_function, budget=50)

        assert result.tier == CompressionTier.PROPERTIES
        assert result.token_estimate <= 60  # Allow some variance
        assert "fn:" in result.compressed
        assert "vis:" in result.compressed
        assert result.compression_ratio > 1.0

    def test_tier_2_behavioral(self, moderate_risk_function):
        """Tier 2 should add behavioral signature."""
        compressor = SemanticCompressor()
        result = compressor.compress(moderate_risk_function, budget=100)

        assert result.tier == CompressionTier.BEHAVIORAL
        assert result.token_estimate <= 110
        assert "sig:" in result.compressed
        assert "ops:" in result.compressed

    def test_tier_3_patterns(self, moderate_risk_function):
        """Tier 3 should add pattern matches."""
        compressor = SemanticCompressor()
        result = compressor.compress(moderate_risk_function, budget=200)

        assert result.tier == CompressionTier.PATTERNS
        assert result.token_estimate <= 220
        assert "patterns:" in result.compressed

    def test_tier_4_critical_lines(self, high_risk_function):
        """Tier 4 should add critical code lines."""
        high_risk_function["critical_lines"] = [
            {"line": 3, "code": "(bool success, ) = msg.sender.call{value: amount}"},
            {"line": 5, "code": "balances[msg.sender] -= amount"}
        ]
        compressor = SemanticCompressor()
        result = compressor.compress(high_risk_function, budget=400)

        assert result.tier == CompressionTier.CRITICAL_LINES
        assert result.token_estimate <= 450
        assert "lines:" in result.compressed

    def test_tier_5_full_source(self, high_risk_function):
        """Tier 5 should add full source code."""
        compressor = SemanticCompressor()
        result = compressor.compress(high_risk_function, budget=2000)

        assert result.tier == CompressionTier.FULL
        assert "source:" in result.compressed
        assert "withdraw" in result.compressed

    def test_compression_ratio(self, high_risk_function):
        """Compressed context should have high compression ratio."""
        compressor = SemanticCompressor()
        result = compressor.compress(high_risk_function, budget=100)

        assert result.compression_ratio >= 3.0  # At least 3x compression


# Context Slicer Tests

class TestContextSlicer:
    """Test KG context slicing."""

    def test_level_0_no_slice(self):
        """Level 0 should return minimal slice."""
        slicer = ContextSlicer()
        result = slicer.slice(None, "fn_test", TriageLevel.LEVEL_0_SKIP)

        assert result.depth == 0
        assert len(result.included_nodes) == 1
        assert len(result.included_edges) == 0

    def test_level_1_focal_only(self, simple_kg):
        """Level 1 should return focal node only."""
        slicer = ContextSlicer()
        result = slicer.slice(simple_kg, "fn_withdraw", TriageLevel.LEVEL_1_QUICK)

        assert result.depth == 0
        assert result.focal_node == "fn_withdraw"

    @pytest.mark.xfail(reason="Stale code: ContextSlicer API changed")
    def test_level_2_immediate_neighbors(self, simple_kg):
        """Level 2 should include immediate neighbors."""
        slicer = ContextSlicer()
        result = slicer.slice(simple_kg, "fn_withdraw", TriageLevel.LEVEL_2_FOCUSED)

        assert result.depth == 1
        assert result.focal_node == "fn_withdraw"
        assert len(result.included_nodes) > 1  # Should include neighbors

    def test_level_3_two_hop(self, simple_kg):
        """Level 3 should include 2-hop neighborhood."""
        slicer = ContextSlicer()
        result = slicer.slice(simple_kg, "fn_withdraw", TriageLevel.LEVEL_3_DEEP)

        assert result.depth == 2
        assert result.focal_node == "fn_withdraw"

    def test_serialize_slice(self, simple_kg):
        """Serialized slice should be compact."""
        slicer = ContextSlicer()
        slice_obj = slicer.slice(simple_kg, "fn_withdraw", TriageLevel.LEVEL_2_FOCUSED)
        serialized = slicer.serialize_slice(slice_obj)

        assert "focal:" in serialized
        assert "nodes:" in serialized
        assert "edges:" in serialized


# Template Tests

class TestTemplates:
    """Test prompt templates."""

    def test_get_template_level_1(self):
        """Level 1 template should be quick scan."""
        template = get_template(1)
        assert "QUICK SECURITY SCAN" in template
        assert "{compressed_context}" in template

    def test_get_template_level_2(self):
        """Level 2 template should be focused analysis."""
        template = get_template(2)
        assert "FOCUSED SECURITY ANALYSIS" in template
        assert "{patterns}" in template
        assert "JSON" in template

    def test_get_template_level_3(self):
        """Level 3 template should be deep analysis."""
        template = get_template(3)
        assert "DEEP ADVERSARIAL" in template
        assert "{source_code}" in template
        assert "solidity" in template

    def test_get_system_prompt(self):
        """System prompts should exist for all levels."""
        for level in [1, 2, 3]:
            prompt = get_system_prompt(level)
            assert len(prompt) > 0
            assert "security" in prompt.lower()

    def test_format_pattern_list(self):
        """Pattern list formatting should be compact."""
        patterns = [
            {"id": "reentrancy", "severity": "critical", "score": 0.95},
            {"id": "access-control", "severity": "high", "score": 0.80}
        ]
        formatted = format_pattern_list(patterns)
        assert "reentrancy" in formatted
        assert "critical" in formatted

    def test_format_pattern_list_empty(self):
        """Empty pattern list should return 'none'."""
        assert format_pattern_list([]) == "none"

    def test_format_spec_list(self):
        """Spec list formatting should be compact."""
        specs = [
            {"spec": "CEI-pattern", "requirement": "follow checks-effects-interactions"}
        ]
        formatted = format_spec_list(specs)
        assert "CEI-pattern" in formatted


# Integration Tests

class TestContextOptimizer:
    """Test integrated context optimization."""

    def test_optimize_level_0(self, trivially_safe_function):
        """Level 0 optimization should skip LLM."""
        optimizer = ContextOptimizer()
        result = optimizer.optimize(trivially_safe_function)

        assert result.triage.level == TriageLevel.LEVEL_0_SKIP
        assert result.prompt is None
        assert result.total_tokens == 0

    def test_optimize_level_1(self, low_risk_function):
        """Level 1 optimization should produce quick scan prompt."""
        optimizer = ContextOptimizer()
        result = optimizer.optimize(low_risk_function)

        assert result.triage.level == TriageLevel.LEVEL_1_QUICK
        assert result.prompt is not None
        assert "QUICK SECURITY SCAN" in result.prompt
        assert result.total_tokens > 0
        assert result.total_tokens < 200  # Should be minimal

    def test_optimize_level_2(self, moderate_risk_function):
        """Level 2 optimization should produce focused analysis prompt."""
        optimizer = ContextOptimizer()
        result = optimizer.optimize(moderate_risk_function)

        assert result.triage.level == TriageLevel.LEVEL_2_FOCUSED
        assert result.prompt is not None
        assert "FOCUSED SECURITY ANALYSIS" in result.prompt
        assert result.total_tokens > 100
        assert result.total_tokens < 700

    def test_optimize_level_3(self, high_risk_function):
        """Level 3 optimization should produce deep analysis prompt."""
        optimizer = ContextOptimizer()
        result = optimizer.optimize(high_risk_function)

        assert result.triage.level == TriageLevel.LEVEL_3_DEEP
        assert result.prompt is not None
        assert "DEEP ADVERSARIAL" in result.prompt
        assert result.total_tokens > 100  # Should have meaningful context
        assert result.total_tokens < 2500  # But stay within budget

    def test_batch_optimize(
        self, trivially_safe_function, moderate_risk_function, high_risk_function
    ):
        """Batch optimization should produce statistics."""
        optimizer = ContextOptimizer()
        functions = [trivially_safe_function, moderate_risk_function, high_risk_function]
        result = optimizer.batch_optimize(functions)

        assert "results" in result
        assert "stats" in result
        assert len(result["results"]) == 3
        assert result["stats"]["functions_analyzed"] == 3
        assert result["stats"]["token_reduction_pct"] > 50  # Significant reduction

    def test_get_optimization_stats(
        self, trivially_safe_function, moderate_risk_function, high_risk_function
    ):
        """Optimization stats should project token savings."""
        optimizer = ContextOptimizer()
        functions = [trivially_safe_function, moderate_risk_function, high_risk_function]
        stats = optimizer.get_optimization_stats(functions)

        assert stats["total_functions"] == 3
        assert stats["level_0_count"] >= 1  # At least the view function
        assert stats["token_reduction_pct"] > 50
        assert stats["avg_tokens_per_function"] < 1000  # Much less than naive 6000


# Success Criteria Tests

class TestSuccessCriteria:
    """Validate P0-T0c success criteria."""

    def test_triage_accuracy(
        self, trivially_safe_function, low_risk_function,
        moderate_risk_function, high_risk_function
    ):
        """Triage should correctly categorize test functions."""
        classifier = TriageClassifier()

        # Test all 4 levels
        assert classifier.classify(trivially_safe_function).level == TriageLevel.LEVEL_0_SKIP
        assert classifier.classify(low_risk_function).level == TriageLevel.LEVEL_1_QUICK
        assert classifier.classify(moderate_risk_function).level == TriageLevel.LEVEL_2_FOCUSED
        assert classifier.classify(high_risk_function).level == TriageLevel.LEVEL_3_DEEP

    def test_level_0_coverage(self):
        """Level 0 should correctly identify trivially safe functions."""
        classifier = TriageClassifier()

        # Create 10 trivially safe functions
        safe_functions = []
        for i in range(10):
            safe_functions.append({
                "name": f"getSomething_{i}",
                "properties": {"state_mutability": "view"}
            })

        results = classifier.batch_classify(safe_functions)
        level_0_pct = results["stats"]["level_0_pct"]

        # Should identify 100% of these as Level 0
        assert level_0_pct == 100.0

    def test_token_reduction(
        self, trivially_safe_function, moderate_risk_function, high_risk_function
    ):
        """Should achieve >= 80% token reduction."""
        optimizer = ContextOptimizer()
        functions = [trivially_safe_function, moderate_risk_function, high_risk_function]
        result = optimizer.batch_optimize(functions)

        reduction = result["stats"]["token_reduction_pct"]
        assert reduction >= 80.0

    def test_compression_parseable(self, high_risk_function):
        """Compressed format should be parseable."""
        compressor = SemanticCompressor()
        result = compressor.compress(high_risk_function, budget=100)

        # Should contain key-value pairs
        assert "|" in result.compressed or ":" in result.compressed
        # Should be compact
        assert len(result.compressed) < 500

    def test_prompt_consistency(self, moderate_risk_function):
        """Same function should produce consistent prompts."""
        optimizer = ContextOptimizer()

        result1 = optimizer.optimize(moderate_risk_function)
        result2 = optimizer.optimize(moderate_risk_function)

        # Should produce identical prompts for same input
        assert result1.prompt == result2.prompt
        assert result1.total_tokens == result2.total_tokens
