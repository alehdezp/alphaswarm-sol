"""Bead triage and prioritization.

This module prioritizes beads for efficient multi-agent verification,
identifying high-value targets and related beads for cascade processing.

Key features:
- Prioritizes by severity and cross-tool agreement
- Identifies related beads for cascade dismissals
- Recommends initial verification agent
- Filters known false positive patterns

Model tier: sonnet-4.5 (triage decisions require reasoning about severity, context)

Usage:
    from alphaswarm_sol.beads.triage import BeadTriager, TriagePriority

    triager = BeadTriager()
    results = triager.triage_beads(beads)

    for result in results:
        if result.priority == TriagePriority.CRITICAL:
            # Verify immediately
            pass
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from .schema import VulnerabilityBead
from .types import Severity


class TriagePriority(str, Enum):
    """Priority levels for bead verification.

    Determines order and urgency of multi-agent verification.

    Levels:
        CRITICAL: Verify immediately - potential high-impact vulnerability
        HIGH: High priority queue - significant issues
        MEDIUM: Standard queue - typical findings
        LOW: Background verification - lower severity or confidence
        SKIP: Known false positive pattern - skip verification
    """

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SKIP = "skip"


@dataclass
class TriageResult:
    """Result of bead triage analysis.

    Contains priority, related beads, and verification recommendations.

    Attributes:
        bead_id: ID of the triaged bead
        priority: Calculated verification priority
        reasoning: Explanation of priority calculation
        related_beads: IDs of beads that may have cascading verdicts
        cascade_potential: Likelihood (0-1) that verdict affects related beads
        recommended_agent: Suggested first agent (attacker/defender/verifier)
        metadata: Additional triage information
    """

    bead_id: str
    priority: TriagePriority
    reasoning: str
    related_beads: List[str] = field(default_factory=list)
    cascade_potential: float = 0.0
    recommended_agent: str = "verifier"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "bead_id": self.bead_id,
            "priority": self.priority.value,
            "reasoning": self.reasoning,
            "related_beads": self.related_beads,
            "cascade_potential": self.cascade_potential,
            "recommended_agent": self.recommended_agent,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TriageResult":
        """Create TriageResult from dictionary."""
        return cls(
            bead_id=data.get("bead_id", ""),
            priority=TriagePriority(data.get("priority", "medium")),
            reasoning=data.get("reasoning", ""),
            related_beads=data.get("related_beads", []),
            cascade_potential=data.get("cascade_potential", 0.0),
            recommended_agent=data.get("recommended_agent", "verifier"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class TriageBatch:
    """Batch of triaged beads for processing.

    Groups beads by priority for efficient batch verification.

    Attributes:
        critical: Beads requiring immediate verification
        high: High priority beads
        medium: Standard priority beads
        low: Low priority beads
        skip: Beads to skip (likely false positives)
    """

    critical: List[TriageResult] = field(default_factory=list)
    high: List[TriageResult] = field(default_factory=list)
    medium: List[TriageResult] = field(default_factory=list)
    low: List[TriageResult] = field(default_factory=list)
    skip: List[TriageResult] = field(default_factory=list)

    @property
    def total_count(self) -> int:
        """Total number of triaged beads."""
        return len(self.critical) + len(self.high) + len(self.medium) + len(self.low) + len(self.skip)

    @property
    def actionable_count(self) -> int:
        """Number of beads requiring verification (excludes SKIP)."""
        return len(self.critical) + len(self.high) + len(self.medium) + len(self.low)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "critical": [r.to_dict() for r in self.critical],
            "high": [r.to_dict() for r in self.high],
            "medium": [r.to_dict() for r in self.medium],
            "low": [r.to_dict() for r in self.low],
            "skip": [r.to_dict() for r in self.skip],
            "total_count": self.total_count,
            "actionable_count": self.actionable_count,
        }


class BeadTriager:
    """Prioritize beads for efficient multi-agent verification.

    Analyzes beads to determine verification priority based on:
    - Severity (critical > high > medium > low)
    - Cross-tool agreement (multiple tools = higher priority)
    - Related bead clusters (cascade potential)
    - Known false positive patterns

    Model tier: sonnet-4.5 (triage decisions require reasoning)

    Example:
        triager = BeadTriager()
        results = triager.triage_beads(beads)

        # Process in priority order
        for result in results:
            agent = get_agent(result.recommended_agent)
            verdict = agent.verify(bead_map[result.bead_id])
    """

    MODEL_TIER = "sonnet-4.5"

    # Known false positive patterns by tool (detector patterns to skip)
    # Based on common false positive experience
    FALSE_POSITIVE_PATTERNS: Dict[str, List[str]] = {
        "slither": [
            "naming-convention",
            "solc-version",
            "pragma",
            "similar-names",
            "too-many-digits",
            "constable-states",
            "immutable-states",
        ],
        "semgrep": [
            "informational-*",
            "erc20-*-not-enforced",
        ],
        "aderyn": [
            "state-variable-could-be-constant",
            "missing-zero-address-check",
        ],
        "mythril": [
            "Integer Overflow",  # Often false positive in ^0.8.0
        ],
    }

    # Vulnerability categories that should always start with attacker agent
    ATTACKER_FIRST_CATEGORIES: Set[str] = {
        "reentrancy",
        "flash_loan",
        "price_manipulation",
    }

    # Vulnerability categories that should start with defender agent
    DEFENDER_FIRST_CATEGORIES: Set[str] = {
        "access_control",
        "authorization",
        "privilege_escalation",
    }

    def __init__(
        self,
        custom_fp_patterns: Optional[Dict[str, List[str]]] = None,
    ):
        """Initialize triager.

        Args:
            custom_fp_patterns: Additional false positive patterns to skip
        """
        self._fp_patterns = self.FALSE_POSITIVE_PATTERNS.copy()
        if custom_fp_patterns:
            for tool, patterns in custom_fp_patterns.items():
                existing = self._fp_patterns.get(tool, [])
                self._fp_patterns[tool] = existing + patterns

    def triage_beads(
        self,
        beads: List[VulnerabilityBead],
    ) -> List[TriageResult]:
        """Prioritize and relate beads for verification.

        Analyzes all beads to determine:
        - Verification priority (critical/high/medium/low/skip)
        - Related beads for cascade processing
        - Recommended first verification agent

        Args:
            beads: List of beads to triage

        Returns:
            List of TriageResult sorted by priority (critical first)
        """
        results: List[TriageResult] = []

        # Build relationship graph
        relationships = self._find_relationships(beads)

        # Create bead index for efficient lookup
        bead_index = {bead.id: bead for bead in beads}

        for bead in beads:
            priority = self._calculate_priority(bead)
            related = relationships.get(bead.id, [])
            cascade = self._calculate_cascade_potential(bead, related, bead_index)
            agent = self._recommend_agent(bead)
            reasoning = self._explain_priority(bead, priority, related)

            results.append(TriageResult(
                bead_id=bead.id,
                priority=priority,
                reasoning=reasoning,
                related_beads=related,
                cascade_potential=cascade,
                recommended_agent=agent,
                metadata={
                    "severity": bead.severity.value,
                    "vulnerability_class": bead.vulnerability_class,
                    "tool_sources": bead.metadata.get("tool_sources", []),
                },
            ))

        # Sort by priority (critical first)
        priority_order = {
            TriagePriority.CRITICAL: 0,
            TriagePriority.HIGH: 1,
            TriagePriority.MEDIUM: 2,
            TriagePriority.LOW: 3,
            TriagePriority.SKIP: 4,
        }
        results.sort(key=lambda r: (priority_order[r.priority], -r.cascade_potential))

        return results

    def triage_to_batch(
        self,
        beads: List[VulnerabilityBead],
    ) -> TriageBatch:
        """Triage beads and group by priority.

        Convenience method that returns beads grouped by priority level.

        Args:
            beads: List of beads to triage

        Returns:
            TriageBatch with beads grouped by priority
        """
        results = self.triage_beads(beads)
        batch = TriageBatch()

        for result in results:
            if result.priority == TriagePriority.CRITICAL:
                batch.critical.append(result)
            elif result.priority == TriagePriority.HIGH:
                batch.high.append(result)
            elif result.priority == TriagePriority.MEDIUM:
                batch.medium.append(result)
            elif result.priority == TriagePriority.LOW:
                batch.low.append(result)
            else:  # SKIP
                batch.skip.append(result)

        return batch

    def _calculate_priority(self, bead: VulnerabilityBead) -> TriagePriority:
        """Calculate priority based on multiple factors.

        Priority is determined by:
        1. Known false positive patterns (-> SKIP)
        2. Severity (base priority)
        3. Cross-tool agreement (priority boost)
        4. Confidence level (priority adjustment)

        Args:
            bead: Bead to calculate priority for

        Returns:
            Calculated TriagePriority
        """
        # Check for skip patterns first
        if self._is_likely_false_positive(bead):
            return TriagePriority.SKIP

        # Severity-based initial priority
        severity_map = {
            Severity.CRITICAL: TriagePriority.CRITICAL,
            Severity.HIGH: TriagePriority.HIGH,
            Severity.MEDIUM: TriagePriority.MEDIUM,
            Severity.LOW: TriagePriority.LOW,
            Severity.INFO: TriagePriority.LOW,
        }
        base_priority = severity_map.get(bead.severity, TriagePriority.MEDIUM)

        # Boost priority if multiple tools agree
        tool_sources = bead.metadata.get("tool_sources", [])
        if len(tool_sources) >= 3:
            # Strong agreement: boost priority
            base_priority = self._boost_priority(base_priority)
        elif len(tool_sources) >= 2:
            # Moderate agreement: boost medium to high
            if base_priority == TriagePriority.MEDIUM:
                base_priority = TriagePriority.HIGH

        # Demote if very low confidence
        if bead.confidence < 0.2:
            base_priority = self._demote_priority(base_priority)

        return base_priority

    def _boost_priority(self, priority: TriagePriority) -> TriagePriority:
        """Boost priority one level.

        Args:
            priority: Current priority

        Returns:
            Boosted priority (capped at CRITICAL)
        """
        boost_map = {
            TriagePriority.LOW: TriagePriority.MEDIUM,
            TriagePriority.MEDIUM: TriagePriority.HIGH,
            TriagePriority.HIGH: TriagePriority.CRITICAL,
            TriagePriority.CRITICAL: TriagePriority.CRITICAL,
            TriagePriority.SKIP: TriagePriority.LOW,
        }
        return boost_map.get(priority, priority)

    def _demote_priority(self, priority: TriagePriority) -> TriagePriority:
        """Demote priority one level.

        Args:
            priority: Current priority

        Returns:
            Demoted priority (capped at LOW)
        """
        demote_map = {
            TriagePriority.CRITICAL: TriagePriority.HIGH,
            TriagePriority.HIGH: TriagePriority.MEDIUM,
            TriagePriority.MEDIUM: TriagePriority.LOW,
            TriagePriority.LOW: TriagePriority.LOW,
            TriagePriority.SKIP: TriagePriority.SKIP,
        }
        return demote_map.get(priority, priority)

    def _is_likely_false_positive(self, bead: VulnerabilityBead) -> bool:
        """Check if bead matches known false positive patterns.

        Args:
            bead: Bead to check

        Returns:
            True if likely false positive
        """
        # Check tool-specific FP patterns
        tool_sources = bead.metadata.get("tool_sources", [])
        detector_ids = bead.metadata.get("detector_ids", [bead.pattern_id])

        for tool in tool_sources:
            patterns = self._fp_patterns.get(tool, [])
            for pattern in patterns:
                for detector in detector_ids:
                    # Support wildcard matching
                    if fnmatch.fnmatch(detector.lower(), pattern.lower()):
                        return True

        return False

    def _find_relationships(
        self,
        beads: List[VulnerabilityBead],
    ) -> Dict[str, List[str]]:
        """Find related beads by file, function, or vulnerability class.

        Related beads may have cascading verdicts:
        - Same file: Changes in one finding may affect others
        - Same function: Multiple issues in one function
        - Same vulnerability class: Pattern applies across codebase

        Args:
            beads: List of beads to analyze

        Returns:
            Dictionary mapping bead ID to related bead IDs
        """
        relationships: Dict[str, List[str]] = {}

        for bead in beads:
            related: List[str] = []

            for other in beads:
                if other.id == bead.id:
                    continue

                # Same file (highest cascade potential)
                if (bead.vulnerable_code.file_path and
                    bead.vulnerable_code.file_path == other.vulnerable_code.file_path):
                    related.append(other.id)
                    continue

                # Same function (high cascade potential)
                if (bead.function_id and
                    bead.function_id == other.function_id):
                    related.append(other.id)
                    continue

                # Same vulnerability class (moderate cascade potential)
                if bead.vulnerability_class == other.vulnerability_class:
                    related.append(other.id)

            relationships[bead.id] = related

        return relationships

    def _calculate_cascade_potential(
        self,
        bead: VulnerabilityBead,
        related_ids: List[str],
        bead_index: Dict[str, VulnerabilityBead],
    ) -> float:
        """Calculate likelihood that verdict affects related beads.

        Higher cascade potential means resolving this bead may help
        resolve related beads more efficiently.

        Args:
            bead: Bead being analyzed
            related_ids: IDs of related beads
            bead_index: Index of all beads by ID

        Returns:
            Cascade potential score (0.0-1.0)
        """
        if not related_ids:
            return 0.0

        # Factors that increase cascade potential
        cascade_score = 0.0

        for related_id in related_ids:
            related = bead_index.get(related_id)
            if not related:
                continue

            # Same file: high cascade
            if (bead.vulnerable_code.file_path and
                bead.vulnerable_code.file_path == related.vulnerable_code.file_path):
                cascade_score += 0.4

            # Same function: very high cascade
            elif bead.function_id and bead.function_id == related.function_id:
                cascade_score += 0.5

            # Same vulnerability class: moderate cascade
            elif bead.vulnerability_class == related.vulnerability_class:
                cascade_score += 0.2

        # Normalize to 0-1 range
        return min(1.0, cascade_score / max(1, len(related_ids)))

    def _recommend_agent(self, bead: VulnerabilityBead) -> str:
        """Recommend which agent should verify first.

        Different vulnerability types benefit from different
        starting agents:
        - Attacker: For exploitability-focused investigation
        - Defender: For guard/mitigation verification
        - Verifier: For balanced analysis

        Args:
            bead: Bead to recommend agent for

        Returns:
            Agent name: "attacker", "defender", or "verifier"
        """
        category = bead.vulnerability_class.lower()

        # High severity: attacker first to prove exploitability
        if bead.severity in [Severity.CRITICAL, Severity.HIGH]:
            return "attacker"

        # Category-specific recommendations
        if category in self.ATTACKER_FIRST_CATEGORIES:
            return "attacker"

        if category in self.DEFENDER_FIRST_CATEGORIES:
            return "defender"

        # Default: verifier for balanced analysis
        return "verifier"

    def _explain_priority(
        self,
        bead: VulnerabilityBead,
        priority: TriagePriority,
        related: List[str],
    ) -> str:
        """Generate human-readable priority explanation.

        Args:
            bead: Bead being explained
            priority: Calculated priority
            related: Related bead IDs

        Returns:
            Explanation string
        """
        parts = []

        # Severity factor
        parts.append(f"Severity: {bead.severity.value}")

        # Tool agreement factor
        tool_sources = bead.metadata.get("tool_sources", [])
        if len(tool_sources) > 1:
            parts.append(f"Tools agreeing: {len(tool_sources)} ({', '.join(tool_sources)})")

        # Skip reason if applicable
        if priority == TriagePriority.SKIP:
            parts.append("Matches known false positive pattern")

        # Related beads
        if related:
            parts.append(f"Related beads: {len(related)}")

        # Confidence
        parts.append(f"Confidence: {bead.confidence:.0%}")

        return " | ".join(parts)


def triage_beads(beads: List[VulnerabilityBead]) -> List[TriageResult]:
    """Convenience function for bead triage.

    Creates a triager and processes beads.

    Args:
        beads: List of beads to triage

    Returns:
        List of TriageResult sorted by priority
    """
    triager = BeadTriager()
    return triager.triage_beads(beads)


__all__ = [
    "TriagePriority",
    "TriageResult",
    "TriageBatch",
    "BeadTriager",
    "triage_beads",
]
