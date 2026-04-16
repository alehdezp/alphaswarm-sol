"""Tests for Phase 10: Cross-Contract Intelligence.

Tests cover:
- P10-T1: Similarity Index
- P10-T2: Exploit Database
- P10-T3: Exploit Similarity Detection
"""

import unittest
from unittest.mock import MagicMock

from alphaswarm_sol.kg.schema import Node, KnowledgeGraph
from alphaswarm_sol.kg.similarity import (
    SimilarityType,
    SimilarFunction,
    StructuralFingerprint,
    SimilarityIndex,
    compute_structural_fingerprint,
    compute_structural_hash,
    compute_property_similarity,
    compute_operation_similarity,
    compute_signature_similarity,
)
from alphaswarm_sol.data.exploits import (
    KnownExploit,
    ExploitCategory,
    EXPLOIT_DATABASE,
    get_exploits_by_category,
    get_exploits_by_signature,
    get_exploit_by_id,
    get_all_signatures,
    get_exploits_by_property,
    get_exploits_requiring_operation,
)
from alphaswarm_sol.kg.exploit_detection import (
    ExploitWarning,
    DetectionResult,
    ExploitDetector,
    check_exploit_similarity,
    scan_graph_for_exploits,
)


class TestStructuralFingerprint(unittest.TestCase):
    """Tests for structural fingerprinting."""

    def test_fingerprint_creation(self):
        """Test creating a structural fingerprint."""
        fp = StructuralFingerprint(
            visibility="public",
            has_parameters=True,
            parameter_count=2,
            has_return=True,
            has_modifiers=True,
            writes_state=True,
            reads_state=True,
            has_loops=False,
            has_conditionals=True,
            has_external_calls=True,
            has_internal_calls=False,
            operation_count=5,
        )
        self.assertEqual(fp.visibility, "public")
        self.assertEqual(fp.parameter_count, 2)
        self.assertTrue(fp.has_external_calls)

    def test_fingerprint_to_hash(self):
        """Test fingerprint hashing."""
        fp1 = StructuralFingerprint(
            visibility="public",
            has_parameters=True,
            parameter_count=2,
            has_return=True,
            has_modifiers=False,
            writes_state=True,
            reads_state=True,
            has_loops=False,
            has_conditionals=True,
            has_external_calls=True,
            has_internal_calls=False,
            operation_count=5,
        )
        fp2 = StructuralFingerprint(
            visibility="public",
            has_parameters=True,
            parameter_count=2,
            has_return=True,
            has_modifiers=False,
            writes_state=True,
            reads_state=True,
            has_loops=False,
            has_conditionals=True,
            has_external_calls=True,
            has_internal_calls=False,
            operation_count=5,
        )
        # Same fingerprints should have same hash
        self.assertEqual(fp1.to_hash(), fp2.to_hash())

    def test_different_fingerprints_different_hash(self):
        """Test that different fingerprints have different hashes."""
        fp1 = StructuralFingerprint(
            visibility="public",
            has_parameters=True,
            parameter_count=2,
            has_return=True,
            has_modifiers=False,
            writes_state=True,
            reads_state=True,
            has_loops=False,
            has_conditionals=True,
            has_external_calls=True,
            has_internal_calls=False,
            operation_count=5,
        )
        fp2 = StructuralFingerprint(
            visibility="internal",  # Different
            has_parameters=True,
            parameter_count=2,
            has_return=True,
            has_modifiers=False,
            writes_state=True,
            reads_state=True,
            has_loops=False,
            has_conditionals=True,
            has_external_calls=True,
            has_internal_calls=False,
            operation_count=5,
        )
        self.assertNotEqual(fp1.to_hash(), fp2.to_hash())


