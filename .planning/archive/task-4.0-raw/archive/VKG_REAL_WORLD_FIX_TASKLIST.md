# BSKG Real-World Detection Fix: Comprehensive Task List

## Executive Summary

**Problem**: BSKG patterns exist and are well-designed, but they detect **0 vulnerabilities** in real-world exploitable code (Damn Vulnerable DeFi). The root cause is **property derivation failures** in `builder.py`, not pattern design.

**Evidence**: Testing against 5 DVDeFi challenges showed:
- Truster: `call_target_user_controlled = false` (should be TRUE)
- Truster: `call_data_user_controlled = false` (should be TRUE)
- Unstoppable: `has_strict_equality_check = false` (should be TRUE)
- Side-Entrance: Same property derivation failures
- Free-Rider/Climber: Pattern conditions never match

**Root Cause Categories**:
1. **High-Level Call Analysis Gap**: Only low-level calls analyzed for user-controlled targets/data
2. **Strict Equality Detection**: Only checks `require` with `==`, misses `if` with `!=`
3. **Library Call Handling**: `Address.functionCall()` destination extraction fails
4. **Taint Propagation**: Parameter-to-call-argument flow not tracked
5. **Silent Failures**: `None` destinations silently treated as "not user-controlled"

---

## Phase 1: Critical Property Derivation Fixes (HIGH PRIORITY)

### Task 1.1: Fix `call_target_user_controlled` for High-Level Calls
**File**: `src/true_vkg/kg/builder.py`
**Lines**: 1446, 2068-2092

**Current Bug**:
```python
# Line 1446 - Only uses low-level summary
"call_target_user_controlled": low_level_summary["call_target_user_controlled"],
```

**Fix Required**:
```python
# Line 1446 - Combine low-level AND high-level analysis
"call_target_user_controlled": (
    low_level_summary["call_target_user_controlled"]
    or external_call_target_user_controlled  # Already computed at line 926!
),
```

**Verification Test**:
```bash
# Build graph for Truster
uv run alphaswarm build-kg examples/damm-vuln-defi/src/truster/

# Query should return flashLoan
uv run alphaswarm query "FIND functions WHERE call_target_user_controlled = true" \
  --graph examples/damm-vuln-defi/src/truster/.true_vkg/graphs/graph.json
```

**Acceptance Criteria**:
- [ ] `flashLoan` in Truster returns `call_target_user_controlled = true`
- [ ] Existing tests still pass
- [ ] No false positives on safe contracts

---

### Task 1.2: Add `call_data_user_controlled` for High-Level Calls
**File**: `src/true_vkg/kg/builder.py`
**Lines**: 1448, new method needed

**Current Bug**:
```python
# Line 1448 - Only low-level summary
"call_data_user_controlled": low_level_summary["call_data_user_controlled"],
```

**Fix Required**:
1. Create new method `_external_call_data_user_controlled()`:
```python
def _external_call_data_user_controlled(
    self, external_calls, high_level_calls, parameter_names
) -> bool:
    """Check if high-level call arguments are user-controlled."""
    for _, call in high_level_calls:
        arguments = getattr(call, "arguments", []) or []
        for arg in arguments:
            arg_name = getattr(arg, "name", None)
            if arg_name and arg_name in parameter_names:
                return True
            # Also check if argument IS a parameter reference
            if hasattr(arg, "value"):
                val_name = getattr(arg.value, "name", None)
                if val_name and val_name in parameter_names:
                    return True
    return False
```

2. Update property assignment:
```python
"call_data_user_controlled": (
    low_level_summary["call_data_user_controlled"]
    or self._external_call_data_user_controlled(external_calls, high_level_calls, parameter_names)
),
```

**Verification Test**:
```bash
# Truster's flashLoan passes 'data' parameter directly to functionCall
uv run alphaswarm query "FIND functions WHERE call_data_user_controlled = true" \
  --graph examples/damm-vuln-defi/src/truster/.true_vkg/graphs/graph.json
# Expected: flashLoan
```

