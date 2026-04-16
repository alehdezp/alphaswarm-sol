# Claude Code Testing Framework

**Version:** 2.0
**Created:** 2026-01-30
**Updated:** 2026-02-11
**Purpose:** Define the architecture and evolution of agentic self-testing using Claude Code

---

## VISION

Test Claude Code using Claude Code. This is the only way to properly validate an agentic system.

The testing framework is centered on the evaluation pipeline -- not just execution and transcript capture, but intelligent assessment of reasoning quality, continuous improvement, and regression detection.

```
Workflow Run
  -> Hooks observe (selective per evaluation contract, JSONL)
  -> Evaluation Contract loaded (smart selection)
  -> Capability Contract checks (3.1b: pass/fail)
  -> Deterministic Checks
  -> Graph Value Score (if applicable)
  -> LLM Reasoning Evaluator (Claude Code subagent, per-category)
  -> Debrief (approach TBD — research required)
  -> EvaluationResult produced
  -> Improvement Loop (sandbox, compare, regress?)
  -> Human Report (if can't auto-fix)
```

```
+---------------------------------------------------------------------------+
|                     AGENTIC SELF-TESTING ARCHITECTURE                      |
+-----+---------------------------------------------------------------------+
|                                                                            |
|  Human Developer                                                           |
|       |                                                                    |
|       | invokes                                                            |
|       v                                                                    |
|  +-------------------+                                                     |
|  | Controller        |  Your active Claude Code session                    |
|  | Claude Code       |  Uses claude-code-controller for session control    |
|  +--------+----------+                                                     |
|           |                                                                |
|           | orchestrates via /vrs-self-test                                |
|           | uses claude-code-controller commands                           |
|           v                                                                |
|  +---------------------------------------------------------------+        |
|  | Isolated claude-code-agent-teams Session                       |        |
|  | +---------------------------------------------------------+   |        |
|  | | Subject Claude Code                                      |   |        |
|  | | - Runs with --dangerously-skip-permissions               |   |        |
|  | | - Executes actual workflows (/vrs-audit, /vrs-investigate)|  |        |
|  | | - Makes real Anthropic API calls                         |   |        |
|  | | - Produces real findings, real tokens, real duration      |   |        |
|  | | - Evaluation-contract-selected hooks observe relevant events |   |        |
|  | +---------------------------------------------------------+   |        |
|  +---------------------------------------------------------------+        |
|           |                                                                |
|           | hooks write to .vrs/observations/{session_id}.jsonl            |
|           | output captured via claude-code-controller capture              |
|           v                                                                |
|  +-------------------+                                                     |
|  | Evaluation        |  Intelligent assessment, not just transcript diff   |
|  | Pipeline          |  Observation Parser -> GVS -> Reasoning Evaluator   |
|  |                   |  -> Debrief -> EvaluationResult                     |
|  +--------+----------+                                                     |
|           |                                                                |
|           | identifies weaknesses                                          |
|           v                                                                |
|  +-------------------+                                                     |
|  | Improvement Loop  |  Sandbox copy -> modify prompt -> re-run -> compare |
|  | (Safe Sandbox)    |  Regression detection -> human report               |
|  +-------------------+                                                     |
|                                                                            |
+----------------------------------------------------------------------------+
```

---

## EVALUATION PIPELINE (Phase 3.1c)

This is the primary architecture of the testing framework. The evaluation pipeline transforms raw workflow runs into actionable quality assessments and drives continuous improvement.

### Overview

Phase 3.1c extends the testing framework with intelligent evaluation capabilities that go beyond mechanical assertions. Instead of only checking "did the agent call the right tools?", the framework evaluates "did the agent REASON correctly?"

### Pipeline Stages

```
Workflow Run -> Hooks Observe -> Transcript Captured -> Evaluation Contract Loaded
    -> Deterministic Checks -> Graph Value Score -> LLM Reasoning Evaluator
    -> Improvement Suggestions -> Safe Sandbox Testing -> Regression Detection
```

### Smart Dynamic Selection

Not every workflow needs every check. Each workflow's evaluation contract (YAML) declares which components apply:

| Component | Investigation | Tool Integration | Orchestration | Support |
|-----------|:---:|:---:|:---:|:---:|
| Graph Value Score | YES | NO | MAYBE | NO |
| LLM Reasoning Evaluator | YES (full) | YES (focused) | YES (full) | LITE |
| Interactive Debrief | NO | NO | YES | NO |
| Blocking Debrief | YES | NO | YES | NO |

