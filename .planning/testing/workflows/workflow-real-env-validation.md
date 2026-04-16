# Workflow Real Environment Validation

**Purpose:** Validate the system in a production-like environment with real tool installs and full orchestration.

## When To Use

- Before any GA readiness claim.
- After major dependency or tooling changes.

## Preconditions

- claude-code-controller installed.
- Production-like environment with clean state.
- Explicit commands for all required tools are known and recorded.
- Command inventory is complete in ` .planning/testing/COMMAND-INVENTORY.md `.
 - Health-check command verified (see command inventory).
- Scenario manifest entry includes `requires_ground_truth: true` and a valid `ground_truth_ref`.

## Required Components

- Local tool installation in the target environment.
- Graph build using the CLI.
- Orchestrated audit using the testing framework.
- Evidence packs for every run.

## Tooling Requirements To Verify

These tools must be explicitly verified and installed before validation runs.

- claude-code-controller
- `claude` CLI
- AlphaSwarm CLI
- Claude Code skills (installed via `alphaswarm init`)

## Command Discovery

If any command is unknown, complete the command inventory before running this workflow:

- ` .planning/testing/guides/guide-command-discovery.md `
- ` .planning/testing/COMMAND-INVENTORY.md `

## Steps

1. Verify claude-code-controller and `claude` CLI availability.
2. Run `alphaswarm health-check` and resolve any failures.
3. Install required tools in the environment.
4. Run `alphaswarm init` to install Claude Code skills.
5. Build the knowledge graph using the CLI.
6. Generate protocol context pack (if applicable).
7. Fetch ground truth in the evaluator/controller context (not the Claude session).
8. Run a full audit in LIVE mode using the orchestration workflow.
9. Capture transcripts and reports.

## claude-code-controller Commands

```bash
claude-code-controller launch "zsh"
claude-code-controller send "cd /path/to/project" --pane=X
claude-code-controller wait_idle --pane=X
```

**Tool install and graph build commands must be verified before use.**
All shell commands must run **before** launching `claude`.

Use the command inventory for the real commands (shell phase before Claude Code):

```bash
# install required tools (see COMMAND-INVENTORY.md)
claude-code-controller send "uv run alphaswarm health-check --project . --json" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=10.0 --timeout=300
claude-code-controller send "uv run alphaswarm init ." --pane=X
claude-code-controller wait_idle --pane=X --idle-time=10.0 --timeout=300

# build graph
claude-code-controller send "uv run alphaswarm build-kg contracts/" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=10.0 --timeout=600

# generate protocol context pack (if applicable)
claude-code-controller send "uv run alphaswarm context generate . --docs ./docs --output .vrs/context/protocol-pack.yaml --force" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=10.0 --timeout=600
```

After CLI setup, launch Claude Code for the orchestration workflow (Claude-only phase):

```bash
claude-code-controller send "claude" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=10.0 --timeout=30
```

## Orchestrator Execution

Use the Claude Code orchestrator agent with skills to execute the audit workflow.

Example command placeholder:

```bash
/vrs-workflow-test /vrs-audit contracts/ --criteria e2e
```

Capture output and clean up:

```bash
claude-code-controller wait_idle --pane=X --idle-time=60.0 --timeout=1200
claude-code-controller capture --pane=X --output=.vrs/testing/runs/<run_id>/transcript.txt
claude-code-controller send "/exit" --pane=X
claude-code-controller kill --pane=X
```

## Required Evidence

- Transcript showing tool install and graph build.
- Report with duration and mode=live.
- Ground truth provenance if validation is performed.
- `ground_truth_ref` recorded in the scenario manifest and evidence pack for any validation claim.

## Failure Diagnosis

- Missing tool outputs indicates installation failure.
- Graph build errors indicate environment mismatch.
