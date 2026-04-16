"""Confidence Package.

This package provides confidence elevation and PoC narrative generation:
- ConfidenceElevator: Elevates confidence to CONFIRMED when test passes (SDK-14)
- PoCNarrativeGenerator: Generates exploit narratives for attacker claims (SDK-15)

Per PHILOSOPHY.md and 05.2-CONTEXT.md:
- CONFIRMED: Verified by test (passing exploit test)
- No human review needed if test demonstrates the vulnerability
- tests_run field populated for debate protocol

Usage:
    from alphaswarm_sol.agents.confidence import (
        ConfidenceElevator,
        ElevationResult,
        PoCNarrativeGenerator,
        ExploitNarrative,
    )

    # Elevate confidence on test pass
    elevator = ConfidenceElevator()
    result = elevator.elevate_on_test(bead, current_confidence, test_result)
    if result.elevated:
        updated_bead = elevator.apply_elevation(bead, result)

    # Generate exploit narrative
    generator = PoCNarrativeGenerator(runtime)
    narrative = await generator.generate_narrative(bead, test_result)

    # Or without LLM
    narrative = generator.from_bead_directly(bead)
"""

from alphaswarm_sol.agents.confidence.elevation import (
    ConfidenceElevator,
    ElevationResult,
)

from alphaswarm_sol.agents.confidence.poc_narrative import (
    ExploitNarrative,
    PoCNarrativeGenerator,
)

__all__ = [
    # Confidence Elevation
    "ConfidenceElevator",
    "ElevationResult",
    # PoC Narrative
    "PoCNarrativeGenerator",
    "ExploitNarrative",
]
