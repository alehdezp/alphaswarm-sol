#!/usr/bin/env python3
"""Agent E2E Validation Harness.

Validates the agent orchestration architecture end-to-end:
- OrchestratorTester flows: debate, verification, routing
- Supports mock, simulated, and live modes
- Optionally runs AuditTester E2E audit
- Captures pass/fail, assertion counts, and message traces

Usage:
    uv run python scripts/run_agent_e2e_validation.py --help
    uv run python scripts/run_agent_e2e_validation.py --mode simulated --runs 5
    uv run python scripts/run_agent_e2e_validation.py --mode live --runs 3 --output report.json

Phase: 07.3-ga-validation (Plan 03)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

# Add src to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from alphaswarm_sol.testing.integration.orchestrator_tester import (
    OrchestratorTester,
    InvocationMode,
    StepAssertion,
    FlowTestResult,
)
from alphaswarm_sol.testing.integration.flow_simulator import FlowOutcome

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class FlowValidationResult:
    """Result of validating a single flow type."""

    flow_type: str
    runs_passed: int
    runs_failed: int
    total_runs: int
    assertions_passed: int
    assertions_failed: int
    avg_steps: float
    avg_messages: float
    avg_duration_ms: float
    errors: list[str] = field(default_factory=list)
    test_results: list[dict] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate as percentage."""
        if self.total_runs == 0:
            return 0.0
        return (self.runs_passed / self.total_runs) * 100


@dataclass
class E2EValidationReport:
    """Complete E2E validation report."""

    # Metadata
    timestamp: str
    mode: str
    total_runs: int
    api_key_available: bool

    # Flow results
    debate_flow: FlowValidationResult | None = None
    verification_flow: FlowValidationResult | None = None
    routing_flow: FlowValidationResult | None = None
    audit_flow: dict | None = None

    # Aggregate metrics
    overall_pass_rate: float = 0.0
    total_flows_passed: int = 0
    total_flows_failed: int = 0
    total_duration_ms: int = 0

    # Limitations
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "metadata": {
                "timestamp": self.timestamp,
                "mode": self.mode,
                "total_runs": self.total_runs,
                "api_key_available": self.api_key_available,
            },
            "flows": {},
            "aggregate": {
                "overall_pass_rate": self.overall_pass_rate,
                "total_flows_passed": self.total_flows_passed,
                "total_flows_failed": self.total_flows_failed,
                "total_duration_ms": self.total_duration_ms,
            },
            "limitations": self.limitations,
        }

        if self.debate_flow:
            result["flows"]["debate"] = asdict(self.debate_flow)
        if self.verification_flow:
            result["flows"]["verification"] = asdict(self.verification_flow)
        if self.routing_flow:
            result["flows"]["routing"] = asdict(self.routing_flow)
        if self.audit_flow:
            result["flows"]["audit"] = self.audit_flow

        return result


