# Query Guide

**How to Query the AlphaSwarm.sol Knowledge Graph**

---

## Query Types

In production, Claude Code executes graph queries through `/vrs-*` workflows (for example `/vrs-audit` and `/vrs-investigate`). CLI examples below are tool-level commands for development/debug/CI.

| Type | Syntax | Use Case |
|------|--------|----------|
| **Natural Language** | `"public functions without access control"` | Quick exploration |
| **VQL** | `FIND functions WHERE visibility = public` | Structured queries |
| **Pattern** | `pattern:weak-access-control` | Known vulnerabilities |
| **JSON** | `{"query_kind": "logic", ...}` | Full control |

---

## Natural Language Queries

Simple English queries that get parsed to structured format.

```bash
# Find public functions
uv run alphaswarm query "public functions"

# Add conditions
uv run alphaswarm query "public functions that write state"

# Exclude conditions
uv run alphaswarm query "public functions without access control"
```

### Supported Aliases

| Natural | Property |
|---------|----------|
| auth gate | has_access_gate |
| state write | writes_state |
| external call | has_external_calls |
| reentrancy guard | has_reentrancy_guard |
| unbounded loop | has_unbounded_loop |

---

## VQL (VKG Query Language)

SQL-like syntax for structured queries.

### Basic FIND

```sql
-- Find all public functions
FIND functions WHERE visibility = public

-- Multiple conditions (AND implicit)
FIND functions
WHERE visibility = public
  AND writes_state
  AND NOT has_access_gate

-- Explicit AND/OR
FIND functions
WHERE visibility IN ['public', 'external']
  AND (writes_state OR has_external_calls)

-- Limit results
FIND functions WHERE writes_state LIMIT 20
```

### Operators

| Operator | Example |
|----------|---------|
| `=` | `visibility = 'public'` |
| `!=` | `visibility != 'internal'` |
| `IN` | `visibility IN ['public', 'external']` |
| `NOT IN` | `visibility NOT IN ['private']` |
| `>`, `<`, `>=`, `<=` | `complexity > 10` |
| `CONTAINS` | `security_tags CONTAINS 'owner'` |
| `CONTAINS_ANY` | `tags CONTAINS_ANY ['owner', 'admin']` |
| `REGEX` | `label REGEX '^transfer'` |

### MATCH (Graph Patterns)

Traverse relationships between nodes.

```sql
-- Function writes to state variable
MATCH (f:Function)-[:WRITES_STATE]->(s:StateVariable)
WHERE f.visibility = 'public'
RETURN f.label, s.label

-- Multi-hop traversal
MATCH (f:Function)-[:CALLS_INTERNAL*1..3]->(target:Function)
WHERE target.writes_state
RETURN f, target

-- Pattern predicates
MATCH (f:Function)
WHERE (f)-[:WRITES_STATE]->(:StateVariable {security_tags: ['owner']})
  AND NOT (f)-[:USES_MODIFIER]->()
RETURN f
```

### FLOW (Dataflow Analysis)

Track taint from sources to sinks.

```sql
-- Input to state variable
FLOW FROM (i:Input WHERE i.kind = 'parameter')
TO (s:StateVariable)
RETURN PATHS

-- Exclude trusted sources
FLOW FROM (i:Input)
TO (s:StateVariable WHERE s.security_tags CONTAINS 'owner')
EXCLUDE SOURCES ['msg.sender']
RETURN UNSAFE PATHS

-- Backward flow
FLOW BACKWARD FROM (s:StateVariable WHERE s.label = 'owner')
TO ANY
MAX DEPTH 5
RETURN INFLUENCERS
```

### WITH (Composition)

Build complex multi-stage queries.

```sql
WITH risky AS (
  FIND functions
  WHERE writes_state AND NOT has_access_gate
)
FIND functions IN risky
WHERE visibility = 'public'
RETURN *
```

### DESCRIBE (Schema Discovery)

Explore what's available in the graph.

```sql
DESCRIBE TYPES           -- Available node types
DESCRIBE PROPERTIES FOR Function  -- Properties for type
DESCRIBE EDGES           -- Edge types
DESCRIBE PATTERNS        -- Vulnerability patterns
```

