# Phase 3.1b: Workflow Testing Harness & Test Corpus

## Planning Status

- This phase is a **planning draft** — plans not yet generated via `/gsd:plan-phase`.
- All 11 gaps identified in prior review have been resolved. Code changes are in place.
- Execution uses Claude Code's native Agent Teams (`TeamCreate`, `SendMessage`) as primary tool.
- Companion bridge (`claude-code-controller`) is deprioritized to Wave 4 (NICE-TO-HAVE).

## Goal

Front-load 3.1c API contract design (Wave 0), then build the core testing infrastructure (transcript parser with BSKG query extraction, hooks, scenario DSL with `modes`/`team_config`, Jujutsu-based workspace isolation), build a hostile adversarial corpus generation system that harvests all 466+ patterns and known vulnerable projects to create realistic obfuscated Solidity test projects via an Opus-powered Claude Code subagent (each project containing 5-10 security vulnerabilities for comprehensive single-shot testing), commit 15-20 seed projects as Jujutsu fixtures, and prove the full pipeline works end-to-end with an infrastructure smoke test — so Phase 3.1c has everything it needs to build the real evaluation framework.

## Why This Phase Exists

### The Core Problem

The multi-agent debate system has **never been executed**. Phases 3.2 (First Working Audit) and 4 (Agent Teams Debate) will build complex agent-dependent features — but without a testing harness, verification is purely manual, one-off, and non-repeatable.

Testing infrastructure must come first. Otherwise we build features that break later and are hard to fix.

**This phase is infrastructure. Phase 3.1c is the product.**

### What This Phase Delivers

1. **3.1c API contract design review** — Front-loaded type signatures for ALL 3.1c-facing APIs, preventing backtracking (Wave 0)
2. **TranscriptParser + OutputCollector** with `ToolCall`, `BSKGQuery` extraction, `TeamObservation` model, and extensible API designed for 3.1c
3. **Hook infrastructure + observation pipeline** with extensible `install_hooks()`, `.vrs/observations/`, and settings.json patterns
4. **Core testing harness** using Claude Code Agent Teams natively (`TeamCreate`, `SendMessage`, lifecycle management)
5. **Scenario DSL** following Anthropic's eval framework (tasks, trials, graders) with `evaluation:` slot for 3.1c, `modes: [single, team]`, and `team_config`
6. **Corpus generation system** — Guidelines + pattern catalog (466+ patterns as generation-ready specs) + Opus-powered Claude Code subagent that produces realistic adversarial Solidity projects with 5-10 vulnerabilities per project, creative obfuscation, `solc` compilation verification, and ground-truth generation
7. **Seed corpus (15-20 committed projects)** — Each project contains 5-10 security vulnerabilities from our patterns, enabling comprehensive testing in one shot. Committed as Jujutsu fixtures with obfuscated names, realistic project structure, false-positive controls
8. **Infrastructure validation smoke test** proving all plans work together end-to-end
9. **(Optional) Companion bridge** for programmatic N-trial automation — deferred to Wave 4

### What This Phase Does NOT Do

- **Not skill/agent/orchestrator testing** — Those belong to Phase 3.1c
- **Not reasoning evaluation** — Phase 3.1c
- **Not always-on observability** — Phase 3.1c (3.1b provides the hook registration architecture)
- **Not full multi-agent debate validation** — Phase 4
- **Not self-improving iteration loops** — Phase 3.1c-12
- **Not shipping confidence gate** — Phase 8

### Why Now (Before Phase 3.2)

Plans 02-09 have **zero technical dependency** on Phase 3.2 or Phase 4. The harness is pure tooling. Phase 3.2 benefits immediately from E2E regression tests, and Phase 4 benefits from systematic behavioral verification.

## Architecture: Claude Code = The Orchestrator

**Claude Code IS the primary controller in this harness. Claude Code IS you.**

The testing framework works like this:
1. **Claude Code (you) spawns the agent team** using `TeamCreate`
2. **You assign tasks** to attacker/defender/verifier teammates
3. **Teammates execute naturally** — they don't know they're being tested
4. **You monitor every step** — validating alignment with AlphaSwarm workflows
5. **For programmatic repetition** (N-trial runs), use `claude --print -p "prompt"` (native CLI) or optionally the Companion bridge (Wave 4)

```
┌──────────────────────────────────────────────────────────────┐
│  pytest / native CLI (programmatic trigger)                    │
│  - claude --print -p "Run scenario X"                          │
│  - Captures outputs via TranscriptParser                       │
│  - OutputCollector aggregates structured results               │
│  - Optional: Companion REST API for multi-turn N-trial runs    │
└────────────────┬─────────────────────────────────────────────┘
                 │ spawns
                 ▼
┌──────────────────────────────────────────────────────────────┐
│  Claude Code (YOU — THE ORCHESTRATOR)                         │
│  - Creates team: TeamCreate("vrs-audit-test")                 │
│  - Spawns teammates: attacker, defender, verifier             │
│  - Assigns tasks via TaskCreate/TaskUpdate                    │
│  - Monitors via SendMessage, TaskList                         │
│  - Validates: graph-first? evidence anchored? correct flow?   │
│  - Teammates DON'T KNOW this is a test                        │
│  - Uses real shipped skills/agents from shipping/              │
└────────────────┬─────────────────────────────────────────────┘
                 │ spawns teammates
                 ▼
┌──────────────────────────────────────────────────────────────┐
│  Teammates (real Claude Code instances)                        │
│  - attacker (opus): finds vulnerabilities using BSKG          │
│  - defender (sonnet): finds guards/mitigations                │
│  - verifier (opus): arbitrates, produces verdict              │
│  - Each uses shipped skills naturally                          │
│  - Output: evidence packets, verdicts, findings               │
└──────────────────────────────────────────────────────────────┘
```

### Primary Tool: Native Claude Code CLI

Research (4 parallel agents + self-critique) determined that Companion (`claude-code-controller`) is a **NICE-TO-HAVE**, not a prerequisite. The native `claude` CLI provides:
- `claude --print -p "prompt"` for single-turn programmatic invocation
- Agent Teams API (`TeamCreate`, `SendMessage`, etc.) for multi-agent workflows
- Hook system for observation capture
- Transcript JSONL for post-hoc analysis

