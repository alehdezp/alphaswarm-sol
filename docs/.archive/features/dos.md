# DoS (Denial of Service) Detection

**Status**: ✅ Enhanced (December 2025)
**Properties**: 9
**Patterns**: 9
**Test Coverage**: 25 tests

---

## Overview

The DoS detection system identifies functions vulnerable to denial-of-service attacks through gas exhaustion, transaction blocking, or griefing vectors. Enhanced in December 2025 with comprehensive coverage of modern DoS attack patterns.

### Attack Vectors Covered

1. **Unbounded Loops** - User-controlled loop bounds causing gas exhaustion
2. **External Calls in Loops** - Block gas limit DoS
3. **Unbounded Deletion** - Delete operations in unbounded loops
4. **Revert DoS** - Failed external calls blocking execution (King of Ether)
5. **Gridlock Attacks** - Strict equality checks on balances (Edgeware Lockdrop)
6. **Transfer Gas Limit** - .transfer()/.send() fixed 2300 gas stipend
7. **Mass Operations** - Unbounded storage array operations
8. **View Function DoS** - Returning unbounded arrays from view functions
9. **User-Controlled Batch** - Batch operations without size limits

---

## Properties

### Core Loop Properties

#### `has_loops` (Boolean)
**Purpose**: Indicates function contains loop constructs
**Detection**: Any for/while loop in function body
**Usage**: Filter for functions with loops before deeper analysis

#### `loop_count` (Integer)
**Purpose**: Number of loop constructs in function
**Usage**: Complexity metric, identify functions with nested loops

#### `loop_bound_sources` (List[String])
**Purpose**: Sources of loop iteration bounds
**Values**: `["user_input", "storage_length", "constant", "unknown"]`
**Usage**: Distinguish paginated from unbounded loops

**Example**:
```solidity
function iterate(uint256 count) public {  // loop_bound_sources: ["user_input"]
    for (uint i = 0; i < count; i++) { ... }
}

function processAll() public {             // loop_bound_sources: ["storage_length"]
    for (uint i = 0; i < users.length; i++) { ... }
}
```

### Enhanced Properties (December 2025)

#### `has_unbounded_loop` (Boolean) ⭐ Core
**Purpose**: Detect truly unbounded loops (DoS risk)
**Detection**: Loop bounds from `user_input` or `unknown` WITHOUT `constant` or `storage_length`
**False Positive Fix**: Now works with `has_require_bounds` to exclude safe pagination

**Example - Vulnerable**:
```solidity
function process(uint256 count) public {
    // has_unbounded_loop = true (user_input, no bounds check)
    for (uint i = 0; i < count; i++) { ... }
}
```

**Example - Safe**:
```solidity
function paginate(uint256 start, uint256 end) public {
    require(end - start <= 100);  // has_require_bounds = true
    // has_unbounded_loop = false (bounded by require)
    for (uint i = start; i < end; i++) { ... }
}
```

#### `has_require_bounds` (Boolean) ⭐ NEW Dec 2025
**Purpose**: Detect require() statements bounding loop parameters
**Detection**: Looks for patterns like `require(param <= MAX)` or `require(end - start <= LIMIT)`
**Impact**: Reduces false positives for properly bounded pagination

**Detection Logic**:
1. Check require() statements mention loop parameters
2. Look for bound operators: `<=`, `<`, `>=`, `>`
3. Identify bound limits: `MAX`, `LIMIT`, numeric constants
4. Return `true` if parameter is bounded

**Example**:
```solidity
function safe(uint256 start, uint256 end) public {
    require(end - start <= MAX_PAGE_SIZE);  // ← has_require_bounds = true
    for (uint i = start; i < end; i++) { ... }
}
```

#### `external_calls_in_loop` (Boolean)
**Purpose**: Detect external calls inside loops (block gas limit DoS)
**Detection**: Loop contains high-level or low-level external calls
**Risk**: Attacker can cause OOG by forcing many iterations

**Example**:
```solidity
function distribute() public {
    for (uint i = 0; i < recipients.length; i++) {
        recipients[i].transfer(amount);  // ← external_calls_in_loop = true
    }
}
```

#### `has_delete_in_loop` (Boolean)
**Purpose**: Detect delete operations in loops
**Detection**: Loop contains `delete` keyword or Delete IR
**Combined with**: `has_unbounded_deletion` for severity

