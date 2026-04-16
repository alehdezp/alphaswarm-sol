# W2-5: Benchmark Execution Plan

## Executive Summary

**Current state:** AlphaSwarm has ZERO measured benchmark results. The "84.6% DVDeFi detection rate" in `benchmarks/dvdefi/suite.yaml` is a hand-written YAML annotation — not a measured result from running the actual pipeline. The DVDeFi ground truth file (`dvdefi-v3.yaml`) contains 53 contracts all with `pattern: TODO`. The SmartBugs suite (40 challenges) has YAML definitions but no execution harness. There is no benchmark CI pipeline.

**What exists (YAML scaffolding, not results):**
- `benchmarks/dvdefi/` — 13 challenge YAMLs with manually-set `status: detected`
- `benchmarks/smartbugs/` — 40 challenge YAMLs across 9 categories
- `benchmarks/safe-set/` — 18 known-safe contract YAMLs for FP measurement
- `configs/ground_truth_manifest.yaml` — 5 external sources declared, hash manifest "pending_calculation"
- `.planning/testing/execution-sequences/IMP-G1-ablation.yaml` — Ablation study design (never executed)

**What does NOT exist:**
- A benchmark runner script (nothing reads the YAMLs and runs `alphaswarm build-kg` + `query`)
- Any measured precision/recall/F1 numbers
- Any comparison with Slither/Mythril/Aderyn
- Any CI pipeline for automated benchmarking
- Completed ground truth for DVDeFi (all TODO)
- Downloaded SmartBugs Curated contracts (only internal 40-challenge variants)

---

## Available Datasets

| Dataset | Contracts | Ground Truth | Access Method | Relevance |
|---------|-----------|-------------|---------------|-----------|
| **SmartBugs Curated** | 143 contracts, 208 tagged vulns | Line-level annotations, DASP taxonomy | `git clone github.com/smartbugs/smartbugs-curated` | HIGH — Academic benchmark, published tool comparisons |
| **SmartBugs Wild** | 47,398 contracts | Tool consensus only (no manual) | `git clone github.com/smartbugs/smartbugs-wild` | LOW — No reliable ground truth |
| **Damn Vulnerable DeFi v4** | 18 challenges (~53 contracts) | Challenge solutions = ground truth | Already in `examples/damm-vuln-defi/` | HIGH — DeFi-specific, complex vulns |
| **ScaBench** | 31 projects, 555 vulns (114 H/C) | Code4rena/Cantina/Sherlock judged findings | `git clone github.com/scabench-org/scabench` | HIGH — Real-world, recent (2024-2025) |
| **SCONE-bench** | 405 contracts | Exploit reproducibility (value extracted) | `git clone github.com/safety-research/SCONE-bench` | MEDIUM — Exploit-focused, not detection |
| **CGT (Consolidated Ground Truth)** | 50 contracts, 207 findings | Consolidated from 5 datasets | `git clone github.com/gsalzer/cgt` | HIGH — Cross-validated ground truth |
| **Ethernaut** | 30 challenges | Challenge solutions | OpenZeppelin GitHub | MEDIUM — Educational, simpler |
| **Code4rena Reports** | 6,454 contracts / 102 projects | Judge-confirmed H/M findings | `github.com/zhongeric/code4rena-reports` | HIGH — Real audit findings |
| **TrustLLM Dataset** | 1,734 pos + 1,810 neg samples | Code4rena provenance | HuggingFace (darkknight25) | MEDIUM — Classification only |
| **Messi-Q Smart Contract Dataset** | ~10K+ contracts | Multiple labeling schemes | `github.com/Messi-Q/Smart-Contract-Dataset` | MEDIUM — Academic use |

**Recommended priority:** SmartBugs Curated > DVDeFi v4 > ScaBench > CGT

---

## Benchmark 1: SmartBugs Curated Evaluation

