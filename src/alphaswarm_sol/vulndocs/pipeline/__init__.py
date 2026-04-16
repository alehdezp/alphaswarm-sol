"""Pipeline Infrastructure for VulnDocs Knowledge Mining.

Task 18.2: Multi-phase pipeline for processing vulnerability knowledge.

Pipeline Phases:
1. CRAWL (Haiku x20): Fetch content from sources
2. PROCESS (Haiku x50): Extract and summarize content
3. MERGE (Opus x15): Intelligently combine knowledge
4. LINK (Opus x1): Connect to VKG patterns
5. VALIDATE (Opus x1): Ensure quality and completeness
"""

from alphaswarm_sol.vulndocs.pipeline.orchestrator import (
    PipelineConfig,
    PipelineOrchestrator,
    PipelinePhase,
    PipelineResult,
)

__all__ = [
    "PipelineConfig",
    "PipelineOrchestrator",
    "PipelinePhase",
    "PipelineResult",
]
