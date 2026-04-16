"""Phase 12: Fallback Handling for Micro-Agents.

This module provides graceful fallback behavior when CLI tools
are not available. Instead of failing, VKG falls back to:
- Scaffold generation (test templates)
- Manual verification checklists
- Structured output for human review

Key principle: VKG MUST work without CLI tools.

Usage:
    from alphaswarm_sol.agents.fallback import (
        FallbackHandler,
        FallbackResult,
        get_fallback_for_verification,
        get_fallback_for_test_gen,
    )

    handler = FallbackHandler()
    if not sdk_available():
        result = handler.generate_verification_fallback(bead)
        print(result.scaffold)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

from alphaswarm_sol.beads import (
    VulnerabilityBead,
    VerdictType,
    Severity,
    InvestigationStep,
)
from alphaswarm_sol.agents.sdk import (
    SDKType,
    sdk_available,
    get_installation_guide,
    INSTALLATION_GUIDES,
)


logger = logging.getLogger(__name__)


class FallbackType(str, Enum):
    """Type of fallback generated."""
    VERIFICATION_CHECKLIST = "verification_checklist"
    TEST_SCAFFOLD = "test_scaffold"
    INVESTIGATION_GUIDE = "investigation_guide"
    MANUAL_REVIEW = "manual_review"


@dataclass
class FallbackResult:
    """Result from fallback generation.

    When SDK is unavailable, this provides structured output
    that enables manual verification or test writing.

    Attributes:
        fallback_type: Type of fallback
        scaffold: Generated scaffold code/text
        checklist: Verification checklist items
        investigation_steps: Steps for manual investigation
        file_path: Where scaffold was saved (if any)
        sdk_guidance: How to install SDK
        timestamp: When generated
    """
    fallback_type: FallbackType
    scaffold: str = ""
    checklist: List[str] = field(default_factory=list)
    investigation_steps: List[InvestigationStep] = field(default_factory=list)
    file_path: Optional[str] = None
    sdk_guidance: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "fallback_type": self.fallback_type.value,
            "scaffold": self.scaffold,
            "checklist": self.checklist,
            "investigation_steps": [s.to_dict() for s in self.investigation_steps],
            "file_path": self.file_path,
            "sdk_guidance": self.sdk_guidance,
            "timestamp": self.timestamp.isoformat(),
        }

    def get_console_output(self) -> str:
        """Get formatted output for console display."""
        lines = []

        lines.append("=" * 60)
        lines.append("FALLBACK MODE: CLI Tool Not Available")
        lines.append("=" * 60)
        lines.append("")

        if self.checklist:
            lines.append("## Verification Checklist")
            for i, item in enumerate(self.checklist, 1):
                lines.append(f"  [ ] {i}. {item}")
            lines.append("")

        if self.scaffold:
            lines.append("## Generated Scaffold")
            lines.append("```")
            lines.append(self.scaffold[:500] + "..." if len(self.scaffold) > 500 else self.scaffold)
            lines.append("```")
            lines.append("")

        if self.file_path:
            lines.append(f"Scaffold saved to: {self.file_path}")
            lines.append("")

        if self.sdk_guidance:
            lines.append("## To Enable Micro-Agents")
            lines.append(self.sdk_guidance)

        return "\n".join(lines)


class FallbackHandler:
    """Handler for generating fallback output when SDK unavailable.

    This class generates structured output that enables manual
    verification when micro-agents cannot be spawned.

    Example:
        handler = FallbackHandler()
        result = handler.generate_verification_fallback(bead)

        print(result.get_console_output())
        for item in result.checklist:
            print(f"- {item}")
    """

    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize fallback handler.

        Args:
            output_dir: Directory for scaffold files (default: ./.vrs/scaffolds)
        """
        self.output_dir = output_dir or Path(".vrs/scaffolds")

    def generate_verification_fallback(
        self,
        bead: VulnerabilityBead,
        save_to_file: bool = True,
    ) -> FallbackResult:
        """Generate fallback for verification when SDK unavailable.

        Creates a verification checklist and investigation guide
        that enables manual review of the finding.

        Args:
            bead: VulnerabilityBead to verify
            save_to_file: Whether to save scaffold to file

        Returns:
            FallbackResult with checklist and guide
        """
        # Generate checklist based on vulnerability class
        checklist = self._generate_verification_checklist(bead)

        # Get investigation steps from bead
        investigation_steps = []
        if bead.investigation_guide:
            investigation_steps = bead.investigation_guide.steps

        # Generate scaffold
        scaffold = self._generate_verification_scaffold(bead)

        # Save to file if requested
        file_path = None
        if save_to_file:
            file_path = self._save_scaffold(
                scaffold,
                f"verify_{bead.id}.md",
            )

        return FallbackResult(
            fallback_type=FallbackType.VERIFICATION_CHECKLIST,
            scaffold=scaffold,
            checklist=checklist,
            investigation_steps=investigation_steps,
            file_path=file_path,
            sdk_guidance=self._get_sdk_guidance(),
        )

    def generate_test_fallback(
        self,
        bead: VulnerabilityBead,
        save_to_file: bool = True,
    ) -> FallbackResult:
        """Generate fallback for test generation when SDK unavailable.

        Creates a test scaffold that can be manually completed.

        Args:
            bead: VulnerabilityBead to generate test for
            save_to_file: Whether to save scaffold to file

        Returns:
            FallbackResult with test scaffold
        """
        # Generate test scaffold
        scaffold = self._generate_test_scaffold(bead)

        # Generate checklist for test completion
        checklist = [
            "Complete the setUp() function with necessary state",
            "Implement the attack sequence in the test",
            "Add assertions to verify the exploit",
            "Run: forge test -vvv",
            "Verify test fails if vulnerability is fixed",
        ]

        file_path = None
        if save_to_file:
            file_path = self._save_scaffold(
                scaffold,
                f"test_{bead.id}.t.sol",
            )

        return FallbackResult(
            fallback_type=FallbackType.TEST_SCAFFOLD,
            scaffold=scaffold,
            checklist=checklist,
            file_path=file_path,
            sdk_guidance=self._get_sdk_guidance(),
        )

    def _generate_verification_checklist(
        self,
        bead: VulnerabilityBead,
    ) -> List[str]:
        """Generate verification checklist based on vulnerability class."""
        vuln_class = bead.vulnerability_class.lower()

        # Base checklist items
        checklist = [
            f"Review code at: {bead.vulnerable_code.location if bead.vulnerable_code else 'N/A'}",
            "Confirm the flagged pattern exists in the code",
        ]

        # Class-specific items
        if "reentrancy" in vuln_class:
            checklist.extend([
                "Check for external calls (call, send, transfer)",
                "Verify state is updated BEFORE external call (CEI pattern)",
                "Look for reentrancy guard (nonReentrant modifier)",
                "Check if callback functions could re-enter",
            ])
        elif "access" in vuln_class:
            checklist.extend([
                "Identify the access control mechanism used",
                "Verify modifier is applied to all sensitive functions",
                "Check for admin key centralization risks",
                "Look for tx.origin usage (vulnerable to phishing)",
            ])
        elif "oracle" in vuln_class:
            checklist.extend([
                "Identify the oracle source (Chainlink, Uniswap TWAP, etc.)",
                "Check for staleness validation (timestamp checks)",
                "Verify multiple oracle sources or fallbacks",
                "Look for price manipulation vectors",
            ])
        elif "dos" in vuln_class:
            checklist.extend([
                "Check for unbounded loops",
                "Verify external calls don't block execution",
                "Look for gas griefing opportunities",
                "Check for strict equality on balances",
            ])
        else:
            # Generic items
            checklist.extend([
                "Trace all execution paths through the function",
                "Identify any state modifications",
                "Check for proper input validation",
                "Verify return values are handled",
            ])

        checklist.extend([
            "Consider if the issue is exploitable in practice",
            "Document your verdict with evidence",
        ])

        return checklist

    def _generate_verification_scaffold(
        self,
        bead: VulnerabilityBead,
    ) -> str:
        """Generate verification scaffold markdown."""
        location = bead.vulnerable_code.location if bead.vulnerable_code else "Unknown"
        code = bead.vulnerable_code.source if bead.vulnerable_code else "// Code not available"

        return f"""# Verification Report: {bead.id}

## Finding Summary
- **Pattern**: {bead.pattern_id}
- **Severity**: {bead.severity.value}
- **Vulnerability Class**: {bead.vulnerability_class}
- **Location**: {location}

## Code Under Review
```solidity
{code}
```

## Pattern Context
{bead.pattern_context.why_flagged if bead.pattern_context else "N/A"}

### Properties Matched
{chr(10).join(f"- {p}" for p in (bead.pattern_context.matched_properties if bead.pattern_context else []))}

## Investigation Steps
{self._format_investigation_steps(bead)}

## Verdict
- [ ] TRUE_POSITIVE - This is a real vulnerability
- [ ] FALSE_POSITIVE - This is not exploitable
- [ ] NEEDS_MORE_INFO - Cannot determine without additional context

### Evidence
(Document your findings here)

### Reasoning
(Explain your verdict)

---
Generated by VKG Fallback Handler
CLI tool required for automated verification.
"""

    def _generate_test_scaffold(
        self,
        bead: VulnerabilityBead,
    ) -> str:
        """Generate Foundry test scaffold."""
        contract_name = "TargetContract"  # Would be extracted from bead
        function_name = "vulnerableFunction"

        if bead.vulnerable_code:
            contract_name = bead.vulnerable_code.contract_name or contract_name
            function_name = bead.vulnerable_code.function_name or function_name

        return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";

