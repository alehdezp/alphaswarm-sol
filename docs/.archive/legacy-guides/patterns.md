# Pattern Authoring Guide

**How to Design and Write Vulnerability Detection Patterns**

---

## Overview

Patterns are YAML-defined vulnerability checks that leverage the BSKG's 50+ derived properties per function and graph structure. This guide covers:
1. **Pattern Design Methodology** - How to think about vulnerability detection
2. **Pattern Structure** - YAML format and operators
3. **Implementation-Agnostic Detection** - Semantic over syntactic matching
4. **Agent Workflow** - Using `vrs-pattern-architect` and `pattern-tester`

---

## Pattern Development Skills And Agents (Cross-Refs)

**Canonical registries:**
- Skills: `src/alphaswarm_sol/skills/registry.yaml`
- Agents: `src/alphaswarm_sol/agents/catalog.yaml`

**Pattern development skills (selected):**
- `vrs-discover`, `vrs-research`, `vrs-ingest-url`, `vrs-add-vulnerability`, `vrs-merge-findings`
- `pattern-forge`, `vrs-refine`, `vrs-test-pattern`, `pattern-verify`, `pattern-batch`
- `vrs-validate-vulndocs`

**Pattern development agents (selected):**
- `vrs-pattern-scout` → `src/alphaswarm_sol/skills/shipped/agents/vrs-pattern-scout.md`
- `vrs-pattern-verifier` → `src/alphaswarm_sol/skills/shipped/agents/vrs-pattern-verifier.md`
- `vrs-pattern-composer` → `src/alphaswarm_sol/skills/shipped/agents/vrs-pattern-composer.md`
- `vrs-context-packer` → `src/alphaswarm_sol/skills/shipped/agents/vrs-context-packer.md`
- `vrs-prevalidator` → `src/alphaswarm_sol/skills/shipped/agents/vrs-prevalidator.md`

**Dev-only pattern agents (Claude Code):**
- `vrs-pattern-architect` → `.claude/agents/vrs-pattern-architect.md`
- `pattern-tester` → `.claude/agents/pattern-tester.md`

These are referenced here to enable cross‑linking between docs and agent definitions.

## 1. Pattern Design Philosophy

### Core Principles

| Principle | Description | Example |
|-----------|-------------|---------|
| **Semantic > Syntactic** | Use behavioral properties, not names | `writes_privileged_state` not `.*owner.*` |
| **Defense in Depth** | Combine multiple conditions | Visibility + behavior + missing guard |
| **Graph-Native** | Leverage nodes, edges, paths | Edge requirements for data flow |
| **Skeptical by Default** | One flag is a hint, three is a finding | Multiple discriminating conditions |
| **Actionable Output** | Findings must be verifiable | Include attack scenarios and fixes |

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

## 2. Using the Pattern Architect Agent

The `vrs-pattern-architect` agent automates pattern design. Invoke it when:
- Creating new vulnerability detection patterns
- Optimizing existing patterns for lower false positives
- Designing detection for specific vulnerability classes

### Agent Workflow

```
User Request → vrs-pattern-architect
    ├── Research vulnerability (CVEs, exploits, audits)
    ├── Read builder.py for available properties
    ├── Check existing patterns for conventions
    ├── Design: core signal + discriminators + exclusions
    ├── Create pattern YAML
    └── Invoke pattern-tester for quality scoring
```

