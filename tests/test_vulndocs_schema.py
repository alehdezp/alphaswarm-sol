"""Tests for VulnDocs Schema (Task 17.0).

Tests the knowledge schema definitions for the vulnerability
documentation system.
"""

import pytest

from alphaswarm_sol.vulndocs.schema import (
    CategoryIndex,
    CodePattern,
    DetectionDocument,
    DocumentType,
    FixRecommendation,
    GraphSignal,
    KnowledgeDepth,
    KnowledgeIndex,
    PatternDocument,
    RealExploit,
    SubcategoryIndex,
    VulnCategory,
    VulnSubcategory,
    validate_category_index,
    validate_subcategory,
)


# =============================================================================
# VulnCategory Tests
# =============================================================================


class TestVulnCategory:
    """Tests for VulnCategory enum."""

    def test_all_categories_exist(self):
        """Test that all expected categories exist."""
        expected = [
            "reentrancy",
            "access-control",
            "oracle",
            "flash-loan",
            "mev",
            "dos",
            "token",
            "upgrade",
            "crypto",
            "governance",
            "logic",
        ]
        for cat in expected:
            assert VulnCategory(cat) is not None

    def test_from_string_basic(self):
        """Test basic string parsing."""
        assert VulnCategory.from_string("reentrancy") == VulnCategory.REENTRANCY
        assert VulnCategory.from_string("access-control") == VulnCategory.ACCESS_CONTROL
        assert VulnCategory.from_string("oracle") == VulnCategory.ORACLE

    def test_from_string_normalized(self):
        """Test normalized string parsing."""
        assert VulnCategory.from_string("REENTRANCY") == VulnCategory.REENTRANCY
        assert VulnCategory.from_string("access_control") == VulnCategory.ACCESS_CONTROL
        assert VulnCategory.from_string("Access-Control") == VulnCategory.ACCESS_CONTROL

    def test_from_string_aliases(self):
        """Test alias resolution."""
        assert VulnCategory.from_string("access") == VulnCategory.ACCESS_CONTROL
        assert VulnCategory.from_string("price") == VulnCategory.ORACLE
        assert VulnCategory.from_string("flashloan") == VulnCategory.FLASH_LOAN
        assert VulnCategory.from_string("erc20") == VulnCategory.TOKEN

    def test_from_string_invalid(self):
        """Test invalid category raises error."""
        with pytest.raises(ValueError):
            VulnCategory.from_string("not-a-category")

    def test_all_categories(self):
        """Test all_categories returns all values."""
        all_cats = VulnCategory.all_categories()
        assert len(all_cats) == 11
        assert "reentrancy" in all_cats
        assert "access-control" in all_cats


# =============================================================================
# KnowledgeDepth Tests
# =============================================================================


class TestKnowledgeDepth:
    """Tests for KnowledgeDepth enum."""

    def test_all_depths_exist(self):
        """Test that all expected depths exist."""
        expected = ["index", "overview", "detection", "patterns", "exploits", "fixes", "full"]
        for depth in expected:
            assert KnowledgeDepth(depth) is not None

    def test_from_string(self):
        """Test string parsing."""
        assert KnowledgeDepth.from_string("detection") == KnowledgeDepth.DETECTION
        assert KnowledgeDepth.from_string("PATTERNS") == KnowledgeDepth.PATTERNS
        assert KnowledgeDepth.from_string("Full") == KnowledgeDepth.FULL

    def test_from_string_invalid_defaults(self):
        """Test invalid depth defaults to DETECTION."""
        assert KnowledgeDepth.from_string("invalid") == KnowledgeDepth.DETECTION


# =============================================================================
# GraphSignal Tests
# =============================================================================


class TestGraphSignal:
    """Tests for GraphSignal dataclass."""

    def test_creation(self):
        """Test basic creation."""
        signal = GraphSignal(
            property_name="state_write_after_external_call",
            expected_value=True,
            is_critical=True,
            description="Detects CEI pattern violation",
        )
        assert signal.property_name == "state_write_after_external_call"
        assert signal.expected_value is True
        assert signal.is_critical is True

    def test_serialization(self):
        """Test serialization round-trip."""
        signal = GraphSignal(
            property_name="has_reentrancy_guard",
            expected_value=False,
            is_critical=True,
        )

        data = signal.to_dict()
        restored = GraphSignal.from_dict(data)

        assert restored.property_name == signal.property_name
        assert restored.expected_value == signal.expected_value
        assert restored.is_critical == signal.is_critical


# =============================================================================
# CodePattern Tests
# =============================================================================


