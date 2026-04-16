// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../interfaces/IAssetOracle.sol";
import "../libraries/PositionMath.sol";

/// @title CreditFacility (SAFE VARIANT)
contract CreditFacility_safe {
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
    uint256 public accrualRate;
    uint256 public constant HEALTH_THRESHOLD = 15000;
    uint256 public constant ORACLE_FRESHNESS = 3600;
    bool private _systemActive;
    bool private _locked;

    modifier nonReentrant() { require(!_locked); _locked = true; _; _locked = false; }
    modifier onlyRiskManager() { require(msg.sender == riskManager, "Not authorized"); _; }
    modifier whenActive() { require(_systemActive, "System paused"); _; }

    event PositionOpened(address indexed account, uint256 collateral);
    event CreditIssued(address indexed account, uint256 amount);
    event PositionSettled(address indexed account, uint256 returned);

    constructor(address _oracle, uint256 _rate) {
        oracle = IAssetOracle(_oracle);
        riskManager = msg.sender;
        accrualRate = _rate;
        _systemActive = true;
    }

    function openPosition() external payable whenActive {
        require(msg.value > 0, "No collateral");
        _positions[msg.sender].collateral += msg.value;
        totalCollateral += msg.value;
        emit PositionOpened(msg.sender, msg.value);
    }

    function issueCreditLine(uint256 amount) external whenActive nonReentrant {
        CreditPosition storage pos = _positions[msg.sender];
        _accrueInterest(pos);
        (uint256 price, uint256 updatedAt) = oracle.getLatestValue();
        require(block.timestamp - updatedAt < ORACLE_FRESHNESS, "Stale price"); // FIXED
        uint256 collateralValue = (pos.collateral * price) / 1e18;
        uint256 newLiability = pos.liability + amount;
        require((collateralValue * 10000) / newLiability >= HEALTH_THRESHOLD, "Undercollateralized");
        pos.liability = newLiability;
        totalLiabilities += amount;
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Transfer failed");
        emit CreditIssued(msg.sender, amount);
    }

    function settlePosition() external nonReentrant { // FIXED: nonReentrant + CEI
        CreditPosition storage pos = _positions[msg.sender];
        _accrueInterest(pos);
        require(pos.collateral > 0, "No position");
        uint256 returnAmount = pos.collateral;
        require(pos.liability == 0, "Outstanding liability");
        pos.collateral = 0;
        totalCollateral -= returnAmount;
        (bool ok, ) = msg.sender.call{value: returnAmount}("");
        require(ok, "Settlement failed");
        emit PositionSettled(msg.sender, returnAmount);
    }

    function forceClosePosition(address account) external onlyRiskManager { // FIXED: access control
        CreditPosition storage pos = _positions[account];
        _accrueInterest(pos);
        (uint256 price, uint256 updatedAt) = oracle.getLatestValue();
        require(block.timestamp - updatedAt < ORACLE_FRESHNESS, "Stale price");
        uint256 collateralValue = (pos.collateral * price) / 1e18;
        require((collateralValue * 10000) / pos.liability < HEALTH_THRESHOLD, "Position healthy");
        uint256 seized = pos.collateral;
        pos.collateral = 0;
        totalLiabilities -= pos.liability;
        pos.liability = 0;
        totalCollateral -= seized;
        (bool ok, ) = msg.sender.call{value: seized}("");
        require(ok, "Seizure failed");
    }

    function recalibrateSystem(uint256 newRate, address newOracle) external onlyRiskManager { // FIXED
        accrualRate = newRate;
        oracle = IAssetOracle(newOracle);
    }

    function toggleSystemState() external onlyRiskManager { _systemActive = !_systemActive; }

    function _accrueInterest(CreditPosition storage pos) internal {
        if (pos.liability > 0 && pos.lastAccrual > 0) {
            uint256 elapsed = block.timestamp - pos.lastAccrual;
            uint256 interest = pos.liability.computeAccrual(accrualRate, elapsed);
            pos.liability += interest;
            totalLiabilities += interest;
        }
        pos.lastAccrual = block.timestamp;
    }

    function positionHealth(address account) external view returns (uint256) {
        CreditPosition memory pos = _positions[account];
        if (pos.liability == 0) return type(uint256).max;
        (uint256 price, ) = oracle.getLatestValue();
        return (pos.collateral * price * 10000) / (pos.liability * 1e18);
    }

    receive() external payable {}
}
