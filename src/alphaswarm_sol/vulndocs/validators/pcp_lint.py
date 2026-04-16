"""Pattern Context Pack (PCP) v2 Linting Rules.

This module implements lint rules that enforce PCP v2 authoring constraints:
- Required ops and ordering variants are non-empty
- Witness + negative witness presence for high/critical patterns
- Anti-signals or counter-signals present when guards exist
- Unknowns policy is explicit for missing evidence
- Determinism flags set (no_rag, no_name_heuristics)

Part of Phase 5.10-02: PCP v2 Templates and Lint Rules
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from alphaswarm_sol.vulndocs.schema import (
    PatternContextPackV2,
    UnknownsPolicy,
    GuardType,
)


class PCPLintSeverity(str, Enum):
    """Severity level for lint issues."""

    ERROR = "error"  # Blocks validation
    WARNING = "warning"  # Quality concern, doesn't block
    INFO = "info"  # Suggestion for improvement


class PCPLintRuleId(str, Enum):
    """Lint rule identifiers for PCP v2."""

    # Required field rules (errors)
    PCP001 = "PCP001"  # Missing required_ops
    PCP002 = "PCP002"  # Missing pattern_id
    PCP003 = "PCP003"  # Missing name or summary
    PCP004 = "PCP004"  # Invalid ID format (must start with pcp-)

    # Determinism rules (errors)
    PCP010 = "PCP010"  # no_rag must be true
    PCP011 = "PCP011"  # no_name_heuristics must be true
    PCP012 = "PCP012"  # Budget ordering violation (cheap < verify < deep)

    # Evidence rules (warnings for high/critical patterns)
    PCP020 = "PCP020"  # Missing minimal_required witnesses
    PCP021 = "PCP021"  # Missing negative_required witnesses
    PCP022 = "PCP022"  # Missing anti-signals for guarded patterns
    PCP023 = "PCP023"  # Anti-signal without bypass notes
    PCP024 = "PCP024"  # Missing evidence_refs in exploit steps

    # Ordering rules (warnings)
    PCP030 = "PCP030"  # No ordering variants for sequence-dependent pattern
    PCP031 = "PCP031"  # Ordering variant sequence mismatch with required_ops

    # Unknowns policy rules (warnings)
    PCP040 = "PCP040"  # Unknowns policy not explicit
    PCP041 = "PCP041"  # High/critical pattern with fail policy (too strict)

    # Guard taxonomy rules (info)
    PCP050 = "PCP050"  # Guard taxonomy empty but anti-signals present
    PCP051 = "PCP051"  # Counterfactual references non-existent anti-signal

    # Composition rules (info)
    PCP060 = "PCP060"  # co_occurs_with references non-existent pattern
    PCP061 = "PCP061"  # combine_with empty for compound pattern

    # Evidence requirements rules (info)
    PCP070 = "PCP070"  # No node_types specified
    PCP071 = "PCP071"  # No edge_types specified


@dataclass
class PCPLintIssue:
    """A single lint issue found during PCP validation."""

    rule_id: PCPLintRuleId
    severity: PCPLintSeverity
    message: str
    field_path: str = ""  # Dot-separated path to field, e.g., "op_signatures.required_ops"
    suggestion: str = ""  # Suggested fix

    def __str__(self) -> str:
        """Format issue for display."""
        severity_prefix = {
            PCPLintSeverity.ERROR: "[ERROR]",
            PCPLintSeverity.WARNING: "[WARN]",
            PCPLintSeverity.INFO: "[INFO]",
        }[self.severity]
        location = f" at {self.field_path}" if self.field_path else ""
        suggestion = f"\n  Suggestion: {self.suggestion}" if self.suggestion else ""
        return f"{severity_prefix} {self.rule_id.value}: {self.message}{location}{suggestion}"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "rule_id": self.rule_id.value,
            "severity": self.severity.value,
            "message": self.message,
            "field_path": self.field_path,
            "suggestion": self.suggestion,
        }


@dataclass
class PCPLintResult:
    """Result of linting a PCP v2 file."""

    path: Path
    issues: List[PCPLintIssue] = field(default_factory=list)
    pcp_id: str = ""
    pattern_id: str = ""

    @property
    def has_errors(self) -> bool:
        """Check if any errors were found."""
        return any(i.severity == PCPLintSeverity.ERROR for i in self.issues)

    @property
    def has_warnings(self) -> bool:
        """Check if any warnings were found."""
        return any(i.severity == PCPLintSeverity.WARNING for i in self.issues)

    @property
    def is_valid(self) -> bool:
        """Check if PCP passes lint (no errors)."""
        return not self.has_errors

    @property
    def error_count(self) -> int:
        """Count errors."""
        return sum(1 for i in self.issues if i.severity == PCPLintSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        """Count warnings."""
        return sum(1 for i in self.issues if i.severity == PCPLintSeverity.WARNING)

    @property
    def info_count(self) -> int:
        """Count info issues."""
        return sum(1 for i in self.issues if i.severity == PCPLintSeverity.INFO)

    def summary(self) -> str:
        """Generate summary string."""
        return (
            f"{self.path.name}: {self.error_count} errors, "
            f"{self.warning_count} warnings, {self.info_count} info"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "path": str(self.path),
            "pcp_id": self.pcp_id,
            "pattern_id": self.pattern_id,
            "is_valid": self.is_valid,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "issues": [i.to_dict() for i in self.issues],
        }


class PCPLinter:
    """Linter for Pattern Context Pack v2 files.

    Enforces authoring constraints for determinism, evidence gating,
    and unknowns policy.

    Usage:
        linter = PCPLinter()
        result = linter.lint_file(Path("pattern.pcp.yaml"))
        if not result.is_valid:
            for issue in result.issues:
                print(issue)
    """

    def __init__(
        self,
        strict_mode: bool = False,
        check_evidence_refs: bool = True,
        severity_threshold: str = "critical",
    ):
        """Initialize PCP linter.

        Args:
            strict_mode: If True, treat warnings as errors
            check_evidence_refs: If True, check evidence_refs are non-empty
            severity_threshold: Severity level threshold for witness/anti-signal rules
                               ("critical", "high", "medium", "low")
        """
        self.strict_mode = strict_mode
        self.check_evidence_refs = check_evidence_refs
        self.severity_threshold = severity_threshold

    def lint_file(self, path: Path) -> PCPLintResult:
        """Lint a PCP v2 YAML file.

        Args:
            path: Path to PCP YAML file

        Returns:
            PCPLintResult with all issues found
        """
        result = PCPLintResult(path=path)

        # Load YAML
        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            result.issues.append(
                PCPLintIssue(
                    rule_id=PCPLintRuleId.PCP001,
                    severity=PCPLintSeverity.ERROR,
                    message=f"Invalid YAML: {e}",
                )
            )
            return result

        if not data:
            result.issues.append(
                PCPLintIssue(
                    rule_id=PCPLintRuleId.PCP001,
                    severity=PCPLintSeverity.ERROR,
                    message="PCP file is empty",
                )
            )
            return result

        # Store metadata
        result.pcp_id = data.get("id", "")
        result.pattern_id = data.get("pattern_id", "")

        # Run all lint rules
        self._lint_required_fields(data, result)
        self._lint_determinism(data, result)
        self._lint_budget(data, result)
        self._lint_op_signatures(data, result)
        self._lint_witnesses(data, result)
        self._lint_anti_signals(data, result)
        self._lint_unknowns_policy(data, result)
        self._lint_guard_taxonomy(data, result)
        self._lint_counterfactuals(data, result)
        self._lint_evidence_requirements(data, result)

        # If strict mode, convert warnings to errors
        if self.strict_mode:
            for issue in result.issues:
                if issue.severity == PCPLintSeverity.WARNING:
                    issue.severity = PCPLintSeverity.ERROR

        return result

    def lint_pcp(self, pcp: PatternContextPackV2, path: Optional[Path] = None) -> PCPLintResult:
        """Lint a PatternContextPackV2 object.

        Args:
            pcp: PatternContextPackV2 instance
            path: Optional path for reporting

        Returns:
            PCPLintResult with all issues found
        """
        result = PCPLintResult(path=path or Path("<in-memory>"))
        result.pcp_id = pcp.id
        result.pattern_id = pcp.pattern_id

        # Convert to dict for consistent checking
        data = pcp.model_dump(mode="json")

        # Run all lint rules
        self._lint_required_fields(data, result)
        self._lint_determinism(data, result)
        self._lint_budget(data, result)
        self._lint_op_signatures(data, result)
        self._lint_witnesses(data, result)
        self._lint_anti_signals(data, result)
        self._lint_unknowns_policy(data, result)
        self._lint_guard_taxonomy(data, result)
        self._lint_counterfactuals(data, result)
        self._lint_evidence_requirements(data, result)

        return result

    def _lint_required_fields(self, data: Dict[str, Any], result: PCPLintResult) -> None:
        """Check required fields are present and valid."""
        # PCP001: required_ops
        op_sigs = data.get("op_signatures", {})
        required_ops = op_sigs.get("required_ops", [])
        if not required_ops:
            result.issues.append(
                PCPLintIssue(
                    rule_id=PCPLintRuleId.PCP001,
                    severity=PCPLintSeverity.ERROR,
                    message="op_signatures.required_ops must have at least one operation",
                    field_path="op_signatures.required_ops",
                    suggestion="Add at least one semantic operation (e.g., TRANSFERS_VALUE_OUT)",
                )
            )

        # PCP002: pattern_id
        if not data.get("pattern_id"):
            result.issues.append(
                PCPLintIssue(
                    rule_id=PCPLintRuleId.PCP002,
                    severity=PCPLintSeverity.ERROR,
                    message="pattern_id is required",
                    field_path="pattern_id",
                    suggestion="Set pattern_id to the associated pattern ID",
                )
            )

        # PCP003: name and summary
        if not data.get("name"):
            result.issues.append(
                PCPLintIssue(
                    rule_id=PCPLintRuleId.PCP003,
                    severity=PCPLintSeverity.ERROR,
                    message="name is required",
                    field_path="name",
                    suggestion="Add a human-readable pattern name (2-5 words)",
                )
            )
        if not data.get("summary"):
            result.issues.append(
                PCPLintIssue(
                    rule_id=PCPLintRuleId.PCP003,
                    severity=PCPLintSeverity.ERROR,
                    message="summary is required",
                    field_path="summary",
                    suggestion="Add a brief summary (1-2 sentences)",
                )
            )

        # PCP004: ID format
        pcp_id = data.get("id", "")
        if pcp_id and not pcp_id.startswith("pcp-"):
            result.issues.append(
                PCPLintIssue(
                    rule_id=PCPLintRuleId.PCP004,
                    severity=PCPLintSeverity.ERROR,
                    message=f"PCP ID must start with 'pcp-': {pcp_id}",
                    field_path="id",
                    suggestion=f"Change ID to 'pcp-{pcp_id}'",
                )
            )

    def _lint_determinism(self, data: Dict[str, Any], result: PCPLintResult) -> None:
        """Check determinism constraints."""
        determinism = data.get("determinism", {})

        # PCP010: no_rag must be true
        if determinism.get("no_rag") is not True:
            result.issues.append(
                PCPLintIssue(
                    rule_id=PCPLintRuleId.PCP010,
                    severity=PCPLintSeverity.ERROR,
                    message="determinism.no_rag must be true",
                    field_path="determinism.no_rag",
                    suggestion="Set no_rag: true to enforce deterministic context",
                )
            )

        # PCP011: no_name_heuristics must be true
        if determinism.get("no_name_heuristics") is not True:
            result.issues.append(
                PCPLintIssue(
                    rule_id=PCPLintRuleId.PCP011,
                    severity=PCPLintSeverity.ERROR,
                    message="determinism.no_name_heuristics must be true",
                    field_path="determinism.no_name_heuristics",
                    suggestion="Set no_name_heuristics: true to enforce behavior-first detection",
                )
            )

    def _lint_budget(self, data: Dict[str, Any], result: PCPLintResult) -> None:
        """Check budget ordering constraint."""
        budget = data.get("budget", {})
        cheap = budget.get("cheap_pass_tokens", 1200)
        verify = budget.get("verify_pass_tokens", 1800)
        deep = budget.get("deep_pass_tokens", 2400)

        # PCP012: Budget ordering
        if cheap >= verify or verify >= deep:
            result.issues.append(
                PCPLintIssue(
                    rule_id=PCPLintRuleId.PCP012,
                    severity=PCPLintSeverity.ERROR,
                    message=f"Budget ordering violated: cheap({cheap}) < verify({verify}) < deep({deep}) required",
                    field_path="budget",
                    suggestion="Adjust token budgets so cheap < verify < deep",
                )
            )

    def _lint_op_signatures(self, data: Dict[str, Any], result: PCPLintResult) -> None:
        """Check operation signatures and ordering."""
        op_sigs = data.get("op_signatures", {})
        required_ops = set(op_sigs.get("required_ops", []))
        ordering_variants = op_sigs.get("ordering_variants", [])

        # PCP030: Ordering variants for sequence patterns
        # Only warn if there are 2+ required_ops but no ordering variants
        if len(required_ops) >= 2 and not ordering_variants:
            result.issues.append(
                PCPLintIssue(
                    rule_id=PCPLintRuleId.PCP030,
                    severity=PCPLintSeverity.WARNING,
                    message="Pattern has multiple required_ops but no ordering_variants",
                    field_path="op_signatures.ordering_variants",
                    suggestion="Consider adding ordering variants if operation sequence matters",
                )
            )

        # PCP031: Ordering variant sequence should include required_ops
        for i, variant in enumerate(ordering_variants):
            sequence = set(variant.get("sequence", []))
            missing = required_ops - sequence
            if missing:
                result.issues.append(
                    PCPLintIssue(
                        rule_id=PCPLintRuleId.PCP031,
                        severity=PCPLintSeverity.WARNING,
                        message=f"Ordering variant {i} missing required ops: {missing}",
                        field_path=f"op_signatures.ordering_variants[{i}]",
                        suggestion="Include all required_ops in the sequence",
                    )
                )

    def _lint_witnesses(self, data: Dict[str, Any], result: PCPLintResult) -> None:
        """Check witness requirements for high/critical patterns."""
        witness = data.get("witness", {})
        minimal_required = witness.get("minimal_required", [])
        negative_required = witness.get("negative_required", [])

        # Get severity
        risk_envelope = data.get("risk_envelope", {})
        severity_floor = risk_envelope.get("severity_floor", "medium")

        # Only check for high/critical patterns
        if severity_floor not in ["high", "critical"]:
            return

        # PCP020: Missing minimal witnesses
        if not minimal_required:
            result.issues.append(
                PCPLintIssue(
                    rule_id=PCPLintRuleId.PCP020,
                    severity=PCPLintSeverity.WARNING,
                    message=f"{severity_floor.upper()} severity pattern should have minimal_required witnesses",
                    field_path="witness.minimal_required",
                    suggestion="Add evidence refs that must exist for a plausible match",
                )
            )

        # PCP021: Missing negative witnesses (if no anti-signals)
        anti_signals = data.get("anti_signals", [])
        if not negative_required and not anti_signals:
            result.issues.append(
                PCPLintIssue(
                    rule_id=PCPLintRuleId.PCP021,
                    severity=PCPLintSeverity.WARNING,
                    message=f"{severity_floor.upper()} severity pattern should have negative_required witnesses or anti_signals",
                    field_path="witness.negative_required",
                    suggestion="Add evidence refs that must NOT exist, or add anti_signals for guards",
                )
            )

    def _lint_anti_signals(self, data: Dict[str, Any], result: PCPLintResult) -> None:
        """Check anti-signal quality."""
        anti_signals = data.get("anti_signals", [])

        for i, anti_sig in enumerate(anti_signals):
            # PCP022: Missing anti-signal for guarded pattern (checked in _lint_witnesses)
            pass

            # PCP023: Anti-signal without bypass notes
            bypass_notes = anti_sig.get("bypass_notes", [])
            guard_type = anti_sig.get("guard_type", "custom")

            # Only require bypass_notes for non-custom guards
            if guard_type != "custom" and not bypass_notes:
                result.issues.append(
                    PCPLintIssue(
                        rule_id=PCPLintRuleId.PCP023,
                        severity=PCPLintSeverity.WARNING,
                        message=f"Anti-signal '{anti_sig.get('id', i)}' lacks bypass_notes",
                        field_path=f"anti_signals[{i}].bypass_notes",
                        suggestion="Document how this guard might be bypassed (cross-function, inheritance, etc.)",
                    )
                )

        # PCP024: Check evidence_refs in exploit steps
        if self.check_evidence_refs:
            exploit_steps = data.get("exploit_steps", [])
            for i, step in enumerate(exploit_steps):
                if not step.get("evidence_refs", []):
                    result.issues.append(
                        PCPLintIssue(
                            rule_id=PCPLintRuleId.PCP024,
                            severity=PCPLintSeverity.INFO,
                            message=f"Exploit step '{step.get('id', i)}' lacks evidence_refs",
                            field_path=f"exploit_steps[{i}].evidence_refs",
                            suggestion="Add evidence references to support this step",
                        )
                    )

    def _lint_unknowns_policy(self, data: Dict[str, Any], result: PCPLintResult) -> None:
        """Check unknowns policy is explicit and appropriate."""
        unknowns_policy = data.get("unknowns_policy", {})
        missing_required = unknowns_policy.get("missing_required", "")
        missing_optional = unknowns_policy.get("missing_optional", "")
        missing_anti_signal = unknowns_policy.get("missing_anti_signal", "")

        # PCP040: Unknowns policy not explicit
        if not all([missing_required, missing_optional, missing_anti_signal]):
            result.issues.append(
                PCPLintIssue(
                    rule_id=PCPLintRuleId.PCP040,
                    severity=PCPLintSeverity.WARNING,
                    message="unknowns_policy should be explicit for all categories",
                    field_path="unknowns_policy",
                    suggestion="Set missing_required, missing_optional, and missing_anti_signal explicitly",
                )
            )

        # PCP041: High/critical with fail policy
        risk_envelope = data.get("risk_envelope", {})
        severity_floor = risk_envelope.get("severity_floor", "medium")

        if severity_floor in ["high", "critical"]:
            if missing_required == "fail":
                result.issues.append(
                    PCPLintIssue(
                        rule_id=PCPLintRuleId.PCP041,
                        severity=PCPLintSeverity.WARNING,
                        message=f"{severity_floor.upper()} pattern with 'fail' for missing_required may miss vulnerabilities",
                        field_path="unknowns_policy.missing_required",
                        suggestion="Consider 'unknown' or 'warn' to avoid false negatives on incomplete graphs",
                    )
                )

    def _lint_guard_taxonomy(self, data: Dict[str, Any], result: PCPLintResult) -> None:
        """Check guard taxonomy consistency."""
        guard_taxonomy = data.get("guard_taxonomy", [])
        anti_signals = data.get("anti_signals", [])

        # PCP050: Guard taxonomy empty but anti-signals present
        if anti_signals and not guard_taxonomy:
            result.issues.append(
                PCPLintIssue(
                    rule_id=PCPLintRuleId.PCP050,
                    severity=PCPLintSeverity.INFO,
                    message="anti_signals present but guard_taxonomy is empty",
                    field_path="guard_taxonomy",
                    suggestion="Add guard_taxonomy entries to document guard types and expected ops",
                )
            )

    def _lint_counterfactuals(self, data: Dict[str, Any], result: PCPLintResult) -> None:
        """Check counterfactual references."""
        counterfactuals = data.get("counterfactuals", [])
        anti_signal_ids = {a.get("id", "") for a in data.get("anti_signals", [])}

        # PCP051: Counterfactual references non-existent anti-signal
        for i, cf in enumerate(counterfactuals):
            if_removed = cf.get("if_removed", "")
            if if_removed and if_removed not in anti_signal_ids:
                result.issues.append(
                    PCPLintIssue(
                        rule_id=PCPLintRuleId.PCP051,
                        severity=PCPLintSeverity.WARNING,
                        message=f"Counterfactual '{cf.get('id', i)}' references non-existent anti-signal: {if_removed}",
                        field_path=f"counterfactuals[{i}].if_removed",
                        suggestion=f"Add anti-signal with id '{if_removed}' or fix reference",
                    )
                )

    def _lint_evidence_requirements(self, data: Dict[str, Any], result: PCPLintResult) -> None:
        """Check evidence requirements completeness."""
        evidence_req = data.get("evidence_requirements", {})

        # PCP070: No node_types
        if not evidence_req.get("node_types", []):
            result.issues.append(
                PCPLintIssue(
                    rule_id=PCPLintRuleId.PCP070,
                    severity=PCPLintSeverity.INFO,
                    message="evidence_requirements.node_types is empty",
                    field_path="evidence_requirements.node_types",
                    suggestion="Specify required node types (e.g., Function, Call)",
                )
            )

        # PCP071: No edge_types
        if not evidence_req.get("edge_types", []):
            result.issues.append(
                PCPLintIssue(
                    rule_id=PCPLintRuleId.PCP071,
                    severity=PCPLintSeverity.INFO,
                    message="evidence_requirements.edge_types is empty",
                    field_path="evidence_requirements.edge_types",
                    suggestion="Specify required edge types (e.g., CALLS, WRITES_STATE)",
                )
            )


def lint_pcp_file(path: Path, strict: bool = False) -> PCPLintResult:
    """Convenience function to lint a single PCP file.

    Args:
        path: Path to PCP YAML file
        strict: If True, treat warnings as errors

    Returns:
        PCPLintResult with all issues found
    """
    linter = PCPLinter(strict_mode=strict)
    return linter.lint_file(path)


def lint_pcp_directory(
    directory: Path,
    pattern: str = "*.pcp.yaml",
    strict: bool = False,
) -> List[PCPLintResult]:
    """Lint all PCP files in a directory.

    Args:
        directory: Path to directory containing PCP files
        pattern: Glob pattern for PCP files
        strict: If True, treat warnings as errors

    Returns:
        List of PCPLintResult for each file
    """
    linter = PCPLinter(strict_mode=strict)
    results = []

    for pcp_file in directory.rglob(pattern):
        result = linter.lint_file(pcp_file)
        results.append(result)

    return results


def validate_pcp_schema(data: Dict[str, Any]) -> List[PCPLintIssue]:
    """Validate PCP data against schema and lint rules.

    Combines Pydantic schema validation with lint rules.

    Args:
        data: PCP data dictionary

    Returns:
        List of PCPLintIssue for any issues found
    """
    issues = []

    # First, try Pydantic validation
    try:
        pcp = PatternContextPackV2.model_validate(data)
        # If validation passes, run lint rules
        linter = PCPLinter()
        result = linter.lint_pcp(pcp)
        issues.extend(result.issues)
    except Exception as e:
        # Schema validation failed
        issues.append(
            PCPLintIssue(
                rule_id=PCPLintRuleId.PCP001,
                severity=PCPLintSeverity.ERROR,
                message=f"Schema validation failed: {e}",
            )
        )

    return issues
