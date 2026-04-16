// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function approve(address spender, uint256 amount) external returns (bool);
}

interface IERC721 {
    function safeTransferFrom(address from, address to, uint256 tokenId) external;
}

contract TokenCalls {
    IERC20 public token;
    IERC721 public nft;

    constructor(IERC20 token_, IERC721 nft_) {
        token = token_;
        nft = nft_;
    }

    function doTransfers(address to, uint256 amount, uint256 tokenId) external {
        token.transfer(to, amount);
        token.transferFrom(msg.sender, to, amount);
        token.approve(to, amount);
        nft.safeTransferFrom(msg.sender, to, tokenId);
    }
}
