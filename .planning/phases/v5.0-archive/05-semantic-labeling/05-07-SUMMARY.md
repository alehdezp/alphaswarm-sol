---
phase: 05-semantic-labeling
plan: 07
subsystem: patterns
tags: [tier-c, yaml, label-patterns, policy-mismatch, invariants, state-machine]

# Dependency graph
requires:
  - phase: 05-05
    provides: Tier C label-aware pattern matching (TierCMatcher)
  - phase: 05-06
    provides: VQL label query functions for executor integration
provides:
  - Label-dependent pattern packs (21 patterns total)
  - Policy mismatch detection (12 patterns)
  - Invariant violation detection (4 patterns)
  - State machine issue detection (5 patterns)
affects: [05-08, 05-09]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - tier_c YAML conditions with type/value/min_confidence
    - has_label/missing_label for intent vs code detection
    - has_any_label for flexible matching
    - has_category for category-level checks

key-files:
  created:
    - patterns/label_patterns/policy_mismatch.yaml
    - patterns/label_patterns/invariant_violation.yaml
    - patterns/label_patterns/state_machine.yaml
  modified: []

key-decisions:
  - "12 policy mismatch patterns for comprehensive coverage"
  - "All patterns use tier_abc_all aggregation mode"
  - "required_labels field specifies pattern prerequisites"
  - "Detailed descriptions with risk explanations"

patterns-established:
  - "Label pattern YAML format with tier_c conditions"
  - "Policy mismatch: intent (label) vs behavior (tier_a) comparison"
  - "Invariant patterns use has_category for flexible matching"
  - "State machine patterns use temporal labels"

# Metrics
duration: 3min
completed: 2026-01-21
---

# Phase 5 Plan 7: Mismatch Detection Summary

**21 label-dependent patterns across 3 categories detecting logic bugs via semantic label comparison with deterministic properties**

## Performance

- **Duration:** 3 min
- **Started:** 2026-01-21T10:30:11Z
- **Completed:** 2026-01-21T10:32:48Z
- **Tasks:** 3
- **Files created:** 3

## Accomplishments

- Created 12 policy mismatch patterns detecting intent vs. code disagreement (LABEL-09 requirement met)
- Created 4 invariant violation patterns detecting balance/supply constraint issues
- Created 5 state machine patterns detecting illegal state transitions
- All patterns validated with proper tier_c condition structure

## Task Commits

Each task was committed atomically:

1. **Task 1: Create policy_mismatch.yaml patterns (12 patterns)** - `212233a` (feat)
2. **Task 2: Create invariant_violation.yaml patterns (4 patterns)** - `afd75e6` (feat)
3. **Task 3: Create state_machine.yaml patterns (5 patterns)** - `aa68424` (feat)

## Files Created

- `patterns/label_patterns/policy_mismatch.yaml` - 12 patterns (498 LOC)
  - Unauthorized value transfer, unprotected state, owner bypass
  - Fee collection, initializer, admin action, withdrawal
  - Mint/burn unrestricted, pause bypass, oracle, upgrade
- `patterns/label_patterns/invariant_violation.yaml` - 4 patterns (154 LOC)
  - Balance unvalidated, supply manipulation, underflow risk, ratio violation
- `patterns/label_patterns/state_machine.yaml` - 5 patterns (193 LOC)
  - Double initialization, missing dependency, pause bypass, deadline, reentrancy

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| 12 policy mismatch patterns | Exceeds LABEL-09 requirement of 10+, covers major vulnerability classes |
| tier_abc_all aggregation | Both Tier A properties and Tier C labels must match for finding |
| required_labels field | Pattern prerequisites for efficient matching (skip if labels missing) |
| Detailed descriptions with risk | Each pattern explains the vulnerability and attack vector |
| Category-level checks for invariants | has_category enables flexible matching across related labels |

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Pattern files ready for Tier C pattern matching
- 21 total patterns across 3 vulnerability categories
- All patterns use valid tier_c condition types
- Ready for Plan 05-08: Full Integration

---
*Phase: 05-semantic-labeling*
*Completed: 2026-01-21*