**Acceptance Criteria**:
- [ ] `flashLoan` in Truster returns `call_data_user_controlled = true`
- [ ] `data` parameter detected as flowing to external call

---

### Task 1.3: Fix `has_strict_equality_check` to Detect All Patterns
**File**: `src/true_vkg/kg/builder.py`
**Lines**: 4853-4862

**Current Bug**:
```python
def _has_strict_equality_check(self, require_exprs: list[str]) -> bool:
    for expr in require_exprs:  # ONLY checks require!
        lowered = expr.lower()
        has_balance = "balance" in lowered and ("this" in lowered or "address(this)" in lowered)
        has_strict_eq = " == " in expr  # ONLY checks ==, not !=
```

**Problems**:
1. Only checks `require` expressions, not `if` statements
2. Only checks `==`, not `!=`
3. Only checks `address(this).balance`, misses `totalSupply`, `shares`, etc.

**Fix Required**:
```python
def _has_strict_equality_check(self, fn) -> bool:
    """Detect strict equality checks that could break invariants."""
    # Get full function source
    source = self._source_slice(fn) if hasattr(fn, 'source_mapping') else ""

    # Also check require expressions
    require_exprs = getattr(fn, "_vkg_require_exprs", []) or []
    all_sources = [source] + require_exprs

    for text in all_sources:
        lowered = text.lower()

        # Check for balance-related comparisons
        balance_keywords = ["balance", "supply", "shares", "total", "reserve"]
        has_balance = any(kw in lowered for kw in balance_keywords)

        # Check for strict equality (== or !=)
        has_strict_eq = " == " in text or " != " in text

        # Check for dangerous patterns
        if has_balance and has_strict_eq:
            # Exclude safe patterns like `require(balance >= amount)`
            if " >= " not in text and " <= " not in text and " > " not in text and " < " not in text:
                return True

    return False
```

**Verification Test**:
```bash
# Unstoppable uses: if (convertToShares(totalSupply) != balanceBefore)
uv run alphaswarm query "FIND functions WHERE has_strict_equality_check = true" \
  --graph examples/damm-vuln-defi/src/unstoppable/.true_vkg/graphs/graph.json
# Expected: flashLoan
```

**Acceptance Criteria**:
- [ ] Unstoppable's `flashLoan` returns `has_strict_equality_check = true`
- [ ] Detects `!=` comparisons on balance/supply
- [ ] Detects `if` statements, not just `require`

---

### Task 1.4: Fix `_callsite_destination` for Library Calls
**File**: `src/true_vkg/kg/builder.py`
**Lines**: 5276-5283

**Current Bug**:
```python
def _callsite_destination(self, call: Any) -> str | None:
    destination = getattr(call, "destination", None)
    if destination is None:
        return None  # SILENT FAILURE
    name = getattr(destination, "name", None)
    if name:
        return str(name)
    return str(destination)
```

**Problem**: For `Address.functionCall(target, data)`:
- `destination` might be `None` or type `"address"` (filtered out elsewhere)
- The FIRST ARGUMENT is the actual target (`target` parameter)

**Fix Required**:
```python
def _callsite_destination(self, call: Any) -> str | None:
    """Extract call destination, handling library calls."""
    # Standard destination extraction
    destination = getattr(call, "destination", None)
    if destination is not None:
        name = getattr(destination, "name", None)
        if name:
            return str(name)
        # Don't return str(destination) if it's just "address"
        dest_str = str(destination)
        if dest_str and dest_str.lower() != "address":
            return dest_str

    # For library calls (e.g., Address.functionCall(target, data))
    # The first argument IS the destination
    func_name = getattr(call, "function_name", None) or getattr(call, "name", None)
    if func_name and func_name.lower() in ("functioncall", "functioncallwithvalue", "sendvalue", "call"):
        arguments = getattr(call, "arguments", []) or []
        if arguments:
            first_arg = arguments[0]
            arg_name = getattr(first_arg, "name", None)
            if arg_name:
                return str(arg_name)

    return None
```

