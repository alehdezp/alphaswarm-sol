# Improvement Digest

**Last updated:** 2026-02-26
**Passes completed:** 19 (P18: empty convergence checkpoint; P19: 14 structural items)
**Total proposed:** 453 (439 from P1-P17 + 0 from P18 + 14 from P19)
**Total merged:** 387 (373 from P1-P17 + 0 from P18 + 14 from P19)
**Total rejected:** 22 (17 from P1-P13 + 2 from P14 + 3 from P15)
**Active items:** 0

## Active Items

No active items. All improvement passes complete.

## Rejection Log

### P2-IMP-14: Wave 1 "Zero Dependencies" Claim [REJECTED, Pass 2]
**Proposed:** Change Wave 1 description to acknowledge runtime dependency between models and contracts via the evaluator.
**Rejected because:** P1-IMP-05 already addressed the vocabulary coupling. The remaining dependency is Wave 4 (evaluator), not Wave 1. The additional clarification was cosmetic.

### P2-IMP-16: Debrief Layer 3 Is Redundant With Evaluator [REJECTED, Pass 2]
**Proposed:** Remove Layers 2 and 3 from debrief cascade, simplify to Layer 1 (SendMessage) only.
**Rejected because:** Layer 3 transcript analysis serves a different purpose (agent self-explanation) than the evaluator (external assessment). Even low-confidence debrief data provides unique signal that evaluator cannot.

### P2-IMP-19: Collapse From 5 Plans to 3 [REJECTED, Pass 2]
**Proposed:** Further compress 5-plan structure (A-E) into 3 outcome-driven plans.
**Rejected because:** 5 plans already represents a pragmatic collapse from the original 12. Further compression would merge concerns creating oversized plans that violate GSD guidelines.

### P3-IMP-01: EvaluationPlugin Protocol STILL Mismatched (P2-IMP-01 Follow-Up) [REJECTED, Pass 3]
**Proposed:** Add isinstance check to Plan A exit criteria to verify Protocol signature.
**Rejected because:** Python's `@runtime_checkable` Protocol does NOT check parameter signatures (PEP 544). The `context` kwarg is optional and Liskov-substitutable.

### P3-IMP-10: Exit Gate "All 30 Skills Tested" Ambiguity [REJECTED, Pass 3]
**Proposed:** Clarify exit gate item 3 to distinguish "has contract" from "actually tested."
**Rejected because:** Exit gate already disambiguates per-tier. Standard tier "tested" = capability checks passing, which is deterministic (no LLM cost).

### P6-IMP-16: Hook Composition Pipeline — Derived Observations in Real Time [REJECTED, Pass 6]
**Proposed:** Add "Derived Observation Hooks" to Plan 02 — hooks that read other hooks' JSONL output.
**Rejected because:** 5-LOC fix already specified in Plan 04, LOW confidence with unresolved prerequisite, race condition via JSONL side-channel.

### P6-IMP-19: Notification Hooks for Long-Running Evaluation Progress [REJECTED, Pass 6]
**Proposed:** Add `notify_progress.py` hook for macOS notifications via `osascript`.
**Rejected because:** Platform lock-in, silent Plan 08 dependency, misattributed CC capability, scope mismatch.

### P7-IMP-09: Mode Coverage Fraction [REJECTED, Pass 7]
**Proposed:** Add `mode_coverage: dict[str, float]` with hardcoded fractions per run mode.
**Rejected because:** Coverage fraction is trivially computable from `DimensionScore.applicable` (already added). Hardcoded constants without derivation from Mode Capability Matrix create maintenance hazard.

### P7-IMP-23: In-Session Evaluation Signals [DEFERRED, Pass 7]
**Proposed:** Real-time evaluation feedback during interactive sessions via hook-reads-JSONL.
**Deferred because:** Three compounding architectural blockers: hooks are stateless subprocesses, threading.Lock provides zero cross-process protection, CC cannot poll and SendMessage simultaneously.

### P9-IMP-05: VISION.md North Star Items Lack v1/v2 Markers [REJECTED, Pass 9]
**Proposed:** Add per-item (v2) markers to VISION.md North Star items.
**Rejected because:** VISION.md's opening block already contains "This document is NOT binding for 3.1c v1." Adding per-item markers implies items WITHOUT a marker are v1 requirements, contradicting the blanket disclaimer.

### P9-IMP-02: Category Rigidity Trap [REFRAMED, Pass 9]
**Proposed:** Smart Selection Matrix is category-driven despite per-workflow claim.
**Reframed because:** Matrix is already documented as reference-only. Real rigidity is in Plan 07's evaluator dispatch.
**Reframed into:** P9-ADV-2-01

### P9-IMP-11: Reasoning Move Taxonomy Is Investigation-Locked [REFRAMED, Pass 9]
**Proposed:** Add custom_moves extension for non-investigation workflows.
**Reframed because:** Existing 7-move enum already contains all needed moves. Problem is applicability assignment, not vocabulary.
**Reframed into:** P9-ADV-2-02

### P9-IMP-12: Plan 12 Delivers Batch Baseline, Not Living System [REFRAMED, Pass 9]
**Proposed:** Add USAGE.md to close batch-vs-living gap.
**Reframed because:** Problem is operational (no trigger protocol), not documentary.
**Reframed into:** P9-ADV-4-01

