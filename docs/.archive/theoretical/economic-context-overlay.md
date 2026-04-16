# Economic Context Overlay Specification

**Version:** 1.0.0
**Status:** Normative Reference
**Phase:** 05.11 - Economic Context + Agentic Workflow Integrity

The Economic Context Overlay extends the Protocol Context Pack with causal edges for exploitation reasoning, game-theoretic payoff fields for attack modeling, and provenance rules for evidence-gated workflow integrity.

---

## Overview

The overlay provides:
1. **Causal reasoning** - Track how vulnerabilities cause, enable, amplify, or block exploitation
2. **Game-theoretic analysis** - Model attacker/defender payoffs to assess attack viability
3. **Evidence provenance** - Label expectations as declared/inferred/hypothesis for finding gating
4. **Staleness tracking** - TTL and diff beacons to detect stale assumptions

---

## Node Types

### Standard Overlay Nodes

| Type | Description | Key Fields |
|------|-------------|------------|
| `Role` | Protocol role with capabilities | name, capabilities, trust_assumptions |
| `ValueFlow` | Economic value movement | from_role, to_role, asset, conditions |
| `Incentive` | Protocol incentive structure | actor, payoff, cost, time_horizon |
| `OffchainInput` | Oracle, relayer, admin, UI | source, update_policy, trust_model |
| `Governance` | Governance and upgrade paths | upgrade_path, timelock_seconds, quorum |
| `Assumption` | Protocol assumption | description, category, affects_functions |

### Causal Nodes (05.11 Extension)

| Type | Description | Usage |
|------|-------------|-------|
| `RootCause` | Root cause of an exploit path | Starting point for causal reasoning |
| `ExploitStep` | Intermediate exploitation step | Links root cause to financial loss |
| `FinancialLoss` | End-state financial impact | Terminal node in causal chain |

---

## Edge Types

### Standard Overlay Edges

| Edge Type | Source | Target | Description |
|-----------|--------|--------|-------------|
| `ROLE_CONTROLS_FUNCTION` | Role | Function | Role can call this function |
| `VALUE_FLOW_THROUGH_FUNCTION` | ValueFlow | Function | Value moves through function |
| `OFFCHAIN_INPUT_FEEDS_FUNCTION` | OffchainInput | Function | Off-chain data feeds function |
| `ASSUMPTION_AFFECTS_FUNCTION` | Assumption | Function | Assumption applies to function |
| `GOVERNANCE_CAN_CHANGE_STATE` | Governance | State | Governance controls state |

### Causal Edge Types (05.11 Extension)

| Edge Type | Semantics | Example |
|-----------|-----------|---------|
| `CAUSES` | Direct causation (A causes B) | Price manipulation CAUSES bad liquidation |
| `ENABLES` | A enables B (necessary but not sufficient) | Flash loan ENABLES oracle manipulation |
| `AMPLIFIES` | A increases severity of B | MEV extraction AMPLIFIES profit loss |
| `BLOCKS` | A prevents or mitigates B | Timelock BLOCKS governance attack |

**CausalEdge Schema:**

```yaml
source_node: "oracle.price_manipulation"
target_node: "vault.bad_liquidation"
edge_type: "causes"
probability: 0.8  # 0.0-1.0
confidence: "inferred"  # certain/inferred/unknown
evidence_refs:
  - "oracle-manipulation-001"
  - "liquidation-vuln-002"
description: "Manipulated oracle price causes incorrect liquidation"
```

---

## Provenance Rules

### Expectation Provenance Labels

| Label | Definition | Finding Gate |
|-------|------------|--------------|
| `DECLARED` | Explicit in official docs/governance/on-chain config | Can trigger findings |
| `INFERRED` | Deduced from code + patterns + heuristics | Warnings only, no findings |
| `HYPOTHESIS` | Plausible but unsupported | Triggers probes, not findings |

### TTL and Confidence Decay

Every fact includes freshness metadata:

