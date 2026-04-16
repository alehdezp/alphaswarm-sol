// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title NonceNotUpdatedTest
 * @notice Test contract for multisig-002: Nonce Parameter Not Updated
 *
 * FALSE SECURITY VULNERABILITY: Function has nonce parameter but doesn't update nonce state.
 * This is WORSE than having no nonce because it creates false sense of security.
 *
 * Pattern Detection Requirements:
 * - contract_has_multisig == true
 * - has_nonce_parameter == true
 * - writes_nonce_state == false (THE VULNERABILITY)
 * - has_any_operation: [CALLS_EXTERNAL, CALLS_UNTRUSTED]
 * - visibility in [public, external]
 */

// =============================================================================
// HELPER CONTRACTS
// =============================================================================

contract Target {
    uint256 public value;

    function setValue(uint256 _value) external {
        value = _value;
    }
}

// =============================================================================
// TRUE POSITIVES: Nonce parameter BUT no state update
// =============================================================================

/**
 * @notice TP1-TP8: Various patterns of FALSE SECURITY
 * Each has nonce parameter but fails to update nonce state
 */
contract NonceNotUpdatedVulnerable {
    address[] public owners;
    mapping(address => bool) public isOwner;
    uint256 public requiredSignatures;

    // Nonce state declared but NEVER WRITTEN - false security!
    mapping(uint256 => bool) public usedNonces;
    uint256 public nonce;

    constructor(address[] memory _owners, uint256 _required) {
        owners = _owners;
        requiredSignatures = _required;
        for (uint256 i = 0; i < _owners.length; i++) {
            isOwner[_owners[i]] = true;
        }
    }

    // =========================================================================
    // TRUE POSITIVE 1: Standard execute with nonce parameter, NO update
    // =========================================================================
    function executeTransaction(
        address to,
        uint256 value,
        bytes memory data,
        uint256 _nonce,  // ✓ Has nonce parameter (DECEPTIVE)
        bytes[] memory signatures
    ) external payable {
        // ✗ VULNERABILITY: Missing require(!usedNonces[_nonce], "Already used")

        bytes32 txHash = keccak256(abi.encodePacked(to, value, data, _nonce));
        require(verifySignatures(txHash, signatures), "Invalid signatures");

        // ✗ CRITICAL VULNERABILITY: Missing usedNonces[_nonce] = true

        (bool success,) = to.call{value: value}(data);
        require(success, "Transaction failed");
    }

    // =========================================================================
    // TRUE POSITIVE 2: Submit with nonce, only emits event (NO state update)
    // =========================================================================
    function submitTransaction(
        address to,
        uint256 value,
        bytes memory data,
        uint256 txNonce,  // Different nonce naming
        bytes[] memory sigs
    ) external {
        bytes32 hash = keccak256(abi.encodePacked(to, value, data, txNonce));
        require(verifySignatures(hash, sigs), "Invalid sigs");

        // ✗ VULNERABILITY: Only emits event, doesn't update state
        emit TransactionSubmitted(txNonce, to, value, data);

        (bool success,) = to.call{value: value}(data);
        require(success, "Failed");
    }

    event TransactionSubmitted(uint256 indexed nonce, address to, uint256 value, bytes data);

    // =========================================================================
    // TRUE POSITIVE 3: Confirm/Execute with nonce parameter, only reads it
    // =========================================================================
    function confirmAndExecute(
        uint256 txId,
        address destination,
        bytes memory payload,
        uint256 executionNonce  // Yet another nonce naming
    ) external {
        // ✗ VULNERABILITY: Reads nonce for hashing but never updates state
        bytes32 txHash = keccak256(abi.encodePacked(
            destination,
            payload,
            executionNonce  // Included in hash but not tracked!
        ));

        require(isOwner[msg.sender], "Not owner");

        // External call without nonce state update
        (bool success,) = destination.call(payload);
        require(success, "Execution failed");
    }

    // =========================================================================
    // TRUE POSITIVE 4: Sequential nonce with require check BUT no increment
    // =========================================================================
    function executeWithNonce(
        address target,
        bytes memory callData,
        uint256 expectedNonce
    ) external {
        // ✓ Checks nonce (looks secure!)
        require(nonce == expectedNonce, "Nonce mismatch");

        bytes32 hash = keccak256(abi.encodePacked(target, callData, nonce));
        // Assume signature verification...

        // ✗ CRITICAL VULNERABILITY: Missing nonce++
        // Function appears to validate nonce but doesn't increment it!

        (bool success,) = target.call(callData);
        require(success, "Call failed");
    }

    // =========================================================================
    // TRUE POSITIVE 5: Alternative naming - sequenceNumber
    // =========================================================================
    function executeSequential(
        address to,
        bytes memory data,
        uint256 sequenceNumber  // Renamed from nonce
    ) external {
        bytes32 hash = keccak256(abi.encodePacked(to, data, sequenceNumber));

        // ✗ VULNERABILITY: sequenceNumber parameter but no state update

        (bool success,) = to.call(data);
        require(success, "Failed");
    }

    // =========================================================================
    // TRUE POSITIVE 6: Batch execute with nonce field, no tracking
    // =========================================================================
    struct Transaction {
        address to;
        uint256 value;
        bytes data;
        uint256 txNonce;  // Nonce field in struct
    }

    function batchExecute(
        Transaction[] calldata txs,
        bytes[] calldata signatures
    ) external {
        for (uint256 i = 0; i < txs.length; i++) {
            Transaction calldata tx = txs[i];

            // ✗ VULNERABILITY: Uses tx.txNonce in hash but never marks it used
            bytes32 hash = keccak256(abi.encodePacked(
                tx.to,
                tx.value,
                tx.data,
                tx.txNonce  // Present but not enforced!
            ));

            // Assume sig verification...

            (bool success,) = tx.to.call{value: tx.value}(tx.data);
            require(success, "Batch tx failed");
        }
    }

    // =========================================================================
    // TRUE POSITIVE 7: Counter naming variation
    // =========================================================================
    function executeWithCounter(
        address target,
        bytes memory data,
        uint256 counter  // Another nonce synonym
    ) external {
        bytes32 hash = keccak256(abi.encodePacked(target, data, counter));

        // ✗ VULNERABILITY: counter parameter but no increment

        (bool success,) = target.call(data);
        require(success, "Failed");
    }

    // =========================================================================
    // TRUE POSITIVE 8: Index naming variation
    // =========================================================================
    function executeAtIndex(
        address destination,
        bytes memory payload,
        uint256 index  // Yet another nonce synonym
    ) public {
        bytes32 hash = keccak256(abi.encodePacked(destination, payload, index));

        // ✗ VULNERABILITY: index parameter but no state tracking

        (bool success,) = destination.call(payload);
        require(success, "Failed");
    }

    // Helper function
    function verifySignatures(bytes32, bytes[] memory) internal view returns (bool) {
        return true; // Simplified for testing
    }
}

