"""Grimoires & Skills System for VKG.

Phase 13: Per-vulnerability testing playbooks that encode expert knowledge.

A Grimoire is a complete testing playbook powered by:
- VulnerabilityBead context (code, patterns, exploits)
- Pre-configured tools (Foundry, fuzzers, forks)
- Expert verification procedures per vulnerability class

Architecture:
    Finding -> Bead Creation -> Grimoire Selection -> Procedure Execution -> Verdict

Grimoires are invocable as skills:
    /test-reentrancy --finding <id>
    /test-access --finding <id>
    /test-oracle --finding <id>

Per PHILOSOPHY.md:
- Skills & Grimoires is a core pillar
- Each grimoire encodes expert verification knowledge
- Procedures are category-specific, not generic
"""

from alphaswarm_sol.grimoires.schema import (
    GrimoireStep,
    GrimoireStepAction,
    GrimoireProcedure,
    Grimoire,
    GrimoireVerdict,
    VerdictConfidence,
    GrimoireResult,
)
from alphaswarm_sol.grimoires.registry import (
    GrimoireRegistry,
    get_grimoire,
    list_grimoires,
    get_grimoire_for_category,
)
from alphaswarm_sol.grimoires.executor import (
    GrimoireExecutor,
    ExecutionContext,
    StepResult,
)
from alphaswarm_sol.grimoires.skill import (
    Skill,
    SkillRegistry,
    SkillResult,
    invoke_skill,
)
from alphaswarm_sol.grimoires.cost import (
    CostTracker,
    CostReport,
    StepCost,
    TokenUsage,
    ModelPricing,
    CostCategory,
    BudgetExceededError,
    create_cost_tracker,
)

__all__ = [
    # Schema
    "GrimoireStep",
    "GrimoireStepAction",
    "GrimoireProcedure",
    "Grimoire",
    "GrimoireVerdict",
    "VerdictConfidence",
    "GrimoireResult",
    # Registry
    "GrimoireRegistry",
    "get_grimoire",
    "list_grimoires",
    "get_grimoire_for_category",
    # Executor
    "GrimoireExecutor",
    "ExecutionContext",
    "StepResult",
    # Skills
    "Skill",
    "SkillRegistry",
    "SkillResult",
    "invoke_skill",
    # Cost Tracking
    "CostTracker",
    "CostReport",
    "StepCost",
    "TokenUsage",
    "ModelPricing",
    "CostCategory",
    "BudgetExceededError",
    "create_cost_tracker",
]
