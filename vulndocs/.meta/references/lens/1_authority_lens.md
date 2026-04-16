# Authority Lens - Ultra-Expanded Detection Patterns

> Comprehensive access control, authorization, and authentication vulnerability detection
> for AlphaSwarm.sol

---

## Table of Contents
1. [Missing Access Control](#1-missing-access-control)
2. [Incorrect Access Control](#2-incorrect-access-control)
3. [Broken Access Control Logic](#3-broken-access-control-logic)
4. [Centralization & Privilege Risks](#4-centralization--privilege-risks)
5. [Authentication Vulnerabilities](#5-authentication-vulnerabilities)
6. [Signature & Cryptographic Auth](#6-signature--cryptographic-auth)
7. [Role-Based Access Control Issues](#7-role-based-access-control-issues)
8. [Multi-Sig & Governance Auth](#8-multi-sig--governance-auth)
9. [Time-Based Access Control](#9-time-based-access-control)
10. [Cross-Contract Authorization](#10-cross-contract-authorization)

---

## 1. Missing Access Control

### 1.1 Unprotected State Writers
**CWE-284, CWE-285, CWE-862**

#### Detection Phrases (NL Queries)
```
public functions that write state without access modifiers
external functions modifying owner or admin without onlyOwner
functions transferring funds without authorization checks
state-changing functions without require statements on msg.sender
functions that can change critical parameters without role verification
public setters for privileged state variables
functions performing withdrawals without access gates
external functions that modify storage without caller validation
public methods updating contract configuration without auth
functions writing to mapping without ownership verification
state mutations accessible to any caller
setters for fee parameters without admin check
functions that can modify token balances without authorization
public functions that update oracle addresses without restriction
methods changing protocol parameters callable by anyone
external functions that can pause or unpause without auth
functions modifying whitelist or blacklist without access control
public methods that can change reward rates without verification
functions updating vault strategies without authorization
external setters for slippage tolerance without role check
functions that can modify liquidation thresholds without auth
public methods changing collateral factors without restriction
functions updating interest rate models without access control
external functions modifying pool weights without authorization
methods that can change fee recipients without admin verification
functions updating merkle roots without access restriction
public setters for time-sensitive parameters without auth
functions that can modify vesting schedules without authorization
external methods changing emission rates without role verification
functions updating price feed addresses without access control
public functions that can modify governance parameters without auth
methods changing quorum thresholds without authorization
functions updating voting periods without access restriction
external setters for proposal thresholds without role check
functions that can modify execution delays without auth
public methods changing guardian addresses without verification
functions updating emergency contacts without access control
external functions modifying bridge parameters without authorization
methods that can change cross-chain configurations without auth
functions updating relayer addresses without role verification
```

#### Detection Rules
```yaml
rule: unprotected-state-writer
conditions:
  - function.visibility IN [public, external]
  - function.writes_state == true
  - function.has_access_modifier == false
  - function.has_require_msg_sender == false
  - function.has_onlyOwner == false
  - function.has_onlyRole == false
severity: critical
```

#### Sub-Pattern: Unprotected Admin Functions
```
functions named set* or update* without access control
methods with admin or owner in name callable by anyone
functions named configure* without authorization check
methods named change* or modify* without role verification
functions with privileged or restricted in comments but no auth
external initialize functions callable after deployment
functions named grant* or revoke* without access control
methods named add* or remove* for admin lists without auth
functions named pause* or unpause* without role check
methods named upgrade* without authorization verification
functions named migrate* callable by anyone
external rescue or recover functions without access control
functions named emergency* without proper authorization
methods named force* without admin verification
```

#### Sub-Pattern: Unprotected Value Transfers
```
functions that transfer ETH without caller verification
methods sending tokens without authorization check
functions that can drain contract balance without auth
external withdraw functions without access control
methods that forward value without caller validation
functions distributing rewards without role verification
external claim functions without proper authorization
methods that can sweep tokens without admin check
functions transferring NFTs without ownership verification
external functions that can move funds between accounts without auth
methods that can liquidate positions without authorization
functions that can seize collateral without role check
external payout functions without access control
methods distributing dividends without verification
```

### 1.2 Unprotected Initialization
**CWE-665, CWE-284**

#### Detection Phrases
```
initialize functions without initializer modifier
setup methods callable multiple times
init functions without initialized flag check
constructor-like functions in upgradeable contracts without protection
functions that set owner callable after deployment
initialization methods without reentrancy guard on init flag
setup functions that can reset contract state
external init functions without access control
methods that can reinitialize critical parameters
functions setting initial values without one-time check
initialization that can be front-run after deployment
setup functions without deployment-time restrictions
init methods that don't verify caller is deployer
functions that can overwrite initialized state
initialization accessible in proxy implementation directly
setup callable on implementation contract
init functions without proper proxy context check
initialization methods vulnerable to sandwich attacks
setup functions that can be called through delegatecall
init without checking proxy vs implementation context
```

#### Detection Rules
```yaml
rule: unprotected-initializer
conditions:
  - function.name MATCHES (initialize|init|setup|__init__)
  - function.visibility IN [public, external]
  - NOT function.has_initializer_modifier
  - NOT function.checks_initialized_flag
severity: critical
```

### 1.3 Missing Function-Level Access Control
**CWE-285**

#### Detection Phrases
```
internal functions exposed via public wrapper without auth
private logic accessible through unprotected external function
helper functions called by public methods without validation
internal state changes triggered by external calls without auth
protected logic bypassable through alternative entry points
functions with multiple entry points lacking consistent auth
internal transfers callable via external interface without check
private setters exposed through public interface
helper methods that modify state accessible externally
internal calculations affecting balances without auth on caller
```

---

## 2. Incorrect Access Control

### 2.1 tx.origin Vulnerabilities
**CWE-287, CWE-477**

#### Detection Phrases
```
access control using tx.origin instead of msg.sender
authorization checks comparing tx.origin for privileges
require statements validating tx.origin equals owner
modifiers checking tx.origin for admin access
functions using tx.origin in authentication logic
tx.origin comparison in transfer authorization
admin verification using tx.origin instead of msg.sender
role checks based on tx.origin value
tx.origin used to determine caller privileges
authorization depending on transaction originator not immediate caller
access gates using tx.origin for validation
privilege escalation possible via tx.origin phishing
tx.origin checks in multi-contract interactions
authentication logic vulnerable to relay attacks via tx.origin
tx.origin authorization bypassable through malicious contract
owner verification using tx.origin in delegatecall context
tx.origin based access control in callback functions
authorization checks using tx.origin in receive/fallback
tx.origin validation in permit or meta-transaction handlers
access control mixing tx.origin and msg.sender inconsistently
```

#### Detection Rules
```yaml
rule: tx-origin-auth
conditions:
  - function.uses_tx_origin == true
  - function.tx_origin_in_comparison == true
  - comparison.context IN [require, if, modifier]
  - comparison.involves_access_control == true
severity: high
false_positive_filters:
  - context: gas_refund_to_tx_origin  # legitimate use
  - context: fee_payment_to_originator  # acceptable pattern
```

### 2.2 Bypassable Access Control
**CWE-863**

#### Detection Phrases
```
authorization checks that can be bypassed via delegatecall
access control skippable through callback reentrancy
role verification bypassable via flash loan
auth checks that don't account for proxy context
access control bypassable through create2 address prediction
authorization vulnerable to front-running
role checks bypassable via signature replay
access control not enforced in fallback function
auth verification missing in receive function
access control bypassable through multicall batching
authorization skippable via permit + transferFrom combo
role checks bypassable through governance manipulation
access control not enforced on internal function paths
auth verification missing after state transition
access control bypassable through reentrancy
authorization checks incomplete in modifier
role verification not applied to all entry points
access control bypassable via low-level call
auth checks missing on view functions that affect state indirectly
authorization vulnerable to time-of-check-time-of-use
```

#### Detection Rules
```yaml
rule: bypassable-access-control
conditions:
  any:
    - function.has_delegatecall AND NOT function.validates_delegatecall_target
    - function.is_callback AND NOT function.has_access_control
    - function.callable_via_multicall AND function.has_context_dependent_auth
    - modifier.returns_instead_of_reverts
severity: high
```

### 2.3 Flawed Access Control Logic
**CWE-863**

#### Detection Phrases
```
role checks using OR instead of AND for multiple requirements
modifiers that return instead of revert on failure
access control depending on mutable state that attacker can influence
authorization using == instead of != allowing zero address
role checks with incorrect boolean logic
access control with off-by-one in permission levels
authorization comparing wrong variables
role verification with type confusion vulnerability
access control using string comparison instead of address
authorization with incorrect inheritance of permissions
role checks not accounting for role hierarchy
access control with integer overflow in permission calculation
authorization logic with short-circuit evaluation vulnerability
role verification with incorrect keccak256 comparison
access control comparing hashes instead of values incorrectly
authorization with incorrect modifier order
role checks with side effects in condition
access control using storage variable that can be manipulated
authorization with uninitialized permission variable
role verification with incorrect default value
```

### 2.4 Inconsistent Access Control
**CWE-284**

#### Detection Phrases
```
functions with same purpose having different access controls
admin functions with inconsistent role requirements
setter and getter with mismatched authorization
paired functions (add/remove) with different access levels
similar functions with varying access control stringency
override functions removing parent access restrictions
interface implementations weakening access control
functions in same category with inconsistent auth
view function exposing data that setter protects
administrative functions with varying role requirements
emergency functions with weaker auth than normal operations
batch functions with different auth than single operations
internal vs external versions with mismatched access control
upgradeable functions with inconsistent auth across versions
```

---

## 3. Broken Access Control Logic

### 3.1 Privilege Escalation Paths
**CWE-269**

#### Detection Phrases
```
functions allowing users to grant themselves roles
methods where callers can modify their own permissions
role assignment without proper authorization chain
functions that can elevate privileges without admin approval
self-assignment of admin or owner role possible
methods allowing permission inheritance bypass
functions where lower roles can grant higher roles
privilege escalation via role renouncement and reassignment
methods allowing circular role delegation
functions that can modify role hierarchy without restriction
self-promotion to privileged role via voting manipulation
privilege escalation through proposal execution
methods allowing governance takeover via flash loan
functions where token holders can assume admin privileges
privilege escalation via cross-contract role confusion
methods allowing unauthorized role transfer
functions that can impersonate admin through signature
privilege escalation via unprotected delegatecall
methods allowing role assumption through callback
functions where proxy admin can escalate to owner
```

#### Detection Rules
```yaml
rule: privilege-escalation
conditions:
  - function.modifies_roles == true
  - function.allows_self_modification == true
  - OR:
    - function.has_access_control == false
    - function.access_control_is_same_role_being_modified
severity: critical
```

### 3.2 Missing Privilege Revocation
**CWE-269**

#### Detection Phrases
```
roles that cannot be revoked once granted
admin privileges without removal mechanism
permanent role assignment without expiration
functions granting roles without corresponding revoke
privileges that persist after ownership transfer
roles remaining after contract upgrade
admin access not removable by higher authority
functions granting emergency access without revocation path
privileges not cleared on account deactivation
roles persisting across proxy upgrades
admin access remaining after pause
privileges not revoked when underlying conditions change
roles not cleared on ownership renouncement
admin access surviving contract migration
functions granting time-limited roles without enforcement
```

### 3.3 Default Permission Issues
**CWE-276**

#### Detection Phrases
```
default admin role assigned to zero address
uninitialized role defaulting to all permissions
constructor not setting initial access control
default state granting universal access
uninitialized permission variable defaulting to true
missing default deny policy
new functions defaulting to open access
upgraded contracts with reset permissions
default role hierarchy allowing escalation
uninitialized access control mapping
constructor not restricting default permissions
deployment state with overly permissive defaults
unset role checks defaulting to allow
missing explicit deny for sensitive operations
default state not enforcing principle of least privilege
```

---

## 4. Centralization & Privilege Risks

### 4.1 Single Point of Failure
**CWE-284, CWE-654**

#### Detection Phrases
```
single owner address with ability to drain all funds
admin functions without timelock or multisig
privileged roles that can pause or brick contract permanently
upgrade functions controlled by single EOA
functions allowing owner to change critical parameters without delay
single admin with unrestricted withdrawal capability
owner can modify all protocol parameters instantly
single key controlling emergency functions
admin with ability to seize user funds
single address controlling mint functionality
owner can blacklist any address without recourse
single entity controlling oracle updates
admin with unrestricted proxy upgrade power
single key holder controlling bridge operations
owner can modify fee structure arbitrarily
single address with pause and unpause control
admin controlling liquidation parameters
single entity with veto power over governance
owner with ability to modify vesting schedules
single key controlling token distribution
admin with unrestricted access to reserves
single address controlling migration functions
owner can modify invariants without restriction
single entity controlling cross-chain messaging
admin with ability to front-run users
single key controlling reward distribution
owner with unrestricted minting capability
single address controlling access to funds
admin can modify user balances directly
single entity controlling protocol upgrades
```

#### Detection Rules
```yaml
rule: single-point-of-failure
conditions:
  - function.is_privileged == true
  - function.modifies_critical_state == true
  - contract.owner_is_single_address == true
  - NOT contract.has_timelock
  - NOT contract.has_multisig
severity: high
risk_factors:
  - function.can_drain_funds: critical
  - function.can_pause_protocol: high
  - function.can_modify_parameters: medium
```

### 4.2 Missing Timelock
**CWE-284**

#### Detection Phrases
```
admin functions executing immediately without delay
parameter changes taking effect in same transaction
upgrade functions without timelock protection
critical operations without mandatory waiting period
governance proposals executable without delay
emergency functions lacking cooldown period
admin actions not subject to timelock
configuration changes applying instantly
role assignments without delay mechanism
fee changes taking effect immediately
contract migrations without warning period
oracle updates without delay
strategy changes executing instantly
parameter updates without observation window
critical setters without timelock
admin operations not queued before execution
privilege grants without delay
emergency exits without cooldown
protocol changes without announcement period
```

### 4.3 Insufficient Decentralization
**CWE-284**

#### Detection Phrases
```
multisig threshold set to 1 of N
governance quorum too low for security
voting power concentrated in few addresses
admin keys not distributed across parties
single team controlling majority of governance tokens
timelock admin controlled by single entity
proxy admin not sufficiently distributed
emergency functions requiring only one signature
critical operations not requiring consensus
upgrade decisions controlled by minority
governance weighted heavily toward founders
single organization controlling majority votes
insufficient signer diversity in multisig
team tokens able to override community votes
admin rights not distributed across jurisdictions
emergency council too small for critical decisions
governance capture possible with small capital
decision making not sufficiently decentralized
single cloud provider hosting all admin keys
key management not distributed across hardware
```

### 4.4 Dangerous Admin Functions
**CWE-749**

#### Detection Phrases
```
admin function that can brick contract permanently
owner ability to lock user funds indefinitely
admin power to modify historical data
owner function that breaks invariants
admin capability to create unbacked tokens
owner ability to bypass withdrawal limits
admin function allowing arbitrary state modification
owner power to change immutable parameters
admin capability to selfdestruct contract
owner ability to modify user permissions
admin function that can corrupt accounting
owner power to front-run pending transactions
admin capability to modify oracle responses
owner ability to bypass security checks
admin function that can drain liquidity pools
owner power to modify governance outcomes
admin capability to invalidate signatures
owner ability to replay protected transactions
admin function that can modify merkle roots
owner power to change cross-chain message outcomes
```

---

## 5. Authentication Vulnerabilities

### 5.1 tx.origin Phishing
**CWE-287**

#### Detection Phrases
```
authorization checks using tx.origin instead of msg.sender
tx.origin validation vulnerable to phishing contracts
admin check using tx.origin exploitable via malicious dapp
ownership verification using tx.origin in any context
tx.origin used as authentication in payable functions
transfer authorization based on tx.origin
privileged operations authenticated via tx.origin
withdrawal permitted based on tx.origin check
configuration changes authorized via tx.origin
role verification using tx.origin
tx.origin used in modifier for access control
authentication logic comparing tx.origin to stored owner
tx.origin checked in require for admin functions
privileged path unlocked via tx.origin validation
```

### 5.2 Missing Authentication
**CWE-306**

#### Detection Phrases
```
sensitive operations without any authentication
critical functions with no caller verification
state changes without identity validation
value transfers without authentication
privileged operations assuming trusted context
administrative functions without credential check
sensitive reads without access verification
configuration endpoints without authentication
callback functions without origin validation
external interfaces without authentication layer
administrative API without access control
sensitive operations relying on obscurity
critical functions without authentication mechanism
privileged paths without identity verification
```

### 5.3 Weak Authentication
**CWE-287**

#### Detection Phrases
```
authentication using predictable values
access control based on contract address alone
authentication using only block data
verification based on msg.value only
authentication using caller's code hash
access control relying on extcodesize
authentication based on gas remaining
verification using only timestamp
authentication depending on block number
access control using only balance check
authentication based on storage slot contents
verification relying on transaction index
authentication using nonce as sole credential
access control based on create2 address
authentication depending on chain ID alone
```

---

## 6. Signature & Cryptographic Auth

### 6.1 ecrecover Vulnerabilities
**CWE-347**

#### Detection Phrases
```
ecrecover without checking for zero address return
signature verification accepting zero address signer
ecrecover result used without null check
recovered address not validated against expected signer
ecrecover called without verifying non-zero result
signature validation missing zero address guard
recovered signer not checked for address(0)
ecrecover result compared without null validation
signature verification vulnerable to null signer
ecrecover output used directly without validation
recovered address accepted without zero check
signature auth missing address(0) rejection
ecrecover not handling invalid signature edge case
recovered signer used without existence check
signature verification accepting empty signature
```

#### Detection Rules
```yaml
rule: ecrecover-zero-check
conditions:
  - function.uses_ecrecover == true
  - NOT function.checks_recovered_address_nonzero
severity: high
```

### 6.2 Signature Replay
**CWE-294**

#### Detection Phrases
```
signatures without nonce allowing replay attacks
signed messages reusable across transactions
signature verification without incremented counter
permit functions vulnerable to replay
authorization signature without sequence number
signed approval replayable within same chain
signature accepted multiple times
verification without tracking used signatures
signed message without unique identifier
authorization replayable after state change
signature valid across multiple calls
verification not invalidating used signatures
signed permit without nonce increment
authorization signature without expiry tracking
signature replayable in different context
verification missing replay protection
signed message valid indefinitely
authorization without one-time use enforcement
signature not bound to specific transaction
verification allowing signature resubmission
```

#### Detection Rules
```yaml
rule: signature-replay
conditions:
  - function.verifies_signature == true
  - NOT function.uses_nonce
  - NOT function.tracks_used_signatures
  - NOT function.signature_bound_to_state
severity: high
```

### 6.3 Cross-Chain Replay
**CWE-294**

#### Detection Phrases
```
signatures without chainId allowing cross-chain replay
signed messages missing chain identifier
permit functions vulnerable to cross-chain attack
authorization valid across multiple networks
signature without network binding
verification missing chain ID validation
signed message replayable on forked chain
authorization vulnerable to chain split replay
signature valid on mainnet and testnet
verification not checking deployment chain
signed permit without chain restriction
authorization replayable after hard fork
signature not bound to specific network
verification accepting signature from other chain
signed message without domain separator chain ID
authorization vulnerable to bridge replay
signature valid across L1 and L2
verification missing chain context
signed permit replayable on sidechain
authorization without chain-specific binding
```

### 6.4 Signature Malleability
**CWE-347**

#### Detection Phrases
```
ECDSA signatures without s-value normalization
signature verification vulnerable to malleability
ecrecover accepting both s values
signed message verification without canonical check
signature validation missing lower-s requirement
ECDSA without checking s is in lower half
verification accepting malleable signatures
signature not normalized before verification
ecrecover vulnerable to signature mutation
signed authorization without canonical form check
signature verification accepting modified signatures
ECDSA validation missing malleability protection
verification not enforcing signature uniqueness
signature accepted with flipped s value
ecrecover without EIP-2 compliance
signed message vulnerable to third-party modification
signature verification without strict validation
ECDSA accepting non-canonical signatures
verification vulnerable to signature transformation
signature not checked for canonical encoding
```

### 6.5 Missing Deadline/Expiry
**CWE-613**

#### Detection Phrases
```
signature verification without deadline or expiry
signed permits valid indefinitely
authorization signature without time limit
signature accepted regardless of age
verification missing timestamp validation
signed message without expiration check
authorization valid until revoked only
signature without deadline parameter
verification not enforcing time bounds
signed permit without expiry timestamp
authorization missing validity period
signature accepted long after creation
verification without deadline enforcement
signed message with infinite validity
authorization signature never expiring
signature verification missing time check
signed approval without time restriction
authorization valid beyond reasonable period
signature without maximum age validation
verification accepting stale signatures
```

### 6.6 Domain Separator Issues
**CWE-347**

#### Detection Phrases
```
EIP-712 signatures without domain separator
signed typed data missing domain binding
signature without contract address binding
verification missing domain hash
signed message without name and version
authorization signature without domain context
signature not bound to specific contract
verification missing verifyingContract check
signed permit without proper domain
authorization vulnerable to domain confusion
signature replayable across contracts
verification without domain separator validation
signed message missing chainId in domain
authorization signature without domain fields
signature not following EIP-712 standard
verification accepting different domain
signed permit with incomplete domain separator
authorization missing contract binding
signature vulnerable to domain substitution
verification not validating domain hash
```

---

## 7. Role-Based Access Control Issues

### 7.1 RBAC Implementation Flaws
**CWE-284**

#### Detection Phrases
```
role assignment without proper authorization
role hierarchy not enforced correctly
admin role assignable by non-admin
role revocation not cascading to dependent roles
role checks not accounting for hierarchy
role assignment without event emission
admin role transferable without multi-step
role verification missing in inherited functions
role grants not subject to timelock
admin role removable leaving no admin
role checks inconsistent across functions
role assignment allowing self-promotion
admin role bypassable through role combination
role verification using wrong role identifier
role grants not requiring existing role
admin role revocable by lower roles
role checks with incorrect keccak256 hash
role assignment without previous holder consent
admin role hierarchy implemented incorrectly
role verification not checking all required roles
```

### 7.2 Role Enumeration Issues
**CWE-284**

#### Detection Phrases
```
role members not trackable for audit
role count not maintained accurately
role assignment without membership update
admin role enumeration incomplete
role holder list not synchronized
role revocation not removing from enumeration
admin role members queryable but inaccurate
role assignment duplicating members
role holder count incorrect after revocation
admin role enumeration vulnerable to DoS
role membership not paginated for large sets
role assignment not updating member index
admin role enumeration exposing sensitive info
role holder iteration vulnerable to gas limit
role membership query returning stale data
admin role enumeration missing access control
role assignment not maintaining insertion order
role holder list not bounded
admin role enumeration not optimized for reads
role membership not indexed for lookup
```

### 7.3 Default Admin Issues
**CWE-276**

#### Detection Phrases
```
DEFAULT_ADMIN_ROLE assigned to zero address
default admin not set in constructor
admin role defaulting to deployer implicitly
DEFAULT_ADMIN_ROLE not properly initialized
default admin transferable without confirmation
admin role default not following best practices
DEFAULT_ADMIN_ROLE grantable by itself
default admin not set before renouncing
admin role initialization order incorrect
DEFAULT_ADMIN_ROLE hierarchy misconfigured
default admin lost after ownership transfer
admin role default overridable by attacker
DEFAULT_ADMIN_ROLE not revocable
default admin set to contract address
admin role initialization vulnerable to front-run
DEFAULT_ADMIN_ROLE passed to untrusted address
default admin not verified post-deployment
admin role default not documented
DEFAULT_ADMIN_ROLE can grant any role
default admin powers not properly scoped
```

---

## 8. Multi-Sig & Governance Auth

### 8.1 Multi-Sig Vulnerabilities
**CWE-284**

#### Detection Phrases
```
multisig threshold modifiable by single signer
signer addition not requiring threshold signatures
multisig execution without proper signature validation
threshold reduction to 1 possible
signer removal not updating threshold properly
multisig nonce reusable after rejection
threshold increase above signer count possible
signer replacement not atomic
multisig vulnerable to signature front-running
threshold changes taking effect immediately
signer removal leaving multisig inoperable
multisig execution order manipulable
threshold set to zero possible
signer addition without existing signer approval
multisig replay possible after signer change
threshold not enforced on emergency functions
signer key rotation not properly handled
multisig vulnerable to transaction substitution
threshold enforcement bypassable via batching
signer enumeration not properly maintained
```

### 8.2 Governance Auth Issues
**CWE-284**

#### Detection Phrases
```
governance proposal executable without quorum
voting power snapshot not at proposal creation
proposal execution without timelock
governance bypass possible via flash loan voting
quorum calculation using current not snapshot balance
proposal threshold too low for security
governance votes countable after deadline
quorum met using borrowed tokens
proposal cancellation not properly authorized
governance delegation vulnerable to manipulation
voting power calculation with precision errors
proposal execution before voting ends
governance snapshot timing exploitable
quorum calculation excluding delegated votes incorrectly
proposal creation spam not rate limited
governance vote counting with rounding errors
voting extension manipulation possible
proposal state transition not properly validated
governance timelock bypassable
vote delegation circular dependency possible
```

### 8.3 Timelock Issues
**CWE-284**

#### Detection Phrases
```
timelock delay modifiable without delay
timelock admin changeable immediately
queued transaction cancellable by non-admin
timelock delay settable to zero
admin transfer not subject to timelock
timelock grace period too short
queued transaction executable early
timelock bypass through direct call
delay not enforced on critical operations
timelock admin role not properly protected
queued transaction replayable after execution
timelock state not properly synchronized
delay changes affecting queued transactions
timelock emergency bypass too permissive
queued transaction hash collision possible
timelock predecessor requirement bypassable
delay enforcement inconsistent across functions
timelock cancellation not properly authorized
grace period exploitable for MEV
timelock state readable for front-running
```

---

## 9. Time-Based Access Control

### 9.1 Timestamp Dependence
**CWE-829**

#### Detection Phrases
```
access control using block.timestamp manipulable by miners
authorization window based on single timestamp check
time-locked function vulnerable to timestamp manipulation
access period boundaries using block timestamp
authorization valid within miner-influenceable timeframe
time-based access with tight timestamp tolerance
access control deadline using block.timestamp
authorization expiry within miner manipulation range
time-locked release using timestamp directly
access window edges vulnerable to manipulation
authorization based on exact timestamp match
time-based roles with timestamp dependence
access periods defined by manipulable timestamps
authorization timing vulnerable to block manipulation
time-locked vesting using block.timestamp
access schedule with miner-influenceable boundaries
authorization windows without safety margins
time-based permissions using single block time
access control with timestamp precision issues
authorization deadlines vulnerable to minor manipulation
```

### 9.2 Time Lock Bypass
**CWE-284**

#### Detection Phrases
```
timelock bypassed through emergency function
time restriction not enforced after upgrade
lock period resetable by admin
timelock bypassed via delegatecall
time restriction not applying to all entry points
lock period calculation with overflow
timelock bypassed through reentrancy
time restriction using wrong clock
lock period not enforced in proxy
timelock bypass via multicall
time restriction not checked in modifier
lock period overridable by privileged role
timelock state not persisted across upgrades
time restriction bypassed via signature
lock period not enforced for batch operations
timelock bypass through governance
time restriction not applying to internal calls
lock period calculation with precision loss
timelock state manipulable externally
time restriction not synchronized across contracts
```

---

## 10. Cross-Contract Authorization

### 10.1 Cross-Contract Auth Issues
**CWE-284**

#### Detection Phrases
```
authorization not validated across contract calls
caller verification lost in delegatecall chain
access control not preserved in callback
authorization context incorrect in external call
caller identity confused in cross-contract interaction
access control not enforced in called contract
authorization relying on msg.sender in delegatecall
caller verification missing after external call
access control assuming direct call only
authorization not checking full call chain
caller identity spoofable via intermediary contract
access control not accounting for proxy calls
authorization relying on storage context incorrectly
caller verification not preserved across hops
access control confused by create2 deployment
authorization checking wrong contract context
caller identity lost in reentrant call
access control not validating call origin
authorization assuming specific call path
caller verification spoofable via callback
```

### 10.2 Delegatecall Auth Issues
**CWE-284**

#### Detection Phrases
```
delegatecall target not validated for authorization
access control lost when called via delegatecall
delegatecall preserving msg.sender inappropriately
authorization bypass through delegatecall chain
delegatecall not restricted to trusted targets
access control relying on code context
delegatecall allowing privilege escalation
authorization not checking execution context
delegatecall to arbitrary implementation
access control vulnerable to delegatecall from malicious contract
delegatecall not validating caller in target
authorization assuming direct execution context
delegatecall target modifiable by attacker
access control not enforced in library calls
delegatecall context confusion in modifiers
authorization relying on this address incorrectly
delegatecall preserving storage context unexpectedly
access control not accounting for proxy patterns
delegatecall allowing storage manipulation
authorization bypass via fallback delegatecall
```

### 10.3 Callback Authorization
**CWE-284**

#### Detection Phrases
```
callback function without caller validation
authorization not checked in callback context
callback allowing unauthorized state changes
access control missing in hook functions
callback not validating expected caller
authorization context incorrect in callback
callback accepting calls from any address
access control relying on callback parameter
callback not enforcing same-transaction requirement
authorization not preserved through callback
callback vulnerable to unauthorized invocation
access control not checking callback initiator
callback allowing reentrancy with different auth
authorization bypass via malicious callback
callback not validating callback data authenticity
access control missing in notification handlers
callback accepting calls from cloned contracts
authorization not enforcing callback sequence
callback vulnerable to cross-contract manipulation
access control not validating callback chain
```

---

## Complex Query Examples for Authority Lens

### Query 1: Critical Unprotected Functions
```json
{
  "query_kind": "logic",
  "node_types": ["Function"],
  "match": {
    "all": [
      {"property": "visibility", "op": "in", "value": ["public", "external"]},
      {"property": "writes_state", "op": "eq", "value": true}
    ],
    "none": [
      {"property": "has_onlyOwner", "op": "eq", "value": true},
      {"property": "has_onlyRole", "op": "eq", "value": true},
      {"property": "has_require_msg_sender", "op": "eq", "value": true},
      {"property": "has_access_modifier", "op": "eq", "value": true}
    ]
  },
  "paths": [{
    "edge_type": "MODIFIES",
    "target_type": "StateVariable",
    "target_constraints": {
      "any": [
        {"property": "is_owner_related", "op": "eq", "value": true},
        {"property": "is_balance_related", "op": "eq", "value": true},
        {"property": "is_admin_related", "op": "eq", "value": true}
      ]
    }
  }],
  "explain_mode": true,
  "limit": 50
}
```

### Query 2: tx.origin Usage in Auth
```json
{
  "query_kind": "logic",
  "node_types": ["Function"],
  "match": {
    "all": [
      {"property": "uses_tx_origin", "op": "eq", "value": true},
      {"property": "tx_origin_in_require", "op": "eq", "value": true}
    ]
  },
  "edges": [{
    "edge_type": "COMPARES",
    "constraints": {
      "left_or_right": "tx.origin",
      "comparison_op": "eq"
    }
  }],
  "explain_mode": true
}
```

### Query 3: Signature Verification Issues
```json
{
  "query_kind": "logic",
  "node_types": ["Function"],
  "match": {
    "all": [
      {"property": "uses_ecrecover", "op": "eq", "value": true}
    ],
    "any_missing": [
      {"property": "checks_zero_address", "op": "eq", "value": true},
      {"property": "has_nonce_check", "op": "eq", "value": true},
      {"property": "has_deadline_check", "op": "eq", "value": true},
      {"property": "has_domain_separator", "op": "eq", "value": true}
    ]
  },
  "explain_mode": true
}
```

### Query 4: Centralization Risk Assessment
```json
{
  "query_kind": "logic",
  "node_types": ["Function"],
  "match": {
    "all": [
      {"property": "is_privileged_operation", "op": "eq", "value": true},
      {"property": "can_affect_user_funds", "op": "eq", "value": true}
    ]
  },
  "contract_context": {
    "none": [
      {"property": "has_timelock", "op": "eq", "value": true},
      {"property": "has_multisig", "op": "eq", "value": true}
    ]
  },
  "explain_mode": true
}
```

---

## Pattern Pack: Authority Lens Complete

```yaml
# Save as patterns/authority-lens.yaml
patterns:
  - id: auth-001
    name: Unprotected State Writer
    severity: critical
    cwe: [284, 285]

  - id: auth-002
    name: tx.origin Authentication
    severity: high
    cwe: [287]

  - id: auth-003
    name: Missing Signature Validation
    severity: high
    cwe: [347]

  - id: auth-004
    name: Signature Replay Vulnerability
    severity: high
    cwe: [294]

  - id: auth-005
    name: Centralization Single Point of Failure
    severity: high
    cwe: [284, 654]

  - id: auth-006
    name: Unprotected Initializer
    severity: critical
    cwe: [665, 284]

  - id: auth-007
    name: Privilege Escalation Path
    severity: critical
    cwe: [269]

  - id: auth-008
    name: Missing Timelock
    severity: medium
    cwe: [284]

  - id: auth-009
    name: Bypassable Access Control
    severity: high
    cwe: [863]

  - id: auth-010
    name: Cross-Contract Auth Confusion
    severity: high
    cwe: [284]
```
