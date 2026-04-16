"""Shared fixtures for E2E tests.

Provides:
- Mock contracts with known vulnerabilities
- DeterministicRuntime for reproducible agent responses
- Pool/bead factory helpers

SDK-10: Ensures same inputs produce same outputs via DeterministicRuntime.
"""

from __future__ import annotations

import pytest
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from alphaswarm_sol.agents.runtime import (
    AgentConfig,
    AgentResponse,
    AgentRole,
    AgentRuntime,
)
from alphaswarm_sol.beads.schema import (
    VulnerabilityBead,
    PatternContext,
    InvestigationGuide,
    TestContext,
)
from alphaswarm_sol.beads.types import (
    BeadStatus,
    CodeSnippet,
    InvestigationStep,
    Severity,
)
from alphaswarm_sol.orchestration.schemas import Pool, PoolStatus, Scope


# =============================================================================
# Deterministic Response Templates
# =============================================================================

DETERMINISTIC_RESPONSES: Dict[AgentRole, str] = {
    AgentRole.ATTACKER: """## Analysis

The vulnerability is exploitable.

### Attack Vector
1. Deploy attacker contract with fallback
2. Call withdraw() to trigger reentrancy
3. Drain contract balance in recursive calls

### Evidence
- External call before state update (line 45)
- No reentrancy guard detected
- Callback function can re-enter withdraw()

**Verdict: VULNERABLE**
**Confidence: 0.9**
""",
    AgentRole.DEFENDER: """## Analysis

Checking for mitigations...

### Guards Checked
- [ ] nonReentrant modifier - NOT FOUND
- [ ] CEI pattern - VIOLATED
- [ ] Pull payment pattern - NOT USED
- [ ] Balance checks - INSUFFICIENT

### Evidence
- State update on line 47 occurs AFTER external call on line 45
- No mutex or lock mechanism present
- Function is publicly callable

**Verdict: VULNERABLE (no mitigations found)**
**Confidence: 0.85**
""",
    AgentRole.VERIFIER: """## Cross-Check

Verifying attacker and defender claims...

### Attacker Claim: Exploitable reentrancy
- Evidence verified: external call before state update
- Attack vector is realistic and practical
- No access control would prevent exploitation

### Defender Claim: No mitigations
- Verified: no reentrancy guard modifier
- Verified: CEI pattern violated (external call before state)
- Verified: function is externally accessible

**Final Verdict: TRUE POSITIVE**
**Confidence: 0.95**
""",
    AgentRole.TEST_BUILDER: """## Test Generation

Generated Foundry test for reentrancy vulnerability:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";
import "../contracts/VulnerableVault.sol";

contract AttackTest is Test {
    VulnerableVault vault;
    Attacker attacker;

    function setUp() public {
        vault = new VulnerableVault();
        attacker = new Attacker(address(vault));
        vm.deal(address(vault), 10 ether);
        vm.deal(address(attacker), 1 ether);
    }

    function testReentrancy() public {
        attacker.attack{value: 1 ether}();
        assertGt(address(attacker).balance, 1 ether);
    }
}
```

**Test Status: GENERATED**
""",
    AgentRole.SUPERVISOR: """## Supervisor Report

Queue Status:
- Attacker queue: 0 pending
- Defender queue: 0 pending
- Verifier queue: 0 pending

No stuck work detected.
All agents operating normally.

**Status: HEALTHY**
""",
    AgentRole.INTEGRATOR: """## Integration Report

Merging verdicts from attacker, defender, and verifier...

### Verdict Synthesis
- Attacker: VULNERABLE (0.9)
- Defender: VULNERABLE (0.85)
- Verifier: TRUE POSITIVE (0.95)

All agents agree on vulnerability status.
No conflict detected.

**Final Verdict: TRUE POSITIVE**
**Confidence: LIKELY (0.9)**
**Evidence: 3 supporting items**
""",
}


# =============================================================================
# Deterministic Runtime
# =============================================================================


