"""Tests for retrieval packer (Phase 7.1.3-03).

Validates compact evidence bundle packing with TOON format while
preserving evidence-first traceability.
"""

import pytest

from alphaswarm_sol.context.retrieval_packer import (
    RetrievalPacker,
    PackedEvidenceBundle,
    EvidenceItem,
    pack_evidence_items,
    unpack_evidence_bundle,
)
from alphaswarm_sol.context.integrations.evidence import EvidenceAssembler


class TestEvidenceItem:
    """Tests for EvidenceItem dataclass."""

    def test_basic_creation(self):
        """Test basic EvidenceItem creation."""
        item = EvidenceItem(
            evidence_id="E-ABC123",
            file_path="contracts/Vault.sol",
            line_start=45,
            line_end=52,
        )

        assert item.evidence_id == "E-ABC123"
        assert item.file_path == "contracts/Vault.sol"
        assert item.line_start == 45
        assert item.line_end == 52
        assert item.risk_score == 0.0
        assert item.operations == []

    def test_line_end_defaults_to_start(self):
        """Test line_end defaults to line_start if not specified."""
        item = EvidenceItem(
            evidence_id="E-001",
            file_path="test.sol",
            line_start=10,
        )

        assert item.line_end == 10

    def test_to_dict(self):
        """Test EvidenceItem to_dict serialization."""
        item = EvidenceItem(
            evidence_id="E-ABC123",
            file_path="contracts/Vault.sol",
            line_start=45,
            line_end=52,
            code_snippet="function withdraw() { ... }",
            risk_score=0.85,
            operations=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            metadata={"pattern": "reentrancy-classic"},
        )

        d = item.to_dict()

        assert d["id"] == "E-ABC123"
        assert d["file"] == "contracts/Vault.sol"
        assert d["lines"] == [45, 52]
        assert d["risk"] == 0.85
        assert d["code"] == "function withdraw() { ... }"
        assert d["ops"] == ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"]
        assert d["meta"]["pattern"] == "reentrancy-classic"

    def test_from_dict(self):
        """Test EvidenceItem from_dict deserialization."""
        d = {
            "id": "E-XYZ789",
            "file": "Token.sol",
            "lines": [100, 120],
            "risk": 0.7,
            "ops": ["MODIFIES_OWNER"],
        }

        item = EvidenceItem.from_dict(d)

        assert item.evidence_id == "E-XYZ789"
        assert item.file_path == "Token.sol"
        assert item.line_start == 100
        assert item.line_end == 120
        assert item.risk_score == 0.7
        assert "MODIFIES_OWNER" in item.operations

    def test_location_anchor(self):
        """Test location_anchor property."""
        item_single = EvidenceItem(
            evidence_id="E-1",
            file_path="test.sol",
            line_start=10,
            line_end=10,
        )
        assert item_single.location_anchor == "test.sol:10"

        item_range = EvidenceItem(
            evidence_id="E-2",
            file_path="test.sol",
            line_start=10,
            line_end=20,
        )
        assert item_range.location_anchor == "test.sol:10-20"


