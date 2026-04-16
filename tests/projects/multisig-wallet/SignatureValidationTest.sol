// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// =============================================================================
// TEST CONTRACT FOR: multisig-003-execution-without-signature-validation
// =============================================================================
// Tests detection of multisig execution functions that perform external calls
// without proper signature validation using ecrecover.
//
// TEST CATEGORIES:
// 1. TRUE POSITIVES (TP): Functions that should be flagged
// 2. TRUE NEGATIVES (TN): Safe functions that should NOT be flagged
// 3. EDGE CASES: Boundary conditions and special scenarios
// 4. VARIATIONS: Different implementation styles that should be detected
// =============================================================================

// OpenZeppelin library interfaces for variations
interface IERC1271 {
    function isValidSignature(bytes32 hash, bytes memory signature) external view returns (bytes4 magicValue);
}

library ECDSA {
    function recover(bytes32 hash, bytes memory signature) internal pure returns (address) {
        // Simplified mock
        return address(0);
    }
}

// =============================================================================
// TRUE POSITIVES: Functions that SHOULD be flagged by multisig-003
// =============================================================================

contract VulnerableExecutionStandard {
    address[] public owners;
    uint256 public threshold = 3;

    // TP1: Standard signature array parameter, no validation
    function execute(
        address to,
        uint256 value,
        bytes memory data,
        bytes[] memory signatures
    ) external {
        require(signatures.length >= threshold, "Insufficient signatures");

        // VULNERABLE: No ecrecover validation, just external call
        (bool success, ) = to.call{value: value}(data);
        require(success, "Transaction failed");
    }
}

contract VulnerableExecutionSplitSignature {
    address[] public signers;
    uint256 public required = 2;

    // TP2: Split signature parameters (r, s, v), no validation
    function submitWithSignatures(
        address target,
        bytes calldata callData,
        bytes32 r,
        bytes32 s,
        uint8 v
    ) external {
        // VULNERABLE: Has signature parameters but no ecrecover check
        (bool success, ) = target.call(callData);
        require(success);
    }
}

contract VulnerableExecutionSignatureStruct {
    struct Signature {
        bytes32 r;
        bytes32 s;
        uint8 v;
    }

    mapping(address => bool) public isOwner;

    // TP3: Signature struct array, only checks length not validity
    function multiSigExecute(
        address destination,
        uint256 amount,
        Signature[] calldata sigs
    ) external {
        // VULNERABLE: Checks array length but doesn't validate cryptographic signatures
        require(sigs.length >= 3, "Need 3 signatures");

        (bool ok, ) = destination.call{value: amount}("");
        require(ok);
    }
}

contract VulnerableExecutionAddressArray {
    mapping(address => bool) public owners;

    // TP4: Address array claiming to be "signers" but no proof they signed
    function executeWithApprovals(
        address to,
        bytes memory data,
        address[] memory approvers
    ) external {
        // VULNERABLE: Assumes addresses in array approved, no signature verification
        require(approvers.length >= 2, "Need 2 approvers");
        for (uint i = 0; i < approvers.length; i++) {
            require(owners[approvers[i]], "Invalid owner");
        }

        (bool success, ) = to.call(data);
        require(success);
    }
}

contract VulnerableBatchExecution {
    address[] public signers;

    // TP5: Batch execution with signature bytes, no validation
    function batchExecuteWithSigs(
        address[] calldata targets,
        bytes[] calldata calls,
        bytes calldata signatures
    ) external {
        // VULNERABLE: Has signatures parameter but no cryptographic check
        require(signatures.length >= 65, "Sig too short");

        for (uint i = 0; i < targets.length; i++) {
            (bool success, ) = targets[i].call(calls[i]);
            require(success);
        }
    }
}

contract VulnerableEIP712NoValidation {
    bytes32 public DOMAIN_SEPARATOR;
    mapping(address => bool) public isSigner;

    // TP6: Has EIP-712 parameters but no actual signature validation
    function executeEIP712(
        address to,
        bytes memory data,
        bytes32 digest,
        bytes memory signature
    ) external {
        // VULNERABLE: Has EIP-712 digest and signature but doesn't validate
        (bool success, ) = to.call(data);
        require(success);
    }
}

contract VulnerableAlternateNaming {
    address[] public controllers;
    uint256 public quorum = 5;

    // TP7: Different function naming, still vulnerable
    function multiSigCall(
        address target,
        bytes calldata payload,
        bytes[] calldata approvalSigs
    ) external {
        // VULNERABLE: Different naming but same issue - no validation
        require(approvalSigs.length >= quorum, "Insufficient approvals");

        (bool ok, ) = target.call(payload);
        require(ok);
    }
}

