# VulnDocs Basics

**Getting started with the VulnDocs knowledge framework.**

**For advanced topics (validation pipeline, authoring skills), see [VulnDocs Authoring Guide](vulndocs-authoring.md).**

---

## Overview

> **v6.0 Status:** 106 VulnDocs index entries exist, 17 currently fail validation, and only 5 have associated patterns. See `.planning/STATE.md` for details.

VulnDocs is a structured knowledge system that unifies vulnerability documentation, pattern definitions, and test specifications into a single source of truth.

### Purpose

- **Single Source of Truth**: All vulnerability knowledge lives in `vulndocs/`
- **LLM-Optimized**: Structured YAML with rich context
- **Graph-First**: Emphasizes BSKG semantic operations
- **Test-Driven**: Each vulnerability includes test cases

### Relationship to Patterns

Every pattern in `patterns/*.yaml` MUST reference a vulndoc entry:

```yaml
id: reentrancy-classic
name: Classic Reentrancy
vulndoc: vulndocs/reentrancy-classic/
```

---

## Folder Structure

```
vulndocs/
├── .meta/                        # Framework metadata
│   ├── templates/                # Skeleton templates
│   └── instructions/             # Authoring guidance
├── reentrancy-classic/           # Example vulnerability
│   ├── index.yaml                # Main entry (REQUIRED)
│   ├── pattern.yaml              # Pattern definition (optional)
│   ├── tests/                    # Test files (optional)
│   └── research/                 # Supporting materials (optional)
```

### Required vs Optional

**Required:**
- `index.yaml` - Main vulnerability entry

**Optional but Recommended:**
- `pattern.yaml` - Pattern definition
- `tests/` - Test files
- `research/` - Source materials

---

## Creating New Vulnerabilities

### Method 1: Using Agent Skill (Recommended)

```bash
/vrs-add-vulnerability
```

The agent will create folder structure, generate index.yaml, and scaffold tests.

### Method 2: Using Tool-Level CLI (Dev/CI)

```bash
uv run alphaswarm vulndocs scaffold weak-randomness \
  --name "Weak Randomness" \
  --severity high \
  --category randomness
```

---

## Required Fields in index.yaml

```yaml
id: weak-randomness                    # Unique identifier
name: Weak Randomness                   # Human-readable name
category: randomness                    # Category tag
severity: high                          # critical | high | medium | low
status: draft                           # draft | validated | excellent

description: |
  Clear explanation of the vulnerability

detection_strategy:
  graph_query: |                        # BSKG query (REQUIRED)
    FIND functions WHERE
      calls_blockhash OR calls_timestamp

  semantic_operations:                  # Operations to detect (REQUIRED)
    - READS_BLOCKHASH
    - READS_TIMESTAMP

  false_positive_filters:               # How to reduce FPs
    - Check if randomness source is external oracle

related_patterns:                       # Links to pattern files
  - id: weak-randomness-blockhash
    path: patterns/randomness/weak-randomness-blockhash.yaml
```

---

## Validation Levels

| Level | Requirements | Use Case |
|-------|--------------|----------|
| **MINIMAL** | id, name, category, description, detection_strategy | Initial draft |
| **STANDARD** | + false_positive_filters, related_patterns | Ready for testing |
| **COMPLETE** | + real_world_examples, test_coverage | Validated pattern |
| **EXCELLENT** | + precision >= 0.90, 3+ projects | Production-ready |

### Check Level

```bash
uv run alphaswarm vulndocs info vulndocs/weak-randomness/
```

---

## Tool-Level Commands (Dev/CI)

```bash
# Validate all entries
uv run alphaswarm vulndocs validate vulndocs/

# List entries
uv run alphaswarm vulndocs list
uv run alphaswarm vulndocs list --status validated

# Get info
uv run alphaswarm vulndocs info vulndocs/reentrancy-classic/
```

---

## Best Practices

### Graph-First Approach

**DO**: Start with BSKG semantic operations
```yaml
detection_strategy:
  semantic_operations:
    - TRANSFERS_VALUE_OUT
    - WRITES_USER_BALANCE
  graph_query: |
    FIND functions WHERE
      has_operation(TRANSFERS_VALUE_OUT)
```

**DON'T**: Rely on name heuristics
```yaml
# AVOID THIS:
detection_strategy:
  description: "Look for functions with 'withdraw' in the name"
```

### Semantic Operations

**Value:** `TRANSFERS_VALUE_OUT`, `READS_USER_BALANCE`, `WRITES_USER_BALANCE`
**Access:** `CHECKS_PERMISSION`, `MODIFIES_OWNER`, `MODIFIES_ROLES`
**External:** `CALLS_EXTERNAL`, `CALLS_UNTRUSTED`, `READS_EXTERNAL_VALUE`

See `docs/reference/operations.md` for complete list.

---

## Related Documentation

- [VulnDocs Authoring Guide](vulndocs-authoring.md) - Validation pipeline, skills
- [Pattern Basics](patterns-basics.md) - Creating patterns
- [Operations Reference](../reference/operations.md) - Semantic operations

---

*Updated February 2026*
