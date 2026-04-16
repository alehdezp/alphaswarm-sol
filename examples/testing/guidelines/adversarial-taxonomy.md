# Adversarial Obfuscation Taxonomy

Defines adversarial techniques for generating hostile Solidity test projects that stress-test
the AlphaSwarm.sol detection engine. Each technique targets a specific detection capability
failure mode.

**Goal:** Generated projects should BREAK the engine, not test the happy path.

---

## Category A: Name Obfuscation

**Tests:** Whether detection relies on semantic operations vs function/variable names.

A well-built detector should identify `TRANSFERS_VALUE_OUT` + `WRITES_USER_BALANCE` ordering
regardless of what the function is called. These techniques expose name-based shortcuts.

### Technique A1: Function Renaming

**Difficulty:** Easy
**Target:** Detectors that match function names like `withdraw`, `transfer`, `approve`.

Rename vulnerability-bearing functions to business-domain names that hide their true behavior.

```solidity
// VULNERABLE: Classic reentrancy, but no "withdraw" in sight
contract YieldOptimizer {
    mapping(address => uint256) private _allocations;

    // "processRequest" is actually a withdrawal function
    function processRequest(uint256 requestId) external {
        uint256 amount = _allocations[msg.sender];
        require(amount > 0, "No allocation");

        // External call before state update (reentrancy)
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Transfer failed");

        _allocations[msg.sender] = 0;  // State update AFTER call
    }
}
```

**Compilation:** Requires `pragma solidity ^0.8.0;`

### Technique A2: Misleading Names

**Difficulty:** Medium
**Target:** Detectors that trust function names as semantic signals.

Use names that imply safety but perform unsafe operations.

```solidity
contract SafeVault {
    mapping(address => uint256) private balances;

    // Name says "safe" but there's no reentrancy guard
    function safeTransfer(address to, uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient");
        // Missing: nonReentrant modifier
        (bool success, ) = to.call{value: amount}("");
        require(success, "Failed");
        balances[msg.sender] -= amount;  // State update after call
    }

    // Name says "protected" but anyone can call it
    function protectedMint(uint256 amount) external {
        // Missing: onlyOwner or access control
        balances[msg.sender] += amount;
    }
}
```

### Technique A3: Dead Code Red Herrings

**Difficulty:** Medium
**Target:** Detectors that report findings in unreachable code paths.

Insert safe-looking functions that are never called, alongside real vulnerabilities
in actively used functions.

```solidity
contract StakingPool {
    mapping(address => uint256) private stakes;
    bool private _locked;

    // This function is SAFE but never called (dead code)
    function _safeWithdraw(uint256 amount) internal {
        _locked = true;
        stakes[msg.sender] -= amount;
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok);
        _locked = false;
    }

    // This function is the REAL vulnerability (actually used)
    function unstake() external {
        uint256 amount = stakes[msg.sender];
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok);
        stakes[msg.sender] = 0;  // Reentrancy: state after call
    }

    // This calls unstake, never _safeWithdraw
    function exitPool() external {
        this.unstake();
    }
}
```

### Technique A4: Variable Aliasing

**Difficulty:** Medium
**Target:** Detectors that track specific variable names rather than data flow.

Pass the same value through multiple aliases, indirections, and temporary storage.

```solidity
contract LiquidityManager {
    mapping(address => uint256) private _positions;

    function rebalance(address user) external {
        // Alias chain: positions -> cached -> temp -> amount
        uint256 cached = _positions[user];
        uint256 temp = cached;
        uint256 amount = temp;

        // The external call uses the aliased amount
        (bool ok, ) = user.call{value: amount}("");
        require(ok);

        // State update after call (reentrancy via aliasing)
        _positions[user] = 0;
    }
}
```

### Technique A5: Parameter Reordering

**Difficulty:** Easy
**Target:** Detectors that expect specific parameter positions.

Swap expected parameter positions so the "amount" parameter is not in the typical slot.

