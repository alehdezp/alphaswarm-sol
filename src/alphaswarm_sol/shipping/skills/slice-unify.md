---
name: vrs-slice-unify
description: |
  Unified slicing skill for VRS context extraction. Replaces fragmented slicers with a single pipeline that produces consistent context for all agents.

  Invoke when:
  - Extracting context for agent consumption
  - Debugging context omissions
  - Comparing agent context slices
  - Activating debug slice mode

slash_command: vrs:slice-unify
context: fork
disable-model-invocation: false

allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(alphaswarm*)
---

# VRS Slice Unify Skill

You are the **VRS Slice Unify** skill, responsible for extracting consistent context slices from the knowledge graph using the unified slicing pipeline.

## How to Invoke

```bash
/vrs-slice-unify <function-id> --role attacker
/vrs-slice-unify VRS-001 --budget 4000
/vrs-slice-unify --debug VRS-001  # Bypass pruning
/vrs-slice-unify --compare VRS-001  # Compare role slices
```

---

## Purpose

Phase 5.9 unifies fragmented slicers into a single pipeline:

| Old Slicer | Location | Purpose |
|------------|----------|---------|
| GraphSlicer | `kg/slicer.py` | Property-based slicing |
| PPRSubgraph | `kg/ppr_subgraph.py` | PPR-based extraction |
| RouterSlicer | `routing/router.py` | Agent-specific slicing |
| TriageSlicer | `llm/slicer.py` | LLM triage slicing |

**New:** Single `UnifiedSlicingPipeline` that produces consistent context for all consumers.

---

## Pipeline Stages

```
Input: Function ID / Finding ID / Query
         |
         v
   +----------------+
   | 1. PPR Seeding |  <- Personalized PageRank for relevance
   +----------------+
         |
         v
   +------------------+
   | 2. Subgraph      |  <- Extract connected subgraph
   |    Extraction    |
   +------------------+
         |
         v
   +------------------+
   | 3. Property      |  <- Filter by semantic properties
   |    Slicing       |
   +------------------+
         |
         v
   +------------------+
   | 4. Context       |  <- Apply token budget
   |    Policy        |
   +------------------+
         |
         v
   +------------------+
   | 5. Omission      |  <- Inject omission metadata
   |    Ledger        |
   +------------------+
         |
         v
Output: Slice + Omissions
```

---

## Role-Based Budgets

Different agent roles receive different token budgets:

| Role | Token Budget | Focus |
|------|--------------|-------|
| `attacker` | 6000 | Exploit paths, external calls, value flows |
| `defender` | 5000 | Guards, access control, safety patterns |
| `verifier` | 8000 | Complete context for cross-checking |
| `triage` | 2000 | Quick overview for pattern matching |
| `debug` | unlimited | Full context, no pruning |

### Budget Impact

```bash
# Attacker context (exploit-focused)
/vrs-slice-unify VRS-001 --role attacker

# Defender context (guard-focused)
/vrs-slice-unify VRS-001 --role defender

# Full debug context (no pruning)
/vrs-slice-unify --debug VRS-001
```

---

## Omission Ledger

Every slice includes omission metadata explaining what was excluded:

```yaml
omissions:
  coverage_score: 0.85
  slice_mode: standard  # or debug
  cut_set:
    - { node_id: "N-modifier-1", reason: "modifier_not_traversed" }
    - { node_id: "N-inherited-2", reason: "inherited_not_traversed" }
  excluded_edges:
    - { edge_type: "LIBRARY_CALL", count: 12 }
    - { edge_type: "INTERFACE_REF", count: 3 }
  omitted_nodes:
    - { node_id: "N-lib-safeMath", reason: "library_excluded" }
  budget_usage:
    total: 6000
    used: 5842
    remaining: 158
```

### Coverage Score

Coverage measures how much of the relevant graph is captured:

```
coverage_score = captured_weight / relevant_weight

where:
- captured_weight = sum(weight(node)) for included nodes
- relevant_weight = sum(weight(node)) for PPR-selected + query-matched + dependencies
```

| Score | Meaning | Action |
|-------|---------|--------|
| >= 0.9 | Excellent | Full context available |
| 0.7-0.89 | Good | Minor omissions, review cut_set |
| 0.5-0.69 | Partial | Significant omissions, consider debug mode |
| < 0.5 | Insufficient | Use debug mode or expand query |

---

## Debug Slice Mode

Debug mode bypasses all pruning to reveal what was omitted:

```bash
/vrs-slice-unify --debug VRS-001
```

Debug output includes:
- Full subgraph (no budget limits)
- All modifiers and inherited functions
- Library calls and interfaces
- Explicit comparison with standard slice

