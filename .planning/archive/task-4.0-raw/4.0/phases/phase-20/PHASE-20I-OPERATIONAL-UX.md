# Phase 20.I: Operational UX and Failure Modes

**Goal:** Validate that BSKG is usable by real auditors under real constraints.

---

## I.1 UX Focus Areas

- CLI clarity and ergonomics
- Output readability and evidence traceability
- Error messages and recovery guidance
- Tooling friction (setup, dependencies, docs)

**PHILOSOPHY alignment:** outputs must be evidence-first and behavior-first.

---

## I.2 UX Stress Tests

- Run on clean machine with no cached state
- Run with partial dependencies missing
- Run with malformed input contracts
- Run with large repos and nested submodules

---

## I.3 Output Template

Store in `task/4.0/phases/phase-20/artifacts/UX_FAILURES.md`:

```
- id: UX-001
  category: <setup|cli|output|errors|docs>
  severity: <major|minor>
  description: <short>
  reproduction: <steps>
  suggested_fix: <idea>
```

---

## I.4 Acceptance Criteria

- No blocker UX issues
- Clear error messages for 90% of failure cases
- Auditor can reproduce findings with minimal guidance

For each UX failure, link to the related orchestration trace entry.
