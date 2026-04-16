// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IFungibleAsset {
    function moveTo(address recipient, uint256 qty) external returns (bool);
    function moveFrom(address from, address to, uint256 qty) external returns (bool);
    function holdings(address account) external view returns (uint256);
}

/**
 * @title FeeOnTransferRenamed
 * @notice Fee-on-transfer token handling with non-standard naming.
 *         Tests detection of accounting issues without "balance", "transfer", "fee" names.
 *
 * Renamed: balanceOf -> holdings, transfer -> moveTo, deposit -> insertAsset
 */
contract FeeOnTransferRenamed {
    IFungibleAsset public asset;
    mapping(address => uint256) public credited;  // Renamed from "balances"

    constructor(address _asset) {
        asset = IFungibleAsset(_asset);
    }

    // VULNERABLE: Assumes transfer amount equals received amount (fails for fee-on-transfer)
    function insertAsset(uint256 qty) external {
        asset.moveFrom(msg.sender, address(this), qty);
        credited[msg.sender] += qty;  // Should measure actual received amount
    }

    // SAFE: Measures actual received amount
    function insertAssetSafe(uint256 qty) external {
        uint256 before = asset.holdings(address(this));
        asset.moveFrom(msg.sender, address(this), qty);
        uint256 after_ = asset.holdings(address(this));
        uint256 received = after_ - before;
        credited[msg.sender] += received;
    }

    // VULNERABLE: Unchecked return value
    function extractAsset(uint256 qty) external {
        require(credited[msg.sender] >= qty, "insufficient");
        credited[msg.sender] -= qty;
        asset.moveTo(msg.sender, qty);  // Return value not checked
    }
}
