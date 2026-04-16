"""Tests for prompt linting (Phase 7.1.3-05).

Tests lint rules for detecting:
- Oversized sections
- Duplicate context
- Missing constraints
- Unused tools
- Prompt size budget
"""

import pytest

from alphaswarm_sol.llm.prompt_lint import (
    DuplicateContextRule,
    LintSeverity,
    LintViolation,
    MissingConstraintRule,
    OversizedSectionRule,
    PromptLinter,
    PromptLintReport,
    PromptSizeRule,
    UnusedToolRule,
    create_linter,
    get_default_rules,
    lint_prompt,
)


class TestLintViolation:
    """Tests for LintViolation dataclass."""

    def test_violation_creation(self):
        """Test basic violation creation."""
        violation = LintViolation(
            rule_id="test-rule",
            severity=LintSeverity.WARN,
            message="Test message",
        )
        assert violation.rule_id == "test-rule"
        assert violation.severity == LintSeverity.WARN
        assert violation.message == "Test message"
        assert violation.location is None
        assert violation.token_impact == 0

    def test_violation_with_all_fields(self):
        """Test violation with all fields."""
        violation = LintViolation(
            rule_id="test-rule",
            severity=LintSeverity.ERROR,
            message="Test message",
            location="line_42",
            suggestion="Fix it",
            token_impact=100,
        )
        assert violation.location == "line_42"
        assert violation.suggestion == "Fix it"
        assert violation.token_impact == 100

    def test_violation_to_dict(self):
        """Test serialization to dict."""
        violation = LintViolation(
            rule_id="test-rule",
            severity=LintSeverity.WARN,
            message="Test message",
            token_impact=50,
        )
        d = violation.to_dict()
        assert d["rule_id"] == "test-rule"
        assert d["severity"] == "warn"
        assert d["message"] == "Test message"
        assert d["token_impact"] == 50


class TestPromptLintReport:
    """Tests for PromptLintReport."""

    def test_empty_report(self):
        """Test report with no violations."""
        report = PromptLintReport()
        assert not report.has_violations
        assert not report.has_warnings
        assert not report.has_errors
        assert report.error_count == 0
        assert report.warning_count == 0

    def test_report_with_violations(self):
        """Test report with various violations."""
        report = PromptLintReport(
            violations=[
                LintViolation("r1", LintSeverity.ERROR, "Error"),
                LintViolation("r2", LintSeverity.WARN, "Warning"),
                LintViolation("r3", LintSeverity.INFO, "Info"),
            ],
            prompt_tokens=1000,
            wasteful_tokens=200,
        )
        assert report.has_violations
        assert report.has_warnings
        assert report.has_errors
        assert report.error_count == 1
        assert report.warning_count == 1
        assert report.info_count == 1

    def test_report_summary(self):
        """Test summary generation."""
        report = PromptLintReport(
            violations=[
                LintViolation("r1", LintSeverity.WARN, "Test warning"),
            ],
            prompt_tokens=1000,
            wasteful_tokens=50,
        )
        summary = report.summary()
        assert "1 errors" not in summary or "0 errors" in summary
        assert "1 warnings" in summary
        assert "Test warning" in summary

    def test_empty_report_summary(self):
        """Test summary for clean report."""
        report = PromptLintReport(prompt_tokens=500)
        summary = report.summary()
        assert "OK" in summary
        assert "500 tokens" in summary

    def test_report_to_dict(self):
        """Test serialization to dict."""
        report = PromptLintReport(
            violations=[LintViolation("r1", LintSeverity.WARN, "Test")],
            prompt_tokens=1000,
            wasteful_tokens=100,
            rules_applied=["r1", "r2"],
        )
        d = report.to_dict()
        assert len(d["violations"]) == 1
        assert d["prompt_tokens"] == 1000
        assert d["wasteful_tokens"] == 100
        assert d["summary"]["has_warnings"] is True


