#!/usr/bin/env python3
"""
Validate Testing Workflow Script.

This script validates that the testing workflow works correctly
by running a series of tests with increasing complexity.

Usage:
    uv run python scripts/validate_testing_workflow.py

Exit codes:
    0 - All tests passed
    1 - Some tests failed
    2 - Infrastructure issues
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

# Set up paths
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from alphaswarm_sol.testing.workflow import (
    SelfImprovingRunner,
    verify_claude_available,
    run_smoke_test,
    run_self_improving_smoke_test,
)


class ValidationResult(NamedTuple):
    """Result of a validation check."""
    name: str
    passed: bool
    message: str
    duration_ms: float = 0


def check_infrastructure() -> list[ValidationResult]:
    """Check that all infrastructure is available."""
    results = []

    # Check Claude CLI
    available, msg = verify_claude_available()
    results.append(ValidationResult(
        name="claude-cli",
        passed=available,
        message=msg,
    ))

    return results


def run_smoke_tests() -> list[ValidationResult]:
    """Run smoke tests."""
    results = []

    # Basic smoke test
    print("  Running basic smoke test...")
    try:
        smoke = run_smoke_test()
        # run_smoke_test returns individual status flags, not a single 'success' key
        all_passed = (
            smoke.get("claude_available", False) and
            smoke.get("session_created", False) and
            smoke.get("claude_launched", False) and
            smoke.get("prompt_sent", False) and
            smoke.get("response_received", False)
        )
        results.append(ValidationResult(
            name="basic-smoke",
            passed=all_passed,
            message=f"Session: {smoke.get('session_created', False)}, "
                   f"Claude: {smoke.get('claude_launched', False)}, "
                   f"Response: {smoke.get('response_received', False)}, "
                   f"Exit: {smoke.get('exit_clean', False)}",
            duration_ms=smoke.get("duration_ms", 0),
        ))
    except Exception as e:
        results.append(ValidationResult(
            name="basic-smoke",
            passed=False,
            message=f"Error: {e}",
        ))

    # Self-improving runner smoke test
    print("  Running self-improving smoke test...")
    try:
        smoke = run_self_improving_smoke_test()
        results.append(ValidationResult(
            name="self-improving-smoke",
            passed=smoke["success"],
            message=f"Retries: {smoke['retries']}, Issues: {smoke['issues']}",
            duration_ms=smoke["duration_ms"],
        ))
    except Exception as e:
        results.append(ValidationResult(
            name="self-improving-smoke",
            passed=False,
            message=f"Error: {e}",
        ))

    return results


def run_audit_test() -> list[ValidationResult]:
    """Run a realistic audit test."""
    results = []

    # Create test contract
    test_dir = Path("/tmp/vrs-validation-test")
    test_dir.mkdir(parents=True, exist_ok=True)

    contract = test_dir / "Vulnerable.sol"
    contract.write_text("""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Vulnerable {
    mapping(address => uint256) public balances;
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    // VULNERABILITY 1: Reentrancy
    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient");
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
        balances[msg.sender] -= amount;
    }

    // VULNERABILITY 2: No access control
    function setOwner(address newOwner) external {
        owner = newOwner;
    }

    // VULNERABILITY 3: Unchecked return
    function sendTokens(address token, address to, uint256 amount) external {
        // Unchecked external call return value
        token.call(abi.encodeWithSignature("transfer(address,uint256)", to, amount));
    }
}
""")

    print("  Running audit test on Vulnerable.sol...")
    runner = SelfImprovingRunner(max_retries=2, auto_fix=True)

    try:
        result = runner.run_test(
            name="audit-vulnerable",
            prompt="Read Vulnerable.sol and identify all security vulnerabilities. "
                   "List each vulnerability with its severity.",
            working_dir=str(test_dir),
            expected_markers=["reentrancy", "access control", "vulnerable"],
            timeout=120,
        )

        # Check if key vulnerabilities were found
        output_lower = result.output.lower()
        found_reentrancy = "reentrancy" in output_lower
        found_access = "access" in output_lower

        results.append(ValidationResult(
            name="audit-vulnerable",
            passed=result.success and found_reentrancy and found_access,
            message=f"Success: {result.success}, "
                   f"Found reentrancy: {found_reentrancy}, "
                   f"Found access control: {found_access}, "
                   f"Retries: {result.retries}",
            duration_ms=result.duration_ms,
        ))

        # Save report
        runner.save_report(result)

    except Exception as e:
        results.append(ValidationResult(
            name="audit-vulnerable",
            passed=False,
            message=f"Error: {e}",
        ))

    return results


def run_error_recovery_test() -> list[ValidationResult]:
    """Test error recovery capabilities."""
    results = []

    test_dir = Path("/tmp/vrs-recovery-test")
    test_dir.mkdir(parents=True, exist_ok=True)

    # Create a contract that will trigger retry due to missing marker
    contract = test_dir / "Simple.sol"
    contract.write_text("""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Simple {
    uint256 public value;

    function setValue(uint256 _value) external {
        value = _value;
    }
}
""")

    print("  Running error recovery test...")
    runner = SelfImprovingRunner(max_retries=2, auto_fix=True)

    try:
        # This should fail because there's no reentrancy in Simple.sol
        result = runner.run_test(
            name="recovery-test",
            prompt="Read Simple.sol and tell me what it does.",
            working_dir=str(test_dir),
            expected_markers=["value", "function"],  # These should be found
            timeout=60,
        )

        results.append(ValidationResult(
            name="error-recovery",
            passed=result.success,
            message=f"Success: {result.success}, Retries: {result.retries}, "
                   f"Issues: {[i.category.value for i in result.issues]}",
            duration_ms=result.duration_ms,
        ))

    except Exception as e:
        results.append(ValidationResult(
            name="error-recovery",
            passed=False,
            message=f"Error: {e}",
        ))

    return results


def main() -> int:
    """Run all validation tests."""
    print("=" * 60)
    print("Validating Testing Workflow")
    print("=" * 60)
    print()

    all_results = []

    # 1. Infrastructure checks
    print("1. Infrastructure Checks")
    print("-" * 40)
    infra_results = check_infrastructure()
    all_results.extend(infra_results)
    for r in infra_results:
        status = "✓" if r.passed else "✗"
        print(f"  {status} {r.name}: {r.message}")

    # Abort if infrastructure fails
    if not all(r.passed for r in infra_results):
        print()
        print("Infrastructure checks failed. Cannot continue.")
        return 2

    print()

    # 2. Smoke tests
    print("2. Smoke Tests")
    print("-" * 40)
    smoke_results = run_smoke_tests()
    all_results.extend(smoke_results)
    for r in smoke_results:
        status = "✓" if r.passed else "✗"
        duration = f"({r.duration_ms:.0f}ms)" if r.duration_ms else ""
        print(f"  {status} {r.name}: {r.message} {duration}")

    print()

    # 3. Audit test
    print("3. Audit Test")
    print("-" * 40)
    audit_results = run_audit_test()
    all_results.extend(audit_results)
    for r in audit_results:
        status = "✓" if r.passed else "✗"
        duration = f"({r.duration_ms:.0f}ms)" if r.duration_ms else ""
        print(f"  {status} {r.name}: {r.message} {duration}")

    print()

    # 4. Error recovery test
    print("4. Error Recovery Test")
    print("-" * 40)
    recovery_results = run_error_recovery_test()
    all_results.extend(recovery_results)
    for r in recovery_results:
        status = "✓" if r.passed else "✗"
        duration = f"({r.duration_ms:.0f}ms)" if r.duration_ms else ""
        print(f"  {status} {r.name}: {r.message} {duration}")

    print()

    # Summary
    print("=" * 60)
    passed = sum(1 for r in all_results if r.passed)
    total = len(all_results)
    print(f"Summary: {passed}/{total} tests passed")

    if passed == total:
        print("All tests passed! ✓")
        return 0
    else:
        print("Some tests failed. ✗")
        failed = [r for r in all_results if not r.passed]
        for r in failed:
            print(f"  - {r.name}: {r.message}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
