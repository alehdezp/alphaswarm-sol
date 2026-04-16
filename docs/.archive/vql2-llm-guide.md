# VQL 2.0 - LLM Query Construction Guide

**Purpose**: This guide teaches LLMs and AI agents how to construct powerful, reliable VQL 2.0 queries for vulnerability analysis in the AlphaSwarm.sol system.

## Quick Start for LLMs

### Query Selection Flow Chart

```
START: What do I need to find?
│
├─ Need schema/available options?
│  └─> Use DESCRIBE query
│
├─ Looking for single node type with simple filters?
│  └─> Use FIND query
│
├─ Need to traverse relationships between nodes?
│  └─> Use MATCH query
│
├─ Tracking data flow (taint analysis)?
│  └─> Use FLOW query
│
└─ Checking for known vulnerability pattern?
   └─> Use PATTERN query
```

## Progressive Learning Path

### Level 1: Beginner - DESCRIBE Queries

**Use when**: You don't know what's available in the graph.

```vql
-- Discover available node types
DESCRIBE TYPES

-- See all properties for a specific node type
DESCRIBE PROPERTIES FOR Function

-- View available edge types
DESCRIBE EDGES

-- See available vulnerability patterns
DESCRIBE PATTERNS

-- Get complete schema
DESCRIBE SCHEMA
```

**LLM Tip**: Always start with DESCRIBE if you're uncertain about available properties or types.

### Level 2: Beginner - Simple FIND

**Use when**: Looking for nodes of a single type with property filters.

```vql
-- Basic syntax
FIND <node_type> WHERE <conditions>

-- Example: Find all public functions
FIND functions WHERE visibility = public

-- With multiple conditions (AND is implicit)
FIND functions
WHERE visibility = public
  AND writes_state

-- With explicit AND/OR
FIND functions
WHERE visibility IN ['public', 'external']
  AND writes_state
  AND NOT has_access_gate

-- Limit results
FIND functions
WHERE writes_state
LIMIT 20
```

**LLM Decision Points**:
1. Do I need just one node type? → Yes? Use FIND
2. Are my conditions simple property checks? → Yes? Use FIND
3. Do I need to traverse relationships? → No? Use FIND

### Level 3: Intermediate - FIND with RETURN

**Use when**: You want to reduce token usage by selecting specific fields.

```vql
-- Select specific fields
FIND functions
WHERE visibility = public AND writes_state
RETURN id, label, visibility

-- Use aliases for clarity
FIND functions
WHERE NOT has_access_gate
RETURN id, label, has_access_gate AS protected

-- Return all fields (default if RETURN omitted)
FIND functions WHERE writes_state
RETURN *
```

**Token Optimization Strategy**:
- Use `RETURN id, label` for just identifiers (minimal tokens)
- Use `RETURN id, label, <key_properties>` for specific analysis
- Use `RETURN *` only when you need everything
- Use `COMPACT` option for absolute minimum: `FIND functions COMPACT`

### Level 4: Intermediate - Filtering Mastery

**Operators**: `=`, `!=`, `>`, `<`, `>=`, `<=`, `IN`, `NOT IN`, `CONTAINS`, `CONTAINS_ANY`, `CONTAINS_ALL`, `REGEX`, `LIKE`

```vql
-- Equality
WHERE visibility = 'public'

-- Inequality
WHERE visibility != 'internal'

-- Set membership
WHERE visibility IN ['public', 'external']

-- Set exclusion
WHERE visibility NOT IN ['internal', 'private']

-- Numeric comparison
WHERE complexity > 10

-- Array operations
WHERE security_tags CONTAINS 'owner'
WHERE security_tags CONTAINS_ANY ['owner', 'admin', 'role']
WHERE security_tags CONTAINS_ALL ['owner', 'initialized']

-- Pattern matching
WHERE label REGEX '^(mint|burn|transfer)'
WHERE label LIKE 'transfer%'

-- Boolean checks
WHERE writes_state
WHERE NOT has_access_gate

-- Compound conditions
WHERE visibility = 'public'
  AND writes_state
  AND NOT (has_access_gate OR uses_msg_sender)
```

