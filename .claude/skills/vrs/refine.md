---
name: vrs-refine
description: |
  Pattern refinement skill. Improves existing patterns based on test feedback,
  reducing false positives while maintaining recall. Updates pattern YAML and
  tracks precision/recall metrics.

  Invoke when user wants to:
  - Improve pattern accuracy: "refine pattern X", "/vrs-refine"
  - Reduce false positives: "/vrs-refine reentrancy-classic"
  - Adjust pattern after test failures: After /vrs-test-pattern reveals issues

  This skill:
  1. Loads target pattern and associated vulndoc
  2. Analyzes test failures (FP/FN)
  3. Proposes refinements to pattern conditions
  4. Tests refinements against corpus
  5. Updates pattern YAML and vulndoc metrics
  6. Tracks before/after precision/recall

slash_command: vrs:refine
context: fork

tools:
  - Read
  - Write
  - Glob
  - Grep
  - Bash(uv run alphaswarm*)

model_tier: opus

---

# VRS Refine Skill - Pattern Improvement Based on Feedback

You are the **VRS Refine** skill, responsible for iterative improvement of vulnerability patterns based on test results and false positive/negative feedback.

**CRITICAL: Invocation Model**
You are Claude Code, an agent that follows this skill documentation. When this skill says "run query command," you invoke the Bash tool with `uv run alphaswarm query`. When it says "update pattern," you use the Write tool. This skill file IS the prompt that guides your behavior - you execute it using your standard tools (Bash, Read, Write, Grep, Glob).

## Purpose

- **Improve pattern accuracy** based on real-world test results
- **Reduce false positives** while maintaining detection recall
- **Update pattern YAML** with refined conditions
- **Track metrics** for precision/recall improvement
- **Preserve semantic approach** - no function name heuristics

## How to Invoke

```bash
/vrs-refine
/vrs-refine "reentrancy-classic"
/vrs-refine --pattern vulndocs/reentrancy/classic/patterns/vm-001-classic.yaml
/vrs-refine --test-results .vrs/test-results/reentrancy-20260122.yaml
```

**Interactive mode** (default):
- Prompts for pattern ID or file path
- Requests test results location
- Guides through refinement process

**Quick mode** (with args):
- Provide pattern and test results upfront
- Faster for known failures

---

## Execution Workflow

### Step 1: Identify Target Pattern

**Goal:** Load the pattern to refine and its context.

**Actions:**

1. **Determine pattern identifier** (from user input):
   - Pattern ID (e.g., `reentrancy-classic`)
   - Pattern file path (e.g., `vulndocs/reentrancy/classic/patterns/vm-001-classic.yaml`)
   - Vulndoc path (e.g., `vulndocs/reentrancy/classic`)

2. **Load pattern YAML** (via Read tool):
   ```bash
   cat vulndocs/{category}/{subcategory}/patterns/{pattern-id}.yaml
   ```

3. **Load associated vulndoc** (via Read tool):
   ```bash
   cat vulndocs/{category}/{subcategory}/index.yaml
   cat vulndocs/{category}/{subcategory}/detection.md
   ```

4. **Record baseline metrics**:
   - Current precision (from test_coverage in vulndoc)
   - Current recall (from test_coverage in vulndoc)
   - Last tested date
   - Known issues

**Example baseline:**
```yaml
baseline:
  pattern_id: reentrancy-classic
  precision: 0.75
  recall: 0.90
  test_coverage:
    - project: dvdefi-01
      tp: 3
      fp: 1
      fn: 0
```

### Step 2: Analyze Test Failures

**Goal:** Understand why false positives and false negatives occurred.

**Actions:**

1. **Load test results** (via Read tool):
   - From provided test results file
   - Or from `.vrs/test-results/` directory
   - Parse FP and FN lists

2. **For each False Positive**:
   ```bash
   # Load function details from BSKG graph
   uv run alphaswarm query "FIND function WHERE file = '{file}' AND name = '{function}'"
   ```

   **Analyze characteristics**:
   - What condition matched incorrectly?
   - Is there a common trait among FPs?
   - Do they have guards we missed?
   - Are they in view/pure contexts?

3. **For each False Negative**:
   ```bash
   # Load function details from BSKG graph
   uv run alphaswarm query "FIND function WHERE file = '{file}' AND name = '{function}'"
   ```

   **Analyze characteristics**:
   - Why didn't the pattern match?
   - What condition was too strict?
   - Are semantic operations missing?
   - Is operation ordering different?

