"""Prompt Linting (Phase 7.1.3-05).

This module provides lint rules for LLM prompts to detect wasteful context,
duplicate sections, missing constraints, and unused tools. Lint results are
emitted as structured reports without blocking by default.

Key features:
- Oversized section detection (raw code, metadata)
- Duplicate context detection (repeated evidence, redundant sections)
- Missing constraint detection (no budget, no output schema)
- Unused tool reference detection
- Configurable severity levels (warn, error)
- Non-blocking by default (log warnings, don't raise)

Usage:
    from alphaswarm_sol.llm.prompt_lint import (
        PromptLintReport,
        LintRule,
        LintSeverity,
        lint_prompt,
        PromptLinter,
    )

    # Quick lint
    report = lint_prompt(prompt_text)
    if report.has_warnings:
        print(report.summary())

    # Custom linter with specific rules
    linter = PromptLinter(rules=[OversizedSectionRule(), DuplicateContextRule()])
    report = linter.lint(prompt_text, context={"max_tokens": 6000})
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class LintSeverity(Enum):
    """Lint rule severity levels.

    INFO: Informational, no action needed.
    WARN: Warning, should be addressed but not blocking.
    ERROR: Error, should be fixed (still non-blocking by default).
    """

    INFO = "info"
    WARN = "warn"
    ERROR = "error"


@dataclass
class LintViolation:
    """A single lint rule violation.

    Attributes:
        rule_id: Unique identifier for the rule that triggered this violation.
        severity: Severity level (info, warn, error).
        message: Human-readable description of the violation.
        location: Optional location info (line number, section name, etc.).
        suggestion: Optional suggestion for fixing the violation.
        token_impact: Estimated token impact of the violation (positive = wasteful).
    """

    rule_id: str
    severity: LintSeverity
    message: str
    location: Optional[str] = None
    suggestion: Optional[str] = None
    token_impact: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "message": self.message,
            "location": self.location,
            "suggestion": self.suggestion,
            "token_impact": self.token_impact,
        }


@dataclass
class PromptLintReport:
    """Result of linting a prompt.

    Attributes:
        violations: List of all violations found.
        prompt_tokens: Estimated token count of the prompt.
        wasteful_tokens: Estimated tokens that could be saved.
        rules_applied: List of rule IDs that were applied.
        context: Additional context about the lint run.
    """

    violations: List[LintViolation] = field(default_factory=list)
    prompt_tokens: int = 0
    wasteful_tokens: int = 0
    rules_applied: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_violations(self) -> bool:
        """Whether any violations were found."""
        return len(self.violations) > 0

    @property
    def has_warnings(self) -> bool:
        """Whether any warnings or errors were found."""
        return any(
            v.severity in (LintSeverity.WARN, LintSeverity.ERROR)
            for v in self.violations
        )

    @property
    def has_errors(self) -> bool:
        """Whether any errors were found."""
        return any(v.severity == LintSeverity.ERROR for v in self.violations)

    @property
    def error_count(self) -> int:
        """Count of error-level violations."""
        return sum(1 for v in self.violations if v.severity == LintSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        """Count of warning-level violations."""
        return sum(1 for v in self.violations if v.severity == LintSeverity.WARN)

    @property
    def info_count(self) -> int:
        """Count of info-level violations."""
        return sum(1 for v in self.violations if v.severity == LintSeverity.INFO)

    def summary(self) -> str:
        """Generate human-readable summary.

        Returns:
            Summary string with violation counts and top issues.
        """
        if not self.violations:
            return f"Prompt lint: OK ({self.prompt_tokens} tokens)"

        lines = [
            f"Prompt lint: {self.error_count} errors, {self.warning_count} warnings, {self.info_count} info",
            f"  Tokens: {self.prompt_tokens} total, ~{self.wasteful_tokens} wasteful",
        ]

        # Show top violations
        for v in self.violations[:5]:
            prefix = {"error": "E", "warn": "W", "info": "I"}[v.severity.value]
            loc = f" ({v.location})" if v.location else ""
            lines.append(f"  [{prefix}] {v.rule_id}{loc}: {v.message}")

        if len(self.violations) > 5:
            lines.append(f"  ... and {len(self.violations) - 5} more")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "violations": [v.to_dict() for v in self.violations],
            "prompt_tokens": self.prompt_tokens,
            "wasteful_tokens": self.wasteful_tokens,
            "rules_applied": self.rules_applied,
            "context": self.context,
            "summary": {
                "has_violations": self.has_violations,
                "has_warnings": self.has_warnings,
                "has_errors": self.has_errors,
                "error_count": self.error_count,
                "warning_count": self.warning_count,
                "info_count": self.info_count,
            },
        }


class LintRule(ABC):
    """Base class for prompt lint rules.

    Subclasses implement specific lint checks by overriding check().
    """

    @property
    @abstractmethod
    def rule_id(self) -> str:
        """Unique identifier for this rule."""
        ...

    @property
    def description(self) -> str:
        """Human-readable description of what this rule checks."""
        return ""

    @abstractmethod
    def check(
        self,
        prompt: str,
        context: Dict[str, Any],
    ) -> List[LintViolation]:
        """Check prompt for violations of this rule.

        Args:
            prompt: The prompt text to lint.
            context: Additional context (max_tokens, tools, etc.).

        Returns:
            List of violations found (empty if none).
        """
        ...


class OversizedSectionRule(LintRule):
    """Detect oversized sections that waste tokens.

    Flags sections that exceed size thresholds:
    - Code blocks > 2000 chars (~500 tokens)
    - Metadata sections > 1000 chars (~250 tokens)
    - Raw source sections > 3000 chars (~750 tokens)
    """

    CHARS_PER_TOKEN = 4

    # Section patterns and their thresholds (chars)
    SECTION_THRESHOLDS: Dict[str, int] = {
        "code_block": 2000,      # ```...```
        "metadata": 1000,        # ## Metadata
        "raw_source": 3000,      # ## Source, ## Raw Code
        "full_context": 3000,    # ## Full Context
    }

    @property
    def rule_id(self) -> str:
        return "oversized-section"

    @property
    def description(self) -> str:
        return "Detect sections that are larger than recommended thresholds"

    def check(
        self,
        prompt: str,
        context: Dict[str, Any],
    ) -> List[LintViolation]:
        violations: List[LintViolation] = []

        # Check code blocks
        code_blocks = re.findall(r"```[\w]*\n(.*?)```", prompt, re.DOTALL)
        for i, block in enumerate(code_blocks):
            if len(block) > self.SECTION_THRESHOLDS["code_block"]:
                excess = len(block) - self.SECTION_THRESHOLDS["code_block"]
                violations.append(
                    LintViolation(
                        rule_id=self.rule_id,
                        severity=LintSeverity.WARN,
                        message=f"Code block {i + 1} is {len(block)} chars ({excess} over threshold)",
                        location=f"code_block_{i + 1}",
                        suggestion="Trim code to essential lines or use evidence IDs",
                        token_impact=excess // self.CHARS_PER_TOKEN,
                    )
                )

        # Check named sections
        section_patterns = {
            "metadata": r"## Metadata\n(.*?)(?=\n## |\Z)",
            "raw_source": r"## (?:Source|Raw Code)\n(.*?)(?=\n## |\Z)",
            "full_context": r"## Full Context\n(.*?)(?=\n## |\Z)",
        }

        for section_name, pattern in section_patterns.items():
            match = re.search(pattern, prompt, re.DOTALL)
            if match:
                content = match.group(1)
                threshold = self.SECTION_THRESHOLDS.get(section_name, 2000)
                if len(content) > threshold:
                    excess = len(content) - threshold
                    violations.append(
                        LintViolation(
                            rule_id=self.rule_id,
                            severity=LintSeverity.WARN,
                            message=f"Section '{section_name}' is {len(content)} chars ({excess} over threshold)",
                            location=section_name,
                            suggestion=f"Trim {section_name} or move to progressive disclosure",
                            token_impact=excess // self.CHARS_PER_TOKEN,
                        )
                    )

        return violations


class DuplicateContextRule(LintRule):
    """Detect duplicated context that wastes tokens.

    Flags:
    - Repeated evidence IDs
    - Duplicate file paths
    - Repeated code snippets (exact or fuzzy match)
    """

    # Patterns to detect duplicates
    EVIDENCE_ID_PATTERN = re.compile(
        r"(E-[A-Z0-9]{6,}|EV-[a-f0-9]{8,}|evidence_id:\s*\S+)"
    )
    FILE_PATH_PATTERN = re.compile(r"(?:file|path|location):\s*(\S+\.sol)")
    CODE_LINE_PATTERN = re.compile(r"^\s*(function|modifier|contract|mapping|struct)\s+\w+", re.MULTILINE)

    CHARS_PER_TOKEN = 4

    @property
    def rule_id(self) -> str:
        return "duplicate-context"

    @property
    def description(self) -> str:
        return "Detect duplicated evidence, file paths, or code snippets"

    def check(
        self,
        prompt: str,
        context: Dict[str, Any],
    ) -> List[LintViolation]:
        violations: List[LintViolation] = []

        # Check for duplicate evidence IDs
        evidence_ids = self.EVIDENCE_ID_PATTERN.findall(prompt)
        seen_ids: Set[str] = set()
        duplicates: List[str] = []
        for eid in evidence_ids:
            if eid in seen_ids:
                duplicates.append(eid)
            seen_ids.add(eid)

        if duplicates:
            # Estimate wasted tokens (each duplicate ~20 chars)
            waste = len(duplicates) * 20
            violations.append(
                LintViolation(
                    rule_id=self.rule_id,
                    severity=LintSeverity.WARN,
                    message=f"Found {len(duplicates)} duplicate evidence IDs",
                    location="evidence_ids",
                    suggestion="Deduplicate evidence references",
                    token_impact=waste // self.CHARS_PER_TOKEN,
                )
            )

        # Check for duplicate file paths
        file_paths = self.FILE_PATH_PATTERN.findall(prompt)
        seen_paths: Set[str] = set()
        dup_paths: List[str] = []
        for path in file_paths:
            if path in seen_paths:
                dup_paths.append(path)
            seen_paths.add(path)

        if len(dup_paths) > 2:  # Allow some repetition
            waste = len(dup_paths) * 30
            violations.append(
                LintViolation(
                    rule_id=self.rule_id,
                    severity=LintSeverity.INFO,
                    message=f"File path '{dup_paths[0]}' repeated {len(dup_paths) + 1} times",
                    location="file_paths",
                    suggestion="Use file references instead of repeating paths",
                    token_impact=waste // self.CHARS_PER_TOKEN,
                )
            )

        # Check for duplicate code definitions
        code_defs = self.CODE_LINE_PATTERN.findall(prompt)
        if len(code_defs) > len(set(code_defs)) + 2:  # Allow some common patterns
            dup_count = len(code_defs) - len(set(code_defs))
            waste = dup_count * 50  # Estimate 50 chars per duplicate line
            violations.append(
                LintViolation(
                    rule_id=self.rule_id,
                    severity=LintSeverity.INFO,
                    message=f"Found {dup_count} potentially duplicate code definitions",
                    location="code_definitions",
                    suggestion="Remove redundant code snippets",
                    token_impact=waste // self.CHARS_PER_TOKEN,
                )
            )

        return violations


class MissingConstraintRule(LintRule):
    """Detect missing constraints that may cause issues.

    Flags:
    - No output schema specified
    - No token budget mentioned
    - No evidence requirements stated
    - Missing severity/confidence constraints
    """

    @property
    def rule_id(self) -> str:
        return "missing-constraint"

    @property
    def description(self) -> str:
        return "Detect missing constraints that should be specified"

    def check(
        self,
        prompt: str,
        context: Dict[str, Any],
    ) -> List[LintViolation]:
        violations: List[LintViolation] = []
        prompt_lower = prompt.lower()

        # Check for output schema
        has_schema = (
            "output schema" in prompt_lower
            or "json schema" in prompt_lower
            or '"type":' in prompt
            or "output_schema" in context
        )
        if not has_schema:
            violations.append(
                LintViolation(
                    rule_id=self.rule_id,
                    severity=LintSeverity.INFO,
                    message="No output schema specified",
                    suggestion="Add an output schema to constrain LLM response format",
                )
            )

        # Check for evidence requirement
        evidence_keywords = ["evidence", "evidence_id", "cite", "reference"]
        has_evidence_req = any(kw in prompt_lower for kw in evidence_keywords)
        if not has_evidence_req:
            violations.append(
                LintViolation(
                    rule_id=self.rule_id,
                    severity=LintSeverity.WARN,
                    message="No evidence requirement stated",
                    suggestion="Add 'cite evidence IDs' or similar constraint",
                )
            )

        # Check for confidence/severity constraints
        confidence_keywords = ["confidence", "certainty", "severity", "risk_score"]
        has_confidence = any(kw in prompt_lower for kw in confidence_keywords)
        if not has_confidence and "verification" in prompt_lower:
            violations.append(
                LintViolation(
                    rule_id=self.rule_id,
                    severity=LintSeverity.INFO,
                    message="Verification task without confidence constraint",
                    suggestion="Add confidence scoring requirement",
                )
            )

        return violations


class UnusedToolRule(LintRule):
    """Detect tool references that may be unused or invalid.

    Flags:
    - Tool names mentioned but not in allowed list
    - Tool descriptions included but tool not actually needed
    """

    # Common tool name patterns
    TOOL_PATTERNS = [
        r"tool[:\s]+(\w+)",
        r"use[:\s]+(\w+)\s+tool",
        r"run[:\s]+(\w+)",
        r"execute[:\s]+(\w+)",
    ]

    @property
    def rule_id(self) -> str:
        return "unused-tool"

    @property
    def description(self) -> str:
        return "Detect tool references that may be unused or invalid"

    def check(
        self,
        prompt: str,
        context: Dict[str, Any],
    ) -> List[LintViolation]:
        violations: List[LintViolation] = []

        # Get allowed tools from context
        allowed_tools: Set[str] = set(context.get("allowed_tools", []))
        if not allowed_tools:
            return violations  # No tool constraints to check

        # Find tool references in prompt
        referenced_tools: Set[str] = set()
        prompt_lower = prompt.lower()

        for pattern in self.TOOL_PATTERNS:
            matches = re.findall(pattern, prompt_lower)
            referenced_tools.update(matches)

        # Check for unknown tools
        unknown_tools = referenced_tools - allowed_tools
        for tool in unknown_tools:
            violations.append(
                LintViolation(
                    rule_id=self.rule_id,
                    severity=LintSeverity.WARN,
                    message=f"Tool '{tool}' referenced but not in allowed list",
                    location="tool_reference",
                    suggestion=f"Remove reference or add '{tool}' to allowed tools",
                )
            )

        return violations


class PromptSizeRule(LintRule):
    """Check overall prompt size against budget.

    Flags prompts that exceed or approach token limits.
    """

    CHARS_PER_TOKEN = 4

    @property
    def rule_id(self) -> str:
        return "prompt-size"

    @property
    def description(self) -> str:
        return "Check overall prompt size against token budget"

    def check(
        self,
        prompt: str,
        context: Dict[str, Any],
    ) -> List[LintViolation]:
        violations: List[LintViolation] = []

        max_tokens = context.get("max_tokens", 6000)
        estimated_tokens = len(prompt) // self.CHARS_PER_TOKEN

        # Error if over budget
        if estimated_tokens > max_tokens:
            excess = estimated_tokens - max_tokens
            violations.append(
                LintViolation(
                    rule_id=self.rule_id,
                    severity=LintSeverity.ERROR,
                    message=f"Prompt exceeds budget: ~{estimated_tokens} tokens (limit: {max_tokens})",
                    suggestion=f"Reduce prompt by ~{excess} tokens",
                    token_impact=excess,
                )
            )
        # Warn if approaching budget (>80%)
        elif estimated_tokens > max_tokens * 0.8:
            remaining = max_tokens - estimated_tokens
            violations.append(
                LintViolation(
                    rule_id=self.rule_id,
                    severity=LintSeverity.WARN,
                    message=f"Prompt at {estimated_tokens}/{max_tokens} tokens ({remaining} remaining)",
                    suggestion="Consider trimming to leave room for response",
                )
            )

        return violations


# Default rules to apply
DEFAULT_RULES: List[LintRule] = [
    OversizedSectionRule(),
    DuplicateContextRule(),
    MissingConstraintRule(),
    UnusedToolRule(),
    PromptSizeRule(),
]


class PromptLinter:
    """Lint prompts using configurable rules.

    Example:
        linter = PromptLinter()
        report = linter.lint(prompt)
        if report.has_warnings:
            logger.warning(report.summary())
    """

    CHARS_PER_TOKEN = 4

    def __init__(
        self,
        rules: Optional[List[LintRule]] = None,
        log_level: int = logging.WARNING,
    ):
        """Initialize prompt linter.

        Args:
            rules: List of rules to apply (default: DEFAULT_RULES).
            log_level: Level for logging violations (default: WARNING).
        """
        self._rules = rules if rules is not None else DEFAULT_RULES.copy()
        self._log_level = log_level

    @property
    def rules(self) -> List[LintRule]:
        """List of active rules."""
        return self._rules

    def add_rule(self, rule: LintRule) -> None:
        """Add a rule to the linter.

        Args:
            rule: Rule to add.
        """
        self._rules.append(rule)

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID.

        Args:
            rule_id: ID of rule to remove.

        Returns:
            True if rule was found and removed.
        """
        for i, rule in enumerate(self._rules):
            if rule.rule_id == rule_id:
                self._rules.pop(i)
                return True
        return False

    def lint(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> PromptLintReport:
        """Lint a prompt and return a report.

        Args:
            prompt: Prompt text to lint.
            context: Additional context (max_tokens, allowed_tools, etc.).

        Returns:
            PromptLintReport with all violations found.
        """
        context = context or {}
        violations: List[LintViolation] = []
        rules_applied: List[str] = []

        # Apply each rule
        for rule in self._rules:
            rules_applied.append(rule.rule_id)
            try:
                rule_violations = rule.check(prompt, context)
                violations.extend(rule_violations)
            except Exception as e:
                logger.error("Lint rule %s failed: %s", rule.rule_id, e)

        # Calculate totals
        prompt_tokens = len(prompt) // self.CHARS_PER_TOKEN
        wasteful_tokens = sum(v.token_impact for v in violations)

        report = PromptLintReport(
            violations=violations,
            prompt_tokens=prompt_tokens,
            wasteful_tokens=wasteful_tokens,
            rules_applied=rules_applied,
            context=context,
        )

        # Log if violations found
        if report.has_violations:
            logger.log(self._log_level, report.summary())

        return report


def lint_prompt(
    prompt: str,
    context: Optional[Dict[str, Any]] = None,
    rules: Optional[List[LintRule]] = None,
) -> PromptLintReport:
    """Lint a prompt using default or custom rules.

    This is the main entry point for prompt linting. It applies lint rules
    to detect wasteful context, duplicate sections, and missing constraints.

    Args:
        prompt: Prompt text to lint.
        context: Additional context (max_tokens, allowed_tools, etc.).
        rules: Custom rules to apply (default: all rules).

    Returns:
        PromptLintReport with violations and suggestions.

    Example:
        report = lint_prompt(prompt_text, context={"max_tokens": 6000})
        if report.has_warnings:
            print(report.summary())
    """
    linter = PromptLinter(rules=rules)
    return linter.lint(prompt, context=context)


def get_default_rules() -> List[LintRule]:
    """Get a copy of the default lint rules.

    Returns:
        List of default LintRule instances.
    """
    return DEFAULT_RULES.copy()


def create_linter(
    include_rules: Optional[List[str]] = None,
    exclude_rules: Optional[List[str]] = None,
) -> PromptLinter:
    """Create a linter with specific rules.

    Args:
        include_rules: Rule IDs to include (None = all).
        exclude_rules: Rule IDs to exclude.

    Returns:
        Configured PromptLinter.
    """
    rules = get_default_rules()

    if include_rules:
        rules = [r for r in rules if r.rule_id in include_rules]

    if exclude_rules:
        rules = [r for r in rules if r.rule_id not in exclude_rules]

    return PromptLinter(rules=rules)
