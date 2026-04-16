"""Ground Truth Schema and Matching for Real-World Validation (Phase 5).

Provides structured representation of audit findings and matching logic
for comparing VKG detection against known vulnerabilities.

Philosophy:
- Audit reports are ground truth for VKG-detectable vulnerability types
- Business logic bugs are OUT of scope (VKG can't understand semantics)
- Matching is fuzzy (same file + close lines + related category)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import json
import yaml


class VulnerabilityCategory(str, Enum):
    """Vulnerability categories that VKG can potentially detect."""
    # Core patterns VKG excels at
    REENTRANCY = "reentrancy"
    ACCESS_CONTROL = "access_control"
    ORACLE_MANIPULATION = "oracle_manipulation"
    MEV_SLIPPAGE = "mev_slippage"
    DOS = "dos"
    ARITHMETIC = "arithmetic"
    SIGNATURE = "signature"
    DELEGATECALL = "delegatecall"
    UPGRADE_PROXY = "upgrade_proxy"
    TIMESTAMP = "timestamp"
    INPUT_VALIDATION = "input_validation"
    UNCHECKED_RETURN = "unchecked_return"
    CRYPTOGRAPHIC = "cryptographic"

    # Categories VKG may partially detect
    FLASH_LOAN = "flash_loan"
    FRONTRUNNING = "frontrunning"
    GOVERNANCE = "governance"

    # Out of scope for VKG (for documentation purposes)
    BUSINESS_LOGIC = "business_logic"
    ECONOMIC = "economic"
    GAS_OPTIMIZATION = "gas_optimization"
    INFORMATIONAL = "informational"

    @classmethod
    def vkg_detectable(cls) -> Set["VulnerabilityCategory"]:
        """Categories that VKG can reasonably detect."""
        return {
            cls.REENTRANCY,
            cls.ACCESS_CONTROL,
            cls.ORACLE_MANIPULATION,
            cls.MEV_SLIPPAGE,
            cls.DOS,
            cls.ARITHMETIC,
            cls.SIGNATURE,
            cls.DELEGATECALL,
            cls.UPGRADE_PROXY,
            cls.TIMESTAMP,
            cls.FLASH_LOAN,
            cls.FRONTRUNNING,
            cls.INPUT_VALIDATION,
            cls.UNCHECKED_RETURN,
        }

    @classmethod
    def out_of_scope(cls) -> Set["VulnerabilityCategory"]:
        """Categories VKG cannot detect (require semantic understanding)."""
        return {
            cls.BUSINESS_LOGIC,
            cls.ECONOMIC,
            cls.GAS_OPTIMIZATION,
            cls.INFORMATIONAL,
            cls.CRYPTOGRAPHIC,  # Complex crypto proofs
        }


class Severity(str, Enum):
    """Vulnerability severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


@dataclass
class AuditFinding:
    """A finding from an audit report.

    Represents ground truth for validation.
    """
    id: str  # Original finding ID from audit (e.g., "C-01", "H-02")
    title: str
    category: VulnerabilityCategory
    severity: Severity
    file: str  # Relative path to affected file
    function: Optional[str] = None  # Function name if applicable
    line_start: int = 0
    line_end: int = 0
    description: str = ""
    recommendation: str = ""
    vkg_should_find: bool = True  # False for business logic, economic, etc.

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category.value,
            "severity": self.severity.value,
            "location": {
                "file": self.file,
                "function": self.function,
                "line_start": self.line_start,
                "line_end": self.line_end,
            },
            "description": self.description,
            "recommendation": self.recommendation,
            "vkg_should_find": self.vkg_should_find,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditFinding":
        """Create from dictionary."""
        location = data.get("location", {})
        return cls(
            id=data["id"],
            title=data["title"],
            category=VulnerabilityCategory(data["category"]),
            severity=Severity(data["severity"]),
            file=location.get("file", ""),
            function=location.get("function"),
            line_start=location.get("line_start", 0),
            line_end=location.get("line_end", 0),
            description=data.get("description", ""),
            recommendation=data.get("recommendation", ""),
            vkg_should_find=data.get("vkg_should_find", True),
        )


