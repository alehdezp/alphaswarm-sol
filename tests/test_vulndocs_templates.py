"""Tests for VulnDocs Templates (Task 17.2).

Tests the document templates for the vulnerability documentation system.
Covers:
- Template dataclass creation and serialization
- Markdown rendering for all four document types
- Template generation utilities
- Template validation
"""

import pytest
from datetime import datetime

from alphaswarm_sol.knowledge.vulndocs.schema import (
    CodePattern,
    ExploitReference,
    FixRecommendation,
    GraphSignal,
    OperationSequences,
)

from alphaswarm_sol.knowledge.vulndocs.templates import (
    # Template dataclasses
    DetectionTemplate,
    PatternsTemplate,
    ExploitsTemplate,
    FixesTemplate,
    ExploitIncident,
    FixRecommendationExtended,
    # Rendering functions
    render_detection_md,
    render_patterns_md,
    render_exploits_md,
    render_fixes_md,
    # Generation helpers
    generate_document_templates,
    create_template_bundle,
    # Validation functions
    validate_detection_template,
    validate_patterns_template,
    validate_exploits_template,
    validate_fixes_template,
    # Constants
    TEMPLATE_VERSION,
    TOKEN_BUDGET,
)


# =============================================================================
# DETECTION TEMPLATE TESTS
# =============================================================================


class TestDetectionTemplate:
    """Tests for DetectionTemplate dataclass."""

    def test_basic_creation(self):
        """Test basic template creation."""
        template = DetectionTemplate(
            subcategory_id="classic",
            subcategory_name="Classic Reentrancy",
        )
        assert template.subcategory_id == "classic"
        assert template.subcategory_name == "Classic Reentrancy"
        assert template.signals == []
        assert template.detection_checklist == []

    def test_full_creation(self):
        """Test creation with all fields."""
        signal = GraphSignal(
            property_name="state_write_after_external_call",
            expected=True,
            critical=True,
            description="State write after external call",
        )
        op_seq = OperationSequences(
            vulnerable=["R:bal -> X:out -> W:bal"],
            safe=["R:bal -> W:bal -> X:out"],
        )
        template = DetectionTemplate(
            subcategory_id="classic",
            subcategory_name="Classic Reentrancy",
            category_id="reentrancy",
            category_name="Reentrancy Vulnerabilities",
            overview="State write after external call allows attackers to drain funds",
            signals=[signal],
            behavioral_signatures=["R:bal -> X:out -> W:bal"],
            operation_sequences=op_seq,
            detection_checklist=[
                "Check for state writes after external calls",
                "Verify reentrancy guard is present",
            ],
            false_positive_indicators=[
                "nonReentrant modifier present",
                "CEI pattern followed",
            ],
            severity="critical",
            confidence_notes="High confidence when CEI violation detected",
            related_patterns=["reentrancy-001", "reentrancy-002"],
        )

        assert template.category_id == "reentrancy"
        assert len(template.signals) == 1
        assert template.signals[0].property_name == "state_write_after_external_call"
        assert len(template.detection_checklist) == 2
        assert template.severity == "critical"

    def test_serialization_roundtrip(self):
        """Test serialization and deserialization."""
        signal = GraphSignal(
            property_name="has_reentrancy_guard",
            expected=False,
            critical=True,
        )
        template = DetectionTemplate(
            subcategory_id="classic",
            subcategory_name="Classic Reentrancy",
            signals=[signal],
            detection_checklist=["Check for guards"],
        )

        data = template.to_dict()
        restored = DetectionTemplate.from_dict(data)

        assert restored.subcategory_id == template.subcategory_id
        assert restored.subcategory_name == template.subcategory_name
        assert len(restored.signals) == 1
        assert restored.signals[0].property_name == signal.property_name

    def test_render_method(self):
        """Test template render method."""
        signal = GraphSignal(
            property_name="state_write_after_external_call",
            expected=True,
            critical=True,
        )
        template = DetectionTemplate(
            subcategory_id="classic",
            subcategory_name="Classic Reentrancy",
            category_name="Reentrancy",
            signals=[signal],
            false_positive_indicators=["nonReentrant modifier present"],
        )

        md = template.render()

        assert "# Detection: Classic Reentrancy" in md
        assert "state_write_after_external_call" in md
        assert "nonReentrant" in md


