# AlphaSwarm.sol - Project Status

**Last Updated:** 2026-01-22
**Version:** 5.0 (In Progress)
**Current Milestone:** 5.0 GA Release

---

## Executive Summary

AlphaSwarm.sol is building a **Vulnerability Knowledge Graph** for Solidity security analysis. The core detection system is working with **84.6% detection rate** on DVDeFi challenges.

| Component | Status | Evidence |
|-----------|--------|----------|
| Core Knowledge Graph | Working | 50+ properties, 20 semantic operations |
| DVDeFi Detection | 84.6% | 11/13 challenges detected |
| Builder Modularization | Complete | 10 modules, ~9,500 LOC |
| Beads System | Complete | 227 tests, Phase 4 done |
| Protocol Context Pack | Complete | Roles, assumptions, invariants |
| Semantic Labeling | Complete | 20 labels, 21 Tier C patterns |
| Tool Integration | Complete | 7 adapters, SARIF normalization |
| Multi-Agent SDK | Complete | Anthropic + OpenAI runtimes |
| OpenCode SDK Refactor | Complete | Multi-model routing, 75%+ cost savings |
| VulnDocs Framework | Complete | 7 VRS skills, 147 tests |

---

## Current Phase: Phase 5.5 - Agent Execution & Context Enhancement

**Status:** PENDING (ready to start)

**Previous Phase (5.4) Completed:** 2026-01-22
- Framework infrastructure built: `vulndocs/` at root with templates, validation, CLI, skills
- 147 tests passing, all CLI commands functional
- 7 VRS skills complete: discover, add-vulnerability, refine, test-pattern, research, merge-findings, generate-tests

**Next Actions:**
1. Run `/gsd:discuss-phase 5.5` to begin planning
2. Improve subagent accuracy with vulnerability-specific context
3. Integrate economic context and reasoning templates from VulnDocs

---

## Phase Status Overview

| Phase | Name | Status | Plans |
|-------|------|--------|-------|
| 1 | VulnDocs Completion | **COMPLETE** | 7/7 |
| 2 | Builder Foundation & Modularization | **COMPLETE** | 8/8 |
| 3 | Protocol Context Pack | **COMPLETE** | 6/6 |
| 4 | Orchestration Layer | **COMPLETE** | 7/7 |
| 5 | Semantic Labeling | **COMPLETE** | 9/9 |
| 5.1 | Static Analysis Tool Integration | **COMPLETE** | 10/10 |
| 5.2 | Multi-Agent SDK Integration | **COMPLETE** | 10/10 |
| 5.3 | OpenCode SDK Refactor | **COMPLETE** | 10/10 |
| 5.4 | VulnDocs-Patterns Unification | **COMPLETE** | 10/10 |
| 5.5 | Agent Execution & Context Enhancement | PENDING | 0/? |
| 5.6 | Orchestration Skill Separation | PENDING | 0/? |
| 6 | Release Preparation | PENDING | 0/5 |
| 7 | Final Testing (GA Gate) | PENDING | 0/11 |
| 8 | Test Performance Research | **COMPLETE** | 4/4 |

**Overall Progress:** ~76% complete (81/~107 plans)

---

## DVDeFi Detection Results

| Challenge | Expected | Detected | Status |
|-----------|----------|----------|--------|
| Unstoppable | dos-strict-equality | dos-strict-equality | Pass |
| Truster | auth-011, auth-017 | auth-011, auth-017 | Pass |
| Naive Receiver | callback-auth | external-call-public-no-gate | Pass |
| Side Entrance | reentrancy | reentrancy-basic | Pass |
| The Rewarder | flash-loan-reward-attack | flash-loan-reward-attack | Pass |
| Selfie | governance-flash-loan | governance-flash-loan | Pass |
| Compromised | oracle-manipulation | - | Fail (needs off-chain trust modeling) |
| Puppet | dex-oracle-manipulation | dex-oracle-manipulation | Pass |
| Puppet V2 | dex-oracle-manipulation | dex-oracle-manipulation | Pass |
| Puppet V3 | dex-oracle-manipulation | dex-oracle-manipulation | Pass |
| Free Rider | msg-value-loop-reuse | msg-value-loop-reuse | Pass |
| Backdoor | callback-controlled-recipient | callback-controlled-recipient | Pass |
| Climber | timelock-bypass | - | Fail |

