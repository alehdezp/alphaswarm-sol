"""Tests for VulnDocs Knowledge Schema (Phase 17.0).

Tests for the knowledge/vulndocs schema module located at:
    src/alphaswarm_sol/knowledge/vulndocs/schema.py

This module tests:
1. Schema parsing (YAML -> Python objects)
2. Category/subcategory validation
3. Document structure validation
4. Index loading and navigation
5. Serialization round-trips
"""

import unittest
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from alphaswarm_sol.knowledge.vulndocs.schema import (
    # Core dataclasses
    Category,
    Subcategory,
    SubcategoryRef,
    Document,
    KnowledgeIndex,
    GraphSignal,
    CodePattern,
    ExploitReference,
    FixRecommendation,
    OperationSequences,
    NavigationMetadata,
    CacheConfig,
    # Enums
    Severity,
    KnowledgeDepth,
    DocumentType,
    CacheControlType,
    # Loading functions
    load_index,
    load_category,
    load_subcategory,
    # Validation functions
    validate_category,
    validate_subcategory,
    validate_document,
    validate_index,
    validate_id,
    validate_severity_range,
    # Constants
    SCHEMA_VERSION,
    KNOWLEDGE_DIR,
)


class TestSeverityEnum(unittest.TestCase):
    """Tests for Severity enum."""

    def test_from_string_valid(self):
        """Test parsing valid severity levels."""
        self.assertEqual(Severity.from_string("critical"), Severity.CRITICAL)
        self.assertEqual(Severity.from_string("high"), Severity.HIGH)
        self.assertEqual(Severity.from_string("medium"), Severity.MEDIUM)
        self.assertEqual(Severity.from_string("low"), Severity.LOW)
        self.assertEqual(Severity.from_string("informational"), Severity.INFORMATIONAL)

    def test_from_string_case_insensitive(self):
        """Test case-insensitive parsing."""
        self.assertEqual(Severity.from_string("CRITICAL"), Severity.CRITICAL)
        self.assertEqual(Severity.from_string("High"), Severity.HIGH)
        self.assertEqual(Severity.from_string("MEDIUM"), Severity.MEDIUM)

    def test_from_string_invalid(self):
        """Test invalid severity defaults to MEDIUM."""
        self.assertEqual(Severity.from_string("invalid"), Severity.MEDIUM)
        self.assertEqual(Severity.from_string("unknown"), Severity.MEDIUM)
        self.assertEqual(Severity.from_string(""), Severity.MEDIUM)


class TestKnowledgeDepthEnum(unittest.TestCase):
    """Tests for KnowledgeDepth enum."""

    def test_from_string_valid(self):
        """Test parsing valid depth levels."""
        self.assertEqual(KnowledgeDepth.from_string("index"), KnowledgeDepth.INDEX)
        self.assertEqual(KnowledgeDepth.from_string("overview"), KnowledgeDepth.OVERVIEW)
        self.assertEqual(KnowledgeDepth.from_string("detection"), KnowledgeDepth.DETECTION)
        self.assertEqual(KnowledgeDepth.from_string("patterns"), KnowledgeDepth.PATTERNS)
        self.assertEqual(KnowledgeDepth.from_string("exploits"), KnowledgeDepth.EXPLOITS)
        self.assertEqual(KnowledgeDepth.from_string("fixes"), KnowledgeDepth.FIXES)
        self.assertEqual(KnowledgeDepth.from_string("full"), KnowledgeDepth.FULL)

    def test_from_string_invalid(self):
        """Test invalid depth defaults to DETECTION."""
        self.assertEqual(KnowledgeDepth.from_string("invalid"), KnowledgeDepth.DETECTION)
        self.assertEqual(KnowledgeDepth.from_string("unknown"), KnowledgeDepth.DETECTION)

    def test_token_estimate(self):
        """Test token estimate property."""
        self.assertEqual(KnowledgeDepth.INDEX.token_estimate, 200)
        self.assertEqual(KnowledgeDepth.OVERVIEW.token_estimate, 500)
        self.assertEqual(KnowledgeDepth.DETECTION.token_estimate, 1000)
        self.assertEqual(KnowledgeDepth.PATTERNS.token_estimate, 1500)
        self.assertEqual(KnowledgeDepth.EXPLOITS.token_estimate, 1000)
        self.assertEqual(KnowledgeDepth.FIXES.token_estimate, 800)
        self.assertEqual(KnowledgeDepth.FULL.token_estimate, 5000)


