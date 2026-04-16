"""Tests for VulnKnowledgeDoc and multi-model pipeline schema.

Task 18.2: Tests for the knowledge document schema.
"""

import unittest
from datetime import datetime

from alphaswarm_sol.vulndocs.knowledge_doc import (
    DetectionSection,
    DocMetadata,
    ExamplesSection,
    ExploitationSection,
    MergeConflict,
    MergeResult,
    MitigationSection,
    PatternLinkage,
    PatternLinkageType,
    Prevalence,
    RealExploitRef,
    Severity,
    SourceSummary,
    UniqueIdea,
    VulnKnowledgeDoc,
)


class TestPatternLinkageType(unittest.TestCase):
    """Tests for PatternLinkageType enum."""

    def test_from_string_valid(self):
        """Test parsing valid linkage types."""
        self.assertEqual(
            PatternLinkageType.from_string("exact_match"),
            PatternLinkageType.EXACT_MATCH,
        )
        self.assertEqual(
            PatternLinkageType.from_string("partial_match"),
            PatternLinkageType.PARTIAL_MATCH,
        )
        self.assertEqual(
            PatternLinkageType.from_string("theoretical"),
            PatternLinkageType.THEORETICAL,
        )
        self.assertEqual(
            PatternLinkageType.from_string("requires_llm"),
            PatternLinkageType.REQUIRES_LLM,
        )
        self.assertEqual(
            PatternLinkageType.from_string("composite"),
            PatternLinkageType.COMPOSITE,
        )

    def test_from_string_invalid(self):
        """Test parsing invalid linkage type defaults to THEORETICAL."""
        self.assertEqual(
            PatternLinkageType.from_string("invalid"),
            PatternLinkageType.THEORETICAL,
        )


class TestSeverity(unittest.TestCase):
    """Tests for Severity enum."""

    def test_from_string_valid(self):
        """Test parsing valid severity levels."""
        self.assertEqual(Severity.from_string("critical"), Severity.CRITICAL)
        self.assertEqual(Severity.from_string("high"), Severity.HIGH)
        self.assertEqual(Severity.from_string("medium"), Severity.MEDIUM)
        self.assertEqual(Severity.from_string("low"), Severity.LOW)

    def test_from_string_case_insensitive(self):
        """Test case-insensitive parsing."""
        self.assertEqual(Severity.from_string("CRITICAL"), Severity.CRITICAL)
        self.assertEqual(Severity.from_string("High"), Severity.HIGH)

    def test_from_string_invalid(self):
        """Test invalid severity defaults to MEDIUM."""
        self.assertEqual(Severity.from_string("invalid"), Severity.MEDIUM)


class TestDetectionSection(unittest.TestCase):
    """Tests for DetectionSection dataclass."""

    def test_create_empty(self):
        """Test creating empty detection section."""
        section = DetectionSection()
        self.assertEqual(section.graph_signals, [])
        self.assertEqual(section.vulnerable_sequence, "")

    def test_create_with_data(self):
        """Test creating detection section with data."""
        section = DetectionSection(
            graph_signals=["state_write_after_external_call"],
            vulnerable_sequence="R:bal -> X:out -> W:bal",
            safe_sequence="R:bal -> W:bal -> X:out",
            indicators=["external call before state update"],
            checklist=["Check call ordering"],
        )
        self.assertEqual(len(section.graph_signals), 1)
        self.assertIn("R:bal", section.vulnerable_sequence)

    def test_to_dict_round_trip(self):
        """Test serialization round trip."""
        section = DetectionSection(
            graph_signals=["test_signal"],
            vulnerable_sequence="test",
        )
        data = section.to_dict()
        restored = DetectionSection.from_dict(data)
        self.assertEqual(section.graph_signals, restored.graph_signals)

    def test_to_markdown(self):
        """Test markdown generation."""
        section = DetectionSection(
            graph_signals=["signal1", "signal2"],
            checklist=["Check 1", "Check 2"],
        )
        md = section.to_markdown()
        self.assertIn("## Detection", md)
        self.assertIn("signal1", md)
        self.assertIn("Check 1", md)


class TestExploitationSection(unittest.TestCase):
    """Tests for ExploitationSection dataclass."""

    def test_create_with_data(self):
        """Test creating exploitation section."""
        section = ExploitationSection(
            attack_vector="Deploy malicious contract",
            prerequisites=["Contract deployment capability"],
            attack_steps=["Deploy attacker", "Call target", "Reenter"],
            potential_impact="Fund drain",
            monetary_risk="critical",
        )
        self.assertEqual(len(section.attack_steps), 3)

    def test_to_markdown(self):
        """Test markdown generation."""
        section = ExploitationSection(
            attack_vector="Test attack",
            attack_steps=["Step 1", "Step 2"],
        )
        md = section.to_markdown()
        self.assertIn("## Exploitation", md)
        self.assertIn("Test attack", md)
        self.assertIn("1.", md)


