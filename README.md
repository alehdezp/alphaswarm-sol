# AlphaSwarm.sol

> **A behavior-first, evidence-grounded, self-testing multi-agent security
> framework for Solidity.**
>
> This is a research-grade design study and an in-progress build, not a
> shipped product. The architecture is genuinely novel; the end-to-end
> pipeline is not yet proven. This README explains what it's *planned to
> be*, what's *novel about it*, what *doesn't work yet*, and how the
> *redesign* is going to swap the orchestration runtime out from under
> the audit logic without rewriting the audit logic.

---

## Status banner

```
┌──────────────────────────────────────────────────────────────────────┐
│  Milestone v6.0 — "From Theory to Reality"                            │
│  Nothing ships until proven. Prove everything. Ship only what works.  │
├──────────────────────────────────────────────────────────────────────┤
│  Designed         ✅  Architecture, 22 phase plans, 466 patterns      │
│  Scaffolded       ✅  ~260K LOC, 24 agents, 34 skills                 │
│  Works in pieces  🟡  BSKG builder, pattern engine, router            │
│  E2E audit        ❌  /vrs-audit breaks at Stage 4                    │
│  Multi-agent run  ❌  Debate has never executed                       │
│  Benchmarks       ❌  Zero ever run                                   │
│  Public ship      ❌  Phase 8 (way out)                               │
└──────────────────────────────────────────────────────────────────────┘
```

Authoritative: [`.planning/STATE.md`](.planning/STATE.md) ·
[`.planning/ROADMAP.md`](.planning/ROADMAP.md) ·
[`docs/LIMITATIONS.md`](docs/LIMITATIONS.md)

---

## Table of contents

