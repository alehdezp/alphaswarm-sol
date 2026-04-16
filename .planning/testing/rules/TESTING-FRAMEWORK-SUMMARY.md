# Testing Framework Summary

This is a short, testing-only summary. The canonical source is ` .planning/testing/rules/canonical/TESTING-FRAMEWORK.md `.

## Architecture

- Controller uses claude-code-controller to drive subject in an isolated claude-code-agent-teams session.
- Subject executes real workflows and produces transcripts.
- Evaluator compares outputs to external ground truth and generates reports.
- Every run uses a dedicated demo claude-code-agent-teams session label (`vrs-demo-{workflow}-{timestamp}`).

## Mandatory claude-code-controller Usage

- All interactive testing must use claude-code-controller.
- No raw claude-code-agent-teams commands.
- Capture full transcripts for every run.
- Never reuse a demo session or pane across workflows.

## Required Components

- /vrs-self-test for orchestration
- /vrs-workflow-test for execution
- /vrs-evaluate-workflow for evaluation
- vrs-claude-controller for Claude automation