```yaml
source_id: "whitepaper-v1.2"
source_date: "2025-01-15"
source_type: "docs"  # docs, governance, on-chain, audit, code
expires_at: "2025-04-15"  # Optional TTL
```

**Staleness rules:**
- If `expires_at` is past current date, mark fact as stale
- Stale facts downgrade to `unknown` confidence
- Agents must cite date of assumptions they rely on
- Diff beacon auto-detects content changes and marks stale

---

## Game-Theoretic Payoff Fields

### AttackPayoff

Models attacker's expected value for exploiting a vulnerability:

```yaml
expected_profit_usd: 100000
gas_cost_usd: 500
mev_risk: 0.3  # Probability of MEV front-running
success_probability: 0.7
capital_required_usd: 0  # Flash loans = 0
execution_complexity: "medium"  # low/medium/high
detection_risk: 0.2
evidence_refs:
  - "price-oracle-001"
```

**Expected Value Calculation:**

```
EV = P(success) * profit - gas_cost - P(MEV) * profit * 0.5
```

### DefensePayoff

Models defender's detection and mitigation capabilities:

```yaml
detection_probability: 0.8
mitigation_cost_usd: 50000
timelock_delay_seconds: 86400  # 1 day
response_time_seconds: 3600  # 1 hour
insurance_coverage_usd: 500000
emergency_pause_capable: true
evidence_refs:
  - "security-audit-002"
```

**Expected Loss Calculation:**

```
Loss = (1 - P(detect)) * attack_profit + mitigation_cost - min(loss, insurance)
```

### PayoffMatrix

3-player game model for complete attack analysis:

```yaml
scenario: "oracle_manipulation"
attacker_payoff:
  expected_profit_usd: 100000
  success_probability: 0.7
  # ...
defender_payoff:
  detection_probability: 0.8
  # ...
outcomes:
  - name: "attack_succeeds_undetected"
    probability: 0.14
    attacker_payoff_usd: 100000
    protocol_payoff_usd: -100000
    mev_payoff_usd: 0
  - name: "attack_detected_blocked"
    probability: 0.56
    attacker_payoff_usd: -500  # Gas cost
    protocol_payoff_usd: 0
    mev_payoff_usd: 0
tvl_at_risk_usd: 10000000
evidence_refs:
  - "economic-analysis-001"
```

**Nash Equilibrium (Stub):**

```python
matrix = PayoffMatrix(...)
eq = matrix.compute_nash_equilibrium()
# Returns heuristic strategies until full implementation in 05.11-06
```

---

## Example Dossier

An Aave V3-style protocol dossier excerpt:

```yaml
version: "1.0"
schema_version: "1.1"
protocol_name: "Aave V3"
protocol_type: "lending"

roles:
  - name: "admin"
    capabilities: ["pause", "upgrade", "set_risk_params"]
    trust_assumptions:
      - "Admin is trusted multisig (3/5)"
      - "Admin will not rug users"
    confidence: "certain"
    provenance: "declared"
    source_id: "governance-docs"
    source_date: "2025-01-10"
    source_type: "docs"

  - name: "liquidator"
    capabilities: ["liquidate"]
    trust_assumptions:
      - "Liquidators are permissionless"
      - "Liquidators act for profit"
    confidence: "certain"
    provenance: "declared"

assumptions:
  - description: "Oracle prices are accurate within 1% of spot"
    category: "price"
    affects_functions: ["liquidate", "borrow", "repay"]
    confidence: "inferred"
    provenance: "declared"
    source_id: "risk-docs"
    source_date: "2025-01-08"
    source_type: "docs"
    expires_at: "2025-04-08"  # 90-day TTL

invariants:
  - formal:
      what: "user_collateral_value"
      must: "gte"
      value: "user_debt_value * min_health_factor"
    natural_language: "User collateral must exceed debt by health factor"
    confidence: "certain"
    provenance: "declared"
    category: "solvency"
    critical: true

causal_edges:
  - source_node: "oracle.stale_price"
    target_node: "liquidation.bad_liquidation"
    edge_type: "causes"
    probability: 0.6
    evidence_refs: ["oracle-staleness-001"]
    description: "Stale oracle price causes incorrect liquidation threshold"

  - source_node: "timelock.24h_delay"
    target_node: "governance.param_attack"
    edge_type: "blocks"
    probability: 0.9
    evidence_refs: ["governance-timelock-001"]
    description: "24-hour timelock blocks rapid parameter changes"

attack_payoff_model:
  expected_profit_usd: 500000
  gas_cost_usd: 1000
  mev_risk: 0.4
  success_probability: 0.3
  capital_required_usd: 0  # Flash loan
  execution_complexity: "high"
  detection_risk: 0.7

defender_payoff_model:
  detection_probability: 0.85
  mitigation_cost_usd: 100000
  timelock_delay_seconds: 86400
  response_time_seconds: 1800
  insurance_coverage_usd: 10000000
  emergency_pause_capable: true
```

