# Graph Density Investigation for LLM Consumption

**Status:** TODO (Critical Research)
**Priority:** HIGH
**Phase:** 9 (Context Optimization)
**Last Updated:** 2026-01-07

---

## The Problem

VKG's knowledge graph contains 50+ properties per function. When an LLM consumes this graph to investigate a finding, it may receive:

- **Too much irrelevant data**: 30+ fields that don't matter for the current vulnerability
- **Context pollution**: Noise fills the context window, pushing out useful information
- **Hallucination risk**: Irrelevant fields may confuse the LLM into false correlations
- **Token waste**: Paying for tokens that don't contribute to the verdict

### Example: Reentrancy Investigation

For a reentrancy finding, the LLM needs:
- ✅ `state_write_after_external_call`
- ✅ `has_reentrancy_guard`
- ✅ `external_call_sites`
- ✅ `state_variables_written`
- ✅ `callers` (attack surface)

But the LLM receives ALL 50+ properties:
- ❌ `reads_oracle_price` (irrelevant for reentrancy)
- ❌ `has_staleness_check` (oracle-specific)
- ❌ `uses_chainid` (crypto-specific)
- ❌ `swap_like` (MEV-specific)
- ❌ `upgradeable_without_storage_gap` (upgrade-specific)
- ... 40 more irrelevant fields

**Hypothesis:** This noise degrades LLM performance and increases costs.

---

## Investigation Tasks

### 1. Measure Current Graph Density

```python
# For each vulnerability category, measure:
# - Total properties in graph
# - Properties actually relevant to that category
# - Relevance ratio (relevant / total)

categories = [
    "reentrancy",
    "access_control",
    "oracle",
    "dos",
    "mev",
    "token",
    "upgrade",
    "crypto",
]

for category in categories:
    measure_relevance_ratio(category)
```

**Expected Output:**
| Category | Total Props | Relevant Props | Relevance Ratio |
|----------|-------------|----------------|-----------------|
| Reentrancy | 50 | 8 | 16% |
| Access Control | 50 | 12 | 24% |
| Oracle | 50 | 10 | 20% |
| ... | ... | ... | ... |

### 2. Benchmark LLM Accuracy: Full Graph vs Sliced Graph

**Experiment Design:**
```
For each test finding:
  1. Get full graph context (50+ properties)
  2. Get sliced graph context (category-relevant only)
  3. Send both to LLM with same prompt
  4. Compare:
     - Verdict accuracy (TP/FP/FN)
     - Confidence score
     - Reasoning quality
     - Token usage
     - Response time
```

**Expected Results:**
| Context Type | Accuracy | Tokens | Cost | Latency |
|--------------|----------|--------|------|---------|
| Full Graph | TBD% | ~2000 | $X | Yms |
| Sliced Graph | TBD% | ~500 | $X/4 | Y/2ms |

### 3. Define Category-Relevant Property Sets

Create explicit property sets per vulnerability category:

```yaml
# property_sets.yaml

reentrancy:
  required:
    - state_write_after_external_call
    - has_reentrancy_guard
    - external_call_sites
    - state_variables_written
    - visibility
    - modifiers
  optional:
    - callers
    - callees
    - cross_function_writes

access_control:
  required:
    - has_access_gate
    - writes_privileged_state
    - visibility
    - modifiers
    - uses_tx_origin
  optional:
    - role_checks
    - owner_comparisons
    - caller_restrictions

oracle:
  required:
    - reads_oracle_price
    - has_staleness_check
    - has_sequencer_uptime_check
    - oracle_sources
  optional:
    - twap_window
    - price_deviation_check

# ... more categories
```

### 4. Implement Graph Slicing

```python
class GraphSlicer:
    """Slice graph to category-relevant properties only."""

    def __init__(self, property_sets: Dict[str, PropertySet]):
        self.property_sets = property_sets

    def slice_for_category(
        self,
        graph: KnowledgeGraph,
        category: str
    ) -> SlicedGraph:
        """Return graph with only category-relevant properties."""
        relevant = self.property_sets[category]

        sliced = SlicedGraph()
        for node in graph.nodes:
            sliced_node = self._filter_properties(node, relevant)
            sliced.add_node(sliced_node)

        return sliced

    def slice_for_finding(
        self,
        graph: KnowledgeGraph,
        finding: Finding
    ) -> SlicedGraph:
        """Slice based on finding's pattern category."""
        category = finding.pattern.category
        return self.slice_for_category(graph, category)
```