class TestComputeFunctions(unittest.TestCase):
    """Tests for similarity computation functions."""

    def create_function_node(
        self,
        fn_id: str,
        label: str,
        visibility: str = "public",
        has_access_gate: bool = False,
        writes_state: bool = False,
        has_external_calls: bool = False,
        semantic_ops: list = None,
        behavioral_signature: str = "",
    ) -> Node:
        """Create a function node for testing."""
        return Node(
            id=fn_id,
            type="Function",
            label=label,
            properties={
                "visibility": visibility,
                "has_access_gate": has_access_gate,
                "writes_state": writes_state,
                "reads_state": False,
                "has_external_calls": has_external_calls,
                "param_types": [],
                "return_types": [],
                "modifiers": [],
                "semantic_ops": semantic_ops or [],
                "behavioral_signature": behavioral_signature,
            },
        )

    def test_compute_structural_fingerprint(self):
        """Test computing fingerprint from node."""
        fn = self.create_function_node(
            "fn1", "withdraw",
            visibility="external",
            writes_state=True,
            has_external_calls=True,
        )
        fp = compute_structural_fingerprint(fn)
        self.assertEqual(fp.visibility, "external")
        self.assertTrue(fp.writes_state)
        self.assertTrue(fp.has_external_calls)

    def test_compute_structural_hash(self):
        """Test computing hash from node."""
        fn = self.create_function_node("fn1", "withdraw")
        hash_val = compute_structural_hash(fn)
        self.assertEqual(len(hash_val), 16)  # 16-char hex string

    def test_property_similarity_identical(self):
        """Test property similarity for identical functions."""
        fn1 = self.create_function_node(
            "fn1", "withdraw",
            has_access_gate=True,
            writes_state=True,
        )
        fn2 = self.create_function_node(
            "fn2", "withdrawFunds",
            has_access_gate=True,
            writes_state=True,
        )
        similarity = compute_property_similarity(fn1, fn2)
        self.assertEqual(similarity, 1.0)

    def test_property_similarity_different(self):
        """Test property similarity for different functions."""
        fn1 = self.create_function_node(
            "fn1", "withdraw",
            has_access_gate=True,
            writes_state=True,
        )
        fn2 = self.create_function_node(
            "fn2", "view_balance",
            has_access_gate=False,
            writes_state=False,
        )
        similarity = compute_property_similarity(fn1, fn2)
        self.assertLess(similarity, 1.0)

    def test_operation_similarity_identical(self):
        """Test operation similarity for identical ops."""
        fn1 = self.create_function_node(
            "fn1", "withdraw",
            semantic_ops=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        )
        fn2 = self.create_function_node(
            "fn2", "withdrawFunds",
            semantic_ops=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        )
        similarity = compute_operation_similarity(fn1, fn2)
        self.assertEqual(similarity, 1.0)

    def test_operation_similarity_partial(self):
        """Test operation similarity with partial overlap."""
        fn1 = self.create_function_node(
            "fn1", "withdraw",
            semantic_ops=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        )
        fn2 = self.create_function_node(
            "fn2", "send",
            semantic_ops=["TRANSFERS_VALUE_OUT", "CALLS_EXTERNAL"],
        )
        similarity = compute_operation_similarity(fn1, fn2)
        # 1 overlap, 3 union = 1/3
        self.assertAlmostEqual(similarity, 1/3, places=2)

    def test_signature_similarity_identical(self):
        """Test signature similarity for identical signatures."""
        sig1 = "R:bal→X:out→W:bal"
        sig2 = "R:bal→X:out→W:bal"
        similarity = compute_signature_similarity(sig1, sig2)
        self.assertEqual(similarity, 1.0)

    def test_signature_similarity_partial(self):
        """Test signature similarity for partial match."""
        sig1 = "R:bal→X:out→W:bal"
        sig2 = "R:bal→W:bal→X:out"  # CEI pattern vs vulnerable
        similarity = compute_signature_similarity(sig1, sig2)
        # Should have some similarity but not 1.0
        self.assertGreater(similarity, 0.5)
        self.assertLess(similarity, 1.0)

    def test_signature_similarity_empty(self):
        """Test signature similarity with empty signatures."""
        self.assertEqual(compute_signature_similarity("", "R:bal"), 0.0)
        self.assertEqual(compute_signature_similarity("R:bal", ""), 0.0)
        self.assertEqual(compute_signature_similarity("", ""), 0.0)


