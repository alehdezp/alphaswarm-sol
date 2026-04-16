---
name: vrs-test-full
description: |
  Complete test orchestration skill for AlphaSwarm Test Forge. Runs all testing phases including
  health check, component tests, integration tests, E2E pipeline, model comparison, mutation tests,
  adversarial tests, and gap analysis.

  Invoke when user wants to:
  - Run full test suite: "run all tests", "complete test run", "/vrs-test-full"
  - Validate before release: "test everything", "GA validation"
  - Generate comprehensive metrics: "full benchmark", "test report"

  This skill orchestrates the complete testing pipeline:
  1. Health check (tools, corpus, rankings)
  2. Component tests (each agent role)
  3. Integration tests (context-merge flow)
  4. E2E pipeline tests (request to verdicts)
  5. Model comparison (if requested)
  6. Mutation tests (pattern robustness)
  7. Adversarial tests (false positive traps)
  8. Gap analysis (coverage holes)
  9. Report generation (TestMetrics summary)

slash_command: vrs:test-full
context: fork
disable-model-invocation: true

allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(pytest*)
  - Bash(uv run*)
  - Bash(alphaswarm*)
---

# VRS Test Full - Complete Test Orchestration

You are the **VRS Test Full** skill, responsible for orchestrating comprehensive testing of the AlphaSwarm vulnerability detection system using the AlphaSwarm Test Forge.

## Philosophy

From PHILOSOPHY.md and Test Forge Context:
- **Accuracy is paramount** - Quality gates must be met before cost optimization
- **Layered testing** - Component, integration, and E2E tests validate different concerns
- **Evidence-based metrics** - Precision, recall, and F1 scores drive decisions
- **No shortcuts** - All agent roles tested, all interactions validated

**Quality Gate Targets (GA Requirements):**
- Precision >= 85% (low false positive rate)
- Recall (Critical) >= 95% (catch critical vulnerabilities)
- Recall (High) >= 85%
- Recall (Medium/Low) >= 70%

## How to Invoke

```bash
/vrs-test-full
/vrs-test-full --mode thorough
/vrs-test-full --skip-model-comparison
/vrs-test-full --corpus recent-audits
```

---

## Execution Flow

The test orchestration follows 9 phases:

```
HEALTH CHECK -> COMPONENT -> INTEGRATION -> E2E -> MODEL COMPARISON
      -> MUTATION -> ADVERSARIAL -> GAP ANALYSIS -> REPORT
```

### Phase 1: HEALTH CHECK
**Verify tools, corpus, and rankings are available**

```bash
# Check VRS installation
alphaswarm tools status

# Verify corpus database
ls -la .vrs/testing/corpus.db

# Check rankings exist
ls -la .vrs/rankings/rankings.yaml
```

### Phase 2: COMPONENT TESTS
**Test each agent role independently**

```bash
# Run agent component tests in parallel
pytest tests/agents/ -n auto --dist loadfile -v

# Individual agent tests:
# - vrs-context-merge: Context synthesis quality
# - vrs-context-verifier: Quality gate accuracy
# - vrs-vuln-discovery: Detection accuracy
# - vrs-attacker: Exploit path construction
# - vrs-defender: Guard detection
# - vrs-verifier: Evidence cross-checking
```

### Phase 3: INTEGRATION TESTS
**Test agent interactions and bead flows**

```bash
# Run integration tests
pytest tests/integration/ -n auto --dist loadfile -v

# Validates:
# - Context-merge -> verifier -> bead flow
# - Skill invocation chains
# - Bead state persistence
```

### Phase 4: E2E PIPELINE TESTS
**Full workflow from request to verdicts**

```bash
# Run E2E tests
pytest tests/e2e/ -v

# Tests complete audit pipeline:
# - Solidity source -> BSKG graph
# - Pattern detection -> beads
# - Multi-agent verification -> verdicts
```

### Phase 5: MODEL COMPARISON (Optional)
**Compare models on corpus for accuracy**

```bash
# Run model comparison benchmark
/vrs-benchmark-model --models "opus,sonnet" --task-type detect

# Updates rankings.yaml with results
```

### Phase 6: MUTATION TESTS
**Validate pattern robustness against mutations**

```bash
# Generate and test mutations
/vrs-mutate-contract tests/contracts/reentrancy.sol --count 5
pytest tests/e2e/test_mutation_robustness.py -v
```

### Phase 7: ADVERSARIAL TESTS
**Test false positive traps and obfuscation**

```bash
# Run adversarial test suite
pytest tests/adversarial/ -v

# Tests:
# - Safe code that looks vulnerable
# - Proxy/delegatecall edge cases
# - Obfuscation techniques
```

### Phase 8: GAP ANALYSIS
**Identify coverage holes and improvement priorities**

```bash
# Run gap finder
pytest tests/ --cov=src/alphaswarm_sol --cov-report=html

# Analyze missed detections
# Generate gap inventory
```

### Phase 9: REPORT GENERATION
**Generate comprehensive TestMetrics summary**

```bash
# Final report generation
# Outputs:
# - TestMetrics summary (precision, recall, F1)
# - Per-segment breakdown
# - Model rankings update
# - Gap inventory
```

