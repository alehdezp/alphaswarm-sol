"""
Findings Store

Persistent storage for findings that survives session restarts.
Enables session handoff between AI agents.

Philosophy: "Persistent state enables seamless session handoff"
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

from alphaswarm_sol.findings.model import (
    Finding,
    FindingConfidence,
    FindingSeverity,
    FindingStatus,
)


class FindingsStore:
    """
    Persistent store for security findings.

    Stores findings in `.vrs/findings.json` for session persistence.

    Example:
        >>> store = FindingsStore(Path(".vrs"))
        >>> store.add(finding)
        >>> store.save()
        >>> # Later session
        >>> store = FindingsStore(Path(".vrs"))
        >>> next_finding = store.get_next()
    """

    def __init__(self, vkg_dir: Path) -> None:
        """
        Initialize findings store.

        Args:
            vkg_dir: Path to .vkg directory
        """
        self.vkg_dir = vkg_dir
        self.findings_file = vkg_dir / "findings.json"
        self._findings: dict[str, Finding] = {}
        self._load()

    def _load(self) -> None:
        """Load findings from disk."""
        if self.findings_file.exists():
            try:
                data = json.loads(self.findings_file.read_text())
                for finding_data in data.get("findings", []):
                    finding = Finding.from_dict(finding_data)
                    self._findings[finding.id] = finding
            except (json.JSONDecodeError, KeyError):
                # Corrupted file, start fresh
                self._findings = {}

    def save(self) -> None:
        """Save findings to disk."""
        self.vkg_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "version": "1.0.0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "count": len(self._findings),
            "findings": [f.to_dict() for f in self._findings.values()],
        }
        self.findings_file.write_text(json.dumps(data, indent=2))

    def add(self, finding: Finding) -> str:
        """
        Add a finding to the store.

        Args:
            finding: Finding to add

        Returns:
            ID of the added finding
        """
        self._findings[finding.id] = finding
        return finding.id

    def get(self, finding_id: str) -> Optional[Finding]:
        """
        Get a finding by ID.

        Args:
            finding_id: Finding ID

        Returns:
            Finding if found, None otherwise
        """
        return self._findings.get(finding_id)

    def update(
        self,
        finding_id: str,
        status: Optional[FindingStatus] = None,
        reason: str = "",
        notes: str = "",
    ) -> bool:
        """
        Update a finding's status.

        Args:
            finding_id: Finding ID
            status: New status
            reason: Reason for status change
            notes: Investigator notes

        Returns:
            True if updated, False if not found
        """
        finding = self._findings.get(finding_id)
        if not finding:
            return False

        if status:
            finding.update_status(status, reason, notes)
        return True

    def delete(self, finding_id: str) -> bool:
        """
        Delete a finding.

        Args:
            finding_id: Finding ID

        Returns:
            True if deleted, False if not found
        """
        if finding_id in self._findings:
            del self._findings[finding_id]
            return True
        return False

    def clear(self) -> None:
        """Clear all findings."""
        self._findings.clear()

    def get_next(self) -> Optional[Finding]:
        """
        Get the next finding to investigate.

        Returns highest priority pending finding.
        """
        pending = [
            f for f in self._findings.values()
            if f.status in (FindingStatus.PENDING, FindingStatus.ESCALATED)
        ]
        if not pending:
            return None

        # Sort by priority score (descending)
        pending.sort(key=lambda f: f.priority_score, reverse=True)
        return pending[0]

    def list(
        self,
        status: Optional[FindingStatus] = None,
        severity: Optional[FindingSeverity] = None,
        pattern: Optional[str] = None,
        limit: int = 100,
    ) -> list[Finding]:
        """
        List findings with optional filters.

        Args:
            status: Filter by status
            severity: Filter by severity
            pattern: Filter by pattern ID
            limit: Maximum number of findings

        Returns:
            List of matching findings
        """
        results = list(self._findings.values())

        if status:
            results = [f for f in results if f.status == status]
        if severity:
            results = [f for f in results if f.severity == severity]
        if pattern:
            results = [f for f in results if f.pattern == pattern]

        # Sort by priority
        results.sort(key=lambda f: f.priority_score, reverse=True)

        return results[:limit]

    def count(self, status: Optional[FindingStatus] = None) -> int:
        """
        Count findings.

        Args:
            status: Optional status filter

        Returns:
            Number of findings
        """
        if status:
            return sum(1 for f in self._findings.values() if f.status == status)
        return len(self._findings)

    def stats(self) -> dict[str, int]:
        """
        Get statistics about findings.

        Returns:
            Dict with counts by status and severity
        """
        stats = {
            "total": len(self._findings),
            "by_status": {},
            "by_severity": {},
        }

        for status in FindingStatus:
            count = self.count(status)
            if count > 0:
                stats["by_status"][status.value] = count

        for severity in FindingSeverity:
            count = sum(
                1 for f in self._findings.values()
                if f.severity == severity
            )
            if count > 0:
                stats["by_severity"][severity.value] = count

        return stats

    def __len__(self) -> int:
        """Return number of findings."""
        return len(self._findings)

    def __iter__(self) -> Iterator[Finding]:
        """Iterate over findings."""
        return iter(self._findings.values())

    def __contains__(self, finding_id: str) -> bool:
        """Check if finding exists."""
        return finding_id in self._findings

    def to_json(self, indent: int = 2) -> str:
        """Export all findings to JSON."""
        data = {
            "version": "1.0.0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "count": len(self._findings),
            "findings": [f.to_dict() for f in self._findings.values()],
        }
        return json.dumps(data, indent=indent)

    @classmethod
    def from_analysis(
        cls,
        vkg_dir: Path,
        pattern_matches: list[dict],
    ) -> "FindingsStore":
        """
        Create store from pattern analysis results.

        Args:
            vkg_dir: Path to .vkg directory
            pattern_matches: List of pattern match dictionaries

        Returns:
            FindingsStore with findings from analysis
        """
        store = cls(vkg_dir)

        for match in pattern_matches:
            from alphaswarm_sol.findings.model import Evidence, Location

            finding = Finding(
                pattern=match.get("pattern_id", ""),
                severity=FindingSeverity(match.get("severity", "medium")),
                confidence=FindingConfidence(match.get("confidence", "medium")),
                location=Location(
                    file=match.get("file", ""),
                    line=match.get("line", 0),
                    function=match.get("function", ""),
                    contract=match.get("contract", ""),
                ),
                description=match.get("description", ""),
                evidence=Evidence(
                    behavioral_signature=match.get("behavioral_signature", ""),
                    properties_matched=match.get("properties_matched", []),
                    code_snippet=match.get("code_snippet", ""),
                ),
                verification_steps=match.get("verification_steps", []),
                recommended_fix=match.get("recommended_fix", ""),
            )
            store.add(finding)

        return store
