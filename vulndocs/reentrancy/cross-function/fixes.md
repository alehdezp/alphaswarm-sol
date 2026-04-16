# Fixes: Cross-Function Reentrancy

## Recommended Fixes

### 1. Global ReentrancyGuard

**Effectiveness:** High
**Complexity:** Low

Apply nonReentrant to ALL functions that access shared state.

```solidity
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

contract SafeVault is ReentrancyGuard {
    function withdraw() external nonReentrant { /* ... */ }
    function transfer(address to, uint256 amount) external nonReentrant { /* ... */ }
    function borrow(uint256 amount) external nonReentrant { /* ... */ }
}
```

### 2. CEI Pattern on All Functions

**Effectiveness:** High
**Complexity:** Medium

Ensure all state updates happen before any external calls.

```solidity
function withdraw() external {
    uint256 bal = balances[msg.sender];
    balances[msg.sender] = 0;  // Update FIRST
    (bool success, ) = msg.sender.call{value: bal}("");
    require(success);
}
```

### 3. Mutex Pattern for Related Functions

**Effectiveness:** High
**Complexity:** Medium

Group related functions under same lock.

```solidity
mapping(address => bool) private _userLocked;

modifier userLock() {
    require(!_userLocked[msg.sender], "Locked");
    _userLocked[msg.sender] = true;
    _;
    _userLocked[msg.sender] = false;
}
```

## Best Practices

1. **Audit all functions accessing same state** - Treat them as a group
2. **Document state dependencies** - Clear mapping of which functions share state
3. **Global guard over selective** - When in doubt, protect all external functions
