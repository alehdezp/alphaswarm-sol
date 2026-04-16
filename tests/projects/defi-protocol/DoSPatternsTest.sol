// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title DoSPatternsTest
 * @notice Comprehensive test contract for DoS patterns (live-001, live-002)
 *
 * This contract tests detection of:
 * - live-001: Unbounded Loop DoS (loops without bounds + gas-intensive work)
 * - live-002: Block Gas Limit Exhaustion (external calls OR unbounded deletions in loops)
 *
 * Pattern live-001 detection logic:
 *   has_loops: true
 *   + has_unbounded_loop: true
 *   + has_require_bounds: false
 *   + (external_calls_in_loop: true OR has_delete_in_loop: true OR writes_state: true)
 *
 * Pattern live-002 detection logic:
 *   has_loops: true
 *   + (external_calls_in_loop: true OR has_unbounded_deletion: true)
 */

// =============================================================================
// SECTION 1: live-001 (Unbounded Loop DoS)
// =============================================================================

contract UnboundedLoopDoSTest {
    address[] public users;
    uint256[] public balances;
    mapping(address => uint256) public stakes;

    // === TRUE POSITIVES ===

    // TP1: Unbounded loop with state writes (classic DoS)
    function distributeRewards() external {
        for (uint256 i = 0; i < users.length; i++) {
            stakes[users[i]] += 100; // State write in unbounded loop
        }
    }

    // TP2: Unbounded loop with external calls
    function notifyAllUsers() external {
        for (uint256 i = 0; i < users.length; i++) {
            // External call in unbounded loop
            (bool success,) = users[i].call("");
            require(success);
        }
    }

    // TP3: Unbounded loop with delete operations
    function clearAllBalances() external {
        for (uint256 i = 0; i < balances.length; i++) {
            delete balances[i]; // Delete in unbounded loop
        }
    }

    // TP4: Nested unbounded loops
    mapping(address => address[]) public userConnections;
    function processConnections() external {
        for (uint256 i = 0; i < users.length; i++) {
            for (uint256 j = 0; j < userConnections[users[i]].length; j++) {
                stakes[userConnections[users[i]][j]] += 1;
            }
        }
    }

    // === TRUE NEGATIVES ===

    // TN1: Bounded loop with require check
    function distributeRewardsBounded(uint256 maxUsers) external {
        require(maxUsers <= users.length && maxUsers <= 100, "Too many users");
        for (uint256 i = 0; i < maxUsers; i++) {
            stakes[users[i]] += 100;
        }
    }

    // TN2: Loop with pagination (safe pattern)
    function distributeRewardsPaginated(uint256 start, uint256 end) external {
        require(start < end && end <= users.length, "Invalid range");
        require(end - start <= 50, "Batch too large"); // Explicit bounds
        for (uint256 i = start; i < end; i++) {
            stakes[users[i]] += 100;
        }
    }

    // TN3: View function with unbounded loop (no state changes)
    function getUserCount() external view returns (uint256) {
        uint256 count = 0;
        for (uint256 i = 0; i < users.length; i++) {
            count++;
        }
        return count;
    }

    // TN4: Internal function (not externally callable)
    function _internalDistribute() internal {
        for (uint256 i = 0; i < users.length; i++) {
            stakes[users[i]] += 100;
        }
    }

    // === EDGE CASES ===

    // EDGE1: Fixed-size loop (not unbounded)
    function processFixedBatch() external {
        for (uint256 i = 0; i < 10; i++) {
            if (i < users.length) {
                stakes[users[i]] += 100;
            }
        }
    }

    // EDGE2: Unbounded loop but gas-light operations
    uint256[] public ids;
    function sumIds() external view returns (uint256) {
        uint256 sum = 0;
        for (uint256 i = 0; i < ids.length; i++) {
            sum += ids[i]; // Simple arithmetic, no storage writes
        }
        return sum;
    }

    // === VARIATIONS ===

    // VAR1: Different loop style - while loop
    function distributeRewardsWhile() external {
        uint256 i = 0;
        while (i < users.length) {
            stakes[users[i]] += 100;
            i++;
        }
    }

    // VAR2: Different collection naming
    address[] public participants;
    function rewardParticipants() external {
        for (uint256 i = 0; i < participants.length; i++) {
            stakes[participants[i]] += 100;
        }
    }

    // VAR3: Loop with break condition (still vulnerable)
    function distributeUntilEmpty() external {
        for (uint256 i = 0; i < users.length; i++) {
            stakes[users[i]] += 100;
            if (address(this).balance == 0) break;
        }
    }
}

// =============================================================================
// SECTION 2: live-002 (Block Gas Limit Exhaustion)
// =============================================================================

