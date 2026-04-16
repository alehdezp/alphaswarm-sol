# Research Report: Interactive Agent Testing Improvements (March 2026)

**Date:** 2026-03-01
**Sources:** 4 parallel research agents, 70+ papers/frameworks/tools surveyed
**Scope:** Latest techniques for improving interactive testing of agents in Claude Code

---

## Executive Summary

Four research domains were surveyed in parallel, yielding **high-impact findings** across Claude Code platform updates, evaluation science, self-improvement techniques, and workflow testing. The most transformative findings are:

1. **Claude Agent SDK** eliminates the biggest infrastructure pain point (binary staleness) and provides programmatic agent control with true tool restriction
2. **Meta-Evaluation Collapse** proves that dual-evaluator agreement is insufficient — ground truth anchoring is mandatory
3. **Agent Behavioral Contracts (ABC)** provides the formal foundation for evaluation contracts with mathematical drift bounds
4. **MARS dual reflection** enables practical self-improvement in a single reflection pass
5. **SkillsBench** proves ungoverned self-improvement is harmful (zero average improvement across 7,308 trajectories)

---

## TOP 10 Actionable Improvements

Ordered by impact-to-effort ratio, mapped to AlphaSwarm.sol's existing framework.

### 1. MIGRATE TO CLAUDE AGENT SDK (Impact: CRITICAL | Effort: Medium)

**What:** Replace Agent Teams spawning with `claude-agent-sdk` Python library (`pip install claude-agent-sdk`).

**Why:** Eliminates ALL 5 failure modes from Plan 12 Batch 1:
- Binary staleness (SDK manages its own lifecycle)
- Context leakage (`allowed_tools` + `cwd` isolation + custom MCP tools)
- Transcript parsing (Python-function hooks capture everything in-process)
- Shared graph state (each `query()` call runs in isolated `cwd`)
- Team coordination overhead (direct programmatic control)

**Architecture:**
```
Evaluation Runner (Python)
  +-- query(prompt, options=ClaudeAgentOptions(
  |       allowed_tools=["mcp__eval__build_kg", "mcp__eval__query", "Read"],
  |       cwd="/isolated/contract/dir",
  |       hooks={"PostToolUse": [observe_fn], "Stop": [capture_fn]},
  |       max_turns=30
  |   ))
  +-- Custom MCP Server (@tool decorator)
  |       build_kg() -> wraps CLI, logs usage
  |       query() -> wraps CLI, logs queries + results
  |       read_contract() -> wraps Read, restricts to contract dir
  +-- Scoring Pipeline (processes observation log)
```

**Sources:** Claude Agent SDK docs, Promptfoo `anthropic:claude-agent-sdk` provider, Langfuse agent skill evaluation blog (2026-02-26)

---

### 2. ANCHOR EVALUATORS IN GROUND TRUTH (Impact: CRITICAL | Effort: Low)

**What:** Create 50-100 expert-labeled agent transcripts with known-good and known-bad reasoning as calibration anchors.

**Why:** The "Meta-Evaluation Collapse" paper (ICLR 2026 submission) proves that recursive LLM-based evaluation converges toward internally consistent but fragile fixed points **detached from ground truth**. Two Opus evaluators CAN reach high agreement while being systematically wrong. Without anchoring, the dual-evaluator system will drift.

**The fix is cheap:** Calibrate on 5% oracle labels (CJE paper: 99% ranking accuracy at 14x lower cost).

**Implementation:**
1. Select 50 transcripts spanning the quality spectrum (10 excellent, 20 good, 10 mediocre, 10 bad)
2. Expert-label each with ground-truth reasoning scores per 7-move dimension
3. Run dual-Opus evaluator on same transcripts periodically
4. If evaluator scores drift >15% from ground truth: recalibrate

**Sources:** Meta-Evaluation Collapse (ICLR 2026), CJE (arXiv:2512.11150), PRECISE (AAAI 2026), The Progress Illusion (EMNLP 2025)

---

### 3. FORMALIZE EVALUATION CONTRACTS WITH ABC (Impact: HIGH | Effort: Medium)

**What:** Replace ad-hoc evaluation contracts with Agent Behavioral Contracts: C = (P, I, G, R).

