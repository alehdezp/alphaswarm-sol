# GAP-06/07/08 Resolution: Corpus Strategy for AI Security Reasoning Validation

**Created:** 2026-02-12
**Resolves:** GAP-06 (Adversarial/Trick Scenarios), GAP-07 (Pattern-Derived Generation), GAP-08 (External Source Integration)
**Status:** Resolution complete -- ready for 3.1b-06 implementation

---

## 1. Corpus Strategy Overview

These three gaps form a unified **corpus strategy** answering one question: _How do we build a test corpus that validates genuine AI security reasoning rather than measuring recall of memorized training data?_

The strategy has three interlocking pillars:

```
                    CORPUS STRATEGY
                         |
          +--------------+--------------+
          |              |              |
     GAP-06          GAP-07          GAP-08
   Adversarial    Pattern-Derived   External Source
    Scenarios      Generation        Mapping
          |              |              |
    "Can it resist   "Can it detect  "What categories
     being tricked?"  from specs?"    need coverage?"
          |              |              |
          +--------------+--------------+
                         |
              TRAINING DATA CONTAMINATION
                    PROTOCOL
                  (Cross-cutting)
                         |
              CURATED CORPUS (10-12 scenarios)
```

**Key Insight:** External sources (GAP-08) provide category coverage analysis and inspiration for what vulnerability TYPES to test. Patterns (GAP-07) provide the behavioral specification for HOW to construct each test. Adversarial techniques (GAP-06) ensure the tests measure REASONING, not memorization. The contamination protocol is the binding constraint across all three.

---

## 2. GAP-06 Resolution: Adversarial Scenario Guidelines

### 2.1 The Core Problem

Every well-known vulnerable contract (Ethernaut, DamnVulnerableDeFi, kadenzipfel examples, SWC test cases) exists in LLM training data from 2024 onward. An agent that "detects" the classic DAO reentrancy might be reciting memorized knowledge, not analyzing code. Testing with recognizable contracts measures **recall**, not **reasoning**.

Adversarial scenarios flip the test: instead of asking "can you find the vulnerability?", they ask "can you find it when I actively try to hide it?" and "can you avoid reporting one that does not exist?"

### 2.2 Three Adversarial Categories

#### Category A: Name Obfuscation (Behavior vs. Names)

Tests the core philosophy: "Names lie. Behavior does not."

| Trick Technique | What It Validates | Difficulty |
|-----------------|-------------------|------------|
| A1: Renamed critical functions | Semantic operation detection independent of naming | Medium |
| A2: Misleading function names | Resistance to name-based shortcuts | Medium |
| A3: Deep internal call chain hiding | Cross-function behavioral tracing | Hard |
| A4: Dead code red herring | Reachability analysis before reporting | Hard |
| A5: Safe code with vulnerable-looking names | False positive resistance | Medium |

#### Category B: Protocol Complexity

Tests cross-contract and protocol-level reasoning.

| Trick Technique | What It Validates | Difficulty |
|-----------------|-------------------|------------|
| B1: Multi-contract split vulnerability | Cross-contract graph reasoning | Hard |
| B2: Vulnerability in proxy implementation | Upgrade-aware analysis | Hard |
| B3: Callback-triggered reentrancy (non-ERC777) | Custom callback pattern detection | Medium |
| B4: State machine ordering violation | Temporal state reasoning | Hard |
| B5: Economic rounding exploit | Arithmetic + economic reasoning | Very Hard |

#### Category C: Honeypot Inversions

Contracts that invert expectations -- safe ones that look dangerous, or dangerous ones that look safe.

| Trick Technique | What It Validates | Difficulty |
|-----------------|-------------------|------------|
| C1: Fake vulnerability behind proper guard | FP rate under pressure | Medium |
| C2: Guard hidden in deep inheritance | Guard discovery across hierarchy | Medium |
| C3: Custom reentrancy lock (non-standard) | Detection of non-OZ protection | Medium |
| C4: Function that always reverts | Dead path analysis | Medium |
| C5: Vulnerability masked by unconventional modifier | Modifier semantic understanding | Hard |

### 2.3 Worked Examples

#### Worked Example A1: Renamed Withdraw with Reentrancy

**Target Pattern:** `token-002-erc777-reentrancy` (behavioral signature: `X:call -> W:bal`)
**Trick Applied:** Name obfuscation -- all functions named with business-domain terms

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC777/IERC777.sol";

/// @title LiquidityPoolSettlement
/// @notice Handles settlement of liquidity provider positions
contract LiquidityPoolSettlement {
    IERC777 public settlementAsset;
    mapping(address => uint256) public providerAllocations;
    uint256 public totalAllocated;

    event PositionSettled(address indexed provider, uint256 amount);
    event AllocationAdjusted(address indexed provider, uint256 newAmount);

    constructor(IERC777 _asset) {
        settlementAsset = _asset;
    }

    /// @notice Providers deposit assets to receive allocation
    function contributeToPool(uint256 amount) external {
        settlementAsset.operatorSend(msg.sender, address(this), amount, "", "");
        providerAllocations[msg.sender] += amount;
        totalAllocated += amount;
    }

    /// @notice Settle a provider's position and return their assets
    /// @dev VULNERABLE: ERC-777 send triggers tokensReceived before
    ///      providerAllocations is decremented (CEI violation)
    function settlePosition(uint256 amount) external {
        require(providerAllocations[msg.sender] >= amount, "Exceeds allocation");
        // Interaction BEFORE Effect -- CEI violation
        settlementAsset.send(msg.sender, amount, "");
        providerAllocations[msg.sender] -= amount;
        totalAllocated -= amount;
        emit PositionSettled(msg.sender, amount);
    }

    /// @notice View current allocation for a provider
    function getAllocation(address provider) external view returns (uint256) {
        return providerAllocations[provider];
    }

    /// @notice Emergency pause (admin only, not shown for brevity)
    function adjustAllocation(address provider, uint256 newAmount) external {
        // Intentionally left without access control for simplicity
        providerAllocations[provider] = newAmount;
        emit AllocationAdjusted(provider, newAmount);
    }
}
```

**Ground Truth:**
```yaml
scenario_id: adversarial-a1-renamed-reentrancy
adversarial_category: A
trick_applied: >
  All functions use liquidity-pool settlement terminology instead of
  standard withdraw/deposit naming. Function "settlePosition" performs
  the same R:bal -> X:out -> W:bal pattern as a classic vulnerable withdraw.
