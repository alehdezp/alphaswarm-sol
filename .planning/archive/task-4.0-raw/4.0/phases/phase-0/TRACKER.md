# Phase 0: Builder Refactor + Alignment Foundation

**Status:** IN PROGRESS (5/5 MUST + 3/3 SHOULD alignment tasks complete, 3/3 review tasks complete)
**Priority:** CRITICAL
**Last Updated:** 2026-01-08
**Author:** BSKG Team

---

## Quick Reference

| Field | Value |
|-------|-------|
| Entry Gate | Phase 0 docs exist; builder.py change protocol in place |
| Exit Gate | Builder refactor tasks complete + alignment workstream P documented and validated |
| Philosophy Pillars | Knowledge Graph, Semantic Ops, Beads, Tool Orchestration |
| Threat Model Categories | All (foundation accuracy for all attack surfaces) |
| Estimated Hours | 90-120h (refactor) + 6-8h (alignment) |
| Actual Hours | TBD |
| Task Count | 14 tasks (6 refactor, 5 alignment, 3 review) |
| Test Count Target | 50+ (refactor), alignment adds test requirements only |

---

## 0. CROSS-PHASE DEPENDENCIES

### 0.1 Upstream Dependencies (What This Phase Needs)

| Phase | Artifact Needed | Why Required | Task Reference |
|-------|----------------|--------------|----------------|
| None | - | Phase 0 is the foundation | - |

### 0.2 Downstream Dependencies (What Uses This Phase)

| Phase | What They Need | Artifact We Produce | Our Task |
|-------|----------------|---------------------|----------|
| Phase 1 | Evidence packets + bucket defaults | Packet mapping + bucket rules | P0.P.1, P0.P.2 |
| Phase 2 | Evidence packet completeness tests | Test requirements list | P0.P.5 |
| Phase 3 | Evidence packet output contract | Packet field map + schema notes | P0.P.1 |
| Phase 17 | VulnDocs category mapping | Mapping table | P0.P.4 |

### 0.3 Cross-Phase Task References

| Our Task | Related Task in Other Phase | Relationship |
|----------|----------------------------|--------------|
| P0.P.1 | Phase 1 P1.P.1 | Depends on packet field mapping |
| P0.P.2 | Phase 1 P1.P.3 | Buckets must align for Tier A |
| P0.P.4 | Phase 17 P17.P.1 | VulnDocs retrieval needs mapping |
| P0.P.5 | Phase 2 P2.P.1 | Benchmarks need packet summaries |

**ARCHITECTURAL NOTE:** Phase 0 cannot modify `builder.py`; all alignment outputs must be post-processing or documentation.

---

## 1. OBJECTIVES

### 1.1 Primary Objective

**Refactor builder safely while establishing alignment foundations for evidence packets, confidence buckets, and VulnDocs mapping.**

### 1.2 Secondary Objectives

1. Define evidence packet mapping rules without changing builder.py
2. Establish Tier A bucket defaults and rationale rules
3. Route graph quality issues into debate convoys
4. Publish VulnDocs category mapping for semantic ops
5. Specify evidence packet completeness tests for later phases

### 1.3 Philosophy Alignment

| Pillar | How This Phase Contributes |
|--------|---------------------------|
| Knowledge Graph | Builder refactor preserves behavioral signals and determinism |
| NL Query System | Evidence packet mapping enables stable query outputs |
| Agentic Automation | Graph-quality debate routing enables autonomous escalation |
| Self-Improvement | Early completeness tests prevent silent regressions |
| Task System (Beads) | Packet mapping ensures findings are bead-ready |

### 1.4 Success Metrics

| Metric | Target | Minimum | How to Measure | Command/Test |
|--------|--------|---------|----------------|--------------|
| Builder output parity | 100% identical | 100% | Fingerprint diff against baseline | `uv run pytest tests/test_fingerprint.py -v` |
| Evidence packet mapping spec | Complete | Complete | Mapping doc exists | Manual review |
| Bucket defaults (Tier A) | Defined | Defined | Rules table exists | Manual review |
| Graph-quality routing | Documented | Documented | Routing rules exist | Manual review |
| Completeness tests listed | Complete | Complete | Test list exists | Manual review |

### 1.5 Non-Goals (Explicit Scope Boundaries)

- No modifications to `src/true_vkg/kg/builder.py`
- No modifications to `src/true_vkg/queries/executor.py`
- No Tier B logic or LLM integration
- No schema-breaking changes to evidence packets or beads