**Detection Rate:** 11/13 (84.6%)

---

## What Works (Production-Ready)

### Core Knowledge Graph (Phase 2)
- Builds graph from Solidity via Slither
- Derives 50+ security properties per function
- 20 semantic operations for name-agnostic detection
- Behavioral signatures (`R:bal->X:out->W:bal`)
- Modular builder: 10 modules, ~9,500 LOC
- ProxyResolver: EIP-1967, UUPS, Diamond, Beacon patterns
- Deterministic IDs, completeness reports

### Pattern Engine
- 44 semantic patterns with operation matchers
- YAML-defined vulnerability checks
- 21 Tier C label-dependent patterns
- Operation sequencing detection
- Risk scoring and evidence linking

### Semantic Labeling (Phase 5)
- 20 labels across 6 categories
- LLM labeler with tool calling
- Tier C pattern matching
- 100% precision validated at exit gate

### Protocol Context Pack (Phase 3)
- Context schema with roles, assumptions, invariants
- Code analyzer: 12 operation-to-assumption mappings
- Evidence/bead integrations
- 6 CLI commands

### Orchestration Layer (Phase 4)
- Pool schemas, routing, execution loop (~6,400 LOC)
- Debate protocol with 13 phase handlers
- Claude skills (/vkg:audit, /vkg:investigate, etc.)
- Agent definitions (attacker/defender/verifier)

### Tool Integration (Phase 5.1)
- 7 adapters: Slither, Aderyn, Mythril, Echidna, Foundry, Semgrep, Halmos
- 205 detector mappings
- SARIF normalization + deduplication
- Agent skills for tool coordination

### Multi-Agent SDK (Phase 5.2)
- AgentRuntime ABC with Anthropic/OpenAI implementations
- Hook system with prioritized queues
- Supervisor/integrator agents
- Test Builder with Foundry integration

### OpenCode SDK Refactor (Phase 5.3)
- Runtimes: OpenCode, Claude Code CLI, Codex CLI
- Model ranking system with EMA-based feedback
- Task router with policy-based model selection
- 75%+ cost savings vs API billing

### VulnDocs Framework (Phase 5.4)
- Framework at `vulndocs/` with templates, instructions
- Schema validation (Pydantic), CLI commands
- 7 VRS skills for vulnerability research
- 147 integration tests

### Test Performance (Phase 8)
- 3.79x speedup (73.6% reduction) with pytest-xdist
- Recommendation: `-n auto --dist loadfile` for CI

---

## Known Limitations

### Builder Bugs
| Bug | Impact | Priority |
|-----|--------|----------|
| High-level call target tracking | Misses some delegatecall patterns | HIGH |
| High-level call data analysis | Call data not fully tracked | HIGH |
| Strict equality detection | Only checks require() | MEDIUM |
| Library call handling | Address.functionCall() fails | MEDIUM |

### Pending Features
| Feature | Status | Phase |
|---------|--------|-------|
| Agent execution context | Not implemented | 5.5 |
| Skill separation (dev vs product) | Not implemented | 5.6 |
| PyPI release | Pending | 6 |
| GA validation | Pending | 7 |

---

## Architecture

