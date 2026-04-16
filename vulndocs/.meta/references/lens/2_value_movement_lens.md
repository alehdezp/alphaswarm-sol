# Value Movement Lens - Ultra-Expanded Detection Patterns

> Comprehensive reentrancy, external calls, and token operation vulnerability detection
> for AlphaSwarm.sol

---

## Table of Contents
1. [Classic Reentrancy](#1-classic-reentrancy)
2. [Cross-Function Reentrancy](#2-cross-function-reentrancy)
3. [Cross-Contract Reentrancy](#3-cross-contract-reentrancy)
4. [Read-Only Reentrancy](#4-read-only-reentrancy)
5. [ERC Token Reentrancy](#5-erc-token-reentrancy)
6. [External Call Safety](#6-external-call-safety)
7. [Low-Level Call Patterns](#7-low-level-call-patterns)
8. [Delegatecall Vulnerabilities](#8-delegatecall-vulnerabilities)
9. [Token Transfer Safety](#9-token-transfer-safety)
10. [Token Accounting Issues](#10-token-accounting-issues)
11. [Value Extraction Patterns](#11-value-extraction-patterns)
12. [Flash Loan Interactions](#12-flash-loan-interactions)

---

## 1. Classic Reentrancy

### 1.1 State-Before-External Pattern
**CWE-841** (Improper Enforcement of Behavioral Workflow)

#### Detection Phrases (NL Queries)
```
functions that perform external calls before updating state variables
external calls followed by state writes without reentrancy guard
public functions with ETH transfers before balance decrements
methods calling unknown addresses before modifying storage
functions where .call{value:} precedes state mutation
withdraw functions without reentrancy protection
functions sending ETH before zeroing user balance
methods making external calls then updating mappings
functions where transfer happens before balance update
external calls preceding storage modifications
functions calling untrusted contracts before state change
methods with value transfer before internal accounting
functions where callback can occur before state finalization
external calls to user-provided address before state write
functions sending funds before marking withdrawal complete
methods making calls to arbitrary address then writing storage
functions where ETH send precedes balance decrement
external calls in public functions before state mutation
functions transferring value before updating withdrawal status
methods calling external contracts before finalizing state
functions where low-level call happens before storage update
external calls preceding mapping updates
functions sending tokens before balance modification
methods making external calls before flag updates
functions where value movement precedes state synchronization
external calls before loop counter updates in withdrawals
functions calling unknown code before storage writes
methods with external interaction before state persistence
functions where fund transfer precedes accounting update
external calls to msg.sender before balance zeroing
functions sending ETH via call before state modification
methods making untrusted calls before storage changes
functions where external callback possible before state commit
calls to arbitrary contracts before internal state update
functions transferring control before completing state change
methods with external calls before withdrawal completion
functions where reentrancy window exists before state update
external interactions preceding critical state modifications
functions calling user contracts before zeroing balances
methods sending value before state machine transition
```

#### Detection Rules
```yaml
rule: classic-reentrancy-state-before-external
conditions:
  all:
    - function.visibility IN [public, external]
    - function.has_external_call == true
    - function.writes_state == true
    - function.external_call_precedes_state_write == true
    - function.has_reentrancy_guard == false
severity: critical
flow_analysis:
  - trace: external_call -> state_write
    constraint: no_guard_between
```

### 1.2 ETH Transfer Reentrancy
**CWE-841**

#### Detection Phrases
```
functions using .call{value:} without reentrancy protection
withdraw functions sending ETH before updating balance
methods using payable.transfer or send before state change
functions with ETH transfer to msg.sender before balance update
withdraw patterns vulnerable to reentrancy via fallback
functions sending ETH to arbitrary address before state write
methods transferring ETH where recipient controls callback
functions using low-level call with value before accounting
withdraw implementations not following checks-effects-interactions
functions where ETH recipient can reenter before state change
methods sending native token before balance decrement
functions with value transfer in loop without reentrancy guard
withdraw allowing callback before withdrawal completion
functions where ETH send recipient is msg.sender or parameter
methods transferring value before marking funds as claimed
functions sending ETH without mutex protection
withdraw vulnerable to reentrancy through receive function
functions transferring native currency before state update
methods where value movement triggers recipient callback
functions sending ETH to user-controlled address before state
withdraw patterns where fallback can call back
functions with .call{value:} to dynamic address before write
methods sending ETH before updating sent/claimed flag
functions where native transfer enables callback before state
withdraw implementations with external call before accounting
```

#### Detection Rules
```yaml
rule: eth-transfer-reentrancy
conditions:
  all:
    - function.transfers_eth == true
    - function.eth_recipient IN [msg.sender, parameter, storage_address]
    - function.writes_state_after_transfer == true
    - function.has_reentrancy_guard == false
severity: critical
```

### 1.3 Balance Update Patterns
**CWE-841**

#### Detection Phrases
```
functions decrementing balance after external call
methods updating user balance mapping after transfer
functions modifying balanceOf after sending tokens
withdraw where balance[user] -= amount after transfer
functions updating internal accounting after external send
methods zeroing balance after ETH transfer
functions modifying shares after value distribution
withdraw updating totalSupply after token burn
functions adjusting deposits mapping after withdrawal send
methods updating stake balance after reward claim
functions modifying liquidity after position exit
withdraw updating withdrawal mapping after transfer
functions adjusting collateral balance after liquidation
methods updating borrow balance after repayment
functions modifying reserve after withdrawal
withdraw updating claimable after distribution
functions adjusting pool balance after swap
methods updating vault shares after redemption
functions modifying position size after close
withdraw updating pending after claim execution
```

### 1.4 Loop Reentrancy
**CWE-841**

#### Detection Phrases
```
functions with external calls inside loops without protection
batch transfers vulnerable to reentrancy on each iteration
loops making external calls where state updated after loop
functions iterating with external calls before batch state update
methods with for/while loops containing unprotected external calls
batch withdraw functions with transfer in loop before accounting
loops calling external contracts with shared state vulnerability
functions iterating recipients with external call per iteration
batch distribution with external calls before total update
loops making external calls that can reenter same function
methods with unbounded loops containing external interactions
batch processing with external call per item before state sync
loops calling untrusted addresses with cumulative state update
functions iterating with external calls sharing reentrancy surface
batch operations where each iteration can reenter
loops making external calls with state dependency across iterations
methods with iteration over external calls before loop completion
batch functions where reentrancy affects subsequent iterations
loops calling dynamic addresses with state modified post-loop
functions iterating external calls with shared balance state
```

---

## 2. Cross-Function Reentrancy

### 2.1 Shared State Vulnerabilities
**CWE-841, CWE-362**

#### Detection Phrases
```
functions sharing state variables where one has external call and another reads same state
external calls in function A that can reenter function B reading uncommitted state
contracts where external call in one method affects invariants checked by another
state variables written after external call that are read by other public functions
functions where callback can call another function reading intermediate state
methods sharing balance mappings where one transfers and another checks
functions with external calls allowing reentry into state-dependent function
contracts where withdrawal can reenter deposit reading stale balance
shared state between functions with different reentrancy timing
methods where external call enables reentry to function assuming committed state
functions sharing total supply where one mints and another calculates shares
contracts with functions reading state modified by another after external call
methods where callback from A can call B reading A's uncommitted changes
functions sharing liquidity state where external call creates inconsistency window
contracts where function A's external call allows B to see intermediate state
methods with shared accounting where reentrancy breaks invariants
functions where external interaction allows cross-function state corruption
contracts where callback enables reading state mid-transaction
methods sharing reward state where claim can reenter stake
functions with external calls creating cross-function race condition
contracts where function A's callback allows B to act on partial state
methods sharing collateral where liquidate can reenter borrow
functions with shared position state vulnerable to cross-function attack
contracts where withdrawal callback allows deposit to see wrong balance
methods sharing price state where update can reenter swap
functions with external calls enabling cross-function invariant violation
contracts where one function's callback breaks another's assumptions
methods sharing governance state where vote can reenter proposal
functions with shared oracle state vulnerable to cross-function manipulation
contracts where claim callback allows stake to see intermediate rewards
```

#### Detection Rules
```yaml
rule: cross-function-reentrancy
conditions:
  contract_level:
    - exists_function_with_external_call: A
    - exists_function_reading_same_state: B
    - A.external_call_precedes_state_write == true
    - B.reads_state_modified_by_A == true
    - NOT A.has_reentrancy_guard OR NOT B.has_reentrancy_guard
severity: high
```

### 2.2 Cross-Function via Inheritance
**CWE-841**

#### Detection Phrases
```
inherited function with external call affecting child function's state assumptions
parent contract external call allowing reentry into child override
base function's callback enabling call to derived function with shared state
inherited method with external call creating reentrancy into child function
parent function external interaction affecting inherited state variables
base contract callback allowing derived function state manipulation
inherited external call creating window for child function attack
parent method's callback enabling cross-function reentrancy in child
base function external call affecting state read by child override
inherited callback vulnerability exploitable through derived function
parent contract external call with child function reading uncommitted state
base method creating reentrancy surface for inherited function
inherited external interaction affecting child's state assumptions
parent function callback allowing derived contract state corruption
base contract external call enabling child function state manipulation
inherited method external call with child reading intermediate state
parent callback creating cross-function vulnerability in child
base function's external interaction breaking child's invariants
inherited external call allowing reentry through child's interface
parent method callback enabling cross-function attack via inheritance
```

### 2.3 Cross-Function via Composition
**CWE-841**

#### Detection Phrases
```
composed contract external call affecting composer's state
external call in dependency enabling reentry into composing contract
library external call creating reentrancy into calling contract
composed module callback allowing state manipulation in parent
external interaction in helper contract affecting main contract state
dependency's external call creating window for main contract attack
helper function external call enabling reentrancy in composing contract
composed contract callback affecting shared state assumptions
external call in inherited library breaking caller's invariants
module external interaction creating cross-contract reentrancy
composed helper's callback enabling state corruption in parent
dependency external call affecting state read by composing contract
library callback creating reentrancy surface in calling code
composed module external call with parent reading uncommitted state
helper contract external interaction breaking composition invariants
dependency callback allowing cross-function attack in composer
external call in composed contract affecting parent's state machine
library external interaction creating window for caller attack
composed dependency callback enabling parent state manipulation
helper external call creating cross-contract state inconsistency
```

---

## 3. Cross-Contract Reentrancy

### 3.1 Protocol-Level Reentrancy
**CWE-841**

#### Detection Phrases
```
external calls to untrusted contracts that callback into dependent contracts
protocol interactions where state sync happens after external call
functions calling external contracts before updating shared protocol state
cross-contract calls creating reentrancy window in protocol invariants
external interaction in contract A enabling reentry into contract B
protocol functions where external call affects multi-contract state
cross-contract state dependency vulnerable to reentrancy attack
external calls creating inconsistency window across protocol contracts
functions in contract A calling external allowing attack on contract B
protocol-level state sync vulnerable to cross-contract reentrancy
external interaction enabling reentry into dependent protocol component
cross-contract external calls before shared state synchronization
protocol functions with external calls affecting system-wide invariants
external calls creating window for cross-protocol state manipulation
functions calling external contracts before protocol state reconciliation
cross-contract reentrancy through shared protocol dependency
external interaction in one contract breaking another's assumptions
protocol-level external calls with cross-contract state dependency
functions with external calls affecting multi-contract accounting
cross-contract callbacks enabling protocol-wide state corruption
external calls before cross-contract invariant enforcement
protocol interactions creating reentrancy across contract boundaries
functions calling external before updating shared protocol mapping
cross-contract external calls with dependent state assumptions
protocol-level reentrancy through callback chain across contracts
```

### 3.2 DeFi Protocol Reentrancy
**CWE-841**

#### Detection Phrases
```
lending protocol where borrow callback can reenter supply
AMM where swap callback can manipulate reserve before update
vault where deposit callback can reenter withdraw
staking where claim callback can reenter stake
bridge where lock callback can reenter unlock
yield aggregator where harvest callback can reenter deposit
options protocol where exercise callback can reenter mint
perpetuals where close callback can reenter open
lending where liquidation callback can reenter borrow
AMM where add liquidity callback can reenter remove
vault where redeem callback can reenter deposit
staking where withdraw callback can reenter claim
bridge where mint callback can reenter burn
yield protocol where compound callback can reenter withdraw
options where mint callback can reenter exercise
perpetuals where funding callback can reenter close
lending where repay callback can reenter liquidate
AMM where swap callback can reenter price calculation
vault where strategy callback can reenter user withdraw
staking where distribution callback can reenter unstake
```

### 3.3 Callback Chain Reentrancy
**CWE-841**

#### Detection Phrases
```
callback chain allowing reentry through multiple contract hops
external call triggering callback that reenters original contract
multi-hop callback creating reentrancy through intermediate contract
callback chain where intermediate contract enables reentry attack
external interaction starting callback sequence back to origin
multi-contract callback path creating reentrancy opportunity
callback triggering chain that returns to vulnerable function
external call starting callback loop through multiple contracts
multi-hop reentry through callback chain across protocols
callback sequence creating window for original contract attack
external interaction initiating callback path back to caller
multi-contract callback chain enabling state manipulation
callback triggering reentry through protocol integration
external call creating callback loop exploitable for reentrancy
multi-hop callback enabling attack on originating contract
callback chain through integrated protocols back to origin
external interaction starting multi-contract reentry path
callback sequence exploitable for cross-contract reentrancy
multi-hop callback creating attack vector on original state
callback chain through external protocols enabling reentry
```

---

## 4. Read-Only Reentrancy

### 4.1 View Function Exploitation
**CWE-841**

#### Detection Phrases
```
view functions returning state that can be stale during callback execution
external protocols reading contract state mid-execution via view calls
price or balance getters called by external contracts during state transition
view functions used for pricing that read storage modified by non-reentrant functions
getters returning intermediate state exploitable by external protocols
view functions exposing uncommitted state during callback window
external contracts reading stale state through view functions
getters returning values that will change after callback completes
view functions called by oracles during state transition
external protocols exploiting intermediate state via view calls
getters exposing state between external call and update
view functions returning manipulable state during callback
external contracts exploiting stale view function returns
getters called by lending protocols during borrower callback
view functions exposing accounting during distribution callback
external protocols reading manipulated state via view calls
getters returning total supply during mint callback exploitation
view functions called by AMM during swap callback
external contracts exploiting getters during liquidation callback
view functions exposing reserve state during flash loan callback
```

#### Detection Rules
```yaml
rule: read-only-reentrancy
conditions:
  all:
    - function.is_view == true
    - function.reads_state_variable: X
    - exists_function.writes_state_variable: X
    - exists_function.has_external_call_before_write_to: X
    - function.called_by_external_protocol == likely
severity: high
```

### 4.2 Price Oracle Exploitation
**CWE-841**

#### Detection Phrases
```
price getters returning manipulable value during callback
spot price view functions exploitable during flash loan
reserve-based price calculations stale during swap callback
price oracle getters called during state transition
exchange rate functions returning intermediate value during callback
price calculation view functions exploitable mid-transaction
oracle price getters reading manipulated reserves
price feed functions returning stale value during attack
exchange rate calculations exploitable via view function during callback
price oracle view functions called by external lending protocols
spot price getters exploitable during liquidity manipulation
reserve-based oracles stale during callback exploitation
price calculation functions returning manipulable values
oracle getters called during flash loan callback
exchange rate view functions exploitable during state transition
price feed calculations stale during reentry window
spot oracle getters returning intermediate prices
reserve ratio calculations exploitable via callback
price oracle functions called during multi-hop attack
exchange rate getters stale during flash mint callback
```

### 4.3 Balance/Share Exploitation
**CWE-841**

#### Detection Phrases
```
share price getters manipulable during callback
balance view functions returning stale during deposit callback
total supply getters exploitable during mint callback
share calculation view functions stale during redemption
balance queries returning intermediate during withdraw callback
total assets getters exploitable during harvest callback
share ratio calculations stale during strategy callback
balance view functions manipulable during flash loan
total supply queries exploitable during burn callback
share price calculations stale during deposit callback
balance getters returning intermediate during claim
total value getters exploitable during rebalance callback
share calculations stale during compound callback
balance queries manipulable during liquidation
total supply view functions exploitable during callback
share ratio getters returning intermediate values
balance calculations stale during distribution callback
total assets queries exploitable during exit callback
share price view functions manipulable during attack
balance getters stale during callback exploitation
```

---

## 5. ERC Token Reentrancy

### 5.1 ERC777 Hooks
**CWE-841**

#### Detection Phrases
```
ERC777 tokensToSend hook enabling reentrancy before transfer
ERC777 tokensReceived hook enabling reentrancy after receive
ERC777 send function allowing callback before balance update
ERC777 operatorSend enabling reentrancy via sender hook
ERC777 burn function with tokensToSend hook vulnerability
ERC777 transfer triggering sender callback before state change
ERC777 receive hook allowing reentry before balance credit
ERC777 send with sender hook before sender balance decrement
ERC777 transfer enabling receiver callback exploitation
ERC777 hooks creating reentrancy window in integrated protocols
ERC777 tokensToSend enabling attack before transfer completion
ERC777 tokensReceived enabling attack after balance credit
ERC777 operator functions with hook-based reentrancy
ERC777 mint with receiver hook vulnerability
ERC777 burn triggering sender hook before supply decrement
ERC777 transfer hooks exploitable in DeFi integrations
ERC777 send/receive hooks creating cross-contract reentrancy
ERC777 operator transfer with callback chain vulnerability
ERC777 hooks enabling read-only reentrancy exploitation
ERC777 token operations with hook-based state manipulation
```

### 5.2 ERC721 Callbacks
**CWE-841**

#### Detection Phrases
```
ERC721 safeTransferFrom with onERC721Received callback reentrancy
ERC721 safeMint triggering receiver callback before state update
ERC721 safe transfer allowing reentry via receiver hook
ERC721 safeTransferFrom enabling callback before ownership update
ERC721 safeMint with onERC721Received vulnerability
ERC721 safe functions triggering callbacks in loops
ERC721 batch transfer with per-item callback reentrancy
ERC721 safeMint allowing callback before tokenId increment
ERC721 safeTransferFrom with callback before balance update
ERC721 receiver callback enabling reentrancy in marketplace
ERC721 safeMint callback exploitable in minting function
ERC721 safe transfer with callback before approval clear
ERC721 batch operations with per-NFT callback vulnerability
ERC721 safeMint triggering callback before supply update
ERC721 safeTransferFrom allowing callback chain reentrancy
ERC721 receiver hook enabling state manipulation
ERC721 safe operations with callback before enumeration update
ERC721 batch mint with per-token callback vulnerability
ERC721 safeTransferFrom callback exploitable in auction
ERC721 safeMint with receiver callback before mapping update
```

### 5.3 ERC1155 Callbacks
**CWE-841**

#### Detection Phrases
```
ERC1155 safeTransferFrom with onERC1155Received callback reentrancy
ERC1155 safeBatchTransferFrom enabling callback reentrancy
ERC1155 mint triggering onERC1155Received before state update
ERC1155 batch transfer with callback before balance updates
ERC1155 safe transfer allowing reentry via receiver hook
ERC1155 safeMint with callback vulnerability
ERC1155 batch operations triggering onERC1155BatchReceived
ERC1155 transfer callback enabling state manipulation
ERC1155 safeBatchTransferFrom with loop callback vulnerability
ERC1155 mint callback exploitable before supply update
ERC1155 safe transfer with callback before approval check
ERC1155 batch mint triggering per-batch callback
ERC1155 receiver hook enabling reentrancy in game items
ERC1155 safeTransferFrom callback before id balance update
ERC1155 batch operations with callback chain vulnerability
ERC1155 safeMint triggering callback before total update
ERC1155 transfer allowing callback exploitation
ERC1155 batch callback enabling cross-function reentrancy
ERC1155 receiver hook exploitable in marketplace
ERC1155 safe operations with callback before metadata update
```

### 5.4 ERC4626 Vault Reentrancy
**CWE-841**

#### Detection Phrases
```
ERC4626 deposit with callback before share mint
ERC4626 withdraw triggering callback before share burn
ERC4626 redeem with callback before asset transfer
ERC4626 mint callback vulnerability before share credit
ERC4626 deposit enabling reentrancy via asset transfer callback
ERC4626 withdraw with callback before accounting update
ERC4626 convertToShares stale during deposit callback
ERC4626 convertToAssets manipulable during withdraw callback
ERC4626 totalAssets returning intermediate during callback
ERC4626 deposit callback enabling share inflation attack
ERC4626 withdraw callback before total supply update
ERC4626 preview functions stale during state transition
ERC4626 redeem callback enabling vault manipulation
ERC4626 mint triggering asset transfer with callback
ERC4626 deposit with asset callback before share calculation
ERC4626 withdraw enabling share price manipulation via callback
ERC4626 vault operations with underlying token callbacks
ERC4626 deposit callback exploitable for share inflation
ERC4626 redeem with callback before asset accounting
ERC4626 preview functions exploitable via read-only reentrancy
```

---

## 6. External Call Safety

### 6.1 Unchecked Return Values
**CWE-252**

#### Detection Phrases
```
low-level calls without checking return boolean
ERC20 transfer calls without verifying success
external calls where return value is ignored
send or transfer without handling false return
approve calls without checking return value
call return value not checked before proceeding
external function return not validated
low-level call success not verified
ERC20 transferFrom without return check
external call result discarded
call return boolean ignored in if statement
transfer return value not used
external interaction without success verification
low-level call without boolean capture
ERC20 approve return not checked
call success not required for continuation
external function result not validated
transfer result ignored allowing silent failure
call return not checked in conditional
ERC20 operations without return value handling
external call outcome not verified
low-level interaction without success check
transfer return value silently discarded
call result not captured or checked
ERC20 transfer assuming always succeeds
external call without failure handling
low-level call return not in require
transfer success not validated
external interaction return value lost
call boolean not used in control flow
```

#### Detection Rules
```yaml
rule: unchecked-return-value
conditions:
  all:
    - expression.is_external_call == true
    - expression.return_value_used == false
  or:
    - call.is_low_level_call == true
    - call.target_function IN [transfer, transferFrom, approve, send]
severity: high
```

### 6.2 Gas Stipend Issues
**CWE-400**

#### Detection Phrases
```
transfer or send failing due to 2300 gas limit
low-level call with hardcoded gas that may fail
external call with insufficient gas for recipient
transfer to contract failing on gas
send with 2300 gas to contract with logic
external call gas limit causing unexpected failure
transfer failing when recipient has receive logic
hardcoded gas limit in call expression
external interaction with gas stipend vulnerability
transfer to proxy failing on forwarding
send gas limit blocking legitimate operations
external call with gas parameter below required
transfer failing on gas with EIP-1884 changes
hardcoded gas in call breaking on network upgrade
external interaction failing due to gas stipend
transfer to multisig failing on signature verification
send gas limit insufficient for state changes
external call gas stipend causing silent failure
transfer failing when recipient needs computation
hardcoded gas causing call failure on gas repricing
```

### 6.3 Call Return Data Handling
**CWE-252**

#### Detection Phrases
```
call return data not decoded before use
external call returndata assumed to have specific length
low-level call return not checked for expected format
call return data decoded without length verification
external call returndata causing revert on decode
call return assumed to contain boolean
low-level call return decoded as wrong type
external call returndata overflow on decode
call return data not validated before abi.decode
external interaction return causing decode failure
low-level call return assumed non-empty
call returndata decoded without try-catch
external call return causing out-of-bounds read
call return data format not verified
low-level call returndata decoded unsafely
external call return causing revert in caller
call return data assumed to match interface
low-level call return not checked for emptiness
external call returndata causing panic on decode
call return data decoded with wrong selector assumption
```

---

## 7. Low-Level Call Patterns

### 7.1 Arbitrary Call Target
**CWE-20**

#### Detection Phrases
```
call or delegatecall with user-controlled target address
external calls with attacker-controlled calldata
functions forwarding arbitrary calls without whitelist
multicall patterns allowing arbitrary contract interactions
call target derived from user input without validation
low-level call to address from function parameter
external call with target from storage settable by user
call to arbitrary address with value transfer
low-level call forwarding user-provided calldata
external interaction with unvalidated target
call to address from mapping populated by users
low-level call target computable by attacker
external call with target from untrusted source
call to arbitrary contract with attacker data
low-level call forwarding without target whitelist
external interaction to user-specified address
call target from oracle controllable by attacker
low-level call with both target and data from user
external call to address derived from user bytes
call forwarding to arbitrary implementation
```

#### Detection Rules
```yaml
rule: arbitrary-call-target
conditions:
  all:
    - call.is_low_level == true
    - call.target_source IN [parameter, user_controllable_storage, calldata]
    - NOT call.target_validated_against_whitelist
severity: critical
flow_analysis:
  - trace: user_input -> call.target
```

### 7.2 Arbitrary Calldata
**CWE-20**

#### Detection Phrases
```
external calls with user-provided calldata without validation
low-level call forwarding attacker-controlled data
call with selector from user input
external interaction with arbitrary function selector
low-level call data constructed from user bytes
call forwarding full user calldata
external call with function selector from parameter
low-level call executing arbitrary function
call data including user-controlled selector
external interaction forwarding unvalidated calldata
low-level call with bytes parameter passed directly
call executing function selected by user
external call with full user bytes as data
low-level call allowing arbitrary function execution
call forwarding user data to trusted contract
external interaction with attacker-chosen selector
low-level call data from decoded user input
call with arbitrary method invocation
external call data constructed from user abi.encode
low-level call forwarding without selector validation
```

### 7.3 Value Forwarding Issues
**CWE-20**

#### Detection Phrases
```
call with msg.value forwarding without validation
external call forwarding full contract balance
low-level call with value from user-controlled calculation
call value derived from untrusted input
external interaction forwarding more value than intended
low-level call with value manipulation vulnerability
call forwarding ETH without amount validation
external call with value from attacker-influenced storage
low-level call value exceeding user deposit
call with value extraction through forwarding
external interaction with value from manipulable source
low-level call forwarding unintended amounts
call value derived from flash loan amounts
external call with value calculation overflow
low-level call forwarding accumulated fees incorrectly
call value from price oracle manipulation
external interaction forwarding borrowed funds
low-level call with value from stale balance
call forwarding value without slippage check
external call value exceeding protocol limits
```

---

## 8. Delegatecall Vulnerabilities

### 8.1 Arbitrary Delegatecall Target
**CWE-829**

#### Detection Phrases
```
delegatecall to address derived from user input
delegatecall to non-library contracts
delegatecall in proxy without proper implementation validation
functions using delegatecall that can be called by non-admin
delegatecall preserving msg.sender in untrusted context
delegatecall target from user-controlled storage
delegatecall to arbitrary implementation address
delegatecall with target from function parameter
delegatecall to address computable by attacker
delegatecall forwarding to unvalidated contract
delegatecall target derived from user bytes
delegatecall to implementation without ownership check
delegatecall with target from upgradeable storage slot
delegatecall to address from mapping settable by user
delegatecall forwarding without target whitelist
delegatecall to arbitrary logic contract
delegatecall target from oracle controllable by attacker
delegatecall to unverified implementation
delegatecall with target derived from calldata
delegatecall forwarding to user-specified address
```

#### Detection Rules
```yaml
rule: arbitrary-delegatecall
conditions:
  all:
    - call.is_delegatecall == true
    - call.target_source IN [parameter, user_controllable_storage, calldata]
    - NOT call.target_validated_against_whitelist
    - NOT call.in_proxy_upgrade_context
severity: critical
```

### 8.2 Delegatecall Storage Collision
**CWE-787**

#### Detection Phrases
```
delegatecall to contract with different storage layout
delegatecall overwriting unexpected storage slots
delegatecall to implementation with conflicting variables
delegatecall corrupting caller's storage
delegatecall to contract using same slots differently
delegatecall storage layout mismatch
delegatecall overwriting owner via storage collision
delegatecall to contract with additional storage variables
delegatecall corrupting state via slot collision
delegatecall to implementation without storage compatibility
delegatecall overwriting critical slots
delegatecall storage layout incompatibility
delegatecall to contract with inherited storage differences
delegatecall corrupting mappings via collision
delegatecall overwriting initialized values
delegatecall to implementation with slot conflicts
delegatecall storage ordering mismatch
delegatecall corrupting packed storage
delegatecall overwriting proxy admin slot
delegatecall storage collision with inherited contracts
```

### 8.3 Delegatecall Context Issues
**CWE-829**

#### Detection Phrases
```
delegatecall relying on msg.sender in wrong context
delegatecall with this address confusion
delegatecall misusing address(this) for authorization
delegatecall where target checks caller incorrectly
delegatecall preserving unexpected msg.value
delegatecall context confusion in access control
delegatecall where target assumes different caller
delegatecall msg.sender propagation exploitation
delegatecall preserving wrong execution context
delegatecall target assuming direct call context
delegatecall with balance confusion
delegatecall context affecting authorization checks
delegatecall msg.value passed to target unexpectedly
delegatecall preserving caller context incorrectly
delegatecall target checking msg.sender for self
delegatecall execution context mismatch
delegatecall preserving value in target function
delegatecall context confusion in callbacks
delegatecall target authorization based on wrong caller
delegatecall preserving tx.origin exploitation
```

---

## 9. Token Transfer Safety

### 9.1 ERC20 Transfer Issues
**CWE-252**

#### Detection Phrases
```
ERC20 transfer calls without SafeERC20 wrapper
transfer return value not checked for non-standard tokens
ERC20 transferFrom without return validation
approve not checking for non-compliant token
ERC20 transfer assuming boolean return
transferFrom success not verified
ERC20 operations on tokens with fee-on-transfer
transfer to tokens with blacklist functionality
ERC20 approve with non-standard increase/decrease
transferFrom on rebasing tokens without accounting
ERC20 transfer on deflationary tokens
approve race condition not mitigated
ERC20 operations on tokens with transfer hooks
transfer on tokens returning false instead of reverting
ERC20 transferFrom on tokens with max transfer limits
approve on tokens with allowance requirements
ERC20 operations without SafeERC20.safeTransfer
transfer success assumed on non-standard tokens
ERC20 approval on tokens requiring zero first
transferFrom on tokens with pausable functionality
```

### 9.2 Token Approval Vulnerabilities
**CWE-362**

#### Detection Phrases
```
approve function vulnerable to front-running race condition
allowance update without checking current value
approval race condition allowing double-spend
approve not using increase/decrease allowance
allowance change front-runnable for theft
approval without reset to zero first
allowance manipulation via race condition
approve vulnerable to approval racing
allowance update front-runnable by spender
approval race allowing more than intended
allowance race condition on decrease
approve not atomic with transfer
allowance racing between approve calls
approval front-run extracting extra tokens
allowance manipulation window
approve race condition exploitation
allowance update without previous consumption check
approval racing to drain extra tokens
allowance front-running to double-spend
approve not checking unconsumed allowance
```

### 9.3 Fee-on-Transfer Handling
**CWE-682**

#### Detection Phrases
```
fee-on-transfer tokens not handled in swap calculations
transfer amount assumed without balance check
deflationary token transfer not accounting for fee
token transfer assuming amount equals received
fee-on-transfer breaking accounting invariants
transfer fee not deducted from expected amount
deflationary token not handled in deposit
amount transferred not validated post-transfer
fee-on-transfer corrupting internal balances
transfer assuming received equals sent
deflationary token breaking liquidity accounting
amount credited without post-transfer verification
fee-on-transfer causing share calculation errors
transfer fee not considered in vault deposits
deflationary token causing withdraw shortfall
received amount not checked after transfer
fee-on-transfer breaking swap output calculations
transfer amount discrepancy not handled
deflationary token corrupting pool reserves
amount received different from amount sent not handled
```

---

## 10. Token Accounting Issues

### 10.1 Balance vs Internal Accounting
**CWE-682**

#### Detection Phrases
```
direct balance queries instead of internal accounting
using balanceOf instead of internal balance mapping
external balance check vulnerable to manipulation
direct token balance used for calculations
balanceOf call instead of tracked deposits
external balance query in value calculations
direct balance check for share pricing
balanceOf used for collateral valuation
external balance vulnerable to donation attack
direct balance query for reward calculations
balanceOf check for withdrawal limits
external balance used for exchange rate
direct balance for liquidity calculations
balanceOf query for pool share pricing
external balance check exploitable via transfer
direct balance used in swap calculations
balanceOf for position valuation
external balance query manipulable via flash loan
direct balance check for vault share price
balanceOf used instead of internal tracking
```

#### Detection Rules
```yaml
rule: balance-vs-accounting
conditions:
  all:
    - expression.is_balance_query == true
    - expression.target IN [address(this), contract_address]
    - expression.used_in_calculation == true
    - NOT contract.has_internal_balance_tracking
severity: medium
```

### 10.2 Share Calculation Issues
**CWE-682**

#### Detection Phrases
```
share calculations vulnerable to first depositor inflation
vault share price manipulable by initial deposit
share calculation with rounding exploitation
first deposit share inflation attack
vault initialization vulnerable to share manipulation
share price attackable via small initial deposit
total shares calculation with precision loss
first depositor able to steal from subsequent
share ratio manipulation at vault creation
initial deposit share calculation vulnerability
vault share inflation via donation before deposit
share calculation rounding favoring attacker
first minter share manipulation
vault share price set by initial tiny deposit
share calculation allowing extraction via rounding
initial deposit exploitable for share inflation
vault share dilution attack
share ratio manipulation via flash loan
first depositor share attack in empty vault
share calculation precision loss exploitation
```

### 10.3 Supply Accounting Issues
**CWE-682**

#### Detection Phrases
```
mint and burn operations with inconsistent total supply updates
total supply not updated on mint
burn not decrementing total supply
supply accounting out of sync with balances
mint increasing balance without supply update
burn reducing balance without supply sync
total supply overflow on mint
supply underflow on burn
minting without total supply increment
burning without supply decrement
total supply not reflecting actual tokens
mint and burn supply accounting mismatch
supply tracking inconsistent with balance sum
mint failing to update cached supply
burn not adjusting supply variable
total supply stale after mint/burn
supply accounting skipped in some paths
mint with conditional supply update
burn missing supply decrement
total supply diverging from token balances
```

---

## 11. Value Extraction Patterns

### 11.1 Withdrawal Vulnerabilities
**CWE-284**

#### Detection Phrases
```
withdrawal functions without balance sufficiency check
withdraw allowing more than deposited
withdrawal not validating available balance
withdraw exceeding user balance possible
withdrawal without checking claimable amount
withdraw allowing negative balance
withdrawal not enforcing deposit limits
withdraw of unvested amounts
withdrawal from wrong user balance
withdraw without time lock check
withdrawal bypassing withdrawal delay
withdraw during cooldown period
withdrawal not checking freeze status
withdraw from locked position
withdrawal of staked tokens before unlock
withdraw without penalty application
withdrawal ignoring withdrawal fee
withdraw exceeding withdrawal limit
withdrawal from paused state
withdraw without slashing application
```

### 11.2 Deposit Vulnerabilities
**CWE-682**

#### Detection Phrases
```
deposit crediting wrong amount
deposits not validated for minimum
deposit accounting for wrong token
deposits allowing zero amount
deposit crediting before transfer confirmation
deposits not checking maximum
deposit from wrong source address
deposits allowing during paused state
deposit not enforcing whitelist
deposits crediting inflated amounts
deposit without rate limiting
deposits not checking token blacklist
deposit allowing flash deposit-withdraw
deposits vulnerable to sandwich
deposit not enforcing deadline
deposits accepting wrong token type
deposit without balance verification
deposits allowing reentrancy exploitation
deposit crediting more than received
deposits not handling deflationary tokens
```

---

## 12. Flash Loan Interactions

### 12.1 Flash Loan Callback Safety
**CWE-362**

#### Detection Phrases
```
flash loan callback without proper validation
callback accepting calls from arbitrary flashers
flash loan callback not verifying initiator
callback without checking loan amount
flash loan callback exploitable for reentrancy
callback not validating expected parameters
flash loan callback from untrusted source
callback without fee verification
flash loan callback not checking repayment
callback allowing state manipulation during loan
flash loan callback from wrong pool
callback not enforcing same-transaction rule
flash loan callback state check bypassable
callback without loan token verification
flash loan callback enabling price manipulation
callback not validating callback data
flash loan callback from impersonated source
callback allowing partial repayment
flash loan callback without balance check
callback enabling governance manipulation
```

### 12.2 Flash Loan Protected Operations
**CWE-362**

#### Detection Phrases
```
operations vulnerable to flash loan manipulation
governance votes during flash loan possible
oracle prices manipulable via flash loan
collateral valuation attackable with flash loan
share calculations exploitable via flash loan
reward distribution manipulable with flash loan
liquidation thresholds attackable via flash loan
price oracle not protected from flash loan
balance-based calculations vulnerable to flash loan
voting power inflatable via flash loan
collateral ratio manipulable with flash loan
interest calculations exploitable via flash loan
pool weights attackable via flash loan
reserve calculations vulnerable to flash loan
staking rewards manipulable with flash loan
governance quorum achievable via flash loan
price impact exploitable with flash loan
vault share price attackable via flash loan
liquidity depth manipulable with flash loan
fee calculations vulnerable to flash loan manipulation
```

---

## Complex Query Examples for Value Movement Lens

### Query 1: Reentrancy Risk Detection
```json
{
  "query_kind": "logic",
  "node_types": ["Function"],
  "match": {
    "all": [
      {"property": "visibility", "op": "in", "value": ["public", "external"]},
      {"property": "has_external_call", "op": "eq", "value": true},
      {"property": "writes_state", "op": "eq", "value": true},
      {"property": "has_reentrancy_guard", "op": "eq", "value": false}
    ]
  },
  "edges": [{
    "edge_type": "CALLS_EXTERNAL",
    "sequence_constraint": "before_state_write",
    "constraints": {
      "call_type_in": ["call", "delegatecall", "transfer", "send"]
    }
  }],
  "explain_mode": true,
  "limit": 50
}
```

### Query 2: Cross-Function Reentrancy
```json
{
  "query_kind": "logic",
  "node_types": ["Contract"],
  "match": {
    "all": [
      {"property": "has_functions_sharing_state", "op": "eq", "value": true}
    ]
  },
  "paths": [
    {
      "from": {"function_has": "external_call_before_state_write"},
      "edge_type": "SHARES_STATE_WITH",
      "to": {"function_has": "reads_same_state"},
      "constraint": "neither_has_reentrancy_guard"
    }
  ],
  "explain_mode": true
}
```

### Query 3: Unchecked External Calls
```json
{
  "query_kind": "logic",
  "node_types": ["Function"],
  "match": {
    "any": [
      {
        "all": [
          {"property": "has_low_level_call", "op": "eq", "value": true},
          {"property": "checks_return_value", "op": "eq", "value": false}
        ]
      },
      {
        "all": [
          {"property": "calls_erc20_transfer", "op": "eq", "value": true},
          {"property": "uses_safe_erc20", "op": "eq", "value": false}
        ]
      }
    ]
  },
  "explain_mode": true
}
```

### Query 4: Token Callback Reentrancy
```json
{
  "query_kind": "logic",
  "node_types": ["Function"],
  "match": {
    "all": [
      {"property": "interacts_with_token_type", "op": "in", "value": ["ERC777", "ERC721", "ERC1155", "ERC4626"]},
      {"property": "writes_state_after_token_interaction", "op": "eq", "value": true},
      {"property": "has_reentrancy_guard", "op": "eq", "value": false}
    ]
  },
  "explain_mode": true
}
```

### Query 5: Read-Only Reentrancy Surface
```json
{
  "query_kind": "logic",
  "node_types": ["Function"],
  "match": {
    "all": [
      {"property": "is_view", "op": "eq", "value": true},
      {"property": "reads_state_modified_by_nonreentrant", "op": "eq", "value": true},
      {"property": "likely_called_by_external_protocol", "op": "eq", "value": true}
    ]
  },
  "context": {
    "exists_function": {
      "has_external_call_before_modifying": "same_state_variable"
    }
  },
  "explain_mode": true
}
```

---

## Pattern Pack: Value Movement Lens Complete

```yaml
# Save as patterns/value-movement-lens.yaml
patterns:
  - id: vm-001
    name: Classic Reentrancy - State Before External
    severity: critical
    cwe: [841]

  - id: vm-002
    name: ETH Transfer Reentrancy
    severity: critical
    cwe: [841]

  - id: vm-003
    name: Cross-Function Reentrancy
    severity: high
    cwe: [841, 362]

  - id: vm-004
    name: Read-Only Reentrancy
    severity: high
    cwe: [841]

  - id: vm-005
    name: ERC Token Callback Reentrancy
    severity: high
    cwe: [841]

  - id: vm-006
    name: Unchecked Low-Level Call
    severity: high
    cwe: [252]

  - id: vm-007
    name: Unchecked ERC20 Transfer
    severity: high
    cwe: [252]

  - id: vm-008
    name: Arbitrary Delegatecall
    severity: critical
    cwe: [829]

  - id: vm-009
    name: Approval Race Condition
    severity: medium
    cwe: [362]

  - id: vm-010
    name: First Depositor Share Inflation
    severity: high
    cwe: [682]

  - id: vm-011
    name: Flash Loan Price Manipulation
    severity: critical
    cwe: [362]

  - id: vm-012
    name: Balance vs Internal Accounting
    severity: medium
    cwe: [682]
```
