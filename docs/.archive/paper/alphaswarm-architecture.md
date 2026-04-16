# AlphaSwarm.sol: Behavioral Vulnerability Detection Through Semantic Reasoning

**Version:** 0.5.0
**Authors:** AlphaSwarm Team
**Date:** January 2026
**Status:** Technical Report (Pre-evaluation)

---

## Abstract

Smart contract vulnerabilities continue to cause significant financial losses in decentralized systems. Traditional static analysis tools rely on syntactic pattern matching and function name heuristics, failing to detect vulnerabilities when developers rename functions or implement custom withdrawal patterns. This paper presents AlphaSwarm.sol, a behavioral vulnerability detection framework that captures what code *does* rather than what it is *named*. The framework introduces the Behavioral Security Knowledge Graph (BSKG), which extracts 50+ security properties per function and derives behavioral signatures from ordered semantic operations. AlphaSwarm.sol employs a three-tier pattern system spanning deterministic graph queries to LLM-verified exploratory patterns, combined with an adversarial verification protocol featuring specialized attacker, defender, and verifier agents. The system includes a protocol context pack for economic reasoning about logic bugs that require understanding of roles, trust assumptions, and off-chain inputs. This technical report documents the architecture and design decisions; empirical evaluation is deferred to future work.

---

## 1. Introduction

### 1.1 Problem Statement

Smart contract vulnerabilities have resulted in billions of dollars in losses across decentralized finance protocols. The 2024-2025 period alone witnessed numerous high-profile exploits targeting reentrancy, access control, and oracle manipulation vulnerabilities. Traditional static analysis tools such as Slither, Aderyn, and Semgrep have improved detection coverage for common vulnerability classes, yet fundamental limitations persist.

These tools predominantly rely on syntactic patterns and function name heuristics. A rule detecting `withdraw()` functions with external calls before state updates fails when the same vulnerable logic appears in `processPayment()` or `executeTransfer()`. This brittleness stems from a fundamental architectural choice: matching code syntax rather than code behavior.

The core insight driving AlphaSwarm.sol is simple: **Names lie. Behavior does not.**

A function named `withdraw()` may be a safe utility function, while `processPayment()` may contain critical reentrancy vulnerabilities. The function name carries no security semantics. What matters is the *behavior*: does the function read a user balance, make an external call, and then write the balance? This ordering pattern indicates reentrancy risk regardless of naming.

### 1.2 Solution Overview

AlphaSwarm.sol addresses these limitations through a behavior-first approach. The system constructs a Behavioral Security Knowledge Graph (BSKG) that captures what code does through semantic operations and behavioral signatures, enabling detection independent of implementation variations.

The framework introduces:

1. **Semantic Operations**: A vocabulary of 20 core operations (e.g., `TRANSFERS_VALUE_OUT`, `CHECKS_PERMISSION`, `READS_ORACLE`) that describe behavior independent of function names
2. **Behavioral Signatures**: Ordered sequences of operations (e.g., `R:bal -> X:out -> W:bal`) that encode execution flow patterns
3. **Three-Tier Patterns**: Detection rules spanning fully automated (Tier A), LLM-verified (Tier B), and label-dependent (Tier C) categories
4. **Adversarial Verification Protocol**: Multi-agent debate with attacker, defender, and verifier roles ensuring evidence-anchored findings
5. **Protocol Context Pack**: Economic context capturing roles, trust assumptions, and off-chain inputs for logic bug detection

### 1.3 Contributions

This paper makes the following contributions:

1. **Behavioral Security Knowledge Graph (BSKG)**: A knowledge graph architecture extracting 50+ security properties per function with evidence linking to exact code locations

2. **Semantic Operations Vocabulary**: A stable vocabulary of 20 core operations that capture security-relevant behavior independent of implementation syntax

3. **Behavioral Signatures**: A notation system encoding ordered semantic operations that identifies vulnerability patterns regardless of function naming

4. **Three-Tier Pattern System**: A detection hierarchy from deterministic graph queries (Tier A) through LLM-verified exploration (Tier B) to semantic label-dependent patterns (Tier C)

5. **Adversarial Verification Protocol**: A multi-agent verification approach inspired by debate protocols, featuring attacker, defender, and verifier agents with mandatory evidence anchoring

6. **Protocol Context Pack**: A structured representation of economic context enabling detection of logic bugs requiring understanding of protocol economics and trust assumptions

---

## 2. Related Work

Recent advances in LLM-assisted smart contract analysis have produced several notable frameworks. This section positions AlphaSwarm.sol relative to the state of the art.

