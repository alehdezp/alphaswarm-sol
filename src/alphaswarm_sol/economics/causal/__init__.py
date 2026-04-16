"""Causal exploitation graph package for root cause reasoning.

Per 05.11-07-PLAN.md: Causal Exploitation Graph (CEG) system that traces
causation chains from root cause to financial loss, enables counterfactual
queries, and estimates loss amplification.

Key features:
- CausalExploitationGraph: Build and traverse causal exploitation graphs
- CausalNode/CausalEdge: Graph elements with probabilities and evidence
- CounterfactualEngine: "What if" reasoning for mitigation analysis
- LossEstimator: Loss estimation with amplification factors

CEG Node Types:
- RootCause: The fundamental vulnerability (missing_access_control, oracle_manipulation)
- ExploitStep: Intermediate exploitation steps (unauthorized_call, state_manipulation)
- FinancialLoss: The financial outcome (treasury_drain, token_theft)
- Amplifier: Factors that increase loss (flash_loan, leverage)

CEG Edge Types:
- CAUSES: Direct causation (root -> exploit step)
- ENABLES: Prerequisite (state A enables exploit B)
- AMPLIFIES: Multiplies loss (flash loan amplifies attack)
- BLOCKS: Mitigation breaks chain (guard prevents step)

Usage:
    from alphaswarm_sol.economics.causal import (
        CausalExploitationGraph,
        CausalNode,
        CausalNodeType,
        CEGEdge,
        build_ceg,
        CounterfactualEngine,
        CounterfactualQuery,
        CounterfactualResult,
        LossEstimator,
        LossEstimate,
    )

    # Build a CEG from vulnerability analysis
    ceg = build_ceg(vulnerability_id, linker)

    # Trace all paths from root cause to loss
    paths = ceg.get_all_paths(root_cause_id, loss_id)

    # Run counterfactual query
    engine = CounterfactualEngine()
    result = engine.query(ceg, CounterfactualQuery(
        condition="reentrancy_guard_exists",
        target_edge="external_call_step"
    ))

    print(f"Chain blocked: {result.chain_blocked}")
    print(f"Loss reduction: {result.loss_reduction:.1%}")
"""

from .exploitation_graph import (
    CausalExploitationGraph,
    CausalNode,
    CausalNodeType,
    CEGEdge,
    CausalPath,
    build_ceg,
)

from .counterfactual_engine import (
    CounterfactualEngine,
    CounterfactualQuery,
    CounterfactualResult,
)

from .loss_estimation import (
    LossEstimator,
    LossEstimate,
    ProtocolState,
)

__all__ = [
    # Exploitation graph
    "CausalExploitationGraph",
    "CausalNode",
    "CausalNodeType",
    "CEGEdge",
    "CausalPath",
    "build_ceg",
    # Counterfactual engine
    "CounterfactualEngine",
    "CounterfactualQuery",
    "CounterfactualResult",
    # Loss estimation
    "LossEstimator",
    "LossEstimate",
    "ProtocolState",
]
