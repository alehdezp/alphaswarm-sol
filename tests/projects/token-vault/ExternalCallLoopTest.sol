// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title ExternalCallLoopTest
 * @notice Comprehensive test contract for dos-002: External Call in Loop
 *
 * Tests cover:
 * - True Positives: Functions with external calls in loops (token transfers, ETH transfers, contract calls)
 * - True Negatives: Safe patterns (pull-over-push, try-catch, low-level call with success check)
 * - Edge Cases: Batch operations with pagination, view functions with external calls
 * - Variation Testing: Different loop types, different external call patterns
 */

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

interface IRewardContract {
    function notifyReward(uint256 amount) external;
    function distributeReward() external;
}

// =============================================================================
// TRUE POSITIVES - Functions with external calls in loops (SHOULD BE FLAGGED)
// =============================================================================

contract VulnerableAirdrop {
    address[] public recipients;
    IERC20 public token;

    // TP1: Standard airdrop with token.transfer in loop
    function airdropTokens(uint256 amount) external {
        // VULNERABLE: One reverting recipient bricks entire function
        for (uint256 i = 0; i < recipients.length; i++) {
            token.transfer(recipients[i], amount);  // dos-002 should flag
        }
    }

    // TP2: Batch transfer with transferFrom in loop
    function batchTransfer(address[] calldata users, uint256[] calldata amounts) external {
        // VULNERABLE: One failing transfer bricks entire batch
        for (uint256 i = 0; i < users.length; i++) {
            token.transferFrom(msg.sender, users[i], amounts[i]);  // dos-002 should flag
        }
    }

    // TP3: ETH refund loop (Akutars pattern)
    mapping(address => uint256) public contributions;
    address[] public contributors;

    function refundAll() external {
        // VULNERABLE: One rejecting contract bricks all refunds ($34M Akutars incident)
        for (uint256 i = 0; i < contributors.length; i++) {
            payable(contributors[i]).transfer(contributions[contributors[i]]);  // dos-002 should flag
        }
    }

    // TP4: External contract calls in loop
    address[] public rewardContracts;

    function notifyAllRewards(uint256 amount) external {
        // VULNERABLE: One gas-consuming contract causes DoS
        for (uint256 i = 0; i < rewardContracts.length; i++) {
            IRewardContract(rewardContracts[i]).notifyReward(amount);  // dos-002 should flag
        }
    }

    // TP5: While loop with external call
    function processUntilEmpty() external {
        // VULNERABLE: Unbounded while loop with external calls
        while (recipients.length > 0) {
            address recipient = recipients[recipients.length - 1];
            recipients.pop();
            token.transfer(recipient, 100 ether);  // dos-002 should flag
        }
    }

    // TP6: Do-while loop with external call
    uint256 public currentIndex;

    function processInDoWhile() external {
        // VULNERABLE: Do-while loop with external call
        do {
            token.transfer(recipients[currentIndex], 100 ether);  // dos-002 should flag
            currentIndex++;
        } while (currentIndex < recipients.length);
    }

    // TP7: Nested loop with external call
    address[][] public recipientGroups;

    function airdropNested(uint256 amount) external {
        // VULNERABLE: Nested loops with external calls (severity increased)
        for (uint256 i = 0; i < recipientGroups.length; i++) {
            for (uint256 j = 0; j < recipientGroups[i].length; j++) {
                token.transfer(recipientGroups[i][j], amount);  // dos-002 should flag
            }
        }
    }

    // TP8: Loop with low-level call WITHOUT success check
    function sendETHLoop(address[] calldata targets, uint256 amount) external {
        // VULNERABLE: Low-level call without checking return value
        for (uint256 i = 0; i < targets.length; i++) {
            targets[i].call{value: amount}("");  // dos-002 should flag (no success check)
        }
    }

    // TP9: Loop with multiple external calls
    function distributeWithCallback(address[] calldata users, uint256 amount) external {
        // VULNERABLE: Multiple external calls per iteration
        for (uint256 i = 0; i < users.length; i++) {
            token.transfer(users[i], amount);  // dos-002 should flag
            IRewardContract(users[i]).notifyReward(amount);  // dos-002 should flag
        }
    }

    // TP10: Variation - Different naming convention
    function removeFundsFromAll(address[] calldata accounts) external {
        // VULNERABLE: Different naming but same pattern
        for (uint256 i = 0; i < accounts.length; i++) {
            token.transfer(accounts[i], 1000 ether);  // dos-002 should flag
        }
    }
}

// =============================================================================
// TRUE NEGATIVES - Safe patterns (SHOULD NOT BE FLAGGED)
// =============================================================================

