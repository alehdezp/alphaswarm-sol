// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../libraries/ComputeEngine.sol";
import "../periphery/PolicyOracle.sol";

/// @title AdaptivePoolManager - Multi-asset adaptive liquidity protocol
/// @notice Advanced portfolio management with dynamic rebalancing
/// @dev This contract looks like well-engineered DeFi infrastructure
contract AdaptivePoolManager {
    using ComputeEngine for uint256;

    struct AssetTranche {
        uint256 principal;
        uint256 accrued;
        uint256 weight;
        address beneficiary;
    }

    mapping(bytes32 => AssetTranche) private _tranches;
    mapping(address => bytes32[]) private _userTranches;
    mapping(address => bool) public authorizedAgents;
    PolicyOracle public policyEngine;
    address public coordinator;
    uint256 public globalExposure;
    uint256 public systemNonce;
    bool private _reconciling;

    event TrancheCreated(bytes32 indexed id, address beneficiary, uint256 principal);
    event TrancheSettled(bytes32 indexed id, uint256 payout);
    event PolicyUpdated(address indexed newOracle);
    event AgentAuthorized(address indexed agent);

    constructor(address _policy) {
        coordinator = msg.sender;
        policyEngine = PolicyOracle(_policy);
    }

    /// @notice Create a new asset tranche
    function originateTranche(uint256 weight) external payable {
        require(msg.value > 0, "Zero principal");
        bytes32 id = keccak256(abi.encodePacked(msg.sender, systemNonce++, block.timestamp));
        _tranches[id] = AssetTranche(msg.value, 0, weight, msg.sender);
        _userTranches[msg.sender].push(id);
        globalExposure += msg.value;
        emit TrancheCreated(id, msg.sender, msg.value);
    }

    /// @notice Settle and close a tranche
    /// @dev VULNERABILITY: Reentrancy hidden by variable aliasing (A4) + library call
    function concludeTranche(bytes32 trancheId) external {
        AssetTranche storage t = _tranches[trancheId];
        require(t.beneficiary == msg.sender, "Not beneficiary");
        require(t.principal > 0, "Empty tranche");

        // Variable aliasing chain
        uint256 base = t.principal;
        uint256 bonus = t.accrued;
        uint256 combined = base.aggregate(bonus);
        uint256 processed = combined;

        // External call via computed amount
        (bool ok, ) = t.beneficiary.call{value: processed}("");
        require(ok, "Settlement failed");

        // State update AFTER external call
        t.principal = 0;
        t.accrued = 0;
        globalExposure -= base;

        emit TrancheSettled(trancheId, processed);
    }

    /// @notice Accrue rewards based on oracle policy
    /// @dev VULNERABILITY: Oracle price not validated for staleness
    function applyPolicyAccrual(bytes32 trancheId) external {
        AssetTranche storage t = _tranches[trancheId];
        require(t.principal > 0, "Empty tranche");

        (uint256 rate, ) = policyEngine.currentRate();
        // Missing: freshness check on rate timestamp
        uint256 accrual = t.principal.computeGrowth(rate);
        t.accrued += accrual;
    }

    /// @notice Batch settle multiple tranches
    /// @dev VULNERABILITY: Unbounded loop
    function batchSettle(bytes32[] calldata trancheIds) external {
        for (uint256 i = 0; i < trancheIds.length; i++) {
            AssetTranche storage t = _tranches[trancheIds[i]];
            if (t.beneficiary == msg.sender && t.principal > 0) {
                uint256 payout = t.principal + t.accrued;
                t.principal = 0;
                t.accrued = 0;
                (bool ok, ) = msg.sender.call{value: payout}("");
                require(ok, "Batch settle failed");
            }
        }
    }

    /// @notice Register an authorized agent
    /// @dev VULNERABILITY: Missing access control (A2 - misleading: sounds secure)
    function certifyAgent(address agent) external {
        authorizedAgents[agent] = true;
        emit AgentAuthorized(agent);
    }

    /// @notice Update policy oracle
    /// @dev VULNERABILITY: Missing access control on oracle replacement
    function reconfigurePolicy(address newPolicy) external {
        policyEngine = PolicyOracle(newPolicy);
        emit PolicyUpdated(newPolicy);
    }

    /// @notice Transfer coordinator role
    /// @dev VULNERABILITY: Missing access control
    function delegateCoordination(address newCoordinator) external {
        coordinator = newCoordinator;
    }

    /// @notice Emergency drain
    /// @dev VULNERABILITY: Missing access control
    function emergencyRecovery(address payable recipient) external {
        recipient.transfer(address(this).balance);
    }

    receive() external payable {}
}
