# Detection: Cross-Chain Signature Replay

## Graph Signals

| Property | Expected | Critical? |
|----------|----------|-----------|
| uses_ecrecover | true | YES |
| checks_chainid | false | YES |
| has_deadline_check | false | YES |
| validates_domain_separator | false | YES |
| uses_nonce | true | NO |

## Semantic Operations

**Vulnerable Sequence:**
- `READS_SIGNATURE -> ECRECOVER -> VALIDATES_SIGNER -> EXECUTES`
- `ACCEPTS_USER_DOMAIN_SEPARATOR -> HASHES_MESSAGE -> VALIDATES -> REPLAYS`

**Safe Sequence:**
- `READS_SIGNATURE -> VALIDATES_CHAINID -> VALIDATES_DEADLINE -> ECRECOVER -> EXECUTES`
- `HARDCODED_DOMAIN_SEPARATOR -> VALIDATES_SIG -> CHECKS_NONCE -> EXECUTES`

## Behavioral Signatures

- `R:sig->ECRECOVER->CHECK:signer->X:exec` - Missing chainId/deadline
- `R:domainSep(user)->R:sig->VALIDATE->REPLAY` - User-controlled domain separator

## Detection Checklist

1. Function accepts signatures for authentication or authorization
2. Uses `ecrecover` or signature verification library
3. **Missing:** chainId in signature hash
4. **Missing:** deadline/expiration timestamp
5. **Missing:** domain separator validation
6. Contract deployed on multiple chains
7. Nonces can align across chains (e.g., user resets wallet)

## Vulnerability Variants

### Variant 1: Missing chainId

```solidity
// VULNERABLE: No chainId in message hash
function executeWithSignature(
    address target,
    bytes calldata data,
    bytes calldata signature
) external {
    bytes32 messageHash = keccak256(abi.encode(
        target,
        data
        // Missing: block.chainid
    ));

    address signer = ECDSA.recover(messageHash, signature);
    require(signer == trustedSigner, "Invalid signer");

    target.call(data); // Can be replayed on other chains
}
```

**Detection Signal:** `uses_ecrecover: true` + `checks_chainid: false`

### Variant 2: Missing Deadline

```solidity
// VULNERABLE: Signature never expires
function forward(
    address from,
    address to,
    uint256 value,
    bytes calldata signature
) external {
    bytes32 hash = keccak256(abi.encode(from, to, value));
    address signer = ECDSA.recover(hash, signature);

    require(signer == from, "Invalid signature");
    // No deadline check - signature valid forever

    _transfer(from, to, value);
}
```

**Detection Signal:** `uses_ecrecover: true` + `has_deadline_check: false`

### Variant 3: User-Supplied Domain Separator

```solidity
// VULNERABLE: User controls domainSeparator
function execute(
    ForwardRequest calldata req,
    bytes32 domainSeparator, // User-supplied!
    bytes calldata signature
) external {
    bytes32 digest = keccak256(abi.encodePacked(
        "\x19\x01",
        domainSeparator, // Not validated
        keccak256(abi.encode(req))
    ));

    address signer = ECDSA.recover(digest, signature);
    require(nonces[req.from]++ == req.nonce, "Invalid nonce");

    // Execute request (can be replayed with different domainSeparator)
}
```

**Detection Signal:** `accepts_user_domain_separator: true` + `validates_domain_separator: false`

## Code Patterns to Detect

### Pattern 1: EIP-712 Without chainId

```solidity
// Search for EIP-712 structs missing chainId
bytes32 public constant DOMAIN_TYPEHASH = keccak256(
    "EIP712Domain(string name,string version,address verifyingContract)"
    // Missing: uint256 chainId
);
```

### Pattern 2: Message Hash Without chainId

```solidity
// Look for message hashing without block.chainid
bytes32 messageHash = keccak256(abi.encode(
    action,
    target,
    value
    // Missing: block.chainid
));
```

### Pattern 3: No Deadline Validation

```solidity
// Search for signature validation without deadline
function verifySignature(bytes calldata sig) internal {
    address signer = ECDSA.recover(messageHash, sig);
    require(signer == expected, "Invalid");
    // Missing: require(deadline >= block.timestamp, "Expired");
}
```

## False Positive Indicators

- Domain separator includes `block.chainid`
- Deadline timestamp enforced: `require(deadline >= block.timestamp)`
- Contract only deployed on single chain (check deployment records)
- Nonce tracking makes cross-chain replay detectable
- ChainId explicitly validated in signature verification
