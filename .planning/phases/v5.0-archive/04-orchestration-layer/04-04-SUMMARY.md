---
phase: 04-orchestration-layer
plan: 04
subsystem: orchestration
tags: [confidence, validation, rules, batching, enforcement]
requires: ["04-01"]
provides: ["ORCH-09", "ORCH-10", "confidence-enforcement", "orchestration-rules", "batching-policy"]
affects: ["04-05", "04-06", "04-07"]
tech-stack:
  added: []
  patterns: ["dataclass-validation", "enum-error-types", "rule-based-enforcement"]
key-files:
  created:
    - src/true_vkg/orchestration/confidence.py
    - src/true_vkg/orchestration/rules.py
    - tests/test_confidence_enforcement.py
  modified:
    - src/true_vkg/orchestration/__init__.py
decisions:
  - id: confidence-enforcement-layered
    choice: "ConfidenceEnforcer validates + enforces in two-step process"
    reason: "Allows validation-only mode vs auto-correction mode"
  - id: rules-batching-policy
    choice: "BatchingPolicy as dataclass with DEFAULT_BATCHING constant"
    reason: "Configurable batching while providing sensible defaults"
  - id: validation-error-types
    choice: "ValidationErrorType enum for categorized errors"
    reason: "Enables filtering and handling by error category"
  - id: rule-severity-levels
    choice: "RuleSeverity with ERROR/WARNING/INFO"
    reason: "Distinguishes blocking vs non-blocking violations"
metrics:
  duration: "~6 minutes"
  completed: "2026-01-20"
---

# Phase 4 Plan 04: Confidence Enforcement Summary

Confidence enforcement rules implementing ORCH-09 and ORCH-10 requirements.

## One-liner

Confidence enforcement with validation, auto-correction, test elevation, and batching policy for agent role ordering.

## What Was Built

### confidence.py (539 LOC)

**ConfidenceEnforcer Class:**
- `validate(verdict)` - Check verdict against rules without modification
- `enforce(verdict)` - Auto-correct verdict to pass validation
- `bucket_uncertain(finding_id, reason)` - Create UNCERTAIN verdict for missing context (ORCH-10)
- `elevate_on_test(verdict, test_passed)` - Elevate/downgrade based on test result

**ValidationResult Dataclass:**
- `is_valid` - Whether validation passed
- `errors` - List of ValidationError objects
- `warnings` - Non-blocking issues
- `enforced_changes` - Record of auto-corrections

**ValidationErrorType Enum:**
- MISSING_EVIDENCE, INSUFFICIENT_EVIDENCE, MISSING_RATIONALE
- DEBATE_INCOMPLETE, DEBATE_DISAGREEMENT
- CONFIDENCE_TOO_HIGH, INVALID_ELEVATION

### rules.py (606 LOC)

**OrchestrationRules Class:**
- `check_verdict_rules(verdict)` - Validate verdict against all rules (V-01 to V-06)
- `check_pool_rules(pool)` - Validate pool against all rules (P-01 to P-05)
- `can_advance_phase(pool)` - Check if pool can transition to next phase
- `get_next_batch(current_batch, completed_roles)` - Determine next agent batch
- `should_pause_for_human(pool)` - Check if human input needed
- `validate_batching(roles, batch_number)` - Validate role assignment to batch

**BatchingPolicy Dataclass:**
- `first_batch` - Agent roles to run first (default: ["attacker"])
- `second_batch` - Agent roles to run second (default: ["defender"])
- `third_batch` - Agent roles to run third (default: ["verifier"])
- `parallel_within_batch` - Whether to parallelize within batch
- `max_parallel` - Maximum concurrent agents
- `timeout_seconds` - Timeout per batch

**RuleViolation Dataclass:**
- `rule_type` - Category (VERDICT, POOL, PHASE, BATCHING, HUMAN_FLAG)
- `severity` - ERROR (blocking) / WARNING / INFO
- `message` - Human-readable description
- `rule_id` - Identifier (V-01, P-02, etc.)
- `suggested_fix` - Resolution guidance

