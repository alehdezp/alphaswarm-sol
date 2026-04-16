# VQL 2.0 Specification

**SQL-like Query Language for Vulnerability Knowledge Graphs**

---

## Query Types

| Type | Syntax | Use Case |
|------|--------|----------|
| `DESCRIBE` | `DESCRIBE TYPES` | Schema discovery |
| `FIND` | `FIND functions WHERE ...` | Simple node queries |
| `MATCH` | `MATCH (f:Function)-[...]->()` | Graph patterns |
| `FLOW` | `FLOW FROM ... TO ...` | Dataflow analysis |
| `PATTERN` | `PATTERN reentrancy-basic` | Vulnerability patterns |

---

## DESCRIBE - Schema Discovery

```sql
DESCRIBE TYPES              -- All node types
DESCRIBE PROPERTIES         -- All properties
DESCRIBE PROPERTIES FOR Function
DESCRIBE EDGES              -- Edge types
DESCRIBE PATTERNS           -- Vulnerability patterns
DESCRIBE LENSES             -- Security lenses
```

---

## FIND - Simple Queries

```sql
FIND functions
WHERE visibility IN ['public', 'external']
  AND writes_state
  AND NOT has_access_gate
RETURN id, label, visibility
LIMIT 20
```

**Operators:**

| Operator | Example |
|----------|---------|
| `=`, `!=` | `visibility = 'public'` |
| `>`, `<`, `>=`, `<=` | `complexity > 10` |
| `IN`, `NOT IN` | `visibility IN ['public', 'external']` |
| `CONTAINS` | `security_tags CONTAINS 'owner'` |
| `CONTAINS_ANY` | `tags CONTAINS_ANY ['owner', 'admin']` |
| `CONTAINS_ALL` | `tags CONTAINS_ALL ['owner', 'admin']` |
| `REGEX` | `label REGEX '^transfer'` |
| `AND`, `OR`, `NOT` | `writes_state AND NOT has_access_gate` |

---

## MATCH - Graph Patterns

```sql
-- Basic pattern
MATCH (f:Function)-[:WRITES_STATE]->(s:StateVariable)
WHERE f.visibility = 'public'
RETURN f.label, s.label

-- Variable-length paths
MATCH (f:Function)-[:CALLS_INTERNAL*1..3]->(target:Function)
WHERE target.writes_state
RETURN f, target

-- Pattern predicates
MATCH (f:Function)
WHERE (f)-[:WRITES_STATE]->(:StateVariable {security_tags: ['owner']})
  AND NOT (f)-[:USES_MODIFIER]->()
RETURN f
```

---

## FLOW - Dataflow Analysis

```sql
-- Forward flow
FLOW FROM (i:Input WHERE i.kind = 'parameter')
TO (s:StateVariable WHERE s.security_tags CONTAINS 'owner')
EXCLUDE SOURCES ['msg.sender']
RETURN PATHS

-- Backward flow
FLOW BACKWARD FROM (s:StateVariable WHERE s.label = 'owner')
TO ANY
MAX DEPTH 5
RETURN INFLUENCERS
```

---

## PATTERN - Vulnerability Patterns

```sql
PATTERN weak-access-control
LENS Authority
SEVERITY high
LIMIT 20
```

---

## WITH - Query Composition

```sql
WITH risky AS (
  FIND functions
  WHERE writes_state AND NOT has_access_gate
)
FIND functions IN risky
WHERE visibility = 'public'
RETURN *
```

---

## Result Modifiers

| Modifier | Description |
|----------|-------------|
| `LIMIT n` | Return at most n results |
| `OFFSET n` | Skip first n results |
| `ORDER BY field [ASC\|DESC]` | Sort results |
| `COMPACT` | Return only id, type, label |
| `EXPLAIN` | Show execution plan |
| `NO EVIDENCE` | Omit evidence payloads |

---

## Aggregations

```sql
FIND functions
GROUP BY visibility
RETURN visibility,
       COUNT(*) AS total,
       SUM(writes_state) AS writers
HAVING COUNT(*) > 5
ORDER BY total DESC
```

**Functions:** `COUNT`, `SUM`, `AVG`, `MAX`, `MIN`, `COLLECT`

---

## Common Queries

### Access Control

```sql
-- Unprotected state writes
FIND functions
WHERE visibility IN ['public', 'external']
  AND writes_state
  AND NOT has_access_gate

-- Privileged state without auth
MATCH (f:Function)-[:WRITES_STATE]->(s:StateVariable)
WHERE s.security_tags CONTAINS_ANY ['owner', 'admin']
  AND NOT f.has_access_gate
```

### Reentrancy

```sql
-- CEI violation
FIND functions
WHERE state_write_after_external_call
  AND NOT has_reentrancy_guard
```

### DoS

```sql
-- Unbounded loops
MATCH (f:Function)-[:FUNCTION_HAS_LOOP]->(l:Loop)
WHERE l.has_unbounded_loop
  AND NOT l.has_require_bounds

-- External calls in loops
MATCH (f:Function)-[:FUNCTION_HAS_LOOP]->(l:Loop)
WHERE l.external_calls_in_loop > 0
```

### Oracle

```sql
FIND functions
WHERE reads_oracle_price
  AND NOT has_staleness_check
```

### MEV

```sql
FIND functions
WHERE swap_like
  AND (risk_missing_slippage_parameter
       OR risk_missing_deadline_check)
```

---

## Error Recovery

VQL 2.0 provides helpful error messages:

```
Error: Unknown property 'visability' for type 'Function'
Did you mean: 'visibility' (confidence: 0.95)
Auto-fix: FIND functions WHERE visibility = public
```

---

## LLM Decision Tree

```
What do I need?
├─ Schema discovery? → DESCRIBE
├─ Simple node filter? → FIND
├─ Relationship traversal? → MATCH
├─ Dataflow tracking? → FLOW
└─ Known vulnerability? → PATTERN
```

---

## Performance Tips

1. Use `LIMIT` during exploration
2. Use `RETURN` to select only needed fields
3. Limit path depth in variable-length patterns
4. Use `COMPACT` for overview queries
5. Start with `FIND`, upgrade to `MATCH` if needed

---

*See [Query Guide](../guides/queries.md) for examples.*
*See [Properties Reference](properties.md) for available properties.*