1. [What this is planned to be](#1--what-this-is-planned-to-be)
2. [The core insight: names lie, behavior doesn't](#2--the-core-insight)
3. [Architecture (planned)](#3--architecture-planned)
4. [Multi-agent verification](#4--multi-agent-verification)
5. [Three-tier pattern system](#5--three-tier-pattern-system)
6. [Why this is novel](#6--why-this-is-novel)
7. [Current state — what works and what doesn't](#7--current-state--what-works-and-what-doesnt)
8. [Limitations — what this cannot do (even when finished)](#8--limitations)
9. [Planned redesign — pi-mono harness](#9--planned-redesign--pi-mono-harness)
10. [Self-testing meta-loop — the framework qualifies its own replacement](#10--self-testing-meta-loop)
11. [Roadmap](#11--roadmap)
12. [Repository layout](#12--repository-layout)
13. [License & honest note to readers](#13--license--honest-note)

---

## 1 · What this is planned to be

A multi-agent orchestration framework where **specialized AI agents
audit Solidity contracts using a behavioral knowledge graph instead of
function-name pattern matching**, with every finding traced to graph
node IDs and code locations through a non-fakeable proof-token chain.

```
┌──────────────────────────────────────────────────────────────────────┐
│                    AlphaSwarm.sol (planned)                           │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                ┌─────────────────────────────┐
                │ Solidity contract(s)         │
                └──────────────┬──────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
   ┌─────────┐            ┌─────────┐            ┌─────────┐
   │ Slither │            │ Mythril │            │ Aderyn  │
   │SlithIR  │            │symbolic │            │ Rust SA │
   └────┬────┘            └────┬────┘            └────┬────┘
        └──────────────────────┼──────────────────────┘
                               ▼
            ┌──────────────────────────────────────┐
            │  BSKG — Behavioral Security KG       │
            │  Functions × ~200 properties each    │
            │  Semantic operations + signatures    │
            │  Cross-contract relationships        │
            └──────────────────┬───────────────────┘
                               │
                  ┌────────────┴────────────┐
                  ▼                         ▼
        ┌──────────────────┐      ┌──────────────────┐
        │ 466 Patterns     │      │ Protocol Context │
        │ Tier A / B / C   │      │ via Exa MCP      │
        └────────┬─────────┘      └────────┬─────────┘
                 └────────────┬────────────┘
                              ▼
              ┌──────────────────────────────┐
              │ Candidate findings           │
              └──────────────┬───────────────┘
                             ▼
              ┌──────────────────────────────┐
              │ Multi-agent verification      │
              │  ┌──────────┐ ┌──────────┐   │
              │  │ Attacker │ │ Defender │   │
              │  │  (Opus)  │ │ (Sonnet) │   │
              │  └────┬─────┘ └────┬─────┘   │
              │       └─────┬──────┘         │
              │             ▼                │
              │       ┌──────────┐           │
              │       │ Verifier │  (Opus)   │
              │       └────┬─────┘           │
              └────────────┼─────────────────┘
                           ▼
            ┌──────────────────────────────────┐
            │ Evidence-linked finding          │
            │ + proof tokens (build hash, node │
            │   IDs, debate transcript)        │
            └──────────────────────────────────┘
```

Five layers, each non-trivial on its own:

1. **BSKG** — Behavioral Security Knowledge Graph. Built from Slither's
   SlithIR, ~200 properties per function, encoded as semantic operations
   and behavioral signatures.
2. **Three-tier pattern engine** — 466 active patterns (39 archived,
   57 quarantined) across 18 vulnerability categories. Patterns are
   first-class governed objects with measured precision/recall.
3. **Tailored adversarial agents** — different models for different
   roles (Opus attacker, Sonnet defender, Opus verifier), graph-first
   evidence requirements, role-locked prompts.
4. **Tool fusion as a signal** — Slither + Mythril + Aderyn + Echidna +
   Foundry + Semgrep + Halmos integrated. Tool *disagreement*
   automatically routes to multi-agent debate.
5. **Proof tokens** — non-fakeable evidence chain. A finding without
   provenance cannot exist in the system; the integrity hook rejects
   fabricated outputs.

---

## 2 · The core insight

> **Names lie. Behavior doesn't.**

Traditional tools detect a function called `withdraw()`. Rename it to
`processPayment()` and naïve rules fail. AlphaSwarm.sol detects the
**behavior** — and the function name is irrelevant.

```
                    Same vulnerability, different names

┌──────────────────────────────────┐    ┌──────────────────────────────────┐
│ function withdraw(uint amount) { │    │ function process(uint amt) {     │
│   require(balances[msg.sender]   │    │   if (bal[msg.sender] < amt)     │
│           >= amount);            │    │       revert();                  │
│   payable(msg.sender)            │    │   payable(msg.sender)            │
│       .transfer(amount);         │    │       .send(amt);                │
│   balances[msg.sender]           │    │   bal[msg.sender] -= amt;        │
│       -= amount;                 │    │ }                                │
│ }                                │    │                                  │
└──────────────────────────────────┘    └──────────────────────────────────┘
                  │                                    │
                  ▼                                    ▼
                       Same behavioral signature

                    ┌──────────────────────────┐
                    │  R:bal -> X:out -> W:bal │
                    │  ───────────────────────  │
                    │  Reads balance            │
                    │  External call out        │
                    │  Writes balance           │
                    │  → REENTRANCY CANDIDATE   │
                    └──────────────────────────┘
```

Detection is on **semantic operations** (`TRANSFERS_VALUE_OUT`,
`READS_USER_BALANCE`, `CHECKS_PERMISSION`, `MODIFIES_CRITICAL_STATE`,
…) and the **order in which they execute**. Function renames, comment
removal, control-flow rewrites — none of it changes the signature.

The CEI (Checks-Effects-Interactions) safe pattern is the same idea
inverted: `R:bal -> W:bal -> X:out` is *always-safe* in a way that's
detectable without reading code.

---

## 3 · Architecture (planned)

### Product execution model

> **AlphaSwarm.sol is NOT a CLI tool. It is a Claude Code orchestration framework.**

```
┌────────────────────────────────────────────────────────────────┐
│                          User                                   │
│              "Audit my contracts" or  /vrs-audit                │
└────────────────────────────┬───────────────────────────────────┘
                             ▼
┌────────────────────────────────────────────────────────────────┐
│  Claude Code  (THE ORCHESTRATOR)                                │
│  ────────────────────────────────                               │
│  Skills  (.claude/skills/)        →  WHAT to do                 │
│  Subagents (attacker/defender/…)  →  WHO investigates           │
│  Bash → CLI (`alphaswarm …`)      →  HOW to inspect contracts   │
│  Hooks                            →  ENFORCE quality            │
│  TaskCreate / TaskUpdate          →  TRACK work                 │
└─────┬─────────────┬───────────────┬───────────────┬────────────┘
      ▼             ▼               ▼               ▼
 ┌─────────┐  ┌─────────┐    ┌──────────┐    ┌───────────┐
 │Subagent │  │Subagent │    │  CLI     │    │ Evidence  │
 │attacker │  │defender │    │alphaswarm│    │ packets   │
 └────┬────┘  └────┬────┘    │ build-kg │    │ (output)  │
      └─────┬──────┘         │ query    │    └───────────┘
            ▼                │ tools    │
       ┌─────────┐           │ vulndocs │
       │Subagent │           └──────────┘
       │verifier │
       └─────────┘
```

The CLI is *subordinate tooling* called by Claude Code. The user never
talks to the terminal directly.

### The 9-stage audit pipeline

```
/vrs-audit contracts/
      │
      ▼
┌──── Stage 1: Preflight ─────────────────────────────────────────────┐
│   Validate settings, check tools, load state                         │
│   Marker: [PREFLIGHT_PASS] | [PREFLIGHT_FAIL]                        │
└──────────────────────────────────────────────────────────────────────┘
      │
      ▼
┌──── Stage 2: Build Graph ───────────────────────────────────────────┐
│   alphaswarm build-kg → BSKG with ~200 props/function                │
│   Marker: [GRAPH_BUILD_SUCCESS]                                      │
└──────────────────────────────────────────────────────────────────────┘
      │
      ▼
┌──── Stage 3: Protocol Context ──────────────────────────────────────┐
│   Exa MCP research → economic context, prior exploits                │
│   Marker: [CONTEXT_READY]                                            │
└──────────────────────────────────────────────────────────────────────┘
      │
      ▼
┌──── Stage 4: Tool Init ─────────────────────────────────────────────┐
│   Slither + Aderyn (+ Mythril/Echidna/Halmos optional)               │
│   Marker: [TOOLS_COMPLETE]                                           │
└──────────────────────────────────────────────────────────────────────┘
      │
      ▼
┌──── Stage 5: Pattern Detection ─────────────────────────────────────┐
│   466 patterns × Tier A (deterministic) / B (LLM-verified) / C       │
│   Marker: [DETECTION_COMPLETE]                                       │
└──────────────────────────────────────────────────────────────────────┘
      │
      ▼
┌──── Stage 6: Task Creation ─────────────────────────────────────────┐
│   TaskCreate per candidate finding (bead lifecycle)                  │
└──────────────────────────────────────────────────────────────────────┘
      │
      ▼
┌──── Stage 7: Verification ──────────────────────────────────────────┐
│   Attacker → Defender → Verifier (multi-agent debate)                │
│   TaskUpdate(verdict)                                                │
└──────────────────────────────────────────────────────────────────────┘
      │
      ▼
┌──── Stage 8: Report ────────────────────────────────────────────────┐
│   Evidence-linked findings, proof-token chain                        │
│   Marker: [REPORT_GENERATED]                                         │
└──────────────────────────────────────────────────────────────────────┘
      │
      ▼
┌──── Stage 9: Progress ──────────────────────────────────────────────┐
│   Persist state, emit resume hints                                   │
│   Marker: [PROGRESS_SAVED]                                           │
└──────────────────────────────────────────────────────────────────────┘
```

**Without these markers in the transcript, orchestration did not
happen.** Hooks gate every stage.

---

## 4 · Multi-agent verification

A single LLM auditing its own findings is a yes-loop. Three
explicit roles, three different models, role-locked prompts:

```
                    Candidate finding
                          │
                          ▼
  ┌───────────────────────────────────────────────────────────┐
  │           Multi-agent verification (per finding)          │
  │                                                           │
  │   ┌──────────────┐                  ┌──────────────┐      │
  │   │  ATTACKER    │   evidence       │  DEFENDER    │      │
  │   │  (Opus)      │ ◄──────────────► │  (Sonnet)    │      │
  │   │              │   debate         │              │      │
  │   │ Build the    │                  │ Find guards, │      │
  │   │ exploit path │                  │ prove safe   │      │
  │   └──────┬───────┘                  └──────┬───────┘      │
  │          │                                 │              │
  │          └─────────────┬───────────────────┘              │
  │                        ▼                                  │
  │                ┌──────────────┐                           │
  │                │  VERIFIER    │                           │
  │                │  (Opus)      │                           │
  │                │              │                           │
  │                │ Arbitrate.   │                           │
  │                │ Verdict +    │                           │
  │                │ confidence   │                           │
  │                └──────┬───────┘                           │
  └────────────────────── │ ──────────────────────────────────┘
                          ▼
                  Verdict ∈ {confirmed, likely, uncertain, rejected}
                  + Evidence Packet
                  + Proof tokens
```

| Role | Model | Job | Constraint |
|---|---|---|---|
| **Attacker** | Opus | Construct exploit paths from BSKG nodes | Must cite graph evidence for every step |
| **Defender** | Sonnet | Find mitigations, guards, invariants | Must show guard *dominates* the vulnerable path (not just exists) |
| **Verifier** | Opus | Arbitrate, set confidence, decide verdict | Has access to both transcripts; cannot fabricate |

**Different models per role is structural, not cosmetic.** A single
model debating itself shares priors and converges. Three models with
locked roles produce real disagreement that can be reasoned over.

The **Verifier verdict is not the end** — `inconclusive` routes back
to retrieval (more BSKG context, more tool runs) before re-debating.
Rejected findings are *also* training signal for the Pattern Miner.

---

## 5 · Three-tier pattern system

466 active patterns across 18 vulnerability categories. **Patterns are
governed objects** — they're archived, quarantined, or promoted based
on measured precision and recall.

```
┌──── Tier A — Deterministic, graph-only ─────────────────────────────┐
│                                                                      │
│   VQL / Cypher query against BSKG.                                   │
│   No LLM call. High precision, scales linearly.                      │
│   Example: "function with R:bal -> X:out -> W:bal pattern,           │
│             no nonReentrant modifier on path"                        │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
            │
            │ (when the bug needs reasoning)
            ▼
┌──── Tier B — LLM-verified ──────────────────────────────────────────┐
│                                                                      │
│   Tier A finds candidates → Sonnet verifies with graph context.      │
│   For complex logic bugs that require reading intent.                │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
            │
            │ (when classification depends on labels)
            ▼
┌──── Tier C — Label-dependent ───────────────────────────────────────┐
│                                                                      │
│   Uses semantic role annotations (e.g., "this address is the         │
│   protocol owner"). Requires upstream labeling pass.                 │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### Pattern graduation pipeline

```
   ┌─────────────────┐
   │ Cluster similar │   HDBSCAN over finding embeddings
   │   findings      │
   └────────┬────────┘
            ▼
   ┌─────────────────┐
   │ Extract pattern │   LLM synthesizes Cypher/VQL + description
   │ from cluster    │
   └────────┬────────┘
            ▼
   ┌─────────────────┐
   │ Validate on     │   Held-out audits.
   │ held-out set    │   Gate: precision ≥ 0.8, recall ≥ 0.5
   └────────┬────────┘
            ▼
   ┌─────────────────┐
   │ Promote to KG   │   Now matched without LLM.
   │ as detection    │   Knowledge GRADUATES from lesson to rule.
   │ rule            │
   └─────────────────┘
```

**Lessons graduate into capabilities the system carries forward
without re-paying the LLM cost.**

---

## 6 · Why this is novel

Smart-contract auditing has plenty of tools. None individually
distinctive piece here is new — code knowledge graphs, multi-agent
debate, RAG, Reflexion all exist in academic literature. **The
novelty is the specific composition + two design choices that other
systems don't make:**

```
behavioral KG (Slither + Mythril + Solodit + properties)
   ⨯ tailored adversarial agents (different models per role)
   ⨯ tool disagreement → debate (not averaging)
   ⨯ pattern graduation (lesson → governed rule)
   ⨯ proof-token integrity chain (no fabrication possible)
   ⨯ self-testing as a tier of the testing pyramid
   ─────────────────────────────────────────────────────────
   = an auditor that gets smarter without fine-tuning
```

### Design choice 1 — Patterns *graduate* from lessons to detection rules

Most "self-improving" agent systems store lessons as fuzzy memory
(Reflexion-style verbal feedback) and re-retrieve them at inference.
That's slow, lossy, unreviewable.

Here, the **promotion pipeline** turns clusters of confirmed findings
into validated Cypher detection rules in the BSKG. Once promoted, the
Scanner matches without LLM reasoning. This is the same
**Observed → Framed → Usable → Trusted → Governed** lifecycle used in
governed-knowledge systems for company memory, applied to vulnerability
patterns.

### Design choice 2 — Adversarial validation as structure, not vibes

Three explicit roles, three different models, role-locked prompts,
graph-first evidence requirements, integrity-checked transcripts.
The Verifier's verdict is not the end — `inconclusive` routes back
to retrieval. Rejected findings are training signal for the Miner.

### Honest comparison vs prior art

| System | Approach | Where AlphaSwarm differs |
|---|---|---|
| **Slither** | Static analysis, 100 detectors | We use Slither *as input* (BSKG is built on its IR). We add reasoning. |
| **Mythril** | Symbolic execution | Tool integrated for path-dependent bugs. |
| **Sherlock AI** | LLM auditor (found a $2.4M mainnet bug Sept 2025) | Closed source. Different bet — we expose the reasoning chain. |
| **CKG-LLM** (academic) | Code KG + LLM auditor | We add multi-agent debate + pattern graduation. |
| **LLM-SmartAudit** (IEEE TSE Oct 2025) | Multi-agent + buffer-of-thought | Architecturally closest. We add proof tokens + governed pattern lifecycle. |

**Note honestly:** these are public-vs-public comparisons. Sherlock
AI has already found a multi-million-dollar bug on mainnet. We have
not yet run a single benchmark. The architecture is more developed
than the demonstrated capability.

---

## 7 · Current state — what works and what doesn't

Read this before assuming anything works.

### Works today

| Component | Evidence |
|---|---|
| **BSKG builder** | Builds graphs from Solidity via Slither, real contracts |
| **Pattern engine** | Loads + matches 466 patterns on real contracts |
| **Property pipeline** | 275 emitted, 90.5% consumed by patterns |
| **Router / state advancement** | Pool advances `INTAKE → CONTEXT → BEADS` |
| **CI gate** | Orphan + broken-pattern ratchet active |
| **Skill / agent registry** | 34 skills, 24 agents catalogued |
| **Test infrastructure (Phase 3.1b)** | 280 tests passing, 18 adversarial corpus projects |

### Doesn't work yet

| Component | Status | Target phase |
|---|---|---|
| `/vrs-audit` E2E | Breaks at Stage 4 | Phase 3.2 ("First Working Audit") |
| Multi-agent debate execution | Never executed | Phase 4 |
| Benchmarks | Zero ever run | Phase 5 |
| Orchestration markers chain | Not emitted | Phase 3.2 / 3.1f |
| TaskCreate/TaskUpdate lifecycle | Theoretical | Phase 3.2 |
| Pi-mono harness migration | Not yet planned | (new milestone, post-v6.0) |

### Honest scale

```
260,000  lines of code across 475 Python files
    466  active patterns (39 archived, 57 quarantined)
     24  agents catalogued
     34  skills catalogued
     22  phase folders of planning
 11,282  tests (many mock-heavy, scheduled for Phase 6 overhaul)
      0  benchmarks ever run
```

**This is not a weekend project. It is also not a working tool yet.**

---

## 8 · Limitations

What this *cannot* do, even when finished. Full version:
[`docs/LIMITATIONS.md`](docs/LIMITATIONS.md).

### The fundamental gap

We detect **what code does**. We cannot detect **what code should do**.

```solidity
function withdraw(uint amount) external {
    balances[msg.sender] -= amount;
    payable(msg.sender).transfer(amount);
}
```

Without a specification, we can't know:
- *Should* users only withdraw their own funds?
- *Should* there be a withdrawal limit?
- *Should* withdrawals be pausable?

**Business logic bugs require specifications. No spec → no ground truth → uncertain findings.**

### What requires human judgment, period

- Protocol-specific invariants ("total deposits should equal sum of balances")
- Risk acceptance (is 0.1% chance of exploit acceptable? depends on TVL)
- Business impact (which finding is critical for *your* protocol?)
- Fix verification (does the patch actually work + not introduce new issues?)

### Failure modes we expect to hit

- **Pattern Miner poisoning the KG** — correlated false positives could cluster into a bad rule
- **Debate collapse** — Challenger and Defender (same base model) converge instead of disagreeing
- **Self-RAG over-filtering** — relevance gate filters out indirectly-relevant evidence
- **Halmos formal-verification false negatives** — SMT can't model some EVM constructs
- **Cost runaway** — debate × Self-RAG × Reflexion multiplies LLM calls per audit

### When NOT to use AlphaSwarm.sol

- High-value launch (>$100M TVL) → use multiple human audits
- Novel protocol design → first-principles human review
- Post-exploit forensics → Tenderly / Phalcon, not static analysis
- Compliance / certification → certified human firms

> **The portion it misses could be the one that drains your protocol. Use it to accelerate your security process, not to replace it.**

---

## 9 · Planned redesign — pi-mono harness

The current architecture rents orchestration from Claude Code. That
worked for the design phase. It's hitting structural limits as the
system grows. The redesign keeps everything *except* the orchestration
plane and rebuilds it on [`pi-mono`](https://github.com/badlogic/pi-mono).

### Current harness limits — concrete

```
                    Claude Code as harness — what hurts
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  Subagents can't spawn nested subagents                              │
│    └─ All coordination funnels through main session                  │
│       No true hierarchical delegation                                │
│                                                                      │
│  Skills are markdown prompts, not programs                           │
│    └─ Can't compose, can't call each other natively                  │
│       Can't return typed values                                      │
│                                                                      │
│  MCP boundary on every external tool                                 │
│    └─ Out-of-process latency                                         │
│       JSON serialization overhead                                    │
│       No event interception                                          │
│                                                                      │
│  Hook bug #20221: prompt-type Stop hooks send feedback but           │
│    don't actually block                                              │
│    └─ Forces command-type hooks with exit codes                      │
│       Verified the hard way                                          │
│                                                                      │
│  Driving Claude Code from outside (PiloTY-style):                    │
│    expect_prompt unreliable, send_claude string-index bugs           │
│    └─ Structural fragility around session boundaries                 │
│                                                                      │
│  Session-tree branching needs external orchestration                 │
│    (clauty, Companion v0.19.1 web/REST/WS bridge)                    │
│    └─ Layered band-aids around a missing primitive                   │
│                                                                      │
│  State persistence across sessions is filesystem-only                │
│    └─ No native session-tree control                                 │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### How pi-mono surpasses each limit

```
              ┌───────────────────────────────┐
              │    Claude Code (today)        │
              │                               │
              │  Skills + Subagents +         │
              │  MCP tools + Hooks            │
              └────────────────┬──────────────┘
                               │
                          replaced by
                               │
                               ▼
              ┌───────────────────────────────┐
              │      pi-mono (planned)        │
              │                               │
              │  4 native extension points:   │
              │   • Tools  (LLM-callable,     │
              │              in-process)      │
              │   • Skills (on-demand KB)     │
              │   • Prompt Templates          │
              │   • Commands (programmatic    │
              │              session control) │
              │                               │
              │  + Native event handlers      │
              │  + ctx.newSession()           │
              │  + ctx.fork() — parallel      │
              │     debate as forked siblings │
              │  + ctx.navigateTree()         │
              └───────────────────────────────┘
```

| Need | Claude Code (today) | pi-mono (planned) |
|---|---|---|
| Tool implementations | MCP, out-of-process | Native, in-process, zero protocol overhead |
| Knowledge injection | Always-on system prompts | Skills loaded on demand via `/skill:name` |
| Spawn child sessions | External wrapper (clauty/Companion) | `ctx.newSession()` built-in |
| Fork session for parallel debate | Manual orchestration | `ctx.fork()` — Challenger / Defender as forked siblings, Judge merges transcripts |
| Event interception | Hooks-only, command-type only | First-class event handlers |
| Session-tree navigation | Filesystem state | `ctx.navigateTree()` |
| Bundled UX | TUI + slash commands | Editor + commands |

**The non-obvious part: pi-mono doesn't replace AlphaSwarm.sol — it
replaces the parts of Claude Code we were duct-taping around.** The
466-pattern library, BSKG builder, evidence schema, tool adapters,
proof-token contract — all stay. Only the orchestration plane moves.

```
              What stays                      What moves
        ┌───────────────────┐         ┌───────────────────┐
        │ BSKG builder      │         │ Orchestrator      │
        │ Pattern engine    │         │ Subagent spawning │
        │ 466 patterns      │         │ Hook system       │
        │ Tool adapters     │  ───►   │ Skill triggering  │
        │ Evidence schema   │         │ Session branching │
        │ Proof tokens      │         │ Event handling    │
        │ VQL queries       │         │                   │
        │ All of `src/`     │         │                   │
        └───────────────────┘         └───────────────────┘
```

---

## 10 · Self-testing meta-loop

### The premise

Before migrating production from Claude Code → pi-mono, we want
**evidence** that the pi-mono harness produces *equal or better*
audits on the same contracts. Hand-running A/B comparisons is fragile.

### The architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│ Layer 0 — Ground truth                                                │
│  • Damn Vulnerable DeFi (vendored)                                    │
│  • 18 hostile corpus projects (Phase 3.1b output)                     │
│  • 466 patterns with measured precision/recall                        │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │ same test inputs
                  ┌──────────────┴──────────────┐
                  ▼                             ▼
        ┌──────────────────┐           ┌──────────────────┐
        │   Claude Code    │           │     pi-mono      │
        │     (today)      │           │   (candidate)    │
        │                  │           │                  │
        │   /vrs-audit     │           │   /vrs-audit     │
        │   (same skill,   │           │   (same skill,   │
        │    different     │           │    different     │
        │    runtime)      │           │    runtime)      │
        └────────┬─────────┘           └────────┬─────────┘
                 │ evidence packet              │ evidence packet
                 │ + proof tokens               │ + proof tokens
                 │ + transcript                 │ + transcript
                 └──────────────┬───────────────┘
                                ▼
              ┌────────────────────────────────────┐
              │  cmux harness                       │
              │  ─────────────────────────────────  │
              │  • Spawns both runtimes             │
              │  • Isolates contexts (no leakage)   │
              │  • Captures full transcripts        │
              │  • Runs the SAME evaluation         │
              │    contract on both                 │
              └────────────────┬───────────────────┘
                               ▼
              ┌────────────────────────────────────┐
              │  Reasoning Evaluator (Phase 3.1c)  │
              │  ─────────────────────────────────  │
              │  • Dual-Opus scoring                │
              │  • 7-move reasoning decomposition   │
              │  • Graph-Value Scorer (GVS)         │
              │  • Anti-fabrication signals         │
              │  • Capability-then-reasoning gate   │
              │  • Debrief protocol                 │
              └────────────────┬───────────────────┘
                               ▼
              ┌────────────────────────────────────┐
              │  Verdict per contract               │
              │                                     │
              │  Pi ≥ Claude on N contracts         │
              │   → migration phase advances        │
              │                                     │
              │  Pi < Claude on M contracts         │
              │   → blocking issue logged           │
              │   → pi harness improvement loop     │
              │     fires (jj-workspace sandbox)    │
              └────────────────────────────────────┘
```

### Why this is the right move

The **evaluation contract** enforced by the Reasoning Evaluator is
*harness-neutral*. It scores reasoning quality (did the agent query
the graph? did the conclusion follow the evidence? was the debate
substantive?) — not implementation. So **the same evaluator that lets
Claude Code self-improve becomes the qualifier for the pi-mono
migration**.

The product harness validates its own replacement candidate using the
product's own self-testing infrastructure. **The framework that audits
contracts also audits its own runtime.**

### `cmux` (not `tmux`)

`cmux` is the test multiplexer that drives both runtimes in isolated
contexts and captures transcripts deterministically. (Unlike tmux,
which is a generic terminal multiplexer with no awareness of agent
session state.)

> **Note on scope:** the pi-mono migration is a planned next milestone,
> not yet documented in `.planning/`. The current documented migration
> path is Agent Teams + Companion v0.19.1 (see
> `.planning/research/agent-teams-migration/`). The pi-mono direction
> is a more ambitious follow-on once the Agent Teams self-testing
> infrastructure proves the meta-loop pattern.

---

## 11 · Roadmap

```
v5.0 — Theoretical infrastructure          ✅  CLOSED
       (276/288 plans done, product didn't work)

v6.0 — From Theory to Reality              🚧  IN PROGRESS
       Nothing ships until proven
       │
       ├── Phases 1, 1.1, 2, 2.1           ✅  Triage + reviews
       ├── Phase 3.1, 3.1.1, 3.1b          ✅  Testing audit + harness
       ├── Phase 3.1c (family)             🟡  Reasoning evaluation framework
       │     ├── 3.1c.1                    ✅  CLI + graph isolation
       │     ├── 3.1c.2                    ✅  Agent harness hardening
       │     └── 3.1c.3                    ⏳  Evaluation intelligence
       ├── Phase 3.1d, 3.1e                ✅  Feedback bridge + empirical sprint
       ├── Phase 3.1f                      ⏳  Proven loop closure
       ├── Phase 3.2                       ⏳  First working audit ◄── KEY MILESTONE
       ├── Phase 4                         ⏳  Agent Teams debate
       ├── Phase 4.1                       ⏳  Workflow test expansion
       ├── Phase 6                         ⏳  Test framework overhaul
       ├── Phase 7                         ⏳  Documentation honesty + hooks
       ├── Phase 5                         ⏳  Benchmark reality
       └── Phase 8                         ⏳  Ship what works

v7.0 — Pi-mono harness migration           🔵  NOT YET PLANNED
       (Your verbal direction — needs scoping
        as a milestone after v6.0)
```

Full machine-readable: [`.planning/ROADMAP.md`](.planning/ROADMAP.md)
· State: [`.planning/STATE.md`](.planning/STATE.md)

---

## 12 · Repository layout

```
alphaswarm-sol/
├── README.md                  ← you are here
├── CLAUDE.md                  ← session contract for working in this repo
│
├── docs/                      ← architectural docs
│   ├── PHILOSOPHY.md          ← vision + execution model + 9-stage pipeline
│   ├── architecture.md        ← system components + modules
│   ├── LIMITATIONS.md         ← what this CANNOT do (honest)
│   ├── claude-code-architecture.md
│   ├── DOC-INDEX.md
│   ├── getting-started/
│   ├── guides/                ← patterns, skills, testing, vulndocs guides
│   ├── reference/             ← API + tool adapters + agent catalog
│   └── workflows/             ← 9-stage pipeline detail per stage
│
├── src/alphaswarm_sol/        ← Python source (~260K LOC)
│   ├── kg/builder/            ← BSKG construction from Slither (~9.5K LOC)
│   ├── orchestration/         ← Pools, debate, routing (~6.4K LOC)
│   ├── tools/                 ← 7 external tool adapters (~12K LOC)
│   ├── context/               ← Protocol context packs (~6K LOC)
│   ├── labels/                ← Semantic labeling (~4K LOC)
│   ├── shipping/              ← Product distribution (skills + agents)
│   ├── agents/catalog.yaml    ← 24 agent definitions
│   └── skills/registry.yaml   ← 34 skill definitions
│
├── vulndocs/                  ← 466 active patterns, 18 categories
│
├── .planning/                 ← 22 phase folders, ROADMAP, STATE
│   ├── ROADMAP.md             ← v6.0 phase plan
│   ├── STATE.md               ← current position, blockers
│   ├── PHILOSOPHY.md          ← (mirror)
│   ├── phases/                ← per-phase context, plans, gates
│   ├── milestones/            ← milestone closure docs
│   ├── new-milestone/         ← v6.0 prep
│   ├── research/              ← upstream research notes
│   └── testing/               ← canonical testing rules + governance
│
├── tests/                     ← 11,282 tests (many mock-heavy)
├── examples/                  ← DVDeFi + adversarial corpus
├── .claude/                   ← skills + agents + hooks (dev surface)
├── .github/workflows/         ← CI (validate, benchmark, docs, …)
└── docker-compose.yml         ← Neo4j + supporting services
```

---

## 13 · License & honest note

**License:** MIT.

**Honest note to readers landing here from a portfolio link:**

This repo is a **research artifact and an in-progress build**. The
architecture is genuinely designed; substantial scaffolding exists; the
end-to-end auditor does not yet run. If you're evaluating it as a tool,
don't — use Slither directly today. If you're evaluating it as a design
study in:

- multi-agent orchestration on top of LLM harnesses
- behavior-based vs name-based vulnerability detection
- governed pattern lifecycles
- self-testing as a tier of the testing pyramid
- the case for owning your harness instead of renting it

…then the documentation under `docs/` and `.planning/` is the substance.
Start with [`docs/PHILOSOPHY.md`](docs/PHILOSOPHY.md), then
[`docs/LIMITATIONS.md`](docs/LIMITATIONS.md), then
[`.planning/ROADMAP.md`](.planning/ROADMAP.md).

Issues, critiques, adversarial review welcome. Especially adversarial.