```solidity
contract TokenBridge {
    mapping(address => uint256) private deposits;

    // Parameters in unusual order: nonce first, amount last
    function processWithdrawal(
        uint256 nonce,
        bytes calldata proof,
        address recipient,
        uint256 amount
    ) external {
        require(deposits[recipient] >= amount, "Insufficient");
        // Vulnerability: no access control, anyone can call
        deposits[recipient] -= amount;
        (bool ok, ) = recipient.call{value: amount}("");
        require(ok);
    }
}
```

### Technique A6: Encoding Indirection

**Difficulty:** Hard
**Target:** Detectors that match direct calls vs encoded/delegated calls.

Use abi.encode/decode and low-level calls to hide the actual operation being performed.

```solidity
contract StrategyExecutor {
    mapping(address => uint256) private shares;

    function executeStrategy(bytes calldata data) external {
        // Decode hidden withdrawal parameters
        (address target, uint256 amt) = abi.decode(data, (address, uint256));

        // Low-level call hides the transfer semantics
        (bool ok, bytes memory result) = target.call{value: amt}("");
        require(ok, "Strategy failed");

        // State update after the hidden external call
        shares[msg.sender] -= amt;
    }
}
```

---

## Category B: Protocol Complexity

**Tests:** Cross-contract reasoning, temporal state analysis, and inheritance-aware detection.

Real DeFi protocols are multi-contract systems where vulnerabilities span contracts,
transactions, and inheritance hierarchies. These techniques expose detectors that only
analyze single functions in isolation.

### Technique B1: Multi-Contract Split Vulnerabilities

**Difficulty:** Hard
**Target:** Detectors limited to single-contract analysis.

Split the vulnerability across two or more contracts so no single contract
looks vulnerable in isolation.

```solidity
// Contract 1: Handles accounting (looks safe alone)
contract AccountingModule {
    mapping(address => uint256) public balances;

    function recordWithdrawal(address user, uint256 amount) external {
        // Only updates state -- no external calls here
        balances[user] -= amount;
    }

    function getBalance(address user) external view returns (uint256) {
        return balances[user];
    }
}

// Contract 2: Handles transfers (vulnerability emerges in combination)
contract TransferModule {
    AccountingModule public accounting;

    constructor(address _accounting) {
        accounting = AccountingModule(_accounting);
    }

    function withdraw() external {
        uint256 amount = accounting.getBalance(msg.sender);

        // External call BEFORE accounting update
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok);

        // Cross-contract state update happens AFTER the external call
        accounting.recordWithdrawal(msg.sender, amount);
    }
}
```

### Technique B2: Proxy/Delegate Pattern Hiding

**Difficulty:** Hard
**Target:** Detectors that don't follow delegatecall chains.

Use proxy patterns to separate storage from logic, hiding the vulnerability
in the implementation contract behind a proxy facade.

```solidity
contract VaultProxy {
    address public implementation;
    address public admin;

    fallback() external payable {
        address impl = implementation;
        assembly {
            calldatacopy(0, 0, calldatasize())
            let result := delegatecall(gas(), impl, 0, calldatasize(), 0, 0)
            returndatacopy(0, 0, returndatasize())
            switch result
            case 0 { revert(0, returndatasize()) }
            default { return(0, returndatasize()) }
        }
    }
}

// Implementation has the vulnerability but is called via proxy
contract VaultImplementation {
    mapping(address => uint256) private deposits;

    // Vulnerable to reentrancy when called through proxy
    function withdraw(uint256 amount) external {
        require(deposits[msg.sender] >= amount);
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok);
        deposits[msg.sender] -= amount;
    }
}
```

### Technique B3: State Machine Violations

**Difficulty:** Hard
**Target:** Detectors that don't track multi-transaction state transitions.

Create state machines where the vulnerability only manifests when specific
state transitions are executed in a particular order across multiple transactions.