contract VulnerableCompactSignature {
    mapping(address => bool) public authorized;
    address[] public signers; // Add multisig indicator

    // TP8: Compact 65-byte signature format, no validation
    function executeCompact(
        address to,
        uint256 value,
        bytes calldata data,
        bytes calldata signature // 65 bytes compact
    ) external {
        // VULNERABLE: Has compact signature but doesn't use ecrecover
        require(signature.length == 65, "Invalid signature length");

        (bool success, ) = to.call{value: value}(data);
        require(success);
    }
}

contract VulnerableEIP2098Signature {
    address[] public owners;

    // TP9: EIP-2098 compact signature (64 bytes), no validation
    function executeEIP2098(
        address target,
        bytes memory data,
        bytes32 r,
        bytes32 vs // EIP-2098 compact: s and v combined
    ) external {
        // VULNERABLE: Has EIP-2098 signature format but no validation
        (bool success, ) = target.call(data);
        require(success);
    }
}

contract VulnerableOnlyLengthCheck {
    uint256 public requiredSigs = 4;
    address[] public owners; // Add multisig indicator

    // TP10: Only validates signature count, not content
    function executeMultiple(
        address to,
        bytes memory data,
        bytes[] memory sigs
    ) external {
        // VULNERABLE: Only checks array length, doesn't verify signatures are valid
        require(sigs.length == requiredSigs, "Wrong number of signatures");

        for (uint i = 0; i < sigs.length; i++) {
            require(sigs[i].length == 65, "Invalid sig format");
        }

        (bool success, ) = to.call(data);
        require(success);
    }
}

// =============================================================================
// TRUE NEGATIVES: Safe functions that should NOT be flagged
// =============================================================================

contract SafeWithEcrecover {
    mapping(address => bool) public isOwner;
    uint256 public nonce;

    // TN1: SAFE - Uses ecrecover to validate signatures
    function execute(
        address to,
        uint256 value,
        bytes memory data,
        bytes[] memory signatures
    ) external {
        bytes32 txHash = keccak256(abi.encodePacked(address(this), nonce++, to, value, data));
        bytes32 ethSignedHash = keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", txHash));

        for (uint i = 0; i < signatures.length; i++) {
            (uint8 v, bytes32 r, bytes32 s) = _splitSignature(signatures[i]);

            // SAFE: Uses ecrecover for validation
            address signer = ecrecover(ethSignedHash, v, r, s);
            require(signer != address(0), "Invalid signature");
            require(isOwner[signer], "Not an owner");
        }

        (bool success, ) = to.call{value: value}(data);
        require(success);
    }

    function _splitSignature(bytes memory sig) internal pure returns (uint8, bytes32, bytes32) {
        require(sig.length == 65);
        bytes32 r;
        bytes32 s;
        uint8 v;
        assembly {
            r := mload(add(sig, 32))
            s := mload(add(sig, 64))
            v := byte(0, mload(add(sig, 96)))
        }
        return (v, r, s);
    }
}

contract SafeWithECDSALibrary {
    mapping(address => bool) public isSigner;

    // TN2: SAFE - Uses ECDSA library for signature recovery
    function submitWithSignatures(
        address to,
        bytes memory data,
        bytes32 digest,
        bytes memory signature
    ) external {
        // SAFE: Uses ECDSA.recover
        address signer = ECDSA.recover(digest, signature);
        require(signer != address(0), "Invalid sig");
        require(isSigner[signer], "Not authorized");

        (bool success, ) = to.call(data);
        require(success);
    }
}

contract SafeWithEIP1271 {
    address[] public owners;

    // TN3: SAFE - Uses EIP-1271 contract signature validation
    function multiSigExecute(
        address to,
        bytes memory data,
        address[] memory signers,
        bytes[] memory signatures
    ) external {
        bytes32 hash = keccak256(abi.encodePacked(to, data));

        for (uint i = 0; i < signers.length; i++) {
            // SAFE: Uses EIP-1271 for validation
            if (_isContract(signers[i])) {
                bytes4 result = IERC1271(signers[i]).isValidSignature(hash, signatures[i]);
                require(result == 0x1626ba7e, "Invalid contract signature");
            } else {
                // Use _split helper for EOA signatures
                (uint8 v, bytes32 r, bytes32 s) = _split(signatures[i]);
                address recovered = ecrecover(hash, v, r, s);
                require(recovered == signers[i], "Invalid EOA signature");
            }
        }

        (bool success, ) = to.call(data);
        require(success);
    }

    function _isContract(address account) internal view returns (bool) {
        uint256 size;
        assembly { size := extcodesize(account) }
        return size > 0;
    }

    function _split(bytes memory sig) internal pure returns (uint8, bytes32, bytes32) {
        require(sig.length == 65);
        bytes32 r; bytes32 s; uint8 v;
        assembly {
            r := mload(add(sig, 32))
            s := mload(add(sig, 64))
            v := byte(0, mload(add(sig, 96)))
        }
        return (v, r, s);
    }
}