**Companion adds** multi-turn session management and REST API for N-trial automation. This is only needed by 3.1c-12 (regression baseline) and can be built at any time without blocking the critical path.

### Existing Code (Already Implemented)

Several harness components already exist from prior iterations:

| Component | File | Status |
|-----------|------|--------|
| `TranscriptParser` + `ToolCall` | `tests/workflow_harness/lib/transcript_parser.py` | Exists, needs extension (BSKGQuery, TeamObservation) |
| `WorkspaceManager` | `tests/workflow_harness/lib/workspace.py` | Exists, needs `install_hooks()` extensibility |
| `EventStream` + `ControllerEvent` | `tests/workflow_harness/lib/controller_events.py` | Exists (160 LOC) |
| `ScenarioLoader` + `TestScenario` | `src/alphaswarm_sol/testing/harness/scenario_loader.py` | Exists with `modes` + `team_config` |
| `ScenarioConfig` (Pydantic) | `src/alphaswarm_sol/testing/scenarios/config_schema.py` | Exists with `TeamConfig`, `modes`, `IsolationConfig`, `ChaosConfig` |
| `ClaudeCodeRunner` + `ClaudeCodeResult` | `src/alphaswarm_sol/testing/harness/runner.py` | Exists with `failure_notes` field |
| `log_session.py` hook | `tests/workflow_harness/hooks/log_session.py` | Exists |
| Agent catalog with `category` | `src/alphaswarm_sol/agents/catalog.yaml` + `catalog.py` | 24 agents categorized |
| Skill registry with `category` | `src/alphaswarm_sol/skills/registry.yaml` | 34 skills categorized |
| Vulndocs coverage audit | `examples/testing/scripts/audit-vulndocs-coverage.py` | Created (one-time audit script) |

## Wave Execution Order

Revised wave structure consolidates corpus plans (06a+06b+06c → 06a+06b) and front-loads API contract design:

```
Time --->

Wave 0:  [08: 3.1c API Contract Design Review]              [03: DONE]
Wave 1:  [02: Parser+Collector] [06a-pt1: Guidelines+Catalog]
Wave 2:  [04: Agent Teams]  [06a-pt2: Opus Generation Agent]
Wave 3:  [05: Scenario DSL]  [06b: Seed Corpus (15-20 projects)]
Wave 4:  [01: Companion -------- optional, any time --------]
Wave 5:                          [07: Smoke Test]
```

**Rationale:**
- **Wave 0** (first): 08 (API contract review) produces type signatures that guide ALL subsequent plans. Prevents backtracking. 03 is already DONE
- **Wave 1** (parallel): 02 has 4 blocking 3.1c consumers, 06a Part 1 is independent (pure documentation + cataloging)
- **Wave 2** (parallel): 04 depends on 02 (parser) and 03 (hooks, done). 06a Part 2 (Opus generation agent) depends on 06a Part 1 (needs the guidelines/catalog to generate from)
- **Wave 3** (parallel): 05 depends on 04 (team-aware scenarios). 06b (seed corpus) depends on 06a Part 2 (uses the generation agent to produce projects)
- **Wave 4**: 01 has ZERO blocking 3.1c consumers — only NICE-TO-HAVE for 3.1c-12
- **Wave 5**: 07 integrates all; works without Companion

**Parallelization note (Rec 2):** Within each wave, plans are independent and should be executed in parallel wherever possible. Plans 02, 03, and 05 in particular have minimal coupling — if wave boundaries prove too conservative during execution, 05 could potentially start alongside Wave 1 work since its only real dependency is on ScenarioConfig (already implemented).

## Plans (9)

## Phase-Wide Strict Validation Contract (Mandatory)

No 3.1b plan is complete unless all artifacts below exist for that plan:

1. **Machine Gate Report**: `.vrs/debug/phase-3.1b/gates/<plan-id>.json`
2. **Human Checkpoint Record**: `.vrs/debug/phase-3.1b/hitl/<plan-id>.md`
3. **Drift Log Entry**: `.vrs/debug/phase-3.1b/drift-log.jsonl` (append-only)

## `/gsd-plan-phase` Dynamic Check Contract

For each `3.1b-xx` plan, `/gsd-plan-phase` must generate derived checks and research notes before implementation:

1. `.vrs/debug/phase-3.1b/plan-phase/derived-checks/<plan-id>.yaml`
2. `.vrs/debug/phase-3.1b/plan-phase/research/<plan-id>.md`
3. `.vrs/debug/phase-3.1b/plan-phase/hitl-runbooks/<scenario-id>.md`

Canonical governance and schema/template references:
- `.planning/testing/PLAN-PHASE-GOVERNANCE.md`
- `.planning/testing/schemas/phase_plan_contract.schema.json`
- `.planning/testing/templates/PLAN-INVESTIGATION-CHECKS-TEMPLATE.yaml`
- `.planning/testing/templates/HITL-RUNBOOK-TEMPLATE.md`
- `.planning/testing/templates/DRIFT-RCA-TEMPLATE.md`

Rule: no static success criteria are allowed unless they are protocol invariants or externally sourced constraints.

## Plan Preconditions (Resolve During `/gsd-plan-phase`)

| Plan | Preconditions to Resolve | Derivation Requirement |
|---|---|---|
| 3.1b-08 | 3.1c plan descriptions, existing harness API surface | Derive from 3.1c context.md + `tests/workflow_harness/lib/` inventory |
| 3.1b-02 | Existing transcript parser + missing BSKGQuery/TeamObservation fields | Derive gaps from `tests/workflow_harness/lib/` inventory and 3.1b-08 API contracts |
| 3.1b-03 | Hook registration model, JSONL schema, settings.json pattern | DONE — verify completeness during plan |
| 3.1b-04 | Native Agent Teams capabilities, missing lifecycle features | Derive from Agent Teams API and `EventStream` inventory |
| 3.1b-05 | Scenario DSL constraints, `modes`/`team_config` integration | Verify `ScenarioConfig` and `TestScenario` have all fields (already implemented) |
| 3.1b-06a | Active pattern inventory, adversarial obfuscation taxonomy, Opus subagent prompt design, `solc` toolchain | Derive from `vulndocs/` inventory, audit script output, known vulnerable project analysis, ScenarioConfig schema |
| 3.1b-06b | 5-10 vulns per project requirement, pattern coverage targets, false-positive control contracts | Derive from 06a catalog + generation agent capabilities + vulndocs coverage audit |
| 3.1b-07 | Infrastructure component availability | Derive from plans 02-06b API surface |
| 3.1b-01 | Companion prerequisites (npm, bun), env flags | Derive from `claude-code-controller` docs (Wave 4, optional) |

