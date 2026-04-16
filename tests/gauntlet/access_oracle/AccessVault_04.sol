// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title AccessVault_04 - SAFE
 * @dev Proper access control with OpenZeppelin patterns.
 * @notice Case ID: AC-SAFE-001
 *
 * SAFE: Uses OwnableUpgradeable with two-step transfer and proper modifiers
 * on all critical functions.
 */

import "@openzeppelin/contracts-upgradeable/access/Ownable2StepUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";

contract AccessVault_04 is Initializable, Ownable2StepUpgradeable, UUPSUpgradeable {
    mapping(address => uint256) public balances;
    mapping(address => bool) public allowedTargets;

    function initialize(address _owner) public initializer {
        __Ownable2Step_init();
        _transferOwnership(_owner);
    }

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        balances[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
    }

    // SAFE: Proper access control on upgrade function
    function _authorizeUpgrade(address newImplementation) internal override onlyOwner {
        // Only owner can authorize upgrades (via Ownable2Step)
    }

    // SAFE: Two-step ownership transfer inherited from Ownable2Step
    // transferOwnership() sets pendingOwner
    // acceptOwnership() must be called by new owner to confirm

    // SAFE: Delegatecall only to whitelisted targets
    function setAllowedTarget(address target, bool allowed) external onlyOwner {
        allowedTargets[target] = allowed;
    }

    function execute(address target, bytes calldata data) external onlyOwner returns (bytes memory) {
        require(allowedTargets[target], "Target not whitelisted");
        (bool success, bytes memory result) = target.delegatecall(data);
        require(success, "Delegatecall failed");
        return result;
    }
}