### Pattern Quality Lifecycle

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   DRAFT     │───►│   READY     │───►│  EXCELLENT  │
│  <70% prec  │    │  ≥70% prec  │    │  ≥90% prec  │
│  <50% rec   │    │  ≥50% rec   │    │  ≥85% rec   │
│  <60% var   │    │  ≥60% var   │    │  ≥85% var   │
└─────────────┘    └─────────────┘    └─────────────┘
```

---

## 3. Pattern Structure

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

test_coverage:                # Populated by pattern-tester
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

## 4. Match Conditions

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
| `contains_any` | Contains any | `{property: tags, op: contains_any, value: [a,b]}` |
| `contains_all` | Contains all | `{property: tags, op: contains_all, value: [a,b]}` |
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

## 5. Key Properties by Category

### Access Control (20+ properties)

```yaml
has_access_gate              # Any access restriction
has_access_modifier          # Modifier-based access
has_only_owner               # onlyOwner pattern
has_only_role                # onlyRole pattern
writes_privileged_state      # Modifies owner/role/admin
writes_sensitive_config      # Modifies fee/config
uses_tx_origin               # Uses tx.origin
is_privileged_operation      # Privileged classification
```

### Reentrancy & External Calls (25+ properties)

```yaml
has_external_calls           # Any external call
has_untrusted_external_call  # User-controlled target
state_write_before_external_call  # Safe CEI
state_write_after_external_call   # Potential reentrancy
has_reentrancy_guard         # nonReentrant guard
uses_delegatecall            # Delegatecall usage
call_target_user_controlled  # User controls target
external_calls_in_loop       # Calls in loops
```

### Oracle & Pricing (35+ properties)

```yaml
reads_oracle_price           # Reads oracle feed
has_staleness_check          # Validates freshness
has_sequencer_uptime_check   # L2 sequencer check
oracle_source_count          # Number of sources
reads_twap                   # Uses TWAP
has_twap_window_parameter    # TWAP window set
```

### MEV & Trading (15+ properties)

```yaml
swap_like                    # Swap operation
has_deadline_parameter       # Deadline param
has_deadline_check           # Deadline validated
has_slippage_parameter       # Slippage param
has_slippage_check           # Slippage validated
risk_missing_slippage_parameter  # Missing protection
```

### DoS & Liveness (15+ properties)

```yaml
has_unbounded_loop           # User-controlled bounds
external_calls_in_loop       # Calls in loops
has_strict_equality_check    # == with block data
uses_transfer                # transfer() 2300 gas
storage_growth_operation     # Array push
```

See [Property Reference](../reference/properties.md) for complete list.

---

## 6. Advanced Matching

### Edge Requirements

Match based on graph relationships:

```yaml
edges:
  # Function writes to privileged state variable
  - type: WRITES_STATE
    direction: out
    target_type: StateVariable
    target_match:
      property: security_tags
      op: contains_any
      value: [owner, role, admin]

  # Function receives tainted input
  - type: FUNCTION_INPUT_TAINTS_STATE
    direction: out
```

### Path Requirements

Match based on multi-hop graph traversal:

```yaml
paths:
  # Reachable from public entry point
  - from_type: Function
    from_property: visibility
    from_value: public
    edge_types: [CALLS_INTERNAL]
    max_depth: 5
```

### Tier A + B Matching (Semantic)

Tier A (deterministic) and Tier B (LLM-enhanced) can work together:

| Aggregation Mode | Description | Use Case |
|------------------|-------------|----------|
| `tier_a_only` | Only Tier A conditions matter | Standard deterministic patterns |
| `tier_a_required` | Tier A must match, Tier B confirms | Business logic, invariants |
| `tier_b_enhances` | Tier A is broad filter, Tier B does real detection | Semantic inconsistency |
| `voting` | Multiple tiers vote on match | Future: consensus-based |

```yaml
match:
  # Tier A: Deterministic (always evaluated)
  tier_a:
    all:
      - property: visibility
        op: in
        value: [public, external]
      - has_operation: TRANSFERS_VALUE_OUT
      - sequence_order:
          before: TRANSFERS_VALUE_OUT
          after: WRITES_USER_BALANCE
    none:
      - property: has_reentrancy_guard
        value: true

  # Tier B: Semantic (LLM-enhanced)
  tier_b:
    any:
      - has_risk_tag: reentrancy

aggregation:
  mode: tier_a_required  # tier_a_only, tier_a_required, voting
```

### Tier B Pattern Types

Tier B patterns require LLM reasoning for vulnerabilities that can't be detected deterministically:

| Pattern Type | Example | Risk Tags |
|--------------|---------|-----------|
| **Business Logic** | Intent vs implementation mismatch | `intent_deviation`, `business_logic_mismatch` |
| **Invariant Violation** | Protocol invariants not enforced | `invariant_violation`, `unbacked_shares` |
| **Semantic Inconsistency** | Naming doesn't match behavior | `naming_behavior_mismatch`, `fake_safety_label` |
| **Trust Assumption** | Implicit trust boundaries violated | `implicit_trust_boundary`, `trust_transitivity_risk` |

**Example Tier B Pattern (Business Logic):**
```yaml
match:
  tier_a:
    all:
      - property: visibility
        op: in
        value: [public, external]
      - property: writes_state
        op: eq
        value: true
    any:
      - property: transfers_value
        op: eq
        value: true
      - property: writes_privileged_state
        op: eq
        value: true
  tier_b:
    any:
      - has_risk_tag: intent_deviation
      - has_risk_tag: business_logic_mismatch
      - has_risk_tag: invariant_violation

