"""
Test Scaffold Tier System Design (Task 4.1)

Defines three distinct tiers of test scaffold generation with realistic
success criteria and clear boundaries.

Philosophy:
- Tier 1 MUST NEVER FAIL - always produces useful output
- Tier 2 attempts compilation - realistic 30-40% success rate
- Tier 3 is aspirational - <10% success rate expected

CRITICAL: Do not confuse with src/alphaswarm_sol/kg/scaffold.py which handles
SEMANTIC SCAFFOLDING for LLM context. This is for TEST GENERATION.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class TestTier(Enum):
    """
    Test generation quality tiers with realistic expectations.

    Each tier has different guarantees:
    - TIER_1: Always produces output, may not compile
    - TIER_2: Attempts compilation, ~30-40% success
    - TIER_3: Full tests, aspirational (<10% success)
    """

    TIER_1_TEMPLATE = 1   # Always works, needs manual completion
    TIER_2_SMART = 2      # Attempts compilation, 30-40% success (REALISTIC)
    TIER_3_COMPLETE = 3   # Full test (aspirational, <10% success)


@dataclass
class TierDefinition:
    """
    Definition of what each tier provides and its success expectations.

    This is used for:
    - Documentation of tier capabilities
    - Setting expectations for users
    - Quality tracking and metrics

    Attributes:
        tier: The tier enum value
        description: Human-readable description
        success_rate_target: Target success rate (0.0 to 1.0)
        success_rate_minimum: Minimum acceptable success rate
        provides: List of capabilities this tier provides
        does_not_provide: List of things NOT guaranteed
    """

    tier: TestTier
    description: str
    success_rate_target: float  # Realistic target (0.0 to 1.0)
    success_rate_minimum: float  # Minimum acceptable
    provides: List[str] = field(default_factory=list)
    does_not_provide: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate rates are in valid range."""
        if not 0.0 <= self.success_rate_target <= 1.0:
            raise ValueError(f"success_rate_target must be 0.0-1.0, got {self.success_rate_target}")
        if not 0.0 <= self.success_rate_minimum <= 1.0:
            raise ValueError(f"success_rate_minimum must be 0.0-1.0, got {self.success_rate_minimum}")
        if self.success_rate_minimum > self.success_rate_target:
            raise ValueError("success_rate_minimum cannot exceed success_rate_target")


# =============================================================================
# TIER DEFINITIONS
# =============================================================================
# CRITICAL: These targets are REALISTIC based on the original TRACKER's
# honest assessment: "20% compile AND test right thing, 30% compile but
# test wrong thing, 50% won't compile at all"
# =============================================================================

TIER_DEFINITIONS = {
    TestTier.TIER_1_TEMPLATE: TierDefinition(
        tier=TestTier.TIER_1_TEMPLATE,
        description="Template with TODO comments - always generates",
        success_rate_target=1.0,  # 100% - always produces output
        success_rate_minimum=1.0,  # MUST always succeed
        provides=[
            "Test file structure with valid Solidity syntax",
            "Vulnerability description in comments",
            "Attack vector explanation for the category",
            "TODO markers for manual completion",
            "Suggested assertion patterns",
            "Helper contract templates (for reentrancy, etc.)",
        ],
        does_not_provide=[
            "Correct import paths (must be added manually)",
            "Compilable code (imports likely broken)",
            "Working test logic (requires implementation)",
            "Project-specific configuration",
        ]
    ),
    TestTier.TIER_2_SMART: TierDefinition(
        tier=TestTier.TIER_2_SMART,
        description="Smart template with resolved imports - 30-40% compile rate",
        success_rate_target=0.40,  # 40% - REALISTIC, not the original 60%
        success_rate_minimum=0.25,  # 25% minimum acceptable
        provides=[
            "Everything from Tier 1",
            "Attempted import resolution using project config",
            "Pragma version matching from source files",
            "Basic setUp() structure with deployment",
            "forge-std import for Foundry projects",
            "Compile confidence estimate",
        ],
        does_not_provide=[
            "Guaranteed compilation (only ~30-40% will compile)",
            "Correct test logic (attack implementation)",
            "Full attack implementation",
            "Handling of complex dependencies",
        ]
    ),
    TestTier.TIER_3_COMPLETE: TierDefinition(
        tier=TestTier.TIER_3_COMPLETE,
        description="Complete test - aspirational, <10% success",
        success_rate_target=0.10,  # 10% - highly aspirational
        success_rate_minimum=0.05,  # 5% - minimum to be useful
        provides=[
            "Everything from Tier 2",
            "Attack implementation attempt",
            "Assertion logic for vulnerability",
            "State setup for exploit scenario",
        ],
        does_not_provide=[
            "Guaranteed correctness (only ~10% will work)",
            "Coverage of complex scenarios",
            "Economic attack modeling",
            "Cross-function exploit chains",
        ]
    ),
}


def get_tier_definition(tier: TestTier) -> TierDefinition:
    """
    Get the definition for a specific tier.

    Args:
        tier: The tier to get definition for

    Returns:
        TierDefinition with capabilities and expectations

    Raises:
        KeyError: If tier not found in definitions
    """
    return TIER_DEFINITIONS[tier]


def validate_tier_success_rate(tier: TestTier, actual_rate: float) -> bool:
    """
    Check if an actual success rate meets the tier's minimum requirement.

    Args:
        tier: The tier to check against
        actual_rate: The observed success rate (0.0 to 1.0)

    Returns:
        True if actual_rate meets minimum requirement
    """
    definition = TIER_DEFINITIONS[tier]
    return actual_rate >= definition.success_rate_minimum


def format_tier_summary(tier: TestTier) -> str:
    """
    Format a human-readable summary of a tier.

    Args:
        tier: The tier to summarize

    Returns:
        Multi-line string with tier details
    """
    defn = TIER_DEFINITIONS[tier]
    lines = [
        f"=== {tier.name} ===",
        f"Description: {defn.description}",
        f"Target Success Rate: {defn.success_rate_target * 100:.0f}%",
        f"Minimum Acceptable: {defn.success_rate_minimum * 100:.0f}%",
        "",
        "Provides:",
    ]
    for item in defn.provides:
        lines.append(f"  + {item}")
    lines.append("")
    lines.append("Does NOT provide:")
    for item in defn.does_not_provide:
        lines.append(f"  - {item}")
    return "\n".join(lines)
