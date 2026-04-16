# Economic Model Library

**Status:** CANONICAL
**Purpose:** Curated economic behavior models across protocol types for vulnerability reasoning.
**Required By:** Plan 12 (Economic Behavior Modeling)
**References:** `ECONOMIC-MODEL-TEMPLATE.md`, `.planning/testing/rules/canonical/ORCHESTRATION-MARKERS.md`

---

## Overview

This library provides pre-built economic models for common DeFi protocol types. Each model captures actors, incentives, value flows, and attack economics specific to that protocol category. Use these models as starting points for vulnerability reasoning.

**Usage:** Reference `model_id` in `SCENARIO-MANIFEST.yaml` under `behavior_model_ref`.

---

## Model Index

| model_id | protocol_type | scenario_ref | actors | key_vulnerability | summary |
|----------|---------------|--------------|--------|-------------------|---------|
| econ-lend-001 | lending | side-entrance | depositors, borrowers, liquidators | Accounting manipulation | Flash-loan repayment check exploit with depositor loss |
| econ-lend-002 | lending | compound-fork | depositors, borrowers, liquidators | Oracle manipulation | Interest rate manipulation via price oracle |
| econ-dex-001 | dex | twap-manipulation | LPs, traders, arbitrageurs | Price oracle manipulation | TWAP manipulation affecting downstream consumers |
| econ-dex-002 | dex | sandwich-attack | traders, MEV searchers | Front-running | Sandwich attack extracting value from swaps |
| econ-stake-001 | staking | reward-snapshot | stakers, protocol treasury | Timing manipulation | Reward snapshot timing exploitation |
| econ-stake-002 | staking | liquid-staking | stakers, validators, LST holders | Exchange rate manipulation | LST exchange rate manipulation |
| econ-flash-001 | flash-loan | flash-loan-drain | flash loan lender, attacker | Callback exploitation | Flash-loan funded drain with repayment check gap |
| econ-oracle-001 | oracle | spot-price | oracle consumers, attackers | Price manipulation | Spot price manipulation via flash loans |

---

## Protocol Type: Lending

### econ-lend-001: Flash Loan Accounting Manipulation (SideEntranceLenderPool)

**Protocol Type:** lending
**Scenario Ref:** side-entrance
**Contract Reference:** `tests/fixtures/dvd/side-entrance/src/SideEntranceLenderPool.sol`

#### Actors

| Actor | Role | Incentives | Resources |
|-------|------|------------|-----------|
| Depositors | Provide liquidity | Earn yield (if any), safe storage | ETH deposits |
| Flash Loan Borrower | Borrow without collateral | Arbitrage, liquidation, exploit | Transaction execution, gas |
| Attacker | Malicious borrower | Drain pool balance | Flash loan capability |

#### Value Flows

```
Normal Operation:
  deposit()  : User ETH -> Pool Balance + User Credit (balances[msg.sender])
  withdraw() : User Credit -> User ETH
  flashLoan(): Pool ETH -> Borrower (temporary) -> Repayment Check -> Pool ETH

Attack Flow:
  flashLoan(pool.balance)
    -> execute() callback
    -> deposit() during callback (credits attacker balance)
    -> repayment check passes (pool balance unchanged)
    -> withdraw() credited balance
    -> PROFIT: entire pool balance
```

#### Attack Economics

```yaml
exploit_path: "flashLoan -> execute -> deposit -> repay check -> withdraw"
profit_calculation:
  formula: "profit = pool_balance - gas_costs"
  variables:
    - name: pool_balance
      value: "1000 ETH (example)"
      source: "pool.balance at exploit time"
    - name: gas_costs
      value: "~0.01 ETH"
      source: "transaction gas (flashLoan + deposit + withdraw)"
  estimated_profit: "999.99 ETH"

costs:
  gas_costs: "~50,000 gas (~0.01 ETH at 200 gwei)"
  setup_costs: "Deploy attacker contract (~200,000 gas)"
  opportunity_costs: "Minimal (single transaction)"

risks:
  mev_competition: "HIGH - profitable, likely to be sandwiched or front-run"
  detection_risk: "LOW - single transaction, no on-chain signals before"
  execution_risk: "LOW - deterministic if pool balance exists"

break_even: "pool_balance > 0.02 ETH"
incentive_compatibility: "YES - rational attacker will execute if pool_balance > gas_costs"

sensitivity:
  key_variables:
    - "pool_balance (directly determines profit)"
    - "gas price (affects break-even)"
  impact_on_profit: "Linear with pool balance"
```

