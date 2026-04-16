# Phase 19D: Label-Aware Pattern Integration

**Purpose:** Add label-aware matching so complex semantic patterns can
be expressed as rules over labels and properties.

---

## Key Inputs

- `src/true_vkg/queries/patterns.py`
- `patterns/core/` (existing YAML patterns)
- Overlay labels from `src/true_vkg/learning/overlay.py`

---

## Tasks

### 19.5 Label-Aware Pattern Matcher
**Doc:** `task/4.0/phases/phase-19/tasks/19.5-label-pattern-matcher.md`

### 19.6 Policy Mismatch Pattern Pack
**Doc:** `task/4.0/phases/phase-19/tasks/19.6-policy-mismatch-patterns.md`

### 19.7 Invariant + State Machine Patterns
**Doc:** `task/4.0/phases/phase-19/tasks/19.7-invariant-state-patterns.md`

---

## Exit Criteria

- [ ] Pattern engine can match on label overlays
- [ ] 10+ label-aware patterns defined
- [ ] Label-aware patterns evaluated on benchmarks

---

## Retrospective Trigger

If pattern matches are noisy or low precision, spawn a
label relevance tuning task.