**Hook selection is per evaluation contract.** Tests only enable the hooks they need. Performance-sensitive tests skip unnecessary hooks.

### Evaluation Contracts

Per-workflow YAML files at `tests/workflow_harness/contracts/workflows/` (defined in plan 3.1c-06):
- Define what "good performance" looks like for each workflow
- Specify which hooks, checks, and evaluation dimensions apply
- Set minimum scores for each scored dimension
- Declare ground truth mode (full, partial, none)

### Safe Sandboxing Rule

**Production prompts are NEVER modified during testing.** When experimenting with prompt improvements:
1. Copy production `.md` file into test project's `.claude/` folder
2. Modify ONLY the copy
3. Re-run and compare scores
4. If improved -> human approves -> production `.md` updated manually

### Continuous Improvement Loop

```
Test -> Evaluate -> Identify Failures -> Improve (sandbox) -> Re-test -> Detect Regression -> Report
```

The improvement loop is augmented by the intelligence layer:

- **Coverage radar** feeds gap priorities into the scenario synthesis engine, which generates new test scenarios targeting cold cells (zero-coverage areas). Gap prioritization weights vulnerability severity and skill claims.
- **Scenario synthesis** analyzes skill/agent prompt text to discover untested behavioral claims and generates targeted scenarios without manual authorship.
- **Self-healing contracts** monitor evaluation dimension distributions. When a dimension consistently produces zero-variance or trivially-passing scores, the contract is flagged as stale and a replacement is proposed.
- **Adaptive tier promotion** applies when a workflow sustains low scores or persistent meta-evaluation disagreement: the tier is automatically escalated to increase evaluation rigor. Tier demotion (reducing rigor) requires explicit human approval.

### Integration with Infrastructure

- **Hooks:** Supplement existing `log_session.py` with observation hooks (PreToolUse, PostToolUse, SubagentStart, SubagentStop, Stop, SessionStart)
- **Assertions:** Extend existing categories with Category 8 (Reasoning score assertions)
- **TranscriptParser:** Extended with `get_debrief_response()`, `get_text_between_tools()`, `get_graph_queries()`
- **WorkspaceManager:** Extended hook installation for observation hooks via `install_hooks(extra_hooks=...)`

---

## PHASE ARCHITECTURE

The testing framework is split across two phases with distinct responsibilities:

### Phase 3.1b: Testing Infrastructure Foundation (SUPPORTING)

Phase 3.1b provides the plumbing that the evaluation framework depends on:

- **Controller + Python bridge** -- claude-code-controller for session management
- **TranscriptParser + data model** -- parsing raw transcripts into structured tool call sequences
- **Hook registration architecture** -- `.claude/settings.json` hook registration, `_ensure_hook()` deduplication
- **Core harness** -- WorkspaceManager, scenario runner, evidence collection
- **Scenario DSL** -- YAML scenario definitions with tasks, trials, graders
- **Test project corpus** -- 10 curated scenarios + dynamic generation guidelines for 466 patterns
- **Capability contracts** -- Binary pass/fail precondition and postcondition checks
- **Regression baseline** -- pass@k metrics as starting point

### Phase 3.1c: Smart Adaptive Testing Framework (PRIMARY)

Phase 3.1c IS the testing framework. It provides two tiers of capability:

**Tier 1 — Evaluation Engine (deterministic pipeline):**

- **Observation hooks** -- 5 hooks (selective per evaluation contract) + shared JSONL writer
- **Assessment data structures** -- ReasoningAssessment, GraphValueScore, EvaluationResult
- **Observation parser** -- Mechanical extraction of metrics from JSONL observation files
- **Graph value scorer** -- Mechanical scoring of graph query quality and checkbox detection
- **Debrief protocol** -- Agent debrief approach (RESEARCH REQUIRED — mechanism TBD, see 3.1c-05)
- **Evaluation contracts** -- 24 per-workflow YAML files defining "good performance"
- **Reasoning evaluator** -- Claude Code subagent evaluation (via Task tool, not direct API) with 4 category-specific prompt templates
- **Evaluation runner** -- Full pipeline orchestration (parse -> score -> evaluate -> result)
- **Improvement loop** -- Safe sandbox prompt experimentation with regression detection
- **Metaprompting feedback** -- Convert evaluation failures into targeted prompt improvements
- **All skill/agent/orchestrator tests** -- Every test that needs reasoning evaluation lives here

**Tier 2 — Evaluation Intelligence (adaptive layer, 10 sub-modules):**

The intelligence layer sits alongside the evaluation engine and activates incrementally as run data accumulates. Its sub-modules:

1. **Scenario synthesis engine** -- Analyzes shipped skill/agent prompts, cross-references against the test corpus, identifies untested claims, and generates new test scenarios targeting coverage gaps
2. **Coverage radar** -- Live heat map tracking tested vs untested space across 4 axes (vulnerability class, semantic operation, reasoning skill, graph query pattern). Cold cells prioritized by severity
3. **Adaptive tier management** -- Tiers are dynamic, not static. Auto-promote on sustained low scores or persistent meta-evaluation disagreement. Demotion requires human approval
4. **Behavioral fingerprinting** -- Detects behavioral drift across runs by comparing reasoning move profiles and output distributions
5. **Self-healing evaluation contracts** -- Statistical detection of stale, trivial, or unreasonable evaluation dimensions. Proposes contract updates when dimensions consistently produce zero-variance scores
6. **Cross-workflow learning** -- Propagates evaluation insights across related workflows (e.g., a reasoning weakness found in /vrs-investigate informs /vrs-audit evaluation)
7. **Reasoning chain decomposition** -- Scores 7 discrete reasoning moves (HYPOTHESIS_FORMATION, QUERY_FORMULATION, RESULT_INTERPRETATION, EVIDENCE_INTEGRATION, CONTRADICTION_HANDLING, CONCLUSION_SYNTHESIS, SELF_CRITIQUE) independently
8. **Evaluator self-improvement** -- When meta-evaluation detects persistent inter-rater disagreement, generates evaluator prompt variants and selects the best. Bounded to 3 iterations per dimension, human approval required
9. **Compositional stress testing** -- 8 non-standard agent compositions tested (missing agent x3, degraded x3, doubled, unusual order). Keystone analysis identifies most impactful agent
10. **Gap-driven synthesis loop** -- Closed-loop integration of coverage radar with scenario synthesis for automatic gap filling

---

## MANDATORY: claude-code-controller Usage

**All claude-code-agent-teams operations MUST use the claude-code-controller command, not raw claude-code-agent-teams commands.**

**Full documentation:** `.planning/testing/rules/claude-code-controller-REFERENCE.md` and `.planning/testing/rules/canonical/claude-code-controller-instructions.md`

### claude-code-controller Command Reference

| Operation | claude-code-controller Command | NOT Raw claude-code-agent-teams |
|-----------|------------------|--------------|
| Launch pane | `claude-code-controller launch "zsh"` | ~~`claude-code-agent-teams new-session -d -s name`~~ |
| Send command | `claude-code-controller send "cmd" --pane=0:1.2` | ~~`claude-code-agent-teams send-keys -t name 'cmd' Enter`~~ |
| Wait for idle | `claude-code-controller wait_idle --pane=0:1.2 --idle-time=10.0` | ~~No equivalent~~ |
| Capture output | `claude-code-controller capture --pane=0:1.2` | ~~`claude-code-agent-teams capture-pane -t name -p`~~ |
| Kill demo pane | `claude-code-controller kill --pane=0:1.2` (only for current `vrs-demo-*` run) | ~~`claude-code-agent-teams kill-session -t name`~~ |

### Validated Workflow

```bash
# 1. Launch a new claude-code-agent-teams pane with zsh
claude-code-controller launch "zsh"
# Returns: pane_id (e.g., "0:1.2")

# 2. Change to working directory
claude-code-controller send "cd /path/to/project" --pane=0:1.2

# 3. Wait for shell to be idle
claude-code-controller wait_idle --pane=0:1.2 --idle-time=2.0

# 4. Launch Claude Code
claude-code-controller send "claude" --pane=0:1.2

# 5. Wait for Claude to be ready (longer timeout)
claude-code-controller wait_idle --pane=0:1.2 --idle-time=10.0 --timeout=30

# 6. Send the actual prompt
claude-code-controller send "Your prompt here" --pane=0:1.2

# 7. Wait for Claude to finish processing
claude-code-controller wait_idle --pane=0:1.2 --idle-time=10.0 --timeout=120

# 8. Capture the response
claude-code-controller capture --pane=0:1.2 --output=.vrs/testing/runs/<run_id>/transcript.txt
## Local mode note
If claude-code-controller reports MODE: LOCAL, redirect output instead:
claude-code-controller capture --pane=0:1.2 > .vrs/testing/runs/<run_id>/transcript.txt

# 9. Exit Claude
claude-code-controller send "/exit" --pane=0:1.2

# 10. Kill the pane
claude-code-controller kill --pane=0:1.2
```

