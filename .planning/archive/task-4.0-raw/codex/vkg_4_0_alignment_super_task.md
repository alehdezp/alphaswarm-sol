# BSKG 4.0 Alignment Super Task (Consolidated)

Purpose: single, actionable task file to completely review and improve
`task/4.0/` by aligning every phase with `docs/PHILOSOPHY.md`, updating the
master roadmap and phase trackers, and adding review/reflect gates so every
new task is justified, conflict-free, and spawnable for follow-up work.

This document consolidates:
- `task/codex/philosophy_phase_alignment_review.md`
- `task/codex/vkg_4_0_philosophy_alignment_master_plan.md`
- `task/codex/vkg_4_0_production_grade_roadmap_review.md`

---

## How to Use This File

- Treat this as the single source of truth for the 4.0 alignment sweep.
- Every task is written so it can be picked up independently with enough
  context to start immediately.
- Each phase has two task layers:
  - Alignment tasks (add/update tasks in the phase tracker)
  - Review tasks (evaluate necessity and conflicts)
- Use Workstream P in trackers for alignment tasks.
- For phases without a tracker, create one using `task/4.0/phases/PHASE_TEMPLATE.md`.

---

## Task Detail Standard (Required in Trackers)

When copying tasks into phase trackers, include these fields so each task can
be picked up independently:

- Objective: one sentence, testable outcome
- Start here: exact files to read first
- Dependencies: upstream tasks or artifacts required
- Deliverables: specific files or schema updates
- Validation: concrete checks or tests
- Conflicts: downstream tasks to verify against
- Spawn triggers: what discoveries create new tasks

---

## Hard Constraints (Do Not Violate)

- Do not modify `src/true_vkg/kg/builder.py` or `src/true_vkg/queries/executor.py`.
- Prefer pattern packs and post-processing over hardcoded logic changes.
- Evidence packet and bead schemas must be versioned and backward compatible.
- Tier A and Tier B outputs remain strictly separated.
- ASCII only unless an existing file already uses Unicode.

---

## Global Principles (From PHILOSOPHY.md)

- Behavior-first knowledge graph and semantic ops
- Behavioral signatures and two-tier patterns
- Beads as core investigation units
- Multi-agent debate and verification
- Convoys/hooks for routing and persistence
- Evidence packets as the minimal context contract
- Confidence buckets with rationale and escalation
- Tool orchestration with dedup/disagreement handling
- VulnDocs feeds patterns, beads, and grimoires
- Context minimization with PPR and explicit fallbacks

---

## Deliverables of the Alignment Sweep

1) Updated `task/4.0/MASTER.md` with:
   - Phase 20 gate and VulnDocs track integration
   - Alignment sweep progress section
   - Updated dependency and gate logic

2) Updated phase trackers for Phases 0-20 with:
   - Workstream P tasks (alignment)
   - Review/evaluate/reflect tasks
   - Conflict notes with downstream phases
   - Dynamic task spawning rules

3) Conflict log with fixes for known inconsistencies

---

## Global Conflict Log (Resolve as Part of Tasks)

1) TOON vs YAML vs JSON output formats
   - Fix: JSON is canonical; YAML optional for human review.

2) Determinism scope vs philosophy
   - Fix: determinism gates apply to Tier A and reproducible manifests only.

3) Evidence packet contract missing in earlier phases
   - Fix: add evidence packet generation and schema checks as alignment tasks.

4) Phase 17/18 track not integrated into master flow
   - Fix: integrate as a parallel track that must finish before Phase 20.

5) LLM safety controls scheduled too late
   - Fix: add LLM safety and context minimization to Phase 3/10 gates.

6) Proxy resolution treated as warnings only
   - Fix: enforce resolution (ERC-1967 + ERC-2535) as a Phase 3 requirement.

---

## Dynamic Task Spawning Rule (Global)

Every phase tracker must include a "Dynamic Task Spawning" section:
- Trigger conditions: new evidence, conflicts, missing schema fields,
  or test failures.
- Spawn process: assign next available ID, update dependency graph,
  and update phase tracker status.
