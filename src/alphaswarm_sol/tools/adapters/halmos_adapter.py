"""Halmos Adapter - Symbolic Execution Results to SARIF/VKG Conversion.

Parses Halmos symbolic testing output and converts to SARIF 2.1.0 or VKG
internal format. Handles counterexamples from formal verification.

Halmos is a symbolic execution tool for Solidity, providing:
- Formal verification of assertions
- Counterexample generation for failing tests
- Path exploration with symbolic inputs
- Mathematical proof of bugs (confidence = 1.0)
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


class HalmosAdapter:
    """Adapter for Halmos symbolic execution output.

    Converts Halmos counterexamples to SARIF 2.1.0 and VKGFinding.
    Maps assertion failures to VKG pattern IDs for correlation.

    Halmos provides formal proofs, so findings have confidence = 1.0
    (mathematically proven bugs).

    Example:
        >>> adapter = HalmosAdapter()
        >>> findings = adapter.parse_json(halmos_output)
        >>> vkg_findings = adapter.to_vkg_findings(findings)
        >>> sarif = adapter.to_sarif(findings)
    """

    # Test name pattern to VKG pattern mapping
    TEST_TO_PATTERN: Dict[str, str] = {
        "check_NoOverflow": "arithmetic-overflow",
        "check_NoUnderflow": "arithmetic-underflow",
        "check_Reentrancy": "reentrancy-classic",
        "check_NoReentrancy": "reentrancy-classic",
        "check_AccessControl": "access-control-missing",
        "check_Ownership": "access-control-missing",
        "check_Balance": "arithmetic-overflow",
        "check_Invariant": "invariant-violation",
        "check_StateConsistency": "state-corruption",
        "check_NoArbitrarySend": "access-control-permissive",
        "check_NoSelfdestruct": "selfdestruct-unprotected",
        "check_NoDelegateCall": "delegatecall-injection",
    }

    # Assertion type to category mapping
    ASSERTION_TO_CATEGORY: Dict[str, str] = {
        "assert": "assertion",
        "require": "requirement",
        "revert": "revert",
        "overflow": "arithmetic",
        "underflow": "arithmetic",
        "division": "arithmetic",
        "access": "access_control",
        "owner": "access_control",
        "balance": "arithmetic",
        "invariant": "invariant",
        "reentrancy": "reentrancy",
    }

    # Halmos result status
    STATUS_FAIL = "FAIL"
    STATUS_PASS = "PASS"
    STATUS_TIMEOUT = "TIMEOUT"
    STATUS_UNKNOWN = "UNKNOWN"

    def __init__(self) -> None:
        """Initialize the Halmos adapter."""
        self._sarif_adapter = SARIFAdapter()

    def parse_json(self, output: str) -> List[Dict[str, Any]]:
        """Parse Halmos JSON output.

        Args:
            output: JSON string from Halmos

        Returns:
            List of raw counterexample dictionaries (failures only)

        Raises:
            ValueError: If JSON parsing fails
        """
        if not output or not output.strip():
            return []

        try:
            data = json.loads(output)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Halmos JSON: {e}")
            raise ValueError(f"Invalid Halmos JSON output: {e}") from e

        results: List[Dict[str, Any]] = []

        # Handle Halmos JSON format
        if isinstance(data, dict):
            # Check for test results
            tests = data.get("tests", data.get("results", []))

            if isinstance(tests, list):
                for test in tests:
                    if isinstance(test, dict):
                        status = test.get("status", "").upper()
                        # Only include failures (counterexamples found)
                        if status == self.STATUS_FAIL:
                            results.append(test)

            # Handle single test format
            elif data.get("status", "").upper() == self.STATUS_FAIL:
                results.append(data)

            # Handle counterexamples at top level
            counterexamples = data.get("counterexamples", [])
            for ce in counterexamples:
                if isinstance(ce, dict):
                    results.append(ce)

        elif isinstance(data, list):
            # Direct array of results
            for item in data:
                if isinstance(item, dict):
                    status = item.get("status", "").upper()
                    if status == self.STATUS_FAIL or "counterexample" in item:
                        results.append(item)

        return results

    def parse_text(self, output: str) -> List[Dict[str, Any]]:
        """Parse Halmos text output (stdout).

        Args:
            output: Standard output from Halmos

        Returns:
            List of raw counterexample dictionaries
        """
        results: List[Dict[str, Any]] = []

        # Pattern for test failure
        # Example: "[FAIL] check_NoOverflow(uint256) (paths: 5, time: 2.3s)"
        fail_pattern = re.compile(
            r"\[FAIL\]\s+(\w+)\s*\(([^)]*)\)(?:\s+\(([^)]+)\))?",
            re.IGNORECASE
        )

        # Pattern for counterexample
        # Example: "Counterexample: x = 0x..."
        ce_pattern = re.compile(
            r"Counterexample[:\s]*(.*?)(?=\n\[|\nTest|\Z)",
            re.DOTALL | re.IGNORECASE
        )

        current_test = None
        lines = output.split("\n")

        for i, line in enumerate(lines):
            fail_match = fail_pattern.search(line)
            if fail_match:
                test_name = fail_match.group(1)
                params = fail_match.group(2)
                info = fail_match.group(3) or ""

                current_test = {
                    "name": test_name,
                    "parameters": params,
                    "status": self.STATUS_FAIL,
                    "info": info,
                    "counterexample": {},
                }

                # Look for counterexample in following lines
                remaining = "\n".join(lines[i:])
                ce_match = ce_pattern.search(remaining)
                if ce_match:
                    ce_text = ce_match.group(1).strip()
                    current_test["counterexample"] = self._parse_counterexample(ce_text)

                results.append(current_test)

        return results

    def to_vkg_findings(
        self,
        raw: List[Dict[str, Any]],
        source_file: Optional[str] = None,
    ) -> List[VKGFinding]:
        """Convert Halmos raw results to VKG findings.

        Args:
            raw: List of Halmos result dictionaries
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
        """Convert Halmos raw results to SARIF format.

        Args:
            raw: List of Halmos result dictionaries
            version: Halmos version string

        Returns:
            SARIF 2.1.0 document
        """
        findings = self.to_vkg_findings(raw)
        return self._sarif_adapter.to_sarif(findings, "halmos", version)

    def get_vkg_pattern(self, test_name: str) -> Optional[str]:
        """Get VKG pattern ID for a Halmos test.

        Args:
            test_name: Halmos test function name

        Returns:
            VKG pattern ID or None if not mapped
        """
        # Try exact match
        if test_name in self.TEST_TO_PATTERN:
            return self.TEST_TO_PATTERN[test_name]

        # Try prefix match
        for pattern_name, vkg_pattern in self.TEST_TO_PATTERN.items():
            if test_name.startswith(pattern_name):
                return vkg_pattern

        # Try keyword matching
        test_lower = test_name.lower()
        if "overflow" in test_lower:
            return "arithmetic-overflow"
        if "underflow" in test_lower:
            return "arithmetic-underflow"
        if "reentrancy" in test_lower or "reentrant" in test_lower:
            return "reentrancy-classic"
        if "access" in test_lower or "owner" in test_lower:
            return "access-control-missing"
        if "invariant" in test_lower:
            return "invariant-violation"
        if "delegate" in test_lower:
            return "delegatecall-injection"

        return None

    def get_category(self, test_name: str) -> str:
        """Get category for a Halmos test.

        Args:
            test_name: Halmos test function name

        Returns:
            Category string
        """
        test_lower = test_name.lower()

        for keyword, category in self.ASSERTION_TO_CATEGORY.items():
            if keyword in test_lower:
                return category

        return "symbolic_verification"

    def _result_to_finding(
        self,
        result: Dict[str, Any],
        source_file: Optional[str] = None,
    ) -> Optional[VKGFinding]:
        """Convert Halmos result to VKGFinding.

        Args:
            result: Halmos result dictionary
            source_file: Optional override for source file path

        Returns:
            VKGFinding or None if conversion fails
        """
        try:
            # Extract test info
            test_name = result.get("name", result.get("test", "unknown"))
            contract = result.get("contract", "")
            file_path = source_file or result.get("file", "")

            # Extract counterexample
            counterexample = result.get("counterexample", {})
            if isinstance(counterexample, str):
                counterexample = self._parse_counterexample(counterexample)

            # Build description
            description = self._build_description(test_name, counterexample, result)

            # Halmos provides formal proofs - confidence is 1.0
            # These are mathematically proven bugs
            severity = "critical"
            confidence = 1.0

            return VKGFinding(
                source="halmos",
                rule_id=test_name,
                title=f"Symbolic verification failure: {test_name}",
                description=description,
                severity=severity,
                category=self.get_category(test_name),
                file=file_path or "unknown",
                line=0,  # Halmos doesn't typically provide line numbers
                contract=contract or None,
                confidence=confidence,
                tool_confidence="Proven",  # Formal proof
                raw=result,
                vkg_pattern=self.get_vkg_pattern(test_name),
            )

        except Exception as e:
            logger.error(f"Failed to convert Halmos result: {e}")
            return None

    def _parse_counterexample(self, ce_text: str) -> Dict[str, Any]:
        """Parse counterexample text into structured format.

        Args:
            ce_text: Counterexample text

        Returns:
            Dictionary of variable name to value
        """
        counterexample: Dict[str, Any] = {}

        # Pattern: variable = value
        var_pattern = re.compile(r"(\w+)\s*[=:]\s*(.+?)(?=\n|\s+\w+\s*=|$)")

        for match in var_pattern.finditer(ce_text):
            var_name = match.group(1)
            value = match.group(2).strip()
            counterexample[var_name] = value

        return counterexample

    def _build_description(
        self,
        test_name: str,
        counterexample: Dict[str, Any],
        result: Dict[str, Any],
    ) -> str:
        """Build description from Halmos result.

        Args:
            test_name: Test function name
            counterexample: Counterexample values
            result: Full result dictionary

        Returns:
            Human-readable description
        """
        desc = f"Halmos symbolic execution found a counterexample for `{test_name}`."
        desc += "\n\nThis is a formal proof that the assertion can fail."

        if counterexample:
            desc += "\n\nCounterexample inputs:"
            for var, value in counterexample.items():
                desc += f"\n  {var} = {value}"

        # Add path info if available
        paths = result.get("paths", result.get("path_count"))
        if paths:
            desc += f"\n\nPaths explored: {paths}"

        # Add execution time if available
        time_info = result.get("time", result.get("duration"))
        if time_info:
            desc += f"\nExecution time: {time_info}"

        return desc

    @classmethod
    def get_supported_tests(cls) -> List[str]:
        """Get list of recognized test naming patterns.

        Returns:
            List of test name patterns with VKG mappings
        """
        return list(cls.TEST_TO_PATTERN.keys())


