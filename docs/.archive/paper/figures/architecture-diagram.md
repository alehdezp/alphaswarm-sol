# AlphaSwarm.sol Architecture Diagram

## End-to-End System Flow

```mermaid
flowchart TB
    subgraph Input["Input Layer"]
        SOL[Solidity Source]
        DOCS[Protocol Documentation]
    end

    subgraph Builder["BSKG Builder"]
        SLITHER[Slither Parser]
        PROPS[Property Extraction<br/>50+ properties/function]
        OPS[Semantic Operations<br/>20 core operations]
        SIGS[Behavioral Signatures<br/>R:bal → X:out → W:bal]
        BSKG[(BSKG<br/>Behavioral Security<br/>Knowledge Graph)]
    end

    subgraph Context["Protocol Context"]
        ROLES[Roles & Capabilities]
        TRUST[Trust Assumptions]
        OFFCHAIN[Off-Chain Inputs]
        CTXPACK[Context Pack]
    end

    subgraph Detection["Pattern Engine"]
        TIERA[Tier A Patterns<br/>Deterministic, Graph-only]
        TIERB[Tier B Patterns<br/>LLM-verified, Exploratory]
        TIERC[Tier C Patterns<br/>Label-dependent, Semantic]
        CANDS[Candidate Findings]
    end

    subgraph Orchestration["Beads & Orchestration"]
        BEADS[Beads<br/>Investigation Packages]
        POOL[Agent Pool<br/>Routing & Assignment]
    end

    subgraph Agents["Adversarial Verification"]
        ATK[Attacker Agent<br/>Exploit Construction]
        DEF[Defender Agent<br/>Guard Search]
        VER[Verifier Agent<br/>Evidence Cross-check]
        DEBATE[Debate Protocol<br/>Claim/Counterclaim/Arbitration]
    end

    subgraph Output["Output Layer"]
        VERDICT[Verdicts<br/>confirmed/likely/uncertain/rejected]
        EVIDENCE[Evidence Packets<br/>Code-linked Rationale]
        REPORT[Audit Report]
    end

    %% Flow connections
    SOL --> SLITHER
    SLITHER --> PROPS
    PROPS --> OPS
    OPS --> SIGS
    PROPS --> BSKG
    OPS --> BSKG
    SIGS --> BSKG

    DOCS --> ROLES
    DOCS --> TRUST
    DOCS --> OFFCHAIN
    ROLES --> CTXPACK
    TRUST --> CTXPACK
    OFFCHAIN --> CTXPACK

    BSKG --> TIERA
    BSKG --> TIERB
    BSKG --> TIERC
    CTXPACK --> TIERB
    CTXPACK --> TIERC

    TIERA --> CANDS
    TIERB --> CANDS
    TIERC --> CANDS

    CANDS --> BEADS
    BEADS --> POOL

    POOL --> ATK
    POOL --> DEF
    ATK --> DEBATE
    DEF --> DEBATE
    DEBATE --> VER
    VER --> VERDICT

    VERDICT --> EVIDENCE
    EVIDENCE --> REPORT
```

## Behavioral Signature Derivation

```mermaid
flowchart LR
    subgraph Source["Source Code"]
        FUNC["function withdraw(uint amt)"]
        CODE["require(balances[msg.sender] >= amt);<br/>(bool ok,) = msg.sender.call{value: amt}(\"\");<br/>balances[msg.sender] -= amt;"]
    end

    subgraph Analysis["Semantic Analysis"]
        OP1["READS_USER_BALANCE"]
        OP2["TRANSFERS_VALUE_OUT"]
        OP3["WRITES_USER_BALANCE"]
    end

    subgraph Signature["Behavioral Signature"]
        SIG["R:bal → X:out → W:bal"]
        PATTERN["Reentrancy Pattern Match"]
    end

    FUNC --> CODE
    CODE --> OP1
    CODE --> OP2
    CODE --> OP3
    OP1 --> SIG
    OP2 --> SIG
    OP3 --> SIG
    SIG --> PATTERN
```

## Three-Tier Pattern Hierarchy

```mermaid
flowchart TB
    subgraph TierA["Tier A: Deterministic"]
        A1[Graph Properties]
        A2[Semantic Operations]
        A3[Signature Ordering]
        A4[HIGH Confidence<br/>No LLM Required]
    end

    subgraph TierB["Tier B: Exploratory"]
        B1[Graph + Context Questions]
        B2[LLM Verification]
        B3[MEDIUM Confidence<br/>Targets Complex Logic]
    end

    subgraph TierC["Tier C: Label-Dependent"]
        C1[Semantic Labels from LLM Pass]
        C2[Label Presence/Absence Matching]
        C3[MEDIUM Confidence<br/>Policy & Invariant Violations]
    end

    A1 --> A2 --> A3 --> A4
    B1 --> B2 --> B3
    C1 --> C2 --> C3
```

## Adversarial Verification Protocol

```mermaid
sequenceDiagram
    participant B as Bead
    participant A as Attacker Agent
    participant D as Defender Agent
    participant V as Verifier Agent
    participant I as Integrator

    B->>A: Candidate Finding + Evidence
    A->>A: Construct Exploit Path
    A->>D: Claim: Vulnerability exists<br/>+ Attack Narrative
    D->>D: Search Guards & Mitigations
    D->>V: Counterclaim: Guards found<br/>+ Evidence
    A->>V: Rebuttal: Guards insufficient<br/>+ Bypass
    V->>V: Cross-check all evidence
    V->>V: Run tests if available
    V->>I: Verdict + Rationale
    I->>B: Final Classification<br/>+ Confidence Bucket
```