**Verification Test**:
```bash
# Truster uses: target.functionCall(data)
# 'target' parameter should be detected as destination
```

**Acceptance Criteria**:
- [ ] Library calls like `Address.functionCall(target, ...)` return `target` as destination
- [ ] Standard calls still work correctly

---

## Phase 2: Taint Analysis & Parameter Flow

### Task 2.1: Track Parameter-to-Call-Argument Flow
**File**: `src/true_vkg/kg/builder.py`
**New Property**: `parameter_flows_to_external_call`

**Description**: Track which function parameters flow into external call arguments.

**Implementation**:
```python
def _analyze_parameter_flow(self, fn, parameter_names, high_level_calls, low_level_calls) -> dict:
    """Analyze which parameters flow to external calls."""
    result = {
        "address_params_to_call_target": [],  # address params used as call targets
        "bytes_params_to_call_data": [],      # bytes params used as call data
        "any_param_to_call": []               # any param used in calls
    }

    for _, call in high_level_calls:
        arguments = getattr(call, "arguments", []) or []
        for i, arg in enumerate(arguments):
            arg_name = getattr(arg, "name", None)
            if arg_name and arg_name in parameter_names:
                result["any_param_to_call"].append(arg_name)

                # Check if address parameter used as first arg (likely target)
                if i == 0 and self._is_address_type(arg):
                    result["address_params_to_call_target"].append(arg_name)

                # Check if bytes parameter (likely call data)
                if self._is_bytes_type(arg):
                    result["bytes_params_to_call_data"].append(arg_name)

    return result
```

**New Properties**:
```python
"has_address_param_as_call_target": bool(param_flow["address_params_to_call_target"]),
"has_bytes_param_as_call_data": bool(param_flow["bytes_params_to_call_data"]),
"user_controlled_call_pattern": (
    bool(param_flow["address_params_to_call_target"])
    and bool(param_flow["bytes_params_to_call_data"])
),
```

**Acceptance Criteria**:
- [ ] Truster's `flashLoan` detected as having `user_controlled_call_pattern = true`
- [ ] `target` parameter tracked as flowing to call target
- [ ] `data` parameter tracked as flowing to call data

---

### Task 2.2: Add Semantic Parameter Classification
**File**: `src/true_vkg/kg/builder.py`
**Enhancement**: Better parameter semantics

**Implementation**:
```python
def _classify_parameter_semantics(self, param_name: str, param_type: str) -> set[str]:
    """Classify parameter by its semantic role."""
    semantics = set()
    name_lower = param_name.lower()
    type_lower = param_type.lower() if param_type else ""

    # Target/recipient patterns
    if any(kw in name_lower for kw in ["target", "to", "recipient", "receiver", "dest"]):
        if "address" in type_lower:
            semantics.add("POTENTIAL_CALL_TARGET")

    # Callback patterns
    if any(kw in name_lower for kw in ["callback", "handler", "hook", "on"]):
        semantics.add("CALLBACK_HANDLER")

    # Data patterns
    if any(kw in name_lower for kw in ["data", "payload", "calldata", "params"]):
        if "bytes" in type_lower:
            semantics.add("CALL_DATA")

    # Amount patterns
    if any(kw in name_lower for kw in ["amount", "value", "qty", "quantity"]):
        if "uint" in type_lower or "int" in type_lower:
            semantics.add("VALUE_AMOUNT")

    return semantics
```

---

### Task 2.3: Detect Flash Loan Callback Patterns
**File**: `src/true_vkg/kg/builder.py`
**New Property**: `is_flashloan_like`, `has_callback_to_untrusted`

