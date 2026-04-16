// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Weak authentication based on gasleft.
contract WeakAuthGasleft {
    function privileged(uint256 minGas) external view returns (bool) {
        require(gasleft() > minGas, "low gas");
        return true;
    }
}
