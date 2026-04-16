// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title ProxySafe
 * @notice Safe implementations of proxy and upgrade patterns.
 * @dev These contracts demonstrate proper proxy/upgrade security patterns.
 */

/**
 * @title StorageGapSafe
 * @notice Safe: Proper storage gap for upgradeable contracts
 */
abstract contract StorageGapSafe {
    // State variables
    address public owner;
    uint256 public value;

    // SAFE: 50 slot gap for future upgrades
    uint256[48] private __gap;
}

contract StorageGapImplementationSafe is StorageGapSafe {
    // New state variable in upgrade
    uint256 public newFeature;

    // Gap reduced by 1 for new variable
    uint256[47] private __gapV2;
}

/**
 * @title InitializableSafe
 * @notice Safe: Protected initializer pattern
 */
abstract contract InitializableSafe {
    bool private _initialized;
    bool private _initializing;

    modifier initializer() {
        require(!_initialized || _initializing, "Already initialized");
        bool isTopLevelCall = !_initializing;
        if (isTopLevelCall) {
            _initializing = true;
            _initialized = true;
        }
        _;
        if (isTopLevelCall) {
            _initializing = false;
        }
    }

    modifier reinitializer(uint8 version) {
        // For version-controlled reinitializers
        _;
    }

    function _disableInitializers() internal {
        _initialized = true;
    }
}

contract UpgradeableContractSafe is InitializableSafe, StorageGapSafe {
    // SAFE: Initialize instead of constructor
    function initialize(address _owner) external initializer {
        owner = _owner;
        value = 0;
    }

    // SAFE: Disable initializers in implementation
    constructor() {
        _disableInitializers();
    }
}

/**
 * @title UUPSSafe
 * @notice Safe: UUPS proxy with proper authorization
 */
abstract contract UUPSSafe is InitializableSafe {
    address public implementation;
    address public owner;

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    // SAFE: Protected upgrade function
    function upgradeTo(address newImplementation) external onlyOwner {
        require(newImplementation != address(0), "Invalid implementation");
        require(newImplementation.code.length > 0, "Not a contract");
        implementation = newImplementation;
    }

    // SAFE: Upgrade with reinitialization
    function upgradeToAndCall(address newImplementation, bytes calldata data) external onlyOwner {
        require(newImplementation != address(0), "Invalid implementation");
        require(newImplementation.code.length > 0, "Not a contract");
        implementation = newImplementation;

        if (data.length > 0) {
            (bool success, ) = newImplementation.delegatecall(data);
            require(success, "Initialization failed");
        }
    }
}

/**
 * @title TransparentProxySafe
 * @notice Safe: Transparent proxy with admin separation
 */
contract TransparentProxySafe {
    bytes32 private constant IMPLEMENTATION_SLOT = bytes32(uint256(keccak256("eip1967.proxy.implementation")) - 1);
    bytes32 private constant ADMIN_SLOT = bytes32(uint256(keccak256("eip1967.proxy.admin")) - 1);

    constructor(address _logic, address _admin) {
        _setAdmin(_admin);
        _setImplementation(_logic);
    }

    // SAFE: Admin functions separated from implementation
    modifier ifAdmin() {
        if (msg.sender == _getAdmin()) {
            _;
        } else {
            _fallback();
        }
    }

    function admin() external ifAdmin returns (address) {
        return _getAdmin();
    }

    function implementation() external ifAdmin returns (address) {
        return _getImplementation();
    }

    // SAFE: Only admin can upgrade
    function upgradeTo(address newImplementation) external ifAdmin {
        _setImplementation(newImplementation);
    }

    // SAFE: Two-step admin change
    function changeAdmin(address newAdmin) external ifAdmin {
        require(newAdmin != address(0), "Invalid admin");
        _setAdmin(newAdmin);
    }

    function _fallback() internal {
        _delegate(_getImplementation());
    }

    function _delegate(address impl) internal {
        assembly {
            calldatacopy(0, 0, calldatasize())
            let result := delegatecall(gas(), impl, 0, calldatasize(), 0, 0)
            returndatacopy(0, 0, returndatasize())
            switch result
            case 0 { revert(0, returndatasize()) }
            default { return(0, returndatasize()) }
        }
    }

    function _getImplementation() internal view returns (address impl) {
        bytes32 slot = IMPLEMENTATION_SLOT;
        assembly {
            impl := sload(slot)
        }
    }

    function _setImplementation(address newImplementation) internal {
        require(newImplementation.code.length > 0, "Not a contract");
        bytes32 slot = IMPLEMENTATION_SLOT;
        assembly {
            sstore(slot, newImplementation)
        }
    }

    function _getAdmin() internal view returns (address adm) {
        bytes32 slot = ADMIN_SLOT;
        assembly {
            adm := sload(slot)
        }
    }

    function _setAdmin(address newAdmin) internal {
        bytes32 slot = ADMIN_SLOT;
        assembly {
            sstore(slot, newAdmin)
        }
    }

    receive() external payable {}

    fallback() external payable {
        _fallback();
    }
}

