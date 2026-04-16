# EigenLayer Restaking Vulnerabilities and Risks

## Overview

EigenLayer introduces **restaking** - reusing staked ETH to secure additional services called Actively Validated Services (AVSs). While increasing capital efficiency, restaking introduces novel risk vectors: amplified slashing, cascading failures, operator malicious behavior, and smart contract vulnerabilities. These risks are compounded because the same capital secures multiple services simultaneously.

## Core Vulnerability Pattern

**DISCOVER**: Restaking vulnerabilities stem from capital reuse, shared security assumptions, complex slashing logic, and coordination failures between Ethereum L1, EigenLayer contracts, and multiple AVSs.

**REASON**: The architecture creates:
- **Amplified Risk**: Same stake subject to multiple slashing conditions
- **Systemic Risk**: Failure in one AVS can cascade to others
- **Operator Risk**: Malicious or incompetent operators affect all delegators
- **Smart Contract Risk**: Bugs in EigenLayer core or AVS contracts
- **Liquidity Risk**: Additional lock-up periods beyond Ethereum's unbonding

## Known Incidents and Vulnerabilities

### EigenLayer $5.7M Email Phishing Attack (Oct 2024)
**Loss**: $5.7 million EIGEN tokens
**Root Cause**: Social engineering attack, NOT smart contract vulnerability
**Mechanism**:
- Attacker compromised email thread between investor, custodian, and EigenLabs
- Used lookalike emails to authorize token transfer to attacker address
- Tokens transferred before detection

**Note**: Protocol infrastructure (contracts, website) NOT compromised
**Detection**: Social engineering, not on-chain vulnerability

### Slashing Activation (April 17, 2025)
**Status**: Slashing went live on mainnet
**Impact**: Restakers now subject to actual fund loss for misbehavior
**Risk**: Before this date, slashing was theoretical; now it's real

**Implication**: All earlier restakers operated without actual slashing risk; post-April 2025 risk profile fundamentally changed

## Vulnerability Categories

### 1. Amplified Slashing Risk

#### Pattern: Correlated Slashing Across AVSs
**Mechanism**: Validator restakes on multiple AVSs. Single mistake triggers slashing on ALL services.

**Properties**:
- Operator participates in N AVSs
- Single misbehavior (missed attestation, double-sign) triggers N slashing events
- Loss compounds multiplicatively

**Real-World Scenario**:
```
Validator stakes 32 ETH on Ethereum L1
Restakes same 32 ETH on:
  - AVS A (slashing penalty: 10%)
  - AVS B (slashing penalty: 15%)
  - AVS C (slashing penalty: 5%)

Single double-sign event triggers:
  - ETH L1 slash: 1 ETH (3.125%)
  - AVS A slash: 3.2 ETH (10%)
  - AVS B slash: 4.8 ETH (15%)
  - AVS C slash: 1.6 ETH (5%)

Total loss: 10.6 ETH (33.125% of original stake)
```

**Detection Signals**:
- `MODIFIES_CRITICAL_STATE` affecting staking status
- Slashing logic triggered by external events
- Multiple AVS registrations per operator

#### Pattern: Operational Mistakes Amplified
**Mechanism**: Infrastructure errors (key management, client bugs, configuration) affect all AVSs simultaneously

**Common Triggers**:
1. **Key Reuse/Duplication**: Moving validator across machines causes double-signing
2. **Misconfiguration**: Anti-slashing database disabled or corrupted
3. **Client Bugs**: Software bugs cause invalid attestations
4. **Network Issues**: Downtime causes missed responsibilities

**Detection**: Monitor for:
- Validator key management practices
- Single client implementations (no diversity)
- Centralized infrastructure (single point of failure)

### 2. Systemic Risk and Cascading Failures

#### Pattern: Rehypothecation Cascade
**Mechanism**: Restaked assets used in lending loops or derivative stacks create systemic risk