expected_findings:
  - pattern_id: token-002-erc777-reentrancy
    function: settlePosition
    vulnerability: CEI violation with ERC-777 send before state update
    severity: critical
  - pattern_id: ac-*  # wildcard -- adjustAllocation has no access control
    function: adjustAllocation
    vulnerability: Missing access control on state-modifying function
    severity: high
false_positives_expected: []
detection_difficulty: >
  Medium. Agent must recognize settlePosition as a withdraw-equivalent
  by analyzing behavioral operations (CALLS_EXTERNAL before WRITES_USER_BALANCE),
  not by matching function name "withdraw".
reasoning_requirements:
  - "Identify ERC-777 send() as external call with callback potential"
  - "Detect CEI violation: send before providerAllocations decrement"
  - "Name 'settlePosition' must not prevent reentrancy detection"
```

#### Worked Example C3: Custom Reentrancy Lock (Safe Contract -- FP Trap)

**Target Pattern:** `reentrancy-001-classic`
**Trick Applied:** Contract LOOKS vulnerable but has a custom non-standard reentrancy guard using raw storage slot

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title YieldDistributor
/// @notice Distributes yield to stakers
contract YieldDistributor {
    mapping(address => uint256) public stakes;
    mapping(address => uint256) public pendingYield;
    uint256 public totalStaked;

    // Custom reentrancy guard using raw storage slot (non-standard)
    // Slot chosen to avoid collision: keccak256("yield.distributor.lock") - 1
    bytes32 private constant _LOCK_SLOT =
        0xa1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2;

    modifier guarded() {
        bytes32 slot = _LOCK_SLOT;
        uint256 locked;
        assembly { locked := sload(slot) }
        require(locked == 0, "no re-entry");
        assembly { sstore(slot, 1) }
        _;
        assembly { sstore(slot, 0) }
    }

    /// @notice Claim pending yield
    /// @dev LOOKS vulnerable (external call before state update)
    ///      but guarded modifier prevents reentrancy via storage-slot lock
    function claimYield() external guarded {
        uint256 amount = pendingYield[msg.sender];
        require(amount > 0, "Nothing to claim");
        // External call before state update -- LOOKS like CEI violation
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Transfer failed");
        pendingYield[msg.sender] = 0;
    }

    /// @notice Withdraw staked funds
    function unstake(uint256 amount) external guarded {
        require(stakes[msg.sender] >= amount, "Insufficient stake");
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Transfer failed");
        stakes[msg.sender] -= amount;
        totalStaked -= amount;
    }

    receive() external payable {}
}
```

**Ground Truth:**
```yaml
scenario_id: adversarial-c3-custom-lock-fp-trap
adversarial_category: C
trick_applied: >
  Contract has CEI violation pattern (external call before state update)
  but uses a custom storage-slot reentrancy guard instead of OpenZeppelin's
  ReentrancyGuard. The guard is implemented in assembly using a raw storage
  slot, making it invisible to pattern matchers that look for nonReentrant
  modifier or known guard implementations.
expected_findings: []  # NO vulnerabilities -- this contract is SAFE
false_positives_expected:
  - pattern_id: reentrancy-001-classic
    function: claimYield
    reason: >
      CEI violation pattern present but custom guard prevents exploitation.
      Flagging this is a false positive.
  - pattern_id: reentrancy-001-classic
    function: unstake
    reason: Same as above
detection_difficulty: >
  Hard. Agent must:
  1. Identify the assembly-based storage lock as a reentrancy guard
  2. Understand that the guarded modifier prevents re-entry
  3. NOT report reentrancy despite the CEI violation pattern matching
reasoning_requirements:
  - "Analyze guarded modifier assembly to understand it implements a mutex"
  - "Recognize that storage-slot-based lock is functionally equivalent to nonReentrant"
  - "Conclude that CEI violation is protected and not exploitable"
success_criteria: >
  Framework reports ZERO reentrancy findings. If it reports reentrancy on
  claimYield or unstake, that is a false positive failure. Ideal output:
  reasoning explains WHY the CEI violation is not exploitable.
```

#### Worked Example B4: State Machine Ordering Violation