### P9-IMP-15: Intelligence Module LOC Estimates Unrealistically Low [REFRAMED, Pass 9]
**Proposed:** Revise LOC estimates upward.
**Reframed because:** 3-source inconsistency is the real problem, not magnitude.
**Reframed into:** P9-ADV-3-02

### P10-IMP-06: POSIX Atomic Append Simplification [REJECTED, Pass 10]
**Proposed:** Replace `fcntl.flock` + `open("a")` with POSIX `O_APPEND` atomic guarantee.
**Rejected because:** Python's buffered `f.write()` may split large writes into multiple `write(2)` syscalls, breaking the POSIX atomicity guarantee.

### P10-IMP-04: Hook Registration Discovery Protocol [REFRAMED, Pass 10]
**Proposed:** Add hook self-registration via manifest file for dynamic discovery.
**Reframed because:** CC hooks are filesystem-convention based, not registry-based.
**Reframed into:** P10-ADV-1-01

### P10-IMP-07: Observation Schema Versioning [REFRAMED, Pass 10]
**Proposed:** Add schema version field to observation JSONL for forward compatibility.
**Reframed because:** v1 has exactly one schema version. Real problem is parser resilience to unknown fields.
**Reframed into:** P10-SYN-01

### P10-IMP-09: Evaluator Plugin Hot-Reload [REFRAMED, Pass 10]
**Proposed:** Support live reloading of evaluator plugins during a session.
**Reframed because:** Evaluator runs in Python subprocess, not in CC session. Real need is faster iteration.
**Reframed into:** P10-CSC-04

### P10-IMP-12: Adaptive Difficulty Scaling [REFRAMED, Pass 10]
**Proposed:** Auto-adjust scenario difficulty based on agent performance history.
**Reframed because:** No performance history exists in v1.
**Reframed into:** P10-IMP-24

### P10-IMP-15: Cross-Session State Persistence [REFRAMED, Pass 10]
**Proposed:** Full state persistence across CC sessions for evaluation continuity.
**Reframed because:** CC sessions are ephemeral by design.
**Reframed into:** P10-ADV-4-02

### P10-IMP-19: Multi-Model Evaluation Comparison [REFRAMED, Pass 10]
**Proposed:** Run same scenarios across multiple LLM models for comparative evaluation.
**Reframed because:** Real need is model binding clarity.
**Reframed into:** P10-ADV-3-02

### P11-IMP-03: Graph Complexity Budget Per Plan [REFRAMED, Pass 11]
**Proposed:** Per-plan graph complexity budgets.
**Reframed because:** LOC complexity budgets already exist at plan level. Graph complexity is an implementation concern.

### P11-IMP-05: Hook Dependency Declaration [REFRAMED, Pass 11]
**Proposed:** Add hook dependency declaration for ordering guarantees.
**Reframed because:** CC hooks don't support ordering. Filesystem order is deterministic (alphabetical).

### P11-IMP-07: Parallel Evaluator Execution [REFRAMED, Pass 11]
**Proposed:** Run evaluator dimensions in parallel.
**Reframed because:** Evaluator is a single `claude -p` call. Parallelism is at scenario level.

### P11-IMP-09: Observation Schema Migration [REFRAMED, Pass 11]
**Proposed:** Add schema migration framework for observation data.
**Reframed because:** v1 has no shipped data to migrate. P10-SYN-01 already covers with field validation.

### P11-IMP-14: Plan 07→09 Priority Inversion [REFRAMED, Pass 11]
**Proposed:** Cited SkillsBench (arxiv 2602.12670v1) for evaluation ordering.
**Reframed because:** Fabricated citation. Legitimate concern already addressed by ADV-5-01.

### P12-IMP-04: EvaluationPlugin Protocol Signature Mismatch [REJECTED, Pass 12]
**Proposed:** EvaluationPlugin Protocol missing `context` kwarg needs Plan 01 fix.
**Rejected because:** Already fully addressed by existing CONTEXT: KCI, DC-3, Plan 01 deliverable 4.

### P12-IMP-03: DimensionScore Missing `applicable` Field [REFRAMED, Pass 12]
**Proposed:** DimensionScore.applicable not yet built, needs Plan 01 attention.
**Reframed because:** Three separate CONTEXT locations already specify it. Real gap is `effective_score()` edge case.
**Reframed into:** P12-ADV-2-01

### P12-IMP-05: ground_truth_rubric No Wiring Specification [REFRAMED, Pass 12]
**Proposed:** ground_truth_rubric missing from Schema Hardening, no prompt injection spec.
**Reframed because:** Gap is underspecified TYPE/FORMAT/INJECTION, not missing from manifest.
**Reframed into:** P12-ADV-1-01

### P12-IMP-10: Sub-Wave Circular Ordering [REFRAMED, Pass 12]
**Proposed:** Plan 10 Core HITL gate blocks Plan 09 sub-wave, creating circular ordering.
**Reframed because:** Not circular ordering — a missing joint gate.
**Reframed into:** P12-ADV-3-01

### P13-IMP-02: Hook Enum Contains Factually Wrong Locked Decision [REFRAMED, Pass 13]
**Proposed:** Correct the locked decision that PermissionRequest is not a distinct hook event.
**Reframed because:** The core finding is correct but the action plan was incomplete. TeammateIdle/TaskCompleted sourcing unverified.
**Reframed into:** P13-ADV-2-01

