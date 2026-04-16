# Economic Risk Scoring Reference

**Version:** 1.0
**Phase:** 05.11-04
**Status:** Implemented

## Overview

Economic risk scoring provides a prioritization signal (0-10) for vulnerability findings based on real-world exploitability and economic impact. The score combines three major components:

1. **Base Risk**: Traditional risk factors (VAR, PRIV, OFFCHAIN, GOV, INCENTIVE)
2. **Game-Theoretic Adjustment**: Attack expected value multiplier
3. **Causal Amplification**: Loss amplification from exploitation chains
4. **Systemic Risk**: Cross-protocol cascade risk

**Important**: Economic risk affects prioritization and verification depth only. It does NOT affect correctness or confidence of findings.

## Score Interpretation

| Score | Priority | Verification Depth |
|-------|----------|-------------------|
| 8-10 | Critical | Full multi-agent verification |
| 6-8 | High | Enhanced verification with debate |
| 4-6 | Medium | Standard verification |
| 2-4 | Low | Lightweight verification |
| 0-2 | Minimal | Basic pattern check only |

## Component 1: Base Risk (0-10)

The base risk score is the sum of five sub-components:

### 1.1 Value at Risk (VAR) - 0 to 4 points

Scaled by TVL or asset exposure:

| TVL Threshold | Score |
|--------------|-------|
| >= $100M | 4.0 |
| >= $10M | 3.0 |
| >= $1M | 2.0 |
| >= $100K | 1.0 |
| < $100K | 0.5 |

### 1.2 Privilege Concentration (PRIV) - 0 to 2 points

Risk from concentrated administrative control:

```
PRIV = min(2.0, privilege_concentration * 2.0)
```

Where `privilege_concentration` (0-1) considers:
- Single-role admin vs multisig
- Separation of concerns
- Timelock presence
- Emergency powers concentration

### 1.3 Off-chain Reliance (OFFCHAIN) - 0 to 2 points

Risk from external dependencies:

```
OFFCHAIN = min(2.0, offchain_reliance * 2.0)
```

Where `offchain_reliance` (0-1) considers:
- Oracle dependencies
- Relayer dependencies
- External committee reliance
- Keeper dependencies

### 1.4 Governance Mutability (GOV) - 0 to 1 point

Risk from governance attack surface:

```
GOV = min(1.0, governance_mutability)
```

Where `governance_mutability` (0-1) considers:
- Upgradeability
- Timelock presence/absence
- Parameter bounds
- Governance capture potential

### 1.5 Incentive Misalignment (INCENTIVE) - 0 to 1 point

Risk from economic incentive misalignment:

```
INCENTIVE = min(1.0, incentive_misalignment)
```

Where `incentive_misalignment` (0-1) considers:
- Profitable exploit vs cost
- Keeper/MEV incentives
- Protocol revenue extraction

### Base Score Calculation

```
base_score = VAR + PRIV + OFFCHAIN + GOV + INCENTIVE
base_score = min(10.0, base_score)  # Cap at 10
```

## Component 2: Game-Theoretic Adjustment (1.0-2.0x)

The game-theoretic adjustment uses the `PayoffMatrix` to determine if an attack is economically rational and how profitable it would be.

### Attack Expected Value Calculation

```
EV = P(success) * profit - gas_cost - P(MEV) * profit * MEV_share
```

### EV to Multiplier Mapping

| Attack EV (ETH equivalent) | Multiplier |
|---------------------------|------------|
| >= 100 ETH | 2.0x |
| >= 10 ETH | 1.5x |
| > 0 ETH | 1.0x (no adjustment) |
| <= 0 ETH | 1.0x (not profitable) |

**Rationale**: If an attack is economically rational with high expected value, it's more likely to be attempted by sophisticated attackers with resources.

## Component 3: Causal Loss Amplification (1.0-3.0x cap)

The causal amplification factor analyzes AMPLIFIES edges in the exploitation chain to determine how initial losses can be magnified through DeFi mechanics.

### Amplification Types and Multipliers

