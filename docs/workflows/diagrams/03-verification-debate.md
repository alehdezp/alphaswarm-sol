# Verification & Debate Protocol

**Purpose:** Define the multi-agent debate protocol for finding verification.

## Protocol Overview

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant B as Bead
    participant A as Attacker<br/>(opus)
    participant D as Defender<br/>(sonnet)
    participant V as Verifier<br/>(opus)
    participant C as Contradiction<br/>(optional)

    Note over O,V: Phase 1: Setup
    O->>B: Create bead from candidate
    B-->>O: bead_id

    Note over O,V: Phase 2: Attack Analysis
    O->>A: Analyze bead
    A->>A: Construct exploit path
    A->>A: Estimate exploitability
    A-->>O: Attack narrative + evidence

    Note over O,V: Phase 3: Defense Analysis
    O->>D: Analyze with attack context
    D->>D: Search guards/mitigations
    D->>D: Assess residual risk
    D-->>O: Defense narrative + evidence

    Note over O,V: Phase 4: Optional Debate
    opt Conflicting Evidence
        A->>V: Rebuttal: guards insufficient
        D->>V: Counter: bypass impossible
    end

    Note over O,V: Phase 5: Arbitration
    O->>V: All evidence
    V->>V: Cross-check claims
    V->>V: Determine verdict
    V-->>O: Verdict + confidence + rationale

    Note over O,V: Phase 6: Optional Contradiction
    opt Low Confidence
        O->>C: Challenge verdict
        C->>C: Find refutations only
        C-->>O: Counter-evidence
    end
```

## Agent Roles

```mermaid
flowchart TB
    subgraph Attacker["Attacker Agent (opus)"]
        A1["Role: Construct exploit paths"]
        A2["Bias: Assume vulnerability exists"]
        A3["Output: Attack preconditions<br/>Attack steps<br/>Exploitability<br/>Impact"]
    end

    subgraph Defender["Defender Agent (sonnet)"]
        D1["Role: Find guards/mitigations"]
        D2["Bias: Search for protection"]
        D3["Output: Guards found<br/>Mitigation analysis<br/>Residual risks"]
    end

    subgraph Verifier["Verifier Agent (opus)"]
        V1["Role: Arbitrate dispute"]
        V2["Bias: Evidence-first"]
        V3["Output: Verdict<br/>Confidence<br/>Evidence quality<br/>Rationale"]
    end

    subgraph Contradiction["Contradiction Agent (sonnet)"]
        C1["Role: Refutation only"]
        C2["Bias: Never confirms"]
        C3["Output: Refutations<br/>Counter-evidence<br/>Strength"]
    end
```

## Evidence Requirements

### Attacker Evidence

```yaml
attacker_output:
  attack_preconditions:
    - "msg.sender can be any address"
    - "No rate limiting on withdraw"
  attack_steps:
    - step: 1
      action: "Call withdraw(100 ether)"
      result: "External call before state update"
    - step: 2
      action: "Reenter via fallback"
      result: "Drain funds"
  exploitability: "HIGH"
  impact: "Complete fund drainage"
  evidence:
    - type: "graph_node"
      id: "func_vault_withdraw_123"
      property: "behavioral_signature"
      value: "R:bal -> X:out -> W:bal"
    - type: "code_location"
      file: "Vault.sol"
      line: 48
      snippet: "msg.sender.call{value: amount}(\"\")"
```

### Defender Evidence

```yaml
defender_output:
  guards_found:
    - guard: "nonReentrant modifier"
      location: "Vault.sol:42"
      effectiveness: "NONE - not applied"
    - guard: "onlyOwner modifier"
      location: "Vault.sol:42"
      effectiveness: "PARTIAL - limits callers"
  mitigation_analysis: |
    The onlyOwner modifier limits attack surface but
    owner can still self-drain. No CEI pattern.
  residual_risks:
    - "Owner-initiated reentrancy still possible"
  evidence:
    - type: "graph_node"
      id: "func_vault_withdraw_123"
      property: "has_reentrancy_guard"
      value: false
```

### Verifier Evidence

```yaml
verifier_output:
  verdict: "confirmed"
  confidence: 0.92
  evidence_quality: "HIGH"
  verdict_rationale: |
    Attacker correctly identified R:bal -> X:out -> W:bal pattern.
    Defender found no effective guard (nonReentrant missing).
    onlyOwner limits attack surface but owner can exploit.
    Cross-checked with graph properties: has_reentrancy_guard=false.
  evidence_synthesis:
    attacker_claims_valid: 2
    attacker_claims_refuted: 0
    defender_guards_effective: 0
    defender_guards_partial: 1
```

## Debate Flow

```mermaid
flowchart TB
    subgraph NoDebate["Simple Case: No Debate"]
        N1["Attacker: Clear exploit"]
        N2["Defender: No guards"]
        N3["Verifier: Confirm"]
    end

    subgraph WithDebate["Complex Case: Debate Required"]
        W1["Attacker: Claims exploit"]
        W2["Defender: Claims guard exists"]
        W3["Conflict detected"]
        W4["Attacker: Rebuttal"]
        W5["Defender: Counter"]
        W6["Verifier: Arbitrate"]
    end

    N1 --> N2 --> N3

    W1 --> W2 --> W3
    W3 --> W4 --> W5 --> W6
