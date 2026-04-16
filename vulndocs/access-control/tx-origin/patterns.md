# Patterns: tx.origin Authentication

## Vulnerable Pattern

```solidity
contract TxOriginVault {
    address public owner;
    mapping(address => uint256) public balances;

    constructor() {
        owner = msg.sender;
    }

    // VULNERABLE: Uses tx.origin for authentication
    function transferTo(address to, uint256 amount) external {
        require(tx.origin == owner, "Not owner");  // VULNERABLE!
        require(balances[owner] >= amount, "Insufficient balance");

        balances[owner] -= amount;
        balances[to] += amount;
    }

    // VULNERABLE: Uses tx.origin for fund withdrawal
    function withdrawAll() external {
        require(tx.origin == owner, "Not owner");  // VULNERABLE!

        uint256 balance = address(this).balance;
        (bool success, ) = owner.call{value: balance}("");
        require(success, "Transfer failed");
    }
}
```

## Safe Pattern

```solidity
contract SafeVault {
    address public owner;
    mapping(address => uint256) public balances;

    constructor() {
        owner = msg.sender;
    }

    // SAFE: Uses msg.sender for authentication
    function transferTo(address to, uint256 amount) external {
        require(msg.sender == owner, "Not owner");  // CORRECT
        require(balances[owner] >= amount, "Insufficient balance");

        balances[owner] -= amount;
        balances[to] += amount;
    }

    // SAFE: Uses msg.sender for fund withdrawal
    function withdrawAll() external {
        require(msg.sender == owner, "Not owner");  // CORRECT

        uint256 balance = address(this).balance;
        (bool success, ) = owner.call{value: balance}("");
        require(success, "Transfer failed");
    }
}
```

## Attack Scenario

```solidity
// Attacker's phishing contract
contract TxOriginPhishing {
    TxOriginVault public vault;
    address public attacker;

    constructor(address _vault) {
        vault = TxOriginVault(_vault);
        attacker = msg.sender;
    }

    // Victim calls this thinking they're getting free tokens
    function claimFreeTokens() external {
        // tx.origin is still the victim!
        // This call will pass the tx.origin check in the vault
        vault.withdrawAll();
    }

    receive() external payable {
        // Receive stolen funds
        payable(attacker).transfer(address(this).balance);
    }
}
```

## Variations

### tx.origin in Modifier

```solidity
// Vulnerable - modifier uses tx.origin
modifier onlyOwner() {
    require(tx.origin == owner, "Not owner");  // VULNERABLE
    _;
}
```

### tx.origin for Admin Functions

```solidity
// Vulnerable - admin functions with tx.origin
function setFee(uint256 newFee) external {
    require(tx.origin == admin, "Not admin");  // VULNERABLE
    fee = newFee;
}
```