class TestOversizedSectionRule:
    """Tests for OversizedSectionRule."""

    def test_rule_id(self):
        """Test rule has correct ID."""
        rule = OversizedSectionRule()
        assert rule.rule_id == "oversized-section"

    def test_small_code_block_passes(self):
        """Test small code blocks don't trigger violations."""
        rule = OversizedSectionRule()
        prompt = "```solidity\nfunction test() {}\n```"
        violations = rule.check(prompt, {})
        assert len(violations) == 0

    def test_large_code_block_fails(self):
        """Test large code blocks trigger warnings."""
        rule = OversizedSectionRule()
        # Create code block over 2000 chars
        large_code = "x" * 2500
        prompt = f"```solidity\n{large_code}\n```"
        violations = rule.check(prompt, {})
        assert len(violations) == 1
        assert violations[0].severity == LintSeverity.WARN
        assert "code block" in violations[0].message.lower()
        assert violations[0].token_impact > 0

    def test_large_metadata_section_fails(self):
        """Test large metadata section triggers warning."""
        rule = OversizedSectionRule()
        large_metadata = "key: value\n" * 200  # >1000 chars
        prompt = f"## Metadata\n{large_metadata}\n## Next"
        violations = rule.check(prompt, {})
        assert len(violations) == 1
        assert "metadata" in violations[0].location

    def test_large_source_section_fails(self):
        """Test large source section triggers warning."""
        rule = OversizedSectionRule()
        large_source = "// code\n" * 500  # >3000 chars
        prompt = f"## Source\n{large_source}\n## Next"
        violations = rule.check(prompt, {})
        assert len(violations) == 1
        assert "raw_source" in violations[0].location


class TestDuplicateContextRule:
    """Tests for DuplicateContextRule."""

    def test_rule_id(self):
        """Test rule has correct ID."""
        rule = DuplicateContextRule()
        assert rule.rule_id == "duplicate-context"

    def test_no_duplicates_passes(self):
        """Test unique content passes."""
        rule = DuplicateContextRule()
        prompt = "Evidence ID: E-ABC123\nfile: Vault.sol"
        violations = rule.check(prompt, {})
        assert len(violations) == 0

    def test_duplicate_evidence_ids_fails(self):
        """Test duplicate evidence IDs trigger warning."""
        rule = DuplicateContextRule()
        prompt = """
        Evidence: E-ABC123
        Evidence: E-ABC123
        Evidence: E-DEF456
        Evidence: E-ABC123
        """
        violations = rule.check(prompt, {})
        assert len(violations) >= 1
        assert any("evidence" in v.location for v in violations)

    def test_repeated_file_paths_fails(self):
        """Test repeated file paths trigger info."""
        rule = DuplicateContextRule()
        prompt = """
        file: Vault.sol
        file: Vault.sol
        file: Vault.sol
        file: Vault.sol
        file: Vault.sol
        """
        violations = rule.check(prompt, {})
        # Should trigger info for >2 repetitions
        path_violations = [v for v in violations if "file_path" in v.location]
        assert len(path_violations) >= 1
        assert path_violations[0].severity == LintSeverity.INFO


class TestMissingConstraintRule:
    """Tests for MissingConstraintRule."""

    def test_rule_id(self):
        """Test rule has correct ID."""
        rule = MissingConstraintRule()
        assert rule.rule_id == "missing-constraint"

    def test_missing_evidence_constraint(self):
        """Test missing evidence requirement triggers warning."""
        rule = MissingConstraintRule()
        prompt = "Analyze this code and provide verdict"
        violations = rule.check(prompt, {})
        evidence_violations = [v for v in violations if "evidence" in v.message.lower()]
        assert len(evidence_violations) == 1
        assert evidence_violations[0].severity == LintSeverity.WARN

    def test_with_evidence_constraint_passes(self):
        """Test prompt with evidence requirement passes."""
        rule = MissingConstraintRule()
        prompt = "Analyze this code and cite evidence IDs"
        violations = rule.check(prompt, {})
        evidence_violations = [v for v in violations if "evidence" in v.message.lower()]
        assert len(evidence_violations) == 0

    def test_missing_schema_info(self):
        """Test missing output schema triggers info."""
        rule = MissingConstraintRule()
        prompt = "Analyze this code"
        violations = rule.check(prompt, {})
        schema_violations = [v for v in violations if "schema" in v.message.lower()]
        assert len(schema_violations) == 1
        assert schema_violations[0].severity == LintSeverity.INFO

    def test_with_schema_passes(self):
        """Test prompt with output schema passes."""
        rule = MissingConstraintRule()
        prompt = 'Output Schema: {"type": "object"}'
        violations = rule.check(prompt, {"output_schema": {}})
        schema_violations = [v for v in violations if "schema" in v.message.lower()]
        assert len(schema_violations) == 0


