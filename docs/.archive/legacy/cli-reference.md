# CLI Reference

Complete reference for all AlphaSwarm.sol command-line commands.

## Global Options

```bash
alphaswarm [OPTIONS] COMMAND [ARGS]
```

| Option | Description |
|--------|-------------|
| `--log-level TEXT` | Override log level (DEBUG, INFO, WARNING, ERROR) |
| `--help` | Show help and exit |
| `--install-completion` | Install shell completion |
| `--show-completion` | Show completion script |

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
| `--output, -o` | `.vrs/graphs/graph.json` | Output path for graph |
| `--force, -f` | False | Overwrite existing graph |
| `--skip-slither` | False | Skip Slither analysis (use cached) |

**Examples:**
```bash
# Build from single file
alphaswarm build-kg Contract.sol

# Build from directory
alphaswarm build-kg contracts/

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
- `QUERY` - Query string (NL, VQL, pattern, or JSON)

**Options:**
| Option | Default | Description |
|--------|---------|-------------|
| `--graph, -g` | `.vrs/graphs/graph.json` | Path to graph |
| `--compact` | False | Reduced output for LLM |
| `--explain` | False | Include match reasoning |
| `--show-intent` | False | Show parsed query intent |
| `--limit, -n` | 50 | Maximum results |
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

# JSON query
alphaswarm query '{"query_kind": "logic", "node_types": ["Function"], "match": {...}}'
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
| `--graph, -g` | `.vrs/graphs/graph.json` | Path to graph |
| `--format` | `json` | Output format (json, sarif, human) |
| `--output, -o` | stdout | Output file path |
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

### suggest

Suggest high-value queries based on contract analysis.

```bash
alphaswarm suggest [OPTIONS]
```

**Options:**
| Option | Default | Description |
|--------|---------|-------------|
| `--graph, -g` | `.vrs/graphs/graph.json` | Path to graph |
| `--contract` | all | Filter by contract name |
| `--limit, -n` | 10 | Maximum suggestions |

---

### schema

Export schema snapshot for autocomplete and validation.

```bash
alphaswarm schema [OPTIONS]
```

**Options:**
| Option | Default | Description |
|--------|---------|-------------|
| `--graph, -g` | `.vrs/graphs/graph.json` | Path to graph |
| `--output, -o` | stdout | Output file path |

---

## Management Commands

### validate

Validate `.vrs` directory integrity.

```bash
alphaswarm validate [OPTIONS]
```

**Options:**
| Option | Default | Description |
|--------|---------|-------------|
| `--path` | `.vrs` | Path to BSKG directory |
| `--fix` | False | Attempt to fix issues |

---

### reset

Reset BSKG state (destructive).

```bash
alphaswarm reset [OPTIONS]
```

**Options:**
| Option | Default | Description |
|--------|---------|-------------|
| `--force, -f` | False | Skip confirmation |
| `--keep-config` | False | Keep configuration files |

---

## Beads Commands

Manage vulnerability investigation beads.

### beads list

```bash
alphaswarm beads list [OPTIONS]
```

**Options:**
| Option | Default | Description |
|--------|---------|-------------|
| `--status` | all | Filter by status (open, investigating, complete) |
| `--priority` | all | Filter by priority |

### beads create

```bash
alphaswarm beads create [OPTIONS]
```

**Options:**
| Option | Default | Description |
|--------|---------|-------------|
| `--finding` | required | Finding ID to investigate |
| `--priority` | medium | Priority (low, medium, high, critical) |
| `--assignee` | none | Assign to user |

### beads complete

```bash
alphaswarm beads complete BEAD_ID [OPTIONS]
```

**Options:**
| Option | Default | Description |
|--------|---------|-------------|
| `--verdict` | required | Verdict (confirmed, false_positive, needs_review) |
| `--notes` | none | Investigation notes |

---

## Findings Commands

Manage vulnerability findings.

### findings list

```bash
alphaswarm findings list [OPTIONS]
```

**Options:**
| Option | Default | Description |
|--------|---------|-------------|
| `--severity` | all | Filter by severity |
| `--lens` | all | Filter by lens |
| `--status` | all | Filter by status |

### findings export

```bash
alphaswarm findings export [OPTIONS]
```

**Options:**
| Option | Default | Description |
|--------|---------|-------------|
| `--format` | json | Format (json, sarif, csv) |
| `--output, -o` | stdout | Output file |

---

## Learn Commands

Conservative learning system for pattern adjustment.

### learn record-fp

Record a false positive for learning.

```bash
alphaswarm learn record-fp [OPTIONS]
```

**Options:**
| Option | Default | Description |
|--------|---------|-------------|
| `--finding-id` | required | Finding ID |
| `--reason` | required | Reason for false positive |

### learn show

Show learned adjustments.

```bash
alphaswarm learn show [OPTIONS]
```

### learn rollback

Rollback learning adjustments.

```bash
alphaswarm learn rollback [OPTIONS]
```

**Options:**
| Option | Default | Description |
|--------|---------|-------------|
| `--to-version` | previous | Target version |

---

## Metrics Commands

Performance and detection metrics.

### metrics show

```bash
alphaswarm metrics show [OPTIONS]
```

**Options:**
| Option | Default | Description |
|--------|---------|-------------|
| `--period` | 24h | Time period |
| `--format` | human | Format (human, json) |

### metrics export

```bash
alphaswarm metrics export [OPTIONS]
```

---

## Novel Commands

Advanced analysis solutions.

### novel info

Show information about available novel solutions.

```bash
alphaswarm novel info
```

### novel similar find

Find semantically similar functions.

```bash
alphaswarm novel similar find [OPTIONS]
```

**Options:**
| Option | Default | Description |
|--------|---------|-------------|
| `--graph, -g` | required | Path to graph |
| `--function` | required | Function to find similar to |
| `--threshold` | 0.7 | Minimum similarity (0-1) |

### novel similar clones

Detect code clones.

```bash
alphaswarm novel similar clones [OPTIONS]
```

**Options:**
| Option | Default | Description |
|--------|---------|-------------|
| `--graph, -g` | required | Path to graph |
| `--threshold` | 0.9 | Clone detection threshold |

### novel evolve pattern

Evolve patterns via genetic algorithm.

```bash
alphaswarm novel evolve pattern PATTERN_FILE [OPTIONS]
```

**Options:**
| Option | Default | Description |
|--------|---------|-------------|
| `--generations` | 10 | Number of generations |
| `--population` | 20 | Population size |
| `--output, -o` | stdout | Output evolved pattern |

### novel evolve status

Check evolution status.

```bash
alphaswarm novel evolve status
```

### novel invariants discover

Discover formal invariants.

```bash
alphaswarm novel invariants discover [OPTIONS]
```

**Options:**
| Option | Default | Description |
|--------|---------|-------------|
| `--graph, -g` | required | Path to graph |
| `--contract` | all | Filter by contract |
| `--format` | json | Output format (json, solidity) |

### novel invariants verify

Verify an invariant holds.

```bash
alphaswarm novel invariants verify [OPTIONS]
```

**Options:**
| Option | Default | Description |
|--------|---------|-------------|
| `--graph, -g` | required | Path to graph |
| `--invariant` | required | Invariant expression |

### novel invariants generate

Generate Solidity assertions.

```bash
alphaswarm novel invariants generate [OPTIONS]
```

### novel adversarial mutate

Generate mutated contracts for testing.

```bash
alphaswarm novel adversarial mutate CONTRACT [OPTIONS]
```

**Options:**
| Option | Default | Description |
|--------|---------|-------------|
| `--mutations` | 10 | Number of mutations |
| `--output-dir` | ./mutants | Output directory |
| `--operators` | all | Mutation operators to use |

### novel adversarial metamorphic

Test pattern rename-invariance.

```bash
alphaswarm novel adversarial metamorphic CONTRACT [OPTIONS]
```

**Options:**
| Option | Default | Description |
|--------|---------|-------------|
| `--iterations` | 5 | Number of rename iterations |
| `--pattern` | test-all | Pattern ID to test |

### novel adversarial rename

Rename identifiers in contract.

```bash
alphaswarm novel adversarial rename CONTRACT [OPTIONS]
```

**Options:**
| Option | Default | Description |
|--------|---------|-------------|
| `--strategy` | semantic | Renaming strategy |

---

## Scaffold Commands

Test scaffold generation.

### scaffold generate

```bash
alphaswarm scaffold generate [OPTIONS]
```

**Options:**
| Option | Default | Description |
|--------|---------|-------------|
| `--finding` | required | Finding ID |
| `--framework` | foundry | Test framework (foundry, hardhat) |
| `--output, -o` | stdout | Output file |

---

## Benchmark Commands

Benchmark detection validation.

### benchmark run

```bash
alphaswarm benchmark run [OPTIONS]
```

**Options:**
| Option | Default | Description |
|--------|---------|-------------|
| `--suite` | dvd | Benchmark suite (dvd, smartbugs) |
| `--output, -o` | stdout | Results file |

### benchmark compare

```bash
alphaswarm benchmark compare [OPTIONS]
```

**Options:**
| Option | Default | Description |
|--------|---------|-------------|
| `--baseline` | main | Baseline to compare against |

---

## Doctor Commands

Diagnose BSKG issues.

### doctor check

```bash
alphaswarm doctor check [OPTIONS]
```

**Options:**
| Option | Default | Description |
|--------|---------|-------------|
| `--verbose` | False | Detailed output |

---

## Repair Commands

Repair BSKG issues.

### repair run

```bash
alphaswarm repair run [OPTIONS]
```

**Options:**
| Option | Default | Description |
|--------|---------|-------------|
| `--dry-run` | False | Show what would be fixed |

---

## Tools Commands

Tool management.

### tools list

```bash
alphaswarm tools list
```

### tools check

```bash
alphaswarm tools check [OPTIONS]
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error / Findings found (with --exit-code) |
| 2 | Invalid arguments |
| 3 | Configuration error |

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `VKG_LOG_LEVEL` | Default log level |
| `VKG_GRAPH_PATH` | Default graph path |
| `VKG_CONFIG_PATH` | Configuration file path |
| `ANTHROPIC_API_KEY` | For Tier B LLM features |
| `OPENAI_API_KEY` | Alternative LLM provider |

---

## Shell Completion

```bash
# Install completion (bash/zsh/fish)
alphaswarm --install-completion

# Manually for bash
eval "$(_TRUE_VKG_COMPLETE=bash_source alphaswarm)"

# Manually for zsh
eval "$(_TRUE_VKG_COMPLETE=zsh_source alphaswarm)"
```
