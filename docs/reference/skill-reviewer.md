# Skill Reviewer (Best Practices Gate)

**Purpose:** Define the skill review gate required in every phase for every skill.

## When To Load

- When creating or modifying skills.
- When preparing a phase plan.
- When reviewing shipped skills for quality.

## Canonical Assets

The full reviewer package lives in:

- `.planning/testing/skill-reviewer/SKILL.md`
- `.planning/testing/skill-reviewer/references/evaluation_checklist.md`
- `.planning/testing/skill-reviewer/references/pr_template.md`
- `.planning/testing/skill-reviewer/references/marketplace_template.json`
- `.planning/testing/skill-reviewer/references/review_report_template.md`

## Rule

Every phase must run the skill reviewer for **every skill** in the registry
(`src/alphaswarm_sol/skills/registry.yaml`). This is required before execution.

## Output Requirement

Store review reports in `.planning/testing/skill-reviewer/reviews/` using
`references/review_report_template.md` and link them in the phase super report.

## Origin

This reviewer is derived from the DVWare Iron skill meta approach.

## Agents (Indirect)

Agents are not reviewed with the skill reviewer directly, but use the same quality criteria
for prompt clarity, output contracts, and error handling.

## Related Docs

- `docs/guides/skills-basics.md`
- `docs/reference/agents.md`
- `.planning/testing/guides/guide-skill-reviewer.md`