#### Failure Conditions

| Loss Scenario | Impacted Parties | Impact Estimate |
|---------------|------------------|-----------------|
| Full pool drain | All depositors | 100% of deposits |
| Partial drain | All depositors | Pro-rata loss |

#### Evidence Requirements

```yaml
evidence_node_ids:
  - "flashLoan function node"
  - "execute callback node"
  - "deposit function node"
  - "balances mapping write node"
  - "repayment check node"
code_locations:
  - "SideEntranceLenderPool.sol:flashLoan"
  - "SideEntranceLenderPool.sol:execute"
  - "SideEntranceLenderPool.sol:deposit"
```

---

### econ-lend-002: Oracle-Based Interest Rate Manipulation (Compound-Fork)

**Protocol Type:** lending
**Scenario Ref:** compound-fork
**Contract Reference:** (generic Compound fork pattern)

#### Actors

| Actor | Role | Incentives | Resources |
|-------|------|------------|-----------|
| Depositors | Supply assets | Earn interest | Collateral assets |
| Borrowers | Borrow against collateral | Leverage, liquidity | Collateral |
| Liquidators | Liquidate unhealthy positions | Liquidation bonus | Capital, bots |
| Attacker | Manipulate oracle | Arbitrage liquidations | Flash loans, oracle control |

#### Value Flows

```
Normal Operation:
  supply()   : User Asset -> Protocol + cToken mint
  borrow()   : Protocol Asset -> User (tracked as debt)
  repay()    : User Asset -> Protocol (reduces debt)
  liquidate(): Liquidator repays debt -> receives collateral + bonus

Attack Flow (Oracle Manipulation):
  1. Flash loan large amount of target asset
  2. Manipulate oracle price (e.g., swap to skew spot price)
  3. Trigger liquidations at manipulated price
  4. Receive liquidation bonus at artificial prices
  5. Repay flash loan
  6. PROFIT: liquidation bonus - slippage - gas
```

#### Attack Economics

```yaml
profit_calculation:
  formula: "profit = liquidation_bonus - slippage - gas_costs - flash_loan_fees"
  estimated_profit: "Variable based on liquidatable positions"

costs:
  gas_costs: "~500,000 gas (complex multi-step)"
  flash_loan_fees: "0.09% (Aave) or 0% (dYdX)"
  slippage: "Depends on liquidity depth"

risks:
  mev_competition: "VERY HIGH - liquidation bots compete"
  detection_risk: "MEDIUM - unusual trading patterns"
  execution_risk: "MEDIUM - requires precise timing"
```

---

## Protocol Type: DEX (Decentralized Exchange)

### econ-dex-001: TWAP Oracle Manipulation

**Protocol Type:** dex
**Scenario Ref:** twap-manipulation
**Contract Reference:** (Uniswap V2/V3 TWAP pattern)

#### Actors

| Actor | Role | Incentives | Resources |
|-------|------|------------|-----------|
| Liquidity Providers | Provide liquidity | Trading fees | Token pairs |
| Traders | Execute swaps | Best execution price | Tokens |
| Arbitrageurs | Correct price deviations | Arbitrage profit | Capital, bots |
| Attacker | Manipulate TWAP | Exploit downstream protocols | Flash loans |

#### Value Flows

```
Normal Operation:
  addLiquidity() : Tokens -> LP shares
  swap()         : Token A -> Token B (price impact)
  TWAP update    : Cumulative price update per block

Attack Flow:
  1. Identify downstream protocol using TWAP oracle
  2. Accumulate position to manipulate over time window
  3. Execute large swap to skew TWAP
  4. Exploit downstream protocol at manipulated price
  5. Unwind position
  6. PROFIT: downstream extraction - slippage
```

