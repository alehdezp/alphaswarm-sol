# Allocation Delay Exploitation

## Vulnerability Pattern

**Core Issue:** Operators allocate stake to AVS but stakers can withdraw during 17.5-day delay before slashing activates.

**Vulnerable Pattern:**
```solidity
uint256 constant ALLOCATION_DELAY = 17.5 days;

function allocateStake(OperatorSet set) external {
    allocationTimestamp = block.timestamp;
    // Slashing only possible after ALLOCATION_DELAY
    // Staker can still withdraw during this window
}

function withdraw() external {
    // No check for pending allocations
    _transferStake(msg.sender);
}
```

**Why Vulnerable:**
- Operator allocates stake to AVS operator set
- 17.5 day safety delay before allocation active
- During delay: operator provides service, staker can withdraw
- AVS cannot slash misbehavior in this window
- Economic security guarantee temporarily broken

**Safe Pattern:**
```solidity
function allocateStake(OperatorSet set) external {
    allocationTimestamp = block.timestamp;
    lockedUntil[msg.sender] = block.timestamp + ALLOCATION_DELAY;
}

function withdraw() external {
    require(block.timestamp >= lockedUntil[msg.sender], "Locked");
    _transferStake(msg.sender);
}
```

## Detection Signals

**Tier A (Deterministic):**
- `has_allocation_delay: true`
- `locks_stake_during_allocation: false`
- `allows_withdrawal_during_delay: true`

**Behavioral Signature:**
```
ALLOCATE_STAKE -> !LOCK_STAKE -> DELAY_PERIOD -> WITHDRAW -> UNSLASHABLE
```

## Fix

1. Lock staker withdrawals during allocation delay
2. Extend slashing retroactivity to cover allocation window
3. Require staker consent before operator allocation
4. Implement pro-rata slashing for partial withdrawals

**Real-world:** EigenLayer Mainnet (2025) - design constraint documented