class TestDocumentTypeEnum(unittest.TestCase):
    """Tests for DocumentType enum."""

    def test_from_string_valid(self):
        """Test parsing valid document types."""
        self.assertEqual(DocumentType.from_string("index"), DocumentType.INDEX)
        self.assertEqual(DocumentType.from_string("detection"), DocumentType.DETECTION)
        self.assertEqual(DocumentType.from_string("patterns"), DocumentType.PATTERNS)
        self.assertEqual(DocumentType.from_string("exploits"), DocumentType.EXPLOITS)
        self.assertEqual(DocumentType.from_string("fixes"), DocumentType.FIXES)

    def test_from_string_invalid(self):
        """Test invalid type defaults to INDEX."""
        self.assertEqual(DocumentType.from_string("invalid"), DocumentType.INDEX)


class TestGraphSignal(unittest.TestCase):
    """Tests for GraphSignal dataclass."""

    def test_create_minimal(self):
        """Test creating minimal graph signal."""
        signal = GraphSignal(property_name="test_property", expected=True)
        self.assertEqual(signal.property_name, "test_property")
        self.assertEqual(signal.expected, True)
        self.assertFalse(signal.critical)
        self.assertEqual(signal.description, "")
        self.assertEqual(signal.confidence, 0.8)

    def test_create_full(self):
        """Test creating full graph signal."""
        signal = GraphSignal(
            property_name="state_write_after_external_call",
            expected=True,
            critical=True,
            description="Function writes state after external call",
            confidence=0.95,
        )
        self.assertEqual(signal.property_name, "state_write_after_external_call")
        self.assertTrue(signal.critical)
        self.assertEqual(signal.confidence, 0.95)

    def test_to_dict(self):
        """Test serialization to dictionary."""
        signal = GraphSignal(
            property_name="test",
            expected=True,
            critical=True,
            description="Test description",
            confidence=0.9,
        )
        data = signal.to_dict()
        self.assertEqual(data["property"], "test")
        self.assertEqual(data["expected"], True)
        self.assertEqual(data["critical"], True)
        self.assertEqual(data["description"], "Test description")
        self.assertEqual(data["confidence"], 0.9)

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "property": "has_reentrancy_guard",
            "expected": False,
            "critical": True,
            "description": "No reentrancy protection",
            "confidence": 0.85,
        }
        signal = GraphSignal.from_dict(data)
        self.assertEqual(signal.property_name, "has_reentrancy_guard")
        self.assertEqual(signal.expected, False)
        self.assertTrue(signal.critical)
        self.assertEqual(signal.confidence, 0.85)

    def test_round_trip(self):
        """Test serialization round-trip."""
        original = GraphSignal(
            property_name="visibility",
            expected=["public", "external"],
            critical=True,
            description="Must be public or external",
            confidence=0.95,
        )
        data = original.to_dict()
        restored = GraphSignal.from_dict(data)
        self.assertEqual(original.property_name, restored.property_name)
        self.assertEqual(original.expected, restored.expected)
        self.assertEqual(original.critical, restored.critical)


class TestCodePattern(unittest.TestCase):
    """Tests for CodePattern dataclass."""

    def test_create_minimal(self):
        """Test creating minimal code pattern."""
        pattern = CodePattern(name="Test Pattern", vulnerable_code="// vulnerable")
        self.assertEqual(pattern.name, "Test Pattern")
        self.assertEqual(pattern.vulnerable_code, "// vulnerable")
        self.assertEqual(pattern.safe_code, "")
        self.assertEqual(pattern.severity, "medium")

    def test_create_full(self):
        """Test creating full code pattern."""
        pattern = CodePattern(
            name="Classic Reentrancy",
            vulnerable_code="msg.sender.call{value: bal}('');",
            safe_code="balances[msg.sender] = 0; msg.sender.call{value: bal}('');",
            description="State write after external call",
            severity="critical",
        )
        self.assertEqual(pattern.name, "Classic Reentrancy")
        self.assertEqual(pattern.severity, "critical")
        self.assertIn("call", pattern.vulnerable_code)

    def test_round_trip(self):
        """Test serialization round-trip."""
        original = CodePattern(
            name="Test",
            vulnerable_code="vuln code",
            safe_code="safe code",
            description="Test description",
            severity="high",
        )
        data = original.to_dict()
        restored = CodePattern.from_dict(data)
        self.assertEqual(original.name, restored.name)
        self.assertEqual(original.vulnerable_code, restored.vulnerable_code)
        self.assertEqual(original.safe_code, restored.safe_code)