---

## INFRASTRUCTURE COMPONENTS (Phase 3.1b)

These components provide the mechanical foundation that the evaluation pipeline (Phase 3.1c) builds upon.

### Component 1: Testing Skills

**Skill Hierarchy:**
```
/vrs-self-test (orchestrator)
    |
    +-- /vrs-workflow-test (execution)
    |       |
    |       +-- /vrs-claude-code-agent-teams-runner (command execution)
    |       +-- vrs-claude-controller (Claude Code automation)
    |
    +-- /vrs-evaluate-workflow (evaluation)
    |       |
    |       +-- vrs-workflow-evaluator (judgment)
    |
    +-- vrs-self-improver (fix simple errors)
```

All agent-related testing must use this hierarchy inside the dedicated demo session.

### Component 2: Ground Truth Management

**External Sources:**
```
.vrs/corpus/
+-- contracts/              # Actual contract files
|   +-- code4rena/
|   +-- smartbugs/
|   +-- custom/
+-- ground-truth/           # Labels with provenance
|   +-- code4rena/
|   +-- smartbugs/
|   +-- provenance.yaml
+-- corpus.db               # SQLite index
```

### Component 3: Criteria System

Criteria files define pass/fail for workflow tests:

```yaml
# .vrs/testing/criteria/full-audit.yaml
name: full-audit
expected_patterns:
  - regex: "Phase 1.*Build.*graph|Building knowledge graph"
    required: true
forbidden_patterns:
  - regex: "Error:|Traceback|FAIL"
    severity: error
expected_files:
  - path: ".vrs/graphs/*.toon"
    required: true
custom_validators:
  has_evidence: "lambda t: ('Evidence:' in t, 'Missing evidence section')"
expected_duration:
  min_seconds: 30
  max_seconds: 600
```

**Drift detection (optional):**
- Define a baseline transcript per workflow.
- Compare key markers and output structure across runs.
- Flag deviations as `DRIFT` in evaluation reports.

---

## FRAMEWORK PRINCIPLES

Principles 1-5 are the evaluation-focused principles defined in `TESTING-PHILOSOPHY.md`. Principles 6-9 below are the infrastructure principles that govern how the testing framework operates mechanically:

6. **Real Execution Only** - No simulations for validation
7. **External Ground Truth** - Never test against your own output
8. **Measured Metrics** - Tokens and duration from actual API
9. **Honest Reporting** - Document limitations, expect imperfection
10. **Isolated Testing** - Subject separate from controller and isolated in a demo session
11. **Transcript Preservation** - Full audit trail
12. **claude-code-controller Only** - No raw claude-code-agent-teams commands
13. **Ground Truth Isolation** - Subject sessions must not access ground truth files
14. **Sequential Execution for Agent Teams** - Plans that spawn Agent Teams must execute in top-level Claude Code sessions, not via subagents. Agent Teams cannot be spawned from subagents. Wave parallelism in plan dependencies is for planning only — execution is strictly sequential
15. **Agent Team Context Isolation** - Teammates MUST be spawned with controlled, minimal context. Full project CLAUDE.md context makes evaluations unrealistic. See Agent Team Spawning Protocol below.

## Agent Team Spawning Protocol

When spawning Agent Team teammates for evaluation workflows, context must be
controlled to produce realistic test results.

### Why Context Isolation Matters

Teammates spawned at the project root inherit the full CLAUDE.md, all project
instructions, and all tool capabilities. This:
- **Bloats context**: Wastes tokens on irrelevant project planning/architecture docs
- **Makes tests unrealistic**: A real audit user has focused context, not dev context
- **Masks reasoning gaps**: Agent performs well because it has answers pre-loaded

### How to Spawn Teammates

Use `Task(team_name=...)` to create named teammates in an Agent Team:

```python
# 1. Create the team (once, from orchestrator)
TeamCreate(team_name="eval-core-wave", description="Core tier evaluations")

# 2. Create tasks in the shared task list
TaskCreate(subject="Evaluate skill-vrs-investigate on Contract.sol", ...)

# 3. Spawn named teammates with FOCUSED context
Task(
    team_name="eval-core-wave",
    name="investigator-1",
    subagent_type="general-purpose",
    prompt="""You are evaluating a single Solidity contract for security vulnerabilities.

TOOLS YOU MUST USE:
- `uv run alphaswarm build-kg {contract_path}` — build knowledge graph
- `uv run alphaswarm query "{semantic query}"` — query the graph
- `Read` — read the contract source file ONLY

TOOLS YOU MUST NOT USE:
- Do NOT read CLAUDE.md, .planning/*, docs/*, or any project files
- Do NOT read vulndocs/ or other VulnDocs patterns
- Do NOT run git commands or modify any files outside .vrs/observations/

YOUR ONLY GOAL: Build the BSKG, run 3+ queries, identify vulnerabilities,
write structured debrief.json and exit_report.json.

Check TaskList for your assigned task. Claim it, execute, mark complete."""
)
```

