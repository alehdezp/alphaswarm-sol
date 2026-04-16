# Patterns: Yala Bridge LayerZero Exploit

## Vulnerable Pattern 1: Unvalidated LayerZero Message Processing

```solidity
// VULNERABLE: No message validation, no nonce tracking, no access control
pragma solidity ^0.8.0;

interface ILayerZeroReceiver {
    function lzReceive(
        uint16 _srcChainId,
        bytes calldata _srcAddress,
        uint64 _nonce,
        bytes calldata _payload
    ) external;
}

contract VulnerableBridge is ILayerZeroReceiver {
    mapping(address => uint256) public balances;
    address public layerZeroEndpoint;

    // VULNERABLE: Accepts messages from anyone, no validation
    function lzReceive(
        uint16 _srcChainId,
        bytes calldata _srcAddress,
        uint64 _nonce,
        bytes calldata _payload
    ) external {
        // VULNERABLE: No validation of source
        // VULNERABLE: No nonce checking
        // VULNERABLE: No signature verification

        // Decode payload without proper validation
        (uint256 amount, address recipient) = abi.decode(_payload, (uint256, address));

        // VULNERABLE: Direct state modification based on untrusted data
        balances[recipient] += amount;
    }
}
```

**Vulnerability Details:**
- No verification of message source (which chain, which endpoint)
- No nonce tracking to prevent replay attacks
- No validation of payload structure or content
- Direct state modification without any guards
- Function callable by anyone through LayerZero endpoint

---

## Vulnerable Pattern 2: Weak Nonce Tracking Without Verification

```solidity
// VULNERABLE: Nonce exists but not properly validated
pragma solidity ^0.8.0;

contract WeakNonceBridge {
    mapping(address => uint256) public balances;
    uint64 public lastNonce;  // VULNERABLE: Single nonce for all chains

    function lzReceive(
        uint16 _srcChainId,
        bytes calldata _srcAddress,
        uint64 _nonce,
        bytes calldata _payload
    ) external {
        // VULNERABLE: Only increment, never verify properly
        lastNonce++;

        // VULNERABLE: Nonce not per-chain, allows cross-chain replay
        // If lastNonce = 5, an attacker can replay same message from different chain

        (uint256 amount, address to) = abi.decode(_payload, (uint256, address));

        // VULNERABLE: amount and to not validated
        balances[to] += amount;

        emit Received(_srcChainId, amount, to);
    }

    event Received(uint16 srcChainId, uint256 amount, address indexed to);
}
```

**Vulnerability Details:**
- Single nonce for all chains (should be per-chain)
- Nonce incremented but not strictly validated
- No requirement that `_nonce == lastNonce[_srcChainId] + 1`
- Allows replay attacks across chains
- Allows out-of-order message processing

---

## Vulnerable Pattern 3: Insufficient Source Chain Validation

```solidity
// VULNERABLE: No validation of source chain or address
pragma solidity ^0.8.0;

contract NoSourceValidationBridge {
    mapping(address => uint256) public balances;
    mapping(uint16 => uint64) public lastNonce;

    function lzReceive(
        uint16 _srcChainId,
        bytes calldata _srcAddress,
        uint64 _nonce,
        bytes calldata _payload
    ) external {
        // VULNERABLE: No check that _srcChainId is authorized
        // VULNERABLE: No check that _srcAddress is authorized
        // Any chain can send, any address on that chain can send

        lastNonce[_srcChainId] = _nonce;

        (uint256 amount, address to) = abi.decode(_payload, (uint256, address));
        balances[to] += amount;
    }
}
```

**Vulnerability Details:**
- No whitelist of authorized source chains
- No verification of source address
- No check that message comes from trusted bridge on other chain
- Any contract can call lzReceive
- Attacker can craft messages from fake chains

---

## Vulnerable Pattern 4: Missing Signature Verification

```solidity
// VULNERABLE: Message not signed, no cryptographic verification
pragma solidity ^0.8.0;

contract NoSignatureBridge {
    mapping(address => uint256) public balances;
    mapping(uint16 => uint64) public lastNonce;
    mapping(uint16 => bytes) public trustedRemotes;

    function lzReceive(
        uint16 _srcChainId,
        bytes calldata _srcAddress,
        uint64 _nonce,
        bytes calldata _payload
    ) external {
        // Has basic nonce tracking
        require(_nonce > lastNonce[_srcChainId], "Replay attack");
        lastNonce[_srcChainId] = _nonce;

        // Has source validation
        require(
            keccak256(_srcAddress) == keccak256(trustedRemotes[_srcChainId]),
            "Untrusted source"
        );

        // VULNERABLE: No signature verification!
        // Attacker can craft arbitrary messages if they can call this function

        (uint256 amount, address to) = abi.decode(_payload, (uint256, address));
        balances[to] += amount;  // VULNERABLE: Direct state change
    }
}
```

