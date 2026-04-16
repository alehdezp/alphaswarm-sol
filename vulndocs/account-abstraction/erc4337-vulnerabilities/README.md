# ERC-4337 Account Abstraction Vulnerabilities

## Overview

ERC-4337 introduces account abstraction to Ethereum without protocol changes, using smart contract wallets that execute user operations. This creates new attack surfaces in validation logic, paymaster sponsorship, signature handling, and entry point interactions. Vulnerabilities can lead to full account takeover, gas griefing, or unauthorized operations.

## Core Vulnerability Pattern

**DISCOVER**: ERC-4337 vulnerabilities arise from the separation of validation and execution, complex signature schemes, paymaster trust assumptions, and non-deterministic behavior in validation.

**REASON**: The architecture introduces:
- **Validation Phase**: Must be deterministic, gas-bounded, no storage writes
- **Execution Phase**: Can perform arbitrary operations
- **Paymaster Sponsorship**: Third-party gas payment with abuse potential
- **Entry Point Trust**: Central coordinator with specific invariants

Breaking these invariants or assumptions creates exploitable conditions.

## Known Exploits and Vulnerabilities

### UniPass Account Takeover (2023)
**Discovered by**: Fireblocks Research
**Impact**: Full account takeover vulnerability
**Root Cause**: Three-part vulnerability chain:

1. **Empty Signature Validation Flaw**: `validateSignature` returned `success=true` for empty signature, resulting in zero role weights
2. **Missing Permission Check**: `getRoleOfPermission` returned 0 weights when permissions weren't explicitly set via `addPermission`
3. **Unprotected Critical Function**: ERC-4337 module installation failed to call `addPermission` for `setEntrypoint` function

**Attack Flow**:
```
1. Submit UserOperation with empty signature
2. Call setEntrypoint(attackerControlledEntryPoint)
3. Attacker's malicious EntryPoint executes arbitrary operations
4. Full wallet takeover
```

**Detection Signals**:
- `VALIDATES_SIGNATURE` returns success for empty input
- Critical functions missing `has_access_gate`
- `MODIFIES_CRITICAL_STATE` (entry point) without permission check

### EntryPoint Packing Vulnerability (Feb 2024)
**Discovered by**: Alchemy Research
**Impact**: Hash divergence breaking off-chain infrastructure
**Root Cause**: Non-deterministic UserOperation hashing using assembly

**Mechanism**:
- `pack` function used assembly to generate hashes from calldata
- Malicious calldata construction could create divergent hashes
- Same UserOperation → different hashes OR different UserOperations → same hash

**Impact**: Bundlers cannot reconcile mempool state with on-chain events, expensive re-decoding required

**Detection Signals**:
- Assembly code in hashing functions
- No canonical encoding enforcement
- Reliance on ABI encoding specifics

### VerifyingPaymaster Signature Validation (Feb 2024)
**Discovered by**: Alchemy Research
**Impact**: Paymaster exploitation via signature bypasses
**Root Cause**: Similar packing vulnerability in paymaster signature validation

**Attack**: Craft malicious paymaster data to bypass signature checks

**Detection Signals**:
- Paymaster signature validation using assembly
- Non-standard encoding in validation phase

## Vulnerability Categories

### 1. Validation Phase Violations

#### Non-Deterministic Behavior
**Pattern**: Validation logic depends on variable state or external calls without staking

**Properties**:
- `VALIDATES_SIGNATURE` calls `CALLS_EXTERNAL` or `READS_EXTERNAL_VALUE`
- Uses `block.timestamp`, `block.number`, `blockhash` in validation
- Storage writes (`SSTORE`) in validation phase
- Unbounded loops or variable gas consumption

**Risk**: Bundlers cannot simulate consistently, operations fail unpredictably

#### Unbounded Gas Consumption
**Pattern**: Validation logic has no gas limit enforcement

**Properties**:
- `VALIDATES_SIGNATURE` contains unbounded loops
- Recursive calls in validation
- No gas metering on external calls

**Risk**: Gas griefing attacks on bundlers

### 2. Signature Validation Flaws

#### Empty Signature Acceptance
**Pattern**: Validation succeeds with empty or zero signature data

**Properties**:
- `VALIDATES_SIGNATURE` returns success for `signature.length == 0`
- No signature data presence check
- Default return values interpreted as success

**Risk**: Bypass authentication, unauthorized operations

#### Signature Malleability
**Pattern**: Multiple valid signatures for same operation

**Properties**:
- No `CHECKS_SIG_S` for ECDSA malleability
- `ecrecover` without canonical signature checks
- Missing replay protection across signature schemes

**Risk**: Replay attacks, front-running

### 3. Paymaster Vulnerabilities

#### Gas Penalty Exploitation
**Pattern**: Paymaster refund calculation doesn't account for 10% unused gas penalty

**Properties**:
- Paymaster calculates refund based on actual gas used only
- Doesn't account for `EntryPoint` 10% penalty on unused gas limit
- Malicious users set high gas limit to trigger penalty

**Attack Flow**:
```
1. User sets gasLimit = 1M but operation uses 100K
2. EntryPoint charges 10% of 900K unused = 90K penalty
3. Paymaster charged 190K total but only expected 100K
4. Repeat to drain paymaster deposit
```