// =============================================================================
// TRUE NEGATIVES: Correct nonce usage (should NOT be flagged)
// =============================================================================

/**
 * @notice TN1-TN8: Safe implementations with proper nonce tracking
 */
contract NonceUpdatedSafe {
    address[] public owners;
    mapping(address => bool) public isOwner;
    uint256 public requiredSignatures;

    // Nonce state - WILL BE WRITTEN (safe)
    mapping(uint256 => bool) public usedNonces;
    uint256 public nonce;
    mapping(bytes32 => bool) public executedTxs;

    constructor(address[] memory _owners, uint256 _required) {
        owners = _owners;
        requiredSignatures = _required;
        for (uint256 i = 0; i < _owners.length; i++) {
            isOwner[_owners[i]] = true;
        }
    }

    // =========================================================================
    // TRUE NEGATIVE 1: Correct nonce tracking with mapping
    // =========================================================================
    function executeTransaction(
        address to,
        uint256 value,
        bytes memory data,
        uint256 _nonce,
        bytes[] memory signatures
    ) external payable {
        // ✓ Check nonce not used
        require(!usedNonces[_nonce], "Nonce already used");

        bytes32 txHash = keccak256(abi.encodePacked(to, value, data, _nonce));
        require(verifySignatures(txHash, signatures), "Invalid signatures");

        // ✓ CORRECT: Mark nonce as used
        usedNonces[_nonce] = true;

        (bool success,) = to.call{value: value}(data);
        require(success, "Transaction failed");

        emit TransactionExecuted(_nonce, to, value);
    }

    event TransactionExecuted(uint256 indexed nonce, address to, uint256 value);

    // =========================================================================
    // TRUE NEGATIVE 2: Incremental nonce counter (sequential)
    // =========================================================================
    function executeSequential(
        address to,
        bytes memory data,
        uint256 expectedNonce
    ) external {
        // ✓ Validate current nonce
        require(nonce == expectedNonce, "Invalid nonce");

        bytes32 hash = keccak256(abi.encodePacked(to, data, nonce));
        // Assume signature verification...

        // ✓ CORRECT: Increment nonce after use
        nonce++;

        (bool success,) = to.call(data);
        require(success, "Failed");
    }

    // =========================================================================
    // TRUE NEGATIVE 3: No nonce parameter (different vulnerability - multisig-001)
    // =========================================================================
    function executeWithoutNonce(
        address to,
        bytes memory data,
        bytes[] memory signatures
    ) external {
        // No nonce parameter at all - this is multisig-001, not multisig-002
        bytes32 hash = keccak256(abi.encodePacked(to, data));
        require(verifySignatures(hash, signatures), "Invalid sigs");

        (bool success,) = to.call(data);
        require(success, "Failed");
    }

    // =========================================================================
    // TRUE NEGATIVE 4: Transaction hash tracking (alternative to nonce)
    // =========================================================================
    function executeWithFlag(
        bytes32 txHash,
        address to,
        bytes memory data
    ) external {
        // Not nonce-based, uses hash tracking instead
        require(!executedTxs[txHash], "Already executed");

        // ✓ CORRECT: Uses executed flag
        executedTxs[txHash] = true;

        (bool success,) = to.call(data);
        require(success, "Failed");
    }

    // =========================================================================
    // TRUE NEGATIVE 5: View function with nonce parameter
    // =========================================================================
    function getNonceHash(
        address to,
        uint256 value,
        bytes memory data,
        uint256 _nonce
    ) external view returns (bytes32) {
        // View function - can't execute transactions
        return keccak256(abi.encodePacked(to, value, data, _nonce));
    }

    // =========================================================================
    // TRUE NEGATIVE 6: Internal helper with nonce
    // =========================================================================
    function _executeInternal(
        address to,
        bytes memory data,
        uint256 _nonce
    ) internal {
        // Internal function - not externally callable
        bytes32 hash = keccak256(abi.encodePacked(to, data, _nonce));
        (bool success,) = to.call(data);
        require(success, "Failed");
    }

    // =========================================================================
    // TRUE NEGATIVE 7: Nonce getter (view function)
    // =========================================================================
    function currentNonce() external view returns (uint256) {
        return nonce;
    }

    // =========================================================================
    // TRUE NEGATIVE 8: Deadline parameter (not nonce)
    // =========================================================================
    function executeWithDeadline(
        address to,
        bytes memory data,
        uint256 deadline,  // Different from nonce
        bytes[] memory sigs
    ) external {
        require(block.timestamp <= deadline, "Expired");

        bytes32 hash = keccak256(abi.encodePacked(to, data, deadline));
        require(verifySignatures(hash, sigs), "Invalid sigs");

        // Deadline-based, not nonce-based - different protection mechanism
        (bool success,) = to.call(data);
        require(success, "Failed");
    }

    // Helper
    function verifySignatures(bytes32, bytes[] memory) internal view returns (bool) {
        return true;
    }
}