### Context Control Checklist

- [ ] Prompt specifies ONLY the tools needed (build-kg, query, Read)
- [ ] Prompt explicitly prohibits reading project context files (CLAUDE.md, .planning/)
- [ ] Prompt does NOT reference project architecture, patterns DB, or dev workflows
- [ ] Contract path and output path are the ONLY file references
- [ ] Teammate has no way to access ground truth or evaluation contracts

### Known Failure Modes (discovered Plan 11, 2026-02-27)

**F1: Binary Staleness — Auto-update kills Agent Teams spawns**
Claude Code auto-updates delete old version binaries. If a session started on
version X but auto-update installs Y and removes X, ALL Agent Teams spawns fail:
`env: .../versions/X: No such file or directory`. Built-in tools (Glob, Grep)
also degrade. **Preflight**: Before any TeamCreate, run
`ls ~/.local/share/claude/versions/` and verify the session's binary version
still exists. If stale, restart the session. Start Agent Teams work in FRESH
sessions only.

**F2: Context Isolation Violation — Teammates inherit full project context**
Spawning teammates at project root without explicit context control means they
inherit full CLAUDE.md — all project internals, testing framework, planning docs.
This makes evaluations unrealistically easy (agents "know" what to find).
**Prevention**: ALWAYS use the Context Control Checklist above. Explicitly
restrict tools and prohibit reading project files in the prompt. The `isolation:
"worktree"` parameter is recommended for strict isolation.

### Task() Subagent vs Agent Teams — Critical Distinction

| | Task() Subagent | Agent Teams |
|---|---|---|
| Created with | `Task(subagent_type=...)` | `TeamCreate` + `Task(team_name=...)` |
| Coordination | None — isolated leaf worker | Shared TaskList + SendMessage |
| Can spawn sub-agents | No | Yes |
| Named | No (anonymous) | Yes (e.g., "investigator-1") |
| Use for evaluations | Never claim as "Agent Teams" | Required for real evaluations |

## Demo Session Policy

- Every workflow run must use a dedicated demo session label.
- Standard label: `vrs-demo-{workflow}-{timestamp}`.
- Record the label and the pane ID in the run metadata or transcript header.
- Never reuse a demo session or pane across workflows.
- claude-code-controller runs MUST be launched from a shell/session that is separate from your active development claude-code-agent-teams session.
- Never target or kill panes outside the current `vrs-demo-*` run.

## Parallel Run Policy

- Use a unique demo session label per workflow run.
- Use separate jj workspaces or run directories to avoid `.vrs/` collisions.
- Validate pane uniqueness with `claude-code-controller status` or `claude-code-controller list_panes`.
- If stale panes exist, run `claude-code-controller cleanup` before starting new runs.

---

## Integration with Validation Rules

This framework implements the requirements in `.planning/testing/rules/canonical/VALIDATION-RULES.md`:

- Rule A4: claude-code-agent-teams-based execution -> claude-code-controller
- Rule D1: Use existing testing skills -> /vrs-workflow-test, /vrs-self-test
- Rule D2: Transcript capture required -> claude-code-controller capture
- Rule D3: Isolation required -> Separate claude-code-agent-teams pane via claude-code-controller

---

## When to Use This Framework

- Phase 7.3.* validation plans (GA testing)
- Any plan requiring real-world workflow validation
- Integration testing of Claude Code orchestration
- A/B comparison tests (Solo vs Swarm)
- Reasoning quality assessment of skills, agents, and orchestration flows

**Reference:** `.planning/testing/rules/canonical/TESTING-PHILOSOPHY.md` for core reasoning principles.

---

## Phase-Type Taxonomy and Testing Gates

Every phase CONTEXT.md must include a Testing Gate section declaring phase type
and testing requirements. See:
- Phase-type taxonomy: `.planning/testing/rules/canonical/PHASE-TYPE-TAXONOMY.md`
- Testing gate template: `.planning/testing/templates/TESTING-GATE-TEMPLATE.md`
- Enforcement: via plan task done criteria per `PLAN-PHASE-GOVERNANCE.md`
