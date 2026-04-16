"""Phase 14: Tier B Pattern Integration Tests.

Tests for Tier B matching using risk tags and aggregation modes.
"""

import unittest
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from alphaswarm_sol.queries.patterns import (
    PatternDefinition,
    PatternStore,
    PatternEngine,
    TierBConditionSpec,
)
from alphaswarm_sol.queries.tier_b import (
    AggregationMode,
    ConfidenceLevel,
    TierBCondition,
    TierBMatch,
    TierResult,
    TierBMatcher,
    aggregate_tier_results,
    parse_tier_b_conditions,
)
from alphaswarm_sol.taxonomy.tags import RiskCategory, RiskTag
from alphaswarm_sol.taxonomy.storage import TagStore, NodeTags
from alphaswarm_sol.taxonomy.assignment import TagAssignment
from alphaswarm_sol.kg.schema import Node, KnowledgeGraph


class TestConfidenceLevel(unittest.TestCase):
    """Tests for ConfidenceLevel thresholds."""

    def test_threshold_values(self):
        """Confidence levels have correct thresholds."""
        self.assertEqual(ConfidenceLevel.LOW.threshold(), 0.3)
        self.assertEqual(ConfidenceLevel.MEDIUM.threshold(), 0.5)
        self.assertEqual(ConfidenceLevel.HIGH.threshold(), 0.7)
        self.assertEqual(ConfidenceLevel.VERY_HIGH.threshold(), 0.9)


class TestTierBCondition(unittest.TestCase):
    """Tests for TierBCondition dataclass."""

    def test_condition_creation(self):
        """TierBCondition can be created with all fields."""
        cond = TierBCondition(
            type="has_risk_tag",
            value="cei_violation",
            min_confidence=ConfidenceLevel.HIGH,
        )
        self.assertEqual(cond.type, "has_risk_tag")
        self.assertEqual(cond.value, "cei_violation")
        self.assertEqual(cond.min_confidence, ConfidenceLevel.HIGH)


