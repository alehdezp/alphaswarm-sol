# AlphaSwarm.sol: Philosophy and Vision

This document defines AlphaSwarm.sol's core philosophy, the problem it solves, the execution model, and the target state for the 9-stage audit workflow.

---

## The Problem

**Smart contract security has a fundamental gap.**

| Approach | Strengths | Weaknesses |
|----------|-----------|------------|
| **Static analyzers** (Slither, Mythril) | Fast, deterministic, scalable | Miss complex logic bugs, authorization flaws, economic vulnerabilities |
| **Human auditors** | Find subtle bugs, understand context | Expensive, don't scale, inconsistent |
| **LLMs alone** | Flexible reasoning, natural language | Hallucinate, no evidence grounding, unreliable |

The result:
- **90% of DeFi hacks** come from logic bugs and authorization issues, not reentrancy
- **Static tools** catch the easy stuff but miss what matters
- **Human auditors** find the hard bugs but can't audit everything
- **LLMs** reason well but fabricate evidence and miss code-level details

**The gap:** No tool reasons like a human auditor with evidence grounding at scale.

---

## The Core Insight

**Names lie. Behavior does not.**

Traditional tools detect a function named `withdraw()`. Rename it to `processPayment()` and naive rules fail. AlphaSwarm.sol detects the **behavior**:

```
R:bal -> X:out -> W:bal
(read balance, external call, write balance)
```

The function name is irrelevant. The behavioral pattern reveals the vulnerability.

**But behavior detection alone is not enough.** Complex vulnerabilities require:
- Cross-function reasoning (call paths across multiple functions)
- Protocol context (economic incentives, trust boundaries, upgrade mechanisms)
- Adversarial thinking (what can an attacker do with this?)
- Evidence grounding (findings must trace to code, not LLM assertions)

**AlphaSwarm.sol combines:**
1. **Behavioral knowledge graph** — Rich semantic properties per function
2. **Multi-agent verification** — Attacker, defender, verifier debate with evidence
3. **Claude Code orchestration** — Coordinated AI agents with tool access
4. **Proof tokens** — Non-fakeable evidence of actual analysis

---

## Vision Statement

AlphaSwarm.sol is the **behavioral security platform for Solidity**. It detects the full spectrum of vulnerabilities—including subtle logic bugs and weak authorization that only appear under real protocol assumptions. It helps auditors reason about monetary loss, user trust, and systemic risk—not just code patterns.

**The goal:** Build the world's best AI-powered Solidity security tool that finds vulnerabilities like a top human auditor—with complex reasoning, cross-function analysis, and protocol-aware context—not just pattern matching.

---

## Execution Model (Critical)

**AlphaSwarm.sol is NOT a CLI tool. It is a Claude Code orchestration framework.**

This distinction is fundamental. The user interacts with **Claude Code**, not with a terminal. Claude Code is the orchestrator that:
- Creates and manages tasks (TaskCreate, TaskUpdate)
- Spawns specialized subagents (attacker, defender, verifier)
- Calls CLI tools via Bash (`alphaswarm build-kg`, `tools run`, etc.)
- Synthesizes findings and produces reports

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         EXECUTION MODEL                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   User                                                                   │
│     │                                                                    │
│     │  "Audit my contracts" or /vrs-audit                               │
│     ▼                                                                    │
│   ┌──────────────────────────────────────────────────────────────────┐  │
│   │ Claude Code (THE ORCHESTRATOR)                                    │  │
│   │                                                                    │  │
│   │  Skills tell Claude Code WHAT to do:                              │  │
│   │  - /vrs-audit, /vrs-verify, /vrs-discover, etc.                   │  │
│   │                                                                    │  │
│   │  Claude Code uses TOOLS to do it:                                 │  │
│   │  - TaskCreate/TaskUpdate → manage work items                      │  │
│   │  - Task (subagent_type) → spawn attacker/defender/verifier        │  │
│   │  - Bash → call alphaswarm CLI commands                            │  │
│   │  - Read/Write → manage state and evidence                         │  │
│   └──────────────────────────────────────────────────────────────────┘  │
│          │              │                │                               │
│          │              │                │                               │
│          ▼              ▼                ▼                               │
│   ┌──────────┐   ┌──────────┐   ┌────────────────┐                      │
│   │ Subagent │   │ Subagent │   │ CLI (Bash)     │                      │
│   │ Attacker │   │ Defender │   │ alphaswarm ... │                      │
│   └──────────┘   └──────────┘   └────────────────┘                      │
│          │              │                │                               │
│          └──────────────┴────────────────┘                               │
│                         │                                                │
│                         ▼                                                │
│                  ┌─────────────┐                                         │
│                  │ Subagent    │                                         │
│                  │ Verifier    │  ← Arbitrates attacker vs defender     │
│                  └─────────────┘                                         │
│                         │                                                │
│                         ▼                                                │
│                  Verdicts + Evidence Packets                             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Why This Architecture?

