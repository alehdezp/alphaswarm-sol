# Bridge Compromise - Subcategory Overview

## What is Bridge Compromise?

Bridge compromise occurs when attackers exploit vulnerabilities in cross-chain bridge contracts to directly bypass normal operations and steal assets or perform unauthorized actions. Unlike message validation failures that target the relay mechanism, bridge compromises target the bridge contract itself.

## Key Characteristics

Bridge compromise vulnerabilities typically involve:

1. **Direct Access to Bridge Functions** - Attacker can call bridge functions directly (or via relay)
2. **Insufficient Validation** - Bridge doesn't properly validate the source or authenticity of messages
3. **Weak Authorization** - Insufficient access controls on critical operations
4. **State Modification** - Attacker can modify critical state (balances, supply, mappings)
5. **Asset Loss** - Direct financial loss through unauthorized token transfers

## Attack Surface

Bridge contracts have several critical operations:

### 1. Message Reception
- Receive cross-chain messages
- Decode and parse message data
- Execute actions based on message content

**Vulnerable Patterns:**
- No verification that message is authentic
- No validation of message format or content
- No checks on message source or timestamp

### 2. Token Minting/Burning
- Mint tokens representing bridged assets
- Burn tokens when assets are withdrawn
- Maintain accounting of minted vs backed tokens

**Vulnerable Patterns:**
- Direct minting without authorization checks
- No validation of mint amount
- Missing collateral verification

### 3. Asset Movement
- Transfer assets from bridge to recipients
- Receive assets from users
- Maintain balance for all recipients

**Vulnerable Patterns:**
- No access control on transfers
- Missing amount validation
- No check on recipient legitimacy

## Real-World Examples

### Yala Bridge LayerZero (September 2025, $7.64M)

**Attack Path:**
1. Bridge uses LayerZero for cross-chain messages
2. Messages not signed/verified
3. Attacker crafts fake LayerZero messages
4. Messages pass weak nonce checks (global counter, not per-chain)
5. Bridge mints tokens based on fake messages
6. Attacker claims tokens on multiple chains
7. Total damage: $7.64M

**Root Causes:**
- No ECDSA/BLS signature verification
- Global nonce instead of per-chain tracking
- No source chain validation
- No input validation on amounts

### Wormhole Bridge (February 2022, $325M)

**Attack Path:**
1. Bridge uses guardian set to approve messages
2. Guardian signature verification vulnerable to state mutation
3. Attacker finds way to pass signature check
4. Attacker crafts message to approve arbitrary transfers
5. Attacker withdraws $325M in wrapped tokens

**Root Cause:**
- Insufficient signature verification logic
- Missing edge case handling

### Ronin Bridge (March 2022, $625M)

**Attack Path:**
1. Bridge requires K-of-N validator approval
2. Validator private keys compromised (via social engineering)
3. Attacker gains 5 of 9 validators (majority)
4. Attacker creates transaction minting tokens
5. Attacker withdraws $625M

**Root Causes:**
- Over-reliance on validator security
- Insufficient separation of duties
- No monitoring/alerting for unusual transactions

## Detection Pattern

The typical bridge compromise follows this pattern:

```
CALLS_EXTERNAL (to bridge/relay)
  ↓
READS_EXTERNAL_VALUE (from cross-chain message)
  ↓
VALIDATES_INPUT = FALSE (CRITICAL GAP!)
  ↓
WRITES_PRIVILEGED_STATE (mints/transfers)
```

Without the validation step, the bridge is vulnerable.

## Common Vulnerabilities

| Vulnerability | Example | Risk |
|---|---|---|
| **No Signature Verification** | Message parameter ignored | CRITICAL |
| **Global Nonce** | Single counter for all chains | CRITICAL |
| **No Source Validation** | Accept messages from any chain | CRITICAL |
| **No Input Validation** | Use decoded values directly | HIGH |
| **Missing Access Control** | Anyone can call critical functions | HIGH |
| **Wrong Ordering** | Call before validating | HIGH |

## Subcategory Specifics

This subcategory includes detailed analysis of specific exploits:

### Yala Bridge LayerZero (September 2025)
- **Loss**: $7.64M
- **Status**: [See `/specifics/yala-layerzero/` for full analysis]
- **Key Issue**: Unvalidated LayerZero messages + weak nonce tracking
- **Detection**: Look for `CALLS_EXTERNAL -> READS_EXTERNAL_VALUE -> WRITES_PRIVILEGED_STATE` without validation

## Remediation Priorities

### Priority 1: Signature Verification
Every cross-chain message must be cryptographically signed and verified. This is the foundation of trust.

### Priority 2: Per-Chain Nonce Tracking
Each source chain must have independent, strictly sequential nonce tracking to prevent replays.

### Priority 3: Source Validation
Maintain whitelist of authorized source chains and endpoints. Reject all others.

### Priority 4: Input Validation
Validate all decoded message parameters for bounds, format, and validity.

### Priority 5: Access Control
Restrict who can call critical functions. Use role-based access control.

## BSKG Properties to Check

For bridge functions, verify:

```
has_operation(CALLS_EXTERNAL) ✓
AND
has_operation(READS_EXTERNAL_VALUE) ✓
AND
NOT has_operation(VALIDATES_INPUT) → VULNERABLE!
```

Red flags:
- `validates_input` = false
- `has_access_gate` = false
- `writes_privileged_state` = true
- No signature verification
- Global nonce tracking

Green flags:
- Signature verification present
- Per-chain nonce tracking
- Source address validation
- Strict input validation
- Access control modifiers

## Testing Strategy

For contracts using this pattern, test:

1. **Valid Messages** - Should succeed
2. **Invalid Signatures** - Should fail
3. **Replayed Messages** - Should fail
4. **Messages from Unknown Chains** - Should fail
5. **Malformed Payloads** - Should fail
6. **Out-of-Bounds Amounts** - Should fail
7. **Zero Address Recipients** - Should fail
8. **Sequential Nonce Gaps** - Should fail

## Further Resources

- **Full Yala Analysis**: See `/yala-layerzero/` directory
- **Detection Guidance**: `detection.md` in this directory
- **Code Patterns**: `patterns.md` shows vulnerable vs safe code
- **Exploit Details**: `exploits.md` with real-world attack flows
- **Fix Guidance**: `fixes.md` with complete remediation steps
