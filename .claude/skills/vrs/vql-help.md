---
name: vrs-vql-help
description: |
  On-demand VQL (Vulnerability Query Language) syntax and query examples for agents.
  Provides quick reference for formulating correct graph queries without embedding
  full VQL documentation in every prompt.

  Invoke when:
  - Agent needs to formulate VQL query
  - Agent unsure of VQL syntax for specific operation
  - Agent wants example queries for vulnerability class
  - Need to check available semantic operations

  This skill:
  1. Provides VQL syntax reference
  2. Shows semantic operation usage
  3. Gives vulnerability-specific query examples
  4. Explains common pitfalls

slash_command: vrs:vql-help
context: fork

tools:
  - Read(docs/guides/queries.md, docs/reference/operations.md)

model_tier: haiku

---

# VRS VQL Help Skill - VQL Syntax Assistance

You are the **VRS VQL Help** skill, providing fast, concise VQL syntax and query examples to agents during vulnerability investigation.

**CRITICAL: Invocation Model**
You are Claude Code, an agent that follows this skill documentation. This is a reference skill - you provide syntax and examples, not execute queries. Keep responses under 500 tokens for fast Haiku performance.

## Purpose

- **Quick VQL reference** for agents formulating graph queries
- **Semantic operation syntax** for vulnerability detection
- **Example queries by vulnerability class** for common patterns
- **Common pitfalls** to avoid incorrect queries

---

## VQL Syntax Reference

### Basic Query Structure

```sql
FIND {target} WHERE {conditions}
```

**Targets:**
- `functions` - Function nodes
- `contracts` - Contract nodes
- `state_variables` - State variable nodes

**Example:**
```sql
FIND functions WHERE visibility = public
```

---

### Property Operators

| Operator | Usage | Example |
|----------|-------|---------|
| `=` | Equality | `visibility = public` |
| `!=` | Inequality | `visibility != private` |
| `IN` | List membership | `visibility IN [public, external]` |
| `NOT IN` | List exclusion | `visibility NOT IN [private, internal]` |
| `AND` | Logical AND | `writes_state AND is_payable` |
| `OR` | Logical OR | `has_modifier OR has_require` |
| `NOT` | Logical NOT | `NOT has_reentrancy_guard` |

---

### Semantic Operation Checks

**Has Operation:**
```sql
FIND functions WHERE has_operation(TRANSFERS_VALUE_OUT)
```

**Has All Operations:**
```sql
FIND functions WHERE has_all_operations([READS_BALANCE, WRITES_BALANCE])
```

**Operation Sequence (order matters):**
```sql
FIND functions WHERE operation_before(TRANSFERS_VALUE_OUT, WRITES_BALANCE)
```

**Common Operations:**
- `TRANSFERS_VALUE_OUT` - Transfers ETH/tokens
- `READS_USER_BALANCE` - Reads balance state
- `WRITES_USER_BALANCE` - Writes balance state
- `CALLS_EXTERNAL` - External contract calls
- `READS_ORACLE` - Reads oracle data
- `MODIFIES_CRITICAL_STATE` - Changes owner/admin/roles
- `CHECKS_PERMISSION` - Has access control check

---

### Label Checks (Tier C Patterns)

**Has Label:**
```sql
FIND functions WHERE has_label(state_mutation.balance_update)
```

**Missing Label:**
```sql
FIND functions WHERE missing_label(access_control.reentrancy_guard)
```

**Common Labels:**
- `state_mutation.balance_update` - Balance modification
- `access_control.reentrancy_guard` - Has reentrancy protection
- `access_control.owner_check` - Has owner check
- `oracle.price_read` - Reads price data
- `oracle.staleness_check` - Validates data freshness

---

## Example Queries by Vulnerability Class

### Reentrancy (Classic)

**Find vulnerable functions:**
```sql
FIND functions WHERE
  visibility IN [public, external] AND
  has_all_operations([TRANSFERS_VALUE_OUT, WRITES_USER_BALANCE]) AND
  operation_before(TRANSFERS_VALUE_OUT, WRITES_USER_BALANCE) AND
  NOT has_reentrancy_guard
```

**Explanation:** Functions that transfer value before updating state (CEI violation) without reentrancy guard.

---

### Access Control (Weak/Missing)

**Find unprotected critical functions:**
```sql
FIND functions WHERE
  visibility IN [public, external] AND
  has_operation(MODIFIES_CRITICAL_STATE) AND
  NOT has_access_gate
```

**Explanation:** Public functions that modify critical state (owner, roles, config) without access control.

---

### Oracle Manipulation (Stale Data)

**Find functions using oracle without validation:**
```sql
FIND functions WHERE
  has_operation(READS_ORACLE) AND
  uses_external_value_in_calculation AND
  NOT checks_timestamp
```

**Explanation:** Functions reading oracle data without checking staleness (updatedAt timestamp).

---

### Oracle Manipulation (Price Manipulation)

**Find functions vulnerable to price manipulation:**
```sql
FIND functions WHERE
  has_operation(READS_ORACLE) AND
  has_operation(TRANSFERS_VALUE_OUT) AND
  NOT has_price_validation
```

**Explanation:** Functions using oracle price to determine transfer amounts without validation.

---

### Flash Loan Attacks