**Flow**:
```
1. User stakes ETH → gets stETH (Lido)
2. Deposits stETH into EigenLayer → gets Liquid Restaking Token (LRT: eETH, ezETH)
3. Deposits LRT into lending protocol (Aave, Compound)
4. Borrows stablecoins against LRT
5. Uses stablecoins to buy more ETH
6. Repeats (leverage loop)
```

**Failure Cascade**:
```
AVS experiences bug → slashing triggered →
LRT value drops → liquidations triggered →
Lending protocol bad debt → LRT depeg →
More slashing as validators exit → death spiral
```

**Detection Signals**:
- `TRANSFERS_VALUE_OUT` creating derivative tokens
- LRT tokens used as collateral in lending protocols
- High leverage ratios (>5x)

#### Pattern: Contagious Slashing
**Mechanism**: Single AVS bug or exploit causes mass slashing, affecting Ethereum L1 security

**Scenario**:
```
Popular AVS has critical bug
Bug affects 40% of Ethereum validators (those restaking on AVS)
Mass slashing event reduces Ethereum security budget
Ethereum network stability threatened
```

**Detection**: Concentration metrics:
- % of total ETH staked in single AVS
- % of validators participating in same AVS
- TVL concentration in top 3 AVSs

### 3. Malicious AVS Risk

#### Pattern: AVS Rug Pull via Slashing Manipulation
**Mechanism**: Malicious AVS creators deploy with favorable conditions, then change rules to slash operators

**Properties**:
- AVS contract allows mutable slashing conditions
- No timelock on slashing parameter changes
- Centralized slashing trigger (not consensus-based)
- Operators locked in with withdrawal delays

**Attack Flow**:
```
1. Launch AVS with attractive yield (20% APY)
2. Attract operators to restake (accumulate TVL)
3. Change slashing conditions via unguarded function
4. Trigger mass slashing with false claims
5. Steal slashed funds
```

**Detection Signals**:
- `MODIFIES_CRITICAL_STATE` for slashing parameters without timelock
- Centralized admin control over slashing
- Mutable reward/punishment logic
- Recent AVS deployment (<6 months) without audits

#### Pattern: False Information Attack
**Mechanism**: AVS provides misleading risk parameters to attract operators, then actual risk materializes

**Example**:
- AVS claims "0.1% max slash"
- Contract actually allows "10% slash"
- Operators discover discrepancy after funds locked

**Detection**:
- Discrepancy between documentation and on-chain parameters
- Complex or obfuscated slashing logic
- Missing formal verification of slashing bounds

### 4. EigenLayer Core Contract Vulnerabilities

#### Pattern: Incomplete Slash Implementation
**Status**: As of Feb 5, 2024, slash functionality incomplete
**Risk**: Centralized execution by StrategyManager owner

**Properties**:
- `slash()` function only has interfaces, no complete logic
- Slashing triggered by single admin (StrategyManager owner)
- No decentralized consensus on slashing decisions
- Subject to admin key compromise

**Current State (as of data)**:
```solidity
// Pseudo-code of incomplete implementation
function slash(address operator, uint256 amount) external onlyOwner {
    // TODO: Implement slashing logic
    // Currently: centralized trigger
}
```

**Detection**:
- `has_access_gate` = true but single owner
- `MODIFIES_CRITICAL_STATE` (balance reduction) via admin function
- Missing multi-signature or DAO governance

#### Pattern: Delegate Function Risk
**Warning**: Users advised against enabling delegate function before full AVS/slash implementation
**Risk**: Potential fund loss if delegation enabled prematurely

**Detection**:
- Early delegations to operators before slashing complete
- Missing operator reputation systems
- No operator insurance or stake minimums

### 5. Operator Risk

#### Pattern: Malicious Operator Behavior
**Mechanism**: Operators can act maliciously or negligently, triggering slashing for all delegators

