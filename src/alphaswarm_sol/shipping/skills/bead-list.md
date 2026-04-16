---
name: vrs-bead-list
description: List beads with optional filtering
slash_command: vrs:bead-list
disable-model-invocation: false
allowed-tools: Bash(alphaswarm:*)
---

# List Security Beads

List all security investigation beads with optional filtering by status and severity.

## Purpose

Query the bead index to:
- Check work queue status
- Find next investigation to pick up
- Review completed investigations
- Identify blocked work
- Prioritize high-severity issues

## Arguments

All arguments are optional:

- **status**: Filter by status (open | in_progress | complete | blocked)
- **severity**: Filter by severity (critical | high | medium | low)

Omit arguments to list all beads.

## Execution

**List all beads:**
```bash
alphaswarm bead list
```

**Filter by status:**
```bash
alphaswarm bead list --status in_progress
```

**Filter by severity:**
```bash
alphaswarm bead list --severity critical
```

**Combined filters:**
```bash
alphaswarm bead list --status open --severity high
```

## Output Format

Table with columns:
- **ID**: Bead identifier (bd-{hash})
- **Title**: Brief investigation description
- **Status**: Current status
- **Severity**: Issue severity
- **Priority**: Numeric priority (0 = highest)
- **Blocked By**: Dependencies (if blocked)

Example output:
```
ID          Title                              Status       Severity  Priority  Blocked By
----------  ---------------------------------  -----------  --------  --------  ----------
bd-a3f5b912 Reentrancy in withdrawAll         in_progress  high      0         -
bd-c7e89f23 Access control on mint            complete     critical  0         -
bd-d4f2e1a5 Unchecked transfer return         open         medium    1         -
bd-e8b6c4d3 Weak randomness in lottery        blocked      high      0         bd-a3f5b912
```

## Common Queries

**Find next work to pick up:**
```bash
alphaswarm bead list --status open
```

**Check what's currently being worked on:**
```bash
alphaswarm bead list --status in_progress
```

**Review critical issues:**
```bash
alphaswarm bead list --severity critical
```

**Find blocked work:**
```bash
alphaswarm bead list --status blocked
```

## Priority Ordering

Beads are ordered by:
1. Severity (critical > high > medium > low)
2. Priority number (0 = highest)
3. Creation time (oldest first)

Use this to determine which open bead to work on next.
