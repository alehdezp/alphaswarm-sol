"""Economic prompt contracts for agent reasoning.

This module provides prompt contract builders and validators that enforce
economic context requirements on agent outputs:

- Lens tags (VALUE, CONTROL, INCENTIVE, TRUST, TIMING, CONFIG)
- Causal chain citations (root_cause -> exploit -> loss)
- Counterfactual exploration (at least 2 scenarios per finding)
- Cross-protocol dependency awareness

Per 05.11-CONTEXT.md: Agents must reason like auditors with game-theoretic
awareness, causal reasoning, and provenance-backed citations.

Usage:
    from alphaswarm_sol.agents.prompts import (
        EconomicPromptContract,
        PromptValidator,
        LensTag,
    )

    contract = EconomicPromptContract.for_attacker(
        dossier_summary="...",
        passport_snippet="...",
        attack_ev=PayoffMatrix(...),
    )

    # Validate agent output
    validator = PromptValidator()
    result = validator.validate(agent_output)
    if not result.valid:
        print(result.failures)
"""

from alphaswarm_sol.agents.prompts.economic_contract import (
    LensTag,
    CausalChainElement,
    CounterfactualScenario,
    ValidationResult,
    PromptValidator,
    EconomicPromptContract,
)

__all__ = [
    "LensTag",
    "CausalChainElement",
    "CounterfactualScenario",
    "ValidationResult",
    "PromptValidator",
    "EconomicPromptContract",
]
