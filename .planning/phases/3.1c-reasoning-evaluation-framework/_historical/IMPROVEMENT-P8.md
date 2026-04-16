# Improvement Pass 8

**Pass:** 8
**Date:** 2026-02-19
**Prior passes read:** 1-6 (via IMPROVEMENT-DIGEST.md), 7 (active file)
**Areas:** Plan Summary Expansion, Information Architecture & Reference Separation, Known Code Issues Reclassification & Deduplication
**Agents spawned:** 3 improvement + 0 adversarial (pending)
**Status:** complete

<!-- File-level status: complete -->

## Improvements

### P8-IMP-01: Restructure All Plan Summaries from Prose to Structured Fields
**Target:** CONTEXT
**What:** Lines 677-898 contain 10 plan summary entries written as dense paragraphs mixing 5-7 distinct concerns per entry. Plan 02 (lines 700-718) embeds: fcntl fix, hook installation, tool_use_id capture, subagent start hook, real transcript capture, and exit criteria — all in a single paragraph with no visual separation. A planner must re-read the entire block to extract "what does Plan 02 produce?"

Replace each plan summary with consistent structured fields: Goal (1-2 sentences), Exists (what 3.1d built, with % pre-addressed), Deliverables (numbered list), Depends on, Blocks, Exit criteria, Location (matching Location Resolution table). Inline Depends-on/Blocks fields are LOCAL CONTEXT only — the Cross-Plan Dependencies table (IMP-02) is authoritative for dependency ordering. The "Exists" field becomes the sole location for "% pre-addressed" data IF IMP-07 is accepted (Scope Adjustments table deleted). Apply to all 10 plan entries.

**Why:** Plan summaries serve planners generating PLAN.md task breakdowns and cross-plan dependency resolution. Both need to scan deliverables and dependencies quickly. Prose paragraphs force linear reading. With 12 plans and 50+ cross-plan dependencies, the probability of missing an inline dependency is non-trivial.
**How:** Apply the 7-field structured format, with two implementation constraints:
1. Inline Depends-on/Blocks fields carry the note: "See Cross-Plan Dependencies table for authoritative ordering." They are NOT a parallel authoritative source.
2. The "Exists" field must be written while the Scope Adjustments table still exists as source material — apply IMP-01 before IMP-07.

Net document size: 10 plans currently 8-19 lines each become 12-16 lines each; field label overhead is offset by prose compression. Net change approximately neutral to +30 lines — acceptable given readability gain. Plans 09-11 handling: if IMP-03 split is accepted, three entries with IMP-01 format; if not, single merged entry with IMP-01 format.
**Impacts:** All plans — planner generating PLAN.md files will extract tasks more accurately
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — Structured plan summary formats are standard in project management
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Plan Summary Coherence):** The original How field created a dual-source-of-truth problem: inline Depends/Blocks fields would coexist with IMP-02's consolidated table, both claiming dependency authority. The rewrite constrains inline fields to local-context convenience only, making IMP-02 the single authoritative source. Second problem found: the proposed "Exists" field contains Scope Adjustments data that IMP-07 intends to delete — the ordering dependency between IMP-01 and IMP-07 was unacknowledged and must be explicit. Third: IMP-01's proposed Plan 02 example already uses the correct Location (`tests/workflow_harness/hooks/`) — this partially subsumes IMP-06. If IMP-01 is applied to all 10 plans including correct Location fields, IMP-06 is fully subsumed and the merge step should mark IMP-06 as satisfied by IMP-01.

---

### P8-IMP-02: Extract Cross-Plan Dependency Graph from Inline Mentions
**Target:** CONTEXT
**What:** At least 15 cross-plan dependency mentions are scattered across 220 lines of plan summary prose: "Blocked on Plan 02 delivering tool_use_id" (line 728), "fallback replacement requires Plan 02 node ID capture" (line 741), "Ordering dependency: IMP-07 before IMP-04" (line 768), "Prestep P3 must complete before Core sub-wave begins" (line 854).

Add a "Cross-Plan Dependencies" section with an exhaustive dependency table (minimum 15 rows, populated by full scan of lines 677-898 for all "Blocked on", "requires Plan", "depends on", "before", "needed by" occurrences). The table is the authoritative reference; inline plan summary mentions remain for local reading convenience only. A table header note must state: "Authoritative. Inline plan summary Depends/Blocks fields are convenience-only."

**Why:** Dependencies are the most critical planning input. Buried in prose, a planner building PLAN.md task breakdowns can miss ordering constraints. The Depends on/Blocks fields in IMP-01 partially address this, but a consolidated table provides a single scannable reference.
**How:** Add a "Cross-Plan Dependencies" subsection:
```markdown
## Cross-Plan Dependencies
<!-- AUTHORITATIVE: Inline plan summary Depends/Blocks fields are convenience-only. -->
| From | To | What | Hard? |
|------|----|------|-------|
| 02 | 03 | tool_use_id in hook payloads | YES |
| 02 | 04 | BSKG query result node IDs | YES |
| 02 | 09-11 | Hook installation API | YES |
| 05 (IMP-07) | 05 (IMP-04) | Debrief prompt before validator | YES |
| 06 (coverage_axes) | 12 (coverage_radar) | Schema field must exist | YES |
| P0 (real transcripts) | 03-12 | Parser validation on real data | YES |
| P3 (marker stripping) | 09-11 | Clean corpus contracts | YES |
| 01 | all | Data models consumed everywhere | NO |
| [7+ rows from full scan] | ... | ... | ... |
```
**Impacts:** All plans — planner can verify dependency ordering at a glance
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — Dependency tables are standard practice
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Plan Summary Coherence):** The original How field showed an 8-row example table against a claimed 15+ dependencies — if the table ships with only 8 rows, it creates false confidence that the dependency set is exhaustive. The rewrite commits to exhaustive extraction via full prose scan and requires minimum 15 rows. Specific gaps in the 8-row example that must be added: (1) Plan 08 runner disk-read path for DebriefResponse depends on Plan 05 producing the serialized artifact — not in the example table; (2) Plan 12 Part 0 Calibration Anchor depends on corpus/ground_truth.yaml existing and being clean — a data dependency, not a plan-to-plan dependency; the table format should accommodate this with a "From" of "P2 (corpus ground truth)"; (3) Plan 07 Reasoning Evaluator depends on Plan 06 contracts to know which dimensions to evaluate — also missing. The table header comment establishing authoritative status (vs inline fields) is added to prevent the dual-source-of-truth problem identified in IMP-01.

---

### P8-IMP-03: Split Plans 09-11 Summary into Separate Entries
**Target:** CONTEXT
**What:** Lines 840-861 present Plans 09, 10, and 11 as a single merged entry (22 lines dense prose) covering: CC skill architecture, 51 workflow tests across 3 categories, staged rollout, debrief trigger, and pytest wrapper strategy. The Scope Adjustments and Location Resolution tables list them separately.
**Why:** A planner cannot determine from the merged entry what tasks belong to skill testing vs agent testing vs orchestrator testing. The staged rollout (sub-waves a/b/c) maps to the 3 categories but this mapping is implicit.
**How:** Split into three entries with IMP-01 structured fields, plus a shared execution note. At minimum, one fully worked example entry must be specified before implementation. Distinct content by plan: Plan 09 deliverables are 30 skill contracts and sub-wave (b) execution; Plan 10 deliverables are 21 agent behavioral contracts and HITL gate on Core tier; Plan 11 deliverables are orchestrator flow lifecycle and multi-agent coherence scoring. Shared content (CC skill architecture, AgentSpawner usage, debrief trigger) goes into the shared execution note — not repeated in all three entries.
```markdown
### 3.1c-09: Skill Evaluation Tests (30 skills)
[IMP-01 structured fields] — Sub-wave (b): Important tier ~15
### 3.1c-10: Agent Evaluation Tests (21 agents)
[IMP-01 structured fields] — Sub-wave (a): Core tier ~10 with HITL gate
### 3.1c-11: Orchestrator Evaluation Tests
[IMP-01 structured fields] — Cross-agent coherence, full team lifecycle
> **Shared Execution Note:** Plans 09-11 share `/vrs-test-suite` CC skill and AgentSpawner parallel execution. Debrief trigger step is identical across all three. Listed separately for distinct deliverables, exit criteria, tier rollout gates, and dependency profiles (Plans 09 and 10 do not require multi-agent ground truth P1; Plan 11 does).
```
**Impacts:** Plans 09, 10, 11 — planner generates 3 distinct PLAN.md files
**Research needed:** no
**Confidence:** MEDIUM — risk of redundancy since infrastructure IS shared, but planner needs task-level clarity
**Prior art:** 4 — Standard to have separate plans for distinct deliverable sets
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Plan Summary Coherence):** The original How field used "[structured fields]" placeholders that make it impossible to verify the split produces clarity rather than thin redundant entries. The rewrite specifies what genuinely differs per plan (deliverables, exit criteria, tier rollout gates, dependency profiles) vs what goes into the shared execution note. The key justification for the split is the P1 dependency asymmetry: Plan 11 (Orchestrator Tests) requires multi-agent ground truth entries (Prestep P1 — 10-15 templates), but Plans 09 and 10 do not. A merged entry obscures this difference, causing a planner to either apply P1 as a prerequisite for all three (over-blocking Plans 09/10) or miss it for Plan 11 (under-blocking). The shared execution note must be placed once before the three entries, not repeated inside each, to avoid the redundancy risk that justified MEDIUM confidence.

