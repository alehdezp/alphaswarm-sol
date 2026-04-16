# AlphaSwarm.sol — Multi-Agent Smart Contract Security Framework

## Session Starters

| If you want to... | Load |
|---|---|
| Understand the vision | `docs/PHILOSOPHY.md` |
| See system architecture | `docs/architecture.md` |
| Find the right doc | `docs/DOC-INDEX.md` |
| Run an audit | `.claude/skills/vrs-audit/SKILL.md` |
| Write or fix patterns | `docs/guides/patterns-basics.md` |
| Author skills/agents | `docs/guides/skills-basics.md` |
| Run tests | Quick Commands below |
| Check project status | `.planning/STATE.md` |
| See the testing philosophy | `.planning/testing/rules/canonical/TESTING-PHILOSOPHY.md` |
| Plan a phase | `.planning/testing/PLAN-PHASE-GOVERNANCE.md` |

## Key Terms

AlphaSwarm.sol, BSKG, behavioral-signature, semantic-operation, VulnDocs, pattern-tier-A/B/C, evidence-packet, bead, proof-token, VQL, multi-agent-debate, Claude-Code-orchestration, graph-first-reasoning

---

## Core Identity

**AlphaSwarm.sol is a shippable multi-agent orchestration framework for smart contract security.**

It coordinates specialized AI agents (attacker, defender, verifier) using Claude Code as the orchestrator to perform **human-like security assessments** that go far beyond static analysis. The agents use a behavioral security knowledge graph (BSKG), vulnerability pattern reasoning, and economic protocol context to discover **complex authorization bugs, logic flaws, and novel vulnerabilities** that cause real financial losses in Web3.

**The Goal:** Build the world's best AI-powered Solidity security tool that finds vulnerabilities like a top human auditor — with complex reasoning, cross-function analysis, and protocol-aware context — not just pattern matching.

**The Core Insight: Names lie. Behavior does not.** Traditional tools detect `withdraw()`. Rename it to `processPayment()` and naive rules fail. AlphaSwarm.sol detects the **behavioral pattern** `R:bal -> X:out -> W:bal` (read balance, external call, write balance) regardless of naming.

---

## Execution Model

**This is NOT a CLI tool. This is a Claude Code orchestration framework.**

The user interacts with **Claude Code**, not with the terminal. Claude Code is the orchestrator that:
- Creates and manages tasks (TaskCreate, TaskUpdate)
- Spawns specialized subagents (attacker, defender, verifier)
- Calls CLI tools via Bash (`alphaswarm build-kg`, `tools run`, etc.)
- Synthesizes findings and produces reports

**The CLI (`alphaswarm`) is a TOOL called by Claude Code, not the product.**

```
User → Claude Code (orchestrator)
         ├── Skills (.claude/skills/) define WHAT to do
         ├── Subagents (attacker/defender/verifier) investigate
         ├── CLI (Bash: alphaswarm ...) builds graph, runs tools
         └── Verdicts + Evidence Packets (output)
```

### 9-Stage Audit Pipeline (`/vrs-audit`)

```
Stage 1: Preflight     → Validate settings, check tools
Stage 2: Build Graph   → alphaswarm build-kg (200+ properties/function)
Stage 3: Context       → Economic context via Exa MCP
Stage 4: Tool Init     → Static analyzers (Slither, Aderyn)
Stage 5: Detection     → 466 active patterns, Tier A/B/C
Stage 6: Tasks         → TaskCreate per candidate finding
Stage 7: Verification  → Attacker → Defender → Verifier debate
Stage 8: Report        → Evidence-linked findings
Stage 9: Progress      → Store state, emit resume hints
```

Full execution model details: `docs/PHILOSOPHY.md`

### Development vs Product Context

| Aspect | DEVELOPMENT | PRODUCT |
|--------|-------------|---------|
| **What** | Source repo where we BUILD | Skills + agents running INSIDE Claude Code |
| **Claude Code role** | Dev assistant | **THE ORCHESTRATOR** |
| **CLI role** | Dev testing | Tool called BY Claude Code |

```bash
# Install CLI (called BY Claude Code)
uv tool install -e .
# User runs: /vrs-audit contracts/
```

---

## Architecture