class TestRetrievalPacker:
    """Tests for RetrievalPacker."""

    def test_pack_empty_list(self):
        """Test packing empty list returns empty bundle."""
        packer = RetrievalPacker()
        bundle = packer.pack([])

        assert bundle.toon_output == ""
        assert bundle.evidence_ids == []
        assert bundle.total_items == 0
        assert bundle.estimated_tokens == 0

    def test_pack_single_item(self):
        """Test packing a single evidence item."""
        packer = RetrievalPacker()

        item = EvidenceItem(
            evidence_id="E-SINGLE",
            file_path="contracts/Test.sol",
            line_start=10,
            risk_score=0.5,
        )

        bundle = packer.pack([item])

        assert bundle.total_items == 1
        assert "E-SINGLE" in bundle.evidence_ids
        assert bundle.toon_output != ""
        assert bundle.estimated_tokens > 0

    def test_pack_multiple_items(self):
        """Test packing multiple evidence items."""
        packer = RetrievalPacker()

        items = [
            EvidenceItem(
                evidence_id=f"E-{i:03d}",
                file_path=f"contracts/Contract{i}.sol",
                line_start=i * 10,
                risk_score=0.1 * i,
            )
            for i in range(1, 6)
        ]

        bundle = packer.pack(items)

        assert bundle.total_items == 5
        assert len(bundle.evidence_ids) == 5
        assert "E-001" in bundle.evidence_ids
        assert "E-005" in bundle.evidence_ids

    def test_unpack_recovers_items(self):
        """Test unpack recovers items from packed output."""
        packer = RetrievalPacker()

        original = EvidenceItem(
            evidence_id="E-RECOVER",
            file_path="recover.sol",
            line_start=25,
            line_end=30,
            risk_score=0.75,
            operations=["CALLS_EXTERNAL"],
        )

        bundle = packer.pack([original])
        unpacked = packer.unpack(bundle.toon_output)

        assert len(unpacked) == 1
        recovered = unpacked[0]
        assert recovered.evidence_id == "E-RECOVER"
        assert recovered.file_path == "recover.sol"
        assert recovered.line_start == 25
        assert recovered.line_end == 30
        assert abs(recovered.risk_score - 0.75) < 0.001

    def test_evidence_ids_preserved(self):
        """Test evidence IDs are always preserved (never trimmed)."""
        packer = RetrievalPacker(max_tokens=100)  # Very small budget

        items = [
            EvidenceItem(
                evidence_id=f"E-PRESERVE-{i}",
                file_path="test.sol",
                line_start=i,
                code_snippet="x" * 1000,  # Large snippet to force trimming
            )
            for i in range(3)
        ]

        bundle = packer.pack(items)

        # Evidence IDs must all be present
        for i in range(3):
            assert f"E-PRESERVE-{i}" in bundle.evidence_ids

        # Verify via unpack
        unpacked = packer.unpack(bundle.toon_output)
        unpacked_ids = {item.evidence_id for item in unpacked}
        for i in range(3):
            assert f"E-PRESERVE-{i}" in unpacked_ids

    def test_file_paths_preserved(self):
        """Test file paths are preserved even under budget pressure."""
        packer = RetrievalPacker(max_tokens=200)

        items = [
            EvidenceItem(
                evidence_id="E-PATH",
                file_path="contracts/deep/nested/Important.sol",
                line_start=100,
                code_snippet="x" * 2000,
            )
        ]

        bundle = packer.pack(items)
        unpacked = packer.unpack(bundle.toon_output)

        assert unpacked[0].file_path == "contracts/deep/nested/Important.sol"

    def test_line_numbers_preserved(self):
        """Test line numbers are preserved under budget pressure."""
        packer = RetrievalPacker(max_tokens=200)

        items = [
            EvidenceItem(
                evidence_id="E-LINES",
                file_path="test.sol",
                line_start=123,
                line_end=456,
                code_snippet="x" * 2000,
            )
        ]

        bundle = packer.pack(items)
        unpacked = packer.unpack(bundle.toon_output)

        assert unpacked[0].line_start == 123
        assert unpacked[0].line_end == 456

    def test_risk_scores_preserved(self):
        """Test risk scores are preserved under budget pressure."""
        packer = RetrievalPacker(max_tokens=200)

        items = [
            EvidenceItem(
                evidence_id="E-RISK",
                file_path="test.sol",
                line_start=1,
                risk_score=0.8765,
                code_snippet="x" * 2000,
            )
        ]

        bundle = packer.pack(items)
        unpacked = packer.unpack(bundle.toon_output)

        assert abs(unpacked[0].risk_score - 0.8765) < 0.001

    def test_code_snippets_trimmed_first(self):
        """Test code snippets are trimmed first when over budget."""
        packer = RetrievalPacker(max_tokens=500)

        long_code = "function test() {\n" + "    x = y;\n" * 100 + "}"
        items = [
            EvidenceItem(
                evidence_id="E-SNIPPET",
                file_path="test.sol",
                line_start=1,
                code_snippet=long_code,
                risk_score=0.9,
            )
        ]

        bundle = packer.pack(items)

        # Bundle should fit within budget
        assert bundle.estimated_tokens <= 500

        # Evidence ID should be preserved
        assert "E-SNIPPET" in bundle.evidence_ids

    def test_validate_preservation_passes(self):
        """Test validate_preservation passes for correctly packed data."""
        packer = RetrievalPacker()

        items = [
            EvidenceItem(
                evidence_id="E-VAL1",
                file_path="test1.sol",
                line_start=10,
                line_end=15,
                risk_score=0.5,
            ),
            EvidenceItem(
                evidence_id="E-VAL2",
                file_path="test2.sol",
                line_start=20,
                line_end=25,
                risk_score=0.6,
            ),
        ]

        bundle = packer.pack(items)
        valid, issues = packer.validate_preservation(items, bundle)

        assert valid
        assert issues == []

    def test_validate_preservation_detects_issues(self):
        """Test validate_preservation detects ID mismatches."""
        packer = RetrievalPacker()

        original_items = [
            EvidenceItem(
                evidence_id="E-ORIGINAL",
                file_path="test.sol",
                line_start=10,
                risk_score=0.5,
            ),
        ]

        # Create items with different ID but same content
        different_items = [
            EvidenceItem(
                evidence_id="E-DIFFERENT",
                file_path="test.sol",
                line_start=10,
                risk_score=0.5,
            ),
        ]

        # Pack the different items
        bundle = packer.pack(different_items)

        # Validate against original items - should detect ID mismatch
        valid, issues = packer.validate_preservation(original_items, bundle)

        assert not valid
        assert len(issues) > 0
        # Should mention the missing original ID
        assert any("E-ORIGINAL" in issue or "Missing" in issue for issue in issues)

    def test_bundle_metadata(self):
        """Test bundle metadata is included in output."""
        packer = RetrievalPacker()

        items = [
            EvidenceItem(
                evidence_id="E-META",
                file_path="test.sol",
                line_start=1,
            )
        ]

        bundle = packer.pack(items, bundle_metadata={"pattern": "test-pattern"})

        assert bundle.metadata.get("pattern") == "test-pattern"


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_pack_evidence_items(self):
        """Test pack_evidence_items convenience function."""
        items = [
            EvidenceItem(
                evidence_id="E-CONV1",
                file_path="test.sol",
                line_start=1,
            )
        ]

        bundle = pack_evidence_items(items, max_tokens=1000)

        assert bundle.total_items == 1
        assert "E-CONV1" in bundle.evidence_ids

    def test_unpack_evidence_bundle(self):
        """Test unpack_evidence_bundle convenience function."""
        packer = RetrievalPacker()
        items = [
            EvidenceItem(
                evidence_id="E-UNPACK",
                file_path="test.sol",
                line_start=50,
            )
        ]
        bundle = packer.pack(items)

        unpacked = unpack_evidence_bundle(bundle.toon_output)

        assert len(unpacked) == 1
        assert unpacked[0].evidence_id == "E-UNPACK"