| Type | Default Multiplier | Description |
|------|-------------------|-------------|
| FLASH_LOAN | 100x | Capital-free attack |
| LEVERAGE | 10x | Borrowed funds multiply exposure |
| CASCADING_LIQUIDATION | 5x | Liquidation triggers more liquidations |
| ORACLE_MANIPULATION | 20x | Price manipulation affects multiple protocols |
| GOVERNANCE_CAPTURE | 50x | Control over protocol parameters |
| TOKEN_MINT | 1000x | Unbounded token minting |
| REENTRANCY | 10x | Multiple extraction in single tx |
| POOL_DRAIN | 1x | Complete pool extraction |
| BRIDGE_EXPLOIT | 100x | Cross-chain loss multiplication |
| MEV_SANDWICH | 2x | MEV extraction from victims |

### Amplification Combination

Multipliers are combined using a capped additive formula to avoid score explosion:

```
total_multiplier = max_multiplier + sum((other_multipliers - 1.0) * 0.1)
amplification_factor = min(3.0, total_multiplier)  # Cap at 3x
```

### LossAmplificationFactor Output

```python
LossAmplificationFactor:
    base_loss: float          # Initial loss before amplification
    amplified_loss: float     # Loss after amplification
    amplification_multiplier: float  # Combined multiplier
    amplification_sources: List[AmplificationSource]
    confidence: float         # Based on chain probability
```

## Component 4: Systemic Risk Factor (1.0-1.5x)

The systemic risk factor uses cross-protocol dependencies from contract passports to assess cascade risk.

### Systemic Risk Score Components

1. **Dependency Centrality** (0-3 points)
   - Degree: Number of direct dependencies
   - Betweenness: How often protocol is on shortest paths

2. **Cascade TVL Risk** (0-3 points)
   | Affected TVL | Score |
   |--------------|-------|
   | >= $1B | 3.0 |
   | >= $100M | 2.0 |
   | >= $10M | 1.0 |
   | < $10M | 0.5 |

3. **Oracle Dependency** (0-3 points)
   - Based on number and criticality of oracle dependencies

4. **Bridge Dependency** (0-2 points)
   - Based on cross-chain bridge dependencies

5. **Governance Concentration** (0-2 points)
   - Based on single admin control over critical functions

### Systemic to Multiplier Conversion

```
systemic_factor = 1.0 + (systemic_score / 10.0) * 0.5
```

This maps a 0-10 systemic score to a 1.0-1.5x multiplier.

## Total Score Calculation

The final score combines base risk with multiplier adjustments:

```python
# Multipliers are applied additively to avoid score explosion
adjustment = (
    (attack_ev_score - 1.0) * 0.3
    + (loss_amplification - 1.0) * 0.4
    + (systemic_factor - 1.0) * 0.3
)

total_score = base_score * (1.0 + adjustment)
total_score = min(10.0, total_score)  # Cap at 10
```

### Weighting Rationale

- **Causal amplification (0.4)**: Most direct impact on loss magnitude
- **Game-theoretic EV (0.3)**: Strong indicator of attack likelihood
- **Systemic risk (0.3)**: Important for ecosystem-wide impact

## Risk Breakdown Output

```python
RiskBreakdown:
    total_score: float
    base_score: float
    value_at_risk_score: float
    privilege_concentration_score: float
    offchain_reliance_score: float
    governance_mutability_score: float
    incentive_misalignment_score: float
    attack_ev_score: float
    loss_amplification_factor: float
    systemic_risk_factor: float
    priority: RiskPriority
    evidence_refs: List[str]
    notes: List[str]
```

## Example Calculations

### Example 1: High-Value DeFi Vulnerability

**Inputs:**
- TVL: $50M (VAR = 3.0)
- Single admin, no timelock (PRIV = 1.8)
- Oracle dependency (OFFCHAIN = 1.5)
- Upgradeable, short timelock (GOV = 0.8)
- Profitable exploit (INCENTIVE = 0.7)
- Attack EV: 50 ETH (multiplier = 1.5x)
- Flash loan amplification (capped at 3.0x)
- Systemic score: 6/10 (factor = 1.3x)