class TestExploitReference(unittest.TestCase):
    """Tests for ExploitReference dataclass."""

    def test_create_minimal(self):
        """Test creating minimal exploit reference."""
        exploit = ExploitReference(id="dao-hack", name="The DAO Hack")
        self.assertEqual(exploit.id, "dao-hack")
        self.assertEqual(exploit.name, "The DAO Hack")
        self.assertEqual(exploit.chain, "ethereum")

    def test_create_full(self):
        """Test creating full exploit reference."""
        exploit = ExploitReference(
            id="dao-hack",
            name="The DAO Hack",
            date="2016-06-17",
            loss_usd="60000000",
            protocol="The DAO",
            chain="ethereum",
            category="reentrancy",
            subcategory="classic",
            description="Classic reentrancy exploit",
            attack_steps=["Step 1", "Step 2"],
            postmortem_url="https://example.com/postmortem",
            pattern_ids=["vm-001"],
        )
        self.assertEqual(exploit.loss_usd, "60000000")
        self.assertEqual(len(exploit.attack_steps), 2)
        self.assertEqual(exploit.pattern_ids, ["vm-001"])

    def test_round_trip(self):
        """Test serialization round-trip."""
        original = ExploitReference(
            id="test-exploit",
            name="Test Exploit",
            date="2024-01-01",
            loss_usd="1000000",
            attack_steps=["Step 1", "Step 2"],
        )
        data = original.to_dict()
        restored = ExploitReference.from_dict(data)
        self.assertEqual(original.id, restored.id)
        self.assertEqual(original.loss_usd, restored.loss_usd)
        self.assertEqual(original.attack_steps, restored.attack_steps)


class TestFixRecommendation(unittest.TestCase):
    """Tests for FixRecommendation dataclass."""

    def test_create_minimal(self):
        """Test creating minimal fix recommendation."""
        fix = FixRecommendation(name="Use ReentrancyGuard", description="Add OpenZeppelin guard")
        self.assertEqual(fix.name, "Use ReentrancyGuard")
        self.assertEqual(fix.effectiveness, "high")
        self.assertEqual(fix.complexity, "low")

    def test_round_trip(self):
        """Test serialization round-trip."""
        original = FixRecommendation(
            name="CEI Pattern",
            description="Check-Effects-Interactions",
            code_example="balances[msg.sender] = 0; msg.sender.call{value: bal}('');",
            effectiveness="high",
            complexity="medium",
        )
        data = original.to_dict()
        restored = FixRecommendation.from_dict(data)
        self.assertEqual(original.name, restored.name)
        self.assertEqual(original.code_example, restored.code_example)


class TestOperationSequences(unittest.TestCase):
    """Tests for OperationSequences dataclass."""

    def test_create_empty(self):
        """Test creating empty sequences."""
        seq = OperationSequences()
        self.assertEqual(seq.vulnerable, [])
        self.assertEqual(seq.safe, [])

    def test_create_with_data(self):
        """Test creating sequences with data."""
        seq = OperationSequences(
            vulnerable=["R:bal -> X:out -> W:bal"],
            safe=["R:bal -> W:bal -> X:out"],
        )
        self.assertEqual(len(seq.vulnerable), 1)
        self.assertEqual(len(seq.safe), 1)

    def test_round_trip(self):
        """Test serialization round-trip."""
        original = OperationSequences(
            vulnerable=["V1", "V2"],
            safe=["S1"],
        )
        data = original.to_dict()
        restored = OperationSequences.from_dict(data)
        self.assertEqual(original.vulnerable, restored.vulnerable)
        self.assertEqual(original.safe, restored.safe)


class TestSubcategory(unittest.TestCase):
    """Tests for Subcategory dataclass."""

    def test_create_minimal(self):
        """Test creating minimal subcategory."""
        sub = Subcategory(
            id="classic",
            name="Classic Reentrancy",
            description="State write after external call",
            parent_category="reentrancy",
        )
        self.assertEqual(sub.id, "classic")
        self.assertEqual(sub.parent_category, "reentrancy")
        self.assertEqual(sub.severity_range, ["medium", "high"])
        self.assertEqual(sub.token_estimate, 500)

    def test_create_full(self):
        """Test creating full subcategory."""
        sub = Subcategory(
            id="classic",
            name="Classic Reentrancy",
            description="State write after external call",
            parent_category="reentrancy",
            severity_range=["high", "critical"],
            patterns=["vm-001", "vm-002"],
            relevant_properties=["state_write_after_external_call"],
            graph_signals=[
                GraphSignal(property_name="state_write_after_external_call", expected=True, critical=True),
            ],
            behavioral_signatures=["R:bal.*X:out.*W:bal"],
            operation_sequences=OperationSequences(
                vulnerable=["R:bal -> X:out -> W:bal"],
                safe=["R:bal -> W:bal -> X:out"],
            ),
            false_positive_indicators=["nonReentrant modifier"],
            token_estimate=800,
        )
        self.assertEqual(len(sub.graph_signals), 1)
        self.assertEqual(len(sub.behavioral_signatures), 1)
        self.assertIsNotNone(sub.operation_sequences)

    def test_get_detection_context(self):
        """Test generating detection context."""
        sub = Subcategory(
            id="classic",
            name="Classic Reentrancy",
            description="Test description",
            parent_category="reentrancy",
            severity_range=["high", "critical"],
            graph_signals=[
                GraphSignal(property_name="test_prop", expected=True, critical=True),
            ],
            behavioral_signatures=["R:bal.*X:out.*W:bal"],
            false_positive_indicators=["Has guard"],
        )
        context = sub.get_detection_context()
        self.assertIn("Classic Reentrancy", context)
        self.assertIn("Graph Signals", context)
        self.assertIn("test_prop", context)
        self.assertIn("Behavioral Signatures", context)
        self.assertIn("False Positive Indicators", context)

    def test_round_trip(self):
        """Test serialization round-trip."""
        original = Subcategory(
            id="test-sub",
            name="Test Subcategory",
            description="Test description",
            parent_category="test-cat",
            patterns=["p1", "p2"],
            graph_signals=[GraphSignal(property_name="test", expected=True)],
        )
        data = original.to_dict()
        restored = Subcategory.from_dict(data)
        self.assertEqual(original.id, restored.id)
        self.assertEqual(original.patterns, restored.patterns)
        self.assertEqual(len(original.graph_signals), len(restored.graph_signals))


