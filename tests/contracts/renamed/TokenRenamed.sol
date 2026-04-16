// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title TokenRenamed
 * @notice Token contract with non-standard naming conventions.
 *         Tests detection of token vulnerabilities without relying on standard ERC20 names.
 *
 * Renamed: balanceOf -> holdings, transfer -> moveTo, approve -> authorize, allowance -> spendLimit
 */
contract TokenRenamed {
    mapping(address => uint256) public holdings;  // Renamed from "balanceOf"
    mapping(address => mapping(address => uint256)) public spendLimit;  // Renamed from "allowance"
    uint256 public circulation;  // Renamed from "totalSupply"

    // Renamed from "mint" - VULNERABLE: no access control
    function createUnits(address recipient, uint256 qty) external {
        holdings[recipient] += qty;
        circulation += qty;
    }

    // Renamed from "burn" - VULNERABLE: no access control
    function destroyUnits(address from, uint256 qty) external {
        holdings[from] -= qty;
        circulation -= qty;
    }

    // Renamed from "transfer" - token transfer
    function moveTo(address recipient, uint256 qty) external returns (bool) {
        require(holdings[msg.sender] >= qty, "insufficient");
        holdings[msg.sender] -= qty;
        holdings[recipient] += qty;
        return true;
    }

    // Renamed from "approve" - VULNERABLE: approval race condition possible
    function authorize(address spender, uint256 qty) external returns (bool) {
        spendLimit[msg.sender][spender] = qty;
        return true;
    }

    // Renamed from "transferFrom"
    function moveFrom(address from, address to, uint256 qty) external returns (bool) {
        require(holdings[from] >= qty, "insufficient");
        require(spendLimit[from][msg.sender] >= qty, "not authorized");
        holdings[from] -= qty;
        holdings[to] += qty;
        spendLimit[from][msg.sender] -= qty;
        return true;
    }
}
