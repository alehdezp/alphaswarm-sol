"""Tests for deterministic evidence IDs and graph build hashes.

These tests verify:
1. Evidence IDs are stable across runs (determinism)
2. Resolver maps back to source locations correctly
3. Build hashes are consistent for same input
4. ClauseMatrixBuilder produces correct v2 contract format
"""

import pytest
from alphaswarm_sol.llm.evidence_ids import (
    EvidenceID,
    EvidenceIDError,
    EvidenceRegistry,
    EvidenceResolutionError,
    SourceSpan,
    ClauseEvidence,
    ClauseMatrixBuilder,
    generate_evidence_id,
    validate_evidence_id,
    validate_build_hash,
    parse_evidence_id,
    build_evidence_ref,
    build_evidence_refs_from_nodes,
    EVIDENCE_ID_PATTERN,
    BUILD_HASH_PATTERN,
)
from alphaswarm_sol.kg.graph_hash import (
    BuildHashError,
    BuildHashTracker,
    compute_graph_hash,
    compute_source_hash,
    compute_content_hash,
    compute_incremental_hash,
    validate_build_hash as validate_build_hash_kg,
    validate_build_hash_strict,
    check_build_hash_consistency,
    embed_build_hash,
    extract_build_hash,
    BUILD_HASH_LENGTH,
)


# ============================================================================
# Evidence ID Tests
# ============================================================================


class TestSourceSpan:
    """Tests for SourceSpan."""

    def test_basic_span(self) -> None:
        """Test basic source span creation."""
        span = SourceSpan(file="Token.sol", line_start=42)
        assert span.file == "Token.sol"
        assert span.line_start == 42
        assert span.line == 42
        assert span.column == 0

    def test_span_with_all_fields(self) -> None:
        """Test span with all fields specified."""
        span = SourceSpan(
            file="Token.sol",
            line_start=42,
            line_end=45,
            column_start=4,
            column_end=20,
        )
        assert span.line_end == 45
        assert span.column_start == 4
        assert span.column_end == 20

    def test_span_validation_line_start(self) -> None:
        """Test that line_start must be >= 1."""
        with pytest.raises(ValueError, match="line_start must be >= 1"):
            SourceSpan(file="Token.sol", line_start=0)

    def test_span_validation_line_end(self) -> None:
        """Test that line_end cannot be before line_start."""
        with pytest.raises(ValueError, match="line_end.*cannot be before line_start"):
            SourceSpan(file="Token.sol", line_start=10, line_end=5)

    def test_span_to_dict(self) -> None:
        """Test span serialization."""
        span = SourceSpan(file="Token.sol", line_start=42, column_start=4)
        d = span.to_dict()
        assert d["file"] == "Token.sol"
        assert d["line"] == 42
        assert d["column"] == 4

    def test_span_from_dict(self) -> None:
        """Test span deserialization."""
        data = {"file": "Token.sol", "line": 42, "column": 4}
        span = SourceSpan.from_dict(data)
        assert span.file == "Token.sol"
        assert span.line_start == 42
        assert span.column_start == 4


class TestEvidenceID:
    """Tests for EvidenceID."""

    def test_deterministic_id(self) -> None:
        """Test that same inputs produce same ID."""
        span = SourceSpan(file="Token.sol", line_start=42)

        id1 = EvidenceID(
            build_hash="a1b2c3d4e5f6",
            node_id="N-withdraw-001",
            span=span,
        )
        id2 = EvidenceID(
            build_hash="a1b2c3d4e5f6",
            node_id="N-withdraw-001",
            span=span,
        )

        assert id1.id == id2.id
        assert str(id1) == str(id2)

    def test_different_inputs_different_id(self) -> None:
        """Test that different inputs produce different IDs."""
        span = SourceSpan(file="Token.sol", line_start=42)

        id1 = EvidenceID(
            build_hash="a1b2c3d4e5f6",
            node_id="N-withdraw-001",
            span=span,
        )
        id2 = EvidenceID(
            build_hash="a1b2c3d4e5f6",
            node_id="N-withdraw-002",  # Different node
            span=span,
        )

        assert id1.id != id2.id

    def test_id_format(self) -> None:
        """Test that ID follows EVD-xxxxxxxx format."""
        span = SourceSpan(file="Token.sol", line_start=42)
        evidence = EvidenceID(
            build_hash="a1b2c3d4e5f6",
            node_id="N-001",
            span=span,
        )

        assert EVIDENCE_ID_PATTERN.match(evidence.id) is not None
        assert evidence.id.startswith("EVD-")
        assert len(evidence.id) == 12  # EVD- + 8 hex

    def test_invalid_build_hash(self) -> None:
        """Test that invalid build hash raises error."""
        span = SourceSpan(file="Token.sol", line_start=42)

        with pytest.raises(EvidenceIDError, match="Invalid build_hash format"):
            EvidenceID(
                build_hash="invalid",
                node_id="N-001",
                span=span,
            )

    def test_to_dict(self) -> None:
        """Test evidence ID to dictionary conversion."""
        span = SourceSpan(file="Token.sol", line_start=42, column_start=4)
        evidence = EvidenceID(
            build_hash="a1b2c3d4e5f6",
            node_id="N-001",
            span=span,
        )

        d = evidence.to_dict()
        assert d["file"] == "Token.sol"
        assert d["line"] == 42
        assert d["column"] == 4
        assert d["node_id"] == "N-001"
        assert d["snippet_id"] == evidence.id
        assert d["build_hash"] == "a1b2c3d4e5f6"


