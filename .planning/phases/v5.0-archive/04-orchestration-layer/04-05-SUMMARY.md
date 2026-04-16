---
phase: 04
plan: 05
subsystem: orchestration
tags: [debate, agents, handlers, iMAD]
dependency-graph:
  requires: ["04-01", "04-02", "04-03"]
  provides: ["debate-protocol", "phase-handlers"]
  affects: ["04-06", "04-07"]
tech-stack:
  added: []
  patterns: ["iMAD-inspired-debate", "handler-injection", "evidence-anchoring"]
key-files:
  created:
    - src/true_vkg/orchestration/debate.py
    - src/true_vkg/orchestration/handlers.py
    - tests/test_debate_protocol.py
  modified:
    - src/true_vkg/orchestration/__init__.py
decisions:
  - id: debate-always-human-flagged
    choice: "All debate outcomes require human review"
    rationale: "Per PHILOSOPHY.md - no fully autonomous verdicts"
  - id: evidence-anchoring-required
    choice: "Claims must reference code locations"
    rationale: "iMAD protocol requires grounded evidence"
  - id: handler-injection-pattern
    choice: "Handlers injected into loop, not hardcoded"
    rationale: "Enables testing and swapping domain logic"
  - id: rebuttal-rounds-configurable
    choice: "Default 2 rebuttal rounds, configurable"
    rationale: "Balance debate depth vs. efficiency"
metrics:
  duration: 5 min
  completed: 2026-01-20
---

# Phase 4 Plan 5: Agent Orchestration Summary

**One-liner:** Structured debate protocol with claim/rebuttal/synthesis phases and handler injection for execution loop.

## What Was Built

### 1. Structured Debate Protocol (debate.py - 802 LOC)

Implements iMAD-inspired multi-agent debate:

- **DebatePhase enum**: CLAIM -> REBUTTAL -> SYNTHESIS -> COMPLETE
- **DebateOrchestrator**: Orchestrates full debate between attacker/defender
- **DebateRound**: Captures arguments from each round
- **DebateConfig**: Configurable max rebuttals, evidence requirements
- **run_debate()**: Convenience function for quick debates

Key features:
- Evidence anchoring: All claims must have code locations
- Human flagging: All debate outcomes flagged for human review
- Dissent tracking: Strong minority opinions preserved
- Confidence synthesis: Weighs attacker vs defender evidence

### 2. Phase Handlers (handlers.py - 1057 LOC)

Handlers for all RouteActions connecting loop to BSKG modules:

| Handler | Action | Purpose |
|---------|--------|---------|
| BuildGraphHandler | BUILD_GRAPH | Builds BSKG from scope files |
| LoadContextHandler | LOAD_CONTEXT | Loads protocol context pack |
| DetectPatternsHandler | DETECT_PATTERNS | Runs pattern engine |
| CreateBeadsHandler | CREATE_BEADS | Creates beads from matches |
| SpawnAttackersHandler | SPAWN_ATTACKERS | Spawns attacker agents |
| SpawnDefendersHandler | SPAWN_DEFENDERS | Spawns defender agents |
| SpawnVerifiersHandler | SPAWN_VERIFIERS | Synthesizes results |
| RunDebateHandler | RUN_DEBATE | Runs structured debate |
| CollectVerdictsHandler | COLLECT_VERDICTS | Finalizes verdicts |
| GenerateReportHandler | GENERATE_REPORT | Generates audit report |
| FlagForHumanHandler | FLAG_FOR_HUMAN | Flags for human review |
| CompleteHandler | COMPLETE | Marks audit complete |
| WaitHandler | WAIT | No-op waiting state |

Factory function:
- `create_default_handlers(manager, config)` - Returns all handlers

### 3. Tests (test_debate_protocol.py - 686 LOC)

Comprehensive test coverage:

| Test Class | Tests | Purpose |
|------------|-------|---------|
| TestDebatePhases | 4 | Phase enum and round structure |
| TestDebateConfig | 2 | Configuration options |
| TestDebateProtocol | 5 | Claim/rebuttal/synthesis execution |
| TestEvidenceAnchoring | 5 | Evidence items and locations |
| TestDebateOutcomes | 4 | Attacker/defender/uncertain outcomes |
| TestDissentTracking | 3 | Dissenting opinion detection |
| TestDebateRecord | 2 | Record creation and completion |
| TestConvenienceFunction | 3 | run_debate function |
| TestRationaleSynthesis | 3 | Rationale generation |
| TestPhaseHandlersIntegration | 3 | Handler imports |

**Total: 34 tests, all passing**

## Commits

| Hash | Type | Description |
|------|------|-------------|
| d6057fe | feat | implement structured debate protocol |
| 5f43ab7 | feat | implement phase handlers for execution loop |
| d9b9a62 | test | add debate protocol tests |
| 58621de | chore | export debate and handler modules |

## Key Links Verified

- debate.py -> agents/attacker.py: Uses AttackerAgent.analyze()
- debate.py -> agents/defender.py: Uses DefenderAgent.analyze()
- handlers.py -> loop.py: Implements RouteAction handlers
- handlers.py -> debate.py: RunDebateHandler uses DebateOrchestrator

## Verification Checklist

- [x] `uv run pytest tests/test_debate_protocol.py -v` passes (34/34)
- [x] Debate follows claim -> rebuttal -> synthesis protocol
- [x] All debate outcomes are human-flagged
- [x] Handlers connect loop to BSKG modules
- [x] debate.py >= 150 lines (802)
- [x] handlers.py >= 200 lines (1057)
- [x] tests >= 100 lines (686)

## Deviations from Plan

None - plan executed exactly as written.

## Must-Haves Verification

### Truths

| Truth | Verified |
|-------|----------|
| Debate follows structured protocol: claim -> rebuttal -> synthesis | Yes - DebateOrchestrator.run_debate() |
| Evidence is anchored to code locations | Yes - EvidenceItem.location required |
| Disagreement triggers human flag | Yes - Always True per _run_synthesis() |
| Verifier synthesizes attacker/defender arguments | Yes - _assess_debate_outcome() |

### Artifacts

| Artifact | Status | LOC |
|----------|--------|-----|
| debate.py | Created | 802 |
| handlers.py | Created | 1057 |
| test_debate_protocol.py | Created | 686 |

## Next Phase Readiness

Phase 4 Wave 3 progress:
- Plan 04-05 COMPLETE: Agent orchestration (this plan)
- Plan 04-06 PENDING: CLI + Audit Workflow

Ready for:
1. CLI commands for audit workflow (04-06)
2. Integration testing (04-07)
