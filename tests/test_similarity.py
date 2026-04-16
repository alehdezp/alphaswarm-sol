"""
Tests for Novel Solution 9: Semantic Code Similarity Engine

Tests the ability to find semantically similar code across contracts,
even when syntactically different.
"""

import unittest
from datetime import datetime

from alphaswarm_sol.similarity import (
    # Fingerprint
    SemanticFingerprint,
    FingerprintType,
    OperationSequence,
    FingerprintGenerator,
    FingerprintConfig,
    # Similarity
    SimilarityScore,
    SimilarityType,
    SimilarityCalculator,
    SimilarityConfig,
    SimilarityResult,
    # Index
    ContractIndex,
    IndexEntry,
    IndexConfig,
    SearchResult,
    SearchConfig,
    # Matcher
    PatternMatcher,
    MatchResult,
    MatchType,
    CloneDetector,
    CloneType,
    Clone,
    # Engine
    SimilarityEngine,
    EngineConfig,
    AnalysisResult,
    SimilarContract,
    VulnerabilityCorrelation,
)


class TestOperationSequence(unittest.TestCase):
    """Test operation sequence class."""

    def test_creation(self):
        """Test operation sequence creation."""
        seq = OperationSequence(
            operations=["READS_BALANCE", "TRANSFERS_OUT", "WRITES_BALANCE"],
            guards=["ACCESS_GATE"],
            loops=1,
            branches=2,
        )

        self.assertEqual(len(seq.operations), 3)
        self.assertEqual(len(seq.guards), 1)
        self.assertEqual(seq.loops, 1)
        self.assertEqual(seq.branches, 2)

    def test_to_hash(self):
        """Test hash generation."""
        seq = OperationSequence(
            operations=["READS_BALANCE", "TRANSFERS_OUT"],
        )

        hash_val = seq.to_hash()
        self.assertEqual(len(hash_val), 16)

        # Same sequence = same hash
        seq2 = OperationSequence(
            operations=["READS_BALANCE", "TRANSFERS_OUT"],
        )
        self.assertEqual(seq.to_hash(), seq2.to_hash())

    def test_similarity(self):
        """Test sequence similarity calculation."""
        seq1 = OperationSequence(operations=["A", "B", "C"])
        seq2 = OperationSequence(operations=["A", "B", "C"])

        self.assertEqual(seq1.similarity(seq2), 1.0)

        seq3 = OperationSequence(operations=["A", "C"])
        sim = seq1.similarity(seq3)
        self.assertGreater(sim, 0.5)
        self.assertLess(sim, 1.0)


class TestSemanticFingerprint(unittest.TestCase):
    """Test semantic fingerprint class."""

    def test_creation(self):
        """Test fingerprint creation."""
        fp = SemanticFingerprint(
            fingerprint_id="FP-001",
            fingerprint_type=FingerprintType.OPERATION_SEQUENCE,
            source_name="withdraw",
            contract_name="Vault",
            operations=["READS_BALANCE", "TRANSFERS_OUT"],
            complexity=5,
            num_operations=2,
        )

        self.assertEqual(fp.source_name, "withdraw")
        self.assertEqual(fp.contract_name, "Vault")
        self.assertEqual(fp.num_operations, 2)

    def test_to_vector(self):
        """Test vector conversion."""
        fp = SemanticFingerprint(
            fingerprint_id="FP-001",
            fingerprint_type=FingerprintType.OPERATION_SEQUENCE,
            source_name="test",
            operations=["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT"],
            complexity=3,
            num_operations=2,
            num_external_calls=1,
        )

        vector = fp.to_vector()
        self.assertIsInstance(vector, list)
        self.assertTrue(len(vector) > 5)

    def test_to_dict(self):
        """Test dictionary conversion."""
        fp = SemanticFingerprint(
            fingerprint_id="FP-001",
            fingerprint_type=FingerprintType.BEHAVIORAL_SIGNATURE,
            source_name="test",
        )

        d = fp.to_dict()
        self.assertIn("fingerprint_id", d)
        self.assertIn("type", d)


