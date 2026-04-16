# Policy Configuration Reference

Complete specification for `configs/governance_policies.yaml`.

## Overview

The governance policies file defines operational boundaries enforced at runtime by `PolicyEnforcer`. Policies cover cost budgets, tool access, evidence integrity, and model usage.

## Schema

```yaml
metadata:
  version: string              # Schema version (e.g., "1.0")
  description: string          # Human-readable description
  updated: string              # Last update date (YYYY-MM-DD)

policies:
  cost_budget:
    hard_limit_usd: float      # Required: Block threshold
    soft_limit_usd: float      # Required: Alert threshold
    enabled: bool              # Default: true
    block_on_exceed: bool      # Default: true

  tool_access:
    enabled: bool              # Default: true
    role_restrictions:
      {agent_type}:            # Agent type (e.g., vrs-attacker)
        - string               # List of allowed tools
      ...
    forbidden_tools:
      - string                 # Tools forbidden for all agents

  evidence_integrity:
    enabled: bool              # Default: true
    require_evidence_refs: bool  # Block confidence upgrades without evidence
    min_evidence_count: int    # Minimum number of evidence refs

  model_usage:
    enabled: bool              # Default: true
    tier_restrictions:
      {agent_type}:            # Agent type
        - string               # List of allowed tiers (opus, sonnet, haiku)
      ...
    allowed_models: [string]   # If non-empty, overrides tier_restrictions
```

## PolicyAction Values

| Action | Behavior |
|--------|----------|
| `ALLOW` | Allow execution, no logging |
| `BLOCK` | Raise `PolicyViolationError`, stop execution |
| `SANITIZE` | Clean output before returning |
| `ALERT` | Log warning, continue execution |

## Policy Details

### Cost Budget

Controls spending per pool with hard and soft limits.

```yaml
policies:
  cost_budget:
    hard_limit_usd: 10.0      # Block when exceeded
    soft_limit_usd: 8.0       # Alert when exceeded (80% of hard)
    enabled: true
    block_on_exceed: true     # If false, logs warning instead of blocking
```

**Enforcement:**
- Checked before each agent execution
- Cost tracked in `CostLedger` by `pool_id`
- Hard limit: Raises `PolicyViolationError` if `block_on_exceed: true`
- Soft limit: Logs warning, continues execution

**Violation Fields:**
```python
PolicyViolation(
    policy_id="cost_budget.hard_limit",
    violation_type="budget_exceeded",
    severity="critical",
    message="Pool cost $10.50 exceeds hard limit $10.00",
    suggested_action=PolicyAction.BLOCK,
    details={
        "current_cost": 10.50,
        "hard_limit": 10.0,
        "pool_id": "pool-abc123",
    },
)
```

### Tool Access

Role-based restrictions on which tools each agent type can use.

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
      - shell_exec
      - file_write
```

**Enforcement:**
- Checked when agent requests tool usage
- Tool must be in agent's `allowed` list
- Tool must NOT be in global `forbidden_tools`
- Violation blocks execution

**Violation Fields:**
```python
PolicyViolation(
    policy_id="tool_access.role_restriction",
    violation_type="forbidden_tool",
    severity="high",
    message="Agent vrs-verifier cannot use tool 'mythril'",
    suggested_action=PolicyAction.BLOCK,
    details={
        "agent_type": "vrs-verifier",
        "requested_tool": "mythril",
        "allowed_tools": ["bskg_query", "semgrep"],
    },
)
```

### Evidence Integrity

Ensures verdicts are backed by evidence from BSKG/tools.

```yaml
policies:
  evidence_integrity:
    enabled: true
    require_evidence_refs: true  # Block confidence upgrades without evidence
    min_evidence_count: 1        # Minimum number of evidence refs required
```

**Enforcement:**
- Checked when agent outputs verdict with confidence
- `LIKELY` or `CONFIRMED` confidence requires evidence
- Evidence count must meet `min_evidence_count`
- Evidence must have valid lineage chain (if lineage tracking enabled)

**Violation Fields:**
```python
PolicyViolation(
    policy_id="evidence_integrity.missing_evidence",
    violation_type="insufficient_evidence",
    severity="high",
    message="Confidence 'LIKELY' requires at least 1 evidence reference",
    suggested_action=PolicyAction.BLOCK,
    details={
        "confidence": "LIKELY",
        "evidence_count": 0,
        "required_count": 1,
    },
)
```

### Model Usage

Restricts which models each agent type can use.

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
- Checked before agent execution
- If `allowed_models` is non-empty, it overrides `tier_restrictions`
- Model must be in agent's approved list
- Violation blocks execution

**Tier Mapping:**
| Tier | Models |
|------|--------|
| `opus` | `claude-opus-4`, `claude-3-opus`, `gpt-4o` |
| `sonnet` | `claude-3-5-sonnet`, `claude-sonnet-4` |
| `haiku` | `claude-3-haiku`, `claude-3-5-haiku` |

**Violation Fields:**
```python
PolicyViolation(
    policy_id="model_usage.tier_restriction",
    violation_type="unapproved_model",
    severity="medium",
    message="Agent cost-governor cannot use model 'claude-3-opus'",
    suggested_action=PolicyAction.BLOCK,
    details={
        "agent_type": "cost-governor",
        "requested_model": "claude-3-opus",
        "allowed_tiers": ["haiku"],
    },
)
```

## Default Configuration

Complete default configuration:

```yaml
metadata:
  version: "1.0"
  description: "Runtime governance policies for multi-agent orchestration"
  updated: "2026-01-29"

policies:
  cost_budget:
    hard_limit_usd: 10.0
    soft_limit_usd: 8.0
    enabled: true
    block_on_exceed: true

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
      - shell_exec
      - file_write

  evidence_integrity:
    enabled: true
    require_evidence_refs: true
    min_evidence_count: 1

  model_usage:
    enabled: true
    tier_restrictions:
      vrs-attacker:
        - opus
        - sonnet
      vrs-defender:
        - sonnet
        - haiku
      vrs-verifier:
        - opus
        - sonnet
      cost-governor:
        - haiku
    allowed_models: []
```

## Usage

### Loading Policies

```python
from alphaswarm_sol.governance import load_policies
from pathlib import Path

policies = load_policies(Path("configs/governance_policies.yaml"))
```

### Creating PolicyEnforcer

```python
from alphaswarm_sol.governance import PolicyEnforcer
from alphaswarm_sol.metrics.cost_ledger import CostLedger
from alphaswarm_sol.observability.audit import AuditLogger

enforcer = PolicyEnforcer(
    policies_path=Path("configs/governance_policies.yaml"),
    cost_ledger=CostLedger(),
    audit_logger=AuditLogger(),
)
```

### Checking Policies

```python
# Manual check
violation = enforcer.check_input_policy(
    agent_type="vrs-attacker",
    input_data={"tools": ["slither"]},
    pool_id="pool-abc123",
)

# Decorator-based
from alphaswarm_sol.governance import enforce_policy

@enforce_policy(enforcer)
def execute_agent(pool_id: str, agent_type: str, input_data: dict):
    # Policies checked automatically
    ...
```

## See Also

- [Governance Guide](../guides/governance.md)
- [Role-Based Tool Policies](skill-tool-policies.md)
