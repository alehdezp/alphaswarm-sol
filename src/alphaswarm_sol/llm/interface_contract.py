"""Graph Interface Contract v2 - Validator and Compatibility Shim.

This module enforces the Graph Interface Contract v2 as a serialization gate.
All LLM-facing outputs MUST pass validation before being emitted.

Key responsibilities:
1. Load and validate outputs against the v2 JSON Schema
2. Enforce ABI semver compatibility
3. Provide v1 -> v2 compatibility shim with explicit defaults
4. Manage unknowns budget gating
5. Generate deterministic evidence IDs

Reference: docs/reference/graph-interface-v2.md
Schema: schemas/graph_interface_v2.json
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import jsonschema
    from jsonschema import Draft202012Validator, ValidationError

    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    ValidationError = Exception  # type: ignore

logger = logging.getLogger(__name__)

# Current contract version
CONTRACT_VERSION = "2.0.0"
CONTRACT_MAJOR = 2
CONTRACT_MINOR = 0
CONTRACT_PATCH = 0

# Schema file location (relative to project root)
SCHEMA_PATH = Path(__file__).parent.parent.parent.parent / "schemas" / "graph_interface_v2.json"


class GraphInterfaceContractViolation(Exception):
    """Raised when output violates the Graph Interface Contract v2."""

    def __init__(self, message: str, errors: Optional[List[str]] = None):
        super().__init__(message)
        self.errors = errors or []


class SliceMode(str, Enum):
    """Slicing modes for graph extraction."""

    STANDARD = "standard"
    DEBUG = "debug"


class ClauseStatus(str, Enum):
    """Status of a pattern clause."""

    MATCHED = "matched"
    FAILED = "failed"
    UNKNOWN = "unknown"


class Severity(str, Enum):
    """Finding severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EvidenceMissingReason(str, Enum):
    """Reason codes for missing evidence."""

    TAINT_DATAFLOW_UNAVAILABLE = "taint_dataflow_unavailable"
    DOMINANCE_UNKNOWN = "dominance_unknown"
    INTERPROCEDURAL_TRUNCATED = "interprocedural_truncated"
    EXTERNAL_RETURN_UNTRACKED = "external_return_untracked"
    ALIASING_UNKNOWN = "aliasing_unknown"
    SANITIZER_UNCERTAIN = "sanitizer_uncertain"
    LEGACY_NO_EVIDENCE = "legacy_no_evidence"


class OmissionReason(str, Enum):
    """Reason codes for omissions."""

    MODIFIER_NOT_TRAVERSED = "modifier_not_traversed"
    INHERITED_NOT_TRAVERSED = "inherited_not_traversed"
    EXTERNAL_TARGET_UNKNOWN = "external_target_unknown"
    BUDGET_EXCEEDED = "budget_exceeded"
    DEPTH_LIMIT_REACHED = "depth_limit_reached"
    LIBRARY_EXCLUDED = "library_excluded"


@dataclass
class UnknownsBudget:
    """Configuration for unknowns budget gating.

    Defines limits on how many unknown clauses are acceptable
    before a finding is marked as insufficient evidence.
    """

    max_ratio: float = 0.3  # Max unknown/total ratio
    max_absolute: int = 2  # Max absolute unknown count
    critical_clauses: List[str] = field(default_factory=list)  # Cannot be unknown


@dataclass
class EvidenceRef:
    """Reference to evidence in source code."""

    file: str
    line: int
    node_id: str
    snippet_id: str
    build_hash: str
    column: Optional[int] = None
    snippet: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result: Dict[str, Any] = {
            "file": self.file,
            "line": self.line,
            "node_id": self.node_id,
            "snippet_id": self.snippet_id,
            "build_hash": self.build_hash,
        }
        if self.column is not None:
            result["column"] = self.column
        if self.snippet is not None:
            result["snippet"] = self.snippet[:200]  # Max 200 chars
        return result


@dataclass
class ClauseMatrixEntry:
    """Entry in the clause truth table."""

    clause: str
    status: ClauseStatus
    evidence_refs: List[EvidenceRef] = field(default_factory=list)
    omission_refs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "clause": self.clause,
            "status": self.status.value,
            "evidence_refs": [e.to_dict() for e in self.evidence_refs],
            "omission_refs": self.omission_refs,
        }


