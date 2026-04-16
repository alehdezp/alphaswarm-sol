# UNIFIED BSKG MEGA TASK: Real-World Detection & Pattern Overhaul

**Status:** CRITICAL - COMPLETE SYSTEM OVERHAUL REQUIRED
**Created:** 2025-12-31
**Scope:** Property Derivation + Pattern Rewrite + Limitation Analysis + System Evolution

---

## Executive Summary

### The Brutal Truth

VKG has **1315+ tests** and **22 phases** of infrastructure, but it detects **0 vulnerabilities** in Damn Vulnerable DeFi - a benchmark of known exploitable contracts.

**Two Parallel Problems:**

| Problem | Root Cause | Impact | Solution |
|---------|------------|--------|----------|
| **Property Derivation** | builder.py bugs - properties return wrong values | Patterns can't match because properties are FALSE when they should be TRUE | Fix builder.py property derivation |
| **Pattern Design** | 49.8% of patterns use name-based matching | Patterns won't match renamed contracts even if properties are correct | Rewrite patterns with semantic operations |

**The Vicious Cycle:**
```
Broken Properties → Patterns Don't Match → Detection Fails
      ↑                                           ↓
      └──── Both Must Be Fixed Together ──────────┘
```

### Combined Success Metrics

| Metric | Current | Phase 1 Target | Final Target |
|--------|---------|----------------|--------------|
| DVDeFi Detection | 0/18 (0%) | 10/18 (55%) | 16/18 (89%) |
| Name-dependency rate | 49.8% | < 25% | < 5% |
| Property derivation accuracy | ~30% | > 70% | > 90% |
| Pattern precision (critical) | Unknown | > 75% | > 90% |
| Pattern recall (critical) | Unknown | > 70% | > 85% |
| "Excellent" rated patterns | 0 | 10 | 50+ |

---

## Part I: Current System Limitations (Critical Analysis)

### Section 1.1: Property Derivation Failures

#### BUG-001: High-Level Call Target Not Tracked
**Severity:** CRITICAL
**Location:** `builder.py:1446`
**Impact:** 100% miss rate on library call vulnerabilities (Truster, Address.functionCall)

```python
# CURRENT (BROKEN)
"call_target_user_controlled": low_level_summary["call_target_user_controlled"],

# PROBLEM
# external_call_target_user_controlled IS computed at line 926 for high-level calls
# but NEVER exposed as a node property - only used internally
```

**Real-World Evidence:**
```
Contract: TrusterLenderPool.sol
Function: flashLoan(amount, borrower, target, data)
Call: target.functionCall(data)  // HIGH-LEVEL call via Address library

VKG Result: call_target_user_controlled = FALSE
Expected:   call_target_user_controlled = TRUE

Detection: FAILED
```

---

#### BUG-002: High-Level Call Data Not Analyzed
**Severity:** CRITICAL
**Location:** `builder.py:1448`, `builder.py:2068-2092`
**Impact:** Can't detect user-controlled call data in high-level calls

```python
# CURRENT (BROKEN)
"call_data_user_controlled": low_level_summary["call_data_user_controlled"],

# PROBLEM
# Only low-level calls (line 2049) are checked for user-controlled data
# High-level calls skip data analysis entirely
```

**Real-World Evidence:**
```
Contract: TrusterLenderPool.sol
Function: flashLoan(..., bytes calldata data)
Call: target.functionCall(data)  // 'data' is user-controlled parameter

VKG Result: call_data_user_controlled = FALSE
Expected:   call_data_user_controlled = TRUE

Detection: FAILED
```

---

#### BUG-003: Strict Equality Check Too Narrow
**Severity:** HIGH
**Location:** `builder.py:4853-4862`
**Impact:** Misses DoS vulnerabilities using `if` statements or `!=` operator

```python
# CURRENT (BROKEN)
def _has_strict_equality_check(self, require_exprs: list[str]) -> bool:
    for expr in require_exprs:  # ONLY checks require statements!
        lowered = expr.lower()
        has_balance = "balance" in lowered and ("this" in lowered)
        has_strict_eq = " == " in expr  # ONLY checks ==, NOT !=
```

**Real-World Evidence:**
```
Contract: UnstoppableLender.sol
Code: if (convertToShares(totalSupply) != balanceBefore) revert InvalidBalance();
      ^^                                ^^
      if statement                      != operator

VKG Result: has_strict_equality_check = FALSE
Expected:   has_strict_equality_check = TRUE

Detection: FAILED (DoS via forced donation attack undetected)
```

---

#### BUG-004: Library Call Destination Extraction Fails
**Severity:** HIGH
**Location:** `builder.py:5276-5283`
**Impact:** Library calls (Address, SafeERC20) have NULL destinations

```python
# CURRENT (BROKEN)
def _callsite_destination(self, call: Any) -> str | None:
    destination = getattr(call, "destination", None)
    if destination is None:
        return None  # SILENT FAILURE - no fallback
    # ...
```

**The Problem Chain:**
```
Address.functionCall(target, data)
    ↓
destination = getattr(call, "destination", None)
    ↓
destination.type = "address"  (generic type)
    ↓
_call_contract_name filters out "address" type (line 5149)
    ↓
Returns None
    ↓
_is_user_controlled_destination skips check when destination is None (line 2085)
    ↓
call_target_user_controlled = FALSE (WRONG!)
```

---

#### BUG-005: State Write After Call Limited to Direct Writes
**Severity:** HIGH
**Location:** `builder.py:2413-2428`
**Impact:** 31 patterns depend on this property; all may have false negatives

```python
# CURRENT (LIMITED)
def _infer_call_order(self, fn: Any) -> dict[str, bool]:
    for node in nodes:
        if self._node_has_external_call(node):
            seen_call = True
        if getattr(node, "state_variables_written", []):  # Only DIRECT writes!
            if seen_call:
                write_after = True
```

**Limitation:** Doesn't detect:
- Writes through internal function calls
- Writes through library functions
- Writes in conditional branches
- Indirect state modifications

---

#### BUG-006: Cross-Function Reentrancy Not Implemented
**Severity:** MEDIUM
**Location:** Partially exists at `builder.py:1934-1935`
**Impact:** Misses sophisticated reentrancy attacks

```python
# Properties exist but likely incomplete:
"cross_function_reentrancy_read": ...,
"cross_function_reentrancy_surface": ...,
```

**Not Detected:**
- Function A reads `balance[user]`
- Function A makes external call
- Attacker re-enters Function B
- Function B writes `balance[user]`
- Function A continues with stale value

---

#### BUG-007: Dataflow Analysis May Be Disabled
**Severity:** MEDIUM
**Location:** `builder.py:4976-4982`
**Impact:** `attacker_controlled_write` property unreliable

```python
attacker_controlled_write = bool(dataflow_edges) and bool(attacker_sources) and is_public
```

**Unknown:** Is `compute_dataflow()` actually running? Are `dataflow_edges` populated?

---

#### BUG-008: Silent None Handling
**Severity:** MEDIUM
**Location:** Multiple locations
**Impact:** No errors when critical data is missing; properties silently return FALSE

```python
# Pattern repeated throughout:
if destination and self._is_user_controlled_destination(...):
    return True
# SILENT: Returns False when destination is None, no warning
```

---

### Section 1.2: Pattern Design Failures

#### PATTERN-001: Name-Based Modifier Matching
**Severity:** CRITICAL
**Affected:** 100% of reentrancy patterns

```yaml
# BROKEN
none:
  - property: modifiers
    op: contains_any
    value: [nonReentrant, noReentrant, reentrancyGuard]  # NAME DEPENDENT
```

**Problem:** Rename `nonReentrant` to `mutex` → Pattern fails to exclude safe contracts → False positives

---

#### PATTERN-002: Hardcoded Variable Names (263 patterns)
**Severity:** CRITICAL
**Affected:** 60% of Authority patterns, 40% of Value Movement

```yaml
# BROKEN - 263 patterns have this problem
property: writes_state
op: contains_any
value: [owner, admin, controller, authority, manager]  # HARDCODED NAMES
```

**Problem:** Different project naming conventions → Massive false negatives

---

#### PATTERN-003: Function Name Regex (18 patterns)
**Severity:** HIGH
**Affected:** Withdrawal, transfer, swap detection

```yaml
# BROKEN
property: label
op: regex
value: ".*[Ww]ithdraw.*"  # NAME REGEX
```

