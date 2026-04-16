// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ValueMovementStuckEther
 * @dev Demonstrates stuck/locked ether vulnerabilities and withdrawal pattern issues
 *
 * Contracts that accept ether but provide no withdrawal mechanism,
 * or have flawed withdrawal logic that can permanently lock funds.
 *
 * REAL EXAMPLES:
 * - Contracts with receive()/fallback() but no withdrawal
 * - Failed transfers in loops causing DoS
 * - Missing emergency withdrawal functions
 * - SWC-105: Unprotected Ether Withdrawal
 * - SWC-113: DoS with Failed Call
 *
 * REFERENCES:
 * - https://swcregistry.io/docs/SWC-105
 * - https://consensys.io/blog/ethereum-smart-contract-security-recommendations
 */

// VULNERABLE: Accepts ether but no way to withdraw
contract StuckEtherVault {
    mapping(address => uint256) public balances;

    // Accepts ether via deposit
    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    // No withdrawal function - ether is permanently locked!
    // Once deposited, ether cannot be retrieved

    receive() external payable {
        // Also accepts direct sends, which are also stuck forever
    }
}

// SAFE: Provides withdrawal mechanism
contract SafeEtherVault {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    // SAFE: Withdrawal function allows users to retrieve funds
    function withdraw() external {
        uint256 amount = balances[msg.sender];
        require(amount > 0, "No balance");
        balances[msg.sender] = 0;
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
    }

    receive() external payable {
        balances[msg.sender] += msg.value;
    }
}

// VULNERABLE: DoS via failed call in loop (push pattern)
contract VulnerablePaymentSplitter {
    address[] public recipients;
    mapping(address => uint256) public shares;

    function addRecipient(address recipient, uint256 share) external {
        recipients.push(recipient);
        shares[recipient] = share;
    }

    // If any transfer fails, entire function reverts
    // Malicious recipient can use a reverting fallback to DoS all payments
    function distributePayments() external payable {
        uint256 totalShares = getTotalShares();
        for (uint256 i = 0; i < recipients.length; i++) {
            address recipient = recipients[i];
            uint256 amount = (msg.value * shares[recipient]) / totalShares;
            // PROBLEM: If this fails, everyone's payment fails
            payable(recipient).transfer(amount);
        }
    }

    function getTotalShares() public view returns (uint256) {
        uint256 total = 0;
        for (uint256 i = 0; i < recipients.length; i++) {
            total += shares[recipients[i]];
        }
        return total;
    }
}

// Malicious contract that rejects payments
contract MaliciousRecipient {
    // Revert on receiving ether to DoS payment splitter
    receive() external payable {
        revert("I refuse payment");
    }
}

// SAFE: Pull pattern - users withdraw their own shares
contract SafePaymentSplitter {
    address[] public recipients;
    mapping(address => uint256) public shares;
    mapping(address => uint256) public pendingWithdrawals;
    uint256 public totalShares;

    function addRecipient(address recipient, uint256 share) external {
        recipients.push(recipient);
        shares[recipient] = share;
        totalShares += share;
    }

    // SAFE: Credits pending withdrawals instead of pushing payments
    function distributePayments() external payable {
        for (uint256 i = 0; i < recipients.length; i++) {
            address recipient = recipients[i];
            uint256 amount = (msg.value * shares[recipient]) / totalShares;
            pendingWithdrawals[recipient] += amount;
        }
    }

    // SAFE: Pull pattern - each user withdraws independently
    function withdraw() external {
        uint256 amount = pendingWithdrawals[msg.sender];
        require(amount > 0, "No pending withdrawal");
        pendingWithdrawals[msg.sender] = 0;
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
    }
}

// VULNERABLE: No emergency withdrawal for stuck funds
contract VulnerableTreasury {
    address public owner;
    mapping(address => uint256) public allocations;

    constructor() {
        owner = msg.sender;
    }

    receive() external payable {}

    function allocate(address recipient, uint256 amount) external {
        require(msg.sender == owner, "Not owner");
        allocations[recipient] = amount;
    }

    function claim() external {
        uint256 amount = allocations[msg.sender];
        require(amount > 0, "No allocation");
        allocations[msg.sender] = 0;
        payable(msg.sender).transfer(amount);
    }

    // No emergency withdrawal if funds get stuck
    // No way to recover accidentally sent ether
}

// SAFE: Includes emergency withdrawal
contract SafeTreasury {
    address public owner;
    mapping(address => uint256) public allocations;
    uint256 public totalAllocated;

    constructor() {
        owner = msg.sender;
    }

    receive() external payable {}

    function allocate(address recipient, uint256 amount) external {
        require(msg.sender == owner, "Not owner");
        allocations[recipient] = amount;
        totalAllocated += amount;
    }

    function claim() external {
        uint256 amount = allocations[msg.sender];
        require(amount > 0, "No allocation");
        allocations[msg.sender] = 0;
        totalAllocated -= amount;
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
    }

    // SAFE: Emergency withdrawal for unallocated funds
    function emergencyWithdraw(uint256 amount) external {
        require(msg.sender == owner, "Not owner");
        uint256 unallocated = address(this).balance - totalAllocated;
        require(amount <= unallocated, "Insufficient unallocated balance");
        (bool success, ) = payable(owner).call{value: amount}("");
        require(success, "Transfer failed");
    }
}

// VULNERABLE: Transfer with fixed gas (2300) can fail
contract VulnerableGasStipend {
    function sendPayment(address payable recipient, uint256 amount) external {
        // transfer() and send() use fixed 2300 gas
        // This can fail if recipient requires more gas
        recipient.transfer(amount);
    }

    function sendPaymentAlt(address payable recipient, uint256 amount) external {
        // send() also uses 2300 gas and returns bool
        bool success = recipient.send(amount);
        require(success, "Send failed");
    }
}

// SAFE: Use call with value for flexible gas
contract SafeGasFlexible {
    function sendPayment(address payable recipient, uint256 amount) external {
        // SAFE: call{value:} forwards all available gas
        (bool success, ) = recipient.call{value: amount}("");
        require(success, "Transfer failed");
    }
}

// VULNERABLE: Unprotected ether withdrawal
contract UnprotectedWithdrawal {
    function withdraw() external {
        // Anyone can withdraw all ether
        (bool success, ) = msg.sender.call{value: address(this).balance}("");
        require(success, "Transfer failed");
    }

    receive() external payable {}
}

// SAFE: Protected withdrawal with balance tracking
contract ProtectedWithdrawal {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    // SAFE: Users can only withdraw their own balance
    function withdraw() external {
        uint256 amount = balances[msg.sender];
        require(amount > 0, "No balance");
        balances[msg.sender] = 0;
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
    }

    receive() external payable {
        balances[msg.sender] += msg.value;
    }
}
