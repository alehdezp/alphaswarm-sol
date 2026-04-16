# Liveness Lens - Ultra-Expanded Detection Patterns

> Comprehensive denial of service, gas exhaustion, griefing, and availability
> vulnerability detection for AlphaSwarm.sol

---

## Table of Contents
1. [Gas Limit DoS](#1-gas-limit-dos)
2. [Block Gas Limit Exhaustion](#2-block-gas-limit-exhaustion)
3. [Unbounded Operations](#3-unbounded-operations)
4. [Griefing Attacks](#4-griefing-attacks)
5. [External Call Failures](#5-external-call-failures)
6. [Unexpected Revert Conditions](#6-unexpected-revert-conditions)
7. [Storage DoS](#7-storage-dos)
8. [Economic DoS](#8-economic-dos)
9. [State Machine DoS](#9-state-machine-dos)
10. [Resource Exhaustion](#10-resource-exhaustion)
11. [Locking & Freezing](#11-locking--freezing)
12. [Recovery & Emergency Mechanisms](#12-recovery--emergency-mechanisms)

---

## 1. Gas Limit DoS

### 1.1 Loop-Based Gas Exhaustion
**CWE-400** (Uncontrolled Resource Consumption)

#### Detection Phrases (NL Queries)
```
loops iterating over unbounded arrays
external calls inside loops without gas limits
functions processing user-controlled array length
batch operations without pagination or size limits
storage writes in loops that grow with user actions
for loops with dynamic upper bound from storage
while loops with user-controllable termination condition
iteration over mapping keys without bound
loops processing unbounded token holder list
batch transfers iterating over recipient array without limit
loops with external calls per iteration
iteration over user-supplied array without length cap
for loops over storage array with no maximum
while loops dependent on external state for termination
batch operations processing unlimited items
loops writing storage on each iteration
iteration over growing array without pagination
for loops making external calls unbounded times
while loops with attacker-controlled continuation
batch processing without gas checkpoints
loops iterating over all depositors
iteration over unbounded staker list
for loops over all token holders
while loops processing accumulated entries
batch claiming iterating all pending claims
loops with storage reads per iteration
iteration over all liquidity providers
for loops over all position holders
while loops processing entire queue
batch operations over all participants
loops over all approved addresses
iteration over all delegators
for loops processing all votes
while loops over all proposals
batch reward distribution to all users
loops iterating all historical entries
iteration over all registered addresses
for loops over all pool participants
while loops processing all pending transactions
batch processing all accumulated rewards
```

#### Detection Rules
```yaml
rule: loop-gas-exhaustion
conditions:
  all:
    - function.has_loop == true
    - OR:
      - loop.bound_source == storage_array_length
      - loop.bound_source == user_input
      - loop.bound_source == dynamic_calculation
    - loop.contains_gas_intensive_operation == true
  gas_intensive_operations:
    - external_call
    - storage_write
    - storage_read_in_calculation
    - event_emission
severity: high
```

### 1.2 Nested Loop Complexity
**CWE-400**

#### Detection Phrases
```
nested loops with multiplicative iteration count
double iteration over storage arrays
nested loops with external calls in inner loop
multiple loops over same unbounded data
nested iteration with storage operations
double for loop over user arrays
nested while loops with dynamic bounds
multiple nested iterations without limit
nested loops with quadratic complexity
double iteration causing gas explosion
nested for loops over all pairs
multiple loops with storage writes in each
nested iteration over token holders
double while loop with external calls
nested loops processing all combinations
multiple iterations with unbounded inner loop
nested for loops without combined limit
double iteration over all positions
nested loops with O(n²) complexity
multiple nested iterations over mappings
nested for loops over participants
double iteration causing DoS potential
nested loops without gas consideration
multiple iterations with quadratic growth
nested for loops over all voters
double iteration over all stakers
nested loops causing exponential gas
multiple nested loops without bound
nested iteration without complexity limit
double for loop over all entries
```

### 1.3 Dynamic Gas Consumption
**CWE-400**

#### Detection Phrases
```
gas consumption dependent on input size
variable gas usage based on user data
dynamic gas cost from array length
gas consumption scaling with input
variable operation count from user input
dynamic gas based on storage state
gas usage growing with accumulated data
variable gas cost per transaction
dynamic gas consumption unbounded
gas usage dependent on historical growth
variable operation count unbounded
dynamic gas from batch size
gas consumption scaling with time
variable gas usage from queue length
dynamic gas cost from pending operations
gas usage dependent on user activity
variable gas consumption from storage growth
dynamic operation count unbounded
gas usage scaling with deposit count
variable gas cost from claim history
dynamic gas consumption from stake count
gas usage dependent on delegation depth
variable gas from governance participation
dynamic gas cost unbounded
gas consumption from accumulated votes
variable gas usage from position count
dynamic gas consumption scaling
gas usage from historical transactions
variable gas cost from reward epochs
dynamic gas consumption from liquidity events
```

---

## 2. Block Gas Limit Exhaustion

### 2.1 Transaction Size Attacks
**CWE-400**

#### Detection Phrases
```
functions that can exceed block gas limit with large inputs
withdrawal patterns requiring iteration over all depositors
state cleanup requiring unbounded deletions
reward distribution iterating all stakers in single transaction
single transaction processing exceeding block limit
function requiring all users in one call
withdrawal processing all pending in single tx
state update requiring full iteration
reward calculation for all stakers at once
single call processing unbounded recipients
function requiring complete data processing
withdrawal iteration exceeding block gas
state cleanup in single transaction
reward distribution requiring full pass
single transaction over all participants
function processing entire user base
withdrawal requiring complete iteration
state transition processing all entries
reward claiming for all in one tx
single call iterating entire storage
function exceeding practical gas limits
withdrawal processing blocking on size
state update requiring complete pass
reward distribution exceeding block limit
single transaction processing all holders
function requiring unbounded gas
withdrawal iteration causing block limit hit
state cleanup exceeding gas limit
reward calculation requiring full iteration
single call over all depositors
```

### 2.2 Batch Operation Limits
**CWE-400**

#### Detection Phrases
```
batch operations without maximum size limit
multi-transfer without recipient cap
batch processing without pagination
multi-call without operation limit
batch withdraw without size restriction
multi-send without recipient maximum
batch claim without item cap
multi-operation without gas checkpoint
batch distribution without pagination
multi-transfer exceeding practical limits
batch processing without chunking
multi-call without batch size validation
batch operation unbounded by design
multi-send without safe iteration
batch claim without operation limit
multi-operation exceeding block gas
batch distribution without maximum
multi-transfer without chunking support
batch processing requiring all at once
multi-call without size restriction
batch withdraw without pagination
multi-send exceeding gas limits
batch claim without chunking
multi-operation without maximum items
batch distribution without safe limits
multi-transfer requiring single transaction
batch processing exceeding limits
multi-call without maximum batch
batch operation without gas consideration
multi-send without operation cap
```

### 2.3 State Growth Attacks
**CWE-400**

#### Detection Phrases
```
storage arrays growing without bounds
mapping with unlimited key growth
state accumulation without cleanup mechanism
storage growth from user actions unbounded
arrays appended without size limit
mapping entries accumulating forever
state growth without expiration
storage expansion from deposits unlimited
arrays growing with each transaction
mapping accumulating without removal
state growth causing iteration issues
storage arrays without maximum length
mapping entries without cleanup
state accumulation breaking functions
storage growth without bounds check
arrays expanding without limit
mapping growing without pruning
state growth affecting gas costs
storage expansion without cap
arrays accumulating without removal
mapping entries growing unbounded
state growth without size limit
storage arrays causing DoS over time
mapping accumulation without expiration
state growth breaking withdrawal
storage expansion unlimited
arrays growing causing gas issues
mapping entries without limit
state accumulation without cleanup
storage growth without management
```

---

## 3. Unbounded Operations

### 3.1 Unbounded Array Operations
**CWE-400**

#### Detection Phrases
```
array iteration without length limit
array operations on growing storage
array processing without pagination
array iteration over all elements
array operations without chunking
array processing scaling with size
array iteration without gas checkpoint
array operations on unbounded storage
array processing without maximum
array iteration causing gas issues
array operations without size validation
array processing all elements required
array iteration without safe bounds
array operations causing DoS
array processing without limit
array iteration over storage array
array operations requiring full pass
array processing without pagination support
array iteration without chunking
array operations on unlimited array
array processing causing gas exhaustion
array iteration over all entries
array operations without gas consideration
array processing requiring complete iteration
array iteration unbounded
array operations scaling linearly
array processing without safe iteration
array iteration causing block limit
array operations without bound
array processing over all items
```

### 3.2 Unbounded Mapping Iterations
**CWE-400**

#### Detection Phrases
```
iteration over mapping keys without limit
mapping enumeration requiring all keys
iteration over all mapping entries
mapping traversal without bound
iteration requiring mapping key list
mapping enumeration unbounded
iteration over stored key array for mapping
mapping traversal causing gas issues
iteration over mapping without pagination
mapping enumeration requiring full pass
iteration over all stored keys
mapping traversal without chunking
iteration requiring complete mapping pass
mapping enumeration scaling with entries
iteration over mapping key storage
mapping traversal without limit
iteration requiring all mapping values
mapping enumeration without gas checkpoint
iteration over unbounded key set
mapping traversal requiring single transaction
iteration over mapping without bound
mapping enumeration causing DoS
iteration requiring complete key iteration
mapping traversal without safe bounds
iteration over all mapping keys
mapping enumeration without pagination
iteration requiring full mapping read
mapping traversal causing gas exhaustion
iteration over mapping causing block limit
mapping enumeration without chunking
```

### 3.3 Unbounded String/Bytes Operations
**CWE-400**

#### Detection Phrases
```
string operations on unbounded input
bytes processing without length limit
string concatenation in loops
bytes operations on user data unbounded
string manipulation without size cap
bytes processing scaling with input size
string operations in storage without limit
bytes manipulation unbounded
string concatenation without length check
bytes operations on large input
string processing without maximum
bytes manipulation without gas consideration
string operations causing gas issues
bytes processing without bound
string concatenation growing unbounded
bytes operations without size limit
string manipulation in loop
bytes processing causing gas exhaustion
string operations on unlimited input
bytes manipulation without limit
string concatenation without cap
bytes operations without length validation
string processing causing DoS
bytes manipulation on large data
string operations without bound
bytes processing unbounded
string manipulation without maximum
bytes operations scaling with size
string processing without size check
bytes manipulation causing gas issues
```

---

## 4. Griefing Attacks

### 4.1 Push Payment Griefing
**CWE-400**

#### Detection Phrases
```
push-based payments that revert on receiver failure
transfer to recipient that can reject
push payment without pull alternative
transfer failing if recipient reverts
push payment to arbitrary address
transfer blocked by malicious recipient
push payment without fallback mechanism
transfer vulnerable to receiver rejection
push payment allowing grief
transfer to contract that reverts
push payment without receive handling
transfer dependent on recipient acceptance
push payment griefable by recipient
transfer failing on recipient revert
push payment without retry mechanism
transfer vulnerable to griefing recipient
push payment blocking subsequent operations
transfer to rejecting contract
push payment without handling failure
transfer blocked by recipient fallback
push payment to attacker-controlled address
transfer failing blocking function
push payment without isolation
transfer vulnerable to malicious receiver
push payment griefing vector
transfer failing preventing completion
push payment without safe handling
transfer to contract without receive
push payment allowing blocking
transfer griefable by receiver
```

#### Detection Rules
```yaml
rule: push-payment-griefing
conditions:
  all:
    - function.has_push_payment == true
    - function.payment_recipient_controllable == true
    - OR:
      - function.handles_transfer_failure == false
      - function.has_pull_payment_alternative == false
severity: medium
```

### 4.2 Auction Griefing
**CWE-400**

#### Detection Phrases
```
auctions where highest bidder can grief by rejecting refunds
bid refund failing blocking next bid
auction griefable via refund rejection
bid return to previous bidder reverts
auction blocked by griefing bidder
bid refund via push payment
auction vulnerable to bid rejection
bid return failing halting auction
auction griefable by malicious bidder
bid refund without handling failure
auction blocked by rejecting previous
bid return dependent on bidder acceptance
auction vulnerable to refund grief
bid rejection blocking auction
auction griefable via contract bidder
bid refund failing preventing overbid
auction blocked by refund revert
bid return vulnerable to griefing
auction halted by malicious refund
bid refund without pull mechanism
auction griefable by smart contract
bid rejection halting auction progress
auction blocked by previous bidder
bid return grief vector
auction vulnerable to blocking bid
bid refund failure blocking function
auction griefable via rejecting receive
bid return to contract without receive
auction blocked by bid refund failure
bid rejection causing auction halt
```

### 4.3 Callback Griefing
**CWE-400**

#### Detection Phrases
```
callbacks that revert blocking protocol operations
callback failure blocking caller
callback revert halting function
callback griefable by receiver
callback failure preventing completion
callback revert blocking subsequent code
callback griefable via malicious contract
callback failure halting protocol
callback revert causing DoS
callback griefable by attacker
callback failure blocking operations
callback revert preventing state update
callback griefable via contract logic
callback failure causing halt
callback revert blocking function completion
callback griefable by recipient
callback failure causing DoS
callback revert halting processing
callback griefable via receive rejection
callback failure blocking caller operation
callback revert causing function failure
callback griefable by target contract
callback failure halting batch
callback revert blocking iteration
callback griefable via fallback revert
callback failure causing operation halt
callback revert blocking protocol
callback griefable by hook implementation
callback failure preventing operation
callback revert causing grief
```

### 4.4 State Manipulation Griefing
**CWE-400**

#### Detection Phrases
```
state changes allowing grief by front-running
state manipulation blocking legitimate users
state griefable via timing attack
state changes front-runnable for grief
state manipulation causing legitimate tx failure
state griefable via sandwich
state changes allowing blocking attack
state manipulation via front-run grief
state griefable by attacker transaction
state changes allowing DoS via timing
state manipulation blocking subsequent users
state griefable via transaction ordering
state changes front-runnable for DoS
state manipulation causing user lockout
state griefable via MEV
state changes allowing manipulation
state manipulation blocking valid operations
state griefable via block manipulation
state changes causing grief opportunity
state manipulation via ordering attack
state griefable by malicious transaction
state changes blocking legitimate access
state manipulation causing DoS
state griefable via timing manipulation
state changes front-runnable for blocking
state manipulation preventing user action
state griefable via transaction insertion
state changes causing legitimate failure
state manipulation via front-running
state griefable by state change
```

---

## 5. External Call Failures

### 5.1 External Call Dependency
**CWE-754**

#### Detection Phrases
```
require statements depending on external contract state
function success dependent on external call
critical path blocked by external failure
function requiring external contract response
critical operation dependent on external state
function blocked by external revert
critical path requiring external success
function dependent on external availability
critical operation blocked by external
function requiring external contract availability
critical path dependent on external response
function blocked by external contract state
critical operation requiring external success
function dependent on external contract
critical path blocked by external failure
function requiring external response
critical operation dependent on external availability
function blocked by external state
critical path requiring external call success
function dependent on external contract response
critical operation blocked by external revert
function requiring external availability
critical path dependent on external call
function blocked by external contract failure
critical operation requiring external contract
function dependent on external success
critical path blocked by external contract
function requiring external state
critical operation dependent on external response
function blocked by external call failure
```

### 5.2 Cascading Failures
**CWE-754**

#### Detection Phrases
```
single external failure blocking multiple operations
cascade of failures from external revert
single point of failure in external call
cascade causing protocol-wide halt
single external blocking critical functions
cascade from external dependency failure
single failure propagating through protocol
cascade of reverts from external call
single external causing system-wide DoS
cascade blocking multiple users
single failure in external preventing operations
cascade from external contract failure
single external blocking withdrawals
cascade of failures blocking protocol
single point blocking all operations
cascade from external state dependency
single external failure halting protocol
cascade blocking critical operations
single failure causing protocol DoS
cascade from external call dependency
single external blocking deposits
cascade of failures from external
single point causing cascading failure
cascade blocking user operations
single external causing multiple failures
cascade from external dependency
single failure blocking protocol functions
cascade causing system halt
single external creating cascading DoS
cascade blocking protocol operations
```

### 5.3 External Call Gas Forwarding
**CWE-400**

#### Detection Phrases
```
external calls forwarding all remaining gas
call passing unlimited gas to external
external call without gas limit
call forwarding gas without restriction
external call allowing gas drain
call passing all gas to untrusted
external call without gas cap
call forwarding unlimited gas
external call gas forwarding unrestricted
call passing gas without limit
external call allowing callee gas consumption
call forwarding all gas unrestricted
external call without gas restriction
call passing excessive gas
external call gas forwarded completely
call without gas limit to external
external call forwarding without bound
call passing remaining gas to external
external call allowing unlimited gas use
call forwarding gas to untrusted contract
external call without specifying gas
call passing all remaining gas
external call gas unrestricted
call forwarding gas without cap
external call allowing gas exhaustion
call passing gas without restriction
external call forwarding all gas
call without gas bound to external
external call gas forwarding unbounded
call passing unlimited gas to untrusted
```

---

## 6. Unexpected Revert Conditions

### 6.1 Division by Zero
**CWE-754**

#### Detection Phrases
```
division operations that can divide by zero
divisor not checked before division
division with potentially zero denominator
divisor from user input not validated
division by zero possible in calculation
divisor could be zero from state
division without zero check on divisor
divisor potentially zero from formula
division operation with unchecked denominator
divisor from storage possibly zero
division by zero in financial calculation
divisor not validated nonzero
division with denominator from input
divisor could be zero causing revert
division without divisor validation
divisor from calculation possibly zero
division by zero risk in formula
divisor not checked for zero value
division with potentially zero value
divisor from parameter not validated
division operation risking revert
divisor could be zero from state
division without checking denominator
divisor potentially zero in path
division by zero causing transaction failure
divisor from external call potentially zero
division with unchecked zero possibility
divisor not ensured nonzero
division operation with zero risk
divisor from mapping possibly zero
```

#### Detection Rules
```yaml
rule: division-by-zero
conditions:
  all:
    - expression.has_division == true
    - expression.divisor_source IN [parameter, storage, calculation]
    - NOT expression.divisor_validated_nonzero
severity: medium
```

### 6.2 Array Bounds Issues
**CWE-119**

#### Detection Phrases
```
array access without bounds checking
index exceeding array length possible
array access with unchecked index
index from user input without validation
array access risking out of bounds
index potentially exceeding length
array access without length check
index from parameter without bounds
array access with unvalidated index
index from storage potentially invalid
array access risking revert
index not checked against length
array access without index validation
index from calculation possibly invalid
array access with unchecked bounds
index from external source unvalidated
array access risking out of bounds revert
index potentially larger than array
array access without bounds validation
index from user not checked
array access with invalid index risk
index exceeding array possible
array access without checking length
index from input without bounds check
array access risking index error
index not validated against array
array access with potentially invalid index
index from mapping possibly invalid
array access without index bounds check
index exceeding bounds possible
```

### 6.3 Assert vs Require
**CWE-754**

#### Detection Phrases
```
assert statements that consume all gas on failure
assert used for input validation
assert consuming gas on violation
assert used instead of require
assert causing full gas consumption
assert for user input checking
assert statement in validation path
assert causing gas drain on failure
assert used for parameter validation
assert consuming gas on invalid input
assert in user-facing function
assert causing excessive gas use
assert for external input validation
assert statement consuming all gas
assert used in validation logic
assert causing gas consumption on revert
assert for user-provided data
assert in input validation path
assert consuming remaining gas
assert used for runtime validation
assert causing gas waste on failure
assert for user input checking
assert statement in public function
assert causing gas drain
assert used where require appropriate
assert consuming gas on condition failure
assert in validation context
assert causing full gas use on revert
assert for input bounds checking
assert consuming gas inappropriately
```

### 6.4 Underflow/Overflow Reverts
**CWE-190, CWE-191**

#### Detection Phrases
```
arithmetic overflow causing revert in Solidity 0.8+
subtraction underflow reverting transaction
arithmetic overflow in calculation reverting
subtraction causing revert on underflow
arithmetic operation reverting on overflow
subtraction underflow in user-facing function
arithmetic overflow blocking transaction
subtraction reverting when minuend smaller
arithmetic causing revert on edge case
subtraction underflow blocking operation
arithmetic overflow from large inputs
subtraction reverting unexpectedly
arithmetic causing transaction failure
subtraction underflow in critical path
arithmetic overflow in fee calculation
subtraction causing revert in withdrawal
arithmetic causing unexpected revert
subtraction underflow blocking critical function
arithmetic overflow from user input
subtraction reverting blocking operations
arithmetic causing revert on boundary
subtraction underflow in calculation
arithmetic overflow blocking function
subtraction causing unexpected failure
arithmetic causing revert in public function
subtraction underflow reverting transaction
arithmetic overflow in public function
subtraction causing operation revert
arithmetic causing revert on large values
subtraction underflow causing DoS
```

---

## 7. Storage DoS

### 7.1 Storage Slot Exhaustion
**CWE-400**

#### Detection Phrases
```
storage arrays growing without cleanup
mapping entries accumulating without removal
storage growth unlimited over time
mapping keys never deleted
storage accumulation without pruning
mapping entries permanent
storage growth causing iteration issues
mapping without entry removal
storage arrays without deletion mechanism
mapping accumulating forever
storage growth without size management
mapping entries without cleanup
storage unlimited growth potential
mapping without pruning mechanism
storage arrays accumulating
mapping growth without removal
storage growing unbounded
mapping entries without deletion
storage accumulation over time
mapping without cleanup function
storage growth without expiration
mapping entries permanent by design
storage arrays without cleanup
mapping growing without limit
storage growth causing problems
mapping without entry expiration
storage accumulation without management
mapping entries never removed
storage growing without bounds
mapping without deletion capability
```

### 7.2 Storage Cost Attacks
**CWE-400**

#### Detection Phrases
```
storage writes paid by protocol not user
storage allocation subsidized
storage writes without user cost
storage allocation paid by contract
storage writes free for attacker
storage allocation without payment
storage writes enabling free storage attack
storage allocation subsidized by protocol
storage writes without cost to caller
storage allocation free to user
storage writes paid by fees not user
storage allocation without direct cost
storage writes enabling griefing
storage allocation paid from reserves
storage writes without proper cost
storage allocation enabling attack
storage writes subsidized for users
storage allocation without caller payment
storage writes enabling spam
storage allocation paid by contract balance
storage writes without user payment
storage allocation subsidized attack vector
storage writes free to attacker
storage allocation without cost enforcement
storage writes enabling storage attack
storage allocation paid by protocol funds
storage writes without cost to attacker
storage allocation free for griefing
storage writes subsidized enabling attack
storage allocation without proper payment
```

### 7.3 Storage Cleanup Failures
**CWE-400**

#### Detection Phrases
```
storage cleanup consuming excessive gas
deletion requiring iteration over all entries
storage cleanup blocked by gas limits
deletion consuming more gas than available
storage cleanup requiring multiple transactions
deletion exceeding block gas limit
storage cleanup not possible in single tx
deletion requiring unbounded gas
storage cleanup failing on large data
deletion blocked by accumulated entries
storage cleanup exceeding practical limits
deletion requiring excessive gas
storage cleanup not feasible
deletion consuming too much gas
storage cleanup blocked by size
deletion requiring unbounded iterations
storage cleanup exceeding block limit
deletion blocked by growth
storage cleanup not achievable
deletion consuming more than block gas
storage cleanup failing due to size
deletion blocked by accumulated data
storage cleanup exceeding limits
deletion requiring more gas than available
storage cleanup not possible
deletion consuming excessive gas
storage cleanup blocked by accumulation
deletion exceeding gas limits
storage cleanup requiring too much gas
deletion blocked by storage size
```

---

## 8. Economic DoS

### 8.1 Fee Manipulation DoS
**CWE-400**

#### Detection Phrases
```
fee parameters manipulable to block operations
fee calculation allowing DoS via high fees
fee manipulation blocking withdrawals
fee parameters set to block users
fee calculation enabling economic attack
fee manipulation causing transaction failure
fee parameters allowing blocking
fee calculation set to prevent operations
fee manipulation blocking deposits
fee parameters enabling DoS
fee calculation allowing economic DoS
fee manipulation preventing user actions
fee parameters blocking legitimate use
fee calculation enabling griefing
fee manipulation causing economic block
fee parameters allowing operational block
fee calculation set too high
fee manipulation blocking function use
fee parameters enabling economic attack
fee calculation preventing transactions
fee manipulation blocking protocol use
fee parameters set to grief users
fee calculation enabling operational block
fee manipulation causing user lockout
fee parameters allowing economic DoS
fee calculation blocking operations
fee manipulation enabling griefing
fee parameters causing transaction failure
fee calculation allowing operational DoS
fee manipulation blocking legitimate users
```

### 8.2 Economic Barrier DoS
**CWE-400**

#### Detection Phrases
```
minimum requirements set to exclude users
threshold parameters blocking small users
minimum stake preventing participation
threshold set to exclude legitimate users
minimum requirement blocking access
threshold parameters enabling exclusion
minimum balance preventing operation
threshold set too high for users
minimum requirement causing exclusion
threshold blocking small participants
minimum stake enabling DoS
threshold parameters set to block
minimum balance excluding users
threshold enabling economic barrier
minimum requirement set too high
threshold blocking legitimate users
minimum stake causing exclusion
threshold parameters blocking access
minimum balance enabling barrier
threshold set to prevent participation
minimum requirement excluding participants
threshold blocking user access
minimum stake set too high
threshold enabling exclusion attack
minimum balance blocking operations
threshold parameters preventing access
minimum requirement blocking participation
threshold set to exclude users
minimum stake excluding participants
threshold enabling economic DoS
```

### 8.3 Liquidity DoS
**CWE-400**

#### Detection Phrases
```
liquidity removal blocking subsequent users
pool draining causing operation failure
liquidity manipulation blocking withdrawals
pool liquidity removal affecting others
liquidity drain blocking operations
pool manipulation causing DoS
liquidity removal griefing attack
pool liquidity affecting user operations
liquidity manipulation causing failure
pool draining blocking functions
liquidity removal affecting protocol
pool manipulation enabling griefing
liquidity drain causing user lockout
pool liquidity manipulation attack
liquidity removal blocking claims
pool draining affecting withdrawals
liquidity manipulation blocking users
pool liquidity removal DoS
liquidity drain blocking protocol
pool manipulation blocking operations
liquidity removal causing lockout
pool liquidity drain attack
liquidity manipulation preventing access
pool draining blocking users
liquidity removal enabling DoS
pool manipulation causing failure
liquidity drain affecting operations
pool liquidity manipulation DoS
liquidity removal blocking operations
pool draining enabling attack
```

---

## 9. State Machine DoS

### 9.1 State Transition Blocking
**CWE-400**

#### Detection Phrases
```
state transition blocked by failed condition
state machine stuck by external dependency
state transition failure blocking progress
state machine blocked by external state
state transition prevented by condition
state machine stuck on external call
state transition blocked by requirement
state machine halted by failed check
state transition failure causing halt
state machine blocked by external dependency
state transition prevented by external
state machine stuck by condition
state transition blocked by state check
state machine halted by external failure
state transition failure preventing progress
state machine blocked by failed condition
state transition prevented by requirement
state machine stuck on failed check
state transition blocked by dependency
state machine halted by external
state transition failure blocking operations
state machine blocked by requirement failure
state transition prevented by external state
state machine stuck by dependency
state transition blocked by external failure
state machine halted by condition
state transition failure causing blockage
state machine blocked by external call
state transition prevented by failed check
state machine stuck blocking progress
```

### 9.2 Pause Mechanism Issues
**CWE-284**

#### Detection Phrases
```
pause mechanism blocking critical operations
paused state without user recourse
pause blocking withdrawals indefinitely
paused contract locking user funds
pause mechanism without expiration
paused state permanent by admin
pause blocking critical user functions
paused contract without timeout
pause mechanism lacking bypass for emergencies
paused state blocking fund recovery
pause without user withdrawal exception
paused contract funds locked
pause mechanism too broad
paused state blocking all operations
pause without emergency override
paused contract preventing withdrawals
pause mechanism without time limit
paused state indefinite
pause blocking essential operations
paused contract without escape hatch
pause mechanism without limits
paused state locking funds
pause blocking user critical paths
paused contract indefinitely
pause mechanism permanent potential
paused state without recourse
pause blocking fund access
paused contract without timeout mechanism
pause mechanism without safeguards
paused state blocking fund withdrawal
```

### 9.3 Deadline & Expiration DoS
**CWE-400**

#### Detection Phrases
```
deadline manipulation blocking operations
expiration set to block legitimate use
deadline parameter allowing DoS
expiration manipulation blocking access
deadline set to prevent transactions
expiration enabling operational DoS
deadline manipulation preventing operations
expiration set too short for legitimate use
deadline enabling blocking attack
expiration manipulation causing failure
deadline set to grief users
expiration blocking legitimate operations
deadline manipulation causing DoS
expiration set to prevent access
deadline enabling griefing
expiration manipulation blocking users
deadline set to block operations
expiration enabling DoS attack
deadline manipulation blocking legitimate
expiration set to cause failure
deadline blocking user transactions
expiration manipulation enabling attack
deadline set to prevent completion
expiration blocking operations
deadline manipulation griefing
expiration set to block users
deadline enabling operational block
expiration manipulation preventing completion
deadline set to cause transaction failure
expiration enabling blocking
```

---

## 10. Resource Exhaustion

### 10.1 Memory Exhaustion
**CWE-400**

#### Detection Phrases
```
memory array allocation with user-controlled size
dynamic memory allocation unbounded
memory array size from user input
memory allocation potentially exhausting resources
memory array created with large size
dynamic memory size from parameter
memory allocation without size limit
memory array unbounded allocation
dynamic memory from user-controlled value
memory allocation causing out-of-memory
memory array size without bound
dynamic memory allocation from input
memory allocation potentially too large
memory array from user size parameter
dynamic memory size unbounded
memory allocation without validation
memory array causing resource exhaustion
dynamic memory from untrusted size
memory allocation size not limited
memory array with large user size
dynamic memory allocation unchecked
memory allocation from user parameter
memory array potentially huge
dynamic memory size from user
memory allocation causing exhaustion
memory array without size validation
dynamic memory unbounded allocation
memory allocation size from input
memory array causing failure
dynamic memory without limit
```

### 10.2 Calldata/Stack Exhaustion
**CWE-400**

#### Detection Phrases
```
calldata processing with unbounded size
stack depth exhaustion possible
calldata iteration without limit
stack usage growing with input
calldata size causing resource issues
stack depth from recursive calls
calldata processing unbounded
stack exhaustion from depth
calldata without size limit processing
stack usage from nested calls
calldata causing memory issues
stack depth exhaustion risk
calldata size unchecked
stack usage potentially exhausting
calldata processing causing issues
stack depth from input
calldata iteration unbounded
stack exhaustion possible
calldata size from user input
stack depth growing unbounded
calldata processing without bound
stack usage from recursion
calldata causing resource exhaustion
stack depth without limit
calldata iteration causing issues
stack exhaustion from nesting
calldata size unbounded
stack depth from user input
calldata processing exhausting resources
stack usage unbounded
```

### 10.3 Event Log Exhaustion
**CWE-400**

#### Detection Phrases
```
event emission in unbounded loop
log output scaling with input size
event emission without limit
log generation unbounded
event emission causing gas issues
log output from iteration
event emission in loop
log generation scaling with data
event emission unbounded
log output potentially excessive
event emission from iteration
log generation without limit
event emission causing gas exhaustion
log output unbounded
event emission scaling with input
log generation from loop
event emission without bound
log output causing issues
event emission from unbounded iteration
log generation potentially excessive
event emission causing gas drain
log output from unbounded loop
event emission in unbounded iteration
log generation causing gas issues
event emission gas cost scaling
log output without bound
event emission from large input
log generation unbounded
event emission causing excessive gas
log output scaling with iteration
```

---

## 11. Locking & Freezing

### 11.1 Permanent Lock Conditions
**CWE-400, CWE-667**

#### Detection Phrases
```
funds locked permanently by failed condition
assets frozen without recovery mechanism
funds locked by state that cannot change
assets frozen permanently by admin
funds locked without unlock path
assets frozen by failed external dependency
funds locked permanently possible
assets frozen without recourse
funds locked by unrecoverable state
assets frozen by permanent condition
funds locked without recovery
assets frozen by admin indefinitely
funds locked by failed transition
assets frozen permanently possible
funds locked without unlock mechanism
assets frozen by unrecoverable condition
funds locked by permanent state
assets frozen without recovery path
funds locked indefinitely
assets frozen by failed state
funds locked without escape
assets frozen permanently by design
funds locked by design flaw
assets frozen without unlock
funds locked permanently by bug
assets frozen by state lock
funds locked without recovery option
assets frozen indefinitely possible
funds locked by unreachable state
assets frozen without mechanism to unlock
```

### 11.2 Conditional Unlock Failures
**CWE-400**

#### Detection Phrases
```
unlock condition impossible to meet
unlock dependent on external contract
unlock condition unreachable
unlock requiring impossible state
unlock condition blocked by external
unlock dependent on unreachable state
unlock condition impossible
unlock requiring failed external
unlock condition not achievable
unlock dependent on impossible state
unlock condition unreachable by design
unlock requiring external that reverts
unlock condition blocked
unlock dependent on failed condition
unlock condition not possible
unlock requiring unreachable state
unlock condition blocked by design
unlock dependent on impossible condition
unlock condition permanently blocked
unlock requiring failed state
unlock condition unreachable state
unlock dependent on reverted external
unlock condition impossible by design
unlock requiring blocked state
unlock condition permanently unreachable
unlock dependent on condition impossible
unlock condition blocked permanently
unlock requiring impossible condition
unlock condition not achievable by design
unlock dependent on unreachable condition
```

### 11.3 Time Lock Issues
**CWE-400**

#### Detection Phrases
```
time lock set to impossible duration
unlock time overflow blocking access
time lock duration causing permanent lock
unlock time set too far in future
time lock overflow causing lock
unlock time causing permanent freeze
time lock duration overflowed
unlock time impossible to reach
time lock causing indefinite lock
unlock time overflow
time lock set to maximum value
unlock time causing permanent lock
time lock duration too long
unlock time set to block permanently
time lock causing fund freeze
unlock time duration overflow
time lock overflow blocking funds
unlock time unreachable
time lock duration causing freeze
unlock time overflow causing permanent
time lock set to permanent
unlock time too far future
time lock causing locked forever
unlock time causing freeze
time lock maximum duration
unlock time permanently locked
time lock duration blocking access
unlock time overflow blocking
time lock causing permanent freeze
unlock time set impossible
```

---

## 12. Recovery & Emergency Mechanisms

### 12.1 Missing Emergency Functions
**CWE-754**

#### Detection Phrases
```
contract without emergency withdrawal
protocol lacking rescue function
contract without fund recovery mechanism
protocol missing emergency escape
contract without emergency pause
protocol lacking emergency withdrawal
contract missing rescue mechanism
protocol without emergency function
contract without fallback recovery
protocol missing emergency mechanism
contract lacking emergency withdraw
protocol without rescue function
contract missing emergency escape
protocol lacking recovery mechanism
contract without emergency mechanism
protocol missing fallback recovery
contract lacking rescue function
protocol without emergency withdrawal
contract missing recovery function
protocol lacking emergency escape
contract without rescue mechanism
protocol missing emergency pause
contract lacking emergency function
protocol without recovery function
contract missing emergency withdraw
protocol lacking rescue mechanism
contract without emergency recovery
protocol missing recovery mechanism
contract lacking fallback recovery
protocol without emergency escape
```

### 12.2 Broken Recovery Mechanisms
**CWE-754**

#### Detection Phrases
```
emergency function blocked by same condition
rescue mechanism affected by DoS
emergency withdrawal blocked by state
rescue function failing on condition
emergency mechanism broken by dependency
rescue blocked by same issue
emergency function not accessible
rescue mechanism failing
emergency withdrawal blocked
rescue function blocked by state
emergency mechanism inaccessible
rescue blocked by condition
emergency function broken
rescue mechanism blocked
emergency withdrawal failing
rescue function inaccessible
emergency mechanism blocked by dependency
rescue blocked by DoS condition
emergency function blocked
rescue mechanism broken by state
emergency withdrawal blocked by condition
rescue function blocked by dependency
emergency mechanism failing
rescue blocked by same DoS
emergency function inaccessible
rescue mechanism blocked by condition
emergency withdrawal inaccessible
rescue function broken
emergency mechanism blocked by state
rescue blocked by failing condition
```

### 12.3 Admin Recovery Risks
**CWE-284**

#### Detection Phrases
```
admin recovery draining user funds
rescue function allowing arbitrary withdrawal
admin recovery bypassing user protections
rescue mechanism allowing fund theft
admin recovery with excessive power
rescue function without proper limits
admin recovery allowing drain
rescue mechanism without user protection
admin recovery too powerful
rescue function allowing arbitrary access
admin recovery without safeguards
rescue mechanism bypassing limits
admin recovery enabling theft
rescue function with excessive access
admin recovery without limits
rescue mechanism allowing drain
admin recovery allowing arbitrary
rescue function without safeguards
admin recovery bypassing protections
rescue mechanism with excessive power
admin recovery without proper limits
rescue function allowing theft
admin recovery enabling drain
rescue mechanism without limits
admin recovery with arbitrary access
rescue function bypassing user protections
admin recovery allowing unauthorized
rescue mechanism without proper safeguards
admin recovery excessive power
rescue function without user limits
```

---

## Complex Query Examples for Liveness Lens

### Query 1: Unbounded Loop Detection
```json
{
  "query_kind": "logic",
  "node_types": ["Function"],
  "match": {
    "all": [
      {"property": "has_loop", "op": "eq", "value": true},
      {"property": "loop_bound_source", "op": "in", "value": ["user_input", "storage_array_length", "dynamic"]}
    ],
    "any": [
      {"property": "loop_contains_external_call", "op": "eq", "value": true},
      {"property": "loop_contains_storage_write", "op": "eq", "value": true},
      {"property": "loop_contains_event_emission", "op": "eq", "value": true}
    ]
  },
  "explain_mode": true
}
```

### Query 2: Griefing Attack Surface
```json
{
  "query_kind": "logic",
  "node_types": ["Function"],
  "match": {
    "all": [
      {"property": "has_push_payment", "op": "eq", "value": true},
      {"property": "payment_recipient_controllable", "op": "eq", "value": true}
    ],
    "none": [
      {"property": "handles_transfer_failure", "op": "eq", "value": true},
      {"property": "has_pull_payment_alternative", "op": "eq", "value": true}
    ]
  },
  "explain_mode": true
}
```

### Query 3: Division by Zero Risk
```json
{
  "query_kind": "logic",
  "node_types": ["Function"],
  "match": {
    "all": [
      {"property": "has_division", "op": "eq", "value": true},
      {"property": "divisor_source", "op": "in", "value": ["parameter", "storage", "calculation"]}
    ],
    "none": [
      {"property": "divisor_validated_nonzero", "op": "eq", "value": true}
    ]
  },
  "explain_mode": true
}
```

### Query 4: Permanent Lock Risk
```json
{
  "query_kind": "logic",
  "node_types": ["Function"],
  "match": {
    "all": [
      {"property": "locks_funds", "op": "eq", "value": true}
    ],
    "any": [
      {"property": "unlock_condition_external_dependent", "op": "eq", "value": true},
      {"property": "unlock_condition_potentially_impossible", "op": "eq", "value": true}
    ]
  },
  "contract_context": {
    "none": [
      {"property": "has_emergency_withdrawal", "op": "eq", "value": true}
    ]
  },
  "explain_mode": true
}
```

---

## Pattern Pack: Liveness Lens Complete

```yaml
# Save as patterns/liveness-lens.yaml
patterns:
  - id: live-001
    name: Unbounded Loop DoS
    severity: high
    cwe: [400]

  - id: live-002
    name: Block Gas Limit Exhaustion
    severity: high
    cwe: [400]

  - id: live-003
    name: Push Payment Griefing
    severity: medium
    cwe: [400]

  - id: live-004
    name: Auction Griefing
    severity: medium
    cwe: [400]

  - id: live-005
    name: Division by Zero
    severity: medium
    cwe: [754]

  - id: live-006
    name: Array Out of Bounds
    severity: medium
    cwe: [119]

  - id: live-007
    name: Assert Gas Consumption
    severity: low
    cwe: [754]

  - id: live-008
    name: Storage Growth DoS
    severity: medium
    cwe: [400]

  - id: live-009
    name: Economic DoS via Fees
    severity: medium
    cwe: [400]

  - id: live-010
    name: Permanent Fund Lock
    severity: critical
    cwe: [400, 667]

  - id: live-011
    name: Missing Emergency Recovery
    severity: high
    cwe: [754]

  - id: live-012
    name: External Call Cascade Failure
    severity: high
    cwe: [754]
```

### Pattern ID Mapping Notes
- `live-001` through `live-012` map exactly to the pattern pack above.
- `live-013` through `live-039` extend coverage for every additional subsection in this lens.

| ID | Name |
| --- | --- |
| live-013 | Nested Loop Complexity |
| live-014 | Dynamic Gas Consumption |
| live-015 | Transaction Size Attacks |
| live-016 | Batch Operation Limits |
| live-017 | Unbounded Array Operations |
| live-018 | Unbounded Mapping Iterations |
| live-019 | Unbounded String or Bytes Operations |
| live-020 | Callback Griefing |
| live-021 | State Manipulation Griefing |
| live-022 | External Call Dependency |
| live-023 | External Call Gas Forwarding |
| live-024 | Underflow or Overflow Reverts |
| live-025 | Storage Slot Exhaustion |
| live-026 | Storage Cost Attacks |
| live-027 | Storage Cleanup Failures |
| live-028 | Economic Barrier DoS |
| live-029 | Liquidity DoS |
| live-030 | State Transition Blocking |
| live-031 | Pause Mechanism Issues |
| live-032 | Deadline and Expiration DoS |
| live-033 | Memory Exhaustion |
| live-034 | Calldata or Stack Exhaustion |
| live-035 | Event Log Exhaustion |
| live-036 | Conditional Unlock Failures |
| live-037 | Time Lock Issues |
| live-038 | Broken Recovery Mechanisms |
| live-039 | Admin Recovery Risks |