interface IToken {
    function transfer(address to, uint256 amount) external returns (bool);
}

contract GasLimitExhaustionTest {
    address[] public recipients;
    uint256[] public amounts;
    mapping(address => bool) public registered;
    IToken public token;

    // === TRUE POSITIVES ===

    // TP1: External calls in loop (classic MEV/DoS vector)
    function batchTransfer() external {
        for (uint256 i = 0; i < recipients.length; i++) {
            (bool success,) = recipients[i].call{value: 0.1 ether}("");
            require(success, "Transfer failed");
        }
    }

    // TP2: Unbounded deletion in loop
    function clearRegistry() external {
        for (uint256 i = 0; i < recipients.length; i++) {
            delete registered[recipients[i]]; // Unbounded deletion
        }
    }

    // TP3: Multiple external calls per iteration

    function batchTokenTransfer() external {
        for (uint256 i = 0; i < recipients.length; i++) {
            token.transfer(recipients[i], 100 ether); // External call
        }
    }

    // TP4: External delegate call in loop (even more dangerous)
    function batchDelegateCalls(bytes[] calldata calls) external {
        for (uint256 i = 0; i < calls.length; i++) {
            (bool success,) = address(this).delegatecall(calls[i]);
            require(success);
        }
    }

    // === TRUE NEGATIVES ===

    // TN1: Bounded loop with external calls
    function batchTransferBounded(uint256 maxRecipients) external {
        require(maxRecipients <= recipients.length && maxRecipients <= 20, "Too many");
        for (uint256 i = 0; i < maxRecipients; i++) {
            (bool success,) = recipients[i].call{value: 0.1 ether}("");
            require(success);
        }
    }

    // TN2: No external calls in loop
    mapping(address => uint256) public balances;
    function batchUpdate() external {
        for (uint256 i = 0; i < recipients.length; i++) {
            balances[recipients[i]] += amounts[i]; // State write but no external call
        }
    }

    // TN3: View function with external calls (no state changes)
    function checkAllBalances() external view returns (uint256) {
        uint256 total = 0;
        for (uint256 i = 0; i < recipients.length; i++) {
            total += recipients[i].balance; // External read but view function
        }
        return total;
    }

    // TN4: Internal function
    function _internalBatchTransfer() internal {
        for (uint256 i = 0; i < recipients.length; i++) {
            (bool success,) = recipients[i].call{value: 0.1 ether}("");
        }
    }

    // === EDGE CASES ===

    // EDGE1: Try-catch around external call (safer but still DoS risk)
    function batchTransferWithTryCatch() external {
        for (uint256 i = 0; i < recipients.length; i++) {
            try IToken(token).transfer(recipients[i], 100 ether) {
                // Success
            } catch {
                // Ignore failure
            }
        }
    }

    // EDGE2: Low-level call with gas limit (partial mitigation)
    function batchTransferLimitedGas() external {
        for (uint256 i = 0; i < recipients.length; i++) {
            (bool success,) = recipients[i].call{value: 0.1 ether, gas: 10000}("");
            // Limited gas, still DoS risk
        }
    }

    // === VARIATIONS ===

    // VAR1: Different external call pattern - address.send()
    function batchSend() external {
        for (uint256 i = 0; i < recipients.length; i++) {
            payable(recipients[i]).send(0.1 ether); // External call variant
        }
    }

    // VAR2: Different external call pattern - address.transfer()
    function batchTransferDirect() external {
        for (uint256 i = 0; i < recipients.length; i++) {
            payable(recipients[i]).transfer(0.1 ether); // External call variant
        }
    }

    receive() external payable {}

    // VAR3: Static call in loop (less dangerous but still gas risk)
    function batchStaticCalls(address target) external view returns (bytes[] memory) {
        bytes[] memory results = new bytes[](recipients.length);
        for (uint256 i = 0; i < recipients.length; i++) {
            (bool success, bytes memory data) = target.staticcall(
                abi.encodeWithSignature("balanceOf(address)", recipients[i])
            );
            results[i] = data;
        }
        return results;
    }
}

// =============================================================================
// SECTION 3: Combined Test (both patterns)
// =============================================================================

contract CombinedDoSTest {
    address[] public users;

    // Matches BOTH live-001 AND live-002
    function atomicBatchProcess() external {
        for (uint256 i = 0; i < users.length; i++) {  // Unbounded
            (bool success,) = users[i].call("");  // External call
            // Triggers both patterns
        }
    }

    // Safe version with pagination and bounds
    function safeBatchProcess(uint256 start, uint256 count) external {
        require(start + count <= users.length, "Out of range");
        require(count <= 50, "Batch too large");

        for (uint256 i = start; i < start + count; i++) {
            (bool success,) = users[i].call("");
        }
    }
}
