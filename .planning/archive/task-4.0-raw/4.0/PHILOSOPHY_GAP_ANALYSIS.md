# BSKG 4.0 Philosophy Gap Analysis Report

**Generated:** 2026-01-08
**Philosophy Version:** docs/PHILOSOPHY.md (current)
**Implementation Baseline:** task/4.0/phases/ (19 phases)

---

## Executive Summary

This report compares the **target spec** in `docs/PHILOSOPHY.md` against the **current implementation status** in `task/4.0/phases/`. It identifies missing items, partial implementations, and proposes new tasks to achieve full alignment.

**Status:**
| Category | Fully Aligned | Partial | Missing | Total |
|----------|---------------|---------|---------|-------|
| Core Architecture | 4 | 3 | 0 | 7 |
| Orchestration Model | 1 | 4 | 2 | 7 |
| Agent Roles | 2 | 3 | 4 | 9 |
| Evidence System | 1 | 3 | 1 | 5 |
| Knowledge System | 0 | 1 | 0 | 1 |

**Overall:** 8 fully aligned, 14 partial, 7 missing

---

## 1. Core Architecture Alignment

### 1.1 Behavioral Signatures [ALIGNED]

**Philosophy Requirement:**
```
R:bal -> X:out -> W:bal  (read balance, external call, write balance)
```
20 signature codes defined: R:bal, W:bal, X:out, X:in, X:call, X:unk, C:auth, M:own, M:role, M:crit, R:orc, R:ext, L:arr, U:time, U:blk, A:div, A:mul, V:in, E:evt, I:init

**Implementation Status:** Phase 1 COMPLETE - behavioral signatures implemented in `src/true_vkg/kg/sequencing.py`

**Gap:** None

---

### 1.2 Semantic Operations [ALIGNED]

**Philosophy Requirement:** 20 core operations (TRANSFERS_VALUE_OUT, READS_USER_BALANCE, CHECKS_PERMISSION, etc.)

**Implementation Status:** Phase 1 COMPLETE - operations in `src/true_vkg/kg/operations.py`

**Gap:** None

---

### 1.3 Two-Tier Pattern System [PARTIAL]

**Philosophy Requirement:**
- Tier A: strict, graph-only, high confidence
- Tier B: exploratory, LLM-verified, targets complex logic bugs

**Implementation Status:**
- Tier A: Phase 1 COMPLETE (84.6% detection rate)
- Tier B: Phase 11 BLOCKED (LLM integration)

**Gap:** Tier B pipeline not yet implemented

**Existing Task:** Phase 11 tasks 11.2-11.4

---

### 1.4 Evidence-Linked Findings [ALIGNED]

**Philosophy Requirement:** "Every finding links to code locations and the IR/AST path that produced the signal"

**Implementation Status:** Findings include file, contract, function, lines, and evidence_lines

**Gap:** None

---

### 1.5 Context Packaging (PPR-style) [PARTIAL]

**Philosophy Requirement:**
- Build tiered context packages (summary -> evidence -> code)
- Use importance-ranked subgraphs (PPR-style) for retrieval

**Implementation Status:** Phase 9 BLOCKED (Context Optimization)

**Gap:** PPR-style retrieval not implemented

**Existing Task:** Phase 9 tasks 9.1-9.4

---

### 1.6 TOON Format [ALIGNED]

**Philosophy Requirement:** Token-optimized output notation for 30-50% reduction

**Implementation Status:** Phase 6 COMPLETE - TOON format implemented in beads system

**Gap:** None

---

### 1.7 Deduplication Rules [PARTIAL]

**Philosophy Requirement:**
- Normalize by file + contract + function + line range + vulnerability class
- Same location and class -> merge into one bead
- Same location, different class -> link as a cluster
- Different locations, same pattern -> keep distinct beads

**Implementation Status:** Partially in Phase 12 (Integrator role concept exists)

**Gap:** Explicit deduplication validation rules not tested

**NEW TASK:** P0.P.6 - Deduplication Rule Validation Tests

---

## 2. Orchestration Model Alignment

### 2.1 Beads System [ALIGNED]

**Philosophy Requirement:** Self-contained investigation packages with ID, status, pattern_id, vulnerability_class, location, behavioral_signature, semantic_ops, evidence, questions, tests, verdict, confidence_bucket, confidence_score

**Implementation Status:** Phase 6 COMPLETE (227 tests)

**Gap:** None

---

### 2.2 Convoy System [MISSING]

**Philosophy Requirement:**
- "Convoys group related beads for batch workflows and shared context"
- Convoy walkthrough: Coordinator creates convoy, Triage Analyst labels, Attacker/Defender process, etc.

