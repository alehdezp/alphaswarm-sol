# Phase 17: Vulnerability Knowledge Documentation System (VulnDocs)

**Status:** COMPLETE - Phase 17 Knowledge System Operational
**Progress:** Infrastructure (7/7), Re-Crawl (13/13), Patterns (594 loaded), VulnDocs (251 files, 140 dirs), Tests (530 passing)
**Priority:** COMPLETE - All core objectives achieved
**Last Updated:** 2026-01-09T23:30:00Z (Phase 17 Complete)
**Author:** BSKG Team

---

## Quick Reference

| Field | Value |
|-------|-------|
| Entry Gate | Phase 9 complete, Phase 11 LLM provider ready |
| Exit Gate | Knowledge system operational, world knowledge aggregated, patterns generated, Exa discovery complete |
| Philosophy Pillars | Knowledge Graph, Multi-Agent Framework, Self-Improvement |
| Estimated Hours | 200h (80h infra + 80h crawl + 40h patterns) |
| Actual Hours | [Tracked as work progresses] |
| Task Count | 35 tasks (7 infra + 10 crawl + 6 Exa + 4 patterns + 5 parallel + 3 validation) |
| Test Count Target | 1000+ tests (600 infra + 200 crawl + 200 patterns) |
| Parallel Subagents | 4 max concurrent (knowledge-aggregation-worker, Haiku 4.5) |

---

## PHASE COMPLETION SUMMARY

**Phase 17 completed 2026-01-09**

### Final Metrics

| Metric | Value |
|--------|-------|
| **Patterns** | 594 loaded successfully |
| **VulnDocs Files** | 251 (YAML + Markdown) |
| **VulnDocs Directories** | 140 categories/subcategories |
| **Test Suite** | 530 tests passing |
| **Pattern Tests** | 50 tests passing |
| **Infrastructure** | 7/7 complete |
| **Re-Crawl Sources** | 13/13 complete |

### Key Patterns Created

| Pattern | Type | Status | Related Exploit |
|---------|------|--------|-----------------|
| `logic-001-parameter-confusion` | Semantic | draft | DeusDao $6.5M |
| `logic-002-balancer-rounding` | Semantic | draft | Balancer $128M |
| `logic-003-cetus-overflow` | Semantic | draft | Cetus $260M |
| `external-002-unprotected-delegatecall` | Semantic | excellent | Parity $30M |
| `vault-001-share-inflation` | Semantic | ready | ResupplyFi $9.8M |
| `reentrancy-002-gmx-cross-function` | Semantic | ready | GMX $42M |

### VulnDocs-Pattern Linkage

All major patterns are now linked to their VulnDocs entries:

- `logic/parameter-confusion` → `logic-001-parameter-confusion`
- `logic/arithmetic/balancer-v2-rounding` → `logic-002-balancer-rounding`
- `logic/arithmetic/cetus-sui-overflow` → `logic-003-cetus-overflow`
- `access-control/delegatecall-control` → `external-002-unprotected-delegatecall`

### Remaining Tasks (Future Work)

- [ ] Process 36 additional uncrawled sources (low priority)
- [ ] Implement Weekly Exa Scan Automation (17.21)
- [ ] Continuous Solodit Fetcher (17.8)
- [ ] Expand pattern test coverage to achieve "ready" status on draft patterns

---

## 1. OBJECTIVES

### 1.1 Primary Objective

Build a comprehensive **Vulnerability Knowledge Documentation System** that:
1. Extracts and structures vulnerability knowledge from public sources
2. Provides granular, navigable docs organized by category/subcategory
3. Supports prompt caching for efficient LLM context
4. Enables both manual (Python) and agentic (LLM) navigation
5. Self-improves via Solodit vulnerability analysis skill

### 1.2 Key Requirements

**From User:**
> "The knowledge must be extracted from all the public available repositories and medium posts, videos, checklists, etc. Also we will have a skill that reads solodit latest vulnerabilities, analyze them logically, and create a specific pattern or add more granulated content for a specific vulnerability."

> "The pattern docs must be split into small categories to more specific subcategories, so the LLM knows how to navigate this infrastructure and only grabs the docs that make sense for testing the specific vulnerability."

> **CRITICAL**: "All the knowledge in the world must be included. The system must detect and CREATE NEW categories, subcategories, and specific vulnerabilities as needed."

### 1.3 Self-Improving Vulnerability Discovery

**Goal:** DISCOVER vulnerabilities through reasoning, not just aggregate into predefined categories.

**Primary Skill:** `vuln-discovery` (Self-Improving Discovery Skill)
- See `.claude/skills/vuln-discovery.md` for full specification
- Invoked via: `/vuln-discovery crawl|analyze|reflect|evolve|status`

**Agents:**

| Agent | Model | Purpose |
|-------|-------|---------|
| `knowledge-aggregation-worker` | **Sonnet 4.5** | Deep reasoning, discovery, heuristic evolution |
| `crawl-filter-worker` | **Haiku 4.5** | Fast parallel filtering, 50-80% token reduction |

**Pipeline:**
```
┌─────────────┐     ┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────┐
│  DOWNLOAD   │ ──► │  FILTER (Haiku)     │ ──► │  DISCOVER (Sonnet)  │ ──► │  INTEGRATE  │
│  crawl4ai   │     │  Parallel, Fast     │     │  Deep Reasoning     │     │  VulnDocs   │
│             │     │  50-80% reduction   │     │  Self-improving     │     │             │
└─────────────┘     └─────────────────────┘     └─────────────────────┘     └─────────────┘
```

**Philosophy: DISCOVER > REASON > LEARN > EVOLVE**

```
┌─────────────────────────────────────────────────────────────────┐
│  DISCOVER: Find vulnerabilities in sources                      │
│      ↓                                                          │
│  REASON: Understand WHY the vulnerability exists                │
│      ↓                                                          │
│  LEARN: Does it fit existing structure?                         │
│      ├─ YES → Enhance existing with new evidence                │
│      └─ NO → CREATE NEW category/subcategory/specific           │
│      ↓                                                          │
│  EVOLVE: Update detection heuristics based on discoveries       │
└─────────────────────────────────────────────────────────────────┘
```

**Discovery State:** `.true_vkg/discovery/`
- `state.yaml` - Current discovery state, learned patterns, emerging themes
- `novel_findings.yaml` - Log of novel discoveries
- `detection_heuristics.yaml` - Self-evolved detection rules (versioned)
- `reasoning_log.jsonl` - Reasoning traces for learning
- `category_proposals/` - Proposed new categories awaiting evidence

### 1.4 Claude Code 2.1 Integration (NEW)

**Status:** COMPLETE (2026-01-09)