**Implementation**:
```python
def _is_flashloan_pattern(self, fn, parameter_names, param_types) -> dict:
    """Detect flash loan callback patterns."""
    result = {
        "is_flashloan_like": False,
        "has_callback_to_untrusted": False,
        "callback_target_param": None,
        "callback_data_param": None
    }

    name_lower = fn.name.lower() if fn.name else ""

    # Name-based detection
    if any(kw in name_lower for kw in ["flash", "loan", "borrow"]):
        result["is_flashloan_like"] = True

    # Pattern-based detection: has address param + bytes param + external call
    address_params = [n for n, t in zip(parameter_names, param_types) if "address" in str(t).lower()]
    bytes_params = [n for n, t in zip(parameter_names, param_types) if "bytes" in str(t).lower()]

    if address_params and bytes_params:
        high_level_calls = getattr(fn, "high_level_calls", []) or []
        for _, call in high_level_calls:
            args = getattr(call, "arguments", []) or []
            arg_names = [getattr(a, "name", None) for a in args]

            # Check if address param is call target and bytes param is call data
            for addr_param in address_params:
                if addr_param in arg_names:
                    for bytes_param in bytes_params:
                        if bytes_param in arg_names:
                            result["has_callback_to_untrusted"] = True
                            result["callback_target_param"] = addr_param
                            result["callback_data_param"] = bytes_param
                            break

    return result
```

---

## Phase 3: Missing Property Implementations

### Task 3.1: Implement `attacker_controlled_write` Properly
**File**: `src/true_vkg/kg/builder.py`
**Lines**: Check current implementation at ~4976-4982

**Issue**: Property exists but may have incomplete dataflow analysis.

**Verification**:
```bash
# Check current implementation
grep -n "attacker_controlled_write" src/true_vkg/kg/builder.py
```

**Required Analysis**:
- [ ] Verify dataflow computation is enabled
- [ ] Check if taint sources include all parameters
- [ ] Ensure state writes are correctly identified as sinks

---

### Task 3.2: Implement `state_write_after_external_call` Correctly
**File**: `src/true_vkg/kg/builder.py`

**Issue**: 31 patterns depend on this property - HIGHEST IMPACT

**Required**:
- [ ] Verify CFG traversal captures correct ordering
- [ ] Check operation detection for external calls
- [ ] Ensure state writes after calls are flagged

**Test Case**:
```solidity
// Vulnerable pattern
function withdraw(uint amount) external {
    msg.sender.call{value: amount}("");  // External call
    balances[msg.sender] -= amount;       // State write AFTER
}
```

---

### Task 3.3: Implement Cross-Function Reentrancy Detection
**File**: `src/true_vkg/kg/builder.py`
**Properties**: `cross_function_reentrancy_read`, `cross_function_reentrancy_surface`

**Issue**: Currently only analyzes single-function scope.

**Required**:
- [ ] Track state variables read in function A
- [ ] Track state variables written in function B
- [ ] If A has external call and B writes to var A reads → flag

---

## Phase 4: Pattern Validation & Testing

### Task 4.1: Create DVDeFi Test Suite
**Location**: `tests/test_dvdefi_detection.py`

