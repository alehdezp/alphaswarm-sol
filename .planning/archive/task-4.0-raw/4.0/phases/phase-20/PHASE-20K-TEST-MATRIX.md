# Phase 20.K: Real-World Test Matrix (Behavior-First)

**Goal:** Provide a concrete, behavior-first matrix mapping vulnerability classes to signatures, semantic operations, and target protocols.

---

## K.1 How to Use

- Use this matrix to select corpus targets (Phase 20.B).
- Use it to drive end-to-end tests (Phase 20.D) and adversarial runs (Phase 20.E).
- Each row is a **behavior-first requirement**, not a name-based heuristic.

---

## K.2 Coverage Requirements

- At least **3 test cases per subcategory**.
- At least **1 adversarial case per category**.
- At least **1 real incident case per category** (if available).

---

## K.3 Matrix (Category → Signatures → Ops → Targets)

### Reentrancy
- **Signature:** `R:bal -> X:out -> W:bal`
- **Ops:** READS_USER_BALANCE, CALLS_EXTERNAL, WRITES_USER_BALANCE
- **Targets:** The DAO, Curve, Yearn vaults
- **Tier:** A (strict); B for cross-contract

### Access Control
- **Signature:** `C:auth (missing) -> M:crit`
- **Ops:** CHECKS_PERMISSION (absent), MODIFIES_CRITICAL_STATE
- **Targets:** OpenZeppelin upgradeable proxies, admin functions
- **Tier:** A for missing checks; B for weak logic

### Oracle
- **Signature:** `R:orc -> A:div -> X:out`
- **Ops:** READS_ORACLE, PERFORMS_DIVISION, TRANSFERS_VALUE_OUT
- **Targets:** Uniswap v2/v3, Aave, Maker
- **Tier:** A for stale price; B for manipulative paths

### Flash Loan
- **Signature:** `X:in -> R:orc -> X:out -> W:bal`
- **Ops:** RECEIVES_VALUE_IN, READS_ORACLE, TRANSFERS_VALUE_OUT, WRITES_USER_BALANCE
- **Targets:** Aave, Compound
- **Tier:** B

### MEV
- **Signature:** `R:ext -> X:out -> X:out`
- **Ops:** READS_EXTERNAL_VALUE, TRANSFERS_VALUE_OUT
- **Targets:** DEX aggregators, AMMs
- **Tier:** B

### Arithmetic/Precision
- **Signature:** `R:bal -> A:div -> W:bal`
- **Ops:** READS_USER_BALANCE, PERFORMS_DIVISION, WRITES_USER_BALANCE
- **Targets:** Lending protocols with interest math
- **Tier:** A for precision loss, B for complex math

### Signature/Auth Replay
- **Signature:** `C:auth (weak) -> M:crit`
- **Ops:** CHECKS_PERMISSION (weak), MODIFIES_CRITICAL_STATE
- **Targets:** Permit flows, meta-tx relays
- **Tier:** A/B

### Upgrade/Proxy
- **Signature:** `I:init -> M:own`
- **Ops:** INITIALIZES_STATE, MODIFIES_OWNER
- **Targets:** UUPS, Transparent proxies
- **Tier:** A

### DoS
- **Signature:** `L:arr -> X:call -> (fail)`
- **Ops:** LOOPS_OVER_ARRAY, CALLS_EXTERNAL
- **Targets:** Crowdsales, batch transfer patterns
- **Tier:** A

### Governance
- **Signature:** `R:bal -> C:auth (token) -> M:crit`
- **Ops:** READS_USER_BALANCE, CHECKS_PERMISSION, MODIFIES_CRITICAL_STATE
- **Targets:** Compound Governor, Aave Governance
- **Tier:** B

### Bridge
- **Signature:** `R:ext (message) -> M:crit -> X:out`
- **Ops:** READS_EXTERNAL_VALUE, MODIFIES_CRITICAL_STATE, TRANSFERS_VALUE_OUT
- **Targets:** Nomad, Wormhole, Ronin
- **Tier:** B

### Lending
- **Signature:** `R:orc -> R:bal -> X:out`
- **Ops:** READS_ORACLE, READS_USER_BALANCE, TRANSFERS_VALUE_OUT
- **Targets:** Aave, Compound
- **Tier:** A/B

### Token
- **Signature:** `R:bal -> W:bal -> X:out (mismatch)`
- **Ops:** READS_USER_BALANCE, WRITES_USER_BALANCE, TRANSFERS_VALUE_OUT
- **Targets:** Fee-on-transfer, rebasing tokens
- **Tier:** B

### Crypto
- **Signature:** `R:ext -> V:in (weak) -> M:crit`
- **Ops:** READS_EXTERNAL_VALUE, VALIDATES_INPUT, MODIFIES_CRITICAL_STATE
- **Targets:** signature verification flows
- **Tier:** A/B

### Logic (Business Logic)
- **Signature:** `C:auth (weak) -> M:crit (unexpected)`
- **Ops:** CHECKS_PERMISSION (weak), MODIFIES_CRITICAL_STATE
- **Targets:** NFT marketplaces, staking vaults
- **Tier:** B

---

## K.4 Evidence Requirements

For every test case, record:
- Behavioral signature
- Semantic operations
- Evidence locations (code + graph signals)
- Bead verdict (confirmed/likely/uncertain/rejected)