---

### P8-IMP-04: Deduplicate Plan Summary Content Against Known Code Issues
**Target:** CONTEXT
**What:** Plan summaries in Plans 02, 04, and 07 contain problem descriptions that are already the primary content of Known Code Issues entries. The duplication is not symmetric: plan summaries contain both the problem description (which belongs in KCI) AND the fix description (which belongs in the plan summary). These two concerns are currently conflated in prose.

**Original framing:** "Replace duplicated problem descriptions with cross-references to KCI entries by name."

**Why:** The original DRY framing is correct in goal but wrong in mechanism. The counter-argument dismissed as MEDIUM confidence — "plan summaries should be self-contained" — is actually the stronger position for a planning document. A planner working on Plan 02 must not need to navigate to KCI to understand what they are implementing. The real problem is not duplication per se; it is that problem descriptions and fix descriptions are unsegregated within the same prose block, making it hard to tell "what this plan owns" from "what the bug is."
**How:** In each of the 5 identified plan summary locations, segregate problem description from fix description:
- Problem description: add ONE sentence referencing the KCI entry by name: "See KCI: [Entry Name] for bug analysis."
- Fix description: keep in full in plan summary — this is what the planner needs.

Apply AFTER IMP-11 (KCI subsection split) so references use stable post-restructure heading names. Do not apply before IMP-11 — pre-IMP-11 heading names may change.

Five targets:
1. Plan 02 threading.Lock: "See KCI: ObservationWriter Threading Lock. Fix: replace with fcntl.flock() + platform fallback (~20 LOC)."
2. Plan 04 citation rate: "See KCI: Citation Rate Fallback Is Keyword Soup. Fix: observation-based structural matching using BSKG node IDs from Plan 02."
3. Plan 04 graph-first: "See KCI: Graph-First Compliance Check Assumes Any Bash. Fix: filter tool_sequence for alphaswarm substrings (~5 LOC)."
4. Plan 07 keyword matching: "See KCI: _check_model_capability Is Naive Keyword Matching. Fix: replace with LLM call via claude -p --output-format json (~30 LOC)."
5. Plan 02 tool_use_id: "See KCI: Hooks Do Not Capture tool_use_id. Fix: extract tool_use_id in obs_tool_use.py and obs_tool_result.py (hard gate)."
**Impacts:** Plans 02, 04, 07 — reduced prose, fix description stays self-contained, problem description referenced not repeated
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 5 — DRY principle applied with self-containment constraint
**Prerequisite:** IMP-11 must be applied first to establish stable KCI heading names
**Status:** implemented

**Original framing:** "Deduplicate plan summary content by replacing problem descriptions with cross-references to KCI entries."

**Adversarial note (Plan Summary Coherence):** The original framing proposed replacing the full duplicated prose block with a cross-reference, trading self-containment for DRY. The reframe preserves self-containment for the fix description (what the planner needs) while adding a single-sentence pointer for the problem description (what belongs in KCI). This is a stronger position: plan summaries remain useful without context-switching, and KCI remains the single source of truth for bug analysis. The prerequisite on IMP-11 is a genuine blocking dependency: IMP-04 references KCI entries by heading name, and IMP-11 will rename those headings as part of the subsection restructure. If IMP-04 is applied before IMP-11 using current heading names (e.g., "Citation Rate Fallback Is Keyword Soup"), the references will break after IMP-11 restructures KCI. Execution constraint: IMP-11 first, IMP-04 second.

---

### P8-IMP-05: Plan 12 Summary Needs Internal Structure
**Target:** CONTEXT
**What:** Plan 12 (lines 863-898) is 36 lines containing 6 work streams (Parts 0-5 + CLI subcommand) with unstated internal dependencies, in a single paragraph flow.
**Why:** Plan 12 is effectively 6 plans compressed into one. Parts have internal dependencies (Part 0 before Part 1, Part 1 before Part 2) that are not stated explicitly.
**How:** Apply IMP-01 structured format with sub-structure for 6 parts:
```markdown
**Parts (sequential: 0 → 1 → 2 → 3; Parts 4-5 parallel to 2-3):**
**Part 0 — Calibration Anchor (ADV-03):** 4 Core agents on 18 corpus contracts, compare against ground_truth.yaml
**Part 1 — Baseline:** All 51 tests 1x; Core 5x for variance; keyed by (workflow_id, run_mode)
**Part 2 — Improvement:** Low-scoring dimensions → Jujutsu sandbox → sequential variants
[...etc...]
```
**Impacts:** Plan 12 task generation accuracy
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — Standard to break large plans into sub-phases
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Plan Summary Coherence):** Plan 12's current 36-line prose at lines 863-898 genuinely encodes sequential Part dependencies (0→1→2→3, Parts 4-5 parallel) that are completely invisible in the prose flow. A planner generating PLAN.md tasks would miss that Part 0 (Calibration Anchor) is a hard prerequisite for accepting improvement hints — documented in the Calibration Anchor Protocol Implementation Decision but not linked to Part ordering in Plan 12's summary. The proposed sub-structure with explicit sequential notation (0→1→2→3) is the minimum needed. IMP-05 is complementary to IMP-01 (IMP-01 applies the 7-field wrapper; IMP-05 adds Plan 12-specific depth within the Deliverables field) and creates no conflicts with other improvements. No second-order risks identified specific to this item.

---

### P8-IMP-06: Plan Summary Location Fields Contradict Location Resolution Table
**Target:** CONTEXT
**What:** Plan summary Location fields use aspirational paths (`src/alphaswarm_sol/evaluation/`) that contradict the authoritative Location Resolution table. Confirmed contradictions in 6 plan summaries that have components listed in the Location Resolution table:
- Plan 01: `src/alphaswarm_sol/evaluation/models.py` vs actual `src/alphaswarm_sol/testing/evaluation/models.py` (missing `/testing/` segment)
- Plan 02: `src/alphaswarm_sol/evaluation/hooks/` vs actual `tests/workflow_harness/hooks/` (entirely different tree)
- Plan 03: `src/alphaswarm_sol/evaluation/parser.py` vs actual `tests/workflow_harness/lib/observation_parser.py`
- Plan 04: `src/alphaswarm_sol/evaluation/graph_scorer.py` vs actual `tests/workflow_harness/graders/graph_value_scorer.py`
- Plan 05: `src/alphaswarm_sol/evaluation/debrief.py` vs actual `tests/workflow_harness/lib/debrief_protocol.py`
- Plan 07: `src/alphaswarm_sol/evaluation/evaluator.py` vs actual `tests/workflow_harness/graders/reasoning_evaluator.py`
- Plan 08: `src/alphaswarm_sol/evaluation/runner.py` vs actual `tests/workflow_harness/lib/evaluation_runner.py`