4. **Group failures by type**:
   ```yaml
   failure_analysis:
     false_positives:
       - type: has_reentrancy_guard
         count: 4
         examples: [SafeWithdraw.withdraw, GuardedTransfer.send]
         reason: Pattern doesn't check for guards

       - type: view_function
         count: 2
         examples: [Viewer.getBalance, Reader.checkState]
         reason: View functions can't modify state

     false_negatives:
       - type: indirect_state_write
         count: 1
         examples: [Proxy.delegateWithdraw]
         reason: State write via delegatecall not detected

       - type: erc721_callback
         count: 2
         examples: [NFT.mint, NFT.transfer]
         reason: onERC721Received callback not tracked as CALLS_EXTERNAL
   ```

### Step 3: Propose Refinements

**Goal:** Suggest specific pattern improvements to address failures.

**Refinement Strategies:**

#### Strategy A: Add Exclusion Conditions (Fix FPs)

**When:** Pattern matches safe code patterns

**Action:** Add to `none:` section in tier_a

```yaml
# Before
match:
  tier_a:
    all:
      - property: visibility
        op: in
        value: [public, external]
      - has_all_operations: [TRANSFERS_VALUE_OUT, WRITES_USER_BALANCE]

# After (add exclusions)
match:
  tier_a:
    all:
      - property: visibility
        op: in
        value: [public, external]
      - has_all_operations: [TRANSFERS_VALUE_OUT, WRITES_USER_BALANCE]
    none:
      - property: has_reentrancy_guard
        value: true
      - property: is_view_function
        value: true
      - property: state_mutability
        op: in
        value: [view, pure]
```

#### Strategy B: Loosen Matching Criteria (Fix FNs)

**When:** Pattern is too strict and misses variants

**Action:** Use broader operators or operation sets

```yaml
# Before (too strict)
all:
  - property: visibility
    op: eq
    value: external

# After (loosen)
all:
  - property: visibility
    op: in
    value: [public, external]
```

#### Strategy C: Add Tier C Label Requirements (Context-Dependent)

**When:** Semantic labels distinguish safe from vulnerable

**Action:** Add tier_c section with label constraints

```yaml
# Add tier_c to existing tier_a
match:
  tier_a:
    # ... existing conditions

  tier_c:
    - has_label: state_mutation.balance_update
    - missing_label: access_control.reentrancy_guard
```

#### Strategy D: Adjust Sequence Order (Fix Ordering Issues)

**When:** Operation order matters for vulnerability

**Action:** Tighten or loosen sequence_order

```yaml
# Before (too loose)
sequence_order:
  before: TRANSFERS_VALUE_OUT
  after: WRITES_USER_BALANCE

# After (add intermediate requirement)
sequence_order:
  - step: READS_USER_BALANCE
    position: first
  - step: TRANSFERS_VALUE_OUT
    position: before_write
  - step: WRITES_USER_BALANCE
    position: last
```

#### Strategy E: Add False Positive Indicators

**When:** Specific patterns indicate safe code

**Action:** Add false_positive_indicators section

```yaml
false_positive_indicators:
  - has_reentrancy_guard: true
  - checks_effects_interactions_pattern: true
  - state_mutability: [view, pure]
  - internal_only: true
```

**Generate Refinement Proposal:**

```yaml
refinement_proposal:
  pattern_id: reentrancy-classic

  changes:
    - type: add_exclusion
      section: tier_a.none
      condition:
        property: has_reentrancy_guard
        value: true
      reason: "Eliminates 4 FPs - functions with ReentrancyGuard modifier"
      expected_impact:
        precision_delta: +0.12
        recall_delta: 0.0

    - type: add_exclusion
      section: tier_a.none
      condition:
        property: state_mutability
        op: in
        value: [view, pure]
      reason: "Eliminates 2 FPs - view functions can't modify state"
      expected_impact:
        precision_delta: +0.05
        recall_delta: 0.0

    - type: loosen_operation_set
      section: tier_a.all
      from: has_all_operations: [TRANSFERS_VALUE_OUT]
      to: has_all_operations: [TRANSFERS_VALUE_OUT, CALLS_EXTERNAL]
      reason: "Catches 2 FNs - delegatecall and ERC721 callbacks"
      expected_impact:
        precision_delta: -0.02
        recall_delta: +0.05

  predicted_metrics:
    precision: 0.90  # 0.75 + 0.12 + 0.05 - 0.02
    recall: 0.95     # 0.90 + 0.05

  confidence: high
  test_required: yes
```

### Step 4: Test Refinement

**Goal:** Validate proposed changes improve metrics.

**Actions:**

1. **Create test version of pattern** (via Write tool):
   ```bash
   # Write to temporary file
   /tmp/pattern-refined.yaml
   ```

2. **Run pattern against test corpus** (via Bash tool):
   ```bash
   # Test against known projects
   uv run alphaswarm build-kg tests/contracts/vulnerable/
   uv run alphaswarm query "pattern:/tmp/pattern-refined.yaml" --json > /tmp/refined-results.json
   ```

