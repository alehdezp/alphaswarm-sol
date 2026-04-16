# Phase 7: Final Testing (GA Gate) - Research

**Researched:** 2026-01-21
**Domain:** LLM application testing, agentic evaluation, security corpus benchmarking
**Confidence:** HIGH

## Summary

Phase 7 requires building a comprehensive testing framework that mirrors real-world agentic security auditing workflows. This research identifies the state-of-the-art in LLM evaluation (2026), corpus construction for smart contract security, and orchestration patterns for agent testing.

The landscape has matured significantly: **LLM-as-a-judge** with chain-of-thought reasoning has become standard, achieving 10-15% improvement over direct scoring. **Agent-specific benchmarks** like AgentBench, TRAIL, and AgentIF now test multi-step, tool-using capabilities rather than single-shot QA. **Record-and-replay patterns** (AgentRR paradigm) enable cost-effective regression testing. **DeepEval, RAGAS, and TruLens** dominate the evaluation ecosystem with different specializations.

For AlphaSwarm.sol specifically, the testing framework must support:
1. **Three test modes**: Quick (pattern-specific), Standard (area coverage), Thorough (full 50+ protocol corpus)
2. **SQLite-backed persistence** for historical comparison, regression detection, and trend analysis
3. **Golden test validation** for LLM reasoning quality using model-graded evidence scoring
4. **Orchestration replay** to record, analyze, and regression-test agent interactions
5. **Parallel execution** across protocols with isolated agent contexts

**Primary recommendation:** Build a layered testing architecture combining DeepEval's CI/CD integration for pattern regression, TruLens tracing for agent debugging, and a custom SQLite-backed corpus runner for longitudinal benchmarking. Use Claude Code skills for gap tracking, improvement testing, and consistency validation.

## Standard Stack

### Core Testing Frameworks

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| DeepEval | 1.4+ | Unit testing LLM outputs, CI/CD integration | 14+ metrics, red-teaming, pytest-native |
| RAGAS | 0.2+ | RAG-specific evaluation | Faithfulness, answer relevancy, context precision (LLM-powered) |
| TruLens | 1.0+ | Execution tracing + observability | Developer-first, trace instrumentation for agentic workflows |
| pytest-xdist | 3.8+ | Parallel test execution | 3.79x speedup achieved in Phase 8 research |
| SQLite | 3.45+ | Test result persistence | Zero-config, JSON columns for flexible schema |

### Supporting Tools

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-testmon | 2.2+ | Incremental testing | Local dev iterations (skip unchanged) |
| Anthropic Evals | - | Agent evaluation primitives | Task/trial/grader structure for agents |
| W&B Weave | 0.51+ | Visualization + team collaboration | Cross-run comparison, metric dashboards |
| LangSmith | - | Dataset versioning + human feedback | If using LangChain components |
| pytest-monitor | 1.6+ | CPU/memory tracking | Identifying resource-intensive tests |

### Benchmark Datasets

| Dataset | Size | Purpose | Source |
|---------|------|---------|--------|
| Damn Vulnerable DeFi (DVDeFi) | 13 challenges | Security training benchmark | github.com/theredguild/damn-vulnerable-defi (v4, Foundry) |
| LISABench | 10,185 vulns | Real-world audit corpus | 10 platforms: C4, OpenZeppelin, Sherlock, TrailOfBits, etc. |
| SmartBugs | 9,369 contracts | Classic vulnerability dataset | Injected vulnerabilities, 7 types |
| Code4rena/Sherlock | Ongoing | Live contest data | VigilSeek aggregator for tracking |

**Installation:**
```bash
# Core evaluation stack
uv add --dev deepeval ragas trulens-eval

# Already have pytest-xdist, pytest-testmon (Phase 8)

# Corpus tools
git clone https://github.com/theredguild/damn-vulnerable-defi.git .vrs/benchmarks/dvdefi
```

## Architecture Patterns

### Pattern 1: Three-Tier Testing Architecture

**What:** Separate quick regression tests, standard validation, and thorough GA-gate corpus testing

**Structure:**
```
tests/
├── unit/                      # Pattern-specific unit tests
│   ├── test_*_lens.py        # Existing pattern tests
│   └── test_golden_*.py      # Golden LLM reasoning tests
├── integration/               # Cross-pattern, multi-agent
│   ├── test_debate_protocol.py
│   └── test_orchestration.py
├── corpus/                    # Full benchmark suite
│   ├── test_corpus_runner.py # Main corpus executor
│   ├── protocols/            # 50+ protocol subdirs
│   └── ground_truth/         # Audit reports, exploit POMs
└── framework/
    ├── golden_tests.py       # LLM reasoning validation
    ├── corpus_db.py          # SQLite persistence
    └── orchestration_replay.py
```

**When to use:**
- **Quick mode** (`pytest tests/unit/ -k pattern_name`): Post-change regression (< 30s)
- **Standard mode** (`pytest tests/integration/`): Pre-commit validation (< 5min)
- **Thorough mode** (`pytest tests/corpus/`): GA gate, weekly regression (hours)

**Example:**
```python
# tests/corpus/test_corpus_runner.py
import pytest
from framework.corpus_db import CorpusDB
from true_vkg.kg.builder import VKGBuilder

@pytest.fixture(scope="session")
def corpus_db():
    return CorpusDB("tests/corpus/results.db")

@pytest.mark.corpus
@pytest.mark.parametrize("protocol", load_protocols())
def test_protocol_detection(protocol, corpus_db):
    """Run full BSKG detection pipeline per protocol."""
    # Build graph
    graph = VKGBuilder().build(protocol.contracts_path)

    # Run pattern engine
    findings = run_detection_pipeline(graph, protocol)

    # Compare to ground truth
    metrics = evaluate_findings(findings, protocol.ground_truth)

    # Persist to SQLite
    corpus_db.record_run(protocol.name, metrics, findings)

    # Assert thresholds
    assert metrics.recall >= protocol.min_recall
    assert metrics.precision >= protocol.min_precision
```