---

## 2. RESEARCH REQUIREMENTS

### 2.1 Required Research Before Implementation

| ID | Research Topic | Output | Est. Hours | Status | Documented At |
|----|---------------|--------|------------|--------|---------------|
| - | None (use existing docs) | - | - | N/A | `docs/PHILOSOPHY.md` |

### 2.2 Knowledge Gaps

- [ ] Confirm evidence packet required fields against current finding schema
- [ ] Confirm post-processing layer can be implemented without builder changes

### 2.3 External References

| Reference | URL/Path | Purpose | Last Verified |
|-----------|----------|---------|---------------|
| PHILOSOPHY | `docs/PHILOSOPHY.md` | Evidence packet contract | 2026-01-08 |
| Builder refactor docs | `task/4.0/phases/phase-0/` | Refactor scope | 2026-01-08 |

### 2.4 Research Completion Criteria

- [ ] Required documents reviewed
- [ ] Uncertainties documented in tracker notes

---

## 3. TASK DECOMPOSITION

### 3.1 Task Dependency Graph

```
Builder Refactor (0.BR.*) runs in parallel with Alignment (P0.P.*)

0.BR.1 ─┬─ 0.BR.3 ── 0.BR.4 ── 0.BR.5
0.BR.2 ─┤
0.BR.6 ─┘

P0.P.1 ─┬─ P0.P.5
P0.P.2 ─┤
P0.P.3 ─┤
P0.P.4 ─┘

R0.1 → R0.2 → R0.3 (reviews after alignment tasks drafted)
```

### 3.2 Task Registry

#### Builder Refactor (Existing Workstream)

| ID | Task | Est. | Priority | Depends On | Status | Exit Criteria |
|----|------|------|----------|------------|--------|---------------|
| 0.BR.1 | Extract contexts | 8-12h | MUST | - | TODO | Context dataclasses extracted |
| 0.BR.2 | Centralize tokens | 6-8h | MUST | - | TODO | Token lists centralized |
| 0.BR.3 | Split detectors | 40-60h | MUST | 0.BR.1,0.BR.2,0.BR.6 | TODO | Detectors modularized |
| 0.BR.4 | Table-driven pipeline | 8-12h | SHOULD | 0.BR.3 | TODO | Pipeline tables replace if/else |
| 0.BR.5 | Performance pass | 12-16h | SHOULD | 0.BR.3,0.BR.4 | TODO | >=20% speedup, no regressions |
| 0.BR.6 | Protocol types | 6-10h | MUST | - | TODO | Protocol types defined |

#### Workstream P: Alignment Tasks

| ID | Task | Est. | Priority | Depends On | Status | Exit Criteria |
|----|------|------|----------|------------|--------|---------------|
| P0.P.1 | Evidence packet mapping (post-graph) | 2h | MUST | - | COMPLETE | Mapping spec exists |
| P0.P.2 | Bucket defaults for Tier A | 2h | MUST | P0.P.1 | COMPLETE | Bucket rules table exists |
| P0.P.3 | Graph-quality debate trigger | 2h | SHOULD | P0.P.1 | COMPLETE | Routing rules documented |
| P0.P.4 | VulnDocs category mapping | 2h | SHOULD | - | COMPLETE | Mapping table exists |
| P0.P.5 | Evidence packet completeness tests | 2h | MUST | P0.P.1 | COMPLETE | Test requirements list exists |
| P0.P.6 | Deduplication rule validation tests | 2h | SHOULD | P0.P.1 | COMPLETE | Tests validate dedupe rules |
| P0.P.7 | Tool disagreement routing rules | 2h | MUST | P0.P.1 | COMPLETE | Routing rules documented |
| P0.P.8 | Evidence packet fallback rules | 3h | MUST | P0.P.1 | COMPLETE | Fallback behavior implemented |

#### Review Tasks (Required for Every Phase)

| ID | Task | Est. | Priority | Depends On | Status | Exit Criteria |
|----|------|------|----------|------------|--------|---------------|
| R0.1 | Phase necessity review | 1h | MUST | - | COMPLETE | Keep/cut/modify decision logged |
| R0.2 | Task necessity review | 2h | MUST | P0.P.1-P0.P.8 | COMPLETE | Justification log completed |
| R0.3 | Conflict review | 1h | MUST | P0.P.1-P0.P.8 | COMPLETE | Conflict notes recorded |

**Review Decisions:** See `R0-REVIEW-DECISIONS.md` for full review documentation.