class TestCategory(unittest.TestCase):
    """Tests for Category dataclass."""

    def test_create_minimal(self):
        """Test creating minimal category."""
        cat = Category(
            id="reentrancy",
            name="Reentrancy",
            description="Callback exploitation",
        )
        self.assertEqual(cat.id, "reentrancy")
        self.assertEqual(cat.context_cache_key, "reentrancy-v1")
        self.assertEqual(cat.path, "categories/reentrancy/")

    def test_create_full(self):
        """Test creating full category."""
        cat = Category(
            id="reentrancy",
            name="Reentrancy Vulnerabilities",
            description="Attacks exploiting callback mechanisms",
            severity_range=["high", "critical"],
            subcategories=[
                SubcategoryRef(id="classic", name="Classic", description="Basic reentrancy"),
                SubcategoryRef(id="cross-function", name="Cross-Function", description="Multi-function"),
            ],
            relevant_properties=["state_write_after_external_call"],
            semantic_operations=["TRANSFERS_VALUE_OUT"],
            context_cache_key="reentrancy-v2",
            token_estimate=2000,
        )
        self.assertEqual(len(cat.subcategories), 2)
        self.assertEqual(cat.context_cache_key, "reentrancy-v2")

    def test_get_subcategory(self):
        """Test getting subcategory by ID."""
        cat = Category(
            id="test",
            name="Test",
            description="Test",
            subcategories=[
                SubcategoryRef(id="sub1", name="Sub1", description="First"),
                SubcategoryRef(id="sub2", name="Sub2", description="Second"),
            ],
        )
        sub = cat.get_subcategory("sub1")
        self.assertIsNotNone(sub)
        self.assertEqual(sub.id, "sub1")

        none_sub = cat.get_subcategory("nonexistent")
        self.assertIsNone(none_sub)

    def test_get_subcategory_ids(self):
        """Test getting subcategory IDs."""
        cat = Category(
            id="test",
            name="Test",
            description="Test",
            subcategories=[
                SubcategoryRef(id="sub1", name="Sub1", description="First"),
                SubcategoryRef(id="sub2", name="Sub2", description="Second"),
            ],
        )
        ids = cat.get_subcategory_ids()
        self.assertEqual(ids, ["sub1", "sub2"])

    def test_get_overview_context(self):
        """Test generating overview context."""
        cat = Category(
            id="reentrancy",
            name="Reentrancy",
            description="Callback exploitation attacks",
            subcategories=[
                SubcategoryRef(id="classic", name="Classic", description="Basic"),
            ],
            relevant_properties=["prop1"],
        )
        context = cat.get_overview_context()
        self.assertIn("Reentrancy", context)
        self.assertIn("Subcategories", context)
        self.assertIn("classic", context)
        self.assertIn("prop1", context)

    def test_round_trip(self):
        """Test serialization round-trip."""
        original = Category(
            id="test-cat",
            name="Test Category",
            description="Test description",
            subcategories=[
                SubcategoryRef(id="sub1", name="Sub1", description="First"),
            ],
            relevant_properties=["prop1", "prop2"],
        )
        data = original.to_dict()
        restored = Category.from_dict(data)
        self.assertEqual(original.id, restored.id)
        self.assertEqual(len(original.subcategories), len(restored.subcategories))

    def test_from_dict_with_string_subcategories(self):
        """Test parsing subcategories as string IDs."""
        data = {
            "id": "test",
            "name": "Test",
            "description": "Test",
            "subcategories": ["sub1", "sub2", "sub3"],
        }
        cat = Category.from_dict(data)
        self.assertEqual(len(cat.subcategories), 3)
        self.assertEqual(cat.subcategories[0].id, "sub1")