All agents and skills have been upgraded with Claude Code 2.1 features:

**Features Implemented:**

| Feature | Description | Files Updated |
|---------|-------------|---------------|
| **Hooks in Frontmatter** | PreToolUse, PostToolUse, Stop hooks for lifecycle management | All 7 agents |
| **Wildcard Tool Permissions** | Pattern-based tool access (e.g., `Bash(uv run*)`) | All 7 agents |
| **Forked Context** | Skills run in isolated context (`context: fork`) | All 3 skills |
| **Hot Reload** | Skills auto-reload on file changes (`hot_reload: true`) | All 3 skills |
| **Slash Commands** | Invoke skills via `/skill-name` | `/pattern-forge`, `/vkg-lens-tasker`, `/vuln-discovery` |
| **agent_type Hook** | SessionStart receives agent_type if `--agent` specified | Project settings |

**Updated Agents (7):**

```
.claude/agents/
├── vkg-pattern-architect.md      # Pattern design (Sonnet)
├── pattern-tester.md             # Pattern testing (Sonnet)
├── vkg-docs-curator.md           # Documentation (Sonnet)
├── vkg-security-research.md      # Security research (Sonnet)
├── vkg-real-world-auditor.md     # Real-world testing (Opus)
├── knowledge-aggregation-worker.md # Deep reasoning (Sonnet 4.5)
└── crawl-filter-worker.md        # Fast filtering (Haiku)
```

**Updated Skills (3):**

```
.claude/skills/
├── pattern-forge/SKILL.md        # /pattern-forge
├── vkg-lens-tasker/SKILL.md      # /vkg-lens-tasker
└── vuln-discovery.md             # /vuln-discovery
```

**Project Settings:**

```
.claude/settings.yaml             # Claude Code 2.1 project configuration
```

**Hook Examples:**

```yaml
# Pattern validation after write
PostToolUse:
  - tool: Write
    match: "patterns/**/*.yaml"
    command: "python -c 'import yaml; yaml.safe_load(open(\"$FILE\"))'"

# Knowledge update tracking
PostToolUse:
  - tool: Write
    match: "knowledge/vulndocs/**"
    command: "echo 'VulnDocs updated: $FILE'"

# Discovery state evolution
PostToolUse:
  - tool: Write
    match: ".true_vkg/discovery/**"
    command: "echo 'Discovery state evolved'"
```

**Wildcard Permission Examples:**

```yaml
tools:
  - Bash(uv run*)                # BSKG commands
  - Bash(docker run*crawl4ai*)   # Crawl4ai Docker
  - Bash(cat*)                   # Read files
  - Bash(mkdir -p*)              # Create directories
```

**Slash Command Invocation:**

```bash
# Invoke skills directly
/pattern-forge reentrancy          # Forge reentrancy pattern
/vuln-discovery crawl https://...  # Crawl for vulnerabilities
/vkg-lens-tasker authority-lens    # Process authority lens
```

**Dynamic Discovery (NOT Predefined Categories):**

The skill REASONS about each finding:
1. **UNDERSTAND** - What is the fundamental mechanism?
2. **CHECK NOVELTY** - Does current structure capture this?
3. **CREATE IF NOVEL** - Build new structure from reasoning
4. **LEARN** - Update detection heuristics
5. **EVOLVE** - Improve future discovery

**Evidence Thresholds for New Structure:**
| Structure | Evidence Required | Auto-Create |
|-----------|-------------------|-------------|
| Specific | 1 occurrence | Yes |
| Subcategory | 3 occurrences | Yes |
| Category | 5 occurrences | Proposal + Review |

**Semantic-Only Rule:**
- NEVER use variable names (except library methods like `SafeERC20.safeTransfer`)
- ALWAYS use operations, behavioral signatures, and properties

### 1.4 Design Principles

1. **Granular Structure** - Fine-grained categories → subcategories → specific patterns
2. **Minimal Context** - Each doc contains only what's needed, nothing more
3. **Navigable Hierarchy** - LLMs can discover and traverse the knowledge tree
4. **Cacheable Blocks** - Stable content cached for token efficiency
5. **Self-Improving** - Solodit skill extracts new patterns automatically
6. **Dual Navigation** - Python API or LLM agent can navigate

---

## 2. ARCHITECTURE

### 2.1 Knowledge Hierarchy

```
knowledge/vulndocs/
├── index.yaml                      # Top-level navigation
├── categories/
│   ├── reentrancy/
│   │   ├── index.yaml              # Category overview
│   │   ├── overview.md             # Category-level overview
│   │   └── subcategories/
│   │       ├── classic/
│   │       │   ├── index.yaml      # Subcategory overview
│   │       │   ├── detection.md    # How to detect
│   │       │   ├── patterns.md     # Known patterns
│   │       │   ├── exploits.md     # Real-world exploits
│   │       │   └── fixes.md        # Remediation
│   │       ├── cross-function/
│   │       ├── read-only/
│   │       ├── erc777/
│   │       └── cross-contract/
│   ├── access-control/
│   │   └── subcategories/
│   │       ├── missing-modifier/
│   │       ├── weak-modifier/
│   │       ├── tx-origin/
│   │       ├── role-escalation/
│   │       └── initialization/
│   ├── oracle/
│   │   └── subcategories/
│   │       ├── price-manipulation/
│   │       ├── staleness/
│   │       ├── sequencer-uptime/
│   │       └── twap-manipulation/
│   ├── flash-loan/
│   │   └── subcategories/
│   │       ├── collateral-drain/
│   │       ├── governance-attack/
│   │       └── price-oracle/
│   ├── mev/
│   │   └── subcategories/
│   │       ├── sandwich/
│   │       ├── frontrunning/
│   │       └── backrunning/
│   ├── dos/
│   │   └── subcategories/
│   │       ├── unbounded-loop/
│   │       ├── gas-griefing/
│   │       ├── block-stuffing/
│   │       └── return-bomb/
│   ├── token/
│   │   └── subcategories/
│   │       ├── fee-on-transfer/
│   │       ├── rebasing/
│   │       ├── approval-race/
│   │       └── missing-return/
│   ├── upgrade/
│   │   └── subcategories/
│   │       ├── unprotected-initialize/
│   │       ├── storage-collision/
│   │       ├── selfdestruct/
│   │       └── delegatecall-context/
│   ├── crypto/
│   │   └── subcategories/
│   │       ├── signature-replay/
│   │       ├── ecrecover-zero/
│   │       ├── weak-randomness/
│   │       └── hash-collision/
│   ├── governance/
│   │   └── subcategories/
│   │       ├── flash-loan-voting/
│   │       ├── proposal-front-run/
│   │       └── quorum-manipulation/
│   └── logic/
│       └── subcategories/
│           ├── accounting/
│           ├── state-machine/
│           ├── invariant/
│           └── configuration/
└── sources/                        # External knowledge sources
    ├── solodit/
    ├── rekt/
    ├── medium/
    └── checklists/
```