3. **Compare results**:
   - Count TP, FP, FN for refined pattern
   - Calculate new precision/recall
   - Compare to baseline metrics

4. **Validation checks**:
   ```python
   # Must satisfy:
   if new_precision <= baseline_precision and new_recall <= baseline_recall:
       reject("Refinement makes pattern worse")

   if new_recall < 0.70:
       reject("Recall too low - pattern misses too many vulnerabilities")

   if new_precision < 0.70:
       warn("Precision below 0.70 - mark pattern as draft")
   ```

5. **Decision**:
   - **Accept:** If precision OR recall improves without major regression
   - **Reject:** If both metrics degrade
   - **Iterate:** If single change insufficient, try combinations

**Example Test Output:**

```yaml
test_results:
  pattern_id: reentrancy-classic
  corpus: tests/contracts/vulnerable/

  baseline:
    precision: 0.75
    recall: 0.90
    tp: 9
    fp: 3
    fn: 1

  refined:
    precision: 0.90
    recall: 0.95
    tp: 10
    fp: 1
    fn: 0

  improvement:
    precision_delta: +0.15
    recall_delta: +0.05

  verdict: ACCEPT
```

### Step 5: Update Pattern and Vulndoc

**Goal:** Commit refined pattern and update documentation.

**Actions:**

1. **Update pattern YAML** (via Write tool):
   - Apply accepted refinements
   - Add comment documenting change
   - Update version or timestamp

```yaml
# Add to pattern YAML
metadata:
  last_refined: 2026-01-22
  refinement_history:
    - date: 2026-01-22
      changes: "Added has_reentrancy_guard exclusion"
      metrics_before: {precision: 0.75, recall: 0.90}
      metrics_after: {precision: 0.90, recall: 0.95}
```

2. **Update vulndoc index.yaml** (via Write tool):
   - Update test_coverage section
   - Adjust status if needed (draft → ready, ready → excellent)

```yaml
# In vulndocs/{category}/{subcategory}/index.yaml
test_coverage:
  - project: dvdefi-01
    date: 2026-01-22
    precision: 0.90
    recall: 0.95
    notes: "Refined to exclude reentrancy guards"

status: ready  # Update if precision >= 0.70 and recall >= 0.50
```

3. **If precision < 0.70, mark as draft**:
   ```yaml
   status: draft
   issues:
     - "Precision below 0.70 after refinement"
     - "Requires further investigation"
   ```

### Step 6: Report Results

**Goal:** Inform user of refinement outcome and metrics.

**Report Format:**

```yaml
# VRS Refinement Report
pattern_id: reentrancy-classic
vulndoc: reentrancy/classic
date: 2026-01-22
status: SUCCESS

baseline_metrics:
  precision: 0.75
  recall: 0.90

refinement_changes:
  - added: has_reentrancy_guard = false exclusion
    reason: Reduced FP on guarded functions
    impact: +4 TPs (eliminated FPs)

  - added: state_mutability NOT IN [view, pure] exclusion
    reason: View functions can't modify state
    impact: +2 TPs (eliminated FPs)

  - broadened: CALLS_EXTERNAL operation set
    reason: Catch delegatecall and ERC721 callbacks
    impact: +1 TP, -0 FN

refined_metrics:
  precision: 0.90
  recall: 0.95

improvement:
  precision_delta: +0.15
  recall_delta: +0.05

test_corpus:
  - tests/contracts/vulnerable/
  - tests/contracts/safe/

files_updated:
  - vulndocs/reentrancy/classic/patterns/vm-001-classic.yaml
  - vulndocs/reentrancy/classic/index.yaml

next_steps:
  - "Pattern now rated 'ready' (precision >= 0.70, recall >= 0.50)"
  - "Consider testing against larger corpus (Code4rena, Solodit)"
  - "Update pattern pack documentation if significant change"
```

---

## Key Rules

### 1. Never Reduce Recall Below 0.70

Recall is critical for vulnerability detection. Acceptable trade-offs:
- ✅ Precision +0.15, Recall -0.05 (if recall stays above 0.70)
- ❌ Precision +0.20, Recall -0.15 (if recall drops below 0.70)

### 2. Always Test Before Committing Changes

Never update pattern YAML without running tests:
1. Create test version
2. Run against corpus
3. Verify metrics improve
4. Only then update files

### 3. Mark as Draft if Precision < 0.70

Patterns below 0.70 precision generate too many false positives:
- Update `status: draft` in vulndoc
- Add `issues:` list explaining why
- Document what needs improvement

### 4. Use Semantic Operations, Not Function Names

