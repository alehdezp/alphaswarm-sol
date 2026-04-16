"""
Tests for P0-T4: Knowledge Graph Persistence

Tests serialization, deserialization, compression, and version management
for all three knowledge graph types.
"""

import pytest
import tempfile
from pathlib import Path
import gzip
import json

from alphaswarm_sol.knowledge import (
    # Domain KG
    DomainKnowledgeGraph,
    Specification,
    Invariant,
    DeFiPrimitive,
    SpecType,
    # Adversarial KG
    AdversarialKnowledgeGraph,
    AttackPattern,
    ExploitRecord,
    AttackCategory,
    Severity,
    # Cross-Graph Linker
    CrossGraphLinker,
    CrossGraphEdge,
    CrossGraphRelation,
    # Persistence
    save_domain_kg,
    load_domain_kg,
    save_adversarial_kg,
    load_adversarial_kg,
    save_cross_graph_edges,
    load_cross_graph_edges,
    get_file_stats,
    SCHEMA_VERSION,
    # Helpers
    load_builtin_patterns,
    load_exploit_database,
)


# Test Fixtures

@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_domain_kg():
    """Create sample Domain KG with minimal data."""
    kg = DomainKnowledgeGraph()

    # Add a spec
    spec = Specification(
        id="test-spec",
        spec_type=SpecType.ERC_STANDARD,
        name="Test Spec",
        description="Test specification",
        version="1.0",
        function_signatures=["test()"],
        expected_operations=["TEST_OP"],
        invariants=[
            Invariant(
                id="test-inv",
                description="Test invariant",
                must_have=["prop1"],
                must_not_have=["prop2"],
            )
        ],
        semantic_tags=["test"],
    )
    kg.add_specification(spec)

    # Add a primitive
    prim = DeFiPrimitive(
        id="test-prim",
        name="Test Primitive",
        description="Test DeFi primitive",
        attack_surface=["Test attack"],
        primitive_invariants=[
            Invariant(
                id="prim-inv",
                description="Primitive invariant",
            )
        ],
    )
    kg.add_primitive(prim)

    return kg


@pytest.fixture
def sample_adversarial_kg():
    """Create sample Adversarial KG with minimal data."""
    kg = AdversarialKnowledgeGraph()

    # Add a pattern
    pattern = AttackPattern(
        id="test-pattern",
        name="Test Pattern",
        category=AttackCategory.REENTRANCY,
        severity=Severity.HIGH,
        description="Test attack pattern",
        required_operations=["TEST_OP"],
        preconditions=["test_precondition"],
        false_positive_indicators=["test_fp"],
        violated_properties=["test_prop"],
        cwes=["CWE-123"],
    )
    kg.add_pattern(pattern)

    # Add an exploit
    exploit = ExploitRecord(
        id="test-exploit",
        name="Test Exploit",
        date="2024-01-01",
        loss_usd=1000000,
        chain="ethereum",
        category=AttackCategory.REENTRANCY,
        cwes=["CWE-123"],
        pattern_ids=["test-pattern"],
        attack_summary="Test exploit",
        attack_steps=["Step 1", "Step 2"],
    )
    kg.add_exploit(exploit)

    return kg


@pytest.fixture
def sample_cross_graph_edge():
    """Create sample cross-graph edge."""
    return CrossGraphEdge(
        id="test-edge",
        source_graph="code",
        source_id="fn_test",
        target_graph="adversarial",
        target_id="test-pattern",
        relation=CrossGraphRelation.SIMILAR_TO,
        confidence=0.85,
        evidence=["Test evidence 1", "Test evidence 2"],
        created_by="test",
        created_at="2024-01-01T00:00:00",
    )


# Domain KG Persistence Tests

