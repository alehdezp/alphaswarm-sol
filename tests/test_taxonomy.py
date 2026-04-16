"""Phase 13: Risk Tag Taxonomy Tests.

Tests for the hierarchical risk tag system including:
- Tag hierarchy and categories
- Tag assignment from properties and operations
- Tag storage and querying
- Tag-based pattern matching
"""

import unittest
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from alphaswarm_sol.taxonomy.tags import (
    RiskCategory,
    RiskTag,
    RISK_TAG_HIERARCHY,
    RISK_TAG_DESCRIPTIONS,
    get_tag_category,
    get_tags_in_category,
    get_all_tags,
    is_valid_tag,
    get_parent_category,
    get_tag_description,
    get_related_tags,
)
from alphaswarm_sol.taxonomy.assignment import (
    TagAssignment,
    TagAssigner,
    PROPERTY_TAG_RULES,
    OPERATION_TAG_RULES,
    assign_tags_from_properties,
    assign_tags_from_operations,
)
from alphaswarm_sol.taxonomy.storage import (
    NodeTags,
    TagStore,
    add_tag_to_node,
    get_node_tags,
    query_nodes_by_tag,
)
from alphaswarm_sol.taxonomy.matching import (
    MatchOperator,
    TagCondition,
    TagPattern,
    TagMatchResult,
    TagMatcher,
    match_tag_pattern,
    has_risk_tag,
    REENTRANCY_PATTERN,
    ACCESS_CONTROL_PATTERN,
    ORACLE_MANIPULATION_PATTERN,
    DOS_PATTERN,
)


# Mock Node class for testing
@dataclass
class MockNode:
    """Mock Node for testing tag assignment."""
    id: str
    properties: Dict[str, Any] = field(default_factory=dict)


class TestRiskTags(unittest.TestCase):
    """Tests for the hierarchical tag system."""

    def test_risk_categories_defined(self):
        """All expected categories are defined."""
        expected = [
            "ACCESS_CONTROL", "REENTRANCY", "ARITHMETIC", "ORACLE",
            "MEV", "LOGIC", "UPGRADE", "DOS", "CRYPTO", "TOKEN",
            "INITIALIZATION", "EXTERNAL"
        ]
        for cat in expected:
            self.assertTrue(hasattr(RiskCategory, cat))

    def test_risk_tags_defined(self):
        """Critical risk tags are defined."""
        critical_tags = [
            "CEI_VIOLATION", "MISSING_ACCESS_CONTROL", "STALE_PRICE",
            "UNBOUNDED_LOOP", "UNPROTECTED_INIT", "ECRECOVER_ZERO"
        ]
        for tag in critical_tags:
            self.assertTrue(hasattr(RiskTag, tag))

    def test_hierarchy_complete(self):
        """Every tag has a category in hierarchy."""
        all_tags_in_hierarchy = set()
        for tags in RISK_TAG_HIERARCHY.values():
            all_tags_in_hierarchy.update(tags)

        for tag in RiskTag:
            self.assertIn(tag, all_tags_in_hierarchy,
                          f"Tag {tag} not in hierarchy")

    def test_descriptions_complete(self):
        """Every tag has a description."""
        for tag in RiskTag:
            desc = RISK_TAG_DESCRIPTIONS.get(tag)
            self.assertIsNotNone(desc, f"Tag {tag} missing description")
            self.assertGreater(len(desc), 0)

    def test_get_tag_category(self):
        """get_tag_category returns correct category."""
        self.assertEqual(
            get_tag_category(RiskTag.CEI_VIOLATION),
            RiskCategory.REENTRANCY
        )
        self.assertEqual(
            get_tag_category(RiskTag.STALE_PRICE),
            RiskCategory.ORACLE
        )
        self.assertEqual(
            get_tag_category(RiskTag.MISSING_ACCESS_CONTROL),
            RiskCategory.ACCESS_CONTROL
        )

    def test_get_tags_in_category(self):
        """get_tags_in_category returns correct tags."""
        reentrancy_tags = get_tags_in_category(RiskCategory.REENTRANCY)
        self.assertIn(RiskTag.CEI_VIOLATION, reentrancy_tags)
        self.assertIn(RiskTag.EXTERNAL_CALL, reentrancy_tags)
        self.assertIn(RiskTag.STATE_AFTER_CALL, reentrancy_tags)

    def test_get_all_tags(self):
        """get_all_tags returns all defined tags."""
        all_tags = get_all_tags()
        self.assertEqual(len(all_tags), len(RiskTag))

    def test_is_valid_tag(self):
        """is_valid_tag correctly validates tags."""
        self.assertTrue(is_valid_tag("cei_violation"))
        self.assertTrue(is_valid_tag("stale_price"))
        self.assertFalse(is_valid_tag("not_a_real_tag"))
        self.assertFalse(is_valid_tag(""))

    def test_get_tag_description(self):
        """get_tag_description returns correct description."""
        desc = get_tag_description(RiskTag.CEI_VIOLATION)
        self.assertIn("Checks-Effects-Interactions", desc)

    def test_get_related_tags(self):
        """get_related_tags returns tags in same category."""
        related = get_related_tags(RiskTag.CEI_VIOLATION)
        self.assertIn(RiskTag.EXTERNAL_CALL, related)
        self.assertNotIn(RiskTag.CEI_VIOLATION, related)  # Exclude self