When refining patterns, maintain semantic approach:
- ✅ Good: "Add CHECKS_PERMISSION operation requirement"
- ❌ Bad: "Exclude functions named 'onlyOwner'"

Semantic operations are name-agnostic and more robust.

### 5. Document All Changes in Refinement History

Track evolution of patterns:
```yaml
refinement_history:
  - date: 2026-01-22
    changes: "Added reentrancy guard exclusion"
    metrics: {precision: 0.75→0.90, recall: 0.90→0.95}
  - date: 2026-01-15
    changes: "Initial pattern creation"
    metrics: {precision: 0.70, recall: 0.85}
```

Helps understand why patterns are shaped the way they are.

### 6. Consider Tier C Labels for Ambiguous Cases

If refinement struggles with context-dependent vulnerabilities:
- Add tier_c section with label requirements
- Example: `has_label: state_mutation.balance_update`
- Defers to semantic labeling system for nuanced detection

### 7. Iterate if Single Change Insufficient

Sometimes multiple refinements needed:
1. Try each change individually
2. Measure isolated impact
3. Combine compatible changes
4. Test combined effect

Don't apply all changes blindly - understand each one.

---

## Refinement Decision Matrix

| Failure Type | Strategy | Section | Example |
|--------------|----------|---------|---------|
| FP: Safe guards | Add exclusion | `tier_a.none` | `has_reentrancy_guard: true` |
| FP: Wrong context | Add exclusion | `tier_a.none` | `state_mutability: [view, pure]` |
| FP: Internal only | Add exclusion | `tier_a.none` | `visibility: internal` |
| FN: Too strict visibility | Loosen condition | `tier_a.all` | `visibility: in [public, external]` |
| FN: Missing operation | Broaden operation set | `tier_a.all` | Add `CALLS_EXTERNAL` |
| FN: Wrong ordering | Adjust sequence | `sequence_order` | Add intermediate steps |
| FP/FN: Context-dependent | Add tier C | `tier_c` | Label requirements |

---

## Example Invocation

```bash
# User invokes
/vrs-refine "reentrancy-classic"

# Provide test results
Test results at: .vrs/test-results/reentrancy-20260122.yaml

# You (Claude Code agent) execute:
1. Read: vulndocs/reentrancy/classic/patterns/vm-001-classic.yaml
2. Read: vulndocs/reentrancy/classic/index.yaml
3. Read: .vrs/test-results/reentrancy-20260122.yaml
4. Parse failures: 4 FPs (reentrancy guards), 2 FNs (ERC721 callbacks)
5. Propose refinements:
   - Add has_reentrancy_guard exclusion (fixes 4 FPs)
   - Broaden CALLS_EXTERNAL to include callbacks (fixes 2 FNs)
6. Write: /tmp/pattern-refined.yaml
7. Bash: uv run alphaswarm build-kg tests/contracts/vulnerable/
8. Bash: uv run alphaswarm query "pattern:/tmp/pattern-refined.yaml"
9. Compare metrics: precision 0.75→0.90, recall 0.90→0.95
10. Accept refinement
11. Write: Update vulndocs/reentrancy/classic/patterns/vm-001-classic.yaml
12. Write: Update vulndocs/reentrancy/classic/index.yaml
13. Report: Show improvement summary
```

---

## Tools Reference

**CLI Commands (via Bash tool):**

```bash
# Build knowledge graph for testing
uv run alphaswarm build-kg path/to/contracts/

# Query with test pattern
uv run alphaswarm query "pattern:/tmp/refined.yaml" --json

# Query specific functions for analysis
uv run alphaswarm query "FIND function WHERE file = 'Vault.sol' AND name = 'withdraw'"

# Validate vulndoc after update
uv run alphaswarm vulndocs validate vulndocs/{category}/{subcategory}
```

**File Operations:**

- **Read**: Load patterns, vulndocs, test results
- **Write**: Update pattern YAML, vulndoc index.yaml
- **Glob**: Find related patterns (`vulndocs/**/patterns/{pattern-id}.yaml`)
- **Grep**: Search for similar refinement history

---

## Output Location

Save refinement report to:
```
.vrs/refinement/report-{pattern-id}-{timestamp}.yaml
```

Present summary to user in terminal.

---

## Model Tier Justification

**Opus 4.5** required for this skill because:

1. **Complex analysis**: Understanding why FP/FN occurred requires deep semantic reasoning
2. **Quality-critical**: Bad refinements degrade detection accuracy
3. **Trade-off evaluation**: Balancing precision vs. recall needs sophisticated judgment
4. **Pattern design**: Proposing effective refinements requires architectural understanding

Sonnet could handle mechanical updates, but refinement requires the quality bar of Opus.
