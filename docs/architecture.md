# Architecture

**AlphaSwarm.sol system architecture and design principles.**

## Overview

AlphaSwarm.sol is a **Claude Code orchestration framework** for Solidity smart contract security. It builds a behavioral knowledge graph, coordinates AI agents (attacker/defender/verifier), and produces evidence-linked findings through a 9-stage audit pipeline.

**Key distinction:** This is NOT a CLI tool. Claude Code IS the orchestrator. See [PHILOSOPHY.md](PHILOSOPHY.md) for the execution model.

### What It Does

1. **Orchestrates** Claude Code to manage a 9-stage audit pipeline
2. **Builds** a Behavioral Security Knowledge Graph (BSKG) via Slither
3. **Derives** 200+ security properties per function
4. **Matches** 466 active vulnerability patterns (Tier A/B/C)
5. **Coordinates** specialized agents for investigation (3-4 functional)
6. **Debates** findings through attacker/defender/verifier protocol
7. **Produces** evidence-linked findings with proof tokens

### What It Is Not

- Not a standalone CLI tool (CLI is called BY Claude Code)
- Not a user-facing command-runner model (users drive workflows via `/vrs-*`)
- Not a symbolic executor or formal verifier
- Not a runtime fuzzer
- Not a machine learning model
- Not a replacement for human audits

## Core Principles

### 1. Behavior Over Names

Traditional tools detect functions named `withdraw()`. AlphaSwarm.sol detects the **behavior**:

```
R:bal -> X:out -> W:bal
(read balance, external call, write balance)
```

The function name is irrelevant. The behavioral pattern reveals vulnerability.

### 2. Deterministic Execution

Same code = identical results. No randomness, no probabilistic inference.

**Why**: Enables CI/CD integration, regression testing, reproducible audits.

### 3. Evidence-First Findings

Every finding links to exact file paths and line numbers with supporting evidence.

**Why**: Auditors need proof. LLMs need context.

### 4. Two-Tier Detection

| Tier | Purpose | Confidence |
|------|---------|------------|
| **Tier A** | Deterministic, graph-only | HIGH |
| **Tier B** | LLM-verified, exploratory | MEDIUM |
| **Tier C** | Label-dependent | MEDIUM |

### 5. Human Escalation

All findings route to human review. No fully autonomous verdicts.

## System Architecture

```
Solidity Source
    |
    v
+-------------------------------------------+
|           SLITHER ANALYSIS                |
|  - AST parsing                            |
|  - CFG construction                       |
|  - Dataflow analysis                      |
|  - IR generation                          |
+-------------------------------------------+
    |
    v
+-------------------------------------------+
|           VKG BUILDER                     |
|  src/alphaswarm_sol/kg/builder/           |
|  - ContractProcessor (1,377 LOC)          |
|  - FunctionProcessor (1,194 LOC)          |
|  - StateVarProcessor (317 LOC)            |
|  - CallTracker (1,160 LOC)                |
|  - ProxyResolver (825 LOC)                |
+-------------------------------------------+
    |
    v
+-------------------------------------------+
|         KNOWLEDGE GRAPH                   |
|  - 200+ security properties per function  |
|  - 20 semantic operations                 |
|  - Behavioral signatures                  |
|  - Deterministic IDs (SHA256)             |
+-------------------------------------------+
    |
    +----------------+
    |                |
    v                v
+---------------+  +----------------+
| PATTERN       |  | TOOL           |
| ENGINE        |  | INTEGRATION    |
| - Tier A/B/C  |  | - Slither      |
| - 466 pats    |  | - Aderyn       |
| - 21 label    |  | - Mythril      |
|   patterns    |  | - 7 adapters   |
+---------------+  +----------------+
    |                |
    v                v
+-------------------------------------------+
|           BEADS & POOLS                   |
|  - Investigation packages                 |
|  - Evidence tracking                      |
|  - Pool orchestration                     |
+-------------------------------------------+
    |
    v
+-------------------------------------------+
|       MULTI-AGENT VERIFICATION            |
|  - Attacker (opus)                        |
|  - Defender (sonnet)                      |
|  - Verifier (opus)                        |
|  - Debate protocol + proof tokens         |
+-------------------------------------------+
    |
    v
+-------------------------------------------+
|    VERDICTS + HUMAN ESCALATION            |
+-------------------------------------------+
```

