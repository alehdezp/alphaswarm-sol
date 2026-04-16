# Workflow Context

**Purpose:** Minimal overview of how workflows fit together.

## Visual Diagrams

**Start here for visual understanding:**

| Diagram | When to Load |
|---------|--------------|
| [00-master-orchestration](diagrams/00-master-orchestration.md) | System overview |
| [01-audit-stages](diagrams/01-audit-stages.md) | Audit pipeline detail |
| [02-task-lifecycle](diagrams/02-task-lifecycle.md) | Task state machine |
| [03-verification-debate](diagrams/03-verification-debate.md) | Multi-agent debate |
| [04-progress-state](diagrams/04-progress-state.md) | Resume/rollback |
| [05-testing-architecture](diagrams/05-testing-architecture.md) | Dev testing patterns |

Full index: [diagrams/README.md](diagrams/README.md)

## Orchestrator Overview

The audit entrypoint (`/vrs-audit`) is the main orchestrator. It sequences 9 stages:

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Preflight → 2. Graph → 3. Context → 4. Tools → 5. Detection │
│                                                                  │
│ 6. Tasks → 7. Verification → 8. Report → 9. Progress            │
└─────────────────────────────────────────────────────────────────┘
```

See [01-audit-stages](diagrams/01-audit-stages.md) for stage details.

## Task & Verification Flow

```
TaskCreate(candidate) → Attacker → Defender → Verifier → TaskUpdate(verdict)
```

See [02-task-lifecycle](diagrams/02-task-lifecycle.md) and [03-verification-debate](diagrams/03-verification-debate.md).

## Hook Enforcement

Hooks enforce workflow compliance:

| Hook | Enforcement |
|------|-------------|
| `SessionStart` | Load state, emit current stage |
| `PreToolUse` | Block if preflight failed |
| `Stop/SubagentStop` | Block if no TaskCreate/TaskUpdate |

## Settings vs State

- **Settings:** `.vrs/settings.yaml` (user-configured)
- **State:** `.vrs/state/current.yaml` (auto-updated per stage)

See [04-progress-state](diagrams/04-progress-state.md) for state schema.

## Testing Workflows

Workflow testing uses automated test suites and evidence-based validation:

```
pytest tests/ → Evidence Validation → Pass/Fail
```

See [05-testing-architecture](diagrams/05-testing-architecture.md).

## Progressive Disclosure

1. Start with this file for overview
2. Load [diagrams/README.md](diagrams/README.md) for visual index
3. Load specific workflow doc from [README.md](README.md)
4. Load [testing-framework.md](../reference/testing-framework.md) for validation rules
5. Load [claude-code-orchestration.md](../reference/claude-code-orchestration.md) for hooks