contract SafeAirdrop {
    mapping(address => uint256) public claimable;
    IERC20 public token;

    // TN1: Pull-over-push pattern (SAFE)
    function setClaimable(address[] calldata users, uint256[] calldata amounts) external {
        // SAFE: No external calls in loop, just state writes
        for (uint256 i = 0; i < users.length; i++) {
            claimable[users[i]] = amounts[i];  // dos-002 should NOT flag
        }
    }

    // TN2: User pulls their own tokens (SAFE)
    function claim() external {
        // SAFE: Single external call outside loop
        uint256 amount = claimable[msg.sender];
        require(amount > 0, "Nothing to claim");
        claimable[msg.sender] = 0;
        token.transfer(msg.sender, amount);  // dos-002 should NOT flag (no loop)
    }

    // TN3: Try-catch handles failures gracefully (SAFE)
    address[] public recipients;

    function airdropWithTryCatch(uint256 amount) external {
        // SAFE: Try-catch allows function to continue despite failures
        for (uint256 i = 0; i < recipients.length; i++) {
            try token.transfer(recipients[i], amount) {
                // Success
            } catch {
                // Continue on failure
            }
        }
        // dos-002 should NOT flag (has_try_catch: true)
    }

    // TN4: Low-level call with success check (SAFE)
    mapping(address => uint256) public failedRefunds;
    address[] public contributors;
    mapping(address => uint256) public contributions;

    function refundWithSuccessCheck() external {
        // SAFE: Low-level call with success check and failure handling
        for (uint256 i = 0; i < contributors.length; i++) {
            (bool success, ) = contributors[i].call{value: contributions[contributors[i]]}("");
            if (!success) {
                failedRefunds[contributors[i]] = contributions[contributors[i]];
            }
        }
        // dos-002 should NOT flag (checks_low_level_call_success: true)
    }

    // TN5: View function with external calls (SAFE - read-only)
    function getBalances(address[] calldata accounts) external view returns (uint256[] memory) {
        // SAFE: View function, no state mutation risk
        uint256[] memory balances = new uint256[](accounts.length);
        for (uint256 i = 0; i < accounts.length; i++) {
            balances[i] = token.balanceOf(accounts[i]);  // dos-002 should NOT flag (view)
        }
        return balances;
    }

    // TN6: Pure function (SAFE - no external calls possible)
    function calculateAmounts(uint256[] calldata inputs, uint256 multiplier) external pure returns (uint256[] memory) {
        // SAFE: Pure function, no external calls
        uint256[] memory results = new uint256[](inputs.length);
        for (uint256 i = 0; i < inputs.length; i++) {
            results[i] = inputs[i] * multiplier;  // dos-002 should NOT flag (pure)
        }
        return results;
    }

    // TN7: Pagination limits iterations (SAFE)
    function distributeBatch(uint256 amount, uint256 start, uint256 end) external {
        // SAFE: Pagination with bounded iterations and try-catch
        require(end <= recipients.length, "Invalid range");
        require(end - start <= 50, "Batch too large");

        for (uint256 i = start; i < end; i++) {
            try token.transfer(recipients[i], amount) {
                // Success
            } catch {
                // Continue on failure
            }
        }
        // dos-002 should NOT flag (has_try_catch: true)
    }

    // TN8: Internal function (SAFE - not callable by users)
    function _distributeInternal(address[] memory users, uint256 amount) internal {
        // SAFE: Internal function, not entry point
        for (uint256 i = 0; i < users.length; i++) {
            token.transfer(users[i], amount);
        }
        // dos-002 should NOT flag (visibility: internal)
    }

    // TN9: Private function (SAFE - not callable by users)
    function _distributePrivate(address[] memory users, uint256 amount) private {
        // SAFE: Private function, not entry point
        for (uint256 i = 0; i < users.length; i++) {
            token.transfer(users[i], amount);
        }
        // dos-002 should NOT flag (visibility: private)
    }
}

// =============================================================================
// EDGE CASES - Boundary conditions and special scenarios
// =============================================================================

contract EdgeCaseAirdrop {
    IERC20 public token;
    address[] public recipients;

    // EDGE1: External call after loop completes (NOT in loop body)
    function distributeAfterLoop(uint256 amount) external {
        // Edge: External call AFTER loop, not inside
        uint256 totalAmount = 0;
        for (uint256 i = 0; i < recipients.length; i++) {
            totalAmount += amount;
        }
        // External call outside loop
        token.transfer(msg.sender, totalAmount);  // dos-002 should NOT flag
    }

    // EDGE2: Loop with external call in conditional branch
    mapping(address => bool) public eligibleForBonus;

    function distributeConditional(uint256 amount) external {
        // Edge: External call only for some recipients
        for (uint256 i = 0; i < recipients.length; i++) {
            if (eligibleForBonus[recipients[i]]) {
                token.transfer(recipients[i], amount * 2);  // dos-002 SHOULD flag
            }
        }
    }

    // EDGE3: Empty array (zero iterations)
    function distributeEmpty(uint256 amount) external {
        // Edge: Array could be empty, but pattern still vulnerable if populated
        address[] memory emptyArray = new address[](0);
        for (uint256 i = 0; i < emptyArray.length; i++) {
            token.transfer(emptyArray[i], amount);  // dos-002 SHOULD flag
        }
    }

    // EDGE4: Single iteration loop (still vulnerable to revert)
    function distributeSingle(address recipient, uint256 amount) external {
        // Edge: Only one iteration, but still vulnerable if recipient reverts
        address[] memory singleRecipient = new address[](1);
        singleRecipient[0] = recipient;
        for (uint256 i = 0; i < singleRecipient.length; i++) {
            token.transfer(singleRecipient[i], amount);  // dos-002 SHOULD flag
        }
    }

    // EDGE5: View function that could revert from external view calls
    function checkAllBalances(address[] calldata accounts) external view returns (bool) {
        // Edge: View function with external view calls in loop
        // Not state-mutating but could DoS if one balanceOf reverts
        for (uint256 i = 0; i < accounts.length; i++) {
            if (token.balanceOf(accounts[i]) < 100 ether) {
                return false;  // dos-002 should NOT flag (view)
            }
        }
        return true;
    }
}