**Implementation Status:** Phase 6 P6.P.2 mentions convoy routing but no explicit convoy implementation

**Gap:** Convoy data model, lifecycle, and CLI commands not implemented

**NEW TASKS:**
- P6.P.3 - Convoy Data Model (ID, beads, status, progress)
- P6.P.4 - Convoy Lifecycle Manager (create, add_bead, complete)
- P6.P.5 - Convoy CLI Commands (vkg convoy create, vkg convoy status)

---

### 2.3 Hook System (Agent Inboxes) [MISSING]

**Philosophy Requirement:**
- "Each agent has a hook (inbox) with a prioritized bead queue"
- Priority order: critical severity > exploitability > tool agreement > recency
- "Disputed or uncertain beads are routed to multi-agent debate by default"

**Implementation Status:** Phase 6 P6.P.2 exists but not detailed

**Gap:** Hook data model, priority queue, routing rules not implemented

**NEW TASKS:**
- P6.P.6 - Hook Data Model (agent_id, queue, priorities)
- P6.P.7 - Hook Priority Ordering (severity > exploitability > tool_agreement > recency)
- P6.P.8 - Hook Routing Rules (disputed -> debate, uncertain -> escalate)

---

### 2.4 Propulsion Principle [PARTIAL]

**Philosophy Requirement:** "If an agent finds work on its hook, it runs it without waiting for permission"

**Implementation Status:** Concept exists in Phase 12 swarm mode but not explicit

**Gap:** Auto-execution behavior not explicitly implemented

**NEW TASK:** P12.P.3 - Propulsion Behavior Implementation

---

### 2.5 Supervisor Responsibilities [PARTIAL]

**Philosophy Requirement:** "Supervisor monitors queues, nudges stuck work, enforces SLAs, escalates"

**Implementation Status:** Phase 12 P12.P.1 mentions supervisor but lacks detail

**Gap:** Supervisor monitoring, SLA enforcement, escalation triggers not specified

**ENHANCED TASK:** P12.P.1 → Add: SLA rules, escalation triggers, stuck detection

---

### 2.6 Integrator Responsibilities [PARTIAL]

**Philosophy Requirement:** "Integrator dedupes overlaps, merges evidence, and finalizes verdicts"

**Implementation Status:** Phase 12 P12.P.1 mentions integrator but lacks detail

**Gap:** Dedupe algorithm, merge rules, verdict finalization not specified

**ENHANCED TASK:** P12.P.1 → Add: dedupe algorithm, merge strategy, verdict rules

---

### 2.7 Escalation Triggers [PARTIAL]

**Philosophy Requirement:**
- "If claim and counterclaim cannot be reconciled -> human review"
- "If tests are inconclusive -> uncertain bucket and escalate"
- "Escalation triggers move beads from agent hooks to human review"

**Implementation Status:** Concept exists but not formalized

**Gap:** Explicit escalation trigger definitions

**NEW TASK:** P12.P.4 - Escalation Trigger Specification

---

## 3. Multi-Agent Role Alignment

### 3.1 Infrastructure Roles

| Role | Philosophy | Implementation | Status |
|------|------------|----------------|--------|
| Coordinator | "triage, scheduling, and routing" | Phase 12 P12.P.1 | PARTIAL |
| Supervisor | "watches progress, nudges stuck work, escalates" | Phase 12 P12.P.1 | PARTIAL |
| Integrator | "dedupes, merges, and resolves overlapping outputs" | Phase 12 P12.P.1 | PARTIAL |

### 3.2 Audit Roles

| Role | Philosophy | Implementation | Status |
|------|------------|----------------|--------|
| Triage Analyst | "validate evidence and classify risk" | Not tracked | MISSING |
| Attacker | "construct exploit paths and attack narratives" | Phase 12 VerificationMicroAgent | ALIGNED |
| Defender | "search for guards, invariants, or mitigating logic" | Phase 12 concept | PARTIAL |
| Verifier | "cross-check reasoning and evidence consistency" | Phase 12 VerificationMicroAgent | ALIGNED |
| Test Builder | "generate tests and PoCs" | Phase 12 TestGenMicroAgent | ALIGNED |
| Evidence Curator | "package evidence and maintain audit trails" | Not tracked | MISSING |

**Gap Summary:**
- MISSING: Triage Analyst, Evidence Curator explicit roles
- PARTIAL: Coordinator, Supervisor, Integrator, Defender need detail

**NEW TASKS:**
- P12.P.5 - Triage Analyst Role Definition
- P12.P.6 - Evidence Curator Role Definition
- P12.P.7 - Defender Role Enhancement

---

## 4. Evidence System Alignment

### 4.1 Evidence Packet Contract [PARTIAL]

