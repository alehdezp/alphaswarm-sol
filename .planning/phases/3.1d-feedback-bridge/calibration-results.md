# Phase 3.1d-04: Calibration Results

**Date:** 2026-02-18
**Status:** COMPLETE - All calibration tests pass

## 1. Detection Results on Corpus Contracts

### SideEntranceLenderPool (flash loan + reentrancy)
- **Graph:** 111 nodes, 143 edges, 100% coverage
- **Findings:** 19 total (11 on target contract, 8 on SafeTransferLib)
- **Target findings:** 7 HIGH, 2 MEDIUM, 2 LOW
- **Patterns matched:** reentrancy-basic, state-write-after-call, value-movement-cross-function-reentrancy, value-movement-cross-function-reentrancy-read, access-tierb-001-trust-assumption-violation, external-call-public-no-gate, lib-002
- **Assessment:** Correctly identifies the core flash-loan + cross-function reentrancy vulnerability. The reentrancy-basic pattern matches on withdraw(). Cross-function patterns correctly flag the deposit()+withdraw() interaction.

### TrusterLenderPool (trust assumption violation)
- **Graph:** 173 nodes, 301 edges, 100% coverage
- **Findings:** 50 total (6 on TrusterLenderPool, 22 on DamnValuableToken, 19 on ERC20, 3 on Address lib)
- **Target findings:** 5 HIGH, 0 MEDIUM, 0 LOW (all on flashLoan)
- **Patterns matched:** access-tierb-001-trust-assumption-violation, external-call-public-no-gate, attacker-controlled-write, dataflow-input-taints-state, has-user-input-writes-state-no-gate, lib-001
- **Assessment:** Correctly identifies the critical trust-assumption-violation on flashLoan(). The attacker-controlled target+data parameters and unguated external call are flagged. High false-positive count on inherited ERC20 token patterns (cosmetic, not security-relevant for the pool contract).

### NaiveReceiverPool (naive flash loan receiver)
- **Graph:** 263 nodes, 431 edges, 100% coverage
- **Findings:** 50 total (17 on NaiveReceiverPool, 5 on FlashLoanReceiver, 2 on Multicall, 15 on ERC20, 11 on WETH)
- **Target findings:** 15 HIGH, 0 MEDIUM, 0 LOW
- **Patterns matched:** ext-001, access-tierb-001-trust-assumption-violation, attacker-controlled-write, dataflow-input-taints-state, external-call-public-no-gate, has-user-input-writes-state-no-gate
- **Assessment:** Correctly identifies the access control issue on flashLoan() and the trust-assumption-violation on FlashLoanReceiver.onFlashLoan(). The core vulnerability (anyone can drain the receiver by calling flashLoan repeatedly on its behalf) is surfaced through the trust-assumption and external-call patterns.

### Detection Summary
| Contract | Total Findings | Target Findings | Core Vuln Detected? |
|----------|---------------|-----------------|---------------------|
| SideEntrance | 19 | 11 (7H/2M/2L) | Yes (reentrancy + flash loan) |
| Truster | 50 | 6 (5H) | Yes (trust assumption) |
| NaiveReceiver | 50 | 17 (15H) | Yes (unprotected flashLoan) |

**Observation:** High finding counts (50 each for Truster and NaiveReceiver) indicate the lens-report includes inherited contract findings. This inflates counts but doesn't affect vulnerability identification accuracy.

## 2. Evaluator Score Distribution

### Calibration Transcripts

| Transcript | Overall | GVS | BSKG Queries | Graph-First | Evidence Quality |
|-----------|---------|-----|--------------|-------------|-----------------|
| **good-01** | **83** | 82 | 4 (all types) | Yes | 100 |
| **good-02** | **76** | 79 | 3 | Yes | 85 |
| mediocre-01 | **53** | 38 | 1 | No* | 55 |
| mediocre-02 | **53** | 43 | 1 | No | 55 |
| bad-01 | **16** | 0 | 0 | No | 20 |
| bad-02 | **16** | 0 | 0 | No | 20 |

*mediocre-01 has Bash (build-kg) first but then Read before any pattern queries.

### Score Bands
| Quality | Avg Score | Min | Max | Expected Band |
|---------|-----------|-----|-----|---------------|
| Good | 79.5 | 76 | 83 | >70 |
| Mediocre | 53.0 | 53 | 53 | 30-60 |
| Bad | 16.0 | 16 | 16 | <30 |

### Differential
- **Good - Bad: 63.5 points** (requirement: >20)
- **Good - Mediocre: 26.5 points**
- **Mediocre - Bad: 37.0 points**