- Provide at least one example spawned task per phase.

---

# A. MASTER ROADMAP UPDATE TASKS

These tasks update the top-level roadmap and enable the phase alignment work.

## M.1 Update Master Roadmap Flow

Objective:
- Integrate Phase 20 as the final GA gate and add the VulnDocs track.

Scope:
- Update `task/4.0/MASTER.md` phase overview diagram.
- Add Gate 4 after Phase 20.
- Add Phase 17/18 as a parallel track starting after Phase 9 + 11.

Dependencies:
- None

Deliverables:
- Updated `task/4.0/MASTER.md` sections: Phase Overview, Decision Gates,
  Phase Summary, Dependencies.

Validation:
- Diagram shows Phase 20 and VulnDocs track.
- Gate logic is consistent with dependency tables.

## M.2 Add Alignment Sweep Progress Section

Objective:
- Track status of alignment tasks across phases in one place.

Scope:
- Add an "Alignment Sweep" section to `task/4.0/MASTER.md`.

Deliverables:
- Checklist for phase tracker updates.

Validation:
- Each phase has a checkbox and a short status note.

## M.3 Add Master Conflict Notes

Objective:
- Record top-level conflicts and fixes so future updates do not reintroduce them.

Scope:
- Add a conflict notes subsection under the master roadmap.

Deliverables:
- Conflict list (see Global Conflict Log) and fixes.

Validation:
- Conflicts referenced in phase tasks.

---

# B. PHASE-BY-PHASE UPDATE PACKAGES

Each phase includes:
- Alignment tasks (to add into tracker)
- Review tasks (evaluate necessity and conflict risks)
- Dynamic task spawning triggers

Use task IDs in the form `N.P.x` or `[ALIGN] N.x` depending on the tracker.

---

## Per-Phase Quickstart Checklist

Before starting any phase update:
- Read `docs/PHILOSOPHY.md` sections relevant to evidence packets, beads,
  confidence buckets, and debate protocol.
- Read the phase tracker in `task/4.0/phases/phase-N/TRACKER.md` (or create it).
- Check dependencies in `task/4.0/MASTER.md` and note downstream consumers.
- Scan related protocols in `task/4.0/protocols/` if referenced by the phase.

## Required Review Tasks (Must Add to Every Phase)

Add these review tasks even if not listed below:
- R.N.1 Phase necessity review: keep/cut/modify with rationale.
- R.N.2 Task necessity review: validate each new alignment task is needed.
- R.N.3 Conflict review: verify no clashes with downstream phase outputs.

---

## Phase 0 Update Package (Builder Refactor)

Context:
- Phase 0 exists as files under `task/4.0/phases/phase-0/` but lacks a tracker.

Add/Update Tasks:

P0.P.1 Evidence Packet Mapping (post-graph)
- Why: enforce evidence packet contract without modifying `builder.py`.
- Start here: read `docs/PHILOSOPHY.md` evidence packet contract.
- Scope: post-processing layer that maps semantic ops/properties to packet fields.
- Deliverables: mapping spec + minimal exporter module doc.
- Validation: sample packet from a known contract passes required fields.

P0.P.2 Bucket Defaults for Tier A
- Why: determinism applies to Tier A and sets base confidence.
- Scope: define default bucketing for Tier A findings.
- Deliverables: spec doc added to tracker.
- Validation: bucket rules referenced in Phase 1 outputs.

P0.P.3 Graph Quality Debate Trigger
- Why: missing evidence should be escalated, not hidden.
- Scope: define what missing data routes to a `graph-quality` convoy.
- Deliverables: routing rules in tracker.
- Validation: failure mode documented.

P0.P.4 VulnDocs Category Mapping
- Why: map semantic ops to VulnDocs categories for later bead context.
- Scope: mapping table only (no code).
- Deliverables: mapping spec doc.
- Validation: referenced by Phase 17 tasks.

P0.P.5 Evidence Packet Completeness Tests
- Why: enforce evidence packet schema early.
- Scope: tests in Phase 0 plan (no code implementation here).
- Deliverables: test requirements list.
- Validation: references in Phase 2/3 test sections.