def halmos_to_sarif(
    output: str,
    version: str = "0.0.0",
) -> Dict[str, Any]:
    """Convenience function to convert Halmos JSON output to SARIF.

    Args:
        output: JSON output from Halmos
        version: Halmos version

    Returns:
        SARIF 2.1.0 document
    """
    adapter = HalmosAdapter()
    raw = adapter.parse_json(output)
    return adapter.to_sarif(raw, version)


def halmos_text_to_sarif(
    output: str,
    version: str = "0.0.0",
) -> Dict[str, Any]:
    """Convenience function to convert Halmos text output to SARIF.

    Args:
        output: Text output from Halmos (stdout)
        version: Halmos version

    Returns:
        SARIF 2.1.0 document
    """
    adapter = HalmosAdapter()
    raw = adapter.parse_text(output)
    return adapter.to_sarif(raw, version)


def halmos_to_vkg_findings(output: str) -> List[VKGFinding]:
    """Convenience function to convert Halmos JSON output to VKG findings.

    Args:
        output: JSON output from Halmos

    Returns:
        List of VKGFinding instances
    """
    adapter = HalmosAdapter()
    raw = adapter.parse_json(output)
    return adapter.to_vkg_findings(raw)


def halmos_text_to_vkg_findings(output: str) -> List[VKGFinding]:
    """Convenience function to convert Halmos text output to VKG findings.

    Args:
        output: Text output from Halmos (stdout)

    Returns:
        List of VKGFinding instances
    """
    adapter = HalmosAdapter()
    raw = adapter.parse_text(output)
    return adapter.to_vkg_findings(raw)


__all__ = [
    "HalmosAdapter",
    "halmos_to_sarif",
    "halmos_text_to_sarif",
    "halmos_to_vkg_findings",
    "halmos_text_to_vkg_findings",
]
