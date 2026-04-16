# Path Exploration Template

**Status:** CANONICAL
**Purpose:** Record cross-function and cross-contract attack paths with graph evidence.
**Required By:** Plan 11 (Cross-Function Path Exploration)
**References:** `.planning/testing/rules/canonical/ORCHESTRATION-MARKERS.md`

---

## Overview

This template captures attack paths discovered through VQL graph traversal. It is required for Tier B/C scenarios where cross-function analysis is necessary to identify vulnerabilities that span multiple functions or contracts.

---

## Metadata

```yaml
path_exploration_id: ""           # Unique identifier (e.g., path-001)
scenario_id: ""                   # Reference to scenario manifest
contract: ""                      # Target contract path
timestamp: ""                     # ISO 8601 format
transcript_ref: ""                # Path to claude-code-agent-teams transcript
vql_query_refs:                   # VQL queries used for exploration
  - query_id: ""                  # e.g., VQL-MIN-04, VQL-MIN-07
    query_purpose: ""             # What the query was looking for
    result_count: 0               # Number of paths found
```

---

## Query Configuration

Define the VQL queries used for path exploration.

### Structural Queries

```yaml
structural_queries:
  - query_id: ""                  # e.g., VQL-MIN-01
    query_string: ""              # Full VQL query
    purpose: ""                   # What pattern this query identifies
    filters:
      max_depth: 3                # Maximum call depth to traverse
      semantic_operations: []     # Filter by semantic ops (e.g., TRANSFERS_VALUE_OUT)
      exclude_patterns: []        # Patterns to exclude from results
```

### Semantic Queries

```yaml
semantic_queries:
  - query_id: ""                  # e.g., VQL-MIN-04
    query_string: ""              # Full VQL query
    target_pattern: ""            # Vulnerability pattern being searched
    semantic_filter:
      required_ops: []            # Operations that MUST appear in path
      forbidden_ops: []           # Operations that MUST NOT appear
      ordering_constraint: ""     # e.g., "READS_BALANCE before EXTERNAL_CALL"
```

---

## Entry/Exit Points

Define the entry and exit points for path analysis.

### Entry Points

```yaml
entry_points:
  - function: ""                  # Function name (e.g., withdraw)
    contract: ""                  # Contract name
    visibility: ""                # public/external/internal
    modifiers: []                 # Access control modifiers
    attacker_controlled: true     # Can attacker invoke directly?
    node_id: ""                   # Graph node ID
```

### Exit Points (Vulnerable States)

```yaml
exit_points:
  - state_variable: ""            # Variable being modified
    contract: ""                  # Contract name
    vulnerability_type: ""        # e.g., "balance manipulation"
    impact: ""                    # e.g., "funds drained"
    node_id: ""                   # Graph node ID
```

---

## Attack Path

Document the discovered attack path in detail.

### Path Summary

```yaml
attack_path:
  path_id: ""                     # Unique path identifier
  severity: ""                    # critical/high/medium/low
  confidence: 0.0                 # 0.0-1.0
  entry_point: ""                 # Starting function
  external_call: ""               # External call enabling attack
  vulnerable_state: ""            # State variable being exploited

  steps:
    - step_id: 1
      function: ""                # Function name
      contract: ""                # Contract name
      operation: ""               # Semantic operation (e.g., READS_USER_BALANCE)
      node_id: ""                 # Graph node ID
      code_location: ""           # file:line
      notes: ""                   # Why this step matters

    - step_id: 2
      function: ""
      contract: ""
      operation: ""
      node_id: ""
      code_location: ""
      notes: ""

    - step_id: 3
      function: ""
      contract: ""
      operation: ""
      node_id: ""
      code_location: ""
      notes: ""
```

### Path Diagram (ASCII)

```
[entry_function]
    |
    | OPERATION_TYPE
    v
[intermediate_function]
    |
    | EXTERNAL_CALL
    v
[callback / reentry point]
    |
    | WRITES_STATE
    v
[vulnerable_state]
```

---

## Evidence Contract

The evidence required to validate this path exploration.

### Required Evidence

```yaml
evidence_contract:
  # VQL Markers (must appear in transcript)
  vql_markers:
    - "[VQL_QUERY id=VQL-MIN-XX result_count=N]"

  # Path Evidence
  path_evidence:
    - node_id: ""                 # Graph node ID for each step
      relationship: ""            # Edge type connecting to next node

  # Code Locations
  code_locations:
    - file: ""
      line: 0
      snippet: ""                 # Relevant code snippet

  # Semantic Operations Sequence
  operation_sequence:
    - operation: ""               # e.g., READS_USER_BALANCE
      before_or_after: ""         # Relative to external call
```

### Validation Rules

```yaml
validation_rules:
  # The path must include these elements
  required_elements:
    - "At least one CALLS_EXTERNAL or CALLS_UNTRUSTED operation"
    - "At least one state-modifying operation (WRITES_*)"
    - "Clear ordering: state read -> external call -> state write"

  # These would invalidate the path
  invalidation_conditions:
    - "Checks-effects-interactions pattern properly followed"
    - "Reentrancy guard present on entry point"
    - "State updated before external call"
```

---

## Reasoning Usage

How this path informed vulnerability reasoning.

```yaml
reasoning_usage:
  how_path_informed_reasoning: |
    Explain how discovering this path contributed to the vulnerability finding.
    - What would have been missed without path exploration?
    - How does the path sequence prove the vulnerability?

  conclusion_impact: |
    Explain how the path evidence supports the severity and confidence ratings.

  without_path_exploration: |
    What would single-function analysis have concluded?
    Why is cross-function analysis necessary here?
```

---

## Anti-Fabrication Markers

Required markers to prove path exploration actually occurred.

```yaml
anti_fabrication:
  # Orchestration marker (must appear in transcript)
  markers_required:
    - "[VQL_QUERY id=..."
    - "Path discovered:"
    - "Node IDs:"

  # Minimum thresholds
  thresholds:
    min_transcript_lines: 100
    min_duration_ms: 30000
    min_path_steps: 2
    min_node_ids: 3
```

---

## Completion Checklist

- [ ] Query configuration defined with semantic filters
- [ ] Entry points identified with node IDs
- [ ] Exit points (vulnerable states) identified
- [ ] Attack path documented with all steps
- [ ] Each step has graph node ID and code location
- [ ] Evidence contract fulfilled
- [ ] Reasoning explains why path exploration was necessary
- [ ] VQL markers present in transcript
- [ ] Anti-fabrication thresholds met

---

## Usage Instructions

1. **Before Path Exploration**: Define entry points and target vulnerability types
2. **During Exploration**: Run VQL queries and record results with markers
3. **After Discovery**: Document the path with all evidence
4. **Validation**: Verify evidence contract is fulfilled
5. **Integration**: Reference this path in vulnerability findings

**Related Documents:**
- `.planning/testing/rules/canonical/ORCHESTRATION-MARKERS.md` (marker formats)
- `.planning/testing/vql/VQL-LIBRARY.md` (query library)
- `.planning/testing/guides/guide-pattern-lattice.md` (tier requirements)

---

**Template Version:** 2.0
**Last Updated:** 2026-02-04
