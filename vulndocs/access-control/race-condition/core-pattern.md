# Temporal Access Control Race

## Vulnerability Pattern

**Core Issue:** Race condition during access control state transition allows unauthorized actions during role modification window.

**Vulnerable Pattern:**
```solidity
function setAdmin(address newAdmin) external onlyAdmin {
    admin = newAdmin;  // Immediate change
    // Window: old admin can still act if tx pending
}

function upgradeVia(address impl) external onlyAdmin {
    (bool s,) = impl.delegatecall(abi.encodeWithSignature("upgrade()"));
    // delegatecall changes context, potential backdoor
}
```

**Why Vulnerable:**
- Role changes not atomic with dependent operations
- Pending transactions execute with old permissions
- delegatecall during transition can install backdoors

**Safe Pattern:**
```solidity
function setAdmin(address newAdmin) external onlyAdmin {
    pendingAdmin = newAdmin;
    adminChangeTime = block.timestamp + TIMELOCK;
}

function acceptAdmin() external {
    require(msg.sender == pendingAdmin);
    require(block.timestamp >= adminChangeTime);
    admin = pendingAdmin;
    pendingAdmin = address(0);
}
```

## Detection Signals

**Tier A (Deterministic):**
- `modifies_roles: true`
- `uses_delegatecall: true`
- `atomic_operation: false`
- `has_timelock: false`

**Behavioral Signature:**
```
MODIFIES_ROLES -> (race_window) -> DELEGATECALL -> INCONSISTENT_STATE
```

## Fix

1. Implement timelock for role changes (24-48h)
2. Two-step role transfer (propose + accept)
3. Pause critical operations during role transition
4. No delegatecall to user-controlled targets

**Real-world:** MUD Framework (2023)
