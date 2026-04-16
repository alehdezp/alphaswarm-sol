"""Shared VKG build cache for tests.

This module builds graphs in-memory from Solidity source using VKGBuilder.
It does NOT load/save graph files, so serialization format (JSON/TOON) is
irrelevant here. Changes to GraphStore save/load won't affect this cache.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from alphaswarm_sol.kg.builder import VKGBuilder

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "tests" / "contracts"
PROJECTS = ROOT / "tests" / "projects"


@lru_cache(maxsize=None)
def load_graph(contract_path: str):
    """Load VKG from contract file with LRU caching.

    Args:
        contract_path: Path to contract, supports two formats:
            - "ContractName.sol": Loads from tests/contracts/
            - "projects/<project>/<file>.sol": Loads from tests/projects/

    Returns:
        Built VKG KnowledgeGraph instance.

    Examples:
        # Legacy: Load from tests/contracts/
        graph = load_graph("NoAccessGate.sol")

        # New: Load from test projects
        graph = load_graph("projects/defi-lending/LendingPool.sol")
    """
    if contract_path.startswith("projects/"):
        # New format: projects/<project>/<file>.sol
        full_path = ROOT / "tests" / contract_path
    else:
        # Legacy format: direct filename in tests/contracts/
        full_path = CONTRACTS / contract_path

    return VKGBuilder(ROOT).build(full_path)
