"""
Specification Definitions

ERC standards and DeFi primitives with invariants.
"""

from alphaswarm_sol.knowledge.specs.erc_standards import ALL_ERC_STANDARDS
from alphaswarm_sol.knowledge.specs.defi_primitives import ALL_DEFI_PRIMITIVES


def load_all_specs():
    """
    Load all ERC standards and DeFi primitives.

    Returns:
        Tuple of (specifications, primitives)
    """
    return (ALL_ERC_STANDARDS, ALL_DEFI_PRIMITIVES)


__all__ = [
    "ALL_ERC_STANDARDS",
    "ALL_DEFI_PRIMITIVES",
    "load_all_specs",
]
