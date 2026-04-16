"""Knowledge Graph Package

Includes Domain KG (WHAT CODE SHOULD DO), Adversarial KG (HOW CODE GETS BROKEN),
and Cross-Graph Linker (connecting all three KGs).
"""

from .domain_kg import (
    DomainKnowledgeGraph,
    Specification,
    Invariant,
    DeFiPrimitive,
    SpecType,
    InvariantViolation,
)
from .adversarial_kg import (
    AdversarialKnowledgeGraph,
    AttackPattern,
    ExploitRecord,
    PatternMatch,
    AttackCategory,
    Severity,
)
from .linker import (
    CrossGraphLinker,
    CrossGraphEdge,
    CrossGraphRelation,
    VulnerabilityCandidate,
)
from .patterns import ALL_PATTERNS
from .exploits import ALL_EXPLOITS
from .persistence import (
    save_domain_kg,
    load_domain_kg,
    save_adversarial_kg,
    load_adversarial_kg,
    save_cross_graph_edges,
    load_cross_graph_edges,
    get_file_stats,
    SCHEMA_VERSION,
)


def load_builtin_patterns(adv_kg: AdversarialKnowledgeGraph) -> None:
    """
    Load all builtin attack patterns into adversarial KG.

    Args:
        adv_kg: AdversarialKnowledgeGraph instance to load patterns into
    """
    for pattern in ALL_PATTERNS:
        adv_kg.add_pattern(pattern)


def load_exploit_database(adv_kg: AdversarialKnowledgeGraph) -> None:
    """
    Load historical exploit database into adversarial KG.

    Args:
        adv_kg: AdversarialKnowledgeGraph instance to load exploits into
    """
    for exploit in ALL_EXPLOITS:
        adv_kg.add_exploit(exploit)


__all__ = [
    # Domain KG
    "DomainKnowledgeGraph",
    "Specification",
    "Invariant",
    "DeFiPrimitive",
    "SpecType",
    "InvariantViolation",

    # Adversarial KG
    "AdversarialKnowledgeGraph",
    "AttackPattern",
    "ExploitRecord",
    "PatternMatch",
    "AttackCategory",
    "Severity",
    "load_builtin_patterns",
    "load_exploit_database",

    # Cross-Graph Linker
    "CrossGraphLinker",
    "CrossGraphEdge",
    "CrossGraphRelation",
    "VulnerabilityCandidate",

    # Data
    "ALL_PATTERNS",
    "ALL_EXPLOITS",

    # Persistence
    "save_domain_kg",
    "load_domain_kg",
    "save_adversarial_kg",
    "load_adversarial_kg",
    "save_cross_graph_edges",
    "load_cross_graph_edges",
    "get_file_stats",
    "SCHEMA_VERSION",
]
