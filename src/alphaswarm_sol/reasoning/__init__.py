"""
Phase 3: Iterative + Causal Reasoning

Provides ToG-2 style iterative reasoning for vulnerability detection
and causal reasoning for root cause analysis.
"""

from alphaswarm_sol.reasoning.iterative import (
    ExpansionType,
    ExpandedNode,
    CrossGraphFinding,
    AttackChain,
    ReasoningRound,
    ReasoningResult,
    IterativeReasoningEngine,
)

from alphaswarm_sol.reasoning.causal import (
    CausalRelationType,
    CausalNode,
    CausalEdge,
    CausalGraph,
    RootCause,
    InterventionPoint,
    CausalAnalysis,
    OperationInfo,
    CausalReasoningEngine,
)

from alphaswarm_sol.reasoning.counterfactual import (
    InterventionType,
    Counterfactual,
    CounterfactualSet,
    CounterfactualGenerator,
)

from alphaswarm_sol.reasoning.attack_synthesis import (
    AttackComplexity,
    AttackImpact,
    AttackStep,
    AttackPath,
    AttackPathSet,
    AttackPathSynthesizer,
)

__all__ = [
    # Iterative reasoning
    "ExpansionType",
    "ExpandedNode",
    "CrossGraphFinding",
    "AttackChain",
    "ReasoningRound",
    "ReasoningResult",
    "IterativeReasoningEngine",
    # Causal reasoning
    "CausalRelationType",
    "CausalNode",
    "CausalEdge",
    "CausalGraph",
    "RootCause",
    "InterventionPoint",
    "CausalAnalysis",
    "OperationInfo",
    "CausalReasoningEngine",
    # Counterfactual generation
    "InterventionType",
    "Counterfactual",
    "CounterfactualSet",
    "CounterfactualGenerator",
    # Attack path synthesis
    "AttackComplexity",
    "AttackImpact",
    "AttackStep",
    "AttackPath",
    "AttackPathSet",
    "AttackPathSynthesizer",
]