/**
 * @title Exploit Test for {bead.id}
 * @notice Tests for {bead.vulnerability_class} vulnerability
 * @dev Pattern: {bead.pattern_id}
 *
 * Finding Details:
 * - Severity: {bead.severity.value}
 * - Location: {bead.vulnerable_code.location if bead.vulnerable_code else "N/A"}
 *
 * This test should:
 * 1. PASS if the vulnerability exists (exploit succeeds)
 * 2. FAIL after the vulnerability is fixed
 */
contract Exploit_{bead.id.replace("-", "_")} is Test {{

    // Target contract
    // TODO: Import the actual contract
    // {contract_name} target;

    // Attacker address
    address attacker = makeAddr("attacker");
    address victim = makeAddr("victim");

    function setUp() public {{
        // TODO: Deploy the vulnerable contract
        // target = new {contract_name}();

        // TODO: Set up initial state
        // - Fund accounts
        // - Set up any required state
        // vm.deal(attacker, 10 ether);
        // vm.deal(address(target), 100 ether);
    }}

    function test_exploit_{bead.vulnerability_class.replace("-", "_")}() public {{
        // Record state before attack
        // uint256 attackerBalanceBefore = address(attacker).balance;
        // uint256 targetBalanceBefore = address(target).balance;

        vm.startPrank(attacker);

        // TODO: Implement the exploit
        // Step 1: ...
        // Step 2: ...
        // target.{function_name}(...);

        vm.stopPrank();

        // TODO: Assert the exploit succeeded
        // assertGt(address(attacker).balance, attackerBalanceBefore);
        // or
        // assertLt(address(target).balance, targetBalanceBefore);
    }}

    // Helper function for reentrancy attacks
    // receive() external payable {{
    //     // TODO: Implement callback if needed
    // }}
}}

