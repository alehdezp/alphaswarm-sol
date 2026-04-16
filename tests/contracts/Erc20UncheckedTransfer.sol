// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20Unchecked {
    function transfer(address to, uint256 amount) external returns (bool);
}

contract Erc20UncheckedTransfer {
    IERC20Unchecked public token;

    constructor(IERC20Unchecked token_) {
        token = token_;
    }

    function pay(address to, uint256 amount) external {
        token.transfer(to, amount);
    }
}
