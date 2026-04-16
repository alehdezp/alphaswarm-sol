---
name: vrs-bead-create
description: Create a new security investigation bead
slash_command: vrs:bead-create
context: fork
disable-model-invocation: false
allowed-tools: Bash(alphaswarm:*), Write
---

# Create Security Bead

Create a new bead for security investigation work.

## Purpose

Beads are AI-optimized task tracking units following the steveyegge pattern. Use this skill to create beads for security-related Solidity investigation work. Beads enable:

- Work resumption across agent sessions
- Task dependency tracking
- Priority-based work scheduling
- Progress visibility

## When to Use

Create beads ONLY for:
- Security vulnerability investigations
- Exploit path construction
- Mitigation verification
- Pattern validation
- Audit findings requiring deep analysis

Do NOT create beads for:
- Simple queries
- Documentation tasks
- Non-security work

## Arguments

When invoking this skill, provide:

- **title**: Brief description of investigation (e.g., "Reentrancy in withdrawAll function")
- **severity**: critical | high | medium | low
- **pattern_id**: (Optional) Pattern that triggered this investigation
- **location**: File and function information (e.g., "Vault.sol:withdrawAll")

## Execution

```bash
alphaswarm bead create "$TITLE" \
  --severity $SEVERITY \
  --pattern "$PATTERN_ID" \
  --location "$FILE:$FUNCTION"
```

## Output

Returns bead ID in format `bd-{hash}` for tracking and reference.

## Example

```bash
alphaswarm bead create "Unchecked external call in transfer" \
  --severity high \
  --pattern "unchecked-lowlevel" \
  --location "Token.sol:transfer"
```

Returns: `bd-a3f5b912`

## Storage

Beads are stored in `.beads/` directory:
- `.beads/index.jsonl` - Bead index with status
- `.beads/bd-{hash}.jsonl` - Individual bead files

Beads are git-trackable but users choose whether to commit them.
