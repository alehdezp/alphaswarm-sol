# AlphaSwarm.sol

Smart-contract security framework built around a behavioral knowledge
graph and role-locked agent debate. It audits Solidity code and produces
findings whose every claim resolves to specific graph nodes and a full
debate transcript.

## For non-technical readers

Smart contracts hold large amounts of money and bugs in them are
effectively irreversible. Two kinds of tool exist today: static
analyzers that only catch simple syntax patterns, and LLM-based auditors
that reason more broadly but fabricate evidence. This project takes a
different approach. It first builds a structured map of what each
function actually does — not what it is named — and then has three AI
agents in different roles argue every suspicious finding using evidence
from that map. A fourth role arbitrates. Unfounded claims are rejected
by the system, not filtered afterwards.

The project is under active development. The end-to-end audit pipeline
is not yet proven on real benchmarks; see
[`docs/LIMITATIONS.md`](docs/LIMITATIONS.md).

## The knowledge graph — BSKG

The Behavioral Security Knowledge Graph is the substrate every other
layer queries. It is not a vector index over source and not a plain call
graph. It is a typed graph whose nodes carry around 200 security-relevant
properties each, derived by fusing outputs from:

- Slither IR (AST, CFG, dataflow)
- Mythril (symbolic traces, reachable paths)
- Aderyn (Rust-based static diagnostics)
- Foundry / Halmos (formal verification results)
- Solodit (historical vulnerability findings)

Each function node carries:
- Semantic operations (20 defined — e.g. `TRANSFERS_VALUE_OUT`,
  `READS_USER_BALANCE`, `CHECKS_PERMISSION`, `MODIFIES_CRITICAL_STATE`)
- A behavioral signature — a compact opcode sequence over those
  operations describing execution order
- Dominator information — which guards control which paths to a sink
- Taint flow — where attacker-controllable data reaches
- Cross-contract edges — calls, inheritance, delegatecall, proxy
- Deterministic IDs (SHA-256 of node properties) so evidence references
  stay stable across builds

Queries run in VQL (Vulnerability Query Language) as graph traversals,
not similarity search. Every finding's evidence is a specific set of
node IDs and edge traversals that can be resolved back to source at a
given build hash.

## Behavioral signatures

Each function compiles to a compact sequence over the operations
vocabulary. Patterns match the sequence, not the source.

```
function withdraw(uint a) {              function process(uint a) {
    require(bal[msg.sender] >= a);           if (bal[msg.sender] < a)
    payable(msg.sender).transfer(a);             revert();
    bal[msg.sender] -= a;                    payable(msg.sender).send(a);
}                                            bal[msg.sender] -= a;
                                         }
        ╲                                ╱
         ╲ R:bal -> X:out -> W:bal ◄─── same signature
          ╲   (CEI inverted)              guard dominance: NONE
```

Queries are path-qualified (always-before vs sometimes-before vs
never-before), dominance-aware (guard dominates sink vs bypassable),
and taint-aware (sink reachable from attacker-controllable source).
These distinctions come from the project's own
[`docs/PITFALLS.md`](docs/PITFALLS.md) and are what separates a true
positive from a false negative.

## Role-locked agent debate

Each candidate finding goes through three role-locked agents with
different models:

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
│ graph nodes.  │                  │ vulnerable    │
│               │                  │ path.         │
└──────┬────────┘                  └────────┬──────┘
       └─────────────┬───────────────────────┘
                     ▼
              ┌──────────────┐
              │   VERIFIER   │      ┌──────────────────┐
              │    (Opus)    │ ───► │ confirmed │      │
              │ Reads both   │      │ likely    │      │
              │ transcripts. │      │ uncertain │      │
              │ Confidence.  │      │ rejected  │      │
              └──────────────┘      └──────────────────┘