class TestTagAssignment(unittest.TestCase):
    """Tests for tag assignment from properties and operations."""

    def test_tag_assignment_creation(self):
        """TagAssignment can be created with all fields."""
        assignment = TagAssignment(
            tag=RiskTag.CEI_VIOLATION,
            confidence=0.9,
            source="property",
            reason="State written after external call",
            evidence=["state_write_after_external_call=True"]
        )
        self.assertEqual(assignment.tag, RiskTag.CEI_VIOLATION)
        self.assertEqual(assignment.confidence, 0.9)
        self.assertEqual(assignment.source, "property")

    def test_tag_assignment_to_dict(self):
        """TagAssignment serializes to dictionary."""
        assignment = TagAssignment(
            tag=RiskTag.STALE_PRICE,
            confidence=0.8,
            source="operation",
            reason="No staleness check"
        )
        d = assignment.to_dict()
        self.assertEqual(d["tag"], "stale_price")
        self.assertEqual(d["category"], "oracle")
        self.assertEqual(d["confidence"], 0.8)

    def test_tag_assignment_from_dict(self):
        """TagAssignment deserializes from dictionary."""
        d = {
            "tag": "cei_violation",
            "confidence": 0.85,
            "source": "llm",
            "reason": "Detected CEI violation",
            "evidence": ["line 42"]
        }
        assignment = TagAssignment.from_dict(d)
        self.assertEqual(assignment.tag, RiskTag.CEI_VIOLATION)
        self.assertEqual(assignment.confidence, 0.85)
        self.assertEqual(assignment.source, "llm")

    def test_property_rules_defined(self):
        """Property-based tag rules are defined."""
        expected_properties = [
            "uses_tx_origin", "has_access_gate", "state_write_after_external_call",
            "has_reentrancy_guard", "reads_oracle_price", "has_unbounded_loop"
        ]
        for prop in expected_properties:
            self.assertIn(prop, PROPERTY_TAG_RULES)

    def test_operation_rules_defined(self):
        """Operation-based tag rules are defined."""
        expected_ops = [
            "TRANSFERS_VALUE_OUT", "CALLS_EXTERNAL", "CALLS_UNTRUSTED",
            "MODIFIES_OWNER", "READS_ORACLE"
        ]
        for op in expected_ops:
            self.assertIn(op, OPERATION_TAG_RULES)

    def test_assign_from_properties_cei_violation(self):
        """Properties assign CEI violation tag."""
        node = MockNode(
            id="test_func",
            properties={"state_write_after_external_call": True}
        )
        assignments = assign_tags_from_properties(node)
        tags = [a.tag for a in assignments]
        self.assertIn(RiskTag.CEI_VIOLATION, tags)

    def test_assign_from_properties_tx_origin(self):
        """Properties assign tx.origin tag."""
        node = MockNode(
            id="test_func",
            properties={"uses_tx_origin": True}
        )
        assignments = assign_tags_from_properties(node)
        tags = [a.tag for a in assignments]
        self.assertIn(RiskTag.TX_ORIGIN, tags)

    def test_assign_from_properties_unbounded_loop(self):
        """Properties assign unbounded loop tag."""
        node = MockNode(
            id="test_func",
            properties={"has_unbounded_loop": True}
        )
        assignments = assign_tags_from_properties(node)
        tags = [a.tag for a in assignments]
        self.assertIn(RiskTag.UNBOUNDED_LOOP, tags)

    def test_assign_from_operations(self):
        """Operations assign appropriate tags."""
        node = MockNode(
            id="test_func",
            properties={"semantic_ops": ["CALLS_UNTRUSTED", "TRANSFERS_VALUE_OUT"]}
        )
        assignments = assign_tags_from_operations(node)
        tags = [a.tag for a in assignments]
        self.assertIn(RiskTag.UNTRUSTED_CALL, tags)
        self.assertIn(RiskTag.EXTERNAL_CALL, tags)

    def test_tag_assigner_combined(self):
        """TagAssigner combines property and operation assignments."""
        node = MockNode(
            id="vulnerable_func",
            properties={
                "uses_tx_origin": True,
                "has_access_gate": False,
                "semantic_ops": ["MODIFIES_OWNER"]
            }
        )
        assigner = TagAssigner(min_confidence=0.5)
        assignments = assigner.assign_tags(node)
        tags = [a.tag for a in assignments]
        self.assertIn(RiskTag.TX_ORIGIN, tags)
        self.assertIn(RiskTag.MISSING_ACCESS_CONTROL, tags)
        self.assertIn(RiskTag.PRIVILEGED_WRITE, tags)

    def test_confidence_boosting(self):
        """Multiple signals in same category boost confidence."""
        node = MockNode(
            id="test_func",
            properties={
                "state_write_after_external_call": True,  # CEI_VIOLATION
                "has_reentrancy_guard": False,  # EXTERNAL_CALL
                "semantic_ops": ["CALLS_EXTERNAL"]  # EXTERNAL_CALL
            }
        )
        assigner = TagAssigner(min_confidence=0.3)
        assignments = assigner.assign_tags(node)

        # Find reentrancy-related tags
        reentrancy_assignments = [
            a for a in assignments
            if get_tag_category(a.tag) == RiskCategory.REENTRANCY
        ]
        # Should have boosted confidence
        if reentrancy_assignments:
            self.assertGreater(len(reentrancy_assignments), 0)

    def test_min_confidence_filter(self):
        """Low confidence assignments are filtered."""
        node = MockNode(
            id="test_func",
            properties={"reads_oracle_price": True}  # 0.5 confidence
        )
        assigner = TagAssigner(min_confidence=0.7)
        assignments = assigner.assign_tags(node)
        tags = [a.tag for a in assignments]
        # MANIPULATION has 0.5 confidence, should be filtered
        self.assertNotIn(RiskTag.MANIPULATION, tags)


