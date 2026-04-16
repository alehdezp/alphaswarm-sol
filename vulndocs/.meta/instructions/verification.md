# How to Write verification.md

The `verification.md` file explains **how to verify** that a finding is a true vulnerability, not a false positive.

## Purpose

This file provides:
1. Step-by-step verification workflow
2. Evidence requirements for confirmed findings
3. Exploit test guidance
4. False positive patterns to exclude

## Structure

### 1. Verification Steps

Numbered steps using graph queries:

```markdown
## Verification Steps

How to verify a finding is real (not a false positive):

1. **Check [Condition 1]**
   - Use graph query: `has_all_operations: [OP1, OP2]`
   - Expected: Both operations present in function

2. **Verify [Condition 2]**
   - Use graph query: `sequence_order: {before: OP1, after: OP2}`
   - Expected: OP1 happens before OP2

3. **Confirm [Condition 3]**
   - Use graph query: `NOT has_protection_mechanism`
   - Expected: No protective guards present
```

### 2. Evidence Requirements

Checklist of evidence items:

```markdown
## Evidence Requirements

A confirmed finding must have:
- [ ] Graph query result showing vulnerable pattern
- [ ] Operation sequence verification (CEI violation)
- [ ] Absence of protective measures (guards, checks)
- [ ] Exploit path demonstration (how to trigger)
```

### 3. Exploit Test

Guidance for creating a test:

```markdown
## Exploit Test

To definitively confirm, create a test that:
1. Deploy vulnerable contract
2. Execute attack sequence (e.g., reentrancy callback)
3. Verify exploit success (balance drained, state corrupted, etc.)

Expected result: Test passes, proving vulnerability is exploitable.
```

### 4. Common False Positives

Table of safe patterns:

```markdown
## Common False Positives

| Pattern | Why It's Safe | How to Detect |
|---------|---------------|---------------|
| Reentrancy guard | NonReentrant modifier blocks reentrancy | `has_reentrancy_guard = true` |
| Trusted contracts | Only calls to known safe addresses | `calls_only_trusted = true` |
| CEI pattern | State updated before external call | `sequence_order: safe pattern` |
```

## Good Example

```markdown
# Classic Reentrancy - Verification

## Verification Steps

How to verify a finding is real (not a false positive):

1. **Check operation presence**
   - Use graph query: `has_all_operations: [TRANSFERS_VALUE_OUT, WRITES_USER_BALANCE]`
   - Expected: Both operations in same function

2. **Verify ordering (CEI violation)**
   - Use graph query: `sequence_order: {before: TRANSFERS_VALUE_OUT, after: WRITES_USER_BALANCE}`
   - Expected: Value transfer happens BEFORE state write

3. **Confirm no guards**
   - Use graph query: `has_reentrancy_guard = false`
   - Expected: No nonReentrant modifier

4. **Check visibility**
   - Use graph query: `visibility IN [public, external]`
   - Expected: Function is externally callable

## Evidence Requirements

A confirmed finding must have:
- [ ] CEI violation (external call before state write)
- [ ] No reentrancy guard
- [ ] External visibility
- [ ] User balance affected by state write

## Exploit Test

To definitively confirm, create a test that:
1. Deploy vulnerable contract with withdrawal function
2. Create attacker contract with fallback/receive that re-enters
3. Call withdrawal, trigger reentrancy in callback
4. Verify attacker drained more than their balance

Expected result: Attacker balance > initial deposit (reentrancy successful).

## Common False Positives

| Pattern | Why It's Safe | How to Detect |
|---------|---------------|---------------|
| NonReentrant modifier | Blocks reentrant calls | `has_reentrancy_guard = true` |
| CEI pattern | State updated first | `sequence_order: safe` |
| Pull over Push | User withdraws, no push | `NOT TRANSFERS_VALUE_OUT` |
| Trusted contract | Only calls known addresses | `calls_only_trusted = true` |
```

## Bad Example (What NOT to do)

```markdown
# Verification

Check if the function looks vulnerable by reading the code.
Try to find reentrant patterns manually.
```

Problems:
- No graph queries
- "Read the code" instead of using VKG
- No evidence checklist
- No false positive table
- Not structured

## Common Mistakes

### Mistake 1: No Graph Queries
Every verification step should use a graph query. Manual inspection is not acceptable.

### Mistake 2: Missing Evidence Checklist
Verification must have clear evidence requirements that can be checked programmatically.

### Mistake 3: Vague Exploit Test
Exploit test should be concrete: exact steps, expected outcome.

### Mistake 4: No False Positive Table
Common false positives should be documented with detection methods.

## Graph-First Enforcement

All verification steps MUST use:
- BSKG property queries (e.g., `has_reentrancy_guard`)
- Operation checks (e.g., `has_all_operations`)
- Sequence validation (e.g., `sequence_order`)

No manual code reading. Agents use graph exclusively.

## Validation

Your verification.md should:
- [ ] Have numbered verification steps
- [ ] Use graph queries in every step
- [ ] Include evidence requirements checklist
- [ ] Provide concrete exploit test guidance
- [ ] List false positive patterns with detection methods

---

*Verification also uses graph queries. Tests are the ultimate proof.*
