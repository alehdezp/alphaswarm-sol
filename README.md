# AlphaSwarm.sol

**A research-engineering case study in behavioral, evidence-grounded AI security auditing for Solidity.**

AlphaSwarm.sol explores a simple thesis:

> Smart contract security tools should reason about what code does, not what functions are named, and every AI-generated claim should trace back to concrete evidence.

The project is not presented as a finished commercial auditor. It is an actively developed framework and case study with substantial implemented infrastructure, unfinished orchestration, and a deliberately strict roadmap for proving what works before claiming it works.

## Honest Status

| Area | Current state |
|---|---|
| Behavioral Security Knowledge Graph | Implemented; builds rich Solidity graphs from Slither-derived analysis |
| Semantic operations | Implemented; 20 behavior-level operations such as value transfer, balance read/write, permission checks |
| Vulnerability pattern catalog | Implemented; 466 active YAML patterns across 18 categories |
| Claude Code skill/agent system | Implemented as workflow definitions; 51 skills and 24 agent definitions in registry/catalog |
| Full `/vrs-audit` pipeline | Partial; the end-to-end audit has not been proven on a real benchmark |
| Multi-agent attacker/defender/verifier debate | Designed and partially implemented; not yet proven end-to-end on real audit output |
| Benchmark claims | None; precision/recall/F1 are intentionally unknown until benchmark phases run |
| Evaluation intelligence engine | In progress; Tier 1 exists, Tier 2 adaptive modules are planned/partial |

The current project principle is: **nothing ships until proven**. The authoritative status lives in [`.planning/STATE.md`](.planning/STATE.md), and limitations are documented in [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md).

## Why This Matters

Most smart contract losses are not caused by the easy bugs static analyzers are best at finding. They come from logic errors, weak authorization, missing invariants, economic assumptions, protocol composition, and strange interactions between functions.

Static analyzers are fast and reproducible, but often shallow. LLMs can reason more broadly, but they hallucinate and are hard to trust. Human auditors can reason deeply, but they are expensive and do not scale.

AlphaSwarm.sol investigates a middle path:

- build a structured graph of contract behavior,
- search it with vulnerability patterns,
- hand suspicious cases to role-scoped AI agents,
- force those agents to cite graph nodes and code locations,
- use adversarial verification before producing a finding,
- test the whole reasoning loop against itself.

The goal is not "replace auditors." The goal is a tool that makes a human auditor faster while making AI claims more falsifiable.

## Core Idea

Names lie. Behavior does not.

Two functions can have different names and the same dangerous behavior:

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

Both reduce to the same behavioral signature:

```text
R:bal -> X:out -> W:bal
read balance -> external value transfer -> write balance
```

That ordering matters more than either function name. AlphaSwarm.sol tries to make those behavioral signatures queryable, testable, and usable by agents.

## What Is Novel Here

### 1. Behavioral Security Knowledge Graph

The BSKG is not a vector index over Solidity source and not a plain call graph. It is a typed graph with security-oriented properties, semantic operations, call edges, taint hints, dominance relationships, and deterministic evidence identifiers.

The intended workflow is:

```text
Solidity source
  -> Slither-derived analysis
  -> behavioral graph
  -> semantic operations
  -> vulnerability patterns
  -> evidence packets
  -> agent verification
```

### 2. Semantic Operations Instead Of Name Matching

Patterns target operations like:

| Category | Examples |
|---|---|
| Value | `TRANSFERS_VALUE_OUT`, `READS_USER_BALANCE`, `WRITES_USER_BALANCE` |
| Access | `CHECKS_PERMISSION`, `MODIFIES_OWNER`, `MODIFIES_ROLES` |
| External interaction | `CALLS_EXTERNAL`, `CALLS_UNTRUSTED`, `READS_EXTERNAL_VALUE` |
| State | `MODIFIES_CRITICAL_STATE`, `READS_ORACLE`, `INITIALIZES_STATE` |

This is the heart of the project: detect the shape of dangerous behavior even when names, layout, and style change.

### 3. Evidence-First Agent Workflows

The agent design is intentionally adversarial:

- **Attacker** constructs exploit paths.
- **Defender** searches for guards, invariants, and mitigations.
- **Verifier** arbitrates using cited evidence.
- **Reviewer** challenges weak or fabricated conclusions.