**Problem:** `drainFunds()`, `pullAssets()`, `exitPosition()` all do withdrawals but don't match

---

#### PATTERN-004: No Semantic Operation Usage
**Severity:** HIGH
**Affected:** Most patterns
**Problem:** 20 semantic operations exist but aren't used

```yaml
# AVAILABLE BUT NOT USED:
has_operation: TRANSFERS_VALUE_OUT
has_operation: CHECKS_PERMISSION
has_all_operations: [CALLS_EXTERNAL, WRITES_USER_BALANCE]
sequence_order:
  before: CALLS_EXTERNAL
  after: WRITES_USER_BALANCE
```

---

#### PATTERN-005: Missing `none` Conditions
**Severity:** MEDIUM
**Affected:** ~40% of patterns
**Problem:** Patterns match safe code because exclusions are incomplete

```yaml
# BROKEN - Missing exclusions
match:
  all:
    - property: visibility
      op: in
      value: [public, external]
    - property: writes_state
      value: true
# NO NONE SECTION - Will match constructors, initializers, view functions, guarded functions
```

---

### Section 1.3: Architecture Limitations

#### ARCH-001: No Parameter-to-Call-Argument Tracking
**Impact:** Can't detect "parameter X flows to call target Y"

```
flashLoan(target, data)
         ↓
    Address.functionCall(???, ???)
                        Can't connect target→first_arg
```

---

#### ARCH-002: No Semantic Parameter Classification
**Impact:** Can't distinguish callback targets from amounts from recipients

```solidity
function flashLoan(
    uint256 amount,     // Amount - safe
    address borrower,   // Recipient - somewhat controlled
    address target,     // CALLBACK TARGET - DANGEROUS
    bytes calldata data // CALLBACK DATA - DANGEROUS
)
```

VKG treats all address parameters the same way.

---

#### ARCH-003: No Flash Loan Pattern Detection
**Impact:** Major DeFi vulnerability class undetected

Flash loan callback patterns:
1. Receive loan
2. Execute user-provided callback with user data
3. Expect repayment

This is not modeled.

---

#### ARCH-004: High-Level Call Tuple Context Discarded
**Location:** All `for _, call in high_level_calls:` iterations
**Impact:** Potentially valuable contract context lost

```python
# The first element is ALWAYS discarded
for _, call in high_level_calls:  # What is _? Contract reference? Type?
```

---

#### ARCH-005: No Property Debug Mode
**Impact:** Can't diagnose why properties have unexpected values

Need:
```bash
uv run alphaswarm build-kg path/ --debug-properties
# Should show: flashLoan.call_target_user_controlled = FALSE because destination=None
```

---

#### ARCH-006: Pattern Matching Silent on Missing Properties
**Location:** `patterns.py:899`
**Impact:** Pattern silently fails if property doesn't exist

```python
return node.properties.get(name)  # Returns None if missing
# Then: property: X, value: true
# Check: None == true → False (silent mismatch)
```

---

### Section 1.4: Testing & Validation Gaps

#### TEST-001: No Real-World Benchmark Suite
**Current:** Tests use synthetic contracts
**Missing:** Testing against known exploits (DVDeFi, Immunefi reports)

---

#### TEST-002: No Precision/Recall Metrics
**Current:** Pass/fail tests only
**Missing:** Quantitative detection metrics

---

#### TEST-003: No Renamed Contract Testing
**Current:** test_rename_baseline.py exists but incomplete
**Missing:** Systematic renamed variant testing

---

#### TEST-004: No False Positive Rate Tracking
**Current:** Only check for matches
**Missing:** Track matches on SAFE contracts (should be 0)

---

## Part II: Unified Fix Implementation Plan

### TRACK A: Property Derivation Fixes (builder.py)

#### Task A.1: Fix call_target_user_controlled for High-Level Calls
**Priority:** P0 - CRITICAL
**Effort:** 2 hours
**File:** `src/true_vkg/kg/builder.py`

**Before:**
```python
# Line 1446
"call_target_user_controlled": low_level_summary["call_target_user_controlled"],
```

**After:**
```python
# Line 1446
"call_target_user_controlled": (
    low_level_summary["call_target_user_controlled"]
    or external_call_target_user_controlled  # Already computed at line 926!
),
```

**Verification:**
```bash
uv run alphaswarm build-kg examples/damm-vuln-defi/src/truster/
uv run alphaswarm query "FIND functions WHERE call_target_user_controlled = true" \
  --graph examples/damm-vuln-defi/src/truster/.true_vkg/graphs/graph.json
# Expected: flashLoan
```

---

#### Task A.2: Add call_data_user_controlled for High-Level Calls
**Priority:** P0 - CRITICAL
**Effort:** 4 hours
**File:** `src/true_vkg/kg/builder.py`

**New Method:**
```python
def _external_call_data_user_controlled(
    self, external_calls, high_level_calls, parameter_names
) -> bool:
    """Check if high-level call arguments are user-controlled parameters."""
    for _, call in high_level_calls:
        arguments = getattr(call, "arguments", []) or []
        for arg in arguments:
            # Check if argument name matches a parameter
            arg_name = getattr(arg, "name", None)
            if arg_name and arg_name in parameter_names:
                return True

            # Check if argument value references a parameter
            if hasattr(arg, "value"):
                val_name = getattr(arg.value, "name", None)
                if val_name and val_name in parameter_names:
                    return True
    return False
```

**Property Update:**
```python
# After line 926
external_call_data_user_controlled = self._external_call_data_user_controlled(
    external_calls, high_level_calls, parameter_names
)

# Line 1448
"call_data_user_controlled": (
    low_level_summary["call_data_user_controlled"]
    or external_call_data_user_controlled
),
```

**Verification:**
```bash
# Truster passes 'data' parameter directly to functionCall
uv run alphaswarm query "FIND functions WHERE call_data_user_controlled = true" \
  --graph examples/damm-vuln-defi/src/truster/.true_vkg/graphs/graph.json
# Expected: flashLoan
```

---

#### Task A.3: Fix has_strict_equality_check
**Priority:** P0 - CRITICAL
**Effort:** 3 hours
**File:** `src/true_vkg/kg/builder.py`

**Complete Rewrite:**
```python
def _has_strict_equality_check(self, fn) -> bool:
    """Detect strict equality checks that could break invariants.

    Detects:
    - require(balance == X)
    - if (supply != Y) revert
    - assert(shares == Z)

    On balance-related values:
    - balance, balanceOf, totalSupply, shares, reserves
    - totalAssets, totalDeposits, poolBalance
    """
    # Get function source if available
    source = ""
    if hasattr(fn, "source_mapping") and fn.source_mapping:
        source = self._source_slice(fn)

    # Also check require expressions
    require_exprs = getattr(fn, "_vkg_require_exprs", []) or []

    # Combine all text to analyze
    all_sources = [source] + require_exprs

    # Balance-related keywords
    balance_keywords = [
        "balance", "supply", "shares", "total", "reserve",
        "assets", "deposits", "pool", "amount"
    ]

    for text in all_sources:
        if not text:
            continue

        lowered = text.lower()

        # Check for balance-related term
        has_balance = any(kw in lowered for kw in balance_keywords)
        if not has_balance:
            continue

        # Check for strict equality operators (== or !=)
        has_strict_eq = " == " in text or " != " in text
        if not has_strict_eq:
            continue

        # Exclude safe patterns that use >= or <=
        # These are bounds checks, not strict equality
        line_has_inequality = False
        for line in text.split('\n'):
            if (" == " in line or " != " in line):
                # Check if this specific line also has >= or <= (making it safe)
                if " >= " not in line and " <= " not in line:
                    return True

    return False
```

**Verification:**
```bash
uv run alphaswarm build-kg examples/damm-vuln-defi/src/unstoppable/
uv run alphaswarm query "FIND functions WHERE has_strict_equality_check = true" \
  --graph examples/damm-vuln-defi/src/unstoppable/.true_vkg/graphs/graph.json
# Expected: flashLoan
```

---

#### Task A.4: Fix _callsite_destination for Library Calls
**Priority:** P1 - HIGH
**Effort:** 4 hours
**File:** `src/true_vkg/kg/builder.py`

