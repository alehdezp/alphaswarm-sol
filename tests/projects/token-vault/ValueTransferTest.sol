// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title ValueTransferTest
 * @notice Test contract for vm-002-unprotected-transfer pattern
 * @dev Tests semantic operations TRANSFERS_VALUE_OUT and WRITES_USER_BALANCE
 */
contract ValueTransferTest {
    address public owner;
    mapping(address => uint256) public balances;
    mapping(address => uint256) public shares;
    mapping(address => uint256) public deposits;
    mapping(address => uint256) public userFunds;
    bool private locked;

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    modifier nonReentrant() {
        require(!locked, "Reentrant call");
        locked = true;
        _;
        locked = false;
    }

    // =========================================================================
    // TRUE POSITIVES - Should be flagged by vm-002
    // =========================================================================

    /// @dev TP1: Unprotected ETH transfer (standard naming)
    /// TRANSFERS_VALUE_OUT operation without access control
    function withdraw(uint256 amount) external {
        payable(msg.sender).transfer(amount);
    }

    /// @dev TP2: Unprotected balance write (WRITES_USER_BALANCE)
    function setBalance(address user, uint256 amount) external {
        balances[user] = amount;  // vm-002 should flag this
    }

    /// @dev TP3: Alternative naming - "extract" instead of "withdraw"
    /// Tests name-agnostic detection
    function extract(uint256 amount) external {
        payable(msg.sender).transfer(amount);
    }

    /// @dev TP4: Alternative naming - "removeFunds"
    /// Tests name-agnostic detection
    function removeFunds(uint256 amount) external {
        userFunds[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
    }

    /// @dev TP5: Obfuscated function name
    /// Tests detection with non-standard naming
    function fn_0x123abc(uint256 amount) external {
        payable(msg.sender).transfer(amount);
    }

    /// @dev TP6: Alternative balance variable name - "shares"
    /// Tests WRITES_USER_BALANCE with different variable naming
    function updateShares(address user, uint256 amount) external {
        shares[user] = amount;  // vm-002 should flag this
    }

    /// @dev TP7: Alternative balance variable name - "deposits"
    /// Tests WRITES_USER_BALANCE detection across naming variations
    function modifyDeposit(address user, uint256 amount) external {
        deposits[user] = amount;  // vm-002 should flag this
    }

    /// @dev TP8: Low-level call{value:} transfer
    /// Tests TRANSFERS_VALUE_OUT with low-level call
    function sendFunds(address recipient, uint256 amount) external {
        (bool success, ) = payable(recipient).call{value: amount}("");
        require(success, "Transfer failed");
    }

    /// @dev TP9: Using send() method
    /// Tests TRANSFERS_VALUE_OUT detection with send()
    function sendEther(address recipient, uint256 amount) external {
        require(payable(recipient).send(amount), "Send failed");
    }

    // =========================================================================
    // TRUE NEGATIVES - Should NOT be flagged (Protected functions)
    // =========================================================================

    /// @dev TN1: Protected with onlyOwner modifier
    function withdrawProtected(uint256 amount) external onlyOwner {
        payable(msg.sender).transfer(amount);
    }

    /// @dev TN2: Protected with require check
    function withdrawWithRequire(uint256 amount) external {
        require(msg.sender == owner, "Not owner");
        payable(msg.sender).transfer(amount);
    }

    /// @dev TN3: Protected balance write with onlyOwner
    function setBalanceProtected(address user, uint256 amount) external onlyOwner {
        balances[user] = amount;
    }

    /// @dev TN4: Protected with if statement revert
    function withdrawWithIf(uint256 amount) external {
        if (msg.sender != owner) revert("Not authorized");
        payable(msg.sender).transfer(amount);
    }

    /// @dev TN5: Pull payment pattern (self-authorization)
    /// User can only withdraw their own balance
    function withdrawOwn() external {
        uint256 amount = balances[msg.sender];
        require(amount > 0, "Nothing to withdraw");
        balances[msg.sender] = 0;
        payable(msg.sender).transfer(amount);
    }

    /// @dev TN6: Protected with custom modifier
    function withdrawGuarded(uint256 amount) external nonReentrant {
        require(msg.sender == owner, "Not owner");
        payable(msg.sender).transfer(amount);
    }

    // =========================================================================
    // EDGE CASES - Should NOT be flagged
    // =========================================================================

    /// @dev EDGE1: View function (no state changes)
    function getBalance(address user) external view returns (uint256) {
        return balances[user];
    }

    /// @dev EDGE2: Pure function (no state access)
    function calculate(uint256 a, uint256 b) external pure returns (uint256) {
        return a + b;
    }

    /// @dev EDGE3: Internal function (not externally callable)
    function _internalTransfer(address recipient, uint256 amount) internal {
        payable(recipient).transfer(amount);
    }

    /// @dev EDGE4: Private function (not externally callable)
    function _privateSetBalance(address user, uint256 amount) private {
        balances[user] = amount;
    }

    /// @dev EDGE5: Receive function (special case, no explicit access control)
    receive() external payable {}

    /// @dev EDGE6: Fallback function
    fallback() external payable {}

    // =========================================================================
    // VARIATION TESTS - Alternative implementations that should still detect
    // =========================================================================

    /// @dev VAR1: Different variable naming - "controller" instead of "owner"
    address public controller;

    function setController(address _controller) external {
        controller = _controller;
    }

    /// @dev VAR2: Unprotected function with controller pattern (should flag)
    function extractAsController(uint256 amount) external {
        payable(msg.sender).transfer(amount);
    }

    /// @dev VAR3: Alternative balance storage pattern
    struct UserAccount {
        uint256 balance;
        uint256 lastUpdate;
    }
    mapping(address => UserAccount) public accounts;

    function updateAccount(address user, uint256 amount) external {
        accounts[user].balance = amount;  // WRITES_USER_BALANCE
    }

    /// @dev VAR4: Batch transfer (multiple transfers in one function)
    function batchWithdraw(address[] calldata recipients, uint256[] calldata amounts) external {
        for (uint256 i = 0; i < recipients.length; i++) {
            payable(recipients[i]).transfer(amounts[i]);
        }
    }

    /// @dev VAR5: Protected batch transfer (should NOT flag)
    function batchWithdrawProtected(address[] calldata recipients, uint256[] calldata amounts) external onlyOwner {
        for (uint256 i = 0; i < recipients.length; i++) {
            payable(recipients[i]).transfer(amounts[i]);
        }
    }

    // =========================================================================
    // FALSE POSITIVE PREVENTION - Intentionally public patterns
    // =========================================================================

    /// @dev FP_PREVENT1: Airdrop/distribution function (intentionally public)
    /// This WILL be flagged by vm-002, but needs Tier B analysis to determine
    /// if it's intentional. Pattern is correct to flag it.
    mapping(address => bool) public claimed;
    function claimAirdrop() external {
        require(!claimed[msg.sender], "Already claimed");
        claimed[msg.sender] = true;
        payable(msg.sender).transfer(1 ether);
    }

    /// @dev FP_PREVENT2: Reward distribution (intentionally public)
    mapping(address => uint256) public rewards;
    function claimReward() external {
        uint256 reward = rewards[msg.sender];
        require(reward > 0, "No reward");
        rewards[msg.sender] = 0;
        payable(msg.sender).transfer(reward);
    }
}

/**
 * @title InitializerTest
 * @notice Test initializer detection for vm-002
 */
contract InitializerTest {
    bool public initialized;
    address public owner;
    mapping(address => uint256) public balances;

    /// @dev EDGE7: Initializer function (should NOT flag)
    /// is_initializer_function = true
    function initialize(address _owner) external {
        require(!initialized, "Already initialized");
        initialized = true;
        owner = _owner;
        balances[_owner] = 1000 ether;  // Initial balance allocation
    }

    /// @dev EDGE8: OpenZeppelin-style initializer
    modifier initializer() {
        require(!initialized, "Already initialized");
        initialized = true;
        _;
    }

    function init(address _owner) external initializer {
        owner = _owner;
        balances[_owner] = 1000 ether;
    }
}

/**
 * @title ConstructorTest
 * @notice Test constructor detection for vm-002
 */
contract ConstructorTest {
    address public owner;
    mapping(address => uint256) public balances;

    /// @dev EDGE9: Constructor (should NOT flag)
    /// is_constructor = true
    constructor() {
        owner = msg.sender;
        balances[msg.sender] = 1000 ether;  // Initial allocation
    }
}
