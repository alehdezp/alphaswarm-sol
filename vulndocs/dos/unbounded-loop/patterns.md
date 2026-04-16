# Patterns: DoS via Unbounded Loop

## Crowdfund Refund Loop DoS

**Vulnerable Pattern:**
```solidity
function refundDos() public {
    for(uint i; i < refundAddresses.length; i++) {
        require(refundAddresses[i].transfer(refundAmount[refundAddresses[i]]));
    }
}
```

**Attack**: Single address with reverting fallback stalls entire refund process

**Operations**:
- `LOOP_WITH_EXTERNAL_CALLS`
- `TRANSFERS_VALUE_OUT` in loop
- Loop bound depends on array length (unbounded)

**Safe Patterns:**

### 1. Pull Pattern

```solidity
function withdraw() external {
    uint refund = refundAmount[msg.sender];
    refundAmount[msg.sender] = 0;
    msg.sender.transfer(refund);
}
```

### 2. Iterator Pattern

```solidity
uint256 nextIdx;
function refundSafe() public {
    uint256 i = nextIdx;
    while(i < refundAddresses.length && gasleft() > 200000) {
        refundAddresses[i].transfer(refundAmount[i]);
        i++;
    }
    nextIdx = i;
}
```

**Note**: Iterator pattern protects against gas limit DoS but NOT against external revert DoS. Pull pattern is safer.
