"""VulnDocs Sources Registry.

Comprehensive catalog of all vulnerability knowledge sources to scrape
and process for building the world's most complete vulnerability database.

Source Categories:
1. Audit Reports & Findings (Solodit, Immunefi, Code4rena, Sherlock)
2. Exploit Databases (Rekt, DeFiLlama, SlowMist)
3. Security Research (Trail of Bits, OpenZeppelin, Consensys)
4. GitHub Repositories (SWC, Smart Contract Best Practices)
5. Educational Content (Medium, YouTube transcripts)
6. Official Documentation (Solidity, EIPs, OpenZeppelin)
7. Checklists & Frameworks (SCSVS, Secureum, Damn Vulnerable DeFi)
"""

from alphaswarm_sol.vulndocs.sources.registry import (
    KnowledgeSource,
    SourceCategory,
    SourcePriority,
    SourceRegistry,
    get_default_sources,
)

__all__ = [
    "KnowledgeSource",
    "SourceCategory",
    "SourcePriority",
    "SourceRegistry",
    "get_default_sources",
]
