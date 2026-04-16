# Phase 07.3.1.8 Synthetic Expansion + Stress Testing Context

**Status:** Draft context
**Scope:** Expand synthetic corpus and stress-test workflows across projects/worktrees
**Purpose:** Scale the synthetic dataset beyond 50 repos, introduce adversarial overlap, and validate stability under multi-project stress.

---

**Important**
This document is context only. It is not an execution plan and must not be treated as one.

## Phase Definition

- Perform gap analysis from 07.3.1.7 outputs.
- Expand synthetic dataset to **50+ repos** (up to 100 if gaps remain).
- Increase vulnerability overlap and adversarial/decoy signals.
- Stress-test workflows across **multi-project, multi-worktree** matrices.
- Produce coverage and stability reports, including FP/FN audits and misleading pattern lists.

## Locked Decisions (Non-Negotiable)

- Minimum dataset size: **50 synthetic repos**; target **75–100** if coverage gaps remain.
- Stress testing must use **claude-code-controller** with dedicated demo labels.
- Evidence packs and proof tokens are required for all runs.
- Metrics must show variance (no perfect scores) per anti-fabrication rules.
- External ground truth must be clearly separated from synthetic expectations.
- Stress matrix must include **multiple worktree configurations** and **git workflow variants**.

## Non-Goals

- Rewriting core detection algorithms (use existing frameworks).
- Claiming GA-level precision/recall from synthetic-only data.

## Required Sources Of Truth

- `.planning/testing/rules/canonical/RULES-ESSENTIAL.md`
- `.planning/testing/rules/canonical/VALIDATION-RULES.md`
- `.planning/testing/rules/canonical/TESTING-FRAMEWORK.md`
- `.planning/testing/rules/canonical/TESTING-PHILOSOPHY.md`
- `.planning/testing/rules/claude-code-controller-REFERENCE.md` and `.planning/testing/rules/canonical/claude-code-controller-instructions.md`
- `docs/PHILOSOPHY.md`
- `docs/reference/testing-framework.md`
- `.planning/phases/07.3.1.7-synthetic-test-environments-workspace-harness/*`

## Evidence Rules

- Evidence packs must include proof tokens and transcript markers.
- Transcript line/duration thresholds are mandatory.
- Workspace isolation and rollback must be validated for stress runs.

## Success Definition

- 50+ synthetic repos exist with overlap and adversarial patterns.
- Multi-project stress tests complete with claude-code-agent-teams evidence and recovery runs.
- Coverage/stability reports quantify FP/FN and misleading patterns.