```

The protocol is inspired by iMAD (Fan et al., 2025) and is documented
in the project's paper draft (`docs/.archive/paper/`). `inconclusive`
verdicts route back to retrieval, never to a coin flip. Rejected
findings are retained for pattern curation.

## Pattern catalog and tiering

The catalog holds 466 active patterns across 18 vulnerability categories
(39 archived, 57 quarantined). Patterns carry a status determined by
measured precision and recall on real contracts:

| Status | Precision | Recall |
|---|---|---|
| draft | < 70% | < 50% |
| ready | ≥ 70% | ≥ 50% |
| excellent | ≥ 90% | ≥ 85% |

Three detection tiers, in order of cost:
- **Tier A** — deterministic graph-only queries (no LLM call)
- **Tier B** — LLM-verified, for logic bugs that require reasoning over
  graph context
- **Tier C** — label-dependent, requires upstream semantic role labeling

Triage rules (active / archived / quarantined) live in
[`docs/guides/patterns-basics.md`](docs/guides/patterns-basics.md).

## Why target Solidity specifically

- Losses are irreversible — no patch-and-redeploy after an exploit.
- Contracts are short in code but long in composition; most serious
  bugs appear at interaction boundaries between contracts, not inside
  a single one.
- Function names in DeFi are near-universal (every protocol has
  `withdraw`, `swap`, `claim`); security properties live in behavior
  and ordering, not naming.
- Attack viability depends on economic context (oracle depth, flash-loan
  liquidity, governance token distribution), not on code alone.

A graph model captures composition, ordering, and dataflow. An operation
vocabulary captures behavior independent of naming. A protocol-context
layer supplies the economic dimension. None of the three alone is
enough.

## The harness — Pi-mono

Production orchestration is moving to the Pi-mono coding-agent package
(`@mariozechner/pi-coding-agent`,
[GitHub](https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent)).
Implementation specifics are not fully settled; the direction is
committed, the shape is being worked out. Relevant Pi primitives:

- **Native tool registration** via `pi.registerTool`. BSKG queries,
  Slither / Mythril / Aderyn / Halmos adapters, pattern matcher,
  evidence builder, proof-token issuer, and `/web-research` all become
  first-class in-process tools. No MCP boundary.
- **Per-agent tool scoping.** Pi ships no permission popup system;
  scoping is composed from `pi.setActiveTools`, `allowed-tools` in skill
  frontmatter, and `tool_call` event handlers that can return
  `{block: true, reason}`. Each agent definition can be given a distinct
  tool set, file-write scope, and command allow-list.
- **Session control.** `ctx.newSession({parentSession, setup})`,
  `ctx.fork(entryId)`, `ctx.navigateTree`, `ctx.waitForIdle`. Challenger
  and Defender can be spawned as sibling forks; the Verifier reads both.
- **Middleware hooks.** `before_provider_request` can rewrite the system
  prompt per call (per-agent prompt surgery); `tool_result` middleware
  post-processes raw tool output; `session_before_compact` can gate long
  audits.
- **Cross-session messaging** through the event bus and injected
  messages (`pi.sendMessage`, `pi.sendUserMessage` with
  `deliverAs: "steer" | "followUp" | "nextTurn"`).
- **RPC mode** — stdin/stdout JSONL, LF-delimited. Lets an outer harness
  drive Pi sessions programmatically without a network surface.

Pi's explicit non-goals (from its README): no MCP, no sub-agents, no
permission popups, no plan mode, no background bash. Each absence is
something this project builds as an extension or deliberately leaves
out.

## Multiple orchestrators

The architecture is not a single Pi session running audits. It assumes
several orchestrators, each a Pi session with a distinct system prompt,
tool scope, and termination condition:

- **Audit orchestrator** — runs the 9-stage pipeline on a target contract
- **Dataset-population orchestrator** — mines real contracts, extracts
  ground-truth labels, grows the corpus
- **Dataset-improvement orchestrator** — re-labels low-confidence
  entries, rebalances coverage, detects drift
- **Static-checker orchestrator** — runs Slither / Aderyn / Mythril /
  Halmos against the corpus on a schedule and normalizes outputs
- **Work-unit orchestrator** — splits long audits into trackable
  subtasks (beads) and coordinates recovery across sessions
- **Testing orchestrator** — drives the self-testing meta-loop below

Orchestrators are Pi extensions, not hardcoded flows in a monolithic
runtime.

## Claude Code's role

Claude Code is not the production runtime under the new direction. It
is kept for three dev-time responsibilities:

1. **IDE-level assistance** for writing and maintaining Pi agent
   definitions, skills, prompts, and tool adapters.
2. **Driving the self-testing meta-loop** during development: running
   the current Pi orchestrator and any prior Claude-Code orchestrator
   against the same corpus under identical conditions, capturing both
   transcripts.
3. **Quality assessment** of Pi audit outputs. The Reasoning Evaluator
   runs under Claude Code and scores Pi runs — dual-Opus scoring,
   7-move reasoning decomposition (HYPOTHESIS_FORMATION, QUERY_
   FORMULATION, RESULT_INTERPRETATION, EVIDENCE_INTEGRATION,
   CONTRADICTION_HANDLING, CONCLUSION_SYNTHESIS, SELF_CRITIQUE),
   Graph-Value Scorer distinguishing checkbox use from genuine use,
   and anti-fabrication signals.

## Read further

- [`docs/PHILOSOPHY.md`](docs/PHILOSOPHY.md) — system philosophy and 9-stage pipeline
- [`docs/architecture.md`](docs/architecture.md) — modules and data flow
- [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) — explicit limits
- [`docs/PITFALLS.md`](docs/PITFALLS.md) — domain pitfalls
- [`.planning/ROADMAP.md`](.planning/ROADMAP.md) — phase plan
- [`vulndocs/`](vulndocs/) — pattern catalog (18 categories)
- [`src/alphaswarm_sol/`](src/alphaswarm_sol/) — implementation
- Pi-mono coding-agent: https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent

License: MIT.