class TestDocument(unittest.TestCase):
    """Tests for Document dataclass."""

    def test_create_minimal(self):
        """Test creating minimal document."""
        doc = Document(
            subcategory_id="classic",
            document_type=DocumentType.DETECTION,
        )
        self.assertEqual(doc.subcategory_id, "classic")
        self.assertEqual(doc.document_type, DocumentType.DETECTION)

    def test_create_detection_document(self):
        """Test creating detection document."""
        doc = Document(
            subcategory_id="classic",
            document_type=DocumentType.DETECTION,
            graph_signals=[
                GraphSignal(property_name="test", expected=True, critical=True),
            ],
            operation_sequences=OperationSequences(
                vulnerable=["V1"],
                safe=["S1"],
            ),
            behavioral_signatures=["R:bal.*X:out.*W:bal"],
            false_positive_indicators=["Has guard"],
        )
        markdown = doc.to_markdown()
        self.assertIn("Detection: classic", markdown)
        self.assertIn("Graph Signals", markdown)
        self.assertIn("Operation Sequences", markdown)

    def test_create_patterns_document(self):
        """Test creating patterns document."""
        doc = Document(
            subcategory_id="classic",
            document_type=DocumentType.PATTERNS,
            code_patterns=[
                CodePattern(
                    name="Basic Reentrancy",
                    vulnerable_code="// vuln",
                    safe_code="// safe",
                ),
            ],
            associated_pattern_ids=["vm-001"],
        )
        markdown = doc.to_markdown()
        self.assertIn("Patterns: classic", markdown)
        self.assertIn("Basic Reentrancy", markdown)
        self.assertIn("vm-001", markdown)

    def test_create_exploits_document(self):
        """Test creating exploits document."""
        doc = Document(
            subcategory_id="classic",
            document_type=DocumentType.EXPLOITS,
            exploits=[
                ExploitReference(
                    id="dao",
                    name="The DAO Hack",
                    date="2016-06-17",
                    loss_usd="60000000",
                    description="Classic reentrancy",
                ),
            ],
        )
        markdown = doc.to_markdown()
        self.assertIn("Exploits: classic", markdown)
        self.assertIn("The DAO Hack", markdown)
        self.assertIn("60000000", markdown)

    def test_create_fixes_document(self):
        """Test creating fixes document."""
        doc = Document(
            subcategory_id="classic",
            document_type=DocumentType.FIXES,
            fixes=[
                FixRecommendation(
                    name="Use ReentrancyGuard",
                    description="Add OpenZeppelin guard",
                    effectiveness="high",
                ),
            ],
        )
        markdown = doc.to_markdown()
        self.assertIn("Fixes: classic", markdown)
        self.assertIn("ReentrancyGuard", markdown)

    def test_round_trip(self):
        """Test serialization round-trip."""
        original = Document(
            subcategory_id="test",
            document_type=DocumentType.DETECTION,
            graph_signals=[GraphSignal(property_name="test", expected=True)],
        )
        data = original.to_dict()
        restored = Document.from_dict(data)
        self.assertEqual(original.subcategory_id, restored.subcategory_id)
        self.assertEqual(original.document_type, restored.document_type)