**Target Pattern:** `logic/sequencing` category
**Trick Applied:** Protocol complexity -- vulnerability only emerges from calling functions in wrong order

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title CollateralAuction
/// @notice Auction system for liquidated collateral positions
contract CollateralAuction {
    enum Phase { Inactive, Bidding, Settlement, Finalized }

    struct Auction {
        address seller;
        address highBidder;
        uint256 highBid;
        uint256 collateralAmount;
        Phase phase;
        uint256 deadline;
    }

    mapping(uint256 => Auction) public auctions;
    uint256 public nextAuctionId;

    /// @notice Start a new auction
    function startAuction(uint256 collateralAmount) external returns (uint256) {
        uint256 id = nextAuctionId++;
        auctions[id] = Auction({
            seller: msg.sender,
            highBidder: address(0),
            highBid: 0,
            collateralAmount: collateralAmount,
            phase: Phase.Bidding,
            deadline: block.timestamp + 1 days
        });
        return id;
    }

    /// @notice Place a bid
    function bid(uint256 auctionId) external payable {
        Auction storage a = auctions[auctionId];
        require(a.phase == Phase.Bidding, "Not in bidding phase");
        require(msg.value > a.highBid, "Bid too low");
        // Refund previous bidder (safe -- no reentrancy issue here)
        if (a.highBidder != address(0)) {
            payable(a.highBidder).transfer(a.highBid);
        }
        a.highBidder = msg.sender;
        a.highBid = msg.value;
    }

    /// @notice Settle the auction -- transition to settlement phase
    /// @dev VULNERABLE: No check that deadline has passed.
    ///      Anyone can call settle() immediately after startAuction(),
    ///      skipping the bidding period entirely.
    function settle(uint256 auctionId) external {
        Auction storage a = auctions[auctionId];
        require(a.phase == Phase.Bidding, "Not in bidding phase");
        // MISSING: require(block.timestamp >= a.deadline, "Bidding not over");
        a.phase = Phase.Settlement;
    }

    /// @notice Finalize -- transfer collateral to winner
    function finalize(uint256 auctionId) external {
        Auction storage a = auctions[auctionId];
        require(a.phase == Phase.Settlement, "Not in settlement");
        require(msg.sender == a.seller, "Only seller");
        // Transfer collateral logic (simplified)
        a.phase = Phase.Finalized;
        if (a.highBidder != address(0)) {
            payable(a.seller).transfer(a.highBid);
        }
    }
}
```

**Ground Truth:**
```yaml
scenario_id: adversarial-b4-state-machine-violation
adversarial_category: B
trick_applied: >
  Vulnerability is NOT in any single function but in the state machine
  transition logic. settle() allows skipping from Bidding to Settlement
  without checking that the deadline has elapsed. The bug is a missing
  temporal guard, not a classic reentrancy or access control issue.
expected_findings:
  - pattern_id: logic-sequencing-*
    function: settle
    vulnerability: >
      Missing deadline check allows premature auction settlement.
      Seller (or accomplice) can call settle() + finalize() immediately,
      preventing any bids and reclaiming collateral without auction.
    severity: high
detection_difficulty: >
  Hard. Requires understanding the intended state machine flow
  (Bidding -> Settlement requires deadline expiry) and recognizing
  that the require(a.phase == Phase.Bidding) check is insufficient
  without a temporal guard.
reasoning_requirements:
  - "Reconstruct the intended state machine from Phase enum and transitions"
  - "Identify that settle() can be called immediately (no temporal guard)"
  - "Explain the economic impact: auction can be settled with zero bids"
```

### 2.4 Adversarial Scenario Generation Template

To create new adversarial scenarios, follow this process:

```
Step 1: SELECT target pattern from vulndocs/
         - Choose pattern with clear behavioral_signature or match.tier_a
         - Prefer patterns with real test_coverage data

Step 2: CHOOSE trick category (A/B/C)
         A = rename everything, keep identical behavior
         B = split across contracts/add protocol complexity
         C = make it look vulnerable but add hidden protection (or vice versa)

Step 3: DESIGN the contract
         - Invent a novel business domain (not DeFi lending if testing reentrancy)
         - Use domain-specific naming throughout
         - If Category A: keep vulnerability identical, change ALL names
         - If Category B: split vulnerability across 2+ contracts
         - If Category C: add non-obvious protection mechanism
         - Add 2-3 red herring functions that look suspicious but are safe

Step 4: VERIFY novelty
         - Contract must NOT be findable on GitHub/Etherscan
         - Must use novel variable names, contract names, business logic
         - Structure must differ from any CTF/educational example
         - Test: could an LLM recognize this as "the X vulnerability"
           from structure alone? If yes, restructure.

Step 5: WRITE ground truth
         Required fields:
         - scenario_id: adversarial-{category}{number}-{short-name}
         - adversarial_category: A | B | C
         - trick_applied: prose description of what was done
         - expected_findings: list (empty for FP traps)
         - false_positives_expected: list (empty for TP scenarios)
         - detection_difficulty: easy | medium | hard | very_hard
         - reasoning_requirements: list of specific reasoning steps needed
         - success_criteria: what correct output looks like

Step 6: VALIDATE
         - Does the contract compile? (forge build)
         - Is the ground truth unambiguous?
         - Could a human auditor solve it in < 5 minutes?
           (If not, the trick may be too hard for current AI)
         - Does it test a SPECIFIC capability, not general difficulty?
```

### 2.5 Quality Criteria for Adversarial Scenarios

| Criterion | Required | Description |
|-----------|----------|-------------|
| Compiles | YES | `forge build` succeeds without errors |
| Novel | YES | Not findable via GitHub code search |
| Specific trick | YES | Tests ONE identifiable detection capability |
| Unambiguous ground truth | YES | No reasonable disagreement about findings |
| Human-solvable | YES | Expert auditor can solve in < 10 minutes |
| Red herrings present | RECOMMENDED | At least one distraction element |
| Multi-function context | RECOMMENDED | Surrounding code adds realistic noise |
| Documented reasoning chain | RECOMMENDED | Ground truth explains step-by-step reasoning |

---

## 3. GAP-07 Resolution: Pattern-Derived Scenario Generation Pipeline

### 3.1 Pipeline Overview

```
INPUT: vulndocs/{category}/{subcategory}/patterns/{id}.yaml
                          |
                 [1. Extract Specification]
                          |
                 pattern_id, match.tier_a, behavioral_signature,
                 attack_scenarios, severity, scope
                          |
                 [2. Select Business Domain]
                          |
                 Novel domain NOT associated with the pattern
                 (e.g., reentrancy -> insurance claims, not lending)
                          |
                 [3. Generate Vulnerable Contract]
                          |
                 Function with all match.tier_a.all properties TRUE
                 and all match.tier_a.none properties FALSE
                          |
                 [4. Generate Safe Variant]
                          |
                 Same structure but with proper protection
                 (match.tier_a.none properties become TRUE)
                          |
                 [5. Generate Ground Truth YAML]
                          |
                 pattern_id, expected_properties, function, severity
                          |
                 [6. Generate Evaluation Guidance]
                          |
                 reasoning_questions from attack_scenarios,
                 check_graph_usage from tier
                          |