**Enhanced Method:**
```python
def _callsite_destination(self, call: Any) -> str | None:
    """Extract call destination, with special handling for library calls.

    Library calls like Address.functionCall(target, data) have:
    - destination.type = "address" (filtered elsewhere)
    - First argument IS the actual target

    We need to extract the first argument as destination for these patterns.
    """
    # Standard destination extraction
    destination = getattr(call, "destination", None)
    if destination is not None:
        name = getattr(destination, "name", None)
        if name:
            dest_str = str(name)
            # Don't return generic "address" type
            if dest_str.lower() not in ("address", "address payable"):
                return dest_str

    # For library calls, check function name and extract first argument
    func_name = getattr(call, "function_name", None) or getattr(call, "name", None)
    func_name_lower = str(func_name).lower() if func_name else ""

    # Known library call patterns where first arg is the target
    library_call_patterns = [
        "functioncall",           # Address.functionCall(target, data)
        "functioncallwithvalue",  # Address.functionCallWithValue(target, data, value)
        "sendvalue",              # Address.sendValue(target, amount)
        "call",                   # When wrapped
        "delegatecall",
        "staticcall",
    ]

    if func_name_lower in library_call_patterns:
        arguments = getattr(call, "arguments", []) or []
        if arguments:
            first_arg = arguments[0]
            arg_name = getattr(first_arg, "name", None)
            if arg_name:
                return str(arg_name)
            # Try to get the string representation
            arg_str = str(first_arg)
            if arg_str and arg_str not in ("None", ""):
                return arg_str

    # Fallback: try destination string if not "address"
    if destination is not None:
        dest_str = str(destination)
        if dest_str.lower() not in ("address", "address payable", "none"):
            return dest_str

    # Log for debugging (optional debug mode)
    if self._debug_mode:
        self._log_debug(f"_callsite_destination returned None for {call}")

    return None
```

---

#### Task A.5: Add Parameter Flow Tracking
**Priority:** P1 - HIGH
**Effort:** 6 hours
**File:** `src/true_vkg/kg/builder.py`

**New Properties:**
```python
def _analyze_parameter_call_flow(
    self, fn, parameter_names, param_types, high_level_calls, low_level_calls
) -> dict:
    """Track which parameters flow to external call arguments."""

    result = {
        "address_params_used_as_target": [],
        "bytes_params_used_as_data": [],
        "any_param_to_external_call": [],
        "has_callback_pattern": False,
    }

    # Identify address and bytes parameters
    address_params = set()
    bytes_params = set()
    for name, typ in zip(parameter_names, param_types):
        type_str = str(typ).lower() if typ else ""
        if "address" in type_str:
            address_params.add(name)
        if "bytes" in type_str:
            bytes_params.add(name)

    # Analyze high-level calls
    for _, call in high_level_calls:
        arguments = getattr(call, "arguments", []) or []

        for i, arg in enumerate(arguments):
            arg_name = getattr(arg, "name", None)
            if not arg_name:
                continue

            if arg_name in parameter_names:
                result["any_param_to_external_call"].append(arg_name)

                # First argument is typically the target
                if i == 0 and arg_name in address_params:
                    result["address_params_used_as_target"].append(arg_name)

                # Bytes parameters are typically call data
                if arg_name in bytes_params:
                    result["bytes_params_used_as_data"].append(arg_name)

    # Callback pattern: address param as target + bytes param as data
    result["has_callback_pattern"] = bool(
        result["address_params_used_as_target"] and
        result["bytes_params_used_as_data"]
    )

    return result
```

**New Node Properties:**
```python
# Add to function properties
"has_address_param_as_call_target": bool(param_flow["address_params_used_as_target"]),
"has_bytes_param_as_call_data": bool(param_flow["bytes_params_used_as_data"]),
"has_callback_pattern": param_flow["has_callback_pattern"],
"user_controlled_callback": (
    param_flow["has_callback_pattern"] and
    visibility in ("public", "external")
),
```

---

#### Task A.6: Add Flash Loan Pattern Detection
**Priority:** P1 - HIGH
**Effort:** 4 hours
**File:** `src/true_vkg/kg/builder.py`

**New Property:**
```python
def _detect_flashloan_pattern(self, fn, parameter_names, param_types) -> dict:
    """Detect flash loan callback patterns.

    Typical pattern:
    - Takes amount parameter
    - Takes target/receiver address parameter
    - Takes data/calldata bytes parameter
    - Makes external call to target with data
    - Has balance/pool state interactions
    """
    result = {
        "is_flashloan_like": False,
        "has_untrusted_callback": False,
        "callback_target_param": None,
        "callback_data_param": None,
    }

    fn_name = (fn.name or "").lower()

    # Name-based hint (not sole detection)
    name_hints = ["flash", "loan", "borrow", "lend"]
    has_name_hint = any(hint in fn_name for hint in name_hints)

    # Parameter structure analysis
    has_amount_param = False
    has_address_param = False
    has_bytes_param = False
    address_param_name = None
    bytes_param_name = None

    for name, typ in zip(parameter_names, param_types):
        type_str = str(typ).lower() if typ else ""
        name_lower = name.lower() if name else ""

        if "uint" in type_str and any(kw in name_lower for kw in ["amount", "qty", "value"]):
            has_amount_param = True
        if "address" in type_str:
            has_address_param = True
            # Prefer target/callback named params
            if any(kw in name_lower for kw in ["target", "callback", "receiver", "to"]):
                address_param_name = name
        if "bytes" in type_str:
            has_bytes_param = True
            bytes_param_name = name

    # Flashloan-like if has amount + address + bytes parameters
    if has_amount_param and has_address_param and has_bytes_param:
        result["is_flashloan_like"] = True
        result["callback_target_param"] = address_param_name
        result["callback_data_param"] = bytes_param_name

        # Check if this creates untrusted callback
        high_level_calls = getattr(fn, "high_level_calls", []) or []
        if high_level_calls and address_param_name:
            result["has_untrusted_callback"] = True

    return result
```

---

#### Task A.7: Add Property Debug Mode
**Priority:** P2 - MEDIUM
**Effort:** 3 hours
**File:** `src/true_vkg/kg/builder.py`

```python
class VKGBuilder:
    def __init__(self, ..., debug_properties: bool = False):
        self._debug_mode = debug_properties
        self._debug_log = []

    def _log_debug(self, message: str):
        if self._debug_mode:
            self._debug_log.append(message)
            print(f"[VKG-DEBUG] {message}")

    def _log_property_derivation(
        self, fn_name: str, prop_name: str, value: Any, reason: str
    ):
        if self._debug_mode:
            msg = f"{fn_name}.{prop_name} = {value} (reason: {reason})"
            self._log_debug(msg)
```

**CLI Integration:**
```bash
uv run alphaswarm build-kg path/to/contracts --debug-properties
```

---

### TRACK B: Pattern Rewrite (Semantic Operations)

#### Task B.1: Reentrancy Patterns (100% broken → 0%)
**Priority:** P0 - CRITICAL
**Effort:** 4 hours per pattern
**Target Status:** excellent

**Pattern: vm-001-reentrancy-classic**