contract SafeViewFunction {
    // TN4: SAFE - View function, doesn't perform external calls
    function getTransactionHash(
        address to,
        uint256 value,
        bytes memory data,
        bytes[] memory signatures
    ) external view returns (bytes32) {
        // Use abi.encode instead of abi.encodePacked for bytes[]
        return keccak256(abi.encode(to, value, data, signatures));
    }
}

contract SafeInternalHelper {
    // TN5: SAFE - Internal function, not externally callable
    function _executeInternal(
        address to,
        bytes memory data,
        bytes[] memory signatures
    ) internal {
        // Internal function - pattern shouldn't flag (visibility check)
        (bool success, ) = to.call(data);
        require(success);
    }
}

contract SafeWithoutSignatureParams {
    mapping(bytes32 => bool) public approved;

    // TN6: SAFE - Different pattern: uses pre-approved hashes, no signature params
    function execute(
        address to,
        uint256 value,
        bytes memory data
    ) external {
        bytes32 txHash = keccak256(abi.encodePacked(to, value, data));
        require(approved[txHash], "Not approved");

        (bool success, ) = to.call{value: value}(data);
        require(success);
    }
}

contract SafeNonMultisigContract {
    // TN7: SAFE - Not a multisig contract (no multisig indicators)
    function executeAction(
        address target,
        bytes memory data,
        bytes memory signature
    ) external {
        // This is NOT a multisig contract - pattern checks contract_has_multisig
        (bool success, ) = target.call(data);
        require(success);
    }
}

contract SafeConstructor {
    address[] public owners;

    // TN8: SAFE - Constructor excluded by pattern
    constructor(address[] memory _owners) {
        owners = _owners;
    }
}

contract SafeInitializer {
    bool private initialized;
    address[] public signers;

    // TN9: SAFE - Initializer excluded by pattern
    function initialize(address[] memory _signers) external {
        require(!initialized, "Already initialized");
        initialized = true;
        signers = _signers;
    }
}

// =============================================================================
// EDGE CASES: Boundary conditions and special scenarios
// =============================================================================

contract EdgeSignatureInModifier {
    mapping(address => bool) public isOwner;

    modifier validSignatures(bytes32 hash, bytes[] memory sigs) {
        for (uint i = 0; i < sigs.length; i++) {
            (uint8 v, bytes32 r, bytes32 s) = _split(sigs[i]);
            address signer = ecrecover(hash, v, r, s);
            require(isOwner[signer], "Invalid signer");
        }
        _;
    }

    // EDGE1: Signature validation in modifier (should be SAFE)
    function execute(
        address to,
        bytes memory data,
        bytes32 hash,
        bytes[] memory signatures
    ) external validSignatures(hash, signatures) {
        (bool success, ) = to.call(data);
        require(success);
    }

    function _split(bytes memory sig) internal pure returns (uint8, bytes32, bytes32) {
        require(sig.length == 65);
        bytes32 r; bytes32 s; uint8 v;
        assembly {
            r := mload(add(sig, 32))
            s := mload(add(sig, 64))
            v := byte(0, mload(add(sig, 96)))
        }
        return (v, r, s);
    }
}

contract EdgeSignatureInExternalContract {
    address public validator;

    // EDGE2: Signature validation delegated to external contract
    function executeWithApprovals(
        address to,
        bytes memory data,
        bytes[] memory signatures
    ) external {
        // Validation in external contract - pattern might miss this
        (bool valid, ) = validator.call(abi.encodeWithSignature(
            "validateSignatures(bytes32,bytes[])",
            keccak256(abi.encodePacked(to, data)),
            signatures
        ));
        require(valid, "Invalid signatures");

        (bool success, ) = to.call(data);
        require(success);
    }
}

