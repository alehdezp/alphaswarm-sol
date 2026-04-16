# Phase 9: Context Optimization (PPR)

**Status:** COMPLETE (core) - fixtures pending
**Priority:** MEDIUM - Token efficiency for LLM usage
**Last Updated:** 2026-01-08
**Author:** BSKG Team

---

## Quick Reference

| Field | Value |
|-------|-------|
| Entry Gate | Phase 8 complete (metrics tracked) |
| Exit Gate | PPR works, balanced mode < 5% accuracy loss, token reduction measured |
| Philosophy Pillars | Knowledge Graph, NL Query System, Self-Improvement |
| Threat Model Categories | Data Minimization, Context Injection |
| Estimated Hours | 44h |
| Actual Hours | [Tracked as work progresses] |
| Task Count | 9 tasks (revised) |
| Test Count Target | 45+ tests |

---

## CRITIQUE SUMMARY

See `CRITIQUE.md` for detailed issues found. Key fixes:

1. **Moved 9.7 to 9.0** - Data minimization is SECURITY, comes FIRST
2. **Fixed PPR algorithm** - Original pseudocode had bugs (no normalization)
3. **Replaced TOON with YAML** - TOON doesn't exist, use real format
4. **Added R9.1 as proper research** - Algorithm needs research before implementation
5. **Clarified subgraph.py integration** - File already exists (23KB)
6. **Fixed unrealistic token reduction targets** - 30-40% realistic, not 70%
7. **Unified context modes + policy** - Were confusingly separate

---

## 1. OBJECTIVES

### 1.1 Primary Objective

Implement graph-based context optimization for LLM consumption, achieving 30-40% token reduction while preserving vulnerability detection accuracy.

### 1.0 CRITICAL RESEARCH: Graph Density Investigation

**See: [GRAPH_DENSITY_INVESTIGATION.md](GRAPH_DENSITY_INVESTIGATION.md)**

**Problem:** VKG's knowledge graph contains 50+ properties per function. When an LLM investigates a finding, it receives ALL properties - but only 8-12 are relevant for any given vulnerability category. This causes:
- Context pollution (noise fills context window)
- Hallucination risk (irrelevant fields confuse LLM)
- Token waste (paying for 40+ irrelevant properties)

**Proposed Solution: Category-Aware Graph Slicing**
```
Reentrancy finding → Slice to 8 reentrancy-relevant properties
Oracle finding     → Slice to 10 oracle-relevant properties
Access finding     → Slice to 12 access-relevant properties
```

**Expected Impact:**
| Stage | Before | After | Reduction |
|-------|--------|-------|-----------|
| Full Graph | 2000 tokens | - | - |
| Graph Slicing | - | 500 tokens | 75% |
| TOON Encoding | - | 350 tokens | 30% more |
| **Total** | **2000 tokens** | **350 tokens** | **82.5%** |

**Tasks Added:**
- 9.A: Define property sets per category
- 9.B: Implement GraphSlicer
- 9.C: Benchmark full vs sliced accuracy
- 9.D: Integrate with BeadCreator
- 9.E: Add "request more context" fallback

### 1.2 Secondary Objectives

1. Enforce data minimization principle - LLM sees only what's necessary (SECURITY)
2. Provide user-controllable context modes (strict/standard/relaxed)
3. Implement compact YAML format for token-efficient output
4. Create audit trail for all LLM context submissions

### 1.3 Philosophy Alignment

| Pillar | How This Phase Contributes |
|--------|---------------------------|
| Knowledge Graph | PPR leverages graph structure for intelligent subgraph extraction |
| NL Query System | Optimized context improves NL query accuracy by reducing noise |
| Agentic Automation | Context modes enable automated analysis with configurable precision |
| Self-Improvement | Token reduction metrics feed into optimization feedback loop |

### 1.4 Success Metrics (REVISED - Realistic Targets)

