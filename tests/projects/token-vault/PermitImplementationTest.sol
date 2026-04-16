// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title PermitImplementationTest
 * @notice Comprehensive test contract for crypto-002: Incomplete EIP-2612 Permit Implementation
 *
 * Tests cover:
 * - TRUE POSITIVES: Permit functions missing critical checks (deadline, nonce, domain separator, ecrecover)
 * - TRUE NEGATIVES: Complete permit implementations
 * - EDGE CASES: View permit functions, internal helpers
 * - VARIATIONS: Different EIP-2612 implementation styles
 */

// =============================================================================
// INTERFACES & HELPERS
// =============================================================================

interface IERC20Basic {
    function approve(address spender, uint256 amount) external returns (bool);
    function allowance(address owner, address spender) external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
}

library ECDSAHelper {
    /**
     * @dev Recover signer from signature
     */
    function recover(bytes32 hash, uint8 v, bytes32 r, bytes32 s) internal pure returns (address) {
        // Check s-value for malleability
        if (uint256(s) > 0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0) {
            return address(0);
        }

        // Check v-value
        if (v != 27 && v != 28) {
            return address(0);
        }

        address signer = ecrecover(hash, v, r, s);
        require(signer != address(0), "ECDSA: invalid signature");

        return signer;
    }
}

// Minimal ERC20 base for testing
abstract contract ERC20Base is IERC20Basic {
    mapping(address => uint256) internal _balances;
    mapping(address => mapping(address => uint256)) internal _allowances;

    function approve(address spender, uint256 amount) external virtual override returns (bool) {
        _approve(msg.sender, spender, amount);
        return true;
    }

    function _approve(address owner, address spender, uint256 amount) internal virtual {
        _allowances[owner][spender] = amount;
    }

    function allowance(address owner, address spender) external view override returns (uint256) {
        return _allowances[owner][spender];
    }

    function balanceOf(address account) external view override returns (uint256) {
        return _balances[account];
    }
}

// =============================================================================
// TRUE POSITIVES: Incomplete Permit Implementations
// =============================================================================

contract PermitMissingDeadline is ERC20Base {
    bytes32 public constant PERMIT_TYPEHASH = keccak256(
        "Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)"
    );
    bytes32 public immutable DOMAIN_SEPARATOR;
    mapping(address => uint256) public nonces;

    constructor() {
        DOMAIN_SEPARATOR = keccak256(abi.encode(
            keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
            keccak256(bytes("Token")),
            keccak256(bytes("1")),
            block.chainid,
            address(this)
        ));
    }

    // TP: Missing deadline check - allows stale signature attacks
    function permit(
        address owner,
        address spender,
        uint256 value,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        // VULNERABILITY: No deadline check (should have: require(block.timestamp <= deadline))

        bytes32 structHash = keccak256(abi.encode(
            PERMIT_TYPEHASH,
            owner,
            spender,
            value,
            nonces[owner]++,
            deadline
        ));

        bytes32 hash = keccak256(abi.encodePacked(
            "\x19\x01",
            DOMAIN_SEPARATOR,
            structHash
        ));

        address signer = ECDSAHelper.recover(hash, v, r, s);
        require(signer == owner, "Invalid signature");

        _approve(owner, spender, value);
    }
}

contract PermitMissingNonce is ERC20Base {
    bytes32 public constant PERMIT_TYPEHASH = keccak256(
        "Permit(address owner,address spender,uint256 value,uint256 deadline)"
    );
    bytes32 public immutable DOMAIN_SEPARATOR;

    constructor() {
        DOMAIN_SEPARATOR = keccak256(abi.encode(
            keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
            keccak256(bytes("Token")),
            keccak256(bytes("1")),
            block.chainid,
            address(this)
        ));
    }

    // TP: Missing nonce management - allows infinite replay attacks
    function permit(
        address owner,
        address spender,
        uint256 value,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        require(block.timestamp <= deadline, "Expired");

        // VULNERABILITY: No nonce mapping or increment (allows signature replay)
        bytes32 structHash = keccak256(abi.encode(
            PERMIT_TYPEHASH,
            owner,
            spender,
            value,
            deadline
        ));

        bytes32 hash = keccak256(abi.encodePacked(
            "\x19\x01",
            DOMAIN_SEPARATOR,
            structHash
        ));

        address signer = ECDSAHelper.recover(hash, v, r, s);
        require(signer == owner, "Invalid signature");

        _approve(owner, spender, value);
    }
}