class TestSimilarityIndex(unittest.TestCase):
    """Tests for the SimilarityIndex class."""

    def create_function_node(
        self,
        fn_id: str,
        label: str,
        visibility: str = "public",
        behavioral_signature: str = "",
        semantic_ops: list = None,
        **kwargs,
    ) -> Node:
        """Create a function node for testing."""
        props = {
            "visibility": visibility,
            "behavioral_signature": behavioral_signature,
            "semantic_ops": semantic_ops or [],
            "param_types": [],
            "return_types": [],
            "modifiers": [],
            **kwargs,
        }
        return Node(id=fn_id, type="Function", label=label, properties=props)

    def test_index_function(self):
        """Test indexing a single function."""
        index = SimilarityIndex()
        fn = self.create_function_node("fn1", "withdraw")
        index.index_function(fn)
        self.assertEqual(len(index._functions), 1)

    def test_index_multiple_functions(self):
        """Test indexing multiple functions."""
        index = SimilarityIndex()
        fn1 = self.create_function_node(
            "fn1", "withdraw",
            behavioral_signature="R:bal→X:out→W:bal",
        )
        fn2 = self.create_function_node(
            "fn2", "withdrawFunds",
            behavioral_signature="R:bal→X:out→W:bal",
        )
        index.index_function(fn1)
        index.index_function(fn2)
        self.assertEqual(len(index._functions), 2)
        # Should be grouped by same signature
        self.assertEqual(len(index.behavioral_index["R:bal→X:out→W:bal"]), 2)

    def test_find_similar_structural(self):
        """Test finding structurally similar functions."""
        index = SimilarityIndex()
        fn1 = self.create_function_node("fn1", "withdraw")
        fn2 = self.create_function_node("fn2", "withdrawFunds")  # Same structure
        fn3 = self.create_function_node(
            "fn3", "transfer",
            visibility="internal",
        )  # Different structure

        index.index_function(fn1)
        index.index_function(fn2)
        index.index_function(fn3)

        similar = index.find_similar(
            fn1,
            similarity_types=[SimilarityType.STRUCTURAL],
        )
        # fn2 should be similar (same visibility, same default props)
        self.assertGreater(len(similar), 0)

    def test_find_similar_behavioral(self):
        """Test finding behaviorally similar functions."""
        index = SimilarityIndex()
        fn1 = self.create_function_node(
            "fn1", "withdraw",
            behavioral_signature="R:bal→X:out→W:bal",
        )
        fn2 = self.create_function_node(
            "fn2", "withdrawFunds",
            behavioral_signature="R:bal→X:out→W:bal",  # Same
        )
        fn3 = self.create_function_node(
            "fn3", "deposit",
            behavioral_signature="V:input→W:bal",  # Different
        )

        index.index_function(fn1)
        index.index_function(fn2)
        index.index_function(fn3)

        similar = index.find_similar(
            fn1,
            similarity_types=[SimilarityType.BEHAVIORAL],
        )
        # Should find fn2 (same signature)
        found_ids = [s.function.id for s in similar]
        self.assertIn("fn2", found_ids)
        self.assertNotIn("fn3", found_ids)

    def test_find_by_signature(self):
        """Test finding functions by signature."""
        index = SimilarityIndex()
        fn1 = self.create_function_node(
            "fn1", "withdraw",
            behavioral_signature="R:bal→X:out→W:bal",
        )
        fn2 = self.create_function_node(
            "fn2", "withdrawFunds",
            behavioral_signature="R:bal→X:out→W:bal",
        )
        index.index_function(fn1)
        index.index_function(fn2)

        matches = index.find_by_signature("R:bal→X:out→W:bal")
        self.assertEqual(len(matches), 2)

    def test_get_statistics(self):
        """Test getting index statistics."""
        index = SimilarityIndex()
        fn1 = self.create_function_node(
            "fn1", "withdraw",
            behavioral_signature="R:bal→X:out→W:bal",
        )
        fn2 = self.create_function_node(
            "fn2", "withdrawFunds",
            behavioral_signature="R:bal→X:out→W:bal",
        )
        fn3 = self.create_function_node(
            "fn3", "deposit",
            behavioral_signature="V:input→W:bal",
        )
        index.index_function(fn1)
        index.index_function(fn2)
        index.index_function(fn3)

        stats = index.get_statistics()
        self.assertEqual(stats["total_functions"], 3)
        self.assertEqual(stats["unique_signatures"], 2)
        self.assertEqual(stats["largest_behavioral_group"], 2)

    def test_clear(self):
        """Test clearing the index."""
        index = SimilarityIndex()
        fn = self.create_function_node("fn1", "withdraw")
        index.index_function(fn)
        self.assertEqual(len(index._functions), 1)

        index.clear()
        self.assertEqual(len(index._functions), 0)
        self.assertEqual(len(index.structural_index), 0)
        self.assertEqual(len(index.behavioral_index), 0)


