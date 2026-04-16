---
name: vrs-taint-extend
description: |
  Taint extension skill for VRS dataflow analysis. Analyzes taint sources, sinks, sanitizers, and availability for vulnerability detection.

  Invoke when:
  - Tracing attacker-controlled input
  - Identifying taint sources in a function
  - Checking if tainted data reaches sensitive sinks
  - Verifying sanitizer effectiveness

slash_command: vrs:taint-extend
context: fork
disable-model-invocation: false

allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(alphaswarm*)
---

# VRS Taint Extend Skill

You are the **VRS Taint Extend** skill, responsible for analyzing taint propagation from attacker-controlled sources to sensitive sinks.

## How to Invoke

```bash
/vrs-taint-extend <function-id> --sources
/vrs-taint-extend <function-id> --trace "amount"
/vrs-taint-extend VRS-001 --sinks
/vrs-taint-extend --check-sanitizers <function-id>
```

---

## Purpose

Phase 5.9 expands taint analysis with:

1. **Extended sources** - User input, external returns, oracle values, call target control
2. **Explicit sinks** - Call targets, storage writes, arithmetic operations
3. **Sanitizer tracking** - Bounds checks, whitelist checks, safe math
4. **Availability flags** - Confidence in taint analysis results

CRITICAL: Missing taint data is marked **unknown**, not safe.

---

## Taint Sources

Sources of tainted data, ranked by risk:

| Source | Risk | Description |
|--------|------|-------------|
| `CALL_TARGET_CONTROL` | CRITICAL | User controls call destination |
| `EXTERNAL_RETURN` | HIGH | Return value from external call |
| `USER_INPUT` | HIGH | Function parameters |
| `ORACLE` | HIGH | External price feeds |
| `ENVIRONMENT` | MEDIUM | msg.sender, msg.value, block.* |
| `STORAGE_ALIASED` | LOW | Read from tainted storage slot |

### Call Target Control (CRITICAL)

User controls the address being called:

```solidity
function execute(address target, bytes calldata data) external {
    target.call(data);  // CRITICAL: target is user-controlled
}
```

### External Return (HIGH)

Return values from external calls are tainted:

```solidity
function getPrice() external {
    uint price = oracle.latestAnswer();  // Tainted: external return
    balances[msg.sender] = price;         // Tainted flows to storage
}
```

### User Input (HIGH)

All function parameters are tainted:

```solidity
function transfer(address to, uint amount) external {
    // 'to' and 'amount' are tainted
}
```

---

## Taint Sinks

Operations where tainted data creates security risk:

| Sink | Severity | Description |
|------|----------|-------------|
| `CALL_TARGET` | CRITICAL | TAINTED_ADDR.call() |
| `EXTERNAL_CALL_VALUE` | CRITICAL | .call{value: TAINTED}() |
| `STORAGE_WRITE` | HIGH | balances[x] = TAINTED |
| `ARITHMETIC` | MEDIUM | a + TAINTED (overflow risk) |
| `COMPARISON` | LOW | if (TAINTED > x) |

### Source-Sink Severity Matrix

| Source | CALL_TARGET | STORAGE_WRITE | ARITHMETIC |
|--------|-------------|---------------|------------|
| CALL_TARGET_CONTROL | CRITICAL | HIGH | MEDIUM |
| EXTERNAL_RETURN | CRITICAL | HIGH | MEDIUM |
| USER_INPUT | CRITICAL | HIGH | MEDIUM |
| ORACLE | HIGH | HIGH | HIGH |
| ENVIRONMENT | MEDIUM | MEDIUM | LOW |

---

## Taint Sanitizers

Operations that reduce or eliminate taint:

| Sanitizer | Affects | Example |
|-----------|---------|---------|
| `BOUNDS_CHECK` | ARITHMETIC | require(x < MAX) |
| `OWNERSHIP_CHECK` | (context) | require(msg.sender == owner) |
| `SAFE_MATH` | ARITHMETIC | x.add(y) |
| `TYPE_CAST` | ARITHMETIC | uint8(x) |
| `WHITELIST_CHECK` | CALL_TARGET | require(allowed[addr]) |
| `ZERO_CHECK` | (weak) | require(addr != address(0)) |

### Sanitizer Effectiveness

```solidity
function transfer(address to, uint amount) external {
    require(amount <= balances[msg.sender]);  // BOUNDS_CHECK sanitizes ARITHMETIC
    require(whitelist[to]);                    // WHITELIST_CHECK sanitizes CALL_TARGET
    to.call{value: amount}("");
}
```

---

## Taint Availability

Confidence in taint analysis results:

| Availability | Confidence | Action |
|--------------|------------|--------|
| `full` | 1.0 | Use result directly |
| `aliased` | 0.7 | Use with caution (storage aliasing) |
| `external_call` | 0.5 | Require manual review |
| `delegatecall` | 0.0 (unavailable) | Treat as UNKNOWN |
| `inline_assembly` | 0.0 (unavailable) | Treat as UNKNOWN |
| `dynamic_loop` | 0.6 | Iteration-dependent taint |
| `recursive` | 0.5 | Depth unknown |
| `try_catch` | 0.4 | Exception path uncertainty |