**Why:** The ABC framework (arXiv:2602.22302, Feb 25, 2026) provides:
- **Probabilistic compliance** (not binary pass/fail) — accounts for LLM unpredictability
- **Drift Bounds Theorem** — contracts with recovery rate gamma > alpha bound drift to D* = alpha/gamma
- **Safe Composition** — mathematical guarantees for multi-agent chains (attacker -> defender -> verifier)
- <10ms overhead per action

**Contract structure per workflow:**
```yaml
contract:
  preconditions:
    - graph_built_successfully
    - tools_available: [build-kg, query]
    - contract_loaded
  invariants:
    - graph_first_enforcement  # MUST query before concluding
    - evidence_required         # No unsupported claims
    - no_fabrication            # Anti-hallucination gate
  governance:
    - token_budget: 6000
    - tool_restriction: [build-kg, query, Read]
    - isolation: worktree
  recovery:
    - on_empty_query: retry_with_reformulated_query
    - on_tool_failure: escalate_to_human
    - on_budget_exceeded: summarize_and_conclude
```

**Also adopt:** Relari Agent Contracts YAML format for practical implementation.

**Sources:** ABC (arXiv:2602.22302), Relari Agent Contracts (GitHub), AgentSpec (arXiv:2503.18666)

---

### 4. IMPLEMENT MARS DUAL REFLECTION (Impact: HIGH | Effort: Low)

**What:** After each evaluation batch, extract dual reflections:
- **Principle-based:** Normative rules to prevent errors ("Always verify graph queries return results before drawing conclusions")
- **Procedural:** Step-by-step strategies for success ("When querying for access control, check modifier presence AND function visibility")

**Why:** MARS (arXiv:2601.11974, Jan 2026) achieves self-improvement in ONE reflection pass — not multi-turn recursive loops — at drastically lower cost. Outperforms multi-turn self-critique across 6 benchmarks.

**Implementation:**
1. After batch evaluation, collect all failures
2. Prompt Opus: "Extract 3-5 normative rules these failures violate"
3. Prompt Opus: "Extract 3-5 procedural strategies from the successes"
4. Store reflections in structured format
5. Propose prompt modifications based on reflections
6. Test in worktree sandbox -> compare scores -> human approve

**Sources:** MARS (arXiv:2601.11974), ICML 2025 metacognition position paper

---

### 5. BUILD FAILURE-TO-TEST-CASE PIPELINE (Impact: HIGH | Effort: Low)

**What:** Every failed evaluation automatically becomes a new regression test case.

**Why:** Multiple production systems (Arize, Adaline, Amazon) converge on this pattern. Combined with DoVer's intervention debugging (arXiv:2512.06749v2), failures can be automatically diagnosed and converted to targeted tests.

**Pipeline:**
```
Failed Evaluation
  -> Classify failure mode (policy refusal / task resignation / scaffold non-compliance / fabrication)
  -> Extract minimal reproduction (contract + prompt + tool sequence)
  -> Generate hypothesis about root cause (DoVer-style)
  -> Create regression test YAML (Relari format)
  -> Add to regression suite
  -> Track fix rate over time
```

**Failure taxonomy (from UK AISI / NIST):**
1. Policy compliance refusal (agent refuses to analyze pattern)
2. Task resignation (agent gives up on complex analysis)
3. Scaffold non-compliance (agent ignores CLI tools)
4. False completion (agent claims done but state contradicts)
5. Fabrication (agent invents evidence)

**Sources:** AISI transcript analysis, NIST CAISI, DoVer (Microsoft), Adaline regression protocol

---

### 6. REPLACE 15-POINT THRESHOLD WITH STATISTICAL TESTING (Impact: HIGH | Effort: Medium)

**What:** Replace the fixed 15-point disagreement threshold between dual evaluators with statistically principled methods.

**Why:** Current threshold is arbitrary. Research provides three better alternatives:

| Method | Source | Approach |
|--------|--------|----------|
| Permutation testing | Hebbia (Sep 2025) | Test if score difference is statistically significant given evaluator variance |
| Beta-Binomial + KS-test | NeurIPS 2025 | Adaptive stopping based on distributional similarity |
| Calibrated CIs | CJE (Dec 2025) | Oracle-uncertainty-aware confidence intervals |

**Also upgrade from:** simple dual-evaluator to reasoning tree divergence analysis (AgentAuditor, arXiv:2602.09341). When evaluators disagree, build a tree from both assessment traces and audit the specific divergence point — not just flag "disagreement."

