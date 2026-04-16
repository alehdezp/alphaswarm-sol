# System Architecture

**AlphaSwarm.sol Core Architecture & Design Principles**

---

## Overview

AlphaSwarm.sol is a **deterministic Solidity security reasoning system** that builds a knowledge graph from smart contract code for LLM-driven vulnerability discovery.

### What It Does

1. **Builds** a knowledge graph from Solidity via Slither
2. **Derives** 50+ security properties per function
3. **Enables** structured queries without ML training
4. **Provides** reproducible, evidence-backed results

### What It Is Not

- Not a symbolic executor or formal verifier
- Not a runtime fuzzer
- Not a machine learning model
- Not a replacement for human audits

---

## Core Principles

### 1. Deterministic Execution

Same code = identical results. No randomness, no probabilistic inference.

**Why**: Enables CI/CD integration, regression testing, reproducible audits.

### 2. Composable Properties

Small boolean properties combine into complex patterns.

**Example**: Reentrancy detection =
- `visibility in [public, external]` +
- `state_write_after_external_call == true` +
- `has_reentrancy_guard == false`

### 3. Evidence-First

Every finding links to exact file paths and line numbers.

**Why**: Auditors need proof. LLMs need context.

### 4. Lenses Over Lists

Model security primitives (Authority, Reentrancy, Oracle, MEV) rather than vulnerability checklists.

**Why**: Composable primitives enable novel pattern discovery.

---

## Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SOLIDITY CODE                            │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   SLITHER ANALYSIS                          │
│  • AST parsing                                              │
│  • CFG construction                                         │
│  • Dataflow analysis                                        │
│  • IR generation                                            │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                 BSKG BUILDER (builder.py)                    │
│  • Create nodes (Contract, Function, StateVariable, etc.)  │
│  • Derive 50+ security properties                          │
│  • Create edges (CONTAINS, TAINTS, CALLS, etc.)            │
│  • Extract invariants from NatSpec                         │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  KNOWLEDGE GRAPH (graph.json)               │
│  • Nodes with properties                                    │
│  • Edges with metadata                                      │
│  • Evidence with source locations                           │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    QUERY ENGINE                             │
├─────────────────────────────────────────────────────────────┤
│  Intent Parser    │ NL → Intent → QueryPlan                 │
│  Executor         │ Run queries against graph               │
│  Pattern Engine   │ Match YAML patterns                     │
│  Report Generator │ Lens-based reports                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Source Files

| File | Lines | Purpose |
|------|-------|---------|
| `kg/builder.py` | ~1000 | Graph construction, property derivation |
| `kg/schema.py` | ~200 | Node, Edge, KnowledgeGraph dataclasses |
| `kg/heuristics.py` | ~150 | Security tag classification |
| `kg/taint.py` | ~200 | Dataflow/taint modeling |
| `queries/executor.py` | ~400 | Query execution engine |
| `queries/patterns.py` | ~500 | Pattern pack matching |
| `queries/intent.py` | ~300 | NL/VQL parsing |

---

## Data Flow

### Build Phase

```
1. Slither parses Solidity → AST, CFG, IR
2. VKGBuilder iterates contracts, functions, variables
3. For each function:
   - Derive 50+ security properties
   - Detect operations (TRANSFERS_VALUE_OUT, etc.)
   - Compute behavioral signature
   - Create edges to state variables
4. Extract invariants from NatSpec comments
5. Serialize graph to JSON
```

### Query Phase

```
1. Parse input (NL, VQL, or JSON)
2. Create Intent object
3. Build QueryPlan
4. Execute:
   - Filter nodes by type and properties
   - Check edge requirements
   - Apply path constraints
   - Collect evidence
5. Return results with explanations
```

---

## Design Decisions

### Why Slither?

| Alternative | Issue |
|-------------|-------|
| Raw Solc AST | No CFG, no dataflow |
| Mythril | Too slow (symbolic execution) |
| Manticore | Same (full symbolic) |

**Slither**: Fast, has IR, actively maintained.

### Why JSON Storage?

| Alternative | Issue |
|-------------|-------|
| Neo4j | External dependency |
| SQLite | Relational doesn't fit graphs |
| Pickle | Not human-readable |

**JSON**: Diffable, no dependencies, LLM-friendly.

### Why YAML Patterns?

| Alternative | Issue |
|-------------|-------|
| Python DSL | Code execution risk |
| JSON | No comments, verbose |

**YAML**: Readable, commentable, safe.

---

## Performance

### Build Times

| Project Size | Functions | Time | Graph Size |
|-------------|-----------|------|------------|
| Small | 10 | <1s | ~50KB |
| Medium | 50 | 2-3s | ~250KB |
| Large | 200 | 10-15s | ~1MB |

**Bottleneck**: Slither (95% of time).

### Query Times

| Query Type | Time |
|-----------|------|
| Property filter | <10ms |
| Pattern match | <50ms |
| Flow query | <500ms |

### Memory

- Graph (100 functions): ~10MB
- Total working set: <100MB

---

## Two-Tier Architecture (Roadmap)

### Tier A: Deterministic (Current + Enhanced)

- Slither-based analysis
- 50+ properties
- 20 semantic operations
- Behavioral signatures
- Pattern matching

### Tier B: Semantic (Planned)

- LLM context enhancement
- Business intent analysis
- Risk tags
- False positive filtering

See [ROADMAP.md](../ROADMAP.md) for implementation plan.

---

## Testing Philosophy

1. **One fixture per vulnerability class**
2. **Positive AND negative test cases**
3. **Property assertions, not just pattern matches**
4. **Cached builds for speed**
5. **100% determinism (no flaky tests)**

---

*See [Graph Schema](graph-schema.md) for node/edge details.*
*See [ROADMAP.md](../ROADMAP.md) for enhancement plan.*
