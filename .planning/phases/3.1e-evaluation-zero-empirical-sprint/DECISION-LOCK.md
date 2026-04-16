# Decision Lock: Phase 3.1e Evaluation Zero -- Empirical Sprint

**Created:** 2026-02-25T21:45:00Z
**Status:** LOCKED
**No-Modification Clause:** All decision rules in this document are immutable after the `locked_at` timestamp in `pre-commitment.json`. Any modification after that timestamp invalidates experimental results. Plan 05 step 0 verifies this constraint.

---

## Plan 01: Minimum Viable Loop

### Outcome Variables Observed

- `precision_delta`: Change in per-function precision after access-tierb-001 YAML fix
- `tp_preserved`: Whether all baseline TPs still fire after fix
- `fp_removed_count`: Number of FPs eliminated by the fix
- `negative_control_pass`: Whether ReentrancyWithGuard access-tierb-001 stops firing after fix

### Decision Rules

```json
{
  "outcome_A": "precision_delta >= 5pp AND zero regressions AND negative_control_pass",
  "outcome_B": "0 < precision_delta < 5pp AND zero regressions",
  "outcome_C": "YAML fix requires > ~200 LOC builder changes with no YAML-addressable subset"
}
```

### Branch Table

Thresholds reference `counting-policy.md` derivation -- NOT hardcoded absolute values.

| Condition | Action |
|-----------|--------|
| `observed_tp < (authoritative_tp - tolerance)` where `authoritative_tp` and `tolerance` are imported from counting-policy.md derivation | Investigation required: TP regression detected. Halt fix. |
| `observed_fp_after < observed_fp_before` AND `observed_tp_after >= observed_tp_before` | FP reduction confirmed without TP regression. Compute precision_delta. |
| precision_delta >= 5pp | Outcome A: Metric responsiveness demonstrated. |
| 0 < precision_delta < 5pp | Outcome B: Weak signal. Document and proceed. |
| YAML fix infeasible (> ~200 LOC builder changes) | Outcome C: Document LOC estimate and builder-fix characterization. |

### No-Modification Clause

Rules locked before Session A execution. No changes permitted after `locked_at` timestamp in `pre-commitment.json`.

---

## Plan 02: First Real LLM Evaluation

### Outcome Variables Observed

- `H1_ordering`: Does LLM produce GOOD > MEDIOCRE > BAD ordering for reasoning_depth?
- `H2_ordering`: Does LLM produce GOOD > MEDIOCRE > BAD ordering for evidence_quality?
- `H3_divergence`: Does LLM explanation cite content heuristic CANNOT access?

### Decision Rules

```json
{
  "scoring": {
    "H1_pass": 1.0,
    "H1_fail": 0.0,
    "H2_pass": 1.0,
    "H2_fail": 0.0,
    "H3_pass": 1.0,
    "H3_partial": 0.5,
    "H3_fail": 0.0
  },
  "go_threshold": "H1 + H2 + H3 >= 2.0",
  "ambiguous_range": "1.0 <= H1 + H2 + H3 <= 1.5",
  "no_go_threshold": "H1 + H2 + H3 < 1.0"
}
```

### No-Modification Clause

Rules locked before Session A execution. No changes permitted after `locked_at` timestamp in `pre-commitment.json`.

---

## Plans 03/04: Taxonomy Discovery + Adversarial Validity

### Outcome Variables Observed

- `taxonomy_categories`: Discovered FP failure categories (undirected discovery)
- `validity_coefficient`: Normalized IC per dimension (Spearman rho for N >= 10, rank-ordering with inversion count for N < 10)
- `gameability_count`: Number of archetype transcripts that fool the heuristic evaluator

### Decision Rules

```json
{
  "taxonomy": {
    "method": "undirected_discovery",
    "scope_tags": ["corpus_specific", "candidate_generalizable"],
    "fix_cost_categories": ["YAML-fixable", "builder-fixable", "architectural", "graph-property-error"]
  },
  "validity_coefficient": {
    "high_validity": "normalized_IC < 0.2",
    "near_zero_validity": "0.2 <= normalized_IC <= 0.4",
    "counter_productive": "normalized_IC > 0.4"
  },
  "gameability": {
    "go_threshold": "successful_gaming_archetypes >= ceil(N/2)",
    "interpretation": "If go_threshold met, heuristic evaluator is gameable and LLM layer is critical defense"
  }
}
```

### No-Modification Clause

Rules locked before Session A execution. No changes permitted after `locked_at` timestamp in `pre-commitment.json`.

---

## Plan 05: Integration + Field Provenance

### Outcome Variables Observed

- `track_activation`: Which integration track (A, B, or C) is activated
- `phase_entry_mode`: Entry mode for 3.1c continuation
- `decision_lock_integrity`: Whether `locked_at` precedes all experiment execution timestamps

### Decision Rules

```json
{
  "track_A": {
    "condition": "Plan 01 Outcome A AND Plan 02 Go AND Plan 03/04 validity confirmed",
    "action": "Full integration: detection + evaluation schemas ready for 3.1c"
  },
  "track_B": {
    "condition": "Plan 01 Outcome A or B AND Plan 02 Ambiguous AND partial validity",
    "action": "Partial integration: detection schemas ready, evaluation needs 3.1c iteration"
  },
  "track_C": {
    "condition": "Plan 01 Outcome C OR Plan 02 No-go OR validity counter-productive",
    "action": "Minimal integration: document blockers, characterize required infrastructure changes for 3.1c"
  },
  "phase_entry_mode": {
    "full": "track_A activated",
    "partial": "track_B activated",
    "diagnostic": "track_C activated"
  }
}
```

### No-Modification Clause

Rules locked before Session A execution. No changes permitted after `locked_at` timestamp in `pre-commitment.json`.