contract PermitMissingDomainSeparator is ERC20Base {
    bytes32 public constant PERMIT_TYPEHASH = keccak256(
        "Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)"
    );
    mapping(address => uint256) public nonces;

    // TP: Missing domain separator - allows cross-contract/cross-chain replay
    function permit(
        address owner,
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
            owner,
            spender,
            value,
            nonces[owner]++,
            deadline
        ));

        // VULNERABILITY: No domain separator used (allows cross-contract replay)
        bytes32 hash = keccak256(abi.encode(structHash));

        address signer = ECDSAHelper.recover(hash, v, r, s);
        require(signer == owner, "Invalid signature");

        _approve(owner, spender, value);
    }
}

contract PermitMissingSignatureVerification is ERC20Base {
    bytes32 public immutable DOMAIN_SEPARATOR;
    mapping(address => uint256) public nonces;

    constructor() {
        DOMAIN_SEPARATOR = keccak256(abi.encode(
            keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
            keccak256(bytes("Token")),
            keccak256(bytes("1")),
            block.chainid,
            address(this)
        ));
    }

    // TP: Missing signature verification - critical authorization bypass
    function permit(
        address owner,
        address spender,
        uint256 value,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        require(block.timestamp <= deadline, "Expired");

        nonces[owner]++;

        // VULNERABILITY: No ecrecover call (anyone can grant approvals for anyone)
        _approve(owner, spender, value);
    }
}

contract PermitMultipleMissing is ERC20Base {
    // TP: Missing ALL checks - extremely vulnerable
    function permit(
        address owner,
        address spender,
        uint256 value,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        // VULNERABILITY: Missing deadline, nonce, domain separator, signature verification
        _approve(owner, spender, value);
    }
}

contract PermitNonStandardNaming is ERC20Base {
    // TP: Different function name but still permit-like behavior, missing all checks
    function grantApprovalWithSignature(
        address owner,
        address spender,
        uint256 value,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        // VULNERABILITY: Missing all EIP-2612 checks
        _approve(owner, spender, value);
    }

    // TP: Another variant
    function approveViaSignature(
        address owner,
        address spender,
        uint256 value,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        // VULNERABILITY: Missing all EIP-2612 checks
        _approve(owner, spender, value);
    }
}

contract PermitHardcodedNonce is ERC20Base {
    bytes32 public constant PERMIT_TYPEHASH = keccak256(
        "Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)"
    );
    bytes32 public immutable DOMAIN_SEPARATOR;

    constructor() {
        DOMAIN_SEPARATOR = keccak256(abi.encode(
            keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
            keccak256(bytes("Token")),
            keccak256(bytes("1")),
            block.chainid,
            address(this)
        ));
    }

    // TP: Hardcoded nonce - allows replay
    function permit(
        address owner,
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
            owner,
            spender,
            value,
            0, // VULNERABILITY: Hardcoded nonce instead of nonces[owner]++
            deadline
        ));

        bytes32 hash = keccak256(abi.encodePacked(
            "\x19\x01",
            DOMAIN_SEPARATOR,
            structHash
        ));

        address signer = ECDSAHelper.recover(hash, v, r, s);
        require(signer == owner, "Invalid signature");

        _approve(owner, spender, value);
    }
}