### Why This Benchmark
The SmartBugs Curated dataset is the de facto academic standard. Published results exist for Slither (93.5% recall on reentrancy), Mythril, Oyente, and 16 other tools via SmartBugs 2.0 framework. This enables direct head-to-head comparison with published numbers.

### Dataset Setup

```bash
# 1. Clone SmartBugs Curated
git clone https://github.com/smartbugs/smartbugs-curated.git \
  benchmarks/external/smartbugs-curated/

# 2. Verify structure
# dataset/
#   ├── reentrancy/          (31 contracts)
#   ├── access_control/      (18 contracts)
#   ├── arithmetic/          (15 contracts)
#   ├── unchecked_low_level_calls/ (52 contracts)
#   ├── denial_of_service/   (6 contracts)
#   ├── bad_randomness/      (8 contracts)
#   ├── front_running/       (4 contracts)
#   ├── time_manipulation/   (5 contracts)
#   ├── short_addresses/     (1 contract)
#   └── other/               (3 contracts)

# 3. Parse ground truth from annotations
python scripts/bench/parse_smartbugs_ground_truth.py \
  --input benchmarks/external/smartbugs-curated/dataset/ \
  --output benchmarks/external/smartbugs-curated/ground-truth.json
```

**Ground truth format:** Each contract has `@vulnerable_at_lines` header annotation plus inline `// <yes> <report> [CATEGORY]` markers. Need a parser to extract line-level ground truth.

### Execution Pipeline

```bash
# For each contract in dataset:
for category in reentrancy access_control arithmetic ...; do
  for contract in benchmarks/external/smartbugs-curated/dataset/$category/*.sol; do
    # Step 1: Build knowledge graph
    uv run alphaswarm build-kg "$contract" \
      --output ".vrs/bench/smartbugs/$category/$(basename $contract .sol)/kg.json" \
      2>&1 | tee ".vrs/bench/smartbugs/$category/$(basename $contract .sol)/build.log"

    # Step 2: Run pattern queries
    uv run alphaswarm query "pattern:*" \
      --kg ".vrs/bench/smartbugs/$category/$(basename $contract .sol)/kg.json" \
      --output ".vrs/bench/smartbugs/$category/$(basename $contract .sol)/findings.json"

    # Step 3: Run external tools for comparison
    uv run alphaswarm tools run "$contract" --tools slither,aderyn \
      --output ".vrs/bench/smartbugs/$category/$(basename $contract .sol)/tools.json"
  done
done
```

**Critical note:** Many SmartBugs contracts use Solidity 0.4.x-0.6.x. AlphaSwarm's Slither integration MUST handle old pragma versions. This is a known compatibility challenge — need to test which contracts actually compile.

### Metrics Collection

```python
# Per-category and overall metrics:
metrics = {
    "true_positives": 0,    # Found and it's in ground truth
    "false_positives": 0,   # Found but not in ground truth
    "false_negatives": 0,   # In ground truth but not found
    "true_negatives": 0,    # Not found and not in ground truth (safe contracts)
}

precision = TP / (TP + FP)
recall = TP / (TP + FN)
f1 = 2 * (precision * recall) / (precision + recall)

# Category-level breakdown:
# reentrancy:     P=?, R=?, F1=?
# access_control: P=?, R=?, F1=?
# arithmetic:     P=?, R=?, F1=?
# ... etc
```

**Matching criteria:** A detection is a true positive if:
1. It identifies the correct vulnerability category, AND
2. It identifies the correct contract, AND
3. It identifies a function/line within ±5 lines of the annotated vulnerable line

### Expected Baselines (Published Results for Comparison)

| Tool | Reentrancy Recall | Overall Detection | Source |
|------|-------------------|-------------------|--------|
| Slither | 93.5% | 37% (w/Mythril) | SmartBugs ICSE 2020, Unity is Strength 2024 |
| Mythril | ~65% | 27% (standalone) | SmartBugs ICSE 2020 |
| Oyente | ~40% | ~15% | SmartBugs ICSE 2020 |
| Slither+Mythril combined | ~95% | 37% | Unity is Strength 2024 |
| 6-tool ensemble | N/A | 83.6% precision | Unity is Strength 2024 |
| LLM-based (GPT-4 class) | ~48% recall | ~48% avg | arXiv:2505.15756 (2025) |
| **AlphaSwarm (target)** | **>= 70%** | **>= 50%** | **Must be measured** |