class TestTierBMatcher(unittest.TestCase):
    """Tests for TierBMatcher class."""

    def setUp(self):
        """Set up test fixtures."""
        self.store = TagStore()
        self.matcher = TierBMatcher(self.store)

    def test_has_risk_tag_match(self):
        """has_risk_tag matches when tag is present."""
        # Create a node with properties
        node = Node(
            id="test_func",
            label="vulnerableWithdraw",
            type="Function",
            properties={"state_write_after_external_call": True}
        )

        # Add tag directly to store
        self.store.add_tag("test_func", TagAssignment(
            tag=RiskTag.CEI_VIOLATION,
            confidence=0.9,
            source="property",
            reason="State written after external call",
        ))

        cond = TierBCondition(
            type="has_risk_tag",
            value="cei_violation",
            min_confidence=ConfidenceLevel.MEDIUM,
        )

        matched, details = self.matcher.match_condition(node, cond)
        self.assertTrue(matched)
        self.assertIn(RiskTag.CEI_VIOLATION.value, details.get("matched_tags", []))

    def test_has_risk_tag_no_match(self):
        """has_risk_tag does not match when tag is missing."""
        node = Node(
            id="test_func",
            label="safeWithdraw",
            type="Function",
            properties={}
        )

        cond = TierBCondition(
            type="has_risk_tag",
            value="cei_violation",
            min_confidence=ConfidenceLevel.MEDIUM,
        )

        matched, _ = self.matcher.match_condition(node, cond)
        self.assertFalse(matched)

    def test_has_risk_tag_confidence_threshold(self):
        """has_risk_tag respects confidence threshold."""
        node = Node(
            id="test_func",
            label="vulnerableWithdraw",
            type="Function",
            properties={}
        )

        # Add tag with low confidence
        self.store.add_tag("test_func", TagAssignment(
            tag=RiskTag.CEI_VIOLATION,
            confidence=0.4,  # Below HIGH threshold
            source="property",
        ))

        cond = TierBCondition(
            type="has_risk_tag",
            value="cei_violation",
            min_confidence=ConfidenceLevel.HIGH,  # 0.7 threshold
        )

        matched, _ = self.matcher.match_condition(node, cond)
        self.assertFalse(matched)  # Should not match due to low confidence

    def test_has_any_risk_tag(self):
        """has_any_risk_tag matches when any tag is present."""
        node = Node(
            id="test_func",
            label="test",
            type="Function",
            properties={}
        )

        self.store.add_tag("test_func", TagAssignment(
            tag=RiskTag.STALE_PRICE,
            confidence=0.8,
        ))

        cond = TierBCondition(
            type="has_any_risk_tag",
            value=["cei_violation", "stale_price", "unbounded_loop"],
            min_confidence=ConfidenceLevel.MEDIUM,
        )

        matched, details = self.matcher.match_condition(node, cond)
        self.assertTrue(matched)

    def test_has_all_risk_tags(self):
        """has_all_risk_tags matches only when all tags are present."""
        node = Node(
            id="test_func",
            label="test",
            type="Function",
            properties={}
        )

        self.store.add_tag("test_func", TagAssignment(
            tag=RiskTag.CEI_VIOLATION,
            confidence=0.8,
        ))
        self.store.add_tag("test_func", TagAssignment(
            tag=RiskTag.EXTERNAL_CALL,
            confidence=0.7,
        ))

        # Should match - both tags present
        cond = TierBCondition(
            type="has_all_risk_tags",
            value=["cei_violation", "external_call"],
            min_confidence=ConfidenceLevel.MEDIUM,
        )

        matched, _ = self.matcher.match_condition(node, cond)
        self.assertTrue(matched)

        # Should not match - missing tag
        cond2 = TierBCondition(
            type="has_all_risk_tags",
            value=["cei_violation", "stale_price"],
            min_confidence=ConfidenceLevel.MEDIUM,
        )

        matched2, _ = self.matcher.match_condition(node, cond2)
        self.assertFalse(matched2)

    def test_has_category(self):
        """has_category matches when any tag in category is present."""
        node = Node(
            id="test_func",
            label="test",
            type="Function",
            properties={}
        )

        self.store.add_tag("test_func", TagAssignment(
            tag=RiskTag.STALE_PRICE,  # Oracle category
            confidence=0.8,
        ))

        cond = TierBCondition(
            type="has_category",
            value="oracle",
            min_confidence=ConfidenceLevel.MEDIUM,
        )

        matched, _ = self.matcher.match_condition(node, cond)
        self.assertTrue(matched)

    def test_match_tier_b_all(self):
        """match_tier_b matches when all conditions pass."""
        node = Node(
            id="test_func",
            label="test",
            type="Function",
            properties={}
        )

        self.store.add_tag("test_func", TagAssignment(
            tag=RiskTag.CEI_VIOLATION,
            confidence=0.9,
            reason="CEI violation detected",
        ))
        self.store.add_tag("test_func", TagAssignment(
            tag=RiskTag.EXTERNAL_CALL,
            confidence=0.8,
            reason="External call made",
        ))

        all_conds = [
            TierBCondition(type="has_risk_tag", value="cei_violation"),
            TierBCondition(type="has_risk_tag", value="external_call"),
        ]

        result = self.matcher.match_tier_b(node, all_conds, [], [])
        self.assertTrue(result.matched)
        self.assertIn(RiskTag.CEI_VIOLATION, result.matched_tags)
        self.assertIn(RiskTag.EXTERNAL_CALL, result.matched_tags)

    def test_match_tier_b_any(self):
        """match_tier_b matches when any condition passes."""
        node = Node(
            id="test_func",
            label="test",
            type="Function",
            properties={}
        )

        self.store.add_tag("test_func", TagAssignment(
            tag=RiskTag.STALE_PRICE,
            confidence=0.8,
        ))

        any_conds = [
            TierBCondition(type="has_risk_tag", value="cei_violation"),
            TierBCondition(type="has_risk_tag", value="stale_price"),
        ]

        result = self.matcher.match_tier_b(node, [], any_conds, [])
        self.assertTrue(result.matched)

    def test_match_tier_b_none(self):
        """match_tier_b fails when none conditions match."""
        node = Node(
            id="test_func",
            label="test",
            type="Function",
            properties={}
        )

        self.store.add_tag("test_func", TagAssignment(
            tag=RiskTag.CEI_VIOLATION,
            confidence=0.9,
        ))

        # Should fail - the node HAS the tag that should be excluded
        none_conds = [
            TierBCondition(type="has_risk_tag", value="cei_violation"),
        ]

        result = self.matcher.match_tier_b(node, [], [], none_conds)
        self.assertFalse(result.matched)


