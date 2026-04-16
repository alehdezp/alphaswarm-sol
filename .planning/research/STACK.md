# Technology Stack

**Project:** Phase 5.9 LLM Graph Interface Improvements
**Researched:** 2026-01-27

## Recommended Stack

### Core Analysis Infrastructure

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Slither | 0.10.x+ | CFG, SlithIR, data dependency | Already integrated; provides SSA form and CFG structure |
| Python | 3.10+ | Implementation | Project requirement; matches Slither |
| NetworkX | 3.x | Graph algorithms (dominance) | Mature, well-tested graph library with dominator algorithms |

**Dominance computation:** Use NetworkX's `immediate_dominators()` or implement Cooper-Harvey-Kennedy iterative algorithm. The iterative approach is simpler and faster for typical CFG sizes (< 30,000 nodes).

### Schema and Validation

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| JSON Schema | 2020-12 | Interface contract validation | Industry standard; supported by Pydantic |
| Pydantic | 2.x | Python schema enforcement | Type-safe, generates JSON Schema, fast validation |
| jsonschema | 4.x | Schema validation library | Reference implementation for JSON Schema |

**Note:** Pydantic 2.x is preferred over v1 for performance. Use `model_json_schema()` to generate JSON Schema for external tools.

### Evidence and Interoperability

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| SARIF | 2.1.0 | Evidence reference format | OASIS standard; tool interoperability |
| CWE | Current | Weakness classification | Industry standard for vulnerability taxonomy |

**Note:** SARIF provides `physicalLocation` (file, line, column) and `logicalLocation` (namespace, function) which map directly to our evidence ref requirements.

### LLM Interface

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Structured Outputs | API-native | Response validation | OpenAI, Anthropic support native schema enforcement |
| Pydantic | 2.x | Response parsing | Type-safe, automatic retry on validation failure |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| structlog | 24.x | Structured logging | All modules; already integrated |
| xxhash | 3.x | Fast hashing | Build hash computation |
| semver | 3.x | Version comparison | Interface version compatibility checks |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Dominance | NetworkX/iterative | Lengauer-Tarjan | Iterative is simpler, faster for our CFG sizes |
| Schema | Pydantic + JSON Schema | Protocol Buffers | JSON is LLM-native; protobuf adds complexity |
| Schema | Pydantic + JSON Schema | TypedDict | No runtime validation |
| Evidence | SARIF | Custom format | SARIF is industry standard; tool interop |
| Hashing | xxhash | SHA256 | xxhash is faster for content hashing |

## Key Design Decisions

### 1. Dominance Algorithm: Iterative over Lengauer-Tarjan

Per Cooper-Harvey-Kennedy (2001): "The iterative algorithm is simpler, easier to understand, easier to implement, and faster in practice... it should be the technique of choice."

For CFGs under 30,000 nodes (all smart contracts), the iterative approach wins on simplicity and real-world performance. Asymptotic complexity only matters for unreasonably large graphs.

**Implementation:**
```python
def compute_dominators(cfg_nodes, entry_node):
    """Compute immediate dominators using iterative algorithm."""
    dom = {n: set(cfg_nodes) for n in cfg_nodes}
    dom[entry_node] = {entry_node}
    changed = True
    while changed:
        changed = False
        for n in cfg_nodes:
            if n == entry_node:
                continue
            new_dom = set.intersection(*[dom[p] for p in predecessors(n)]) | {n}
            if new_dom != dom[n]:
                dom[n] = new_dom
                changed = True
    return dom
```

### 2. Schema: JSON Schema 2020-12 with Pydantic

JSON Schema is the de facto standard for LLM structured outputs. OpenAI, Anthropic, and open-source tools all support it. Pydantic 2.x provides:
- Type-safe Python models
- Automatic JSON Schema generation
- Fast validation
- Automatic coercion where appropriate

**Example:**
```python
from pydantic import BaseModel, Field
from typing import Literal

class ClauseStatus(BaseModel):
    clause: str
    status: Literal["matched", "failed", "unknown"]
    evidence_refs: list[str] = Field(default_factory=list)
    omission_refs: list[str] = Field(default_factory=list)
```

### 3. Evidence: SARIF-Compatible References

SARIF 2.1.0 provides `physicalLocation` and `logicalLocation` that map to our needs:

```yaml
# Our evidence ref
evidence_ref:
  file: "Token.sol"
  line: 42
  node_id: "N-123"
  snippet_id: "EVD-001"
  build_hash: "abc123"

# SARIF equivalent
location:
  physicalLocation:
    artifactLocation:
      uri: "Token.sol"
    region:
      startLine: 42
  logicalLocation:
    fullyQualifiedName: "Token.withdraw"
```

### 4. Hash Algorithm: xxhash for Build Hashes

xxhash is non-cryptographic but extremely fast. For content-addressable evidence IDs, collision resistance is less important than speed. SHA256 would work but adds latency.

## Installation

```bash
# Core (already in project)
uv add slither-analyzer networkx

# Schema validation
uv add pydantic jsonschema

# Supporting
uv add xxhash semver structlog
```

## Version Compatibility Matrix

| Component | Min Version | Max Tested | Notes |
|-----------|-------------|------------|-------|
| Python | 3.10 | 3.12 | Project requirement |
| Slither | 0.10.0 | 0.10.x | SlithIR API stable |
| Pydantic | 2.0 | 2.x | v1 API incompatible |
| NetworkX | 3.0 | 3.x | Stable API |
| JSON Schema | 2020-12 | 2020-12 | Use latest draft |

## Sources

- [Slither GitHub](https://github.com/crytic/slither)
- [A Simple, Fast Dominance Algorithm](https://www.cs.tufts.edu/comp/150FP/archive/keith-cooper/dom14.pdf)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [JSON Schema 2020-12](https://json-schema.org/draft/2020-12/json-schema-core.html)
- [SARIF 2.1.0 Specification](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html)