### 2.1 Knowledge Graph Approaches

**CKG-LLM** (Li et al., 2025) constructs Contract Knowledge Graphs from AST and control flow information, using LLM-based detection for access control vulnerabilities. The approach demonstrates the value of structured knowledge representation but remains limited to structural patterns derived from syntax trees. CKG-LLM successfully detects access control issues but cannot identify behavioral patterns that span multiple functions or require understanding of operation ordering.

AlphaSwarm.sol differs fundamentally in graph construction philosophy. Rather than encoding syntactic structure, BSKG captures behavioral semantics through operations that describe what code does. This enables detection of vulnerabilities that manifest through behavioral patterns rather than structural anomalies.

### 2.2 LLM-Enhanced Detection

**SmartGuard** (Ding et al., 2025) introduces an LLM-enhanced framework combining traditional analysis with large language model reasoning. The approach improves detection of complex vulnerabilities beyond static pattern matching. However, SmartGuard employs single-pass LLM analysis without verification mechanisms, creating risk of hallucinated findings and inconsistent results across runs.

AlphaSwarm.sol addresses this limitation through its adversarial verification protocol, requiring multi-agent consensus and evidence anchoring before findings achieve high confidence status.

### 2.3 Multi-Agent Systems

**LLM-SmartAudit** (Wei et al., 2025) leverages multi-agent systems for vulnerability detection, demonstrating improved coverage through specialized agent roles. The framework does not incorporate structured debate protocols, and agent claims lack mandatory evidence linking to code locations.

The adversarial verification protocol in AlphaSwarm.sol draws inspiration from **iMAD** (Fan et al., 2025), which demonstrates that structured multi-agent debate improves inference accuracy. AlphaSwarm.sol adapts this approach for security analysis with explicit claim/counterclaim/arbitration phases and evidence anchoring requirements.

### 2.4 Symbolic and Formal Approaches

Symbolic execution tools such as Mythril and formal verification platforms like Certora provide strong guarantees for specific vulnerability classes. However, these approaches struggle with logic bugs requiring economic context understanding. **SymGPT** focuses on ERC specification violations but does not address protocol-specific business logic vulnerabilities.

**FLAMES** synthesizes invariants for vulnerability detection but remains limited to properties expressible as invariants, missing vulnerabilities that require understanding of intended protocol behavior and economic incentives.

### 2.5 Industry Benchmarks

The **Anthropic SCONE-bench** (December 2025) evaluation demonstrated that AI agents can identify exploitable vulnerabilities worth $4.6M, establishing the viability of LLM-based security analysis. This benchmark motivates continued development of LLM-assisted detection frameworks while highlighting the importance of structured verification to avoid false positives.

### 2.6 Summary of Differentiators

| Approach | Limitation | AlphaSwarm.sol Solution |
|----------|------------|-------------------------|
| CKG-LLM (Li et al., 2025) | Structural KG (AST/CFG), access control only | Behavioral signatures via semantic operations |
| SmartGuard (Ding et al., 2025) | Single-pass LLM, hallucination risk | Adversarial verification protocol |
| LLM-SmartAudit (Wei et al., 2025) | Multi-agent but no structured debate | iMAD-inspired claim/rebuttal/arbitration |
| SymGPT | ERC rules only, not logic bugs | Protocol context for economic reasoning |
| FLAMES | Limited to invariants | Three-tier pattern system |

AlphaSwarm.sol is the **first framework** to use ordered semantic operations for vulnerability detection, enabling behavior-first analysis independent of naming conventions. It is the **only framework** that captures economic context through protocol context packs, enabling detection of logic bugs requiring understanding of roles, trust assumptions, and off-chain dependencies.

---

## 3. Architecture

### 3.1 System Overview

AlphaSwarm.sol processes Solidity source code through a pipeline that constructs behavioral representations, applies multi-tier pattern detection, and verifies findings through adversarial debate. The system flow proceeds as follows:

```
Solidity Source -> BSKG Builder -> Pattern Engine -> Beads -> Agent Pool -> Verdicts
```

**BSKG Builder**: Parses source code via Slither, extracts security properties, derives semantic operations, and constructs behavioral signatures with evidence linking.

**Pattern Engine**: Applies three-tier patterns against the graph, generating candidate findings with associated evidence.

**Beads**: Packages findings as self-contained investigation units with evidence, questions, and verification guidance.

**Agent Pool**: Routes beads to specialized agents (attacker, defender, verifier) for adversarial verification.

