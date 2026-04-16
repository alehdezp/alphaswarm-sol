// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ValueMovementRenamed
 * @notice Value movement vulnerabilities with non-standard naming.
 *         Tests detection without relying on names like "transfer", "withdraw", "deposit".
 *
 * Renamed: transfer -> moveFunds, withdraw -> extractValue, deposit -> insertValue
 */
contract ValueMovementRenamed {
    mapping(address => uint256) public ledger;  // Renamed from "balances"
    address public vault;  // Renamed from "treasury"

    constructor(address _vault) {
        vault = _vault;
    }

    // Renamed from "deposit" - receives ETH
    function insertValue() external payable {
        ledger[msg.sender] += msg.value;
    }

    // Renamed from "withdraw" - VULNERABLE: no access control on value extraction
    function extractValue(uint256 qty) external {
        require(ledger[msg.sender] >= qty, "insufficient");
        ledger[msg.sender] -= qty;
        (bool ok, ) = msg.sender.call{value: qty}("");
        require(ok, "failed");
    }

    // Renamed from "transfer" - VULNERABLE: no auth on ETH movement
    function moveFunds(address recipient, uint256 qty) external {
        require(ledger[msg.sender] >= qty, "insufficient");
        ledger[msg.sender] -= qty;
        ledger[recipient] += qty;
    }

    // VULNERABLE: Sends contract ETH without proper auth
    function evacuateVault() external {
        (bool ok, ) = vault.call{value: address(this).balance}("");
        require(ok, "failed");
    }
}
