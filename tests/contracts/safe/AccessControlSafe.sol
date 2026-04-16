// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title AccessControlSafe
 * @notice Safe implementations of access control patterns.
 * @dev These contracts demonstrate proper access control mechanisms.
 */

/**
 * @title OwnableSafe
 * @notice Safe: Proper owner-based access control
 */
contract OwnableSafe {
    address public owner;

    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    constructor() {
        owner = msg.sender;
        emit OwnershipTransferred(address(0), msg.sender);
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    // SAFE: Protected by onlyOwner modifier
    function setOwner(address newOwner) external onlyOwner {
        require(newOwner != address(0), "Invalid owner");
        address oldOwner = owner;
        owner = newOwner;
        emit OwnershipTransferred(oldOwner, newOwner);
    }

    // SAFE: Protected by onlyOwner
    function withdrawFunds() external onlyOwner {
        (bool success, ) = owner.call{value: address(this).balance}("");
        require(success, "Transfer failed");
    }

    receive() external payable {}
}

/**
 * @title TwoStepOwnershipSafe
 * @notice Safe: Two-step ownership transfer prevents accidents
 */
contract TwoStepOwnershipSafe {
    address public owner;
    address public pendingOwner;

    event OwnershipTransferStarted(address indexed previousOwner, address indexed newOwner);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    // SAFE: First step - initiate transfer
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "Invalid owner");
        pendingOwner = newOwner;
        emit OwnershipTransferStarted(owner, newOwner);
    }

    // SAFE: Second step - new owner must accept
    function acceptOwnership() external {
        require(msg.sender == pendingOwner, "Not pending owner");
        address oldOwner = owner;
        owner = msg.sender;
        pendingOwner = address(0);
        emit OwnershipTransferred(oldOwner, msg.sender);
    }
}

/**
 * @title RoleBasedAccessSafe
 * @notice Safe: Role-based access control (RBAC)
 */
contract RoleBasedAccessSafe {
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");

    mapping(bytes32 => mapping(address => bool)) private _roles;

    event RoleGranted(bytes32 indexed role, address indexed account, address indexed sender);
    event RoleRevoked(bytes32 indexed role, address indexed account, address indexed sender);

    constructor() {
        _roles[ADMIN_ROLE][msg.sender] = true;
        emit RoleGranted(ADMIN_ROLE, msg.sender, msg.sender);
    }

    modifier onlyRole(bytes32 role) {
        require(_roles[role][msg.sender], "Missing role");
        _;
    }

    function hasRole(bytes32 role, address account) public view returns (bool) {
        return _roles[role][account];
    }

    // SAFE: Only admin can grant roles
    function grantRole(bytes32 role, address account) external onlyRole(ADMIN_ROLE) {
        _roles[role][account] = true;
        emit RoleGranted(role, account, msg.sender);
    }

    // SAFE: Only admin can revoke roles
    function revokeRole(bytes32 role, address account) external onlyRole(ADMIN_ROLE) {
        _roles[role][account] = false;
        emit RoleRevoked(role, account, msg.sender);
    }

    // SAFE: Protected by MINTER_ROLE
    function mint(address to, uint256 amount) external onlyRole(MINTER_ROLE) {
        // Minting logic would go here
    }

    // SAFE: Protected by PAUSER_ROLE
    function pause() external onlyRole(PAUSER_ROLE) {
        // Pause logic would go here
    }
}

/**
 * @title MultisigSafe
 * @notice Safe: Multi-signature approval required
 */
contract MultisigSafe {
    address[] public signers;
    uint256 public requiredSignatures;
    mapping(bytes32 => mapping(address => bool)) public hasApproved;
    mapping(bytes32 => uint256) public approvalCount;

    constructor(address[] memory _signers, uint256 _required) {
        require(_signers.length >= _required, "Invalid threshold");
        require(_required > 0, "Need at least 1 sig");
        signers = _signers;
        requiredSignatures = _required;
    }

    modifier onlySigner() {
        bool isSigner = false;
        for (uint i = 0; i < signers.length; i++) {
            if (signers[i] == msg.sender) {
                isSigner = true;
                break;
            }
        }
        require(isSigner, "Not a signer");
        _;
    }

    // SAFE: Requires multiple signatures
    function approve(bytes32 txHash) external onlySigner {
        require(!hasApproved[txHash][msg.sender], "Already approved");
        hasApproved[txHash][msg.sender] = true;
        approvalCount[txHash]++;
    }

    // SAFE: Only executes if threshold met
    function execute(address to, uint256 value, bytes calldata data) external onlySigner returns (bool) {
        bytes32 txHash = keccak256(abi.encodePacked(to, value, data));
        require(approvalCount[txHash] >= requiredSignatures, "Not enough approvals");

        (bool success, ) = to.call{value: value}(data);
        return success;
    }
}

/**
 * @title TimelockSafe
 * @notice Safe: Time-delayed execution for sensitive operations
 */
contract TimelockSafe {
    uint256 public constant DELAY = 2 days;
    address public admin;

    struct QueuedTx {
        address target;
        uint256 value;
        bytes data;
        uint256 executeTime;
        bool executed;
    }

    mapping(bytes32 => QueuedTx) public queuedTransactions;

    event TransactionQueued(bytes32 indexed txHash, address target, uint256 value, bytes data, uint256 executeTime);
    event TransactionExecuted(bytes32 indexed txHash);

    constructor() {
        admin = msg.sender;
    }

    modifier onlyAdmin() {
        require(msg.sender == admin, "Not admin");
        _;
    }

    // SAFE: Queue transaction with time delay
    function queueTransaction(address target, uint256 value, bytes calldata data) external onlyAdmin returns (bytes32) {
        bytes32 txHash = keccak256(abi.encodePacked(target, value, data, block.timestamp));
        uint256 executeTime = block.timestamp + DELAY;

        queuedTransactions[txHash] = QueuedTx({
            target: target,
            value: value,
            data: data,
            executeTime: executeTime,
            executed: false
        });

        emit TransactionQueued(txHash, target, value, data, executeTime);
        return txHash;
    }

    // SAFE: Can only execute after delay
    function executeTransaction(bytes32 txHash) external onlyAdmin {
        QueuedTx storage qtx = queuedTransactions[txHash];
        require(qtx.executeTime != 0, "Transaction not queued");
        require(!qtx.executed, "Already executed");
        require(block.timestamp >= qtx.executeTime, "Timelock not expired");

        qtx.executed = true;
        (bool success, ) = qtx.target.call{value: qtx.value}(qtx.data);
        require(success, "Transaction failed");

        emit TransactionExecuted(txHash);
    }
}

/**
 * @title MsgSenderCheckSafe
 * @notice Safe: Explicit msg.sender checks in require statements
 */
contract MsgSenderCheckSafe {
    address public admin;
    address public treasury;

    constructor(address _treasury) {
        admin = msg.sender;
        treasury = _treasury;
    }

    // SAFE: Explicit require with msg.sender check
    function setAdmin(address newAdmin) external {
        require(msg.sender == admin, "Caller is not admin");
        require(newAdmin != address(0), "Invalid admin");
        admin = newAdmin;
    }

    // SAFE: Explicit require with msg.sender check
    function setTreasury(address newTreasury) external {
        require(msg.sender == admin, "Caller is not admin");
        require(newTreasury != address(0), "Invalid treasury");
        treasury = newTreasury;
    }
}
