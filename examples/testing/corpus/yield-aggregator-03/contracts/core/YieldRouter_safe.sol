// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title YieldRouter (SAFE VARIANT)
contract YieldRouter_safe {
    struct Strategy { address vault; uint256 allocation; bool active; }

    mapping(uint256 => Strategy) public strategies;
    mapping(address => uint256) public userDeposits;
    mapping(address => uint256) public userShares;
    uint256 public strategyCount;
    uint256 public totalDeposits;
    uint256 public totalShares;
    address public strategist;
    bool private _locked;
    uint256 public constant MAX_STRATEGIES = 20;

    modifier nonReentrant() { require(!_locked); _locked = true; _; _locked = false; }
    modifier onlyStrategist() { require(msg.sender == strategist, "Not strategist"); _; }

    event Deposited(address indexed user, uint256 amount);
    event Withdrawn(address indexed user, uint256 amount);
    event Harvested(uint256 totalYield);

    constructor() { strategist = msg.sender; }

    function allocateCapital(uint256 amount) external payable {
        require(msg.value == amount && amount > 0, "Invalid");
        uint256 shares = totalShares == 0 ? amount : (amount * totalShares) / totalDeposits;
        userDeposits[msg.sender] += amount;
        userShares[msg.sender] += shares;
        totalDeposits += amount;
        totalShares += shares;
        emit Deposited(msg.sender, amount);
    }

    function reclaimCapital(uint256 shareAmount) external nonReentrant {
        require(userShares[msg.sender] >= shareAmount, "Insufficient");
        uint256 payout = (shareAmount * totalDeposits) / totalShares;
        userShares[msg.sender] -= shareAmount;
        totalDeposits -= payout;
        totalShares -= shareAmount;
        (bool ok, ) = msg.sender.call{value: payout}("");
        require(ok, "Withdrawal failed");
        emit Withdrawn(msg.sender, payout);
    }

    function harvestAllYields() external onlyStrategist {
        uint256 totalYield;
        uint256 count = strategyCount;
        require(count <= MAX_STRATEGIES, "Too many strategies");
        for (uint256 i = 0; i < count; i++) {
            Strategy memory s = strategies[i];
            if (s.active) {
                (bool ok, bytes memory data) = s.vault.call(abi.encodeWithSignature("harvest()"));
                if (ok && data.length >= 32) { totalYield += abi.decode(data, (uint256)); }
            }
        }
        totalDeposits += totalYield;
        emit Harvested(totalYield);
    }

    function registerStrategy(address vault, uint256 allocation) external onlyStrategist {
        require(strategyCount < MAX_STRATEGIES, "Max strategies");
        strategies[strategyCount] = Strategy(vault, allocation, true);
        strategyCount++;
    }

    function deactivateStrategy(uint256 id) external onlyStrategist { strategies[id].active = false; }

    function recoverFunds(address to, uint256 amount) external onlyStrategist {
        (bool ok, ) = to.call{value: amount}("");
        require(ok, "Recovery failed");
    }

    function rotateStrategist(address newStrategist) external onlyStrategist {
        require(newStrategist != address(0));
        strategist = newStrategist;
    }

    receive() external payable {}
}