@dataclass
class CutSetEntry:
    """Entry in the cut set (traversal blockers)."""

    blocker: str
    reason: OmissionReason
    impact: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result: Dict[str, Any] = {
            "blocker": self.blocker,
            "reason": self.reason.value,
        }
        if self.impact is not None:
            result["impact"] = self.impact
        return result


@dataclass
class OmissionLedger:
    """Ledger of omissions from graph extraction."""

    coverage_score: float
    cut_set: List[CutSetEntry] = field(default_factory=list)
    excluded_edges: List[str] = field(default_factory=list)
    omitted_nodes: List[str] = field(default_factory=list)
    slice_mode: SliceMode = SliceMode.STANDARD

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "coverage_score": self.coverage_score,
            "cut_set": [c.to_dict() for c in self.cut_set],
            "excluded_edges": self.excluded_edges,
            "omitted_nodes": self.omitted_nodes,
            "slice_mode": self.slice_mode.value,
        }


def generate_evidence_id(build_hash: str, node_id: str, line: int, column: int = 0) -> str:
    """Generate deterministic evidence ID.

    Format: EVD-<hash-8>
    Where hash = SHA256(build_hash + node_id + line + column)[:8]

    Args:
        build_hash: 12-char graph build hash
        node_id: Graph node identifier
        line: Line number (1-indexed)
        column: Column number (1-indexed, default 0)

    Returns:
        Deterministic evidence ID (EVD-xxxxxxxx)
    """
    content = f"{build_hash}:{node_id}:{line}:{column}"
    hash_val = hashlib.sha256(content.encode()).hexdigest()[:8]
    return f"EVD-{hash_val}"


def generate_build_hash(source_content: str) -> str:
    """Generate graph build hash from source content.

    Args:
        source_content: Concatenated source file contents

    Returns:
        12-char hex build hash
    """
    return hashlib.sha256(source_content.encode()).hexdigest()[:12]


