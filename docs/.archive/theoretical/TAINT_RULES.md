# Taint Propagation Rules and Aliasing Strategy

This document defines the canonical taint propagation rules for AlphaSwarm.sol's dataflow analysis.
It serves as the single source of truth for taint semantics implemented in `src/alphaswarm_sol/kg/taint.py`.

**Version:** 1.0
**Status:** Canonical

---

## Taint Sources

Taint sources are ranked by risk level. Higher risk sources require stricter handling.

| Source Type | Risk Level | Enum Value | Example | Notes |
|-------------|------------|------------|---------|-------|
| Call-target control | CRITICAL | `CALL_TARGET_CONTROL` | `user_addr.call()` | User controls call destination |
| External return | HIGH | `EXTERNAL_RETURN` | `oracle.getPrice()` | Untrusted external data |
| User input | HIGH | `USER_INPUT` | `function f(uint x)` | Direct parameter taint |
| Oracle | HIGH | `ORACLE` | `chainlink.latestAnswer()` | External price feeds |
| Environment | MEDIUM | `ENVIRONMENT` | `msg.sender`, `msg.value` | Context-dependent risk |
| Storage aliased | LOW | `STORAGE_ALIASED` | `balances[user]` | Only if storage was tainted |

### Source Detection Rules

1. **USER_INPUT**: All function parameters in `public`/`external` functions
2. **ENVIRONMENT**: `msg.sender`, `msg.value`, `msg.data`, `tx.origin`, `block.*`
3. **EXTERNAL_RETURN**: Return value from any external contract call
4. **CALL_TARGET_CONTROL**: Address operand in `.call()`, `.delegatecall()`, `.staticcall()`
5. **ORACLE**: Known oracle interfaces (Chainlink, Uniswap TWAP, etc.)
6. **STORAGE_ALIASED**: Storage read from slot previously written with tainted value

---

## Aliasing Strategy

**DESIGN CHOICE: Direct-then-Aliased Propagation**

This implementation uses a two-tier taint propagation model:

### Tier 1: Direct Taint (Default)

Direct taint tracks immediate use of tainted values. External return values taint
IMMEDIATE uses only by default.

```solidity
// Direct taint example
uint price = oracle.getPrice();  // price is tainted (EXTERNAL_RETURN)
use(price);                      // use() receives tainted value
// price taint does NOT automatically propagate through storage
```

**Direct taint properties:**
- Source: Original taint source (EXTERNAL_RETURN, USER_INPUT, etc.)
- Confidence: 1.0 (full confidence)
- Scope: Current function execution only

### Tier 2: Aliased Taint (Explicit Tracking)

Aliased taint propagates taint through storage writes and subsequent reads.

```solidity
// Aliased taint example
uint price = oracle.getPrice();  // price is tainted (EXTERNAL_RETURN)
cachedPrice = price;             // cachedPrice (storage) now tainted (STORAGE_ALIASED)
// Later...
uint p = cachedPrice;            // p is tainted via storage alias
```

**Aliased taint properties:**
- Source: STORAGE_ALIASED (original source recorded in path)
- Confidence: 0.7 (reduced due to storage indirection)
- Scope: Persists across function calls

### Storage Aliasing Rules

| Operation | Taint Propagation | Confidence |
|-----------|-------------------|------------|
| `storage = tainted_local` | Storage slot marked tainted | 0.7 |
| `local = tainted_storage` | Local inherits storage taint | 0.7 |
| `storage[key] = tainted` | Slot at `key` marked tainted | 0.7 |
| `tainted_storage[key]` | Result inherits storage taint | 0.7 * key_taint |

### Delegatecall Propagation

Delegatecall to external contracts creates **unavailable** taint analysis:

```solidity
target.delegatecall(data);  // ALL storage potentially tainted
// availability = false
// reason = "delegatecall to external contract - storage effects unknown"
```

**Delegatecall rules:**
- Mark ALL subsequent storage reads as potentially tainted
- Set `availability.available = false`
- Set `availability.confidence = 0.0`
- Reason: Cannot track external contract's storage modifications

---

## Taint Sinks

Sinks are operations where tainted data creates security risk.

| Sink Type | Severity | Enum Value | Pattern | Risk |
|-----------|----------|------------|---------|------|
| Call target | CRITICAL | `CALL_TARGET` | `TAINTED_ADDR.call()` | Arbitrary call destination |
| External call value | CRITICAL | `EXTERNAL_CALL_VALUE` | `.call{value: TAINTED}()` | Value theft |
| Storage write | HIGH | `STORAGE_WRITE` | `balances[x] = TAINTED` | State corruption |
| Arithmetic | MEDIUM | `ARITHMETIC` | `a + TAINTED` | Overflow/underflow |
| Comparison | LOW | `COMPARISON` | `if (TAINTED > x)` | Logic manipulation |

### Sink Severity Matrix

