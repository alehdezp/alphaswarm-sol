---
name: vrs-validate-vulndocs
description: |
  Mandatory validation pipeline for any vulndocs/ changes. Orchestrates the cost-optimized
  validation workflow required for Phase 7.2 corpus research and VulnDocs expansion.

  Invoke when:
  - Any file under vulndocs/ is created, modified, or deleted
  - Before committing VulnDocs changes
  - After pattern refinement or addition
  - As part of CI/CD pipeline for VulnDocs quality gate

slash_command: vrs:validate-vulndocs
disable-model-invocation: true

allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(alphaswarm*)
  - Bash(uv run*)
---

# VRS Validate VulnDocs Skill - Mandatory Validation Pipeline

You are the **VRS Validate VulnDocs** skill, responsible for orchestrating the mandatory validation pipeline for any `vulndocs/` changes.

## How to Invoke

```bash
/vrs-validate-vulndocs                      # Validate all vulndocs changes
/vrs-validate-vulndocs --mode quick         # Quick validation (prevalidator + schema only)
/vrs-validate-vulndocs --mode standard      # Standard validation (default)
/vrs-validate-vulndocs --mode thorough      # Full GA-level validation
/vrs-validate-vulndocs --category reentrancy  # Validate specific category
/vrs-validate-vulndocs --pattern reentrancy-classic  # Validate specific pattern
```

---

## Purpose

This skill enforces the **mandatory VulnDocs validation workflow** from Phase 7.2. Every change to `vulndocs/` MUST pass through this pipeline before merge.

**Policy:** Any addition or change to `vulndocs/` MUST follow this workflow. No direct edits without the pipeline.

---

## Pipeline Stages (In Order)

The validation pipeline executes these stages **sequentially**:

### Stage 1: Test Conductor (Orchestration)

**Agent:** `vrs-test-conductor` (claude-opus-4)
**Purpose:** Coordinate the full validation run
**Always runs:** Yes

```bash
# Orchestration setup - no direct execution
# Test conductor coordinates all subsequent stages
```

### Stage 2: Prevalidation Gate

**Agent:** `vrs-prevalidator` (claude-haiku-4.5)
**Purpose:** Fast provenance, schema, and duplicate checks
**Always runs:** Yes

Validates:
- URL provenance in `.vrs/corpus/metadata/urls.yaml`
- Schema compliance for all VulnDoc entries
- Duplicate detection across patterns
- Required fields present (url, accessed_at, query, category)

**Gate:** If prevalidation fails, pipeline STOPS immediately.

```bash
# Prevalidation checks
uv run alphaswarm vulndocs validate vulndocs/ --schema-only
```

### Stage 3: Corpus Validation

**Agent:** `vrs-corpus-curator` (claude-sonnet-4)
**Purpose:** Corpus integrity and ground truth verification
**Always runs:** Yes

Validates:
- Corpus.db schema compliance
- Ground truth from authoritative sources
- Composition balance (30% recent-audits, 40% mutations, 30% adversarial)
- No duplicate entries

### Stage 4: Pattern Verification

**Agent:** `vrs-pattern-verifier` (claude-sonnet-4)
**Purpose:** Evidence gates for Tier B/C patterns
**Always runs:** Yes

Validates:
- Tier A patterns have strict match criteria
- Tier B patterns have LLM verification gates
- Tier C patterns have label dependencies declared
- All patterns have test coverage references

### Stage 5: Benchmark Execution

**Agent:** `vrs-benchmark-runner` (claude-haiku-4)
**Purpose:** Compute precision/recall metrics
**Always runs:** Yes (in standard/thorough mode)

Metrics collected:
- Precision (target: >= 85%)
- Recall critical (target: >= 95%)
- Recall high (target: >= 85%)
- F1 score

```bash
# Quick benchmark for changed patterns
uv run alphaswarm vulndocs validate vulndocs/ --metrics
```

### Stage 6: Mutation Testing

**Agent:** `vrs-mutation-tester` (claude-haiku-4)
**Purpose:** Generate variants for pattern robustness
**Conditional:** Only when patterns changed

Generates:
- 10x variants per changed pattern
- Identifier renames, code reordering, structural changes
- Safe variants for FP testing

### Stage 7: Regression Analysis