/*
Investigation Notes:
{self._format_investigation_notes(bead)}

Evidence from Pattern Match:
{chr(10).join(f"- Line {line}" for line in (bead.pattern_context.evidence_lines if bead.pattern_context else []))}
*/
"""

    def _format_investigation_steps(self, bead: VulnerabilityBead) -> str:
        """Format investigation steps as markdown."""
        if not bead.investigation_guide or not bead.investigation_guide.steps:
            return "No investigation steps defined."

        lines = []
        for step in bead.investigation_guide.steps:
            lines.append(f"### Step {step.step_number}: {step.action}")
            lines.append(f"**Look for**: {step.look_for}")
            lines.append(f"**Evidence needed**: {step.evidence_needed}")
            if step.red_flag:
                lines.append(f"**Red flag**: {step.red_flag}")
            if step.safe_if:
                lines.append(f"**Safe if**: {step.safe_if}")
            lines.append("")

        return "\n".join(lines)

    def _format_investigation_notes(self, bead: VulnerabilityBead) -> str:
        """Format investigation notes for test scaffold."""
        notes = []

        if bead.investigation_guide:
            for step in bead.investigation_guide.steps[:3]:  # First 3 steps
                notes.append(f"- {step.action}: {step.look_for}")

        if bead.similar_exploits:
            for exploit in bead.similar_exploits[:2]:  # First 2 exploits
                notes.append(f"- Similar to: {exploit.name} ({exploit.loss})")

        return "\n".join(notes) if notes else "No investigation notes available."

    def _save_scaffold(self, content: str, filename: str) -> str:
        """Save scaffold to file.

        Args:
            content: Scaffold content
            filename: Output filename

        Returns:
            Absolute path to saved file
        """
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            file_path = self.output_dir / filename
            file_path.write_text(content)
            return str(file_path.absolute())
        except Exception as e:
            logger.error(f"Failed to save scaffold: {e}")
            return ""

    def _get_sdk_guidance(self) -> str:
        """Get SDK installation guidance."""
        available = []
        unavailable = []

        for sdk_type in [SDKType.CLAUDE, SDKType.CODEX, SDKType.OPENCODE]:
            if sdk_available(sdk_type):
                available.append(sdk_type.value)
            else:
                unavailable.append(sdk_type)

        if available:
            return f"Available SDKs: {', '.join(available)}"

        # Return installation guide for first unavailable
        if unavailable:
            return get_installation_guide(unavailable[0])

        return "No SDK installation guidance available."


# Convenience functions

def get_fallback_for_verification(
    bead: VulnerabilityBead,
    output_dir: Optional[Path] = None,
) -> FallbackResult:
    """Get fallback for verification when SDK unavailable.

    Args:
        bead: VulnerabilityBead to verify
        output_dir: Optional output directory

    Returns:
        FallbackResult with verification checklist
    """
    handler = FallbackHandler(output_dir)
    return handler.generate_verification_fallback(bead)


def get_fallback_for_test_gen(
    bead: VulnerabilityBead,
    output_dir: Optional[Path] = None,
) -> FallbackResult:
    """Get fallback for test generation when SDK unavailable.

    Args:
        bead: VulnerabilityBead to generate test for
        output_dir: Optional output directory

    Returns:
        FallbackResult with test scaffold
    """
    handler = FallbackHandler(output_dir)
    return handler.generate_test_fallback(bead)


def should_use_fallback() -> bool:
    """Check if fallback should be used (no SDK available).

    Returns:
        True if no SDK is available
    """
    return not sdk_available()


def get_fallback_message() -> str:
    """Get user-friendly fallback message.

    Returns:
        Message explaining fallback mode
    """
    return """
╔══════════════════════════════════════════════════════════════╗
║               CLI TOOL NOT AVAILABLE                          ║
╠══════════════════════════════════════════════════════════════╣
║                                                               ║
║  VKG is running in FALLBACK MODE.                            ║
║                                                               ║
║  Instead of automated micro-agent verification, you will     ║
║  receive:                                                     ║
║    • Verification checklists                                 ║
║    • Test scaffolds                                          ║
║    • Investigation guides                                    ║
║                                                               ║
║  For automated verification, install one of:                 ║
║    • Claude Code: npm install -g @anthropic-ai/claude-code   ║
║    • Codex CLI: npm install -g @openai/codex-cli             ║
║    • OpenCode CLI: go install github.com/opencode-ai/opencode║
║                                                               ║
╚══════════════════════════════════════════════════════════════╝
"""