Note: Plan 12's location fields (`src/alphaswarm_sol/evaluation/improvement.py`, etc.) reference files that do not yet exist — they are intended locations for NEW files, not contradictions with the Location Resolution table (which has no entries for Plan 12 components). Plan 12 should retain a note: "These files will be created at these paths during Plan 12 execution."
**Why:** Highest-severity concrete failure: a planner will use the Location field (most proximate reference) and generate tasks targeting non-existent paths. The Location Resolution heading explicitly says "3.1c plans extend code at actual locations, NOT originally planned paths" — plan summaries contradict this.
**How:** Update all 7 plan summary Location fields (Plans 01-08 that have Location Resolution entries) to match the Location Resolution table. Add inline note to Plan 12: "Paths above are intended future locations; files created during Plan 12 execution." If IMP-01 is implemented first with correct Location fields for all plans, this improvement is fully subsumed — the merge step should mark IMP-06 as satisfied by IMP-01.
**Impacts:** Plans 01-08 — correct file paths prevent PLAN.md task breakdowns targeting non-existent directories
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — Keeping file paths consistent is basic documentation hygiene
**Prerequisite:** no
**Status:** implemented (subsumed by IMP-01)

**Adversarial note (Plan Summary Coherence):** The original "7 of 8" count was imprecise — the correct count is 7 contradictions across plans 01-08 (not "7 of 8 plan summaries" since the merged Plans 09-11 entry correctly uses the Location Resolution paths). Verified by grep: plan summaries use `src/alphaswarm_sol/evaluation/` while Location Resolution uses `src/alphaswarm_sol/testing/evaluation/` (Models, Contracts) and `tests/workflow_harness/` (Hooks, Parser, Scorer, Evaluator, Runner, Debrief). These are genuinely different paths that would cause a planner to create files in non-existent directories. The Plan 12 scoping addition is critical: Plan 12 locations ARE aspirational (new files being created), not wrong references to existing files. Treating Plan 12 like Plans 01-08 would change its location fields from correct intent to wrong correction. Subsumed-by-IMP-01 note added: if IMP-01 uses correct Location fields for all 10 plans, this improvement is redundant and should be collapsed at merge time.

---

### P8-IMP-07: Collapse 3.1d Deliverables Section Into 5-Line Operational Summary
**Target:** CONTEXT
**What:** Lines 22-72 contain three subsections: "What 3.1d Built" (20-row table), "What Was Fabricated" (3-row table), and "Plan Scope Adjustments" (12-row table) — ~50 lines total. The deliverables table duplicates Location Resolution. The fabrication audit is historical. The scope adjustments duplicate plan summaries (each already states "~N% pre-addressed").
**Why:** Three distinct content types mixed without markers: audit trail, reference lookup, and planning context. A planner burns 50 lines on context they already have (from plan summaries) or never need again (fabrication history).
**How:** Replace the entire section with:
```markdown
## 3.1d Pre-Existing Work
Phase 3.1d built 17 components (models, hooks, parser, scorers, runner, skills, agent).
See Location Resolution table for actual file paths. Per-plan scope adjustments are
noted in each Plan Summary. **Critical fact:** Zero real transcripts exist — all
fabricated data was deleted in quality audit. Plan 02 must capture 3+ real transcripts.
```
Delete all three sub-tables. Information preserved in: Location Resolution (paths), plan summaries (scope %), Known Code Issues "All Tests Use Synthetic Data" (fabrication consequence).
**Impacts:** No plan impact — information deduplicated, not removed. Saves ~45 lines.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — Standard document refactoring
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Information Architecture Integrity):** The "information preserved elsewhere" claim must be verified for each deleted sub-table before this can be executed. Verification: (1) The 20-row "What 3.1d Built" table contains Status column values ("Genuine", "Installed but need real run validation", "Working JSON Schema validation") that are NOT in Location Resolution, which has only Component|Actual Location columns. These status values inform a plan author whether a component is trustworthy or suspect — the debrief_protocol.py entry has a detailed multi-layer status not captured anywhere else. (2) The fabrication table's third row ("Calibration score claims... was circular") is not in Known Code Issues under any entry — only the transcript deletion is noted. (3) The Scope Adjustments table's per-plan % estimates ARE partially in plan summaries but in a different form: "~30% pre-addressed" in the table versus "Remaining scope: Replace threading.Lock..." prose in the summary. The % figures provide a quick scan signal not available in prose. Rewrite: The How must explicitly confirm each of these three information classes is either truly redundant (with pointer to where it lives) or must be migrated before deletion — not assumed eliminated. The current proposal risks removing the Status column context (hook trustworthiness) and the specific calibration fabrication narrative. Revised How: (1) Migrate Status column values to Location Resolution as a third column ("Validation Status"). (2) Migrate the calibration fabrication detail to the "All Tests Use Synthetic Data" KCI entry — one sentence. (3) Then collapse. The 5-line summary is correct in form; the deletion sequence must be explicit.

---

### P8-IMP-08: Mark Infrastructure Available Section as Reference-Only
**Target:** CONTEXT
**What:** Lines 406-463 contain ~57 lines of Component|File|LOC|Relevance tables listing all 3.1b infrastructure. This is pure reference data — improvement agents cannot meaningfully improve "ClaudeCodeRunner | harness/runner.py | 510 | 3.1c-08 execution engine."
**Why:** Reference tables are not improvable content. They waste improvement pass budget and may generate proposals like "update LOC counts." Useful exactly once: when a plan author needs to know what exists.
**How:** Add a skip directive:
```markdown
## Infrastructure Available (from 3.1b)
<!-- REFERENCE-ONLY: Inventory of existing code. Not subject to improvement review.
     Consult when writing plans. Do not propose changes to this section. -->
```
**Impacts:** Reduces noise in future improvement passes. No plan impact.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — Common in large specs to mark sections as reference-only
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Information Architecture Integrity):** The mechanism is HTML comments in Markdown. The assumption that improvement agents will honor this directive requires examination. In this project, improvement agents are Claude Code subagents reading CONTEXT.md directly — they are LLMs, not static analysis tools. An HTML comment `<!-- REFERENCE-ONLY: ... Do not propose changes to this section. -->` is readable text that an LLM will see and likely follow, since instruction-following is a trained behavior. However, this is probabilistic, not enforced: a future improvement agent with a different framing prompt may not have the comment in scope, or may treat it as a soft suggestion. The improvement is still net positive — the comment reduces the probability of noise proposals without eliminating it — but the confidence claim of HIGH overstates the mechanism's reliability. The How should be expanded to include: (1) The comment text above, which is correct. (2) A note in the improvement pass header or a pass-level directive: "Sections marked REFERENCE-ONLY are excluded from improvement scope in this pass" — giving the skip signal at the agent instruction level, not just the content level. Two-layer signaling (content + prompt) is more robust than one. The improvement is valid; the mechanism needs a second layer.

---

### P8-IMP-09: Deduplicate ObservationWriter Threading Bug Across Three Locations
**Target:** CONTEXT
**What:** The threading.Lock issue appears in: (1) Line 63 in Scope Adjustments ("ObservationWriter uses threading.Lock"), (2) Lines 704-707 in Plan 02 summary ("Replace threading.Lock() with fcntl.flock()"), and (3) implicitly in Known Code Issues where hooks are described as needing validation. Three locations for one bug.
**Why:** Duplicated bug descriptions create drift risk. Single-source-of-truth: describe the bug once in Known Code Issues, describe the fix once in Plan 02.
**How:** If IMP-07 is accepted (scope adjustments table deleted), occurrence (1) disappears. Add explicit KCI entry: "ObservationWriter uses threading.Lock — no-op for inter-process concurrency. Fix: fcntl.flock() with platform fallback. Owner: Plan 02." Plan 02 retains fix description.
**Impacts:** Plan 02 — reduced duplication
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — Standard deduplication
**Prerequisite:** no — but synergizes with IMP-07
**Status:** implemented

