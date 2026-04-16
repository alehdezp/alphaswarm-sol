# Phase 19: Semantic Labeling for Complex Logic Detection

**Status:** TODO
**Priority:** HIGH
**Last Updated:** 2026-01-08
**Author:** BSKG Team
**Estimated Hours:** 140h
**Actual Hours:** [Tracked]

---

## Quick Reference

| Field | Value |
|-------|-------|
| Entry Gate | Phase 9 (context slicing), Phase 11 (LLM provider), Phase 6/7 (beads + learning overlay) |
| Exit Gate | Labeler pipeline + label-aware patterns + real-world eval report |
| Philosophy Pillars | Knowledge Graph, Agentic Automation, Self-Improvement |
| Threat Model Categories | Business logic, Access control, State machine, Oracle misuse, Value movement |
| Task Count | 14 (4 research + 10 implementation) |
| Test Count Target | 60+ (unit + integration + real-world) |

---

## 0. CROSS-PHASE DEPENDENCIES

### 0.1 Upstream Dependencies (What This Phase Needs)

| Phase | Artifact Needed | Why Required | Task Reference |
|-------|----------------|--------------|----------------|
| Phase 6 | Beads system | Provides investigation context and verdicts | 6.* |
| Phase 7 | Learning events/FP recorder | Enables label decay + conservative learning | 7.* |
| Phase 9 | Graph slicing | Token-budgeted context for labeler | 9.* |
| Phase 11 | LLM provider abstraction | Labeler agent uses LLM | 11.1 |
| Phase 13 | Grimoires/investigation patterns | Labeler alignment with reasoning steps | 13.* |

### 0.2 Downstream Dependencies (What Uses This Phase)

| Phase | What They Need | Artifact We Produce | Our Task |
|-------|----------------|---------------------|----------|
| Phase 14 | Calibration improvements | Labeler precision/recall metrics | 19.8 |
| Phase 20 | Final testing phase | Label-aware detection pipeline | 19.5-19.8 |
| VulnDocs Track | Spec templates | Intent/capability labels | 19.6-19.7 |

### 0.3 Cross-Phase Task References

| Our Task | Related Task | Relationship |
|----------|--------------|--------------|
| 19.2 | 11.16 | depends on cached knowledge | depends on |
| 19.5 | 9.1 | uses sliced context for label-aware matching | extends |

**ARCHITECTURAL NOTE:** Do NOT modify `builder.py` or `executor.py`.
Pattern integration must occur via new modules or safe adapters.

---

## 1. OBJECTIVES

### 1.1 Primary Objective

Implement a semantic labeling pipeline that captures intent, authority, and
business logic and uses these labels to detect complex vulnerabilities that
static analysis misses, while staying within strict token budgets.

### 1.2 Secondary Objectives

1. Create a label taxonomy that maps to complex detection patterns.
2. Build deterministic validation for label quality.
3. Prove measurable precision gains on real-world protocols.

### 1.3 Philosophy Alignment

| Pillar | Contribution |
|--------|--------------|
| Knowledge Graph | Adds semantic overlays with evidence | 
| Agentic Automation | LLM labeler executes scoped reasoning | 
| Self-Improvement | Retrospective tests refine taxonomy + rules | 
| Task System (Beads) | Labels derived from bead evidence | 
| NL Query | N/A |

### 1.4 Success Metrics

| Metric | Target | Minimum | How to Measure | Command/Test |
|--------|--------|---------|----------------|--------------|
| Label precision | 0.85 | 0.75 | Manual audit of 50 labels | `tests/test_labeler_eval.py` |
| Detection delta | +10% precision | +5% | Compare baseline vs label-aware | `tests/test_labeler_realworld.py` |
| Token budget | < 6k tokens per label call | < 8k | Prompt size logs | `tests/test_labeler_budget.py` |
| FP reduction | 20% | 10% | FP warning impact | `tests/test_labeler_fp.py` |

### 1.5 Non-Goals

- No global, cross-project label persistence without curation.
- No ML training or model fine-tuning in this phase.
- No modifications to core builder/executor modules.

---

## 2. RESEARCH REQUIREMENTS

### 2.1 Required Research Before Implementation