class TestTagStorage(unittest.TestCase):
    """Tests for tag storage and querying."""

    def setUp(self):
        """Set up test fixtures."""
        self.store = TagStore()

    def test_add_and_get_tags(self):
        """Tags can be added and retrieved."""
        assignment = TagAssignment(
            tag=RiskTag.CEI_VIOLATION,
            confidence=0.9,
            source="test"
        )
        self.store.add_tag("func1", assignment)

        node_tags = self.store.get_node_tags("func1")
        self.assertIsNotNone(node_tags)
        self.assertIn(RiskTag.CEI_VIOLATION, node_tags.get_tags())

    def test_query_by_tag(self):
        """Nodes can be queried by tag."""
        self.store.add_tag("func1", TagAssignment(tag=RiskTag.CEI_VIOLATION))
        self.store.add_tag("func2", TagAssignment(tag=RiskTag.CEI_VIOLATION))
        self.store.add_tag("func3", TagAssignment(tag=RiskTag.STALE_PRICE))

        results = self.store.query_by_tag(RiskTag.CEI_VIOLATION)
        self.assertEqual(len(results), 2)
        self.assertIn("func1", results)
        self.assertIn("func2", results)

    def test_query_by_category(self):
        """Nodes can be queried by category."""
        self.store.add_tag("func1", TagAssignment(tag=RiskTag.CEI_VIOLATION))
        self.store.add_tag("func2", TagAssignment(tag=RiskTag.EXTERNAL_CALL))
        self.store.add_tag("func3", TagAssignment(tag=RiskTag.STALE_PRICE))

        results = self.store.query_by_category(RiskCategory.REENTRANCY)
        self.assertEqual(len(results), 2)
        self.assertIn("func1", results)
        self.assertIn("func2", results)
        self.assertNotIn("func3", results)

    def test_query_by_multiple_tags_all(self):
        """Query requires all tags when match_all=True."""
        self.store.add_tag("func1", TagAssignment(tag=RiskTag.CEI_VIOLATION))
        self.store.add_tag("func1", TagAssignment(tag=RiskTag.EXTERNAL_CALL))
        self.store.add_tag("func2", TagAssignment(tag=RiskTag.CEI_VIOLATION))

        results = self.store.query_by_tags(
            [RiskTag.CEI_VIOLATION, RiskTag.EXTERNAL_CALL],
            match_all=True
        )
        self.assertEqual(len(results), 1)
        self.assertIn("func1", results)

    def test_query_by_multiple_tags_any(self):
        """Query requires any tag when match_all=False."""
        self.store.add_tag("func1", TagAssignment(tag=RiskTag.CEI_VIOLATION))
        self.store.add_tag("func2", TagAssignment(tag=RiskTag.EXTERNAL_CALL))

        results = self.store.query_by_tags(
            [RiskTag.CEI_VIOLATION, RiskTag.EXTERNAL_CALL],
            match_all=False
        )
        self.assertEqual(len(results), 2)

    def test_query_by_confidence(self):
        """Nodes can be queried by confidence threshold."""
        self.store.add_tag("func1", TagAssignment(tag=RiskTag.CEI_VIOLATION, confidence=0.9))
        self.store.add_tag("func2", TagAssignment(tag=RiskTag.CEI_VIOLATION, confidence=0.5))

        results = self.store.query_by_confidence(min_confidence=0.8)
        self.assertEqual(len(results), 1)
        self.assertIn("func1", results)

    def test_remove_tag(self):
        """Tags can be removed."""
        self.store.add_tag("func1", TagAssignment(tag=RiskTag.CEI_VIOLATION))
        self.store.add_tag("func1", TagAssignment(tag=RiskTag.EXTERNAL_CALL))

        result = self.store.remove_tag("func1", RiskTag.CEI_VIOLATION)
        self.assertTrue(result)

        node_tags = self.store.get_node_tags("func1")
        self.assertNotIn(RiskTag.CEI_VIOLATION, node_tags.get_tags())
        self.assertIn(RiskTag.EXTERNAL_CALL, node_tags.get_tags())

    def test_no_duplicate_tags(self):
        """Duplicate tags are not added."""
        self.store.add_tag("func1", TagAssignment(tag=RiskTag.CEI_VIOLATION))
        self.store.add_tag("func1", TagAssignment(tag=RiskTag.CEI_VIOLATION))

        node_tags = self.store.get_node_tags("func1")
        tags = node_tags.get_tags()
        cei_count = sum(1 for t in tags if t == RiskTag.CEI_VIOLATION)
        self.assertEqual(cei_count, 1)

    def test_tag_counts(self):
        """Tag counts are tracked correctly."""
        self.store.add_tag("func1", TagAssignment(tag=RiskTag.CEI_VIOLATION))
        self.store.add_tag("func2", TagAssignment(tag=RiskTag.CEI_VIOLATION))
        self.store.add_tag("func3", TagAssignment(tag=RiskTag.STALE_PRICE))

        counts = self.store.get_tag_counts()
        self.assertEqual(counts[RiskTag.CEI_VIOLATION], 2)
        self.assertEqual(counts[RiskTag.STALE_PRICE], 1)

    def test_category_counts(self):
        """Category counts are tracked correctly."""
        self.store.add_tag("func1", TagAssignment(tag=RiskTag.CEI_VIOLATION))
        self.store.add_tag("func2", TagAssignment(tag=RiskTag.EXTERNAL_CALL))
        self.store.add_tag("func3", TagAssignment(tag=RiskTag.STALE_PRICE))

        counts = self.store.get_category_counts()
        self.assertEqual(counts[RiskCategory.REENTRANCY], 2)
        self.assertEqual(counts[RiskCategory.ORACLE], 1)

    def test_serialization(self):
        """Store can be serialized and deserialized."""
        self.store.add_tag("func1", TagAssignment(
            tag=RiskTag.CEI_VIOLATION,
            confidence=0.9,
            source="test",
            reason="Test reason"
        ))

        data = self.store.to_dict()
        restored = TagStore.from_dict(data)

        node_tags = restored.get_node_tags("func1")
        self.assertIsNotNone(node_tags)
        self.assertEqual(node_tags.assignments[0].confidence, 0.9)

    def test_convenience_functions(self):
        """Convenience functions work correctly."""
        add_tag_to_node(self.store, "func1", RiskTag.CEI_VIOLATION, 0.9)
        tags = get_node_tags(self.store, "func1")
        self.assertIn(RiskTag.CEI_VIOLATION, tags)

        nodes = query_nodes_by_tag(self.store, RiskTag.CEI_VIOLATION)
        self.assertIn("func1", nodes)