### 3.3 Dynamic Task Spawning

**Tasks may be added during execution when:**
- Evidence packet exports are missing required fields
- New semantic operations are added
- Tests reveal gaps in completeness or routing

**Process for adding tasks:**
1. Document reason for new task
2. Assign next available ID (P0.P.6, P0.P.7, ...)
3. Update task registry and dependency graph
4. Update `task/4.0/phases/INDEX.md`

**Example spawned task:**
- **P0.P.6 Evidence Packet Fallback Rules**: Added when a required field is missing in sample exports; defines fallback values and `request_more_context` rules.

### 3.4 Task Details

#### Task P0.P.1: Evidence Packet Mapping (post-graph)

**Objective:** Define a post-processing mapping from graph properties/semantic ops to evidence packet fields.

**Start here:** `docs/PHILOSOPHY.md` (Evidence Packet Contract), `src/true_vkg/kg/schema.py`

**Dependencies:** None

**Deliverables:**
- `task/4.0/phases/phase-0/P0.P.1-EVIDENCE-PACKET-MAPPING.md`

**Validation:**
- Sample packet from a known contract includes all required fields

**Conflicts:** Output format conflicts (JSON vs YAML) resolved per master conflict notes.

**Spawn Triggers:** New semantic op added without mapping.

---

#### Task P0.P.2: Bucket Defaults for Tier A

**Objective:** Define Tier A bucket defaults and rationale fields for deterministic outputs.

**Start here:** `docs/PHILOSOPHY.md` (Confidence Buckets), Phase 1 tracker

**Dependencies:** P0.P.1

**Deliverables:**
- `task/4.0/phases/phase-0/P0.P.2-BUCKET-DEFAULTS.md`

**Validation:**
- Bucket rules referenced by Phase 1 alignment tasks

**Conflicts:** Determinism applies only to Tier A; do not apply to Tier B.

**Spawn Triggers:** New bucket category introduced.

---

#### Task P0.P.3: Graph Quality Debate Trigger

**Objective:** Define routing rules that escalate missing evidence to a `graph-quality` convoy.

**Start here:** `docs/PHILOSOPHY.md` (Debate Protocol), `task/4.0/protocols/`

**Dependencies:** P0.P.1

**Deliverables:**
- `task/4.0/phases/phase-0/P0.P.3-GRAPH-QUALITY-ROUTING.md`

**Validation:**
- Failure modes documented with examples

**Conflicts:** Must not suppress missing evidence; escalations are required.

**Spawn Triggers:** New failure mode discovered in builder outputs.

---

#### Task P0.P.4: VulnDocs Category Mapping

**Objective:** Map semantic operations to VulnDocs categories for retrieval and bead context.

**Start here:** `docs/PHILOSOPHY.md` (VulnDocs), `task/4.0/phases/phase-17/`

**Dependencies:** None

**Deliverables:**
- `task/4.0/phases/phase-0/P0.P.4-VULNDOCS-MAPPING.md`

**Validation:**
- Mapping referenced in Phase 17 tracker

**Conflicts:** Keep mapping additive; do not change core ops list.

**Spawn Triggers:** Missing VulnDocs category identified.

---

#### Task P0.P.5: Evidence Packet Completeness Tests

**Objective:** Specify tests that enforce evidence packet completeness early.

**Start here:** `docs/PHILOSOPHY.md` (Evidence Packet Contract), Phase 2 tracker

**Dependencies:** P0.P.1

**Deliverables:**
- `task/4.0/phases/phase-0/P0.P.5-PACKET-COMPLETENESS-TESTS.md`

**Validation:**
- Tests referenced in Phase 2 and Phase 3 test sections

**Conflicts:** None

**Spawn Triggers:** Evidence packet schema changes.

---

#### Task R0.1: Phase Necessity Review

**Objective:** Decide keep/cut/modify for Phase 0 scope relative to philosophy pillars.

**Start here:** `docs/PHILOSOPHY.md`, `task/4.0/phases/phase-0/BUILDER-REFACTOR.md`

**Dependencies:** None

**Deliverables:**
- Decision note in this tracker (Section 6.4 or Notes)

**Validation:**
- Decision recorded with rationale

**Conflicts:** None

**Spawn Triggers:** Major scope mismatch discovered.

---

#### Task R0.2: Task Necessity Review

**Objective:** Validate each alignment task is required or mark as doc-only if already implemented.