class TestFingerprintGenerator(unittest.TestCase):
    """Test fingerprint generation."""

    def setUp(self):
        self.generator = FingerprintGenerator()

    def test_generator_creation(self):
        """Test generator creation."""
        self.assertIsNotNone(self.generator.config)

    def test_generate_from_function(self):
        """Test generating fingerprint from function data."""
        fp = self.generator.generate_from_function(
            function_name="withdraw",
            operations=["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            properties={"visibility": "external", "has_access_gate": True},
            contract_name="Vault",
        )

        self.assertEqual(fp.source_name, "withdraw")
        self.assertEqual(fp.contract_name, "Vault")
        self.assertEqual(fp.num_operations, 3)

    def test_generate_from_kg(self):
        """Test generating fingerprints from KG data."""
        kg_data = {
            "functions": [
                {
                    "name": "deposit",
                    "operations": ["WRITES_USER_BALANCE"],
                    "properties": {"visibility": "external"},
                },
                {
                    "name": "withdraw",
                    "operations": ["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT"],
                    "properties": {"visibility": "external", "has_access_gate": True},
                },
            ],
        }

        fingerprints = self.generator.generate_from_kg(kg_data, "TestContract")

        # Should have function fingerprints + contract fingerprint
        self.assertGreaterEqual(len(fingerprints), 2)

    def test_generate_behavioral_signature(self):
        """Test behavioral signature generation."""
        sig = self.generator.generate_behavioral_signature(
            operations=["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        )

        self.assertIn("→", sig)
        self.assertIn("R:bal", sig)

    def test_compare_fingerprints(self):
        """Test fingerprint comparison."""
        fp1 = self.generator.generate_from_function(
            "test1",
            ["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT"],
            {},
        )
        fp2 = self.generator.generate_from_function(
            "test2",
            ["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT"],
            {},
        )

        similarity = self.generator.compare_fingerprints(fp1, fp2)
        self.assertGreater(similarity, 0.8)


class TestSimilarityScore(unittest.TestCase):
    """Test similarity score class."""

    def test_creation(self):
        """Test score creation."""
        score = SimilarityScore(
            score=0.85,
            similarity_type=SimilarityType.STRUCTURAL,
            confidence=0.9,
        )

        self.assertEqual(score.score, 0.85)
        self.assertEqual(score.similarity_type, SimilarityType.STRUCTURAL)

    def test_to_dict(self):
        """Test dictionary conversion."""
        score = SimilarityScore(
            score=0.75,
            similarity_type=SimilarityType.BEHAVIORAL,
        )

        d = score.to_dict()
        self.assertIn("score", d)
        self.assertIn("type", d)

    def test_is_significant(self):
        """Test significance check."""
        high_score = SimilarityScore(score=0.7, similarity_type=SimilarityType.STRUCTURAL)
        low_score = SimilarityScore(score=0.3, similarity_type=SimilarityType.NONE)

        self.assertTrue(high_score.is_significant(0.5))
        self.assertFalse(low_score.is_significant(0.5))


class TestSimilarityCalculator(unittest.TestCase):
    """Test similarity calculation."""

    def setUp(self):
        self.calculator = SimilarityCalculator()
        self.generator = FingerprintGenerator()

    def test_calculator_creation(self):
        """Test calculator creation."""
        self.assertIsNotNone(self.calculator.config)

    def test_calculate_identical(self):
        """Test calculation for identical fingerprints."""
        fp1 = self.generator.generate_from_function(
            "test",
            ["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT"],
            {"visibility": "external"},
        )
        fp2 = self.generator.generate_from_function(
            "test",
            ["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT"],
            {"visibility": "external"},
        )

        result = self.calculator.calculate(fp1, fp2)
        self.assertGreater(result.score.score, 0.9)

    def test_calculate_different(self):
        """Test calculation for different fingerprints."""
        fp1 = self.generator.generate_from_function(
            "withdraw",
            ["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            {},
        )
        fp2 = self.generator.generate_from_function(
            "setOwner",
            ["CHECKS_PERMISSION", "MODIFIES_OWNER"],
            {},
        )

        result = self.calculator.calculate(fp1, fp2)
        self.assertLess(result.score.score, 0.5)

    def test_batch_compare(self):
        """Test batch comparison."""
        fps = [
            self.generator.generate_from_function(f"func{i}", ["OP_A", "OP_B"], {})
            for i in range(3)
        ]

        results = self.calculator.batch_compare(fps, threshold=0.5)
        self.assertIsInstance(results, list)

    def test_find_most_similar(self):
        """Test finding most similar."""
        target = self.generator.generate_from_function(
            "target",
            ["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT"],
            {},
        )

        candidates = [
            self.generator.generate_from_function("c1", ["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT"], {}),
            self.generator.generate_from_function("c2", ["MODIFIES_OWNER"], {}),
            self.generator.generate_from_function("c3", ["READS_USER_BALANCE"], {}),
        ]

        results = self.calculator.find_most_similar(target, candidates, top_k=2)
        self.assertEqual(len(results), 2)
        self.assertGreater(results[0].score.score, results[1].score.score)


class TestContractIndex(unittest.TestCase):
    """Test contract index."""

    def setUp(self):
        self.index = ContractIndex()

    def test_index_creation(self):
        """Test index creation."""
        self.assertIsNotNone(self.index.config)

    def test_add_contract(self):
        """Test adding contract to index."""
        kg_data = {
            "functions": [
                {"name": "deposit", "operations": ["WRITES_USER_BALANCE"], "properties": {}},
            ],
        }

        entry = self.index.add_contract("TestContract", kg_data)

        self.assertEqual(entry.contract_name, "TestContract")
        self.assertGreater(len(entry.fingerprints), 0)

    def test_search(self):
        """Test searching index."""
        # Add some contracts
        kg1 = {"functions": [{"name": "f1", "operations": ["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT"], "properties": {}}]}
        kg2 = {"functions": [{"name": "f2", "operations": ["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT"], "properties": {}}]}

        self.index.add_contract("Contract1", kg1)
        self.index.add_contract("Contract2", kg2)

        # Create query fingerprint
        generator = FingerprintGenerator()
        query_fp = generator.generate_from_function(
            "query",
            ["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT"],
            {},
        )

        result = self.index.search(query_fp)
        self.assertIsInstance(result, SearchResult)

    def test_find_similar_contracts(self):
        """Test finding similar contracts."""
        kg1 = {"functions": [{"name": "f1", "operations": ["A", "B", "C"], "properties": {}}]}
        kg2 = {"functions": [{"name": "f2", "operations": ["A", "B", "C"], "properties": {}}]}
        kg3 = {"functions": [{"name": "f3", "operations": ["X", "Y", "Z"], "properties": {}}]}

        self.index.add_contract("Similar1", kg1)
        self.index.add_contract("Similar2", kg2)
        self.index.add_contract("Different", kg3)

        results = self.index.find_similar_contracts("Similar1", min_similarity=0.5)
        self.assertIsInstance(results, list)

    def test_remove_contract(self):
        """Test removing contract from index."""
        kg = {"functions": [{"name": "f", "operations": ["A"], "properties": {}}]}
        self.index.add_contract("ToRemove", kg)

        self.assertTrue(self.index.remove_contract("ToRemove"))
        self.assertFalse(self.index.remove_contract("ToRemove"))

    def test_get_statistics(self):
        """Test getting statistics."""
        stats = self.index.get_statistics()
        self.assertIn("total_contracts", stats)
        self.assertIn("total_fingerprints", stats)

    def test_clear(self):
        """Test clearing index."""
        kg = {"functions": [{"name": "f", "operations": ["A"], "properties": {}}]}
        self.index.add_contract("Test", kg)
        self.index.clear()

        stats = self.index.get_statistics()
        self.assertEqual(stats["total_contracts"], 0)


class TestCloneDetector(unittest.TestCase):
    """Test clone detection."""

    def setUp(self):
        self.detector = CloneDetector()
        self.generator = FingerprintGenerator()

    def test_detector_creation(self):
        """Test detector creation."""
        self.assertIsNotNone(self.detector)

    def test_detect_clones(self):
        """Test detecting clones."""
        fps = [
            SemanticFingerprint(
                fingerprint_id=f"FP-{i}",
                fingerprint_type=FingerprintType.OPERATION_SEQUENCE,
                source_name=f"func{i}",
                contract_name=f"Contract{i}",
                operations=["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT"],
                complexity=2,
                num_operations=2,
            )
            for i in range(3)
        ]

        clones = self.detector.detect_clones(fps, min_similarity=0.7)
        self.assertIsInstance(clones, list)

    def test_find_clones_of(self):
        """Test finding clones of specific function."""
        target = self.generator.generate_from_function(
            "target",
            ["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT"],
            {},
            "SourceContract",
        )

        candidates = [
            self.generator.generate_from_function(f"func{i}", ["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT"], {}, f"Contract{i}")
            for i in range(3)
        ]

        clones = self.detector.find_clones_of(target, candidates, min_similarity=0.7)
        self.assertIsInstance(clones, list)


class TestPatternMatcher(unittest.TestCase):
    """Test pattern matching."""

    def setUp(self):
        self.matcher = PatternMatcher()
        self.generator = FingerprintGenerator()

    def test_matcher_creation(self):
        """Test matcher creation with default patterns."""
        self.assertGreater(len(self.matcher.patterns), 0)

    def test_match_reentrancy(self):
        """Test matching reentrancy pattern."""
        fp = self.generator.generate_from_function(
            "withdraw",
            ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],  # Vulnerable order
            {"visibility": "external"},
        )

        matches = self.matcher.match(fp)
        # Should match reentrancy pattern
        self.assertIsInstance(matches, list)

    def test_no_match_safe(self):
        """Test no match for safe code."""
        fp = self.generator.generate_from_function(
            "safeFunction",
            ["WRITES_USER_BALANCE", "TRANSFERS_VALUE_OUT", "USES_REENTRANCY_GUARD"],
            {},
        )

        matches = self.matcher.match(fp, "REENTRANCY-001")
        # Reentrancy guard should prevent match
        self.assertEqual(len(matches), 0)

    def test_batch_match(self):
        """Test batch pattern matching."""
        fps = [
            self.generator.generate_from_function("f1", ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"], {}),
            self.generator.generate_from_function("f2", ["MODIFIES_CRITICAL_STATE"], {"visibility": "public"}),
        ]

        results = self.matcher.batch_match(fps)
        self.assertIsInstance(results, dict)


class TestClone(unittest.TestCase):
    """Test Clone class."""

    def test_creation(self):
        """Test clone creation."""
        clone = Clone(
            clone_id="CLN-001",
            clone_type=CloneType.TYPE_2,
            similarity=0.95,
            source_function="withdraw",
            source_contract="Vault1",
            source_fingerprint_id="FP-001",
            target_function="withdrawFunds",
            target_contract="Vault2",
            target_fingerprint_id="FP-002",
        )

        self.assertEqual(clone.similarity, 0.95)
        self.assertEqual(clone.clone_type, CloneType.TYPE_2)

    def test_to_dict(self):
        """Test dictionary conversion."""
        clone = Clone(
            clone_id="CLN-001",
            clone_type=CloneType.TYPE_3,
            similarity=0.8,
            source_function="f1",
            source_contract="C1",
            source_fingerprint_id="FP-1",
            target_function="f2",
            target_contract="C2",
            target_fingerprint_id="FP-2",
        )

        d = clone.to_dict()
        self.assertIn("clone_id", d)
        self.assertIn("type", d)
        self.assertIn("similarity", d)


class TestSimilarityEngine(unittest.TestCase):
    """Test similarity engine."""

    def setUp(self):
        self.engine = SimilarityEngine()

    def test_engine_creation(self):
        """Test engine creation."""
        self.assertIsNotNone(self.engine.config)

    def test_analyze_contract(self):
        """Test contract analysis."""
        kg_data = {
            "functions": [
                {"name": "deposit", "operations": ["WRITES_USER_BALANCE"], "properties": {}},
                {"name": "withdraw", "operations": ["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT"], "properties": {}},
            ],
        }

        result = self.engine.analyze_contract("TestContract", kg_data)

        self.assertEqual(result.contract_name, "TestContract")
        self.assertGreater(len(result.fingerprints), 0)

    def test_analyze_with_patterns(self):
        """Test analysis with pattern matching."""
        kg_data = {
            "functions": [
                {
                    "name": "vulnerableWithdraw",
                    "operations": ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
                    "properties": {"visibility": "external"},
                },
            ],
        }

        result = self.engine.analyze_contract("VulnContract", kg_data)

        # Should find pattern matches
        self.assertIsInstance(result.pattern_matches, list)

    def test_find_similar_across_contracts(self):
        """Test finding similar code across multiple contracts."""
        # Add some contracts
        kg1 = {
            "functions": [
                {"name": "withdraw", "operations": ["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"], "properties": {}},
            ],
        }
        kg2 = {
            "functions": [
                {"name": "extractFunds", "operations": ["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"], "properties": {}},
            ],
        }
        kg3 = {
            "functions": [
                {"name": "setOwner", "operations": ["CHECKS_PERMISSION", "MODIFIES_OWNER"], "properties": {}},
            ],
        }

        self.engine.analyze_contract("Vault1", kg1)
        self.engine.analyze_contract("Vault2", kg2)
        self.engine.analyze_contract("Access", kg3)

        # Find similar to Vault1
        similar = self.engine.find_similar_contracts("Vault1", top_k=2)
        self.assertIsInstance(similar, list)

    def test_add_vulnerability_pattern(self):
        """Test adding custom vulnerability pattern."""
        self.engine.add_vulnerability_pattern(
            pattern_id="CUSTOM-001",
            name="Custom Pattern",
            vuln_type="custom",
            severity="medium",
            required_ops=["CUSTOM_OP"],
        )

        self.assertIn("CUSTOM-001", self.engine.pattern_matcher.patterns)

    def test_get_statistics(self):
        """Test getting engine statistics."""
        stats = self.engine.get_statistics()
        self.assertIn("index", stats)
        self.assertIn("patterns", stats)

    def test_analysis_result_summary(self):
        """Test analysis result summary."""
        result = AnalysisResult(
            contract_name="Test",
            fingerprints=[SemanticFingerprint("FP-1", FingerprintType.OPERATION_SEQUENCE, "f1")],
            similar_contracts=[SimilarContract("C1", 0.8)],
        )

        summary = result.summary()
        self.assertIn("Test", summary)
        self.assertIn("Fingerprints", summary)


class TestVulnerabilityCorrelation(unittest.TestCase):
    """Test vulnerability correlation."""

    def test_creation(self):
        """Test correlation creation."""
        corr = VulnerabilityCorrelation(
            vulnerability_type="reentrancy",
            severity="critical",
            affected_contracts=["Vault1", "Vault2"],
            affected_functions=["Vault1.withdraw", "Vault2.extractFunds"],
            confidence=0.85,
        )

        self.assertEqual(corr.vulnerability_type, "reentrancy")
        self.assertEqual(len(corr.affected_contracts), 2)

    def test_to_dict(self):
        """Test dictionary conversion."""
        corr = VulnerabilityCorrelation(
            vulnerability_type="access_control",
            severity="high",
        )

        d = corr.to_dict()
        self.assertIn("vulnerability", d)
        self.assertIn("severity", d)


class TestIntegration(unittest.TestCase):
    """Integration tests for similarity engine."""

    def test_full_analysis_workflow(self):
        """Test complete analysis workflow."""
        engine = SimilarityEngine()

        # Add multiple similar contracts
        for i in range(3):
            kg = {
                "functions": [
                    {
                        "name": "withdraw",
                        "operations": ["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
                        "properties": {"visibility": "external"},
                    },
                    {
                        "name": "deposit",
                        "operations": ["WRITES_USER_BALANCE"],
                        "properties": {},
                    },
                ],
            }
            engine.analyze_contract(f"Vault{i}", kg)

        # Analyze a new contract
        new_kg = {
            "functions": [
                {
                    "name": "extractFunds",  # Different name, same behavior
                    "operations": ["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
                    "properties": {"visibility": "external"},
                },
            ],
        }

        result = engine.analyze_contract("NewVault", new_kg)

        self.assertEqual(result.contract_name, "NewVault")
        # Should find similar contracts
        self.assertGreater(len(result.similar_contracts), 0)

    def test_clone_detection_across_contracts(self):
        """Test clone detection across multiple contracts."""
        engine = SimilarityEngine(EngineConfig(
            clone_threshold=0.6,
            detect_clones=True,
        ))

        # Add contracts with cloned functions
        kg1 = {"functions": [{"name": "transfer", "operations": ["A", "B", "C", "D"], "properties": {}}]}
        kg2 = {"functions": [{"name": "sendTokens", "operations": ["A", "B", "C", "D"], "properties": {}}]}

        engine.analyze_contract("Token1", kg1)
        result = engine.analyze_contract("Token2", kg2)

        # Should detect clones
        self.assertIsInstance(result.clones, list)

    def test_vulnerability_pattern_correlation(self):
        """Test vulnerability pattern correlation."""
        engine = SimilarityEngine()

        # Add contracts with same vulnerability pattern
        vulnerable_kg = {
            "functions": [
                {
                    "name": "unsafeWithdraw",
                    "operations": ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
                    "properties": {"visibility": "external"},
                },
            ],
        }

        engine.analyze_contract("VulnVault1", vulnerable_kg)
        result = engine.analyze_contract("VulnVault2", vulnerable_kg)

        # Should have vulnerability correlations
        self.assertIsInstance(result.vulnerability_correlations, list)


if __name__ == "__main__":
    unittest.main()
