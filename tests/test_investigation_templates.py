"""Tests for investigation templates.

Tests the YAML investigation templates and their loader functions.
Ensures all 7 vulnerability class templates are present and valid.
"""

import pytest

from alphaswarm_sol.beads.templates import (
    load_template,
    list_available_templates,
    get_template_version,
    get_template_metadata,
    clear_cache,
)
from alphaswarm_sol.beads.schema import InvestigationGuide
from alphaswarm_sol.beads.types import InvestigationStep


# Required templates that must exist
REQUIRED_TEMPLATES = [
    "reentrancy",
    "access_control",
    "oracle",
    "dos",
    "mev",
    "token",
    "upgrade",
]


class TestTemplateLoader:
    """Tests for template loading functionality."""

    def setup_method(self):
        """Clear cache before each test to ensure fresh loads."""
        clear_cache()

    def test_all_required_templates_exist(self):
        """All 7 required templates must be available."""
        available = list_available_templates()
        for required in REQUIRED_TEMPLATES:
            assert required in available, f"Missing required template: {required}"

    def test_list_templates_returns_sorted(self):
        """list_available_templates returns sorted list."""
        available = list_available_templates()
        assert available == sorted(available), "Templates should be sorted"

    def test_list_templates_returns_list(self):
        """list_available_templates returns a list."""
        available = list_available_templates()
        assert isinstance(available, list)
        assert len(available) >= 7, "Should have at least 7 templates"

    @pytest.mark.parametrize("class_name", REQUIRED_TEMPLATES)
    def test_template_loads_successfully(self, class_name):
        """Each required template loads without error."""
        guide = load_template(class_name)
        assert guide is not None, f"Failed to load template: {class_name}"

    @pytest.mark.parametrize("class_name", REQUIRED_TEMPLATES)
    def test_template_returns_investigation_guide(self, class_name):
        """Loaded template returns InvestigationGuide type."""
        guide = load_template(class_name)
        assert isinstance(guide, InvestigationGuide)

    def test_unknown_template_returns_none(self):
        """Unknown template name returns None, not error."""
        guide = load_template("nonexistent_class")
        assert guide is None

    def test_template_loading_normalizes_names(self):
        """Template loader normalizes various input formats."""
        # Test hyphenated name
        guide1 = load_template("access-control")
        assert guide1 is not None

        # Test space-separated name
        guide2 = load_template("access control")
        assert guide2 is not None

        # Test underscore name (standard)
        guide3 = load_template("access_control")
        assert guide3 is not None

        # All should be the same template
        assert len(guide1.steps) == len(guide2.steps) == len(guide3.steps)

    def test_template_loading_case_insensitive(self):
        """Template loading is case-insensitive."""
        guide1 = load_template("REENTRANCY")
        guide2 = load_template("reentrancy")
        guide3 = load_template("ReEnTrAnCy")

        assert guide1 is not None
        assert guide2 is not None
        assert guide3 is not None


