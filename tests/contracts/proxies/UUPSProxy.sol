// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title UUPSUpgradeable
 * @notice Abstract base contract for UUPS upgradeable implementations.
 * @dev UUPS pattern: upgrade logic lives in the implementation, not the proxy.
 */
abstract contract UUPSUpgradeable {
    // EIP-1967 implementation slot
    bytes32 internal constant IMPLEMENTATION_SLOT =
        0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc;

    // EIP-1822 proxiable storage slot
    bytes32 internal constant PROXIABLE_UUID =
        0xc5f16f0fcc639fa48a6947836d9850f504798523bf8c9a3a87d5876cf622bcf7;

    event Upgraded(address indexed implementation);

    /**
     * @dev Must be implemented by inheriting contract to authorize upgrades.
     */
    function _authorizeUpgrade(address newImplementation) internal virtual;

    /**
     * @dev Returns the proxiable UUID for EIP-1822 compatibility.
     */
    function proxiableUUID() external view virtual returns (bytes32) {
        return IMPLEMENTATION_SLOT;
    }

    /**
     * @dev Upgrades to a new implementation.
     */
    function upgradeTo(address newImplementation) external virtual {
        _authorizeUpgrade(newImplementation);
        _upgradeToAndCallUUPS(newImplementation, new bytes(0), false);
    }

    /**
     * @dev Upgrades to a new implementation and calls a function.
     */
    function upgradeToAndCall(address newImplementation, bytes memory data) external payable virtual {
        _authorizeUpgrade(newImplementation);
        _upgradeToAndCallUUPS(newImplementation, data, true);
    }

    /**
     * @dev Internal upgrade function.
     */
    function _upgradeToAndCallUUPS(
        address newImplementation,
        bytes memory data,
        bool forceCall
    ) internal {
        // Verify the new implementation is UUPS compatible
        try UUPSUpgradeable(newImplementation).proxiableUUID() returns (bytes32 slot) {
            require(slot == IMPLEMENTATION_SLOT, "Invalid implementation");
        } catch {
            revert("Not UUPS compatible");
        }

        assembly {
            sstore(IMPLEMENTATION_SLOT, newImplementation)
        }
        emit Upgraded(newImplementation);

        if (data.length > 0 || forceCall) {
            (bool success,) = newImplementation.delegatecall(data);
            require(success, "Call failed");
        }
    }
}

/**
 * @title TestUUPSImplementation
 * @notice Test UUPS implementation contract.
 */
contract TestUUPSImplementation is UUPSUpgradeable {
    address public owner;
    uint256 public value;
    bool private _initialized;

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    /**
     * @dev Initializer (replaces constructor for proxied contracts).
     */
    function initialize() external {
        require(!_initialized, "Already initialized");
        owner = msg.sender;
        _initialized = true;
    }

    /**
     * @dev Sets a value (owner only).
     */
    function setValue(uint256 _value) external onlyOwner {
        value = _value;
    }

    /**
     * @dev Returns the current value.
     */
    function getValue() external view returns (uint256) {
        return value;
    }

    /**
     * @dev Authorization check for upgrades (owner only).
     */
    function _authorizeUpgrade(address) internal override onlyOwner {}
}

/**
 * @title TestUUPSProxy
 * @notice Minimal UUPS proxy that delegates to implementation.
 */
contract TestUUPSProxy {
    // EIP-1967 implementation slot
    bytes32 internal constant IMPLEMENTATION_SLOT =
        0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc;

    constructor(address _implementation) {
        assembly {
            sstore(IMPLEMENTATION_SLOT, _implementation)
        }
    }

    fallback() external payable {
        address impl;
        assembly {
            impl := sload(IMPLEMENTATION_SLOT)
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