Review Tasks:
- P0.R.1 Necessity Review: confirm each alignment task is required or mark as
  doc-only if already covered elsewhere.
- P0.R.2 Conflict Review: check conflicts with Phase 1/2 outputs.

Dynamic Task Spawning:
- Trigger: evidence packet missing fields in sample export.
- Spawn: add P0.P.6 for new field mapping or fallback rule.

---

## Phase 1 Update Package (Fix Detection)

Alignment Tasks:

P1.P.1 Evidence Packet Creation Per Finding
- Why: outputs must be evidence-linked and bead-ready.
- Scope: update tracker to require packet creation per pattern match.
- Deliverables: packet fields list + mapping from properties and ops.
- Validation: evidence packet required field checklist.

P1.P.2 Bead ID Assignment
- Why: findings become beads for investigation.
- Scope: add a stable bead ID spec derived from finding ID.
- Deliverables: ID scheme description.
- Validation: ID is deterministic across reruns.

P1.P.3 Bucket + Rationale Rules (Tier A)
- Why: bucket-first outcomes are a core philosophy output.
- Scope: define bucket assignment for Tier A with rationale fields.
- Deliverables: rules table.
- Validation: referenced by Phase 3 CLI output.

P1.P.4 Dispute Flagging
- Why: disagreement must be routed to debate.
- Scope: define `disputed` flag in evidence packets when tool sources disagree.
- Deliverables: flag rules.
- Validation: Phase 5 dedup workflow uses flag.

P1.P.5 VulnDocs Mapping for Patterns
- Why: patterns must map to knowledge sources.
- Scope: add mapping list in tracker.
- Deliverables: mapping table.
- Validation: Phase 17 retrieval uses the mapping.

Review Tasks:
- P1.R.1 Check determinism scope (Tier A only).
- P1.R.2 Confirm evidence packet mapping does not require builder changes.

Dynamic Task Spawning:
- Trigger: new semantic op added.
- Spawn: new mapping task for packet fields and signatures.

---

## Phase 2 Update Package (Benchmark Infrastructure)

Alignment Tasks:

P2.P.1 Benchmark -> Evidence Packet Summaries
- Why: benchmarks should emit evidence packets to calibrate buckets.
- Scope: add a summary export spec per expected finding.
- Deliverables: schema mapping notes.
- Validation: used by Phase 14 calibration.

P2.P.2 Dataset Provenance and Holdout Protocol
- Why: production-grade repeatability.
- Scope: add provenance docs and holdout split requirement.
- Deliverables: `PROVENANCE.md` and holdout rules.
- Validation: referenced in benchmark runner outputs.

P2.P.3 Coverage Matrix Contract
- Why: honesty about modeled vs unmodeled behaviors.
- Scope: add coverage schema contract to benchmark output.
- Deliverables: per-feature coverage list.
- Validation: used by confidence bucket overrides.

P2.P.4 Calibration Artifact Export
- Why: feed Phase 14 calibration.
- Scope: per-pattern calibration inputs.
- Deliverables: export file spec.
- Validation: Phase 14 tasks reference the export.

Review Tasks:
- P2.R.1 Evaluate metrics vs philosophy (internal calibration only).
- P2.R.2 Conflict check with Phase 14 calibration inputs.

Dynamic Task Spawning:
- Trigger: new dataset source added.
- Spawn: provenance update task + licensing check.

---

## Phase 3 Update Package (Basic CLI & Task System)

Alignment Tasks:

P3.P.1 Evidence Packet Output Contract
- Why: CLI is the primary user interface for agents.
- Scope: enforce evidence packet fields in JSON/SARIF outputs.
- Deliverables: schema versioning notes.
- Validation: schema validation test list.

P3.P.2 Stable Finding IDs + SARIF Fingerprints
- Why: triage stability and dedup.
- Scope: stable ID formula from graph fingerprint + pattern ID + location.
- Deliverables: ID spec and SARIF fingerprint mapping.
- Validation: rerun stability criteria.

