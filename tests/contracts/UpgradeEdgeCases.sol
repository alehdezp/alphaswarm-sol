// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

contract TransparentInitGuarded {
    address public admin;
    bool public initialized;

    modifier onlyAdmin() {
        require(msg.sender == admin, "not admin");
        _;
    }

    function initialize(address _admin) external onlyAdmin {
        require(!initialized, "already initialized");
        admin = _admin;
        initialized = true;
    }

    function upgradeTo(address newImpl) external onlyAdmin {
        admin = newImpl;
    }
}

contract BeaconInitGuarded {
    address public beacon;
    bool public initialized;

    modifier onlyGuardian() {
        require(msg.sender == beacon, "not guardian");
        _;
    }

    function initialize(address _beacon) external onlyGuardian {
        require(!initialized, "already initialized");
        beacon = _beacon;
        initialized = true;
    }

    function upgradeBeaconTo(address newBeacon) external onlyGuardian {
        beacon = newBeacon;
    }
}

contract MixedUpgradeModifiers {
    address public impl;
    address public owner;

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    function upgradeTo(address newImpl) external {
        impl = newImpl;
    }

    function upgradeToAndCall(address newImpl, bytes calldata) external onlyOwner {
        impl = newImpl;
    }
}

contract StorageGapEdgeCases {
    uint256[10] private __gap;
    bytes32[5] private __gapExtra;
    uint128[3] private __gapSmall;

    function upgradeTo(address) external {}
}