**Test Cases**:
```python
import pytest
from tests.graph_cache import load_graph

class TestDVDeFiDetection:
    """Real-world vulnerability detection tests against Damn Vulnerable DeFi."""

    def test_truster_arbitrary_call(self):
        """Truster: Arbitrary external call via Address.functionCall."""
        graph = load_graph("TrusterLenderPool")  # Or path to DVDeFi

        # flashLoan should have these properties TRUE
        flashloan = self._find_function(graph, "flashLoan")
        assert flashloan["properties"]["call_target_user_controlled"] == True
        assert flashloan["properties"]["call_data_user_controlled"] == True
        assert flashloan["properties"]["has_callback_to_untrusted"] == True

    def test_unstoppable_strict_equality(self):
        """Unstoppable: DoS via strict equality check."""
        graph = load_graph("UnstoppableLender")

        flashloan = self._find_function(graph, "flashLoan")
        assert flashloan["properties"]["has_strict_equality_check"] == True

    def test_side_entrance_accounting_bypass(self):
        """Side-Entrance: Flash loan accounting bypass."""
        graph = load_graph("SideEntranceLenderPool")

        # flashLoan doesn't prevent reentrancy via deposit
        flashloan = self._find_function(graph, "flashLoan")
        deposit = self._find_function(graph, "deposit")

        # Cross-function: flashLoan reads balance, deposit writes balance
        assert flashloan["properties"]["cross_function_reentrancy_read"] == True
        assert deposit["properties"]["cross_function_reentrancy_surface"] == True

    def test_naive_receiver_unprotected_loan(self):
        """Naive-Receiver: Flash loan without borrower authorization."""
        graph = load_graph("NaiveReceiverLenderPool")

        flashloan = self._find_function(graph, "flashLoan")
        # receiver parameter is user-controlled, no borrower auth
        assert flashloan["properties"]["call_target_user_controlled"] == True

    def test_free_rider_payment_logic(self):
        """Free-Rider: Payment logic bug in NFT marketplace."""
        graph = load_graph("FreeRiderNFTMarketplace")

        buymany = self._find_function(graph, "buyMany")
        # ETH sent before ownership transfer
        assert buymany["properties"]["value_transfer_before_state_update"] == True
```

---

### Task 4.2: Create Pattern Precision/Recall Benchmarks
**Location**: `benchmarks/pattern_metrics.py`

**Structure**:
```python
BENCHMARK_CONTRACTS = {
    "arbitrary-call": {
        "true_positives": ["TrusterLenderPool.flashLoan", "AuthorizedExecutor.execute"],
        "true_negatives": ["SafeExecutor.execute"],  # with proper validation
        "expected_pattern": "attacker-controlled-write"
    },
    "strict-equality-dos": {
        "true_positives": ["UnstoppableLender.flashLoan"],
        "true_negatives": ["SafeVault.flashLoan"],  # uses >= instead
        "expected_pattern": "dos-strict-equality"
    },
    # ... more benchmarks
}
```

---

### Task 4.3: Create Property Derivation Tests
**Location**: `tests/test_property_derivation.py`

**Purpose**: Unit tests for each property derivation method.

```python
class TestPropertyDerivation:
    def test_call_target_user_controlled_high_level(self):
        """Test detection of user-controlled high-level call targets."""
        code = """
        function execute(address target, bytes calldata data) external {
            target.functionCall(data);
        }
        """
        graph = build_graph_from_source(code)
        fn = graph.functions["execute"]
        assert fn.properties["call_target_user_controlled"] == True

    def test_strict_equality_if_statement(self):
        """Test detection of strict equality in if statements."""
        code = """
        function check() external {
            if (totalSupply != expectedBalance) revert();
        }
        """
        graph = build_graph_from_source(code)
        fn = graph.functions["check"]
        assert fn.properties["has_strict_equality_check"] == True

    def test_library_call_destination(self):
        """Test destination extraction for library calls."""
        code = """
        import "@openzeppelin/contracts/utils/Address.sol";
        function exec(address target, bytes calldata data) external {
            Address.functionCall(target, data);
        }
        """
        graph = build_graph_from_source(code)
        fn = graph.functions["exec"]
        assert fn.properties["call_target_user_controlled"] == True
```

---

## Phase 5: Debugging & Observability

### Task 5.1: Add Property Derivation Debug Mode
**File**: `src/true_vkg/kg/builder.py`

**Implementation**:
```python
class VKGBuilder:
    def __init__(self, ..., debug_properties=False):
        self.debug_properties = debug_properties

    def _log_property_derivation(self, fn_name: str, prop_name: str, value: Any, reason: str):
        if self.debug_properties:
            print(f"[DEBUG] {fn_name}.{prop_name} = {value} ({reason})")
```

**Usage**:
```bash
uv run alphaswarm build-kg path/to/contracts --debug-properties
```

---

### Task 5.2: Add None Destination Logging
**File**: `src/true_vkg/kg/builder.py`