class TestUnusedToolRule:
    """Tests for UnusedToolRule."""

    def test_rule_id(self):
        """Test rule has correct ID."""
        rule = UnusedToolRule()
        assert rule.rule_id == "unused-tool"

    def test_no_tools_context_passes(self):
        """Test prompts with no tool constraints pass."""
        rule = UnusedToolRule()
        prompt = "Use tool: slither to analyze"
        violations = rule.check(prompt, {})  # No allowed_tools
        assert len(violations) == 0

    def test_allowed_tool_passes(self):
        """Test allowed tool reference passes."""
        rule = UnusedToolRule()
        prompt = "Use tool: slither to analyze"
        violations = rule.check(prompt, {"allowed_tools": ["slither", "aderyn"]})
        assert len(violations) == 0

    def test_unknown_tool_fails(self):
        """Test unknown tool reference triggers warning."""
        rule = UnusedToolRule()
        prompt = "Use tool: unknown_tool to analyze"
        violations = rule.check(prompt, {"allowed_tools": ["slither", "aderyn"]})
        assert len(violations) == 1
        assert violations[0].severity == LintSeverity.WARN
        assert "unknown_tool" in violations[0].message


class TestPromptSizeRule:
    """Tests for PromptSizeRule."""

    def test_rule_id(self):
        """Test rule has correct ID."""
        rule = PromptSizeRule()
        assert rule.rule_id == "prompt-size"

    def test_small_prompt_passes(self):
        """Test small prompts pass."""
        rule = PromptSizeRule()
        prompt = "Analyze this code"
        violations = rule.check(prompt, {"max_tokens": 6000})
        assert len(violations) == 0

    def test_large_prompt_fails(self):
        """Test oversized prompts trigger error."""
        rule = PromptSizeRule()
        # ~7500 tokens at 4 chars/token
        prompt = "x" * 30000
        violations = rule.check(prompt, {"max_tokens": 6000})
        assert len(violations) == 1
        assert violations[0].severity == LintSeverity.ERROR
        assert "exceeds" in violations[0].message.lower()

    def test_approaching_limit_warns(self):
        """Test prompts approaching limit trigger warning."""
        rule = PromptSizeRule()
        # ~5000 tokens (>80% of 6000)
        prompt = "x" * 20000
        violations = rule.check(prompt, {"max_tokens": 6000})
        assert len(violations) == 1
        assert violations[0].severity == LintSeverity.WARN


class TestPromptLinter:
    """Tests for PromptLinter class."""

    def test_default_rules(self):
        """Test linter has default rules."""
        linter = PromptLinter()
        assert len(linter.rules) > 0
        rule_ids = [r.rule_id for r in linter.rules]
        assert "oversized-section" in rule_ids
        assert "duplicate-context" in rule_ids

    def test_custom_rules(self):
        """Test linter with custom rules."""
        linter = PromptLinter(rules=[OversizedSectionRule()])
        assert len(linter.rules) == 1

    def test_add_rule(self):
        """Test adding a rule."""
        linter = PromptLinter(rules=[])
        linter.add_rule(OversizedSectionRule())
        assert len(linter.rules) == 1

    def test_remove_rule(self):
        """Test removing a rule."""
        linter = PromptLinter(rules=[OversizedSectionRule(), DuplicateContextRule()])
        removed = linter.remove_rule("oversized-section")
        assert removed is True
        assert len(linter.rules) == 1
        assert linter.rules[0].rule_id == "duplicate-context"

    def test_remove_nonexistent_rule(self):
        """Test removing non-existent rule returns False."""
        linter = PromptLinter(rules=[])
        removed = linter.remove_rule("nonexistent")
        assert removed is False

    def test_lint_returns_report(self):
        """Test lint returns a report."""
        linter = PromptLinter()
        report = linter.lint("Test prompt")
        assert isinstance(report, PromptLintReport)
        assert report.prompt_tokens > 0
        assert len(report.rules_applied) > 0


