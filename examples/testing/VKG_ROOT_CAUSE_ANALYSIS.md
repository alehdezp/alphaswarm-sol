# BSKG Detection Failures: Root Cause Analysis

## Summary

After code review of `builder.py`, I've identified **4 critical bugs** that explain why BSKG fails to detect DVDeFi vulnerabilities.

---

## Bug #1: `call_target_user_controlled` Only Checks LOW-LEVEL Calls

### Location
`builder.py:1446` and `builder.py:2020-2066`

### The Problem

```python
# Line 1446 - Node property assignment
"call_target_user_controlled": low_level_summary["call_target_user_controlled"],
```

The `low_level_summary` is built from:
```python
# Line 2030
for call in low_level_calls:  # <-- ONLY low-level calls!
    destination = self._callsite_destination(call)
    if destination and self._is_user_controlled_destination(destination, parameter_names):
        call_target_user_controlled = True
```

### Why Truster Fails

Truster uses:
```solidity
target.functionCall(data);  // OpenZeppelin Address.functionCall - HIGH LEVEL call
```

This is NOT a low-level call (like `.call()`), it's a high-level call. So `low_level_calls` is empty!

### The Irony

VKG DOES compute `external_call_target_user_controlled` for high-level calls:
```python
# Line 926
external_call_target_user_controlled = self._external_call_target_user_controlled(
    external_calls, high_level_calls, parameter_names
)
```

But this value is **NEVER exposed as a node property**! It's only used internally for `has_untrusted_external_call`.

### Fix Required

```python
# Change line 1446 from:
"call_target_user_controlled": low_level_summary["call_target_user_controlled"],

# To:
"call_target_user_controlled": (
    low_level_summary["call_target_user_controlled"]
    or external_call_target_user_controlled  # <-- ADD THIS
),
```

---

## Bug #2: No High-Level Call DATA Analysis

### Location
`builder.py:2068-2092`

### The Problem

For LOW-LEVEL calls, we check both target AND data:
```python
# Line 2042-2051
destination = self._callsite_destination(call)
if destination and self._is_user_controlled_destination(destination, parameter_names):
    call_target_user_controlled = True

call_data = self._callsite_data_expression(call)
if call_data and self._is_user_controlled_expression(call_data, parameter_names):
    call_data_user_controlled = True  # <-- EXISTS for low-level
```

For HIGH-LEVEL calls, we ONLY check target:
```python
# Line 2083-2091
for _, call in high_level_calls:
    destination = self._callsite_destination(call)
    if destination and self._is_user_controlled_destination(...):
        return True
    # NO call_data check here!
```

### Why Truster Fails

The `data` parameter in `target.functionCall(data)` is 100% user controlled, but BSKG doesn't check it for high-level calls.

### Fix Required

Add a new function:
```python
def _external_call_data_user_controlled(
    self, external_calls, high_level_calls, parameter_names
) -> bool:
    for _, call in high_level_calls:
        # Extract call arguments and check if any are user-controlled
        arguments = getattr(call, "arguments", []) or []
        for arg in arguments:
            if self._is_user_controlled_expression(arg, parameter_names):
                return True
    return False
```

And expose it as a property:
```python
"call_data_user_controlled": (
    low_level_summary["call_data_user_controlled"]
    or external_call_data_user_controlled  # <-- ADD THIS
),
```

---

## Bug #3: `has_strict_equality_check` Is Too Narrow

### Location
`builder.py:4853-4862`

### The Problem

```python
def _has_strict_equality_check(self, require_exprs: list[str]) -> bool:
    """Detect strict equality checks on balance."""
    for expr in require_exprs:  # <-- ONLY checks require expressions!
        lowered = expr.lower()
        # Look for address(this).balance with == operator
        has_balance = "balance" in lowered and ("this" in lowered or "address(this)" in lowered)
        has_strict_eq = " == " in expr  # <-- ONLY checks ==, not !=
        if has_balance and has_strict_eq:
            return True
    return False
```

### Why Unstoppable Fails