**Honest assessment:** AlphaSwarm should aim to beat LLM-only approaches (~48%) and approach Slither on categories it covers. On reentrancy specifically, Slither's 93.5% is very hard to beat with graph-based analysis alone.

---

## Benchmark 2: DVDeFi End-to-End

### Why This Benchmark
DVDeFi is already in the repo (`examples/damm-vuln-defi/`) with all 18 v4 challenges. The current "84.6% detection rate" is aspirational. We need to actually run the pipeline and measure.

### Ground Truth (Must Be Created)

The existing `dvdefi-v3.yaml` has `pattern: TODO` for all 53 contracts. The benchmark YAMLs (e.g., `side-entrance.yaml`) have manually-set `status: detected` but no evidence of execution.

**Required ground truth per challenge:**

| # | Challenge | Vulnerability Type | Key Contract(s) | Expected Detection Pattern |
|---|-----------|-------------------|------------------|---------------------------|
| 1 | Unstoppable | DoS via balance manipulation | UnstoppableVault | `exact-balance-check`, `dos-balance-dependency` |
| 2 | Naive Receiver | Fee drain via repeated flash loans | NaiveReceiverPool | `flash-loan-fee-drain`, `missing-sender-check` |
| 3 | Truster | Arbitrary call in flash loan | TrusterLenderPool | `arbitrary-external-call`, `uncontrolled-delegatecall` |
| 4 | Side Entrance | Callback reentrancy | SideEntranceLenderPool | `reentrancy-callback`, `flash-loan-deposit-trick` |
| 5 | The Rewarder | Merkle proof claim manipulation | TheRewarderDistributor | `merkle-claim-manipulation`, `multi-claim` |
| 6 | Selfie | Flash loan governance attack | SelfiePool, SimpleGovernance | `governance-flash-loan`, `vote-weight-manipulation` |
| 7 | Compromised | Off-chain oracle key leak | Exchange, TrustfulOracle | `centralized-oracle-trust` (off-chain) |
| 8 | Puppet | DEX oracle manipulation | PuppetPool | `dex-oracle-manipulation`, `spot-price-dependency` |
| 9 | Puppet V2 | UniV2 oracle manipulation | PuppetV2Pool | `dex-oracle-manipulation`, `twap-bypass` |
| 10 | Free Rider | msg.value reuse in loop | FreeRiderNFTMarketplace | `msg-value-loop-reuse`, `payment-to-buyer` |
| 11 | Backdoor | Gnosis Safe module injection | WalletRegistry | `callback-injection`, `delegatecall-setup` |
| 12 | Climber | Timelock execute-before-schedule | ClimberTimelock | `execute-before-validate`, `role-escalation` |
| 13 | Wallet Mining | CREATE2 address prediction | WalletDeployer | `deterministic-address`, `proxy-init-bypass` |
| 14 | Puppet V3 | UniV3 TWAP manipulation | PuppetV3Pool | `twap-oracle-manipulation` |
| 15 | ABI Smuggling | ABI encoding bypass | AuthorizedExecutor | `abi-encoding-bypass`, `calldata-manipulation` |
| 16 | Shards | Fractional NFT rounding | ShardsNFTMarketplace | `rounding-error`, `fractional-share-drain` |
| 17 | Curvy Puppet | Curve oracle + liquidation | CurvyPuppetLending | `curve-oracle-manipulation`, `flash-liquidation` |
| 18 | Withdrawal | Bridge withdrawal replay | L1Gateway, TokenBridge | `message-replay`, `bridge-withdrawal-bypass` |

### Execution Pipeline