**Vulnerability Details:**
- No ECDSA or BLS signature on messages
- No cryptographic proof of message authenticity
- Relying only on source address check (insufficient)
- Attacker who can bypass LayerZero can drain bridge

---

## Safe Pattern 1: Complete Message Validation

```solidity
// SAFE: Proper validation at every step
pragma solidity ^0.8.0;

interface ILayerZeroReceiver {
    function lzReceive(
        uint16 _srcChainId,
        bytes calldata _srcAddress,
        uint64 _nonce,
        bytes calldata _payload
    ) external;
}

contract SafeBridge is ILayerZeroReceiver {
    mapping(address => uint256) public balances;
    address public layerZeroEndpoint;

    // Nonce tracking PER SOURCE CHAIN
    mapping(uint16 => uint64) public lastNonce;

    // Whitelist of trusted remote bridges
    mapping(uint16 => bytes) public trustedRemotes;

    // Signature verification helpers
    bytes32 private constant DOMAIN_SEPARATOR = keccak256("BridgeMessage");

    modifier onlyAuthorizedLz() {
        // SAFE: Only LayerZero endpoint can call
        require(msg.sender == layerZeroEndpoint, "Unauthorized");
        _;
    }

    function lzReceive(
        uint16 _srcChainId,
        bytes calldata _srcAddress,
        uint64 _nonce,
        bytes calldata _payload
    ) external onlyAuthorizedLz {
        // STEP 1: Validate source chain
        require(trustedRemotes[_srcChainId].length > 0, "Unknown chain");

        // STEP 2: Validate source address
        require(
            keccak256(_srcAddress) == keccak256(trustedRemotes[_srcChainId]),
            "Untrusted source"
        );

        // STEP 3: Replay protection - nonce MUST be strictly increasing per chain
        require(_nonce == lastNonce[_srcChainId] + 1, "Invalid nonce sequence");
        lastNonce[_srcChainId] = _nonce;

        // STEP 4: Strict payload validation
        require(_payload.length >= 64, "Payload too short");

        (uint256 amount, address recipient) = abi.decode(_payload, (uint256, address));

        // STEP 5: Validate decoded values
        require(amount > 0, "Invalid amount");
        require(amount <= 10_000_000 * 10**18, "Amount exceeds limit");
        require(recipient != address(0), "Invalid recipient");

        // STEP 6: Only now modify state
        balances[recipient] += amount;

        emit MessageProcessed(_srcChainId, amount, recipient, _nonce);
    }

    function setTrustedRemote(uint16 _chainId, bytes calldata _remoteAddress) external {
        // SAFE: Add access control here
        require(msg.sender == owner, "Unauthorized");
        trustedRemotes[_chainId] = _remoteAddress;
    }

    // ... owner/permission management ...

    event MessageProcessed(
        uint16 indexed srcChainId,
        uint256 amount,
        address indexed recipient,
        uint64 nonce
    );
}
```

**Safety Features:**
- Per-chain nonce tracking (prevents replay across chains)
- Strict nonce validation (must be sequential)
- Trusted endpoint whitelist
- Strict payload validation (length, type, bounds)
- Access control on configuration changes
- Clear separation: validate → authorize → process
- Event logging for audit trail

---

## Safe Pattern 2: With Signature Verification

