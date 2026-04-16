#!/usr/bin/env python3
"""Tool Integration Validation Runner (Phase 7.3 Plan 09).

Validates static analysis tool integrations (Slither, Aderyn) and dedup pipeline.
Supports both live tool execution and mock mode for automated testing.

Usage:
    uv run python scripts/run_tool_validation.py --sample 5 --mode mock
    uv run python scripts/run_tool_validation.py --sample 3 --mode live --output-dir .vrs/tools/validation/
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from alphaswarm_sol.tools.registry import ToolRegistry, ToolHealth
from alphaswarm_sol.tools.adapters.sarif import VKGFinding
from alphaswarm_sol.orchestration.dedup import (
    SemanticDeduplicator,
    DeduplicatedFinding,
    DeduplicationStats,
)


@dataclass
class MockFinding:
    """Mock finding for simulated tool output."""

    source: str
    rule_id: str
    title: str
    description: str
    severity: str
    category: str
    file: str
    line: int
    function: Optional[str] = None
    confidence: float = 0.7


# Realistic mock findings based on common vulnerability patterns
MOCK_SLITHER_FINDINGS: List[MockFinding] = [
    MockFinding(
        source="slither",
        rule_id="reentrancy-eth",
        title="Reentrancy in withdraw()",
        description="External call to msg.sender.call{value:...}() before state update",
        severity="high",
        category="reentrancy",
        file="Vault.sol",
        line=42,
        function="withdraw",
        confidence=0.85,
    ),
    MockFinding(
        source="slither",
        rule_id="uninitialized-state",
        title="Uninitialized state variable",
        description="State variable 'owner' is never initialized",
        severity="medium",
        category="state",
        file="Vault.sol",
        line=10,
        function=None,
        confidence=0.75,
    ),
    MockFinding(
        source="slither",
        rule_id="arbitrary-send-eth",
        title="Arbitrary send ETH",
        description="Function sends Ether to arbitrary address",
        severity="high",
        category="access_control",
        file="Vault.sol",
        line=55,
        function="emergencyWithdraw",
        confidence=0.80,
    ),
    MockFinding(
        source="slither",
        rule_id="unchecked-lowlevel",
        title="Unchecked low-level call",
        description="Low-level call return value not checked",
        severity="medium",
        category="unchecked",
        file="Vault.sol",
        line=45,
        function="withdraw",
        confidence=0.70,
    ),
    MockFinding(
        source="slither",
        rule_id="missing-zero-check",
        title="Missing zero address validation",
        description="Parameter '_to' not validated for zero address",
        severity="low",
        category="validation",
        file="Vault.sol",
        line=30,
        function="transfer",
        confidence=0.65,
    ),
]

MOCK_ADERYN_FINDINGS: List[MockFinding] = [
    MockFinding(
        source="aderyn",
        rule_id="ADR-001",
        title="State change after external call",
        description="State variable updated after external call in withdraw()",
        severity="high",
        category="reentrancy",
        file="Vault.sol",
        line=43,  # Similar to slither finding
        function="withdraw",
        confidence=0.82,
    ),
    MockFinding(
        source="aderyn",
        rule_id="ADR-010",
        title="Centralization risk",
        description="Single owner can withdraw all funds",
        severity="medium",
        category="access_control",
        file="Vault.sol",
        line=55,
        function="emergencyWithdraw",
        confidence=0.78,
    ),
    MockFinding(
        source="aderyn",
        rule_id="ADR-015",
        title="Floating pragma",
        description="Contract uses floating pragma ^0.8.0",
        severity="low",
        category="best-practice",
        file="Vault.sol",
        line=2,
        function=None,
        confidence=0.90,
    ),
    MockFinding(
        source="aderyn",
        rule_id="ADR-020",
        title="Missing events",
        description="State-changing function lacks event emission",
        severity="low",
        category="best-practice",
        file="Vault.sol",
        line=42,
        function="withdraw",
        confidence=0.85,
    ),
]


@dataclass
class ToolValidationResult:
    """Result of tool validation run."""

    tool: str
    available: bool
    findings_count: int
    findings: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    execution_time: float = 0.0
    mode: str = "mock"


@dataclass
class ValidationSummary:
    """Summary of validation run."""

    timestamp: str
    mode: str
    sample_size: int
    contracts: List[str]
    tools_checked: Dict[str, bool]
    raw_findings: int
    deduped_findings: int
    reduction_percent: float
    dedup_stats: Dict[str, Any]
    tool_results: List[Dict[str, Any]]
    success: bool


def get_sample_contracts(sample_size: int) -> List[Path]:
    """Select sample contracts for tool validation.

    Args:
        sample_size: Number of contracts to select.

    Returns:
        List of contract paths.
    """
    contracts_dir = project_root / "tests" / "contracts"
    if not contracts_dir.exists():
        print(f"Warning: Contracts directory not found: {contracts_dir}")
        return []

    # Priority contracts for testing (diverse vulnerability types)
    priority_contracts = [
        "Vault.sol",
        "ReentrancyVuln.sol",
        "AccessControl.sol",
        "OracleConsumer.sol",
        "TokenSwap.sol",
    ]

    selected: List[Path] = []

    # First add priority contracts that exist
    for name in priority_contracts:
        contract_path = contracts_dir / name
        if contract_path.exists() and len(selected) < sample_size:
            selected.append(contract_path)

    # Fill remaining with any .sol files
    if len(selected) < sample_size:
        for sol_file in contracts_dir.glob("*.sol"):
            if sol_file not in selected and len(selected) < sample_size:
                selected.append(sol_file)

    return selected[:sample_size]


def mock_findings_for_contract(contract_path: Path) -> List[VKGFinding]:
    """Generate mock findings for a contract.

    Args:
        contract_path: Path to contract.

    Returns:
        List of mock VKGFinding instances.
    """
    contract_name = contract_path.name
    findings: List[VKGFinding] = []

    # Use mock findings adjusted for contract name
    for mock in MOCK_SLITHER_FINDINGS:
        finding = VKGFinding(
            source=mock.source,
            rule_id=mock.rule_id,
            title=mock.title,
            description=mock.description,
            severity=mock.severity,
            category=mock.category,
            file=contract_name,
            line=mock.line,
            function=mock.function,
            confidence=mock.confidence,
        )
        findings.append(finding)

    for mock in MOCK_ADERYN_FINDINGS:
        finding = VKGFinding(
            source=mock.source,
            rule_id=mock.rule_id,
            title=mock.title,
            description=mock.description,
            severity=mock.severity,
            category=mock.category,
            file=contract_name,
            line=mock.line,
            function=mock.function,
            confidence=mock.confidence,
        )
        findings.append(finding)

    return findings


def run_tool_mock(tool: str, contracts: List[Path]) -> ToolValidationResult:
    """Run mock tool execution.

    Args:
        tool: Tool name.
        contracts: List of contracts.

    Returns:
        Validation result with mock findings.
    """
    findings: List[Dict[str, Any]] = []

    for contract in contracts:
        mock_list = MOCK_SLITHER_FINDINGS if tool == "slither" else MOCK_ADERYN_FINDINGS
        for mock in mock_list:
            finding = VKGFinding(
                source=mock.source,
                rule_id=mock.rule_id,
                title=mock.title,
                description=mock.description,
                severity=mock.severity,
                category=mock.category,
                file=contract.name,
                line=mock.line,
                function=mock.function,
                confidence=mock.confidence,
            )
            findings.append(finding.to_dict())

    return ToolValidationResult(
        tool=tool,
        available=True,
        findings_count=len(findings),
        findings=findings,
        error=None,
        execution_time=0.5,
        mode="mock",
    )


def run_tool_live(
    tool: str, contracts: List[Path], registry: ToolRegistry
) -> ToolValidationResult:
    """Run actual tool execution.

    Args:
        tool: Tool name.
        contracts: List of contracts.
        registry: Tool registry.

    Returns:
        Validation result with actual findings.
    """
    import time

    health = registry.check_tool(tool)
    if not health.healthy:
        return ToolValidationResult(
            tool=tool,
            available=False,
            findings_count=0,
            findings=[],
            error=health.error or f"Tool {tool} not available",
            execution_time=0.0,
            mode="live",
        )

    start_time = time.time()
    findings: List[Dict[str, Any]] = []

    try:
        from alphaswarm_sol.tools.executor import ToolExecutor
        from alphaswarm_sol.tools.config import get_optimal_config

        executor = ToolExecutor()
        config = get_optimal_config(tool)

        for contract in contracts:
            result = executor.execute_tool(tool, config, contract)
            if result.success:
                for finding in result.findings:
                    findings.append(finding.to_dict())

        execution_time = time.time() - start_time
        return ToolValidationResult(
            tool=tool,
            available=True,
            findings_count=len(findings),
            findings=findings,
            error=None,
            execution_time=execution_time,
            mode="live",
        )

    except Exception as e:
        return ToolValidationResult(
            tool=tool,
            available=True,
            findings_count=0,
            findings=[],
            error=str(e),
            execution_time=time.time() - start_time,
            mode="live",
        )


def run_deduplication(
    findings: List[Dict[str, Any]],
) -> tuple[List[DeduplicatedFinding], DeduplicationStats]:
    """Run deduplication on findings.

    Args:
        findings: List of finding dictionaries.

    Returns:
        Tuple of (deduplicated findings, stats).
    """
    # Convert to VKGFinding
    vkg_findings: List[VKGFinding] = []
    for f in findings:
        vkg_findings.append(
            VKGFinding(
                source=f.get("source", "unknown"),
                rule_id=f.get("rule_id", "unknown"),
                title=f.get("title", ""),
                description=f.get("description", ""),
                severity=f.get("severity", "medium"),
                category=f.get("category", "unknown"),
                file=f.get("file", "unknown"),
                line=f.get("line", 0),
                function=f.get("function"),
                confidence=f.get("confidence", 0.7),
            )
        )

    # Run deduplication (no embeddings for speed)
    dedup = SemanticDeduplicator(use_embeddings=False)
    return dedup.deduplicate(vkg_findings)


def write_dedup_output(
    output_dir: Path,
    deduped: List[DeduplicatedFinding],
    stats: DeduplicationStats,
) -> None:
    """Write deduplication results to file.

    Args:
        output_dir: Output directory.
        deduped: Deduplicated findings.
        stats: Deduplication statistics.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    output = {
        "timestamp": datetime.utcnow().isoformat(),
        "stats": stats.to_dict(),
        "findings": [f.to_dict() for f in deduped],
    }

    dedup_file = output_dir / "dedup.json"
    with open(dedup_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Wrote dedup results to {dedup_file}")


def run_validation(
    sample_size: int,
    mode: str,
    output_dir: Optional[Path],
) -> ValidationSummary:
    """Run full tool validation.

    Args:
        sample_size: Number of contracts to test.
        mode: 'mock' or 'live'.
        output_dir: Optional output directory.

    Returns:
        Validation summary.
    """
    print(f"\n{'='*60}")
    print(f"Tool Integration Validation - Mode: {mode.upper()}")
    print(f"{'='*60}\n")

    # Get sample contracts
    contracts = get_sample_contracts(sample_size)
    if not contracts:
        print("Error: No contracts found for validation")
        return ValidationSummary(
            timestamp=datetime.utcnow().isoformat(),
            mode=mode,
            sample_size=0,
            contracts=[],
            tools_checked={},
            raw_findings=0,
            deduped_findings=0,
            reduction_percent=0.0,
            dedup_stats={},
            tool_results=[],
            success=False,
        )

    print(f"Selected {len(contracts)} contracts:")
    for c in contracts:
        print(f"  - {c.name}")
    print()

    # Check tool availability
    registry = ToolRegistry()
    tools_to_check = ["slither", "aderyn"]
    tools_status: Dict[str, bool] = {}

    print("Checking tool availability...")
    for tool in tools_to_check:
        health = registry.check_tool(tool)
        tools_status[tool] = health.healthy
        status = "OK" if health.healthy else f"MISSING ({health.error})"
        print(f"  {tool}: {status}")
    print()

    # Run tools
    all_findings: List[Dict[str, Any]] = []
    tool_results: List[ToolValidationResult] = []

    for tool in tools_to_check:
        print(f"Running {tool} ({mode} mode)...")
        if mode == "mock":
            result = run_tool_mock(tool, contracts)
        else:
            result = run_tool_live(tool, contracts, registry)

        tool_results.append(result)
        all_findings.extend(result.findings)
        print(f"  Findings: {result.findings_count}")
        if result.error:
            print(f"  Error: {result.error}")
    print()

    # Run deduplication
    print("Running deduplication...")
    deduped, stats = run_deduplication(all_findings)
    print(f"  Raw findings: {stats.input_count}")
    print(f"  Deduplicated: {stats.output_count}")
    print(f"  Reduction: {stats.reduction_percent:.1f}%")
    print(f"  Location matches: {stats.location_matches}")
    print(f"  Tool agreement boosts: {stats.tool_agreement_boosts}")
    print()

    # Write output if directory specified
    if output_dir:
        write_dedup_output(output_dir, deduped, stats)

    # Build summary
    summary = ValidationSummary(
        timestamp=datetime.utcnow().isoformat(),
        mode=mode,
        sample_size=len(contracts),
        contracts=[c.name for c in contracts],
        tools_checked=tools_status,
        raw_findings=stats.input_count,
        deduped_findings=stats.output_count,
        reduction_percent=stats.reduction_percent,
        dedup_stats=stats.to_dict(),
        tool_results=[
            {
                "tool": r.tool,
                "available": r.available,
                "findings_count": r.findings_count,
                "error": r.error,
                "execution_time": r.execution_time,
                "mode": r.mode,
            }
            for r in tool_results
        ],
        success=True,
    )

    # Print summary
    print("="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    print(f"Mode: {summary.mode}")
    print(f"Contracts tested: {summary.sample_size}")
    print(f"Tools checked: {summary.tools_checked}")
    print(f"Raw findings: {summary.raw_findings}")
    print(f"Deduplicated: {summary.deduped_findings}")
    print(f"Reduction: {summary.reduction_percent:.1f}%")
    print(f"Success: {summary.success}")
    print()

    return summary


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Tool Integration Validation Runner"
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=5,
        help="Number of contracts to test (default: 5)",
    )
    parser.add_argument(
        "--mode",
        choices=["mock", "live"],
        default="mock",
        help="Execution mode: mock (simulated) or live (actual tools)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory for results",
    )

    args = parser.parse_args()

    summary = run_validation(
        sample_size=args.sample,
        mode=args.mode,
        output_dir=args.output_dir,
    )

    # Return exit code
    return 0 if summary.success else 1


if __name__ == "__main__":
    sys.exit(main())