## Core Modules

### Knowledge Graph Builder

**Location**: `src/alphaswarm_sol/kg/builder/`

| Module | LOC | Purpose |
|--------|-----|---------|
| `core.py` | 787 | VKGBuilder orchestration |
| `contracts.py` | 1,377 | Contract-level properties |
| `functions.py` | 1,194 | Function-level properties (225 fields) |
| `state_vars.py` | 317 | State variable analysis |
| `calls.py` | 1,160 | Call tracking with confidence |
| `proxy.py` | 825 | Proxy resolution (EIP-1967, UUPS, Diamond) |
| `helpers.py` | 551 | Utility functions |
| `completeness.py` | 489 | Build quality reports |

### Pattern Engine

**Location**: `vulndocs/`

- **466 active patterns** across 18 vulnerability categories (39 archived, 57 quarantined)
- **21 Tier C patterns** dependent on semantic labels
- YAML-based, human-readable definitions
- Organized by vulnerability type (reentrancy, access-control, oracle, etc.)

### Orchestration Layer

**Location**: `src/alphaswarm_sol/orchestration/`

| Module | LOC | Purpose |
|--------|-----|---------|
| `schemas.py` | 999 | Pool, Verdict, Scope definitions |
| `pool.py` | 507 | PoolStorage, PoolManager |
| `loop.py` | ~500 | Execution loop with route states |
| `debate.py` | 802 | Multi-agent debate protocol |
| `handlers.py` | 1,057 | 13 phase handlers |

### Agent Infrastructure

**Location**: `src/alphaswarm_sol/agents/`

| Subsystem | Files | LOC | Purpose |
|-----------|-------|-----|---------|
| `runtime/` | 11 | ~3,800 | Multi-SDK execution |
| `propulsion/` | 3 | ~1,800 | Task routing, cost tracking |
| `ranking/` | 5 | ~1,800 | Model selection with feedback |
| `roles/` | 4 | ~1,300 | Agent role definitions |

**Agent Catalog**: `src/alphaswarm_sol/agents/catalog.yaml`
- **24 agent definitions** (3-4 currently functional)
- Functional agents: attacker, defender, verifier, secure-reviewer
- Support agents (defined, not yet exercised): supervisor, integrator, test-builder, controller

### Tool Integration

**Location**: `src/alphaswarm_sol/tools/`

| Module | LOC | Purpose |
|--------|-----|---------|
| `coordinator.py` | 970 | Tool orchestration |
| `registry.py` | 648 | Discovery and health checks |
| `dedup.py` | 865 | Finding deduplication |
| `sarif.py` | 645 | SARIF normalization |
| `adapters/*` | ~4,000 | 7 tool adapters |

## Semantic Operations

Operations describe **behavior**, not function names:

| Category | Operations |
|----------|------------|
| **Value** | `TRANSFERS_VALUE_OUT`, `READS_USER_BALANCE`, `WRITES_USER_BALANCE` |
| **Access** | `CHECKS_PERMISSION`, `MODIFIES_OWNER`, `MODIFIES_ROLES` |
| **External** | `CALLS_EXTERNAL`, `CALLS_UNTRUSTED`, `READS_EXTERNAL_VALUE` |
| **State** | `MODIFIES_CRITICAL_STATE`, `READS_ORACLE`, `INITIALIZES_STATE` |
| **Arithmetic** | `PERFORMS_DIVISION`, `PERFORMS_MULTIPLICATION` |
| **Control** | `LOOPS_OVER_ARRAY`, `USES_TIMESTAMP`, `HAS_LOOP` |