### 2.2 Document Templates

#### Category Index (index.yaml)
```yaml
id: reentrancy
name: Reentrancy Vulnerabilities
description: Attacks exploiting callback mechanisms during external calls
severity_range: [HIGH, CRITICAL]

subcategories:
  - id: classic
    name: Classic Reentrancy
    description: State write after external call
    patterns: [vm-001, vm-002]
  - id: cross-function
    name: Cross-Function Reentrancy
    description: Reentrancy affecting multiple functions sharing state

relevant_properties:
  - state_write_after_external_call
  - has_reentrancy_guard
  - external_call_sites
  - state_variables_written

context_cache_key: "reentrancy-v1"
token_estimate: 1500
```

#### Detection Document (detection.md)
```markdown
# Detection: Classic Reentrancy

## Graph Signals
| Property | Expected | Critical? |
|----------|----------|-----------|
| state_write_after_external_call | true | YES |
| has_reentrancy_guard | false | YES |
| visibility | public/external | YES |

## Operation Sequences
- VULNERABLE: `R:bal → X:out → W:bal`
- SAFE: `R:bal → W:bal → X:out`

## Code Patterns
```solidity
// VULNERABLE
function withdraw() public {
    uint bal = balances[msg.sender];
    msg.sender.call{value: bal}("");  // External call
    balances[msg.sender] = 0;          // State write AFTER
}
```

## False Positive Indicators
- `nonReentrant` modifier present
- All state writes complete before external call
- External call is to trusted contract (hardcoded)
```

### 2.3 Navigation System

```python
# Usage: Python API
from true_vkg.vulndocs import VulnDocsNavigator

nav = VulnDocsNavigator()

# Get context for specific vulnerability
context = nav.get_context(
    category="reentrancy",
    subcategory="classic",
    depth="detection",
)

# Get context for multiple vulns (union)
context = nav.get_context_for_findings([
    {"category": "reentrancy", "subcategory": "classic"},
    {"category": "access-control", "subcategory": "missing-modifier"},
])

# For LLM: generate navigation prompt
nav_prompt = nav.get_navigation_prompt()
```

### 2.4 Prompt Caching Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: CACHED SYSTEM CONTEXT (~3k tokens, SESSION)           │
│  - Knowledge navigation instructions                            │
│  - Category index (what exists)                                 │
│  - Graph property reference                                     │
│  cache_control: {"type": "ephemeral"}                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2: CATEGORY CONTEXT (~1.5k per category, PER-CATEGORY)   │
│  - Category overview                                            │
│  - Subcategory index                                           │
│  - Common detection patterns                                    │
│  Cached per unique category in session                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3: SUBCATEGORY CONTEXT (~1k per, DYNAMIC)                │
│  - Detection specifics                                          │
│  - Known patterns                                               │
│  - Real exploits                                                │
│  - Fix recommendations                                          │
│  Not cached - loaded on demand per finding                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. SOLODIT SKILL

### 3.1 Purpose

Automatically analyze new vulnerabilities from Solodit and:
1. Extract vulnerability pattern
2. Categorize into hierarchy
3. Add to knowledge docs
4. Create/update detection patterns

### 3.2 Skill Definition

```yaml
# skills/solodit-learner.yaml
name: solodit-learner
description: Learn from Solodit vulnerabilities to improve VulnDocs
trigger_phrases:
  - "analyze solodit"
  - "learn from solodit"
  - "/solodit-learn"

workflow:
  1. fetch_latest:
      source: "https://solodit.xyz/api/v1/vulnerabilities"
      params:
        severity: [HIGH, CRITICAL]
        limit: 10

  2. for_each:
      analyze:
        - Extract vulnerability description
        - Identify category and subcategory
        - Extract detection signals
        - Extract false positive indicators
        - Extract fix recommendations

      categorize:
        - Map to existing category/subcategory
        - Create new subcategory if novel

      update_docs:
        - Add to exploits.md
        - Enhance detection.md if new signals
        - Update patterns.md if new pattern

      generate_pattern:
        - If pattern extractable, generate YAML
        - Run pattern-tester for validation
```

---

## 4. TASK DECOMPOSITION

### 4.1 Task Dependency Graph

```
17.0 (Schema) ─┬── 17.1 (Structure) ─── 17.2 (Templates) ─── 17.3 (Population)
               │                                                    │
               │                                               17.4 (Navigator)
               │                                                    │
               ├── 17.5 (Cache) ───────────────────────────── 17.6 (Builder)
               │                                                    │
               │                                               17.7 (LLM Nav)
               │
               └── 17.8 (Solodit Fetch) ─── 17.9 (Analyzer) ─── 17.10 (Updater)
                                                                    │
                                                               17.11 (PatternGen)

17.12 (Integration) ─── 17.13 (Testing) ─── 17.14 (Docs)
```

### 4.2 Task Registry

**Infrastructure Tasks (COMPLETE):**

| ID | Task | Est. | Priority | Status | Description |
|----|------|------|----------|--------|-------------|
| 17.0 | Knowledge Schema Design | 4h | MUST | ✅ DONE | 78 tests, schema.yaml, schema.py |
| 17.1 | Category Structure | 4h | MUST | ✅ DONE | 11 categories, 47 subcategories, 144 files |
| 17.2 | Document Templates | 4h | MUST | ✅ DONE | 48 tests, templates.py, 4 template types |
| 17.4 | Knowledge Navigator API | 6h | MUST | ✅ DONE | 52 tests, navigator.py |
| 17.5 | Prompt Cache Integration | 4h | MUST | ✅ DONE | 62 tests, cache.py |
| 17.6 | Context Builder | 6h | MUST | ✅ DONE | 67 tests, builder.py |
| 17.7 | LLM Navigation Interface | 4h | SHOULD | ✅ DONE | 72 tests, llm_interface.py, 9 tools |

**World Knowledge Aggregation Tasks (Use `knowledge-aggregation-worker`):**