# =============================================================================
# PATTERNS TEMPLATE TESTS
# =============================================================================


class TestPatternsTemplate:
    """Tests for PatternsTemplate dataclass."""

    def test_basic_creation(self):
        """Test basic template creation."""
        template = PatternsTemplate(
            subcategory_id="classic",
            subcategory_name="Classic Reentrancy",
        )
        assert template.subcategory_id == "classic"
        assert template.vulnerable_patterns == []
        assert template.safe_patterns == []

    def test_full_creation(self):
        """Test creation with all fields."""
        vuln_pattern = CodePattern(
            name="CEI Violation",
            vulnerable_code="msg.sender.call{value: bal}(''); balances[msg.sender] = 0;",
            description="State update after external call",
            severity="critical",
        )
        safe_pattern = CodePattern(
            name="CEI Compliant",
            vulnerable_code="",
            safe_code="balances[msg.sender] = 0; msg.sender.call{value: bal}('');",
            description="State update before external call",
        )
        template = PatternsTemplate(
            subcategory_id="classic",
            subcategory_name="Classic Reentrancy",
            category_id="reentrancy",
            overview="Classic reentrancy occurs when state is updated after an external call",
            vulnerable_patterns=[vuln_pattern],
            safe_patterns=[safe_pattern],
            edge_cases=["Cross-function reentrancy via shared state"],
            pattern_ids=["reentrancy-001"],
            common_mistakes=["Updating balance after transfer"],
            best_practices=["Use ReentrancyGuard from OpenZeppelin"],
        )

        assert len(template.vulnerable_patterns) == 1
        assert len(template.safe_patterns) == 1
        assert template.pattern_ids == ["reentrancy-001"]

    def test_serialization_roundtrip(self):
        """Test serialization and deserialization."""
        pattern = CodePattern(
            name="Test Pattern",
            vulnerable_code="// vulnerable",
            safe_code="// safe",
        )
        template = PatternsTemplate(
            subcategory_id="classic",
            subcategory_name="Classic Reentrancy",
            vulnerable_patterns=[pattern],
        )

        data = template.to_dict()
        restored = PatternsTemplate.from_dict(data)

        assert restored.subcategory_id == template.subcategory_id
        assert len(restored.vulnerable_patterns) == 1

    def test_render_method(self):
        """Test template render method."""
        vuln_pattern = CodePattern(
            name="Vulnerable Pattern",
            vulnerable_code="msg.sender.call{value: bal}('')",
            severity="critical",
        )
        template = PatternsTemplate(
            subcategory_id="classic",
            subcategory_name="Classic Reentrancy",
            vulnerable_patterns=[vuln_pattern],
            pattern_ids=["reentrancy-001"],
        )

        md = template.render()

        assert "# Patterns: Classic Reentrancy" in md
        assert "Vulnerable Pattern" in md
        assert "call{value:" in md
        assert "reentrancy-001" in md


# =============================================================================
# EXPLOITS TEMPLATE TESTS
# =============================================================================


