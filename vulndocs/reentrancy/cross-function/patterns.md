# Patterns: Cross-Function Reentrancy

## Vulnerable Pattern

```solidity
contract VulnerableVault {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    // Vulnerable: external call before state update
    function withdraw() external {
        uint256 bal = balances[msg.sender];
        (bool success, ) = msg.sender.call{value: bal}("");
        require(success);
        balances[msg.sender] = 0;  // Updated AFTER call
    }

    // This function can be entered during withdraw's external call
    function transfer(address to, uint256 amount) external {
        require(balances[msg.sender] >= amount);  // Reads stale balance!
        balances[msg.sender] -= amount;
        balances[to] += amount;
    }
}
```

**Attack Flow:**
1. Attacker deposits 1 ETH, balance = 1 ETH
2. Attacker calls withdraw()
3. During external call, attacker re-enters transfer()
4. transfer() sees balance = 1 ETH (not yet zeroed)
5. Attacker transfers 1 ETH to accomplice
6. withdraw() continues, zeros already-transferred balance
7. Result: Attacker got 1 ETH + transferred 1 ETH = 2x profit

## Safe Pattern

```solidity
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

contract SafeVault is ReentrancyGuard {
    mapping(address => uint256) public balances;

    // nonReentrant on ALL state-modifying external functions
    function withdraw() external nonReentrant {
        uint256 bal = balances[msg.sender];
        balances[msg.sender] = 0;
        (bool success, ) = msg.sender.call{value: bal}("");
        require(success);
    }

    function transfer(address to, uint256 amount) external nonReentrant {
        require(balances[msg.sender] >= amount);
        balances[msg.sender] -= amount;
        balances[to] += amount;
    }
}
```
