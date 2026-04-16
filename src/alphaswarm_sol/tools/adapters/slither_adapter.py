"""Slither Adapter - JSON to SARIF/VKG Conversion.

Parses Slither JSON output and converts to SARIF 2.1.0 or VKG internal format.
Provides detector-to-pattern mapping for cross-tool correlation.

Slither is the most widely-used Solidity static analyzer, detecting:
- Reentrancy vulnerabilities
- Access control issues
- State variable shadowing
- Dangerous patterns
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from alphaswarm_sol.tools.adapters.sarif import (
    SARIF_SCHEMA,
    SARIF_VERSION,
    SARIFAdapter,
    VKGFinding,
)


logger = logging.getLogger(__name__)


class SlitherAdapter:
    """Adapter for Slither JSON output.

    Converts Slither's native JSON format to SARIF 2.1.0 and VKGFinding.
    Maps Slither detectors to VKG pattern IDs for correlation.

    Example:
        >>> adapter = SlitherAdapter()
        >>> findings = adapter.parse_json(slither_output)
        >>> vkg_findings = adapter.to_vkg_findings(findings)
        >>> sarif = adapter.to_sarif(findings)
    """

    # Slither detector to VKG pattern mapping
    DETECTOR_TO_PATTERN: Dict[str, str] = {
        # Reentrancy patterns
        "reentrancy-eth": "reentrancy-classic",
        "reentrancy-no-eth": "reentrancy-state",
        "reentrancy-benign": "reentrancy-benign",
        "reentrancy-events": "reentrancy-events",
        "reentrancy-unlimited-gas": "reentrancy-unlimited-gas",
        # Access control patterns
        "arbitrary-send-eth": "access-control-permissive",
        "arbitrary-send-erc20": "access-control-permissive",
        "arbitrary-send-erc20-permit": "access-control-permissive",
        "protected-vars": "access-control-missing",
        "unprotected-upgrade": "upgrade-unprotected",
        "suicidal": "selfdestruct-unprotected",
        "tx-origin": "tx-origin-auth",
        # Delegation patterns
        "controlled-delegatecall": "delegatecall-injection",
        "delegatecall-loop": "delegatecall-loop",
        # Return value patterns
        "unchecked-transfer": "unchecked-return",
        "unchecked-lowlevel": "unchecked-low-level",
        "unchecked-send": "unchecked-send",
        # Arithmetic patterns
        "divide-before-multiply": "arithmetic-precision-loss",
        "incorrect-shift": "arithmetic-incorrect-shift",
        # State patterns
        "write-after-write": "state-double-write",
        "incorrect-equality": "state-strict-equality",
        "locked-ether": "locked-funds",
        "uninitialized-state": "state-uninitialized",
        "uninitialized-local": "state-uninitialized-local",
        "uninitialized-storage": "state-uninitialized-storage",
        # Time patterns
        "timestamp": "timestamp-dependence",
        "weak-prng": "weak-randomness",
        "block-timestamp": "timestamp-dependence",
        # External call patterns
        "calls-loop": "dos-external-call-loop",
        "low-level-calls": "low-level-call",
        "multiple-constructors": "constructor-multiple",
        "msg-value-loop": "msg-value-loop",
        # ERC patterns
        "erc20-interface": "erc20-interface-violation",
        "erc721-interface": "erc721-interface-violation",
        # Shadowing patterns
        "shadowing-state": "state-shadowing",
        "shadowing-local": "local-shadowing",
        "shadowing-builtin": "builtin-shadowing",
        "shadowing-abstract": "abstract-shadowing",
        # Naming patterns
        "naming-convention": "naming-convention",
        "similar-names": "similar-names",
        # Assembly patterns
        "assembly": "assembly-usage",
        "incorrect-return": "return-incorrect",
        # Storage patterns
        "storage-array": "storage-array-issue",
        "array-by-reference": "array-reference-issue",
        # Miscellaneous
        "constant-function-asm": "constant-function-asm",
        "constant-function-state": "constant-function-state",
        "dead-code": "dead-code",
        "unused-state": "unused-state",
        "unused-return": "unused-return",
        "void-cst": "void-constructor",
        "missing-zero-check": "missing-zero-check",
        "boolean-cst": "boolean-constant",
        "boolean-equal": "boolean-equality",
        "deprecated-standards": "deprecated-standards",
        "encode-packed-collision": "encode-packed-collision",
        "incorrect-modifier": "modifier-incorrect",
        "mapping-deletion": "mapping-deletion",
        "pragma": "pragma-version",
        "public-mappings-nested": "public-mapping-nested",
        "reentrancy-no-eth-send": "reentrancy-state",
        "reused-constructor": "constructor-reused",
        "rtlo": "rtlo-character",
        "solc-version": "solc-version",
        "too-many-digits": "too-many-digits",
        "tx-gasprice-manipulation": "gas-price-manipulation",
        "unimplemented-functions": "unimplemented-functions",
        "variable-scope": "variable-scope",
    }

    # Slither detector to category mapping
    DETECTOR_TO_CATEGORY: Dict[str, str] = {
        # Reentrancy
        "reentrancy-eth": "reentrancy",
        "reentrancy-no-eth": "reentrancy",
        "reentrancy-benign": "reentrancy",
        "reentrancy-events": "reentrancy",
        "reentrancy-unlimited-gas": "reentrancy",
        # Access control
        "arbitrary-send-eth": "access_control",
        "arbitrary-send-erc20": "access_control",
        "arbitrary-send-erc20-permit": "access_control",
        "protected-vars": "access_control",
        "unprotected-upgrade": "access_control",
        "suicidal": "access_control",
        "tx-origin": "access_control",
        # Delegation
        "controlled-delegatecall": "delegation",
        "delegatecall-loop": "delegation",
        # Return values
        "unchecked-transfer": "unchecked_return",
        "unchecked-lowlevel": "unchecked_return",
        "unchecked-send": "unchecked_return",
        # Arithmetic
        "divide-before-multiply": "arithmetic",
        "incorrect-shift": "arithmetic",
        # State
        "write-after-write": "state",
        "incorrect-equality": "state",
        "locked-ether": "locked_funds",
        "uninitialized-state": "initialization",
        "uninitialized-local": "initialization",
        "uninitialized-storage": "initialization",
        # Time
        "timestamp": "time_manipulation",
        "weak-prng": "randomness",
        "block-timestamp": "time_manipulation",
        # DOS
        "calls-loop": "dos",
        "msg-value-loop": "dos",
        # External calls
        "low-level-calls": "external_calls",
        # ERC standards
        "erc20-interface": "erc_compliance",
        "erc721-interface": "erc_compliance",
        # Code quality
        "shadowing-state": "shadowing",
        "shadowing-local": "shadowing",
        "shadowing-builtin": "shadowing",
        "shadowing-abstract": "shadowing",
        "naming-convention": "code_style",
        "similar-names": "code_style",
        "dead-code": "code_quality",
        "unused-state": "code_quality",
        "unused-return": "code_quality",
        "deprecated-standards": "code_quality",
        "pragma": "code_quality",
        "solc-version": "code_quality",
    }

    # Slither confidence to numeric mapping
    CONFIDENCE_MAP: Dict[str, float] = {
        "High": 0.9,
        "Medium": 0.7,
        "Low": 0.5,
        "Informational": 0.3,
    }

    # Slither impact to VKG severity mapping
    IMPACT_TO_SEVERITY: Dict[str, str] = {
        "High": "high",
        "Medium": "medium",
        "Low": "low",
        "Informational": "info",
        "Optimization": "info",
    }

    def __init__(self) -> None:
        """Initialize the Slither adapter."""
        self._sarif_adapter = SARIFAdapter()

    def parse_json(self, output: str) -> List[Dict[str, Any]]:
        """Parse Slither JSON output.

        Handles both detector results and printers output format.

        Args:
            output: JSON string from Slither

        Returns:
            List of raw result dictionaries

        Raises:
            ValueError: If JSON parsing fails
        """
        if not output or not output.strip():
            return []

        try:
            data = json.loads(output)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Slither JSON: {e}")
            raise ValueError(f"Invalid Slither JSON output: {e}") from e

        # Handle different Slither output formats
        if isinstance(data, dict):
            # Standard format: {"results": {"detectors": [...]}}
            if "results" in data and "detectors" in data["results"]:
                return data["results"]["detectors"]
            # Legacy format: {"detectors": [...]}
            if "detectors" in data:
                return data["detectors"]
            # Direct results array
            if "results" in data and isinstance(data["results"], list):
                return data["results"]
        elif isinstance(data, list):
            # Direct array of results
            return data

        logger.warning("Unexpected Slither JSON format, returning empty list")
        return []

    def to_vkg_findings(
        self,
        raw: List[Dict[str, Any]],
        source_file: Optional[str] = None,
    ) -> List[VKGFinding]:
        """Convert Slither raw results to VKG findings.

        Args:
            raw: List of Slither result dictionaries
            source_file: Optional override for source file path

        Returns:
            List of VKGFinding instances
        """
        findings: List[VKGFinding] = []

        for result in raw:
            finding = self._result_to_finding(result, source_file)
            if finding:
                findings.append(finding)

        return findings

    def to_sarif(
        self,
        raw: List[Dict[str, Any]],
        version: str = "0.0.0",
    ) -> Dict[str, Any]:
        """Convert Slither raw results to SARIF format.

        Args:
            raw: List of Slither result dictionaries
            version: Slither version string

        Returns:
            SARIF 2.1.0 document
        """
        findings = self.to_vkg_findings(raw)
        return self._sarif_adapter.to_sarif(findings, "slither", version)

    def get_vkg_pattern(self, detector: str) -> Optional[str]:
        """Get VKG pattern ID for a Slither detector.

        Args:
            detector: Slither detector name

        Returns:
            VKG pattern ID or None if not mapped
        """
        return self.DETECTOR_TO_PATTERN.get(detector)

    def get_category(self, detector: str) -> str:
        """Get category for a Slither detector.

        Args:
            detector: Slither detector name

        Returns:
            Category string
        """
        return self.DETECTOR_TO_CATEGORY.get(detector, "unknown")

    def _result_to_finding(
        self,
        result: Dict[str, Any],
        source_file: Optional[str] = None,
    ) -> Optional[VKGFinding]:
        """Convert single Slither result to VKGFinding.

        Args:
            result: Slither result dictionary
            source_file: Optional override for source file path

        Returns:
            VKGFinding or None if conversion fails
        """
        try:
            # Get detector info
            detector = result.get("check", result.get("detector", "unknown"))
            impact = result.get("impact", "Medium")
            confidence = result.get("confidence", "Medium")

            # Extract location from elements
            elements = result.get("elements", [])
            file_path = source_file or ""
            line = 0
            end_line = None
            function_name = None
            contract_name = None

            if elements:
                first_elem = elements[0]

                # Get source mapping
                source_mapping = first_elem.get("source_mapping", {})
                if source_mapping:
                    file_path = source_file or source_mapping.get(
                        "filename_relative",
                        source_mapping.get("filename", ""),
                    )
                    lines = source_mapping.get("lines", [])
                    if lines:
                        line = lines[0]
                        if len(lines) > 1:
                            end_line = lines[-1]

                # Get function/contract from element type
                elem_type = first_elem.get("type", "")
                if elem_type == "function":
                    function_name = first_elem.get("name")
                    # Try to get contract from additional context
                    type_specific = first_elem.get("type_specific_fields", {})
                    parent = type_specific.get("parent", {})
                    if parent.get("type") == "contract":
                        contract_name = parent.get("name")
                elif elem_type == "contract":
                    contract_name = first_elem.get("name")

                # Try to extract function from any element
                if not function_name:
                    for elem in elements:
                        if elem.get("type") == "function":
                            function_name = elem.get("name")
                            break

                # Extract contract from any element
                if not contract_name:
                    for elem in elements:
                        if elem.get("type") == "contract":
                            contract_name = elem.get("name")
                            break

            # Handle case where we have no location
            if not file_path and not line:
                logger.debug(f"Skipping finding with no location: {detector}")
                # Still create finding for aggregate reports
                file_path = "unknown"
                line = 0

            # Get description (truncate for title)
            description = result.get("description", "")
            title = description[:200] + "..." if len(description) > 200 else description

            # Map severity and confidence
            severity = self.IMPACT_TO_SEVERITY.get(impact, "medium")
            confidence_score = self.CONFIDENCE_MAP.get(confidence, 0.7)

            return VKGFinding(
                source="slither",
                rule_id=detector,
                title=title,
                description=description,
                severity=severity,
                category=self.get_category(detector),
                file=file_path,
                line=line,
                end_line=end_line,
                function=function_name,
                contract=contract_name,
                confidence=confidence_score,
                tool_confidence=confidence,
                raw=result,
                vkg_pattern=self.get_vkg_pattern(detector),
            )

        except Exception as e:
            logger.error(f"Failed to convert Slither result: {e}")
            return None

    @classmethod
    def get_supported_detectors(cls) -> List[str]:
        """Get list of all supported Slither detectors.

        Returns:
            List of detector names with VKG pattern mappings
        """
        return list(cls.DETECTOR_TO_PATTERN.keys())

    @classmethod
    def get_unmapped_detector(cls, detector: str) -> Dict[str, Any]:
        """Get info for an unmapped detector.

        Useful for identifying detectors that need mapping.

        Args:
            detector: Detector name

        Returns:
            Dictionary with detector info and suggestions
        """
        return {
            "detector": detector,
            "has_pattern": detector in cls.DETECTOR_TO_PATTERN,
            "has_category": detector in cls.DETECTOR_TO_CATEGORY,
            "suggested_category": cls._suggest_category(detector),
        }

    @classmethod
    def _suggest_category(cls, detector: str) -> str:
        """Suggest category for an unmapped detector.

        Args:
            detector: Detector name

        Returns:
            Suggested category based on name heuristics
        """
        detector_lower = detector.lower()

        if "reentrancy" in detector_lower:
            return "reentrancy"
        if "delegate" in detector_lower:
            return "delegation"
        if any(x in detector_lower for x in ["access", "auth", "owner", "admin"]):
            return "access_control"
        if any(x in detector_lower for x in ["math", "arithmetic", "overflow"]):
            return "arithmetic"
        if any(x in detector_lower for x in ["time", "block", "timestamp"]):
            return "time_manipulation"
        if any(x in detector_lower for x in ["dos", "loop", "gas"]):
            return "dos"
        if any(x in detector_lower for x in ["erc20", "erc721", "erc1155"]):
            return "erc_compliance"

        return "unknown"


def slither_to_sarif(
    output: str,
    version: str = "0.0.0",
) -> Dict[str, Any]:
    """Convenience function to convert Slither output to SARIF.

    Args:
        output: Slither JSON output string
        version: Slither version

    Returns:
        SARIF 2.1.0 document
    """
    adapter = SlitherAdapter()
    raw = adapter.parse_json(output)
    return adapter.to_sarif(raw, version)


def slither_to_vkg_findings(output: str) -> List[VKGFinding]:
    """Convenience function to convert Slither output to VKG findings.

    Args:
        output: Slither JSON output string

    Returns:
        List of VKGFinding instances
    """
    adapter = SlitherAdapter()
    raw = adapter.parse_json(output)
    return adapter.to_vkg_findings(raw)


__all__ = [
    "SlitherAdapter",
    "slither_to_sarif",
    "slither_to_vkg_findings",
]
