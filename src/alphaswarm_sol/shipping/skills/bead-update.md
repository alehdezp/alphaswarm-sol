---
name: vrs-bead-update
description: Update status of an existing bead
slash_command: vrs:bead-update
context: fork
disable-model-invocation: false
allowed-tools: Bash(alphaswarm:*), Write
---

# Update Bead Status

Update the status and metadata of an existing security investigation bead.

## Purpose

Maintain bead state throughout the investigation lifecycle. Enables:

- Work handoff between agents
- Progress tracking
- Dependency resolution
- Priority adjustments
- Resumption context preservation

## Arguments

When invoking this skill, provide:

- **bead_id**: Bead identifier (format: `bd-{hash}`)
- **status**: New status
  - `open` - Not yet started
  - `in_progress` - Currently being worked on
  - `complete` - Investigation finished
  - `blocked` - Waiting on dependency
- **notes**: (Optional) Additional context or findings

## Status Transitions

Valid transitions:
- `open` → `in_progress` (agent picks up work)
- `in_progress` → `complete` (investigation finished)
- `in_progress` → `blocked` (dependency found)
- `blocked` → `in_progress` (blocker resolved)
- `in_progress` → `open` (agent releases work)

## Execution

**Basic update:**
```bash
alphaswarm bead update $BEAD_ID --status $STATUS
```

**With notes:**
```bash
alphaswarm bead update $BEAD_ID --status $STATUS --notes "$NOTES"
```

**Mark as blocked:**
```bash
alphaswarm bead update $BEAD_ID \
  --status blocked \
  --blocked-by $OTHER_BEAD_ID \
  --notes "Waiting for access control pattern validation"
```

## Work State Preservation

When marking bead as `in_progress` or `blocked`, include work state for resumption:

```bash
alphaswarm bead update $BEAD_ID \
  --status in_progress \
  --agent-id $AGENT_ID \
  --work-state '{"checked_files": ["Vault.sol"], "next_step": "analyze_external_calls"}'
```

## Example

```bash
# Agent starts investigation
alphaswarm bead update bd-a3f5b912 --status in_progress

# Investigation blocked by dependency
alphaswarm bead update bd-a3f5b912 \
  --status blocked \
  --blocked-by bd-c7e89f23 \
  --notes "Need access control analysis before proceeding"

# Blocker resolved, resume work
alphaswarm bead update bd-a3f5b912 --status in_progress

# Investigation complete
alphaswarm bead update bd-a3f5b912 \
  --status complete \
  --notes "Confirmed reentrancy, exploit path documented"
```

## Output

Confirms update with current bead status.
