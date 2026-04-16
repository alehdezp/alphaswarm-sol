# BSKG 4.0 - Master Roadmap

**Mission:** Give LLM agents superpowers for smart contract security. Make every auditor 3x more effective.

**Last Updated:** 2026-01-09
**Status:** IMPLEMENTATION IN PROGRESS (Complete: 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,18; In progress: 0,17; TODO: 16,19,20)
**Philosophy:** See `docs/PHILOSOPHY.md` for core vision (v2.0)

---

## Quick Navigation

| Document | Purpose |
|----------|---------|
| `MASTER.md` | This file - High-level roadmap with phase overview |
| `phases/phase-N/TRACKER.md` | **Detailed phase trackers (190+ tasks, ~1010h est.)** - Source of truth |
| `phases/PHASE_TEMPLATE.md` | Standardized template for all phase trackers |
| `TODO.md` | Daily tracking and progress |

**Note:** Phase trackers are the authoritative source for all task details. Each phase tracker contains:
- Full task decomposition with dependencies
- Research requirements
- Test suite specifications
- Brutal self-critique checklists
- Iteration protocols for failed approaches
- Dynamic task spawning guidelines

---

## The Hard Truth

| Metric | Claimed | Reality |
|--------|---------|---------|
| Test Count | 2,424+ | Testing mocks, not real exploits |
| Precision | 88.73% | On YOUR test contracts only |
| DVDeFi Detection | **84.6%** | ✅ Phase 1 COMPLETE (11/13 challenges) |

**Phase 1 achieved 84.6% DVDeFi detection. Now building infrastructure to maintain and measure this.**

---

## Phase Overview

```
PHASE 1: FIX DETECTION          ✅ COMPLETE (84.6%)
    │ (sequential)
    ▼
PHASE 2: BENCHMARK INFRASTRUCTURE  ✅ COMPLETE (12/12 tasks)
    │ (sequential)
    ▼
PHASE 3: BASIC CLI & TASK SYSTEM  ✅ COMPLETE (17/17 tasks, 451 tests)
    │ (sequential)
    ▼
PHASE 4: TEST SCAFFOLDING        ✅ COMPLETE (258 tests)
    │ (sequential)
    ▼
PHASE 5: REAL-WORLD VALIDATION   ⏳ IN PROGRESS
    │
    ├─────────────────┬─────────────────┐
    ▼                 ▼                 ▼
┌─────────┐     ┌─────────┐     ┌─────────┐
│PHASE 6  │     │PHASE 7  │     │PHASE 8  │   ⟵ PARALLEL WINDOW 1
│ Beads   │     │Learning │     │Metrics  │     (~110h → ~45h)
└────┬────┘     └────┬────┘     └────┬────┘
    └─────────────────┴─────────────────┘
                      │ (wait for all 3)
                      ▼
PHASE 9: CONTEXT OPTIMIZATION (PPR)
    │ (sequential)
    ▼
PHASE 10: GRACEFUL DEGRADATION ─────────────── ★ GATE 2
    │
    ├─────────────────┬─────────────────┐
    ▼                 ▼                 ▼
┌─────────┐     ┌─────────┐     ┌─────────┐
│PHASE 11 │     │PHASE 12 │     │PHASE 13 │   ⟵ PARALLEL WINDOW 2
│ LLM     │     │ Agents  │     │Grimoires│     (~135h → ~55h)
└────┬────┘     └────┬────┘     └────┬────┘
    └─────────────────┴─────────────────┘
                      │ (wait for all 3) ── ★ GATE 3
                      ▼
PHASE 14: CONFIDENCE CALIBRATION
    │ (sequential)
    ▼
PHASE 15: NOVEL SOLUTIONS INTEGRATION
    │ (sequential)
    ▼
PHASE 16: RELEASE PREP (RC)
    │ (sequential)
    ▼
PHASE 20: FINAL TESTING PHASE ── ★ GATE 4
    │
    └── RELEASE 4.0.0 (GA)

VULNDOCS TRACK (start after Phase 9 + Phase 11):
PHASE 17: VULNDOCS KNOWLEDGE SCHEMA -> PHASE 18: KNOWLEDGE MINING -> (joins before Phase 20)

SEMANTIC LABELING TRACK (start after Phases 6/7/9/11):
PHASE 19: SEMANTIC LABELING FOR COMPLEX LOGIC DETECTION -> (joins before Phase 20)

LEGEND:
  │    Sequential (must wait)
  ├──┐ Parallel fork (can run simultaneously)
  └──┘ Parallel join (wait for all branches)
  ★    Decision gate (go/no-go checkpoint)

DECISION GATES (Stop & Evaluate):
  ★ After Phase 5: Real-world precision < 70%? → Re-evaluate detection strategy
  ★ After Phase 10: No user adoption? → Pivot distribution strategy
  ★ After Phase 11/12/13: Tier B doesn't improve precision by 10%? → Cut LLM scope
  ★ After Phase 20: Dossier incomplete or evidence packet audit fails? → Halt GA release
```