class TestKnowledgeIndex(unittest.TestCase):
    """Tests for KnowledgeIndex dataclass."""

    def test_create_empty(self):
        """Test creating empty index."""
        index = KnowledgeIndex()
        self.assertEqual(index.version, SCHEMA_VERSION)
        self.assertEqual(len(index.categories), 0)

    def test_create_with_categories(self):
        """Test creating index with categories."""
        index = KnowledgeIndex(
            version="1.0",
            last_updated="2026-01-08",
            categories={
                "reentrancy": Category(
                    id="reentrancy",
                    name="Reentrancy",
                    description="Callback attacks",
                    subcategories=[
                        SubcategoryRef(id="classic", name="Classic", description="Basic"),
                    ],
                ),
            },
        )
        self.assertEqual(len(index.categories), 1)
        self.assertIn("reentrancy", index.categories)

    def test_get_category(self):
        """Test getting category by ID."""
        index = KnowledgeIndex(
            categories={
                "reentrancy": Category(
                    id="reentrancy",
                    name="Reentrancy",
                    description="Test",
                ),
            },
        )
        cat = index.get_category("reentrancy")
        self.assertIsNotNone(cat)
        self.assertEqual(cat.id, "reentrancy")

        none_cat = index.get_category("nonexistent")
        self.assertIsNone(none_cat)

    def test_get_all_category_ids(self):
        """Test getting all category IDs."""
        index = KnowledgeIndex(
            categories={
                "cat1": Category(id="cat1", name="Cat1", description="First"),
                "cat2": Category(id="cat2", name="Cat2", description="Second"),
            },
        )
        ids = index.get_all_category_ids()
        self.assertIn("cat1", ids)
        self.assertIn("cat2", ids)

    def test_get_categories_for_operation(self):
        """Test getting categories for semantic operation."""
        index = KnowledgeIndex(
            operation_to_categories={
                "TRANSFERS_VALUE_OUT": {
                    "primary": ["reentrancy", "mev"],
                    "secondary": ["flash-loan"],
                },
            },
        )
        primary = index.get_categories_for_operation("TRANSFERS_VALUE_OUT")
        self.assertEqual(primary, ["reentrancy", "mev"])

        with_secondary = index.get_categories_for_operation(
            "TRANSFERS_VALUE_OUT", include_secondary=True
        )
        self.assertIn("flash-loan", with_secondary)

    def test_get_category_for_signature(self):
        """Test getting category for behavioral signature."""
        index = KnowledgeIndex(
            signature_to_categories={
                "R:bal->X:out->W:bal": {
                    "category": "reentrancy",
                    "subcategory": "classic",
                    "severity": "critical",
                },
            },
        )
        result = index.get_category_for_signature("R:bal->X:out->W:bal")
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "reentrancy")
        self.assertEqual(result[1], "classic")
        self.assertEqual(result[2], "critical")

        none_result = index.get_category_for_signature("unknown")
        self.assertIsNone(none_result)

    def test_get_navigation_context(self):
        """Test generating navigation context."""
        index = KnowledgeIndex(
            categories={
                "reentrancy": Category(
                    id="reentrancy",
                    name="Reentrancy",
                    description="Callback attacks",
                    subcategories=[
                        SubcategoryRef(id="classic", name="Classic", description="Basic"),
                    ],
                ),
            },
        )
        context = index.get_navigation_context()
        self.assertIn("VulnDocs Knowledge Navigation", context)
        self.assertIn("Reentrancy", context)
        self.assertIn("classic", context)
        self.assertIn("get_context", context)

    def test_estimate_total_tokens(self):
        """Test estimating total tokens."""
        index = KnowledgeIndex(
            categories={
                "cat1": Category(
                    id="cat1",
                    name="Cat1",
                    description="First",
                    token_estimate=1000,
                    subcategories=[
                        SubcategoryRef(id="sub1", name="Sub1", description="First sub"),
                    ],
                ),
            },
        )
        total = index.estimate_total_tokens()
        self.assertGreater(total, 0)
        self.assertEqual(total, 1500)  # 1000 for cat + 500 for sub

    def test_round_trip(self):
        """Test serialization round-trip."""
        original = KnowledgeIndex(
            version="1.0",
            last_updated="2026-01-08",
            categories={
                "test": Category(
                    id="test",
                    name="Test",
                    description="Test category",
                ),
            },
            operation_to_categories={
                "TEST_OP": {"primary": ["test"], "secondary": []},
            },
        )
        data = original.to_dict()
        restored = KnowledgeIndex.from_dict(data)
        self.assertEqual(original.version, restored.version)
        self.assertEqual(len(original.categories), len(restored.categories))


class TestValidateId(unittest.TestCase):
    """Tests for validate_id function."""

    def test_valid_ids(self):
        """Test valid IDs."""
        self.assertEqual(validate_id("reentrancy"), [])
        self.assertEqual(validate_id("access-control"), [])
        self.assertEqual(validate_id("flash-loan"), [])
        self.assertEqual(validate_id("a123"), [])
        self.assertEqual(validate_id("test-123-abc"), [])

    def test_invalid_ids(self):
        """Test invalid IDs."""
        self.assertGreater(len(validate_id("")), 0)  # Empty
        self.assertGreater(len(validate_id("123abc")), 0)  # Starts with number
        self.assertGreater(len(validate_id("Test")), 0)  # Uppercase
        self.assertGreater(len(validate_id("test_foo")), 0)  # Underscore
        self.assertGreater(len(validate_id("test.foo")), 0)  # Period


class TestValidateSeverityRange(unittest.TestCase):
    """Tests for validate_severity_range function."""

    def test_valid_severities(self):
        """Test valid severity ranges."""
        self.assertEqual(validate_severity_range(["critical"]), [])
        self.assertEqual(validate_severity_range(["high", "critical"]), [])
        self.assertEqual(validate_severity_range(["low", "medium", "high"]), [])
        self.assertEqual(validate_severity_range(["informational"]), [])

    def test_invalid_severities(self):
        """Test invalid severity values."""
        errors = validate_severity_range(["invalid"])
        self.assertGreater(len(errors), 0)

        errors = validate_severity_range(["high", "unknown"])
        self.assertGreater(len(errors), 0)