**Sources:** AgentAuditor (Feb 2026), Hebbia consensus framework, D3: Debate Deliberate Decide (arXiv:2410.04663)

---

### 7. IMPLEMENT CURRICULUM SCHEDULING (Impact: HIGH | Effort: Medium)

**What:** Use Multi-Armed Bandit scheduling to select test contracts by difficulty.

**Why:** Self-Evolving Curriculum (SEC, Mila/ServiceNow) achieves 13-33% improvement on out-of-distribution tasks. TAROT (Feb 2026) adds that optimal curriculum depends on model capability — weaker agents need easy-first, stronger agents benefit from hard-first.

**Implementation:**
```python
# Categories mapped to difficulty tiers
TIERS = {
    "basic_reentrancy": 1,
    "cross_function_access_control": 2,
    "complex_oracle_manipulation": 3,
    "novel_defi_composability": 4
}

# MAB selection (Thompson Sampling)
def select_next_contract(history):
    for tier in TIERS:
        alpha = successes[tier] + 1
        beta = failures[tier] + 1
        scores[tier] = np.random.beta(alpha, beta)
    # Maximize learning: prefer tiers near 50% success rate (ZPD)
    return tier_with_highest_learning_signal(scores)
```

**Also add:** Historical revisiting (AdaCuRL) — periodically re-test on mastered tiers to prevent forgetting.

**Sources:** SEC (arXiv:2505.14970), TAROT (arXiv:2602.15449), AdaCuRL (arXiv:2511.09478)

---

### 8. ADOPT TRACE DIFF FOR REGRESSION DETECTION (Impact: MEDIUM | Effort: Medium)

**What:** Record golden baseline evaluation traces, diff against new runs to detect behavioral drift.

**Why:** agent-replay (GitHub, Feb 28, 2026) provides time-travel debugging with diff/fork capabilities. Combined with behavioral fingerprinting (97.2% F1 in agent identification from 41 features), this detects subtle drift before it causes evaluation failures.

**Track per session:**
- Tool call sequence patterns (frequency, order, diversity)
- Query formulation patterns (specificity, graph-first compliance)
- Reasoning structure (which 7 moves appear, in what order)
- Evidence citation patterns (count, specificity, graph grounding)
- Time-to-conclusion and token consumption

**Alert when:** Agent Stability Index (composite of 12 dimensions) diverges beyond threshold.

**Sources:** agent-replay, behavioral fingerprinting (arXiv:2601.17406), agent drift framework (arXiv:2601.04170)

---

### 9. DYNAMIC RUBRIC EVOLUTION (Impact: MEDIUM | Effort: High)

**What:** Let the 7-move reasoning decomposition evolve based on observed data, not remain static.

**Why:** Three converging ICLR 2026 papers show dynamic rubrics outperform static:
- **OnlineRubrics:** Rubrics evolve via pairwise comparison (up to 8% improvement)
- **Rubric-ARM:** Joint rubric-judge optimization prevents collapse
- **AutoLibra:** Transforms open-ended feedback into evaluation metrics automatically

**Implementation:** After each evaluation batch, use AutoLibra's approach to check if the 7 existing moves still capture the most important reasoning dimensions. If agents exhibit a new failure mode not covered by existing moves, propose a new rubric dimension.

**Sources:** OnlineRubrics (ICLR 2026), Rubric-ARM (arXiv:2602.01511), AutoLibra (ICLR 2026)

---

### 10. ACTIVE GOVERNANCE REGISTRY (Impact: MEDIUM | Effort: Low)

**What:** Formalize a constraints-registry.json mapping every governance rule to its canonical source.

**Why:** SkillsBench (7,308 trajectories) proved self-generated skills show **zero average improvement** while curated skills improve by 16.2 points. Ungoverned self-improvement is actively harmful. Blake Crosley's synthesis (Feb 2026) of 6 research papers converges on a three-file runtime constitution:

```
constitution.md          -> Immutable behavioral constraints
capabilities.json        -> Skill inventory with provenance
constraints-registry.json -> Maps every constraint to canonical source
```

**Our mapping:**
- `constitution.md` = CLAUDE.md + TESTING-PHILOSOPHY.md (immutable)
- `capabilities.json` = evaluation contracts (evolving, governed)
- `constraints-registry.json` = new file linking constraints to sources

