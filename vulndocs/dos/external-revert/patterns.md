# Patterns: DoS via External Call Revert

## Auction Frontrunner Refund DoS

**Vulnerable Pattern:**
```solidity
// Refund current leader when outbid
if (currentFrontrunner != 0) {
    require(currentFrontrunner.send(currentBid)); // DoS vector
}
currentFrontrunner = msg.sender;
```

**Attack**: Frontrunner implements fallback that reverts, preventing anyone from outbidding

**Operations**:
- `TRANSFERS_VALUE_OUT` in loop/conditional
- `CALLS_EXTERNAL` with revert propagation (require/assert)

**Safe Pattern:**
```solidity
// Store refunds instead of pushing
refunds[currentFrontrunner] += currentBid;
currentFrontrunner = msg.sender;

// Separate withdrawal function
function withdraw() external {
    uint refund = refunds[msg.sender];
    refunds[msg.sender] = 0;
    msg.sender.send(refund);
}
```

## Hidden External Dependency DoS

**Vulnerable Pattern:**
```solidity
constructor(address _logContract) {
    TransferLog = Log(_logContract); // User-supplied address
}

function CashOut(uint _am) {
    // External call to user-controlled contract
    TransferLog.AddMessage(msg.sender, msg.value, "CashOut");
    // Critical logic follows
}
```

**Attack**: Malicious Log contract consumes all gas or reverts selectively

**Operations**:
- `CALLS_EXTERNAL` to user-supplied address
- External call in critical execution path
- No gas limit on external call

**Detection**:
- Property: `calls_user_supplied_address`
- Signature: `X:user_addr->logic` (external call before critical logic)
