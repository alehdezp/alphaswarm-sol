"""
Invariant Synthesizer

High-level interface that combines mining, verification, and generation
into a complete invariant synthesis pipeline.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

from .types import (
    Invariant,
    InvariantType,
    InvariantStrength,
    InvariantViolation,
    VerificationResult,
)
from .miner import InvariantMiner, MiningConfig, MiningResult
from .verifier import InvariantVerifier, VerifierConfig
from .generator import InvariantGenerator, GeneratorConfig, AssertionCode, InvariantSpec

logger = logging.getLogger(__name__)


@dataclass
class SynthesisConfig:
    """Configuration for full synthesis pipeline."""
    # Mining config
    mining_config: Optional[MiningConfig] = None

    # Verification config
    verifier_config: Optional[VerifierConfig] = None

    # Generation config
    generator_config: Optional[GeneratorConfig] = None

    # Pipeline control
    verify_candidates: bool = True
    generate_assertions: bool = True
    generate_specs: bool = True
    generate_tests: bool = True

    # Quality thresholds
    min_confidence_for_output: float = 0.7
    require_verification: bool = False


@dataclass
class SynthesisResult:
    """Result of the full synthesis pipeline."""
    contract: str

    # Mining results
    candidates_mined: int = 0
    mining_time_ms: int = 0

    # Verification results
    verified_count: int = 0
    violated_count: int = 0
    verification_time_ms: int = 0

    # Final invariants
    invariants: List[Invariant] = field(default_factory=list)
    violations: List[InvariantViolation] = field(default_factory=list)

    # Generated outputs
    assertions: List[AssertionCode] = field(default_factory=list)
    scribble_specs: List[InvariantSpec] = field(default_factory=list)
    foundry_tests: Optional[str] = None
    certora_spec: Optional[str] = None

    def get_proven_invariants(self) -> List[Invariant]:
        """Get formally proven invariants."""
        return [i for i in self.invariants if i.strength == InvariantStrength.PROVEN]

    def get_likely_invariants(self) -> List[Invariant]:
        """Get likely (high confidence) invariants."""
        return [i for i in self.invariants if i.strength == InvariantStrength.LIKELY]

    def get_by_type(self, inv_type: InvariantType) -> List[Invariant]:
        """Get invariants by type."""
        return [i for i in self.invariants if i.invariant_type == inv_type]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract": self.contract,
            "candidates_mined": self.candidates_mined,
            "verified": self.verified_count,
            "violated": self.violated_count,
            "total_invariants": len(self.invariants),
            "proven": len(self.get_proven_invariants()),
            "likely": len(self.get_likely_invariants()),
            "assertions_generated": len(self.assertions),
            "violations_found": len(self.violations),
            "mining_time_ms": self.mining_time_ms,
            "verification_time_ms": self.verification_time_ms,
        }

    def summary(self) -> str:
        """Get human-readable summary."""
        lines = [
            f"=== Invariant Synthesis: {self.contract} ===",
            f"Candidates mined: {self.candidates_mined}",
            f"Verified: {self.verified_count}",
            f"Violated: {self.violated_count}",
            "",
            f"Final invariants: {len(self.invariants)}",
            f"  - Proven: {len(self.get_proven_invariants())}",
            f"  - Likely: {len(self.get_likely_invariants())}",
            "",
            f"Assertions generated: {len(self.assertions)}",
            f"Scribble specs: {len(self.scribble_specs)}",
            f"Foundry tests: {'Yes' if self.foundry_tests else 'No'}",
            "",
            f"Violations found: {len(self.violations)}",
        ]

        if self.violations:
            lines.append("  Violations:")
            for vio in self.violations[:5]:
                lines.append(f"    - {vio.invariant.name}: {vio.description[:50]}")

        return "\n".join(lines)


class InvariantSynthesizer:
    """
    Complete invariant synthesis pipeline.

    Pipeline:
    1. Mine candidate invariants from code patterns
    2. Verify candidates using formal methods
    3. Generate assertions and specifications
    """

    def __init__(self, config: Optional[SynthesisConfig] = None):
        self.config = config or SynthesisConfig()

        # Initialize components
        self.miner = InvariantMiner(self.config.mining_config)
        self.verifier = InvariantVerifier(self.config.verifier_config)
        self.generator = InvariantGenerator(self.config.generator_config)

    def synthesize(
        self,
        contract_name: str,
        code: Optional[str] = None,
        state_vars: Optional[List[Dict[str, Any]]] = None,
        functions: Optional[List[Dict[str, Any]]] = None,
        kg_data: Optional[Dict[str, Any]] = None,
    ) -> SynthesisResult:
        """
        Run the full synthesis pipeline.

        Args:
            contract_name: Name of the contract
            code: Solidity source code
            state_vars: State variable information
            functions: Function information
            kg_data: Knowledge graph data (alternative input)
        """
        logger.info(f"Starting invariant synthesis for {contract_name}")

        result = SynthesisResult(contract=contract_name)

        # Step 1: Mine candidate invariants
        mining_start = datetime.now()

        if kg_data:
            mining_result = self.miner.mine_from_kg(contract_name, kg_data)
        else:
            mining_result = self.miner.mine(
                contract_name,
                code or "",
                state_vars,
                functions,
            )

        result.candidates_mined = len(mining_result.invariants)
        result.mining_time_ms = mining_result.mining_time_ms

        logger.info(f"Mined {result.candidates_mined} candidate invariants")

        # Step 2: Verify candidates
        if self.config.verify_candidates:
            verification_start = datetime.now()

            for inv in mining_result.invariants:
                ver_result = self.verifier.verify(
                    inv,
                    code=code,
                    state_vars=state_vars,
                    functions=functions,
                )

                if ver_result.verified:
                    result.verified_count += 1
                    result.invariants.append(inv)
                else:
                    result.violated_count += 1
                    if ver_result.violation:
                        result.violations.append(ver_result.violation)

                    # Still include likely ones if not requiring verification
                    if not self.config.require_verification and inv.confidence >= self.config.min_confidence_for_output:
                        result.invariants.append(inv)

            result.verification_time_ms = int(
                (datetime.now() - verification_start).total_seconds() * 1000
            )

            logger.info(f"Verified {result.verified_count}, violated {result.violated_count}")
        else:
            # Skip verification, use all candidates
            result.invariants = mining_result.invariants

        # Step 3: Generate outputs
        valid_invariants = [
            i for i in result.invariants
            if i.confidence >= self.config.min_confidence_for_output
        ]

        if self.config.generate_assertions:
            result.assertions = self.generator.generate_assertions(valid_invariants)
            logger.info(f"Generated {len(result.assertions)} assertions")

        if self.config.generate_specs:
            result.scribble_specs = self.generator.generate_scribble(valid_invariants)

        if self.config.generate_tests:
            result.foundry_tests = self.generator.generate_foundry_tests(
                valid_invariants, contract_name
            )

        logger.info(f"Synthesis complete for {contract_name}")

        return result

    def synthesize_from_kg(
        self,
        contract_name: str,
        kg_data: Dict[str, Any],
    ) -> SynthesisResult:
        """
        Synthesize invariants from knowledge graph data.

        This is the primary integration point with True VKG.
        """
        # Extract info from KG
        functions = []
        state_vars = []

        for node in kg_data.get("nodes", []):
            if node.get("type") == "Function":
                functions.append({
                    "name": node.get("name"),
                    "visibility": node.get("visibility"),
                    "modifiers": node.get("modifiers", []),
                    "properties": node.get("properties", {}),
                })
            elif node.get("type") == "StateVariable":
                state_vars.append({
                    "name": node.get("name"),
                    "type": node.get("var_type"),
                    "visibility": node.get("visibility"),
                })

        return self.synthesize(
            contract_name=contract_name,
            state_vars=state_vars,
            functions=functions,
            kg_data={"functions": functions, "state_variables": state_vars},
        )

    def quick_mine(
        self,
        contract_name: str,
        code: str,
    ) -> List[Invariant]:
        """Quick mining without verification."""
        result = self.miner.mine(contract_name, code)
        return result.invariants

    def verify_invariant(
        self,
        invariant: Invariant,
        **kwargs,
    ) -> VerificationResult:
        """Verify a single invariant."""
        return self.verifier.verify(invariant, **kwargs)

    def generate_for_invariant(
        self,
        invariant: Invariant,
    ) -> Dict[str, Any]:
        """Generate outputs for a single invariant."""
        return self.generator.generate_all([invariant])

    def get_statistics(self) -> Dict[str, Any]:
        """Get synthesizer statistics."""
        return {
            "miner": self.miner.get_statistics(),
            "verifier": self.verifier.get_statistics(),
        }

    def add_custom_template(self, template) -> None:
        """Add a custom mining template."""
        self.miner.add_template(template)

    def clear_cache(self):
        """Clear verification cache."""
        self.verifier.clear_cache()