class TestExploitIncident:
    """Tests for ExploitIncident dataclass."""

    def test_basic_creation(self):
        """Test basic incident creation."""
        incident = ExploitIncident(
            id="dao-001",
            name="DAO Hack",
        )
        assert incident.id == "dao-001"
        assert incident.name == "DAO Hack"
        assert incident.chain == "ethereum"

    def test_full_creation(self):
        """Test creation with all fields."""
        incident = ExploitIncident(
            id="dao-001",
            name="DAO Hack",
            date="2016-06-17",
            loss_usd="50,000,000",
            protocol="The DAO",
            chain="ethereum",
            description="Classic reentrancy attack draining ETH",
            attack_vector="Reentrant call in withdraw function",
            attack_steps=[
                "Deploy malicious contract",
                "Call splitDAO to trigger recursive calls",
                "Drain ETH via repeated withdrawals",
            ],
            root_cause="State update after external call",
            postmortem_url="https://example.com/dao-postmortem",
            tx_hash="0x...",
        )

        assert incident.loss_usd == "50,000,000"
        assert len(incident.attack_steps) == 3

    def test_from_exploit_reference(self):
        """Test creation from ExploitReference."""
        ref = ExploitReference(
            id="test-001",
            name="Test Exploit",
            date="2024-01-01",
            loss_usd="1,000,000",
            protocol="Test Protocol",
        )
        incident = ExploitIncident.from_exploit_reference(ref)

        assert incident.id == ref.id
        assert incident.name == ref.name
        assert incident.loss_usd == ref.loss_usd


class TestExploitsTemplate:
    """Tests for ExploitsTemplate dataclass."""

    def test_basic_creation(self):
        """Test basic template creation."""
        template = ExploitsTemplate(
            subcategory_id="classic",
            subcategory_name="Classic Reentrancy",
        )
        assert template.incidents == []
        assert template.attack_vectors == []

    def test_full_creation(self):
        """Test creation with all fields."""
        incident = ExploitIncident(
            id="dao-001",
            name="DAO Hack",
            date="2016-06-17",
            loss_usd="50,000,000",
        )
        template = ExploitsTemplate(
            subcategory_id="classic",
            subcategory_name="Classic Reentrancy",
            category_id="reentrancy",
            overview="Reentrancy exploits have caused billions in losses",
            incidents=[incident],
            attack_vectors=[
                "Withdraw function without reentrancy guard",
                "Callback in ERC777 tokens",
            ],
            total_losses="1,000,000,000",
            common_targets=["DeFi protocols", "Lending platforms"],
        )

        assert len(template.incidents) == 1
        assert template.total_losses == "1,000,000,000"

    def test_serialization_roundtrip(self):
        """Test serialization and deserialization."""
        incident = ExploitIncident(
            id="test-001",
            name="Test Exploit",
        )
        template = ExploitsTemplate(
            subcategory_id="classic",
            subcategory_name="Classic Reentrancy",
            incidents=[incident],
        )

        data = template.to_dict()
        restored = ExploitsTemplate.from_dict(data)

        assert len(restored.incidents) == 1
        assert restored.incidents[0].id == "test-001"

    def test_render_method(self):
        """Test template render method."""
        incident = ExploitIncident(
            id="dao-001",
            name="DAO Hack",
            date="2016-06-17",
            loss_usd="50,000,000",
            protocol="The DAO",
            postmortem_url="https://example.com/postmortem",
        )
        template = ExploitsTemplate(
            subcategory_id="classic",
            subcategory_name="Classic Reentrancy",
            incidents=[incident],
            attack_vectors=["Recursive withdrawal"],
        )

        md = template.render()

        assert "# Exploits: Classic Reentrancy" in md
        assert "DAO Hack" in md
        assert "$50,000,000" in md
        assert "The DAO" in md


# =============================================================================
# FIXES TEMPLATE TESTS
# =============================================================================