---

## Usage Notes for Agent Reasoning

### Evidence Gates

Agents must follow evidence gating rules:

1. **No confidence upgrade without evidence_refs**
   - Findings require explicit evidence citations
   - Missing evidence blocks confidence upgrade

2. **Missing economic assumptions => unknown**
   - If critical context is missing, degrade to unknown
   - Request context expansion before proceeding

3. **Provenance gates findings**
   - DECLARED provenance can trigger findings
   - INFERRED provenance emits warnings
   - HYPOTHESIS triggers probes for investigation

### Economic Reasoning Lenses

Agents should tag reasoning with economic lenses:

| Lens | Question |
|------|----------|
| Value Flow | Where does value enter/exit? Who holds custody? |
| Control | Who can alter parameters, pause, upgrade, seize funds? |
| Incentive | Who profits from breaking an invariant? At what cost? |
| Trust | Which off-chain inputs can move prices or state? |
| Timing | Where do delays, auctions, or timelocks create windows? |
| Configuration | What mis-set parameters create exploitability? |

Each finding should reference at least one lens or explicitly state "lens missing".

### Staleness Handling

When encountering stale facts:

1. Check `is_stale()` method on assumptions, roles, invariants
2. Stale facts auto-downgrade to `unknown` confidence
3. Surface stale facts to agents as "uncertain" context
4. Request refresh via dossier builder if critical

### Payoff-Based Prioritization

Use payoff models to prioritize investigation:

```python
if matrix.is_attack_profitable and matrix.is_high_risk:
    # High priority - profitable attack with low detection
    priority = "critical"
elif matrix.is_attack_profitable:
    # Medium priority - profitable but detectable
    priority = "high"
else:
    # Low priority - unprofitable attack
    priority = "medium"
```

---

## Integration Points

| Component | Integration |
|-----------|-------------|
| `ProtocolContextPack` | `causal_edges`, `attack_payoff_model`, `defender_payoff_model` fields |
| `DossierBuilder` | Ingests sources with provenance, builds records with TTL |
| `DiffBeacon` | Detects content changes, marks stale sources |
| `PayoffMatrix` | Computes expected values, stub Nash equilibrium |

---

## References

- [05.11-CONTEXT.md](../../.planning/phases/05.11-economic-context-agentic-workflow-integrity/05.11-CONTEXT.md) - Phase context
- [types.py](../../src/alphaswarm_sol/context/types.py) - ExpectationProvenance, CausalEdgeType, CausalEdge
- [schema.py](../../src/alphaswarm_sol/context/schema.py) - ProtocolContextPack extensions
- [dossier.py](../../src/alphaswarm_sol/context/dossier.py) - DossierBuilder, DiffBeacon
- [payoff.py](../../src/alphaswarm_sol/economics/payoff.py) - AttackPayoff, DefensePayoff, PayoffMatrix

---

*Specification Version: 1.0.0*
*Created: 2026-01-27*
*Phase: 05.11-economic-context-agentic-workflow-integrity*