```bash
# Step 1: Build KG for each challenge
for challenge in unstoppable naive-receiver truster side-entrance ...; do
  uv run alphaswarm build-kg \
    "examples/damm-vuln-defi/src/$challenge/" \
    --output ".vrs/bench/dvdefi/$challenge/kg.json" \
    --with-labels \
    2>&1 | tee ".vrs/bench/dvdefi/$challenge/build.log"
done

# Step 2: Run all pattern queries
for challenge in unstoppable naive-receiver truster side-entrance ...; do
  uv run alphaswarm query "pattern:*" \
    --kg ".vrs/bench/dvdefi/$challenge/kg.json" \
    --output ".vrs/bench/dvdefi/$challenge/findings.json"
done

# Step 3: Compare findings to ground truth
python scripts/bench/score_dvdefi.py \
  --findings ".vrs/bench/dvdefi/*/findings.json" \
  --ground-truth benchmarks/dvdefi/ground-truth.json \
  --output ".vrs/bench/dvdefi/results.json"
```

### Metrics Collection

```
Per-challenge:
  Challenge: side-entrance
  Expected: [reentrancy-callback, flash-loan-deposit-trick]
  Found: [reentrancy-callback]
  TP: 1, FP: 0, FN: 1

Overall:
  Total expected detections: ~30 (across 18 challenges)
  Total found: ?
  Precision: ?
  Recall: ?
  F1: ?

By difficulty tier:
  Basic (1-2):    ?/?
  Intermediate (3): ?/?
  Advanced (4-5): ?/?
  Expert (6):     ?/?
```

### Expected Honest Results

Based on the current state of the codebase (patterns exist as YAML, but many have never been tested against real contracts):

| Tier | Challenges | Expected Detection | Reasoning |
|------|-----------|-------------------|-----------|
| Basic (1-2) | Unstoppable, Naive Receiver, Truster, Side Entrance | 3-4 / 4 | Simple patterns, likely covered |
| Intermediate (3) | Rewarder, Selfie, Puppet | 1-2 / 3 | Flash loan + governance complex |
| Advanced (4-5) | Puppet V2, V3, Free Rider, Backdoor | 1-2 / 4 | Oracle + callback injection complex |
| Expert (6) | Climber, Wallet Mining, ABI Smuggling, Shards, Curvy Puppet, Withdrawal | 0-1 / 6 | Very complex, likely beyond current patterns |

**Realistic expectation: 5-9 out of 18 challenges (28-50%), not 84.6%.**

---

## Benchmark 3: Head-to-Head Comparison

### Why This Benchmark
Users need to know: "Is AlphaSwarm better than just running Slither?" If the answer is no, the entire project has no value. This benchmark answers that question directly.

### Design

**Test set:** 50 contracts from mixed sources:
- 20 from SmartBugs Curated (diverse vulnerability types)
- 13 DVDeFi challenges
- 10 from Code4rena 2024 contests
- 7 from safe-set (for FP comparison)

**Three runs per contract:**

```bash
# Run 1: Slither alone
slither "$contract" --json ".vrs/bench/h2h/$name/slither.json" 2>/dev/null

# Run 2: AlphaSwarm alone (build-kg → query)
uv run alphaswarm build-kg "$contract" --output ".vrs/bench/h2h/$name/kg.json"
uv run alphaswarm query "pattern:*" \
  --kg ".vrs/bench/h2h/$name/kg.json" \
  --output ".vrs/bench/h2h/$name/alphaswarm.json"

# Run 3: AlphaSwarm with tools integration (includes Slither data)
uv run alphaswarm tools run "$contract" --tools slither,aderyn \
  --output ".vrs/bench/h2h/$name/tools.json"
uv run alphaswarm build-kg "$contract" \
  --tool-results ".vrs/bench/h2h/$name/tools.json" \
  --output ".vrs/bench/h2h/$name/kg-enhanced.json"
uv run alphaswarm query "pattern:*" \
  --kg ".vrs/bench/h2h/$name/kg-enhanced.json" \
  --output ".vrs/bench/h2h/$name/alphaswarm-enhanced.json"
```