**Negation Patterns**:
```vql
-- Negate single condition
WHERE NOT has_access_gate

-- Negate compound condition
WHERE NOT (is_view OR is_pure)

-- Negate set membership
WHERE visibility NOT IN ['internal', 'private']

-- Negate existence (requires EXISTS - see Level 5)
WHERE NOT EXISTS (...)
```

### Level 5: Advanced - MATCH (Graph Patterns)

**Use when**: Relationships between nodes matter.

```vql
-- Basic pattern: Function writes to StateVariable
MATCH (f:Function)-[:WRITES_STATE]->(s:StateVariable)
WHERE f.visibility = 'public'
RETURN f.label, s.label

-- Pattern components:
-- (f:Function)        - Node pattern: variable 'f' of type 'Function'
-- -[:WRITES_STATE]->  - Relationship pattern: directed edge of type WRITES_STATE
-- (s:StateVariable)   - Target node: variable 's' of type 'StateVariable'

-- Multiple patterns (AND)
MATCH (f:Function)-[:WRITES_STATE]->(s),
      (f)-[:CALLS_EXTERNAL]->(ext)
WHERE NOT (f)-[:USES_MODIFIER]->()
RETURN f

-- Multi-hop pattern
MATCH (f:Function)-[:CALLS_EXTERNAL]->(ext)-[:WRITES_STATE]->(s)
RETURN f.label, ext.label, s.label

-- Variable-length paths
MATCH (f:Function)-[:CALLS_INTERNAL*1..3]->(target:Function)
WHERE f.visibility = 'public' AND target.writes_state
RETURN f, target, LENGTH(PATH) AS depth

-- Named paths
MATCH path = (f:Function)-[:CALLS_EXTERNAL*]->(target)
WHERE ALL(node IN NODES(path) WHERE node.type = 'Function')
RETURN path, LENGTH(path)

-- Optional patterns (may not exist)
MATCH (f:Function)
OPTIONAL MATCH (f)-[:USES_MODIFIER]->(m:Modifier)
WHERE f.writes_state
RETURN f, m

-- Pattern predicates in WHERE
MATCH (f:Function)
WHERE (f)-[:WRITES_STATE]->(:StateVariable {security_tags: ['owner']})
  AND NOT (f)-[:USES_MODIFIER]->()
RETURN f
```

**MATCH Decision Guide**:
1. Need to follow edges? → Use MATCH
2. Care about which nodes are connected? → Use MATCH
3. Need multi-hop traversal? → Use MATCH with variable-length paths
4. Pattern may not exist? → Use OPTIONAL MATCH

### Level 6: Advanced - FLOW (Dataflow Analysis)

**Use when**: Tracking how data flows from sources to sinks (taint analysis).

```vql
-- Basic flow: Input to StateVariable
FLOW FROM (i:Input WHERE i.kind = 'parameter')
TO (s:StateVariable)
RETURN PATHS

-- Flow with filtering
FLOW FROM (i:Input WHERE i.kind = 'parameter')
TO (s:StateVariable WHERE s.security_tags CONTAINS 'owner')
EXCLUDE SOURCES ['msg.sender']
RETURN SOURCES, SINKS, PATHS

-- Flow with sanitizer requirements
FLOW FROM (i:Input)
TO (s:StateVariable)
REQUIRE ALL PATHS PASS (
  EXISTS (f:Function WHERE f.has_require_bounds)
)
RETURN UNSAFE PATHS

-- Backward flow (what influences this state?)
FLOW BACKWARD FROM (s:StateVariable WHERE s.label = 'owner')
TO ANY
MAX DEPTH 5
RETURN INFLUENCERS

-- Multi-source flow
FLOW FROM (
  (i:Input WHERE i.kind IN ['parameter', 'env'])
  UNION
  (call:ExternalCallSite)
)
TO (s:StateVariable)
RETURN TAINTED FUNCTIONS
```