```yaml
id: vm-001-reentrancy-classic
name: Classic Reentrancy (CEI Violation)
description: |
  ## What This Detects
  External calls or value transfers occurring BEFORE balance state updates,
  allowing attacker callbacks to re-enter and drain funds.

  ## Why It's Dangerous
  The classic reentrancy attack (DAO hack, $60M):
  1. Attacker calls withdraw()
  2. Contract sends ETH before updating balance
  3. Attacker's receive() callback re-enters withdraw()
  4. Repeat until drained

  ## Detection Logic
  1. Has TRANSFERS_VALUE_OUT OR CALLS_EXTERNAL operation
  2. Has WRITES_USER_BALANCE operation
  3. TRANSFER/CALL occurs BEFORE BALANCE WRITE (sequence_order)
  4. NO reentrancy guard property
  5. Public/external visibility

scope: Function
lens:
  - ValueMovement
  - ExternalInfluence
severity: critical
status: draft

match:
  tier_a:
    all:
      - property: visibility
        op: in
        value: [public, external]
      # Core signal: Both operations exist
      - has_all_operations:
          - TRANSFERS_VALUE_OUT
          - WRITES_USER_BALANCE
      # CEI Violation: Transfer BEFORE write
      - sequence_order:
          before: TRANSFERS_VALUE_OUT
          after: WRITES_USER_BALANCE
    none:
      # Exclusions - safe patterns
      - property: has_reentrancy_guard
        value: true
      - property: is_view
        value: true
      - property: is_pure
        value: true
      - property: is_constructor
        value: true
      - property: is_initializer_function
        value: true

# Alternative: Behavioral signature matching
match_alternatives:
  - signature_matches: "R:bal.*X:out.*W:bal"  # Read balance, transfer out, write balance
  - signature_matches: "X:call.*W:bal"        # External call before write

attack_scenarios:
  - name: Classic Reentrancy Drain
    preconditions:
      - Contract sends value before updating state
      - No reentrancy guard present
      - External call allows callback (ETH transfer, ERC777, etc.)
    steps:
      - Attacker calls vulnerable function (e.g., withdraw)
      - Contract calculates amount based on stored balance
      - Contract sends ETH/tokens to attacker
      - Attacker's receive()/fallback() re-enters the function
      - Balance not yet updated, check passes again
      - Repeat until contract drained
    impact: Complete fund drainage

fix_recommendations:
  - name: Apply CEI Pattern
    description: Update state BEFORE external calls
    example: |
      function withdraw(uint amount) external {
          require(balances[msg.sender] >= amount);
          balances[msg.sender] -= amount;  // STATE UPDATE FIRST
          payable(msg.sender).transfer(amount);  // THEN TRANSFER
      }
  - name: Use ReentrancyGuard
    description: Add OpenZeppelin ReentrancyGuard
    example: |
      import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

      contract MyContract is ReentrancyGuard {
          function withdraw(uint amount) external nonReentrant {
              // Safe even with wrong ordering
          }
      }

real_world_examples:
  - name: The DAO Hack
    date: 2016-06-17
    loss: $60M
    description: Recursive reentrancy drained 3.6M ETH
  - name: Cream Finance
    date: 2021-08-30
    loss: $18M
    description: AMP token callback reentrancy

cwe_mapping:
  - CWE-841  # Improper Enforcement of Behavioral Workflow
  - CWE-696  # Incorrect Behavior Order

owasp_mapping:
  - SC02  # Reentrancy

test_coverage:
  contracts:
    - tests/contracts/ReentrancyBasic.sol  # TP: withdraw vulnerable
    - tests/contracts/ReentrancySafe.sol   # TN: CEI pattern
    - tests/contracts/ReentrancyGuarded.sol # TN: nonReentrant modifier
    - tests/contracts/renamed/FundExtractor.sol # TP: renamed withdraw
  true_positives: 0
  true_negatives: 0
  precision: 0.0
  recall: 0.0
  last_tested: null
```

---

#### Task B.2: Arbitrary Call Patterns
**Priority:** P0 - CRITICAL
**Effort:** 4 hours
**Target Status:** excellent

**Pattern: ext-001-attacker-controlled-call**

```yaml
id: ext-001-attacker-controlled-call
name: Attacker-Controlled External Call
description: |
  ## What This Detects
  External call where BOTH the target address AND call data are controlled
  by user input, enabling arbitrary code execution.

  ## Why It's Dangerous
  Allows attacker to:
  - Execute any function on any contract
  - Steal tokens via transferFrom
  - Drain ETH via transfers
  - Manipulate state on behalf of the victim contract

scope: Function
lens:
  - ExternalInfluence
  - Authority
severity: critical
status: draft

match:
  tier_a:
    all:
      - property: visibility
        op: in
        value: [public, external]
      # Primary signals (any of these)
      - any:
          # Direct property check
          - all:
              - property: call_target_user_controlled
                value: true
              - property: call_data_user_controlled
                value: true
          # Callback pattern check
          - property: user_controlled_callback
            value: true
          # Flash loan callback pattern
          - all:
              - property: has_callback_pattern
                value: true
              - property: has_untrusted_callback
                value: true
    none:
      - property: has_access_gate
        value: true
      - property: has_reentrancy_guard
        value: true
      # Exclude well-known safe patterns
      - property: is_known_safe_callback
        value: true

attack_scenarios:
  - name: Token Theft via Callback
    steps:
      - Attacker calls vulnerable function with malicious target
      - Target = victim's token contract
      - Data = transferFrom(victim, attacker, balance)
      - Contract executes call on behalf of attacker
      - All approved tokens stolen

real_world_examples:
  - name: Damn Vulnerable DeFi - Truster
    description: Flash loan with arbitrary callback execution
```

---

#### Task B.3: Oracle Patterns (87.5% broken → 0%)
**Priority:** P0 - CRITICAL
**Effort:** 3 hours per pattern
**Target Status:** ready

**Pattern: oracle-001-missing-staleness**

```yaml
id: oracle-001-missing-staleness
name: Oracle Price Without Staleness Check
description: |
  ## What This Detects
  Oracle price reads without verifying data freshness (updatedAt timestamp).
  Stale prices can be manipulated or reflect outdated market conditions.

  ## Detection Logic
  1. Function READS_ORACLE operation detected
  2. Missing has_staleness_check property
  3. Public/external visibility

scope: Function
lens:
  - Oracle
  - ExternalInfluence
severity: high
status: draft

match:
  tier_a:
    all:
      - property: visibility
        op: in
        value: [public, external]
      - has_operation: READS_ORACLE
      - property: has_staleness_check
        value: false
    none:
      - property: is_view
        value: true
      - property: is_pure
        value: true
      # Exclude if oracle freshness is checked elsewhere
      - property: oracle_freshness_ok
        value: true

fix_recommendations:
  - name: Add Staleness Check
    example: |
      (, int256 price, , uint256 updatedAt, ) = priceFeed.latestRoundData();
      require(block.timestamp - updatedAt < MAX_STALENESS, "Stale price");
```

---

#### Task B.4: Authority Patterns (60% broken → 0%)
**Priority:** P1 - HIGH
**Effort:** 2 hours per pattern
**Target Status:** ready

**Pattern: auth-001-unprotected-privileged-write**

```yaml
id: auth-001-unprotected-privileged-write
name: Unprotected Privileged State Write
description: |
  ## What This Detects
  Functions that modify privileged state (owner, admin, roles, fees)
  without access control checks.

  ## Why Semantic Detection
  OLD (BROKEN): Check for "owner" or "admin" in variable names
  NEW (CORRECT): Check for writes_privileged_state property + missing CHECKS_PERMISSION

scope: Function
lens:
  - Authority
severity: critical
status: draft

match:
  tier_a:
    all:
      - property: visibility
        op: in
        value: [public, external]
      # Core signal: Writes privileged state
      - property: writes_privileged_state
        value: true
    none:
      # Must have NO access control
      - has_operation: CHECKS_PERMISSION
      - property: has_access_gate
        value: true
      - property: has_access_modifier
        value: true
      - property: has_require_msg_sender
        value: true
      # Safe contexts
      - property: is_constructor
        value: true
      - property: is_initializer_function
        value: true

# DO NOT USE:
# - property: modifiers
#   op: contains_any
#   value: [onlyOwner, onlyAdmin]  # NAME DEPENDENT - BROKEN
```

---

#### Task B.5: DoS Patterns
**Priority:** P1 - HIGH
**Effort:** 3 hours per pattern
**Target Status:** ready

**Pattern: dos-001-strict-equality**

```yaml
id: dos-001-strict-equality
name: DoS via Strict Balance Equality
description: |
  ## What This Detects
  Functions using strict equality (== or !=) on balance/supply values,
  which can be manipulated by forced donations (selfdestruct, direct transfer).

  ## Real-World Impact
  - Attacker sends 1 wei to contract
  - Balance check fails: require(balance == expected)
  - Contract permanently bricked

scope: Function
lens:
  - DoS
  - Liveness
severity: medium
status: draft

match:
  tier_a:
    all:
      - property: visibility
        op: in
        value: [public, external]
      - property: has_strict_equality_check
        value: true
    none:
      - property: is_view
        value: true
      - property: is_pure
        value: true

fix_recommendations:
  - name: Use Inequality Check
    description: Replace == with >= to tolerate unexpected deposits
    example: |
      // BEFORE (vulnerable)
      require(address(this).balance == expectedBalance);

      // AFTER (safe)
      require(address(this).balance >= expectedBalance);
```

---

#### Task B.6: Token Patterns (85.7% broken → 0%)
**Priority:** P1 - HIGH
**Effort:** 3 hours per pattern
**Target Status:** ready

**Pattern: token-001-unchecked-return**