// =============================================================================
// EDGE CASES: Tricky scenarios that test pattern robustness
// =============================================================================

/**
 * @notice Edge cases for multisig-002 detection
 */
contract NonceEdgeCases {
    address[] public owners;
    mapping(address => bool) public isOwner;

    mapping(uint256 => bool) public usedNonces;
    uint256 public nonce;

    constructor(address[] memory _owners) {
        owners = _owners;
        for (uint256 i = 0; i < _owners.length; i++) {
            isOwner[_owners[i]] = true;
        }
    }

    // =========================================================================
    // EDGE 1: Nonce updated in modifier (should be TN if detected)
    // =========================================================================
    modifier consumeNonce(uint256 _nonce) {
        require(!usedNonces[_nonce], "Used");
        usedNonces[_nonce] = true;  // Updated in modifier
        _;
    }

    function executeWithModifier(
        address to,
        bytes memory data,
        uint256 _nonce
    ) external consumeNonce(_nonce) {
        // Nonce updated in modifier - pattern should detect this as SAFE
        (bool success,) = to.call(data);
        require(success, "Failed");
    }

    // =========================================================================
    // EDGE 2: Nonce updated via assembly (advanced case)
    // =========================================================================
    function executeWithAssembly(
        address to,
        bytes memory data,
        uint256 _nonce
    ) external {
        // Update nonce via assembly
        assembly {
            // Get storage slot for usedNonces[_nonce]
            mstore(0x00, _nonce)
            mstore(0x20, usedNonces.slot)
            let slot := keccak256(0x00, 0x40)

            // Check if used
            let isUsed := sload(slot)
            if isUsed {
                revert(0, 0)
            }

            // Mark as used
            sstore(slot, 1)
        }

        (bool success,) = to.call(data);
        require(success, "Failed");
    }

    // =========================================================================
    // EDGE 3: Multiple nonce parameters (TP - neither updated)
    // =========================================================================
    function executeMultiNonce(
        address to,
        bytes memory data,
        uint256 userNonce,
        uint256 globalNonce
    ) external {
        bytes32 hash = keccak256(abi.encodePacked(to, data, userNonce, globalNonce));

        // ✗ VULNERABILITY: Both nonce parameters but neither updated

        (bool success,) = to.call(data);
        require(success, "Failed");
    }

    // =========================================================================
    // EDGE 4: Nonce validation in require but no write (TP)
    // =========================================================================
    function executeWithRequire(
        address to,
        bytes memory data,
        uint256 _nonce
    ) external {
        // Looks secure - validates nonce matches expected
        require(nonce == _nonce, "Invalid nonce");
        require(!usedNonces[_nonce], "Used");

        // ✗ VULNERABILITY: Validates but doesn't update!
        // Missing: nonce++ or usedNonces[_nonce] = true

        (bool success,) = to.call(data);
        require(success, "Failed");
    }

    // =========================================================================
    // EDGE 5: Nonce only in event (TP - event doesn't prevent replay)
    // =========================================================================
    function executeOnlyEvent(
        address to,
        bytes memory data,
        uint256 _nonce
    ) external {
        bytes32 hash = keccak256(abi.encodePacked(to, data, _nonce));

        // External call
        (bool success,) = to.call(data);
        require(success, "Failed");

        // ✗ VULNERABILITY: Nonce only in event, not in state
        emit Executed(_nonce, to);
    }

    event Executed(uint256 nonce, address to);

    // =========================================================================
    // EDGE 6: Nonce in return value only (TP)
    // =========================================================================
    function executeReturnNonce(
        address to,
        bytes memory data,
        uint256 _nonce
    ) external returns (uint256) {
        bytes32 hash = keccak256(abi.encodePacked(to, data, _nonce));

        (bool success,) = to.call(data);
        require(success, "Failed");

        // ✗ VULNERABILITY: Returns nonce but doesn't update state
        return _nonce;
    }
}

