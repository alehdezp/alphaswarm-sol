// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IPriceOracle {
    function latestAnswer() external view returns (int256);
}

contract ValueMovementFlashLoan {
    IPriceOracle public oracle;

    constructor(IPriceOracle _oracle) {
        oracle = _oracle;
    }

    function executeOperation(
        address asset,
        uint256 amount,
        uint256 premium,
        address initiator,
        bytes calldata params
    ) external returns (bool) {
        asset;
        amount;
        premium;
        initiator;
        params;
        return true;
    }

    function safeExecuteOperation(
        address asset,
        uint256 amount,
        uint256 premium,
        address initiator,
        bytes calldata params
    ) external returns (bool) {
        require(asset != address(0), "bad asset");
        params;
        require(initiator == address(this), "bad initiator");
        require(amount + premium >= amount, "bad repay");
        return true;
    }

    modifier flashGuard() {
        _;
    }

    function sensitivePrice() external view returns (int256) {
        return oracle.latestAnswer();
    }

    function guardedSensitivePrice() external view flashGuard returns (int256) {
        return oracle.latestAnswer();
    }
}
