---
name: vrs-economic-context
description: |
  Economic Context Skills for vulnerability reasoning with game-theoretic,
  causal, and cross-protocol awareness. Provides 11 skills for building
  protocol dossiers, contract passports, policy diffs, and advanced analysis.

  Invoke when user wants to:
  - Build protocol dossier: "/vrs-protocol-dossier"
  - Generate contract passports: "/vrs-passport"
  - Compare expected vs actual policy: "/vrs-policy-diff"
  - Compute attack expected value: "/vrs-attack-ev"
  - Trace causal exploitation chains: "/vrs-causal-trace"
  - Explore counterfactual mitigations: "/vrs-counterfactual"
  - Analyze cascade failures: "/vrs-cascade-risk"

slash_command: vrs:economic-context
context: fork

tools:
  - Read
  - Glob
  - Grep
  - Bash(uv run alphaswarm*)
  - Task

model_tier: sonnet

---

# VRS Economic Context Skills - Protocol Dossier and Game-Theoretic Analysis

You are the **VRS Economic Context** skill pack, providing comprehensive economic reasoning capabilities for vulnerability analysis.

**CRITICAL: Invocation Model**
You are Claude Code, an agent that follows this skill documentation. When this skill says "use Bash tool," you invoke the Bash tool with the specified command. Skills are documentation files that guide agent behavior using standard tools.

## Purpose

Enable agents to reason about smart contract vulnerabilities with:
- **Protocol-level context** (dossier, passports, invariants)
- **Game-theoretic analysis** (attack EV, incentives, payoffs)
- **Causal reasoning** (exploitation chains, counterfactuals)
- **Cross-protocol awareness** (cascade failures, systemic risk)

---

## Skill Overview

| Skill | Purpose | Model |
|-------|---------|-------|
| `/vrs-protocol-dossier` | Build protocol dossier from docs/audits/config | Sonnet |
| `/vrs-passport` | Generate contract passports + lifecycle stages | Sonnet |
| `/vrs-policy-diff` | Compare expected policy vs access-control graph | Sonnet |
| `/vrs-econ-probes` | Run economic probes and record evidence refs | Haiku |
| `/vrs-misconfig-radar` | Scan for known misconfiguration patterns | Haiku |
| `/vrs-context-refresh` | Detect drift and expire stale facts | Haiku |
| `/vrs-attack-ev` | Compute game-theoretic expected value of attack | Sonnet |
| `/vrs-causal-trace` | Build and validate causal exploitation chains | Sonnet |
| `/vrs-counterfactual` | Explore "what if" scenarios for mitigations | Sonnet |
| `/vrs-cascade-risk` | Analyze cross-protocol cascade failures | Opus |
| `/vrs-loss-amplify` | Compute loss amplification from causal edges | Sonnet |

---

## Core Economic Skills

### `/vrs-protocol-dossier`

**Purpose:** Build a structured protocol dossier from docs, audits, and on-chain configuration.

**Inputs:**
- Protocol name and version
- Documentation URLs (whitepaper, docs, governance)
- Optional: Audit reports, on-chain addresses

**Outputs:**
```yaml
dossier:
  protocol_name: "Aave V3"
  version: "3.0.2"
  tvl_usd: 10_000_000_000
  roles:
    - name: admin
      capabilities: [upgrade, pause, set_params]
      trust_assumptions: ["3-of-5 multisig", "24h timelock"]
  value_flows:
    - name: deposit
      from: user
      to: pool
      asset: collateral
    - name: borrow
      from: pool
      to: user
      asset: debt
  invariants:
    - formal: {what: "healthFactor", must: "gte", value: 1}
      natural: "Users must maintain health factor >= 1"
  assumptions:
    - description: "Oracle prices accurate within 1%"
      source_id: "aave-risk-docs"
      source_date: "2025-01-15"
      provenance: declared
```

**Workflow:**
1. Fetch protocol documentation (Read URLs)
2. Extract roles, flows, invariants, assumptions
3. Validate against on-chain configuration if available
4. Generate structured dossier with provenance

---

### `/vrs-passport`

**Purpose:** Generate per-contract economic passports with lifecycle stages.

**Inputs:**
- Contract address or path
- Protocol dossier (from `/vrs-protocol-dossier`)

**Outputs:**
```yaml
passport:
  contract_id: "Vault.sol"
  economic_purpose: "ETH custody and yield generation"
  assets_handled:
    - type: ETH
      max_exposure_usd: 50_000_000
  critical_actions:
    - deposit
    - withdraw
    - rebalance
  roles:
    - admin (pause, upgrade)
    - keeper (rebalance)
  invariant_ids:
    - "inv-001"
    - "inv-002"
  lifecycle_stage: active  # init, active, paused, emergency, sunset
  cross_protocol_dependencies:
    - protocol: "Chainlink ETH/USD"
      dependency_type: oracle
      criticality: 9
  systemic_risk_score: 7.2
```