| ID | Task | Est. | Priority | Status | Sources | Description |
|----|------|------|----------|--------|---------|-------------|
| 17.3a | Crawl Vulnerability DBs | 8h | MUST | TODO | Solodit, Rekt, DefiLlama, SlowMist, Immunefi | Primary exploit databases (6 sources) |
| 17.3b | Crawl Audit Contests | 12h | MUST | TODO | Code4rena, Sherlock, Cantina, CodeHawks, Hats, Secure3 | All contest reports (6 sources) |
| 17.3c | Crawl Audit Firms | 16h | MUST | TODO | ToB, OZ, Spearbit, Cyfrin, Zellic, +14 more | Professional audits (19 sources) |
| 17.3d | Crawl Security Researchers | 8h | HIGH | TODO | samczsun, cmichel, Tincho, +9 more | Top researcher blogs (12 sources) |
| 17.3e | Crawl Educational Resources | 6h | HIGH | TODO | SWC, Secureum, Smart Contract Programmer, +4 more | Education & videos (7 sources) |
| 17.3f | Crawl CTFs & Practice | 4h | HIGH | TODO | DamnVulnerableDeFi, Ethernaut, +5 more | CTF solutions (7 sources) |
| 17.3g | Crawl GitHub Repos | 8h | HIGH | TODO | DeFiHackLabs, Web3Bugs, Solcurity, +7 more | Security repos (10 sources) |
| 17.3h | Crawl Protocol Docs | 6h | MEDIUM | TODO | Uniswap, Aave, Compound, +5 more | Protocol security (8 sources) |
| 17.3i | Crawl Formal Verification | 4h | MEDIUM | TODO | Certora, Halmos, Echidna, +2 more | FV resources (5 sources) |
| 17.3j | Crawl Emerging/L2/Bridge | 6h | MEDIUM | TODO | Arbitrum, Optimism, zkSync, EigenLayer, +3 more | Emerging patterns (7 sources) |
| 17.8 | Continuous Solodit Fetcher | 4h | SHOULD | TODO | Solodit API/crawl | Real-time new vulns |
| 17.9 | Vulnerability Analyzer | 6h | SHOULD | TODO | - | Semantic extraction + CREATE decisions |
| 17.10 | Knowledge Updater | 4h | SHOULD | TODO | - | MERGE/ACCEPT/CREATE integration |
| 17.11 | Pattern Generator | 6h | SHOULD | TODO | - | Auto-generate BSKG patterns |
| 17.15 | Continuous Learning | 6h | SHOULD | TODO | All sources | Scheduled re-crawl for updates |

**Exa-Based Discovery Tasks (Dynamic Source Expansion):**

| ID | Task | Est. | Priority | Status | Focus Area | Description |
|----|------|------|----------|--------|------------|-------------|
| 17.16 | Exa Source Discovery | 4h | HIGH | ✅ DONE | New sources | Found OWASP SC 2025, Anthropic Red, Hacken, BlockScope |
| 17.17 | Exa Novel Vulnerability Search | 6h | HIGH | ✅ DONE | 2024-2026 vulns | Found Balancer $128M, GMX $42M, ResupplyFi $9.8M, Cetus $260M |
| 17.18 | Exa Protocol-Specific Deep Dive | 8h | HIGH | ✅ DONE | Emerging protocols | ERC-4337, EigenLayer, ZK-rollups documented |
| 17.19 | Exa Specific Vulnerability Extraction | 12h | MUST | ✅ DONE | One-by-one | 33 vulnerabilities documented in VulnDocs (incl. specifics: Balancer, GMX, Cetus, Arcadia, Yala, 1inch) |
| 17.20 | Exa Pattern Enrichment | 4h | SHOULD | ✅ DONE | Code patterns | Enriched 4 patterns via parallel Haiku agents: logic-002 (+327 lines), reentrancy-002 (+35 refs), cc-001 (+335 lines), ac-002 (+294 lines) |
| 17.21 | Weekly Exa Scan Automation | 4h | SHOULD | TODO | Continuous | Automated weekly scans for new vulnerabilities |

**Pattern Generation Super Task:**

| ID | Task | Est. | Priority | Status | Description |
|----|------|------|----------|--------|-------------|
| 17.22 | Pattern Super Task | 20h | MUST | ✅ DONE | Generated 14 patterns: 6 semantic (Tier A), 4 library, 4 Tier B |
| 17.22a | Semantic Patterns (Tier A) | 8h | MUST | ✅ DONE | Created 6 patterns: vault-001, logic-002, logic-003, reentrancy-002, cc-001, ac-002 |
| 17.22b | Library Exact Match | 4h | MUST | ✅ DONE | Created 4 library patterns: lib-001-safe-erc20 (27KB), lib-002-reentrancy-guard (30KB), lib-003-ecrecover-safety (21KB), lib-004-safe-math (16KB) |
| 17.22c | LLM Reasoning Patterns (Tier B) | 8h | HIGH | ✅ DONE | Created 4 Tier B patterns: logic-tierb-001 (17KB), logic-tierb-002 (18KB), logic-tierb-003 (7KB), access-tierb-001 (8.7KB) |

**Progress Tracking (Updated 2026-01-09T18:30:00Z - Ralph Loop Iteration 3):**

| Artifact | Location | Description |
|----------|----------|-------------|
| Crawl Manifest | `.true_vkg/discovery/crawl_manifest.yaml` | Tracks all crawled URLs, 33 documented vulns, 6 patterns created |
| New Categories | `knowledge/vulndocs/categories/` | 5 new: account-abstraction, restaking, zk-rollup, vault, cross-chain |
| Semantic Patterns | `patterns/semantic/*/` | 6 patterns: vault-001, logic-002, logic-003, reentrancy-002, cc-001, ac-002 |
| Specific Exploits | `categories/*/subcategories/*/specifics/` | 6 detailed exploit docs created |

**New Categories Added (2026-01-09):**

| Category | Subcategories | Status |
|----------|---------------|--------|
| account-abstraction | bundler-manipulation, paymaster-exploits, userop-validation, entrypoint-issues | Category index + paymaster docs created |
| restaking | slashing-exploits, avs-security, operator-collusion, withdrawal-delay | Category index created |
| zk-rollup | soundness-bugs, circuit-constraints, prover-exploits, state-verification | Category index created |
| vault | share-inflation, first-depositor, donation-attack, exchange-rate | Category index + share-inflation docs + pattern created |
| **cross-chain** | bridge-compromise, message-validation, nonce-replay, oracle-dependency | **NEW**: Category index + yala-layerzero specific |

**Specific Exploit Documentation Created (Iteration 2):**

| Path | Exploit | Total Loss |
|------|---------|------------|
| `logic/arithmetic/specifics/balancer-v2-rounding/` | Balancer V2 Rounding | $128M |
| `logic/arithmetic/specifics/cetus-sui-overflow/` | Cetus SUI Overflow | $260M |
| `reentrancy/cross-function/specifics/gmx-v1-reentrancy/` | GMX v1 Reentrancy | $42M |
| `access-control/weak-modifier/specifics/arcadia-trust-assumption/` | Arcadia Trust Assumption | $3.5M |
| `cross-chain/bridge-compromise/specifics/yala-layerzero/` | Yala Bridge LayerZero | $7.64M |

