# Workflow Knowledge Graph Build And Query

**Purpose:** Validate KG construction, query correctness, and graph-first reasoning order.

## When To Use

- Any change to builder, KG schema, or graph query logic.

## Preconditions

- claude-code-controller installed.
- A target contract or corpus path.

## Steps

1. Build the KG from contracts.
2. Run a graph query that returns known nodes.
3. If protocol context is required, generate or load it (CLI).
4. If economic context is required, run the economic context skill (Claude Code).
5. Validate the query output against the Graph Interface contract (Claude Code).
6. Capture transcripts and evidence.

## claude-code-controller Commands

**Shell phase (pre-Claude only):** run all CLI commands **before** launching `claude`.

```bash
claude-code-controller launch "zsh"
claude-code-controller send "cd /path/to/project" --pane=X
claude-code-controller wait_idle --pane=X
claude-code-controller send "uv run alphaswarm build-kg contracts/" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=10.0 --timeout=300
claude-code-controller send "uv run alphaswarm query \"functions without access control\" --output .vrs/graphs/graph-query.json" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=10.0 --timeout=120
claude-code-controller send "uv run alphaswarm context generate . --docs ./docs --output .vrs/context/protocol-pack.yaml --force" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=10.0 --timeout=300
```

**Claude phase (post-launch only):** only slash commands and skill prompts.

```bash
# Launch Claude Code only for skill-driven steps
claude-code-controller send "claude" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=10.0 --timeout=30
# If economic context is enabled, run the appropriate skill command
claude-code-controller send "/vrs-economic-context" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=15.0 --timeout=300
claude-code-controller send "/vrs-graph-contract-validate .vrs/graphs/graph-query.json --strict" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=15.0 --timeout=300
claude-code-controller capture --pane=X --output=.vrs/testing/runs/<run_id>/transcript.txt
claude-code-controller send "/exit" --pane=X
claude-code-controller kill --pane=X
```

## Required Evidence

- Transcript showing KG build and query outputs.
- Findings that reference graph node IDs.
- If context packs are used, transcript must show context load markers.

## Failure Diagnosis

- Missing graph node IDs indicates reasoning order violation.
- Query errors indicate builder or schema failure.