OUTPUT: scenario directory with contracts/ + ground-truth.yaml + scenario.yaml
```

### 3.2 Full Worked Example: oracle/manipulation -> DEX Price Oracle

**Source Pattern:** `dex-oracle-manipulation` from `vulndocs/oracle/manipulation/`

**Step 1: Extract Specification**

From the pattern YAML:
```yaml
match:
  all:
    - property: balance_used_for_collateralization (eq: true)
    - property: visibility (in: [public, external])
  none:
    - property: flash_loan_guard (eq: true)
    - property: uses_historical_snapshot (eq: true)
    - property: has_twap_window_parameter (eq: true)
severity: critical
lens: [ExternalInfluence, Oracle]
```

Required behavioral properties for vulnerable contract:
- Uses on-chain balance/reserves for pricing (not TWAP)
- No flash loan protection
- Public/external visibility
- No historical snapshot mechanism

**Step 2: Select Business Domain**

Pattern references DVDeFi "puppet" challenges (lending). Choose DIFFERENT domain: **NFT marketplace with dynamic floor pricing** based on DEX liquidity pool.

**Step 3: Generate Vulnerable Contract**

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IUniswapV2Pair {
    function getReserves() external view returns (uint112, uint112, uint32);
}

interface IERC721 {
    function transferFrom(address, address, uint256) external;
}

/// @title DynamicFloorMarketplace
/// @notice NFT marketplace with floor price derived from DEX pair reserves
contract DynamicFloorMarketplace {
    IUniswapV2Pair public pricePair;
    IERC721 public nftCollection;
    address public feeRecipient;

    struct Listing {
        address seller;
        uint256 tokenId;
        uint256 minMultiplier; // Minimum price as multiplier of floor
        bool active;
    }

    mapping(uint256 => Listing) public listings;

    constructor(
        IUniswapV2Pair _pair,
        IERC721 _collection,
        address _feeRecipient
    ) {
        pricePair = _pair;
        nftCollection = _collection;
        feeRecipient = _feeRecipient;
    }

    /// @notice Get current floor price based on DEX reserves
    /// @dev VULNERABLE: Uses spot reserves, manipulable via flash loan
    function currentFloorPrice() public view returns (uint256) {
        (uint112 reserveToken, uint112 reserveETH, ) = pricePair.getReserves();
        // Floor = 10 tokens worth of ETH (simplified)
        return (uint256(reserveETH) * 10) / uint256(reserveToken);
    }

    /// @notice List an NFT for sale
    function listNFT(uint256 tokenId, uint256 minMultiplier) external {
        nftCollection.transferFrom(msg.sender, address(this), tokenId);
        listings[tokenId] = Listing(msg.sender, tokenId, minMultiplier, true);
    }

    /// @notice Buy a listed NFT at floor-derived price
    /// @dev VULNERABLE: Price derived from manipulable spot reserves
    function buyNFT(uint256 tokenId) external payable {
        Listing storage listing = listings[tokenId];
        require(listing.active, "Not listed");

        uint256 price = currentFloorPrice() * listing.minMultiplier;
        require(msg.value >= price, "Below asking price");

        listing.active = false;
        nftCollection.transferFrom(address(this), msg.sender, tokenId);

        // Pay seller minus 2.5% fee
        uint256 fee = msg.value * 25 / 1000;
        payable(listing.seller).transfer(msg.value - fee);
        payable(feeRecipient).transfer(fee);
    }
}
```

**Step 4: Generate Safe Variant**

```solidity
/// @title DynamicFloorMarketplaceSafe
/// @notice Same marketplace but with TWAP oracle and flash loan protection
contract DynamicFloorMarketplaceSafe {
    // ... same fields plus:
    uint256 public constant TWAP_WINDOW = 30 minutes;
    uint256 public lastSnapshotBlock;
    uint256 public twapPrice;

    /// @notice Get floor price from TWAP, not spot reserves
    function currentFloorPrice() public view returns (uint256) {
        // Uses stored TWAP, not live reserves
        return twapPrice * 10;
    }

    /// @notice Update TWAP -- cannot be called in same block as buy
    function updateTWAP() external {
        require(block.number > lastSnapshotBlock, "Already updated this block");
        // TWAP calculation from cumulative prices (simplified)
        (uint112 r0, uint112 r1, ) = pricePair.getReserves();
        twapPrice = uint256(r1) / uint256(r0);
        lastSnapshotBlock = block.number;
    }

    function buyNFT(uint256 tokenId) external payable {
        // Flash loan protection: TWAP must not have been updated this block
        require(block.number > lastSnapshotBlock, "Price update same block");
        // ... same logic but using TWAP-based price
    }
}
```

**Step 5: Ground Truth**

```yaml
scenario_id: pattern-derived-oracle-nft-marketplace
source_pattern: dex-oracle-manipulation
business_domain: NFT marketplace with dynamic floor pricing
contracts:
  - file: DynamicFloorMarketplace.sol
    type: vulnerable
    expected_findings:
      - pattern_id: dex-oracle-manipulation
        functions: [currentFloorPrice, buyNFT]
        vulnerability: >
          Floor price derived from spot DEX reserves. Attacker can flash-loan
          to skew reserves, crash floor price, buy NFTs at fraction of value.
        severity: critical
        behavioral_signature: "READS_EXTERNAL_VALUE -> balance_used_for_collateralization"
  - file: DynamicFloorMarketplaceSafe.sol
    type: safe
    expected_findings: []
    protection_mechanisms:
      - TWAP oracle instead of spot reserves
      - Same-block update prevention (flash loan guard)
evaluation_guidance:
  reasoning_questions:
    - "Did the agent identify that currentFloorPrice reads spot reserves?"
    - "Did the agent recognize flash loan manipulation potential?"
    - "Did the agent explain the economic attack: crash price -> buy cheap NFTs?"
    - "For the safe variant, did the agent identify TWAP as protection?"
  check_graph_usage: true
  expected_graph_queries:
    - "Functions that read external price data"
    - "pattern:dex-oracle-manipulation"
```

### 3.3 Category-Specific Generation Strategies