**Adversarial note (Information Architecture Integrity):** The claim of "three locations" is partially false. The actual count and nature of locations are: (1) Line 63, Scope Adjustments — explicitly states "ObservationWriter uses threading.Lock (no-op for inter-process concurrency)." REAL occurrence. (2) Lines 704-707, Plan 02 summary — explicitly states "Replace threading.Lock() with fcntl.flock()." REAL occurrence. (3) "Implicitly in Known Code Issues where hooks are described as needing validation" — this is a mischaracterization. The KCI entry "Hook Scripts Exist But Need Real Validation" (lines 480-484) describes hooks needing validation against real sessions, not the threading.Lock bug specifically. There is NO existing KCI entry for threading.Lock. The improvement's proposed fix is actually: add a NEW KCI entry (which doesn't exist yet), not deduplicate an existing one. This changes the nature of the work: it's not deduplication, it's extraction-and-creation. The How should say: "Extract threading.Lock bug from Scope Adjustments table into a new KCI entry (it has no KCI entry currently). Delete from Scope Adjustments (or rely on IMP-07). Plan 02 summary retains fix description but adds 'see KCI: ObservationWriter threading.Lock' pointer." The "three locations, reduce to one" framing also conflicts with the outcome: if IMP-07 passes, there are still two locations (new KCI entry + Plan 02 summary) not one. One location is not achievable without removing Plan 02's fix description, which would degrade Plan 02's self-containedness.

---

### P8-IMP-10: Add Section Purpose Headers to Distinguish Content Types
**Target:** CONTEXT
**What:** CONTEXT.md has 13 top-level sections across 1170 lines. Some are actionable (Implementation Decisions, Plan Summaries, Exit Gate), others reference (Infrastructure, Location Resolution), others structural (Architecture, Smart Selection Matrix). Currently all sections look identical.
**Why:** A planner or improvement agent has no signal about which sections to read carefully vs skim vs skip. Implementation Decisions (75-348) is the most important section; Architecture (925-977) rarely changes.
**How:** Add one-line purpose comment after each `##` heading:
```markdown
## Implementation Decisions (Locked)
<!-- BINDING: Constrain all plans. Changes require explicit justification. -->

## Infrastructure Available (from 3.1b)
<!-- REFERENCE: Existing code inventory. Consult when writing plans. -->

## Known Code Issues
<!-- ACTIONABLE: Bugs with plan assignments. Review when writing affected plans. -->

## Architecture
<!-- STRUCTURAL: Design overview. Rarely changes after initial design. -->
```
13 one-line additions across 1170 lines.
**Impacts:** Future passes and planners can triage reading effort
**Research needed:** no
**Confidence:** MEDIUM — value depends on whether consumers read comments
**Prior art:** 3 — Some large specs use section classification
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Information Architecture Integrity):** Withstands scrutiny on three dimensions. (1) Conflict check with IMP-08: IMP-08 adds a skip directive to the Infrastructure section; IMP-10 adds a purpose header to the same section. These are compatible — IMP-10's `<!-- REFERENCE: ... -->` and IMP-08's `<!-- REFERENCE-ONLY: ... Do not propose changes ... -->` can coexist or be merged into one comment. No conflict. (2) Mechanism validity: as noted for IMP-08, HTML comments are visible to LLM improvement agents — the signal is probabilistic but real. The MEDIUM confidence rating accurately reflects this. (3) Coverage: all 13 sections need headers; the proposal lists only 4 examples but commits to 13 additions. The How is complete in intent if not in enumeration. The four-label vocabulary (BINDING, REFERENCE, ACTIONABLE, STRUCTURAL) is sufficiently orthogonal to classify all sections without overlap. Second-order note: if IMP-10 is implemented before IMP-08, the Infrastructure section gets two comments — minor redundancy, harmless.

---

### P8-IMP-11: Split Known Code Issues into Three Typed Subsections
**Target:** CONTEXT
**What:** The Known Code Issues section (lines 466-608) contains 20 items in three distinct types presented as a flat list: (A) bugs with specific plan assignments and fix descriptions (9 items), (B) cross-cutting constraints affecting multiple plans (6 items), (C) informational pointers/status observations (5 items). A plan implementer looking for "what bugs does Plan 04 own?" must scan all 20 items. 6 prior passes with 118 merged improvements never proposed this split, meaning every pass re-read and re-interpreted the mixed list.
**Why:** The three-way split serves genuinely different readers: plan authors need (A) to build their task lists, architects need (B) to understand cross-plan risk, and new contributors need (C) to orient themselves. The flat list imposes the most expensive reader role — full triage — on everyone regardless of their actual need. The summary table enables further triage without even entering subsections.
**How:** Reorganize into three subsections with a summary table at top. The 20 items must be classified explicitly — implementer must produce a classification manifest before restructuring to avoid ad hoc decisions on borderline items. Known hard cases: "Pipeline Integration Constraints" is a composite heading spanning types (A), (B), and (C) and must be decomposed rather than placed wholesale (see P8-ADV-02). "Corpus Contracts Have Embedded Vulnerability Markers" is a resolved item (Prestep P3, commit 97f6fd4b) and belongs in (C) as historical context, not in (A). The summary table with Owner and Severity columns must be authored from scratch:
```markdown
## Known Code Issues
<!-- ACTIONABLE: Bugs with plan assignments. Review when writing affected plans. -->
| Issue | Type | Owner | Severity |
|-------|------|-------|----------|
| Observation Pairing Broken | Bug | Plan 02 | CRITICAL |
| Graph-First Compliance | Bug | Plan 04 | HIGH |
| ...18 more rows... |

### A. Bugs (Plan-Assigned)
<!-- Each entry: title, owning plan, fix description, cross-plan dependencies -->

### B. Cross-Cutting Constraints
<!-- Items affecting multiple plans or the pipeline as a whole -->

### C. Status Notes & Pointers
<!-- Informational items: decisions needed, disambiguation, incomplete features -->
```
**Impacts:** All plans — easier scanning. Particularly Plan 02 (3 bugs) and Plan 04 (2 bugs). Subsection (C) becomes the landing zone for IMP-17 and IMP-18 relocations. IMP-12 target goes to Infrastructure Available (not subsection C). IMP-14 targets are deleted entirely (not moved to C).
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — Standard document organization
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Known Code Issues Taxonomy):** The original How gave no guidance on borderline cases. Two classification problems are visible from reading the actual 20 items against the proposed taxonomy. First, the "Pipeline Integration Constraints" entry (lines 580-588) is a composite of four bullets spanning all three types: "Evaluator MUST receive CollectedOutput" is type B, "Plugins receive optional `context` kwarg" is type A (a live API bug per DC-3, not a constraint), "Contract loader resolves workflow IDs" is type B, "Scenario `expected_tools` has no consumer" is type C. Placing this composite entry in one subsection misleads all readers about the nature of three of its four bullets. Second, "Corpus Contracts Have Embedded Vulnerability Markers" (lines 492-498) is described as if still active, but Prestep P3 (commit 97f6fd4b) already resolved it. Placing it in subsection A implies an open bug. Both classification decisions are now explicit in the How. Also added the ACTIONABLE comment directive that IMP-10 introduces, since IMP-10 and IMP-11 both modify the same section header and must be consistent.

<!-- Merged from: Area 2 IMP-04 (summary table concept) + Area 3 IMP-01 (three-way taxonomy). Combined: three-way split WITH summary table. -->

---

### P8-IMP-12: Remove "Hook Input Schemas Documented" from Issues Section
**Target:** CONTEXT
**What:** Lines 505-508 is not an issue, bug, or constraint — it's a pointer to reference documentation. "3.1c-02 hook developers should read this first" is a prerequisite pointer.
**Why:** Pointers in a "Known Code Issues" section dilute signal. Readers expect problems or risks.
**How:** Move to Infrastructure Available section as a row: `| Hook Input Schemas | .vrs/debug/phase-3.1b/research/hook-verification-findings.md | N/A | 3.1c-02 prerequisite reading |`. Delete from Known Code Issues.
**Impacts:** Plan 02 clarity — prerequisite reading co-located with infrastructure inventory
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — Moving reference pointers to reference sections
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Known Code Issues Taxonomy):** Withstands scrutiny. The item at lines 505-508 carries zero actionable content — it only says "a document exists, go read it." Its presence in KCI has two harms: it dilutes signal for readers scanning for actual problems, and it could mislead improvement agents into proposing updates to the KCI entry rather than to the referenced document. Moving it to Infrastructure Available co-locates it with the hook scripts it describes. No conflict with IMP-11: this item should go to Infrastructure Available rather than KCI subsection C, because it is reference material for plan authors rather than a status note about the project state. No information loss risk.