### Metrics: Venn Diagram Analysis

```
                    Slither Only    Both Found    AlphaSwarm Only
Ground Truth:       |  A findings  | B findings  |  C findings  |
                    |              |             |              |
Not in GT:          |  D (Slither  | E (both FP) |  F (AS FP)   |
                    |   FP only)   |             |              |

Key metrics:
- A: "Slither finds, AlphaSwarm misses" — competitiveness gap
- C: "AlphaSwarm finds, Slither misses" — value-add proof
- B: "Both find" — overlap / commodity detection
- D vs F: FP comparison — who is noisier?

Value proposition = C / (A + B + C) = "unique detection contribution"
```

### Report Format

```markdown
## Head-to-Head Results: AlphaSwarm vs Slither

| Metric | Slither | AlphaSwarm | AlphaSwarm+Tools |
|--------|---------|------------|------------------|
| True Positives | ? | ? | ? |
| False Positives | ? | ? | ? |
| Precision | ? | ? | ? |
| Recall | ? | ? | ? |
| F1 | ? | ? | ? |
| Unique Finds | ? | ? | ? |
| Time (avg) | ? | ? | ? |

### What AlphaSwarm Found That Slither Missed
[List with evidence]

### What Slither Found That AlphaSwarm Missed
[List with evidence]

### Overlap Analysis
[Venn diagram data]
```

---

## Benchmark 4: BSKG Ablation Study

### Why This Benchmark
The BSKG (Behavioral Semantic Knowledge Graph) is AlphaSwarm's core value proposition. If the graph doesn't improve detection over raw LLM analysis, the entire architecture is wrong. This ablation study proves (or disproves) the graph's value.

### Design

**Three conditions:**
1. **Control (No Graph):** LLM reads Solidity source directly, no BSKG
2. **Graph Only:** BSKG built, pattern queries only, no LLM reasoning
3. **Graph + LLM:** BSKG built, pattern queries, LLM-enhanced reasoning (Tier B/C detection)

**Test set:** 15 contracts with known ground truth:
- 5 from DVDeFi (Side Entrance, Truster, Puppet, Selfie, Free Rider)
- 5 from SmartBugs Curated (reentrancy, access control mix)
- 5 from safe-set (for FP measurement)

### Execution Pipeline

```bash
# Condition 1: No Graph (LLM only)
# Use Claude to analyze raw Solidity — prompt-only, no tools
# This tests: "Does the graph actually help?"

# Condition 2: Graph Only (deterministic)
for contract in $TEST_SET; do
  uv run alphaswarm build-kg "$contract" --output "$OUT/graph-only/kg.json"
  uv run alphaswarm query "pattern:*" --kg "$OUT/graph-only/kg.json" \
    --output "$OUT/graph-only/findings.json"
done

# Condition 3: Graph + LLM (full pipeline)
for contract in $TEST_SET; do
  uv run alphaswarm build-kg "$contract" --with-labels --output "$OUT/full/kg.json"
  uv run alphaswarm query "pattern:*" --kg "$OUT/full/kg.json" \
    --output "$OUT/full/pattern-findings.json"
  # + LLM-enhanced analysis via agent spawning
done
```

### Metrics

| Metric | No Graph (LLM) | Graph Only | Graph + LLM |
|--------|----------------|------------|-------------|
| Precision | ? | ? | ? |
| Recall | ? | ? | ? |
| F1 | ? | ? | ? |
| False Positive Rate | ? | ? | ? |
| Avg Findings per Contract | ? | ? | ? |
| Evidence Quality (0-5) | ? | ? | ? |
| Avg Processing Time | ? | ? | ? |

**Success criteria for graph value:**
- Graph Only should beat No Graph on precision (fewer hallucinated findings)
- Graph + LLM should beat Graph Only on recall (LLM catches nuance)
- Graph + LLM should beat No Graph on both precision AND recall

