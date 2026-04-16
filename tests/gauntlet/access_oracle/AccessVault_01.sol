// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title AccessVault_01 - VULNERABLE
 * @dev Missing auth on upgrade - Critical upgrade function lacks access control.
 * @notice Case ID: AC-VULN-001
 *
 * VULNERABILITY: upgradeTo() is public without onlyOwner or onlyRole modifier.
 * Anyone can call upgradeTo() and point the proxy to a malicious implementation.
 */

import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";

contract AccessVault_01 is Initializable, UUPSUpgradeable {
    address public owner;
    mapping(address => uint256) public balances;

    function initialize(address _owner) public initializer {
        owner = _owner;
    }

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        balances[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
    }

    // VULNERABILITY: No access control on critical upgrade function
    // Anyone can call this and replace the implementation
    function _authorizeUpgrade(address newImplementation) internal override {
        // Missing: require(msg.sender == owner, "Not authorized");
        // This allows anyone to upgrade the contract
    }

    function upgradeTo(address newImplementation) public {
        // VULNERABLE: No onlyOwner modifier
        _upgradeToAndCallUUPS(newImplementation, new bytes(0), false);
    }
}
