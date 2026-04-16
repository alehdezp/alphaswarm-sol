# Phase 19F: Retrospective and Optimization

**Purpose:** Use empirical results to refine labels, prompts, and
pattern definitions with minimal token costs.

---

## Required Inputs

- Evaluation results from Task 19.8
- Token/cost report from Task 19.9
- Label precision audit from Task 19.3

---

## Retrospective Questions

- Which label classes produced the highest detection gains?
- Which labels produced noise or false positives?
- Did token budgets hold across projects?
- Are label-aware patterns outperforming static patterns?

---

## Outputs

- `task/4.0/phases/phase-19/RETROSPECTIVE_REPORT.md`
- Updated task list if new work is required
- Recommendations for Phase 21+ (if needed)

---

## Spawn Rules

Create new tasks if any of the following are true:
- Label precision < 0.75
- Token budget > 8k per label call
- Improvement delta < +5%
- Label-to-pattern mapping ambiguous