**Sources:** SkillsBench, Runtime Constitutions (Crosley, Feb 2026), Agent Skills Survey (arXiv:2602.12430)

---

## IMPLEMENTATION PRIORITY MATRIX

| # | Improvement | Effort | Impact | Risk | Priority |
|---|------------|--------|--------|------|----------|
| 1 | Claude Agent SDK migration | Medium | Critical | Low | **P0** |
| 2 | Ground truth calibration anchors | Low | Critical | Low | **P0** |
| 4 | MARS dual reflection | Low | High | Low | **P0** |
| 5 | Failure-to-test-case pipeline | Low | High | Low | **P0** |
| 10 | Active governance registry | Low | Medium | Low | **P0** |
| 3 | ABC formal contracts | Medium | High | Low | **P1** |
| 6 | Statistical disagreement testing | Medium | High | Low | **P1** |
| 7 | Curriculum scheduling (MAB) | Medium | High | Low | **P1** |
| 8 | Trace diff regression detection | Medium | Medium | Low | **P1** |
| 9 | Dynamic rubric evolution | High | Medium | Medium | **P2** |

**Quick wins (< 1 week):** Items 2, 4, 5, 10
**Strategic investments (1-3 weeks):** Items 1, 3, 6, 7, 8
**Research-grade (> 3 weeks):** Item 9

---

## HOOK SYSTEM IMPROVEMENTS TO LEVERAGE

New Claude Code hooks directly applicable to evaluation:

| Hook | Use Case | Priority |
|------|----------|----------|
| `TeammateIdle` (v2.1.33) | Quality gate: inject follow-up questions | HIGH |
| `TaskCompleted` (v2.1.33) | Quality gate: validate output before accepting | HIGH |
| `SubagentStart` (v2.1.43) | Observe agent spawning patterns | MEDIUM |
| `last_assistant_message` in Stop (v2.1.50) | Capture final output without transcript parsing | HIGH |
| `WorktreeCreate/Remove` (v2.1.50) | Set up/tear down evaluation environments | HIGH |
| Agent hooks (`type: "agent"`) | Spawn verification subagents with tools | HIGH |
| HTTP hooks (v2.1.63) | POST evaluation data to external services | LOW |

---

## TOOLS & FRAMEWORKS TO EVALUATE

| Tool | Purpose | Relevance |
|------|---------|-----------|
| **Promptfoo** (`anthropic:claude-agent-sdk` provider) | Evaluation pipeline with agent SDK | Direct integration |
| **Relari Agent Contracts** | YAML contract testing, offline+runtime | High — standardizes our contracts |
| **LangWatch Scenario** | Agent-tests-agent with judge pattern | High — closest to our approach |
| **agent-replay** | Trace diff/fork/replay | Medium — regression detection |
| **DeepEval** | Trajectory metrics (Plan Quality, Step Efficiency) | Medium — enriches scoring |
| **DSPy 3.0** | Automated prompt optimization | Medium — for prompt improvement loop |
| **promptolution** | Meta-framework for comparing optimizers | Medium — for comparing strategies |
| **Inspect Scout** (UK AISI) | Transcript scanning for cheating detection | Medium — anti-fabrication |

---

## KEY RESEARCH GAPS (Opportunities)

1. **No security-domain LLM-as-Judge work** — All evaluation papers focus on general NLP. We'd be first to publish security reasoning evaluation.
2. **No graph-grounded evaluation** — No framework evaluates whether reasoning is genuinely grounded in structured knowledge.
3. **No long-horizon agent evaluation** — Most trajectory work covers 5-20 steps; our agents run 100+.
4. **No adversarial evaluation-of-evaluation** — Limited work on agents gaming evaluation criteria.

---

## Detailed Findings by Research Agent

Individual research documents with full citations:

1. `findings_claude_code_features.md` — 807 lines, 30+ features catalogued
2. `findings_eval_frameworks.md` — 623 lines, 25+ papers, 8+ frameworks
3. `findings_self_improvement.md` — 702 lines, 38 indexed papers/resources
4. `findings_workflow_testing.md` — 743 lines, 11 papers, 10 tools, 3 government sources

Total research corpus: ~2,875 lines across 70+ sources.