// =============================================================================
// VARIATION TESTS: Different naming and implementation patterns
// =============================================================================

/**
 * @notice Test pattern detection across naming variations
 */
contract NonceVariations {
    mapping(address => bool) public isOwner;

    // Various nonce state variable names
    mapping(uint256 => bool) public nonceUsed;
    mapping(uint256 => bool) public sequenceUsed;
    mapping(uint256 => bool) public counterUsed;
    mapping(uint256 => bool) public indexUsed;
    uint256 public txCount;
    uint256 public execCount;

    // =========================================================================
    // VAR1: Alternative nonce naming - sequenceNumber (TP)
    // =========================================================================
    function executeSequence(
        address to,
        bytes memory data,
        uint256 sequenceNumber  // Different naming
    ) external {
        bytes32 hash = keccak256(abi.encodePacked(to, data, sequenceNumber));

        // ✗ VULNERABILITY: sequenceNumber parameter but no sequenceUsed update

        (bool success,) = to.call(data);
        require(success, "Failed");
    }

    // =========================================================================
    // VAR2: Alternative naming - counter (TP)
    // =========================================================================
    function executeCount(
        address to,
        bytes memory data,
        uint256 counter
    ) external {
        bytes32 hash = keccak256(abi.encodePacked(to, data, counter));

        // ✗ VULNERABILITY: counter parameter but no counterUsed update

        (bool success,) = to.call(data);
        require(success, "Failed");
    }

    // =========================================================================
    // VAR3: Alternative naming - index (TP)
    // =========================================================================
    function executeIndex(
        address to,
        bytes memory data,
        uint256 index
    ) external {
        bytes32 hash = keccak256(abi.encodePacked(to, data, index));

        // ✗ VULNERABILITY: index parameter but no indexUsed update

        (bool success,) = to.call(data);
        require(success, "Failed");
    }

    // =========================================================================
    // VAR4: Incremental counter - SAFE version
    // =========================================================================
    function executeIncrement(
        address to,
        bytes memory data,
        uint256 expectedCount
    ) external {
        require(txCount == expectedCount, "Invalid count");

        bytes32 hash = keccak256(abi.encodePacked(to, data, txCount));

        // ✓ SAFE: Increments state
        txCount++;

        (bool success,) = to.call(data);
        require(success, "Failed");
    }

    // =========================================================================
    // VAR5: Mapping-based tracking - SAFE version
    // =========================================================================
    function executeTracked(
        address to,
        bytes memory data,
        uint256 _nonce
    ) external {
        require(!nonceUsed[_nonce], "Used");

        // ✓ SAFE: Marks nonce as used
        nonceUsed[_nonce] = true;

        bytes32 hash = keccak256(abi.encodePacked(to, data, _nonce));

        (bool success,) = to.call(data);
        require(success, "Failed");
    }
}

// =============================================================================
// NON-MULTISIG CONTRACTS: Should NOT be flagged
// =============================================================================

/**
 * @notice Regular contract without multisig characteristics
 * Pattern should NOT match because contract_has_multisig == false
 */
contract RegularContract {
    uint256 public nonce;

    // This has nonce parameter and doesn't update it, BUT it's not a multisig
    // Pattern should NOT flag this because contract_has_multisig == false
    function executeAction(
        address to,
        bytes memory data,
        uint256 _nonce
    ) external {
        (bool success,) = to.call(data);
        require(success, "Failed");
    }
}