class TestDomainKGPersistence:
    """Test Domain KG save/load."""

    def test_save_and_load_domain_kg(self, sample_domain_kg, temp_dir):
        """Should save and load Domain KG correctly."""
        file_path = temp_dir / "domain_kg.json.gz"

        # Save
        save_domain_kg(sample_domain_kg, file_path)

        assert file_path.exists()

        # Load
        loaded_kg = load_domain_kg(file_path)

        # Verify
        assert len(loaded_kg.specifications) == 1
        assert "test-spec" in loaded_kg.specifications

        spec = loaded_kg.specifications["test-spec"]
        assert spec.name == "Test Spec"
        assert len(spec.invariants) == 1
        assert spec.invariants[0].id == "test-inv"

        assert len(loaded_kg.primitives) == 1
        assert "test-prim" in loaded_kg.primitives

    def test_save_uncompressed(self, sample_domain_kg, temp_dir):
        """Should save uncompressed when compress=False."""
        file_path = temp_dir / "domain_kg.json"

        save_domain_kg(sample_domain_kg, file_path, compress=False)

        # Should be readable as plain JSON
        with open(file_path, 'r') as f:
            data = json.load(f)

        assert data["schema_version"] == SCHEMA_VERSION
        assert data["graph_type"] == "domain"

    def test_compression_reduces_size(self, sample_domain_kg, temp_dir):
        """Compressed file should be smaller than uncompressed."""
        compressed_path = temp_dir / "compressed.json.gz"
        uncompressed_path = temp_dir / "uncompressed.json"

        save_domain_kg(sample_domain_kg, compressed_path, compress=True)
        save_domain_kg(sample_domain_kg, uncompressed_path, compress=False)

        compressed_size = compressed_path.stat().st_size
        uncompressed_size = uncompressed_path.stat().st_size

        assert compressed_size < uncompressed_size

    def test_round_trip_with_full_kg(self, temp_dir):
        """Test with fully loaded Domain KG."""
        kg = DomainKnowledgeGraph()
        kg.load_all()

        file_path = temp_dir / "full_domain.json.gz"

        # Save
        save_domain_kg(kg, file_path)

        # Load
        loaded_kg = load_domain_kg(file_path)

        # Verify all specs preserved
        assert len(loaded_kg.specifications) == len(kg.specifications)
        for spec_id in kg.specifications:
            assert spec_id in loaded_kg.specifications
            original = kg.specifications[spec_id]
            loaded = loaded_kg.specifications[spec_id]
            assert loaded.name == original.name
            assert len(loaded.invariants) == len(original.invariants)

        # Verify all primitives preserved
        assert len(loaded_kg.primitives) == len(kg.primitives)


# Adversarial KG Persistence Tests

class TestAdversarialKGPersistence:
    """Test Adversarial KG save/load."""

    def test_save_and_load_adversarial_kg(self, sample_adversarial_kg, temp_dir):
        """Should save and load Adversarial KG correctly."""
        file_path = temp_dir / "adversarial_kg.json.gz"

        # Save
        save_adversarial_kg(sample_adversarial_kg, file_path)

        assert file_path.exists()

        # Load
        loaded_kg = load_adversarial_kg(file_path)

        # Verify patterns
        assert len(loaded_kg.patterns) == 1
        assert "test-pattern" in loaded_kg.patterns

        pattern = loaded_kg.patterns["test-pattern"]
        assert pattern.name == "Test Pattern"
        assert pattern.category == AttackCategory.REENTRANCY
        assert pattern.severity == Severity.HIGH

        # Verify exploits
        assert len(loaded_kg.exploits) == 1
        assert "test-exploit" in loaded_kg.exploits

        exploit = loaded_kg.exploits["test-exploit"]
        assert exploit.name == "Test Exploit"
        assert exploit.loss_usd == 1000000

    def test_round_trip_with_all_patterns(self, temp_dir):
        """Test with all builtin patterns and exploits."""
        kg = AdversarialKnowledgeGraph()
        load_builtin_patterns(kg)
        load_exploit_database(kg)

        file_path = temp_dir / "full_adversarial.json.gz"

        # Save
        save_adversarial_kg(kg, file_path)

        # Load
        loaded_kg = load_adversarial_kg(file_path)

        # Verify all patterns preserved
        assert len(loaded_kg.patterns) == len(kg.patterns)
        for pattern_id in kg.patterns:
            assert pattern_id in loaded_kg.patterns
            original = kg.patterns[pattern_id]
            loaded = loaded_kg.patterns[pattern_id]
            assert loaded.name == original.name
            assert loaded.category == original.category
            assert loaded.severity == original.severity

        # Verify all exploits preserved
        assert len(loaded_kg.exploits) == len(kg.exploits)

    def test_enum_serialization(self, sample_adversarial_kg, temp_dir):
        """Enums should serialize and deserialize correctly."""
        file_path = temp_dir / "enum_test.json.gz"

        save_adversarial_kg(sample_adversarial_kg, file_path)
        loaded_kg = load_adversarial_kg(file_path)

        pattern = loaded_kg.patterns["test-pattern"]
        assert isinstance(pattern.category, AttackCategory)
        assert isinstance(pattern.severity, Severity)


# Cross-Graph Edges Persistence Tests