**If Graph Only ≈ No Graph:** The graph is not adding value. Fundamental architecture problem.
**If Graph + LLM < No Graph:** The graph is actively harmful. Critical failure.

### Existing Ablation Design

The file `.planning/testing/execution-sequences/IMP-G1-ablation.yaml` already has a claude-code-agent-teams-based execution plan. However:
- It was never executed
- It relies on `--no-graph` flag that may not be implemented
- It uses 3 target contracts (need 15 for statistical significance)
- Its comparison script (`scripts/compare_ablation_runs.py`) doesn't exist

---

## Benchmark 5: ScaBench Real-World Evaluation (Bonus — High Value)

### Why This Benchmark
ScaBench uses recent (2024-2025) Code4rena/Cantina/Sherlock vulnerabilities with the official Nethermind AuditAgent scoring algorithm. This is the closest thing to "how would AlphaSwarm perform on a real audit?"

### Dataset Setup

```bash
# Clone ScaBench
git clone https://github.com/scabench-org/scabench.git benchmarks/external/scabench/

# Download dataset
python benchmarks/external/scabench/dataset-generator/download_sources.py \
  --dataset benchmarks/external/scabench/datasets/curated-2025-08-18.json \
  --output benchmarks/external/scabench/sources/

# Install scorer
pip install "git+https://github.com/NethermindEth/auditagent-scoring-algo"
```

### Execution Pipeline

```bash
# For each project in ScaBench:
for project in $(jq -r '.[].project_id' curated-2025-08-18.json); do
  # Build KG for project
  uv run alphaswarm build-kg \
    "benchmarks/external/scabench/sources/$project/contracts/" \
    --output ".vrs/bench/scabench/$project/kg.json"

  # Run pattern analysis
  uv run alphaswarm query "pattern:*" \
    --kg ".vrs/bench/scabench/$project/kg.json" \
    --output ".vrs/bench/scabench/$project/findings.json"

  # Format to ScaBench expected output
  python scripts/bench/format_scabench_output.py \
    --findings ".vrs/bench/scabench/$project/findings.json" \
    --project "$project" \
    --output ".vrs/bench/scabench/$project/submission.json"

  # Score using AuditAgent algorithm
  scabench score \
    --findings ".vrs/bench/scabench/$project/submission.json" \
    --ground-truth curated-2025-08-18.json \
    --project "$project" \
    --output ".vrs/bench/scabench/$project/score.json"
done
```

### Metrics
ScaBench provides standardized metrics via the AuditAgent scoring algorithm:
- Detection rate per severity (High, Medium, Low)
- Precision / Recall per project
- Aggregate score across all 31 projects
- Comparison with baseline LLM runner

**This benchmark is especially valuable because ScaBench updates regularly, preventing overfitting.**

---

## CI Pipeline Design

### Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                     Benchmark CI Pipeline                            │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Trigger: nightly cron OR manual dispatch OR PR to patterns/         │
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
│  │ Quick Suite  │  │ Standard    │  │ Full Suite  │                  │
│  │ (~5 min)     │  │ (~30 min)   │  │ (~2 hr)     │                  │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤                  │
│  │ 5 DVDeFi    │  │ All DVDeFi  │  │ SmartBugs   │                  │
│  │ 5 SmartBugs │  │ All Smart-  │  │ DVDeFi      │                  │
│  │ 3 safe-set  │  │ bugs custom │  │ ScaBench    │                  │
│  │             │  │ safe-set    │  │ safe-set    │                  │
│  │             │  │             │  │ ablation    │                  │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                  │
│         │                │                │                          │
│         ▼                ▼                ▼                          │
│  ┌──────────────────────────────────────────┐                        │
│  │          Results Aggregator               │                        │
│  │  - Compute P/R/F1 per category            │                        │
│  │  - Compare to previous run                │                        │
│  │  - Flag regressions (> 5% drop)           │                        │
│  │  - Generate dashboard JSON                │                        │
│  └──────────────────────────────────────────┘                        │
│         │                                                            │
│         ▼                                                            │
│  ┌──────────────────────────────────────────┐                        │
│  │          Outputs                          │                        │
│  │  - .vrs/bench/latest/results.json         │                        │
│  │  - .vrs/bench/latest/dashboard.md         │                        │
│  │  - .vrs/bench/history/<date>/             │                        │
│  │  - GitHub Actions artifact (if CI)        │                        │
│  └──────────────────────────────────────────┘                        │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### Implementation