```solidity
contract AuctionHouse {
    enum Phase { BIDDING, SETTLEMENT, FINALIZED }
    Phase public currentPhase;
    mapping(address => uint256) public bids;
    address public highestBidder;

    function bid() external payable {
        require(currentPhase == Phase.BIDDING);
        bids[msg.sender] += msg.value;
        if (bids[msg.sender] > bids[highestBidder]) {
            highestBidder = msg.sender;
        }
    }

    // Vulnerability: can be called multiple times before finalization
    function settle() external {
        require(currentPhase == Phase.BIDDING);
        currentPhase = Phase.SETTLEMENT;
        // Missing: should only allow highestBidder or admin
    }

    // State machine violation: settle() doesn't prevent re-entry to BIDDING
    function reopenBidding() external {
        require(currentPhase == Phase.SETTLEMENT);
        // Missing: onlyAdmin check
        currentPhase = Phase.BIDDING;
        // Bids from previous round are still active!
    }
}
```

### Technique B4: Inherited Vulnerability via Contract Hierarchy

**Difficulty:** Medium
**Target:** Detectors that don't trace inherited functions and virtual overrides.

Place the vulnerability in a base contract, then create a child that inherits
the vulnerable behavior through virtual function overrides.

```solidity
abstract contract BaseVault {
    mapping(address => uint256) internal _balances;

    // Base implementation: looks fine, follows CEI
    function _processWithdrawal(address user) internal virtual {
        uint256 amount = _balances[user];
        _balances[user] = 0;
        _transfer(user, amount);
    }

    function _transfer(address to, uint256 amount) internal virtual;
}

contract AdvancedVault is BaseVault {
    // Override breaks CEI pattern from base
    function _processWithdrawal(address user) internal override {
        uint256 amount = _balances[user];
        // External call BEFORE state update (overrides safe base behavior)
        _transfer(user, amount);
        _balances[user] = 0;
    }

    function _transfer(address to, uint256 amount) internal override {
        (bool ok, ) = to.call{value: amount}("");
        require(ok);
    }

    function withdraw() external {
        _processWithdrawal(msg.sender);
    }
}
```

### Technique B5: Library-Mediated Exploits

**Difficulty:** Medium
**Target:** Detectors that don't analyze library code alongside caller code.

Create a library with a subtle vulnerability that only manifests when used
by a specific caller pattern.

```solidity
library TransferLib {
    // Library function looks safe: just does a transfer
    function safeTransfer(address to, uint256 amount) internal returns (bool) {
        (bool ok, ) = to.call{value: amount}("");
        return ok;
    }
}

contract RewardDistributor {
    using TransferLib for address;
    mapping(address => uint256) private rewards;

    function claim() external {
        uint256 amount = rewards[msg.sender];
        require(amount > 0, "Nothing to claim");

        // Library call makes external transfer (hidden reentrancy surface)
        bool ok = msg.sender.safeTransfer(amount);
        require(ok, "Transfer failed");

        // State update after library-mediated external call
        rewards[msg.sender] = 0;
    }
}
```

### Technique B6: Callback-Driven State Corruption

**Difficulty:** Hard
**Target:** Detectors that don't model callback control flow.

Use legitimate callback mechanisms (ERC-721 onERC721Received, flash loan callbacks)
as the reentrancy vector.

```solidity
import "@openzeppelin/contracts/token/ERC721/IERC721Receiver.sol";

contract NFTMarketplace {
    mapping(uint256 => address) public listings;
    mapping(uint256 => uint256) public prices;
    mapping(address => uint256) public proceeds;

    function purchase(uint256 tokenId) external payable {
        require(msg.value >= prices[tokenId], "Underpaid");
        address seller = listings[tokenId];

        // Safe transfer triggers onERC721Received callback
        // Buyer's contract can re-enter during callback
        IERC721(nftContract).safeTransferFrom(address(this), msg.sender, tokenId);

        // State updates after callback-triggering transfer
        proceeds[seller] += msg.value;
        delete listings[tokenId];
        delete prices[tokenId];
    }
}
```

---

## Category C: Honeypot Inversions

**Tests:** False-positive resistance. Can the detector correctly identify SAFE code
that superficially resembles a vulnerability?

High false-positive rates destroy trust. These techniques create safe code that
looks suspicious to naive detectors.

