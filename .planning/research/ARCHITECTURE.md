# Architecture Patterns

**Domain:** LLM-facing graph interface for security analysis
**Researched:** 2026-01-27

## Recommended Architecture

```
                                   +------------------+
                                   |  Interface       |
                                   |  Contract v2     |
                                   |  (JSON Schema)   |
                                   +--------+---------+
                                            |
                    +-----------------------+-----------------------+
                    |                       |                       |
          +---------v----------+  +---------v----------+  +---------v----------+
          |  Taxonomy Registry |  |  Evidence Resolver |  |  Schema Validator  |
          |  (ops + edges)     |  |  (build hash)      |  |  (Pydantic)        |
          +---------+----------+  +---------+----------+  +---------+----------+
                    |                       |                       |
                    +-----------------------+-----------------------+
                                            |
                                   +--------v---------+
                                   |  Unified Slicing |
                                   |  Pipeline        |
                                   +--------+---------+
                                            |
                    +-----------------------+-----------------------+
                    |                       |                       |
          +---------v----------+  +---------v----------+  +---------v----------+
          |  PPR Seed          |  |  Subgraph          |  |  Context Policy    |
          |  Selection         |  |  Extraction        |  |  (budgets)         |
          +---------+----------+  +---------+----------+  +---------+----------+
                    |                       |                       |
                    +-----------------------+-----------------------+
                                            |
                    +-----------------------+-----------------------+
                    |                       |                       |
          +---------v----------+  +---------v----------+  +---------v----------+
          |  Dominance         |  |  Taint Engine      |  |  Omission Ledger   |
          |  Analyzer          |  |  (expanded)        |  |  (coverage)        |
          +---------+----------+  +---------+----------+  +---------+----------+
                    |                       |                       |
                    +--------+--------------+------------+----------+
                             |                           |
                    +--------v----------+       +--------v----------+
                    |  Pattern Engine   |       |  Query Executor   |
                    |  (v2 outputs)     |       |  (VQL 2.0)        |
                    +--------+----------+       +--------+----------+
                             |                           |
                             +-------------+-------------+
                                           |
                                  +--------v---------+
                                  |  LLM Surface     |
                                  |  (CLI/SDK/Skills)|
                                  +------------------+
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| Interface Contract v2 | Schema definition, semver, compatibility | All consumers |
| Taxonomy Registry | Operation/edge normalization, migration | Pattern engine, query executor |
| Evidence Resolver | Deterministic ID generation, source mapping | Pattern engine, LLM surface |
| Schema Validator | Output validation, fail-fast gate | All output surfaces |
| Unified Slicing Pipeline | Context assembly, budget enforcement | All slicing calls |
| PPR Seed Selection | Relevance scoring, focal node selection | Subgraph extraction |
| Subgraph Extraction | Node/edge selection, distance computation | Slicing pipeline |
| Context Policy | Token budgets, data minimization | Slicing pipeline |
| Dominance Analyzer | Path qualification, guard dominance | Pattern engine, taint engine |
| Taint Engine | Dataflow tracking, sanitizers, availability | Pattern engine |
| Omission Ledger | Cut sets, excluded edges, coverage scores | Slicing pipeline |
| Pattern Engine | Pattern matching, clause matrix, evidence | LLM surface |
| Query Executor | VQL parsing, execution, evidence | LLM surface |
| LLM Surface | CLI, SDK, skills - unified output | End users (LLM agents) |

### Data Flow

```
1. Source Code
       |
       v
2. Slither (CFG, SlithIR, data deps)
       |
       v
3. BSKG Builder (nodes, edges, properties)
       |
       v
4. Dominance Analyzer (path-qualified ordering)
       |
       v
5. Taint Engine (dataflow with availability)
       |
       v
6. Pattern Engine (tier A/B/C matching)
       |
       v
7. Unified Slicing (context assembly)
       |
       v
8. Omission Ledger (attach coverage metadata)
       |
       v
9. Schema Validator (v2 contract enforcement)
       |
       v
10. LLM Surface (CLI/SDK/skills output)
```

## Patterns to Follow

### Pattern 1: Explicit Unknown States

**What:** Every analysis result has a three-valued outcome: known-true, known-false, unknown.

**When:** Any analysis that can fail or be incomplete (dominance, taint, guards).

**Example:**
```python
from enum import Enum
from typing import Optional

class OrderingRelation(Enum):
    ALWAYS_BEFORE = "always_before"
    SOMETIMES_BEFORE = "sometimes_before"
    NEVER_BEFORE = "never_before"
    UNKNOWN = "unknown"

@dataclass
class OrderingResult:
    relation: OrderingRelation
    confidence: float  # 0.0-1.0
    reason: Optional[str] = None  # Why unknown, if applicable
```

### Pattern 2: Omission Ledger Attachment

**What:** Every subgraph/slice output carries metadata about what was omitted.

**When:** Any pruning, truncation, or extraction operation.

**Example:**
```python
@dataclass
class OmissionLedger:
    coverage_score: float  # 0.0-1.0
    cut_set: list[str]  # Edges that blocked traversal
    excluded_edges: list[str]  # Edge types not followed
    omitted_nodes: list[str]  # Nodes dropped (optional, can be large)
    slice_mode: Literal["standard", "debug"]

    def attach_to(self, output: dict) -> dict:
        output["omissions"] = self.to_dict()
        return output