#### `has_unbounded_deletion` (Boolean) ⭐ High Severity
**Purpose**: Detect unbounded delete in loops (high gas cost)
**Detection**: Loop has delete AND unbounded bounds
**Risk**: Delete refunds gas but consumes lot upfront (DoS)

**Example**:
```solidity
function clearAll() public {
    // has_unbounded_deletion = true (unbounded + delete)
    for (uint i = 0; i < data.length; i++) {
        delete data[i];
    }
}
```

#### `uses_transfer` (Boolean) ⭐ NEW Dec 2025
**Purpose**: Detect usage of .transfer() method
**Risk**: Fixed 2300 gas stipend, fails if recipient needs more gas
**Detection**: Scans function nodes and IR for `.transfer(`

**Example**:
```solidity
function pay(address recipient) public {
    recipient.transfer(amount);  // ← uses_transfer = true, DoS if recipient is contract
}
```

**Why Deprecated**:
- 2300 gas not enough for modern contracts (storage writes, logging)
- EIP-1884 increased SLOAD gas cost, breaking existing contracts
- Recommended: Use `.call{value: X}("")` with reentrancy protection

#### `uses_send` (Boolean) ⭐ NEW Dec 2025
**Purpose**: Detect usage of .send() method
**Risk**: Same as transfer (2300 gas), but returns bool instead of reverting
**Detection**: Scans function nodes and IR for `.send(`

**Example**:
```solidity
function tryPay(address recipient) public {
    bool success = recipient.send(amount);  // ← uses_send = true
    require(success);  // Still vulnerable, 2300 gas limit
}
```

#### `has_strict_equality_check` (Boolean) ⭐ NEW Dec 2025
**Purpose**: Detect strict equality checks on `address(this).balance`
**Risk**: Gridlock attack - attacker sends wei to break equality
**Detection**: Looks for `require(address(this).balance == X)`

**Real-World Example - Edgeware Lockdrop (2019)**:
```solidity
function withdraw() public {
    require(address(this).balance == expectedBalance);  // ← Gridlock vulnerability
    // Attacker sends 1 wei via selfdestruct, breaks equality forever
}
```

**Safe Alternative**:
```solidity
function withdraw() public {
    require(address(this).balance >= expectedBalance);  // ✓ Safe, uses >=
}
```

#### `state_mutability` (String) ⭐ NEW Dec 2025
**Purpose**: Normalized state mutability classification
**Values**: `"pure"`, `"view"`, `"payable"`, `"nonpayable"`
**Usage**: Enables view function DoS detection

**Detection Priority**:
1. Check Slither's `.pure` property → `"pure"`
2. Check Slither's `.view` property → `"view"`
3. Check Slither's `.payable` property → `"payable"`
4. Check `state_mutability` attribute → normalize
5. Default → `"nonpayable"`

**Example - View Function DoS**:
```solidity
function getAllUsers() public view returns (User[] memory) {
    // state_mutability = "view"
    // Risk: If users array is unbounded, can run out of gas
    return users;
}
```

---

## Patterns

### 1. dos-unbounded-loop (Medium Severity)

**Detection**:
```yaml
match:
  all:
    - property: has_unbounded_loop
      op: eq
      value: true
  none:
    - property: has_require_bounds  # ← Exclude safe pagination
      op: eq
      value: true
```

**Example**:
```solidity
// ✗ VULNERABLE
function processUsers(uint256 count) public {
    for (uint i = 0; i < count; i++) { ... }  // No bounds check
}

// ✓ SAFE
function processUsersPaginated(uint256 start, uint256 end) public {
    require(end - start <= 100);  // Bounded
    for (uint i = start; i < end; i++) { ... }
}
```

### 2. dos-external-call-in-loop (Medium Severity, SWC-128)

**Detection**:
```yaml
match:
  all:
    - property: has_loops
      op: eq
      value: true
    - property: external_calls_in_loop
      op: eq
      value: true
```

**Real-World Impact**: Block gas limit DoS, gas griefing

**Example**:
```solidity
// ✗ VULNERABLE
function distribute(address[] calldata recipients) public {
    for (uint i = 0; i < recipients.length; i++) {
        recipients[i].transfer(1 ether);  // External call in loop
    }
}
```

### 3. dos-unbounded-deletion (High Severity, SWC-128)