class TestExploitDatabase(unittest.TestCase):
    """Tests for the exploit database."""

    def test_database_not_empty(self):
        """Test that the database is populated."""
        self.assertGreater(len(EXPLOIT_DATABASE), 0)

    def test_dao_hack_present(self):
        """Test that the DAO hack is in the database."""
        dao = get_exploit_by_id("dao-hack-2016")
        self.assertIsNotNone(dao)
        self.assertEqual(dao.name, "The DAO Reentrancy Attack")
        self.assertEqual(dao.category, ExploitCategory.REENTRANCY)
        self.assertIn("READS_USER_BALANCE", dao.required_operations)

    def test_get_by_category(self):
        """Test filtering by category."""
        reentrancy = get_exploits_by_category(ExploitCategory.REENTRANCY)
        self.assertGreater(len(reentrancy), 0)
        for exploit in reentrancy:
            self.assertEqual(exploit.category, ExploitCategory.REENTRANCY)

    def test_get_by_signature(self):
        """Test filtering by signature."""
        sig = "R:bal→X:out→W:bal"
        matches = get_exploits_by_signature(sig)
        self.assertGreater(len(matches), 0)
        for exploit in matches:
            self.assertEqual(exploit.affected_pattern, sig)

    def test_get_all_signatures(self):
        """Test getting all unique signatures."""
        signatures = get_all_signatures()
        self.assertGreater(len(signatures), 0)
        # Should be unique
        self.assertEqual(len(signatures), len(set(signatures)))

    def test_get_by_property(self):
        """Test filtering by property."""
        matches = get_exploits_by_property("has_reentrancy_guard", False)
        self.assertGreater(len(matches), 0)

    def test_get_by_operation(self):
        """Test filtering by required operation."""
        matches = get_exploits_requiring_operation("READS_USER_BALANCE")
        self.assertGreater(len(matches), 0)
        for exploit in matches:
            self.assertIn("READS_USER_BALANCE", exploit.required_operations)

    def test_exploit_serialization(self):
        """Test exploit to_dict and from_dict."""
        exploit = get_exploit_by_id("dao-hack-2016")
        data = exploit.to_dict()
        restored = KnownExploit.from_dict(data)
        self.assertEqual(restored.id, exploit.id)
        self.assertEqual(restored.name, exploit.name)
        self.assertEqual(restored.category, exploit.category)


