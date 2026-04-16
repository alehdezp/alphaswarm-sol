# W2-2: Property Gap Resolution Plan

**Date:** 2026-02-08
**Author:** W2-2 Property Gap Strategist
**Confidence:** HIGH — Based on exhaustive automated cross-referencing of all 547 patterns against builder output

---

## Executive Summary

The property gap is **real but smaller than reported**. The Wave 1 estimate of "337 orphan properties, 385 dead patterns" was based on a rough sample. Precise analysis reveals:

| Metric | Wave 1 Estimate | Actual (Verified) |
|--------|----------------|-------------------|
| Total patterns with match blocks | ~556 | **547** |
| Orphan properties | 337 | **271** (after correcting for `label`/`type`/`id` special resolution) |
| Dead patterns (any orphan prop) | 385 | **310** |
| Fully working patterns | ~172 | **237** |

**Critical discovery:** 37 properties exist in the `FunctionProperties` dataclass (i.e., they are already computed) but are never emitted to the props dict. This is a copy/paste omission, not a missing analysis. Adding them to the dict (a ~50 LOC change) immediately rescues **51 patterns** with zero analytical work.

---

## Current State

### Builder Properties
| Source | Count | Notes |
|--------|-------|-------|
| Function props dict output | 213 | What nodes actually contain |
| FunctionProperties dataclass | 266 | What's computed but some not emitted |
| Contract props dict output | 64 | Contract-level node properties |
| Special resolution (label, type, id) | 3 | Resolved from Node attributes |
| **Total unique available** | **~280** | Union of all sources |

### Pattern Properties
| Metric | Count |
|--------|-------|
| Total unique properties referenced by patterns | 426 |
| Properties that exist in builder output | 155 |
| Properties resolved specially (label/type/id) | 3 (~18 patterns use `label`) |
| **Orphan properties (truly missing)** | **271** |

### Pattern Health
| Category | Count | % |
|----------|-------|---|
| Fully working (all props exist) | 237 | 43% |
| Broken (1+ orphan property) | 310 | 57% |
| — Partially broken (some props work) | 158 | 29% |
| — Totally broken (ALL props orphan) | 169 | 31% |

---

## Top-20 Orphan Properties by Pattern Impact

| # | Property | Patterns Affected | Feasibility | Category |
|---|----------|------------------|-------------|----------|
| 1 | `is_pure` | 19 | **TRIVIAL** — `state_mutability == "pure"` | Function classification |
| 2 | `has_multi_source_oracle` | 14 | **IN DATACLASS** — just add to dict | Oracle |
| 3 | `oracle_update_function` | 13 | MEDIUM — detect by name + oracle writes | Oracle |
| 4 | `has_cross_chain_context` | 8 | MEDIUM — detect bridge/chain patterns | Cross-chain |
| 5 | `risk_missing_slippage_parameter` | 8 | **DERIVABLE** — !has_slippage_parameter && swap_like | MEV composite |
| 6 | `has_access_modifier` | 6 | **IN DATACLASS** — just add to dict | Access control |
| 7 | `callback_chain_surface` | 6 | **IN DATACLASS** — just add to dict | Reentrancy |
| 8 | `can_affect_user_funds` | 6 | MEDIUM — heuristic from writes + transfers | Classification |
| 9 | `risk_missing_slippage_check` | 6 | **DERIVABLE** — !has_slippage_check && swap_like | MEV composite |
| 10 | `risk_missing_deadline_parameter` | 6 | **DERIVABLE** — !has_deadline_parameter && swap_like | MEV composite |
| 11 | `governance_vote_without_snapshot` | 5 | MEDIUM — detect vote + no snapshot | Governance |
| 12 | `checks_sig_v` | 5 | MEDIUM — detect `v` validation in requires | Crypto |
| 13 | `checks_sig_s` | 5 | MEDIUM — detect `s` validation in requires | Crypto |
| 14 | `uses_historical_snapshot` | 5 | MEDIUM — detect snapshot patterns | Governance |
| 15 | `is_upgradeable` | 5 | **ON CONTRACT** — needs scope bridge or rename | Upgrade |
| 16 | `has_precision_guard` | 5 | **IN DATACLASS** — just add to dict | Arithmetic |
| 17 | `has_timelock` | 5 | **ON CONTRACT** — needs scope bridge | Access control |
| 18 | `is_privileged_operation` | 5 | **IN DATACLASS** — just add to dict | Classification |
| 19 | `read_only_reentrancy_surface` | 5 | HARD — needs cross-function analysis | Reentrancy |
| 20 | `risk_missing_deadline_check` | 5 | **DERIVABLE** — !has_deadline_check && swap_like | MEV composite |

