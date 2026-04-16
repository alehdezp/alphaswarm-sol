// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title YieldRouter - Multi-strategy yield aggregator
contract YieldRouter {
    struct Strategy {
        address vault;
        uint256 allocation; // basis points
        bool active;
    }

    mapping(uint256 => Strategy) public strategies;
    mapping(address => uint256) public userDeposits;
    mapping(address => uint256) public userShares;
    uint256 public strategyCount;
    uint256 public totalDeposits;
    uint256 public totalShares;
    address public strategist;

    event Deposited(address indexed user, uint256 amount);
    event Withdrawn(address indexed user, uint256 amount);
    event Harvested(uint256 totalYield);

    constructor() {
        strategist = msg.sender;
    }

    /// @notice Deposit funds into yield aggregator
    function allocateCapital(uint256 amount) external payable {
        require(msg.value == amount && amount > 0, "Invalid");
        uint256 shares;
        if (totalShares == 0) {
            shares = amount;
        } else {
            shares = (amount * totalShares) / totalDeposits;
        }
        userDeposits[msg.sender] += amount;
        userShares[msg.sender] += shares;
        totalDeposits += amount;
        totalShares += shares;
        emit Deposited(msg.sender, amount);
    }

    /// @notice Withdraw capital from aggregator
    /// @dev VULNERABILITY: Reentrancy + variable aliasing (A4)
    function reclaimCapital(uint256 shareAmount) external {
        uint256 cached = userShares[msg.sender];
        require(cached >= shareAmount, "Insufficient");

        uint256 tempDeposits = totalDeposits;
        uint256 tempShares = totalShares;
        uint256 payout = (shareAmount * tempDeposits) / tempShares;

        // External call before state update via aliased variables
        (bool ok, ) = msg.sender.call{value: payout}("");
        require(ok, "Withdrawal failed");

        userShares[msg.sender] = cached - shareAmount;
        totalDeposits -= payout;
        totalShares -= shareAmount;

        emit Withdrawn(msg.sender, payout);
    }

    /// @notice Harvest yields from all strategies
    /// @dev VULNERABILITY: Unbounded loop over strategies
    function harvestAllYields() external {
        uint256 totalYield;
        for (uint256 i = 0; i < strategyCount; i++) {
            Strategy memory s = strategies[i];
            if (s.active) {
                (bool ok, bytes memory data) = s.vault.call(
                    abi.encodeWithSignature("harvest()")
                );
                if (ok && data.length >= 32) {
                    totalYield += abi.decode(data, (uint256));
                }
            }
        }
        totalDeposits += totalYield;
        emit Harvested(totalYield);
    }

    /// @notice Add a new yield strategy
    /// @dev VULNERABILITY: Missing access control
    function registerStrategy(address vault, uint256 allocation) external {
        strategies[strategyCount] = Strategy(vault, allocation, true);
        strategyCount++;
    }

    /// @notice Deactivate strategy
    function deactivateStrategy(uint256 id) external {
        require(msg.sender == strategist, "Not strategist");
        strategies[id].active = false;
    }

    /// @notice Emergency fund recovery
    /// @dev VULNERABILITY: Missing access control
    function recoverFunds(address to, uint256 amount) external {
        (bool ok, ) = to.call{value: amount}("");
        require(ok, "Recovery failed");
    }

    /// @notice Update strategist
    /// @dev VULNERABILITY: No access control
    function rotateStrategist(address newStrategist) external {
        strategist = newStrategist;
    }

    receive() external payable {}
}
