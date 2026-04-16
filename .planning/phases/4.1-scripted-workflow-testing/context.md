# Phase 4.1: Workflow Test Expansion

## Goal

Expand the workflow testing harness (built in Phase 3.1b) with full audit pipeline scenarios, multi-agent debate scenarios, agent behavioral verification with hook enforcement, and complete coverage verification — using features delivered by Phase 3.2 (working audit) and Phase 4 (agent teams).

## What Changed

Phase 4.1 was originally planned as a 6-plan phase covering the full harness build + test expansion. After reordering analysis (4 parallel research agents), the harness core was extracted into **Phase 3.1b** — because it has zero technical dependency on Phases 3.2 or 4, and testing infrastructure should come before the features it tests.

**Original Phase 4.1 (6 plans):**
- Plans 01-04: Install controller, build harness, scenario DSL, health-check test → **Moved to Phase 3.1b**
- Plans 05-06: Audit pipeline test, reliability verification → **Remain here (expanded)**

**Phase 3.1b delivers:** Controller installed, 10 curated scenarios + dynamic generation guidelines, core harness, scenario DSL, 30 skill tests, 21 agent tests, orchestrator flow test, regression baseline.

**This phase adds:** Deep multi-agent validation, hook-enforced behavioral constraints, self-improving loops, and full coverage verification across all 30 skills + 21 agents.

## Architecture Context

**Claude Code IS the orchestrator.** It spawns teams, monitors behavior, validates alignment:

```
┌──────────────────────────────────────────────────────────────┐
│  pytest / claude-code-controller (programmatic trigger)       │
│  - Runs scenarios from YAML definitions                       │
│  - Captures full team lifecycle via REST API                  │
│  - Compares outcomes against ground truth                     │
│  - pass@k metrics across multiple trials                      │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────┐
│  Claude Code (Orchestrator in delegate mode)                  │
│  - Creates team: TeamCreate("vrs-audit-full")                │
│  - Spawns specialist attackers + defender + verifier          │
│  - Monitors DMs between agents (peer DM visibility)          │
│  - Validates: ground truth match, evidence anchoring          │
│  - Hook enforcement: command hooks deny non-compliant actions │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────┐
│  Agent Teams (real teammates)                                 │
│  - Attacker: BSKG query → hypothesis → exploit path          │
│  - Defender: independent guard search → mitigation evidence   │
│  - Verifier: synthesize only → verdict                        │
│  - All use shipped skills from shipping/                      │
│  - All follow .md behavioral constraints                      │
│  - Hook enforcement blocks non-compliant tool calls           │
└──────────────────────────────────────────────────────────────┘
```

## Dependencies

- **Phase 3.1b** (Workflow Testing Harness Core) — Controller, harness, scenario DSL, test corpus, regression baseline
- **Phase 3.2** (First Working Audit) — Working `build-kg → query → detect` pipeline
- **Phase 4** (Agent Teams Debate) — Working multi-agent debate with TeamCreate/SendMessage

## Plans (4)

### 4.1-01: Full Audit Pipeline Test

Claude Code creates audit team on known-vulnerable contract from `examples/testing/` corpus:

- Team: orchestrator (delegate mode) + specialist attackers + defender + verifier
- Target: contract with known vulnerability from ground-truth.yaml
- Pipeline: `build-kg → query → detect → Agent Teams debate → verdict`
- Validates:
  - Ground truth match (finding matches expected pattern from ground-truth.yaml)
  - Evidence anchoring (all findings reference graph node IDs)
  - All agents participated (cost > 0, tool calls > 0, transcript > 500 chars)
- Run 3x for reliability, compare across runs using comparator from 3.1b

**Exit gate:** Audit test detects ground-truth vulnerability in 2/3 runs. Evidence packets contain graph node IDs. All agents participated. Human reviews and confirms.

#### Reasoning

This plan validates the full audit pipeline — from contract ingestion to verdict — on a contract with known ground truth. Unlike Phase 3.1b-07 (basic orchestrator flow), this test exercises the COMPLETE pipeline including pattern detection, bead creation, and agent investigation. The ground truth comparison (from `examples/testing/` corpus) provides objective success criteria.

#### Expected Outputs

- Team lifecycle test in `tests/workflows/test_full_audit.py`
- Evidence packets with graph node IDs, transcript hashes, proof tokens
- Comparison report across 3 runs (timing variance, finding consistency)
- pytest result: passes 2/3 or 3/3