**Detection Signals**:
- `TRANSFERS_VALUE_OUT` for gas refund without penalty calculation
- Refund based on `actualGasUsed` alone
- Missing validation of `gasLimit` vs expected usage

#### Post-Execution Charging Exploits
**Pattern**: Paymaster charges users in `postOp()` after execution

**Mechanism**:
- User operation executes successfully
- In `postOp()`, paymaster tries to charge user (e.g., transfer tokens)
- User revokes token approval before `postOp()`
- `postOp()` fails, but bundler already got paid from paymaster deposit

**Attack**: Malicious bundler ensures `postOp()` fails while collecting payment

**Detection Signals**:
- `TRANSFERS_VALUE_OUT` in `postOp()` function
- Token transfer dependent on user allowance
- No pre-charge mechanism

#### Whitelist Bypass
**Pattern**: Paymaster whitelist validation can be circumvented

**Properties**:
- Whitelist checked in validation but not enforced on-chain
- Off-chain signature can be replayed or manipulated
- Missing cryptographic binding between user and whitelist proof

**Risk**: Unauthorized users get sponsored gas

### 4. Entry Point Trust Issues

#### Malicious Entry Point
**Pattern**: Wallet trusts arbitrary entry point without validation

**Properties**:
- `MODIFIES_CRITICAL_STATE` allowing entry point change
- No entry point address validation
- Missing canonical entry point check

**Risk**: Attacker sets own entry point to execute arbitrary operations

#### Entry Point Upgrade Risks
**Pattern**: Entry point upgrade mechanism lacks safeguards

**Properties**:
- Entry point mutable without timelock
- No migration verification
- Immediate upgrade execution

**Risk**: Malicious upgrade disrupts all wallets

### 5. Initialization Vulnerabilities

#### Unprotected Initialization
**Pattern**: Account initialization callable by anyone

**Properties**:
- `INITIALIZES_CONTRACT` without `has_access_gate`
- No `initialized` state check
- Constructor parameters controllable

**Risk**: Front-run initialization with malicious parameters

#### Module Installation Race
**Pattern**: ERC-4337 module installation lacks proper setup

**Properties**:
- Modules installed without permission setup
- Critical functions unprotected during installation
- No atomicity in multi-step initialization

**Risk**: Window for account takeover during setup

## Attack Scenarios

### Scenario 1: Gas Griefing via Paymaster
```
1. Attacker identifies paymaster with penalty miscalculation
2. Crafts UserOperation with extremely high gasLimit (10M)
3. Operation uses minimal gas (100K)
4. EntryPoint charges paymaster: 100K + 10% * 9.9M = ~1M gas
5. Repeat until paymaster deposit drained
6. Legitimate users cannot use paymaster
```

**Detection**: `TRANSFERS_VALUE_OUT` for gas without accounting for penalties

### Scenario 2: Account Takeover via Empty Signature
```
1. Target account has empty signature validation flaw
2. Attacker crafts UserOperation with empty signature
3. Validation passes with zero permissions
4. Call setEntrypoint(attackerEntryPoint)
5. Use malicious entry point to execute arbitrary operations
6. Drain account funds
```

**Detection**: `VALIDATES_SIGNATURE` returns true for empty input, `MODIFIES_CRITICAL_STATE` unprotected

### Scenario 3: Hash Collision for Fee Evasion
```
1. Attacker crafts malicious calldata for UserOperation
2. Off-chain hash differs from on-chain hash
3. Bundler accepts based on off-chain hash
4. On-chain execution uses different hash
5. Fee payment bypassed or incorrect operation executed
```

**Detection**: Assembly-based hashing without canonical encoding

## Detection Criteria

### Critical Signals (High Confidence)
1. **Empty signature acceptance**: `VALIDATES_SIGNATURE` succeeds for `signature.length == 0`
2. **Unprotected entry point modification**: `MODIFIES_CRITICAL_STATE` without access control
3. **Storage writes in validation**: `SSTORE` in `validateUserOp` or `validatePaymasterUserOp`
4. **Post-execution charging**: `TRANSFERS_VALUE_OUT` for gas in `postOp()` based on user allowance

### Medium Confidence Signals
1. **Gas penalty miscalculation**: Refund logic doesn't account for 10% penalty
2. **Non-deterministic validation**: Validation depends on `block.timestamp`, external calls
3. **Assembly in signature validation**: Low-level operations in validation without canonical checks
4. **Missing signature malleability checks**: `ecrecover` without `s` value validation

### Context Indicators
- Contract implements `IAccount` or `IPaymaster` interface
- Interacts with EntryPoint (0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789 on mainnet)
- Recent deployment (<1 year) of custom wallet implementation
- Paymaster with public sponsorship (not permissioned)

## Fixes and Mitigations

### Proper Signature Validation
```solidity
function validateSignature(
    bytes32 userOpHash,
    bytes calldata signature
) internal returns (uint256 validationData) {
    // Reject empty signatures
    require(signature.length > 0, "Empty signature");

    // Recover signer
    address signer = ECDSA.recover(userOpHash, signature);

    // Check signer has required role/weight
    require(hasRole[signer], "Unauthorized signer");
    require(roleWeight[signer] >= REQUIRED_WEIGHT, "Insufficient weight");

    return 0; // Success
}
```