// =============================================================================
// VARIATION TESTING - Different implementations of the same vulnerability
// =============================================================================

contract VariationAirdrop {
    IERC20 public token;

    // VAR1: Reverse iteration
    function airdropReverse(address[] calldata users, uint256 amount) external {
        // VULNERABLE: Reverse loop iteration
        for (uint256 i = users.length; i > 0; i--) {
            token.transfer(users[i - 1], amount);  // dos-002 should flag
        }
    }

    // VAR2: Iterator increment at start
    function airdropPreIncrement(address[] calldata users, uint256 amount) external {
        // VULNERABLE: Pre-increment
        for (uint256 i = 0; i < users.length; ++i) {
            token.transfer(users[i], amount);  // dos-002 should flag
        }
    }

    // VAR3: Loop without increment (manual)
    function airdropManualIncrement(address[] calldata users, uint256 amount) external {
        // VULNERABLE: Manual increment
        for (uint256 i = 0; i < users.length; ) {
            token.transfer(users[i], amount);  // dos-002 should flag
            unchecked { i++; }
        }
    }

    // VAR4: External call via interface cast
    IRewardContract[] public contracts;

    function notifyRewardsWithCast(uint256 amount) external {
        // VULNERABLE: External call via interface
        for (uint256 i = 0; i < contracts.length; i++) {
            IRewardContract(address(contracts[i])).distributeReward();  // dos-002 should flag
        }
    }

    // VAR5: Token send via send() instead of transfer()
    address[] public ethRecipients;

    function sendETHLoop(uint256 amount) external {
        // VULNERABLE: ETH send in loop
        for (uint256 i = 0; i < ethRecipients.length; i++) {
            payable(ethRecipients[i]).send(amount);  // dos-002 should flag
        }
    }

    // VAR6: Token call via call selector
    address[] public tokenRecipients;

    function transferViaCall(uint256 amount) external {
        // VULNERABLE: Low-level call without success check
        for (uint256 i = 0; i < tokenRecipients.length; i++) {
            address(token).call(
                abi.encodeWithSignature("transfer(address,uint256)", tokenRecipients[i], amount)
            );  // dos-002 should flag
        }
    }

    // VAR7: Different array access pattern
    mapping(uint256 => address) public recipientById;
    uint256 public recipientCount;

    function distributeById(uint256 amount) external {
        // VULNERABLE: Mapping iteration
        for (uint256 i = 0; i < recipientCount; i++) {
            token.transfer(recipientById[i], amount);  // dos-002 should flag
        }
    }

    // VAR8: External call in nested function within loop
    function distributeWithHelper(address[] calldata users, uint256 amount) external {
        // VULNERABLE: Helper function has external call
        for (uint256 i = 0; i < users.length; i++) {
            _sendToUser(users[i], amount);  // dos-002 might flag if analyzer follows calls
        }
    }

    function _sendToUser(address user, uint256 amount) private {
        token.transfer(user, amount);
    }
}

// =============================================================================
// MIXED SCENARIOS - Complex real-world patterns
// =============================================================================

contract ComplexAirdrop {
    IERC20 public token;
    address[] public recipients;
    mapping(address => uint256) public claimable;

    // MIXED1: Loop with both state writes AND external calls
    function setupAndAirdrop(address[] calldata users, uint256 amount) external {
        // VULNERABLE: External calls in loop even with state writes
        for (uint256 i = 0; i < users.length; i++) {
            claimable[users[i]] = amount;  // State write
            token.transfer(users[i], amount);  // dos-002 SHOULD flag
        }
    }

    // MIXED2: Multiple loops, one safe, one vulnerable
    function mixedDistribution(uint256 amount) external {
        // First loop: SAFE (no external calls)
        for (uint256 i = 0; i < recipients.length; i++) {
            claimable[recipients[i]] = amount;
        }

        // Second loop: VULNERABLE
        for (uint256 i = 0; i < recipients.length; i++) {
            token.transfer(recipients[i], amount);  // dos-002 SHOULD flag
        }
    }

    // MIXED3: Try-catch only for part of external calls
    IRewardContract[] public rewardContracts;

    function partialTryCatch(uint256 amount) external {
        // VULNERABLE: Try-catch wraps one call but not the other
        for (uint256 i = 0; i < recipients.length; i++) {
            try rewardContracts[i].notifyReward(amount) {
                // Success
            } catch {
                // Handled
            }
            // This one is NOT wrapped
            token.transfer(recipients[i], amount);  // dos-002 SHOULD flag
        }
    }
}