**Rented orchestration:** We don't own Claude Code; we guide it via skills and prompts. This creates unique challenges:
- Skills must be explicit about tool usage (TaskCreate, Bash, etc.)
- Evidence must be captured in transcripts and artifacts
- State must persist across sessions and context resets

**Multi-agent coordination:** Specialized agents must debate, produce evidence, and reach verdicts. This requires:
- Clear handoff protocols between agents
- Scope enforcement (agents must not drift)
- Evidence linking (every claim traces to graph nodes)

**No established patterns:** This is genuinely novel. We are building the patterns as we build the tool.

### Key Components

| Component | Role | Location |
|-----------|------|----------|
| **Skills** | Guide Claude Code behavior | `.claude/skills/`, `src/.../skills/` |
| **Subagents** | Isolated investigation contexts | `src/.../agents/catalog.yaml` |
| **CLI** | Tools called by Claude Code | `src/alphaswarm_sol/cli/` |
| **Hooks** | Enforce workflow compliance | `docs/reference/claude-code-orchestration.md` |
| **State** | Persist progress across sessions | `.vrs/state/current.yaml` |

---

## The 9-Stage Audit Pipeline

The product is `/vrs-audit`—a fully orchestrated pipeline:

```
/vrs-audit contracts/

Stage 1: Preflight         → Validate settings, check tools, load state
Stage 2: Build Graph       → alphaswarm build-kg (200+ properties/function)
Stage 3: Protocol Context  → Economic context via Exa MCP search
Stage 4: Tool Init         → Run static analyzers (Slither, Aderyn)
Stage 5: Pattern Detection → 466 active patterns, Tier A/B/C
Stage 6: Task Creation     → TaskCreate per candidate finding
Stage 7: Verification      → Attacker → Defender → Verifier debate
Stage 8: Report Generation → Evidence-linked findings
Stage 9: Progress Update   → Store state, emit resume hints
```

### Stage Flow

```
Solidity Source
    │
    ▼
Static Parsers (Slither, Aderyn)
    │
    ▼
BSKG (nodes, edges, properties, operations, signatures)
    │
    ▼
Protocol Context Pack (Exa MCP research)
    │
    ▼
Pattern Engine (Tier A strict + Tier B exploratory + Tier C labels)
    │
    ▼
TaskCreate per candidate → Agent Investigation
    │
    ▼
Multi-Agent Debate (attacker/defender/verifier)
    │
    ▼
TaskUpdate with verdicts + Evidence Packets
    │
    ▼
Report + Human Escalation
```

### Required Orchestration Markers

Every audit must emit these markers in transcripts:

| Marker | Stage | Purpose |
|--------|-------|---------|
| `[PREFLIGHT_PASS]` or `[PREFLIGHT_FAIL]` | 1 | Gate validation |
| `[GRAPH_BUILD_SUCCESS]` | 2 | Graph construction |
| `[CONTEXT_READY]` | 3 | Protocol context available |
| `[TOOLS_COMPLETE]` | 4 | Static analysis done |
| `[DETECTION_COMPLETE]` | 5 | Pattern matching done |
| `TaskCreate(task-id)` | 6 | Task lifecycle start |
| `TaskUpdate(task-id, verdict)` | 7 | Task lifecycle end |
| `[REPORT_GENERATED]` | 8 | Report produced |
| `[PROGRESS_SAVED]` | 9 | State persisted |

Without these markers, orchestration did not happen.

---

## The Pillars

### 1. Behavior-First Knowledge Graph (BSKG)

Rich nodes with properties, evidence, and cross-links. Queryable by agents in natural language and VQL. Every function is annotated with:
- Semantic operations (what it does)
- Behavioral signature (operation ordering)
- Properties (access gates, value handling, etc.)
- Cross-contract relationships

### 2. Semantic Operations

Operations capture intent, not names. Core vocabulary:

| Category | Operations |
|----------|------------|
| **Value** | `TRANSFERS_VALUE_OUT`, `READS_USER_BALANCE`, `WRITES_USER_BALANCE` |
| **Access** | `CHECKS_PERMISSION`, `MODIFIES_OWNER`, `MODIFIES_ROLES` |
| **External** | `CALLS_EXTERNAL`, `CALLS_UNTRUSTED`, `READS_EXTERNAL_VALUE` |
| **State** | `MODIFIES_CRITICAL_STATE`, `READS_ORACLE`, `INITIALIZES_STATE` |