@dataclass
class ProjectGroundTruth:
    """Ground truth for a project's audit findings.

    Contains all findings from audit report(s) for validation.
    """
    project_name: str
    project_type: str  # lending, dex, nft, governance, etc.
    audit_source: str  # Trail of Bits, OpenZeppelin, etc.
    audit_date: str
    audit_url: Optional[str] = None
    code_url: str = ""
    code_commit: str = ""
    solidity_version: str = ""
    findings: List[AuditFinding] = field(default_factory=list)
    notes: str = ""

    @property
    def total_findings(self) -> int:
        """Total number of findings."""
        return len(self.findings)

    @property
    def vkg_detectable_findings(self) -> List[AuditFinding]:
        """Findings that VKG should be able to detect."""
        return [f for f in self.findings if f.vkg_should_find]

    @property
    def out_of_scope_findings(self) -> List[AuditFinding]:
        """Findings outside VKG's detection capability."""
        return [f for f in self.findings if not f.vkg_should_find]

    def findings_by_category(self) -> Dict[VulnerabilityCategory, List[AuditFinding]]:
        """Group findings by category."""
        result: Dict[VulnerabilityCategory, List[AuditFinding]] = {}
        for f in self.findings:
            if f.category not in result:
                result[f.category] = []
            result[f.category].append(f)
        return result

    def findings_by_severity(self) -> Dict[Severity, List[AuditFinding]]:
        """Group findings by severity."""
        result: Dict[Severity, List[AuditFinding]] = {}
        for f in self.findings:
            if f.severity not in result:
                result[f.severity] = []
            result[f.severity].append(f)
        return result

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "project_name": self.project_name,
            "project_type": self.project_type,
            "audit_source": self.audit_source,
            "audit_date": self.audit_date,
            "audit_url": self.audit_url,
            "code_url": self.code_url,
            "code_commit": self.code_commit,
            "solidity_version": self.solidity_version,
            "findings": [f.to_dict() for f in self.findings],
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectGroundTruth":
        """Create from dictionary."""
        findings = [
            AuditFinding.from_dict(f) for f in data.get("findings", [])
        ]
        return cls(
            project_name=data["project_name"],
            project_type=data["project_type"],
            audit_source=data["audit_source"],
            audit_date=data["audit_date"],
            audit_url=data.get("audit_url"),
            code_url=data.get("code_url", ""),
            code_commit=data.get("code_commit", ""),
            solidity_version=data.get("solidity_version", ""),
            findings=findings,
            notes=data.get("notes", ""),
        )

    def save(self, path: Path) -> None:
        """Save to YAML file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)

    @classmethod
    def load(cls, path: Path) -> "ProjectGroundTruth":
        """Load from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)


@dataclass
class VKGFinding:
    """A finding from VKG analysis.

    Normalized representation for matching against ground truth.
    """
    id: str
    pattern_id: str
    category: str
    severity: str
    file: str
    function: Optional[str]
    line: int
    confidence: float
    description: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_pattern_match(cls, match: Dict[str, Any]) -> "VKGFinding":
        """Create from pattern engine match result."""
        location = match.get("location", {})
        return cls(
            id=match.get("id", f"VKG-{hash(str(match)) % 10000:04d}"),
            pattern_id=match.get("pattern_id", "unknown"),
            category=match.get("category", "unknown"),
            severity=match.get("severity", "medium"),
            file=location.get("file", match.get("file", "")),
            function=location.get("function", match.get("function")),
            line=location.get("line", match.get("line", 0)),
            confidence=match.get("confidence", 0.5),
            description=match.get("description", match.get("why_match", "")),
            raw=match,
        )


@dataclass
class MatchResult:
    """Result of matching a VKG finding to ground truth."""
    vkg_finding: VKGFinding
    audit_finding: Optional[AuditFinding]
    is_match: bool
    match_type: str = "none"  # exact, fuzzy, category_only, none
    match_confidence: float = 0.0
    notes: str = ""


