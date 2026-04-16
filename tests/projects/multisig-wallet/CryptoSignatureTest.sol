// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title CryptoSignatureTest
 * @notice Test contract for crypto-001: Insecure Signature Validation pattern
 * @dev Tests ecrecover usage with various missing checks
 */

// =============================================================================
// TRUE POSITIVES: Missing Critical Checks
// =============================================================================

contract MissingZeroAddressCheck {
    address public owner;

    // TP: ecrecover without zero address check
    function executeWithSignature(
        address target,
        bytes memory data,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        bytes32 hash = keccak256(abi.encodePacked(target, data));
        address signer = ecrecover(hash, v, r, s);
        // VULNERABLE: No check for address(0)
        require(signer == owner, "Not owner");
        (bool success, ) = target.call(data);
        require(success);
    }
}

contract MissingSMalleabilityCheck {
    address public owner;
    mapping(address => uint256) public nonces;

    // TP: ecrecover without s-value malleability check
    function permit(
        address spender,
        uint256 value,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        require(block.timestamp <= deadline, "Expired");

        bytes32 hash = keccak256(abi.encodePacked(
            spender,
            value,
            nonces[msg.sender]++,
            block.chainid
        ));

        address signer = ecrecover(hash, v, r, s);
        require(signer != address(0), "Invalid signature");
        require(signer == owner, "Not owner");
        // VULNERABLE: No s-value malleability check
        // Same message can have two valid signatures: (v,r,s) and (v',r,s')
    }
}

contract MissingVValueCheck {
    address public owner;
    mapping(address => uint256) public nonces;

    // TP: ecrecover without v-value validation
    function executeTransaction(
        address target,
        bytes memory data,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        bytes32 hash = keccak256(abi.encodePacked(
            target,
            data,
            nonces[msg.sender]++
        ));

        address signer = ecrecover(hash, v, r, s);
        require(signer != address(0), "Invalid signature");
        // VULNERABLE: No v-value check (should be 27 or 28)
        require(signer == owner, "Not owner");

        (bool success, ) = target.call(data);
        require(success);
    }
}

contract MissingNonceProtection {
    address public owner;

    // TP: ecrecover without nonce-based replay protection
    function transferWithSignature(
        address to,
        uint256 amount,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        bytes32 hash = keccak256(abi.encodePacked(to, amount));

        address signer = ecrecover(hash, v, r, s);
        require(signer != address(0), "Invalid signature");
        require(signer == owner, "Not owner");
        // VULNERABLE: No nonce tracking - signature can be replayed infinitely

        payable(to).transfer(amount);
    }
}

contract MissingDeadlineCheck {
    address public owner;
    mapping(address => uint256) public nonces;

    // TP: ecrecover without deadline parameter
    function approveWithSignature(
        address spender,
        uint256 value,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        bytes32 hash = keccak256(abi.encodePacked(
            spender,
            value,
            nonces[msg.sender]++
        ));

        address signer = ecrecover(hash, v, r, s);
        require(signer != address(0), "Invalid signature");
        require(signer == owner, "Not owner");
        // VULNERABLE: No deadline - signature valid forever
    }
}

contract MissingChainIdCheck {
    address public owner;
    mapping(address => uint256) public nonces;

    // TP: ecrecover without chain ID in hash
    function executeOnChain(
        address target,
        bytes memory data,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        require(block.timestamp <= deadline, "Expired");

        bytes32 hash = keccak256(abi.encodePacked(
            target,
            data,
            nonces[msg.sender]++
            // VULNERABLE: No block.chainid - can be replayed on other chains
        ));

        address signer = ecrecover(hash, v, r, s);
        require(signer != address(0), "Invalid signature");
        require(signer == owner, "Not owner");

        (bool success, ) = target.call(data);
        require(success);
    }
}

contract MultipleVulnerabilities {
    address public owner;

    // TP: Multiple missing checks
    function executeMultiVuln(
        address target,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        bytes32 hash = keccak256(abi.encodePacked(target));
        address signer = ecrecover(hash, v, r, s);
        // VULNERABLE: Missing ALL checks
        // - No zero address check
        // - No s-value check
        // - No v-value check
        // - No nonce
        // - No deadline
        // - No chain ID
        require(signer == owner);
        (bool success, ) = target.call("");
        require(success);
    }
}

// =============================================================================
// TRUE NEGATIVES: Safe Implementations
// =============================================================================

contract SafeWithComprehensiveChecks {
    address public owner;
    mapping(address => uint256) public nonces;

    // TN: All checks implemented manually
    function executeSafe(
        address target,
        bytes memory data,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        // Deadline check
        require(block.timestamp <= deadline, "Expired");

        // V-value validation
        require(v == 27 || v == 28, "Invalid v");

        // S-value malleability check
        require(
            uint256(s) <= 0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0,
            "Invalid s"
        );

        // Build hash with nonce and chain ID
        bytes32 hash = keccak256(abi.encodePacked(
            target,
            data,
            nonces[msg.sender]++, // Replay protection
            block.chainid // Cross-chain protection
        ));

        // Recover signer
        address signer = ecrecover(hash, v, r, s);

        // Zero address check
        require(signer != address(0), "Invalid signature");
        require(signer == owner, "Not owner");

        (bool success, ) = target.call(data);
        require(success);
    }
}