### Pattern 2: SQLite Corpus Database Schema

**What:** Time-series storage for corpus test results with regression detection

**Schema:**
```sql
CREATE TABLE corpus_runs (
    run_id TEXT PRIMARY KEY,
    timestamp INTEGER NOT NULL,
    vkg_version TEXT NOT NULL,
    mode TEXT NOT NULL, -- 'quick' | 'standard' | 'thorough'
    total_protocols INTEGER,
    git_commit TEXT
);

CREATE TABLE protocol_results (
    id INTEGER PRIMARY KEY,
    run_id TEXT NOT NULL,
    protocol_name TEXT NOT NULL,
    protocol_version TEXT,

    -- Detection metrics
    true_positives INTEGER,
    false_positives INTEGER,
    false_negatives INTEGER,
    precision REAL,
    recall REAL,
    f1_score REAL,

    -- Performance
    build_time_ms INTEGER,
    detection_time_ms INTEGER,
    total_time_ms INTEGER,

    -- LLM usage
    llm_calls INTEGER,
    total_tokens INTEGER,
    cost_usd REAL,

    -- Evidence quality (LLM-graded)
    avg_evidence_score REAL, -- 0.0-1.0

    -- Findings JSON
    findings_json TEXT, -- JSON array of finding objects

    FOREIGN KEY (run_id) REFERENCES corpus_runs(run_id)
);

CREATE INDEX idx_protocol_time ON protocol_results(protocol_name, run_id);

CREATE TABLE regression_alerts (
    id INTEGER PRIMARY KEY,
    detected_at INTEGER NOT NULL,
    protocol_name TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    previous_value REAL,
    current_value REAL,
    threshold_pct REAL, -- e.g., 0.10 for 10% drop
    severity TEXT -- 'critical' | 'high' | 'medium'
);
```

**Usage:**
```python
# Compare current run to baseline
def detect_regressions(db: CorpusDB, current_run_id: str, baseline_run_id: str):
    """Flag protocols with >10% metric drops."""
    query = """
        SELECT
            c.protocol_name,
            c.recall - b.recall AS recall_drop,
            c.precision - b.precision AS precision_drop
        FROM protocol_results c
        JOIN protocol_results b ON c.protocol_name = b.protocol_name
        WHERE c.run_id = ? AND b.run_id = ?
        AND (c.recall < b.recall * 0.9 OR c.precision < b.precision * 0.9)
    """
    return db.execute(query, (current_run_id, baseline_run_id))
```

### Pattern 3: Golden Tests for LLM Reasoning Quality

**What:** Store expected reasoning patterns, detect regressions in evidence quality

**Source:** Confident AI golden dataset pattern + Anthropic eval guidance

**Example:**
```python
# tests/framework/golden_tests.py
from dataclasses import dataclass
from typing import List
import json

@dataclass
class GoldenReasoning:
    """Expected reasoning for a test case."""
    finding_id: str
    protocol: str
    vulnerability_class: str

    # Expected reasoning elements
    must_mention: List[str]  # Key concepts (e.g., ["reentrancy", "CEI pattern"])
    must_trace: List[str]    # Code locations
    expected_confidence: str # "confirmed" | "likely" | "uncertain"

    # Grading rubric
    rubric: str = """
    Score 0-10:
    - Root cause identified (0-3 pts)
    - Code path traced (0-3 pts)
    - Impact articulated (0-2 pts)
    - Mitigation suggested (0-2 pts)
    """

def grade_reasoning(finding: dict, golden: GoldenReasoning, llm_grader) -> float:
    """Use LLM-as-judge to grade reasoning quality."""
    prompt = f"""
    Grade this security finding's reasoning quality using the rubric.

    Rubric: {golden.rubric}

    Expected to mention: {golden.must_mention}
    Expected to trace: {golden.must_trace}

    Finding:
    {json.dumps(finding, indent=2)}

    Provide:
    1. Score (0-10)
    2. What was present
    3. What was missing
    """

    response = llm_grader.grade(prompt)
    return response.score / 10.0  # Normalize to 0.0-1.0
```

### Pattern 4: Agent Orchestration Replay

**What:** Record agent interactions for debugging, regression testing, and cost analysis

**Source:** AgentRR record-and-replay paradigm + Anthropic transcript guidance

**Structure:**
```python
@dataclass
class OrchestrationTrace:
    """Complete record of agent orchestration run."""
    trace_id: str
    timestamp: int
    protocol: str
    finding_id: str

    # Agent interactions
    turns: List[AgentTurn]

    # Outcomes
    final_verdict: str
    confidence_bucket: str

    # Costs
    total_tokens: int
    total_cost_usd: float

@dataclass
class AgentTurn:
    """Single agent turn in orchestration."""
    agent_role: str  # "attacker" | "defender" | "verifier" | "arbiter"
    model: str       # "claude-opus-4-5" | "claude-sonnet-4-5"
    input_context: str
    output: str
    tool_calls: List[dict]
    tokens: int

def record_orchestration(trace: OrchestrationTrace, db: CorpusDB):
    """Persist orchestration trace to SQLite."""
    db.execute("""
        INSERT INTO orchestration_traces (
            trace_id, timestamp, protocol, finding_id,
            turns_json, final_verdict, total_tokens, total_cost_usd
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        trace.trace_id, trace.timestamp, trace.protocol, trace.finding_id,
        json.dumps([turn.__dict__ for turn in trace.turns]),
        trace.final_verdict, trace.total_tokens, trace.total_cost_usd
    ))

def replay_for_regression(trace_id: str, db: CorpusDB) -> OrchestrationTrace:
    """Retrieve trace and re-run with current BSKG version."""
    original = db.load_trace(trace_id)

    # Re-run with same inputs
    new_trace = orchestrate(
        protocol=original.protocol,
        finding_id=original.finding_id,
        input_context=original.turns[0].input_context
    )

    # Compare verdicts
    if new_trace.final_verdict != original.final_verdict:
        alert_regression(original, new_trace)

    return new_trace
```