class TestFixRecommendationExtended:
    """Tests for FixRecommendationExtended dataclass."""

    def test_basic_creation(self):
        """Test basic recommendation creation."""
        rec = FixRecommendationExtended(
            name="Use ReentrancyGuard",
            description="Add OpenZeppelin ReentrancyGuard to vulnerable functions",
        )
        assert rec.name == "Use ReentrancyGuard"
        assert rec.effectiveness == "high"
        assert rec.complexity == "low"

    def test_full_creation(self):
        """Test creation with all fields."""
        rec = FixRecommendationExtended(
            name="Use ReentrancyGuard",
            description="Add OpenZeppelin ReentrancyGuard to vulnerable functions",
            code_example="modifier nonReentrant() { require(!locked); locked = true; _; locked = false; }",
            effectiveness="high",
            complexity="low",
            testing_strategy="Test with malicious contract attempting reentry",
            migration_notes="Add modifier to all external functions that transfer value",
            gas_impact="~100 gas per call",
            dependencies=["@openzeppelin/contracts"],
        )

        assert rec.gas_impact == "~100 gas per call"
        assert len(rec.dependencies) == 1

    def test_from_fix_recommendation(self):
        """Test creation from FixRecommendation."""
        rec = FixRecommendation(
            name="Test Fix",
            description="Test description",
            code_example="// test",
        )
        extended = FixRecommendationExtended.from_fix_recommendation(rec)

        assert extended.name == rec.name
        assert extended.description == rec.description
        assert extended.code_example == rec.code_example


class TestFixesTemplate:
    """Tests for FixesTemplate dataclass."""

    def test_basic_creation(self):
        """Test basic template creation."""
        template = FixesTemplate(
            subcategory_id="classic",
            subcategory_name="Classic Reentrancy",
        )
        assert template.recommendations == []
        assert template.testing_strategies == []

    def test_full_creation(self):
        """Test creation with all fields."""
        rec = FixRecommendationExtended(
            name="Use ReentrancyGuard",
            description="Add OpenZeppelin ReentrancyGuard",
            code_example="nonReentrant modifier",
        )
        template = FixesTemplate(
            subcategory_id="classic",
            subcategory_name="Classic Reentrancy",
            category_id="reentrancy",
            overview="Reentrancy can be prevented with guards or CEI pattern",
            recommendations=[rec],
            code_examples=[
                {"name": "CEI Pattern", "code": "// CEI example", "description": "Checks-Effects-Interactions"}
            ],
            testing_strategies=[
                "Create malicious contract that attempts reentry",
                "Fuzz test with random callback sequences",
            ],
            tools=["Slither", "Echidna"],
            audit_checklist=[
                "Verify all external calls have reentrancy protection",
                "Check for cross-function reentrancy",
            ],
        )

        assert len(template.recommendations) == 1
        assert len(template.testing_strategies) == 2
        assert len(template.tools) == 2

    def test_serialization_roundtrip(self):
        """Test serialization and deserialization."""
        rec = FixRecommendationExtended(
            name="Test Fix",
            description="Test description",
        )
        template = FixesTemplate(
            subcategory_id="classic",
            subcategory_name="Classic Reentrancy",
            recommendations=[rec],
        )

        data = template.to_dict()
        restored = FixesTemplate.from_dict(data)

        assert len(restored.recommendations) == 1
        assert restored.recommendations[0].name == "Test Fix"

    def test_render_method(self):
        """Test template render method."""
        rec = FixRecommendationExtended(
            name="Use ReentrancyGuard",
            description="Add OpenZeppelin ReentrancyGuard",
            code_example="modifier nonReentrant() { ... }",
            testing_strategy="Test with reentrant calls",
        )
        template = FixesTemplate(
            subcategory_id="classic",
            subcategory_name="Classic Reentrancy",
            recommendations=[rec],
            audit_checklist=["Check for reentrancy guards"],
        )

        md = template.render()

        assert "# Fixes: Classic Reentrancy" in md
        assert "ReentrancyGuard" in md
        assert "nonReentrant()" in md
        assert "Audit Checklist" in md


# =============================================================================
# MARKDOWN RENDERING TESTS
# =============================================================================