```solidity
// SAFE: Complete validation with cryptographic signatures
pragma solidity ^0.8.0;

contract SafeSignedBridge {
    mapping(address => uint256) public balances;
    address public layerZeroEndpoint;
    mapping(uint16 => uint64) public lastNonce;
    mapping(uint16 => bytes) public trustedRemotes;

    // Signer accounts per chain
    mapping(uint16 => address[]) public signers;
    mapping(uint16 => uint256) public requiredSignatures;

    event MessageProcessed(uint16 indexed srcChainId, uint256 amount, address indexed to, uint64 nonce);

    modifier onlyAuthorizedLz() {
        require(msg.sender == layerZeroEndpoint, "Unauthorized");
        _;
    }

    function lzReceive(
        uint16 _srcChainId,
        bytes calldata _srcAddress,
        uint64 _nonce,
        bytes calldata _payload
    ) external onlyAuthorizedLz {
        // STEP 1: Source validation
        require(
            keccak256(_srcAddress) == keccak256(trustedRemotes[_srcChainId]),
            "Untrusted source"
        );

        // STEP 2: Nonce validation (must be strictly sequential)
        require(_nonce == lastNonce[_srcChainId] + 1, "Invalid nonce");
        lastNonce[_srcChainId] = _nonce;

        // STEP 3: Decode and validate payload structure
        require(_payload.length >= 96, "Payload too short");

        (uint256 amount, address recipient, bytes[] memory signatures) = abi.decode(
            _payload,
            (uint256, address, bytes[])
        );

        // STEP 4: Validate payload content
        require(amount > 0 && amount <= 10_000_000 * 10**18, "Invalid amount");
        require(recipient != address(0), "Invalid recipient");

        // STEP 5: Cryptographic signature verification
        bytes32 messageHash = keccak256(
            abi.encode(_srcChainId, _nonce, amount, recipient)
        );

        address[] memory signerList = signers[_srcChainId];
        require(signerList.length > 0, "No signers configured");
        require(signatures.length >= requiredSignatures[_srcChainId], "Not enough signatures");

        bytes32 ethSignedMessageHash = keccak256(
            abi.encodePacked("\x19Ethereum Signed Message:\n32", messageHash)
        );

        for (uint256 i = 0; i < requiredSignatures[_srcChainId]; i++) {
            address recovered = recoverSigner(ethSignedMessageHash, signatures[i]);
            require(isAuthorizedSigner(_srcChainId, recovered), "Invalid signature");
        }

        // STEP 6: Only after ALL validation, modify state
        balances[recipient] += amount;

        emit MessageProcessed(_srcChainId, amount, recipient, _nonce);
    }

    function recoverSigner(bytes32 messageHash, bytes memory signature)
        internal
        pure
        returns (address)
    {
        require(signature.length == 65, "Invalid signature length");

        bytes32 r;
        bytes32 s;
        uint8 v;

        assembly {
            r := mload(add(signature, 0x20))
            s := mload(add(signature, 0x40))
            v := byte(0, mload(add(signature, 0x60)))
        }

        if (v < 27) {
            v += 27;
        }

        require(v == 27 || v == 28, "Invalid signature v");
        return ecrecover(messageHash, v, r, s);
    }

    function isAuthorizedSigner(uint16 _chainId, address signer)
        internal
        view
        returns (bool)
    {
        address[] memory signerList = signers[_chainId];
        for (uint256 i = 0; i < signerList.length; i++) {
            if (signerList[i] == signer) {
                return true;
            }
        }
        return false;
    }

    // Configuration functions (with access control)
    function setSigners(uint16 _chainId, address[] calldata _signers, uint256 _required) external {
        require(msg.sender == owner, "Unauthorized");
        require(_required > 0 && _required <= _signers.length, "Invalid required count");
        signers[_chainId] = _signers;
        requiredSignatures[_chainId] = _required;
    }
}
```

**Safety Features:**
- Multi-signature verification
- ECDSA signature recovery and validation
- Per-chain signer configuration
- Requires M-of-N signatures
- Strict validation at every step
- Nonce-based replay protection
- Complete payload validation

---

## Key Differences Summary

| Aspect | Vulnerable | Safe |
|--------|-----------|------|
| **Nonce Tracking** | Single global nonce, or not checked | Per-chain nonce, strictly sequential |
| **Source Validation** | None or weak | Whitelist of trusted endpoints |
| **Signature** | None | ECDSA/BLS verification required |
| **Payload Validation** | None | Structure, type, and bounds checked |
| **State Modification** | Immediate | After all validation complete |
| **Access Control** | None | Only authorized endpoint can call |
| **Ordering** | Arbitrary | Validate → Authorize → Process |

---

## Edge Cases to Consider

### Case 1: Multiple Messages in Flight
Even with nonce tracking, multiple messages across different chains can be in flight simultaneously. Safe implementation handles this by:
- Per-chain nonce tracking (not global)
- Allowing messages from different chains to be processed concurrently
- Not assuming any ordering across chains

### Case 2: Chain Reorganization
Blockchain reorganizations could invalidate nonces. Safe implementation:
- Uses finalized blocks only
- Implements block-height-based confirmation windows
- Allows nonce reset only via governance

### Case 3: Message Duplication
If the same message is relayed twice:
- Per-chain nonce makes duplicate unprocessable
- Signature verification adds additional layer
- State should not change on second attempt

### Case 4: Delayed Messages
Messages from old nonces arriving late:
- Will be rejected by nonce check
- Safe pattern allows safe rejection without state change
- Proper event logging helps identify issues