class TestExploitDetector(unittest.TestCase):
    """Tests for exploit detection."""

    def create_function_node(
        self,
        fn_id: str,
        label: str,
        visibility: str = "public",
        behavioral_signature: str = "",
        semantic_ops: list = None,
        **kwargs,
    ) -> Node:
        """Create a function node for testing."""
        props = {
            "visibility": visibility,
            "behavioral_signature": behavioral_signature,
            "semantic_ops": semantic_ops or [],
            **kwargs,
        }
        return Node(id=fn_id, type="Function", label=label, properties=props)

    def test_detect_exact_signature_match(self):
        """Test detection of exact signature match."""
        fn = self.create_function_node(
            "fn1", "withdraw",
            behavioral_signature="R:bal→X:out→W:bal",
            semantic_ops=[
                "READS_USER_BALANCE",
                "TRANSFERS_VALUE_OUT",
                "WRITES_USER_BALANCE",
            ],
            has_reentrancy_guard=False,
        )

        detector = ExploitDetector()
        warnings = detector.check_function(fn)

        self.assertGreater(len(warnings), 0)
        # Should match DAO hack
        dao_match = next(
            (w for w in warnings if w.similar_exploit.id == "dao-hack-2016"),
            None
        )
        self.assertIsNotNone(dao_match)
        self.assertGreater(dao_match.confidence, 0.9)  # High confidence

    def test_detect_operations_match(self):
        """Test detection based on required operations."""
        fn = self.create_function_node(
            "fn1", "withdraw",
            behavioral_signature="",  # No signature
            semantic_ops=[
                "READS_USER_BALANCE",
                "TRANSFERS_VALUE_OUT",
                "WRITES_USER_BALANCE",
            ],
        )

        detector = ExploitDetector()
        warnings = detector.check_function(fn)

        # Should find match based on operations
        self.assertGreater(len(warnings), 0)

    def test_detect_property_match(self):
        """Test detection based on property patterns."""
        fn = self.create_function_node(
            "fn1", "initialize",
            visibility="public",
            is_initializer_like=True,
            has_access_gate=False,
            semantic_ops=["INITIALIZES_STATE", "MODIFIES_OWNER"],
        )

        detector = ExploitDetector()
        warnings = detector.check_function(fn)

        # Should match initialization exploits
        init_matches = [
            w for w in warnings
            if w.similar_exploit.category == ExploitCategory.INITIALIZATION
        ]
        self.assertGreater(len(init_matches), 0)

    def test_no_match_safe_function(self):
        """Test that safe functions with guards have reduced confidence for reentrancy."""
        fn = self.create_function_node(
            "fn1", "safeWithdraw",
            visibility="public",
            behavioral_signature="R:bal→W:bal→X:out",  # CEI pattern
            semantic_ops=["READS_USER_BALANCE", "WRITES_USER_BALANCE", "TRANSFERS_VALUE_OUT"],
            has_reentrancy_guard=True,
            has_access_gate=True,
        )

        # Use high min_confidence to filter weak matches
        detector = ExploitDetector(min_confidence=0.85)
        warnings = detector.check_function(fn)

        # Should have no reentrancy warnings with high confidence
        # (the reentrancy guard should significantly reduce confidence)
        reentrancy_warnings = [
            w for w in warnings
            if w.similar_exploit.category == ExploitCategory.REENTRANCY
            and w.confidence >= 0.9
        ]
        self.assertEqual(len(reentrancy_warnings), 0)

    def test_check_multiple_functions(self):
        """Test checking multiple functions."""
        fn1 = self.create_function_node(
            "fn1", "vulnerableWithdraw",
            behavioral_signature="R:bal→X:out→W:bal",
        )
        fn2 = self.create_function_node(
            "fn2", "safeFunction",
            behavioral_signature="",
        )

        detector = ExploitDetector(min_confidence=0.7)
        results = detector.check_functions([fn1, fn2])

        # Should find at least one result (for fn1)
        fn1_result = next(
            (r for r in results if r.function.id == "fn1"),
            None
        )
        self.assertIsNotNone(fn1_result)

    def test_convenience_function(self):
        """Test the check_exploit_similarity convenience function."""
        fn = self.create_function_node(
            "fn1", "withdraw",
            behavioral_signature="R:bal→X:out→W:bal",
        )

        warning = check_exploit_similarity(fn, min_confidence=0.7)
        self.assertIsNotNone(warning)

    def test_warning_to_dict(self):
        """Test ExploitWarning serialization."""
        fn = self.create_function_node("fn1", "withdraw")
        exploit = get_exploit_by_id("dao-hack-2016")

        warning = ExploitWarning(
            function=fn,
            similar_exploit=exploit,
            match_type="exact_signature",
            confidence=0.95,
            matched_criteria=["exact_signature:R:bal→X:out→W:bal"],
            recommendation=exploit.remediation,
        )

        data = warning.to_dict()
        self.assertEqual(data["function_id"], "fn1")
        self.assertEqual(data["exploit_id"], "dao-hack-2016")
        self.assertEqual(data["confidence"], 0.95)

    def test_detection_result(self):
        """Test DetectionResult methods."""
        fn = self.create_function_node("fn1", "withdraw")
        exploit = get_exploit_by_id("dao-hack-2016")

        warning = ExploitWarning(
            function=fn,
            similar_exploit=exploit,
            match_type="exact_signature",
            confidence=0.95,
            matched_criteria=[],
            recommendation="",
        )

        result = DetectionResult(
            function=fn,
            warnings=[warning],
            highest_confidence=0.95,
            categories_matched={ExploitCategory.REENTRANCY},
        )

        self.assertTrue(result.has_warnings())
        critical = result.get_critical_warnings(0.9)
        self.assertEqual(len(critical), 1)

        data = result.to_dict()
        self.assertEqual(data["warning_count"], 1)

    def test_category_summary(self):
        """Test category summary from results."""
        fn1 = self.create_function_node(
            "fn1", "withdraw",
            behavioral_signature="R:bal→X:out→W:bal",
        )
        fn2 = self.create_function_node(
            "fn2", "initialize",
            is_initializer_like=True,
            has_access_gate=False,
        )

        detector = ExploitDetector(min_confidence=0.5)
        results = detector.check_functions([fn1, fn2])
        summary = detector.get_category_summary(results)

        # Should have reentrancy category
        self.assertIn(ExploitCategory.REENTRANCY, summary)