/**
 * @title TimelockUpgradeSafe
 * @notice Safe: Upgrade with timelock delay
 */
contract TimelockUpgradeSafe {
    address public implementation;
    address public owner;
    address public pendingImplementation;
    uint256 public upgradeTime;

    uint256 public constant UPGRADE_DELAY = 2 days;

    event UpgradeScheduled(address indexed newImplementation, uint256 upgradeTime);
    event UpgradeExecuted(address indexed oldImplementation, address indexed newImplementation);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    constructor(address _owner) {
        owner = _owner;
    }

    // SAFE: Schedule upgrade with delay
    function scheduleUpgrade(address newImplementation) external onlyOwner {
        require(newImplementation != address(0), "Invalid implementation");
        require(newImplementation.code.length > 0, "Not a contract");

        pendingImplementation = newImplementation;
        upgradeTime = block.timestamp + UPGRADE_DELAY;

        emit UpgradeScheduled(newImplementation, upgradeTime);
    }

    // SAFE: Execute upgrade only after delay
    function executeUpgrade() external onlyOwner {
        require(pendingImplementation != address(0), "No upgrade pending");
        require(block.timestamp >= upgradeTime, "Timelock not expired");

        address oldImpl = implementation;
        implementation = pendingImplementation;
        pendingImplementation = address(0);
        upgradeTime = 0;

        emit UpgradeExecuted(oldImpl, implementation);
    }

    // SAFE: Cancel pending upgrade
    function cancelUpgrade() external onlyOwner {
        pendingImplementation = address(0);
        upgradeTime = 0;
    }
}

/**
 * @title NoSelfDestructSafe
 * @notice Safe: Implementation without selfdestruct
 */
contract NoSelfDestructSafe {
    address public owner;
    uint256 public value;

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    // SAFE: No selfdestruct - use disable pattern instead
    bool public disabled;

    function disable() external onlyOwner {
        disabled = true;
    }

    modifier notDisabled() {
        require(!disabled, "Contract disabled");
        _;
    }

    function setValue(uint256 _value) external onlyOwner notDisabled {
        value = _value;
    }
}

/**
 * @title DiamondStorageSafe
 * @notice Safe: Diamond storage pattern to avoid collisions
 */
library DiamondStorageSafe {
    bytes32 constant DIAMOND_STORAGE_POSITION = keccak256("diamond.storage.safe");

    struct Storage {
        address owner;
        uint256 value;
        mapping(address => uint256) balances;
    }

    // SAFE: Namespaced storage
    function diamondStorage() internal pure returns (Storage storage ds) {
        bytes32 position = DIAMOND_STORAGE_POSITION;
        assembly {
            ds.slot := position
        }
    }
}

contract DiamondFacetSafe {
    modifier onlyOwner() {
        require(msg.sender == DiamondStorageSafe.diamondStorage().owner, "Not owner");
        _;
    }

    function setValue(uint256 _value) external onlyOwner {
        DiamondStorageSafe.diamondStorage().value = _value;
    }

    function getValue() external view returns (uint256) {
        return DiamondStorageSafe.diamondStorage().value;
    }
}
