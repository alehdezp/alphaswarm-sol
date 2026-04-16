# Patterns: Balance Manipulation

## Multiplicator Honeypot

**Vulnerable Pattern:**
```solidity
function multiplicate() payable {
    if(msg.value >= this.balance) { // Always false!
        msg.sender.transfer(this.balance + msg.value);
    }
}
```

**Issue**: `this.balance` already includes `msg.value` when condition is evaluated

**Operations**:
- `READS_BALANCE` during payable function execution
- `COMPARES_VALUE_WITH_BALANCE`
- Balance includes current transaction value

**Detection**:
- Property: `reads_balance_in_payable` = true
- Signature: `R:msg.value->R:balance->CMP`

**Fix**: Store old balance before function execution or use internal accounting

## Strict Equality Migration Check

See: [forced-ether-selfdestruct specific](specifics/forced-ether-selfdestruct/patterns.md)

## Balance-Dependent State Machine

**Vulnerable Pattern:**
```solidity
enum Phase { Deposit, Withdraw, Complete }

function advancePhase() {
    require(address(this).balance == expectedAmount);
    currentPhase = Phase.Withdraw;
}
```

**Issue**: Forced ether breaks phase transition

**Safe Pattern:**
```solidity
uint256 internal deposits;

function advancePhase() {
    require(deposits >= expectedAmount);
    currentPhase = Phase.Withdraw;
}
```