**Delegator Risk**:
```
User delegates 32 ETH to Operator X
Operator X participates in 5 AVSs
Operator X double-signs on AVS 3
All delegators to Operator X lose proportional stake
User loses 8 ETH (25%) due to Operator X's action
```

**Detection Signals**:
- Operator with no reputation or history
- Operator participates in >10 AVSs (over-extended)
- Operator has poor infrastructure (high downtime)
- No operator self-stake (no skin in the game)

#### Pattern: Operator Key Compromise
**Mechanism**: Insider threats or hackers compromise operator keys, cause intentional slashing

**Scenario**:
```
1. Attacker gains access to operator validator keys
2. Triggers slashing conditions across all AVSs
3. Steals slashed funds (if AVS design allows)
4. All delegators suffer losses
```

**Detection**:
- Centralized key storage (not HSM/MPC)
- No multi-party validation for critical operations
- Single administrator access to keys

### 6. Liquidity and Exit Risk

#### Pattern: Extended Lock-Up Periods
**Mechanism**: EigenLayer adds 7-day withdrawal delay ON TOP of Ethereum's unbonding period

**Total Exit Time**:
```
Ethereum unbonding: ~27 days (since Shapella)
EigenLayer additional delay: 7 days
Total: 34+ days to fully withdraw
```

**Risk**: During this period:
- User exposed to market volatility (ETH price)
- AVS slashing risk continues
- Cannot respond to emergencies

**Detection**:
- Withdrawal functions with `CHECKS_TIMESTAMP` enforcing delays
- Missing emergency exit mechanisms
- No partial withdrawal options

#### Pattern: LRT Depeg Risk
**Mechanism**: Liquid Restaking Tokens (eETH, ezETH) can depeg from underlying ETH value

**Causes**:
- Mass exit demand exceeds available liquidity
- Slashing event reduces backing
- Smart contract exploit in LRT protocol
- Loss of confidence in restaking model

**Impact**:
```
User holds 10 eETH (representing 10 ETH)
Slashing event occurs, eETH depegs to 0.85 ETH
User effectively lost 15% immediately
Cannot exit quickly due to lock-up
```

**Detection Signals**:
- `TRANSFERS_VALUE_OUT` creating LRT tokens
- LRT price < backing ETH price (depeg)
- High LRT redemption queue

### 7. Client Diversity and Single Points of Failure

#### Pattern: Lack of AVS Client Diversity
**Mechanism**: New AVSs often have single client implementation; critical bug affects all validators

**Scenario**:
```
AVS launches with one client implementation
Bug in client causes all validators to miss attestations
Mass slashing event
No client diversity means no fallback
```

**Detection**:
- AVS documentation mentions only one client
- No alternative implementations available
- Client code not open-source or audited

## Attack Scenarios

### Scenario 1: Malicious AVS Slashing Rug Pull
```
Day 1: Launch "SuperYield AVS" promising 30% APY
Day 30: Accumulate $100M in restaked ETH
Day 31: Admin calls updateSlashingConditions(100%) # Set to max
Day 32: Trigger fabricated slashing event
Day 33: Slash all operators, steal $100M
Day 34: Admin disappears, users discover funds gone after 7-day delay
```

**Prevention**:
- Immutable slashing conditions OR
- DAO governance with 30-day timelock OR
- Formal verification of slashing bounds

### Scenario 2: Cascading Liquidation via LRT Depeg
```
1. 40% of Ethereum validators restake on popular AVS
2. AVS has critical bug, triggers mass slashing
3. LRT tokens (eETH, ezETH) depeg 20%
4. Lending protocols see LRT collateral value drop
5. Mass liquidations triggered
6. LRT price drops further (40% depeg)
7. More validators exit, more slashing
8. Death spiral: Ethereum security budget reduced
```

**Prevention**:
- Limit AVS concentration (<10% of validators per AVS)
- Circuit breakers in LRT protocols
- Conservative collateral factors for LRT in lending

