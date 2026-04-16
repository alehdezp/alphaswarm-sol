# Semantic-Agnostic Detection System v2

Status: experimental concept, not an implementation plan. This document captures ideas,
risks, and open questions. It should be read as a critique plus a menu of options, not
as a roadmap.

Goal: name-agnostic vulnerability detection without exploding build time or sacrificing
determinism and testability.

## Brutal Critique of v1 (pattern-robustness-ideas.md)

The original document is **too conservative**. It commits several design sins:

### 1. False Dichotomy: Determinism vs LLM Usage

The document assumes `LLM = non-determinism`. This is wrong. LLM outputs are deterministic
when:
- Temperature = 0
- Model version is pinned
- Prompts are identical
- Results are cached

The real concern is **reproducibility across environments**, which is solvable through
artifact caching. We threw away the most powerful tool available because of a
misunderstanding.

### 2. "Semantic Roles from Static Analysis" is Still Brittle

Proposing to derive roles like `is_upgrade_like` from syntax/dataflow just moves the
brittleness. How do you detect "upgrade-like" behavior without knowing what upgrade means
semantically? You're still hardcoding patterns, just at a different abstraction level.

### 3. Missing the Embedding Revolution

**Zero mention of semantic embeddings.** This is a massive oversight. Embeddings enable
matching by MEANING, not by string patterns. Two functions that do the same thing have
similar embeddings regardless of naming.

### 4. Pattern Engine Extensions are Incremental

Adding edge constraints is nice but doesn't solve the fundamental problem: we're matching
against developer-chosen identifiers, and developers don't follow our naming conventions.

### 5. Two-Tier Matching is a Cop-Out

Labeling results as "suspicion" instead of improving detection quality is avoiding the
hard problem. Users want fewer tiers, not more.

### 6. "LLM as Offline Assistant" Wastes the Technology

Treating LLMs as suggestion generators rather than reasoning engines underutilizes them by
an order of magnitude.

---

## Brutal Critique of v2 (This Document)

This v2 design reads like a research thesis, not an execution plan. It is
over-ambitious, under-specified, and likely too slow for real use. Specific
problems:

1. Layer boundaries are fuzzy. Layer 1 vs Layer 2 is not crisp. Both depend on
   dataflow, both are semantic, and the distinction is unclear for pattern
   authors.
2. Integration is missing. There is no mapping to actual code paths
   (`builder.py`, pattern YAML, pattern engine). Without that, it cannot be
   implemented or tested.
3. Runtime cost is hand-waved. With current runs already taking ~3 hours on a
   medium project, adding embeddings and LLMs risks doubling or tripling build
   time.
4. Data requirements are unrealistic. Semantic similarity needs a prototype
   library or labeled corpus. We do not have one, and the doc does not say how
   to build it.
5. "LLM layer is critical" is wrong. It is the most expensive, least reliable
   layer and should never be mandatory.
6. Confidence aggregation is undefined. Weighted sums without calibration are
   cosmetic. Without validated thresholds, "confidence" is not meaningful.
7. Security and stability risks are ignored: prompt injection, model updates,
   vendor downtime, and non-deterministic outputs across environments.

If we want practical impact, the plan must be trimmed to the smallest set of
deterministic improvements with strict time budgets.

## Critical Questions and Unknowns

Answer these before any implementation:

1. What is the maximum acceptable build time increase for default runs?
2. Which layers can be run offline with no new dependencies?
3. What is the minimum viable layer set that improves recall today?
4. How will new layers be validated without a large labeled corpus?
5. How will pattern authors debug multi-layer matches?
6. What is the rollback strategy if a layer increases false positives?
7. How will we prevent LLM prompt injection via code comments?

## The New Architecture: Multi-Layer Semantic Detection

### Core Insight

The solution is not smarter string matching. It's **multiple independent detection
layers** that aggregate confidence. If naming breaks one layer, others still catch the
vulnerability.

