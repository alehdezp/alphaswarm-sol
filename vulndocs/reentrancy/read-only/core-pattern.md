# Read-Only Reentrancy

## Vulnerability Pattern

**Core Issue:** View function reads state during callback when state is temporarily inconsistent, returning manipulated values.

**Vulnerable Pattern:**
```solidity
// Pool contract
function removeLiquidity() external {
    uint256 lpAmount = lpBalances[msg.sender];
    _burnLP(lpAmount);
    msg.sender.call{value: ethAmount}("");  // Callback here
    _updateReserves();  // State inconsistent during callback
}

function getVirtualPrice() public view returns (uint256) {
    return totalAssets / totalSupply;  // Reads stale totalSupply
}

// External lending protocol reads price during callback
// Gets inflated price due to LP burned but reserves not updated
```

**Why Vulnerable:**
- View function has no reentrancy guard (read-only)
- State temporarily inconsistent between burn and reserve update
- External protocols read stale/manipulated price via view

**Safe Pattern:**
```solidity
uint256 private _lock;

modifier readProtected() {
    require(_lock != 2, "Read reentrancy");
    _;
}

function removeLiquidity() external {
    _lock = 2;  // Lock reads too
    // ... operations ...
    _lock = 1;
}

function getVirtualPrice() public view readProtected returns (uint256) {
    return totalAssets / totalSupply;
}
```

## Detection Signals

**Tier A (Deterministic):**
- `view_function_reads_modified_state: true`
- `external_call_before_state_sync: true`
- `view_has_reentrancy_protection: false`

**Behavioral Signature:**
```
F1:W:partial_state -> F1:X:callback -> [F2:R:stale_view] -> F1:W:complete
```

## Fix

1. Complete all state updates before external calls
2. Lock that also blocks view function reads
3. Use EIP-4626 virtual shares to prevent price manipulation
4. Snapshot state for external queries

**Real-world:** Curve LP Oracle (2022)
