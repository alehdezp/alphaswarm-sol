// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../libraries/ComputeEngine.sol";
import "../periphery/PolicyOracle_safe.sol";

/// @title AdaptivePoolManager (SAFE VARIANT)
contract AdaptivePoolManager_safe {
    using ComputeEngine for uint256;

    struct AssetTranche { uint256 principal; uint256 accrued; uint256 weight; address beneficiary; }

    mapping(bytes32 => AssetTranche) private _tranches;
    mapping(address => bytes32[]) private _userTranches;
    mapping(address => bool) public authorizedAgents;
    PolicyOracle_safe public policyEngine;
    address public coordinator;
    uint256 public globalExposure;
    uint256 public systemNonce;
    bool private _locked;
    uint256 public constant MAX_BATCH = 50;
    uint256 public constant ORACLE_FRESHNESS = 3600;

    modifier nonReentrant() { require(!_locked); _locked = true; _; _locked = false; }
    modifier onlyCoordinator() { require(msg.sender == coordinator, "Not coordinator"); _; }

    event TrancheCreated(bytes32 indexed id, address beneficiary, uint256 principal);
    event TrancheSettled(bytes32 indexed id, uint256 payout);

    constructor(address _policy) { coordinator = msg.sender; policyEngine = PolicyOracle_safe(_policy); }

    function originateTranche(uint256 weight) external payable {
        require(msg.value > 0); bytes32 id = keccak256(abi.encodePacked(msg.sender, systemNonce++, block.timestamp));
        _tranches[id] = AssetTranche(msg.value, 0, weight, msg.sender); _userTranches[msg.sender].push(id);
        globalExposure += msg.value; emit TrancheCreated(id, msg.sender, msg.value);
    }

    function concludeTranche(bytes32 trancheId) external nonReentrant {
        AssetTranche storage t = _tranches[trancheId];
        require(t.beneficiary == msg.sender && t.principal > 0);
        uint256 payout = t.principal + t.accrued;
        uint256 base = t.principal;
        t.principal = 0; t.accrued = 0; globalExposure -= base;
        (bool ok, ) = t.beneficiary.call{value: payout}("");
        require(ok);
        emit TrancheSettled(trancheId, payout);
    }

    function applyPolicyAccrual(bytes32 trancheId) external {
        AssetTranche storage t = _tranches[trancheId];
        require(t.principal > 0);
        (uint256 r, uint256 ts) = policyEngine.currentRate();
        require(block.timestamp - ts < ORACLE_FRESHNESS, "Stale rate");
        t.accrued += t.principal.computeGrowth(r);
    }

    function batchSettle(bytes32[] calldata ids) external nonReentrant {
        require(ids.length <= MAX_BATCH, "Batch too large");
        for (uint256 i = 0; i < ids.length; i++) {
            AssetTranche storage t = _tranches[ids[i]];
            if (t.beneficiary == msg.sender && t.principal > 0) {
                uint256 p = t.principal + t.accrued; t.principal = 0; t.accrued = 0;
                (bool ok, ) = msg.sender.call{value: p}(""); require(ok);
            }
        }
    }

    function certifyAgent(address agent) external onlyCoordinator { authorizedAgents[agent] = true; }
    function reconfigurePolicy(address np) external onlyCoordinator { policyEngine = PolicyOracle_safe(np); }
    function delegateCoordination(address nc) external onlyCoordinator { coordinator = nc; }
    function emergencyRecovery(address payable r) external onlyCoordinator { r.transfer(address(this).balance); }

    receive() external payable {}
}