class TestAggregationModes(unittest.TestCase):
    """Tests for aggregation modes."""

    def test_tier_a_only_mode(self):
        """tier_a_only ignores tier_b results."""
        tier_b = TierBMatch(matched=True, confidence=0.9)

        result = aggregate_tier_results(
            tier_a_matched=False,
            tier_b=tier_b,
            mode=AggregationMode.TIER_A_ONLY,
        )

        self.assertFalse(result.final_matched)  # Tier A result

    def test_tier_a_required_gates(self):
        """tier_a_required requires tier_a to match."""
        tier_b = TierBMatch(matched=True, confidence=0.9)

        result = aggregate_tier_results(
            tier_a_matched=False,
            tier_b=tier_b,
            mode=AggregationMode.TIER_A_REQUIRED,
        )

        self.assertFalse(result.final_matched)

        # When tier_a matches
        result2 = aggregate_tier_results(
            tier_a_matched=True,
            tier_b=tier_b,
            mode=AggregationMode.TIER_A_REQUIRED,
        )

        self.assertTrue(result2.final_matched)

    def test_voting_mode_threshold_2(self):
        """voting mode requires threshold matches."""
        tier_b = TierBMatch(matched=True, confidence=0.9)

        # Both match - should pass
        result = aggregate_tier_results(
            tier_a_matched=True,
            tier_b=tier_b,
            mode=AggregationMode.VOTING,
            voting_threshold=2,
        )
        self.assertTrue(result.final_matched)

        # Only tier_a matches - should fail with threshold=2
        result2 = aggregate_tier_results(
            tier_a_matched=True,
            tier_b=TierBMatch(matched=False),
            mode=AggregationMode.VOTING,
            voting_threshold=2,
        )
        self.assertFalse(result2.final_matched)

    def test_voting_mode_threshold_1(self):
        """voting mode with threshold=1 passes if any tier matches."""
        # Only tier_b matches
        result = aggregate_tier_results(
            tier_a_matched=False,
            tier_b=TierBMatch(matched=True),
            mode=AggregationMode.VOTING,
            voting_threshold=1,
        )
        self.assertTrue(result.final_matched)


class TestParseTierBConditions(unittest.TestCase):
    """Tests for parsing tier_b conditions from YAML."""

    def test_parse_has_risk_tag(self):
        """Parse has_risk_tag condition."""
        data = {
            "tier_b": {
                "all": [
                    {"has_risk_tag": "cei_violation", "min_confidence": "high"}
                ]
            }
        }

        all_conds, any_conds, none_conds = parse_tier_b_conditions(data.get("tier_b"))

        self.assertEqual(len(all_conds), 1)
        self.assertEqual(all_conds[0].type, "has_risk_tag")
        self.assertEqual(all_conds[0].value, "cei_violation")
        self.assertEqual(all_conds[0].min_confidence, ConfidenceLevel.HIGH)

    def test_parse_has_category(self):
        """Parse has_category condition."""
        data = {
            "tier_b": {
                "any": [
                    {"has_category": "reentrancy", "min_confidence": "medium"}
                ]
            }
        }

        all_conds, any_conds, none_conds = parse_tier_b_conditions(data.get("tier_b"))

        self.assertEqual(len(any_conds), 1)
        self.assertEqual(any_conds[0].type, "has_category")
        self.assertEqual(any_conds[0].value, "reentrancy")

    def test_parse_none_conditions(self):
        """Parse none conditions."""
        data = {
            "tier_b": {
                "none": [
                    {"has_risk_tag": "owner_only"}
                ]
            }
        }

        all_conds, any_conds, none_conds = parse_tier_b_conditions(data.get("tier_b"))

        self.assertEqual(len(none_conds), 1)
        self.assertEqual(none_conds[0].type, "has_risk_tag")