def create_debate_test_cases() -> list[dict]:
    """Create test cases for debate flow validation."""
    return [
        {
            "name": "reentrancy_high_confidence",
            "bead_data": {
                "id": "bead-reentrancy-001",
                "finding": {
                    "pattern": "reentrancy-classic",
                    "severity": "critical",
                    "location": "Vault.withdraw:45",
                    "confidence": 0.85,
                },
                "type": "finding",
                "severity": "critical",
            },
            "expected_outcome": FlowOutcome.CONFIRMED,
            "attacker_response": {
                "claim": "Reentrancy vulnerability in withdraw function",
                "exploit_path": ["call withdraw", "reenter via fallback", "drain funds"],
                "confidence": 0.85,
            },
            "defender_response": {
                "counterclaim": "No effective guard detected",
                "guards": [],
                "strength": 0.2,
            },
        },
        {
            "name": "false_positive_guarded",
            "bead_data": {
                "id": "bead-fp-001",
                "finding": {
                    "pattern": "reentrancy-classic",
                    "severity": "high",
                    "location": "SafeVault.withdraw:50",
                    "confidence": 0.6,
                },
                "type": "finding",
                "severity": "high",
            },
            "expected_outcome": FlowOutcome.REJECTED,
            "attacker_response": {
                "claim": "Potential reentrancy",
                "exploit_path": ["call withdraw"],
                "confidence": 0.5,
            },
            "defender_response": {
                "counterclaim": "ReentrancyGuard prevents attack",
                "guards": ["ReentrancyGuard", "nonReentrant modifier"],
                "strength": 0.9,
            },
        },
        {
            "name": "uncertain_needs_review",
            "bead_data": {
                "id": "bead-uncertain-001",
                "finding": {
                    "pattern": "access-control-missing",
                    "severity": "medium",
                    "location": "Admin.setFee:30",
                    "confidence": 0.5,
                },
                "type": "finding",
                "severity": "medium",
            },
            "expected_outcome": FlowOutcome.UNCERTAIN,
            "attacker_response": {
                "claim": "Missing access control",
                "exploit_path": ["anyone can call setFee"],
                "confidence": 0.55,
            },
            "defender_response": {
                "counterclaim": "Implicit control via contract ownership",
                "guards": ["implicit owner check in modifier"],
                "strength": 0.5,
            },
        },
    ]


def create_verification_test_cases() -> list[dict]:
    """Create test cases for verification flow validation."""
    return [
        {
            "name": "high_confidence_verified",
            "finding": {
                "id": "finding-001",
                "pattern": "oracle-manipulation",
                "severity": "critical",
                "confidence": 0.9,
            },
            "expected_status": "VERIFIED",
        },
        {
            "name": "low_confidence_refuted",
            "finding": {
                "id": "finding-002",
                "pattern": "unchecked-return",
                "severity": "low",
                "confidence": 0.2,
            },
            "expected_status": "REFUTED",
        },
        {
            "name": "medium_needs_evidence",
            "finding": {
                "id": "finding-003",
                "pattern": "front-running",
                "severity": "medium",
                "confidence": 0.5,
            },
            "expected_status": "NEEDS_MORE_EVIDENCE",
        },
    ]


def create_routing_test_cases() -> list[dict]:
    """Create test cases for routing flow validation."""
    return [
        {
            "name": "critical_routes_to_debate",
            "bead": {
                "id": "bead-critical-001",
                "type": "finding",
                "severity": "critical",
                "pattern": "reentrancy",
            },
            "expected_route": "debate",
            "expected_agents": ["vkg-attacker", "vkg-defender", "vkg-verifier"],
        },
        {
            "name": "high_routes_to_debate",
            "bead": {
                "id": "bead-high-001",
                "type": "finding",
                "severity": "high",
                "pattern": "access-control",
            },
            "expected_route": "debate",
            "expected_agents": ["vkg-attacker", "vkg-defender", "vkg-verifier"],
        },
        {
            "name": "medium_routes_to_verification",
            "bead": {
                "id": "bead-medium-001",
                "type": "finding",
                "severity": "medium",
                "pattern": "unchecked-call",
            },
            "expected_route": "direct_verification",
            "expected_agents": ["vkg-verifier"],
        },
    ]


