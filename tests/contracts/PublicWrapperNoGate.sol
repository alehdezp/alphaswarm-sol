// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Public wrapper calls internal state mutation without access control.
contract PublicWrapperNoGate {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    function _setOwner(address newOwner) internal {
        owner = newOwner;
    }

    function setOwner(address newOwner) external {
        _setOwner(newOwner);
    }

    function setOwnerProtected(address newOwner) external onlyOwner {
        _setOwner(newOwner);
    }
}
