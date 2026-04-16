// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title GuardedToken - Token with correct use of dangerous patterns (C6)
/// @dev Uses delegatecall, selfdestruct-style patterns, and complex access control
/// @dev ALL properly constrained - false positive control
contract GuardedToken {
    mapping(address => uint256) public balances;
    mapping(address => mapping(address => uint256)) public allowances;
    uint256 public totalSupply;
    string public name;
    string public symbol;
    address public owner;
    address public upgradeTarget;
    bool public migrationActive;
    bool private _locked;
    uint256 public constant MAX_SUPPLY = 1000000e18;

    modifier nonReentrant() {
        require(!_locked, "Reentrancy");
        _locked = true;
        _;
        _locked = false;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    event Transfer(address indexed from, address indexed to, uint256 amount);
    event Approval(address indexed owner, address indexed spender, uint256 amount);
    event MigrationStarted(address indexed target);

    constructor(string memory _name, string memory _symbol) {
        name = _name;
        symbol = _symbol;
        owner = msg.sender;
    }

    /// @notice Transfer tokens (looks dangerous with external call, is safe)
    function transfer(address to, uint256 amount) external returns (bool) {
        require(balances[msg.sender] >= amount, "Insufficient");
        balances[msg.sender] -= amount; // CEI: state before any effects
        balances[to] += amount;
        emit Transfer(msg.sender, to, amount);
        return true;
    }

    /// @notice Approve with race condition protection
    function approve(address spender, uint256 amount) external returns (bool) {
        // Safe: requires reset to 0 before changing to non-zero
        require(amount == 0 || allowances[msg.sender][spender] == 0, "Reset allowance first");
        allowances[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    /// @notice TransferFrom (properly bounded by allowance)
    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        require(allowances[from][msg.sender] >= amount, "Allowance exceeded");
        require(balances[from] >= amount, "Insufficient");
        allowances[from][msg.sender] -= amount;
        balances[from] -= amount;
        balances[to] += amount;
        emit Transfer(from, to, amount);
        return true;
    }

    /// @notice Mint (properly access controlled with supply cap)
    function mint(address to, uint256 amount) external onlyOwner {
        require(totalSupply + amount <= MAX_SUPPLY, "Exceeds max");
        totalSupply += amount;
        balances[to] += amount;
        emit Transfer(address(0), to, amount);
    }

    /// @notice Burn own tokens
    function burn(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient");
        balances[msg.sender] -= amount;
        totalSupply -= amount;
        emit Transfer(msg.sender, address(0), amount);
    }

    /// @notice Migration (C6: correct use of dangerous pattern)
    /// @dev delegatecall-LIKE pattern that is actually a regular call
    function startMigration(address target) external onlyOwner {
        require(target != address(0), "Zero address");
        require(!migrationActive, "Already migrating");
        upgradeTarget = target;
        migrationActive = true;
        emit MigrationStarted(target);
    }

    /// @notice Transfer ownership (properly guarded)
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "Zero address");
        owner = newOwner;
    }

    /// @notice Emergency token rescue (safe: only owner, only other tokens)
    function rescueTokens(address token, uint256 amount) external onlyOwner nonReentrant {
        require(token != address(this), "Cannot rescue self"); // Safe: can't drain own tokens
        (bool ok, ) = token.call(
            abi.encodeWithSignature("transfer(address,uint256)", owner, amount)
        );
        require(ok, "Rescue failed");
    }
}
