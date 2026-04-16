---
phase: 04
plan: 03
subsystem: orchestration
tags: [routing, execution-loop, deterministic-flow, batch-spawning]
depends_on:
  requires: ["04-01", "04-02"]
  provides: ["thin-routing-layer", "fixed-execution-loop", "phase-advancement"]
  affects: ["04-04", "04-05", "04-06"]
tech_stack:
  added: []
  patterns: ["handler-injection", "fixed-sequence-loop", "checkpoint-resume"]
key_files:
  created:
    - "src/true_vkg/orchestration/router.py"
    - "src/true_vkg/orchestration/loop.py"
    - "tests/test_execution_loop.py"
  modified:
    - "src/true_vkg/orchestration/__init__.py"
decisions:
  - id: "router-is-thin"
    choice: "Router only routes, no domain logic"
    rationale: "ORCH-01 requires thin routing layer"
  - id: "handler-injection"
    choice: "Domain logic injected via handlers"
    rationale: "Makes loop testable and swappable"
  - id: "batch-spawning-order"
    choice: "Attackers -> Defenders -> Verifiers"
    rationale: "Per 04-CONTEXT.md batch spawning decision"
metrics:
  duration: "4.5 minutes"
  completed: "2026-01-20"
---

# Phase 04 Plan 03: Thin Routing Layer and Execution Loop Summary

**One-liner:** Status-based routing + fixed execution loop with handler injection for deterministic orchestration

## What Was Done

### Task 1: Thin Routing Layer (ORCH-01)
Created `router.py` (297 LOC) implementing:

- **RouteAction enum** with 13 routing actions:
  - BUILD_GRAPH, DETECT_PATTERNS, LOAD_CONTEXT, CREATE_BEADS
  - SPAWN_ATTACKERS, SPAWN_DEFENDERS, SPAWN_VERIFIERS
  - RUN_DEBATE, COLLECT_VERDICTS, GENERATE_REPORT
  - FLAG_FOR_HUMAN, COMPLETE, WAIT

- **RouteDecision dataclass** capturing:
  - Action to take
  - Target beads (for batch operations)
  - Reason (for logging)
  - Metadata (extensibility)

- **Router class** with:
  - PHASE_ROUTES mapping status to action
  - `route()` pure function (no side effects)
  - `_route_execute_phase()` for batch spawning order
  - `_route_verify_phase()` for debate detection

### Task 2: Fixed Execution Loop (ORCH-07)
Created `loop.py` (483 LOC) implementing:

- **LoopPhase enum** mirroring pool lifecycle
- **PhaseResult dataclass** with success, phase, checkpoint tracking
- **LoopConfig dataclass** with auto_advance, pause_on_human_flag, max_iterations
- **ExecutionLoop class** with:
  - PHASE_ORDER fixed sequence (intake -> context -> beads -> execute -> verify -> integrate -> complete)
  - `run()` until checkpoint or completion
  - `run_single_phase()` for step-by-step execution
  - `resume()` for checkpoint continuation
  - `register_handler()` for domain logic injection
  - `_try_advance_phase()` with persistence

### Task 3: Tests
Created `test_execution_loop.py` (646 LOC) with 39 tests:

| Test Class | Tests | Coverage |
|------------|-------|----------|
| TestRouteAction | 2 | Action enum values |
| TestRouteDecision | 2 | Decision dataclass |
| TestRouter | 14 | Status routing, batch order, debate detection |
| TestRoutePoolConvenience | 1 | Convenience function |
| TestLoopPhase | 1 | Phase enum |
| TestPhaseResult | 2 | Result dataclass |
| TestLoopConfig | 2 | Config defaults |
| TestExecutionLoop | 10 | Loop behavior, checkpoints, resume |
| TestPhaseTransitions | 4 | Phase/status mapping |

## Key Design Decisions

### Router is Thin (ORCH-01)
The router contains NO domain logic:
```python
# Router only looks at status and metadata
decision = self.router.route(pool)
# Returns RouteAction - which handler to invoke
```

### Handler Injection Pattern
Domain logic is injected, not built-in:
```python
loop.register_handler(RouteAction.BUILD_GRAPH, build_graph_handler)
loop.register_handler(RouteAction.SPAWN_ATTACKERS, spawn_attackers_handler)
# Loop just orchestrates, handlers do the work
```

### Batch Spawning Order
Per 04-CONTEXT.md decision:
1. Attackers first (all at once)
2. Defenders after ALL attackers done
3. Verifiers after ALL defenders done

This ensures complete information flow before moving to next role.

### Checkpoint Resume
Loop can pause and resume:
```python
result = loop.run(pool_id)
if result.checkpoint:
    # Human does review
    pass
result = loop.resume(pool_id)  # Continue from where we left off
```

## Artifacts

| Artifact | Lines | Purpose |
|----------|-------|---------|
| router.py | 297 | Thin routing layer (ORCH-01) |
| loop.py | 483 | Fixed execution loop (ORCH-07) |
| test_execution_loop.py | 646 | 39 comprehensive tests |
| **Total** | **1,426** | |

## Verification Results

- [x] `uv run pytest tests/test_execution_loop.py -v` - 39/39 passed
- [x] Router is thin - no domain logic, just rules
- [x] Loop follows fixed sequence (PHASE_ORDER)
- [x] Loop pauses on human_flag
- [x] Each phase transition persisted via PoolManager.advance_phase()

## Commits

| Hash | Type | Description |
|------|------|-------------|
| fa66f9e | feat | Implement thin routing layer (ORCH-01) |
| ba4e031 | feat | Implement fixed execution loop (ORCH-07) |
| 848f79d | test | Add execution loop and router tests |
| 0e6aa76 | chore | Export router and loop from orchestration module |

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

**Prerequisites for 04-04 (Debate Protocol):**
- [x] Router can route to RUN_DEBATE action
- [x] Loop can checkpoint for human review
- [x] PoolStatus.VERIFY triggers debate detection

**Prerequisites for 04-05 (Agent Orchestration):**
- [x] Handler injection pattern ready
- [x] Batch spawning order defined
- [x] RouteAction for agent spawning defined