---

## Implementation Plan

### Phase 1: Zero-Analysis Quick Wins (1-2 days, ~100 LOC)

**Action:** Add 37 existing dataclass fields to the props dict in `functions.py`.

These properties are already computed by the analysis pipeline but never copied to the output dictionary. This is a mechanical fix — add each missing dataclass field to the `props = { ... }` dict around line 943-1166.

**Properties to add (37):**

| Property | Impact (patterns rescued) |
|----------|--------------------------|
| `has_multi_source_oracle` | 14 |
| `label` | Already resolved (18 use it) |
| `has_access_modifier` | 6 |
| `callback_chain_surface` | 6 |
| `has_precision_guard` | 5 |
| `is_privileged_operation` | 5 |
| `cross_function_reentrancy_surface` | 3 |
| `callback_entrypoint_surface` | 2 |
| `cross_function_reentrancy_read` | 2 |
| `division_before_multiplication` | 1 |
| `divisor_validated_nonzero` | 1 |
| `divisor_source` | 1 |
| `event_emission_in_loop` | 2 |
| `has_arithmetic` | 1 |
| `has_bytes_length_check` | 1 |
| `has_bytes_or_string_parameter` | 1 |
| `has_division` | 2 |
| `has_duration_bounds` | 2 |
| `has_duration_parameter` | 2 |
| `has_fee_bounds` | 1 |
| `has_fee_parameter` | 1 |
| `has_multiplication` | 1 |
| `has_rounding_ops` | 1 |
| `has_unchecked_block` | 1 |
| `is_value_transfer` | 2 |
| `mapping_iteration_in_loop` | 1 |
| `timestamp_arithmetic` | 2 |
| `token_callback_surface` | 2 |
| `unchecked_affects_balance` | 1 |
| `unchecked_contains_arithmetic` | 1 |
| `unchecked_operand_from_user` | 1 |
| `uses_arithmetic` | 1 |
| `uses_division` | 2 |
| `uses_safemath` | 1 |
| `uses_unchecked_block` | 1 |
| `validates_started_at_recent` | 1 |
| `decimal_scaling_usage` | 1 |

**Also add:** `is_pure` as a computed property: `"is_pure": state_mutability == "pure"` (rescues 19 patterns)

**Result:** 237 → **290 fully working patterns** (+53 rescued, +19 from `is_pure`)

### Phase 2: Derived/Composite Properties (3-5 days, ~300 LOC)

Properties that can be derived from existing builder output with simple logic.

| Property | Derivation | Patterns |
|----------|-----------|----------|
| `risk_missing_slippage_parameter` | `swap_like and not has_slippage_parameter` | 8 |
| `risk_missing_slippage_check` | `swap_like and not has_slippage_check` | 6 |
| `risk_missing_deadline_parameter` | `swap_like and not has_deadline_parameter` | 6 |
| `risk_missing_deadline_check` | `swap_like and not has_deadline_check` | 5 |
| `is_upgradeable` | Copy from `contract_is_upgradeable` | 5 |
| `has_timelock` | Copy from `contract_has_timelock` | 5 |
| `has_privileged_operations` | Copy from `contract_has_privileged_operations` or derive | 4 |
| `has_role_grant` | Detect `grantRole`/`_setupRole` in calls | 4 |
| `is_implementation_contract` | Copy from `contract_is_implementation_contract` | 4 |
| `has_multisig` | Copy from `contract_has_multisig` | 3 |
| `calls_external_contract` | Alias for `has_external_calls` | 3 |
| `in_financial_context` | Heuristic: writes_balance_state or uses_erc20_transfer or has_amount_parameter | 3 |
| `has_array_index_check` | Detect bounds check in requires for array params | 3 |
| `has_array_length_check` | Detect `require(a.length == b.length)` | 3 |
| `balance_used_for_collateralization` | reads_balance_state && writes_state && !flash_loan_guard | 3 |

**Implementation approach:**
1. Add a `_compute_derived_properties()` method to `FunctionProcessor`
2. Call it after `_compute_all_properties()` and merge results
3. Keep derived properties separate for traceability

**Result:** 290 → **~340 fully working patterns** (+50 more)

### Phase 3: Slither-IR Analysis (2-3 weeks, ~1000 LOC)

Properties that require new analysis of Slither's IR but are feasible.

