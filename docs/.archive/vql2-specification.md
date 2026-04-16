# VQL 2.0 Specification

**Version**: 2.0.0
**Status**: Implementation Draft
**Authors**: AlphaSwarm.sol Team

## Overview

VQL 2.0 is a powerful, LLM-friendly query language for the Vulnerability Knowledge Graph. It provides SQL-like expressiveness with graph pattern matching capabilities, advanced dataflow analysis, and comprehensive error recovery.

## Design Principles

1. **Deterministic and Reproducible**: No probabilistic parsing, same query always produces same result
2. **Progressive Complexity**: Simple queries are simple, complex queries are possible
3. **LLM-Friendly**: Self-documenting syntax with rich guidance and error recovery
4. **Composable**: Small queries build into large ones through WITH clauses and subqueries
5. **Type-Safe**: Early validation with clear type expectations and suggestions
6. **Fault-Tolerant**: Fuzzy matching, auto-correction, and helpful error messages

## Query Types

VQL 2.0 supports five main query types:

### 1. DESCRIBE - Schema Introspection

Discover available types, properties, edges, and patterns.

```vql
DESCRIBE TYPES
DESCRIBE PROPERTIES
DESCRIBE PROPERTIES FOR Function
DESCRIBE EDGES
DESCRIBE PATTERNS
DESCRIBE LENSES
DESCRIBE SCHEMA
```

**Use when**: LLM needs to discover what's available in the knowledge graph.

### 2. FIND - Simple Node/Edge Queries

Find nodes or edges matching specific criteria.

```vql
FIND functions
WHERE visibility IN ['public', 'external']
  AND writes_state
  AND NOT has_access_gate
RETURN id, label, visibility
LIMIT 20
```

**Use when**: Looking for a single node type with property filters.

**Features**:
- Simple syntax (backward compatible with VQL 1.0)
- Property filtering with boolean logic
- Result projection with RETURN
- Aggregations with GROUP BY

### 3. MATCH - Graph Pattern Matching

Match complex graph patterns using Cypher-inspired syntax.

```vql
MATCH (f:Function)-[:WRITES_STATE]->(s:StateVariable)
WHERE f.visibility = 'public'
  AND s.security_tags CONTAINS 'owner'
  AND NOT (f)-[:USES_MODIFIER]->()
RETURN f.label, s.label, s.security_tags
```

**Use when**: Relationships between nodes matter, multi-hop traversal needed.

**Features**:
- Graph pattern matching with relationships
- Variable-length paths: `-[:CALLS_INTERNAL*1..3]->`
- Optional patterns: `OPTIONAL MATCH`
- Named paths: `path = (start)-[*]->(end)`
- Pattern predicates in WHERE clause

### 4. FLOW - Dataflow Analysis

Track data flow from sources to sinks with taint analysis.

```vql
FLOW FROM (i:Input WHERE i.kind = 'parameter')
TO (s:StateVariable WHERE s.security_tags CONTAINS 'owner')
EXCLUDE SOURCES ['msg.sender']
RETURN SOURCES, SINKS, PATHS
```

**Use when**: Need to track how data flows through the code (taint analysis).

**Features**:
- Source and sink specification
- Taint propagation tracking
- Sanitizer requirements
- Backward slicing with `FLOW BACKWARD`
- Path filtering and validation

### 5. PATTERN - Vulnerability Pattern Matching

Run predefined vulnerability patterns from pattern packs.

```vql
PATTERN weak-access-control
LENS Authority
SEVERITY high
LIMIT 20
```

**Use when**: Checking for known vulnerability patterns.

## Core Language Features

### WHERE Clause - Filtering

Boolean logic with rich operators:

```vql
WHERE visibility = 'public'
  AND writes_state
  AND NOT has_access_gate
  AND state_write_count > 0
  AND label REGEX '^(mint|burn|transfer)'
  AND security_tags CONTAINS_ANY ['owner', 'admin']
```

**Operators**:
- Comparison: `=`, `!=`, `>`, `<`, `>=`, `<=`
- Set operations: `IN`, `NOT IN`
- Array operations: `CONTAINS`, `CONTAINS_ANY`, `CONTAINS_ALL`
- Pattern matching: `REGEX`, `LIKE`
- Boolean: `AND`, `OR`, `NOT`
- Existence: `EXISTS (subquery)`

