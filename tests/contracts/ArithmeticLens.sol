// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract ArithmeticLens {
    mapping(address => uint256) public balances;
    uint256 public totalShares;
    uint256 public totalSupply;

    function uncheckedAdd(uint256 amount) external {
        unchecked {
            uint256 next = balances[msg.sender] + amount;
            balances[msg.sender] = next;
        }
    }

    function divisionBeforeMul(uint256 amount, uint256 price) external pure returns (uint256) {
        return amount / 10 * price;
    }

    function truncationInFees(uint256 amount, uint256 feeBps) external pure returns (uint256) {
        uint256 fee = amount / 10000 * feeBps;
        return fee;
    }

    function roundingExploit(uint256 amount) external pure returns (uint256) {
        uint256 shares = amount / 3;
        return shares;
    }

    function narrowingCast(uint256 amount) external pure returns (uint128) {
        return uint128(amount);
    }

    function signedToUnsigned(int256 amount) external pure returns (uint256) {
        return uint256(amount);
    }

    function addressToUint(address user) external pure returns (uint256) {
        return uint256(uint160(user));
    }

    function divideBy(uint256 amount, uint256 divisor) external pure returns (uint256) {
        return amount / divisor;
    }

    function lossCalc(uint256 amount, uint256 rate) external pure returns (uint256) {
        return amount / rate;
    }

    function largeMul(uint256 amount) external pure returns (uint256) {
        return amount * 1e36;
    }

    function loopSmallCounter(uint8 limit) external {
        for (uint8 i = 0; i < limit; i++) {
            balances[msg.sender] += i;
        }
    }

    function priceAmount(uint256 amount, uint256 price) external pure returns (uint256) {
        return amount * price;
    }

    function percentageCalc(uint256 amount, uint256 pct) external pure returns (uint256) {
        return amount * pct / 100;
    }

    function basisPoints(uint256 amount, uint256 bps) external pure returns (uint256) {
        return amount * bps / 10000;
    }

    function deposit(uint256 amount) external {
        uint256 shares = amount * totalShares / totalSupply;
        totalShares += shares;
        balances[msg.sender] += amount;
    }

    function ratioCalc(uint256 a, uint256 b) external pure returns (uint256) {
        uint256 ratio = a / b;
        return ratio;
    }

    function feeCalc(uint256 amount, uint256 fee) external pure returns (uint256) {
        uint256 chargedFee = amount * fee / 10000;
        return chargedFee;
    }

    function accumulateFees(uint256[] calldata fees) external pure returns (uint256) {
        uint256 totalFee = 0;
        for (uint256 i = 0; i < fees.length; i++) {
            totalFee += fees[i];
        }
        return totalFee;
    }

    function timeMath(uint256 duration) external view returns (uint256) {
        return block.timestamp + duration;
    }

    function durationCalc(uint256 duration) external view returns (uint256) {
        uint256 unlock = block.timestamp + duration;
        return unlock;
    }

    function decimalMismatch(uint256 amount, uint8 decimals) external pure returns (uint256) {
        return amount * (10 ** decimals);
    }

    function decimalIssue(uint256 amount, uint8 decimals) external pure returns (uint256) {
        return amount * 1e18 * decimals;
    }
}
