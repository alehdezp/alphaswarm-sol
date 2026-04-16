# Phase 7: Final Testing (GA Gate) - Context

**Gathered:** 2026-01-21
**Updated:** 2026-01-21 (Agent/Skill Audit & Testing Framework)
**Status:** Ready for planning

<domain>
## Phase Boundary

Prove BSKG works in real-world auditing conditions with agentic orchestration. Validate all 8 PHILOSOPHY pillars through structured testing, ground truth comparison, and comprehensive documentation before GA release. Includes building a dedicated testing framework that mirrors real-world agentic usage patterns.

**Core Deliverable:** BSKG Test Forge - A self-improving testing ecosystem with standardized metrics, corpus management, and feedback loops for continuous improvement.

</domain>

<agent-audit>
## Agent Audit Results

### Agents to KEEP (8 agents)

| Agent | Model | Purpose | Phase 7 Role |
|-------|-------|---------|--------------|
| `vkg-attacker` | opus | Exploit path construction | Adversarial testing |
| `vkg-defender` | sonnet | Guard detection | Validation testing |
| `vkg-verifier` | opus | Verdict synthesis | Verdict validation |
| `vkg-pattern-architect` | sonnet | Pattern design/improvement | Gap remediation |
| `pattern-tester` | sonnet | Pattern validation | Core testing (UPDATE) |
| `vkg-security-research` | sonnet | Vulnerability research | Knowledge expansion |
| `knowledge-aggregation-worker` | sonnet | VulnDocs aggregation | Knowledge system |
| `vkg-docs-curator` | haiku | Documentation maintenance | Docs update (UPDATE) |

### Agents to REMOVE (2 agents)

| Agent | Reason | Replacement |
|-------|--------|-------------|
| `solidity-security-tester` | Overly broad, duplicates pattern-tester functionality | Consolidated into `vkg-test-conductor` |
| `vkg-real-world-auditor` | Overlaps with shadow audit concept | Consolidated into `vkg-shadow-auditor` |

### Agents to UPDATE (2 agents)

**pattern-tester → MAJOR UPDATE**
- Add corpus integration (query corpus.db)
- Add benchmark metrics output (standardized TestMetrics)
- Add regression baseline comparison
- Add coverage tracking per pattern/category
- Add mutation testing integration

**vkg-docs-curator → MINOR UPDATE**
- Add Phase 7 documentation requirements
- Add GA dossier generation support
- Add testing report templates

### NEW Agents (6 agents)

| Agent | Model | Purpose | Key Capabilities |
|-------|-------|---------|------------------|
| `vkg-test-conductor` | opus | Testing orchestration maestro | Coordinates all testing phases, manages dependencies, produces executive reports, decides quality gates |
| `vkg-corpus-curator` | sonnet | Test corpus management | Maintains corpus integrity, discovers new contracts, tags/categorizes findings, ensures balanced representation |
| `vkg-mutation-tester` | haiku | Chaos/mutation testing | Generates mutant contracts, tests pattern sensitivity, identifies false negative risks, validates edge cases |
| `vkg-regression-hunter` | sonnet | Regression detection | Compares across versions, identifies degradation, bisects to find breaking changes, reports root causes |
| `vkg-benchmark-champion` | haiku | Performance benchmarking | Runs standardized benchmarks, measures metrics, tracks trends, alerts on anomalies |
| `vkg-gap-finder` | opus | Detection gap analysis | Analyzes coverage, identifies blind spots, proposes new patterns, prioritizes improvements |

**Total Agents: 14** (from 10 original)

</agent-audit>

<skill-audit>
## Skill Audit Results

### Skills to KEEP (7 skills)

| Skill | Purpose | Phase 7 Role |
|-------|---------|--------------|
| `/vkg:audit` | Full audit pipeline | E2E testing target |
| `/vkg:investigate` | Deep bead investigation | Agent testing |
| `/vkg:verify` | Multi-agent verification | Debate testing |
| `/vkg:debate` | Structured debate protocol | Protocol testing |
| `/test-builder` | Performance-optimized tests | Test construction (UPDATE) |
| `/pattern-forge` | Iterative pattern development | Pattern improvement (UPDATE) |
| `/vkg:coordinate-tools` | Tool coordination | Tool integration testing |

### Skills to UPDATE (2 skills)