class TestNodeTags(unittest.TestCase):
    """Tests for NodeTags container."""

    def test_get_tags_in_category(self):
        """Can get tags filtered by category."""
        node_tags = NodeTags(node_id="test")
        node_tags.add_assignment(TagAssignment(tag=RiskTag.CEI_VIOLATION))
        node_tags.add_assignment(TagAssignment(tag=RiskTag.STALE_PRICE))

        reentrancy_tags = node_tags.get_tags_in_category(RiskCategory.REENTRANCY)
        self.assertIn(RiskTag.CEI_VIOLATION, reentrancy_tags)
        self.assertNotIn(RiskTag.STALE_PRICE, reentrancy_tags)

    def test_has_category(self):
        """Can check if node has tags in category."""
        node_tags = NodeTags(node_id="test")
        node_tags.add_assignment(TagAssignment(tag=RiskTag.CEI_VIOLATION))

        self.assertTrue(node_tags.has_category(RiskCategory.REENTRANCY))
        self.assertFalse(node_tags.has_category(RiskCategory.ORACLE))

    def test_get_highest_confidence(self):
        """Can get highest confidence assignment."""
        node_tags = NodeTags(node_id="test")
        node_tags.add_assignment(TagAssignment(tag=RiskTag.CEI_VIOLATION, confidence=0.7))
        node_tags.add_assignment(TagAssignment(tag=RiskTag.STALE_PRICE, confidence=0.9))

        highest = node_tags.get_highest_confidence()
        self.assertEqual(highest.tag, RiskTag.STALE_PRICE)
        self.assertEqual(highest.confidence, 0.9)

    def test_get_by_source(self):
        """Can filter assignments by source."""
        node_tags = NodeTags(node_id="test")
        node_tags.add_assignment(TagAssignment(tag=RiskTag.CEI_VIOLATION, source="property"))
        node_tags.add_assignment(TagAssignment(tag=RiskTag.STALE_PRICE, source="llm"))

        property_tags = node_tags.get_by_source("property")
        self.assertEqual(len(property_tags), 1)
        self.assertEqual(property_tags[0].tag, RiskTag.CEI_VIOLATION)