class TestTemplateSteps:
    """Tests for investigation steps in templates."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()

    @pytest.mark.parametrize("class_name", REQUIRED_TEMPLATES)
    def test_template_has_at_least_3_steps(self, class_name):
        """Each template needs at least 3 investigation steps."""
        guide = load_template(class_name)
        assert len(guide.steps) >= 3, f"{class_name} needs at least 3 steps, has {len(guide.steps)}"

    @pytest.mark.parametrize("class_name", REQUIRED_TEMPLATES)
    def test_template_has_5_steps(self, class_name):
        """Each template should have exactly 5 investigation steps."""
        guide = load_template(class_name)
        assert len(guide.steps) == 5, f"{class_name} should have 5 steps, has {len(guide.steps)}"

    @pytest.mark.parametrize("class_name", REQUIRED_TEMPLATES)
    def test_steps_are_investigation_step_type(self, class_name):
        """Steps should be InvestigationStep instances."""
        guide = load_template(class_name)
        for step in guide.steps:
            assert isinstance(step, InvestigationStep)

    @pytest.mark.parametrize("class_name", REQUIRED_TEMPLATES)
    def test_steps_are_numbered_correctly(self, class_name):
        """Steps should be numbered 1 through N."""
        guide = load_template(class_name)
        for i, step in enumerate(guide.steps, 1):
            assert step.step_number == i, f"Step {i} has wrong number: {step.step_number}"

    @pytest.mark.parametrize("class_name", REQUIRED_TEMPLATES)
    def test_steps_have_required_fields(self, class_name):
        """Each step has required action, look_for, evidence_needed."""
        guide = load_template(class_name)
        for step in guide.steps:
            assert step.action, f"Step {step.step_number} missing action"
            assert step.look_for, f"Step {step.step_number} missing look_for"
            assert step.evidence_needed, f"Step {step.step_number} missing evidence_needed"

    def test_reentrancy_steps_cover_key_aspects(self):
        """Reentrancy template covers critical investigation aspects."""
        guide = load_template("reentrancy")
        step_actions = [s.action.lower() for s in guide.steps]

        # Should cover: external call, state changes, protection, target control, impact
        assert any("external" in a for a in step_actions), "Should check external calls"
        assert any("state" in a for a in step_actions), "Should check state changes"
        assert any("protect" in a or "guard" in a for a in step_actions), "Should check protection"


class TestTemplateQuestions:
    """Tests for questions_to_answer in templates."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()

    @pytest.mark.parametrize("class_name", REQUIRED_TEMPLATES)
    def test_template_has_questions(self, class_name):
        """Each template must have questions to answer."""
        guide = load_template(class_name)
        assert len(guide.questions_to_answer) >= 3, f"{class_name} needs at least 3 questions"

    @pytest.mark.parametrize("class_name", REQUIRED_TEMPLATES)
    def test_questions_are_strings(self, class_name):
        """Questions should be non-empty strings."""
        guide = load_template(class_name)
        for q in guide.questions_to_answer:
            assert isinstance(q, str)
            assert len(q) > 10, "Question too short to be meaningful"

    @pytest.mark.parametrize("class_name", REQUIRED_TEMPLATES)
    def test_questions_end_with_question_mark(self, class_name):
        """Questions should end with '?'."""
        guide = load_template(class_name)
        for q in guide.questions_to_answer:
            assert q.strip().endswith("?"), f"Question should end with ?: {q[:50]}"


class TestTemplateFalsePositives:
    """Tests for common_false_positives in templates."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()

    @pytest.mark.parametrize("class_name", REQUIRED_TEMPLATES)
    def test_template_has_false_positives(self, class_name):
        """Each template must list common false positives."""
        guide = load_template(class_name)
        assert len(guide.common_false_positives) >= 2, f"{class_name} needs at least 2 FPs"

    @pytest.mark.parametrize("class_name", REQUIRED_TEMPLATES)
    def test_false_positives_are_descriptive(self, class_name):
        """False positive descriptions should be meaningful."""
        guide = load_template(class_name)
        for fp in guide.common_false_positives:
            assert isinstance(fp, str)
            assert len(fp) > 15, f"FP too short: {fp}"


class TestTemplateIndicators:
    """Tests for key_indicators and safe_patterns in templates."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()

    @pytest.mark.parametrize("class_name", REQUIRED_TEMPLATES)
    def test_template_has_key_indicators(self, class_name):
        """Each template must have key vulnerability indicators."""
        guide = load_template(class_name)
        assert len(guide.key_indicators) >= 2, f"{class_name} needs at least 2 key indicators"

    @pytest.mark.parametrize("class_name", REQUIRED_TEMPLATES)
    def test_template_has_safe_patterns(self, class_name):
        """Each template must list safe patterns."""
        guide = load_template(class_name)
        assert len(guide.safe_patterns) >= 2, f"{class_name} needs at least 2 safe patterns"


class TestTemplateVersion:
    """Tests for template versioning."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()

    @pytest.mark.parametrize("class_name", REQUIRED_TEMPLATES)
    def test_template_has_version(self, class_name):
        """Each template must have a version."""
        version = get_template_version(class_name)
        assert version is not None, f"{class_name} missing version"

    @pytest.mark.parametrize("class_name", REQUIRED_TEMPLATES)
    def test_version_is_string(self, class_name):
        """Version should be a string."""
        version = get_template_version(class_name)
        assert isinstance(version, str)
        assert version, "Version should not be empty"

    def test_unknown_template_version_returns_none(self):
        """Unknown template returns None for version."""
        version = get_template_version("nonexistent")
        assert version is None


class TestTemplateMetadata:
    """Tests for template metadata."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()

    @pytest.mark.parametrize("class_name", REQUIRED_TEMPLATES)
    def test_template_has_metadata(self, class_name):
        """Each template should have metadata."""
        meta = get_template_metadata(class_name)
        assert meta is not None

    @pytest.mark.parametrize("class_name", REQUIRED_TEMPLATES)
    def test_metadata_has_required_fields(self, class_name):
        """Metadata should include version, last_updated, vulnerability_class."""
        meta = get_template_metadata(class_name)
        assert "version" in meta
        assert "last_updated" in meta
        assert "vulnerability_class" in meta

    @pytest.mark.parametrize("class_name", REQUIRED_TEMPLATES)
    def test_metadata_vulnerability_class_matches(self, class_name):
        """Metadata vulnerability_class should match the template name."""
        meta = get_template_metadata(class_name)
        assert meta["vulnerability_class"] == class_name

    def test_unknown_template_metadata_returns_none(self):
        """Unknown template returns None for metadata."""
        meta = get_template_metadata("nonexistent")
        assert meta is None


