// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../periphery/DataRegistry.sol";
import "../libraries/CipherLib.sol";

/// @title NexusController - Obfuscated multi-module protocol controller
/// @notice Manages interconnected protocol modules with encoded operations
contract NexusController {
    using CipherLib for bytes;

    enum ModuleState { Dormant, Active, Frozen, Decommissioned }

    struct Module {
        address endpoint;
        ModuleState state;
        uint256 throughput;
        uint256 lastPing;
    }

    mapping(bytes32 => Module) public modules;
    mapping(address => uint256) private _stakes;
    mapping(address => uint256) private _credits;
    DataRegistry public registry;
    address public nexusOwner;
    uint256 public moduleCount;
    uint256 public stakingThreshold;

    event ModuleRegistered(bytes32 indexed id, address endpoint);
    event OperationDispatched(bytes32 indexed moduleId, bytes data);
    event StakeRecorded(address indexed user, uint256 amount);
    event CreditIssued(address indexed user, uint256 amount);

    constructor(address _registry, uint256 _threshold) {
        registry = DataRegistry(_registry);
        nexusOwner = msg.sender;
        stakingThreshold = _threshold;
    }

    /// @notice Register protocol module
    function enrollModule(address endpoint) external returns (bytes32) {
        require(msg.sender == nexusOwner, "Not owner");
        bytes32 id = keccak256(abi.encodePacked(endpoint, moduleCount++));
        modules[id] = Module(endpoint, ModuleState.Active, 0, block.timestamp);
        emit ModuleRegistered(id, endpoint);
        return id;
    }

    /// @notice Stake into nexus
    function commitStake() external payable {
        require(msg.value >= stakingThreshold, "Below threshold");
        _stakes[msg.sender] += msg.value;
        emit StakeRecorded(msg.sender, msg.value);
    }

    /// @notice Issue credit against stake
    /// @dev VULNERABILITY: No collateral check (invariant-balance-unvalidated)
    function issueCredit(uint256 amount) external {
        // Missing: require(_stakes[msg.sender] >= amount * COLLATERAL_RATIO)
        _credits[msg.sender] += amount;
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Credit issuance failed");
        emit CreditIssued(msg.sender, amount);
    }

    /// @notice Release stake
    /// @dev VULNERABILITY: Reentrancy via encoded callback (A6)
    function releaseStake(uint256 amount, bytes calldata callbackData) external {
        require(_stakes[msg.sender] >= amount, "Insufficient stake");
        require(_credits[msg.sender] == 0, "Outstanding credits");

        // Encoded external call hides transfer semantics
        bytes memory payload = callbackData.length > 0
            ? callbackData
            : abi.encodeWithSignature("onStakeReleased(uint256)", amount);

        (bool ok, ) = msg.sender.call{value: amount}(payload);
        require(ok, "Release failed");

        _stakes[msg.sender] -= amount;
    }

    /// @notice Dispatch encoded operation to module
    /// @dev VULNERABILITY: Arbitrary call to module endpoint (arbitrary-calldata)
    function dispatchOperation(bytes32 moduleId, bytes calldata opData) external {
        Module storage m = modules[moduleId];
        require(m.state == ModuleState.Active, "Module inactive");

        // Arbitrary encoded call to module endpoint
        (bool ok, ) = m.endpoint.call(opData);
        require(ok, "Operation failed");

        m.throughput++;
        m.lastPing = block.timestamp;
        emit OperationDispatched(moduleId, opData);
    }

    /// @notice Cross-module data sync
    /// @dev VULNERABILITY: Cross-contract - registry can be manipulated (B1)
    function syncModuleData(bytes32 moduleId) external {
        Module storage m = modules[moduleId];
        require(m.state == ModuleState.Active, "Module inactive");

        (uint256 data, bool valid) = registry.fetchLatest(moduleId);
        // Missing: freshness check on registry data
        require(valid, "Invalid data");
        m.throughput = data;
    }

    /// @notice Freeze module
    /// @dev VULNERABILITY: State machine - can freeze already decommissioned (B3)
    function freezeModule(bytes32 moduleId) external {
        require(msg.sender == nexusOwner, "Not owner");
        Module storage m = modules[moduleId];
        // Missing: require(m.state != ModuleState.Decommissioned)
        m.state = ModuleState.Frozen;
    }

    /// @notice Decommission module
    function decommissionModule(bytes32 moduleId) external {
        require(msg.sender == nexusOwner, "Not owner");
        Module storage m = modules[moduleId];
        require(m.state == ModuleState.Frozen, "Must freeze first");
        m.state = ModuleState.Decommissioned;
    }

    /// @notice Update registry
    /// @dev VULNERABILITY: Missing access control
    function replaceRegistry(address newRegistry) external {
        registry = DataRegistry(newRegistry);
    }

    /// @notice Transfer ownership
    /// @dev VULNERABILITY: Missing access control
    function transferNexus(address newOwner) external {
        nexusOwner = newOwner;
    }

    /// @notice Update threshold
    /// @dev VULNERABILITY: Missing access control
    function setThreshold(uint256 newThreshold) external {
        stakingThreshold = newThreshold;
    }

    receive() external payable {}
}
