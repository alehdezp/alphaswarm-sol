"""Context Builder for VulnDocs Knowledge System.

Task 18.21: Dynamic context assembly for LLM consumption.

This module provides intelligent context assembly that:
- Respects token budgets
- Prioritizes relevant knowledge
- Supports progressive loading
- Enables Anthropic prompt caching
- Uses TOON format for token efficiency

Per PHILOSOPHY.md:
- Token-optimized retrieval (~33K tokens max)
- TOON format by default for LLM consumption (30-50% token reduction)
- Two-tier pattern system support (Tier A strict, Tier B LLM-verified)
"""

from alphaswarm_sol.vulndocs.context.builder import (
    ContextBuilder,
    ContextMode,
    ContextPriority,
    ContextSection,
    ContextConfig,
)
from alphaswarm_sol.vulndocs.context.cache import (
    CacheableContext,
    CacheLayer,
    PromptCacheManager,
)
from alphaswarm_sol.vulndocs.context.assembly import (
    ContextAssembler,
    AssemblyStrategy,
    AssembledContext,
)

__all__ = [
    # Builder
    "ContextBuilder",
    "ContextMode",
    "ContextPriority",
    "ContextSection",
    "ContextConfig",
    # Cache
    "CacheableContext",
    "CacheLayer",
    "PromptCacheManager",
    # Assembly
    "ContextAssembler",
    "AssemblyStrategy",
    "AssembledContext",
]
