# AlphaSwarm.sol Documentation Index

**Version**: 2.0 (December 2025)
**Last Updated**: 2025-12-30

Welcome to the AlphaSwarm.sol documentation. This index provides structured access to all technical documentation for the Vulnerability Knowledge Graph system.

---

## Quick Navigation

### 🏗️ Architecture Documentation
Understand the system design, principles, and implementation decisions.

| Document | Description | Audience |
|----------|-------------|----------|
| [Architecture Overview](architecture/overview.md) | System design, philosophy, and core principles | All developers |
| [Knowledge Graph Schema](architecture/knowledge-graph.md) | Node types, edge types, property model | Pattern authors, researchers |
| [Property Reference](architecture/properties.md) | Complete reference of all 50+ properties | Pattern authors, advanced users |
| [Performance & Optimization](architecture/performance.md) | Build times, query performance, memory usage | DevOps, performance engineers |

---

### ⚡ Feature Documentation
Deep dive into each security detection capability.

| Feature | Document | Properties | Patterns | Status |
|---------|----------|------------|----------|--------|
| **Access Control** | [access-control.md](features/access-control.md) | 38 properties | 5+ patterns | ✅ Stable |
| **Reentrancy** | [reentrancy.md](features/reentrancy.md) | 3 properties | 4+ patterns | ✅ Stable |
| **DoS Detection** | [dos.md](features/dos.md) | 9 properties | 9 patterns | ✅ Enhanced Dec 2025 |
| **Crypto/Signatures** | [crypto.md](features/crypto.md) | 12 properties | 11+ patterns | ✅ Stable |
| **MEV Protection** | [mev.md](features/mev.md) | 7 properties | 5+ patterns | ✅ Stable |
| **Oracle Security** | [oracle.md](features/oracle.md) | 8 properties | 6+ patterns | ✅ Stable |
| **Token Handling** | [tokens.md](features/tokens.md) | 8 properties | 3+ patterns | ✅ Stable |
| **Invariants** | [invariants.md](features/invariants.md) | 4 properties | 1 pattern | ✅ New Dec 2025 |
| **Proxy/Upgrade** | [proxy.md](features/proxy.md) | 3 properties | 3+ patterns | ✅ Stable |

---

### 📚 User Guides
Learn how to use AlphaSwarm.sol effectively.

| Guide | Description | Level |
|-------|-------------|-------|
| [Query System](guides/query-system.md) | NL queries, VQL, JSON queries, flow analysis | Beginner-Intermediate |
| [Pattern Pack Authoring](guides/pattern-packs.md) | Write custom patterns in YAML | Intermediate-Advanced |
| [Testing Guide](guides/testing.md) | Write tests, create fixtures, run test suite | Advanced |

---

### 🚀 Enhancement Documentation
Detailed documentation of major system enhancements.

| Enhancement | Document | Date | Impact |
|------------|----------|------|--------|
| **DoS Detection V2** | [2025-12-dos.md](enhancements/2025-12-dos.md) | 2025-12-29 | +5 properties, +6 patterns, 0 breaking changes |

---

### 🧠 Semantic BSKG (Next Generation)
Documentation for the semantic-aware detection system.

| Document | Description | Status |
|----------|-------------|--------|
| [**MEGA Implementation Plan**](mega-implementation-plan.md) | 22-phase comprehensive roadmap with all enhancements | **🚀 MASTER PLAN** |
| [Pattern Robustness Ideas v1](pattern-robustness-ideas.md) | Initial brainstorm on name-agnostic detection | Archived |
| [Semantic Detection v2](semantic-agnostic-detection-v2.md) | Multi-layer architecture proposal | Superseded |
| [Critical Analysis](semantic-detection-critical-analysis.md) | Honest critique and trade-off analysis | Review |
| [Implementation Plan v3](semantic-vkg-implementation-plan.md) | Refined plan with novel ideas | Merged into Mega |
| [Detailed Roadmap](implementation-roadmap-detailed.md) | 12-phase implementation with tests | Merged into Mega |

#### Key Concepts

**Six-Layer Architecture:**
- **Layer 1**: Enhanced Graph Structure (Hierarchical nodes, Intelligent edges)
- **Layer 2**: Tier A Deterministic (Operations, Signatures, Paths, Constraints)
- **Layer 3**: Subgraph Extraction (Query-aware slicing, Semantic scaffolding)
- **Layer 4**: Multi-Agent Verification (Explorer, Pattern, Constraint, Risk agents)
- **Layer 5**: Tier B Semantic/LLM (Context, Intent, Risk tags)
- **Layer 6**: Cross-Contract Intelligence (Similarity, Exploit DB, Intent propagation)

