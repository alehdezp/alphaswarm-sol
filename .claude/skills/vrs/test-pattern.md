---
name: vrs-test-pattern
description: |
  Pattern testing and validation skill. Runs patterns against real-world projects,
  measures precision and recall, validates matches against ground truth, and generates
  reports for refinement.

  Invoke when user wants to:
  - Test pattern accuracy: "test pattern X", "/vrs-test-pattern"
  - Validate before promotion: "/vrs-test-pattern reentrancy-classic"
  - Generate metrics: "measure precision and recall for pattern"

  This skill:
  1. Selects test corpus (DVDeFi, audits, benchmarks)
  2. Builds knowledge graphs via CLI
  3. Runs pattern queries
  4. Validates matches against ground truth
  5. Calculates precision/recall metrics
  6. Reports FP/FN for refinement

slash_command: vrs:test-pattern
context: fork

tools:
  - Read
  - Write
  - Glob
  - Grep
  - Bash(uv run alphaswarm*)

model_tier: sonnet

---

# VRS Test Pattern Skill - Pattern Validation and Metrics

You are the **VRS Test Pattern** skill, responsible for testing vulnerability patterns against real-world projects, measuring accuracy, and generating actionable feedback for refinement.

**CRITICAL: Invocation Model**
You are Claude Code, an agent that follows this skill documentation. When this skill says "build knowledge graph," you invoke the Bash tool with `uv run alphaswarm build-kg`. When it says "run pattern query," you invoke Bash with `uv run alphaswarm query`. This skill file IS the prompt that guides your behavior - you execute it using your standard tools.

## Purpose

- **Validate patterns** against real-world Solidity projects
- **Measure precision and recall** with ground truth validation
- **Generate test reports** for pattern refinement
- **Identify false positives and false negatives** with detailed analysis
- **Track test coverage** in vulndoc metadata
- **Support promotion** from draft to ready status

## How to Invoke

```bash
/vrs-test-pattern
/vrs-test-pattern "reentrancy-classic"
/vrs-test-pattern --pattern vulndocs/reentrancy/classic/patterns/vm-001-classic.yaml
/vrs-test-pattern --corpus damm-vuln-defi
```

**Interactive mode** (default):
- Prompts for pattern to test
- Suggests test corpus based on category
- Guides through validation

**Quick mode** (with args):
- Provide pattern and corpus upfront
- Faster for known test scenarios

---

## Execution Workflow

### Step 1: Select Test Corpus

**Goal:** Choose appropriate real-world projects for testing pattern.

**Available Corpora:**

1. **Damn Vulnerable DeFi (DVDeFi)**
   - Location: `examples/damm-vuln-defi/`
   - Focus: Common DeFi vulnerabilities
   - Ground truth: Documented challenges
   - Best for: reentrancy, flash loans, oracle, access-control

2. **Real-World Audit Reports**
   - Location: `.vrs/benchmarks/corpora/c4-*/`
   - Focus: Code4rena findings
   - Ground truth: Audit reports
   - Best for: All categories

3. **Benchmark Contracts**
   - Location: `tests/contracts/vulnerable/`, `tests/contracts/safe/`
   - Focus: Known TP/FP cases
   - Ground truth: Explicitly labeled
   - Best for: Regression testing

4. **User-Specified Projects**
   - Location: User-provided path
   - Focus: Custom validation
   - Ground truth: Manual verification required
   - Best for: Real-world testing

**Selection Logic:**

```python
def select_corpus(pattern_category):
    """Select appropriate test corpus based on pattern category"""

    corpus_map = {
        "reentrancy": ["damm-vuln-defi", "tests/contracts/vulnerable/reentrancy"],
        "oracle": [".vrs/benchmarks/corpora/c4-*", "tests/contracts/vulnerable/oracle"],
        "access-control": ["damm-vuln-defi", "tests/contracts/vulnerable/access"],
        "arithmetic": ["tests/contracts/vulnerable/arithmetic"],
        "defi": ["damm-vuln-defi", ".vrs/benchmarks/corpora/c4-*"],
    }

    return corpus_map.get(pattern_category, ["tests/contracts/vulnerable/"])
```

**User Prompt:**