**test-builder → MINOR UPDATE**
- Add corpus-aware test generation
- Add TestMetrics output format
- Add parallel execution hints for new test types

**pattern-forge → MINOR UPDATE**
- Add mutation testing integration
- Better quality gate definitions for Phase 7
- Add gap-finder feedback loop

### NEW Skills (6 skills)

| Skill | Model | Purpose | Spawns |
|-------|-------|---------|--------|
| `/vkg:test-full` | sonnet | Complete test orchestration | vkg-test-conductor |
| `/vkg:benchmark` | haiku | Quick benchmark execution | vkg-benchmark-champion |
| `/vkg:mutate` | haiku | Mutation testing | vkg-mutation-tester |
| `/vkg:hunt-regressions` | sonnet | Regression detection | vkg-regression-hunter |
| `/vkg:find-gaps` | opus | Gap analysis | vkg-gap-finder |
| `/vkg:shadow-audit` | sonnet | Shadow audit execution | vkg-corpus-curator + attacker/defender |

**Total Skills: 13** (from 7 original)

</skill-audit>

<testing-framework>
## BSKG Test Forge - Reusable Testing Framework

### Architectural Pillars

**Pillar 1: Corpus System (Foundation)**
```
.vrs/
├── corpus/
│   ├── corpus.db              # SQLite - contracts, findings, ground truth
│   ├── contracts/             # Test contracts
│   │   ├── vulnerable/        # Known vulnerable (with CVE/audit refs)
│   │   ├── safe/              # Known safe (false positive testing)
│   │   └── edge/              # Edge cases (proxies, delegatecall, etc.)
│   ├── ground-truth/          # Known findings
│   │   ├── dvdefi.json        # DVDeFi challenge solutions
│   │   ├── audit-findings.json # Real audit findings
│   │   └── cve-mappings.json  # CVE → contract mappings
│   ├── benchmarks/            # Benchmark definitions
│   │   ├── quick.yaml         # < 2 min smoke tests
│   │   ├── standard.yaml      # < 10 min full regression
│   │   └── thorough.yaml      # < 30 min exhaustive
│   └── baselines/             # Version baselines for regression
│       ├── v4.0-baseline.json
│       └── v5.0-baseline.json
```

**Pillar 2: Standardized Metrics**
```python
@dataclass
class TestMetrics:
    precision: float      # TP / (TP + FP)
    recall: float         # TP / (TP + FN)
    f1_score: float       # Harmonic mean
    execution_time_ms: int
    memory_peak_mb: float
    contracts_tested: int
    patterns_tested: int

    # Per-category breakdown
    by_category: Dict[str, CategoryMetrics]

    # Per-severity breakdown
    by_severity: Dict[str, SeverityMetrics]

    # Comparison to baseline
    baseline_delta: Optional[MetricsDelta]

    # Cost tracking
    tokens_used: int
    cost_usd: float
```

**Pillar 3: Test Modes**
```python
QUICK_TESTS = ["unit", "smoke", "critical-path"]
# Time: < 2 min | Purpose: Fast feedback during development

STANDARD_TESTS = ["unit", "integration", "regression", "pattern-validation"]
# Time: < 10 min | Purpose: Full regression before commits

THOROUGH_TESTS = ["unit", "integration", "regression", "e2e", "adversarial", "mutation", "shadow"]
# Time: < 30 min | Purpose: GA gate, release validation
```

**Pillar 4: Orchestration Flow**
```
/vkg:test-full
    │
    ├── 1. CORPUS VALIDATION (corpus-curator)
    │   └── Verify integrity, coverage, freshness
    │
    ├── 2. QUICK TESTS (benchmark-champion)
    │   └── Smoke tests, critical paths
    │
    ├── 3. STANDARD TESTS (pattern-tester)
    │   └── Unit, integration, regression
    │
    ├── 4. MUTATION TESTS (mutation-tester)
    │   └── Pattern robustness validation
    │
    ├── 5. SHADOW AUDIT (attacker + defender)
    │   └── Test against known findings
    │
    ├── 6. REGRESSION CHECK (regression-hunter)
    │   └── Compare to baseline, bisect if needed
    │
    ├── 7. GAP ANALYSIS (gap-finder)
    │   └── Identify coverage holes
    │
    └── 8. REPORT GENERATION (test-conductor)
        └── All reports + GA dossier
```

### Feedback Loop Architecture

The testing framework creates self-improvement cycles:

```
gap-finder → identifies blind spots
    ↓
vkg-pattern-architect → proposes new patterns
    ↓
pattern-forge → develops patterns
    ↓
pattern-tester → validates patterns
    ↓
mutation-tester → stress tests patterns
    ↓
regression-hunter → ensures no regressions
    ↓
corpus-curator → adds new test cases
    ↓
gap-finder → measures improvement
    ↓
(repeat)
```

### Reusability Design

1. **Configuration-driven** - YAML files define test suites, benchmarks, thresholds
2. **Pluggable corpus** - Add contracts, findings, benchmarks without code changes
3. **Standard interfaces** - All agents implement common testing protocols
4. **Metrics abstraction** - Same format for any test type
5. **Report templates** - Customizable output formats

</testing-framework>

<decisions>
## Implementation Decisions

### Corpus Selection
- **Protocol types:** Comprehensive - DeFi + NFT + DAOs + yield + lending + vaults - designed to stress-test and break the implementation
- **Ground truth source:** Audit reports + exploit post-mortems (not manual labeling)
- **Corpus size:** 50+ protocols minimum
- **Adversarial inclusion:** Yes - intentionally include known hard cases (proxies, delegatecall, complex patterns)
- **Categorization:** Matrix of vulnerability class × complexity level
- **Contest sources:** All major platforms - Code4rena, Sherlock, Immunefi, Hats
- **Time range:** 2023-2026 (modern patterns)
- **False positive testing:** Include audited-clean protocols subset
- **Version handling:** Include both exploited version + fixed version for detection delta comparison
- **Metadata per entry:** Protocol name, version, source URL, audit reports, known vulns, complexity rating
- **Results versioning:** Snapshot comparison per BSKG version with automated regression detection
- **Public release:** Yes - release corpus as public benchmark after GA
- **Build priority:** Parallel tracks - core 15 protocols deep, remaining 35+ at surface level
- **Proxy contracts:** Include all proxy types (EIP-1967, UUPS, Diamond, Beacon) as part of adversarial testing

### Ground Truth Comparison (Shadow Audit)
- **No live human auditors** - use known vulnerabilities from audit reports/exploits as ground truth
- **Measurement approach:** Full evidence match - detection + severity + evidence quality (root cause, impact, PoC potential)
- **Model tracking:** Cost-optimized metrics - tokens + cost + detection rate for quality/cost tradeoff
- **Model selection:** Role-based - Attacker/Verifier use Opus (critical analysis), Defender/Explorer use Sonnet (volume)
- **Detection target:** 90% of known vulnerabilities
- **Focus area:** Logic bugs requiring complex reasoning beyond static analysis - economic/incentive bugs, business logic violations, cross-function reasoning, timing/ordering
- **Static tool comparison:** Internal only - compare to Slither/Mythril for learning, don't publish
- **FP/FN balance:** Balanced - target F1 score as primary metric
- **Novel findings:** Separate category - track as potential discoveries, verify later, don't count in main metrics yet

### Success Thresholds
- **Tier A precision:** 95% (deterministic patterns should be near-certain)
- **Tier B precision:** 80% (LLM-verified patterns, acknowledge uncertainty)
- **Logic bug recall:** 70% (meaningful assistance to human auditors)
- **PHILOSOPHY pillars:** Core 5 must pass (pillars 1-5 required), others documented as partial
- **Severity-differentiated:** Critical/high vulns require 90%+ recall, medium/low at 70%+
- **Token budget:** Claude's discretion to optimize based on complexity
- **Latency:** No hard limit - quality over speed
- **Gap handling:** Document findings/gaps comprehensively, create improvement roadmap in `.planning/`, build Claude skill for gap tracking

### Limitations Scope
- **Transparency:** Brutally honest - document all known gaps, failure modes, and root causes
- **Visibility:** Internal only - detailed limitations kept private
- **Roadmap integration:** Both - actionable items to backlog, systemic gaps to research themes for 5.1+
- **Categories tracked:** All - detection gaps + technical constraints + scalability + UX + cost
- **Attribution:** Blame map - track which component (builder, pattern, LLM, orchestration) caused each gap
- **Progress tracking:** Skill-managed - Claude skill handles updates with consistent format and auto-organization
- **Skill creation:** Part of Phase 7 deliverables
- **Layered testing:** Pattern tests for regressions, gap tests for improvements, full corpus for GA gates only
- **Severity grading:** Critical/high/medium/low for prioritizing which gaps matter most

