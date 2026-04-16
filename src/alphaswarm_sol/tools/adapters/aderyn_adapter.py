"""Aderyn Adapter - JSON to SARIF/VKG Conversion.

Parses Aderyn JSON output and converts to SARIF 2.1.0 or VKG internal format.
Provides detector-to-pattern mapping for cross-tool correlation.

Aderyn is a Rust-based Solidity static analyzer focused on:
- Security vulnerability detection
- Code quality issues
- Gas optimization suggestions
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from alphaswarm_sol.tools.adapters.sarif import (
    SARIFAdapter,
    VKGFinding,
)


logger = logging.getLogger(__name__)


class AderynAdapter:
    """Adapter for Aderyn JSON output.

    Converts Aderyn's native JSON format to SARIF 2.1.0 and VKGFinding.
    Maps Aderyn detectors to VKG pattern IDs for correlation.

    Aderyn organizes findings by severity:
    - high_issues: Critical security issues
    - medium_issues: Moderate security issues
    - low_issues: Minor issues
    - nc_issues: Non-critical/informational

    Example:
        >>> adapter = AderynAdapter()
        >>> findings = adapter.parse_json(aderyn_output)
        >>> vkg_findings = adapter.to_vkg_findings(findings)
        >>> sarif = adapter.to_sarif(findings)
    """

    # Aderyn detector to VKG pattern mapping
    DETECTOR_TO_PATTERN: Dict[str, str] = {
        # Reentrancy patterns
        "state-change-after-external-call": "reentrancy-state",
        "reentrancy": "reentrancy-classic",
        "reentrancy-state": "reentrancy-state",
        # Access control patterns
        "centralization-risk": "access-control-centralized",
        "unprotected-initializer": "access-control-missing-initializer",
        "missing-access-control": "access-control-missing",
        "unprotected-upgrade": "upgrade-unprotected",
        "selfdestruct": "selfdestruct-unprotected",
        "tx-origin-auth": "tx-origin-auth",
        # Arithmetic patterns
        "unsafe-casting": "arithmetic-unsafe-cast",
        "unchecked-math": "arithmetic-unchecked",
        "divide-before-multiply": "arithmetic-precision-loss",
        "integer-overflow": "arithmetic-overflow",
        # Return value patterns
        "unchecked-return-value": "unchecked-return",
        "unchecked-low-level": "unchecked-low-level",
        "unchecked-send": "unchecked-send",
        # Delegation patterns
        "delegatecall-in-loop": "delegatecall-loop",
        "controlled-delegatecall": "delegatecall-injection",
        # External call patterns
        "external-call-in-loop": "dos-external-call-loop",
        "low-level-call": "low-level-call",
        # Storage patterns
        "uninitialized-storage": "state-uninitialized-storage",
        "uninitialized-state-variable": "state-uninitialized",
        "storage-collision": "storage-collision",
        # Time patterns
        "weak-randomness": "weak-randomness",
        "timestamp-dependence": "timestamp-dependence",
        "block-timestamp": "timestamp-dependence",
        # ERC patterns
        "incorrect-erc20": "erc20-interface-violation",
        "incorrect-erc721": "erc721-interface-violation",
        "missing-erc20-return": "erc20-missing-return",
        # Code quality
        "dead-code": "dead-code",
        "unused-import": "unused-import",
        "unused-state-variable": "unused-state",
        "shadowing": "state-shadowing",
        "magic-number": "magic-number",
        "assembly-usage": "assembly-usage",
        "deprecated-functions": "deprecated-standards",
        # Gas optimization
        "gas-use-require-string": "gas-require-string",
        "gas-use-immutable": "gas-immutable",
        "gas-use-constant": "gas-constant",
        "gas-cache-array-length": "gas-array-length",
        "gas-state-variable-caching": "gas-state-caching",
        # Miscellaneous
        "missing-zero-address-check": "missing-zero-check",
        "floating-pragma": "pragma-version",
        "push-zero-optimization": "gas-push-zero",
        "missing-natspec": "missing-natspec",
        "public-vs-external": "gas-public-external",
    }

    # Aderyn detector to category mapping
    DETECTOR_TO_CATEGORY: Dict[str, str] = {
        # Reentrancy
        "state-change-after-external-call": "reentrancy",
        "reentrancy": "reentrancy",
        "reentrancy-state": "reentrancy",
        # Access control
        "centralization-risk": "access_control",
        "unprotected-initializer": "access_control",
        "missing-access-control": "access_control",
        "unprotected-upgrade": "access_control",
        "selfdestruct": "access_control",
        "tx-origin-auth": "access_control",
        # Arithmetic
        "unsafe-casting": "arithmetic",
        "unchecked-math": "arithmetic",
        "divide-before-multiply": "arithmetic",
        "integer-overflow": "arithmetic",
        # Return values
        "unchecked-return-value": "unchecked_return",
        "unchecked-low-level": "unchecked_return",
        "unchecked-send": "unchecked_return",
        # Delegation
        "delegatecall-in-loop": "delegation",
        "controlled-delegatecall": "delegation",
        # DOS
        "external-call-in-loop": "dos",
        # External calls
        "low-level-call": "external_calls",
        # Storage
        "uninitialized-storage": "initialization",
        "uninitialized-state-variable": "initialization",
        "storage-collision": "storage",
        # Time
        "weak-randomness": "randomness",
        "timestamp-dependence": "time_manipulation",
        "block-timestamp": "time_manipulation",
        # ERC
        "incorrect-erc20": "erc_compliance",
        "incorrect-erc721": "erc_compliance",
        "missing-erc20-return": "erc_compliance",
        # Code quality
        "dead-code": "code_quality",
        "unused-import": "code_quality",
        "unused-state-variable": "code_quality",
        "shadowing": "shadowing",
        "magic-number": "code_style",
        "assembly-usage": "code_quality",
        "deprecated-functions": "code_quality",
        # Gas
        "gas-use-require-string": "gas_optimization",
        "gas-use-immutable": "gas_optimization",
        "gas-use-constant": "gas_optimization",
        "gas-cache-array-length": "gas_optimization",
        "gas-state-variable-caching": "gas_optimization",
        "push-zero-optimization": "gas_optimization",
        "public-vs-external": "gas_optimization",
        # Misc
        "missing-zero-address-check": "validation",
        "floating-pragma": "code_quality",
        "missing-natspec": "documentation",
    }

    # Severity mapping for issue categories
    SEVERITY_MAP: Dict[str, str] = {
        "high_issues": "high",
        "medium_issues": "medium",
        "low_issues": "low",
        "nc_issues": "info",
    }

    # Confidence based on severity (Aderyn doesn't provide explicit confidence)
    CONFIDENCE_MAP: Dict[str, float] = {
        "high": 0.85,
        "medium": 0.7,
        "low": 0.5,
        "info": 0.3,
    }

    def __init__(self) -> None:
        """Initialize the Aderyn adapter."""
        self._sarif_adapter = SARIFAdapter()

    def parse_json(self, output: str) -> List[Dict[str, Any]]:
        """Parse Aderyn JSON output.

        Args:
            output: JSON string from Aderyn

        Returns:
            List of raw result dictionaries with severity attached

        Raises:
            ValueError: If JSON parsing fails
        """
        if not output or not output.strip():
            return []

        try:
            data = json.loads(output)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Aderyn JSON: {e}")
            raise ValueError(f"Invalid Aderyn JSON output: {e}") from e

        results: List[Dict[str, Any]] = []

        # Process each severity level
        for severity_key, severity in self.SEVERITY_MAP.items():
            issues_data = data.get(severity_key, {})
            issues = issues_data.get("issues", [])

            for issue in issues:
                # Attach severity to each issue
                issue["_severity"] = severity
                results.append(issue)

        return results

    def to_vkg_findings(
        self,
        raw: List[Dict[str, Any]],
    ) -> List[VKGFinding]:
        """Convert Aderyn raw results to VKG findings.

        Args:
            raw: List of Aderyn result dictionaries

        Returns:
            List of VKGFinding instances
        """
        findings: List[VKGFinding] = []

        for result in raw:
            # Each issue can have multiple instances
            detector = result.get("detector_name", "unknown")
            title = result.get("title", "")
            description = result.get("description", "")
            severity = result.get("_severity", "medium")
            instances = result.get("instances", [])

            for instance in instances:
                finding = self._instance_to_finding(
                    instance=instance,
                    detector=detector,
                    title=title,
                    description=description,
                    severity=severity,
                    raw_issue=result,
                )
                if finding:
                    findings.append(finding)

            # If no instances, create a finding from the issue itself
            if not instances:
                finding = self._create_issue_finding(
                    detector=detector,
                    title=title,
                    description=description,
                    severity=severity,
                    raw=result,
                )
                if finding:
                    findings.append(finding)

        return findings

    def to_sarif(
        self,
        raw: List[Dict[str, Any]],
        version: str = "0.0.0",
    ) -> Dict[str, Any]:
        """Convert Aderyn raw results to SARIF format.

        Args:
            raw: List of Aderyn result dictionaries
            version: Aderyn version string

        Returns:
            SARIF 2.1.0 document
        """
        findings = self.to_vkg_findings(raw)
        return self._sarif_adapter.to_sarif(findings, "aderyn", version)

    def get_vkg_pattern(self, detector: str) -> Optional[str]:
        """Get VKG pattern ID for an Aderyn detector.

        Args:
            detector: Aderyn detector name

        Returns:
            VKG pattern ID or None if not mapped
        """
        return self.DETECTOR_TO_PATTERN.get(detector)

    def get_category(self, detector: str) -> str:
        """Get category for an Aderyn detector.

        Args:
            detector: Aderyn detector name

        Returns:
            Category string
        """
        return self.DETECTOR_TO_CATEGORY.get(detector, "unknown")

    def _instance_to_finding(
        self,
        instance: Dict[str, Any],
        detector: str,
        title: str,
        description: str,
        severity: str,
        raw_issue: Dict[str, Any],
    ) -> Optional[VKGFinding]:
        """Convert Aderyn instance to VKGFinding.

        Args:
            instance: Instance dictionary with src field
            detector: Detector name
            title: Issue title
            description: Issue description
            severity: Severity level
            raw_issue: Original issue dictionary

        Returns:
            VKGFinding or None if conversion fails
        """
        try:
            # Parse src format: "file.sol:line:col"
            src = instance.get("src", "")
            file_path, line, column = self._parse_src(src)

            # Extract contract/function from instance if available
            contract_name = instance.get("contract")
            function_name = instance.get("function")

            # Try to extract from snippet context
            snippet = instance.get("snippet", "")
            if not function_name and "function " in snippet:
                # Extract function name from snippet
                match = re.search(r"function\s+(\w+)", snippet)
                if match:
                    function_name = match.group(1)

            confidence = self.CONFIDENCE_MAP.get(severity, 0.7)

            return VKGFinding(
                source="aderyn",
                rule_id=detector,
                title=title,
                description=description or title,
                severity=severity,
                category=self.get_category(detector),
                file=file_path,
                line=line,
                column=column,
                function=function_name,
                contract=contract_name,
                confidence=confidence,
                tool_confidence=severity.title(),
                raw=raw_issue,
                vkg_pattern=self.get_vkg_pattern(detector),
            )

        except Exception as e:
            logger.error(f"Failed to convert Aderyn instance: {e}")
            return None

    def _create_issue_finding(
        self,
        detector: str,
        title: str,
        description: str,
        severity: str,
        raw: Dict[str, Any],
    ) -> Optional[VKGFinding]:
        """Create a finding when no instances are provided.

        Args:
            detector: Detector name
            title: Issue title
            description: Issue description
            severity: Severity level
            raw: Raw issue data

        Returns:
            VKGFinding or None
        """
        confidence = self.CONFIDENCE_MAP.get(severity, 0.7)

        return VKGFinding(
            source="aderyn",
            rule_id=detector,
            title=title,
            description=description or title,
            severity=severity,
            category=self.get_category(detector),
            file="unknown",
            line=0,
            confidence=confidence,
            tool_confidence=severity.title(),
            raw=raw,
            vkg_pattern=self.get_vkg_pattern(detector),
        )

    def _parse_src(self, src: str) -> tuple[str, int, Optional[int]]:
        """Parse Aderyn src format.

        Args:
            src: Source location string (e.g., "file.sol:42:10")

        Returns:
            Tuple of (file_path, line, column)
        """
        if not src:
            return "unknown", 0, None

        parts = src.split(":")
        file_path = parts[0] if parts else "unknown"
        line = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        column = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None

        return file_path, line, column

    @classmethod
    def get_supported_detectors(cls) -> List[str]:
        """Get list of all supported Aderyn detectors.

        Returns:
            List of detector names with VKG pattern mappings
        """
        return list(cls.DETECTOR_TO_PATTERN.keys())


def aderyn_to_sarif(
    output: str,
    version: str = "0.0.0",
) -> Dict[str, Any]:
    """Convenience function to convert Aderyn output to SARIF.

    Args:
        output: Aderyn JSON output string
        version: Aderyn version

    Returns:
        SARIF 2.1.0 document
    """
    adapter = AderynAdapter()
    raw = adapter.parse_json(output)
    return adapter.to_sarif(raw, version)


def aderyn_to_vkg_findings(output: str) -> List[VKGFinding]:
    """Convenience function to convert Aderyn output to VKG findings.

    Args:
        output: Aderyn JSON output string

    Returns:
        List of VKGFinding instances
    """
    adapter = AderynAdapter()
    raw = adapter.parse_json(output)
    return adapter.to_vkg_findings(raw)


__all__ = [
    "AderynAdapter",
    "aderyn_to_sarif",
    "aderyn_to_vkg_findings",
]
