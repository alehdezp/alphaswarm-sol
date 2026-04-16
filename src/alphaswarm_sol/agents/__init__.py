"""True VKG Agent System.

Multi-agent verification for security auditing with SDK abstraction,
hooks system, propulsion, and infrastructure agents.

## Quick Start

```python
from alphaswarm_sol.agents import (
    # Runtime - SDK abstraction
    AgentRuntime, AgentConfig, AgentRole, AgentResponse,
    AnthropicRuntime, OpenAIAgentsRuntime,

    # Hooks - work distribution
    AgentInbox, PrioritizedBeadQueue,

    # Propulsion - autonomous execution
    PropulsionEngine, AgentCoordinator,

    # Infrastructure agents
    SupervisorAgent, IntegratorAgent,

    # Role agents
    TestBuilderAgent,

    # Confidence
    ConfidenceElevator,
)

# Example: Run orchestration
runtime = AnthropicRuntime()
coordinator = AgentCoordinator(runtime)
coordinator.setup_for_pool(pool, beads)
report = await coordinator.run()
```

## Module Organization

- `runtime/` - SDK abstraction (Anthropic, OpenAI)
- `hooks/` - Work distribution (inboxes, queues)
- `propulsion/` - Autonomous execution
- `infrastructure/` - Supervisor, Integrator
- `roles/` - TestBuilder, Foundry integration
- `confidence/` - Elevation, PoC narratives

## SDK Requirements Coverage

| Req | Description | Implementation |
|-----|-------------|----------------|
| SDK-01 | Multi-SDK abstraction | AgentRuntime ABC |
| SDK-02 | Hook system | AgentInbox, PrioritizedBeadQueue |
| SDK-03 | Supervisor agent | SupervisorAgent |
| SDK-04 | Integrator agent | IntegratorAgent |
| SDK-05 | Role-to-model mapping | ROLE_MODEL_MAP |
| SDK-06 | Propulsion engine | PropulsionEngine |
| SDK-07 | E2E tests | tests/e2e/ |
| SDK-08 | CLI/SDK parity | CoordinatorReport |
| SDK-09 | Context-fresh execution | PropulsionConfig |
| SDK-10 | Determinism | DeterministicRuntime |
| SDK-11 | Test Builder role | TestBuilderAgent |
| SDK-12 | Foundry scaffolds | GeneratedTest |
| SDK-13 | Foundry execution | FoundryRunner |
| SDK-14 | Confidence elevation | ConfidenceElevator |
| SDK-15 | PoC narratives | PoCNarrativeGenerator |
"""

# =============================================================================
# Phase 5.2: Multi-Agent SDK Integration
# =============================================================================

# Runtime abstraction (SDK-01, SDK-05)
from alphaswarm_sol.agents.runtime import (
    AgentRuntime,
    AgentConfig,
    AgentRole,
    AgentResponse,
    RuntimeConfig,
    ROLE_MODEL_MAP,
    UsageTracker,
    calculate_cost,
    create_runtime,
)
from alphaswarm_sol.agents.runtime.anthropic import AnthropicRuntime
from alphaswarm_sol.agents.runtime.openai_agents import OpenAIAgentsRuntime

# Catalog (Phase 7.1.2)
from alphaswarm_sol.agents.catalog import (
    SubagentEntry,
    OutputContract,
    EvidenceRequirements,
    AgentLocation,
    list_subagents,
    get_subagent,
    filter_by_role,
    filter_by_model_tier,
    filter_shipped_only,
    filter_dev_only,
    validate_catalog,
    get_catalog_stats,
)

# Hooks system (SDK-02)
from alphaswarm_sol.agents.hooks import (
    AgentInbox,
    InboxConfig,
    WorkClaim,
    PrioritizedBeadQueue,
    BeadPriority,
    PrioritizedBead,
    HookStorage,
)

# Propulsion (SDK-06, SDK-09)
from alphaswarm_sol.agents.propulsion import (
    PropulsionEngine,
    PropulsionConfig,
    WorkResult,
    AgentCoordinator,
    CoordinatorConfig,
    CoordinatorStatus,
    CoordinatorReport,
)

# Infrastructure agents (SDK-03, SDK-04)
from alphaswarm_sol.agents.infrastructure import (
    SupervisorAgent,
    SupervisorConfig,
    SupervisorReport,
    StuckWorkReport,
    IntegratorAgent,
    IntegratorConfig,
    MergedVerdict,
    AgentVerdict,
    SUPERVISOR_SYSTEM_PROMPT,
    INTEGRATOR_SYSTEM_PROMPT,
)

