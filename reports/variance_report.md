# Variance Analysis Report

**Report Type:** Multi-Run Variance Analysis for G5 Gate
**Phase:** 07.3.2 - Execution Evidence Protocol
**Gate:** G5 (Consensus & Variance)

---

## Executive Summary

This report documents the variance analysis framework and thresholds for
enforcing reproducibility in AlphaSwarm security audits. Multi-run variance
analysis ensures that audit results are stable across different seed values
and that agent consensus (attacker/defender/verifier) remains within acceptable bounds.

**G5 Gate Purpose:** Ensure multi-run stability and agent consensus.

---

## Variance Thresholds

The following thresholds define acceptable variance bounds for G5 pass/fail:

| Metric | Threshold | Rationale |
|--------|-----------|-----------|
| Variance Coefficient (CV) | <= 0.15 (15%) | Findings count should vary by no more than 15% stddev/mean |
| Findings Delta (max) | <= 2 findings | Maximum difference between runs should not exceed 2 |
| Token Variance | <= 25% delta | Token usage across runs should be within 25% range |
| Timing Variance | <= 30% delta | Execution time variance within 30% is acceptable |
| Agent Agreement | >= 80% | At least 80% agreement between attacker/defender/verifier |
| Disagreement Rate | <= 20% | Maximum 20% disagreement on findings |

---

## Seed Manifest

The deterministic seed manifest ensures reproducible runs:

```yaml
seeds:
  - id: seed-001, value: 42   # Base seed
  - id: seed-002, value: 1337 # Secondary
  - id: seed-003, value: 9876 # Tertiary
  - id: seed-004, value: 5555 # Fourth
  - id: seed-005, value: 2024 # Fifth
```

**Recommended runs:** 5 seeds for production validation.
**Minimum runs:** 3 seeds for quick validation.

---

## Run-by-Run Delta Template

Each variance analysis produces a `variance_result.json` with the following structure:

### Per-Run Metrics

For each seed, the following metrics are captured:

| Field | Type | Description |
|-------|------|-------------|
| `seed_id` | string | Seed identifier |
| `seed_value` | integer | Seed value for randomness |
| `run_id` | string | Unique run identifier |
| `findings_count` | integer | Total findings detected |
| `critical_findings` | integer | Critical severity count |
| `high_findings` | integer | High severity count |
| `medium_findings` | integer | Medium severity count |
| `total_tokens` | integer | Token consumption |
| `duration_ms` | integer | Execution time |
| `attacker_confidence` | float | Attacker agent confidence (0-1) |
| `defender_confidence` | float | Defender agent confidence (0-1) |
| `verifier_confidence` | float | Verifier agent confidence (0-1) |
| `attacker_findings` | list | Findings identified by attacker |
| `defender_findings` | list | Findings confirmed by defender |
| `verifier_findings` | list | Final verified findings |

### Aggregate Variance Metrics

| Category | Metrics |
|----------|---------|
| Findings | mean, stddev, variance_coeff, delta_max |
| Tokens | mean, stddev, variance_coeff, delta_pct |
| Timing | mean, stddev, variance_coeff, delta_pct |
| Consensus | agreement_rate, disagreement_rate, verdict_stability |

---

## G5 Gate Decision Logic

The G5 gate validates variance against thresholds:

```
G5 PASS if ALL of:
  - findings_variance_coeff <= 0.15
  - findings_delta_max <= 2
  - tokens_delta_pct <= 25%
  - timing_delta_pct <= 30%
  - agent_agreement_rate >= 0.80
  - disagreement_rate <= 0.20

G5 FAIL if ANY threshold is exceeded.
```

---

## Agent Consensus Metrics

### Agreement Rate

Measures overlap between attacker, defender, and verifier findings:

```
agreement_rate = |attacker AND defender AND verifier| / |attacker OR defender OR verifier|
```

### Disagreement Rate

```
disagreement_rate = 1 - agreement_rate
```

### Verdict Stability

Measures consistency of verifier findings across different seeds:

```
verdict_stability = |intersection of verifier findings across runs| / |union of verifier findings|
```

---

## Sample Report Output

```
============================================================
MULTI-SEED VARIANCE ANALYSIS RESULT
============================================================
Runs: 5/5 successful

Variance Metrics:
  Findings: mean=5.2, stddev=0.75, CV=0.144
  Tokens: mean=12500, delta=18.3%
  Timing: mean=45000ms, delta=24.1%

Agent Consensus:
  Agreement rate: 85.00%
  Disagreement rate: 15.00%
  Verdict stability: 75.00%

G5 Gate: PASS
============================================================
```

---

## G5 Pass/Fail Status

**Current Status:** FRAMEWORK READY

The variance analysis framework is complete and ready for integration into
the full testing pipeline. G5 gate status will be determined by actual
multi-run validation runs.

| Criterion | Status | Notes |
|-----------|--------|-------|
| Multi-seed harness | COMPLETE | scripts/e2e/run_multiseed_variance.py |
| Seed manifest | COMPLETE | configs/run_seed_manifest.yaml |
| Variance thresholds | DEFINED | See thresholds table above |
| G5 validation logic | COMPLETE | Integrated in harness |
| Evidence pack integration | COMPLETE | Each run produces evidence pack |

---

## Integration with 07.3.2-GATES.md

This variance analysis directly implements **G5: Consensus & Variance** from
the gate definitions:

**From 07.3.2-GATES.md:**

> ## G5 Consensus & Variance
> **Purpose:** Ensure multi-run stability.
>
> **Pass Criteria:**
> - multi-seed variance within tolerance
> - attacker/defender/verifier disagreement below threshold
>
> **Fail Conditions:**
> - high variance or instability

**Implementation Status:** COMPLETE

---

## Usage

```bash
# Run variance analysis with default seeds
uv run python scripts/e2e/run_multiseed_variance.py contracts/ --seeds 5

# Use custom manifest
uv run python scripts/e2e/run_multiseed_variance.py contracts/ \
    --manifest configs/run_seed_manifest.yaml

# Dry run for testing
uv run python scripts/e2e/run_multiseed_variance.py contracts/ --dry-run

# JSON output for CI integration
uv run python scripts/e2e/run_multiseed_variance.py contracts/ --json
```

---

## References

- [07.3.2-GATES.md](../.planning/phases/07.3.2-execution-evidence-protocol/07.3.2-GATES.md) - G5 gate definition
- [07.3.2-EVIDENCE-PACK-SCHEMA.md](../.planning/phases/07.3.2-execution-evidence-protocol/07.3.2-EVIDENCE-PACK-SCHEMA.md) - Evidence pack structure
- [run_seed_manifest.yaml](../configs/run_seed_manifest.yaml) - Seed configuration
- [run_multiseed_variance.py](../scripts/e2e/run_multiseed_variance.py) - Variance harness

---

**Report Generated:** 2026-01-30
**Phase:** 07.3.2 Execution Evidence Protocol
**Plan:** 03 - Multi-Run Variance Analysis