```yaml
# .github/workflows/benchmark.yml
name: Benchmark Suite
on:
  schedule:
    - cron: '0 3 * * *'  # Nightly at 3am UTC
  workflow_dispatch:
    inputs:
      suite:
        type: choice
        options: [quick, standard, full]
  push:
    paths: ['vulndocs/**', 'src/alphaswarm_sol/kg/**']

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync
      - run: uv run python scripts/bench/run_suite.py --suite ${{ inputs.suite || 'quick' }}
      - uses: actions/upload-artifact@v4
        with:
          name: benchmark-results-${{ github.run_number }}
          path: .vrs/bench/latest/
```

### Key Script: `scripts/bench/run_suite.py`

```python
"""
Benchmark runner.
Reads suite YAMLs, runs build-kg + query, scores against ground truth.
"""
# This script must:
# 1. Parse suite YAML (dvdefi/suite.yaml, smartbugs/suite.yaml)
# 2. For each contract: build KG, run queries
# 3. Match findings to ground truth
# 4. Compute metrics per-category and overall
# 5. Compare to baseline (previous run) and flag regressions
# 6. Output structured JSON + human-readable markdown
```

### Reproducibility Requirements

1. **Pinned dependencies:** `uv.lock` committed, exact solver versions
2. **Pinned dataset versions:** Git commit hashes in `ground_truth_manifest.yaml`
3. **Deterministic output:** Same contract → same KG → same findings (no LLM in Tier A)
4. **No internet required:** All datasets cached locally
5. **Time budget:** Quick suite < 5 min, Standard < 30 min, Full < 2 hr

### Regression Detection

```python
# Flag regression if:
# - Any category recall drops > 5% from previous run
# - Overall F1 drops > 3%
# - New false positives on safe-set contracts
# - Any previously-detected DVDeFi challenge becomes undetected
```

---

## Effort Estimate

| Benchmark | Effort | Dependencies | Priority |
|-----------|--------|-------------|----------|
| **DVDeFi Ground Truth** | 2-3 days | DVDeFi v4 contracts (already in repo) | P0 — easiest, most embarrassing gap |
| **Benchmark Runner Script** | 3-5 days | Working `build-kg` + `query` CLI | P0 — nothing works without this |
| **DVDeFi Execution** | 1-2 days | Runner script + ground truth | P0 — first real measured number |
| **SmartBugs Curated Setup** | 2-3 days | Clone + parse annotations + handle old Solidity | P1 — compatibility challenge with old pragma |
| **SmartBugs Execution** | 1-2 days | Runner + SmartBugs setup | P1 |
| **Head-to-Head Comparison** | 2-3 days | Working Slither integration | P1 — high marketing value |
| **BSKG Ablation Study** | 3-5 days | All three conditions implemented | P1 — architectural validation |
| **ScaBench Integration** | 3-5 days | Clone + format adapter + AuditAgent scorer | P2 — highest credibility |
| **CI Pipeline** | 2-3 days | At least one benchmark working | P2 |
| **Safe-Set FP Measurement** | 1-2 days | Runner + safe contracts | P1 |

**Total estimated effort: 20-33 days**

### Recommended Execution Order

1. **Week 1:** Benchmark runner script + DVDeFi ground truth + first DVDeFi run
2. **Week 2:** SmartBugs setup + execution + safe-set FP measurement
3. **Week 3:** Head-to-head comparison + BSKG ablation
4. **Week 4:** ScaBench integration + CI pipeline + dashboard