```
Pattern: reentrancy-classic
Category: reentrancy

Suggested test corpora:
1. damm-vuln-defi (DeFi challenges)
2. tests/contracts/vulnerable/reentrancy (regression tests)
3. .vrs/benchmarks/corpora/c4-* (Code4rena audits)

Select corpus [1-3, or provide path]: 1
```

### Step 2: Build Knowledge Graphs

**Goal:** Generate BSKG graphs for test projects.

**Actions:**

1. **Check if graphs already exist** (via Bash tool):
   ```bash
   ls -la {corpus_path}/.vrs/graph*.json
   ```

2. **Build graphs if needed** (via Bash tool):
   ```bash
   uv run alphaswarm build-kg {corpus_path}
   ```

   **Example:**
   ```bash
   uv run alphaswarm build-kg examples/damm-vuln-defi/
   ```

3. **Verify graph creation** (via Bash tool):
   ```bash
   # Check graph files exist
   find {corpus_path} -name "graph*.json" -type f
   ```

4. **Handle build failures**:
   - If Slither fails: Log error, skip project
   - If contracts too complex: Note in report
   - If no vulnerabilities: Include as negative cases

**Expected Output:**

```
Building knowledge graphs...
✓ damm-vuln-defi/contracts/side-entrance/SideEntrance.sol
✓ damm-vuln-defi/contracts/naive-receiver/NaiveReceiver.sol
✓ damm-vuln-defi/contracts/unstoppable/Unstoppable.sol

Graphs created: 12 contracts
```

### Step 3: Run Pattern Query

**Goal:** Execute pattern against knowledge graphs.

**Actions:**

1. **Load pattern file** (via Read tool):
   ```bash
   cat vulndocs/{category}/{subcategory}/patterns/{pattern-id}.yaml
   ```

2. **Run pattern query** (via Bash tool):
   ```bash
   uv run alphaswarm query "pattern:{pattern-id}" --corpus {corpus_path} --json > /tmp/pattern-results.json
   ```

   **Alternative: Direct file reference**
   ```bash
   uv run alphaswarm query "pattern:vulndocs/{category}/{subcategory}/patterns/{pattern-id}.yaml" --json > /tmp/pattern-results.json
   ```

3. **Parse results** (via Read tool):
   ```bash
   cat /tmp/pattern-results.json
   ```

4. **Extract matches**:
   ```python
   # Parse JSON results
   results = json.load(open("/tmp/pattern-results.json"))

   matches = []
   for finding in results.get("findings", []):
       matches.append({
           "file": finding["file"],
           "function": finding["function"],
           "severity": finding["severity"],
           "evidence": finding["evidence"],
       })
   ```

**Example Results:**

```json
{
  "pattern_id": "reentrancy-classic",
  "findings": [
    {
      "file": "contracts/side-entrance/SideEntrance.sol",
      "function": "withdraw",
      "severity": "critical",
      "evidence": {
        "operations": ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        "sequence": "read → external_call → write"
      }
    },
    {
      "file": "contracts/safe/SafeVault.sol",
      "function": "safeWithdraw",
      "severity": "critical",
      "evidence": {
        "operations": ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        "sequence": "read → external_call → write"
      }
    }
  ]
}
```

### Step 4: Validate Matches Against Ground Truth

**Goal:** Determine which matches are TP, FP, or FN.

**Ground Truth Sources:**

1. **DVDeFi Challenges** - Documented vulnerabilities
2. **Tests with labeled contracts** - Explicit TP/FP markers
3. **Audit reports** - Known findings
4. **Manual verification** - For new projects

**Ground Truth Format:**

```yaml
# tests/ground_truth/reentrancy/classic.yaml
vulnerable_functions:
  - file: contracts/side-entrance/SideEntrance.sol
    function: withdraw
    vuln_type: reentrancy-classic
    reason: "Balance updated after ETH transfer"

  - file: contracts/naive-receiver/NaiveReceiver.sol
    function: flashLoan
    vuln_type: reentrancy-classic
    reason: "External call before state update"

safe_functions:
  - file: contracts/safe/SafeVault.sol
    function: safeWithdraw
    reason: "Uses ReentrancyGuard modifier"
    false_positive_if_matched: true

  - file: contracts/safe/ViewOnly.sol
    function: getBalance
    reason: "View function, no state modification"
    false_positive_if_matched: true
```

