# CLI Reference

Complete reference for AlphaSwarm.sol command-line interface.

## Overview

AlphaSwarm.sol provides the `alphaswarm` CLI as a **subordinate tooling surface**.

- Primary user workflow: Claude Code `/vrs-*` orchestration.
- CLI usage: developer debugging, CI pipelines, and explicit subagent tool calls.
- Artifact contract: CLI outputs must remain compatible with workflow evidence and marker contracts.

## Global Options

```bash
alphaswarm [OPTIONS] COMMAND [ARGS]
```

| Option | Description |
|--------|-------------|
| `--version`, `-v` | Show version and exit |
| `--help` | Show help and exit |
| `--log-level TEXT` | Override log level (DEBUG, INFO, WARNING, ERROR) |

## Core Commands

### build-kg

Build a knowledge graph from Solidity source files.

```bash
alphaswarm build-kg PATH [OPTIONS]
```

**Arguments:**

- `PATH` - Path to Solidity file or directory

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--output`, `-o` | `.vrs/graphs/graph.json` | Output path for graph |
| `--force`, `-f` | False | Overwrite existing graph |
| `--with-labels` | False | Include semantic labels |
| `--skip-slither` | False | Skip Slither analysis (use cached) |

**Examples:**

```bash
# Build from single file
alphaswarm build-kg Contract.sol

# Build from directory
alphaswarm build-kg contracts/

# Include semantic labels
alphaswarm build-kg contracts/ --with-labels

# Custom output location
alphaswarm build-kg contracts/ -o my-graph.json
```

---

### query

Query the knowledge graph using natural language, VQL, or patterns.

```bash
alphaswarm query QUERY [OPTIONS]
```

**Arguments:**

- `QUERY` - Query string (NL, VQL, pattern reference, or JSON)

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--graph`, `-g` | `.vrs/graphs/graph.json` | Path to graph |
| `--compact` | False | Reduced output for LLM consumption |
| `--explain` | False | Include match reasoning |
| `--limit`, `-n` | 50 | Maximum results |
| `--format` | `json` | Output format (json, human) |

**Query Formats:**

```bash
# Natural Language
alphaswarm query "public functions without access control"

# VQL (VKG Query Language)
alphaswarm query "FIND functions WHERE visibility = public AND NOT has_access_gate"

# Pattern reference
alphaswarm query "pattern:weak-access-control"

# Lens query
alphaswarm query "lens:Authority severity high"
```

---

### lens-report

Generate a comprehensive security report organized by lens.

```bash
alphaswarm lens-report [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--graph`, `-g` | `.vrs/graphs/graph.json` | Path to graph |
| `--format` | `json` | Output format (json, sarif, human) |
| `--output`, `-o` | stdout | Output file path |
| `--severity` | all | Minimum severity (low, medium, high, critical) |
| `--exit-code` | False | Exit with code 1 if findings exist |

**Examples:**

```bash
# Full report
alphaswarm lens-report

# SARIF for GitHub
alphaswarm lens-report --format sarif > results.sarif

# High severity only
alphaswarm lens-report --severity high

# CI/CD with exit code
alphaswarm lens-report --exit-code
```

---

## Label Commands

### label

Apply semantic labels to a knowledge graph.

```bash
alphaswarm label PATH [OPTIONS]
```

### label-info

Show statistics about a label overlay.

```bash
alphaswarm label-info PATH
```

### label-export

Export labels in different formats.