class TestValidateCategory(unittest.TestCase):
    """Tests for validate_category function."""

    def test_valid_category(self):
        """Test valid category data."""
        data = {
            "id": "reentrancy",
            "name": "Reentrancy",
            "description": "Callback attacks",
            "severity_range": ["high", "critical"],
            "subcategories": [
                {"id": "classic", "name": "Classic"},
            ],
        }
        errors = validate_category(data)
        self.assertEqual(errors, [])

    def test_missing_required_fields(self):
        """Test missing required fields."""
        data = {"id": "test"}
        errors = validate_category(data)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("name" in e for e in errors))
        self.assertTrue(any("description" in e for e in errors))

    def test_invalid_id(self):
        """Test invalid ID."""
        data = {
            "id": "Invalid",
            "name": "Test",
            "description": "Test",
        }
        errors = validate_category(data)
        self.assertGreater(len(errors), 0)

    def test_invalid_severity(self):
        """Test invalid severity."""
        data = {
            "id": "test",
            "name": "Test",
            "description": "Test",
            "severity_range": ["invalid"],
        }
        errors = validate_category(data)
        self.assertGreater(len(errors), 0)

    def test_invalid_subcategory(self):
        """Test invalid subcategory."""
        data = {
            "id": "test",
            "name": "Test",
            "description": "Test",
            "subcategories": [
                {"name": "Missing ID"},  # Missing id
            ],
        }
        errors = validate_category(data)
        self.assertGreater(len(errors), 0)


class TestValidateSubcategory(unittest.TestCase):
    """Tests for validate_subcategory function."""

    def test_valid_subcategory(self):
        """Test valid subcategory data."""
        data = {
            "id": "classic",
            "name": "Classic Reentrancy",
            "description": "State write after external call",
            "parent_category": "reentrancy",
        }
        errors = validate_subcategory(data)
        self.assertEqual(errors, [])

    def test_missing_required_fields(self):
        """Test missing required fields."""
        data = {"id": "test"}
        errors = validate_subcategory(data)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("parent_category" in e for e in errors))

    def test_invalid_graph_signals(self):
        """Test invalid graph signals."""
        data = {
            "id": "test",
            "name": "Test",
            "description": "Test",
            "parent_category": "test",
            "graph_signals": [
                {"expected": True},  # Missing property
            ],
        }
        errors = validate_subcategory(data)
        self.assertGreater(len(errors), 0)


class TestValidateDocument(unittest.TestCase):
    """Tests for validate_document function."""

    def test_valid_document(self):
        """Test valid document data."""
        data = {
            "subcategory_id": "classic",
            "document_type": "detection",
        }
        errors = validate_document(data)
        self.assertEqual(errors, [])

    def test_missing_subcategory_id(self):
        """Test missing subcategory_id."""
        data = {"document_type": "detection"}
        errors = validate_document(data)
        self.assertGreater(len(errors), 0)

    def test_invalid_document_type(self):
        """Test invalid document type."""
        data = {
            "subcategory_id": "classic",
            "document_type": "invalid",
        }
        errors = validate_document(data)
        self.assertGreater(len(errors), 0)


class TestValidateIndex(unittest.TestCase):
    """Tests for validate_index function."""

    def test_valid_index(self):
        """Test valid index data."""
        data = {
            "schema_version": "1.0",
            "categories": {
                "reentrancy": {
                    "id": "reentrancy",
                    "name": "Reentrancy",
                    "description": "Test",
                },
            },
        }
        errors = validate_index(data)
        self.assertEqual(errors, [])

    def test_invalid_version(self):
        """Test invalid version format."""
        data = {
            "schema_version": "invalid",
            "categories": {},
        }
        errors = validate_index(data)
        self.assertGreater(len(errors), 0)

    def test_invalid_category_id(self):
        """Test invalid category ID in index."""
        data = {
            "schema_version": "1.0",
            "categories": {
                "Invalid-ID": {
                    "id": "Invalid-ID",
                    "name": "Test",
                    "description": "Test",
                },
            },
        }
        errors = validate_index(data)
        self.assertGreater(len(errors), 0)


class TestLoadIndex(unittest.TestCase):
    """Tests for load_index function."""

    @pytest.mark.xfail(reason="Stale code: VulnDocs index schema format changed")
    def test_load_from_disk(self):
        """Test loading index from disk if it exists."""
        # This test uses the actual knowledge directory
        if KNOWLEDGE_DIR.exists() and (KNOWLEDGE_DIR / "index.yaml").exists():
            index = load_index()
            self.assertIsInstance(index, KnowledgeIndex)
            self.assertIsNotNone(index.version)

    def test_load_missing_returns_empty(self):
        """Test loading from missing directory returns empty index."""
        with TemporaryDirectory() as tmpdir:
            index = load_index(Path(tmpdir))
            self.assertIsInstance(index, KnowledgeIndex)
            self.assertEqual(len(index.categories), 0)

    def test_load_from_temp_file(self):
        """Test loading index from temporary file."""
        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create test index file
            index_data = {
                "schema_version": "1.0",
                "last_updated": "2026-01-08",
                "categories": {
                    "test": {
                        "name": "Test Category",
                        "description": "A test category",
                        "severity_range": ["medium"],
                        "subcategories": ["sub1"],
                    },
                },
            }
            with open(tmp_path / "index.yaml", "w") as f:
                yaml.dump(index_data, f)

            index = load_index(tmp_path)
            self.assertEqual(index.version, "1.0")
            self.assertIn("test", index.categories)