| Category | Pattern Count | Sampling Strategy | Domain Ideas |
|----------|-------------|-------------------|--------------|
| access-control | 199 | Sample 5: missing-modifier, tx-origin, initialization, delegatecall, role-escalation | Insurance policy admin, DAO treasury, game inventory, staking manager, registry |
| reentrancy | 96 | Sample 3: classic, cross-function, hook-callback | Insurance claims, auction settlement, loyalty rewards |
| logic | 35 | Sample 3: sequencing, state-inconsistency, configuration | Escrow state machine, voting lifecycle, subscription billing |
| dos | 44 | Sample 2: unbounded-loop, external-revert | Batch airdrop, mass payout, dividend distribution |
| oracle | 13 | Sample 2: staleness, manipulation | NFT pricing, derivative settlement |
| upgrade | 30 | Sample 2: uninitialized-proxy, storage-collision | Plugin system, modular vault |
| crypto | 14 | Sample 1: insecure-signature | Gasless relay, meta-transactions |
| flash-loan | 5 | Sample 1: price-oracle | Synthetic asset minting |
| vault | 1 | Sample 1: share-inflation | Community fund shares |

**Sampling Priority:** Prefer patterns with `status: ready` or `status: excellent` in test_coverage. Among equal status, prefer higher severity. Among equal severity, prefer patterns with richer `attack_scenarios` fields (more context for generation).

### 3.4 Novelty Assurance Process

For every generated contract:

1. **Domain novelty:** Business context must NOT match pattern's real-world examples or references
2. **Structural novelty:** Contract must not resemble any CTF/educational contract
3. **Naming novelty:** No standard vulnerable-example naming (no "VulnerableVault", "UnsafeBank", etc.)
4. **Code novelty:** Add 2+ functions unrelated to the vulnerability (view functions, admin functions, event emissions) that are NOT in any template
5. **Verification:** Contract must compile. Vulnerability (or safety) must be demonstrable through analysis, not just asserted

---

## 4. GAP-08 Resolution: External Source Mapping

### 4.1 External Source Inventory

| Source | Categories | Contract Count | License | Use Case |
|--------|-----------|---------------|---------|----------|
| kadenzipfel/smart-contract-vulnerabilities | 5 groups, ~35 topics | ~35 code examples | MIT | Category taxonomy + vulnerability mechanics descriptions |
| SWC Registry | 37 weakness types | ~37 test cases | CC0 | Standardized IDs, already mapped in `vulndocs/.meta/references/swc-mapping.yaml` |
| Ethernaut (OpenZeppelin) | 34 levels | ~34 contracts | MIT | Progressive difficulty, proxy/delegatecall emphasis |
| DamnVulnerableDeFi v4 | 18 challenges | ~53 contracts | MIT | Already in `examples/testing/`, DeFi-focused |
| SmartBugs Curated | SWC-aligned | 143 contracts | Apache-2.0 | Ground truth labels, tool benchmarking |
| Consolidated Ground Truth (CGT) | SWC-aligned | ~500 contracts | MIT | Largest labeled dataset, multi-source consensus |
| not-so-smart-contracts (Trail of Bits) | ~15 categories | ~15 examples | -- | Minimal, clear examples from audit experts |

### 4.2 Category Coverage Matrix

Map external categories to vulndocs categories, then identify gaps.

**kadenzipfel Categories -> VulnDocs Mapping:**

| kadenzipfel Group | kadenzipfel Topic | VulnDocs Category | VulnDocs Patterns | Coverage |
|-------------------|-------------------|-------------------|-------------------|----------|
| Access Control | Authorization tx.origin | access-control/tx-origin | 2 patterns | GOOD |
| Access Control | Insufficient Access Control | access-control/missing-modifier | 199 patterns | GOOD |
| Access Control | Delegatecall to Untrusted Callee | access-control/delegatecall-control | patterns exist | GOOD |
| Access Control | Signature Malleability | crypto/signature-malleability | patterns exist | GOOD |
| Access Control | Signature Replay | crypto/replay | patterns exist | GOOD |
| Math | Integer Overflow/Underflow | arithmetic/ | 2 subcategories | GOOD |
| Math | Off-By-One | logic/arithmetic | covered | GOOD |
| Math | Lack of Precision | precision-loss/ | 0 patterns (!) | **GAP** |
| Control Flow | Reentrancy | reentrancy/ | 96 patterns | GOOD |
| Control Flow | DoS Block Gas Limit | dos/block-gas-limit | patterns exist | GOOD |
| Control Flow | DoS with Revert | dos/external-revert | patterns exist | GOOD |
| Control Flow | msg.value in Loop | logic/ | **NO MATCH** | **GAP** |
| Control Flow | Transaction Ordering | mev/frontrunning | 8 patterns | GOOD |
| Control Flow | Insufficient Gas Griefing | dos/ | covered by SWC-126 | ADEQUATE |
| Data Handling | Unchecked Return Value | token/missing-return | 1 pattern | ADEQUATE |
| Data Handling | Arbitrary Storage Write | upgrade/storage-collision | covered | GOOD |
| Data Handling | Unbounded Return Data | -- | **NO MATCH** | **GAP** |
| Data Handling | Uninitialized Storage Pointer | logic/state-inconsistency | covered | GOOD (pre-0.5) |
| Data Handling | ecrecover null address | crypto/ecrecover-zero | patterns exist | GOOD |
| Unsafe Logic | Weak Randomness | crypto/weak-randomness | covered | GOOD |
| Unsafe Logic | Hash Collision encodePacked | crypto/hash-collision | covered | GOOD |
| Unsafe Logic | Timestamp Dependence | -- (partially crypto/weak-randomness) | minimal | **GAP** |
| Unsafe Logic | Unsafe Low-Level Call | -- | **NO MATCH** | **GAP** |
| Unsafe Logic | Unencrypted Private Data | -- | **NO MATCH** | **GAP** |
| Unsafe Logic | Contract from Code Size | -- | **NO MATCH** | **GAP** |
| Code Quality | (7 topics) | N/A | N/A | OUT OF SCOPE |

