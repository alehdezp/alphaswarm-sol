"""
Finding Data Model

Core data structures for security findings.
Designed for AI agent workflows and session handoff.

Philosophy: "Every finding includes behavioral evidence"
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class FindingStatus(str, Enum):
    """Status of a finding in the investigation workflow."""

    PENDING = "pending"          # Not yet investigated
    INVESTIGATING = "investigating"  # Currently being analyzed
    CONFIRMED = "confirmed"      # Verified as vulnerability
    FALSE_POSITIVE = "false_positive"  # Verified as not a vulnerability
    ESCALATED = "escalated"      # Needs human review
    FIXED = "fixed"              # Issue has been fixed


class FindingSeverity(str, Enum):
    """Severity level of a finding."""

    CRITICAL = "critical"  # Immediate fund loss risk
    HIGH = "high"          # Significant security issue
    MEDIUM = "medium"      # Security concern
    LOW = "low"            # Best practice violation
    INFO = "info"          # Informational


class FindingConfidence(str, Enum):
    """Confidence level in the finding."""

    HIGH = "high"      # Strong behavioral evidence, low FP rate
    MEDIUM = "medium"  # Likely issue, needs verification
    LOW = "low"        # Possible issue, high FP rate


class FindingTier(str, Enum):
    """
    Detection tier for the finding.

    Tier A: Deterministic detection - same code always produces same findings
    Tier B: LLM-verified detection - requires model judgment
    """

    TIER_A = "tier_a"  # Deterministic (pattern-based)
    TIER_B = "tier_b"  # LLM-verified (needs model judgment)


# Schema version for output stability
FINDING_SCHEMA_VERSION = "1.0.0"


@dataclass
class Location:
    """Source code location of a finding."""

    file: str
    line: int
    column: int = 0
    end_line: Optional[int] = None
    end_column: Optional[int] = None
    function: Optional[str] = None
    contract: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "end_line": self.end_line,
            "end_column": self.end_column,
            "function": self.function,
            "contract": self.contract,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Location":
        """Create from dictionary."""
        return cls(
            file=data.get("file", ""),
            line=data.get("line", 0),
            column=data.get("column", 0),
            end_line=data.get("end_line"),
            end_column=data.get("end_column"),
            function=data.get("function"),
            contract=data.get("contract"),
        )

    def __str__(self) -> str:
        """Format as file:line:column (IDE-compatible)."""
        return f"{self.file}:{self.line}:{self.column}"

    def format_range(self) -> str:
        """Format as file:line:column-end_line:end_column for ranges."""
        base = f"{self.file}:{self.line}:{self.column}"
        if self.end_line is not None:
            end_col = self.end_column if self.end_column is not None else 0
            base += f"-{self.end_line}:{end_col}"
        return base

    def format_compact(self) -> str:
        """Format as file:line (compact, no column)."""
        return f"{self.file}:{self.line}"

    def is_valid(self) -> bool:
        """Check if location has minimum required data."""
        return bool(self.file) and self.line > 0


@dataclass
class EvidenceRef:
    """
    Reference to code evidence (Task 3.14).

    Captures a specific code location with context.
    """

    type: str  # "code", "property", "operation", "call_graph"
    ref: str  # e.g., "Vault.sol:45-52" or property name
    value: Any = None  # property value or code snippet
    context: str = ""  # additional context

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type,
            "ref": self.ref,
            "value": self.value,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceRef":
        """Create from dictionary."""
        return cls(
            type=data.get("type", ""),
            ref=data.get("ref", ""),
            value=data.get("value"),
            context=data.get("context", ""),
        )


@dataclass
class Evidence:
    """
    Evidence supporting a finding (Task 3.14: Evidence-First Output).

    Philosophy: Every finding includes behavioral evidence that explains
    WHY it's vulnerable, not just WHAT was detected.

    Example:
        >>> evidence = Evidence(
        ...     behavioral_signature="R:bal→X:out→W:bal",
        ...     why_vulnerable="External call transfers ETH before balance update",
        ...     attack_scenario=[
        ...         "1. Attacker deposits funds",
        ...         "2. Attacker calls withdraw()",
        ...         "3. In receive(), attacker re-enters withdraw()",
        ...         "4. Balance not yet decremented, full amount withdrawn again"
        ...     ],
        ... )
    """

    behavioral_signature: str = ""  # e.g., "R:bal→X:out→W:bal"
    properties_matched: list[str] = field(default_factory=list)
    properties_missing: list[str] = field(default_factory=list)
    code_snippet: str = ""
    operations: list[str] = field(default_factory=list)
    explanation: str = ""

    # Task 3.14: Evidence-First Output additions
    why_vulnerable: str = ""  # Plain English explanation
    attack_scenario: list[str] = field(default_factory=list)  # Minimal repro steps
    evidence_refs: list[EvidenceRef] = field(default_factory=list)  # Detailed refs
    data_flow: list[str] = field(default_factory=list)  # Taint flow path
    guard_analysis: str = ""  # What guards were checked/missing

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "behavioral_signature": self.behavioral_signature,
            "properties_matched": self.properties_matched,
            "properties_missing": self.properties_missing,
            "code_snippet": self.code_snippet,
            "operations": self.operations,
            "explanation": self.explanation,
            # Task 3.14 additions
            "why_vulnerable": self.why_vulnerable,
            "attack_scenario": self.attack_scenario,
            "evidence_refs": [ref.to_dict() for ref in self.evidence_refs],
            "data_flow": self.data_flow,
            "guard_analysis": self.guard_analysis,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Evidence":
        """Create from dictionary."""
        return cls(
            behavioral_signature=data.get("behavioral_signature", ""),
            properties_matched=data.get("properties_matched", []),
            properties_missing=data.get("properties_missing", []),
            code_snippet=data.get("code_snippet", ""),
            operations=data.get("operations", []),
            explanation=data.get("explanation", ""),
            # Task 3.14 additions
            why_vulnerable=data.get("why_vulnerable", ""),
            attack_scenario=data.get("attack_scenario", []),
            evidence_refs=[
                EvidenceRef.from_dict(ref)
                for ref in data.get("evidence_refs", [])
            ],
            data_flow=data.get("data_flow", []),
            guard_analysis=data.get("guard_analysis", ""),
        )

    def has_behavioral_evidence(self) -> bool:
        """Check if evidence includes behavioral data (Task 3.14 requirement)."""
        return bool(self.behavioral_signature or self.operations)

    def has_attack_context(self) -> bool:
        """Check if evidence includes attack context (Task 3.14 requirement)."""
        return bool(self.why_vulnerable or self.attack_scenario)

    def is_complete(self) -> bool:
        """Check if evidence meets Task 3.14 completeness requirements."""
        return (
            self.has_behavioral_evidence()
            and self.has_attack_context()
            and bool(self.code_snippet or self.evidence_refs)
        )

    def format_summary(self) -> str:
        """Format a short evidence summary."""
        parts = []
        if self.behavioral_signature:
            parts.append(f"Signature: {self.behavioral_signature}")
        if self.why_vulnerable:
            parts.append(f"Why: {self.why_vulnerable}")
        if self.properties_matched:
            parts.append(f"Properties: {', '.join(self.properties_matched[:3])}")
        return " | ".join(parts) if parts else "No evidence details"


@dataclass
class Finding:
    """
    A security finding from VKG analysis.

    Example:
        >>> finding = Finding(
        ...     pattern="auth-001",
        ...     severity=FindingSeverity.HIGH,
        ...     confidence=FindingConfidence.HIGH,
        ...     location=Location(file="Vault.sol", line=42, function="withdraw"),
        ...     description="Public function writes privileged state without access control",
        ... )
        >>> print(finding.id)
        VKG-A1B2C3D4
    """

    pattern: str
    severity: FindingSeverity
    confidence: FindingConfidence
    location: Location
    description: str

    # Optional fields
    id: str = ""
    title: str = ""
    tier: FindingTier = FindingTier.TIER_A  # Default to deterministic detection
    evidence: Evidence = field(default_factory=Evidence)
    verification_steps: list[str] = field(default_factory=list)
    recommended_fix: str = ""
    references: list[str] = field(default_factory=list)

    # Status tracking
    status: FindingStatus = FindingStatus.PENDING
    status_reason: str = ""
    investigator_notes: str = ""

    # Timestamps
    created_at: str = ""
    updated_at: str = ""

    # Linking
    related_findings: list[str] = field(default_factory=list)
    cwe: str = ""
    swc: str = ""

    def __post_init__(self) -> None:
        """Initialize computed fields."""
        if not self.id:
            self.id = self._generate_id()
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at
        if not self.title:
            self.title = self._generate_title()

    def _generate_id(self) -> str:
        """Generate unique finding ID."""
        data = f"{self.pattern}:{self.location.file}:{self.location.line}:{self.description[:50]}"
        hash_suffix = hashlib.sha256(data.encode()).hexdigest()[:8].upper()
        return f"VKG-{hash_suffix}"

    def _generate_title(self) -> str:
        """Generate title from pattern and location."""
        pattern_title = self.pattern.replace("-", " ").title()
        if self.location.function:
            return f"{pattern_title} in {self.location.function}"
        return pattern_title

    def update_status(
        self,
        status: FindingStatus,
        reason: str = "",
        notes: str = "",
    ) -> None:
        """Update finding status."""
        self.status = status
        if reason:
            self.status_reason = reason
        if notes:
            self.investigator_notes = notes
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "schema_version": FINDING_SCHEMA_VERSION,
            "id": self.id,
            "pattern": self.pattern,
            "tier": self.tier.value,
            "severity": self.severity.value,
            "confidence": self.confidence.value,
            "location": self.location.to_dict(),
            "description": self.description,
            "title": self.title,
            "evidence": self.evidence.to_dict(),
            "verification_steps": self.verification_steps,
            "recommended_fix": self.recommended_fix,
            "references": self.references,
            "status": self.status.value,
            "status_reason": self.status_reason,
            "investigator_notes": self.investigator_notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "related_findings": self.related_findings,
            "cwe": self.cwe,
            "swc": self.swc,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Finding":
        """Create Finding from dictionary."""
        # Parse tier with fallback
        tier_value = data.get("tier", "tier_a")
        tier = FindingTier(tier_value) if tier_value else FindingTier.TIER_A

        return cls(
            id=data.get("id", ""),
            pattern=data.get("pattern", ""),
            severity=FindingSeverity(data.get("severity", "medium")),
            confidence=FindingConfidence(data.get("confidence", "medium")),
            location=Location.from_dict(data.get("location", {})),
            description=data.get("description", ""),
            title=data.get("title", ""),
            tier=tier,
            evidence=Evidence.from_dict(data.get("evidence", {})),
            verification_steps=data.get("verification_steps", []),
            recommended_fix=data.get("recommended_fix", ""),
            references=data.get("references", []),
            status=FindingStatus(data.get("status", "pending")),
            status_reason=data.get("status_reason", ""),
            investigator_notes=data.get("investigator_notes", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            related_findings=data.get("related_findings", []),
            cwe=data.get("cwe", ""),
            swc=data.get("swc", ""),
        )

    @property
    def priority_score(self) -> int:
        """
        Calculate priority score for ordering.

        Higher score = higher priority.
        Based on severity, confidence, and status.
        """
        severity_scores = {
            FindingSeverity.CRITICAL: 100,
            FindingSeverity.HIGH: 80,
            FindingSeverity.MEDIUM: 50,
            FindingSeverity.LOW: 20,
            FindingSeverity.INFO: 5,
        }
        confidence_scores = {
            FindingConfidence.HIGH: 1.0,
            FindingConfidence.MEDIUM: 0.7,
            FindingConfidence.LOW: 0.4,
        }
        status_penalties = {
            FindingStatus.PENDING: 0,
            FindingStatus.INVESTIGATING: -10,
            FindingStatus.CONFIRMED: -100,
            FindingStatus.FALSE_POSITIVE: -200,
            FindingStatus.ESCALATED: 50,  # Boost escalated
            FindingStatus.FIXED: -200,
        }

        base = severity_scores.get(self.severity, 50)
        confidence_mult = confidence_scores.get(self.confidence, 0.7)
        status_adj = status_penalties.get(self.status, 0)

        return int(base * confidence_mult + status_adj)

    def format_summary(self) -> str:
        """Format a short summary for CLI output."""
        status_emoji = {
            FindingStatus.PENDING: "⏳",
            FindingStatus.INVESTIGATING: "🔍",
            FindingStatus.CONFIRMED: "✅",
            FindingStatus.FALSE_POSITIVE: "❌",
            FindingStatus.ESCALATED: "🚨",
            FindingStatus.FIXED: "🔧",
        }
        emoji = status_emoji.get(self.status, "•")
        return f"{emoji} [{self.id}] {self.severity.value.upper()} - {self.title} @ {self.location}"

    def format_detail(self) -> str:
        """Format detailed output for investigation."""
        lines = [
            f"Finding: {self.id}",
            "=" * 60,
            f"Pattern: {self.pattern}",
            f"Severity: {self.severity.value.upper()}",
            f"Confidence: {self.confidence.value}",
            f"Status: {self.status.value}",
            f"Location: {self.location}",
            "",
            "Description:",
            self.description,
            "",
        ]

        if self.evidence.behavioral_signature:
            lines.append(f"Behavioral Signature: {self.evidence.behavioral_signature}")

        if self.evidence.properties_matched:
            lines.append(f"Properties Matched: {', '.join(self.evidence.properties_matched)}")

        if self.evidence.code_snippet:
            lines.append("")
            lines.append("Code:")
            lines.append("```solidity")
            lines.append(self.evidence.code_snippet)
            lines.append("```")

        if self.verification_steps:
            lines.append("")
            lines.append("Verification Steps:")
            for i, step in enumerate(self.verification_steps, 1):
                lines.append(f"  {i}. {step}")

        if self.recommended_fix:
            lines.append("")
            lines.append("Recommended Fix:")
            lines.append(self.recommended_fix)

        return "\n".join(lines)
