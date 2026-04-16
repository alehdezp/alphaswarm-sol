# Testing Documentation Index

> AlphaSwarm.sol testing docs with LLM-optimized retrieval | Last updated: 2026-02-03

## Quick Stats

| Metric | Value |
|---|---|
| Total docs | 89 |
| Total tokens | ~82,000 |
| Tier 1 tokens | ~5,500 |
| Tier 2 tokens | ~37,000 |
| Tier 3 tokens | ~39,500 |

## Session Starters (Query → Doc)

| If you want to... | Load | ~Tokens |
|---|---|---|
| Pick the right workflow quickly | `.planning/testing/CONTEXT-OVERVIEW.md` | 1,068 |
| Understand overall testing structure | `.planning/testing/README.md` | 1,212 |
| Run a real claude-code-controller test | `.planning/testing/guides/guide-claude-code-controller.md` | 780 |
| Test skills end-to-end | `.planning/testing/workflows/workflow-skills.md` | 528 |
| Test sub-agents and routing | `.planning/testing/workflows/workflow-agents.md` | 528 |
| Test orchestration and debate flows | `.planning/testing/workflows/workflow-orchestration.md` | 636 |
| Validate audit entrypoint orchestration | `.planning/testing/workflows/workflow-audit-entrypoint.md` | 1,032 |
| Test knowledge graph build and query | `.planning/testing/workflows/workflow-graph.md` | 600 |
| Test external tools | `.planning/testing/workflows/workflow-tools.md` | 552 |
| Run E2E validation | `.planning/testing/workflows/workflow-e2e.md` | 552 |
| Diagnose failures and recovery | `.planning/testing/workflows/workflow-failure-recovery.md` | 552 |
| Validate instructions before subagents | `.planning/testing/workflows/workflow-instruction-verification.md` | 540 |
| Test grammar and in-situ outputs | `.planning/testing/workflows/workflow-grammar.md` | 492 |
| Add a new workflow test | `.planning/testing/guides/guide-new-workflow.md` | 444 |
| Prompt an agent or LLM for testing | `.planning/testing/guides/guide-agent-prompting.md` | 1,284 |
| Run alignment campaign | `.planning/testing/guides/guide-alignment-campaign.md` | 912 |
| Debug agent behavior and drift | `.planning/testing/guides/guide-agent-debugging.md` | 540 |
| Check orchestration progress | `.planning/testing/guides/guide-orchestration-progress.md` | 780 |
| Configure settings file | `.planning/testing/guides/guide-settings.md` | 1,356 |
| Decide Tier C testing | `.planning/testing/guides/guide-tier-c.md` | 444 |
| Validate context quality gate | `.planning/testing/guides/guide-context-quality.md` | 828 |
| Verify patterns with lattice scenarios | `.planning/testing/guides/guide-pattern-lattice.md` | 1,224 |
| Evaluate patterns with agent reasoning | `.planning/testing/guides/guide-pattern-evaluation.md` | 1,224 |
| Generate derived phase checks for `/gsd-plan-phase` | `.planning/testing/PLAN-PHASE-GOVERNANCE.md` | 1,800 |
| Run pattern discovery | `.planning/testing/guides/guide-pattern-discovery.md` | 420 |
| Use tool maximization matrix | `.planning/testing/TOOL-MAX-MATRIX.md` | 312 |
| Browse Tier B/C scenario library | `.planning/testing/scenarios/tier-bc/SCENARIO-LIBRARY.md` | 204 |
| Browse economic model library | `.planning/testing/scenarios/economic/ECONOMIC-MODEL-LIBRARY.md` | 588 |
| Check hard-case coverage | `.planning/testing/scenarios/hard-cases/HARD-CASE-COVERAGE.md` | 240 |
| Run graph ablation scenarios | `.planning/testing/scenarios/graph/GRAPH-ABLATION.md` | 360 |
| Measure graph contribution | `docs/reference/graph-usage-metrics.md` | 540 |
| Run performance suite | `.planning/testing/perf/PERF-PLAN.md` | 480 |
| Review perf scenarios | `.planning/testing/scenarios/perf/PERF-SCENARIOS.md` | 300 |
| Validate docs with real runs | `.planning/testing/workflows/workflow-docs-validation.md` | 408 |
| Validate in a real environment | `.planning/testing/workflows/workflow-real-env-validation.md` | 1,068 |
| Resolve missing commands | `.planning/testing/guides/guide-command-discovery.md` | 312 |
| Check command inventory | `.planning/testing/COMMAND-INVENTORY.md` | 312 |
| Check docs validation status | `.planning/testing/DOCS-VALIDATION-STATUS.md` | 288 |
| Load scenario manifest | `.planning/testing/scenarios/SCENARIO-MANIFEST.yaml` | 2,412 |
| Ensure evidence and provenance | `.planning/testing/guides/guide-evidence.md` | 336 |
| Locate ground truth provenance | `.planning/testing/ground_truth/PROVENANCE-INDEX.md` | 360 |
| Understand rules quickly | `.planning/testing/rules/RULES-ESSENTIAL-SUMMARY.md` | 396 |
| Use jj workspace scenarios | `.planning/testing/guides/guide-jujutsu-workspaces.md` | 588 |
| Use alignment ledger | `.planning/testing/ALIGNMENT-LEDGER-TEMPLATE.md` | 276 |
| Run skill reviewer | `.planning/testing/guides/guide-skill-reviewer.md` | 636 |
| Use iteration protocol | `.planning/testing/guides/guide-iteration.md` | 600 |
| Check coverage map | `.planning/testing/COVERAGE-MAP.md` | 480 |
| Check operator status contract | `.planning/testing/OPERATOR-STATUS-CONTRACT.md` | 360 |
| Use decision log schema | `.planning/testing/DECISION-LOG-SCHEMA.md` | 300 |
| Use scenario manifest template | `.planning/testing/templates/scenario-manifest.yaml` | 240 |
| Use pattern evaluation template | `.planning/testing/templates/PATTERN-EVALUATION-TEMPLATE.md` | 300 |
| Use discovery log template | `.planning/testing/templates/PATTERN-DISCOVERY-LOG.md` | 240 |
| Load VQL minimum set | `.planning/testing/vql/VQL-LIBRARY.md` | 1,200 |
| Check marker registry | `.planning/testing/MARKER-REGISTRY.yaml` | 240 |