class TestEvidenceRegistry:
    """Tests for EvidenceRegistry."""

    def test_register_and_resolve(self) -> None:
        """Test registering and resolving evidence."""
        registry = EvidenceRegistry(build_hash="a1b2c3d4e5f6")
        span = SourceSpan(file="Token.sol", line_start=42)

        evidence = registry.register("N-001", span)
        resolved = registry.resolve(evidence.id)

        assert resolved == evidence
        assert resolved.span.file == "Token.sol"
        assert resolved.span.line == 42

    def test_resolve_not_found(self) -> None:
        """Test resolving non-existent ID."""
        registry = EvidenceRegistry(build_hash="a1b2c3d4e5f6")

        with pytest.raises(EvidenceResolutionError, match="not found"):
            registry.resolve("EVD-00000000")

    def test_resolve_invalid_format(self) -> None:
        """Test resolving invalid ID format."""
        registry = EvidenceRegistry(build_hash="a1b2c3d4e5f6")

        with pytest.raises(EvidenceResolutionError, match="Invalid evidence ID format"):
            registry.resolve("invalid-id")

    def test_get_returns_none(self) -> None:
        """Test get returns None for missing ID."""
        registry = EvidenceRegistry(build_hash="a1b2c3d4e5f6")
        assert registry.get("EVD-00000000") is None

    def test_contains(self) -> None:
        """Test contains method."""
        registry = EvidenceRegistry(build_hash="a1b2c3d4e5f6")
        span = SourceSpan(file="Token.sol", line_start=42)

        evidence = registry.register("N-001", span)

        assert registry.contains(evidence.id)
        assert not registry.contains("EVD-00000000")

    def test_all_ids_and_count(self) -> None:
        """Test all_ids and count methods."""
        registry = EvidenceRegistry(build_hash="a1b2c3d4e5f6")

        registry.register("N-001", SourceSpan(file="A.sol", line_start=1))
        registry.register("N-002", SourceSpan(file="B.sol", line_start=2))

        assert registry.count() == 2
        assert len(registry.all_ids()) == 2


class TestGenerateEvidenceID:
    """Tests for generate_evidence_id function."""

    def test_deterministic(self) -> None:
        """Test determinism of generate_evidence_id."""
        id1 = generate_evidence_id("a1b2c3d4e5f6", "N-001", 42, 4)
        id2 = generate_evidence_id("a1b2c3d4e5f6", "N-001", 42, 4)

        assert id1 == id2

    def test_format(self) -> None:
        """Test format of generated ID."""
        evidence_id = generate_evidence_id("a1b2c3d4e5f6", "N-001", 42)

        assert validate_evidence_id(evidence_id)
        assert evidence_id.startswith("EVD-")

    def test_different_column_different_id(self) -> None:
        """Test that different column produces different ID."""
        id1 = generate_evidence_id("a1b2c3d4e5f6", "N-001", 42, 0)
        id2 = generate_evidence_id("a1b2c3d4e5f6", "N-001", 42, 10)

        assert id1 != id2