The target standard is that no finding is accepted just because an LLM says it confidently. A valid finding should cite graph nodes, source locations, operation sequences, and transcript evidence.

### 4. Testing The Reasoning, Not Just The Code

The `.planning/testing` and `3.1c` work treats AI audit quality as something that must be measured directly.

The planned evaluation engine decomposes agent behavior into reasoning moves such as:

- hypothesis formation,
- evidence integration,
- conclusion synthesis,
- query formulation,
- contradiction handling,
- self-critique.

The more interesting idea is not "run tests." It is: **did the agent think correctly, and can the framework detect when it did not?**

### 5. Self-Diagnostic Evaluation Loop

The pending Tier 2 evaluation layer is designed to notice gaps in the testing system itself:

| Module | Purpose | Status |
|---|---|---|
| Coverage radar | Find cold spots across vuln class, semantic op, reasoning skill, graph-query pattern | Partial |
| Contract healer | Detect stale, trivial, or ambiguous evaluation contracts | Partial |
| Tier manager | Increase evaluation rigor when workflows degrade | Partial |
| Reasoning decomposer | Score reasoning moves independently | Planned |
| Scenario synthesizer | Generate draft test scenarios from untested skill/agent claims | Planned |
| Graph diagnostics | Explain why queries or pattern matches failed | Planned |
| Counterfactual replayer | Record trajectories for manual "what if" analysis | Planned |
| Recommendation engine | Map evaluation failures to concrete fixes | Planned |
| Planning bridge | Convert test gaps into GSD planning actions | Planned |
| Hotfix protocol | Classify small safe fixes vs deeper phase work | Planned |

This part is mostly not built yet. It is included because it is one of the most important research directions in the repository.

## Architecture At A Glance

```text
User
  |
  v
Claude Code workflow / VRS skill
  |
  +--> alphaswarm build-kg
  |      |
  |      v
  |   Behavioral Security Knowledge Graph
  |
  +--> pattern detection
  |      |
  |      v
  |   candidate findings / beads
  |
  +--> attacker / defender / verifier agents
         |
         v
      verdicts, evidence packets, human review
```

The CLI is not the product interface. It is a tool surface the orchestrator calls. The product direction is a Claude Code-orchestrated workflow using skills, agents, graph queries, and persistent evidence artifacts.

## Current Numbers

These numbers are intentionally conservative and should be treated as engineering inventory, not product claims.

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

The test count is not a quality claim. A major theme of the roadmap is replacing mock-heavy tests with live, evidence-producing validation.

## Maturity Model

| Label | Meaning |
|---|---|
| Proven | Demonstrated on real inputs with reproducible evidence |
| Implemented | Code exists and local tests or spot checks support it |
| Designed | Documented in architecture/planning, not yet implemented |
| Unknown | Requires benchmark or live evaluation before making claims |

Using that model:

| Capability | Maturity |
|---|---|
| Build behavioral graph | Implemented |
| Load active pattern catalog | Implemented |
| Query graph for security-relevant behavior | Implemented/partial |
| Produce a complete audit report from `/vrs-audit` | Unknown |
| Prove graph reasoning improves LLM audit quality | Unknown |
| Run attacker/defender/verifier debate on real candidates | Designed/partial |
| Benchmark against SmartBugs or DVDeFi | Unknown |
| Self-improving evaluation loop | Designed/partial |

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

The most important exit gate is simple: prove one complete audit works end-to-end on a real contract, with evidence, transcript, graph usage, and human-reviewable findings.

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
| [`src/alphaswarm_sol/`](src/alphaswarm_sol/) | Main implementation |
| [`src/alphaswarm_sol/agents/catalog.yaml`](src/alphaswarm_sol/agents/catalog.yaml) | Canonical agent catalog |
| [`src/alphaswarm_sol/skills/registry.yaml`](src/alphaswarm_sol/skills/registry.yaml) | Canonical skill registry |
| [`vulndocs/`](vulndocs/) | Vulnerability pattern catalog |

## Developer Commands

The commands below are useful for development and inspection. They are not a claim that the full product workflow is complete.

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
- a guarantee of contract safety,
- a replacement for human auditors,
- a benchmark-proven superior detector,
- an autonomous security oracle,
- a scanner whose output should be trusted blindly.

The honest ambition is narrower and stronger: make AI-assisted security review more behavioral, more evidence-grounded, more adversarial, and more measurable.

## License

MIT.
