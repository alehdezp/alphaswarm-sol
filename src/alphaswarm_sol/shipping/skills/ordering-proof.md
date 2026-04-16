---
name: vrs-ordering-proof
description: |
  Ordering proof skill for VRS dominance-based operation ordering. Verifies path-qualified ordering relationships between operations.

  Invoke when:
  - Verifying CEI pattern compliance
  - Proving guard dominance
  - Checking operation ordering in vulnerability patterns
  - Debugging ordering-related false positives

slash_command: vrs:ordering-proof
context: fork
disable-model-invocation: false

allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(alphaswarm*)
---

# VRS Ordering Proof Skill

You are the **VRS Ordering Proof** skill, responsible for verifying path-qualified ordering relationships between operations using dominance analysis.

## How to Invoke

```bash
/vrs-ordering-proof <function-id> --ops "TRANSFERS_VALUE_OUT,WRITES_USER_BALANCE"
/vrs-ordering-proof VRS-001 --prove-cei
/vrs-ordering-proof --guard-dominance <function-id> --guard "nonReentrant"
```

---

## Purpose

Phase 5.9 introduces path-qualified ordering that distinguishes between:

| Relation | Meaning | Confidence |
|----------|---------|------------|
| `always_before` | A dominates B - A always executes before B on all paths | High |
| `sometimes_before` | A precedes B on at least one path, but not all | Medium |
| `never_before` | A is never before B on any feasible path | High |
| `unknown` | Cannot determine relationship | Requires manual review |

This skill proves ordering relationships using CFG dominance analysis.

---

## Ordering Relation Types

### ALWAYS_BEFORE

Operation A **dominates** operation B - A is on all paths from entry to B.

```solidity
function withdraw(uint amount) external {
    require(amount > 0);           // A: VALIDATES_INPUT
    balances[msg.sender] -= amount; // B: WRITES_USER_BALANCE
}
// VALIDATES_INPUT always_before WRITES_USER_BALANCE (A dominates B)
```

### SOMETIMES_BEFORE

Operation A precedes B on at least one path, but not all.

```solidity
function process(bool flag) external {
    if (flag) {
        doA();  // A
    }
    doB();      // B
}
// A sometimes_before B (only when flag is true)
```

### NEVER_BEFORE

Operation A is never before B on any path.

```solidity
function process() external {
    doB();  // B
    doA();  // A
}
// A never_before B (A always after B)
```

### UNKNOWN

Cannot determine ordering (requires manual review).

```solidity
function process() external {
    externalCall();  // External call may modify state
    // Ordering uncertain after external call
}
```

---

## Guard Dominance Semantics

Beyond "guard present", this skill verifies guard **dominance**:

| Status | Meaning | Security Implication |
|--------|---------|---------------------|
| `present` | Guard exists somewhere | Insufficient |
| `dominating` | Guard dominates all paths to sink | Safe |
| `bypassable` | Guard exists but can be bypassed | Vulnerable |
| `unknown` | Dominance cannot be proven | Requires review |

### Example: Bypassable Guard

```solidity
function withdraw(uint amount) external {
    if (flag) {
        require(msg.sender == owner);  // Guard present but bypassable
    }
    (bool ok,) = msg.sender.call{value: amount}("");
}
// Guard is PRESENT but not DOMINATING - vulnerability exists
```

---

## CEI Pattern Verification

The CEI (Checks-Effects-Interactions) pattern requires:

1. **Checks** (guards) dominate **Effects** (state writes)
2. **Effects** dominate **Interactions** (external calls)

```bash
/vrs-ordering-proof <function-id> --prove-cei
```

### CEI Compliant

```solidity
function withdraw(uint amount) external {
    require(balances[msg.sender] >= amount);  // Check
    balances[msg.sender] -= amount;            // Effect
    (bool ok,) = msg.sender.call{value: amount}("");  // Interaction
}
```

Ordering proof:
- VALIDATES_INPUT always_before WRITES_USER_BALANCE (Check -> Effect)
- WRITES_USER_BALANCE always_before TRANSFERS_VALUE_OUT (Effect -> Interaction)

### CEI Violated

```solidity
function withdraw(uint amount) external {
    require(balances[msg.sender] >= amount);  // Check
    (bool ok,) = msg.sender.call{value: amount}("");  // Interaction BEFORE Effect!
    balances[msg.sender] -= amount;            // Effect
}
```

