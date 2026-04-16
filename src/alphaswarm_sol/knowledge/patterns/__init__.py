"""
Attack Pattern Definitions

Organized by vulnerability category.
"""

from alphaswarm_sol.knowledge.patterns.reentrancy import REENTRANCY_PATTERNS
from alphaswarm_sol.knowledge.patterns.access_control import ACCESS_CONTROL_PATTERNS
from alphaswarm_sol.knowledge.patterns.oracle import ORACLE_PATTERNS
from alphaswarm_sol.knowledge.patterns.economic import ECONOMIC_PATTERNS
from alphaswarm_sol.knowledge.patterns.upgrade import UPGRADE_PATTERNS


# All builtin patterns
ALL_PATTERNS = (
    REENTRANCY_PATTERNS +
    ACCESS_CONTROL_PATTERNS +
    ORACLE_PATTERNS +
    ECONOMIC_PATTERNS +
    UPGRADE_PATTERNS
)


__all__ = [
    "REENTRANCY_PATTERNS",
    "ACCESS_CONTROL_PATTERNS",
    "ORACLE_PATTERNS",
    "ECONOMIC_PATTERNS",
    "UPGRADE_PATTERNS",
    "ALL_PATTERNS",
]
