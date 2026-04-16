"""
Agent Routing Package

GLM-style agent routing with selective context sharing for 95% token reduction.
"""

from .router import (
    AgentType,
    AgentContext,
    ContextSlicer,
    AgentRouter,
    ChainedResult,
)

__all__ = [
    "AgentType",
    "AgentContext",
    "ContextSlicer",
    "AgentRouter",
    "ChainedResult",
]
