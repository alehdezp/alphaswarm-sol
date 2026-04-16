"""Foundry CLI Integration for Test Builder Agent.

This module provides the FoundryRunner class for executing Foundry commands
(forge build, forge test) from the Test Builder agent.

Per 05.2-CONTEXT.md:
- Full shell access for agents
- Tests stored in pool directory
- Passing exploit test elevates confidence to "confirmed"

Usage:
    from alphaswarm_sol.agents.roles import FoundryRunner, ForgeTestResult

    runner = FoundryRunner(project_path)

    # Write a test file
    runner.write_test(test_code, "test/Exploit.t.sol")

    # Compile
    build_result = runner.build()
    if build_result.success:
        # Run tests
        test_results = runner.test(test_file="test/Exploit.t.sol")
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ForgeTestResult:
    """Result of running forge test.

    Attributes:
        test_name: Name of the test (contract::function format)
        passed: Whether the test passed
        gas_used: Gas consumed by the test
        duration_ms: Time taken to run the test
        failure_reason: Reason for failure if test failed
        stdout: Raw stdout from forge
        stderr: Raw stderr from forge
    """
    test_name: str
    passed: bool
    gas_used: Optional[int] = None
    duration_ms: Optional[int] = None
    failure_reason: Optional[str] = None
    stdout: str = ""
    stderr: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "test_name": self.test_name,
            "passed": self.passed,
            "gas_used": self.gas_used,
            "duration_ms": self.duration_ms,
            "failure_reason": self.failure_reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ForgeTestResult":
        """Create from dictionary."""
        return cls(
            test_name=data.get("test_name", "unknown"),
            passed=data.get("passed", False),
            gas_used=data.get("gas_used"),
            duration_ms=data.get("duration_ms"),
            failure_reason=data.get("failure_reason"),
            stdout=data.get("stdout", ""),
            stderr=data.get("stderr", ""),
        )


@dataclass
class ForgeBuildResult:
    """Result of running forge build.

    Attributes:
        success: Whether compilation succeeded
        errors: List of compilation errors
        warnings: List of compilation warnings
        stdout: Raw stdout from forge
        stderr: Raw stderr from forge
    """
    success: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "errors": self.errors,
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ForgeBuildResult":
        """Create from dictionary."""
        return cls(
            success=data.get("success", False),
            errors=data.get("errors", []),
            warnings=data.get("warnings", []),
            stdout=data.get("stdout", ""),
            stderr=data.get("stderr", ""),
        )


class FoundryRunner:
    """Execute Foundry commands (forge build, forge test).

    Per 05.2-CONTEXT.md: Full shell access for agents.
    Tests stored in pool directory per context decision.

    Attributes:
        project_path: Path to the Foundry project root

    Usage:
        runner = FoundryRunner(Path("/path/to/project"))

        # Write test
        runner.write_test("// test code", "test/Exploit.t.sol")

        # Build
        result = runner.build()
        if result.success:
            # Run tests
            tests = runner.test()
    """

    def __init__(self, project_path: Path):
        """Initialize the Foundry runner.

        Args:
            project_path: Path to the Foundry project root directory

        Raises:
            RuntimeError: If forge is not available in PATH
        """
        self.project_path = Path(project_path)
        self._validate_foundry_available()

    def _validate_foundry_available(self) -> None:
        """Check that forge is available in PATH.

        Raises:
            RuntimeError: If forge is not found
        """
        if not shutil.which("forge"):
            raise RuntimeError(
                "forge not found in PATH. Install foundry: "
                "curl -L https://foundry.paradigm.xyz | bash && foundryup"
            )

    def build(self, extra_args: Optional[List[str]] = None) -> ForgeBuildResult:
        """Run forge build to compile contracts.

        Args:
            extra_args: Additional arguments to pass to forge build

        Returns:
            ForgeBuildResult with success status and any errors/warnings
        """
        cmd = ["forge", "build"]
        if extra_args:
            cmd.extend(extra_args)

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=120,  # 2 min timeout for compilation
            )
        except subprocess.TimeoutExpired:
            return ForgeBuildResult(
                success=False,
                errors=["Build timed out after 120 seconds"],
                stdout="",
                stderr="",
            )
        except Exception as e:
            return ForgeBuildResult(
                success=False,
                errors=[f"Build failed with exception: {e}"],
                stdout="",
                stderr="",
            )

        errors = []
        warnings = []

        # Parse output for errors/warnings
        combined_output = result.stdout + result.stderr
        for line in combined_output.split("\n"):
            line_lower = line.lower()
            if "error" in line_lower and line.strip():
                errors.append(line.strip())
            elif "warning" in line_lower and line.strip():
                warnings.append(line.strip())

        return ForgeBuildResult(
            success=result.returncode == 0,
            errors=errors,
            warnings=warnings,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    def test(
        self,
        test_file: Optional[str] = None,
        test_function: Optional[str] = None,
        verbosity: int = 2,
        gas_report: bool = False,
        fork_url: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
    ) -> List[ForgeTestResult]:
        """Run forge test and capture results.

        Args:
            test_file: Specific test file to run (e.g., "test/Exploit.t.sol")
            test_function: Specific function to run (e.g., "test_reentrancy_exploit")
            verbosity: -v level (0-5), default 2
            gas_report: Include gas report in output
            fork_url: RPC URL for forked testing
            extra_args: Additional arguments to pass to forge test

        Returns:
            List of ForgeTestResult objects for each test
        """
        cmd = ["forge", "test"]

        # Add verbosity
        if verbosity > 0:
            cmd.append(f"-{'v' * verbosity}")

        if test_file:
            cmd.extend(["--match-path", test_file])
        if test_function:
            cmd.extend(["--match-test", test_function])
        if gas_report:
            cmd.append("--gas-report")
        if fork_url:
            cmd.extend(["--fork-url", fork_url])
        if extra_args:
            cmd.extend(extra_args)

        # Use JSON output for structured parsing
        cmd.append("--json")

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=300,  # 5 min timeout for tests
            )
        except subprocess.TimeoutExpired:
            return [ForgeTestResult(
                test_name="timeout",
                passed=False,
                failure_reason="Test execution timed out after 300 seconds",
            )]
        except Exception as e:
            return [ForgeTestResult(
                test_name="error",
                passed=False,
                failure_reason=f"Test execution failed: {e}",
            )]

        return self._parse_test_output(result.stdout, result.stderr, result.returncode)

    def _parse_test_output(
        self, stdout: str, stderr: str, returncode: int
    ) -> List[ForgeTestResult]:
        """Parse forge test JSON output into ForgeTestResult objects.

        Args:
            stdout: Standard output from forge test
            stderr: Standard error from forge test
            returncode: Process return code

        Returns:
            List of ForgeTestResult objects
        """
        results = []

        try:
            # forge test --json outputs JSON per line
            for line in stdout.strip().split("\n"):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    # Parse based on forge test JSON format
                    # Format varies by forge version, handle multiple formats
                    if "test_results" in data:
                        for contract, tests in data["test_results"].items():
                            if isinstance(tests, dict):
                                for test_name, test_data in tests.items():
                                    if isinstance(test_data, dict):
                                        results.append(ForgeTestResult(
                                            test_name=f"{contract}::{test_name}",
                                            passed=test_data.get("status") == "Success",
                                            gas_used=test_data.get("gas"),
                                            duration_ms=test_data.get("duration_ms"),
                                            failure_reason=test_data.get("reason"),
                                            stdout=stdout,
                                            stderr=stderr,
                                        ))
                    # Alternative format: direct test results
                    elif "status" in data and "name" in data:
                        results.append(ForgeTestResult(
                            test_name=data.get("name", "unknown"),
                            passed=data.get("status") == "Success",
                            gas_used=data.get("gas"),
                            duration_ms=data.get("duration"),
                            failure_reason=data.get("reason"),
                            stdout=stdout,
                            stderr=stderr,
                        ))
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            logger.warning(f"Failed to parse forge output: {e}")

        # Fallback: if no results parsed, try to extract from stderr/stdout
        if not results:
            results = self._fallback_parse(stdout, stderr, returncode)

        return results

    def _fallback_parse(
        self, stdout: str, stderr: str, returncode: int
    ) -> List[ForgeTestResult]:
        """Fallback parsing when JSON parsing fails.

        Args:
            stdout: Standard output from forge test
            stderr: Standard error from forge test
            returncode: Process return code

        Returns:
            List of ForgeTestResult objects extracted from text output
        """
        results = []
        combined = stdout + stderr

        # Try to find test results in text format
        # Pattern: [PASS] test_name (gas: 12345)
        # Pattern: [FAIL] test_name
        pass_pattern = re.compile(r"\[PASS\]\s+(\S+)(?:\s+\(gas:\s+(\d+)\))?")
        fail_pattern = re.compile(r"\[FAIL\.\s*(\w+)\]\s+(\S+)(?:.*?Reason:\s*(.+))?")

        for match in pass_pattern.finditer(combined):
            results.append(ForgeTestResult(
                test_name=match.group(1),
                passed=True,
                gas_used=int(match.group(2)) if match.group(2) else None,
                stdout=stdout,
                stderr=stderr,
            ))

        for match in fail_pattern.finditer(combined):
            results.append(ForgeTestResult(
                test_name=match.group(2),
                passed=False,
                failure_reason=match.group(3) if match.group(3) else match.group(1),
                stdout=stdout,
                stderr=stderr,
            ))

        # If still no results, create single result from return code
        if not results:
            results.append(ForgeTestResult(
                test_name="unknown",
                passed=returncode == 0,
                failure_reason=stderr.strip() if returncode != 0 else None,
                stdout=stdout,
                stderr=stderr,
            ))

        return results

    def write_test(self, test_code: str, test_file: str) -> Path:
        """Write test code to test file in project.

        Args:
            test_code: Solidity test source code
            test_file: Relative path to test file (e.g., "test/Exploit.t.sol")

        Returns:
            Path to the written test file
        """
        test_path = self.project_path / test_file
        test_path.parent.mkdir(parents=True, exist_ok=True)
        test_path.write_text(test_code)
        logger.info(f"Wrote test to {test_path}")
        return test_path

    def init_project(self) -> ForgeBuildResult:
        """Initialize a new Foundry project if not already initialized.

        Returns:
            ForgeBuildResult indicating success/failure of initialization
        """
        foundry_toml = self.project_path / "foundry.toml"
        if foundry_toml.exists():
            return ForgeBuildResult(
                success=True,
                warnings=["Project already initialized"],
                stdout="",
                stderr="",
            )

        try:
            result = subprocess.run(
                ["forge", "init", "--no-commit", "."],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=60,
            )
            return ForgeBuildResult(
                success=result.returncode == 0,
                errors=[result.stderr] if result.returncode != 0 else [],
                stdout=result.stdout,
                stderr=result.stderr,
            )
        except Exception as e:
            return ForgeBuildResult(
                success=False,
                errors=[f"Initialization failed: {e}"],
                stdout="",
                stderr="",
            )

    def clean(self) -> bool:
        """Run forge clean to remove build artifacts.

        Returns:
            True if clean succeeded
        """
        try:
            result = subprocess.run(
                ["forge", "clean"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode == 0
        except Exception:
            return False


# Export for module
__all__ = [
    "ForgeTestResult",
    "ForgeBuildResult",
    "FoundryRunner",
]