def run_debate_validation(
    tester: OrchestratorTester,
    runs: int,
) -> FlowValidationResult:
    """Run debate flow validation."""
    test_cases = create_debate_test_cases()

    result = FlowValidationResult(
        flow_type="debate",
        runs_passed=0,
        runs_failed=0,
        total_runs=0,
        assertions_passed=0,
        assertions_failed=0,
        avg_steps=0.0,
        avg_messages=0.0,
        avg_duration_ms=0.0,
    )

    total_steps = 0
    total_messages = 0
    total_duration = 0

    for run_idx in range(runs):
        for test_case in test_cases:
            result.total_runs += 1

            # Configure agent responses
            tester.configure_agent_response(
                "vkg-attacker", "claim", test_case["attacker_response"]
            )
            tester.configure_agent_response(
                "vkg-defender", "counterclaim", test_case["defender_response"]
            )

            # Run test
            start = time.monotonic()
            test_result = tester.test_debate_flow(
                test_name=f"{test_case['name']}_run{run_idx}",
                bead_data=test_case["bead_data"],
                expected_outcome=test_case["expected_outcome"],
            )
            duration = int((time.monotonic() - start) * 1000)

            if test_result.passed:
                result.runs_passed += 1
            else:
                result.runs_failed += 1
                if test_result.error:
                    result.errors.append(f"{test_case['name']}: {test_result.error}")

            result.assertions_passed += test_result.assertions_passed
            result.assertions_failed += test_result.assertions_failed

            total_steps += test_result.total_steps
            total_messages += test_result.total_messages
            total_duration += duration

            result.test_results.append({
                "name": test_result.test_name,
                "passed": test_result.passed,
                "steps": test_result.total_steps,
                "messages": test_result.total_messages,
                "duration_ms": duration,
            })

    if result.total_runs > 0:
        result.avg_steps = total_steps / result.total_runs
        result.avg_messages = total_messages / result.total_runs
        result.avg_duration_ms = total_duration / result.total_runs

    return result


def run_verification_validation(
    tester: OrchestratorTester,
    runs: int,
) -> FlowValidationResult:
    """Run verification flow validation."""
    test_cases = create_verification_test_cases()

    result = FlowValidationResult(
        flow_type="verification",
        runs_passed=0,
        runs_failed=0,
        total_runs=0,
        assertions_passed=0,
        assertions_failed=0,
        avg_steps=0.0,
        avg_messages=0.0,
        avg_duration_ms=0.0,
    )

    total_steps = 0
    total_messages = 0
    total_duration = 0

    for run_idx in range(runs):
        for test_case in test_cases:
            result.total_runs += 1

            start = time.monotonic()
            test_result = tester.test_verification_flow(
                test_name=f"{test_case['name']}_run{run_idx}",
                finding=test_case["finding"],
                expected_status=test_case["expected_status"],
            )
            duration = int((time.monotonic() - start) * 1000)

            if test_result.passed:
                result.runs_passed += 1
            else:
                result.runs_failed += 1
                if test_result.error:
                    result.errors.append(f"{test_case['name']}: {test_result.error}")

            result.assertions_passed += test_result.assertions_passed
            result.assertions_failed += test_result.assertions_failed

            total_steps += test_result.total_steps
            total_messages += test_result.total_messages
            total_duration += duration

            result.test_results.append({
                "name": test_result.test_name,
                "passed": test_result.passed,
                "steps": test_result.total_steps,
                "messages": test_result.total_messages,
                "duration_ms": duration,
            })

    if result.total_runs > 0:
        result.avg_steps = total_steps / result.total_runs
        result.avg_messages = total_messages / result.total_runs
        result.avg_duration_ms = total_duration / result.total_runs

    return result


def run_routing_validation(
    tester: OrchestratorTester,
    runs: int,
) -> FlowValidationResult:
    """Run routing flow validation."""
    test_cases = create_routing_test_cases()

    result = FlowValidationResult(
        flow_type="routing",
        runs_passed=0,
        runs_failed=0,
        total_runs=0,
        assertions_passed=0,
        assertions_failed=0,
        avg_steps=0.0,
        avg_messages=0.0,
        avg_duration_ms=0.0,
    )

    total_steps = 0
    total_messages = 0
    total_duration = 0

    for run_idx in range(runs):
        for test_case in test_cases:
            result.total_runs += 1

            start = time.monotonic()
            test_result = tester.test_routing_flow(
                test_name=f"{test_case['name']}_run{run_idx}",
                bead=test_case["bead"],
                expected_route=test_case["expected_route"],
                expected_agents=test_case["expected_agents"],
            )
            duration = int((time.monotonic() - start) * 1000)

            if test_result.passed:
                result.runs_passed += 1
            else:
                result.runs_failed += 1
                if test_result.error:
                    result.errors.append(f"{test_case['name']}: {test_result.error}")

            result.assertions_passed += test_result.assertions_passed
            result.assertions_failed += test_result.assertions_failed

            total_steps += test_result.total_steps
            total_messages += test_result.total_messages
            total_duration += duration

            result.test_results.append({
                "name": test_result.test_name,
                "passed": test_result.passed,
                "steps": test_result.total_steps,
                "messages": test_result.total_messages,
                "duration_ms": duration,
            })

    if result.total_runs > 0:
        result.avg_steps = total_steps / result.total_runs
        result.avg_messages = total_messages / result.total_runs
        result.avg_duration_ms = total_duration / result.total_runs

    return result