```
Solidity → Slither → BSKG Builder → VulnDocs Patterns → Tool Integration
                           ↓                                    ↓
                    Protocol Context                    Beads + Pools
                           ↓                                    ↓
                    Multi-Agent Verification (attacker ↔ defender ↔ verifier)
                           ↓
                    Verdicts + Evidence Packets
```

### Core Modules

| Module | Purpose | LOC |
|--------|---------|-----|
| `kg/builder/` | Graph construction from Slither | ~9,500 |
| `orchestration/` | Pools, debate, routing | ~6,400 |
| `tools/` | External tool integration (7 adapters) | ~12,000 |
| `context/` | Protocol context packs | ~6,000 |
| `labels/` | Semantic labeling | ~4,000 |
| `shipping/` | Product distribution (skills + agents) | ~50 files |
| `vulndocs/` | 466 active patterns across 18 categories | 680+ patterns |

### Detection Philosophy

- **Semantic Operations > Names**: Detect `TRANSFERS_VALUE_OUT` + `WRITES_USER_BALANCE` ordering, not function names
- **Three-Tier Detection**: Tier A (deterministic, graph-only) + Tier B (LLM-verified) + Tier C (label-dependent)
- **Evidence-First**: Every finding links to graph node IDs, code locations, operation sequences
- **Graph-First Rule**: Agents MUST query BSKG before conclusions — no manual code reading first

Full architecture: `docs/architecture.md` | Full philosophy: `docs/PHILOSOPHY.md`

---

## Skills & Agents

### Core Investigation Agents

| Agent | Purpose | Model |
|-------|---------|-------|
| `vrs-attacker` | Construct exploit paths | opus |
| `vrs-defender` | Find guards/mitigations | sonnet |
| `vrs-verifier` | Cross-check evidence, arbitrate | opus |
| `vrs-secure-reviewer` | Evidence-first security review | sonnet |

All agents follow `docs/reference/graph-first-template.md`: BSKG queries → Evidence packet → Conclusion citing evidence.

### Canonical Sources

- **Agent Catalog:** `src/alphaswarm_sol/agents/catalog.yaml` (24 agents)
- **Skill Registry:** `src/alphaswarm_sol/skills/registry.yaml` (34 skills)

<!-- AUTO-MANAGED-BEGIN: skills -->
### Product Skills (shipped: `src/alphaswarm_sol/shipping/skills/`)

| Skill | Purpose |
|-------|---------|
| `/vrs-audit` | Full 9-stage audit execution loop |
| `/vrs-verify` | Multi-agent verification |
| `/vrs-investigate` | Deep vulnerability investigation |
| `/vrs-debate` | Structured adversarial debate |
| `/vrs-tool-slither` | Run Slither analysis |
| `/vrs-tool-aderyn` | Run Aderyn analysis |
| `/vrs-tool-mythril` | Run Mythril symbolic execution |
| `/vrs-tool-coordinator` | Optimal tool selection strategy |
| `/vrs-bead-*` | Create, update, list investigation beads |
| `/vrs-orch-spawn` | Spawn worker agent |
| `/vrs-orch-resume` | Resume interrupted work |
| `/vrs-health-check` | Validate installation |

### Development Skills (`.claude/skills/`, not shipped)

| Skill | Purpose | Auto? |
|-------|---------|-------|
| `/test-builder` | Test construction guidelines | **AUTO-INVOKE** |
| `/vrs-test-enforce` | Quality gates | **AUTO-INVOKE** |
| `/pattern-forge` | Iterative pattern creation | |
| `/agent-skillcraft` | Skill/subagent design system | |
| `/vrs:discover` | Automated vulnerability search | |
| `/vrs:add-vulnerability` | Add new vuln to VulnDocs | |
| `/vrs:ingest-url` | Ingest from URL to VulnDocs | |
| `/vrs:refine` | Improve patterns from feedback | |
| `/vrs-test-*` | Workflow, E2E, component testing | |
<!-- AUTO-MANAGED-END: skills -->

### Location Guide

| Category | Location | Shipped? |
|----------|----------|----------|
| Product skills | `src/alphaswarm_sol/shipping/skills/` | Yes |
| Product agents | `src/alphaswarm_sol/shipping/agents/` | Yes |
| Dev skills | `.claude/skills/` (real files) | No |
| Dev agents | `.claude/agents/` (real files) | No |

---