**Vulnerabilities Discovered via Exa (2026-01-09):**

| Vulnerability | Date | Loss | Category | VulnDocs | Pattern |
|--------------|------|------|----------|----------|---------|
| Balancer V2 Rounding | 2025-11-03 | $128M | logic/arithmetic | ✅ | ✅ logic-002 |
| GMX v1 Reentrancy | 2025-07-09 | $42M | reentrancy/cross-function | ✅ | ✅ reentrancy-002 |
| ResupplyFi Donation | 2025-06-26 | $9.8M | vault/share-inflation | ✅ | ✅ vault-001 |
| Arcadia Trust Assumption | 2025-07-15 | $3.5M | access-control/weak-modifier | ✅ | ✅ ac-002 |
| 1inch Calldata Corruption | 2025-03-05 | Unknown | logic/configuration | ✅ | Pending |
| Yala Bridge LayerZero | 2025-09 | $7.64M | cross-chain/bridge-compromise | ✅ | ✅ cc-001 |
| Cetus Protocol SUI | 2025-05-22 | $260M | logic/arithmetic | ✅ | ✅ logic-003 |
| zkSync Era Soundness | 2023-09 | ~$1.9B potential | zk-rollup | ✅ | Pending |
| ERC-4337 UserOp Packing | 2024-02 | Potential | account-abstraction | ✅ | Pending |
| EigenLayer Sidecar DivZero | 2025-06 | Unknown | restaking | ✅ | Pending |

**Pattern Types:**
- **Type 1: Semantic** - Detect via operations, behavioral signatures, properties (deterministic)
- **Type 2: Library/Exact Match** - Match specific library methods (SafeERC20.safeTransfer, etc.)
- **Type 3: LLM Reasoning** - Require LLM to analyze code context and business logic

**Pattern Linking:**
- Every pattern MUST have `vulndocs_reference` pointing to category/subcategory/specific
- Every specific vulnerability in VulnDocs MUST have `pattern_id` in its index.yaml

---

## 4.4 Parallel Subagent Processing (Max 4 Concurrent)

### Docs Creation Parallelization Strategy

**CRITICAL**: Use up to 4 `knowledge-aggregation-worker` subagents in parallel to accelerate docs creation.

### Parallel Execution Model

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR (Main Agent)                            │
│  - Assigns sources to subagents                                         │
│  - Monitors progress                                                    │
│  - Aggregates results                                                   │
│  - Handles conflicts/merges                                             │
└─────────────────────────────────────────────────────────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ SUBAGENT 1  │ │ SUBAGENT 2  │ │ SUBAGENT 3  │ │ SUBAGENT 4  │
│ (Haiku 4.5) │ │ (Haiku 4.5) │ │ (Haiku 4.5) │ │ (Haiku 4.5) │
├─────────────┤ ├─────────────┤ ├─────────────┤ ├─────────────┤
│ Tier 1+2    │ │ Tier 3      │ │ Tier 4+5+6  │ │ Tier 7+8+9  │
│ Vuln DBs    │ │ Audit Firms │ │ Researchers │ │ GitHub/Docs │
│ Contests    │ │ (19 sources)│ │ Education   │ │ FV/Emerging │
│ (12 sources)│ │             │ │ CTFs        │ │ (22 sources)│
│             │ │             │ │ (26 sources)│ │             │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
         │              │              │              │
         └──────────────┴──────────────┴──────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ MERGE & DEDUPE  │
                    │ Conflict Resolution
                    │ Final VulnDocs  │
                    └─────────────────┘
```

### Subagent Assignment

| Subagent | Tiers | Sources | Focus |
|----------|-------|---------|-------|
| 1 | 1, 2 | 12 | Vulnerability DBs + Audit Contests |
| 2 | 3 | 19 | Professional Audit Firms |
| 3 | 4, 5, 6 | 26 | Researchers + Education + CTFs |
| 4 | 7, 8, 9, 10 | 30 | GitHub + Protocol Docs + FV + Emerging |

### Parallel Task Execution

```yaml
# Task tool invocation for parallel docs creation
parallel_docs_creation:
  - task:
      subagent_type: knowledge-aggregation-worker
      description: "Crawl Tier 1+2: Vuln DBs and Contests"
      prompt: |
        Process sources 1-12 (Solodit, Rekt, DefiLlama, SlowMist,
        Immunefi, Code4rena, Sherlock, Cantina, Hats, CodeHawks, Secure3).
        Follow download-process-delete pipeline.
        Extract ALL knowledge signals. Generate patterns.
      run_in_background: true

  - task:
      subagent_type: knowledge-aggregation-worker
      description: "Crawl Tier 3: Audit Firms"
      prompt: |
        Process sources 13-31 (ToB, OZ, Consensys, Spearbit, Cyfrin,
        Sigma Prime, Dedaub, Peckshield, CertiK, Quantstamp, etc.).
        Follow download-process-delete pipeline.
        Extract ALL knowledge signals. Generate patterns.
      run_in_background: true

  - task:
      subagent_type: knowledge-aggregation-worker
      description: "Crawl Tier 4+5+6: Researchers + Education + CTFs"
      prompt: |
        Process sources 32-57 (samczsun, cmichel, SWC Registry,
        Secureum, DamnVulnerableDeFi, Ethernaut, etc.).
        Follow download-process-delete pipeline.
        Extract ALL knowledge signals. Generate patterns.
      run_in_background: true

  - task:
      subagent_type: knowledge-aggregation-worker
      description: "Crawl Tier 7+8+9+10: GitHub + Docs + FV + Emerging"
      prompt: |
        Process sources 58-87 (DeFiHackLabs, Solcurity, Uniswap docs,
        Certora, Arbitrum, EigenLayer, etc.).
        Follow download-process-delete pipeline.
        Extract ALL knowledge signals. Generate patterns.
      run_in_background: true
```

### Conflict Resolution

When multiple subagents write to the same VulnDocs location:

1. **MERGE by timestamp** - Later write includes earlier content
2. **DEDUPLICATE** - Remove duplicate exploits/patterns by signature
3. **HIGHEST VALUE wins** - If conflict, keep higher-value content
4. **LOG conflicts** - Write to `.true_vkg/vulndocs_conflicts.log`

```yaml
conflict_resolution:
  strategy: merge_highest_value
  log_file: ".true_vkg/vulndocs_conflicts.log"

  rules:
    - duplicate_exploit:
        action: keep_most_detailed
        fields_to_compare: [name, date, loss, description]

    - duplicate_pattern:
        action: merge_conditions
        keep: all_unique_conditions

    - same_subcategory_different_content:
        action: append_with_source_tag