## Tier 1 - Always Load

| Document | ~Tokens | Questions Answered | Key Terms |
|---|---|---|---|
| `.planning/testing/README.md` | 1,212 | What is this doc set for? How do I load the right workflow? | testing docs, progressive disclosure, claude-code-controller |
| `.planning/testing/DOC-INDEX.md` | 2,112 | Which doc should I load? What is the smallest next step? | index, routing, session starters |
| `.planning/testing/CONTEXT-OVERVIEW.md` | 1,068 | What are the non-negotiables? Which workflow fits my intent? | live mode, claude-code-controller, ground truth |
| `.planning/testing/rules/RULES-ESSENTIAL-SUMMARY.md` | 396 | What are the minimal rules I must follow? | auto-invoke, claude-code-controller, anti-fabrication |
| `.planning/testing/rules/claude-code-controller-REFERENCE.md` | 480 | What is the required claude-code-controller sequence? | claude-code-controller, launch zsh, capture |

## Tier 2 - On Demand

| Document | ~Tokens | Questions Answered | Key Terms |
|---|---|---|---|
| `.planning/testing/DOCS-MAINTAIN.md` | 1,920 | How do I maintain these docs? How do I update the index? | docs maintain, progressive disclosure, llms.txt |
| `.planning/testing/guides/guide-claude-code-controller.md` | 780 | How do I run claude-code-controller per workflow? | claude-code-controller, workflows, commands |
| `.planning/testing/guides/guide-evidence.md` | 336 | What evidence is required per run? | evidence pack, transcripts, reports |
| `.planning/testing/guides/guide-ground-truth.md` | 300 | What counts as ground truth? | provenance, Code4rena, SmartBugs |
| `.planning/testing/ground_truth/PROVENANCE-INDEX.md` | 360 | Where is the canonical provenance registry? | ground truth, provenance |
| `.planning/testing/guides/guide-inventory.md` | 324 | How do I ensure full coverage? | inventory, registry, coverage gaps |
| `.planning/testing/guides/guide-new-workflow.md` | 444 | How do I add a new workflow test? | workflow template, scenario manifest |
| `.planning/testing/guides/guide-agent-prompting.md` | 1,284 | How do I prompt an agent or LLM for testing? | prompting, controller, subject |
| `.planning/testing/guides/guide-alignment-campaign.md` | 912 | How do I align workflows, skills, and tests? | alignment, campaign, claude-code-controller |
| `.planning/testing/guides/guide-agent-debugging.md` | 540 | How do I debug agent drift and scope? | drift, scope, debugging |
| `.planning/testing/guides/guide-orchestration-progress.md` | 780 | How do I check progress and resume? | status, resume, checkpoints |
| `.planning/testing/guides/guide-settings.md` | 1,356 | How do I control tools and tiers? | settings, yaml, tools |
| `.planning/testing/guides/guide-tier-c.md` | 444 | When do I run Tier C tests? | tier c, labels, gating |
| `.planning/testing/guides/guide-context-quality.md` | 828 | How do I validate context packs? | context quality, gating |
| `.planning/testing/guides/guide-pattern-lattice.md` | 1,224 | How do I design lattice-based pattern scenarios? | lattice, tier c, vql, scenarios |
| `.planning/testing/guides/guide-pattern-evaluation.md` | 1,224 | How do I verify agent reasoning on patterns? | pattern evaluation, reasoning, graph |
| `.planning/testing/PLAN-PHASE-GOVERNANCE.md` | 1,800 | How do I keep `/gsd-plan-phase` checks research-backed and non-hardcoded? | plan-phase, drift, preconditions, runbooks |
| `.planning/testing/guides/guide-pattern-discovery.md` | 420 | When do I trigger novel pattern discovery? | pattern discovery, anomalies |
| `.planning/testing/guides/guide-iteration.md` | 600 | How do I classify and remediate failures? | iteration, taxonomy, remediation |
| `.planning/testing/TOOL-MAX-MATRIX.md` | 312 | Which tools are required per scenario type? | tools, matrix |
| `.planning/testing/scenarios/tier-bc/SCENARIO-LIBRARY.md` | 204 | What Tier B/C scenarios are available? | tier b/c, scenarios |
| `.planning/testing/scenarios/economic/ECONOMIC-MODEL-LIBRARY.md` | 588 | What economic models exist? | economic models, incentives |
| `.planning/testing/scenarios/hard-cases/HARD-CASE-COVERAGE.md` | 240 | What hard-case coverage exists? | hard cases, coverage |
| `.planning/testing/scenarios/graph/GRAPH-ABLATION.md` | 360 | How do I run graph ablation? | graph usage, ablation |
| `.planning/testing/perf/PERF-PLAN.md` | 480 | How do I measure performance? | throughput, latency |
| `.planning/testing/scenarios/perf/PERF-SCENARIOS.md` | 300 | What perf scenarios are required? | perf suite, concurrency |
| `.planning/testing/scenarios/hard-cases/HARD-CASE-LIBRARY.md` | 2,000 | What are the curated hard cases? | hard cases, provenance |
| `.planning/testing/scenarios/economic/ECONOMIC-MODEL-TEMPLATE.md` | 560 | How do I author economic models? | template, economics |
| `.planning/testing/scenarios/tier-bc/TEMPLATE.md` | 1,400 | How do I author Tier B/C scenarios? | template, lattice |
| `.planning/testing/templates/scenario-manifest.yaml` | 240 | How do I draft a scenario manifest entry? | template, manifest |
| `.planning/testing/templates/PATTERN-EVALUATION-TEMPLATE.md` | 300 | How do I structure pattern evaluations? | template, evaluation |
| `.planning/testing/templates/PATTERN-DISCOVERY-LOG.md` | 240 | How do I capture discovery candidates? | template, discovery |
| `.planning/testing/templates/PATH-EXPLORATION-TEMPLATE.md` | 240 | How do I capture exploration paths? | template, paths |
| `.planning/testing/vql/VQL-LIBRARY.md` | 1,200 | What VQL queries are mandatory? | vql, graph-first |
| `.planning/testing/MARKER-REGISTRY.yaml` | 240 | What are canonical markers? | markers, registry |
| `.planning/testing/COVERAGE-MAP.md` | 480 | Which workflows lack proof? | coverage, gaps |
| `.planning/testing/OPERATOR-STATUS-CONTRACT.md` | 360 | What must status/resume show? | status, progress |
| `.planning/testing/DECISION-LOG-SCHEMA.md` | 300 | What decision log fields are required? | decisions, evidence |
| `.planning/testing/guides/guide-command-discovery.md` | 312 | How do I resolve missing commands? | command discovery, verification |
| `.planning/testing/guides/guide-jujutsu-workspaces.md` | 960 | How do I isolate scenarios with jj workspaces? | jj workspace, scenarios, isolation |
| `.planning/testing/guides/guide-skill-reviewer.md` | 636 | How do I review skills each phase? | skill reviewer, checklist |
| `.planning/testing/rules/VALIDATION-RULES-SUMMARY.md` | 492 | What are validation blockers? | live mode, external ground truth, metrics |
| `.planning/testing/rules/TESTING-FRAMEWORK-SUMMARY.md` | 276 | What is the testing architecture? | controller, subject, evaluator |
| `.planning/testing/rules/TESTING-PHILOSOPHY-SUMMARY.md` | 204 | Why is real testing required? | human-like CLI, evidence-first |
| `.planning/testing/rules/SOURCE-OF-TRUTH.md` | 180 | Where are canonical rules? | canonical rules, references |
| `.planning/testing/workflows/workflow-cli-install.md` | 576 | How do I test install and first run? | install, first run, onboarding |
| `.planning/testing/workflows/workflow-graph.md` | 600 | How do I test KG build and query? | build-kg, query, graph-first |
| `.planning/testing/workflows/workflow-skills.md` | 528 | How do I test skills and chaining? | skills, routing, chaining |
| `.planning/testing/workflows/workflow-agents.md` | 528 | How do I test sub-agents? | agents, delegation, routing |
| `.planning/testing/workflows/workflow-orchestration.md` | 636 | How do I test orchestration? | debate, pools, beads |
| `.planning/testing/workflows/workflow-audit-entrypoint.md` | 1,032 | How do I validate audit orchestration? | audit entrypoint, TaskCreate, progress |
| `.planning/testing/workflows/workflow-tools.md` | 552 | How do I test external tools? | slither, mythril, aderyn |
| `.planning/testing/workflows/workflow-e2e.md` | 552 | How do I run E2E validation? | E2E, ground truth, metrics |
| `.planning/testing/workflows/workflow-failure-recovery.md` | 552 | How do I test recovery and diagnosis? | failure injection, retry, classification |
| `.planning/testing/workflows/workflow-grammar.md` | 492 | How do I test grammar and in-situ flows? | grammar, structured outputs |
| `.planning/testing/workflows/workflow-instruction-verification.md` | 540 | How do I validate instructions before subagents? | instruction verification, subagents |
| `.planning/testing/workflows/workflow-docs-validation.md` | 408 | How do I validate docs with real runs? | documentation, validation |
| `.planning/testing/workflows/workflow-real-env-validation.md` | 1,068 | How do I validate in a production-like environment? | environment, install, audit |
| `.planning/testing/ALIGNMENT-LEDGER-TEMPLATE.md` | 276 | How do I map workflows to evidence? | ledger, alignment, coverage |
| `.planning/testing/skill-reviewer/SKILL.md` | 2,520 | How do I review skills? | skill reviewer, best practices |
| `.planning/testing/skill-reviewer/references/evaluation_checklist.md` | 1,344 | What checklist should I follow? | checklist, frontmatter, triggers |
| `.planning/testing/skill-reviewer/references/pr_template.md` | 1,560 | How do I write PRs for skills? | PR template, tone |
| `.planning/testing/skill-reviewer/references/marketplace_template.json` | 360 | How do I create marketplace.json? | marketplace, template |
| `.planning/testing/skill-reviewer/references/review_report_template.md` | 756 | How do I write review reports? | review report, template |
| `.planning/testing/COMMAND-INVENTORY.md` | 312 | What commands are verified for testing? | command inventory, verification |
| `.planning/testing/DOCS-VALIDATION-STATUS.md` | 288 | Which docs are validated? | docs status, validation |
| `.planning/testing/scenarios/SCENARIO-MANIFEST.yaml` | 2,412 | What scenarios are defined? | scenario manifest, coverage |