### Availability Thresholds

| Range | Meaning | Recommendation |
|-------|---------|----------------|
| >= 0.9 | High confidence | Use result directly |
| 0.7-0.89 | Medium confidence | Use with caution |
| 0.5-0.69 | Low confidence | Require manual review |
| < 0.5 | Insufficient | Treat as UNKNOWN |

---

## Taint Result Structure

```python
TaintResult:
    is_tainted: bool          # Is value tainted?
    sources: List[TaintSource]  # Contributing sources
    path: List[str]           # Propagation path
    availability: TaintAvailability  # Confidence
    sanitizers_applied: List[TaintSanitizer]  # Applied sanitizers
    sink: Optional[TaintSink]  # Target sink if checking reachability
```

### Key Properties

- `is_unknown`: True if taint analysis unavailable - NOT safe
- `is_safe`: True only if available AND not tainted
- `risk_level`: Highest risk among sources

---

## Analysis Output

```markdown
# Taint Analysis: withdraw (Vault.sol:42)

## Sources Detected
| Variable | Source Type | Risk | Line |
|----------|-------------|------|------|
| amount | USER_INPUT | HIGH | 42 |
| recipient | USER_INPUT | HIGH | 42 |

## Taint Propagation
```
amount (USER_INPUT) -> balances[sender] (STORAGE_WRITE)
amount (USER_INPUT) -> call{value: amount} (EXTERNAL_CALL_VALUE)
recipient (USER_INPUT) -> recipient.call (CALL_TARGET)
```

## Sinks Reached
| Sink | Source | Sanitizers | Severity |
|------|--------|------------|----------|
| CALL_TARGET | recipient (USER_INPUT) | ZERO_CHECK | CRITICAL |
| EXTERNAL_CALL_VALUE | amount (USER_INPUT) | BOUNDS_CHECK | HIGH (sanitized) |
| STORAGE_WRITE | amount (USER_INPUT) | none | HIGH |

## Availability
| Check | Confidence | Reason |
|-------|------------|--------|
| amount -> storage | 1.0 | Full |
| recipient -> call | 0.7 | Storage aliasing |
| external return | 0.0 | Unavailable - delegatecall present |

## Risk Assessment
**Highest Risk:** CRITICAL (CALL_TARGET with USER_INPUT)
**Sanitizer Gap:** CALL_TARGET sink has only ZERO_CHECK (weak)
```

---

## Integration with Contract v2

Taint analysis produces evidence for Graph Interface v2:

```yaml
clause_matrix:
  - clause: "tainted_call_target"
    status: matched
    evidence_refs:
      - { file: "Vault.sol", line: 45, node_id: "N-call", snippet_id: "EVD-001", build_hash: "abc123" }
    omission_refs: []
  - clause: "tainted_storage_write"
    status: unknown
    evidence_refs: []
    omission_refs: ["taint_dataflow_unavailable"]

evidence_missing:
  - reason: "aliasing_unknown"
    clause: "tainted_storage_write"
    details: "Storage aliasing reduces confidence below threshold"
```

---

## Aliasing Strategy

Phase 5.9 uses **Direct-then-Aliased** strategy:

1. **Direct taint** - User input flows directly to sink
2. **Aliased taint** - User input writes to storage, later read flows to sink

```solidity
function deposit(uint amount) external {
    balances[msg.sender] += amount;  // Tainted write to storage
}

function withdraw() external {
    uint bal = balances[msg.sender];  // Aliased: reads tainted storage
    msg.sender.call{value: bal}("");  // Tainted flows to sink
}
```

Aliased taint has lower confidence (0.7).

---

## When to Invoke

Invoke this skill when:
- **Source identification**: Find all taint sources in a function
- **Sink reachability**: Check if tainted data reaches sensitive sinks
- **Sanitizer verification**: Verify sanitizers are effective
- **Availability diagnosis**: Understand why taint analysis is unavailable
- **Risk assessment**: Prioritize findings by taint risk level

---

## Related Skills

| Skill | Purpose |
|-------|---------|
| `/vrs-graph-contract-validate` | Schema/evidence validation |
| `/vrs-ordering-proof` | Dominance-based ordering verification |
| `/vrs-investigate` | Deep vulnerability investigation |

---

## Write Boundaries

This skill is restricted to writing in:
- `.claude/vrs/` - VRS working directory
- `.beads/` - Bead storage directory

All other directories are read-only.

---

## Notes

- Missing taint data is UNKNOWN, not safe
- Delegatecall makes all taint analysis unavailable
- Inline assembly makes taint analysis unavailable
- Storage aliasing reduces confidence to 0.7
- External returns are HIGH risk sources
- Call target control is CRITICAL risk
- Zero-check is a weak sanitizer (not sufficient alone)
- This skill CAN be invoked by orchestrators (disable-model-invocation: false)