class DeterministicRuntime(AgentRuntime):
    """Runtime that produces deterministic responses for testing.

    Ensures SDK-10: same inputs produce same outputs by returning
    pre-defined responses based on agent role.

    Usage:
        runtime = DeterministicRuntime()
        response = await runtime.spawn_agent(config, "analyze this")
        # Response is deterministic based on config.role
    """

    def __init__(
        self,
        responses: Optional[Dict[AgentRole, str]] = None,
        custom_handler: Optional[Callable[[AgentConfig, List[Dict]], str]] = None,
    ):
        """Initialize deterministic runtime.

        Args:
            responses: Optional custom response templates per role
            custom_handler: Optional handler for custom response logic
        """
        self.responses = responses or DETERMINISTIC_RESPONSES
        self.custom_handler = custom_handler
        self.call_log: List[Dict[str, Any]] = []
        self._call_count = 0

    async def execute(
        self, config: AgentConfig, messages: List[Dict]
    ) -> AgentResponse:
        """Execute agent with deterministic response.

        Args:
            config: Agent configuration
            messages: Message history

        Returns:
            Deterministic AgentResponse based on role
        """
        self._call_count += 1
        self.call_log.append({
            "call_id": self._call_count,
            "role": config.role.value,
            "messages": deepcopy(messages),
            "timestamp": datetime.now().isoformat(),
        })

        # Use custom handler if provided
        if self.custom_handler:
            response_text = self.custom_handler(config, messages)
        else:
            response_text = self.responses.get(
                config.role, "Analysis complete. No issues found."
            )

        return AgentResponse(
            content=response_text,
            tool_calls=[],
            input_tokens=len(str(messages)) // 4,  # Approximate
            output_tokens=len(response_text) // 4,
            cache_read_tokens=0,
            cache_write_tokens=0,
            model=f"mock-{config.role.value}",
            latency_ms=100,
        )

    async def spawn_agent(self, config: AgentConfig, task: str) -> AgentResponse:
        """Spawn agent with deterministic response.

        Args:
            config: Agent configuration
            task: Task description

        Returns:
            Deterministic AgentResponse based on role
        """
        messages = [{"role": "user", "content": task}]
        return await self.execute(config, messages)

    def get_model_for_role(self, role: AgentRole) -> str:
        """Get model name for role (mock)."""
        return f"mock-{role.value}"

    def reset(self) -> None:
        """Reset call log and counter."""
        self.call_log.clear()
        self._call_count = 0

    def get_usage(self) -> Dict[str, Any]:
        """Get aggregated usage statistics.

        Returns:
            Dictionary with mock token counts and per-model breakdown
        """
        total_input = 0
        total_output = 0
        by_model: Dict[str, Dict[str, int]] = {}

        for log in self.call_log:
            # Approximate tokens from call log
            input_tokens = len(str(log.get("messages", []))) // 4
            output_tokens = len(self.responses.get(
                AgentRole(log.get("role", "attacker")), ""
            )) // 4

            total_input += input_tokens
            total_output += output_tokens

            model = f"mock-{log.get('role', 'unknown')}"
            if model not in by_model:
                by_model[model] = {"input_tokens": 0, "output_tokens": 0, "count": 0}
            by_model[model]["input_tokens"] += input_tokens
            by_model[model]["output_tokens"] += output_tokens
            by_model[model]["count"] += 1

        return {
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_cache_read_tokens": 0,
            "total_cache_write_tokens": 0,
            "total_cost_usd": 0.0,  # Mock runtime is free
            "request_count": self._call_count,
            "by_model": by_model,
            "cache_savings_ratio": 0.0,
        }


# =============================================================================
# Bead Factory Helper
# =============================================================================


def create_minimal_bead(
    bead_id: str = "VKG-E2E-001",
    vulnerability_class: str = "reentrancy",
    pattern_id: str = "reentrancy-classic",
    severity: Severity = Severity.CRITICAL,
    confidence: float = 0.9,
    status: BeadStatus = BeadStatus.PENDING,
    pool_id: Optional[str] = None,
) -> VulnerabilityBead:
    """Create a minimal bead for testing.

    Args:
        bead_id: Unique bead identifier
        vulnerability_class: Category of vulnerability
        pattern_id: Pattern that matched
        severity: Severity level
        confidence: Initial confidence
        status: Current status
        pool_id: Optional pool association

    Returns:
        VulnerabilityBead with minimal fields populated
    """
    return VulnerabilityBead(
        id=bead_id,
        vulnerability_class=vulnerability_class,
        pattern_id=pattern_id,
        severity=severity,
        confidence=confidence,
        status=status,
        vulnerable_code=CodeSnippet(
            source='''function withdraw() external {
    uint256 amount = balances[msg.sender];
    require(amount > 0, "No balance");

    // VULNERABLE: external call before state update
    (bool success, ) = msg.sender.call{value: amount}("");
    require(success, "Transfer failed");

    // State update AFTER external call
    balances[msg.sender] = 0;
}''',
            file_path="contracts/VulnerableVault.sol",
            start_line=12,
            end_line=22,
            contract_name="VulnerableVault",
            function_name="withdraw",
        ),
        related_code=[],
        full_contract=None,
        inheritance_chain=[],
        pattern_context=PatternContext(
            pattern_name="Classic Reentrancy",
            pattern_description="External call before state update allows reentrant calls",
            why_flagged="External call on line 17 before state update on line 21",
            matched_properties=["state_write_after_external_call", "calls_external"],
            evidence_lines=[17, 21],
        ),
        investigation_guide=InvestigationGuide(
            steps=[
                InvestigationStep(
                    step_number=1,
                    action="Check for reentrancy guard",
                    look_for="nonReentrant modifier or similar lock",
                    evidence_needed="Modifier on function declaration",
                    red_flag="No modifier present",
                    safe_if="nonReentrant modifier present",
                ),
                InvestigationStep(
                    step_number=2,
                    action="Check CEI pattern",
                    look_for="State updates before external calls",
                    evidence_needed="Balance set to 0 before call",
                    red_flag="External call before state update",
                    safe_if="CEI pattern followed",
                ),
            ],
            questions_to_answer=["Is there a reentrancy guard?", "Is CEI pattern followed?"],
            common_false_positives=["nonReentrant modifier", "CEI pattern", "pull payment"],
            key_indicators=["External call before state update", "User-controlled callback"],
            safe_patterns=["CEI pattern", "nonReentrant modifier", "ReentrancyGuard"],
        ),
        test_context=TestContext(
            scaffold_code="contract AttackTest is Test { ... }",
            attack_scenario="1. Deploy attacker contract\n2. Deposit ETH\n3. Call withdraw in fallback",
            setup_requirements=["Attacker contract with receive() or fallback()"],
            expected_outcome="Attacker drains more than deposited",
        ),
        similar_exploits=[],
        fix_recommendations=[
            "Use nonReentrant modifier from OpenZeppelin",
            "Follow Checks-Effects-Interactions pattern",
            "Use pull payment pattern",
        ],
        pool_id=pool_id,
    )


