# AlphaSwarm.sol

A behavioral, multi-expert, self-testing security framework for Solidity.

It rejects three premises most 2026 audit tools accept: that names mean
things, that one model can judge its own work, and that your agent
harness is somebody else's problem.

## The bets

1. **Behavior beats names.** Detection runs on operation signatures, not identifiers.
2. **Evidence beats assertion.** Findings without graph + location + transcript are structurally rejected.
3. **Disagreement beats consensus.** Tool conflicts and agent dissent route to a verifier — they are signal.
4. **Model divergence beats LLM-as-judge.** Three roles, three model families, role-locked prompts.
5. **Lessons graduate to rules.** Recurring debate outcomes become deterministic Cypher queries in the graph.
6. **The harness is replaceable.** Audit logic is harness-neutral; the same evaluator qualifies the replacement.

## The graph — BSKG

The Behavioral Security Knowledge Graph is not a RAG index over Solidity
source. It is a typed, queryable model of what each function *does*,
fused from multiple analyzers.

```
Slither IR · Mythril traces · Aderyn · Foundry/Halmos · Solodit
                              │
                              ▼
                  ┌──────────────────────────┐
                  │  BSKG                    │
                  │  Functions × ~200 props  │
                  │  Operations · Signatures │
                  │  Dominators · Taint flow │
                  │  Cross-contract edges    │
                  └──────────────────────────┘
```

GraphRAG over source gives you adjacency. The BSKG gives you *semantic
ordering* — what runs before what, under what guard, with what data
flowing in. Every downstream claim resolves to a node ID, a code
location, and a build hash.

## The query language — behavioral signatures

Every function compiles to a compact opcode sequence over semantic
operations. Patterns query the sequence, not the source.

```
R:bal   READS_USER_BALANCE          X:out   CALLS_EXTERNAL
W:bal   WRITES_USER_BALANCE         X:un    CALLS_UNTRUSTED
C:auth  CHECKS_PERMISSION           M:crit  MODIFIES_CRITICAL_STATE
                                                        (40+ ops total)
```

Two functions, identical signatures, no name-based tool can tell them
apart:

```
function withdraw(uint a) {              function process(uint a) {
    require(bal[msg.sender] >= a);           if (bal[msg.sender] < a)
    payable(msg.sender).transfer(a);             revert();
    bal[msg.sender] -= a;                    payable(msg.sender).send(a);
}                                            bal[msg.sender] -= a;
                                         }
        ╲                                ╱
         ╲ R:bal -> X:out -> W:bal ◄─── reentrancy candidate
          ╲   (CEI inverted)              guard dominance: NONE
```

The query language is **path-qualified, dominance-aware, and taint-aware**.
It distinguishes "guard exists" from "guard dominates every path to the
sink". That distinction is the difference between a true positive and a
false negative.

## The experts — role-locked, model-divergent debate

```
                  Candidate finding
                          │
        ┌─────────────────┴─────────────────┐
        ▼                                   ▼
┌───────────────┐                  ┌───────────────┐
│   ATTACKER    │  ◄── debate ──►  │   DEFENDER    │
│    (Opus)     │  graph evidence  │    (Sonnet)   │
│ Build exploit │                  │ Prove guard   │
│ path. Cite    │                  │ DOMINATES the │
│ graph nodes.  │                  │ path — not    │
│               │                  │ just exists.  │
└──────┬────────┘                  └────────┬──────┘
       └─────────────┬───────────────────────┘
                     ▼
              ┌──────────────┐
              │   VERIFIER   │      ┌──────────────────┐
              │    (Opus)    │ ───► │ confirmed │      │
              │ Both         │      │ likely    │      │
              │ transcripts. │      │ uncertain │      │
              │ Confidence.  │      │ rejected  │      │
              └──────────────┘      └──────────────────┘
```

Inter-model adversarial debate (iMAD-style, 2025) hardened with two
non-standard constraints: (a) the Defender must prove *guard dominance*,
not just guard presence; (b) `inconclusive` verdicts route back to
retrieval, never to a coin flip. **Rejected findings feed the Pattern
Miner.** Wrong is signal too.

## The pattern lifecycle — lessons graduate to rules

```
   Cluster findings (HDBSCAN) ──► Extract pattern (LLM → VQL)
   ──► Validate on held-out set (P ≥ 0.8, R ≥ 0.5)
   ──► Promote to KG as deterministic Cypher rule

   Observed → Framed → Usable → Trusted → Governed
```

Most agent systems remember lessons as fuzzy embeddings retrieved at
inference. Here, patterns are first-class, versioned, scored, and
governed. A pattern starts as a recurring debate outcome and ends as a
Cypher rule the Scanner matches without an LLM call. **Knowledge
graduates** — closer to how compliance tracks regulations than to how
RAG stores embeddings.

## The orchestration — audit logic outlives the harness

```
   Surface 1 ──►  Claude Code as orchestrator
                   (skills · subagents · hooks · Bash → CLI)
                       │
                       │  structural limits: subagents can't nest,
                       │  MCP latency per tool, skills are prompts
                       │  not programs, hooks block via exit code,
                       │  no native session-tree control
                       ▼
   Surface 2 ──►  pi-mono as harness
                   ctx.fork() (Challenger + Defender as parallel
                   siblings) · ctx.newSession() · native in-process
                   tools · first-class event handlers · skills on demand
```

The audit logic does not change between Surface 1 and Surface 2 — only
the runtime does. Most agent frameworks do not make this bet: **own your
orchestration primitives** so debate, fork, and evidence capture are not
external scaffolding. When the next harness comes, the audit logic moves
with it.

## The meta-loop — the framework qualifies its own runtime

```
   Same corpus (DVDeFi + adversarial fixtures)
            │
   ┌────────┴────────┐
   ▼                 ▼
Claude Code        pi-mono       ◄── two harnesses, one audit logic
   │                 │
   └────────┬────────┘
            ▼
   cmux (isolated contexts, no leak, full transcripts)
            ▼
   Reasoning Evaluator
     • dual-Opus (>15pt disagreement = unreliable)
     • 7-move reasoning breakdown, scored independently
     • Graph-Value Scorer (checkbox <30 vs genuine >70)
     • anti-fabrication signals (perfect score, identical
       output, sub-5s duration)
            ▼
   Pi ≥ Claude → migrate
   Pi <  Claude → improve, re-test
```

Self-testing is not a feature on top of the testing pyramid. **It is a
tier of the pyramid.** The product harness qualifies its own replacement
candidate using the product's own evaluation infrastructure.

## Why this might be good

The graph is what the agents query. The agents are what the patterns
govern. The patterns are what the evaluator scores. The evaluator is
what qualifies the harness. **Pull any one layer and the chain
collapses.** The contemporary alternative — single-LLM auditor + RAG +
LLM-as-judge — is faster to demonstrate and is also a yes-loop wrapped
in a vector index. The bet here: auditing requires evidence, debate
requires divergence, learning requires governance — and the cost of
building those into the substrate pays back the moment the system has
to defend a finding to a human reviewer.

## Read further

- [`docs/PHILOSOPHY.md`](docs/PHILOSOPHY.md) — execution model and pillars
- [`docs/architecture.md`](docs/architecture.md) — modules and data flow
- [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) — what it does not do
- [`vulndocs/`](vulndocs/) — pattern catalog (18 categories)
- [`src/alphaswarm_sol/`](src/alphaswarm_sol/) — implementation

License: MIT.
