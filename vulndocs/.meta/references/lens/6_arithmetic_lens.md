# Arithmetic Lens - Ultra-Expanded Detection Patterns

> Comprehensive integer overflow, precision loss, unsafe casting, and mathematical
> vulnerability detection for AlphaSwarm.sol

---

## Table of Contents
1. [Integer Overflow/Underflow](#1-integer-overflowunderflow)
2. [Precision Loss](#2-precision-loss)
3. [Unsafe Type Casting](#3-unsafe-type-casting)
4. [Division Issues](#4-division-issues)
5. [Multiplication Overflow](#5-multiplication-overflow)
6. [Percentage & Basis Point Calculations](#6-percentage--basis-point-calculations)
7. [Share & Ratio Calculations](#7-share--ratio-calculations)
8. [Fee Calculations](#8-fee-calculations)
9. [Time-Based Calculations](#9-time-based-calculations)
10. [Token Decimal Handling](#10-token-decimal-handling)

---

## 1. Integer Overflow/Underflow

### 1.1 Unchecked Block Vulnerabilities
**CWE-190** (Integer Overflow), **CWE-191** (Integer Underflow)

#### Detection Phrases (NL Queries)
```
arithmetic operations on uint without SafeMath in Solidity < 0.8
unchecked blocks with addition or multiplication on user input
loop counters that can overflow causing infinite loops
balance calculations in unchecked blocks
subtraction operations that could underflow to max uint
unchecked arithmetic with user-controlled values
unchecked addition potentially overflowing
unchecked subtraction with underflow risk
unchecked multiplication overflow possible
unchecked arithmetic in financial calculation
unchecked block with user input arithmetic
unchecked addition of large values
unchecked subtraction potentially underflowing
unchecked multiplication with user values
unchecked arithmetic in balance update
unchecked block arithmetic overflow risk
unchecked addition in loop
unchecked subtraction in withdrawal
unchecked multiplication in reward calculation
unchecked arithmetic with attacker-controlled value
unchecked block with overflow potential
unchecked addition overflow possibility
unchecked subtraction underflow vulnerability
unchecked multiplication overflow risk
unchecked arithmetic affecting balances
unchecked block with financial arithmetic
unchecked addition with large inputs
unchecked subtraction without validation
unchecked multiplication without bounds
unchecked arithmetic in critical path
```

#### Detection Rules
```yaml
rule: unchecked-arithmetic
conditions:
  all:
    - expression.in_unchecked_block == true
    - expression.is_arithmetic == true
    - OR:
      - expression.operand_source == user_input
      - expression.operand_source == storage
      - expression.affects_balance == true
severity: high
```

### 1.2 Pre-0.8 Overflow/Underflow
**CWE-190, CWE-191**

#### Detection Phrases
```
Solidity < 0.8 without SafeMath
pre-0.8 arithmetic without overflow protection
Solidity 0.7 or lower arithmetic overflow risk
pre-0.8 code without SafeMath library
Solidity < 0.8 subtraction underflow
pre-0.8 multiplication overflow possible
Solidity 0.6 arithmetic without protection
pre-0.8 addition overflow risk
Solidity < 0.8 without checked math
pre-0.8 code overflow vulnerability
Solidity 0.7 without SafeMath
pre-0.8 arithmetic vulnerability
Solidity < 0.8 balance overflow
pre-0.8 subtraction without check
Solidity 0.6 overflow risk
pre-0.8 multiplication without SafeMath
Solidity < 0.8 loop overflow
pre-0.8 arithmetic without library
Solidity 0.7 underflow risk
pre-0.8 addition without SafeMath
Solidity < 0.8 financial calculation overflow
pre-0.8 balance underflow
Solidity 0.6 without protection
pre-0.8 counter overflow
Solidity < 0.8 arithmetic without checking
pre-0.8 subtraction underflow risk
Solidity 0.7 multiplication overflow
pre-0.8 without safe math
Solidity < 0.8 reward overflow
pre-0.8 calculation overflow
```

### 1.3 Loop Counter Issues
**CWE-190**

#### Detection Phrases
```
loop counter overflow causing infinite loop
loop index overflow in for loop
loop counter uint8 overflowing
loop index reaching max value
loop counter overflow DoS
loop index overflow risk
loop counter type too small
loop index max value overflow
loop counter increment overflow
loop index uint overflow
loop counter size insufficient
loop index overflow causing hang
loop counter max iteration overflow
loop index type overflow risk
loop counter overflow possibility
loop index increment overflow
loop counter reaching max
loop index overflow vulnerability
loop counter type overflow
loop index overflow in iteration
loop counter max value reached
loop index type too small
loop counter overflow attack
loop index reaching maximum
loop counter increment max
loop index overflow in loop
loop counter overflow infinite
loop index uint8 overflow
loop counter overflow vulnerability
loop index overflow causing DoS
```

---

## 2. Precision Loss

### 2.1 Division Before Multiplication
**CWE-682** (Incorrect Calculation)

#### Detection Phrases
```
division before multiplication causing precision loss
integer division truncating significant value in financial calculations
division before multiplication losing precision
integer division before multiplication
division truncation before multiplication
integer division precision loss
division first causing truncation
integer division then multiplication
division order causing precision loss
integer truncation in calculation
division before multiplication in formula
integer division losing precision
division truncating then multiplying
integer division order issue
division precision loss in calculation
integer truncation before multiplication
division order precision issue
integer division precision truncation
division causing precision loss
integer truncation in financial math
division before multiply precision
integer division order precision
division truncation in calculation
integer division precision issue
division first precision loss
integer truncation precision loss
division order causing truncation
integer division truncation
division precision truncation
integer division precision loss in calculation
```

#### Detection Rules
```yaml
rule: division-before-multiplication
conditions:
  all:
    - expression.has_division == true
    - expression.has_multiplication == true
    - expression.division_before_multiplication == true
    - expression.in_financial_context == true
severity: medium
```

### 2.2 Truncation in Financial Calculations
**CWE-682**

#### Detection Phrases
```
integer division truncating in reward distribution
truncation in share calculation
integer division losing value in fees
truncation in interest calculation
integer division truncating user rewards
truncation in yield calculation
integer division precision in distribution
truncation in rate calculation
integer division truncating in swap
truncation in price calculation
integer division losing in fee calculation
truncation in percentage calculation
integer division truncating tokens
truncation in dividend distribution
integer division precision loss in rewards
truncation in exchange rate
integer division truncating value
truncation in share pricing
integer division losing precision in interest
truncation in collateral calculation
integer division truncating in distribution
truncation in loan calculation
integer division precision in fees
truncation in reward rate
integer division truncating in payment
truncation in token calculation
integer division losing value
truncation in value calculation
integer division truncating amount
truncation in protocol calculation
```

### 2.3 Rounding Exploitation
**CWE-682**

#### Detection Phrases
```
rounding errors in share or token amount calculations
rounding exploitation in vault deposits
rounding error favor attacker
rounding exploitation in share calculation
rounding error allowing extraction
rounding exploitation in withdrawal
rounding error in conversion
rounding exploitation in swap
rounding error direction exploitable
rounding exploitation in mint
rounding error accumulation
rounding exploitation in redeem
rounding error in fee calculation
rounding exploitation for profit
rounding error direction wrong
rounding exploitation in conversion
rounding error allowing profit
rounding exploitation in distribution
rounding error in reward
rounding exploitation in claim
rounding error accumulating over transactions
rounding exploitation in deposit
rounding error direction favoritism
rounding exploitation in pricing
rounding error exploitable
rounding exploitation in rate calculation
rounding error in share pricing
rounding exploitation vulnerability
rounding error direction issue
rounding exploitation attack vector
```

---

## 3. Unsafe Type Casting

### 3.1 Narrowing Casts
**CWE-681** (Incorrect Conversion)

#### Detection Phrases
```
explicit casts from larger to smaller integer types without bounds check
int to uint conversions on potentially negative values
downcasting uint256 to uint128 or smaller without validation
type conversions in financial calculations without overflow checks
narrowing cast without bounds validation
downcasting without range check
narrowing conversion losing data
downcasting uint256 without validation
narrowing cast overflow possible
downcasting without overflow check
narrowing conversion truncation
downcasting to smaller type
narrowing cast without validation
downcasting uint without bounds
narrowing conversion data loss
downcasting without checking range
narrowing cast vulnerability
downcasting without validation
narrowing conversion overflow
downcasting to uint128 without check
narrowing cast truncating value
downcasting uint256 to uint96
narrowing conversion without check
downcasting without bounds check
narrowing cast data loss
downcasting without range validation
narrowing conversion without bounds
downcasting to smaller uint
narrowing cast without range check
downcasting without overflow validation
```

#### Detection Rules
```yaml
rule: unsafe-narrowing-cast
conditions:
  all:
    - expression.is_explicit_cast == true
    - expression.cast_direction == narrowing
    - NOT expression.has_bounds_check_before_cast
severity: medium
```

### 3.2 Signed/Unsigned Conversions
**CWE-681**

#### Detection Phrases
```
int to uint conversion on negative value
signed to unsigned cast losing sign
int converted to uint without check
signed to unsigned overflow
int to uint negative value issue
signed to unsigned conversion vulnerability
int cast to uint without validation
signed to unsigned losing data
int to uint conversion overflow
signed to unsigned without check
int cast to uint vulnerability
signed to unsigned cast issue
int to uint negative conversion
signed to unsigned without validation
int cast to uint overflow
signed to unsigned conversion issue
int to uint without sign check
signed to unsigned cast overflow
int cast to uint losing sign
signed to unsigned data loss
int to uint sign loss
signed to unsigned without sign check
int cast to uint negative
signed to unsigned conversion overflow
int to uint conversion issue
signed to unsigned cast vulnerability
int cast to uint without sign validation
signed to unsigned overflow issue
int to uint without negative check
signed to unsigned cast without validation
```

### 3.3 Address to Uint Conversions
**CWE-681**

#### Detection Phrases
```
address to uint conversion for comparison
address cast to uint160 for arithmetic
address converted to integer
address to uint for manipulation
address cast for calculation
address converted to uint160
address to uint conversion vulnerability
address cast to integer type
address converted for arithmetic
address to uint security issue
address cast without proper handling
address converted to uint for comparison
address to uint casting issue
address cast to uint160 vulnerability
address converted for manipulation
address to uint conversion risk
address cast vulnerability
address converted to integer for comparison
address to uint for arithmetic
address cast for comparison
address converted without validation
address to uint cast issue
address cast to uint160 for comparison
address converted to integer vulnerability
address to uint conversion without check
address cast for manipulation
address converted to uint security
address to uint vulnerability
address cast to uint for calculation
address converted for comparison vulnerability
```

---

## 4. Division Issues

### 4.1 Division by Zero
**CWE-369**

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
    - expression.divisor_source IN [parameter, storage, calculation, external_call]
    - NOT expression.divisor_validated_nonzero
severity: medium
```

### 4.2 Division Precision
**CWE-682**

#### Detection Phrases
```
division losing precision in small values
division truncating significant amount
division precision insufficient for calculation
division losing decimal places
division truncating small amounts
division precision loss in conversion
division losing value for small numbers
division truncating in rate calculation
division precision insufficient for small values
division losing in small amount calculation
division truncating precision
division precision loss for small inputs
division losing significant figures
division truncating value in calculation
division precision issue with small values
division losing precision in fee
division truncating small value
division precision loss in rate
division losing in division of small numbers
division truncating in small calculation
division precision insufficient
division losing precision in reward
division truncating significant value
division precision loss in small amounts
division losing in small number division
division truncating precision loss
division precision issue in calculation
division losing value in small calculation
division truncating in conversion
division precision loss significant
```

---

## 5. Multiplication Overflow

### 5.1 Large Number Multiplication
**CWE-190**

#### Detection Phrases
```
multiplication of large numbers overflowing
large value multiplication overflow risk
multiplication overflow with big numbers
large number multiplication vulnerability
multiplication of uint256 values overflowing
large value overflow in multiplication
multiplication causing overflow with large inputs
large number overflow risk
multiplication of big values overflow
large value multiplication vulnerability
multiplication overflow with large values
large number multiplication overflow risk
multiplication causing overflow large numbers
large value overflow potential
multiplication of large amounts
large number multiplication risk
multiplication overflow potential
large value multiplication overflow possible
multiplication of large values overflow risk
large number overflow in multiplication
multiplication overflow with big values
large value overflow vulnerability
multiplication causing large number overflow
large number multiplication overflow
multiplication overflow from large inputs
large value multiplication causing overflow
multiplication of big numbers overflow
large number overflow potential
multiplication overflow large values
large value overflow in calculation
```

### 5.2 Price * Amount Calculations
**CWE-190**

#### Detection Phrases
```
price times amount overflow possible
price multiplication overflow risk
price times quantity overflow
price amount multiplication overflow
price multiplied by amount overflow
price times amount overflow vulnerability
price multiplication with large amount
price times quantity overflow risk
price amount calculation overflow
price multiplied overflow potential
price times amount overflow possible
price multiplication overflow potential
price times large amount overflow
price amount overflow vulnerability
price multiplied by quantity overflow
price times amount calculation overflow
price multiplication vulnerability
price times amount overflow risk
price amount overflow potential
price multiplied overflow risk
price times quantity calculation overflow
price multiplication overflow in calculation
price times amount overflow in swap
price amount multiplication vulnerability
price multiplied by large amount
price times amount overflow calculation
price multiplication large values
price times quantity overflow potential
price amount calculation vulnerability
price multiplied amount overflow
```

---

## 6. Percentage & Basis Point Calculations

### 6.1 Percentage Overflow
**CWE-190**

#### Detection Phrases
```
percentage calculations without proper decimal handling
percentage calculation overflow possible
percentage multiplication overflow
percentage calculation without bound
percentage value overflow risk
percentage calculation exceeding limits
percentage multiplication vulnerability
percentage value overflow possible
percentage calculation overflow vulnerability
percentage value exceeding maximum
percentage calculation overflow risk
percentage multiplication with large base
percentage value overflow potential
percentage calculation without maximum check
percentage multiplication overflow potential
percentage value overflow in calculation
percentage calculation overflow in fee
percentage multiplication with large value
percentage value exceeding bound
percentage calculation without validation
percentage multiplication overflow risk
percentage value overflow vulnerability
percentage calculation exceeding maximum
percentage multiplication vulnerability
percentage value overflow exceeding
percentage calculation without bounds
percentage multiplication with overflow
percentage value overflow in percentage
percentage calculation overflow potential
percentage multiplication causing overflow
```

### 6.2 Basis Points Handling
**CWE-682**

#### Detection Phrases
```
basis points calculation precision loss
basis point conversion losing precision
basis points division truncation
basis point calculation precision issue
basis points conversion truncating
basis point division losing value
basis points calculation truncation
basis point conversion precision loss
basis points division precision
basis point calculation losing precision
basis points conversion losing value
basis point division truncating
basis points calculation precision
basis point conversion truncation
basis points division losing precision
basis point calculation truncating
basis points conversion precision issue
basis point division precision loss
basis points calculation losing value
basis point conversion losing precision
basis points division truncation issue
basis point calculation precision issue
basis points conversion truncating value
basis point division precision issue
basis points calculation truncating value
basis point conversion truncating precision
basis points division precision issue
basis point calculation conversion issue
basis points truncation in calculation
basis point precision loss in conversion
```

---

## 7. Share & Ratio Calculations

### 7.1 Share Inflation Attacks
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
vault share inflation attack vector
share ratio calculation vulnerability
first depositor attack in vault
share calculation first depositor vulnerability
vault share manipulation on initialization
share ratio precision attack
first depositor inflation vulnerability
share calculation rounding attack
vault share first depositor attack
share ratio manipulation vulnerability
```

### 7.2 Ratio Calculation Issues
**CWE-682**

#### Detection Phrases
```
ratio calculation precision loss
ratio division truncating
ratio calculation losing precision
ratio division precision issue
ratio calculation truncation
ratio division losing value
ratio calculation precision issue
ratio division truncating value
ratio calculation losing value
ratio division precision loss
ratio calculation truncating precision
ratio division losing precision
ratio calculation precision truncation
ratio division truncation issue
ratio calculation losing precision in calculation
ratio division precision truncation
ratio calculation truncation issue
ratio division losing precision value
ratio calculation precision loss significant
ratio division truncating precision
ratio calculation losing significant value
ratio division precision loss issue
ratio calculation truncation losing value
ratio division losing value precision
ratio calculation precision issue significant
ratio division truncation precision
ratio calculation precision loss in ratio
ratio division truncating value precision
ratio calculation losing precision ratio
ratio division precision loss in calculation
```

---

## 8. Fee Calculations

### 8.1 Fee Precision Issues
**CWE-682**

#### Detection Phrases
```
fee calculations where order of operations loses precision
fee calculation precision loss
fee calculation truncating value
fee calculation order of operations
fee precision loss in calculation
fee calculation truncation issue
fee calculation losing precision
fee precision truncation
fee calculation order issue
fee precision loss significant
fee calculation truncating fee
fee precision issue in calculation
fee calculation losing fee value
fee precision truncation issue
fee calculation precision truncation
fee precision loss in fee calculation
fee calculation truncating precision
fee precision calculation issue
fee calculation losing precision value
fee precision truncation significant
fee calculation precision issue
fee precision loss in calculation order
fee calculation truncating in order
fee precision issue significant
fee calculation losing value
fee precision truncation in calculation
fee calculation precision loss order
fee precision issue in fee
fee calculation truncating order
fee precision loss issue
```

### 8.2 Fee Accumulation Overflow
**CWE-190**

#### Detection Phrases
```
fee accumulation potentially overflowing
accumulated fees overflow risk
fee accumulation overflow possible
accumulated fees exceeding limit
fee accumulation overflow vulnerability
accumulated fees overflow vulnerability
fee accumulation exceeding maximum
accumulated fees overflow potential
fee accumulation overflow potential
accumulated fees exceeding bound
fee accumulation exceeding bounds
accumulated fees overflow risk significant
fee accumulation overflow in calculation
accumulated fees exceeding maximum value
fee accumulation overflow significant
accumulated fees potential overflow
fee accumulation exceeding limit
accumulated fees overflow in accumulation
fee accumulation overflow from accumulation
accumulated fees exceeding storage
fee accumulation overflow vulnerability potential
accumulated fees overflow exceeding
fee accumulation exceeding in accumulation
accumulated fees overflow from fees
fee accumulation overflow in fee
accumulated fees exceeding calculation
fee accumulation overflow accumulation
accumulated fees overflow potential risk
fee accumulation overflow significant risk
accumulated fees exceeding fees
```

---

## 9. Time-Based Calculations

### 9.1 Timestamp Arithmetic
**CWE-190**

#### Detection Phrases
```
timestamp arithmetic overflow possible
time calculation overflow risk
timestamp addition overflow
time arithmetic overflow potential
timestamp calculation overflow
time addition potentially overflowing
timestamp arithmetic vulnerability
time calculation overflow vulnerability
timestamp addition overflow risk
time arithmetic overflow risk
timestamp calculation overflow potential
time addition overflow possible
timestamp arithmetic overflow potential
time calculation overflow potential
timestamp addition overflow vulnerability
time arithmetic overflow vulnerability
timestamp calculation overflow risk
time addition overflow vulnerability
timestamp arithmetic overflow risk
time calculation overflow significant
timestamp addition overflow potential
time arithmetic overflow possible
timestamp calculation overflow in calculation
time addition overflow risk significant
timestamp arithmetic overflow significant
time calculation overflow in time
timestamp addition overflow significant
time arithmetic overflow in calculation
timestamp calculation overflow vulnerability
time addition overflow in time
```

### 9.2 Duration Calculations
**CWE-682**

#### Detection Phrases
```
duration calculation precision loss
duration division truncating
duration calculation losing precision
duration arithmetic precision issue
duration calculation truncation
duration division losing value
duration calculation precision issue
duration arithmetic truncation
duration calculation losing value
duration division precision loss
duration calculation truncating precision
duration arithmetic losing precision
duration calculation precision truncation
duration division truncation issue
duration calculation losing precision in calculation
duration arithmetic precision truncation
duration calculation truncation issue
duration division losing precision value
duration calculation precision loss significant
duration arithmetic truncating precision
duration calculation losing significant value
duration division precision loss issue
duration calculation truncation losing value
duration arithmetic losing value precision
duration calculation precision issue significant
duration division truncation precision
duration calculation precision loss in duration
duration arithmetic truncating value precision
duration calculation losing precision duration
duration division precision loss in calculation
```

---

## 10. Token Decimal Handling

### 10.1 Decimal Mismatch
**CWE-682**

#### Detection Phrases
```
token decimal mismatch in calculation
tokens with different decimals compared directly
decimal conversion missing in swap
token decimal handling incorrect
decimal mismatch between tokens
token decimals not normalized
decimal conversion error
token decimal calculation wrong
decimal mismatch in price calculation
token decimals not accounted for
decimal conversion missing
token decimal handling vulnerability
decimal mismatch causing calculation error
token decimals different not handled
decimal conversion not performed
token decimal mismatch vulnerability
decimal handling incorrect
token decimal conversion missing
decimal mismatch in conversion
token decimals not converted
decimal handling error
token decimal mismatch in calculation
decimal conversion vulnerability
token decimals not handled correctly
decimal mismatch causing error
token decimal conversion error
decimal handling not normalized
token decimal mismatch in swap
decimal conversion not normalized
token decimal handling error
```

### 10.2 Decimal Scaling Issues
**CWE-682**

#### Detection Phrases
```
decimal scaling causing precision loss
decimal scaling overflow possible
decimal scaling truncating value
decimal scaling precision issue
decimal scaling losing precision
decimal scaling overflow risk
decimal scaling truncation
decimal scaling precision loss
decimal scaling losing value
decimal scaling overflow vulnerability
decimal scaling truncating precision
decimal scaling precision truncation
decimal scaling losing precision value
decimal scaling overflow potential
decimal scaling truncation issue
decimal scaling precision loss significant
decimal scaling losing significant value
decimal scaling overflow in calculation
decimal scaling truncation precision
decimal scaling precision issue significant
decimal scaling losing precision calculation
decimal scaling overflow significant
decimal scaling truncating value precision
decimal scaling precision loss in scaling
decimal scaling losing value precision
decimal scaling overflow vulnerability potential
decimal scaling truncation losing value
decimal scaling precision truncation issue
decimal scaling losing precision scaling
decimal scaling overflow risk significant
```

---

## Complex Query Examples for Arithmetic Lens

### Query 1: Unchecked Arithmetic Detection
```json
{
  "query_kind": "logic",
  "node_types": ["Function"],
  "match": {
    "all": [
      {"property": "has_unchecked_block", "op": "eq", "value": true},
      {"property": "unchecked_contains_arithmetic", "op": "eq", "value": true}
    ],
    "any": [
      {"property": "unchecked_operand_from_user", "op": "eq", "value": true},
      {"property": "unchecked_affects_balance", "op": "eq", "value": true}
    ]
  },
  "explain_mode": true
}
```

### Query 2: Division Precision Issues
```json
{
  "query_kind": "logic",
  "node_types": ["Function"],
  "match": {
    "all": [
      {"property": "has_division", "op": "eq", "value": true},
      {"property": "has_multiplication", "op": "eq", "value": true},
      {"property": "division_before_multiplication", "op": "eq", "value": true},
      {"property": "in_financial_context", "op": "eq", "value": true}
    ]
  },
  "explain_mode": true
}
```

### Query 3: Unsafe Casting
```json
{
  "query_kind": "logic",
  "node_types": ["Function"],
  "match": {
    "all": [
      {"property": "has_explicit_cast", "op": "eq", "value": true},
      {"property": "cast_is_narrowing", "op": "eq", "value": true}
    ],
    "none": [
      {"property": "has_bounds_check_before_cast", "op": "eq", "value": true}
    ]
  },
  "explain_mode": true
}
```

---

## Pattern Pack: Arithmetic Lens Complete

```yaml
# Save as patterns/arithmetic-lens.yaml
patterns:
  - id: arith-001
    name: Unchecked Arithmetic
    severity: high
    cwe: [190, 191]

  - id: arith-002
    name: Division Before Multiplication
    severity: medium
    cwe: [682]

  - id: arith-003
    name: Unsafe Narrowing Cast
    severity: medium
    cwe: [681]

  - id: arith-004
    name: Division by Zero Risk
    severity: medium
    cwe: [369]

  - id: arith-005
    name: Share Inflation Attack
    severity: high
    cwe: [682]

  - id: arith-006
    name: Fee Precision Loss
    severity: medium
    cwe: [682]

  - id: arith-007
    name: Token Decimal Mismatch
    severity: medium
    cwe: [682]

  - id: arith-008
    name: Multiplication Overflow
    severity: high
    cwe: [190]

  - id: arith-009
    name: Rounding Exploitation
    severity: medium
    cwe: [682]

  - id: arith-010
    name: Percentage Overflow
    severity: medium
    cwe: [190]
```

---
---
---

# Logic & State Lens - Ultra-Expanded Detection Patterns

> Comprehensive business logic, state machine, and invariant vulnerability detection for
> AlphaSwarm.sol

---

## Table of Contents
1. [State Machine Vulnerabilities](#1-state-machine-vulnerabilities)
2. [Invariant Violations](#2-invariant-violations)
3. [Missing Validation Checks](#3-missing-validation-checks)
4. [Business Logic Flaws](#4-business-logic-flaws)
5. [Accounting Errors](#5-accounting-errors)
6. [Shadowing & Inheritance Issues](#6-shadowing--inheritance-issues)
7. [Selfdestruct Vulnerabilities](#7-selfdestruct-vulnerabilities)
8. [Contract Existence Checks](#8-contract-existence-checks)
9. [Default Value Issues](#9-default-value-issues)
10. [Event & Logging Issues](#10-event--logging-issues)

---

## 1. State Machine Vulnerabilities

### 1.1 Invalid State Transitions
**CWE-840** (Business Logic Errors)

#### Detection Phrases (NL Queries)
```
state variables modifiable out of expected sequence
functions bypassing intended state machine transitions
boolean flags settable without proper preconditions
emergency functions without proper state reset
pause mechanisms that don't halt all critical operations
state transition without proper guard
state machine bypass possible
state transition from invalid state
state machine guards missing
state transition skippable
state machine sequence bypassable
state transition without validation
state machine state skipping
state transition from wrong state
state machine order violation
state transition guard missing
state machine bypass vulnerability
state transition without sequence check
state machine states skippable
state transition order violation
state machine without proper guards
state transition invalid sequence
state machine bypass via function
state transition without state check
state machine sequence violation
state transition skipping states
state machine without validation
state transition from invalid
state machine order bypass
state transition guards missing
```

#### Detection Rules
```yaml
rule: invalid-state-transition
conditions:
  all:
    - function.modifies_state_variable == true
    - function.state_variable_is_state_machine == true
    - OR:
      - function.validates_current_state == false
      - function.allows_invalid_transition == true
severity: high
```

### 1.2 Incomplete State Management
**CWE-840**

#### Detection Phrases
```
state variable not reset after operation
state cleanup missing on completion
state variable left in intermediate state
state not finalized after transaction
state cleanup incomplete
state variable dangling
state not reset after failure
state cleanup missing on error
state variable not cleared
state not reset on completion
state cleanup incomplete on failure
state variable stuck in intermediate
state not finalized properly
state cleanup not performed
state variable remaining set
state not cleared after use
state cleanup missing on completion
state variable not reset properly
state not cleared on error
state cleanup incomplete after operation
state variable not updated on completion
state not reset after success
state cleanup missing after failure
state variable dangling after operation
state not finalized on error
state cleanup incomplete after success
state variable stuck after failure
state not cleared properly
state cleanup not complete
state variable remaining after operation
```

### 1.3 Race Conditions in State
**CWE-362**

#### Detection Phrases
```
state race condition between functions
concurrent state modification
state race in state machine
concurrent access to state variable
state race condition vulnerability
concurrent modification of state
state race between callers
concurrent state change
state race exploitable
concurrent state modification issue
state race in critical section
concurrent access state race
state race condition in function
concurrent modification vulnerability
state race between transactions
concurrent state access issue
state race in state transition
concurrent modification race
state race vulnerability
concurrent state change race
state race between operations
concurrent access race condition
state race in state change
concurrent modification in state
state race condition attack
concurrent state race vulnerability
state race between users
concurrent access state issue
state race in transition
concurrent modification state race
```

---

## 2. Invariant Violations

### 2.1 Balance Invariant Violations
**CWE-682**

#### Detection Phrases
```
functions that can break total supply equals sum of balances
operations allowing more withdrawals than deposits
share calculations where total shares can exceed assets
vault functions breaking asset-to-share ratio invariant
staking operations where rewards exceed intended distribution
balance invariant breakable
total supply mismatch with balances
balance sum exceeding total
invariant total equals sum breakable
balance calculation breaking invariant
total supply invariant violation
balance sum mismatch
invariant breakable in function
balance exceeding total supply
total supply not equal to sum
balance invariant violation
total supply mismatch vulnerability
balance calculation invariant
total supply sum mismatch
balance exceeding expected
invariant violation in balance
total supply invariant breakable
balance sum calculation error
invariant breakable balance
balance total mismatch
total supply calculation invariant
balance invariant breakable
total supply equals sum violated
balance calculation breaking sum
invariant violation total balance
```

### 2.2 Collateral Invariant Violations
**CWE-682**

#### Detection Phrases
```
collateral ratio invariant breakable
collateralization below minimum possible
collateral invariant violation
loan exceeding collateral value
collateral ratio breakable
collateralization invariant violation
collateral value invariant breakable
loan collateral ratio violation
collateral invariant breakable
collateralization below threshold possible
collateral ratio violation
loan exceeding collateral invariant
collateral value violation
collateralization invariant breakable
collateral ratio below minimum
loan collateral invariant breakable
collateral invariant violation possible
collateralization ratio breakable
collateral value ratio violation
loan collateral violation
collateral invariant ratio breakable
collateralization invariant violation possible
collateral ratio invariant violation
loan exceeding collateral ratio
collateral value invariant violation
collateralization ratio violation
collateral invariant breakable possible
loan collateral ratio invariant
collateral value ratio breakable
collateralization invariant breakable possible
```

### 2.3 Pool Invariant Violations
**CWE-682**

#### Detection Phrases
```
pool invariant K breakable
constant product invariant violation
pool reserves invariant breakable
AMM invariant violation
pool K value manipulable
constant product breakable
pool reserves ratio violation
AMM constant product invariant
pool invariant violation possible
constant product manipulable
pool reserves invariant violation
AMM invariant breakable
pool K calculation violation
constant product violation
pool reserves ratio breakable
AMM pool invariant violation
pool invariant calculation breakable
constant product invariant breakable
pool reserves invariant breakable possible
AMM invariant violation possible
pool K value violation
constant product breakable possible
pool reserves ratio invariant
AMM constant product breakable
pool invariant breakable via manipulation
constant product ratio violation
pool reserves invariant violation possible
AMM invariant calculation
pool K invariant breakable
constant product invariant violation possible
```

---

## 3. Missing Validation Checks

### 3.1 Balance Sufficiency Checks
**CWE-754**

#### Detection Phrases
```
withdrawal functions without balance sufficiency check
transfer functions without sender balance validation
functions assuming non-zero values without explicit checks
operations on expired or invalid state without validation
withdrawal without balance check
transfer without sufficient balance validation
balance check missing on withdrawal
transfer without balance verification
withdrawal allowing negative balance
transfer without sender balance check
balance validation missing
transfer without checking balance
withdrawal exceeding balance possible
transfer without balance sufficiency
balance check absent on withdrawal
transfer without verifying balance
withdrawal without balance validation
transfer without sender verification
balance sufficiency check missing
transfer without balance check
withdrawal without checking balance
transfer without sufficient funds check
balance verification missing
transfer without balance validation
withdrawal without balance verification
transfer without funds check
balance check missing
transfer without verifying sender balance
withdrawal allowing overdraft
transfer without balance sufficiency check
```

### 3.2 Return Value Checks
**CWE-252**

#### Detection Phrases
```
external view calls with results used without validation
create2 deployment without checking returned address
abi.decode results used without sanity checks
return value not validated before use
external call return unchecked
create2 address not verified
abi.decode without validation
return value used directly
external call result unchecked
create2 return not checked
abi.decode result unchecked
return value assumption
external call return not validated
create2 deployment unchecked
abi.decode without sanity check
return value not checked
external call result not verified
create2 address unchecked
abi.decode result assumption
return value validation missing
external call return ignored
create2 not verified
abi.decode unchecked
return value unchecked
external call result ignored
create2 address not validated
abi.decode validation missing
return value not verified
external call return assumption
create2 return unchecked
```

### 3.3 Boundary Condition Checks
**CWE-754**

#### Detection Phrases
```
boundary condition not validated
edge case not handled
boundary value not checked
edge condition missing validation
boundary condition vulnerability
edge case validation missing
boundary value unchecked
edge condition not handled
boundary condition check missing
edge case not validated
boundary value validation missing
edge condition vulnerability
boundary condition not handled
edge case unchecked
boundary value not validated
edge condition missing check
boundary condition edge case
edge case not handled properly
boundary value edge case
edge condition not validated
boundary condition missing validation
edge case handling missing
boundary value edge unchecked
edge condition unchecked
boundary condition not checked
edge case edge condition
boundary value not handled
edge condition handling missing
boundary condition validation missing
edge case boundary not checked
```

---

## 4. Business Logic Flaws

### 4.1 Ordering & Sequencing Flaws
**CWE-840**

#### Detection Phrases
```
operations executable in wrong order
sequence of operations bypassable
order of operations exploitable
operations sequence not enforced
order dependent logic bypassable
sequence violation possible
operations order not validated
sequence of steps skippable
order of execution exploitable
operations sequence violation
order dependent vulnerability
sequence not enforced properly
operations order vulnerability
sequence of operations not enforced
order of steps bypassable
sequence violation vulnerability
operations order not enforced
sequence skipping possible
order of operations not validated
sequence of execution bypassable
order dependent flaw
sequence enforcement missing
operations order exploitable
sequence of operations bypassable
order of operations flaw
sequence validation missing
operations sequence not validated
sequence of operations violation
order validation missing
sequence of steps not enforced
```

### 4.2 Conditional Logic Flaws
**CWE-840**

#### Detection Phrases
```
conditional logic bypassable
condition check exploitable
conditional logic vulnerability
condition bypass possible
conditional check bypassable
condition logic flaw
conditional logic flaw
condition exploitable
conditional bypass vulnerability
condition check flaw
conditional logic exploitable
condition bypass vulnerability
conditional check vulnerability
condition logic bypass
conditional logic condition
condition check bypassable
conditional bypass condition
condition logic vulnerability
conditional check condition
condition bypass flaw
conditional logic bypass
condition check bypass
conditional condition flaw
condition logic exploitable
conditional check exploitable
condition bypass condition
conditional logic check
condition check vulnerability
conditional bypass logic
condition logic check
```

### 4.3 Protocol Interaction Flaws
**CWE-840**

#### Detection Phrases
```
protocol interaction assumption incorrect
external protocol integration flaw
protocol interaction vulnerability
external integration assumption
protocol interaction logic flaw
external protocol assumption wrong
protocol integration vulnerability
external interaction flaw
protocol interaction incorrect
external protocol integration assumption
protocol logic interaction flaw
external protocol vulnerability
protocol interaction assumption
external integration vulnerability
protocol logic flaw
external protocol interaction flaw
protocol interaction integration
external integration assumption wrong
protocol assumption vulnerability
external protocol logic flaw
protocol integration logic flaw
external interaction assumption
protocol interaction vulnerability assumption
external protocol flaw
protocol logic vulnerability
external integration logic flaw
protocol assumption incorrect
external protocol assumption
protocol interaction logic
external integration flaw
```

---

## 5. Accounting Errors

### 5.1 Double Counting
**CWE-682**

#### Detection Phrases
```
double counting in balance calculation
value counted twice in accounting
double counting vulnerability
balance double counted
double counting in calculation
value counted multiple times
double accounting error
balance counted twice
double counting accounting
value double counted
double counting in balance
balance accounting double
double counting error
value counted twice in balance
double counting balance calculation
balance double counting vulnerability
double counting in value
value double counted error
double counting accounting error
balance counted multiple times
double counting in accounting
value accounting double counted
double counting calculation error
balance double counted vulnerability
double counting value calculation
value double counting error
double counting in total
balance double counting error
double counting total calculation
value double counted in accounting
```

### 5.2 Missing Accounting Updates
**CWE-682**

#### Detection Phrases
```
accounting update missing
balance not updated after operation
accounting not synchronized
balance update missing
accounting out of sync
balance not updated properly
accounting update absent
balance synchronization missing
accounting not updated
balance update absent
accounting synchronization missing
balance not synchronized
accounting update not performed
balance update not performed
accounting balance mismatch
balance update missing after operation
accounting not updated properly
balance accounting mismatch
accounting update not synchronized
balance not updated on operation
accounting missing update
balance update synchronization
accounting not synchronized properly
balance update missing operation
accounting update mismatch
balance not updated after
accounting balance update
balance accounting not updated
accounting update missing after
balance update accounting missing
```

### 5.3 Rounding Accumulation
**CWE-682**

#### Detection Phrases
```
rounding errors accumulating over time
accumulated rounding error
rounding accumulation vulnerability
error accumulation from rounding
rounding errors accumulating
accumulated error from rounding
rounding accumulation error
error accumulation vulnerability
rounding accumulating over transactions
accumulated rounding vulnerability
rounding error accumulation
error accumulating from rounding
rounding accumulation over time
accumulated error vulnerability
rounding errors over time
error accumulation rounding
rounding accumulating vulnerability
accumulated rounding error over time
rounding error accumulating
error accumulation over transactions
rounding accumulation transactions
accumulated error over time
rounding accumulating over time
error accumulation over time
rounding accumulation vulnerability over time
accumulated rounding over transactions
rounding error over transactions
error accumulating over time
rounding accumulating transactions
accumulated error accumulation
```

---

## 6. Shadowing & Inheritance Issues

### 6.1 Variable Shadowing
**CWE-710**

#### Detection Phrases
```
state variables shadowing inherited contract variables
local variable shadowing state variable
function parameter shadowing state variable
inherited variable shadowed by child
state variable shadowing parent
local shadowing state variable
parameter shadowing state
inherited shadowed variable
state shadowing inherited variable
local variable shadowing
parameter shadowing variable
inherited variable shadow
state variable shadow
local shadowing variable
parameter shadow state
inherited shadow variable
state shadow inherited
local shadow state
parameter shadowing state variable
inherited variable shadowing
state variable shadowing
local variable shadow
parameter shadow variable
inherited shadowing
state shadow variable
local shadow variable
parameter shadow
inherited variable shadow issue
state variable shadow issue
local shadowing issue
```

### 6.2 Function Override Issues
**CWE-710**

#### Detection Phrases
```
function overrides not calling super implementation
override missing super call
function override without super
override not calling parent
function override super missing
override missing parent call
function override vulnerability
override not calling super
function override without parent
override super call missing
function override missing super
override parent call missing
function override flaw
override not calling parent implementation
function override super call missing
override missing super implementation
function override without super call
override parent implementation missing
function override issue
override super missing
function override parent missing
override calling super missing
function override vulnerability super
override missing parent implementation
function override without calling super
override parent call vulnerability
function override super
override super implementation missing
function override calling super
override parent super missing
```

### 6.3 Diamond Inheritance
**CWE-710**

#### Detection Phrases
```
diamond inheritance with conflicting function implementations
multiple inheritance conflict
diamond inheritance vulnerability
multiple inheritance function conflict
diamond inheritance conflict
multiple inheritance issue
diamond pattern conflict
multiple inheritance vulnerability
diamond inheritance function conflict
multiple inheritance conflict issue
diamond inheritance issue
multiple inheritance function issue
diamond pattern vulnerability
multiple inheritance pattern conflict
diamond inheritance pattern
multiple inheritance diamond conflict
diamond function conflict
multiple inheritance function vulnerability
diamond inheritance vulnerability conflict
multiple inheritance conflict vulnerability
diamond pattern function
multiple inheritance diamond issue
diamond inheritance function
multiple inheritance pattern issue
diamond conflict vulnerability
multiple inheritance function conflict issue
diamond inheritance conflict issue
multiple inheritance diamond vulnerability
diamond inheritance pattern conflict
multiple inheritance conflict pattern
```

---

## 7. Selfdestruct Vulnerabilities

### 7.1 Unprotected Selfdestruct
**CWE-749**

#### Detection Phrases
```
selfdestruct callable by non-admin accounts
selfdestruct without access control
selfdestruct callable by anyone
selfdestruct missing authorization
selfdestruct without protection
selfdestruct accessible to attacker
selfdestruct without access gate
selfdestruct callable without restriction
selfdestruct missing access control
selfdestruct without authorization
selfdestruct accessible without auth
selfdestruct callable by attacker
selfdestruct missing protection
selfdestruct without auth check
selfdestruct accessible publicly
selfdestruct callable externally without check
selfdestruct missing auth
selfdestruct without restriction
selfdestruct accessible by anyone
selfdestruct callable without auth
selfdestruct missing access gate
selfdestruct without check
selfdestruct accessible without restriction
selfdestruct callable publicly
selfdestruct missing restriction
selfdestruct without gate
selfdestruct accessible to all
selfdestruct callable without protection
selfdestruct missing check
selfdestruct without proper authorization
```

### 7.2 Forced Ether via Selfdestruct
**CWE-749**

#### Detection Phrases
```
force-ether attacks via selfdestruct to contract
ether forcibly sent via selfdestruct
forced ether via destruction
ether balance manipulation via selfdestruct
forced ether attack
ether sent via selfdestruct
forced balance via selfdestruct
ether injection via destruction
forced ether to contract
ether manipulation via selfdestruct
forced ether vulnerability
ether balance forced
forced balance attack
ether via selfdestruct attack
forced ether balance
ether injection attack
forced ether via destruction
ether balance attack
forced balance vulnerability
ether selfdestruct attack
forced ether manipulation
ether forced to contract
forced balance selfdestruct
ether attack via selfdestruct
forced ether contract
ether injection selfdestruct
forced balance via destruction
ether manipulation attack
forced ether injection
ether forced balance
```

---

## 8. Contract Existence Checks

### 8.1 extcodesize Issues
**CWE-749**

#### Detection Phrases
```
extcodesize checks vulnerable to constructor context
extcodesize zero in constructor
extcodesize check bypassable
extcodesize during construction
extcodesize vulnerability
extcodesize check insufficient
extcodesize constructor bypass
extcodesize check during construction
extcodesize vulnerability constructor
extcodesize check constructor
extcodesize bypass possible
extcodesize insufficient check
extcodesize during deploy
extcodesize check vulnerability
extcodesize deploy bypass
extcodesize check during deploy
extcodesize vulnerability during construction
extcodesize check bypass
extcodesize during constructor
extcodesize check insufficient during
extcodesize constructor vulnerability
extcodesize check during constructor
extcodesize vulnerability deploy
extcodesize check deploy
extcodesize deploy vulnerability
extcodesize check during deployment
extcodesize vulnerability during deploy
extcodesize check constructor bypass
extcodesize during deployment
extcodesize check vulnerability constructor
```

### 8.2 Contract vs EOA Assumptions
**CWE-749**

#### Detection Phrases
```
assuming address is EOA when could be contract
assuming address is contract when could be EOA
address type assumption incorrect
EOA assumption vulnerability
contract assumption incorrect
address type check missing
EOA contract assumption
contract EOA assumption
address assumption vulnerability
EOA assumption incorrect
contract assumption vulnerability
address type assumption
EOA contract confusion
contract EOA confusion
address assumption incorrect
EOA assumption issue
contract assumption issue
address type confusion
EOA contract type confusion
contract EOA type confusion
address assumption issue
EOA type assumption
contract type assumption
address type incorrect
EOA contract type assumption
contract EOA type assumption
address EOA assumption
EOA assumption check
contract type check
address type vulnerability
```

---

## 9. Default Value Issues

### 9.1 Uninitialized Storage
**CWE-665**

#### Detection Phrases
```
storage variable used before initialization
uninitialized storage pointer
storage variable default zero used
uninitialized storage vulnerability
storage used before set
uninitialized storage issue
storage default value vulnerability
uninitialized storage variable
storage initialization missing
uninitialized storage pointer vulnerability
storage variable uninitialized
uninitialized storage used
storage not initialized
uninitialized storage default
storage initialization issue
uninitialized storage usage
storage variable not initialized
uninitialized storage variable used
storage default uninitialized
uninitialized storage value
storage initialization vulnerability
uninitialized variable storage
storage not set before use
uninitialized storage issue vulnerability
storage variable default vulnerability
uninitialized storage default zero
storage default value issue
uninitialized pointer storage
storage initialization not performed
uninitialized storage pointer issue
```

### 9.2 Boolean Default Issues
**CWE-665**

#### Detection Phrases
```
boolean default false causing logic flaw
uninitialized boolean vulnerability
boolean default value issue
uninitialized bool false
boolean initialization missing
uninitialized boolean default
boolean default vulnerability
uninitialized bool vulnerability
boolean default false vulnerability
uninitialized boolean issue
boolean default logic flaw
uninitialized bool issue
boolean initialization vulnerability
uninitialized boolean logic
boolean default false issue
uninitialized bool logic
boolean default flaw
uninitialized boolean flaw
boolean initialization issue
uninitialized bool default false
boolean default value flaw
uninitialized boolean default false
boolean default issue
uninitialized bool flaw
boolean initialization flaw
uninitialized boolean value
boolean default vulnerability logic
uninitialized bool value
boolean default logic issue
uninitialized boolean default value
```

---

## 10. Event & Logging Issues

### 10.1 Missing Events
**CWE-778**

#### Detection Phrases
```
state change without event emission
critical operation without logging
state modification no event
critical function without event
state change event missing
critical operation event missing
state modification without event
critical function no event
state change no logging
critical operation logging missing
state modification event missing
critical function event missing
state change without logging
critical operation no logging
state modification no logging
critical function logging missing
state change event absent
critical operation event absent
state modification event absent
critical function event absent
state change logging absent
critical operation logging absent
state modification logging absent
critical function logging absent
state change without event
critical operation without event
state modification without logging
critical function without logging
state change logging missing
critical operation without log
```

### 10.2 Incorrect Event Parameters
**CWE-778**

#### Detection Phrases
```
event emitting wrong value
event parameters incorrect
event emitting incorrect data
event parameters wrong
event incorrect value
event parameters incorrect data
event emitting wrong data
event parameters value wrong
event incorrect parameters
event parameters data wrong
event emitting incorrect value
event parameters incorrect value
event wrong value emitted
event parameters wrong value
event incorrect data emitted
event parameters data incorrect
event emitting wrong parameter
event parameters incorrect parameters
event wrong data emitted
event parameters wrong data
event incorrect value emitted
event parameters value incorrect
event emitting incorrect parameter
event parameters incorrect parameter
event wrong parameter emitted
event parameters parameter wrong
event incorrect emission
event parameters emission incorrect
event emitting wrong values
event parameters values wrong
```

---

## Complex Query Examples for Logic & State Lens

### Query 1: State Transition Validation
```json
{
  "query_kind": "logic",
  "node_types": ["Function"],
  "match": {
    "all": [
      {"property": "modifies_state_machine_variable", "op": "eq", "value": true}
    ],
    "none": [
      {"property": "validates_current_state", "op": "eq", "value": true},
      {"property": "enforces_valid_transition", "op": "eq", "value": true}
    ]
  },
  "explain_mode": true
}
```

### Query 2: Invariant Violation Risk
```json
{
  "query_kind": "logic",
  "node_types": ["Function"],
  "match": {
    "all": [
      {"property": "modifies_balance_state", "op": "eq", "value": true}
    ],
    "none": [
      {"property": "maintains_balance_invariant", "op": "eq", "value": true}
    ]
  },
  "explain_mode": true
}
```

### Query 3: Variable Shadowing
```json
{
  "query_kind": "logic",
  "node_types": ["Contract"],
  "match": {
    "all": [
      {"property": "has_inherited_contracts", "op": "eq", "value": true},
      {"property": "shadows_parent_variable", "op": "eq", "value": true}
    ]
  },
  "explain_mode": true
}
```

---

## Pattern Pack: Logic & State Lens Complete

```yaml
# Save as patterns/logic-state-lens.yaml
patterns:
  - id: logic-001
    name: Invalid State Transition
    severity: high
    cwe: [840]

  - id: logic-002
    name: Balance Invariant Violation
    severity: high
    cwe: [682]

  - id: logic-003
    name: Missing Balance Check
    severity: medium
    cwe: [754]

  - id: logic-004
    name: Double Counting Error
    severity: high
    cwe: [682]

  - id: logic-005
    name: Variable Shadowing
    severity: medium
    cwe: [710]

  - id: logic-006
    name: Unprotected Selfdestruct
    severity: critical
    cwe: [749]

  - id: logic-007
    name: extcodesize Bypass
    severity: medium
    cwe: [749]

  - id: logic-008
    name: Uninitialized Storage
    severity: high
    cwe: [665]

  - id: logic-009
    name: Missing Event Emission
    severity: low
    cwe: [778]

  - id: logic-010
    name: Incomplete State Cleanup
    severity: medium
    cwe: [840]
```
