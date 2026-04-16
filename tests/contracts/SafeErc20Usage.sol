// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20Safe {
    function transfer(address to, uint256 amount) external returns (bool);
}

library SafeERC20 {
    function safeTransfer(IERC20Safe token, address to, uint256 amount) internal {
        require(token.transfer(to, amount), "transfer failed");
    }
}

contract SafeErc20Usage {
    using SafeERC20 for IERC20Safe;
    IERC20Safe public token;

    constructor(IERC20Safe token_) {
        token = token_;
    }

    function pay(address to, uint256 amount) external {
        token.safeTransfer(to, amount);
    }
}
