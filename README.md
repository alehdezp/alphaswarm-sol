# AlphaSwarm.sol

Multi-orchestrator smart-contract security framework. Audits Solidity
code through a behavioral knowledge graph and a set of role-scoped
agent teams coordinated by distinct orchestrators. Produces findings
whose every claim resolves to graph nodes, code locations, debate
transcripts, and non-fakeable proof tokens.

> **Status legend used in this README:**
> **S** = shipped and running end-to-end on real contracts ·
> **C** = code exists but not proven end-to-end (scaffolded) ·
> **D** = designed in `.planning/` only, not yet implemented.

## For non-technical readers

Smart contracts hold large amounts of money and bugs in them are
effectively irreversible. Two kinds of tool exist today: static
analyzers that only catch simple syntax patterns, and LLM-based
auditors that reason more broadly but fabricate evidence. This project
takes a different approach. It first builds a structured map of what
each function actually does — not what it's named — and then has a
team of AI agents in different roles argue every suspicious finding
with evidence from that map. Unfounded claims are rejected by the
system, not filtered afterwards.

It is not one agent debating another. It is more than two dozen
specialized agents coordinated through several distinct orchestrators
(one for the audit itself, others for growing the dataset, improving
it, running static checkers, splitting work into trackable units,
and a separate one for testing the whole system against itself).

The project is under active development. The end-to-end audit
pipeline is not yet proven on real benchmarks. The
`.planning/STATE.md` and `docs/LIMITATIONS.md` are the authoritative
honest status.

## The knowledge graph — BSKG

The Behavioral Security Knowledge Graph is the substrate every agent
queries. It is not a vector index over source and not a plain call
graph. It is a typed graph whose nodes carry around 200
security-relevant properties each, derived by fusing outputs from:

- Slither IR (AST, CFG, dataflow)
- Mythril (symbolic traces, reachable paths)
- Aderyn (Rust-based static diagnostics)
- Foundry / Halmos (formal verification results)
- Solodit (historical vulnerability findings)

Each function node carries:
- Semantic operations (20 defined — e.g. `TRANSFERS_VALUE_OUT`,
  `READS_USER_BALANCE`, `CHECKS_PERMISSION`,
  `MODIFIES_CRITICAL_STATE`)
- A behavioral signature — a compact opcode sequence over those
  operations describing execution order
- Dominator information — which guards control which paths to a sink
- Taint flow — where attacker-controllable data reaches
- Cross-contract edges — calls, inheritance, delegatecall, proxy
- Deterministic IDs (SHA-256 of node properties) so evidence
  references stay stable across builds

Queries run in **VQL** (Vulnerability Query Language) as graph
traversals, not similarity search. Every finding's evidence is a
specific set of node IDs and edge traversals that resolve back to
source at a given build hash.

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

Queries are path-qualified (always-before / sometimes-before /
never-before), dominance-aware (guard dominates sink vs bypassable),
and taint-aware (sink reachable from an attacker-controllable source).
These distinctions come from the project's own
[`docs/PITFALLS.md`](docs/PITFALLS.md) and separate a true positive
from a false negative.

## Agent catalog — 24 agents, 11 roles

The project ships 21 agents and keeps 3 dev-only. Source of truth:
[`src/alphaswarm_sol/agents/catalog.yaml`](src/alphaswarm_sol/agents/catalog.yaml).
They are **not** organized into four fixed teams — team compositions
are dynamic per workflow. Grouped by function:

| Group | Agent | Model | Role |
|---|---|---|---|
| **Verification triad** | `vrs-attacker` | Opus | Construct exploit paths, cite graph nodes |
| | `vrs-defender` | Sonnet | Prove guard dominance — not just presence |
| | `vrs-verifier` | Opus | Read both transcripts, arbitrate verdict + confidence |
| | `vrs-secure-reviewer` | Sonnet | Evidence-first adversarial review |
| **Workflow coordination** | `vrs-supervisor` | Sonnet | Coordinate multi-agent workflows, debate protocol |
| | `vrs-integrator` | Sonnet | Merge verdicts, generate consolidated reports |
| **Pattern work** | `vrs-pattern-scout` | Haiku | Fast pattern triage |
| | `vrs-pattern-verifier` | Sonnet | Verify Tier B / C pattern matches |
| | `vrs-pattern-composer` | Sonnet | Discover composite vulnerabilities via op algebra |
| **Context & evidence** | `vrs-context-packer` | Sonnet | Assemble Pattern Context Packs for batch discovery |
| | `vrs-finding-merger` | Sonnet | Merge duplicate findings deterministically |
| | `vrs-finding-synthesizer` | Sonnet | Merge convergent evidence with confidence bounds |
| | `vrs-contradiction` | Sonnet | Refutation-only adversarial review |
| **Testing pipeline (Phase 7.2)** | `vrs-test-conductor` | Opus | Orchestrate validation pipeline + quality gates |
| | `vrs-corpus-curator` | Sonnet | Validate corpus integrity and composition |
| | `vrs-benchmark-runner` | Haiku | Execute benchmarks, collect metrics |
| | `vrs-mutation-tester` | Haiku | Generate contract variants for pattern-robustness testing |
| | `vrs-regression-hunter` | Sonnet | Detect accuracy degradation via behavioral fingerprinting |
| | `vrs-gap-finder` | Opus | Comprehensive 4-axis coverage-gap analysis |
| | `vrs-gap-finder-lite` | Sonnet | Fast coverage scan with escalation flag |
| **Discovery & validation** | `vrs-prevalidator` | Haiku | Fast gate for URL provenance and duplicate detection |
| **Dev-only** | `skill-auditor` | Sonnet | Audit skill / subagent quality + guardrails |
| | `cost-governor` | Haiku | Budget-aware model routing recommendations |
| | `gsd-context-researcher` | Sonnet | Deep Exa research for roadmap context |

## Orchestrator topology — 27+ distinct orchestrators

The system has multiple orchestrators operating at different layers
and tempos. Source: `src/alphaswarm_sol/orchestration/`, the skills
registry, and the Phase 3.1c / 3.1c.3 intelligence-module plans.

### Audit-time orchestrators

| Orchestrator | What it does | State |
|---|---|---|
| **Claude Code framework** (today) / **Pi-mono** (planned) | Primary execution model — receives user prompt, invokes skills, spawns subagents, enforces hooks | **S** (Claude Code) / **D** (Pi) |
| `/vrs-audit` skill | 9-stage audit pipeline entrypoint; invokes the CLI, supervisor, and integrator | **C** — stages 1–3 run; Stage 4 (tool init) breaks end-to-end per `.planning/STATE.md` |
| `/vrs-verify`, `/vrs-investigate`, `/vrs-debate` | Per-workflow orchestration skills that spawn attacker / defender / verifier | **C** — shipped specs; debate has never executed on a real contract |
| `/vrs-orch-spawn`, `/vrs-orch-resume` | Pool-based orchestration: spawn parallel investigation beads; resume suspended pools | **C** |
| `DebateOrchestrator` (`orchestration/debate.py`) | Structured iMAD-inspired debate: Claim → Rebuttal(s) → Synthesis → Human checkpoint | **C** — full class implemented, never executed per `STATE.md` "Multi-agent debate \| Core feature \| Never executed" |
| `Router` (`orchestration/router.py`) | Stateless routing decisions based on pool status; emits `RouteAction` enum over BUILD_GRAPH → DETECT_PATTERNS → LOAD_CONTEXT → CREATE_BEADS → SPAWN_ATTACKERS → SPAWN_DEFENDERS → SPAWN_VERIFIERS → RUN_DEBATE → COLLECT_VERDICTS → GENERATE_REPORT | **C** |
| `PoolManager` / `PoolStorage` (`orchestration/pool.py`) | Manage persistent pool state at `.vrs/pools/{pool_id}.yaml`: create, add bead, record verdict, advance phase, track budget | **C** |
| `ToolRunner` (`orchestration/runner.py`) | Run Slither / Aderyn / Mythril, normalize to a common schema | **C** — integration breaks at Stage 4 |
| `ExecutionLoop` (`orchestration/loop.py`) | Drive the state machine: pool status → router decision → handler invocation | **C** |
| `vrs-tool-coordinator` (skill) | Select optimal tool subset per contract profile, deduplicate SARIF | **C** |

### Testing-framework orchestrators (Phase 3.1c family)

A separate multi-agent system whose job is to score the audit system.

