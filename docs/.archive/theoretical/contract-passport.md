# Contract Passport Reference

**Version:** 1.0
**Status:** Normative
**Updated:** 2026-01-27

## Overview

Contract passports are compact, per-contract summaries that capture the economic role,
assets handled, critical actions, and cross-protocol dependencies of each contract in
a protocol. They serve as the primary context snippet for agent reasoning.

## Purpose

Passports solve the **context overload problem**: agents need enough context to reason
about economic implications, but too much context leads to omission or hallucination.
Passports provide a structured, bounded summary that agents can consume efficiently.

## Schema

### ContractPassport

```yaml
contract_id: "Vault"
economic_purpose: "Handles ETH deposits and withdrawals for users"
assets_handled:
  - ETH
  - WETH
critical_actions:
  - deposit
  - withdraw
  - liquidate
allowed_lifecycle_stages:
  - active
  - paused
  - emergency
roles_controls:
  admin:
    - pause
    - upgrade
  keeper:
    - liquidate
external_dependencies:
  - oracle:liquidate
cross_protocol_dependencies:
  - protocol_id: chainlink
    dependency_type: oracle
    description: "ETH/USD price feed"
    criticality: 9
    failure_cascade_impact: "Incorrect liquidations, potential bad debt"
    last_verified_date: "2026-01-15"
    confidence: certain
    affected_functions:
      - liquidate
      - getCollateralValue
invariant_ids:
  - inv:balance:001
  - inv:supply:002
systemic_risk_score: 7.5
created_at: "2026-01-27T12:00:00Z"
last_updated: "2026-01-27T12:00:00Z"
```

### CrossProtocolDependency

External protocol dependencies track systemic risk from composability.

```yaml
protocol_id: "chainlink"
dependency_type: oracle  # oracle, liquidity, governance, collateral, bridge, keeper, custody, lending
description: "ETH/USD price feed for liquidation calculations"
criticality: 9  # 1-10 scale (10 = critical)
failure_cascade_impact: "Incorrect liquidations, potential bad debt accumulation"
last_verified_date: "2026-01-15"
confidence: certain  # certain, inferred, unknown
affected_functions:
  - liquidate
  - getCollateralValue
```

### Dependency Types

| Type | Description | Example |
|------|-------------|---------|
| `oracle` | Price feeds, data oracles | Chainlink, Pyth |
| `liquidity` | Liquidity sources, AMM pools | Uniswap, Curve |
| `governance` | External governance tokens/votes | Compound governance |
| `collateral` | External collateral assets | stETH, wstETH |
| `bridge` | Cross-chain bridges | LayerZero, Wormhole |
| `keeper` | External keepers/bots | Gelato, Chainlink Automation |
| `custody` | External custody/vaults | Yearn vaults |
| `lending` | External lending protocols | Aave, Compound |

### Lifecycle Stages

| Stage | Description |
|-------|-------------|
| `init` | Setup and role assignment |
| `active` | Normal operation |
| `paused` | Limited actions, often admin-only |
| `emergency` | Rescue/withdrawal paths only |
| `sunset` | Shutdown or migration phase |
| `upgrade` | Governance-driven changes |

## Systemic Risk Scoring

The `systemic_risk_score` (0-10) is derived from dependency analysis:

```python
risk_score = avg_criticality + critical_bonus + oracle_bonus + centrality_bonus
```

**Components:**

1. **Average criticality** - Mean criticality of all dependencies
2. **Critical bonus** - +0.5 per critical dependency (>= 8), max +2.0
3. **Oracle bonus** - +0.3 per oracle dependency, max +1.0
4. **Centrality bonus** - +0.2 per unique protocol, max +1.5

**Interpretation:**

| Score | Risk Level | Action |
|-------|------------|--------|
| 0-3 | Low | Standard verification |
| 4-6 | Medium | Enhanced verification |
| 7-8 | High | Full multi-agent debate |
| 9-10 | Critical | Manual review required |

## Integration with Routing

Passports are attached to agent context slices at routing time:

1. Router retrieves passport for target contract
2. Cross-protocol dependencies are included in context
3. Systemic risk score influences verification depth
4. Missing passports trigger context expansion requests

```python
from alphaswarm_sol.context.passports import PassportBuilder

builder = PassportBuilder(context_pack, kg_nodes)
passports = builder.build_all()

# Router attaches passport to context
passport = passports.get("Vault")
agent_context.passport = passport
agent_context.systemic_risk = passport.systemic_risk_score
```

## Invariant Registry Integration

Passports reference invariants from the `InvariantRegistry`:

```python
from alphaswarm_sol.context.invariant_registry import InvariantRegistry

registry = InvariantRegistry()

# Get invariants for a passport
for inv_id in passport.invariant_ids:
    invariant = registry.get(inv_id)
    if invariant.is_high_confidence:
        # Include in verification
        ...
```

## Generation

### From Context Pack + KG

```python
from alphaswarm_sol.context.passports import PassportBuilder, CrossProtocolDependency

builder = PassportBuilder(context_pack, kg_nodes)
passports = builder.build_all()

# Manually add dependency
dep = CrossProtocolDependency(
    protocol_id="uniswap-v3",
    dependency_type=DependencyType.LIQUIDITY,
    description="WETH/USDC pool for swaps",
    criticality=6,
)
builder.add_cross_protocol_dependency("Vault", dep)
```

### Manual Creation

```python
from alphaswarm_sol.context.passports import ContractPassport, LifecycleStage

passport = ContractPassport(
    contract_id="Vault",
    economic_purpose="Handles user deposits and liquidations",
    assets_handled=["ETH", "WETH"],
    critical_actions=["deposit", "withdraw", "liquidate"],
    allowed_lifecycle_stages=[LifecycleStage.ACTIVE, LifecycleStage.PAUSED],
)
```

## Serialization

Passports are stored in context pack storage alongside the protocol context:

```
{base_path}/
  {protocol_name}/
    context.yaml
    passports/
      Vault.yaml
      Token.yaml
      ...
```

## Best Practices

1. **Keep passports focused** - Include only security-relevant information
2. **Update regularly** - Passports should reflect current state
3. **Track dependencies** - All external protocol interactions should be documented
4. **Link invariants** - Connect passports to the invariant registry
5. **Verify criticality** - Cross-check criticality scores against actual risk

## Related Documentation

- [Economic Context Overlay](./economic-context-overlay.md) - Economic overlay schema
- [Graph Interface v2](./graph-interface-v2.md) - KG interface contract
- [Routing](./routing.md) - Agent routing system