**Hierarchical Node Types:**
| Type | Subtypes |
|------|----------|
| Function | Guardian, Checkpoint, EscapeHatch, EntryPoint |
| StateVariable | StateAnchor, CriticalState, ConfigState |
| ExecutionPath | Multi-step attack sequences |
| StateTransition | Temporal state changes |
| ExternalDependency | Cross-contract links |

**20 Semantic Operations:**
| Category | Operations |
|----------|------------|
| Value Movement | TRANSFERS_VALUE_OUT, RECEIVES_VALUE_IN, READS_USER_BALANCE, WRITES_USER_BALANCE |
| Access Control | CHECKS_PERMISSION, MODIFIES_OWNER, MODIFIES_ROLES |
| External | CALLS_EXTERNAL, CALLS_UNTRUSTED, READS_EXTERNAL_VALUE |
| State | MODIFIES_CRITICAL_STATE, INITIALIZES_STATE, READS_ORACLE |
| Control Flow | LOOPS_OVER_ARRAY, USES_TIMESTAMP, USES_BLOCK_DATA |
| Arithmetic | PERFORMS_DIVISION, PERFORMS_MULTIPLICATION |
| Validation | VALIDATES_INPUT, EMITS_EVENT |

**4-Agent Verification System:**
1. **Explorer Agent**: BFS path traversal, critical path identification
2. **Pattern Agent**: Vulnerability motif matching
3. **Constraint Agent**: Z3/SMT satisfiability checking
4. **Risk Agent**: Exploitability assessment, attack scenario generation

**Novel Ideas (10+):**
1. Adversarial Scenario Generation
2. Economic Model Understanding
3. Intent Deviation Detection
4. Cross-Contract Intent Propagation
5. Temporal Vulnerability Windows
6. Protocol Semantic Layer
7. Compositional Vulnerability Chains
8. Behavioral Regression Detection
9. Fuzzy Intent Matching
10. Self-Improving Pattern Library
11. Attack Path Synthesis
12. Intelligent Edge Risk Scoring

---

## Understanding AlphaSwarm.sol's Power

AlphaSwarm.sol is a **deterministic security reasoning system** that combines:

### 1. Comprehensive Property Derivation (50+ properties/function)
Every function is analyzed for 50+ security-relevant properties across all vulnerability classes. This enables composable pattern matching without hardcoded heuristics.

**Example**: Detecting reentrancy requires combining:
- `visibility in [public, external]` (accessibility)
- `state_write_after_external_call == true` (CEI violation)
- `has_reentrancy_guard == false` (no protection)

### 2. Multi-Layer Query System
- **Natural Language**: "public functions that write state"
- **VQL**: "find functions where visibility in [public, external] and writes_state"
- **JSON**: Full boolean logic with edge/path constraints
- **Patterns**: Named, versioned, regression-tested queries

### 3. Deterministic, Reproducible Results
Given the same Solidity code, AlphaSwarm.sol produces **identical results**. This enables:
- CI/CD integration
- Regression testing
- Reproducible security audits

### 4. Evidence-First Design
Every finding includes:
- Exact file path and line numbers
- Property values that triggered the match
- Graph structure explaining the vulnerability

### 5. LLM-Optimized Output
- **Compact mode**: 10x smaller results for LLM context
- **Explain mode**: Include reasoning for pattern matches
- **No-evidence mode**: Drop file paths for quick scans

---

## Getting Started

### For Users
1. Read [Architecture Overview](architecture/overview.md) to understand the system
2. Review [Query System Guide](guides/query-system.md) to learn how to query
3. Explore feature docs to understand what can be detected

### For Pattern Authors
1. Read [Property Reference](architecture/properties.md) to understand all properties
2. Study [Pattern Pack Guide](guides/pattern-packs.md) to learn YAML syntax
3. Review existing patterns in `patterns/core/` for examples

### For Developers
1. Start with [Architecture Overview](architecture/overview.md)
2. Read [Knowledge Graph Schema](architecture/knowledge-graph.md)
3. Review [Testing Guide](guides/testing.md) for contribution workflow

### For Security Researchers
1. Review feature docs for your area of interest (DoS, Reentrancy, etc.)
2. Read [Property Reference](architecture/properties.md) to understand detection capabilities
3. Explore [Enhancement Documentation](enhancements/) for latest improvements

---

## Feature Highlights

### 🔒 Access Control Detection
- Detects weak access control on privileged functions
- Identifies tx.origin authentication (phishing vector)
- Tracks arbitrary delegatecall vulnerabilities
- **Coverage**: Parity Wallet, DAO-style attacks

### 🔄 Reentrancy Detection
- CEI (Checks-Effects-Interactions) violation detection
- Cross-function reentrancy tracking
- Read-only reentrancy (flash loan attacks)
- **Coverage**: DAO hack, Lendf.me exploit