**Verdicts**: Produces classified findings with confidence buckets (confirmed, likely, uncertain, rejected) and evidence-linked rationale.

### 3.2 Behavioral Security Knowledge Graph (BSKG)

The BSKG differs from traditional contract knowledge graphs in its focus on behavioral rather than structural representation. While approaches like CKG-LLM encode AST nodes and control flow edges, BSKG captures what functions *do* through semantic operations and derived properties.

#### 3.2.1 Property Extraction

The BSKG builder extracts 50+ security properties per function through Slither-based parsing with semantic enrichment. Properties fall into several categories:

**Access Control Properties**:
- `has_access_gate`: Function includes permission checks
- `uses_onlyowner`: Function protected by onlyOwner modifier
- `uses_role_modifier`: Function protected by role-based modifier
- `writes_privileged_state`: Function modifies owner, admin, or fee state

**Value Flow Properties**:
- `sends_value`: Function transfers ETH or tokens
- `receives_value`: Function is payable or accepts tokens
- `reads_balances`: Function accesses balance mappings
- `writes_balances`: Function modifies balance mappings

**Reentrancy Properties**:
- `has_reentrancy_guard`: Function protected by reentrancy mutex
- `external_calls_before_state`: External calls precede state modifications
- `external_calls_after_state`: External calls follow state modifications

**External Interaction Properties**:
- `calls_external`: Function makes external calls
- `calls_untrusted`: Function calls user-controlled addresses
- `reads_oracle`: Function queries price feeds or oracles

#### 3.2.2 Evidence Linking

Every property maps to exact code locations through evidence linking. When the system identifies `writes_privileged_state: true`, the evidence includes:

- Source file and line numbers
- Contract and function identifiers
- AST node references
- Variable and expression details

This evidence linking enables auditors to verify detected patterns against source code and provides LLM agents with grounded context for reasoning.

#### 3.2.3 Modular Architecture

The BSKG builder employs a modular architecture with 10 specialized modules:

1. **Core**: Graph initialization and coordination
2. **Contracts**: Contract-level node creation
3. **Functions**: Function property extraction
4. **Variables**: State variable analysis
5. **Calls**: External call tracking
6. **Access**: Permission and modifier analysis
7. **Proxies**: Upgradeability pattern resolution
8. **Events**: Event emission tracking
9. **Operations**: Semantic operation derivation
10. **Signatures**: Behavioral signature construction

This modularity enables independent testing, focused maintenance, and clear separation of concerns.

### 3.3 Semantic Operations

Semantic operations describe security-relevant behavior independent of function naming. The vocabulary consists of 20 core operations organized by category:

**Value Operations**:
- `TRANSFERS_VALUE_OUT`: ETH or token transfers out of contract
- `RECEIVES_VALUE_IN`: Payable function or token receipt
- `READS_USER_BALANCE`: Reads balance mappings or balanceOf
- `WRITES_USER_BALANCE`: Writes to balance mappings

**Access Control Operations**:
- `CHECKS_PERMISSION`: require/assert or modifier-based auth
- `MODIFIES_OWNER`: Owner changes
- `MODIFIES_ROLES`: Role assignments or access control updates

**External Interaction Operations**:
- `CALLS_EXTERNAL`: Any external call
- `CALLS_UNTRUSTED`: External call to user-controlled address
- `READS_EXTERNAL_VALUE`: Reads external contract values

**State Operations**:
- `MODIFIES_CRITICAL_STATE`: Writes to privileged state
- `INITIALIZES_STATE`: Initializer or constructor-like setup
- `READS_ORACLE`: Oracle or price feed reads

**Control Flow Operations**:
- `LOOPS_OVER_ARRAY`: Unbounded or user-driven loops
- `USES_TIMESTAMP`: block.timestamp access
- `USES_BLOCK_DATA`: block.number, blockhash, prevrandao

**Arithmetic Operations**:
- `PERFORMS_DIVISION`: Division or precision-sensitive math
- `PERFORMS_MULTIPLICATION`: Multiplication or overflow-sensitive math

**Other Operations**:
- `VALIDATES_INPUT`: Input validation checks
- `EMITS_EVENT`: Event emission

#### 3.3.1 Name Independence

The key advantage of semantic operations is detection independent of naming. Consider:

```solidity
function withdraw(uint amount) external {
    require(balances[msg.sender] >= amount);
    (bool ok,) = msg.sender.call{value: amount}("");
    balances[msg.sender] -= amount;
}

function processPayment(uint value) external {
    require(userFunds[msg.sender] >= value);
    (bool success,) = msg.sender.call{value: value}("");
    userFunds[msg.sender] -= value;
}
```