**Lifecycle Stages:**
- `init`: Setup and role assignment
- `active`: Normal operation
- `paused`: Limited actions, admin-only
- `emergency`: Rescue/withdrawal paths only
- `sunset`: Shutdown or migration
- `upgrade`: Governance-driven changes

---

### `/vrs-policy-diff`

**Purpose:** Compare expected access control policy against actual code implementation.

**Inputs:**
- Contract passport
- Knowledge graph (from `build-kg`)

**Outputs:**
```yaml
policy_diff:
  contract_id: "Vault.sol"
  mismatches:
    - action: upgrade
      expected_role: admin
      actual_role: null  # Missing check!
      mismatch_type: missing_check
      provenance: declared
      confidence: 0.95
      evidence_refs: ["EVD-12345678"]

    - action: pause
      expected_role: admin
      actual_role: any  # Public!
      mismatch_type: wrong_role
      provenance: inferred
      confidence: 0.70
```

**Mismatch Types:**
- `missing_check`: No access control on privileged action
- `wrong_role`: Different role than expected
- `extra_permission`: More permissive than declared
- `bypass_path`: Alternate path avoids checks

---

## Advanced Reasoning Skills

### `/vrs-attack-ev`

**Purpose:** Compute game-theoretic expected value of an attack scenario.

**Inputs:**
- Attack scenario description
- TVL at risk
- Success probability estimate
- Gas costs, MEV risk

**Outputs:**
```yaml
attack_ev:
  scenario: "oracle_manipulation"
  expected_value_usd: 45_000
  is_profitable: true
  breakdown:
    expected_profit: 100_000
    success_probability: 0.7
    gas_cost: 500
    mev_loss: 15_000  # 30% MEV risk * 50% extraction
  risk_adjusted_value: 35_000  # Accounts for detection
  confidence: medium
  evidence_refs: ["EVD-..."]
```

**Formula:**
```
EV = P(success) * profit - gas_cost - (mev_risk * profit * 0.5)
Risk-adjusted EV = EV - (detection_risk * profit)
```

---

### `/vrs-causal-trace`

**Purpose:** Build and validate causal exploitation chains.

**Inputs:**
- Root cause (vulnerability)
- Target outcome (financial loss)
- Graph context

**Outputs:**
```yaml
causal_chain:
  - step_type: root_cause
    description: "Oracle price not validated for staleness"
    node_id: "func_Vault_liquidate_abc123"
    evidence_refs: ["EVD-12345678"]
    probability: 1.0

  - step_type: exploit
    description: "Attacker front-runs oracle with stale price"
    probability: 0.8

  - step_type: amplifier
    description: "Flash loan magnifies extractable value"
    probability: 0.95

  - step_type: loss
    description: "$500,000 extracted from vault"
    probability: 1.0

chain_probability: 0.76  # Product of all steps
is_valid: true
missing_elements: []
```

**Chain Requirements:**
- Must have at least one `root_cause`, `exploit`, and `loss`
- Chain probability must be >= 0.1
- Each step should have evidence refs

---

### `/vrs-counterfactual`

**Purpose:** Explore "what if" mitigation scenarios.

**Inputs:**
- Causal chain
- Potential mitigations to evaluate

**Outputs:**
```yaml
counterfactuals:
  - scenario_type: guard_exists
    description: "What if staleness check was present?"
    would_prevent: true
    impact: "Attack blocked at oracle read - price rejected"
    evidence_refs: ["EVD-..."]
    confidence: high

  - scenario_type: param_different
    description: "What if heartbeat timeout was 10 minutes?"
    would_prevent: false
    impact: "Window reduced but MEV bots could still exploit"
    confidence: medium

  - scenario_type: timing_change
    description: "What if 2-block delay on liquidations?"
    would_prevent: true
    impact: "Front-running window eliminated"
    confidence: high

recommendation: "Add staleness check (cheapest, most effective)"
```

**Scenario Types:**
- `guard_exists` - Protective guard is present
- `param_different` - Configuration is different
- `role_change` - Permission is different
- `timing_change` - Delay is different
- `invariant_enforced` - Invariant is checked

---

### `/vrs-cascade-risk`

**Purpose:** Analyze cross-protocol cascade failures and systemic risk.

**Model:** Opus 4.5 (complex multi-protocol reasoning)

**Inputs:**
- Protocol dossier with cross-protocol dependencies
- Contract passports

**Outputs:**
```yaml
cascade_analysis:
  protocol: "Lending Protocol X"
  dependencies:
    - protocol: "Chainlink ETH/USD"
      failure_mode: "Stale prices for > 1 hour"
      cascade_impact:
        immediate: "Incorrect liquidations"
        secondary: "Bad debt accumulation"
        systemic: "Insolvency if > $10M"
      criticality: 9

    - protocol: "Uniswap V3"
      failure_mode: "Liquidity drain via exploit"
      cascade_impact:
        immediate: "Flash loan source unavailable"
        secondary: "Arbitrage mechanisms break"
      criticality: 5

  systemic_risk_score: 8.1
  high_risk_paths:
    - ["Chainlink failure", "Bad liquidation", "Protocol insolvency"]
  recommendations:
    - "Add circuit breaker on price deviation"
    - "Diversify oracle sources"
```