class TestScanGraphForExploits(unittest.TestCase):
    """Tests for scanning entire graphs."""

    def test_scan_graph(self):
        """Test scanning an entire graph."""
        graph = KnowledgeGraph()

        # Add a vulnerable function
        fn = Node(
            id="fn1",
            type="Function",
            label="withdraw",
            properties={
                "visibility": "public",
                "behavioral_signature": "R:bal→X:out→W:bal",
                "semantic_ops": [
                    "READS_USER_BALANCE",
                    "TRANSFERS_VALUE_OUT",
                    "WRITES_USER_BALANCE",
                ],
                "has_reentrancy_guard": False,
            },
        )
        graph.add_node(fn)

        results = scan_graph_for_exploits(graph, min_confidence=0.7)
        self.assertGreater(len(results), 0)

    def test_scan_graph_with_category_filter(self):
        """Test scanning with category filter."""
        graph = KnowledgeGraph()

        fn = Node(
            id="fn1",
            type="Function",
            label="withdraw",
            properties={
                "visibility": "public",
                "behavioral_signature": "R:bal→X:out→W:bal",
            },
        )
        graph.add_node(fn)

        # Only check reentrancy
        results = scan_graph_for_exploits(
            graph,
            min_confidence=0.7,
            categories=[ExploitCategory.REENTRANCY],
        )

        for result in results:
            for cat in result.categories_matched:
                self.assertEqual(cat, ExploitCategory.REENTRANCY)


class TestSimilarFunction(unittest.TestCase):
    """Tests for SimilarFunction dataclass."""

    def test_similar_function_to_dict(self):
        """Test SimilarFunction serialization."""
        fn = Node(
            id="fn1",
            type="Function",
            label="withdraw",
            properties={},
        )

        similar = SimilarFunction(
            function=fn,
            similarity_type=SimilarityType.BEHAVIORAL,
            score=0.95,
            details={"signature": "R:bal→X:out→W:bal"},
        )

        data = similar.to_dict()
        self.assertEqual(data["function_id"], "fn1")
        self.assertEqual(data["similarity_type"], "behavioral")
        self.assertEqual(data["score"], 0.95)


if __name__ == "__main__":
    unittest.main()