### Pattern 5: Claude Code Skill for Testing

**What:** Specialized skills for gap tracking, targeted testing, consistency validation

**Source:** Claude Code best practices + skill authoring guide

**Example: Gap Tracker Skill**
```markdown
---
name: track-gap
description: Track a detection gap or limitation found during testing
allowed-tools: Read, Write, Grep
context: fork
agent: Explore
---

# Gap Tracking Skill

When a detection gap is found, record it systematically:

1. **Identify the gap**
   - What vulnerability class?
   - Which protocol/contract?
   - What should have been detected but wasn't?

2. **Root cause analysis**
   - Is this a builder.py limitation?
   - Pattern too strict?
   - LLM reasoning failure?
   - Missing VulnDocs knowledge?

3. **Record to gap log**
   Create/update `.planning/testing/gaps/${VULN_CLASS}.md`:

   ```markdown
   ## Gap: ${PROTOCOL} - ${FUNCTION}

   **Severity:** Critical | High | Medium | Low
   **Root Cause:** Builder | Pattern | LLM | Knowledge
   **Found:** YYYY-MM-DD

   ### Expected Detection
   [What should have been flagged]

   ### Actual Behavior
   [What happened instead]

   ### Impact
   [How this affects real audits]

   ### Fix Strategy
   [How to address - specific, actionable]
   ```

4. **Update gap summary**
   Maintain `.planning/testing/GAP-SUMMARY.md` with:
   - Total gaps by severity
   - Progress tracking
   - Prioritized fix queue
```

### Anti-Patterns to Avoid

- **Single test mode only:** GA gate corpus tests must be separate from quick regressions
- **No historical tracking:** Without SQLite persistence, can't detect gradual quality degradation
- **Manual evidence quality:** LLM-as-judge enables automated, scalable quality measurement
- **Synchronous corpus testing:** 50+ protocols must run in parallel for reasonable runtime
- **Hardcoded ground truth in tests:** Ground truth should be data-driven, versionable
- **No orchestration traces:** Can't debug agent interactions or measure cost per finding type

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM output evaluation | Regex/string matching | DeepEval G-Eval, LLM-as-judge | Semantic understanding, rubric-based scoring |
| Agent tracing | Manual logging | TruLens trace instrumentation | Structured spans, automatic tool tracking |
| Test parallelization | Threading/multiprocessing | pytest-xdist | Process isolation, load balancing (3.79x proven) |
| Reasoning quality grading | Heuristic scoring | Model-based graders with CoT | 10-15% improvement, explainable |
| Dataset versioning | Git submodules | LangSmith datasets or DVC | Metadata tracking, diff visualization |
| Regression detection | Manual comparison | SQLite time-series queries | Trend analysis, automated alerts |
| Ground truth parsing | Custom scrapers | Structured benchmark datasets | Community-validated, maintained |

**Key insight:** LLM evaluation is now a mature ecosystem. Hand-rolling evaluation logic misses calibration against human judgment, statistical significance testing, and integration with observability platforms.

## Common Pitfalls

### Pitfall 1: Over-reliance on Accuracy Metrics

**What goes wrong:** High accuracy masks poor performance on minority classes (rare vulnerabilities)

**Why it happens:** Imbalanced datasets - most functions are benign, critical vulns are rare

**How to avoid:**
- Use F1 score as primary metric (balances precision/recall)
- Stratify by severity - require 90%+ recall for critical/high
- Track per-vulnerability-class metrics separately

**Warning signs:**
- 95% accuracy but missing all critical vulnerabilities
- Pattern passes tests but fails on real protocols

**Source:** F1 score vulnerability detection research (2024-2026) shows deep learning models achieving 91% accuracy but only 2% F1 score due to extreme imbalance

### Pitfall 2: Golden Tests Without Calibration

**What goes wrong:** LLM-as-judge grades diverge from human expert judgment

**Why it happens:** Rubric not validated against human grading, judge model biases

**How to avoid:**
- Calibrate judge model on 20-50 human-graded examples first
- Measure inter-rater agreement (judge vs human)
- Use chain-of-thought prompting for explainability
- Test multiple judge models for robustness

**Warning signs:**
- Judge scores don't correlate with human review
- Same finding gets different scores on re-run
- Judge model "teaches to the test"

**Source:** Anthropic eval guidance emphasizes model-grader calibration as critical

### Pitfall 3: Session Fixtures with pytest-xdist

**What goes wrong:** Corpus database corrupted by concurrent writes from parallel workers

**Why it happens:** Each xdist worker is separate process, session fixtures run per-worker

**How to avoid:**
- Use `--dist loadfile` to group by protocol (one protocol = one worker)
- Implement file locking for shared SQLite access
- Or use worker-local databases, merge after

**Warning signs:**
- Tests pass serially, fail or deadlock in parallel
- SQLite "database locked" errors
- Corrupted test results database

**Source:** Phase 8 research identified this as major xdist pitfall

### Pitfall 4: Corpus Size Without Stratification

**What goes wrong:** 50 protocols, all simple DeFi lending, misses coverage gaps

**Why it happens:** Quantity without diversity - same vulnerability patterns repeated

**How to avoid:**
- Matrix categorization: vuln class × complexity level × protocol type
- Ensure representation: proxies, diamonds, cross-contract, oracles, governance
- Include adversarial "should not detect" protocols (false positive testing)

**Warning signs:**
- All protocols share similar architecture
- New vulnerability class discovered in production
- False positive rate unknown (no negative test cases)

**Source:** 07-CONTEXT.md emphasizes adversarial inclusion and matrix categorization