Both functions exhibit identical semantic operations: `READS_USER_BALANCE`, `TRANSFERS_VALUE_OUT`, `WRITES_USER_BALANCE`. Name-based detection would require rules for both `withdraw` and `processPayment`, while operation-based detection identifies the pattern regardless of naming.

#### 3.3.2 Vocabulary Stability

The 20 core operations constitute a stable contract for pattern definitions. Extensions are permitted but must be additive and versioned. This stability ensures patterns and queries remain functional as the system evolves.

### 3.4 Behavioral Signatures

Behavioral signatures encode ordered sequences of semantic operations, representing what a function does and in what order. This ordering captures temporal relationships critical for vulnerability detection.

#### 3.4.1 Signature Syntax

Signatures use operation codes connected by arrows indicating ordering:

```
R:bal -> X:out -> W:bal   # Read balance, external call, write balance
C:auth -> M:crit          # Permission check, modify critical state
R:orc -> A:div -> X:out   # Read oracle, division, value out
```

The operation codes are:

```
R:bal   read user balance
W:bal   write user balance
X:out   transfer value out
X:in    receive value in
X:call  external call
X:unk   call untrusted address
C:auth  permission check
M:own   modify owner
M:role  modify role
M:crit  modify critical state
R:orc   read oracle
R:ext   read external value
L:arr   loop over array
U:time  use timestamp
U:blk   use block data
A:div   division
A:mul   multiplication
V:in    validate input
E:evt   emit event
I:init  initializer pattern
```

#### 3.4.2 Ordering and Vulnerability Patterns

The ordering encoded in signatures directly maps to vulnerability patterns:

**Reentrancy** (vulnerable):
```
R:bal -> X:out -> W:bal
```
Read balance, then external call, then write balance. The external call occurs before state update, enabling reentrant calls to observe stale state.

**Checks-Effects-Interactions** (safe):
```
R:bal -> W:bal -> X:out
```
Read balance, write balance, then external call. State update precedes external call, preventing reentrancy.

**Unprotected Critical State** (vulnerable):
```
M:crit
```
Modify critical state without permission check. Missing `C:auth` operation indicates access control vulnerability.

**Protected Critical State** (safe):
```
C:auth -> M:crit
```
Permission check precedes critical state modification.

#### 3.4.3 Multiple Paths

Functions with conditional logic may have multiple execution paths, each producing different signatures. The BSKG preserves ordering pairs and dominant sequences, enabling detection of vulnerabilities that manifest only on specific paths.

### 3.5 Three-Tier Pattern System

AlphaSwarm.sol employs a three-tier pattern system spanning the automation spectrum from fully deterministic to semantic reasoning-dependent.

#### 3.5.1 Tier A: Deterministic Patterns

Tier A patterns operate purely on graph structure without LLM reasoning. They provide:

- **High confidence**: Deterministic matching produces consistent results
- **Repeatability**: Same graph produces same findings
- **Low latency**: No LLM calls required

Tier A patterns match against properties, operations, and signature ordering:

```yaml
id: reentrancy-classic
name: Classic Reentrancy
severity: critical
lens: [Reentrancy]
tier: A

match:
  tier_a:
    all:
      - property: visibility
        op: in
        value: [public, external]
      - has_all_operations:
          - TRANSFERS_VALUE_OUT
          - WRITES_USER_BALANCE
      - sequence_order:
          before: TRANSFERS_VALUE_OUT
          after: WRITES_USER_BALANCE
    none:
      - property: has_reentrancy_guard
        value: true
```

This pattern detects functions where value transfers occur before balance writes, without reentrancy protection, regardless of function naming.

#### 3.5.2 Tier B: Exploratory Patterns

Tier B patterns target complex vulnerabilities requiring contextual reasoning. They produce candidates with evidence and questions rather than final claims:

```yaml
id: oracle-manipulation
name: Oracle Manipulation Vulnerability
severity: high
lens: [Oracle]
tier: B

match:
  tier_b:
    all:
      - has_operation: READS_ORACLE
      - has_operation: TRANSFERS_VALUE_OUT
    context_questions:
      - Is the oracle trusted (Chainlink, TWAP)?
      - Is there sufficient staleness checking?
      - Can the oracle be manipulated within a single block?
    verification_required: true
```

Tier B patterns achieve high recall by design, accepting false positives that LLM verification subsequently filters. This approach ensures complex vulnerabilities are not missed due to overly restrictive pattern definitions.

