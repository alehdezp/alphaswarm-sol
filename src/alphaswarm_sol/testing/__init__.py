"""
AlphaSwarm Testing Module.

Provides test scaffolding for verifying security findings:
- Tier 1 (Template): Always works - provides TODO markers
- Tier 2 (Smart): Attempts import resolution - 30-40% compile rate
- Tier 3 (Complete): Full tests - aspirational, <10% success

IMPORTANT: This module is for TEST GENERATION, not to be confused
with src/alphaswarm_sol/kg/scaffold.py which handles SEMANTIC SCAFFOLDING
for LLM context compression.
"""

# CLI-consumed symbols (from cli/main.py)
from alphaswarm_sol.testing.tiers import (
    TestTier,
    TIER_DEFINITIONS,
    format_tier_summary,
)

from alphaswarm_sol.testing.detection import (
    detect_project_structure,
)

from alphaswarm_sol.testing.generator import (
    write_scaffold_to_file,
)

from alphaswarm_sol.testing.quality import (
    QualityTracker,
    generate_with_fallback,
    batch_generate_with_quality,
)

__all__ = [
    "TestTier",
    "TIER_DEFINITIONS",
    "format_tier_summary",
    "detect_project_structure",
    "write_scaffold_to_file",
    "QualityTracker",
    "generate_with_fallback",
    "batch_generate_with_quality",
]