---

## Phase Summary

| Phase | Name | Priority | Status | Tracker |
|-------|------|----------|--------|---------|
| **1** | **Fix Detection** | CRITICAL | ✅ COMPLETE | `phases/phase-1/` |
| **2** | **Benchmark Infrastructure** | CRITICAL | IN PROGRESS (8/12 tasks complete) | `phases/phase-2/` |
| **3** | **Basic CLI & Task System** | HIGH | BLOCKED (by Phase 2) | `phases/phase-3/` |
| **4** | **Test Scaffolding** | HIGH | ✅ COMPLETE | `phases/phase-4/` |
| **5** | **Real-World Validation** | HIGH | IN PROGRESS | `phases/phase-5/` |
| **6** | **Beads System** | MEDIUM | ✅ COMPLETE (227 tests) | `phases/phase-6/` |
| **7** | **Conservative Learning** | MEDIUM | ✅ COMPLETE (273 tests) | `phases/phase-7/` |
| **8** | **Metrics & Observability** | MEDIUM | COMPLETE (core) - optional tasks pending | `phases/phase-8/` |
| **9** | **Context Optimization** | MEDIUM | COMPLETE (core) - fixtures pending | `phases/phase-9/` |
| **10** | **Graceful Degradation** | MEDIUM | COMPLETE (core) - optional tasks pending | `phases/phase-10/` |
| 11 | LLM Integration | MEDIUM | IN PROGRESS | `phases/phase-11/` |
| 12 | Agent SDK Micro-Agents | LOW | IN PROGRESS (deferred MUST tasks pending) | `phases/phase-12/` |
| 13 | Grimoires & Skills | MEDIUM | ✅ COMPLETE (138 tests) | `phases/phase-13/` |
| 14 | Confidence Calibration | MEDIUM | ✅ COMPLETE (62 tests) | `phases/phase-14/` |
| 15 | Novel Solutions | LOW | ✅ COMPLETE (30 tests) | `phases/phase-15/` |
| 16 | Release Prep (RC) | MEDIUM | TODO (unblocked) | `phases/phase-16/` |
| **17** | **VulnDocs Knowledge System** | **CRITICAL** | IN PROGRESS (7/35 tasks, 87+Exa, 4 parallel subagents) | `phases/phase-17/` |
| **18** | **VulnDocs Knowledge Mining** | **CRITICAL** | COMPLETE (core) - optional task pending | `phases/phase-18/` |
| **19** | **Semantic Labeling for Complex Logic Detection** | **HIGH** | TODO | `phases/phase-19/` |
| **20** | **Final Testing Phase** | **CRITICAL** | TODO | `phases/phase-20/` |

---

## Phase 17: Self-Improving Vulnerability Discovery

**Mission:** DISCOVER vulnerabilities through reasoning, not just aggregate into predefined categories.

**Primary Skill:** `vuln-discovery` (Self-Improving Discovery Skill)
- Location: `.claude/skills/vuln-discovery.md`
- Philosophy: DISCOVER > REASON > LEARN > EVOLVE
- Commands: `/vuln-discovery crawl|analyze|reflect|evolve|status`

**Agents:**
| Agent | Model | Purpose |
|-------|-------|---------|
| `knowledge-aggregation-worker` | **Sonnet 4.5** | Deep reasoning, discovery |
| `crawl-filter-worker` | **Haiku 4.5** | Fast parallel filtering |

**Pipeline**: Download → Filter (Haiku, parallel) → Discover (Sonnet) → Integrate

**Discovery State:** `.true_vkg/discovery/`
- `state.yaml` - Learned patterns, emerging themes
- `detection_heuristics.yaml` - Self-evolved detection rules (versioned)
- `novel_findings.yaml` - Log of novel discoveries
- `category_proposals/` - Proposed new categories

### Source Coverage (87 Sources Across 10 Tiers)

| Tier | Category | Sources | Priority | Status |
|------|----------|---------|----------|--------|
| 1 | Vulnerability DBs | Solodit, Rekt, DefiLlama, SlowMist, Immunefi | CRITICAL | TODO |
| 2 | Audit Contests | Code4rena, Sherlock, Cantina, CodeHawks, Hats, Secure3 | CRITICAL | TODO |
| 3 | Audit Firms | ToB, OZ, Spearbit, Cyfrin, Zellic +14 more | CRITICAL | TODO |
| 4 | Researchers | samczsun, cmichel, Tincho, Patrick Collins +8 more | HIGH | TODO |
| 5 | Education | SWC, Secureum, Smart Contract Programmer +4 more | HIGH | TODO |
| 6 | CTFs | DamnVulnerableDeFi, Ethernaut, Paradigm CTF +4 more | HIGH | TODO |
| 7 | GitHub Repos | DeFiHackLabs, Web3Bugs, Solcurity +7 more | HIGH | TODO |
| 8 | Protocol Docs | Uniswap, Aave, Compound, Chainlink +4 more | MEDIUM-HIGH | TODO |
| 9 | Formal Verification | Certora, Halmos, Echidna, Foundry, Scribble | MEDIUM | TODO |
| 10 | Emerging/L2 | Arbitrum, Optimism, zkSync, EigenLayer +3 more | MEDIUM | TODO |