class TestMitigationSection(unittest.TestCase):
    """Tests for MitigationSection dataclass."""

    def test_create_with_data(self):
        """Test creating mitigation section."""
        section = MitigationSection(
            primary_fix="Use reentrancy guard",
            alternative_fixes=["Use CEI pattern", "Use mutex"],
            safe_pattern="nonReentrant",
            how_to_verify=["Run tests", "Manual review"],
        )
        self.assertEqual(section.primary_fix, "Use reentrancy guard")
        self.assertEqual(len(section.alternative_fixes), 2)


class TestExamplesSection(unittest.TestCase):
    """Tests for ExamplesSection dataclass."""

    def test_create_with_code(self):
        """Test creating examples with code."""
        section = ExamplesSection(
            vulnerable_code="function withdraw() { msg.sender.call{value: bal}(); balances[msg.sender] = 0; }",
            vulnerable_code_explanation="State update after external call",
            fixed_code="function withdraw() { uint bal = balances[msg.sender]; balances[msg.sender] = 0; msg.sender.call{value: bal}(); }",
            fixed_code_explanation="CEI pattern applied",
        )
        self.assertIn("call", section.vulnerable_code)

    def test_with_real_exploits(self):
        """Test adding real exploit references."""
        exploit = RealExploitRef(
            name="The DAO Hack",
            date="2016-06-17",
            loss="$60M",
            protocol="The DAO",
            brief="Classic reentrancy attack",
        )
        section = ExamplesSection(
            real_exploits=[exploit],
        )
        self.assertEqual(len(section.real_exploits), 1)
        self.assertEqual(section.real_exploits[0].loss, "$60M")


class TestRealExploitRef(unittest.TestCase):
    """Tests for RealExploitRef dataclass."""

    def test_to_inline(self):
        """Test inline format generation."""
        exploit = RealExploitRef(
            name="Test Hack",
            date="2024-01-01",
            loss="$10M",
            protocol="TestProtocol",
        )
        inline = exploit.to_inline()
        self.assertIn("Test Hack", inline)
        self.assertIn("2024-01-01", inline)
        self.assertIn("$10M", inline)


class TestPatternLinkage(unittest.TestCase):
    """Tests for PatternLinkage dataclass."""

    def test_exact_match(self):
        """Test exact match linkage."""
        linkage = PatternLinkage(
            linkage_type=PatternLinkageType.EXACT_MATCH,
            pattern_ids=["reentrancy-001", "reentrancy-002"],
            coverage_pct=0.95,
        )
        self.assertEqual(len(linkage.pattern_ids), 2)
        self.assertEqual(linkage.coverage_pct, 0.95)

    def test_theoretical(self):
        """Test theoretical linkage."""
        linkage = PatternLinkage(
            linkage_type=PatternLinkageType.THEORETICAL,
            why_no_pattern="Requires semantic understanding",
            manual_hints=["Check business logic", "Review invariants"],
        )
        self.assertIsNotNone(linkage.why_no_pattern)
        self.assertEqual(len(linkage.manual_hints), 2)

    def test_composite(self):
        """Test composite linkage."""
        linkage = PatternLinkage(
            linkage_type=PatternLinkageType.COMPOSITE,
            composite_patterns=["flash-loan-001", "oracle-001"],
            combination_logic="AND",
        )
        self.assertEqual(len(linkage.composite_patterns), 2)


class TestVulnKnowledgeDoc(unittest.TestCase):
    """Tests for VulnKnowledgeDoc dataclass."""

    def test_create_minimal(self):
        """Test creating minimal document."""
        doc = VulnKnowledgeDoc(
            id="reentrancy/classic",
            name="Classic Reentrancy",
            category="reentrancy",
            subcategory="classic-reentrancy",
        )
        self.assertEqual(doc.category, "reentrancy")
        self.assertIsNotNone(doc.metadata.content_hash)
        self.assertIsNotNone(doc.metadata.last_updated)

    def test_create_full(self):
        """Test creating full document."""
        doc = VulnKnowledgeDoc(
            id="reentrancy/classic/state-after-call",
            name="State Write After External Call",
            category="reentrancy",
            subcategory="classic-reentrancy",
            severity=Severity.CRITICAL,
            prevalence=Prevalence.VERY_COMMON,
            one_liner="State update after external call allows reentrancy",
            tldr="This vulnerability occurs when...",
            detection=DetectionSection(
                graph_signals=["state_write_after_external_call"],
            ),
            exploitation=ExploitationSection(
                attack_vector="Deploy malicious contract",
            ),
            mitigation=MitigationSection(
                primary_fix="Use reentrancy guard",
            ),
            examples=ExamplesSection(
                vulnerable_code="...",
            ),
            pattern_linkage=PatternLinkage(
                linkage_type=PatternLinkageType.EXACT_MATCH,
                pattern_ids=["reentrancy-001"],
            ),
        )
        self.assertEqual(doc.severity, Severity.CRITICAL)

    def test_to_dict_round_trip(self):
        """Test serialization round trip."""
        doc = VulnKnowledgeDoc(
            id="test/test",
            name="Test",
            category="test",
            subcategory="test",
            one_liner="Test vulnerability",
        )
        data = doc.to_dict()
        restored = VulnKnowledgeDoc.from_dict(data)
        self.assertEqual(doc.id, restored.id)
        self.assertEqual(doc.name, restored.name)
        self.assertEqual(doc.one_liner, restored.one_liner)

    def test_to_markdown(self):
        """Test markdown generation."""
        doc = VulnKnowledgeDoc(
            id="reentrancy/classic",
            name="Classic Reentrancy",
            category="reentrancy",
            subcategory="classic",
            severity=Severity.CRITICAL,
            one_liner="Test vulnerability",
        )
        md = doc.to_markdown()
        self.assertIn("# Classic Reentrancy", md)
        self.assertIn("critical", md)

    def test_to_compact_context(self):
        """Test compact context generation."""
        doc = VulnKnowledgeDoc(
            id="test/test",
            name="Test",
            category="test",
            subcategory="test",
            one_liner="Short description",
            detection=DetectionSection(
                graph_signals=["signal1", "signal2"],
            ),
            mitigation=MitigationSection(
                primary_fix="Fix it",
            ),
        )
        compact = doc.to_compact_context(max_tokens=200)
        self.assertIn("Test", compact)
        self.assertIn("signal1", compact)
        self.assertLess(len(compact), 1000)

    def test_estimate_tokens(self):
        """Test token estimation."""
        doc = VulnKnowledgeDoc(
            id="test/test",
            name="Test",
            category="test",
            subcategory="test",
        )
        tokens = doc.estimate_tokens()
        self.assertGreater(tokens, 0)

    def test_get_section(self):
        """Test getting individual sections."""
        doc = VulnKnowledgeDoc(
            id="test/test",
            name="Test",
            category="test",
            subcategory="test",
            detection=DetectionSection(
                graph_signals=["test_signal"],
            ),
        )
        detection_md = doc.get_section("detection")
        self.assertIn("Detection", detection_md)
        self.assertIn("test_signal", detection_md)