**Detection**:
```yaml
match:
  all:
    - property: has_unbounded_deletion
      op: eq
      value: true
```

**Example**:
```solidity
// ✗ VULNERABLE
function clearAll() public {
    for (uint i = 0; i < data.length; i++) {
        delete data[i];  // Unbounded delete
    }
}

// ✓ SAFE
function clearRange(uint256 start, uint256 end) public {
    require(end - start <= 50);
    for (uint i = start; i < end; i++) {
        delete data[i];
    }
}
```

### 4. dos-revert-failed-call (High Severity, SWC-113) ⭐ NEW

**Detection**:
```yaml
match:
  all:
    - property: has_external_calls
      op: eq
      value: true
  # Additional heuristics for revert-blocking patterns
```

**Real-World Example - King of Ether Throne**:
```solidity
// ✗ VULNERABLE
function becomeKing() public payable {
    require(msg.value > currentKing.bid);
    currentKing.addr.transfer(currentKing.bid);  // ← Can revert, blocks function
    currentKing = King(msg.sender, msg.value);
}
```

**Attack**: Malicious contract reverts on receive, blocks all future kings.

### 5. dos-strict-equality (Medium Severity, CWE-1077) ⭐ NEW

**Detection**:
```yaml
match:
  all:
    - property: has_strict_equality_check
      op: eq
      value: true
```

**Real-World Example**: Edgeware Lockdrop gridlock attack

### 6. dos-unbounded-mass-operation (High Severity, SWC-128) ⭐ NEW

**Detection**: Functions operating on entire unbounded storage arrays

**Example**:
```solidity
// ✗ VULNERABLE
function resetAll() public {
    for (uint i = 0; i < users.length; i++) {
        users[i].balance = 0;
    }
}
```

### 7. dos-array-return-unbounded (Medium Severity, CWE-770) ⭐ NEW

**Detection**:
```yaml
match:
  all:
    - property: state_mutability
      op: eq
      value: view
    # Returns unbounded array
```

**Example**:
```solidity
// ✗ VULNERABLE
function getAllUsers() public view returns (User[] memory) {
    return users;  // If users array is large, runs out of gas
}

// ✓ SAFE
function getUsers(uint256 start, uint256 count) public view returns (User[] memory) {
    require(count <= 100);
    User[] memory result = new User[](count);
    for (uint i = 0; i < count; i++) {
        result[i] = users[start + i];
    }
    return result;
}
```

### 8. dos-transfer-in-loop (Medium Severity, SWC-113) ⭐ NEW

**Detection**:
```yaml
match:
  all:
    - property: has_loops
      op: eq
      value: true
    - property: uses_transfer  # or uses_send
      op: eq
      value: true
```

**Why Vulnerable**: Fixed 2300 gas per transfer, recipient may need more.

### 9. dos-user-controlled-batch (High Severity, SWC-128) ⭐ NEW

**Detection**: Batch operations without size limits

**Example**:
```solidity
// ✗ VULNERABLE
function batchMint(address[] calldata recipients, uint256[] calldata amounts) public {
    for (uint i = 0; i < recipients.length; i++) {
        _mint(recipients[i], amounts[i]);
    }
}

// ✓ SAFE
function batchMint(address[] calldata recipients, uint256[] calldata amounts) public {
    require(recipients.length <= 50, "Batch too large");
    for (uint i = 0; i < recipients.length; i++) {
        _mint(recipients[i], amounts[i]);
    }
}
```

---

## Testing

### Test Contracts

**DosComprehensive.sol** (340 lines):
- 14 vulnerable function variants
- 7 safe alternative implementations
- 3 helper contracts (MaliciousReverter, GridlockAttacker, DosSafe)

**LoopDos.sol** (original):
- 5 loop pattern variants
- Backward compatibility testing

### Test Suite

**test_queries_dos_comprehensive.py** (17 tests):
- Property detection tests
- Pattern matching tests
- Negative tests (safe patterns)
- Edge case tests

**test_queries_dos.py** (2 tests):
- Original backward compatibility tests

**test_vkg_enhancements.py** (6 tests):
- New property validation
- Backward compatibility verification

### Running Tests

