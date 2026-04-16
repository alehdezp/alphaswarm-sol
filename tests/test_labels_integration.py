"""Integration tests for semantic labeling.

Tests the complete flow from labeling to pattern matching,
covering the labeling pipeline, Tier C matching, context filtering,
evaluation, validation, and overlay persistence.
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from alphaswarm_sol.labels import (
    LLMLabeler,
    LabelingConfig,
    LabelOverlay,
    FunctionLabel,
    LabelConfidence,
    LabelSource,
    LabelSet,
    LabelFilter,
    LabelValidator,
    ValidationStatus,
    run_evaluation,
    EvaluationReport,
    PrecisionMetrics,
    get_relevant_categories,
    filter_labels_for_context,
    CONTEXT_TO_CATEGORIES,
)
from alphaswarm_sol.queries.tier_c import (
    TierCMatcher,
    TierCCondition,
    TierCConditionType,
    TierCMatch,
    aggregate_tier_results,
)


class TestLabelingIntegration:
    """Test complete labeling flow."""

    @pytest.fixture
    def mock_graph(self):
        """Create mock knowledge graph."""
        graph = MagicMock()
        graph.nodes = {
            "Vault.withdraw": MagicMock(
                id="Vault.withdraw",
                type="function",
                properties={
                    "signature": "function withdraw(uint256 amount) external",
                    "visibility": "external",
                    "source_code": "function withdraw(uint256 amount) external { msg.sender.transfer(amount); }",
                },
            ),
            "Vault.deposit": MagicMock(
                id="Vault.deposit",
                type="function",
                properties={
                    "signature": "function deposit() external payable",
                    "visibility": "external",
                    "source_code": "function deposit() external payable { balances[msg.sender] += msg.value; }",
                },
            ),
            "Vault.owner": MagicMock(
                id="Vault.owner",
                type="state_variable",
                properties={},
            ),
        }
        graph.edges = MagicMock()
        graph.edges.values = MagicMock(return_value=[])
        return graph

    @pytest.fixture
    def mock_provider(self):
        """Create mock LLM provider."""
        provider = MagicMock()
        response = MagicMock()
        response.content = ""
        response.tool_calls = [{
            "name": "apply_labels_batch",
            "input": {
                "labels": [
                    {
                        "function_id": "Vault.withdraw",
                        "label": "value_handling.transfers_value_out",
                        "confidence": "high",
                        "reasoning": "Transfers ETH to msg.sender",
                    },
                    {
                        "function_id": "Vault.withdraw",
                        "label": "access_control.no_restriction",
                        "confidence": "medium",
                        "reasoning": "No access control modifier",
                    },
                    {
                        "function_id": "Vault.deposit",
                        "label": "value_handling.collects_fees",
                        "confidence": "high",
                        "reasoning": "Payable function that receives ETH",
                    },
                ]
            }
        }]
        response.input_tokens = 500
        response.output_tokens = 200
        response.cost_usd = 0.001
        provider.generate_with_tools = AsyncMock(return_value=response)
        return provider

    @pytest.mark.asyncio
    async def test_labeling_flow(self, mock_graph, mock_provider):
        """Test complete labeling flow."""
        config = LabelingConfig(max_tokens_per_call=6000)
        labeler = LLMLabeler(mock_provider, config)

        # Run labeling on function nodes only
        function_ids = [
            node_id for node_id, node in mock_graph.nodes.items()
            if node.type == "function"
        ]

        result = await labeler.label_functions(mock_graph, function_ids)

        # Check results
        assert result.functions_labeled == 2
        assert result.labels_applied == 3
        assert result.total_tokens > 0
        assert result.total_cost_usd > 0

        # Check overlay
        overlay = labeler.get_overlay()
        assert len(overlay.labels) == 2

        withdraw_labels = overlay.get_labels("Vault.withdraw")
        assert withdraw_labels.has_label("value_handling.transfers_value_out")
        assert withdraw_labels.has_label("access_control.no_restriction")

    @pytest.mark.asyncio
    async def test_tier_c_matching_with_labels(self, mock_graph, mock_provider):
        """Test Tier C pattern matching with labels."""
        # First, label the functions
        labeler = LLMLabeler(mock_provider)
        function_ids = [k for k, v in mock_graph.nodes.items() if v.type == "function"]
        await labeler.label_functions(mock_graph, function_ids)
        overlay = labeler.get_overlay()

        # Create Tier C matcher
        matcher = TierCMatcher(overlay)

        # Test has_label condition
        result = matcher.match(
            "Vault.withdraw",
            conditions_all=[
                TierCCondition(TierCConditionType.HAS_LABEL, "value_handling.transfers_value_out"),
            ],
        )
        assert result.matched
        assert "value_handling.transfers_value_out" in result.matched_labels

        # Test missing_label condition
        result = matcher.match(
            "Vault.withdraw",
            conditions_all=[
                TierCCondition(TierCConditionType.MISSING_LABEL, "access_control.owner_only"),
            ],
        )
        assert result.matched

    @pytest.mark.asyncio
    async def test_labeling_with_batch_size(self, mock_graph, mock_provider):
        """Test labeling respects batch size configuration."""
        config = LabelingConfig(
            max_tokens_per_call=6000,
            max_functions_per_batch=1,  # One function per batch
        )
        labeler = LLMLabeler(mock_provider, config)

        function_ids = [k for k, v in mock_graph.nodes.items() if v.type == "function"]
        result = await labeler.label_functions(mock_graph, function_ids)

        # With batch size of 1, should make 2 calls for 2 functions
        assert mock_provider.generate_with_tools.call_count == 2

    def test_labeling_config_defaults(self):
        """Test default labeling configuration."""
        config = LabelingConfig()
        assert config.max_tokens_per_call == 6000
        assert config.max_functions_per_batch == 5
        assert config.min_confidence_threshold == LabelConfidence.LOW
        assert config.temperature == 0.1


class TestContextFiltering:
    """Test context-filtered label retrieval."""

    @pytest.fixture
    def labeled_overlay(self):
        """Create overlay with various labels."""
        overlay = LabelOverlay()
        overlay.add_label("func_1", FunctionLabel(
            label_id="access_control.owner_only",
            confidence=LabelConfidence.HIGH,
            source=LabelSource.LLM,
        ))
        overlay.add_label("func_1", FunctionLabel(
            label_id="value_handling.transfers_value_out",
            confidence=LabelConfidence.MEDIUM,
            source=LabelSource.LLM,
        ))
        overlay.add_label("func_1", FunctionLabel(
            label_id="state_mutation.writes_critical",
            confidence=LabelConfidence.LOW,
            source=LabelSource.LLM,
            reasoning="Modifies balance mapping",
        ))
        overlay.add_label("func_1", FunctionLabel(
            label_id="external_interaction.calls_untrusted",
            confidence=LabelConfidence.HIGH,
            source=LabelSource.LLM,
        ))
        return overlay

    def test_reentrancy_context_filters_access_control(self, labeled_overlay):
        """Test that access_control labels are filtered for reentrancy context."""
        filter = LabelFilter(labeled_overlay)
        result = filter.get_filtered_labels("func_1", "reentrancy")

        # Should NOT include access_control labels
        label_ids = [l.label_id for l in result.labels_included]
        assert "access_control.owner_only" not in label_ids

        # Should include value_handling and external_interaction
        assert "value_handling.transfers_value_out" in label_ids
        assert "external_interaction.calls_untrusted" in label_ids

    def test_access_control_context(self, labeled_overlay):
        """Test access_control context filters correctly."""
        filter = LabelFilter(labeled_overlay)
        result = filter.get_filtered_labels("func_1", "access_control")

        label_ids = [l.label_id for l in result.labels_included]
        assert "access_control.owner_only" in label_ids
        # Value handling should be filtered out
        assert "value_handling.transfers_value_out" not in label_ids

    def test_general_context_includes_all(self, labeled_overlay):
        """Test general context includes all labels."""
        filter = LabelFilter(labeled_overlay)
        result = filter.get_filtered_labels("func_1", "general")

        # All labels should be included (that pass confidence threshold)
        assert result.included_count >= 3

    def test_confidence_threshold_filtering(self, labeled_overlay):
        """Test filtering by confidence threshold."""
        filter = LabelFilter(labeled_overlay, default_min_confidence=LabelConfidence.HIGH)
        result = filter.get_filtered_labels("func_1", "general")

        # Only HIGH confidence labels should be included
        for label in result.labels_included:
            assert label.confidence == LabelConfidence.HIGH

    def test_context_to_categories_mapping(self):
        """Test CONTEXT_TO_CATEGORIES contains expected mappings."""
        assert "reentrancy" in CONTEXT_TO_CATEGORIES
        assert "access_control" in CONTEXT_TO_CATEGORIES
        assert "oracle_manipulation" in CONTEXT_TO_CATEGORIES
        assert "flash_loan" in CONTEXT_TO_CATEGORIES

        # Reentrancy should include external_interaction and value_handling
        reentrancy_cats = CONTEXT_TO_CATEGORIES["reentrancy"]
        assert "external_interaction" in reentrancy_cats
        assert "value_handling" in reentrancy_cats

    def test_get_relevant_categories_fuzzy_match(self):
        """Test fuzzy matching for context names."""
        # Exact match
        cats = get_relevant_categories("reentrancy")
        assert "external_interaction" in cats

        # Partial match should work
        cats = get_relevant_categories("access")
        assert "access_control" in cats

    def test_filter_labels_for_context_helper(self):
        """Test convenience function for filtering."""
        labels = [
            FunctionLabel("access_control.owner_only", LabelConfidence.HIGH, LabelSource.LLM),
            FunctionLabel("value_handling.transfers_value_out", LabelConfidence.HIGH, LabelSource.LLM),
        ]

        filtered = filter_labels_for_context(labels, "reentrancy")
        label_ids = [l.label_id for l in filtered]

        # Only value_handling should remain
        assert "access_control.owner_only" not in label_ids
        assert "value_handling.transfers_value_out" in label_ids


class TestEvaluationIntegration:
    """Test evaluation with real overlays."""

    def test_full_evaluation(self):
        """Test evaluation pipeline."""
        # Create ground truth
        ground_truth = LabelOverlay()
        ground_truth.add_label("func_1", FunctionLabel(
            label_id="access_control.owner_only",
            confidence=LabelConfidence.HIGH,
            source=LabelSource.USER_OVERRIDE,
        ))
        ground_truth.add_label("func_1", FunctionLabel(
            label_id="state_mutation.writes_critical",
            confidence=LabelConfidence.MEDIUM,
            source=LabelSource.USER_OVERRIDE,
        ))

        # Create predicted (partial match)
        predicted = LabelOverlay()
        predicted.add_label("func_1", FunctionLabel(
            label_id="access_control.owner_only",
            confidence=LabelConfidence.MEDIUM,
            source=LabelSource.LLM,
        ))
        predicted.add_label("func_1", FunctionLabel(
            label_id="external_interaction.calls_untrusted",
            confidence=LabelConfidence.HIGH,
            source=LabelSource.LLM,
        ))

        # Run evaluation
        report = run_evaluation(predicted, ground_truth)

        # Check metrics
        assert report.precision_metrics.true_positives == 1
        assert report.precision_metrics.false_positives == 1
        assert report.precision_metrics.false_negatives == 1
        assert report.precision_metrics.precision == 0.5

    def test_evaluation_report_methods(self):
        """Test EvaluationReport methods."""
        report = EvaluationReport()
        report.precision_metrics = PrecisionMetrics(
            true_positives=8,
            false_positives=2,
            false_negatives=2,
        )

        # Check precision calculation
        assert report.precision_metrics.precision == 0.8  # 8/10
        assert report.precision_metrics.recall == 0.8  # 8/10
        assert abs(report.precision_metrics.f1_score - 0.8) < 0.01

    def test_exit_gate_criteria(self):
        """Test exit gate checking."""
        report = EvaluationReport()
        report.precision_metrics = PrecisionMetrics(
            true_positives=80,
            false_positives=20,
            false_negatives=10,
        )

        # Set token metrics
        from alphaswarm_sol.labels.evaluation import TokenMetrics
        report.token_metrics = TokenMetrics(
            total_tokens=5000,
            max_tokens_single_call=5500,
        )

        # Check exit gate with default criteria
        passed = report.check_exit_gate(
            min_precision=0.75,
            min_detection_delta=0.0,  # Ignore for this test
            max_tokens_per_call=6000,
        )

        assert report.exit_gate_details["precision_met"] is True
        assert report.exit_gate_details["token_budget_met"] is True

    def test_empty_evaluation(self):
        """Test evaluation with empty overlays."""
        empty_gt = LabelOverlay()
        empty_pred = LabelOverlay()

        report = run_evaluation(empty_pred, empty_gt)
        assert report.precision_metrics.precision == 0.0
        assert report.precision_metrics.recall == 0.0


class TestValidationIntegration:
    """Test validation in full flow."""

    def test_validation_catches_invalid_labels(self):
        """Test that validator catches issues."""
        overlay = LabelOverlay()

        # Add valid label
        overlay.add_label("func_1", FunctionLabel(
            label_id="access_control.owner_only",
            confidence=LabelConfidence.HIGH,
            source=LabelSource.LLM,
        ))

        # Add label with missing reasoning (LOW confidence)
        overlay.add_label("func_2", FunctionLabel(
            label_id="state_mutation.writes_critical",
            confidence=LabelConfidence.LOW,
            source=LabelSource.LLM,
            # Missing reasoning - should be flagged
        ))

        validator = LabelValidator(strict_reasoning=True)

        # Validate func_1 - should pass
        result1 = validator.validate_label_set(overlay.get_labels("func_1"))
        assert not result1.has_errors

        # Validate func_2 - should flag missing reasoning
        result2 = validator.validate_label_set(overlay.get_labels("func_2"))
        assert result2.has_errors
        errors = result2.get_errors()
        assert any(e.status == ValidationStatus.MISSING_REASONING for e in errors)

    def test_validation_allows_low_confidence_with_reasoning(self):
        """Test that LOW confidence with reasoning passes."""
        overlay = LabelOverlay()
        overlay.add_label("func_1", FunctionLabel(
            label_id="state_mutation.writes_critical",
            confidence=LabelConfidence.LOW,
            source=LabelSource.LLM,
            reasoning="Uncertain due to complex control flow",
        ))

        validator = LabelValidator(strict_reasoning=True)
        result = validator.validate_label_set(overlay.get_labels("func_1"))
        assert not result.has_errors

    def test_validation_detects_invalid_label_ids(self):
        """Test detection of invalid label IDs."""
        validator = LabelValidator()

        # Create a label with invalid ID
        invalid_label = FunctionLabel(
            label_id="not_a_real.category",
            confidence=LabelConfidence.HIGH,
            source=LabelSource.LLM,
        )

        result = validator.validate_label(invalid_label)
        assert result.status == ValidationStatus.INVALID_LABEL

    def test_validation_quality_scoring(self):
        """Test quality scoring for overlays."""
        overlay = LabelOverlay()

        # Add labels with mixed confidence
        overlay.add_label("func_1", FunctionLabel(
            "access_control.owner_only", LabelConfidence.HIGH, LabelSource.LLM
        ))
        overlay.add_label("func_2", FunctionLabel(
            "value_handling.transfers_value_out", LabelConfidence.MEDIUM, LabelSource.LLM
        ))
        overlay.add_label("func_3", FunctionLabel(
            "state_mutation.writes_critical", LabelConfidence.LOW, LabelSource.LLM,
            reasoning="Needs review"
        ))

        validator = LabelValidator()
        score = validator.score_labels(overlay)

        # Check confidence distribution
        assert score.confidence_distribution.high == 1
        assert score.confidence_distribution.medium == 1
        assert score.confidence_distribution.low == 1
        assert score.confidence_distribution.total == 3

        # Overall score should be between 0 and 1
        assert 0 <= score.overall_score <= 1


class TestOverlayPersistence:
    """Test overlay save/load."""

    def test_json_round_trip(self, tmp_path):
        """Test JSON export and import."""
        overlay = LabelOverlay()
        overlay.add_label("Vault.withdraw", FunctionLabel(
            label_id="access_control.owner_only",
            confidence=LabelConfidence.HIGH,
            source=LabelSource.LLM,
            reasoning="Has onlyOwner modifier",
        ))

        # Export
        json_path = tmp_path / "labels.json"
        overlay.export_json(json_path)
        assert json_path.exists()

        # Import
        loaded = LabelOverlay.from_json(json_path)
        assert len(loaded.labels) == 1
        assert loaded.get_labels("Vault.withdraw").has_label("access_control.owner_only")

        # Check reasoning was preserved
        label = loaded.get_labels("Vault.withdraw").get_label("access_control.owner_only")
        assert label.reasoning == "Has onlyOwner modifier"

    def test_yaml_round_trip(self, tmp_path):
        """Test YAML export and import."""
        overlay = LabelOverlay()
        overlay.add_label("Token.transfer", FunctionLabel(
            label_id="value_handling.transfers_value_out",
            confidence=LabelConfidence.MEDIUM,
            source=LabelSource.LLM,
        ))

        # Export
        yaml_path = tmp_path / "labels.yaml"
        overlay.export_yaml(yaml_path)
        assert yaml_path.exists()

        # Import
        loaded = LabelOverlay.from_yaml(yaml_path)
        assert len(loaded.labels) == 1

        label_set = loaded.get_labels("Token.transfer")
        assert label_set.has_label("value_handling.transfers_value_out")

    def test_overlay_merge(self):
        """Test merging two overlays."""
        overlay_a = LabelOverlay()
        overlay_a.add_label("func_1", FunctionLabel(
            "access_control.owner_only", LabelConfidence.HIGH, LabelSource.LLM
        ))

        overlay_b = LabelOverlay()
        overlay_b.add_label("func_2", FunctionLabel(
            "value_handling.transfers_value_out", LabelConfidence.HIGH, LabelSource.LLM
        ))

        merged = overlay_a.merge(overlay_b)

        # Should have labels from both
        assert len(merged.labels) == 2
        assert "func_1" in merged.labels
        assert "func_2" in merged.labels

    def test_overlay_metadata_preserved(self, tmp_path):
        """Test that metadata survives round-trip."""
        overlay = LabelOverlay()
        overlay.metadata = {"source": "test", "version": "1.0"}
        overlay.add_label("func_1", FunctionLabel(
            "access_control.owner_only", LabelConfidence.HIGH, LabelSource.LLM
        ))

        json_path = tmp_path / "labels_meta.json"
        overlay.export_json(json_path)

        loaded = LabelOverlay.from_json(json_path)
        assert loaded.metadata.get("source") == "test"
        assert loaded.metadata.get("version") == "1.0"


class TestTierCMatcher:
    """Test Tier C pattern matching in detail."""

    @pytest.fixture
    def test_overlay(self):
        """Create overlay for testing."""
        overlay = LabelOverlay()
        overlay.add_label("vulnerable_fn", FunctionLabel(
            "value_handling.transfers_value_out", LabelConfidence.HIGH, LabelSource.LLM
        ))
        overlay.add_label("vulnerable_fn", FunctionLabel(
            "access_control.no_restriction", LabelConfidence.MEDIUM, LabelSource.LLM
        ))
        overlay.add_label("vulnerable_fn", FunctionLabel(
            "external_interaction.calls_untrusted", LabelConfidence.HIGH, LabelSource.LLM
        ))

        overlay.add_label("safe_fn", FunctionLabel(
            "access_control.owner_only", LabelConfidence.HIGH, LabelSource.LLM
        ))
        overlay.add_label("safe_fn", FunctionLabel(
            "value_handling.transfers_value_out", LabelConfidence.HIGH, LabelSource.LLM
        ))

        return overlay

    def test_has_label_condition(self, test_overlay):
        """Test has_label condition type."""
        matcher = TierCMatcher(test_overlay)

        result = matcher.match(
            "vulnerable_fn",
            conditions_all=[
                TierCCondition(TierCConditionType.HAS_LABEL, "value_handling.transfers_value_out"),
            ]
        )
        assert result.matched
        assert "value_handling.transfers_value_out" in result.matched_labels

    def test_has_any_label_condition(self, test_overlay):
        """Test has_any_label condition type."""
        matcher = TierCMatcher(test_overlay)

        result = matcher.match(
            "vulnerable_fn",
            conditions_any=[
                TierCCondition(
                    TierCConditionType.HAS_ANY_LABEL,
                    ["access_control.owner_only", "access_control.no_restriction"]
                ),
            ]
        )
        assert result.matched
        assert "access_control.no_restriction" in result.matched_labels

    def test_has_all_labels_condition(self, test_overlay):
        """Test has_all_labels condition type."""
        matcher = TierCMatcher(test_overlay)

        result = matcher.match(
            "vulnerable_fn",
            conditions_all=[
                TierCCondition(
                    TierCConditionType.HAS_ALL_LABELS,
                    ["value_handling.transfers_value_out", "external_interaction.calls_untrusted"]
                ),
            ]
        )
        assert result.matched

    def test_missing_label_condition(self, test_overlay):
        """Test missing_label condition type."""
        matcher = TierCMatcher(test_overlay)

        result = matcher.match(
            "vulnerable_fn",
            conditions_all=[
                TierCCondition(TierCConditionType.MISSING_LABEL, "access_control.owner_only"),
            ]
        )
        assert result.matched

    def test_none_conditions(self, test_overlay):
        """Test none conditions (forbidden patterns)."""
        matcher = TierCMatcher(test_overlay)

        # vulnerable_fn has no_restriction, so it should fail none condition
        result = matcher.match(
            "vulnerable_fn",
            conditions_none=[
                TierCCondition(TierCConditionType.HAS_LABEL, "access_control.no_restriction"),
            ]
        )
        assert not result.matched

    def test_aggregate_tier_results(self, test_overlay):
        """Test aggregation of tier results."""
        # tier_a_only mode - only tier A matters
        result = aggregate_tier_results(
            tier_a=True,
            tier_c=TierCMatch(matched=False),
            mode="tier_a_only",
        )
        assert result.final_matched is True

        # tier_abc_all mode - all must match
        result = aggregate_tier_results(
            tier_a=True,
            tier_c=TierCMatch(matched=False),
            mode="tier_abc_all",
        )
        assert result.final_matched is False

        # voting mode
        result = aggregate_tier_results(
            tier_a=True,
            tier_c=TierCMatch(matched=True),
            mode="voting",
        )
        assert result.final_matched is True


class TestLabelSet:
    """Test LabelSet operations."""

    def test_label_replacement_on_higher_confidence(self):
        """Test that higher confidence labels replace lower ones."""
        label_set = LabelSet(function_id="test")

        # Add LOW confidence
        label_set.add(FunctionLabel(
            "access_control.owner_only", LabelConfidence.LOW, LabelSource.LLM
        ))
        assert label_set.labels[0].confidence == LabelConfidence.LOW

        # Add HIGH confidence - should replace
        label_set.add(FunctionLabel(
            "access_control.owner_only", LabelConfidence.HIGH, LabelSource.LLM
        ))
        assert len(label_set.labels) == 1
        assert label_set.labels[0].confidence == LabelConfidence.HIGH

    def test_has_label_with_confidence(self):
        """Test has_label with confidence threshold."""
        label_set = LabelSet(function_id="test")
        label_set.add(FunctionLabel(
            "access_control.owner_only", LabelConfidence.MEDIUM, LabelSource.LLM
        ))

        # Should match with LOW threshold
        assert label_set.has_label("access_control.owner_only", LabelConfidence.LOW)

        # Should match with MEDIUM threshold
        assert label_set.has_label("access_control.owner_only", LabelConfidence.MEDIUM)

        # Should NOT match with HIGH threshold
        assert not label_set.has_label("access_control.owner_only", LabelConfidence.HIGH)

    def test_get_by_category(self):
        """Test getting labels by category."""
        label_set = LabelSet(function_id="test")
        label_set.add(FunctionLabel(
            "access_control.owner_only", LabelConfidence.HIGH, LabelSource.LLM
        ))
        label_set.add(FunctionLabel(
            "value_handling.transfers_value_out", LabelConfidence.HIGH, LabelSource.LLM
        ))

        ac_labels = label_set.get_by_category("access_control")
        assert len(ac_labels) == 1
        assert ac_labels[0].label_id == "access_control.owner_only"


class TestFunctionLabel:
    """Test FunctionLabel properties."""

    def test_category_extraction(self):
        """Test category property extracts correctly."""
        label = FunctionLabel(
            "access_control.owner_only", LabelConfidence.HIGH, LabelSource.LLM
        )
        assert label.category == "access_control"
        assert label.subcategory == "owner_only"

    def test_serialization_round_trip(self):
        """Test label serialization."""
        label = FunctionLabel(
            label_id="value_handling.transfers_value_out",
            confidence=LabelConfidence.MEDIUM,
            source=LabelSource.LLM,
            reasoning="Makes external call with value",
        )

        data = label.to_dict()
        restored = FunctionLabel.from_dict(data)

        assert restored.label_id == label.label_id
        assert restored.confidence == label.confidence
        assert restored.source == label.source
        assert restored.reasoning == label.reasoning

    def test_confidence_from_score(self):
        """Test converting numeric scores to confidence."""
        assert LabelConfidence.from_score(0.9) == LabelConfidence.HIGH
        assert LabelConfidence.from_score(0.75) == LabelConfidence.MEDIUM
        assert LabelConfidence.from_score(0.3) == LabelConfidence.LOW
