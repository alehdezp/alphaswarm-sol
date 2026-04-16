"""Task 14.4: Context Factor Integration.

Adjusts calibrated confidence based on contextual factors like
guards, mitigations, and code patterns.

Philosophy:
- Guards (like reentrancy guard) reduce vulnerability likelihood
- Access control patterns provide partial mitigation
- Context factors never fully dismiss or amplify
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


# Default multipliers for common guards/mitigations
GUARD_MULTIPLIERS: Dict[str, float] = {
    # Strong guards (significant confidence reduction)
    "has_reentrancy_guard": 0.2,
    "has_nonreentrant_modifier": 0.2,
    "has_mutex_lock": 0.25,

    # Access control (moderate reduction)
    "has_onlyowner": 0.4,
    "has_access_gate": 0.5,
    "has_role_check": 0.5,
    "has_whitelist": 0.6,

    # Input validation (partial reduction)
    "has_require_checks": 0.7,
    "has_input_validation": 0.7,
    "has_bounds_check": 0.75,

    # CEI pattern (strong for reentrancy)
    "follows_cei_pattern": 0.3,
    "state_update_before_call": 0.35,

    # Trusted targets (moderate)
    "calls_trusted_only": 0.5,
    "no_external_calls": 0.3,

    # Oracle safety
    "has_staleness_check": 0.5,
    "has_price_bounds": 0.6,
    "uses_twap": 0.7,

    # Upgrade safety
    "has_initializer_guard": 0.4,
    "has_upgrade_timelock": 0.5,
}


@dataclass
class ContextConfig:
    """Configuration for context factor adjustments."""
    # Minimum multiplier (never fully dismiss)
    min_multiplier: float = 0.1

    # Maximum multiplier (never amplify)
    max_multiplier: float = 1.0

    # Whether to combine multiple factors multiplicatively
    multiplicative: bool = True

    # Custom multipliers (override defaults)
    custom_multipliers: Dict[str, float] = field(default_factory=dict)


@dataclass
class ContextAdjustment:
    """Record of a context adjustment."""
    factor_name: str
    multiplier: float
    reason: str


@dataclass
class ContextResult:
    """Result of applying context factors."""
    original_confidence: float
    adjusted_confidence: float
    factors_applied: List[ContextAdjustment]
    combined_multiplier: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "original_confidence": round(self.original_confidence, 4),
            "adjusted_confidence": round(self.adjusted_confidence, 4),
            "combined_multiplier": round(self.combined_multiplier, 4),
            "factors_applied": [
                {
                    "factor": a.factor_name,
                    "multiplier": round(a.multiplier, 2),
                    "reason": a.reason,
                }
                for a in self.factors_applied
            ],
        }


class ContextFactors:
    """Apply context-based adjustments to calibrated confidence.

    Example:
        factors = ContextFactors()

        # Apply factors based on detected guards
        result = factors.apply(
            confidence=0.85,
            present_factors={"has_reentrancy_guard", "has_access_gate"}
        )

        print(f"Adjusted: {result.adjusted_confidence}")
        # With reentrancy guard (0.2) and access gate (0.5):
        # Combined multiplier = 0.2 * 0.5 = 0.1
        # Adjusted = 0.85 * 0.1 = 0.085
    """

    def __init__(self, config: Optional[ContextConfig] = None):
        """Initialize with configuration.

        Args:
            config: Optional configuration
        """
        self.config = config or ContextConfig()
        self._multipliers = {**GUARD_MULTIPLIERS, **self.config.custom_multipliers}

    def apply(
        self,
        confidence: float,
        present_factors: Set[str],
        pattern_id: Optional[str] = None,
    ) -> ContextResult:
        """Apply context factors to a confidence value.

        Args:
            confidence: Calibrated confidence value
            present_factors: Set of factor names that are present
            pattern_id: Optional pattern for pattern-specific logic

        Returns:
            ContextResult with adjusted confidence
        """
        adjustments: List[ContextAdjustment] = []
        combined_multiplier = 1.0

        for factor in sorted(present_factors):
            if factor not in self._multipliers:
                continue

            multiplier = self._multipliers[factor]

            # Pattern-specific adjustments
            if pattern_id:
                multiplier = self._adjust_for_pattern(factor, multiplier, pattern_id)

            adjustments.append(ContextAdjustment(
                factor_name=factor,
                multiplier=multiplier,
                reason=self._get_reason(factor),
            ))

            if self.config.multiplicative:
                combined_multiplier *= multiplier
            else:
                # Additive: use minimum
                combined_multiplier = min(combined_multiplier, multiplier)

        # Apply bounds
        combined_multiplier = max(
            self.config.min_multiplier,
            min(self.config.max_multiplier, combined_multiplier)
        )

        adjusted = confidence * combined_multiplier

        return ContextResult(
            original_confidence=confidence,
            adjusted_confidence=adjusted,
            factors_applied=adjustments,
            combined_multiplier=combined_multiplier,
        )

    def _adjust_for_pattern(
        self,
        factor: str,
        base_multiplier: float,
        pattern_id: str,
    ) -> float:
        """Adjust multiplier based on pattern type.

        Some factors are more relevant for certain vulnerabilities.
        """
        # Reentrancy patterns: reentrancy guard is very effective
        if "reentrancy" in pattern_id.lower() or "vm-001" in pattern_id:
            if factor in {"has_reentrancy_guard", "has_nonreentrant_modifier", "follows_cei_pattern"}:
                return base_multiplier * 0.5  # Even stronger reduction

        # Access control patterns: access checks are highly relevant
        if "auth" in pattern_id.lower() or "access" in pattern_id.lower():
            if factor in {"has_onlyowner", "has_access_gate", "has_role_check"}:
                return base_multiplier * 0.5  # Stronger reduction

        # Oracle patterns: staleness check is critical
        if "oracle" in pattern_id.lower():
            if factor in {"has_staleness_check", "has_price_bounds"}:
                return base_multiplier * 0.5  # Stronger reduction

        return base_multiplier

    def _get_reason(self, factor: str) -> str:
        """Get human-readable reason for a factor."""
        reasons = {
            "has_reentrancy_guard": "Reentrancy guard prevents recursive calls",
            "has_nonreentrant_modifier": "NonReentrant modifier blocks reentrancy",
            "has_mutex_lock": "Mutex lock prevents concurrent access",
            "has_onlyowner": "OnlyOwner restricts to privileged caller",
            "has_access_gate": "Access control gate restricts callers",
            "has_role_check": "Role-based access control in place",
            "has_whitelist": "Whitelist restricts to approved addresses",
            "has_require_checks": "Input validation via require statements",
            "has_input_validation": "Explicit input validation present",
            "has_bounds_check": "Bounds checking prevents overflows",
            "follows_cei_pattern": "Follows Checks-Effects-Interactions pattern",
            "state_update_before_call": "State updated before external call",
            "calls_trusted_only": "Only calls trusted contracts",
            "no_external_calls": "No external calls detected",
            "has_staleness_check": "Oracle staleness check present",
            "has_price_bounds": "Price bounds prevent manipulation",
            "uses_twap": "Uses time-weighted average price",
            "has_initializer_guard": "Initializer guard prevents re-init",
            "has_upgrade_timelock": "Upgrade protected by timelock",
        }
        return reasons.get(factor, f"Factor '{factor}' detected")

    def get_multiplier(self, factor: str) -> Optional[float]:
        """Get multiplier for a specific factor."""
        return self._multipliers.get(factor)

    def set_multiplier(self, factor: str, multiplier: float) -> None:
        """Set or override a multiplier."""
        self._multipliers[factor] = multiplier

    def available_factors(self) -> Set[str]:
        """Get all available factor names."""
        return set(self._multipliers.keys())

    def summary(self) -> str:
        """Generate summary of available factors."""
        lines = [
            "Context Factors Summary",
            "=" * 50,
        ]

        # Group by category
        categories = {
            "Guards": ["has_reentrancy_guard", "has_nonreentrant_modifier", "has_mutex_lock"],
            "Access Control": ["has_onlyowner", "has_access_gate", "has_role_check", "has_whitelist"],
            "Validation": ["has_require_checks", "has_input_validation", "has_bounds_check"],
            "Patterns": ["follows_cei_pattern", "state_update_before_call"],
            "Call Safety": ["calls_trusted_only", "no_external_calls"],
            "Oracle": ["has_staleness_check", "has_price_bounds", "uses_twap"],
            "Upgrade": ["has_initializer_guard", "has_upgrade_timelock"],
        }

        for category, factors in categories.items():
            lines.append(f"\n{category}:")
            for factor in factors:
                multiplier = self._multipliers.get(factor, "N/A")
                lines.append(f"  {factor}: {multiplier}")

        return "\n".join(lines)


def apply_context_factors(
    confidence: float,
    present_factors: Set[str],
    pattern_id: Optional[str] = None,
    config: Optional[ContextConfig] = None,
) -> ContextResult:
    """Convenience function to apply context factors.

    Args:
        confidence: Calibrated confidence value
        present_factors: Set of present factor names
        pattern_id: Optional pattern ID
        config: Optional configuration

    Returns:
        ContextResult with adjusted confidence
    """
    factors = ContextFactors(config)
    return factors.apply(confidence, present_factors, pattern_id)
