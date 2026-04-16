// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title IBeacon
 * @notice Interface for beacon contracts.
 */
interface IBeacon {
    function implementation() external view returns (address);
}

/**
 * @title TestBeaconProxy
 * @notice Test contract for Beacon Proxy pattern detection.
 * @dev Uses EIP-1967 beacon slot to store beacon address.
 */
contract TestBeaconProxy {
    // EIP-1967 beacon slot: keccak256('eip1967.proxy.beacon') - 1
    bytes32 internal constant BEACON_SLOT =
        0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50;

    event BeaconUpgraded(address indexed beacon);

    /**
     * @dev Sets the beacon address.
     */
    constructor(address _beacon) {
        require(_beacon != address(0), "Zero beacon");
        assembly {
            sstore(BEACON_SLOT, _beacon)
        }
        emit BeaconUpgraded(_beacon);
    }

    /**
     * @dev Returns the current beacon address.
     */
    function beacon() public view returns (address b) {
        assembly {
            b := sload(BEACON_SLOT)
        }
    }

    /**
     * @dev Returns the current implementation from the beacon.
     */
    function implementation() public view returns (address) {
        return IBeacon(beacon()).implementation();
    }

    /**
     * @dev Fallback delegates to implementation from beacon.
     */
    fallback() external payable {
        address impl = IBeacon(beacon()).implementation();
        require(impl != address(0), "Implementation not set");

        assembly {
            calldatacopy(0, 0, calldatasize())
            let result := delegatecall(gas(), impl, 0, calldatasize(), 0, 0)
            returndatacopy(0, 0, returndatasize())
            switch result
            case 0 { revert(0, returndatasize()) }
            default { return(0, returndatasize()) }
        }
    }

    receive() external payable {}
}

/**
 * @title TestUpgradeableBeacon
 * @notice Test beacon contract that manages implementation address.
 */
contract TestUpgradeableBeacon is IBeacon {
    address private _implementation;
    address public owner;

    event Upgraded(address indexed implementation);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    constructor(address implementation_) {
        require(implementation_ != address(0), "Zero implementation");
        _implementation = implementation_;
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    /**
     * @dev Returns the current implementation address.
     */
    function implementation() public view override returns (address) {
        return _implementation;
    }

    /**
     * @dev Upgrades the implementation (owner only).
     */
    function upgradeTo(address newImplementation) external onlyOwner {
        require(newImplementation != address(0), "Zero implementation");
        _implementation = newImplementation;
        emit Upgraded(newImplementation);
    }

    /**
     * @dev Transfers ownership (owner only).
     */
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "Zero owner");
        address oldOwner = owner;
        owner = newOwner;
        emit OwnershipTransferred(oldOwner, newOwner);
    }
}

/**
 * @title TestBeaconImplementation
 * @notice Implementation contract for beacon proxy testing.
 */
contract TestBeaconImplementation {
    uint256 public counter;
    address public lastCaller;

    event CounterIncremented(uint256 newValue, address caller);

    function increment() external {
        counter++;
        lastCaller = msg.sender;
        emit CounterIncremented(counter, msg.sender);
    }

    function getCounter() external view returns (uint256) {
        return counter;
    }

    function reset() external {
        counter = 0;
        lastCaller = msg.sender;
    }
}
