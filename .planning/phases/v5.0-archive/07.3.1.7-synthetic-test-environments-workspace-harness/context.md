# Phase 07.3.1.7 Synthetic Test Environments + Workspace Harness Context

**Status:** Draft context
**Scope:** Synthetic repo foundation + jj workspace isolation for workflow testing
**Purpose:** Build a controlled, fake-but-realistic corpus and a repeatable jj workspace harness so workflows can be tested without full audit reruns.

---

**Important**
This document is context only. It is not an execution plan and must not be treated as one.

## Phase Definition

- Build the **foundation dataset** of synthetic repos (target: 20) under `tests/fixtures/repos/`.
- Establish a **standard repo template** and **manifest schema** for synthetic repos.
- Enforce **quality gates** for vulnerability diversity, decoys, safe controls, compile, and graph build.
- Provide a **jj workspace-based harness** for isolation, rollback, and debug-friendly iteration.
- Define **3 scenarios per workflow** for baseline validation, plus a mini-stress subset.

## Locked Decisions (Non-Negotiable)

- Phase 1 target: **20 synthetic repos** in `tests/fixtures/repos/`.
- Each repo must be a minimal PoC and **compile or run sufficiently** for workflow tests.
- Each repo must **build a graph** successfully (graph-first validation).
- Each repo must include **intentional vulnerabilities** (multiple types when possible), **decoy signals**, and at least one **safe control**.
- Each repo must include **meaningful jj revision history + checkpoints** for workspace branching.
- Workflows are tested using **claude-code-controller** with dedicated demo labels `vrs-demo-{workflow}-{timestamp}`.
- External ground truth is **not** derived from synthetic repos. Synthetic repos use **expectations** only.

## Non-Goals

- Expanding beyond 20 repos (handled in 07.3.1.8).
- Claiming external validation precision/recall from synthetic repos.
- Modifying `builder_legacy.py` or `executor.py`.

## Required Sources Of Truth

- `.planning/testing/rules/canonical/RULES-ESSENTIAL.md`
- `.planning/testing/rules/canonical/VALIDATION-RULES.md`
- `.planning/testing/rules/canonical/TESTING-FRAMEWORK.md`
- `.planning/testing/rules/canonical/TESTING-PHILOSOPHY.md`
- `.planning/testing/rules/claude-code-controller-REFERENCE.md` and `.planning/testing/rules/canonical/claude-code-controller-instructions.md`
- `docs/PHILOSOPHY.md`
- `docs/reference/testing-framework.md`
- `docs/workflows/README.md`
- `docs/workflows/PLAYBOOKS.md`
- `scripts/manage_workspaces.sh`
- `configs/workspace_snapshot_policy.yaml`

## Execution Model

- All execution is autonomous with conditional human confirmation (confidence < 0.95).
- Every workflow test must emit transcripts and evidence packs with proof tokens.
- Graph-first enforcement is mandatory: BSKG/VQL queries run before conclusions.

## Evidence Rules

- Evidence packs must include proof tokens (graph hash, agent spawn, debate, detection).
- Transcript markers must include TaskCreate/TaskUpdate and stage markers.
- claude-code-agent-teams transcripts must meet minimum line + duration thresholds.

## Workspace Strategy

- Use one jj workspace per workflow scenario.
- Allow rollback to explicit revisions without full audit reruns (`jj edit <revision>`).
- Preserve `.vrs/` state in debug mode for failure analysis.
- Enforce collision checks to prevent shared `.vrs` state across workspaces.
- Leverage jj's automatic conflict detection for parallel workspace safety.

## Success Definition

- 20 synthetic repos exist with manifests, checkpoints, and quality gate compliance.
- Workspace harness can create/rollback isolated scenario runs with collision checks.
- Each workflow has 3 scenario variants defined and runnable via claude-code-controller.
- Mini-stress subset demonstrates expanded run size beyond baseline.
- `jj workspace add` / `jj workspace forget` commands work correctly in harness.