**FLOW Special Returns**:
- `RETURN SOURCES` - Show taint sources
- `RETURN SINKS` - Show taint sinks
- `RETURN PATHS` - Show complete taint paths
- `RETURN TAINTED FUNCTIONS` - Show all tainted functions
- `RETURN UNSAFE PATHS` - Show paths that fail sanitizer checks
- `RETURN INFLUENCERS` - Show what influences a variable (backward flow)

### Level 7: Expert - WITH (Query Composition)

**Use when**: Building complex multi-stage analysis.

```vql
-- Basic WITH (Common Table Expression)
WITH risky AS (
  FIND functions
  WHERE writes_state AND NOT has_access_gate
)
FIND functions IN risky
WHERE visibility = 'public'
RETURN *

-- Multiple CTEs
WITH public_writers AS (
  FIND functions
  WHERE visibility = 'public' AND writes_state
),
critical_state AS (
  FIND state_variables
  WHERE security_tags CONTAINS_ANY ['owner', 'admin', 'implementation']
)
MATCH (f:Function IN public_writers)-[:WRITES_STATE]->(s:StateVariable IN critical_state)
RETURN f.label, s.label

-- Chaining different query types
WITH tainted AS (
  FLOW FROM (i:Input) TO (s:StateVariable)
  RETURN TAINTED FUNCTIONS
)
MATCH (f:Function IN tainted)-[:CALLS_EXTERNAL]->(ext)
WHERE ext.transfers_value
RETURN f, ext
```

**WITH Best Practices**:
1. Use descriptive CTE names (e.g., `risky_functions`, not `temp1`)
2. Break complex queries into logical stages
3. Reuse CTEs to avoid duplication
4. Each CTE should have a clear purpose

### Level 8: Expert - Aggregations

**Use when**: Need to count, sum, or group results.

```vql
-- Simple count
FIND functions
RETURN COUNT(*) AS total

-- Group by property
FIND functions
GROUP BY visibility
RETURN visibility, COUNT(*) AS total

-- Multiple aggregations
FIND functions
GROUP BY visibility
RETURN visibility,
       COUNT(*) AS total,
       SUM(writes_state) AS writers,
       AVG(complexity) AS avg_complexity

-- Filter aggregated results with HAVING
FIND functions
GROUP BY visibility
RETURN visibility, COUNT(*) AS total
HAVING COUNT(*) > 5
ORDER BY total DESC

-- Aggregation functions
COUNT(*)              -- Count all results
COUNT(field)          -- Count non-null values
SUM(field)            -- Sum numeric values
AVG(field)            -- Average numeric values
MAX(field)            -- Maximum value
MIN(field)            -- Minimum value
COLLECT(field)        -- Collect values into array
```

### Level 9: Expert - Subqueries

**Use when**: Need to filter based on results of another query.

```vql
-- Subquery in WHERE
FIND functions
WHERE id IN (
  FIND functions
  WHERE uses_delegatecall
  RETURN id
)
AND writes_state

-- EXISTS subquery
FIND functions
WHERE EXISTS (
  MATCH (f)-[:WRITES_STATE]->(:StateVariable {security_tags: ['owner']})
)

-- NOT EXISTS
FIND functions
WHERE NOT EXISTS (
  MATCH (f)-[:USES_MODIFIER]->()
)
AND writes_state
```

### Level 10: Expert - Set Operations

**Use when**: Combining or comparing result sets.

```vql
-- UNION: Combine results (remove duplicates)
FIND functions WHERE visibility = 'public'
UNION
FIND functions WHERE visibility = 'external'

-- INTERSECT: Find common results
FIND functions WHERE writes_state
INTERSECT
FIND functions WHERE has_external_calls

-- EXCEPT: Find differences
FIND functions WHERE visibility IN ['public', 'external']
EXCEPT
FIND functions WHERE has_access_gate
```

## Common Vulnerability Patterns

### Access Control Issues