### Infrastructure Status (7/21 Tasks Complete)

| Task | Status | Tests |
|------|--------|-------|
| 17.0 Schema | ✅ DONE | 78 |
| 17.1 Category Structure | ✅ DONE | 144 files |
| 17.2 Templates | ✅ DONE | 48 |
| 17.4 Navigator API | ✅ DONE | 52 |
| 17.5 Cache Integration | ✅ DONE | 62 |
| 17.6 Context Builder | ✅ DONE | 67 |
| 17.7 LLM Interface | ✅ DONE | 72 |
| **Total Tests** | | **608** |

### Knowledge Aggregation Tasks (Pending)

| Task | Sources | Est. Hours |
|------|---------|------------|
| 17.3a Vuln DBs | 6 | 8h |
| 17.3b Audit Contests | 6 | 12h |
| 17.3c Audit Firms | 19 | 16h |
| 17.3d Researchers | 12 | 8h |
| 17.3e Education | 7 | 6h |
| 17.3f CTFs | 7 | 4h |
| 17.3g GitHub | 10 | 8h |
| 17.3h Protocol Docs | 8 | 6h |
| 17.3i Formal Verification | 5 | 4h |
| 17.3j Emerging/L2 | 7 | 6h |

### Exa-Based Discovery Tasks (Dynamic Source Expansion)

| Task | Focus Area | Est. Hours | Status |
|------|------------|------------|--------|
| 17.16 Exa Source Discovery | New sources not in 87-list | 4h | TODO |
| 17.17 Novel Vulnerability Search | 2024-2026 writeups | 6h | TODO |
| 17.18 Protocol-Specific Deep Dive | ERC-4337, EigenLayer, ZK, bridges, intents | 8h | TODO |
| 17.19 Specific Vuln Extraction | One-by-one vulnerability extraction | 12h | TODO |
| 17.20 Pattern Enrichment | Code patterns via get_code_context_exa | 4h | TODO |
| 17.21 Weekly Scan Automation | Continuous discovery | 4h | TODO |

**Exa Query Categories:**
- Account Abstraction (ERC-4337, bundler, paymaster)
- Restaking (EigenLayer, AVS, slashing)
- ZK-Rollup (zkSync, zkEVM, proof verification)
- Cross-chain/Bridges (LayerZero, message replay, relayer)
- Intent-Based (CoW protocol, solver collusion)
- ERC-4626 Vaults (share inflation, first depositor, donation)
- Novel Reentrancy (Curve read-only, cross-contract, view function)
- Oracle Variants (CCIP, Pyth, Redstone)
- Protocol-Specific (Uniswap V4 hooks, GMX perpetuals, Morpho, Pendle)
- Emerging 2025-2026 (latest exploits and novel attack vectors)

### Pattern Generation Super Task (17.22)

| Task | Type | Focus | Status |
|------|------|-------|--------|
| 17.22a | Semantic (Tier A) | Operations, signatures, properties | TODO |
| 17.22b | Library Exact Match | SafeERC20, ReentrancyGuard, ecrecover | TODO |
| 17.22c | LLM Reasoning (Tier B) | Context-aware detection | TODO |

**Pattern Types:**
- **Type 1: Semantic** - Deterministic detection via operations/signatures/properties
- **Type 2: Library Match** - Exact match for known safe/unsafe library methods
- **Type 3: LLM Reasoning** - Context-dependent patterns requiring LLM analysis

### Parallel Subagent Processing (4 Max Concurrent)

| Subagent | Tiers | Sources | Focus |
|----------|-------|---------|-------|
| 17.3-P1 | 1, 2 | 12 | Vuln DBs + Contests |
| 17.3-P2 | 3 | 19 | Audit Firms |
| 17.3-P3 | 4, 5, 6 | 26 | Researchers + Education + CTFs |
| 17.3-P4 | 7-10 | 30 | GitHub + Docs + FV + Emerging |

**Pipeline**: Download → Process → Delete (local cache management)
**Conflict Resolution**: Merge by timestamp, dedupe, highest-value wins

### Protocol-Specific Categories (May CREATE_CATEGORY)

