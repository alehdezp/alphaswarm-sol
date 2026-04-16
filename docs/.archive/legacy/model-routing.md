# Model Routing Guide

This guide covers the tiered model routing system for cost-effective LLM usage in AlphaSwarm.sol.

## Overview

AlphaSwarm.sol uses a **validator-first** approach to model selection:

1. Start with the cheapest viable tier (CHEAP/validator)
2. Escalate to higher tiers only when needed (risk, evidence gaps, complexity)
3. Downgrade when budget is constrained

This approach reduces costs by 35-50% while maintaining detection precision.

## Model Tiers

| Tier | Models | Use Case | Relative Cost |
|------|--------|----------|---------------|
| **CHEAP** | Haiku, GPT-4o-mini, Gemini Flash | Simple validation, pattern checks | 0.1x |
| **STANDARD** | Sonnet, GPT-4o, Gemini Pro | Typical analysis, verification | 1.0x |
| **PREMIUM** | Opus, O1 | Complex reasoning, business logic | 10.0x |

## Quick Start

```python
from alphaswarm_sol.llm.routing_policy import TierRoutingPolicy, route_task
from alphaswarm_sol.llm.tiers import ModelTier

# Simple routing
decision = route_task(
    task_type="pattern_validation",
    risk_score=0.2,
    evidence_completeness=0.9,
)
print(f"Tier: {decision.tier}")  # ModelTier.CHEAP

# High-risk routing (escalates)
decision = route_task(
    task_type="tier_b_verification",
    risk_score=0.85,
    evidence_completeness=0.3,
)
print(f"Tier: {decision.tier}")  # ModelTier.PREMIUM
print(f"Rationale: {decision.rationale}")
```

## TierRoutingPolicy

The core routing logic lives in `TierRoutingPolicy`:

```python
from alphaswarm_sol.llm.routing_policy import (
    TierRoutingPolicy,
    EscalationThresholds,
)

# Default policy
policy = TierRoutingPolicy()

# Custom thresholds
thresholds = EscalationThresholds(
    risk_score_standard=0.4,      # Escalate at lower risk
    risk_score_premium=0.7,       # Premium at moderate risk
    evidence_completeness_low=0.4, # Require more evidence
    budget_low_threshold_usd=3.0, # Stricter budget awareness
)
policy = TierRoutingPolicy(thresholds=thresholds)
```

### Routing Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `task_type` | str | Task identifier (maps to default tier) | Required |
| `risk_score` | float | Risk level (0.0-1.0) | 0.0 |
| `evidence_completeness` | float | Evidence coverage (0.0-1.0) | 1.0 |
| `budget_remaining` | float | Remaining budget in USD | None (unlimited) |
| `severity` | str | Severity level (critical/high/medium/low) | None |
| `pattern_type` | str | Pattern being analyzed | None |
| `pool_id` | str | Pool ID for per-pool config | None |
| `workflow_id` | str | Workflow ID for per-workflow config | None |

### Task Type Defaults

The policy maps task types to default tiers:

**CHEAP (validator) tier:**
- `evidence_extraction`
- `pattern_validation`
- `code_parsing`
- `format_validation`
- `syntax_check`

**STANDARD (specialist) tier:**
- `tier_b_verification`
- `context_analysis`
- `fp_filtering`
- `guard_analysis`

**PREMIUM (expert) tier:**
- `exploit_synthesis`
- `business_logic_analysis`
- `multi_step_reasoning`
- `attack_path_generation`
- `cross_contract_analysis`

## Escalation Rules

### Risk-Based Escalation

| Risk Score | Action |
|------------|--------|
| < 0.5 | Stay at default tier |
| >= 0.5 | Escalate to STANDARD |
| >= 0.8 | Escalate to PREMIUM |

```python
# Low risk - stays CHEAP
policy.route("pattern_validation", risk_score=0.3)  # -> CHEAP

# Moderate risk - escalates to STANDARD
policy.route("pattern_validation", risk_score=0.6)  # -> STANDARD

# High risk - escalates to PREMIUM
policy.route("pattern_validation", risk_score=0.9)  # -> PREMIUM
```

### Evidence-Based Escalation

Low evidence completeness triggers escalation:

```python
# Good evidence - default tier
policy.route("pattern_validation", evidence_completeness=0.9)  # -> CHEAP

# Poor evidence - needs better analysis
policy.route("pattern_validation", evidence_completeness=0.2)  # -> STANDARD
```

### Severity-Based Escalation

Critical/high severity always escalates from CHEAP:

```python
policy.route("pattern_validation", severity="critical")  # -> STANDARD
policy.route("pattern_validation", severity="high")      # -> STANDARD
```

### Pattern Complexity Escalation

Complex patterns force PREMIUM tier:

- `business-logic-*`
- `cross-contract-*`
- `flash-loan-*`
- `governance-*`
- `economic-*`
- `oracle-manipulation-*`

```python
policy.route("tier_b_verification", pattern_type="flash-loan-attack")  # -> PREMIUM
```

## Budget-Aware Downgrades

When budget is constrained, the policy downgrades tiers:

| Budget Remaining | Action |
|------------------|--------|
| > $2.00 | No downgrade |
| $0.50 - $2.00 | Cap at STANDARD |
| < $0.50 | Force CHEAP |

