# Documentation Index

> AlphaSwarm.sol docs with LLM-optimized retrieval | Last updated: 2026-02-03

## Session Starters

| If you want to... | Load |
|---|---|
| See the doc map | `docs/index.md` |
| Understand philosophy | `docs/PHILOSOPHY.md` |
| Install and run first audit (Claude Code orchestrator) | `docs/getting-started/installation.md`, `docs/getting-started/first-audit.md` |
| See workflow contracts | `docs/workflows/README.md` |
| Understand testing | `docs/reference/testing-framework.md` |
| Learn patterns | `docs/guides/patterns-basics.md` |
| Define skills | `docs/guides/skills-basics.md` |
| Use VulnDocs | `docs/guides/vulndocs-basics.md` |
| Understand tools | `docs/reference/tools-overview.md` |

## Tier 1 - Always Load

| Document | Purpose |
|---|---|
| `docs/index.md` | Doc map and routing |
| `docs/PHILOSOPHY.md` | Core philosophy, 9-stage pipeline |
| `docs/workflows/README.md` | Workflow contracts |
| `docs/reference/testing-framework.md` | Testing contract |

## Tier 2 - On Demand

### Getting Started
- `docs/getting-started/installation.md` - Install and verify
- `docs/getting-started/first-audit.md` - Run first audit

### Guides
- `docs/guides/patterns-basics.md` - Pattern fundamentals
- `docs/guides/patterns-advanced.md` - Tier A+B, PCP v2
- `docs/guides/skills-basics.md` - Skills fundamentals
- `docs/guides/skills-authoring.md` - Schema v2, authoring
- `docs/guides/testing-basics.md` - Pattern testing
- `docs/guides/testing-advanced.md` - Workflow harness and advanced validation
- `docs/guides/vulndocs-basics.md` - VulnDocs fundamentals
- `docs/guides/vulndocs-authoring.md` - Validation pipeline
- `docs/guides/beads.md` - Bead lifecycle
- `docs/guides/queries.md` - Graph queries

### Reference
- `docs/reference/agents.md` - 24-agent system
- `docs/reference/cli.md` - CLI tool calls (subagent/dev)
- `docs/claude-code-architecture.md` - Claude Code workflow architecture
- `docs/migrations/claude-code-workflow-migration.md` - Breaking changes and migration steps
- `docs/reference/tools-overview.md` - Tool architecture
- `docs/reference/tools-adapters.md` - Detector mappings
- `docs/reference/skill-schema-v2.md` - Skill schema
- `docs/reference/graph-first-template.md` - Evidence template
- `docs/reference/operations.md` - Semantic operations
- `docs/reference/properties.md` - Properties reference
- `docs/reference/vql-library.md` - VQL Query Library (8 core queries)

### Workflows
- `docs/workflows/workflow-audit.md` - Audit entrypoint
- `docs/workflows/workflow-graph.md` - Graph build
- `docs/workflows/workflow-verify.md` - Verification
- `docs/workflows/workflow-tasks.md` - Task orchestration

## By Topic

| Topic | Basic | Advanced |
|-------|-------|----------|
| Patterns | `patterns-basics.md` | `patterns-advanced.md` |
| Skills | `skills-basics.md` | `skills-authoring.md` |
| Testing | `testing-basics.md` | `testing-advanced.md` |
| VulnDocs | `vulndocs-basics.md` | `vulndocs-authoring.md` |
| Tools | `tools-overview.md` | `tools-adapters.md` |

## Quick Commands

```bash
# Core docs
cat docs/index.md
cat docs/PHILOSOPHY.md
cat docs/workflows/README.md

# Guides
cat docs/guides/patterns-basics.md
cat docs/guides/skills-basics.md
```

## Archive

Archive docs indexed in `docs/.archive/index.md`.