class TestCodePattern:
    """Tests for CodePattern dataclass."""

    def test_creation(self):
        """Test basic creation."""
        pattern = CodePattern(
            name="Classic Reentrancy",
            vulnerable_code="msg.sender.call{value: bal}()",
            safe_code="balances[msg.sender] = 0; msg.sender.transfer(bal);",
            description="State update after external call",
            severity="critical",
        )
        assert pattern.name == "Classic Reentrancy"
        assert "call{value:" in pattern.vulnerable_code

    def test_serialization(self):
        """Test serialization round-trip."""
        pattern = CodePattern(
            name="Test Pattern",
            vulnerable_code="// vulnerable",
            safe_code="// safe",
        )

        data = pattern.to_dict()
        restored = CodePattern.from_dict(data)

        assert restored.name == pattern.name
        assert restored.vulnerable_code == pattern.vulnerable_code


# =============================================================================
# RealExploit Tests
# =============================================================================


class TestRealExploit:
    """Tests for RealExploit dataclass."""

    def test_creation(self):
        """Test basic creation."""
        exploit = RealExploit(
            name="DAO Hack",
            date="2016-06-17",
            loss_usd="50M",
            protocol="The DAO",
            chain="ethereum",
            description="Classic reentrancy exploit",
            references=["https://example.com/dao-hack"],
        )
        assert exploit.name == "DAO Hack"
        assert exploit.loss_usd == "50M"

    def test_serialization(self):
        """Test serialization round-trip."""
        exploit = RealExploit(
            name="Test Exploit",
            date="2024-01-01",
            protocol="Test Protocol",
        )

        data = exploit.to_dict()
        restored = RealExploit.from_dict(data)

        assert restored.name == exploit.name
        assert restored.date == exploit.date


# =============================================================================
# VulnSubcategory Tests
# =============================================================================


class TestVulnSubcategory:
    """Tests for VulnSubcategory dataclass."""

    def test_creation(self):
        """Test basic creation."""
        subcategory = VulnSubcategory(
            id="classic",
            name="Classic Reentrancy",
            description="State write after external call",
            parent_category="reentrancy",
            severity_range=["high", "critical"],
            patterns=["vm-001", "vm-002"],
        )
        assert subcategory.id == "classic"
        assert subcategory.parent_category == "reentrancy"

    def test_serialization(self):
        """Test serialization round-trip."""
        subcategory = VulnSubcategory(
            id="test-sub",
            name="Test Subcategory",
            description="Test description",
            parent_category="test-cat",
            graph_signals=[
                GraphSignal(
                    property_name="test_prop",
                    expected_value=True,
                    is_critical=True,
                )
            ],
        )

        data = subcategory.to_dict()
        restored = VulnSubcategory.from_dict(data)

        assert restored.id == subcategory.id
        assert len(restored.graph_signals) == 1
        assert restored.graph_signals[0].property_name == "test_prop"

    def test_get_detection_context(self):
        """Test detection context generation."""
        subcategory = VulnSubcategory(
            id="classic",
            name="Classic Reentrancy",
            description="State write after external call",
            parent_category="reentrancy",
            graph_signals=[
                GraphSignal(
                    property_name="state_write_after_external_call",
                    expected_value=True,
                    is_critical=True,
                )
            ],
            false_positive_indicators=["nonReentrant modifier present"],
        )

        context = subcategory.get_detection_context()

        assert "Classic Reentrancy" in context
        assert "state_write_after_external_call" in context
        assert "nonReentrant" in context

    def test_get_patterns_context(self):
        """Test patterns context generation."""
        subcategory = VulnSubcategory(
            id="classic",
            name="Classic Reentrancy",
            description="Test",
            parent_category="reentrancy",
            patterns=["vm-001"],
            code_patterns=[
                CodePattern(
                    name="Basic Reentrancy",
                    vulnerable_code="msg.sender.call{value: bal}()",
                    safe_code="balances[msg.sender] = 0;",
                )
            ],
        )

        context = subcategory.get_patterns_context()

        assert "vm-001" in context
        assert "Basic Reentrancy" in context
        assert "call{value:" in context


# =============================================================================
# CategoryIndex Tests
# =============================================================================


