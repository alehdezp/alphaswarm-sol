# DoS (Denial of Service) Vulnerability Taxonomy for Solidity

This document provides a comprehensive taxonomy of DoS vulnerabilities in Solidity smart contracts, based on research from CWE databases, SWC registry, OWASP SC Top 10 (2025), and real-world audit findings from 2023-2025.

## Classification Standards

### CWE Mappings
- **CWE-400**: Uncontrolled Resource Consumption
- **CWE-770**: Allocation of Resources Without Limits or Throttling
- **CWE-834**: Excessive Iteration
- **CWE-703**: Improper Check or Handling of Exceptional Conditions
- **CWE-1077**: Floating Point Comparison with Incorrect Operator

### SWC Mappings
- **SWC-113**: DoS with Failed Call
- **SWC-128**: DoS with Block Gas Limit

### OWASP SC Top 10
- **SC10:2025**: Denial of Service

## Vulnerability Categories

### 1. Gas Limit DoS - Unbounded Loops

**Description**: Loop bounds depend on user input or grow without limits, allowing attackers to cause out-of-gas errors.

**CWE**: CWE-834 (Excessive Iteration), CWE-400 (Uncontrolled Resource Consumption)

**Attack Vector**:
```solidity
// VULNERABLE
function processItems(uint256 n) external {
    for (uint256 i = 0; i < n; i++) {
        // Operations
    }
}
```

**Exploitation**: Attacker passes large value for `n`, causing transaction to exceed block gas limit.

**Severity**: Medium to High

**Mitigation**:
- Enforce maximum batch size
- Use pagination
- Process in multiple transactions
```solidity
// SAFE
function processItems(uint256 n) external {
    require(n <= MAX_BATCH_SIZE, "Batch too large");
    for (uint256 i = 0; i < n; i++) {
        // Operations
    }
}
```

**Pattern**: `dos-unbounded-loop`, `dos-user-controlled-batch`

---

### 2. Block Gas Limit DoS - External Calls in Loops

**Description**: External calls inside loops can amplify gas usage, especially if the array grows large.

**CWE**: CWE-834, CWE-770

**SWC**: SWC-128

**Attack Vector**:
```solidity
// VULNERABLE
function distributeRewards() external {
    for (uint256 i = 0; i < recipients.length; i++) {
        recipients[i].call{value: 1 ether}("");
    }
}
```

**Exploitation**: As `recipients` array grows, function eventually exceeds block gas limit and becomes permanently uncallable.

**Severity**: High

**Mitigation**:
- Use pagination
- Implement pull-over-push pattern
- Batch with bounds checking
```solidity
// SAFE
function distributeRewardsPaginated(uint256 start, uint256 end) external {
    require(end <= recipients.length && end - start <= 50, "Invalid range");
    for (uint256 i = start; i < end; i++) {
        recipients[i].call{value: 1 ether}("");
    }
}
```

**Pattern**: `dos-external-call-in-loop`

---

### 3. Unbounded Deletion

**Description**: Delete operations (SSTORE to zero) in unbounded loops are expensive and can cause DoS.

**CWE**: CWE-834, CWE-400

**Attack Vector**:
```solidity
// VULNERABLE
function clearAll(uint256 n) external {
    for (uint256 i = 0; i < n; i++) {
        delete data[i];
    }
}
```

**Exploitation**: Attacker passes large `n`, causing expensive storage deletions that exceed gas limits.

**Severity**: High

**Mitigation**:
- Paginate deletion operations
- Consider lazy deletion (mark as deleted without actual delete)
```solidity
// SAFE
function clearPaginated(uint256 start, uint256 end) external {
    require(end - start <= 100, "Batch too large");
    for (uint256 i = start; i < end; i++) {
        delete data[i];
    }
}
```

**Pattern**: `dos-unbounded-deletion`

---

### 4. DoS with Unexpected Revert (SWC-113)

**Description**: Push payment pattern where failed external call causes entire transaction to revert, allowing malicious recipients to block execution.

