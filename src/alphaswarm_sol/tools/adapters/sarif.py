"""SARIF 2.1.0 Adapter - Universal Normalization Layer.

Converts between VKG internal finding format and SARIF 2.1.0
for cross-tool integration and standardized output.

SARIF (Static Analysis Results Interchange Format) is the industry
standard for static analysis tool output, enabling:
- Cross-tool deduplication
- IDE integration
- CI/CD pipeline integration
- Standardized reporting
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union


# SARIF 2.1.0 Constants
SARIF_VERSION = "2.1.0"
SARIF_SCHEMA = (
    "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/"
    "master/Schemata/sarif-schema-2.1.0.json"
)


@dataclass
class VKGFinding:
    """VKG internal finding representation.

    A unified format for findings from any source (VKG, Slither, Aderyn, Mythril, etc.)
    that captures all essential information for vulnerability analysis.

    Attributes:
        id: Unique finding identifier (generated if not provided)
        source: Tool that produced the finding
        rule_id: Detector/rule identifier from the source tool
        title: Short description of the finding
        description: Detailed description with context
        severity: Normalized severity (critical/high/medium/low/info)
        category: Vulnerability category (reentrancy, access_control, etc.)
        file: Relative path to the affected file
        line: Starting line number
        end_line: Ending line number (optional)
        column: Column number (optional)
        function: Affected function name (optional)
        contract: Affected contract name (optional)
        confidence: Confidence score (0.0-1.0)
        tool_confidence: Original confidence string from tool
        raw: Original finding data from the source tool
        vkg_pattern: Mapped VKG pattern ID (optional)
        fix_suggestion: Suggested fix (optional)
    """

    source: str
    rule_id: str
    title: str
    description: str
    severity: str
    category: str
    file: str
    line: int
    id: str = ""
    end_line: Optional[int] = None
    column: Optional[int] = None
    function: Optional[str] = None
    contract: Optional[str] = None
    confidence: float = 0.7
    tool_confidence: str = "Medium"
    raw: Dict[str, Any] = field(default_factory=dict)
    vkg_pattern: Optional[str] = None
    fix_suggestion: Optional[str] = None

    def __post_init__(self) -> None:
        """Generate ID if not provided."""
        if not self.id:
            # Create deterministic ID from key fields
            content = f"{self.source}:{self.rule_id}:{self.file}:{self.line}:{self.category}"
            self.id = hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary with all finding fields
        """
        return {
            "id": self.id,
            "source": self.source,
            "rule_id": self.rule_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "category": self.category,
            "file": self.file,
            "line": self.line,
            "end_line": self.end_line,
            "column": self.column,
            "function": self.function,
            "contract": self.contract,
            "confidence": self.confidence,
            "tool_confidence": self.tool_confidence,
            "vkg_pattern": self.vkg_pattern,
            "fix_suggestion": self.fix_suggestion,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VKGFinding":
        """Create VKGFinding from dictionary.

        Args:
            data: Dictionary with finding fields

        Returns:
            VKGFinding instance
        """
        return cls(
            id=data.get("id", ""),
            source=data.get("source", "unknown"),
            rule_id=data.get("rule_id", "unknown"),
            title=data.get("title", ""),
            description=data.get("description", ""),
            severity=data.get("severity", "medium"),
            category=data.get("category", "unknown"),
            file=data.get("file", ""),
            line=data.get("line", 0),
            end_line=data.get("end_line"),
            column=data.get("column"),
            function=data.get("function"),
            contract=data.get("contract"),
            confidence=data.get("confidence", 0.7),
            tool_confidence=data.get("tool_confidence", "Medium"),
            raw=data.get("raw", {}),
            vkg_pattern=data.get("vkg_pattern"),
            fix_suggestion=data.get("fix_suggestion"),
        )


class SARIFAdapter:
    """Adapter for SARIF 2.1.0 format conversion.

    Converts between VKG internal format and SARIF 2.1.0, enabling:
    - Standard output format for CI/CD integration
    - Cross-tool deduplication via SARIF
    - IDE integration (VS Code, IntelliJ)

    Example:
        >>> adapter = SARIFAdapter()
        >>> sarif = adapter.to_sarif(findings, "vkg", "1.0.0")
        >>> findings = adapter.from_sarif(sarif)
    """

    # SARIF level to VKG severity mapping
    LEVEL_TO_SEVERITY: Dict[str, str] = {
        "error": "high",
        "warning": "medium",
        "note": "low",
        "none": "info",
    }

    # VKG severity to SARIF level mapping
    SEVERITY_TO_LEVEL: Dict[str, str] = {
        "critical": "error",
        "high": "error",
        "medium": "warning",
        "low": "note",
        "info": "none",
    }

    # SARIF level to severity with critical support
    LEVEL_SEVERITY_MAP: Dict[str, Dict[str, str]] = {
        "error": {"default": "high", "security": "critical"},
        "warning": {"default": "medium"},
        "note": {"default": "low"},
        "none": {"default": "info"},
    }

    def to_sarif(
        self,
        findings: List[VKGFinding],
        tool_name: str,
        tool_version: str,
        include_raw: bool = False,
    ) -> Dict[str, Any]:
        """Convert VKG findings to SARIF 2.1.0 format.

        Args:
            findings: List of VKG findings to convert
            tool_name: Name of the originating tool
            tool_version: Version of the originating tool
            include_raw: Whether to include raw data in properties

        Returns:
            SARIF 2.1.0 document as dictionary
        """
        # Collect unique rules
        rules_map: Dict[str, Dict[str, Any]] = {}
        for finding in findings:
            if finding.rule_id not in rules_map:
                rules_map[finding.rule_id] = self._finding_to_rule(finding)

        # Build results
        results = [
            self._finding_to_result(f, include_raw=include_raw)
            for f in findings
        ]

        return {
            "$schema": SARIF_SCHEMA,
            "version": SARIF_VERSION,
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": tool_name,
                            "version": tool_version,
                            "informationUri": f"https://github.com/alphaswarm/{tool_name}",
                            "rules": list(rules_map.values()),
                        }
                    },
                    "results": results,
                    "invocations": [
                        {
                            "executionSuccessful": True,
                            "endTimeUtc": datetime.now(timezone.utc).isoformat(),
                        }
                    ],
                }
            ],
        }

    def from_sarif(self, sarif: Dict[str, Any]) -> List[VKGFinding]:
        """Parse SARIF 2.1.0 document to VKG findings.

        Args:
            sarif: SARIF 2.1.0 document as dictionary

        Returns:
            List of VKG findings
        """
        findings: List[VKGFinding] = []

        runs = sarif.get("runs", [])
        for run in runs:
            tool_name = run.get("tool", {}).get("driver", {}).get("name", "unknown")
            rules = self._build_rules_index(run)
            results = run.get("results", [])

            for result in results:
                finding = self._result_to_finding(result, tool_name, rules)
                if finding:
                    findings.append(finding)

        return findings

    def validate_sarif(self, sarif: Dict[str, Any]) -> bool:
        """Basic validation of SARIF document structure.

        Checks required fields per SARIF 2.1.0 specification.
        Not a full schema validation, but catches common issues.

        Args:
            sarif: SARIF document to validate

        Returns:
            True if basic structure is valid
        """
        # Check version
        if sarif.get("version") != SARIF_VERSION:
            return False

        # Check runs array exists
        runs = sarif.get("runs")
        if not isinstance(runs, list) or not runs:
            return False

        # Check each run has required fields
        for run in runs:
            if not isinstance(run, dict):
                return False

            # Tool driver is required
            tool = run.get("tool")
            if not isinstance(tool, dict):
                return False

            driver = tool.get("driver")
            if not isinstance(driver, dict):
                return False

            if "name" not in driver:
                return False

            # Results should be a list (can be empty)
            results = run.get("results")
            if results is not None and not isinstance(results, list):
                return False

        return True

    def sarif_level_to_severity(
        self, level: str, is_security: bool = False
    ) -> str:
        """Convert SARIF level to VKG severity.

        Args:
            level: SARIF level (error/warning/note/none)
            is_security: Whether this is a security-related finding

        Returns:
            VKG severity string
        """
        level_lower = level.lower()
        level_map = self.LEVEL_SEVERITY_MAP.get(level_lower, {"default": "medium"})

        if is_security and "security" in level_map:
            return level_map["security"]
        return level_map.get("default", "medium")

    def severity_to_sarif_level(self, severity: str) -> str:
        """Convert VKG severity to SARIF level.

        Args:
            severity: VKG severity (critical/high/medium/low/info)

        Returns:
            SARIF level string
        """
        return self.SEVERITY_TO_LEVEL.get(severity.lower(), "warning")

    def _finding_to_rule(self, finding: VKGFinding) -> Dict[str, Any]:
        """Convert finding to SARIF rule definition.

        Args:
            finding: VKG finding

        Returns:
            SARIF rule object
        """
        rule: Dict[str, Any] = {
            "id": finding.rule_id,
            "name": finding.rule_id.replace("-", " ").title(),
            "shortDescription": {"text": finding.title[:200] if finding.title else ""},
            "fullDescription": {"text": finding.description},
            "defaultConfiguration": {
                "level": self.severity_to_sarif_level(finding.severity),
            },
            "properties": {
                "category": finding.category,
                "severity": finding.severity,
            },
        }

        if finding.vkg_pattern:
            rule["properties"]["vkgPattern"] = finding.vkg_pattern

        return rule

    def _finding_to_result(
        self, finding: VKGFinding, include_raw: bool = False
    ) -> Dict[str, Any]:
        """Convert VKG finding to SARIF result.

        Args:
            finding: VKG finding to convert
            include_raw: Whether to include raw data

        Returns:
            SARIF result object
        """
        result: Dict[str, Any] = {
            "ruleId": finding.rule_id,
            "level": self.severity_to_sarif_level(finding.severity),
            "message": {
                "text": finding.description or finding.title,
            },
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": finding.file,
                        },
                        "region": self._build_region(finding),
                    },
                }
            ],
            "fingerprints": {
                "primaryLocationLineHash": finding.id,
            },
        }

        # Add logical location if we have function/contract info
        if finding.function or finding.contract:
            result["locations"][0]["logicalLocations"] = [
                self._build_logical_location(finding)
            ]

        # Add properties
        properties: Dict[str, Any] = {
            "confidence": finding.confidence,
            "toolConfidence": finding.tool_confidence,
            "category": finding.category,
        }
        if finding.vkg_pattern:
            properties["vkgPattern"] = finding.vkg_pattern
        if finding.fix_suggestion:
            properties["fixSuggestion"] = finding.fix_suggestion
        if include_raw and finding.raw:
            properties["raw"] = finding.raw

        result["properties"] = properties

        return result

    def _build_region(self, finding: VKGFinding) -> Dict[str, Any]:
        """Build SARIF region from finding.

        Args:
            finding: VKG finding

        Returns:
            SARIF region object
        """
        region: Dict[str, int] = {
            "startLine": finding.line,
        }
        if finding.end_line:
            region["endLine"] = finding.end_line
        if finding.column:
            region["startColumn"] = finding.column

        return region

    def _build_logical_location(self, finding: VKGFinding) -> Dict[str, Any]:
        """Build SARIF logical location from finding.

        Args:
            finding: VKG finding

        Returns:
            SARIF logical location object
        """
        location: Dict[str, Any] = {}

        if finding.function:
            location["name"] = finding.function
            location["kind"] = "function"
            if finding.contract:
                location["fullyQualifiedName"] = f"{finding.contract}.{finding.function}"
        elif finding.contract:
            location["name"] = finding.contract
            location["kind"] = "module"

        return location

    def _build_rules_index(
        self, run: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """Build index of rules from SARIF run.

        Args:
            run: SARIF run object

        Returns:
            Dictionary mapping rule ID to rule definition
        """
        rules_index: Dict[str, Dict[str, Any]] = {}
        driver = run.get("tool", {}).get("driver", {})
        rules = driver.get("rules", [])

        for rule in rules:
            rule_id = rule.get("id", "")
            if rule_id:
                rules_index[rule_id] = rule

        return rules_index

    def _result_to_finding(
        self,
        result: Dict[str, Any],
        tool_name: str,
        rules: Dict[str, Dict[str, Any]],
    ) -> Optional[VKGFinding]:
        """Convert SARIF result to VKG finding.

        Args:
            result: SARIF result object
            tool_name: Source tool name
            rules: Rules index for the run

        Returns:
            VKGFinding or None if conversion fails
        """
        rule_id = result.get("ruleId", "unknown")
        rule = rules.get(rule_id, {})

        # Extract location info
        locations = result.get("locations", [])
        file_path = ""
        line = 0
        end_line = None
        column = None
        function = None
        contract = None

        if locations:
            loc = locations[0]
            phys = loc.get("physicalLocation", {})
            artifact = phys.get("artifactLocation", {})
            file_path = artifact.get("uri", "")

            region = phys.get("region", {})
            line = region.get("startLine", 0)
            end_line = region.get("endLine")
            column = region.get("startColumn")

            # Extract logical location
            logical_locs = loc.get("logicalLocations", [])
            if logical_locs:
                logical = logical_locs[0]
                fqn = logical.get("fullyQualifiedName", "")
                if "." in fqn:
                    parts = fqn.split(".")
                    contract = parts[0]
                    function = parts[1] if len(parts) > 1 else None
                elif logical.get("kind") == "function":
                    function = logical.get("name")
                elif logical.get("kind") == "module":
                    contract = logical.get("name")

        # Get severity from level
        level = result.get("level", "warning")
        properties = result.get("properties", {})
        is_security = properties.get("category", "").lower() in [
            "security", "vulnerability", "reentrancy", "access_control"
        ]
        severity = properties.get("severity") or self.sarif_level_to_severity(
            level, is_security
        )

        # Get category
        rule_props = rule.get("properties", {})
        category = properties.get("category") or rule_props.get("category", "unknown")

        # Get descriptions
        message = result.get("message", {})
        description = message.get("text", "")
        title = rule.get("shortDescription", {}).get("text", "")
        if not title:
            title = description[:200] if description else rule_id

        # Get confidence
        confidence = properties.get("confidence", 0.7)
        tool_confidence = properties.get("toolConfidence", "Medium")

        # Get VKG pattern
        vkg_pattern = properties.get("vkgPattern") or rule_props.get("vkgPattern")

        return VKGFinding(
            id=result.get("fingerprints", {}).get("primaryLocationLineHash", ""),
            source=tool_name,
            rule_id=rule_id,
            title=title,
            description=description,
            severity=severity,
            category=category,
            file=file_path,
            line=line,
            end_line=end_line,
            column=column,
            function=function,
            contract=contract,
            confidence=confidence,
            tool_confidence=tool_confidence,
            raw=properties.get("raw", {}),
            vkg_pattern=vkg_pattern,
            fix_suggestion=properties.get("fixSuggestion"),
        )


# Module-level convenience functions
_default_adapter = SARIFAdapter()


def sarif_to_vkg_findings(sarif: Union[Dict[str, Any], str]) -> List[VKGFinding]:
    """Convert SARIF document to VKG findings.

    Convenience function using default adapter.

    Args:
        sarif: SARIF document as dict or JSON string

    Returns:
        List of VKG findings
    """
    if isinstance(sarif, str):
        sarif = json.loads(sarif)
    return _default_adapter.from_sarif(sarif)


def vkg_findings_to_sarif(
    findings: List[VKGFinding],
    tool_name: str = "vkg",
    tool_version: str = "1.0.0",
) -> Dict[str, Any]:
    """Convert VKG findings to SARIF document.

    Convenience function using default adapter.

    Args:
        findings: List of VKG findings
        tool_name: Name of source tool
        tool_version: Version of source tool

    Returns:
        SARIF 2.1.0 document
    """
    return _default_adapter.to_sarif(findings, tool_name, tool_version)


def validate_sarif(sarif: Dict[str, Any]) -> bool:
    """Validate SARIF document structure.

    Args:
        sarif: SARIF document to validate

    Returns:
        True if valid
    """
    return _default_adapter.validate_sarif(sarif)


__all__ = [
    "SARIF_VERSION",
    "SARIF_SCHEMA",
    "VKGFinding",
    "SARIFAdapter",
    "sarif_to_vkg_findings",
    "vkg_findings_to_sarif",
    "validate_sarif",
]