**Find vulnerable callback targets:**
```sql
FIND functions WHERE
  has_all_operations([READS_BALANCE, WRITES_BALANCE]) AND
  is_callback_target AND
  NOT has_flash_loan_protection
```

**Explanation:** Callback functions that read/write balance without flash loan checks.

---

### Integer Overflow/Underflow

**Find unchecked arithmetic:**
```sql
FIND functions WHERE
  has_arithmetic_operations AND
  NOT uses_safe_math AND
  solidity_version < "0.8.0"
```

**Explanation:** Pre-0.8.0 contracts with arithmetic but no SafeMath library.

---

### Unprotected Initialization

**Find unprotected initialize functions:**
```sql
FIND functions WHERE
  label REGEX "^(initialize|init)" AND
  visibility IN [public, external] AND
  NOT has_initializer_modifier
```

**Explanation:** Initialization functions that can be called multiple times.

---

## Common Pitfalls

### ❌ Don't Use Function Names

**Bad:**
```sql
FIND functions WHERE label = "transfer"
```

**Good:**
```sql
FIND functions WHERE has_operation(TRANSFERS_VALUE_OUT)
```

**Reason:** Name-based detection misses renamed/obfuscated functions. Semantic operations are name-agnostic.

---

### ❌ Don't Forget Operation Order

**Bad:**
```sql
FIND functions WHERE
  has_operation(TRANSFERS_VALUE_OUT) AND
  has_operation(WRITES_BALANCE)
```

**Good:**
```sql
FIND functions WHERE
  operation_before(TRANSFERS_VALUE_OUT, WRITES_BALANCE)
```

**Reason:** Order matters for CEI violations. First query finds both vulnerable and safe functions.

---

### ❌ Don't Mix Operators Incorrectly

**Bad:**
```sql
FIND functions WHERE visibility = [public, external]
```

**Good:**
```sql
FIND functions WHERE visibility IN [public, external]
```

**Reason:** Use `IN` for list membership, not `=`.

---

### ❌ Don't Forget Negation

**Bad:**
```sql
FIND functions WHERE
  visibility = public AND
  has_operation(MODIFIES_OWNER)
```

**Good:**
```sql
FIND functions WHERE
  visibility = public AND
  has_operation(MODIFIES_OWNER) AND
  NOT has_access_gate
```

**Reason:** Without negation, you'll get both vulnerable AND protected functions.

---

## Response Format

When invoked, provide:

1. **Relevant syntax** for the query type
2. **1-2 example queries** for the vulnerability class
3. **Common pitfalls** to avoid

Keep response **under 500 tokens** for Haiku performance.

---

## Usage Examples

**User:** "Help me query for reentrancy"

**Response:**
```
VQL Query for Reentrancy:

FIND functions WHERE
  visibility IN [public, external] AND
  has_all_operations([TRANSFERS_VALUE_OUT, WRITES_USER_BALANCE]) AND
  operation_before(TRANSFERS_VALUE_OUT, WRITES_USER_BALANCE) AND
  NOT has_reentrancy_guard

This finds functions that:
- Are publicly callable
- Transfer value before updating balance (CEI violation)
- Lack reentrancy guard

Pitfall: Don't forget operation_before() - order matters!
```

---

**User:** "How do I check for missing access control?"

**Response:**
```
VQL Query for Missing Access Control:

FIND functions WHERE
  visibility IN [public, external] AND
  has_operation(MODIFIES_CRITICAL_STATE) AND
  NOT has_access_gate

This finds functions that:
- Are publicly callable
- Modify critical state (owner, roles, config)
- Have no access control check

Pitfall: Always include NOT has_access_gate to exclude protected functions.
```

---

**User:** "What operations exist for oracle manipulation?"

**Response:**
```
Oracle Operations:
- READS_ORACLE - Reads external oracle
- READS_EXTERNAL_VALUE - Reads external data
- USES_IN_CALCULATION - Uses value in math
- CHECKS_TIMESTAMP - Validates staleness

Example Query:
FIND functions WHERE
  has_operation(READS_ORACLE) AND
  uses_external_value_in_calculation AND
  NOT checks_timestamp

This finds oracle reads without staleness validation.
```

---

## Key Rules

### 1. Keep Responses Concise

Target **300-500 tokens** per response. This is a quick reference skill, not comprehensive documentation.

### 2. Always Show Semantic Operations

Prefer semantic operations (`has_operation(...)`) over property checks (`label = "transfer"`).

### 3. Include Pitfalls

Every response should warn about at least one common mistake.

### 4. Use Real Examples

Show queries that actually work against BSKG graphs, not theoretical syntax.

---

## Quick Reference Card

**Basic Query:**
```sql
FIND functions WHERE visibility = public
```

**With Operations:**
```sql
FIND functions WHERE has_operation(TRANSFERS_VALUE_OUT)
```

**With Sequence:**
```sql
FIND functions WHERE operation_before(READ, WRITE)
```

**With Negation:**
```sql
FIND functions WHERE writes_state AND NOT has_access_gate
```

**With Labels:**
```sql
FIND functions WHERE has_label(state_mutation.balance_update)
```

---

**VRS VQL Help - Part of Phase 5.5 (Agent Execution & Context Enhancement)**
*Created: 2026-01-22*