// TN: Using OpenZeppelin ECDSA library (detected by has_signature_validity_checks)
// This would be flagged as TN if ECDSA.recover is properly detected
contract SafeWithECDSA {
    address public owner;
    mapping(address => uint256) public nonces;

    // TN: OpenZeppelin ECDSA library handles all checks
    function executeWithECDSA(
        address target,
        bytes memory data,
        uint256 deadline,
        bytes memory signature
    ) external {
        require(block.timestamp <= deadline, "Expired");

        bytes32 hash = keccak256(abi.encodePacked(
            target,
            data,
            nonces[msg.sender]++,
            block.chainid
        ));

        bytes32 ethSignedHash = keccak256(abi.encodePacked(
            "\x19Ethereum Signed Message:\n32",
            hash
        ));

        // OpenZeppelin ECDSA.recover includes:
        // - Zero address check
        // - S-value malleability check
        // - V-value validation
        address signer = recoverSigner(ethSignedHash, signature);

        require(signer == owner, "Not owner");
        (bool success, ) = target.call(data);
        require(success);
    }

    function recoverSigner(bytes32 hash, bytes memory signature) internal pure returns (address) {
        // Simplified ECDSA.recover logic
        bytes32 r;
        bytes32 s;
        uint8 v;

        if (signature.length == 65) {
            assembly {
                r := mload(add(signature, 32))
                s := mload(add(signature, 64))
                v := byte(0, mload(add(signature, 96)))
            }
        }

        require(v == 27 || v == 28, "Invalid v");
        require(
            uint256(s) <= 0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0,
            "Invalid s"
        );

        address signer = ecrecover(hash, v, r, s);
        require(signer != address(0), "Invalid signature");

        return signer;
    }
}

