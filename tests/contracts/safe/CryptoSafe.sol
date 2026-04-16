// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title CryptoSafe
 * @notice Safe implementations of cryptographic patterns.
 * @dev These contracts demonstrate proper signature validation and crypto usage.
 */

/**
 * @title SignatureValidationSafe
 * @notice Safe: Complete signature validation
 */
contract SignatureValidationSafe {
    mapping(address => uint256) public nonces;
    mapping(bytes32 => bool) public usedSignatures;

    bytes32 public immutable DOMAIN_SEPARATOR;
    bytes32 public constant PERMIT_TYPEHASH = keccak256(
        "Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)"
    );

    constructor() {
        DOMAIN_SEPARATOR = keccak256(
            abi.encode(
                keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
                keccak256(bytes("SafeContract")),
                keccak256(bytes("1")),
                block.chainid,
                address(this)
            )
        );
    }

    // SAFE: Complete signature validation
    function permitWithFullValidation(
        address owner,
        address spender,
        uint256 value,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        // 1. Deadline check
        require(block.timestamp <= deadline, "Signature expired");

        // 2. Create digest
        bytes32 structHash = keccak256(
            abi.encode(
                PERMIT_TYPEHASH,
                owner,
                spender,
                value,
                nonces[owner]++,
                deadline
            )
        );
        bytes32 digest = keccak256(
            abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, structHash)
        );

        // 3. Replay protection - mark signature as used
        require(!usedSignatures[digest], "Signature already used");
        usedSignatures[digest] = true;

        // 4. Recover signer
        address recoveredAddress = ecrecover(digest, v, r, s);

        // 5. Zero address check
        require(recoveredAddress != address(0), "Invalid signature");

        // 6. Signer check
        require(recoveredAddress == owner, "Unauthorized");

        // 7. Signature malleability check (s value)
        require(uint256(s) <= 0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0, "Invalid s value");

        // 8. V value check
        require(v == 27 || v == 28, "Invalid v value");
    }
}

/**
 * @title EIP712Safe
 * @notice Safe: Complete EIP-712 implementation
 */
contract EIP712Safe {
    bytes32 public immutable DOMAIN_SEPARATOR;
    string public name;
    string public version;

    constructor(string memory _name, string memory _version) {
        name = _name;
        version = _version;
        DOMAIN_SEPARATOR = _buildDomainSeparator();
    }

    function _buildDomainSeparator() internal view returns (bytes32) {
        return keccak256(
            abi.encode(
                keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
                keccak256(bytes(name)),
                keccak256(bytes(version)),
                block.chainid, // SAFE: Uses chainId
                address(this)
            )
        );
    }

    // SAFE: Verify domain separator on chain ID change (for forks)
    function getDomainSeparator() public view returns (bytes32) {
        return _buildDomainSeparator();
    }

    function verifyTypedData(
        bytes32 structHash,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) public view returns (address) {
        bytes32 digest = keccak256(
            abi.encodePacked("\x19\x01", getDomainSeparator(), structHash)
        );
        return ecrecover(digest, v, r, s);
    }
}

/**
 * @title NonceManagementSafe
 * @notice Safe: Proper nonce management for replay protection
 */
contract NonceManagementSafe {
    mapping(address => uint256) public nonces;

    // SAFE: Increment nonce before use
    function useNonce(address account) internal returns (uint256) {
        return nonces[account]++;
    }

    // SAFE: Verify nonce matches expected
    function verifyNonce(address account, uint256 expectedNonce) internal view {
        require(nonces[account] == expectedNonce, "Invalid nonce");
    }

    // SAFE: Allow users to invalidate old signatures by incrementing nonce
    function incrementNonce() external {
        nonces[msg.sender]++;
    }
}

/**
 * @title ZeroAddressCheckSafe
 * @notice Safe: Always check for zero address from ecrecover
 */