```yaml
id: token-001-unchecked-return
name: Unchecked Token Transfer Return Value
description: |
  ## What This Detects
  ERC20 transfer/transferFrom calls without checking return value.
  Some tokens (USDT) don't revert on failure, just return false.

scope: Function
lens:
  - Token
  - ValueMovement
severity: high
status: draft

match:
  tier_a:
    all:
      - property: visibility
        op: in
        value: [public, external]
      # Uses ERC20 transfer but doesn't guard return
      - property: uses_erc20_transfer
        value: true
      - property: token_return_guarded
        value: false
    none:
      # Safe if using SafeERC20
      - property: uses_safe_erc20
        value: true

# DO NOT USE:
# - property: external_call_targets
#   op: contains_any
#   value: [transfer, transferFrom]  # NAME DEPENDENT
```

---

### TRACK C: Testing & Validation Infrastructure

#### Task C.1: Create DVDeFi Test Suite
**Priority:** P0 - CRITICAL
**Effort:** 8 hours
**File:** `tests/test_dvdefi_detection.py`

```python
"""
Real-world vulnerability detection tests against Damn Vulnerable DeFi.

This test suite validates that BSKG can detect actual exploitable vulnerabilities
in known-vulnerable contracts.
"""

import pytest
from pathlib import Path
import json

DVDEFI_PATH = Path("examples/damm-vuln-defi/src")

class TestDVDeFiDetection:
    """Test BSKG detection against Damn Vulnerable DeFi challenges."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Build graphs for DVDeFi contracts if not cached."""
        # Implementation: build graphs, cache results
        pass

    # ==================== TRUSTER ====================

    def test_truster_arbitrary_call_detected(self):
        """
        Truster Challenge: Arbitrary external call via Address.functionCall

        Vulnerability: flashLoan passes user-controlled target and data
        to Address.functionCall(), allowing arbitrary code execution.

        Expected Properties:
        - call_target_user_controlled = TRUE
        - call_data_user_controlled = TRUE
        - has_callback_pattern = TRUE
        """
        graph = self.load_graph("truster/TrusterLenderPool")
        flashloan = self.find_function(graph, "flashLoan")

        # Property checks
        assert flashloan["properties"]["call_target_user_controlled"] == True, \
            "Should detect target parameter flows to call"
        assert flashloan["properties"]["call_data_user_controlled"] == True, \
            "Should detect data parameter flows to call"

        # Pattern checks
        matches = self.run_pattern(graph, "ext-001-attacker-controlled-call")
        assert "flashLoan" in matches, \
            "Pattern should match flashLoan function"

    # ==================== UNSTOPPABLE ====================

    def test_unstoppable_strict_equality_detected(self):
        """
        Unstoppable Challenge: DoS via strict equality check

        Vulnerability: if (convertToShares(totalSupply) != balanceBefore)
        Attacker can donate tokens to break the invariant check.

        Expected Properties:
        - has_strict_equality_check = TRUE
        """
        graph = self.load_graph("unstoppable/UnstoppableLender")
        flashloan = self.find_function(graph, "flashLoan")

        assert flashloan["properties"]["has_strict_equality_check"] == True, \
            "Should detect != comparison on balance"

        matches = self.run_pattern(graph, "dos-001-strict-equality")
        assert "flashLoan" in matches

    # ==================== SIDE ENTRANCE ====================

    def test_side_entrance_cross_function_detected(self):
        """
        Side-Entrance Challenge: Flash loan accounting bypass via deposit()

        Vulnerability: flashLoan reads balance, but deposit() can be called
        during callback to manipulate it.

        Expected Properties:
        - cross_function_reentrancy_read = TRUE (flashLoan reads balance)
        - cross_function_reentrancy_surface = TRUE (deposit writes balance)
        """
        graph = self.load_graph("side-entrance/SideEntranceLenderPool")
        flashloan = self.find_function(graph, "flashLoan")
        deposit = self.find_function(graph, "deposit")

        # Cross-function reentrancy detection
        assert flashloan["properties"].get("cross_function_reentrancy_read", False) or \
               flashloan["properties"].get("reads_balance_state", False), \
            "flashLoan should be marked as reading balance"

    # ==================== NAIVE RECEIVER ====================

    def test_naive_receiver_unauthorized_callback_detected(self):
        """
        Naive-Receiver Challenge: Anyone can trigger flash loan on behalf of receiver

        Vulnerability: flashLoan takes receiver as parameter, not msg.sender
        """
        graph = self.load_graph("naive-receiver/NaiveReceiverLenderPool")
        flashloan = self.find_function(graph, "flashLoan")

        # Receiver parameter is user-controlled
        assert flashloan["properties"]["call_target_user_controlled"] == True

    # ==================== FREE RIDER ====================

    def test_free_rider_payment_logic_detected(self):
        """
        Free-Rider Challenge: Payment sent before ownership transfer

        Vulnerability: ETH sent to current owner before NFT ownership changes,
        allowing attacker to receive payment for their own purchase.
        """
        graph = self.load_graph("free-rider/FreeRiderNFTMarketplace")
        buymany = self.find_function(graph, "buyMany")

        # Should detect value transfer before state update
        # Or detect the specific payment ordering issue
        assert buymany["properties"].get("value_before_state", False) or \
               buymany["properties"].get("state_write_after_external_call", False)

    # ==================== CLIMBER ====================

    def test_climber_execute_before_validate_detected(self):
        """
        Climber Challenge: execute() runs before checking if proposal is valid

        Vulnerability: Timelock executes operations THEN checks they were scheduled
        """
        graph = self.load_graph("climber/ClimberTimelock")
        execute = self.find_function(graph, "execute")

        # Should detect execute-before-validate pattern
        # This is a custom business logic bug
        pass  # TODO: Define detection criteria

    # ==================== SELFIE ====================

    def test_selfie_governance_attack_detected(self):
        """
        Selfie Challenge: Flash loan + governance attack

        Vulnerability: Can borrow tokens, create governance proposal,
        execute immediately with flash-loaned voting power
        """
        graph = self.load_graph("selfie/SelfiePool")
        flashloan = self.find_function(graph, "flashLoan")

        # Flash loan callback pattern
        assert flashloan["properties"].get("has_callback_pattern", False) or \
               flashloan["properties"]["call_target_user_controlled"]

    # ==================== HELPERS ====================

    def load_graph(self, contract_path: str) -> dict:
        """Load BSKG graph for a DVDeFi contract."""
        graph_path = DVDEFI_PATH / contract_path / ".true_vkg/graphs/graph.json"
        with open(graph_path) as f:
            return json.load(f)

    def find_function(self, graph: dict, name: str) -> dict:
        """Find function node in graph by name."""
        for node in graph.get("nodes", []):
            if node.get("type") == "Function" and node.get("name") == name:
                return node
        raise ValueError(f"Function {name} not found")

    def run_pattern(self, graph: dict, pattern_id: str) -> list[str]:
        """Run a pattern against graph and return matching function names."""
        # Implementation: use pattern engine
        pass
```

---

#### Task C.2: Create Precision/Recall Benchmark Framework
**Priority:** P1 - HIGH
**Effort:** 6 hours
**File:** `benchmarks/pattern_metrics.py`