```vql
-- Unprotected state-changing functions
FIND functions
WHERE visibility IN ['public', 'external']
  AND writes_state
  AND NOT has_access_gate
  AND NOT is_view_pure

-- Functions writing privileged state without checks
MATCH (f:Function)-[:WRITES_STATE]->(s:StateVariable)
WHERE f.visibility = 'public'
  AND s.security_tags CONTAINS_ANY ['owner', 'admin', 'role']
  AND NOT EXISTS (
    MATCH (f)-[:USES_MODIFIER]->(m:Modifier)
    WHERE m.label LIKE '%Access%'
  )
RETURN f.label, s.label
```

### Reentrancy

```vql
-- State changes after external calls
FIND functions
WHERE state_write_after_external_call
  AND NOT has_reentrancy_guard

-- Cross-function reentrancy
WITH writers AS (
  FIND functions WHERE writes_state RETURN id
)
MATCH (f1:Function)-[:CALLS_EXTERNAL]->(ext),
      (f2:Function IN writers)
WHERE f1.id != f2.id
  AND NOT f1.has_reentrancy_guard
  AND NOT f2.has_reentrancy_guard
RETURN f1.label, f2.label
```

### Dataflow/Taint Analysis

```vql
-- Attacker-controlled input to critical state
FLOW FROM (i:Input WHERE i.kind = 'parameter')
TO (s:StateVariable WHERE s.security_tags CONTAINS_ANY ['owner', 'implementation'])
EXCLUDE SOURCES ['msg.sender']
RETURN PATHS

-- Tainted external calls
FLOW FROM (i:Input)
TO (call:ExternalCallSite WHERE call.transfers_value)
RETURN TAINTED FUNCTIONS
```

### MEV Vulnerabilities

```vql
-- Missing slippage/deadline protection
FIND functions
WHERE swap_like
  AND (risk_missing_slippage_parameter OR risk_missing_deadline_check)

-- Functions susceptible to frontrunning
FIND functions
WHERE visibility = 'public'
  AND writes_state
  AND uses_block_timestamp
  AND NOT has_deadline_check
```

### Oracle Issues

```vql
-- Oracle usage without staleness checks
FIND functions
WHERE reads_oracle_price
  AND NOT has_staleness_check

-- L2 oracle without sequencer uptime check
FIND functions
WHERE reads_oracle_price
  AND NOT has_sequencer_uptime_check
```

### DoS Vulnerabilities

```vql
-- Unbounded loops
MATCH (f:Function)-[:FUNCTION_HAS_LOOP]->(l:Loop)
WHERE l.has_unbounded_loop
  AND NOT l.has_require_bounds

-- External calls in loops
MATCH (f:Function)-[:FUNCTION_HAS_LOOP]->(l:Loop)
WHERE l.external_calls_in_loop > 0
```

## Error Handling Strategy

### When You Get Errors

1. **Read the error message carefully** - it contains specific hints
2. **Check the suggested correction** - often it's a simple typo
3. **Use DESCRIBE to verify** - confirm property/type names
4. **Simplify your query** - remove clauses until it works, then add back
5. **Check examples** - look for similar queries in this guide

### Common Mistakes

**Unknown Property**:
```
❌ FIND functions WHERE visability = public
Error: Unknown property 'visability'
✅ FIND functions WHERE visibility = public
```

**Missing WHERE**:
```
❌ FIND functions visibility = public
Error: Missing WHERE clause
✅ FIND functions WHERE visibility = public
```

**Type Mismatch**:
```
❌ FIND functions WHERE visibility = true
Error: visibility expects string, got boolean
✅ FIND functions WHERE visibility IN ['public', 'external']
```

**Contradictory Conditions**:
```
❌ FIND functions WHERE visibility = 'public' AND visibility = 'private'
Warning: Contradictory conditions
✅ FIND functions WHERE visibility IN ['public', 'private']
   (or use OR if you want either)
```

## Performance Best Practices

### For LLM Query Construction

1. **Start with LIMIT during exploration**:
   ```vql
   FIND functions WHERE writes_state LIMIT 10
   ```

2. **Use RETURN to reduce tokens**:
   ```vql
   RETURN id, label  -- Minimal
   ```

3. **Use COMPACT for overviews**:
   ```vql
   FIND functions WHERE writes_state COMPACT
   ```

