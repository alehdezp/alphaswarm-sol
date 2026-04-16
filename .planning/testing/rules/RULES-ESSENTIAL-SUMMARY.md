# Rules Essential Summary

This is a short, testing-only summary. The canonical source is ` .planning/testing/rules/canonical/RULES-ESSENTIAL.md `.

## Auto-Invoke Triggers

Load rules immediately when you see any of these patterns.

- skill, SKILL.md, /vrs-*, /gsd:*
- subagent, agent, .claude/agents/
- orchestrat, workflow, multi-agent
- validation, e2e, ga-validation
- claude-code-agent-teams, interactive, CLI

## Mandatory claude-code-controller Testing

- Every skill, agent, and workflow test must use claude-code-controller.
- No subprocess shortcuts and no simulations.
- A full transcript is required for every run.

## Validation Mode

- LIVE mode only for validation and E2E.
- External ground truth only.
- No circular validation.

## Anti-Fabrication

- Minimum transcript lines required by test type.
- Tool invocation markers required.
- Duration must be realistic for the operation type.
- Perfect metrics require investigation and must be flagged.