```python
"""
Pattern precision and recall measurement framework.

Measures:
- Precision: TP / (TP + FP) - How many matches are real vulnerabilities?
- Recall: TP / (TP + FN) - How many vulnerabilities are found?
- F1: Harmonic mean of precision and recall
"""

from dataclasses import dataclass
from typing import Dict, List, Set

@dataclass
class PatternBenchmark:
    """Benchmark data for a vulnerability pattern."""
    pattern_id: str

    # Known vulnerable functions (must be detected)
    true_positives: Set[str]

    # Known safe functions (must NOT be detected)
    true_negatives: Set[str]

    # Expected results
    expected_matches: Set[str]

    # Actual results (filled after running)
    actual_matches: Set[str] = None

BENCHMARKS = {
    "reentrancy": PatternBenchmark(
        pattern_id="vm-001-reentrancy-classic",
        true_positives={
            "ReentrancyBasic.withdraw",
            "ReentrancyETH.withdrawAll",
            "ReentrancyCallback.drain",
            # DVDeFi
            "SideEntranceLenderPool.flashLoan",
        },
        true_negatives={
            "ReentrancySafe.withdraw",  # CEI pattern
            "ReentrancyGuarded.withdraw",  # Has nonReentrant
            "SafeVault.withdraw",  # All guards
        },
        expected_matches={
            "ReentrancyBasic.withdraw",
            "ReentrancyETH.withdrawAll",
            "ReentrancyCallback.drain",
            "SideEntranceLenderPool.flashLoan",
        }
    ),

    "arbitrary-call": PatternBenchmark(
        pattern_id="ext-001-attacker-controlled-call",
        true_positives={
            "TrusterLenderPool.flashLoan",
            "ArbitraryCall.execute",
            "UnsafeExecutor.run",
        },
        true_negatives={
            "SafeExecutor.execute",  # Has access control
            "Timelock.execute",  # Has delay check
        },
        expected_matches={
            "TrusterLenderPool.flashLoan",
            "ArbitraryCall.execute",
            "UnsafeExecutor.run",
        }
    ),

    "strict-equality": PatternBenchmark(
        pattern_id="dos-001-strict-equality",
        true_positives={
            "UnstoppableLender.flashLoan",
            "StrictVault.deposit",
        },
        true_negatives={
            "SafeVault.deposit",  # Uses >=
        },
        expected_matches={
            "UnstoppableLender.flashLoan",
            "StrictVault.deposit",
        }
    ),
}


def calculate_metrics(benchmark: PatternBenchmark) -> Dict:
    """Calculate precision, recall, F1 for a pattern benchmark."""
    if benchmark.actual_matches is None:
        raise ValueError("Must run pattern first to get actual_matches")

    tp = len(benchmark.actual_matches & benchmark.true_positives)
    fp = len(benchmark.actual_matches - benchmark.true_positives)
    fn = len(benchmark.true_positives - benchmark.actual_matches)
    tn = len(benchmark.true_negatives - benchmark.actual_matches)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    # False positive rate on safe contracts
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_positive_rate": fpr,
    }


def generate_metrics_report(results: Dict[str, Dict]) -> str:
    """Generate markdown report of pattern metrics."""
    lines = ["# Pattern Metrics Report\n"]
    lines.append("| Pattern | Precision | Recall | F1 | FPR |")
    lines.append("|---------|-----------|--------|-----|-----|")

    for pattern_id, metrics in results.items():
        lines.append(
            f"| {pattern_id} | "
            f"{metrics['precision']:.1%} | "
            f"{metrics['recall']:.1%} | "
            f"{metrics['f1']:.2f} | "
            f"{metrics['false_positive_rate']:.1%} |"
        )

    return "\n".join(lines)
```

---

#### Task C.3: Create Property Coverage Report Tool
**Priority:** P2 - MEDIUM
**Effort:** 4 hours
**File:** `scripts/property_coverage.py`

```python
#!/usr/bin/env python3
"""
Property Coverage Report

Analyzes a BSKG graph and reports which properties are:
- Always FALSE (potential derivation bug)
- Always TRUE (may be too broad)
- Missing (not computed)
- Correctly varied (good signal)
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

def analyze_property_coverage(graph_path: str) -> dict:
    """Analyze property coverage in a BSKG graph."""

    with open(graph_path) as f:
        graph = json.load(f)

    # Track property values across all function nodes
    property_values = defaultdict(list)

    for node in graph.get("nodes", []):
        if node.get("type") != "Function":
            continue

        props = node.get("properties", {})
        for name, value in props.items():
            property_values[name].append({
                "function": node.get("name"),
                "value": value
            })

    # Analyze each property
    analysis = {}
    for prop_name, values in property_values.items():
        all_values = [v["value"] for v in values]

        # Skip non-boolean properties
        if not all(isinstance(v, bool) for v in all_values):
            continue

        true_count = sum(1 for v in all_values if v)
        false_count = sum(1 for v in all_values if not v)
        total = len(all_values)

        status = "GOOD"
        if true_count == 0:
            status = "ALWAYS_FALSE"  # Potential bug
        elif false_count == 0:
            status = "ALWAYS_TRUE"  # May be too broad
        elif true_count < total * 0.1:
            status = "MOSTLY_FALSE"
        elif false_count < total * 0.1:
            status = "MOSTLY_TRUE"

        analysis[prop_name] = {
            "true_count": true_count,
            "false_count": false_count,
            "total": total,
            "true_rate": true_count / total if total > 0 else 0,
            "status": status,
            "examples_true": [v["function"] for v in values if v["value"]][:3],
            "examples_false": [v["function"] for v in values if not v["value"]][:3],
        }

    return analysis


def print_coverage_report(analysis: dict):
    """Print formatted coverage report."""

    # Group by status
    always_false = [(k, v) for k, v in analysis.items() if v["status"] == "ALWAYS_FALSE"]
    always_true = [(k, v) for k, v in analysis.items() if v["status"] == "ALWAYS_TRUE"]
    good = [(k, v) for k, v in analysis.items() if v["status"] == "GOOD"]

    print("=" * 60)
    print("PROPERTY COVERAGE REPORT")
    print("=" * 60)

    print(f"\nALWAYS FALSE ({len(always_false)}) - POTENTIAL BUGS:")
    print("-" * 40)
    for name, data in sorted(always_false):
        print(f"  {name}: 0/{data['total']} TRUE")

    print(f"\nALWAYS TRUE ({len(always_true)}) - MAY BE TOO BROAD:")
    print("-" * 40)
    for name, data in sorted(always_true):
        print(f"  {name}: {data['total']}/{data['total']} TRUE")

    print(f"\nGOOD SIGNAL ({len(good)}):")
    print("-" * 40)
    for name, data in sorted(good, key=lambda x: x[1]["true_rate"], reverse=True):
        print(f"  {name}: {data['true_count']}/{data['total']} ({data['true_rate']:.0%})")
        if data["examples_true"]:
            print(f"    TRUE in: {', '.join(data['examples_true'])}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze BSKG property coverage")
    parser.add_argument("graph", help="Path to graph.json")
    args = parser.parse_args()

    analysis = analyze_property_coverage(args.graph)
    print_coverage_report(analysis)
```

---

### TRACK D: Limitation Detection & System Evolution

#### Task D.1: Implement Limitation Detection Framework
**Priority:** P1 - HIGH
**Effort:** 8 hours
**File:** `src/true_vkg/validation/limitation_detector.py`