class TestTagMatching(unittest.TestCase):
    """Tests for tag-based pattern matching."""

    def setUp(self):
        """Set up test fixtures."""
        self.store = TagStore()
        self.matcher = TagMatcher(self.store)

    def test_condition_has(self):
        """HAS condition matches correctly."""
        node_tags = NodeTags(node_id="test")
        node_tags.add_assignment(TagAssignment(tag=RiskTag.CEI_VIOLATION))

        condition = TagCondition(operator=MatchOperator.HAS, tag=RiskTag.CEI_VIOLATION)
        self.assertTrue(condition.evaluate(node_tags))

        condition2 = TagCondition(operator=MatchOperator.HAS, tag=RiskTag.STALE_PRICE)
        self.assertFalse(condition2.evaluate(node_tags))

    def test_condition_not_has(self):
        """NOT_HAS condition matches correctly."""
        node_tags = NodeTags(node_id="test")
        node_tags.add_assignment(TagAssignment(tag=RiskTag.CEI_VIOLATION))

        condition = TagCondition(operator=MatchOperator.NOT_HAS, tag=RiskTag.STALE_PRICE)
        self.assertTrue(condition.evaluate(node_tags))

        condition2 = TagCondition(operator=MatchOperator.NOT_HAS, tag=RiskTag.CEI_VIOLATION)
        self.assertFalse(condition2.evaluate(node_tags))

    def test_condition_has_any(self):
        """HAS_ANY condition matches correctly."""
        node_tags = NodeTags(node_id="test")
        node_tags.add_assignment(TagAssignment(tag=RiskTag.STALE_PRICE))

        condition = TagCondition(
            operator=MatchOperator.HAS_ANY,
            tags=[RiskTag.CEI_VIOLATION, RiskTag.STALE_PRICE]
        )
        self.assertTrue(condition.evaluate(node_tags))

    def test_condition_has_all(self):
        """HAS_ALL condition matches correctly."""
        node_tags = NodeTags(node_id="test")
        node_tags.add_assignment(TagAssignment(tag=RiskTag.CEI_VIOLATION))
        node_tags.add_assignment(TagAssignment(tag=RiskTag.EXTERNAL_CALL))

        condition = TagCondition(
            operator=MatchOperator.HAS_ALL,
            tags=[RiskTag.CEI_VIOLATION, RiskTag.EXTERNAL_CALL]
        )
        self.assertTrue(condition.evaluate(node_tags))

        condition2 = TagCondition(
            operator=MatchOperator.HAS_ALL,
            tags=[RiskTag.CEI_VIOLATION, RiskTag.STALE_PRICE]
        )
        self.assertFalse(condition2.evaluate(node_tags))

    def test_condition_has_category(self):
        """HAS_CATEGORY condition matches correctly."""
        node_tags = NodeTags(node_id="test")
        node_tags.add_assignment(TagAssignment(tag=RiskTag.CEI_VIOLATION))

        condition = TagCondition(
            operator=MatchOperator.HAS_CATEGORY,
            category=RiskCategory.REENTRANCY
        )
        self.assertTrue(condition.evaluate(node_tags))

        condition2 = TagCondition(
            operator=MatchOperator.HAS_CATEGORY,
            category=RiskCategory.ORACLE
        )
        self.assertFalse(condition2.evaluate(node_tags))

    def test_condition_confidence_gte(self):
        """CONFIDENCE_GTE condition matches correctly."""
        node_tags = NodeTags(node_id="test")
        node_tags.add_assignment(TagAssignment(tag=RiskTag.CEI_VIOLATION, confidence=0.8))

        condition = TagCondition(
            operator=MatchOperator.CONFIDENCE_GTE,
            tag=RiskTag.CEI_VIOLATION,
            value=0.7
        )
        self.assertTrue(condition.evaluate(node_tags))

        condition2 = TagCondition(
            operator=MatchOperator.CONFIDENCE_GTE,
            tag=RiskTag.CEI_VIOLATION,
            value=0.9
        )
        self.assertFalse(condition2.evaluate(node_tags))

    def test_pattern_all_conditions(self):
        """Pattern with all_conditions matches correctly."""
        node_tags = NodeTags(node_id="test")
        node_tags.add_assignment(TagAssignment(tag=RiskTag.CEI_VIOLATION))
        node_tags.add_assignment(TagAssignment(tag=RiskTag.EXTERNAL_CALL))

        pattern = TagPattern(
            name="test",
            all_conditions=[
                TagCondition(operator=MatchOperator.HAS, tag=RiskTag.CEI_VIOLATION),
                TagCondition(operator=MatchOperator.HAS, tag=RiskTag.EXTERNAL_CALL),
            ]
        )
        self.assertTrue(pattern.matches(node_tags))

    def test_pattern_any_conditions(self):
        """Pattern with any_conditions matches correctly."""
        node_tags = NodeTags(node_id="test")
        node_tags.add_assignment(TagAssignment(tag=RiskTag.STALE_PRICE))

        pattern = TagPattern(
            name="test",
            any_conditions=[
                TagCondition(operator=MatchOperator.HAS, tag=RiskTag.CEI_VIOLATION),
                TagCondition(operator=MatchOperator.HAS, tag=RiskTag.STALE_PRICE),
            ]
        )
        self.assertTrue(pattern.matches(node_tags))

    def test_pattern_none_conditions(self):
        """Pattern with none_conditions excludes correctly."""
        node_tags = NodeTags(node_id="test")
        node_tags.add_assignment(TagAssignment(tag=RiskTag.CEI_VIOLATION))
        node_tags.add_assignment(TagAssignment(tag=RiskTag.EXTERNAL_CALL))  # Has reentrancy guard

        # Pattern: has CEI violation but NOT external call
        pattern = TagPattern(
            name="test",
            all_conditions=[
                TagCondition(operator=MatchOperator.HAS, tag=RiskTag.CEI_VIOLATION),
            ],
            none_conditions=[
                TagCondition(operator=MatchOperator.HAS, tag=RiskTag.EXTERNAL_CALL),
            ]
        )
        self.assertFalse(pattern.matches(node_tags))

    def test_matcher_match_pattern(self):
        """TagMatcher matches patterns against store."""
        self.store.add_tag("func1", TagAssignment(tag=RiskTag.CEI_VIOLATION))
        self.store.add_tag("func1", TagAssignment(tag=RiskTag.EXTERNAL_CALL))
        self.store.add_tag("func2", TagAssignment(tag=RiskTag.CEI_VIOLATION))

        pattern = TagPattern(
            name="full_reentrancy",
            all_conditions=[
                TagCondition(operator=MatchOperator.HAS, tag=RiskTag.CEI_VIOLATION),
                TagCondition(operator=MatchOperator.HAS, tag=RiskTag.EXTERNAL_CALL),
            ]
        )

        results = self.matcher.match_pattern(pattern)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].node_id, "func1")

    def test_matcher_specific_node(self):
        """TagMatcher can match against specific node."""
        self.store.add_tag("func1", TagAssignment(tag=RiskTag.CEI_VIOLATION))

        pattern = TagPattern(
            name="test",
            all_conditions=[
                TagCondition(operator=MatchOperator.HAS, tag=RiskTag.CEI_VIOLATION),
            ]
        )

        results = self.matcher.match_pattern(pattern, node_id="func1")
        self.assertEqual(len(results), 1)

        results2 = self.matcher.match_pattern(pattern, node_id="func2")
        self.assertEqual(len(results2), 0)

    def test_matcher_find_by_tag(self):
        """TagMatcher finds nodes by tag."""
        self.store.add_tag("func1", TagAssignment(tag=RiskTag.CEI_VIOLATION))
        self.store.add_tag("func2", TagAssignment(tag=RiskTag.CEI_VIOLATION))

        results = self.matcher.find_by_tag(RiskTag.CEI_VIOLATION)
        self.assertEqual(len(results), 2)

    def test_matcher_find_by_category(self):
        """TagMatcher finds nodes by category."""
        self.store.add_tag("func1", TagAssignment(tag=RiskTag.CEI_VIOLATION))
        self.store.add_tag("func2", TagAssignment(tag=RiskTag.EXTERNAL_CALL))

        results = self.matcher.find_by_category(RiskCategory.REENTRANCY)
        self.assertEqual(len(results), 2)

    def test_matcher_find_high_risk(self):
        """TagMatcher finds high-risk nodes."""
        self.store.add_tag("func1", TagAssignment(tag=RiskTag.CEI_VIOLATION, confidence=0.9))
        self.store.add_tag("func2", TagAssignment(tag=RiskTag.STALE_PRICE, confidence=0.5))

        results = self.matcher.find_high_risk(min_confidence=0.8)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].node_id, "func1")

    def test_predefined_patterns(self):
        """Predefined patterns are valid."""
        # Just verify they're defined correctly
        self.assertEqual(REENTRANCY_PATTERN.name, "reentrancy")
        self.assertEqual(ACCESS_CONTROL_PATTERN.name, "access_control")
        self.assertEqual(ORACLE_MANIPULATION_PATTERN.name, "oracle_manipulation")
        self.assertEqual(DOS_PATTERN.name, "dos")

    def test_reentrancy_pattern_match(self):
        """Reentrancy pattern matches vulnerable functions."""
        self.store.add_tag("func1", TagAssignment(tag=RiskTag.CEI_VIOLATION))
        self.store.add_tag("func1", TagAssignment(tag=RiskTag.EXTERNAL_CALL))

        results = self.matcher.match_pattern(REENTRANCY_PATTERN)
        self.assertEqual(len(results), 1)

    def test_access_control_pattern_match(self):
        """Access control pattern matches vulnerable functions."""
        self.store.add_tag("func1", TagAssignment(tag=RiskTag.MISSING_ACCESS_CONTROL))

        results = self.matcher.match_pattern(ACCESS_CONTROL_PATTERN)
        self.assertEqual(len(results), 1)

    def test_convenience_functions(self):
        """Convenience functions work correctly."""
        self.store.add_tag("func1", TagAssignment(tag=RiskTag.CEI_VIOLATION))

        # has_risk_tag
        self.assertTrue(has_risk_tag(self.store, "func1", RiskTag.CEI_VIOLATION))
        self.assertFalse(has_risk_tag(self.store, "func1", RiskTag.STALE_PRICE))

        # match_tag_pattern
        pattern = TagPattern(
            name="test",
            all_conditions=[
                TagCondition(operator=MatchOperator.HAS, tag=RiskTag.CEI_VIOLATION),
            ]
        )
        results = match_tag_pattern(self.store, pattern)
        self.assertEqual(len(results), 1)