# Role agents (SDK-11, SDK-12, SDK-13)
from alphaswarm_sol.agents.roles import (
    TestBuilderAgent,
    TestGenerationConfig,
    GeneratedTest,
    FoundryRunner,
    ForgeTestResult,
    ForgeBuildResult,
)
from alphaswarm_sol.agents.roles.prompts import (
    TEST_BUILDER_SYSTEM_PROMPT,
    ATTACKER_SYSTEM_PROMPT,
    DEFENDER_SYSTEM_PROMPT,
    VERIFIER_SYSTEM_PROMPT,
)

# Confidence (SDK-14, SDK-15)
from alphaswarm_sol.agents.confidence import (
    ConfidenceElevator,
    ElevationResult,
    PoCNarrativeGenerator,
    ExploitNarrative,
)

# =============================================================================
# Legacy: Phase 9, VKG 3.5, VKG 4.0 Agents (preserved for compatibility)
# =============================================================================

from alphaswarm_sol.agents.base import (
    VerificationAgent,
    AgentResult,
    AgentEvidence,
    EvidenceType,
)
from alphaswarm_sol.agents.explorer import ExplorerAgent
from alphaswarm_sol.agents.pattern import PatternAgent
from alphaswarm_sol.agents.constraint import ConstraintAgent
from alphaswarm_sol.agents.risk import RiskAgent
from alphaswarm_sol.agents.consensus import AgentConsensus, ConsensusResult, Verdict
from alphaswarm_sol.agents.attacker import (
    AttackerAgent,
    AttackerResult,
    AttackConstruction,
    AttackCategory,
    AttackFeasibility,
    EconomicImpact,
    ExploitabilityFactors,
)
from alphaswarm_sol.agents.defender import (
    DefenderAgent,
    DefenderResult,
    DefenseArgument,
    DefenseType,
    RebuttalStrategy,
    GuardInfo,
    Rebuttal,
)
from alphaswarm_sol.agents.arbiter import (
    AdversarialArbiter,
    ArbitrationResult,
    VerdictType,
    ConfidenceLevel,
    WinningSide,
    Evidence,
    EvidenceChain,
)
from alphaswarm_sol.agents.enhanced_consensus import (
    EnhancedAgentConsensus,
    EnhancedConsensusResult,
    ConsensusMode,
)
from alphaswarm_sol.agents.verifier import (
    LLMDFAVerifier,
    VerificationResult,
    VerificationStatus,
    ConstraintType,
    PathConstraint,
    ConstraintSet,
    WitnessValues,
    UnsatCore,
    verify_path_feasibility,
)

# Phase 12: Agent SDK Micro-Agents
from alphaswarm_sol.agents.sdk import (
    SDKManager,
    SDKType,
    SDKStatus,
    SDKInfo,
    SDKConfig,
    sdk_available,
    get_available_sdks,
    get_sdk_manager,
    get_installation_guide,
    get_fallback_message,
)
from alphaswarm_sol.agents.microagent import (
    MicroAgent,
    MicroAgentType,
    MicroAgentStatus,
    MicroAgentConfig,
    MicroAgentCost,
    MicroAgentResult,
    VerificationMicroAgent,
    TestGenMicroAgent,
    create_verifier,
    create_test_generator,
)
from alphaswarm_sol.agents.swarm import (
    SwarmManager,
    SwarmStatus,
    SwarmConfig,
    SwarmProgress,
    SwarmResult,
    swarm_verify,
    swarm_generate_tests,
    create_swarm_manager,
)
from alphaswarm_sol.agents.fallback import (
    FallbackHandler,
    FallbackType,
    FallbackResult,
    get_fallback_for_verification,
    get_fallback_for_test_gen,
    should_use_fallback,
)
from alphaswarm_sol.agents.cost import (
    CostTracker,
    CostReport,
    UsageRecord,
    BudgetExceededError,
    estimate_cost,
    get_global_tracker,
    set_global_budget,
    reset_global_tracker,
)