**Negation Support**:
```vql
-- Negate individual conditions
WHERE NOT has_access_gate

-- Negate compound conditions
WHERE NOT (has_access_gate OR uses_msg_sender OR is_view_pure)

-- Negate existence checks
WHERE NOT EXISTS (
  MATCH (f)-[:USES_MODIFIER]->(m:Modifier)
)
```

### RETURN Clause - Result Projection

Control what fields are returned to reduce token usage:

```vql
-- Specific fields
RETURN id, label, visibility

-- Computed fields
RETURN id, label, has_access_gate AS protected

-- Aggregations
RETURN visibility, COUNT(*) AS total, SUM(writes_state) AS writers

-- All fields
RETURN *

-- Conditional expressions
RETURN id, label,
  CASE
    WHEN has_access_gate THEN 'protected'
    WHEN visibility = 'internal' THEN 'internal'
    ELSE 'vulnerable'
  END AS status

-- Nested property access
RETURN id, label, properties.risk_score, evidence[0].location.filename
```

### WITH Clause - Query Composition

Build complex analyses from simpler queries (Common Table Expressions):

```vql
WITH public_writers AS (
  FIND functions
  WHERE visibility = 'public' AND writes_state
)
FIND functions IN public_writers
WHERE NOT has_access_gate
RETURN id, label
```

**Multi-stage analysis**:
```vql
WITH risky_functions AS (
  FIND functions
  WHERE writes_state AND NOT has_access_gate
),
high_value_state AS (
  FIND state_variables
  WHERE security_tags CONTAINS_ANY ['owner', 'admin', 'implementation']
)
MATCH (f:Function IN risky_functions)-[:WRITES_STATE]->(s:StateVariable IN high_value_state)
RETURN f.label, s.label
```

### GROUP BY and Aggregations

Aggregate and group results:

```vql
FIND functions
GROUP BY visibility
RETURN visibility, COUNT(*) AS total,
       SUM(writes_state) AS writers,
       AVG(complexity) AS avg_complexity
HAVING COUNT(*) > 5
ORDER BY total DESC
```

**Aggregation Functions**:
- `COUNT(*)` - Count results
- `SUM(field)` - Sum numeric values
- `AVG(field)` - Average numeric values
- `MAX(field)` - Maximum value
- `MIN(field)` - Minimum value
- `COLLECT(field)` - Collect values into array

### Subqueries

Use subqueries in WHERE clauses:

```vql
FIND functions
WHERE id IN (
  FIND functions
  WHERE uses_delegatecall
  RETURN id
)
AND writes_state
```

### Set Operations

Combine query results:

```vql
FIND functions WHERE visibility = 'public'
UNION
FIND functions WHERE visibility = 'external'

FIND functions WHERE writes_state
INTERSECT
FIND functions WHERE has_external_calls

FIND functions WHERE visibility IN ['public', 'external']
EXCEPT
FIND functions WHERE has_access_gate
```

### Query Modifiers

Control query execution and output:

```vql
FIND functions
WHERE writes_state
ORDER BY label ASC
LIMIT 20
OFFSET 10
COMPACT
EXPLAIN
NO EVIDENCE
```

**Available Modifiers**:
- `LIMIT n` - Return at most n results
- `OFFSET n` - Skip first n results
- `ORDER BY field [ASC|DESC]` - Sort results
- `COMPACT` - Return minimal fields (id, type, label only)
- `EXPLAIN` - Show execution plan
- `NO EVIDENCE` - Omit evidence payloads
- `VERBOSE` - Include detailed debugging info

## Advanced Features

### Variable-Length Paths

Match paths of variable length:

```vql
-- 1 to 3 hops
MATCH (f:Function)-[:CALLS_INTERNAL*1..3]->(target:Function)
WHERE f.visibility = 'public' AND target.writes_state
RETURN f, target, LENGTH(PATH) AS depth

-- Any length (use with caution!)
MATCH (f)-[:CALLS_INTERNAL*]->(target)
WHERE target.writes_privileged_state
RETURN PATHS
```

### Optional Patterns

Match patterns that may not exist:

```vql
MATCH (f:Function)
OPTIONAL MATCH (f)-[:USES_MODIFIER]->(m:Modifier)
WHERE f.writes_state
RETURN f, m
```

### Named Paths

Capture and analyze entire paths:

```vql
MATCH path = (f:Function)-[:CALLS_EXTERNAL*]->(target)
WHERE ALL(node IN NODES(path) WHERE node.type = 'Function')
RETURN path, LENGTH(path), NODES(path)
```

### Pattern Predicates

Use patterns in WHERE clauses:

```vql
MATCH (f:Function)
WHERE (f)-[:WRITES_STATE]->(:StateVariable {security_tags: ['owner']})
  AND NOT (f)-[:USES_MODIFIER]->()
RETURN f
```

### Flow Query Advanced Features

**Multi-source flow**:
```vql
FLOW FROM (
  (i:Input WHERE i.kind IN ['parameter', 'env'])
  UNION
  (call:ExternalCallSite)
)
TO (s:StateVariable)
RETURN TAINTED FUNCTIONS
```

**Sanitizer requirements**:
```vql
FLOW FROM (i:Input)
TO (s:StateVariable)
REQUIRE ALL PATHS PASS (
  (f:Function)-[:USES_MODIFIER]->(m WHERE m.label LIKE '%Access%')
  OR
  (f:Function WHERE f.has_require_bounds)
)
RETURN UNSAFE PATHS
```

**Backward slicing**:
```vql
FLOW BACKWARD FROM (s:StateVariable WHERE s.label = 'owner')
TO ANY
MAX DEPTH 5
WHERE MODIFIED = true
RETURN INFLUENCERS
```

## LLM Guidance System

### Progressive Complexity Ladder

VQL 2.0 provides a progressive learning path for LLMs:

**Level 1: Beginner - Simple FIND**
```vql
FIND functions WHERE visibility = public
```

**Level 2: Intermediate - Filtered Projections**
```vql
FIND functions
WHERE visibility = public AND writes_state
RETURN id, label, visibility
```

**Level 3: Advanced - Graph Patterns**
```vql
MATCH (f:Function)-[:WRITES_STATE]->(s:StateVariable)
WHERE f.visibility = 'public'
RETURN f.label, s.label
```

**Level 4: Expert - Dataflow**
```vql
FLOW FROM (i:Input) TO (s:StateVariable)
WHERE s.security_tags CONTAINS 'owner'
RETURN PATHS
```

**Level 5: Expert - Composition**
```vql
WITH risky AS (
  FIND functions WHERE writes_state AND NOT has_access_gate
)
MATCH (f:Function IN risky)-[:CALLS_EXTERNAL]->(ext)
RETURN f, ext
```

### Decision Tree for Query Construction

LLMs should follow this decision process:

1. **What am I looking for?**
   - Single node type → Use FIND
   - Relationships between nodes → Use MATCH
   - Data flow paths → Use FLOW
   - Known vulnerability pattern → Use PATTERN

2. **Do I need all fields?**
   - No → Add RETURN clause with specific fields
   - Yes → Omit RETURN or use RETURN *

3. **Do I need to filter results?**
   - Yes → Add WHERE clause
   - No → Omit WHERE

4. **Am I building on previous results?**
   - Yes → Use WITH clause (CTE)
   - No → Single query

5. **Do I need aggregations?**
   - Yes → Add GROUP BY and aggregation functions
   - No → Omit GROUP BY

### Schema Discovery Protocol

LLMs can discover available schema elements:

**Request**:
```json
{
  "command": "vql:schema",
  "type": "full"
}
```

**Response**:
```json
{
  "capabilities": {
    "node_types": ["Function", "Contract", "StateVariable", "Event", "Input", "Loop", "Invariant"],
    "edge_types": ["WRITES_STATE", "READS_STATE", "CALLS_EXTERNAL", "CALLS_INTERNAL", "USES_MODIFIER"],
    "operators": ["eq", "neq", "in", "not_in", "gt", "gte", "lt", "lte", "regex", "contains_any", "contains_all"],
    "query_types": ["FIND", "MATCH", "FLOW", "PATTERN", "DESCRIBE"],
    "clauses": ["WHERE", "RETURN", "WITH", "GROUP BY", "HAVING", "ORDER BY", "LIMIT"]
  },
  "properties_by_type": {
    "Function": [
      {"name": "visibility", "type": "string", "values": ["public", "external", "internal", "private"]},
      {"name": "writes_state", "type": "boolean"},
      {"name": "has_access_gate", "type": "boolean"},
      {"name": "uses_delegatecall", "type": "boolean"}
    ]
  }
}
```