class TestValidation:
    """Tests for validation functions."""

    def test_validate_evidence_id_valid(self) -> None:
        """Test valid evidence ID formats."""
        assert validate_evidence_id("EVD-a1b2c3d4")
        assert validate_evidence_id("EVD-00000000")
        assert validate_evidence_id("EVD-ffffffff")

    def test_validate_evidence_id_invalid(self) -> None:
        """Test invalid evidence ID formats."""
        assert not validate_evidence_id("evd-a1b2c3d4")  # Wrong case
        assert not validate_evidence_id("EVD-a1b2c3")  # Too short
        assert not validate_evidence_id("EVD-a1b2c3d4e")  # Too long
        assert not validate_evidence_id("EVD-ABCDEFGH")  # Uppercase hex
        assert not validate_evidence_id("XYZ-a1b2c3d4")  # Wrong prefix

    def test_validate_build_hash_valid(self) -> None:
        """Test valid build hash formats."""
        assert validate_build_hash("a1b2c3d4e5f6")
        assert validate_build_hash("000000000000")
        assert validate_build_hash("ffffffffffff")

    def test_validate_build_hash_invalid(self) -> None:
        """Test invalid build hash formats."""
        assert not validate_build_hash("a1b2c3d4e5f")  # Too short
        assert not validate_build_hash("a1b2c3d4e5f6g")  # Too long
        assert not validate_build_hash("ABCDEF123456")  # Uppercase

    def test_parse_evidence_id(self) -> None:
        """Test parsing evidence ID."""
        prefix, hash_part = parse_evidence_id("EVD-a1b2c3d4")
        assert prefix == "EVD"
        assert hash_part == "a1b2c3d4"

    def test_parse_evidence_id_invalid(self) -> None:
        """Test parsing invalid ID raises error."""
        with pytest.raises(EvidenceIDError):
            parse_evidence_id("invalid")


# ============================================================================
# Clause Matrix Tests
# ============================================================================


class TestClauseMatrixBuilder:
    """Tests for ClauseMatrixBuilder."""

    def test_add_matched_clause(self) -> None:
        """Test adding a matched clause with evidence."""
        registry = EvidenceRegistry(build_hash="a1b2c3d4e5f6")
        builder = ClauseMatrixBuilder(registry)

        span = SourceSpan(file="Token.sol", line_start=42)
        evidence = builder.add_matched("pattern:all:0", "N-001", span)

        matrix = builder.build()
        assert len(matrix) == 1
        assert matrix[0]["clause"] == "pattern:all:0"
        assert matrix[0]["status"] == "matched"
        assert len(matrix[0]["evidence_refs"]) == 1
        assert matrix[0]["evidence_refs"][0]["snippet_id"] == evidence.id

    def test_add_failed_clause(self) -> None:
        """Test adding a failed clause."""
        registry = EvidenceRegistry(build_hash="a1b2c3d4e5f6")
        builder = ClauseMatrixBuilder(registry)

        builder.add_failed("pattern:none:0", reason="guard_present")

        matrix = builder.build()
        assert len(matrix) == 1
        assert matrix[0]["clause"] == "pattern:none:0"
        assert matrix[0]["status"] == "failed"
        assert "guard_present" in matrix[0]["omission_refs"]

    def test_add_unknown_clause(self) -> None:
        """Test adding an unknown clause with omission reason."""
        registry = EvidenceRegistry(build_hash="a1b2c3d4e5f6")
        builder = ClauseMatrixBuilder(registry)

        builder.add_unknown("pattern:all:1", "external_return_untracked")

        matrix = builder.build()
        assert len(matrix) == 1
        assert matrix[0]["clause"] == "pattern:all:1"
        assert matrix[0]["status"] == "unknown"
        assert "external_return_untracked" in matrix[0]["omission_refs"]

    def test_get_clause_lists(self) -> None:
        """Test getting clause lists."""
        registry = EvidenceRegistry(build_hash="a1b2c3d4e5f6")
        builder = ClauseMatrixBuilder(registry)

        builder.add_matched("p:all:0", "N-001", SourceSpan(file="A.sol", line_start=1))
        builder.add_failed("p:none:0", reason="guard_present")
        builder.add_unknown("p:all:1", "unknown_reason")

        matched, failed, unknown = builder.get_clause_lists()

        assert "p:all:0" in matched
        assert "p:none:0" in failed
        assert "p:all:1" in unknown

    def test_get_all_evidence_refs(self) -> None:
        """Test getting all evidence refs."""
        registry = EvidenceRegistry(build_hash="a1b2c3d4e5f6")
        builder = ClauseMatrixBuilder(registry)

        builder.add_matched("p:all:0", "N-001", SourceSpan(file="A.sol", line_start=1))
        builder.add_matched("p:all:1", "N-002", SourceSpan(file="B.sol", line_start=2))

        refs = builder.get_all_evidence_refs()
        assert len(refs) == 2