| Metric | Target | Minimum | How to Measure |
|--------|--------|---------|----------------|
| Token Reduction | 35% | 25% | `standard` vs `relaxed` mode token count |
| Accuracy Preservation | < 5% loss | < 10% loss | Vuln detection rate comparison |
| Compact Format | 30% reduction | 20% reduction | Compact YAML vs JSON |
| Critical Vuln Retention | 100% | 95% | All criticals detected in standard mode |

### 1.5 Non-Goals (Explicit Scope Boundaries)

- NOT modifying core graph building (Phase 1-4)
- NOT implementing LLM integration (that's Phase 11)
- Compact format is for LLM only, JSON remains canonical
- No query language changes in this phase

---

## 2. RESEARCH REQUIREMENTS

### 2.1 Required Research Before Implementation

| ID | Research Topic | Output | Est. Hours | Status | Task File |
|----|---------------|--------|------------|--------|-----------|
| R9.1 | PPR Algorithm for BSKG | Corrected algorithm with justification | 4h | TODO | `tasks/R9.1-ppr-research.md` |

### 2.2 Knowledge Gaps (ADDRESSED)

- [x] How does HippoRAG implement PPR? -> For text, not security graphs
- [x] How to weight security-relevant edges? -> See R9.1 research
- [x] What teleport probability (alpha)? -> 0.25 strict, 0.15 standard, 0.10 relaxed
- [x] Does TOON exist? -> NO, use YAML instead

### 2.3 Existing Code to Integrate With

| File | Size | Purpose | Integration |
|------|------|---------|-------------|
| `src/true_vkg/kg/subgraph.py` | 23KB | Subgraph extraction | Extend, don't replace |
| `src/true_vkg/llm/compressor.py` | 6KB | Context compression | Complement with PPR |
| `src/true_vkg/llm/optimizer.py` | 9KB | Optimization | Add PPR as strategy |
| `src/true_vkg/kg/rich_edge.py` | 23KB | Risk scores | Use for edge weights |

---

## 3. TASK DECOMPOSITION

### 3.1 Task Dependency Graph (CORRECTED)

```
9.0 (Data Minimization - SECURITY FIRST)
    │
    ├── R9.1 (PPR Research)
    │       │
    │       └── 9.1 (PPR Algorithm)
    │               │
    │               ├── 9.2 (Query-to-Seed Mapping)
    │               │
    │               └── 9.6 (Subgraph Extraction)
    │                       │
    │                       └── 9.4 (Context Modes)
    │                               │
    │                               └── 9.5 (Accuracy Validation)
    │
    └── 9.3 (Serialization)
            │
            └── 9.8 (Compact Output Format)
```

### 3.2 Task Registry (REVISED)

| ID | Task | Est. | Priority | Depends On | Status | Task File |
|----|------|------|----------|------------|--------|-----------|
| 9.0 | Data Minimization Security | 4h | MUST | - | DONE (38 tests) | `tasks/9.0-data-minimization-security.md` |
| R9.1 | PPR Algorithm Research | 4h | MUST | - | DONE | `tasks/R9.1-ppr-research.md` |
| 9.1 | VKG-PPR Algorithm | 8h | MUST | R9.1 | DONE (37 tests) | `tasks/9.1-ppr-algorithm.md` |
| 9.2 | Query-to-Seed Mapping | 4h | MUST | 9.1 | DONE (39 tests) | tasks/9.2-query-seed-mapping.md |
| 9.3 | Token-Optimized Serialization | 4h | MUST | - | DONE (33 tests) | tasks/9.3-serialization.md |
| 9.4 | Context Modes | 4h | MUST | 9.0, 9.6 | DONE (38 tests) | tasks/9.4-context-modes.md |
| 9.5 | Accuracy Validation | 6h | MUST | 9.4 | DONE (30 tests) | tasks/9.5-accuracy-validation.md |
| 9.6 | Subgraph Extraction | 4h | MUST | 9.1, 9.2 | DONE (37 tests) | tasks/9.6-subgraph-extraction.md |
| 9.8 | Compact Output Format | 4h | SHOULD | 9.3 | DONE (with 9.3) | `tasks/9.8-compact-output-format.md` |
| **9.A** | **Define Property Sets per Category** | 4h | **CRITICAL** | - | DONE (43 tests) | `GRAPH_DENSITY_INVESTIGATION.md` |
| **9.B** | **Implement GraphSlicer** | 6h | **CRITICAL** | 9.A | DONE (34 tests) | `GRAPH_DENSITY_INVESTIGATION.md` |
| **9.C** | **Benchmark Full vs Sliced Accuracy** | 4h | **CRITICAL** | 9.B | DONE (27 tests) | `GRAPH_DENSITY_INVESTIGATION.md` |
| **9.D** | **Integrate with BeadCreator** | 4h | SHOULD | 9.B, 9.C | DONE | `GRAPH_DENSITY_INVESTIGATION.md` |
| **9.E** | **Add "Request More Context" Fallback** | 2h | SHOULD | 9.D | DONE (24 tests) | `GRAPH_DENSITY_INVESTIGATION.md` |

**Note:** Task 9.7 was MERGED into Task 9.0 (security comes first)

### 3.3 Integration Points

| Component | Existing File | How PPR Integrates |
|-----------|---------------|-------------------|
| Subgraph | `kg/subgraph.py` | PPR scores guide node selection |
| Compression | `llm/compressor.py` | PPR runs before compression |
| Optimization | `llm/optimizer.py` | Add PPR as optimization strategy |
| Edge Weights | `kg/rich_edge.py` | Use risk_score for PPR weights |

---

## 4. TEST SUITE REQUIREMENTS

### 4.1 Test Categories

| Category | Count Target | Coverage Target | Location |
|----------|--------------|-----------------|----------|
| Unit Tests | 25 | 90% | `tests/test_ppr.py`, `tests/test_compact_output.py` |
| Security Tests | 10 | - | `tests/test_context_policy.py` |
| Integration Tests | 10 | - | `tests/integration/test_context_optimization.py` |

### 4.2 Test Fixtures Required

- [ ] `tests/fixtures/VulnerableWithdraw.sol` - Reentrancy test case
- [ ] `tests/fixtures/ComplexDeFi.sol` - Multi-function DeFi contract
- [ ] `tests/fixtures/LargeContract.sol` - Token budget stress test

---

## 5. IMPLEMENTATION GUIDELINES

### 5.1 File Locations

| Component | Location | Naming Convention |
|-----------|----------|-------------------|
| PPR Core | `src/true_vkg/kg/ppr.py` | `snake_case.py` |
| PPR Weights | `src/true_vkg/kg/ppr_weights.py` | `snake_case.py` |
| Context Policy | `src/true_vkg/llm/context_policy.py` | `snake_case.py` |
| Compact Output | `src/true_vkg/output/compact.py` | `snake_case.py` |
| Tests | `tests/test_ppr.py` | `test_[feature].py` |

### 5.2 Dependencies

| Dependency | Version | Purpose | Optional? |
|------------|---------|---------|-----------|
| numpy | >= 1.20 | PPR matrix operations | No |
| pyyaml | >= 6.0 | Compact YAML format | No |

**Note:** tiktoken removed - use provider-agnostic token estimation

### 5.3 Configuration

```yaml
# New configuration options
context:
  policy: standard     # strict, standard, relaxed
  show_filtered: false # Show what was filtered

ppr:
  alpha:
    strict: 0.25       # High teleport
    standard: 0.15     # Balanced
    relaxed: 0.10      # Wide exploration
  max_iter: 50
  epsilon: 0.0001

output:
  format: json         # json, compact, yaml
  detail: detailed     # summary, detailed, full
```

---

## 6. REFLECTION PROTOCOL

### 6.1 Critical Risks (From Critique)

| Risk | Mitigation |
|------|------------|
| PPR cuts wrong nodes | User-controllable policy levels |
| TOON doesn't exist | Replaced with YAML |
| 70% reduction unrealistic | Revised to 30-40% target |
| Security is afterthought | Made 9.0 - comes FIRST |

### 6.2 Fallback Plans

**If PPR consistently loses vulnerabilities:**
1. Increase alpha (more teleport = closer to seeds)
2. Add "critical edge" protection list
3. Fall back to relaxed mode for high-severity findings

---

## 7. COMPLETION CHECKLIST

### 7.1 Exit Criteria

- [ ] All tasks completed
- [ ] All tests passing
- [ ] Security policy enforced (standard = default)
- [ ] PPR algorithm works and converges
- [ ] Accuracy loss < 5% in standard mode
- [ ] Token reduction >= 25%
- [ ] Audit trail for LLM context

**Gate Keeper:** Run on 10 vulnerable contracts. With standard mode, detection must work 9/10 times.

### 7.2 Artifacts Produced

| Artifact | Location | Purpose |
|----------|----------|---------|
| Context Policy | `src/true_vkg/llm/context_policy.py` | Security enforcement |
| PPR Module | `src/true_vkg/kg/ppr.py` | Graph-based optimization |
| Compact Encoder | `src/true_vkg/output/compact.py` | Token-efficient output |
| Tests | `tests/test_ppr.py`, `tests/test_context_policy.py` | Validation |

---

## 8. TASK FILES

All tasks have self-contained task files in `tasks/` directory:

| File | Description |
|------|-------------|
| `tasks/9.0-data-minimization-security.md` | Security policy (FIRST) |
| `tasks/R9.1-ppr-research.md` | PPR algorithm research |
| `tasks/9.1-ppr-algorithm.md` | PPR implementation |
| `tasks/9.8-compact-output-format.md` | Compact YAML (replaces TOON) |

**Pick up any task file independently.** Each contains:
- Full implementation steps
- Code examples
- Validation criteria
- Test requirements
- Files to create/modify

---

*Phase 9 Tracker | Version 3.0 | 2026-01-07*
*Revised after brutal critique - see CRITIQUE.md*

---

## Alignment Addendum (Workstream P)

### Workstream P: Alignment Tasks

| ID | Objective | Start here | Dependencies | Deliverables | Validation | Conflicts | Spawn Triggers |
|----|-----------|------------|--------------|--------------|------------|-----------|----------------|
| P9.P.1 | Treat evidence packet as minimal context contract for PPR | `docs/PHILOSOPHY.md`, `src/true_vkg/context/` | P1.P.1 | Output contract notes | Phase 11 LLM usage references it | Do not drop required fields | PPR drops required fields |
| P9.P.2 | Define request-more-context rules + flags | `docs/PHILOSOPHY.md`, `src/true_vkg/context/` | P9.P.1 | Fallback rules | Phase 10 degraded mode uses flags | No silent failures | Missing field detected |

### Review Tasks (Required + Phase-Specific)

| ID | Objective | Start here | Dependencies | Deliverables | Validation | Conflicts | Spawn Triggers |
|----|-----------|------------|--------------|--------------|------------|-----------|----------------|
| P9.R.1 | Phase necessity review (keep/cut/modify) | `task/4.0/MASTER.md`, `docs/PHILOSOPHY.md` | - | Decision log in tracker | Decision referenced in alignment sweep | None | Phase outputs no longer needed |
| P9.R.2 | Task necessity review for P9.P.* | `task/4.0/phases/phase-9/TRACKER.md`, `task/codex/vkg_4_0_alignment_super_task.md` | P9.P.1-P9.P.2 | Task justification log | Each task has keep/merge decision | Avoid overlap with Phase 11 | Redundant task discovered |
| P9.R.3 | Conflict review with downstream phases | `task/4.0/MASTER.md` | P9.P.1-P9.P.2 | Conflict notes in tracker | Conflicts resolved or escalated | Tier A/Tier B separation | Conflict discovered |
| P9.R.4 | Resolve format conflicts with Phase 6 | `task/4.0/phases/phase-6/TRACKER.md` | P9.P.1 | Format compatibility note | JSON canonical recorded | TOON remains optional | Format conflict found |

### Dynamic Task Spawning (Alignment)

**Trigger:** PPR drops required fields.
**Spawn:** Add PPR tuning task.
**Example spawned task:** P9.P.3 Tune PPR to retain evidence packet fields.
