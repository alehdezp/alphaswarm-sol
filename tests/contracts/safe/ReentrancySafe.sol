// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title ReentrancySafe
 * @notice Safe implementations of common reentrancy patterns.
 * @dev These contracts demonstrate proper protections against reentrancy.
 */

// OpenZeppelin-style reentrancy guard
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

/**
 * @title ReentrancySafeCEI
 * @notice Safe: Checks-Effects-Interactions pattern
 */
contract ReentrancySafeCEI {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    // SAFE: State updated before external call (CEI pattern)
    function withdrawCEI(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");

        // Effects (state change first)
        balances[msg.sender] -= amount;

        // Interactions (external call last)
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
    }
}

/**
 * @title ReentrancySafeGuard
 * @notice Safe: Using nonReentrant modifier
 */
contract ReentrancySafeGuard is ReentrancyGuard {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    // SAFE: Protected by reentrancy guard
    function withdrawWithGuard(uint256 amount) external nonReentrant {
        require(balances[msg.sender] >= amount, "Insufficient balance");

        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");

        // State updated after call but protected by guard
        balances[msg.sender] -= amount;
    }
}

/**
 * @title ReentrancySafePullPayment
 * @notice Safe: Pull payment pattern - users withdraw themselves
 */
contract ReentrancySafePullPayment {
    mapping(address => uint256) public pendingWithdrawals;

    function addPayment(address recipient) external payable {
        pendingWithdrawals[recipient] += msg.value;
    }

    // SAFE: Pull pattern - user withdraws own funds, CEI pattern
    function pullWithdraw() external {
        uint256 amount = pendingWithdrawals[msg.sender];
        require(amount > 0, "Nothing to withdraw");

        // Effects first
        pendingWithdrawals[msg.sender] = 0;

        // Interactions last
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
    }
}

/**
 * @title ReentrancySafeTransfer
 * @notice Safe: Using transfer() with 2300 gas stipend
 */
contract ReentrancySafeTransfer {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    // SAFE: transfer() limits gas to 2300, preventing reentrancy
    // Note: Not recommended due to gas cost changes, but demonstrates the pattern
    function withdrawTransfer(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        balances[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
    }
}

/**
 * @title CrossFunctionSafe
 * @notice Safe: Cross-function reentrancy with mutex
 */
contract CrossFunctionSafe is ReentrancyGuard {
    mapping(address => uint256) public balances;
    mapping(address => bool) public authorized;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    // SAFE: Both functions protected by same mutex
    function withdraw(uint256 amount) external nonReentrant {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        balances[msg.sender] -= amount;
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
    }

    function transfer(address to, uint256 amount) external nonReentrant {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        balances[msg.sender] -= amount;
        balances[to] += amount;
    }
}

/**
 * @title ReadOnlySafe
 * @notice Safe: Read-only reentrancy protection
 */
contract ReadOnlySafe is ReentrancyGuard {
    uint256 public totalDeposits;
    mapping(address => uint256) public balances;

    function deposit() external payable nonReentrant {
        balances[msg.sender] += msg.value;
        totalDeposits += msg.value;
    }

    function withdraw(uint256 amount) external nonReentrant {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        balances[msg.sender] -= amount;
        totalDeposits -= amount;
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
    }

    // SAFE: View function but state is consistent due to reentrancy guard on mutators
    function getShareValue(address user) external view returns (uint256) {
        if (totalDeposits == 0) return 0;
        return (balances[user] * 1e18) / totalDeposits;
    }
}
