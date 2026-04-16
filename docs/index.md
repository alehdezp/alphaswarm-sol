# AlphaSwarm.sol Documentation

> Multi-agent Solidity security framework | Milestone 6.0: From Theory to Reality

---

## Quick Stats (Honest — v6.0)

| Metric | Value | Notes |
|--------|-------|-------|
| Active patterns | 466 | 39 archived, 57 quarantined (562 on disk) |
| Functional agents | 3-4 | attacker, defender, verifier, secure-reviewer |
| Skills | 53 total (30 shipped) | Claude Code skill registry as of 2026-02-10 |
| Tools | 7 | Slither, Aderyn, Mythril, Echidna, Medusa, Foundry, Semgrep |
| E2E pipeline | Partial | Breaks at Stage 4 — Phase 3 target |
| Multi-agent debate | Not yet run | Phase 4 target |
| Benchmarks | None run | Phase 5 target |

---

## Session Starters

| If you want to... | Load |
|-------------------|------|
| Run your first audit | [getting-started/first-audit.md](getting-started/first-audit.md) |
| Understand the vision | [PHILOSOPHY.md](PHILOSOPHY.md) |
| Write patterns | [guides/patterns-basics.md](guides/patterns-basics.md) |
| Query the graph | [guides/queries.md](guides/queries.md) |
| Use VRS skills | [guides/skills-basics.md](guides/skills-basics.md) |
| Configure agents | [reference/agents.md](reference/agents.md) |
| Understand tools | [reference/tools-overview.md](reference/tools-overview.md) |
| Test patterns | [guides/testing-basics.md](guides/testing-basics.md) |

---

## LLM-Optimized Index

Use the progressive disclosure index for minimal context loads:

- [DOC-INDEX.md](DOC-INDEX.md)

---

## Quick Start

```bash
# Install (dev — not yet on PyPI)
git clone <repo> && cd alphaswarm
uv tool install -e .

# Primary workflow: Claude Code orchestrates the audit
claude
/vrs-audit contracts/

# Optional developer tool calls (debug/CI):
uv run alphaswarm build-kg contracts/
uv run alphaswarm query "functions without access control"
```

> **Status:** Claude Code workflows are the product interface. CLI commands are subordinate tool calls for development, CI, and deep diagnostics.

---

## Documentation Structure

```
docs/
├── index.md              # This file
├── DOC-INDEX.md          # LLM-optimized routing
├── PHILOSOPHY.md         # Vision and principles
├── LIMITATIONS.md        # Known constraints
├── architecture.md       # System overview
├── getting-started/
│   ├── installation.md   # Setup
│   └── first-audit.md    # First audit tutorial
├── guides/
│   ├── patterns-basics.md    # Pattern fundamentals
│   ├── patterns-advanced.md  # Tier A+B, PCP v2
│   ├── skills-basics.md      # Skills fundamentals
│   ├── skills-authoring.md   # Schema v2, authoring
│   ├── testing-basics.md     # Pattern testing
│   ├── testing-advanced.md   # Workflow harness + validation
│   ├── vulndocs-basics.md    # VulnDocs intro
│   ├── vulndocs-authoring.md # Validation pipeline
│   ├── queries.md        # Query syntax
│   └── beads.md          # Investigation packages
├── workflows/
│   ├── README.md         # Workflow index
│   └── workflow-*.md     # Per-workflow contracts
├── reference/
│   ├── agents.md         # Agent catalog (3-4 functional)
│   ├── tools-overview.md # Tool architecture
│   ├── tools-adapters.md # Detector mappings
│   ├── operations.md     # 20 semantic operations
│   ├── properties.md     # 275 emitted properties
│   ├── cli.md            # CLI tool reference (subagent/dev)
│   ├── skill-schema-v2.md# Skill authoring
│   └── graph-first-template.md
├── claude-code-architecture.md              # Claude Code workflow-first architecture
└── .archive/             # Legacy docs
```

---

## Core Docs