- AMM/DEX vulnerabilities (Curve read-only reentrancy, sandwich attacks)
- Lending vulnerabilities (liquidation cascade, bad debt)
- ERC-4626 vault attacks (share inflation, first depositor)
- Bridge/cross-chain (message replay, sequencer manipulation)
- Account Abstraction ERC-4337 (bundler manipulation, paymaster exploits)
- Restaking/EigenLayer (slashing exploits, AVS security)
- ZK-Rollup specific (prover exploits, escape hatch attacks)

---

## Parallelization Analysis

### Critical Path (Sequential - Cannot Parallelize)

The longest dependency chain determines minimum project duration:

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → [GATE 1]
                                            ↓
                                     Phase 6,7,8 (parallel)
                                            ↓
                                        Phase 9 → Phase 10 → [GATE 2]
                                                        ↓
                                                 Phase 11,12,13 (parallel)
                                                        ↓
                                        Phase 14 → Phase 15 → Phase 16 (RC) → Phase 20 → [GATE 4]
```

**Critical Path Length:** ~450h + Phase 17/18/20 (estimates pending)
**Parallelization Savings:** ~40% time reduction with 2-3 parallel workers

**Additional Track:** Phase 17 → Phase 18 (starts after Phase 9 + Phase 11, must finish before Phase 20)

---

### Parallel Execution Windows

| Window | Phases | Can Run Simultaneously | Dependencies |
|--------|--------|----------------------|--------------|
| **Window 1** | 6, 7, 8 | ✅ YES - All 3 parallel | All need Phase 5 complete |
| **Window 2** | 11, 12, 13 | ✅ YES - All 3 parallel | All need Phase 10 complete |
| **Window 3** | 17 → 18 | ✅ YES - Separate track | Start after Phase 9 + Phase 11 |
| **Window 4** | 16 prep | ⚠️ PARTIAL - Docs only | Can start during Phase 14 |

---

### Detailed Phase Dependencies

#### STRICTLY SEQUENTIAL (Must Wait)

| Phase | Must Wait For | Reason |
|-------|---------------|--------|
| 2 | Phase 1 | Needs detection baseline (84.6%) |
| 3 | Phase 2 | Needs benchmark infrastructure |
| 4 | Phase 3 | Needs CLI commands |
| 5 | Phase 4 | Needs test scaffolding |
| 9 | Phases 6 AND 7 AND 8 | Needs beads, learning, AND metrics |
| 10 | Phase 9 | Needs context optimization |
| 14 | Phases 11 AND 12 AND 13 | Needs LLM, agents, AND grimoires |
| 15 | Phase 14 | Needs calibrated confidence |
| 16 | Phase 15 | Needs integrated solutions |
| 17 | Phases 9 AND 11 | Needs PPR context + LLM provider |
| 18 | Phase 17 | Needs VulnDocs schema |
| 20 | Phases 1-19 | Final testing gate before GA |

#### CAN RUN IN PARALLEL (After Prerequisite)

| After Phase | Parallel Options | Notes |
|-------------|------------------|-------|
| **Phase 5** | 6 ∥ 7 ∥ 8 | All three independent, ~110h work in ~45h wall-clock |
| **Phase 10** | 11 ∥ 12 ∥ 13 | All three independent, ~135h work in ~55h wall-clock |
| **Phase 11 + 9** | 17 → 18 | VulnDocs track can run alongside 14/15 |
| **Phase 14** | 16 docs prep | Start README, guides while 15 runs |

---

### Within-Phase Parallelization

#### Phases with Internal Parallelization

| Phase | Parallel Tasks | Sequential Tasks |
|-------|----------------|------------------|
| **Phase 2** | 2.5, 2.7, 2.8 (after 2.6) | 2.1→2.2→2.3→2.4→2.6 |
| **Phase 3** | 3.2-3.8 (after 3.1) | 3.1 must complete first |
| **Phase 4** | 4.3 ∥ 4.4 ∥ 4.7 ∥ 4.8 (after 4.2) | 4.1→4.2→4.5→4.6→4.9→4.10→4.11 |
| **Phase 5** | 5.3 ∥ 5.4 ∥ 5.6 (after 5.2) | Ground truth must be labeled first |
| **Phase 11** | 11.5 ∥ 11.7 ∥ 11.9 ∥ 11.10 (after 11.1) | Provider abstraction first |
| **Phase 16** | 16.3 ∥ 16.10 ∥ 16.11 (independent) | 16.1→16.2 and 16.4→16.5→16.6 |

---

### Optimal Resource Allocation

#### With 1 Worker (Baseline)
- **Total Time:** ~737h
- **No parallelization possible**

#### With 2 Workers
- **Phase 5→**: Worker 1 does 6, Worker 2 does 7, then 8
- **Phase 10→**: Worker 1 does 11, Worker 2 does 12→13
- **Estimated Savings:** ~150h (20% reduction)

#### With 3 Workers
- **Phase 5→**: Workers 1,2,3 do 6,7,8 simultaneously
- **Phase 10→**: Workers 1,2,3 do 11,12,13 simultaneously
- **Estimated Savings:** ~290h (40% reduction)

---

### Anti-Patterns (DO NOT Parallelize)

| Bad Idea | Why |
|----------|-----|
| 3 ∥ 4 | Phase 4 needs Phase 3 CLI |
| 5 ∥ 6 | Phase 6 needs Phase 5 validation baseline |
| 11 ∥ 14 | Phase 14 needs Phase 11 LLM findings |
| 9 before 6,7,8 | Phase 9 combines all three outputs |
| 16 before 15 | Release requires integrated solutions |
| 20 before 17/18 | Phase 20 requires VulnDocs track completion |
| GA release before 20 | Phase 20 is the final validation gate |

---

## Self-Critique Protocol

**Every task completion requires:**

1. **Validation**: Run against real-world corpus (DVDeFi, audits)
2. **Independent Verification**: Use isolated agent (e.g., `vkg-real-world-auditor`)
3. **Metrics Comparison**: Before/after on key metrics
4. **Regression Check**: No existing tests broken
5. **Iteration**: If validation fails, iterate don't proceed

**Agents for Validation:**
- `vkg-real-world-auditor`: Stress-test BSKG on real contracts
- `pattern-tester`: Calculate precision/recall for patterns
- `solidity-learning-mentor`: Verify investigation steps are educational

---

## Conflict Notes (Implementation)

These conflicts and fixes must be referenced in phase trackers as alignment tasks.

1) Output formats (TOON vs YAML vs JSON)
   - Fix: JSON is canonical; YAML remains optional for human review.
2) Determinism scope vs philosophy
   - Fix: determinism gates apply to Tier A and reproducible manifests only.
3) Evidence packet contract missing in early phases
   - Fix: add evidence packet generation and schema checks as alignment tasks.
4) Phase 17/18 track not integrated into master flow
   - Fix: treat 17/18 as a parallel track that completes before Phase 20.
5) LLM safety controls scheduled too late
   - Fix: add LLM safety and context minimization gates in Phases 3 and 10.
6) Proxy resolution treated as warnings only
   - Fix: enforce ERC-1967 and ERC-2535 resolution as Phase 3 requirements.

---

## Key Decisions

### BSKG Gives Superpowers to LLM Agents
- BSKG is infrastructure FOR Claude Code, Codex, OpenCode, and other AI agents
- CLI interface for Bash invocation by LLMs
- Agent SDKs for parallel verification and specialized subagents
- AGENTS.md for tool discoverability

### Beads: How Agents Get Context

**Every finding comes with a VulnerabilityBead - complete context for investigation:**

```
┌─────────────────────────────────────────────────────────────────┐
│  VULNERABILITY BEAD (per finding)                               │
│                                                                 │
│  CODE CONTEXT: Function source, callers, state variables       │
│  PATTERN CONTEXT: Why flagged, matched properties, evidence    │
│  INVESTIGATION GUIDANCE: Per-category steps to follow          │
│  HISTORICAL EXPLOITS: Real attacks (DAO, Parity, etc.)         │
│  TOOLS: Foundry scaffold, fuzzing config, fork RPC            │
│  TOON FORMAT: 30-50% token reduction for LLM efficiency        │
└─────────────────────────────────────────────────────────────────┘
```

### Grimoires: Per-Vulnerability Testing Playbooks

**Each vulnerability class has a Grimoire = Bead + Tools + Procedure:**

| Category | Grimoire Skill | Tools Used |
|----------|---------------|------------|
| Reentrancy | `/test-reentrancy` | Foundry, fork, Medusa |
| Access Control | `/test-access` | Foundry, fuzz |
| Oracle | `/test-oracle` | Fork, Chainlink mocks |
| DoS | `/test-dos` | Medusa, Echidna |
| MEV | `/test-mev` | Fork, Tenderly simulate |

### Zero-Config Tooling (Ship Ready)

**All testing tools pre-configured, no manual setup:**

- **Frameworks**: Foundry, Hardhat, Medusa, Echidna (auto-installed)
- **Testnets**: Sepolia, Holesky, Base Sepolia, Arbitrum Sepolia (free RPC)
- **MCP Servers**: mcp-foundry, mcp-ethereum, mcp-tenderly (pre-configured)
- **Skills**: `/test-exploit`, `/fuzz`, `/fork-test`, `/deploy-testnet`

### Two-Tier Pattern Architecture
- **Tier A (Strict):** Deterministic, high precision (>90%), match/exceed static tools
- **Tier B (Lax):** High FP rate by design, REQUIRE LLM verification to complete detection
- Tier A catches what static tools catch (but name-agnostic)
- Tier B catches what static tools CANNOT: business logic, economic attacks, nuanced access control
- The tiers are NEVER conflated

### Multi-Agent Debate Framework
- Attacker/Defender/Verifier/Arbiter personas debate uncertain findings
- Disagreement is information, not failure - document for human review
- Use Agent SDK for parallel model execution (Claude, Codex, free models)
- Each agent receives full Bead context in TOON format

### Human Escalation Protocol
- LLMs admit uncertainty (not 100% sure = don't assert certainty)
- "Gut feeling" is valid output
- Escalate to human with full context when uncertain
- Never black/white - nuance matters

### Conservative Learning
- OFF by default
- Bounded confidence adjustments
- Rollback on degradation
- A/B testing before production

### TOON: Token-Optimized Output
- Beads output in TOON format by default for LLM consumption
- 30-50% token reduction without losing semantic content
- Full JSON available for tools/APIs that need it

---

## Global Decision Gates

**These are GO/NO-GO checkpoints. If criteria not met, STOP and re-evaluate.**

### Gate 1: After Phase 5 (Real-World Validation)

| Criteria | Threshold | Action if Failed |
|----------|-----------|------------------|
| Real-world precision | >= 70% | Stop. Fix detection before proceeding. |
| FP rate | < 30% | Stop. Add discriminators to patterns. |
| Auditor verdict | "Has potential" or better | Stop. Get more feedback, understand why. |
| Builder.py failure rate | < 20% on 100 real contracts | Stop. Fix builder.py bugs. |

### Gate 2: After Phase 10 (Graceful Degradation)

| Criteria | Threshold | Action if Failed |
|----------|-----------|------------------|
| User testing | >= 3 users have tried BSKG | Pivot. Focus on distribution/discoverability. |
| CLI usability | "Intuitive" rating | Iterate CLI before LLM integration. |
| Task persistence | Works across sessions | Fix Beads before LLM depends on it. |

### Gate 3: After Phase 11/12/13 (LLM + Agents + Grimoires)

| Criteria | Threshold | Action if Failed |
|----------|-----------|------------------|
| Tier B precision improvement | >= 10% over Tier A alone | Cut scope. Tier B becomes optional "premium". |
| Cost per audit | < $2.00 | Optimize prompts or reduce LLM usage. |
| Multi-agent value | Debate reduces FP by 15% | Simplify to single-agent verification. |

### Gate 4: After Phase 20 (Final Testing Phase)

| Criteria | Threshold | Action if Failed |
|----------|-----------|------------------|
| Real-world dossier complete | 100% | Halt GA release and finish dossier |
| Evidence packet completeness | >= 95% | Fix exporter and re-run validation |
| Dispute backlog | 0 unresolved criticals | Extend debate and human review |

---

## Priority Gates

*Source: CRITIQUE-INTEGRATION.md*

### MUST (Blockers for Production Readiness)

| # | Requirement | Phase | Tracker |
|---|-------------|-------|---------|
| 1 | Rename-resistance test harness | 1.B.1 | `phase-1/TRACKER.md` |
| 2 | Graph fingerprinting for CI | 1.B.2-3 | `phase-1/TRACKER.md` |
| 3 | SmartBugs curated dataset | 2.7 | `phase-2/TRACKER.md` |
| 4 | Safe set for FP measurement | 2.8 | `phase-2/TRACKER.md` |
| 5 | Analysis completeness report | 2.10 | `phase-2/TRACKER.md` |
| 6 | Output schema versioning | 3.9 | `phase-3/TRACKER.md` |
| 7 | Proxy resolution/warnings | 3.13 | `phase-3/TRACKER.md` |
| 8 | Builder change protocol | 1.A.1-3 | `phase-1/TRACKER.md` |
| 9 | Evidence-first finding output | 3.14 | `phase-3/TRACKER.md` |
| 10 | Verification loop closure | 4.9-11 | `phase-4/TRACKER.md` |

**Determinism**: Rename-resistance tests + graph fingerprints gating CI
**Analysis completeness**: Coverage report + failure modes per run
**Stable outputs**: SARIF/JSON schemas, stable IDs, location accuracy
**Proxy/upgradeability**: Resolve or flag; never silent
**Benchmarks**: DVDeFi + SmartBugs + safe set with tracked FPs

### SHOULD (Needed for Strong Usability)

| # | Requirement | Phase | Tracker |
|---|-------------|-------|---------|
| 11 | Orchestrator mode (Slither/Aderyn dedup) | 5.8 | `phase-5/TRACKER.md` |
| 12 | LLM prompt contract with schema validation | 11.8 | `phase-11/TRACKER.md` |
| 13 | Performance budgets with baselines | 8.8-10 | `phase-8/TRACKER.md` |
| 14 | 6-project minimum validation | 5.9 | `phase-5/TRACKER.md` |
| 15 | LLM safety guardrails | 11.7 | `phase-11/TRACKER.md` |
| 16 | Tier labels in output | 3.10 | `phase-3/TRACKER.md` |
| 17 | Offline mode | 16.10 | `phase-16/TRACKER.md` |
| 18 | Deterministic dependency pinning | 16.11 | `phase-16/TRACKER.md` |
| 19 | Pattern pack versioning | 16.12 | `phase-16/TRACKER.md` |

**Orchestrator mode**: Dedup vs Slither/Aderyn, disagreement labeling
**LLM runbook**: Evidence-first output, tier separation
**Performance budgets**: Tied to measured baselines

### COULD (Nice-to-Have)

| # | Requirement | Phase | Tracker |
|---|-------------|-------|---------|
| 19 | JSONL streaming output | 3 | - |
| 20 | Pattern pack versioning | 2-3 | - |
| 21 | Build failure diagnostics | 3.12 | `phase-3/TRACKER.md` |
| 22 | Ownership model (CODEOWNERS) | 16 | - |

---

## Production Readiness Integration (2026-01-07)

*Source: `REVIEW-INTEGRATION.md` - Critical analysis of `task/codex/vkg_4_0_production_readiness_review.md`*

### New Tasks Added

| Task ID | Description | Phase | Priority |
|---------|-------------|-------|----------|
| **1.C.4** | Build Manifest (`build_manifest.json`) | 1 | MUST |
| **1.A.4** | Property Schema Contract | 1 | MUST |
| **2.0** | Benchmark Provenance (`PROVENANCE.md`) | 2 | MUST |
| **2.10+** | Feature-Level Coverage Map | 2 | MUST |
| **3.13+** | Full Proxy Resolution (EIP-1967, beacon, diamond) | 3 | MUST |
| **3.15** | Stable Finding IDs | 3 | MUST |
| **3.16** | Pattern Taxonomy Mapping (SWC, DASP, CWE) | 3 | SHOULD |
| **4.12** | Scaffold Risk Tags | 4 | SHOULD |
| **5.10** | Audit Pack/Diff Commands | 5 | SHOULD |
| **9.8** | TOON Format for LLM Output | 9 | SHOULD |
| **11.12** | Multi-Tier Model Support (Claude SDK + Codex SDK + OpenCode SDK) | 11 | SHOULD |
| **12.8** | LLM Subagent Orchestration Manager | 12 | SHOULD |

### Key Additions

1. **Build Manifest**: Environment locking for determinism
2. **Property Schema Contract**: Prevent silent semantic drift in builder.py
3. **TOON Format**: Token-efficient LLM output (30-50% reduction)
4. **Multi-Provider SDK**: Claude + Codex + OpenCode with cheap/medium/expensive tiers
5. **Subagent Orchestration**: Task-appropriate routing to models
6. **OpenCode SDK Support**: 75+ LLM providers via single interface (https://opencode.ai/docs/sdk/)
7. **Codex SDK Support**: Thread-based stateful analysis (https://developers.openai.com/codex/sdk/)
8. **Codex Noninteractive**: `codex exec` for CI/CD pipelines with `--output-schema` (https://developers.openai.com/codex/noninteractive)

### Agent Integration Model

**VKG is infrastructure FOR AI agents. Flexible routing determines WHO spawns subagents.**

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI CODING AGENTS                              │
│  (Claude Code, Codex, OpenCode, Cursor, etc.)                   │
│                                                                  │
│  Invoke BSKG via Bash: `vkg build`, `vkg analyze`, etc.          │
│  Discover tools via: AGENTS.md                                   │
│  Parse output: JSON/SARIF                                        │
└─────────────────────────┬───────────────────────────────────────┘
                          │
          ┌───────────────┴───────────────┐
          │                               │
          ▼                               ▼
┌─────────────────────┐         ┌─────────────────────┐
│  ROUTE A: Parent    │         │  ROUTE B: BSKG       │
│  Agent Spawns       │         │  Spawns Subagents   │
│                     │         │                     │
│  When better:       │         │  When better:       │
│  • Agent has full   │         │  • BSKG has graph    │
│    conversation     │         │    context ready    │
│    context          │         │  • Parallel batch   │
│  • User interaction │         │    verification     │
│    needed           │         │  • Specialized      │
│  • Complex multi-   │         │    security tasks   │
│    step reasoning   │         │  • Test generation  │
│  • Orchestration    │         │    with fixtures    │
│    decisions        │         │  • CI/CD pipelines  │
└─────────────────────┘         └─────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BSKG CLI (Tier A Core)                         │
│  Deterministic detection • Evidence-first findings              │
│  Behavioral signatures • Graph context                          │
└─────────────────────────────────────────────────────────────────┘
```

