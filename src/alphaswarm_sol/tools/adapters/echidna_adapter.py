"""Echidna Adapter - Property Test Results to SARIF/VKG Conversion.

Parses Echidna property-based fuzzing output and converts to SARIF 2.1.0
or VKG internal format. Handles both text and JSON output formats.

Echidna is a property-based fuzzer for Ethereum smart contracts, detecting:
- Property violations (echidna_xxx: failed!)
- Invariant breaks
- Assertion failures
- Custom test property violations
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from alphaswarm_sol.tools.adapters.sarif import (
    SARIFAdapter,
    VKGFinding,
)


logger = logging.getLogger(__name__)


class EchidnaAdapter:
    """Adapter for Echidna fuzzing output.

    Converts Echidna's property test results to SARIF 2.1.0 and VKGFinding.
    Maps Echidna property names to VKG pattern IDs for correlation.

    Echidna outputs in two formats:
    1. Text format (stdout): "echidna_xxx: failed!" / "echidna_xxx: passed!"
    2. JSON format (--format json): Full corpus, seeds, and coverage data

    Example:
        >>> adapter = EchidnaAdapter()
        >>> findings = adapter.parse_output(stdout, stderr)
        >>> vkg_findings = adapter.to_vkg_findings(findings)
        >>> sarif = adapter.to_sarif(findings)
    """

    # Common Echidna property naming patterns to VKG pattern mapping
    PROPERTY_TO_PATTERN: Dict[str, str] = {
        # Reentrancy tests
        "echidna_revert": "dos-revert",
        "echidna_no_reentrant": "reentrancy-classic",
        "echidna_no_reentrancy": "reentrancy-classic",
        "echidna_reentrancy": "reentrancy-classic",
        # Balance/value tests
        "echidna_balance_invariant": "arithmetic-overflow",
        "echidna_balance": "arithmetic-overflow",
        "echidna_total_supply": "arithmetic-overflow",
        "echidna_no_overflow": "arithmetic-overflow",
        "echidna_no_underflow": "arithmetic-underflow",
        # Access control tests
        "echidna_owner": "access-control-missing",
        "echidna_admin": "access-control-missing",
        "echidna_only_owner": "access-control-missing",
        "echidna_access": "access-control-missing",
        # State tests
        "echidna_invariant": "invariant-violation",
        "echidna_state": "state-corruption",
        "echidna_locked": "locked-funds",
        # Transfer tests
        "echidna_transfer": "unchecked-return",
        "echidna_no_drain": "access-control-permissive",
        "echidna_pause": "pausable-bypass",
    }

    # Property name pattern to category mapping (fuzzy matching)
    PROPERTY_CATEGORY_PATTERNS: Dict[str, str] = {
        r"reentran": "reentrancy",
        r"balance": "arithmetic",
        r"overflow": "arithmetic",
        r"underflow": "arithmetic",
        r"owner|admin|access|role": "access_control",
        r"transfer|send|withdraw": "value_transfer",
        r"invariant": "invariant",
        r"pause|freeze|stop": "pausable",
        r"lock|stuck": "locked_funds",
        r"drain|steal": "access_control",
        r"state": "state",
        r"supply": "arithmetic",
    }

    # Echidna result types
    RESULT_FAILED = "failed"
    RESULT_PASSED = "passed"
    RESULT_TIMEOUT = "timeout"
    RESULT_ERROR = "error"

    # Regex patterns for text output parsing
    TEXT_RESULT_PATTERN = re.compile(
        r"(\w+):\s*(failed|passed|timeout|error)!?(?:\s*(.*))?",
        re.IGNORECASE
    )
    COUNTEREXAMPLE_PATTERN = re.compile(
        r"Call sequence[:\s]*(.*?)(?=\n\n|\Z)",
        re.DOTALL | re.IGNORECASE
    )

    def __init__(self) -> None:
        """Initialize the Echidna adapter."""
        self._sarif_adapter = SARIFAdapter()

    def parse_output(
        self,
        stdout: str,
        stderr: str = "",
    ) -> List[Dict[str, Any]]:
        """Parse Echidna text output from stdout/stderr.

        Args:
            stdout: Standard output from Echidna
            stderr: Standard error from Echidna

        Returns:
            List of raw result dictionaries
        """
        results: List[Dict[str, Any]] = []

        # Combine output for parsing
        combined = f"{stdout}\n{stderr}"

        # Parse property test results
        for match in self.TEXT_RESULT_PATTERN.finditer(combined):
            property_name = match.group(1)
            status = match.group(2).lower()
            extra_info = match.group(3) or ""

            result: Dict[str, Any] = {
                "property": property_name,
                "status": status,
                "extra": extra_info.strip(),
            }

            # Only report failures as findings
            if status == self.RESULT_FAILED:
                # Try to extract counterexample
                counterexample = self._extract_counterexample(
                    combined, property_name
                )
                if counterexample:
                    result["counterexample"] = counterexample

                results.append(result)

        return results

    def parse_json(self, output: str) -> List[Dict[str, Any]]:
        """Parse Echidna JSON output (--format json).

        Args:
            output: JSON string from Echidna

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
            logger.error(f"Failed to parse Echidna JSON: {e}")
            raise ValueError(f"Invalid Echidna JSON output: {e}") from e

        results: List[Dict[str, Any]] = []

        # Handle Echidna JSON format
        if isinstance(data, dict):
            # Check for test results
            tests = data.get("tests", [])
            if tests:
                for test in tests:
                    # Only include failed tests
                    if test.get("status") == "falsified":
                        result = {
                            "property": test.get("name", "unknown"),
                            "status": self.RESULT_FAILED,
                            "contract": test.get("contract"),
                            "counterexample": test.get("counterexample", []),
                            "seed": test.get("seed"),
                            "calls": test.get("calls", 0),
                            "corpus": test.get("corpus"),
                        }
                        results.append(result)

            # Check for coverage data
            coverage = data.get("coverage", {})
            if coverage:
                for contract_name, contract_cov in coverage.items():
                    # Coverage can reveal unreachable code paths
                    if isinstance(contract_cov, dict):
                        uncovered = contract_cov.get("uncovered", [])
                        for func in uncovered:
                            # These are informational, not failures
                            pass

            # Handle single test format
            if "name" in data and data.get("status") == "falsified":
                result = {
                    "property": data.get("name", "unknown"),
                    "status": self.RESULT_FAILED,
                    "contract": data.get("contract"),
                    "counterexample": data.get("counterexample", []),
                    "seed": data.get("seed"),
                }
                results.append(result)

        elif isinstance(data, list):
            # Direct array of test results
            for test in data:
                if isinstance(test, dict) and test.get("status") == "falsified":
                    result = {
                        "property": test.get("name", "unknown"),
                        "status": self.RESULT_FAILED,
                        "contract": test.get("contract"),
                        "counterexample": test.get("counterexample", []),
                        "seed": test.get("seed"),
                    }
                    results.append(result)

        return results

    def to_vkg_findings(
        self,
        raw: List[Dict[str, Any]],
        source_file: Optional[str] = None,
    ) -> List[VKGFinding]:
        """Convert Echidna raw results to VKG findings.

        Args:
            raw: List of Echidna result dictionaries
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
        """Convert Echidna raw results to SARIF format.

        Args:
            raw: List of Echidna result dictionaries
            version: Echidna version string

        Returns:
            SARIF 2.1.0 document
        """
        findings = self.to_vkg_findings(raw)
        return self._sarif_adapter.to_sarif(findings, "echidna", version)

    def get_vkg_pattern(self, property_name: str) -> Optional[str]:
        """Get VKG pattern ID for an Echidna property.

        Args:
            property_name: Echidna property test name

        Returns:
            VKG pattern ID or None if not mapped
        """
        # Exact match first
        if property_name in self.PROPERTY_TO_PATTERN:
            return self.PROPERTY_TO_PATTERN[property_name]

        # Try lowercase
        property_lower = property_name.lower()
        if property_lower in self.PROPERTY_TO_PATTERN:
            return self.PROPERTY_TO_PATTERN[property_lower]

        # Try fuzzy matching on property name
        for pattern_prefix, vkg_pattern in self.PROPERTY_TO_PATTERN.items():
            if property_lower.startswith(pattern_prefix.lower()):
                return vkg_pattern

        return None

    def get_category(self, property_name: str) -> str:
        """Get category for an Echidna property.

        Args:
            property_name: Echidna property test name

        Returns:
            Category string
        """
        property_lower = property_name.lower()

        # Check pattern-based category matching
        for pattern, category in self.PROPERTY_CATEGORY_PATTERNS.items():
            if re.search(pattern, property_lower):
                return category

        # Default category for property violations
        return "property_violation"

    def _result_to_finding(
        self,
        result: Dict[str, Any],
        source_file: Optional[str] = None,
    ) -> Optional[VKGFinding]:
        """Convert Echidna result to VKGFinding.

        Args:
            result: Echidna result dictionary
            source_file: Optional override for source file path

        Returns:
            VKGFinding or None if conversion fails
        """
        try:
            property_name = result.get("property", "unknown")
            status = result.get("status", "")

            # Only process failures
            if status != self.RESULT_FAILED:
                return None

            # Extract contract info
            contract = result.get("contract", "")
            file_path = source_file or ""

            # Build description from counterexample
            counterexample = result.get("counterexample", [])
            description = self._build_description(property_name, counterexample)

            # Add seed info if available
            seed = result.get("seed")
            if seed:
                description += f"\n\nSeed for reproduction: {seed}"

            # Property test failure = high severity and high confidence
            # Fuzzing found actual violation
            severity = "high"
            confidence = 0.95

            # Get VKG pattern mapping
            vkg_pattern = self.get_vkg_pattern(property_name)

            return VKGFinding(
                source="echidna",
                rule_id=property_name,
                title=f"Property violation: {property_name}",
                description=description,
                severity=severity,
                category=self.get_category(property_name),
                file=file_path or "unknown",
                line=0,  # Echidna doesn't provide line numbers
                contract=contract or None,
                confidence=confidence,
                tool_confidence="High",  # Fuzzing found actual violation
                raw=result,
                vkg_pattern=vkg_pattern,
            )

        except Exception as e:
            logger.error(f"Failed to convert Echidna result: {e}")
            return None

    def _extract_counterexample(
        self,
        output: str,
        property_name: str,
    ) -> Optional[List[str]]:
        """Extract counterexample call sequence from text output.

        Args:
            output: Combined stdout/stderr output
            property_name: Name of the failed property

        Returns:
            List of call strings or None
        """
        # Look for call sequence after property failure
        pattern = rf"{re.escape(property_name)}.*?failed.*?(?:Call sequence|Shrunk|Sequence)[:\s]*(.*?)(?=\n\n|\Z)"
        match = re.search(pattern, output, re.DOTALL | re.IGNORECASE)

        if match:
            sequence_text = match.group(1).strip()
            # Split into individual calls
            calls = [
                call.strip()
                for call in sequence_text.split("\n")
                if call.strip() and not call.strip().startswith("#")
            ]
            return calls if calls else None

        return None

    def _build_description(
        self,
        property_name: str,
        counterexample: List[Any],
    ) -> str:
        """Build description from property and counterexample.

        Args:
            property_name: Name of the failed property
            counterexample: Counterexample call sequence

        Returns:
            Human-readable description
        """
        desc = f"Echidna found a violation of property `{property_name}`."

        if counterexample:
            desc += "\n\nCounterexample call sequence:"
            for i, call in enumerate(counterexample, 1):
                if isinstance(call, dict):
                    # JSON format call
                    func = call.get("function", call.get("name", "unknown"))
                    args = call.get("args", call.get("arguments", []))
                    value = call.get("value", 0)
                    sender = call.get("sender", call.get("from", ""))
                    call_str = f"{func}({', '.join(str(a) for a in args)})"
                    if value:
                        call_str += f" [value: {value}]"
                    if sender:
                        call_str += f" [from: {sender}]"
                    desc += f"\n  {i}. {call_str}"
                else:
                    desc += f"\n  {i}. {call}"

        return desc

    @classmethod
    def get_supported_properties(cls) -> List[str]:
        """Get list of recognized property naming patterns.

        Returns:
            List of property names with VKG pattern mappings
        """
        return list(cls.PROPERTY_TO_PATTERN.keys())


def echidna_to_sarif(
    stdout: str,
    stderr: str = "",
    version: str = "0.0.0",
) -> Dict[str, Any]:
    """Convenience function to convert Echidna text output to SARIF.

    Args:
        stdout: Standard output from Echidna
        stderr: Standard error from Echidna
        version: Echidna version

    Returns:
        SARIF 2.1.0 document
    """
    adapter = EchidnaAdapter()
    raw = adapter.parse_output(stdout, stderr)
    return adapter.to_sarif(raw, version)


def echidna_json_to_sarif(
    output: str,
    version: str = "0.0.0",
) -> Dict[str, Any]:
    """Convenience function to convert Echidna JSON output to SARIF.

    Args:
        output: JSON output from Echidna (--format json)
        version: Echidna version

    Returns:
        SARIF 2.1.0 document
    """
    adapter = EchidnaAdapter()
    raw = adapter.parse_json(output)
    return adapter.to_sarif(raw, version)


def echidna_to_vkg_findings(
    stdout: str,
    stderr: str = "",
) -> List[VKGFinding]:
    """Convenience function to convert Echidna text output to VKG findings.

    Args:
        stdout: Standard output from Echidna
        stderr: Standard error from Echidna

    Returns:
        List of VKGFinding instances
    """
    adapter = EchidnaAdapter()
    raw = adapter.parse_output(stdout, stderr)
    return adapter.to_vkg_findings(raw)


def echidna_json_to_vkg_findings(output: str) -> List[VKGFinding]:
    """Convenience function to convert Echidna JSON output to VKG findings.

    Args:
        output: JSON output from Echidna (--format json)

    Returns:
        List of VKGFinding instances
    """
    adapter = EchidnaAdapter()
    raw = adapter.parse_json(output)
    return adapter.to_vkg_findings(raw)


__all__ = [
    "EchidnaAdapter",
    "echidna_to_sarif",
    "echidna_json_to_sarif",
    "echidna_to_vkg_findings",
    "echidna_json_to_vkg_findings",
]