### Pitfall 5: No Orchestration Cost Tracking

**What goes wrong:** Thorough mode costs $500+ per run, blocks frequent testing

**Why it happens:** LLM calls for 50+ protocols × multi-agent debate add up fast

**How to avoid:**
- Track tokens/cost per protocol in SQLite schema
- Set cost budgets per test mode (Quick: $1, Standard: $10, Thorough: $200)
- Use Sonnet for volume tasks, Opus only for critical reasoning
- Implement early exit if cost exceeds budget

**Warning signs:**
- Surprise API bills after corpus run
- Can't afford to run thorough mode weekly
- No visibility into which protocols are expensive

**Source:** 07-CONTEXT.md specifies role-based model selection for cost optimization

## Code Examples

### Example 1: DeepEval Pattern Regression Test

```python
# tests/unit/test_golden_reentrancy.py
from deepeval import assert_test
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase

def test_reentrancy_reasoning_quality():
    """Golden test: Reentrancy detection must identify CEI violation."""

    # Run BSKG detection
    graph = load_graph("ReentrancyClassic.sol")
    finding = run_pattern(graph, "reentrancy-classic")[0]

    # Grade reasoning quality
    reasoning_metric = GEval(
        name="reentrancy_reasoning",
        criteria="Does the reasoning correctly identify the CEI pattern violation?",
        evaluation_steps=[
            "Verify read-external call-write sequence is mentioned",
            "Check if 'checks-effects-interactions' pattern is referenced",
            "Confirm impact on user balances is explained"
        ],
        threshold=0.7
    )

    test_case = LLMTestCase(
        input=finding["evidence"],
        actual_output=finding["reasoning"],
        expected_output="Should identify read-call-write ordering violation"
    )

    assert_test(test_case, [reasoning_metric])
```

