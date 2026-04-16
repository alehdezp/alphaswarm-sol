# Governance Guide

This guide explains how to configure and enforce governance policies for cost control, tool access, and evidence integrity.

## Overview

Phase 7.1.5 governance provides:

- **Cost Budgets**: Hard/soft limits per pool with blocking or alerting
- **Tool Access Control**: Role-based tool restrictions per agent type
- **Evidence Integrity**: Gates requiring evidence for confidence upgrades
- **Model Usage**: Approved model lists with tier routing enforcement

## Quick Start

### Enable Policy Enforcement

```python
from alphaswarm_sol.governance import PolicyEnforcer, enforce_policy
from alphaswarm_sol.observability.audit import AuditLogger
from alphaswarm_sol.metrics.cost_ledger import CostLedger
from pathlib import Path

# Setup
cost_ledger = CostLedger()
audit_logger = AuditLogger()

enforcer = PolicyEnforcer(
    policies_path=Path("configs/governance_policies.yaml"),
    cost_ledger=cost_ledger,
    audit_logger=audit_logger,
)
```

### Check Policies Manually

```python
# Check before agent execution
violation = enforcer.check_input_policy(
    agent_type="vrs-attacker",
    input_data={"tools": ["slither", "mythril"]},
    pool_id="pool-abc123",
    trace_id="trace_xyz789",
)

if violation:
    print(f"Policy violated: {violation.message}")
    if violation.suggested_action == PolicyAction.BLOCK:
        raise PolicyViolationError(violation)
```

### Use Decorator

```python
from alphaswarm_sol.governance import enforce_policy

@enforce_policy(enforcer)
def execute_agent(pool_id: str, agent_type: str, input_data: dict, trace_id: str = None):
    # Policy checks happen automatically before/after execution
    return run_agent(...)
```

## Policy Configuration

### Cost Budget

```yaml
# configs/governance_policies.yaml
policies:
  cost_budget:
    hard_limit_usd: 10.0      # Block when exceeded
    soft_limit_usd: 8.0       # Alert when exceeded
    enabled: true
    block_on_exceed: true     # If false, logs warning instead
```

**Behavior:**
- **Hard limit**: `PolicyViolationError` raised, execution blocked (if `block_on_exceed: true`)
- **Soft limit**: Warning logged, execution continues
- Budget is per-pool (tracked in CostLedger by pool_id)

### Tool Access

```yaml
policies:
  tool_access:
    enabled: true
    role_restrictions:
      vrs-attacker:
        - slither
        - mythril
        - echidna
        - bskg_query
      vrs-defender:
        - slither
        - aderyn
        - halmos
        - bskg_query
      vrs-verifier:
        - bskg_query
        - semgrep
      vrs-secure-reviewer:
        - slither
        - bskg_query
        - semgrep
    forbidden_tools:
      - shell_exec  # No arbitrary shell execution
      - file_write  # No direct file writes
```

**Enforcement:**
- Agent can only use tools in their `allowed` list
- `forbidden_tools` are blocked for all agents
- Violation raises `PolicyViolationError`

### Evidence Integrity

```yaml
policies:
  evidence_integrity:
    enabled: true
    require_evidence_refs: true  # Block confidence upgrades without evidence
    min_evidence_count: 1        # Minimum number of evidence refs required
```

**Behavior:**
- Upgrading confidence to `LIKELY` or `CONFIRMED` requires evidence references
- Minimum evidence count enforced (default: 1)
- Evidence must have valid lineage chain (if lineage tracking enabled)

### Model Usage

```yaml
policies:
  model_usage:
    enabled: true
    tier_restrictions:
      vrs-attacker:
        - opus    # High-tier for exploit construction
        - sonnet
      vrs-defender:
        - sonnet  # Mid-tier for guard search
        - haiku
      vrs-verifier:
        - opus    # High-tier for cross-check
        - sonnet
      cost-governor:
        - haiku   # Low-tier for budget monitoring
    allowed_models: []  # Empty = use tier_restrictions
```