**Validation Logic:**

```python
def validate_matches(matches, ground_truth):
    """Compare matches against ground truth"""

    tp = []  # True Positives
    fp = []  # False Positives
    fn = []  # False Negatives

    # Check each match
    for match in matches:
        is_vulnerable = is_in_ground_truth(
            match, ground_truth["vulnerable_functions"]
        )

        if is_vulnerable:
            tp.append(match)
        else:
            # Check if explicitly marked as safe
            is_safe = is_in_ground_truth(
                match, ground_truth["safe_functions"]
            )
            if is_safe:
                fp.append(match)
            else:
                # Unknown - request manual verification
                manual_check = verify_manually(match)
                if manual_check == "vulnerable":
                    tp.append(match)
                else:
                    fp.append(match)

    # Find false negatives (ground truth not matched)
    for vuln in ground_truth["vulnerable_functions"]:
        matched = any(
            m["file"] == vuln["file"] and m["function"] == vuln["function"]
            for m in matches
        )
        if not matched:
            fn.append(vuln)

    return tp, fp, fn
```

**Manual Verification Prompt:**

When ground truth doesn't exist, ask user:

```
Match requires verification:
  File: contracts/UnknownVault.sol
  Function: withdraw

Pattern matched on:
  - TRANSFERS_VALUE_OUT at line 45
  - WRITES_USER_BALANCE at line 47
  - Sequence: read → external_call → write

Is this a TRUE vulnerability? [y/n/skip]: _
```

### Step 5: Calculate Metrics

**Goal:** Compute precision and recall from validation results.

**Formulas:**

```python
def calculate_metrics(tp, fp, fn):
    """Calculate precision, recall, F1 score"""

    precision = len(tp) / (len(tp) + len(fp)) if (len(tp) + len(fp)) > 0 else 0.0
    recall = len(tp) / (len(tp) + len(fn)) if (len(tp) + len(fn)) > 0 else 0.0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "precision": round(precision, 2),
        "recall": round(recall, 2),
        "f1_score": round(f1_score, 2),
        "tp": len(tp),
        "fp": len(fp),
        "fn": len(fn),
        "total_matches": len(tp) + len(fp),
        "total_vulnerable": len(tp) + len(fn),
    }
```

**Example Calculation:**

```yaml
validation_results:
  tp: 9   # Correctly identified vulnerabilities
  fp: 3   # Safe code incorrectly flagged
  fn: 1   # Vulnerability missed

metrics:
  precision: 0.75  # 9 / (9 + 3)
  recall: 0.90     # 9 / (9 + 1)
  f1_score: 0.82   # 2 * (0.75 * 0.90) / (0.75 + 0.90)
```

**Pattern Rating:**

```python
def rate_pattern(precision, recall):
    """Determine pattern status based on metrics"""

    if precision >= 0.90 and recall >= 0.85:
        return "excellent"
    elif precision >= 0.70 and recall >= 0.50:
        return "ready"
    else:
        return "draft"
```

### Step 6: Generate Test Report

**Goal:** Create detailed report for pattern improvement.

**Report Structure:**