## Tier 3 - Canonical Rules (Load Only When Needed)

| Document | ~Tokens | Questions Answered | Key Terms |
|---|---|---|---|
| `.planning/testing/rules/canonical/RULES-ESSENTIAL.md` | 2,628 | What are the full essential rules? | rules, claude-code-controller, anti-fabrication |
| `.planning/testing/rules/canonical/VALIDATION-RULES.md` | 14,448 | What are all validation rules A1-G3? | validation, ground truth, metrics |
| `.planning/testing/rules/canonical/TESTING-FRAMEWORK.md` | 2,484 | What is the full testing architecture? | controller, subject, evaluator |
| `.planning/testing/rules/canonical/TESTING-PHILOSOPHY.md` | 840 | Why is real testing mandatory? | philosophy, evidence-first |
| `.planning/testing/rules/canonical/claude-code-controller-instructions.md` | 2,700 | What are complete claude-code-controller commands? | claude-code-controller, commands |
| `.planning/testing/rules/canonical/README.md` | 1,044 | How are rules organized? | rule index, triggers |

## Section Index (Partial Loading)

### `.planning/testing/DOCS-MAINTAIN.md` (~1,920 tokens)

| Section | Lines | Summary |
|---|---|---|
| Header and Objective | 1-13 | Skill header and objective |
| Scope and Actions | 14-26 | Scope and actions supported |
| Process Steps 1-6 | 28-97 | Progressive disclosure workflow |
| Process Steps 7-17 | 99-146 | Maintenance steps and reporting |
| Success Criteria | 148-160 | Completion checklist |