class TestCacheConfig(unittest.TestCase):
    """Tests for CacheConfig dataclass."""

    def test_create(self):
        """Test creating cache config."""
        config = CacheConfig(
            name="system_context",
            content="Navigation index",
            cache_control=CacheControlType.EPHEMERAL,
            estimated_tokens=3000,
            key="vulndocs-system-v1",
        )
        self.assertEqual(config.name, "system_context")
        self.assertEqual(config.cache_control, CacheControlType.EPHEMERAL)

    def test_round_trip(self):
        """Test serialization round-trip."""
        original = CacheConfig(
            name="test",
            content="test content",
            cache_control=CacheControlType.STATIC,
            estimated_tokens=1000,
            key="test-v1",
        )
        data = original.to_dict()
        restored = CacheConfig.from_dict(data)
        self.assertEqual(original.name, restored.name)
        self.assertEqual(original.cache_control, restored.cache_control)


class TestNavigationMetadata(unittest.TestCase):
    """Tests for NavigationMetadata dataclass."""

    def test_create_empty(self):
        """Test creating empty navigation metadata."""
        nav = NavigationMetadata()
        self.assertEqual(nav.hints, [])
        self.assertEqual(nav.depth_guide, {})

    def test_create_with_data(self):
        """Test creating navigation metadata with data."""
        nav = NavigationMetadata(
            hints=["Hint 1", "Hint 2"],
            depth_guide={"index": "200 tokens"},
            retrieval_strategy={"single": "detection"},
        )
        self.assertEqual(len(nav.hints), 2)

    def test_round_trip(self):
        """Test serialization round-trip."""
        original = NavigationMetadata(
            hints=["Test hint"],
            depth_guide={"test": "value"},
        )
        data = original.to_dict()
        restored = NavigationMetadata.from_dict(data)
        self.assertEqual(original.hints, restored.hints)


class TestSchemaIntegration(unittest.TestCase):
    """Integration tests for the schema system."""

    def test_full_workflow(self):
        """Test a full workflow of creating and validating knowledge."""
        # Create a complete category with subcategories
        cat = Category(
            id="test-category",
            name="Test Category",
            description="A test vulnerability category",
            severity_range=["medium", "high"],
            subcategories=[
                SubcategoryRef(
                    id="test-sub",
                    name="Test Subcategory",
                    description="A test subcategory",
                    patterns=["ts-001"],
                ),
            ],
            relevant_properties=["test_property"],
            semantic_operations=["TEST_OPERATION"],
        )

        # Validate category
        cat_data = cat.to_dict()
        errors = validate_category(cat_data)
        self.assertEqual(errors, [], f"Category validation failed: {errors}")

        # Create index with category
        index = KnowledgeIndex(
            version="1.0",
            last_updated="2026-01-08",
            categories={cat.id: cat},
            operation_to_categories={
                "TEST_OPERATION": {"primary": [cat.id], "secondary": []},
            },
        )

        # Validate index
        index_data = index.to_dict()
        errors = validate_index(index_data)
        self.assertEqual(errors, [], f"Index validation failed: {errors}")

        # Test navigation
        self.assertEqual(index.get_categories_for_operation("TEST_OPERATION"), [cat.id])

        # Test context generation
        context = index.get_navigation_context()
        self.assertIn(cat.name, context)

    def test_yaml_round_trip(self):
        """Test YAML serialization round-trip."""
        original = KnowledgeIndex(
            version="1.0",
            last_updated="2026-01-08",
            categories={
                "test": Category(
                    id="test",
                    name="Test",
                    description="Test category",
                    subcategories=[
                        SubcategoryRef(id="sub", name="Sub", description="Subcategory"),
                    ],
                ),
            },
        )

        # Serialize to YAML string
        yaml_str = yaml.dump(original.to_dict(), default_flow_style=False)

        # Parse YAML back
        data = yaml.safe_load(yaml_str)
        restored = KnowledgeIndex.from_dict(data)

        self.assertEqual(original.version, restored.version)
        self.assertEqual(len(original.categories), len(restored.categories))


if __name__ == "__main__":
    unittest.main()
