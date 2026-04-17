# AlphaSwarm.sol

**A case study in Claude Code agent orchestration, graph-grounded security reasoning, and self-testing AI workflows.**

AlphaSwarm.sol is not presented here as a finished audit product. It is a research-engineering project about a harder question:

> How do you coordinate multiple coding agents so they can investigate a real security problem, disagree with each other, cite durable evidence, and then test whether their own reasoning was any good?

Solidity security is the domain. The deeper case study is agent orchestration.

The project combines three ideas:

1. **A Behavioral Security Knowledge Graph (BSKG)** that gives agents a shared evidence substrate.
2. **Claude Code skills and role-scoped agents** that split an audit into attacker, defender, verifier, reviewer, tool, and evaluation responsibilities.
3. **A self-testing harness** that treats agent behavior itself as something to observe, score, replay, and improve.

The current principle is strict: **nothing ships until proven**. The repository contains substantial implemented infrastructure, many designed workflows, and some intentionally unfinished pieces. The point of this README is to make the ideas understandable without pretending the system is already a benchmark-proven auditor.

## Honest Status

| Area | Current state |
|---|---|
| BSKG graph builder | Implemented; builds Solidity behavior graphs from Slither-derived analysis |
| Semantic operations | Implemented; 20 operation types for behavior-level reasoning |
| VulnDocs pattern catalog | Implemented; 466 active YAML patterns across 18 categories |
| Claude Code skills and agent definitions | Implemented as workflow specs; 51 skills and 24 agent definitions |
| `/vrs-audit` end-to-end pipeline | Partial; not yet proven on real benchmark runs |
| Multi-agent debate | Designed and partially implemented; not yet proven end-to-end on real audit candidates |
| Benchmarks | Not claimed; precision, recall, and F1 are intentionally unknown |
| Evaluation intelligence layer | In progress; Tier 1 exists, Tier 2 modules are planned/partial |

Authoritative state: [`.planning/STATE.md`](.planning/STATE.md).
Known limits and non-goals: [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md).

## What Makes This A Case Study

Most agent demos are linear:

```text
prompt -> agent -> tool calls -> answer
```

AlphaSwarm.sol explores a more difficult shape:

```text
contract code
  -> graph build
  -> pattern candidates
  -> task/bead creation
  -> attacker investigation
  -> defender challenge
  -> verifier arbitration
  -> evidence-linked report
  -> transcript capture
  -> reasoning evaluation
  -> planning feedback
```

That makes it useful as a study of:

- how to give agents a shared memory that is not just chat history,
- how to prevent role drift between specialized agents,
- how to make AI security claims traceable to code and graph evidence,
- how to persist long-running investigations across context resets,
- how to test workflows where "correctness" includes reasoning quality,
- how to design feedback loops without pretending they are autonomous magic.

## The Central Problem

LLMs can reason about code, but they are unreliable witnesses. They can miss details, overfit to function names, fabricate evidence, or agree with each other for the wrong reasons.

The project asks: what infrastructure would make agents more useful and more auditable?

The answer being explored is:

```text
agent reasoning must be grounded in a graph,
claims must resolve to evidence packets,
agents must challenge each other in separate roles,
and the whole workflow must be tested from transcripts.
```

Solidity is a strong domain for this because small code paths can hold huge value, function names are often misleading, and many bugs depend on behavior ordering rather than syntax.

## BSKG: The Shared Evidence Substrate

The Behavioral Security Knowledge Graph is the object all security agents are supposed to query before reaching conclusions.

It is not a vector database over Solidity files. It is a typed graph of what the contract does:

| Graph concept | Why agents need it |
|---|---|
| Semantic operations | Lets agents reason about behavior instead of names |
| Behavioral signatures | Encodes ordering such as read balance -> external call -> write balance |
| Call and inheritance edges | Supports cross-function and cross-contract reasoning |
| Guard and dominance hints | Separates "guard exists" from "guard actually controls the dangerous path" |
| Taint and source/sink hints | Tracks attacker-controlled data toward sensitive operations |
| Deterministic node IDs | Makes evidence stable across transcripts and reports |

