# T2: Pattern Audit Report

## Executive Summary

**Of 557 detection patterns, only ~12 have evidence of actually working.** The vast majority (385/557 = 69%) reference properties the builder never produces, making them structurally non-functional. Of the 172 that use real properties, only 12 have any test_coverage data, and only 6 report non-zero true positives. The claimed "84.6% DVDeFi detection rate" is a self-assessed YAML annotation, not a reproducible benchmark result. The ground truth file for DVDeFi is entirely TODOs.

**Honest answer: ~2% of patterns are proven to work. ~31% could theoretically work. ~69% are dead code.**

---

## Pattern Inventory

### Total Files

| Type | Count |
|------|-------|
| Pattern YAML files (in `*/patterns/`) | 557 |
| Pattern Context Packs (`.pcp.yaml`) | 5 |
| Index YAML files | 106 |
| Core-pattern.md knowledge docs | 18 |
| **Total YAML in vulndocs** | **686** |

### By Category

| Category | Pattern Count | % of Total |
|----------|--------------|------------|
| access-control | 246 | 44.2% |
| reentrancy | 99 | 17.8% |
| logic | 56 | 10.1% |
| dos | 49 | 8.8% |
| upgrade | 30 | 5.4% |
| arithmetic | 24 | 4.3% |
| oracle | 16 | 2.9% |
| crypto | 15 | 2.7% |
| mev | 8 | 1.4% |
| token | 7 | 1.3% |
| flash-loan | 5 | 0.9% |
| governance | 3 | 0.5% |
| cross-chain | 3 | 0.5% |
| vault | 1 | 0.2% |

**Red flag:** Access-control alone is 44% of all patterns (246). The `access-control/general/patterns/` directory contains 113 `auth-NNN` files (auth-001 through auth-120, with some gaps), most of which are minimal stubs under 15 lines. This looks like batch-generated content.

### By Quality Rating (status field)

| Status | Count | Notes |
|--------|-------|-------|
| **NO STATUS** | **482** | **86.5% of patterns have no status field at all** |
| ready | ~27 | Some have inline comments appended |
| deprecated | 20 | Explicitly marked deprecated |
| excellent | ~19 | Some have inline comments appended |
| draft | ~16 | |
| Other/malformed | ~3 | e.g., `status: true`, quoted strings |

**Only 80 of 557 patterns (14.4%) have any status field.** The remaining 482 are status-less YAML files — indeterminate quality.

### By Tier

| Tier Structure | Count | Notes |
|----------------|-------|-------|
| Patterns with `tier_a:` section | 67 | Explicit deterministic matching |
| Patterns with `tier_b:` section | 23 | LLM risk-tag matching |
| Patterns with `tier_match: {}` (empty) | 0 (by exact match) | But many have effectively empty tier blocks |
| Patterns with flat `match:` (no tier) | ~490 | Backward-compatible format; treated as tier_a_only |

**Assessment:** The tier system exists in code but is barely used. 67/557 (12%) use explicit tier_a, 23/557 (4%) use tier_b. The vast majority use the flat format which defaults to tier_a_only. Tier C (semantic labels) exists in code but no patterns use it.

---

## The Devastating Property Gap

### The Core Problem

**337 of 485 unique properties referenced by patterns DO NOT EXIST in the builder.**

| Metric | Count |
|--------|-------|
| Unique properties referenced by patterns | 485 |
| Properties actually produced by builder (`FunctionProperties`) | 208 |
| Properties in patterns that match builder | 148 |
| **Orphan properties (not in builder)** | **337 (69.5%)** |

### Impact on Patterns

| Category | Count | % |
|----------|-------|---|
| Patterns using at least one orphan property | **385** | **69.1%** |
| Patterns using only builder-supported properties | **172** | **30.9%** |

**What this means:** 385 patterns reference properties that the graph builder never computes. When the pattern engine evaluates these, `_resolve_node_property` returns `None` from `node.properties.get(name)`. For conditions like `{property: multicall_batching_without_guard, op: eq, value: true}`, `None != true` so the pattern **silently never matches anything**. These patterns are dead code.