library SignatureLib {
    function validateWithEcrecover(
        bytes32 hash,
        bytes memory sig,
        address expected
    ) internal pure returns (bool) {
        (uint8 v, bytes32 r, bytes32 s) = _split(sig);
        address signer = ecrecover(hash, v, r, s);
        return signer == expected;
    }

    function _split(bytes memory sig) private pure returns (uint8, bytes32, bytes32) {
        require(sig.length == 65);
        bytes32 r; bytes32 s; uint8 v;
        assembly {
            r := mload(add(sig, 32))
            s := mload(add(sig, 64))
            v := byte(0, mload(add(sig, 96)))
        }
        return (v, r, s);
    }
}

contract EdgeSignatureInLibrary {
    using SignatureLib for bytes32;
    mapping(address => bool) public owners;

    // EDGE3: Signature validation via library
    function execute(
        address to,
        bytes memory data,
        bytes memory signature
    ) external {
        bytes32 hash = keccak256(abi.encodePacked(to, data));

        // Validation via library - pattern should detect library ecrecover
        bool valid = hash.validateWithEcrecover(signature, msg.sender);
        require(valid, "Invalid signature");
        require(owners[msg.sender], "Not owner");

        (bool success, ) = to.call(data);
        require(success);
    }
}

contract EdgeSignatureInAssembly {
    address[] public signers;

    // EDGE4: Signature validation using assembly ecrecover
    function executeWithAssembly(
        address to,
        bytes memory data,
        bytes32 hash,
        bytes memory signature
    ) external {
        bytes32 r;
        bytes32 s;
        uint8 v;

        assembly {
            r := mload(add(signature, 32))
            s := mload(add(signature, 64))
            v := byte(0, mload(add(signature, 96)))
        }

        address signer;
        assembly {
            // Assembly ecrecover
            let ptr := mload(0x40)
            mstore(ptr, hash)
            mstore(add(ptr, 32), v)
            mstore(add(ptr, 64), r)
            mstore(add(ptr, 96), s)

            let result := staticcall(gas(), 0x01, ptr, 128, ptr, 32)
            signer := mload(ptr)
        }

        require(signer != address(0), "Invalid sig");

        (bool success, ) = to.call(data);
        require(success);
    }
}

contract EdgeMultipleSignatureTypes {
    mapping(address => bool) public eoaOwners;
    mapping(address => bool) public contractOwners;

    // EDGE5: Handles both EOA (ecrecover) and contract (EIP-1271) signatures
    function execute(
        address to,
        bytes memory data,
        address[] memory signers,
        bytes[] memory signatures
    ) external {
        bytes32 hash = keccak256(abi.encodePacked(to, data));

        for (uint i = 0; i < signers.length; i++) {
            if (_isContract(signers[i])) {
                // EIP-1271 for contract
                bytes4 result = IERC1271(signers[i]).isValidSignature(hash, signatures[i]);
                require(result == 0x1626ba7e);
                require(contractOwners[signers[i]]);
            } else {
                // ecrecover for EOA
                (uint8 v, bytes32 r, bytes32 s) = _split(signatures[i]);
                address recovered = ecrecover(hash, v, r, s);
                require(recovered == signers[i]);
                require(eoaOwners[signers[i]]);
            }
        }

        (bool success, ) = to.call(data);
        require(success);
    }

    function _isContract(address a) internal view returns (bool) {
        uint256 size;
        assembly { size := extcodesize(a) }
        return size > 0;
    }

    function _split(bytes memory sig) internal pure returns (uint8, bytes32, bytes32) {
        require(sig.length == 65);
        bytes32 r; bytes32 s; uint8 v;
        assembly {
            r := mload(add(sig, 32))
            s := mload(add(sig, 64))
            v := byte(0, mload(add(sig, 96)))
        }
        return (v, r, s);
    }
}

contract EdgeSignatureInStructField {
    struct Transaction {
        address to;
        uint256 value;
        bytes data;
        bytes signature;
    }

    mapping(address => bool) public owners;

    // EDGE6: Signature parameter inside struct
    function batchExecute(Transaction[] calldata txs) external {
        for (uint i = 0; i < txs.length; i++) {
            bytes32 hash = keccak256(abi.encodePacked(txs[i].to, txs[i].value, txs[i].data));

            (uint8 v, bytes32 r, bytes32 s) = _split(txs[i].signature);
            address signer = ecrecover(hash, v, r, s);
            require(owners[signer], "Invalid signer");

            (bool success, ) = txs[i].to.call{value: txs[i].value}(txs[i].data);
            require(success);
        }
    }

    function _split(bytes memory sig) internal pure returns (uint8, bytes32, bytes32) {
        require(sig.length == 65);
        bytes32 r; bytes32 s; uint8 v;
        assembly {
            r := mload(add(sig, 32))
            s := mload(add(sig, 64))
            v := byte(0, mload(add(sig, 96)))
        }
        return (v, r, s);
    }
}