## Testing

### Testing Identity (Phase 3.1c)

The testing framework is an intelligent continuous improvement system that answers: **"Did the agent THINK correctly, and can we make it think better?"**

It does not just assert "did the workflow run?" — it evaluates reasoning quality using LLM-powered assessment, graph value scoring, and agent debriefs. The most dangerous failure is a workflow that "works" but reasons badly.

**Two-Tier Evaluation Architecture:**
- **Tier 1 (Engine):** Deterministic pipeline — hooks observe, parser extracts, scorer computes, evaluator judges, runner orchestrates
- **Tier 2 (Intelligence):** Adaptive layer — discovers gaps, generates tests, heals contracts, fingerprints behavior (12 sub-modules, activates as data accumulates)

**Key Capabilities:**
- **Two-stage testing**: Capability contract check (pass/fail) FIRST, reasoning evaluation ONLY if capability passes
- **7-move reasoning decomposition**: HYPOTHESIS_FORMATION, QUERY_FORMULATION, RESULT_INTERPRETATION, EVIDENCE_INTEGRATION, CONTRADICTION_HANDLING, CONCLUSION_SYNTHESIS, SELF_CRITIQUE — each scored independently
- **Dual-Opus evaluator**: Two independent evaluators score the same transcript; disagreement > 15 points flags unreliable evaluation
- **Graph Value Scorer**: Distinguishes checkbox compliance (< 30) from genuine graph use (> 70)
- **Adaptive tiers**: Dynamic promotion/demotion based on behavioral signals. Auto-promote on sustained low scores
- **Regression detection**: Tier-weighted thresholds (Core >10pt=REJECT, Important >15pt, Standard >25pt)
- **Anti-fabrication**: 100% pass rate, identical outputs, scores at 100, duration < 5s → all trigger investigation
- **Safe improvement**: NEVER modify production `.claude/` — use jujutsu workspace isolation

**Execution constraint:** Plans spawning Agent Teams execute sequentially in top-level sessions (not from subagents).

Philosophy: `.planning/testing/rules/canonical/TESTING-PHILOSOPHY.md`
Framework: `.planning/testing/rules/canonical/TESTING-FRAMEWORK.md`
Phase docs: `.planning/phases/3.1c-reasoning-evaluation-framework/`

### Test Practices

- Test contracts: `tests/contracts/*.sol`
- Use `load_graph(contract_name)` from `tests/graph_cache.py`
- Include both **vulnerable** and **safe** variants
- **Performance:** `pytest -n auto --dist loadfile` (3.79x speedup)

**CRITICAL: Targeted Tests Only.** Never run the full test suite for localized changes. Run only tests that exercise changed files (`pytest tests/test_specific.py -k "test_name"`). Full suite runs ONLY when: (1) user explicitly requests it, (2) change is cross-cutting (core schema), or (3) pre-release. A `PreToolUse` hook enforces this — see `.claude/hooks/guard-full-tests.sh`.

### Evaluation Framework — Agent Teams Protocol

When running evaluation/testing framework sessions (Phase 3.1c evaluations, calibration batches):

- **MUST use Agent Teams** (TeamCreate + teammates with SendMessage), not bare Task() subagents
- **MUST use `isolation: "worktree"`** — teammates get zero access to project root context
- **MUST ensure zero leakage**: teammates must NOT know this is a test, what the project is, or expected results. Prompt only with the contract path and CLI tools available.
- **MUST restrict tools**: only `build-kg`, `query`, `Read` (contract files only)
- **MUST use interactive feedback on failure**: When results are unexpected, use SendMessage to ask the teammate WHY, capture structured feedback, and use it to improve the evaluation process

---

## Quick Commands

```bash
# Knowledge Graph
uv run alphaswarm build-kg contracts/           # Build graph (TOON default)
uv run alphaswarm build-kg contracts/ --with-labels  # Include semantic labels
uv run alphaswarm query "functions without access control"  # NL query

# VulnDocs
uv run alphaswarm vulndocs validate vulndocs/   # Validate all
uv run alphaswarm vulndocs list --status validated

# Tools
uv run alphaswarm tools status                  # Check installed
uv run alphaswarm tools run contracts/ --tools slither,aderyn

# Tests
uv run pytest tests/ -n auto --dist loadfile    # Parallel (fast)

# Evaluation Session Analysis
uv run alphaswarm eval sessions                 # List recorded sessions
uv run alphaswarm eval timeline <session-id>    # Chronological event timeline
uv run alphaswarm eval search "build-kg"        # FTS5 full-text search
uv run alphaswarm eval violations               # Show violations across sessions
uv run alphaswarm eval patterns                 # Cross-session failure patterns
```