### Examples of Orphan Properties (245 singleton properties used only once)

Properties that appear in exactly one pattern and don't exist in the builder:
- `multicall_batching_without_guard` (auth-050)
- `multisig_member_change_without_minimum_check` (auth-099)
- `bypassable_access_control`
- `cross_contract_auth_confusion`
- `division_before_multiplication`
- `allows_self_modification`

These look like aspirational properties — someone wrote patterns assuming the builder would eventually produce them, but it never did.

---

## Test Coverage

### Pattern Tests

| Metric | Count |
|--------|-------|
| Patterns with `test_coverage:` section | 60 |
| Patterns with non-zero `true_positives` | 36 |
| Patterns with non-zero TP **AND** using builder-supported properties | **6** |
| Patterns WITHOUT any test_coverage | **502** |

**Only 6 patterns have test evidence AND use properties the builder actually produces.** The other 30 patterns claiming non-zero true_positives reference orphan properties — meaning their test_coverage data was likely self-reported or computed against a different version of the builder.

### Test Files Related to Patterns

Tests found in `tests/` that mention "pattern":
- `test_defi_infrastructure_patterns.py` — Tests DeFi infrastructure pattern detection
- `test_property_sets.py` — Tests property set definitions
- `test_confidence_enforcement.py` — Tests confidence scoring
- Various other files that mention "pattern" incidentally

**Critical finding:** Most test files test the pattern engine's YAML parsing and condition evaluation mechanics, not whether patterns detect actual vulnerabilities in real contracts. There are no systematic tests that:
1. Build a graph from a known-vulnerable contract
2. Run a specific pattern against that graph
3. Assert the pattern detects the known vulnerability

### The DVDeFi "Benchmark"

The `benchmarks/dvdefi/suite.yaml` contains:

```yaml
summary:
  total_challenges: 13
  detectable: 12
  detected: 11
  not_applicable: 1
  not_detected: 1
  detection_rate: 0.846
```

**This is a manually-annotated YAML file, not computed results.** The `status: detected` flags are hand-placed claims. Evidence:

1. **The ground truth is all TODOs:** `.vrs/corpus/ground-truth/dvdefi-v3.yaml` contains entries like:
   ```yaml
   ground_truth:
   - pattern: TODO
     severity: medium
     location: function_name:line
     description: 'TODO: Add description'
   ```

2. **The benchmark validation test validates the YAML, not detection:**
   `test_benchmark_validation.py` checks that the suite YAML file has the right structure and that `detection_rate >= 0.80` — but it reads this from the YAML file itself, not from running patterns against contracts.

3. **No CI pipeline runs the benchmark.** The `benchmark.yml` GitHub workflow exists but tests validation of the YAML format, not actual detection.

**Verdict on 84.6%:** This number is a self-assessment annotation. There is no evidence of a reproducible end-to-end test that builds graphs from DVDeFi contracts, runs all patterns, and measures detection. The number should be treated as aspirational, not factual.

---

## Tier C Reality Check

**Tier C (semantic labels) is pure vaporware.**

- The `TierCConditionSpec` dataclass exists in `patterns.py`
- The `_parse_tier_c_conditions` method exists
- **Zero patterns use Tier C conditions**
- No `_match_tier_c` method exists in `PatternEngine` — the engine parses them but never evaluates them
- The semantic labeling module (`labels/`) would need to be integrated, but there's no evidence this integration exists end-to-end

**Tier B is partially implemented but barely used:**
- 23 patterns have tier_b sections
- The `TierBMatcher` exists and is lazily loaded
- However, Tier B depends on a `TagStore` which requires LLM-generated risk tags
- No evidence of end-to-end testing with actual LLM tag generation

---

## Honest Verdict

### What Percentage of 557 Patterns Are PROVEN to Work?

