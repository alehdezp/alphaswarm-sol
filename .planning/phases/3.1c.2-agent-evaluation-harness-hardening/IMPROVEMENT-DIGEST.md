# Improvement Digest — Phase 3.1c.2

**Generated:** 2026-03-01
**Passes:** 1
**Total items:** 22 (21 implemented, 1 reframed)

## Active Items

No active items — all items are terminal.

## Rejection Log

| ID | Verdict | Reason |
|----|---------|--------|
| P1-IMP-05 | reframed | Symlink swap rejected: obs hooks are observation-only and cannot block/abort on failure. Replaced by P1-ADV-2-01 (env-var gating + invocation-time config). |

## Convergence State

Pass 1: 0% cosmetic (0/22). Signal: ACTIVE.
All 22 items were structural — no cosmetic tweaks. This is expected for Pass 1 where foundational corrections dominate.

## Provenance Manifest

| ID | Verdict | Lens | Key Insight |
|----|---------|------|-------------|
| P1-IMP-01 | implemented | Enforcement Model Correction | subagent_type does NOT enforce tools; delegate_guard.py PreToolUse hook is the real primitive |
| P1-IMP-02 | implemented | Enforcement Model Correction | Current blocked_patterns [".sol"] provides ZERO Python import blocking; need ["python", "python3", "import "] |
| P1-IMP-03 | implemented | Enforcement Model Correction | Exit criteria must be disk-observable or behavior-observable, not judgment calls |
| P1-IMP-04 | implemented | Plan Completeness | JSONL transcripts at ~/.claude/projects/{path}/{uuid}.jsonl; SubagentStop hook provides agent_transcript_path (v2.0.42+) |
| P1-IMP-05 | reframed | Plan Completeness | Symlink swap fails silently; replaced by env-var gating (P1-ADV-2-01) |
| P1-IMP-06 | implemented | Plan Completeness | Exit criterion 5 needs explicit failure mode mapping to validator checks, not just "VERDICT: PASS" |
| P1-IMP-07 | implemented | Plan Completeness | Coverage audit of existing artifacts before planning prevents duplicate work |
| P1-IMP-08 | implemented | Enforcement Model Correction | Plan 01 deliverable is delegate_guard_config_eval.yaml, not prompt templates |
| P1-IMP-09 | implemented | Plan Completeness | Plan 02 scope = CLIAttemptState enum + JSONL parser; 4-state enum distinguishes tried/failed from never-tried |
| P1-IMP-10 | implemented | Plan Completeness | Plan 05 should wire existing 3.1c debrief protocol, not re-design it |
| P1-IMP-11 | implemented | Enforcement Model Correction | Output Contract row 1: YAML config + activation script, not prompt templates |
| P1-IMP-12 | implemented | Plan Completeness | Pre-phase snapshot must be created before Plan 01 runs; no plan currently owns this |
| P1-IMP-13 | implemented | Plan Completeness | Plan 06 needs explicit thresholds: 0 critical violations, CLIAttemptState success, non-zero query results |
| P1-IMP-14 | implemented | Plan Completeness | Plans need explicit dependency graph with wave assignments; 3.1c.1 merge is a hard prerequisite |
| P1-ADV-2-01 | implemented | ADV Validation | Config read at INVOCATION time; env-var gating (ALPHASWARM_EVAL_MODE + DELEGATE_GUARD_CONFIG) is correct scoping |
| P1-SYN-01 | implemented | Synthesis | Wrong enforcement layer at 4 CONTEXT locations must be fixed atomically |
| P1-SYN-02 | implemented | Synthesis | All 5 exit criteria need disk-observable + behavior-observable rewrite |
| P1-SYN-03 | implemented | Synthesis | Dependencies needed at both inter-plan (table) and intra-plan (task-level) granularity |
| P1-CSC-01 | implemented | Cascade | D-1 must propagate IMP-01's enforcement correction |
| P1-CSC-02 | implemented | Cascade | Output Contract row 1 must match IMP-08's YAML config deliverable |
| P1-CSC-03 | implemented | Cascade | Failure mode map needs check 13 (CLIAttemptState) after IMP-09 |
| P1-CSC-04 | implemented | Cascade | Testing Gate plan references must update if IMP-07 reduces plan count |

## Merged Summary

| Pass | Date | Items | Structural | Cosmetic | Themes |
|------|------|-------|------------|----------|--------|
| 1 | 2026-03-01 | 22 | 22 | 0 | Enforcement model correction (prompt→hook), exit criteria observability, plan dependency graph, coverage audit |

## Research Findings (from gaps/)

| Gap | Finding | Confidence |
|-----|---------|------------|
| GAP-01 | blocked_patterns [".sol"] does NOT block Python imports; need ["python", "python3", "import "] | HIGH |
| GAP-02 | JSONL at ~/.claude/projects/{path}/{uuid}.jsonl; SubagentStop hook provides agent_transcript_path | HIGH |
| GAP-03 | Config read at invocation time; env-var gating recommended (ALPHASWARM_EVAL_MODE + DELEGATE_GUARD_CONFIG) | HIGH |