Full tooling guide: `.planning/TOOLING.md`

---

## Current Status

**Milestone 6.0: From Theory to Reality** — Nothing ships until proven.

| Phase | Name | Status |
|-------|------|--------|
| 1, 1.1, 2, 2.1 | Triage + Property Gap + Reviews | DONE |
| 3.1, 3.1.1, 3.1b | Testing Audit + Harness | DONE |
| 3.1c | Reasoning Evaluation Framework | PARTIAL (resumes after 3.1e) |
| 3.1c.1 | CLI & Graph Isolation Hardening | PLANNED |
| 3.1c.2 | Agent Evaluation Harness Hardening | PLANNED |
| **3.1c.3** | **Evaluation Intelligence Bootstrap** | **PLANNED** |
| 3.1d | Detection-Evaluation Feedback Bridge | DONE |
| 3.1e | Evaluation Zero — Empirical Sprint | DONE |
| 3.1f | Proven Loop Closure | PLANNED |
| 3.2 | First Working Audit | PLANNED |
| 4+ | Agent Teams, Benchmarks, Ship | PLANNED |

**Critical path:** 3.1c (resumes) → 3.1c.1 → 3.1c.2 → 3.1c.3 → 3.1f → 3.2
**Current state:** `.planning/STATE.md`

---

## Constraints

- **Never modify** `builder_legacy.py` or `executor.py` without explicit permission
- **Graph-first enforcement**: Agents MUST use BSKG queries, not manual code reading
- **Token budget**: < 6k per LLM call (< 8k absolute max)
- **LSP-first**: Use pyright-lsp for Python navigation/refactoring (go_to_definition, find_references, hover)
- **Tooling guide**: `.planning/TOOLING.md` for task → tool selection

### Model Delegation

| Model | Use For |
|-------|---------|
| **Haiku** | URL filtering, dedupe, mechanical extraction |
| **Sonnet** | Core authoring, pattern validation, test generation |
| **Opus** | Pattern refinement when gates fail, complex reasoning |

### Pattern Rating

| Status | Precision | Recall |
|--------|-----------|--------|
| draft | < 70% | < 50% |
| ready | >= 70% | >= 50% |
| excellent | >= 90% | >= 85% |

---

## Progressive Disclosure

### Documentation Layers
| Layer | Content | When to Load |
|-------|---------|--------------|
| Index | Titles, paths (this file) | Always (in context) |
| Overview | Section summaries | On topic mention |
| Detail | Full docs/guides | On specific need |

### Loading Priority
1. `.planning/STATE.md` — Current position, decisions, blockers
2. Relevant skill SKILL.md — If task matches a skill trigger
3. Plan governance — For phase planning: `.planning/testing/PLAN-PHASE-GOVERNANCE.md`
4. `docs/DOC-INDEX.md` — For discovering deeper resources
5. Specific docs — On demand

### Documentation Index

| Category | Basic | Advanced |
|----------|-------|----------|
| Vision | `docs/PHILOSOPHY.md` | `docs/architecture.md` |
| Patterns | `docs/guides/patterns-basics.md` | `docs/guides/patterns-advanced.md` |
| Skills | `docs/guides/skills-basics.md` | `docs/guides/skills-authoring.md` |
| Testing | `docs/guides/testing-basics.md` | `docs/guides/testing-advanced.md` |
| VulnDocs | `docs/guides/vulndocs-basics.md` | `docs/guides/vulndocs-authoring.md` |
| Tools | `docs/reference/tools-overview.md` | `docs/reference/tools-adapters.md` |
| Agents | `docs/reference/agents.md` | |
| Graph-First | `docs/reference/graph-first-template.md` | |
| Roadmap | `.planning/ROADMAP.md` | `.planning/STATE.md` |

### Token Budget
- Available: ~200K total
- This file: ~5K target
- Reserve for reasoning: ~50K
- Max doc loading: ~30K per request