| Category | Count | % | Evidence |
|----------|-------|---|----------|
| **Proven working** (non-zero TP + real properties) | **~6** | **1.1%** | Have test_coverage with actual TP counts against builder properties |
| **Likely working** (real properties + status) | ~12 | 2.2% | Status "excellent" or "ready" with builder-supported properties |
| **Potentially working** (real properties, untested) | ~160 | 28.7% | Use builder-supported properties but no test evidence |
| **Deprecated** | ~20 | 3.6% | Explicitly marked deprecated |
| **Dead code** (orphan properties) | **385** | **69.1%** | Reference properties the builder never produces |
| **Total non-functional** | **~405** | **~72.7%** | Deprecated + dead code |

### Pattern Engine Assessment

The pattern engine (`PatternEngine.run()`) is well-implemented:
- Properly handles Tier A matching (property, edge, path, operation conditions)
- Has Tier B integration
- Supports explain mode
- Good condition operators (eq, neq, in, regex, etc.)

**The engine is solid. The data it runs against is the problem.** It's like having a well-built search engine with a database full of empty records.

---

## Specific Gaps

1. **Property gap is catastrophic:** 337/485 referenced properties don't exist. Patterns silently fail with no error — they just never match. This is the #1 issue.

2. **No validation pipeline:** Nothing checks at pattern load time whether referenced properties actually exist in the builder's `FunctionProperties`. A simple check would flag 385 dead patterns immediately.

3. **No end-to-end detection tests:** The test suite verifies YAML parsing and engine mechanics but not "does pattern X detect vulnerability Y in contract Z."

4. **DVDeFi ground truth is empty TODOs:** The benchmark claims 84.6% detection but the ground truth is placeholder text.

5. **Mass-generated access-control patterns:** auth-001 through auth-120 look batch-generated. Many are 10-14 line stubs with single-property matches on properties that don't exist.

6. **No false positive measurement:** Of 557 patterns, none have systematic FP rates measured against safe contracts.

7. **Tier B/C are effectively unused:** 23/557 use Tier B. 0/557 use Tier C. The multi-tier system described in docs is aspirational.

8. **Deprecated patterns not cleaned up:** 20 deprecated patterns still sit in the active pattern directories, potentially matched by the engine.

9. **No precision/recall on real projects:** Test_coverage sections that exist show metrics for toy "token-vault" or "upgrade-proxy" test projects, not real-world DeFi protocols.

10. **Status field inconsistency:** 86.5% of patterns have no status. Status values have trailing comments (`status: excellent  # FIXED: ...`). No enforcement.

---

## Recommendations for Milestone 6.0

### Immediate (Before Claiming Pattern Count)

1. **Property validation gate:** Add a CI check that loads all patterns and verifies every referenced property exists in `FunctionProperties`. Fail build on orphan properties. This will instantly reveal the true state.

2. **Remove dead patterns:** Delete or quarantine the 385 patterns with orphan properties. Either implement the properties in the builder or remove the patterns. Do NOT count them.

3. **Honest metrics:** Replace "557 patterns" with whatever survives the property validation. Currently that's ~172, of which ~12 have any quality evidence.

### Short-term (Milestone 6.0 Focus)

4. **DVDeFi end-to-end benchmark:** Actually run graphs + patterns against DVDeFi contracts. Record results programmatically. Generate detection rate from data, not YAML annotations.

5. **Pattern quality pipeline:** For each pattern, require at least one vulnerable contract + one safe contract that produce expected match/no-match results.

6. **Curate top-30 patterns:** Focus on the ~12 proven patterns + ~18 most promising ones. Get these to "excellent" status with real metrics. 30 high-quality patterns > 557 untested YAML files.

### Medium-term

7. **Property roadmap:** Prioritize implementing high-value orphan properties in the builder. The 337 missing properties represent detection *potential* — but only if implemented.

8. **Tier B pilot:** Pick 5 patterns where LLM risk tagging would add clear value. Test end-to-end with actual LLM calls. Measure whether Tier B adds precision.

9. **Real-world benchmark:** Test against known-vulnerable Code4rena or Immunefi submissions. This is the only credible way to claim detection capability.
