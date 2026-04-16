"""Semgrep Adapter - JSON to SARIF/VKG Conversion.

Parses Semgrep JSON output and converts to SARIF 2.1.0 or VKG internal format.
Maps Semgrep rule IDs (particularly Decurity smart-contracts rules) to VKG patterns.

Semgrep is a pattern-matching tool supporting custom rules for:
- Reentrancy patterns
- Access control issues
- Unsafe external calls
- Solidity-specific vulnerabilities
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from alphaswarm_sol.tools.adapters.sarif import (
    SARIFAdapter,
    VKGFinding,
)


logger = logging.getLogger(__name__)


class SemgrepAdapter:
    """Adapter for Semgrep JSON output.

    Converts Semgrep's JSON format to SARIF 2.1.0 and VKGFinding.
    Maps Semgrep rule IDs to VKG pattern IDs for correlation.

    Supports Decurity smart-contracts ruleset:
    https://github.com/Decurity/semgrep-smart-contracts

    Example:
        >>> adapter = SemgrepAdapter()
        >>> findings = adapter.parse_json(semgrep_output)
        >>> vkg_findings = adapter.to_vkg_findings(findings)
        >>> sarif = adapter.to_sarif(findings)
    """

    # Semgrep rule ID to VKG pattern mapping
    # Based on Decurity smart-contracts ruleset
    RULE_TO_PATTERN: Dict[str, str] = {
        # Reentrancy
        "solidity.security.reentrancy": "reentrancy-classic",
        "solidity.security.reentrancy-eth": "reentrancy-classic",
        "solidity.security.reentrancy-benign": "reentrancy-benign",
        "solidity.security.call-value-reentrancy": "reentrancy-classic",
        "solidity.security.cross-function-reentrancy": "reentrancy-cross-function",
        "solidity.security.read-only-reentrancy": "reentrancy-read-only",
        # Access control
        "solidity.security.tx-origin": "tx-origin-auth",
        "solidity.security.tx-origin-auth": "tx-origin-auth",
        "solidity.security.missing-access-control": "access-control-missing",
        "solidity.security.unprotected-selfdestruct": "selfdestruct-unprotected",
        "solidity.security.unprotected-ether-withdrawal": "access-control-permissive",
        "solidity.security.arbitrary-send": "access-control-permissive",
        # Delegation
        "solidity.security.delegatecall": "delegatecall-injection",
        "solidity.security.delegatecall-to-arbitrary": "delegatecall-injection",
        "solidity.security.controlled-delegatecall": "delegatecall-injection",
        "solidity.security.unsafe-delegatecall": "delegatecall-injection",
        # Return values
        "solidity.security.unchecked-send": "unchecked-return",
        "solidity.security.unchecked-call": "unchecked-return",
        "solidity.security.unchecked-transfer": "unchecked-return",
        "solidity.security.unchecked-low-level-call": "unchecked-low-level",
        # Arithmetic
        "solidity.security.integer-overflow": "arithmetic-overflow",
        "solidity.security.integer-underflow": "arithmetic-underflow",
        "solidity.security.divide-before-multiply": "arithmetic-precision-loss",
        # External calls
        "solidity.security.arbitrary-low-level-call": "arbitrary-call",
        "solidity.security.unsafe-external-call": "external-call-unsafe",
        "solidity.security.call-in-loop": "dos-external-call-loop",
        # State
        "solidity.security.uninitialized-storage": "state-uninitialized-storage",
        "solidity.security.uninitialized-state": "state-uninitialized",
        "solidity.security.shadowing-state": "state-shadowing",
        "solidity.security.write-after-write": "state-double-write",
        "solidity.security.incorrect-equality": "state-strict-equality",
        # Time/randomness
        "solidity.security.timestamp-dependence": "timestamp-dependence",
        "solidity.security.block-timestamp": "timestamp-dependence",
        "solidity.security.weak-randomness": "weak-randomness",
        "solidity.security.predictable-randomness": "weak-randomness",
        # Denial of Service
        "solidity.security.dos-gas-limit": "dos-gas-limit",
        "solidity.security.denial-of-service": "dos-revert",
        "solidity.security.unbounded-loop": "dos-unbounded-loop",
        "solidity.security.array-length-assignment": "dos-array-manipulation",
        # Signature/EIP
        "solidity.security.signature-malleability": "signature-malleability",
        "solidity.security.ecrecover-no-check": "signature-ecrecover-unsafe",
        "solidity.security.missing-eip712": "eip-compliance",
        # Flash loans
        "solidity.security.flash-loan-callback": "flash-loan-callback",
        "solidity.security.price-manipulation": "oracle-manipulation",
        # Oracle
        "solidity.security.oracle-stale-price": "oracle-stale-data",
        "solidity.security.chainlink-stale-data": "oracle-stale-data",
        "solidity.security.spot-price-manipulation": "oracle-manipulation",
        # ERC standards
        "solidity.security.erc20-return-value": "erc20-interface-violation",
        "solidity.security.erc721-return-value": "erc721-interface-violation",
        "solidity.security.approve-race": "erc20-approve-race",
        # Upgrades
        "solidity.security.unprotected-upgrade": "upgrade-unprotected",
        "solidity.security.storage-collision": "upgrade-storage-collision",
        "solidity.security.initializer-missing": "upgrade-initializer-missing",
        # Miscellaneous
        "solidity.security.locked-ether": "locked-funds",
        "solidity.security.msg-value-loop": "msg-value-loop",
        "solidity.security.assert-violation": "assert-violation",
        "solidity.security.use-of-deprecated": "deprecated-standards",
        "solidity.security.floating-pragma": "floating-pragma",
        "solidity.security.hardcoded-gas": "gas-hardcoded",
    }

    # Rule ID to category mapping
    RULE_TO_CATEGORY: Dict[str, str] = {
        # Reentrancy
        "solidity.security.reentrancy": "reentrancy",
        "solidity.security.reentrancy-eth": "reentrancy",
        "solidity.security.reentrancy-benign": "reentrancy",
        "solidity.security.call-value-reentrancy": "reentrancy",
        "solidity.security.cross-function-reentrancy": "reentrancy",
        "solidity.security.read-only-reentrancy": "reentrancy",
        # Access control
        "solidity.security.tx-origin": "access_control",
        "solidity.security.tx-origin-auth": "access_control",
        "solidity.security.missing-access-control": "access_control",
        "solidity.security.unprotected-selfdestruct": "access_control",
        "solidity.security.unprotected-ether-withdrawal": "access_control",
        "solidity.security.arbitrary-send": "access_control",
        # Delegation
        "solidity.security.delegatecall": "delegation",
        "solidity.security.delegatecall-to-arbitrary": "delegation",
        "solidity.security.controlled-delegatecall": "delegation",
        "solidity.security.unsafe-delegatecall": "delegation",
        # Return values
        "solidity.security.unchecked-send": "unchecked_return",
        "solidity.security.unchecked-call": "unchecked_return",
        "solidity.security.unchecked-transfer": "unchecked_return",
        "solidity.security.unchecked-low-level-call": "unchecked_return",
        # Arithmetic
        "solidity.security.integer-overflow": "arithmetic",
        "solidity.security.integer-underflow": "arithmetic",
        "solidity.security.divide-before-multiply": "arithmetic",
        # External calls
        "solidity.security.arbitrary-low-level-call": "external_calls",
        "solidity.security.unsafe-external-call": "external_calls",
        "solidity.security.call-in-loop": "dos",
        # State
        "solidity.security.uninitialized-storage": "state",
        "solidity.security.uninitialized-state": "state",
        "solidity.security.shadowing-state": "shadowing",
        "solidity.security.write-after-write": "state",
        "solidity.security.incorrect-equality": "state",
        # Time/randomness
        "solidity.security.timestamp-dependence": "time_manipulation",
        "solidity.security.block-timestamp": "time_manipulation",
        "solidity.security.weak-randomness": "randomness",
        "solidity.security.predictable-randomness": "randomness",
        # DOS
        "solidity.security.dos-gas-limit": "dos",
        "solidity.security.denial-of-service": "dos",
        "solidity.security.unbounded-loop": "dos",
        "solidity.security.array-length-assignment": "dos",
        # Oracle
        "solidity.security.oracle-stale-price": "oracle",
        "solidity.security.chainlink-stale-data": "oracle",
        "solidity.security.spot-price-manipulation": "oracle",
        "solidity.security.price-manipulation": "oracle",
    }

    # Semgrep severity to VKG severity mapping
    SEVERITY_MAP: Dict[str, str] = {
        "ERROR": "high",
        "WARNING": "medium",
        "INFO": "low",
    }

    # Base confidence for Semgrep (pattern matching, may have false positives)
    BASE_CONFIDENCE = 0.6

    def __init__(self) -> None:
        """Initialize the Semgrep adapter."""
        self._sarif_adapter = SARIFAdapter()

    def parse_json(self, output: str) -> List[Dict[str, Any]]:
        """Parse Semgrep JSON output.

        Args:
            output: JSON string from `semgrep --json`

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
            logger.error(f"Failed to parse Semgrep JSON: {e}")
            raise ValueError(f"Invalid Semgrep JSON output: {e}") from e

        results: List[Dict[str, Any]] = []

        # Handle Semgrep JSON format
        if isinstance(data, dict):
            # Standard format: {"results": [...], "errors": [...]}
            raw_results = data.get("results", [])

            for result in raw_results:
                if isinstance(result, dict):
                    results.append(result)

            # Log errors if any
            errors = data.get("errors", [])
            for error in errors:
                logger.warning(f"Semgrep error: {error}")

        elif isinstance(data, list):
            # Direct array of results
            results = [r for r in data if isinstance(r, dict)]

        return results

    def to_vkg_findings(
        self,
        raw: List[Dict[str, Any]],
    ) -> List[VKGFinding]:
        """Convert Semgrep raw results to VKG findings.

        Args:
            raw: List of Semgrep result dictionaries

        Returns:
            List of VKGFinding instances
        """
        findings: List[VKGFinding] = []

        for result in raw:
            finding = self._result_to_finding(result)
            if finding:
                findings.append(finding)

        return findings

    def to_sarif(
        self,
        raw: List[Dict[str, Any]],
        version: str = "0.0.0",
    ) -> Dict[str, Any]:
        """Convert Semgrep raw results to SARIF format.

        Args:
            raw: List of Semgrep result dictionaries
            version: Semgrep version string

        Returns:
            SARIF 2.1.0 document
        """
        findings = self.to_vkg_findings(raw)
        return self._sarif_adapter.to_sarif(findings, "semgrep", version)

    def get_vkg_pattern(self, rule_id: str) -> Optional[str]:
        """Get VKG pattern ID for a Semgrep rule.

        Args:
            rule_id: Semgrep rule ID (e.g., "solidity.security.reentrancy")

        Returns:
            VKG pattern ID or None if not mapped
        """
        # Try exact match
        if rule_id in self.RULE_TO_PATTERN:
            return self.RULE_TO_PATTERN[rule_id]

        # Try partial match for non-standard rule IDs
        for known_rule, pattern in self.RULE_TO_PATTERN.items():
            if rule_id.endswith(known_rule.split(".")[-1]):
                return pattern

        return None

    def get_category(self, rule_id: str) -> str:
        """Get category for a Semgrep rule.

        Args:
            rule_id: Semgrep rule ID

        Returns:
            Category string
        """
        # Try exact match
        if rule_id in self.RULE_TO_CATEGORY:
            return self.RULE_TO_CATEGORY[rule_id]

        # Try inferring from rule ID
        rule_lower = rule_id.lower()

        if "reentrancy" in rule_lower or "reentrant" in rule_lower:
            return "reentrancy"
        if "access" in rule_lower or "owner" in rule_lower or "auth" in rule_lower:
            return "access_control"
        if "delegate" in rule_lower:
            return "delegation"
        if "unchecked" in rule_lower:
            return "unchecked_return"
        if "overflow" in rule_lower or "underflow" in rule_lower:
            return "arithmetic"
        if "oracle" in rule_lower or "price" in rule_lower:
            return "oracle"
        if "dos" in rule_lower or "loop" in rule_lower:
            return "dos"
        if "time" in rule_lower or "timestamp" in rule_lower:
            return "time_manipulation"
        if "random" in rule_lower:
            return "randomness"

        return "security"

    def _result_to_finding(
        self,
        result: Dict[str, Any],
    ) -> Optional[VKGFinding]:
        """Convert Semgrep result to VKGFinding.

        Args:
            result: Semgrep result dictionary

        Returns:
            VKGFinding or None if conversion fails
        """
        try:
            # Extract basic info
            rule_id = result.get("check_id", "unknown")
            file_path = result.get("path", "")

            # Extract location
            start = result.get("start", {})
            end = result.get("end", {})
            line = start.get("line", 0)
            end_line = end.get("line")
            column = start.get("col")

            # Extract extra metadata
            extra = result.get("extra", {})
            message = extra.get("message", "")
            severity_raw = extra.get("severity", "WARNING")
            metadata = extra.get("metadata", {})

            # Get CWE info if available
            cwe_ids = metadata.get("cwe", [])
            references = metadata.get("references", [])

            # Map severity
            severity = self.SEVERITY_MAP.get(severity_raw.upper(), "medium")

            # Adjust confidence based on metadata
            confidence = self.BASE_CONFIDENCE
            if metadata.get("confidence") == "HIGH":
                confidence = 0.8
            elif metadata.get("confidence") == "LOW":
                confidence = 0.4

            # Build description
            description = message
            if cwe_ids:
                cwe_str = ", ".join(str(c) for c in cwe_ids)
                description += f"\n\nCWE: {cwe_str}"
            if references:
                ref_str = "\n".join(f"- {ref}" for ref in references[:3])
                description += f"\n\nReferences:\n{ref_str}"

            # Title from rule ID
            title = rule_id.replace("solidity.security.", "").replace("-", " ").title()

            return VKGFinding(
                source="semgrep",
                rule_id=rule_id,
                title=title,
                description=description or title,
                severity=severity,
                category=self.get_category(rule_id),
                file=file_path,
                line=line,
                end_line=end_line if end_line != line else None,
                column=column,
                confidence=confidence,
                tool_confidence=severity_raw,
                raw=result,
                vkg_pattern=self.get_vkg_pattern(rule_id),
            )

        except Exception as e:
            logger.error(f"Failed to convert Semgrep result: {e}")
            return None

    @classmethod
    def get_supported_rules(cls) -> List[str]:
        """Get list of supported Semgrep rules with VKG mappings.

        Returns:
            List of rule IDs
        """
        return list(cls.RULE_TO_PATTERN.keys())

    @classmethod
    def get_decurity_rules(cls) -> List[str]:
        """Get list of Decurity smart-contracts rules.

        Returns:
            List of rule IDs from Decurity ruleset
        """
        return [
            rule for rule in cls.RULE_TO_PATTERN.keys()
            if rule.startswith("solidity.")
        ]


def semgrep_to_sarif(
    output: str,
    version: str = "0.0.0",
) -> Dict[str, Any]:
    """Convenience function to convert Semgrep output to SARIF.

    Args:
        output: Semgrep JSON output string
        version: Semgrep version

    Returns:
        SARIF 2.1.0 document
    """
    adapter = SemgrepAdapter()
    raw = adapter.parse_json(output)
    return adapter.to_sarif(raw, version)


def semgrep_to_vkg_findings(output: str) -> List[VKGFinding]:
    """Convenience function to convert Semgrep output to VKG findings.

    Args:
        output: Semgrep JSON output string

    Returns:
        List of VKGFinding instances
    """
    adapter = SemgrepAdapter()
    raw = adapter.parse_json(output)
    return adapter.to_vkg_findings(raw)


__all__ = [
    "SemgrepAdapter",
    "semgrep_to_sarif",
    "semgrep_to_vkg_findings",
]