The goal is not only detection. The BSKG gives independent agents a common language. An attacker, defender, and verifier can disagree while pointing at the same underlying graph nodes.

## Behavior Over Names

Traditional checks often depend too much on source shape or naming. AlphaSwarm.sol tries to capture security behavior directly.

```solidity
function withdraw(uint256 amount) external {
    require(balance[msg.sender] >= amount);
    payable(msg.sender).call{value: amount}("");
    balance[msg.sender] -= amount;
}

function processPayment(uint256 amount) external {
    if (balance[msg.sender] < amount) revert();
    payable(msg.sender).call{value: amount}("");
    balance[msg.sender] -= amount;
}
```

Both functions have the same dangerous ordering:

```text
R:bal -> X:out -> W:bal
read balance -> external value transfer -> write balance
```

The function name is not the evidence. The operation sequence is.

## Agent Orchestration Model

The product direction is not "one agent scans a repo." It is an orchestrated workflow where Claude Code is guided by skills, calls CLI tools, creates work items, and spawns role-scoped agents.

```text
User request
  |
  v
Claude Code skill, for example /vrs-audit
  |
  +-- Preflight: settings, tools, state
  +-- Build graph: alphaswarm build-kg
  +-- Detect candidates: VulnDocs patterns over BSKG
  +-- Create beads: one investigation unit per candidate
  +-- Spawn agents:
  |     attacker -> exploit path
  |     defender -> guards and mitigations
  |     verifier -> evidence arbitration
  |     reviewer -> adversarial quality check
  +-- Persist:
  |     pools, beads, evidence packets, transcripts
  +-- Evaluate:
        graph usage, reasoning moves, missing evidence, drift
```

The CLI is subordinate tooling. It exists so the orchestrator and agents can build graphs, query evidence, run static analyzers, and validate patterns. The interesting layer is the coordination contract around those calls.

## Role Design

The agent catalog is not just a list of prompts. It is an attempt to encode separation of concerns.

| Role | Question it answers | Evidence expectation |
|---|---|---|
| Attacker | "How could this be exploited?" | exploit path, preconditions, graph nodes |
| Defender | "What prevents or limits this?" | guards, dominance, invariants, mitigations |
| Verifier | "Which side is better supported?" | cross-checked evidence and confidence |
| Secure reviewer | "What is weak, missing, or fabricated?" | gaps, known unknowns, rejected claims |
| Pattern agents | "Which behavioral patterns explain this?" | matched operations and pattern IDs |
| Tool agents | "What do Slither, Aderyn, Mythril, etc. add?" | normalized external findings |
| Evaluation agents | "Did the workflow reason correctly?" | transcript and observation scores |

The research question is how much of this role discipline can be enforced with prompts, skills, tool permissions, hooks, transcripts, and evidence schemas.

## Beads, Pools, And Long-Running Work

Security audits are not one-shot answers. AlphaSwarm.sol models investigations as persistent units:

- **Beads** are candidate findings with status, scope, evidence, questions, and verdicts.
- **Pools** are collections of beads for a full audit session.
- **Evidence packets** store the graph nodes, code locations, traces, and agent claims that support or reject a finding.
- **Proof tokens** are planned/partial artifacts showing that important workflow stages actually happened.

This is one of the most useful orchestration ideas in the repo: make agent work resumable and inspectable instead of letting it vanish into a chat transcript.

## Self-Testing Harness

The testing system is not only checking Python functions. Its purpose is to evaluate the agent workflow itself.

The target loop is:

```text
run scenario
  -> capture transcript and tool events
  -> extract graph queries and evidence references
  -> score reasoning quality
  -> detect missing or fake evidence
  -> compare against expected behavior
  -> generate recommendations or planning tasks
```