---

### 3.1b-02: TranscriptParser + OutputCollector + Data Model (Wave 1)

**The core data model that everything downstream depends on.**

**Part A — Extend TranscriptParser:**

The existing `TranscriptParser` (225 LOC) and `ToolCall` dataclass need extension with:

1. **`BSKGQuery` extraction** (GAP-02): Structured extraction of BSKG queries from Bash tool calls
   ```python
   @dataclass
   class BSKGQuery:
       command: str                    # Full alphaswarm command
       query_type: str                # "build-kg", "query", "pattern-query"
       query_text: str                # The query string itself
       result_snippet: str            # First 2000 chars of result (not 500)
       tool_call_index: int           # Position in transcript
       cited_in_conclusion: bool      # Heuristic: was this result referenced later?
   ```
   New methods: `get_bskg_queries() -> list[BSKGQuery]`, `graph_citation_rate() -> float`

2. **Extension-friendly API** for 3.1c:
   - `_records` must remain accessible (private but stable)
   - `get_raw_messages()` for callers needing full message objects
   - Index-based access: `get_message_at(index)`, `get_messages_between(start_idx, end_idx)`
   - `timestamp` and `duration_ms` fields on `ToolCall` enable 3.1c-03 timing distributions

**Part B — TeamObservation model** (GAP-01): Cross-agent observation correlation

```python
@dataclass
class AgentObservation:
    agent_id: str
    agent_type: str                      # "attacker", "defender", "verifier"
    transcript: TranscriptParser         # Agent's parsed transcript
    bskg_queries: list[BSKGQuery]        # Agent's graph queries
    messages_sent: list[InboxMessage]    # DMs from this agent
    messages_received: list[InboxMessage] # DMs to this agent

@dataclass
class TeamObservation:
    agents: dict[str, AgentObservation]  # agent_id -> observation
    events: EventStream                   # Team event stream

    def get_agent_by_type(self, agent_type: str) -> AgentObservation | None
    def cross_agent_evidence_flow(self) -> list[EvidenceFlowEdge]
    def debate_turns(self) -> list[DebateTurn]
```

**Part C — OutputCollector** (GAP-02): Aggregate run results

```python
@dataclass
class CollectedOutput:
    scenario_name: str
    run_id: str
    transcript: TranscriptParser
    team_observation: TeamObservation | None
    structured_output: dict | None       # Parsed JSON from agent
    tool_sequence: list[str]
    bskg_queries: list[BSKGQuery]
    duration_ms: float
    cost_usd: float
    failure_notes: str = ""              # Free-text failure classification (GAP-11)
```

Location: `tests/workflow_harness/lib/transcript_parser.py`, `tests/workflow_harness/lib/output_collector.py`

**Exit gate:** `BSKGQuery` extraction works on real transcripts. `TeamObservation` links agent transcripts to EventStream data. `OutputCollector` produces `CollectedOutput` from a scenario run. All existing 20+ parser tests still pass.

**Scope note:** This plan's scope is ~4x the original (parser-only) due to BSKGQuery + TeamObservation additions. Consider splitting into 02a (parser extension) and 02b (observation models) during `/gsd:plan-phase` if the plan exceeds the normal task budget.

#### Expected Outputs

- **Modified:** `tests/workflow_harness/lib/transcript_parser.py` — BSKGQuery extraction, extended API
- **Created:** `tests/workflow_harness/lib/output_collector.py` — OutputCollector + TeamObservation + CollectedOutput
- **Created:** Tests for new extraction methods and observation models
- **Metric:** BSKGQuery correctly identifies query type, text, and citation status
- **Metric:** TeamObservation correlates agent transcripts with team events

---

### 3.1b-03: Hook Infrastructure + Observation Pipeline (Wave 1 — DONE)

**Status: DONE (iterations 1-2 complete). Verify completeness during planning.**

Core deliverables already built:
1. `WorkspaceManager.install_hooks(hook_scripts)` extensibility
2. `_ensure_hook()` deduplication helper
3. `.claude/settings.json` hook registration pattern (multiple scripts per event type)
4. `.vrs/observations/` directory convention
5. `log_session.py` as the initial SubagentStop/Stop hook
6. Hook exit code 2 blocking convention documented (UNVERIFIED — 3.1c-05 research)

**During planning:** Verify that existing hook infrastructure supports the 5+ hooks 3.1c will add. Check `install_hooks()` accepts arbitrary lists, not just hardcoded paths.

---

### 3.1b-04: Agent Teams Framework (Wave 2)

**Depends on 3.1b-02 (parser/collector), 3.1b-03 (hooks, DONE). Does NOT depend on 3.1b-01.**

Build the core team testing framework using Claude Code's **native Agent Teams features**:

- Agent lifecycle: spawn → configure → run → capture → verify → cleanup
- Team lifecycle: `TeamCreate` → spawn teammates → monitor via `SendMessage`/`TaskList` → `TeamDelete`
- **Event capture must include `SendMessage` content** — full message body, not just metadata stubs
- **Sandbox `.claude/` support** — copy production skills/agents into test workspace; restore after
- Cross-run comparator (diff outputs across N runs)
- **Jujutsu-based workspace isolation** — Each test run uses a Jujutsu workspace for isolation, snapshot, and rollback. `jj workspace add` creates isolated copies; `jj op restore` rolls back to known state. This enables repeatable regression testing across iterations.
- **Multiple workspaces per scenario** — No limit on workspace count. Different workflows, different scenarios, different test configurations can each get their own workspace from the same repository state. A single corpus project can spawn N workspaces testing N different aspects simultaneously.
- **Manual scenario support** — Scenarios do NOT have to be generated by the framework or the generation agent. Tests can manually craft scenarios (prompts, task definitions, expected behaviors) for specific subagent testing. The generation agent is for Solidity contract creation; workflow/skill/agent scenarios can be manually authored YAML that points to any corpus project.

