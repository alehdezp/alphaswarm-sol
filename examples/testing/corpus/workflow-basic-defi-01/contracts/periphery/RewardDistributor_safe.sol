// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title RewardDistributor - SAFE VARIANT
contract RewardDistributor_safe {
    address public vault;
    address public owner;
    mapping(address => uint256) public pendingRewards;
    address[] public rewardRecipients;
    bool private _locked;
    uint256 public constant MAX_RECIPIENTS = 100;

    modifier nonReentrant() {
        require(!_locked, "Reentrancy");
        _locked = true;
        _;
        _locked = false;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    constructor(address _vault) {
        vault = _vault;
        owner = msg.sender;
    }

    function registerReward(address user, uint256 amount) external onlyOwner {
        if (pendingRewards[user] == 0) {
            require(rewardRecipients.length < MAX_RECIPIENTS, "Too many recipients");
            rewardRecipients.push(user);
        }
        pendingRewards[user] += amount;
    }

    /// @notice FIXED: nonReentrant + CEI pattern
    function claimReward() external nonReentrant {
        uint256 amount = pendingRewards[msg.sender];
        require(amount > 0, "No rewards");
        pendingRewards[msg.sender] = 0;
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Claim failed");
    }

    /// @notice FIXED: Bounded loop with pagination
    function distributeAll(uint256 offset, uint256 limit) external onlyOwner {
        uint256 end = offset + limit;
        if (end > rewardRecipients.length) end = rewardRecipients.length;
        for (uint256 i = offset; i < end; i++) {
            address user = rewardRecipients[i];
            uint256 amount = pendingRewards[user];
            if (amount > 0) {
                pendingRewards[user] = 0;
                (bool ok, ) = user.call{value: amount}("");
                require(ok, "Distribution failed");
            }
        }
    }

    /// @notice FIXED: Access control added
    function emergencyDrain(address to) external onlyOwner {
        (bool ok, ) = to.call{value: address(this).balance}("");
        require(ok, "Drain failed");
    }

    receive() external payable {}
}