class TestRenderDetectionMd:
    """Tests for render_detection_md function."""

    def test_basic_rendering(self):
        """Test basic markdown rendering."""
        signal = GraphSignal(
            property_name="test_property",
            expected=True,
            critical=True,
        )
        md = render_detection_md(
            subcategory="Test Subcategory",
            signals=[signal],
            checks=["Check 1", "Check 2"],
        )

        assert "# Detection: Test Subcategory" in md
        assert "test_property" in md
        assert "Check 1" in md

    def test_full_rendering(self):
        """Test rendering with all sections."""
        signal = GraphSignal(
            property_name="test_property",
            expected=True,
            critical=True,
        )
        op_seq = OperationSequences(
            vulnerable=["A -> B -> C"],
            safe=["A -> C -> B"],
        )
        md = render_detection_md(
            subcategory="Test Subcategory",
            signals=[signal],
            checks=["Check 1"],
            overview="Test overview",
            behavioral_signatures=["sig1", "sig2"],
            operation_sequences=op_seq,
            false_positive_indicators=["FP indicator"],
            severity="critical",
            confidence_notes="High confidence",
            related_patterns=["pattern-001"],
            category="Test Category",
        )

        assert "## Overview" in md
        assert "## Graph Signals" in md
        assert "## Behavioral Signatures" in md
        assert "## Operation Sequences" in md
        assert "## Detection Checklist" in md
        assert "## False Positive Indicators" in md
        assert "## Confidence Notes" in md
        assert "## Related Patterns" in md


class TestRenderPatternsMd:
    """Tests for render_patterns_md function."""

    def test_basic_rendering(self):
        """Test basic markdown rendering."""
        vuln_pattern = CodePattern(
            name="Vuln Pattern",
            vulnerable_code="// vulnerable",
        )
        md = render_patterns_md(
            subcategory="Test Subcategory",
            vulnerable_patterns=[vuln_pattern],
            safe_patterns=[],
        )

        assert "# Patterns: Test Subcategory" in md
        assert "Vuln Pattern" in md
        assert "// vulnerable" in md

    def test_full_rendering(self):
        """Test rendering with all sections."""
        vuln_pattern = CodePattern(
            name="Vuln Pattern",
            vulnerable_code="// vulnerable",
            description="A vulnerable pattern",
            severity="high",
        )
        safe_pattern = CodePattern(
            name="Safe Pattern",
            vulnerable_code="",
            safe_code="// safe",
            description="A safe pattern",
        )
        md = render_patterns_md(
            subcategory="Test Subcategory",
            vulnerable_patterns=[vuln_pattern],
            safe_patterns=[safe_pattern],
            overview="Pattern overview",
            edge_cases=["Edge case 1"],
            pattern_ids=["pattern-001"],
            common_mistakes=["Mistake 1"],
            best_practices=["Best practice 1"],
        )

        assert "## Overview" in md
        assert "## Vulnerable Patterns" in md
        assert "## Safe Patterns" in md
        assert "## Edge Cases" in md
        assert "## Common Mistakes" in md
        assert "## Best Practices" in md


class TestRenderExploitsMd:
    """Tests for render_exploits_md function."""

    def test_basic_rendering(self):
        """Test basic markdown rendering."""
        incident = ExploitIncident(
            id="test-001",
            name="Test Exploit",
            date="2024-01-01",
            loss_usd="1,000,000",
        )
        md = render_exploits_md(
            subcategory="Test Subcategory",
            exploits=[incident],
        )

        assert "# Exploits: Test Subcategory" in md
        assert "Test Exploit" in md
        assert "$1,000,000" in md

    def test_full_rendering(self):
        """Test rendering with all sections."""
        incident = ExploitIncident(
            id="test-001",
            name="Test Exploit",
            date="2024-01-01",
            loss_usd="1,000,000",
            protocol="Test Protocol",
            description="Test description",
            attack_steps=["Step 1", "Step 2"],
            postmortem_url="https://example.com",
        )
        md = render_exploits_md(
            subcategory="Test Subcategory",
            exploits=[incident],
            overview="Exploit overview",
            attack_vectors=["Vector 1"],
            total_losses="10,000,000",
            common_targets=["DeFi"],
        )

        assert "## Overview" in md
        assert "## Summary" in md
        assert "## Attack Vectors" in md
        assert "## Incidents" in md
        assert "**Attack Steps:**" in md