contract ZeroAddressCheckSafe {
    // SAFE: Check recovered address is not zero
    function verifySignature(
        bytes32 hash,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) public pure returns (address) {
        address signer = ecrecover(hash, v, r, s);
        require(signer != address(0), "Invalid signature - zero address");
        return signer;
    }

    // SAFE: Using OpenZeppelin ECDSA-style recovery
    function recoverSigner(
        bytes32 hash,
        bytes memory signature
    ) public pure returns (address) {
        require(signature.length == 65, "Invalid signature length");

        bytes32 r;
        bytes32 s;
        uint8 v;

        assembly {
            r := mload(add(signature, 32))
            s := mload(add(signature, 64))
            v := byte(0, mload(add(signature, 96)))
        }

        // Normalize v
        if (v < 27) {
            v += 27;
        }

        require(v == 27 || v == 28, "Invalid v value");

        address signer = ecrecover(hash, v, r, s);
        require(signer != address(0), "Invalid signature");
        return signer;
    }
}

/**
 * @title MalleabilityProtectionSafe
 * @notice Safe: Protect against signature malleability
 */
contract MalleabilityProtectionSafe {
    // Half of the secp256k1 curve order
    bytes32 private constant HALF_CURVE_ORDER =
        0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0;

    // SAFE: Check s is in lower half of curve
    function verifyNonMalleable(
        bytes32 hash,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) public pure returns (address) {
        // Malleability check
        require(uint256(s) <= uint256(HALF_CURVE_ORDER), "Malleable signature");

        // V check
        require(v == 27 || v == 28, "Invalid v");

        address signer = ecrecover(hash, v, r, s);
        require(signer != address(0), "Invalid signature");
        return signer;
    }
}

/**
 * @title DeadlineCheckSafe
 * @notice Safe: Always check signature deadline
 */
contract DeadlineCheckSafe {
    struct SignedMessage {
        address signer;
        uint256 deadline;
        bytes data;
    }

    // SAFE: Always check deadline
    function processSignedMessage(
        SignedMessage calldata message,
        bytes calldata signature
    ) external view {
        require(block.timestamp <= message.deadline, "Signature expired");
        // ... process message
    }

    // SAFE: Reasonable deadline bounds
    function validateDeadline(uint256 deadline) public view {
        require(deadline > block.timestamp, "Deadline in past");
        require(deadline <= block.timestamp + 365 days, "Deadline too far");
    }
}

/**
 * @title ChainIdCheckSafe
 * @notice Safe: Include chain ID in signed data
 */
contract ChainIdCheckSafe {
    uint256 public immutable deploymentChainId;

    constructor() {
        deploymentChainId = block.chainid;
    }

    // SAFE: Verify chain ID hasn't changed (fork protection)
    modifier checkChainId() {
        require(block.chainid == deploymentChainId, "Chain ID mismatch");
        _;
    }

    // SAFE: Include chain ID in message hash
    function getMessageHash(
        address user,
        uint256 amount,
        uint256 nonce
    ) public view returns (bytes32) {
        return keccak256(abi.encodePacked(
            user,
            amount,
            nonce,
            block.chainid, // SAFE: Chain ID included
            address(this)
        ));
    }
}

/**
 * @title PermitSafe
 * @notice Safe: Complete ERC-2612 permit implementation
 */
contract PermitSafe {
    mapping(address => uint256) public nonces;
    mapping(address => mapping(address => uint256)) public allowance;

    bytes32 public immutable DOMAIN_SEPARATOR;
    bytes32 public constant PERMIT_TYPEHASH = keccak256(
        "Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)"
    );

    constructor() {
        DOMAIN_SEPARATOR = keccak256(
            abi.encode(
                keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
                keccak256("Token"),
                keccak256("1"),
                block.chainid,
                address(this)
            )
        );
    }

    // SAFE: Complete permit with all checks
    function permit(
        address owner,
        address spender,
        uint256 value,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        // Deadline
        require(deadline >= block.timestamp, "PERMIT_DEADLINE_EXPIRED");

        // S malleability
        require(uint256(s) <= 0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0, "INVALID_S");

        // V value
        require(v == 27 || v == 28, "INVALID_V");

        // Compute digest
        bytes32 digest = keccak256(
            abi.encodePacked(
                "\x19\x01",
                DOMAIN_SEPARATOR,
                keccak256(abi.encode(PERMIT_TYPEHASH, owner, spender, value, nonces[owner]++, deadline))
            )
        );

        // Recover
        address recoveredAddress = ecrecover(digest, v, r, s);

        // Checks
        require(recoveredAddress != address(0), "INVALID_SIGNER");
        require(recoveredAddress == owner, "INVALID_SIGNER");

        // Set allowance
        allowance[owner][spender] = value;
    }
}