**CWE**: CWE-703 (Improper Check or Handling of Exceptional Conditions)

**SWC**: SWC-113

**Attack Vector**:
```solidity
// VULNERABLE
function refundAll() external {
    for (uint256 i = 0; i < users.length; i++) {
        (bool success, ) = users[i].call{value: refunds[users[i]]}("");
        require(success, "Refund failed"); // DoS vector
    }
}
```

**Exploitation**: Attacker deploys contract with reverting fallback/receive function, blocking all refunds.

**Real-World Example**: King of Ether throne contract vulnerability

**Severity**: High

**Mitigation**:
- Use pull-over-push pattern
- Handle failures gracefully (store failed refunds for later withdrawal)
```solidity
// SAFE: Pull pattern
function withdraw() external {
    uint256 amount = refunds[msg.sender];
    require(amount > 0, "No refund");
    refunds[msg.sender] = 0;
    (bool success, ) = msg.sender.call{value: amount}("");
    require(success, "Withdrawal failed");
}
```

**Pattern**: `dos-revert-failed-call`

---

### 5. DoS via Strict Equality (Gridlock Attack)

**Description**: Strict equality checks on contract balance can be manipulated via `selfdestruct`, causing permanent DoS.

**CWE**: CWE-1077 (Floating Point Comparison with Incorrect Operator)

**Attack Vector**:
```solidity
// VULNERABLE
function withdrawAll() external {
    assert(address(this).balance == totalDeposited); // Strict equality
    payable(msg.sender).transfer(totalDeposited);
}
```

**Exploitation**: Attacker uses `selfdestruct` to send ETH to contract without updating `totalDeposited`, breaking invariant permanently.

**Real-World Example**: Edgeware lockdrop contract (disclosed 2019)

**Severity**: Medium to High

**Mitigation**:
- Use `>=` instead of `==` for balance checks
```solidity
// SAFE
function withdrawAll() external {
    assert(address(this).balance >= totalDeposited);
    payable(msg.sender).transfer(totalDeposited);
}
```

**Pattern**: `dos-strict-equality`

---

### 6. DoS via Large Array Access Without Pagination

**Description**: View functions that return entire unbounded arrays or iterate over them can exceed gas limits as arrays grow.

**CWE**: CWE-770 (Allocation of Resources Without Limits or Throttling)

**Attack Vector**:
```solidity
// VULNERABLE
function getAllUsers() external view returns (address[] memory) {
    return users; // Entire array copied to memory
}

function sumAll() external view returns (uint256 total) {
    for (uint256 i = 0; i < data.length; i++) {
        total += data[i];
    }
}
```

**Exploitation**: As array grows, reading/copying entire array into memory exceeds block gas limit.

**Severity**: Medium

**Mitigation**:
- Implement pagination
- Return array slices
```solidity
// SAFE
function getUsersPaginated(uint256 start, uint256 end)
    external view returns (address[] memory) {
    require(end <= users.length && end - start <= 100, "Invalid range");
    address[] memory result = new address[](end - start);
    for (uint256 i = start; i < end; i++) {
        result[i - start] = users[i];
    }
    return result;
}
```

**Pattern**: `dos-array-return-unbounded`, `dos-unbounded-mass-operation`

---

### 7. DoS via Failed Transfer (transfer/send with Fixed Gas Stipend)

**Description**: Using `transfer()` or `send()` with fixed 2300 gas stipend can fail if recipient is contract with non-trivial fallback.

**CWE**: CWE-703

**Attack Vector**:
```solidity
// VULNERABLE
function distribute() external {
    for (uint256 i = 0; i < recipients.length; i++) {
        payable(recipients[i]).transfer(1 ether); // Fixed 2300 gas
    }
}
```

**Exploitation**: Recipient contracts with fallback functions requiring >2300 gas cause transfer to fail and revert entire transaction.

**Severity**: Medium

