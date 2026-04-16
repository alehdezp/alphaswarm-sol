# Testing Framework (Product Expectations)

**Purpose:** Define what “real” validation means for AlphaSwarm.sol and what evidence is required.

This is the product‑level expectation doc. Development workflow details live in:
- `.planning/testing/`

## When To Load

- If you need to understand how validation is supposed to work.
- If you are defining or reviewing workflow correctness.

## Non‑Negotiables

- **Live execution** only for validation and E2E.
- **External ground truth** for validation claims.
- **Evidence packs** for every run.
- **Hook enforcement** for preflight and task lifecycle.

## Real‑World Validation Definition

A run is valid only if:
- It uses LIVE mode (not mock/simulated).
- It captures a transcript with realistic duration.
- It links findings to evidence (graph node IDs + file:line).
- It compares to external ground truth when claims are made.

## Evidence Pack Contract

Required layout:

```text
.vrs/testing/runs/<run_id>/
  manifest.json
  transcript.txt
  report.json
  commands.log
  environment.json
  ground_truth.json
```

Marker registry (canonical strings): `.planning/testing/MARKER-REGISTRY.yaml`  
Context markers: `.planning/testing/CONTEXT-MARKERS.md`

## Scenario Manifest Requirement

All tests must be defined in a scenario manifest for traceable coverage:

- `.planning/testing/scenarios/SCENARIO-MANIFEST.yaml`

Each scenario must define:
- id, tier, command
- expected markers
- min duration + transcript length
- artifacts
- `behavior_model_ref` for Tier B/C economic scenarios (must point to `.planning/testing/scenarios/economic/ECONOMIC-MODEL-LIBRARY.md`)
- `min_markers` must be drawn from `.planning/testing/MARKER-REGISTRY.yaml`

## Graph Contribution Validation

Graph-first is mandatory, but **graph contribution must be measured**:
- Evidence packs must include `graph_usage` metrics (query count, unique nodes, query time).
- Graph ablation scenarios compare detection quality with graph enabled vs disabled.

Reference: `docs/reference/graph-usage-metrics.md`

## Performance Validation

Multi-agent orchestration must be measured under load:
- Use the HENTI performance suite in `.planning/testing/perf/PERF-PLAN.md`.
- Capture throughput, latency, queue wait, and failure rates in evidence packs.

## Ground Truth Contract

Ground truth must be external and provenance‑linked:
- Code4rena
- Sherlock
- Immunefi disclosures
- SmartBugs (with commit hash)

Canonical registry: `.planning/testing/ground_truth/PROVENANCE-INDEX.md`

## Settings vs State (Contract)

**Settings (user‑configured):** `.vrs/settings.yaml`  
**State (auto‑updated):** `.vrs/state/current.yaml`

Settings control:
- tools enabled/disabled
- Tier A/B/C gating
- context generation

State exposes:
- current stage
- completed stages
- pending tasks/beads
- available tools

**Schema reference:** `docs/reference/settings-state-schema.md`

## Tier C Gating

Tier C patterns can only run when:
- Protocol context pack exists
- Economic context is generated or explicitly skipped with justification
- Label coverage is sufficient
 - Context quality markers show `[CONTEXT_READY]` (see `.planning/testing/CONTEXT-MARKERS.md`)

If gating fails, Tier C must be marked **unknown** and skipped.

## Tool Initialization Requirement

Static tools must run before final findings are reported:
- tool status check (`uv run alphaswarm tools status`)
- tool execution (`uv run alphaswarm tools run ...`)

In product workflows, these are orchestrator tool calls, not user-facing primary steps.

## Naming Contract

All commands use `vrs-*` naming (not `/vrs:`).

## Hook Enforcement Requirement

Validation runs must prove hook enforcement in transcripts:

- Preflight gates block runs when settings/tools/graph/context are missing.
- Stop/SubagentStop blocks completion until TaskCreate/TaskUpdate markers exist.

Reference: `docs/reference/claude-code-orchestration.md`.

## Agent Testing Contract

Agent-related testing must validate evidence quality, graph-first reasoning compliance,
and verdict accuracy through automated test suites (`uv run pytest tests/`).

## Blind Critic Review

Validation reports require a blind review pass:
- critic reviews transcripts before seeing ground truth
- flags suspicious or incomplete evidence
- failure blocks reporting

## Iterative Self‑Learning Loop

Validation is not a one‑shot pass. The expected loop is:

1. Run live tests.
2. Identify gaps or mismatches.
3. Update workflow expectations in `docs/workflows/`.
4. Refine skills/subagents to match.
5. Re‑test with new evidence.

This loop continues until behavior and documentation align.

---

## Evaluation Intelligence Architecture (Tier 2)

The evaluation framework operates in two tiers. Tier 1 (Evaluation Engine) is the deterministic pipeline described throughout this document. Tier 2 (Evaluation Intelligence) is an adaptive layer with 10 sub-modules that activates incrementally as run data accumulates:

| Sub-module | Function |
|------------|----------|
| Scenario synthesis | Analyze skill/agent prompts, identify untested claims, generate test scenarios |
| Coverage radar | Live heat map across 4 axes (vuln class, semantic op, reasoning skill, graph pattern) |
| Adaptive tier management | Auto-promote tiers on sustained low scores; demotion requires human approval |
| Behavioral fingerprinting | Detect drift via reasoning move profiles and output distributions |
| Self-healing contracts | Statistical detection of stale/trivial evaluation dimensions |
| Cross-workflow learning | Propagate insights across related workflows |
| Reasoning chain decomposition | Score 7 discrete reasoning moves independently |
| Evaluator self-improvement | Generate evaluator prompt variants on inter-rater disagreement (max 3 iterations) |
| Compositional stress testing | 8 non-standard agent compositions; keystone analysis |
| Gap-driven synthesis loop | Closed-loop coverage radar + scenario synthesis |

### Coverage Gap Detection and Prioritization

The coverage radar maintains a heat map with 4 axes. Each cell represents a (vulnerability class, semantic operation, reasoning skill, graph query pattern) tuple. The system tracks:

- **Hot cells:** Covered by 3+ test scenarios with passing results
- **Warm cells:** Covered by 1-2 scenarios
- **Cold cells:** Zero test coverage

Cold cells are prioritized for scenario synthesis by:
1. Vulnerability severity (critical > high > medium > low)
2. Skill claim density (how many skill prompts reference this area)
3. Historical failure rate in adjacent cells

The scenario synthesis engine generates targeted tests for high-priority cold cells, creating a closed loop between gap detection and test generation.

### Adaptive Tier Promotion

Evaluation tiers are dynamic, not static assignments:

- **Auto-promotion triggers:** Sustained low scores (3+ consecutive runs below threshold), persistent meta-evaluation disagreement (inter-rater correlation < 0.6), or detection of behavioral drift via fingerprinting
- **Promotion effect:** Increases evaluation rigor — adds more evaluation dimensions, enables deeper reasoning chain decomposition, activates compositional stress testing
- **Demotion:** Requires explicit human approval. The framework never reduces evaluation rigor automatically

### Sequential Execution Constraint

Plans that spawn Agent Teams must execute in top-level Claude Code sessions, not via subagents. Agent Teams cannot be spawned from subagents. Wave parallelism in plan dependencies is for planning purposes only — execution within a session is strictly sequential.
