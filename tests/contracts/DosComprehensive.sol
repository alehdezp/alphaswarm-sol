// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

/**
 * Comprehensive DoS (Denial of Service) Test Contract
 *
 * This contract demonstrates various DoS attack vectors identified in:
 * - CWE-400: Uncontrolled Resource Consumption
 * - CWE-770: Allocation of Resources Without Limits or Throttling
 * - CWE-834: Excessive Iteration
 * - SWC-113: DoS with Failed Call
 * - SWC-128: DoS with Block Gas Limit
 * - OWASP SC10:2025: Denial of Service
 *
 * Attack vectors covered:
 * 1. Gas Limit DoS - Unbounded loops
 * 2. Block Gas Limit DoS - External calls in loops
 * 3. Unbounded Deletion - Storage operations in unbounded loops
 * 4. DoS with Unexpected Revert - Failed external calls blocking execution
 * 5. DoS via Strict Equality - Assert/require with exact balance checks
 * 6. DoS via Large Array Access - Accessing arrays without pagination
 * 7. DoS via Failed Transfer - Push payment pattern that can be blocked
 */

contract DosComprehensive {
    address[] public recipients;
    uint256[] public data;
    mapping(address => uint256) public balances;
    address public currentLeader;
    uint256 public highestBid;
    uint256 public totalDeposited;

    // ========== 1. GAS LIMIT DOS - UNBOUNDED LOOPS ==========

    /// @notice VULNERABLE: Loop bound depends on user input (CWE-834, SWC-128)
    /// @dev An attacker can pass a large value for 'n' to cause out-of-gas
    function unboundedLoop(uint256 n) external {
        for (uint256 i = 0; i < n; i++) {
            data.push(i);
        }
    }

    /// @notice VULNERABLE: Loops over entire storage array without bounds check
    /// @dev As array grows, this function will eventually exceed block gas limit
    function processAllData() external {
        for (uint256 i = 0; i < data.length; i++) {
            data[i] = data[i] * 2;
        }
    }

    /// @notice SAFE: Loop with constant bound
    function constantBoundLoop() external {
        for (uint256 i = 0; i < 10; i++) {
            data.push(i);
        }
    }

    /// @notice SAFE: Paginated processing with bounds
    function processDataPaginated(uint256 start, uint256 end) external {
        require(end <= data.length, "Invalid range");
        require(end - start <= 100, "Batch too large");
        for (uint256 i = start; i < end; i++) {
            data[i] = data[i] * 2;
        }
    }

    // ========== 2. BLOCK GAS LIMIT DOS - EXTERNAL CALLS IN LOOPS ==========

    /// @notice VULNERABLE: External calls in unbounded loop (SWC-128)
    /// @dev Each external call consumes gas; many recipients can exceed block gas limit
    function distributeFundsAllRecipients() external {
        for (uint256 i = 0; i < recipients.length; i++) {
            (bool success, ) = recipients[i].call{value: 1 ether}("");
            require(success, "Transfer failed");
        }
    }

    /// @notice VULNERABLE: External calls in user-controlled loop
    function batchTransfer(address[] calldata targets, uint256[] calldata amounts) external {
        require(targets.length == amounts.length, "Length mismatch");
        // No upper bound check on array length
        for (uint256 i = 0; i < targets.length; i++) {
            (bool success, ) = targets[i].call{value: amounts[i]}("");
            require(success, "Transfer failed");
        }
    }

    /// @notice SAFE: External calls with pagination
    function distributeFundsPaginated(uint256 start, uint256 end) external {
        require(end <= recipients.length, "Invalid range");
        require(end - start <= 50, "Batch too large");
        for (uint256 i = start; i < end; i++) {
            (bool success, ) = recipients[i].call{value: 1 ether}("");
            require(success, "Transfer failed");
        }
    }

    // ========== 3. UNBOUNDED DELETION - STORAGE OPERATIONS ==========

    /// @notice VULNERABLE: Delete operations in unbounded loop (High severity)
    /// @dev Storage operations (SSTORE) are expensive; unbounded deletes can DoS
    function clearAllData(uint256 n) external {
        for (uint256 i = 0; i < n; i++) {
            delete data[i];
        }
    }

    /// @notice VULNERABLE: Delete entire storage array without bounds
    function clearAllStorageArray() external {
        for (uint256 i = 0; i < data.length; i++) {
            delete data[i];
        }
    }

    /// @notice SAFE: Bounded deletion
    function clearDataPaginated(uint256 start, uint256 end) external {
        require(end <= data.length, "Invalid range");
        require(end - start <= 100, "Batch too large");
        for (uint256 i = start; i < end; i++) {
            delete data[i];
        }
    }

    // ========== 4. DOS WITH UNEXPECTED REVERT (SWC-113) ==========

    /// @notice VULNERABLE: Push payment pattern susceptible to revert DoS
    /// @dev If previous leader is a contract with reverting fallback, this DoS's
    function becomeLeader() external payable {
        require(msg.value > highestBid, "Bid too low");

        // Vulnerable push payment - if this fails, entire tx reverts
        if (currentLeader != address(0)) {
            (bool success, ) = currentLeader.call{value: highestBid}("");
            require(success, "Refund failed"); // DoS vector
        }

        currentLeader = msg.sender;
        highestBid = msg.value;
    }

    /// @notice VULNERABLE: Mass refund with revert risk
    /// @dev Single failed transfer blocks all refunds
    function refundAll() external {
        for (uint256 i = 0; i < recipients.length; i++) {
            address recipient = recipients[i];
            uint256 amount = balances[recipient];
            if (amount > 0) {
                balances[recipient] = 0;
                (bool success, ) = recipient.call{value: amount}("");
                require(success, "Refund failed"); // DoS vector
            }
        }
    }

    /// @notice SAFE: Pull payment pattern (user withdraws their own funds)
    function withdraw() external {
        uint256 amount = balances[msg.sender];
        require(amount > 0, "No balance");
        balances[msg.sender] = 0;
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Withdrawal failed");
    }

    /// @notice SAFE: Push payment with failure handling (continue on error)
    function becomeLeaderSafe() external payable {
        require(msg.value > highestBid, "Bid too low");

        // Safe: Continue even if refund fails
        if (currentLeader != address(0)) {
            (bool success, ) = currentLeader.call{value: highestBid}("");
            if (!success) {
                // Fallback: Store refund in balances for pull withdrawal
                balances[currentLeader] += highestBid;
            }
        }

        currentLeader = msg.sender;
        highestBid = msg.value;
    }

    // ========== 5. DOS VIA STRICT EQUALITY (Gridlock Attack) ==========

    /// @notice VULNERABLE: Strict equality check on contract balance (CWE-1077)
    /// @dev Attacker can send ETH via selfdestruct to break this invariant
    function withdrawAllStrictEquality() external {
        // Vulnerable: Exact balance check
        assert(address(this).balance == totalDeposited);
        payable(msg.sender).transfer(totalDeposited);
        totalDeposited = 0;
    }

    /// @notice VULNERABLE: Require with strict balance equality
    function processIfExactBalance(uint256 expectedBalance) external {
        require(address(this).balance == expectedBalance, "Balance mismatch");
        // Process logic
    }

    /// @notice SAFE: Use >= instead of ==
    function withdrawAllSafe() external {
        assert(address(this).balance >= totalDeposited);
        payable(msg.sender).transfer(totalDeposited);
        totalDeposited = 0;
    }

    // ========== 6. DOS VIA LARGE ARRAY WITHOUT PAGINATION ==========

    /// @notice VULNERABLE: Reads entire array into memory
    /// @dev As array grows, memory allocation can exceed block gas limit
    function getAllRecipients() external view returns (address[] memory) {
        return recipients; // Entire array copied to memory
    }

    /// @notice VULNERABLE: Sum calculation over entire unbounded array
    function sumAllData() external view returns (uint256 total) {
        for (uint256 i = 0; i < data.length; i++) {
            total += data[i];
        }
    }

    /// @notice SAFE: Paginated view function
    function getRecipientsPaginated(uint256 start, uint256 end)
        external
        view
        returns (address[] memory)
    {
        require(end <= recipients.length, "Invalid range");
        require(end - start <= 100, "Range too large");

        address[] memory result = new address[](end - start);
        for (uint256 i = start; i < end; i++) {
            result[i - start] = recipients[i];
        }
        return result;
    }

    // ========== 7. DOS VIA FAILED TRANSFER (transfer/send) ==========

    /// @notice VULNERABLE: Using transfer() which has fixed gas stipend
    /// @dev If recipient is a contract with expensive fallback, transfer fails
    function distributeFundsWithTransfer() external {
        for (uint256 i = 0; i < recipients.length; i++) {
            payable(recipients[i]).transfer(1 ether); // Can fail and revert entire tx
        }
    }

    /// @notice VULNERABLE: Using send() without checking return value
    function distributeFundsWithSendUnchecked() external {
        for (uint256 i = 0; i < recipients.length; i++) {
            payable(recipients[i]).send(1 ether); // Ignores failure
        }
    }

    /// @notice PARTIALLY SAFE: Using send() with failure handling
    /// @dev Still has external calls in loop issue
    function distributeFundsWithSendChecked() external {
        for (uint256 i = 0; i < recipients.length; i++) {
            bool success = payable(recipients[i]).send(1 ether);
            if (!success) {
                balances[recipients[i]] += 1 ether;
            }
        }
    }

    // ========== HELPER FUNCTIONS ==========

    function addRecipient(address recipient) external {
        recipients.push(recipient);
    }

    function addData(uint256 value) external {
        data.push(value);
    }

    function deposit() external payable {
        balances[msg.sender] += msg.value;
        totalDeposited += msg.value;
    }

    receive() external payable {
        totalDeposited += msg.value;
    }
}