class TestCategoryIndex:
    """Tests for CategoryIndex dataclass."""

    def test_creation(self):
        """Test basic creation."""
        category = CategoryIndex(
            id="reentrancy",
            name="Reentrancy Vulnerabilities",
            description="Attacks exploiting callback mechanisms",
            severity_range=["high", "critical"],
        )
        assert category.id == "reentrancy"
        assert category.context_cache_key == "reentrancy-v1"

    def test_with_subcategories(self):
        """Test category with subcategories."""
        category = CategoryIndex(
            id="reentrancy",
            name="Reentrancy",
            description="Reentrancy attacks",
            subcategories=[
                VulnSubcategory(
                    id="classic",
                    name="Classic Reentrancy",
                    description="State write after external call",
                    parent_category="reentrancy",
                ),
                VulnSubcategory(
                    id="cross-function",
                    name="Cross-Function Reentrancy",
                    description="Reentrancy across multiple functions",
                    parent_category="reentrancy",
                ),
            ],
        )

        assert len(category.subcategories) == 2
        assert category.get_subcategory("classic") is not None
        assert category.get_subcategory("cross-function") is not None
        assert category.get_subcategory("nonexistent") is None

    def test_get_subcategory_ids(self):
        """Test getting subcategory IDs."""
        category = CategoryIndex(
            id="reentrancy",
            name="Reentrancy",
            description="Test",
            subcategories=[
                VulnSubcategory(id="classic", name="Classic", description="", parent_category="reentrancy"),
                VulnSubcategory(id="cross", name="Cross", description="", parent_category="reentrancy"),
            ],
        )

        ids = category.get_subcategory_ids()
        assert "classic" in ids
        assert "cross" in ids

    def test_serialization(self):
        """Test serialization round-trip."""
        category = CategoryIndex(
            id="test",
            name="Test Category",
            description="Test description",
            subcategories=[
                VulnSubcategory(
                    id="sub1",
                    name="Sub 1",
                    description="Description",
                    parent_category="test",
                )
            ],
        )

        data = category.to_dict()
        restored = CategoryIndex.from_dict(data)

        assert restored.id == category.id
        assert len(restored.subcategories) == 1

    def test_get_overview_context(self):
        """Test overview context generation."""
        category = CategoryIndex(
            id="reentrancy",
            name="Reentrancy Vulnerabilities",
            description="Attacks exploiting callback mechanisms",
            relevant_properties=["state_write_after_external_call", "has_reentrancy_guard"],
            subcategories=[
                VulnSubcategory(
                    id="classic",
                    name="Classic",
                    description="State write after call",
                    parent_category="reentrancy",
                )
            ],
        )

        context = category.get_overview_context()

        assert "Reentrancy Vulnerabilities" in context
        assert "callback mechanisms" in context
        assert "Classic" in context
        assert "state_write_after_external_call" in context


# =============================================================================
# KnowledgeIndex Tests
# =============================================================================


class TestKnowledgeIndex:
    """Tests for KnowledgeIndex dataclass."""

    def test_creation(self):
        """Test basic creation."""
        index = KnowledgeIndex(version="1.0")
        assert index.version == "1.0"
        assert len(index.categories) == 0

    def test_with_categories(self):
        """Test index with categories."""
        index = KnowledgeIndex(
            version="1.0",
            categories={
                "reentrancy": CategoryIndex(
                    id="reentrancy",
                    name="Reentrancy",
                    description="Reentrancy attacks",
                ),
                "access-control": CategoryIndex(
                    id="access-control",
                    name="Access Control",
                    description="Access control issues",
                ),
            },
        )

        assert index.get_category("reentrancy") is not None
        assert index.get_category("access-control") is not None
        assert index.get_category("nonexistent") is None

    def test_get_all_category_ids(self):
        """Test getting all category IDs."""
        index = KnowledgeIndex(
            categories={
                "reentrancy": CategoryIndex(id="reentrancy", name="R", description=""),
                "oracle": CategoryIndex(id="oracle", name="O", description=""),
            }
        )

        ids = index.get_all_category_ids()
        assert "reentrancy" in ids
        assert "oracle" in ids

    def test_get_subcategory(self):
        """Test getting subcategory through index."""
        index = KnowledgeIndex(
            categories={
                "reentrancy": CategoryIndex(
                    id="reentrancy",
                    name="Reentrancy",
                    description="",
                    subcategories=[
                        VulnSubcategory(
                            id="classic",
                            name="Classic",
                            description="",
                            parent_category="reentrancy",
                        )
                    ],
                )
            }
        )

        sub = index.get_subcategory("reentrancy", "classic")
        assert sub is not None
        assert sub.id == "classic"

        assert index.get_subcategory("reentrancy", "nonexistent") is None
        assert index.get_subcategory("nonexistent", "classic") is None

    def test_serialization(self):
        """Test serialization round-trip."""
        index = KnowledgeIndex(
            version="1.0",
            categories={
                "test": CategoryIndex(
                    id="test",
                    name="Test",
                    description="Test category",
                )
            },
        )

        data = index.to_dict()
        restored = KnowledgeIndex.from_dict(data)

        assert restored.version == index.version
        assert "test" in restored.categories

    def test_get_navigation_context(self):
        """Test navigation context generation."""
        index = KnowledgeIndex(
            categories={
                "reentrancy": CategoryIndex(
                    id="reentrancy",
                    name="Reentrancy",
                    description="Reentrancy attacks",
                    subcategories=[
                        VulnSubcategory(
                            id="classic",
                            name="Classic",
                            description="",
                            parent_category="reentrancy",
                        )
                    ],
                )
            }
        )

        context = index.get_navigation_context()

        assert "VulnDocs Knowledge Navigation" in context
        assert "Reentrancy" in context
        assert "classic" in context
        assert "get_context" in context

    def test_estimate_total_tokens(self):
        """Test token estimation."""
        index = KnowledgeIndex(
            categories={
                "test": CategoryIndex(
                    id="test",
                    name="Test",
                    description="",
                    token_estimate=1000,
                    subcategories=[
                        VulnSubcategory(
                            id="sub1",
                            name="Sub1",
                            description="",
                            parent_category="test",
                            token_estimate=500,
                        )
                    ],
                )
            }
        )

        total = index.estimate_total_tokens()
        assert total == 1500