__all__ = [
    # =========================================================================
    # Phase 5.2: Multi-Agent SDK Integration (New)
    # =========================================================================
    # Runtime (SDK-01, SDK-05)
    "AgentRuntime",
    "AgentConfig",
    "AgentRole",
    "AgentResponse",
    "RuntimeConfig",
    "ROLE_MODEL_MAP",
    "UsageTracker",
    "calculate_cost",
    "create_runtime",
    "AnthropicRuntime",
    "OpenAIAgentsRuntime",
    # Catalog (Phase 7.1.2)
    "SubagentEntry",
    "OutputContract",
    "EvidenceRequirements",
    "AgentLocation",
    "list_subagents",
    "get_subagent",
    "filter_by_role",
    "filter_by_model_tier",
    "filter_shipped_only",
    "filter_dev_only",
    "validate_catalog",
    "get_catalog_stats",
    # Hooks (SDK-02)
    "AgentInbox",
    "InboxConfig",
    "WorkClaim",
    "PrioritizedBeadQueue",
    "BeadPriority",
    "PrioritizedBead",
    "HookStorage",
    # Propulsion (SDK-06, SDK-09)
    "PropulsionEngine",
    "PropulsionConfig",
    "WorkResult",
    "AgentCoordinator",
    "CoordinatorConfig",
    "CoordinatorStatus",
    "CoordinatorReport",
    # Infrastructure (SDK-03, SDK-04)
    "SupervisorAgent",
    "SupervisorConfig",
    "SupervisorReport",
    "StuckWorkReport",
    "IntegratorAgent",
    "IntegratorConfig",
    "MergedVerdict",
    "AgentVerdict",
    "SUPERVISOR_SYSTEM_PROMPT",
    "INTEGRATOR_SYSTEM_PROMPT",
    # Roles (SDK-11, SDK-12, SDK-13)
    "TestBuilderAgent",
    "TestGenerationConfig",
    "GeneratedTest",
    "FoundryRunner",
    "ForgeTestResult",
    "ForgeBuildResult",
    "TEST_BUILDER_SYSTEM_PROMPT",
    "ATTACKER_SYSTEM_PROMPT",
    "DEFENDER_SYSTEM_PROMPT",
    "VERIFIER_SYSTEM_PROMPT",
    # Confidence (SDK-14, SDK-15)
    "ConfidenceElevator",
    "ElevationResult",
    "PoCNarrativeGenerator",
    "ExploitNarrative",
    # =========================================================================
    # Legacy: Phase 9, VKG 3.5, VKG 4.0 (Preserved)
    # =========================================================================
    # Base classes
    "VerificationAgent",
    "AgentResult",
    "AgentEvidence",
    "EvidenceType",
    # Phase 9 Agents
    "ExplorerAgent",
    "PatternAgent",
    "ConstraintAgent",
    "RiskAgent",
    # Phase 2 Agents (VKG 3.5)
    "AttackerAgent",
    "AttackerResult",
    "AttackConstruction",
    "AttackCategory",
    "AttackFeasibility",
    "EconomicImpact",
    "ExploitabilityFactors",
    "DefenderAgent",
    "DefenderResult",
    "DefenseArgument",
    "DefenseType",
    "RebuttalStrategy",
    "GuardInfo",
    "Rebuttal",
    "AdversarialArbiter",
    "ArbitrationResult",
    "VerdictType",
    "ConfidenceLevel",
    "WinningSide",
    "Evidence",
    "EvidenceChain",
    # Consensus
    "AgentConsensus",
    "ConsensusResult",
    "Verdict",
    # Enhanced Consensus (P2-T6)
    "EnhancedAgentConsensus",
    "EnhancedConsensusResult",
    "ConsensusMode",
    # LLMDFA Verifier (P2-T4)
    "LLMDFAVerifier",
    "VerificationResult",
    "VerificationStatus",
    "ConstraintType",
    "PathConstraint",
    "ConstraintSet",
    "WitnessValues",
    "UnsatCore",
    "verify_path_feasibility",
    # Phase 12: Agent SDK Micro-Agents
    "SDKManager",
    "SDKType",
    "SDKStatus",
    "SDKInfo",
    "SDKConfig",
    "sdk_available",
    "get_available_sdks",
    "get_sdk_manager",
    "get_installation_guide",
    "get_fallback_message",
    "MicroAgent",
    "MicroAgentType",
    "MicroAgentStatus",
    "MicroAgentConfig",
    "MicroAgentCost",
    "MicroAgentResult",
    "VerificationMicroAgent",
    "TestGenMicroAgent",
    "create_verifier",
    "create_test_generator",
    "SwarmManager",
    "SwarmStatus",
    "SwarmConfig",
    "SwarmProgress",
    "SwarmResult",
    "swarm_verify",
    "swarm_generate_tests",
    "create_swarm_manager",
    "FallbackHandler",
    "FallbackType",
    "FallbackResult",
    "get_fallback_for_verification",
    "get_fallback_for_test_gen",
    "should_use_fallback",
    "CostTracker",
    "CostReport",
    "UsageRecord",
    "BudgetExceededError",
    "estimate_cost",
    "get_global_tracker",
    "set_global_budget",
    "reset_global_tracker",
]