Unstoppable uses:
```solidity
if (convertToShares(totalSupply) != balanceBefore) revert InvalidBalance();
```

Problems:
1. It's an `if` statement, not a `require` - not in `require_exprs`
2. It uses `!=` not `==` - not matched
3. It compares `totalSupply` with `balanceBefore`, not `address(this).balance` - not matched

### Fix Required

```python
def _has_strict_equality_check(self, fn) -> bool:
    """Detect strict equality checks that could break invariants."""
    source = self._source_slice(...)

    # Check for any strict comparison (== or !=) on balances/shares/supplies
    patterns = [
        r'(balance|supply|shares|total)\w*\s*(==|!=)\s*\w+',
        r'\w+\s*(==|!=)\s*\w*(balance|supply|shares|total)',
    ]
    for pattern in patterns:
        if re.search(pattern, source, re.IGNORECASE):
            return True
    return False
```

---

## Bug #4: `_callsite_destination` Doesn't Work for All High-Level Call Types

### Location
`builder.py:5276-5283`

### The Problem

```python
def _callsite_destination(self, call: Any) -> str | None:
    destination = getattr(call, "destination", None)
    if destination is None:
        return None
    name = getattr(destination, "name", None)
    if name:
        return str(name)
    return str(destination)
```

For Slither's high-level calls, the structure is `(contract, HighLevelCall)` tuple. The `call` part may not have a `destination` attribute that points to the actual call target when using library functions like `Address.functionCall`.

### Why Truster Fails

`target.functionCall(data)` is:
- Target: The `target` parameter (user controlled)
- But `_callsite_destination` may return the Address library contract, not `target`

### Fix Required

Need to inspect the IR (intermediate representation) to find the actual call destination:
```python
def _callsite_destination(self, call: Any) -> str | None:
    # Try standard destination
    destination = getattr(call, "destination", None)
    if destination is not None:
        name = getattr(destination, "name", None)
        if name:
            return str(name)

    # For library calls like Address.functionCall(target, data)
    # The first argument is the actual target
    arguments = getattr(call, "arguments", []) or []
    if arguments:
        first_arg = arguments[0]
        name = getattr(first_arg, "name", None)
        if name:
            return str(name)

    return str(destination) if destination else None
```

---

## Impact Summary

| Bug | Property Affected | DVDeFi Challenge | Impact |
|-----|-------------------|------------------|--------|
| #1 | `call_target_user_controlled` | Truster | CRITICAL - Misses arbitrary call |
| #2 | `call_data_user_controlled` | Truster | CRITICAL - Misses arbitrary data |
| #3 | `has_strict_equality_check` | Unstoppable | HIGH - Misses DoS vuln |
| #4 | Target extraction | All high-level | HIGH - Wrong target analysis |

---

## Verification Test

After fixing, these queries should work:

```bash
# Truster - should find flashLoan
uv run alphaswarm query "FIND functions WHERE call_target_user_controlled = true" \
  --graph examples/damm-vuln-defi/src/truster/.true_vkg/graphs/graph.json

# Expected: flashLoan(uint256,address,address,bytes)

# Unstoppable - should find flashLoan
uv run alphaswarm query "FIND functions WHERE has_strict_equality_check = true" \
  --graph examples/damm-vuln-defi/src/unstoppable/.true_vkg/graphs/graph.json

# Expected: flashLoan(...)
```

---

## Priority Order for Fixes

1. **Bug #1 + #2** (Truster): Quick fix - just add `or external_call_*` to property assignments
2. **Bug #4** (Target extraction): Medium - needs careful IR analysis
3. **Bug #3** (Strict equality): Rewrite to be more comprehensive

---

## Files to Modify

All fixes are in: `src/true_vkg/kg/builder.py`

Key line numbers:
- Line 1446: `call_target_user_controlled` property
- Line 1448: `call_data_user_controlled` property
- Line 2068-2092: `_external_call_target_user_controlled`
- Line 4853-4862: `_has_strict_equality_check`
- Line 5276-5283: `_callsite_destination`
