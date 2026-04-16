// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title RewardDistributor - Distributes rewards to vault depositors
contract RewardDistributor {
    address public vault;
    address public owner;
    mapping(address => uint256) public pendingRewards;
    address[] public rewardRecipients;

    constructor(address _vault) {
        vault = _vault;
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    /// @notice Register a reward for a user
    function registerReward(address user, uint256 amount) external onlyOwner {
        if (pendingRewards[user] == 0) {
            rewardRecipients.push(user);
        }
        pendingRewards[user] += amount;
    }

    /// @notice Claim pending rewards
    /// @dev VULNERABILITY: Reentrancy - state update after call
    function claimReward() external {
        uint256 amount = pendingRewards[msg.sender];
        require(amount > 0, "No rewards");

        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Claim failed");

        pendingRewards[msg.sender] = 0;
    }

    /// @notice Distribute rewards to all recipients
    /// @dev VULNERABILITY: Unbounded loop - DoS if too many recipients
    function distributeAll() external onlyOwner {
        for (uint256 i = 0; i < rewardRecipients.length; i++) {
            address user = rewardRecipients[i];
            uint256 amount = pendingRewards[user];
            if (amount > 0) {
                pendingRewards[user] = 0;
                (bool ok, ) = user.call{value: amount}("");
                require(ok, "Distribution failed");
            }
        }
        delete rewardRecipients;
    }

    /// @notice Emergency drain
    /// @dev VULNERABILITY: Missing access control
    function emergencyDrain(address to) external {
        (bool ok, ) = to.call{value: address(this).balance}("");
        require(ok, "Drain failed");
    }

    receive() external payable {}
}