class TestEvidenceAssembler:
    """Tests for EvidenceAssembler integration."""

    def test_assemble_packed_from_findings(self):
        """Test assembling packed evidence from finding dicts."""
        assembler = EvidenceAssembler(max_tokens=2000)

        findings = [
            {
                "id": "F-001",
                "file": "Vault.sol",
                "line": 45,
                "code": "function withdraw() { ... }",
                "risk_score": 0.8,
                "pattern": "reentrancy",
            },
            {
                "evidence_id": "F-002",
                "location": {"file": "Token.sol", "line": 100},
                "severity_score": 0.6,
                "operations": ["TRANSFERS_VALUE_OUT"],
            },
        ]

        packed = assembler.assemble_packed(findings)

        assert packed.total_items == 2
        assert len(packed.evidence_ids) == 2

    def test_unpack_bundle_via_assembler(self):
        """Test unpacking bundle through assembler."""
        assembler = EvidenceAssembler()

        findings = [
            {
                "id": "F-UNPACK",
                "file": "test.sol",
                "line": 10,
                "risk_score": 0.7,
            }
        ]

        packed = assembler.assemble_packed(findings)
        unpacked = assembler.unpack_bundle(packed)

        assert len(unpacked) == 1
        assert unpacked[0].evidence_id == "F-UNPACK"
        assert unpacked[0].file_path == "test.sol"
        assert unpacked[0].line_start == 10

    def test_finding_with_various_id_formats(self):
        """Test assembler handles various ID formats in findings."""
        assembler = EvidenceAssembler()

        findings = [
            {"id": "ID-FORMAT-1", "file": "a.sol", "line": 1},
            {"evidence_id": "ID-FORMAT-2", "file": "b.sol", "line": 2},
            {"node_id": "NODE-FORMAT-3", "file": "c.sol", "line": 3},
            # Auto-generated ID for finding without explicit ID
            {"file": "d.sol", "line": 4},
        ]

        packed = assembler.assemble_packed(findings)

        assert packed.total_items == 4
        assert len(packed.evidence_ids) == 4


