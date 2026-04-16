"""False positive recording and warning system.

Task 7.4: Track false positive patterns and surface warnings when similar
findings are encountered, preventing repeated investigation of known FP cases.

Key concepts:
- FPPattern: A recorded pattern of false positives
- Similarity matching: Based on pattern_id + modifier_signature + guard patterns
- Warning levels: Based on occurrence count (2+ = possible, 5+ = likely)
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Set

from alphaswarm_sol.learning.types import SimilarityKey, SimilarityTier


class FindingLike(Protocol):
    """Protocol for objects that look like findings."""

    pattern_id: str


@dataclass
class FPPattern:
    """A false positive pattern identified from rejections.

    Tracks when specific combinations of pattern + modifiers + guards
    have been repeatedly marked as false positives.
    """

    pattern_id: str
    modifier_signature: str  # Sorted, joined modifiers that indicate FP
    guard_patterns: Set[str]  # Guard patterns that indicate FP
    occurrence_count: int = 0
    last_seen: datetime = field(default_factory=datetime.now)
    reasons: List[str] = field(default_factory=list)
    first_seen: datetime = field(default_factory=datetime.now)

    def matches(
        self,
        finding: Any,
        tier: SimilarityTier = SimilarityTier.STRUCTURAL,
    ) -> bool:
        """Check if a finding matches this FP pattern.

        Args:
            finding: Finding-like object with pattern_id and modifiers
            tier: Similarity tier for matching

        Returns:
            True if finding matches this FP pattern
        """
        # Must match pattern_id
        finding_pattern = getattr(finding, "pattern_id", None)
        if finding_pattern != self.pattern_id:
            return False

        # For pattern-only tier, just need pattern match
        if tier == SimilarityTier.PATTERN:
            return True

        # Check modifier overlap
        finding_mods = set(getattr(finding, "modifiers", []))
        pattern_mods = set(self.modifier_signature.split("|")) if self.modifier_signature else set()

        # Structural: modifiers must match
        if tier == SimilarityTier.STRUCTURAL:
            # FP pattern indicates these modifiers make it safe
            # If the finding has all the modifiers in the FP pattern, it matches
            if pattern_mods and pattern_mods.issubset(finding_mods):
                return True
            # Empty pattern mods with empty finding mods is also a match
            if not pattern_mods and not finding_mods:
                return True
            return False

        # Exact: need guard patterns too
        if tier == SimilarityTier.EXACT:
            if not pattern_mods.issubset(finding_mods):
                return False
            # Check guard patterns
            finding_guards = set(getattr(finding, "guard_patterns", []))
            if self.guard_patterns and not self.guard_patterns.issubset(finding_guards):
                return False
            return True

        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dict."""
        return {
            "pattern_id": self.pattern_id,
            "modifier_signature": self.modifier_signature,
            "guard_patterns": list(self.guard_patterns),
            "occurrence_count": self.occurrence_count,
            "last_seen": self.last_seen.isoformat(),
            "first_seen": self.first_seen.isoformat(),
            "reasons": self.reasons,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FPPattern":
        """Create from dict."""
        return cls(
            pattern_id=data["pattern_id"],
            modifier_signature=data.get("modifier_signature", ""),
            guard_patterns=set(data.get("guard_patterns", [])),
            occurrence_count=data.get("occurrence_count", 0),
            last_seen=datetime.fromisoformat(data["last_seen"]),
            first_seen=datetime.fromisoformat(data.get("first_seen", data["last_seen"])),
            reasons=data.get("reasons", []),
        )


@dataclass
class FPWarning:
    """A warning about potential false positive."""

    level: str  # "possible" or "likely"
    message: str
    occurrence_count: int
    reasons: List[str]
    pattern_id: str
    modifier_signature: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for serialization."""
        return {
            "level": self.level,
            "message": self.message,
            "occurrence_count": self.occurrence_count,
            "reasons": self.reasons,
            "pattern_id": self.pattern_id,
            "modifier_signature": self.modifier_signature,
        }


class FalsePositiveRecorder:
    """Track and warn about false positive patterns.

    Records false positives and generates warnings when similar findings
    are encountered, helping auditors avoid re-investigating known FPs.
    """

    # Minimum occurrences before generating warning
    MIN_OCCURRENCES_WARNING = 2

    # Strong warning threshold
    STRONG_WARNING_THRESHOLD = 5

    # Maximum reasons to store per pattern
    MAX_REASONS = 10

    def __init__(
        self,
        storage_path: Path,
        min_warning_threshold: int = 2,
        strong_warning_threshold: int = 5,
    ):
        """Initialize FP recorder.

        Args:
            storage_path: Directory for FP pattern storage
            min_warning_threshold: Minimum occurrences for "possible" warning
            strong_warning_threshold: Minimum occurrences for "likely" warning
        """
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.MIN_OCCURRENCES_WARNING = min_warning_threshold
        self.STRONG_WARNING_THRESHOLD = strong_warning_threshold
        self._fp_patterns: Dict[str, FPPattern] = {}
        self._load()

    def record(
        self,
        finding: Any,
        reason: str,
        guard_patterns: Optional[List[str]] = None,
    ) -> str:
        """Record a false positive.

        Args:
            finding: Finding-like object with pattern_id and modifiers
            reason: Why this was marked as FP
            guard_patterns: Optional guard patterns detected in the code

        Returns:
            Key for the FP pattern
        """
        key = self._make_key(finding)

        if key not in self._fp_patterns:
            self._fp_patterns[key] = FPPattern(
                pattern_id=getattr(finding, "pattern_id", "unknown"),
                modifier_signature=self._get_modifier_signature(finding),
                guard_patterns=set(guard_patterns or []),
                occurrence_count=0,
                first_seen=datetime.now(),
                last_seen=datetime.now(),
                reasons=[],
            )

        pattern = self._fp_patterns[key]
        pattern.occurrence_count += 1
        pattern.last_seen = datetime.now()

        # Update guard patterns
        if guard_patterns:
            pattern.guard_patterns.update(guard_patterns)

        # Add reason if not duplicate and under limit
        if reason and reason not in pattern.reasons:
            if len(pattern.reasons) < self.MAX_REASONS:
                pattern.reasons.append(reason)

        self._save()
        return key

    def get_warnings(
        self,
        finding: Any,
        tier: SimilarityTier = SimilarityTier.STRUCTURAL,
    ) -> List[FPWarning]:
        """Get FP warnings for a finding.

        Args:
            finding: Finding to check for warnings
            tier: Similarity tier for matching

        Returns:
            List of FPWarning objects
        """
        warnings = []

        for fp in self._fp_patterns.values():
            if not fp.matches(finding, tier):
                continue

            if fp.occurrence_count >= self.STRONG_WARNING_THRESHOLD:
                warnings.append(
                    FPWarning(
                        level="likely",
                        message=(
                            f"LIKELY FALSE POSITIVE: {fp.occurrence_count} similar "
                            f"findings were rejected. Common reasons: {', '.join(fp.reasons[:3])}"
                        ),
                        occurrence_count=fp.occurrence_count,
                        reasons=fp.reasons[:3],
                        pattern_id=fp.pattern_id,
                        modifier_signature=fp.modifier_signature,
                    )
                )
            elif fp.occurrence_count >= self.MIN_OCCURRENCES_WARNING:
                warnings.append(
                    FPWarning(
                        level="possible",
                        message=(
                            f"Possible FP: {fp.occurrence_count} similar rejections. "
                            f"Check: {fp.reasons[0] if fp.reasons else 'unknown'}"
                        ),
                        occurrence_count=fp.occurrence_count,
                        reasons=fp.reasons[:1],
                        pattern_id=fp.pattern_id,
                        modifier_signature=fp.modifier_signature,
                    )
                )

        return warnings

    def get_warning_strings(
        self,
        finding: Any,
        tier: SimilarityTier = SimilarityTier.STRUCTURAL,
    ) -> List[str]:
        """Get FP warning messages as strings.

        Convenience method for simple integration.
        """
        return [w.message for w in self.get_warnings(finding, tier)]

    def get_fp_count(self, pattern_id: str) -> int:
        """Get total FP count for a pattern.

        Args:
            pattern_id: Pattern to query

        Returns:
            Total number of FPs recorded
        """
        relevant = [fp for fp in self._fp_patterns.values()
                    if fp.pattern_id == pattern_id]
        return sum(fp.occurrence_count for fp in relevant)

    def get_fp_patterns_for(self, pattern_id: str) -> List[FPPattern]:
        """Get all FP patterns for a given pattern_id.

        Args:
            pattern_id: Pattern to query

        Returns:
            List of FPPattern objects
        """
        return [fp for fp in self._fp_patterns.values()
                if fp.pattern_id == pattern_id]

    def get_all_patterns(self) -> Dict[str, FPPattern]:
        """Get all recorded FP patterns.

        Returns:
            Dict mapping key to FPPattern
        """
        return self._fp_patterns.copy()

    def clear_pattern(self, pattern_id: str) -> int:
        """Clear all FP records for a pattern.

        Args:
            pattern_id: Pattern to clear

        Returns:
            Number of records cleared
        """
        keys_to_remove = [
            key for key, fp in self._fp_patterns.items()
            if fp.pattern_id == pattern_id
        ]
        for key in keys_to_remove:
            del self._fp_patterns[key]

        self._save()
        return len(keys_to_remove)

    def decay_old_patterns(self, max_age_days: int = 180) -> int:
        """Remove FP patterns older than max_age_days.

        Args:
            max_age_days: Maximum age for patterns to keep

        Returns:
            Number of patterns removed
        """
        cutoff = datetime.now() - timedelta(days=max_age_days)
        keys_to_remove = [
            key for key, fp in self._fp_patterns.items()
            if fp.last_seen < cutoff
        ]
        for key in keys_to_remove:
            del self._fp_patterns[key]

        if keys_to_remove:
            self._save()
        return len(keys_to_remove)

    def _make_key(self, finding: Any) -> str:
        """Make a unique key for FP pattern matching."""
        pattern_id = getattr(finding, "pattern_id", "unknown")
        mod_sig = self._get_modifier_signature(finding)
        return f"{pattern_id}:{mod_sig}"

    def _get_modifier_signature(self, finding: Any) -> str:
        """Get modifier signature for similarity matching."""
        modifiers = getattr(finding, "modifiers", [])
        # Sort for consistency
        return "|".join(sorted(modifiers))

    def _load(self) -> None:
        """Load FP patterns from storage."""
        fp_file = self.storage_path / "fp_patterns.json"
        if not fp_file.exists():
            return

        try:
            with open(fp_file, "r") as f:
                data = json.load(f)

            self._fp_patterns = {}
            for key, item in data.items():
                self._fp_patterns[key] = FPPattern.from_dict(item)
        except (json.JSONDecodeError, KeyError, ValueError):
            # Corrupted file - start fresh
            self._fp_patterns = {}

    def _save(self) -> None:
        """Save FP patterns to storage."""
        fp_file = self.storage_path / "fp_patterns.json"
        data = {key: fp.to_dict() for key, fp in self._fp_patterns.items()}

        with open(fp_file, "w") as f:
            json.dump(data, f, indent=2)

    def summary(self) -> str:
        """Generate summary of FP patterns.

        Returns:
            Markdown-formatted summary
        """
        if not self._fp_patterns:
            return "# False Positive Patterns\n\nNo FP patterns recorded yet."

        lines = ["# False Positive Patterns", ""]

        by_pattern: Dict[str, List[FPPattern]] = defaultdict(list)
        for fp in self._fp_patterns.values():
            by_pattern[fp.pattern_id].append(fp)

        for pattern_id, fps in sorted(by_pattern.items()):
            total = sum(fp.occurrence_count for fp in fps)
            lines.append(f"## {pattern_id}: {total} total FPs")
            for fp in sorted(fps, key=lambda x: -x.occurrence_count):
                mod_desc = fp.modifier_signature if fp.modifier_signature else "(no modifiers)"
                lines.append(f"  - {mod_desc}: {fp.occurrence_count} occurrences")
                for reason in fp.reasons[:2]:
                    lines.append(f"    - Reason: {reason}")
            lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Export all data as dict.

        Returns:
            Dict with all FP pattern data
        """
        return {
            "patterns": {key: fp.to_dict() for key, fp in self._fp_patterns.items()},
            "total_fps": sum(fp.occurrence_count for fp in self._fp_patterns.values()),
            "pattern_count": len(self._fp_patterns),
            "exported_at": datetime.now().isoformat(),
        }