class TestPatternStoreTierB(unittest.TestCase):
    """Tests for PatternStore parsing tier_b."""

    def test_parse_pattern_with_tier_b(self):
        """PatternStore parses tier_b section correctly."""
        import tempfile
        import yaml

        pattern_data = {
            "id": "test-tier-b-pattern",
            "name": "Test Tier B Pattern",
            "description": "Test pattern with tier_b",
            "scope": "Function",
            "severity": "high",
            "match": {
                "tier_a": {
                    "all": [
                        {"property": "visibility", "op": "in", "value": ["public", "external"]}
                    ]
                },
                "tier_b": {
                    "all": [
                        {"has_risk_tag": "cei_violation", "min_confidence": "high"}
                    ],
                    "any": [
                        {"has_category": "reentrancy"}
                    ]
                }
            },
            "aggregation": {
                "mode": "tier_a_required"
            }
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.yaml"
            path.write_text(yaml.dump(pattern_data))

            store = PatternStore(Path(tmpdir))
            patterns = store.load()

            self.assertEqual(len(patterns), 1)
            p = patterns[0]

            self.assertEqual(p.id, "test-tier-b-pattern")
            self.assertEqual(p.aggregation_mode, "tier_a_required")

            # Check tier_b conditions
            self.assertEqual(len(p.tier_b_all), 1)
            self.assertEqual(p.tier_b_all[0].type, "has_risk_tag")
            self.assertEqual(p.tier_b_all[0].value, "cei_violation")
            self.assertEqual(p.tier_b_all[0].min_confidence, "high")

            self.assertEqual(len(p.tier_b_any), 1)
            self.assertEqual(p.tier_b_any[0].type, "has_category")
            self.assertEqual(p.tier_b_any[0].value, "reentrancy")

    def test_parse_voting_threshold(self):
        """PatternStore parses voting threshold."""
        import tempfile
        import yaml

        pattern_data = {
            "id": "voting-pattern",
            "name": "Voting Pattern",
            "description": "Test voting mode",
            "scope": "Function",
            "match": {
                "tier_a": {
                    "all": [{"property": "visibility", "value": "public"}]
                },
                "tier_b": {
                    "all": [{"has_risk_tag": "external_call"}]
                }
            },
            "aggregation": {
                "mode": "voting",
                "threshold": 1
            }
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.yaml"
            path.write_text(yaml.dump(pattern_data))

            store = PatternStore(Path(tmpdir))
            patterns = store.load()

            self.assertEqual(len(patterns), 1)
            p = patterns[0]
            self.assertEqual(p.aggregation_mode, "voting")
            self.assertEqual(p.voting_threshold, 1)


class TestPatternEngineTierB(unittest.TestCase):
    """Tests for PatternEngine with Tier B integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.store = TagStore()
        self.engine = PatternEngine(tag_store=self.store)

    def test_tier_a_only_mode(self):
        """tier_a_only mode ignores tier_b."""
        # Create a simple graph
        graph = KnowledgeGraph(
            nodes={
                "func1": Node(
                    id="func1",
                    label="vulnerableWithdraw",
                    type="Function",
                    properties={"visibility": "public"}
                )
            },
            edges={},
            metadata={}
        )

        # Pattern with tier_a_only mode
        pattern = PatternDefinition(
            id="test-pattern",
            name="Test Pattern",
            description="Test",
            scope="Function",
            match_all=[],
            aggregation_mode="tier_a_only",
        )

        findings = self.engine.run(graph, [pattern])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["aggregation_mode"], "tier_a_only")

    def test_tier_a_required_with_tier_b(self):
        """tier_a_required mode uses tier_b for context."""
        # Create graph
        graph = KnowledgeGraph(
            nodes={
                "func1": Node(
                    id="func1",
                    label="vulnerableWithdraw",
                    type="Function",
                    properties={"visibility": "public"}
                )
            },
            edges={},
            metadata={}
        )

        # Add tag to store
        self.store.add_tag("func1", TagAssignment(
            tag=RiskTag.CEI_VIOLATION,
            confidence=0.9,
            reason="State after call",
        ))

        # Pattern with tier_a_required mode and tier_b conditions
        pattern = PatternDefinition(
            id="test-pattern",
            name="Test Pattern",
            description="Test",
            scope="Function",
            match_all=[],  # Tier A always matches
            tier_b_all=[TierBConditionSpec(
                type="has_risk_tag",
                value="cei_violation",
                min_confidence="high",
            )],
            aggregation_mode="tier_a_required",
        )

        findings = self.engine.run(graph, [pattern], explain=True)
        self.assertEqual(len(findings), 1)

        # Tier B context should be in explain
        explain = findings[0].get("explain", {})
        tier_b_info = explain.get("tier_b", {})
        self.assertTrue(tier_b_info.get("matched", False))

    def test_voting_mode_both_match(self):
        """voting mode matches when both tiers match."""
        graph = KnowledgeGraph(
            nodes={
                "func1": Node(
                    id="func1",
                    label="test",
                    type="Function",
                    properties={"visibility": "public"}
                )
            },
            edges={},
            metadata={}
        )

        self.store.add_tag("func1", TagAssignment(
            tag=RiskTag.CEI_VIOLATION,
            confidence=0.9,
        ))

        pattern = PatternDefinition(
            id="test-pattern",
            name="Test Pattern",
            description="Test",
            scope="Function",
            match_all=[],  # Tier A matches
            tier_b_all=[TierBConditionSpec(
                type="has_risk_tag",
                value="cei_violation",
            )],
            aggregation_mode="voting",
            voting_threshold=2,
        )

        findings = self.engine.run(graph, [pattern])
        self.assertEqual(len(findings), 1)

    def test_voting_mode_only_tier_a(self):
        """voting mode fails when only tier_a matches and threshold=2."""
        graph = KnowledgeGraph(
            nodes={
                "func1": Node(
                    id="func1",
                    label="test",
                    type="Function",
                    properties={"visibility": "public"}
                )
            },
            edges={},
            metadata={}
        )

        # No tags - tier_b won't match
        pattern = PatternDefinition(
            id="test-pattern",
            name="Test Pattern",
            description="Test",
            scope="Function",
            match_all=[],  # Tier A matches
            tier_b_all=[TierBConditionSpec(
                type="has_risk_tag",
                value="cei_violation",
            )],
            aggregation_mode="voting",
            voting_threshold=2,
        )

        findings = self.engine.run(graph, [pattern])
        self.assertEqual(len(findings), 0)  # No match

    def test_automatic_tag_assignment(self):
        """Tags are assigned automatically from properties."""
        graph = KnowledgeGraph(
            nodes={
                "func1": Node(
                    id="func1",
                    label="test",
                    type="Function",
                    properties={
                        "visibility": "public",
                        "state_write_after_external_call": True,
                    }
                )
            },
            edges={},
            metadata={}
        )

        # Don't pre-add tags - let them be assigned automatically
        engine = PatternEngine()  # No pre-populated store

        pattern = PatternDefinition(
            id="test-pattern",
            name="Test Pattern",
            description="Test",
            scope="Function",
            match_all=[],
            tier_b_all=[TierBConditionSpec(
                type="has_risk_tag",
                value="cei_violation",
                min_confidence="medium",
            )],
            aggregation_mode="tier_a_required",
        )

        findings = engine.run(graph, [pattern], explain=True)
        self.assertEqual(len(findings), 1)

        # Tag should have been auto-assigned
        explain = findings[0].get("explain", {})
        tier_b_info = explain.get("tier_b", {})
        self.assertTrue(tier_b_info.get("matched", False))


class TestTierBMatchSerialization(unittest.TestCase):
    """Tests for TierBMatch serialization."""

    def test_tier_result_creation(self):
        """TierResult can be created with all fields."""
        tier_b = TierBMatch(
            matched=True,
            matched_tags=[RiskTag.CEI_VIOLATION],
            confidence=0.85,
            evidence=["State after call"],
        )

        result = TierResult(
            tier_a_matched=True,
            tier_b_matched=True,
            tier_b_context=tier_b,
            final_matched=True,
            aggregation_mode="tier_a_required",
        )

        self.assertTrue(result.tier_a_matched)
        self.assertTrue(result.tier_b_matched)
        self.assertTrue(result.final_matched)
        self.assertEqual(result.aggregation_mode, "tier_a_required")


if __name__ == "__main__":
    unittest.main()