**Critical for 3.1c:**
- `SubagentStop` events must include `agent_transcript_path`
- Event capture pipeline stores all fields in structured run result for Python access
- SendMessage content fully captured for 3.1c interactive debrief protocol

Location: `tests/workflow_harness/`

**Exit gate:** Team lifecycle works with native Agent Teams. SendMessage content fully captured. Event stream parseable. No orphan sessions after cleanup.

#### Expected Outputs

- **Created/Modified:** Harness module with team lifecycle management
- **Created:** Python bridge for pytest integration
- **Created:** Environment manager for sandbox isolation
- **Metric:** `run_scenario()` returns structured result with `.messages`, `.tool_uses`, `.events`, `.duration_ms`, `.cost_usd`
- **State:** Harness works WITHOUT Companion (native Agent Teams only)

---

### 3.1b-05: Implement Scenario DSL (Wave 3)

**Depends on 3.1b-04 (team framework).**

Following Anthropic's eval framework: **tasks + trials + graders**.

**Already implemented in code:**
- `ScenarioConfig` (Pydantic) with `modes: [single, team]`, `TeamConfig`, `IsolationConfig`, `ChaosConfig`
- `TestScenario` (dataclass) with `modes`, `team_config`, `get_team_evaluation_questions()`

**Remaining work:**

1. **YAML scenario format** with full DSL:
   ```yaml
   name: health-check-basic
   description: Verify /vrs-health-check produces valid output
   timeout_seconds: 120
   model: sonnet
   modes: [single]                     # or [single, team] for comparison
   team_config:                         # Required when "team" in modes
     roles: [attacker, defender, verifier]
     model: sonnet
     team_ground_truth:
       evidence_passing: true
       debate_depth: 2
   steps:
     - prompt: "Run /vrs-health-check"
       expect:
         response_contains: ["alphaswarm", "build-kg"]
         tool_was_used: ["Bash", "Skill"]
   graders:
     - type: code    # exact match, regex, schema validation
     - type: model   # AI judge for nuanced evaluation
   trials: 3
   evaluation:                          # OPTIONAL — 3.1c populates logic
     contract: vrs-attacker
     run_gvs: true
     run_reasoning: true
   post_run_hooks:                      # OPTIONAL — 3.1c hook scripts
     - hooks/evaluate_reasoning.py
   ```

