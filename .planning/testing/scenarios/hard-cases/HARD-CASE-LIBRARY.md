# Hard-Case Library

## Scope
This library curates protocol hard cases for Tier B/C evaluation. Each case includes difficulty rationale, provenance, and the reasoning required to evaluate it. At least one case explicitly requires cross-contract reasoning.

## Field Guide
- Category: Protocol category tag.
- Difficulty: High or Extreme.
- Difficulty justification: Why this is hard (specific challenge).
- Provenance: Source type and reference (audit report, exploit analysis, bug bounty).
- Required reasoning: Cross-function, economic, temporal, cross-contract.
- Expected challenge: What the system should struggle with.
- Attack vector: Short description of the vulnerability.

## Lending

### LND-01: Flash-Loan Price Manipulation (bZx 2020)
- Category: Lending
- Difficulty: High
- Difficulty justification: Multi-hop price manipulation, collateral valuation, and liquidation interactions across protocols.
- Provenance: Exploit postmortem - bZx 2020 (https://bzx.network/blog/)
- Required reasoning: Cross-contract, economic, temporal
- Expected challenge: Track price impact propagation and collateral ratios across contracts in a single transaction.
- Attack vector: Use a flash loan to manipulate a DEX price feed, inflate collateral value, and borrow against it.

### LND-02: Oracle Manipulation to Drain Collateral (Cream Finance 2021)
- Category: Lending
- Difficulty: Extreme
- Difficulty justification: Thin-liquidity oracle dependency with rapid price movements and re-entrancy risk.
- Provenance: Exploit analysis - Cream Finance 2021 (https://medium.com/cream-finance)
- Required reasoning: Cross-contract, economic
- Expected challenge: Detect oracle dependency across markets and quantify exploitable price windows.
- Attack vector: Manipulate a price oracle for a listed asset to borrow more than collateral supports.

## DEX

### DEX-01: TWAP Manipulation Affecting Downstream Protocols
- Category: DEX
- Difficulty: High
- Difficulty justification: Requires reasoning about TWAP windows, liquidity depth, and downstream oracle consumers.
- Provenance: Exploit analysis - Value DeFi 2020 (https://medium.com/valuedefi)
- Required reasoning: Cross-contract, temporal, economic
- Expected challenge: Show how short-lived TWAP manipulation impacts dependent lending or vault logic.
- Attack vector: Manipulate pool price over a short window to skew TWAP used by another protocol.

### DEX-02: Sandwich + Slippage Guard Bypass in Aggregators
- Category: DEX
- Difficulty: High
- Difficulty justification: MEV-driven ordering plus partial slippage checks produce non-obvious loss paths.
- Provenance: Internal scenario based on MEV research notes
- Required reasoning: Temporal, economic
- Expected challenge: Connect transaction ordering, slippage guards, and downstream value extraction.
- Attack vector: Sandwich trades force poor execution while bypassing weak slippage validation.

## Staking

### STK-01: Reward Snapshot Manipulation
- Category: Staking
- Difficulty: High
- Difficulty justification: Snapshot timing, delegated stake, and reward epochs create subtle exploitation windows.
- Provenance: Audit finding - staking reward timing issues (public contest reports)
- Required reasoning: Temporal, cross-function
- Expected challenge: Model reward epoch boundaries and detect timing-sensitive reward inflation.
- Attack vector: Stake/unstake around snapshot windows to inflate rewards without proportional lock time.

### STK-02: Liquid Staking Share Price Inflation
- Category: Staking
- Difficulty: Extreme
- Difficulty justification: Share price math, rounding, and delayed accounting across components.
- Provenance: Internal scenario based on liquid staking audits
- Required reasoning: Cross-contract, economic
- Expected challenge: Trace share price changes across token, staking, and accounting contracts.
- Attack vector: Manipulate share price through asymmetric deposits/withdrawals and rounding.

## Vault

### VLT-01: Share Price Manipulation (Harvest Finance 2020)
- Category: Vault
- Difficulty: Extreme
- Difficulty justification: Multi-tx price manipulation across Curve pools and vault share accounting.
- Provenance: Exploit postmortem - Harvest Finance 2020 (https://medium.com/harvest-finance)
- Required reasoning: Cross-contract, economic, temporal
- Expected challenge: Connect pool price manipulation to vault share valuation and withdrawal gains.
- Attack vector: Manipulate stablecoin pool prices to distort vault share price and withdraw profit.

### VLT-02: Reentrancy Across Vault + Strategy
- Category: Vault
- Difficulty: High
- Difficulty justification: Requires tracing state updates across vault, strategy, and token callbacks.
- Provenance: Audit finding - strategy/vault reentrancy patterns
- Required reasoning: Cross-contract, cross-function
- Expected challenge: Identify state update order bugs across contracts that look safe in isolation.
- Attack vector: Reenter via strategy callback to double-count shares or bypass accounting.

## Oracle

### ORC-01: Stale Price Window Exploit
- Category: Oracle
- Difficulty: High
- Difficulty justification: Stale/lagged oracle feeds combined with fast market moves.
- Provenance: Bug bounty reports on stale price oracle usage
- Required reasoning: Temporal, economic
- Expected challenge: Detect reliance on stale feeds and quantify exploitability during updates.
- Attack vector: Exploit stale price feed to mint or borrow assets at outdated prices.

### ORC-02: Price Manipulation to Inflate Collateral (Mango Markets 2022)
- Category: Oracle
- Difficulty: Extreme
- Difficulty justification: Large price swings engineered via thin liquidity and on-chain oracle reliance.
- Provenance: Exploit analysis - Mango Markets 2022 (https://mango.markets/blog)
- Required reasoning: Cross-contract, economic, temporal
- Expected challenge: Model how manipulated market prices impact collateral valuation and solvency.
- Attack vector: Manipulate oracle price to inflate collateral and withdraw unbacked assets.

## Governance

### GOV-01: Flash-Loan Governance Takeover (Beanstalk 2022)
- Category: Governance
- Difficulty: Extreme
- Difficulty justification: Multi-step governance actions executed within a flash-loan window.
- Provenance: Exploit postmortem - Beanstalk 2022 (https://bean.money/)
- Required reasoning: Temporal, cross-function, economic
- Expected challenge: Track governance proposal lifecycle inside a single block and detect value transfer.
- Attack vector: Borrow voting power via flash loan, pass malicious proposal, drain funds.

### GOV-02: Vote Weight Misaccounting in Delegation
- Category: Governance
- Difficulty: High
- Difficulty justification: Delegation chains and snapshots create non-obvious vote weight bugs.
- Provenance: Internal scenario based on governance audits
- Required reasoning: Cross-function, temporal
- Expected challenge: Reconcile vote weights across delegation changes and snapshots.
- Attack vector: Exploit delegation misaccounting to gain excess voting power.

## Bridge

### BRG-01: Message Verification Bypass (Wormhole 2022)
- Category: Bridge
- Difficulty: Extreme
- Difficulty justification: Signature verification and guardian set handling across contracts.
- Provenance: Exploit analysis - Wormhole 2022 (https://wormhole.com/blog)
- Required reasoning: Cross-contract, economic
- Expected challenge: Identify verification gaps across on-chain verification and guardian updates.
- Attack vector: Bypass message verification to mint assets on the destination chain.

### BRG-02: Cross-Chain Replay After Initialization Bug (Nomad 2022)
- Category: Bridge
- Difficulty: Extreme
- Difficulty justification: Initialization state shared across contracts allowed message replay.
- Provenance: Exploit analysis - Nomad 2022 (https://nomad.xyz/)
- Required reasoning: Cross-contract, temporal
- Expected challenge: Track initialization logic across contracts and detect replay conditions.
- Attack vector: Replay verified messages to withdraw funds repeatedly.
