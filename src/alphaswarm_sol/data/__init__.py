"""Phase 10: Data module for exploit database and known vulnerabilities."""

from alphaswarm_sol.data.exploits import (
    KnownExploit,
    ExploitCategory,
    EXPLOIT_DATABASE,
    get_exploits_by_category,
    get_exploits_by_signature,
    get_exploit_by_id,
)

__all__ = [
    "KnownExploit",
    "ExploitCategory",
    "EXPLOIT_DATABASE",
    "get_exploits_by_category",
    "get_exploits_by_signature",
    "get_exploit_by_id",
]