class TestCrossGraphEdgesPersistence:
    """Test cross-graph edge save/load."""

    def test_save_and_load_edges(self, sample_cross_graph_edge, temp_dir):
        """Should save and load cross-graph edges correctly."""
        # Create mock KGs
        from unittest.mock import MagicMock
        code_kg = MagicMock()
        domain_kg = DomainKnowledgeGraph()
        adversarial_kg = AdversarialKnowledgeGraph()

        # Create linker with one edge
        linker = CrossGraphLinker(code_kg, domain_kg, adversarial_kg)
        linker._add_edge(sample_cross_graph_edge)

        file_path = temp_dir / "edges.json.gz"

        # Save
        save_cross_graph_edges(linker, file_path)

        assert file_path.exists()

        # Load
        loaded_linker = load_cross_graph_edges(file_path, code_kg, domain_kg, adversarial_kg)

        # Verify
        assert len(loaded_linker.edges) == 1
        edge = loaded_linker.edges[0]
        assert edge.id == "test-edge"
        assert edge.relation == CrossGraphRelation.SIMILAR_TO
        assert edge.confidence == 0.85
        assert len(edge.evidence) == 2

    def test_multiple_edges(self, temp_dir):
        """Should handle multiple edges correctly."""
        from unittest.mock import MagicMock
        code_kg = MagicMock()
        domain_kg = DomainKnowledgeGraph()
        adversarial_kg = AdversarialKnowledgeGraph()

        linker = CrossGraphLinker(code_kg, domain_kg, adversarial_kg)

        # Add multiple edges
        for i in range(5):
            edge = CrossGraphEdge(
                id=f"edge-{i}",
                source_graph="code",
                source_id=f"fn_{i}",
                target_graph="domain",
                target_id=f"spec-{i}",
                relation=CrossGraphRelation.IMPLEMENTS,
                confidence=0.9,
                evidence=[f"Evidence {i}"],
                created_by="test",
                created_at="2024-01-01T00:00:00",
            )
            linker._add_edge(edge)

        file_path = temp_dir / "multi_edges.json.gz"

        save_cross_graph_edges(linker, file_path)
        loaded_linker = load_cross_graph_edges(file_path, code_kg, domain_kg, adversarial_kg)

        assert len(loaded_linker.edges) == 5


# File Stats Tests