### Scenario 3: Insider Key Compromise
```
1. Disgruntled employee at operator company
2. Exports validator private keys
3. Spins up duplicate validator elsewhere
4. Causes double-signing across all AVSs
5. All delegators slashed (100+ ETH total loss)
6. Operator lacks insurance, delegators uncompensated
```

**Prevention**:
- MPC/HSM key management
- Operator insurance requirements
- Multi-party authorization for key operations

## Detection Criteria

### Critical Signals (Immediate Risk)
1. **Centralized slashing control**: Single admin can trigger slashing
2. **Mutable slashing conditions**: Parameters changeable without timelock
3. **Incomplete slash implementation**: Interfaces without logic
4. **Missing operator insurance**: No compensation mechanism for errors
5. **LRT used as collateral**: Liquid restaking tokens in lending protocols

### High Risk Signals
1. **High AVS concentration**: >30% of validators in single AVS
2. **Unaudited AVS contracts**: New AVS without security review
3. **Complex slashing logic**: Difficult to verify slashing bounds
4. **Single client implementation**: No fallback for bugs
5. **Operator over-extension**: Participates in >10 AVSs

### Medium Risk Signals
1. **Extended lock-ups**: >14 days total withdrawal time
2. **LRT depeg**: >5% difference from backing ETH
3. **Low operator self-stake**: <10% operator funds vs delegated
4. **Centralized operator infrastructure**: Single region/provider
5. **Missing reputation system**: No operator history/metrics

## Fixes and Mitigations

### Immutable or Governed Slashing Conditions
```solidity
// Option 1: Immutable (set at deployment)
contract ImmutableSlashAVS {
    uint256 public immutable MAX_SLASH_PERCENTAGE = 10; // 10%, cannot change

    function slash(address operator) external {
        require(calculateSlash() <= MAX_SLASH_PERCENTAGE, "Exceeds max");
        // Execute slash...
    }
}

// Option 2: DAO Governed with Timelock
contract GovernedSlashAVS {
    uint256 public maxSlashPercentage = 5;
    uint256 public pendingMaxSlash;
    uint256 public timelockExpiry;

    function proposeSlashChange(uint256 newMax) external onlyDAO {
        require(newMax <= 20, "Absolute max: 20%");
        pendingMaxSlash = newMax;
        timelockExpiry = block.timestamp + 30 days;
        emit SlashChangeProposed(newMax, timelockExpiry);
    }

    function executeSlashChange() external {
        require(block.timestamp >= timelockExpiry, "Timelock active");
        maxSlashPercentage = pendingMaxSlash;
    }
}
```

### Operator Insurance and Stake Requirements
```solidity
contract InsuredOperator {
    mapping(address => uint256) public operatorSelfStake;
    mapping(address => uint256) public operatorInsurance;

    uint256 public constant MIN_SELF_STAKE_PERCENTAGE = 10; // 10% of delegated

    function registerOperator() external payable {
        require(msg.value >= MIN_OPERATOR_STAKE, "Insufficient self-stake");
        operatorSelfStake[msg.sender] = msg.value;
    }

    function depositInsurance() external payable {
        operatorInsurance[msg.sender] += msg.value;
    }

    function slash(address operator, uint256 amount) internal {
        // Slash operator self-stake first
        uint256 fromSelfStake = min(operatorSelfStake[operator], amount);
        operatorSelfStake[operator] -= fromSelfStake;
        amount -= fromSelfStake;

        // Then insurance
        uint256 fromInsurance = min(operatorInsurance[operator], amount);
        operatorInsurance[operator] -= fromInsurance;
        amount -= fromInsurance;

        // Finally delegated stake (last resort)
        if (amount > 0) {
            slashDelegators(operator, amount);
        }
    }
}
```

