// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface ICallbackTarget {
    function ping() external;
}

contract ValueMovementCallbacks {
    address public callbackTarget;
    uint256 public counter;

    modifier nonReentrant() {
        _;
    }

    constructor(address target) {
        callbackTarget = target;
    }

    function onSwapCallback(address sender, uint256 amount0, uint256 amount1, bytes calldata data) external {
        ICallbackTarget(callbackTarget).ping();
        counter += amount0 + amount1;
        if (sender == address(0) || data.length == 0) {
            counter += 1;
        }
    }

    function hookNotify(uint256 value) external {
        counter += value;
    }

    function onFlashLoan(bytes calldata data) external nonReentrant {
        counter += data.length;
    }
}
