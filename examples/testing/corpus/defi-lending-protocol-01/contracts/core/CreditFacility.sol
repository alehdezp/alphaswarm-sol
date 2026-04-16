// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../interfaces/IAssetOracle.sol";
import "../libraries/PositionMath.sol";

/// @title CreditFacility - Core lending and borrowing engine
/// @notice Manages collateral deposits, credit issuance, and position health
contract CreditFacility {
    using PositionMath for uint256;

    struct CreditPosition {
        uint256 collateral;
        uint256 liability;
        uint256 lastAccrual;
    }

    mapping(address => CreditPosition) private _positions;
    IAssetOracle public oracle;
    address public riskManager;
    uint256 public totalCollateral;
    uint256 public totalLiabilities;
    uint256 public accrualRate; // basis points per day
    uint256 public constant HEALTH_THRESHOLD = 15000; // 150%
    bool private _systemActive;

    event PositionOpened(address indexed account, uint256 collateral);
    event CreditIssued(address indexed account, uint256 amount);
    event PositionSettled(address indexed account, uint256 returned);

    constructor(address _oracle, uint256 _rate) {
        oracle = IAssetOracle(_oracle);
        riskManager = msg.sender;
        accrualRate = _rate;
        _systemActive = true;
    }

    modifier whenActive() {
        require(_systemActive, "System paused");
        _;
    }

    /// @notice Open a collateral position
    function openPosition() external payable whenActive {
        require(msg.value > 0, "No collateral");
        _positions[msg.sender].collateral += msg.value;
        totalCollateral += msg.value;
        emit PositionOpened(msg.sender, msg.value);
    }

    /// @notice Issue credit against collateral
    /// @dev VULNERABILITY: Oracle price not checked for staleness (oracle-stale-price)
    function issueCreditLine(uint256 amount) external whenActive {
        CreditPosition storage pos = _positions[msg.sender];
        _accrueInterest(pos);

        (uint256 price, ) = oracle.getLatestValue();
        uint256 collateralValue = (pos.collateral * price) / 1e18;
        uint256 newLiability = pos.liability + amount;

        require(
            (collateralValue * 10000) / newLiability >= HEALTH_THRESHOLD,
            "Undercollateralized"
        );

        pos.liability = newLiability;
        totalLiabilities += amount;

        // VULNERABILITY: External call before state finalization (reentrancy)
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Transfer failed");

        emit CreditIssued(msg.sender, amount);
    }

    /// @notice Settle credit and recover collateral
    /// @dev VULNERABILITY: Reentrancy - external call before state update
    function settlePosition() external {
        CreditPosition storage pos = _positions[msg.sender];
        _accrueInterest(pos);
        require(pos.collateral > 0, "No position");

        uint256 returnAmount = pos.collateral;
        require(pos.liability == 0, "Outstanding liability");

        // External call before state zeroing
        (bool ok, ) = msg.sender.call{value: returnAmount}("");
        require(ok, "Settlement failed");

        pos.collateral = 0;
        totalCollateral -= returnAmount;

        emit PositionSettled(msg.sender, returnAmount);
    }

    /// @notice Force-close an unhealthy position
    /// @dev VULNERABILITY: Missing access control - anyone can liquidate
    function forceClosePosition(address account) external {
        CreditPosition storage pos = _positions[account];
        _accrueInterest(pos);

        (uint256 price, ) = oracle.getLatestValue();
        uint256 collateralValue = (pos.collateral * price) / 1e18;

        // No access control check
        require(
            (collateralValue * 10000) / pos.liability < HEALTH_THRESHOLD,
            "Position healthy"
        );

        uint256 seized = pos.collateral;
        pos.collateral = 0;
        totalLiabilities -= pos.liability;
        pos.liability = 0;
        totalCollateral -= seized;

        // Liquidator receives seized collateral
        (bool ok, ) = msg.sender.call{value: seized}("");
        require(ok, "Seizure failed");
    }

    /// @notice Update system configuration
    /// @dev VULNERABILITY: Missing access control on critical params
    function recalibrateSystem(uint256 newRate, address newOracle) external {
        accrualRate = newRate;
        oracle = IAssetOracle(newOracle);
    }

    /// @notice Toggle system state
    function toggleSystemState() external {
        require(msg.sender == riskManager, "Not authorized");
        _systemActive = !_systemActive;
    }

    /// @dev Accrue interest on position
    function _accrueInterest(CreditPosition storage pos) internal {
        if (pos.liability > 0 && pos.lastAccrual > 0) {
            uint256 elapsed = block.timestamp - pos.lastAccrual;
            uint256 interest = pos.liability.computeAccrual(accrualRate, elapsed);
            pos.liability += interest;
            totalLiabilities += interest;
        }
        pos.lastAccrual = block.timestamp;
    }

    /// @notice View position health factor
    function positionHealth(address account) external view returns (uint256) {
        CreditPosition memory pos = _positions[account];
        if (pos.liability == 0) return type(uint256).max;
        (uint256 price, ) = oracle.getLatestValue();
        uint256 collateralValue = (pos.collateral * price) / 1e18;
        return (collateralValue * 10000) / pos.liability;
    }

    receive() external payable {}
}