**SWC -> VulnDocs Mapping:** Already exists at `vulndocs/.meta/references/swc-mapping.yaml`. Summary:
- 26 of 37 SWC entries mapped to vulndocs categories
- 11 are quality/tooling issues (not runtime vulnerabilities)
- 7 mapped as "critical" relevance

### 4.3 Gap Analysis: Underrepresented Vulnerability Types

| Rank | Vulnerability Type | External Sources | VulnDocs Status | Test Priority |
|------|-------------------|------------------|-----------------|---------------|
| 1 | Precision loss / Rounding manipulation | kadenzipfel Math, real DeFi hacks | 0 patterns in precision-loss/ | **HIGH** |
| 2 | msg.value in loop (multi-call value reuse) | kadenzipfel Control Flow | No direct pattern | **HIGH** |
| 3 | Unsafe low-level call (returnbomb) | kadenzipfel, SWC-104 extension | Partial (token/missing-return) | MEDIUM |
| 4 | Timestamp dependence (beyond randomness) | kadenzipfel, SWC-116 | Minimal | MEDIUM |
| 5 | Contract size check bypass (extcodesize) | kadenzipfel, Ethernaut | No pattern | LOW |
| 6 | Unencrypted private data | kadenzipfel, Ethernaut Lvl 12 | No pattern | LOW (not runtime) |
| 7 | Unbounded return data (returnbomb) | kadenzipfel Data Handling | No pattern | MEDIUM |
| 8 | Force-feeding ether (selfdestruct/coinbase) | SWC-132, Ethernaut Lvl 7 | logic/balance-manipulation (1 pattern) | MEDIUM |
| 9 | Governance flash loan voting | SWC-114 extension, real attacks | governance/flash-loan-voting | ADEQUATE |
| 10 | Cross-chain replay | SWC-121 extension | cross-chain/ | ADEQUATE |

### 4.4 Integration Strategy

**Rule: External sources provide MECHANICS and CATEGORY COVERAGE, never templates.**

Process for using external sources:

```
1. IDENTIFY category gap from coverage matrix above
2. READ external source description of vulnerability MECHANICS
   - What operations cause the vulnerability?
   - What conditions must hold?
   - What is the attacker's economic incentive?
3. MAP mechanics to VulnDocs semantic operations
   - Which BSKG properties would detect this?
   - What behavioral signature describes this?
4. WRITE original contract in novel business domain
   - NEVER copy or modify external source code
   - Business domain must differ from all known examples
   - Must pass novelty assurance (Section 3.4)
5. CROSS-REFERENCE with SWC mapping
   - Include SWC ID in ground-truth.yaml if applicable
   - Note: SWC is classification, not template source
```

### 4.5 Top 10 Vulnerability Types Needing New Test Scenarios

These are the types most valuable for the curated corpus, based on:
- Gap in current vulndocs coverage
- Real-world impact (frequency and severity of exploits)
- Testing value (requires genuine reasoning, not pattern matching)

| Priority | Vulnerability Type | Why It Needs a Scenario | Suggested Approach |
|----------|-------------------|------------------------|-------------------|
| 1 | **Classic reentrancy (adversarial)** | Most common, but contaminated in training data | Category A trick: novel domain + renamed functions |
| 2 | **Missing access control (adversarial)** | Largest pattern set (199), needs adversarial test | Category C trick: guard hidden in parent contract |
| 3 | **Oracle manipulation** | Critical DeFi risk, requires economic reasoning | Novel domain (NFT pricing, not lending) |
| 4 | **Precision loss / Rounding** | 0 patterns but frequent real exploit cause | New pattern + novel scenario |
| 5 | **State machine violation** | Tests temporal reasoning, not pattern matching | Category B trick: multi-step protocol |
| 6 | **Proxy initialization** | Tests upgrade-awareness | Novel proxy pattern, not OZ transparent |
| 7 | **Signature validation** | Tests crypto reasoning depth | Multiple missing checks, partial fixes |
| 8 | **msg.value in loop** | Underrepresented, real attack vector | Multi-call pattern in batch processor |
| 9 | **Flash loan + callback** | Tests cross-protocol reasoning | Novel callback mechanism |
| 10 | **Custom reentrancy guard (FP trap)** | Tests FP resistance | Category C: non-standard guard |

---

## 5. Training Data Contamination Protocol

### 5.1 The Problem

Any contract that has ever appeared in a public GitHub repository, CTF challenge, educational resource, or audit report is likely in LLM training data from mid-2024 onward. Research confirms this concern:

- SC-Bench (arxiv:2410.06176) explicitly warns about benchmark contamination for LLM evaluation
- The "Compositional Generalization" paper (arxiv:2601.06914) demonstrates that LLMs can achieve 98%+ accuracy on known reentrancy patterns through memorization, not reasoning
- Benchmark data contamination surveys (arxiv:2406.04244) document systematic contamination across model families

### 5.2 Concrete Rules

**Rule 1: No Public Derivatives**
Every test contract must be an ORIGINAL composition. No modifications of Ethernaut levels, DVDeFi challenges, SWC test cases, kadenzipfel examples, or any other publicly available contract.

**Rule 2: Novel Business Domains**
Each scenario must use a business domain NOT commonly associated with its vulnerability type:
- Reentrancy -> NOT lending/borrowing. USE: insurance claims, auction settlements, loyalty programs
- Access control -> NOT token minting. USE: game inventory, registry management, subscription systems
- Oracle manipulation -> NOT lending collateral. USE: NFT pricing, derivative settlement, insurance payouts

**Rule 3: Structural Disguise**
Even if the vulnerability is identical, the contract structure must differ:
- Different number of functions (add 2-3 unrelated utility functions)
- Different state variable layout
- Different inheritance hierarchy
- Mix of custom errors and require strings
- Vary return patterns (named returns vs explicit)