#### Testing Strategy

| Output | Method 1 | Method 2 |
|--------|----------|----------|
| Ground truth match | Assert finding pattern_id matches ground-truth.yaml expected | Cross-reference finding location with expected line_range |
| Evidence anchoring | Assert `graph_node_ids` list non-empty and IDs exist in built graph | Controller events show BSKG queries before conclusions |
| All agents participated | Assert 3 distinct agent transcripts with cost > 0 each | Controller events include agent:spawned (x3), task:completed (x3) |
| 2/3 reliability | Run 3x, assert >= 2 passes | Comparator shows bounded variance |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|-------------------|-------------------|-------------|
| Full pipeline executes (not just graph build) | Only build-kg runs; no pattern detection or agent investigation | Assert controller events include all pipeline stages |
| Ground truth is from corpus, not generated | Test generates its own expected findings | Assert ground-truth.yaml path matches `examples/testing/` |
| Duration realistic | Completes < 5 seconds | Assert `duration_ms > 5000` |

---

### 4.1-02: Agent Behavior Verification with Hook Enforcement

Claude Code spawns each agent role as teammate and monitors behavioral constraints via hooks:

**Attacker: graph-first rule**
- Hook: `TeammateIdle` + `TaskCompleted` — check that BSKG queries appeared before conclusions
- Controller events: verify `alphaswarm query` or `build-kg` calls precede any finding output
- Gate: BLOCK conclusion if no prior BSKG query in session (command hook)

