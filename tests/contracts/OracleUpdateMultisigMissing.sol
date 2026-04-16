// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

contract OracleUpdateMultisigMissing {
    uint256 public price;
    address[] public signers;

    constructor(address[] memory signers_) {
        signers = signers_;
    }

    function setPrice(uint256 newPrice) external {
        price = newPrice;
    }
}