#### Attack Economics

```yaml
profit_calculation:
  formula: "profit = downstream_extraction - (slippage + holding_cost + gas)"
  variables:
    - name: downstream_extraction
      value: "Depends on downstream protocol TVL"
    - name: slippage
      value: "Depends on AMM liquidity"

costs:
  gas_costs: "~200,000-500,000 gas per manipulation tx"
  slippage: "Proportional to swap size / liquidity"
  holding_cost: "Capital lockup during TWAP window"

risks:
  mev_competition: "HIGH - arbitrageurs will correct"
  detection_risk: "MEDIUM - unusual volume patterns"
  execution_risk: "HIGH - timing sensitive"
```

---

### econ-dex-002: Sandwich Attack

**Protocol Type:** dex
**Scenario Ref:** sandwich-attack

#### Actors

| Actor | Role | Incentives | Resources |
|-------|------|------------|-----------|
| Victim Trader | Execute swap | Best price | Tokens |
| MEV Searcher | Extract value | Sandwich profit | Flashbots access, capital |

#### Value Flows

```
Attack Flow:
  1. Observe pending victim swap in mempool
  2. Front-run: Buy target token (raises price)
  3. Victim swap executes at worse price
  4. Back-run: Sell target token (at inflated price)
  5. PROFIT: price difference - gas
```

#### Attack Economics

```yaml
profit_calculation:
  formula: "profit = (back_run_price - front_run_price) * amount - gas_costs - bribe"
  estimated_profit: "0.1-5% of victim swap value"

costs:
  gas_costs: "~150,000 gas x 2 transactions"
  bribe: "Flashbots block builder payment"

risks:
  mev_competition: "EXTREME - many searchers compete"
  execution_risk: "MEDIUM - requires mempool access and speed"
```

---

## Protocol Type: Staking

### econ-stake-001: Reward Snapshot Timing Manipulation

**Protocol Type:** staking
**Scenario Ref:** reward-snapshot

#### Actors

| Actor | Role | Incentives | Resources |
|-------|------|------------|-----------|
| Stakers | Lock tokens | Earn rewards | Staking tokens |
| Protocol Treasury | Distribute rewards | User retention | Reward tokens |
| Attacker | Manipulate timing | Inflated rewards | Capital, timing control |

#### Value Flows

```
Normal Operation:
  stake()     : User tokens -> Staking contract
  snapshot()  : Record eligible balances
  distribute(): Rewards proportional to snapshot balances

Attack Flow:
  1. Monitor for upcoming snapshot
  2. Stake large amount just before snapshot
  3. Snapshot captures inflated balance
  4. Receive disproportionate rewards
  5. Unstake (if no lockup) or wait for lockup
  6. PROFIT: inflated rewards - lockup opportunity cost
```

#### Attack Economics

```yaml
profit_calculation:
  formula: "profit = (inflated_share - fair_share) * total_rewards - lockup_cost"

costs:
  gas_costs: "~100,000 gas (stake + unstake)"
  lockup_cost: "Opportunity cost of locked capital"

risks:
  execution_risk: "LOW - deterministic if timing known"
  detection_risk: "MEDIUM - suspicious timing pattern"
```

---

### econ-stake-002: Liquid Staking Exchange Rate Manipulation

**Protocol Type:** staking
**Scenario Ref:** liquid-staking

#### Actors

| Actor | Role | Incentives | Resources |
|-------|------|------------|-----------|
| LST Holders | Hold liquid staking tokens | Staking yield without lockup | ETH |
| Validators | Validate network | Staking rewards | Validator infrastructure |
| Attacker | Manipulate exchange rate | Arbitrage LST/ETH | Flash loans |

#### Value Flows

