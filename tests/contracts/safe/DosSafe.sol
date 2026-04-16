// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title DosSafe
 * @notice Safe implementations protecting against Denial of Service attacks.
 * @dev These contracts demonstrate proper protections against DoS vectors.
 */

/**
 * @title BoundedLoopSafe
 * @notice Safe: Loop iterations are bounded
 */
contract BoundedLoopSafe {
    uint256 public constant MAX_BATCH_SIZE = 100;

    mapping(address => uint256) public balances;
    address[] public users;

    // SAFE: Loop has explicit bound
    function distributeRewards(uint256 perUserAmount) external {
        uint256 length = users.length;
        require(length <= MAX_BATCH_SIZE, "Too many users, use batch");

        for (uint256 i = 0; i < length; i++) {
            balances[users[i]] += perUserAmount;
        }
    }

    // SAFE: Paginated batch processing
    function distributeRewardsBatched(
        uint256 perUserAmount,
        uint256 startIndex,
        uint256 batchSize
    ) external {
        require(batchSize <= MAX_BATCH_SIZE, "Batch too large");
        uint256 endIndex = startIndex + batchSize;
        if (endIndex > users.length) {
            endIndex = users.length;
        }

        for (uint256 i = startIndex; i < endIndex; i++) {
            balances[users[i]] += perUserAmount;
        }
    }
}

/**
 * @title NoExternalCallInLoopSafe
 * @notice Safe: External calls are not made inside loops
 */
contract NoExternalCallInLoopSafe {
    mapping(address => uint256) public pendingPayments;
    address[] public recipients;

    // SAFE: Calculate totals in loop, single external call outside
    function preparePayments(uint256[] calldata amounts) external {
        require(amounts.length == recipients.length, "Length mismatch");
        for (uint256 i = 0; i < amounts.length; i++) {
            pendingPayments[recipients[i]] += amounts[i];
        }
    }

    // SAFE: Pull pattern - each user claims their own payment
    function claimPayment() external {
        uint256 amount = pendingPayments[msg.sender];
        require(amount > 0, "Nothing to claim");
        pendingPayments[msg.sender] = 0;
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
    }

    receive() external payable {}
}

/**
 * @title NoStrictEqualitySafe
 * @notice Safe: Uses >= instead of == for balance checks
 */
contract NoStrictEqualitySafe {
    uint256 public targetAmount;
    bool public goalReached;

    constructor(uint256 _target) {
        targetAmount = _target;
    }

    // SAFE: Uses >= instead of ==
    function checkGoal() external {
        if (address(this).balance >= targetAmount) {
            goalReached = true;
        }
    }

    // SAFE: Range check instead of exact match
    function processWithinRange(uint256 value) external pure returns (bool) {
        // Accept values within a range instead of exact match
        return value >= 100 && value <= 1000;
    }

    receive() external payable {}
}

/**
 * @title SafeSendPatternSafe
 * @notice Safe: Failed sends don't revert the whole transaction
 */
contract SafeSendPatternSafe {
    mapping(address => uint256) public pendingRefunds;

    // SAFE: Store failed sends for later claim
    function sendOrStore(address recipient, uint256 amount) external {
        (bool success, ) = recipient.call{value: amount}("");
        if (!success) {
            // Store for pull withdrawal instead of reverting
            pendingRefunds[recipient] += amount;
        }
    }

    // SAFE: Pull pattern for failed sends
    function withdrawRefund() external {
        uint256 amount = pendingRefunds[msg.sender];
        require(amount > 0, "No refund pending");
        pendingRefunds[msg.sender] = 0;
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Refund failed");
    }

    receive() external payable {}
}

/**
 * @title ArrayLengthCachedSafe
 * @notice Safe: Array length cached before loop
 */
contract ArrayLengthCachedSafe {
    uint256[] public values;

    function addValue(uint256 value) external {
        values.push(value);
    }

    // SAFE: Length cached, no SLOAD in loop condition
    function sumValues() external view returns (uint256) {
        uint256 total = 0;
        uint256 length = values.length;  // Cache length
        for (uint256 i = 0; i < length; i++) {
            total += values[i];
        }
        return total;
    }
}

/**
 * @title GasLimitedBatchSafe
 * @notice Safe: Gas limit checked during batch processing
 */
contract GasLimitedBatchSafe {
    uint256 public constant MIN_GAS_FOR_ITERATION = 30000;

    mapping(address => uint256) public balances;
    address[] public users;

    // SAFE: Check gas before each iteration
    function distributeWithGasCheck(uint256 perUserAmount) external {
        for (uint256 i = 0; i < users.length; i++) {
            // Ensure enough gas for next iteration
            if (gasleft() < MIN_GAS_FOR_ITERATION) {
                // Emit event or store progress for continuation
                break;
            }
            balances[users[i]] += perUserAmount;
        }
    }
}

/**
 * @title MerkleProofDistributionSafe
 * @notice Safe: Use merkle proofs instead of loops for airdrops
 */
contract MerkleProofDistributionSafe {
    bytes32 public merkleRoot;
    mapping(address => bool) public hasClaimed;

    constructor(bytes32 _merkleRoot) {
        merkleRoot = _merkleRoot;
    }

    // SAFE: O(log n) verification instead of O(n) loop
    function claim(uint256 amount, bytes32[] calldata proof) external {
        require(!hasClaimed[msg.sender], "Already claimed");

        bytes32 leaf = keccak256(abi.encodePacked(msg.sender, amount));
        require(verify(proof, merkleRoot, leaf), "Invalid proof");

        hasClaimed[msg.sender] = true;
        // Transfer tokens...
    }

    function verify(bytes32[] calldata proof, bytes32 root, bytes32 leaf) internal pure returns (bool) {
        bytes32 computedHash = leaf;
        for (uint256 i = 0; i < proof.length; i++) {
            computedHash = computedHash < proof[i]
                ? keccak256(abi.encodePacked(computedHash, proof[i]))
                : keccak256(abi.encodePacked(proof[i], computedHash));
        }
        return computedHash == root;
    }
}

/**
 * @title SafeArrayDeletionSafe
 * @notice Safe: Efficient array element deletion
 */
contract SafeArrayDeletionSafe {
    address[] public activeUsers;
    mapping(address => uint256) public userIndex;

    function addUser(address user) external {
        userIndex[user] = activeUsers.length;
        activeUsers.push(user);
    }

    // SAFE: O(1) deletion by swapping with last element
    function removeUser(address user) external {
        uint256 index = userIndex[user];
        require(index < activeUsers.length, "User not found");

        // Swap with last element
        address lastUser = activeUsers[activeUsers.length - 1];
        activeUsers[index] = lastUser;
        userIndex[lastUser] = index;

        // Remove last element
        activeUsers.pop();
        delete userIndex[user];
    }
}
