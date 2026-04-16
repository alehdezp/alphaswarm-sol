// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title VaultLogicV1 (SAFE VARIANT)
contract VaultLogicV1_safe {
    // Storage gap to avoid proxy collision (EIP-1967 safe)
    uint256[50] private __gap;

    address public owner;
    uint256 public totalDeposits;
    mapping(address => uint256) public balances;
    bool public initialized;
    bool private _locked;

    modifier nonReentrant() { require(!_locked); _locked = true; _; _locked = false; }
    modifier onlyOwner() { require(msg.sender == owner, "Not owner"); _; }

    function initialize(address _owner) external {
        require(!initialized, "Already initialized"); // FIXED
        owner = _owner;
        initialized = true;
    }

    function deposit() external payable {
        require(msg.value > 0, "Zero deposit");
        balances[msg.sender] += msg.value;
        totalDeposits += msg.value;
    }

    function withdraw(uint256 amount) external nonReentrant { // FIXED
        require(balances[msg.sender] >= amount, "Insufficient");
        balances[msg.sender] -= amount;
        totalDeposits -= amount;
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Withdraw failed");
    }

    function adminWithdraw(uint256 amount) external onlyOwner {
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Admin withdraw failed");
    }

    // destroy removed in safe variant
}