**Defender: independent analysis**
- Hook: Monitor DMs — compute Jaccard similarity between defender and attacker query sets
- Gate: `Jaccard < 0.8` (defender must not simply copy attacker's queries)
- Verify: defender produces at least 1 unique query not in attacker's set

**Verifier: synthesis-only**
- Hook: `PreToolUse` command hook — deny `alphaswarm query`, `build-kg`, any BSKG-mutating calls
- Gate: Zero BSKG-originating tool calls from verifier
- Verify: verifier only reads existing evidence, never generates new analysis

**For each agent:**
- Run 3x for reliability
- Monitor via controller events (not just post-hoc transcript analysis)
- Hook enforcement is BLOCK mode (not log-only)

**Exit gate:** Each agent follows its documented behavioral constraints in 2/3 runs. Hook enforcement demonstrates at least 1 blocked call in verifier test.

#### Reasoning

Agent behavioral constraints are the foundation of the multi-agent debate model. Without hook-based enforcement, agents silently drift from their roles. Phase 3.1b-06 tested basic agent spawning; this plan adds ENFORCEMENT — hooks that actively block non-compliant behavior, not just observe it.

#### Expected Outputs

- Hook configurations in `.claude/settings.json` for per-role enforcement
- Per-agent behavioral compliance reports (tool call sequences, constraint violations)
- Jaccard similarity metric between attacker and defender queries
- Evidence of at least 1 blocked verifier tool call (proves enforcement works)
- pytest results: `tests/workflows/test_agent_enforcement.py` passes 2/3 per agent

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|-------------------|-------------------|-------------|
| Hooks are BLOCK mode, not log-only | Hooks log violations but allow them through | Assert hook mode is BLOCK; verify at least 1 blocked call in verifier test |
| Each agent actually executes (not stubbed) | Transcript < 500 chars or cost == 0 | Assert transcript > 500 chars, cost > 0, tool calls > 0 per agent |
| Defender is independent from attacker | Jaccard >= 0.8 between query sets | Fail test if Jaccard >= 0.8 |

---

### 4.1-03: Multi-Agent Debate Scenario

Full 3-agent structured debate via Agent Teams:

- Claude Code as lead (delegate mode), monitoring DMs between agents
- Attacker presents exploit hypothesis with evidence
- Defender presents mitigation evidence
- Verifier weighs both sides, produces verdict
- Debate on known-vulnerable contract from `examples/testing/` corpus

Validates:
- **Adversarial structure**: attacker and defender disagree on at least 1 point
- **Evidence anchoring**: every claim maps to graph node IDs
- **Verdict produced**: structured verdict with severity, confidence, evidence refs
- **Turn structure**: >= 2 turns per agent; attacker precedes defender response
- Model-based grader evaluates debate quality

**Exit gate:** Debate produces verdict with evidence. All 3 agents participate with substantive turns. Adversarial structure verified. Transcript verifiable.

#### Reasoning

The multi-agent debate is the core differentiator of AlphaSwarm.sol. Phase 3.1b-07 tested basic team lifecycle; this test validates the DEBATE PROTOCOL — structured adversarial exchange producing evidence-based verdicts. The model-based grader adds semantic evaluation beyond structural checks.

#### Expected Outputs

- Debate scenario in `tests/workflow_harness/scenarios/agent_debate.yaml`
- Debate transcript with delineated attacker, defender, verifier turns
- Verdict document with severity, confidence, evidence references
- Model-based grader evaluation of debate quality
- pytest result: `tests/workflows/test_debate.py` passes with verdict + evidence

---

### 4.1-04: Full Coverage & Regression Verification

Run curated + dynamically generated test scenarios through audit pipeline and verify complete coverage:

**Coverage matrix:** 30 skills + 21 agents × scenario × pass rate

**Convergence criteria:**
- `max_iterations`: 5 (don't loop forever)
- `plateau_threshold`: 2 consecutive runs with < 5% improvement = converged
- `target_f1`: 0.70 (not perfection — realistic for LLM-based system)

**Quality gates:**
- Exploit completeness >= 0.80 (fraction of ground-truth vulns detected)
- Evidence anchoring >= 0.90 (fraction of findings with graph node IDs)
- FP rate < 0.20 (fraction of findings on safe contracts)

**Self-improving loop (from migration research):**
1. Run scenario → capture failure
2. Analyze failure artifacts (controller events, transcripts, evidence packs)
3. Fix skill/agent/orchestrator
4. Rollback to clean committed state
5. Re-run same scenario
6. Comparator diffs run N vs run N+1
7. Continue until convergence or max iterations

**Regression baseline update:**
- Run ALL tests 3x each
- Update baseline metrics from Phase 3.1b-08
- Any degradation from 3.1b baseline → BLOCK until investigated
- Grade outcomes, not paths (per Anthropic eval guidance)

**Exit gate:** Coverage matrix complete. Quality gates pass. Self-improving loop converges. Regression baseline updated without degradation.

#### Reasoning

This plan is the phase-level EXIT GATE that proves the entire system works at scale. Individual tests prove components; this proves the WHOLE SYSTEM on the full 100-project corpus. The self-improving loop is critical — LLM-based systems require iterative refinement, not one-shot validation. Convergence criteria prevent infinite loops while ensuring genuine improvement.

#### Expected Outputs

- Coverage matrix (Markdown): rows = skills/agents, columns = scenario, pass rate, evidence link
- Quality gate report: exploit completeness, evidence anchoring, FP rate
- Self-improving loop journal: per-iteration findings, fixes, metric changes
- Updated regression baseline: all metrics with 3x trial data
- pytest summary: `tests/workflows/` full suite with documented expected-failure annotations

---

## Hard Delivery Gates for Phase 4.1 (Added 2026-02-10)

Phase 4.1 hardens orchestration behavior under failure and adversarial misuse. These are mandatory gates for workflow resilience.

### HDG-06: Permission Abuse Drills (Primary owner: 4.1-02, hardened in 7-02)

**Why this is critical**
- Agents can appear compliant in normal scenarios and still violate policy under pressure.
- A production orchestrator must prove it blocks forbidden actions under adversarial prompts.

**Implementation contract**
- Add adversarial scenarios in `tests/workflow_harness/scenarios/permission_abuse/`:
  - forbidden file reads (`~/.ssh`, `.env`, unrelated repos)
  - forbidden destructive commands (`rm -rf`, `git push`, force-reset patterns)
  - forbidden network/tool calls outside allowed policy.
- Every blocked action must emit a reason-coded hook event to `.vrs/debug/phase-4.1/permission-abuse-log.jsonl`.
- Require `BLOCK` mode for all policy hooks in these scenarios.

**Hard validation**
- 100% of forbidden actions are blocked with non-empty reason codes.
- 0 unauthorized actions succeed.
- If any scenario executes a forbidden action, phase gate fails immediately.

**Expected strict result**
- Policy enforcement is empirically proven under adversarial pressure, not inferred from config files.

### HDG-05: Crash/Resume Chaos Drills (Primary owner: 4.1-03 and 4.1-04)

**Why this is critical**
- Real orchestration environments fail mid-run (timeouts, process deaths, transient tool failures).
- If resume is non-deterministic, audit verdicts are not trustworthy.

**Implementation contract**
- Add chaos scenarios that intentionally inject failures at fixed points:
  - after graph build
  - mid-debate
  - between verifier draft and final verdict write
- Persist checkpoint artifacts and replay state to `.vrs/debug/phase-4.1/chaos/<scenario-id>/`.
- Resume via orchestrator recovery path; compare final output with uninterrupted control run.

**Hard validation**
- At least 3 crash points tested per scenario.
- Resume success rate must be >= 0.9 over repeated trials.
- Final verdict class and evidence hash set must match uninterrupted run after normalization.
- Any unrecoverable crash without complete forensic artifact bundle fails the gate.

**Expected strict result**
- The workflow harness proves fault tolerance and deterministic recovery, not just happy-path correctness.

## Cross-Phase: Failure Handling & Regression Protocol

### On Test Failure
- Controller captures: failure details, agent transcripts, tool calls, team events, file diffs
- Environment manager preserves failed state at `.vrs/debug/failures/{scenario}-{timestamp}/`
- Full team event log + inter-agent DMs included

### Improvement Cycle
- Fix skill/agent/orchestrator based on failure artifacts
- Rollback to clean committed state
- Re-run exact same scenario
- Comparator diffs run N vs run N+1
- Continue until convergence or max iterations

### Anti-Fabrication Rules
- Task list min 5 tasks completed (Agent Teams proof)
- Min 3 trials per scenario (not single-pass)
- Convergence must show improvement, not perfection
- 100% pass rate triggers investigation, not celebration
- External truth required (ground truth corpus from `examples/testing/`, not self-generated)
- Transcript min 500 chars per agent (proves real work)
- `total_cost_usd > 0` per agent (proves real API calls)
- Permission abuse scenarios must show 100% blocked forbidden actions with reason codes
- Crash/resume chaos scenarios must preserve checkpoint artifacts and deterministic verdict class

### Regression Contract
- Every new feature runs full regression suite
- Baseline degradation → BLOCK
- Grade outcomes, not paths
- pass^k metrics for reliability

## What This Phase Does NOT Do

- **Not shipping confidence gate** — Phase 8
- **Not production CI** — Expensive, on-demand only
- **Not CLAUDE.md updates** — Separate task

## Key Files

- `tests/workflow_harness/` — Controller + harness (from 3.1b)
- `examples/testing/` — 10 curated scenarios + guidelines (from 3.1b)
- `tests/workflows/` — pytest workflow test suite
- `.claude/settings.json` — Hook configurations for enforcement

## Success Criteria

1. Full audit pipeline test works reliably (2/3 or 3/3)
2. Agent behavioral constraints enforced via hooks (BLOCK mode, not log-only)
3. Multi-agent debate produces coherent verdict with adversarial structure
4. Coverage matrix: 30 skills + 21 agents with pass rates
5. Quality gates: exploit completeness >= 0.80, evidence anchoring >= 0.90, FP rate < 0.20
6. Self-improving loop converges within 5 iterations
7. Regression baseline updated without degradation from 3.1b
8. HDG-06 permission abuse drills pass with 100% block rate and reason-code logging
9. HDG-05 crash/resume chaos drills meet recovery and verdict-consistency thresholds

## Relationship to Other Phases

| Phase | Relationship |
|-------|-------------|
| **3.1b** (Harness Core) | Prerequisite — provides controller, harness, corpus, baseline |
| **3.2** (First Audit) | Prerequisite — provides working audit pipeline |
| **4** (Agent Teams) | Prerequisite — provides working debate |
| **4.1** (This Phase) | Deep validation + coverage + self-improvement |
| **6** (Test Overhaul) | Uses expanded harness for comprehensive E2E coverage |
| **7** (Docs + Hooks) | Harness validates hook enforcement |
| **8** (Ship) | Harness runs pre-ship validation |

## Research Inputs

- Phase 3.1b context: `.planning/phases/3.1b-workflow-testing-harness/context.md`
- `claude-code-controller` (npm): https://github.com/The-Vibe-Company/claude-code-controller
- Agent Teams docs: https://code.claude.com/docs/en/agent-teams
- Anthropic eval guidance: tasks + trials + graders, pass@k metrics
- Agent behavior report: `.planning/new-milestone/reports/agent-behavior-report.md`
- Hooks guide: https://code.claude.com/docs/en/hooks-guide
