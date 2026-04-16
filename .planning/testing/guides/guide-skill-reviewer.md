# Skill Reviewer Guide

**Purpose:** Require a skill review pass in every phase for every skill (not subagents).

## When To Use

- Before any phase plan is executed.
- When a skill is added or modified.
- When reviewing the quality of shipped or dev-only skills.
- When discussing skill changes in future phases (always load this guide).

## Required Inputs

- `src/alphaswarm_sol/skills/registry.yaml`
- `.planning/testing/skill-reviewer/SKILL.md`
- `.planning/testing/skill-reviewer/references/evaluation_checklist.md`
- `.planning/testing/skill-reviewer/references/pr_template.md`
- `.planning/testing/skill-reviewer/references/marketplace_template.json`
- `.planning/testing/skill-reviewer/references/review_report_template.md`

## Rule

Every phase must run the skill reviewer for **every skill** in the registry.
This is not optional and is separate from subagent review.

## Origin

This reviewer is derived from the DVWare Iron skill meta approach.

## Workflow (Per Skill)

1. Load the skill file and read its frontmatter.
2. Run the evaluation checklist.
3. Record findings and improvements.
4. If external, follow PR template tone and structure.

## Output (Required)

- Store a review report in `.planning/testing/skill-reviewer/reviews/` using
  `references/review_report_template.md`.
- Link the report in the phase super report.

## Evidence

- Record review results in the phase super report.
- Link any updated docs or follow-up tasks.

## Agent Improvement (Indirect)

For subagents, apply the same quality criteria, but do not run this skill directly.
Use the agent catalog (`src/alphaswarm_sol/agents/catalog.yaml`) and the rules in
`docs/reference/agents.md` for analogous review.