class TestLintPromptFunction:
    """Tests for lint_prompt convenience function."""

    def test_lint_prompt_basic(self):
        """Test basic lint_prompt usage."""
        report = lint_prompt("Test prompt with evidence ID: E-ABC123")
        assert isinstance(report, PromptLintReport)

    def test_lint_prompt_with_context(self):
        """Test lint_prompt with context."""
        report = lint_prompt(
            "Test prompt",
            context={"max_tokens": 1000, "allowed_tools": ["slither"]},
        )
        assert "max_tokens" in report.context

    def test_lint_prompt_with_custom_rules(self):
        """Test lint_prompt with custom rules."""
        report = lint_prompt(
            "Test prompt",
            rules=[PromptSizeRule()],
        )
        assert len(report.rules_applied) == 1
        assert "prompt-size" in report.rules_applied


class TestFactoryFunctions:
    """Tests for factory/helper functions."""

    def test_get_default_rules(self):
        """Test getting default rules."""
        rules = get_default_rules()
        assert len(rules) == 5
        rule_ids = [r.rule_id for r in rules]
        assert "oversized-section" in rule_ids
        assert "duplicate-context" in rule_ids
        assert "missing-constraint" in rule_ids
        assert "unused-tool" in rule_ids
        assert "prompt-size" in rule_ids

    def test_create_linter_include(self):
        """Test creating linter with included rules."""
        linter = create_linter(include_rules=["prompt-size"])
        assert len(linter.rules) == 1
        assert linter.rules[0].rule_id == "prompt-size"

    def test_create_linter_exclude(self):
        """Test creating linter with excluded rules."""
        linter = create_linter(exclude_rules=["prompt-size", "unused-tool"])
        rule_ids = [r.rule_id for r in linter.rules]
        assert "prompt-size" not in rule_ids
        assert "unused-tool" not in rule_ids
        assert len(linter.rules) == 3


class TestIntegration:
    """Integration tests for prompt linting."""

    def test_lint_realistic_prompt(self):
        """Test linting a realistic prompt."""
        prompt = """
Task Type: tier_b_verification

Context (TOON format):
F:withdraw|C:Vault|L:45|S:critical
P:vm-001|M:state_write_after_external_call
E:ext_call@48,bal_write@52

Instructions:
Verify this finding by examining the evidence and cite evidence IDs.

Output Schema:
{
  "type": "object",
  "properties": {
    "verdict": {"type": "string"},
    "confidence": {"type": "number"}
  }
}
        """
        report = lint_prompt(prompt, context={"max_tokens": 6000})
        assert report.prompt_tokens > 0
        # Should not have errors (prompt is reasonable)
        assert not report.has_errors

    def test_lint_problematic_prompt(self):
        """Test linting a problematic prompt."""
        # Create prompt with various issues
        large_code = "function test() {\n" + "// code\n" * 500 + "}\n"
        duplicate_ids = "E-ABC123 " * 10

        prompt = f"""
Task Type: verification

Context:
{duplicate_ids}

```solidity
{large_code}
```

Analyze the code.
        """
        report = lint_prompt(prompt, context={"max_tokens": 2000})

        # Should have warnings for oversized code
        assert report.has_warnings or report.has_errors
        # Should have token impact
        assert report.wasteful_tokens > 0