## Behavioral Signatures

Signatures encode operation ordering:

```
R:bal -> X:out -> W:bal   # Reentrancy vulnerable
R:bal -> W:bal -> X:out   # Safe CEI pattern
C:auth -> M:crit          # Access control check
R:orc -> A:div -> X:out   # Oracle + division + transfer
```

| Code | Meaning |
|------|---------|
| `R:bal` | Read user balance |
| `W:bal` | Write user balance |
| `X:out` | Transfer value out |
| `X:call` | External call |
| `C:auth` | Permission check |
| `M:crit` | Modify critical state |
| `R:orc` | Read oracle |

## Beads and Pools

### Bead

A self-contained investigation package:

```yaml
id: VRS-042
status: investigating
vulnerability_class: access-control
pattern_id: access-control-permissive
location:
  file: src/Vault.sol
  contract: Vault
  function: setBalance
  lines: [138, 152]
behavioral_signature: M:crit
semantic_ops: [MODIFIES_CRITICAL_STATE]
evidence:
  - property: writes_privileged_state
  - property: has_access_gate = false
questions:
  - Who can reach setBalance across all call paths?
verdict: uncertain
confidence_score: 0.48
```

### Pool

Groups related beads for batch workflows:

```
Pool: audit-wave-erc4626
  |
  +-- VRS-042 (access-control) -> attacker + defender
  +-- VRS-043 (reentrancy)     -> test builder
  +-- VRS-044 (oracle)         -> verifier
  |
  +-- Integrator merges overlaps
  |
  +-- Supervisor escalates uncertain beads
```

## Confidence Buckets

| Bucket | Score | Meaning |
|--------|-------|---------|
| `confirmed` | - | Verified by test or multi-agent consensus |
| `likely` | >= 0.75 | Strong evidence, no exploit proof |
| `uncertain` | 0.40-0.75 | Weak or conflicting signals |
| `rejected` | - | Disproven or benign |

## Data Flow

### Build Phase

```
1. Slither parses Solidity -> AST, CFG, IR
2. VKGBuilder processes contracts, functions, variables
3. For each function:
   - Derive 200+ security properties
   - Detect semantic operations
   - Compute behavioral signature
   - Create edges to state variables
4. Serialize graph to JSON
```

### Query Phase

```
1. Parse input (NL, VQL, or JSON)
2. Build query plan
3. Execute against graph:
   - Filter nodes by type and properties
   - Check edge requirements
   - Apply path constraints
4. Return results with evidence
```

### Verification Phase

```
1. Create beads from findings
2. Route to agent pools
3. Execute debate protocol:
   - Attacker: construct exploit path
   - Defender: find guards/mitigations
   - Verifier: cross-check evidence
4. Integrate verdicts
5. Escalate uncertain findings
```

## Performance

### Build Times

| Project Size | Functions | Time | Graph Size |
|-------------|-----------|------|------------|
| Small | 10 | <1s | ~50KB |
| Medium | 50 | 2-3s | ~250KB |
| Large | 200 | 10-15s | ~1MB |

### Query Times

| Query Type | Time |
|-----------|------|
| Property filter | <10ms |
| Pattern match | <50ms |
| Flow query | <500ms |

## Design Decisions

### Why Slither?

| Alternative | Issue |
|-------------|-------|
| Raw Solc AST | No CFG, no dataflow |
| Mythril | Too slow (symbolic execution) |
| Manticore | Full symbolic, heavy |

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

## Related Documentation

- [Philosophy](PHILOSOPHY.md) - Vision and guiding principles
- [Properties Reference](reference/properties.md) - All 275 emitted security properties
- [Operations Reference](reference/operations.md) - Semantic operations
- [Pattern Guide](guides/patterns.md) - Writing custom patterns
