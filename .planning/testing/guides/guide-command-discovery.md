# Guide Command Discovery

**Purpose:** Resolve real commands before running workflows that require tool installs.

## When To Use

- Any workflow that references placeholders.
- Real environment validation.

## Required Output

- Completed command inventory file:
  ` .planning/testing/COMMAND-INVENTORY.md `

## Steps

1. Identify the missing command in the workflow.
2. Check ` .planning/TOOLING.md ` for canonical commands.
3. Verify the command in a claude-code-controller session.
4. Record the command and verification status in the inventory.

## Verification Rules

- Commands must be verified in a real claude-code-controller session.
- Include timestamps and the verifying transcript path.