**Rule 4: Name Independence**
No function, variable, or contract name should hint at the vulnerability:
- BAD: `VulnerableVault`, `withdraw`, `balances[msg.sender]`
- GOOD: `PositionSettlementEngine`, `settlePosition`, `providerAllocations[msg.sender]`

**Rule 5: Verification Gate**
Before a scenario enters the curated corpus, verify:
- [ ] Contract compiles (`forge build`)
- [ ] No exact match on GitHub code search for any 3-line code block
- [ ] No exact match for contract name on Etherscan
- [ ] Business domain differs from pattern's `references` and `attack_scenarios` examples
- [ ] At least 2 functions exist that are NOT part of the vulnerability

### 5.3 Why This Matters Quantitatively

If a model has seen the Ethernaut "Re-entrancy" level in training:
- It can achieve ~100% detection by recognizing the pattern structure
- It achieves ~0% detection on a structurally novel reentrancy in an insurance contract
- The delta between these measures actual reasoning capability

Our corpus must produce the second measurement, not the first.

---

## 6. Curated Corpus Composition

Recommended 12-scenario breakdown across four categories:

### 6.1 Standard Detection Scenarios (3)

These test basic detection capability with novel contracts.

| # | Scenario | Source Pattern | Domain | Expected |
|---|----------|---------------|--------|----------|
| S1 | Reentrancy in loyalty rewards | reentrancy/classic | Loyalty program | 1 TP finding |
| S2 | Missing access on game inventory | access-control/missing-modifier | Game items | 1 TP finding |
| S3 | Stale oracle in insurance payout | oracle/staleness | Parametric insurance | 1 TP finding |

### 6.2 Adversarial Scenarios (4)

These test resistance to tricks and false positive pressure.

| # | Scenario | Category | Trick | Expected |
|---|----------|----------|-------|----------|
| A1 | Renamed reentrancy in LP settlement | A (names) | All domain terminology, no "withdraw" | 1 TP finding despite renaming |
| A2 | Custom storage-slot lock (FP trap) | C (honeypot) | Non-standard guard in assembly | 0 findings (safe contract) |
| A3 | State machine auction violation | B (complexity) | Vulnerability in transition logic, not single function | 1 TP finding requiring temporal reasoning |
| A4 | Dead code red herring + real vuln | A+C combo | Unreachable vulnerable function + real hidden vuln | 1 TP (the real one), 0 FP on dead code |

### 6.3 Orchestration Scenarios (2)

These test multi-agent team behavior.

| # | Scenario | Focus | Team | Expected |
|---|----------|-------|------|----------|
| O1 | Multi-agent reentrancy debate | 3-agent lifecycle | attacker + defender + verifier | Attacker finds, defender checks guards, verifier arbitrates |
| O2 | Tool coordination on complex contract | Tool selection + synthesis | single agent + tools | Agent selects appropriate tools, synthesizes results |

### 6.4 FP Control Scenarios (3)

These test the framework's ability to correctly report "no vulnerability found."

| # | Scenario | Pattern Tested | Protection Mechanism | Expected |
|---|----------|---------------|---------------------|----------|
| F1 | Safe vault with CEI pattern | reentrancy | Proper CEI ordering | 0 reentrancy findings |
| F2 | Proper OZ AccessControl | access-control | Role-based access | 0 access control findings |
| F3 | Chainlink oracle with staleness check | oracle | Heartbeat + deviation check | 0 oracle findings |

### 6.5 Corpus Distribution Summary

```
Total scenarios: 12
  Standard detection: 3 (25%) -- baseline capability
  Adversarial:        4 (33%) -- reasoning depth validation
  Orchestration:      2 (17%) -- multi-agent/tool behavior
  FP Control:         3 (25%) -- precision validation

Vulnerability categories covered:
  reentrancy:      3 scenarios (S1, A1, F1)
  access-control:  2 scenarios (S2, F2)
  oracle:          2 scenarios (S3, F3)
  logic:           1 scenario  (A3)
  mixed/composite: 2 scenarios (A4, O1)

Detection tiers tested:
  Tier A: 8 scenarios (deterministic graph matching)
  Tier B: 3 scenarios (LLM-verified)
  Tier C: 1 scenario  (label-dependent, stretch goal)

Adversarial trick categories:
  A (Name obfuscation):    2 scenarios
  B (Protocol complexity): 1 scenario
  C (Honeypot inversion):  2 scenarios (incl. A2 and partial A4)
```

---

## 7. Implementation Priority for 3.1b-06

### Phase 1: Foundation (Week 1)

1. **Create scenario directory structure** in `examples/testing/corpus/`
   ```
   examples/testing/corpus/
     guidelines/
       adversarial-template.md         # From Section 2.4
       pattern-derived-template.md     # From Section 3.1-3.2
       novelty-checklist.md            # From Section 5.2
       external-sources.yaml           # From Section 4.2
       workflow-categories.yaml        # From GAP-10
     scenarios/
       S1-loyalty-reentrancy/
       S2-game-access-control/
       ...
   ```

2. **Write 3 seed scenarios** as reference implementations:
   - A1 (Renamed reentrancy -- worked example from Section 2.3)
   - A2 (Custom lock FP trap -- worked example from Section 2.3)
   - S1 (Standard reentrancy in loyalty domain)

3. **Create ground-truth.yaml schema** defining all required fields

### Phase 2: Coverage (Week 2)

4. **Generate remaining 9 scenarios** following the pipeline
5. **Validate all 12 scenarios compile** (`forge build` for each)
6. **Run novelty verification** against GitHub code search

### Phase 3: Integration (Week 3)

7. **Wire scenarios into test harness** (pytest discovery)
8. **Create scenario loader** that reads ground-truth.yaml
9. **Implement evaluation guidance integration** with EvaluationGuidance DSL

### Dependencies

| Deliverable | Depends On | Blocks |
|------------|-----------|--------|
| Scenario directory structure | Nothing | Everything else |
| Ground truth schema | Nothing | All scenarios |
| Seed scenarios (3) | Schema | Coverage phase |
| Remaining scenarios (9) | Seed scenarios as reference | Integration phase |
| Scenario loader | 3.1b-02 OutputCollector | 3.1c evaluators |
| Evaluation guidance | 3.1b-05 DSL schema | 3.1c evaluation contracts |

