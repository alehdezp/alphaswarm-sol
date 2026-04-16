# Patterns: Weak or Bypassable Modifier

## Vulnerable Pattern - Empty Modifier

```solidity
contract WeakAccess {
    address public owner;

    // VULNERABLE: Empty modifier provides no protection
    modifier onlyOwner() {
        // Nothing here!
        _;
    }

    function setOwner(address newOwner) external onlyOwner {
        owner = newOwner;  // Anyone can call despite modifier
    }
}
```

## Vulnerable Pattern - Wrong Comparison

```solidity
contract WrongComparison {
    address public owner;
    address public pendingOwner;

    // VULNERABLE: Uses != instead of ==
    modifier onlyOwner() {
        require(msg.sender != owner, "Not owner");  // WRONG!
        _;
    }

    function setFee(uint256 fee) external onlyOwner {
        // Actually allows everyone EXCEPT owner
    }
}
```

## Vulnerable Pattern - Bypassable State

```solidity
contract BypassableAccess {
    bool public restricted;
    address public owner;

    modifier whenRestricted() {
        require(restricted, "Not restricted");
        _;
    }

    // VULNERABLE: Anyone can toggle restricted flag
    function toggleRestricted() external {
        restricted = !restricted;
    }

    function adminAction() external whenRestricted {
        // Can be bypassed by toggling restricted off
    }
}
```

## Safe Pattern

```solidity
contract StrongAccess {
    address public owner;

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    function setOwner(address newOwner) external onlyOwner {
        require(newOwner != address(0), "Zero address");
        owner = newOwner;
    }
}
```

## Variations

### Modifier with Dead Code

```solidity
// Vulnerable - condition never triggers
modifier onlyOwner() {
    if (false) {  // Dead code
        require(msg.sender == owner, "Not owner");
    }
    _;
}
```

### Modifier Checking Wrong Variable

```solidity
address public owner;
address public admin;

// Vulnerable - checks admin instead of owner
modifier onlyOwner() {
    require(msg.sender == admin, "Not owner");  // Wrong variable!
    _;
}
```