| Orchestrator | What it does | State |
|---|---|---|
| `EvaluationRunner` | Drive a scenario through: spawn agent → capture hooks → score reasoning → update coverage | **C** — Tier 1 engine works on synthetic data |
| `/vrs-test-enforce` skill | Quality gates during development: coverage radar + contract-healer alerts | **C** |
| `/vrs-test-e2e` skill | Multi-wave end-to-end validation pipeline | **C** |
| `/vrs-test-workflow` skill | Test skills and agents via Agent Teams with compositional stress | **C** |
| **5 Claude Code hooks** (`PreToolUse`, `PostToolUse`, `SubagentStart`, `SubagentStop`, `Stop`) | Capture observations, enforce evidence requirements, block fabricated outputs | **D** — designed in 3.1c Plan 01; deployment to `.claude/settings.json` is Phase 3.1c.3 work |

### Tier-2 intelligence sub-modules (all Phase 3.1c.3, 12 modules)

Per [`.planning/phases/3.1c.3-evaluation-intelligence-bootstrap/3.1c.3-CONTEXT.md`](.planning/phases/3.1c.3-evaluation-intelligence-bootstrap/3.1c.3-CONTEXT.md),
this layer is **~90% unbuilt**. It is the adaptive intelligence that
consumes Tier-1 output.

| Module | Purpose | State |
|---|---|---|
| `ReasoningDecomposer` | Per-move scoring: HYPOTHESIS_FORMATION, QUERY_FORMULATION, RESULT_INTERPRETATION, EVIDENCE_INTEGRATION, CONTRADICTION_HANDLING, CONCLUSION_SYNTHESIS, SELF_CRITIQUE | **D** |
| `CoverageRadar` | 4-axis heat map (vuln class × semantic op × reasoning skill × graph-query pattern) with severity weighting (Core 3× / Important 2× / Standard 1×). Cold-cell reporting | **C** (170 LOC, design wired to 4 contract templates, undeployed) |
| `ScenarioSynthesizer` | Analyze skill/agent prompts → extract testable claims → generate scenario YAML stubs (status: draft, require manual review) | **D** |
| `ContractHealer` | Bimodal detection for ambiguous evaluation contracts; anomaly-report output | **C** (117 LOC) |
| `TierManager` | Promotion / demotion proposals as YAML at `.vrs/evaluations/tier-proposals.yaml` | **C** (110 LOC) |
| `CounterfactualReplayer` | Trajectory recording from hook-captured events for manual "what-if" analysis | **D** |
| `Fingerprinter` | Behavioral-signature schema (activation stub); matches only once 20+ runs/workflow exist | **D** (schema only) |
| `GraphDiagnostics` | Diagnose why queries fail and why patterns don't match; recommend fixes | **D** |
| `RecommendationEngine` | Failure → fix mapping (low HYPOTHESIS_FORMATION ⇒ "add state hypothesis"; 0 queries ⇒ "CLI path broken") | **D** |
| `PlanningBridge` | Translate test gaps into planning actions (`/msd:insert-phase`, `/msd:improve-phase`); experiment-before-continue | **D** |
| `HotfixProtocol` | Classify failure (HOTFIX_NOW / PLAN_NEXT / PHASE_NEEDED / INVESTIGATE / DEFER); spawn `Task()` subagent for safe small fixes | **D** |
| `Framework Self-Validation` | Meta-test suite — tests the testing framework against itself (synthetic data, regression detection, both spawn paths) | **D** |

Five more modules (`InsightPropagator`, `EvaluatorImprover`,
`CompositionTester`, `AdversarialAuditor`, `FeedbackIngester`) are
explicitly **deferred to post-3.1f** because they require data
volumes not yet produced.

### Supporting orchestrators (dataset / pattern / knowledge)

| Orchestrator | Purpose |
|---|---|
| `/pattern-forge` skill | Iterative pattern creation — compose → test → validate gates → merge |
| `/refine`, `/test-pattern`, `/pattern-verify`, `/pattern-batch` | Pattern improvement, validation, and batch execution |
| `/vrs-discover`, `/vrs-ingest-url`, `/vrs-add-vulnerability`, `/merge-findings` | Dataset curation — mine, ingest, dedupe, add to VulnDocs |
| `WorkspaceRollback` (Jujutsu) | `jj workspace add` → run eval → `jj restore` for repeatable test scenarios |