### Testing Framework
- **Full framework required:** Yes - build testing framework that mirrors real-world agentic assessment workflow
- **Core capabilities:** Orchestration replay + metric collection + before/after comparison on improvements
- **Parallel execution:** Yes - run multiple protocols concurrently (pytest -n auto --dist loadfile from Phase 8)
- **Persistence:** SQLite for historical results, trend analysis, regression detection
- **Test modes:** Three modes - Quick (pattern-specific), Standard (area coverage), Thorough (full corpus)
- **LLM quality measurement:** Automated evidence scoring + periodic human review of edge cases
- **Golden tests:** Yes - store expected reasoning outputs, detect quality regressions
- **Pattern validation:** Full validation suite - regression check + targeted improvement + side-effect detection
- **Skills/agents:** 14 agents, 13 skills (see audit sections above)
- **Granularity:** Support testing specific patterns, specific areas, or full corpus
- **Purpose:** Test LLM reasoning capabilities on complex logic/economic bugs, not just static pattern matching

### Cost-Efficient Model Selection (Testing Subagents)
- **Principle:** Use cheapest model capable of the task - maximize cost efficiency
- **Model tiers:**
  - **Haiku 4.5** (lowest cost): Tool execution, file operations, simple grep/glob, metric collection, cache lookups, health checks, result parsing, benchmark running, mutation generation
  - **Sonnet 4.5** (mid cost): Test orchestration, result aggregation, report generation, deduplication logic, pattern matching, intermediate reasoning, corpus curation, regression hunting
  - **Opus 4.5** (highest cost): Critical security analysis (Attacker/Verifier roles), complex reasoning, final verdicts, arbitration, gap analysis, test conductor decisions
- **Default:** Haiku for all non-thinking tasks; escalate only when reasoning required
- **Orchestration pattern:** Sonnet coordinates, spawns Haiku workers for tool running
- **Token tracking:** Log cost per test run for optimization feedback

### Claude's Discretion
- Token budget optimization per protocol
- Specific skill naming conventions
- Testing framework architecture details
- SQLite schema design for test results

### Phase 5.1 Testing (Static Analysis Tool Integration)
- **Scope:** Validate all TOOL-01 to TOOL-09 requirements
- **Tool coverage:** Slither, Aderyn, Mythril, Echidna, Halmos, Foundry, Semgrep
- **Test categories:**
  - Tool health and detection (graceful handling of missing tools)
  - Tool execution (parallel, config overrides)
  - Library handling (scope filtering, known libraries)
  - Result caching (file hash-based)
  - Deduplication (location-based + semantic similarity)
  - Agent skill behavior (lazy loading, coordination)
  - Tool-to-VKG pattern mapping
- **Thresholds:** 80%+ dedup reduction, 100% tool detection for installed tools

### Phase 5.2 Testing (Multi-Agent SDK Integration)
- **Scope:** Validate all SDK-01 to SDK-15 requirements
- **Test categories:**
  - SDK abstraction (Anthropic, OpenAI, local)
  - Hook system (agent inboxes, prioritized queues)
  - Propulsion (autonomous work-pulling)
  - Supervisor agent (queue monitoring, SLA, escalation)
  - Integrator agent (evidence merging, verdict finalization)
  - E2E agentic flow (build → detect → beads → verify → report)
  - Test generation (Foundry scaffolds, execution, confidence elevation)
  - Determinism, replayability, resumability
- **PHILOSOPHY Pillar 4:** Multi-agent debate validation

### Phase 5.2 Infrastructure (IMPLEMENT IN PHASE 7)
**NOTE:** Phase 7 must BUILD the following infrastructure so Phase 5.2 has something to test:

- **SDK Runtime Abstraction** (SDK-01): Implement `AgentRuntime` class with pluggable backends
- **Hook System Skeleton** (SDK-02): Implement `HookRegistry`, `AgentInbox`, `PrioritizedQueue`
- **Agent Spawner** (SDK-09): Implement context-fresh agent spawning per bead
- **Checkpoint Manager** (SDK-10): Implement save/load for resumability
- **Test Builder Interface** (SDK-11-13): Implement `FoundryScaffoldGenerator`, `FoundryRunner`
- **Confidence Scorer** (SDK-14): Implement test result → confidence elevation
- **PoC Generator** (SDK-15): Implement `PoCNarrativeGenerator`