contract PermitNonceNotIncremented is ERC20Base {
    bytes32 public constant PERMIT_TYPEHASH = keccak256(
        "Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)"
    );
    bytes32 public immutable DOMAIN_SEPARATOR;
    mapping(address => uint256) public nonces;

    constructor() {
        DOMAIN_SEPARATOR = keccak256(abi.encode(
            keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
            keccak256(bytes("Token")),
            keccak256(bytes("1")),
            block.chainid,
            address(this)
        ));
    }

    // TP: Nonce read but not incremented
    function permit(
        address owner,
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
            owner,
            spender,
            value,
            nonces[owner], // VULNERABILITY: Nonce read but NOT incremented (allows replay)
            deadline
        ));

        bytes32 hash = keccak256(abi.encodePacked(
            "\x19\x01",
            DOMAIN_SEPARATOR,
            structHash
        ));

        address signer = ECDSAHelper.recover(hash, v, r, s);
        require(signer == owner, "Invalid signature");

        _approve(owner, spender, value);
    }
}

contract PermitManualEcrecover is ERC20Base {
    bytes32 public immutable DOMAIN_SEPARATOR;

    constructor() {
        DOMAIN_SEPARATOR = keccak256(abi.encode(
            keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
            keccak256(bytes("Token")),
            keccak256(bytes("1")),
            block.chainid,
            address(this)
        ));
    }

    // TP: Missing nonce even with manual ecrecover
    function permit(
        address owner,
        address spender,
        uint256 value,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        require(block.timestamp <= deadline, "Expired");

        bytes32 structHash = keccak256(abi.encode(
            keccak256("Permit(address owner,address spender,uint256 value,uint256 deadline)"),
            owner,
            spender,
            value,
            deadline
        ));

        bytes32 hash = keccak256(abi.encodePacked(
            "\x19\x01",
            DOMAIN_SEPARATOR,
            structHash
        ));

        // VULNERABILITY: Manual ecrecover but missing nonce management
        address signer = ecrecover(hash, v, r, s);
        require(signer != address(0), "Invalid signature");
        require(signer == owner, "Invalid signer");

        _approve(owner, spender, value);
    }
}

// =============================================================================
// TRUE NEGATIVES: Complete and Safe Permit Implementations
// =============================================================================

contract PermitSafeManual is ERC20Base {
    bytes32 public constant DOMAIN_TYPEHASH = keccak256(
        "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
    );

    bytes32 public constant PERMIT_TYPEHASH = keccak256(
        "Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)"
    );

    bytes32 public immutable DOMAIN_SEPARATOR;
    mapping(address => uint256) public nonces;

    constructor() {
        DOMAIN_SEPARATOR = keccak256(abi.encode(
            DOMAIN_TYPEHASH,
            keccak256(bytes("SafeToken")),
            keccak256(bytes("1")),
            block.chainid,
            address(this)
        ));
    }

    // TN: Complete implementation with all required checks
    function permit(
        address owner,
        address spender,
        uint256 value,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        // CHECK 1: Deadline validation
        require(block.timestamp <= deadline, "ERC20Permit: expired deadline");

        // CHECK 2: Nonce management with increment
        bytes32 structHash = keccak256(abi.encode(
            PERMIT_TYPEHASH,
            owner,
            spender,
            value,
            nonces[owner]++,
            deadline
        ));

        // CHECK 3: Domain separator for cross-contract/cross-chain protection
        bytes32 hash = keccak256(abi.encodePacked(
            "\x19\x01",
            DOMAIN_SEPARATOR,
            structHash
        ));

        // CHECK 4: Signature verification with zero address check
        address signer = ECDSAHelper.recover(hash, v, r, s);
        require(signer == owner, "ERC20Permit: invalid signature");

        _approve(owner, spender, value);
    }
}

