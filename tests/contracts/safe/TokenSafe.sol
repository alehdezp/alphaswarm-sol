// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title TokenSafe
 * @notice Safe implementations of token handling patterns.
 * @dev These contracts demonstrate proper ERC20/ERC721 token handling.
 */

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function approve(address spender, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
    function allowance(address owner, address spender) external view returns (uint256);
}

/**
 * @title SafeTransferSafe
 * @notice Safe: Check return values of ERC20 transfers
 */
contract SafeTransferSafe {
    // SAFE: Check return value
    function safeTransfer(IERC20 token, address to, uint256 amount) external {
        bool success = token.transfer(to, amount);
        require(success, "Transfer failed");
    }

    // SAFE: Check return value
    function safeTransferFrom(IERC20 token, address from, address to, uint256 amount) external {
        bool success = token.transferFrom(from, to, amount);
        require(success, "TransferFrom failed");
    }
}

/**
 * @title SafeERC20Wrapper
 * @notice Safe: OpenZeppelin-style SafeERC20 wrapper
 */
library SafeERC20 {
    function safeTransfer(IERC20 token, address to, uint256 value) internal {
        _callOptionalReturn(token, abi.encodeWithSelector(token.transfer.selector, to, value));
    }

    function safeTransferFrom(IERC20 token, address from, address to, uint256 value) internal {
        _callOptionalReturn(token, abi.encodeWithSelector(token.transferFrom.selector, from, to, value));
    }

    function safeApprove(IERC20 token, address spender, uint256 value) internal {
        // Reset approval first to prevent race condition
        require(
            (value == 0) || (token.allowance(address(this), spender) == 0),
            "SafeERC20: approve from non-zero to non-zero allowance"
        );
        _callOptionalReturn(token, abi.encodeWithSelector(token.approve.selector, spender, value));
    }

    function safeIncreaseAllowance(IERC20 token, address spender, uint256 value) internal {
        uint256 newAllowance = token.allowance(address(this), spender) + value;
        _callOptionalReturn(token, abi.encodeWithSelector(token.approve.selector, spender, newAllowance));
    }

    function _callOptionalReturn(IERC20 token, bytes memory data) private {
        (bool success, bytes memory returndata) = address(token).call(data);
        require(success, "SafeERC20: low-level call failed");

        if (returndata.length > 0) {
            require(abi.decode(returndata, (bool)), "SafeERC20: ERC20 operation did not succeed");
        }
    }
}

contract SafeERC20WrapperSafe {
    using SafeERC20 for IERC20;

    // SAFE: Using SafeERC20 library
    function deposit(IERC20 token, uint256 amount) external {
        token.safeTransferFrom(msg.sender, address(this), amount);
    }

    function withdraw(IERC20 token, uint256 amount) external {
        token.safeTransfer(msg.sender, amount);
    }
}

/**
 * @title FeeOnTransferSafe
 * @notice Safe: Handle fee-on-transfer tokens correctly
 */
contract FeeOnTransferSafe {
    using SafeERC20 for IERC20;

    mapping(address => uint256) public balances;

    // SAFE: Measure actual received amount for fee-on-transfer tokens
    function depositFeeToken(IERC20 token, uint256 amount) external {
        uint256 balanceBefore = token.balanceOf(address(this));
        token.safeTransferFrom(msg.sender, address(this), amount);
        uint256 balanceAfter = token.balanceOf(address(this));

        // Credit actual received amount
        uint256 actualReceived = balanceAfter - balanceBefore;
        balances[msg.sender] += actualReceived;
    }
}

/**
 * @title ApprovalRaceSafe
 * @notice Safe: Prevent approval race condition
 */
contract ApprovalRaceSafe {
    using SafeERC20 for IERC20;

    // SAFE: Use increaseAllowance/decreaseAllowance pattern
    function increaseSpenderAllowance(IERC20 token, address spender, uint256 addedValue) external {
        token.safeIncreaseAllowance(spender, addedValue);
    }

    // SAFE: Reset to zero first, then set new value
    function safeApprovePattern(IERC20 token, address spender, uint256 newValue) external {
        // First reset to 0
        token.safeApprove(spender, 0);
        // Then set new value
        if (newValue > 0) {
            token.safeApprove(spender, newValue);
        }
    }
}