### ⏸️ DoS Detection (Enhanced Dec 2025)
- Unbounded loop detection with require() bound analysis
- Transfer/send gas limit detection (2300 gas DoS)
- Gridlock attack detection (strict equality checks)
- External calls in loops (block gas limit DoS)
- **Coverage**: Edgeware Lockdrop, King of Ether Throne

### 🔐 Cryptography/Signature Security
- Signature malleability detection (s-value, v-value)
- Replay protection validation (nonce, chain ID, deadline)
- EIP-712 compliance checking
- Zero address validation after ecrecover
- **Coverage**: Permit front-running, cross-chain replays

### 💰 MEV Protection
- Slippage parameter detection
- Deadline parameter validation
- TWAP window configuration
- **Coverage**: Sandwich attacks, generalized front-running

### 🔮 Oracle Security
- Staleness check validation (Chainlink)
- L2 sequencer uptime checks
- TWAP configuration validation
- Round ID validation
- **Coverage**: Venus Protocol manipulation

### 🪙 Token Handling
- ERC20 return value checking
- Safe ERC20 library usage
- Transfer/transferFrom validation
- **Coverage**: USDT-style tokens without return values

### 📋 Invariant System (New Dec 2025)
- Extract formal properties from NatSpec comments
- Track invariant violations in functions
- Detect functions that touch invariants without validation
- **Coverage**: Custom logic bugs (total supply, balance sums)

### 🔄 Proxy/Upgradeability
- Storage gap detection
- Upgrade function access control
- Initializer protection
- **Coverage**: Storage collision attacks

---

## Statistics

| Metric | Count |
|--------|-------|
| **Node Types** | 9 (Contract, Function, StateVariable, Event, Input, Loop, Invariant, ExternalCallSite, SignatureUse) |
| **Edge Types** | 13 (CONTAINS_*, INPUT_TAINTS_STATE, FUNCTION_TOUCHES_INVARIANT, etc.) |
| **Function Properties** | 50+ |
| **Vulnerability Classes** | 9 (Authority, Reentrancy, DoS, Crypto, MEV, Oracle, Token, Invariant, Proxy) |
| **Patterns** | 47+ (9 DoS, 11+ Crypto, 5+ Authority, etc.) |
| **Test Contracts** | 80+ |
| **Test Coverage** | 120+ tests |

---

## System Requirements

- **Python**: 3.11+
- **Slither**: Installed via `uv sync`
- **Solidity**: Any version supported by Slither
- **Memory**: <100MB for typical projects
- **Disk**: ~1MB per 100 functions (graph storage)

---

## Documentation Maintenance

**Update Frequency**:
- Architecture docs: On major design changes
- Feature docs: When properties/patterns added
- Guides: When user-facing features change
- Enhancements: For each major version

**Maintainers**: See [CLAUDE.md](../CLAUDE.md) for contribution guidelines.

---

## External Resources

- **Repository**: [AlphaSwarm.sol GitHub](https://github.com/yourusername/alphaswarm)
- **Issue Tracker**: [GitHub Issues](https://github.com/yourusername/alphaswarm/issues)
- **Security Standards**:
  - [CWE Database](https://cwe.mitre.org/)
  - [SWC Registry](https://swcregistry.io/)
  - [OWASP Smart Contract Top 10](https://owasp.org/www-project-smart-contract-top-10/)

---

## Document Version History

- **v2.0** (2025-12-30): MEGA Implementation Plan
  - Created comprehensive 22-phase implementation roadmap
  - Added 6-layer architecture (Graph, Tier A, Subgraph, Agents, Tier B, Cross-Contract)
  - Integrated Edge Intelligence with risk scoring
  - Added Hierarchical Node Types (Guardian, Checkpoint, StateAnchor)
  - Added Execution Path Analysis for multi-step attacks
  - Added Multi-Agent Verification (4 agents, consensus)
  - Added Cross-Contract Intelligence with exploit database
  - Added Constraint-Based Verification (Z3/SMT)
  - Added Supply-Chain/Dependency Layer
  - Added Temporal Execution Layer
  - Added Semantic Scaffolding for LLM efficiency
  - Added Attack Path Synthesis
  - 12 novel detection ideas

- **v1.1** (2025-12-30): Semantic BSKG Documentation
  - Added semantic detection architecture design
  - Created 12-phase implementation roadmap
  - Defined 20 semantic operations
  - Added 10 novel detection ideas
  - Created critical analysis with trade-offs

- **v1.0** (2025-12-29): Initial structured documentation
  - Migrated from root-level markdown files
  - Created feature-specific documentation
  - Added comprehensive DoS enhancement docs
  - Added invariant system documentation

---

*For questions or contributions, see [CLAUDE.md](../CLAUDE.md) and [AGENTS.md](../AGENTS.md)*