class TestBuildEvidenceRef:
    """Tests for build_evidence_ref helper."""

    def test_basic_ref(self) -> None:
        """Test building basic evidence ref."""
        ref = build_evidence_ref(
            build_hash="a1b2c3d4e5f6",
            node_id="N-001",
            file="Token.sol",
            line=42,
        )

        assert ref["file"] == "Token.sol"
        assert ref["line"] == 42
        assert ref["node_id"] == "N-001"
        assert ref["build_hash"] == "a1b2c3d4e5f6"
        assert "snippet_id" in ref
        assert validate_evidence_id(ref["snippet_id"])

    def test_ref_with_snippet(self) -> None:
        """Test building ref with snippet."""
        ref = build_evidence_ref(
            build_hash="a1b2c3d4e5f6",
            node_id="N-001",
            file="Token.sol",
            line=42,
            snippet="function withdraw() external {",
        )

        assert ref["snippet"] == "function withdraw() external {"

    def test_ref_snippet_truncation(self) -> None:
        """Test that long snippets are truncated."""
        long_snippet = "x" * 300
        ref = build_evidence_ref(
            build_hash="a1b2c3d4e5f6",
            node_id="N-001",
            file="Token.sol",
            line=42,
            snippet=long_snippet,
        )

        assert len(ref["snippet"]) == 200


class TestBuildEvidenceRefsFromNodes:
    """Tests for build_evidence_refs_from_nodes helper."""

    def test_from_nodes(self) -> None:
        """Test building refs from node list."""
        nodes = [
            {"id": "N-001", "file": "A.sol", "line": 10},
            {"id": "N-002", "file": "B.sol", "line": 20},
        ]

        refs = build_evidence_refs_from_nodes("a1b2c3d4e5f6", nodes)

        assert len(refs) == 2
        assert refs[0]["file"] == "A.sol"
        assert refs[1]["file"] == "B.sol"

    def test_skips_incomplete_nodes(self) -> None:
        """Test that incomplete nodes are skipped."""
        nodes = [
            {"id": "N-001", "file": "A.sol", "line": 10},
            {"id": "N-002", "file": "B.sol"},  # Missing line
            {"id": "N-003", "line": 30},  # Missing file
        ]

        refs = build_evidence_refs_from_nodes("a1b2c3d4e5f6", nodes)

        assert len(refs) == 1
        assert refs[0]["file"] == "A.sol"


# ============================================================================
# Graph Build Hash Tests
# ============================================================================


class TestComputeGraphHash:
    """Tests for compute_graph_hash."""

    def test_deterministic(self) -> None:
        """Test that same graph produces same hash."""
        graph = {
            "nodes": [
                {"id": "N-001", "type": "Function", "label": "withdraw"},
                {"id": "N-002", "type": "StateVariable", "label": "balance"},
            ],
            "edges": [
                {"id": "E-001", "type": "WRITES", "source": "N-001", "target": "N-002"},
            ],
        }

        hash1 = compute_graph_hash(graph)
        hash2 = compute_graph_hash(graph)

        assert hash1 == hash2
        assert len(hash1) == BUILD_HASH_LENGTH

    def test_order_independence(self) -> None:
        """Test that node/edge order doesn't affect hash."""
        graph1 = {
            "nodes": [
                {"id": "N-001", "type": "Function", "label": "a"},
                {"id": "N-002", "type": "Function", "label": "b"},
            ],
            "edges": [],
        }
        graph2 = {
            "nodes": [
                {"id": "N-002", "type": "Function", "label": "b"},
                {"id": "N-001", "type": "Function", "label": "a"},
            ],
            "edges": [],
        }

        assert compute_graph_hash(graph1) == compute_graph_hash(graph2)

    def test_different_content_different_hash(self) -> None:
        """Test that different content produces different hash."""
        graph1 = {"nodes": [{"id": "N-001", "type": "Function", "label": "a"}], "edges": []}
        graph2 = {"nodes": [{"id": "N-001", "type": "Function", "label": "b"}], "edges": []}

        assert compute_graph_hash(graph1) != compute_graph_hash(graph2)

    def test_hash_format(self) -> None:
        """Test that hash has correct format."""
        graph = {"nodes": [], "edges": []}
        build_hash = compute_graph_hash(graph)

        assert validate_build_hash_kg(build_hash)
        assert BUILD_HASH_PATTERN.match(build_hash) is not None