**Implementation**:
```python
def _callsite_destination(self, call: Any) -> str | None:
    destination = getattr(call, "destination", None)
    if destination is None:
        self._log_warning(f"Call {call} has None destination - may miss user-controlled detection")
        # Try fallback extraction
        return self._try_destination_fallback(call)
    ...
```

---

### Task 5.3: Create Property Coverage Report
**File**: `scripts/property_coverage.py`

**Purpose**: Report which properties are used by patterns but return False/None.

```bash
uv run python scripts/property_coverage.py path/to/graph.json
# Output:
# Property Coverage Report
# ========================
# call_target_user_controlled: 0/15 functions (ISSUE: always False)
# has_strict_equality_check: 0/15 functions (ISSUE: always False)
# state_write_after_external_call: 3/15 functions (OK)
```

---

## Phase 6: Pattern Improvements

### Task 6.1: Update `attacker-controlled-write` Pattern
**File**: `patterns/core/attacker-controlled-write.yaml`

**Current Issue**: May rely on properties that aren't derived correctly.

**Updated Pattern**:
```yaml
id: attacker-controlled-write-v2
name: Attacker-Controlled External Call (Comprehensive)
severity: critical
description: |
  Function allows attacker to control external call target and/or data.
  This enables arbitrary code execution including draining funds.
match:
  any:
    # Method 1: Direct property check
    - all:
        - property: call_target_user_controlled
          op: eq
          value: true
    # Method 2: Address parameter flows to call
    - all:
        - property: has_address_param_as_call_target
          op: eq
          value: true
    # Method 3: Flashloan callback pattern
    - all:
        - property: has_callback_to_untrusted
          op: eq
          value: true
  none:
    - property: has_access_gate
      value: true
    - property: has_reentrancy_guard
      value: true
```

---

### Task 6.2: Update `dos-strict-equality` Pattern
**File**: `patterns/core/dos-strict-equality.yaml`

**Updated Pattern**:
```yaml
id: dos-strict-equality-v2
name: DoS via Strict Equality Check (Comprehensive)
severity: medium
description: |
  Function uses strict equality (== or !=) on balance, supply, or shares.
  Can be manipulated via selfdestruct or direct transfers to cause permanent DoS.
match:
  all:
    - property: has_strict_equality_check
      op: eq
      value: true
    - property: visibility
      op: in
      value: [public, external]
  none:
    # Exclude if using safe inequality checks
    - property: uses_safe_balance_check
      value: true
```

---

## Phase 7: Real-World Validation Framework

### Task 7.1: Create Audit Report Comparison Framework
**Location**: `benchmarks/audit_comparison/`

**Purpose**: Compare BSKG findings against known audit reports.

**Structure**:
```
benchmarks/audit_comparison/
├── audits/
│   ├── cream-finance-2021.json    # Known findings from audit
│   ├── beanstalk-2022.json
│   └── euler-2023.json
├── compare_findings.py            # Comparison script
└── metrics.py                     # Precision/Recall calculation
```

---

### Task 7.2: Create Exploit Database Integration
**Location**: `src/true_vkg/validation/exploit_db.py`

**Purpose**: Match BSKG findings against known exploits.

```python
KNOWN_EXPLOITS = {
    "reentrancy": [
        {"name": "DAO Hack", "pattern": "state_write_after_external_call", "loss": "$60M"},
        {"name": "Cream Finance", "pattern": "cross_function_reentrancy", "loss": "$130M"},
    ],
    "arbitrary-call": [
        {"name": "Ronin Bridge", "pattern": "attacker_controlled_write", "loss": "$600M"},
    ],
    # ...
}

def validate_against_exploits(graph) -> list[dict]:
    """Check if known exploit patterns are detected."""
    detected = []
    for category, exploits in KNOWN_EXPLOITS.items():
        for exploit in exploits:
            if pattern_matches(graph, exploit["pattern"]):
                detected.append(exploit)
    return detected
```

---

