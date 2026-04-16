"""Progressive Validation for VulnDocs Framework.

This module implements progressive validation logic that warns but doesn't block,
using levels: MINIMAL -> STANDARD -> COMPLETE -> EXCELLENT.

Design Philosophy:
- Only index.yaml is strictly required (errors if missing/invalid)
- Additional files unlock higher validation levels
- Warnings for quality issues, suggestions for improvements
- CI can warn on incomplete entries without blocking builds
- Pattern Context Pack (PCP) v2 files are validated with lint rules

Validation Levels:
- MINIMAL: Just index.yaml with required fields
- STANDARD: index.yaml + at least one .md file
- COMPLETE: All recommended files (overview, detection, verification)
- EXCELLENT: All files + patterns/ with test coverage + PCP v2 lint clean

Part of Plan 05.4-03: Progressive Validation Framework
Phase 5.10-02: PCP v2 lint integration
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional

import yaml
from pydantic import ValidationError

from alphaswarm_sol.vulndocs.schema import VulnDocIndex
from alphaswarm_sol.vulndocs.types import ValidationLevel
from alphaswarm_sol.vulndocs.discovery import (
    discover_categories,
    discover_vulnerabilities,
    discover_patterns,
    get_expected_files,
)


@dataclass
class ValidationResult:
    """Result of validating a single vulnerability folder.

    Attributes:
        path: Path to vulnerability folder
        level: Validation level achieved (None if failed minimum requirements)
        errors: Blocking issues (missing required fields, invalid YAML)
        warnings: Quality issues (missing recommended files)
        suggestions: Improvement ideas (research topics, pattern creation)
    """

    path: Path
    level: Optional[ValidationLevel] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if validation passed (no errors)."""
        return len(self.errors) == 0 and self.level is not None

    @property
    def has_warnings(self) -> bool:
        """Check if validation has warnings."""
        return len(self.warnings) > 0

    @property
    def has_suggestions(self) -> bool:
        """Check if validation has suggestions."""
        return len(self.suggestions) > 0


@dataclass
class FrameworkValidationResult:
    """Result of validating the entire vulndocs framework.

    Attributes:
        vulnerabilities: List of individual validation results
        has_errors: Whether any vulnerabilities have errors
        has_warnings: Whether any vulnerabilities have warnings
        summary: Counts per validation level
    """

    vulnerabilities: List[ValidationResult] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """Check if any vulnerabilities have errors."""
        return any(not v.is_valid for v in self.vulnerabilities)

    @property
    def has_warnings(self) -> bool:
        """Check if any vulnerabilities have warnings."""
        return any(v.has_warnings for v in self.vulnerabilities)

    @property
    def summary(self) -> Dict[str, int]:
        """Get summary counts per validation level."""
        counts = {
            "total": len(self.vulnerabilities),
            "errors": sum(1 for v in self.vulnerabilities if not v.is_valid),
            "minimal": 0,
            "standard": 0,
            "complete": 0,
            "excellent": 0,
        }

        for v in self.vulnerabilities:
            if v.level == ValidationLevel.MINIMAL:
                counts["minimal"] += 1
            elif v.level == ValidationLevel.STANDARD:
                counts["standard"] += 1
            elif v.level == ValidationLevel.COMPLETE:
                counts["complete"] += 1
            elif v.level == ValidationLevel.EXCELLENT:
                counts["excellent"] += 1

        return counts