### 5. Integrate with Beads

Update VulnerabilityBead to use sliced graphs:

```python
@dataclass
class VulnerabilityBead:
    # ... existing fields ...

    # CHANGE: graph_context uses sliced graph, not full graph
    graph_context: SlicedGraphContext  # Only category-relevant properties

    # NEW: Option to include full graph if needed
    full_graph_available: bool = True  # Agent can request more if needed
```

### 6. Measure Hallucination Rate

**Specific Tests:**
```python
def test_hallucination_with_irrelevant_context():
    """LLM should NOT reference irrelevant properties."""

    # Reentrancy finding with full graph (includes oracle properties)
    full_bead = create_bead(finding, full_graph=True)

    # Send to LLM
    response = llm.analyze(full_bead)

    # Check if LLM mentioned irrelevant properties
    irrelevant_mentions = [
        "oracle", "staleness", "chainid", "swap", "upgrade"
    ]

    for term in irrelevant_mentions:
        assert term not in response.reasoning.lower(), \
            f"LLM hallucinated about {term} for reentrancy finding"
```

---

## Proposed Solution: Context-Aware Graph Slicing

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  FINDING                                                        │
│  Pattern: reentrancy-basic                                      │
│  Category: reentrancy                                           │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  GRAPH SLICER                                                   │
│                                                                 │
│  Input: Full graph (50+ properties per node)                   │
│  Category: reentrancy                                           │
│  Property Set: [state_write_after_external_call,               │
│                 has_reentrancy_guard, external_call_sites, ...] │
│                                                                 │
│  Output: Sliced graph (8 properties per node)                  │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  BEAD CREATOR                                                   │
│                                                                 │
│  Creates VulnerabilityBead with:                               │
│  - Sliced graph context (category-relevant only)               │
│  - TOON format (additional 30-50% reduction)                   │
│  - Full graph reference (if agent needs more)                  │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  LLM CONSUMPTION                                                │
│                                                                 │
│  Before: ~2000 tokens, 50+ properties, noise                   │
│  After:  ~400 tokens, 8-12 properties, focused                 │
│                                                                 │
│  Result: Higher accuracy, lower cost, less hallucination       │
└─────────────────────────────────────────────────────────────────┘
```

### Token Savings Calculation

| Stage | Before | After | Reduction |
|-------|--------|-------|-----------|
| Full Graph | 2000 tokens | - | - |
| Graph Slicing | - | 500 tokens | 75% |
| TOON Encoding | - | 350 tokens | 30% more |
| **Total** | **2000 tokens** | **350 tokens** | **82.5%** |

---

## Success Metrics

| Metric | Target | Minimum | How to Measure |
|--------|--------|---------|----------------|
| Token Reduction | >= 75% | >= 50% | Full vs sliced graph tokens |
| Accuracy Preservation | 0% loss | < 5% loss | Verdict accuracy comparison |
| Hallucination Reduction | >= 80% | >= 50% | Irrelevant term mentions |
| Cost Savings | >= 75% | >= 50% | $ per finding analysis |
| Latency Improvement | >= 50% | >= 30% | Time to verdict |

---

## Implementation Priority

1. **[HIGH]** Define property sets per category (Task 9.A)
2. **[HIGH]** Implement GraphSlicer (Task 9.B)
3. **[HIGH]** Benchmark full vs sliced accuracy (Task 9.C)
4. **[MEDIUM]** Integrate with BeadCreator (Task 9.D)
5. **[MEDIUM]** Add "request more context" fallback (Task 9.E)
6. **[LOW]** Create category-agnostic smart slicer (Task 9.F)

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Slice removes needed property | False negative | Allow agent to request full graph |
| Property sets incomplete | Missing context | Iterative refinement based on failures |
| Overhead of slicing | Performance | Cache sliced graphs per category |
| Category detection wrong | Wrong slice | Use pattern metadata, not inference |

---

## Decision Point

After investigation, decide:

1. **Slicing is essential**: Graph noise significantly hurts LLM performance
   - Action: Implement full graph slicing system

2. **Slicing is beneficial but not critical**: Minor improvements
   - Action: Implement optional slicing, default to full

3. **Slicing has no significant impact**: LLMs handle noise well
   - Action: Skip slicing, focus on TOON only

---

*Graph Density Investigation | Phase 9 | BSKG 4.0 | 2026-01-07*