**Rationale:** Testing framework needs working implementations to test against. Phase 7 builds minimal viable implementations; Phase 5.2 extends them to production quality.

### Incremental Improvement Tracking
- **Purpose:** Track before/after metrics when improvements are made
- **Infrastructure:** ImprovementTracker with SQLite storage
- **Capabilities:**
  - Set baseline metrics per component
  - Compare current to baseline
  - Detect regressions automatically
  - Track phase-specific progress (5.1, 5.2, future)
- **Roadmap-driven testing:**
  - Generate test stubs from ROADMAP.md requirements
  - Run tests incrementally as phases are built
  - Prepare infrastructure for future phases
- **Skill:** /vkg:track-improvement for CLI access

</decisions>

<ga-gate>
## GA Gate Criteria (v5.0 Release)

### Required (Must Pass)
- [ ] All unit tests pass (pytest exit 0)
- [ ] All integration tests pass
- [ ] DVDeFi detection ≥ 85%
- [ ] Tier A pattern precision ≥ 95%
- [ ] Tier B pattern precision ≥ 80%
- [ ] Overall recall ≥ 70%
- [ ] Critical/high severity recall ≥ 90%
- [ ] No regressions from v4.0 baseline
- [ ] Performance within 2x of Phase 8 targets
- [ ] Shadow audit coverage ≥ 75%
- [ ] Gap analysis shows no critical blind spots
- [ ] All agents pass health checks
- [ ] All skills pass integration tests
- [ ] PHILOSOPHY pillars 1-5 validated
- [ ] Security review completed

### Recommended (Should Pass)
- [ ] Medium/low severity recall ≥ 70%
- [ ] Token cost ≤ $5 per protocol
- [ ] Full pipeline latency ≤ 30 min per protocol
- [ ] Documentation complete
- [ ] Public corpus prepared

### Documented (Track but Don't Block)
- [ ] Novel findings count
- [ ] Cross-chain detection gaps
- [ ] Proxy pattern coverage gaps
- [ ] Areas for v5.1 improvement

</ga-gate>

<specifics>
## Specific Ideas

- "This is mega important and super critical" - testing must be exhaustive, designed to break the implementation
- Testing framework should mimic exactly how the agentic-first application will run in the real world
- Focus on "logic bugs only humans find" - economic, business logic, cross-function reasoning
- Framework must support granular pattern testing with configurable intensity
- "Hinted human reasoning capabilities about Solidity code first" - the core value proposition
- Multiple specialized skills preferred over monolithic tools
- Sub-agents with clean context for specific tasks
- Feedback loops enable continuous improvement beyond GA

</specifics>

<deferred>
## Deferred Ideas

- **Cross-chain/bridge exploits** - Exclude for GA, focus on it for version 5.1 (add to roadmap)
- External professional auditors for shadow comparison - no budget/expertise currently
- Real-time monitoring/alerting system - v5.1+
- Multi-language support (Vyper, etc.) - v5.1+

</deferred>

<implementation-order>
## Implementation Order (07-01 through 07-11)

| Plan | Description | Dependencies | Key Agents |
|------|-------------|--------------|------------|
| 07-01 | Testing Skills & Orchestration | None | Create all new agents/skills |
| 07-02 | Corpus Database Architecture | 07-01 | corpus-curator |
| 07-03 | Ground Truth Dataset Development | 07-02 | corpus-curator |
| 07-04 | End-to-End Validation Harness | 07-03 | test-conductor, pattern-tester |
| 07-05 | Adversarial Testing Framework | 07-04 | mutation-tester, attacker |
| 07-06 | Agentic Orchestration Trials | 07-05 | All verification agents |
| 07-07 | Performance Measurement Harness | 07-06 | benchmark-champion |
| 07-08 | Shadow Audit Protocol | 07-07 | gap-finder, regression-hunter |
| 07-09 | Security Review Checkpoint | 07-08 | Human review |
| 07-10 | GA Readiness Dossier | 07-09 | docs-curator |
| 07-11 | Version 5.0 Release | 07-10 | test-conductor (final gate) |

</implementation-order>

---

*Phase: 07-final-testing-ga-gate*
*Context gathered: 2026-01-21*
*Updated: 2026-01-21 (Agent/Skill Audit + Testing Framework)*