class TestFileStats:
    """Test get_file_stats utility."""

    def test_get_stats_compressed(self, sample_domain_kg, temp_dir):
        """Should return correct stats for compressed file."""
        file_path = temp_dir / "test.json.gz"
        save_domain_kg(sample_domain_kg, file_path, compress=True)

        stats = get_file_stats(file_path)

        assert stats["compressed"] is True
        assert stats["schema_version"] == SCHEMA_VERSION
        assert stats["graph_type"] == "domain"
        assert "file_size_bytes" in stats
        assert stats["file_size_bytes"] > 0
        assert "created_at" in stats
        assert stats["metadata"]["total_specifications"] == 1

    def test_get_stats_uncompressed(self, sample_adversarial_kg, temp_dir):
        """Should return correct stats for uncompressed file."""
        file_path = temp_dir / "test.json"
        save_adversarial_kg(sample_adversarial_kg, file_path, compress=False)

        stats = get_file_stats(file_path)

        assert stats["compressed"] is False
        assert stats["graph_type"] == "adversarial"
        assert stats["metadata"]["total_patterns"] == 1

    def test_get_stats_nonexistent(self, temp_dir):
        """Should raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            get_file_stats(temp_dir / "nonexistent.json")


# Schema Version Tests

class TestSchemaVersion:
    """Test schema version handling."""

    def test_schema_version_in_saved_file(self, sample_domain_kg, temp_dir):
        """Saved files should include schema version."""
        file_path = temp_dir / "version_test.json"
        save_domain_kg(sample_domain_kg, file_path, compress=False)

        with open(file_path, 'r') as f:
            data = json.load(f)

        assert "schema_version" in data
        assert data["schema_version"] == SCHEMA_VERSION

    def test_load_with_matching_version(self, sample_domain_kg, temp_dir):
        """Should load successfully with matching version."""
        file_path = temp_dir / "version_match.json.gz"
        save_domain_kg(sample_domain_kg, file_path)

        # Should not raise
        loaded_kg = load_domain_kg(file_path)
        assert len(loaded_kg.specifications) == 1

    def test_load_with_incompatible_version(self, temp_dir):
        """Should raise ValueError with incompatible version."""
        file_path = temp_dir / "old_version.json"

        # Create file with old version
        data = {
            "schema_version": "3.4.0",
            "graph_type": "domain",
            "content": {"specifications": {}, "defi_primitives": {}},
        }

        with open(file_path, 'w') as f:
            json.dump(data, f)

        # Should raise on load
        with pytest.raises(ValueError, match="Cannot migrate"):
            load_domain_kg(file_path)


# Success Criteria Tests

class TestSuccessCriteria:
    """Validate P0-T4 success criteria."""

    def test_all_kg_types_serialize_correctly(self, temp_dir):
        """All KG types should serialize/deserialize correctly."""
        # Domain KG
        domain_kg = DomainKnowledgeGraph()
        domain_kg.load_all()
        save_domain_kg(domain_kg, temp_dir / "domain.json.gz")
        loaded_domain = load_domain_kg(temp_dir / "domain.json.gz")
        assert len(loaded_domain.specifications) > 0

        # Adversarial KG
        adv_kg = AdversarialKnowledgeGraph()
        load_builtin_patterns(adv_kg)
        save_adversarial_kg(adv_kg, temp_dir / "adversarial.json.gz")
        loaded_adv = load_adversarial_kg(temp_dir / "adversarial.json.gz")
        assert len(loaded_adv.patterns) > 0

        # Cross-graph edges
        from unittest.mock import MagicMock
        linker = CrossGraphLinker(MagicMock(), domain_kg, adv_kg)
        edge = CrossGraphEdge(
            id="test", source_graph="code", source_id="fn",
            target_graph="domain", target_id="spec",
            relation=CrossGraphRelation.IMPLEMENTS,
            confidence=0.9, evidence=[], created_by="test",
            created_at="2024-01-01T00:00:00",
        )
        linker._add_edge(edge)
        save_cross_graph_edges(linker, temp_dir / "edges.json.gz")
        loaded_linker = load_cross_graph_edges(
            temp_dir / "edges.json.gz", MagicMock(), domain_kg, adv_kg
        )
        assert len(loaded_linker.edges) == 1

    def test_round_trip_preserves_data(self, temp_dir):
        """Round-trip should preserve all data exactly."""
        # Create KG with known data
        kg = DomainKnowledgeGraph()
        spec = Specification(
            id="erc20-test",
            spec_type=SpecType.ERC_STANDARD,
            name="ERC-20 Test",
            description="Test ERC-20",
            version="EIP-20",
            function_signatures=["transfer(address,uint256)"],
            expected_operations=["TRANSFERS_VALUE_OUT"],
            invariants=[
                Invariant(
                    id="test-inv-1",
                    description="First invariant",
                    must_have=["prop1", "prop2"],
                ),
                Invariant(
                    id="test-inv-2",
                    description="Second invariant",
                    must_not_have=["bad_prop"],
                ),
            ],
            semantic_tags=["token", "transfer"],
        )
        kg.add_specification(spec)

        # Round-trip
        file_path = temp_dir / "round_trip.json.gz"
        save_domain_kg(kg, file_path)
        loaded_kg = load_domain_kg(file_path)

        # Verify exact match
        loaded_spec = loaded_kg.specifications["erc20-test"]
        assert loaded_spec.name == spec.name
        assert loaded_spec.description == spec.description
        assert loaded_spec.function_signatures == spec.function_signatures
        assert loaded_spec.expected_operations == spec.expected_operations
        assert len(loaded_spec.invariants) == 2
        assert loaded_spec.invariants[0].must_have == ["prop1", "prop2"]
        assert loaded_spec.invariants[1].must_not_have == ["bad_prop"]

    def test_compression_ratio(self, temp_dir):
        """Compressed files should be < 50% of uncompressed."""
        kg = AdversarialKnowledgeGraph()
        load_builtin_patterns(kg)
        load_exploit_database(kg)

        compressed_path = temp_dir / "compressed.json.gz"
        uncompressed_path = temp_dir / "uncompressed.json"

        save_adversarial_kg(kg, compressed_path, compress=True)
        save_adversarial_kg(kg, uncompressed_path, compress=False)

        compressed_size = compressed_path.stat().st_size
        uncompressed_size = uncompressed_path.stat().st_size

        compression_ratio = compressed_size / uncompressed_size
        assert compression_ratio < 0.5, f"Compression ratio {compression_ratio:.2%} >= 50%"

    def test_load_performance(self, temp_dir):
        """Load time should be < 1s for typical graphs."""
        import time

        # Create typical-sized graph
        kg = AdversarialKnowledgeGraph()
        load_builtin_patterns(kg)
        load_exploit_database(kg)

        file_path = temp_dir / "perf_test.json.gz"
        save_adversarial_kg(kg, file_path)

        # Measure load time
        start = time.time()
        loaded_kg = load_adversarial_kg(file_path)
        elapsed = time.time() - start

        assert elapsed < 1.0, f"Load time {elapsed:.2f}s >= 1s"
        assert len(loaded_kg.patterns) > 0