This is why the `.planning/testing` work matters. It treats an agent run as an observable system, not as a black box.

## Reasoning Evaluation Ideas

The planned and partial evaluation framework decomposes agent behavior into moves:

| Reasoning move | What the harness should notice |
|---|---|
| Hypothesis formation | Did the agent state plausible security hypotheses? |
| Query formulation | Did it ask the BSKG the right questions? |
| Result interpretation | Did it understand what graph results mean? |
| Evidence integration | Did it connect graph evidence to code and exploitability? |
| Contradiction handling | Did it respond to defender/verifier disagreement? |
| Conclusion synthesis | Did the final verdict follow from evidence? |
| Self-critique | Did it identify uncertainty and missing context? |

The novel part is not simply "LLM grades LLM." The goal is structured evaluation tied to graph usage, transcript markers, scenario manifests, and evidence contracts.

## Tier 2 Evaluation Intelligence

The pending Tier 2 layer is the most experimental part of the project. It asks whether a harness can diagnose its own blind spots.

| Module | Research purpose | Status |
|---|---|---|
| Coverage radar | Find cold areas across vuln class, semantic op, reasoning skill, and query pattern | Partial |
| Contract healer | Detect stale, trivial, or ambiguous evaluation contracts | Partial |
| Tier manager | Increase evaluation rigor when workflows degrade | Partial |
| Reasoning decomposer | Score reasoning moves independently | Planned |
| Scenario synthesizer | Draft new scenarios from untested skill and agent claims | Planned |
| Counterfactual replayer | Record tool trajectories for "what changed?" analysis | Planned |
| Fingerprinter | Detect behavioral drift across repeated runs | Planned/stub |
| Graph diagnostics | Explain why graph queries or patterns fail | Planned |
| Recommendation engine | Map observed failures to concrete fixes | Planned |
| Planning bridge | Turn test gaps into GSD phase or plan actions | Planned |
| Hotfix protocol | Separate tiny safe fixes from deeper design work | Planned |

This is not advertised as complete. It is valuable because it documents the design pressure of building self-improving agent systems without hand-waving away validation.

## Solidity-Specific Value

The orchestration study is domain-general, but Solidity makes the graph grounding meaningful.

Smart contract bugs often depend on:

- operation ordering, such as external call before balance update,
- missing or bypassable access checks,
- cross-function state transitions,
- proxy and delegatecall behavior,
- oracle reads and stale assumptions,
- economic context that is not visible in one function,
- safe-looking code that becomes dangerous through composition.

The BSKG is meant to give agents a compact, queryable view of those behaviors. The agent system is meant to debate what the graph means.

## What Is Actually Interesting To Study

This repo is useful if you care about:

- Claude Code as an orchestrator rather than just an assistant,
- skill files as executable workflow contracts,
- role-scoped agents with different evidence requirements,
- graph-first reasoning as a guardrail against hallucination,
- persistent work units for long-running agent tasks,
- transcript markers and hooks as audit logs for agent behavior,
- adversarial debate as a verification protocol,
- testing agent reasoning instead of only testing code,
- planning systems that react to evaluation failures.

That is the research contribution: not a claim that the scanner is done, but a concrete design space for building agent systems that can be inspected, challenged, and improved.

## Current Numbers

These are engineering inventory, not product-performance claims.

| Metric | Value |
|---|---:|
| Python source files | ~475 |
| Production code | ~260k LOC |
| Active VulnDocs patterns | 466 |
| Archived patterns | 39 |
| Quarantined patterns | 57 |
| Semantic operations | 20 |
| Agent definitions | 24 |
| Skill definitions | 51 |
| Test files | 245 |
| Tests | 11k+ |

The test count is not a quality claim. A major roadmap theme is replacing mock-heavy checks with live, evidence-producing validation.

## Maturity Model

