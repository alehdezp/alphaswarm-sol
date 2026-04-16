"""LLM Investigation Patterns for VKG.

Task 13.11: Per-vulnerability investigation patterns that guide LLM reasoning.

Investigation patterns are designed for vulnerabilities that cannot be detected
through deterministic property checks. They guide the LLM to use tools
(graph queries, LSP, PPR) to intelligently explore code and find vulnerabilities
through reasoning.

Key Distinction:
- Tier A Patterns: Deterministic, same code = same finding
- Investigation Patterns: Reasoning-based, LLM explores and concludes

Architecture:
    Trigger Check -> Execute Steps -> Interpret Results -> Synthesize Verdict

Investigation Actions:
- explore_graph: Query the knowledge graph
- lsp_references: Find all references to a symbol
- lsp_definition: Go to symbol definition
- lsp_call_hierarchy: Trace call hierarchy
- ppr_expand: Expand context via PPR
- read_code: Read specific file/function
- reason: LLM reasoning step
- synthesize: Combine multiple findings
"""

from alphaswarm_sol.investigation.schema import (
    InvestigationAction,
    InvestigationStep,
    InvestigationPattern,
    InvestigationTrigger,
    VerdictCriteria,
    StepResult,
    InvestigationResult,
    InvestigationVerdict,
)
from alphaswarm_sol.investigation.executor import (
    InvestigationExecutor,
    InvestigationContext,
)
from alphaswarm_sol.investigation.loader import (
    InvestigationLoader,
    load_investigation_pattern,
    load_all_investigations,
)
from alphaswarm_sol.investigation.registry import (
    InvestigationRegistry,
    get_investigation_registry,
    get_investigation,
    list_investigations,
)

__all__ = [
    # Schema
    "InvestigationAction",
    "InvestigationStep",
    "InvestigationPattern",
    "InvestigationTrigger",
    "VerdictCriteria",
    "StepResult",
    "InvestigationResult",
    "InvestigationVerdict",
    # Executor
    "InvestigationExecutor",
    "InvestigationContext",
    # Loader
    "InvestigationLoader",
    "load_investigation_pattern",
    "load_all_investigations",
    # Registry
    "InvestigationRegistry",
    "get_investigation_registry",
    "get_investigation",
    "list_investigations",
]