#### 3.5.3 Tier C: Label-Dependent Patterns

Tier C patterns require semantic labels from an LLM labeling pass. These patterns detect vulnerabilities requiring understanding of function intent and data flow semantics:

```yaml
id: state-machine-invalid-transition
name: Invalid State Machine Transition
severity: medium
lens: [Logic]
tier: C

match:
  tier_c:
    requires_labels: true
    conditions:
      - has_label: state_mutation.state_variable_update
      - missing_label: control_flow.state_transition_check
    context_questions:
      - What are the valid state transitions?
      - Is this transition allowed from the current state?
```

The labeling pass annotates functions with semantic labels such as `state_mutation.balance_update` or `access_control.reentrancy_guard`. Tier C patterns match against these labels, enabling detection of policy mismatches, invariant violations, and state machine errors.

#### 3.5.4 Pattern Tier Summary

| Tier | Input | Verification | Confidence |
|------|-------|--------------|------------|
| A | Graph properties and signatures | None required | HIGH |
| B | Graph + context questions | LLM verification | MEDIUM |
| C | Graph + semantic labels | Labels + LLM | MEDIUM |

### 3.6 Multi-Agent Adversarial Verification Protocol

AlphaSwarm.sol verifies findings through an adversarial protocol featuring specialized agents in debate. This approach, inspired by iMAD (Fan et al., 2025), ensures findings are challenged and evidence is cross-checked before achieving high confidence status.

#### 3.6.1 Agent Roles

**Attacker Agent (Opus)**:
- Constructs exploit paths from vulnerable function to economic impact
- Identifies preconditions required for exploitation
- Proposes attack narratives with step-by-step execution
- Estimates potential loss and impact severity

**Defender Agent (Sonnet)**:
- Searches for guards, invariants, and mitigating logic
- Identifies access control that may prevent exploitation
- Finds compensating controls and protocol safeguards
- Proposes scenarios where vulnerability is not exploitable

**Verifier Agent (Opus)**:
- Cross-checks evidence from attacker and defender
- Validates code references and claim accuracy
- Runs tests when available to confirm or refute claims
- Arbitrates conflicts and issues reasoned verdicts

#### 3.6.2 Debate Protocol

The verification protocol proceeds through structured phases:

1. **Claim Phase**: Attacker agent produces exploit narrative with evidence
2. **Counterclaim Phase**: Defender agent identifies guards and mitigations
3. **Verification Phase**: Verifier agent cross-checks both sides
4. **Arbitration Phase**: Integrator issues verdict with rationale

#### 3.6.3 Evidence Anchoring

All claims must reference code locations. The system enforces evidence anchoring through validation:

- Claims without code references are rejected
- Evidence links must resolve to valid source locations
- Assertions about code behavior must be verifiable against the graph

This requirement prevents hallucinated findings and ensures all claims are grounded in actual code.

#### 3.6.4 Confidence Buckets

Findings are classified into confidence buckets based on verification outcomes:

- **Confirmed**: Exploit test passes OR multi-agent consensus with no conflicts
- **Likely**: Strong evidence with score >= 0.75 and no major contradictions
- **Uncertain**: Mixed evidence, score in [0.40, 0.75), or disputed findings
- **Rejected**: Exploit test fails OR strong counter-evidence confirmed

Missing core evidence forces `uncertain` regardless of score. Tool disagreement forces `uncertain` until resolved through debate.

---

## 4. Protocol Context Pack

Logic bugs often require understanding of protocol economics, role capabilities, and trust assumptions. A function that appears safe in isolation may be exploitable when considering how oracles can be manipulated or how admin roles may be compromised.

### 4.1 Context Pack Structure

The protocol context pack provides structured economic context for logic-level reasoning:

**Roles and Capabilities**:
- Owner, admin, operator, user role definitions
- Capabilities and permissions per role
- Trust levels and assumptions about role behavior

**Trust Assumptions**:
- Oracle reliability expectations
- External contract trust boundaries
- Admin key custody assumptions

**Accepted Risks**:
- Known limitations accepted by the protocol
- Findings in this category are auto-filtered from results
- Reduces false positives for documented design decisions

**Off-Chain Inputs**:
- Oracle feeds and price sources
- Relayer behavior expectations
- Keeper and bot assumptions
- Admin intervention capabilities

### 4.2 Document-Code Conflict Detection

The context pack includes analysis of documentation against implementation:

- Requirements stated in docs vs. implemented in code
- Role definitions in specs vs. actual permissions
- Invariants claimed vs. enforced

Conflicts between documentation and implementation indicate potential vulnerabilities or specification drift.

### 4.3 Economic Reasoning

With protocol context, the system can reason about logic bugs that require economic understanding:

- Price manipulation attacks via oracle control
- Privilege escalation through role assumption chains
- MEV extraction through transaction ordering
- Flash loan attacks exploiting composability

These vulnerability classes require understanding of protocol economics beyond static code analysis.

---

## 5. Implementation

### 5.1 Codebase Structure

AlphaSwarm.sol is implemented in Python with the following module organization:

- `src/alphaswarm_sol/kg/builder/`: BSKG construction (10 modules, ~9,500 LOC)
- `src/alphaswarm_sol/agents/`: Multi-agent verification (17 files)
- `src/alphaswarm_sol/beads/`: Investigation packages
- `src/alphaswarm_sol/orchestration/`: Pools, routing, debate (~6,400 LOC)
- `src/alphaswarm_sol/context/`: Protocol context packs (~6,000 LOC)
- `src/alphaswarm_sol/labels/`: Semantic labeling system (~4,000 LOC)
- `src/alphaswarm_sol/tools/`: External tool integration (~12,000 LOC)
- `src/alphaswarm_sol/queries/`: VQL 2.0 query engine + Tier C matcher
- `vulndocs/`: Unified vulnerability knowledge (556+ patterns co-located with docs)
- Patterns located in `vulndocs/{category}/{subcategory}/patterns/`

### 5.2 Tool Integration

The framework integrates outputs from multiple static analysis tools:

- Slither: AST/IR parsing and base property extraction
- Aderyn: Supplementary rule-based detection
- Mythril: Symbolic execution findings
- Semgrep: Syntactic pattern matches
- Echidna: Fuzzing results
- Foundry: Test execution outcomes
- Halmos: SMT-based analysis

Tool outputs are normalized to SARIF format and deduplicated using location and vulnerability class matching.

### 5.3 Query Language

VQL 2.0 provides structured queries against the BSKG:

```
FIND functions
WHERE visibility = public
  AND writes_state
  AND NOT has_access_gate
```

Natural language queries are also supported through LLM translation:

```
"public functions that write state without access control"
```

Both query forms produce identical graph traversals.

---

## 6. Conclusion

This paper presented AlphaSwarm.sol, a behavioral vulnerability detection framework for Solidity smart contracts. The framework addresses fundamental limitations of syntactic pattern matching through semantic operations and behavioral signatures that capture what code does regardless of naming conventions.

Key contributions include:

1. **Behavioral Security Knowledge Graph**: Extracting 50+ security properties with evidence linking
2. **Semantic Operations**: A stable 20-operation vocabulary enabling name-independent detection
3. **Behavioral Signatures**: Ordered operation sequences capturing vulnerability patterns
4. **Three-Tier Patterns**: Detection spanning deterministic to semantic reasoning-dependent
5. **Adversarial Verification**: Multi-agent debate with mandatory evidence anchoring
6. **Protocol Context**: Economic reasoning for logic bug detection

### 6.1 Limitations

This technical report documents architecture and design decisions. Empirical evaluation including precision, recall, and comparison with existing tools is deferred to future work. The three-tier pattern system has been validated on test contracts but awaits evaluation on production protocols.

### 6.2 Future Work

Planned evaluation activities include:

- Performance benchmarking against DVDeFi and similar challenge sets
- Precision/recall measurement across vulnerability classes
- Comparative evaluation against CKG-LLM, SmartGuard, and LLM-SmartAudit
- Real-world deployment study with professional auditors

---

## 7. References

[1] Li et al. "LLM-Assisted Detection of Smart Contract Access Control Vulnerabilities Based on Knowledge Graphs." 2025.

[2] Ding et al. "SmartGuard: An LLM-enhanced Framework for Smart Contract Vulnerability Detection." 2025.

[3] Wei et al. "LLM-SmartAudit: Advanced Smart Contract Vulnerability Detection via LLM-Powered Multi-Agent Systems." 2025.

[4] Fan et al. "iMAD: Intelligent Multi-Agent Debate for Efficient and Accurate LLM Inference." 2025.

[5] Anthropic. "SCONE-bench: AI Agents Finding $4.6M in Smart Contract Exploits." December 2025.

---

## Appendices

- [Appendix A: Semantic Operations Reference](appendix-operations.md)
- [Appendix B: Pattern Examples](appendix-patterns.md)