**SDKs for spawning (all have built-in subscriptions):**
- Claude Agent SDK: `anthropic.com/docs/agent-sdk`
- Codex SDK: `developers.openai.com/codex/sdk/`
- OpenCode SDK: `opencode.ai/docs/sdk/`
- Noninteractive: `codex exec --output-schema` for CI/CD

**Dynamic Routing Principles:**
1. **No API keys in VKG** - SDKs inherit parent's subscription
2. **Smart routing** - System chooses based on context and performance
3. **Either can spawn** - Parent agent OR VKG, whichever is better for the task
4. **Fallback gracefully** - If one route fails, try the other

---

## Threat Model

### Attack Surfaces BSKG Must Address

| Attack Surface | Description | Key Patterns |
|----------------|-------------|--------------|
| **Access control failures** | Missing or bypassable authorization gates | auth-*, vm-* |
| **External call risks** | Reentrancy, callbacks, delegatecall abuse | reentrancy-*, proxy-* |
| **Oracle manipulation** | Stale or manipulable price feeds | oracle-* |
| **MEV and ordering** | Sandwich, backrun, forced ordering assumptions | mev-* |
| **Governance capture** | Timelock bypass, voting power inflation | governance-* |
| **Upgradeability abuse** | Proxy/implementation mismatch, initializer misuse | upgrade-* |
| **Tokenomics flaws** | Inflation bugs, fee miscalculation, rounding | token-* |
| **Denial of service** | Unbounded loops, gas griefing, block dependence | dos-* |