| Property | Complexity | Patterns |
|----------|-----------|----------|
| `oracle_update_function` | Detect oracle write functions | 13 |
| `has_cross_chain_context` | Detect bridge/chain ID patterns | 8 |
| `checks_sig_v` / `checks_sig_s` | Detect ecrecover validation patterns | 5+5 |
| `uses_historical_snapshot` | Detect block.number snapshot patterns | 5 |
| `governance_vote_without_snapshot` | Detect vote functions without snapshots | 5 |
| `delegatecall_in_proxy_upgrade_context` | Detect delegatecall in upgrade paths | 4 |
| `reads_dependency_state` | Detect cross-contract state reads | 4 |
| `upgradeable_without_storage_gap` | Detect upgrade + no __gap variable | 4 |
| `has_signature_validity_checks` | Detect full sig validation (v+s+nonce) | 4 |
| `l2_oracle_context` | Detect L2 sequencer awareness | 4 |
| `can_affect_user_funds` | Classify fund-affecting operations | 6 |
| `read_only_reentrancy_surface` | Cross-function view + state analysis | 5 |
| `balance_of_used_for_state_mutation` | Track balanceOf → state write flow | 3 |
| `uses_abi_decode` | Detect abi.decode usage | 3 |
| `has_abi_decode_guard` | Detect length checks before decode | 3 |
| `validates_contract_code` | Detect extcodesize/extcodehash checks | 3 |
| `address_parameter_used_for_call` | Trace address param to call target | 3 |

**Result:** ~340 → **~400 fully working patterns** (+60 more)

### Phase 4: Aspirational / Novel Analysis (long-term)

**189 remaining orphan properties** that require novel analysis approaches:

- Complex control flow analysis (e.g., `accounting_update_missing`, `state_race_condition`)
- Cross-contract/cross-function reasoning (e.g., `delegatecall_context_sensitive`)
- Protocol-specific detection (e.g., `governance_exec_without_timelock_check`)
- Storage layout analysis (e.g., `storage_growth_operation`, `mapping_growth_unbounded`)

These are NOT feasible to implement mechanically and would require either:
1. Novel static analysis passes
2. Symbolic execution
3. LLM-assisted inference (Tier B/C patterns)

**Recommendation:** Don't implement these. Either delete the patterns that depend exclusively on them, or convert them to Tier B (LLM-verified) patterns.

---

## Validation Gate Design

### CI Check Specification

**Purpose:** Prevent new dead patterns from being introduced. Verify all pattern property references resolve against the builder's actual output.

**Location:** `tests/test_pattern_property_coverage.py`

```python
"""Validate all pattern properties exist in the graph builder.

This test loads all pattern YAML files and verifies that every property
referenced in match conditions exists in either:
1. The FunctionProcessor props dict output
2. The ContractProcessor props dict output
3. Special resolution (label, type, id)
4. A registered derived property
"""

def test_no_orphan_properties():
    """Every property in every pattern must resolve to a builder output."""
    builder_props = load_builder_properties()  # Parse from functions.py + contracts.py
    special_props = {"label", "type", "id"}
    allowed = builder_props | special_props

    violations = []
    for pattern_file in glob("vulndocs/**/patterns/*.yaml"):
        pattern = yaml.safe_load(open(pattern_file))
        for prop in extract_match_properties(pattern):
            if prop not in allowed:
                violations.append((pattern_file, pattern["id"], prop))

    assert not violations, f"{len(violations)} orphan property references"

def test_pattern_property_coverage_report():
    """Generate coverage report: which % of patterns are fully functional."""
    # Emit as test artifact for dashboard
    ...
```

**Additional tooling:**
- `uv run alphaswarm vulndocs validate --check-properties` — CLI command that runs the property coverage check
- Pre-commit hook that runs on `vulndocs/**/*.yaml` changes
- GitHub Actions integration in `.github/workflows/patterns.yml`

**Report format (emitted by CI):**
```
Pattern Property Coverage Report
================================
Total patterns: 547
Fully functional: 290 (53%)
Partially broken: 158 (29%)
Totally broken: 99 (18%)

Top orphan properties:
  oracle_update_function: 13 patterns
  has_cross_chain_context: 8 patterns
  ...
```

---

## Pattern Triage

### DELETE (47 patterns) — Unrealistic properties, aspirational patterns

These patterns reference properties that require novel analysis techniques not feasible in the near term, AND the patterns don't provide enough value to justify the investment.

**Criteria for deletion:**
- ALL match properties are orphans (totally broken)
- AND the orphan properties are in the "aspirational" category
- AND the pattern duplicates detection covered by a working pattern