### P13-IMP-03: Prompt-Type Hooks Can Transform Debrief Layer 3 [REJECTED, Pass 13]
**Proposed:** Use prompt-type SubagentStop hooks to enhance debrief Layer 3.
**Rejected because:** Contradicts locked Implementation Decision. BUG #20221 flags prompt-type SubagentStop hooks as BROKEN. Misidentifies target layer.

### P13-IMP-04: transcript_path Enables Direct Transcript Reading [REJECTED, Pass 13]
**Proposed:** obs_precompact should use TranscriptParser instead of inline JSONL parsing.
**Rejected because:** "No TranscriptParser import" is a locked architectural decision (P11-ADV-1-02) with specific failure-mode justification. Inline JSONL parsing is ~15 LOC.

### P13-IMP-13: Compaction Destroys Observation Data Mid-Evaluation [REJECTED, Pass 13]
**Proposed:** Concrete failure scenario for compaction during evaluation.
**Rejected because:** Already comprehensively addressed by 5 locked decisions (obs_precompact, GVS node inventory merge, DebriefResponse.compacted, compacted marker, CalibrationConfig tracking).

### P13-IMP-14: GVS Citation Rate Fallback Should Use Observation-Based Matching [REFRAMED, Pass 13]
**Proposed:** Replace TranscriptParser as primary citation source with observation-based node-ID matching.
**Reframed because:** Would demote TranscriptParser from PRIMARY to secondary, using truncated data. Locked decision forbids this.
**Reframed into:** P13-ADV-3-01

### P13-IMP-15: Agent-Type Hooks as Debrief Layer Alternative [REFRAMED, Pass 13]
**Proposed:** Replace Layers 3-4 with agent-type SubagentStop hooks.
**Reframed because:** Layers 3-4 are a degradation sequence, not data channels. Agent hook is a Layer 1 variant.
**Reframed into:** P13-ADV-4-01

### P13-IMP-17: Position Bias in Evaluator Debate Protocol [REJECTED, Pass 13]
**Proposed:** Revert sequential dispatch to parallel to avoid anchoring bias.
**Rejected because:** Sequential protocol was deliberately designed to replace parallel. Correct fix is instrumentation (B_score_pre_exposure) — see P13-ADV-5-01.

### P13-IMP-20: GVS Should Be Demoted from Scorer to Evaluator Input [REJECTED, Pass 13]
**Proposed:** Demote GVS from independent scorer to evaluator input signal.
**Rejected because:** Violates locked Mode Capability Matrix. Removes ONLY deterministic enforcement of Graph-First Rule. 66-combo calibration IS the validation mechanism.

### P13-IMP-21: Debrief Signal Uniqueness — Layer 1 Only [REFRAMED, Pass 13]
**Proposed:** Only Layer 1 has scoring value; Layers 2-4 should not contribute.
**Reframed because:** Binary "diagnostic-only" framing too coarse. Weight parameter preserves cascade while preventing noise dilution.
**Reframed into:** P13-ADV-4-02

### P13-IMP-22: Three-System Overhead Budget Needs Empirical Measurement [REFRAMED, Pass 13]
**Proposed:** Budget ceiling is premature before first real run.
**Reframed because:** Real problem is `scoring_p95` was never estimated. Defer ceiling to empirical data.

### P13-IMP-23: GVS graph_first — Add Graduated Score [REFRAMED, Pass 13]
**Proposed:** Replace binary graph_first_compliant with graduated score.
**Reframed because:** Graph-First Rule is a hard architectural constraint. Graduated score should complement, not replace, binary enforcement.
**Reframed into:** P13-ADV-3-02

### P14-IMP-05: Annotate Plan 01 Model Fields as [core] vs [defensive] [REJECTED, Pass 14]
**Proposed:** Add [core]/[defensive] annotations to ~30+ model fields.
**Rejected because:** Process overhead on a design document. [core]/[defensive] would double signal-to-noise. `run_mode=simulated` already distinguishes untested paths. LOW confidence on cosmetic change to converged model list.

### P14-IMP-13: Debrief Protocol Layers 2-4 Over-Designed for v1 [REJECTED, Pass 14]
**Proposed:** Narrow Plan 05 v1 scope to Layer 1 only.
**Rejected because:** Already rejected as P2-IMP-16. Pass 13 further refined layer weights via `debrief_layer_weight` (P13-ADV-4-02). Rehashing without engaging rejection rationale.

### P14-IMP-01: Split Plan 01 Into "First-Run" vs "Post-Observation" Type Tiers [REFRAMED, Pass 14]
**Proposed:** Defer ~12 types to Wave 4 as stubs.
**Reframed because:** Breaks dependency graph — types are load-bearing infrastructure. Correct fix: annotate provisional fields, don't defer types.
**Reframed into:** P14-ADV-1-01

### P14-IMP-02: calibration_epoch Needs 'failed' State [REFRAMED, Pass 14]
**Proposed:** Add `'failed'` to calibration_epoch Literal.
**Reframed because:** `calibration_epoch` routes ExperimentLedgerEntry — `'failed'` would be permanent terminal state. Status belongs on CalibrationConfig (the artifact), not the routing enum.
**Reframed into:** P14-ADV-2-01