```python
"""
Limitation Detection Framework

Automatically detects and reports system limitations during analysis.
Records cases where BSKG cannot properly analyze code.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
import json
from datetime import datetime

class LimitationType(Enum):
    """Categories of system limitations."""

    # Property derivation issues
    PROPERTY_ALWAYS_FALSE = "property_always_false"
    PROPERTY_ALWAYS_TRUE = "property_always_true"
    PROPERTY_MISSING = "property_missing"

    # Slither extraction issues
    SLITHER_ATTRIBUTE_NONE = "slither_attribute_none"
    SLITHER_TYPE_FILTERED = "slither_type_filtered"

    # Pattern matching issues
    PATTERN_NO_MATCHES = "pattern_no_matches"
    PATTERN_EXCESSIVE_MATCHES = "pattern_excessive_matches"

    # Semantic operation issues
    OPERATION_NOT_DETECTED = "operation_not_detected"

    # Architecture limitations
    CROSS_FUNCTION_NOT_SUPPORTED = "cross_function_not_supported"
    CROSS_CONTRACT_NOT_SUPPORTED = "cross_contract_not_supported"
    LIBRARY_CALL_NOT_HANDLED = "library_call_not_handled"

    # Unknown/new
    UNKNOWN = "unknown"


@dataclass
class Limitation:
    """A detected system limitation."""

    type: LimitationType
    severity: str  # critical, high, medium, low
    description: str

    # Context
    file: Optional[str] = None
    function: Optional[str] = None
    line: Optional[int] = None

    # Evidence
    expected: Any = None
    actual: Any = None

    # Metadata
    detected_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "severity": self.severity,
            "description": self.description,
            "file": self.file,
            "function": self.function,
            "line": self.line,
            "expected": str(self.expected),
            "actual": str(self.actual),
            "detected_at": self.detected_at,
        }


class LimitationDetector:
    """Detects and records system limitations."""

    def __init__(self):
        self.limitations: List[Limitation] = []

    def record(
        self,
        type: LimitationType,
        severity: str,
        description: str,
        **kwargs
    ):
        """Record a detected limitation."""
        limitation = Limitation(
            type=type,
            severity=severity,
            description=description,
            **kwargs
        )
        self.limitations.append(limitation)

    def check_property_derivation(self, fn_name: str, prop_name: str, value: Any, expected: Any):
        """Check if property derivation matches expectation."""
        if value != expected:
            self.record(
                type=LimitationType.PROPERTY_ALWAYS_FALSE if expected and not value
                     else LimitationType.PROPERTY_ALWAYS_TRUE,
                severity="high",
                description=f"Property {prop_name} = {value}, expected {expected}",
                function=fn_name,
                expected=expected,
                actual=value,
            )

    def check_slither_extraction(self, call: Any, attribute: str, value: Any):
        """Check if Slither attribute extraction succeeded."""
        if value is None:
            self.record(
                type=LimitationType.SLITHER_ATTRIBUTE_NONE,
                severity="medium",
                description=f"Slither attribute '{attribute}' returned None",
                expected="non-None value",
                actual=None,
            )

    def check_library_call(self, call: Any, destination: Any):
        """Check if library call handling succeeded."""
        if destination is None:
            func_name = getattr(call, "function_name", "unknown")
            self.record(
                type=LimitationType.LIBRARY_CALL_NOT_HANDLED,
                severity="high",
                description=f"Library call '{func_name}' destination not extracted",
                expected="destination string",
                actual=None,
            )

    def generate_report(self) -> str:
        """Generate markdown report of limitations."""
        if not self.limitations:
            return "# No Limitations Detected\n"

        lines = ["# System Limitations Report\n"]
        lines.append(f"**Generated:** {datetime.now().isoformat()}\n")
        lines.append(f"**Total Limitations:** {len(self.limitations)}\n")

        # Group by type
        by_type: Dict[LimitationType, List[Limitation]] = {}
        for lim in self.limitations:
            by_type.setdefault(lim.type, []).append(lim)

        # Summary table
        lines.append("## Summary\n")
        lines.append("| Type | Count | Severity |")
        lines.append("|------|-------|----------|")
        for ltype, lims in sorted(by_type.items(), key=lambda x: len(x[1]), reverse=True):
            severities = set(l.severity for l in lims)
            lines.append(f"| {ltype.value} | {len(lims)} | {', '.join(severities)} |")

        # Details
        lines.append("\n## Details\n")
        for ltype, lims in by_type.items():
            lines.append(f"### {ltype.value}\n")
            for lim in lims[:10]:  # Top 10 per type
                lines.append(f"- **{lim.severity.upper()}**: {lim.description}")
                if lim.function:
                    lines.append(f"  - Function: `{lim.function}`")
                if lim.expected:
                    lines.append(f"  - Expected: `{lim.expected}`, Actual: `{lim.actual}`")
            if len(lims) > 10:
                lines.append(f"- ... and {len(lims) - 10} more")
            lines.append("")

        return "\n".join(lines)

    def save_json(self, path: str):
        """Save limitations as JSON."""
        data = {
            "generated_at": datetime.now().isoformat(),
            "total": len(self.limitations),
            "limitations": [l.to_dict() for l in self.limitations]
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
```

---

#### Task D.2: Create Known Limitations Database
**Priority:** P1 - HIGH
**Effort:** 4 hours
**File:** `docs/reference/known-limitations.md`

```markdown
# BSKG Known Limitations Database

This document tracks all known limitations of the BSKG system, their impact,
and planned fixes.

## Critical Limitations (Detection Failures)

### LIM-001: High-Level Call Target Extraction
**Status:** FIXING
**Impact:** 100% miss rate on library call vulnerabilities
**Affected:** Truster, any Address.functionCall usage
**Root Cause:** `_callsite_destination()` returns None for library calls
**Fix Task:** A.4

### LIM-002: High-Level Call Data Not Analyzed
**Status:** FIXING
**Impact:** Can't detect user-controlled call data
**Affected:** All callback patterns
**Root Cause:** Only low-level calls checked for data
**Fix Task:** A.2

### LIM-003: Strict Equality Detection Limited
**Status:** FIXING
**Impact:** Misses DoS vulnerabilities
**Affected:** Unstoppable, any `!=` or `if` patterns
**Root Cause:** Only checks `require` with `==`
**Fix Task:** A.3

## High Limitations (Reduced Accuracy)

### LIM-004: State Write After Call Limited Scope
**Status:** PLANNED
**Impact:** 31 patterns affected
**Affected:** All reentrancy patterns
**Root Cause:** Only direct writes detected
**Fix Task:** Future

### LIM-005: Cross-Function Reentrancy Incomplete
**Status:** PLANNED
**Impact:** Sophisticated attacks missed
**Affected:** Side-Entrance pattern
**Root Cause:** Single-function scope only
**Fix Task:** Future

### LIM-006: Dataflow Analysis Reliability
**Status:** INVESTIGATING
**Impact:** attacker_controlled_write unreliable
**Affected:** 6 patterns
**Root Cause:** Unclear if dataflow runs
**Fix Task:** A.7 (debug mode)

## Medium Limitations (Workarounds Available)

### LIM-007: No Parameter-to-Call Tracking
**Status:** FIXING
**Impact:** Can't connect params to call args
**Workaround:** Use param names heuristically
**Fix Task:** A.5

### LIM-008: Flash Loan Pattern Not Modeled
**Status:** FIXING
**Impact:** Major DeFi pattern missed
**Workaround:** Manual callback detection
**Fix Task:** A.6

### LIM-009: Name-Based Pattern Matching
**Status:** FIXING
**Impact:** 49.8% of patterns affected
**Workaround:** Use semantic operations
**Fix Task:** Track B

## Low Limitations (Edge Cases)

### LIM-010: Tuple Context Discarded
**Status:** DEFERRED
**Impact:** Missing contract context
**Mitigation:** Use other attributes

### LIM-011: Slither Version Differences
**Status:** MONITORING
**Impact:** Attribute availability varies
**Mitigation:** Multiple fallback checks

## Architectural Limitations (Design Constraints)

### LIM-ARCH-001: Single-Contract Analysis
**Description:** BSKG analyzes contracts individually, not cross-contract
**Impact:** Cross-contract attacks not detected
**Mitigation:** Use cross_contract_* properties when available

### LIM-ARCH-002: Static Analysis Only
**Description:** No dynamic/symbolic execution
**Impact:** Path-sensitive vulnerabilities may be missed
**Mitigation:** Use operation sequence detection

### LIM-ARCH-003: Heuristic-Based Detection
**Description:** Many properties use heuristics, not formal verification
**Impact:** False negatives on unusual patterns
**Mitigation:** Multiple detection strategies per vulnerability

## Limitation Statistics

| Category | Count | Fixing | Planned | Deferred |
|----------|-------|--------|---------|----------|
| Critical | 3 | 3 | 0 | 0 |
| High | 3 | 1 | 2 | 0 |
| Medium | 3 | 2 | 1 | 0 |
| Low | 2 | 0 | 0 | 2 |
| Architecture | 3 | 0 | 0 | 3 |
| **Total** | **14** | **6** | **3** | **5** |
```

---

#### Task D.3: Create System Evolution Tracker
**Priority:** P2 - MEDIUM
**Effort:** 4 hours
**File:** `docs/EVOLUTION.md`

```markdown
# BSKG System Evolution Tracker

Tracks system improvements, lessons learned, and architectural decisions.

## Evolution Log

### 2025-12-31: Real-World Detection Crisis

**Trigger:** DVDeFi testing revealed 0% detection rate

**Root Causes Identified:**
1. Property derivation bugs (4 critical)
2. Pattern design issues (49.8% name-dependent)
3. Missing testing infrastructure

**Actions Taken:**
- Created UNIFIED_VKG_MEGA_TASK.md
- Implemented limitation detection framework
- Started Track A (property fixes)
- Started Track B (pattern rewrites)

**Lessons Learned:**
- Unit tests don't guarantee real-world performance
- Property derivation must be tested on known vulnerabilities
- Patterns need semantic operations, not name matching

### Architecture Decisions

#### ADR-001: Semantic Operations over Name Matching
**Status:** ADOPTED
**Context:** 49.8% of patterns used name matching, failing on renamed contracts
**Decision:** All patterns must use semantic operations
**Consequences:** Pattern rewrite required, but more robust detection

#### ADR-002: Property Debug Mode
**Status:** IMPLEMENTING
**Context:** Can't diagnose property derivation failures
**Decision:** Add --debug-properties flag to track derivation
**Consequences:** Easier debugging, slight performance overhead

#### ADR-003: Limitation Detection Integration
**Status:** IMPLEMENTING
**Context:** System limitations discovered ad-hoc
**Decision:** Integrate automatic limitation detection
**Consequences:** Better visibility, automated reporting

## Improvement Backlog

### High Priority
- [ ] Cross-contract analysis (LIM-ARCH-001)
- [ ] Symbolic execution integration (LIM-ARCH-002)
- [ ] Dataflow analysis verification (LIM-006)

### Medium Priority
- [ ] Slither version compatibility layer (LIM-011)
- [ ] Enhanced tuple context extraction (LIM-010)
- [ ] Pattern recommendation engine

### Low Priority
- [ ] Machine learning for pattern discovery
- [ ] Automatic false positive feedback
- [ ] IDE integration

## Metrics History

| Date | DVDeFi Detection | Name Dependency | Precision | Recall |
|------|------------------|-----------------|-----------|--------|
| 2025-12-31 | 0% | 49.8% | Unknown | Unknown |
| Target | 89% | <5% | >90% | >85% |
```

