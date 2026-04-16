// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ValueMovementForcedEther
 * @dev Demonstrates selfdestruct forced ether injection vulnerabilities
 *
 * Contracts that rely on address(this).balance for critical logic
 * can be manipulated via selfdestruct, which forcibly sends ether without calling
 * any functions (not even fallback/receive).
 *
 * REAL EXAMPLES:
 * - Game contracts relying on balance checks
 * - Escrow contracts with balance-based logic
 * - CWE-1339: Insufficient Precision or Accuracy of a Real Number
 * - SWC-132: Unexpected Ether balance
 *
 * REFERENCES:
 * - https://swcregistry.io/docs/SWC-132
 * - https://immunebytes.com/blog/self-destruct-exploit-forced-ether-injection-in-solidity-contracts/
 */

// VULNERABLE: Game contract relying on exact balance
contract VulnerableBalanceGame {
    uint256 public constant TARGET_BALANCE = 7 ether;
    bool public gameWon = false;

    function deposit() external payable {
        require(!gameWon, "Game already won");
        require(msg.value <= 1 ether, "Max deposit 1 ether");

        // Relies on exact balance check
        // Attacker can use selfdestruct to force ether and break this logic
        if (address(this).balance >= TARGET_BALANCE) {
            gameWon = true;
        }
    }

    function withdraw() external {
        require(gameWon, "Game not won yet");
        payable(msg.sender).transfer(address(this).balance);
    }
}

// ATTACKER: Forces ether via selfdestruct
contract ForcedEtherAttacker {
    constructor() payable {}

    function attack(address target) external {
        // Selfdestruct forces ether to target without calling any function
        selfdestruct(payable(target));
    }
}

// SAFE: Uses internal accounting instead of balance
contract SafeBalanceGame {
    uint256 public constant TARGET_BALANCE = 7 ether;
    uint256 public internalBalance; // Tracks deposits separately
    bool public gameWon = false;

    function deposit() external payable {
        require(!gameWon, "Game already won");
        require(msg.value <= 1 ether, "Max deposit 1 ether");

        // SAFE: Uses internal accounting that cannot be manipulated by selfdestruct
        internalBalance += msg.value;
        if (internalBalance >= TARGET_BALANCE) {
            gameWon = true;
        }
    }

    function withdraw() external {
        require(gameWon, "Game not won yet");
        uint256 amount = internalBalance;
        internalBalance = 0;
        payable(msg.sender).transfer(amount);
    }

    // Allow contract to receive forced ether but don't count it
    receive() external payable {
        // Forced ether is accepted but not counted in game logic
    }
}

// VULNERABLE: Escrow relying on balance equality
contract VulnerableEscrow {
    mapping(address => uint256) public deposits;
    uint256 public totalDeposits;

    function deposit() external payable {
        deposits[msg.sender] += msg.value;
        totalDeposits += msg.value;
    }

    function withdraw() external {
        uint256 amount = deposits[msg.sender];
        require(amount > 0, "No deposit");

        // Relies on balance matching internal accounting
        // If someone selfdestructs into this contract, this check fails
        require(address(this).balance == totalDeposits, "Balance mismatch");

        deposits[msg.sender] = 0;
        totalDeposits -= amount;
        payable(msg.sender).transfer(amount);
    }
}

// SAFE: Handles excess balance gracefully
contract SafeEscrow {
    mapping(address => uint256) public deposits;
    uint256 public totalDeposits;

    function deposit() external payable {
        deposits[msg.sender] += msg.value;
        totalDeposits += msg.value;
    }

    function withdraw() external {
        uint256 amount = deposits[msg.sender];
        require(amount > 0, "No deposit");

        // SAFE: Check we have enough, not exact match
        require(address(this).balance >= totalDeposits, "Insufficient balance");

        deposits[msg.sender] = 0;
        totalDeposits -= amount;
        payable(msg.sender).transfer(amount);
    }

    // Explicitly handle unexpected ether
    receive() external payable {
        // Forced/unexpected ether does not affect deposit accounting
    }
}

// VULNERABLE: Payable selfdestruct without access control
contract UnprotectedSelfdestruct {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    // Anyone can destroy the contract
    function destroy(address payable recipient) external {
        selfdestruct(recipient);
    }
}

// SAFE: Selfdestruct with access control
contract ProtectedSelfdestruct {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    // SAFE: Only owner can destroy
    function destroy(address payable recipient) external onlyOwner {
        selfdestruct(recipient);
    }
}
