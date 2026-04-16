"""Multi-Model Agent System for VulnDocs Pipeline.

Task 18.2: Agent base classes for the multi-model knowledge pipeline.

This module provides the agent infrastructure for:
- Haiku workers (fast, cheap processing)
- Opus orchestrators (intelligent decision making)
- Parallel subagent coordination

Architecture:
    Orchestrator (Opus) -> CategoryAgent (Haiku) -> SubcategoryWorker (Haiku)
                       -> MergeOrchestrator (Opus) -> validates and merges
"""

from alphaswarm_sol.vulndocs.agents.base import (
    AgentConfig,
    AgentModel,
    AgentResult,
    BaseAgent,
)
from alphaswarm_sol.vulndocs.agents.category_agent import CategoryAgent
from alphaswarm_sol.vulndocs.agents.subcategory_worker import SubcategoryWorker
from alphaswarm_sol.vulndocs.agents.merge_orchestrator import MergeOrchestrator

__all__ = [
    "AgentConfig",
    "AgentModel",
    "AgentResult",
    "BaseAgent",
    "CategoryAgent",
    "SubcategoryWorker",
    "MergeOrchestrator",
]