```
Normal Operation:
  deposit()  : ETH -> LST (at exchange rate)
  withdraw() : LST -> ETH (at exchange rate)
  rebase()   : Update exchange rate based on rewards

Attack Flow (First Depositor / Inflation Attack):
  1. Be first depositor or exploit rounding
  2. Donate ETH to inflate exchange rate
  3. Subsequent depositors receive fewer LST
  4. Withdraw at inflated rate
  5. PROFIT: exchange rate arbitrage
```

---

## Protocol Type: Flash Loan

### econ-flash-001: Flash Loan Drain (Generic Pattern)

**Protocol Type:** flash-loan
**Scenario Ref:** flash-loan-drain

#### Actors

| Actor | Role | Incentives | Resources |
|-------|------|------------|-----------|
| Flash Loan Lender | Provide instant liquidity | Fees | Pool capital |
| Honest Borrower | Use for arbitrage/liquidation | Profit > fees | Strategy |
| Attacker | Exploit vulnerable protocols | Drain funds | Flash loan access |

#### Value Flows

```
Normal Operation:
  flashLoan() : Pool -> Borrower -> Action -> Repay + Fee -> Pool

Attack Flow:
  1. Flash loan large amount
  2. Use borrowed funds to exploit vulnerable protocol
  3. Extract value from vulnerable protocol
  4. Repay flash loan + fee
  5. PROFIT: extracted value - fees - gas
```

#### Attack Economics

```yaml
profit_calculation:
  formula: "profit = extracted_value - flash_loan_fee - gas_costs"

costs:
  flash_loan_fees: "0-0.09% depending on provider"
  gas_costs: "Variable based on complexity"

risks:
  mev_competition: "HIGH for known vulnerabilities"
  execution_risk: "LOW - atomic transaction"
```

---

## Protocol Type: Oracle

### econ-oracle-001: Spot Price Manipulation

**Protocol Type:** oracle
**Scenario Ref:** spot-price

#### Actors

| Actor | Role | Incentives | Resources |
|-------|------|------------|-----------|
| Oracle Consumer | Read price data | Accurate pricing | Oracle integration |
| Attacker | Manipulate spot price | Exploit consumers | Flash loans |

#### Value Flows

```
Attack Flow:
  1. Flash loan large amount
  2. Execute swap to manipulate spot price
  3. Trigger oracle consumer at manipulated price
  4. Extract value from consumer (liquidation, unfair swap, etc.)
  5. Reverse swap
  6. Repay flash loan
  7. PROFIT: consumer extraction - slippage - fees
```

#### Attack Economics

```yaml
profit_calculation:
  formula: "profit = consumer_extraction - 2*slippage - flash_loan_fee - gas"

risks:
  execution_risk: "LOW - atomic"
  detection_risk: "HIGH - obvious price spike"
```

---

## Usage Guidelines

### When to Use Economic Models

1. **Tier B/C Vulnerabilities**: Economic context required for economic exploitation chains
2. **Severity Assessment**: Justify severity with concrete profit/loss calculations
3. **False Positive Filtering**: Use economic viability to filter out impractical attacks
4. **Report Quality**: Provide actionable impact estimates

### Behavior Model Requirements for Scenarios

```yaml
# In SCENARIO-MANIFEST.yaml
behavior_model_ref: "econ-lend-001"  # REQUIRED for Tier B/C economic scenarios
incentive_analysis_required: true    # Must include profit calculation
profit_calculation_required: true    # Attack must have concrete numbers
```

### Creating New Models

Use `ECONOMIC-MODEL-TEMPLATE.md` for full per-scenario detail. Minimum requirements:
- Identify all actors and their incentives
- Map value flows for normal and attack scenarios
- Calculate profit with concrete formulas
- Assess costs and risks
- Provide evidence traceability

---

## Completion Checklist for Using Models

- [ ] Selected appropriate model for protocol type
- [ ] Adapted model values to specific contract
- [ ] Calculated concrete profit numbers (not just "attacker profits")
- [ ] Documented all assumptions
- [ ] Linked evidence to graph nodes and code locations
- [ ] Verified incentive compatibility (is attack rational?)

---

**Library Version:** 2.0
**Last Updated:** 2026-02-04
**Models Count:** 8 (covers 4 protocol types with 2 models each)