```
Solidity Source
    │
    ▼
Slither Parser
    │
    ▼
VKG Builder (src/true_vkg/kg/builder/)
    │
    ├── 50+ security properties per function
    ├── 20 semantic operations (name-agnostic)
    ├── Behavioral signatures (operation ordering)
    ├── Proxy resolution (EIP-1967, UUPS, Diamond, Beacon)
    └── Deterministic IDs + completeness reports
    │
    ▼
VulnDocs Knowledge System (vulndocs/)
    │
    ├── Unified vulnerability documentation
    ├── Pattern definitions with test coverage
    ├── Graph-first detection strategies
    └── Semantic operation mappings
    │
    ▼
Pattern Engine (patterns/*.yaml)
    │
    ├── Tier A: Strict, graph-only, high confidence
    ├── Tier B: Exploratory, LLM-verified
    └── Tier C: Label-dependent patterns (21 patterns)
    │
    ▼
Protocol Context Pack (src/true_vkg/context/)
    │
    ├── Roles, assumptions, invariants
    ├── Off-chain inputs (oracles, relayers)
    └── Doc-code conflict detection
    │
    ▼
Tool Integration (src/true_vkg/tools/)
    │
    ├── 7 adapters: Slither, Aderyn, Mythril, Echidna, Foundry, Semgrep, Halmos
    ├── SARIF normalization + deduplication
    └── Smart pattern skip logic
    │
    ▼
Beads + Pools (src/true_vkg/beads/, src/true_vkg/orchestration/)
    │
    ▼
Multi-Agent Verification
    │
    ├── Attacker: exploit construction (claude-opus-4)
    ├── Defender: guard/mitigation search (claude-sonnet-4)
    ├── Verifier: evidence cross-check (claude-opus-4)
    └── Debate protocol: claim/counterclaim/arbitration
    │
    ▼
Verdicts + Evidence Packets
```

---

## Quick Reference

### Commands
```bash
# Build knowledge graph
uv run alphaswarm build-kg path/to/contracts/
uv run alphaswarm build-kg path/to/contracts/ --with-labels  # Include semantic labels

# Query graph
uv run alphaswarm query "pattern:weak-access-control"

# VulnDocs
uv run alphaswarm vulndocs validate vulndocs/
uv run alphaswarm vulndocs scaffold reentrancy-classic --name "Classic Reentrancy" --severity critical

# Tools
uv run alphaswarm tools status
uv run alphaswarm tools run path/to/contracts/ --tools slither,aderyn

# Run tests
uv run pytest tests/ -n auto --dist loadfile  # Parallel (3.79x faster)
```

### Documentation
| Document | Purpose |
|----------|---------|
| `.planning/ROADMAP.md` | Full milestone roadmap |
| `.planning/STATE.md` | Current execution state |
| `docs/PHILOSOPHY.md` | Vision and requirements |
| `docs/guides/patterns-basics.md` | Pattern authoring |
| `docs/guides/vulndocs-basics.md` | VulnDocs framework guide |

---

## Key Decisions

### Architecture
- **Pool terminology**: "convoy" renamed to "pool" (crypto-native)
- **Debate protocol**: Always human-flagged, evidence anchoring required (iMAD-inspired)
- **Batch spawning**: Attackers → Defenders → Verifiers
- **Model routing**: Opus for attacker/verifier (critical), Sonnet for defender (fast)

### Multi-Agent & Cost
- **Primary SDK**: OpenCode for multi-model access (400+ models)
- **Free models**: MiniMax M2, Big Pickle for verification/summarization
- **Cost target**: 75-95% savings vs API billing (~$31-116/mo vs $500+)
- **Loop prevention**: 10 iterations, 3 repeated outputs, 100K token ceiling

### VulnDocs Framework
- **Location**: `vulndocs/` at project root (flattened structure)
- **Progressive validation**: MINIMAL → STANDARD → COMPLETE → EXCELLENT
- **Skills namespace**: `vrs:` for vulnerability research, `vkg:` for core operations
- **Graph-first**: Agents MUST use BSKG queries, NOT manual code reading

### Testing
- **Primary**: pytest-xdist with `-n auto --dist loadfile` (3.79x speedup)
- **Secondary**: pytest-testmon for local development
- **Quality gates**: draft <0.70, ready ≥0.70, excellent ≥0.90 precision

---

*Status reflects milestone 5.0 implementation. Updated 2026-01-22.*