**Source:** [DeepEval documentation](https://docs.confident-ai.com)

### Example 2: TruLens Agent Tracing

```python
# tests/framework/orchestration_replay.py
from trulens_eval import Tru, Feedback, Select
from trulens_eval.app import App

def test_debate_protocol_trace():
    """Trace multi-agent debate orchestration."""

    tru = Tru()

    # Wrap orchestration with tracing
    @tru.app(app_id="vkg-debate")
    def run_debate(finding_id: str):
        attacker_claim = attacker_agent.analyze(finding_id)
        defender_counter = defender_agent.analyze(finding_id, attacker_claim)
        verifier_check = verifier_agent.cross_check(attacker_claim, defender_counter)
        return arbiter_agent.decide(attacker_claim, defender_counter, verifier_check)

    # Define feedback functions
    f_relevance = Feedback(Select.output.relevance).on_output()
    f_consistency = Feedback(Select.output.consistency).on_output()

    # Run with tracing
    result = run_debate("VKG-042")

    # Query trace
    records = tru.get_records_and_feedback(app_ids=["vkg-debate"])[0]
    assert records[-1].output == "confirmed"
    assert records[-1].feedback_summary["relevance"] > 0.8
```

**Source:** [TruLens documentation](https://www.trulens.org/trulens_eval/getting_started/)

### Example 3: SQLite Corpus Regression Detection

```python
# tests/corpus/test_regression_detection.py
import sqlite3
from datetime import datetime, timedelta

def test_no_recall_regression(corpus_db):
    """Alert if any protocol's recall drops >10% from last week."""

    one_week_ago = int((datetime.now() - timedelta(days=7)).timestamp())

    query = """
    WITH latest_run AS (
        SELECT run_id FROM corpus_runs
        WHERE timestamp > ?
        ORDER BY timestamp DESC LIMIT 1
    ),
    baseline_run AS (
        SELECT run_id FROM corpus_runs
        WHERE timestamp < ?
        ORDER BY timestamp DESC LIMIT 1
    )
    SELECT
        c.protocol_name,
        c.recall AS current_recall,
        b.recall AS baseline_recall,
        (c.recall - b.recall) AS recall_change
    FROM protocol_results c
    JOIN protocol_results b ON c.protocol_name = b.protocol_name
    WHERE c.run_id = (SELECT run_id FROM latest_run)
    AND b.run_id = (SELECT run_id FROM baseline_run)
    AND c.recall < b.recall * 0.9
    """

    regressions = corpus_db.execute(query, (one_week_ago, one_week_ago)).fetchall()

    if regressions:
        report = "\n".join(
            f"  {p}: {cr:.1%} -> {br:.1%} (Δ {rc:.1%})"
            for p, cr, br, rc in regressions
        )
        pytest.fail(f"Recall regressions detected:\n{report}")
```

### Example 4: Claude Code Testing Skill

```markdown
---
name: test-improvement
description: Test a specific fix or improvement targeting a known gap
allowed-tools: Bash, Read, Write
context: fork
agent: Explore
---

# Test Improvement Skill

Validate that a fix addresses a specific gap without regressions.

## Input
Specify gap ID (e.g., "GAP-042") or pattern ID to test.

## Process

1. **Load gap context**
   Read `.planning/testing/gaps/*.md` to understand:
   - What was broken
   - Expected fix
   - Test protocol

2. **Run targeted test**
   ```bash
   # Quick regression for this pattern only
   pytest tests/unit/test_*_lens.py -k pattern_name -v

   # Test on specific protocol from gap
   pytest tests/corpus/ -k protocol_name --tb=short
   ```

3. **Compare before/after**
   Query corpus database for historical results:
   ```python
   SELECT precision, recall, f1_score
   FROM protocol_results
   WHERE protocol_name = ?
   ORDER BY timestamp DESC LIMIT 5
   ```

4. **Report outcome**
   Update gap file:
   - If fixed: Move to `## Fixed Gaps` section, add resolution date
   - If improved: Note progress, link to test run
   - If regression: Alert immediately, create incident report

5. **Side-effect check**
   Run full pattern lens test to ensure no regressions:
   ```bash
   pytest tests/unit/test_*_lens.py -v
   ```

## Output
Concise summary:
- ✅ Gap fixed, recall improved X% -> Y%
- ⚠️ Partial fix, precision decreased
- ❌ Still broken, needs different approach
```

## State of the Art (2026)

| Technique | Old Approach (2024) | Current Approach (2026) | Impact |
|-----------|---------------------|------------------------|--------|
| LLM evaluation | BLEU/ROUGE (reference-based) | LLM-as-judge with CoT | 10-15% reliability improvement |
| Agent testing | Single-shot QA benchmarks | Multi-step task completion (AgentBench) | Realistic capability measurement |
| Corpus size | 100s of contracts | 10,000+ with ground truth (LISABench) | Production-representative testing |
| Cost tracking | Manual/none | Per-protocol token/cost in DB | Enables cost-aware optimization |
| Reasoning quality | Manual review only | Automated grading + periodic human validation | Scalable quality assurance |
| Orchestration debugging | Print statements | Structured tracing (TruLens) | Root cause analysis for agent failures |
| Regression detection | Git bisect + manual testing | Time-series SQL queries with alerts | Proactive quality monitoring |

**Key 2026 Innovation: AgentRR Record-and-Replay**

The AgentRR paradigm (2025 research) enables:
- Record agent interaction traces during task execution
- Summarize into reusable "experiences"
- Replay with new BSKG versions for regression testing
- Dramatically reduce LLM costs for repeated tests

**Deprecated/outdated:**
- BLEU/ROUGE metrics for reasoning quality (superseded by semantic similarity)
- Single-process test execution (xdist parallelization is standard)
- Hardcoded test expectations in code (data-driven golden sets)
- Manual evidence quality review (LLM-grading at scale)

## Corpus Building Strategy

### Source Hierarchy

**Tier 1: Ground Truth Datasets (Use these first)**
1. **Damn Vulnerable DeFi (DVDeFi)** - 13 challenges, vulnerability-focused
   - URL: https://www.damnvulnerabledefi.xyz/
   - GitHub: https://github.com/theredguild/damn-vulnerable-defi
   - Status: v4 (Foundry, Solidity 0.8.25)
   - Use: Core benchmark for detection capability

2. **LISABench** - 10,185 verified vulnerabilities
   - GitHub: https://github.com/agentlisa/bench
   - Sources: Code4rena, OpenZeppelin, Halborn, Sherlock, TrailOfBits
   - Use: Real-world corpus with audit report ground truth

3. **SmartBugs** - 9,369 vulnerable contracts
   - URL: https://smartbugs.github.io/
   - Types: 7 vulnerability classes, injected
   - Use: False positive testing (known safe contracts)

**Tier 2: Contest Platforms (Manual ground truth extraction)**
1. **Code4rena** - https://code4rena.com/audits
2. **Sherlock** - https://audits.sherlock.xyz/
3. **Immunefi** - https://immunefi.com/
4. **Cantina** - https://cantina.xyz/
5. **Codehawks** - https://www.codehawks.com/

**Aggregator:** VigilSeek (https://www.vigilseek.com/) tracks contests across platforms

### Ground Truth Labeling Methodology

**For Contest Data (Code4rena, Sherlock):**
1. **Parse audit reports** - Extract vulnerability findings
   - Contract name + function
   - Severity (Critical/High/Medium/Low)
   - Vulnerability class (reentrancy, access control, etc.)
   - Root cause explanation
   - Line numbers (if available)

2. **Structure per protocol:**
```yaml
protocol: "protocol-name"
contest_url: "https://..."
audit_report: "path/to/report.md"
version: "exploited"  # or "fixed"
ground_truth:
  - finding_id: "H-1"
    severity: "high"
    vulnerability_class: "reentrancy"
    contract: "Vault.sol"
    function: "withdraw"
    lines: [123, 145]
    description: "CEI pattern violation allows recursive withdrawal"
    exploited: true
  - finding_id: "M-2"
    severity: "medium"
    vulnerability_class: "access-control"
    contract: "Admin.sol"
    function: "setConfig"
    lines: [67]
    description: "Missing access control on admin function"
    exploited: false
```

3. **Include both versions:**
   - Original (exploited) version
   - Fixed version (from resolution PR)
   - Enables detection delta testing

**For Exploit Post-Mortems (Immunefi, Rekt):**
- Higher confidence ground truth (real monetary loss)
- Include exploit transaction hash
- Link to post-mortem analysis
- Mark as "critical-proven"

**Metadata Schema:**
```python
@dataclass
class ProtocolGroundTruth:
    name: str
    version: str  # git hash or version tag
    source_url: str
    audit_reports: List[str]
    complexity_rating: str  # "simple" | "medium" | "complex"
    protocol_type: str  # "lending" | "dex" | "yield" | "nft" | "dao" | "vault"
    proxy_type: Optional[str]  # "EIP-1967" | "UUPS" | "Diamond" | None

    vulnerabilities: List[Vulnerability]

    # Testing thresholds
    min_recall: float = 0.70
    min_precision: float = 0.80

@dataclass
class Vulnerability:
    finding_id: str
    severity: str
    vulnerability_class: str
    contract: str
    function: str
    lines: Optional[List[int]]
    description: str
    exploited: bool
    exploit_tx: Optional[str]  # If real exploit
```

### 50+ Protocol Selection Strategy

**Core 15 (Deep Investigation):**
| Protocol | Type | Complexity | Key Challenges |
|----------|------|------------|----------------|
| Uniswap V3 | DEX | High | Concentrated liquidity, tick math |
| Aave V3 | Lending | High | Multi-collateral, flash loans |
| Compound V3 | Lending | Medium | Collateral tracking |
| MakerDAO | Stablecoin | High | Multi-module, governance |
| Curve Finance | DEX | Medium | Stableswap invariants |
| Yearn V3 | Yield | High | Strategy composition |
| Balancer V2 | DEX | High | Weighted pools, composability |
| SushiSwap | DEX | Medium | Fork with extensions |
| Synthetix | Derivatives | High | Oracle dependencies |
| Convex | Yield | Medium | Gauge manipulation risks |
| Euler Finance | Lending | High | Soft liquidations (exploited) |
| Ren Protocol | Bridge | Medium | Cross-chain messaging |
| GMX V2 | Perps | High | Perpetual futures, funding rates |
| Ribbon Finance | Options | Medium | Vault strategies |
| Olympus DAO | Reserve | Medium | Bonding mechanisms |

**Remaining 35+ (Surface Coverage):**
- Ensure representation across:
  - 3 proxy types (EIP-1967, UUPS, Diamond)
  - 5 protocol types (lending, DEX, yield, NFT, DAO)
  - 4 complexity levels (simple, medium, complex, adversarial)
- Include known hard cases from CONTEXT.md:
  - Delegatecall patterns (Truster DVDeFi)
  - Strict equality (Unstoppable DVDeFi)
  - Callback patterns (Side Entrance DVDeFi)

**Adversarial Subset (10 protocols):**
- Audited-clean protocols (false positive testing)
- Obfuscated code (renamed functions, split logic)
- Edge cases from known BSKG limitations

### Corpus Storage Structure

```
tests/corpus/
├── protocols/
│   ├── uniswap-v3/
│   │   ├── contracts/          # Source code
│   │   ├── ground_truth.yaml   # Labeled vulnerabilities
│   │   └── metadata.yaml       # Protocol info
│   ├── aave-v3/
│   └── ...
├── results.db                  # SQLite test results
├── ground_truth/
│   ├── audit_reports/          # Original reports
│   └── exploit_poms/           # Post-mortems
└── test_corpus_runner.py       # Main test executor
```

## LLM Evaluation Patterns

### Pattern 1: LLM-as-Judge with Chain-of-Thought

**What:** Use secondary LLM to grade evidence quality with step-by-step reasoning

**Source:** G-Eval framework (SOTA 2026), achieves 10-15% improvement over direct scoring

**Implementation:**
```python
def grade_finding_quality(finding: dict, rubric: str) -> tuple[float, str]:
    """Grade finding using LLM-as-judge with CoT."""

    prompt = f"""
You are an expert security auditor grading the quality of a vulnerability finding.

# Rubric
{rubric}

# Finding
Contract: {finding['contract']}
Function: {finding['function']}
Severity: {finding['severity']}

Evidence:
{finding['evidence']}

Reasoning:
{finding['reasoning']}

# Your Task
1. Think step-by-step through each rubric criterion
2. Provide your reasoning for each score
3. Assign final score (0-10)

Output format:
Criterion 1: [score] - [reasoning]
Criterion 2: [score] - [reasoning]
...
Final Score: [total]/10
"""

    response = llm_grader(prompt, model="claude-sonnet-4-5")

    # Parse score and reasoning
    score = extract_score(response)
    reasoning = response.strip()

    return score / 10.0, reasoning
```

**Calibration Process:**
1. Human expert grades 20-50 findings
2. Compare LLM grades to human grades
3. Measure agreement (Cohen's kappa > 0.6 acceptable)
4. Refine rubric if disagreement high
5. Re-test on new sample

### Pattern 2: RAGAS Metrics for Evidence Quality

**What:** Specialized metrics for RAG-like evidence retrieval (VulnDocs → findings)

**Metrics:**
- **Faithfulness**: Can finding be inferred from evidence alone?
- **Answer Relevancy**: Does reasoning address the vulnerability question?
- **Context Precision**: Is evidence focused on relevant code?

**Implementation:**
```python
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision

def evaluate_evidence_quality(findings: List[dict]) -> dict:
    """Use RAGAS to measure evidence quality."""

    dataset = {
        "question": [f"Is {f['function']} vulnerable to {f['vuln_class']}?"
                     for f in findings],
        "answer": [f["reasoning"] for f in findings],
        "contexts": [[f["evidence"]] for f in findings],
        "ground_truth": [f["expected_reasoning"] for f in findings]
    }

    result = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision]
    )

    return result
```

### Pattern 3: Pass@k vs Pass^k Metrics

**What:** Measure both "any success" and "consistent success" for agent tasks

**Source:** Anthropic eval guidance for agents

**Definitions:**
- **pass@k**: Probability of at least one correct solution in k attempts
- **pass^k**: Probability that all k trials succeed

**Use Cases:**
- pass@k: Detection capability (did agent find vuln in any trial?)
- pass^k: Reliability (does agent consistently produce quality?)

**Implementation:**
```python
def calculate_pass_at_k(results: List[bool], k: int) -> float:
    """Calculate pass@k: at least one success in k trials."""
    # Binomial probability: 1 - P(all fail)
    fail_rate = sum(1 for r in results if not r) / len(results)
    return 1 - (fail_rate ** k)

def calculate_pass_hat_k(results: List[bool], k: int) -> float:
    """Calculate pass^k: all k trials succeed."""
    success_rate = sum(1 for r in results if r) / len(results)
    return success_rate ** k

# Example usage for pattern detection
trials_per_protocol = 3  # Run each protocol 3 times

for protocol in protocols:
    trial_results = []
    for trial in range(trials_per_protocol):
        findings = run_detection(protocol)
        correct = evaluate_findings(findings, protocol.ground_truth)
        trial_results.append(correct)

    # At least one trial detected the vulnerability
    detection_capability = calculate_pass_at_k(trial_results, k=3)

    # All three trials consistent
    detection_reliability = calculate_pass_hat_k(trial_results, k=3)

    print(f"{protocol}: pass@3={detection_capability:.1%}, pass^3={detection_reliability:.1%}")
```

### Pattern 4: Severity-Stratified Metrics

**What:** Different thresholds for critical vs low severity findings

**Source:** 07-CONTEXT.md requirements

**Thresholds:**
- Critical/High: 90%+ recall required
- Medium: 80%+ recall
- Low: 70%+ recall
- Precision: 95% (Tier A), 80% (Tier B) across all severities

**Implementation:**
```python
def evaluate_stratified(findings: List[dict], ground_truth: List[dict]) -> dict:
    """Calculate metrics stratified by severity."""

    severities = ["critical", "high", "medium", "low"]
    metrics = {}

    for severity in severities:
        # Filter to this severity only
        gt_sev = [v for v in ground_truth if v["severity"] == severity]
        findings_sev = [f for f in findings if f["severity"] == severity]

        # Calculate precision/recall for this severity
        tp = len(set(f["finding_id"] for f in findings_sev) &
                 set(v["finding_id"] for v in gt_sev))
        fp = len(findings_sev) - tp
        fn = len(gt_sev) - tp

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0

        metrics[severity] = {
            "precision": precision,
            "recall": recall,
            "f1": 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        }

        # Check threshold
        threshold = 0.90 if severity in ["critical", "high"] else 0.70
        metrics[severity]["passed"] = recall >= threshold

    return metrics
```

## Claude Code Skill/Agent Patterns

### Pattern 1: Specialized Testing Skills

**Architecture:** Multiple focused skills > one monolithic skill

**Skills Needed for Phase 7:**

1. **`/track-gap`** - Record detection gaps systematically
2. **`/test-improvement`** - Validate fixes for known gaps
3. **`/corpus-summary`** - Generate corpus test reports
4. **`/check-consistency`** - Validate test/corpus alignment
5. **`/analyze-regression`** - Deep-dive on metric drops

**Design Principles:**
- Each skill has clear, single purpose
- Use `context: fork` for isolated exploration
- Specify `allowed-tools` to limit scope
- Include examples in skill documentation

**Example: `/corpus-summary` skill**
```markdown
---
name: corpus-summary
description: Generate comprehensive summary of corpus test results
allowed-tools: Bash, Read
context: fork
agent: Explore
---

# Corpus Test Summary Generator

Generate a human-readable summary from SQLite corpus results.

## Usage
`/corpus-summary [run_id]` - Summarize specific run
`/corpus-summary latest` - Most recent run

## Output Format

### Executive Summary
- Total protocols tested
- Overall metrics (precision, recall, F1)
- Regressions detected
- Cost analysis

### By Vulnerability Class
- Recall per class
- Top missed vulnerabilities
- False positive hotspots

### By Protocol Type
- DeFi vs NFT vs DAO performance
- Complexity correlation

### Recommendations
- Which gaps to prioritize
- Estimated improvement impact
```

### Pattern 2: Two-Claude Testing Pattern

**What:** One Claude designs tests, another Claude validates independently

**Source:** Claude Code best practices

**Process:**
1. **Claude A (Designer)**: Create test plan based on gaps
2. **Claude B (Validator)**: Execute tests without seeing plan
3. Compare outcomes - disagreements surface assumptions
4. Iterate until both agree

**Implementation:**
```bash
# Terminal 1: Claude A - Design
claude code
> /plan-test gap-042

# Claude A creates test_gap_042.py with expectations

# Terminal 2: Claude B - Validate
claude code
> Run test_gap_042.py and tell me if it makes sense

# Claude B executes, reports findings independently
```

### Pattern 3: Subagent for Deep Investigation

**What:** Spawn fresh-context subagent for specific investigation

**When to use:**
- Evidence quality degraded on specific protocol
- Need to understand why pattern is failing
- Root cause analysis without polluting main context

**Example:**
```markdown
---
name: investigate-failure
description: Deep-dive on why a specific test is failing
context: fork
agent: Explore
allowed-tools: Read, Grep, Bash
---

# Failure Investigation

Spawn fresh context to investigate test failure without assumptions.

## Input
- Test name or protocol name
- Failure symptom (FP, FN, error)

## Process
1. Read test file and understand expectations
2. Load protocol contracts and ground truth
3. Run BSKG detection pipeline with verbose logging
4. Compare expected vs actual findings
5. Identify root cause:
   - Builder limitation?
   - Pattern too strict/loose?
   - Missing VulnDocs knowledge?
   - LLM reasoning failure?

## Output
- Root cause identified
- Proposed fix strategy
- Related tests that might be affected
```

## Open Questions

### 1. Corpus Test Frequency
**What we know:**
- Quick mode should run pre-commit (< 30s)
- Thorough mode targets GA gate + weekly
**What's unclear:** Standard mode frequency? Daily? Per-PR?
**Recommendation:** Daily scheduled run, alert on regressions

### 2. LLM Grader Model Choice
**What we know:** Model-graders need calibration against human judgment
**What's unclear:** Use Opus or Sonnet for grading? Haiku fast enough?
**Recommendation:** Start with Sonnet (cost/speed), validate with Opus on sample, consider Haiku if batch grading

### 3. Historical Corpus Results Retention
**What we know:** SQLite stores all runs for time-series
**What's unclear:** How long to retain? Disk space concerns?
**Recommendation:** Keep all data for first 3 months, then monthly snapshots

### 4. Ground Truth Version Control
**What we know:** Need both exploited + fixed versions
**What's unclear:** Store in Git or Git-LFS? Separate repo?
**Recommendation:** Git submodules per protocol, LFS for large codebases

## Sources

### Primary (HIGH confidence)

#### LLM Evaluation Frameworks
- [LLM Testing in 2026: Top Methods and Strategies](https://www.confident-ai.com/blog/llm-testing-in-2024-top-methods-and-strategies) - DeepEval, G-Eval, golden datasets
- [Building an LLM evaluation framework: best practices | Datadog](https://www.datadoghq.com/blog/llm-evaluation-framework-best-practices/) - Metrics, graders, calibration
- [Best LLM Evaluation Tools: Top 9 Frameworks | ZenML](https://www.zenml.io/blog/best-llm-evaluation-tools) - Tool comparison, RAG-specific
- [Demystifying Evals for AI Agents | Anthropic](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) - Task/trial/grader framework
- [Claude Code: Best practices for agentic coding | Anthropic](https://www.anthropic.com/engineering/claude-code-best-practices) - Testing patterns, TDD
- [Extend Claude with skills | Claude Code Docs](https://code.claude.com/docs/en/skills) - Skill structure, invocation

#### Agent Benchmarking
- [10 AI agent benchmarks | Evidently AI](https://www.evidentlyai.com/blog/ai-agent-benchmarks) - AgentBench, TRAIL, BALROG
- [AgentBench: Comprehensive Benchmark to Evaluate LLMs as Agents | GitHub](https://github.com/THUDM/AgentBench) - 8 environments, multi-turn
- [TRAIL: Benchmark for Agentic Evaluation | Patronus AI](https://www.patronus.ai/blog/introducing-trail-a-benchmark-for-agentic-evaluation) - Debug complex workflows
- [Rethinking LLM Benchmarks for 2025 | Fluid AI](https://www.fluid.ai/blog/rethinking-llm-benchmarks-for-2025) - Agentic vs static

#### Orchestration & Replay
- [LLM Orchestration in 2026 | AIMultiple](https://research.aimultiple.com/llm-orchestration/) - Frameworks, patterns
- [Get Experience from Practice: AgentRR | arXiv](https://arxiv.org/html/2505.17716v1) - Record & replay paradigm
- [LLM Observability for Multi-Agent Systems | Medium](https://medium.com/@arpitchaukiyal/llm-observability-for-multi-agent-systems-part-1-tracing-and-logging-what-actually-happened-c11170cd70f9) - Tracing patterns

#### Smart Contract Corpora
- [Damn Vulnerable DeFi](https://www.damnvulnerabledefi.xyz/) - 13 challenges, v4
- [SmartBugs: Dataset of Vulnerable Solidity Contracts](https://smartbugs.github.io/) - 9,369 contracts
- [LISABench | GitHub](https://github.com/agentlisa/bench) - 10,185 verified vulnerabilities
- [Forge: LLM-driven Vulnerability Dataset Construction | ICSE 2026](https://nzjohng.github.io/publications/papers/icse2026.pdf) - Benchmark 13 tools
- [Bad Randomness Benchmark Dataset | arXiv](https://arxiv.org/html/2601.09836) - 1,758 contracts, SWC-120

#### Contest Platforms
- [Code4rena Audits](https://code4rena.com/audits) - DeFi contests
- [Sherlock Audits](https://audits.sherlock.xyz/) - Crowdsourced audits
- [VigilSeek - Charts](https://www.vigilseek.com/charts) - Contest aggregator
- [Comparison: Code4rena vs Sherlock | HackenProof](https://hackenproof.com/blog/for-business/code4rena-vs-sherlock-crowdsourced-audits-comparison-guide)

### Secondary (MEDIUM confidence)

#### Metrics & Evaluation
- [LLM-as-a-Judge Systems | Medium](https://medium.com/@puttt.spl/how-to-build-llm-as-a-judge-systems-for-automated-quality-scoring-2026-blueprint-18b1838765df) - Chain-of-thought grading
- [F1 Score for Vulnerability Detection | PDF](https://rebels.cs.uwaterloo.ca/papers/tse2024_chakraborty.pdf) - DeepWukong evaluation
- [Classification Metrics | Google ML](https://developers.google.com/machine-learning/crash-course/classification/accuracy-precision-recall) - Precision/recall/F1
- [What is F1 score? | Openlayer](https://www.openlayer.com/blog/post/f1-score-precision-recall-balance) - Imbalanced data

#### Testing Infrastructure
- [Pytest Parallel Execution | Johal.in](https://johal.in/pytest-parallel-execution-for-large-test-suites-in-python-2025/) - Architecture patterns
- [SQLite Testing Documentation](https://sqlite.org/testing.html) - Schema patterns
- [SQLite Time Series | MoldStud](https://moldstud.com/articles/p-handling-time-series-data-in-sqlite-best-practices) - Best practices

### Tertiary (LOW confidence - verify before use)

- Ground truth labeling methodology - no direct 2026 source found, synthesized from security audit practices
- Cost tracking per protocol - common practice but not standardized

## Metadata

**Confidence breakdown:**
- LLM evaluation tools/frameworks: HIGH - Multiple authoritative sources (Anthropic, Confident AI, ZenML)
- Agent benchmarking: HIGH - Recent papers, active research (AgentBench, TRAIL)
- Corpus datasets: HIGH - Established benchmarks (DVDeFi, SmartBugs, LISABench)
- Orchestration patterns: MEDIUM - Industry practices, no single standard
- Ground truth methodology: MEDIUM - Synthesized from audit practices, needs validation

**Research date:** 2026-01-21
**Valid until:** 60 days (LLM tooling evolves rapidly, benchmark datasets stable)

**Key assumptions:**
1. Phase 5 (Semantic Labeling) completes before Phase 7 begins
2. Claude Code remains primary orchestration environment
3. Budget allows for Opus/Sonnet hybrid model usage
4. 50+ protocols accessible via public sources (contests, GitHub)

**Risks:**
- **Corpus availability:** Contest protocols may have licensing restrictions
- **LLM cost:** Thorough mode with 50+ protocols × multi-agent could exceed budget
- **Ground truth quality:** Manual labeling from audit reports is labor-intensive
- **Calibration drift:** LLM-as-judge needs periodic re-calibration as models update
