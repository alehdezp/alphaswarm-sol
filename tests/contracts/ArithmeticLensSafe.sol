// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract ArithmeticLensSafe {
    mapping(address => uint256) public balances;
    uint256 public totalShares;
    uint256 public totalSupply;

    function checkedAdd(uint256 amount) external {
        require(amount <= type(uint256).max - balances[msg.sender], "overflow");
        balances[msg.sender] += amount;
    }

    function mulBeforeDiv(uint256 amount, uint256 price) external pure returns (uint256) {
        return amount * price / 10;
    }

    function feeWithPrecision(uint256 amount, uint256 feeBps) external pure returns (uint256) {
        uint256 precisionFactor = 1e18;
        uint256 fee = (amount * feeBps * precisionFactor) / 10000;
        return fee;
    }

    function roundingSafe(uint256 amount) external pure returns (uint256) {
        uint256 precisionFactor = 1e18;
        return amount * precisionFactor / 3;
    }

    function narrowingCastSafe(uint256 amount) external pure returns (uint128) {
        require(amount <= type(uint128).max, "bounds");
        return uint128(amount);
    }

    function signedToUnsignedSafe(int256 amount) external pure returns (uint256) {
        require(amount >= 0, "negative");
        return uint256(amount);
    }

    function divideBySafe(uint256 amount, uint256 divisor) external pure returns (uint256) {
        require(divisor != 0, "zero");
        return amount / divisor;
    }

    function precisionLossSafe(uint256 amount, uint256 rate) external pure returns (uint256) {
        uint256 precisionFactor = 1e18;
        return amount * precisionFactor / rate;
    }

    function largeMulSafe(uint256 amount) external pure returns (uint256) {
        return mulDiv(amount, 1e18, 1e18);
    }

    function loopLargeCounter(uint256 limit) external {
        for (uint256 i = 0; i < limit; i++) {
            balances[msg.sender] += i;
        }
    }

    function priceAmountSafe(uint256 amount, uint256 price) external pure returns (uint256) {
        return mulDiv(amount, price, 1);
    }

    function percentageCalcSafe(uint256 amount, uint256 pct) external pure returns (uint256) {
        require(pct <= 100, "pct");
        return amount * pct / 100;
    }

    function basisPointsSafe(uint256 amount, uint256 bps) external pure returns (uint256) {
        uint256 precisionFactor = 1e4;
        return amount * bps / precisionFactor;
    }

    function depositSafe(uint256 amount) external {
        require(totalSupply > 0, "supply");
        uint256 precisionFactor = 1e18;
        uint256 shares = amount * totalShares * precisionFactor / totalSupply;
        totalShares += shares;
        balances[msg.sender] += amount;
    }

    function ratioSafe(uint256 a, uint256 b) external pure returns (uint256) {
        uint256 precisionFactor = 1e18;
        return a * precisionFactor / b;
    }

    function feePrecisionSafe(uint256 amount, uint256 fee) external pure returns (uint256) {
        uint256 precisionFactor = 1e18;
        return amount * fee * precisionFactor / 10000;
    }

    function accumulateSafely(uint256[] calldata fees) external pure returns (uint256) {
        uint256 sum = 0;
        for (uint256 i = 0; i < fees.length; i++) {
            sum = sum + fees[i];
        }
        return sum;
    }

    function timeCheck(uint256 start) external view returns (bool) {
        return block.timestamp >= start;
    }

    function durationCalcSafe(uint256 duration) external view returns (uint256) {
        require(duration <= 30 days, "bounds");
        return block.timestamp + duration;
    }

    function decimalMismatchSafe(uint256 amount, uint8 decimals) external pure returns (uint256) {
        uint256 precisionFactor = 10 ** decimals;
        return amount * precisionFactor;
    }

    function decimalScalingSafe(uint256 amount, uint8 decimals) external pure returns (uint256) {
        uint256 precisionFactor = 10 ** decimals;
        return mulDiv(amount, precisionFactor, 1);
    }

    function mulDiv(uint256 a, uint256 b, uint256 c) internal pure returns (uint256) {
        return (a * b) / c;
    }
}
