---
phase: 02-builder-foundation-modularization
plan: 05
subsystem: kg-builder
tags: [call-tracking, confidence-scoring, callbacks, reentrancy, slither]

# Dependency graph
requires:
  - phase: 02-01
    provides: BuildContext DI pattern
  - phase: 02-02
    provides: Core orchestration module
  - phase: 02-04
    provides: FunctionProcessor and helpers.py

provides:
  - CallTracker class with confidence-scored call edges
  - CallInfo and CallbackPattern dataclasses
  - Callback detection (flash loans, ERC777, ERC721, Uniswap)
  - Bidirectional edges for reentrancy detection
  - Unresolved target tracking

affects:
  - 02-06 (Proxy Resolution)
  - 02-07 (Determinism + Completeness Report)
  - 02-08 (Integration + Final Testing)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Confidence scoring (HIGH/MEDIUM/LOW)
    - Resolution tracking (direct/inferred/interface/unresolved)
    - Callback pattern detection for bidirectional edges

key-files:
  created:
    - src/true_vkg/kg/builder/calls.py
  modified:
    - src/true_vkg/kg/builder/types.py
    - src/true_vkg/kg/builder/__init__.py

key-decisions:
  - "24 callback patterns covering flash loans, ERC777, ERC721, Uniswap"
  - "CALLBACK_FROM edge type for bidirectional callback detection"
  - "Resolution-based confidence: direct=HIGH, interface=MEDIUM, unresolved=LOW"

patterns-established:
  - "CallTracker follows processor pattern from FunctionProcessor"
  - "Callback detection creates bidirectional edges for reentrancy analysis"
  - "Unresolved targets tracked via BuildContext.add_unresolved()"

# Metrics
duration: 6min
completed: 2026-01-20
---

# Phase 02 Plan 05: Call Tracking + Confidence Summary

**CallTracker with per-edge confidence scoring (HIGH/MEDIUM/LOW), 24 callback patterns for bidirectional edge creation, and unresolved target tracking**

## Performance

- **Duration:** 6 min
- **Started:** 2026-01-20T20:50:31Z
- **Completed:** 2026-01-20T20:56:51Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Created CallTracker class (1160 LOC) with confidence-scored edge creation
- Added CallInfo and CallbackPattern dataclasses for type-safe call tracking
- Implemented 24 callback patterns (flash loans, ERC777, ERC721, Uniswap swaps)
- Bidirectional CALLBACK_FROM edges for reentrancy pattern detection
- Unresolved targets tracked in BuildContext for completeness reporting

## Task Commits

Each task was committed atomically:

1. **Task 1: Add CallInfo and callback types** - `66a208d` (feat)
2. **Task 2: Create calls.py with CallTracker** - `3f9ec3e` (feat)
3. **Task 3: Update exports and run tests** - `a1ca9e8` (chore)

## Files Created/Modified
- `src/true_vkg/kg/builder/calls.py` - CallTracker class with call tracking, callback detection, and confidence scoring (1160 LOC)
- `src/true_vkg/kg/builder/types.py` - Added CallInfo, CallbackPattern, CallType, TargetResolution types
- `src/true_vkg/kg/builder/__init__.py` - Updated exports for call tracking

## Decisions Made
- **24 callback patterns** covering flash loans (flashLoan, flash, flashLoanSimple), ERC777 (transfer, send), ERC721 (safeTransferFrom, safeMint), ERC1155, and Uniswap (swap, uniswapV2Call)
- **CALLBACK_FROM edge type** for bidirectional edges linking external calls to their callback handlers
- **Resolution-based confidence**: direct contract references get HIGH, interface types get MEDIUM, unresolved/dynamic targets get LOW
- **TargetResolution enum**: direct, inferred, interface, unresolved for understanding how targets were resolved

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- One unrelated test failure (Google provider quota exceeded) - not related to call tracking changes
- All builder and integration tests pass (149 builder tests, 286 related tests)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Call tracking module complete and exported
- Ready for Plan 02-06 (Proxy Resolution) which may use call tracking for proxy detection
- Ready for Plan 02-07 (Determinism + Completeness Report) which will report unresolved targets

---
*Phase: 02-builder-foundation-modularization*
*Completed: 2026-01-20*
