---
name: msd:docs-maintain
description: Maintain project documentation using three-layer progressive disclosure for LLM-optimized retrieval
argument-hint: "[action]"
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
---

# Docs Maintain Workflow

## Objective

Maintain project documentation with progressive disclosure architecture optimized for LLM agents.

## Scope For This Folder

These instructions should be applied to ` .planning/testing/ ` unless explicitly maintaining another docs directory.

If a command references `docs/`, substitute ` .planning/testing/ ` when maintaining this testing doc set.

## Actions

- `audit` to analyze existing docs structure and token costs.
- `index` to create or update DOC-INDEX.md with enhanced format.
- `split` to split oversized docs into granular files.
- `llms` to generate llms.txt and llms-full.txt only.
- No args to run the full maintenance cycle.

## Process

### Step 1 Detect Documentation Scope

```bash
ls -la docs/ 2>/dev/null || echo "No docs/ directory"
for f in docs/*.md; do
  lines=$(wc -l < "$f" 2>/dev/null || echo 0)
  tokens=$((lines * 12))
  echo "$f: ~$tokens tokens"
done
```

### Step 2 Apply Three-Layer Progressive Disclosure

Layer 1 Index
- Document ID and semantic title
- Category and priority indicators
- Token cost estimate
- Enables filtering before fetching

Layer 2 Context
- Summary and key decisions
- Cross-references to related docs
- When-to-load conditions
- Helps agent decide if full load needed

Layer 3 Detail
- Full implementation details
- Code examples and patterns
- Edge cases and troubleshooting
- Loaded only when explicitly needed

### Step 3 Generate Session Starters

```markdown
## Session Starters (Query → Doc)

| If you want to... | Load | ~Tokens |
|-------------------|------|---------|
| [user intent 1] | [doc-name.md] | [tokens] |
| [user intent 2] | [doc-name.md] | [tokens] |
```

### Step 4 Extract Questions Answered Per Doc

```markdown
| Document | Questions Answered |
|----------|-------------------|
| [doc.md] | [Question 1? Question 2? Question 3?] |
```

### Step 5 Extract Key Terms Per Doc

```markdown
| Document | Key Terms |
|----------|-----------|
| [doc.md] | term1, term2, term3, term4 |
```

### Step 6 Generate Section Index For Large Docs

```markdown
## Section Index (Partial Loading)

### [doc.md] (~X tokens)
| Section | Lines | Summary |
|---------|-------|---------|
| [Section Name] | [start-end] | [One-line summary] |
```

### Step 7 Apply Granularity Rules

Target token budgets and split triggers should be enforced.

### Step 8 Apply Semantic Title Compression

Use the formula `[Action] [Object] [Scope?]` and keep titles to 3-4 tokens.

### Step 9 Self-Contained Page Audit

Each doc must have one clear purpose and be self-contained.

### Step 10 Create Or Update DOC-INDEX.md

Follow the DOC-INDEX template from the objective guidance.

### Step 11 Generate llms.txt

Create `llms.txt` at project root using the provided template.

### Step 12 Generate llms-full.txt

Concatenate all docs into `llms-full.txt` with headers. Keep under 50K tokens.

### Step 13 Sync Cross-References

Update Markdown links, @-references, and doc tables after any file changes.

### Step 14 Maintain CLAUDE.md

Apply progressive disclosure to CLAUDE.md using the available docs-maintain tooling.
If a dedicated CLAUDE.md maintenance skill is not installed, update CLAUDE.md manually.

### Step 15 Report

Produce a summary report of actions, docs processed, and any flagged issues.

### Step 16 Validate Documentation In Practice

After changes, run real claude-code-controller validation of updated workflows:

- ` .planning/testing/workflows/workflow-docs-validation.md `

### Step 17 Update Scenario And Command Inventory

Ensure the scenario manifest and command inventory reflect new or changed workflows:

- ` .planning/testing/scenarios/SCENARIO-MANIFEST.yaml `
- ` .planning/testing/COMMAND-INVENTORY.md `

## Success Criteria

- All docs indexed with token estimates.
- Session starters cover most common questions.
- Each doc lists questions answered and key terms.
- Section index exists for large docs.
- Titles compressed to 3-4 tokens.
- No files exceed tier budgets.
- DOC-INDEX.md updated.
- llms.txt and llms-full.txt generated.
- Self-contained audit passed.
- Cross-references synced.
- CLAUDE.md under budget with progressive disclosure sections.