```

### Pattern 3: Registry-Mediated Taxonomy

**What:** All operation/edge names go through a registry that handles aliases and migrations.

**When:** Any pattern matching, query execution, or output generation.

**Example:**
```python
class TaxonomyRegistry:
    _aliases: dict[str, str] = {
        "TRANSFERS_ETH": "TRANSFERS_VALUE_OUT",
        "VALUE_TRANSFER": "TRANSFERS_VALUE_OUT",
    }
    _deprecations: dict[str, tuple[str, str]] = {
        "TRANSFERS_ETH": ("TRANSFERS_VALUE_OUT", "1.0.0"),
    }

    def resolve(self, name: str) -> str:
        """Resolve alias to canonical name."""
        canonical = self._aliases.get(name, name)
        if name in self._deprecations:
            new_name, sunset = self._deprecations[name]
            warnings.warn(f"{name} deprecated since {sunset}, use {new_name}")
        return canonical
```

### Pattern 4: Schema-Gated Output

**What:** All LLM-facing outputs validated against JSON Schema before emission.

**When:** Any output to CLI, SDK, or skills.

**Example:**
```python
from pydantic import BaseModel, ValidationError

class InterfaceV2Output(BaseModel):
    interface_version: int = 2
    query: QuerySpec
    summary: SummarySpec
    findings: list[FindingSpec]

def emit_output(data: dict, surface: str) -> InterfaceV2Output:
    try:
        validated = InterfaceV2Output.model_validate(data)
    except ValidationError as e:
        raise SchemaComplianceError(f"Output failed v2 contract: {e}")
    return validated
```

### Pattern 5: Build Hash Binding

**What:** Evidence references include a build hash for reproducibility.

**When:** Any evidence ID generation.

**Example:**
```python
import xxhash

def compute_build_hash(graph_data: bytes) -> str:
    """Compute fast content hash for graph build."""
    return xxhash.xxh64(graph_data).hexdigest()[:12]

@dataclass
class EvidenceRef:
    file: str
    line: int
    node_id: str
    snippet_id: str
    build_hash: str  # Ties evidence to specific build

    @property
    def deterministic_id(self) -> str:
        return f"{self.build_hash}:{self.node_id}:{self.snippet_id}"
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Silent Omission

**What:** Pruning or truncating data without recording what was lost.

**Why bad:** LLM agents assume completeness; missing data interpreted as "no evidence" = safe.

**Instead:** Always attach omission ledger; make coverage score mandatory.

### Anti-Pattern 2: Boolean Guard Properties

**What:** `has_reentrancy_guard: true/false` without dominance context.

**Why bad:** A guard that exists but is bypassable is worse than no guard (false confidence).

**Instead:** `guard_status: dominating | bypassable | unknown` with evidence.

### Anti-Pattern 3: Multiple Slicing Paths

**What:** Different code paths for router slicing, LLM slicing, KG slicing.

**Why bad:** Different agents receive different context for the same query; debugging is impossible.

**Instead:** Single unified pipeline with role-specific budget parameters.

### Anti-Pattern 4: Schema Warnings

**What:** Emitting non-compliant output with a warning instead of failing.

**Why bad:** Downstream consumers expect schema compliance; warnings are ignored.

**Instead:** Schema validation as a gate; non-compliant output = error.

### Anti-Pattern 5: Hardcoded Taxonomy

**What:** Operation names scattered across code as string literals.

**Why bad:** Taxonomy drift; patterns, VQL, and tools use different names.

**Instead:** Central registry; all names resolved through registry.

## Scalability Considerations

| Concern | At 10 contracts | At 100 contracts | At 1000 contracts |
|---------|-----------------|------------------|-------------------|
| Dominance computation | In-memory, < 1s per contract | In-memory, batch | Consider caching |
| Build hash | Per-graph, instant | Per-graph, instant | Per-graph, instant |
| Omission ledger | Small metadata | Small metadata | Consider summary mode |
| Schema validation | Per-output, fast | Per-output, fast | Per-output, fast |
| Registry lookup | O(1) hash lookup | O(1) hash lookup | O(1) hash lookup |

**Note:** Phase 5.9 is interface-focused, not performance-focused. Performance optimization was addressed in Phase 8 research.

## Integration Points

### With Existing Modules

| Module | Integration | Changes Needed |
|--------|-------------|----------------|
| `kg/operations.py` | Dominance analyzer consumes operations | Add CFG node association |
| `kg/sequencing.py` | Replace with dominance-aware ordering | Major rewrite |
| `kg/taint.py` | Expand with external returns, sanitizers | Medium extension |
| `kg/subgraph.py` | Attach omission ledger | Add ledger parameter |
| `kg/slicer.py` | Integrate into unified pipeline | Refactor to component |
| `llm/context_policy.py` | Use as budget source for unified pipeline | Interface adapter |
| `queries/patterns.py` | Add clause matrix, unknowns | Output format change |

### With New Modules

| New Module | Purpose | Location |
|------------|---------|----------|
| `kg/dominance.py` | Dominance tree, path qualification | New file |
| `kg/taxonomy.py` | Operation/edge registry | New file |
| `kg/omission.py` | Omission ledger, coverage | New file |
| `kg/evidence.py` | Evidence IDs, build hash | New file |
| `kg/pipeline.py` | Unified slicing orchestration | New file |
| `interface/contract.py` | Interface v2 schema, validator | New file |

## Sources

- [05.9-CONTEXT.md](/Volumes/ex_ssd/home/projects/python/vkg-solidity/true-vkg/.planning/phases/05.9-llm-graph-interface-improvements/05.9-CONTEXT.md)
- [PHILOSOPHY.md](/Volumes/ex_ssd/home/projects/python/vkg-solidity/true-vkg/docs/PHILOSOPHY.md)
- [A Simple, Fast Dominance Algorithm](https://www.cs.tufts.edu/comp/150FP/archive/keith-cooper/dom14.pdf)
- [SARIF 2.1.0 Specification](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html)
- [Knowledge Graph Incompleteness in RAG](https://arxiv.org/html/2508.08344v1)