```yaml
# .vrs/test-results/reentrancy-classic-20260122.yaml
pattern_id: reentrancy-classic
pattern_file: vulndocs/reentrancy/classic/patterns/vm-001-classic.yaml
vulndoc: reentrancy/classic
test_date: 2026-01-22T10:30:00Z

corpus:
  name: damm-vuln-defi
  path: examples/damm-vuln-defi/
  contracts_tested: 12
  graphs_built: 12

metrics:
  precision: 0.75
  recall: 0.90
  f1_score: 0.82
  tp: 9
  fp: 3
  fn: 1
  total_matches: 12
  total_vulnerable: 10

rating: ready  # excellent | ready | draft

true_positives:
  - file: contracts/side-entrance/SideEntrance.sol
    function: withdraw
    reason: "Balance updated after ETH transfer"

  - file: contracts/naive-receiver/NaiveReceiver.sol
    function: flashLoan
    reason: "External call before state update"

false_positives:
  - file: contracts/safe/SafeVault.sol
    function: safeWithdraw
    reason: "Has ReentrancyGuard modifier (pattern missed this)"
    suggested_fix: "Add has_reentrancy_guard exclusion to tier_a.none"

  - file: contracts/safe/ViewOnly.sol
    function: getBalance
    reason: "View function, no state modification possible"
    suggested_fix: "Add state_mutability: [view, pure] exclusion to tier_a.none"

false_negatives:
  - file: contracts/tricky/IndirectReentrancy.sol
    function: delegateWithdraw
    reason: "State write via delegatecall not detected"
    suggested_fix: "Broaden CALLS_EXTERNAL to include delegatecall"

recommendations:
  priority: high
  actions:
    - "Use /vrs-refine to add reentrancy guard exclusion (fixes 1 FP)"
    - "Add view/pure state mutability exclusion (fixes 1 FP)"
    - "Broaden external call detection for delegatecall (fixes 1 FN)"

  expected_improvement:
    precision: "0.75 → 0.90 (+0.15)"
    recall: "0.90 → 0.95 (+0.05)"

next_steps:
  - "Review FP/FN details"
  - "Run /vrs-refine with this report"
  - "Re-test after refinement"
  - "Update vulndoc test_coverage if rating changes"
```

**Terminal Output:**

```
Pattern Test Results: reentrancy-classic
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Corpus:     damm-vuln-defi (12 contracts)
Precision:  0.75 (9 TP, 3 FP)
Recall:     0.90 (9 TP, 1 FN)
F1 Score:   0.82
Rating:     ready

False Positives (3):
  1. SafeVault.safeWithdraw - Has reentrancy guard
  2. ViewOnly.getBalance - View function
  3. GuardedTransfer.send - Uses CEI pattern

False Negatives (1):
  1. IndirectReentrancy.delegateWithdraw - Delegatecall not tracked

Recommendations:
  → Use /vrs-refine to improve precision to 0.90
  → Expected improvement: +0.15 precision, +0.05 recall

Report saved: .vrs/test-results/reentrancy-classic-20260122.yaml
```

### Step 7: Update Vulndoc Test Coverage

**Goal:** Record test results in vulndoc metadata.

**Actions:**

1. **Load vulndoc index.yaml** (via Read tool):
   ```bash
   cat vulndocs/{category}/{subcategory}/index.yaml
   ```

2. **Update test_coverage section** (via Write tool):

```yaml
# Add new test entry to test_coverage array
test_coverage:
  - project: damm-vuln-defi
    date: 2026-01-22
    precision: 0.75
    recall: 0.90
    notes: "3 FPs (reentrancy guards), 1 FN (delegatecall)"

  - project: tests-regression
    date: 2026-01-15
    precision: 0.80
    recall: 0.85
    notes: "Initial test run"
```

3. **Update status if rating changed**:

```yaml
status: ready  # Update from draft if precision >= 0.70 and recall >= 0.50
```

4. **Validate updated vulndoc** (via Bash tool):
   ```bash
   uv run alphaswarm vulndocs validate vulndocs/{category}/{subcategory}
   ```

---

## Key Rules

### 1. Always Use BSKG Queries, Not Manual Code Reading

Pattern testing MUST use knowledge graph queries:

✅ **Correct:**
```bash
uv run alphaswarm query "pattern:reentrancy-classic"
```

❌ **Incorrect:**
```python
# Don't manually scan code
for file in glob("**/*.sol"):
    with open(file) as f:
        if "external call" in f.read():
            # Manual pattern matching
```

**Why:** Graph-based testing ensures consistency with production detection.

### 2. Record All Verification Decisions

Every manual verification must be documented:

```yaml
manual_verifications:
  - file: UnknownVault.sol
    function: withdraw
    decision: vulnerable
    reason: "External call before balance update"
    verified_by: user
    date: 2026-01-22
```

Enables reproducible testing and ground truth building.

### 3. Update test_coverage After Testing

Always update vulndoc with new test results:

```bash
# After test completes:
1. Read vulndoc index.yaml
2. Append new entry to test_coverage
3. Update status if rating changed
4. Validate vulndoc
```

Tracks pattern evolution over time.

### 4. Flag Patterns Below 0.70 Precision as Draft

Patterns with too many false positives need work:

```python
if precision < 0.70:
    rating = "draft"
    recommend_action = "Use /vrs-refine to improve precision"
```