### Autocomplete Protocol

LLMs can request completion suggestions:

**Request**:
```json
{
  "command": "vql:complete",
  "query": "FIND functions WHERE visi",
  "cursor_position": 27
}
```

**Response**:
```json
{
  "suggestions": [
    {
      "text": "visibility",
      "type": "property",
      "description": "Function visibility (public, external, internal, private)",
      "values": ["public", "external", "internal", "private"],
      "confidence": 0.95
    }
  ]
}
```

### Validation Protocol

LLMs can validate queries before execution:

**Request**:
```json
{
  "command": "vql:validate",
  "query": "FIND functions WHERE visability = public"
}
```

**Response**:
```json
{
  "valid": false,
  "errors": [
    {
      "line": 1,
      "column": 21,
      "message": "Unknown property 'visability'",
      "hint": "Did you mean 'visibility'?",
      "suggestions": ["visibility"],
      "severity": "error",
      "auto_fix_available": true,
      "corrected_query": "FIND functions WHERE visibility = public"
    }
  ]
}
```

## Error Recovery

VQL 2.0 provides comprehensive error recovery:

### Syntax Errors

**Missing WHERE clause**:
```
Error: Missing WHERE clause
Query: FIND functions visibility = public
Hint: Add WHERE before conditions
Suggested: FIND functions WHERE visibility = public
```

**Missing RETURN**:
```
Error: Expected RETURN clause or query end
Query: FIND functions WHERE visibility = public id, label
Hint: Add RETURN before field list
Suggested: FIND functions WHERE visibility = public RETURN id, label
```

### Semantic Errors

**Unknown Property**:
```
Error: Unknown property 'visability' for type 'Function'
Did you mean: 'visibility' (confidence: 0.95)
Available properties: visibility, writes_state, has_access_gate, uses_delegatecall, ...
Auto-fix available: yes
```

**Type Mismatch**:
```
Error: Property 'visibility' expects string, got boolean
Got: visibility = true
Expected: visibility IN ['public', 'external', 'internal', 'private']
Or: has_public_visibility = true (if this property exists)
```

### Logical Errors

**Contradictory Conditions**:
```
Warning: Contradictory conditions detected
Conditions: visibility = 'public' AND visibility = 'private'
This will always return empty results
Suggestion: Use OR if you want either condition
```

**Empty Results**:
```
Warning: This query may return no results
Reason: No functions have both visibility='public' and visibility='internal'
Suggestion: Review your conditions or use OR
```

### Ambiguity Resolution

**Multiple Pattern Matches**:
```
Query: check reentrancy
Matches:
  1. PATTERN reentrancy-basic (confidence: 0.8)
  2. PATTERN reentrancy-cross-function (confidence: 0.6)
  3. FIND functions WHERE state_write_after_external_call (confidence: 0.7)
Choose [1-3] or clarify query with 'PATTERN reentrancy-basic'
```

## Formal Grammar

See [vql2-grammar.ebnf](./vql2-grammar.ebnf) for the complete EBNF grammar specification.

## Migration from VQL 1.0

VQL 2.0 is backward compatible with VQL 1.0. All existing queries will continue to work.

**VQL 1.0**:
```vql
find functions where visibility in [public, external] and writes_state limit 20
```

**VQL 2.0 equivalent** (more explicit):
```vql
FIND functions
WHERE visibility IN ['public', 'external']
  AND writes_state
LIMIT 20
```

**VQL 2.0 enhanced** (with projections):
```vql
FIND functions
WHERE visibility IN ['public', 'external']
  AND writes_state
RETURN id, label, visibility, writes_privileged_state
LIMIT 20
```

## Example Queries

### Access Control

**Find unprotected state-changing functions**:
```vql
FIND functions
WHERE visibility IN ['public', 'external']
  AND writes_state
  AND NOT has_access_gate
  AND NOT is_view_pure
RETURN id, label, visibility, writes_privileged_state
LIMIT 20
```