# =============================================================================
# Pytest Fixtures
# =============================================================================


@pytest.fixture
def deterministic_runtime() -> DeterministicRuntime:
    """Create deterministic runtime for testing.

    Returns:
        Fresh DeterministicRuntime instance
    """
    return DeterministicRuntime()


@pytest.fixture
def vulnerable_contract_dir(tmp_path: Path) -> Path:
    """Create directory with vulnerable contract.

    Args:
        tmp_path: Pytest temp path fixture

    Returns:
        Path to contracts directory
    """
    contracts = tmp_path / "contracts"
    contracts.mkdir()

    # Classic reentrancy vulnerability
    vulnerable_sol = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract VulnerableVault {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw() external {
        uint256 amount = balances[msg.sender];
        require(amount > 0, "No balance");

        // VULNERABLE: external call before state update
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");

        // State update AFTER external call - vulnerable to reentrancy
        balances[msg.sender] = 0;
    }

    function getBalance(address account) external view returns (uint256) {
        return balances[account];
    }

    receive() external payable {
        balances[msg.sender] += msg.value;
    }
}
'''
    (contracts / "VulnerableVault.sol").write_text(vulnerable_sol)

    # Safe contract for comparison
    safe_sol = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

contract SafeVault is ReentrancyGuard {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw() external nonReentrant {
        uint256 amount = balances[msg.sender];
        require(amount > 0, "No balance");

        // CEI pattern: state update before external call
        balances[msg.sender] = 0;

        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
    }
}
'''
    (contracts / "SafeVault.sol").write_text(safe_sol)

    return contracts


@pytest.fixture
def sample_bead() -> VulnerabilityBead:
    """Create sample bead for testing.

    Returns:
        VulnerabilityBead with all fields populated
    """
    return create_minimal_bead()


@pytest.fixture
def sample_pool(sample_bead: VulnerabilityBead) -> Pool:
    """Create sample pool with one bead.

    Args:
        sample_bead: Bead to include in pool

    Returns:
        Pool with sample bead
    """
    return Pool(
        id="e2e-test-pool",
        scope=Scope(
            files=["contracts/VulnerableVault.sol"],
            contracts=["VulnerableVault"],
            focus_areas=["reentrancy"],
        ),
        bead_ids=[sample_bead.id],
        status=PoolStatus.INTAKE,
        initiated_by="pytest:e2e",
    )


@pytest.fixture
def multi_bead_pool() -> tuple[Pool, List[VulnerabilityBead]]:
    """Create pool with multiple beads for parallel testing.

    Returns:
        Tuple of (pool, list of beads)
    """
    beads = [
        create_minimal_bead(
            bead_id=f"VKG-E2E-{i:03d}",
            vulnerability_class="reentrancy" if i % 2 == 0 else "access-control",
            confidence=0.7 + (i * 0.05),
        )
        for i in range(5)
    ]

    pool = Pool(
        id="e2e-multi-bead-pool",
        scope=Scope(
            files=["contracts/VulnerableVault.sol"],
            contracts=["VulnerableVault"],
            focus_areas=["reentrancy", "access-control"],
        ),
        bead_ids=[b.id for b in beads],
        status=PoolStatus.INTAKE,
        initiated_by="pytest:e2e:multi",
    )

    return pool, beads


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Classes
    "DeterministicRuntime",
    # Constants
    "DETERMINISTIC_RESPONSES",
    # Factory functions
    "create_minimal_bead",
    # Fixtures
    "deterministic_runtime",
    "vulnerable_contract_dir",
    "sample_bead",
    "sample_pool",
    "multi_bead_pool",
]