---

## Usage Examples

### Standard Full Test
```bash
/vrs-test-full

# Output:
# Phase 1/9: Health Check... PASS
# Phase 2/9: Component Tests... 45/45 PASS
# Phase 3/9: Integration Tests... 12/12 PASS
# Phase 4/9: E2E Pipeline... 8/8 PASS
# Phase 5/9: Model Comparison... SKIPPED (use --with-model-comparison)
# Phase 6/9: Mutation Tests... 20/20 PASS
# Phase 7/9: Adversarial Tests... 15/15 PASS
# Phase 8/9: Gap Analysis... 3 gaps identified
# Phase 9/9: Report Generation... COMPLETE
#
# === Test Metrics Summary ===
# Precision: 87.2%
# Recall (Critical): 96.1%
# Recall (High): 88.3%
# F1 Score: 0.89
#
# GA Gate Status: PASS
```

### With Model Comparison
```bash
/vrs-test-full --with-model-comparison

# Adds Phase 5 model comparison
# Updates .vrs/rankings/rankings.yaml
```

### Specific Corpus Segment
```bash
/vrs-test-full --corpus adversarial

# Runs only against adversarial test contracts
# Useful for stress testing detection
```

### Thorough Mode (30 min)
```bash
/vrs-test-full --mode thorough

# Runs exhaustive test suite
# Includes all corpus segments
# Full mutation testing (10x variants)
```

---

## Output Format

### TestMetrics Summary
```markdown
# VRS Test Report

**Run ID:** test-2026-01-22-001
**Duration:** 12m 34s
**Mode:** standard

## Quality Metrics

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Precision | 87.2% | >= 85% | PASS |
| Recall (Critical) | 96.1% | >= 95% | PASS |
| Recall (High) | 88.3% | >= 85% | PASS |
| Recall (Med/Low) | 74.5% | >= 70% | PASS |
| F1 Score | 0.89 | - | - |

## Per-Segment Breakdown

| Segment | Precision | Recall | Contracts |
|---------|-----------|--------|-----------|
| recent-audits | 89.1% | 91.2% | 25 |
| mutations | 85.3% | 87.8% | 100 |
| adversarial | 72.4% | 76.1% | 15 |

## Agent Component Results

| Agent | Tests | Pass | Fail |
|-------|-------|------|------|
| vrs-context-merge | 12 | 12 | 0 |
| vrs-vuln-discovery | 18 | 18 | 0 |
| vrs-verifier | 15 | 15 | 0 |

## Gaps Identified

- GAP-001: Cross-contract reentrancy (severity: high)
- GAP-002: Multi-token flash loan detection (severity: medium)
- GAP-003: Governance timelock bypass (severity: medium)

## GA Gate Status

**PASS** - All quality gates met.
```

---

## Test Modes

| Mode | Time | Purpose |
|------|------|---------|
| quick | < 2 min | Fast feedback during development |
| standard | < 10 min | Full regression before commits |
| thorough | < 30 min | GA gate, release validation |

### Quick Mode
```bash
/vrs-test-quick  # Separate skill for quick tests
```

### Standard Mode (Default)
```bash
/vrs-test-full  # Runs standard mode by default
```

### Thorough Mode
```bash
/vrs-test-full --mode thorough
```

---

## Quality Gates

### GA Gate Criteria

| Metric | Target | Rationale |
|--------|--------|-----------|
| Precision | >= 85% | Low false positive rate critical for usability |
| Recall (Critical) | >= 95% | Must catch critical vulnerabilities |
| Recall (High) | >= 85% | Should catch most high-severity |
| Recall (Med/Low) | >= 70% | Acceptable miss rate for lower severity |

### Per-Segment Targets

| Corpus Segment | Precision | Recall |
|----------------|-----------|--------|
| Recent Audits | >= 85% | >= 90% |
| Mutations | >= 80% | >= 85% |
| Adversarial | >= 70% | >= 75% |

---

## Related Skills

| Skill | Purpose |
|-------|---------|
| `/vrs-test-quick` | Fast smoke tests (< 2 min) |
| `/vrs-test-component` | Single agent component test |
| `/vrs-benchmark-model` | Model comparison benchmark |
| `/vrs-mutate-contract` | Generate contract mutations |
| `/vrs-track-gap` | Record testing gaps |
| `/vrs-health-check` | Validate VRS installation |

---

## Write Boundaries

This skill is restricted to writing in:
- `.vrs/testing/` - Test results and reports
- `.vrs/rankings/` - Model ranking updates

All other directories are read-only.

---

## Error Handling

| Error | Resolution |
|-------|------------|
| Corpus not found | Initialize with `alphaswarm corpus init` |
| Test failures | Check specific test output for details |
| Model API errors | Verify API keys with `/vrs-health-check` |
| Timeout | Use `--mode quick` for faster feedback |

---

## Notes

- This is a USER-CONTROLLED skill (disable-model-invocation: true)
- Full test suite validates all agent roles and interactions
- Quality gates are enforced before GA release
- Model comparison is optional but recommended before major releases
- Gap tracking integrates with BACKLOG.md for actionable items
- Use `--mode thorough` for release validation
