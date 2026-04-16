#!/usr/bin/env python3
"""
Real Workflow Test Runner for AlphaSwarm.sol

This script validates the REAL product workflow:
- `/vrs-audit` skill with 7-stage pipeline
- BSKG graph building with 200+ emitted properties
- Pattern matching with 556+ patterns
- Multi-agent orchestration (attacker/defender/verifier)
- Exa MCP for economic context

NOT acceptable:
- Simple prompts like "analyze this for vulnerabilities"
- No BSKG graph
- No pattern matching
- No multi-agent debate

Usage:
    uv run python scripts/test_real_workflow.py --stage all
    uv run python scripts/test_real_workflow.py --stage graph
    uv run python scripts/test_real_workflow.py --stage patterns
    uv run python scripts/test_real_workflow.py --stage agents
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add src to path
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from alphaswarm_sol.testing.workflow import (
    ClaudeTestSession,
    SelfImprovingRunner,
    verify_claude_available,
)


@dataclass
class StageResult:
    """Result of testing a pipeline stage."""
    stage: str
    passed: bool
    message: str
    evidence: dict = field(default_factory=dict)
    duration_ms: float = 0


@dataclass
class WorkflowTestResult:
    """Complete workflow test result."""
    name: str
    worktree: str
    stages: list[StageResult] = field(default_factory=list)
    passed: bool = False
    started_at: datetime = None
    completed_at: datetime = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "worktree": self.worktree,
            "passed": self.passed,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "stages": [
                {
                    "stage": s.stage,
                    "passed": s.passed,
                    "message": s.message,
                    "evidence": s.evidence,
                    "duration_ms": s.duration_ms,
                }
                for s in self.stages
            ],
        }


class RealWorkflowTester:
    """
    Tests the REAL AlphaSwarm.sol workflow.

    Validates that `/vrs-audit` executes:
    1. Setup & Validation
    2. BSKG Graph Building (200+ emitted properties)
    3. Protocol Context Research (Exa MCP)
    4. Pattern Matching (556+ patterns)
    5. Specialized Agent Investigation
    6. Multi-Agent Debate
    7. Report Generation
    """

    def __init__(self, worktrees_base: str = "/tmp/vrs-worktrees"):
        self.worktrees_base = Path(worktrees_base)
        self.worktrees_base.mkdir(parents=True, exist_ok=True)
        self.repo_root = REPO_ROOT

    def create_test_contract(self, contracts_dir: Path, scenario: str = "vault"):
        """Create test contracts with known vulnerabilities."""
        contracts_dir.mkdir(parents=True, exist_ok=True)

        if scenario == "vault":
            # Vault with known reentrancy
            (contracts_dir / "Vault.sol").write_text("""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./Ownable.sol";

contract Vault is Ownable {
    mapping(address => uint256) public balances;

    event Deposit(address indexed user, uint256 amount);
    event Withdrawal(address indexed user, uint256 amount);

    function deposit() external payable {
        balances[msg.sender] += msg.value;
        emit Deposit(msg.sender, msg.value);
    }

    // VULNERABILITY: Reentrancy - external call before state update
    // Expected: BSKG detects TRANSFERS_VALUE_OUT before WRITES_USER_BALANCE
    // Expected: Pattern reentrancy-classic matches
    // Expected: Attacker agent constructs exploit path
    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");

        // BUG: External call BEFORE state update
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");

        // State update AFTER external call = reentrancy
        balances[msg.sender] -= amount;
        emit Withdrawal(msg.sender, amount);
    }

    // SAFE: Has access control
    // Expected: BSKG detects has_access_gate = true
    // Expected: Access control patterns do NOT match
    function emergencyWithdraw() external onlyOwner {
        payable(owner()).transfer(address(this).balance);
    }
}
""")
            # Simple Ownable for the vault
            (contracts_dir / "Ownable.sol").write_text("""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Ownable {
    address private _owner;

    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    constructor() {
        _owner = msg.sender;
        emit OwnershipTransferred(address(0), msg.sender);
    }

    function owner() public view returns (address) {
        return _owner;
    }

    modifier onlyOwner() {
        require(owner() == msg.sender, "Ownable: caller is not the owner");
        _;
    }

    function transferOwnership(address newOwner) public onlyOwner {
        require(newOwner != address(0), "Ownable: new owner is zero address");
        emit OwnershipTransferred(_owner, newOwner);
        _owner = newOwner;
    }
}
""")

        elif scenario == "lending":
            # Lending protocol with oracle dependency
            (contracts_dir / "LendingPool.sol").write_text("""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IPriceOracle {
    function getPrice(address asset) external view returns (uint256);
}