```bash
# All DoS tests
uv run python -m unittest discover tests -v -k dos

# Comprehensive only
uv run python -m unittest tests.test_queries_dos_comprehensive -v

# Specific pattern
uv run python -m unittest tests.test_queries_dos_comprehensive.DosComprehensiveTests.test_pattern_dos_unbounded_loop -v
```

---

## Query Examples

### Find Unbounded Loops

**VQL**:
```bash
uv run alphaswarm query "find functions where has_unbounded_loop and not has_require_bounds"
```

**JSON**:
```bash
uv run alphaswarm query '{
  "query_kind": "logic",
  "node_types": ["Function"],
  "match": {
    "all": [
      {"property": "has_unbounded_loop", "op": "eq", "value": true}
    ],
    "none": [
      {"property": "has_require_bounds", "op": "eq", "value": true}
    ]
  }
}'
```

### Find Transfer/Send Usage

```bash
uv run alphaswarm query "find functions where uses_transfer or uses_send"
```

### Find Gridlock Vulnerabilities

```bash
uv run alphaswarm query "pattern:dos-strict-equality"
```

### Lens Query (All DoS Issues)

```bash
uv run alphaswarm query "lens:DoS severity:high"
```

---

## Real-World Examples

### Edgeware Lockdrop (2019) - Gridlock Attack

**Vulnerability**: Strict equality on balance
```solidity
require(address(this).balance == expectedBalance);
```

**Attack**: Attacker sends 1 wei via selfdestruct, breaking equality forever.

**Detection**: `has_strict_equality_check = true`

### King of Ether Throne - Revert DoS

**Vulnerability**: Transfer in critical path
```solidity
previousKing.transfer(prize);  // Can revert
```

**Attack**: Malicious contract reverts on receive, blocks all transfers.

**Detection**: `has_external_calls = true` + revert pattern

### Gas Griefing - Unbounded Loops

**Vulnerability**: User-controlled loop bounds
```solidity
function process(uint256 count) public {
    for (uint i = 0; i < count; i++) { ... }
}
```

**Attack**: Pass massive count, consume all block gas.

**Detection**: `has_unbounded_loop = true`, `has_require_bounds = false`

---

## Mitigation Strategies

### 1. Bound All Loops
```solidity
require(end - start <= MAX_PAGE_SIZE);
```

### 2. Use .call Instead of .transfer/.send
```solidity
(bool success, ) = recipient.call{value: amount}("");
require(success);
```

### 3. Use >= Not == for Balance Checks
```solidity
require(address(this).balance >= expectedBalance);
```

### 4. Pagination for Large Operations
```solidity
function processPage(uint256 start, uint256 count) public {
    require(count <= 100);
    // Process [start, start + count)
}
```

### 5. Pull Over Push
```solidity
// Instead of pushing funds in loop:
function claim() public {
    uint256 amount = pending[msg.sender];
    pending[msg.sender] = 0;
    msg.sender.call{value: amount}("");
}
```

---

## Enhancement History

**December 2025** - DoS Detection V2:
- ✅ Added 5 new properties (has_require_bounds, uses_transfer, uses_send, has_strict_equality_check, state_mutability)
- ✅ Enhanced 1 property (has_external_calls now includes low-level calls)
- ✅ Added 6 new patterns (9 total)
- ✅ Created comprehensive test suite (25 tests)
- ✅ Zero breaking changes
- ✅ Reduced false positives (pagination detection)

**Coverage Improvement**:
- Before: 3 patterns, 5 vulnerable variants
- After: 9 patterns, 14 vulnerable variants + 7 safe variants
- Real-world: Covers Edgeware, King of Ether, gas griefing attacks

---

## References

- **CWE-400**: Uncontrolled Resource Consumption
- **CWE-703**: Improper Check or Handling of Exceptional Conditions
- **CWE-770**: Allocation of Resources Without Limits
- **CWE-834**: Excessive Iteration
- **CWE-1077**: Floating Point Comparison with Incorrect Operator
- **SWC-113**: DoS with Failed Call
- **SWC-128**: DoS with Block Gas Limit
- **OWASP SC Top 10 (2025)**: SC10 - Denial of Service

**Further Reading**:
- [DoS Taxonomy](../../tests/contracts/DOS_TAXONOMY.md)
- [Enhancement Details](../enhancements/2025-12-dos.md)
- [Consensys Best Practices](https://consensys.github.io/smart-contract-best-practices/attacks/denial-of-service/)
