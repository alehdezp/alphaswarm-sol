# BSKG Behavioral Signature Flow

## From Code to Signature

```mermaid
flowchart TB
    subgraph Source["Solidity Source"]
        CODE["function processPayment(uint value) external {<br/>    require(userFunds[msg.sender] >= value);<br/>    (bool success,) = msg.sender.call{value: value}(\"\");<br/>    userFunds[msg.sender] -= value;<br/>}"]
    end

    subgraph Slither["Slither Parsing"]
        AST[Abstract Syntax Tree]
        CFG[Control Flow Graph]
        IR[Slither IR]
    end

    subgraph Extraction["Property & Operation Extraction"]
        PROP1["visibility: external"]
        PROP2["sends_value: true"]
        PROP3["reads_balances: true"]
        PROP4["writes_balances: true"]
        PROP5["has_reentrancy_guard: false"]

        OP1["READS_USER_BALANCE<br/>userFunds[msg.sender]"]
        OP2["TRANSFERS_VALUE_OUT<br/>msg.sender.call{value: value}"]
        OP3["WRITES_USER_BALANCE<br/>userFunds[msg.sender] -= value"]
    end

    subgraph Ordering["Order Analysis"]
        SEQ["Execution Order:<br/>1. require (read)<br/>2. call (transfer)<br/>3. assignment (write)"]
    end

    subgraph Signature["Behavioral Signature"]
        SIG["R:bal → X:out → W:bal"]
        CODES["Signature Codes:<br/>R:bal = read user balance<br/>X:out = transfer value out<br/>W:bal = write user balance"]
    end

    subgraph Matching["Pattern Matching"]
        PATTERN["Pattern: reentrancy-classic<br/>Requires: X:out before W:bal<br/>Without: reentrancy_guard"]
        MATCH["MATCH: Vulnerable Pattern"]
    end

    CODE --> AST
    AST --> CFG
    CFG --> IR

    IR --> PROP1
    IR --> PROP2
    IR --> PROP3
    IR --> PROP4
    IR --> PROP5

    IR --> OP1
    IR --> OP2
    IR --> OP3

    OP1 --> SEQ
    OP2 --> SEQ
    OP3 --> SEQ

    SEQ --> SIG
    SIG --> CODES

    SIG --> PATTERN
    PROP5 --> PATTERN
    PATTERN --> MATCH
```

## Signature Code Reference

```mermaid
mindmap
  root((Signature Codes))
    Value Operations
      R:bal[R:bal<br/>Read User Balance]
      W:bal[W:bal<br/>Write User Balance]
      X:out[X:out<br/>Transfer Value Out]
      X:in[X:in<br/>Receive Value In]
    External Operations
      X:call[X:call<br/>External Call]
      X:unk[X:unk<br/>Call Untrusted]
      R:ext[R:ext<br/>Read External]
    Access Operations
      C:auth[C:auth<br/>Permission Check]
      M:own[M:own<br/>Modify Owner]
      M:role[M:role<br/>Modify Role]
      M:crit[M:crit<br/>Modify Critical]
    Oracle & Data
      R:orc[R:orc<br/>Read Oracle]
      U:time[U:time<br/>Use Timestamp]
      U:blk[U:blk<br/>Use Block Data]
    Arithmetic
      A:div[A:div<br/>Division]
      A:mul[A:mul<br/>Multiplication]
    Other
      V:in[V:in<br/>Validate Input]
      E:evt[E:evt<br/>Emit Event]
      I:init[I:init<br/>Initializer]
      L:arr[L:arr<br/>Loop Array]
```

## Safe vs Vulnerable Signatures

```mermaid
flowchart LR
    subgraph Vulnerable["Vulnerable: Reentrancy"]
        V_READ["R:bal<br/>Read Balance"]
        V_CALL["X:out<br/>External Call"]
        V_WRITE["W:bal<br/>Write Balance"]
        V_READ --> V_CALL --> V_WRITE
    end

    subgraph Safe["Safe: CEI Pattern"]
        S_READ["R:bal<br/>Read Balance"]
        S_WRITE["W:bal<br/>Write Balance"]
        S_CALL["X:out<br/>External Call"]
        S_READ --> S_WRITE --> S_CALL
    end

    style V_CALL fill:#f66,stroke:#900
    style S_WRITE fill:#6f6,stroke:#090
```

## Evidence Linking

```mermaid
flowchart TB
    subgraph Finding["Detection Finding"]
        SIG2["Signature: R:bal → X:out → W:bal"]
        VULN["Vulnerability: Reentrancy"]
    end

    subgraph Evidence["Evidence Links"]
        E1["Source: Vault.sol:42-55"]
        E2["Contract: Vault"]
        E3["Function: processPayment"]
        E4["Operation: TRANSFERS_VALUE_OUT<br/>Line 48: msg.sender.call{value: value}"]
        E5["Operation: WRITES_USER_BALANCE<br/>Line 52: userFunds[msg.sender] -= value"]
    end

    subgraph Verification["Auditor Verification"]
        CHECK["Code reference verifiable"]
        GROUND["All claims grounded in source"]
    end

    SIG2 --> E1
    VULN --> E2
    E2 --> E3
    E3 --> E4
    E3 --> E5

    E4 --> CHECK
    E5 --> CHECK
    CHECK --> GROUND
```