## By Topic

- Index and navigation: `.planning/testing/DOC-INDEX.md`
- Minimal overview: `.planning/testing/CONTEXT-OVERVIEW.md`
- Plan-phase governance: `.planning/testing/PLAN-PHASE-GOVERNANCE.md`
- claude-code-controller usage: `.planning/testing/guides/guide-claude-code-controller.md`
- Evidence and reporting: `.planning/testing/guides/guide-evidence.md`
- Ground truth: `.planning/testing/guides/guide-ground-truth.md`
- Coverage inventory: `.planning/testing/guides/guide-inventory.md`
- Iteration protocol: `.planning/testing/guides/guide-iteration.md`
- Add new workflows: `.planning/testing/guides/guide-new-workflow.md`
- Agent prompting: `.planning/testing/guides/guide-agent-prompting.md`
- Alignment campaign: `.planning/testing/guides/guide-alignment-campaign.md`
- Jujutsu workspaces: `.planning/testing/guides/guide-jujutsu-workspaces.md`
- Skill reviewer: `.planning/testing/guides/guide-skill-reviewer.md`
- Agent debugging: `.planning/testing/guides/guide-agent-debugging.md`
- Orchestration progress: `.planning/testing/guides/guide-orchestration-progress.md`
- Settings control: `.planning/testing/guides/guide-settings.md`
- Tier C gating: `.planning/testing/guides/guide-tier-c.md`
- Context quality gate: `.planning/testing/guides/guide-context-quality.md`
- Pattern lattice verification: `.planning/testing/guides/guide-pattern-lattice.md`
- Pattern evaluation: `.planning/testing/guides/guide-pattern-evaluation.md`
- Pattern discovery: `.planning/testing/guides/guide-pattern-discovery.md`
- VQL minimum set: `.planning/testing/vql/VQL-LIBRARY.md`
- Tool maximization: `.planning/testing/TOOL-MAX-MATRIX.md`
- Command discovery: `.planning/testing/guides/guide-command-discovery.md`
- Rules summaries: `.planning/testing/rules/`
- Canonical rules: `.planning/testing/rules/canonical/`
- Workflows: `.planning/testing/workflows/`
- Command inventory: `.planning/testing/COMMAND-INVENTORY.md`
- Alignment ledger: `.planning/testing/ALIGNMENT-LEDGER-TEMPLATE.md`
- Coverage map: `.planning/testing/COVERAGE-MAP.md`
- Operator status contract: `.planning/testing/OPERATOR-STATUS-CONTRACT.md`
- Decision log schema: `.planning/testing/DECISION-LOG-SCHEMA.md`
- Ground truth provenance: `.planning/testing/ground_truth/PROVENANCE-INDEX.md`
- Docs validation status: `.planning/testing/DOCS-VALIDATION-STATUS.md`
- Scenario manifest: `.planning/testing/scenarios/SCENARIO-MANIFEST.yaml`
- Tier B/C scenario library: `.planning/testing/scenarios/tier-bc/SCENARIO-LIBRARY.md`
- Tier B/C scenario template: `.planning/testing/scenarios/tier-bc/TEMPLATE.md`
- Economic model library: `.planning/testing/scenarios/economic/ECONOMIC-MODEL-LIBRARY.md`
- Economic model template: `.planning/testing/scenarios/economic/ECONOMIC-MODEL-TEMPLATE.md`
- Hard-case coverage: `.planning/testing/scenarios/hard-cases/HARD-CASE-COVERAGE.md`
- Hard-case library: `.planning/testing/scenarios/hard-cases/HARD-CASE-LIBRARY.md`
- Templates: `.planning/testing/templates/`
- Plan contract schema: `.planning/testing/schemas/phase_plan_contract.schema.json`

## Retrieval Commands

```bash
# Start with the index
cat .planning/testing/DOC-INDEX.md

# Load minimal overview
cat .planning/testing/CONTEXT-OVERVIEW.md

# Load plan-phase governance contract
cat .planning/testing/PLAN-PHASE-GOVERNANCE.md

# Load one workflow only
cat .planning/testing/workflows/workflow-orchestration.md
```

## Outputs And Artifacts

Generated files you should expect in real runs:

- `.vrs/testing/runs/<run_id>/transcript.txt`
- `.vrs/testing/runs/<run_id>/report.json`
- `.vrs/testing/runs/<run_id>/environment.json`
- `.vrs/testing/runs/<run_id>/ground_truth.json`
- `.vrs/testing/runs/<run_id>/manifest.json`
- `.vrs/testing/state/current.yaml`
- `.vrs/testing/state/history/`

## Token Budget Summary

| Tier | Documents | Tokens | % |
|---|---|---|---|
| Tier 1 | 5 | ~5,500 | ~7% |
| Tier 2 | 45 | ~36,000 | ~45% |
| Tier 3 | 6 | ~38,500 | ~48% |