Prevents low-quality patterns from being promoted.

### 5. Include Both Positive and Negative Cases

Test corpus should include:
- ✅ Vulnerable contracts (for recall testing)
- ✅ Safe contracts (for precision testing)
- ✅ Edge cases (complex patterns)
- ✅ False positive traps (guards, view functions)

Balanced testing reveals true pattern accuracy.

### 6. Suggest Specific Refinements

Don't just report failures - suggest fixes:

```yaml
false_positive:
  function: safeWithdraw
  issue: "Has reentrancy guard"
  suggested_fix: "Add has_reentrancy_guard = false to tier_a.none"
```

Makes refinement process actionable.

---

## Test Corpus Management

### DVDeFi Challenges

```bash
# Location
examples/damm-vuln-defi/

# Contracts (documented challenges)
contracts/
  side-entrance/     # Reentrancy via deposit
  naive-receiver/    # Flash loan reentrancy
  unstoppable/       # DOS via unexpected balance
  ...
```

**Ground Truth:** Built-in (each challenge has known vulnerability)

### Code4rena Audits

```bash
# Location
.vrs/benchmarks/corpora/c4-*/

# Structure
c4-2025-04-virtuals/
  audits/
    findings.md      # Contains vulnerability locations
  contracts/
    *.sol            # Audited code
```

**Ground Truth:** Parse findings.md for vulnerability locations

### Regression Tests

```bash
# Location
tests/contracts/

# Structure
vulnerable/
  reentrancy/
    classic-reentrancy.sol
    cross-function-reentrancy.sol
  oracle/
    stale-price.sol
safe/
  reentrancy/
    guarded-withdraw.sol
    cei-pattern.sol
```

**Ground Truth:** File organization indicates vulnerability status

---

## Example Invocation

```bash
# User invokes
/vrs-test-pattern "reentrancy-classic"

# You (Claude Code agent) prompt:
Select test corpus:
1. damm-vuln-defi
2. tests/contracts/vulnerable/reentrancy
3. .vrs/benchmarks/corpora/c4-*

User selects: 1

# You execute:
1. Bash: uv run alphaswarm build-kg examples/damm-vuln-defi/
2. Bash: uv run alphaswarm query "pattern:reentrancy-classic" --json > /tmp/results.json
3. Read: /tmp/results.json (parse matches)
4. Read: tests/ground_truth/reentrancy/classic.yaml (load ground truth)
5. Compare: Identify TP, FP, FN
6. Calculate: precision = 0.75, recall = 0.90
7. Generate: .vrs/test-results/reentrancy-classic-20260122.yaml
8. Write: Update vulndocs/reentrancy/classic/index.yaml test_coverage
9. Report: Show metrics and recommendations
```

---

## Tools Reference

**CLI Commands (via Bash tool):**

```bash
# Build knowledge graphs
uv run alphaswarm build-kg {corpus_path}

# Run pattern query
uv run alphaswarm query "pattern:{pattern-id}" --json
uv run alphaswarm query "pattern:{pattern-file-path}" --json

# List available patterns
uv run alphaswarm query "list-patterns"

# Validate vulndoc after update
uv run alphaswarm vulndocs validate vulndocs/{category}/{subcategory}
```

**File Operations:**

- **Read**: Load pattern YAML, ground truth, results
- **Write**: Update vulndoc test_coverage, save report
- **Glob**: Find test contracts (`examples/**/*.sol`)
- **Grep**: Search ground truth files

---

## Output Location

Save test report to:
```
.vrs/test-results/{pattern-id}-{timestamp}.yaml
```

Present summary to user in terminal.

Update vulndoc at:
```
vulndocs/{category}/{subcategory}/index.yaml
```

---

## Integration with /vrs-refine

Test reports feed directly into refinement:

```bash
# Test → Refine cycle
1. /vrs-test-pattern "reentrancy-classic"
   → Generates: .vrs/test-results/reentrancy-classic-20260122.yaml

2. /vrs-refine "reentrancy-classic" --test-results .vrs/test-results/reentrancy-classic-20260122.yaml
   → Applies suggested fixes

3. /vrs-test-pattern "reentrancy-classic"
   → Verify improvement
```

Iterative improvement loop until metrics meet quality bar.