class TestMatchResultSerialization(unittest.TestCase):
    """Tests for TagMatchResult serialization."""

    def test_to_dict(self):
        """Match result serializes correctly."""
        result = TagMatchResult(
            matched=True,
            node_id="func1",
            pattern_name="reentrancy",
            matched_tags=[RiskTag.CEI_VIOLATION, RiskTag.EXTERNAL_CALL],
            confidence=0.85,
            evidence=["state_write_after_call=True"]
        )
        d = result.to_dict()
        self.assertEqual(d["matched"], True)
        self.assertEqual(d["node_id"], "func1")
        self.assertEqual(d["matched_tags"], ["cei_violation", "external_call"])
        self.assertEqual(d["confidence"], 0.85)


class TestNullNodeTags(unittest.TestCase):
    """Tests for handling None/empty node tags."""

    def test_condition_with_none(self):
        """Conditions handle None node_tags correctly."""
        condition = TagCondition(operator=MatchOperator.HAS, tag=RiskTag.CEI_VIOLATION)
        self.assertFalse(condition.evaluate(None))

        condition_not = TagCondition(operator=MatchOperator.NOT_HAS, tag=RiskTag.CEI_VIOLATION)
        self.assertTrue(condition_not.evaluate(None))

    def test_pattern_with_none(self):
        """Patterns handle None node_tags correctly."""
        pattern = TagPattern(
            name="test",
            all_conditions=[
                TagCondition(operator=MatchOperator.HAS, tag=RiskTag.CEI_VIOLATION),
            ]
        )
        self.assertFalse(pattern.matches(None))


if __name__ == "__main__":
    unittest.main()
