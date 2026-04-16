"""Mythril Adapter - JSON to SARIF/VKG Conversion.

Parses Mythril JSONv2 output and converts to SARIF 2.1.0 or VKG internal format.
Provides SWC ID to pattern mapping for cross-tool correlation.

Mythril is a symbolic execution tool for EVM bytecode, detecting:
- Integer overflow/underflow
- Reentrancy vulnerabilities
- Unprotected SELFDESTRUCT
- Arbitrary code execution
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


class MythrilAdapter:
    """Adapter for Mythril JSONv2 output.

    Converts Mythril's JSONv2 format to SARIF 2.1.0 and VKGFinding.
    Maps SWC IDs to VKG pattern IDs for correlation.

    Mythril uses SWC (Smart Contract Weakness Classification) IDs.
    See: https://swcregistry.io/

    Example:
        >>> adapter = MythrilAdapter()
        >>> findings = adapter.parse_json(mythril_output)
        >>> vkg_findings = adapter.to_vkg_findings(findings)
        >>> sarif = adapter.to_sarif(findings)
    """

    # SWC ID to VKG pattern mapping
    SWC_TO_PATTERN: Dict[str, str] = {
        # Integer
        "SWC-101": "arithmetic-overflow",  # Integer Overflow and Underflow
        # Access Control
        "SWC-102": "access-control-missing",  # Outdated Compiler Version (deprecated)
        "SWC-103": "floating-pragma",  # Floating Pragma
        "SWC-104": "unchecked-return",  # Unchecked Call Return Value
        "SWC-105": "access-control-missing",  # Unprotected Ether Withdrawal
        "SWC-106": "selfdestruct-unprotected",  # Unprotected SELFDESTRUCT
        # Reentrancy
        "SWC-107": "reentrancy-classic",  # Reentrancy
        # State
        "SWC-108": "state-uninitialized",  # State Variable Default Visibility
        "SWC-109": "state-uninitialized",  # Uninitialized Storage Pointer
        # Assertions
        "SWC-110": "assert-violation",  # Assert Violation
        "SWC-111": "deprecated-standards",  # Use of Deprecated Solidity Functions
        # Delegation
        "SWC-112": "delegatecall-injection",  # Delegatecall to Untrusted Callee
        # DOS
        "SWC-113": "dos-gas-limit",  # DoS with Failed Call
        "SWC-114": "dos-block-gas",  # Transaction Order Dependence
        # Authorization
        "SWC-115": "tx-origin-auth",  # Authorization through tx.origin
        # Time
        "SWC-116": "timestamp-dependence",  # Block values as a proxy for time
        # Signature
        "SWC-117": "signature-malleability",  # Signature Malleability
        # Constructors
        "SWC-118": "constructor-typo",  # Incorrect Constructor Name
        "SWC-119": "shadowing-state",  # Shadowing State Variables
        # Return values
        "SWC-120": "weak-randomness",  # Weak Sources of Randomness
        "SWC-121": "eip-compliance",  # Missing Protection against Signature Replay
        "SWC-122": "unchecked-return",  # Lack of Proper Signature Verification
        "SWC-123": "eip-compliance",  # Requirement Violation
        "SWC-124": "write-to-arbitrary-storage",  # Write to Arbitrary Storage Location
        "SWC-125": "arbitrary-jump",  # Incorrect Inheritance Order
        "SWC-126": "ether-lost",  # Insufficient Gas Griefing
        "SWC-127": "arbitrary-jump",  # Arbitrary Jump with Function Type Variable
        "SWC-128": "dos-block-gas",  # DoS With Block Gas Limit
        "SWC-129": "constructor-typo",  # Typographical Error
        "SWC-130": "assert-state-change",  # Right-To-Left-Override control character
        "SWC-131": "shadowing-builtin",  # Presence of unused variables
        "SWC-132": "unexpected-ether",  # Unexpected Ether balance
        "SWC-133": "hash-collision",  # Hash Collisions With Multiple Variable Length Args
        "SWC-134": "msg-value-loop",  # Message call with hardcoded gas amount
        "SWC-135": "gas-price-manipulation",  # Code With No Effects
        "SWC-136": "unchecked-return",  # Unencrypted Private Data On-Chain
    }

    # SWC ID to category mapping
    SWC_TO_CATEGORY: Dict[str, str] = {
        "SWC-101": "arithmetic",
        "SWC-102": "code_quality",
        "SWC-103": "code_quality",
        "SWC-104": "unchecked_return",
        "SWC-105": "access_control",
        "SWC-106": "access_control",
        "SWC-107": "reentrancy",
        "SWC-108": "state",
        "SWC-109": "state",
        "SWC-110": "assertion",
        "SWC-111": "code_quality",
        "SWC-112": "delegation",
        "SWC-113": "dos",
        "SWC-114": "frontrunning",
        "SWC-115": "access_control",
        "SWC-116": "time_manipulation",
        "SWC-117": "signature",
        "SWC-118": "initialization",
        "SWC-119": "shadowing",
        "SWC-120": "randomness",
        "SWC-121": "signature",
        "SWC-122": "signature",
        "SWC-123": "assertion",
        "SWC-124": "storage",
        "SWC-125": "inheritance",
        "SWC-126": "dos",
        "SWC-127": "control_flow",
        "SWC-128": "dos",
        "SWC-129": "code_quality",
        "SWC-130": "code_quality",
        "SWC-131": "code_quality",
        "SWC-132": "unexpected_state",
        "SWC-133": "encoding",
        "SWC-134": "dos",
        "SWC-135": "code_quality",
        "SWC-136": "privacy",
    }

    # Mythril severity to VKG severity mapping
    SEVERITY_MAP: Dict[str, str] = {
        "High": "high",
        "Medium": "medium",
        "Low": "low",
        "Informational": "info",
    }

    # Confidence based on severity
    CONFIDENCE_MAP: Dict[str, float] = {
        "high": 0.85,
        "medium": 0.7,
        "low": 0.5,
        "info": 0.3,
    }

    def __init__(self) -> None:
        """Initialize the Mythril adapter."""
        self._sarif_adapter = SARIFAdapter()

    def parse_json(self, output: str) -> List[Dict[str, Any]]:
        """Parse Mythril JSONv2 output.

        Args:
            output: JSON string from Mythril

        Returns:
            List of raw issue dictionaries

        Raises:
            ValueError: If JSON parsing fails
        """
        if not output or not output.strip():
            return []

        try:
            data = json.loads(output)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Mythril JSON: {e}")
            raise ValueError(f"Invalid Mythril JSON output: {e}") from e

        # Handle JSONv2 format
        if isinstance(data, dict):
            # Standard format: {"issues": [...]}
            if "issues" in data:
                return data["issues"]
            # Error format
            if "error" in data:
                logger.warning(f"Mythril reported error: {data['error']}")
                return []
            # Success with empty results
            if data.get("success", False) and "issues" not in data:
                return []
        elif isinstance(data, list):
            # Direct array of issues
            return data

        logger.warning("Unexpected Mythril JSON format, returning empty list")
        return []

    def to_vkg_findings(
        self,
        raw: List[Dict[str, Any]],
    ) -> List[VKGFinding]:
        """Convert Mythril raw issues to VKG findings.

        Args:
            raw: List of Mythril issue dictionaries

        Returns:
            List of VKGFinding instances
        """
        findings: List[VKGFinding] = []

        for issue in raw:
            finding = self._issue_to_finding(issue)
            if finding:
                findings.append(finding)

        return findings

    def to_sarif(
        self,
        raw: List[Dict[str, Any]],
        version: str = "0.0.0",
    ) -> Dict[str, Any]:
        """Convert Mythril raw issues to SARIF format.

        Args:
            raw: List of Mythril issue dictionaries
            version: Mythril version string

        Returns:
            SARIF 2.1.0 document
        """
        findings = self.to_vkg_findings(raw)
        return self._sarif_adapter.to_sarif(findings, "mythril", version)

    def get_vkg_pattern(self, swc_id: str) -> Optional[str]:
        """Get VKG pattern ID for a SWC ID.

        Args:
            swc_id: SWC identifier (e.g., "SWC-107")

        Returns:
            VKG pattern ID or None if not mapped
        """
        return self.SWC_TO_PATTERN.get(swc_id)

    def get_category(self, swc_id: str) -> str:
        """Get category for a SWC ID.

        Args:
            swc_id: SWC identifier

        Returns:
            Category string
        """
        return self.SWC_TO_CATEGORY.get(swc_id, "unknown")

    def _issue_to_finding(
        self,
        issue: Dict[str, Any],
    ) -> Optional[VKGFinding]:
        """Convert Mythril issue to VKGFinding.

        Args:
            issue: Mythril issue dictionary

        Returns:
            VKGFinding or None if conversion fails
        """
        try:
            # Extract SWC info
            swc_id = issue.get("swc-id", "")
            if not swc_id and "swc_id" in issue:
                swc_id = issue["swc_id"]

            # Normalize SWC ID format
            if swc_id and not swc_id.startswith("SWC-"):
                swc_id = f"SWC-{swc_id}"

            swc_title = issue.get("title", issue.get("swc-title", ""))

            # Extract severity
            severity_raw = issue.get("severity", "Medium")
            severity = self.SEVERITY_MAP.get(severity_raw, "medium")

            # Extract location
            file_path = issue.get("filename", "")
            if not file_path:
                # Try to get from sourceMap
                source_map = issue.get("sourceMap", "")
                if source_map:
                    file_path = self._parse_source_map(source_map)

            line_no = issue.get("lineno", 0)
            if not line_no and "line" in issue:
                line_no = issue["line"]

            # Extract contract/function
            contract = issue.get("contract", "")
            function = issue.get("function", "")

            # Handle code snippet for context
            code = issue.get("code", "")

            # Build description
            description = issue.get("description", "")
            if code and code not in description:
                description = f"{description}\n\nCode: {code}" if description else code

            # Build title
            title = swc_title or swc_id or "Unknown Issue"

            confidence = self.CONFIDENCE_MAP.get(severity, 0.7)

            return VKGFinding(
                source="mythril",
                rule_id=swc_id or "unknown",
                title=title,
                description=description or title,
                severity=severity,
                category=self.get_category(swc_id) if swc_id else "unknown",
                file=file_path or "unknown",
                line=line_no,
                function=function or None,
                contract=contract or None,
                confidence=confidence,
                tool_confidence=severity_raw,
                raw=issue,
                vkg_pattern=self.get_vkg_pattern(swc_id) if swc_id else None,
            )

        except Exception as e:
            logger.error(f"Failed to convert Mythril issue: {e}")
            return None

    def _parse_source_map(self, source_map: str) -> str:
        """Parse Mythril source map to extract filename.

        Args:
            source_map: Source map string

        Returns:
            Filename or empty string
        """
        # Source map format: "offset:length:file_index:jump"
        # We need to handle various formats
        if ":" in source_map:
            parts = source_map.split(":")
            # Try to find a .sol file reference
            for part in parts:
                if ".sol" in part:
                    return part

        return ""

    @classmethod
    def get_supported_swc_ids(cls) -> List[str]:
        """Get list of all supported SWC IDs.

        Returns:
            List of SWC IDs with VKG pattern mappings
        """
        return list(cls.SWC_TO_PATTERN.keys())

    @classmethod
    def swc_id_to_url(cls, swc_id: str) -> str:
        """Get SWC registry URL for an ID.

        Args:
            swc_id: SWC identifier

        Returns:
            URL to SWC registry entry
        """
        # Extract numeric part
        num = swc_id.replace("SWC-", "")
        return f"https://swcregistry.io/docs/SWC-{num}"


def mythril_to_sarif(
    output: str,
    version: str = "0.0.0",
) -> Dict[str, Any]:
    """Convenience function to convert Mythril output to SARIF.

    Args:
        output: Mythril JSON output string
        version: Mythril version

    Returns:
        SARIF 2.1.0 document
    """
    adapter = MythrilAdapter()
    raw = adapter.parse_json(output)
    return adapter.to_sarif(raw, version)


def mythril_to_vkg_findings(output: str) -> List[VKGFinding]:
    """Convenience function to convert Mythril output to VKG findings.

    Args:
        output: Mythril JSON output string

    Returns:
        List of VKGFinding instances
    """
    adapter = MythrilAdapter()
    raw = adapter.parse_json(output)
    return adapter.to_vkg_findings(raw)


__all__ = [
    "MythrilAdapter",
    "mythril_to_sarif",
    "mythril_to_vkg_findings",
]