```

### When Debate Triggers

| Condition | Debate? |
|-----------|---------|
| Attacker HIGH + Defender NO_GUARD | No |
| Attacker HIGH + Defender GUARD_FOUND | **Yes** |
| Attacker MEDIUM + Defender PARTIAL | **Yes** |
| Attacker LOW | No (discard) |

## Debate Protocol Rules

```mermaid
flowchart LR
    subgraph Rules["Protocol Rules"]
        R1["Max 3 rounds"]
        R2["Each claim must cite evidence"]
        R3["No new vulnerabilities"]
        R4["Verifier breaks ties"]
    end

    subgraph Round["Each Round"]
        A["Attacker: Claim + Evidence"]
        D["Defender: Counter + Evidence"]
        V["Verifier: Assess"]
    end

    R1 --> Round
    R2 --> A
    R2 --> D
    R4 --> V
```

**Round Limits:**
- Round 1: Initial claims
- Round 2: Rebuttals
- Round 3: Final counter (if needed)
- After Round 3: Verifier decides

## Verdict Determination

```mermaid
flowchart TB
    subgraph Evidence["Evidence Collection"]
        E1["Attacker evidence items"]
        E2["Defender evidence items"]
        E3["Graph verification"]
        E4["Code inspection"]
    end

    subgraph Scoring["Evidence Scoring"]
        S1["Count valid attacker claims"]
        S2["Count effective guards"]
        S3["Calculate confidence"]
    end

    subgraph Decision["Verdict Decision"]
        D1{"Exploit<br/>feasible?"}
        D2{"Guards<br/>effective?"}
        D3["confirmed"]
        D4["likely"]
        D5["uncertain"]
        D6["rejected"]
    end

    E1 --> S1
    E2 --> S2
    E3 --> S3
    E4 --> S3

    S1 --> D1
    S2 --> D2

    D1 -->|Yes| D2
    D1 -->|No| D6

    D2 -->|No| D3
    D2 -->|Partial| D4
    D2 -->|Yes| D5
```

**Confidence Calculation:**
```
confidence = (valid_attack_claims / total_claims) *
             (1 - effective_guards / total_guards) *
             graph_evidence_quality
```

## False Positive Flow

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant A as Attacker
    participant D as Defender
    participant V as Verifier

    O->>A: Analyze candidate
    A->>A: Attempt exploit construction
    A-->>O: "No feasible exploit path"

    O->>D: Confirm defense
    D->>D: Find guards
    D-->>O: "Effective guard: nonReentrant"

    O->>V: Arbitrate
    V->>V: Verify guard effectiveness
    V-->>O: verdict: rejected

    Note over O,V: TaskUpdate with rejection rationale
```

**Rejection Evidence Required:**
- Why exploit path fails
- Which guard prevents attack
- Graph evidence of guard presence

## Integration with Task System

```mermaid
flowchart TB
    subgraph TaskCreate["TaskCreate"]
        T1["subject: Investigate reentrancy"]
        T2["status: pending"]
    end

    subgraph AttackerPhase["Attacker Phase"]
        A1["TaskUpdate: owner=attacker"]
        A2["TaskUpdate: evidence+=attack"]
    end

    subgraph DefenderPhase["Defender Phase"]
        D1["TaskUpdate: owner=defender"]
        D2["TaskUpdate: evidence+=defense"]
    end

    subgraph VerifierPhase["Verifier Phase"]
        V1["TaskUpdate: owner=verifier"]
        V2["TaskUpdate: verdict=confirmed"]
        V3["TaskUpdate: status=completed"]
    end

    TaskCreate --> AttackerPhase --> DefenderPhase --> VerifierPhase
```

## Hook Enforcement

```mermaid
flowchart TB
    subgraph StopHook["Stop/SubagentStop Hook"]
        H1{"All agents<br/>completed?"}
        H2{"Evidence<br/>attached?"}
        H3{"Verdict<br/>determined?"}
        BLOCK["Block completion"]
        ALLOW["Allow completion"]
    end

    H1 -->|No| BLOCK
    H1 -->|Yes| H2
    H2 -->|No| BLOCK
    H2 -->|Yes| H3
    H3 -->|No| BLOCK
    H3 -->|Yes| ALLOW
```

## Marker Summary

| Phase | Markers |
|-------|---------|
| Attacker spawn | `[ATTACKER_SPAWN task_id]` |
| Attacker done | `[ATTACKER_DONE exploit:feasible/not_feasible]` |
| Defender spawn | `[DEFENDER_SPAWN task_id]` |
| Defender done | `[DEFENDER_DONE guards:N]` |
| Debate start | `[DEBATE_START task_id round:1]` |
| Debate round | `[DEBATE_ROUND:N]` |
| Verifier spawn | `[VERIFIER_SPAWN task_id]` |
| Verdict | `[VERDICT:confirmed/likely/uncertain/rejected confidence:0.XX]` |
| Contradiction | `[CONTRADICTION_SPAWN]` (optional) |