# =============================================================================
# Document Tests
# =============================================================================


class TestDetectionDocument:
    """Tests for DetectionDocument."""

    def test_creation(self):
        """Test basic creation."""
        doc = DetectionDocument(
            subcategory_id="classic",
            graph_signals=[
                GraphSignal(
                    property_name="state_write_after_external_call",
                    expected_value=True,
                    is_critical=True,
                )
            ],
            operation_sequences=["R:bal → X:out → W:bal"],
            false_positive_indicators=["nonReentrant modifier"],
        )

        assert doc.subcategory_id == "classic"
        assert len(doc.graph_signals) == 1

    def test_to_markdown(self):
        """Test markdown generation."""
        doc = DetectionDocument(
            subcategory_id="classic",
            graph_signals=[
                GraphSignal(
                    property_name="state_write_after_external_call",
                    expected_value=True,
                    is_critical=True,
                )
            ],
            operation_sequences=["R:bal → X:out → W:bal"],
            behavioral_signatures=["VULNERABLE: state_after_call"],
            false_positive_indicators=["nonReentrant"],
        )

        md = doc.to_markdown()

        assert "# Detection: classic" in md
        assert "state_write_after_external_call" in md
        assert "R:bal" in md
        assert "nonReentrant" in md


class TestPatternDocument:
    """Tests for PatternDocument."""

    def test_creation(self):
        """Test basic creation."""
        doc = PatternDocument(
            subcategory_id="classic",
            patterns=[
                CodePattern(
                    name="Basic Pattern",
                    vulnerable_code="// vulnerable",
                    safe_code="// safe",
                )
            ],
            associated_pattern_ids=["vm-001"],
        )

        assert doc.subcategory_id == "classic"
        assert len(doc.patterns) == 1

    def test_to_markdown(self):
        """Test markdown generation."""
        doc = PatternDocument(
            subcategory_id="classic",
            patterns=[
                CodePattern(
                    name="Reentrancy Pattern",
                    vulnerable_code="msg.sender.call{value: bal}()",
                    safe_code="balances[msg.sender] = 0;",
                    description="CEI violation",
                )
            ],
            associated_pattern_ids=["vm-001"],
        )

        md = doc.to_markdown()

        assert "# Patterns: classic" in md
        assert "vm-001" in md
        assert "Reentrancy Pattern" in md
        assert "call{value:" in md


# =============================================================================
# Validation Tests
# =============================================================================


class TestValidation:
    """Tests for schema validation functions."""

    def test_validate_category_index_valid(self):
        """Test validation of valid category index."""
        data = {
            "id": "reentrancy",
            "name": "Reentrancy",
            "description": "Reentrancy attacks",
            "subcategories": [
                {"id": "classic", "name": "Classic"},
            ],
        }

        errors = validate_category_index(data)
        assert len(errors) == 0

    def test_validate_category_index_missing_fields(self):
        """Test validation catches missing fields."""
        data = {
            "name": "Reentrancy",
            # Missing id and description
        }

        errors = validate_category_index(data)
        assert len(errors) >= 2
        assert any("id" in e for e in errors)
        assert any("description" in e for e in errors)

    def test_validate_category_index_invalid_subcategories(self):
        """Test validation catches invalid subcategories."""
        data = {
            "id": "test",
            "name": "Test",
            "description": "Test",
            "subcategories": [
                {"name": "Missing ID"},  # Missing id
            ],
        }

        errors = validate_category_index(data)
        assert any("id" in e.lower() for e in errors)

    def test_validate_subcategory_valid(self):
        """Test validation of valid subcategory."""
        data = {
            "id": "classic",
            "name": "Classic Reentrancy",
            "description": "State write after call",
            "parent_category": "reentrancy",
        }

        errors = validate_subcategory(data)
        assert len(errors) == 0

    def test_validate_subcategory_missing_fields(self):
        """Test validation catches missing subcategory fields."""
        data = {
            "id": "classic",
            # Missing name, description, parent_category
        }

        errors = validate_subcategory(data)
        assert len(errors) >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
