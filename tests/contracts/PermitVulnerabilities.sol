// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title PermitVulnerabilities
 * @dev Demonstrates EIP-2612 permit signature vulnerabilities
 *
 * VULNERABILITIES:
 * 1. Signature replay attacks
 * 2. Front-running permit calls
 * 3. Missing deadline validation
 * 4. Signature malleability
 * 5. Missing nonce validation
 * 6. Cross-chain replay
 *
 * EIP-2612: Permit extension for ERC-20
 */

// VULNERABLE: Permit without proper replay protection
contract VulnerablePermitToken {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    mapping(address => uint256) public nonces;

    bytes32 public DOMAIN_SEPARATOR;
    bytes32 public constant PERMIT_TYPEHASH =
        keccak256("Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)");

    constructor() {
        // PROBLEM: DOMAIN_SEPARATOR doesn't include chainId!
        // Signatures valid on one chain can be replayed on another
        DOMAIN_SEPARATOR = keccak256(
            abi.encode(
                keccak256("EIP712Domain(string name,string version,address verifyingContract)"),
                keccak256(bytes("VulnerableToken")),
                keccak256(bytes("1")),
                address(this)
            )
        );
    }

    function permit(
        address owner,
        address spender,
        uint256 value,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) public {
        // PROBLEM: No deadline check!
        // Old signatures can be replayed indefinitely

        bytes32 structHash = keccak256(
            abi.encode(PERMIT_TYPEHASH, owner, spender, value, nonces[owner], deadline)
        );

        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, structHash));

        address signer = ecrecover(digest, v, r, s);
        require(signer == owner, "Invalid signature");
        // PROBLEM: No check for v value malleability (should be 27 or 28)

        nonces[owner]++;
        allowance[owner][spender] = value;
    }
}

// SAFE: Proper permit implementation
contract SafePermitToken {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    mapping(address => uint256) public nonces;

    bytes32 public immutable DOMAIN_SEPARATOR;
    bytes32 public constant PERMIT_TYPEHASH =
        keccak256("Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)");

    constructor() {
        // Proper DOMAIN_SEPARATOR with chainId
        DOMAIN_SEPARATOR = keccak256(
            abi.encode(
                keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
                keccak256(bytes("SafeToken")),
                keccak256(bytes("1")),
                block.chainid,
                address(this)
            )
        );
    }

    function permit(
        address owner,
        address spender,
        uint256 value,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) public {
        // Check deadline
        require(block.timestamp <= deadline, "Permit expired");

        // Check for zero address
        require(owner != address(0), "Invalid owner");

        bytes32 structHash = keccak256(
            abi.encode(PERMIT_TYPEHASH, owner, spender, value, nonces[owner], deadline)
        );

        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, structHash));

        address signer = ecrecover(digest, v, r, s);
        require(signer == owner && signer != address(0), "Invalid signature");

        // Protect against signature malleability
        require(uint256(s) <= 0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0, "Invalid s value");
        require(v == 27 || v == 28, "Invalid v value");

        nonces[owner]++;
        allowance[owner][spender] = value;
    }

    function DOMAIN_SEPARATOR_CURRENT() public view returns (bytes32) {
        // Recompute to handle chain forks
        return keccak256(
            abi.encode(
                keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
                keccak256(bytes("SafeToken")),
                keccak256(bytes("1")),
                block.chainid,
                address(this)
            )
        );
    }
}

// VULNERABLE: Contract using permit without proper checks
contract VulnerablePermitHandler {
    function depositWithPermit(
        address token,
        address owner,
        uint256 amount,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) public {
        // PROBLEM: No validation of deadline or signature freshness
        // Attacker can front-run with old signatures

        VulnerablePermitToken(token).permit(owner, address(this), amount, deadline, v, r, s);

        // PROBLEM: No check if permit actually succeeded
        // PROBLEM: No verification that allowance was set correctly

        // Transfer tokens
        // Could fail if permit was front-run
    }
}

// SAFE: Contract with proper permit handling
contract SafePermitHandler {
    function depositWithPermit(
        address token,
        address owner,
        uint256 amount,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) public {
        // Validate deadline is reasonable
        require(deadline >= block.timestamp, "Deadline in past");
        require(deadline <= block.timestamp + 1 hours, "Deadline too far");

        // Try-catch permit in case it's front-run
        try SafePermitToken(token).permit(owner, address(this), amount, deadline, v, r, s) {
            // Permit succeeded
        } catch {
            // Permit failed - check if allowance already exists
            require(
                SafePermitToken(token).allowance(owner, address(this)) >= amount,
                "Permit failed and no allowance"
            );
        }

        // Verify allowance is sufficient
        require(
            SafePermitToken(token).allowance(owner, address(this)) >= amount,
            "Insufficient allowance"
        );

        // Now safe to transfer
    }
}

// VULNERABLE: Permit signature replay after approval reset
contract VulnerablePermitReplay {
    mapping(address => mapping(address => mapping(bytes32 => bool))) public usedSignatures;

    function permitAndTransfer(
        address token,
        address owner,
        uint256 amount,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) public {
        bytes32 sigHash = keccak256(abi.encodePacked(v, r, s));
        // PROBLEM: Only checks if signature used in THIS contract
        // Signature could be reused across different contracts

        require(!usedSignatures[token][owner][sigHash], "Signature already used");
        usedSignatures[token][owner][sigHash] = true;

        VulnerablePermitToken(token).permit(owner, address(this), amount, deadline, v, r, s);
    }
}

// VULNERABLE: Permit with ERC-1271 without proper validation
contract VulnerableContractWithPermit {
    address public owner;

    // Smart contract wallet implementing ERC-1271
    function isValidSignature(bytes32 hash, bytes memory signature) public view returns (bytes4) {
        // PROBLEM: No proper validation of signature freshness
        // PROBLEM: Doesn't check if signature was already used
        return 0x1626ba7e;  // ERC-1271 magic value
    }
}

// Phishing attack using permit
contract PermitPhishingAttack {
    // Attacker tricks user into signing a permit for malicious spender
    function phishingAttack(
        address token,
        address victim,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) public {
        // User thinks they're signing permit for legit dApp
        // But spender is attacker's address!
        SafePermitToken(token).permit(
            victim,
            address(this),  // Attacker
            type(uint256).max,  // Unlimited approval!
            deadline,
            v,
            r,
            s
        );

        // Now attacker can drain victim's tokens
        // SafePermitToken(token).transferFrom(victim, attacker, amount);
    }
}

// VULNERABLE: Missing chainId validation
contract CrossChainReplayVulnerable {
    // After a chain split/fork, signatures from one chain
    // can be replayed on the other if chainId not checked
    function vulnerablePermit(address token, address owner, uint256 value) public {
        // Uses permit without verifying current chainId matches signature chainId
    }
}
