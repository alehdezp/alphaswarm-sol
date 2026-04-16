# Taint Model Reference

This document describes AlphaSwarm.sol's taint analysis model for LLM agents.

For canonical propagation rules, see: [TAINT_RULES.md](./TAINT_RULES.md)

---

## Overview

Taint analysis tracks attacker-controlled data through smart contracts to identify
where it reaches security-sensitive operations (sinks).

**Key principle:** Missing taint data yields **unknown**, not **safe**.

```python
# WRONG - treats unknown as safe
if not result.is_tainted:
    assume_safe()

# CORRECT - checks availability
if result.is_unknown:
    treat_as_potentially_tainted()
elif result.is_safe:
    assume_safe()
```

---

## Taint Sources

Sources are origins of potentially attacker-controlled data.

| Source | Risk | Description |
|--------|------|-------------|
| `CALL_TARGET_CONTROL` | CRITICAL | User controls call destination |
| `EXTERNAL_RETURN` | HIGH | Return from external contract call |
| `USER_INPUT` | HIGH | Function parameters |
| `ORACLE` | HIGH | Price feeds (Chainlink, etc.) |
| `ENVIRONMENT` | MEDIUM | `msg.sender`, `msg.value`, `block.*` |
| `STORAGE_ALIASED` | LOW | Read from previously tainted storage |

### Example Usage

```python
from alphaswarm_sol.kg.taint import TaintSource, TAINT_SOURCE_RISK

# Check if high risk
if TAINT_SOURCE_RISK[TaintSource.EXTERNAL_RETURN] == "HIGH":
    print("External return is high risk")
```

---

## Taint Sinks

Sinks are operations where tainted data creates security risk.

| Sink | Severity | Pattern |
|------|----------|---------|
| `CALL_TARGET` | CRITICAL | `TAINTED_ADDR.call()` |
| `EXTERNAL_CALL_VALUE` | CRITICAL | `.call{value: TAINTED}()` |
| `STORAGE_WRITE` | HIGH | `balances[x] = TAINTED` |
| `ARITHMETIC` | MEDIUM | `a + TAINTED` |
| `COMPARISON` | LOW | `if (TAINTED > x)` |

---

## Taint Sanitizers

Sanitizers reduce or eliminate taint risk.

| Sanitizer | Effect | Example |
|-----------|--------|---------|
| `BOUNDS_CHECK` | Removes ARITHMETIC risk | `require(x < MAX)` |
| `WHITELIST_CHECK` | Removes CALL_TARGET risk | `require(allowed[addr])` |
| `SAFE_MATH` | Removes ARITHMETIC risk | `x.add(y)` |
| `OWNERSHIP_CHECK` | Context validation only | `require(msg.sender == owner)` |

**Important:** Sanitizers are sink-specific. A `BOUNDS_CHECK` does not sanitize `CALL_TARGET`.

---

## TaintAvailability

Availability indicates confidence in taint analysis results.

```python
@dataclass
class TaintAvailability:
    available: bool       # Is analysis available?
    confidence: float     # 0.0-1.0
    reason: Optional[str] # Explanation
```

### Confidence Interpretation

| Confidence | Meaning | Action |
|------------|---------|--------|
| >= 0.9 | High | Use result directly |
| 0.7-0.89 | Medium | Use with caution flag |
| 0.5-0.69 | Low | Require manual review |
| < 0.5 | Insufficient | Treat as UNKNOWN |

### Common Availability States

| State | available | confidence | Trigger |
|-------|-----------|------------|---------|
| Full | `true` | 1.0 | Direct taint, full CFG |
| Aliased | `true` | 0.7 | Storage indirection |
| External | `true` | 0.5 | External call in path |
| Delegatecall | `false` | 0.0 | Delegatecall present |
| Assembly | `false` | 0.0 | Inline assembly |

### Using Availability

```python
# Factory methods for common states
avail = TaintAvailability.full()       # (True, 1.0)
avail = TaintAvailability.aliased()    # (True, 0.7)
avail = TaintAvailability.delegatecall()  # (False, 0.0)

# Check confidence level
if avail.is_high_confidence():
    # >= 0.9, use directly
    pass
elif avail.is_insufficient():
    # < 0.5 or unavailable, treat as unknown
    pass
```

---

## TaintResult

Complete taint analysis result.

```python
@dataclass
class TaintResult:
    is_tainted: bool
    sources: list[TaintSource]
    path: list[str]
    availability: TaintAvailability
    sanitizers_applied: list[TaintSanitizer]
    sink: Optional[TaintSink]
```

### Key Properties

```python
result = TaintResult.tainted([TaintSource.USER_INPUT], ["x -> y"])

# Check if unknown (unavailable)
if result.is_unknown:
    # DO NOT treat as safe
    handle_unknown()

# Check if truly safe
if result.is_safe:
    # Available AND not tainted
    proceed_safely()

# Get highest risk level
risk = result.risk_level  # "CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE"
```