**Start here:** P0.P.1-P0.P.5 task details

**Dependencies:** P0.P.1-P0.P.5

**Deliverables:**
- Justification log in tracker notes

**Validation:**
- Each alignment task has a necessity decision

**Conflicts:** None

**Spawn Triggers:** Redundant tasks found.

---

#### Task R0.3: Conflict Review

**Objective:** Identify conflicts between Phase 0 alignment outputs and downstream phases.

**Start here:** `task/4.0/MASTER.md` conflict notes

**Dependencies:** P0.P.1-P0.P.5

**Deliverables:**
- Conflict notes in tracker and MASTER references

**Validation:**
- Conflicts referenced in Phase 1/3 trackers

**Conflicts:** Output format conflicts, determinism scope

**Spawn Triggers:** New conflict discovered during alignment.

---

## 4. TEST SUITE REQUIREMENTS

### 4.1 Test Categories

| Category | Count Target | Coverage Target | Location |
|----------|--------------|-----------------|----------|
| Unit Tests | 50+ | Builder refactor coverage | `tests/` |
| Integration Tests | TBD | Graph parity + fingerprints | `tests/test_fingerprint.py` |
| Regression Tests | 10+ | Determinism + snapshots | `tests/test_golden_snapshots.py` |

### 4.2 Test Matrix

| Feature | Happy Path | Edge Cases | Error Cases | Performance |
|---------|-----------|------------|-------------|-------------|
| Builder refactor | [ ] | [ ] | [ ] | [ ] |
| Evidence packet mapping | [ ] | [ ] | [ ] | [ ] |

### 4.3 Test Fixtures Required

| Fixture | Location | Purpose | Exists? |
|---------|----------|---------|---------|
| BasicVault | `tests/contracts/BasicVault.sol` | Parity check | [x] |

### 4.4 Benchmark Validation

| Benchmark | Target | Baseline | Current | Command |
|-----------|--------|----------|---------|---------|
| DVDeFi | No regression | 84.6% | TBD | `uv run alphaswarm benchmark run --suite dvd` |

### 4.5 Test Automation

```bash
uv run pytest tests/test_fingerprint.py tests/test_rename_resistance.py -v
uv run pytest tests/test_golden_snapshots.py -v
```

---

## 5. IMPLEMENTATION GUIDELINES

### 5.1 Code Standards

- Type hints on all public functions
- No changes to builder.py without protocol approval
- Evidence packet and bead schemas are versioned and backward compatible

### 5.2 File Locations

| Component | Location | Naming Convention |
|-----------|----------|-------------------|
| Builder refactor docs | `task/4.0/phases/phase-0/` | `BR.*.md` |
| Alignment specs | `task/4.0/phases/phase-0/` | `P0.P.*.md` |

---

## 6. REFLECTION PROTOCOL

### 6.1 Brutal Self-Critique Checklist

- [ ] Does this preserve behavioral detection?
- [ ] Are we documenting missing evidence, not hiding it?
- [ ] Are output contracts minimal and consistent?
- [ ] Would a new developer understand the mapping?

### 6.2 Real-World Validation Protocol

Run parity tests and benchmark regression checks after refactor tasks.

---

## 7. ITERATION PROTOCOL

Use the global iteration protocol from `task/4.0/phases/PHASE_TEMPLATE.md`.

---

## 8. COMPLETION CHECKLIST

### 8.1 Exit Criteria

- [ ] All MUST tasks complete (0.BR.1, 0.BR.2, 0.BR.3, 0.BR.6, P0.P.1, P0.P.2, P0.P.5)
- [ ] Builder parity tests pass
- [ ] Alignment specs reviewed and referenced by downstream phases
- [ ] INDEX.md updated

### 8.2 Artifacts Produced

| Artifact | Location | Purpose | Verified? |
|----------|----------|---------|-----------|
| Alignment specs | `task/4.0/phases/phase-0/` | Evidence packet + bucket rules | [ ] |
| Builder refactor docs | `task/4.0/phases/phase-0/` | Refactor plan | [ ] |

---

## 10. PHASE METADATA

**Version History:**
| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-01-08 | Initial tracker with alignment workstream P | BSKG Team |

**Cross-References:**
- MASTER.md: Alignment sweep section
- INDEX.md: Phase 0 entry
- Related Phases: 1, 2, 3, 17

---

*Phase 0 Tracker | Version 1.0 | 2026-01-08*
*Template: PHASE_TEMPLATE.md v2.0*