def validate_vulnerability(path: Path) -> ValidationResult:
    """Validate a single vulnerability folder with progressive levels.

    Progressive validation logic:

    1. REQUIRED: index.yaml must exist with minimum fields
       - If missing/invalid: level=None, add error
       - Required fields: id, category, subcategory, severity, vulndoc

    2. MINIMAL level: Just valid index.yaml
       - No additional files required

    3. STANDARD level: index.yaml + at least 1 .md file
       - Warn if missing overview.md (most important)

    4. COMPLETE level: All recommended .md files
       - Check for overview.md, detection.md, verification.md
       - Warn if missing exploits.md

    5. EXCELLENT level: All files + patterns with coverage
       - Check patterns/ folder exists with .yaml files
       - Suggest running tests if test_coverage empty

    Args:
        path: Path to vulnerability folder

    Returns:
        ValidationResult with level, errors, warnings, suggestions
    """
    result = ValidationResult(path=path)

    # === PHASE 1: Check for index.yaml (REQUIRED) ===
    index_path = path / "index.yaml"
    if not index_path.exists():
        result.errors.append("Missing required file: index.yaml")
        result.level = None
        return result

    # === PHASE 2: Parse and validate index.yaml ===
    try:
        with open(index_path, "r") as f:
            index_data = yaml.safe_load(f)

        if not index_data:
            result.errors.append("index.yaml is empty")
            result.level = None
            return result

        # Validate with pydantic schema
        index = VulnDocIndex.model_validate(index_data)

        # At this point, index.yaml is valid -> MINIMAL level achieved
        result.level = ValidationLevel.MINIMAL

    except yaml.YAMLError as e:
        result.errors.append(f"Invalid YAML in index.yaml: {e}")
        result.level = None
        return result
    except ValidationError as e:
        # Pydantic validation errors
        for error in e.errors():
            field = ".".join(str(x) for x in error["loc"])
            msg = error["msg"]
            result.errors.append(f"index.yaml validation error: {field} - {msg}")
        result.level = None
        return result
    except Exception as e:
        result.errors.append(f"Error reading index.yaml: {e}")
        result.level = None
        return result

    # === PHASE 3: Check for .md files (STANDARD level) ===
    md_files = list(path.glob("*.md"))
    if len(md_files) > 0:
        result.level = ValidationLevel.STANDARD

        # Warn if missing overview.md (most important)
        if not (path / "overview.md").exists():
            result.warnings.append("Missing overview.md - recommended for human readability")

    # === PHASE 4: Check for recommended files (COMPLETE level) ===
    recommended_files = ["overview.md", "detection.md", "verification.md"]
    has_all_recommended = all((path / f).exists() for f in recommended_files)

    if has_all_recommended:
        result.level = ValidationLevel.COMPLETE

        # Warn if missing exploits.md (valuable but not required for COMPLETE)
        if not (path / "exploits.md").exists():
            result.warnings.append("Missing exploits.md - valuable for evidence-based analysis")

    # === PHASE 5: Check for patterns and test coverage (EXCELLENT level) ===
    patterns = discover_patterns(path)

    if result.level == ValidationLevel.COMPLETE and len(patterns) > 0:
        # Check if patterns have test coverage
        has_test_coverage = len(index.test_coverage) > 0

        if has_test_coverage:
            result.level = ValidationLevel.EXCELLENT
        else:
            # Still COMPLETE, but suggest adding tests
            result.suggestions.append(
                "Patterns exist but test_coverage is empty - consider running pattern tests"
            )

    elif result.level == ValidationLevel.COMPLETE and len(patterns) == 0:
        # No patterns yet
        result.suggestions.append(
            "No patterns/ folder found - consider creating patterns for this vulnerability"
        )

    # === PHASE 6: Check for Phase 7 test generation fields ===
    # Suggest research if fields are empty
    phase7_suggestions = suggest_research(index, path)
    result.suggestions.extend(phase7_suggestions)

    return result


def validate_framework(root: Path) -> FrameworkValidationResult:
    """Validate the entire vulndocs framework.

    Discovers all vulnerability folders and validates each one,
    then aggregates results.

    Args:
        root: Path to vulndocs root folder

    Returns:
        FrameworkValidationResult with all validation results
    """
    result = FrameworkValidationResult()

    # Discover all vulnerabilities
    vulnerabilities = discover_vulnerabilities(root)

    # Validate each one
    for vuln in vulnerabilities:
        validation = validate_vulnerability(vuln.path)
        result.vulnerabilities.append(validation)

    return result


def suggest_research(index: VulnDocIndex, path: Path) -> List[str]:
    """Suggest research topics based on missing/empty fields.

    Checks Phase 7 test generation fields and suggests Exa research
    when content gaps are detected.

    Args:
        index: Validated VulnDocIndex
        path: Path to vulnerability folder

    Returns:
        List of suggestion strings
    """
    suggestions = []

    # Check if Phase 7 fields are empty
    if len(index.semantic_triggers) == 0:
        suggestions.append(
            f"semantic_triggers is empty - consider researching VKG operations for {index.category}/{index.subcategory}"
        )

    if len(index.vql_queries) == 0:
        suggestions.append(
            f"vql_queries is empty - consider adding example VQL queries for detection"
        )

    if len(index.graph_patterns) == 0:
        suggestions.append(
            f"graph_patterns is empty - consider documenting behavioral signatures"
        )

    if not index.reasoning_template or len(index.reasoning_template.strip()) < 50:
        suggestions.append(
            f"reasoning_template is missing or too brief - consider adding LLM reasoning guidance"
        )

    # Check for exploits
    if len(index.related_exploits) == 0:
        suggestions.append(
            f"related_exploits is empty - consider researching real-world exploits via Exa"
        )

    # If multiple fields are missing, suggest comprehensive research
    empty_count = sum([
        len(index.semantic_triggers) == 0,
        len(index.vql_queries) == 0,
        len(index.graph_patterns) == 0,
        not index.reasoning_template or len(index.reasoning_template.strip()) < 50,
        len(index.related_exploits) == 0,
    ])

    if empty_count >= 3:
        vuln_topic = f"{index.category} {index.subcategory}"
        suggestions.append(
            f"Consider: uv run alphaswarm vulndocs research '{vuln_topic}' "
            f"to populate Phase 7 fields via Exa"
        )

    return suggestions