### P14-IMP-04: Plan 03 Should Be Absorbed Into Plan 02 [REFRAMED, Pass 14]
**Proposed:** Merge Plan 03 into Plan 02 as "Part B: Observation Adapter."
**Reframed because:** Premature refactoring. Wave 2/3 distinction encodes empirical gate. Scheduling risk addressed by parallelism note instead.
**Reframed into:** P14-ADV-4-01

### P14-IMP-10: No Cost Constraint on Dual-Opus Evaluation Per Run [REFRAMED, Pass 14]
**Proposed:** Add $10 programmatic ceiling via claude -p.
**Reframed because:** $100-270 scare figure doesn't reflect actual architecture (per-dimension filtering). Per-dimension cost ~$0.03-0.038. Unenforceable ceiling replaced by cost derivation.
**Reframed into:** P14-ADV-2-02

### P14-IMP-20: Plan 12 Needs Explicit 3.1e MVL Gate [REFRAMED, Pass 14]
**Proposed:** Add cross-phase dependency from 3.1e Plan 01 to Plan 12 Part 2.
**Reframed because:** (1) 3.1e MVL measures different thing, (2) Plan 12 has internal go/no-go gates, (3) creates dependency graph loop. Strengthened internal gates instead.
**Reframed into:** P14-ADV-1-02

### P14-IMP-22: API Cost Estimates Missing [REFRAMED, Pass 14]
**Proposed:** Add $50-200+ cost estimates.
**Reframed because:** 4x range with open upper bound is not visibility. Conflates execution and scoring cost. Static dollars mislead.
**Reframed into:** P14-ADV-2-02

### P15-IMP-04: Missing Evaluation-to-Detection Bridge in ImprovementHints [REFRAMED, Pass 15]
**Proposed:** Add `target_component` enum to ImprovementHint.
**Reframed because:** Defining routing enum before any evaluations is premature. Enum discovered from data in Plan 12.
**Reframed into:** P15-ADV-3-01

### P15-IMP-06: Empirical Override Protocol for Locked Decisions [REFRAMED, Pass 15]
**Proposed:** Three-state formal amendment machinery (CONFIRM/AMEND/REVOKE).
**Reframed because:** Adds specification weight — the anti-pattern IMP-01 is stopping. Replaced by lightweight per-plan permission gates.
**Reframed into:** P15-ADV-2-01

### P15-IMP-09: Cross-Phase Artifact Contracts [REFRAMED, Pass 15]
**Proposed:** Pre-specified YAML schemas for 3.1e→3.1c artifacts.
**Reframed because:** 3.1e Plan 05 owns schema extraction. Pre-specifying field names constrains discovery.
**Reframed into:** P15-ADV-2-02

### P15-IMP-16: Cross-Phase Interface Questions Must Be Answered [REFRAMED, Pass 15]
**Proposed:** Answer all 5 cross-phase interface questions definitively.
**Reframed because:** 2 of 5 are implementation-dependent. Consolidated with definitive + provisional answers.
**Reframed into:** P15-ADV-2-03

### P15-IMP-18: /vrs-test-suite Skill Decomposition [REFRAMED, Pass 15]
**Proposed:** Split into coordinator + 4 sub-skills.
**Reframed because:** Pre-optimizes unwritten skill. Real problem is context exhaustion from 51-workflow fan-out.
**Reframed into:** P15-ADV-4-01

### P15-IMP-23: Compaction Preservation Protocol Consolidation [REJECTED, Pass 15]
**Proposed:** Consolidate 6 scattered compaction decisions into one section.
**Rejected because:** Creates 7th maintenance location. Right fix is cross-reference annotations within existing sections.

### P15-IMP-25: ObservationSummary Interface Contract [REFRAMED, Pass 15]
**Proposed:** GUARANTEED/CONDITIONAL/DERIVED taxonomy for ObservationSummary fields.
**Reframed because:** New taxonomy adds consumer burden. Simpler fix: producer-side null-safety contract.
**Reframed into:** P15-ADV-5-01

### P15-IMP-34: Heuristic Evaluator Mediocre Band Limitation [REJECTED, Pass 15]
**Proposed:** Document mediocre band compression at 53.
**Rejected because:** Self-resolving limitation (Plan 07 LLM evaluator replaces heuristic). Already documented in 3.1e-CONTEXT.md.

### P15-IMP-35: Headless-First Wave 6 Execution Order [REFRAMED, Pass 15]
**Proposed:** Restructure Wave 6 to headless-first.
**Reframed because:** Headless-first validates only headless pipeline. Interactive pipeline unvalidated without gate.
**Reframed into:** P15-ADV-1-01

### P15-IMP-36: Split Plan 12 at Parts 0-1 / 2-5 [REJECTED, Pass 15]
**Proposed:** Near-duplicate of IMP-12.
**Rejected because:** Duplicate. Unique detail absorbed into P15-IMP-12.

## Convergence State

**Pass 9 assessment (2026-02-19):** 25 items (17 improvements + 6 adversarial-created + 2 synthesis-created). 20 merged, 1 rejected, 4 reframed. Pass 9 was a PHILOSOPHY.md/CONTEXT.md alignment audit focused on workflow flexibility, interactive framework philosophy, and Claude Code orchestration centrality.

**Pass 10 assessment (2026-02-19):** 44 items. 33 merged, 1 rejected, 6 reframed. Pass 10 broke 9-pass convergence with fresh CC platform research (Feb 2026) revealing 12-event hook lifecycle, SubagentStop/TeammateIdle events, and tool_use_id pairing.