aggregation:
  mode: tier_a_required  # Tier A is prerequisite, Tier B confirms
```

**LLM Guidance Section:** Tier B patterns should include an `llm_guidance` field with instructions for the LLM on how to evaluate the pattern and assign risk tags.

### Operation Matching

```yaml
# Single operation
- has_operation: TRANSFERS_VALUE_OUT

# All required
- has_all_operations:
    - TRANSFERS_VALUE_OUT
    - WRITES_USER_BALANCE

# Any of
- has_any_operation:
    - CALLS_EXTERNAL
    - CALLS_UNTRUSTED

# Sequence ordering (CEI violation)
- sequence_order:
    before: TRANSFERS_VALUE_OUT
    after: WRITES_USER_BALANCE
```

---

## 7. Pattern Design Methodology

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

## 8. Complete Pattern Example

```yaml
id: auth-001
name: Unprotected Privileged State Write
description: |
  ## What This Detects
  Public/external functions that modify privileged state (owner, admin,
  roles) without access control, allowing privilege escalation.

  ## Why It's Dangerous
  Attackers can call these functions to:
  - Change contract ownership
  - Grant themselves admin roles
  - Drain funds by changing withdrawal addresses

  ## Real-World Examples
  - Poly Network ($611M, 2021) - Exposed keeper modification

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
    preconditions:
      - Function is public/external
      - No access control present
    steps:
      - Identify unprotected privileged function
      - Call function with attacker address
      - Attacker gains owner privileges
    impact: Complete protocol takeover

verification_steps:
  - Verify function is externally callable
  - Confirm no access control in modifiers or body
  - Check if intentional initialization pattern
  - Verify state variable is truly privileged

fix_recommendations:
  - name: Add onlyOwner Modifier
    description: Restrict to current owner
    example: |
      function setOwner(address newOwner) external onlyOwner {
          owner = newOwner;
      }

related_patterns:
  - auth-002
  - auth-006

owasp_mapping:
  - SC01

cwe_mapping:
  - CWE-284
  - CWE-285

test_coverage:
  projects: [defi-lending, governance-dao]
  true_positives: 8
  true_negatives: 5
  precision: 0.89
  recall: 0.92
  variation_score: 0.88
  last_tested: "2025-01-15"
```

---

## 9. Severity Guidelines

| Severity | Criteria | Examples |
|----------|----------|----------|
| **critical** | Direct fund loss, no conditions | Unprotected withdrawAll |
| **high** | Fund loss with conditions | CEI violation without guard |
| **medium** | Partial impact or difficult | Missing slippage check |
| **low** | Edge case or minor | Deprecated function use |
| **info** | Best practice | Missing events |

---

## 10. Quality Checklist

Before finalizing any pattern:

### Accuracy
- [ ] Core condition is SEMANTIC, not syntactic
- [ ] At least one `none` condition excludes safe patterns
- [ ] No reliance on naming conventions
- [ ] Visibility appropriately constrained
- [ ] Severity matches actual risk

### Completeness
- [ ] Description explains "why" not just "what"
- [ ] Attack scenarios documented
- [ ] Verification steps included
- [ ] Fix recommendations provided
- [ ] Real-world examples referenced

### Metadata
- [ ] ID follows `<lens>-<number>` convention
- [ ] Correct lens category
- [ ] OWASP/CWE mappings included
- [ ] Related patterns linked

### Implementation-Agnostic
- [ ] Would survive code renaming
- [ ] Works with owner/admin/controller naming
- [ ] Works with different modifier patterns
- [ ] Works with inheritance variations

---

## 11. Running Patterns

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

## 12. Pattern Migration (v1 → v2)

### Before (Name-dependent)

```yaml
# BAD: Relies on naming
match:
  all:
    - property: label
      op: regex
      value: ".*[Ww]ithdraw.*"
```

### After (Operation-based)

```yaml
# GOOD: Uses semantic operations
match:
  tier_a:
    all:
      - has_operation: TRANSFERS_VALUE_OUT
      - has_operation: WRITES_USER_BALANCE
