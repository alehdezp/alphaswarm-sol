# Patterns: Forced Ether Reception

## Vulnerable Pattern: Migration Check

```solidity
function migrate_and_destroy() onlyOwner {
    assert(this.balance == totalSupply); // Can be broken by forced ether
    selfdestruct(owner);
}
```

**Operations**:
- `READS_BALANCE`
- `COMPARES_WITH_STRICT_EQUALITY`
- `USES_ASSERT`

**Attack Vector:**
```solidity
contract Attacker {
    function attack(address target) payable {
        selfdestruct(payable(target)); // Force ether to target
    }
}
```

## Vulnerable Pattern: State Machine

```solidity
function completeRound() {
    require(address(this).balance == expectedPayout);
    // Round completion logic
}
```

## Safe Pattern: Inequality Checks

```solidity
function migrate_and_destroy() onlyOwner {
    require(this.balance >= totalSupply); // Allow forced ether
    selfdestruct(owner);
}
```

## Safe Pattern: Internal Accounting

```solidity
uint256 internal totalDeposits;

function deposit() payable {
    totalDeposits += msg.value;
}

function withdraw() {
    require(totalDeposits >= amount);
    totalDeposits -= amount;
    // Use totalDeposits instead of balance
}
```