```bash
alphaswarm label-export OVERLAY_PATH [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `-f`, `--format` | yaml | Export format (yaml, json) |

---

## Context Commands

### context generate

Generate a protocol context pack from source code.

```bash
alphaswarm context generate PATH [OPTIONS]
```

### context show

Display context pack details.

```bash
alphaswarm context show CONTEXT_PATH
```

---

## Orchestration Commands

### orchestrate start

Start an audit pool.

```bash
alphaswarm orchestrate start POOL_ID --scope PATH [OPTIONS]
```

### orchestrate status

Check pool status.

```bash
alphaswarm orchestrate status POOL_ID
```

### orchestrate beads

List beads in a pool.

```bash
alphaswarm orchestrate beads POOL_ID
```

---

## Bead Commands

Manage investigation beads.

### bead create

Create a new investigation bead.

```bash
alphaswarm bead create [OPTIONS]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--vuln-class` | Yes | Vulnerability class |
| `--target` | Yes | Target function (Contract.function) |
| `--priority` | No | Priority (low, medium, high, critical) |

### bead list

List beads.

```bash
alphaswarm bead list [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--status` | all | Filter by status |
| `--format` | table | Output format (table, json) |

### bead show

Show bead details.

```bash
alphaswarm bead show BEAD_ID
```

### bead update

Update a bead.

```bash
alphaswarm bead update BEAD_ID [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--status` | New status (open, investigating, confirmed, rejected) |
| `--notes` | Add investigation notes |

---

## Tool Commands

Manage external tool integrations.

### tools status

Show installed tools and their status.

```bash
alphaswarm tools status
```

### tools run

Run tools on contracts.

```bash
alphaswarm tools run PATH [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--tools` | all | Comma-separated tool list (slither, aderyn, mythril) |

### tools dedupe

Deduplicate findings across tools.

```bash
alphaswarm tools dedupe FINDINGS_PATH [OPTIONS]
```

---

## VulnDocs Commands

Manage vulnerability documentation.

### vulndocs validate

Validate VulnDocs entries.

```bash
alphaswarm vulndocs validate PATH
```

### vulndocs scaffold

Create a new VulnDoc entry.

```bash
alphaswarm vulndocs scaffold ID --name NAME [OPTIONS]
```

### vulndocs list

List all VulnDocs entries.

```bash
alphaswarm vulndocs list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--status` | Filter by validation status |

---

## Init Commands

### init

Initialize VRS in a project.

```bash
alphaswarm init [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--skip-health-check` | False | Skip health check after init |

Creates:
- `.vrs/` directory structure
- `.vrs/AGENTS.md` agent interface
- `.vrs/tools.yaml` tool configuration
- Skills integration for Claude Code

### health-check

Verify VRS installation.

```bash
alphaswarm health-check [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--json` | False | Output as JSON |

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | API key for LLM features (Tier B, labels) |
| `OPENAI_API_KEY` | Alternative LLM provider |
| `VRS_LOG_LEVEL` | Default log level |
| `VRS_GRAPH_PATH` | Default graph path |

---

## Exit Codes (Contract)

All CLI commands MUST follow the same exit code semantics.

| Code | Meaning |
|------|---------|
| 0 | Success (no findings, or `--exit-code` not set) |
| 1 | Failure OR findings present when `--exit-code` is enabled |
| 2 | Invalid arguments / usage |
| 3 | Configuration or preflight error |

---

## Idempotency (Repeat-Run Behavior)

Commands below MUST be safe to re-run and emit a repeat-run detection marker in output.

| Command | Repeat-Run Behavior | Marker Requirement |
|---------|---------------------|--------------------|
| `alphaswarm init` | No destructive changes; reuses existing config and reprints status | Emit `REPEAT_RUN_DETECTED:init` |
| `alphaswarm build-kg` | Rebuilds graph deterministically or updates in-place; no duplicate artifacts | Emit `REPEAT_RUN_DETECTED:build-kg` |
| `alphaswarm tools run` | Re-runs tools deterministically; no duplicated tool artifacts | Emit `REPEAT_RUN_DETECTED:tools-run` |
| `alphaswarm health-check` | Safe read-only repeat | Emit `REPEAT_RUN_DETECTED:health-check` |

---

## Shell Completion

```bash
# Install completion (bash/zsh/fish)
alphaswarm --install-completion

# Manually for bash
eval "$(_ALPHASWARM_COMPLETE=bash_source alphaswarm)"

# Manually for zsh
eval "$(_ALPHASWARM_COMPLETE=zsh_source alphaswarm)"
```
