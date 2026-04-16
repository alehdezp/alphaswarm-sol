# Guide Agent Debugging And Validation

**Purpose:** Provide a shared debugging and validation framework for production agents and sub-agents.

## When To Use

- Any time an agent or sub-agent is created or modified.
- When a test fails without a clear cause.

## Required Signals

- Transcript with tool markers.
- Report with duration, mode, and tokens.
- Evidence links to graph nodes, pattern IDs, and file:line locations.

## Drift Detection

- Re-run the same scenario with identical inputs.
- Compare findings and tool outputs.
- Excessive drift is a failure requiring investigation.

### Drift Indicator Library (Starter)

Watch for off-track behavior signals:
- "I'll help you with something else"
- "Let me reconsider" / "different approach"
- Asking clarifying questions when instructions were explicit
- Starting unrelated tasks
- Excessive apologizing or refusal without reason

This list is a starter set; formalize in the failure taxonomy plan seed.

## Scope Guardrails

- If the agent is assigned to a single pattern, it must only test that pattern.
- Unrelated findings must be marked as out-of-scope.
- Scope violations invalidate the run.

## Debugging Checklist

- Did the agent load the intended skill or prompt?
- Did the agent run BSKG queries before conclusions?
- Did the agent emit required tool markers?
- Did the agent respect scope constraints?
- Did the agent produce a complete evidence pack?

## Output Requirements

Every debugging run must include:

- Failure classification category.
- Rule or guideline violated.
- Evidence path.
- Recommended fix.
- When the failure occurred.
- Why it failed.

## Error Pattern Library (Starter)

Use these classifications for fast triage:

| Pattern | Type | Fixable |
|---|---|---|
| `ImportError` / `ModuleNotFoundError` | import_error | Yes |
| `FileNotFoundError` / `No such file` | file_not_found | Yes |
| `PermissionError` | permission | No |
| `SyntaxError` | syntax_error | Sometimes |
| `TypeError` | type_error | Sometimes |
| `ValidationError` | validation | Sometimes |
| `Tool execution failed` | tool_error | No |

This is a starter list; align with the failure taxonomy plan seed.
