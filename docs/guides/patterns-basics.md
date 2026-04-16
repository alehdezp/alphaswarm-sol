# Pattern Basics

**Introduction to vulnerability detection patterns in AlphaSwarm.sol.**

---

## Overview

Patterns are YAML-defined vulnerability checks that leverage the BSKG's 200+ derived properties per function. This guide covers the fundamentals of pattern design and structure.

**For advanced topics (Tier A+B matching, PCP v2, migration), see [Pattern Advanced Guide](patterns-advanced.md).**

---

## Pattern Design Philosophy

### Core Principles

| Principle | Description | Example |
|-----------|-------------|---------|
| **Semantic > Syntactic** | Use behavioral properties, not names | `writes_privileged_state` not `.*owner.*` |
| **Defense in Depth** | Combine multiple conditions | Visibility + behavior + missing guard |
| **Graph-Native** | Leverage nodes, edges, paths | Edge requirements for data flow |
| **Skeptical by Default** | One flag is a hint, three is a finding | Multiple discriminating conditions |

### Implementation-Agnostic Detection

**NEVER** use:
- Function name regex (`.*[Ww]ithdraw.*`)
- Variable name matching (`owner`, `admin`)
- Hardcoded identifiers

**ALWAYS** use:
- Semantic properties (`writes_privileged_state`)
- Behavioral detection (`state_write_after_external_call`)
- Graph relationships (edges, paths)

---

## Pattern Structure

### Basic Template

```yaml
id: <lens>-<number>           # auth-001, vm-015, ext-003
name: "Human Readable Name"
description: |
  What this pattern detects and why it's dangerous.
scope: Function               # Function, Contract, StateVariable
lens:
  - Authority                 # Primary security lens
severity: high                # critical, high, medium, low, info
status: draft                 # draft, ready, excellent

match:
  all: []                     # All must match (AND)
  any: []                     # At least one (OR)
  none: []                    # None can match (NOT)

edges: []                     # Optional graph edge requirements
paths: []                     # Optional graph path requirements

test_coverage:                # Populated by workflow test harness / pytest
  projects: []
  precision: 0.0
  recall: 0.0
  variation_score: 0.0
```

### Lens Prefixes

| Lens | Prefix | Focus |
|------|--------|-------|
| Authority | `auth-` | Access control, ownership, roles |
| Value Movement | `vm-` | Reentrancy, fund transfers |
| External Influence | `ext-` | Oracles, external calls |
| Arithmetic | `arith-` | Math, precision, overflow |
| Liveness | `live-` | DoS, gas limits |
| Ordering/Upgradability | `ord-` | Proxies, upgrades |
| Logic State | `logic-` | Business logic, state machines |

---

## Match Conditions

### Property Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `eq` | Equals | `{property: x, op: eq, value: true}` |
| `neq` | Not equals | `{property: x, op: neq, value: false}` |
| `in` | In list | `{property: x, op: in, value: [a, b]}` |
| `not_in` | Not in list | `{property: x, op: not_in, value: [a]}` |
| `gt`, `gte` | Greater than | `{property: x, op: gt, value: 5}` |
| `lt`, `lte` | Less than | `{property: x, op: lt, value: 10}` |
| `contains` | Array contains | `{property: tags, op: contains, value: owner}` |
| `regex` | Regex match | `{property: label, op: regex, value: "^set"}` |
| `exists` | Property exists | `{property: x, op: exists}` |

### Boolean Logic

```yaml
match:
  # AND: All must be true
  all:
    - property: visibility
      op: in
      value: [public, external]
    - property: writes_privileged_state
      op: eq
      value: true

  # OR: At least one true
  any:
    - property: uses_delegatecall
      op: eq
      value: true
    - property: uses_call
      op: eq
      value: true

  # NOT: None can be true (CRITICAL for false positive reduction)
  none:
    - property: has_access_gate
      op: eq
      value: true
    - property: is_constructor
      op: eq
      value: true
```

---

## Key Properties by Category

### Access Control

```yaml
has_access_gate              # Any access restriction
has_access_modifier          # Modifier-based access
has_only_owner               # onlyOwner pattern
writes_privileged_state      # Modifies owner/role/admin
```

### Reentrancy & External Calls

```yaml
has_external_calls           # Any external call
state_write_before_external_call  # Safe CEI
state_write_after_external_call   # Potential reentrancy
has_reentrancy_guard         # nonReentrant guard
```

### Oracle & Pricing

```yaml
reads_oracle_price           # Reads oracle feed
has_staleness_check          # Validates freshness
oracle_source_count          # Number of sources
```

See [Property Reference](../reference/properties.md) for complete list.

---

## Pattern Design Methodology

### Step 1: Identify Core Signal

Ask: **"What is the ONE property that MUST be true?"**

| Vulnerability | Core Signal |
|---------------|-------------|
| Reentrancy | `state_write_after_external_call == true` |
| Unprotected write | `writes_privileged_state AND NOT has_access_gate` |
| Missing slippage | `swap_like AND NOT has_slippage_parameter` |

### Step 2: Add Discriminators

Ask:
- "What visibility makes this exploitable?" (usually public/external)
- "What guard would make this safe?" (add to `none` section)
- "What context increases danger?" (callbacks, inheritance)

### Step 3: Validate Mentally

Before finalizing:
1. Would this catch the classic exploit? (e.g., DAO hack)
2. Would this flag clearly safe code? (e.g., CEI with guard)
3. What would cause false positives? (document and exclude)
4. Would this survive code renaming? (no naming dependencies)

---

## Complete Pattern Example

```yaml
id: auth-001
name: Unprotected Privileged State Write
description: |
  Public/external functions that modify privileged state (owner, admin,
  roles) without access control, allowing privilege escalation.

scope: Function
lens:
  - Authority
severity: critical
status: ready

match:
  all:
    - property: visibility
      op: in
      value: [public, external]
    - property: writes_privileged_state
      op: eq
      value: true
  none:
    - property: has_access_gate
      op: eq
      value: true
    - property: is_constructor
      op: eq
      value: true
    - property: has_access_modifier
      op: eq
      value: true

attack_scenarios:
  - name: Direct Ownership Takeover
    description: Attacker calls unprotected function to become owner

verification_steps:
  - Verify function is externally callable
  - Confirm no access control in modifiers or body

fix_recommendations:
  - name: Add onlyOwner Modifier
    example: |
      function setOwner(address newOwner) external onlyOwner {
          owner = newOwner;
      }

related_patterns:
  - auth-002

cwe_mapping:
  - CWE-284
  - CWE-285

test_coverage:
  projects: [defi-lending, governance-dao]
  precision: 0.89
  recall: 0.92
```

---

## Running Patterns

```bash
# Test single pattern
uv run alphaswarm query "pattern:auth-001"

# With explanation
uv run alphaswarm query "pattern:auth-001" --explain

# All patterns in lens
uv run alphaswarm query "lens:Authority"

# Run pattern tests
uv run pytest -k "auth-001" -v
```

---

## Related Documentation

- [Pattern Advanced Guide](patterns-advanced.md) - Tier A+B matching, edge requirements, PCP v2
- [Pattern Testing Guide](testing.md) - Test patterns and assign ratings
- [Property Reference](../reference/properties.md) - All 275 emitted properties

---

*Version 3.0 | February 2026*