---

## Pattern Queries

Run predefined vulnerability patterns.

```bash
# Single pattern
uv run alphaswarm query "pattern:weak-access-control"

# By lens
uv run alphaswarm query "lens:Authority"

# With severity filter
uv run alphaswarm query "lens:Reentrancy severity high"
```

### Available Lenses

| Lens | Patterns |
|------|----------|
| Authority | weak-access-control, tx-origin-auth, arbitrary-delegatecall |
| Reentrancy | reentrancy-basic, cross-function-reentrancy |
| DoS | unbounded-loop, external-call-in-loop, strict-equality |
| Oracle | missing-staleness, missing-sequencer-check |
| MEV | missing-slippage, missing-deadline |
| Crypto | missing-chainid, signature-malleability |

---

## JSON Queries

Full control for programmatic access.

### Logic Query

```json
{
  "query_kind": "logic",
  "node_types": ["Function"],
  "match": {
    "all": [
      {"property": "visibility", "op": "in", "value": ["public", "external"]},
      {"property": "writes_state", "op": "eq", "value": true}
    ],
    "any": [],
    "none": [
      {"property": "has_access_gate", "op": "eq", "value": true}
    ]
  },
  "limit": 50
}
```

### Flow Query

```json
{
  "query_kind": "flow",
  "node_types": ["Function"],
  "properties": {"visibility": "public"},
  "flow": {
    "from_kinds": ["parameter", "env"],
    "exclude_sources": ["msg.sender"],
    "target_type": "StateVariable",
    "edge_type": "INPUT_TAINTS_STATE"
  }
}
```

---

## Output Modes

```bash
--compact      # Minimal output (10x smaller)
--explain      # Include match reasoning
--no-evidence  # Drop file paths
--show-intent  # Show parsed intent (debugging)
```

### Output Size Comparison

| Mode | Size/Function | Use Case |
|------|---------------|----------|
| Full | ~5KB | Human review |
| Compact | ~0.5KB | LLM context |
| No-evidence | ~2KB | Quick scans |

---

## Common Vulnerability Queries

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

-- Cross-function
MATCH (f1:Function)-[:CALLS_EXTERNAL]->(ext),
      (f2:Function)
WHERE f1.id != f2.id
  AND f2.writes_state
  AND NOT f1.has_reentrancy_guard
```

### DoS

```sql
-- Unbounded loops
FIND functions
WHERE has_unbounded_loop
  AND NOT has_require_bounds

-- External calls in loops
MATCH (f:Function)-[:FUNCTION_HAS_LOOP]->(l:Loop)
WHERE l.external_calls_in_loop > 0
```

### Oracle

```sql
-- Missing staleness check
FIND functions
WHERE reads_oracle_price
  AND NOT has_staleness_check
```

### MEV

```sql
-- Missing protection
FIND functions
WHERE swap_like
  AND (risk_missing_slippage_parameter OR risk_missing_deadline_check)
```

---

## Performance Tips

1. **Use LIMIT during exploration**
   ```sql
   FIND functions WHERE writes_state LIMIT 10
   ```

2. **Select only needed fields**
   ```sql
   RETURN id, label, visibility
   ```

3. **Use EXISTS for large sets**
   ```sql
   WHERE EXISTS (MATCH (f)-[:WRITES_STATE]->())
   ```

4. **Limit path depth**
   ```sql
   MATCH (f)-[:CALLS*1..3]->(target)  -- Not *
   ```

---

## LLM Query Construction

### Decision Flow

```
What do I need?
├─ Schema discovery? → DESCRIBE
├─ Simple node filter? → FIND
├─ Relationship traversal? → MATCH
├─ Dataflow tracking? → FLOW
└─ Known vulnerability? → PATTERN
```

### Checklist

- [ ] Correct query type?
- [ ] Properties spelled correctly?
- [ ] WHERE clause present?
- [ ] LIMIT for large results?
- [ ] RETURN for specific fields?
- [ ] Operators correct (IN vs =)?

---

*See [Pattern Authoring](patterns.md) for creating custom patterns.*
*See [Pattern Authoring](patterns.md) to create custom patterns.*