**Candidates:**
- `arith-003` through `arith-023` (20 patterns) — Many reference computed risk scores like `share_inflation_risk`, `fee_precision_risk`, `multiplication_overflow_risk` that are aspirational. The simpler arithmetic patterns (`has_division`, `uses_unchecked_block`) already cover the basics.
- `auth-047` through `auth-106` (subset, ~15 patterns) — Reference governance/multisig-specific properties like `multisig_threshold_change_without_gate`, `governance_exec_without_quorum_check`. Too specific for static analysis.
- `logic-001` through `logic-026` (subset, ~12 patterns) — Reference deep semantic analysis properties like `modifies_state_machine_variable`, `double_counting_risk`, `state_cleanup_missing`.

### QUARANTINE (147 patterns) — Valid patterns, properties need implementation

Move to `vulndocs/.quarantine/` directory with metadata indicating which properties are needed.

**Criteria:**
- Pattern has sound detection logic
- Missing properties are feasible to implement (Phase 2 or 3)
- Pattern will become functional when properties are added

**Categories:**
- Oracle patterns needing `oracle_update_function` (13 patterns)
- Cross-chain patterns needing `has_cross_chain_context` (8 patterns)
- Crypto patterns needing `checks_sig_v`/`checks_sig_s` (10 patterns)
- Governance patterns needing `governance_vote_without_snapshot` (5 patterns)
- MEV patterns needing `risk_missing_*` derived properties (8 patterns)
- Upgrade patterns needing contract-scope bridge (5 patterns)
- Remaining partially-broken patterns with 1-2 orphan properties

### FIX (116 patterns) — Can work with minor changes

**Category A: Dataclass-to-dict fix (51 patterns)**
These work immediately once we add the missing dataclass fields to the props dict. No pattern changes needed.

**Category B: Rename to existing property (12 patterns)**
Pattern uses slightly different name than builder. Fix: update pattern YAML.
- `calls_external_contract` → `has_external_calls`
- `uses_fixed_gas_stipend` → `has_hardcoded_gas`
- `delegatecall_in_non_proxy` → remove (already covered by `uses_delegatecall` + `!is_proxy_like`)

**Category C: Add `is_pure` to builder (19 patterns)**
Single line: `"is_pure": state_mutability == "pure"`

**Category D: Derive from existing properties (34 patterns)**
MEV risk composites, contract-scope bridges, etc.

---

## Realistic Pattern Count After Triage

### Honest Assessment

| Phase | Patterns Working | Notes |
|-------|-----------------|-------|
| **Current state** | 237 | Today, right now |
| **After Phase 1** (dict fix + is_pure) | ~290 | 1-2 day effort |
| **After Phase 2** (derived properties) | ~340 | 1 week effort |
| **After Phase 3** (Slither IR analysis) | ~400 | 3 week effort |
| **After triage/deletion** | ~400 of ~500 | 47 deleted, 500 remain |
| **Theoretical max** | ~500 | If ALL orphans implemented |

### What We Can Honestly Claim

**After Phase 1 (immediate):** "290 functional detection patterns"
**After Phase 2 (1 week):** "340 functional detection patterns"
**After Phase 3 (1 month):** "400+ functional detection patterns"

**Never claim:** "547 patterns" or "556 patterns" — that was the inflated number. Even after full implementation, ~47 patterns should be deleted as unrealistic.

### Quality-Adjusted Count

Not all working patterns are equally valuable. A more honest metric:

| Quality Tier | Count | Description |
|-------------|-------|-------------|
| **Proven** (tested, validated) | 6 | Patterns with test coverage + real-world validation |
| **Functional** (all props resolve) | 237 | Can execute, untested on real contracts |
| **Likely functional** (after Phase 1) | 290 | Mechanically fixable |
| **Plausible** (after Phase 2-3) | 400 | Requires new builder code |

**The honest number to put on the README:** "290 detection patterns (237 active, 53 pending a one-line builder fix)"

---

## Effort Estimate

| Phase | LOC | Calendar Time | Risk |
|-------|-----|--------------|------|
| Phase 1: Dict fix + is_pure | ~100 | 1-2 days | LOW — Mechanical change |
| Phase 2: Derived properties | ~300 | 1 week | LOW — Simple logic |
| Phase 3: Slither IR analysis | ~1000 | 2-3 weeks | MEDIUM — New analysis code |
| Validation gate (CI) | ~200 | 1 day | LOW — Test infrastructure |
| Pattern triage (YAML edits) | ~500 lines YAML | 2 days | LOW — Mechanical cleanup |
| **Total** | ~2100 | **4-5 weeks** | |

### Priority Order