class GraphInterfaceValidator:
    """Validates outputs against Graph Interface Contract v2.

    This validator enforces schema compliance at serialization time.
    Invalid outputs raise GraphInterfaceContractViolation.
    """

    def __init__(self, schema_path: Optional[Path] = None, strict: bool = True):
        """Initialize validator.

        Args:
            schema_path: Path to JSON schema file (default: schemas/graph_interface_v2.json)
            strict: If True, raise on validation errors. If False, log warnings.
        """
        self.schema_path = schema_path or SCHEMA_PATH
        self.strict = strict
        self._schema: Optional[Dict[str, Any]] = None
        self._validator: Optional[Any] = None

    @property
    def schema(self) -> Dict[str, Any]:
        """Load and cache the JSON schema."""
        if self._schema is None:
            if not self.schema_path.exists():
                raise FileNotFoundError(
                    f"Graph Interface v2 schema not found at {self.schema_path}"
                )
            with open(self.schema_path) as f:
                self._schema = json.load(f)
        return self._schema

    @property
    def validator(self) -> Any:
        """Get JSON Schema validator instance."""
        if self._validator is None:
            if not JSONSCHEMA_AVAILABLE:
                raise ImportError(
                    "jsonschema package required for Graph Interface validation. "
                    "Install with: pip install jsonschema"
                )
            self._validator = Draft202012Validator(self.schema)
        return self._validator

    def validate(self, output: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate output against v2 schema.

        Args:
            output: Output dictionary to validate

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        if not JSONSCHEMA_AVAILABLE:
            logger.warning("jsonschema not available, skipping validation")
            return True, []

        errors: List[str] = []

        # Schema validation
        try:
            self.validator.validate(output)
        except ValidationError as e:
            errors.append(f"Schema validation failed: {e.message}")
            # Collect all errors
            for error in sorted(self.validator.iter_errors(output), key=str):
                if error.message not in [e.split(": ", 1)[-1] for e in errors]:
                    errors.append(f"  - {error.json_path}: {error.message}")

        # Semantic validation
        errors.extend(self._validate_semantic(output))

        return len(errors) == 0, errors

    def _validate_semantic(self, output: Dict[str, Any]) -> List[str]:
        """Perform semantic validation beyond JSON Schema.

        Args:
            output: Output dictionary to validate

        Returns:
            List of semantic validation errors
        """
        errors: List[str] = []

        # Check version compatibility
        version = output.get("interface_version", "")
        if version:
            errors.extend(self._validate_version(version))

        # Check build hash consistency
        build_hash = output.get("build_hash", "")
        if build_hash:
            errors.extend(self._validate_build_hash_consistency(output, build_hash))

        # Check clause list completeness for each finding
        for i, finding in enumerate(output.get("findings", [])):
            errors.extend(self._validate_finding_clauses(finding, i))

        # Check coverage score bounds
        errors.extend(self._validate_coverage_scores(output))

        return errors

    def _validate_version(self, version: str) -> List[str]:
        """Validate version compatibility.

        Args:
            version: Version string (e.g., "2.0.0")

        Returns:
            List of version-related errors
        """
        errors: List[str] = []
        try:
            parts = version.split(".")
            major = int(parts[0])
            if major != CONTRACT_MAJOR:
                errors.append(
                    f"Incompatible major version: {version} (expected {CONTRACT_MAJOR}.x.x)"
                )
        except (ValueError, IndexError):
            errors.append(f"Invalid version format: {version}")
        return errors

    def _validate_build_hash_consistency(
        self, output: Dict[str, Any], build_hash: str
    ) -> List[str]:
        """Validate all evidence refs use consistent build hash.

        Args:
            output: Output dictionary
            build_hash: Expected build hash

        Returns:
            List of consistency errors
        """
        errors: List[str] = []
        for i, finding in enumerate(output.get("findings", [])):
            for j, ref in enumerate(finding.get("evidence_refs", [])):
                ref_hash = ref.get("build_hash", "")
                if ref_hash and ref_hash != build_hash:
                    errors.append(
                        f"Finding[{i}].evidence_refs[{j}]: build_hash mismatch "
                        f"({ref_hash} != {build_hash})"
                    )
            for k, entry in enumerate(finding.get("clause_matrix", [])):
                for m, ref in enumerate(entry.get("evidence_refs", [])):
                    ref_hash = ref.get("build_hash", "")
                    if ref_hash and ref_hash != build_hash:
                        errors.append(
                            f"Finding[{i}].clause_matrix[{k}].evidence_refs[{m}]: "
                            f"build_hash mismatch ({ref_hash} != {build_hash})"
                        )
        return errors

    def _validate_finding_clauses(
        self, finding: Dict[str, Any], index: int
    ) -> List[str]:
        """Validate clause list completeness and consistency.

        Args:
            finding: Finding dictionary
            index: Finding index for error messages

        Returns:
            List of clause validation errors
        """
        errors: List[str] = []

        matched = set(finding.get("matched_clauses", []))
        failed = set(finding.get("failed_clauses", []))
        unknown = set(finding.get("unknown_clauses", []))

        # Check for duplicates across lists
        overlap_mf = matched & failed
        overlap_mu = matched & unknown
        overlap_fu = failed & unknown

        if overlap_mf:
            errors.append(
                f"Finding[{index}]: clauses in both matched and failed: {overlap_mf}"
            )
        if overlap_mu:
            errors.append(
                f"Finding[{index}]: clauses in both matched and unknown: {overlap_mu}"
            )
        if overlap_fu:
            errors.append(
                f"Finding[{index}]: clauses in both failed and unknown: {overlap_fu}"
            )

        # Check clause_matrix alignment
        matrix_clauses = set()
        for entry in finding.get("clause_matrix", []):
            clause_id = entry.get("clause", "")
            status = entry.get("status", "")
            matrix_clauses.add(clause_id)

            # Check status matches list membership
            if status == "matched" and clause_id not in matched:
                errors.append(
                    f"Finding[{index}]: clause_matrix has {clause_id} as matched, "
                    "but not in matched_clauses"
                )
            elif status == "failed" and clause_id not in failed:
                errors.append(
                    f"Finding[{index}]: clause_matrix has {clause_id} as failed, "
                    "but not in failed_clauses"
                )
            elif status == "unknown" and clause_id not in unknown:
                errors.append(
                    f"Finding[{index}]: clause_matrix has {clause_id} as unknown, "
                    "but not in unknown_clauses"
                )

            # Check evidence linkage for matched clauses
            if status == "matched":
                has_evidence = len(entry.get("evidence_refs", [])) > 0
                has_omission = len(entry.get("omission_refs", [])) > 0
                if not has_evidence and not has_omission:
                    # Check if finding-level evidence_missing covers this clause
                    evidence_missing = finding.get("evidence_missing", [])
                    covered = any(
                        em.get("clause") == clause_id for em in evidence_missing
                    )
                    if not covered:
                        errors.append(
                            f"Finding[{index}]: matched clause {clause_id} has no evidence"
                        )

            # Check omission linkage for unknown clauses
            if status == "unknown":
                has_omission = len(entry.get("omission_refs", [])) > 0
                if not has_omission:
                    errors.append(
                        f"Finding[{index}]: unknown clause {clause_id} has no omission reason"
                    )

        # Check all clauses in lists appear in matrix
        all_clauses = matched | failed | unknown
        missing_from_matrix = all_clauses - matrix_clauses
        if missing_from_matrix:
            errors.append(
                f"Finding[{index}]: clauses missing from clause_matrix: {missing_from_matrix}"
            )

        return errors

    def _validate_coverage_scores(self, output: Dict[str, Any]) -> List[str]:
        """Validate coverage scores are in valid range.

        Args:
            output: Output dictionary

        Returns:
            List of coverage score errors
        """
        errors: List[str] = []

        # Check summary coverage
        summary_coverage = output.get("summary", {}).get("coverage_score")
        if summary_coverage is not None:
            if not (0.0 <= summary_coverage <= 1.0):
                errors.append(
                    f"summary.coverage_score out of range: {summary_coverage}"
                )

        # Check global omissions coverage
        global_coverage = output.get("omissions", {}).get("coverage_score")
        if global_coverage is not None:
            if not (0.0 <= global_coverage <= 1.0):
                errors.append(
                    f"omissions.coverage_score out of range: {global_coverage}"
                )

        # Check per-finding coverage
        for i, finding in enumerate(output.get("findings", [])):
            finding_coverage = finding.get("omissions", {}).get("coverage_score")
            if finding_coverage is not None:
                if not (0.0 <= finding_coverage <= 1.0):
                    errors.append(
                        f"findings[{i}].omissions.coverage_score out of range: "
                        f"{finding_coverage}"
                    )

        return errors

    def validate_and_raise(self, output: Dict[str, Any]) -> None:
        """Validate output and raise on errors (fail-fast gate).

        Args:
            output: Output dictionary to validate

        Raises:
            GraphInterfaceContractViolation: If validation fails
        """
        is_valid, errors = self.validate(output)
        if not is_valid:
            if self.strict:
                raise GraphInterfaceContractViolation(
                    f"Output violates Graph Interface Contract v2: {len(errors)} errors",
                    errors=errors,
                )
            else:
                for error in errors:
                    logger.warning(f"Graph Interface Contract warning: {error}")


class UnknownsBudgetGate:
    """Gate for checking unknowns budget compliance.

    Determines if a finding has acceptable level of unknown clauses.
    """

    def __init__(self, budget: Optional[UnknownsBudget] = None):
        """Initialize gate.

        Args:
            budget: Unknowns budget configuration (default: 30% ratio, 2 absolute max)
        """
        self.budget = budget or UnknownsBudget()

    def check(self, finding: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Check if finding meets unknowns budget.

        Args:
            finding: Finding dictionary

        Returns:
            Tuple of (passes_gate, reason_if_failed)
        """
        matched = finding.get("matched_clauses", [])
        failed = finding.get("failed_clauses", [])
        unknown = finding.get("unknown_clauses", [])

        total = len(matched) + len(failed) + len(unknown)
        if total == 0:
            return True, None

        unknown_ratio = len(unknown) / total

        # Check ratio limit
        if unknown_ratio > self.budget.max_ratio:
            return False, (
                f"Unknown ratio {unknown_ratio:.2f} exceeds max {self.budget.max_ratio}"
            )

        # Check absolute limit
        if len(unknown) > self.budget.max_absolute:
            return False, (
                f"Unknown count {len(unknown)} exceeds max {self.budget.max_absolute}"
            )

        # Check critical clauses
        for clause in self.budget.critical_clauses:
            if clause in unknown:
                return False, f"Critical clause {clause} is unknown"

        return True, None

    def apply_to_findings(
        self, findings: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Apply unknowns budget gate to findings, marking insufficient evidence.

        Args:
            findings: List of finding dictionaries

        Returns:
            Findings with insufficient_evidence flag set where applicable
        """
        result = []
        for finding in findings:
            passes, reason = self.check(finding)
            finding_copy = dict(finding)
            if not passes:
                finding_copy["insufficient_evidence"] = True
                logger.info(
                    f"Finding {finding.get('id', 'unknown')} marked insufficient: {reason}"
                )
            result.append(finding_copy)
        return result


class V1ToV2CompatibilityShim:
    """Compatibility shim for transforming v1 outputs to v2 format.

    This shim applies explicit defaults for new required fields and
    emits deprecation warnings for legacy patterns.
    """

    def __init__(self, default_build_hash: str = "000000000000"):
        """Initialize shim.

        Args:
            default_build_hash: Build hash to use for legacy outputs
        """
        self.default_build_hash = default_build_hash

    def transform(self, v1_output: Dict[str, Any]) -> Dict[str, Any]:
        """Transform v1 output to v2 format.

        Args:
            v1_output: v1-format output dictionary

        Returns:
            v2-format output dictionary
        """
        logger.warning(
            "Transforming v1 output to v2 format via compatibility shim. "
            "Update to native v2 output generation."
        )

        # Start with copy
        v2_output: Dict[str, Any] = dict(v1_output)

        # Transform version
        if "version" in v2_output:
            del v2_output["version"]
        v2_output["interface_version"] = CONTRACT_VERSION

        # Add build_hash if missing
        if "build_hash" not in v2_output:
            v2_output["build_hash"] = self.default_build_hash
            logger.warning(
                f"Using default build_hash: {self.default_build_hash} (legacy mode)"
            )

        # Add timestamp if missing
        if "timestamp" not in v2_output:
            v2_output["timestamp"] = datetime.utcnow().isoformat() + "Z"

        # Ensure query section
        if "query" not in v2_output:
            v2_output["query"] = {
                "kind": "fetch",
                "id": "legacy",
                "source": "legacy_v1_output",
            }

        # Ensure summary section
        if "summary" not in v2_output:
            findings = v2_output.get("findings", [])
            v2_output["summary"] = {
                "nodes": 0,
                "edges": 0,
                "findings": len(findings),
                "coverage_score": 1.0,
                "omissions_present": False,
                "unknowns_count": 0,
            }

        # Ensure global omissions
        if "omissions" not in v2_output:
            v2_output["omissions"] = {
                "coverage_score": 1.0,
                "cut_set": [],
                "excluded_edges": [],
                "omitted_nodes": [],
                "slice_mode": "standard",
            }

        # Transform findings
        v2_output["findings"] = [
            self._transform_finding(f, v2_output["build_hash"])
            for f in v2_output.get("findings", [])
        ]

        # Update summary unknowns count
        total_unknowns = sum(
            len(f.get("unknown_clauses", [])) for f in v2_output["findings"]
        )
        v2_output["summary"]["unknowns_count"] = total_unknowns

        return v2_output

    def _transform_finding(
        self, finding: Dict[str, Any], build_hash: str
    ) -> Dict[str, Any]:
        """Transform a single finding to v2 format.

        Args:
            finding: v1 finding dictionary
            build_hash: Build hash to use for evidence

        Returns:
            v2 finding dictionary
        """
        f = dict(finding)

        # Ensure clause lists
        if "matched_clauses" not in f:
            f["matched_clauses"] = []
        if "failed_clauses" not in f:
            f["failed_clauses"] = []
        if "unknown_clauses" not in f:
            f["unknown_clauses"] = []

        # Build clause_matrix if missing
        if "clause_matrix" not in f:
            f["clause_matrix"] = self._build_clause_matrix(f, build_hash)

        # Ensure evidence_refs or evidence_missing
        if "evidence_refs" not in f or not f["evidence_refs"]:
            if "evidence_missing" not in f or not f["evidence_missing"]:
                # Add legacy marker
                f["evidence_missing"] = [
                    {
                        "reason": "legacy_no_evidence",
                        "clause": "legacy",
                        "details": "Evidence not available in v1 format",
                    }
                ]

        # Transform evidence_refs to include build_hash
        if "evidence_refs" in f:
            for ref in f["evidence_refs"]:
                if "build_hash" not in ref:
                    ref["build_hash"] = build_hash
                if "snippet_id" not in ref:
                    ref["snippet_id"] = generate_evidence_id(
                        build_hash,
                        ref.get("node_id", "legacy"),
                        ref.get("line", 0),
                        ref.get("column", 0),
                    )

        # Ensure finding-level omissions
        if "omissions" not in f:
            f["omissions"] = {
                "coverage_score": 1.0,
                "cut_set": [],
                "excluded_edges": [],
                "slice_mode": "standard",
            }

        return f

    def _build_clause_matrix(
        self, finding: Dict[str, Any], build_hash: str
    ) -> List[Dict[str, Any]]:
        """Build clause_matrix from clause lists.

        Args:
            finding: Finding dictionary
            build_hash: Build hash for evidence

        Returns:
            List of clause matrix entries
        """
        matrix = []

        for clause in finding.get("matched_clauses", []):
            matrix.append(
                {
                    "clause": clause,
                    "status": "matched",
                    "evidence_refs": [],  # Will be populated from finding-level refs
                    "omission_refs": [],
                }
            )

        for clause in finding.get("failed_clauses", []):
            matrix.append(
                {
                    "clause": clause,
                    "status": "failed",
                    "evidence_refs": [],
                    "omission_refs": [],
                }
            )

        for clause in finding.get("unknown_clauses", []):
            matrix.append(
                {
                    "clause": clause,
                    "status": "unknown",
                    "evidence_refs": [],
                    "omission_refs": ["legacy_no_evidence"],
                }
            )

        return matrix


# Singleton instances for convenience
_default_validator: Optional[GraphInterfaceValidator] = None
_default_budget_gate: Optional[UnknownsBudgetGate] = None
_default_shim: Optional[V1ToV2CompatibilityShim] = None


def get_validator(strict: bool = True) -> GraphInterfaceValidator:
    """Get the default validator instance.

    Args:
        strict: If True, raise on validation errors

    Returns:
        GraphInterfaceValidator instance
    """
    global _default_validator
    if _default_validator is None or _default_validator.strict != strict:
        _default_validator = GraphInterfaceValidator(strict=strict)
    return _default_validator


def get_budget_gate(budget: Optional[UnknownsBudget] = None) -> UnknownsBudgetGate:
    """Get the default unknowns budget gate.

    Args:
        budget: Optional custom budget configuration

    Returns:
        UnknownsBudgetGate instance
    """
    global _default_budget_gate
    if budget is not None:
        return UnknownsBudgetGate(budget)
    if _default_budget_gate is None:
        _default_budget_gate = UnknownsBudgetGate()
    return _default_budget_gate


def get_compatibility_shim(
    default_build_hash: str = "000000000000",
) -> V1ToV2CompatibilityShim:
    """Get the default v1-to-v2 compatibility shim.

    Args:
        default_build_hash: Build hash for legacy outputs

    Returns:
        V1ToV2CompatibilityShim instance
    """
    global _default_shim
    if _default_shim is None:
        _default_shim = V1ToV2CompatibilityShim(default_build_hash)
    return _default_shim


def validate_output(output: Dict[str, Any], strict: bool = True) -> Tuple[bool, List[str]]:
    """Validate output against Graph Interface Contract v2.

    Args:
        output: Output dictionary to validate
        strict: If True, raise on validation errors

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    return get_validator(strict).validate(output)


def validate_and_serialize(
    output: Dict[str, Any],
    strict: bool = True,
    indent: Optional[int] = None,
) -> str:
    """Validate output and serialize to JSON.

    This is the recommended serialization path for all LLM-facing outputs.

    Args:
        output: Output dictionary to validate and serialize
        strict: If True, raise on validation errors (default: True)
        indent: JSON indentation (default: None for compact)

    Returns:
        JSON string

    Raises:
        GraphInterfaceContractViolation: If validation fails in strict mode
    """
    get_validator(strict).validate_and_raise(output)
    return json.dumps(output, indent=indent, default=str)


def transform_v1_to_v2(v1_output: Dict[str, Any]) -> Dict[str, Any]:
    """Transform v1 output to v2 format via compatibility shim.

    Args:
        v1_output: v1-format output dictionary

    Returns:
        v2-format output dictionary
    """
    return get_compatibility_shim().transform(v1_output)


__all__ = [
    # Core classes
    "GraphInterfaceValidator",
    "GraphInterfaceContractViolation",
    "UnknownsBudgetGate",
    "V1ToV2CompatibilityShim",
    # Data classes
    "UnknownsBudget",
    "EvidenceRef",
    "ClauseMatrixEntry",
    "CutSetEntry",
    "OmissionLedger",
    # Enums
    "SliceMode",
    "ClauseStatus",
    "Severity",
    "EvidenceMissingReason",
    "OmissionReason",
    # Helper functions
    "generate_evidence_id",
    "generate_build_hash",
    "validate_output",
    "validate_and_serialize",
    "transform_v1_to_v2",
    # Singleton accessors
    "get_validator",
    "get_budget_gate",
    "get_compatibility_shim",
    # Constants
    "CONTRACT_VERSION",
]