---

### P8-IMP-13: Deduplicate Plan-Assigned Bugs Against Scope Adjustments Table
**Target:** CONTEXT
**What:** Scope Adjustments table (lines 58-71) paraphrases bugs already detailed in Known Code Issues and plan summaries. Example: "ObservationWriter uses threading.Lock" in scope table, "Hooks Do Not Capture tool_use_id" in KCI, "~30% pre-addressed" in Plan 02 summary — three locations for related facts.
**Why:** If someone updates one location but not the others, they drift. Bugs should carry detail; scope table should reference them.
**How:** If IMP-07 is accepted (scope table deleted), this resolves automatically. If not: add cross-references in both directions — scope table entries reference KCI entries by name, KCI entries note their plan ownership.
**Impacts:** Plans 02, 04, 07 — reduced drift risk
**Research needed:** no
**Confidence:** MEDIUM — format requires judgment
**Prior art:** 4 — Single-source-of-truth practice
**Prerequisite:** no — synergizes with IMP-07
**Status:** implemented (resolved by IMP-07)

**Adversarial note (Known Code Issues Taxonomy):** Structurally correct. One nuance: if IMP-07 is accepted but its How is not updated per the Information Architecture reviewer's note (migrate Status column values before deletion), the scope table disappears along with its bug paraphrases, but the threading.Lock entry still has no KCI home until IMP-09 creates it. IMP-13 is safe if executed in this order: IMP-09 (create threading.Lock KCI entry) then IMP-07 (delete scope table) then IMP-13 is already resolved. If IMP-07 is rejected, IMP-13's cross-reference path is valid. Confidence should be HIGH when conditioned on IMP-07 acceptance (nominal case), MEDIUM only for the standalone path.

---

### P8-IMP-14: Migrate "Skill Specs" and "Agent Specs" Entries Out of Issues
**Target:** CONTEXT
**What:** Lines 597-607: "Skill Specs Lack Capability Contracts" and "Agent Specs Lack Behavioral Contracts" describe Plan 06 scope — the need to author evaluation contracts from scratch (51 contracts, ~5,135 lines of agent spec prose to derive from). These are not bugs (nothing is broken), not constraints, and not issues. They describe work that hasn't been done yet, which is exactly what Plan 06 is for.
**Why:** Framing plan scope as "known code issues" implies something is wrong with current code, creating noise for readers scanning for actual problems. The entries carry genuinely useful information — they quantify the authoring challenge (30 skills, 21 agents, ~5,135 lines of prose, four authoring tiers) — but this information belongs in the Plan 06 summary, not in a bugs list.
**How:** Remove both entries from KCI. Before deleting, verify that the Plan 06 summary captures: (1) the authoring challenge quantification (~5,135 lines of agent spec prose, no machine-readable contracts exist), (2) the authoring order constraint (investigation → orchestrator → synthesis → tools), (3) the three-tier authoring policy (Core hand-authored now, Important stub+placeholder, Standard deferred). The Plan 06 summary at lines 772-790 currently contains "Evaluation contracts must be manually derived from ~5,135 lines of agent spec prose. Author in dependency order: investigation agents first, then orchestrator, then synthesis, then tools." — this detail IS present, so deletion is safe. If IMP-01 restructuring of Plan 06 is applied first, verify it preserves these details before proceeding.
**Impacts:** Plan 06 summary absorbs the authoring challenge detail; KCI signal improved for all other plan authors who currently must read past scope descriptions to find actual bugs.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — Removing scope descriptions from bug lists
**Prerequisite:** IMP-01 restructuring of Plan 06 summary should be verified (or applied atomically) before deletion to ensure the quantification detail is not lost. Deletion without verification risks losing the authoring order constraint if IMP-01 omits it from the restructured entry.
**Status:** implemented

**Adversarial note (Known Code Issues Taxonomy):** The lens brief asked whether these entries serve as "reminders that Plan 06 faces a significant authoring challenge." They do — and that is the problem. A bugs list is the wrong delivery mechanism for challenge reminders: readers scanning KCI for problems must mentally filter out scope descriptions, and improvement agents may propose fixes for "issues" that are not broken. The key finding from examining the actual CONTEXT.md: the Plan 06 summary currently carries the ~5,135 lines quantification and the authoring order constraint (lines 772-790), so deletion is safe without new content creation. The original How said only "Verify Plan 06 scope adjustments and summary capture authoring order detail" — insufficient specificity. The rewrite adds an explicit verification checklist and confirms which detail is already present. Second-order risk: if IMP-01 restructures Plan 06 incorrectly and loses the authoring order, there is no other source. The prerequisite field is updated to reflect this dependency.

---

### P8-IMP-15: Consolidate Three tool_use_id / Parallel Pairing Entries into One
**Target:** CONTEXT
**What:** Three separate entries describe one causal chain: (1) "Hooks Do Not Capture tool_use_id" (lines 566-571), (2) "Parallel Tool Calls Corrupt Observation Pairing" (lines 573-578), (3) LIFO pairing mention inside the "Pipeline Integration Constraints" entry (which is itself a composite type-B/type-A entry). Missing tool_use_id → LIFO pairing → parallel call corruption → wrong scores downstream in Plans 04, 07, 08. The HARD EXIT CRITERION label (IMP-09) currently appears only in entry (1) — a reader who reads only entry (2) does not know this is a hard gate.
**Why:** Three entries for one causal chain create three update targets, three surfaces for improvement agents to propose duplicate fixes, and force a reader to mentally reconstruct the causal chain from three separate readings. Consolidation also resolves the HARD EXIT CRITERION visibility problem: the gate label will appear in the single entry that describes the complete chain.
**How:** Replace entries (1) and (2) in KCI with one consolidated root-cause entry under subsection A (after IMP-11 is applied). For the LIFO mention inside Pipeline Integration Constraints: remove it from that entry and replace with a cross-reference ("See: Observation Pairing Is Broken — KCI subsection A"). The consolidated entry:
```markdown
### Observation Pairing Is Broken for Parallel Tool Calls
**Root cause:** Hooks do not capture tool_use_id (zero occurrences in hooks/).
**Mechanism:** observation_parser.py:161 uses LIFO stack pairing.
**Failure mode:** N parallel tool calls → results assigned to wrong calls, silently drops
  some results, cascades wrong data into GVS citation rates and evaluation scores.
**Fix chain:** Plan 02 extracts tool_use_id (HARD EXIT CRITERION, IMP-09) → Plan 03
  replaces LIFO at observation_parser.py:161 → Plans 04, 07, 08 consume correct data.
**Validation:** Plan 02 exit criterion: "Validated pairing on real session with >= 2
  parallel calls." (IMP-12)
**Owner:** Plan 02 (root cause fix); Plan 03 (LIFO replacement)
```
**Impacts:** Plans 02, 03, 04, 07, 08 — dependency chain visible from one entry; HARD EXIT CRITERION label unambiguously present; Pipeline Integration Constraints cleaned of its only type-A item.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — Consolidating related bugs into root-cause entries
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Known Code Issues Taxonomy):** The lens brief asked whether consolidation loses "independent actionability" of each entry. It does not here: entries (1) and (2) are causally chained, not independently actionable — Plan 03's LIFO fix is hard-blocked on Plan 02's tool_use_id fix. There is one fix sequence, not two parallel options. Two gaps in the original How required fixing. First, it did not specify what happens to the LIFO mention inside Pipeline Integration Constraints — leaving it creates a fourth location after consolidation. The rewrite specifies cross-reference replacement. Second, the original proposed consolidated entry text dropped the HARD EXIT CRITERION label. This label is the most critical piece of information in entry (1), identifying tool_use_id capture as a hard gate for Plan 02. The rewrite restores it explicitly. Adding `**Owner:** Plan 02 (root cause fix); Plan 03 (LIFO replacement)` to the consolidated entry makes IMP-16's minimal owner tagging redundant for this specific entry — no conflict, just efficiency.

