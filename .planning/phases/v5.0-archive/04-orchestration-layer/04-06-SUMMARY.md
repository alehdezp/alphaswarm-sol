---
phase: 04-orchestration-layer
plan: 06
subsystem: claude-skills
tags: [claude-code, skills, agents, orchestration, audit-workflow]
depends_on:
  requires: ["04-03", "04-04", "04-05"]
  provides: ["vkg-audit-skill", "vkg-agent-definitions", "orchestration-cli"]
  affects: ["04-07"]
tech_stack:
  added: []
  patterns: ["slash-commands", "agent-model-selection", "skill-hooks"]
key_files:
  created:
    - .claude/skills/vkg/audit.md
    - .claude/skills/vkg/investigate.md
    - .claude/skills/vkg/verify.md
    - .claude/skills/vkg/debate.md
    - .claude/agents/vkg-attacker.md
    - .claude/agents/vkg-defender.md
    - .claude/agents/vkg-verifier.md
  modified: []
decisions:
  - id: skill-slash-commands
    description: Skills use /vkg:* slash command pattern
  - id: model-selection
    description: Opus for attacker/verifier (quality), Sonnet for defender (speed)
  - id: skill-fork-context
    description: Skills run in forked context to prevent pollution
metrics:
  duration: ~5m
  completed: 2026-01-20
---

# Phase 04 Plan 06: Claude Skills and Agent Definitions Summary

**One-liner:** Claude Code skills (/vkg:audit, /vkg:investigate, /vkg:verify, /vkg:debate) and agent definitions (attacker/defender/verifier) for BSKG orchestration integration.

## What Was Built

### Skills Created (4 files, 1455 LOC)

| Skill | Trigger | Purpose | Lines |
|-------|---------|---------|-------|
| audit.md | `/vkg:audit` | Full audit workflow with ExecutionLoop | 400 |
| investigate.md | `/vkg:investigate` | Deep bead investigation | 310 |
| verify.md | `/vkg:verify` | Multi-agent verification | 345 |
| debate.md | `/vkg:debate` | Structured debate protocol | 400 |

### Agents Created (3 files, 1057 LOC)

| Agent | Model | Role | Lines |
|-------|-------|------|-------|
| vkg-attacker.md | claude-opus-4 | Exploit path constructor | 311 |
| vkg-defender.md | claude-sonnet-4 | Guard detection | 377 |
| vkg-verifier.md | claude-opus-4 | Verdict synthesis | 369 |

## Key Features

### Audit Skill (/vkg:audit)

- Documents full ExecutionLoop integration
- 7-phase workflow: INTAKE -> CONTEXT -> BEADS -> EXECUTE -> VERIFY -> INTEGRATE -> COMPLETE
- Agent spawning in batch order (attackers -> defenders -> verifiers)
- Checkpoint handling for human review
- Resume support after pauses
- LoopConfig and DebateConfig documentation

### Investigation Skill (/vkg:investigate)

- Deep-dive into individual beads
- Evidence display with code locations
- Behavioral signature explanation
- Guard detection analysis
- Status transition documentation

### Verify Skill (/vkg:verify)

- Multi-agent verification workflow
- Agent spawning with Task tool
- Batch order enforcement (attacker -> defender -> verifier)
- Confidence level documentation (CONFIRMED, LIKELY, UNCERTAIN, REJECTED)
- Skip-debate mode for faster verification

### Debate Skill (/vkg:debate)

- iMAD-inspired debate protocol
- Phase documentation: CLAIM -> REBUTTAL -> SYNTHESIS -> COMPLETE
- Evidence anchoring requirements
- Dissent recording for strong losing arguments
- Configurable rebuttal rounds

### Agent Definitions

**vkg-attacker (claude-opus-4):**
- Attack construction with evidence anchoring
- AttackStep and AttackConstruction output
- Exploitability scoring (0.0-1.0)
- Behavioral signature analysis

**vkg-defender (claude-sonnet-4):**
- Guard detection and strength assessment
- Protocol context integration
- Spec reference checking
- Defense rebuttal capability

**vkg-verifier (claude-opus-4):**
- Evidence synthesis (NOT new analysis)
- Confidence determination
- Dissent recording
- Human flag enforcement

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| `/vkg:*` slash commands | Follows Claude Code 2.1 skill pattern |
| claude-opus-4 for attacker/verifier | Quality over speed for critical analysis |
| claude-sonnet-4 for defender | Faster guard detection, balanced analysis |
| Forked context for skills | Prevents conversation pollution |
| Skill hooks for logging | Track agent spawning phases |

## Orchestration Module References

Skills reference these orchestration components:

| Component | Usage |
|-----------|-------|
| ExecutionLoop | Main audit workflow driver |
| PoolManager | Pool creation and storage |
| DebateOrchestrator | Structured debate protocol |
| ConfidenceEnforcer | Verdict validation |
| create_default_handlers | Phase handler registration |

## Commits

| Hash | Message |
|------|---------|
| 82a791d | feat(04-06): create BSKG audit skill |
| db1f693 | feat(04-06): create investigate, verify, and debate skills |
| 0de27c8 | feat(04-06): create BSKG agent definitions |

## Files Created

```
.claude/
  skills/
    vkg/
      audit.md         # 400 lines - /vkg:audit
      investigate.md   # 310 lines - /vkg:investigate
      verify.md        # 345 lines - /vkg:verify
      debate.md        # 400 lines - /vkg:debate
  agents/
    vkg-attacker.md    # 311 lines - claude-opus-4
    vkg-defender.md    # 377 lines - claude-sonnet-4
    vkg-verifier.md    # 369 lines - claude-opus-4
```

## Verification

### Must-Haves Verified

- [x] Skills are discoverable via /vkg:* commands (audit, investigate, verify, debate)
- [x] Agents have clear roles and model selection (opus/sonnet)
- [x] Skills reference orchestration module (ExecutionLoop, DebateOrchestrator)
- [x] Audit skill triggers full execution loop

### Artifact Requirements Verified

- [x] audit.md: 400 lines (>50), contains "orchestration", provides main audit skill
- [x] vkg-attacker.md: 311 lines, contains "opus", provides attacker definition
- [x] vkg-defender.md: 377 lines, contains "sonnet", provides defender definition

### Key Links Verified

- [x] audit.md -> loop.py via "ExecutionLoop" reference (line 73, 138-140)
- [x] Agents reference debate protocol via DebateClaim structure

## Next Phase Readiness

Plan 04-07 (Integration Tests) can now proceed:
- Skills documented for testing
- Agent definitions available for verification
- Orchestration module fully documented

## Deviations from Plan

None - plan executed exactly as written.
