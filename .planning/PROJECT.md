# AlphaSwarm.sol - Milestone 6.0 (From Theory to Reality)

## What This Is

AlphaSwarm.sol is a behavioral security framework for Solidity smart contracts. It builds a Vulnerability Knowledge Graph (BSKG) from code using semantic operations, then coordinates AI agents (attacker, defender, verifier) to investigate and verify findings through evidence-linked debate.

**Current reality (v6.0):** The graph builder works. Individual modules are architecturally sound. But the end-to-end pipeline — from contract to verified vulnerability report — has never been proven to work. Milestone 6.0 exists to prove (or disprove) every capability on real contracts.

## Core Value

Detect complex logic bugs and authorization vulnerabilities using behavioral graph reasoning with multi-agent verification — but ONLY claim what's been proven with evidence.

## Requirements

### Validated

<!-- Proven capabilities from v5.0 -->

- ✓ **BSKG Builder** — 208 security properties per function, 20 semantic operations — v5.0 (graph builds reliably)
- ✓ **VulnDocs Infrastructure** — Pattern store, navigator, cache, templates — v5.0
- ✓ **Orchestration Architecture** — Routing, schemas, execution loop design — v5.0
- ✓ **Semantic Labeling** — Label taxonomy, LLM labeler, overlay lifecycle — v5.0
- ✓ **Tool Integration** — SARIF adapters for Slither, Aderyn, Mythril — v5.0
- ✓ **Protocol Context Pack** — Economic context, off-chain dependency tracking — v5.0
- ✓ **CLI Interface** — `alphaswarm build-kg`, `query`, `orchestrate` commands — v5.0
- ✓ **Testing Infrastructure** — Pytest framework, DVDeFi corpus, gauntlet structure — v5.0
- ✓ **P0 Bug Fixes** — PatternEngine API, resume loop, skill frontmatter, vulndocs validation — v6.0 Phase 1
- ✓ **Property Gap Resolution** — 37 properties emitted, ~290 working patterns, dead code removed — v6.0 Phase 2

### Active

<!-- v6.0 requirements — must be proven, not just built -->

- [ ] **E2E Pipeline** — ONE complete audit from Solidity contract to vulnerability report
- [ ] **Agent Teams Debate** — Real multi-agent debate using Claude Code Agent Teams
- [ ] **Benchmark Results** — Reproducible precision/recall/F1 on SmartBugs + DVDeFi
- [ ] **Graph Value Proof** — Ablation study showing graph helps (or honest "it doesn't")
- [ ] **Test Overhaul** — Detection regression tests replacing mock-heavy unit tests
- [ ] **Documentation Honesty** — All docs reflect proven capabilities only
- [ ] **Hook Enforcement** — Graph-first and evidence hooks active in production
- [ ] **Ship** — New user can run `/vrs-audit contracts/` and get a real report

### Out of Scope

<!-- Things we know we won't do in v6.0 -->

- **Pool batching** — Fix basic pipeline first
- **Autonomous work-pulling** — Prove orchestration works at all first
- **Multi-SDK parallel** — Single provider sufficient
- **Self-improving loop** — Prove debate quality before automating improvement
- **Continuous validation pipeline** — Manual validation first
- **Publications** — Prove the tool works before publishing about it

## Context

### Current State (Post v5.0 Closure)

**What works:**
- BSKG builder: Constructs graph reliably with 208 properties/function
- Pattern engine: ~290 patterns active (after pruning 385 dead patterns)
- CLI commands: `build-kg`, `query` functional
- Tool adapters: SARIF parsing from Slither/Aderyn/Mythril

**What doesn't work (yet):**
- E2E pipeline: Breaks at Stage 4 (pattern matching → bead creation)
- Multi-agent debate: Never executed with real LLMs
- Graph reasoning by agents: Agents can't run `alphaswarm query` (wrong tool permissions)
- Benchmark claims: 84.6% DVDeFi detection based on YAML annotation, not pipeline output
- Most tests: 11,282 tests but majority are mock-heavy implementation mirrors

**Codebase:**
- ~260,000 LOC across 475 Python files
- 556 pattern files (290 working, 141 quarantined, 169 deleted in v6.0 Phase 2)
- 245 test files, 11,282 tests
- 43 v5.0 phase directories preserved as history

### Lessons from v5.0

1. Building features without validating they work creates a house of cards
2. Mock tests that mirror implementation prove nothing about real behavior
3. Planning 288 sub-plans creates overhead that prevents validation
4. "99% complete" is meaningless when the 1% is "does it actually work?"
5. Theoretical capabilities must be proven before claiming them

## Constraints

- **Prove before build** — Every feature must demonstrate value on real contracts
- **Evidence-first** — No claims without reproducible evidence
- **No aspirational docs** — Only document what actually works
- **Token budget** — < 6k per LLM call (< 8k absolute max)
- **Graph-first enforcement** — Agents MUST use BSKG, enforced by hooks
- **Agent Teams-first orchestration** — Claude Code Agent Teams for orchestration and testing

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Close v5.0 honestly | Product doesn't work E2E despite 276/288 plans | ✓ Good — honest foundation for v6.0 |
| Prune 385 dead patterns | Orphan properties made patterns uncacheable | ✓ Good — ~290 honest patterns |
| Fix P0 bugs first | Can't validate if basic functions are broken | ✓ Good — pipeline partially unblocked |
| Agent Teams-first orchestration | Legacy controller-first orchestration was fragile; Agent Teams is the target model | — Pending (Phase 4) |
| Ablation study for graph | Must prove graph reasoning adds value | — Pending (Phase 5) |
| Replace mock tests | Current tests don't prove real behavior | — Pending (Phase 6) |
| Quality over timeline | No deadline pressure, ship when proven | — Active (same as v5.0) |

---
*Last updated: 2026-02-08*