class TestComputeContentHash:
    """Tests for compute_content_hash."""

    def test_deterministic(self) -> None:
        """Test that same content produces same hash."""
        content = "contract Token { function foo() {} }"

        hash1 = compute_content_hash(content)
        hash2 = compute_content_hash(content)

        assert hash1 == hash2

    def test_different_content(self) -> None:
        """Test that different content produces different hash."""
        hash1 = compute_content_hash("contract A {}")
        hash2 = compute_content_hash("contract B {}")

        assert hash1 != hash2


class TestComputeIncrementalHash:
    """Tests for compute_incremental_hash."""

    def test_incremental_update(self) -> None:
        """Test incremental hash update."""
        base = compute_content_hash("original")
        updated = compute_incremental_hash(base, "additional")

        assert updated != base
        assert validate_build_hash_kg(updated)

    def test_invalid_base_hash(self) -> None:
        """Test that invalid base hash raises error."""
        with pytest.raises(BuildHashError, match="Invalid base hash"):
            compute_incremental_hash("invalid", "content")


class TestBuildHashValidation:
    """Tests for build hash validation functions."""

    def test_validate_build_hash_valid(self) -> None:
        """Test validation of valid hash."""
        assert validate_build_hash_kg("a1b2c3d4e5f6")

    def test_validate_build_hash_invalid(self) -> None:
        """Test validation of invalid hash."""
        assert not validate_build_hash_kg("invalid")
        assert not validate_build_hash_kg("abc")
        assert not validate_build_hash_kg("")

    def test_validate_build_hash_strict(self) -> None:
        """Test strict validation raises on invalid."""
        with pytest.raises(BuildHashError):
            validate_build_hash_strict("invalid")


class TestCheckBuildHashConsistency:
    """Tests for check_build_hash_consistency."""

    def test_consistent_refs(self) -> None:
        """Test checking consistent refs."""
        refs = [
            {"build_hash": "a1b2c3d4e5f6", "file": "A.sol"},
            {"build_hash": "a1b2c3d4e5f6", "file": "B.sol"},
        ]

        errors = check_build_hash_consistency("a1b2c3d4e5f6", refs)
        assert len(errors) == 0

    def test_inconsistent_refs(self) -> None:
        """Test detecting inconsistent refs."""
        refs = [
            {"build_hash": "a1b2c3d4e5f6", "file": "A.sol"},
            {"build_hash": "different12ab", "file": "B.sol"},
        ]

        errors = check_build_hash_consistency("a1b2c3d4e5f6", refs)
        assert len(errors) == 1
        assert "mismatch" in errors[0]


class TestEmbedExtractBuildHash:
    """Tests for embed_build_hash and extract_build_hash."""

    def test_embed_and_extract(self) -> None:
        """Test embedding and extracting build hash."""
        graph = {"nodes": [], "edges": [], "metadata": {}}

        embed_build_hash(graph, "a1b2c3d4e5f6")
        extracted = extract_build_hash(graph)

        assert extracted == "a1b2c3d4e5f6"

    def test_embed_computes_if_not_provided(self) -> None:
        """Test that embed computes hash if not provided."""
        graph = {"nodes": [{"id": "N-1", "type": "F", "label": "x"}], "edges": [], "metadata": {}}

        embed_build_hash(graph)
        extracted = extract_build_hash(graph)

        assert extracted is not None
        assert validate_build_hash_kg(extracted)

    def test_extract_returns_none_if_missing(self) -> None:
        """Test extract returns None if no hash."""
        graph = {"nodes": [], "edges": [], "metadata": {}}

        assert extract_build_hash(graph) is None

    def test_extract_computes_if_missing(self) -> None:
        """Test extract computes if requested."""
        graph = {"nodes": [], "edges": [], "metadata": {}}

        extracted = extract_build_hash(graph, compute_if_missing=True)

        assert extracted is not None
        assert validate_build_hash_kg(extracted)


