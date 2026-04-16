# Appendix A: Semantic Operations Reference

This appendix provides a complete reference for the semantic operations vocabulary used in AlphaSwarm.sol's Behavioral Security Knowledge Graph (BSKG).

---

## A.1 Operations Table

| Operation | Signature Code | Description | Evidence |
|-----------|----------------|-------------|----------|
| TRANSFERS_VALUE_OUT | X:out | ETH or token transfers out of contract | `transfer()`, `send()`, `call{value:}` |
| RECEIVES_VALUE_IN | X:in | Payable function or token receipt | `payable` modifier, token transfers in |
| READS_USER_BALANCE | R:bal | Reads balance mappings or balanceOf | `balances[user]`, `balanceOf()` |
| WRITES_USER_BALANCE | W:bal | Writes to balance mappings | `balances[user] = x` |
| CHECKS_PERMISSION | C:auth | require/assert or modifier-based auth | `onlyOwner`, `require(msg.sender == owner)` |
| MODIFIES_OWNER | M:own | Owner changes | `owner = newOwner` |
| MODIFIES_ROLES | M:role | Role assignments or access control updates | `grantRole()`, `revokeRole()` |
| CALLS_EXTERNAL | X:call | Any external call | `.call()`, external function calls |
| CALLS_UNTRUSTED | X:unk | External call to user-controlled address | Call to address from parameter |
| READS_EXTERNAL_VALUE | R:ext | Reads external contract values | External view calls |
| MODIFIES_CRITICAL_STATE | M:crit | Writes to privileged state | Owner, paused, fee updates |
| INITIALIZES_STATE | I:init | Initializer or constructor-like setup | `initialize()`, constructor |
| READS_ORACLE | R:orc | Oracle or price feed reads | `latestAnswer()`, Chainlink calls |
| LOOPS_OVER_ARRAY | L:arr | Unbounded or user-driven loops | `for (i=0; i < array.length; i++)` |
| USES_TIMESTAMP | U:time | block.timestamp access | `block.timestamp` |
| USES_BLOCK_DATA | U:blk | block.number, blockhash, prevrandao | `block.number`, `blockhash()` |
| PERFORMS_DIVISION | A:div | Division or precision-sensitive math | `/`, `div()` |
| PERFORMS_MULTIPLICATION | A:mul | Multiplication or overflow-sensitive math | `*`, `mul()` |
| VALIDATES_INPUT | V:in | Input validation checks | `require(amount > 0)` |
| EMITS_EVENT | E:evt | Event emission | `emit Transfer(...)` |

---

## A.2 Signature Code Reference

Complete signature code vocabulary used in behavioral signatures:

```
R:bal   read user balance
W:bal   write user balance
X:out   transfer value out
X:in    receive value in
X:call  external call
X:unk   call untrusted address
C:auth  permission check
M:own   modify owner
M:role  modify role
M:crit  modify critical state
R:orc   read oracle
R:ext   read external value
L:arr   loop over array
U:time  use timestamp
U:blk   use block data
A:div   division
A:mul   multiplication
V:in    validate input
E:evt   emit event
I:init  initializer pattern
```

### Code Prefixes

| Prefix | Category | Meaning |
|--------|----------|---------|
| R: | Read | Reading state or external data |
| W: | Write | Modifying state |
| X: | External | External calls or value transfer |
| C: | Check | Permission or validation checks |
| M: | Modify | State modification (privileged) |
| A: | Arithmetic | Mathematical operations |
| U: | Use | Block/timestamp data usage |
| V: | Validate | Input validation |
| E: | Emit | Event emission |
| I: | Initialize | Initialization patterns |
| L: | Loop | Iteration constructs |

---

## A.3 Signature Composition Examples

Behavioral signatures encode operation ordering using arrows to indicate sequence:

### Reentrancy Patterns

```
R:bal -> X:out -> W:bal       # Reentrancy candidate (read, call, write)
R:bal -> W:bal -> X:out       # Safe CEI pattern (read, write, call)
R:bal -> X:call -> W:bal      # General external call before write
```

### Access Control Patterns

```
C:auth -> M:crit              # Protected critical state update
C:auth -> M:own               # Protected ownership transfer
M:crit                        # Unprotected critical state (vulnerable)
M:own                         # Unprotected owner change (vulnerable)
C:auth -> M:role              # Protected role modification
```

### Value Flow Patterns

```
V:in -> R:bal -> W:bal -> X:out    # Full safe withdrawal flow
X:in -> W:bal                       # Deposit pattern
R:bal -> A:div -> X:out             # Balance with division (precision risk)
```

### Oracle Patterns

```
R:orc -> A:div -> X:out       # Oracle-driven value transfer
R:orc -> W:bal                # Oracle-based balance update
R:orc -> A:mul -> W:bal       # Oracle multiplication pattern
```

### Initialization Patterns

