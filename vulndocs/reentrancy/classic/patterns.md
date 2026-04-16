# Patterns: Classic Reentrancy

## Vulnerable Pattern

```solidity
function withdraw() external {
    uint256 bal = balances[msg.sender];  // Read balance
    require(bal > 0, "No balance");

    // VULNERABLE: External call before state update
    (bool success, ) = msg.sender.call{value: bal}("");
    require(success, "Transfer failed");

    // State write AFTER external call - can be bypassed via reentrancy
    balances[msg.sender] = 0;
}
```

## Safe Pattern (CEI - Checks-Effects-Interactions)

```solidity
function withdraw() external {
    uint256 bal = balances[msg.sender];  // Check
    require(bal > 0, "No balance");

    // Effect: State update BEFORE external call
    balances[msg.sender] = 0;

    // Interaction: External call AFTER state is safe
    (bool success, ) = msg.sender.call{value: bal}("");
    require(success, "Transfer failed");
}
```

## Safe Pattern (ReentrancyGuard)

```solidity
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

contract SafeVault is ReentrancyGuard {
    mapping(address => uint256) public balances;

    function withdraw() external nonReentrant {
        uint256 bal = balances[msg.sender];
        require(bal > 0, "No balance");

        (bool success, ) = msg.sender.call{value: bal}("");
        require(success, "Transfer failed");

        balances[msg.sender] = 0;  // Even though after call, guard prevents reentrancy
    }
}
```

## Variations

### With Transfer Amount Parameter

```solidity
// Vulnerable
function withdraw(uint256 amount) external {
    require(balances[msg.sender] >= amount, "Insufficient");
    (bool success, ) = msg.sender.call{value: amount}("");
    require(success, "Transfer failed");
    balances[msg.sender] -= amount;  // VULNERABLE
}
```

### With Token Transfer

```solidity
// Vulnerable if token has hooks (ERC777)
function withdraw() external {
    uint256 bal = balances[msg.sender];
    token.transfer(msg.sender, bal);  // ERC777 tokensReceived hook
    balances[msg.sender] = 0;  // VULNERABLE
}
```
