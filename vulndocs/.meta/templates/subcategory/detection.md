# Detection: {{subcategory_name}}

## Graph-First Detection Strategy

> **CRITICAL:** Always use BSKG graph queries, NOT manual code reading.

### Primary Semantic Operations

| Operation | Relevance | Description |
|-----------|-----------|-------------|
| `{{OPERATION_1}}` | Critical | {{why this operation indicates vulnerability}} |
| `{{OPERATION_2}}` | High | {{why this operation indicates vulnerability}} |

### VQL Detection Queries

```vql
# Primary detection query
FIND functions WHERE
  {{primary_condition}} AND
  {{secondary_condition}} AND
  NOT {{guard_condition}}

# Refined detection
FIND functions WHERE
  has_operation: {{operation}} AND
  visibility IN [public, external] AND
  NOT has_access_gate
```

### Behavioral Signatures

**Vulnerable Sequence:**
```
{{operation_1}} -> {{operation_2}} -> {{operation_3}}
```

**Safe Sequence:**
```
{{guard}} -> {{operation_1}} -> {{operation_2}}
```

## Graph Signals

| Signal | Expected | Confidence | Notes |
|--------|----------|------------|-------|
| `{{property_1}}` | `{{value}}` | High | {{notes}} |
| `{{property_2}}` | `{{value}}` | Medium | {{notes}} |

## False Positive Indicators

- {{Condition that might trigger false positive}}
- {{Another false positive scenario}}

## Detection Confidence Levels

| Confidence | Conditions |
|------------|------------|
| **High** | {{all_critical_signals_present}} |
| **Medium** | {{some_signals_present}} |
| **Low** | {{minimal_signals_present}} |