/**
 * @notice Malicious contract used to demonstrate DoS via revert attack
 * @dev This contract's fallback always reverts to block refunds
 */
contract MaliciousReverter {
    fallback() external payable {
        revert("I reject payments");
    }

    receive() external payable {
        revert("I reject payments");
    }

    /// @notice Attack function to exploit vulnerable contracts
    function attack(address payable target) external payable {
        DosComprehensive(target).becomeLeader{value: msg.value}();
    }
}

/**
 * @notice Contract used to demonstrate Gridlock attack via selfdestruct
 * @dev Can send ETH to target without calling fallback/receive
 */
contract GridlockAttacker {
    constructor() payable {}

    /// @notice Sends ETH to target without triggering receive/fallback
    function attack(address target) external {
        selfdestruct(payable(target));
    }
}

/**
 * @notice Safe example contract demonstrating best practices
 */
contract DosSafe {
    mapping(address => uint256) public balances;
    uint256 public constant MAX_BATCH_SIZE = 50;

    /// @notice Safe: Pull payment pattern
    function withdraw() external {
        uint256 amount = balances[msg.sender];
        require(amount > 0, "No balance");
        balances[msg.sender] = 0;
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Withdrawal failed");
    }

    /// @notice Safe: Paginated batch processing
    function processUsers(address[] calldata users, uint256 start, uint256 end) external {
        require(end <= users.length, "Invalid range");
        require(end - start <= MAX_BATCH_SIZE, "Batch too large");
        for (uint256 i = start; i < end; i++) {
            // Process user
        }
    }
}
