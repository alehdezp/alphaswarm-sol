// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title DelegatecallSafe
 * @notice Safe implementations of delegatecall patterns.
 * @dev These contracts demonstrate proper delegatecall security.
 */

/**
 * @title DelegatecallWithAccessControlSafe
 * @notice Safe: Delegatecall protected by access control
 */
contract DelegatecallWithAccessControlSafe {
    address public owner;
    address public trustedImplementation;

    constructor(address _trustedImpl) {
        owner = msg.sender;
        trustedImplementation = _trustedImpl;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    // SAFE: Only owner can trigger delegatecall
    function execute(bytes calldata data) external onlyOwner returns (bytes memory) {
        (bool success, bytes memory result) = trustedImplementation.delegatecall(data);
        require(success, "Delegatecall failed");
        return result;
    }

    // SAFE: Only owner can change implementation
    function setImplementation(address newImpl) external onlyOwner {
        require(newImpl != address(0), "Invalid implementation");
        require(newImpl.code.length > 0, "Not a contract");
        trustedImplementation = newImpl;
    }
}

/**
 * @title DelegatecallWhitelistSafe
 * @notice Safe: Delegatecall only to whitelisted targets
 */
contract DelegatecallWhitelistSafe {
    address public owner;
    mapping(address => bool) public whitelistedTargets;

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    function addToWhitelist(address target) external onlyOwner {
        require(target != address(0), "Invalid target");
        require(target.code.length > 0, "Not a contract");
        whitelistedTargets[target] = true;
    }

    function removeFromWhitelist(address target) external onlyOwner {
        whitelistedTargets[target] = false;
    }

    // SAFE: Only delegatecall to whitelisted targets
    function delegateTo(address target, bytes calldata data) external onlyOwner returns (bytes memory) {
        require(whitelistedTargets[target], "Target not whitelisted");
        (bool success, bytes memory result) = target.delegatecall(data);
        require(success, "Delegatecall failed");
        return result;
    }
}

/**
 * @title DelegatecallSelectorGuardSafe
 * @notice Safe: Delegatecall with function selector validation
 */
contract DelegatecallSelectorGuardSafe {
    address public owner;
    address public implementation;
    mapping(bytes4 => bool) public allowedSelectors;

    constructor(address _impl) {
        owner = msg.sender;
        implementation = _impl;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    function allowSelector(bytes4 selector) external onlyOwner {
        allowedSelectors[selector] = true;
    }

    function disallowSelector(bytes4 selector) external onlyOwner {
        allowedSelectors[selector] = false;
    }

    // SAFE: Only allowed function selectors can be called
    function delegateWithSelector(bytes calldata data) external onlyOwner returns (bytes memory) {
        require(data.length >= 4, "Invalid calldata");

        bytes4 selector = bytes4(data[:4]);
        require(allowedSelectors[selector], "Selector not allowed");

        (bool success, bytes memory result) = implementation.delegatecall(data);
        require(success, "Delegatecall failed");
        return result;
    }
}

/**
 * @title StaticDelegatecallSafe
 * @notice Safe: Using staticcall for read-only operations
 */
contract StaticDelegatecallSafe {
    address public implementation;

    constructor(address _impl) {
        implementation = _impl;
    }

    // SAFE: Use staticcall for read-only operations (no state changes)
    function viewDelegate(bytes calldata data) external view returns (bytes memory) {
        // staticcall prevents state modifications
        (bool success, bytes memory result) = implementation.staticcall(data);
        require(success, "Staticcall failed");
        return result;
    }
}

/**
 * @title MulticallSafe
 * @notice Safe: Multicall with reentrancy protection
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

contract MulticallSafe is ReentrancyGuard {
    // SAFE: Protected multicall with reentrancy guard
    function multicall(bytes[] calldata data) external nonReentrant returns (bytes[] memory results) {
        results = new bytes[](data.length);
        for (uint256 i = 0; i < data.length; i++) {
            (bool success, bytes memory result) = address(this).delegatecall(data[i]);
            require(success, "Multicall failed");
            results[i] = result;
        }
    }
}

/**
 * @title NoArbitraryDelegatecallSafe
 * @notice Safe: Avoid arbitrary delegatecall targets
 */
contract NoArbitraryDelegatecallSafe {
    // Immutable implementation - cannot be changed
    address public immutable TRUSTED_IMPL;

    constructor(address _impl) {
        require(_impl != address(0), "Invalid implementation");
        require(_impl.code.length > 0, "Not a contract");
        TRUSTED_IMPL = _impl;
    }

    // SAFE: Delegatecall only to immutable trusted implementation
    function execute(bytes calldata data) external returns (bytes memory) {
        (bool success, bytes memory result) = TRUSTED_IMPL.delegatecall(data);
        require(success, "Execution failed");
        return result;
    }
}

/**
 * @title DelegatecallStorageAlignedSafe
 * @notice Safe: Ensure storage layout alignment with implementation
 */
contract DelegatecallStorageAlignedSafe {
    // Storage layout MUST match implementation exactly

    // Slot 0
    address public owner;
    // Slot 1
    uint256 public value;
    // Slot 2
    mapping(address => uint256) public balances;

    address public implementation;

    constructor(address _impl) {
        owner = msg.sender;
        implementation = _impl;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    // SAFE: Delegatecall with storage-aligned implementation
    function delegateExecute(bytes calldata data) external onlyOwner returns (bytes memory) {
        (bool success, bytes memory result) = implementation.delegatecall(data);
        require(success, "Delegatecall failed");
        return result;
    }
}

/**
 * @title DelegatecallTimelockSafe
 * @notice Safe: Time-delayed delegatecall for sensitive operations
 */
contract DelegatecallTimelockSafe {
    address public owner;
    address public implementation;

    uint256 public constant DELAY = 2 days;

    struct PendingCall {
        bytes data;
        uint256 executeTime;
        bool executed;
    }

    mapping(bytes32 => PendingCall) public pendingCalls;

    constructor(address _impl) {
        owner = msg.sender;
        implementation = _impl;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    // SAFE: Queue call with time delay
    function queueCall(bytes calldata data) external onlyOwner returns (bytes32) {
        bytes32 callId = keccak256(abi.encodePacked(data, block.timestamp));

        pendingCalls[callId] = PendingCall({
            data: data,
            executeTime: block.timestamp + DELAY,
            executed: false
        });

        return callId;
    }

    // SAFE: Execute only after delay
    function executeCall(bytes32 callId) external onlyOwner returns (bytes memory) {
        PendingCall storage pending = pendingCalls[callId];

        require(pending.executeTime > 0, "Call not queued");
        require(!pending.executed, "Already executed");
        require(block.timestamp >= pending.executeTime, "Timelock not expired");

        pending.executed = true;

        (bool success, bytes memory result) = implementation.delegatecall(pending.data);
        require(success, "Delegatecall failed");
        return result;
    }
}