class TestRenderFixesMd:
    """Tests for render_fixes_md function."""

    def test_basic_rendering(self):
        """Test basic markdown rendering."""
        rec = FixRecommendationExtended(
            name="Test Fix",
            description="Test description",
        )
        md = render_fixes_md(
            subcategory="Test Subcategory",
            recommendations=[rec],
        )

        assert "# Fixes: Test Subcategory" in md
        assert "Test Fix" in md
        assert "Test description" in md

    def test_full_rendering(self):
        """Test rendering with all sections."""
        rec = FixRecommendationExtended(
            name="Test Fix",
            description="Test description",
            code_example="// fix code",
            testing_strategy="Test strategy",
            migration_notes="Migration notes",
            dependencies=["dep1"],
            gas_impact="~100 gas",
        )
        md = render_fixes_md(
            subcategory="Test Subcategory",
            recommendations=[rec],
            overview="Fix overview",
            code_examples=[{"name": "Example", "code": "// code", "description": "desc"}],
            testing_strategies=["Strategy 1"],
            tools=["Tool 1"],
            audit_checklist=["Item 1"],
        )

        assert "## Overview" in md
        assert "## Recommendations" in md
        assert "## Code Examples" in md
        assert "## Testing Strategies" in md
        assert "## Recommended Tools" in md
        assert "## Audit Checklist" in md


# =============================================================================
# TEMPLATE GENERATION TESTS
# =============================================================================


class TestGenerateDocumentTemplates:
    """Tests for generate_document_templates function."""

    def test_basic_generation(self):
        """Test basic template generation."""
        templates = generate_document_templates("reentrancy", "classic")

        assert "detection" in templates
        assert "patterns" in templates
        assert "exploits" in templates
        assert "fixes" in templates

    def test_generated_content(self):
        """Test generated content has expected structure."""
        templates = generate_document_templates("reentrancy", "classic")

        # Detection should have expected sections
        assert "# Detection: Classic" in templates["detection"]
        assert "## Graph Signals" in templates["detection"]
        assert "[TODO:" in templates["detection"]

        # Patterns should have expected sections
        assert "# Patterns: Classic" in templates["patterns"]
        assert "## Vulnerable Patterns" in templates["patterns"]

        # Exploits should have expected sections
        assert "# Exploits: Classic" in templates["exploits"]
        assert "## Incidents" in templates["exploits"]

        # Fixes should have expected sections
        assert "# Fixes: Classic" in templates["fixes"]
        assert "## Recommendations" in templates["fixes"]

    def test_custom_names(self):
        """Test generation with custom names."""
        templates = generate_document_templates(
            category_id="reentrancy",
            subcategory_id="classic",
            category_name="Reentrancy Vulnerabilities",
            subcategory_name="Classic Reentrancy",
        )

        assert "Classic Reentrancy" in templates["detection"]
        assert "Reentrancy Vulnerabilities" in templates["detection"]


class TestCreateTemplateBundle:
    """Tests for create_template_bundle function."""

    def test_bundle_structure(self):
        """Test bundle has expected structure."""
        bundle = create_template_bundle("reentrancy", "classic")

        assert "templates" in bundle
        assert "markdown" in bundle
        assert "metadata" in bundle

    def test_templates_section(self):
        """Test templates section contains template instances."""
        bundle = create_template_bundle("reentrancy", "classic")
        templates = bundle["templates"]

        assert isinstance(templates["detection"], DetectionTemplate)
        assert isinstance(templates["patterns"], PatternsTemplate)
        assert isinstance(templates["exploits"], ExploitsTemplate)
        assert isinstance(templates["fixes"], FixesTemplate)

    def test_markdown_section(self):
        """Test markdown section contains strings."""
        bundle = create_template_bundle("reentrancy", "classic")
        markdown = bundle["markdown"]

        assert isinstance(markdown["detection"], str)
        assert isinstance(markdown["patterns"], str)
        assert isinstance(markdown["exploits"], str)
        assert isinstance(markdown["fixes"], str)

    def test_metadata_section(self):
        """Test metadata section contains expected fields."""
        bundle = create_template_bundle("reentrancy", "classic")
        metadata = bundle["metadata"]

        assert metadata["category_id"] == "reentrancy"
        assert metadata["subcategory_id"] == "classic"
        assert "template_version" in metadata
        assert "generated_at" in metadata