**Calculation:**
```
base_score = 3.0 + 1.8 + 1.5 + 0.8 + 0.7 = 7.8
adjustment = (1.5 - 1.0) * 0.3 + (3.0 - 1.0) * 0.4 + (1.3 - 1.0) * 0.3
           = 0.15 + 0.8 + 0.09 = 1.04
total_score = 7.8 * (1.0 + 1.04) = 7.8 * 2.04 = 15.9 -> capped at 10.0
```

**Result:** Critical priority (10.0/10)

### Example 2: Low-Value Isolated Vulnerability

**Inputs:**
- TVL: $50K (VAR = 0.5)
- Multisig admin (PRIV = 0.2)
- No oracle (OFFCHAIN = 0.0)
- Not upgradeable (GOV = 0.0)
- Minimal profit (INCENTIVE = 0.1)
- Attack EV: -$1000 (multiplier = 1.0x)
- No amplification (factor = 1.0x)
- Systemic score: 1/10 (factor = 1.05x)

**Calculation:**
```
base_score = 0.5 + 0.2 + 0.0 + 0.0 + 0.1 = 0.8
adjustment = (1.0 - 1.0) * 0.3 + (1.0 - 1.0) * 0.4 + (1.05 - 1.0) * 0.3
           = 0 + 0 + 0.015 = 0.015
total_score = 0.8 * 1.015 = 0.81
```

**Result:** Minimal priority (0.81/10)

## Economic Probes

Economic probes pressure-test real-world exploitability. Probe failures produce unknowns or expansion requests, not false positives.

### Available Probes

| Probe | Purpose | Output |
|-------|---------|--------|
| profitability_probe | Is there clear payoff? | PASSED/FAILED/UNKNOWN |
| control_path_probe | Can attacker reach control? | PASSED/FAILED/UNKNOWN |
| assumption_break_probe | What if assumption fails? | PASSED/UNKNOWN |
| governance_capture_probe | Can governance enable abuse? | PASSED/FAILED/UNKNOWN |
| value_at_risk_probe | Max extractable value? | PASSED/UNKNOWN |
| counterfactual_probe | What if X guard existed? | PASSED/FAILED |
| cascade_probe | What protocols affected? | PASSED/FAILED |

### Probe Status Meanings

- **PASSED**: Probe confirms exploitability concern
- **FAILED**: Probe suggests not exploitable
- **UNKNOWN**: Insufficient data to determine
- **EXPANSION_REQUIRED**: Need more context

## Usage

```python
from alphaswarm_sol.economics import (
    EconomicRiskScorer,
    compute_economic_risk,
    CausalAnalyzer,
    SystemicRiskScorer,
)

# Create scorer with dependencies
scorer = EconomicRiskScorer(
    payoff_matrix=payoff_matrix,
    causal_analyzer=CausalAnalyzer(causal_edges=edges),
    systemic_scorer=SystemicRiskScorer(passports=passports),
)

# Compute risk breakdown
breakdown = scorer.compute_risk(
    value_at_risk_usd=10_000_000,
    privilege_concentration=0.5,
    offchain_reliance=0.7,
    governance_mutability=0.3,
    incentive_misalignment=0.6,
    causal_chain=chain,
    protocol_id="my-protocol",
)

print(f"Total risk: {breakdown.total_score:.1f}/10")
print(f"Priority: {breakdown.priority.value}")
print(f"Breakdown: {breakdown.to_dict()}")
```

## Integration Points

- **Orchestration output**: Risk metadata included in findings via `FindingRiskMetadata`
- **Beads**: Risk breakdown stored in bead metadata
- **Agent routing**: High-risk findings get more verification depth
- **Pool prioritization**: Beads sorted by economic risk for processing

## Constraints

1. **Risk is for prioritization only**: Never affects correctness or confidence
2. **Score capped at 10**: Prevents runaway scores from multipliers
3. **Amplification capped at 3x**: Prevents extreme loss estimates
4. **Evidence required**: Risk claims must have evidence_refs
5. **Unknown handling**: Missing data produces lower confidence, not assumptions

---

*Per 05.11-CONTEXT.md: Economic risk is a secondary priority signal that informs verification depth, not correctness.*