contract PermitSafeWithTryCatch is ERC20Base {
    bytes32 public constant PERMIT_TYPEHASH = keccak256(
        "Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)"
    );
    bytes32 public immutable DOMAIN_SEPARATOR;
    mapping(address => uint256) public nonces;

    constructor() {
        DOMAIN_SEPARATOR = keccak256(abi.encode(
            keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
            keccak256(bytes("SafeToken")),
            keccak256(bytes("1")),
            block.chainid,
            address(this)
        ));
    }

    // TN: Complete implementation with defensive programming
    function permit(
        address owner,
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
            owner,
            spender,
            value,
            nonces[owner]++,
            deadline
        ));

        bytes32 hash = keccak256(abi.encodePacked(
            "\x19\x01",
            DOMAIN_SEPARATOR,
            structHash
        ));

        address signer = ECDSAHelper.recover(hash, v, r, s);
        require(signer == owner, "Invalid signature");
        _approve(owner, spender, value);
    }
}

// =============================================================================
// EDGE CASES
// =============================================================================

contract PermitEdgeCases is ERC20Base {
    bytes32 public immutable DOMAIN_SEPARATOR;
    mapping(address => uint256) public nonces;

    constructor() {
        DOMAIN_SEPARATOR = keccak256(abi.encode(
            keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
            keccak256(bytes("Token")),
            keccak256(bytes("1")),
            block.chainid,
            address(this)
        ));
    }

    // Edge: View function - should NOT be flagged (no state changes)
    function viewPermitHash(
        address owner,
        address spender,
        uint256 value,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external view returns (bytes32) {
        bytes32 structHash = keccak256(abi.encode(
            keccak256("Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)"),
            owner,
            spender,
            value,
            nonces[owner],
            deadline
        ));

        return keccak256(abi.encodePacked(
            "\x19\x01",
            DOMAIN_SEPARATOR,
            structHash
        ));
    }

    // Edge: Internal helper - should NOT be flagged (not externally callable)
    function _internalPermit(
        address owner,
        address spender,
        uint256 value,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) internal {
        // Even though missing checks, internal functions are not exploitable from outside
        _approve(owner, spender, value);
    }

    // Edge: Private helper - should NOT be flagged (not externally callable)
    function _privatePermitHelper(
        address owner,
        address spender,
        uint256 value
    ) private {
        _approve(owner, spender, value);
    }
}

// =============================================================================
// VARIATIONS: Different Implementation Styles
// =============================================================================

contract PermitVariation1_DifferentSignature is ERC20Base {
    // TP: Different parameter order but still permit-like
    function permit(
        uint256 value,
        uint256 deadline,
        address owner,
        address spender,
        bytes32 r,
        bytes32 s,
        uint8 v
    ) external {
        // VULNERABILITY: Missing all checks
        _approve(owner, spender, value);
    }
}

contract PermitVariation2_BytesSignature is ERC20Base {
    // TP: Signature as bytes instead of v,r,s
    function permit(
        address owner,
        address spender,
        uint256 value,
        uint256 deadline,
        bytes memory signature
    ) external {
        // VULNERABILITY: Missing all checks
        _approve(owner, spender, value);
    }
}

contract PermitVariation3_InheritedBase is ERC20Base {
    bytes32 public immutable DOMAIN_SEPARATOR;
    mapping(address => uint256) public nonces;

    constructor() {
        DOMAIN_SEPARATOR = keccak256(abi.encode(
            keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
            keccak256(bytes("Token")),
            keccak256(bytes("1")),
            block.chainid,
            address(this)
        ));
    }

    // TP: Base implementation missing deadline
    function permit(
        address owner,
        address spender,
        uint256 value,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external virtual {
        // VULNERABILITY: Missing deadline check

        bytes32 structHash = keccak256(abi.encode(
            keccak256("Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)"),
            owner,
            spender,
            value,
            nonces[owner]++,
            deadline
        ));

        bytes32 hash = keccak256(abi.encodePacked(
            "\x19\x01",
            DOMAIN_SEPARATOR,
            structHash
        ));

        address signer = ECDSAHelper.recover(hash, v, r, s);
        require(signer == owner, "Invalid signature");

        _approve(owner, spender, value);
    }
}

// TN: Derived contract that adds missing deadline check
contract PermitVariation3_Derived is PermitVariation3_InheritedBase {
    // Override to add deadline check
    function permit(
        address owner,
        address spender,
        uint256 value,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external override {
        // Add missing deadline check
        require(block.timestamp <= deadline, "Expired");

        // Duplicate parent logic with fixed deadline check
        bytes32 structHash = keccak256(abi.encode(
            keccak256("Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)"),
            owner,
            spender,
            value,
            nonces[owner]++,
            deadline
        ));

        bytes32 hash = keccak256(abi.encodePacked(
            "\x19\x01",
            DOMAIN_SEPARATOR,
            structHash
        ));

        address signer = ECDSAHelper.recover(hash, v, r, s);
        require(signer == owner, "Invalid signature");

        _approve(owner, spender, value);
    }
}

contract PermitVariation4_DaiStyle is ERC20Base {
    bytes32 public constant PERMIT_TYPEHASH = keccak256(
        "Permit(address holder,address spender,uint256 nonce,uint256 expiry,bool allowed)"
    );
    bytes32 public immutable DOMAIN_SEPARATOR;
    mapping(address => uint256) public nonces;

    constructor() {
        DOMAIN_SEPARATOR = keccak256(abi.encode(
            keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
            keccak256(bytes("Token")),
            keccak256(bytes("1")),
            block.chainid,
            address(this)
        ));
    }

    // TP: DAI-style permit (uses "holder" instead of "owner", "expiry" instead of "deadline")
    // Still missing deadline check
    function permit(
        address holder,
        address spender,
        uint256 nonce,
        uint256 expiry,
        bool allowed,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        // VULNERABILITY: Missing expiry check (DAI-style deadline)

        bytes32 digest = keccak256(abi.encodePacked(
            "\x19\x01",
            DOMAIN_SEPARATOR,
            keccak256(abi.encode(PERMIT_TYPEHASH, holder, spender, nonce, expiry, allowed))
        ));

        require(holder == ECDSAHelper.recover(digest, v, r, s), "Invalid signature");
        require(nonces[holder]++ == nonce, "Invalid nonce");

        uint256 amount = allowed ? type(uint256).max : 0;
        _approve(holder, spender, amount);
    }
}

// TN: Complete DAI-style implementation
contract PermitVariation4_DaiStyleSafe is ERC20Base {
    bytes32 public constant PERMIT_TYPEHASH = keccak256(
        "Permit(address holder,address spender,uint256 nonce,uint256 expiry,bool allowed)"
    );
    bytes32 public immutable DOMAIN_SEPARATOR;
    mapping(address => uint256) public nonces;

    constructor() {
        DOMAIN_SEPARATOR = keccak256(abi.encode(
            keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
            keccak256(bytes("Token")),
            keccak256(bytes("1")),
            block.chainid,
            address(this)
        ));
    }

    // TN: DAI-style with all checks
    function permit(
        address holder,
        address spender,
        uint256 nonce,
        uint256 expiry,
        bool allowed,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        // Expiry check (DAI-style deadline)
        require(block.timestamp <= expiry, "Expired");

        bytes32 digest = keccak256(abi.encodePacked(
            "\x19\x01",
            DOMAIN_SEPARATOR,
            keccak256(abi.encode(PERMIT_TYPEHASH, holder, spender, nonce, expiry, allowed))
        ));

        require(holder == ECDSAHelper.recover(digest, v, r, s), "Invalid signature");
        require(nonces[holder]++ == nonce, "Invalid nonce");

        uint256 amount = allowed ? type(uint256).max : 0;
        _approve(holder, spender, amount);
    }
}