### Gas Penalty-Aware Paymaster
```solidity
function postOp(
    PostOpMode mode,
    bytes calldata context,
    uint256 actualGasCost
) external override {
    // Account for 10% penalty on unused gas
    uint256 gasLimit = abi.decode(context, (uint256));
    uint256 actualGasUsed = actualGasCost / tx.gasprice;
    uint256 unusedGas = gasLimit - actualGasUsed;
    uint256 penalty = unusedGas / 10; // 10% penalty

    uint256 totalCost = (actualGasUsed + penalty) * tx.gasprice;

    // Charge user the total cost including penalty
    // Use pre-charged deposit, not post-op transfer
}
```

### Protected Entry Point Updates
```solidity
address public immutable CANONICAL_ENTRYPOINT;

function setEntryPoint(address newEntryPoint) external onlyOwner {
    require(newEntryPoint != address(0), "Invalid entry point");
    require(isValidEntryPoint(newEntryPoint), "Not canonical");

    // Time delay for security
    entryPointPending = newEntryPoint;
    entryPointUpdateTime = block.timestamp + TIMELOCK;
}

function executeEntryPointUpdate() external {
    require(block.timestamp >= entryPointUpdateTime, "Timelock active");
    emit EntryPointUpdated(entryPoint, entryPointPending);
    entryPoint = entryPointPending;
}
```

### Secure Initialization
```solidity
bool private initialized;

modifier initializer() {
    require(!initialized, "Already initialized");
    initialized = true;
    _;
}

function initialize(
    address _owner,
    address[] calldata _guardians
) external initializer {
    require(_owner != address(0), "Invalid owner");

    owner = _owner;

    // Set up all permissions atomically
    for (uint i = 0; i < _guardians.length; i++) {
        addPermission(_guardians[i], ALL_PERMISSIONS);
    }

    // Explicitly protect critical functions
    addPermission(address(this), bytes4(keccak256("setEntrypoint(address)")));
}
```

### Deterministic Validation
```solidity
function validateUserOp(
    UserOperation calldata userOp,
    bytes32 userOpHash,
    uint256 missingAccountFunds
) external returns (uint256 validationData) {
    // NO external calls without staking
    // NO storage reads of mutable state
    // NO timestamp dependencies
    // NO unbounded loops

    // Only pure cryptographic validation
    address signer = ECDSA.recover(userOpHash, userOp.signature);

    if (owner == signer) {
        return 0; // Success
    }

    return 1; // Failure
}
```

## Security Best Practices

### For Wallet Implementers
1. **Validate signature presence**: Never accept empty signatures
2. **Protect critical functions**: Entry point changes, owner updates
3. **Use canonical entry point**: Verify against official deployment
4. **Atomic initialization**: Set all permissions in constructor/initializer
5. **Deterministic validation**: No external calls, storage writes, or variable gas

### For Paymaster Implementers
1. **Account for gas penalties**: Include 10% unused gas penalty in calculations
2. **Pre-charge users**: Don't rely on post-execution transfers
3. **Validate gas limits**: Reject unreasonably high gas limits
4. **Use verifying signatures**: Off-chain validation with on-chain verification
5. **Monitor deposit levels**: Auto-pause if deposit below threshold

### For Bundlers
1. **Simulate with actual EntryPoint**: Use canonical simulation environment
2. **Validate packing**: Check for non-standard calldata encoding
3. **Rate-limit operations**: Per sender, per paymaster
4. **Monitor reputation**: Track validation failure rates

### For dApp Integrators
1. **Verify entry point**: Check wallet uses canonical EntryPoint
2. **Validate paymaster trust**: Only use audited, reputable paymasters
3. **UI warnings**: Alert users to security risks
4. **Fallback mechanisms**: Support EOAs as backup

## CWE Mappings

- **CWE-287**: Improper Authentication (empty signature acceptance)
- **CWE-288**: Authentication Bypass Using Alternate Path (entry point manipulation)
- **CWE-362**: Concurrent Execution using Shared Resource (race conditions in init)
- **CWE-400**: Uncontrolled Resource Consumption (gas griefing)
- **CWE-841**: Improper Enforcement of Behavioral Workflow (validation phase violations)

## References

- ERC-4337: Account Abstraction via Entry Point Contract
- Fireblocks: First Account Abstraction Wallet Vulnerability (UniPass)
- Alchemy: ERC-4337 UserOperation Packing Vulnerability (Feb 2024)
- Ethereum Foundation Bug Bounty: Up to $250K for ERC-4337 vulnerabilities
- OpenZeppelin Audits: EIP-4337 audits (7+ high severity issues found)
- OSEC Research: Paymasters EVM Security Issues

## Related Categories

- **Access Control**: Entry point and owner management
- **Signature Verification**: ECDSA malleability, replay protection
- **Logic Errors**: Validation phase violations
- **DoS**: Gas griefing via paymasters