### 3. Behavioral Signatures

Compact sequences of operation codes describing execution order:

```
R:bal -> X:out -> W:bal   # reentrancy candidate
R:bal -> W:bal -> X:out   # safe CEI pattern
C:auth -> M:crit          # access control pattern
R:orc -> A:div -> X:out   # oracle + arithmetic + value out
```

### 4. Three-Tier Pattern System

**Tier A:** Strict, graph-only, high confidence (deterministic)
**Tier B:** Exploratory, LLM-verified, targets complex logic bugs
**Tier C:** Label-dependent, uses semantic role annotations

466 active patterns across 18 vulnerability categories (39 archived, 57 quarantined).

### 5. Multi-Agent Verification

Specialized roles debate, test, and verify findings:

| Role | Purpose | Model |
|------|---------|-------|
| **Attacker** | Construct exploit paths, attack preconditions | opus |
| **Defender** | Find guards, mitigations, invariants | sonnet |
| **Verifier** | Cross-check evidence, arbitrate disputes | opus |
| **Test Builder** | Generate Foundry exploit PoCs | sonnet |

Multiple models reduce correlated failures. Debate protocol requires evidence from BSKG.

### 6. Beads-Based Investigation

Every finding becomes a trackable, evidence-linked work unit (bead). Beads are grouped into pools for batch workflows. Work persists across sessions and agents.

### 7. Protocol Context

Compact context packs built from Exa MCP research:
- Protocol type and common exploits
- Economic incentives and attack vectors
- Off-chain dependencies (oracles, relayers, admins)
- Historical vulnerabilities in similar protocols

---

## Evidence Requirements

All findings require evidence-linked conclusions. The system enforces:

### Proof Token Types

1. **BSKG Build Proof** — Graph hash, node/edge counts, sample nodes
2. **Agent Spawn Proof** — Nodes queried, VQL executed, findings produced
3. **Debate Proof** — Attacker/defender/verifier claims with evidence
4. **Detection Proof** — Evidence chain linking finding to ground truth

Every proof token includes timestamps, graph references, and verification data.

### Graph-First Rule

**Agents MUST query BSKG before conclusions.** No manual code reading before graph queries run. Findings must cite:
- Graph node IDs
- Matched properties
- Operation sequences
- Source locations

---

## Validation Gates (G0-G7)

All audits pass through validation gates:

| Gate | Purpose |
|------|---------|
| **G0 Preflight** | Tool versions, environment, dataset hashes |
| **G1 Evidence Integrity** | Proof tokens present and valid |
| **G2 Graph Soundness** | Graph hash matches, property coverage |
| **G3 Ground Truth Coverage** | Category coverage thresholds met |
| **G4 Mutation Robustness** | Mutation testing pass rate |
| **G5 Consensus & Variance** | Multi-run stability |
| **G6 Regression Baseline** | No drop vs baseline |
| **G7 Continuous Health** | Pipeline status, trend reports |

---

## Confidence Model

Primary output is qualitative bucket with rationale:

| Bucket | Meaning |
|--------|---------|
| **confirmed** | Verified by test or convergent multi-agent evidence |
| **likely** | Strong behavioral evidence, no exploit proof yet |
| **uncertain** | Weak or conflicting signals, needs human review |
| **rejected** | Disproven or explained as benign |

Rules:
- No "confirmed" without evidence + verification
- Missing context defaults to `uncertain`
- Tool disagreement forces `uncertain` until resolved
- 100%/100% metrics trigger fabrication investigation

---

## Current State (Milestone 6.0)

### What Works Today

| Component | Status | Evidence |
|-----------|--------|----------|
| BSKG Builder | **Works** | Builds graph from Solidity via Slither |
| Pattern Engine | **Works** | 466 active patterns, loads and matches on real contracts |
| Router/Resume | **Works** | State advancement prevents infinite loops |
| Property Pipeline | **Works** | 275 properties emitted, 90.5% consumed by patterns |
| CI Gate | **Works** | Orphan + broken-pattern ratchet active |

### What Doesn't Work Yet

| Component | Current State | Target Phase |
|-----------|---------------|--------------|
| `/vrs-audit` E2E | Breaks at Stage 4 | Phase 3 |
| Multi-agent debate | Never executed | Phase 4 |
| Benchmarks | Zero ever run | Phase 5 |
| Orchestration markers | Not emitted | Phase 3-4 |
| TaskCreate/TaskUpdate lifecycle | Theoretical | Phase 3 |

