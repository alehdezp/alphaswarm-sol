// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20Checked {
    function transfer(address to, uint256 amount) external returns (bool);
}

contract Erc20CheckedTransfer {
    IERC20Checked public token;

    constructor(IERC20Checked token_) {
        token = token_;
    }

    function pay(address to, uint256 amount) external {
        require(token.transfer(to, amount), "transfer failed");
    }
}