**Philosophy Required Fields:**
```yaml
id: string
finding_id: string
location:
  file: string
  contract: string
  function: string
  lines: [int, int]
behavioral_signature: string
semantic_ops: [string]
properties: [string]
evidence_lines: [string]
tool_sources: [string]
confidence_bucket: string
rationale: string
```

**Philosophy Optional Fields:**
```yaml
evidence_links: [string]
disputed: bool
missing_tools: [string]
request_more_context: bool
context_hint: string
artifacts: [string]
```

**Implementation Status:** Phase 0 P0.P.1 (Evidence packet mapping) TODO

**Gap:** Schema not validated against implementation

**Existing Task:** P0.P.1 - needs completion

---

### 4.2 Confidence Buckets [PARTIAL]

**Philosophy Bucket Definitions:**
- confirmed: exploit test passes OR multi-agent consensus with no conflicts
- likely: score >= 0.75 and no major contradictions
- uncertain: score in [0.40, 0.75) OR any disputed evidence
- rejected: exploit test fails OR strong counter-evidence is confirmed

**Philosophy Overrides:**
- Missing core evidence forces `uncertain` regardless of score
- Tool disagreement forces `uncertain` until resolved
- Human confirmation can override to `confirmed` or `rejected`

**Implementation Status:** Phase 0 P0.P.2 (Bucket defaults) TODO, Phase 14 (Calibration) BLOCKED

**Gap:** Bucket mapping rules not validated

**Existing Tasks:** P0.P.2, Phase 14

**ENHANCED TASK:** P0.P.2 → Add explicit bucket mapping validation tests

---

### 4.3 Debate Protocol [PARTIAL]

**Philosophy Required Outputs:**
```yaml
claim: string
counterclaim: string
evidence: [string]
tests_run: [string]
verdict: string
confidence_bucket: string
rationale: string
```

**Philosophy Escalation Rules:**
- If claim and counterclaim cannot be reconciled -> human review
- If tests are inconclusive -> uncertain bucket and escalate

**Implementation Status:** Phase 11/12 have debate concepts but schema not validated

**Gap:** Debate protocol output schema not validated

**NEW TASK:** P11.P.1 - Debate Protocol Schema Validation

---

### 4.4 Tool Disagreement Handling [PARTIAL]

**Philosophy Requirement:**
- "If tools disagree on a finding, mark it as disputed"
- "Disputed beads automatically enter multi-agent debate"
- "Evidence from each tool is preserved and attributed"

**Implementation Status:** Concept exists but not formalized

**Gap:** Automatic disputed routing not implemented

**NEW TASK:** P0.P.7 - Tool Disagreement Routing Rules

---

### 4.5 Fallback Rules [MISSING]

**Philosophy Requirement:**
- If required fields are missing, set `request_more_context: true`
- If tools are unavailable, record them in `missing_tools` and lower confidence
- If sources disagree, set `disputed: true` and route to debate
- If context budget is tight, drop to evidence packet and skip full bead

**Implementation Status:** Not tracked

**Gap:** Fallback behavior not implemented

**NEW TASK:** P0.P.8 - Evidence Packet Fallback Rules Implementation

---

## 5. Knowledge System Alignment

### 5.1 VulnDocs [PARTIAL]

**Philosophy Requirement:**
- Curate vulnerability knowledge into categories and subcategories
- Provide detection, testing, and business impact guidance
- Keep content minimal, navigable, and LLM-friendly
- Feed evidence packets and bead templates with targeted excerpts

**Integration Points:**
- Pattern packs: convert knowledge signals into new pattern candidates
- Bead templates: attach detection/testing sections as evidence packets
- Grimoires: supply procedures, invariants, and exploit narratives

**Implementation Status:** Phase 17 TODO, Phase 18 IN PROGRESS (10/12 done)

**Gap:** Phase 17 not started

**Existing Task:** Phase 17

---

## 6. Discovery and Integration

### 6.1 AGENTS.md Discovery [PARTIAL]

**Philosophy Requirement:** "Discovery should be standardized via `.vrs/AGENTS.md` so any compliant agent can use BSKG without custom instructions"

**Implementation Status:** Phase 13 task 13.7 "AGENTS.md generation" exists but BLOCKED

**Gap:** Not yet implemented

**Existing Task:** Phase 13.7

---

## 7. Summary: New Tasks Required

### Phase 0 (Builder Refactor + Alignment Foundation)

| ID | Task | Est. | Priority |
|----|------|------|----------|
| P0.P.6 | Deduplication Rule Validation Tests | 2h | SHOULD |
| P0.P.7 | Tool Disagreement Routing Rules | 2h | MUST |
| P0.P.8 | Evidence Packet Fallback Rules Implementation | 3h | MUST |