### Technique C1: Safe Code with Dangerous Names

**Difficulty:** Easy
**Target:** Detectors that flag based on function name patterns.

Functions named `withdraw`, `transfer`, `approve` that are actually properly guarded
and follow best practices.

```solidity
contract SecureBank {
    mapping(address => uint256) private balances;
    bool private _locked;

    modifier nonReentrant() {
        require(!_locked, "Reentrancy");
        _locked = true;
        _;
        _locked = false;
    }

    // Named "withdraw" but fully protected
    function withdraw(uint256 amount) external nonReentrant {
        require(balances[msg.sender] >= amount, "Insufficient");
        balances[msg.sender] -= amount;  // State update BEFORE call (CEI)
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Transfer failed");
    }

    // Named "unsafeTransfer" but actually follows CEI
    function unsafeTransfer(address to, uint256 amount) external nonReentrant {
        require(balances[msg.sender] >= amount);
        balances[msg.sender] -= amount;
        balances[to] += amount;
        emit Transfer(msg.sender, to, amount);
    }

    event Transfer(address indexed from, address indexed to, uint256 amount);
}
```

### Technique C2: Complex but Correct Access Control

**Difficulty:** Medium
**Target:** Detectors that flag multi-step access control as suspicious.

Implement access control with multiple layers (roles, timelock, multisig) that
looks complex but is actually correctly configured.

```solidity
contract GovernanceVault {
    mapping(address => bool) public governors;
    mapping(address => bool) public guardians;
    uint256 public timelockDuration;
    mapping(bytes32 => uint256) public proposalTimestamps;

    modifier onlyGovernorOrGuardian() {
        require(governors[msg.sender] || guardians[msg.sender], "Unauthorized");
        _;
    }

    modifier afterTimelock(bytes32 proposalId) {
        require(proposalTimestamps[proposalId] > 0, "Not proposed");
        require(
            block.timestamp >= proposalTimestamps[proposalId] + timelockDuration,
            "Timelock active"
        );
        _;
    }

    // Looks complex but every path is properly guarded
    function executeProposal(bytes32 proposalId, address target, bytes calldata data)
        external
        onlyGovernorOrGuardian
        afterTimelock(proposalId)
    {
        delete proposalTimestamps[proposalId];
        (bool ok, ) = target.call(data);
        require(ok, "Execution failed");
    }
}
```

### Technique C3: Defense-in-Depth That Looks Vulnerable

**Difficulty:** Hard
**Target:** Detectors that don't recognize layered defense patterns.

Stack multiple protections (reentrancy guard + CEI + access control + pausable)
so each individual pattern might look suspicious but the combination is safe.

```solidity
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract FortifiedVault is ReentrancyGuard, Pausable, Ownable {
    mapping(address => uint256) private deposits;
    uint256 public withdrawalLimit;

    function withdraw(uint256 amount)
        external
        nonReentrant     // Layer 1: reentrancy guard
        whenNotPaused    // Layer 2: pausable
    {
        require(amount <= withdrawalLimit, "Exceeds limit");  // Layer 3: amount limit
        require(deposits[msg.sender] >= amount, "Insufficient");

        deposits[msg.sender] -= amount;  // Layer 4: CEI pattern

        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Transfer failed");
    }
}
```

### Technique C4: Unreachable Vulnerable Code Paths

**Difficulty:** Medium
**Target:** Detectors that don't perform reachability analysis.

Include code that CONTAINS real vulnerability patterns but is guarded by
conditions that make the vulnerable path unreachable.

```solidity
contract ConditionalVault {
    mapping(address => uint256) private balances;
    bool public immutable SAFETY_ENABLED = true;

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount);

        if (!SAFETY_ENABLED) {
            // This path is UNREACHABLE (SAFETY_ENABLED is immutable true)
            // But it contains a real reentrancy pattern
            (bool ok, ) = msg.sender.call{value: amount}("");
            require(ok);
            balances[msg.sender] -= amount;
        } else {
            // This is the ACTUAL path -- safe CEI pattern
            balances[msg.sender] -= amount;
            (bool ok, ) = msg.sender.call{value: amount}("");
            require(ok);
        }
    }
}
```