P3.P.3 Convoy/Hook CLI Commands
- Why: hooks/convoys must be first-class.
- Scope: add commands to list and route beads.
- Deliverables: CLI command list and output fields.
- Validation: CLI tests for routing output.

P3.P.4 Proxy and Upgradeability Resolution
- Why: production systems are upgradeable by default.
- Scope: enforce ERC-1967 + ERC-2535 resolution modes in CLI output.
- Deliverables: warning vs resolved path definitions.
- Validation: proxy tests required.

P3.P.5 LLM Safety Controls (Early)
- Why: LLM usage is a security boundary.
- Scope: define minimal context rules and schema validation gates.
- Deliverables: LLM safety checklist in tracker.
- Validation: referenced by Phase 11 tasks.

Review Tasks:
- P3.R.1 Confirm evidence packet contract covers bucket and rationale.
- P3.R.2 Conflict check with Phase 9 PPR (no duplicate formats).

Dynamic Task Spawning:
- Trigger: new output format or client integration.
- Spawn: schema extension task + compatibility tests.

---

## Phase 4 Update Package (Test Scaffolding)

Alignment Tasks:

P4.P.1 Scaffold -> Bead Verdict Update
- Why: scaffold results must update bead status and confidence.
- Scope: add rules for mapping test outcomes to buckets.
- Deliverables: mapping spec in tracker.
- Validation: failure mode documented.

P4.P.2 Evidence Packet Test Fields
- Why: test results must attach to evidence packets.
- Scope: add fields for test results and tool metadata.
- Deliverables: schema update notes.
- Validation: references in Phase 3 schema.

P4.P.3 Compile Failure Taxonomy
- Why: compile failures must degrade confidence.
- Scope: define failure categories and bucket overrides.
- Deliverables: taxonomy list.
- Validation: used by Phase 10 degraded mode.

Review Tasks:
- P4.R.1 Verify mapping does not conflict with Phase 6 bead lifecycle.

Dynamic Task Spawning:
- Trigger: new testing tool added.
- Spawn: add tool-specific scaffold mapping task.

---

## Phase 5 Update Package (Real-World Validation)

Alignment Tasks:

P5.P.1 Ground-Truth Matching Rubric
- Why: real-world validation needs strict mapping rules.
- Scope: exact vs partial vs related match criteria.
- Deliverables: rubric doc added to tracker.
- Validation: referenced by benchmark results.

P5.P.2 Tool Disagreement -> Disputed Beads
- Why: dedup/disagreement is a core philosophy pillar.
- Scope: define rules for disputed flag and debate routing.
- Deliverables: routing rules.
- Validation: Phase 11 debate uses disputed beads.

P5.P.3 Audit Pack + Diffable Runs
- Why: audit-grade outputs must be reproducible.
- Scope: define audit pack artifact and diff command outputs.
- Deliverables: artifact spec (manifest + findings + evidence).
- Validation: used by Phase 16 release checks.

Review Tasks:
- P5.R.1 Evaluate whether metrics are internal calibration only.

Dynamic Task Spawning:
- Trigger: disagreements between BSKG and external tools.
- Spawn: add conflict-resolution analysis task.

---

## Phase 6 Update Package (Beads System)

Alignment Tasks:

P6.P.1 Bead Schema = Evidence Packet Compatible
- Why: beads and evidence packets must be convertible.
- Scope: ensure schema fields map 1:1.
- Deliverables: mapping table.
- Validation: conversion rules documented.

P6.P.2 Hook/Convoy Routing Model
- Why: persistence and routing are core philosophy.
- Scope: define priority rules and escalation paths.
- Deliverables: routing policy in tracker.
- Validation: Phase 3 CLI references routing fields.

Review Tasks:
- P6.R.1 Resolve TOON vs JSON format conflict.

Dynamic Task Spawning:
- Trigger: new bead template type added.
- Spawn: add new schema fields or conversion rules.

---

## Phase 7 Update Package (Conservative Learning)

Alignment Tasks:

P7.P.1 Bucket-Gated Learning
- Why: learning only from confirmed/rejected outcomes.
- Scope: define allowed buckets for learning events.
- Deliverables: policy notes in tracker.
- Validation: referenced by Phase 14 calibration.

P7.P.2 Evidence Packet References in Learning
- Why: learning must be traceable to evidence.
- Scope: add packet reference requirement to learning records.
- Deliverables: record schema update in tracker.
- Validation: audit pack includes learning provenance.

Review Tasks:
- P7.R.1 Check learning does not override evidence-based buckets.

Dynamic Task Spawning:
- Trigger: false positive confirmed by human.
- Spawn: add learning rollback task.

---

## Phase 8 Update Package (Metrics & Observability)

Alignment Tasks:

P8.P.1 Dispute + Escalation Metrics
- Why: disagreement is first-class signal.
- Scope: add dispute rate, debate time, backlog metrics.
- Deliverables: metric list.
- Validation: Phase 16 release requires health thresholds.

P8.P.2 Evidence Packet Completeness Metrics
- Why: ensure evidence packets are not hollow.
- Scope: define completeness score and threshold.
- Deliverables: metric definition.
- Validation: Phase 20 uses completeness gate.

Review Tasks:
- P8.R.1 Ensure metrics are internal (non-marketing).

Dynamic Task Spawning:
- Trigger: metric regression detected.
- Spawn: add root-cause analysis task.

---

## Phase 9 Update Package (Context Optimization, PPR)

Alignment Tasks:

P9.P.1 Evidence Packet as Minimal Context Contract
- Why: PPR must preserve required fields.
- Scope: ensure PPR outputs always include packet fields.
- Deliverables: output contract notes.
- Validation: Phase 11 LLM usage references it.

P9.P.2 Request-More-Context Rules
- Why: missing fields must trigger fallback, not silent failures.
- Scope: define rules and flags.
- Deliverables: fallback rules.
- Validation: Phase 10 degraded mode uses flags.

Review Tasks:
- P9.R.1 Resolve format conflicts with Phase 6.

Dynamic Task Spawning:
- Trigger: PPR drops required fields.
- Spawn: add PPR tuning task.

---

## Phase 10 Update Package (Graceful Degradation)

Alignment Tasks:

P10.P.1 Missing Tool -> Bucket Override
- Why: degraded tools must reduce confidence.
- Scope: define bucket downgrade rules.
- Deliverables: override table.
- Validation: Phase 3 CLI outputs bucket changes.

P10.P.2 Evidence Packet Missing Tool Fields
- Why: missing tools must be explicit in outputs.
- Scope: add `missing_tools` and rationale rules.
- Deliverables: schema notes.
- Validation: Phase 20 audit checks missing tools.

Review Tasks:
- P10.R.1 Ensure degraded mode does not conflict with Phase 11 LLM usage.

Dynamic Task Spawning:
- Trigger: new tool integration added.
- Spawn: add degraded-mode handling task.

---

## Phase 11 Update Package (LLM Integration, Tier B)

Alignment Tasks:

P11.P.1 Debate Protocol Schema Enforcement
- Why: multi-agent verification is core to philosophy.
- Scope: enforce claim/counterclaim/verdict fields.
- Deliverables: debate schema notes.
- Validation: debate output tests in tracker.

P11.P.2 Bucket + Rationale Required
- Why: bucket-first is mandatory.
- Scope: ensure every Tier B output includes bucket + rationale.
- Deliverables: output contract update.
- Validation: CLI schema validation.

Review Tasks:
- P11.R.1 Check that LLM safety gates exist before use.

Dynamic Task Spawning:
- Trigger: debate unresolved for critical finding.
- Spawn: human review escalation task.

---

## Phase 12 Update Package (Agent SDK Micro-Agents)

Alignment Tasks:

P12.P.1 Role Mapping for Coordinator/Supervisor/Integrator
- Why: roles must be explicit for routing.
- Scope: define role responsibilities and routing rules.
- Deliverables: role map doc.
- Validation: Phase 3 CLI output includes role labels.