```
I:init -> M:own -> M:crit     # Standard initializer pattern
I:init -> M:role              # Initializer with role setup
```

### Complex Patterns

```
C:auth -> R:orc -> A:div -> X:out     # Protected oracle-driven transfer
L:arr -> X:call                        # Loop with external calls (DoS risk)
U:time -> C:auth                       # Time-based access control
R:ext -> A:mul -> W:bal               # External read with arithmetic
```

---

## A.4 Operation Categories

### Value Operations

Operations related to value (ETH/token) movement:

| Operation | Direction | Risk Level |
|-----------|-----------|------------|
| TRANSFERS_VALUE_OUT | Outbound | HIGH - funds leaving contract |
| RECEIVES_VALUE_IN | Inbound | MEDIUM - payable functions |
| READS_USER_BALANCE | N/A | LOW - read only |
| WRITES_USER_BALANCE | N/A | HIGH - state modification |

### Access Control Operations

Operations related to permissions and authorization:

| Operation | Scope | Risk if Missing |
|-----------|-------|-----------------|
| CHECKS_PERMISSION | Function-level | CRITICAL - unauthorized access |
| MODIFIES_OWNER | Contract-level | CRITICAL - ownership takeover |
| MODIFIES_ROLES | Role-level | HIGH - privilege escalation |

### External Interaction Operations

Operations involving external contracts:

| Operation | Trust Level | Reentrancy Risk |
|-----------|-------------|-----------------|
| CALLS_EXTERNAL | Varies | MEDIUM - depends on target |
| CALLS_UNTRUSTED | Low | HIGH - user-controlled target |
| READS_EXTERNAL_VALUE | Varies | LOW - read only |

### State Operations

Operations modifying contract state:

| Operation | Privilege Level | Typical Guards |
|-----------|-----------------|----------------|
| MODIFIES_CRITICAL_STATE | HIGH | onlyOwner, onlyAdmin |
| INITIALIZES_STATE | SETUP | initializer modifier |
| READS_ORACLE | EXTERNAL | Freshness checks |

---

## A.5 Evidence Extraction Rules

Each operation is identified through specific code patterns:

### TRANSFERS_VALUE_OUT

```solidity
// Direct patterns
address.transfer(amount)
address.send(amount)
address.call{value: amount}("")

// Token patterns
IERC20(token).transfer(recipient, amount)
IERC20(token).safeTransfer(recipient, amount)
```

### CHECKS_PERMISSION

```solidity
// Require patterns
require(msg.sender == owner, "Not owner");
require(hasRole(ADMIN_ROLE, msg.sender), "Not admin");

// Modifier patterns
modifier onlyOwner() { require(msg.sender == owner); _; }
modifier onlyRole(bytes32 role) { require(hasRole(role, msg.sender)); _; }
```

### READS_ORACLE

```solidity
// Chainlink patterns
priceFeed.latestRoundData()
priceFeed.latestAnswer()

// Uniswap TWAP patterns
oracle.consult(token, amountIn)
```

### MODIFIES_CRITICAL_STATE

```solidity
// State variables matched
owner = newOwner;
paused = true;
feeRate = newRate;
admin = newAdmin;
```

---

## A.6 Vocabulary Policy

The semantic operations vocabulary follows these stability rules:

1. **Stable Core**: The 20 operations listed above constitute the stable contract for patterns and signatures. These operations will not be removed or have their semantics changed in breaking ways.

2. **Additive Extensions**: New operations may be added to the vocabulary but must:
   - Define a unique signature code
   - Document evidence extraction rules
   - Be versioned with the release that introduces them
   - Not conflict with existing operation semantics

3. **Deprecation Process**: If an operation becomes obsolete:
   - It will be marked deprecated for at least one major version
   - Patterns using deprecated operations will emit warnings
   - Removal will only occur in major version updates

4. **Pattern Compatibility**: Patterns authored against core operations remain valid across versions. The vocabulary stability ensures detection rules do not break due to vocabulary changes.

---

## A.7 Detection Guidance by Operation

| Operation | Primary Vulnerabilities | Key Combinations |
|-----------|------------------------|------------------|
| TRANSFERS_VALUE_OUT | Reentrancy, Unauthorized withdrawal | + WRITES_USER_BALANCE (ordering) |
| CHECKS_PERMISSION | Access control bypass | Missing before M:crit, M:own |
| READS_ORACLE | Price manipulation | + A:div, + X:out |
| LOOPS_OVER_ARRAY | DoS via gas exhaustion | + X:call (unbounded gas) |
| MODIFIES_CRITICAL_STATE | Privilege escalation | Missing C:auth |
| CALLS_UNTRUSTED | Reentrancy, Arbitrary call | + W:bal after |
| USES_TIMESTAMP | Timing manipulation | + C:auth (time locks) |
| PERFORMS_DIVISION | Precision loss | + X:out (value impact) |