### Non-Goals (Must Report as Unsupported)

- **Inline assembly/Yul**: Partially modeled, flagged in completeness report
- **Purely off-chain operational compromise**: No on-chain or documented
  evidence (key theft, infra breach, social engineering)

Off-chain inputs and economic assumptions are modeled via protocol context
packs and surfaced as assumption-risk when unverified.

### Threat-Model-Driven Acceptance

- Each attack surface MUST map to at least one deterministic pattern
- Each category MUST have at least one "safe set" contract
- New patterns MUST specify which threat they address

---

## Success Metrics

### Accuracy

| Metric | Target | Minimum |
|--------|--------|---------|
| DVDeFi Detection | >= 80% | 70% |
| SmartBugs Detection | >= 70% | 60% |
| False Positive Rate | < 15% | < 25% |
| Scaffold Compile Rate | >= 60% | 40% |
| LLM Verdict Accuracy (with Bead) | >= 80% | 70% |
| Real-World Auditor Feedback | "Useful" | "Has potential" |

### Determinism

| Metric | Target | Validation |
|--------|--------|------------|
| Rename Invariance | 100% | Harness test in CI |
| Graph Fingerprint Stability | 100% | Same code = same fingerprint |

### Performance

| Metric | Target | Maximum |
|--------|--------|---------|
| Build Time / 10k LOC | <= 2 min | 3 min |
| Query Latency | <= 2 sec | 5 sec |
| Memory Usage / 10k LOC | <= 1 GB | 2 GB |

