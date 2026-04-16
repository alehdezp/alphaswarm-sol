"""Output parser for Claude Code results.

Extracts structured data from Claude Code JSON output
and converts to TestMetrics for accuracy measurement.

Example:
    >>> from alphaswarm_sol.testing.harness import OutputParser
    >>> findings = OutputParser.parse_findings(result.structured_output)
    >>> accuracy = OutputParser.calculate_accuracy(findings, ground_truth)
    >>> print(f"Precision: {accuracy['precision']:.1%}")
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ParsedFinding:
    """A parsed vulnerability finding.

    Represents a single finding extracted from Claude Code output.

    Attributes:
        pattern: Vulnerability pattern identifier (e.g., "reentrancy-classic")
        severity: Severity level (critical, high, medium, low, info)
        location: Code location (e.g., "withdraw:45" or "Vault.sol:withdraw")
        confidence: Confidence score between 0 and 1
        reasoning: Optional reasoning explanation

    Example:
        >>> finding = ParsedFinding(
        ...     pattern="reentrancy-classic",
        ...     severity="critical",
        ...     location="withdraw:45",
        ...     confidence=0.92,
        ...     reasoning="External call before state update"
        ... )
    """

    pattern: str
    severity: str
    location: str
    confidence: float
    reasoning: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "pattern": self.pattern,
            "severity": self.severity,
            "location": self.location,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ParsedFinding":
        """Create from dictionary."""
        return cls(
            pattern=data.get("pattern", "unknown"),
            severity=data.get("severity", "medium"),
            location=data.get("location", "unknown"),
            confidence=data.get("confidence", 0.5),
            reasoning=data.get("reasoning"),
        )

    def matches_pattern(self, pattern: str) -> bool:
        """Check if finding matches a pattern (case-insensitive, partial match)."""
        return (
            pattern.lower() in self.pattern.lower()
            or self.pattern.lower() in pattern.lower()
        )

    def matches_severity(self, severity: str) -> bool:
        """Check if finding matches severity level."""
        return self.severity.lower() == severity.lower()


class OutputParser:
    """Parse Claude Code output into structured findings.

    Static methods for extracting findings and calculating accuracy
    against ground truth datasets.

    Example:
        >>> findings = OutputParser.parse_findings(structured_output)
        >>> accuracy = OutputParser.calculate_accuracy(findings, ground_truth)
        >>> print(f"F1: {accuracy['f1_score']:.1%}")
    """

    @staticmethod
    def parse_findings(structured_output: dict[str, Any] | None) -> list[ParsedFinding]:
        """Extract findings from structured output.

        Args:
            structured_output: The structured_output field from ClaudeCodeResult

        Returns:
            List of ParsedFinding objects

        Example:
            >>> output = {"findings": [{"pattern": "reentrancy", ...}]}
            >>> findings = OutputParser.parse_findings(output)
            >>> len(findings)
            1
        """
        if not structured_output:
            return []

        findings_data = structured_output.get("findings", [])
        if not isinstance(findings_data, list):
            return []

        return [
            ParsedFinding(
                pattern=f.get("pattern", "unknown"),
                severity=f.get("severity", "medium"),
                location=f.get("location", "unknown"),
                confidence=float(f.get("confidence", 0.5)),
                reasoning=f.get("reasoning"),
            )
            for f in findings_data
            if isinstance(f, dict)
        ]

    @staticmethod
    def calculate_accuracy(
        findings: list[ParsedFinding],
        ground_truth: list[dict[str, Any]],
        severity_weights: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Calculate precision, recall, F1 against ground truth.

        Matches findings to ground truth entries based on pattern
        and location similarity.

        Args:
            findings: Parsed findings from analysis
            ground_truth: Expected findings with pattern, severity, location
            severity_weights: Weight for each severity level (optional)

        Returns:
            Dict with precision, recall, f1_score, and confusion counts

        Example:
            >>> findings = [ParsedFinding(pattern="reentrancy", ...)]
            >>> ground_truth = [{"pattern": "reentrancy", "location": "withdraw"}]
            >>> accuracy = OutputParser.calculate_accuracy(findings, ground_truth)
            >>> accuracy["precision"]
            1.0
        """
        weights = severity_weights or {
            "critical": 1.0,
            "high": 0.8,
            "medium": 0.5,
            "low": 0.3,
            "info": 0.1,
        }

        # Track matches
        tp = 0  # True positives
        fp = 0  # False positives
        fn = 0  # False negatives

        matched_gt: set[int] = set()

        for finding in findings:
            matched = False
            for i, gt in enumerate(ground_truth):
                if i in matched_gt:
                    continue
                if OutputParser._is_match(finding, gt):
                    tp += 1
                    matched_gt.add(i)
                    matched = True
                    break
            if not matched:
                fp += 1

        fn = len(ground_truth) - len(matched_gt)

        # Calculate metrics
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        # Calculate severity-weighted metrics
        weighted_tp = 0.0
        weighted_total_gt = 0.0

        for i, gt in enumerate(ground_truth):
            severity = gt.get("severity", "medium")
            weight = weights.get(severity, 0.5)
            weighted_total_gt += weight
            if i in matched_gt:
                weighted_tp += weight

        weighted_recall = (
            weighted_tp / weighted_total_gt if weighted_total_gt > 0 else 0.0
        )

        return {
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "weighted_recall": weighted_recall,
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "matched_indices": list(matched_gt),
        }

    @staticmethod
    def calculate_severity_recall(
        findings: list[ParsedFinding],
        ground_truth: list[dict[str, Any]],
    ) -> dict[str, float]:
        """Calculate recall by severity level.

        Args:
            findings: Parsed findings from analysis
            ground_truth: Expected findings with pattern, severity, location

        Returns:
            Dict mapping severity to recall (0.0 to 1.0)

        Example:
            >>> recall_by_severity = OutputParser.calculate_severity_recall(findings, gt)
            >>> recall_by_severity["critical"]
            0.95
        """
        severity_levels = ["critical", "high", "medium", "low", "info"]
        recall_by_severity: dict[str, float] = {}

        for severity in severity_levels:
            # Filter ground truth by severity
            gt_for_severity = [
                gt for gt in ground_truth if gt.get("severity", "").lower() == severity
            ]

            if not gt_for_severity:
                recall_by_severity[severity] = 1.0  # No ground truth = perfect recall
                continue

            # Count matches
            matched = 0
            for gt in gt_for_severity:
                for finding in findings:
                    if OutputParser._is_match(finding, gt):
                        matched += 1
                        break

            recall_by_severity[severity] = matched / len(gt_for_severity)

        return recall_by_severity

    @staticmethod
    def _is_match(finding: ParsedFinding, ground_truth: dict[str, Any]) -> bool:
        """Check if finding matches ground truth entry.

        Matching criteria:
        1. Pattern must match (case-insensitive, partial match allowed)
        2. Location should be similar (substring match)

        Args:
            finding: Parsed finding to check
            ground_truth: Ground truth entry

        Returns:
            True if finding matches ground truth
        """
        # Pattern must match (case-insensitive)
        gt_pattern = ground_truth.get("pattern", "")
        if not gt_pattern:
            return False

        # Partial pattern matching (e.g., "reentrancy" matches "reentrancy-classic")
        pattern_match = (
            gt_pattern.lower() in finding.pattern.lower()
            or finding.pattern.lower() in gt_pattern.lower()
        )

        if not pattern_match:
            return False

        # Location matching (more lenient - substring match)
        gt_location = ground_truth.get("location", "")
        if gt_location and finding.location:
            # Extract function/line from both
            gt_parts = gt_location.lower().replace(":", " ").split()
            finding_parts = finding.location.lower().replace(":", " ").split()

            # Check if any part matches
            location_match = any(
                gt_part in finding.location.lower() or finding_part in gt_location.lower()
                for gt_part in gt_parts
                for finding_part in finding_parts
            )
            if not location_match:
                # Fallback: simple substring match
                location_match = (
                    gt_location.lower() in finding.location.lower()
                    or finding.location.lower() in gt_location.lower()
                )
            return location_match

        # If no location in ground truth, pattern match is sufficient
        return True

    @staticmethod
    def extract_detection_decision(
        structured_output: dict[str, Any] | None,
    ) -> bool | None:
        """Extract the overall vulnerability detection decision.

        Args:
            structured_output: The structured_output field from ClaudeCodeResult

        Returns:
            True if vulnerable, False if safe, None if undetermined
        """
        if not structured_output:
            return None

        has_vuln = structured_output.get("has_vulnerability")
        if isinstance(has_vuln, bool):
            return has_vuln

        # Fallback: check if there are any high/critical findings
        findings = structured_output.get("findings", [])
        if findings:
            high_severity = [
                f
                for f in findings
                if isinstance(f, dict)
                and f.get("severity", "").lower() in ["critical", "high"]
            ]
            return len(high_severity) > 0

        return None

    @staticmethod
    def group_findings_by_pattern(
        findings: list[ParsedFinding],
    ) -> dict[str, list[ParsedFinding]]:
        """Group findings by vulnerability pattern.

        Args:
            findings: List of parsed findings

        Returns:
            Dict mapping pattern name to list of findings
        """
        grouped: dict[str, list[ParsedFinding]] = {}
        for finding in findings:
            pattern = finding.pattern.lower()
            if pattern not in grouped:
                grouped[pattern] = []
            grouped[pattern].append(finding)
        return grouped

    @staticmethod
    def group_findings_by_severity(
        findings: list[ParsedFinding],
    ) -> dict[str, list[ParsedFinding]]:
        """Group findings by severity level.

        Args:
            findings: List of parsed findings

        Returns:
            Dict mapping severity to list of findings
        """
        grouped: dict[str, list[ParsedFinding]] = {}
        for finding in findings:
            severity = finding.severity.lower()
            if severity not in grouped:
                grouped[severity] = []
            grouped[severity].append(finding)
        return grouped

    @staticmethod
    def filter_by_confidence(
        findings: list[ParsedFinding],
        min_confidence: float = 0.5,
    ) -> list[ParsedFinding]:
        """Filter findings by minimum confidence threshold.

        Args:
            findings: List of parsed findings
            min_confidence: Minimum confidence score (0.0 to 1.0)

        Returns:
            Filtered list of findings
        """
        return [f for f in findings if f.confidence >= min_confidence]

    @staticmethod
    def format_findings_summary(findings: list[ParsedFinding]) -> str:
        """Format findings as a human-readable summary.

        Args:
            findings: List of parsed findings

        Returns:
            Multi-line summary string
        """
        if not findings:
            return "No findings detected."

        lines = [f"Found {len(findings)} potential issue(s):", ""]

        # Group by severity
        by_severity = OutputParser.group_findings_by_severity(findings)
        severity_order = ["critical", "high", "medium", "low", "info"]

        for severity in severity_order:
            if severity in by_severity:
                severity_findings = by_severity[severity]
                lines.append(f"[{severity.upper()}] ({len(severity_findings)}):")
                for f in severity_findings:
                    lines.append(
                        f"  - {f.pattern} at {f.location} "
                        f"(confidence: {f.confidence:.0%})"
                    )
                lines.append("")

        return "\n".join(lines)