### AVS Concentration Limits
```solidity
contract ConcentrationLimit {
    mapping(address => uint256) public avsStake;
    uint256 public totalStake;

    uint256 public constant MAX_AVS_CONCENTRATION = 30; // 30% max

    function restakeToAVS(address avs, uint256 amount) external {
        uint256 newAVSStake = avsStake[avs] + amount;
        uint256 newTotal = totalStake + amount;

        require(
            newAVSStake * 100 / newTotal <= MAX_AVS_CONCENTRATION,
            "Exceeds concentration limit"
        );

        avsStake[avs] = newAVSStake;
        totalStake = newTotal;
    }
}
```

### LRT Circuit Breakers
```solidity
contract CircuitBreakerLRT {
    uint256 public lastPriceUpdate;
    uint256 public currentPrice;
    uint256 public constant MAX_PRICE_DROP = 10; // 10% per update

    bool public circuitBreakerActive;

    function updatePrice(uint256 newPrice) external {
        uint256 priceChange = ((currentPrice - newPrice) * 100) / currentPrice;

        if (priceChange > MAX_PRICE_DROP) {
            circuitBreakerActive = true;
            emit CircuitBreakerTriggered(currentPrice, newPrice);
            return; // Don't update price, pause operations
        }

        currentPrice = newPrice;
        lastPriceUpdate = block.timestamp;
    }

    modifier whenNotPaused() {
        require(!circuitBreakerActive, "Circuit breaker active");
        _;
    }
}
```

## Security Best Practices

### For Restakers
1. **Diversify operators**: Don't delegate all to one operator
2. **Check operator reputation**: History, uptime, self-stake
3. **Understand total risk**: Sum slashing risk across all AVSs
4. **Avoid over-leveraging**: Don't use LRTs as collateral excessively
5. **Monitor actively**: Track operator performance, AVS health

### For Operators
1. **Limit AVS participation**: Don't overextend (max 5-10 AVSs)
2. **Use HSM/MPC**: Secure key management
3. **Client diversity**: Run multiple client implementations
4. **Self-stake significantly**: 20%+ of delegated funds
5. **Carry insurance**: Buffer for operational mistakes

### For AVS Developers
1. **Immutable slash bounds**: Or use DAO + timelock
2. **Formal verification**: Prove slashing conditions correct
3. **Transparent parameters**: Clear documentation of risks
4. **Audits before launch**: Multiple security reviews
5. **Bug bounties**: Ongoing incentives for vulnerability disclosure

### For LRT Protocols
1. **Circuit breakers**: Auto-pause on large price moves
2. **Conservative backing**: Maintain >100% collateral ratio
3. **Redemption limits**: Rate-limit mass exits
4. **Insurance fund**: Buffer for slashing events

## CWE Mappings

- **CWE-400**: Uncontrolled Resource Consumption (amplified slashing)
- **CWE-362**: Concurrent Execution using Shared Resource (systemic risk)
- **CWE-269**: Improper Privilege Management (centralized slashing)
- **CWE-693**: Protection Mechanism Failure (incomplete slash implementation)
- **CWE-841**: Improper Enforcement of Behavioral Workflow (mutable conditions)

## References

- EigenLayer Documentation: https://docs.eigenlayer.xyz
- BlockSec: "Examining EigenLayer and Restaking from Security Perspective" (Nov 2025)
- Cubist: "Slashing Risks You Need to Think About When Restaking" (Jan 2025)
- QuickNode: "Restaking Revolution: EigenLayer and DeFi Yields in 2025" (Sept 2025)
- Cobo: "Restaking in EigenLayer: Mitigating Risks & Best Practices" (Mar 2025)
- EigenLayer Hack Report: $5.7M phishing attack (Oct 2024)
- Slashing Activation: April 17, 2025 mainnet launch

## Related Categories

- **Access Control**: Centralized slashing triggers
- **Governance**: AVS parameter governance
- **Oracle**: External data for slashing decisions
- **Logic Errors**: Complex slashing calculation bugs
- **DoS**: Mass slashing affecting network availability