# =============================================================================
# TEMPLATE VALIDATION TESTS
# =============================================================================


class TestValidateDetectionTemplate:
    """Tests for validate_detection_template function."""

    def test_valid_template(self):
        """Test validation of valid template."""
        template = DetectionTemplate(
            subcategory_id="classic",
            subcategory_name="Classic Reentrancy",
        )
        errors = validate_detection_template(template)
        assert len(errors) == 0

    def test_missing_id(self):
        """Test validation catches missing ID."""
        template = DetectionTemplate(
            subcategory_id="",
            subcategory_name="Classic Reentrancy",
        )
        errors = validate_detection_template(template)
        assert any("subcategory_id" in e for e in errors)

    def test_missing_name(self):
        """Test validation catches missing name."""
        template = DetectionTemplate(
            subcategory_id="classic",
            subcategory_name="",
        )
        errors = validate_detection_template(template)
        assert any("subcategory_name" in e for e in errors)


class TestValidatePatternsTemplate:
    """Tests for validate_patterns_template function."""

    def test_valid_template(self):
        """Test validation of valid template."""
        template = PatternsTemplate(
            subcategory_id="classic",
            subcategory_name="Classic Reentrancy",
        )
        errors = validate_patterns_template(template)
        assert len(errors) == 0

    def test_missing_fields(self):
        """Test validation catches missing fields."""
        template = PatternsTemplate(
            subcategory_id="",
            subcategory_name="",
        )
        errors = validate_patterns_template(template)
        assert len(errors) >= 2


class TestValidateExploitsTemplate:
    """Tests for validate_exploits_template function."""

    def test_valid_template(self):
        """Test validation of valid template."""
        template = ExploitsTemplate(
            subcategory_id="classic",
            subcategory_name="Classic Reentrancy",
        )
        errors = validate_exploits_template(template)
        assert len(errors) == 0

    def test_invalid_incident(self):
        """Test validation catches invalid incident."""
        incident = ExploitIncident(
            id="",
            name="",
        )
        template = ExploitsTemplate(
            subcategory_id="classic",
            subcategory_name="Classic Reentrancy",
            incidents=[incident],
        )
        errors = validate_exploits_template(template)
        assert any("id" in e for e in errors)
        assert any("name" in e for e in errors)


class TestValidateFixesTemplate:
    """Tests for validate_fixes_template function."""

    def test_valid_template(self):
        """Test validation of valid template."""
        template = FixesTemplate(
            subcategory_id="classic",
            subcategory_name="Classic Reentrancy",
        )
        errors = validate_fixes_template(template)
        assert len(errors) == 0

    def test_invalid_recommendation(self):
        """Test validation catches invalid recommendation."""
        rec = FixRecommendationExtended(
            name="",
            description="",
        )
        template = FixesTemplate(
            subcategory_id="classic",
            subcategory_name="Classic Reentrancy",
            recommendations=[rec],
        )
        errors = validate_fixes_template(template)
        assert any("name" in e for e in errors)
        assert any("description" in e for e in errors)


# =============================================================================
# CONSTANTS TESTS
# =============================================================================


class TestConstants:
    """Tests for template constants."""

    def test_template_version(self):
        """Test TEMPLATE_VERSION is set."""
        assert TEMPLATE_VERSION == "1.0"

    def test_token_budget(self):
        """Test TOKEN_BUDGET has expected keys."""
        assert "detection" in TOKEN_BUDGET
        assert "patterns" in TOKEN_BUDGET
        assert "exploits" in TOKEN_BUDGET
        assert "fixes" in TOKEN_BUDGET

        # Ensure budgets are reasonable
        for key, value in TOKEN_BUDGET.items():
            assert isinstance(value, int)
            assert value > 0
            assert value < 10000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