**Mitigation**:
- Use `.call{value: X}("")` instead of `transfer()`
- Handle failures gracefully
- Consider pull pattern
```solidity
// SAFE
function distribute() external {
    for (uint256 i = 0; i < recipients.length; i++) {
        (bool success, ) = recipients[i].call{value: 1 ether}("");
        if (!success) {
            // Store for pull withdrawal
            balances[recipients[i]] += 1 ether;
        }
    }
}
```

**Pattern**: `dos-transfer-in-loop`

---

### 8. DoS via Unbounded Mass Operations

**Description**: Functions that process entire storage arrays without bounds checking become increasingly expensive and eventually unusable.

**CWE**: CWE-834, SWC-128

**Attack Vector**:
```solidity
// VULNERABLE
function processAll() external {
    for (uint256 i = 0; i < items.length; i++) {
        items[i] = items[i] * 2; // Storage writes
    }
}
```

**Exploitation**: As `items` grows, storage operations exceed block gas limit.

**Severity**: High

**Mitigation**:
- Always paginate mass operations
- Enforce batch size limits
```solidity
// SAFE
function processPaginated(uint256 start, uint256 end) external {
    require(end <= items.length && end - start <= 50, "Invalid range");
    for (uint256 i = start; i < end; i++) {
        items[i] = items[i] * 2;
    }
}
```

**Pattern**: `dos-unbounded-mass-operation`

---

## Additional DoS Vectors (Awareness)

### Block Stuffing
**Description**: Attacker fills blocks with high-gas transactions to prevent legitimate transactions from being included.

**Mitigation**: Protocol-level defenses, not contract-level. Design systems to handle temporary unavailability.

### Front-Running DoS
**Description**: Attacker monitors mempool and front-runs critical transactions to cause reverts.

**Mitigation**: Use commit-reveal schemes, private mempools, or MEV protection.

**Note**: OWASP SC 2025 removed front-running from top 10 due to EIP-1559 and private mempools reducing impact.

### Storage Collision DoS
**Description**: Proxy pattern storage collision can cause unexpected state corruption leading to DoS.

**Mitigation**: Use proper storage layout patterns (e.g., EIP-1967), avoid storage collisions in upgradeable contracts.

---

## Pattern Detection Matrix

| Vulnerability | Pattern ID | BSKG Property | Severity | CWE | SWC |
|---------------|-----------|--------------|----------|-----|-----|
| Unbounded Loop | `dos-unbounded-loop` | `has_unbounded_loop` | Medium | CWE-834 | SWC-128 |
| External Call in Loop | `dos-external-call-in-loop` | `external_calls_in_loop` | Medium | CWE-834 | SWC-128 |
| Unbounded Deletion | `dos-unbounded-deletion` | `has_unbounded_deletion` | High | CWE-834 | SWC-128 |
| Revert Failed Call | `dos-revert-failed-call` | `has_external_calls` + `uses_call` | High | CWE-703 | SWC-113 |
| Strict Equality | `dos-strict-equality` | `has_strict_equality_check` | Medium | CWE-1077 | - |
| Unbounded Mass Op | `dos-unbounded-mass-operation` | `has_loops` + `writes_state` + `storage_length` | High | CWE-834 | SWC-128 |
| Array Return | `dos-array-return-unbounded` | `state_mutability: view` + array return | Medium | CWE-770 | - |
| Transfer in Loop | `dos-transfer-in-loop` | `has_loops` + uses `transfer/send` | Medium | CWE-703 | SWC-113 |
| User Controlled Batch | `dos-user-controlled-batch` | `has_loops` + `user_input` bounds | High | CWE-400 | SWC-128 |

---

## Test Coverage

### Test Contracts
- **DosComprehensive.sol**: Comprehensive test contract with all vulnerability patterns and safe alternatives
- **LoopDos.sol**: Original basic loop DoS tests (backward compatibility)

### Test Suite
- **tests/test_queries_dos_comprehensive.py**: Comprehensive test suite covering all DoS patterns

