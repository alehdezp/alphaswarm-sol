// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../periphery/DataRegistry_safe.sol";
import "../libraries/CipherLib.sol";

/// @title NexusController (SAFE VARIANT)
contract NexusController_safe {
    using CipherLib for bytes;

    enum ModuleState { Dormant, Active, Frozen, Decommissioned }
    struct Module { address endpoint; ModuleState state; uint256 throughput; uint256 lastPing; }

    mapping(bytes32 => Module) public modules;
    mapping(address => uint256) private _stakes;
    mapping(address => uint256) private _credits;
    DataRegistry_safe public registry;
    address public nexusOwner;
    uint256 public moduleCount;
    uint256 public stakingThreshold;
    uint256 public constant COLLATERAL_RATIO = 150; // 150%
    uint256 public constant DATA_FRESHNESS = 3600;
    bool private _locked;

    modifier nonReentrant() { require(!_locked); _locked = true; _; _locked = false; }
    modifier onlyOwner() { require(msg.sender == nexusOwner, "Not owner"); _; }

    constructor(address _registry, uint256 _threshold) {
        registry = DataRegistry_safe(_registry); nexusOwner = msg.sender; stakingThreshold = _threshold;
    }

    function enrollModule(address endpoint) external onlyOwner returns (bytes32) {
        bytes32 id = keccak256(abi.encodePacked(endpoint, moduleCount++));
        modules[id] = Module(endpoint, ModuleState.Active, 0, block.timestamp);
        return id;
    }

    function commitStake() external payable { require(msg.value >= stakingThreshold); _stakes[msg.sender] += msg.value; }

    function issueCredit(uint256 amount) external nonReentrant {
        require(_stakes[msg.sender] * 100 >= (_credits[msg.sender] + amount) * COLLATERAL_RATIO, "Undercollateralized"); // FIXED
        _credits[msg.sender] += amount;
        (bool ok, ) = msg.sender.call{value: amount}(""); require(ok);
    }

    function releaseStake(uint256 amount) external nonReentrant { // FIXED: no callback
        require(_stakes[msg.sender] >= amount && _credits[msg.sender] == 0);
        _stakes[msg.sender] -= amount;
        (bool ok, ) = msg.sender.call{value: amount}(""); require(ok);
    }

    function dispatchOperation(bytes32 moduleId, bytes calldata opData) external onlyOwner { // FIXED
        Module storage m = modules[moduleId]; require(m.state == ModuleState.Active);
        (bool ok, ) = m.endpoint.call(opData); require(ok);
        m.throughput++; m.lastPing = block.timestamp;
    }

    function freezeModule(bytes32 moduleId) external onlyOwner {
        Module storage m = modules[moduleId];
        require(m.state != ModuleState.Decommissioned, "Already decommissioned"); // FIXED
        m.state = ModuleState.Frozen;
    }

    function replaceRegistry(address nr) external onlyOwner { registry = DataRegistry_safe(nr); } // FIXED
    function transferNexus(address no) external onlyOwner { nexusOwner = no; } // FIXED
    function setThreshold(uint256 nt) external onlyOwner { stakingThreshold = nt; } // FIXED

    receive() external payable {}
}
