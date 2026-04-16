# Validation Rules Summary

This is a short, testing-only summary. The canonical source is ` .planning/testing/rules/canonical/VALIDATION-RULES.md `.

## Execution Mode

- Validation must run in LIVE mode.
- Real API calls and real durations are required.
- claude-code-agent-teams-based execution is mandatory for interactive tests.

## Ground Truth

- External sources only with documented provenance.
- No self-generated ground truth.
- Ground truth must be stored separately from test logic.

## Metrics

- Perfect metrics are suspicious and must be investigated.
- Error budgets are expected and must be documented.
- Variance across test cases is required.

## Infrastructure

- Use existing testing skills and claude-code-agent-teams-based execution.
- Transcripts must be captured and stored.
- Controller and subject must be isolated.

## Anti-Fabrication

- Minimum transcript length enforced.
- Tool invocation markers required.
- Duration thresholds enforced by operation type.
- Findings must include graph nodes, pattern IDs, and file:line locations.

## Artifact Dependency

- Plans must declare produced artifacts.
- Dependencies must be verified before execution.
- Wave gates block progression if unmet.

