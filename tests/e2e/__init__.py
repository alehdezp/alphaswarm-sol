"""End-to-end tests for the VKG agentic pipeline.

This package contains E2E tests that validate:
- Full pipeline: build -> detect -> beads -> verify -> report
- Determinism: same inputs produce same outputs
- Replayability: execution can be replayed from artifacts
- Resumability: pools can be resumed from any checkpoint

SDK-07: E2E agentic flow tests
SDK-10: Determinism, replayability, resumability validation
"""

from .fixtures import (
    DeterministicRuntime,
    DETERMINISTIC_RESPONSES,
    deterministic_runtime,
    vulnerable_contract_dir,
    sample_bead,
    sample_pool,
    create_minimal_bead,
)

__all__ = [
    "DeterministicRuntime",
    "DETERMINISTIC_RESPONSES",
    "deterministic_runtime",
    "vulnerable_contract_dir",
    "sample_bead",
    "sample_pool",
    "create_minimal_bead",
]