### Factory Methods

```python
# Create safe result
result = TaintResult.safe()

# Create unknown result
result = TaintResult.unknown("delegatecall present")

# Create tainted result
result = TaintResult.tainted(
    sources=[TaintSource.EXTERNAL_RETURN],
    path=["oracle.getPrice() -> price"],
    availability=TaintAvailability.full(),
)
```

---

## TaintAnalyzer

Analyzer class for function-level taint analysis.

```python
from alphaswarm_sol.kg.taint import TaintAnalyzer

# Initialize for a contract
analyzer = TaintAnalyzer(contract)

# Analyze all variables in a function
results = analyzer.analyze_function(fn)
for var_name, result in results.items():
    if result.is_unknown:
        print(f"{var_name}: UNKNOWN - {result.availability.reason}")
    elif result.is_tainted:
        print(f"{var_name}: TAINTED via {result.sources}")

# Analyze specific variable
result = analyzer.analyze_variable(fn, var, sink=TaintSink.STORAGE_WRITE)

# Track storage taint across functions
analyzer.mark_storage_tainted("cachedPrice", [TaintSource.ORACLE])
storage_taint = analyzer.get_storage_taint()
```

---

## Aliasing Strategy

AlphaSwarm uses **Direct-then-Aliased** propagation:

### Direct Taint (Tier 1)
- Immediate uses of tainted values
- Confidence: 1.0
- Scope: Current function

```solidity
uint price = oracle.getPrice();  // price is tainted
use(price);  // use() receives tainted value
```

### Aliased Taint (Tier 2)
- Taint propagates through storage
- Confidence: 0.7 (reduced)
- Scope: Persists across calls

```solidity
cachedPrice = oracle.getPrice();  // storage tainted
// Later...
uint p = cachedPrice;  // p is tainted via alias
```

### Delegatecall
- Makes ALL storage potentially tainted
- Availability: `false` (cannot track)

---

## Integration with Graph Interface

Taint results integrate with the Graph Interface Contract v2:

```yaml
findings:
  - id: reentrancy-classic
    clause_matrix:
      - clause: "tainted_value_reaches_sink"
        status: matched  # or unknown if unavailable
        evidence_refs:
          - { source: "USER_INPUT", sink: "EXTERNAL_CALL_VALUE" }
    taint:
      available: true
      confidence: 0.85
      sources: ["user_input"]
      sanitizers: []
```

When `taint.available = false`, the clause status should be `unknown`, not `failed`.

---

## Best Practices for LLM Agents

1. **Always check availability first**
   ```python
   if result.is_unknown:
       # Cannot make safety claims
       report_as_needs_review()
   ```

2. **Use `is_safe` property, not `not is_tainted`**
   ```python
   # WRONG
   if not result.is_tainted:
       claim_safe()

   # CORRECT
   if result.is_safe:  # Checks availability too
       claim_safe()
   ```

3. **Report confidence with findings**
   ```
   Finding: Tainted user input reaches storage write
   Confidence: 0.7 (storage aliasing)
   ```

4. **Treat delegatecall as unknown**
   - If a function contains delegatecall, do not claim safety
   - Report as "requires manual review"

5. **Consider sanitizers in context**
   - `BOUNDS_CHECK` only sanitizes `ARITHMETIC` sinks
   - Cross-check sanitizer vs sink type

---

## API Reference

### Enums

| Enum | Values |
|------|--------|
| `TaintSource` | `CALL_TARGET_CONTROL`, `EXTERNAL_RETURN`, `USER_INPUT`, `ORACLE`, `ENVIRONMENT`, `STORAGE_ALIASED` |
| `TaintSink` | `CALL_TARGET`, `EXTERNAL_CALL_VALUE`, `STORAGE_WRITE`, `ARITHMETIC`, `COMPARISON` |
| `TaintSanitizer` | `BOUNDS_CHECK`, `OWNERSHIP_CHECK`, `SAFE_MATH`, `TYPE_CAST`, `WHITELIST_CHECK`, `ZERO_CHECK` |

### Constants

| Constant | Type | Description |
|----------|------|-------------|
| `TAINT_SOURCE_RISK` | `dict[TaintSource, str]` | Risk level for each source |
| `TAINT_SINK_SEVERITY` | `dict[TaintSink, str]` | Severity for each sink |
| `SANITIZER_AFFECTS` | `dict[TaintSanitizer, list[TaintSink]]` | Which sinks each sanitizer affects |

### Functions

| Function | Description |
|----------|-------------|
| `extract_inputs(fn)` | Extract parameter sources |
| `extract_special_sources(fn)` | Extract environment sources |
| `extract_external_return_sources(fn)` | Extract external call returns |
| `extract_oracle_sources(fn)` | Extract oracle data sources |
| `compute_dataflow(contract, inputs, state_vars)` | Legacy dataflow API |

---

*Reference: src/alphaswarm_sol/kg/taint.py*
*Rules: docs/reference/TAINT_RULES.md*