class TestBuildHashTracker:
    """Tests for BuildHashTracker."""

    def test_set_and_get(self) -> None:
        """Test setting and getting hash."""
        tracker = BuildHashTracker()
        tracker.set("a1b2c3d4e5f6")

        assert tracker.current == "a1b2c3d4e5f6"

    def test_history(self) -> None:
        """Test hash history tracking."""
        tracker = BuildHashTracker()
        tracker.set("111111111111")
        tracker.set("222222222222")
        tracker.set("333333333333")

        assert tracker.current == "333333333333"
        assert tracker.history == ["111111111111", "222222222222"]

    def test_validate_consistent(self) -> None:
        """Test consistency validation."""
        tracker = BuildHashTracker()
        tracker.set("a1b2c3d4e5f6")

        assert tracker.validate_consistent("a1b2c3d4e5f6")
        assert not tracker.validate_consistent("000000000000")

    def test_set_invalid_raises(self) -> None:
        """Test that setting invalid hash raises error."""
        tracker = BuildHashTracker()

        with pytest.raises(BuildHashError):
            tracker.set("invalid")


# ============================================================================
# Integration Tests
# ============================================================================


class TestEvidenceAndBuildHashIntegration:
    """Integration tests for evidence IDs and build hashes."""

    def test_evidence_tied_to_build_hash(self) -> None:
        """Test that evidence IDs are tied to specific build hash."""
        build_hash = "a1b2c3d4e5f6"
        registry = EvidenceRegistry(build_hash=build_hash)

        span = SourceSpan(file="Token.sol", line_start=42)
        evidence = registry.register("N-001", span)

        # Evidence should reference the build hash
        ref_dict = evidence.to_dict()
        assert ref_dict["build_hash"] == build_hash

    def test_different_build_hash_different_evidence_id(self) -> None:
        """Test that same source with different build hash produces different ID."""
        span = SourceSpan(file="Token.sol", line_start=42)

        evidence1 = EvidenceID(build_hash="111111111111", node_id="N-001", span=span)
        evidence2 = EvidenceID(build_hash="222222222222", node_id="N-001", span=span)

        assert evidence1.id != evidence2.id

    def test_full_workflow(self) -> None:
        """Test full workflow: graph hash -> evidence IDs -> resolution."""
        # 1. Compute build hash from graph
        graph = {
            "nodes": [
                {"id": "N-001", "type": "Function", "label": "withdraw"},
            ],
            "edges": [],
        }
        build_hash = compute_graph_hash(graph)

        # 2. Create evidence registry
        registry = EvidenceRegistry(build_hash=build_hash)

        # 3. Register evidence
        span = SourceSpan(file="Token.sol", line_start=42, column_start=4)
        evidence = registry.register("N-001", span)

        # 4. Verify evidence can be resolved
        resolved = registry.resolve(evidence.id)
        assert resolved.span.file == "Token.sol"
        assert resolved.span.line == 42
        assert resolved.build_hash == build_hash

        # 5. Verify same ID is generated for same inputs
        evidence2 = EvidenceID(build_hash=build_hash, node_id="N-001", span=span)
        assert evidence.id == evidence2.id

    def test_clause_matrix_with_graph_hash(self) -> None:
        """Test clause matrix builder with graph-computed hash."""
        # Compute hash from graph
        graph = {"nodes": [{"id": "N-001", "type": "F", "label": "x"}], "edges": []}
        build_hash = compute_graph_hash(graph)

        # Build clause matrix
        registry = EvidenceRegistry(build_hash=build_hash)
        builder = ClauseMatrixBuilder(registry)

        builder.add_matched(
            "reentrancy:all:0",
            "N-001",
            SourceSpan(file="Token.sol", line_start=42),
        )
        builder.add_unknown("reentrancy:all:1", "external_return_untracked")

        # Verify output
        matrix = builder.build()
        matched, failed, unknown = builder.get_clause_lists()

        assert len(matrix) == 2
        assert len(matched) == 1
        assert len(unknown) == 1

        # Verify evidence refs have consistent build hash
        refs = builder.get_all_evidence_refs()
        errors = check_build_hash_consistency(build_hash, refs)
        assert len(errors) == 0
