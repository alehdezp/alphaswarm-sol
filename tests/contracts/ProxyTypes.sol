// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

contract UUPSLogic {
    address public impl;
    uint256[50] private __gap;

    function upgradeTo(address newImpl) external {
        impl = newImpl;
    }
}

contract TransparentProxy {
    address private _admin;

    function implementation() external pure returns (address) {
        return address(0);
    }

    function admin() external view returns (address) {
        return _admin;
    }

    function upgradeTo(address newImpl) external {
        _admin = newImpl;
    }
}

contract BeaconProxy {
    address private _beacon;

    function beacon() external view returns (address) {
        return _beacon;
    }

    function upgradeBeaconTo(address newBeacon) external {
        _beacon = newBeacon;
    }
}

contract GenericProxy {
    function upgradeToAndCall(address, bytes calldata) external {}
}

contract PlainProxy {}

contract PlainLogic {
    uint256 public value;

    function setValue(uint256 nextValue) external {
        value = nextValue;
    }
}

contract UpgradeNoGuard {
    address public impl;

    function upgradeTo(address newImpl) external {
        impl = newImpl;
    }
}

contract UpgradeWithGuard {
    address public impl;
    address public owner;

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    function upgradeTo(address newImpl) external onlyOwner {
        impl = newImpl;
    }
}

contract UUPSGuardedNoOnlyProxy {
    address public impl;
    address public owner;

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    function upgradeTo(address newImpl) external onlyOwner {
        impl = newImpl;
    }
}