---

## Critical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Old Solidity versions** in SmartBugs (0.4.x-0.6.x) | KG builder may fail on legacy syntax | Test compilation first, exclude incompatible contracts, document coverage |
| **AlphaSwarm CLI commands may not work end-to-end** | Can't run benchmarks at all | Fix `build-kg` + `query` pipeline first (P0 bug fix) |
| **Results may be embarrassing** (< 30% detection) | Team morale, stakeholder trust | Report honestly. Bad numbers now → improvement roadmap. Hiding them is worse. |
| **Pattern YAML exists but matching logic broken** | Patterns "exist" but don't detect anything | Run sanity check on 3-5 known-vulnerable contracts first |
| **ScaBench scorer dependency breaks** | Can't compute standardized scores | Fall back to custom scorer; keep ScaBench as stretch goal |
| **Ground truth disagreements** | Different tools disagree on what's vulnerable | Use "confirmed by 2+ sources" threshold for contested findings |

---

## Anti-Fabrication Rules for Benchmarks

These rules MUST be enforced to prevent the "84.6% problem" (claiming results that were never measured):

1. **No YAML annotations without execution evidence.** Every `status: detected` MUST have a corresponding `findings.json` from an actual run.
2. **Results file must include:**
   - Timestamp of run
   - AlphaSwarm version / git commit
   - Exact command executed
   - Raw output (before scoring)
   - Machine-readable metrics
3. **History tracking:** Results stored in `.vrs/bench/history/<date>/` so regressions are detectable.
4. **Separate "claimed" vs "measured":** If a benchmark hasn't been run, it's "unmeasured", not "detected".
5. **CI enforcement:** The benchmark runner MUST fail if it encounters a `status: detected` without execution evidence.

---

## Sources

- [SmartBugs Curated Dataset](https://github.com/smartbugs/smartbugs-curated)
- [SmartBugs Framework](https://github.com/smartbugs/smartbugs)
- [SmartBugs Published Results (ICSE 2020)](https://github.com/smartbugs/smartbugs-results)
- [SmartBugs 2.0 Paper](https://arxiv.org/abs/2306.05057)
- [Unity is Strength: Reentrancy Tool Precision (2024)](https://arxiv.org/html/2402.09094)
- [Line-Level SmartBugs Evaluation (2025)](https://arxiv.org/html/2505.15756)
- [Damn Vulnerable DeFi v4](https://www.damnvulnerabledefi.xyz/)
- [DVDeFi v4 Solutions](https://github.com/RealJohnnyTime/damn-vulnerable-defi-v4-solutions)
- [ScaBench: Smart Contract Audit Benchmark](https://github.com/scabench-org/scabench)
- [SCONE-bench: Smart Contract Exploitation Benchmark](https://github.com/safety-research/SCONE-bench)
- [Anthropic Smart Contract Research (2025)](https://red.anthropic.com/2025/smart-contracts/)
- [CGT: Consolidated Ground Truth](https://github.com/gsalzer/cgt)
- [Code4rena Reports](https://github.com/zhongeric/code4rena-reports)
- [Smart Contract Dataset (Messi-Q)](https://github.com/Messi-Q/Smart-Contract-Dataset)
- [Smart Contract Vulnerability SLR (2024)](https://arxiv.org/abs/2412.01719)
- [ICSE 2026 Large-Scale LLM Framework](https://nzjohng.github.io/publications/papers/icse2026.pdf)
- [ASE 2025 Access Control Benchmark](https://conf.researchr.org/details/ase-2025/ase-2025-papers/77/)
- [Smart Contract Vulnerability Dataset (HuggingFace)](https://huggingface.co/datasets/darkknight25/Smart_Contract_Vulnerability_Dataset)
- [GRACE: Graph + LLM Vulnerability Detection](https://www.sciencedirect.com/science/article/abs/pii/S0164121224000748)