```

---

## 13. Pattern Context Pack (PCP) v2

Pattern Context Pack (PCP) v2 provides deterministic, evidence-first context for agentic pattern discovery. PCPs are co-located with patterns at:

```
vulndocs/{category}/{subcategory}/patterns/{pattern-id}.pcp.yaml
```

### PCP v2 Design Principles

| Principle | Description |
|-----------|-------------|
| **Deterministic** | No RAG, no semantic search - context is predictable |
| **Evidence-First** | Every claim references explicit evidence IDs |
| **Unknown != Safe** | Missing signals = unknown, never assumed safe |
| **Graph-First** | Semantic operations describe behavior, not names |

### When to Create a PCP

Create a PCP v2 file when:

1. **High/critical severity patterns** - Required for reliable detection
2. **Multi-step exploits** - Ordering and preconditions matter
3. **Guard-dependent patterns** - Anti-signals and bypasses need documentation
4. **Economic context needed** - Value flows and incentives affect severity

### PCP v2 Required Fields

```yaml
# Minimum required for valid PCP v2
id: pcp-<pattern-id>          # Must start with pcp-
version: "2.0"                 # Must be 2.x
pattern_id: "<pattern-id>"     # Associated pattern
name: "<Pattern Name>"         # Human-readable
summary: "<Brief description>" # 1-2 sentences

determinism:
  no_rag: true                 # Must be true
  no_name_heuristics: true     # Must be true

op_signatures:
  required_ops:                # At least one required
    - "OPERATION_1"
```

### Evidence Gating for High/Critical Patterns

High and critical severity patterns should include:

1. **Witnesses** - Evidence that must exist for a match
2. **Negative witnesses** - Evidence that must NOT exist (guards)
3. **Anti-signals** - Guards/mitigations that negate the pattern
4. **Bypass notes** - How guards might be circumvented

```yaml
witness:
  minimal_required:
    - "EVD-12345678"           # Code location showing vulnerability
  negative_required:
    - "EVD-87654321"           # Guard presence invalidates match

anti_signals:
  - id: "guard.reentrancy"
    guard_type: "reentrancy_guard"
    severity: "critical"
    expected_context: "nonReentrant modifier present"
    bypass_notes:
      - "Guard only applies to one entry point"
      - "Cross-contract reentrancy may bypass"
```

### Unknowns Policy

Never infer safety from missing context:

```yaml
unknowns_policy:
  missing_required: "unknown"     # Default: mark as unknown
  missing_optional: "unknown"     # Not fail - avoid false negatives
  missing_anti_signal: "unknown"  # Guard absence != confirmed vulnerable
```

### PCP Lint Rules

PCPs are validated by `pcp_lint.py` during `vulndocs validate`. Key rules:

| Rule | Severity | Description |
|------|----------|-------------|
| PCP001 | ERROR | Missing required_ops |
| PCP010 | ERROR | no_rag must be true |
| PCP011 | ERROR | no_name_heuristics must be true |
| PCP012 | ERROR | Budget ordering: cheap < verify < deep |
| PCP020 | WARN | High/critical missing minimal_required witnesses |
| PCP021 | WARN | High/critical missing negative witnesses or anti-signals |
| PCP023 | WARN | Anti-signal without bypass notes |
| PCP040 | WARN | Unknowns policy not explicit |

### Running PCP Validation

```bash
# Validate all PCP files in vulndocs/
uv run alphaswarm vulndocs validate vulndocs/ --pcp

# Strict mode (warnings become errors)
uv run alphaswarm vulndocs validate vulndocs/ --pcp --strict
```

### PCP v2 Template

See: `vulndocs/.meta/templates/pattern_context_pack_v2.yaml`

Reference: [Pattern Context Pack v2 Specification](../reference/pattern-context-pack-v2.md)

---

## Related Documentation

- [Pattern Testing Guide](testing.md) - Test patterns and assign ratings
- [Property Reference](../reference/properties.md) - All 250+ properties
- [Operations Reference](../reference/operations.md) - 20 semantic operations
- [PCP v2 Specification](../reference/pattern-context-pack-v2.md) - Full PCP v2 schema
- [Pattern Template](../../vulndocs/.meta/templates/pattern.yaml) - Pattern YAML schema

---

*Version 3.0 | January 2026*
