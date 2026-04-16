---
name: vrs-orch-resume
description: Resume interrupted audit work from beads
slash_command: vrs:orch-resume
context: fork
disable-model-invocation: true
allowed-tools: Bash(alphaswarm:*), Read
---

# Resume Interrupted Work

Resume interrupted security audit work using bead state.

## Purpose

Security audits are often interrupted. This skill enables graceful resumption by:

- **State recovery**: Load work state from beads
- **Priority-based resumption**: Auto-resume highest priority work
- **User choice**: Present options for multiple interrupted tasks
- **Context restoration**: Rebuild investigation context from bead data

## When to Use

Invoke this skill when:
- Returning to an interrupted audit
- Starting a new session on existing audit
- Agent crash or timeout occurred
- User requested pause and resume

## Resumption Strategy

The skill follows this priority logic:

1. **Query for interrupted work**:
   - Find all `in_progress` beads
   - Find all `blocked` beads where blockers are now resolved

2. **Prioritize**:
   - Severity: critical > high > medium > low
   - Priority number: 0 = highest
   - Last modified: most recent first

3. **Auto-resume or present**:
   - If ONE highest-priority bead: auto-resume it
   - If MULTIPLE high-priority beads: present user with choices
   - If BLOCKED beads with unresolved blockers: show dependencies

## Execution

```bash
# Check for resumable work
alphaswarm orch resume
```

The command:
1. Lists all `in_progress` and unblocked beads
2. Shows bead details: ID, title, severity, last agent, progress state
3. Auto-resumes highest priority OR prompts for selection

## Work State Restoration

Each bead contains `work_state` field with resumption context:

```json
{
  "bead_id": "bd-a3f5b912",
  "agent_id": "vrs-attacker-001",
  "last_step": "analyzing_external_calls",
  "progress": {
    "checked_files": ["Vault.sol", "Token.sol"],
    "found_issues": ["unchecked_call_line_45"],
    "pending": ["validate_exploit_path"]
  },
  "context": {
    "graph_node": "Vault.withdrawAll",
    "pattern_match": "reentrancy-classic"
  }
}
```

This state is used to:
- Restore investigation context
- Avoid duplicate work
- Continue from last checkpoint

## Output Modes

### Auto-resume (single high-priority bead)
```
[Auto-resuming] bd-a3f5b912: Reentrancy in withdrawAll
Severity: high | Last agent: vrs-attacker-001
Progress: analyzing_external_calls (67% complete)

Restoring context...
Spawning investigator...
```

### User selection (multiple options)
```
Resumable work found:

1. [bd-a3f5b912] Reentrancy in withdrawAll
   Status: in_progress | Severity: high | Progress: 67%
   Last step: analyzing_external_calls

2. [bd-c7e89f23] Access control on mint
   Status: in_progress | Severity: critical | Progress: 40%
   Last step: checking_role_modifiers

3. [bd-e8b6c4d3] Weak randomness in lottery
   Status: blocked | Blocked by: bd-a3f5b912
   Blocker status: in_progress

Select bead to resume (1-3) or 'all' for sequential:
```

### Blocked work display
```
Blocked work:

[bd-e8b6c4d3] Weak randomness in lottery
Blocked by: bd-a3f5b912 (Reentrancy in withdrawAll)
Blocker status: in_progress
Action: Complete bd-a3f5b912 first
```

## Error Handling

- **No resumable work**: Reports "No interrupted work found"
- **Corrupted work state**: Warns and allows fresh start
- **Missing bead files**: Reports error with bead IDs
- **Concurrency limit**: Queues resume if workers already at limit

## Integration with Other Skills

Works with:
- `/vrs-bead-list` - Query current bead status
- `/vrs-bead-update` - Manually update bead before resume
- `/vrs-orch-spawn` - Spawns workers to continue investigation