def run_audit_validation(
    mode: InvocationMode,
    contract_sample: int,
) -> dict:
    """Run optional AuditTester E2E validation."""
    from alphaswarm_sol.testing.e2e.audit_tester import AuditTester

    # Get sample contracts
    contracts_dir = project_root / "tests" / "contracts"
    contracts = sorted(contracts_dir.glob("*.sol"))[:contract_sample]

    if not contracts:
        return {
            "status": "skipped",
            "reason": "No contracts found in tests/contracts/",
        }

    audit_mode = "mock"
    if mode == InvocationMode.SIMULATED:
        audit_mode = "direct"
    elif mode == InvocationMode.LIVE:
        audit_mode = "cli"

    tester = AuditTester(
        project_root=project_root,
        mode=audit_mode,
        default_timeout=60,
    )

    start = time.monotonic()
    result = tester.run_audit(
        test_name="e2e_sample_audit",
        contracts=[str(c) for c in contracts],
        verify_all=True,
        use_debate=True,
    )
    duration = int((time.monotonic() - start) * 1000)

    return {
        "status": "completed",
        "passed": result.passed,
        "contracts_audited": len(contracts),
        "findings_count": result.finding_count,
        "verified_count": result.verified_count,
        "phases_completed": len([p for p in result.phases if p.succeeded]),
        "phases_total": len(result.phases),
        "duration_ms": duration,
        "error": result.error,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Agent E2E Validation Harness for GA Validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run in mock mode (fast, no API needed)
  uv run python scripts/run_agent_e2e_validation.py --mode mock

  # Run in simulated mode with 5 iterations
  uv run python scripts/run_agent_e2e_validation.py --mode simulated --runs 5

  # Run in live mode (requires ANTHROPIC_API_KEY)
  uv run python scripts/run_agent_e2e_validation.py --mode live --runs 3

  # Include audit E2E validation
  uv run python scripts/run_agent_e2e_validation.py --mode mock --contract-sample 3
        """
    )

    parser.add_argument(
        "--mode",
        choices=["mock", "simulated", "live"],
        default="mock",
        help="Invocation mode: mock (fast), simulated (deterministic), live (real API)"
    )

    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="Number of runs per flow type (default: 3)"
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".vrs/testing/reports/agent-e2e.json"),
        help="Output path for JSON report"
    )

    parser.add_argument(
        "--contract-sample",
        type=int,
        default=0,
        help="Number of contracts for audit E2E test (0 = skip)"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Check API key availability
    api_key_available = bool(os.environ.get("ANTHROPIC_API_KEY"))

    # Map mode string to InvocationMode enum
    mode_map = {
        "mock": InvocationMode.MOCK,
        "simulated": InvocationMode.SIMULATED,
        "live": InvocationMode.LIVE,
    }
    mode = mode_map[args.mode]

    # Check if live mode is requested but API key missing
    limitations = []
    if args.mode == "live" and not api_key_available:
        logger.warning("ANTHROPIC_API_KEY not set, falling back to simulated mode")
        mode = InvocationMode.SIMULATED
        limitations.append(
            "Live mode requested but ANTHROPIC_API_KEY not available. "
            "Fell back to simulated mode."
        )

    logger.info(f"Starting Agent E2E Validation (mode={mode.value}, runs={args.runs})")

    # Initialize tester
    tester = OrchestratorTester(mode=mode)

    # Create report
    report = E2EValidationReport(
        timestamp=datetime.utcnow().isoformat() + "Z",
        mode=mode.value,
        total_runs=args.runs,
        api_key_available=api_key_available,
        limitations=limitations,
    )

    start_time = time.monotonic()

    # Run debate flow validation
    logger.info("Running debate flow validation...")
    report.debate_flow = run_debate_validation(tester, args.runs)
    logger.info(
        f"Debate flow: {report.debate_flow.runs_passed}/{report.debate_flow.total_runs} passed "
        f"({report.debate_flow.pass_rate:.1f}%)"
    )

    # Run verification flow validation
    logger.info("Running verification flow validation...")
    report.verification_flow = run_verification_validation(tester, args.runs)
    logger.info(
        f"Verification flow: {report.verification_flow.runs_passed}/{report.verification_flow.total_runs} passed "
        f"({report.verification_flow.pass_rate:.1f}%)"
    )

    # Run routing flow validation
    logger.info("Running routing flow validation...")
    report.routing_flow = run_routing_validation(tester, args.runs)
    logger.info(
        f"Routing flow: {report.routing_flow.runs_passed}/{report.routing_flow.total_runs} passed "
        f"({report.routing_flow.pass_rate:.1f}%)"
    )

    # Optional: Run audit E2E validation
    if args.contract_sample > 0:
        logger.info(f"Running audit E2E validation with {args.contract_sample} contracts...")
        report.audit_flow = run_audit_validation(mode, args.contract_sample)
        logger.info(f"Audit E2E: {report.audit_flow.get('status')}")

    # Calculate aggregate metrics
    total_passed = (
        report.debate_flow.runs_passed +
        report.verification_flow.runs_passed +
        report.routing_flow.runs_passed
    )
    total_runs = (
        report.debate_flow.total_runs +
        report.verification_flow.total_runs +
        report.routing_flow.total_runs
    )

    report.total_flows_passed = total_passed
    report.total_flows_failed = total_runs - total_passed
    report.overall_pass_rate = (total_passed / total_runs * 100) if total_runs > 0 else 0.0
    report.total_duration_ms = int((time.monotonic() - start_time) * 1000)

    # Ensure output directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Write report
    with open(args.output, "w") as f:
        json.dump(report.to_dict(), f, indent=2)

    logger.info(f"Report written to {args.output}")

    # Print summary
    print("\n" + "=" * 60)
    print("AGENT E2E VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Mode: {mode.value}")
    print(f"Total Runs: {total_runs}")
    print(f"Overall Pass Rate: {report.overall_pass_rate:.1f}%")
    print()
    print("Flow Results:")
    print(f"  Debate:       {report.debate_flow.runs_passed}/{report.debate_flow.total_runs} ({report.debate_flow.pass_rate:.1f}%)")
    print(f"  Verification: {report.verification_flow.runs_passed}/{report.verification_flow.total_runs} ({report.verification_flow.pass_rate:.1f}%)")
    print(f"  Routing:      {report.routing_flow.runs_passed}/{report.routing_flow.total_runs} ({report.routing_flow.pass_rate:.1f}%)")
    print()
    print(f"Duration: {report.total_duration_ms}ms")

    if report.limitations:
        print("\nLimitations:")
        for lim in report.limitations:
            print(f"  - {lim}")

    # Exit with appropriate code
    gate_pass_rate = 95.0
    if report.overall_pass_rate >= gate_pass_rate:
        print(f"\n[PASS] Pass rate {report.overall_pass_rate:.1f}% >= {gate_pass_rate}% gate")
        return 0
    else:
        print(f"\n[FAIL] Pass rate {report.overall_pass_rate:.1f}% < {gate_pass_rate}% gate")
        return 1


if __name__ == "__main__":
    sys.exit(main())