### Usability

| Metric | Target |
|--------|--------|
| SARIF GitHub Validation | Pass |
| Analysis Completeness Report | Every run |
| JSON Schema Validation | 100% outputs validated |
| Proxy Resolution | Resolved or warned |

---

## Quick Commands

```bash
# Run tests
uv run pytest tests/ -v

# Build graph
vkg build path/to/contracts/

# Analyze
vkg analyze

# Benchmark
vkg benchmark run --suite dvd

# Compare to baseline
vkg benchmark compare --baseline main
```

---

## VulnDocs + Final Testing Track

This track starts after Phase 9 + Phase 11 and must complete before Phase 20.

- **Phase 17:** VulnDocs knowledge schema (`phases/phase-17/TRACKER.md`)
- **Phase 18:** VulnDocs mining + retrieval (`phases/phase-18/TRACKER.md`)
- **Phase 20:** Final testing phase (`phases/phase-20/TRACKER.md`)
- **Master Plan:** `task/4.0/phases/phase-20/INDEX.md`

---

## Archive

Previously documented content moved to `archive/`:
- `archive/analysis-docs/` - Risk analysis, best practices
- `archive/premature-phases/` - Original detailed phase designs

The archive contains **valuable reference material** - designs, research, and analysis that inform the current implementation.

---

## Daily Checklist

```
Morning:
[ ] What phase am I in?
[ ] What task am I working on?
[ ] What's the validation criteria?

During Work:
[ ] Make ONE change
[ ] Run validation
[ ] If fails: iterate, don't proceed
[ ] If passes: update tracker

End of Day:
[ ] Update phase tracker
[ ] Note any blockers
[ ] What's tomorrow's target?
```

---

*Roadmap Version: 4.3 (Alignment sweep + Phase 20 gate integrated)*
*Previous: 4.2 (19 phases + Real-World Agentic Validation)*
*Current: Full roadmap with Priority Gates, VulnDocs track integration, and alignment sweep*
*Production Readiness Integration: 2026-01-07*
*Integration Document: `REVIEW-INTEGRATION.md`*