**Agent:** `vrs-regression-hunter` (claude-sonnet-4)
**Purpose:** Detect accuracy degradation vs baseline
**Conditional:** Only if baseline exists AND metrics dropped

Checks:
- Per-pattern recall changes
- Overall precision/recall delta
- Critical severity recall gates

### Stage 8: Gap Analysis

**Agent:** `vrs-gap-finder-lite` (claude-sonnet-4.5)
**Purpose:** Fast coverage and FP hotspot scan
**Always runs:** Yes

If `vrs-gap-finder-lite` returns `escalate_to_opus: true`:
- Spawn `vrs-gap-finder` (claude-opus-4) for deep analysis
- Generate prioritized roadmap items

---

## Adaptive Pipeline Rules

The pipeline adapts based on what changed:

### New Pattern Added

```
Stage 1: test-conductor
Stage 2: prevalidator (provenance required for new entries)
Stage 3: corpus-curator
Stage 4: pattern-verifier (strict evidence gates)
Stage 5: benchmark-runner (new pattern metrics)
Stage 6: mutation-tester (generate variants)
Stage 7: regression-hunter (skip if no baseline)
Stage 8: gap-finder-lite
```

### Existing Pattern Modified

```
Stage 1: test-conductor
Stage 2: prevalidator
Stage 3: corpus-curator (skip if only pattern change)
Stage 4: pattern-verifier
Stage 5: benchmark-runner
Stage 6: mutation-tester (re-generate variants)
Stage 7: regression-hunter (compare to previous)
Stage 8: gap-finder-lite
```

### Metadata-Only Change

```
Stage 1: test-conductor
Stage 2: prevalidator (schema only)
Stage 3: corpus-curator (skip)
Stage 4: pattern-verifier (skip)
Stage 5: benchmark-runner (skip)
Stage 6: mutation-tester (skip)
Stage 7: regression-hunter (skip)
Stage 8: gap-finder-lite (skip)
```

---

## CLI Commands

### Full Validation

```bash
# Run complete validation pipeline
uv run alphaswarm vulndocs validate vulndocs/

# Validate specific category
uv run alphaswarm vulndocs validate vulndocs/reentrancy/

# Validate with JSON output
uv run alphaswarm vulndocs validate vulndocs/ --json

# Validate with metrics collection
uv run alphaswarm vulndocs validate vulndocs/ --metrics --baseline .vrs/baselines/latest.json
```

### Quick Checks

```bash
# Schema validation only
uv run alphaswarm vulndocs validate vulndocs/ --schema-only

# List validation status per entry
uv run alphaswarm vulndocs list --status validated

# Show entry info
uv run alphaswarm vulndocs info vulndocs/reentrancy/classic/
```

---

## Output Format

### Console Output

```
VRS VulnDocs Validation Pipeline
================================

Stage 1: Test Conductor
  Status: COORDINATING
  Mode: standard

Stage 2: Prevalidation
  Status: PASSED
  Provenance: 47/47 URLs verified
  Schema: 47/47 entries valid
  Duplicates: 0 found

Stage 3: Corpus Validation
  Status: PASSED
  Contracts: 450 total
  Balance: recent-audits 30%, mutations 40%, adversarial 30%

Stage 4: Pattern Verification
  Status: PASSED
  Tier A: 44 patterns verified
  Tier B: 12 patterns with LLM gates
  Tier C: 21 patterns with label deps

Stage 5: Benchmark Execution
  Status: PASSED
  Precision: 87% (target: 85%)
  Recall (critical): 97% (target: 95%)
  Recall (high): 88% (target: 85%)

Stage 6: Mutation Testing
  Status: SKIPPED (no pattern changes)

Stage 7: Regression Analysis
  Status: PASSED
  Delta precision: +0.02
  Delta recall: -0.01

Stage 8: Gap Analysis
  Status: PASSED
  Gaps found: 3 (low severity)
  Escalation: not required

Pipeline Result: PASSED
Quality Gates: 3/3 passed
```

### JSON Output

