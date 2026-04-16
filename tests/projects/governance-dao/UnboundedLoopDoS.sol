// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title UnboundedLoopDoS
 * @notice Test contract for dos-001-unbounded-loop pattern
 * @dev Tests unbounded loop denial of service vulnerabilities
 *
 * TRUE POSITIVES: Functions with unbounded loops that can cause DoS
 * TRUE NEGATIVES: Safe patterns with bounded loops, pull patterns, early exits
 * EDGE CASES: Loops with various exit conditions, require checks
 * VARIATIONS: Different loop types (for, while), different bound sources
 */
contract UnboundedLoopDoS {
    address[] public users;
    address[] public voters;
    mapping(address => uint256) public balances;
    mapping(address => bool) public hasVoted;
    mapping(address => uint256) public userIndex;

    address public owner;
    uint256 public totalRewards;

    // For pagination tests
    uint256 public constant MAX_BATCH_SIZE = 100;

    constructor() {
        owner = msg.sender;
    }

    // =============================================================================
    // TRUE POSITIVES: Unbounded loops that should be flagged
    // =============================================================================

    /// @notice TP-1: Classic unbounded array iteration
    /// @dev Loops over entire users array without bounds - classic DoS vector
    function distributeRewards(uint256 amountPerUser) external {
        for (uint256 i = 0; i < users.length; i++) {
            balances[users[i]] += amountPerUser;
        }
    }

    /// @notice TP-2: Unbounded loop with external state write
    /// @dev Iterates all voters - governance DoS attack vector
    function tallyVotes() external returns (uint256 yesVotes) {
        for (uint256 i = 0; i < voters.length; i++) {
            if (hasVoted[voters[i]]) {
                yesVotes++;
            }
        }
        return yesVotes;
    }

    /// @notice TP-3: Unbounded while loop based on array length
    /// @dev While loop variant - still unbounded
    function processAllUsers() external {
        uint256 i = 0;
        while (i < users.length) {
            balances[users[i]] = 0;
            i++;
        }
    }

    /// @notice TP-4: Unbounded loop with value transfer
    /// @dev Most dangerous - can trap funds permanently
    function distributeETH() external payable {
        uint256 share = msg.value / users.length;
        for (uint256 i = 0; i < users.length; i++) {
            payable(users[i]).transfer(share);
        }
    }

    /// @notice TP-5: Nested unbounded loops
    /// @dev Extremely dangerous - quadratic gas cost
    function crossReferenceUsers() external {
        for (uint256 i = 0; i < users.length; i++) {
            for (uint256 j = 0; j < voters.length; j++) {
                if (users[i] == voters[j]) {
                    balances[users[i]] += 1;
                }
            }
        }
    }

    /// @notice TP-6: Unbounded loop finding element
    /// @dev Linear search over unbounded array
    function findUser(address user) external view returns (uint256) {
        for (uint256 i = 0; i < users.length; i++) {
            if (users[i] == user) {
                return i;
            }
        }
        revert("User not found");
    }

    /// @notice TP-7: Unbounded loop with deletion
    /// @dev Deletion in loop - gas intensive
    function clearAllUsers() external {
        for (uint256 i = 0; i < users.length; i++) {
            delete balances[users[i]];
        }
    }

    /// @notice TP-8: Unbounded loop with user input bound (implicit)
    /// @dev User controls array size indirectly through addUser()
    function rewardAllUsers() external {
        for (uint256 i = 0; i < users.length; i++) {
            balances[users[i]] += totalRewards;
        }
    }

    // =============================================================================
    // TRUE NEGATIVES: Safe patterns that should NOT be flagged
    // =============================================================================

    /// @notice TN-1: Bounded loop with explicit max check
    /// @dev Enforces maximum iteration limit - SAFE
    function distributeBounded(uint256 start, uint256 end, uint256 amount) external {
        require(end <= users.length, "Invalid range");
        require(end - start <= MAX_BATCH_SIZE, "Batch too large");

        for (uint256 i = start; i < end; i++) {
            balances[users[i]] += amount;
        }
    }

    /// @notice TN-2: Direct mapping lookup (no loop)
    /// @dev Uses mapping instead of iteration - SAFE
    function getUserIndexSafe(address user) external view returns (uint256) {
        require(userIndex[user] != 0, "User not found");
        return userIndex[user];
    }

    /// @notice TN-3: Pull pattern (no loop)
    /// @dev Users claim individually - SAFE pull-over-push pattern
    function claimReward() external {
        uint256 reward = balances[msg.sender];
        require(reward > 0, "No rewards");
        balances[msg.sender] = 0;
        payable(msg.sender).transfer(reward);
    }

    /// @notice TN-4: Fixed-size loop (not dependent on storage)
    /// @dev Loop bound is constant - SAFE
    function processFixedCount() external {
        for (uint256 i = 0; i < 10; i++) {
            // Process fixed number of items
            totalRewards += i;
        }
    }

    /// @notice TN-5: Loop with parameter bound (bounded by caller)
    /// @dev Bound is function parameter, not storage - SAFER
    /// @dev NOTE: This might still be flagged if count can be arbitrarily large
    function processCount(uint256 count) external {
        for (uint256 i = 0; i < count; i++) {
            totalRewards += i;
        }
    }

    /// @notice TN-6: Internal helper (not directly callable)
    /// @dev Internal functions have lower DoS risk
    function _internalDistribute(uint256 amount) internal {
        for (uint256 i = 0; i < users.length; i++) {
            balances[users[i]] += amount;
        }
    }

    /// @notice TN-7: View function with unbounded loop
    /// @dev View functions don't cause permanent DoS (only query failure)
    /// @dev NOTE: Pattern currently doesn't exclude view functions, so this might still flag
    function countUsers() external view returns (uint256) {
        uint256 count = 0;
        for (uint256 i = 0; i < users.length; i++) {
            if (balances[users[i]] > 0) {
                count++;
            }
        }
        return count;
    }

    /// @notice TN-8: Pure function (no storage access)
    /// @dev Pure functions can't have unbounded storage loops
    function calculateSum(uint256[] memory amounts) external pure returns (uint256) {
        uint256 sum = 0;
        for (uint256 i = 0; i < amounts.length; i++) {
            sum += amounts[i];
        }
        return sum;
    }

    // =============================================================================
    // EDGE CASES: Boundary conditions and variations
    // =============================================================================

    /// @notice EDGE-1: Loop with early break based on condition
    /// @dev Has break statement but still unbounded worst-case
    /// @dev Should still be flagged - break doesn't guarantee bounded execution
    function findFirstActiveUser() external view returns (address) {
        for (uint256 i = 0; i < users.length; i++) {
            if (balances[users[i]] > 0) {
                return users[i];
            }
        }
        revert("No active users");
    }

    /// @notice EDGE-2: Loop with require check inside (not on range)
    /// @dev Require inside loop doesn't bound iteration count
    function distributeWithChecks(uint256 amount) external {
        for (uint256 i = 0; i < users.length; i++) {
            require(balances[users[i]] + amount <= type(uint256).max, "Overflow");
            balances[users[i]] += amount;
        }
    }

    /// @notice EDGE-3: Reverse iteration (decrementing loop)
    /// @dev Still unbounded even though counting down
    function processReverse() external {
        for (uint256 i = users.length; i > 0; i--) {
            balances[users[i - 1]] = 0;
        }
    }

    /// @notice EDGE-4: Loop with continue statement
    /// @dev Continue doesn't reduce iteration count
    function selectiveDistribute(uint256 amount) external {
        for (uint256 i = 0; i < users.length; i++) {
            if (balances[users[i]] == 0) {
                continue;
            }
            balances[users[i]] += amount;
        }
    }

    /// @notice EDGE-5: Do-while unbounded loop
    /// @dev Another loop variant
    function processDoWhile() external {
        uint256 i = 0;
        if (users.length > 0) {
            do {
                balances[users[i]] = 0;
                i++;
            } while (i < users.length);
        }
    }

    /// @notice EDGE-6: Multiple sequential unbounded loops
    /// @dev Multiple vulnerable loops in one function
    function multipleLoops(uint256 amount) external {
        // First loop
        for (uint256 i = 0; i < users.length; i++) {
            balances[users[i]] += amount;
        }

        // Second loop
        for (uint256 i = 0; i < voters.length; i++) {
            hasVoted[voters[i]] = false;
        }
    }

    /// @notice EDGE-7: Loop with gas-intensive operation
    /// @dev SSTORE in loop makes DoS even more likely
    function expensiveOperation() external {
        for (uint256 i = 0; i < users.length; i++) {
            // Multiple SSTOREs per iteration
            balances[users[i]] = balances[users[i]] * 2;
            hasVoted[users[i]] = true;
        }
    }

    /// @notice EDGE-8: Conditional unbounded loop (if-guarded)
    /// @dev Unbounded loop behind condition - still vulnerable when condition true
    function conditionalDistribute(bool shouldDistribute, uint256 amount) external {
        if (shouldDistribute) {
            for (uint256 i = 0; i < users.length; i++) {
                balances[users[i]] += amount;
            }
        }
    }

    // =============================================================================
    // VARIATION TESTING: Different naming and patterns
    // =============================================================================

    /// @notice VAR-1: Different array name (participants instead of users)
    /// @dev Tests name-agnostic detection
    address[] public participants;

    function rewardParticipants(uint256 amount) external {
        for (uint256 i = 0; i < participants.length; i++) {
            balances[participants[i]] += amount;
        }
    }

    /// @notice VAR-2: Different loop variable name
    /// @dev Tests detection works with different variable names
    function distributeWithDifferentVar(uint256 amount) external {
        for (uint256 index = 0; index < users.length; index++) {
            balances[users[index]] += amount;
        }
    }

    /// @notice VAR-3: Compound loop condition
    /// @dev More complex condition but still unbounded
    function complexCondition(uint256 amount) external {
        for (uint256 i = 0; i < users.length && i < voters.length; i++) {
            balances[users[i]] += amount;
        }
    }

    /// @notice VAR-4: Loop with increment at end
    /// @dev Different increment style
    function differentIncrement(uint256 amount) external {
        for (uint256 i = 0; i < users.length;) {
            balances[users[i]] += amount;
            i++;
        }
    }

    /// @notice VAR-5: Loop accessing nested struct array
    /// @dev Tests detection on more complex data structures
    struct UserGroup {
        address[] members;
    }
    UserGroup internal group;

    function distributeToGroup(uint256 amount) external {
        for (uint256 i = 0; i < group.members.length; i++) {
            balances[group.members[i]] += amount;
        }
    }

    // =============================================================================
    // HELPER FUNCTIONS (for growing arrays)
    // =============================================================================

    function addUser(address user) external {
        users.push(user);
        userIndex[user] = users.length;
    }

    function addVoter(address voter) external {
        voters.push(voter);
    }

    function addParticipant(address participant) external {
        participants.push(participant);
    }
}