**Pass 11 assessment (2026-02-19):** 27 items. 22 merged, 0 rejected, 5 reframed. Pass 11 corrected CC hook enum errors (PreCompact/SessionEnd discovery, PermissionRequest removal), added evaluator effort pinning, and introduced compaction-aware debrief strategy.

**Pass 12 assessment (2026-02-19):** 19 items. 15 merged, 1 rejected, 3 reframed. Pass 12 focused on Group 4 (Plans 06, 07) and Group 6 (Plans 09, 10, 11). Key themes: dimension registry expansion, schema migration script, ground_truth_rubric, Wave 6 schedule, evidence fidelity metric.

**Pass 13 assessment (2026-02-20):** 37 items (23 IMP + 11 ADV + 2 SYN + 1 CSC). 26 merged, 5 rejected, 6 reframed. Pass 13 focused on Group 2 (Plans 02, 03 — Observation Pipeline) and Group 3 (Plans 04, 05 — Scoring Engine) with web research. Key themes: passive hook elimination (TranscriptParser as single data source), PostToolUse field name bug, SubagentStart schema fix, GVS grader taxonomy, _check_graph_first data model fix, GVS Weight Calibration Procedure, PreCompact race condition resolution, PermissionRequest locked decision correction, deferred SubagentStop prompt-hook research note.

