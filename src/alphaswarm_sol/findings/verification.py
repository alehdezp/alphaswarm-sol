"""
Verification Checklist Generator (Task 3.15)

Generates actionable verification steps for security findings.

Philosophy: "Every finding includes steps to verify or refute"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class VerificationMethod(str, Enum):
    """Methods for verifying a finding."""

    CODE_REVIEW = "code_review"  # Manual code inspection
    STATIC_ANALYSIS = "static_analysis"  # Other static tools
    DYNAMIC_TEST = "dynamic_test"  # Foundry/Hardhat test
    FORMAL_VERIFICATION = "formal_verification"  # Symbolic execution
    MANUAL_TEST = "manual_test"  # Manual testing on testnet


@dataclass
class VerificationStep:
    """
    A single verification step for a finding.

    Example:
        >>> step = VerificationStep(
        ...     action="Check if nonReentrant modifier is applied",
        ...     method=VerificationMethod.CODE_REVIEW,
        ...     expected="Modifier should be present on withdraw()",
        ...     commands=["grep -n 'nonReentrant' Vault.sol"],
        ... )
    """

    action: str  # What to do
    method: VerificationMethod  # How to do it
    expected: str = ""  # Expected result if safe
    commands: list[str] = field(default_factory=list)  # Ready-to-run commands
    if_true: str = ""  # What it means if expectation met
    if_false: str = ""  # What it means if expectation not met

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "action": self.action,
            "method": self.method.value,
            "expected": self.expected,
            "commands": self.commands,
            "if_true": self.if_true,
            "if_false": self.if_false,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VerificationStep":
        """Create from dictionary."""
        return cls(
            action=data.get("action", ""),
            method=VerificationMethod(data.get("method", "code_review")),
            expected=data.get("expected", ""),
            commands=data.get("commands", []),
            if_true=data.get("if_true", ""),
            if_false=data.get("if_false", ""),
        )

    def format_cli(self) -> str:
        """Format for CLI output."""
        lines = [f"□ {self.action}"]
        if self.expected:
            lines.append(f"  Expected: {self.expected}")
        if self.commands:
            lines.append("  Commands:")
            for cmd in self.commands:
                lines.append(f"    $ {cmd}")
        return "\n".join(lines)


@dataclass
class VerificationChecklist:
    """
    Complete verification checklist for a finding.

    Example:
        >>> checklist = VerificationChecklist(
        ...     finding_id="VKG-ABC123",
        ...     pattern="reentrancy-classic",
        ...     steps=[...],
        ... )
    """

    finding_id: str
    pattern: str
    steps: list[VerificationStep] = field(default_factory=list)
    estimated_time: str = ""  # e.g., "5-10 minutes"
    skill_level: str = ""  # e.g., "intermediate"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "finding_id": self.finding_id,
            "pattern": self.pattern,
            "steps": [s.to_dict() for s in self.steps],
            "estimated_time": self.estimated_time,
            "skill_level": self.skill_level,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VerificationChecklist":
        """Create from dictionary."""
        return cls(
            finding_id=data.get("finding_id", ""),
            pattern=data.get("pattern", ""),
            steps=[VerificationStep.from_dict(s) for s in data.get("steps", [])],
            estimated_time=data.get("estimated_time", ""),
            skill_level=data.get("skill_level", ""),
        )

    def format_cli(self) -> str:
        """Format for CLI output."""
        lines = [
            f"Verification Checklist for {self.finding_id}",
            f"Pattern: {self.pattern}",
            "",
        ]
        if self.estimated_time:
            lines.append(f"Estimated time: {self.estimated_time}")
        if self.skill_level:
            lines.append(f"Skill level: {self.skill_level}")
        lines.append("")
        lines.append("Steps:")
        for i, step in enumerate(self.steps, 1):
            lines.append(f"\n{i}. {step.format_cli()}")
        return "\n".join(lines)

    def to_markdown(self) -> str:
        """Format as Markdown."""
        lines = [
            f"## Verification Checklist: {self.finding_id}",
            f"**Pattern:** `{self.pattern}`",
            "",
        ]
        if self.estimated_time or self.skill_level:
            lines.append("| Metric | Value |")
            lines.append("|--------|-------|")
            if self.estimated_time:
                lines.append(f"| Estimated Time | {self.estimated_time} |")
            if self.skill_level:
                lines.append(f"| Skill Level | {self.skill_level} |")
            lines.append("")

        lines.append("### Steps")
        for i, step in enumerate(self.steps, 1):
            lines.append(f"\n#### {i}. {step.action}")
            lines.append(f"- **Method:** {step.method.value}")
            if step.expected:
                lines.append(f"- **Expected:** {step.expected}")
            if step.commands:
                lines.append("- **Commands:**")
                lines.append("  ```bash")
                for cmd in step.commands:
                    lines.append(f"  {cmd}")
                lines.append("  ```")
            if step.if_true:
                lines.append(f"- **If expected:** {step.if_true}")
            if step.if_false:
                lines.append(f"- **If not expected:** {step.if_false}")

        return "\n".join(lines)


# Pattern-specific checklist generators


def generate_reentrancy_checklist(
    finding_id: str,
    contract: str,
    function: str,
) -> VerificationChecklist:
    """Generate verification checklist for reentrancy findings."""
    return VerificationChecklist(
        finding_id=finding_id,
        pattern="reentrancy",
        estimated_time="10-15 minutes",
        skill_level="intermediate",
        steps=[
            VerificationStep(
                action=f"Check for reentrancy guard on {function}",
                method=VerificationMethod.CODE_REVIEW,
                expected="nonReentrant modifier or mutex pattern",
                commands=[
                    f"grep -n 'nonReentrant\\|ReentrancyGuard' {contract}",
                    f"grep -n 'function {function}' {contract}",
                ],
                if_true="Finding is likely FALSE POSITIVE - guard exists",
                if_false="Finding is CONFIRMED - no guard found",
            ),
            VerificationStep(
                action="Verify state updates happen before external calls",
                method=VerificationMethod.CODE_REVIEW,
                expected="State updates should precede external calls (CEI pattern)",
                commands=[
                    f"vkg query 'operations in {contract}.{function}'",
                ],
                if_true="Code follows CEI - may be FALSE POSITIVE",
                if_false="State update after external call - CONFIRMED vulnerable",
            ),
            VerificationStep(
                action="Write Foundry test for reentrancy attack",
                method=VerificationMethod.DYNAMIC_TEST,
                expected="Attack should fail if contract is secure",
                commands=[
                    "forge test --match-test testReentrancy -vvv",
                ],
                if_true="Test fails - contract is secure",
                if_false="Test succeeds - CRITICAL vulnerability confirmed",
            ),
            VerificationStep(
                action="Check for cross-function reentrancy",
                method=VerificationMethod.CODE_REVIEW,
                expected="No shared state modified by multiple functions without guard",
                commands=[
                    f"vkg query 'functions in {contract.replace('.sol', '')} that write state'",
                ],
                if_true="Single function vulnerable only",
                if_false="Multiple functions share vulnerable state - higher severity",
            ),
        ],
    )


def generate_access_control_checklist(
    finding_id: str,
    contract: str,
    function: str,
) -> VerificationChecklist:
    """Generate verification checklist for access control findings."""
    return VerificationChecklist(
        finding_id=finding_id,
        pattern="access-control",
        estimated_time="5-10 minutes",
        skill_level="beginner",
        steps=[
            VerificationStep(
                action=f"Check for access modifiers on {function}",
                method=VerificationMethod.CODE_REVIEW,
                expected="onlyOwner, onlyRole, or similar modifier",
                commands=[
                    f"grep -n 'function {function}' {contract}",
                    f"grep -n 'onlyOwner\\|onlyRole\\|require.*msg.sender' {contract}",
                ],
                if_true="Access control exists - FALSE POSITIVE",
                if_false="No access control - CONFIRMED",
            ),
            VerificationStep(
                action="Identify what state the function can modify",
                method=VerificationMethod.CODE_REVIEW,
                expected="Only non-sensitive state should be modifiable",
                commands=[
                    f"vkg query 'state variables written by {contract}.{function}'",
                ],
                if_true="Only user-specific state modified - may be intentional",
                if_false="Privileged state (owner, fees, etc.) modified - CRITICAL",
            ),
            VerificationStep(
                action="Check if function is intentionally public",
                method=VerificationMethod.CODE_REVIEW,
                expected="NatSpec or comments explaining public access",
                commands=[
                    f"grep -B5 'function {function}' {contract}",
                ],
                if_true="Intentional design - FALSE POSITIVE",
                if_false="No justification - needs access control",
            ),
        ],
    )


def generate_oracle_checklist(
    finding_id: str,
    contract: str,
    function: str,
) -> VerificationChecklist:
    """Generate verification checklist for oracle manipulation findings."""
    return VerificationChecklist(
        finding_id=finding_id,
        pattern="oracle-manipulation",
        estimated_time="15-20 minutes",
        skill_level="advanced",
        steps=[
            VerificationStep(
                action="Check for price staleness validation",
                method=VerificationMethod.CODE_REVIEW,
                expected="updatedAt check with reasonable threshold",
                commands=[
                    f"grep -n 'staleness\\|updatedAt\\|roundId' {contract}",
                ],
                if_true="Staleness check exists - verify threshold is reasonable",
                if_false="No staleness check - CONFIRMED vulnerable",
            ),
            VerificationStep(
                action="Check for multi-oracle or TWAP usage",
                method=VerificationMethod.CODE_REVIEW,
                expected="Multiple price sources or time-weighted average",
                commands=[
                    f"grep -n 'TWAP\\|UniswapV3\\|multiple.*oracle' {contract}",
                ],
                if_true="Price manipulation resistance present",
                if_false="Single oracle - higher manipulation risk",
            ),
            VerificationStep(
                action="Verify oracle address is from trusted source",
                method=VerificationMethod.CODE_REVIEW,
                expected="Chainlink, Uniswap V3, or other reputable oracle",
                commands=[
                    f"grep -n 'AggregatorV3\\|priceFeed\\|oracle' {contract}",
                ],
                if_true="Using reputable oracle",
                if_false="Unknown oracle source - needs verification",
            ),
            VerificationStep(
                action="Test flash loan attack scenario",
                method=VerificationMethod.DYNAMIC_TEST,
                expected="Attack should not be profitable",
                commands=[
                    "forge test --match-test testFlashLoanManipulation -vvv",
                ],
                if_true="Attack unprofitable - acceptable risk",
                if_false="Attack profitable - CRITICAL vulnerability",
            ),
        ],
    )


def generate_default_checklist(
    finding_id: str,
    pattern: str,
    contract: str,
    function: str,
) -> VerificationChecklist:
    """Generate generic verification checklist."""
    return VerificationChecklist(
        finding_id=finding_id,
        pattern=pattern,
        estimated_time="5-10 minutes",
        skill_level="intermediate",
        steps=[
            VerificationStep(
                action=f"Review {function} in {contract}",
                method=VerificationMethod.CODE_REVIEW,
                expected="Code should not match vulnerability pattern",
                commands=[
                    f"cat -n {contract}",
                    f"vkg query 'properties of {contract}.{function}'",
                ],
                if_true="Pattern mismatch - FALSE POSITIVE",
                if_false="Pattern matches - needs deeper analysis",
            ),
            VerificationStep(
                action="Check for existing mitigations",
                method=VerificationMethod.CODE_REVIEW,
                expected="Guards, checks, or safe patterns present",
                commands=[
                    f"grep -n 'require\\|assert\\|revert' {contract}",
                ],
                if_true="Mitigations present - verify completeness",
                if_false="No mitigations - CONFIRMED vulnerable",
            ),
            VerificationStep(
                action="Write test case to exploit the vulnerability",
                method=VerificationMethod.DYNAMIC_TEST,
                expected="Exploit should fail if code is secure",
                commands=[
                    "forge test -vvv",
                ],
                if_true="Exploit fails - code is secure",
                if_false="Exploit succeeds - vulnerability confirmed",
            ),
        ],
    )


def generate_checklist(
    finding_id: str,
    pattern: str,
    contract: str,
    function: str,
) -> VerificationChecklist:
    """
    Generate appropriate verification checklist based on pattern.

    Args:
        finding_id: The finding ID (e.g., VKG-ABC123)
        pattern: The pattern ID that triggered the finding
        contract: The contract file name
        function: The function name

    Returns:
        VerificationChecklist with pattern-specific steps
    """
    pattern_lower = pattern.lower()

    if "reentrancy" in pattern_lower or "reentrant" in pattern_lower:
        return generate_reentrancy_checklist(finding_id, contract, function)
    elif "access" in pattern_lower or "auth" in pattern_lower:
        return generate_access_control_checklist(finding_id, contract, function)
    elif "oracle" in pattern_lower or "price" in pattern_lower:
        return generate_oracle_checklist(finding_id, contract, function)
    else:
        return generate_default_checklist(finding_id, pattern, contract, function)
