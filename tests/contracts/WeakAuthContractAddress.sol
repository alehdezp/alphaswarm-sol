// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Weak authentication using contract address.
contract WeakAuthContractAddress {
    function privileged() external view returns (bool) {
        require(msg.sender == address(this), "not contract");
        return true;
    }
}