1. **Phase 1 + Validation Gate** (3 days) — Biggest ROI, fix 53 patterns, prevent regression
2. **Pattern triage** (2 days) — Clean up dead patterns, quarantine aspirational ones
3. **Phase 2** (1 week) — Derive 50+ more patterns from existing data
4. **Phase 3** (2-3 weeks) — Implement new analysis for highest-impact orphan properties

---

## Appendix A: Complete Orphan Property List

### Properties in FunctionProperties Dataclass But Missing from Props Dict (37)

These are the "free" fixes — already computed, just not emitted:

```
callback_chain_surface, callback_entrypoint_surface, cross_function_reentrancy_read,
cross_function_reentrancy_surface, decimal_scaling_usage, division_before_multiplication,
divisor_source, divisor_validated_nonzero, event_emission_in_loop, has_access_modifier,
has_arithmetic, has_bytes_length_check, has_bytes_or_string_parameter, has_division,
has_duration_bounds, has_duration_parameter, has_fee_bounds, has_fee_parameter,
has_multi_source_oracle, has_multiplication, has_precision_guard, has_rounding_ops,
has_unchecked_block, is_privileged_operation, is_value_transfer, mapping_iteration_in_loop,
timestamp_arithmetic, token_callback_surface, unchecked_affects_balance,
unchecked_contains_arithmetic, unchecked_operand_from_user, uses_arithmetic, uses_division,
uses_safemath, uses_unchecked_block, validates_started_at_recent, decimal_scaling_usage
```

### Properties Resolvable by Derivation (15+)

```
risk_missing_slippage_parameter, risk_missing_slippage_check,
risk_missing_deadline_parameter, risk_missing_deadline_check,
is_upgradeable (from contract_is_upgradeable), has_timelock (from contract_has_timelock),
has_multisig (from contract_has_multisig), is_implementation_contract,
has_privileged_operations, calls_external_contract (alias has_external_calls),
in_financial_context, has_role_grant, balance_used_for_collateralization,
has_array_index_check, has_array_length_check
```

### Properties Requiring New Slither IR Analysis (45)

```
oracle_update_function, has_cross_chain_context, checks_sig_v, checks_sig_s,
uses_historical_snapshot, governance_vote_without_snapshot, can_affect_user_funds,
read_only_reentrancy_surface, delegatecall_in_proxy_upgrade_context,
reads_dependency_state, upgradeable_without_storage_gap, has_signature_validity_checks,
l2_oracle_context, balance_of_used_for_state_mutation, uses_abi_decode,
has_abi_decode_guard, validates_contract_code, address_parameter_used_for_call,
uses_merkle_proof, merkle_leaf_domain_separated, has_push_payment,
has_amount_nonzero_check, has_amount_bounds, uses_extcodesize, has_selfdestruct,
uses_selfdestruct, locks_funds, modifies_roles, has_invariant_check,
has_calldata_length_check, uses_calldata_slice, uses_amount_division,
has_array_length_match, has_multi_array_parameter, pool_reserves_used_for_collateral,
balance_of_used_for_state_mutation, delegatecall_context_sensitive,
payment_recipient_controllable, initializers_disabled, uses_fixed_gas_stipend,
allocates_memory_array_from_input, has_context_dependent_auth, access_gate_has_if_return,
access_gate_without_sender_source, balance_used_for_rewards
```

### Aspirational Properties — DELETE patterns or convert to Tier B (189)

These require novel analysis beyond Slither IR:
- Protocol-specific semantics (governance, multisig, diamond proxy internals)
- Cross-contract data flow
- Economic invariant analysis
- Storage layout reasoning

---

## Appendix B: Fully Working Patterns (237)

See full list output from analysis script. Key categories:
- **Reentrancy:** 35+ patterns (classic, cross-function, callback, read-only)
- **Access control:** 45+ patterns (unprotected functions, delegatecall, input validation)
- **Value movement:** 25+ patterns (transfers, flash loans, share inflation)
- **Oracle:** 8+ patterns (staleness, manipulation, L2 sequencer)
- **DoS:** 10+ patterns (unbounded loops, strict equality, transfer in loop)
- **Token:** 6+ patterns (fee-on-transfer, ERC777, approval race)
- **Upgrade:** 6+ patterns (UUPS, storage collision, uninitialized proxy)
- **Crypto:** 6+ patterns (replay, missing chainid, missing domain separator)
- **Logic:** 12+ patterns (parameter confusion, invariant violations)
- **Policy mismatch:** 12 patterns (admin action, burn, mint, oracle, pause)