---

### `/vrs-loss-amplify`

**Purpose:** Compute loss amplification from causal edges.

**Inputs:**
- Causal chain with probability edges
- TVL at risk
- Amplification factors (flash loans, MEV)

**Outputs:**
```yaml
loss_amplification:
  base_loss_usd: 100_000
  amplification_factors:
    - factor: flash_loan
      multiplier: 10
      probability: 0.9
    - factor: mev_extraction
      multiplier: 1.5
      probability: 0.7
  total_amplified_loss: 1_350_000
  confidence: medium
  causal_path: ["oracle_manipulation", "flash_loan", "liquidation_drain"]
```

---

## Utility Skills

### `/vrs-econ-probes`

**Purpose:** Run lightweight economic probes and record evidence.

**Model:** Haiku 4.5 (fast, parallel execution)

**Probes:**
- **Profitability check:** Is there a clear payoff?
- **Control-path check:** Can attacker reach necessary control?
- **Assumption break check:** What if off-chain assumption fails?
- **Governance capture check:** Can upgrades enable abuse?
- **Value-at-risk check:** Max extractable in one path?

---

### `/vrs-misconfig-radar`

**Purpose:** Scan for known misconfiguration patterns.

**Model:** Haiku 4.5 (pattern matching)

**Patterns Detected:**
- Shadow admin via module/proxy
- Zero-timelock drift
- Role leakage to non-emergency actors
- Keeper drift to governance
- Oracle switch without assumption update
- Permit bypass of main checks
- Dual custody conflicts

---

### `/vrs-context-refresh`

**Purpose:** Detect context drift and expire stale facts.

**Model:** Haiku 4.5 (diff computation)

**Checks:**
- Compare dossier dates against current
- Flag facts older than TTL
- Mark stale facts as "unknown"
- Trigger refresh for critical stale items

---

## Integration with Prompt Contracts

These skills produce outputs that feed into EconomicPromptContract:

```python
from alphaswarm_sol.agents.prompts import EconomicPromptContract

# After running skills, build contract:
contract = EconomicPromptContract.for_attacker(
    dossier_summary=dossier.summary(),  # From /vrs-protocol-dossier
    passport_snippet=passport.to_snippet(),  # From /vrs-passport
    policy_diff=diff.to_string(),  # From /vrs-policy-diff
    attack_ev=attack_ev,  # From /vrs-attack-ev
    cross_protocol_deps=cascade.dependencies,  # From /vrs-cascade-risk
)

prompt = contract.build()
```

---

## Execution Examples

### Build Full Economic Context

```bash
# 1. Build dossier
/vrs-protocol-dossier aave-v3 --docs https://docs.aave.com

# 2. Generate passports for key contracts
/vrs-passport Pool.sol --dossier .vrs/dossiers/aave-v3.yaml

# 3. Compare policy
/vrs-policy-diff Pool.sol

# 4. Analyze attack scenario
/vrs-attack-ev "Oracle manipulation on liquidate()" --tvl 50000000

# 5. Trace causal chain
/vrs-causal-trace --root "stale oracle" --target "bad liquidation"

# 6. Explore mitigations
/vrs-counterfactual --chain .vrs/chains/oracle-liquidation.yaml
```

### Systemic Risk Analysis

```bash
# Analyze cascade failures
/vrs-cascade-risk aave-v3 --depth 2

# Compute loss amplification
/vrs-loss-amplify --chain oracle-attack --tvl 50000000
```

---

## Output Locations

| Skill | Output Location |
|-------|-----------------|
| protocol-dossier | `.vrs/dossiers/{protocol}.yaml` |
| passport | `.vrs/passports/{contract}.yaml` |
| policy-diff | `.vrs/diffs/{contract}.yaml` |
| attack-ev | `.vrs/economics/{scenario}.yaml` |
| causal-trace | `.vrs/chains/{chain-id}.yaml` |
| counterfactual | `.vrs/counterfactuals/{finding-id}.yaml` |
| cascade-risk | `.vrs/cascade/{protocol}.yaml` |

---

## Key Rules

1. **Always cite sources** - Every fact needs source_id and source_date
2. **Validate chains** - Causal chains must have root_cause -> exploit -> loss
3. **Explore both outcomes** - Counterfactuals should show what prevents AND what doesn't
4. **Track staleness** - Facts expire; mark stale as unknown
5. **Note dependencies** - Cross-protocol deps increase systemic risk
6. **Use appropriate models** - Haiku for probes, Sonnet for analysis, Opus for cascade

---

## Related Documentation

- [Economic Agent Contracts](docs/reference/economic-agent-contracts.md)
- [Economic Context Overlay](docs/reference/economic-context-overlay.md)
- [Contract Passport](docs/reference/contract-passport.md)

---

*VRS Economic Context Skills - Part of AlphaSwarm.sol Phase 5.11*
*Created: 2026-01-27*