| Label | Meaning |
|---|---|
| Proven | Demonstrated on real inputs with reproducible evidence |
| Implemented | Code exists and local tests or spot checks support it |
| Designed | Documented in architecture/planning, not yet implemented |
| Unknown | Requires benchmark or live evaluation before making claims |

| Capability | Maturity |
|---|---|
| Build behavioral graph | Implemented |
| Load active pattern catalog | Implemented |
| Query graph for security-relevant behavior | Implemented/partial |
| Persist beads, pools, and evidence schemas | Implemented/partial |
| Produce a full audit report from `/vrs-audit` | Unknown |
| Prove graph reasoning improves LLM audit quality | Unknown |
| Run attacker/defender/verifier debate on real candidates | Designed/partial |
| Benchmark against SmartBugs or DVDeFi | Unknown |
| Self-diagnostic evaluation loop | Designed/partial |

## Roadmap

The v6.0 milestone is named **From Theory to Reality**. Its purpose is to collapse the distance between impressive architecture and proven behavior.

Current critical path:

```text
3.1c   Reasoning evaluation framework
3.1c.3 Evaluation intelligence bootstrap
3.1f   Proven loop closure
3.2    First working audit
4      Agent Teams debate
5      Benchmark reality
8      Ship what works
```

The most important exit gate is not a prettier demo. It is one complete audit on a real contract with graph evidence, transcript evidence, agent disagreement, verifier arbitration, and human-reviewable findings.

## Repository Guide

| Path | Purpose |
|---|---|
| [`docs/PHILOSOPHY.md`](docs/PHILOSOPHY.md) | Vision, execution model, 9-stage pipeline |
| [`docs/architecture.md`](docs/architecture.md) | System architecture and module map |
| [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) | Honest constraints and non-goals |
| [`docs/DOC-INDEX.md`](docs/DOC-INDEX.md) | Progressive documentation index |
| [`.planning/STATE.md`](.planning/STATE.md) | Current project state and phase progress |
| [`.planning/ROADMAP.md`](.planning/ROADMAP.md) | v6.0 roadmap |
| [`.planning/testing/`](.planning/testing/) | Testing philosophy, rules, scenario contracts |
| [`.planning/phases/3.1c.3-evaluation-intelligence-bootstrap/3.1c.3-CONTEXT.md`](.planning/phases/3.1c.3-evaluation-intelligence-bootstrap/3.1c.3-CONTEXT.md) | Evaluation intelligence plan |
| [`src/alphaswarm_sol/`](src/alphaswarm_sol/) | Main implementation |
| [`src/alphaswarm_sol/agents/catalog.yaml`](src/alphaswarm_sol/agents/catalog.yaml) | Canonical agent catalog |
| [`src/alphaswarm_sol/skills/registry.yaml`](src/alphaswarm_sol/skills/registry.yaml) | Canonical skill registry |
| [`vulndocs/`](vulndocs/) | Vulnerability pattern catalog |

## Developer Commands

These commands are useful for development and inspection. They are not a claim that the full product workflow is complete.

```bash
# Build the behavioral graph
uv run alphaswarm build-kg contracts/

# Query the graph
uv run alphaswarm query "functions without access control"

# Validate the pattern catalog
uv run alphaswarm vulndocs validate vulndocs/

# Check external tool integrations
uv run alphaswarm tools status

# Run targeted tests
uv run pytest tests/workflow_harness -q
```

Project policy prefers targeted tests for localized changes. Full-suite runs are reserved for cross-cutting changes, release checks, or explicit requests.

## What This Is Not

AlphaSwarm.sol is not:

- a finished audit product,
- a benchmark-proven detector,
- a replacement for human auditors,
- a guarantee of contract safety,
- an autonomous security oracle,
- a scanner whose output should be trusted blindly.

It is a serious case study in building graph-grounded, role-separated, self-observing agent workflows for a domain where evidence quality matters.

## License

MIT.