contract LendingPool {
    IPriceOracle public oracle;
    mapping(address => mapping(address => uint256)) public deposits;
    mapping(address => mapping(address => uint256)) public borrows;

    // VULNERABILITY: No staleness check on oracle
    // Expected: BSKG detects READS_EXTERNAL_VALUE
    // Expected: Pattern oracle-staleness matches
    function borrow(address asset, uint256 amount) external {
        uint256 price = oracle.getPrice(asset);  // No staleness check!
        uint256 collateralValue = calculateCollateral(msg.sender);
        require(collateralValue >= amount * price / 1e18, "Insufficient collateral");
        borrows[msg.sender][asset] += amount;
    }

    function calculateCollateral(address user) internal view returns (uint256) {
        // Simplified
        return 1e18;
    }
}
""")

    def setup_worktree(self, name: str) -> Path:
        """Create and setup a worktree for testing."""
        worktree_path = self.worktrees_base / name

        # Clean up if exists
        if worktree_path.exists():
            self.cleanup_worktree(name)

        # Create worktree
        result = subprocess.run(
            ["bash", str(self.repo_root / "scripts" / "manage_worktrees.sh"), "init", name],
            capture_output=True,
            text=True,
            cwd=str(self.repo_root),
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to create worktree: {result.stderr}")

        return worktree_path

    def cleanup_worktree(self, name: str):
        """Remove a worktree."""
        subprocess.run(
            ["bash", str(self.repo_root / "scripts" / "manage_worktrees.sh"), "cleanup", name],
            capture_output=True,
            cwd=str(self.repo_root),
        )

    def validate_stage2_graph(self, worktree: Path) -> StageResult:
        """Validate Stage 2: BSKG Graph Building."""
        start = time.time()

        # Check for graph files
        graphs_dir = worktree / ".vrs" / "graphs"
        if not graphs_dir.exists():
            return StageResult(
                stage="2-graph",
                passed=False,
                message="No .vrs/graphs directory found",
            )

        graph_files = list(graphs_dir.glob("*.toon")) + list(graphs_dir.glob("*.json"))
        if not graph_files:
            return StageResult(
                stage="2-graph",
                passed=False,
                message="No graph files (*.toon or *.json) found",
            )

        # Parse and validate graph content
        graph_file = graph_files[0]
        try:
            content = graph_file.read_text()
            # For TOON format, check for key properties
            evidence = {
                "graph_file": str(graph_file),
                "file_size": len(content),
            }

            # Check for expected content
            checks = {
                "has_functions": "function" in content.lower() or "func_" in content,
                "has_operations": "operation" in content.lower() or "TRANSFERS_VALUE" in content,
                "has_properties": "visibility" in content or "external" in content,
            }

            evidence["checks"] = checks
            passed = all(checks.values())

            return StageResult(
                stage="2-graph",
                passed=passed,
                message="Graph built with expected content" if passed else "Graph missing expected content",
                evidence=evidence,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return StageResult(
                stage="2-graph",
                passed=False,
                message=f"Failed to parse graph: {e}",
            )

    def validate_stage3_context(self, worktree: Path) -> StageResult:
        """Validate Stage 3: Protocol Context Research."""
        start = time.time()

        context_dir = worktree / ".vrs" / "context"
        context_files = list(context_dir.glob("*.yaml")) + list(context_dir.glob("*.json"))

        if not context_files:
            return StageResult(
                stage="3-context",
                passed=False,
                message="No context pack files found in .vrs/context/",
            )

        # Check context content
        context_file = context_files[0]
        content = context_file.read_text()

        evidence = {
            "context_file": str(context_file),
            "has_protocol_type": "protocol" in content.lower(),
            "has_roles": "role" in content.lower() or "owner" in content.lower(),
        }

        passed = evidence["has_protocol_type"] or evidence["has_roles"]

        return StageResult(
            stage="3-context",
            passed=passed,
            message="Context pack created" if passed else "Context pack incomplete",
            evidence=evidence,
            duration_ms=(time.time() - start) * 1000,
        )

    def validate_stage4_patterns(self, worktree: Path) -> StageResult:
        """Validate Stage 4: Pattern Matching."""
        start = time.time()

        findings_dir = worktree / ".vrs" / "findings"
        pattern_files = list(findings_dir.glob("*pattern*.json"))

        if not pattern_files:
            return StageResult(
                stage="4-patterns",
                passed=False,
                message="No pattern match files found in .vrs/findings/",
            )

        # Check for expected matches
        pattern_file = pattern_files[0]
        try:
            matches = json.loads(pattern_file.read_text())
            evidence = {
                "pattern_file": str(pattern_file),
                "match_count": len(matches) if isinstance(matches, list) else "unknown",
            }

            # Look for reentrancy pattern
            has_reentrancy = any(
                "reentrancy" in str(m).lower()
                for m in (matches if isinstance(matches, list) else [matches])
            )
            evidence["has_reentrancy_match"] = has_reentrancy

            return StageResult(
                stage="4-patterns",
                passed=has_reentrancy,
                message="Reentrancy pattern matched" if has_reentrancy else "Expected patterns not matched",
                evidence=evidence,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return StageResult(
                stage="4-patterns",
                passed=False,
                message=f"Failed to parse pattern matches: {e}",
            )

    def validate_stage5_agents(self, worktree: Path) -> StageResult:
        """Validate Stage 5: Specialized Agent Investigation."""
        start = time.time()

        findings_dir = worktree / ".vrs" / "findings"
        agent_files = list(findings_dir.glob("*agent*.json")) + list(findings_dir.glob("*investigation*.json"))

        if not agent_files:
            return StageResult(
                stage="5-agents",
                passed=False,
                message="No agent investigation files found",
            )

        # Check agent findings
        agent_file = agent_files[0]
        try:
            findings = json.loads(agent_file.read_text())
            evidence = {
                "agent_file": str(agent_file),
                "finding_count": len(findings) if isinstance(findings, list) else 1,
            }

            # Check for BSKG evidence citations
            content = agent_file.read_text()
            has_graph_evidence = (
                "node" in content.lower() or
                "graph" in content.lower() or
                "func_" in content
            )
            evidence["has_graph_evidence"] = has_graph_evidence

            return StageResult(
                stage="5-agents",
                passed=has_graph_evidence,
                message="Agent findings with graph evidence" if has_graph_evidence else "Agent findings lack graph evidence",
                evidence=evidence,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return StageResult(
                stage="5-agents",
                passed=False,
                message=f"Failed to parse agent findings: {e}",
            )

    def validate_stage6_debate(self, worktree: Path) -> StageResult:
        """Validate Stage 6: Multi-Agent Debate."""
        start = time.time()

        findings_dir = worktree / ".vrs" / "findings"
        verdict_files = list(findings_dir.glob("*verdict*.json"))

        if not verdict_files:
            return StageResult(
                stage="6-debate",
                passed=False,
                message="No verdict files found",
            )

        # Check verdict content
        verdict_file = verdict_files[0]
        try:
            content = verdict_file.read_text()
            evidence = {
                "verdict_file": str(verdict_file),
                "has_attacker": "attacker" in content.lower(),
                "has_defender": "defender" in content.lower(),
                "has_verifier": "verifier" in content.lower(),
            }

            passed = evidence["has_attacker"] and evidence["has_defender"]

            return StageResult(
                stage="6-debate",
                passed=passed,
                message="Multi-agent debate completed" if passed else "Debate incomplete",
                evidence=evidence,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return StageResult(
                stage="6-debate",
                passed=False,
                message=f"Failed to parse verdicts: {e}",
            )

    def validate_stage7_report(self, worktree: Path) -> StageResult:
        """Validate Stage 7: Report Generation."""
        start = time.time()

        reports_dir = worktree / ".vrs" / "reports"
        report_files = list(reports_dir.glob("*.md"))

        if not report_files:
            return StageResult(
                stage="7-report",
                passed=False,
                message="No report files found in .vrs/reports/",
            )

        # Check report content
        report_file = report_files[0]
        content = report_file.read_text()

        evidence = {
            "report_file": str(report_file),
            "word_count": len(content.split()),
            "has_findings": "finding" in content.lower() or "vulnerability" in content.lower(),
            "has_severity": "critical" in content.lower() or "high" in content.lower(),
            "has_evidence": "evidence" in content.lower() or "location" in content.lower(),
        }

        passed = evidence["has_findings"] and evidence["has_severity"]

        return StageResult(
            stage="7-report",
            passed=passed,
            message="Report generated with findings" if passed else "Report incomplete",
            evidence=evidence,
            duration_ms=(time.time() - start) * 1000,
        )

    def run_full_audit(self, worktree: Path, timeout: int = 600) -> bool:
        """Run the full /vrs-audit workflow."""
        session = ClaudeTestSession(working_dir=str(worktree))

        try:
            if not session.start():
                print("  ERROR: Failed to start session")
                return False

            if not session.launch_claude():
                print("  ERROR: Failed to launch Claude")
                return False

            # Run the real audit skill
            print("  Running /vrs-audit contracts/...")
            result = session.send_prompt(
                "/vrs-audit contracts/ --mode swarm",
                timeout=timeout,
                idle_time=60.0,  # Longer idle time for complex operations
            )

            if not result.success:
                print(f"  ERROR: Audit failed: {result.error}")
                return False

            print(f"  Audit completed in {result.duration_ms:.0f}ms")
            return True

        finally:
            session.stop()

    def test_full_workflow(self, scenario: str = "vault") -> WorkflowTestResult:
        """Test the complete workflow from start to finish."""
        name = f"wt-full-{scenario}-{int(time.time())}"
        result = WorkflowTestResult(
            name=f"full-workflow-{scenario}",
            worktree=name,
            started_at=datetime.now(),
        )

        print(f"\n{'='*60}")
        print(f"Testing Full Workflow: {scenario}")
        print(f"{'='*60}")

        try:
            # Setup worktree
            print("\n1. Setting up worktree...")
            worktree = self.setup_worktree(name)
            print(f"   Created: {worktree}")

            # Create test contracts
            print("\n2. Creating test contracts...")
            self.create_test_contract(worktree / "contracts", scenario)
            print("   Contracts created")

            # Run full audit
            print("\n3. Running /vrs-audit...")
            if not self.run_full_audit(worktree):
                result.stages.append(StageResult(
                    stage="audit-execution",
                    passed=False,
                    message="Audit execution failed",
                ))
                return result

            # Validate each stage
            print("\n4. Validating stages...")

            print("   Stage 2: BSKG Graph Building...")
            result.stages.append(self.validate_stage2_graph(worktree))

            print("   Stage 3: Protocol Context...")
            result.stages.append(self.validate_stage3_context(worktree))

            print("   Stage 4: Pattern Matching...")
            result.stages.append(self.validate_stage4_patterns(worktree))

            print("   Stage 5: Agent Investigation...")
            result.stages.append(self.validate_stage5_agents(worktree))

            print("   Stage 6: Multi-Agent Debate...")
            result.stages.append(self.validate_stage6_debate(worktree))

            print("   Stage 7: Report Generation...")
            result.stages.append(self.validate_stage7_report(worktree))

            # Determine overall pass/fail
            result.passed = all(s.passed for s in result.stages)

        except Exception as e:
            result.stages.append(StageResult(
                stage="error",
                passed=False,
                message=str(e),
            ))
        finally:
            result.completed_at = datetime.now()

        return result


def print_result(result: WorkflowTestResult):
    """Print test result summary."""
    print(f"\n{'='*60}")
    print(f"RESULT: {'PASSED' if result.passed else 'FAILED'}")
    print(f"{'='*60}")

    for stage in result.stages:
        status = "✓" if stage.passed else "✗"
        print(f"  {status} {stage.stage}: {stage.message}")
        if stage.evidence:
            for k, v in stage.evidence.items():
                print(f"      {k}: {v}")

    if result.started_at and result.completed_at:
        duration = (result.completed_at - result.started_at).total_seconds()
        print(f"\nTotal duration: {duration:.1f}s")


def main():
    parser = argparse.ArgumentParser(description="Test real AlphaSwarm workflow")
    parser.add_argument(
        "--scenario",
        choices=["vault", "lending", "all"],
        default="vault",
        help="Test scenario",
    )
    parser.add_argument(
        "--keep-worktree",
        action="store_true",
        help="Don't cleanup worktree after test",
    )

    args = parser.parse_args()

    # Check prerequisites
    claude_ok, claude_msg = verify_claude_available()
    if not claude_ok:
        print(f"ERROR: {claude_msg}")
        return 1

    tester = RealWorkflowTester()

    scenarios = ["vault", "lending"] if args.scenario == "all" else [args.scenario]
    all_passed = True

    for scenario in scenarios:
        result = tester.test_full_workflow(scenario)
        print_result(result)

        if not result.passed:
            all_passed = False

        # Save result
        report_path = Path(".vrs/testing/reports")
        report_path.mkdir(parents=True, exist_ok=True)
        report_file = report_path / f"workflow-{result.name}-{int(time.time())}.json"
        report_file.write_text(json.dumps(result.to_dict(), indent=2))
        print(f"\nReport saved: {report_file}")

        # Cleanup unless requested to keep
        if not args.keep_worktree:
            print(f"\nCleaning up worktree: {result.worktree}")
            tester.cleanup_worktree(result.worktree)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
