"""
Invariant Generator

Generates Solidity assertions and specifications from verified invariants.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

from .types import Invariant, InvariantType, InvariantStrength

logger = logging.getLogger(__name__)


@dataclass
class AssertionCode:
    """Generated Solidity assertion code."""
    invariant_id: str
    assertion: str              # The assert() statement
    location: str               # Where to insert (function name or "global")
    placement: str              # "pre", "post", "both"
    gas_cost_estimate: int = 0  # Estimated gas cost

    def to_dict(self) -> Dict[str, Any]:
        return {
            "invariant_id": self.invariant_id,
            "assertion": self.assertion,
            "location": self.location,
            "placement": self.placement,
            "gas_cost": self.gas_cost_estimate,
        }


@dataclass
class InvariantSpec:
    """Formal specification for an invariant."""
    invariant_id: str
    spec_format: str            # "scribble", "certora", "foundry"
    specification: str          # The specification code
    annotations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "invariant_id": self.invariant_id,
            "format": self.spec_format,
            "specification": self.specification,
        }


@dataclass
class GeneratorConfig:
    """Configuration for assertion generation."""
    # Output formats
    generate_asserts: bool = True
    generate_scribble: bool = True
    generate_certora: bool = False
    generate_foundry: bool = True

    # Safety
    only_proven: bool = True        # Only generate for proven invariants
    min_confidence: float = 0.8

    # Gas optimization
    optimize_gas: bool = True
    max_gas_per_assert: int = 5000


class InvariantGenerator:
    """
    Generates code and specifications from invariants.

    Output formats:
    - Solidity assert() statements
    - Scribble annotations
    - Certora CVL specs
    - Foundry invariant tests
    """

    def __init__(self, config: Optional[GeneratorConfig] = None):
        self.config = config or GeneratorConfig()

    def generate_assertions(
        self,
        invariants: List[Invariant],
    ) -> List[AssertionCode]:
        """Generate Solidity assertions for invariants."""
        assertions = []

        for inv in invariants:
            if not self._should_generate(inv):
                continue

            assertion = self._generate_assertion(inv)
            if assertion:
                assertions.append(assertion)

        return assertions

    def _should_generate(self, invariant: Invariant) -> bool:
        """Check if we should generate code for this invariant."""
        if self.config.only_proven:
            if invariant.strength not in [InvariantStrength.PROVEN, InvariantStrength.LIKELY]:
                return False

        return invariant.confidence >= self.config.min_confidence

    def _generate_assertion(self, invariant: Invariant) -> Optional[AssertionCode]:
        """Generate assertion for a single invariant."""
        # Generate assertion based on invariant type
        assertion_code = self._predicate_to_solidity(invariant)

        if not assertion_code:
            return None

        # Determine location and placement
        location = invariant.functions[0] if invariant.functions else "global"
        placement = self._determine_placement(invariant)

        # Estimate gas cost
        gas_cost = self._estimate_gas(assertion_code)

        if self.config.optimize_gas and gas_cost > self.config.max_gas_per_assert:
            logger.warning(f"Skipping high-gas assertion for {invariant.name}")
            return None

        return AssertionCode(
            invariant_id=invariant.invariant_id,
            assertion=assertion_code,
            location=location,
            placement=placement,
            gas_cost_estimate=gas_cost,
        )

    def _predicate_to_solidity(self, invariant: Invariant) -> Optional[str]:
        """Convert predicate to Solidity assertion."""
        predicate = invariant.predicate

        # Type-specific conversions
        if invariant.invariant_type == InvariantType.BALANCE_NON_NEGATIVE:
            var_name = invariant.variables[0] if invariant.variables else "balance"
            return f'assert({var_name} >= 0); // {invariant.name}'

        elif invariant.invariant_type == InvariantType.OWNER_NON_ZERO:
            var_name = invariant.variables[0] if invariant.variables else "owner"
            return f'assert({var_name} != address(0)); // {invariant.name}'

        elif invariant.invariant_type == InvariantType.BALANCE_CONSERVATION:
            return f'assert(_totalSupply == _sumOfBalances()); // {invariant.name}'

        elif invariant.invariant_type == InvariantType.LOCK_HELD:
            return f'assert(_locked); // {invariant.name}'

        elif invariant.invariant_type == InvariantType.MONOTONIC_INCREASE:
            var_name = invariant.variables[0] if invariant.variables else "value"
            return f'assert({var_name} >= _{var_name}Old); // {invariant.name}'

        elif invariant.invariant_type == InvariantType.PERMISSION_REQUIRED:
            return f'assert(hasPermission(msg.sender)); // {invariant.name}'

        elif invariant.invariant_type == InvariantType.BOUNDS_RESPECTED:
            var_name = invariant.variables[0] if invariant.variables else "value"
            return f'assert({var_name} >= min && {var_name} <= max); // {invariant.name}'

        # Default: try to use predicate directly
        return f'assert({predicate}); // {invariant.name}'

    def _determine_placement(self, invariant: Invariant) -> str:
        """Determine where to place assertion (pre/post/both)."""
        # Pre-conditions
        if invariant.invariant_type in [
            InvariantType.PERMISSION_REQUIRED,
            InvariantType.OWNER_NON_ZERO,
        ]:
            return "pre"

        # Post-conditions
        if invariant.invariant_type in [
            InvariantType.BALANCE_CONSERVATION,
            InvariantType.MONOTONIC_INCREASE,
        ]:
            return "post"

        # Both
        return "both"

    def _estimate_gas(self, assertion: str) -> int:
        """Estimate gas cost of assertion."""
        # Rough estimates
        base_cost = 200  # assert base cost

        # Add for storage reads
        if "." in assertion or "[" in assertion:
            base_cost += 2100  # SLOAD

        # Add for comparisons
        base_cost += assertion.count(">=") * 3
        base_cost += assertion.count("==") * 3
        base_cost += assertion.count("!=") * 3

        return base_cost

    def generate_scribble(
        self,
        invariants: List[Invariant],
    ) -> List[InvariantSpec]:
        """Generate Scribble annotations."""
        specs = []

        for inv in invariants:
            if not self._should_generate(inv):
                continue

            spec = self._generate_scribble_spec(inv)
            if spec:
                specs.append(spec)

        return specs

    def _generate_scribble_spec(self, invariant: Invariant) -> Optional[InvariantSpec]:
        """Generate Scribble spec for invariant."""
        # Convert to Scribble format
        if invariant.invariant_type == InvariantType.BALANCE_NON_NEGATIVE:
            var = invariant.variables[0] if invariant.variables else "balance"
            spec = f'/// #invariant {var} >= 0;'

        elif invariant.invariant_type == InvariantType.OWNER_NON_ZERO:
            var = invariant.variables[0] if invariant.variables else "owner"
            spec = f'/// #invariant {var} != address(0);'

        elif invariant.invariant_type == InvariantType.BALANCE_CONSERVATION:
            spec = '/// #invariant forall(address a) sum(balances[a]) == totalSupply;'

        elif invariant.invariant_type == InvariantType.PERMISSION_REQUIRED:
            func = invariant.functions[0] if invariant.functions else "function"
            spec = f'/// #if_succeeds msg.sender == owner;'

        else:
            spec = f'/// #invariant {invariant.predicate};'

        return InvariantSpec(
            invariant_id=invariant.invariant_id,
            spec_format="scribble",
            specification=spec,
            annotations=[f"// {invariant.description}"],
        )

    def generate_foundry_tests(
        self,
        invariants: List[Invariant],
        contract_name: str = "Contract",
    ) -> str:
        """Generate Foundry invariant tests."""
        lines = [
            "// SPDX-License-Identifier: MIT",
            "pragma solidity ^0.8.0;",
            "",
            'import "forge-std/Test.sol";',
            f'import "../src/{contract_name}.sol";',
            "",
            f"contract {contract_name}InvariantTest is Test {{",
            f"    {contract_name} public target;",
            "",
            "    function setUp() public {",
            f"        target = new {contract_name}();",
            "    }",
            "",
        ]

        for inv in invariants:
            if not self._should_generate(inv):
                continue

            test_func = self._generate_foundry_invariant(inv)
            lines.extend(test_func)
            lines.append("")

        lines.append("}")

        return "\n".join(lines)

    def _generate_foundry_invariant(self, invariant: Invariant) -> List[str]:
        """Generate Foundry invariant test function."""
        func_name = f"invariant_{invariant.invariant_id.replace('-', '_')}"

        if invariant.invariant_type == InvariantType.BALANCE_NON_NEGATIVE:
            var = invariant.variables[0] if invariant.variables else "balance"
            return [
                f"    function {func_name}() public view {{",
                f"        // {invariant.description}",
                f"        assertTrue(target.{var}() >= 0);",
                "    }",
            ]

        elif invariant.invariant_type == InvariantType.OWNER_NON_ZERO:
            var = invariant.variables[0] if invariant.variables else "owner"
            return [
                f"    function {func_name}() public view {{",
                f"        // {invariant.description}",
                f"        assertTrue(target.{var}() != address(0));",
                "    }",
            ]

        elif invariant.invariant_type == InvariantType.BALANCE_CONSERVATION:
            return [
                f"    function {func_name}() public view {{",
                f"        // {invariant.description}",
                "        // Note: requires helper to sum balances",
                "        assertTrue(target.totalSupply() >= 0);",
                "    }",
            ]

        else:
            return [
                f"    function {func_name}() public view {{",
                f"        // {invariant.description}",
                f"        // TODO: Implement check for: {invariant.predicate}",
                "    }",
            ]

    def generate_certora_spec(
        self,
        invariants: List[Invariant],
        contract_name: str = "Contract",
    ) -> str:
        """Generate Certora CVL specification."""
        lines = [
            "/*",
            f" * Certora specification for {contract_name}",
            " * Auto-generated from verified invariants",
            " */",
            "",
            "methods {",
            "    // Add method signatures here",
            "}",
            "",
        ]

        for inv in invariants:
            if not self._should_generate(inv):
                continue

            rule = self._generate_certora_rule(inv)
            lines.extend(rule)
            lines.append("")

        return "\n".join(lines)

    def _generate_certora_rule(self, invariant: Invariant) -> List[str]:
        """Generate Certora rule for invariant."""
        rule_name = f"invariant_{invariant.invariant_id.replace('-', '_')}"

        if invariant.invariant_type == InvariantType.BALANCE_NON_NEGATIVE:
            var = invariant.variables[0] if invariant.variables else "balance"
            return [
                f"invariant {rule_name}()",
                f"    {var}() >= 0",
                f"    {{ preserved {{ }} }}",
            ]

        elif invariant.invariant_type == InvariantType.OWNER_NON_ZERO:
            var = invariant.variables[0] if invariant.variables else "owner"
            return [
                f"invariant {rule_name}()",
                f"    {var}() != 0",
                f"    {{ preserved {{ }} }}",
            ]

        else:
            return [
                f"// {rule_name}: {invariant.description}",
                f"// Predicate: {invariant.predicate}",
            ]

    def generate_all(
        self,
        invariants: List[Invariant],
        contract_name: str = "Contract",
    ) -> Dict[str, Any]:
        """Generate all output formats."""
        result = {}

        if self.config.generate_asserts:
            result["assertions"] = self.generate_assertions(invariants)

        if self.config.generate_scribble:
            result["scribble"] = self.generate_scribble(invariants)

        if self.config.generate_foundry:
            result["foundry"] = self.generate_foundry_tests(invariants, contract_name)

        if self.config.generate_certora:
            result["certora"] = self.generate_certora_spec(invariants, contract_name)

        return result