---

### P8-IMP-16: Add Plan Ownership Tags to Bug Entries
**Target:** CONTEXT
**What:** Some bug entries name their owning plan explicitly ("Fix in Plan 04"), some use indirect references ("3.1c-02 should validate"), some describe fixes without naming a plan. No consistent format for plan ownership lookup in KCI.
**Why:** Plan authors need to find assigned bugs quickly. Without consistent tags, they must read every entry and infer ownership from contextual clues.
**How:** Add bolded owner tag to each bug entry: `**Owner:** Plan {NN} | **Fix complexity:** ~N LOC | **Cross-deps:** Plan NN, ... | **Exit criterion:** yes/no`. Example:
```
**Owner:** Plan 02 | **Fix complexity:** ~40 LOC | **Cross-deps:** Plans 03, 04, 07, 08 | **Exit criterion:** yes (hard gate)
```
**Impacts:** All plans with assigned bugs
**Research needed:** no
**Confidence:** MEDIUM — structured metadata on prose entries may feel over-engineered; a table might be cleaner
**Prior art:** 4 — Issue trackers universally use ownership fields
**Prerequisite:** Depends on IMP-11 (subsection split) for clean placement
**Status:** implemented

**Original framing:** "Add bolded owner tag to each bug entry with four pipe-separated fields (Owner, Fix complexity, Cross-deps, Exit criterion) appended to each prose bug description."

**Adversarial note (Known Code Issues Taxonomy):** After IMP-01 restructures plan summaries to include Deliverables and Blocks fields, every plan summary will already enumerate which bugs it owns and which downstream plans it blocks. After IMP-02 adds the Cross-Plan Dependencies table, dependency chains are in one extractable place. After IMP-15 consolidates the pairing entries with an explicit Owner tag, the highest-severity bugs already carry ownership. The four-field inline tag duplicates three of those four fields: Owner is already in IMP-01's Deliverables lists; Cross-deps becomes IMP-02's dependency table; Exit criterion is already explicit in the IMP-15 consolidated entry and in plan summary Exit criteria fields. The residual unique contribution is Fix complexity (~N LOC) — genuinely useful for implementation planning and not captured elsewhere.

Applying the full four-field tag creates three sources of truth for dependency data and two sources for exit criteria, directly reproducing the drift problem this pass is trying to solve.

**Reframed What:** Add a single `**Owner:** Plan {NN}` tag only (not the four-field complex) to each Bug entry in KCI subsection A. This minimal tag enables lookup ("which plan owns this bug?") without duplicating data already captured by IMP-01 (Deliverables/Blocks), IMP-02 (dependency table), and IMP-15 (consolidated entry with full fix chain). The Fix complexity estimate belongs in the plan summary's Deliverables list as a LOC estimate, not in KCI. If Fix complexity is genuinely needed in KCI, add it as a second tag only: `**Owner:** Plan {NN} | **Fix complexity:** ~N LOC` — two fields, not four. Cross-deps and Exit criterion must not be duplicated into KCI.

**Prerequisite note:** This reframe is only safe if IMP-02 (dependency table) is accepted. If IMP-02 is rejected, the Cross-deps field in the four-field tag becomes the only consolidated dependency source and should be retained. The verdict is REFRAME conditional on IMP-02 acceptance.

---

### P8-IMP-17: Convert Testing Skill Readiness from Issue to Status Note
**Target:** CONTEXT
**What:** Lines 590-595 lists three "known limitations" of testing skills that are actually features depending on later plans (coverage radar → Plan 12, BaselineManager wiring → caller, AUTO-INVOKE → Plan 02).
**Why:** Framing plan dependencies as "known code issues" conflates "broken code" with "incomplete code." Readers assessing risk need to distinguish instantly.
**How:** Remove from Known Code Issues. If IMP-11's "Status Notes" subsection is adopted, place there with reframing: "Testing skills are well-formed but depend on later plans for full functionality."
**Impacts:** Minor — clarity improvement
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — Standard bug vs incomplete feature distinction
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Known Code Issues Taxonomy):** Withstands scrutiny. The three items at lines 590-595 are plan dependencies, not defects: "coverage radar features are 3.1c-12 scope (not yet implemented)" is a scope note for Plan 12; "BaselineManager requires explicit wiring in caller (not auto-enabled)" is an API usage note where nothing is broken, callers opt in; "AUTO-INVOKE on skills requires hook-based trigger (3.1c-02 scope)" is a feature dependency. All three belong in KCI subsection C (Status Notes) under IMP-11, not subsection A (Bugs). Placing them in C rather than deleting them entirely is preferable: new contributors benefit from knowing these are planned-and-dependent, not forgotten. The reframing text "well-formed but depend on later plans" is accurate. No conflict with other improvements.

---

### P8-IMP-18: Remove workflow_evaluator.py Disambiguation from Issues
**Target:** CONTEXT
**What:** Lines 500-503 exist solely to prevent confusion between workflow_evaluator.py (3.1b) and ReasoningEvaluator (3.1c). No bug, no constraint, no action item.
**Why:** Disambiguation belongs where people look up file paths. The Location Resolution table already maps components to actual paths.
**How:** Add an inline parenthetical note to the existing Evaluator row in the Location Resolution table — do not add a third column, which would alter the table schema for a single annotation: `| Evaluator | tests/workflow_harness/graders/reasoning_evaluator.py (not workflow_evaluator.py — that is 3.1b legacy) |`. Delete the standalone entry from Known Code Issues.
**Impacts:** None — pure relocation. Disambiguation reaches readers exactly where they look up file paths, rather than appearing in a bugs list where they are looking for problems.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — Co-locate disambiguation with the thing being disambiguated
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Known Code Issues Taxonomy):** The core move (delete from KCI, add note to Location Resolution) is correct and the reasoning is sound. The original How proposed adding a third column to the Location Resolution table: `| Evaluator | tests/.../reasoning_evaluator.py | NOT workflow_evaluator.py (3.1b legacy) |`. This is a structural change — adding a column to a two-column table — for a single disambiguation note on one row. A third column needs to be populated for all 11 rows or left empty, either creating maintenance burden or visual inconsistency. The rewrite uses an inline parenthetical in the existing second column instead: the disambiguation text is appended to the path, which is where a confused reader's eye will be. No table schema change. No conflict with IMP-19's proposed Status column (if that reframe is accepted, the Status column and the parenthetical note are distinct concerns on the same row and can coexist).

---

### P8-IMP-19: Consolidate Location Resolution With 3.1d Deliverables Tables
**Target:** CONTEXT
**What:** Two tables map components to file paths: "What 3.1d Built" (lines 30-48, 17 rows) and "Location Resolution" (lines 352-364, 11 rows). They overlap: both list Models, Hooks, Parser, etc. Location Resolution is authoritative; 3.1d adds status info ("Genuine", "Installed but need real run validation").
**Why:** Two partially-overlapping path tables create confusion about which is canonical.
**How:** If IMP-07 is accepted (collapsing 3.1d Deliverables), this resolves automatically — the 3.1d table is deleted. If not, add cross-reference: "See Location Resolution for canonical paths. This table adds status only." The status info from 3.1d is not genuinely useful — by plan execution time, everything is "exists, needs validation."
**Impacts:** Eliminates maintenance surface. No plan impact.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — Standard deduplication
**Prerequisite:** no — subsumed by IMP-07 if accepted
**Status:** implemented

**Original framing:** "Consolidate Location Resolution With 3.1d Deliverables Tables — subsumed by IMP-07 if accepted."