P12.P.2 Consensus Arbitration Rules
- Why: multi-agent outputs need a deterministic merge.
- Scope: define arbitration rules and bucket mapping.
- Deliverables: arbitration spec.
- Validation: referenced by Phase 11 debate outcomes.

Review Tasks:
- P12.R.1 Verify role mapping does not conflict with Phase 6 routing model.

Dynamic Task Spawning:
- Trigger: new SDK added.
- Spawn: update routing policy task.

---

## Phase 13 Update Package (Grimoires & Skills)

Alignment Tasks:

P13.P.1 Grimoire Output -> Bead Verdict Update
- Why: grimoire tests must update bead buckets.
- Scope: define mapping from test results to verdicts.
- Deliverables: mapping rules.
- Validation: Phase 4 scaffold rules reference these.

P13.P.2 VulnDocs Linkage
- Why: grimoires should cite knowledge sources.
- Scope: embed VulnDocs references in outputs.
- Deliverables: linkage spec.
- Validation: Phase 17 uses it for updates.

Review Tasks:
- P13.R.1 Verify grimoire schema compatibility with evidence packets.

Dynamic Task Spawning:
- Trigger: new grimoire added.
- Spawn: add schema extension task.

---

## Phase 14 Update Package (Confidence Calibration)

Alignment Tasks:

P14.P.1 Score-to-Bucket Mapping Rules
- Why: buckets are the primary output.
- Scope: define thresholds and overrides (missing evidence, disputes).
- Deliverables: mapping table.
- Validation: used by Phase 3 output and Phase 20 audit.

P14.P.2 Calibration Uses Evidence Packets
- Why: calibration must be traceable to evidence.
- Scope: require evidence packet signals as calibration inputs.
- Deliverables: input contract notes.
- Validation: Phase 2 exports referenced.

Review Tasks:
- P14.R.1 Check for conflicts with Phase 7 learning policies.

Dynamic Task Spawning:
- Trigger: calibration drift detected.
- Spawn: add recalibration task.

---

## Phase 15 Update Package (Novel Solutions Integration)

Alignment Tasks:

P15.P.1 Philosophy Alignment Rubric
- Why: new solutions must not violate core philosophy.
- Scope: add rubric checklist (evidence packets, bead flow, debate).
- Deliverables: rubric template.
- Validation: required for acceptance.

Review Tasks:
- P15.R.1 Evaluate each new solution against rubric.

Dynamic Task Spawning:
- Trigger: solution fails rubric.
- Spawn: add remediation or rejection task.

---

## Phase 16 Update Package (Release Prep, RC)

Alignment Tasks:

P16.P.1 Release Checklist Includes Philosophy Sync
- Why: docs must stay aligned with system behavior.
- Scope: add checklist item for `docs/PHILOSOPHY.md` and `AGENTS.md`.
- Deliverables: release checklist update.
- Validation: required before RC.

P16.P.2 Schema Validation in Packaged Builds
- Why: ensure evidence packet and bead schemas are stable.
- Scope: add schema validation step to release process.
- Deliverables: validation criteria.
- Validation: included in release gate.

Review Tasks:
- P16.R.1 Ensure RC does not bypass Phase 20 gate.

Dynamic Task Spawning:
- Trigger: schema mismatch in packaged build.
- Spawn: add schema migration task.

---

## Phase 17 Update Package (VulnDocs Knowledge Schema)

Alignment Tasks:

P17.P.1 Evidence Packet Retrieval Contract
- Why: VulnDocs must populate evidence packets.
- Scope: define minimal retrieval contract and fields.
- Deliverables: retrieval contract doc.
- Validation: Phase 11 uses it for LLM context.

P17.P.2 Bead Template Linkage
- Why: beads must cite VulnDocs sources.
- Scope: add reference fields in bead templates.
- Deliverables: mapping rules.
- Validation: Phase 6 schema mapping uses it.

Review Tasks:
- P17.R.1 Ensure VulnDocs scope does not conflict with pattern packs.

Dynamic Task Spawning:
- Trigger: missing subcategory discovered.
- Spawn: add new VulnDocs category task.

