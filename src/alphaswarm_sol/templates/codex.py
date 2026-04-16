"""Codex output schema and formatting for VKG integration.

This module provides:
1. Programmatic schema definition for VKG audit output
2. Functions to format VKG findings into Codex-compatible output
3. Schema generation for use with `codex exec --output-schema`

The schema is designed to work with OpenAI Codex CLI's `--output-schema` flag,
which enforces JSON Schema-validated structured output.

Usage:
    # Generate schema file for Codex
    from alphaswarm_sol.templates.codex import write_output_schema
    write_output_schema(Path("./vkg-audit-schema.json"))

    # Format findings for Codex output
    from alphaswarm_sol.templates.codex import format_findings_for_codex
    output = format_findings_for_codex(findings, contracts, metadata)

    # Validate output against schema
    from alphaswarm_sol.templates.codex import validate_codex_output
    is_valid, errors = validate_codex_output(output)

Reference: https://developers.openai.com/codex/noninteractive/
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from alphaswarm_sol.findings.model import (
    Evidence,
    Finding,
    FindingConfidence,
    FindingSeverity,
    FindingTier,
    Location,
)

# Schema version for tracking compatibility
CODEX_OUTPUT_SCHEMA_VERSION = "1.0.0"

# Default VKG version (can be overridden)
VKG_VERSION = "3.5"


def get_output_schema() -> dict[str, Any]:
    """Get the VKG Codex output schema as a dictionary.

    This schema is compatible with Codex CLI's `--output-schema` flag
    and follows JSON Schema draft-07.

    Returns:
        Complete JSON Schema for VKG audit output

    Example:
        >>> schema = get_output_schema()
        >>> schema["$schema"]
        'http://json-schema.org/draft-07/schema#'
        >>> "findings" in schema["required"]
        True
    """
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "https://vkg.dev/schemas/vkg-codex-output.json",
        "title": "VKG Codex Audit Output",
        "description": "Schema for VKG security audit results compatible with OpenAI Codex --output-schema",
        "type": "object",
        "required": ["findings", "summary", "metadata"],
        "properties": {
            "findings": _get_findings_schema(),
            "summary": _get_summary_schema(),
            "contracts_analyzed": _get_contracts_schema(),
            "recommendations": _get_recommendations_schema(),
            "verdict": _get_verdict_schema(),
            "metadata": _get_metadata_schema(),
        },
        "additionalProperties": False,
    }


def _get_findings_schema() -> dict[str, Any]:
    """Get the schema for the findings array."""
    return {
        "type": "array",
        "description": "List of security findings detected by VKG",
        "items": {
            "type": "object",
            "required": [
                "id",
                "pattern_id",
                "severity",
                "confidence",
                "title",
                "description",
                "location",
            ],
            "properties": {
                "id": {
                    "type": "string",
                    "pattern": "^VKG-[A-F0-9]{8}$",
                    "description": "Unique finding identifier (e.g., VKG-A1B2C3D4)",
                },
                "pattern_id": {
                    "type": "string",
                    "description": "Pattern that triggered this finding (e.g., reentrancy-001)",
                },
                "severity": {
                    "type": "string",
                    "enum": ["critical", "high", "medium", "low", "info"],
                    "description": "Severity level of the finding",
                },
                "confidence": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                    "description": "Confidence level in the detection",
                },
                "tier": {
                    "type": "string",
                    "enum": ["tier_a", "tier_b"],
                    "description": "Detection tier: tier_a=deterministic, tier_b=LLM-verified",
                },
                "title": {
                    "type": "string",
                    "maxLength": 200,
                    "description": "Short title of the finding",
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description of the vulnerability",
                },
                "location": _get_location_schema(),
                "evidence": _get_evidence_schema(),
                "verification_steps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Steps to verify/reproduce the finding",
                },
                "recommendation": {
                    "type": "string",
                    "description": "Recommended fix for the vulnerability",
                },
                "references": {
                    "type": "array",
                    "description": "External references (CWE, SWC, CVE, etc.)",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": [
                                    "cwe",
                                    "swc",
                                    "cve",
                                    "exploit",
                                    "documentation",
                                ],
                                "description": "Type of reference",
                            },
                            "id": {
                                "type": "string",
                                "description": "Reference identifier (e.g., CWE-841)",
                            },
                            "url": {
                                "type": "string",
                                "format": "uri",
                                "description": "URL to reference",
                            },
                        },
                    },
                },
                "status": {
                    "type": "string",
                    "enum": [
                        "pending",
                        "investigating",
                        "confirmed",
                        "false_positive",
                        "escalated",
                        "fixed",
                    ],
                    "description": "Current status of the finding",
                },
            },
        },
    }


def _get_location_schema() -> dict[str, Any]:
    """Get the schema for location objects."""
    return {
        "type": "object",
        "required": ["file", "line"],
        "description": "Source code location of the finding",
        "properties": {
            "file": {
                "type": "string",
                "description": "File path relative to project root",
            },
            "line": {
                "type": "integer",
                "minimum": 1,
                "description": "Line number (1-indexed)",
            },
            "column": {
                "type": "integer",
                "minimum": 0,
                "description": "Column number (0-indexed)",
            },
            "end_line": {
                "type": "integer",
                "minimum": 1,
                "description": "End line number for ranges",
            },
            "end_column": {
                "type": "integer",
                "minimum": 0,
                "description": "End column number for ranges",
            },
            "function": {
                "type": "string",
                "description": "Function name where finding was detected",
            },
            "contract": {
                "type": "string",
                "description": "Contract name where finding was detected",
            },
        },
    }


def _get_evidence_schema() -> dict[str, Any]:
    """Get the schema for evidence objects."""
    return {
        "type": "object",
        "description": "Evidence supporting the finding",
        "properties": {
            "behavioral_signature": {
                "type": "string",
                "description": "Behavioral signature (e.g., R:bal->X:out->W:bal)",
            },
            "semantic_operations": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Semantic operations detected (e.g., TRANSFERS_VALUE_OUT)",
            },
            "properties_matched": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Security properties that matched",
            },
            "properties_missing": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Expected security properties that were missing",
            },
            "code_snippet": {
                "type": "string",
                "description": "Relevant code snippet",
            },
            "why_vulnerable": {
                "type": "string",
                "description": "Plain English explanation of why this is vulnerable",
            },
            "attack_scenario": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Step-by-step attack scenario",
            },
            "data_flow": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Taint/data flow path",
            },
            "guard_analysis": {
                "type": "string",
                "description": "Analysis of guards present or missing",
            },
        },
    }


def _get_summary_schema() -> dict[str, Any]:
    """Get the schema for summary object."""
    return {
        "type": "object",
        "required": ["total_findings", "by_severity", "by_tier"],
        "description": "Summary statistics of the audit",
        "properties": {
            "total_findings": {
                "type": "integer",
                "minimum": 0,
                "description": "Total number of findings",
            },
            "by_severity": {
                "type": "object",
                "description": "Findings count by severity level",
                "properties": {
                    "critical": {"type": "integer", "minimum": 0},
                    "high": {"type": "integer", "minimum": 0},
                    "medium": {"type": "integer", "minimum": 0},
                    "low": {"type": "integer", "minimum": 0},
                    "info": {"type": "integer", "minimum": 0},
                },
            },
            "by_tier": {
                "type": "object",
                "description": "Findings count by detection tier",
                "properties": {
                    "tier_a": {
                        "type": "integer",
                        "minimum": 0,
                        "description": "Deterministic detections",
                    },
                    "tier_b": {
                        "type": "integer",
                        "minimum": 0,
                        "description": "LLM-verified detections",
                    },
                },
            },
            "by_confidence": {
                "type": "object",
                "description": "Findings count by confidence level",
                "properties": {
                    "high": {"type": "integer", "minimum": 0},
                    "medium": {"type": "integer", "minimum": 0},
                    "low": {"type": "integer", "minimum": 0},
                },
            },
            "risk_score": {
                "type": "number",
                "minimum": 0,
                "maximum": 100,
                "description": "Overall risk score (0-100)",
            },
            "top_risk_areas": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Top risk areas identified",
            },
        },
    }


def _get_contracts_schema() -> dict[str, Any]:
    """Get the schema for contracts_analyzed array."""
    return {
        "type": "array",
        "description": "List of contracts that were analyzed",
        "items": {
            "type": "object",
            "required": ["name", "file"],
            "properties": {
                "name": {"type": "string", "description": "Contract name"},
                "file": {"type": "string", "description": "File path"},
                "function_count": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Number of functions in contract",
                },
                "findings_count": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Number of findings in this contract",
                },
                "properties_extracted": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Number of security properties extracted",
                },
            },
        },
    }


def _get_recommendations_schema() -> dict[str, Any]:
    """Get the schema for recommendations array."""
    return {
        "type": "array",
        "description": "Overall recommendations for the codebase",
        "items": {
            "type": "object",
            "properties": {
                "priority": {
                    "type": "string",
                    "enum": ["critical", "high", "medium", "low"],
                    "description": "Priority level",
                },
                "category": {
                    "type": "string",
                    "description": "Recommendation category (e.g., Access Control, Reentrancy)",
                },
                "recommendation": {
                    "type": "string",
                    "description": "The recommendation text",
                },
                "affected_findings": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Finding IDs this recommendation addresses",
                },
            },
        },
    }


def _get_verdict_schema() -> dict[str, Any]:
    """Get the schema for verdict object."""
    return {
        "type": "object",
        "description": "Overall audit verdict",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["pass", "fail", "needs_review"],
                "description": "Overall audit status",
            },
            "reasoning": {
                "type": "string",
                "description": "Explanation for the verdict",
            },
            "critical_issues_found": {
                "type": "boolean",
                "description": "Whether critical issues were found",
            },
            "deployment_recommended": {
                "type": "boolean",
                "description": "Whether deployment is recommended",
            },
        },
    }


def _get_metadata_schema() -> dict[str, Any]:
    """Get the schema for metadata object."""
    return {
        "type": "object",
        "required": ["timestamp", "vkg_version", "schema_version"],
        "description": "Audit metadata",
        "properties": {
            "timestamp": {
                "type": "string",
                "format": "date-time",
                "description": "Audit timestamp in ISO 8601 format",
            },
            "vkg_version": {
                "type": "string",
                "description": "VKG version used for analysis",
            },
            "schema_version": {
                "type": "string",
                "description": "Output schema version",
            },
            "codex_model": {
                "type": "string",
                "description": "Codex model used (if applicable)",
            },
            "graph_properties_count": {
                "type": "integer",
                "minimum": 0,
                "description": "Total security properties extracted",
            },
            "patterns_evaluated": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Patterns that were evaluated",
            },
            "analysis_duration_seconds": {
                "type": "number",
                "minimum": 0,
                "description": "Time taken for analysis in seconds",
            },
            "project_path": {
                "type": "string",
                "description": "Path to analyzed project",
            },
        },
    }


def write_output_schema(path: Path | str, indent: int = 2) -> Path:
    """Write the VKG Codex output schema to a file.

    This generates a JSON Schema file that can be used with
    `codex exec --output-schema <path>`.

    Args:
        path: Path to write the schema file
        indent: JSON indentation level

    Returns:
        Path to the written schema file

    Example:
        >>> schema_path = write_output_schema(Path("./vkg-audit-schema.json"))
        >>> print(f"Schema written to: {schema_path}")
    """
    if isinstance(path, str):
        path = Path(path)

    schema = get_output_schema()
    path.write_text(json.dumps(schema, indent=indent) + "\n")
    return path


def get_schema_json(indent: int = 2) -> str:
    """Get the VKG Codex output schema as a JSON string.

    Args:
        indent: JSON indentation level

    Returns:
        JSON string of the schema
    """
    return json.dumps(get_output_schema(), indent=indent)


# ============================================================================
# Formatting Functions
# ============================================================================


@dataclass
class ContractInfo:
    """Information about an analyzed contract."""

    name: str
    file: str
    function_count: int = 0
    findings_count: int = 0
    properties_extracted: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "file": self.file,
            "function_count": self.function_count,
            "findings_count": self.findings_count,
            "properties_extracted": self.properties_extracted,
        }


@dataclass
class Recommendation:
    """A recommendation for improving security."""

    priority: str  # critical, high, medium, low
    category: str
    recommendation: str
    affected_findings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "priority": self.priority,
            "category": self.category,
            "recommendation": self.recommendation,
            "affected_findings": self.affected_findings,
        }


@dataclass
class AuditMetadata:
    """Metadata about the audit."""

    timestamp: str = ""
    vkg_version: str = VKG_VERSION
    schema_version: str = CODEX_OUTPUT_SCHEMA_VERSION
    codex_model: str = ""
    graph_properties_count: int = 0
    patterns_evaluated: list[str] = field(default_factory=list)
    analysis_duration_seconds: float = 0.0
    project_path: str = ""

    def __post_init__(self) -> None:
        """Set default timestamp if not provided."""
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "timestamp": self.timestamp,
            "vkg_version": self.vkg_version,
            "schema_version": self.schema_version,
        }
        if self.codex_model:
            result["codex_model"] = self.codex_model
        if self.graph_properties_count > 0:
            result["graph_properties_count"] = self.graph_properties_count
        if self.patterns_evaluated:
            result["patterns_evaluated"] = self.patterns_evaluated
        if self.analysis_duration_seconds > 0:
            result["analysis_duration_seconds"] = self.analysis_duration_seconds
        if self.project_path:
            result["project_path"] = self.project_path
        return result


def format_finding_for_codex(finding: Finding) -> dict[str, Any]:
    """Format a single VKG Finding for Codex output.

    Args:
        finding: VKG Finding object

    Returns:
        Dictionary formatted for Codex output schema
    """
    result: dict[str, Any] = {
        "id": finding.id,
        "pattern_id": finding.pattern,
        "severity": _map_severity(finding.severity),
        "confidence": finding.confidence.value,
        "tier": finding.tier.value,
        "title": finding.title,
        "description": finding.description,
        "location": _format_location(finding.location),
    }

    # Add evidence if present
    if finding.evidence:
        result["evidence"] = _format_evidence(finding.evidence)

    # Add verification steps if present
    if finding.verification_steps:
        result["verification_steps"] = finding.verification_steps

    # Add recommendation if present
    if finding.recommended_fix:
        result["recommendation"] = finding.recommended_fix

    # Add references if present
    references = []
    if finding.cwe:
        references.append({"type": "cwe", "id": finding.cwe})
    if finding.swc:
        references.append({"type": "swc", "id": finding.swc})
    if finding.references:
        for ref in finding.references:
            if ref.startswith("CVE-"):
                references.append({"type": "cve", "id": ref})
            elif ref.startswith("http"):
                references.append({"type": "documentation", "url": ref})
            else:
                references.append({"type": "documentation", "id": ref})
    if references:
        result["references"] = references

    # Add status
    result["status"] = finding.status.value

    return result


def _map_severity(severity: FindingSeverity) -> str:
    """Map FindingSeverity to Codex output severity string."""
    mapping = {
        FindingSeverity.CRITICAL: "critical",
        FindingSeverity.HIGH: "high",
        FindingSeverity.MEDIUM: "medium",
        FindingSeverity.LOW: "low",
        FindingSeverity.INFO: "info",
    }
    return mapping.get(severity, "medium")


def _format_location(location: Location) -> dict[str, Any]:
    """Format a Location for Codex output."""
    result: dict[str, Any] = {
        "file": location.file,
        "line": location.line,
    }
    if location.column > 0:
        result["column"] = location.column
    if location.end_line is not None:
        result["end_line"] = location.end_line
    if location.end_column is not None:
        result["end_column"] = location.end_column
    if location.function:
        result["function"] = location.function
    if location.contract:
        result["contract"] = location.contract
    return result


def _format_evidence(evidence: Evidence) -> dict[str, Any]:
    """Format Evidence for Codex output."""
    result: dict[str, Any] = {}

    if evidence.behavioral_signature:
        result["behavioral_signature"] = evidence.behavioral_signature

    if evidence.operations:
        result["semantic_operations"] = evidence.operations

    if evidence.properties_matched:
        result["properties_matched"] = evidence.properties_matched

    if evidence.properties_missing:
        result["properties_missing"] = evidence.properties_missing

    if evidence.code_snippet:
        result["code_snippet"] = evidence.code_snippet

    if evidence.why_vulnerable:
        result["why_vulnerable"] = evidence.why_vulnerable

    if evidence.attack_scenario:
        result["attack_scenario"] = evidence.attack_scenario

    if evidence.data_flow:
        result["data_flow"] = evidence.data_flow

    if evidence.guard_analysis:
        result["guard_analysis"] = evidence.guard_analysis

    return result


def calculate_summary(findings: list[Finding]) -> dict[str, Any]:
    """Calculate summary statistics from a list of findings.

    Args:
        findings: List of VKG Finding objects

    Returns:
        Summary dictionary for Codex output
    """
    # Count by severity
    by_severity = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "info": 0,
    }
    for finding in findings:
        severity = _map_severity(finding.severity)
        by_severity[severity] = by_severity.get(severity, 0) + 1

    # Count by tier
    by_tier = {"tier_a": 0, "tier_b": 0}
    for finding in findings:
        tier = finding.tier.value
        by_tier[tier] = by_tier.get(tier, 0) + 1

    # Count by confidence
    by_confidence = {"high": 0, "medium": 0, "low": 0}
    for finding in findings:
        conf = finding.confidence.value
        by_confidence[conf] = by_confidence.get(conf, 0) + 1

    # Calculate risk score (weighted by severity)
    severity_weights = {
        "critical": 25,
        "high": 15,
        "medium": 8,
        "low": 3,
        "info": 1,
    }
    risk_score = 0.0
    for sev, count in by_severity.items():
        risk_score += count * severity_weights.get(sev, 0)
    # Normalize to 0-100 (cap at 100)
    risk_score = min(100.0, risk_score)

    # Identify top risk areas (patterns with most findings)
    pattern_counts: dict[str, int] = {}
    for finding in findings:
        pattern = finding.pattern.split("-")[0]  # Get category prefix
        pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
    top_risk_areas = sorted(pattern_counts.keys(), key=lambda x: pattern_counts[x], reverse=True)[:5]

    return {
        "total_findings": len(findings),
        "by_severity": by_severity,
        "by_tier": by_tier,
        "by_confidence": by_confidence,
        "risk_score": round(risk_score, 1),
        "top_risk_areas": top_risk_areas,
    }


def calculate_verdict(findings: list[Finding]) -> dict[str, Any]:
    """Calculate the overall audit verdict.

    Args:
        findings: List of VKG Finding objects

    Returns:
        Verdict dictionary for Codex output
    """
    # Check for critical issues
    critical_count = sum(1 for f in findings if f.severity == FindingSeverity.CRITICAL)
    high_count = sum(1 for f in findings if f.severity == FindingSeverity.HIGH)

    # Determine status
    if critical_count > 0:
        status = "fail"
        reasoning = f"Found {critical_count} critical issue(s) that must be addressed before deployment."
        deployment_recommended = False
    elif high_count > 0:
        status = "needs_review"
        reasoning = f"Found {high_count} high-severity issue(s) that should be reviewed before deployment."
        deployment_recommended = False
    else:
        status = "pass"
        reasoning = "No critical or high-severity issues found. Review medium/low findings as needed."
        deployment_recommended = True

    return {
        "status": status,
        "reasoning": reasoning,
        "critical_issues_found": critical_count > 0,
        "deployment_recommended": deployment_recommended,
    }


def generate_recommendations(findings: list[Finding]) -> list[dict[str, Any]]:
    """Generate recommendations based on findings.

    Args:
        findings: List of VKG Finding objects

    Returns:
        List of recommendation dictionaries
    """
    recommendations: list[Recommendation] = []

    # Group findings by pattern category
    category_findings: dict[str, list[Finding]] = {}
    for finding in findings:
        # Extract category from pattern (e.g., "reentrancy-001" -> "reentrancy")
        parts = finding.pattern.split("-")
        category = parts[0] if parts else "unknown"
        if category not in category_findings:
            category_findings[category] = []
        category_findings[category].append(finding)

    # Generate recommendations by category
    category_recommendations = {
        "reentrancy": "Implement the checks-effects-interactions pattern and consider using ReentrancyGuard.",
        "auth": "Add access control modifiers to sensitive functions and verify ownership patterns.",
        "oracle": "Add staleness checks for oracle data and implement circuit breakers.",
        "mev": "Add slippage protection and deadline parameters to swap functions.",
        "dos": "Bound loop iterations and avoid strict equality checks on balances.",
        "token": "Use SafeERC20 for token transfers and check return values.",
        "upgrade": "Implement storage gaps and verify proxy initialization.",
        "crypto": "Validate signature parameters and check for zero addresses.",
    }

    for category, cat_findings in category_findings.items():
        if category in category_recommendations:
            # Determine priority based on highest severity in category
            max_severity = max(f.severity for f in cat_findings)
            priority = _map_severity(max_severity)

            recommendations.append(
                Recommendation(
                    priority=priority,
                    category=category.title(),
                    recommendation=category_recommendations[category],
                    affected_findings=[f.id for f in cat_findings],
                )
            )

    # Sort by priority
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    recommendations.sort(key=lambda r: priority_order.get(r.priority, 4))

    return [r.to_dict() for r in recommendations]


def format_findings_for_codex(
    findings: list[Finding],
    contracts: list[ContractInfo] | None = None,
    metadata: AuditMetadata | None = None,
    include_recommendations: bool = True,
    include_verdict: bool = True,
) -> dict[str, Any]:
    """Format VKG findings into Codex-compatible output.

    This is the main function for converting VKG analysis results
    into the structured format expected by Codex.

    Args:
        findings: List of VKG Finding objects
        contracts: Optional list of ContractInfo objects
        metadata: Optional AuditMetadata object
        include_recommendations: Whether to include recommendations
        include_verdict: Whether to include verdict

    Returns:
        Dictionary matching the VKG Codex output schema

    Example:
        >>> from alphaswarm_sol.findings.model import Finding, FindingSeverity, FindingConfidence, Location
        >>> findings = [
        ...     Finding(
        ...         pattern="reentrancy-001",
        ...         severity=FindingSeverity.HIGH,
        ...         confidence=FindingConfidence.HIGH,
        ...         location=Location(file="Vault.sol", line=42, function="withdraw"),
        ...         description="State write after external call",
        ...     )
        ... ]
        >>> output = format_findings_for_codex(findings)
        >>> output["summary"]["total_findings"]
        1
    """
    # Format findings
    formatted_findings = [format_finding_for_codex(f) for f in findings]

    # Calculate summary
    summary = calculate_summary(findings)

    # Build result
    result: dict[str, Any] = {
        "findings": formatted_findings,
        "summary": summary,
        "metadata": (metadata or AuditMetadata()).to_dict(),
    }

    # Add contracts if provided
    if contracts:
        result["contracts_analyzed"] = [c.to_dict() for c in contracts]

    # Add recommendations if requested
    if include_recommendations:
        result["recommendations"] = generate_recommendations(findings)

    # Add verdict if requested
    if include_verdict:
        result["verdict"] = calculate_verdict(findings)

    return result


def format_findings_to_json(
    findings: list[Finding],
    contracts: list[ContractInfo] | None = None,
    metadata: AuditMetadata | None = None,
    indent: int = 2,
    **kwargs: Any,
) -> str:
    """Format VKG findings to JSON string.

    Args:
        findings: List of VKG Finding objects
        contracts: Optional list of ContractInfo objects
        metadata: Optional AuditMetadata object
        indent: JSON indentation level
        **kwargs: Additional arguments for format_findings_for_codex

    Returns:
        JSON string of the formatted output
    """
    output = format_findings_for_codex(findings, contracts, metadata, **kwargs)
    return json.dumps(output, indent=indent)


# ============================================================================
# Validation Functions
# ============================================================================


def validate_codex_output(output: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate output against the VKG Codex output schema.

    Args:
        output: Dictionary to validate

    Returns:
        Tuple of (is_valid, list of error messages)

    Example:
        >>> output = {"findings": [], "summary": {...}, "metadata": {...}}
        >>> is_valid, errors = validate_codex_output(output)
        >>> if not is_valid:
        ...     print(f"Validation errors: {errors}")
    """
    try:
        import jsonschema
    except ImportError:
        return False, ["jsonschema package not installed"]

    schema = get_output_schema()
    errors: list[str] = []

    try:
        jsonschema.validate(instance=output, schema=schema)
        return True, []
    except jsonschema.ValidationError as e:
        errors.append(f"Validation error at {'.'.join(str(p) for p in e.path)}: {e.message}")
        return False, errors
    except jsonschema.SchemaError as e:
        errors.append(f"Schema error: {e.message}")
        return False, errors


def validate_codex_output_file(path: Path | str) -> tuple[bool, list[str]]:
    """Validate a JSON file against the VKG Codex output schema.

    Args:
        path: Path to JSON file to validate

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    if isinstance(path, str):
        path = Path(path)

    if not path.exists():
        return False, [f"File not found: {path}"]

    try:
        with open(path) as f:
            output = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"]

    return validate_codex_output(output)
