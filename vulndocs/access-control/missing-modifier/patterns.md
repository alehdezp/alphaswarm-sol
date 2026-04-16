# Patterns: Missing Access Control Modifier

## Vulnerable Pattern

```solidity
contract VulnerableVault {
    address public owner;
    uint256 public fee;

    // VULNERABLE: No access control on ownership transfer
    function setOwner(address newOwner) external {
        owner = newOwner;
    }

    // VULNERABLE: No access control on fee modification
    function setFee(uint256 newFee) external {
        fee = newFee;
    }

    // VULNERABLE: No access control on fund withdrawal
    function withdrawAll() external {
        (bool success, ) = msg.sender.call{value: address(this).balance}("");
        require(success, "Transfer failed");
    }
}
```

## Safe Pattern (Ownable)

```solidity
import "@openzeppelin/contracts/access/Ownable.sol";

contract SafeVault is Ownable {
    uint256 public fee;

    // SAFE: onlyOwner modifier restricts access
    function setFee(uint256 newFee) external onlyOwner {
        fee = newFee;
    }

    // SAFE: onlyOwner modifier restricts access
    function withdrawAll() external onlyOwner {
        (bool success, ) = owner().call{value: address(this).balance}("");
        require(success, "Transfer failed");
    }
}
```

## Safe Pattern (Inline Check)

```solidity
contract SafeVaultInline {
    address public owner;
    uint256 public fee;

    constructor() {
        owner = msg.sender;
    }

    // SAFE: Inline access control check
    function setFee(uint256 newFee) external {
        require(msg.sender == owner, "Not owner");
        fee = newFee;
    }
}
```

## Variations

### Missing Access on Admin Functions

```solidity
// Vulnerable - anyone can pause
function pause() external {
    paused = true;
}

// Vulnerable - anyone can add to whitelist
function addToWhitelist(address user) external {
    whitelist[user] = true;
}
```

### Missing Access on Token Minting

```solidity
// Vulnerable - unlimited minting
function mint(address to, uint256 amount) external {
    _mint(to, amount);
}
```

### Variable Shadowing Leading to Missing Access Control

**Honeypot Pattern:**
```solidity
contract Ownable {
    address public owner;

    modifier onlyOwner {
        require(msg.sender == owner);
        _;
    }
}

contract CEOThrone is Ownable {
    address public owner; // SHADOWING parent's owner!
    uint public largestStake;

    function Stake() public payable {
        if (msg.value > largestStake) {
            owner = msg.sender; // Updates CHILD owner, not parent
            largestStake = msg.value;
        }
    }

    // Uses parent's owner (never updated!)
    function withdraw() public onlyOwner {
        msg.sender.transfer(this.balance);
    }
}
```

**Issue**: Child contract redeclares `owner`, shadowing parent's `owner` variable. The `onlyOwner` modifier checks parent's owner (set in constructor), while `Stake()` updates child's owner.

**Operations**:
- `WRITES_PRIVILEGED_STATE` (child owner)
- `CHECKS_PERMISSION` (parent owner)
- Variable shadowing creates access control bypass

**Detection**:
- Property: `has_variable_shadowing` = true
- Signature: `W:shadow_var->!G:access` (writes shadowed variable without effective access control)

**Fix**: Don't redeclare inherited state variables. Modern Solidity compilers warn about this.