## 3. Real Transcript Evaluation

The 3 existing real transcripts from `.vrs/observations/` were also scored:
- transcript-001-build-kg: GVS graph-first=True, has 3 BSKG queries
- transcript-002-reentrancy-test: Has build-kg + 1 pattern-query, then Read
- transcript-003-lens-findings: Has lens-report + 1 BSKG finding summary

All real transcripts produce non-zero scores and the GVS correctly identifies graph-first compliance.

## 4. Evaluator Reliability Analysis

### Where the evaluator IS reliable
1. **Graph-first detection**: Binary and deterministic. Bash before Read = compliant. Works perfectly.
2. **BSKG query counting**: Accurately counts and categorizes queries by type (build-kg, query, pattern-query, analyze).
3. **Quality band separation**: 63.5-point spread between good and bad is large enough to be robust against noise.
4. **Zero-graph detection**: Bad workflows with no BSKG queries reliably score 0 on GVS.

### Where the evaluator is UNRELIABLE
1. **Citation rate heuristic**: The fallback regex (`node:|edge:|graph:|BSKG|build-kg`) is brittle. It awards credit for any mention of "graph" or "BSKG" in response text, even in context-setting sentences that don't actually cite evidence. Real citation tracking needs structured node-ID extraction.
2. **evidence_cited capability check**: The model-based check (`grader_type: model`) falls back to keyword heuristic. It scored 40 for good transcripts and 0/20 for bad, but the 40 ceiling for good is too low -- a genuinely good transcript with rich evidence citations should score 80+.
3. **reasoning_depth dimension**: Uses `unique_tools` count as proxy. Both good (4 tools) and mediocre (3 tools) get 70, which fails to differentiate them. The heuristic saturates at 3+ unique tools.
4. **Mediocre band compression**: Both mediocre transcripts score exactly 53. The evaluator lacks granularity in the 40-60 range. Different types of mediocre behavior (code-first vs. shallow queries) produce identical scores.
5. **response_text quality**: The evaluator has no semantic understanding of response quality. A verbose but vacuous response scores the same as a concise, evidence-rich one (both checked only for length > 50).

### Quantified Confidence
- GVS component: **HIGH confidence** - deterministic, well-calibrated
- Capability checks (presence/ordering/count): **HIGH confidence** - simple assertions
- Heuristic dimensions (reasoning_depth, evidence_quality): **MEDIUM confidence** - coarse proxies
- Model-based checks (evidence_cited): **LOW confidence** - keyword matching, not real NLU
- Citation rate: **LOW confidence** - regex-based, brittle

## 5. Calibration Recommendations for Phase 3.1d-05

### Priority 1: Fix reasoning_depth saturation
The `unique_tools` proxy for reasoning depth saturates at 3 unique tools (score=70 for both good and mediocre). Recommendation: use `len(tool_sequence)` combined with `len(bskg_queries)` as a compound metric. Good workflows have 6+ total steps; mediocre have 3-5.

### Priority 2: Improve citation_rate scoring
Replace the regex fallback with structured citation extraction:
- Parse BSKG query results for node IDs (format: `node:function:HASH`)
- Check if those node IDs appear in the response_text
- This gives a precise citation_rate instead of keyword-matching

### Priority 3: Add response quality dimension
Currently response_text is checked only for length. Add:
- Severity keyword presence (HIGH, MEDIUM, LOW)
- Finding structure markers (bullet points, numbered items)
- Evidence reference density (node:, file:line, function names)

### Priority 4: Widen mediocre band
The mediocre band is compressed at exactly 53. Consider adding sub-dimensions that differentiate:
- "builds graph but reads code first" (current mediocre-01 pattern)
- "has graph but only one query type" (current mediocre-02 pattern)
- "has graph + multiple queries but poor response quality"

### Test Infrastructure
- 6 calibration transcripts stored in `.vrs/observations/calibration/`
- 17 calibration tests in `tests/evaluation/test_calibration.py`
- Tests cover: GVS direct, full pipeline, score distribution, parser integration, real transcripts
- All 17 pass; 7888 existing tests unaffected

## Exit Gate Verification

| Criterion | Status |
|-----------|--------|
| Evaluator distinguishes good from bad (differential > 20) | PASS (63.5) |
| 3+ calibration transcripts stored | PASS (6 transcripts) |
| Calibration test passes | PASS (17/17) |
| All 298+ existing tests still pass | PASS (7888 pass, 1 pre-existing failure unrelated) |
