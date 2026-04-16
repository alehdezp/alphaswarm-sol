"""
Analysis Completeness Report

Tracks what was analyzed vs. skipped during knowledge graph construction,
providing honest self-assessment of analysis coverage.

Philosophy Alignment: "Admit uncertainty, escalate honestly"
- Users MUST know when analysis is incomplete
- Silent failures hide vulnerabilities
- Every run reports what it analyzed and what it couldn't
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class CompletionStatus(str, Enum):
    """Overall analysis completion status."""

    COMPLETE = "complete"  # All contracts fully analyzed
    PARTIAL = "partial"    # Some contracts/features skipped
    FAILED = "failed"      # Analysis could not complete


class SkipReason(str, Enum):
    """Reason a contract or feature was skipped."""

    INLINE_ASSEMBLY = "inline_assembly"       # Yul/assembly not fully analyzed
    PROXY_UNRESOLVED = "proxy_unresolved"     # Proxy target unknown
    PARSE_ERROR = "parse_error"               # Slither failed to parse
    UNSUPPORTED_SOLC = "unsupported_solc"     # Solidity version not supported
    COMPILATION_ERROR = "compilation_error"   # Compilation failed
    TIMEOUT = "timeout"                       # Analysis exceeded timeout
    IMPORT_ERROR = "import_error"             # Missing imports
    UNKNOWN = "unknown"                       # Unknown error


@dataclass
class SkippedContract:
    """Information about a skipped contract."""

    contract: str
    reason: SkipReason
    details: str = ""
    file_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "contract": self.contract,
            "reason": self.reason.value,
            "reason_code": self.reason.value,
            "details": self.details,
            "file_path": self.file_path,
        }


@dataclass
class UnsupportedFeature:
    """Information about an unsupported feature detected."""

    feature: str
    occurrences: int = 1
    locations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "feature": self.feature,
            "occurrences": self.occurrences,
            "locations": self.locations,
        }


@dataclass
class BuildInfo:
    """Build environment information."""

    solc_version: str = ""
    framework: str = "unknown"
    optimizer_enabled: bool = False
    slither_version: str = ""
    python_version: str = ""
    vkg_version: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "solc_version": self.solc_version,
            "framework": self.framework,
            "optimizer_enabled": self.optimizer_enabled,
            "slither_version": self.slither_version,
            "python_version": self.python_version,
            "vkg_version": self.vkg_version,
        }


@dataclass
class CompletenessReport:
    """
    Analysis completeness report.

    Tracks which contracts were analyzed, which were skipped (and why),
    and which unsupported features were detected.

    Example:
        >>> report = CompletenessReport()
        >>> report.add_analyzed("MyToken.sol", "MyToken")
        >>> report.add_skipped("YulHelper.sol", "YulHelper", SkipReason.INLINE_ASSEMBLY)
        >>> print(report.status)
        CompletionStatus.PARTIAL
        >>> print(f"{report.coverage_pct:.1f}%")
        50.0%
    """

    contracts_analyzed: list[str] = field(default_factory=list)
    contracts_analyzed_files: list[str] = field(default_factory=list)
    skipped: list[SkippedContract] = field(default_factory=list)
    unsupported_features: dict[str, UnsupportedFeature] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    build_info: BuildInfo = field(default_factory=BuildInfo)
    _failed: bool = field(default=False, repr=False)
    _failure_reason: str = field(default="", repr=False)

    @property
    def status(self) -> CompletionStatus:
        """Determine overall completion status."""
        if self._failed:
            return CompletionStatus.FAILED
        if not self.contracts_analyzed and not self.skipped:
            return CompletionStatus.FAILED
        if self.skipped:
            return CompletionStatus.PARTIAL
        return CompletionStatus.COMPLETE

    @property
    def contracts_total(self) -> int:
        """Total number of contracts encountered."""
        return len(self.contracts_analyzed) + len(self.skipped)

    @property
    def coverage_pct(self) -> float:
        """Percentage of contracts successfully analyzed."""
        if self.contracts_total == 0:
            return 0.0
        return (len(self.contracts_analyzed) / self.contracts_total) * 100

    def add_analyzed(self, file_path: str, contract_name: str) -> None:
        """Record a successfully analyzed contract."""
        full_name = f"{file_path}:{contract_name}"
        if full_name not in self.contracts_analyzed:
            self.contracts_analyzed.append(full_name)
        if file_path not in self.contracts_analyzed_files:
            self.contracts_analyzed_files.append(file_path)

    def add_skipped(
        self,
        file_path: str,
        contract_name: str,
        reason: SkipReason,
        details: str = "",
    ) -> None:
        """Record a skipped contract with reason."""
        self.skipped.append(SkippedContract(
            contract=contract_name,
            reason=reason,
            details=details,
            file_path=file_path,
        ))
        # Add warning
        self.add_warning(f"{contract_name}: {reason.value}" + (f" - {details}" if details else ""))

    def add_unsupported_feature(
        self,
        feature: str,
        location: str = "",
    ) -> None:
        """Record an unsupported feature occurrence."""
        if feature not in self.unsupported_features:
            self.unsupported_features[feature] = UnsupportedFeature(
                feature=feature,
                occurrences=0,
                locations=[],
            )
        self.unsupported_features[feature].occurrences += 1
        if location:
            self.unsupported_features[feature].locations.append(location)

    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        if warning not in self.warnings:
            self.warnings.append(warning)

    def mark_failed(self, reason: str) -> None:
        """Mark the analysis as failed."""
        self._failed = True
        self._failure_reason = reason
        self.add_warning(f"Analysis failed: {reason}")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "status": self.status.value,
            "coverage_pct": round(self.coverage_pct, 2),
            "contracts_analyzed": len(self.contracts_analyzed),
            "contracts_skipped": len(self.skipped),
            "contracts_total": self.contracts_total,
            "analyzed_contracts": self.contracts_analyzed,
            "analyzed_files": self.contracts_analyzed_files,
            "skipped_details": [s.to_dict() for s in self.skipped],
            "unsupported_features": [
                f.to_dict() for f in self.unsupported_features.values()
            ],
            "warnings": self.warnings,
            "build_info": self.build_info.to_dict(),
            "failure_reason": self._failure_reason if self._failed else None,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, path: Path) -> None:
        """Save report to file."""
        path.write_text(self.to_json())

    @classmethod
    def load(cls, path: Path) -> "CompletenessReport":
        """Load report from file."""
        data = json.loads(path.read_text())
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CompletenessReport":
        """Create report from dictionary."""
        report = cls()

        # Restore analyzed contracts
        for contract in data.get("analyzed_contracts", []):
            # Parse file:contract format
            if ":" in contract:
                file_path, contract_name = contract.rsplit(":", 1)
                report.add_analyzed(file_path, contract_name)
            else:
                report.contracts_analyzed.append(contract)

        # Restore skipped contracts
        for skipped_data in data.get("skipped_details", []):
            reason = SkipReason(skipped_data.get("reason", "unknown"))
            report.skipped.append(SkippedContract(
                contract=skipped_data.get("contract", ""),
                reason=reason,
                details=skipped_data.get("details", ""),
                file_path=skipped_data.get("file_path", ""),
            ))

        # Restore unsupported features
        for feature_data in data.get("unsupported_features", []):
            feature = feature_data.get("feature", "")
            report.unsupported_features[feature] = UnsupportedFeature(
                feature=feature,
                occurrences=feature_data.get("occurrences", 1),
                locations=feature_data.get("locations", []),
            )

        # Restore warnings
        report.warnings = data.get("warnings", [])

        # Restore build info
        build_info_data = data.get("build_info", {})
        report.build_info = BuildInfo(
            solc_version=build_info_data.get("solc_version", ""),
            framework=build_info_data.get("framework", "unknown"),
            optimizer_enabled=build_info_data.get("optimizer_enabled", False),
            slither_version=build_info_data.get("slither_version", ""),
            python_version=build_info_data.get("python_version", ""),
            vkg_version=build_info_data.get("vkg_version", ""),
        )

        # Restore failure state
        if data.get("failure_reason"):
            report.mark_failed(data["failure_reason"])

        return report

    def format_cli_output(self) -> str:
        """Format report for CLI display."""
        lines = []

        # Header with status
        status_str = self.status.value.upper()
        if self.status == CompletionStatus.COMPLETE:
            lines.append(f"Analysis COMPLETE")
        elif self.status == CompletionStatus.PARTIAL:
            lines.append(f"Analysis PARTIAL COVERAGE")
        else:
            lines.append(f"Analysis FAILED")

        lines.append("")

        # Coverage
        lines.append(
            f"Coverage: {self.coverage_pct:.1f}% "
            f"({len(self.contracts_analyzed)}/{self.contracts_total} contracts)"
        )

        # Build info
        build_parts = []
        if self.build_info.framework != "unknown":
            build_parts.append(self.build_info.framework.capitalize())
        if self.build_info.solc_version:
            build_parts.append(f"Solc {self.build_info.solc_version}")
        if self.build_info.optimizer_enabled:
            build_parts.append("Optimizer ON")
        if build_parts:
            lines.append(f"Build: {' | '.join(build_parts)}")

        lines.append("")

        # Warnings
        if self.warnings:
            lines.append("WARNINGS:")
            for warning in self.warnings[:10]:  # Limit to 10
                lines.append(f"  [!] {warning}")
            if len(self.warnings) > 10:
                lines.append(f"  ... and {len(self.warnings) - 10} more")
            lines.append("")

        # Unsupported features
        if self.unsupported_features:
            lines.append("Unsupported features detected:")
            for feature in self.unsupported_features.values():
                lines.append(f"  - {feature.feature}: {feature.occurrences} occurrence(s)")
            lines.append("")

        return "\n".join(lines)


def generate_completeness_report(
    graph_metadata: dict[str, Any],
    analyzed_contracts: list[tuple[str, str]],
    skipped_contracts: list[tuple[str, str, SkipReason, str]],
    unsupported_features: list[tuple[str, str]],
    warnings: list[str],
) -> CompletenessReport:
    """
    Generate a completeness report from analysis results.

    Args:
        graph_metadata: Metadata from the knowledge graph
        analyzed_contracts: List of (file_path, contract_name) tuples
        skipped_contracts: List of (file_path, contract_name, reason, details) tuples
        unsupported_features: List of (feature, location) tuples
        warnings: List of warning messages

    Returns:
        CompletenessReport instance
    """
    report = CompletenessReport()

    # Add analyzed contracts
    for file_path, contract_name in analyzed_contracts:
        report.add_analyzed(file_path, contract_name)

    # Add skipped contracts
    for file_path, contract_name, reason, details in skipped_contracts:
        report.add_skipped(file_path, contract_name, reason, details)

    # Add unsupported features
    for feature, location in unsupported_features:
        report.add_unsupported_feature(feature, location)

    # Add warnings
    for warning in warnings:
        report.add_warning(warning)

    # Extract build info from metadata
    report.build_info = BuildInfo(
        solc_version=graph_metadata.get("solc_version_selected", ""),
        framework=graph_metadata.get("framework", "unknown"),
        slither_version=graph_metadata.get("slither_version", ""),
    )

    return report


# JSON Schema for validation
COMPLETENESS_REPORT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://alphaswarm.dev/schemas/completeness-report.json",
    "title": "VKG Completeness Report",
    "description": "Analysis completeness report from True VKG",
    "type": "object",
    "required": ["status", "coverage_pct", "contracts_analyzed", "contracts_skipped"],
    "properties": {
        "status": {
            "type": "string",
            "enum": ["complete", "partial", "failed"],
            "description": "Overall analysis status",
        },
        "coverage_pct": {
            "type": "number",
            "minimum": 0,
            "maximum": 100,
            "description": "Percentage of contracts analyzed",
        },
        "contracts_analyzed": {
            "type": "integer",
            "minimum": 0,
            "description": "Number of contracts successfully analyzed",
        },
        "contracts_skipped": {
            "type": "integer",
            "minimum": 0,
            "description": "Number of contracts skipped",
        },
        "contracts_total": {
            "type": "integer",
            "minimum": 0,
            "description": "Total number of contracts encountered",
        },
        "analyzed_contracts": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of analyzed contract identifiers",
        },
        "analyzed_files": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of analyzed file paths",
        },
        "skipped_details": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["contract", "reason"],
                "properties": {
                    "contract": {"type": "string"},
                    "reason": {
                        "type": "string",
                        "enum": [
                            "inline_assembly",
                            "proxy_unresolved",
                            "parse_error",
                            "unsupported_solc",
                            "compilation_error",
                            "timeout",
                            "import_error",
                            "unknown",
                        ],
                    },
                    "reason_code": {"type": "string"},
                    "details": {"type": "string"},
                    "file_path": {"type": "string"},
                },
            },
            "description": "Details of skipped contracts",
        },
        "unsupported_features": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["feature", "occurrences"],
                "properties": {
                    "feature": {"type": "string"},
                    "occurrences": {"type": "integer", "minimum": 1},
                    "locations": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
            "description": "Unsupported features detected",
        },
        "warnings": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Warning messages",
        },
        "build_info": {
            "type": "object",
            "properties": {
                "solc_version": {"type": "string"},
                "framework": {"type": "string"},
                "optimizer_enabled": {"type": "boolean"},
                "slither_version": {"type": "string"},
                "python_version": {"type": "string"},
                "vkg_version": {"type": "string"},
            },
            "description": "Build environment information",
        },
        "failure_reason": {
            "type": ["string", "null"],
            "description": "Reason for failure if status is 'failed'",
        },
    },
}