class TestSourceSummary(unittest.TestCase):
    """Tests for SourceSummary dataclass."""

    def test_create(self):
        """Test creating source summary."""
        summary = SourceSummary(
            source_url="https://example.com/audit",
            source_name="Example Audit",
            category="reentrancy",
            subcategory="classic",
            key_points=["Point 1", "Point 2"],
            attack_vector="Test attack",
        )
        self.assertEqual(len(summary.key_points), 2)

    def test_to_dict_round_trip(self):
        """Test serialization round trip."""
        summary = SourceSummary(
            source_url="https://test.com",
            source_name="Test",
            category="test",
            subcategory="test",
            missing_fields=["attack_vector", "mitigation"],
        )
        data = summary.to_dict()
        restored = SourceSummary.from_dict(data)
        self.assertEqual(summary.source_url, restored.source_url)
        self.assertEqual(summary.missing_fields, restored.missing_fields)


class TestMergeResult(unittest.TestCase):
    """Tests for MergeResult dataclass."""

    def test_create(self):
        """Test creating merge result."""
        doc = VulnKnowledgeDoc(
            id="test/test",
            name="Test",
            category="test",
            subcategory="test",
        )
        idea = UniqueIdea(
            id="idea1",
            description="Test idea",
            source_urls=["https://test.com"],
            category="test",
            idea_type="detection",
            merged=True,
        )
        result = MergeResult(
            subcategory_id="test/test",
            document=doc,
            unique_ideas=[idea],
            conflicts=[],
            source_count=5,
        )
        self.assertEqual(result.source_count, 5)
        self.assertIsNotNone(result.merge_timestamp)

    def test_get_unmerged_ideas(self):
        """Test getting unmerged ideas."""
        doc = VulnKnowledgeDoc(
            id="test/test",
            name="Test",
            category="test",
            subcategory="test",
        )
        ideas = [
            UniqueIdea(id="1", description="Merged", source_urls=[], category="test", idea_type="detection", merged=True),
            UniqueIdea(id="2", description="Not merged", source_urls=[], category="test", idea_type="detection", merged=False),
        ]
        result = MergeResult(
            subcategory_id="test",
            document=doc,
            unique_ideas=ideas,
            conflicts=[],
            source_count=1,
        )
        unmerged = result.get_unmerged_ideas()
        self.assertEqual(len(unmerged), 1)
        self.assertEqual(unmerged[0].id, "2")


class TestMergeConflict(unittest.TestCase):
    """Tests for MergeConflict dataclass."""

    def test_create(self):
        """Test creating merge conflict."""
        conflict = MergeConflict(
            conflict_id="conflict-1",
            description="Conflicting mitigation advice",
            claim_a="Use reentrancy guard",
            source_a="https://source-a.com",
            authority_a=0.95,
            claim_b="Use mutex pattern",
            source_b="https://source-b.com",
            authority_b=0.85,
        )
        self.assertEqual(conflict.authority_a, 0.95)

    def test_to_dict(self):
        """Test serialization."""
        conflict = MergeConflict(
            conflict_id="test",
            description="Test conflict",
            claim_a="A",
            source_a="a",
            authority_a=0.5,
            claim_b="B",
            source_b="b",
            authority_b=0.5,
        )
        data = conflict.to_dict()
        self.assertEqual(data["conflict_id"], "test")


if __name__ == "__main__":
    unittest.main()
