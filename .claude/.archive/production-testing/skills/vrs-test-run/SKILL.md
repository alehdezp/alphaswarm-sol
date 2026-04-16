---
name: vrs-test-run
description: Execute real-world test scenarios using Agent Teams in jj workspaces
---

# /vrs-test-run — Real-World Test Execution

## Purpose

Run one or more test scenarios from the testing framework registry. Each scenario spawns an Agent Team in an isolated Jujutsu workspace where agents execute real workflows without knowing they are being tested.

## Usage

```
/vrs-test-run <scenario-id>           # Run one scenario
/vrs-test-run --tag <tag>             # Run all scenarios with tag
/vrs-test-run --category <category>   # Run all in category
/vrs-test-run --all                   # Run full regression suite
```

## Arguments

- `scenario-id`: Specific scenario ID from the registry (e.g., `ct-access-control-001`)
- `--tag <tag>`: Filter by tag (e.g., `smoke`, `pattern`, `e2e`, `CT`, `BT`)
- `--category <category>`: Filter by category (e.g., `pattern-detection`, `e2e-pipeline`)
- `--all`: Run everything in the registry

## Process

### Step 1: Load Scenario(s)

Read the scenario registry at `.vrs/testing/scenarios/registry.yaml`.
Parse the matching scenario YAML file(s) from `.vrs/testing/scenarios/<category>/<id>.yaml`.

If no scenarios match, report error and list available scenarios.

### Step 2: For Each Scenario — Set Up Workspace

```bash
# Create isolated jj workspace
jj workspace add test-<scenario-id>-<timestamp> --revision main

# Navigate to workspace
cd <workspace-path>
```

### Step 3: Set Up Test Project

Use the `test-scenario-builder` agent (via Task tool) to set up the test project:
- Copy contracts specified in the scenario
- Install any required skills/configs
- Set up the project to look like a real user's project
- The project must NOT contain any indication that this is a test

### Step 4: Spawn Agent Team

Create an Agent Team using `TeamCreate`:

```
Team name: test-<scenario-id>-<timestamp>
Members:
  - worker: Executes the scenario prompt (general-purpose agent)
  - observer: test-observer agent — watches and validates
```

**Worker agent receives ONLY the scenario prompt** — the same thing a real user would type. No hints about expected behavior, no test context.

**Observer agent receives:**
- The scenario expectations (what to look for)
- The failure conditions (what would fail the test)
- Instructions to validate using reasoning, not assertions

### Step 5: Execute

- Send the scenario prompt to the worker agent via `SendMessage`
- Worker executes naturally — builds graphs, runs patterns, spawns subagents, etc.
- Observer monitors progress via task list and workspace artifacts
- Wait for worker to complete or timeout

### Step 6: Validate

Observer agent produces a validation report:
- What the worker did (actions taken, tools used, agents spawned)
- What the worker found (findings, evidence, reports)
- Evaluation against expectations (reasoned pass/fail for each)
- Overall verdict: PASS / FAIL / PARTIAL with reasoning
- Unexpected behaviors (good or bad)

### Step 7: Capture Results

Save results to `.vrs/testing/results/<run-id>/`:
- `scenario.yaml` — The scenario that was run
- `validation.md` — Observer's validation report
- `artifacts/` — Any files the worker created (reports, beads, etc.)
- `summary.json` — Machine-readable result (pass/fail, timestamp, scenario-id)

### Step 8: Clean Up

```bash
# Rollback the workspace
jj workspace forget test-<scenario-id>-<timestamp>
```

### Step 9: Report

Display results to the user:

```
## Test Results: <scenario-name>

**Verdict:** PASS / FAIL / PARTIAL
**Scenario:** <id> (<category>)
**Duration:** <time>

### What Happened
- [action 1]
- [action 2]
- ...

### Expectations
- [expectation 1]: PASS — [reasoning]
- [expectation 2]: FAIL — [reasoning]

### Observer Notes
[Any unexpected behaviors or recommendations]

### Results saved to: .vrs/testing/results/<run-id>/
```

## Error Handling

| Error | Recovery |
|-------|----------|
| Scenario not found | List available scenarios from registry |
| jj workspace creation fails | Check jj status, ensure main branch exists |
| Worker agent crashes | Capture error, report FAIL with error context |
| Worker agent times out | Capture partial output, report PARTIAL |
| Observer fails to validate | Report results without validation, flag for manual review |

## Exit Criteria

- All requested scenarios have been executed
- Results saved to `.vrs/testing/results/`
- Registry updated with latest run results
- Workspaces cleaned up