## Teams — dynamic compositions

The system does not have fixed teams. Teams are **assembled per
workflow** and torn down on completion. Seven are observable in the
docs and code:

| Team | Roster | Trigger | Artifact produced |
|---|---|---|---|
| **Audit Team** | Supervisor + Attacker + Defender + Verifier + Integrator + (optionally) Secure-Reviewer | `/vrs-audit contracts/` | Evidence-linked report at `.vrs/evidence/{pool_id}/` |
| **Investigation Pool** | Per-bead attacker / defender / verifier subagents | `/vrs-orch-spawn` or Stage 6 of audit | Pool YAML at `.vrs/pools/{pool_id}.yaml` + bead YAMLs |
| **Testing Team** | Test-conductor + corpus-curator + benchmark-runner + mutation-tester + regression-hunter + gap-finder | `/vrs-test-enforce` or recurring schedule | Reports under `.vrs/evaluations/` |
| **Pattern-Forge Team** | Pattern-composer + test-builder + secure-reviewer | `/pattern-forge` | Validated pattern YAML in `vulndocs/` |
| **Tool-Coordination Team** | Tool-coordinator + Slither/Aderyn/Mythril runners + deduplicator | Stage 4 of `/vrs-audit` | Unified finding list |
| **Evaluation Team** | Tier-1 engine + 12 Tier-2 intelligence modules | Evaluation session spawn | Artifacts under `.vrs/observations/{session_id}/` + `.vrs/evaluations/` |
| **Knowledge-Aggregation Team** | Context-packer + finding-merger + finding-synthesizer + contradiction agent | Post-investigation | Merged findings with confidence bounds |

## Beads and pools — work-unit coordination

Long audits split into **beads** (trackable investigation units with
status, evidence, and verdict) and **pools** (collections of beads in
one audit session). Skills `/vrs-bead-create`, `/vrs-bead-update`,
`/vrs-bead-list` manage lifecycle: `open → investigating → confirmed
/ rejected`. Storage: `.vrs/pools/{pool_id}.yaml` +
`.vrs/beads/{pool_id}/{bead_id}.yaml`. Persistence across sessions
lets an audit resume after interruption.

## Named multi-agent protocols

| Protocol | Where it appears | State |
|---|---|---|
| **iMAD** (Intelligent Multi-Agent Debate, Fan et al. 2025) | `orchestration/debate.py`, `/vrs-debate` skill; cited in the project's paper draft | **C** — implemented, not yet executed |
| **Tool-MAD** | `vrs-tool-coordinator` — parallel Slither/Aderyn/Mythril + SARIF dedup | **C** |
| **Graph-First Rule** | `docs/reference/graph-first-template.md` + enforced by planned hooks checking for `BSKGQuery` markers | **S** (template) / **D** (enforcement) |
| **Reflect-Refine loop** | Debate + evaluation feedback — agent reasons → verifier critiques → agent refines | **C** |
| **Blind-then-Debate Dual-Opus** | Two evaluators score independently, then debate disagreements > 15pt | **D** |
| **Hierarchical Delegation** | Claude Code → skill → subagents → TaskUpdate verdicts | **S** |
| **Template-Based Context Injection** | Skills and agent prompts are templates filled with graph slices, evidence packets, contract context | **S** |
| **Sub-Coordinator pattern** | Attacker / Defender as sub-coordinators under Supervisor; coverage-radar as sub-coordinator under test-runner | **D** |
| **Self-Healing Tests (5-stage)** | Scenario run → hooks capture → coverage radar → hotfix classifier → subagent fix or escalate | **D** |

## Evidence and artifacts — 15 schemas

Every claim resolves to an artifact with a schema. Mapping:

| Artifact | Schema location | Storage | Producer |
|---|---|---|---|
| Evidence Packet | `orchestration/schemas.py:EvidencePacket` | embedded in beads or `.vrs/evidence/` | investigation agents |
| Proof Token | per PHILOSOPHY.md §"Proof Token Types" (BSKG build / agent spawn / debate / detection) | `.vrs/evidence/proof-tokens.jsonl` | pipeline stages |
| Bead | `schemas.py:Bead` | `.vrs/beads/{pool_id}/{bead_id}.yaml` | pattern detection, updated by agents |
| Pool Manifest | `orchestration/pool.py` | `.vrs/pools/{pool_id}.yaml` | PoolManager |
| Debrief JSON | planned in 3.1c.3 Plans 05 / 02 | `.vrs/observations/{session_id}_debrief.json` | agents post-evaluation |
| Graph Build Hash | metadata header | `.vrs/graphs/{contract}.toon` | VKG Builder |
| Transcript JSONL | ObservationRecord schema | `.vrs/observations/{session_id}/hooks.jsonl` | Claude Code hooks (planned) |
| Ground-Truth YAML | `examples/testing/projects/*/ground-truth.yaml` | per-project | dataset-curation team |
| Coverage Report | 3.1c.3 Plan 03 | `.vrs/evaluations/coverage-report.json` | CoverageRadar |
| Tier Proposals | 3.1c.3 Plan 05 | `.vrs/evaluations/tier-proposals.yaml` | TierManager |
| Hotfix Log | 3.1c.3 Plan 12 | `.vrs/evaluations/hotfix-log.jsonl` | HotfixProtocol |
| Trajectory | 3.1c.3 Plan 06 | `.vrs/observations/{session_id}/trajectory.json` | CounterfactualReplayer |
| Recommendations | 3.1c.3 Plan 10 | `.vrs/evaluations/recommendations-report.json` | RecommendationEngine |
| Graph Diagnostics | 3.1c.3 Plan 08 | `.vrs/evaluations/graph-diagnostics.json` | GraphDiagnostics |
| Scenario Stubs | 3.1c.3 Plan 04 | `.vrs/evaluations/scenario-stubs.yaml` | ScenarioSynthesizer |

## Pattern catalog and tiering

466 active patterns across 18 categories (39 archived, 57 quarantined
— per [`.planning/STATE.md`](.planning/STATE.md)). Patterns carry a
status from measured precision and recall on real contracts:

| Status | Precision | Recall |
|---|---|---|
| draft | < 70% | < 50% |
| ready | ≥ 70% | ≥ 50% |
| excellent | ≥ 90% | ≥ 85% |

Three detection tiers, in order of cost:
- **Tier A** — deterministic graph-only queries (no LLM call)
- **Tier B** — LLM-verified, for logic bugs needing reasoning
- **Tier C** — label-dependent (requires upstream semantic role labeling)

Validation coverage is honest: Phase 2.1 spot-tested 10 rescued
patterns (9/10 true-positive on real contracts). The remaining ~456
are not individually validated; VulnDocs schema checks pass for
89/106 index entries.

## Why target Solidity specifically

- Losses are irreversible — no patch-and-redeploy after exploit.
- Contracts are short in code but long in composition; most serious
  bugs appear at interaction boundaries between contracts, not inside
  one.
- Function names in DeFi are near-universal (every protocol has
  `withdraw`, `swap`, `claim`); security properties live in behavior
  and ordering, not naming.
- Attack viability depends on economic context (oracle depth,
  flash-loan liquidity, governance token distribution), not code alone.

A graph model captures composition, ordering, and dataflow. An
operation vocabulary captures behavior independent of naming. A
protocol-context layer supplies the economic dimension.

## The harness — Pi-mono

Production orchestration is moving to the Pi-mono coding-agent
package (`@mariozechner/pi-coding-agent`,
[GitHub](https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent)).
Implementation specifics are not fully settled; the direction is
committed, the shape is being worked out. Relevant Pi primitives:

- **Native tool registration** (`pi.registerTool`). BSKG queries,
  Slither / Mythril / Aderyn / Halmos adapters, pattern matcher,
  evidence builder, proof-token issuer, and `/web-research` all
  become first-class in-process tools. No MCP boundary.
- **Per-agent tool scoping.** Pi ships no permission-popup system;
  scoping is composed from `pi.setActiveTools`, `allowed-tools` in
  skill frontmatter, and `tool_call` handlers returning
  `{block: true, reason}`. Each agent definition gets a distinct
  tool set, file-write scope, and command allow-list.
- **Session control** — `ctx.newSession({parentSession, setup})`,
  `ctx.fork(entryId)`, `ctx.navigateTree`, `ctx.waitForIdle`.
  Challenger and Defender as sibling forks; Verifier reads both.
