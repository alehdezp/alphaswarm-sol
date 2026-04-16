# Phase 19C: Labeler Pipeline

**Purpose:** Implement the LLM-driven labeling pipeline with strict
validation, token budgets, and project-scoped overlays.

---

## Key Inputs

- `src/true_vkg/learning/overlay.py`
- `src/true_vkg/learning/post_bead.py`
- `src/true_vkg/kg/slicer.py`

---

## Tasks

### 19.2 LLM Labeler Microagent
**Doc:** `task/4.0/phases/phase-19/tasks/19.2-llm-labeler.md`

### 19.3 Deterministic Label Validation
**Doc:** `task/4.0/phases/phase-19/tasks/19.3-label-validation.md`

### 19.4 Overlay Lifecycle Integration
**Doc:** `task/4.0/phases/phase-19/tasks/19.4-overlay-lifecycle.md`

### 19.9 Token/Cost Profiler
**Doc:** `task/4.0/phases/phase-19/tasks/19.9-token-cost-profiler.md`

---

## Exit Criteria

- [ ] Labeler output schema enforced
- [ ] Token budget enforced
- [ ] Labels stored with evidence + confidence

---

## Retrospective Trigger

If validation rejects > 30% of labels, spawn a prompt revision task
and lower candidate scope.