### test_confidence_enforcement.py (757 LOC)

**TestConfidenceEnforcement (7 tests):**
- CONFIRMED without test downgraded to LIKELY
- CONFIRMED with test_pass evidence passes
- CONFIRMED with strong multi-source evidence passes
- LIKELY without evidence downgraded to UNCERTAIN
- LIKELY with evidence passes
- UNCERTAIN always passes
- REJECTED always passes

**TestMissingContextBucketing (3 tests):**
- bucket_uncertain creates UNCERTAIN verdict
- Preserves existing evidence
- Accepts custom reasons

**TestDebateHumanFlag (3 tests):**
- Disagreement triggers warning
- check_debate_requires_human always True
- human_flag always True after enforcement

**TestTestElevation (4 tests):**
- Test pass elevates to CONFIRMED
- Custom evidence preserved
- Test fail downgrades to REJECTED
- UNCERTAIN can be elevated

**TestOrchestrationRules (10 tests):**
- Human flag validation
- CONFIRMED requires evidence
- LIKELY requires evidence
- Positive requires rationale
- Pool requires scope
- EXECUTE requires beads
- Phase advancement rules
- Terminal status handling
- Paused status handling

**TestBatchingPolicy (4 tests):**
- Default ordering
- Role batch identification
- Custom policies
- Serialization roundtrip

**TestValidationResult (3 tests):**
- Error invalidates result
- Warning preserves validity
- Serialization

**TestConvenienceFunctions (2 tests):**
- enforce_confidence function
- validate_confidence function

## Rules Implemented

### Verdict Rules (V-01 to V-06)
| Rule | Description | Severity |
|------|-------------|----------|
| V-01 | human_flag must be True | ERROR |
| V-02 | CONFIRMED requires evidence | ERROR |
| V-03 | CONFIRMED should have debate | WARNING |
| V-04 | LIKELY requires evidence | ERROR |
| V-05 | Positive requires rationale | ERROR |
| V-06 | Dissent triggers human review | INFO |

### Pool Rules (P-01 to P-05)
| Rule | Description | Severity |
|------|-------------|----------|
| P-01 | Pool must have scope files | ERROR |
| P-02 | EXECUTE requires beads | ERROR |
| P-03 | COMPLETE should have all verdicts | WARNING |
| P-04 | FAILED should have reason | WARNING |
| P-05 | All verdicts must pass rules | Inherited |

## Truths Verified

1. **No likely/confirmed verdict without evidence** - LIKELY without evidence fails validation and is downgraded to UNCERTAIN
2. **Missing context defaults to uncertain bucket** - `bucket_uncertain()` creates UNCERTAIN verdict with reason
3. **Debate disagreement triggers human flag** - Dissenting opinion generates warning; human_flag always True
4. **Test passing can elevate to confirmed** - `elevate_on_test(test_passed=True)` elevates to CONFIRMED

## Key Links Verified

- `confidence.py` imports `VerdictConfidence` from `schemas.py` for confidence validation
- `rules.py` imports `Verdict`, `Pool`, `PoolStatus` from `schemas.py` for rule checking
- `__init__.py` exports all new types for module-level access

## Deviations from Plan

None - plan executed exactly as written.

## Commits

| Hash | Message | Files |
|------|---------|-------|
| 5179ca9 | feat(04-04): implement confidence enforcement rules | confidence.py, rules.py, tests |

## Next Phase Readiness

**Ready for:** Plan 04-05 (Agent Orchestration)
- ConfidenceEnforcer provides verdict validation for agent outputs
- OrchestrationRules provides phase transition logic
- BatchingPolicy defines agent execution order

**Dependencies satisfied:**
- Verdict schema from 04-01
- Pool lifecycle from 04-01
- Bead integration from 04-02
