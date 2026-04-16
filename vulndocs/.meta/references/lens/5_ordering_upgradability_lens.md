# Ordering Lens - Ultra-Expanded Detection Patterns

> Comprehensive MEV, front-running, sandwich attacks, and transaction ordering
> vulnerability detection for AlphaSwarm.sol

---

## Table of Contents
1. [Front-Running Attacks](#1-front-running-attacks)
2. [Sandwich Attacks](#2-sandwich-attacks)
3. [Back-Running Attacks](#3-back-running-attacks)
4. [Transaction Ordering Dependence](#4-transaction-ordering-dependence)
5. [Commit-Reveal Issues](#5-commit-reveal-issues)
6. [Slippage Protection](#6-slippage-protection)
7. [Deadline Protection](#7-deadline-protection)
8. [MEV Extraction Surfaces](#8-mev-extraction-surfaces)
9. [Atomic Arbitrage Vulnerabilities](#9-atomic-arbitrage-vulnerabilities)
10. [Governance Ordering Issues](#10-governance-ordering-issues)

---

## 1. Front-Running Attacks

### 1.1 Price-Sensitive Front-Running
**CWE-362**

#### Detection Phrases (NL Queries)
```
swap functions without slippage protection parameter
liquidation functions profitable for front-runners
oracle updates that can be sandwiched
large trades without private mempool or flashbots
price-sensitive transactions visible in mempool
swap without minimum output protection
trade transaction front-runnable for profit
oracle update front-runnable for arbitrage
large swap visible before execution
price-sensitive operation without protection
swap transaction exploitable via front-run
trade without front-running protection
oracle price update front-runnable
large transaction MEV extractable
price-sensitive swap without slippage
trade front-runnable by searchers
oracle update exploitable via ordering
large trade without MEV protection
price-sensitive function without minimum
swap exploitable via transaction ordering
trade without protection from front-run
oracle update visible in mempool
large swap without slippage protection
price-sensitive operation front-runnable
swap function without minimum output
trade exploitable by front-runners
oracle update without ordering protection
large transaction without MEV defense
price-sensitive swap exploitable
trade visible in mempool exploitable
```

#### Detection Rules
```yaml
rule: price-sensitive-frontrun
conditions:
  all:
    - function.performs_swap_or_trade == true
    - function.affects_price == true
    - OR:
      - function.has_slippage_parameter == false
      - function.has_minimum_output == false
severity: high
```

### 1.2 Approval Front-Running
**CWE-362**

#### Detection Phrases
```
approve transaction front-runnable
allowance change visible before execution
approval front-run for double spend
approve vulnerable to race condition
allowance update front-runnable
approval transaction exploitable
approve without atomic usage
allowance change exploitable via front-run
approval front-run window
approve transaction race condition
allowance update race condition
approval exploitable via ordering
approve followed by separate transferFrom
allowance change front-run window
approval race condition vulnerability
approve transaction followed by transfer
allowance update exploitable
approval front-running attack
approve without immediate use
allowance change race condition
approval visible in mempool
approve exploitable via front-run
allowance update front-run attack
approval without atomic pattern
approve race condition window
allowance change without atomic
approval front-run double spend
approve exploitable via ordering
allowance update visible in mempool
approval race attack possible
```

### 1.3 Commit-Reveal Front-Running
**CWE-362**

#### Detection Phrases
```
reveal transaction front-runnable
commit value visible in reveal
reveal front-run before processing
commit-reveal scheme front-runnable
reveal transaction exploitable
commit value deducible before reveal
reveal front-run attack possible
commit-reveal without proper timing
reveal transaction visible in mempool
commit value extractable from reveal
reveal front-runnable by searchers
commit-reveal timing exploitable
reveal transaction MEV extractable
commit value visible on reveal
reveal front-run for value extraction
commit-reveal front-run window
reveal transaction ordering exploitable
commit value derivable from transaction
reveal front-runnable for profit
commit-reveal scheme exploitable
reveal transaction front-run attack
commit value visible before reveal
reveal front-run timing attack
commit-reveal without protection
reveal transaction exploitable via ordering
commit value extractable on reveal
reveal front-runnable via mempool
commit-reveal reveal phase vulnerable
reveal transaction front-run window
commit value visible in reveal tx
```

### 1.4 Governance Front-Running
**CWE-362**

#### Detection Phrases
```
governance proposals executable without delay
proposal execution front-runnable
governance vote front-runnable
proposal submission visible in mempool
governance decision front-runnable
proposal execution without timelock
governance vote exploitable via ordering
proposal front-run for positioning
governance execution front-runnable
proposal vote front-run attack
governance without execution delay
proposal transaction front-runnable
governance action exploitable
proposal execution visible before finality
governance front-run for profit
proposal submission front-runnable
governance decision exploitable
proposal execution timing attack
governance vote ordering exploitable
proposal front-run before execution
governance without delay protection
proposal visible in mempool exploitable
governance front-runnable by voters
proposal execution front-run window
governance timing attack possible
proposal submission exploitable
governance action front-runnable
proposal vote front-runnable
governance execution timing exploitable
proposal front-run attack vector
```

---

## 2. Sandwich Attacks

### 2.1 AMM Sandwich Vulnerability
**CWE-362**

#### Detection Phrases
```
AMM swaps without minimum output amount
price impact calculations vulnerable to manipulation
liquidity additions without deadline parameter
swap without slippage protection
AMM trade sandwichable
price impact exploitable via sandwich
liquidity operation sandwich vulnerable
swap without minimum received
AMM transaction sandwichable
price manipulation via sandwich attack
liquidity add sandwich exploitable
swap without sandwich protection
AMM operation sandwich vulnerable
price impact manipulable
liquidity operation without slippage
swap sandwichable by searchers
AMM swap without protection
price manipulation sandwich attack
liquidity add without minimum
swap without MEV protection
AMM trade sandwich vulnerable
price impact sandwich exploitable
liquidity operation sandwichable
swap transaction sandwich attack
AMM without slippage parameter
price manipulation via ordering
liquidity add sandwich attack
swap sandwich attack surface
AMM operation exploitable
price impact sandwich vulnerability
```

#### Detection Rules
```yaml
rule: amm-sandwich-vulnerability
conditions:
  all:
    - function.interacts_with_amm == true
    - OR:
      - function.has_slippage_parameter == false
      - function.has_minimum_output == false
      - function.has_deadline_parameter == false
severity: high
```

### 2.2 Oracle Sandwich Attacks
**CWE-362**

#### Detection Phrases
```
oracle update sandwichable
price feed update sandwich vulnerable
oracle price manipulation via sandwich
price update transaction sandwichable
oracle manipulation before and after
price feed sandwich attack
oracle update ordering exploitable
price manipulation sandwich oracle
oracle sandwich for profit
price feed update exploitable
oracle price sandwich attack
price update sandwich vulnerable
oracle manipulation via transaction ordering
price feed sandwichable
oracle update sandwich attack
price manipulation via oracle sandwich
oracle price update sandwichable
price feed manipulation sandwich
oracle sandwich attack surface
price update sandwichable by searcher
oracle manipulation sandwich profit
price feed sandwich vulnerable
oracle update exploitable via sandwich
price manipulation around oracle update
oracle sandwich vulnerability
price feed update sandwich attack
oracle price manipulation sandwich
price update sandwich attack vector
oracle sandwichable for arbitrage
price feed sandwich for profit
```

### 2.3 Liquidity Sandwich Attacks
**CWE-362**

#### Detection Phrases
```
liquidity provision sandwichable
LP token minting sandwich vulnerable
liquidity removal sandwich attack
LP operation sandwich exploitable
liquidity add sandwich vulnerable
LP token calculation sandwichable
liquidity remove sandwich attack
LP provision sandwich attack
liquidity operation sandwichable
LP minting sandwich vulnerable
liquidity provision without protection
LP token sandwich exploitable
liquidity removal sandwichable
LP operation without slippage
liquidity add without protection
LP token minting sandwich attack
liquidity remove sandwichable
LP provision sandwich vulnerable
liquidity sandwich for profit
LP operation sandwichable
liquidity provision sandwich attack
LP sandwich attack surface
liquidity removal without minimum
LP token sandwich attack
liquidity add sandwichable
LP minting without protection
liquidity remove sandwich vulnerable
LP provision sandwich exploitable
liquidity sandwich attack vector
LP sandwich for profit extraction
```

---

## 3. Back-Running Attacks

### 3.1 Profitable Back-Running
**CWE-362**

#### Detection Phrases
```
profitable operations visible in mempool before execution
reward claims without commitment scheme
NFT mints with predictable token IDs
arbitrage opportunity visible in mempool
profitable transaction back-runnable
reward claim back-run exploitable
NFT mint back-runnable
arbitrage back-run attack
profitable operation back-runnable
reward distribution back-run vulnerable
NFT token ID predictable
arbitrage transaction back-runnable
profitable claim back-runnable
reward claim without protection
NFT mint predictable tokenId
arbitrage opportunity back-runnable
profitable operation visible before execution
reward back-run for extraction
NFT back-run for snipe
arbitrage back-runnable by searchers
profitable transaction visible in mempool
reward claim back-runnable
NFT mint tokenId predictable
arbitrage back-run attack vector
profitable operation MEV extractable
reward distribution back-runnable
NFT predictable mint back-run
arbitrage visible before execution
profitable back-run opportunity
reward back-runnable for profit
```

### 3.2 Liquidation Back-Running
**CWE-362**

#### Detection Phrases
```
liquidation transaction back-runnable
underwater position visible back-runnable
liquidation profit extractable via back-run
position liquidation back-run attack
liquidation opportunity visible
underwater account back-runnable
liquidation MEV extractable
position back-runnable for liquidation
liquidation transaction visible in mempool
underwater position back-run exploitable
liquidation profit via back-run
position liquidation visible before execution
liquidation back-run by searchers
underwater account visible in mempool
liquidation transaction MEV
position back-run for liquidation profit
liquidation opportunity back-runnable
underwater position MEV extractable
liquidation back-run attack vector
position liquidation back-runnable
liquidation visible before finality
underwater account back-run attack
liquidation profit back-runnable
position back-runnable liquidation
liquidation transaction exploitable
underwater position liquidation visible
liquidation back-run for profit
position liquidation MEV
liquidation opportunity MEV
underwater back-run attack
```

### 3.3 Airdrop & Claim Back-Running
**CWE-362**

#### Detection Phrases
```
airdrop claim transaction back-runnable
merkle proof claim back-runnable
airdrop eligibility visible before claim
claim transaction back-run exploitable
airdrop claim visible in mempool
merkle claim back-run attack
airdrop eligibility back-runnable
claim back-runnable by searchers
airdrop claim MEV extractable
merkle proof back-runnable
airdrop transaction visible before execution
claim back-run for extraction
airdrop eligibility check back-runnable
merkle claim visible in mempool
airdrop claim back-run attack
claim transaction MEV extractable
airdrop back-runnable for theft
merkle proof claim visible
airdrop claim exploitable via back-run
claim back-run attack vector
airdrop eligibility visible in mempool
merkle claim exploitable
airdrop transaction back-runnable
claim back-runnable by MEV
airdrop claim visible before finality
merkle proof back-run attack
airdrop back-run attack
claim transaction back-runnable
airdrop eligibility MEV
merkle back-runnable claim
```

---

## 4. Transaction Ordering Dependence

### 4.1 State-Dependent Ordering
**CWE-362**

#### Detection Phrases
```
function outcome dependent on transaction order
state-dependent result ordering exploitable
transaction ordering affecting outcome
state change ordering dependent
function result dependent on order
transaction order affecting state
ordering dependence in state change
state-dependent ordering vulnerability
function ordering dependent outcome
transaction order exploitable
state change order dependent
ordering affecting function result
state-dependent transaction outcome
function result ordering exploitable
transaction ordering vulnerability
state change ordering exploitable
ordering dependence vulnerability
state-dependent outcome exploitable
function ordering exploitable
transaction order dependence
state change order exploitable
ordering affecting outcome
state-dependent ordering exploitable
function outcome order dependent
transaction ordering state dependent
state order dependency vulnerability
function result order exploitable
transaction ordering dependence
state-dependent ordering vulnerability
ordering dependent function outcome
```

### 4.2 First-Come-First-Served Issues
**CWE-362**

#### Detection Phrases
```
first-come-first-served without fair ordering
FCFS vulnerable to front-running
first-come advantage exploitable
FCFS ordering MEV vulnerable
first-come-first-served front-runnable
FCFS without ordering protection
first-come exploitable by searchers
FCFS vulnerable to ordering attacks
first-come-first-served MEV
FCFS front-run vulnerable
first-come advantage MEV extractable
FCFS ordering exploitable
first-come-first-served vulnerability
FCFS without fair mechanism
first-come front-runnable
FCFS ordering vulnerable
first-come-first-served exploitable
FCFS advantage extractable
first-come without protection
FCFS MEV extractable
first-come-first-served front-run
FCFS vulnerable to MEV
first-come ordering exploitable
FCFS without protection mechanism
first-come MEV vulnerable
FCFS front-running attack
first-come-first-served MEV vulnerable
FCFS ordering attack
first-come exploitable via ordering
FCFS advantage via MEV
```

### 4.3 Race Condition Patterns
**CWE-362**

#### Detection Phrases
```
race condition between transactions
concurrent transaction race condition
race condition in state update
transaction race vulnerability
concurrent access race condition
race between competing transactions
transaction ordering race condition
concurrent state modification race
race condition exploitable
transaction race for state change
concurrent transaction ordering race
race condition in critical section
transaction race condition vulnerability
concurrent access ordering race
race between users for same resource
transaction race exploitable
concurrent transaction race vulnerability
race condition in update path
transaction ordering race exploitable
concurrent race for limited resource
race condition between callers
transaction race for allocation
concurrent transaction race attack
race condition vulnerability
transaction race for claiming
concurrent access race vulnerability
race between transactions for resource
transaction ordering race condition
concurrent race condition attack
race condition in allocation
```

---

## 5. Commit-Reveal Issues

### 5.1 Weak Commit Schemes
**CWE-362**

#### Detection Phrases
```
commit-reveal without proper randomness
commitment hash weak or predictable
reveal value derivable from commit
commitment scheme brute-forceable
commit value guessable
reveal predictable from commitment
commitment without sufficient entropy
commit-reveal scheme weak
reveal value brute-forceable
commitment hash collision possible
commit predictable from context
reveal derivable before reveal phase
commitment scheme insufficient randomness
commit value predictable
reveal brute-forceable from commit
commitment without randomness
commit-reveal scheme breakable
reveal predictable from hash
commitment insufficient entropy
commit guessable from context
reveal derivable from commitment
commitment weak randomness
commit-reveal brute-forceable
reveal predictable from commit value
commitment scheme weak entropy
commit derivable from reveal
reveal value predictable
commitment brute-forceable
commit-reveal scheme insufficient
reveal predictable commitment
```

### 5.2 Timing Vulnerabilities
**CWE-362**

#### Detection Phrases
```
commit-reveal timing exploitable
reveal phase timing attack
commit timing window too short
reveal before commit finality
commit-reveal race condition
reveal timing exploitable
commit window insufficient
reveal phase front-runnable
commit-reveal timing attack
reveal timing vulnerability
commit phase timing issue
reveal before commit confirmed
commit-reveal phase timing
reveal front-runnable in timing window
commit timing vulnerable
reveal timing attack possible
commit-reveal window exploitable
reveal phase timing vulnerability
commit window exploitable
reveal timing front-run
commit-reveal timing vulnerability
reveal phase exploitable timing
commit timing too short
reveal timing exploitable by ordering
commit-reveal timing window
reveal phase timing attack possible
commit window timing attack
reveal timing window exploitable
commit-reveal timing exploitable
reveal timing vulnerability window
```

### 5.3 Reveal Value Extraction
**CWE-362**

#### Detection Phrases
```
reveal value visible in transaction
commit value extractable on reveal
reveal data exposed in calldata
commit secret visible on reveal
reveal transaction exposes value
commit value derivable from reveal tx
reveal exposes commitment value
commit secret in reveal transaction
reveal value visible in mempool
commit extractable from reveal
reveal data visible before processing
commit value exposed on reveal
reveal transaction value visible
commit derivable from reveal data
reveal exposes secret value
commit value in reveal calldata
reveal value extractable from tx
commit secret exposed on reveal
reveal data in transaction visible
commit value visible on reveal phase
reveal transaction exposes commitment
commit extractable from reveal transaction
reveal value visible before finality
commit value derivable from reveal
reveal exposes commitment
commit secret visible in reveal tx
reveal data extractable
commit value in calldata on reveal
reveal transaction commitment visible
commit derivable from reveal phase
```

---

## 6. Slippage Protection

### 6.1 Missing Slippage Parameters
**CWE-20**

#### Detection Phrases
```
swap without slippage tolerance parameter
trade function missing minimum output
exchange without slippage protection
swap missing amountOutMin parameter
trade without expected output validation
exchange function no slippage check
swap without minimum received amount
trade missing slippage parameter
exchange without minimum output
swap function no slippage tolerance
trade without amountOutMin
exchange missing minimum received
swap without output validation
trade function no minimum output
exchange without slippage parameter
swap missing minimum output amount
trade without slippage tolerance
exchange missing output validation
swap without expected minimum
trade function missing slippage
exchange without amountOutMin
swap missing output minimum
trade without minimum output parameter
exchange function missing slippage
swap without minimum output check
trade missing expected output
exchange without minimum amount
swap function missing minimum
trade without output minimum
exchange missing slippage tolerance
```

#### Detection Rules
```yaml
rule: missing-slippage-protection
conditions:
  all:
    - function.performs_swap == true
    - NOT function.has_minimum_output_parameter
severity: high
```

### 6.2 Insufficient Slippage Validation
**CWE-20**

#### Detection Phrases
```
slippage tolerance not enforced
minimum output not validated post-swap
slippage parameter ignored in execution
minimum amount check missing after trade
slippage tolerance check absent
minimum output validation missing
slippage not enforced on result
minimum amount not verified
slippage check missing post-execution
minimum output not checked after swap
slippage tolerance not verified
minimum amount validation absent
slippage enforcement missing
minimum output check not performed
slippage parameter not validated
minimum amount not enforced
slippage tolerance enforcement missing
minimum output not validated
slippage check not performed
minimum amount check missing
slippage not validated post-trade
minimum output enforcement missing
slippage tolerance check missing
minimum amount not verified post-swap
slippage validation missing
minimum output check absent
slippage not enforced correctly
minimum amount validation missing
slippage enforcement not performed
minimum output not enforced
```

### 6.3 Slippage Manipulation
**CWE-362**

#### Detection Phrases
```
slippage parameter user-controllable to zero
minimum output settable to zero by user
slippage tolerance bypassable
minimum amount parameter zero allowed
slippage parameter manipulation possible
minimum output zero accepted
slippage settable to bypass protection
minimum amount bypassable by user
slippage parameter zero allowed
minimum output manipulation possible
slippage tolerance zero accepted
minimum amount settable to zero
slippage bypassable via parameter
minimum output parameter bypassable
slippage zero value accepted
minimum amount zero allowed
slippage protection bypassable
minimum output settable by attacker
slippage parameter bypassable
minimum amount manipulation
slippage tolerance manipulation
minimum output zero value accepted
slippage manipulation via input
minimum amount parameter manipulation
slippage zero allowed
minimum output bypassable
slippage parameter zero accepted
minimum amount bypassable
slippage tolerance bypassable by user
minimum output manipulation possible
```

---

## 7. Deadline Protection

### 7.1 Missing Deadline Parameters
**CWE-20**

#### Detection Phrases
```
swap without transaction deadline
trade function missing deadline parameter
exchange without expiration timestamp
swap missing deadline validation
trade without time constraint
exchange function no deadline check
swap without expiry parameter
trade missing transaction deadline
exchange without deadline protection
swap function no expiration
trade without deadline parameter
exchange missing expiration check
swap without time limit
trade function no deadline
exchange without time constraint
swap missing expiration parameter
trade without expiry validation
exchange missing deadline parameter
swap without deadline check
trade function missing expiration
exchange without time limit
swap missing time constraint
trade without deadline validation
exchange function missing deadline
swap without expiration check
trade missing deadline check
exchange without expiry parameter
swap function missing deadline
trade without time limit parameter
exchange missing time constraint
```

### 7.2 Deadline Not Enforced
**CWE-20**

#### Detection Phrases
```
deadline parameter not validated
transaction deadline not checked
deadline not enforced before execution
transaction expiration ignored
deadline validation missing
transaction deadline not enforced
deadline check absent
transaction time limit not validated
deadline not verified before trade
transaction deadline enforcement missing
deadline parameter ignored
transaction expiration not checked
deadline enforcement missing
transaction deadline validation absent
deadline not checked on execution
transaction time constraint ignored
deadline validation not performed
transaction deadline check missing
deadline enforcement absent
transaction expiration validation missing
deadline parameter not enforced
transaction deadline ignored
deadline check not performed
transaction time limit ignored
deadline not enforced in function
transaction deadline not validated
deadline enforcement not performed
transaction expiration ignored
deadline validation absent
transaction deadline parameter ignored
```

### 7.3 Past Deadline Acceptance
**CWE-20**

#### Detection Phrases
```
deadline accepting past timestamp
expired deadline not rejected
deadline allowing block.timestamp equal
past deadline value accepted
deadline check accepting current block
expired transaction not rejected
deadline validation accepting past
past timestamp deadline allowed
deadline equal to current time accepted
expired deadline passing validation
deadline accepting expired value
past deadline not rejected
deadline check insufficient for past
expired timestamp accepted
deadline allowing expired transactions
past deadline validation passing
deadline accepting block.timestamp
expired value deadline accepted
deadline check accepting expired
past timestamp not rejected
deadline validation past accepted
expired deadline not caught
deadline accepting current or past
past deadline allowed through
deadline check not rejecting past
expired transaction accepted
deadline validation allowing past
past timestamp deadline accepted
deadline not rejecting expired
expired deadline validation passing
```

---

## 8. MEV Extraction Surfaces

### 8.1 Arbitrage Opportunities
**CWE-362**

#### Detection Phrases
```
arbitrage opportunities from predictable state changes
cross-pool price discrepancy exploitable
arbitrage from price update visible in mempool
cross-exchange arbitrage extractable
arbitrage opportunity predictable
cross-pool arbitrage MEV
arbitrage from oracle update
cross-exchange price discrepancy
arbitrage extractable via MEV
cross-pool price manipulation arbitrage
arbitrage opportunity visible
cross-exchange arbitrage opportunity
arbitrage from swap transaction
cross-pool arbitrage extractable
arbitrage visible before execution
cross-exchange price arbitrage
arbitrage from large trade
cross-pool arbitrage opportunity
arbitrage MEV extractable
cross-exchange arbitrage visible
arbitrage from price movement
cross-pool price arbitrage MEV
arbitrage opportunity MEV
cross-exchange arbitrage extractable
arbitrage from state change
cross-pool arbitrage visible
arbitrage extractable from transaction
cross-exchange price discrepancy MEV
arbitrage opportunity extractable
cross-pool arbitrage from price change
```

### 8.2 JIT Liquidity Attacks
**CWE-362**

#### Detection Phrases
```
just-in-time liquidity extractable
JIT liquidity attack possible
liquidity add/remove around swap
JIT attack on swap transaction
liquidity manipulation JIT attack
JIT liquidity MEV extraction
liquidity sandwich JIT attack
JIT liquidity from swap visibility
liquidity provision JIT exploitable
JIT attack from mempool visibility
liquidity JIT for fee extraction
JIT liquidity attack surface
liquidity manipulation for JIT
JIT attack on large swap
liquidity add-remove JIT
JIT liquidity fee extraction
liquidity provision JIT attack
JIT attack extractable
liquidity manipulation JIT
JIT liquidity from pending swap
liquidity JIT attack possible
JIT liquidity extraction
liquidity provision around swap
JIT attack from swap transaction
liquidity JIT extraction MEV
JIT liquidity attack vector
liquidity add-remove JIT attack
JIT attack surface
liquidity manipulation JIT extractable
JIT liquidity from visible swap
```

### 8.3 Generalized MEV
**CWE-362**

#### Detection Phrases
```
MEV extractable from transaction ordering
transaction value extractable via MEV
MEV opportunity from visible transaction
transaction ordering MEV exploitable
MEV extraction from pending transactions
transaction MEV attack surface
MEV from state change visibility
transaction order MEV extractable
MEV opportunity visible in mempool
transaction MEV extraction possible
MEV from predictable outcome
transaction ordering MEV attack
MEV extraction surface
transaction MEV from visibility
MEV opportunity extractable
transaction order exploitable for MEV
MEV from pending transaction
transaction MEV vulnerability
MEV extraction from ordering
transaction visibility MEV
MEV opportunity from ordering
transaction MEV extractable
MEV from transaction visibility
transaction order MEV
MEV extraction opportunity
transaction MEV attack
MEV from visible state change
transaction ordering MEV extraction
MEV opportunity attack
transaction MEV surface
```

---

## 9. Atomic Arbitrage Vulnerabilities

### 9.1 Flash Loan Arbitrage
**CWE-362**

#### Detection Phrases
```
flash loan enabling risk-free arbitrage
atomic arbitrage via flash loan
flash loan arbitrage opportunity
atomic price manipulation arbitrage
flash loan cross-pool arbitrage
atomic arbitrage extractable
flash loan price arbitrage
atomic cross-exchange arbitrage
flash loan arbitrage attack
atomic arbitrage from price discrepancy
flash loan enabling atomic arbitrage
atomic arbitrage opportunity
flash loan for risk-free profit
atomic price discrepancy arbitrage
flash loan cross-exchange arbitrage
atomic arbitrage flash loan enabled
flash loan arbitrage extraction
atomic cross-pool arbitrage
flash loan for atomic arbitrage
atomic arbitrage via flash
flash loan risk-free arbitrage
atomic arbitrage extractable via flash
flash loan price discrepancy
atomic arbitrage opportunity flash
flash loan atomic arbitrage attack
atomic cross-exchange via flash
flash loan enabling arbitrage
atomic arbitrage flash enabled
flash loan arbitrage opportunity
atomic arbitrage via flash loan attack
```

### 9.2 Cross-Protocol Arbitrage
**CWE-362**

#### Detection Phrases
```
cross-protocol price discrepancy arbitrage
inter-protocol arbitrage opportunity
cross-protocol atomic arbitrage
inter-protocol price manipulation
cross-protocol arbitrage extractable
inter-protocol arbitrage via flash loan
cross-protocol price arbitrage
inter-protocol atomic exploitation
cross-protocol arbitrage attack
inter-protocol price discrepancy
cross-protocol atomic arbitrage opportunity
inter-protocol arbitrage surface
cross-protocol price exploitation
inter-protocol atomic arbitrage
cross-protocol arbitrage via integration
inter-protocol price arbitrage opportunity
cross-protocol atomic exploitation
inter-protocol arbitrage extractable
cross-protocol price discrepancy attack
inter-protocol atomic attack
cross-protocol arbitrage opportunity
inter-protocol price exploitation
cross-protocol atomic arbitrage attack
inter-protocol arbitrage opportunity
cross-protocol price arbitrage attack
inter-protocol atomic arbitrage extractable
cross-protocol arbitrage extraction
inter-protocol price discrepancy arbitrage
cross-protocol atomic opportunity
inter-protocol arbitrage via atomic
```

---

## 10. Governance Ordering Issues

### 10.1 Proposal Timing Attacks
**CWE-362**

#### Detection Phrases
```
governance proposal timing exploitable
proposal submission front-runnable
governance timing attack possible
proposal execution timing vulnerability
governance proposal ordering attack
proposal timing manipulation
governance execution timing exploitable
proposal front-run attack
governance timing manipulation
proposal execution front-runnable
governance proposal timing attack
proposal timing front-run
governance ordering attack
proposal submission timing attack
governance proposal front-runnable
proposal ordering manipulation
governance timing vulnerability
proposal timing ordering attack
governance proposal ordering exploitable
proposal execution ordering attack
governance timing front-run
proposal timing vulnerability
governance ordering vulnerability
proposal front-run timing
governance proposal timing vulnerability
proposal ordering attack
governance execution ordering
proposal timing attack possible
governance ordering exploitable
proposal execution timing attack
```

### 10.2 Vote Timing Issues
**CWE-362**

#### Detection Phrases
```
voting period timing exploitable
vote submission front-runnable
voting timing attack possible
vote counting timing vulnerability
voting period ordering attack
vote timing manipulation
voting execution timing exploitable
vote front-run attack
voting timing manipulation
vote counting front-runnable
voting period timing attack
vote timing front-run
voting ordering attack
vote submission timing attack
voting period front-runnable
vote ordering manipulation
voting timing vulnerability
vote timing ordering attack
voting period ordering exploitable
vote counting ordering attack
voting timing front-run
vote timing vulnerability
voting ordering vulnerability
vote front-run timing
voting period timing vulnerability
vote ordering attack
voting execution ordering
vote timing attack possible
voting ordering exploitable
vote counting timing attack
```

---

## Complex Query Examples for Ordering Lens

### Query 1: Front-Running Vulnerability Detection
```json
{
  "query_kind": "logic",
  "node_types": ["Function"],
  "match": {
    "all": [
      {"property": "performs_swap_or_trade", "op": "eq", "value": true},
      {"property": "affects_price_or_state", "op": "eq", "value": true}
    ],
    "none": [
      {"property": "has_slippage_parameter", "op": "eq", "value": true},
      {"property": "has_minimum_output", "op": "eq", "value": true},
      {"property": "has_deadline_parameter", "op": "eq", "value": true}
    ]
  },
  "explain_mode": true
}
```

### Query 2: Sandwich Attack Surface
```json
{
  "query_kind": "logic",
  "node_types": ["Function"],
  "match": {
    "all": [
      {"property": "interacts_with_amm", "op": "eq", "value": true}
    ],
    "any_missing": [
      {"property": "has_slippage_protection"},
      {"property": "has_minimum_output"},
      {"property": "has_deadline"}
    ]
  },
  "explain_mode": true
}
```

### Query 3: MEV Extraction Surface
```json
{
  "query_kind": "logic",
  "node_types": ["Function"],
  "match": {
    "any": [
      {"property": "creates_arbitrage_opportunity", "op": "eq", "value": true},
      {"property": "affects_pool_price", "op": "eq", "value": true},
      {"property": "performs_liquidation", "op": "eq", "value": true}
    ],
    "all": [
      {"property": "visibility", "op": "in", "value": ["public", "external"]}
    ]
  },
  "explain_mode": true
}
```

---

## Pattern Pack: Ordering Lens Complete

```yaml
# Save as patterns/ordering-lens.yaml
patterns:
  - id: ord-001
    name: Missing Slippage Protection
    severity: high
    cwe: [362]

  - id: ord-002
    name: Missing Deadline Parameter
    severity: medium
    cwe: [20]

  - id: ord-003
    name: Sandwich Attack Vulnerable
    severity: high
    cwe: [362]

  - id: ord-004
    name: Front-Running Vulnerable
    severity: high
    cwe: [362]

  - id: ord-005
    name: Approval Race Condition
    severity: medium
    cwe: [362]

  - id: ord-006
    name: Weak Commit-Reveal
    severity: medium
    cwe: [362]

  - id: ord-007
    name: Governance Timing Attack
    severity: medium
    cwe: [362]

  - id: ord-008
    name: JIT Liquidity Attack Surface
    severity: medium
    cwe: [362]

  - id: ord-009
    name: Flash Loan Arbitrage
    severity: medium
    cwe: [362]

  - id: ord-010
    name: Transaction Order Dependence
    severity: medium
    cwe: [362]
```

---
---
---

# Upgradeability Lens - Ultra-Expanded Detection Patterns

> Comprehensive proxy patterns, storage collisions, and upgrade mechanism vulnerability
> detection for AlphaSwarm.sol

---

## Table of Contents
1. [Uninitialized Proxy Issues](#1-uninitialized-proxy-issues)
2. [Storage Collision Vulnerabilities](#2-storage-collision-vulnerabilities)
3. [Function Selector Clashing](#3-function-selector-clashing)
4. [UUPS Specific Issues](#4-uups-specific-issues)
5. [Transparent Proxy Issues](#5-transparent-proxy-issues)
6. [Beacon Proxy Issues](#6-beacon-proxy-issues)
7. [Diamond Proxy Issues](#7-diamond-proxy-issues)
8. [Upgrade Authorization](#8-upgrade-authorization)
9. [Implementation Security](#9-implementation-security)
10. [Initialization Security](#10-initialization-security)

---

## 1. Uninitialized Proxy Issues

### 1.1 Missing Initializer Protection
**CWE-665** (Improper Initialization)

#### Detection Phrases (NL Queries)
```
initializer functions callable by anyone
proxy implementations without initialized flag check
initialize function without initializer modifier
upgradeable contracts with unprotected initialize
UUPS proxies where implementation lacks initialization
initializer missing onlyInitializing modifier
initialize callable multiple times
initializer without initialized state check
initialize function missing reentrancy guard
initializer callable after deployment
initialize without proper modifier
initializer missing initialization check
initialize function unprotected
initializer callable by anyone
initialize missing initializer guard
initializer without proper protection
initialize callable post-deployment
initializer missing initialized flag
initialize without one-time restriction
initializer missing modifier
initialize callable again after init
initializer without reentrancy protection
initialize missing proper guard
initializer callable repeatedly
initialize without initialization flag
initializer unprotected in implementation
initialize callable by attacker
initializer missing proper restriction
initialize without single-use enforcement
initializer callable without restriction
```

#### Detection Rules
```yaml
rule: unprotected-initializer
conditions:
  all:
    - function.name MATCHES (initialize|init|setup|__init__)
    - function.visibility IN [public, external]
    - NOT function.has_initializer_modifier
    - NOT function.checks_initialized_flag
severity: critical
```

### 1.2 Implementation Initialization
**CWE-665**

#### Detection Phrases
```
implementation contract initializable directly
implementation missing disable initializers
implementation initialize callable
implementation initializer not disabled
implementation contract not locked
implementation initialize exploitable
implementation missing _disableInitializers
implementation initializer accessible
implementation contract initializable
implementation not protected from initialize
implementation initializer not locked
implementation missing initialization lock
implementation initialize not disabled
implementation contract exposed
implementation initializer exploitable
implementation not calling _disableInitializers
implementation initialize accessible directly
implementation contract vulnerable
implementation initializer not disabled in constructor
implementation missing disable in constructor
implementation initialize callable directly
implementation not locked against initialization
implementation initializer accessible on implementation
implementation missing proper constructor
implementation initialize exploitable directly
implementation constructor not disabling
implementation initializer not protected
implementation initialize not locked
implementation contract initializable directly
implementation missing _disableInitializers call
```

### 1.3 Reinitialization Vulnerabilities
**CWE-665**

#### Detection Phrases
```
reinitializer callable to reset state
version parameter allowing reinitialization
reinitialize function unprotected
version check bypassable for reinit
reinitializer missing proper guards
version parameter exploitable
reinitialize callable by attacker
version increment allowing re-init
reinitializer without version validation
version parameter manipulation
reinitialize state reset possible
version check insufficient
reinitializer version exploitable
version parameter without proper check
reinitialize allowing state overwrite
version validation missing
reinitializer callable improperly
version parameter allowing reset
reinitialize without version restriction
version check bypassable
reinitializer exploitable via version
version parameter for re-initialization
reinitialize callable with old version
version validation insufficient
reinitializer without proper version check
version parameter exploitable for reinit
reinitialize state manipulation
version check missing
reinitializer version bypass
version parameter allowing reinitialization attack
```

---

## 2. Storage Collision Vulnerabilities

### 2.1 Slot Collision Detection
**CWE-787** (Out-of-bounds Write)

#### Detection Phrases
```
proxy and implementation with conflicting storage layouts
inherited contracts changing storage variable order
upgrades adding state variables not at end of layout
diamond storage without proper namespace isolation
storage slot collision between proxy and implementation
storage layout mismatch in upgrade
storage variable order changed in upgrade
storage slots overlapping between contracts
storage layout incompatible after upgrade
storage collision in inherited contract
storage slot conflict in proxy pattern
storage layout change breaking upgrade
storage variable slot collision
storage slots conflicting in upgrade
storage layout ordering mismatch
storage collision from inheritance
storage slot overlap in implementation
storage layout breaking change
storage variable conflict in upgrade
storage slots misaligned
storage layout incompatibility
storage collision between contracts
storage slot mismatch in proxy
storage layout conflict
storage variable ordering issue
storage slots conflicting
storage layout slot collision
storage collision in upgrade path
storage slot conflict from variable order
storage layout incompatible between versions
```

#### Detection Rules
```yaml
rule: storage-collision
conditions:
  all:
    - contract.is_upgradeable == true
    - OR:
      - contract.storage_layout_changed == true
      - contract.new_variables_not_at_end == true
      - contract.inherited_storage_conflict == true
severity: critical
```

### 2.2 Gap Variable Issues
**CWE-787**

#### Detection Phrases
```
storage gaps not implemented in base contract
gap variable missing for upgrade safety
storage gap size insufficient
gap not reserved in upgradeable contract
storage gap missing in inheritance chain
gap variable not defined
storage gap not accounting for future variables
gap size too small for upgrade needs
storage gap missing in parent contract
gap variable insufficient size
storage gap not properly sized
gap missing in upgradeable base
storage gap absent in contract
gap variable not reserved
storage gap size not calculated
gap missing for upgrade compatibility
storage gap not implemented
gap variable size incorrect
storage gap missing between contracts
gap not defined in inheritance
storage gap absent for future variables
gap variable missing in base
storage gap not sufficient
gap size incorrect for needs
storage gap not reserved properly
gap variable absent
storage gap size miscalculated
gap missing in upgradeable contract
storage gap not defined for safety
gap variable size insufficient for upgrade
```

### 2.3 Packed Storage Issues
**CWE-787**

#### Detection Phrases
```
packed storage layout changed in upgrade
storage packing order modified
packed variables reordered in upgrade
storage packing slot boundary crossed
packed storage layout incompatible
storage packing changed between versions
packed variables slot assignment changed
storage packing order issue
packed storage layout mismatch
storage packing incompatible after upgrade
packed variables reordering
storage packing slot collision
packed storage order changed
storage packing layout conflict
packed variables layout changed
storage packing boundary issue
packed storage incompatible
storage packing order modified in upgrade
packed variables slot mismatch
storage packing layout changed
packed storage slot boundary
storage packing order changed in upgrade
packed variables reordered
storage packing slot overlap
packed storage layout conflict
storage packing order issue in upgrade
packed variables layout incompatible
storage packing changed
packed storage order mismatch
storage packing slot boundary crossed
```

---

## 3. Function Selector Clashing

### 3.1 Proxy-Implementation Selector Clash
**CWE-436** (Interpretation Conflict)

#### Detection Phrases
```
proxy admin functions with selectors matching implementation
transparent proxy with selector collision risks
fallback functions that may intercept intended calls
proxy function selector clashing with implementation
selector collision in proxy pattern
proxy function intercepting implementation call
selector clash between proxy and logic
proxy selector shadowing implementation
function selector collision in proxy
proxy admin selector matching logic function
selector clash causing call interception
proxy function overriding implementation
selector collision blocking implementation
proxy selector conflict with implementation
function clash in proxy pattern
proxy admin function selector collision
selector shadowing in proxy
proxy function clashing with logic
selector collision in transparent proxy
proxy selector overriding implementation function
function selector clash proxy
proxy function selector conflict
selector collision shadowing implementation
proxy admin selector clash
function clashing in proxy pattern
proxy selector collision with logic
selector conflict in proxy
proxy function shadowing implementation
selector clash in proxy pattern
proxy selector matching implementation function
```

### 3.2 Diamond Selector Issues
**CWE-436**

#### Detection Phrases
```
diamond facet selector collision
facet function selector clash
diamond selector conflict between facets
facet selector shadowing another facet
diamond function selector collision
facet selector clash causing routing issue
diamond facet selector conflict
facet function clashing with another
diamond selector collision between facets
facet selector shadowing function
diamond facet selector clash
facet function selector conflict
diamond selector shadowing
facet selector collision
diamond function clash between facets
facet selector conflict
diamond selector routing issue
facet function shadowing
diamond facet selector shadowing
facet selector clashing
diamond selector conflict causing issue
facet function clash
diamond selector shadowing another facet
facet selector routing conflict
diamond facet clash
facet selector issue
diamond selector collision
facet function selector shadowing
diamond facet selector conflict
facet selector collision routing
```

---

## 4. UUPS Specific Issues

### 4.1 UUPS Upgrade Authorization
**CWE-284**

#### Detection Phrases
```
UUPS upgrade function missing onlyProxy modifier
upgradeToAndCall callable on implementation directly
UUPS _authorizeUpgrade not properly protected
upgrade function missing access control
UUPS upgradeToAndCall without authorization
upgrade callable by non-admin
UUPS upgrade authorization missing
upgradeToAndCall without proper check
UUPS _authorizeUpgrade unprotected
upgrade function callable by anyone
UUPS upgrade without onlyProxy
upgradeToAndCall missing authorization
UUPS upgrade authorization bypass
upgrade function unprotected
UUPS _authorizeUpgrade without access control
upgradeToAndCall callable directly
UUPS upgrade function unprotected
upgrade missing authorization check
UUPS upgrade callable on implementation
upgradeToAndCall without access control
UUPS _authorizeUpgrade missing
upgrade function without protection
UUPS upgrade authorization insufficient
upgradeToAndCall accessible on implementation
UUPS upgrade function without authorization
upgrade callable without restriction
UUPS _authorizeUpgrade bypass
upgradeToAndCall missing protection
UUPS upgrade missing protection
upgrade function authorization missing
```

#### Detection Rules
```yaml
rule: uups-upgrade-authorization
conditions:
  all:
    - function.name IN [upgradeTo, upgradeToAndCall]
    - contract.is_uups_proxy == true
    - OR:
      - function.has_only_proxy_modifier == false
      - function.has_access_control == false
severity: critical
```

### 4.2 UUPS Implementation Destruction
**CWE-749**

#### Detection Phrases
```
UUPS implementation vulnerable to selfdestruct
implementation contract destructible
UUPS implementation with selfdestruct callable
implementation can be destroyed
UUPS implementation selfdestruct vulnerability
implementation destruction possible
UUPS implementation vulnerable to destruction
implementation with unprotected selfdestruct
UUPS implementation destructible by attacker
implementation selfdestruct accessible
UUPS implementation destruction attack
implementation can be selfdestructed
UUPS implementation with destruction risk
implementation selfdestruct callable
UUPS implementation vulnerable to destruction
implementation destruction vulnerability
UUPS implementation selfdestruct risk
implementation destructible vulnerability
UUPS implementation destruction possible
implementation with selfdestruct risk
UUPS implementation can be destroyed
implementation destruction accessible
UUPS implementation selfdestruct attack
implementation can be destructed
UUPS implementation destruction risk
implementation selfdestruct vulnerability
UUPS implementation vulnerable to selfdestruct attack
implementation destruction attack possible
UUPS implementation selfdestruct accessible
implementation destruction by attacker
```

---

## 5. Transparent Proxy Issues

### 5.1 Admin Slot Security
**CWE-284**

#### Detection Phrases
```
transparent proxy admin slot not properly protected
admin storage slot accessible
transparent proxy admin slot collision
admin slot readable by implementation
transparent proxy admin storage vulnerable
admin slot overwritable
transparent proxy admin slot accessible
admin storage slot collision
transparent proxy admin vulnerable
admin slot not properly isolated
transparent proxy admin slot readable
admin storage accessible via implementation
transparent proxy admin slot vulnerable
admin slot collision risk
transparent proxy admin storage collision
admin slot accessible to implementation
transparent proxy admin slot conflict
admin storage slot accessible
transparent proxy admin slot protection missing
admin slot not isolated
transparent proxy admin vulnerable to access
admin storage collision
transparent proxy admin slot security
admin slot vulnerable to overwrite
transparent proxy admin storage accessible
admin slot protection insufficient
transparent proxy admin slot accessible via delegatecall
admin storage vulnerable
transparent proxy admin slot conflict risk
admin slot accessible
```

### 5.2 Admin Call Routing
**CWE-436**

#### Detection Phrases
```
transparent proxy admin call routing issue
admin function call routed to implementation
transparent proxy admin call delegation
admin call incorrectly forwarded
transparent proxy admin routing vulnerability
admin function delegated to logic
transparent proxy admin call issue
admin call delegation error
transparent proxy admin routing error
admin function forwarded incorrectly
transparent proxy admin call forwarding
admin call routed to wrong target
transparent proxy admin delegation issue
admin function call routing error
transparent proxy admin forwarding issue
admin call delegation vulnerability
transparent proxy admin routing to implementation
admin function delegation error
transparent proxy admin call to implementation
admin routing issue in proxy
transparent proxy admin delegation error
admin function routing issue
transparent proxy admin call vulnerability
admin call to implementation error
transparent proxy admin forwarding vulnerability
admin function incorrectly routed
transparent proxy admin routing problem
admin call forwarding error
transparent proxy admin call to logic
admin routing vulnerability
```

---

## 6. Beacon Proxy Issues

### 6.1 Beacon Upgrade Security
**CWE-284**

#### Detection Phrases
```
beacon proxy with unprotected upgrade mechanism
beacon implementation changeable by attacker
beacon upgrade function without access control
beacon implementation update unprotected
beacon proxy upgrade authorization missing
beacon implementation setter unprotected
beacon upgrade without proper authorization
beacon implementation changeable
beacon proxy upgrade missing protection
beacon setter without access control
beacon upgrade function unprotected
beacon implementation update without check
beacon proxy upgrade vulnerability
beacon setter missing authorization
beacon upgrade authorization insufficient
beacon implementation changeable by anyone
beacon proxy upgrade access control missing
beacon setter unprotected
beacon upgrade function without protection
beacon implementation update vulnerability
beacon proxy upgrade unprotected
beacon setter without protection
beacon upgrade missing access control
beacon implementation setter without authorization
beacon proxy upgrade without authorization
beacon setter accessible by attacker
beacon upgrade access control missing
beacon implementation changeable without auth
beacon proxy upgrade function unprotected
beacon setter vulnerability
```

### 6.2 Beacon Atomicity Issues
**CWE-362**

#### Detection Phrases
```
beacon upgrade affecting multiple proxies atomically
beacon implementation change impacting all proxies
beacon upgrade atomicity concern
beacon change affecting all instances simultaneously
beacon implementation update atomic impact
beacon upgrade all proxies at once
beacon change atomicity risk
beacon implementation affecting all proxies
beacon upgrade simultaneous impact
beacon change impacting all instances
beacon implementation upgrade atomicity
beacon upgrade affecting all proxies
beacon change simultaneous to all
beacon implementation change atomicity
beacon upgrade atomicity vulnerability
beacon change affecting all simultaneously
beacon implementation upgrade all proxies
beacon upgrade atomic change risk
beacon change impacting proxies atomically
beacon implementation affecting instances
beacon upgrade simultaneous risk
beacon change atomicity concern
beacon implementation update affecting all
beacon upgrade impacting all proxies atomically
beacon change affecting all proxies at once
beacon implementation atomicity risk
beacon upgrade simultaneous impact risk
beacon change affecting all instances at once
beacon implementation upgrade affecting proxies
beacon upgrade atomicity impact
```

---

## 7. Diamond Proxy Issues

### 7.1 Diamond Storage Isolation
**CWE-787**

#### Detection Phrases
```
diamond storage without proper namespace isolation
facet storage collision risk
diamond storage namespace conflict
facet storage slot collision
diamond storage isolation missing
facet storage namespace issue
diamond storage slot conflict
facet storage isolation vulnerability
diamond storage namespace collision
facet storage conflict between facets
diamond storage isolation issue
facet storage namespace conflict
diamond storage without namespace
facet storage slot overlap
diamond storage isolation vulnerability
facet storage collision between facets
diamond storage namespace missing
facet storage overlap
diamond storage slot collision
facet storage isolation missing
diamond storage conflict
facet storage namespace overlap
diamond storage namespace isolation missing
facet storage slot conflict
diamond storage isolation absent
facet storage collision risk
diamond storage without proper isolation
facet storage namespace missing
diamond storage slot overlap
facet storage isolation issue
```

### 7.2 Diamond Cut Security
**CWE-284**

#### Detection Phrases
```
diamond cut function without access control
facet addition unprotected
diamond cut callable by anyone
facet modification without authorization
diamond cut missing access control
facet update unprotected
diamond cut function unprotected
facet removal without check
diamond cut authorization missing
facet management unprotected
diamond cut without proper protection
facet addition without authorization
diamond cut accessible by attacker
facet modification missing protection
diamond cut function missing authorization
facet update without access control
diamond cut vulnerability
facet removal unprotected
diamond cut missing protection
facet management without authorization
diamond cut access control missing
facet addition missing protection
diamond cut callable without auth
facet modification unprotected
diamond cut function vulnerability
facet update missing authorization
diamond cut unprotected
facet removal missing authorization
diamond cut without authorization
facet management vulnerability
```

---

## 8. Upgrade Authorization

### 8.1 Missing Upgrade Access Control
**CWE-284**

#### Detection Phrases
```
upgradeTo function without access control
upgrade mechanism unprotected
upgradeTo callable by anyone
upgrade function missing authorization
upgradeTo without proper protection
upgrade mechanism without access control
upgradeTo function unprotected
upgrade callable by attacker
upgradeTo missing authorization check
upgrade mechanism accessible
upgradeTo without authorization
upgrade function unprotected
upgradeTo accessible by anyone
upgrade mechanism missing protection
upgradeTo function missing protection
upgrade callable without restriction
upgradeTo without access control check
upgrade mechanism unprotected
upgradeTo callable without authorization
upgrade function missing access control
upgradeTo missing protection
upgrade mechanism vulnerability
upgradeTo function vulnerability
upgrade callable by non-admin
upgradeTo without proper authorization
upgrade mechanism accessible to attacker
upgradeTo missing access control
upgrade function without protection
upgradeTo accessible without auth
upgrade mechanism without authorization
```

### 8.2 Timelock on Upgrades
**CWE-284**

#### Detection Phrases
```
upgrade function without timelock
upgrade executable immediately
upgrade without delay mechanism
upgrade function immediate execution
upgrade missing timelock protection
upgrade without waiting period
upgrade function without delay
upgrade immediate without timelock
upgrade missing delay mechanism
upgrade without timelock protection
upgrade function executing immediately
upgrade missing waiting period
upgrade without delay
upgrade function without timelock protection
upgrade immediate execution
upgrade missing timelock
upgrade without mandatory delay
upgrade function without waiting period
upgrade immediate
upgrade missing delay
upgrade without timelock mechanism
upgrade function missing timelock
upgrade immediate without delay
upgrade missing mandatory waiting
upgrade without delay protection
upgrade function without delay mechanism
upgrade immediate execution risk
upgrade missing timelock mechanism
upgrade without waiting mechanism
upgrade function immediate
```

---

## 9. Implementation Security

### 9.1 Destructible Implementation
**CWE-749**

#### Detection Phrases
```
implementation contract that can be selfdestructed
delegatecall targets with selfdestruct
implementation with selfdestruct callable
implementation destructible vulnerability
implementation selfdestruct accessible
implementation contract selfdestruct risk
delegatecall target destructible
implementation with destruction vulnerability
implementation selfdestruct callable by attacker
implementation contract destructible
delegatecall to destructible implementation
implementation selfdestruct risk
implementation contract with selfdestruct
delegatecall target with selfdestruct
implementation destruction vulnerability
implementation selfdestruct accessible to attacker
implementation contract destruction risk
delegatecall to contract with selfdestruct
implementation with selfdestruct risk
implementation selfdestruct vulnerability
implementation contract selfdestruct callable
delegatecall target selfdestruct
implementation destruction risk
implementation selfdestruct
implementation contract selfdestruct accessible
delegatecall selfdestruct target
implementation with destruction risk
implementation selfdestruct callable
implementation contract selfdestruct vulnerability
delegatecall destructible target
```

### 9.2 Implementation Address Validation
**CWE-20**

#### Detection Phrases
```
implementation address not validated before upgrade
upgrade target not verified as contract
implementation address without validation
upgrade to EOA possible
implementation not checked for code
upgrade target validation missing
implementation address EOA allowed
upgrade to non-contract possible
implementation validation missing
upgrade target not verified
implementation address not checked
upgrade to address without code
implementation without code check
upgrade target EOA allowed
implementation address validation missing
upgrade to non-contract allowed
implementation not verified as contract
upgrade target code check missing
implementation address without code verification
upgrade to EOA allowed
implementation code check missing
upgrade target without validation
implementation address unvalidated
upgrade to address without code check
implementation without verification
upgrade target validation absent
implementation address code check missing
upgrade to non-contract address
implementation validation absent
upgrade target not checked for code
```

---

## 10. Initialization Security

### 10.1 Constructor vs Initializer
**CWE-665**

#### Detection Phrases
```
constructor setting state in upgradeable contract
constructor logic in upgradeable implementation
constructor state not preserved in proxy
constructor used instead of initializer
constructor logic lost in proxy pattern
constructor state initialization in upgradeable
constructor used in proxy implementation
constructor state not accessible via proxy
constructor instead of initializer
constructor logic in proxy context
constructor state lost in delegatecall
constructor used where initializer needed
constructor logic not available to proxy
constructor state initialization issue
constructor in upgradeable implementation
constructor logic lost via proxy
constructor state not preserved
constructor instead of initialize
constructor logic unavailable to proxy
constructor state issue in proxy
constructor in proxy implementation
constructor logic lost in proxy
constructor state lost
constructor where initializer needed
constructor logic in upgradeable
constructor state not in proxy
constructor used in upgradeable
constructor logic issue
constructor state initialization lost
constructor in upgradeable context
```

### 10.2 Initialization Order
**CWE-665**

#### Detection Phrases
```
initializer calling parent initializers wrong order
initialization order incorrect in inheritance
initializer parent calls out of order
initialization chain incorrect
initializer inheritance order wrong
initialization parent order issue
initializer calling parents incorrectly
initialization inheritance chain wrong
initializer order issue
initialization calling order wrong
initializer parent initialization order
initialization chain order incorrect
initializer inheritance order issue
initialization parent calls wrong
initializer order incorrect
initialization inheritance order wrong
initializer parent order wrong
initialization order issue in inheritance
initializer chain order wrong
initialization calling parents wrong order
initializer inheritance chain order
initialization order incorrect in chain
initializer parent initialization wrong
initialization chain wrong order
initializer calling order issue
initialization inheritance order issue
initializer order wrong in inheritance
initialization parent order incorrect
initializer chain order issue
initialization order wrong
```

---

## Complex Query Examples for Upgradeability Lens

### Query 1: Unprotected Initializer Detection
```json
{
  "query_kind": "logic",
  "node_types": ["Function"],
  "match": {
    "all": [
      {"property": "function_name_pattern", "op": "matches", "value": "(initialize|init|setup)"},
      {"property": "visibility", "op": "in", "value": ["public", "external"]}
    ],
    "none": [
      {"property": "has_initializer_modifier", "op": "eq", "value": true},
      {"property": "checks_initialized_flag", "op": "eq", "value": true}
    ]
  },
  "explain_mode": true
}
```

### Query 2: Unprotected Upgrade Function
```json
{
  "query_kind": "logic",
  "node_types": ["Function"],
  "match": {
    "all": [
      {"property": "function_name_pattern", "op": "matches", "value": "(upgradeTo|upgradeToAndCall)"},
      {"property": "visibility", "op": "in", "value": ["public", "external"]}
    ],
    "none": [
      {"property": "has_access_control", "op": "eq", "value": true},
      {"property": "has_only_proxy_modifier", "op": "eq", "value": true}
    ]
  },
  "explain_mode": true
}
```

### Query 3: Implementation Destruction Risk
```json
{
  "query_kind": "logic",
  "node_types": ["Contract"],
  "match": {
    "all": [
      {"property": "is_implementation_contract", "op": "eq", "value": true},
      {"property": "has_selfdestruct", "op": "eq", "value": true}
    ]
  },
  "explain_mode": true
}
```

---

## Pattern Pack: Upgradeability Lens Complete

```yaml
# Save as patterns/upgradeability-lens.yaml
patterns:
  - id: upg-001
    name: Unprotected Initializer
    severity: critical
    cwe: [665]

  - id: upg-002
    name: Implementation Not Disabled
    severity: high
    cwe: [665]

  - id: upg-003
    name: Storage Slot Collision
    severity: critical
    cwe: [787]

  - id: upg-004
    name: Missing Storage Gaps
    severity: medium
    cwe: [787]

  - id: upg-005
    name: Function Selector Clash
    severity: high
    cwe: [436]

  - id: upg-006
    name: UUPS Upgrade Unprotected
    severity: critical
    cwe: [284]

  - id: upg-007
    name: Implementation Destructible
    severity: critical
    cwe: [749]

  - id: upg-008
    name: Upgrade Missing Timelock
    severity: medium
    cwe: [284]

  - id: upg-009
    name: Beacon Upgrade Unprotected
    severity: critical
    cwe: [284]

  - id: upg-010
    name: Diamond Storage Collision
    severity: high
    cwe: [787]
```