### Roadmap (v6.0: From Theory to Reality)

| Phase | Goal | Status |
|-------|------|--------|
| 1 + 1.1 | Emergency Triage + Critical Review | COMPLETE |
| 2 + 2.1 | Property Gap + Critical Review | COMPLETE |
| **3** | **First Working Audit** | **NEXT** |
| 4 | Agent Teams Debate | PLANNED |
| 5 | Benchmark Reality | PLANNED |
| 6 | Test Framework Overhaul | PLANNED |
| 7 | Documentation Honesty + Hooks | PLANNED |
| 8 | Ship What Works | PLANNED |

**Philosophy:** Nothing ships until proven. Prove everything. Ship only what works.

---

## Why This Is Hard

This project is genuinely novel. Most security tools are:
- Static analyzers (Slither, Mythril) — run once, produce findings
- Rule-based scanners — pattern match, no reasoning

**AlphaSwarm.sol is different:**

| Traditional Tool | AlphaSwarm.sol |
|------------------|----------------|
| CLI produces findings | Claude Code orchestrates multi-agent debate |
| Single-pass analysis | Iterative attacker ↔ defender ↔ verifier |
| Pattern matching | Graph-first reasoning + economic context |
| Deterministic output | LLM-driven hypothesis and verification |
| User reads report | User interacts with Claude Code throughout |

**The complexity comes from:**
1. **Rented orchestration** — Claude Code is not ours; we guide it via skills/prompts
2. **Multi-agent coordination** — Attacker, defender, verifier must produce coherent debate
3. **Tool integration** — CLI, graph, external tools, all called by Claude Code
4. **State management** — Progress, resume, task lifecycle across sessions
5. **Evidence requirements** — Every finding must trace to graph nodes and code locations

**No established patterns exist for this.** We are building the patterns as we build the tool.

---

## Tool Integration

AlphaSwarm.sol integrates and normalizes outputs from:

| Tool | Purpose |
|------|---------|
| Slither | AST/IR analysis, detector results |
| Aderyn | Rust-based static analysis |
| Mythril | Symbolic execution |
| Echidna/Medusa | Fuzzing |
| Foundry | Test generation and execution |
| Semgrep | Syntactic rules |
| Halmos | SMT-assisted analysis |

Deduplication and disagreement tracking are first-class. Tool disagreements are routed to multi-agent debate.

---

## Glossary

| Term | Definition |
|------|------------|
| **BSKG** | Behavioral Security Knowledge Graph |
| **Behavioral signature** | Sequence of operation codes reflecting function behavior |
| **Semantic operation** | Normalized action extracted from code behavior |
| **Property** | Derived attribute on a node (e.g., `has_access_gate`) |
| **Pattern** | Rule matching properties/operations to detect vulnerabilities |
| **Evidence packet** | Compact, LLM-friendly bundle for a single finding |
| **Bead** | Atomic unit of investigation (task, evidence, verdict) |
| **Pool** | Batch of beads tracked together across a workflow |
| **Proof token** | Non-fakeable evidence of actual execution |
| **VQL** | Vulnerability Query Language for BSKG |
| **Skill** | Prompt that guides Claude Code behavior |
| **Subagent** | Isolated Claude Code context for scope-limited work |
| **Orchestration marker** | Transcript evidence that a workflow step executed |

---

## Runtime Surfaces

**Claude Code (primary):** Human-in-the-loop orchestration, `/vrs-*` workflows, task + subagent coordination
**CLI (subordinate tool):** Tool calls executed by Claude Code (or by developers in debug/CI workflows)
**SDK:** Headless operation, typed APIs, and background automation

All surfaces drive the same artifact contracts, but Claude Code is the primary product interface.

---

## Success Criteria

- Auditors run full analyses, query behavior, and verify findings quickly
- Complex logic bugs and permissive authorization are surfaced reliably
- LLM agents provide evidence-linked findings and honest uncertainty
- Beads keep investigations stable across sessions and agents
- Gauntlet testing achieves 80%+ accuracy on adversarial challenges
- All findings traceable through proof token chain
- Orchestration markers present in all audit transcripts

---

## Related Documentation

- [Architecture](architecture.md) — System components and modules
- [Workflows](workflows/README.md) — 9-stage pipeline details
- [Claude Code Orchestration](reference/claude-code-orchestration.md) — Hooks, tasks, subagents
- [Patterns Guide](guides/patterns.md) — Pattern authoring
- [Agents Reference](reference/agents.md) — Agent catalog
- [Testing Framework](reference/testing-framework.md) — Validation rules