contract EdgeNoExternalCallButHasSigs {
    mapping(address => bool) public owners;

    // EDGE7: Has signature validation but NO external call (should NOT flag)
    function validateOnly(
        bytes32 hash,
        bytes[] memory signatures
    ) external view returns (bool) {
        // No external call - pattern requires CALLS_EXTERNAL or CALLS_UNTRUSTED
        for (uint i = 0; i < signatures.length; i++) {
            (uint8 v, bytes32 r, bytes32 s) = _split(signatures[i]);
            address signer = ecrecover(hash, v, r, s);
            if (!owners[signer]) return false;
        }
        return true;
    }

    function _split(bytes memory sig) internal pure returns (uint8, bytes32, bytes32) {
        require(sig.length == 65);
        bytes32 r; bytes32 s; uint8 v;
        assembly {
            r := mload(add(sig, 32))
            s := mload(add(sig, 64))
            v := byte(0, mload(add(sig, 96)))
        }
        return (v, r, s);
    }
}

// =============================================================================
// VARIATIONS: Different implementation styles
// =============================================================================

contract VariationNamingConventions {
    address[] public controllers;
    uint256 public threshold = 2; // Add multisig indicator

    // VAR1: "controller" instead of "owner"
    function executeAction(
        address target,
        bytes memory payload,
        bytes[] memory authSigs
    ) external {
        // VULNERABLE: Different naming but same issue
        require(authSigs.length >= 2, "Need 2 controllers");
        (bool ok, ) = target.call(payload);
        require(ok);
    }
}

contract VariationGnosisSafeStyle {
    mapping(address => address) public owners;

    // VAR2: Gnosis Safe-style execution
    function execTransaction(
        address to,
        uint256 value,
        bytes calldata data,
        uint8 operation,
        uint256 safeTxGas,
        uint256 baseGas,
        uint256 gasPrice,
        address gasToken,
        address refundReceiver,
        bytes memory signatures
    ) external {
        // VULNERABLE: Gnosis-style but no signature validation
        (bool success, ) = to.call{value: value}(data);
        require(success);
    }
}

contract VariationTimelockStyle {
    mapping(bytes32 => bool) public queued;
    address[] public admins;
    address[] public signers; // Add multisig indicator

    // VAR3: Timelock-style execution with signatures
    function executeQueuedTransaction(
        bytes32 txHash,
        address target,
        bytes memory data,
        bytes[] memory adminSignatures
    ) external {
        // VULNERABLE: Timelock pattern but no signature validation
        require(queued[txHash], "Not queued");
        require(adminSignatures.length >= 3, "Need 3 admin sigs");

        (bool success, ) = target.call(data);
        require(success);
    }
}

contract VariationGovernorStyle {
    struct Proposal {
        address target;
        bytes data;
        bool executed;
    }

    mapping(uint256 => Proposal) public proposals;
    address[] public voters;
    address[] public signers; // Add multisig indicator

    // VAR4: Governor-style execution
    function executeProposal(
        uint256 proposalId,
        bytes[] memory voterSignatures
    ) external {
        // VULNERABLE: Governor pattern but no signature validation
        require(voterSignatures.length >= 5, "Need 5 votes");

        Proposal storage p = proposals[proposalId];
        require(!p.executed, "Already executed");

        (bool success, ) = p.target.call(p.data);
        require(success);
        p.executed = true;
    }
}

contract VariationCompactFormat {
    mapping(address => bool) public authorized;
    address[] public owners; // Add multisig indicator

    // VAR5: Uses compact signature format (65 bytes)
    function executeCompact(
        address to,
        bytes memory data,
        bytes calldata compactSig
    ) external {
        // VULNERABLE: Compact format but no validation
        require(compactSig.length == 65, "Invalid compact sig");

        (bool success, ) = to.call(data);
        require(success);
    }
}

contract VariationEIP2098Format {
    address[] public signers;

    // VAR6: Uses EIP-2098 compact format (64 bytes)
    function executeEIP2098Compact(
        address to,
        bytes memory data,
        bytes32 r,
        bytes32 vs
    ) external {
        // VULNERABLE: EIP-2098 format but no validation
        // vs encodes both v and s
        (bool success, ) = to.call(data);
        require(success);
    }
}
