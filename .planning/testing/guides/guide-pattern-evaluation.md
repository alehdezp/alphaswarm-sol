# Guide Pattern Evaluation For Agentic Reasoning

**Purpose:** Ensure agents apply patterns, tools, and graph reasoning to detect complex vulnerabilities beyond simple matching.

## When To Use

- Any new or updated vulnerability pattern.
- Any Tier B/C scenario with complex logic or economic impact.
- Any time agent reasoning quality is questioned.

## Required Inputs

- Pattern documentation and examples.
- VQL query bundle for the pattern.
- Scenario family with base, safe, and counterfactual variants.
- Ground truth with provenance.
- Current repo Solidity code or a curated real-world sample.
- Template: `.planning/testing/templates/PATTERN-EVALUATION-TEMPLATE.md`.
- Template (paths): `.planning/testing/templates/PATH-EXPLORATION-TEMPLATE.md` for cross-contract or multi-function paths.

## Process (Required)

1. Load the pattern docs and examples.
2. Run VQL queries and capture graph outputs.
3. Execute the workflow in a demo claude-code-agent-teams session.
4. Require TaskCreate and TaskUpdate markers per candidate finding.
5. Require reasoning to cite graph nodes and context.
6. Evaluate false positives and false negatives.
7. Run a self-critique pass on reasoning and tool usage.

## Agent Compliance Checks

Agents must:
- Apply the pattern guidance as written.
- Use available tools (graph query, context, tools).
- Use graph-first reasoning, not keyword matching.
- Adapt reasoning to the specific Solidity code under review.
- Form related VQL queries when patterns are incomplete.

## Metrics And Evidence

Required measurements per pattern:
- False positive ratio.
- Effectiveness on the scenario family.
- Reasoning quality with graph references.
- Tool usage evidence (queries, context pack, tool output).

Evidence pack must include:
- Transcript.
- VQL query outputs.
- Context artifacts.
- Reasoning summary with graph node references.
- Completed pattern evaluation template.
- Path exploration template when a path is used to justify a finding.

## Self-Critique Loop (Required)

After the initial run:
- Identify missed reasoning steps.
- Identify tool usage gaps.
- Propose a single targeted improvement.
- Re-run and compare transcripts.

## Output Format Requirement

All agent outputs should include:
- Evidence references.
- Reasoning chain.
- Impact assessment.
- Confidence level.

## Failure Modes To Record

- Pattern not applied or misapplied.
- Missing graph queries or context usage.
- Findings without TaskCreate/TaskUpdate.
- Reasoning that ignores scenario-specific code.
- Overfitting to pattern text.