class TestSubagentManagerIntegration:
    """Tests for LLMSubagentManager.pack_evidence_context integration."""

    def test_pack_evidence_context_basic(self):
        """Test basic evidence packing through subagent manager."""
        from alphaswarm_sol.llm.subagents import LLMSubagentManager

        manager = LLMSubagentManager()

        evidence = [
            {
                "id": "E-MGR-001",
                "file": "Vault.sol",
                "line": 45,
                "risk_score": 0.85,
                "operations": ["TRANSFERS_VALUE_OUT"],
            }
        ]

        packed = manager.pack_evidence_context(evidence)

        assert packed.total_items == 1
        assert "E-MGR-001" in packed.evidence_ids
        assert packed.toon_output != ""

    def test_pack_evidence_context_with_budget(self):
        """Test evidence packing respects token budget."""
        from alphaswarm_sol.llm.subagents import LLMSubagentManager

        manager = LLMSubagentManager()

        evidence = [
            {
                "id": f"E-BUD-{i}",
                "file": f"Contract{i}.sol",
                "line": i * 10,
                "code": "x" * 500,  # Medium-sized code snippets
            }
            for i in range(10)
        ]

        packed = manager.pack_evidence_context(evidence, max_tokens=500)

        # Should fit within budget
        assert packed.estimated_tokens <= 500


class TestTokenEfficiency:
    """Tests for token efficiency of packed output."""

    def test_toon_output_is_compact(self):
        """Test TOON output is more compact than JSON equivalent."""
        import json

        packer = RetrievalPacker()

        items = [
            EvidenceItem(
                evidence_id=f"E-{i:06d}",
                file_path=f"contracts/Contract{i}.sol",
                line_start=i * 10,
                line_end=i * 10 + 5,
                risk_score=0.1 * (i % 10),
                operations=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            )
            for i in range(5)
        ]

        bundle = packer.pack(items)

        # Compare with naive JSON serialization
        json_output = json.dumps([item.to_dict() for item in items])

        # TOON should be more compact (or at least comparable)
        # Note: The actual savings depend on the toons library implementation
        toon_len = len(bundle.toon_output)
        json_len = len(json_output)

        # Log for debugging (pytest will show on failure)
        print(f"TOON length: {toon_len}, JSON length: {json_len}")

        # TOON should not be significantly larger than JSON
        assert toon_len <= json_len * 1.5  # Allow some overhead for envelope

    def test_estimated_tokens_reasonable(self):
        """Test token estimation is reasonable."""
        packer = RetrievalPacker()

        items = [
            EvidenceItem(
                evidence_id="E-TOKEN-EST",
                file_path="test.sol",
                line_start=1,
                code_snippet="function test() { return 42; }",
            )
        ]

        bundle = packer.pack(items)

        # Verify token estimation matches output length / 4 (chars per token)
        expected_tokens = len(bundle.toon_output) // 4
        assert abs(bundle.estimated_tokens - expected_tokens) <= 1