```json
{
  "validation_result": {
    "status": "passed",
    "mode": "standard",
    "timestamp": "2026-01-29T12:00:00Z",
    "stages": {
      "test_conductor": {"status": "coordinated"},
      "prevalidator": {
        "status": "passed",
        "provenance_ok": true,
        "schema_ok": true,
        "duplicates": []
      },
      "corpus_curator": {"status": "passed"},
      "pattern_verifier": {"status": "passed"},
      "benchmark_runner": {
        "status": "passed",
        "precision": 0.87,
        "recall_critical": 0.97,
        "recall_high": 0.88
      },
      "mutation_tester": {"status": "skipped", "reason": "no_pattern_changes"},
      "regression_hunter": {"status": "passed"},
      "gap_finder_lite": {
        "status": "passed",
        "gaps": 3,
        "escalate_to_opus": false
      }
    },
    "quality_gates": {
      "precision_gate": {"target": 0.85, "actual": 0.87, "passed": true},
      "recall_critical_gate": {"target": 0.95, "actual": 0.97, "passed": true},
      "recall_high_gate": {"target": 0.85, "actual": 0.88, "passed": true}
    }
  }
}
```

---

## Quality Gates

| Gate | Target | Blocking |
|------|--------|----------|
| Precision | >= 85% | Yes |
| Recall (critical) | >= 95% | Yes |
| Recall (high) | >= 85% | Yes |
| Recall (medium) | >= 70% | No (warning) |
| Schema compliance | 100% | Yes |
| Provenance verified | 100% | Yes |

---

## Model Delegation

| Stage | Agent | Model | Cost Tier |
|-------|-------|-------|-----------|
| 1 | vrs-test-conductor | claude-opus-4 | High |
| 2 | vrs-prevalidator | claude-haiku-4.5 | Low |
| 3 | vrs-corpus-curator | claude-sonnet-4 | Medium |
| 4 | vrs-pattern-verifier | claude-sonnet-4 | Medium |
| 5 | vrs-benchmark-runner | claude-haiku-4 | Low |
| 6 | vrs-mutation-tester | claude-haiku-4 | Low |
| 7 | vrs-regression-hunter | claude-sonnet-4 | Medium |
| 8 | vrs-gap-finder-lite | claude-sonnet-4.5 | Medium |
| 8+ | vrs-gap-finder | claude-opus-4 | High (escalation only) |

**Cost optimization:** Default mode uses Haiku/Sonnet. Opus only for orchestration and escalated gap analysis.

---

## Integration with CI/CD

```yaml
# .github/workflows/vulndocs-validation.yml
name: VulnDocs Validation

on:
  pull_request:
    paths:
      - 'vulndocs/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install alphaswarm
      - name: Run validation
        run: uv run alphaswarm vulndocs validate vulndocs/ --json > validation.json
      - name: Check gates
        run: |
          if jq -e '.validation_result.status != "passed"' validation.json; then
            echo "Validation failed"
            exit 1
          fi
```

---

## Common Issues

### Issue: Provenance Missing

```
Error: Missing URL provenance for vulndocs/reentrancy/new-pattern/

Solution:
1. Add URL to .vrs/corpus/metadata/urls.yaml
2. Include: url, accessed_at, query, category, agent, extracted fields
3. Re-run validation
```

### Issue: Schema Violation

```
Error: Schema validation failed for META.yaml

Solution:
1. Check required fields: id, name, severity, category, subcategory
2. Validate YAML syntax
3. Run: uv run alphaswarm vulndocs validate vulndocs/path/ --schema-only
```

### Issue: Quality Gate Failed

```
Error: Recall (critical) below threshold: 92% < 95%

Solution:
1. Review false negatives in benchmark output
2. Adjust pattern match criteria
3. Add missing test cases to corpus
4. Re-run with: /vrs-validate-vulndocs --mode thorough
```

---

## Related Skills

- `/vrs-discover` - Find new vulnerabilities via Exa search
- `/vrs-add-vulnerability` - Add new VulnDocs entries
- `/vrs-refine` - Improve patterns based on test feedback
- `/vrs-test-pattern` - Validate patterns against real projects
- `/vrs-health-check` - Validate overall installation

---

## Notes

- This is a USER-CONTROLLED skill (`disable-model-invocation: true`)
- All stages run sequentially to maintain pipeline integrity
- Failed gates block subsequent stages
- Use `--mode quick` for development feedback, `--mode thorough` for release
- Escalation to Opus only when gap-finder-lite flags issues
