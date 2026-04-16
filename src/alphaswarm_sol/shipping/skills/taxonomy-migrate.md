---
name: vrs-taxonomy-migrate
description: |
  Taxonomy migration skill for VRS ops registry validation. Validates pattern and VQL usage against the canonical ops registry, migrating deprecated aliases.

  Invoke when:
  - Validating patterns against ops registry
  - Migrating deprecated operation names
  - Checking VQL queries for legacy aliases
  - Auditing external tool output compatibility (SARIF)

slash_command: vrs:taxonomy-migrate
context: fork
disable-model-invocation: false

allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(alphaswarm*)
---

# VRS Taxonomy Migrate Skill

You are the **VRS Taxonomy Migrate** skill, responsible for ensuring consistent operation naming across patterns, VQL queries, and external tool outputs using the canonical ops registry.

## How to Invoke

```bash
/vrs-taxonomy-migrate --validate patterns/
/vrs-taxonomy-migrate --migrate reentrancy-classic.yaml
/vrs-taxonomy-migrate --check-sarif findings.sarif
/vrs-taxonomy-migrate --list-deprecated
```

---

## Purpose

Phase 5.9 establishes a unified ops taxonomy registry that maps:

1. **SemanticOperation** - Core ops (e.g., `TRANSFERS_VALUE_OUT`)
2. **EdgeType** - Graph edge types (e.g., `CALLS_EXTERNAL`)
3. **Pattern tags** - Pattern-specific identifiers
4. **Legacy aliases** - Deprecated names with migration paths

This skill validates and migrates usage to prevent taxonomy drift.

---

## Registry Structure

### Canonical Operations

```yaml
ops_registry:
  version: "2.0.0"
  operations:
    TRANSFERS_VALUE_OUT:
      category: value
      description: "Transfers ETH or tokens out"
      edge_type: SENDS_VALUE
      aliases: ["TRANSFERS_ETH", "TRANSFERS_TOKENS", "SENDS_ETH"]
      deprecated_in: null

    WRITES_USER_BALANCE:
      category: state
      description: "Writes to user balance mapping"
      edge_type: WRITES_STATE
      aliases: ["MODIFIES_BALANCE", "UPDATES_BALANCE"]
      deprecated_in: null

    CALLS_EXTERNAL:
      category: external
      description: "Makes external call to another contract"
      edge_type: CALLS_EXTERNAL
      aliases: ["EXTERNAL_CALL", "CALLS_UNTRUSTED"]
      deprecated_in: null
```

### Deprecated Aliases

```yaml
deprecated:
  TRANSFERS_ETH:
    canonical: TRANSFERS_VALUE_OUT
    deprecated_in: "1.5.0"
    sunset_in: "2.0.0"
    migration: "Replace with TRANSFERS_VALUE_OUT in patterns and VQL"

  EXTERNAL_CALL:
    canonical: CALLS_EXTERNAL
    deprecated_in: "1.5.0"
    sunset_in: "2.0.0"
    migration: "Replace with CALLS_EXTERNAL"
```

---

## Migration Workflow

### Step 1: Validation

Check patterns/VQL for deprecated operations:

```bash
/vrs-taxonomy-migrate --validate vulndocs/
```

Output:
```markdown
## Validation Results

### Deprecated Usage Found
| File | Line | Operation | Canonical | Status |
|------|------|-----------|-----------|--------|
| reentrancy/patterns/classic.yaml | 12 | TRANSFERS_ETH | TRANSFERS_VALUE_OUT | deprecated |
| access-control/patterns/missing.yaml | 8 | EXTERNAL_CALL | CALLS_EXTERNAL | deprecated |

### Unknown Operations
| File | Line | Operation | Suggestion |
|------|------|-----------|------------|
| custom/patterns/test.yaml | 15 | SENDS_MONEY | TRANSFERS_VALUE_OUT |
```

### Step 2: Migration

Apply migrations automatically or preview changes:

```bash
# Preview changes
/vrs-taxonomy-migrate --migrate vulndocs/ --dry-run

# Apply changes
/vrs-taxonomy-migrate --migrate vulndocs/
```

Migration output:
```markdown
## Migration Report

### Changes Applied
| File | Change |
|------|--------|
| reentrancy/patterns/classic.yaml | TRANSFERS_ETH -> TRANSFERS_VALUE_OUT |
| access-control/patterns/missing.yaml | EXTERNAL_CALL -> CALLS_EXTERNAL |

### Manual Review Required
| File | Issue |
|------|-------|
| custom/patterns/test.yaml | Unknown operation SENDS_MONEY - suggest TRANSFERS_VALUE_OUT |
```

### Step 3: Verification

Confirm all patterns use canonical operations:

```bash
/vrs-taxonomy-migrate --verify vulndocs/
```

---

## SARIF Compatibility

External tools (Slither, Aderyn, Mythril) emit findings with their own taxonomies. This skill maps tool-specific tags to canonical operations:

