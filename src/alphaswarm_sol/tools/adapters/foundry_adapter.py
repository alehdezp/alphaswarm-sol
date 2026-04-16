"""Foundry Adapter - Forge Test Results to SARIF/VKG Conversion.

Parses Foundry (forge) test output and converts to SARIF 2.1.0 or VKG
internal format. Handles JSON output from `forge test --json`.

Foundry is a modern Solidity testing framework detecting:
- Invariant violations via invariant_* tests
- Fuzz test failures with counterexamples
- Standard unit test failures
- Exploit proof-of-concepts via test_exploit_* naming
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


class FoundryAdapter:
    """Adapter for Foundry (forge) test output.

    Converts Foundry's test results to SARIF 2.1.0 and VKGFinding.
    Maps test naming conventions to VKG pattern IDs for correlation.

    Foundry test conventions:
    - test_*: Standard unit tests
    - testFail_*: Expected to revert
    - testFuzz_*: Fuzz tests with random inputs
    - test_RevertIf_*: Expected to revert on condition
    - invariant_*: Invariant tests (failures are bugs)
    - test_exploit_*: Exploit proof-of-concept

    Example:
        >>> adapter = FoundryAdapter()
        >>> findings = adapter.parse_json(forge_output)
        >>> vkg_findings = adapter.to_vkg_findings(findings)
        >>> sarif = adapter.to_sarif(findings)
    """

    # Test naming prefix to pattern mapping
    TEST_PREFIX_TO_PATTERN: Dict[str, Optional[str]] = {
        "testFail_": None,  # Expected to fail, not a bug
        "testFail": None,  # Expected to fail, not a bug
        "test_RevertIf_": None,  # Expected to revert, not a bug
        "test_revertIf_": None,  # Expected to revert, not a bug
        "testRevertIf_": None,  # Expected to revert, not a bug
        "invariant_": "invariant-violation",  # Invariant break = bug
        "invariant": "invariant-violation",  # Invariant break = bug
        "test_exploit_": "known-exploit",  # Exploit PoC
        "test_Exploit_": "known-exploit",  # Exploit PoC
        "testExploit_": "known-exploit",  # Exploit PoC
        "test_poc_": "known-exploit",  # Proof of concept
        "test_Poc_": "known-exploit",  # Proof of concept
        "testPoc_": "known-exploit",  # Proof of concept
        "testFuzz_": None,  # Handle separately based on result
        "test_fuzz_": None,  # Handle separately based on result
        "testFuzz": None,  # Handle separately based on result
    }

    # Test name pattern hints for category detection
    TEST_CATEGORY_PATTERNS: Dict[str, str] = {
        r"reentrancy|reentrant": "reentrancy",
        r"overflow|underflow|arithmetic": "arithmetic",
        r"access|owner|admin|role|auth": "access_control",
        r"transfer|withdraw|drain": "value_transfer",
        r"invariant": "invariant",
        r"exploit|poc|attack": "exploit",
        r"pause|freeze|stop": "pausable",
        r"lock|stuck|rescue": "locked_funds",
        r"oracle|price": "oracle",
        r"flash|loan": "flash_loan",
        r"sandwich|frontrun": "frontrunning",
        r"slippage": "slippage",
    }

    # Test status constants
    STATUS_SUCCESS = "Success"
    STATUS_FAILURE = "Failure"
    STATUS_SKIPPED = "Skipped"

    def __init__(self) -> None:
        """Initialize the Foundry adapter."""
        self._sarif_adapter = SARIFAdapter()

    def parse_json(self, output: str) -> List[Dict[str, Any]]:
        """Parse Foundry JSON output from `forge test --json`.

        Args:
            output: JSON string from Foundry

        Returns:
            List of raw test result dictionaries (failures only)

        Raises:
            ValueError: If JSON parsing fails
        """
        if not output or not output.strip():
            return []

        try:
            data = json.loads(output)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Foundry JSON: {e}")
            raise ValueError(f"Invalid Foundry JSON output: {e}") from e

        results: List[Dict[str, Any]] = []

        # Handle Foundry JSON format
        # Format: {contract_name: {test_name: {status, reason, counterexample, ...}}}
        if isinstance(data, dict):
            for contract_path, contract_data in data.items():
                if not isinstance(contract_data, dict):
                    continue

                # Extract contract name from path (e.g., "src/Test.t.sol:TestContract")
                contract_name = contract_path
                file_path = ""
                if ":" in contract_path:
                    file_path, contract_name = contract_path.rsplit(":", 1)

                for test_name, test_result in contract_data.items():
                    if not isinstance(test_result, dict):
                        continue

                    # Get test status
                    status = test_result.get("status", "")

                    # Only include failures that aren't expected
                    if status == self.STATUS_FAILURE:
                        if not self._is_expected_failure(test_name):
                            result = {
                                "test_name": test_name,
                                "contract": contract_name,
                                "file": file_path,
                                "status": status,
                                "reason": test_result.get("reason", ""),
                                "counterexample": test_result.get("counterexample"),
                                "logs": test_result.get("logs", []),
                                "decoded_logs": test_result.get("decoded_logs", []),
                                "traces": test_result.get("traces", []),
                                "duration": test_result.get("duration"),
                                "gas": test_result.get("gas"),
                            }
                            results.append(result)

        return results

    def to_vkg_findings(
        self,
        raw: List[Dict[str, Any]],
    ) -> List[VKGFinding]:
        """Convert Foundry raw results to VKG findings.

        Args:
            raw: List of Foundry result dictionaries

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
        """Convert Foundry raw results to SARIF format.

        Args:
            raw: List of Foundry result dictionaries
            version: Foundry version string

        Returns:
            SARIF 2.1.0 document
        """
        findings = self.to_vkg_findings(raw)
        return self._sarif_adapter.to_sarif(findings, "foundry", version)

    def get_vkg_pattern(self, test_name: str) -> Optional[str]:
        """Get VKG pattern ID for a test based on naming convention.

        Args:
            test_name: Forge test name

        Returns:
            VKG pattern ID or None if not mapped
        """
        # Check prefix patterns
        for prefix, pattern in self.TEST_PREFIX_TO_PATTERN.items():
            if test_name.startswith(prefix):
                return pattern

        # Check if it's a fuzz test with failure
        if "fuzz" in test_name.lower():
            # Fuzz failures are significant
            return "fuzz-failure"

        return None

    def get_category(self, test_name: str) -> str:
        """Get category for a test based on naming patterns.

        Args:
            test_name: Forge test name

        Returns:
            Category string
        """
        test_lower = test_name.lower()

        # Check pattern-based category matching
        for pattern, category in self.TEST_CATEGORY_PATTERNS.items():
            if re.search(pattern, test_lower):
                return category

        # Prefix-based categories
        if test_name.startswith("invariant"):
            return "invariant"
        if "exploit" in test_lower or "poc" in test_lower:
            return "exploit"
        if "fuzz" in test_lower:
            return "fuzz"

        return "test_failure"

    def extract_trace_info(self, logs: List[str]) -> Dict[str, Any]:
        """Parse stack trace information from logs.

        Args:
            logs: List of log strings from test execution

        Returns:
            Dictionary with parsed trace information
        """
        trace_info: Dict[str, Any] = {
            "calls": [],
            "reverts": [],
            "events": [],
            "assertions": [],
        }

        for log in logs:
            log_lower = log.lower()

            # Detect call traces
            if "call" in log_lower or "->" in log:
                trace_info["calls"].append(log)

            # Detect reverts
            if "revert" in log_lower or "fail" in log_lower:
                trace_info["reverts"].append(log)

            # Detect events
            if "emit" in log_lower or "event" in log_lower:
                trace_info["events"].append(log)

            # Detect assertion failures
            if "assert" in log_lower:
                trace_info["assertions"].append(log)

        return trace_info

    def get_failure_location(
        self,
        reason: str,
        logs: List[str],
    ) -> Tuple[str, int]:
        """Extract failure location from reason and logs.

        Args:
            reason: Failure reason string
            logs: List of log strings

        Returns:
            Tuple of (file_path, line_number)
        """
        # Try to extract from reason
        # Common formats:
        # - "src/Contract.sol:123"
        # - "Contract.sol:function_name()"
        # - "revert at src/Contract.sol:123"

        location_pattern = r"([a-zA-Z0-9_/\.\-]+\.sol)(?::(\d+))?"

        # Check reason first
        match = re.search(location_pattern, reason)
        if match:
            file_path = match.group(1)
            line = int(match.group(2)) if match.group(2) else 0
            return file_path, line

        # Check logs
        for log in logs:
            match = re.search(location_pattern, log)
            if match:
                file_path = match.group(1)
                line = int(match.group(2)) if match.group(2) else 0
                return file_path, line

        return "", 0

    def _is_expected_failure(self, test_name: str) -> bool:
        """Check if a test failure is expected based on naming.

        Args:
            test_name: Test function name

        Returns:
            True if failure is expected (not a bug)
        """
        expected_prefixes = [
            "testFail_",
            "testFail",
            "test_RevertIf_",
            "test_revertIf_",
            "testRevertIf_",
            "testRevert_",
            "test_Revert_",
        ]

        for prefix in expected_prefixes:
            if test_name.startswith(prefix):
                return True

        return False

    def _is_invariant_test(self, test_name: str) -> bool:
        """Check if test is an invariant test.

        Args:
            test_name: Test function name

        Returns:
            True if invariant test
        """
        return test_name.startswith("invariant") or test_name.startswith("invariant_")

    def _is_fuzz_test(self, test_name: str) -> bool:
        """Check if test is a fuzz test.

        Args:
            test_name: Test function name

        Returns:
            True if fuzz test
        """
        test_lower = test_name.lower()
        return "fuzz" in test_lower or test_name.startswith("testFuzz")

    def _result_to_finding(
        self,
        result: Dict[str, Any],
    ) -> Optional[VKGFinding]:
        """Convert Foundry test result to VKGFinding.

        Args:
            result: Foundry test result dictionary

        Returns:
            VKGFinding or None if conversion fails
        """
        try:
            test_name = result.get("test_name", "unknown")
            contract = result.get("contract", "")
            file_path = result.get("file", "")
            reason = result.get("reason", "")
            logs = result.get("logs", [])
            decoded_logs = result.get("decoded_logs", [])
            counterexample = result.get("counterexample")

            # Try to get file/line from reason/logs
            if not file_path:
                extracted_file, line = self.get_failure_location(
                    reason, logs + decoded_logs
                )
                if extracted_file:
                    file_path = extracted_file
            else:
                line = 0

            # Determine severity and confidence based on test type
            if self._is_invariant_test(test_name):
                # Invariant failures are reproducible bugs
                severity = "critical"
                confidence = 1.0
            elif self._is_fuzz_test(test_name):
                # Fuzz failures with counterexample are high confidence
                severity = "high"
                confidence = 0.95 if counterexample else 0.85
            elif "exploit" in test_name.lower() or "poc" in test_name.lower():
                # Exploit PoC is critical
                severity = "critical"
                confidence = 1.0
            else:
                # Standard test failure
                severity = "high"
                confidence = 0.9

            # Build description
            description = self._build_description(
                test_name, reason, counterexample, logs
            )

            return VKGFinding(
                source="foundry",
                rule_id=test_name,
                title=f"Test failure: {test_name}",
                description=description,
                severity=severity,
                category=self.get_category(test_name),
                file=file_path or "unknown",
                line=line,
                contract=contract or None,
                confidence=confidence,
                tool_confidence="High" if confidence >= 0.9 else "Medium",
                raw=result,
                vkg_pattern=self.get_vkg_pattern(test_name),
            )

        except Exception as e:
            logger.error(f"Failed to convert Foundry result: {e}")
            return None

    def _build_description(
        self,
        test_name: str,
        reason: str,
        counterexample: Optional[Dict[str, Any]],
        logs: List[str],
    ) -> str:
        """Build description from test result.

        Args:
            test_name: Test function name
            reason: Failure reason
            counterexample: Counterexample from fuzz test
            logs: Test execution logs

        Returns:
            Human-readable description
        """
        desc = f"Forge test `{test_name}` failed."

        if reason:
            desc += f"\n\nReason: {reason}"

        if counterexample:
            desc += "\n\nCounterexample (fuzz):"
            if isinstance(counterexample, dict):
                for key, value in counterexample.items():
                    desc += f"\n  {key}: {value}"
            else:
                desc += f"\n  {counterexample}"

        if logs:
            # Include first few relevant logs
            relevant_logs = [
                log for log in logs[:5]
                if any(kw in log.lower() for kw in ["revert", "fail", "assert", "error"])
            ]
            if relevant_logs:
                desc += "\n\nRelevant logs:"
                for log in relevant_logs[:3]:
                    desc += f"\n  {log[:200]}"

        return desc

    @classmethod
    def get_expected_failure_prefixes(cls) -> List[str]:
        """Get list of test prefixes that indicate expected failures.

        Returns:
            List of expected failure prefixes
        """
        return [
            prefix for prefix, pattern in cls.TEST_PREFIX_TO_PATTERN.items()
            if pattern is None and "Fail" in prefix or "Revert" in prefix
        ]


def foundry_to_sarif(
    output: str,
    version: str = "0.0.0",
) -> Dict[str, Any]:
    """Convenience function to convert Foundry JSON output to SARIF.

    Args:
        output: JSON output from `forge test --json`
        version: Foundry version

    Returns:
        SARIF 2.1.0 document
    """
    adapter = FoundryAdapter()
    raw = adapter.parse_json(output)
    return adapter.to_sarif(raw, version)


def foundry_to_vkg_findings(output: str) -> List[VKGFinding]:
    """Convenience function to convert Foundry JSON output to VKG findings.

    Args:
        output: JSON output from `forge test --json`

    Returns:
        List of VKGFinding instances
    """
    adapter = FoundryAdapter()
    raw = adapter.parse_json(output)
    return adapter.to_vkg_findings(raw)


__all__ = [
    "FoundryAdapter",
    "foundry_to_sarif",
    "foundry_to_vkg_findings",
]