---

## Part III: Implementation Schedule

### Week 1: Foundation Fixes (Critical)

| Day | Track A Tasks | Track B Tasks | Track C Tasks |
|-----|---------------|---------------|---------------|
| 1 | A.1: call_target fix | B.1 Start: reentrancy | - |
| 2 | A.2: call_data fix | B.1 Complete | C.1 Start: DVDeFi tests |
| 3 | A.3: strict_equality | B.2: arbitrary call | C.1 Continue |
| 4 | A.4: library calls | B.3: oracle patterns | C.1 Complete |
| 5 | Testing & validation | Testing & validation | Run all tests |

**Week 1 Success Criteria:**
- [ ] DVDeFi detection: 5/18 (28%)
- [ ] Truster: flashLoan detected
- [ ] Unstoppable: flashLoan detected
- [ ] 4 critical bugs fixed

### Week 2: Pattern Overhaul (High)

| Day | Track A Tasks | Track B Tasks | Track C Tasks |
|-----|---------------|---------------|---------------|
| 1 | A.5: param flow | B.4: authority | C.2: metrics framework |
| 2 | A.6: flashloan | B.5: DoS | C.2 Complete |
| 3 | A.7: debug mode | B.6: token | C.3: coverage report |
| 4 | Testing | Pattern testing | Integration tests |
| 5 | Bug fixes | Bug fixes | Report generation |

**Week 2 Success Criteria:**
- [ ] DVDeFi detection: 10/18 (55%)
- [ ] Name dependency: < 25%
- [ ] Critical patterns: "ready" status

### Week 3: Quality & Validation (Medium)

| Day | Track D Tasks | Track B Tasks | Track C Tasks |
|-----|---------------|---------------|---------------|
| 1 | D.1: limitation detector | Remaining patterns | Full test suite run |
| 2 | D.2: limitations DB | Pattern refinement | Precision dashboard |
| 3 | D.3: evolution tracker | Edge case handling | Benchmark analysis |
| 4 | Integration | Integration | Documentation |
| 5 | Final validation | Final validation | Final report |

**Week 3 Success Criteria:**
- [ ] DVDeFi detection: 14/18 (78%)
- [ ] Name dependency: < 10%
- [ ] All critical patterns: "ready" or "excellent"
- [ ] Limitation report generated

### Week 4: Excellence Push (Polish)

| Focus | Target |
|-------|--------|
| Remaining DVDeFi challenges | 16/18 (89%) |
| Pattern precision | > 90% critical |
| Pattern recall | > 85% critical |
| Name dependency | < 5% |
| Documentation | Complete |

---

## Part IV: Definition of Done

### Track A: Property Derivation
- [ ] BUG-001 fixed: call_target_user_controlled for high-level
- [ ] BUG-002 fixed: call_data_user_controlled for high-level
- [ ] BUG-003 fixed: has_strict_equality_check comprehensive
- [ ] BUG-004 fixed: Library call destination extraction
- [ ] BUG-005 addressed: State write scope documented
- [ ] New: Parameter flow tracking implemented
- [ ] New: Flash loan pattern detection implemented
- [ ] New: Debug mode available

### Track B: Pattern Rewrite
- [ ] 100% critical patterns use semantic operations
- [ ] Name dependency < 5%
- [ ] All critical patterns at "ready" or "excellent"
- [ ] All high patterns at "ready"
- [ ] Precision > 90% for critical
- [ ] Recall > 85% for critical

### Track C: Testing
- [ ] DVDeFi test suite complete
- [ ] Precision/recall metrics automated
- [ ] Property coverage tool working
- [ ] CI pipeline integrated

### Track D: Limitations
- [ ] Limitation detector integrated
- [ ] Known limitations documented
- [ ] Evolution tracker established
- [ ] Future roadmap defined

### Overall Success
- [ ] DVDeFi detection rate > 85%
- [ ] No silent failures in property derivation
- [ ] All patterns use semantic operations
- [ ] Comprehensive test coverage
- [ ] Full documentation

---

## Appendix A: Quick Reference - Semantic Operations

```yaml
# VALUE MOVEMENT
TRANSFERS_VALUE_OUT     # Sends ETH/tokens (replace: withdraw, transfer names)
RECEIVES_VALUE_IN       # Receives ETH/tokens
READS_USER_BALANCE      # Reads user balance state
WRITES_USER_BALANCE     # Modifies user balance state

# ACCESS CONTROL
CHECKS_PERMISSION       # Any auth check (replace: onlyOwner, onlyAdmin)
MODIFIES_OWNER          # Changes ownership (replace: setOwner, transferOwnership)
MODIFIES_ROLES          # Changes roles

# EXTERNAL INTERACTION
CALLS_EXTERNAL          # Makes external call
CALLS_UNTRUSTED         # Calls user-controlled target
READS_EXTERNAL_VALUE    # Reads external data

# STATE
MODIFIES_CRITICAL_STATE # Changes critical state
INITIALIZES_STATE       # Initialization
READS_ORACLE            # Oracle price read

# CONTROL FLOW
LOOPS_OVER_ARRAY        # Array iteration
USES_TIMESTAMP          # block.timestamp
USES_BLOCK_DATA         # block.number, etc.

# ARITHMETIC
PERFORMS_DIVISION       # Division operation
PERFORMS_MULTIPLICATION # Multiplication operation

# VALIDATION
VALIDATES_INPUT         # Input validation
EMITS_EVENT             # Event emission
```

## Appendix B: Behavioral Signature Codes

```
X:out  = TRANSFERS_VALUE_OUT
X:in   = RECEIVES_VALUE_IN
R:bal  = READS_USER_BALANCE
W:bal  = WRITES_USER_BALANCE
C:auth = CHECKS_PERMISSION
M:own  = MODIFIES_OWNER
M:role = MODIFIES_ROLES
X:call = CALLS_EXTERNAL
X:unk  = CALLS_UNTRUSTED
R:ext  = READS_EXTERNAL_VALUE
M:crit = MODIFIES_CRITICAL_STATE
I:init = INITIALIZES_STATE
R:orc  = READS_ORACLE
L:arr  = LOOPS_OVER_ARRAY
U:time = USES_TIMESTAMP
U:blk  = USES_BLOCK_DATA
A:div  = PERFORMS_DIVISION
A:mul  = PERFORMS_MULTIPLICATION
V:in   = VALIDATES_INPUT
E:evt  = EMITS_EVENT

# Example signatures:
# Reentrancy: R:bal→X:out→W:bal (read balance, transfer, write balance)
# Safe CEI:  R:bal→W:bal→X:out (read balance, write balance, transfer)
```

## Appendix C: Pattern Quality Thresholds

| Status | Precision | Recall | Variation | Test Cases |
|--------|-----------|--------|-----------|------------|
| draft | < 70% | < 50% | < 60% | < 3 |
| ready | >= 70% | >= 50% | >= 60% | >= 3 |
| excellent | >= 90% | >= 85% | >= 85% | >= 5 |

---

**Document Version:** 1.0
**Last Updated:** 2025-12-31
**Status:** ACTIVE - IMPLEMENTATION IN PROGRESS

---

*This document supersedes:*
- `task/VKG_REAL_WORLD_FIX_TASKLIST.md`
- `task/pattern-rewrite/PATTERN_REWRITE_MEGA_TASK.md`

*All work should reference this unified task list.*