/**
 * @title TokenCallbackSafe
 * @notice Safe: ERC721/1155 callbacks with reentrancy protection
 */
abstract contract ReentrancyGuard {
    uint256 private constant NOT_ENTERED = 1;
    uint256 private constant ENTERED = 2;
    uint256 private _status = NOT_ENTERED;

    modifier nonReentrant() {
        require(_status != ENTERED, "ReentrancyGuard: reentrant call");
        _status = ENTERED;
        _;
        _status = NOT_ENTERED;
    }
}

contract TokenCallbackSafe is ReentrancyGuard {
    mapping(address => uint256) public nftBalances;

    // SAFE: Protected callback
    function onERC721Received(
        address operator,
        address from,
        uint256 tokenId,
        bytes calldata data
    ) external nonReentrant returns (bytes4) {
        nftBalances[from]++;
        return this.onERC721Received.selector;
    }

    // SAFE: Protected callback
    function onERC1155Received(
        address operator,
        address from,
        uint256 id,
        uint256 value,
        bytes calldata data
    ) external nonReentrant returns (bytes4) {
        nftBalances[from] += value;
        return this.onERC1155Received.selector;
    }
}

/**
 * @title InfiniteApprovalSafe
 * @notice Safe: Limited approvals instead of infinite
 */
contract InfiniteApprovalSafe {
    using SafeERC20 for IERC20;

    // SAFE: Only approve exact amount needed
    function approveExact(IERC20 token, address spender, uint256 exactAmount) external {
        // Reset first
        token.safeApprove(spender, 0);
        // Approve exact amount
        token.safeApprove(spender, exactAmount);
    }

    // SAFE: Reset approval after use
    function useAndReset(IERC20 token, address spender, uint256 amount) external {
        token.safeApprove(spender, amount);
        // ... use the approval ...
        // Reset after use
        token.safeApprove(spender, 0);
    }
}

/**
 * @title ShareInflationSafe
 * @notice Safe: Vault share inflation attack protection (ERC-4626)
 */
contract ShareInflationSafe {
    IERC20 public asset;
    uint256 public totalShares;
    uint256 public totalAssets;
    mapping(address => uint256) public shares;

    uint256 public constant MINIMUM_SHARES = 1000; // Minimum share lock

    constructor(IERC20 _asset) {
        asset = _asset;
    }

    // SAFE: Dead shares pattern to prevent inflation attack
    function deposit(uint256 assets) external returns (uint256) {
        uint256 sharesToMint;

        if (totalShares == 0) {
            // First depositor: mint extra shares to dead address
            sharesToMint = assets;
            // Lock minimum shares to prevent inflation
            shares[address(0xdead)] = MINIMUM_SHARES;
            totalShares = MINIMUM_SHARES;
            sharesToMint = assets - MINIMUM_SHARES;
        } else {
            sharesToMint = (assets * totalShares) / totalAssets;
        }

        require(sharesToMint > 0, "Zero shares");

        shares[msg.sender] += sharesToMint;
        totalShares += sharesToMint;
        totalAssets += assets;

        // Transfer assets
        bool success = asset.transferFrom(msg.sender, address(this), assets);
        require(success, "Transfer failed");

        return sharesToMint;
    }
}

/**
 * @title BalanceAccountingSafe
 * @notice Safe: Track balances internally, not via balanceOf
 */
contract BalanceAccountingSafe {
    using SafeERC20 for IERC20;

    IERC20 public token;
    uint256 public totalDeposited;
    mapping(address => uint256) public userDeposits;

    constructor(IERC20 _token) {
        token = _token;
    }

    // SAFE: Use internal accounting, not balanceOf
    function deposit(uint256 amount) external {
        token.safeTransferFrom(msg.sender, address(this), amount);
        userDeposits[msg.sender] += amount;
        totalDeposited += amount;
    }

    // SAFE: Calculate share based on internal accounting
    function getShare(address user) external view returns (uint256) {
        if (totalDeposited == 0) return 0;
        return (userDeposits[user] * 1e18) / totalDeposited;
    }

    function withdraw(uint256 amount) external {
        require(userDeposits[msg.sender] >= amount, "Insufficient balance");
        userDeposits[msg.sender] -= amount;
        totalDeposited -= amount;
        token.safeTransfer(msg.sender, amount);
    }
}
