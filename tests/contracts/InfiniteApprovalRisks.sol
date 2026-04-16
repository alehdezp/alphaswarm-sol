// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title InfiniteApprovalRisks
 * @dev Demonstrates risks of infinite/max allowance approvals
 *
 * Approving type(uint256).max allows spender to drain
 * all tokens if they are compromised or malicious. Common in DeFi
 * for gas optimization but creates permanent risk.
 *
 * CWE-285: Improper Authorization
 *
 * REAL EXAMPLES:
 * - Numerous DeFi exploits where approved contracts were compromised
 * - Phishing attacks exploiting unlimited approvals
 */

interface IERC20Approval {
    function approve(address spender, uint256 amount) external returns (bool);
    function allowance(address owner, address spender) external view returns (uint256);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

// VULNERABLE: Infinite approval pattern
contract VulnerableInfiniteApproval {
    IERC20Approval public token;
    address public dex;

    constructor(address _token, address _dex) {
        token = IERC20Approval(_token);
        dex = _dex;

        // PROBLEM: Infinite approval to DEX
        // If DEX has bug or gets hacked, all user tokens at risk forever
        token.approve(dex, type(uint256).max);
    }

    function trade(uint256 amount) public {
        // Uses the infinite approval
        // No way to reduce risk after approval
    }

    // PROBLEM: No way to revoke approval
    // User's tokens are permanently at risk
}

// SAFE: Exact approval per transaction
contract SafeExactApproval {
    IERC20Approval public token;
    address public dex;

    constructor(address _token, address _dex) {
        token = IERC20Approval(_token);
        dex = _dex;
        // No approval in constructor
    }

    function trade(uint256 amount) public {
        // Approve exact amount needed
        token.approve(dex, amount);

        // Perform trade

        // Optionally revoke remaining approval
        uint256 remaining = token.allowance(address(this), dex);
        if (remaining > 0) {
            token.approve(dex, 0);
        }
    }
}

// VULNERABLE: User approves without validation
contract VulnerableUserApproval {
    IERC20Approval public token;

    function approveContract(address spender, uint256 amount) public {
        // PROBLEM: No validation of spender
        // User could be tricked into approving malicious contract
        // No checks for infinite approval
        token.approve(spender, amount);
    }
}

// SAFE: Approval with validation and limits
contract SafeUserApproval {
    IERC20Approval public token;
    mapping(address => bool) public trustedSpenders;
    uint256 public constant MAX_APPROVAL = 1000000 * 1e18;

    function addTrustedSpender(address spender) public {
        // Only owner or governance
        trustedSpenders[spender] = true;
    }

    function approveContract(address spender, uint256 amount) public {
        // Validate spender is trusted
        require(trustedSpenders[spender], "Untrusted spender");

        // Warn if infinite approval attempted
        require(amount <= MAX_APPROVAL, "Approval too high - use smaller amount");

        token.approve(spender, amount);
    }

    function revokeApproval(address spender) public {
        token.approve(spender, 0);
    }
}

// VULNERABLE: Compound approval vulnerability
contract VulnerableCompoundApproval {
    IERC20Approval public tokenA;
    IERC20Approval public tokenB;
    address public router;

    constructor(address _tokenA, address _tokenB, address _router) {
        tokenA = IERC20Approval(_tokenA);
        tokenB = IERC20Approval(_tokenB);
        router = _router;

        // PROBLEM: Multiple infinite approvals
        // If router is compromised, all tokens at risk
        tokenA.approve(router, type(uint256).max);
        tokenB.approve(router, type(uint256).max);
    }

    // Users can't reduce their exposure without upgrading contract
}

// SAFE: Managed approval with revocation
contract SafeManagedApproval {
    IERC20Approval public tokenA;
    IERC20Approval public tokenB;
    address public router;
    bool public approvalsActive;

    constructor(address _tokenA, address _tokenB, address _router) {
        tokenA = IERC20Approval(_tokenA);
        tokenB = IERC20Approval(_tokenB);
        router = _router;
        approvalsActive = false;
    }

    function enableApprovals(uint256 amountA, uint256 amountB) public {
        require(!approvalsActive, "Already active");

        // Use reasonable limits, not infinite
        tokenA.approve(router, amountA);
        tokenB.approve(router, amountB);
        approvalsActive = true;
    }

    function revokeApprovals() public {
        tokenA.approve(router, 0);
        tokenB.approve(router, 0);
        approvalsActive = false;
    }

    // Emergency: Change router and revoke old approvals
    function changeRouter(address newRouter) public {
        // Revoke old approvals
        revokeApprovals();

        // Update router
        router = newRouter;
    }
}

// VULNERABLE: Approval without return value check
contract VulnerableApprovalReturn {
    function unsafeApprove(address token, address spender, uint256 amount) public {
        // PROBLEM: Some tokens (USDT) don't return bool
        // This assignment will revert for those tokens
        bool success = IERC20Approval(token).approve(spender, amount);
        require(success, "Approval failed");
    }
}

// SAFE: Low-level call for approval
contract SafeApprovalReturn {
    function safeApprove(address token, address spender, uint256 amount) public {
        // Use low-level call to handle non-standard tokens
        (bool success, bytes memory data) = token.call(
            abi.encodeWithSelector(IERC20Approval.approve.selector, spender, amount)
        );

        require(success, "Approval call failed");

        // If data returned, verify it's true
        if (data.length > 0) {
            require(abi.decode(data, (bool)), "Approval returned false");
        }

        // Verify allowance was actually set
        require(
            IERC20Approval(token).allowance(address(this), spender) >= amount,
            "Allowance not set correctly"
        );
    }
}

// VULNERABLE: Approval race condition
contract VulnerableApprovalRace {
    IERC20Approval public token;

    function updateApproval(address spender, uint256 newAmount) public {
        // PROBLEM: Spender can front-run this transaction
        // Spend old allowance, then get new allowance
        // Classic ERC-20 approval race condition
        token.approve(spender, newAmount);
    }
}

// SAFE: Increase/decrease allowance pattern
contract SafeApprovalRace {
    IERC20Approval public token;

    function updateApproval(address spender, uint256 newAmount) public {
        // Step 1: Always reset to 0 first
        token.approve(spender, 0);

        // Step 2: Set new amount
        // Even if front-run, can't exploit both transactions
        token.approve(spender, newAmount);
    }

    // Better: Use increaseAllowance/decreaseAllowance if available
    function increaseApproval(address spender, uint256 addedValue) public {
        uint256 currentAllowance = token.allowance(address(this), spender);
        token.approve(spender, currentAllowance + addedValue);
    }

    function decreaseApproval(address spender, uint256 subtractedValue) public {
        uint256 currentAllowance = token.allowance(address(this), spender);
        require(currentAllowance >= subtractedValue, "Decrease below zero");
        token.approve(spender, currentAllowance - subtractedValue);
    }
}

// VULNERABLE: Approval to proxy without validation
contract VulnerableProxyApproval {
    function approveProxy(address token, address proxy, uint256 amount) public {
        // PROBLEM: No validation that proxy is upgradeable
        // If proxy logic changes, approval becomes dangerous
        IERC20Approval(token).approve(proxy, amount);
    }
}

// SAFE: Proxy approval with validation
contract SafeProxyApproval {
    mapping(address => bool) public verifiedProxies;

    function verifyProxy(address proxy) public {
        // Check proxy implementation is safe
        // Check proxy is not upgradeable or has timelock
        verifiedProxies[proxy] = true;
    }

    function approveProxy(address token, address proxy, uint256 amount) public {
        require(verifiedProxies[proxy], "Proxy not verified");

        // Use limited approval, not infinite
        require(amount < type(uint256).max / 2, "Approval too high");

        IERC20Approval(token).approve(proxy, amount);
    }
}

// Example of phishing attack exploiting approvals
contract PhishingAttack {
    IERC20Approval public token;

    constructor(address _token) {
        token = IERC20Approval(_token);
    }

    // Attacker tricks user into calling this with their token
    function claimReward() public {
        // User thinks they're claiming a reward
        // But actually approving attacker for infinite amount!
        token.approve(address(this), type(uint256).max);
    }

    // Attacker drains approved tokens
    function drain(address victim) public {
        uint256 amount = token.balanceOf(victim);
        token.transferFrom(victim, address(this), amount);
    }
}

// VULNERABLE: Batch approval without individual checks
contract VulnerableBatchApproval {
    function batchApprove(
        address[] memory tokens,
        address[] memory spenders,
        uint256[] memory amounts
    ) public {
        // PROBLEM: No validation of parameters
        // One malicious entry can compromise everything
        for (uint i = 0; i < tokens.length; i++) {
            IERC20Approval(tokens[i]).approve(spenders[i], amounts[i]);
        }
    }
}

// SAFE: Batch approval with validation
contract SafeBatchApproval {
    mapping(address => bool) public trustedTokens;
    mapping(address => bool) public trustedSpenders;
    uint256 public constant MAX_BATCH_SIZE = 10;
    uint256 public constant MAX_APPROVAL = 1000000 * 1e18;

    function batchApprove(
        address[] memory tokens,
        address[] memory spenders,
        uint256[] memory amounts
    ) public {
        require(tokens.length == spenders.length, "Length mismatch");
        require(tokens.length == amounts.length, "Length mismatch");
        require(tokens.length <= MAX_BATCH_SIZE, "Batch too large");

        for (uint i = 0; i < tokens.length; i++) {
            require(trustedTokens[tokens[i]], "Untrusted token");
            require(trustedSpenders[spenders[i]], "Untrusted spender");
            require(amounts[i] <= MAX_APPROVAL, "Amount too high");

            IERC20Approval(tokens[i]).approve(spenders[i], amounts[i]);
        }
    }
}