**Enforcement:**
- Agent can only use models in their tier list
- If `allowed_models` is non-empty, it overrides `tier_restrictions`
- Violation blocks agent execution

## PolicyAction Values

| Action | Behavior |
|--------|----------|
| `ALLOW` | Allow execution, no logging |
| `BLOCK` | Raise `PolicyViolationError`, stop execution |
| `SANITIZE` | Clean output before returning |
| `ALERT` | Log warning, continue execution |

## PolicyViolation Details

```python
from alphaswarm_sol.governance import PolicyViolation, PolicyAction
from dataclasses import dataclass

@dataclass
class PolicyViolation:
    policy_id: str           # e.g., "cost_budget.hard_limit"
    violation_type: str      # e.g., "budget_exceeded"
    severity: str            # "critical", "high", "medium", "low"
    message: str             # Human-readable description
    suggested_action: PolicyAction  # ALLOW, BLOCK, SANITIZE, ALERT
    details: dict            # Additional context
```

## Handling Violations

### Custom Violation Handling

```python
from alphaswarm_sol.governance import PolicyAction, PolicyViolationError

def handle_violation(violation: PolicyViolation, pool_id: str):
    if violation.suggested_action == PolicyAction.BLOCK:
        # Hard stop
        raise PolicyViolationError(violation)
    elif violation.suggested_action == PolicyAction.ALERT:
        # Log and continue
        logger.warning(f"Policy alert: {violation.message}")
    elif violation.suggested_action == PolicyAction.SANITIZE:
        # Clean output
        return sanitize_output(result)
```

### Audit Logging Integration

```python
# Violations automatically logged to audit log
from alphaswarm_sol.observability.audit import AuditLogger

audit_logger = AuditLogger(log_path=Path("logs/audit.jsonl"))

# PolicyEnforcer logs violations automatically
enforcer = PolicyEnforcer(
    policies_path=Path("configs/governance_policies.yaml"),
    audit_logger=audit_logger,
)
```

## Integration with Existing Code

### PoolManager Integration

```python
from alphaswarm_sol.orchestration.pool import PoolManager

pool_manager = PoolManager(
    policy_enforcer=enforcer,
    cost_ledger=cost_ledger,
)

# Policies enforced automatically on agent execution
result = pool_manager.execute_pool(pool.id)
```

### Handler Integration

```python
# In orchestration/handlers.py
from alphaswarm_sol.governance import enforce_policy

@enforce_policy(global_enforcer)
def handle_agent_execution(
    pool_id: str,
    agent_type: str,
    input_data: dict,
    trace_id: str = None,
):
    # Policies checked before/after execution
    # - Tool access checked in input_data
    # - Cost budget checked before execution
    # - Evidence integrity checked in output
    ...
```

### Custom Policy Validators

```python
from alphaswarm_sol.governance.validators import BaseValidator

class CustomValidator(BaseValidator):
    def validate_input(self, agent_type: str, input_data: dict, pool_id: str):
        # Custom validation logic
        if some_condition:
            return PolicyViolation(
                policy_id="custom.check",
                violation_type="custom_failure",
                severity="medium",
                message="Custom check failed",
                suggested_action=PolicyAction.ALERT,
                details={},
            )
        return None

# Register validator
enforcer.add_validator(CustomValidator())
```

## Best Practices

1. **Set soft limits at 80% of hard limits** for early warning
2. **Use role_restrictions for granular tool access** instead of global allowed_models
3. **Enable evidence_integrity** to enforce graph-first reasoning
4. **Log all violations** to audit log for forensics
5. **Review policies after major version upgrades** (model changes, new tools)

## See Also

- [Policy Configuration Reference](../reference/policy-config.md)
- [Observability Guide](observability.md) - Policy violations in audit logs
- [Role-Based Tool Policies](../reference/skill-tool-policies.md)
- [Cost Budgeting Guide](cost-budgeting.md)