**Adversarial note (Information Architecture Integrity):** The framing "subsumed by IMP-07 if accepted" treats IMP-19 as a conditional fallback. This is the wrong abstraction. The problem IMP-19 identifies — two overlapping path tables with ambiguous canonical authority — is real and exists independently of IMP-07. IMP-07's claim that the 3.1d Deliverables table "duplicates Location Resolution" is exactly the IMP-19 problem stated as a premise. If IMP-07 is rejected (because the Status column carries information not in Location Resolution, as noted in the IMP-07 adversarial note), IMP-19 becomes the primary fix. But IMP-19 as written says "if IMP-07 is not: add cross-reference." This fallback How is correct but incomplete — it does not address what to do with the status column information. The right reframe: IMP-19's real value is establishing Location Resolution as the sole canonical path table, regardless of whether the 3.1d section is collapsed or preserved. Rewritten What: "The Location Resolution table (lines 352-364) is authoritative for file paths but has no canonical authority declaration. The 3.1d Deliverables table has 6 more rows (scenario YAML files, validator, plugin, tests, corpus baseline, skills/agent) that Location Resolution lacks. This gap means planners consulting Location Resolution get an incomplete picture." Rewritten How: (1) Add a Status/Notes column to Location Resolution and migrate the 3.1d status values. (2) Add the 6 rows from 3.1d that Location Resolution lacks. (3) Add a canonical authority declaration above the Location Resolution table: "This is the single authoritative path reference. Do not duplicate file paths elsewhere in this document." This makes IMP-19 independently valuable and clarifies the relationship to IMP-07: IMP-07 can now proceed with confidence that the information is captured in Location Resolution before deletion.

---

<!-- Note: P8-IMP-19 reframed from conditional fallback to independent improvement establishing Location Resolution canonical authority. -->

---

### P8-ADV-01: IMP-04 References Will Break if IMP-11 Restructures KCI Headings Before IMP-04 Uses Them
**Target:** CONTEXT
**What:** IMP-04 proposes replacing plan summary bug descriptions with references to KCI entries by name (e.g., "see KCI: Citation Rate Fallback Is Keyword Soup"). IMP-11 proposes restructuring KCI into three typed subsections, which will rename or reorganize headings. If IMP-04 is applied before IMP-11, the five cross-references will point to headings that no longer exist after IMP-11.
**Why:** Two improvements in the same pass interact destructively if applied in the wrong order. The merge step needs an explicit execution constraint between IMP-11 and IMP-04.
**How:** Apply IMP-11 first (establish stable KCI structure and heading names). Then apply IMP-04 using the post-IMP-11 heading names as reference anchors. Add to IMP-04's How field: "Apply after IMP-11. Reference KCI entries by their post-restructure heading names, not current line-referenced names." Add to merge step notes: "IMP-11 before IMP-04 — ordering constraint."
**Impacts:** IMP-04 correctness is contingent on IMP-11 application order. Zero impact if ordering is respected.
**Status:** implemented
**Source:** Adversarial review (Plan Summary Coherence)
**Adversarial note (Plan Summary Coherence):** This gap matters because both IMP-04 and IMP-11 modify the same KCI section in the same pass. The merge step will apply them in file-edit order, and if IMP-04's references are written against pre-IMP-11 heading names, they immediately become stale upon IMP-11 application. The fix is trivial (explicit ordering constraint) but must be captured before implementation.

---

### P8-ADV-02: "Pipeline Integration Constraints" Composite Heading Requires Decomposition for IMP-11
**Target:** CONTEXT
**What:** The current "Pipeline Integration Constraints" heading (lines 580-588) contains four bullet points spanning all three of IMP-11's proposed subsection types. Bullet 1: "Evaluator MUST receive CollectedOutput (not EvaluationInput)" — architectural constraint, type B. Bullet 2: "Plugins receive optional `context` kwarg with obs_summary, debrief, and other runtime data" — an API bug today (the Protocol declaration violates this per DC-3, it is a v1-blocking fix per line 393), type A. Bullet 3: "Contract loader resolves scenario workflow IDs to contract filenames" — convention/decision, type B. Bullet 4: "Scenario `expected_tools` field has no consumer — dead until 3.1c-09" — status note for Plan 09, type C. IMP-11 proposes splitting KCI into three typed subsections but does not specify how to handle this composite heading.
**Why:** Without explicit decomposition guidance, the IMP-11 implementer will either place the composite heading wholesale in one subsection (wrong for 3 of 4 bullets), or decompose it ad hoc. If bullet 2 (API Protocol bug) is misclassified as a cross-cutting constraint, Plan 01's responsibility to fix DC-3 is invisible to plan authors scanning subsection A for their assigned bugs. The DC-3 fix is described as v1-blocking in CONTEXT.md line 393 — missing it in subsection A has real implementation consequences.
**How:** When implementing IMP-11, decompose "Pipeline Integration Constraints" into its four constituent items rather than preserving it as a composite entry: (A) "Plugins receive optional `context` kwarg" moves to subsection A, Owner: Plan 01, pointing to DC-3 and the `EvaluationPlugin` Protocol fix needed in `models.py`; (B) "Evaluator MUST receive CollectedOutput" moves to subsection B as a standalone architectural constraint; (B) "Contract loader resolves workflow IDs" moves to subsection B as a convention/decision note; (C) "Scenario `expected_tools` has no consumer" moves to subsection C as a status note, noting Plan 09 as the future consumer.
**Source:** Adversarial review (Known Code Issues Taxonomy)
**Status:** implemented

**Adversarial note (Known Code Issues Taxonomy):** This gap was revealed by applying IMP-11's taxonomy strictly to every existing KCI item. IMP-11 is correct in proposing the split but incomplete in not providing a classification manifest. Without this CREATE item, the "Pipeline Integration Constraints" composite heading will be handled inconsistently during implementation. The bullet-2 misclassification risk is the most consequential: the EvaluationPlugin Protocol API bug is v1-blocking (CONTEXT.md line 393) and its owner (Plan 01) would not find it in subsection A without explicit placement guidance. This CREATE item provides the decomposition guidance that IMP-11 requires but does not supply. Note: this item supersedes the reference to "P8-ADV-01" in the enhanced IMP-11 How — that reference was written as P8-ADV-02 in the final numbering.

---

## Adversarial Review: Information Architecture Integrity
**Items reviewed:** 5 (IMP-07, IMP-08, IMP-09, IMP-10, IMP-19)
**Verdicts:** ENHANCE: 3 (IMP-07, IMP-08, IMP-09) | CONFIRM: 1 (IMP-10) | REFRAME: 1 (IMP-19)

**Cross-group conflicts:**
- IMP-07 (my group) conflicts with IMP-11 (other group): IMP-07 proposes deleting the Scope Adjustments table; IMP-11 proposes splitting Known Code Issues into typed subsections — no direct conflict, but IMP-07's deletion of the scope table reduces the data available for IMP-11's "Bugs" subsection to correctly identify Plan 02 as owning 3 bugs (one of which — threading.Lock — currently lives only in the scope table with no KCI entry). If IMP-07 executes before IMP-09 creates the new KCI entry, one Plan 02 bug disappears from the document entirely. Execution ordering constraint: IMP-09 (create threading.Lock KCI entry) must land before IMP-07 (delete scope table).
- IMP-08 (my group) and IMP-10 (my group) both modify the Infrastructure Available section header. IMP-08 adds `<!-- REFERENCE-ONLY: ... Do not propose changes ... -->` and IMP-10 adds `<!-- REFERENCE: Existing code inventory. Consult when writing plans. -->`. These should be merged into one comment to avoid two consecutive comment blocks on the same section.
- IMP-19 reframe (my group) expands Location Resolution with a Status column and 6 new rows. This is a prerequisite for IMP-07's safe deletion of the 3.1d table, establishing a dependency that neither improvement currently declares.

