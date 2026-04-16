// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title VaultLogicV1 - Implementation contract for proxy
/// @dev VULNERABILITY: Storage layout collision with proxy (B2)
/// @dev Proxy has slots [0]=implementation, [1]=proxyAdmin
/// @dev This contract's slots [0]=owner, [1]=totalDeposits will COLLIDE
contract VaultLogicV1 {
    // Slot 0: COLLIDES with proxy's implementation slot!
    address public owner;
    // Slot 1: COLLIDES with proxy's proxyAdmin slot!
    uint256 public totalDeposits;
    // Slot 2+: safe
    mapping(address => uint256) public balances;
    bool public initialized;

    /// @notice Initialize vault (replaces constructor for proxy pattern)
    /// @dev VULNERABILITY: No initializer protection - can be called multiple times
    function initialize(address _owner) external {
        // Missing: require(!initialized)
        owner = _owner;
        initialized = true;
    }

    /// @notice Deposit ETH
    function deposit() external payable {
        require(msg.value > 0, "Zero deposit");
        balances[msg.sender] += msg.value;
        totalDeposits += msg.value;
    }

    /// @notice Withdraw ETH
    /// @dev VULNERABILITY: Reentrancy when called through proxy
    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient");

        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Withdraw failed");

        balances[msg.sender] -= amount;
        totalDeposits -= amount;
    }

    /// @notice Admin withdrawal
    function adminWithdraw(uint256 amount) external {
        require(msg.sender == owner, "Not owner");
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Admin withdraw failed");
    }

    /// @notice Self-destruct (V1 migration)
    /// @dev VULNERABILITY: Missing access control
    function destroy() external {
        selfdestruct(payable(msg.sender));
    }
}
