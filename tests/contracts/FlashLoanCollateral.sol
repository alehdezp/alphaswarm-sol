// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface IERC20Collateral {
    function balanceOf(address account) external view returns (uint256);
}

contract FlashLoanCollateral {
    IERC20Collateral public token;

    constructor(IERC20Collateral token_) {
        token = token_;
    }

    function collateralValue(address account) external view returns (uint256) {
        uint256 balance = token.balanceOf(account);
        return balance * 2;
    }

    function collateralValueSnapshot(address account, uint256 snapshotId) external view returns (uint256) {
        require(snapshotId > 0, "snapshot");
        uint256 balance = token.balanceOf(account);
        return balance * 2;
    }
}