```yaml
sarif_mapping:
  slither:
    reentrancy-eth:
      operations: [TRANSFERS_VALUE_OUT, WRITES_USER_BALANCE]
      pattern_id: reentrancy-classic

    unprotected-upgrade:
      operations: [MODIFIES_CRITICAL_STATE]
      pattern_id: unprotected-upgrade

  aderyn:
    state-variable-after-external-call:
      operations: [CALLS_EXTERNAL, WRITES_USER_BALANCE]
      pattern_id: reentrancy-state
```

### Validate SARIF Mappings

```bash
/vrs-taxonomy-migrate --check-sarif slither-findings.sarif
```

Output:
```markdown
## SARIF Mapping Results

### Mapped Findings
| Finding | Tool Rule | Operations | Pattern |
|---------|-----------|------------|---------|
| F-001 | reentrancy-eth | TRANSFERS_VALUE_OUT, WRITES_USER_BALANCE | reentrancy-classic |
| F-002 | arbitrary-send | TRANSFERS_VALUE_OUT | arbitrary-send-eth |

### Unmapped Findings
| Finding | Tool Rule | Reason |
|---------|-----------|--------|
| F-003 | custom-rule-123 | No mapping in sarif_mapping |
```

---

## Registry Commands

### List Deprecated

```bash
/vrs-taxonomy-migrate --list-deprecated
```

Output:
```markdown
## Deprecated Operations

| Deprecated | Canonical | Deprecated In | Sunset In | Usage Count |
|------------|-----------|---------------|-----------|-------------|
| TRANSFERS_ETH | TRANSFERS_VALUE_OUT | 1.5.0 | 2.0.0 | 12 patterns |
| EXTERNAL_CALL | CALLS_EXTERNAL | 1.5.0 | 2.0.0 | 8 patterns |
| MODIFIES_BALANCE | WRITES_USER_BALANCE | 1.6.0 | 2.1.0 | 3 patterns |
```

### List All Operations

```bash
/vrs-taxonomy-migrate --list-all
```

Output by category:
```markdown
## Operations Registry

### Value Operations
| Operation | Description | Edge Type |
|-----------|-------------|-----------|
| TRANSFERS_VALUE_OUT | Transfers ETH or tokens out | SENDS_VALUE |
| READS_USER_BALANCE | Reads user balance mapping | READS_STATE |
| WRITES_USER_BALANCE | Writes to user balance mapping | WRITES_STATE |

### External Operations
| Operation | Description | Edge Type |
|-----------|-------------|-----------|
| CALLS_EXTERNAL | Makes external call | CALLS_EXTERNAL |
| CALLS_UNTRUSTED | Calls user-controlled address | CALLS_UNTRUSTED |
| READS_EXTERNAL_VALUE | Reads from external source | READS_EXTERNAL |
```

---

## Sunset Policy

Operations follow a deprecation lifecycle:

| Phase | Duration | Effect |
|-------|----------|--------|
| Active | Indefinite | Full support |
| Deprecated | 2 minor versions | Warning on use, alias works |
| Sunset | 1 minor version | Error on use, migration required |
| Removed | After sunset | Not recognized |

### Sunset Enforcement

When sunset_in version is reached:
- Validation fails (not just warns)
- Migration is required before pattern execution
- SARIF mappings using sunset ops fail

---

## Integration with Contract v2

Taxonomy validation is part of v2 contract compliance:

```yaml
interface_version: "2.0.0"
taxonomy_version: "2.0.0"
findings:
  - operations_used:
      - TRANSFERS_VALUE_OUT  # Canonical
      - WRITES_USER_BALANCE  # Canonical
    deprecated_aliases: []  # Must be empty for v2 compliance
```

Non-compliant output:
```yaml
# FAILS CONTRACT VALIDATION
findings:
  - operations_used:
      - TRANSFERS_ETH  # DEPRECATED - fails v2 compliance
```

---

## Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| `TX-001` | Unknown operation | Check spelling, use registry |
| `TX-002` | Deprecated operation | Migrate to canonical |
| `TX-003` | Sunset operation | Immediate migration required |
| `TX-004` | SARIF mapping missing | Add mapping to sarif_mapping |
| `TX-005` | Registry version mismatch | Update registry |

---

## When to Invoke

Invoke this skill when:
- **Pattern authoring**: Validate new patterns use canonical ops
- **Pattern update**: Migrate deprecated ops in existing patterns
- **Tool integration**: Map SARIF findings to canonical ops
- **Pre-release**: Audit all patterns before release
- **CI pipeline**: Block deprecated ops in PR checks

---

## Related Skills

| Skill | Purpose |
|-------|---------|
| `/vrs-graph-contract-validate` | Schema/evidence validation |
| `/vrs-slice-unify` | Unified slicing pipeline |
| `/vrs-evidence-audit` | Evidence reference validation |

---

## Write Boundaries

This skill is restricted to writing in:
- `.claude/vrs/` - VRS working directory
- `.beads/` - Bead storage directory

All other directories are read-only.

---

## Notes

- Registry is the single source of truth for operation names
- All patterns must use canonical operations for v2 compliance
- SARIF mappings enable cross-tool deduplication
- Deprecated aliases emit warnings, sunset aliases emit errors
- Migration is non-destructive (creates backup before changes)
- This skill CAN be invoked by orchestrators (disable-model-invocation: false)