| Document | Purpose |
|----------|---------|
| [PHILOSOPHY.md](PHILOSOPHY.md) | Vision, behavioral detection, evidence-first |
| [architecture.md](architecture.md) | System components and data flow |
| [LIMITATIONS.md](LIMITATIONS.md) | Known constraints |

---

## Getting Started

| Document | Purpose |
|----------|---------|
| [installation.md](getting-started/installation.md) | Install dependencies |
| [first-audit.md](getting-started/first-audit.md) | Run first audit |

---

## Guides

| Topic | Basic | Advanced |
|-------|-------|----------|
| Patterns | [patterns-basics.md](guides/patterns-basics.md) | [patterns-advanced.md](guides/patterns-advanced.md) |
| Skills | [skills-basics.md](guides/skills-basics.md) | [skills-authoring.md](guides/skills-authoring.md) |
| Testing | [testing-basics.md](guides/testing-basics.md) | [testing-advanced.md](guides/testing-advanced.md) |
| VulnDocs | [vulndocs-basics.md](guides/vulndocs-basics.md) | [vulndocs-authoring.md](guides/vulndocs-authoring.md) |

**Other guides:** [queries.md](guides/queries.md), [beads.md](guides/beads.md)

---

## Reference

| Document | Purpose |
|----------|---------|
| [agents.md](reference/agents.md) | Agent catalog (3-4 functional) |
| [tools-overview.md](reference/tools-overview.md) | Tool architecture |
| [tools-adapters.md](reference/tools-adapters.md) | Detector mappings |
| [operations.md](reference/operations.md) | Semantic operations |
| [properties.md](reference/properties.md) | Security properties (275 emitted, 147 orphan) |
| [cli.md](reference/cli.md) | CLI tool calls (subagent/dev) |
| [claude-code-architecture.md](claude-code-architecture.md) | Claude Code workflow architecture and APIs |
| [claude-code-workflow-migration.md](migrations/claude-code-workflow-migration.md) | Migration and breaking changes |
| [skill-schema-v2.md](reference/skill-schema-v2.md) | Skill authoring schema |
| [graph-first-template.md](reference/graph-first-template.md) | Mandatory agent workflow |

---

## Key Concepts

| Concept | Description |
|---------|-------------|
| **BSKG** | Behavioral Security Knowledge Graph |
| **Semantic Operations** | 20 behavior-based detections |
| **Behavioral Signatures** | R:bal→X:out→W:bal = reentrancy |
| **Two-Tier Detection** | Tier A (deterministic) + Tier B (LLM) + Tier C (labels) |
| **Beads** | Self-contained investigation packages |
| **Graph-First** | Agents MUST query BSKG before conclusions |

---

## Developer Tool Commands

```bash
uv run alphaswarm build-kg contracts/           # Build graph
uv run alphaswarm query "pattern:X"             # Query patterns
uv run alphaswarm tools status                  # Check tools
uv run alphaswarm vulndocs validate vulndocs/   # Validate patterns
uv run pytest tests/ -n auto             # Run tests (3.79x faster)
```

These are tool-level commands invoked by Claude Code workflows or used directly in dev/CI.

---

## Current Milestone: 6.0 From Theory to Reality

| Phase | Status |
|-------|--------|
| 1 + 1.1: Emergency Triage + Review | COMPLETE |
| 2 + 2.1: Property Gap + Review | COMPLETE |
| **3.1: Testing Audit & Cleanup** | **ACTIVE** |
| **3.1b: Workflow Harness + Test Corpus** | **NEXT** |
| **3.2: First Working Audit** | **NEXT** |
| 4: Agent Teams Debate | PLANNED |
| 5: Benchmark Reality | PLANNED |
| 6-8: Tests, Docs, Ship | PLANNED |

| Document | Purpose |
|----------|---------|
| [.planning/ROADMAP.md](../.planning/ROADMAP.md) | v6.0 milestone phases |
| [.planning/STATE.md](../.planning/STATE.md) | Current progress and honest metrics |

---

*Updated 2026-02-10 | Aligned with Claude Code workflow-first architecture*