### Technique C5: Deliberately Misleading Comments

**Difficulty:** Easy
**Target:** Detectors that use comments or NatSpec as semantic signals.

Write comments that say the code is unsafe or vulnerable when it is actually safe.

```solidity
contract MisleadingDocs {
    mapping(address => uint256) private balances;
    bool private _locked;

    modifier nonReentrant() {
        require(!_locked);
        _locked = true;
        _;
        _locked = false;
    }

    /// @notice WARNING: This function is vulnerable to reentrancy!
    /// @dev TODO: Fix this before mainnet deployment
    /// @dev KNOWN BUG: Does not follow CEI pattern
    function withdraw(uint256 amount) external nonReentrant {
        // UNSAFE: The line below should come after the transfer
        balances[msg.sender] -= amount;  // Actually safe: state update BEFORE call

        // VULNERABLE: No reentrancy protection
        (bool ok, ) = msg.sender.call{value: amount}("");  // Actually safe: has nonReentrant
        require(ok);
    }
}
```

### Technique C6: Correct Use of Known-Dangerous Patterns

**Difficulty:** Medium
**Target:** Detectors that flag patterns like `delegatecall` or `selfdestruct` without context.

Use patterns that are dangerous in isolation but correct when properly constrained.

```solidity
contract UpgradeableProxy {
    address public implementation;
    address public admin;

    modifier onlyAdmin() {
        require(msg.sender == admin, "Not admin");
        _;
    }

    // delegatecall is the CORRECT pattern here (this is a proxy)
    fallback() external payable {
        address impl = implementation;
        assembly {
            calldatacopy(0, 0, calldatasize())
            let result := delegatecall(gas(), impl, 0, calldatasize(), 0, 0)
            returndatacopy(0, 0, returndatasize())
            switch result
            case 0 { revert(0, returndatasize()) }
            default { return(0, returndatasize()) }
        }
    }

    // Upgrade is admin-only (properly access-controlled)
    function upgradeTo(address newImpl) external onlyAdmin {
        require(newImpl != address(0), "Zero address");
        implementation = newImpl;
    }
}
```

---

## Difficulty Matrix

| Technique | Difficulty | Primary Failure Mode |
|-----------|-----------|---------------------|
| A1: Function Renaming | Easy | Name-based detection |
| A2: Misleading Names | Medium | Trust in naming conventions |
| A3: Dead Code Red Herrings | Medium | Reachability analysis |
| A4: Variable Aliasing | Medium | Data flow tracking |
| A5: Parameter Reordering | Easy | Positional assumptions |
| A6: Encoding Indirection | Hard | Low-level call analysis |
| B1: Multi-Contract Split | Hard | Cross-contract analysis |
| B2: Proxy/Delegate Hiding | Hard | Delegatecall following |
| B3: State Machine Violations | Hard | Temporal reasoning |
| B4: Inherited Vulnerability | Medium | Inheritance analysis |
| B5: Library-Mediated Exploits | Medium | Library code inclusion |
| B6: Callback-Driven Corruption | Hard | Callback modeling |
| C1: Safe Dangerous Names | Easy | Name-based false positives |
| C2: Complex Correct ACL | Medium | Multi-check recognition |
| C3: Defense-in-Depth | Hard | Layered defense recognition |
| C4: Unreachable Paths | Medium | Reachability analysis |
| C5: Misleading Comments | Easy | Comment-based signals |
| C6: Correct Dangerous Patterns | Medium | Context-free flagging |

---

## Usage in Generation

When generating adversarial test projects, apply techniques from this taxonomy:

- **Tier 1 (Basic):** 1-2 techniques from Category A only
- **Tier 2 (Complex):** 2-3 techniques from Categories A and B
- **Tier 3 (Adversarial):** 3+ techniques from all three categories, including C (honeypots)

Each generated project should specify which techniques were applied in its `ground-truth.yaml`
so that detection failures can be traced to specific adversarial categories.