| Source \ Sink | CALL_TARGET | EXTERNAL_CALL_VALUE | STORAGE_WRITE | ARITHMETIC | COMPARISON |
|---------------|-------------|---------------------|---------------|------------|------------|
| CALL_TARGET_CONTROL | CRITICAL | CRITICAL | HIGH | HIGH | MEDIUM |
| EXTERNAL_RETURN | CRITICAL | CRITICAL | HIGH | MEDIUM | LOW |
| USER_INPUT | CRITICAL | HIGH | HIGH | MEDIUM | LOW |
| ORACLE | HIGH | HIGH | MEDIUM | MEDIUM | LOW |
| ENVIRONMENT | HIGH | MEDIUM | MEDIUM | LOW | LOW |
| STORAGE_ALIASED | HIGH | HIGH | MEDIUM | LOW | LOW |

---

## Sanitizers

Sanitizers reduce or eliminate taint when applied.

| Sanitizer | Effect | Enum Value | Example | Removes Taint? |
|-----------|--------|------------|---------|----------------|
| Bounds check | Removes overflow risk | `BOUNDS_CHECK` | `require(x < MAX)` | Partial (ARITHMETIC only) |
| Ownership check | Context validation | `OWNERSHIP_CHECK` | `require(msg.sender == owner)` | No (validates context) |
| SafeMath | Arithmetic protection | `SAFE_MATH` | `x.add(y)` | Partial (ARITHMETIC only) |
| Type cast | Type narrowing | `TYPE_CAST` | `uint8(x)` | Partial (bounds implicit) |
| Whitelist check | Address validation | `WHITELIST_CHECK` | `require(allowed[addr])` | Yes (for CALL_TARGET) |
| Zero check | Null validation | `ZERO_CHECK` | `require(addr != address(0))` | No (weak sanitizer) |

### Sanitizer Application Rules

1. **Bounds check before arithmetic**: Removes ARITHMETIC sink risk
2. **Whitelist before call**: Removes CALL_TARGET sink risk
3. **SafeMath wrapping**: Removes ARITHMETIC sink risk for that operation
4. **Ownership check**: Does NOT remove taint, validates context only
5. **Zero check**: Weak sanitizer, does NOT remove significant taint

### Sanitizer Recording

Applied sanitizers are recorded in `TaintResult.sanitizers_applied`:

```python
TaintResult(
    is_tainted=True,
    sources=[TaintSource.USER_INPUT],
    sanitizers_applied=["BOUNDS_CHECK"],  # require(x < MAX) applied
    availability=TaintAvailability(available=True, confidence=1.0)
)
```

---

## Availability Flags

Availability flags indicate confidence in taint analysis results.

| Condition | available | confidence | Reason |
|-----------|-----------|------------|--------|
| Direct taint, full CFG | `true` | 1.0 | Complete analysis path |
| Aliased taint, tracked storage | `true` | 0.7 | Storage indirection uncertainty |
| External call in path | `true` | 0.5 | External effects unknown |
| Delegatecall present | `false` | 0.0 | Cannot track external storage |
| Inline assembly | `false` | 0.0 | Opaque to static analysis |
| Loop with dynamic bound | `true` | 0.6 | Iteration-dependent taint |
| Recursive call | `true` | 0.5 | Recursion depth unknown |
| Try/catch with external | `true` | 0.4 | Exception path uncertainty |

### Availability Calibration

**Confidence thresholds for decisions:**

| Confidence | Interpretation | Action |
|------------|----------------|--------|
| >= 0.9 | High confidence | Use result directly |
| 0.7-0.89 | Medium confidence | Use with caution flag |
| 0.5-0.69 | Low confidence | Require manual review |
| < 0.5 | Insufficient | Treat as UNKNOWN |

**available=false semantics:**

When `availability.available = false`, the taint result is **UNKNOWN**, not safe:

```python
# WRONG interpretation
if not result.is_tainted:
    assume_safe()  # DANGEROUS - may be unavailable, not safe

# CORRECT interpretation
if result.is_unknown:
    treat_as_potentially_tainted()  # Conservative
elif not result.is_tainted:
    assume_safe()  # Only safe if analysis available
```

---

## Propagation Rules Summary

### Intra-procedural Propagation

1. **Assignment**: `y = tainted_x` propagates taint to `y`
2. **Arithmetic**: `y = tainted_x + z` propagates taint to `y`
3. **Array index**: `arr[tainted_idx]` result is tainted
4. **Struct field**: `s.field = tainted` taints `s.field`
5. **Return**: `return tainted` propagates taint to caller

### Inter-procedural Propagation

1. **Internal call**: Taint propagates through arguments and returns
2. **External call return**: Return value is EXTERNAL_RETURN tainted
3. **Delegatecall**: Storage becomes unavailable
4. **Library call**: Treat as internal call (same storage context)

### Special Cases

1. **`abi.encode(tainted)`**: Result is tainted
2. **`keccak256(tainted)`**: Result is tainted (hash of tainted data)
3. **`address(tainted_uint)`**: Result is tainted (arbitrary address)
4. **Comparison result**: `tainted == x` result is tainted (can leak info)

---

## Implementation Reference

These rules are implemented in:
- `src/alphaswarm_sol/kg/taint.py` - Core taint engine
- `src/alphaswarm_sol/kg/rich_edge.py` - TaintSource enum integration

For LLM agent usage, see: `docs/reference/taint.md`
