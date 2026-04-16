// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

library LibDiamond {
    struct DiamondStorage {
        uint256 value;
    }

    function diamondStorage() internal pure returns (DiamondStorage storage ds) {
        assembly {
            ds.slot := 0
        }
    }
}

// VULNERABLE: diamond-style contract without storage isolation helper.
contract DiamondVulnerable {
    uint256 public value;

    function diamondCut(bytes calldata) external {}

    function setValue(uint256 nextValue) external {
        value = nextValue;
    }
}

// SAFE: diamond-style contract using LibDiamond storage namespace.
contract DiamondSafe {
    function diamondCut(bytes calldata) external {}

    function setValue(uint256 nextValue) external {
        LibDiamond.DiamondStorage storage ds = LibDiamond.diamondStorage();
        ds.value = nextValue;
    }
}
