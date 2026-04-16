"""Invariant Synthesis and Exploit Validation.

Per 05.11-CONTEXT.md: Synthesizes require() statements from mined invariants
and validates them against known exploits. Enables proactive security by
generating defensive code that would have prevented historical attacks.

Key features:
- Require() synthesis from invariant patterns
- Exploit database validation
- Discrepancy detection (mined vs declared)
- Integration with InvariantRegistry

Usage:
    from alphaswarm_sol.economics.invariants import (
        InvariantSynthesizer,
        RequireStatement,
        synthesize_require,
    )

    synthesizer = InvariantSynthesizer()

    # Synthesize require() from a candidate
    require = synthesizer.synthesize_require(candidate)
    print(f"{require.code}")
    print(f"Gas overhead: ~{require.gas_overhead}")

    # Validate against known exploits
    result = synthesizer.validate_against_exploits(candidate, exploit_db)
    print(f"Would prevent {result.prevented_count} exploits")

    # Detect discrepancies with declared invariants
    discrepancies = synthesizer.compare_with_declared(mined, declared)
    for d in discrepancies:
        print(f"{d.discrepancy_type}: {d.description}")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from .miner import InvariantCandidate
from .patterns import (
    CallValueUpperBound,
    DifferenceBound,
    InvariantPattern,
    InvariantPatternType,
    MappingLowerBound,
    MappingUpperBound,
    MonotonicProperty,
    RatioBound,
    StateTransitionConstraint,
    SumInvariant,
    VariableRelation,
)

logger = logging.getLogger(__name__)


@dataclass
class RequireStatement:
    """A synthesized Solidity require() statement.

    Per 05.11-CONTEXT.md: Generated defensive code that enforces
    an invariant at runtime.

    Attributes:
        code: The require() statement code
        insertion_point: Where to insert (file, function, position)
        invariant_id: Reference to source invariant
        gas_overhead: Estimated additional gas cost
        revert_message: Custom revert message
        precondition: Whether this is a precondition (before state change)
        postcondition: Whether this is a postcondition (after state change)
    """

    code: str
    insertion_point: Tuple[str, str, str]  # (file, function, position: pre/post)
    invariant_id: str
    gas_overhead: int = 0
    revert_message: str = ""
    precondition: bool = True
    postcondition: bool = False

    def __post_init__(self) -> None:
        """Generate revert message if not provided."""
        if not self.revert_message:
            self.revert_message = f"Invariant {self.invariant_id} violated"

    @property
    def full_code(self) -> str:
        """Get full require() statement with revert message."""
        if "require" in self.code:
            return self.code
        return f'require({self.code}, "{self.revert_message}");'

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "code": self.code,
            "full_code": self.full_code,
            "insertion_point": {
                "file": self.insertion_point[0],
                "function": self.insertion_point[1],
                "position": self.insertion_point[2],
            },
            "invariant_id": self.invariant_id,
            "gas_overhead": self.gas_overhead,
            "revert_message": self.revert_message,
            "precondition": self.precondition,
            "postcondition": self.postcondition,
        }


@dataclass
class ExploitValidationResult:
    """Result of validating invariant against known exploits.

    Per 05.11-CONTEXT.md: Tests whether enforcing an invariant
    would have prevented historical exploits.

    Attributes:
        invariant_id: ID of the invariant validated
        prevented_count: Number of exploits this would prevent
        missed_count: Number of exploits not prevented
        false_alarm_count: Number of false alarms (legitimate tx blocked)
        exploits_prevented: List of exploit IDs prevented
        exploits_missed: List of exploit IDs not prevented
        prevention_rate: Percentage of exploits prevented
    """

    invariant_id: str
    prevented_count: int = 0
    missed_count: int = 0
    false_alarm_count: int = 0
    exploits_prevented: List[str] = field(default_factory=list)
    exploits_missed: List[str] = field(default_factory=list)

    @property
    def prevention_rate(self) -> float:
        """Calculate prevention rate (prevented / total)."""
        total = self.prevented_count + self.missed_count
        if total == 0:
            return 0.0
        return self.prevented_count / total

    @property
    def is_effective(self) -> bool:
        """Whether invariant is effective (>= 50% prevention)."""
        return self.prevention_rate >= 0.5

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "invariant_id": self.invariant_id,
            "prevented_count": self.prevented_count,
            "missed_count": self.missed_count,
            "false_alarm_count": self.false_alarm_count,
            "exploits_prevented": self.exploits_prevented,
            "exploits_missed": self.exploits_missed,
            "prevention_rate": round(self.prevention_rate, 4),
        }


class DiscrepancyType(Enum):
    """Types of discrepancies between mined and declared invariants."""

    MISSING_DECLARED = "missing_declared"  # Mined but not declared (possible safety gap)
    MISSING_MINED = "missing_mined"  # Declared but not mined (untested or dead code)
    CONFLICT = "conflict"  # Contradictory invariants
    CONFIDENCE_GAP = "confidence_gap"  # Declared with high confidence, mined with low


@dataclass
class Discrepancy:
    """A discrepancy between mined and declared invariants.

    Per 05.11-CONTEXT.md: Flags differences for review to catch
    "machine un-auditable" bugs.

    Attributes:
        discrepancy_type: Type of discrepancy
        mined_invariant_id: ID of mined invariant (if any)
        declared_invariant_id: ID of declared invariant (if any)
        description: Human-readable description
        severity: Severity level (low, medium, high, critical)
        resolution_hint: Suggested resolution
    """

    discrepancy_type: DiscrepancyType
    mined_invariant_id: Optional[str] = None
    declared_invariant_id: Optional[str] = None
    description: str = ""
    severity: str = "medium"
    resolution_hint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "discrepancy_type": self.discrepancy_type.value,
            "mined_invariant_id": self.mined_invariant_id,
            "declared_invariant_id": self.declared_invariant_id,
            "description": self.description,
            "severity": self.severity,
            "resolution_hint": self.resolution_hint,
        }


@dataclass
class SynthesisConfig:
    """Configuration for invariant synthesis.

    Attributes:
        min_confidence_for_require: Minimum confidence to generate require()
        include_revert_messages: Whether to include revert messages
        optimize_gas: Whether to optimize for gas
        max_gas_per_require: Maximum acceptable gas overhead
        default_position: Default insertion position (pre/post)
    """

    min_confidence_for_require: float = 0.8
    include_revert_messages: bool = True
    optimize_gas: bool = True
    max_gas_per_require: int = 5000
    default_position: str = "pre"


class InvariantSynthesizer:
    """Synthesizes require() statements from invariants.

    Per 05.11-CONTEXT.md: Converts discovered invariants into defensive
    Solidity code and validates against known exploits.

    Usage:
        synthesizer = InvariantSynthesizer()

        # Synthesize require()
        require = synthesizer.synthesize_require(candidate)

        # Validate against exploits
        result = synthesizer.validate_against_exploits(candidate, exploits)

        # Detect discrepancies
        discrepancies = synthesizer.compare_with_declared(mined, declared)
    """

    def __init__(self, config: Optional[SynthesisConfig] = None) -> None:
        """Initialize the synthesizer.

        Args:
            config: Synthesis configuration
        """
        self.config = config or SynthesisConfig()

    def synthesize_require(
        self,
        candidate: InvariantCandidate,
        contract_file: str = "",
        target_function: str = "",
    ) -> RequireStatement:
        """Synthesize a require() statement from an invariant candidate.

        Args:
            candidate: The invariant candidate
            contract_file: Target contract file
            target_function: Target function (empty = global)

        Returns:
            RequireStatement with synthesized code
        """
        # Get require condition from pattern
        condition = candidate.pattern.to_require_condition()

        # Determine insertion position based on pattern type
        position = self._determine_position(candidate.pattern_type)

        # Calculate gas overhead
        gas_overhead = self._estimate_gas_overhead(condition, candidate.pattern_type)

        # Generate revert message
        revert_msg = ""
        if self.config.include_revert_messages:
            revert_msg = self._generate_revert_message(candidate)

        # Build require statement
        if revert_msg:
            code = f'require({condition}, "{revert_msg}")'
        else:
            code = f"require({condition})"

        return RequireStatement(
            code=code,
            insertion_point=(
                contract_file or candidate.source_contract,
                target_function or candidate.source_function,
                position,
            ),
            invariant_id=candidate.id,
            gas_overhead=gas_overhead,
            revert_message=revert_msg,
            precondition=(position == "pre"),
            postcondition=(position == "post"),
        )

    def _determine_position(self, pattern_type: InvariantPatternType) -> str:
        """Determine require() position based on pattern type."""
        # Preconditions (check before state change)
        precondition_types = {
            InvariantPatternType.CALL_VALUE_UPPER_BOUND,
            InvariantPatternType.STATE_TRANSITION,
        }

        # Postconditions (check after state change)
        postcondition_types = {
            InvariantPatternType.SUM_INVARIANT,
            InvariantPatternType.MONOTONIC_PROPERTY,
            InvariantPatternType.VARIABLE_RELATION,
        }

        if pattern_type in precondition_types:
            return "pre"
        elif pattern_type in postcondition_types:
            return "post"
        else:
            return self.config.default_position

    def _estimate_gas_overhead(
        self,
        condition: str,
        pattern_type: InvariantPatternType,
    ) -> int:
        """Estimate gas overhead of the require() statement."""
        base_gas = 200  # Base require() cost

        # Add for storage reads
        if "[" in condition or "." in condition:
            base_gas += 2100  # SLOAD

        # Add for comparisons
        base_gas += condition.count(">=") * 3
        base_gas += condition.count("<=") * 3
        base_gas += condition.count("==") * 3
        base_gas += condition.count("!=") * 3
        base_gas += condition.count("&&") * 3
        base_gas += condition.count("||") * 3

        # Add for arithmetic
        base_gas += condition.count("*") * 5
        base_gas += condition.count("/") * 5
        base_gas += condition.count("+") * 3
        base_gas += condition.count("-") * 3

        # Special cases by pattern type
        if pattern_type == InvariantPatternType.SUM_INVARIANT:
            base_gas += 5000  # Sum computation is expensive

        return base_gas

    def _generate_revert_message(self, candidate: InvariantCandidate) -> str:
        """Generate a descriptive revert message."""
        # Keep it short for gas efficiency
        if candidate.pattern_type == InvariantPatternType.MAPPING_UPPER_BOUND:
            return "Value exceeds bound"
        elif candidate.pattern_type == InvariantPatternType.MAPPING_LOWER_BOUND:
            return "Value below minimum"
        elif candidate.pattern_type == InvariantPatternType.SUM_INVARIANT:
            return "Conservation violated"
        elif candidate.pattern_type == InvariantPatternType.MONOTONIC_PROPERTY:
            return "Monotonicity violated"
        elif candidate.pattern_type == InvariantPatternType.STATE_TRANSITION:
            return "Invalid state transition"
        elif candidate.pattern_type == InvariantPatternType.CALL_VALUE_UPPER_BOUND:
            return "Value too high"
        elif candidate.pattern_type == InvariantPatternType.VARIABLE_RELATION:
            return "Relation violated"
        elif candidate.pattern_type == InvariantPatternType.RATIO_BOUND:
            return "Ratio out of bounds"
        else:
            return f"Invariant {candidate.id} violated"

    def validate_against_exploits(
        self,
        candidate: InvariantCandidate,
        exploit_db: List[Dict[str, Any]],
    ) -> ExploitValidationResult:
        """Validate an invariant against known exploits.

        Tests whether enforcing this invariant would have prevented
        historical exploits.

        Args:
            candidate: The invariant candidate
            exploit_db: List of exploit records with traces

        Returns:
            ExploitValidationResult with prevention statistics
        """
        result = ExploitValidationResult(invariant_id=candidate.id)

        for exploit in exploit_db:
            exploit_id = exploit.get("id", "unknown")
            exploit_traces = exploit.get("traces", [])

            # Check if any exploit trace violates the invariant
            would_prevent = False
            for trace in exploit_traces:
                if not candidate.pattern.check_trace(trace):
                    would_prevent = True
                    break

            if would_prevent:
                result.prevented_count += 1
                result.exploits_prevented.append(exploit_id)
                candidate.add_exploit_prevention(exploit_id)
            else:
                result.missed_count += 1
                result.exploits_missed.append(exploit_id)

        return result

    def compare_with_declared(
        self,
        mined: List[InvariantCandidate],
        declared: List[Dict[str, Any]],
    ) -> List[Discrepancy]:
        """Compare mined invariants with declared invariants.

        Finds discrepancies that may indicate missing safety checks
        or untested code paths.

        Args:
            mined: List of mined invariant candidates
            declared: List of declared invariant records

        Returns:
            List of Discrepancy objects
        """
        discrepancies: List[Discrepancy] = []

        # Index by expression for comparison
        mined_by_expr = {c.expression: c for c in mined}
        declared_by_expr = {
            d.get("expression", ""): d for d in declared if d.get("expression")
        }

        # Find mined but not declared (potential safety gaps)
        for expr, candidate in mined_by_expr.items():
            if expr not in declared_by_expr:
                discrepancies.append(
                    Discrepancy(
                        discrepancy_type=DiscrepancyType.MISSING_DECLARED,
                        mined_invariant_id=candidate.id,
                        description=f"Invariant discovered but not declared: {candidate.natural_language}",
                        severity="high" if candidate.confidence >= 0.9 else "medium",
                        resolution_hint="Consider documenting this invariant and adding require() statement",
                    )
                )

        # Find declared but not mined (untested or dead code)
        for expr, declared_inv in declared_by_expr.items():
            if expr not in mined_by_expr:
                discrepancies.append(
                    Discrepancy(
                        discrepancy_type=DiscrepancyType.MISSING_MINED,
                        declared_invariant_id=declared_inv.get("invariant_id", ""),
                        description=f"Declared invariant not confirmed by mining: {declared_inv.get('natural_language', expr)}",
                        severity="medium",
                        resolution_hint="Verify invariant is enforced in code and covered by tests",
                    )
                )

        # Find confidence gaps (declared high, mined low)
        for expr, candidate in mined_by_expr.items():
            if expr in declared_by_expr:
                declared_inv = declared_by_expr[expr]
                declared_conf = declared_inv.get("confidence", 1.0)

                if declared_conf >= 0.9 and candidate.confidence < 0.7:
                    discrepancies.append(
                        Discrepancy(
                            discrepancy_type=DiscrepancyType.CONFIDENCE_GAP,
                            mined_invariant_id=candidate.id,
                            declared_invariant_id=declared_inv.get("invariant_id", ""),
                            description=f"Confidence gap: declared={declared_conf}, mined={candidate.confidence}",
                            severity="high",
                            resolution_hint="Investigate why mining confidence is lower than declared",
                        )
                    )

        return discrepancies

    def register_with_registry(
        self,
        candidate: InvariantCandidate,
        registry: Any,  # InvariantRegistry from context module
    ) -> None:
        """Register a mined invariant in the InvariantRegistry.

        Args:
            candidate: The mined invariant candidate
            registry: InvariantRegistry instance
        """
        # Import here to avoid circular dependency
        try:
            from alphaswarm_sol.context.invariant_registry import InvariantCategory

            # Map pattern type to category
            category_map = {
                InvariantPatternType.MAPPING_UPPER_BOUND: InvariantCategory.BALANCE,
                InvariantPatternType.MAPPING_LOWER_BOUND: InvariantCategory.BALANCE,
                InvariantPatternType.SUM_INVARIANT: InvariantCategory.SUPPLY,
                InvariantPatternType.MONOTONIC_PROPERTY: InvariantCategory.SEQUENCE,
                InvariantPatternType.STATE_TRANSITION: InvariantCategory.STATE,
                InvariantPatternType.VARIABLE_RELATION: InvariantCategory.ECONOMIC,
                InvariantPatternType.RATIO_BOUND: InvariantCategory.ECONOMIC,
                InvariantPatternType.CALL_VALUE_UPPER_BOUND: InvariantCategory.ECONOMIC,
            }

            category = category_map.get(candidate.pattern_type, InvariantCategory.BALANCE)

            registry.register_mined(
                invariant_id=candidate.id,
                expression=candidate.expression,
                natural_language=candidate.natural_language,
                mining_method="trace2inv",
                confidence=candidate.confidence,
                category=category,
                scope=f"contract:{candidate.source_contract}",
                validated_against_traces=candidate.supporting_traces,
            )

            # Add exploit prevention info
            record = registry.get(candidate.id)
            if record:
                for exploit_id in candidate.would_prevent_exploits:
                    record.add_exploit_prevention(exploit_id)

            logger.info(f"Registered mined invariant {candidate.id} in registry")

        except ImportError:
            logger.warning("InvariantRegistry not available, skipping registration")

    def batch_synthesize(
        self,
        candidates: List[InvariantCandidate],
        contract_file: str = "",
    ) -> List[RequireStatement]:
        """Synthesize require() statements for multiple candidates.

        Args:
            candidates: List of invariant candidates
            contract_file: Target contract file

        Returns:
            List of RequireStatement objects
        """
        statements = []

        for candidate in candidates:
            if candidate.confidence >= self.config.min_confidence_for_require:
                stmt = self.synthesize_require(candidate, contract_file)

                if self.config.optimize_gas:
                    if stmt.gas_overhead <= self.config.max_gas_per_require:
                        statements.append(stmt)
                else:
                    statements.append(stmt)

        return statements


def synthesize_require(
    candidate: InvariantCandidate,
    config: Optional[SynthesisConfig] = None,
) -> RequireStatement:
    """Convenience function to synthesize a require() statement.

    Args:
        candidate: The invariant candidate
        config: Optional synthesis configuration

    Returns:
        RequireStatement with synthesized code
    """
    synthesizer = InvariantSynthesizer(config)
    return synthesizer.synthesize_require(candidate)


# Export all types
__all__ = [
    "RequireStatement",
    "ExploitValidationResult",
    "DiscrepancyType",
    "Discrepancy",
    "SynthesisConfig",
    "InvariantSynthesizer",
    "synthesize_require",
]