# =============================================================================
# Pattern Context Pack (PCP) v2 Validation
# =============================================================================


@dataclass
class PCPValidationResult:
    """Result of validating Pattern Context Pack v2 files.

    Attributes:
        path: Path to vulnerability folder containing PCP files
        pcp_files: List of PCP files found
        errors: Blocking lint errors
        warnings: Quality warnings
        suggestions: Improvement suggestions
    """

    path: Path
    pcp_files: List[Path] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if all PCP files pass lint (no errors)."""
        return len(self.errors) == 0

    @property
    def has_pcp_files(self) -> bool:
        """Check if any PCP files exist."""
        return len(self.pcp_files) > 0


def validate_pcp_files(path: Path, strict: bool = False) -> PCPValidationResult:
    """Validate Pattern Context Pack v2 files in a vulnerability folder.

    Discovers *.pcp.yaml files in the patterns/ subfolder and runs
    lint rules to enforce determinism, evidence gating, and unknowns policy.

    Args:
        path: Path to vulnerability folder (e.g., vulndocs/reentrancy/classic/)
        strict: If True, treat warnings as errors

    Returns:
        PCPValidationResult with all issues found
    """
    from alphaswarm_sol.vulndocs.validators.pcp_lint import (
        PCPLinter,
        PCPLintSeverity,
    )

    result = PCPValidationResult(path=path)

    # Look for PCP files in patterns/ subfolder
    patterns_dir = path / "patterns"
    if not patterns_dir.exists():
        return result

    # Find all PCP files
    pcp_files = list(patterns_dir.glob("*.pcp.yaml"))
    result.pcp_files = pcp_files

    if not pcp_files:
        return result

    # Lint each PCP file
    linter = PCPLinter(strict_mode=strict)

    for pcp_file in pcp_files:
        lint_result = linter.lint_file(pcp_file)

        for issue in lint_result.issues:
            msg = f"[{pcp_file.name}] {issue}"
            if issue.severity == PCPLintSeverity.ERROR:
                result.errors.append(msg)
            elif issue.severity == PCPLintSeverity.WARNING:
                result.warnings.append(msg)
            else:  # INFO
                result.suggestions.append(msg)

    return result


def validate_vulnerability_with_pcp(path: Path, strict_pcp: bool = False) -> ValidationResult:
    """Validate a vulnerability folder including PCP v2 files.

    Extends validate_vulnerability() to also check Pattern Context Pack
    v2 files for determinism and evidence gating compliance.

    Args:
        path: Path to vulnerability folder
        strict_pcp: If True, treat PCP warnings as errors

    Returns:
        ValidationResult with combined vulndoc and PCP issues
    """
    # First, run standard validation
    result = validate_vulnerability(path)

    # If standard validation failed, return early
    if not result.is_valid:
        return result

    # Validate PCP files
    pcp_result = validate_pcp_files(path, strict=strict_pcp)

    # Merge PCP results
    if pcp_result.has_pcp_files:
        result.errors.extend(pcp_result.errors)
        result.warnings.extend(pcp_result.warnings)
        result.suggestions.extend(pcp_result.suggestions)

        # Downgrade validation level if PCP errors found
        if pcp_result.errors:
            result.level = ValidationLevel.STANDARD

    return result


def validate_framework_with_pcp(
    root: Path,
    strict_pcp: bool = False,
) -> FrameworkValidationResult:
    """Validate the entire vulndocs framework including PCP v2 files.

    Extends validate_framework() to also check Pattern Context Pack
    v2 files for determinism and evidence gating compliance.

    Args:
        root: Path to vulndocs root folder
        strict_pcp: If True, treat PCP warnings as errors

    Returns:
        FrameworkValidationResult with all validation results
    """
    result = FrameworkValidationResult()

    # Discover all vulnerabilities
    vulnerabilities = discover_vulnerabilities(root)

    # Validate each one with PCP
    for vuln in vulnerabilities:
        validation = validate_vulnerability_with_pcp(vuln.path, strict_pcp=strict_pcp)
        result.vulnerabilities.append(validation)

    return result