4. **Use EXISTS instead of IN for large subqueries**:
   ```vql
   -- Faster
   WHERE EXISTS (MATCH (f)-[:WRITES_STATE]->())

   -- Slower
   WHERE id IN (FIND ... large result set ...)
   ```

5. **Limit variable-length path depth**:
   ```vql
   MATCH (f)-[:CALLS_INTERNAL*1..3]->(target)  -- Good
   MATCH (f)-[:CALLS_INTERNAL*]->(target)      -- Potentially slow
   ```

## Decision Matrix for LLMs

| Scenario | Query Type | Syntax | Example |
|----------|-----------|--------|---------|
| Unknown schema | DESCRIBE | `DESCRIBE TYPES` | List available node types |
| Single node type | FIND | `FIND type WHERE ...` | Find public functions |
| Relationships | MATCH | `MATCH (a)-[r]->(b)` | Functions writing to state |
| Dataflow | FLOW | `FLOW FROM ... TO ...` | Input tainting state |
| Known pattern | PATTERN | `PATTERN pattern-id` | Check reentrancy |
| Multi-stage | WITH | `WITH ... AS (...) ...` | Complex analysis |
| Reduce tokens | RETURN | `RETURN id, label` | Get just IDs |
| Aggregation | GROUP BY | `GROUP BY ... RETURN COUNT(*)` | Count by type |

## Query Construction Checklist

Before submitting a query, verify:

- [ ] Did I use the right query type (FIND/MATCH/FLOW/PATTERN)?
- [ ] Are all property names spelled correctly?
- [ ] Did I include WHERE if I have conditions?
- [ ] Did I use RETURN if I want specific fields?
- [ ] Did I add LIMIT for large result sets?
- [ ] Are my conditions logically consistent (no contradictions)?
- [ ] Did I use the right operator (IN vs =, CONTAINS vs =)?
- [ ] For MATCH: Are my relationships directed correctly (-> vs <-)?
- [ ] For FLOW: Did I specify both FROM and TO?
- [ ] Did I use COMPACT if I only need overview?

## MCP-Style Protocol Integration

### Schema Discovery

```json
{
  "tool": "vql:schema",
  "action": "discover"
}
```

Returns all available types, properties, edges, and patterns.

### Query Validation

Before executing, validate:

```json
{
  "tool": "vql:validate",
  "query": "your VQL query here"
}
```

Returns errors, warnings, and suggestions.

### Autocomplete

Get suggestions while constructing query:

```json
{
  "tool": "vql:complete",
  "query": "FIND functions WHERE visi",
  "cursor": 27
}
```

Returns property suggestions.

## Advanced Patterns

### Conditional Logic in RETURN

```vql
RETURN id, label,
  CASE
    WHEN has_access_gate THEN 'protected'
    WHEN visibility = 'internal' THEN 'low-risk'
    ELSE 'vulnerable'
  END AS risk_level
```

### Nested Property Access

```vql
RETURN id, label,
       properties.risk_score,
       evidence[0].location.filename
```

### Complex Boolean Logic

```vql
WHERE (
  (visibility = 'public' AND writes_state)
  OR
  (visibility = 'external' AND has_external_calls)
)
AND NOT (
  has_access_gate
  OR uses_msg_sender
  OR is_view_pure
)
```

## Summary: Quick Reference

```vql
-- Discover schema
DESCRIBE TYPES | PROPERTIES | EDGES | PATTERNS

-- Find nodes
FIND <type> WHERE <conditions> [RETURN fields] [LIMIT n]

-- Match patterns
MATCH (a:Type)-[:EDGE]->(b:Type) WHERE ... RETURN ...

-- Track dataflow
FLOW FROM (source) TO (sink) [WHERE ...] RETURN PATHS

-- Run patterns
PATTERN pattern-id [LENS lens] [SEVERITY level]

-- Compose queries
WITH name AS (query) ...

-- Set operations
query1 UNION|INTERSECT|EXCEPT query2
```

**Remember**: Start simple (FIND), add complexity as needed (MATCH, FLOW), compose with WITH for multi-stage analysis.