### Pattern Files
- `patterns/core/dos-unbounded-loop.yaml`
- `patterns/core/dos-external-call-in-loop.yaml`
- `patterns/core/dos-unbounded-deletion.yaml`
- `patterns/core/dos-revert-failed-call.yaml`
- `patterns/core/dos-strict-equality.yaml`
- `patterns/core/dos-unbounded-mass-operation.yaml`
- `patterns/core/dos-array-return-unbounded.yaml`
- `patterns/core/dos-transfer-in-loop.yaml`
- `patterns/core/dos-user-controlled-batch.yaml`

---

## Known Limitations

### BSKG Analysis Limitations

1. **Require Statement Bounds Not Recognized**
   - BSKG cannot currently distinguish between truly unbounded loops and loops with `require()` bounds on user input
   - Functions like `processPaginated(uint256 start, uint256 end)` with `require(end - start <= MAX)` are still flagged as unbounded
   - **Impact**: False positives for properly bounded functions

2. **Low-Level Call Detection**
   - `.call{value: X}("")` may not set `has_external_calls: true` in some cases
   - Use `external_calls_in_loop` and `state_write_after_external_call` as alternative indicators
   - **Impact**: Some patterns may need refinement

3. **State Mutability Property**
   - `state_mutability` property may not be set for view functions in current BSKG version
   - Use `visibility` as fallback
   - **Impact**: Pattern `dos-array-return-unbounded` may need additional refinement

4. **Transfer/Send Detection**
   - Detecting specific use of `transfer()` or `send()` requires AST-level analysis beyond current BSKG properties
   - Pattern `dos-transfer-in-loop` is defined but may need core enhancements
   - **Impact**: Manual review still needed for this pattern

### Proposed Enhancements

1. **Add `has_require_bounds` property** to distinguish between raw user input and validated input
2. **Enhance external call detection** to properly flag low-level calls in `has_external_calls`
3. **Add `state_mutability` property** for all functions
4. **Add `uses_transfer` and `uses_send` properties** to detect deprecated transfer methods
5. **Add `has_strict_equality_check` property** to detect dangerous equality comparisons

---

## References

### Standards
- [CWE-400: Uncontrolled Resource Consumption](https://cwe.mitre.org/data/definitions/400.html)
- [CWE-834: Excessive Iteration](https://cwe.mitre.org/data/definitions/834.html)
- [SWC-113: DoS with Failed Call](https://swcregistry.io/docs/SWC-113/)
- [SWC-128: DoS with Block Gas Limit](https://swcregistry.io/docs/SWC-128/)
- [OWASP SC10:2025 - Denial of Service](https://owasp.org/www-project-smart-contract-top-10/2025/en/src/SC10-denial-of-service.html)

### Research & Audit Reports
- [Consensys Smart Contract Best Practices - DoS](https://consensys.github.io/smart-contract-best-practices/attacks/denial-of-service/)
- [Trail of Bits - Avoiding Smart Contract Gridlock](https://blog.trailofbits.com/2019/07/03/avoiding-smart-contract-gridlock-with-slither/)
- [SlowMist - DoS Vulnerabilities in Solidity](https://www.slowmist.com/articles/solidity-security/Common-Vulnerabilities-in-Solidity-Denial-of-Service-DOS.html)

### Real-World Exploits
- Edgeware Lockdrop Gridlock (2019)
- King of Ether Throne DoS
- Various DeFi protocol gas griefing attacks

---

## Conclusion

DoS vulnerabilities in smart contracts can range from temporary inconveniences to permanent fund lockups. The most critical patterns to watch for are:

1. **Unbounded loops** over user-controlled or storage-length bounds
2. **External calls in loops** that can exceed block gas limit
3. **Push payment patterns** vulnerable to revert attacks
4. **Strict equality checks** on contract balance

Always prefer:
- **Pull-over-push** for value transfers
- **Pagination** for batch operations
- **Graceful failure handling** for external calls
- **Inequality checks** (`>=`, `<=`) over strict equality for balances

The AlphaSwarm.sol system detects these patterns automatically, but manual review is still essential for understanding context and validating fixes.
