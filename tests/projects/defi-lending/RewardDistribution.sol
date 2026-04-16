// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title RewardDistribution
 * @notice Test contract for dos-001-unbounded-loop in DeFi reward scenarios
 * @dev Tests unbounded loops in staking/lending reward distribution
 *
 * Focuses on DeFi-specific patterns:
 * - Staking reward distribution
 * - Yield farming batch operations
 * - Liquidity pool fee distribution
 * - Withdrawal queue processing
 */
contract RewardDistribution {
    address[] public stakers;
    address[] public withdrawalQueue;
    mapping(address => uint256) public stakes;
    mapping(address => uint256) public pendingRewards;
    mapping(address => uint256) public lastRewardBlock;

    uint256 public rewardPerBlock;
    uint256 public totalStaked;

    // For pull pattern
    uint256 public rewardIndex;
    mapping(address => uint256) public userRewardIndex;

    // =============================================================================
    // TRUE POSITIVES: DeFi unbounded loop vulnerabilities
    // =============================================================================

    /// @notice TP-1: Unbounded staking reward distribution
    /// @dev Classic push-based reward distribution - can be DoS'd
    function distributeStakingRewards() external {
        for (uint256 i = 0; i < stakers.length; i++) {
            uint256 reward = calculateReward(stakers[i]);
            pendingRewards[stakers[i]] += reward;
            lastRewardBlock[stakers[i]] = block.number;
        }
    }

    /// @notice TP-2: Unbounded withdrawal processing
    /// @dev Processes entire withdrawal queue - can trap funds
    function processWithdrawals() external {
        for (uint256 i = 0; i < withdrawalQueue.length; i++) {
            address user = withdrawalQueue[i];
            uint256 amount = stakes[user];
            stakes[user] = 0;
            payable(user).transfer(amount);
        }
        delete withdrawalQueue;
    }

    /// @notice TP-3: Compound-style reward distribution
    /// @dev Calculates and distributes in one transaction
    function compoundRewards() external {
        for (uint256 i = 0; i < stakers.length; i++) {
            address staker = stakers[i];
            uint256 reward = calculateReward(staker);
            stakes[staker] += reward; // Auto-compound
            lastRewardBlock[staker] = block.number;
        }
    }

    /// @notice TP-4: Emergency withdrawal for all users
    /// @dev Emergency function that processes all users at once
    function emergencyWithdrawAll() external {
        for (uint256 i = 0; i < stakers.length; i++) {
            address staker = stakers[i];
            uint256 amount = stakes[staker];
            stakes[staker] = 0;
            payable(staker).transfer(amount);
        }
    }

    /// @notice TP-5: Sweep rewards to treasury
    /// @dev Admin function to collect unclaimed rewards
    function sweepUnclaimedRewards(address treasury) external {
        for (uint256 i = 0; i < stakers.length; i++) {
            if (pendingRewards[stakers[i]] > 0) {
                uint256 amount = pendingRewards[stakers[i]];
                pendingRewards[stakers[i]] = 0;
                payable(treasury).transfer(amount);
            }
        }
    }

    /// @notice TP-6: Snapshot all balances
    /// @dev Creates storage snapshot of all user balances
    mapping(uint256 => mapping(address => uint256)) public snapshots;
    uint256 public snapshotId;

    function snapshotBalances() external {
        for (uint256 i = 0; i < stakers.length; i++) {
            snapshots[snapshotId][stakers[i]] = stakes[stakers[i]];
        }
        snapshotId++;
    }

    // =============================================================================
    // TRUE NEGATIVES: Safe DeFi patterns
    // =============================================================================

    /// @notice TN-1: Pull-based reward claiming
    /// @dev Users claim their own rewards - SAFE
    function claimReward() external {
        uint256 reward = calculateReward(msg.sender);
        pendingRewards[msg.sender] += reward;
        lastRewardBlock[msg.sender] = block.number;

        uint256 amount = pendingRewards[msg.sender];
        pendingRewards[msg.sender] = 0;
        payable(msg.sender).transfer(amount);
    }

    /// @notice TN-2: Paginated withdrawal processing
    /// @dev Processes withdrawals in batches with max limit
    function processWithdrawalsBatch(uint256 start, uint256 end) external {
        require(end <= withdrawalQueue.length, "Invalid range");
        require(end - start <= 50, "Batch too large");

        for (uint256 i = start; i < end; i++) {
            address user = withdrawalQueue[i];
            uint256 amount = stakes[user];
            stakes[user] = 0;
            payable(user).transfer(amount);
        }
    }

    /// @notice TN-3: Index-based reward tracking (Compound-style)
    /// @dev Uses global reward index - no iteration needed
    function updateRewardIndex() external {
        if (totalStaked > 0) {
            uint256 reward = rewardPerBlock * (block.number - lastRewardBlock[address(this)]);
            rewardIndex += (reward * 1e18) / totalStaked;
            lastRewardBlock[address(this)] = block.number;
        }
    }

    /// @notice TN-4: Individual stake/unstake (no loops)
    /// @dev Direct operations without iteration
    function stake() external payable {
        stakes[msg.sender] += msg.value;
        totalStaked += msg.value;
    }

    function unstake(uint256 amount) external {
        require(stakes[msg.sender] >= amount, "Insufficient stake");
        stakes[msg.sender] -= amount;
        totalStaked -= amount;
        payable(msg.sender).transfer(amount);
    }

    /// @notice TN-5: Single user snapshot
    /// @dev Snapshots one user at a time
    function snapshotUser(address user) external {
        snapshots[snapshotId][user] = stakes[user];
    }

    // =============================================================================
    // EDGE CASES: DeFi-specific boundary conditions
    // =============================================================================

    /// @notice EDGE-1: Loop with early exit on threshold
    /// @dev Stops after processing certain amount, but still unbounded worst-case
    function distributeUntilLimit(uint256 maxReward) external {
        uint256 distributed = 0;
        for (uint256 i = 0; i < stakers.length; i++) {
            if (distributed >= maxReward) {
                break;
            }
            uint256 reward = calculateReward(stakers[i]);
            pendingRewards[stakers[i]] += reward;
            distributed += reward;
        }
    }

    /// @notice EDGE-2: Conditional distribution based on stake size
    /// @dev Only distributes to large stakers, but still unbounded loop
    function distributeToBigStakers(uint256 minStake) external {
        for (uint256 i = 0; i < stakers.length; i++) {
            if (stakes[stakers[i]] >= minStake) {
                uint256 reward = calculateReward(stakers[i]);
                pendingRewards[stakers[i]] += reward;
            }
        }
    }

    /// @notice EDGE-3: Two-phase withdrawal (queue + process)
    /// @dev Even with queue, processing is unbounded
    function finalizeWithdrawals() external {
        // Process all queued withdrawals
        for (uint256 i = 0; i < withdrawalQueue.length; i++) {
            address user = withdrawalQueue[i];
            if (stakes[user] > 0) {
                uint256 amount = stakes[user];
                stakes[user] = 0;
                payable(user).transfer(amount);
            }
        }
    }

    /// @notice EDGE-4: Reward distribution with admin override
    /// @dev Admin can trigger unbounded distribution
    address public admin;

    function adminDistributeRewards() external {
        require(msg.sender == admin, "Only admin");
        for (uint256 i = 0; i < stakers.length; i++) {
            uint256 reward = rewardPerBlock;
            pendingRewards[stakers[i]] += reward;
        }
    }

    // =============================================================================
    // VARIATION TESTING: Different DeFi patterns
    // =============================================================================

    /// @notice VAR-1: Liquidity provider reward distribution
    /// @dev Different terminology but same vulnerability
    address[] public liquidityProviders;
    mapping(address => uint256) public liquidity;

    function distributeLPRewards(uint256 totalReward) external {
        for (uint256 i = 0; i < liquidityProviders.length; i++) {
            uint256 share = (liquidity[liquidityProviders[i]] * totalReward) / totalStaked;
            pendingRewards[liquidityProviders[i]] += share;
        }
    }

    /// @notice VAR-2: Yield farming harvest
    /// @dev Farming-specific terminology
    address[] public farmers;
    mapping(address => uint256) public deposits;

    function harvestAll() external {
        for (uint256 i = 0; i < farmers.length; i++) {
            uint256 yield = calculateYield(farmers[i]);
            pendingRewards[farmers[i]] += yield;
        }
    }

    /// @notice VAR-3: Fee distribution to token holders
    /// @dev Different use case, same vulnerability
    address[] public tokenHolders;
    mapping(address => uint256) public tokenBalances;

    function distributeFees(uint256 totalFees) external {
        uint256 totalTokens = getTotalTokens();
        for (uint256 i = 0; i < tokenHolders.length; i++) {
            uint256 share = (tokenBalances[tokenHolders[i]] * totalFees) / totalTokens;
            pendingRewards[tokenHolders[i]] += share;
        }
    }

    // =============================================================================
    // HELPER FUNCTIONS
    // =============================================================================

    function calculateReward(address user) internal view returns (uint256) {
        uint256 blocks = block.number - lastRewardBlock[user];
        return stakes[user] * rewardPerBlock * blocks / 1e18;
    }

    function calculateYield(address user) internal view returns (uint256) {
        return deposits[user] * rewardPerBlock / 1e18;
    }

    function getTotalTokens() internal view returns (uint256) {
        uint256 total = 0;
        for (uint256 i = 0; i < tokenHolders.length; i++) {
            total += tokenBalances[tokenHolders[i]];
        }
        return total;
    }

    function addStaker(address staker) external {
        stakers.push(staker);
        lastRewardBlock[staker] = block.number;
    }

    function queueWithdrawal(address user) external {
        withdrawalQueue.push(user);
    }
}
