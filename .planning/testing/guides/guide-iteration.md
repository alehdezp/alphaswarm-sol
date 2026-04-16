# Guide Iteration Protocol

**Purpose:** Provide a deterministic failure taxonomy and remediation steps for validation runs.

## Iteration Loop

1. Record the failure (transcript + report.json + evidence pack).
2. Classify the failure using the taxonomy below.
3. Run diagnostics to confirm the root cause.
4. Apply remediation steps.
5. Re-run and compare against the prior failure.

## Failure Taxonomy (Required)

### missing-task-lifecycle
- **Trigger:** `TaskCreate(...)` or `TaskUpdate(...)` missing from transcripts or evidence pack.
- **Diagnostics:**
  - Search transcript for `TaskCreate(` and `TaskUpdate(` markers.
  - Verify each candidate pattern has a TaskCreate entry.
  - Verify each task has a TaskUpdate with verdict + evidence.
- **Remediation:**
  - Ensure task creation occurs per candidate before any findings.
  - Enforce TaskUpdate generation before report output.
  - Re-run with hook gates enabled (Stop/SubagentStop).

### missing-orchestration-markers
- **Trigger:** One or more stage markers are missing (preflight, graph build, context, tools, detection, report, progress).
- **Diagnostics:**
  - Compare transcript against required marker list in workflow docs.
  - Check for skipped stages or early termination.
- **Remediation:**
  - Re-run with workflow hooks enabled.
  - Ensure each stage emits its marker before proceeding.
  - If context or tools are disabled, emit the correct bypass marker instead of skipping.

### graph-first-violation
- **Trigger:** Conclusions appear before BSKG/VQL query markers.
- **Diagnostics:**
  - Identify the first conclusion line and the first query marker line.
  - Verify query markers exist and precede conclusions.
- **Remediation:**
  - Insert required queries before reasoning steps.
  - Enforce graph-first checks in prompts and validation hooks.
  - Re-run and verify `graph_first.verified = true` in `report.json`.

### anti-fabrication-threshold-failure
- **Trigger:** Transcript line count, duration, or marker variance falls below thresholds.
- **Diagnostics:**
  - Confirm min line count and duration for the workflow type.
  - Check for missing boundary markers from `.planning/testing/MARKER-REGISTRY.yaml`
    (canonical: `[ALPHASWARM-START]`, `[ALPHASWARM-END]`).
- **Remediation:**
  - Re-run in claude-code-agent-teams with real execution (no mocks/simulated runs).
  - Ensure boundary markers and required proof tokens are emitted.
  - Increase run duration by waiting for full completion.

### output-mismatch
- **Trigger:** Output does not match workflow contract expectations (missing stages, wrong order, or wrong artifacts).
- **Diagnostics:**
  - Compare transcript to the workflow contract’s required markers and stage order.
  - Check evidence pack for missing required artifacts (report.json, proofs, manifest.json).
- **Remediation:**
  - Update the workflow skill/prompt to emit required markers and artifacts.
  - Re-run with hooks enabled to block missing outputs.

### environment-drift
- **Trigger:** Results differ across runs with identical inputs, or environment changes are detected.
- **Diagnostics:**
  - Compare `environment.json` and manifest fields between runs.
  - Check for differences in tool versions, settings, or git commit.
- **Remediation:**
  - Pin tool versions or record overrides in settings.
  - Re-run in a clean jj workspace with a fresh demo session label.