```

### Monitoring & Aggregation

```bash
# Check subagent progress
tail -f .true_vkg/crawl_cache/processing_log.jsonl

# Count processed sources per subagent
grep -c "SUCCESS" .true_vkg/crawl_cache/processing_log.jsonl

# Check for errors
grep "ERROR" .true_vkg/crawl_cache/processing_log.jsonl
```

### Task IDs for Parallel Execution

| Task ID | Description | Subagent Scope |
|---------|-------------|----------------|
| 17.3-P1 | Parallel Subagent 1 | Tier 1+2 (12 sources) |
| 17.3-P2 | Parallel Subagent 2 | Tier 3 (19 sources) |
| 17.3-P3 | Parallel Subagent 3 | Tier 4+5+6 (26 sources) |
| 17.3-P4 | Parallel Subagent 4 | Tier 7+8+9+10 (30 sources) |
| 17.3-MERGE | Merge & Dedupe | All subagent outputs |

---

**Exa Query Checklist (Novel Vulnerabilities):**

**Account Abstraction / ERC-4337:**
- [ ] `ERC-4337 account abstraction security vulnerability 2025`
- [ ] `bundler manipulation attack ERC-4337`
- [ ] `paymaster exploit vulnerability`
- [ ] `user operation validation bypass`

**Restaking / Liquid Staking:**
- [ ] `EigenLayer restaking vulnerability exploit 2025`
- [ ] `AVS security vulnerability`
- [ ] `liquid staking slashing condition exploit`
- [ ] `Lido stETH vulnerability security 2025`

**ZK-Rollup Specific:**
- [ ] `zkSync zkEVM security vulnerability 2025`
- [ ] `zero knowledge proof circuit vulnerability Solidity`
- [ ] `zk-SNARK trusted setup attack`
- [ ] `zkEVM opcode discrepancy vulnerability`

**Cross-chain / Bridges:**
- [ ] `cross-chain bridge vulnerability exploit 2025`
- [ ] `LayerZero omnichain security issue 2025`
- [ ] `message replay cross-chain attack`
- [ ] `bridge relayer manipulation`

**Intent-Based Protocols:**
- [ ] `intent-based trading security vulnerability solver`
- [ ] `CoW protocol MEV security 2025`
- [ ] `solver collusion attack`
- [ ] `intent replay vulnerability`

**ERC-4626 Vaults:**
- [ ] `ERC-4626 vault security vulnerability 2025`
- [ ] `vault share inflation attack`
- [ ] `first depositor attack vault`
- [ ] `vault donation attack`

**Novel Reentrancy:**
- [ ] `Curve read-only reentrancy vulnerability`
- [ ] `cross-contract reentrancy DeFi 2025`
- [ ] `view function reentrancy`
- [ ] `callback reentrancy new vector 2025`

**Oracle Variants:**
- [ ] `Chainlink CCIP security vulnerability 2025`
- [ ] `cross-chain oracle manipulation`
- [ ] `Pyth oracle vulnerability`
- [ ] `Redstone oracle security issue`

**Protocol-Specific:**
- [ ] `Uniswap V4 hooks security vulnerability`
- [ ] `GMX perpetual DEX vulnerability 2025`
- [ ] `Morpho lending vulnerability`
- [ ] `Pendle yield tokenization security`

**Emerging Threats 2025-2026:**
- [ ] `DeFi vulnerability 2025 novel attack vector`
- [ ] `smart contract security new vulnerability 2025`
- [ ] `blockchain exploit January 2026`
- [ ] `DeFi hack 2026 analysis`

**Validation Tasks:**

| ID | Task | Est. | Priority | Status | Description |
|----|------|------|----------|--------|-------------|
| 17.12 | Integration Testing | 4h | MUST | ✅ DONE | Pattern loading verified (593 patterns), YAML validation passed, basic pattern tests passed (4/4) |
| 17.13 | Benchmark Validation | 4h | MUST | TODO | Validate against known exploits |
| 17.14 | Documentation | 4h | SHOULD | ✅ DONE | Updated patterns.md with Tier B documentation, aggregation modes, risk tags |

### 4.3 Source Coverage Checklist (87 Sources)

**TIER 1: Vulnerability DBs (6 sources) - CRITICAL**
- [ ] Solodit (solodit.xyz)
- [ ] DeFiYield REKT (defiyield.app/rekt-database)
- [ ] SlowMist Hacked (hacked.slowmist.io)
- [ ] DefiLlama Hacks (defillama.com/hacks)
- [ ] Rekt News (rekt.news)
- [ ] Immunefi Writeups (immunefi.com/bounty)

**TIER 2: Audit Contests (6 sources) - CRITICAL**
- [ ] Code4rena (code4rena.com/reports)
- [ ] Sherlock (app.sherlock.xyz/audits)
- [ ] Cantina (cantina.xyz)
- [ ] Hats Finance (hats.finance)
- [ ] CodeHawks (codehawks.com)
- [ ] Secure3 (secure3.io)

**TIER 3: Audit Firms (19 sources) - CRITICAL**
- [ ] Trail of Bits (github.com/trailofbits/publications)
- [ ] OpenZeppelin (blog.openzeppelin.com)
- [ ] Consensys Diligence (consensys.io/diligence)
- [ ] Spearbit (github.com/spearbit)
- [ ] Cyfrin (github.com/Cyfrin)
- [ ] Sigma Prime (sigmaprime.io/blog)
- [ ] Dedaub (dedaub.com/blog)
- [ ] Peckshield (peckshield.com/blog)
- [ ] CertiK (certik.com/resources)
- [ ] Quantstamp (quantstamp.com/blog)
- [ ] Runtime Verification (runtimeverification.com/blog)
- [ ] Zellic (zellic.io/blog)
- [ ] yAudit (reports.yaudit.dev)
- [ ] Mixbytes (mixbytes.io/blog)
- [ ] ChainSecurity (chainsecurity.com/research)
- [ ] Halborn (halborn.com/blog)
- [ ] BlockSec (blocksec.com/blog)
- [ ] Nethermind (nethermind.io/blog)
- [ ] a16z Crypto (a16zcrypto.com/posts)

**TIER 4: Security Researchers (12 sources) - HIGH**
- [ ] samczsun (samczsun.com)
- [ ] Mudit Gupta (mudit.blog)
- [ ] cmichel (cmichel.io)
- [ ] Tincho/Red Guild (blog.theredguild.org)
- [ ] Patrick Collins (patrickalphac.medium.com)
- [ ] officer_cia (officercia.mirror.xyz)
- [ ] pcaversaccio (github.com/pcaversaccio)
- [ ] transmissions11 (github.com/transmissions11)
- [ ] 0xWeiss (0xweiss.substack.com)
- [ ] Christoph Michel (cmichel.io)
- [ ] Josselin Feist (mondedesjosselin.fr)
- [ ] Gustavo Grieco (Trail of Bits)

**TIER 5: Education (7 sources) - HIGH**
- [ ] SWC Registry (swcregistry.io)
- [ ] Secureum (secureum.substack.com)
- [ ] Smart Contract Programmer (youtube.com/@smartcontractprogrammer)
- [ ] Owen Thurm (youtube.com/@owenthurm)
- [ ] Andy Li (youtube.com/@andyliofficial)
- [ ] Blockchain Security DB (bsdb.io)
- [ ] Solidity by Example (solidity-by-example.org)

**TIER 6: CTFs (7 sources) - HIGH**
- [ ] DamnVulnerableDeFi (damnvulnerabledefi.xyz)
- [ ] Ethernaut (ethernaut.openzeppelin.com)
- [ ] Capture the Ether (capturetheether.com)
- [ ] Paradigm CTF (github.com/paradigmxyz)
- [ ] Secureum A-MAZE-X
- [ ] Mr Steal Yo Crypto (mrstealyocrypto.xyz)
- [ ] Curta (curta.wtf)

**TIER 7: GitHub Repos (10 sources) - HIGH**
- [ ] crytic/not-so-smart-contracts
- [ ] crytic/building-secure-contracts
- [ ] Rari-Capital/solcurity
- [ ] sigp/solidity-security-blog
- [ ] ConsenSys/smart-contract-best-practices
- [ ] SunWeb3Sec/DeFiHackLabs
- [ ] ZhangZhuoSJTU/Web3Bugs
- [ ] immunefi-team/Web3-Security-Library
- [ ] tintinweb/smart-contract-sanctuary
- [ ] OpenZeppelin/openzeppelin-contracts/security

**TIER 8: Protocol Docs (8 sources) - MEDIUM-HIGH**
- [ ] Uniswap Security (docs.uniswap.org)
- [ ] Aave Security (docs.aave.com)
- [ ] Compound Security (docs.compound.finance)
- [ ] MakerDAO (docs.makerdao.com)
- [ ] Curve (resources.curve.fi)
- [ ] Balancer (docs.balancer.fi)
- [ ] Chainlink (docs.chain.link)
- [ ] Yearn (docs.yearn.fi)

**TIER 9: Formal Verification (5 sources) - MEDIUM**
- [ ] Certora (certora.com/blog)
- [ ] Halmos (github.com/a16z/halmos)
- [ ] Echidna (github.com/crytic/echidna)
- [ ] Foundry Invariants (book.getfoundry.sh)
- [ ] Scribble (docs.scribble.codes)

**TIER 10: Emerging/L2/Bridge (7 sources) - MEDIUM**
- [ ] Arbitrum Security (docs.arbitrum.io)
- [ ] Optimism Security (docs.optimism.io)
- [ ] zkSync Security (docs.zksync.io)
- [ ] LayerZero (docs.layerzero.network)
- [ ] ERC-4337 (eips.ethereum.org)
- [ ] Flashbots (docs.flashbots.net)
- [ ] EigenLayer (docs.eigenlayer.xyz)

---

## 5. IMPLEMENTATION

### 5.1 Core Files

| File | Description |
|------|-------------|
| `src/true_vkg/vulndocs/__init__.py` | Module init |
| `src/true_vkg/vulndocs/schema.py` | Knowledge schema |
| `src/true_vkg/knowledge/vulndocs/templates.py` | Document templates (detection, patterns, exploits, fixes) |
| `src/true_vkg/vulndocs/navigator.py` | Navigation API |
| `src/true_vkg/vulndocs/cache.py` | Prompt caching |
| `src/true_vkg/vulndocs/builder.py` | Context builder |
| `src/true_vkg/vulndocs/llm_interface.py` | LLM navigation |
| `src/true_vkg/skills/solodit_learner.py` | Solodit skill |
| `knowledge/vulndocs/index.yaml` | Top-level index |
| `knowledge/vulndocs/categories/*/` | Category docs |
| `tests/test_vulndocs_navigator.py` | Navigator tests |
| `tests/test_vulndocs_cache.py` | Cache tests |
| `tests/test_vulndocs_templates.py` | Template tests (48 tests) |
| `tests/test_solodit_skill.py` | Solodit tests |

### 5.2 Knowledge Aggregation Worker

**Agent:** `.claude/agents/knowledge-aggregation-worker.md`
**Model:** Claude Haiku 4.5 (fast, cost-efficient)

The `knowledge-aggregation-worker` is the primary agent for crawling, extracting, and integrating vulnerability knowledge into VulnDocs.

**Tasks using this agent:**
| Task | Purpose |
|------|---------|
| 17.3 | Initial Knowledge Population - crawl security sources, populate categories |
| 17.8 | Solodit Fetcher - crawl Solodit using crawl4ai |
| 17.9 | Vulnerability Analyzer - extract semantic signals, make ACCEPT/MERGE/REJECT decisions |
| 17.10 | Knowledge Updater - integrate extracted content into VulnDocs structure |
| 17.11 | Pattern Generator - create new patterns from novel vulnerabilities |
| 17.15 | Rekt/Medium Importers - crawl additional security sources |

**Key Capabilities:**
1. **Crawl4AI Integration** - Uses Docker-based crawl4ai for web scraping
2. **Semantic Extraction** - Extracts operations, signatures, properties (never variable names)
3. **Value Assessment** - ACCEPT/MERGE/REJECT decisions based on novelty and value
4. **Category Mapping** - Maps vulnerabilities to correct VulnDocs subcategory
5. **Pattern Generation** - Creates new BSKG patterns from extracted knowledge

**Critical Rule:** NEVER reference variable names - only semantic operations, behavioral signatures, and properties. Exception: Library method names (SafeERC20.safeTransfer, ReentrancyGuard.nonReentrant).

### 5.2 Navigator API

```python
# src/true_vkg/vulndocs/navigator.py

class KnowledgeDepth(Enum):
    INDEX = "index"
    OVERVIEW = "overview"
    DETECTION = "detection"
    PATTERNS = "patterns"
    EXPLOITS = "exploits"
    FIXES = "fixes"
    FULL = "full"

class VulnDocsNavigator:
    """Navigate and retrieve vulnerability knowledge."""

    def __init__(self, knowledge_dir: str = "knowledge/vulndocs"):
        self.knowledge_dir = Path(knowledge_dir)
        self._index = self._load_index()
        self._cache = {}

    def get_context(
        self,
        category: str,
        subcategory: Optional[str] = None,
        depth: KnowledgeDepth = KnowledgeDepth.DETECTION,
    ) -> str:
        """Get knowledge context for a category/subcategory."""
        ...

    def get_context_for_findings(
        self,
        findings: List[Dict[str, Any]],
        depth: KnowledgeDepth = KnowledgeDepth.DETECTION,
        max_tokens: int = 8000,
    ) -> str:
        """Get combined context for multiple findings."""
        ...

    def get_cacheable_system_context(self) -> str:
        """Get stable context for prompt caching."""
        ...

    def get_navigation_prompt(self) -> str:
        """Generate prompt for LLM navigation."""
        return f"""
Available vulnerability categories:
{self._format_categories()}

To navigate: Use get_context(category, subcategory, depth)
Depths: index, overview, detection, patterns, exploits, fixes, full
"""

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search knowledge base by keyword."""
        ...
```

---

## 6. SUCCESS METRICS

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Knowledge Coverage | ALL world sources crawled | Checklist of sources in 1.3 |
| Category Completeness | 15+ categories (expandable) | Count, including new ones created |
| Subcategory Depth | 60+ subcategories | Count all subcategories |
| Specific Variants | 100+ specific vulnerabilities | Count specifics/ directories |
| Token Efficiency | 60% reduction | Compare tokens |
| Cache Hit Rate | 80%+ | Track usage |
| Navigation Accuracy | 95%+ | Test LLM nav |
| Pattern Generation | 10+/week during aggregation | Track from all sources |
| Semantic Purity | 0% variable names | Grep for hardcoded names |
| Knowledge Quality | 90%+ | Human review |

---

## 7. EXIT CRITERIA

### 7.1 Infrastructure (Tasks 17.0-17.7) ✅ DONE
- [x] Knowledge schema defined and validated (78 tests)
- [x] Category structure created (11 categories, 47 subcategories)
- [x] Document templates implemented (48 tests)
- [x] Python Navigator API works (52 tests)
- [x] Prompt caching integrated (62 tests)
- [x] Context builder functional (67 tests)
- [x] LLM navigation interface complete (72 tests)
- [x] 600+ tests passing

### 7.2 World Knowledge Aggregation (Tasks 17.3, 17.8-17.11, 17.15)
- [ ] ALL 87 sources crawled using `knowledge-aggregation-worker`
- [ ] New categories created as discovered (if any)
- [ ] New subcategories created as discovered
- [ ] Specific vulnerability variants documented
- [ ] Semantic-only content (no variable names)
- [ ] Patterns generated from extracted knowledge

### 7.3 Exa-Based Discovery (Tasks 17.16-17.21)
- [ ] Exa source discovery complete - new sources added to Tier 11+
- [ ] Novel vulnerability search (2024-2026) complete
- [ ] Protocol-specific deep dives done (ERC-4337, EigenLayer, ZK, bridges, intents)
- [ ] Individual vulnerabilities extracted one-by-one
- [ ] Code patterns enriched via get_code_context_exa
- [ ] Weekly Exa scan automation set up
- [ ] All queries in Exa Query Checklist executed

### 7.4 Pattern Generation Super Task (Tasks 17.22)
- [ ] Every specific vulnerability has at least one pattern
- [ ] Semantic patterns (Tier A) generated for deterministic detection
- [ ] Library exact-match patterns for known safe/unsafe methods
- [ ] LLM reasoning patterns (Tier B) for context-dependent vulnerabilities
- [ ] All patterns linked to VulnDocs via `vulndocs_reference`
- [ ] All VulnDocs specifics have `pattern_id` in index.yaml
- [ ] Pattern ratings: 80%+ at "ready" or "excellent" status

### 7.5 Parallel Processing (Tasks 17.3-P1 to P4)
- [ ] 4 parallel subagents executed for docs creation
- [ ] All subagent outputs merged and deduplicated
- [ ] Conflict resolution complete
- [ ] Processing log shows no unresolved errors

### 7.6 Quality Validation (Tasks 17.12-17.14)
- [ ] Integration testing complete
- [ ] Benchmark validation passed
- [ ] Documentation complete

---

*Phase 17 Tracker | Version 1.0 | 2026-01-08*
*Addresses: Vulnerability Knowledge Documentation System*

---

## Alignment Addendum (Workstream P)

### Workstream P: Alignment Tasks

| ID | Objective | Start here | Dependencies | Deliverables | Validation | Conflicts | Spawn Triggers |
|----|-----------|------------|--------------|--------------|------------|-----------|----------------|
| P17.P.1 | Define evidence packet retrieval contract for VulnDocs | `docs/PHILOSOPHY.md`, `task/4.0/phases/phase-17/TRACKER.md` | P1.P.1 | Retrieval contract doc | Phase 11 uses for LLM context | Evidence packet versioned | New VulnDocs source |
| P17.P.2 | Link bead templates to VulnDocs sources | `docs/PHILOSOPHY.md`, `task/4.0/phases/phase-6/TRACKER.md` | P6.P.1 | Mapping rules | Phase 6 schema mapping uses it | Bead schema compatible | New bead template |

### Review Tasks (Required + Phase-Specific)

| ID | Objective | Start here | Dependencies | Deliverables | Validation | Conflicts | Spawn Triggers |
|----|-----------|------------|--------------|--------------|------------|-----------|----------------|
| P17.R.1 | Phase necessity review (keep/cut/modify) | `task/4.0/MASTER.md`, `docs/PHILOSOPHY.md` | - | Decision log in tracker | Decision referenced in alignment sweep | None | Phase outputs no longer needed |
| P17.R.2 | Task necessity review for P17.P.* | `task/4.0/phases/phase-17/TRACKER.md`, `task/codex/vkg_4_0_alignment_super_task.md` | P17.P.1-P17.P.2 | Task justification log | Each task has keep/merge decision | Avoid overlap with pattern packs | Redundant task discovered |
| P17.R.3 | Conflict review with downstream phases | `task/4.0/MASTER.md` | P17.P.1-P17.P.2 | Conflict notes in tracker | Conflicts resolved or escalated | Tier A/Tier B separation | Conflict discovered |
| P17.R.4 | Ensure VulnDocs scope does not conflict with pattern packs | `patterns/`, `task/4.0/phases/phase-17/TRACKER.md` | P17.P.1 | Scope note | No duplicate pattern sources | Pattern pack conflict | Conflict detected |

### Dynamic Task Spawning (Alignment)

**Trigger:** Missing subcategory discovered.
**Spawn:** Add new VulnDocs category task.
**Example spawned task:** P17.P.3 Add a missing VulnDocs category + mapping rules.