---

## Phase 18 Update Package (VulnDocs Knowledge Mining)

Alignment Tasks:

P18.P.1 Mining -> Pattern Candidate Pipeline
- Why: mining must feed patterns and beads.
- Scope: define pipeline from mined chunk to pattern candidate.
- Deliverables: pipeline spec.
- Validation: Phase 2/14 use candidates for calibration.

P18.P.2 Provenance and Quality Scoring
- Why: knowledge reliability affects confidence buckets.
- Scope: add provenance fields and quality scoring.
- Deliverables: schema notes.
- Validation: Phase 14 uses quality weight.

Review Tasks:
- P18.R.1 Ensure mining outputs do not duplicate existing patterns.

Dynamic Task Spawning:
- Trigger: conflicting sources found.
- Spawn: debate/human review task.

---

## Phase 20 Update Package (Final Testing Phase)

Alignment Tasks:

P20.P.1 Evidence Packet Completeness Audit
- Why: Phase 20 is the final GA gate.
- Scope: run completeness audits across real-world corpus.
- Deliverables: audit report spec.
- Validation: Gate 4 criteria.

P20.P.2 Debate Protocol Stress Test
- Why: disputed findings must be resolved or escalated.
- Scope: run debate protocol on high-impact disputes.
- Deliverables: debate reports.
- Validation: unresolved disputes logged for human review.

Review Tasks:
- P20.R.1 Verify VulnDocs track is complete before GA.

Dynamic Task Spawning:
- Trigger: evidence packet completeness < threshold.
- Spawn: add remediation tasks in Phase 0/1/3.

---

# C. REVIEW, EVALUATE, REFLECT (Global)

These tasks ensure every phase and task is necessary.

## C.1 Phase Necessity Review Pass

Objective:
- Validate that each phase still maps to a philosophy pillar and provides
  outputs required by downstream phases.

Deliverables:
- A keep/cut/modify decision for every phase.
- Explicit justification for each decision.

## C.2 Task Necessity Review Pass

Objective:
- Review every new alignment task and remove or merge redundant tasks.

Deliverables:
- A task-level justification log in each phase tracker.
- Notes for any tasks marked as doc-only or already implemented.

## C.3 Conflict Resolution Pass

Objective:
- Identify conflicts between new tasks and existing later-phase tasks.

Deliverables:
- Updated dependency references in trackers.
- Conflict notes in the master roadmap.

---

# D. EXECUTION ORDER (Suggested)

1) M.1-M.3 update `task/4.0/MASTER.md`
2) Phase 0 tracker creation and P0 tasks
3) Phases 1-5 alignment tasks
4) Phases 6-10 alignment tasks
5) Phases 11-19 alignment tasks
6) Run C.1-C.3 review passes

---

# E. Progress Tracking (Checklist)

- [ ] M.1 Master roadmap updated
- [ ] M.2 Alignment sweep section added
- [ ] M.3 Conflict notes added
- [ ] Phase 0 tracker created and updated
- [ ] Phase 1 alignment tasks added
- [ ] Phase 2 alignment tasks added
- [ ] Phase 3 alignment tasks added
- [ ] Phase 4 alignment tasks added
- [ ] Phase 5 alignment tasks added
- [ ] Phase 6 alignment tasks added
- [ ] Phase 7 alignment tasks added
- [ ] Phase 8 alignment tasks added
- [ ] Phase 9 alignment tasks added
- [ ] Phase 10 alignment tasks added
- [ ] Phase 11 alignment tasks added
- [ ] Phase 12 alignment tasks added
- [ ] Phase 13 alignment tasks added
- [ ] Phase 14 alignment tasks added
- [ ] Phase 15 alignment tasks added
- [ ] Phase 16 alignment tasks added
- [ ] Phase 17 alignment tasks added
- [ ] Phase 18 alignment tasks added
- [ ] Phase 20 alignment tasks added
- [ ] C.1 Phase necessity review complete
- [ ] C.2 Task necessity review complete
- [ ] C.3 Conflict resolution pass complete