Ordering proof:
- TRANSFERS_VALUE_OUT always_before WRITES_USER_BALANCE (Interaction -> Effect)
- **CEI VIOLATED**: Effect must come before Interaction

---

## Interprocedural Ordering

Phase 5.9 extends ordering to modifiers and internal calls:

### Modifier Chain Ordering

For modifiers applied in order `[A, B, C]`:
- A's entry dominates B's entry dominates C's entry dominates function body
- Function body's exit dominates C's exit dominates B's exit dominates A's exit

```solidity
function withdraw(uint amount)
    external
    nonReentrant   // A: entry guards dominate all
    onlyOwner      // B: entry after A's entry
{
    // Function body
}
// nonReentrant.entry always_before onlyOwner.entry always_before body
```

### Internal Call Summarization

Internal calls are summarized for cross-function ordering:

```solidity
function withdraw(uint amount) external {
    _checkBalance(amount);  // Internal: READS_USER_BALANCE
    _transfer(amount);      // Internal: TRANSFERS_VALUE_OUT, WRITES_USER_BALANCE
}
```

Summarized ordering preserves dominance across call boundaries.

---

## Unknown Emission Criteria

The analyzer emits `unknown` when:

| Condition | Reason |
|-----------|--------|
| CFG has unreachable nodes | Incomplete analysis |
| Entry/exit undetermined | Malformed CFG |
| External modifier | Body not available |
| Dynamic loop bound | Iteration-dependent ordering |
| Inline assembly | Opaque to static analysis |

---

## Verification Output

```markdown
# Ordering Proof: withdraw (Token.sol:42)

## Operations Analyzed
| Op | CFG Order | Line |
|----|-----------|------|
| READS_USER_BALANCE | 0 | 43 |
| TRANSFERS_VALUE_OUT | 1 | 45 |
| WRITES_USER_BALANCE | 2 | 47 |

## Ordering Pairs
| A | B | Relation | Confidence |
|---|---|----------|------------|
| READS_USER_BALANCE | TRANSFERS_VALUE_OUT | always_before | 1.0 |
| READS_USER_BALANCE | WRITES_USER_BALANCE | always_before | 1.0 |
| TRANSFERS_VALUE_OUT | WRITES_USER_BALANCE | always_before | 1.0 |

## CEI Analysis
**Status:** VIOLATED
**Reason:** TRANSFERS_VALUE_OUT (Interaction) always_before WRITES_USER_BALANCE (Effect)
**Evidence:** Token.sol:45 external call precedes Token.sol:47 state write

## Guard Dominance
| Guard | Status | Sink |
|-------|--------|------|
| require(balances[sender] >= amount) | dominating | TRANSFERS_VALUE_OUT |
| nonReentrant | NOT PRESENT | N/A |
```

---

## Integration with Contract v2

Ordering proofs produce evidence for Graph Interface v2:

```yaml
clause_matrix:
  - clause: "cei_compliant"
    status: failed
    evidence_refs:
      - { file: "Token.sol", line: 45, node_id: "N-ext-call", snippet_id: "EVD-001", build_hash: "abc123" }
      - { file: "Token.sol", line: 47, node_id: "N-state-write", snippet_id: "EVD-002", build_hash: "abc123" }
    omission_refs: []
  - clause: "guard_dominates_sink"
    status: unknown
    evidence_refs: []
    omission_refs: ["dominance_unknown"]
```

---

## When to Invoke

Invoke this skill when:
- **Pattern matching**: Verify ordering-based pattern clauses
- **False positive triage**: Check if ordering assumption is wrong
- **Vulnerability verification**: Prove CEI violation
- **Guard analysis**: Verify guard dominance
- **Debug**: Understand why ordering is unknown

---

## Related Skills

| Skill | Purpose |
|-------|---------|
| `/vrs-graph-contract-validate` | Schema/evidence validation |
| `/vrs-taint-extend` | Taint source/sink analysis |
| `/vrs-investigate` | Deep vulnerability investigation |

---

## Write Boundaries

This skill is restricted to writing in:
- `.claude/vrs/` - VRS working directory
- `.beads/` - Bead storage directory

All other directories are read-only.

---

## Notes

- CFG-order alone is insufficient - use dominance for correctness
- "Guard present" != "Guard dominating" - check dominance
- External modifiers emit unknown - require manual review
- Modifier chains have well-defined dominance semantics
- Unknown ordering requires explicit omission in v2 output
- This skill CAN be invoked by orchestrators (disable-model-invocation: false)