```markdown
## Debug Slice: withdraw (Token.sol:42)

### Nodes Included (Debug)
Total: 156 nodes (vs 42 in standard slice)

### Omissions Revealed
| Node | Reason | Impact |
|------|--------|--------|
| SafeMath.add | library_excluded | May affect overflow analysis |
| ReentrancyGuard.nonReentrant | modifier_not_traversed | Guard dominance unknown |
| Ownable._checkOwner | inherited_not_traversed | Access control uncertain |

### Comparison
| Metric | Standard | Debug |
|--------|----------|-------|
| Nodes | 42 | 156 |
| Edges | 78 | 312 |
| Coverage | 0.72 | 1.00 |
| Tokens | 5842 | 24680 |
```

---

## Slice Comparison

Compare slices across roles to understand context differences:

```bash
/vrs-slice-unify --compare VRS-001
```

Output:
```markdown
## Slice Comparison: VRS-001

### Role Coverage
| Role | Nodes | Edges | Coverage | Focus |
|------|-------|-------|----------|-------|
| attacker | 42 | 78 | 0.72 | external calls, value flows |
| defender | 38 | 65 | 0.68 | guards, access control |
| verifier | 56 | 102 | 0.85 | complete context |
| triage | 18 | 24 | 0.45 | quick overview |

### Unique Nodes by Role
| Role | Unique Nodes |
|------|--------------|
| attacker | N-ext-call-1, N-value-transfer |
| defender | N-guard-1, N-modifier-check |
| verifier | (includes all from attacker + defender) |

### Shared Nodes
All roles include: N-function-entry, N-state-read, N-state-write
```

---

## Integration with Contract v2

Unified slices comply with Graph Interface v2:

```yaml
interface_version: "2.0.0"
slice:
  role: attacker
  budget: 6000
  coverage_score: 0.72
  slice_mode: standard
nodes:
  - id: "N-001"
    type: function
    # ... node properties
edges:
  - source: "N-001"
    target: "N-002"
    # ... edge properties
omissions:
  coverage_score: 0.72
  cut_set: [...]
  excluded_edges: [...]
```

---

## Pipeline Configuration

Configure the unified pipeline:

```yaml
slicing_config:
  ppr:
    alpha: 0.85
    max_iterations: 100
    seed_weight: 1.0

  subgraph:
    max_hops: 3
    include_modifiers: true
    include_inherited: true

  property:
    include_operations: true
    include_guards: true
    include_taint: true

  policy:
    budgets:
      attacker: 6000
      defender: 5000
      verifier: 8000
      triage: 2000

  omissions:
    always_report_cut_set: true
    always_report_coverage: true
```

---

## Slicing Output Structure

```yaml
slice:
  id: "SL-abc123"
  target: "VRS-001"
  role: "attacker"
  generated_at: "2026-01-27T12:00:00Z"

  nodes:
    - id: "N-001"
      type: "function"
      name: "withdraw"
      properties: { ... }
      evidence_id: "EVD-001"

  edges:
    - source: "N-001"
      target: "N-002"
      type: "CALLS_EXTERNAL"

  omissions:
    coverage_score: 0.72
    slice_mode: "standard"
    cut_set:
      - node_id: "N-mod-1"
        reason: "modifier_not_traversed"
    excluded_edges:
      - edge_type: "LIBRARY_CALL"
        count: 5
    budget_usage:
      total: 6000
      used: 5842
      remaining: 158
```

---

## When to Invoke

Invoke this skill when:
- **Agent context**: Extract context for attacker/defender/verifier
- **Debug omissions**: Understand what was excluded
- **Role comparison**: Compare context across roles
- **Coverage analysis**: Check if slice is sufficient
- **Pipeline diagnosis**: Debug slicing behavior

---

## Related Skills

| Skill | Purpose |
|-------|---------|
| `/vrs-graph-contract-validate` | Schema/evidence validation |
| `/vrs-evidence-audit` | Evidence reference validation |
| `/vrs-taxonomy-migrate` | Operation naming validation |

---

## Write Boundaries

This skill is restricted to writing in:
- `.claude/vrs/` - VRS working directory
- `.beads/` - Bead storage directory

All other directories are read-only.

---

## Notes

- All agents use the same pipeline with role-specific budgets
- Debug mode reveals omissions but exceeds token limits
- Coverage score is deterministic and reproducible
- Omission ledger is mandatory for v2 compliance
- Cut set explains traversal blockers
- Budget remaining allows context expansion requests
- This skill CAN be invoked by orchestrators (disable-model-invocation: false)