### Phase 6 (Beads System - Alignment Addendum)

| ID | Task | Est. | Priority |
|----|------|------|----------|
| P6.P.3 | Convoy Data Model | 3h | MUST |
| P6.P.4 | Convoy Lifecycle Manager | 4h | MUST |
| P6.P.5 | Convoy CLI Commands | 2h | SHOULD |
| P6.P.6 | Hook Data Model | 3h | MUST |
| P6.P.7 | Hook Priority Ordering | 2h | MUST |
| P6.P.8 | Hook Routing Rules | 2h | MUST |

### Phase 11 (LLM Integration - Alignment Addendum)

| ID | Task | Est. | Priority |
|----|------|------|----------|
| P11.P.1 | Debate Protocol Schema Validation | 2h | MUST |

### Phase 12 (Agent SDK - Alignment Addendum)

| ID | Task | Est. | Priority |
|----|------|------|----------|
| P12.P.3 | Propulsion Behavior Implementation | 3h | SHOULD |
| P12.P.4 | Escalation Trigger Specification | 2h | MUST |
| P12.P.5 | Triage Analyst Role Definition | 2h | SHOULD |
| P12.P.6 | Evidence Curator Role Definition | 2h | SHOULD |
| P12.P.7 | Defender Role Enhancement | 2h | SHOULD |

### Enhanced Existing Tasks

| Phase | Task | Enhancement |
|-------|------|-------------|
| Phase 0 | P0.P.2 | Add bucket mapping validation tests |
| Phase 12 | P12.P.1 | Add SLA rules, escalation triggers, stuck detection for Supervisor |
| Phase 12 | P12.P.1 | Add dedupe algorithm, merge strategy, verdict rules for Integrator |

---

## 8. Recommended Priority Order

### Critical Path (Must complete for philosophy alignment)

1. **Phase 0:** P0.P.1 (Evidence packet mapping) → P0.P.2 (Bucket defaults) → P0.P.7-P0.P.8 (Fallback rules)
2. **Phase 6:** P6.P.3-P6.P.4 (Convoy system) → P6.P.6-P6.P.8 (Hook system)
3. **Phase 11:** P11.P.1 (Debate schema)
4. **Phase 12:** P12.P.1 enhanced (Supervisor/Integrator detail) → P12.P.4 (Escalation triggers)

### Secondary (Should complete for full alignment)

1. **Phase 0:** P0.P.6 (Dedupe tests)
2. **Phase 6:** P6.P.5 (Convoy CLI)
3. **Phase 12:** P12.P.3, P12.P.5-P12.P.7 (Additional roles)

---

## 9. Cross-Reference Matrix

| Philosophy Section | Phase | Tasks | Status |
|--------------------|-------|-------|--------|
| Behavioral Signatures | 1 | 1.C.*, 1.D.* | COMPLETE |
| Semantic Operations | 1 | 1.C.* | COMPLETE |
| Pattern System (Tier A) | 1 | 1.D.*, 1.E.* | COMPLETE |
| Pattern System (Tier B) | 11 | 11.2-11.4 | BLOCKED |
| Beads System | 6 | 6.0-6.6 | COMPLETE |
| Convoy System | 6 | P6.P.3-P6.P.5 | NEW |
| Hook System | 6 | P6.P.6-P6.P.8 | NEW |
| Evidence Packets | 0 | P0.P.1, P0.P.5 | TODO |
| Confidence Buckets | 0, 14 | P0.P.2, 14.* | TODO/BLOCKED |
| Debate Protocol | 11, 12 | P11.P.1, P12.P.2 | NEW/TODO |
| Multi-Agent Roles | 12 | 12.*, P12.P.* | PARTIAL |
| VulnDocs | 17, 18 | 17.*, 18.* | TODO/IN PROGRESS |
| AGENTS.md | 13 | 13.7 | BLOCKED |
| Context Optimization | 9 | 9.* | BLOCKED |

---

## 10. Conclusion

The BSKG 4.0 implementation has strong alignment with the philosophy's core detection capabilities (behavioral signatures, semantic operations, Tier A patterns). The main gaps are in the **orchestration model** (convoys, hooks, propulsion) and **multi-agent role definitions**.

**Total New Tasks:** 15
**Total Enhanced Tasks:** 3
**Estimated Additional Hours:** ~40h

**Recommendation:** Add the new tasks to their respective phase trackers and update INDEX.md. Prioritize Phase 0 and Phase 6 alignment tasks as they unblock downstream phases.

---

*Report generated by gap analysis comparing docs/PHILOSOPHY.md against task/4.0/phases/*
