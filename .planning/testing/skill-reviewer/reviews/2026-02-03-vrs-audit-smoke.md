# Skill Review Report Template

**Purpose:** Standardize skill review output and make it audit‑ready.

## Metadata

- Skill name: vrs-audit
- Skill path: .claude/skills/vrs-audit.md
- Registry entry: src/alphaswarm_sol/skills/registry.yaml (audit)
- Review date (YYYY‑MM‑DD): 2026-02-03
- Reviewer: claude-code-controller smoke run (Claude Code)
- Scope (self / external): self

## Summary

- Overall assessment: Well-structured multi-stage audit skill with strong documentation, but frontmatter and description format issues reduce discoverability.
- Key strengths: Clear 7-stage pipeline, strong usage examples, visual documentation.
- Key risks: Non-standard frontmatter key and missing trigger conditions.
- Recommended actions: Fix frontmatter key, update description to third-person with triggers, check tool name typo noted in report.

## Checklist Results

| Category | Status | Notes |
|---|---|---|
| Frontmatter | needs-fix | Uses `skill:` instead of `name:` per report.
| Description (third‑person + triggers) | needs-fix | Third-person and trigger clause missing.
| Instructions (imperative + concise) | ok | Structured stages and steps.
| Progressive disclosure | ok | Staged structure and examples.
| Resources (scripts/references) | ok | No missing references flagged in smoke run.
| Privacy + paths | ok | No issues flagged in smoke run.
| Workflow pattern | ok | Clear 7-stage pipeline.
| Error handling | unknown | Not evaluated in smoke run.

## Issues And Fixes

- Issue: Non-standard frontmatter key (`skill:` instead of `name:`)
- Impact: Skill discovery and compliance risk.
- Recommended fix: Use `name: vrs-audit` in frontmatter.
- Evidence (file + line): `.claude/skills/vrs-audit.md` (smoke transcript)

- Issue: Description not third-person and missing trigger clause
- Impact: Weak delegation signal and auto-selection.
- Recommended fix: Update description to third-person and add “Use when...” clause.
- Evidence (file + line): `.claude/skills/vrs-audit.md` (smoke transcript)

- Issue: Tool name typo noted in report (`mcp__exa_search__web_search_exa`)
- Impact: Tool invocation may fail.
- Recommended fix: Replace with `mcp__exa-search__web_search_exa`.
- Evidence (file + line): `.claude/skills/vrs-audit.md` line ~165 (per smoke report)

## Additive Improvements

- Add trigger conditions to description.
- Fix tool name typo if present.

## Validation

- Automated checks executed: None (smoke test only)
- Manual checks executed: Smoke review via Claude Code
- Validation output summary: `.vrs/testing/runs/2026-02-03-skill-reviewer-smoke/transcript.txt`

## Links

- Checklist: `references/evaluation_checklist.md`
- PR template (if external): `references/pr_template.md`
- Marketplace template: `references/marketplace_template.json`

## Storage

Save reports in `.planning/testing/skill-reviewer/reviews/` and link them in the phase super report.