### Task 7.3: Implement Continuous Validation
**Location**: `scripts/validate_detection.py`

**Purpose**: Run on every PR to ensure detection doesn't regress.

```bash
#!/bin/bash
# CI script for detection validation

echo "Running detection validation..."

# Build graphs for all test contracts
for contract in tests/contracts/*.sol; do
    uv run alphaswarm build-kg "$contract"
done

# Run detection tests
uv run pytest tests/test_dvdefi_detection.py -v

# Check precision/recall metrics
uv run python benchmarks/pattern_metrics.py

# Fail if metrics drop below threshold
if [ $? -ne 0 ]; then
    echo "Detection metrics below threshold!"
    exit 1
fi
```

---

## Phase 8: Documentation & Maintenance

### Task 8.1: Document Property Derivation Logic
**Location**: `docs/reference/property-derivation.md`

**Content**: For each property, document:
1. How it's derived
2. What Slither data it uses
3. Known limitations
4. Test coverage

---

### Task 8.2: Create Pattern Development Guide
**Location**: `docs/guides/pattern-development.md`

**Content**:
1. How to check if a property exists
2. How to verify property derivation
3. Testing workflow for new patterns
4. Real-world validation requirements

---

### Task 8.3: Establish Pattern Quality Gates
**Location**: `.github/workflows/pattern-quality.yml`

**Quality Gates**:
- Precision >= 70%
- Recall >= 50%
- At least 3 test cases per pattern
- Real-world validation against DVDeFi

---

## Execution Priority

### Week 1: Critical Fixes
1. [ ] Task 1.1: Fix `call_target_user_controlled`
2. [ ] Task 1.2: Add `call_data_user_controlled` for high-level
3. [ ] Task 1.3: Fix `has_strict_equality_check`
4. [ ] Task 1.4: Fix `_callsite_destination` for libraries

### Week 2: Taint Analysis
5. [ ] Task 2.1: Parameter-to-call flow tracking
6. [ ] Task 2.2: Semantic parameter classification
7. [ ] Task 2.3: Flashloan callback pattern detection

### Week 3: Testing Infrastructure
8. [ ] Task 4.1: DVDeFi test suite
9. [ ] Task 4.2: Precision/recall benchmarks
10. [ ] Task 4.3: Property derivation tests

### Week 4: Validation & Polish
11. [ ] Task 5.1: Debug mode
12. [ ] Task 5.3: Coverage report
13. [ ] Task 6.1-6.2: Pattern updates
14. [ ] Task 7.1-7.3: Real-world validation

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| DVDeFi Detection Rate | 0/5 (0%) | 5/5 (100%) |
| Pattern Precision | Unknown | >= 70% |
| Pattern Recall | Unknown | >= 50% |
| Property Derivation Accuracy | ~40% | >= 90% |
| Test Coverage | Unknown | >= 80% |

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/true_vkg/kg/builder.py` | Critical property derivation fixes |
| `patterns/core/*.yaml` | Pattern updates |
| `tests/test_dvdefi_detection.py` | New test suite |
| `tests/test_property_derivation.py` | Property unit tests |
| `benchmarks/pattern_metrics.py` | Precision/recall framework |
| `scripts/property_coverage.py` | Property coverage tool |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing tests | Medium | High | Run full test suite before each fix |
| False positive increase | Medium | Medium | Track precision metrics continuously |
| Slither API changes | Low | High | Pin Slither version, add version checks |
| Performance regression | Low | Medium | Benchmark before/after |

---

## Conclusion

The BSKG patterns are well-designed but **useless without correct property derivation**. The 4 critical bugs identified explain the 0% detection rate against real-world vulnerabilities.

**Priority Fix**: Tasks 1.1-1.4 will immediately enable detection of:
- Arbitrary external calls (Truster, Naive-Receiver)
- Strict equality DoS (Unstoppable)
- Flash loan callback attacks

After these fixes, BSKG should detect **at least 4/5 DVDeFi challenges** we tested.