**Second-order risks:**
1. IMP-07 executed without IMP-09 causes information loss: the threading.Lock bug (currently only in the Scope Adjustments table and Plan 02 summary) loses its standalone KCI entry if the scope table is deleted before a KCI entry is created. A future improvement agent scanning KCI will not find it.
2. IMP-07 + IMP-19 sequence risk: if IMP-07 deletes the 3.1d table before IMP-19 migrates its 6 unique rows (scenario YAMLs, validator, plugin, tests, corpus baseline, skills/agent) to Location Resolution, those components disappear from all path references entirely. These 6 rows have no Location Resolution equivalent.
3. IMP-08 mechanism reliability: HTML comment-based skip directives are probabilistic for LLM consumers. A future improvement agent with a narrow prompt window may not see the comment or may treat it as non-binding. The proposed mitigation (two-layer signaling: comment + pass-level directive) partially addresses this but does not eliminate the risk.
4. IMP-10 labels create classification work for future improvements: once sections are tagged BINDING / REFERENCE / ACTIONABLE / STRUCTURAL, future improvement agents may reject valid proposals to BINDING sections that genuinely need updates, treating the label as a hard gate rather than a triage signal. The `<!-- BINDING: Constrain all plans. Changes require explicit justification. -->` comment on Implementation Decisions is correct in intent but may create false rigidity if the justification mechanism is not defined.

---

## Adversarial Review: Plan Summary Coherence
**Items reviewed:** 6 (P8-IMP-01 through P8-IMP-06)
**Verdicts:** ENHANCE: 3 (IMP-01, IMP-02, IMP-06) | ENHANCE: 1 (IMP-03) | REFRAME: 1 (IMP-04) | CONFIRM: 1 (IMP-05) | CREATE: 1 (P8-ADV-01)

**Cross-group conflicts:**
- IMP-01 (my group) and IMP-07 (other group): IMP-01's "Exists" field will contain the Scope Adjustments "% pre-addressed" data. If IMP-07 deletes the Scope Adjustments table before IMP-01 is applied, that data must be reconstructed from plan summary prose. Ordering constraint: apply IMP-01 before IMP-07.
- IMP-04 (my group) and IMP-11 (other group): IMP-04 creates references to KCI heading names that IMP-11 will change. IMP-11 must be applied first. Captured in P8-ADV-01.
- IMP-01 (my group) and IMP-06 (my group): IMP-01's example already uses the correct Location for Plan 02. If IMP-01 is fully implemented with correct Location fields for all 10 plans, IMP-06 is completely subsumed. Merge step should collapse IMP-06 into IMP-01 if IMP-01 covers all Location fields correctly.
- IMP-03 (my group) and IMP-07 (other group): If IMP-07 deletes the Scope Adjustments table first, the "~15% pre-addressed" figure for Plans 09-11 (line 70) disappears. IMP-03's split entries need that figure for their "Exists" fields (per IMP-01 format). Same ordering dependency as IMP-01/IMP-07 — apply IMP-01 and IMP-03 before IMP-07.

**Second-order risks:**
1. Document size: IMP-01 across 10 plans adds approximately 30 lines. IMP-03 splitting Plans 09-11 adds 20-30 more (three entries vs one). IMP-07 saves approximately 45 lines. Net is approximately neutral if IMP-07 is accepted. If IMP-07 is rejected, the document grows by 50-60 lines. For a 1170-line document this is acceptable but should be tracked.
2. IMP-02's dependency table: if populated with only 8 of 15+ dependencies (as in the original example), it creates false confidence that the table is exhaustive. A planner will trust the table as complete and miss unrepresented constraints. The table must either (a) include an explicit incompleteness caveat ("Last verified by scan of lines 677-898 on [date]") or (b) be populated exhaustively before publication.
3. IMP-06 fixes aspirational paths in plan summaries for Plans 01-08. But Plan 12's location fields reference files that do not yet exist — they are correct intended locations, not wrong references. The IMP-06 fix must not be applied to Plan 12 or it will incorrectly mark correct intent as wrong. The enhanced How field captures this scoping, but the merge step must enforce it.
4. IMP-04 REFRAME adds a prerequisite on IMP-11. If IMP-11 is rejected (not part of my review group), IMP-04 loses its prerequisite and the "reference KCI entry by stable heading name" mechanism breaks. In that case, IMP-04's references should use verbatim heading text from the current (pre-IMP-11) KCI structure.

---

## Adversarial Review: Known Code Issues Taxonomy
**Items reviewed:** 8 (IMP-11, IMP-12, IMP-13, IMP-14, IMP-15, IMP-16, IMP-17, IMP-18)
**Verdicts:** ENHANCE x4 (IMP-11, IMP-14, IMP-15, IMP-18) | CONFIRM x3 (IMP-12, IMP-13, IMP-17) | REFRAME x1 (IMP-16) | CREATE x1 (P8-ADV-02)

**Cross-group conflicts:**
- IMP-11 (this group) and IMP-10 (other group, Information Architecture Integrity) both modify the `## Known Code Issues` section header. IMP-10 adds a one-line ACTIONABLE comment directive; IMP-11 adds a summary table and three subsections underneath. These must be applied atomically or in the order IMP-10-then-IMP-11. The enhanced IMP-11 How now specifies the ACTIONABLE directive inline, making the two items consistent when applied together.
- IMP-16 (reframed to Owner-tag-only) and IMP-01 (other group, Plan Summary Coherence) partially overlap. After REFRAME, IMP-16 adds only `**Owner:** Plan {NN}` to KCI entries, which does not conflict with IMP-01's Deliverables lists — they serve different lookup directions (KCI-to-plan vs plan-to-KCI). No harmful conflict if IMP-02 is also accepted.
- IMP-14 (this group) has a prerequisite dependency on IMP-01 (other group). The Plan 06 summary must be restructured before the KCI entries are deleted. No conflict detected, but sequencing constraint is real and is now captured in IMP-14's Prerequisite field.
- IMP-15 (this group) and IMP-04 (other group) interact: IMP-04 targets Plan 02's tool_use_id description as a duplication target. After IMP-15 consolidation, the canonical KCI entry becomes the consolidated "Observation Pairing Is Broken" entry, and IMP-04's Plan 02 pointer should reference that entry by name. IMP-04 should be applied after IMP-15. No harmful conflict; sequencing matters.
- IMP-11 (this group) and IMP-04 (other group): IMP-04 creates KCI cross-references using current heading names. IMP-11 will rename those headings. IMP-11 must be applied first. This is captured in P8-ADV-01 (created by Plan Summary Coherence reviewer) but is confirmed from this lens as well.

**Second-order risks:**
1. IMP-11's three-way split is a structural reorganization that all other KCI-touching items (IMP-12, IMP-13, IMP-14, IMP-15, IMP-16, IMP-17, IMP-18, P8-ADV-02) depend on for correct subsection placement. If IMP-11 is accepted but classification decisions are made inconsistently during implementation, downstream items that specify subsection destinations will produce incoherent results. The enhanced IMP-11 How and P8-ADV-02 together provide the classification manifest that prevents this.
2. IMP-14 (remove Skill/Agent Specs entries) is conditioned on Plan 06 summary containing the authoring challenge quantification. The Plan 06 summary currently carries the ~5,135 lines detail (lines 772-790), but if IMP-01 restructuring of Plan 06 omits it, deletion is irreversible from CONTEXT.md alone. The enhanced IMP-14 Prerequisite field flags this.
3. IMP-15 (consolidate pairing entries) eliminates the standalone "Parallel Tool Calls Corrupt Observation Pairing" heading. Future improvement agents searching for "parallel" in KCI must find the consolidated entry. The enhanced How ensures "parallel" appears prominently in the consolidated entry title and failure mode description.
4. IMP-16 REFRAME reduces ownership metadata from four fields to one (or two). This is only safe if IMP-02 (Cross-Plan Dependencies table) is accepted. If IMP-02 is rejected, the REFRAME verdict should be reconsidered — the Cross-deps field in the original four-field tag would become the only consolidated dependency source in KCI. The reframed IMP-16 makes this conditional explicit in the Prerequisite note.
5. IMP-13 confidence: IMP-13 is marked CONFIRM but with MEDIUM confidence. The Information Architecture reviewer's note on IMP-07 (migrate Status column and threading.Lock KCI entry before deletion) is a prerequisite chain that IMP-13 depends on. Safe execution order: IMP-09 (extract threading.Lock to new KCI entry) → IMP-19 (expand Location Resolution) → IMP-07 (delete scope table, resolving IMP-13 automatically).
