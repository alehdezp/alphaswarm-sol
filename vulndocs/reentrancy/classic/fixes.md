# Fixes: Classic Reentrancy

## Recommended Fixes

### 1. Checks-Effects-Interactions Pattern (CEI)

**Effectiveness:** High
**Complexity:** Low

Reorder operations to update state before making external calls.

```solidity
function withdraw() external {
    uint256 bal = balances[msg.sender];  // Check
    require(bal > 0, "No balance");

    balances[msg.sender] = 0;  // Effect - update state FIRST

    (bool success, ) = msg.sender.call{value: bal}("");  // Interaction
    require(success, "Transfer failed");
}
```

### 2. ReentrancyGuard Modifier

**Effectiveness:** High
**Complexity:** Low

Use OpenZeppelin's ReentrancyGuard for functions with external calls.

```solidity
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

contract SafeVault is ReentrancyGuard {
    function withdraw() external nonReentrant {
        uint256 bal = balances[msg.sender];
        require(bal > 0, "No balance");

        (bool success, ) = msg.sender.call{value: bal}("");
        require(success, "Transfer failed");

        balances[msg.sender] = 0;
    }
}
```

### 3. Manual Lock Variable

**Effectiveness:** Medium (error-prone)
**Complexity:** Medium

Implement your own reentrancy guard when not using OpenZeppelin.

```solidity
bool private locked;

modifier noReentrancy() {
    require(!locked, "Reentrant call");
    locked = true;
    _;
    locked = false;
}

function withdraw() external noReentrancy {
    // ... function body
}
```

## Best Practices

1. **Always prefer CEI pattern** - It's the most elegant solution
2. **Use nonReentrant on all external-call functions** - Even if CEI is followed
3. **Mark all external call sites** - Document where reentrancy is possible
4. **Consider token hooks** - ERC777/ERC1155 callbacks need special attention
5. **Audit cross-function interactions** - Reentrancy can occur across functions

## Testing Recommendations

1. Write reentrancy attack test with malicious contract
2. Test all withdrawal/transfer functions
3. Use Foundry's `etch` to inject attacker contracts
4. Test with ERC777 tokens that have callbacks
