# How to Write detection.md

The `detection.md` file explains **how to detect** this vulnerability using BSKG graph queries and semantic operations.

## Purpose

This file provides:
1. Semantic operations to look for
2. VQL queries for detection
3. Behavioral patterns (vulnerable vs safe)
4. Detection workflow
5. False positive filters

## Critical Rule: Graph-First

**Agents MUST use BSKG graph queries, NOT manual code reading.**

All detection logic should be based on:
- BSKG semantic operations (e.g., `TRANSFERS_VALUE_OUT`, `READS_ORACLE`)
- VQL queries (e.g., `FIND functions WHERE ...`)
- Graph patterns (e.g., `read -> call -> write`)

## Structure

### 1. Semantic Operations

List the key BSKG operations that indicate this vulnerability:

```markdown
## Semantic Operations

**CRITICAL:** Use BSKG graph queries, NOT manual code reading.

Key operations to detect:
- `TRANSFERS_VALUE_OUT`: Function transfers value to external address
- `WRITES_USER_BALANCE`: Function modifies user balance mapping
- `READS_USER_BALANCE`: Function reads user balance before transfer
```

### 2. Graph Queries

Provide VQL queries that detect this pattern:

```markdown
## Graph Queries

### Primary Detection Query
\`\`\`vql
FIND functions WHERE
  has_all_operations: [TRANSFERS_VALUE_OUT, WRITES_USER_BALANCE] AND
  sequence_order: {before: TRANSFERS_VALUE_OUT, after: WRITES_USER_BALANCE} AND
  NOT has_reentrancy_guard
\`\`\`

### Secondary Checks
\`\`\`vql
FIND functions WHERE
  visibility IN [public, external] AND
  uses_low_level_call AND
  state_write_after_external_call
\`\`\`
```

### 3. Behavioral Patterns

Show vulnerable vs safe patterns:

```markdown
## Behavioral Patterns

### Vulnerable Pattern
\`\`\`
READS_BALANCE -> TRANSFERS_VALUE -> WRITES_BALANCE
\`\`\`
The function reads balance, makes an external call, then updates balance.
This creates a reentrancy window.

### Safe Pattern
\`\`\`
READS_BALANCE -> WRITES_BALANCE -> TRANSFERS_VALUE
\`\`\`
Checks-Effects-Interactions: state is updated before external call.
```

### 4. Detection Steps

Provide a numbered workflow:

```markdown
## Detection Steps

1. **Identify candidates:** Run VQL query to find functions with value transfers
2. **Verify ordering:** Check operation sequence (value transfer before state write?)
3. **Check protections:** Look for reentrancy guards, CEI pattern
4. **Confirm vulnerability:** Verify no protective measures present
```

### 5. False Positive Filters

List patterns that look vulnerable but aren't:

```markdown
## False Positive Filters

- **Reentrancy guard present:** Function has `nonReentrant` modifier
- **Trusted contract only:** External call is to hardcoded trusted address
- **No state impact:** State write is unrelated to value transfer
- **Pull pattern:** Function doesn't push value, user pulls
```

## Good Example

```markdown
# Oracle Price Manipulation - Detection

## Semantic Operations

**CRITICAL:** Use BSKG graph queries, NOT manual code reading.

Key operations to detect:
- `READS_EXTERNAL_VALUE`: Function reads value from external source
- `READS_ORACLE`: Function queries oracle contract
- `USES_IN_CALCULATION`: External value used in financial calculation
- `NO_STALENESS_CHECK`: No timestamp or freshness validation

## Graph Queries

### Primary Detection Query
\`\`\`vql
FIND functions WHERE
  reads_oracle AND
  uses_external_value_in_calculation AND
  NOT has_staleness_check
\`\`\`

### Check for TWAP
\`\`\`vql
FIND functions WHERE
  reads_oracle AND
  NOT uses_twap AND
  NOT has_bounds_check
\`\`\`

## Behavioral Patterns

### Vulnerable Pattern
\`\`\`
oracle_read -> calculation -> state_write
\`\`\`
Single spot price used directly in calculation.

### Safe Pattern
\`\`\`
twap_read -> staleness_check -> bounds_check -> calculation -> state_write
\`\`\`
TWAP with validation before use.

## Detection Steps

1. **Identify candidates:** Find functions that read from oracles
2. **Check TWAP:** Verify if TWAP is used (multiple price points)
3. **Verify staleness:** Look for timestamp checks (e.g., `updatedAt < block.timestamp - MAX_AGE`)
4. **Trace value flow:** Ensure price is validated before financial calculation

## False Positive Filters

- **TWAP used:** Function averages multiple price points
- **Staleness check present:** Validates price timestamp
- **Bounds checking:** Min/max price validation
- **Read-only function:** Price used for display, not state changes
```

## Bad Example (What NOT to do)

```markdown
# Detection

Look for functions named `getPrice` or `swap`. Check if they call `latestAnswer()`.
Read the source code to see if there are any checks.
```

Problems:
- Uses function names instead of semantic operations
- Tells agent to "read source code" instead of using graph
- No VQL queries
- No behavioral patterns
- Not graph-first

## Common Mistakes

### Mistake 1: Name-Based Detection
Bad: "Look for functions named `withdraw` or `transfer`"
Good: "Look for functions with `TRANSFERS_VALUE_OUT` operation"

### Mistake 2: Manual Code Inspection
Bad: "Read the contract source to check for guards"
Good: "Query graph: `has_reentrancy_guard` property"

### Mistake 3: Implementation Details
Bad: "Check if function calls `address.call{value: x}()`"
Good: "Check if function has `TRANSFERS_VALUE_OUT` operation"

### Mistake 4: Missing VQL Queries
Every detection.md should have at least one VQL query. Graph queries are the primary detection mechanism.

## Validation

Your detection.md should:
- [ ] Start with "Use BSKG graph queries, NOT manual code reading"
- [ ] List semantic operations (ALL CAPS)
- [ ] Include at least one VQL query
- [ ] Show vulnerable vs safe patterns
- [ ] Provide numbered detection steps
- [ ] List false positive filters

## Template Reference

See `.meta/templates/subcategory/detection.md` (if exists) or use the structure above.

---

*Graph-first enforcement: Agents use BSKG queries for all analysis.*