**Pass 14 assessment (2026-02-20):** 34 items (25 IMP + 7 ADV + 1 SYN + 1 CSC). 26 merged, 2 rejected, 6 reframed. Pass 14 cross-pollinated with 3.1e (Evaluation Zero — Empirical Sprint). Key themes: experiment-first philosophy applied to type system (annotate provisional, don't defer), circular import fix (EvaluatorConstants), process/outcome boundary enforcement across 4 touchpoints, per-run cost model ($0.60-0.80/Core workflow), GVS calibration minimum sample size, Spearman rho [0.3, 0.6) bootstrap CI, LLM-as-Judge no-go fallback protocol, scoring quality gate from real agent runs, Plan 03 parallelism opportunity.

**Pass 15 assessment (2026-02-23):** 57 items (41 IMP + 10 ADV + 3 SYN + 3 CSC). 47 merged, 3 rejected, 7 reframed. Pass 15 was a broad strategic alignment pass spanning 7 areas with 3.1e/3.1f cross-phase integration. Key themes: Design Completion Gate (stops further passes without empirical data), Plan 12/3.1f boundary (Parts 0-1 only, 40% scope reduction), coordinator context exhaustion boundary, parallel headless execution, 7-move validation Phase 0 for Plan 07, CalibrationConfig/CalibrationResult split, FailureSignal/InfrastructureFailureType mapping, 8 new cross-plan dependency rows, sequential calibration anchor, Standard-tier baseline exclusion.

**Pass 16 assessment (2026-02-23):** 1 item (1 IMP). 0 merged, 0 rejected, 0 reframed, 1 not-needed. Pass 16 intentionally recorded a convergence checkpoint with no new structural deltas because the Design Completion Gate remains unsatisfied. Cosmetic ratio: 100%.

**Pass 17 assessment (2026-02-25):** 14 items (7 IMP + 2 ADV + 1 SYN + 4 CSC). 12 merged, 0 rejected, 2 reframed. Pass 17 was a 3.1e cross-phase alignment pass — all 14 items structural, zero cosmetic. Key themes: heuristic scoring demotion to structural proxy (NONE validity), claude -p nested session restriction, three-tier fallback chain (replaces invalid heuristic-only), signal validity vocabulary (VALIDITY_CLAIM/STRUCTURAL_PROXY/PROVISIONAL), field stability tiers (Track A/B/C), evaluator independence caveat, 5 deferred items captured with dependency ordering, corpus composition audit for Gate 7, execution wave reconciliation.

**Final assessment (2026-02-25):** 17 improvement passes complete. 439 total items proposed. 373 merged, 22 rejected, 35 reframed, 1 deferred, 7 superseded, 1 not-needed. 0 active items remaining. Design Completion Gate still applies. CONTEXT.md is the canonical source of truth. Ready for `/msd:plan-phase 3.1c`.

**Pass 18 assessment (2026-02-25):** Empty convergence checkpoint. 0 items. Full convergence confirmed across all 4 improvement areas. No structural deltas.

**Pass 19 assessment (2026-02-26):** 14 items (14 IMP). 14 merged, 0 rejected, 0 reframed. Pass 19 was a plan-level structural gap analysis — all items address executor-facing failures in the plan files as authored, independent of any prior improvement pass content. Key themes: missing sequential dependency encoding in Wave 6 frontmatter (Plans 10+11), missing GO/NO-GO gate task (Plan 02), missing bridge transformer ownership (Plan 05), missing 3.1e schema deliverables (Plan 01), HITL checkpoint formalization as numbered tasks with disk artifacts (Plans 07+12), done criteria tightening for tool_use_id dependency (Plan 03), Wave 1/2 sequential ordering markers (Plans 06+03), joint 09a+10a gate encoding (Plan 09), stale line-number references replaced with section-name anchors across all 12 plans. Cosmetic ratio: 0%. Novel structural blockers: 8 distinct failure modes all discoverable from original plan files.

## Provenance Manifest

### Pass 11 Items
| Item ID | Verdict | Lens | Key Insight |
|---------|---------|------|-------------|
| P11-IMP-01 | enhanced | Hook Lifecycle Completeness | PreCompact/SessionEnd are observation-only (exit code 2 = N/A) |
| P11-IMP-02 | enhanced | Hook Configuration & Installation | `_ensure_hook()` silently drops async config |
| P11-IMP-04 | enhanced | Hook Lifecycle Completeness | Original missed trigger-type distinction |
| P11-IMP-06 | enhanced | Evaluator Reliability | effort_level not in BaselineKey corrupts baselines |
| P11-IMP-08 | enhanced | Hook Lifecycle Completeness | Hook MUST use inline stdlib JSONL parsing |
| P11-IMP-10 | enhanced | Evaluator Reliability | 66 combos not 10; disjoint-set constraint added |
| P11-IMP-11 | enhanced | Schema & Test Defense | Baseline exclusion assertion added |
| P11-IMP-12 | enhanced | Skill Architecture & Activation | JSONL contamination exit criterion added |
| P11-IMP-13 | enhanced | Skill Architecture & Activation | Fabricated SkillsBench claim struck |
| P11-IMP-15 | confirmed | Evaluator Reliability | Re-validation trigger and halt condition specific |

**Conflicts resolved:** None (single-pass file)
**Synthesis patterns:** SYN-01 Headless Mode Under-Verified (IMP-02, ADV-1-01, ADV-5-02), SYN-02 Evaluator Config Fragmentation (IMP-06, IMP-10, ADV-3-01)

### Pass 13 Items
| Item ID | Verdict | Lens | Key Insight |
|---------|---------|------|-------------|
| P13-IMP-01 | enhanced | Platform Schema Bugs | tool_output → tool_response — data loss bug |
| P13-IMP-05 | enhanced | Platform Schema Bugs | SessionStart `source` field for compaction detection |
| P13-IMP-06 | enhanced | Platform Schema Bugs | Two invented fields in SubagentStart spec |
| P13-IMP-07 | enhanced | Compaction Resilience | Session contamination from unbounded file loading |
| P13-IMP-08 | enhanced | Pipeline Elimination | Track A/B split; net ~330 LOC not 580 |
| P13-IMP-10 | enhanced | Pipeline Elimination | 3+1 essential hooks; schema enum stays full |
| P13-IMP-11 | confirmed | Pipeline Elimination | Subagent data in transcript + filesystem glob |
| P13-IMP-16 | enhanced | Evaluation Integrity | GVS/reasoning = transcript graders; rho < 0.3 = halt |
| P13-IMP-19 | enhanced | GVS Architecture | tool_sequence has tool names only; needs obs_summary |
| P13-ADV-1-01 | confirmed | Pipeline Elimination | CC waits for sync hooks; 600s timeout; race mitigated |

**Conflicts resolved:** IMP-08 vs IMP-14/ADV-3-01 — TranscriptParser wins as sole source; scoring items re-specified (SYN-01)
**Synthesis patterns:** SYN-01 GVS Data Requirements (IMP-08, IMP-19, ADV-3-01, ADV-3-02), SYN-02 TranscriptParser Platform Validation (IMP-08, IMP-10, IMP-11, IMP-12, ADV-2-02)

### Pass 14 Items
| Item ID | Verdict | Lens | Key Insight |
|---------|---------|------|-------------|
| P14-IMP-03 | confirmed | Experiment-First Overreach | Plan 02 builds 6 deliverables before its own hard prerequisite |
| P14-IMP-06 | enhanced | Technical Debt vs Premature Refactoring | Circular import: EvaluatorConstants.current() takes prompt_template_hash as parameter |
| P14-IMP-07 | enhanced | Experiment-First Overreach | Single-evaluator validation gate before debate protocol |
| P14-IMP-08 | confirmed | Experiment-First Overreach | 66-combo grid search on 3 transcripts is degenerate — minimum 10 sample gate |
| P14-IMP-09 | enhanced | Detection Baseline Alignment | Rubric text MUST describe reasoning process, NOT detection outcomes |
| P14-IMP-11 | enhanced | Technical Debt vs Premature Refactoring | Remove redundant JSON instruction when --json-schema active; temperature unavailable |
| P14-IMP-12 | enhanced | Detection Baseline Alignment | Three diagnostic-first steps replacing unstructured HALT |
| P14-IMP-14 | enhanced | Experiment-First Overreach | Known-good vs known-bad transcript fixtures from real agent runs |
| P14-IMP-16 | enhanced | Detection Baseline Alignment | Structural execution criteria only — outcome fields PROHIBITED in capability gates |
| P14-IMP-21 | enhanced | Cost & Calibration Grounding | Convergence threshold = max(2pt, 1.5 × per_dimension_sd) |
| P14-IMP-25 | enhanced | Cost & Calibration Grounding | Bootstrap CI for [0.3, 0.6) with three-branch decision tree |

**Conflicts resolved:** None (cross-pass alignment with P15 found no conflicts)
**Synthesis patterns:** P14-SYN-01 Process/Outcome Boundary Enforcement (IMP-09, IMP-12, IMP-16, ADV-3-01), P14-CSC-01 Scoring Quality Gate fixtures from real runs (IMP-14 cascade)

### Pass 15 Items
| Item ID | Verdict | Lens | Key Insight |
|---------|---------|------|-------------|
| P15-IMP-01 | enhanced | Scope Reduction Coherence | Design Completion Gate — stops further passes without empirical data |
| P15-IMP-02 | enhanced | Empirical Validation Demand | TP-only filter for rho diagnostic |
| P15-IMP-05 | enhanced | Pipeline Data Integrity | 5 bridge types (PROVISIONAL) vs ~27 internal types |
| P15-IMP-12 | enhanced | Scope Reduction Coherence | Plan 12 Parts 0-1 only; Parts 2-5 migrate to 3.1f |
| P15-IMP-13 | enhanced | Cross-Phase Interface Integrity | 4-value FailureSignal for 3.1f consumption |
| P15-IMP-17 | enhanced | Orchestration Architecture | Headless parallel safe; Agent Teams sequential |
| P15-IMP-37 | enhanced | Scope Reduction Coherence | Phase 1: 2 agents x 10 contracts with quality spread |
| P15-IMP-41 | enhanced | Pipeline Data Integrity | InfrastructureFailureType Literal enum at detection site |
| P15-ADV-4-01 | confirmed | Orchestration Architecture | Coordinator reads summary fields only; each claude -p gets own window |
| P15-SYN-02 | confirmed | Pipeline Data Integrity | 8 new cross-plan dependency rows preventing planning breakage |

**Conflicts resolved:** P15-IMP-36 absorbed into P15-IMP-12 (duplicate)
**Synthesis patterns:** P15-SYN-01 Plan 07 Validation Phase 0 (IMP-08, IMP-29, IMP-31), P15-SYN-02 Cross-Plan Dependencies (8 items), P15-SYN-03 CalibrationConfig/CalibrationResult split (IMP-02, IMP-31, IMP-37), P15-CSC-01 Baseline scoring_denominator_version (IMP-32 cascade), P15-CSC-02 Standard stubs baseline exclusion (IMP-38 + IMP-30 cascade), P15-CSC-03 FailureSignal/InfrastructureFailureType mapping (IMP-13 + IMP-41 cascade)

### Pass 17 Items
| Item ID | Verdict | Lens | Key Insight |
|---------|---------|------|-------------|
| P17-IMP-01 | enhanced | Heuristic Invalidation Cascade | Invalidation scope bounded to ranking signal; structural guard uses preserved |
| P17-IMP-02 | confirmed | Execution Model Constraint Discovery | claude -p nested restriction empirically validated by 3.1e |
| P17-IMP-05 | enhanced | 3.1e Data Integration | Concrete stratification thresholds (>60% cap, 3 min per cluster) |
| P17-IMP-06 | enhanced | Heuristic Invalidation Cascade | Three-tier fallback chain replaces invalid heuristic-only |
| P17-IMP-07 | enhanced | 3.1e Data Integration | Concrete plan mappings + dependency ordering (1->2->3, 4 parallel, 5 before Plan 01) |
| P17-ADV-2-01 | confirmed | Execution Model Constraint Discovery | Caveat + monitoring, not blocking gate (3.1e GO proved no bias) |
| P17-ADV-3-01 | confirmed | 3.1e Data Integration | Three-tier stability model: Track A stable, Track B provisional, Track C proxy |
| P17-SYN-01 | implemented | Cross-cutting | VALIDITY_CLAIM / STRUCTURAL_PROXY / PROVISIONAL vocabulary |
| P17-CSC-01 | implemented | Cascade | Exit gate heuristic thresholds reclassified as STRUCTURAL_PROXY_GUARD |
| P17-CSC-02 | implemented | Cascade | Corpus maintenance contract for Gate 7 stratification |

**Conflicts resolved:** None (single-pass file)
**Synthesis patterns:** P17-SYN-01 Signal Validity Vocabulary (IMP-01, ADV-3-01), P17-CSC-01 Exit Gate Heuristic Audit (IMP-01 cascade), P17-CSC-02 Corpus Maintenance Contract (IMP-05 cascade), P17-CSC-03 Fallback Tier Provenance (IMP-06 cascade), P17-CSC-04 Execution Wave Reconciliation (IMP-07 cascade)

### Pass 19 Items
| Item ID | Verdict | Lens | Key Insight |
|---------|---------|------|-------------|
| P19-IMP-01 | implemented | Plan Executor Integrity | Plan 10+11 Wave 6 sequential ordering missing from frontmatter |
| P19-IMP-02 | implemented | Done Criteria Precision | Plan 03 Task 2 accepts pre-hook transcripts — tool_use_id not verified |
| P19-IMP-03 | implemented | Missing Deliverable | Bridge transformer (3.1e Item 3) unassigned — Plan 07 gate fails opaquely |
| P19-IMP-04 | implemented | Missing Deliverable | 3.1e Items 4+5 unassigned in Plan 01 — schema pre-condition and guard missing |
| P19-IMP-05 | implemented | Missing Gate Task | No GO/NO-GO gate task in Plan 02 — Plan 04 permission gate has no producer |
| P19-IMP-06 | implemented | HITL Enforcement | HITL checkpoints in Plans 07+12 unnumbered with no disk artifact |
| P19-IMP-07 | implemented | Plan Executor Integrity | Plan 06 Wave 1 description contradicts frontmatter depends_on |
| P19-IMP-08 | implemented | Plan Executor Integrity | Plan 03 same-wave sequential dependency creates race condition |
| P19-IMP-09 | implemented | Plan Executor Integrity | Plans 10+11 BaselineManager concurrent write risk (duplicate of IMP-01 target) |
| P19-IMP-10 | implemented | Missing Deliverable | Bridge transformer has no plan owner (duplicate merged with IMP-03) |
| P19-IMP-11 | implemented | HITL Enforcement | Plan 12 Task 2 numbering gap confuses executors — merged with IMP-06 |
| P19-IMP-12 | implemented | Missing Deliverable | 3.1e Item 4 self-evaluation check "Plan 01 or 09" ambiguity resolved |
| P19-IMP-13 | implemented | HITL Enforcement | Joint 09a+10a gate not reflected in Plan 09 tasks or frontmatter |
| P19-IMP-14 | implemented | Documentation Staleness | Stale line-number references in all 12 plans — replaced with section-name anchors |

**Conflicts resolved:** IMP-01 and IMP-09 merged (both target Plan 10+11 sequential ordering — IMP-09 more complete). IMP-03 and IMP-10 merged (both target Plan 05 bridge transformer — IMP-03 more detailed). IMP-06 and IMP-11 merged (both target Plan 12 HITL Task 2 formalization).
**Synthesis patterns:** None (no adversarial items in this pass — all structural gaps from original plan files)

## Merged Summary

| Pass | Context | Plans | Research | Key Themes |
|------|---------|-------|----------|------------|
| 1 | 27 | 0 | 0 | Execution model, cascade DAG, 12-plan collapse, category contracts |
| 2 | 17 | 0 | 0 | Code-reality gaps, parser drops, keyword soup evaluator |
| 3 | 15 | 0 | 0 | Adversarial review (5 agents), parser errors, capability gating |
| 4 | 9 | 0 | 0 | PHILOSOPHY.md split, dead code, anti-fabrication |
| 5 | 28 | 0 | 0 | Schema hardening, tiered authoring, staging strategy |
| 6 | 22 | 0 | 0 | Agent Teams architecture, evaluation protocol hardening |
| 7 | 33 | 0 | 0 | Detection accuracy, external calibration, pattern testing, pipeline hardening |
| 8 | 21 | 0 | 0 | Plan summary restructuring, KCI taxonomy, info architecture |
| 9 | 20 | 0 | 0 | PHILOSOPHY.md alignment, schema field manifest, move applicability table, debate baseline, dual-layer diagram, failure protocol, manual trigger, LOC consolidation |
| 10 | 32 | 0 | 1 | CC hook lifecycle (12 events), zombie detection, session validity manifest, data quality aggregation, tier-mode binding, evaluator model binding, skill quality evaluation, budget reconciliation, experiment ledger storage |
| 11 | 22 | 0 | 1 | Hook enum correction (14 events), PreCompact/SessionEnd hooks, evaluator effort pinning, CalibrationConfig, EvaluatorConstants, negative fixtures, delegate mode, forced-eval, bifurcated hook installation, GVS Weight Calibration |
| 12 | 15 | 0 | 0 | Dimension registry (27 dims), schema migration script, ground_truth_rubric spec, Wave 6 schedule, debate ceiling, delegate mode SVM, P1 schema-first, evidence fidelity metric, scored concept governance |
| 13 | 26 | 0 | 0 | Passive hook elimination (TranscriptParser single source), PostToolUse field bug, SubagentStart transcript-based, GVS grader taxonomy, citation fidelity, ObservationParser→adapter, graduated graph_first_score, debrief_layer_weight, B_score_pre_exposure, _check_graph_first data model fix, PreCompact race resolved, PermissionRequest correction, SubagentStop deferred research |
| 14 | 25 | 0 | 1 | 3.1e cross-pollination, experiment-first philosophy, process/outcome boundary enforcement, per-run cost model, GVS minimum sample size, Spearman rho bootstrap CI, LLM-as-Judge no-go fallback, scoring quality gate fixtures, Plan 03 parallelism, EvaluatorConstants circular import fix |
| 15 | 46 | 0 | 1 | Design Completion Gate, Plan 12/3.1f boundary, coordinator context exhaustion, parallel headless execution, 7-move validation Phase 0, CalibrationConfig/CalibrationResult split, FailureSignal/InfrastructureFailureType mapping, 8 new cross-plan dependencies, sequential calibration anchor, Standard-tier baseline exclusion, 3.1e failure response matrix, cross-phase interface summary |
| 16 | 0 | 0 | 0 | Convergence checkpoint only (no structural deltas), explicit no-op under Design Completion Gate, route to plan-phase |
| 17 | 12 | 0 | 0 | 3.1e cross-phase alignment: heuristic demotion, claude -p restriction, three-tier fallback, signal validity vocabulary, field stability tiers, evaluator independence caveat, 5 deferred items, corpus audit, execution wave reconciliation |
| 18 | 0 | 0 | 0 | Empty convergence checkpoint — no structural deltas, Design Completion Gate in effect |
| 19 | 0 | 14 | 0 | Plan structural gaps: Wave 6 sequential ordering (Plans 10+11), GO/NO-GO gate task (Plan 02), bridge transformer ownership (Plan 05), 3.1e schema deliverables (Plan 01), HITL task formalization (Plans 07+12), done criteria tightening (Plan 03), wave sequential markers (Plans 06+03), joint 09a+10a gate (Plan 09), stale line refs all 12 plans |