```
┌───────────────────────────────────────────────────────────────────┐
│                    SEMANTIC BSKG PIPELINE                          │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  SOLIDITY CODE                                                    │
│       │                                                           │
│       ▼                                                           │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │           BUILD PHASE (Enrichment Layers)                    │ │
│  │                                                              │ │
│  │  1. Slither Analysis (AST, CFG, dataflow) ──────────────┐   │ │
│  │       │                                                  │   │ │
│  │  2. Behavioral Fingerprinting                            │   │ │
│  │       │  • Abstract dataflow graphs                      │   │ │
│  │       │  • Canonical operation sequences                 │   │ │
│  │       │                                                  │   │ │
│  │  3. Compositional Semantic Operators                     │   │ │
│  │       │  • READS_EXTERNAL_VALUE, WRITES_USER_BALANCE     │   │ │
│  │       │  • Temporal ordering: before/after               │   │ │
│  │       │                                                  │   │ │
│  │  4. Semantic Embedding (optional)                        │   │ │
│  │       │  • Code2Vec / CodeBERT embeddings                │   │ │
│  │       │  • Prototype similarity scores                   │   │ │
│  │       │                                                  ▼   │ │
│  │  5. LLM Annotation (optional, premium)            ENRICHED   │ │
│  │       │  • Semantic tags                          KNOWLEDGE  │ │
│  │       │  • Business logic context                 GRAPH      │ │
│  │       │  • Developer intent inference                        │ │
│  │       ▼                                                      │ │
│  │  (nodes have fingerprints, embeddings, ops, tags)           │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │           QUERY PHASE (Multi-layer Matching)                 │ │
│  │                                                              │ │
│  │  Patterns match on ANY layer:                                │ │
│  │  • Layer 0: Properties & regex (existing)                    │ │
│  │  • Layer 1: Behavioral fingerprints                          │ │
│  │  • Layer 2: Compositional operators                          │ │
│  │  • Layer 3: Embedding similarity                             │ │
│  │  • Layer 4: Semantic tags                                    │ │
│  │                                                              │ │
│  │  Multi-layer confidence aggregation                          │ │
│  │  Graceful degradation when layers unavailable                │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

**KEY INSIGHT:** The graph is enriched at BUILD TIME. Query time is deterministic
for deterministic layers. Embeddings and LLM annotations are optional and may
introduce new dependencies, costs, and operational risks.

---

## What The Layers Actually Mean (Clarified)

Layer 0 (existing):
- Property/regex matching on graph nodes.
- Already implemented in pattern packs.

Layer 1 (Behavioral Fingerprint):
- A canonical summary of control-flow and dataflow shape.
- Used to match behaviors regardless of identifier names.

Layer 2 (Compositional Operations):
- A small set of atomic operations derived from existing properties.
- Used to build patterns by composition and ordering.

Layer 3 (Embeddings, optional):
- Similarity scores against prototypes or small reference library.
- Requires model infra and threshold tuning.

Layer 4 (LLM annotations, optional):
- Tags and intent inference from external model calls.
- Highest cost, lowest reliability, should never be required.

Rule of thumb: Layers 1-2 should be the core. Layers 3-4 are research-only
until they can prove value without destroying runtime budgets.

---

## Integration With Current Project (Concrete)

Mapping to the current codebase:

- Build phase: `src/true_vkg/kg/builder.py`
  - Add Function node properties:
    - `fingerprint` and `fingerprint_components` (Layer 1)
    - `semantic_operations` and `operation_sequence` (Layer 2)
    - Optional: `prototype_similarities` (Layer 3)
    - Optional: `llm_annotations` (Layer 4)
- Pattern engine: `src/true_vkg/queries/patterns.py`
  - Add match ops for fingerprints, operation sequences, and similarity scores.
- Pattern packs: `patterns/*.yaml`
  - Add composition-based patterns that avoid name regex.
- Tests: `tests/`
  - Add fixtures that prove renamed code still matches.
  - Assert new properties directly, not only pattern matches.

If a layer cannot map to these points, it should not exist.

---

## Hard Constraints (Time, Cost, and Data)

Current runtime is ~3 hours on medium projects. Any new layer must respect:

- Default build time budget: <= 1.5x current runtime.
- No mandatory network calls for default runs.
- No requirement for a large labeled dataset.
- Clear opt-in flags for expensive layers.

Layers that violate these are optional or out of scope.

---

## De-scope Candidates (For Now)

These items add major cost but unclear near-term value:

- Embeddings without a curated prototype library.
- LLM annotations on all functions (too slow and too expensive).
- Weighted confidence aggregation without calibrated thresholds.
- Any layer that requires new infrastructure before we can validate benefits.

If the system is already slow, these should be postponed.

---

## Layer 1: Behavioral Fingerprinting

### Concept

Instead of matching on properties, match on **BEHAVIORAL SIGNATURES**—abstract
representations of what code DOES, not what it's NAMED.

A behavioral fingerprint captures:
- Abstract control flow shape (loops, branches, guards)
- Data flow signature (inputs → transformations → outputs)
- State interaction pattern (read X → compute → write Y)
- External call signature (call type, value movement, return handling)
- Temporal ordering (what happens before/after what)

### Example: Vulnerable Withdrawal Fingerprint

```
[READ:mapping(address→uint)] →
[EXTERNAL_CALL:value_transfer] →
[WRITE:mapping(address→uint)]
```

This matches ANY function with this shape, regardless of variable names like `balances`,
`deposits`, `userFunds`, or even `x123`.

### Why This Works

Fingerprints are **canonical**—they abstract away names entirely. Two functions with
identical fingerprints behave identically from a security perspective.

### Implementation

```python
# In builder.py
def compute_behavioral_fingerprint(function) -> str:
    """Compute abstract behavioral fingerprint for a function."""
    operations = []

    for node in function.dataflow_nodes:
        op = canonicalize_operation(node)
        # e.g., "READ:mapping(address→uint)" not "READ:balances"
        operations.append(op)

    # Include control flow shape
    cfg_shape = abstract_cfg_signature(function.cfg)

    # Include temporal relationships
    ordering = extract_temporal_ordering(function)

    return hash_fingerprint(operations, cfg_shape, ordering)

# On Function node
function_node.fingerprint = compute_behavioral_fingerprint(func)
function_node.fingerprint_components = {
    "operations": [...],
    "cfg_shape": "...",
    "temporal_ordering": [...]
}
```

### Pattern Matching Against Fingerprints

```yaml
pattern: reentrancy-classic
layers:
  behavioral:
    fingerprint_contains:
      - "EXTERNAL_CALL:value_transfer"
    temporal_constraint:
      before: "EXTERNAL_CALL:value_transfer"
      after: "WRITE:mapping(address→uint)"
```

### Trade-offs

| Aspect | Assessment |
|--------|------------|
| **Value** | HIGH - Truly name-agnostic, works on obfuscated code |
| **Determinism** | 100% deterministic |
| **Cost** | Medium - Requires dataflow extraction |
| **Limitations** | May be too abstract (FPs from similar-shaped safe code) |
| **Effort** | Medium - Needs careful dataflow canonicalization |

### Concerns

- Overlap with Layer 2: if the operation sequence is already captured, is a separate
  fingerprint necessary, or can we derive fingerprints from operations only?
- Risk of false positives if the fingerprint ignores guards or error handling.

---

## Layer 2: Compositional Semantic Operators

### Concept

Instead of monolithic patterns, define **ATOMIC SEMANTIC OPERATIONS** that compose.

### Atomic Operations (Computed During Build)

| Operation | Definition |
|-----------|------------|
| `READS_EXTERNAL_VALUE` | Calls external contract, uses return value |
| `WRITES_USER_BALANCE` | Writes to mapping[address] |
| `TRANSFERS_VALUE_OUT` | ETH transfer or token transfer out |
| `RECEIVES_VALUE_IN` | Receives ETH or tokens |
| `CHECKS_PERMISSION` | Compares msg.sender, role checks |
| `USES_TIMESTAMP` | Uses block.timestamp in logic |
| `MODIFIES_CRITICAL_STATE` | Writes impl slot, owner, paused, etc. |
| `CALLS_UNTRUSTED` | delegatecall, arbitrary call target |
| `LOOPS_OVER_ARRAY` | Iterates over dynamic array |
| `PERFORMS_DIVISION` | Division operation on user input |

### Patterns as Compositions

```yaml
pattern: unprotected-balance-withdrawal
composition:
  required:
    - WRITES_USER_BALANCE
    - TRANSFERS_VALUE_OUT
  absent:
    - CHECKS_PERMISSION
  sequence_matters: false

pattern: reentrancy-classic
composition:
  sequence:
    - TRANSFERS_VALUE_OUT  # First: external call
    - WRITES_USER_BALANCE  # Then: state update
  sequence_matters: true
```

### Why This is Better Than Properties

1. **Operations are derived from behavior, not names**
2. **Temporal relationships are explicit** (before/after)
3. **Absence of operations is meaningful** (`absent: CHECKS_PERMISSION`)
4. **Compositions scale arbitrarily** (combine any operations)

### Implementation

```python
# In builder.py
SEMANTIC_OPERATIONS = {
    "READS_EXTERNAL_VALUE": lambda f: f.has_external_calls and f.uses_return_value,
    "WRITES_USER_BALANCE": lambda f: any(
        is_user_keyed_mapping(w) for w in f.state_writes
    ),
    "TRANSFERS_VALUE_OUT": lambda f: f.sends_eth or f.transfers_tokens,
    "CHECKS_PERMISSION": lambda f: f.has_access_gate or f.compares_msg_sender,
    # ...
}

def derive_operations(function) -> List[str]:
    ops = []
    for name, predicate in SEMANTIC_OPERATIONS.items():
        if predicate(function):
            ops.append(name)
    return ops

def derive_operation_sequence(function) -> List[Tuple[str, int]]:
    """Return operations with their relative ordering."""
    # Extract from CFG traversal
    ...

# On Function node
function_node.semantic_operations = derive_operations(func)
function_node.operation_sequence = derive_operation_sequence(func)
```

### Trade-offs

| Aspect | Assessment |
|--------|------------|
| **Value** | HIGH - Expressive, maintainable, composable |
| **Determinism** | 100% deterministic |
| **Cost** | Low - Simple predicates on existing properties |
| **Limitations** | Need to define the right atomic operations |
| **Effort** | Medium - Requires identifying useful operations |

### Concerns

- Risk of turning operations into another hardcoded taxonomy that drifts from real-world
  patterns.
- If operations are too coarse, patterns become noisy; if too fine, patterns become
  brittle and expensive.

---

## Layer 3: Semantic Embeddings (Research, Optional)

### Concept

Embed each function based on its **abstract behavior**, not its names. Two functions that
do the same thing have similar embeddings regardless of naming.

### Implementation Options

**Option A: Code2Vec-style AST Path Embeddings**
- Extract AST paths from function body
- Replace identifiers with type tokens
- Embed path contexts
- Fast, no external API needed

**Option B: CodeBERT / UniXcoder**
- Normalize code (replace names with placeholders)
- Embed normalized code
- Higher quality, requires model dependency

**Option C: Hybrid**
- Use AST embeddings by default (fast, offline)
- Optionally augment with transformer embeddings

### Prototype Similarity Matching

```yaml
prototypes/
  reentrancy/
    classic.sol         # Classic CEI violation
    read-only.sol       # Read-only reentrancy
    cross-function.sol  # Cross-function reentrancy
  upgrade/
    uups-basic.sol      # Basic UUPS upgrade
    transparent.sol     # Transparent proxy upgrade
```

At build time:
1. Embed all prototypes
2. Embed all target functions
3. Compute similarity scores
4. Store top-N prototype matches per function

```yaml
# On Function node
function_node.prototype_similarities = {
    "reentrancy/classic": 0.89,
    "upgrade/uups-basic": 0.23,
    ...
}
```

### Pattern Matching with Embeddings

```yaml
pattern: reentrancy-any-variant
layers:
  embedding:
    similar_to_any_prototype:
      - "reentrancy/classic"
      - "reentrancy/read-only"
      - "reentrancy/cross-function"
    min_similarity: 0.75
```

### Determinism and Reality Check

Same model + same input should produce the same embedding, but in practice this can
drift due to runtime differences, library versions, GPU/CPU kernels, and updates in
dependency stacks. "Deterministic" here means "repeatable given pinned artifacts and
environment."

```json
{
  "graph_metadata": {
    "embedding_model": "code2vec-solidity-v1.0",
    "embedding_hash": "sha256:abc123...",
    "computed_at": "2025-01-15T..."
  }
}
```

### Trade-offs

| Aspect | Assessment |
|--------|------------|
| **Value** | HIGH - Catches semantic similarity rules miss |
| **Determinism** | Deterministic only with pinned model + pinned environment |
| **Cost** | High - Requires embedding model, storage |
| **Limitations** | Threshold tuning, model updates change results |
| **Effort** | High - Needs embedding infrastructure |

### Critical Concerns

1. No dataset. Without a prototype library or labeled corpus, similarity scores are
   arbitrary. We do not have one today.
2. No proof of value. There are few success stories showing embeddings materially
   improving static vulnerability detection.
3. Runtime cost. Embedding every function and computing similarity can be expensive.
4. Calibration risk. If similarity thresholds are wrong, this layer is noise.

### Open Questions

- What is the smallest prototype library that yields real recall gains?
- Can fingerprints + operations cover most of the benefit without embeddings?
- Can we build a PoC using only existing fixtures to validate any lift?

---

## Layer 4: Build-Time LLM Annotation (Research, Optional)

### Concept

During `build-kg`, **optionally** run an LLM annotation pass that analyzes each function
with full context and assigns semantic understanding.

### What LLM Annotates

```yaml
# On Function node
function_node.llm_annotations:
  semantic_tags:
    - "withdrawal"
    - "balance_update"
    - "user_funds_access"
  business_description: "Allows users to withdraw their deposited ETH balance"
  developer_intent: "Safely transfer user funds with reentrancy protection"
  vulnerability_flags:
    - tag: "potential_reentrancy"
      reason: "External call before state update"
      confidence: 0.85
  security_assumptions:
    - "Assumes reentrancy guard is applied via modifier"
  context_dependencies:
    - "Depends on balances mapping being accurate"
  model_info:
    model: "claude-opus-4-5-20250101"
    temperature: 0
    prompt_version: "v2.1"
    annotation_hash: "sha256:def456..."
```

### Annotation Process

```python
async def annotate_with_llm(graph: KnowledgeGraph, config: AnnotationConfig):
    """Add LLM annotations to graph nodes."""

    # First pass: understand project context
    project_context = await analyze_project_context(graph)

    # Second pass: annotate each function with context
    for function in graph.functions:
        annotations = await annotate_function(
            function=function,
            project_context=project_context,
            model=config.model,
            temperature=0,  # Deterministic
        )
        function.llm_annotations = annotations

    # Store annotation metadata for reproducibility
    graph.metadata.llm_annotation = {
        "model": config.model,
        "prompt_version": config.prompt_version,
        "annotation_hash": compute_annotation_hash(graph),
    }
```

### Pattern Matching with LLM Tags

```yaml
pattern: unsafe-upgrade-llm
layers:
  llm_tags:
    has_any_tag:
      - "upgrade_mechanism"
      - "implementation_change"
      - "proxy_admin_function"
    has_vulnerability_flag: "unprotected_upgrade"
```

### Two Modes

**Static Mode (default):** No LLM, fully offline, Layers 0-3 only **Semantic Mode
(opt-in):** Includes LLM annotation, Layer 4 available

```bash
# Static build (default)
uv run alphaswarm build-kg project/

# Semantic build with LLM annotation
uv run alphaswarm build-kg project/ --semantic --model claude-opus-4-5-20250101
```

### Cost Control

LLM annotation is expensive. Strategies to control cost:

1. **Selective annotation:** Only annotate public/external functions
2. **Caching:** Annotations cached by function content hash
3. **Incremental:** Only re-annotate changed functions
4. **Batch processing:** Group API calls for efficiency

### Reproducibility Contract

Annotations are reproducible IF:
1. Model version is pinned
2. Temperature = 0
3. Prompts are versioned
4. Graph stores annotation hash for verification

```python
def verify_annotations(graph: KnowledgeGraph) -> bool:
    """Verify annotations are reproducible."""
    stored_hash = graph.metadata.llm_annotation.annotation_hash
    computed_hash = compute_annotation_hash(graph)
    return stored_hash == computed_hash
```

### Trade-offs

| Aspect | Assessment |
|--------|------------|
| **Value** | VERY HIGH - Most powerful semantic understanding |
| **Determinism** | Low-to-medium, depends on vendor stability and prompt control |
| **Cost** | VERY HIGH - API costs, build time |
| **Limitations** | Model version changes, requires network |
| **Effort** | High - Needs prompt engineering, caching |

### Critical Concerns

1. Cost and time: This can easily double or triple build time on medium projects.
2. Trust: LLM tags can be wrong or inconsistent, and false positives are hard to debug.
3. Security: Prompt injection via code comments or strings is a real risk.
4. Reproducibility: Even with temperature 0, vendor changes can shift outputs.

### If We Ever Do This

- Must be opt-in and off by default.
- Must run only on filtered subsets (public/external functions, or functions
  already flagged by deterministic layers).
- Must store prompt version and artifact hashes to allow auditing.

---

## Multi-Layer Pattern Schema

Reality check: this schema does not exist in the current pattern engine. It
would require changes to YAML parsing, matching logic, and reporting. Treat
this as a design sketch, not a drop-in example.

### Full Pattern Example

```yaml
id: upg-006-unprotected-upgrade-multi
name: Unprotected Upgrade Function (Multi-Layer)
description: >
  Detects upgrade functions without proper access control using
  multiple detection layers for name-agnostic matching.
scope: Function
lens:
  - Upgradeability
severity: critical

layers:
  # Layer 0: Traditional property matching
  syntactic:
    weight: 0.2
    match:
      any:
        - property: label
          op: regex
          value: ".*[Uu]pgrade.*"
        - property: label
          op: regex
          value: ".*[Mm]igrate.*[Ii]mpl.*"
      all:
        - property: writes_implementation_slot
          op: eq
          value: true
        - property: has_access_gate
          op: eq
          value: false

  # Layer 1: Behavioral fingerprint
  behavioral:
    weight: 0.25
    fingerprint_contains:
      - "WRITES_STORAGE_SLOT(EIP1967_IMPL)"
      - "CHANGES_DELEGATECALL_TARGET"
    absent_operations:
      - "CHECKS_PERMISSION"

  # Layer 2: Compositional operators
  compositional:
    weight: 0.25
    required_operations:
      - MODIFIES_CRITICAL_STATE
    absent_operations:
      - CHECKS_PERMISSION

  # Layer 3: Embedding similarity
  embedding:
    weight: 0.15
    similar_to_prototype: "upgrade/uups-unprotected.sol"
    min_similarity: 0.70

  # Layer 4: LLM semantic tags (optional)
  semantic:
    weight: 0.15
    has_any_tag:
      - "upgrade_mechanism"
      - "implementation_change"
    absent_tag: "access_controlled"

# Aggregation rules
aggregation:
  mode: weighted_sum  # or: any_layer, all_layers, threshold_count
  minimum_confidence: 0.5
  minimum_layers_matched: 2  # At least 2 layers must match

# Evidence configuration
evidence:
  include_matched_layers: true
  include_confidence_breakdown: true
```

### Aggregation Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `weighted_sum` | Sum of layer weights where matched | Default, balanced |
| `any_layer` | Match if any layer matches | High recall |
| `all_layers` | Match only if all layers match | High precision |
| `threshold_count` | Match if N+ layers match | Configurable |

---

## Concrete Example: Detecting UPG-006 Without "UUPS" in Names

### The Problem

Current pattern: `label matches ".*[Uu]pgrade.*"` fails when function is named
`migrateImplementation()` or `setNewLogic()` or even `f7x()`.

### Multi-Layer Solution

```
Function: migrateImplementation()
├── Layer 0 (Syntactic)
│   ├── Name regex: FAIL ❌ (no "upgrade" in name)
│   └── Property check: PASS ✓ (writes_implementation_slot=true)
│       Confidence contribution: 0.10 (partial match)
│
├── Layer 1 (Behavioral)
│   └── Fingerprint: PASS ✓
│       Contains: WRITES_STORAGE_SLOT(EIP1967_IMPL)
│       Confidence contribution: 0.25
│
├── Layer 2 (Compositional)
│   └── Operations: PASS ✓
│       Has: MODIFIES_CRITICAL_STATE
│       Missing: CHECKS_PERMISSION
│       Confidence contribution: 0.25
│
├── Layer 3 (Embedding)
│   └── Similarity: PASS ✓
│       Similar to "upgrade/uups-basic.sol": 0.82
│       Confidence contribution: 0.15
│
└── Layer 4 (LLM Tags)
    └── Tags: PASS ✓
        Has: ["upgrade_mechanism", "implementation_change"]
        Confidence contribution: 0.15

TOTAL CONFIDENCE: 0.90 (exceeds minimum 0.5)
LAYERS MATCHED: 5/5
VERDICT: HIGH CONFIDENCE MATCH
```

Even if Layer 0 regex fails completely, Layers 1-4 catch the vulnerability with high
confidence.

---

## Prototype Library Structure

Reality check: this library does not exist today. If we cannot curate it, Layer 3 is
blocked. A practical fallback is to seed prototypes from `tests/contracts/` and expand
slowly over time.

### Directory Layout

```
prototypes/
├── reentrancy/
│   ├── classic.sol           # External call before state update
│   ├── read-only.sol         # Read-only reentrancy
│   ├── cross-function.sol    # Cross-function reentrancy
│   └── cross-contract.sol    # Cross-contract reentrancy
├── access-control/
│   ├── missing-auth.sol      # Public function, no access check
│   ├── tx-origin.sol         # tx.origin for auth
│   └── weak-modifier.sol     # Bypassable modifier
├── upgrade/
│   ├── uups-unprotected.sol  # UUPS without access control
│   ├── transparent-clash.sol # Function selector clash
│   └── initialize-front.sol  # Frontrunnable initializer
├── oracle/
│   ├── stale-price.sol       # No freshness check
│   ├── single-source.sol     # Single oracle source
│   └── manipulation.sol      # Manipulatable price
├── arithmetic/
│   ├── overflow.sol          # Integer overflow
│   ├── division-zero.sol     # Division by zero
│   └── precision-loss.sol    # Precision loss
└── dos/
    ├── unbounded-loop.sol    # Loop over user-controlled array
    ├── gas-griefing.sol      # Griefable external calls
    └── block-stuffing.sol    # Block gas limit attacks
```

### Prototype Format

Each prototype includes:
1. Vulnerable code snippet
2. Metadata about the vulnerability
3. Pre-computed fingerprint and embedding

```solidity
// prototypes/reentrancy/classic.sol

// METADATA:
// vulnerability: reentrancy-classic
// cwe: CWE-841
// severity: high
// description: Classic reentrancy - external call before state update

contract ReentrancyClassicPrototype {
    mapping(address => uint256) public balances;

    // VULNERABLE FUNCTION
    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount);

        // External call BEFORE state update - vulnerable pattern
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success);

        // State update AFTER external call
        balances[msg.sender] -= amount;
    }
}
```

---

## Implementation Roadmap (Honest Assessment)

These timelines are optimistic and ignore integration/testing overhead. Given
current runtime (~3h on medium projects), performance work is a prerequisite.

### Phase 0: Performance Baseline (required)

**What:**
- Instrument build time by stage (Slither, graph build, pattern eval).
- Add caching/incremental rebuilds where possible.
- Establish a hard budget for default runs.

**Why First:**
- Without a budget, every new layer will be "just one more thing" and runtime
  will silently explode.

**Risks:**
- If baseline cannot be reduced, new layers should be deferred.

### Phase 1: Compositional Operators (2-3 weeks)

**What:**
- Define ~20 atomic semantic operations
- Add operation derivation to builder
- Add operation sequence tracking
- Extend pattern schema for compositions

**Why First:**
- Highest impact-to-effort ratio
- No new dependencies
- Immediate improvement in detection quality

**Risks:**
- Might miss important operations initially
- Iteration needed to find right abstraction level

### Phase 2: Behavioral Fingerprinting (3-4 weeks)

**What:**
- Design fingerprint format
- Implement dataflow canonicalization
- Add fingerprint computation to builder
- Add fingerprint matching to pattern engine

**Why Second:**
- Builds on Phase 1 operations
- Provides name-agnostic foundation
- Still fully deterministic

**Risks:**
- Slither's dataflow may not be detailed enough
- May need custom analysis passes

### Phase 3: Prototype Library (2-3 weeks, parallel with Phase 2)

**What:**
- Curate prototype library (~50 examples)
- Define prototype metadata format
- Add prototype loading to build phase
- Add similarity comparison (string-based initially)

**Why Parallel:**
- Independent workstream
- Provides test cases for other layers
- Useful even without embeddings

**Risks:**
- Curation effort is ongoing
- Quality depends on example selection
- If we cannot curate prototypes quickly, embeddings are blocked.

### Phase 4: Semantic Embeddings (research only, gated)

**What:**
- Evaluate embedding options (Code2Vec vs CodeBERT)
- Implement embedding computation
- Add embedding storage to graph
- Add similarity matching to pattern engine

**Why After Phases 1-3:**
- Most complex infrastructure
- Phases 1-3 provide baseline to compare against

**Risks:**
- Model dependency complicates deployment
- Threshold tuning is iterative
- Storage overhead
- Without a prototype library, this should not start.

### Phase 5: LLM Annotation (research only, gated)

**What:**
- Design annotation schema
- Implement annotation pipeline
- Add caching and incremental updates
- Add semantic tag matching to pattern engine

**Why Last:**
- Highest cost, highest complexity
- Phases 1-4 provide strong baseline
- Optional premium feature

**Risks:**
- API cost management
- Prompt engineering iteration
- Model version compatibility
- This should never be required for default runs.

### Phase 6: Multi-Layer Integration (2-3 weeks)

**What:**
- Implement confidence aggregation
- Add multi-layer pattern schema
- Update reporting for multi-layer results
- Performance optimization

**Why:**
- Ties everything together
- Requires all previous phases

**Risks:**
- Aggregation tuning is empirical
- May surface interactions between layers

---

## Brutal Honesty: What Could Go Wrong

### 1. Fingerprint Collision

**Problem:** Two semantically different functions could have similar fingerprints. A safe
withdrawal with reentrancy guard might fingerprint similarly to an unsafe one if the guard
isn't properly detected.

**Mitigation:** Fingerprints should include guard detection. Test thoroughly against
safe/unsafe pairs.

### 2. Embedding Drift

**Problem:** Embedding model updates change similarity scores. A function that matched
prototype at 0.78 might drop to 0.65 with a new model version.

**Mitigation:** Pin model versions. Store version in graph. Re-compute when upgrading
models. Use thresholds with margin.

### 3. LLM Hallucination

**Problem:** LLM might tag a function as "access_controlled" when it isn't, or miss a
subtle vulnerability.

**Mitigation:** LLM tags are one layer among many. Cross-validate with deterministic
layers. Require multiple layer agreement for high-confidence findings.

### 4. Computational Cost

**Problem:** Build time could explode with embeddings + LLM annotation.

**Mitigation:** Make layers optional. Cache aggressively. Incremental builds. Selective
annotation (public functions only).

### 5. False Positive Explosion

**Problem:** Multiple layers might over-trigger, flagging safe code.

**Mitigation:** Require minimum layers matched. Use `none` conditions for safe patterns.
Tune aggregation thresholds empirically.

### 6. Complexity Tax

**Problem:** System becomes harder to understand and debug. "Why did this match?" becomes
a complex multi-layer question.

**Mitigation:** Detailed evidence output showing each layer's contribution. Explain mode
that walks through matching logic.

---

## Lean Alternative (Practical Path)

If runtime and infra are the primary blockers, a smaller plan is better:

1. Expand deterministic roles in the builder (upgrade-like, balance-like,
   oracle-update-like) and store them as node properties.
2. Extend pattern engine to allow target-node property constraints (edge-aware
   matching). This replaces name regex in many patterns.
3. Add deterministic name normalization as a weak hint only, never as a primary
   signal.
4. Keep embeddings and LLMs out of the default build. Treat them as a future
   research track after we reduce baseline runtime.

This path aligns with the current architecture and avoids the heaviest costs.

---

## Comparison: Current vs Proposed

| Aspect | Current System | Proposed System |
|--------|----------------|-----------------|
| **Name Dependency** | High (regex on labels) | Low (multiple layers) |
| **Detection Robustness** | Brittle to renaming | Robust via multi-layer |
| **False Positives** | Low but misses renamed patterns | Tunable via thresholds |
| **False Negatives** | High for non-standard names | Low via semantic matching |
| **Determinism** | 100% | 100% for Layers 0-2, lower for optional Layers 3-4 |
| **Build Complexity** | Low | Medium-High (very high if Layer 3-4 enabled) |
| **Query Complexity** | Low | Medium |
| **Maintainability** | High | Medium (more moving parts) |
| **Extensibility** | Add YAML patterns | Add patterns + prototypes |

---

## Final Recommendation

**Start with Phase 0 (performance baseline), then Phases 1-2.**

These provide the highest improvement with lowest risk and no new dependencies, while
keeping build time under control. They establish the foundation for more advanced layers
while immediately improving detection robustness.

**Defer Phases 4-5 (Embeddings + LLM) until Phases 1-3 prove value and runtime is under
budget.**

These are high-investment features. Validate the multi-layer approach with deterministic
layers first before adding complex dependencies.

**The goal is not to replace regex with AI. The goal is to make regex one signal among
many, so that no single point of failure (like a renamed function) defeats detection.**

---

## Appendix A: Semantic Operation Definitions

| Operation | Detection Logic |
|-----------|-----------------|
| `READS_EXTERNAL_VALUE` | Has external call AND uses return value in computation |
| `WRITES_USER_BALANCE` | Writes to mapping where key is `msg.sender` or address parameter |
| `TRANSFERS_VALUE_OUT` | Contains `transfer`, `send`, `call{value}` sending ETH out |
| `RECEIVES_VALUE_IN` | Function has `payable` modifier or receives tokens |
| `CHECKS_PERMISSION` | Contains `msg.sender` comparison or uses access modifier |
| `USES_TIMESTAMP` | Uses `block.timestamp` in conditional or assignment |
| `MODIFIES_CRITICAL_STATE` | Writes to: owner, admin, implementation, paused, etc. |
| `CALLS_UNTRUSTED` | `delegatecall`, `call` with non-constant target |
| `LOOPS_OVER_ARRAY` | Has loop with array.length bound |
| `PERFORMS_DIVISION` | Division operation where divisor is user-influenced |
| `READS_ORACLE` | Calls external price feed or oracle contract |
| `EMITS_VALUE_EVENT` | Emits event containing value/amount |
| `INITIALIZES_STATE` | First write to storage variable (constructor-like) |
| `VALIDATES_INPUT` | Has require/assert on function parameters |

---

## Appendix B: Prototype Matching Algorithm

```python
def match_prototype(function: Function, prototype: Prototype) -> float:
    """Compute similarity between function and vulnerability prototype."""

    scores = []

    # 1. Fingerprint similarity (Jaccard on operations)
    fp_sim = jaccard(function.fingerprint_components.operations,
                     prototype.fingerprint_components.operations)
    scores.append(('fingerprint', fp_sim, 0.3))

    # 2. CFG shape similarity
    cfg_sim = cfg_shape_distance(function.cfg_shape, prototype.cfg_shape)
    scores.append(('cfg_shape', 1.0 - cfg_sim, 0.2))

    # 3. Operation sequence alignment (edit distance)
    seq_sim = 1.0 - normalized_edit_distance(
        function.operation_sequence,
        prototype.operation_sequence
    )
    scores.append(('sequence', seq_sim, 0.2))

    # 4. Embedding cosine similarity (if available)
    if function.embedding and prototype.embedding:
        emb_sim = cosine_similarity(function.embedding, prototype.embedding)
        scores.append(('embedding', emb_sim, 0.3))

    # Weighted average
    total_weight = sum(w for _, _, w in scores)
    similarity = sum(s * w for _, s, w in scores) / total_weight

    return similarity
```

---

## Appendix C: Evidence Output Example

```json
{
  "pattern": "upg-006-unprotected-upgrade-multi",
  "match": {
    "node_id": "func_Contract_migrateImplementation",
    "label": "migrateImplementation",
    "confidence": 0.90,
    "layers_matched": 5,
    "layer_details": {
      "syntactic": {
        "matched": true,
        "confidence": 0.10,
        "details": {
          "name_regex": false,
          "writes_implementation_slot": true,
          "has_access_gate": false
        }
      },
      "behavioral": {
        "matched": true,
        "confidence": 0.25,
        "details": {
          "fingerprint_matches": ["WRITES_STORAGE_SLOT(EIP1967_IMPL)"],
          "absent_confirmed": ["CHECKS_PERMISSION"]
        }
      },
      "compositional": {
        "matched": true,
        "confidence": 0.25,
        "details": {
          "has_operations": ["MODIFIES_CRITICAL_STATE"],
          "missing_operations": ["CHECKS_PERMISSION"]
        }
      },
      "embedding": {
        "matched": true,
        "confidence": 0.15,
        "details": {
          "closest_prototype": "upgrade/uups-basic.sol",
          "similarity": 0.82
        }
      },
      "semantic": {
        "matched": true,
        "confidence": 0.15,
        "details": {
          "matching_tags": ["upgrade_mechanism", "implementation_change"],
          "absent_tags_confirmed": ["access_controlled"]
        }
      }
    }
  },
  "evidence": {
    "code_snippet": "function migrateImplementation(address newImpl) external { ... }",
    "location": "Contract.sol:45"
  }
}
```
