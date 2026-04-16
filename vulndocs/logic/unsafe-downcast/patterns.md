# Unsafe Downcasting - Patterns

## Vulnerable: Balance Storage

```solidity
// VULNERABLE
mapping(address => uint128) public balances;

function deposit(uint256 amount) external {
    uint128 bal = uint128(amount);  // Truncates if amount > 2^128-1
    balances[msg.sender] = bal;
}
```

## Vulnerable: Timestamp Storage

```solidity
// VULNERABLE
uint64 public deadline;

function setDeadline(uint256 timestamp) external {
    deadline = uint64(timestamp);  // Truncates if timestamp > 2^64-1
}
```

## Safe: OpenZeppelin SafeCast

```solidity
import "@openzeppelin/contracts/utils/math/SafeCast.sol";

function deposit(uint256 amount) external {
    uint128 bal = SafeCast.toUint128(amount);  // SAFE
    balances[msg.sender] = bal;
}
```

## Safe: Manual Validation

```solidity
function deposit(uint256 amount) external {
    require(amount <= type(uint128).max);  // SAFE
    balances[msg.sender] = uint128(amount);
}
```

## Comparison

| Pattern | Overflow Check | Safe? |
|---------|---------------|-------|
| uint128(value) | No | No |
| SafeCast.toUint128(value) | Yes (reverts) | Yes |
| require + uint128(value) | Yes (reverts) | Yes |