### Estimated Effort

| Task | Est. Hours | Confidence |
|------|-----------|------------|
| Directory structure + templates | 2h | HIGH |
| 3 seed scenarios (contracts + ground truth) | 4h | HIGH |
| 9 additional scenarios | 8h | MEDIUM |
| Novelty verification | 2h | HIGH |
| Scenario loader integration | 3h | MEDIUM |
| **Total** | **19h** | MEDIUM |

---

## Appendix A: Pattern-to-Scenario Quick Reference

For the most common pattern categories, here is a quick mapping of pattern match properties to what the generated contract must exhibit:

| Pattern Property | Vulnerable Contract | Safe Variant |
|-----------------|-------------------|--------------|
| `visibility: [public, external]` | Function is public/external | Same |
| `has_access_gate: false` | No require/modifier checking caller | Has onlyOwner or role check |
| `state_write_after_external_call: true` | .call{} before state = | state = before .call{} |
| `has_reentrancy_guard: false` | No nonReentrant | Has nonReentrant or mutex |
| `uses_tx_origin: true` | require(tx.origin == ...) | require(msg.sender == ...) |
| `balance_used_for_collateralization: true` | getReserves() for pricing | TWAP or Chainlink |
| `uses_ecrecover: true` + missing checks | Raw ecrecover, no OZ ECDSA | OpenZeppelin ECDSA.recover |
| `unbounded_loop: true` | for(i=0; i<array.length; ...) | Paginated or bounded iteration |

## Appendix B: External Source Quick Reference

| Source | URL | Primary Use |
|--------|-----|-------------|
| kadenzipfel | https://kadenzipfel.github.io/smart-contract-vulnerabilities/ | Category taxonomy, 35 vulnerability descriptions |
| SWC Registry | https://swcregistry.io/ | Standardized IDs (already mapped in vulndocs) |
| Ethernaut | https://ethernaut.openzeppelin.com/ | 34 progressive challenges, proxy/delegatecall emphasis |
| DamnVulnerableDeFi | Already in `examples/testing/` | 18 DeFi challenges, flash loan focus |
| SmartBugs Curated | https://github.com/smartbugs/smartbugs-curated | 143 labeled contracts for tool benchmarking |
| CGT (Consolidated Ground Truth) | https://github.com/gsalzer/cgt | ~500 contracts with multi-source consensus labels |
| not-so-smart-contracts | https://github.com/crytic/not-so-smart-contracts | Trail of Bits curated minimal examples |

**Remember: These sources provide CATEGORY COVERAGE and MECHANICS UNDERSTANDING. The actual test contracts must be 100% original.**

---

*Resolution produced by corpus strategy research. Confidence: HIGH for adversarial guidelines and pipeline design, MEDIUM for specific scenario count estimates and effort sizing.*

---

## REVISED: GAP-08 Simplification (2026-02-12)

### What Changed

The original GAP-08 resolution (Section 4 above) proposed building an `external-sources.yaml` mapping file with a category coverage matrix, integration strategy, and gap analysis. This was over-engineered.

### The Insight

**VulnDocs (461+ patterns across 14 categories) IS the external source.** The pattern-derived pipeline (GAP-07, Section 3 above) already handles generation -- it reads vulndocs patterns and generates test scenarios from their `detection_logic` / `match` specs. Building a separate external-sources.yaml that maps kadenzipfel, SWC, Ethernaut, etc. to vulndocs categories adds a maintenance burden with near-zero value, because:

1. The SWC mapping already exists at `vulndocs/.meta/references/swc-mapping.yaml` (37 entries, all mapped)
2. VulnDocs already covers all SWC top-20 and OWASP Smart Contract Top 10 classes
3. The only real question from "external sources" is: **"Is vulndocs missing any important vulnerability class?"** -- and that is a one-time audit question, not infrastructure

### What Replaces It

1. **One-time coverage audit script:** `examples/testing/scripts/audit-vulndocs-coverage.py`
   - Walks `vulndocs/` to inventory all patterns by category
   - Walks `examples/testing/` to find test scenario coverage
   - Cross-references against SWC top-20 and OWASP SC top-10
   - Outputs a human-readable markdown report to stdout
   - Run once, file issues for missing categories, done
   - ~150 lines, zero dependencies beyond stdlib, standalone

2. **GAP-07 pipeline IS the generation mechanism:**
   - For any vulndocs pattern without test coverage, the GAP-07 pipeline generates scenarios
   - No separate mapping file needed -- vulndocs patterns ARE the specs

3. **No `external-sources.yaml` deliverable:**
   - The coverage matrix from Section 4.2 above remains useful reference material
   - But it does not need to be a maintained YAML artifact in the repository
   - The SWC mapping at `vulndocs/.meta/references/swc-mapping.yaml` already serves that role

### Impact on 3.1b-06

The `guidelines/external-sources.yaml` deliverable listed in the 3.1b-06 plan is **replaced** by:
- `examples/testing/scripts/audit-vulndocs-coverage.py` (the audit script)
- The existing `vulndocs/.meta/references/swc-mapping.yaml` (already in repo)

All other 3.1b-06 deliverables (10-12 curated scenarios, tier templates, ground-truth schema, adversarial guidelines, pattern-derived template) remain unchanged.

### Audit Script Usage

```bash
# Run the one-time audit
python examples/testing/scripts/audit-vulndocs-coverage.py

# Or with uv if system python unavailable
uv run python examples/testing/scripts/audit-vulndocs-coverage.py

# Output is markdown to stdout -- pipe to file if needed
uv run python examples/testing/scripts/audit-vulndocs-coverage.py > coverage-audit.md
```

The script requires no installation, no dependencies, and no alphaswarm package. It walks directories and parses YAML by reading lines (no pyyaml needed).