| ID | Research Topic | Output | Est. Hours | Status | Documented At |
|----|---------------|--------|------------|--------|---------------|
| R19.1 | Label taxonomy expansion | Label spec doc | 6h | TODO | `phases/phase-19/research/` |
| R19.2 | Spec mining sources + heuristics | Spec mining doc | 6h | TODO | `phases/phase-19/research/` |
| R19.3 | LLM labeler budget + schema | Prompt + budget doc | 4h | TODO | `phases/phase-19/research/` |
| R19.4 | Evaluation corpus selection | Corpus plan | 4h | TODO | `phases/phase-19/research/` |

### 2.2 Knowledge Gaps

- [ ] Which label types produce the highest detection gains
- [ ] How to encode invariants with minimal tokens
- [ ] How to avoid label drift across upgrades

### 2.3 External References

| Reference | URL/Path | Purpose | Last Verified |
|-----------|----------|---------|---------------|
| AdaTaint | https://arxiv.org/abs/2511.04023 | LLM + validation for taint | 2026-01-08 |
| VulInstruct | https://arxiv.org/abs/2511.04014 | Spec-based detection | 2026-01-08 |
| ReVul-CoT | https://arxiv.org/abs/2511.17027 | RAG + reasoning | 2026-01-08 |

### 2.4 Research Completion Criteria

- [ ] Research tasks complete and documented
- [ ] Taxonomy + prompt schema finalized
- [ ] Corpus selection justified

---

## 3. TASK DECOMPOSITION

### 3.1 Task Dependency Graph

```
R19.1 ─┬─ 19.1 ── 19.2 ── 19.3 ── 19.4
       │                    │
R19.2 ─┼─────────────┬──────┘
       │             └─ 19.5 ── 19.6 ── 19.7
R19.3 ─┼─ 19.2
R19.4 ─┴─ 19.8 ── 19.9 ── 19.10
```

### 3.2 Task Registry

| ID | Task | Est. | Priority | Depends On | Status | Exit Criteria |
|----|------|------|----------|------------|--------|---------------|
| R19.1 | Label taxonomy expansion | 6h | MUST | - | TODO | Taxonomy doc complete |
| R19.2 | Spec mining heuristics | 6h | MUST | - | TODO | Spec mining doc complete |
| R19.3 | Labeler prompt + budget | 4h | MUST | - | TODO | Prompt schema locked |
| R19.4 | Eval corpus selection | 4h | MUST | - | TODO | Corpus list approved |
| 19.1 | Candidate selection + slicing | 10h | MUST | R19.1 | TODO | Candidate generator + tests |
| 19.2 | LLM labeler microagent | 14h | MUST | R19.3, 19.1 | TODO | Labeler outputs valid schema |
| 19.3 | Label validation + scoring | 10h | MUST | 19.2 | TODO | Invalid labels rejected |
| 19.4 | Overlay lifecycle integration | 8h | MUST | 19.3 | TODO | Decay + rollback wired |
| 19.5 | Label-aware pattern matcher | 12h | MUST | 19.3 | TODO | Patterns can query labels |
| 19.6 | Policy mismatch pattern pack | 12h | SHOULD | 19.5 | TODO | 10+ label-aware patterns |
| 19.7 | Invariant/state patterns | 10h | SHOULD | 19.6 | TODO | Invariant + state rules |
| 19.8 | Real-world evaluation harness | 16h | MUST | R19.4 | TODO | End-to-end eval script |
| 19.9 | Token/cost profiler | 6h | SHOULD | 19.2 | TODO | Budget tests + reports |
| 19.10 | Retrospective + replan | 6h | MUST | 19.8-19.9 | TODO | Decision log + new tasks |

### 3.3 Dynamic Task Spawning

**Triggers:**
- Label precision < 0.75
- Token budget > 8k per label call
- Real-world delta < +5%

**Spawn Process:**
1. Create new task file in `phases/phase-19/tasks/`
2. Update tracker registry + dependency graph
3. Add retrospective note in `PHASE-19F-RETROSPECTIVE.md`

---

## 4. EXIT CRITERIA

- [ ] All MUST tasks complete
- [ ] Labeler precision >= 0.75
- [ ] Real-world eval shows measurable improvement
- [ ] Token budget enforced and reported
- [ ] Retrospective report completed

---

## 5. STAGE FILES

- `PHASE-19A-RESEARCH.md`
- `PHASE-19B-LABEL-TAXONOMY.md`
- `PHASE-19C-LABELER-PIPELINE.md`
- `PHASE-19D-PATTERN-INTEGRATION.md`
- `PHASE-19E-EVALUATION.md`
- `PHASE-19F-RETROSPECTIVE.md`