- **Middleware hooks** — `before_provider_request` can rewrite the
  system prompt per call (per-agent prompt surgery); `tool_result`
  middleware post-processes raw tool output; `session_before_compact`
  gates long audits.
- **Cross-session messaging** via the event bus and
  `pi.sendMessage` / `pi.sendUserMessage` with
  `deliverAs: "steer" | "followUp" | "nextTurn"`.
- **RPC mode** — stdin/stdout JSONL with LF delimiters, for
  programmatic drive without a network surface.

Pi's explicit non-goals (from its README): no MCP, no sub-agents,
no permission popups, no plan mode, no background bash. Each absence
is something this project builds as an extension or deliberately
leaves out.

## Claude Code's role under the new direction

Claude Code is not the production runtime once Pi is the harness. It
is kept for three dev-time responsibilities:

1. **IDE-level assistance** for writing and maintaining Pi agent
   definitions, skills, prompts, and tool adapters.
2. **Driving the self-testing meta-loop**: running the current Pi
   orchestrator and any prior Claude-Code orchestrator against the
   same corpus under identical conditions, capturing both transcripts.
3. **Quality assessment** of Pi audit outputs. The Reasoning
   Evaluator runs under Claude Code — dual-Opus scoring, 7-move
   reasoning decomposition, Graph-Value Scorer distinguishing
   checkbox use from genuine use, anti-fabrication signals.

## Doc conflicts — honest note

The planning corpus (22 phase folders, 684-line ROADMAP, 655-line
STATE, research reports, philosophy, architecture, testing rules) is
not internally consistent. A few standing conflicts the reader
should be aware of:

- **"Agent Teams is primary" (REPORT-02) vs "Claude Code skills are
  primary" (CLAUDE.md).** Reconcilable: skills are invoked by Claude
  Code; Agent Teams is the multi-agent coordination mechanism under
  skills. Both are true in different senses.
- **"Testing framework complete" (3.1b-VERIFICATION) vs "Tier 2 is
  90% unbuilt" (3.1c.3-CONTEXT).** Both true: Tier-1 engine is
  proven on synthetic data; Tier-2 intelligence layer is what 3.1c.3
  is building.
- **"Multi-agent debate is a core feature" (PHILOSOPHY) vs "Never
  executed" (STATE.md).** Implementation exists; end-to-end execution
  has not happened.
- **"E2E pipeline works" (PHILOSOPHY) vs "Breaks at Stage 4"
  (STATE.md).** Design works; Tool Init (Stage 4) has integration
  issues.
- **"24 agents in 4 teams" (early summaries) vs 11 role-groups with
  dynamic team assembly (catalog).** There is no fixed 4-team
  topology; teams form per workflow.
- **Claude Code hooks are described as deployed (PHILOSOPHY)** —
  deployment is planned for 3.1c.3 Plan 01, not yet shipped.

The most honest single source is `.planning/STATE.md`. The most
honest single line from it: *"Multi-agent debate is never executed,
benchmarks are zero ever run, the E2E pipeline breaks at Stage 4."*

## Read further

- [`docs/PHILOSOPHY.md`](docs/PHILOSOPHY.md) — execution model, 9-stage pipeline
- [`docs/architecture.md`](docs/architecture.md) — modules and data flow
- [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) — explicit limits
- [`docs/PITFALLS.md`](docs/PITFALLS.md) — domain pitfalls
- [`.planning/ROADMAP.md`](.planning/ROADMAP.md) — phase plan (v6.0)
- [`.planning/STATE.md`](.planning/STATE.md) — current honest state
- [`.planning/phases/3.1c.3-evaluation-intelligence-bootstrap/3.1c.3-CONTEXT.md`](.planning/phases/3.1c.3-evaluation-intelligence-bootstrap/3.1c.3-CONTEXT.md) — Tier-2 intelligence build
- [`src/alphaswarm_sol/agents/catalog.yaml`](src/alphaswarm_sol/agents/catalog.yaml) — canonical agent catalog
- [`src/alphaswarm_sol/skills/registry.yaml`](src/alphaswarm_sol/skills/registry.yaml) — canonical skill registry
- [`vulndocs/`](vulndocs/) — pattern catalog (18 categories)
- [`src/alphaswarm_sol/`](src/alphaswarm_sol/) — implementation
- Pi-mono coding-agent: https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent

License: MIT.