```python
# Low budget - downgrade from PREMIUM
policy.route("exploit_synthesis", budget_remaining=1.5)  # -> STANDARD

# Critical budget - force CHEAP
policy.route("exploit_synthesis", budget_remaining=0.3)  # -> CHEAP
```

## Routing Decision Metadata

Every routing decision includes metadata for auditing:

```python
decision = policy.route(
    task_type="tier_b_verification",
    risk_score=0.7,
    evidence_completeness=0.5,
)

# Access metadata
print(decision.tier)              # ModelTier.STANDARD
print(decision.rationale)         # Human-readable explanation
print(decision.escalation_reasons) # List of EscalationReason
print(decision.was_escalated)     # True/False
print(decision.was_downgraded)    # True/False
print(decision.estimated_cost_usd) # Estimated cost

# Serialize for logging
data = decision.to_dict()
```

## Integration with Subagents

The `LLMSubagentManager` uses routing policy automatically:

```python
from alphaswarm_sol.llm.subagents import (
    LLMSubagentManager,
    SubagentTask,
    TaskType,
)

# Manager with budget
manager = LLMSubagentManager(budget_usd=10.0)

# Task with routing hints
task = SubagentTask(
    type=TaskType.TIER_B_VERIFICATION,
    prompt="Verify this finding",
    context={"finding": finding_data},
    risk_score=0.7,
    evidence_completeness=0.4,
    severity="high",
    pattern_type="reentrancy",
)

result = await manager.dispatch(task)

# Result includes routing metadata
print(result.tier)              # ModelTier.STANDARD
print(result.tier_rationale)    # Why this tier
print(result.routing_decision)  # Full decision dict
```

## Integration with Agent Router

The `PolicyAwareAgentRouter` extends the agent router with tier policy:

```python
from alphaswarm_sol.routing.router import PolicyAwareAgentRouter
from alphaswarm_sol.llm.routing_policy import TierRoutingPolicy

policy = TierRoutingPolicy()
router = PolicyAwareAgentRouter(
    code_kg=knowledge_graph,
    routing_policy=policy,
    budget_usd=10.0,
)

# Route with tier policy
results = router.route_with_tier_policy(
    focal_nodes=["Vault.withdraw"],
    risk_score=0.8,
    evidence_completeness=0.3,
    severity="critical",
)

# Results include tier_routing metadata
for agent_type, result in results.items():
    print(f"{agent_type}: {result.metadata.get('tier_routing')}")

# Get routing summary
summary = router.get_routing_summary()
print(f"Escalations: {summary['escalations']}")
print(f"Downgrades: {summary['downgrades']}")
```

## Configuration

### Per-Pool Configuration

Configure thresholds per pool:

```python
policy = TierRoutingPolicy(
    thresholds=EscalationThresholds(
        risk_score_standard=0.3,  # More aggressive escalation
    )
)

decision = policy.route(
    task_type="tier_b_verification",
    pool_id="high-value-pool",  # Tracked for auditing
)
```

### Per-Workflow Configuration

```python
decision = policy.route(
    task_type="tier_b_verification",
    workflow_id="full-audit-workflow",
)
```

## Customization

### Custom Thresholds

```python
from alphaswarm_sol.llm.routing_policy import (
    TierRoutingPolicy,
    EscalationThresholds,
)

# Aggressive escalation (more cautious)
aggressive = EscalationThresholds(
    risk_score_standard=0.3,
    risk_score_premium=0.5,
    evidence_completeness_low=0.5,
)

# Conservative escalation (cost-saving)
conservative = EscalationThresholds(
    risk_score_standard=0.7,
    risk_score_premium=0.9,
    evidence_completeness_low=0.2,
)

policy = TierRoutingPolicy(thresholds=aggressive)
```

### Custom Default Tier

```python
# Default to STANDARD instead of CHEAP for unknown tasks
policy = TierRoutingPolicy(default_tier=ModelTier.STANDARD)
```

## Best Practices

1. **Always provide risk_score when known** - Enables intelligent escalation
2. **Track evidence_completeness** - Low evidence justifies expensive analysis
3. **Set budget limits** - Prevents runaway costs
4. **Use pool_id/workflow_id** - Enables per-context tuning
5. **Log routing decisions** - Use `decision.to_dict()` for auditing
6. **Review escalation patterns** - Tune thresholds based on outcomes

## Troubleshooting

### Unexpected Escalations

Check escalation reasons:

```python
decision = policy.route(...)
for reason in decision.escalation_reasons:
    print(f"Escalation: {reason.value}")
```

Common causes:
- Risk score > 0.5
- Evidence completeness < 0.3
- Severity = critical/high
- Complex pattern type

### Budget Downgrades

```python
if decision.was_downgraded:
    print(f"Downgraded due to budget: {decision.metadata['budget_remaining']}")
```

### Debugging

Enable debug logging:

```python
import logging
logging.getLogger("alphaswarm_sol.llm.subagents").setLevel(logging.DEBUG)
```

## Related Documentation

- [Model Tiers Reference](../reference/model-tiers.md)
- [Cost Tracking Guide](cost-tracking.md)
- [Context Budget Guide](context-budget.md)