class TestTemplateCache:
    """Tests for template caching."""

    def test_clear_cache_works(self):
        """clear_cache clears the cache."""
        # Load a template (populates cache)
        load_template("reentrancy")

        # Clear cache
        clear_cache()

        # Can still load (proves function works)
        guide = load_template("reentrancy")
        assert guide is not None

    def test_cached_templates_are_identical(self):
        """Multiple loads return identical data."""
        guide1 = load_template("reentrancy")
        guide2 = load_template("reentrancy")

        assert len(guide1.steps) == len(guide2.steps)
        assert guide1.questions_to_answer == guide2.questions_to_answer


class TestTemplateIntegration:
    """Integration tests for templates with beads system."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()

    def test_template_guide_can_be_serialized(self):
        """Loaded guide can be converted to dict and back."""
        guide = load_template("reentrancy")

        # Convert to dict
        data = guide.to_dict()
        assert isinstance(data, dict)
        assert "steps" in data
        assert "questions_to_answer" in data

        # Convert back
        restored = InvestigationGuide.from_dict(data)
        assert len(restored.steps) == len(guide.steps)
        assert restored.questions_to_answer == guide.questions_to_answer

    def test_all_templates_serializable(self):
        """All templates can be serialized and deserialized."""
        for class_name in REQUIRED_TEMPLATES:
            guide = load_template(class_name)
            data = guide.to_dict()
            restored = InvestigationGuide.from_dict(data)

            assert len(restored.steps) == len(guide.steps)
            assert restored.questions_to_answer == guide.questions_to_answer
            assert restored.common_false_positives == guide.common_false_positives
            assert restored.key_indicators == guide.key_indicators
            assert restored.safe_patterns == guide.safe_patterns


class TestSpecificTemplateContent:
    """Tests for specific content in individual templates."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()

    def test_reentrancy_template_content(self):
        """Reentrancy template has correct content."""
        guide = load_template("reentrancy")

        # Check for critical content
        questions = " ".join(guide.questions_to_answer).lower()
        assert "external call" in questions
        assert "reentrancy guard" in questions or "guard" in questions

        # Check safe patterns include CEI
        safe = " ".join(guide.safe_patterns).lower()
        assert "cei" in safe or "checks-effects-interactions" in safe

    def test_access_control_template_content(self):
        """Access control template has correct content."""
        guide = load_template("access_control")

        # Check for access control specific content
        questions = " ".join(guide.questions_to_answer).lower()
        assert "access control" in questions or "who" in questions

        # Check safe patterns mention common protections
        safe = " ".join(guide.safe_patterns).lower()
        assert "onlyowner" in safe or "role" in safe or "accesscontrol" in safe

    def test_oracle_template_content(self):
        """Oracle template has correct content."""
        guide = load_template("oracle")

        # Check for oracle specific content
        questions = " ".join(guide.questions_to_answer).lower()
        assert "staleness" in questions or "oracle" in questions

    def test_dos_template_content(self):
        """DoS template has correct content."""
        guide = load_template("dos")

        # Check for DoS specific content
        questions = " ".join(guide.questions_to_answer).lower()
        assert "loop" in questions or "iteration" in questions

    def test_mev_template_content(self):
        """MEV template has correct content."""
        guide = load_template("mev")

        # Check for MEV specific content
        questions = " ".join(guide.questions_to_answer).lower()
        assert "slippage" in questions or "sandwich" in questions or "mev" in questions

    def test_token_template_content(self):
        """Token template has correct content."""
        guide = load_template("token")

        # Check for token specific content
        questions = " ".join(guide.questions_to_answer).lower()
        assert "transfer" in questions or "token" in questions

    def test_upgrade_template_content(self):
        """Upgrade template has correct content."""
        guide = load_template("upgrade")

        # Check for upgrade specific content
        questions = " ".join(guide.questions_to_answer).lower()
        assert "initialize" in questions or "upgrade" in questions or "proxy" in questions