**Functions writing owner-like state without proper checks**:
```vql
MATCH (f:Function)-[:WRITES_STATE]->(s:StateVariable)
WHERE f.visibility = 'public'
  AND s.security_tags CONTAINS_ANY ['owner', 'admin', 'role']
  AND NOT EXISTS (
    MATCH (f)-[:USES_MODIFIER]->(m:Modifier)
    WHERE m.label LIKE '%Access%' OR m.label LIKE '%Only%'
  )
RETURN f.label, s.label, s.security_tags
```

### Reentrancy

**Potential reentrancy vulnerabilities**:
```vql
FIND functions
WHERE state_write_after_external_call
  AND NOT has_reentrancy_guard
RETURN id, label, external_call_count
```

**Cross-function reentrancy**:
```vql
WITH writers AS (
  FIND functions WHERE writes_state RETURN id
)
MATCH (f1:Function)-[:CALLS_EXTERNAL]->(ext),
      (f2:Function IN writers)
WHERE f1.id != f2.id
  AND NOT f1.has_reentrancy_guard
  AND NOT f2.has_reentrancy_guard
RETURN f1.label AS caller, f2.label AS writer
```

### Dataflow

**User input flowing to critical state**:
```vql
FLOW FROM (i:Input WHERE i.kind = 'parameter')
TO (s:StateVariable WHERE s.security_tags CONTAINS_ANY ['owner', 'implementation', 'fee'])
EXCLUDE SOURCES ['msg.sender']
RETURN SOURCES.label, SINKS.label, PATHS
```

**Taint analysis with sanitizers**:
```vql
FLOW FROM (i:Input)
TO (call:ExternalCallSite WHERE call.transfers_value)
REQUIRE ALL PATHS PASS (
  EXISTS (f:Function WHERE f.has_require_bounds)
)
RETURN UNSAFE PATHS
```

### MEV and Oracle

**Functions missing slippage protection**:
```vql
FIND functions
WHERE risk_missing_slippage_parameter
   OR risk_missing_deadline_check
RETURN id, label, swap_like, risk_missing_slippage_parameter
```

**Oracle usage without staleness checks**:
```vql
FIND functions
WHERE reads_oracle_price
  AND NOT has_staleness_check
RETURN id, label, oracle_freshness_ok
```

### DoS

**Unbounded loops**:
```vql
MATCH (f:Function)-[:FUNCTION_HAS_LOOP]->(l:Loop)
WHERE l.has_unbounded_loop
  AND NOT l.has_require_bounds
RETURN f.label, l.label, l.external_calls_in_loop
```

**External calls in loops**:
```vql
MATCH (f:Function)-[:FUNCTION_HAS_LOOP]->(l:Loop)
WHERE l.external_calls_in_loop > 0
RETURN f.label, l.external_calls_in_loop
```

## Best Practices

1. **Use RETURN to reduce token costs**: Only request fields you need
2. **Start simple, add complexity**: Begin with FIND, upgrade to MATCH if needed
3. **Use WITH for complex analysis**: Break down multi-stage queries
4. **Add LIMIT to exploratory queries**: Prevent large result sets during exploration
5. **Use COMPACT for summaries**: Get overview before diving into details
6. **Use EXPLAIN to understand execution**: Optimize slow queries
7. **Leverage autocomplete**: Let the system guide you to valid properties
8. **Check validation before execution**: Catch errors early

## Performance Considerations

- **Pattern matching** is more expensive than simple property filtering
- **Variable-length paths** can be very expensive - use max_depth
- **FLOW queries** require dataflow analysis - consider using patterns instead for known vulnerabilities
- **RETURN projections** reduce memory and serialization overhead
- **LIMIT early** when exploring to avoid processing entire graph
- **Use indexes** (automatic on id, type, label, common properties)

## Future Enhancements

Planned for future versions:

- **Temporal queries**: Track changes over time
- **Graph mutations**: INSERT, UPDATE, DELETE for graph modification
- **User-defined functions**: Custom aggregations and transformations
- **Query optimization hints**: FORCE INDEX, JOIN ORDER, etc.
- **Distributed execution**: Query federation across multiple graphs
- **Incremental updates**: Real-time graph updates with streaming queries