2. **Grader implementations**: code-based (string match, regex, schema) + model-based (AI judge)
3. **Schema validation** for scenario YAML (JSON Schema)
4. **`evaluation` and `post_run_hooks`** fields parsed and preserved (execution is 3.1c's job)

Location: `tests/workflow_harness/scenarios/`, graders module

**Exit gate:** Can define scenario in YAML with `modes` + `team_config`, load it, run graders against captured output. Both code and model graders work. `evaluation` and `post_run_hooks` fields accepted.

---

### 3.1b-06a: Corpus Generation System — Guidelines + Opus Agent (Wave 1-2)

**Part 1 (Wave 1, parallel with 02): Guidelines + Pattern Catalog. Part 2 (Wave 2): Opus-powered generation agent.**

**The "recipe book" AND the "chef" for the hostile corpus generation system — consolidated into one plan.**

The goal is NOT to test the happy path. The goal is to BUILD PROJECTS THAT BREAK THE ENGINE. Every generated project should simulate a real-world codebase that makes detection as hard as possible — obfuscated names, multi-pattern contracts, misleading structure, dead code red herrings, realistic project layout.

#### Part 1: Guidelines + Pattern Catalog (Wave 1)

**A — Pattern Generation Catalog:**

Catalog all 466+ active vulndocs patterns into generation-ready specifications:

| Per-Pattern Spec | Contents |
|-----------------|----------|
| `pattern_id` | Unique pattern identifier from vulndocs |
| `semantic_operations` | Required behavioral operations (e.g., TRANSFERS_VALUE_OUT, WRITES_USER_BALANCE) |
| `ordering_constraints` | Required operation ordering for vulnerability to exist |
| `combinable_with` | Other patterns that can coexist in the same contract |
| `obfuscation_resistance` | How easily this pattern survives name obfuscation (low/medium/high) |
| `min_contract_complexity` | Minimum LOC / function count for realistic embedding |
| `tier` | A (deterministic), B (LLM-verified), C (label-dependent) |

Output: `examples/testing/guidelines/pattern-catalog.yaml` (machine-readable, one entry per pattern)

**B — Adversarial Obfuscation Taxonomy:**

Three adversarial categories that test REASONING, not memorization:

| Category | What It Tests | Techniques |
|----------|---------------|------------|
| A: Name Obfuscation | Semantic operation detection vs name shortcuts | Rename functions (withdraw→processRequest), misleading names (safeTransfer that isn't safe), dead code red herrings, variable aliasing, parameter reordering |
| B: Protocol Complexity | Cross-contract + temporal reasoning | Multi-contract split vulnerabilities, proxy patterns, state machine violations, inherited vulnerability across contract hierarchy, library-mediated exploits |
| C: Honeypot Inversions | False positive resistance | Safe code with dangerous names, properly guarded but complex-looking patterns, defense-in-depth that looks vulnerable, unreachable vulnerable code paths |

Each category includes:
- 5-10 specific obfuscation techniques with examples
- Difficulty rating per technique
- Compilation requirements (must pass `solc 0.8.x`)

Output: `examples/testing/guidelines/adversarial-taxonomy.md`

**C — Multi-Pattern Combination Rules:**

Rules for combining multiple patterns into single contracts to create realistic complexity:

| Rule | Description |
|------|-------------|
| Compatible combinations | Which patterns can coexist without conflicting (e.g., reentrancy + access-control) |
| Interference patterns | Combinations where one pattern's fix breaks another's detection |
| Realistic complexity targets | 5-10 patterns per project (see minimum vulnerability requirement below) |
| Cross-function distribution | Vulnerabilities spread across multiple functions, not all in one |

Output: `examples/testing/guidelines/combination-rules.yaml`

**D — Generation Pipeline Specification:**

8-step pipeline for creating test projects:

1. Select target patterns from catalog (**minimum 5, target 5-10** per project)
2. Extract behavioral specifications and ordering constraints
3. Design realistic project structure (multiple files, interfaces, libraries)
4. Generate novel contract code implementing all selected patterns
5. Apply adversarial obfuscation from Category A/B/C
6. Create ground truth with `expected_reasoning_chain` per pattern
7. Generate safe variant (same structure, vulnerabilities removed)
8. Compile both variants and validate

Output: `examples/testing/guidelines/generation-pipeline.md`

**E — Vulndocs Coverage Audit:**

The audit script `examples/testing/scripts/audit-vulndocs-coverage.py` cross-references vulndocs patterns against test scenarios and SWC/OWASP classes. Run this to identify coverage gaps and prioritize which patterns need seed corpus coverage first.

**Training data contamination protocol:** All generated contracts must be NOVEL (not from Ethernaut, DVDeFi, or SWC test cases). Detecting known contracts measures recall, not reasoning.

#### Part 2: Opus-Powered Corpus Generation Agent (Wave 2)

**Depends on Part 1 (guidelines). Can parallelize with 3.1b-04.**

**A Claude Code subagent (Opus model) that produces realistic, adversarial Solidity test projects.**

**Why Opus:** The generation agent's quality directly determines corpus quality. Better reasoning = more genuinely adversarial projects, more creative obfuscation, more realistic business logic embedding. No cost concern — use the best model available for this creative task.

The generation agent receives pattern specs from the catalog and creates complete Solidity projects that simulate real-world codebases. It applies creative obfuscation to make detection maximally difficult — not to trick the LLM with known patterns, but to force genuine semantic reasoning.

**Agent Design:**

```
Input:  Pattern spec(s) from catalog + obfuscation category + complexity tier
        MINIMUM: 5 patterns per project (target 5-10)
Output: Complete Solidity project directory with:
        - contracts/*.sol (vulnerable variant)
        - contracts/*_safe.sol (safe variant)
        - ground-truth.yaml (per-pattern findings with expected_reasoning_chain)
        - project-manifest.yaml (metadata: patterns used, obfuscation applied, tier)
        - build-verification.sh (solc compilation check)
```

**Agent Capabilities:**

| Capability | Details |
|------------|---------|
| Multi-pattern embedding | **5-10 patterns per project** based on combination rules — test everything in one shot |
| Creative obfuscation | Apply Category A/B/C techniques intelligently, not mechanically |
| Realistic project structure | Multiple files, interfaces, libraries, imports — not toy contracts |
| Name generation | Realistic but non-standard function/variable/contract names |
| Safe variant generation | Same structure with vulnerabilities properly fixed |
| Ground truth authoring | Per-pattern: pattern_id, function, line_range, severity, expected_reasoning_chain |
| Compilation verification | Run `solc` and verify both variants compile |
| Jujutsu workspace init | Initialize generated project as Jujutsu repository for test isolation |

**Subagent Implementation:**

The agent is defined as a `.claude/agents/corpus-generator.md` (subagent_type in Task tool, **model: opus**). It:
1. Reads the pattern catalog and generation pipeline from guidelines
2. Receives a generation request (target patterns + obfuscation category + tier)
3. Generates the Solidity project using Opus-level reasoning for maximum creativity
4. Runs `solc` compilation check via Bash tool
5. Writes ground-truth.yaml with expected findings
6. Initializes Jujutsu workspace: `jj git init`, `jj commit`

**Key Design Principle:** The agent must produce projects that LOOK LIKE REAL CODEBASES. Not `contract Vulnerable { function withdraw() { ... } }` — but realistic DeFi protocols, token contracts, governance systems, staking mechanisms with vulnerabilities embedded naturally in business logic.

Location: `.claude/agents/corpus-generator.md`, `examples/testing/scripts/generate_project.py` (orchestration wrapper)

**Exit gate:** Pattern catalog covers all 466+ active patterns. Adversarial taxonomy covers 3 categories with 5+ techniques each. Combination rules define compatible/interfering pattern pairs. Generation pipeline specified end-to-end. Agent (Opus-powered) produces compilable Solidity projects from pattern specs. Both vulnerable and safe variants compile. Ground truth matches embedded patterns. Each generated project embeds **minimum 5 distinct vulnerability patterns** from our catalog. Obfuscation is applied (function names differ from pattern descriptions). At least 3 test generations succeed end-to-end. Jujutsu workspace initializes correctly per generated project.

---

### 3.1b-06b: Seed Corpus — 15-20 Committed Adversarial Projects (Wave 3)

**Depends on 3.1b-06a (guidelines + generation agent). Can parallelize with 3.1b-05.**

**The first batch of 15-20 adversarial projects, committed as Jujutsu fixtures.**

Using the Opus-powered generation agent and guidelines (06a), produce and commit the seed corpus. These are the BASELINE projects that every future test run references. They don't change unless deliberately updated.

**CRITICAL REQUIREMENT: Every project must contain 5-10 security vulnerabilities from our pattern catalog.** This lets us test multiple detection capabilities per project in one shot, rather than needing a separate project per vulnerability type. This is both more realistic (real codebases have multiple issues) and more efficient (fewer projects, more coverage).

**Corpus Composition:**

| Category | Projects | Vulns Per Project | Obfuscation Level |
|----------|----------|-------------------|-------------------|
| Workflow-testing | 3 | 5-7 (mixed categories) | None (vanilla) — focus on pipeline testing |
| Tier A: Multi-pattern DeFi | 5 | 5-8 (access-control + reentrancy + oracle + logic + dos combinations) | Category A (name obfuscation) |
| Tier A+B: Complex protocols | 3 | 7-10 (cross-contract + temporal + state machine + value flow) | Category A+B (names + cross-contract) |
| Tier B: Cross-contract | 2 | 5-7 (split across multiple contracts, proxy, inheritance) | Category B (protocol complexity) |
| False-positive controls | 3 | 0 real vulns (safe code with dangerous-looking patterns) | Category C (honeypot inversions) |
| Adversarial stress-test | 2 | 8-10 (maximum density, all obfuscated) | Category A+B+C combined |
| **TOTAL** | **~18** | **5-10 per project (except FP controls)** | All 3 categories represented |

**Per-Project Structure (Jujutsu-managed):**

```
examples/testing/corpus/
├── defi-lending-protocol-01/
│   ├── .jj/                          # Jujutsu repository
│   ├── contracts/
│   │   ├── LendingPool.sol           # 3 vulns: reentrancy, oracle, access-control
│   │   ├── FlashLoanProvider.sol     # 2 vulns: dos, logic
│   │   ├── PriceOracle.sol           # 2 vulns: oracle manipulation, stale data
│   │   ├── interfaces/ILending.sol
│   │   └── *_safe.sol variants
│   ├── ground-truth.yaml             # 7 expected findings with reasoning chains
│   ├── project-manifest.yaml         # Patterns used, obfuscation applied, tier
│   └── build-verification.sh         # solc compilation check
├── governance-staking-02/
│   ├── contracts/
│   │   ├── StakingVault.sol          # 3 vulns embedded in business logic
│   │   ├── GovernanceToken.sol       # 2 vulns in token mechanics
│   │   ├── RewardDistributor.sol     # 2 vulns in reward calculations
│   │   └── *_safe.sol variants
│   ├── ground-truth.yaml             # 7 expected findings
│   └── ...
├── safe-complex-governance/          # False-positive control
│   ├── contracts/
│   │   ├── TimelockController.sol    # Looks vulnerable but isn't
│   │   └── AccessManager.sol         # Complex guards that appear weak
│   ├── ground-truth.yaml             # expected_findings: []
│   └── ...
└── stress-test-max-obfuscation-01/
    ├── contracts/                     # 8-10 patterns, all obfuscated
    │   ├── DataProcessor.sol          # Misleading names everywhere
    │   ├── StateManager.sol
    │   ├── ExternalAdapter.sol
    │   └── *_safe.sol variants
    ├── ground-truth.yaml             # 8-10 expected findings
    └── ...
```

**Workspace Isolation Model:**

Each test run that targets a corpus project:
1. `WorkspaceManager` uses Jujutsu to create an isolated workspace: `jj workspace add test-run-{id}`
2. Test runs in the isolated workspace (hooks, artifacts, observations don't pollute the committed state)
3. After test: `jj workspace forget test-run-{id}` cleans up
4. Rollback: `jj op restore` reverts to any previous state if needed
5. Committed fixtures never change during test runs — isolation is guaranteed

**Multi-workspace strategy:** There is NO LIMIT on how many workspaces can be created from one corpus project. A single project can spawn workspaces for:
- Different workflow tests (single-agent audit vs team debate vs tool integration)
- Different scenario configurations (blind mode, with/without vulndocs, shuffled order)
- Parallel test runs (N trials simultaneously for pass@k measurement)
- Different stages of the pipeline (build-kg only, pattern query only, full audit)

**Manual + generated scenarios coexist:** The corpus provides the Solidity PROJECTS. The SCENARIOS (YAML files defining prompts, expected behaviors, graders) can be:
- Auto-generated by the generation agent alongside the project
- Manually crafted for specific test objectives (e.g., "test if attacker agent queries the graph before concluding")
- Reused across multiple projects (same scenario template, different corpus project)
This separation means we can create many more test scenarios cheaply without needing to generate new Solidity projects for each one.

**Quality Requirements:**

- Every project compiles with `solc 0.8.x` (both vulnerable and safe variants)
- **Every project (except false-positive controls) contains 5-10 distinct vulnerabilities from our pattern catalog**
- Ground truth references actual function names and line ranges in the generated code
- Obfuscation is non-trivial: a human reviewer shouldn't immediately spot the vulnerability category from names alone
- Multi-pattern projects have realistic inter-function data flow (not just independent vulnerabilities in separate functions)
- Safe variants are genuinely safe (not just commented-out vulnerabilities)
- Project structure looks like a real DeFi codebase (interfaces, libraries, imports, events, custom errors)

**Coverage Validation:**

After corpus generation, run the vulndocs coverage audit:
- All 5 major vulnerability categories (access-control, reentrancy, oracle, dos, logic) have at least 2 projects
- All 3 adversarial categories (A, B, C) have at least 3 projects each
- At least 3 false-positive control projects exist
- **Total pattern coverage: ≥75 unique patterns across all projects** (from 466+ available) — achievable with 5-10 per project across 15 non-FP projects
- Every project (except FP controls) has ≥5 distinct vulnerability patterns

Location: `examples/testing/corpus/`

**Exit gate:** 15-20 projects committed as Jujutsu fixtures. All compile. **Every non-FP project contains 5-10 vulnerabilities from our pattern catalog.** Ground truth validated. All 3 adversarial categories represented. False-positive controls included. ≥75 unique patterns covered across corpus. Coverage audit passes minimum thresholds. Workspace isolation via Jujutsu demonstrated (create workspace, run test, forget workspace).

---

### 3.1b-07: Infrastructure Validation Smoke Test (Wave 5)

**Depends on 3.1b-02 through 3.1b-06b — all prior plans must be complete.**

**A single end-to-end path through every infrastructure component:**

1. **Harness** (3.1b-04): Load a health-check scenario from YAML
2. **Native CLI**: Spawn Claude Code session via `claude --print -p`
3. **Hooks** (3.1b-03): `log_session.py` fires on session Stop event
4. **Transcript capture**: Session produces a transcript
5. **Parser** (3.1b-02): `TranscriptParser` extracts `ToolCall` + `BSKGQuery` objects
6. **Corpus** (3.1b-06b): One corpus project compiles and has valid ground-truth.yaml
7. **Scenario DSL** (3.1b-05): Grader scores the captured output
8. **Workspace isolation**: Jujutsu workspace created, test runs in isolation, workspace cleaned up

**Works WITHOUT Companion.** If Companion is available (Wave 4), run an additional variant proving multi-turn automation.

**What this validates:**
- All non-Companion infrastructure components are installed, configured, and interoperable
- Data flows: CLI → harness → hooks → parser → grader → corpus
- At least one corpus project is valid

**What this does NOT validate:**
- Full test coverage (3.1c's job)
- Agent behavioral correctness (3.1c-10)
- Multi-agent team workflows (3.1c-11)
- Regression baselines (3.1c-12)

Location: `tests/workflow_harness/test_infrastructure_smoke.py`

**Exit gate:** Single smoke test passes. All non-Companion infrastructure exercised. Transcript parsed with at least 1 ToolCall extracted. Hook output exists in `.vrs/observations/`. Corpus project compiles.

---

### 3.1b-01: Install Companion Bridge (Wave 4 — Optional)

**NICE-TO-HAVE. Zero blocking 3.1c consumers. Only useful for 3.1c-12 regression baseline.**

- Install `claude-code-controller` npm package
- Create Python bridge: `httpx` client for REST API
- Verify REST API endpoints: session CRUD, agent CRUD, task CRUD
- Smoke tests: single agent + team spawn

**Fallback if deferred:** 3.1c-12 uses `claude --print -p` for N-trial runs. Less capable (no multi-turn memory) but functional for basic regression.

Location: `tests/workflow_harness/`

**Exit gate:** Companion bridge importable, REST+WS verified (if executed).

---

### 3.1b-08: 3.1c API Contract Design Review (Wave 0 — FIRST)

**No plan dependencies. Execute BEFORE all other plans.**

**Front-load the 3.1c integration contract design to prevent backtracking during implementation.**

Phase 3.1b's exit gate requires 10+ API contracts for 3.1c readiness. If any contract is under-specified during implementation, 3.1c planning will hit gaps and require costly backtracking into 3.1b. This plan resolves that risk by producing explicit type signatures for every contract BEFORE implementation begins.

**Deliverables:**

1. **API Contract Specification Document** — Type signatures, method signatures, dataclass fields for ALL 3.1c-facing APIs:
   - `TranscriptParser` extension API (`get_tool_calls`, `get_bskg_queries`, `get_raw_messages`, `get_message_at`, `get_messages_between`)
   - `ToolCall` full field set (6 fields including `timestamp`, `duration_ms`)
   - `BSKGQuery` dataclass (all fields + extraction heuristics)
   - `TeamObservation` + `AgentObservation` dataclasses
   - `OutputCollector` API (`collect()`, `summary()`, `CollectedOutput` fields)
   - `EvaluationGuidance` dataclass (`reasoning_questions`, `hooks_if_failed`, check flags)
   - `WorkspaceManager.install_hooks()` signature (N hooks, event type mapping)
   - `.vrs/observations/` directory convention (file naming, JSONL schema)
   - Scenario DSL `evaluation:` and `evaluation_guidance:` block schemas
   - SendMessage capture format (full body, metadata, agent ID)
   - Jujutsu workspace API (`create_workspace`, `forget_workspace`, `rollback`, `list_workspaces`)
   - Debrief research findings format

2. **Integration Test Stubs** — One test stub per API contract verifying the type signature exists and is importable. These become real tests during implementation plans.

3. **3.1c Dependency Matrix** — Explicit mapping: which 3.1c plan consumes which 3.1b API contract, with version/field requirements.

**Process:** 2-hour focused design session. Read all 3.1c plan descriptions, extract every reference to 3.1b deliverables, produce concrete Python type signatures. Review against 3.1c context.md integration contracts section.

Location: `.planning/phases/3.1b-workflow-testing-harness/api-contracts/`, `tests/workflow_harness/test_api_contracts_stub.py`

**Exit gate:** Every 3.1c-facing API has an explicit Python type signature. Dependency matrix maps each 3.1c plan to its required contracts. Integration test stubs exist and are importable (they fail until implementation, which is correct).

---

## Phase 3.1c Infrastructure Readiness

Phase 3.1c depends DIRECTLY on 3.1b's deliverables. Key integration contracts:

### a) Hook Registration Architecture (3.1b-03 → 3.1c)

`WorkspaceManager.install_hooks()` must accept N hooks per event type. 3.1c adds 5+ hooks: `PreToolUse`, `PostToolUse`, `SubagentStart`, `SubagentStop`, `Stop`, `SessionStart`. Output directory: `.vrs/observations/`.

### b) Transcript Parser API Contract (3.1b-02 → 3.1c)

3.1c extends the parser with:
- `get_text_between_tools()` — reasoning text between tool calls
- `get_debrief_response()` — structured debrief responses
- Graph-specific tool call extraction via `BSKGQuery`

3.1b-02 ensures: `ToolCall` has all 6 fields, `_records` accessible, `BSKGQuery` extraction works, `TeamObservation` links transcripts to events.

### c) Scenario DSL Evaluation Hook (3.1b-05 → 3.1c)

The `evaluation:` and `post_run_hooks:` fields are parsed and preserved by the scenario loader. 3.1c implements the execution logic.

### d) Modes and Team Configuration (3.1b-05 → 3.1c)

`modes: [single, team]` enables any scenario to run as single-agent OR multi-agent team. `TeamConfig` specifies roles, model, and team-specific ground truth. 3.1c uses this for orchestration comparison tests.

**Already implemented:** `ScenarioConfig.modes`, `ScenarioConfig.team_config`, `TestScenario.modes`, `TestScenario.team_config`, `TestScenario.get_team_evaluation_questions()`.

### e) Failure Classification (3.1b → 3.1c)

`ClaudeCodeResult.failure_notes: str` provides free-text failure classification. 3.1c-12 may need structured classification; the cost of building that is deferred to 3.1c when data patterns emerge.

### f) Debrief-Ready Agent Lifecycle (3.1b-04 → 3.1c)

The harness captures ALL `SendMessage` exchanges (full content). `SubagentStop` events include `agent_transcript_path`. 3.1c uses this for interactive debrief protocol.

### g) Capability vs Evaluation Contracts (3.1c)

| Aspect | Capability Contracts (3.1c-09/10) | Evaluation Contracts (3.1c-06) |
|--------|---------------------------|---------------------------|
| Location | `tests/workflow_harness/contracts/` | `src/alphaswarm_sol/evaluation/contracts/` |
| Question | "Did it satisfy preconditions/postconditions?" | "How WELL did it reason?" |
| Output | Binary pass/fail | Scored dimensions (0-1) |

---

## Integration Into Package

```
.planning/phases/3.1b-workflow-testing-harness/
└── api-contracts/                        # 3.1c API contract specs (3.1b-08)

tests/workflow_harness/                   # Testing infrastructure
├── lib/
│   ├── transcript_parser.py              # TranscriptParser + ToolCall + BSKGQuery
│   ├── output_collector.py               # OutputCollector + TeamObservation + CollectedOutput
│   ├── workspace.py                      # WorkspaceManager with install_hooks() + Jujutsu isolation
│   ├── assertions.py                     # Test assertions
│   └── controller_events.py             # EventStream + ControllerEvent
├── hooks/
│   └── log_session.py                    # Initial SubagentStop/Stop hook
├── graders/                              # Grader implementations
├── scenarios/                            # YAML scenario definitions
├── test_api_contracts_stub.py            # Integration test stubs from 3.1b-08
├── test_transcript_parser.py
├── test_hooks_infrastructure.py
└── test_infrastructure_smoke.py          # End-to-end validation

.claude/agents/
└── corpus-generator.md                   # Opus-powered subagent: generates adversarial Solidity projects

examples/testing/
├── guidelines/                           # Corpus generation system (3.1b-06a)
│   ├── pattern-catalog.yaml             # All 466+ patterns as generation-ready specs
│   ├── adversarial-taxonomy.md          # 3 categories, 5+ techniques each
│   ├── combination-rules.yaml           # Multi-pattern compatibility rules
│   └── generation-pipeline.md           # 8-step generation process
├── scripts/
│   ├── generate_project.py              # Orchestration wrapper for generation agent
│   └── audit-vulndocs-coverage.py       # Coverage audit script
└── corpus/                              # Committed adversarial projects (3.1b-06b)
    ├── defi-lending-protocol-01/        # Each has 5-10 vulns, Jujutsu-managed
    │   ├── .jj/
    │   ├── contracts/*.sol              # Vulnerable + safe variants
    │   ├── ground-truth.yaml            # 5-10 expected findings + reasoning chains
    │   ├── project-manifest.yaml        # Patterns, obfuscation, tier metadata
    │   └── build-verification.sh
    ├── governance-staking-02/
    ├── safe-complex-governance/          # False-positive control (0 vulns)
    ├── stress-test-max-obfuscation-01/  # 8-10 vulns, all obfuscated
    └── ... (15-20 total, ≥75 unique patterns)
```

## Dependencies

- **Phase 3.1** (Testing Audit & Cleanup) — Clean foundation, dead code removed
- **`pytest-asyncio`** (pip) — Already in dev dependencies
- **Solidity compiler** (`solc 0.8.x`) — For corpus compilation verification
- **Jujutsu** (`jj`) — Already used in project for VCS; required for workspace isolation and corpus fixtures
- **Optional:** `claude-code-controller` (npm) — Wave 4 only

**No dependency on Phase 3.2, Phase 4, or any unbuilt feature.**

## Success Criteria

1. 3.1c API contracts fully specified with Python type signatures before implementation begins
2. `TranscriptParser` extended with `BSKGQuery` extraction and `TeamObservation` model
3. Hook infrastructure verified complete (extensible, deduplicated, `.vrs/observations/`)
4. Core harness runs team lifecycle with native Agent Teams + Jujutsu workspace isolation (no Companion required)
5. YAML scenario DSL with `modes`, `team_config`, `evaluation` slot, graders
6. Corpus generation system: guidelines catalog all 466+ patterns + Opus-powered agent produces compilable adversarial projects with 5-10 vulnerabilities each
7. 15-20 seed projects committed as Jujutsu fixtures, each containing 5-10 security vulnerabilities (except FP controls), ≥75 unique patterns covered, covering major categories + false-positive controls
8. Infrastructure smoke test passes — path through all non-Companion components including Jujutsu workspace isolation
9. (Optional) Companion bridge installed and verified

## Exit Gate (3.1c Readiness)

3.1b is complete and 3.1c can begin when:

- **API contracts:** All 3.1c-facing APIs have explicit Python type signatures with dependency matrix
- **TranscriptParser API:** `BSKGQuery` extraction works, `TeamObservation` links transcripts to events, `ToolCall` has all 6 fields, `_records` accessible
- **Hook registration:** `install_hooks()` supports N hooks per event, `_ensure_hook()` deduplicates
- **Observation directory:** `.vrs/observations/` created during workspace setup
- **Scenario DSL:** `modes` + `team_config` fields work, `evaluation:` slot accepted
- **Corpus generation system:** Pattern catalog covers 466+ patterns, adversarial taxonomy covers 3 categories with 5+ techniques each, Opus-powered generation agent produces compilable adversarial projects with 5-10 vulnerabilities each
- **Seed corpus:** 15-20 projects committed as Jujutsu fixtures, each with 5-10 vulnerabilities (except FP controls), ≥75 unique patterns covered, all compile, ground truth validated
- **Workspace isolation:** Jujutsu-based isolation demonstrated (create workspace, run test, forget workspace, rollback)
- **Infrastructure smoke:** Health-check runs through harness → hooks → parser → grader → corpus → Jujutsu workspace
- **Optional:** Companion bridge available for multi-turn automation

## Relationship to Other Phases

| Phase | Relationship |
|-------|-------------|
| **3.1** (Testing Cleanup) | Prerequisite — provides clean foundation |
| **3.1b** (This Phase) | Infrastructure: parser, hooks, harness, DSL, corpus |
| **3.1c** (Evaluation Framework) | THE testing framework — extends 3.1b with evaluation, reasoning, debrief, regression |
| **3.2** (First Audit) | Uses harness for E2E regression |
| **4** (Agent Teams) | Uses harness for behavioral verification |

## Research Sources

- Gap resolution archives: `.archive/gap-resolutions/` (GAP-01 through GAP-11 + POST-FIX-CRITIQUE)
- 4 parallel research agents analyzed: phase ordering, agent/skill inventory, controller vs native CLI, pattern inventory
- Companion bridge deprioritization: 3.1c exit gate shows NICE-TO-HAVE status
- Adversarial corpus strategy: 3 categories (name obfuscation, protocol complexity, honeypot inversions)
- Pattern-derived generation: 8-step pipeline from 466+ vulndocs patterns
- Anthropic eval guidance: tasks + trials + graders, grade outcomes not paths, pass@k metrics
- User feedback (2026-02-12): Corpus is a hostile generation SYSTEM, not static fixtures. Committed fixtures first (Jujutsu), dynamic generation contemplated. Claude Code subagent for generation. Projects should BREAK the engine, not test happy path. Multiple Jujutsu workspaces per scenario. Scenarios can be manually crafted, not only framework-generated.
