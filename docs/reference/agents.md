# Multi-Agent Verification System

**Specialized Agents for Evidence-First Security Analysis**

---

## Overview

AlphaSwarm.sol defines 24 agent roles with 3-4 currently functional (attacker, defender, verifier, secure-reviewer). Agents are coordinated by Claude Code and produce evidence-linked findings. Full multi-agent debate has not yet been executed (Phase 4 target).

**Key Benefits:**
- Debate protocol: Attacker → Defender → Verifier
- Graph-first: MUST use BSKG queries, not manual code reading
- Evidence-linked: Code locations and graph node citations
- Role-based: Specialized agents for investigation needs

---

## Workflow And Debugging Links

- Workflow map: `docs/workflows/README.md`
- Task orchestration: `docs/workflows/workflow-tasks.md`
- Verification: `docs/workflows/workflow-verify.md`
- Testing contract: `docs/reference/testing-framework.md`
- Debugging guide: `.planning/testing/guides/guide-agent-debugging.md`

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    KNOWLEDGE GRAPH                          │
└─────────────────────────────────────────────────────────────┘
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │   ATTACKER   │ │   DEFENDER   │ │   VERIFIER   │
    │   (opus)     │ │  (sonnet)    │ │   (opus)     │
    └──────────────┘ └──────────────┘ └──────────────┘
           └───────────────┼───────────────┘
                           ▼
                  ┌────────────────┐
                  │   INTEGRATOR   │
                  └────────────────┘
                           ▼
                  ┌────────────────┐
                  │   SUPERVISOR   │
                  └────────────────┘
```

---

## Agent Catalog

**Canonical Source:** `src/alphaswarm_sol/agents/catalog.yaml`

### Core Verification Agents

| Agent | Role | Model | Purpose |
|-------|------|-------|---------|
| `vrs-attacker` | attacker | opus | Construct exploit paths |
| `vrs-defender` | defender | sonnet | Find guards, mitigations |
| `vrs-verifier` | verifier | opus | Cross-check evidence, verdicts |
| `vrs-secure-reviewer` | reviewer | sonnet | Evidence-first security review |

### Orchestration Agents

| Agent | Role | Model | Purpose |
|-------|------|-------|---------|
| `vrs-supervisor` | supervisor | sonnet | Workflow orchestration |
| `vrs-integrator` | integrator | sonnet | Merge verdicts |
| `vrs-controller` | controller | haiku | Mechanical execution |

### Testing & Research Agents

| Agent | Role | Model | Purpose |
|-------|------|-------|---------|
| `vrs-test-builder` | test-builder | sonnet | Generate Foundry tests |
| `vrs-pattern-architect` | architect | opus | Design patterns |
| `vrs-test-conductor` | tester | sonnet | Workflow test orchestration and validation |

---

## Evidence Requirements

All agents MUST follow `docs/reference/graph-first-template.md`:

1. **BSKG Queries First** — Run queries before conclusions
2. **Evidence Packet** — Include graph node IDs, code locations
3. **Conclusion** — Must cite evidence IDs

**Rule:** No manual code reading before BSKG queries run.

---

## Agent Output Contracts

```yaml
output_contract:
  format: structured
  required_fields:
    - verdict           # confirmed/likely/uncertain/rejected
    - confidence        # 0.0-1.0
    - evidence          # List of evidence items
    - rationale         # Explanation
```

---

## Consensus Engine

**Location:** `src/alphaswarm_sol/agents/consensus.py`

### Consensus Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| **voting** | 3+/4 agents = HIGH_RISK | Default |
| **and** | ALL must agree | Ultra-low FP |
| **or** | ANY finds issue | High recall |
| **weighted** | Confidence-weighted | Production |

### Performance Metrics (Targets, Not Yet Benchmarked)

Benchmark-quality precision/recall/FP metrics are not yet finalized for the multi-agent path. Treat metric ranges as roadmap targets until Phase 5 benchmark outputs are published.

---

## Orchestrated Usage

Agent verification workflows are invoked through Claude Code skills:

```text
/vrs-verify <bead-id>
/vrs-debate <bead-id>
```

CLI `query` is a graph/tool command and is not the primary multi-agent entrypoint.

---

## When to Use Each Agent

| Use Case | Recommended Agents |
|----------|-------------------|
| Initial scan | Explorer + Pattern |
| Deep audit | All 4 agents |
| CI/CD check | Pattern + Risk (fast) |
| Formal verification | Constraint only |

---

## Related Documentation

- [Operations Reference](operations.md) - Semantic operations
- [Pattern Guide](../guides/patterns-basics.md) - Creating patterns
- [Graph-First Template](graph-first-template.md) - Evidence requirements

---

*See `src/alphaswarm_sol/agents/catalog.yaml` for complete agent definitions.*