@dataclass
class ValidationResult:
    """Complete validation result for a project."""
    project_name: str
    timestamp: str
    ground_truth: ProjectGroundTruth
    vkg_findings: List[VKGFinding]
    matches: List[MatchResult]

    # Calculated metrics
    true_positives: List[Tuple[VKGFinding, AuditFinding]] = field(default_factory=list)
    false_positives: List[VKGFinding] = field(default_factory=list)
    false_negatives: List[AuditFinding] = field(default_factory=list)

    @property
    def precision(self) -> float:
        """Calculate precision (TP / (TP + FP))."""
        tp = len(self.true_positives)
        fp = len(self.false_positives)
        if tp + fp == 0:
            return 0.0
        return tp / (tp + fp)

    @property
    def recall(self) -> float:
        """Calculate recall (TP / (TP + FN))."""
        tp = len(self.true_positives)
        fn = len(self.false_negatives)
        if tp + fn == 0:
            return 0.0
        return tp / (tp + fn)

    @property
    def f1_score(self) -> float:
        """Calculate F1 score."""
        p, r = self.precision, self.recall
        if p + r == 0:
            return 0.0
        return 2 * p * r / (p + r)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "project_name": self.project_name,
            "timestamp": self.timestamp,
            "metrics": {
                "precision": round(self.precision, 4),
                "recall": round(self.recall, 4),
                "f1_score": round(self.f1_score, 4),
                "true_positives": len(self.true_positives),
                "false_positives": len(self.false_positives),
                "false_negatives": len(self.false_negatives),
            },
            "summary": {
                "total_vkg_findings": len(self.vkg_findings),
                "total_audit_findings": self.ground_truth.total_findings,
                "vkg_detectable_findings": len(self.ground_truth.vkg_detectable_findings),
                "out_of_scope_findings": len(self.ground_truth.out_of_scope_findings),
            },
            "true_positives": [
                {"vkg": v.id, "audit": a.id, "category": a.category.value}
                for v, a in self.true_positives
            ],
            "false_positives": [
                {"id": f.id, "pattern": f.pattern_id, "file": f.file, "line": f.line}
                for f in self.false_positives
            ],
            "false_negatives": [
                {"id": f.id, "title": f.title, "category": f.category.value, "severity": f.severity.value}
                for f in self.false_negatives
            ],
        }

    def save(self, path: Path) -> None:
        """Save to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)


# Category mapping for fuzzy matching
CATEGORY_ALIASES: Dict[str, Set[str]] = {
    "reentrancy": {"reentrancy", "reentrant", "cross-function-reentrancy", "read-only-reentrancy"},
    "access_control": {"access_control", "access-control", "authorization", "auth", "privilege", "permission"},
    "oracle_manipulation": {"oracle_manipulation", "oracle", "price-manipulation", "stale-price"},
    "mev_slippage": {"mev_slippage", "mev", "slippage", "sandwich", "frontrun"},
    "dos": {"dos", "denial-of-service", "unbounded-loop", "gas-limit"},
    "arithmetic": {"arithmetic", "overflow", "underflow", "integer-overflow"},
    "signature": {"signature", "ecrecover", "replay", "sig-malleability"},
    "delegatecall": {"delegatecall", "delegate-call", "proxy"},
    "upgrade_proxy": {"upgrade_proxy", "upgrade", "initializer", "storage-collision"},
    "timestamp": {"timestamp", "block-timestamp", "time-manipulation"},
}


def normalize_category(category: str) -> str:
    """Normalize category name for matching."""
    category_lower = category.lower().replace("_", "-").replace(" ", "-")

    for canonical, aliases in CATEGORY_ALIASES.items():
        if category_lower in aliases:
            return canonical

    return category_lower


def is_category_match(cat1: str, cat2: str) -> bool:
    """Check if two categories match (including aliases)."""
    norm1 = normalize_category(cat1)
    norm2 = normalize_category(cat2)

    if norm1 == norm2:
        return True

    # Check if they share a canonical category
    for canonical, aliases in CATEGORY_ALIASES.items():
        if norm1 in aliases and norm2 in aliases:
            return True

    return False


class FindingMatcher:
    """Matches VKG findings against audit ground truth.

    Uses fuzzy matching based on:
    1. File name (must match)
    2. Line proximity (within tolerance)
    3. Category similarity
    """

    def __init__(
        self,
        line_tolerance: int = 10,
        require_category_match: bool = False,
    ):
        """Initialize matcher.

        Args:
            line_tolerance: Lines within this range are considered same location
            require_category_match: If True, categories must match
        """
        self.line_tolerance = line_tolerance
        self.require_category_match = require_category_match

    def match_finding(
        self,
        vkg: VKGFinding,
        audit_findings: List[AuditFinding],
    ) -> Optional[Tuple[AuditFinding, str, float]]:
        """Match a VKG finding to audit findings.

        Returns:
            Tuple of (matched_finding, match_type, confidence) or None
        """
        best_match: Optional[Tuple[AuditFinding, str, float]] = None
        best_confidence = 0.0

        vkg_file = Path(vkg.file).name.lower()

        for audit in audit_findings:
            audit_file = Path(audit.file).name.lower()

            # File must match (by name, not full path)
            if vkg_file != audit_file:
                continue

            # Calculate match confidence
            confidence = 0.0
            match_type = "none"

            # Exact function match
            if vkg.function and audit.function and vkg.function == audit.function:
                confidence += 0.5
                match_type = "exact"

            # Line proximity
            if audit.line_start <= vkg.line <= audit.line_end:
                confidence += 0.4
                match_type = "exact" if match_type == "exact" else "fuzzy"
            elif abs(vkg.line - audit.line_start) <= self.line_tolerance:
                confidence += 0.2
                match_type = "fuzzy" if match_type != "exact" else match_type
            elif abs(vkg.line - audit.line_end) <= self.line_tolerance:
                confidence += 0.2
                match_type = "fuzzy" if match_type != "exact" else match_type

            # Category match
            if is_category_match(vkg.category, audit.category.value):
                confidence += 0.3
            elif self.require_category_match:
                continue  # Skip if category must match

            # Update best match
            if confidence > best_confidence and confidence >= 0.3:
                best_confidence = confidence
                best_match = (audit, match_type, confidence)

        return best_match

    def validate_project(
        self,
        ground_truth: ProjectGroundTruth,
        vkg_findings: List[VKGFinding],
    ) -> ValidationResult:
        """Validate VKG findings against project ground truth.

        Args:
            ground_truth: Project audit findings
            vkg_findings: VKG analysis results

        Returns:
            ValidationResult with metrics
        """
        # Only consider VKG-detectable findings for recall calculation
        detectable = ground_truth.vkg_detectable_findings
        matched_audit_ids: Set[str] = set()

        result = ValidationResult(
            project_name=ground_truth.project_name,
            timestamp=datetime.now().isoformat(),
            ground_truth=ground_truth,
            vkg_findings=vkg_findings,
            matches=[],
        )

        # Match each VKG finding
        for vkg in vkg_findings:
            match = self.match_finding(vkg, detectable)

            if match:
                audit, match_type, confidence = match
                if audit.id not in matched_audit_ids:
                    result.true_positives.append((vkg, audit))
                    matched_audit_ids.add(audit.id)
                    result.matches.append(MatchResult(
                        vkg_finding=vkg,
                        audit_finding=audit,
                        is_match=True,
                        match_type=match_type,
                        match_confidence=confidence,
                    ))
                else:
                    # Duplicate match - count as FP
                    result.false_positives.append(vkg)
                    result.matches.append(MatchResult(
                        vkg_finding=vkg,
                        audit_finding=None,
                        is_match=False,
                        notes="Duplicate match to already-matched audit finding",
                    ))
            else:
                result.false_positives.append(vkg)
                result.matches.append(MatchResult(
                    vkg_finding=vkg,
                    audit_finding=None,
                    is_match=False,
                ))

        # Find false negatives (audit findings VKG missed)
        for audit in detectable:
            if audit.id not in matched_audit_ids:
                result.false_negatives.append(audit)

        return result


def format_validation_report(result: ValidationResult) -> str:
    """Format validation result as human-readable report.

    Args:
        result: Validation result

    Returns:
        Multi-line string report
    """
    lines = [
        "=" * 70,
        f"VALIDATION REPORT: {result.project_name}",
        "=" * 70,
        "",
        "SUMMARY",
        "-" * 40,
        f"  VKG Findings:           {len(result.vkg_findings)}",
        f"  Audit Findings (total): {result.ground_truth.total_findings}",
        f"  VKG-Detectable:         {len(result.ground_truth.vkg_detectable_findings)}",
        f"  Out of Scope:           {len(result.ground_truth.out_of_scope_findings)}",
        "",
        "METRICS",
        "-" * 40,
        f"  True Positives:  {len(result.true_positives)}",
        f"  False Positives: {len(result.false_positives)}",
        f"  False Negatives: {len(result.false_negatives)}",
        "",
        f"  Precision: {result.precision:.1%}",
        f"  Recall:    {result.recall:.1%}",
        f"  F1 Score:  {result.f1_score:.1%}",
        "",
    ]

    if result.true_positives:
        lines.extend([
            "TRUE POSITIVES (VKG Correct)",
            "-" * 40,
        ])
        for vkg, audit in result.true_positives:
            lines.append(f"  VKG:{vkg.id} -> AUDIT:{audit.id} ({audit.category.value})")
        lines.append("")

    if result.false_positives:
        lines.extend([
            "FALSE POSITIVES (VKG False Alarms)",
            "-" * 40,
        ])
        for vkg in result.false_positives[:10]:  # Limit to 10
            lines.append(f"  {vkg.id}: {vkg.pattern_id} @ {vkg.file}:{vkg.line}")
        if len(result.false_positives) > 10:
            lines.append(f"  ... and {len(result.false_positives) - 10} more")
        lines.append("")

    if result.false_negatives:
        lines.extend([
            "FALSE NEGATIVES (VKG Missed)",
            "-" * 40,
        ])
        for audit in result.false_negatives:
            lines.append(f"  {audit.id}: {audit.title} ({audit.category.value}, {audit.severity.value})")
        lines.append("")

    lines.append("=" * 70)

    return "\n".join(lines)


__all__ = [
    "VulnerabilityCategory",
    "Severity",
    "AuditFinding",
    "ProjectGroundTruth",
    "VKGFinding",
    "MatchResult",
    "ValidationResult",
    "FindingMatcher",
    "normalize_category",
    "is_category_match",
    "format_validation_report",
]