contract SafeViewFunction {
    // TN: View function - no state changes
    function verifySignatureView(
        bytes32 hash,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external view returns (address) {
        // Even without checks, view functions are lower risk
        return ecrecover(hash, v, r, s);
    }
}

contract SafePureFunction {
    // TN: Pure function - no state access
    function recoverSignerPure(
        bytes32 hash,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external pure returns (address) {
        return ecrecover(hash, v, r, s);
    }
}

contract SafeInternalFunction {
    address public owner;

    // TN: Internal function - not externally callable
    function _recoverInternal(
        bytes32 hash,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) internal view returns (address) {
        return ecrecover(hash, v, r, s);
    }

    // Public wrapper with proper checks
    function executeWithInternal(
        address target,
        bytes memory data,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        bytes32 hash = keccak256(abi.encodePacked(target, data));
        address signer = _recoverInternal(hash, v, r, s);
        require(signer != address(0), "Invalid");
        require(signer == owner, "Not owner");
        (bool success, ) = target.call(data);
        require(success);
    }
}

// =============================================================================
// EDGE CASES
// =============================================================================

contract EdgePartialChecks {
    address public owner;
    mapping(address => uint256) public nonces;

    // EDGE: Has some checks but still vulnerable
    function executePartialChecks(
        address target,
        bytes memory data,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        require(block.timestamp <= deadline, "Expired"); // Has deadline

        bytes32 hash = keccak256(abi.encodePacked(
            target,
            data,
            nonces[msg.sender]++ // Has nonce
        ));

        address signer = ecrecover(hash, v, r, s);
        require(signer != address(0), "Invalid signature"); // Has zero check
        require(signer == owner, "Not owner");

        // VULNERABLE: Still missing s-value, v-value, and chain ID checks
        (bool success, ) = target.call(data);
        require(success);
    }
}

contract EdgeZeroAddressOwner {
    address public owner; // Uninitialized - defaults to address(0)

    // EDGE: Critical when owner is address(0)
    function executeUninitialized(
        address target,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        bytes32 hash = keccak256(abi.encodePacked(target));
        address signer = ecrecover(hash, v, r, s);
        // CRITICAL: If owner is address(0), invalid signatures pass!
        require(signer == owner, "Not owner");
        (bool success, ) = target.call("");
        require(success);
    }
}

contract EdgeConsumedSignatureMapping {
    address public owner;
    mapping(bytes32 => bool) public consumedSignatures;

    // EDGE: Uses signature hash tracking instead of nonce
    function executeWithHashTracking(
        address target,
        bytes memory data,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        bytes32 hash = keccak256(abi.encodePacked(target, data));
        bytes32 sigHash = keccak256(abi.encodePacked(v, r, s));

        require(!consumedSignatures[sigHash], "Signature already used");

        address signer = ecrecover(hash, v, r, s);
        require(signer != address(0), "Invalid signature");
        require(signer == owner, "Not owner");

        consumedSignatures[sigHash] = true;

        // Still vulnerable to s-malleability and missing other checks
        (bool success, ) = target.call(data);
        require(success);
    }
}

// =============================================================================
// VARIATION TESTING: Different Implementation Styles
// =============================================================================

contract VariationEIP712Style {
    address public owner;
    mapping(address => uint256) public nonces;

    bytes32 public constant DOMAIN_TYPEHASH = keccak256(
        "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
    );

    bytes32 public constant PERMIT_TYPEHASH = keccak256(
        "Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)"
    );

    bytes32 public DOMAIN_SEPARATOR;

    constructor() {
        DOMAIN_SEPARATOR = keccak256(abi.encode(
            DOMAIN_TYPEHASH,
            keccak256(bytes("MyToken")),
            keccak256(bytes("1")),
            block.chainid,
            address(this)
        ));
    }

    // TP: EIP-712 but missing checks
    function permitEIP712Vulnerable(
        address sender,
        address spender,
        uint256 value,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        require(block.timestamp <= deadline, "Expired");

        bytes32 structHash = keccak256(abi.encode(
            PERMIT_TYPEHASH,
            sender,
            spender,
            value,
            nonces[sender]++,
            deadline
        ));

        bytes32 hash = keccak256(abi.encodePacked(
            "\x19\x01",
            DOMAIN_SEPARATOR,
            structHash
        ));

        address signer = ecrecover(hash, v, r, s);
        // VULNERABLE: No zero address, s-value, or v-value checks
        require(signer == sender, "Invalid signature");
    }
}

contract VariationCompactSignature {
    address public owner;

    // TP: Compact 65-byte signature format
    function executeCompact(
        address target,
        bytes memory data,
        bytes memory signature
    ) external {
        require(signature.length == 65, "Invalid signature length");

        bytes32 hash = keccak256(abi.encodePacked(target, data));

        bytes32 r;
        bytes32 s;
        uint8 v;

        assembly {
            r := mload(add(signature, 32))
            s := mload(add(signature, 64))
            v := byte(0, mload(add(signature, 96)))
        }

        address signer = ecrecover(hash, v, r, s);
        // VULNERABLE: Missing all checks
        require(signer == owner, "Not owner");

        (bool success, ) = target.call(data);
        require(success);
    }
}

contract VariationEIP2098Format {
    address public owner;

    // TP: EIP-2098 compact format (r + vs combined)
    function executeEIP2098(
        address target,
        bytes memory data,
        bytes32 r,
        bytes32 vs
    ) external {
        bytes32 hash = keccak256(abi.encodePacked(target, data));

        // Extract v and s from vs
        bytes32 s = vs & 0x7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff;
        uint8 v = uint8((uint256(vs) >> 255) + 27);

        address signer = ecrecover(hash, v, r, s);
        // VULNERABLE: Missing checks
        require(signer == owner, "Not owner");

        (bool success, ) = target.call(data);
        require(success);
    }
}

contract VariationMultipleSigners {
    mapping(address => bool) public signers;

    // TP: Multiple signers pattern
    function executeMultiSig(
        address target,
        bytes memory data,
        uint8[] memory v,
        bytes32[] memory r,
        bytes32[] memory s
    ) external {
        require(v.length >= 2, "Need 2 signatures");
        require(v.length == r.length && r.length == s.length, "Length mismatch");

        bytes32 hash = keccak256(abi.encodePacked(target, data));

        for (uint i = 0; i < v.length; i++) {
            address signer = ecrecover(hash, v[i], r[i], s[i]);
            // VULNERABLE: Missing all checks for each signature
            require(signers[signer], "Not a signer");
        }

        (bool success, ) = target.call(data);
        require(success);
    }
}

contract VariationDifferentNaming {
    address public controller; // Different from "owner"
    mapping(address => uint256) public counters; // Different from "nonces"

    // TP: Different naming conventions
    function authorizeAction(
        address destination,
        bytes memory payload,
        uint256 expiry,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        require(block.timestamp <= expiry, "Expired");

        bytes32 digest = keccak256(abi.encodePacked(
            destination,
            payload,
            counters[msg.sender]++,
            block.chainid
        ));

        address authenticator = ecrecover(digest, v, r, s);
        // VULNERABLE: Still missing checks despite different naming
        require(authenticator != address(0), "Invalid");
        require(authenticator == controller, "Unauthorized");

        (bool success, ) = destination.call(payload);
        require(success);
    }
}

contract VariationMetaTransaction {
    mapping(address => uint256) public nonces;

    // TP: Meta-transaction pattern (common in gas abstraction)
    function executeMetaTx(
        address from,
        address to,
        uint256 value,
        bytes memory data,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        bytes32 hash = keccak256(abi.encodePacked(
            from,
            to,
            value,
            data,
            nonces[from]++
        ));

        address signer = ecrecover(hash, v, r, s);
        // VULNERABLE: Missing zero address, s, v, and chain ID checks
        require(signer == from, "Invalid signature");

        (bool success, ) = to.call{value: value}(data);
        require(success);
    }
}
