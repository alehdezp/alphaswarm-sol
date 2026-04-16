// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IVaultCore {
    function deposit(uint256 amount) external payable;
    function redeem(uint256 shares) external;
    function getSharePrice() external view returns (uint256);
    function totalAssets() external view returns (uint256);
    event Deposited(address indexed user, uint256 amount, uint256 shares);
    event Redeemed(address indexed user, uint256 shares, uint256 amount);
}
